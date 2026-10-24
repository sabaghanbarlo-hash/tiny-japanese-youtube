#!/usr/bin/env python3
"""Tiny Japanese - Kana lesson generator (hiragana / katakana, one character per video).

One kana script (.txt) -> one MP4 (landscape 1920x1080 for YouTube by default, --format vertical for 1080x1920):
  hear it -> 3 fonts -> stroke-by-stroke writing animation (numbered, narrated) -> write-along countdown
  -> animated memory trick (picture + the character drawn on it) -> 3 real words (kana highlighted)
  -> look-alike warning -> 2 quiz questions (timer) -> outro.
Reuses lesson.py (voices, Mika, cards, audio track).
Stroke order data: data/strokes.json, derived from KanjiVG (c) Ulrich Apel, CC BY-SA 3.0, https://kanjivg.tagaini.net

Script format (kana/hira-a.txt):
    title: Hiragana A
    kana: あ
    script: hiragana            # or katakana
    romaji: a
    sound: like the "a" in father
    mnemonic_word: Apple
    mnemonic: あ looks like an apple. A for Apple!
    [words]
    あめ | ame | rain
    [similar]
    お | o | how to tell them apart
    [distractors]
    i, u
"""
import argparse, bisect, glob, json, math, os, random, re, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont
import lesson as L
from lesson import BRAND, INK, SOFT, ROMA, GREEN, FPS, font, card, sprite

HERE = os.path.dirname(os.path.abspath(__file__))
BOX, SS, THINK = 720, 2, 6
LAYOUTS = {
    "landscape": dict(SW=1920, SH=1080, header=(40, 24, 1880, 112), panel=(40, 136, 1060, 1040), pc=(550, 588),
                      cw=760, card_cx=1470, card_bottom=1050, mika_y=120, timer=(960, 236)),
    "vertical": dict(SW=1080, SH=1920, header=(50, 80, 1030, 250), panel=(80, 300, 1000, 1060), pc=(540, 680),
                     cw=980, card_cx=540, card_bottom=None, mika_y=None, timer=(860, 400)),
}


def parse_kana(path):
    meta = dict(title="", kana="", script="hiragana", romaji="", sound="", strokes="", mnemonic_word="", mnemonic="")
    words, similar, distractors, sec = [], [], [], None
    for n, raw in enumerate(open(path, encoding="utf-8").read().splitlines(), 1):
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        m = re.match(r"^\[([^\]]+)\]$", s)
        if m:
            sec = m[1].strip().lower(); continue
        if sec is None:
            m = re.match(r"^([a-z_]+)\s*:\s*(.+)$", s, re.I)
            if not m or m[1].lower() not in meta:
                L.die(f"line {n}: expected 'key: value' with keys {', '.join(meta)}: {s}")
            meta[m[1].lower()] = m[2].split("  #")[0].strip(); continue
        parts = [x.strip() for x in s.split("|")]
        if sec == "words":
            if len(parts) < 3: L.die(f"line {n}: words look like 'あめ | ame | rain'")
            words.append(dict(jp=parts[0], romaji=parts[1], en=parts[2]))
        elif sec == "similar":
            if len(parts) < 3: L.die(f"line {n}: similar looks like 'お | o | how to tell them apart'")
            similar.append(dict(kana=parts[0], romaji=parts[1], tip=parts[2]))
        elif sec == "distractors":
            distractors += [x.strip() for x in s.split(",") if x.strip()]
    for k in ("kana", "romaji"):
        if not meta[k]: L.die(f"missing '{k}:' at the top of the script")
    meta["script"] = meta["script"].lower()
    if meta["script"] not in ("hiragana", "katakana"): L.die("script must be hiragana or katakana")
    if not meta["title"]: meta["title"] = f"{meta['script'].title()} {meta['romaji'].upper()}"
    if not words: L.die("add at least one word under [words]")
    if len(distractors) < 2: distractors = [r for r in ("a", "i", "u", "e", "o", "ka", "ki", "ku", "ke", "ko") if r != meta["romaji"]][:3]
    return meta, words[:3], similar[:2], distractors[:3]


def make_quiz(meta, words, distractors):
    rng = random.Random(meta["kana"])
    opts = [meta["romaji"]] + distractors[:2]; rng.shuffle(opts)
    qs = [dict(q=f"Which sound is {meta['kana']}?", opts=opts, ans=opts.index(meta["romaji"]), glyph=meta["kana"], jp=None)]
    w = words[0]; others = [x["en"] for x in words[1:]] + ["thank you", "good morning", "water"]
    o2 = [w["en"]] + [x for x in others if x != w["en"]][:2]; rng.shuffle(o2)
    qs.append(dict(q=f"What does {w['jp']} mean?", opts=o2, ans=o2.index(w["en"]), glyph=w["jp"], jp=w["jp"]))
    return qs


def make_mk():
    ser = sorted(glob.glob("/usr/share/fonts/**/NotoSerifCJK-Bold.ttc", recursive=True))
    def mk(kind, size):
        if kind == "serif" and ser:
            try: return ImageFont.truetype(ser[0], size, index=2)
            except Exception: pass
        return font(size, kind != "light")
    return mk


MK = make_mk()


# ---------------------------------------------------------------- stroke data + drawing helpers
class Stroke:
    def __init__(self, pts):
        self.pts = [tuple(p) for p in pts]
        self.cum = [0.0]
        for a, b in zip(self.pts, self.pts[1:]): self.cum.append(self.cum[-1] + math.dist(a, b))
        self.length = self.cum[-1]

    def upto(self, f):
        if f >= 1: return self.pts
        tgt = self.length * max(0.0, f); i = bisect.bisect_left(self.cum, tgt)
        if i == 0: return [self.pts[0]]
        a, b = self.pts[i - 1], self.pts[i]; seg = (self.cum[i] - self.cum[i - 1]) or 1.0; u = (tgt - self.cum[i - 1]) / seg
        return self.pts[:i] + [(a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)]


def load_strokes(script, romaji):
    p = os.path.join(HERE, "data", "strokes.json")
    if not os.path.exists(p): L.die("data/strokes.json is missing")
    data = json.load(open(p, encoding="utf-8"))
    try: return [Stroke(s) for s in data[script][romaji]]
    except KeyError: L.die(f"no stroke data for {script} '{romaji}' in data/strokes.json")


def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease(f): f = clamp(f); return f * f * (3 - 2 * f)
def ph(t, a, b): return clamp((t - a) / (b - a))
def back(f): f = clamp(f); c1 = 1.70158; c3 = c1 + 1; return 1 + c3 * (f - 1) ** 3 + c1 * (f - 1) ** 2


def line(d, pts, w, fill, U):
    q = [(x * U, y * U) for x, y in pts]
    if len(q) > 1: d.line(q, fill=fill, width=int(w), joint="curve")
    r = w / 2
    for x, y in (q[0], q[-1]): d.ellipse((x - r, y - r, x + r, y + r), fill=fill)


def draw_prog(d, S, prog, w, fill, U):
    for i, s in enumerate(S):
        if prog >= i + 1: line(d, s.pts, w, fill, U)
        elif prog > i: line(d, s.upto(prog - i), w, fill, U)



# ---------------------------------------------------------------- memory-trick scenes (original artwork, drawn in code)
# Each scene draws on a (BOX*SS)^2 layer. t runs 0..1 over the narration of the trick.
def circle(d, x, y, r, fill, outline=None, width=0):
    d.ellipse((x - r, y - r, x + r, y + r), fill=fill, outline=outline, width=width)


def scene_apple(d, S, t, U):
    s = back(ph(t, 0.0, 0.3)); C = BOX * SS // 2; cx, cy = C, C + 60
    if s > 0.01:
        for dx in (-190, 190): circle(d, cx + dx * s, cy + 20 * s, 470 * s, (226, 58, 64))
        d.ellipse((cx - 70 * s, cy - 440 * s, cx + 70 * s, cy - 360 * s), fill=(190, 40, 48))
        d.line([(cx, cy - 380 * s), (cx + 50 * s, cy - 560 * s)], fill=(110, 70, 40), width=max(2, int(56 * s)))
        d.ellipse((cx + 70 * s, cy - 610 * s, cx + 340 * s, cy - 490 * s), fill=(70, 170, 90))
        d.ellipse((cx - 400 * s, cy - 250 * s, cx - 270 * s, cy - 80 * s), fill=(240, 130, 130))
    p = ph(t, 0.3, 0.85)
    if p > 0:
        draw_prog(d, S, len(S) * ease(p), 84, (150, 30, 40), U); draw_prog(d, S, len(S) * ease(p), 58, (255, 255, 255), U)


def scene_eels(d, S, t, U):
    g = ph(t, 0.0, 0.55)
    for i, s in enumerate(S):
        f = ease(clamp((g - i * 0.3) / 0.7))
        if f <= 0: continue
        pts = s.upto(f); line(d, pts, 130, (30, 120, 135), U); line(d, pts, 50, (130, 205, 210), U)
        x, y = s.pts[0][0] * U, s.pts[0][1] * U
        circle(d, x, y, 58, (30, 120, 135)); circle(d, x + 6, y - 6, 28, (255, 255, 255)); circle(d, x + 10, y - 4, 13, (40, 40, 50))
    p = ph(t, 0.55, 0.9)
    if p > 0: draw_prog(d, S, len(S) * ease(p), 26, (255, 255, 255), U)


def scene_hat(d, S, t, U):
    f = ease(ph(t, 0.0, 0.45)); pts = S[1].upto(f)
    line(d, pts, 150, (50, 110, 190), U); line(d, pts, 116, (90, 160, 230), U)
    s = back(ph(t, 0.15, 0.45)); a, b = S[0].pts[0], S[0].pts[-1]; mx, my = (a[0] + b[0]) / 2 * U, (a[1] + b[1]) / 2 * U
    if s > 0.01:
        w, h = 170 * s, 230 * s
        d.polygon([(mx - w, my + 40 * s), (mx + w, my + 40 * s), (mx + 20 * s, my - h)], fill=(240, 80, 110))
        d.ellipse((mx - w - 20 * s, my + 10 * s, mx + w + 20 * s, my + 70 * s), fill=(255, 215, 90))
        circle(d, mx + 20 * s, my - h, 40 * s, (255, 230, 120))
    q = ph(t, 0.5, 0.95)
    if q > 0:
        x, y = S[1].upto(ease(q))[-1]; circle(d, x * U, y * U, 55, (255, 205, 70), (200, 150, 30), 8)


def scene_bird(d, S, t, U):
    f = ease(ph(t, 0.0, 0.6)); body = S[1].upto(f)
    line(d, body, 120, (255, 165, 50), U); line(d, body, 46, (255, 215, 120), U)
    crest = S[0].upto(ease(ph(t, 0.0, 0.3)))
    if len(crest) > 1: line(d, crest, 60, (235, 70, 80), U)
    p0 = S[1].pts[0]; x, y = p0[0] * U, p0[1] * U
    circle(d, x, y, 85, (255, 165, 50))
    k = min(8, len(S[1].pts) - 1); hx, hy = S[1].pts[k][0] - p0[0], S[1].pts[k][1] - p0[1]; n = math.hypot(hx, hy) or 1; hx, hy = hx / n, hy / n
    px, py = -hy, hx; bx, by = x - hx * 80, y - hy * 80
    d.polygon([(bx + px * 40, by + py * 40), (bx - px * 40, by - py * 40), (x - hx * 190, y - hy * 190)], fill=(255, 120, 40))
    ex, ey = min(((x + px * 35, y + py * 35), (x - px * 35, y - py * 35)), key=lambda p: p[1])
    circle(d, ex, ey, 26, (255, 255, 255)); circle(d, ex + 4, ey, 13, (40, 40, 50))
    q = ph(t, 0.6, 1.0)
    if q > 0:
        for (nx, ny) in ((1150, 380), (1260, 760), (260, 1080)):
            d.text((nx, ny - 60 * q), "♪", font=font(170), fill=(230, 90, 140), anchor="mm")


def scene_orange(d, S, t, U):
    f = ease(ph(t, 0.0, 0.6)); draw_prog(d, S[:2], 2 * f, 62, (110, 75, 50), U)
    s = back(ph(t, 0.6, 0.85))
    if s > 0.01:
        dot = S[2].pts; cx = sum(p[0] for p in dot) / len(dot) * U; cy = sum(p[1] for p in dot) / len(dot) * U
        r = 150 * s; circle(d, cx, cy, r, (250, 150, 30)); circle(d, cx - r * 0.35, cy - r * 0.35, r * 0.25, (255, 205, 120))
        d.ellipse((cx - 14 * s, cy - r - 30 * s, cx + 14 * s, cy - r + 10 * s), fill=(110, 75, 50))
        d.ellipse((cx + 10 * s, cy - r - 70 * s, cx + 130 * s, cy - r - 10 * s), fill=(70, 170, 90))


def scene_generic(d, S, t, U):
    draw_prog(d, S, len(S) * ease(ph(t, 0.1, 0.9)), 60, BRAND, U)


def scene_kite(d, S, t, U):
    s = back(ph(t, 0.0, 0.3)); C = BOX * SS // 2; cx, cy = C, C - 40
    if s > 0.01:
        top, rgt, bot, lft = (cx, cy - 560 * s), (cx + 400 * s, cy - 20 * s), (cx, cy + 470 * s), (cx - 400 * s, cy - 20 * s)
        d.polygon([top, rgt, bot, (cx, cy - 20 * s)], fill=(235, 80, 90)); d.polygon([top, (cx, cy - 20 * s), bot, lft], fill=(255, 190, 70))
        d.line([top, bot], fill=(120, 70, 40), width=max(2, int(14 * s))); d.line([lft, rgt], fill=(120, 70, 40), width=max(2, int(14 * s)))
        tail = [(cx + 40 * s * math.sin(k / 3.0), cy + 470 * s + k * 55 * s) for k in range(0, 17)]
        d.line(tail, fill=(120, 70, 40), width=max(2, int(10 * s)))
        for k in (4, 8, 12, 16):
            x, y = tail[k]; d.polygon([(x - 50 * s, y - 28 * s), (x, y), (x - 50 * s, y + 28 * s)], fill=(60, 150, 220)); d.polygon([(x + 50 * s, y - 28 * s), (x, y), (x + 50 * s, y + 28 * s)], fill=(60, 150, 220))
    p = ph(t, 0.3, 0.85)
    if p > 0:
        draw_prog(d, S, len(S) * ease(p), 84, (150, 40, 50), U); draw_prog(d, S, len(S) * ease(p), 58, (255, 255, 255), U)


def scene_key(d, S, t, U):
    s = back(ph(t, 0.0, 0.3)); C = BOX * SS // 2; gold = (240, 185, 40); dark = (190, 135, 20)
    if s > 0.01:
        cx = C
        circle(d, cx, C - 480 * s, 250 * s, gold); circle(d, cx, C - 480 * s, 120 * s, (255, 255, 255))
        d.rectangle((cx - 55 * s, C - 250 * s, cx + 55 * s, C + 600 * s), fill=gold)
        for y0, w in ((300, 190), (450, 150)): d.rectangle((cx + 55 * s, C + y0 * s, cx + (55 + w) * s, C + (y0 + 80) * s), fill=gold)
        d.ellipse((cx - 190 * s, C - 640 * s, cx - 110 * s, C - 560 * s), fill=(255, 225, 130))
    p = ph(t, 0.3, 0.85)
    if p > 0:
        draw_prog(d, S, len(S) * ease(p), 84, (130, 90, 10), U); draw_prog(d, S, len(S) * ease(p), 58, (255, 255, 255), U)


def scene_beak(d, S, t, U):
    s = back(ph(t, 0.0, 0.3)); C = BOX * SS // 2
    if s > 0.01:
        circle(d, C + 190, C, 380 * s, (90, 140, 215)); circle(d, C + 200, C - 190 * s, 56 * s, (255, 255, 255)); circle(d, C + 212, C - 186 * s, 26 * s, (40, 40, 50))
    f = ease(ph(t, 0.15, 0.7)); pts = S[0].upto(f)
    line(d, pts, 150, (250, 150, 40), U); line(d, pts, 56, (255, 205, 120), U)
    p = ph(t, 0.7, 1.0)
    if p > 0:
        for k, (nx, ny) in enumerate(((330, 260), (1180, 200))):
            d.text((nx, ny - 40 * p), "ku!", font=font(120), fill=(230, 90, 140), anchor="mm")


def scene_kettle(d, S, t, U):
    s = back(ph(t, 0.0, 0.3)); C = BOX * SS // 2; cx, cy = C, C + 90
    if s > 0.01:
        d.line([(cx + 300 * s, cy - 40 * s), (cx + 560 * s, cy - 300 * s)], fill=(80, 130, 160), width=max(2, int(110 * s)))
        d.arc((cx - 620 * s, cy - 380 * s, cx - 200 * s, cy + 120 * s), 95, 265, fill=(60, 60, 70), width=max(2, int(60 * s)))
        circle(d, cx, cy, 440 * s, (110, 160, 190)); d.ellipse((cx - 200 * s, cy - 500 * s, cx + 200 * s, cy - 380 * s), fill=(80, 130, 160)); circle(d, cx, cy - 530 * s, 50 * s, (60, 60, 70))
        circle(d, cx - 220 * s, cy - 150 * s, 80 * s, (170, 205, 225))
    q = ph(t, 0.55, 1.0)
    if q > 0:
        for k in range(3):
            y = C - 330 - ((q * 900 + k * 300) % 900) * 0.6; r = 60 + 25 * k
            circle(d, C + 600 + 30 * math.sin(q * 6 + k), y, r, (225, 235, 240))
    p = ph(t, 0.3, 0.85)
    if p > 0:
        draw_prog(d, S, len(S) * ease(p), 84, (40, 70, 95), U); draw_prog(d, S, len(S) * ease(p), 58, (255, 255, 255), U)


def scene_coins(d, S, t, U):
    s = back(ph(t, 0.0, 0.3)); gold = (245, 190, 50)
    if s > 0.01:
        for cy in (390, 1060):
            cxx = 740
            d.ellipse((cxx - 540 * s, cy + 50 * s - 215 * s, cxx + 540 * s, cy + 50 * s + 215 * s), fill=(190, 135, 20))
            d.ellipse((cxx - 540 * s, cy - 215 * s, cxx + 540 * s, cy + 215 * s), fill=gold)
            d.ellipse((cxx - 460 * s, cy - 170 * s, cxx + 460 * s, cy + 170 * s), outline=(220, 150, 30), width=max(2, int(18 * s)))
    p = ph(t, 0.3, 0.9)
    if p > 0: draw_prog(d, S, len(S) * ease(p), 62, (110, 70, 10), U)


SCENES = {("hiragana", "a"): scene_apple, ("hiragana", "i"): scene_eels, ("hiragana", "u"): scene_hat,
          ("hiragana", "e"): scene_bird, ("hiragana", "o"): scene_orange,
          ("hiragana", "ka"): scene_kite, ("hiragana", "ki"): scene_key, ("hiragana", "ku"): scene_beak,
          ("hiragana", "ke"): scene_kettle, ("hiragana", "ko"): scene_coins}



# ---------------------------------------------------------------- timeline + audio
ORD = ["First", "Second", "Third", "Fourth", "Fifth"]
ANIM = ("ghost", "stroke", "write", "mnemonic")


def build(path, rate, dummy, tmp):
    meta, words, similar, distractors = parse_kana(path)
    S = load_strokes(meta["script"], meta["romaji"])
    quiz = make_quiz(meta, words, distractors)
    K, R = meta["kana"], meta["romaji"]
    durs = [min(2.6, max(1.0, 0.6 + s.length / 90)) for s in S]
    tr = L.Track(tmp, rate, dummy); segs = []
    mark = lambda kind, start, **kw: segs.append(dict(kind=kind, start=start, **kw))
    SLOW = "-35%"
    tr.gap(0.3)
    mark("title", 0.0)
    tr.say(f"Learn {meta['script']} in one lesson. Today: {R.upper()}.", "Narrator"); tr.gap(0.4)
    mark("sound", tr.t)
    tr.say("Listen.", "Narrator"); tr.gap(0.2)
    for _ in range(2):
        tr.say(K + "。", "Mika", SLOW); tr.gap(0.7)
    if meta["sound"]:
        tr.say(f"It sounds {meta['sound']}.", "Narrator"); tr.gap(0.4)
    tr.say("Now you.", "Narrator"); tr.gap(0.2)
    mark("think", tr.t, t0=tr.t, n=3); tr.gap(3)
    mark("fonts", tr.t)
    tr.say("In real life you will see it in different fonts. Same character.", "Narrator"); tr.gap(0.6)
    mark("ghost", tr.t)
    tr.say(f"{K} takes {len(S)} stroke{'' if len(S) == 1 else 's'}. Watch the order.", "Narrator"); tr.gap(0.3)
    for i in range(len(S)):
        t0 = tr.t + 0.7
        mark("stroke", tr.t, idx=i, t0=t0, dur=durs[i])
        tr.say(f"{ORD[i]} stroke.", "Narrator")
        tr.gap(max(0.2, t0 + durs[i] + 0.5 - tr.t))
    mark("write", tr.t, t0=tr.t)
    tr.say("Now you. Write it along with me.", "Narrator"); tr.gap(0.2)
    mark("write", tr.t, t0=tr.t, timer=True); tr.gap(THINK)
    if meta["mnemonic"]:
        tr.say("Here is a trick to remember it.", "Narrator"); tr.gap(0.2)
        a = tr.t; mark("mnemonic", a, t0=a, dur=8.0); seg = segs[-1]
        _, b = tr.say(meta["mnemonic"], "Narrator")
        seg["dur"] = max(6.0, b - a + 1.0); tr.gap(max(0.6, seg["dur"] - (b - a)))
    for i, w in enumerate(words):
        mark("word", tr.t, w=w, i=i, n=len(words), shown=0)
        if i == 0:
            tr.say(f"Real words with {K}.", "Narrator"); tr.gap(0.25)
        tr.say(w["jp"], "Mika", "-30%"); tr.gap(0.25)
        mark("word", tr.t, w=w, i=i, n=len(words), shown=1)
        tr.say(w["en"], "Narrator"); tr.gap(0.5)
    for sm in similar:
        mark("similar", tr.t, s=sm)
        tr.say(f"Careful! Do not mix it up with {sm['kana']}.", "Narrator"); tr.gap(0.2)
        tr.say(sm["tip"], "Narrator"); tr.gap(0.4)
    for q in quiz:
        mark("quiz", tr.t, q=q, phase="ask")
        tr.say("Quick quiz!", "Narrator"); tr.gap(0.15)
        if q["jp"]:
            tr.say(q["jp"], "Mika", "-30%"); tr.gap(0.1); tr.say("What does it mean?", "Narrator")
        else:
            tr.say("Which sound is this character?", "Narrator")
        tr.gap(0.3)
        for k, o in enumerate(q["opts"]):
            tr.say("ABC"[k], "Narrator"); tr.gap(0.05); tr.say(o, "Narrator"); tr.gap(0.25)
        mark("quiz", tr.t, q=q, phase="think", t0=tr.t); tr.gap(THINK)
        mark("quiz", tr.t, q=q, phase="answer")
        tr.say(f"The answer is {'ABC'[q['ans']]}. {q['opts'][q['ans']]}.", "Narrator"); tr.gap(0.6)
    mark("outro", tr.t)
    tr.say("Follow Tiny Japanese for the next character!", "Narrator")
    total = tr.t + 1.0
    audio = tr.audio(total); n = int(total * FPS)
    mouth = L.mouth_levels(audio, n)
    spk = [None] * n
    for who, a, b in tr.talk:
        for i in range(max(0, int(a * FPS) - 1), min(n, int(b * FPS) + 2)):
            spk[i] = who
    return dict(meta=meta, words=words, similar=similar, quiz=quiz, segs=segs, audio=audio, n=n, total=total,
                mouth=mouth, spk=spk, S=S, durs=durs)



# ---------------------------------------------------------------- rendering
class Renderer:
    def __init__(self, B, fmt="landscape", assets="assets", lean=False):
        self.B, self.meta, self.S, self.fmt, self.assets, self.lean = B, B["meta"], B["S"], fmt, assets, lean
        self.lo = LAYOUTS[fmt]; self.land = fmt == "landscape"
        self.starts = [s["start"] for s in B["segs"]]; self.cache = {}
        self.cd = [0.8 * x for x in B["durs"]]; self.cycle = sum(self.cd) + 1.0
        self.bg = self._bg()

    def _bg(self):
        lo = self.lo; SW, SH = lo["SW"], lo["SH"]
        im = L.vgrad(SW, SH, (255, 246, 238), (250, 220, 232)).convert("RGB")
        dd = ImageDraw.Draw(im); rng = random.Random(4)
        if self.land:
            L.blossoms(dd, rng, (0, 0, SW, 130), 14); L.blossoms(dd, rng, (0, 1040, SW, SH), 12)
        else:
            L.blossoms(dd, rng, (0, 0, SW, 280), 20); L.blossoms(dd, rng, (0, 1560, SW, SH), 16)
            dd.rectangle((0, 1620, SW, SH), fill=(240, 214, 200))
        im = im.convert("RGBA"); d = ImageDraw.Draw(im, "RGBA")
        d.rounded_rectangle(lo["header"], radius=44, fill=(255, 255, 255, 238))
        if self.land:
            d.text((80, 68), "TINY JAPANESE", font=font(34), fill=BRAND, anchor="lm")
            d.text((1840, 68), self.meta["title"], font=font(46), fill=(60, 45, 48), anchor="rm")
        else:
            d.text((90, 104), "TINY JAPANESE", font=font(34), fill=BRAND)
            d.text((90, 160), self.meta["title"], font=font(56), fill=(60, 45, 48))
        d.rounded_rectangle(lo["panel"], radius=64, fill=(255, 255, 255, 245), outline=(240, 214, 220), width=6)
        return im

    def memo(self, key, fn):
        if key not in self.cache:
            if self.lean and len(self.cache) > 4: self.cache.pop(next(iter(self.cache)))
            self.cache[key] = fn()
        return self.cache[key]

    def put(self, d, text, f, cx, cy, fill):
        d.text((cx, cy), text, font=f, fill=fill, anchor="mm")

    def panel(self, seg):
        lo = self.lo; im = Image.new("RGBA", (lo["SW"], lo["SH"]), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        cx, cy = lo["pc"]; K, Rm, k = self.meta["kana"], self.meta["romaji"], seg["kind"]
        if k in ("title", "sound", "think"):
            self.put(d, K, MK("sans", 520), cx, cy - 30, INK)
            if k != "title": self.put(d, Rm, font(120), cx, cy + 330, BRAND)
        elif k == "fonts":
            for dx, kind, lab in ((-290, "sans", "gothic"), (0, "serif", "mincho"), (290, "light", "light")):
                self.put(d, K, MK(kind, 260), cx + dx, cy - 60, INK); self.put(d, lab, font(34, False), cx + dx, cy + 140, SOFT)
            self.put(d, Rm, font(120), cx, cy + 330, BRAND)
        elif k == "word":
            w = seg["w"]["jp"]; f = MK("sans", 200 if len(w) <= 3 else 150)
            x = cx - sum(f.getlength(c) for c in w) / 2
            for c in w:
                d.text((x, cy - 120), c, font=f, fill=BRAND if c == K else INK, anchor="lm"); x += f.getlength(c)
            if seg["shown"]:
                self.put(d, seg["w"]["romaji"], font(76), cx, cy + 70, ROMA); self.put(d, seg["w"]["en"], font(88), cx, cy + 190, SOFT)
        elif k == "similar":
            s = seg["s"]
            self.put(d, K, MK("sans", 360), cx - 250, cy - 40, BRAND); self.put(d, s["kana"], MK("sans", 360), cx + 250, cy - 40, INK)
            self.put(d, Rm, font(90), cx - 250, cy + 210, BRAND); self.put(d, s["romaji"], font(90), cx + 250, cy + 210, SOFT)
        elif k == "quiz":
            g = seg["q"]["glyph"]; self.put(d, g, MK("sans", 400 if len(g) == 1 else 200), cx, cy - 20, INK)
        elif k == "outro":
            self.put(d, K, MK("sans", 380), cx, cy - 80, BRAND); self.put(d, "また あした！", font(80), cx, cy + 210, INK)
            self.put(d, "Stroke order data: KanjiVG, CC BY-SA 3.0", font(28, False), cx, cy + 330, SOFT)
        return im

    def card_for(self, seg):
        k, M, cw = seg["kind"], self.meta, self.lo["cw"]; mh = 300 if self.land else 330
        if k == "title":
            return card(M["script"].title(), BRAND, [(M["title"], 66, True, INK, 10), (f"{M['kana']}  =  {M['romaji']}", 52, False, ROMA, 0)], cw=cw, min_h=mh)
        if k == "sound":
            b = [(f"“{M['romaji']}”", 100, True, INK, 8)]
            if M["sound"]: b.append((f"sounds {M['sound']}", 42, False, SOFT, 0))
            return card("Listen", BRAND, b, cw=cw, min_h=mh)
        if k == "think":
            return card("Your turn", BRAND, [("Say it out loud!", 64, True, INK, 8), (M["romaji"], 52, False, ROMA, 0)], cw=cw, min_h=mh)
        if k == "fonts":
            return card("Same character", BRAND, [("Many fonts, one sound", 54, True, INK, 8)], cw=cw, min_h=260)
        if k == "ghost":
            return card("Stroke order", BRAND, [(f"{len(self.S)} stroke{'' if len(self.S) == 1 else 's'}", 76, True, INK, 8), ("Watch the order", 42, False, SOFT, 0)], cw=cw, min_h=mh)
        if k == "stroke":
            return card(f"Stroke {seg['idx'] + 1} of {len(self.S)}", BRAND, [(ORD[seg["idx"]] + " stroke", 68, True, INK, 8), ("Follow the pen", 42, False, SOFT, 0)], cw=cw, min_h=mh)
        if k == "write":
            return card("Write along", BRAND, [("Your turn!", 72, True, INK, 8), ("Write it in the air or on paper", 40, False, SOFT, 0)], cw=cw, min_h=mh)
        if k == "mnemonic":
            return card("Memory trick", BRAND, [(M["mnemonic"], 46, True, INK, 0)], cw=cw, min_h=mh)
        if k == "word":
            w = seg["w"]
            return card(f"Word {seg['i'] + 1}/{seg['n']}", BRAND, [(w["jp"], 92, True, INK, 8), (w["romaji"], 46, False, ROMA, 6), (w["en"] if seg["shown"] else "...", 54, False, SOFT, 0)], cw=cw, min_h=380 if self.land else 420)
        if k == "similar":
            return card("Look-alike", (214, 110, 90), [(seg["s"]["tip"], 44, True, INK, 0)], cw=cw, min_h=mh)
        if k == "outro":
            return card("Thanks for watching", BRAND, [("Follow for the next character!", 56, True, INK, 8), ("また あした！ (mata ashita)", 40, False, SOFT, 0)], cw=cw, min_h=mh)
        q, ph_ = seg["q"], seg["phase"]; b = [(q["q"], 50 if self.land else 56, True, INK, 14)]
        for j, o in enumerate(q["opts"]):
            col = INK
            if ph_ == "answer": col = GREEN if j == q["ans"] else (170, 156, 162)
            b.append((f"{'ABC'[j]}.   {o}", 46 if self.land else 52, ph_ != "answer" or j == q["ans"], col, 6))
        return card("Quick quiz", BRAND, b, cw=cw, min_h=380 if self.land else 520)

    def seg_at(self, tt):
        return self.B["segs"][max(0, bisect.bisect_right(self.starts, tt) - 1)]

    def prog_at(self, tau):
        acc = 0.0
        for i, x in enumerate(self.cd):
            if tau < acc + x: return i + ease((tau - acc) / x)
            acc += x
        return float(len(self.cd))

    def animated(self, fr, seg, tt):
        S, k, N = self.S, seg["kind"], BOX * SS; U = N / 109.0
        layer = Image.new("RGBA", (N, N), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
        GW, ghost, badges = 68, (228, 216, 222), 0
        if k == "ghost":
            draw_prog(d, S, len(S), GW, ghost, U)
        elif k == "stroke":
            idx = seg["idx"]; f = ease((tt - seg["t0"]) / seg["dur"])
            draw_prog(d, S, len(S), GW, ghost, U); draw_prog(d, S[:idx], idx, GW, INK, U)
            if f > 0:
                pts = S[idx].upto(f); line(d, pts, GW, BRAND, U)
                if f < 1: circle(d, pts[-1][0] * U, pts[-1][1] * U, GW * 0.8, (255, 255, 255), BRAND, 10)
            badges = idx + 1 if f > 0 else idx
        elif k == "write":
            prog = self.prog_at((tt - seg["t0"]) % self.cycle)
            draw_prog(d, S, len(S), GW, ghost, U); draw_prog(d, S, prog, GW, BRAND, U)
        elif k == "mnemonic":
            t = clamp((tt - seg["t0"]) / seg["dur"])
            SCENES.get((self.meta["script"], self.meta["romaji"]), scene_generic)(d, S, t, U)
        small = layer.resize((BOX, BOX), Image.LANCZOS); ox, oy = self.lo["pc"][0] - BOX // 2, self.lo["pc"][1] - BOX // 2
        fr.alpha_composite(small, (ox, oy))
        if badges:
            dd = ImageDraw.Draw(fr)
            for j in range(badges):
                sx, sy = S[j].pts[0]; bx, by = ox + sx * BOX / 109 - 34, oy + sy * BOX / 109 - 34
                dd.ellipse((bx - 24, by - 24, bx + 24, by + 24), fill=BRAND)
                dd.text((bx, by), str(j + 1), font=font(32), fill=(255, 255, 255), anchor="mm")

    def frame(self, i):
        tt = i / FPS; seg = self.seg_at(tt); B, lo = self.B, self.lo
        j = min(i, B["n"] - 1); speaking, mouth = B["spk"][j] == "Mika", B["mouth"][j]
        fr = self.bg.copy(); k = seg["kind"]
        ident = (k, seg.get("i"), seg.get("shown"), seg.get("phase"), seg.get("idx"), id(seg.get("s")), id(seg.get("q")))
        if k in ANIM: self.animated(fr, seg, tt)
        else: fr.alpha_composite(self.memo(("p",) + ident, lambda: self.panel(seg)))
        bob = 6 * abs(math.sin(tt * 7)) if speaking and mouth else 2 * math.sin(tt * 2)
        s = sprite("Mika", int(mouth) if speaking else 0, (i % 72) < 3, 0.62, False)
        cd = self.memo(("c",) + ident, lambda: self.card_for(seg))
        f = min(1, (tt - seg["start"]) / 0.2)
        if f < 1:
            cd = cd.copy(); cd.putalpha(cd.getchannel("A").point(lambda v: int(v * f)))
        if self.land:
            fr.paste(s, (lo["card_cx"] - s.width // 2, int(lo["mika_y"] - bob)), s)
            fr.paste(cd, (lo["card_cx"] - cd.width // 2, lo["card_bottom"] - cd.height), cd)
        else:
            fr.paste(s, (lo["SW"] - s.width - 10, int(1190 - s.height - bob)), s)
            fr.paste(cd, ((lo["SW"] - cd.width) // 2, 1210), cd)
        if k == "think" or seg.get("timer") or (k == "quiz" and seg["phase"] == "think"):
            total = seg.get("n", 3) if k == "think" else THINK
            left = max(0.0, total - (tt - seg["t0"]))
            d = ImageDraw.Draw(fr); cx, cy = lo["timer"]; r = 70
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255), outline=BRAND, width=9)
            d.arc((cx - r, cy - r, cx + r, cy + r), -90, -90 + 360 * (left / total), fill=(255, 190, 110), width=9)
            d.text((cx, cy), str(max(1, math.ceil(left))), font=font(80), fill=INK, anchor="mm")
        return fr.convert("RGB")


def write_extras(B, outdir, stem):
    m = B["meta"]
    lines = [f"{m['title']} ({m['kana']}) | Learn {m['script'].title()} - how to read, write and remember it",
             "", f"How to read and write {m['kana']} ({m['romaji']}): sound, fonts, stroke order animation, a memory trick, real words and a quiz.", ""]
    lines += [f"{w['jp']} ({w['romaji']}) - {w['en']}" for w in B["words"]]
    lines += ["", "Stroke order data: KanjiVG (c) Ulrich Apel, CC BY-SA 3.0 - https://kanjivg.tagaini.net", "",
              f"#{m['script']} #learnjapanese #japanese #kana"]
    open(os.path.join(outdir, stem + ".description.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description="Tiny Japanese kana lesson generator")
    ap.add_argument("script"); ap.add_argument("-o", "--out", default="output")
    ap.add_argument("--format", choices=list(LAYOUTS), default="landscape")
    ap.add_argument("--rate", default="-12%"); ap.add_argument("--dummy-audio", action="store_true")
    ap.add_argument("--assets", default="assets"); ap.add_argument("--preview", metavar="DIR")
    ap.add_argument("--lean", action="store_true", help="low-memory encode for small machines")
    a = ap.parse_args()
    stem = os.path.splitext(os.path.basename(a.script))[0]
    with tempfile.TemporaryDirectory() as tmp:
        B = build(a.script, a.rate, a.dummy_audio, tmp)
        R = Renderer(B, a.format, a.assets, a.lean); lo = LAYOUTS[a.format]
        if a.preview:
            os.makedirs(a.preview, exist_ok=True); n = 0
            for seg in B["segs"]:
                times = [seg["start"] + 0.8]
                if seg["kind"] == "stroke": times = [seg["t0"] + seg["dur"] * 0.55]
                if seg["kind"] == "mnemonic": times = [seg["t0"] + seg["dur"] * x for x in (0.2, 0.5, 0.95)]
                if seg["kind"] == "write": times = [seg["t0"] + 1.2]
                for tm in times:
                    n += 1; R.frame(min(int(tm * FPS), B["n"] - 1)).save(os.path.join(a.preview, f"{n:02d}-{seg['kind']}{seg.get('idx', '')}.png"))
            print(f"Wrote {n} preview frames (length {L.fmt_time(B['total'])})"); return
        os.makedirs(a.out, exist_ok=True)
        wav = os.path.join(tmp, "final.wav"); L.write_wav(wav, B["audio"])
        out = os.path.join(a.out, stem + ".mp4")
        enc = ["-preset", "ultrafast", "-threads", "1"] if a.lean else ["-preset", "medium"]
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{lo['SW']}x{lo['SH']}",
                              "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", *enc, "-crf", "21",
                              "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-movflags", "+faststart", "-shortest", out], stdin=subprocess.PIPE)
        for i in range(B["n"]):
            p.stdin.write(R.frame(i).tobytes())
        p.stdin.close(); p.wait()
        write_extras(B, a.out, stem)
        th = R.frame(int(min(B["n"] - 1, 1.5 * FPS)))
        th.resize((1280, 720) if a.format == "landscape" else (540, 960), Image.LANCZOS).save(os.path.join(a.out, stem + ".thumbnail.png"))
        print(f"Wrote {out} ({L.fmt_time(B['total'])})")


if __name__ == "__main__":
    main()
