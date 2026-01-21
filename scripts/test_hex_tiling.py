#!/usr/bin/env python3
"""
Standalone hex tiling test - creates a simple HTML file to test tessellation.
Iterate on spacing values until hexes tile correctly.
"""

import asyncio
import json
from pathlib import Path

project_root = Path(__file__).parent.parent

# Test different tessellation parameters
CONFIGS = {
    "pointy_top_standard": {
        "description": "Standard pointy-top hex math",
        "hexWidth": 211,
        "hexHeight": 181,
        "horizontalSpacing": 211,  # Full width
        "verticalSpacing": 136,    # 0.75 * height
        "oddRowOffsetX": 105.5,    # Half width
        "oddRowOffsetY": 0,
        "offsetOddRows": True,     # vs odd columns
    },
    "pointy_top_tight": {
        "description": "Pointy-top with tighter spacing (overlap)",
        "hexWidth": 211,
        "hexHeight": 181,
        "horizontalSpacing": 199,  # Content width
        "verticalSpacing": 133,    # 0.75 * content height
        "oddRowOffsetX": 99.5,
        "oddRowOffsetY": 0,
        "offsetOddRows": True,
    },
    "pointy_top_experimental": {
        "description": "Pointy-top experimental values",
        "hexWidth": 211,
        "hexHeight": 181,
        "horizontalSpacing": 185,  # Even tighter
        "verticalSpacing": 135,
        "oddRowOffsetX": 92.5,
        "oddRowOffsetY": 0,
        "offsetOddRows": True,
    },
    "flat_top_standard": {
        "description": "Standard flat-top hex math",
        "hexWidth": 211,
        "hexHeight": 181,
        "horizontalSpacing": 158,  # 0.75 * width
        "verticalSpacing": 181,    # Full height
        "oddRowOffsetX": 0,
        "oddRowOffsetY": 90.5,     # Half height
        "offsetOddRows": False,    # Offset odd columns
    },
}


def generate_test_html(config_name: str, config: dict) -> str:
    """Generate a standalone HTML test page for hex tiling."""
    return f'''<!DOCTYPE html>
<html>
<head>
    <title>Hex Tiling Test - {config_name}</title>
    <script src="https://pixijs.download/v7.3.2/pixi.min.js"></script>
    <style>
        body {{ margin: 0; background: #1a1a2e; overflow: hidden; }}
        #info {{
            position: absolute;
            top: 10px;
            left: 10px;
            color: white;
            font-family: monospace;
            background: rgba(0,0,0,0.7);
            padding: 10px;
            border-radius: 5px;
            z-index: 100;
        }}
        #controls {{
            position: absolute;
            top: 10px;
            right: 10px;
            color: white;
            font-family: monospace;
            background: rgba(0,0,0,0.7);
            padding: 10px;
            border-radius: 5px;
            z-index: 100;
        }}
        .slider-row {{ margin: 5px 0; }}
        .slider-row label {{ display: inline-block; width: 120px; }}
        .slider-row input {{ width: 100px; }}
        .slider-row span {{ display: inline-block; width: 50px; }}
    </style>
</head>
<body>
    <div id="info">
        <strong>{config_name}</strong><br>
        {config["description"]}<br>
        <span id="status">Loading...</span>
    </div>
    <div id="controls">
        <div class="slider-row">
            <label>Horiz Spacing:</label>
            <input type="range" id="hSpacing" min="150" max="220" value="{config['horizontalSpacing']}" oninput="updateSpacing()">
            <span id="hSpacingVal">{config['horizontalSpacing']}</span>
        </div>
        <div class="slider-row">
            <label>Vert Spacing:</label>
            <input type="range" id="vSpacing" min="100" max="200" value="{config['verticalSpacing']}" oninput="updateSpacing()">
            <span id="vSpacingVal">{config['verticalSpacing']}</span>
        </div>
        <div class="slider-row">
            <label>Odd Offset X:</label>
            <input type="range" id="offsetX" min="0" max="150" value="{config['oddRowOffsetX']}" oninput="updateSpacing()">
            <span id="offsetXVal">{config['oddRowOffsetX']}</span>
        </div>
        <div class="slider-row">
            <label>Odd Offset Y:</label>
            <input type="range" id="offsetY" min="0" max="150" value="{config['oddRowOffsetY']}" oninput="updateSpacing()">
            <span id="offsetYVal">{config['oddRowOffsetY']}</span>
        </div>
        <button onclick="copyConfig()">Copy Config</button>
    </div>
    <canvas id="canvas"></canvas>

    <script>
        const CONFIG = {{
            hexWidth: {config['hexWidth']},
            hexHeight: {config['hexHeight']},
            horizontalSpacing: {config['horizontalSpacing']},
            verticalSpacing: {config['verticalSpacing']},
            oddRowOffsetX: {config['oddRowOffsetX']},
            oddRowOffsetY: {config['oddRowOffsetY']},
            offsetOddRows: {str(config['offsetOddRows']).lower()},
        }};

        let app, mapContainer, sprites = [];
        let currentConfig = {{...CONFIG}};

        const TERRAIN_TYPES = [
            'TERRAIN_TEMPERATE', 'TERRAIN_ARID', 'TERRAIN_LUSH',
            'TERRAIN_SAND', 'TERRAIN_WATER', 'TERRAIN_MARSH'
        ];

        async function init() {{
            app = new PIXI.Application({{
                view: document.getElementById('canvas'),
                width: window.innerWidth,
                height: window.innerHeight,
                backgroundColor: 0x1a1a2e,
            }});

            mapContainer = new PIXI.Container();
            app.stage.addChild(mapContainer);

            // Load textures
            const textures = {{}};
            for (const terrain of TERRAIN_TYPES) {{
                try {{
                    textures[terrain] = await PIXI.Assets.load(`/assets/sprites/terrains/${{terrain}}.png`);
                }} catch(e) {{
                    console.warn(`Failed to load ${{terrain}}`);
                }}
            }}

            // Create grid of hexes
            createHexGrid(textures);

            // Enable pan/zoom
            setupControls();

            document.getElementById('status').textContent = 'Loaded! Drag to pan, scroll to zoom.';
        }}

        function createHexGrid(textures) {{
            // Clear existing
            mapContainer.removeChildren();
            sprites = [];

            const gridWidth = 15;
            const gridHeight = 12;

            for (let y = 0; y < gridHeight; y++) {{
                for (let x = 0; x < gridWidth; x++) {{
                    // Pick terrain based on position for variety
                    const terrainIndex = (x + y * 3) % TERRAIN_TYPES.length;
                    const terrain = TERRAIN_TYPES[terrainIndex];
                    const texture = textures[terrain];

                    if (!texture) continue;

                    const sprite = new PIXI.Sprite(texture);

                    // Calculate position
                    let pixelX, pixelY;
                    if (currentConfig.offsetOddRows) {{
                        // Pointy-top: odd rows offset horizontally
                        pixelX = x * currentConfig.horizontalSpacing + (y % 2) * currentConfig.oddRowOffsetX;
                        pixelY = y * currentConfig.verticalSpacing;
                    }} else {{
                        // Flat-top: odd columns offset vertically
                        pixelX = x * currentConfig.horizontalSpacing;
                        pixelY = y * currentConfig.verticalSpacing + (x % 2) * currentConfig.oddRowOffsetY;
                    }}

                    sprite.x = pixelX;
                    sprite.y = pixelY;

                    mapContainer.addChild(sprite);
                    sprites.push(sprite);
                }}
            }}

            // Center the map
            mapContainer.x = 100;
            mapContainer.y = 100;
        }}

        function updateSpacing() {{
            currentConfig.horizontalSpacing = parseFloat(document.getElementById('hSpacing').value);
            currentConfig.verticalSpacing = parseFloat(document.getElementById('vSpacing').value);
            currentConfig.oddRowOffsetX = parseFloat(document.getElementById('offsetX').value);
            currentConfig.oddRowOffsetY = parseFloat(document.getElementById('offsetY').value);

            document.getElementById('hSpacingVal').textContent = currentConfig.horizontalSpacing;
            document.getElementById('vSpacingVal').textContent = currentConfig.verticalSpacing;
            document.getElementById('offsetXVal').textContent = currentConfig.oddRowOffsetX;
            document.getElementById('offsetYVal').textContent = currentConfig.oddRowOffsetY;

            // Update sprite positions
            let i = 0;
            const gridWidth = 15;
            const gridHeight = 12;

            for (let y = 0; y < gridHeight; y++) {{
                for (let x = 0; x < gridWidth; x++) {{
                    if (i >= sprites.length) break;

                    let pixelX, pixelY;
                    if (currentConfig.offsetOddRows) {{
                        pixelX = x * currentConfig.horizontalSpacing + (y % 2) * currentConfig.oddRowOffsetX;
                        pixelY = y * currentConfig.verticalSpacing;
                    }} else {{
                        pixelX = x * currentConfig.horizontalSpacing;
                        pixelY = y * currentConfig.verticalSpacing + (x % 2) * currentConfig.oddRowOffsetY;
                    }}

                    sprites[i].x = pixelX;
                    sprites[i].y = pixelY;
                    i++;
                }}
            }}
        }}

        function copyConfig() {{
            const config = `horizontalSpacing: ${{currentConfig.horizontalSpacing}},
verticalSpacing: ${{currentConfig.verticalSpacing}},
oddRowOffsetX: ${{currentConfig.oddRowOffsetX}},
oddRowOffsetY: ${{currentConfig.oddRowOffsetY}}`;
            navigator.clipboard.writeText(config);
            alert('Config copied to clipboard!');
        }}

        function setupControls() {{
            let isDragging = false;
            let lastPos = {{ x: 0, y: 0 }};

            app.view.addEventListener('mousedown', (e) => {{
                isDragging = true;
                lastPos = {{ x: e.clientX, y: e.clientY }};
            }});

            window.addEventListener('mousemove', (e) => {{
                if (isDragging) {{
                    mapContainer.x += e.clientX - lastPos.x;
                    mapContainer.y += e.clientY - lastPos.y;
                    lastPos = {{ x: e.clientX, y: e.clientY }};
                }}
            }});

            window.addEventListener('mouseup', () => {{ isDragging = false; }});

            app.view.addEventListener('wheel', (e) => {{
                e.preventDefault();
                const scale = mapContainer.scale.x * (e.deltaY > 0 ? 0.9 : 1.1);
                mapContainer.scale.set(Math.max(0.1, Math.min(3, scale)));
            }});
        }}

        init();
    </script>
</body>
</html>'''


def create_test_files():
    """Create test HTML files for each config."""
    output_dir = project_root / "tournament_visualizer" / "templates"

    for config_name, config in CONFIGS.items():
        html = generate_test_html(config_name, config)
        output_file = output_dir / f"hex_test_{config_name}.html"
        output_file.write_text(html)
        print(f"Created: {output_file}")

    # Also create a simple route to serve these
    print("\nTo test, add this route to map_routes.py or access directly:")
    print("  http://localhost:8050/hex_test_pointy_top_standard.html")


async def run_visual_test():
    """Run Playwright to capture screenshots of different configs."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1200, "height": 800})

        for config_name in CONFIGS.keys():
            url = f"http://localhost:8050/hex_test_{config_name}.html"
            output_path = project_root / f"hex_test_{config_name}.png"

            try:
                await page.goto(url, timeout=10000)
                await asyncio.sleep(2)  # Wait for render
                await page.screenshot(path=str(output_path))
                print(f"Screenshot: {output_path}")
            except Exception as e:
                print(f"Failed {config_name}: {e}")

        await browser.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--screenshot":
        asyncio.run(run_visual_test())
    else:
        create_test_files()
        print("\nRun with --screenshot to capture test images")
