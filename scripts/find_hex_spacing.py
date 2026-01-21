#!/usr/bin/env python3
"""
Interactive hex spacing finder using Playwright.
Tests multiple configurations and saves screenshots.
"""

import asyncio
from pathlib import Path

project_root = Path(__file__).parent.parent


async def test_spacing(page, h_spacing, v_spacing, offset_x):
    """Test a specific spacing configuration."""
    await page.evaluate(f'''
        document.getElementById('hSpacing').value = {h_spacing};
        document.getElementById('vSpacing').value = {v_spacing};
        document.getElementById('offsetX').value = {offset_x};
        updateSpacing();
    ''')
    await asyncio.sleep(0.3)


async def find_best_spacing():
    """Test multiple spacing values to find the best tessellation."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1000, "height": 700})

        # Load the test page
        await page.goto("http://localhost:8050/hex_test_pointy_top_tight.html", timeout=10000)
        await asyncio.sleep(2)

        # Test configurations - trying to find where shadows get hidden
        configs = [
            # (h_spacing, v_spacing, offset_x, description)
            (199, 133, 99.5, "baseline_tight"),
            (195, 130, 97.5, "tighter_1"),
            (190, 128, 95, "tighter_2"),
            (185, 125, 92.5, "tighter_3"),
            (180, 122, 90, "tighter_4"),
            (175, 120, 87.5, "very_tight"),
            (170, 118, 85, "overlap_heavy"),
            # Try different vertical spacings
            (185, 135, 92.5, "h185_v135"),
            (185, 140, 92.5, "h185_v140"),
            (185, 145, 92.5, "h185_v145"),
            # Try matching offset to half of h_spacing
            (188, 130, 94, "balanced_1"),
            (186, 128, 93, "balanced_2"),
            (184, 126, 92, "balanced_3"),
        ]

        output_dir = project_root / "hex_spacing_tests"
        output_dir.mkdir(exist_ok=True)

        for h, v, off, name in configs:
            await test_spacing(page, h, v, off)
            output_file = output_dir / f"{name}_h{h}_v{v}_o{off}.png"
            await page.screenshot(path=str(output_file))
            print(f"Saved: {output_file.name}")

        await browser.close()

    print(f"\nScreenshots saved to: {output_dir}")
    print("Review them to find the best spacing values.")


if __name__ == "__main__":
    asyncio.run(find_best_spacing())
