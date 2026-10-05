"""Generate a synthetic aerial survey tile for a deterministic live demo."""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


def main() -> None:
    random.seed(24)
    width, height = 1200, 800
    image = Image.new("RGB", (width, height), "#526451")
    draw = ImageDraw.Draw(image)
    # Aerial agricultural parcels with roads, field textures, hedgerows, and rooftops.
    fields = [
        ([(0, 0), (370, 0), (350, 330), (0, 355)], "#70805b"),
        ([(385, 0), (790, 0), (760, 350), (368, 329)], "#677a50"),
        ([(807, 0), (1200, 0), (1200, 348), (779, 352)], "#788761"),
        ([(0, 373), (348, 357), (376, 800), (0, 800)], "#7d815d"),
        ([(371, 356), (770, 376), (804, 800), (396, 800)], "#667b56"),
        ([(792, 373), (1200, 368), (1200, 800), (824, 800)], "#89805e"),
    ]
    for polygon, color in fields:
        draw.polygon(polygon, fill=color)
        min_x = max(0, min(point[0] for point in polygon))
        max_x = min(width, max(point[0] for point in polygon))
        min_y = max(0, min(point[1] for point in polygon))
        max_y = min(height, max(point[1] for point in polygon))
        base = tuple(int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        for _ in range(900):
            x, y = random.randint(min_x, max_x), random.randint(min_y, max_y)
            offset = random.choice([-13, -8, 8, 13])
            shade = tuple(max(0, min(255, channel + offset)) for channel in base)
            draw.ellipse((x, y, x + random.randint(2, 8), y + random.randint(2, 6)), fill=shade)
    # Roads and parcel boundaries.
    draw.line([(0, 365), (270, 351), (560, 369), (850, 358), (1200, 360)], fill="#b8ad8a", width=23)
    draw.line([(366, 0), (359, 190), (365, 366), (383, 600), (391, 800)], fill="#b5aa86", width=18)
    draw.line([(790, 0), (782, 180), (786, 372), (809, 580), (816, 800)], fill="#b5aa86", width=14)
    draw.line([(0, 359), (1200, 367)], fill="#ece0bf", width=2)
    # Small rooftops and water tank details.
    for x, y in [(120, 92), (504, 120), (660, 240), (1037, 106), (163, 564), (622, 544), (1010, 644)]:
        draw.polygon([(x, y + 13), (x + 32, y), (x + 67, y + 13), (x + 35, y + 27)], fill="#c5aa82")
        draw.polygon([(x + 4, y + 12), (x + 34, y + 3), (x + 34, y + 26)], fill="#785d4b")
        draw.polygon([(x + 35, y + 3), (x + 64, y + 13), (x + 35, y + 26)], fill="#9b735c")
    # Warm haze, slight texture, and subtle vignette make the synthetic tile read as aerial imagery.
    image = image.filter(ImageFilter.GaussianBlur(0.35)).filter(ImageFilter.UnsharpMask(radius=2, percent=200, threshold=2))
    tint = Image.new("RGB", image.size, "#ead6a9")
    image = Image.blend(image, tint, 0.055)
    output = Path(__file__).resolve().parents[1] / "sample_data" / "sample_tile.jpg"
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, quality=91, optimize=True)
    print(f"Generated {output} ({width}×{height})")


if __name__ == "__main__":
    main()
