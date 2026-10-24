'''Atmosphere for Tiny Japanese Story: weather (rain, storm, snow), time of day and umbrellas.

Everything is drawn with Pillow inside the normal frame loop:
  parse_weather / parse_tod   - the '@weather rain' and '@time sunset' directions
  detect_weather / detect_tod - read the spoken lines, so a script that says "it's raining" gets rain by itself
  offers_umbrella             - a line like "I have an umbrella!" hands that speaker an umbrella
  frame_bg                    - colour-graded background (cached) for the weather and time of day
  draw_umbrellas / draw_precip - open umbrellas, falling rain / snow, ground ripples, lightning
'''
import math, re
import numpy as np
from PIL import Image, ImageDraw

L = None


def bind(mod):
    global L
    L = mod


OUTDOOR = {"street", "park", "sakura", "beach", "amusement", "shrine", "zoo", "airport", "town", "mountain",
           "river", "schoolyard", "busstop", "festival"}
NIGHT_SCENES = {"street", "festival"}          # drawn as night scenes already


# ------------------------------------------------------------------ directions
_WEATHER = {"clear": None, "sunny": None, "fine": None, "dry": None, "none": None, "off": None, "stop": None,
            "stops": None, "stopped": None, "rain": "rain", "rainy": "rain", "raining": "rain", "drizzle": "rain",
            "shower": "rain", "showers": "rain", "storm": "storm", "stormy": "storm", "thunderstorm": "storm",
            "downpour": "storm", "pouring": "storm", "heavy rain": "storm", "snow": "snow", "snowy": "snow",
            "snowing": "snow"}
_TOD = {"morning": "morning", "dawn": "morning", "sunrise": "morning", "day": "day", "daytime": "day", "noon": "day",
        "afternoon": "day", "evening": "sunset", "sunset": "sunset", "dusk": "sunset", "night": "night",
        "midnight": "night"}


def parse_weather(text):
    t = re.sub(r"^(starts?|begins?)( to)?\s+", "", text.strip().lower().rstrip("."))
    if t not in _WEATHER:
        raise ValueError(f"unknown weather '{text}'. Use: rain, storm, snow or clear")
    return _WEATHER[t]


def parse_tod(text):
    t = text.strip().lower().rstrip(".")
    if t not in _TOD:
        raise ValueError(f"unknown time of day '{text}'. Use: morning, day, sunset or night")
    return _TOD[t]


# ------------------------------------------------------------------ reading the story text
def _jp(ln):
    return re.sub(r"[\s、。！？!?「」・…～~]", "", ln.get("jp") or "")


_RAIN_ON = re.compile(r"\braining\b|\brainy\b|\bpouring\b|\bdrizzl\w+|\bthe rain\b|\bin the rain\b|\bit rains\b|\bheavy rain\b|"
                      r"\bdownpour\b|\b(?:started|starts|began|begins) to rain\b|\bit'?s rain")
_RAIN_OFF = re.compile(r"\brain\s+(?:has\s+|had\s+|just\s+)?(?:stopped|ended|is over|is gone|has gone|cleared|let up|is clearing)|"
                       r"\b(?:stopped|stops|stop)\s+raining\b|\bno longer\s+(?:raining|rain)|\b(?:not|isn'?t|wasn'?t|aren'?t)\s+raining|"
                       r"\bthe sun is (?:out|shining)|\bsunny\b|\brainbow\b|\bclear(?:ed)?\s+up\b|\brain is over\b|\bno more rain\b")
_STORM = re.compile(r"\bstorm|\bheavy\b|\bpouring\b|\bdownpour|\bthunder")
_SNOW_ON = re.compile(r"\bsnowing\b|\bsnowy\b|\bit'?s snow|\bsnow(?:flakes?)? (?:is|are) falling|\b(?:started|starts|began|begins) to snow\b|\bfirst snow\b")
_SNOW_OFF = re.compile(r"\bsnow\s+(?:has\s+)?stopped|\bstopped snowing\b|\bsnow is gone\b|\bsnow melted\b")
_JP_RAIN = re.compile(r"雨|あめ(?:が|は)?(?:ふっ|ふり|ふる|ふれ)|ふってきた|ざあざあ|ざーざー")
_JP_STOP = re.compile(r"やんだ|やんで|あがった|あがって|はれた|はれて|はれだ|はれです|晴れ|にじ(?:だ|が|を|です|ね|よ)|虹")
_JP_SNOW = re.compile(r"雪|ゆきが(?:ふっ|ふり|ふる)")


def detect_weather(ln, cur):
    '''Weather after this spoken line (None = dry). cur is the weather before it.'''
    en = (ln.get("en") or "").lower()
    jp = _jp(ln)
    if _SNOW_OFF.search(en):
        return None if cur == "snow" else cur
    if _SNOW_ON.search(en) or _JP_SNOW.search(jp):
        return "snow"
    if _RAIN_OFF.search(en) or _JP_STOP.search(jp):
        return None if cur in ("rain", "storm") else cur
    if _RAIN_ON.search(en) or _JP_RAIN.search(jp):
        return "storm" if _STORM.search(en) else "rain"
    return cur


_TOD_RULES = [
    ("night", re.compile(r"\bgood night\b|\btonight\b|\bat night\b|\bnight\b|\bmidnight\b"), re.compile(r"よる|夜|おやすみ|こんばんは|こんや")),
    ("sunset", re.compile(r"\bsunset\b|\bevening\b|\bdusk\b|\bsun is setting\b"), re.compile(r"ゆうがた|夕方|ゆうやけ|ゆうひ")),
    ("morning", re.compile(r"\bgood morning\b|\bthis morning\b|\bmorning\b|\bbreakfast\b|\bsunrise\b"), re.compile(r"おはよう|あさ|朝")),
    ("day", re.compile(r"\bafternoon\b|\bnoon\b|\blunch\b"), re.compile(r"ひる|ごご|お昼")),
]


def detect_tod(ln):
    en = (ln.get("en") or "").lower()
    jp = _jp(ln)
    for name, ren, rjp in _TOD_RULES:
        if ren.search(en) or rjp.search(jp):
            return name
    return None


_UMB_YES = re.compile(r"\b(?:i have|i've got|i got|i brought|i bring|i've brought|here'?s|here is|my|take|use|share|under)\b[^.?!]*\bumbrella\b|"
                      r"\bumbrella\b[^.?!]*\b(?:for you|with you|together|with me|to share)\b|\bhave an umbrella\b")
_UMB_NO = re.compile(r"\bforgot\b|\bdon'?t have\b|\bdidn'?t (?:bring|have)\b|\bno umbrella\b|\bwithout\b|\bdo you have\b|\bhave you got\b|\bleft (?:my|the) umbrella")
_UMB_JP = re.compile(r"(?:かさ|傘).{0,6}(?:あり|ある|もって|かし|つかっ|いっしょ|はい)|いっしょに.{0,4}(?:かさ|傘)|(?:かさ|傘)を(?:もって|さして|ひらい)")
_UMB_JP_NO = re.compile(r"ありません|ないです|わすれ|もっていません|ない(?:よ|ね|な)")


def offers_umbrella(ln):
    en = (ln.get("en") or "").lower()
    if en and _UMB_YES.search(en) and not _UMB_NO.search(en):
        return True
    jp = _jp(ln)
    return bool(_UMB_JP.search(jp) and not _UMB_JP_NO.search(jp))


# ------------------------------------------------------------------ colour grading (cached per scene / time / weather)
def _tint(a, scene, tod, kind, sky):
    '''a: float array (h, w, 3). sky=True for full backgrounds (adds sky gradients), False for the foreground strip.'''
    out = scene in OUTDOOR
    h = a.shape[0]
    if tod == "morning" and out:
        a = a * np.array([1.03, 1.0, 0.94]) + np.array([8, 4, 0])
    elif tod == "sunset":
        if out:
            a = a * np.array([1.0, 0.86, 0.72])
            if sky:
                g = np.linspace(0.45, 0.0, h)[:, None, None]
                a = a * (1 - g) + np.array([255, 150, 96]) * g
            else:
                a = a * 0.9 + np.array([255, 150, 96]) * 0.1
        else:
            a = a * np.array([1.0, 0.92, 0.82])
    elif tod == "night" and scene not in NIGHT_SCENES:
        a = (a * np.array([0.42, 0.48, 0.70]) + np.array([2, 6, 22])) if out else (a * np.array([0.66, 0.70, 0.84]))
    if kind in ("rain", "storm") and out:
        storm = kind == "storm"
        s = 0.42 if storm else 0.30
        gray = a.mean(axis=2, keepdims=True)
        a = a * (1 - s) + gray * s
        dk = 0.30 if storm else 0.16
        a = a * (1 - dk) + np.array([48, 58, 78]) * dk
        if sky:
            fade = np.clip(1 - np.arange(h) / 560.0, 0, 1)[:, None, None] * (0.55 if storm else 0.42)
            a = a * (1 - fade) + np.array([116, 126, 146]) * fade
    elif kind == "snow" and out:
        gray = a.mean(axis=2, keepdims=True)
        a = a * 0.80 + gray * 0.10
        a = a * 0.90 + np.array([200, 214, 236]) * 0.10
    return a


def grade(img, scene, tod, kind):
    '''Graded copy of a full RGB background. Stars and a moon are added for night outdoors.'''
    if tod in (None, "day") and not kind:
        return img
    a = _tint(np.asarray(img.convert("RGB"), dtype=np.float32), scene, tod, kind, True)
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    if tod == "night" and scene in OUTDOOR and scene not in NIGHT_SCENES and not kind:
        _stars(out, np.asarray(img.convert("RGB"), dtype=np.float32))
    return out


def grade_strip(strip, scene, tod, kind):
    if tod in (None, "day") and not kind:
        return strip
    rgb = np.asarray(strip.convert("RGB"), dtype=np.float32)
    a = np.clip(_tint(rgb, scene, tod, kind, False), 0, 255).astype(np.uint8)
    out = Image.fromarray(a).convert("RGBA")
    out.putalpha(strip.getchannel("A"))
    return out


def _stars(img, orig):
    '''Dots only where the sky is: a pixel counts as sky when it matches the median colour of its row.'''
    import random
    rng = random.Random(5)
    d = ImageDraw.Draw(img)
    med = np.median(orig[:480], axis=1)
    for _ in range(90):
        x, y = rng.randint(30, L.W - 30), rng.randint(20, 460)
        if np.abs(orig[y, x] - med[y]).max() > 14:
            continue
        r = rng.choice((2, 3, 3, 4))
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 236))
    mx, my = 1560, 190
    if np.abs(orig[my, mx] - med[my]).max() <= 14:
        sky = tuple(int(v) for v in img.getpixel((mx + 130, my)))
        d.ellipse((mx - 60, my - 60, mx + 60, my + 60), fill=(255, 246, 214))
        d.ellipse((mx - 28, my - 70, mx + 92, my + 50), fill=sky)


def weather_state(seg, tt):
    '''(kind, strength 0..1) for this segment at time tt, fading in/out over 0.9 s when the weather changes.'''
    new, old = seg.get("weather"), seg.get("prev_weather")
    if new == old:
        return (new, 1.0) if new else (None, 0.0)
    u = min(1.0, max(0.0, (tt - seg["start"]) / 0.9))
    if new is None:
        return (old, 1 - u) if u < 1 else (None, 0.0)
    if old is None:
        return (new, u)
    return (new, 1.0)


def frame_bg(R, name, variant, bg, fg, seg, tt):
    '''(frame, foreground strip) for this moment: the scene background graded for time of day and weather.'''
    cache = R.__dict__.setdefault("_atm", {})
    tod = seg.get("tod")
    kind, k = weather_state(seg, tt)

    def graded(kd):
        key = (name, variant, tod, kd)
        if key not in cache:
            cache[key] = (grade(bg, name, tod, kd), grade_strip(fg, name, tod, kd))
        return cache[key]
    cbg, cfg = graded(None)
    if kind and name in OUTDOOR and k > 0.01:
        wbg, wfg = graded(kind)
        fr = wbg.copy() if k >= 0.999 else Image.blend(cbg, wbg, k)
        return fr, (wfg if k >= 0.5 else cfg)
    return cbg.copy(), cfg


# ------------------------------------------------------------------ umbrellas
_UMB_COLORS = {"Mika": (232, 100, 130), "Alex": (72, 128, 196)}


def _canopy(d, cx, rim, R, h, col):
    c2 = tuple(int(v * 0.45 + 255 * 0.55) for v in col)
    dark = tuple(int(v * 0.62) for v in col)
    n = 8
    xs = [cx - R + 2 * R * k / n for k in range(n + 1)]
    apex = (cx, rim - h)

    def rib(xe):
        return [(apex[0] + (xe - apex[0]) * t, apex[1] + (rim - apex[1]) * t ** 0.7) for t in np.linspace(0, 1, 9)]
    d.pieslice((cx - R, rim - h, cx + R, rim + h), 180, 360, fill=col)
    for k in range(n):                                   # alternate panels
        if k % 2:
            d.polygon(rib(xs[k]) + rib(xs[k + 1])[::-1], fill=c2)
    for k in range(n):                                   # scalloped lower edge
        r = R / n
        mid = (xs[k] + xs[k + 1]) / 2
        d.pieslice((mid - r, rim - r * 0.55, mid + r, rim + r * 0.55), 0, 180, fill=c2 if k % 2 else col)
    for xe in xs[1:-1]:                                   # ribs
        d.line(rib(xe), fill=dark, width=3)
    d.arc((cx - R, rim - h, cx + R, rim + h), 180, 360, fill=dark, width=5)
    d.line([apex, (apex[0], apex[1] - 16)], fill=(70, 56, 50), width=7)
    d.ellipse((cx - R * 0.42, rim - h * 0.86, cx - R * 0.14, rim - h * 0.66), fill=tuple(min(255, int(v * 0.4 + 255 * 0.6)) for v in col))


def draw_umbrellas(fr, lay):
    '''Open umbrellas behind the characters. Returns the sheltered areas (cx, R, apex_y, rim_y) so no rain falls there.'''
    d = ImageDraw.Draw(fr)
    shelters = []
    for h in [e for e in lay if e["open"]]:
        members = [e for e in lay if abs(e["cx"] - h["cx"]) <= 430]
        xs = [e["cx"] for e in members]
        side = -1 if h["mirror"] else 1
        cx = sum(xs) / len(xs) + side * 40
        R = max(235.0, (max(xs) - min(xs)) / 2 + 205)
        rim = h["y"] + 62
        hgt = min(0.5 * R, rim - 8)
        hand = (h["cx"] + side * 64, h["y"] + 404)
        d.line([(cx, rim - hgt), hand], fill=(86, 66, 58), width=8)
        _canopy(d, cx, rim, R, hgt, _UMB_COLORS.get(h["nm"], (120, 110, 170)))
        shelters.append((cx, R, rim - hgt, rim))
    return shelters


# ------------------------------------------------------------------ rain and snow
_cache = {}


def _drops(kind):
    if kind not in _cache:
        r = np.random.RandomState({"rain": 11, "storm": 12, "snow": 13}[kind])
        n = {"rain": 190, "storm": 300, "snow": 150}[kind]
        _cache[kind] = dict(n=n, x=r.uniform(-250, L.W + 50, n), y=r.uniform(0, 1, n), sp=r.uniform(0.8, 1.3, n),
                            ln=r.uniform(0.6, 1.4, n), land=r.uniform(0, 1, n), ph=r.uniform(0, 6.28, n), far=r.rand(n) < 0.55,
                            rx=r.uniform(40, L.W - 40, 40), ry=r.uniform(0, 1, 40), rp=r.uniform(0, 1, 40))
    return _cache[kind]


def _sheltered(x, y, shelters):
    m = np.zeros(len(x), bool)
    for cx, R, apex, rim in shelters:
        hgt = max(1.0, rim - apex)
        w = np.where(y >= rim, R, R * np.sqrt(np.clip(1 - ((rim - y) / hgt) ** 2, 0, 1)))
        m |= (np.abs(x - cx) < w * 0.97) & (y > apex)
    return m


def draw_precip(fr, tt, kind, k, shelters):
    d = ImageDraw.Draw(fr)
    P = _drops(kind)
    W, H, FY = L.W, L.H, L.FLOOR_Y
    show = max(1, int(P["n"] * min(1.0, k)))
    if kind == "storm" and tt > 1 and (tt % 6.5) < 0.10:                  # lightning flash
        fr.paste(Image.blend(fr, Image.new("RGB", fr.size, (255, 255, 255)), 0.45), (0, 0))
    if kind == "snow":
        sp = 120 * P["sp"][:show]
        y = (P["y"][:show] * (H + 40) + tt * sp) % (H + 40) - 20
        x = np.mod(P["x"][:show] + 30 * np.sin(tt * 0.9 + P["ph"][:show]) + 250, W + 300) - 250
        ok = ~_sheltered(x, y, shelters)
        for i in np.nonzero(ok)[0]:
            r = 3 + 4 * P["ln"][i] / 1.4
            d.ellipse((x[i] - r, y[i] - r, x[i] + r, y[i] + r), fill=(250, 252, 255))
        return
    storm = kind == "storm"
    speed = (2000 if storm else 1500) * P["sp"][:show]
    land = FY + 40 + P["land"][:show] * (H - FY - 60)
    span = land + 80
    ypos = (P["y"][:show] * span + tt * speed) % span - 80
    slant = -0.30 if storm else -0.16
    x = P["x"][:show] + slant * ypos
    length = np.where(P["far"][:show], 34, 58) * P["ln"][:show]
    nrm = math.sqrt(1 + slant * slant)
    ok = ~_sheltered(x, ypos, shelters)
    for i in np.nonzero(ok)[0]:
        x1, y1 = x[i], ypos[i]
        x0, y0 = x1 - slant / nrm * length[i], y1 - 1 / nrm * length[i]
        if P["far"][i]:
            d.line([(x0, y0), (x1, y1)], fill=(190, 208, 232), width=2)
        else:
            d.line([(x0, y0), (x1, y1)], fill=(218, 232, 250), width=3)
    for i in range(int(40 * min(1.0, k))):                                   # ripples on the ground
        ph = (tt * 1.3 + P["rp"][i]) % 1.0
        if ph > 0.85:
            continue
        rx, ry = P["rx"][i], FY + 36 + P["ry"][i] * (H - FY - 90)
        if _sheltered(np.array([rx]), np.array([ry]), shelters)[0]:
            continue
        rad = 8 + 34 * ph
        c = tuple(int(a + (b - a) * ph) for a, b in zip((226, 238, 250), (176, 182, 200)))
        d.ellipse((rx - rad, ry - rad * 0.28, rx + rad, ry + rad * 0.28), outline=c, width=2)
