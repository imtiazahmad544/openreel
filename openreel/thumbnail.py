"""Thumbnail maker: AI/stock background + bold overlay text (PIL, free).

Styles: shock (yellow on black stroke), minimal (white, clean), split (red bar).
"""
from __future__ import annotations

import os
import textwrap

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _fit_lines(draw: ImageDraw.ImageDraw, text: str, max_width: int,
               start_size: int = 110) -> tuple[list[str], ImageFont.FreeTypeFont | ImageFont.ImageFont]:
    size = start_size
    while size > 30:
        font = _font(size)
        words, lines, cur = text.split(), [], ""
        for w in words:
            trial = (cur + " " + w).strip()
            if draw.textlength(trial, font=font) <= max_width:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        if len(lines) <= 3:
            return lines, font
        size -= 10
    return lines, _font(30)


def make_thumbnail(background_path: str | None, title_text: str, out_path: str,
                   style: str = "shock") -> str:
    """Compose a 1280x720 click-worthy thumbnail. Returns out_path."""
    if background_path and os.path.exists(background_path):
        bg = Image.open(background_path).convert("RGB").resize((W, H), Image.LANCZOS)
    else:
        bg = Image.new("RGB", (W, H), (12, 12, 20))

    # darken bottom half for text legibility
    overlay = Image.new("L", (1, H))
    for y in range(H):
        overlay.putpixel((0, y), int(255 * max(0, (y - H * 0.35) / (H * 0.65)) * 0.72))
    black = Image.new("RGB", (W, H), (0, 0, 0))
    bg = Image.composite(black, bg, overlay.resize((W, H)))

    draw = ImageDraw.Draw(bg)
    if style == "split":
        draw.rectangle([0, H - 190, W, H], fill=(200, 20, 20))

    lines, font = _fit_lines(draw, title_text.upper(), W - 160)
    stroke_w = 4
    fill = {"shock": (255, 220, 0), "minimal": (255, 255, 255), "split": (255, 255, 255)}[style]
    line_h = font.size + 14
    total_h = line_h * len(lines)
    y = H - total_h - 70
    for line in lines:
        lw = draw.textlength(line, font=font)
        x = (W - lw) / 2
        draw.text((x, y), line, font=font, fill=fill,
                  stroke_width=stroke_w, stroke_fill=(0, 0, 0))
        y += line_h

    bg.save(out_path, "JPEG", quality=90)
    return out_path
