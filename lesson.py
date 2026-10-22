#!/usr/bin/env python3
"""Tiny Japanese - YouTube lesson generator.

One script file (.txt)  ->  one 1920x1080 MP4 containing:
  1. an animated story (Mika & Alex) with Japanese / romaji / English subtitles
  2. a vocabulary section   (every word spoken + meaning + example)
  3. a grammar section      (pattern, meaning, spoken examples)
  4. a quiz                 (question, think-timer, answer)
plus a YouTube description with chapters, an .srt subtitle file and a thumbnail.

Free stack: edge-tts (neural voices), Pillow (drawn characters), ffmpeg (encode).
Same characters and look as the Tiny Japanese Reels project, but landscape.
"""
import argparse, asyncio, bisect, functools, glob, math, os, random, re, subprocess, sys, tempfile, time, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS, SR = 1920, 1080, 24, 24000
CHAR_SCALE, CHAR_Y = 0.9, 190
FLOOR_Y = 800
STAGE_OUT = 0.69   # full-body characters in the story scenes
BRAND = (222, 110, 134)
INK, SOFT, ROMA = (52, 40, 44), (90, 78, 80), (176, 110, 128)
GREEN = (60, 150, 100)
SPRITE_W, SPRITE_H = int(560 * CHAR_SCALE), int(760 * CHAR_SCALE)

CHARS = {
    "Mika": dict(voice="ja-JP-NanamiNeural", hair=(74, 45, 38), skin=(255, 224, 205), top=(244, 168, 184),
                 accent=(222, 110, 134), long_hair=True, x=150),
    "Alex": dict(voice="ja-JP-KeitaNeural", hair=(139, 98, 64), skin=(250, 214, 190), top=(142, 178, 150),
                 accent=(96, 150, 112), long_hair=False, x=W - 150 - SPRITE_W),
}
NARRATOR_VOICE = "en-US-AriaNeural"

SCENES = {
    "cafe": dict(top=(255, 246, 232), bot=(250, 228, 210), floor=(204, 160, 120), table=(228, 184, 140), edge=(176, 130, 92)),
    "station": dict(top=(196, 224, 246), bot=(236, 246, 252), floor=(150, 150, 164), table=(238, 204, 96), edge=(120, 120, 134)),
    "sakura": dict(top=(255, 228, 236), bot=(255, 246, 242), floor=(160, 204, 148), table=(176, 218, 156), edge=(120, 170, 108)),
    "restaurant": dict(top=(255, 236, 214), bot=(250, 214, 186), floor=(150, 96, 74), table=(196, 140, 104), edge=(140, 92, 66)),
    "store": dict(top=(232, 246, 255), bot=(246, 252, 255), floor=(214, 218, 226), table=(120, 196, 170), edge=(84, 150, 128)),
    "bookstore": dict(top=(246, 230, 206), bot=(238, 214, 184), floor=(166, 122, 90), table=(204, 160, 118), edge=(150, 108, 76)),
    "classroom": dict(top=(240, 248, 236), bot=(250, 252, 244), floor=(206, 176, 136), table=(226, 196, 150), edge=(176, 142, 102)),
    "home": dict(top=(255, 242, 226), bot=(252, 226, 204), floor=(196, 150, 112), table=(236, 206, 170), edge=(190, 150, 112)),
    "airport": dict(top=(204, 228, 250), bot=(240, 248, 255), floor=(178, 184, 198), table=(150, 170, 210), edge=(110, 128, 170)),
    "street": dict(top=(46, 52, 98), bot=(120, 90, 130), floor=(84, 84, 104), table=(186, 90, 90), edge=(130, 60, 66)),
    "park": dict(top=(190, 228, 252), bot=(236, 248, 238), floor=(140, 200, 120), table=(190, 152, 110), edge=(146, 112, 78)),
    "beach": dict(top=(150, 214, 244), bot=(224, 244, 252), floor=(240, 220, 170), table=(240, 130, 110), edge=(200, 96, 80)),
    "hospital": dict(top=(236, 248, 250), bot=(248, 252, 252), floor=(200, 222, 224), table=(170, 214, 216), edge=(120, 176, 180)),
}
SCENE_KEYWORDS = {
    "station": ["えき", "でんしゃ", "電車", "駅", "きっぷ", "ホーム", "バス", "station", "train", "bus stop", "ticket"],
    "airport": ["くうこう", "空港", "ひこうき", "飛行機", "パスポート", "airport", "flight", "passport", "luggage"],
    "bookstore": ["ほんや", "本屋", "しょてん", "としょかん", "図書館", "book", "library"],
    "restaurant": ["レストラン", "メニュー", "ちゅうもん", "注文", "ラーメン", "すし", "寿司", "おなか", "ごはん", "restaurant", "menu", "order", "hungry", "ramen", "sushi"],
    "cafe": ["カフェ", "コーヒー", "こうちゃ", "ケーキ", "のみもの", "cafe", "café", "coffee", "tea"],
    "store": ["スーパー", "コンビニ", "みせ", "店", "いくら", "かいもの", "買い物", "shop", "store", "buy", "how much", "price", "convenience"],
    "classroom": ["がっこう", "学校", "せんせい", "先生", "じゅぎょう", "しゅくだい", "きょうしつ", "教室", "school", "class", "teacher", "homework", "student"],
    "hospital": ["びょういん", "病院", "くすり", "いしゃ", "医者", "ねつ", "いたい", "hospital", "doctor", "medicine", "sick", "fever"],
    "home": ["いえ", "家", "うち", "へや", "部屋", "かぞく", "ただいま", "いってきます", "home", "house", "room", "family", "kitchen"],
    "beach": ["うみ", "海", "なつ", "夏", "およぐ", "ビーチ", "sea", "beach", "swim", "summer"],
    "street": ["よる", "夜", "こんばんは", "みち", "道", "まつり", "祭り", "night", "evening", "street", "festival"],
    "park": ["こうえん", "公園", "さんぽ", "てんき", "天気", "あめ", "はれ", "park", "walk", "weather", "sunny", "rain"],
    "sakura": ["さくら", "桜", "はなみ", "花見", "はる", "春", "sakura", "cherry", "blossom", "spring"],
}
SCENE_ALIASES = {"supermarket": "store", "market": "store", "shop": "store", "shopping": "store", "convenience": "store",
                 "school": "classroom", "library": "bookstore", "house": "home", "kitchen": "home", "room": "home",
                 "night": "street", "city": "street", "festival": "street", "sea": "beach", "ocean": "beach",
                 "garden": "park", "courtyard": "park", "playground": "park", "schoolyard": "park", "train": "station", "bus": "station", "clinic": "hospital", "bakery": "cafe", "coffee": "cafe"}
SCENE_ORDER = list(SCENES)


def die(msg):
    sys.exit(f"ERROR: {msg}")


# ------------------------------------------------------------------ text helpers
@functools.lru_cache(None)
def font(size, bold=True):
    w = "Bold" if bold else "Regular"
    for pat in (f"/usr/share/fonts/**/NotoSansCJK-{w}.ttc", f"/usr/share/fonts/**/NotoSansCJKjp-{w}.otf",
                "/usr/share/fonts/**/NotoSansCJK*.ttc", "/usr/share/fonts/**/*CJK*.tt*",
                "/usr/share/fonts/**/fonts-japanese-gothic.ttf", "/usr/share/fonts/**/DejaVuSans.ttf"):
        g = sorted(glob.glob(pat, recursive=True))
        if g:
            try:
                return ImageFont.truetype(g[0], size)
            except Exception:
                pass
    return ImageFont.load_default()


def wrap(text, f, maxw):
    if not text:
        return []
    sep = " " if " " in text else ""
    toks = text.split(" ") if sep else list(text)
    out, cur = [], ""
    for t in toks:
        trial = cur + sep + t if cur else t
        if f.getlength(trial) > maxw and cur:
            out.append(cur)
            cur = t
        else:
            cur = trial
    out.append(cur)
    return out


JP_RUN = re.compile(r"([぀-ヿ㐀-鿿ー〜～]+(?:[、。！？「」あ-ヿ㐀-鿿ー〜～]*))")
HAS_JP = re.compile(r"[぀-ヿ㐀-鿿]")


def to_romaji(t):
    try:
        import pykakasi
        r = pykakasi.kakasi().convert(t)
        s = " ".join(x["hepburn"] for x in r if x["hepburn"].strip())
        s = re.sub(r"\s+([!?,.。！？、])", r"\1", s)
        return s[:1].upper() + s[1:]
    except Exception:
        return ""


def fmt_time(t):
    t = int(round(t))
    return f"{t // 60}:{t % 60:02d}"


# ------------------------------------------------------------------ scenes
def resolve_scene(name):
    sc = SCENE_ALIASES.get(name.strip().lower(), name.strip().lower())
    if sc in SCENES:
        return sc
    hits = [(sc.rfind(key), val) for key, val in list(SCENE_ALIASES.items()) + [(k, k) for k in SCENES] if key in sc]
    return max(hits, key=lambda h: h[0])[1] if hits else None


def pick_scene(meta, lines):
    explicit = meta.get("scene", "auto")
    if explicit.lower() != "auto":
        sc = resolve_scene(explicit)
        if not sc:
            die(f"unknown scene '{explicit}'. Choose one of: {', '.join(SCENES)}")
        return sc
    text = (meta["title"] + " " + " ".join(l["jp"] + " " + l["en"] for l in lines)).lower()
    title = meta["title"].lower()
    best, score = None, 0
    for name, kws in SCENE_KEYWORDS.items():
        n = sum(text.count(k.lower()) + 3 * title.count(k.lower()) for k in kws)
        if n > score:
            best, score = name, n
    return best or SCENE_ORDER[sum(map(ord, meta["title"])) % len(SCENE_ORDER)]


def vgrad(w, h, a, b):
    arr = np.zeros((h, w, 3), np.uint8)
    for i in range(3):
        arr[:, :, i] = np.linspace(a[i], b[i], h)[:, None]
    return Image.fromarray(arr).convert("RGBA")


def blossoms(d, rng, box, n):
    cols = ((255, 200, 214), (255, 214, 224), (250, 184, 202))
    for _ in range(n):
        x, y, r = rng.randint(box[0], box[2]), rng.randint(box[1], box[3]), rng.randint(9, 20)
        d.ellipse((x - r, y - r, x + r, y + r), fill=rng.choice(cols))


def window(d, x, y, w, h, glass=(205, 232, 244)):
    d.rounded_rectangle((x, y, x + w, y + h), radius=30, fill=(255, 255, 255))
    d.rounded_rectangle((x + 18, y + 18, x + w - 18, y + h - 18), radius=20, fill=glass)
    d.line([(x + w // 2, y + 18), (x + w // 2, y + h - 18)], fill=(255, 255, 255), width=10)
    d.line([(x + 18, y + h // 2), (x + w - 18, y + h // 2)], fill=(255, 255, 255), width=10)


def sign(d, cx, y, w, h, text, fill, fg=(255, 255, 255), size=54):
    d.rounded_rectangle((cx - w // 2, y, cx + w // 2, y + h), radius=22, fill=fill)
    d.text((cx, y + h // 2), text, font=font(size), fill=fg, anchor="mm")


def shelves(d, rng, x0, x1, ys, base=(150, 104, 72), books=True):
    d.rectangle((x0, ys[0] - 10, x1, ys[-1] + 175), fill=base)
    pal = [(210, 100, 96), (96, 150, 200), (230, 190, 96), (110, 170, 130), (170, 120, 190), (240, 230, 214)]
    for y in ys:
        d.rectangle((x0 + 10, y + 150, x1 - 10, y + 170), fill=tuple(int(v * 0.78) for v in base))
        x = x0 + 20
        while x < x1 - 70:
            w = rng.randint(34, 62); hh = rng.randint(90, 140)
            d.rectangle((x, y + 150 - hh, x + w, y + 150), fill=rng.choice(pal)); x += w + 4


def make_scene(scene):
    """Return (background RGB, foreground table strip RGBA) for a scene, 1920x1080."""
    sc = SCENES[scene]; rng = random.Random(7)
    bg = vgrad(W, H, sc["top"], sc["bot"]); d = ImageDraw.Draw(bg)
    if scene == "classroom":
        d.rounded_rectangle((470, 170, 1450, 650), radius=22, fill=(150, 112, 78)); d.rounded_rectangle((492, 192, 1428, 628), radius=12, fill=(52, 98, 80))
        d.text((960, 330), "にほんご", font=font(130), fill=(244, 244, 236), anchor="mm"); d.text((960, 520), "あ い う え お", font=font(90), fill=(244, 230, 140), anchor="mm")
        d.ellipse((1500, 200, 1620, 320), fill=(250, 250, 250), outline=(60, 60, 70), width=8); d.line([(1560, 260), (1560, 220)], fill=(60, 60, 70), width=7); d.line([(1560, 260), (1592, 276)], fill=(60, 60, 70), width=7)
    elif scene == "cafe":
        window(d, 640, 150, 640, 520)
        blossoms(d, rng, (680, 190, 1240, 420), 26)
        for x in (330, 1590):
            d.line([(x, 0), (x, 200)], fill=(120, 90, 80), width=7); d.pieslice((x - 70, 180, x + 70, 320), 180, 360, fill=(240, 170, 120))
    elif scene == "station":
        for x in range(-40, W, 170):
            hh = rng.randint(220, 440); d.rectangle((x, FLOOR_Y - hh, x + 150, FLOOR_Y), fill=(206, 218, 234))
        sign(d, 960, 160, 560, 130, "えき  Station", (60, 80, 120), size=66)
    elif scene == "sakura":
        d.line([(0, 250), (500, 210), (1000, 280), (1920, 170)], fill=(122, 84, 72), width=26)
        blossoms(d, rng, (0, 100, W, 460), 260); blossoms(d, rng, (0, 460, W, 780), 60)
    elif scene == "restaurant":
        for x in (330, 960, 1590):
            d.line([(x, 0), (x, 220)], fill=(120, 90, 80), width=6); d.ellipse((x - 70, 200, x + 70, 280), fill=(255, 214, 120))
        sign(d, 960, 330, 1100, 190, "らーめん  ・  すし  ・  どん", (110, 70, 56), (255, 236, 200), 70)
        for x in range(500, 1440, 130):
            d.rounded_rectangle((x, 600, x + 80, 770), radius=14, fill=(214, 70, 70))
    elif scene == "store":
        sign(d, 960, 180, 1200, 90, "コンビニ  OPEN 24h", (52, 160, 120), size=50)
        cols = [(250, 120, 110), (250, 200, 90), (110, 190, 240), (140, 210, 150), (200, 150, 230)]
        for row, y in enumerate((310, 470, 630)):
            d.rectangle((300, y + 70, W - 300, y + 86), fill=(150, 150, 164))
            for k, x in enumerate(range(320, W - 380, 76)):
                hh = 46 + (k * 7 + row * 5) % 32
                d.rounded_rectangle((x, y + 70 - hh, x + 56, y + 70), radius=8, fill=cols[(k * 3 + row) % 5])
    elif scene == "bookstore":
        shelves(d, rng, 420, 1500, (190, 370, 550))
    elif scene == "home":
        window(d, 330, 170, 460, 460)
        d.rounded_rectangle((1080, 210, 1560, 440), radius=18, fill=(255, 240, 220), outline=(190, 150, 112), width=9)
        d.ellipse((1160, 250, 1280, 390), fill=(255, 200, 150)); d.polygon([(1340, 400), (1430, 280), (1520, 400)], fill=(150, 200, 140))
        d.rounded_rectangle((840, 560, 1240, 780), radius=40, fill=(224, 140, 140))
    elif scene == "airport":
        d.rectangle((0, 150, W, 780), fill=(176, 212, 244)); d.polygon([(0, 780), (W, 560), (W, 780)], fill=(160, 200, 236))
        d.polygon([(700, 470), (1160, 440), (1230, 390), (1270, 400), (1220, 470), (1350, 490), (1340, 515), (710, 515)], fill=(250, 250, 255))
        sign(d, 960, 170, 1100, 110, "くうこう  Airport", (40, 52, 80), (250, 220, 110), 62)
    elif scene == "street":
        d.ellipse((1450, 120, 1600, 270), fill=(255, 244, 200))
        for _ in range(110):
            x, y = rng.randint(0, W), rng.randint(0, 420); d.ellipse((x, y, x + 5, y + 5), fill=(255, 255, 255))
        for x in range(-30, W, 190):
            hh = rng.randint(300, 560); d.rectangle((x, FLOOR_Y - hh, x + 170, FLOOR_Y), fill=(36, 40, 72))
            for wy in range(FLOOR_Y - hh + 26, FLOOR_Y - 40, 58):
                for wx in (x + 24, x + 92):
                    if rng.random() < 0.65: d.rectangle((wx, wy, wx + 38, wy + 32), fill=(255, 218, 120))
        for x in (300, 700, 1100, 1500):
            d.line([(x, 500), (x, 570)], fill=(120, 80, 70), width=4); d.ellipse((x - 46, 560, x + 46, 690), fill=(236, 80, 70))
    elif scene == "park":
        d.ellipse((260, 150, 460, 350), fill=(250, 232, 140))
        for x in (1380, 1600):
            d.rectangle((x - 20, 440, x + 20, 790), fill=(122, 88, 66)); d.ellipse((x - 170, 190, x + 170, 540), fill=(96, 176, 108)); d.ellipse((x - 100, 230, x + 50, 360), fill=(120, 196, 128))
        for cx, cy in ((760, 260), (1020, 200), (1160, 330)):
            d.ellipse((cx - 80, cy - 34, cx + 80, cy + 34), fill=(255, 255, 255)); d.ellipse((cx - 34, cy - 62, cx + 56, cy + 12), fill=(255, 255, 255))
    elif scene == "beach":
        d.ellipse((1400, 140, 1560, 300), fill=(255, 226, 120)); d.rectangle((0, 420, W, FLOOR_Y), fill=(70, 170, 220))
        for y in range(470, 780, 60):
            for x in range(-40, W, 150):
                d.arc((x + (y % 120), y, x + 110 + (y % 120), y + 44), 200, 340, fill=(220, 244, 255), width=6)
        d.rectangle((560, 470, 572, 780), fill=(150, 110, 80)); d.pieslice((440, 360, 700, 580), 180, 360, fill=(240, 100, 90))
    elif scene == "hospital":
        sign(d, 960, 170, 1100, 110, "びょういん  Hospital", (90, 170, 180), size=62)
        d.rectangle((900, 330, 1020, 370), fill=(236, 86, 96)); d.rectangle((940, 290, 980, 410), fill=(236, 86, 96))
        for x in (420, 1300):
            d.rounded_rectangle((x, 520, x + 200, 760), radius=12, fill=(250, 250, 252), outline=(160, 200, 206), width=7)
    d.rectangle((0, FLOOR_Y, W, H), fill=sc["floor"])
    for y in range(FLOOR_Y + 70, H, 74):
        d.line([(0, y), (W, y)], fill=tuple(int(v * 0.93) for v in sc["floor"]), width=3)
    fg = Image.new("RGBA", (W, 130), (0, 0, 0, 0)); g = ImageDraw.Draw(fg)
    g.rectangle((0, 40, W, 92), fill=sc["table"]); g.rectangle((0, 92, W, 130), fill=sc["edge"])
    if scene in ("cafe", "restaurant"):
        for x in (330, 1500):
            g.rounded_rectangle((x, 4, x + 84, 46), radius=14, fill=(255, 255, 255)); g.ellipse((x + 70, 12, x + 108, 38), outline=(255, 255, 255), width=8)
    return bg.convert("RGB"), fg


def header(img, meta):
    d = ImageDraw.Draw(img, "RGBA")
    ep = f"Ep.{meta['episode']}  ·  " if meta.get("episode") else ""
    size = 52
    while size > 30 and font(size).getlength(ep + meta["title"]) > 1000:
        size -= 2
    w = int(max(font(size).getlength(ep + meta["title"]), 330)) + 90
    d.rounded_rectangle((44, 34, 44 + w, 156), radius=52, fill=(255, 255, 255, 238))
    d.text((84, 52), "TINY JAPANESE", font=font(30), fill=BRAND)
    d.text((84, 92), ep + meta["title"], font=font(size), fill=(60, 45, 48))


def slide_bg(meta):
    bg = vgrad(W, H, (255, 244, 234), (252, 228, 228)).convert("RGB"); d = ImageDraw.Draw(bg)
    rng = random.Random(3)
    blossoms(d, rng, (0, 0, W, 170), 14); blossoms(d, rng, (1250, 0, W, 400), 26)
    d.rectangle((0, 1000, W, H), fill=(240, 214, 200))
    header(bg, meta)
    return bg


# ------------------------------------------------------------------ characters
@functools.lru_cache(None)
def sprite(name, mouth, blink, out=1.0, full=False):
    """full=True adds the lower body (skirt/trousers, legs, shoes); the default crops it off (hidden behind the table)."""
    c, S = CHARS[name], 2 * CHAR_SCALE
    w, h = int(560 * S), int(960 * S)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    P = lambda *v: [int(x * S) for x in v]
    ell = lambda box, fill: d.ellipse(P(*box), fill=fill)
    ink, hair, skin, top, acc = (70, 45, 48), c["hair"], c["skin"], c["top"], c["accent"]
    if c["long_hair"]:
        d.rounded_rectangle(P(110, 170, 450, 590), radius=int(110 * S), fill=hair)
    shoe = (96, 66, 60)
    if c["long_hair"]:   # skirt, legs, socks, shoes
        for x0 in (214, 306):
            d.rounded_rectangle(P(x0, 780, x0 + 42, 905), radius=int(16 * S), fill=skin)
            d.rounded_rectangle(P(x0 - 2, 862, x0 + 44, 912), radius=int(14 * S), fill=(250, 248, 246))
            ell((x0 - 14, 896, x0 + 62, 940), shoe)
        d.polygon(P(178, 640, 382, 640, 414, 805, 146, 805), fill=(122, 132, 196))
        for x in range(170, 400, 46):
            d.line(P(x, 700, x - (280 - x) * 0.08, 800), fill=(104, 114, 178), width=int(5 * S))
    else:                # trousers, shoes
        for x0 in (198, 292):
            d.rounded_rectangle(P(x0, 640, x0 + 72, 890), radius=int(26 * S), fill=(96, 112, 150))
            ell((x0 - 10, 876, x0 + 84, 926), shoe)
        d.rounded_rectangle(P(190, 628, 370, 700), radius=int(26 * S), fill=(96, 112, 150))
    d.rounded_rectangle(P(185, 450, 375, 690), radius=int(60 * S), fill=top)
    d.polygon(P(245, 452, 280, 505, 315, 452), fill=skin)
    ell((140, 500, 210, 650), top); ell((350, 500, 420, 650), top)
    ell((148, 625, 205, 675), skin); ell((355, 625, 412, 675), skin)
    ell((125, 145, 435, 455), skin)
    d.pieslice(P(118, 136, 442, 460), 180, 360, fill=hair)
    if c["long_hair"]:
        for x in range(150, 420, 48):
            ell((x - 34, 225, x + 34, 300 + (12 if (x // 48) % 2 else 0)), hair)
        ell((112, 280, 168, 520), hair); ell((392, 280, 448, 520), hair)
        ell((340, 165, 392, 215), acc); ell((355, 180, 377, 200), (255, 240, 200))
    else:
        for x in range(135, 420, 58):
            d.polygon(P(x, 225, x + 58, 225, x + 29, 305), fill=hair)
        d.polygon(P(262, 120, 300, 120, 282, 165), fill=hair)
    for ex in (222, 338):
        if blink:
            d.arc(P(ex - 26, 335, ex + 26, 375), 200, 340, fill=ink, width=int(6 * S))
        else:
            ell((ex - 24, 318, ex + 24, 382), (55, 35, 42))
            ell((ex - 15, 330, ex + 3, 350), (255, 255, 255)); ell((ex + 6, 358, ex + 16, 368), (255, 255, 255))
    ell((168, 388, 215, 412), (250, 172, 170)); ell((345, 388, 392, 412), (250, 172, 170))
    if mouth == 0:
        d.arc(P(262, 400, 298, 430), 20, 160, fill=ink, width=int(5 * S))
    elif mouth == 1:
        ell((268, 408, 292, 430), (120, 40, 52))
    else:
        ell((258, 405, 302, 442), (120, 40, 52)); ell((266, 424, 294, 440), (236, 120, 132))
    if not full:
        im = im.crop((0, 0, w, int(760 * S)))
        return im.resize((int(SPRITE_W * out), int(SPRITE_H * out)), Image.LANCZOS)
    return im.resize((int(SPRITE_W * out), int(SPRITE_H * out * 960 / 760)), Image.LANCZOS)


@functools.lru_cache(None)
def pill(text, fill, fg=(255, 255, 255), size=32):
    f = font(size); tw = int(f.getlength(text)) + 56; h = int(size * 1.8)
    im = Image.new("RGBA", (tw, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, tw - 1, h - 1), radius=h // 2, fill=fill)
    d.text((tw / 2, h / 2), text, font=f, fill=fg, anchor="mm")
    return im


# ------------------------------------------------------------------ cards
def card(tag, tag_color, blocks, cw=1500, min_h=0):
    """blocks: (text, size, bold, color, gap_after). Returns RGBA card with soft shadow (40px margin)."""
    pad = 52
    rows = []
    for text, size, bold, color, gap in blocks:
        f = font(size, bold)
        ls = wrap(text, f, cw - 2 * pad)
        for k, ln in enumerate(ls):
            rows.append((ln, f, color, int(size * 1.3) + (gap if k == len(ls) - 1 else 0)))
    body = sum(r[3] for r in rows)
    h = max(min_h, body + 110)
    size = (cw + 80, h + 80)
    m = Image.new("L", size, 0); ImageDraw.Draw(m).rounded_rectangle((40, 52, 40 + cw, 52 + h), radius=56, fill=90)
    sh_ = Image.new("RGBA", size, (120, 80, 70, 0)); sh_.putalpha(m.filter(ImageFilter.GaussianBlur(16)))
    img = Image.alpha_composite(Image.new("RGBA", size, (0, 0, 0, 0)), sh_)
    d = ImageDraw.Draw(img); d.rounded_rectangle((40, 40, 40 + cw, 40 + h), radius=56, fill=(255, 253, 250, 245))
    y = 40 + 58 + (h - 58 - 30 - body) / 2
    for text, f, color, adv in rows:
        d.text((40 + cw / 2, y), text, font=f, fill=color, anchor="ma")
        y += adv
    p = pill(tag, tag_color); img.paste(p, (84, 40 - p.height // 2), p)
    return img


def sub_blocks(jp, romaji, en, jp_size=66, ro_size=38, en_size=44):
    b = [(jp, jp_size, True, INK, 8)]
    if romaji:
        b.append((romaji, ro_size, False, ROMA, 6))
    if en:
        b.append((en, en_size, False, SOFT, 0))
    return b


def story_card(ln):
    return card(ln.get("tag", ln["speaker"]), CHARS[ln["speaker"]]["accent"], sub_blocks(ln["jp"], ln["romaji"], ln["en"]), cw=1560, min_h=250)


def example_blocks(ex, big=False):
    return sub_blocks(ex["jp"], ex["romaji"], ex["en"], 52 if not big else 60, 30, 36)


# ------------------------------------------------------------------ script parsing
SECTIONS = ("story", "vocab", "grammar", "quiz", "ending")


def norm_line(raw):
    """Tidy a script line: drop markdown marks, accept 【story】 / **[story]** / bare 'Story:' as section headers."""
    s = raw.strip().replace("【", "[").replace("】", "]").replace("［", "[").replace("］", "]")
    s = s.strip("*_ \t").strip()
    m = re.match(r"^(hook|story|vocab|vocabulary|grammar|quiz|ending|practice|learning tip|tip|outro|intro)\s*:?$", s, re.I)
    return f"[{m[1]}]" if m else s


DIALOGUE = re.compile(r"^(mika|alex|both)(\s+(?:and|&)\s+(?:mika|alex))?\s*[:：]", re.I)

_ROMAJI = re.compile(r"(?:(?:[kgszjtdnhbpmr]y?|sh|ch|ts|f|w|y)?[aiueo]|n(?![aiueoy])|(?:kk|ss|tt|pp)(?=[aiueo]))+")


def _norm(t):
    return re.sub(r"[^a-z]", "", t.lower())


def _romaji_like(t):
    n = _norm(t)
    return bool(n) and bool(_ROMAJI.fullmatch(n))


def split_rom_en(jp, a, b):
    """Given the two extra parts of 'jp | x | y', decide which is romaji and which is English (either order works)."""
    ra = to_romaji(jp)
    if ra:
        import difflib
        sa = difflib.SequenceMatcher(None, _norm(ra), _norm(a)).ratio()
        sb = difflib.SequenceMatcher(None, _norm(ra), _norm(b)).ratio()
        if abs(sa - sb) > 0.08:
            return (a, b) if sa > sb else (b, a)
    la, lb = _romaji_like(a), _romaji_like(b)
    if la != lb:
        return (a, b) if la else (b, a)
    return a, b          # ambiguous: romaji first, English second


def meaning_of(a, b):
    """For 'pattern | x | y' pick the English explanation (the part that is not romaji)."""
    la, lb = _romaji_like(a), _romaji_like(b)
    if la and not lb:
        return b
    if lb and not la:
        return a
    return b


def example_dict(p):
    if len(p) > 2 and p[1] and p[2]:
        rom, en = split_rom_en(p[0], p[1], p[2])
    else:
        rom, en = (to_romaji(p[0]), p[1] if len(p) > 1 else "")
    return dict(jp=p[0], en=en, romaji=rom or to_romaji(p[0]))


def parse_script(path):
    meta = dict(title="Tiny Lesson", episode="", scene="auto")
    story, vocab, grammar, quiz, ending = [], [], [], [], []
    sec, cur = None, None
    pending_scene = None
    for n, raw in enumerate(open(path, encoding="utf-8"), 1):
        s = norm_line(raw)
        if not s or s.startswith("#"):
            continue
        m = re.match(r"^\[([^\]]+)\]$", s)
        if m:
            sec = m[1].strip().lower()
            if sec == "vocabulary":
                sec = "vocab"
            if sec not in SECTIONS:
                sec = "story"        # any other heading ([learning tip], [practice], ...) holds more dialogue
            cur = None
            continue
        if sec is None and DIALOGUE.match(s):
            sec = "story"
        if sec is None:
            m = re.match(r"^(title|episode|scene)\s*:\s*(.+)$", s, re.I)
            if not m:
                die(f"line {n}: put title/episode/scene first, then a [story] section: {s}")
            meta[m[1].lower()] = m[2].strip()
            continue
        if sec in ("story", "ending"):
            m = re.match(r"^@scene\s+(.+)$", s, re.I)
            if m:
                sc = resolve_scene(m[1])
                if not sc:
                    die(f"line {n}: unknown scene '{m[1]}'. Choose one of: {', '.join(SCENES)}")
                pending_scene = sc
                continue
            m = re.match(r"^([A-Za-z]+(?:\s+(?:and|&)\s+[A-Za-z]+)?)\s*[:：]\s*(.+)$", s)
            who = m[1].strip().capitalize() if m else ""
            tag = None
            if m and (re.search(r"\s(and|&)\s", m[1]) or who == "Both"):
                who, tag = "Mika", "Mika & Alex"
            if not m or who not in CHARS:
                die(f"line {n}: story lines look like 'Mika: こんにちは | Hello' (speakers: {', '.join(CHARS)})")
            p = [x.strip() for x in m[2].split("|")]
            ex = example_dict(p)
            ln = dict(speaker=who, jp=ex["jp"], en=ex["en"], romaji=ex["romaji"], scene=pending_scene)
            if tag:
                ln["tag"] = tag
            (story if sec == "story" else ending).append(ln)
            pending_scene = None
        elif sec == "vocab":
            m = re.match(r"^(vocab|example)\s*:\s*(.+)$", s, re.I)
            if not m:
                die(f"line {n}: use 'vocab: word | meaning' (optional: | romaji) and 'example: 日本語 | English'")
            p = [x.strip() for x in m[2].split("|")]
            if m[1].lower() == "vocab":
                if len(p) < 2:
                    die(f"line {n}: vocab needs 'word | meaning'")
                ex = example_dict(p)
                cur = dict(jp=ex["jp"], en=ex["en"], romaji=ex["romaji"], examples=[])
                vocab.append(cur)
            else:
                if cur is None:
                    die(f"line {n}: 'example:' must come right after a 'vocab:' line")
                cur["examples"].append(example_dict(p))
        elif sec == "grammar":
            m = re.match(r"^(grammar|example)\s*:\s*(.+)$", s, re.I)
            if not m:
                die(f"line {n}: use 'grammar: pattern | meaning' then 'example: 日本語 | English' lines")
            p = [x.strip() for x in m[2].split("|")]
            if m[1].lower() == "grammar":
                if len(p) < 2:
                    die(f"line {n}: grammar needs 'pattern | meaning'")
                cur = dict(pattern=p[0], meaning=meaning_of(p[1], p[2]) if len(p) > 2 and p[2] else p[1], examples=[])
                grammar.append(cur)
            else:
                if cur is None:
                    die(f"line {n}: 'example:' must come right after a 'grammar:' line")
                cur["examples"].append(example_dict(p))
        elif sec == "quiz":
            m = re.match(r"^quiz\s*:\s*(.+)$", s, re.I)
            if not m:
                die(f"line {n}: use 'quiz: question | option | option | option | B | optional explanation'")
            p = [x.strip() for x in m[1].split("|")]
            ai = next((k for k in range(2, len(p)) if re.fullmatch(r"[A-Da-d]", p[k])), None)
            if ai is None or not 3 <= ai <= 5:
                die(f"line {n}: a quiz needs a question, 2-4 options, then the answer letter (A-D)")
            opts = p[1:ai]
            ans = ord(p[ai].upper()) - 65
            if ans >= len(opts):
                die(f"line {n}: answer {p[ai]} but only {len(opts)} options")
            quiz.append(dict(q=p[0], opts=opts, ans=ans, why=p[ai + 1] if len(p) > ai + 1 else ""))
    if not story:
        die("no [story] dialogue found.")
    meta["scene0"] = pick_scene(meta, story)
    sc = meta["scene0"]
    for ln in story:
        sc = ln["scene"] or sc
        ln["scene"] = sc
    for ln in ending:
        sc = ln["scene"] or sc
        ln["scene"] = sc
    meta["ending"] = ending
    return meta, story, vocab, grammar, quiz


# ------------------------------------------------------------------ audio
def write_wav(path, x):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def read_wav(path):
    with wave.open(path) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768


def sh(cmd):
    subprocess.run(cmd, check=True)


FALLBACK_USED = False


def synth(text, who, out_wav, rate, dummy=False):
    if dummy:
        n = int(max(0.8, len(text) * 0.09) * SR); t = np.arange(n) / SR
        write_wav(out_wav, 0.4 * np.sin(2 * np.pi * (220 if who != "Narrator" else 170) * t) * np.abs(np.sin(2 * np.pi * 3.5 * t)) ** 0.7)
        return
    global FALLBACK_USED
    jp = who in CHARS
    voice = CHARS[who]["voice"] if jp else NARRATOR_VOICE
    lang = "ja" if jp else "en"
    mp3, af, ok, last = out_wav + ".mp3", [], False, None
    for attempt in range(1, 6):
        try:
            import edge_tts
            asyncio.run(edge_tts.Communicate(text, voice, rate=rate).save(mp3))
            ok = True
            break
        except Exception as e:
            last = e
            print(f"edge-tts attempt {attempt}/5 failed ({e})", file=sys.stderr)
            if attempt < 5:
                time.sleep(4 * attempt)
    if not ok:
        if os.environ.get("STRICT_VOICE") == "1":
            sys.exit("::error::The natural (edge-tts) voice is unavailable right now. Re-run in a little while.")
        FALLBACK_USED = True
        print(f"::warning::edge-tts unavailable ({last}); using the lower-quality gTTS fallback voice", file=sys.stderr)
        from gtts import gTTS
        gTTS(text, lang=lang).save(mp3)
        if who == "Alex":
            af = ["-af", f"asetrate={int(SR * 0.86)},aresample={SR}"]
    sh(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, *af, "-ar", str(SR), "-ac", "1", out_wav])


class Track:
    """Builds the soundtrack and remembers who is talking when (for lip sync)."""

    def __init__(self, tmp, rate, dummy):
        self.tmp, self.rate, self.dummy = tmp, rate, dummy
        self.chunks, self.t, self.talk, self.k = [], 0.0, [], 0

    def gap(self, sec):
        self.chunks.append(np.zeros(int(sec * SR), np.float32)); self.t += int(sec * SR) / SR

    def say(self, text, who, rate=None):
        text = text.replace("___", " blank ").strip()
        if not text:
            return self.t, self.t
        self.k += 1
        wav = os.path.join(self.tmp, f"a{self.k}.wav")
        synth(text, who, wav, rate or ("+0%" if who == "Narrator" else self.rate), self.dummy)
        x = read_wav(wav); a = self.t
        self.chunks.append(x); self.t += len(x) / SR
        if who in CHARS:
            self.talk.append((who, a, self.t))
        return a, self.t

    def mixed(self, text, jp_rate="-15%", jp_who="Mika"):
        """English parts by the narrator, Japanese parts by a character."""
        a = self.t
        for run in JP_RUN.split(text):
            if not run.strip() or not re.search(r"[A-Za-z぀-ヿ㐀-鿿]", run):
                continue
            if HAS_JP.search(run):
                self.say(run, jp_who, jp_rate)
            else:
                self.say(run, "Narrator")
            self.gap(0.12)
        return a, self.t

    def audio(self, total):
        self.chunks.append(np.zeros(int((total - self.t) * SR) + SR, np.float32))
        x = np.concatenate(self.chunks)
        return x / max(0.01, np.abs(x).max()) * 0.9


def mouth_levels(audio, n):
    spf = SR / FPS
    rms = np.array([np.sqrt(np.mean(audio[int(i * spf):int((i + 1) * spf)] ** 2) + 1e-12)
                    if int(i * spf) < len(audio) else 0 for i in range(n)])
    ref = np.percentile(rms[rms > 1e-3], 90) if (rms > 1e-3).any() else 1
    lv = np.clip(rms / ref, 0, 1.2)
    sm = lv.copy(); sm[1:-1] = 0.5 * lv[1:-1] + 0.25 * (lv[:-2] + lv[2:])
    return np.where(sm < 0.15, 0, np.where(sm < 0.55, 1, 2))


# ------------------------------------------------------------------ timeline
def build(path, rate, dummy, tmp):
    meta, story, vocab, grammar, quiz = parse_script(path)
    tr = Track(tmp, rate, dummy)
    segs, chapters = [], []

    def mark(kind, start, **kw):
        segs.append(dict(kind=kind, start=start, **kw))

    # intro
    chapters.append((0.0, "Intro"))
    tr.gap(0.4)
    mark("title", 0.0, scene=story[0]["scene"])
    tr.say(f"Welcome to Tiny Japanese! Today's story: {meta['title']}. Watch the story first, "
           f"then we'll learn the words and grammar, and finish with a quiz.", "Narrator")
    tr.gap(0.8)

    # story
    chapters.append((tr.t, "Story"))
    prev = story[0]["scene"]
    for ln in story:
        a, b = tr.say(ln["jp"], ln["speaker"]); ln.update(start=a, end=b)
        mark("story", a - 0.02, line=ln, scene=ln["scene"], prev_scene=prev)
        prev = ln["scene"]
        tr.gap(0.6)
    tr.gap(0.4)

    def section(kind, title, sub, say):
        chapters.append((tr.t, title))
        mark("section", tr.t, title=title, sub=sub)
        tr.say(say, "Narrator"); tr.gap(0.5)

    # vocabulary
    if vocab:
        section("vocab", "Vocabulary", "Key words from the story", "Now, let's learn the key words from the story.")
        for i, v in enumerate(vocab):
            mark("vocab", tr.t, v=v, i=i, n=len(vocab), shown=0)
            tr.say(v["jp"], "Mika", "-25%"); tr.gap(0.4)
            tr.say(v["en"].replace("~", "something"), "Narrator"); tr.gap(0.4)
            tr.say(v["jp"], "Mika", "-25%"); tr.gap(0.7)
            for k, ex in enumerate(v["examples"]):
                mark("vocab", tr.t, v=v, i=i, n=len(vocab), shown=k + 1)
                tr.say(ex["jp"], "Mika", "-15%"); tr.gap(0.9)
            tr.gap(0.5)

    # grammar
    if grammar:
        section("grammar", "Grammar", "How the sentences work", "Now, let's look at the grammar.")
        for i, g in enumerate(grammar):
            mark("grammar", tr.t, g=g, i=i, n=len(grammar), shown=0)
            tr.mixed(g["meaning"] + ".", "-25%"); tr.gap(0.8)
            for k, ex in enumerate(g["examples"]):
                mark("grammar", tr.t, g=g, i=i, n=len(grammar), shown=k + 1)
                tr.say(ex["jp"], "Mika", "-15%"); tr.gap(0.5)
                tr.say(ex["en"], "Narrator"); tr.gap(0.9)
            tr.gap(0.5)

    # quiz
    if quiz:
        section("quiz", "Quiz", "Test yourself!", "Time for a quiz! Pick the best answer before the timer runs out.")
        for i, q in enumerate(quiz):
            mark("quiz", tr.t, q=q, i=i, n=len(quiz), phase="ask")
            tr.say(f"Question {i + 1}.", "Narrator"); tr.gap(0.2)
            tr.mixed(q["q"]); tr.gap(0.4)
            for k, o in enumerate(q["opts"]):
                tr.say("ABCD"[k], "Narrator"); tr.gap(0.1)
                tr.mixed(o); tr.gap(0.4)
            think = 5
            mark("quiz", tr.t, q=q, i=i, n=len(quiz), phase="think", t0=tr.t)
            tr.gap(think)
            mark("quiz", tr.t, q=q, i=i, n=len(quiz), phase="answer")
            tr.say(f"The answer is {'ABCD'[q['ans']]}.", "Narrator"); tr.gap(0.2)
            tr.mixed(q["opts"][q["ans"]]); tr.gap(0.5)
            if q["why"]:
                tr.mixed(q["why"]); tr.gap(0.5)
            tr.gap(0.8)

    # ending (optional [ending] section: closing lines by Mika & Alex)
    ending = meta.get("ending") or []
    if ending:
        prev = story[-1]["scene"]
        for ln in ending:
            a, b = tr.say(ln["jp"], ln["speaker"]); ln.update(start=a, end=b)
            mark("story", a - 0.02, line=ln, scene=ln["scene"], prev_scene=prev)
            prev = ln["scene"]
            tr.gap(0.6)
        tr.gap(0.4)

    # outro
    chapters.append((tr.t, "Wrap-up"))
    mark("outro", tr.t, scene=story[-1]["scene"])
    tr.say("Great job! Watch the story again and repeat each line out loud. See you next time!", "Narrator")
    total = tr.t + 1.5
    audio = tr.audio(total)
    n = int(total * FPS)
    mouth = mouth_levels(audio, n)
    spk = [None] * n
    for who, a, b in tr.talk:
        for i in range(max(0, int(a * FPS) - 1), min(n, int(b * FPS) + 2)):
            spk[i] = who
    return dict(meta=meta, story=story, vocab=vocab, grammar=grammar, quiz=quiz, segs=segs, chapters=chapters,
                audio=audio, n=n, total=total, mouth=mouth, spk=spk)


# ------------------------------------------------------------------ rendering
class Renderer:
    def __init__(self, B):
        self.B, self.meta = B, B["meta"]
        self.starts = [s["start"] for s in B["segs"]]
        self.scenes, self.cards = {}, {}
        self.slide_base = slide_bg(self.meta)
        self.pills = {(nm, a): pill(nm, CHARS[nm]["accent"] if a else (226, 214, 206), (255, 255, 255) if a else (130, 112, 108))
                      for nm in CHARS for a in (0, 1)}

    def scene(self, name):
        if name not in self.scenes:
            bg, fg = make_scene(name); header(bg, self.meta); self.scenes[name] = (bg, fg)
        return self.scenes[name]

    def cached(self, key, fn):
        if key not in self.cards:
            self.cards[key] = fn()
        return self.cards[key]

    def seg_at(self, tt):
        return self.B["segs"][max(0, bisect.bisect_right(self.starts, tt) - 1)]

    def character(self, fr, nm, i, tt, speaking, mouth, x, y, scale_pill=True, full=False, out=1.0):
        bob = 6 * abs(math.sin(tt * 7)) if speaking and mouth else 2 * math.sin(tt * 2 + (0 if nm == "Mika" else 1.7))
        blink = ((i + (0 if nm == "Mika" else 41)) % 72) < 3
        s = sprite(nm, int(mouth) if speaking else 0, blink, out, full)
        fr.paste(s, (x, int(y - bob)), s)
        return s

    def fade(self, fr, cardimg, x, y, f):
        if f < 1:
            cardimg = cardimg.copy(); cardimg.putalpha(cardimg.getchannel("A").point(lambda v: int(v * f)))
        fr.paste(cardimg, (x, y), cardimg)

    # ---- stage (story / title / outro)
    def stage(self, seg, i, tt, who, mouth):
        name = seg.get("scene")
        bg, fg = self.scene(name)
        fr = bg.copy()
        if seg["kind"] == "story" and seg["prev_scene"] != name and tt - seg["start"] < 0.5:
            fr = Image.blend(self.scene(seg["prev_scene"])[0], bg, min(1, (tt - seg["start"]) / 0.5))
        for nm, c in CHARS.items():
            cx = c["x"] + SPRITE_W // 2
            fs = sprite(nm, 0, False, STAGE_OUT, True)
            x, y = cx - fs.width // 2, FLOOR_Y - 50 - fs.height
            self.character(fr, nm, i, tt, who == nm, mouth, x, y, full=True, out=STAGE_OUT)
            p = self.pills[(nm, int(who == nm))]
            fr.paste(p, (cx - p.width // 2, y + 36), p)
        fr.paste(fg, (0, FLOOR_Y - 40), fg)
        if seg["kind"] == "story":
            ln = seg["line"]
            cd = self.cached(("story", id(ln)), lambda: story_card(ln))
            self.fade(fr, cd, (W - cd.width) // 2, H - cd.height - 10, min(1, (tt - seg["start"]) / 0.2))
        elif seg["kind"] == "title":
            cd = self.cached("title", lambda: card("Today's lesson", BRAND, [
                (self.meta["title"], 84, True, INK, 14),
                ("Story  ·  Vocabulary  ·  Grammar  ·  Quiz", 40, False, SOFT, 0)], cw=1400, min_h=300))
            self.fade(fr, cd, (W - cd.width) // 2, H - cd.height - 10, min(1, tt / 0.4))
        else:
            cd = self.cached("outro", lambda: card("Thanks for watching", BRAND, [
                ("Watch again and repeat out loud!", 70, True, INK, 14),
                ("また つぎ！ (mata tsugi) – see you next time", 40, False, SOFT, 0)], cw=1400, min_h=300))
            self.fade(fr, cd, (W - cd.width) // 2, H - cd.height - 10, min(1, (tt - seg["start"]) / 0.4))
        return fr

    # ---- slides (section / vocab / grammar / quiz)
    def slide_card(self, seg):
        k = seg["kind"]
        if k == "section":
            return card("Next up", BRAND, [(seg["title"], 110, True, INK, 18), (seg["sub"], 48, False, SOFT, 0)], cw=1150, min_h=420)
        if k == "vocab":
            v = seg["v"]
            b = [(v["jp"], 120, True, INK, 8), (v["romaji"], 52, False, ROMA, 6), (v["en"], 64, False, SOFT, 18)]
            for ex in v["examples"][:seg["shown"]]:
                b += example_blocks(ex)
            return card(f"Word {seg['i'] + 1}/{seg['n']}", BRAND, b, cw=1150, min_h=520)
        if k == "grammar":
            g = seg["g"]
            b = [(g["pattern"], 84, True, INK, 8), (g["meaning"], 50, False, SOFT, 18)]
            for ex in g["examples"][:seg["shown"]]:
                b += example_blocks(ex)
            return card(f"Grammar {seg['i'] + 1}/{seg['n']}", BRAND, b, cw=1150, min_h=520)
        q, ph = seg["q"], seg["phase"]
        b = [(q["q"], 54, True, INK, 24)]
        for j, o in enumerate(q["opts"]):
            ro = to_romaji(o) if HAS_JP.search(o) else ""
            label = f"{'ABCD'[j]}.  {o}" + (f"   ({ro})" if ro else "")
            if ph == "answer":
                col = GREEN if j == q["ans"] else (170, 156, 162)
                if j == q["ans"]:
                    label += "   ← correct!"
            else:
                col = INK
            b.append((label, 50, ph != "answer" or j == q["ans"], col, 10))
        if ph == "answer" and q["why"]:
            b.append((q["why"], 38, False, SOFT, 0))
        return card(f"Quiz {seg['i'] + 1}/{seg['n']}", BRAND, b, cw=1150, min_h=520)

    def slide(self, seg, i, tt, who, mouth):
        fr = self.slide_base.copy()
        key = ("slide", seg["kind"], id(seg))
        cd = self.cached(key, lambda: self.slide_card(seg))
        self.fade(fr, cd, 50, 190 + max(0, (640 - cd.height) // 2), min(1, (tt - seg["start"]) / 0.2))
        ms = sprite("Mika", 0, False, 0.74, True)
        self.character(fr, "Mika", i, tt, who == "Mika", mouth, W - 90 - SPRITE_W // 2 - int(SPRITE_W * 0.74) // 2, 1000 - ms.height + 12, full=True, out=0.74)
        if seg["kind"] == "quiz" and seg["phase"] == "think":
            left = max(0.0, 5 - (tt - seg["t0"]))
            d = ImageDraw.Draw(fr); cx, cy, r = W - 90 - SPRITE_W // 2, 240, 95
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255), outline=BRAND, width=10)
            d.arc((cx - r, cy - r, cx + r, cy + r), -90, -90 + 360 * (left / 5), fill=(255, 190, 110), width=10)
            d.text((cx, cy), str(max(1, math.ceil(left))), font=font(110), fill=INK, anchor="mm")
        return fr

    def frame(self, i):
        tt = i / FPS; seg = self.seg_at(tt); B = self.B
        who, mouth = B["spk"][min(i, B["n"] - 1)], B["mouth"][min(i, B["n"] - 1)]
        if seg["kind"] in ("title", "story", "outro"):
            return self.stage(seg, i, tt, who, mouth)
        return self.slide(seg, i, tt, who, mouth)


# ------------------------------------------------------------------ extras
def write_extras(B, outdir, stem):
    meta, chapters = B["meta"], B["chapters"]
    ep = f"Ep.{meta['episode']} " if meta.get("episode") else ""
    lines = [f"{ep}{meta['title']} | Learn Japanese with a story, vocabulary, grammar & quiz", "",
             "Learn Japanese through a short animated story with Japanese, romaji and English subtitles. "
             "Then we break down the vocabulary and grammar, and test what you learned in a quick quiz.", "", "CHAPTERS"]
    lines += [f"{fmt_time(t)} {name}" for t, name in chapters]
    if B["vocab"]:
        lines += ["", "VOCABULARY"] + [f"{v['jp']} ({v['romaji']}) - {v['en']}" for v in B["vocab"]]
    if B["grammar"]:
        lines += ["", "GRAMMAR"] + [f"{g['pattern']} - {g['meaning']}" for g in B["grammar"]]
    lines += ["", "#learnjapanese #japanese #JLPT #japanesestory"]
    open(os.path.join(outdir, stem + ".description.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")

    def ts(t):
        ms = int(round(t * 1000)); return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    srt = []
    for k, ln in enumerate(B["story"], 1):
        srt.append(f"{k}\n{ts(ln['start'])} --> {ts(ln['end'] + 0.5)}\n{ln['jp']}\n{ln['en']}\n")
    open(os.path.join(outdir, stem + ".srt"), "w", encoding="utf-8").write("\n".join(srt))


def thumbnail(R, path):
    seg = R.B["segs"][0]
    bg, fg = R.scene(seg["scene"]); fr = bg.copy()
    for nm, c in CHARS.items():
        s = sprite(nm, 2 if nm == "Mika" else 1, False); fr.paste(s, (c["x"], CHAR_Y + 70), s)
    fr.paste(fg, (0, FLOOR_Y - 40), fg)
    d = ImageDraw.Draw(fr, "RGBA"); ep = f"Ep.{R.meta['episode']}" if R.meta.get("episode") else "TINY JAPANESE"
    size = 150
    while size > 70 and font(size).getlength(R.meta["title"]) > 1500:
        size -= 6
    d.rounded_rectangle((120, 250, W - 120, 560), radius=60, fill=(255, 255, 255, 240))
    d.text((W // 2, 330), ep + "  ·  Learn Japanese with a story", font=font(52), fill=BRAND, anchor="mm")
    d.text((W // 2, 460), R.meta["title"], font=font(size), fill=INK, anchor="mm")
    fr.resize((1280, 720), Image.LANCZOS).save(path)


def main():
    ap = argparse.ArgumentParser(description="Tiny Japanese YouTube lesson generator")
    ap.add_argument("script"); ap.add_argument("-o", "--out", default="output", help="output folder")
    ap.add_argument("--rate", default="-12%", help="Japanese speech speed, e.g. -12%% (slower)")
    ap.add_argument("--dummy-audio", action="store_true", help="skip TTS (for testing)")
    ap.add_argument("--preview", metavar="DIR", help="save one PNG per section and exit (no video)")
    a = ap.parse_args()
    stem = os.path.splitext(os.path.basename(a.script))[0]
    with tempfile.TemporaryDirectory() as tmp:
        B = build(a.script, a.rate, a.dummy_audio, tmp)
        R = Renderer(B)
        if a.preview:
            os.makedirs(a.preview, exist_ok=True)
            seen = set()
            for seg in B["segs"]:
                key = seg["kind"] + str(seg.get("phase", "")) + str(seg.get("shown", ""))
                if key in seen:
                    continue
                seen.add(key)
                i = int((seg["start"] + 0.6) * FPS)
                R.frame(min(i, B["n"] - 1)).save(os.path.join(a.preview, f"{len(seen):02d}-{key}.png"))
            print(f"Wrote {len(seen)} preview frames to {a.preview}  (length {fmt_time(B['total'])})")
            return
        os.makedirs(a.out, exist_ok=True)
        wav = os.path.join(tmp, "final.wav"); write_wav(wav, B["audio"])
        out = os.path.join(a.out, stem + ".mp4")
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                              "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                              "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", out],
                             stdin=subprocess.PIPE)
        for i in range(B["n"]):
            p.stdin.write(R.frame(i).tobytes())
        p.stdin.close(); p.wait()
        write_extras(B, a.out, stem); thumbnail(R, os.path.join(a.out, stem + ".thumbnail.png"))
        print(f"Wrote {out} ({fmt_time(B['total'])}) + description, srt, thumbnail")


if __name__ == "__main__":
    main()
