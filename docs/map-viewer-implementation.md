# Map Viewer Implementation

This document explains the architecture and implementation of the interactive Map (Beta) feature.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Dash App (matches.py)                                      │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Tabs: Overview | Diplomacy | Map | Map (Beta) | ...    ││
│  └─────────────────────────────────────────────────────────┘│
│                              │                               │
│  ┌───────────────────────────▼─────────────────────────────┐│
│  │  <iframe src="/map/viewer/{match_id}">                  ││
│  │  ┌─────────────────────────────────────────────────────┐││
│  │  │  Pixi.js Map Viewer (self-contained)                │││
│  │  │  - Turn slider                                      │││
│  │  │  - Layer toggles                                    │││
│  │  │  - Pan/zoom                                         │││
│  │  └─────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌─────────────────────┐    ┌─────────────────────────────────┐
│  Flask API Routes   │    │  Static Assets                  │
│  /api/map/*         │    │  /assets/sprites/*              │
└─────────────────────┘    └─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  DuckDB (territories table)                                 │
└─────────────────────────────────────────────────────────────┘
```

The map viewer is fully self-contained within an iframe. All controls (turn slider, layer toggles, pan/zoom) are handled inside the iframe with no communication back to the parent Dash app.

## Key Files

| File | Purpose |
|------|---------|
| `tournament_visualizer/api/__init__.py` | Flask Blueprint definition |
| `tournament_visualizer/api/map_routes.py` | API endpoints for map data |
| `tournament_visualizer/templates/map_viewer.html` | Pixi.js viewer (~1300 lines) |
| `tournament_visualizer/assets/sprites/` | Sprite assets |
| `scripts/create_masked_terrain_sprites.py` | Terrain preprocessing script |

## Data Flow

### 1. User Navigates to Map (Beta) Tab

The Dash app embeds an iframe pointing to the Flask-served map viewer:

```python
# In matches.py
html.Iframe(
    src=f"/map/viewer/{match_id}",
    style={"width": "100%", "height": "700px", "border": "none"}
)
```

### 2. Flask Serves the Map Viewer HTML

```python
# map_routes.py:34
@map_api.route("/map/viewer/<int:match_id>")
def map_viewer(match_id: int) -> str:
    # Gets player names for page title
    # Returns rendered Jinja template with match_id injected
    return render_template("map_viewer.html", match_id=match_id, ...)
```

### 3. Pixi.js Initializes and Fetches Data

```javascript
// map_viewer.html - on page load
async function init() {
    // Get turn range for this match
    const turnRange = await fetchTurnRange();  // GET /api/map/turn-range/{match_id}

    // Initialize Pixi.js WebGL canvas
    await initPixi();

    // Load map data for the final turn
    await loadMapData(currentTurn);  // GET /api/map/territories/{match_id}/{turn}
}
```

### 4. API Returns Territory Data

```python
# map_routes.py:114
@map_api.route("/api/map/territories/<int:match_id>/<int:turn_number>")
def api_territories(match_id: int, turn_number: int):
    df = queries.get_territory_map_full(match_id, turn_number)
    # Transforms DataFrame to JSON with tiles, players, map_info
```

Response structure:

```json
{
  "match_id": 1,
  "turn_number": 90,
  "map_info": { "width": 46, "height": 26 },
  "players": [
    { "player_id": 1, "name": "Sabertooth", "civilization": "Aksum", "color": "#F6EFE1" }
  ],
  "tiles": [
    {
      "x": 10, "y": 5,
      "terrain": "TERRAIN_TEMPERATE",
      "owner": 1,
      "improvement": "IMPROVEMENT_FARM",
      "specialist": "SPECIALIST_FARMER",
      "resource": "RESOURCE_WHEAT",
      "road": true,
      "city": { "name": "Aksum", "population": 12, "is_capital": true }
    }
  ]
}
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/map/viewer/<match_id>` | GET | HTML page with Pixi.js viewer |
| `/api/map/turn-range/<match_id>` | GET | Returns `{min_turn, max_turn}` |
| `/api/map/territories/<match_id>/<turn>` | GET | Returns full tile data for a turn |

## Rendering Layers

The map has 7 layers rendered in z-index order:

| Layer | Z-Index | Default Visible | Content |
|-------|---------|-----------------|---------|
| Terrain | 0 | Yes | Pre-masked hex terrain sprites |
| Roads | 1 | No | Line graphics between tiles |
| Ownership | 2 | Yes | Territory fill + multi-layer glowing borders |
| Improvements | 3 | No | Building sprites (farms, mines, etc.) |
| Resources | 4 | No | Small resource icons (wheat, iron, etc.) |
| Specialists | 5 | No | Worker portrait sprites |
| Cities | 6 | Yes | City sprites + name labels |

### Terrain Layer Rendering

Terrain is the base layer and uses pre-processed sprites:

```javascript
function renderTerrainLayer() {
    mapData.tiles.forEach(tile => {
        const pos = hexToPixel(tile.x, tile.y);
        const centerX = pos.x + CONFIG.hexHorizontalSpacing / 2;
        const centerY = pos.y + CONFIG.hexVerticalSpacing / 2;

        // Load pre-masked sprite (processed by Python script)
        const texture = spriteTextures[tile.terrain];
        const sprite = new PIXI.Sprite(texture);
        sprite.anchor.set(0.5);
        sprite.x = centerX;
        sprite.y = centerY;

        layers.terrain.addChild(sprite);
    });
}
```

### Ownership Layer Rendering

Ownership is shown with two visual elements:

1. **Territory Fill**: Translucent colored overlay (15% opacity) on all owned tiles
2. **Border Glow**: Multi-layer glowing borders at territory edges

The border effect uses 5 stacked layers for a game-like appearance:

| Layer | Width | Alpha | Purpose |
|-------|-------|-------|---------|
| Outermost glow | 28px | 15% | Soft colored halo |
| Shadow | 20px | 40% | Dark depth |
| Mid glow | 14px | 60% | Color spread |
| Core | 8px | 100% | Main border |
| Highlight | 3px | 90% | Bright center |

```javascript
function renderOwnershipLayer() {
    // 1. Draw territory fill (translucent hex for each owned tile)
    tiles.forEach(({ cx, cy }) => {
        graphics.beginFill(playerColor, 0.15);
        drawFilledHex(graphics, cx, cy, 120, 88);
        graphics.endFill();
    });

    // 2. Draw border edges where neighbors have different owner
    // Each edge rendered 5 times with decreasing width for glow effect
}
```

## Hex Grid Math

The map uses pointy-top hexagons with odd-r offset coordinates:

```javascript
// Configuration
const CONFIG = {
    hexHorizontalSpacing: 199,  // Horizontal distance between tile centers
    hexVerticalSpacing: 132,    // Vertical distance (1.5 * radius_y for pointy-top)
    hexRadiusX: 120,            // Horizontal radius for border drawing
    hexRadiusY: 88,             // Vertical radius for border drawing
};

// Convert grid coordinates to pixel position
function hexToPixel(x, y) {
    // Odd rows are offset horizontally by half the spacing
    const pixelX = x * CONFIG.hexHorizontalSpacing
                 + (y % 2) * (CONFIG.hexHorizontalSpacing / 2);
    const pixelY = y * CONFIG.hexVerticalSpacing;
    return { x: pixelX, y: pixelY };
}
```

### Neighbor Offsets (Pointy-Top Odd-R)

```javascript
// For odd rows (y % 2 === 1)
const oddRowNeighbors = [
    [1, -1],   // Upper-right
    [1, 0],    // Right
    [1, 1],    // Lower-right
    [0, 1],    // Lower-left
    [-1, 0],   // Left
    [0, -1],   // Upper-left
];

// For even rows (y % 2 === 0)
const evenRowNeighbors = [
    [0, -1],   // Upper-right
    [1, 0],    // Right
    [0, 1],    // Lower-right
    [-1, 1],   // Lower-left
    [-1, 0],   // Left
    [-1, -1],  // Upper-left
];
```

## User Controls

### Turn Slider

Changes the displayed turn, fetches new data, and re-renders all layers:

```javascript
slider.addEventListener('input', (e) => {
    const turn = parseInt(e.target.value);
    document.getElementById('turn-value').textContent = turn;

    // Debounce to avoid excessive API calls
    clearTimeout(sliderTimeout);
    sliderTimeout = setTimeout(() => {
        currentTurn = turn;
        loadMapData(turn);  // Fetches new data and re-renders
    }, 150);
});
```

### Layer Toggles

Show/hide layers instantly without refetching data:

```javascript
document.getElementById('toggle-improvements').addEventListener('change', (e) => {
    layers.improvements.visible = e.target.checked;
});
```

### Pan and Zoom

Mouse drag to pan, scroll wheel to zoom:

```javascript
// Drag to pan
mapContainer.addEventListener('mousedown', (e) => {
    isDragging = true;
    lastDragPos = { x: e.clientX, y: e.clientY };
});

window.addEventListener('mousemove', (e) => {
    if (isDragging) {
        layers.mapContainer.x += e.clientX - lastDragPos.x;
        layers.mapContainer.y += e.clientY - lastDragPos.y;
        lastDragPos = { x: e.clientX, y: e.clientY };
    }
});

// Scroll to zoom (toward mouse position)
mapContainer.addEventListener('wheel', (e) => {
    e.preventDefault();
    const scaleFactor = e.deltaY > 0 ? 0.9 : 1.1;
    const newScale = layers.mapContainer.scale.x * scaleFactor;

    if (newScale >= 0.1 && newScale <= 3) {
        // Zoom toward mouse position
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;
        // ... adjust position to keep mouse point stable
        layers.mapContainer.scale.set(newScale);
    }
});
```

## Sprite Processing

Terrain sprites exported from Unity have baked-in 3D shadows that extend beyond hex boundaries. This causes visible gaps when tiling. The processing script fixes this:

```
Original sprite (211x181)     →    Processing script    →    Masked sprite
- Has shadow bleed                  - Edge expansion          - Clean hex shape
- Transparent corners               - Hex masking             - Filled edges
```

Run after adding new terrain sprites:

```bash
uv run python scripts/create_masked_terrain_sprites.py
```

See `docs/map-viewer-assets.md` for complete details on asset management.

## Performance Characteristics

| Metric | Typical Value |
|--------|---------------|
| Tiles per map | ~2000 |
| PIXI.Sprites for terrain | ~2000 (one per tile) |
| Initial load time | ~1-2 seconds |
| Turn change re-render | ~200ms |
| Layer toggle | Instant (no re-render) |

**Optimizations applied:**
- Pre-masked sprites (no runtime masking)
- Single sprite per terrain tile (no containers/masks)
- Layer visibility toggle without data refetch
- Debounced turn slider to reduce API calls

## Tooltip

Hovering over a tile shows detailed information:

```javascript
function showTooltip(event, tile) {
    // Title: owner name or "Unowned", city name if applicable
    // Content: terrain, position, improvement, resource, specialist, road, population
}
```

## Player Legend

Shows player colors and civilizations in the top-right corner:

```javascript
function updatePlayerLegend(players) {
    // Creates colored boxes with "PlayerName (Civilization)" labels
}
```

## Error Handling

- API errors show user-friendly messages
- Missing sprites fall back to colored hexagons
- Loading overlay displays during data fetch

## Future Improvements

Potential enhancements:
- Viewport culling (only render visible tiles)
- Tile caching across turn changes
- Minimap for navigation
- Unit layer (if unit data is added to database)
- Animation for turn transitions
