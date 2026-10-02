from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw


FINAL_SIZE = (1200, 1800)
HEADER_HEIGHT = 150
SIDE_MARGIN = 50
ART_SIZE = (1100, 1650)
LOGO_SIZE = (108, 108)


def compose_branded_character_master(source_png: bytes) -> bytes:
    """Place portrait Character Master art under the official square Mini Utopia badge."""

    source = Image.open(BytesIO(source_png)).convert("RGBA")
    source = source.resize(ART_SIZE, Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", FINAL_SIZE, "#FFF8EE")
    draw = ImageDraw.Draw(canvas)
    # Soft header wash; artwork stays untouched below.
    draw.rectangle((0, 0, FINAL_SIZE[0], HEADER_HEIGHT), fill="#FFF6F9")

    logo_path = (
        Path(__file__).resolve().parents[1]
        / "ui"
        / "assets"
        / "mini_utopia_logo_badge.webp"
    )
    logo = Image.open(logo_path).convert("RGBA")
    logo.thumbnail(LOGO_SIZE, Image.Resampling.LANCZOS)

    logo_x = (FINAL_SIZE[0] - logo.width) // 2
    logo_y = (HEADER_HEIGHT - logo.height) // 2
    canvas.alpha_composite(logo, (logo_x, logo_y))
    canvas.alpha_composite(source, (SIDE_MARGIN, HEADER_HEIGHT))

    out = BytesIO()
    canvas.convert("RGB").save(out, format="PNG", optimize=True)
    return out.getvalue()
