#!/usr/bin/env python3
"""Build branding/bootanimation/1080.zip for the tokay (Pixel 9) canvas.

Four seconds, 60 fps, square 1080. GrapheneOS centers that square on the
1080x2424 panel and fills the rest with the part background (#000000).

The splash is the M mark: three slanted stripes (light blue, dark blue,
red) and the white M on the same top and bottom edges, with
"MAKE LIFE A RIDE" under it. Geometry is traced from the reference image.
Zip entries are stored, which BootAnimation.cpp requires.
"""

from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

W = 1080
H = 1080
FPS = 60
INTRO_S = 4.0
INTRO_FRAMES = int(FPS * INTRO_S)
BLACK = (0, 0, 0)
FONT = "/usr/share/fonts/TTF/IBMPlexSans-Medium.ttf"
TAG = (236, 236, 236)
TAG_TEXT = "MAKE LIFE A RIDE"

# Fixed crop so every frame sits in the same place on the square canvas.
CROP = (60, 220, 1020, 820)

# Reference image measurements (source pixels).
TOP = 218.0
BOT = 495.0
SLOPE = (290.0 - 452.0) / (BOT - TOP)  # left edge, top sits to the right
STRIPE_L = 452.0
STRIPE_R = 801.0
M_L = 803.0
M_R = 1081.0
MARK_FIT_W = 820.0  # width of the mark on the 1080 canvas, in final pixels

LIGHT = (0, 102, 177, 255)
DARK = (0, 60, 120, 255)
RED = (227, 38, 24, 255)
WHITE = (255, 255, 255, 255)


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if v < lo else hi if v > hi else v


def ease(t: float) -> float:
    t = clamp(t)
    return t * t * (3.0 - 2.0 * t)


def span(t: float, start: float, end: float) -> float:
    if end <= start:
        return 1.0 if t >= end else 0.0
    return ease((t - start) / (end - start))


def _at(x_top: float, y: float) -> float:
    return x_top + SLOPE * (y - TOP)


def _para(x0: float, x1: float) -> list[tuple[float, float]]:
    """Parallelogram from a horizontal top edge down the shared slant."""
    return [(x0, TOP), (x1, TOP), (_at(x1, BOT), BOT), (_at(x0, BOT), BOT)]


def build_mark(scale: int) -> Image.Image:
    """Stripes plus the white M, supersampled, transparent outside the mark."""
    ref_w = (M_R - _at(STRIPE_L, BOT))
    ref_h = BOT - (TOP - 2)
    # scale is the frame supersample. Draw 4x above that, then shrink.
    k = (MARK_FIT_W / ref_w) * scale * 4
    pad = 4

    def xy(x: float, y: float) -> tuple[float, float]:
        return ((x - _at(STRIPE_L, BOT)) * k + pad, (y - (TOP - 2)) * k + pad)

    def poly(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
        return [xy(x, y) for x, y in pts]

    width = int(ref_w * k) + pad * 2
    height = int(ref_h * k) + pad * 2
    mask = Image.new("L", (width, height), 0)
    color = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    md = ImageDraw.Draw(mask)
    cd = ImageDraw.Draw(color)

    stripe_w = (STRIPE_R - STRIPE_L) / 3.0
    for i, fill in enumerate((LIGHT, DARK, RED)):
        x0 = STRIPE_L + i * stripe_w - 0.6
        x1 = STRIPE_L + (i + 1) * stripe_w + 0.6
        pts = poly(_para(x0, x1))
        cd.polygon(pts, fill=fill)
        md.polygon(pts, fill=255)

    outer = poly([(M_L, TOP), (M_R, TOP), (M_R, BOT), (_at(M_L, BOT), BOT)])
    cd.polygon(outer, fill=WHITE)
    md.polygon(outer, fill=255)

    # Counters. Traced from the reference: a valley off the top, then two
    # notches off the bottom that leave three feet.
    holes = (
        [(909, TOP), (976, TOP), (908, 333)],
        [(822, 381), (755, BOT), (824, BOT)],
        [(982, 381), (915, BOT), (983, BOT)],
    )
    for hole in holes:
        md.polygon(poly(hole), fill=0)

    r, g, b, a = color.split()
    color = Image.merge("RGBA", (r, g, b, Image.composite(a, Image.new("L", mask.size, 0), mask)))
    out_w = max(1, width // 4)
    out_h = max(1, height // 4)
    return color.resize((out_w, out_h), Image.Resampling.LANCZOS)


def reveal(mark: Image.Image, p: float) -> Image.Image:
    if p >= 1:
        return mark
    if p <= 0:
        return Image.new("RGBA", mark.size, (0, 0, 0, 0))
    w, h = mark.size
    edge = w * p
    soft = max(2, int(w * 0.035))
    out = Image.new("RGBA", mark.size, (0, 0, 0, 0))
    hard = int(edge - soft)
    if hard > 0:
        out.paste(mark.crop((0, 0, hard, h)), (0, 0))
    band_l = max(0, hard)
    band_r = min(w, int(edge) + 1)
    if band_r <= band_l:
        return out
    band = mark.crop((band_l, 0, band_r, h)).convert("RGBA")
    ramp = Image.new("L", (band.size[0], 1), 0)
    span_px = max(1, band.size[0] - 1)
    ramp.putdata([int(255 * (1 - i / span_px)) for i in range(band.size[0])])
    ramp = ramp.resize(band.size, Image.Resampling.BILINEAR)
    br, bg, bb, ba = band.split()
    ba = ImageChops.multiply(ba, ramp)
    out.alpha_composite(Image.merge("RGBA", (br, bg, bb, ba)), (band_l, 0))
    return out


def tagline_metrics(scale: int) -> tuple[ImageFont.FreeTypeFont, list[int], int, int]:
    font = ImageFont.truetype(FONT, int(32 * scale))
    tracking = int(9 * scale)
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    widths = []
    tops = []
    bottoms = []
    for ch in TAG_TEXT:
        box = probe.textbbox((0, 0), ch, font=font)
        widths.append(box[2] - box[0])
        tops.append(box[1])
        bottoms.append(box[3])
    total = sum(widths) + tracking * (len(TAG_TEXT) - 1)
    height = max(bottoms) - min(tops)
    return font, widths, total, height


def render_frame(t: float, scale: int, mark: Image.Image) -> Image.Image:
    s = scale
    img = Image.new("RGBA", (W * s, H * s), (*BLACK, 255))
    font, widths, total, text_h = tagline_metrics(s)
    gap = int(36 * s)
    block_h = mark.height + gap + text_h
    # Keep the mark and the line together on the cropped window (y 220..820).
    block_top = int(520 * s) - block_h // 2
    shown_p = span(t, 0.25, 1.55)
    if shown_p > 0:
        shown = reveal(mark, shown_p)
        ox = (img.width - mark.width) // 2
        img.alpha_composite(shown, (ox, block_top))

    tag_p = span(t, 1.85, 2.50)
    if tag_p > 0:
        draw = ImageDraw.Draw(img)
        x = (img.width - total) / 2
        y = block_top + mark.height + gap
        fill = (*TAG, int(255 * tag_p))
        tracking = int(9 * s)
        for ch, cw in zip(TAG_TEXT, widths):
            draw.text((x, y), ch, font=font, fill=fill)
            x += cw + tracking

    rgb = img.convert("RGB")
    if s != 1:
        rgb = rgb.resize((W, H), Image.Resampling.LANCZOS)
    return rgb


def crop_png(frame: Image.Image) -> tuple[bytes, str]:
    left, top, right, bottom = CROP
    cropped = frame.crop(CROP)
    buf = io.BytesIO()
    cropped.save(buf, format="PNG", optimize=True)
    trim = f"{right - left}x{bottom - top}+{left}+{top}\n"
    return buf.getvalue(), trim


def stored(z: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name)
    info.compress_type = zipfile.ZIP_STORED
    info.date_time = (1980, 1, 1, 0, 0, 0)
    info.external_attr = 0o644 << 16
    z.writestr(info, data)


def build(out: Path, scale: int) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    mark = build_mark(scale)
    desc = (
        f"{W} {H} {FPS}\n"
        "c 1 0 part0 #000000\n"
        "p 0 0 part1 #000000\n"
    )
    trims = []
    pngs = []
    for i in range(INTRO_FRAMES):
        t = i / FPS
        png, trim = crop_png(render_frame(t, scale, mark))
        pngs.append(png)
        trims.append(trim)
    hold_png, hold_trim = pngs[-1], trims[-1]
    with zipfile.ZipFile(out, "w") as z:
        stored(z, "desc.txt", desc.encode())
        for i, png in enumerate(pngs):
            stored(z, f"part0/{i:05d}.png", png)
        stored(z, "part0/trim.txt", "".join(trims).encode())
        stored(z, "part1/00000.png", hold_png)
        stored(z, "part1/trim.txt", hold_trim.encode())


def preview(directory: Path, scale: int, times: list[float]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    mark = build_mark(scale)
    mark.save(directory / "mark.png")
    for t in times:
        frame = render_frame(t, scale, mark)
        frame.save(directory / f"t{t:.2f}.png")


def main() -> None:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=here / "1080.zip")
    parser.add_argument("--scale", type=int, default=2)
    parser.add_argument("--preview", type=Path, default=None)
    parser.add_argument("--preview-only", action="store_true")
    args = parser.parse_args()
    if args.preview:
        preview(args.preview, args.scale, [0.4, 0.8, 1.2, 1.6, 3.99])
    if args.preview_only:
        return
    build(args.out, args.scale)
    print(f"wrote {args.out} ({args.out.stat().st_size} bytes, {INTRO_FRAMES} intro frames)")


if __name__ == "__main__":
    main()
