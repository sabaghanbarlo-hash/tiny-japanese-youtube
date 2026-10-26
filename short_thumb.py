#!/usr/bin/env python3
"""Tiny Japanese - YouTube Short thumbnail (1280x720, under 2 MB).

Same artwork as the video: the Short's own place behind Mika & Alex (as stickers), a big title card,
a speech bubble with the key phrase, "word = meaning" chips and a "1-minute lesson" ribbon.
short.py makes one for every Short. Make one without rendering the video:

    python short.py shorts/<file>.txt --thumb output/<file>.thumbnail.png
"""
import os, re
from PIL import Image, ImageDraw, ImageFilter
import tinyvideo as T
from tinyvideo import font, wrap, BRAND

TW, TH = 1280, 720
INK, CREAM, GOLD = (52, 40, 44), (255, 252, 247), (255, 203, 92)
LEFT_X, PANEL_W = 36, 604
HAS_JP = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")


def _round(w, h, r, fill, outline=None, width=0):
    im = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, int(w) - 1, int(h) - 1), radius=r, fill=fill, outline=outline, width=width)
    return im


def _shadow(canvas, box, r, blur=16, alpha=95, dy=10):
    x0, y0, x1, y1 = box
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((x0, y0 + dy, x1, y1 + dy), radius=r, fill=(60, 30, 40, alpha))
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))


def _fit(text, sizes, maxw, bold=True):
    for s in sizes:
        f = font(s, bold)
        if f.getlength(text) <= maxw:
            return f
    return font(sizes[-1], bold)


def _lines(text, f, maxw):
    return wrap(text, f, maxw) if " " in text.strip() else T.balanced(text, f, maxw)


def _pill(canvas, x, y, text, fill, fg=(255, 255, 255), size=30, padx=26, h=56):
    f = font(size)
    w = int(f.getlength(text)) + 2 * padx
    im = _round(w, h, h // 2, fill)
    ImageDraw.Draw(im).text((w / 2, h / 2 + 1), text, font=f, fill=fg, anchor="mm")
    canvas.alpha_composite(im, (int(x), int(y)))
    return w


def _short_en(en):
    return re.split(r"\s*/\s*", en.strip())[0]


def _words(lines):
    """(hero phrase, [(jp, romaji, meaning), ...]) - from the key words, else from short Japanese story lines."""
    vocab = [(l["jp"], l["romaji"], _short_en(l["en"])) for l in lines if l.get("kind") == "vocab"]
    if vocab:
        return vocab[0][0], vocab[:2]
    seen, picks = set(), []
    for l in lines:
        jp = l["jp"].strip()
        if l.get("sec") in ("hook", "story", "practice") and HAS_JP.search(jp) and len(jp) <= 12 and jp not in seen:
            seen.add(jp); picks.append((jp, l["romaji"], _short_en(l["en"])))
    return (picks[0][0] if picks else None), picks[:2]


def _sticker(canvas, nm, cx, k=1.15):
    s = T.sprite(nm, 1, False)
    s = s.resize((int(s.width * k), int(s.height * k)), Image.LANCZOS)
    bb = s.getbbox()
    x, y = int(cx - (bb[0] + bb[2]) / 2), TH - bb[3] + 8
    halo = s.getchannel("A").filter(ImageFilter.MaxFilter(11)).filter(ImageFilter.GaussianBlur(1.2))
    white = Image.new("RGBA", s.size, (255, 255, 255, 255)); white.putalpha(halo)
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0)); sh.paste((50, 25, 35, 120), (x, y + 10), halo)
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)))
    canvas.alpha_composite(white, (x, y))
    canvas.alpha_composite(s, (x, y))
    return x + bb[0], x + bb[2], y + bb[1]


def make_thumbnail(meta, lines, out):
    scene = meta.get("scene") if meta.get("scene") in T.SCENES else T.pick_scene(meta, lines)
    bg, _fg = T.make_scene(scene, dict(meta, scene=scene), header=False)
    band = bg.crop((0, 215, T.W, 215 + 608)).convert("RGB").resize((TW, TH), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.5))
    c = band.convert("RGBA")
    shade = Image.new("RGBA", (TW, TH), (0, 0, 0, 0)); d = ImageDraw.Draw(shade)       # soft light behind the title panel
    for i in range(0, 700, 4):
        d.rectangle((0, 0, 700 - i, TH), fill=(255, 245, 240, int(70 * (1 - i / 700) ** 1.5) // 3))
    c.alpha_composite(shade)

    _sticker(c, "Alex", 1092)                                                           # characters, right side
    mx0, mx1, mtop = _sticker(c, "Mika", 845)

    title = meta["title"].strip()                                                       # title card, left side
    maxw = PANEL_W - 64
    for size in (88, 80, 72, 64, 58, 52):
        f = font(size); ls = _lines(title, f, maxw)
        if len(ls) <= 3 and max(f.getlength(x) for x in ls) <= maxw:
            break
    lh = int(size * 1.12)
    card_h = 40 + len(ls) * lh + 62
    y0 = 104
    _shadow(c, (LEFT_X, y0, LEFT_X + PANEL_W, y0 + card_h), 36)
    c.alpha_composite(_round(PANEL_W, card_h, 36, CREAM + (255,), outline=BRAND + (255,), width=6), (LEFT_X, y0))
    dd = ImageDraw.Draw(c); y = y0 + 40 + lh / 2
    for x in ls:
        dd.text((LEFT_X + PANEL_W / 2, y), x, font=f, fill=INK, anchor="mm", stroke_width=max(1, size // 50), stroke_fill=INK); y += lh
    c.alpha_composite(_round(150, 10, 5, BRAND + (255,)), (LEFT_X + (PANEL_W - 150) // 2, y0 + card_h - 38))

    x = LEFT_X                                                                          # top badges
    x += _pill(c, x, 36, "TINY JAPANESE", BRAND) + 12
    if meta.get("episode"):
        _pill(c, x, 36, f"EP {meta['episode']}", (60, 45, 48))

    hero, chips = _words(lines)                                                         # speech bubble with the key phrase
    if hero:
        bf = _fit(hero, (84, 76, 68, 60, 52), 460)
        bwid, bhei = int(bf.getlength(hero)) + 76, 108
        bx = int(max(mx0 + 10, min(mx0 + 60, TW - bwid - 24))); by = 30
        _shadow(c, (bx, by, bx + bwid, by + bhei), 40, blur=10, alpha=80, dy=7)
        c.alpha_composite(_round(bwid, bhei, 40, (255, 255, 255, 255), outline=BRAND + (255,), width=5), (bx, by))
        tx, g = bx + 78, ImageDraw.Draw(c)
        g.polygon([(tx - 26, by + bhei - 3), (tx + 30, by + bhei - 3), (tx - 2, by + bhei + 34)], fill=(255, 255, 255, 255))
        g.line([(tx - 26, by + bhei - 2), (tx - 2, by + bhei + 34), (tx + 30, by + bhei - 2)], fill=BRAND + (255,), width=5)
        g.line([(tx - 20, by + bhei - 3), (tx + 24, by + bhei - 3)], fill=(255, 255, 255, 255), width=8)
        g.text((bx + bwid / 2, by + bhei / 2 + 2), hero, font=bf, fill=INK, anchor="mm")

    cy = y0 + card_h + 24                                                               # "word = meaning" chips
    room = max(0, min(2, (624 - cy + 12) // 74))                                        # keep them clear of the ribbon
    for jp, ro, en in chips[:room]:
        label = f"{ro} = {en}" if ro else f"{jp} = {en}"
        cf = _fit(label, (36, 33, 30, 27, 24), PANEL_W - 56)
        w = min(PANEL_W, int(cf.getlength(label)) + 56)
        _shadow(c, (LEFT_X, cy, LEFT_X + w, cy + 62), 31, blur=7, alpha=60, dy=5)
        c.alpha_composite(_round(w, 62, 31, (255, 255, 255, 245)), (LEFT_X, cy))
        ImageDraw.Draw(c).text((LEFT_X + w / 2, cy + 32), label, font=cf, fill=INK, anchor="mm")
        cy += 74

    rf = font(32); label = "LEARN JAPANESE IN 1 MINUTE"                                 # ribbon
    rw, rh = int(rf.getlength(label)) + 64, 60
    ry = TH - rh - 30
    _shadow(c, (LEFT_X, ry, LEFT_X + rw, ry + rh), 30, blur=7, alpha=70, dy=5)
    rb = _round(rw, rh, 30, GOLD + (255,)); ImageDraw.Draw(rb).text((rw / 2, rh / 2 + 1), label, font=rf, fill=INK, anchor="mm")
    c.alpha_composite(rb, (LEFT_X, ry))

    im = c.convert("RGB")
    im.save(out, optimize=True)
    if os.path.getsize(out) > 1_900_000:                                                # YouTube limit is 2 MB
        im.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(out, optimize=True)
    print(f"Thumbnail: {out} ({os.path.getsize(out) // 1024} KB, scene {scene}); title {len(ls)} lines @ {size}px, "
          f"bubble {bx if hero else None}+{bwid if hero else None}, card bottom {y0 + card_h}, chips end {cy}, ribbon y {ry}, panel right {LEFT_X + PANEL_W}, Mika left {mx0}")
    return out
