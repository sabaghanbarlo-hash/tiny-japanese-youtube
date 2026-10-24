'''More places for Tiny Japanese Story, plus per-visit variants and a little life in the sky.

New places: town (shopping street), mountain (Mt. Fuji and a lake), river (bridge), train (animated windows),
bedroom, kitchen (steaming pot), schoolyard, festival (fireworks), busstop.
Every place also has three looks (variants) so a place that comes back later in a story, or in another episode,
does not look identical.
'''
import math, random
import numpy as np
from PIL import Image, ImageDraw

L = None


def bind(mod):
    global L
    L = mod


# ------------------------------------------------------------------ palettes, names, spots
SCENES = {
    "town": dict(top=(170, 214, 246), bot=(238, 246, 252), floor=(184, 176, 172), table=(150, 176, 120), edge=(108, 134, 86)),
    "mountain": dict(top=(150, 206, 248), bot=(232, 244, 250), floor=(150, 192, 120), table=(112, 164, 100), edge=(80, 126, 76)),
    "river": dict(top=(190, 224, 250), bot=(240, 248, 238), floor=(172, 202, 142), table=(190, 154, 112), edge=(142, 110, 80)),
    "train": dict(top=(236, 236, 242), bot=(222, 224, 232), floor=(124, 114, 124), table=(70, 100, 146), edge=(52, 74, 118)),
    "bedroom": dict(top=(232, 226, 246), bot=(220, 216, 240), floor=(190, 152, 122), table=(208, 172, 204), edge=(152, 122, 154)),
    "kitchen": dict(top=(255, 248, 230), bot=(250, 238, 214), floor=(204, 172, 132), table=(236, 224, 200), edge=(188, 160, 120)),
    "schoolyard": dict(top=(176, 220, 250), bot=(234, 246, 240), floor=(214, 196, 160), table=(150, 200, 120), edge=(104, 156, 84)),
    "festival": dict(top=(24, 26, 64), bot=(96, 56, 104), floor=(96, 72, 84), table=(186, 70, 70), edge=(130, 48, 56)),
    "busstop": dict(top=(200, 214, 232), bot=(232, 238, 244), floor=(96, 98, 110), table=(190, 190, 196), edge=(150, 150, 160)),
}
KEYWORDS = {
    "town": ["まち", "町", "しょうてんがい", "商店街", "パンや", "パン屋", "bakery", "vending", "shopping street", "flower shop", "town"],
    "mountain": ["やま", "山", "ふじさん", "富士山", "みずうみ", "湖", "mountain", "fuji", "lake", "hiking", "climb"],
    "river": ["かわ", "川", "はし", "橋", "river", "bridge", "riverside"],
    "train": ["ちかてつ", "つりかわ", "subway", "on the train", "commute"],
    "bedroom": ["ベッド", "ねる", "ベッドルーム", "bedroom", "bed", "sleep", "wake up"],
    "kitchen": ["だいどころ", "台所", "キッチン", "りょうり", "料理", "kitchen", "cook", "fridge"],
    "schoolyard": ["こうてい", "校庭", "うんどうかい", "運動会", "schoolyard", "school gate", "sports day", "recess"],
    "festival": ["まつり", "祭り", "はなび", "花火", "たこやき", "きんぎょ", "festival", "fireworks", "yukata", "takoyaki", "goldfish"],
    "busstop": ["バスてい", "バス停", "バス", "bus stop", "bus"],
}
ALIASES = {
    "town": "town", "shopping street": "town", "downtown": "town", "main street": "town", "village": "town", "neighborhood": "town",
    "mountain": "mountain", "mt fuji": "mountain", "mount fuji": "mountain", "fuji": "mountain", "lake": "mountain",
    "river": "river", "riverside": "river", "riverbank": "river", "bridge": "river", "canal": "river",
    "train": "train", "subway": "train", "on the train": "train", "train station": "station", "platform": "station",
    "bedroom": "bedroom", "kitchen": "kitchen",
    "schoolyard": "schoolyard", "school yard": "schoolyard", "school gate": "schoolyard", "playground": "schoolyard",
    "bus stop": "busstop", "busstop": "busstop", "bus station": "busstop",
    "festival": "festival", "matsuri": "festival", "fireworks": "festival", "summer festival": "festival",
}
LANDMARKS = {
    "town": {"vending machine": 0.12, "bakery": 0.34, "fruit shop": 0.58, "flower shop": 0.82},
    "mountain": {"pine tree": 0.1, "bench": 0.3, "lake": 0.55},
    "river": {"willow tree": 0.08, "bridge": 0.5, "riverbank": 0.9},
    "train": {"door": 0.08, "window": 0.3, "seat": 0.5},
    "bedroom": {"bed": 0.25, "window": 0.7, "desk": 0.8},
    "kitchen": {"counter": 0.12, "stove": 0.3, "window": 0.68, "fridge": 0.84},
    "schoolyard": {"gate": 0.11, "door": 0.5, "flagpole": 0.86},
    "festival": {"takoyaki stall": 0.25, "goldfish stall": 0.5, "shaved ice stall": 0.75},
    "busstop": {"bus stop": 0.35, "bench": 0.38, "sign": 0.62, "bus": 0.82},
}


# ------------------------------------------------------------------ variants (three looks per place)
def variant_of(title, scene, visit):
    return (sum(map(ord, (title or "") + scene)) + max(0, visit - 1)) % 3


def variant_grade(img, variant):
    '''Variant 1: warm afternoon light. Variant 2: cool, slightly overcast. Variant 0: as drawn.'''
    if variant == 0:
        return img
    a = np.asarray(img.convert("RGB"), dtype=np.float32)
    if variant == 1:
        a = a * np.array([1.04, 0.99, 0.91]) + np.array([8, 2, -4])
    else:
        g = a.mean(axis=2, keepdims=True)
        a = (a * 0.88 + g * 0.12) * np.array([0.95, 0.99, 1.05]) + np.array([-2, 2, 8])
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


# ------------------------------------------------------------------ places
def _skyline(d, rng, y0, cols, hmin, hmax, windows=True):
    x = -30
    while x < L.W:
        w, h = rng.randint(130, 240), rng.randint(hmin, hmax)
        d.rectangle((x, y0 - h, x + w, y0), fill=rng.choice(cols))
        if windows:
            for wy in range(y0 - h + 34, y0 - 60, 64):
                for wx in range(x + 24, x + w - 50, 58):
                    d.rectangle((wx, wy, wx + 32, wy + 38), fill=(196, 222, 238))
        x += w + rng.randint(4, 20)


def _town(d, rng):
    W = L.W
    d.ellipse((1560, 160, 1690, 290), fill=(255, 240, 176))
    _skyline(d, rng, 800, [(238, 214, 200), (214, 226, 240), (240, 232, 196), (222, 238, 214), (236, 210, 226)], 300, 470)
    pts = [(x, 260 + 30 * math.sin(x / 140)) for x in range(0, W + 40, 40)]
    d.line(pts, fill=(110, 90, 80), width=3)
    cols = [(240, 96, 110), (250, 200, 90), (110, 180, 240), (140, 210, 150)]
    for j, (x, y) in enumerate(pts[:-1]):
        if j % 2 == 0:
            d.polygon([(x, y), (x + 40, y + 2), (x + 20, y + 54)], fill=cols[(j // 2) % 4])
    for fx, label, c1, c2, kind in ((0.34, "パン", (232, 150, 92), (255, 238, 214), "bread"),
                                     (0.58, "くだもの", (110, 184, 112), (246, 250, 238), "fruit"),
                                     (0.82, "はなや", (232, 120, 160), (255, 240, 244), "flower")):
        cx = int(fx * W)
        d.rectangle((cx - 170, 470, cx + 170, 800), fill=(252, 246, 236))
        d.rectangle((cx - 170, 470, cx + 170, 484), fill=(210, 196, 176))
        n, sw = 8, 340 / 8
        for j in range(n):
            xa = cx - 170 + j * sw
            col = c1 if j % 2 == 0 else c2
            d.polygon([(xa, 484), (xa + sw, 484), (xa + sw + 8, 552), (xa - 8, 552)], fill=col)
            d.pieslice((xa - 8, 536, xa + sw + 8, 570), 0, 180, fill=col)
        L.sign(d, cx, 384, 260, 72, label, c1, size=46)
        d.rounded_rectangle((cx - 140, 590, cx + 20, 770), radius=14, fill=(206, 230, 244), outline=(150, 130, 110), width=6)
        d.rounded_rectangle((cx + 56, 590, cx + 140, 800), radius=10, fill=(176, 130, 96))
        d.ellipse((cx + 70, 690, cx + 82, 702), fill=(250, 220, 120))
        for j in range(4):
            xj = cx - 112 + j * 34
            if kind == "bread":
                d.ellipse((xj - 18, 726, xj + 18, 760), fill=(214, 156, 84)); d.arc((xj - 12, 730, xj + 12, 752), 200, 340, fill=(240, 200, 140), width=3)
            elif kind == "fruit":
                d.ellipse((xj - 16, 728, xj + 16, 760), fill=[(230, 70, 70), (250, 190, 60), (130, 200, 90), (240, 130, 60)][j])
            else:
                d.line([(xj, 764), (xj, 704)], fill=(80, 150, 90), width=5)
                d.ellipse((xj - 15, 684, xj + 15, 714), fill=[(240, 110, 150), (250, 220, 90), (190, 130, 230), (250, 150, 120)][j])
    vx = int(0.12 * W)
    d.rounded_rectangle((vx - 70, 540, vx + 70, 800), radius=12, fill=(214, 72, 76))
    d.rectangle((vx - 56, 560, vx + 56, 690), fill=(196, 226, 244))
    for r_ in range(3):
        for c_ in range(4):
            d.rectangle((vx - 48 + c_ * 25, 570 + r_ * 38, vx - 30 + c_ * 25, 600 + r_ * 38), fill=[(250, 190, 60), (90, 170, 240), (130, 200, 110), (240, 120, 120)][(r_ + c_) % 4])
    d.rectangle((vx - 40, 718, vx + 40, 752), fill=(60, 50, 54))


def _mountain(d, rng):
    W = L.W
    d.ellipse((1180, 140, 1300, 260), fill=(255, 240, 180))
    d.polygon([(0, 640), (260, 470), (520, 600), (700, 500), (900, 640)], fill=(170, 190, 220))
    d.polygon([(1300, 640), (1560, 480), (1780, 590), (1920, 520), (1920, 640)], fill=(170, 190, 220))
    d.polygon([(560, 640), (960, 300), (1020, 300), (1440, 640)], fill=(118, 142, 196))
    d.polygon([(960, 300), (1020, 300), (1084, 352), (1040, 340), (1010, 376), (990, 344), (960, 380), (936, 342), (899, 352)], fill=(246, 248, 252))
    d.rectangle((0, 640, W, 800), fill=(104, 168, 218))
    d.polygon([(560, 640), (960, 720), (1020, 720), (1440, 640)], fill=(118, 160, 208))
    for y in range(660, 800, 22):
        x0 = rng.randint(0, 200)
        while x0 < W:
            d.line([(x0, y), (x0 + rng.randint(30, 90), y)], fill=(196, 226, 246), width=3)
            x0 += rng.randint(180, 320)
    for px in (150, 300, 1650, 1790):
        d.rectangle((px - 10, 600, px + 10, 800), fill=(120, 86, 64))
        for k, (ty, hw) in enumerate(((740, 90), (660, 72), (590, 54))):
            d.polygon([(px - hw, ty), (px + hw, ty), (px, ty - 110)], fill=(64 + k * 14, 132 + k * 10, 86 + k * 6))
    L.sign(d, 1560, 330, 500, 76, "ふじさん  Mt. Fuji", (70, 120, 180), size=44)


def _river(d, rng):
    W = L.W
    d.ellipse((260, 150, 400, 290), fill=(255, 240, 180))
    d.ellipse((-200, 430, 700, 760), fill=(150, 196, 150)); d.ellipse((1000, 420, 2100, 780), fill=(140, 190, 146))
    d.rectangle((0, 600, W, 800), fill=(110, 176, 222))
    for y in range(620, 800, 26):
        for x in range(-40 + (y * 7) % 90, W, 130):
            d.arc((x, y, x + 70, y + 20), 200, 340, fill=(220, 240, 252), width=4)
    d.chord((640, 400, 1280, 760), 180, 360, fill=(212, 78, 70))
    d.chord((716, 470, 1204, 690), 180, 360, fill=(200, 226, 246))
    d.rectangle((716, 580, 1204, 620), fill=(110, 176, 222))
    for k in range(15):
        t = math.pi * k / 14
        px, py = 960 + 320 * math.cos(t), 580 - 180 * math.sin(t)
        d.rectangle((px - 5, py - 30, px + 5, py), fill=(150, 40, 36))
    d.arc((640, 370, 1280, 730), 180, 360, fill=(150, 40, 36), width=10)
    for wx in (150, 1760):
        d.rectangle((wx - 14, 420, wx + 14, 800), fill=(110, 82, 62))
        d.ellipse((wx - 130, 330, wx + 130, 490), fill=(120, 178, 112))
        for j in range(-5, 6):
            d.line([(wx + j * 20, 450), (wx + j * 24, 640 + (j % 3) * 22)], fill=(110, 170, 110), width=5)


TRAIN_WIN = [(150, 230), (720, 230), (1290, 230)]
TW, TH = 480, 330


def _train(d, rng):
    W = L.W
    d.rectangle((0, 0, W, 92), fill=(210, 212, 222))
    for x in range(120, W, 300):
        d.rounded_rectangle((x, 24, x + 160, 54), radius=12, fill=(255, 252, 232))
    d.line([(0, 104), (W, 104)], fill=(176, 180, 192), width=8)
    for wx, wy in TRAIN_WIN:
        d.rounded_rectangle((wx - 16, wy - 16, wx + TW + 16, wy + TH + 16), radius=26, fill=(124, 132, 152))
        d.rectangle((wx, wy, wx + TW, wy + TH), fill=(170, 214, 246))
    d.rectangle((0, 600, W, 790), fill=(64, 124, 148))
    for x in range(0, W, 360):
        d.rounded_rectangle((x + 10, 618, x + 340, 770), radius=26, fill=(86, 150, 174))
    for x in (655, 1235):
        d.rectangle((x - 7, 100, x + 7, 800), fill=(206, 210, 220))
    d.line([(1160, 130), (1780, 130)], fill=(60, 150, 110), width=10)
    for j in range(6):
        cx = 1160 + j * 124
        d.ellipse((cx - 14, 116, cx + 14, 144), fill=(255, 255, 255), outline=(60, 150, 110), width=6)


_strips = {}


def _train_strips():
    if not _strips:
        P = 1200
        r = random.Random(4)
        g = np.zeros((TH, P + TW, 3), np.uint8)
        for c in range(3):
            g[:, :, c] = np.linspace((170, 214, 246)[c], (236, 244, 250)[c], TH)[:, None]
        far = Image.fromarray(g).convert("RGBA"); fd = ImageDraw.Draw(far)
        for k in range(8):
            x = k * 150 + r.randint(0, 60); w = r.randint(150, 260)
            for off in (0, P):
                fd.ellipse((x + off - w, 190, x + off + w, 190 + 2 * r.randint(90, 130)), fill=(150, 196, 156))
        for k in range(10):
            x = k * 120 + r.randint(0, 40); hh = r.randint(60, 140)
            for off in (0, P):
                fd.rectangle((x + off, 250 - hh + 60, x + off + 70, 262), fill=(196, 206, 222))
        near = Image.new("RGBA", (P + TW, TH), (0, 0, 0, 0)); nd = ImageDraw.Draw(near)
        for k in range(6):
            x = k * 200 + r.randint(0, 80); w = r.randint(90, 150); hh = r.randint(90, 150)
            for off in (0, P):
                nd.rectangle((x + off, TH - 40 - hh, x + off + w, TH - 40), fill=(150, 130, 124))
                nd.polygon([(x + off - 10, TH - 40 - hh), (x + off + w + 10, TH - 40 - hh), (x + off + w / 2, TH - 40 - hh - 50)], fill=(120, 80, 78))
        for k in range(3):
            for off in (0, P):
                nd.rectangle((k * 400 + 150 + off, 0, k * 400 + 162 + off, TH), fill=(64, 58, 64))
        nd.rectangle((0, TH - 40, P + TW, TH), fill=(96, 150, 100))
        _strips.update(far=far, near=near, P=P)
    return _strips


def _train_dyn(fr, tt):
    S = _train_strips(); P = S["P"]
    fo, no = int(tt * 110) % P, int(tt * 430) % P
    fc, nc = S["far"].crop((fo, 0, fo + TW, TH)), S["near"].crop((no, 0, no + TW, TH))
    for wx, wy in TRAIN_WIN:
        fr.paste(fc, (wx, wy)); fr.paste(nc, (wx, wy), nc)
    d = ImageDraw.Draw(fr)
    for sx in (400, 960, 1520, 1750):
        a = 0.06 * math.sin(tt * 2.2 + sx)
        ex, ey = sx + 130 * math.sin(a), 104 + 130 * math.cos(a)
        d.line([(sx, 104), (ex, ey - 24)], fill=(214, 216, 226), width=5)
        d.ellipse((ex - 22, ey - 30, ex + 22, ey + 14), outline=(236, 238, 248), width=8)


def _bedroom(d, rng):
    W = L.W
    d.rectangle((0, 560, W, 800), fill=(214, 204, 232))
    L.window(d, 1180, 170, 470, 420, glass=(190, 222, 246))
    d.polygon([(1150, 150), (1230, 150), (1210, 610), (1150, 610)], fill=(240, 170, 190)); d.polygon([(1650, 150), (1730, 150), (1730, 610), (1672, 610)], fill=(240, 170, 190))
    d.rounded_rectangle((120, 330, 830, 640), radius=34, fill=(176, 130, 94))
    d.rounded_rectangle((150, 500, 860, 760), radius=36, fill=(244, 244, 252))
    d.rounded_rectangle((150, 590, 860, 760), radius=36, fill=(150, 176, 232))
    for x in range(190, 830, 90):
        d.ellipse((x, 632, x + 44, 676), fill=(190, 208, 246))
    d.rounded_rectangle((190, 470, 440, 560), radius=40, fill=(255, 226, 232)); d.rounded_rectangle((470, 470, 720, 560), radius=40, fill=(255, 240, 200))
    d.rectangle((1000, 640, 1800, 676), fill=(196, 150, 108)); d.rectangle((1020, 676, 1050, 800), fill=(176, 130, 92)); d.rectangle((1750, 676, 1780, 800), fill=(176, 130, 92))
    d.rectangle((1380, 530, 1392, 640), fill=(120, 110, 120)); d.polygon([(1330, 530), (1442, 530), (1410, 440), (1362, 440)], fill=(250, 214, 110))
    for k, c in enumerate(((210, 96, 96), (96, 150, 200), (230, 190, 96))):
        d.rectangle((1560, 620 - 22 * (k + 1), 1700, 640 - 22 * k), fill=c)
    d.rectangle((880, 210, 1030, 400), fill=(255, 248, 232), outline=(190, 150, 112), width=6)
    star = [(955 + (60 if i % 2 == 0 else 26) * math.sin(i * math.pi / 5), 305 - (60 if i % 2 == 0 else 26) * math.cos(i * math.pi / 5)) for i in range(10)]
    d.polygon(star, fill=(250, 200, 90))
    pts = [(x, 90 + 26 * math.sin(x / 170)) for x in range(900, W + 40, 40)]
    d.line(pts, fill=(120, 100, 110), width=3)
    for j, (x, y) in enumerate(pts):
        d.ellipse((x - 9, y, x + 9, y + 22), fill=[(250, 200, 90), (240, 120, 150), (130, 200, 240), (160, 220, 150)][j % 4])


def _kitchen(d, rng):
    W = L.W
    d.rectangle((0, 330, W, 600), fill=(246, 250, 252))
    for x in range(0, W, 64):
        d.line([(x, 330), (x, 600)], fill=(214, 226, 234), width=3)
    for y in range(330, 600, 64):
        d.line([(0, y), (W, y)], fill=(214, 226, 234), width=3)
    for x in (200, 520, 840):
        d.rounded_rectangle((x, 130, x + 300, 330), radius=14, fill=(206, 162, 120), outline=(160, 120, 86), width=5)
        d.rectangle((x + 130, 296, x + 170, 304), fill=(120, 90, 64))
    d.rectangle((0, 600, 1120, 800), fill=(226, 190, 150)); d.rectangle((0, 586, 1120, 614), fill=(236, 232, 226))
    for x in range(0, 1120, 280):
        d.rounded_rectangle((x + 12, 632, x + 268, 790), radius=10, outline=(176, 134, 96), width=5)
        d.rectangle((x + 120, 650, x + 160, 658), fill=(120, 90, 64))
    d.rectangle((476, 560, 676, 590), fill=(60, 60, 66))
    for bx in (516, 636):
        d.ellipse((bx - 28, 556, bx + 28, 574), fill=(34, 34, 40))
    d.rectangle((520, 480, 632, 562), fill=(176, 182, 196)); d.rectangle((510, 470, 642, 486), fill=(150, 158, 174)); d.ellipse((562, 452, 590, 472), fill=(120, 126, 142))
    d.line([(760, 400), (1100, 400)], fill=(120, 120, 130), width=8)
    for ux in range(790, 1100, 60):
        d.line([(ux, 400), (ux, 470)], fill=(120, 120, 130), width=4); d.ellipse((ux - 14, 470, ux + 14, 520), fill=(200, 204, 214))
    L.window(d, 1170, 170, 260, 260)
    d.rounded_rectangle((1480, 190, 1760, 800), radius=18, fill=(244, 246, 250), outline=(200, 206, 214), width=6)
    d.line([(1480, 440), (1760, 440)], fill=(200, 206, 214), width=6)
    d.rounded_rectangle((1500, 300, 1516, 400), radius=6, fill=(176, 182, 196)); d.rounded_rectangle((1500, 470, 1516, 570), radius=6, fill=(176, 182, 196))
    for k, c in enumerate(((240, 120, 120), (110, 180, 240), (250, 200, 90))):
        d.ellipse((1600 + k * 40, 240, 1628 + k * 40, 268), fill=c)


def _steam(fr, tt):
    d = ImageDraw.Draw(fr)
    for i in range(6):
        u = ((tt * 0.5) + i / 6.0) % 1.0
        x = 576 + 18 * math.sin(tt * 2 + i * 1.7) + (i - 2.5) * 8
        y = 440 - 170 * u
        r = 14 + 16 * u
        c = tuple(int(255 - 30 * u) for _ in range(3))
        d.ellipse((x - r, y - r, x + r, y + r), fill=c)


def _schoolyard(d, rng):
    W = L.W
    d.ellipse((1560, 150, 1690, 280), fill=(255, 240, 176))
    d.rectangle((420, 300, 1480, 800), fill=(246, 236, 206)); d.rectangle((420, 300, 1480, 332), fill=(206, 190, 156))
    for ry in (366, 516):
        for x in range(470, 1440, 118):
            d.rectangle((x, ry, x + 84, ry + 110), fill=(196, 224, 240), outline=(150, 160, 170), width=4)
            d.line([(x + 42, ry), (x + 42, ry + 110)], fill=(150, 160, 170), width=3)
    d.rectangle((850, 628, 1050, 650), fill=(190, 170, 140)); d.rectangle((880, 650, 1020, 800), fill=(130, 100, 80)); d.line([(950, 650), (950, 800)], fill=(96, 72, 58), width=4)
    d.rectangle((860, 786, 1040, 800), fill=(200, 196, 190))
    d.rectangle((870, 190, 1030, 300), fill=(236, 224, 196)); d.polygon([(850, 190), (1050, 190), (950, 112)], fill=(196, 96, 84))
    d.ellipse((910, 210, 990, 290), fill=(255, 255, 250), outline=(80, 70, 70), width=6)
    d.line([(950, 250), (950, 222)], fill=(60, 50, 50), width=5); d.line([(950, 250), (972, 262)], fill=(60, 50, 50), width=5)
    for px in (60, 300):
        d.rectangle((px, 560, px + 60, 800), fill=(190, 190, 198))
    L.sign(d, 210, 470, 330, 66, "がっこう", (60, 120, 90), size=38)
    d.rectangle((1640, 300, 1652, 800), fill=(200, 200, 208)); d.rectangle((1652, 312, 1772, 392), fill=(255, 255, 255), outline=(190, 190, 196), width=3); d.ellipse((1690, 332, 1734, 376), fill=(222, 50, 60))
    d.rectangle((1816, 430, 1846, 800), fill=(122, 88, 66)); d.ellipse((1730, 270, 1910, 520), fill=(104, 176, 112))
    L.blossoms(d, rng, (1740, 290, 1900, 500), 18)


def _festival(d, rng):
    W = L.W
    for _ in range(90):
        x, y = rng.randint(0, W), rng.randint(0, 420); r = rng.choice((2, 3, 3, 4))
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 236))
    d.polygon([(0, 640), (200, 520), (460, 600), (700, 500), (980, 610), (1300, 520), (1600, 600), (1920, 540), (1920, 800), (0, 800)], fill=(40, 36, 76))
    for row in (210, 300):
        pts = [(x, row + 26 * math.sin(x / 190 + row)) for x in range(-20, W + 40, 40)]
        d.line(pts, fill=(90, 66, 76), width=3)
        for x, y in pts[::3]:
            d.ellipse((x - 24, y, x + 24, y + 56), fill=(236, 84, 72)); d.rectangle((x - 12, y - 6, x + 12, y + 2), fill=(60, 40, 40))
            d.line([(x - 22, y + 28), (x + 22, y + 28)], fill=(255, 214, 150), width=3)
    for fx, label, c1, kind in ((0.25, "たこやき", (236, 120, 60), "tako"), (0.5, "きんぎょ", (66, 150, 214), "gold"), (0.75, "かきごおり", (120, 190, 120), "ice")):
        cx = int(fx * W)
        d.rectangle((cx - 190, 520, cx + 190, 800), fill=(66, 48, 60)); d.rectangle((cx - 190, 650, cx + 190, 690), fill=(150, 104, 76))
        n, sw = 8, 380 / 8
        for j in range(n):
            xa = cx - 190 + j * sw
            d.polygon([(xa, 470), (xa + sw, 470), (xa + sw + 6, 540), (xa - 6, 540)], fill=c1 if j % 2 == 0 else (250, 246, 240))
        L.sign(d, cx, 392, 270, 66, label, c1, size=40)
        if kind == "tako":
            for j in range(6):
                d.ellipse((cx - 120 + j * 44, 610, cx - 80 + j * 44, 650), fill=(190, 120, 70))
        elif kind == "gold":
            d.ellipse((cx - 130, 600, cx + 130, 660), fill=(90, 170, 230))
            for j, (dx, dy) in enumerate(((-60, 626), (20, 636), (80, 618))):
                d.ellipse((cx + dx - 18, dy - 9, cx + dx + 18, dy + 9), fill=(250, 140, 70))
        else:
            for j in range(4):
                d.polygon([(cx - 110 + j * 70, 650), (cx - 70 + j * 70, 650), (cx - 90 + j * 70, 696)], fill=(236, 236, 240))
                d.ellipse((cx - 112 + j * 70, 616, cx - 68 + j * 70, 660), fill=[(250, 120, 140), (120, 200, 250), (250, 220, 100), (150, 220, 150)][j])


def _fireworks(fr, tt):
    d = ImageDraw.Draw(fr)
    for cx, cy, off, col in ((1220, 290, 0.0, (255, 120, 140)), (1600, 230, 1.4, (255, 220, 120)), (1000, 340, 2.7, (140, 200, 255))):
        p = ((tt + off) % 4.2) / 4.2
        if p < 0.12:
            y = 640 - (640 - cy) * (p / 0.12)
            d.line([(cx, y), (cx, y + 40)], fill=(255, 240, 200), width=4)
        elif p < 0.75:
            u = (p - 0.12) / 0.63
            r = 30 + 190 * (1 - (1 - u) ** 2)
            fade = 1 - u ** 1.5
            c = tuple(int(v * fade + s * (1 - fade)) for v, s in zip(col, (30, 30, 72)))
            rr = max(1.5, 5 * (1 - u * 0.6))
            for k in range(26):
                a = k * 2 * math.pi / 26
                x, y = cx + r * math.cos(a), cy + r * math.sin(a) + 40 * u * u
                d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=c)


def _busstop(d, rng):
    W = L.W
    _skyline(d, rng, 800, [(196, 202, 214), (214, 208, 200), (186, 196, 210), (220, 214, 222)], 240, 460)
    d.rectangle((520, 470, 1020, 500), fill=(90, 116, 150))
    for px in (530, 1000):
        d.rectangle((px, 500, px + 18, 800), fill=(110, 120, 138))
    d.rectangle((548, 500, 1000, 700), fill=(214, 232, 246), outline=(150, 170, 190), width=4)
    d.rectangle((600, 690, 940, 716), fill=(150, 110, 80))
    for lx in (620, 910):
        d.rectangle((lx, 716, lx + 14, 790), fill=(110, 84, 62))
    d.rectangle((1172, 340, 1188, 800), fill=(130, 136, 150)); d.ellipse((1120, 270, 1240, 390), fill=(40, 110, 190), outline=(255, 255, 255), width=6)
    d.text((1180, 330), "バス", font=L.font(44), fill=(255, 255, 255), anchor="mm")
    d.rounded_rectangle((1330, 470, 1900, 770), radius=40, fill=(86, 170, 120))
    for x in range(1360, 1880, 110):
        d.rounded_rectangle((x, 500, x + 90, 610), radius=12, fill=(204, 232, 246))
    d.rectangle((1330, 640, 1900, 670), fill=(250, 250, 246))
    for wx in (1430, 1760):
        d.ellipse((wx - 50, 730, wx + 50, 830), fill=(40, 40, 46)); d.ellipse((wx - 22, 758, wx + 22, 802), fill=(170, 174, 186))


DRAW = {"town": _town, "mountain": _mountain, "river": _river, "train": _train, "bedroom": _bedroom, "kitchen": _kitchen,
        "schoolyard": _schoolyard, "festival": _festival, "busstop": _busstop}
BIRD_SCENES = {"park", "sakura", "beach", "town", "mountain", "river", "schoolyard", "shrine"}


def _birds(fr, tt):
    d = ImageDraw.Draw(fr)
    for i in range(5):
        x = (i * 397 + tt * (62 + 9 * i)) % (L.W + 240) - 120
        y = 200 + (i * 53) % 150 + 14 * math.sin(tt * 2.6 + i)
        w = 15 + (i % 3) * 4
        flap = 9 * math.sin(tt * 9 + i * 2)
        d.line([(x - w, y - flap), (x, y), (x + w, y - flap)], fill=(70, 70, 92), width=3)


def dynamic(fr, scene, tt, seg):
    '''Moving things for new places and for the birds. Called before the characters are drawn.'''
    if scene == "train":
        _train_dyn(fr, tt)
    elif scene == "festival":
        _fireworks(fr, tt)
    elif scene == "kitchen":
        _steam(fr, tt)
    if scene in BIRD_SCENES and seg.get("tod") != "night":
        import atmos
        kind, k = atmos.weather_state(seg, tt)
        if not kind or k < 0.3:
            _birds(fr, tt)
