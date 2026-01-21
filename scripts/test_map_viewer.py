#!/usr/bin/env python3
"""
Test script to iterate on map viewer hex tessellation using Playwright.
Takes screenshots and analyzes hex sprite structure.
"""

import asyncio
import sys
from pathlib import Path
from PIL import Image
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def analyze_terrain_sprite(sprite_path: Path) -> dict:
    """Analyze a terrain sprite to understand its structure."""
    img = Image.open(sprite_path).convert("RGBA")
    data = np.array(img)

    # Get dimensions
    height, width = data.shape[:2]

    # Find non-transparent pixels
    alpha = data[:, :, 3]
    non_transparent = alpha > 10

    # Find bounding box of non-transparent content
    rows = np.any(non_transparent, axis=1)
    cols = np.any(non_transparent, axis=0)

    if not rows.any() or not cols.any():
        return {"error": "No non-transparent pixels found"}

    row_indices = np.where(rows)[0]
    col_indices = np.where(cols)[0]

    content_top = row_indices[0]
    content_bottom = row_indices[-1]
    content_left = col_indices[0]
    content_right = col_indices[-1]

    content_width = content_right - content_left + 1
    content_height = content_bottom - content_top + 1

    # Check transparency at corners and edges
    corner_samples = {
        "top_left": alpha[0, 0],
        "top_right": alpha[0, width-1],
        "bottom_left": alpha[height-1, 0],
        "bottom_right": alpha[height-1, width-1],
        "top_center": alpha[0, width//2],
        "bottom_center": alpha[height-1, width//2],
        "left_center": alpha[height//2, 0],
        "right_center": alpha[height//2, width-1],
    }

    # Find where the hex content starts/ends horizontally at different rows
    hex_profile = []
    for y in range(0, height, 10):
        row_alpha = alpha[y, :]
        non_zero = np.where(row_alpha > 10)[0]
        if len(non_zero) > 0:
            hex_profile.append({
                "y": y,
                "left": int(non_zero[0]),
                "right": int(non_zero[-1]),
                "width": int(non_zero[-1] - non_zero[0] + 1)
            })

    return {
        "sprite_size": (width, height),
        "content_bounds": {
            "top": int(content_top),
            "bottom": int(content_bottom),
            "left": int(content_left),
            "right": int(content_right),
        },
        "content_size": (content_width, content_height),
        "corner_alpha": corner_samples,
        "hex_profile": hex_profile,
    }


def analyze_all_terrain_sprites():
    """Analyze all terrain sprites to understand the hex shape."""
    sprites_dir = project_root / "tournament_visualizer" / "assets" / "sprites" / "terrains"

    print("=" * 60)
    print("TERRAIN SPRITE ANALYSIS")
    print("=" * 60)

    for sprite_file in sorted(sprites_dir.glob("*.png")):
        print(f"\n{sprite_file.name}:")
        analysis = analyze_terrain_sprite(sprite_file)

        if "error" in analysis:
            print(f"  Error: {analysis['error']}")
            continue

        print(f"  Sprite size: {analysis['sprite_size']}")
        print(f"  Content bounds: {analysis['content_bounds']}")
        print(f"  Content size: {analysis['content_size']}")
        print(f"  Corner alpha values: {analysis['corner_alpha']}")
        print(f"  Hex profile (y -> left, right, width):")
        for p in analysis['hex_profile'][:5]:  # First 5 rows
            print(f"    y={p['y']:3d}: left={p['left']:3d}, right={p['right']:3d}, width={p['width']:3d}")
        print("    ...")
        for p in analysis['hex_profile'][-3:]:  # Last 3 rows
            print(f"    y={p['y']:3d}: left={p['left']:3d}, right={p['right']:3d}, width={p['width']:3d}")


async def take_map_screenshot(url: str, output_path: str):
    """Take a screenshot of the map viewer."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})

        await page.goto(url)

        # Wait for map to load
        await page.wait_for_selector("#map-canvas", timeout=10000)
        await asyncio.sleep(2)  # Wait for sprites to render

        await page.screenshot(path=output_path)
        print(f"Screenshot saved to: {output_path}")

        await browser.close()


async def main():
    # First, analyze the terrain sprites
    analyze_all_terrain_sprites()

    # Then take a screenshot of the current map
    print("\n" + "=" * 60)
    print("TAKING MAP SCREENSHOT")
    print("=" * 60)

    try:
        await take_map_screenshot(
            "http://localhost:8050/map/viewer/1",
            str(project_root / "test_map_screenshot.png")
        )
    except Exception as e:
        print(f"Failed to take screenshot: {e}")
        print("Make sure the server is running: uv run python manage.py start")


if __name__ == "__main__":
    asyncio.run(main())
