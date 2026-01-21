#!/usr/bin/env python3
"""
Fine-tuning hex spacing - focusing on values around h=170-180.
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
    await asyncio.sleep(0.2)


async def find_best_spacing():
    """Test multiple spacing values to find the best tessellation."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1000, "height": 700})

        await page.goto("http://localhost:8050/hex_test_pointy_top_tight.html", timeout=10000)
        await asyncio.sleep(2)

        # Fine-tuning around the heavy overlap values
        configs = [
            # (h_spacing, v_spacing, offset_x, description)
            # Vary vertical around 115-125 with h=170-175
            (172, 115, 86, "h172_v115"),
            (172, 118, 86, "h172_v118"),
            (172, 120, 86, "h172_v120"),
            (172, 122, 86, "h172_v122"),
            (175, 118, 87.5, "h175_v118"),
            (175, 120, 87.5, "h175_v120"),
            (175, 122, 87.5, "h175_v122"),
            (175, 125, 87.5, "h175_v125"),
            # Try with slightly different offsets
            (173, 119, 86.5, "h173_v119_o86.5"),
            (173, 119, 87, "h173_v119_o87"),
            (173, 119, 88, "h173_v119_o88"),
            # Even tighter
            (168, 116, 84, "h168_v116"),
            (165, 114, 82.5, "h165_v114"),
        ]

        output_dir = project_root / "hex_spacing_tests"
        output_dir.mkdir(exist_ok=True)

        for h, v, off, name in configs:
            await test_spacing(page, h, v, off)
            output_file = output_dir / f"{name}.png"
            await page.screenshot(path=str(output_file))
            print(f"Saved: {name}")

        await browser.close()

    print(f"\nScreenshots saved to: {output_dir}")


if __name__ == "__main__":
    asyncio.run(find_best_spacing())
