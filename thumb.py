#!/usr/bin/env python3
"""Tiny Japanese - YouTube thumbnail: your approved illustration with each episode's title painted in.

Usage: python thumb.py lessons/01-first-day-at-school.txt output/01-first-day-at-school.thumbnail.png
Needs assets/thumbnail_template.png. If it is missing the existing thumbnail is left untouched.
"""
import glob, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import lesson as L
from lesson import font, wrap

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "thumbnail_template.png")
NAVY = (42, 67, 146)


def _title_font(size):
    for pat in ("/usr/share/fonts/**/NotoSansCJK-Black.ttc", "/usr/share/fonts/**/NotoSansCJK-Bold.ttc"):
        g = sorted(glob.glob(pat, recursive=True))
        if g:
            try:
                return ImageFont.truetype(g[0], size)
            except Exception:
                pass
    return font(size)


def thumbnail_from_template(meta, path):
    """Cover = the approved illustration (assets/thumbnail_template.png) with this episode's title painted in."""
    im = Image.open(TEMPLATE).convert("RGB")
    sw, sh = im.size; k = sw / 1672
    box = tuple(int(v * k) for v in (300, 540, 1385, 775))          # area holding the old title text
    arr = np.asarray(im).astype(int)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    ink = (r < 120) & (g < 130) & (b < 200) & (b > r + 25)           # navy letters only (not the purple/pink decor)
    m = np.zeros(ink.shape, bool); m[box[1]:box[3], box[0]:box[2]] = ink[box[1]:box[3], box[0]:box[2]]
    inner = tuple(int(v * k) for v in (335, 575, 1355, 772))         # inside the white banner: wipe the old sparkles + flower too
    sat = (arr.max(axis=2) - arr.min(axis=2)) > 28
    m[inner[1]:inner[3], inner[0]:inner[2]] |= sat[inner[1]:inner[3], inner[0]:inner[2]]
    mask = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(11))
    im.paste((253, 253, 253), mask=mask)
    d = ImageDraw.Draw(im)
    ep = f"Ep.{meta['episode']} · " if meta.get("episode") else ""
    text = ep + meta["title"]
    bw, bh = int((box[2] - box[0]) * 0.97), int((box[3] - box[1]) * 0.98)
    size = int(128 * k)
    while size > 40:
        f = _title_font(size); ls = wrap(text, f, bw)
        if len(ls) <= 2 and max(f.getlength(x) for x in ls) <= bw and int(size * 1.1) * len(ls) <= bh:
            break
        size -= 4
    f = _title_font(size); lh = int(size * 1.12)
    y = (box[1] + box[3]) / 2 - lh * len(ls) / 2 + lh / 2 + 4
    cx = (box[0] + box[2]) / 2
    for x in ls:
        d.text((cx, y), x, font=f, fill=NAVY, anchor="mm", stroke_width=max(1, size // 40), stroke_fill=NAVY); y += lh
    # little decorations beside the last line, like the original banner
    ly, half = y - lh, f.getlength(ls[-1]) / 2
    fx, rx = cx - half - 50 * k, cx + half + 70 * k
    if len(ls) > 1 and rx < box[2] - 20 * k:
        pr = 22 * k
        for a in range(5):
            ang = a * 2 * math.pi / 5 - math.pi / 2
            px, py = rx + math.cos(ang) * pr * .9, ly + math.sin(ang) * pr * .9
            d.ellipse((px - pr * .62, py - pr * .62, px + pr * .62, py + pr * .62), fill=(250, 170, 215))
        d.ellipse((rx - pr * .35, ly - pr * .35, rx + pr * .35, ly + pr * .35), fill=(255, 215, 120))
    if len(ls) > 1 and fx > box[0] + 20 * k:
        for dy, ln in ((-22, 34), (2, 40), (26, 30)):
            d.line((fx - ln * k, ly + dy * k, fx, ly + dy * k * 0.6), fill=(133, 126, 251), width=max(3, int(7 * k)))
    im.resize((1280, 720), Image.LANCZOS).save(path)


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: python thumb.py <script.txt> <out.png>")
    if not os.path.exists(TEMPLATE):
        print("assets/thumbnail_template.png not found - keeping the default thumbnail"); return
    meta = L.parse_script(sys.argv[1])[0]
    thumbnail_from_template(meta, sys.argv[2])
    print("Wrote", sys.argv[2])


if __name__ == "__main__":
    main()
