# Map Viewer Assets

This document explains how to add and process sprite assets for the interactive map viewer.

## Overview

The map viewer uses 2D sprites exported from Old World's Unity assets via pyunity. Different asset types require different handling:

| Asset Type | Requires Processing | Tessellates |
|------------|---------------------|-------------|
| Terrain tiles | Yes | Yes |
| Improvements | No | No |
| Resources | No | No |
| Specialists | No | No |

## Directory Structure

```
tournament_visualizer/assets/sprites/
├── terrains/
│   ├── TERRAIN_ARID.png          # Original exports
│   ├── TERRAIN_TEMPERATE.png
│   ├── ...
│   └── masked/                    # Processed versions (auto-generated)
│       ├── TERRAIN_ARID.png
│       └── ...
├── improvements/
│   ├── IMPROVEMENT_FARM.png
│   ├── IMPROVEMENT_MINE.png
│   └── ...
├── resources/
│   ├── RESOURCE_WHEAT.png
│   ├── RESOURCE_IRON.png
│   └── ...
└── specialists/
    ├── SPECIALIST_FARMER.png
    ├── SPECIALIST_MINER.png
    └── ...
```

## Terrain Tiles (Special Processing Required)

Terrain tiles must tessellate seamlessly on the hex grid. The exported sprites have:
- 3D shadows baked in that extend beyond hex boundaries
- Transparent corners/edges

These issues cause visible gaps between tiles. The processing script fixes this by:
1. **Edge expansion**: Fills transparent areas with colors from nearby opaque pixels
2. **Hex masking**: Clips sprites to elliptical hex boundaries that match tile spacing

### Adding New Terrain Tiles

1. Export the terrain PNG from Unity/pyunity
2. Place it in `assets/sprites/terrains/` with naming convention `TERRAIN_<NAME>.png`
3. Run the processing script:

```bash
uv run python scripts/create_masked_terrain_sprites.py
```

4. Processed sprites are saved to `terrains/masked/`
5. Restart the server: `uv run python manage.py restart`

### Processing Script Details

The script (`scripts/create_masked_terrain_sprites.py`) uses these parameters:

```python
# Hex geometry - sized to fit within sprite bounds (211x181)
HEX_RADIUS_X = 120  # Horizontal radius (fits in 211px width)
HEX_RADIUS_Y = 88   # Vertical radius (fits in 181px height)

# Hex centered in sprite (no offset)
VERTICAL_OFFSET = 0

# Edge expansion iterations
iterations = 50
```

The hex must fit entirely within the sprite dimensions for edge expansion to work. If you change tile spacing in `map_viewer.html`, update these values accordingly.

### Tile Spacing Configuration

The map viewer (`templates/map_viewer.html`) uses these spacing values:

```javascript
hexHorizontalSpacing: 199,  // Horizontal distance between tile centers
hexVerticalSpacing: 132,    // Vertical distance (1.5 * HEX_RADIUS_Y for pointy-top)
```

These are intentionally smaller than sprite dimensions to create overlap and hide seams.

## Other Assets (No Processing)

Improvements, resources, and specialists are overlays rendered on top of terrain. They don't need processing because:
- They don't tessellate (no seams to hide)
- Transparency is desired (terrain shows through)
- They're auto-scaled to fit within hexes

### Adding New Assets

1. Export the PNG from Unity/pyunity
2. Place in the appropriate directory:
   - `assets/sprites/improvements/IMPROVEMENT_<NAME>.png`
   - `assets/sprites/resources/RESOURCE_<NAME>.png`
   - `assets/sprites/specialists/SPECIALIST_<NAME>.png`
3. Restart the server: `uv run python manage.py restart`

The map viewer automatically loads sprites based on database values.

### Naming Convention Quirks

Religious buildings have swapped naming between database and sprites:
- Database: `IMPROVEMENT_MONASTERY_CHRISTIANITY`
- Sprite file: `IMPROVEMENT_CHRISTIANITY_MONASTERY`

The map viewer handles this mapping automatically in `getSpriteFilename()`.

## Troubleshooting

### Gaps Between Terrain Tiles
- Ensure you ran the processing script after adding new terrains
- Check that the map viewer is loading from `terrains/masked/` not `terrains/`
- May need to adjust `HEX_RADIUS_X/Y` if sprites have different dimensions

### Missing Sprites
- Check browser console for 404 errors
- Verify filename matches database value exactly (case-sensitive)
- Check for naming convention mismatches (especially religious buildings)

### Sprites Not Updating
- Clear browser cache (Cmd+Shift+R / Ctrl+Shift+R)
- Restart the server: `uv run python manage.py restart`

## Future Improvements

For cleaner terrain tiles, consider adjusting the pyunity export process:
- Disable shadow casting/receiving on terrain meshes
- Use unlit shaders during export
- Export at consistent dimensions

This would eliminate the need for post-processing edge expansion.
