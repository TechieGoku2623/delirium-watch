"""Title, problem, end, and caption cards as 1280x720 PNGs."""

from __future__ import annotations

from pathlib import Path

WIDTH = 1280
HEIGHT = 720
BG = (13, 17, 23)
FG = (230, 237, 243)
MUTED = (139, 148, 158)
ACCENT = (240, 193, 75)


def _font(name: str, size: int):
    from PIL import ImageFont

    candidates = [
        Path("/usr/share/fonts/truetype/dejavu") / name,
        Path("/usr/share/fonts/truetype/liberation") / name,
        Path("/usr/share/fonts/truetype/jetbrains-mono") / name,
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _new_canvas():
    from PIL import Image

    return Image.new("RGB", (WIDTH, HEIGHT), BG)


def _draw_centered(draw, text: str, y: int, font, fill: tuple[int, int, int]) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) / 2, y), text, font=font, fill=fill)


def write_title(path: Path, title: str, tagline: str) -> None:
    from PIL import ImageDraw

    img = _new_canvas()
    draw = ImageDraw.Draw(img)
    title_font = _font("DejaVuSans-Bold.ttf", 64)
    tag_font = _font("DejaVuSans.ttf", 28)
    _draw_centered(draw, title, 260, title_font, FG)
    _draw_centered(draw, tagline, 360, tag_font, MUTED)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG")


def write_problem(path: Path, lines: list[str]) -> None:
    from PIL import ImageDraw

    img = _new_canvas()
    draw = ImageDraw.Draw(img)
    label_font = _font("DejaVuSans-Bold.ttf", 22)
    body_font = _font("DejaVuSans.ttf", 32)
    _draw_centered(draw, "THE PROBLEM", 160, label_font, ACCENT)
    y = 250
    for line in lines:
        _draw_centered(draw, line, y, body_font, FG)
        y += 70
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG")


def write_end(path: Path, url: str, license_name: str) -> None:
    from PIL import ImageDraw

    img = _new_canvas()
    draw = ImageDraw.Draw(img)
    url_font = _font("DejaVuSans-Bold.ttf", 36)
    lic_font = _font("DejaVuSans.ttf", 28)
    _draw_centered(draw, url, 300, url_font, FG)
    _draw_centered(draw, f"License: {license_name}", 380, lic_font, MUTED)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG")


def write_caption_bar(path: Path, lines: list[str]) -> None:
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (WIDTH, 150), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle((40, 10, WIDTH - 40, 140), fill=(0, 0, 0, 210))
    font = _font("DejaVuSans-Bold.ttf", 28)
    total = sum(font.getbbox(line)[3] - font.getbbox(line)[1] for line in lines)
    gap = 8
    y = 75 - (total + gap * (len(lines) - 1)) / 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        draw.text(((WIDTH - w) / 2, y), line, font=font, fill=(255, 255, 255, 255))
        y += (bbox[3] - bbox[1]) + gap
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG")
