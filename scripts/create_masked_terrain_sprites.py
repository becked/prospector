#!/usr/bin/env python3
"""
Create pre-masked terrain sprites.

Clips terrain sprites to hexagonal boundaries to remove shadow bleed,
enabling fast sprite-based rendering without runtime masking.
"""

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
SPRITES_DIR = PROJECT_ROOT / "tournament_visualizer" / "assets" / "sprites" / "terrains"
OUTPUT_DIR = SPRITES_DIR / "masked"

# Hex geometry - elliptical hex sized to fit within sprite bounds
# Sprite dimensions: 211x181
# Hex must fit entirely within sprite for edge expansion to fill it
HEX_RADIUS_X = 120  # Creates ~208px wide hex (fits in 211px sprite width)
HEX_RADIUS_Y = 88   # Creates 176px tall hex (fits in 181px sprite height with margin)

# Center the hex in the sprite (no offset needed when hex fits within bounds)
VERTICAL_OFFSET = 0


def create_hex_mask(
    width: int, height: int, center_x: float, center_y: float,
    radius_x: float, radius_y: float
) -> Image.Image:
    """Create a pointy-top hexagonal mask with separate x/y scaling.

    Args:
        width: Image width
        height: Image height
        center_x: X coordinate of hex center
        center_y: Y coordinate of hex center
        radius_x: Horizontal radius (half of hex width)
        radius_y: Vertical radius (half of hex height)

    Returns:
        Grayscale image with white hex on black background
    """
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)

    # Calculate pointy-top hex vertices with elliptical scaling
    # Starting from top, going clockwise
    points = []
    for i in range(6):
        angle = (math.pi / 3) * i - math.pi / 2  # Start from top
        x = center_x + radius_x * math.cos(angle)
        y = center_y + radius_y * math.sin(angle)
        points.append((x, y))

    draw.polygon(points, fill=255)
    return mask


def expand_edges(img_array: np.ndarray, iterations: int = 10) -> np.ndarray:
    """Expand opaque pixels into transparent areas.

    Fills transparent pixels with colors from nearby opaque pixels.
    This allows overlapping tiles to show content instead of gaps.

    Args:
        img_array: RGBA numpy array
        iterations: Number of dilation passes

    Returns:
        Modified RGBA array with expanded edges
    """
    result = img_array.copy()
    h, w = result.shape[:2]

    for _ in range(iterations):
        # Find transparent pixels that have opaque neighbors
        alpha = result[:, :, 3]
        transparent = alpha < 128

        # For each transparent pixel, look for opaque neighbors
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            # Shift the array to find neighbors
            shifted_alpha = np.zeros_like(alpha)
            shifted_colors = np.zeros_like(result)

            if dy == -1:
                shifted_alpha[1:, :] = alpha[:-1, :]
                shifted_colors[1:, :] = result[:-1, :]
            elif dy == 1:
                shifted_alpha[:-1, :] = alpha[1:, :]
                shifted_colors[:-1, :] = result[1:, :]
            elif dx == -1:
                shifted_alpha[:, 1:] = alpha[:, :-1]
                shifted_colors[:, 1:] = result[:, :-1]
            elif dx == 1:
                shifted_alpha[:, :-1] = alpha[:, 1:]
                shifted_colors[:, :-1] = result[:, 1:]

            # Fill transparent pixels that have opaque neighbors
            fill_mask = transparent & (shifted_alpha >= 128)
            result[fill_mask] = shifted_colors[fill_mask]

    return result


def mask_terrain_sprite(input_path: Path, output_path: Path) -> None:
    """Apply hex mask to a terrain sprite with edge expansion.

    Args:
        input_path: Path to original sprite PNG
        output_path: Path to save masked sprite
    """
    # Load sprite
    img = Image.open(input_path).convert("RGBA")

    # Center hex on each sprite's actual dimensions
    center_x = img.width / 2
    center_y = img.height / 2 + VERTICAL_OFFSET

    # Convert to numpy
    img_array = np.array(img)

    # Expand edges to fill transparent areas with nearby colors
    # Need enough iterations to fill entire mask area
    img_array = expand_edges(img_array, iterations=50)

    # Create hex mask with elliptical scaling to match tile spacing
    mask = create_hex_mask(img.width, img.height, center_x, center_y, HEX_RADIUS_X, HEX_RADIUS_Y)
    mask_array = np.array(mask)

    # Apply mask directly as alpha (edge expansion filled in RGB values)
    img_array[:, :, 3] = mask_array

    # Save
    masked_img = Image.fromarray(img_array)
    masked_img.save(output_path, "PNG")


def main() -> None:
    """Process all terrain sprites."""
    print("Creating masked terrain sprites...")
    print(f"Input:  {SPRITES_DIR}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Hex radius: {HEX_RADIUS_X}x{HEX_RADIUS_Y}, vertical offset: +{VERTICAL_OFFSET}px")
    print()

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Find all terrain sprites
    terrain_files = sorted(SPRITES_DIR.glob("TERRAIN_*.png"))

    if not terrain_files:
        print("No terrain sprites found!")
        return

    print(f"Found {len(terrain_files)} terrain sprites")

    for input_path in terrain_files:
        output_path = OUTPUT_DIR / input_path.name
        print(f"  Processing {input_path.name}...")
        mask_terrain_sprite(input_path, output_path)

    print()
    print(f"Done! Masked sprites saved to: {OUTPUT_DIR}")
    print()
    print("To use in map_viewer.html, update the sprite path:")
    print("  spriteBase: '/assets/sprites' → load from 'terrains/masked/'")


if __name__ == "__main__":
    main()
