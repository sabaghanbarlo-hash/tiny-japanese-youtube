"""Acting layer for Tiny Japanese Story (v2).

Stage directions in the [story] section (lines starting with '>' or '&') become keyframes: walking,
running, expressions, held items (cotton candy, balloon...), eating, giving, rides (carousel, ferris
wheel). Every frame asks Stage.state() what each character is doing. Places have named spots
("cotton candy stall") that directions can walk to. Characters are drawn by rig(): the same Mika and
Alex art as lesson.py, parameterised (walk cycle, waving arm, expressions, held item).
"""
import functools, math, re
from PIL import Image, ImageDraw, ImageOps
import atmos as AT
import scenery as SC

L = None            # the lesson module, set by bind()
SPEED = 380.0       # px / second when walking
RUN_SPEED = 720.0
EXPRS = {"neutral": "neutral", "confused": "confused", "puzzled": "confused", "nervous": "confused",
         "lost": "confused", "surprised": "surprised", "shocked": "surprised", "amazed": "surprised",
         "happy": "happy", "excited": "happy", "smiling": "happy", "glad": "happy", "laughing": "happy",
         "sad": "sad", "worried": "sad", "disappointed": "sad", "shy": "shy", "embarrassed": "shy"}

# ------------------------------------------------------------------ items
EDIBLE = {"cotton_candy", "ice_cream", "popcorn"}
ITEMS = {"cotton_candy", "ice_cream", "balloon", "ticket", "drink", "bag", "book", "popcorn", "plush", "umbrella"}
ITEM_ALIASES = {"cotton candy": "cotton_candy", "candyfloss": "cotton_candy", "candy floss": "cotton_candy",
                "fairy floss": "cotton_candy", "ice cream": "ice_cream", "icecream": "ice_cream", "ice-cream": "ice_cream",
                "tickets": "ticket", "juice": "drink", "soda": "drink", "tea": "drink", "coffee": "drink", "cup": "drink",
                "shopping bag": "bag", "gift": "bag", "present": "bag", "teddy": "plush", "teddy bear": "plush",
                "prize": "plush", "stuffed animal": "plush", "toy": "plush", "bear": "plush", "plushie": "plush",
                "balloons": "balloon", "brolly": "umbrella", "umbrellas": "umbrella", "rain umbrella": "umbrella", "parasol": "umbrella"}


def item_name(text):
    s = text.strip().lower()
    for _ in range(2):
        s = re.sub(r"^up\s+", "", s)
        s = re.sub(r"^(a|an|the|some|her|his|their|another|one)\s+", "", s)
    key = ITEM_ALIASES.get(s, s.replace(" ", "_"))
    if key not in ITEMS:
        raise ValueError(f"unknown item '{text}'. Items: {', '.join(sorted(i.replace('_', ' ') for i in ITEMS))}")
    return key


# ------------------------------------------------------------------ places: named spots and rides
LANDMARKS = {
    "amusement": {"entrance": 0.07, "gate": 0.07, "ticket booth": 0.17, "carousel": 0.36, "merry-go-round": 0.36,
                  "cotton candy stall": 0.58, "cotton candy": 0.58, "snack stall": 0.58, "prize stall": 0.72,
                  "game stall": 0.72, "balloon stall": 0.72, "ferris wheel": 0.88, "bench": 0.47},
    "shrine": {"torii gate": 0.5, "torii": 0.5, "gate": 0.5, "offering box": 0.2, "lantern": 0.78, "steps": 0.5},
    "zoo": {"entrance": 0.08, "giraffe": 0.3, "elephant": 0.72, "fence": 0.5},
    "aquarium": {"big tank": 0.5, "tank": 0.5, "jellyfish": 0.2, "shark": 0.8, "entrance": 0.08},
    "classroom": {"door": 0.1, "blackboard": 0.5, "desk": 0.35},
    "cafe": {"counter": 0.8, "window": 0.45, "door": 0.1},
    "station": {"platform": 0.5, "ticket gate": 0.2, "ticket machine": 0.12},
    "store": {"register": 0.8, "shelf": 0.5, "door": 0.1},
}
RIDES = {"amusement": {"carousel": 0.36, "ferris": 0.88}}
RIDE_SECONDS = {"carousel": 5.0, "ferris": 7.0}


def ride_kind(arg):
    a = re.sub(r"^(on\s+)?(the\s+)?", "", arg.strip().lower())
    m = re.search(r"\bfor\s+(\d+(?:\.\d+)?)", a)
    secs = float(m[1]) if m else None
    a = re.sub(r"\bfor\s+.*$", "", a).strip()
    if any(k in a for k in ("carousel", "merry", "horse")):
        kind = "carousel"
    elif any(k in a for k in ("ferris", "wheel")):
        kind = "ferris"
    else:
        raise ValueError(f"can't ride '{arg}'. Rides: carousel, ferris wheel")
    return kind, secs or RIDE_SECONDS[kind]


def bind(mod):
    global L
    L = mod
    SC.bind(mod); AT.bind(mod)
    L.SCENES.update(NEW_SCENES); L.SCENES.update(SC.SCENES)
    L.SCENE_KEYWORDS.update(NEW_KEYWORDS); L.SCENE_KEYWORDS.update(SC.KEYWORDS)
    L.SCENE_KEYWORDS["street"] = [k for k in L.SCENE_KEYWORDS["street"] if k not in ("まつり", "祭り", "festival")]
    L.SCENE_ALIASES.update(NEW_ALIASES); L.SCENE_ALIASES.update(SC.ALIASES)
    LANDMARKS.update(SC.LANDMARKS); SCENE_DRAW.update(SC.DRAW)
    L.SCENE_ORDER[:] = list(L.SCENES)


# ------------------------------------------------------------------ directive parsing
def _names():
    return {k.lower(): k for k in L.CHARS}


VERBS = {}
for _v, _ws in {
    "enter": "enters enter", "walk": "walks walk goes go moves move steps step heads", "run": "runs run dashes dash hurries hurry rushes rush",
    "exit": "exits exit leaves leave", "look": "looks look feels feel seems seem is gets_feeling",
    "face": "faces face turns turn", "wave": "waves wave", "hop": "jumps jump hops hop",
    "hold": "holds hold gets get takes take grabs grab picks pick has have carries carry opens open raises raise",
    "buy": "buys buy", "eat": "eats eat licks lick nibbles nibble", "drink": "drinks drink sips sip",
    "drop": "drops drop finishes finish puts put throws throw closes close folds fold", "give": "gives give hands hand passes pass shares share",
    "ride": "rides ride", "laugh": "laughs laugh giggles giggle", "nod": "nods nod", "cheer": "cheers cheer",
}.items():
    for _w in _ws.split():
        VERBS[_w] = _v


def parse_dir(text):
    """'Mika enters left' -> (['Mika'], 'enter', 'left').  Raises ValueError with a friendly message."""
    t = text.strip().rstrip(".")
    m = re.match(r"^(wait|pause)\s*([\d.]*)\s*s?$", t, re.I)
    if m:
        return [], "wait", m[2] or "1"
    names = _names()
    m = re.match(r"^(%s|both|everyone|they)\s+([A-Za-z]+)\s*(.*)$" % "|".join(names), t, re.I)
    if not m:
        raise ValueError(f"can't read the stage direction '{text}'. Use e.g. 'Mika enters left', 'Alex walks to center', "
                         f"'Mika looks confused', 'Mika buys cotton candy', 'both ride the carousel', 'wait 1'")
    who = m[1].lower()
    whos = list(L.CHARS) if who in ("both", "everyone", "they") else [names[who]]
    verb_w, arg = m[2].lower(), m[3].strip()
    if verb_w not in VERBS:
        raise ValueError(f"unknown action '{verb_w}' in '{text}'. Actions: enters, walks to, runs to, exits, looks <feeling>, faces, "
                         f"waves, jumps, laughs, nods, cheers, holds/buys <item>, eats, drinks, drops, gives <item> to <name>, rides, wait")
    verb = VERBS[verb_w]
    if verb == "look":
        a = re.sub(r"^(at\s+)", "", arg, flags=re.I).strip()
        if arg.lower().startswith("at "):
            verb, arg = "face", a
        else:
            if a.lower() not in EXPRS:
                raise ValueError(f"unknown feeling '{arg}' in '{text}'. Feelings: {', '.join(sorted(set(EXPRS)))}")
            arg = a.lower()
    elif verb in ("hold", "buy"):
        arg = item_name(arg)
    elif verb == "eat":
        if arg and arg.lower() not in ("it", "some", "them"):
            arg = item_name(arg)
            if arg not in EDIBLE:
                raise ValueError(f"'{text}': you can't eat {arg.replace('_', ' ')}. Edible: cotton candy, ice cream, popcorn (use 'drinks' for a drink)")
        else:
            arg = ""
    elif verb == "give":
        mm = re.match(r"^(.*?)\s*\bto\s+(\w+)$", arg, re.I)
        if not mm or mm[2].lower() not in names:
            raise ValueError(f"'{text}': use 'gives <item> to <name>', e.g. 'Mika gives the ticket to Alex'")
        ip = mm[1].strip().lower()
        arg = ("" if ip in ("", "it", "them", "one") else item_name(ip)) + "|" + names[mm[2].lower()]
    elif verb == "ride":
        ride_kind(arg)
    return whos, verb, arg


def check_dir(text):
    parse_dir(text)


# ------------------------------------------------------------------ the stage
def _smooth(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


class Stage:
    def __init__(self):
        W = L.W
        self.W = W
        self.scene = None
        self.home = {nm: c["x"] + L.SPRITE_W // 2 for nm, c in L.CHARS.items()}
        self.dflt_face = {nm: (1 if self.home[nm] < W / 2 else -1) for nm in L.CHARS}
        mk = lambda: {nm: [] for nm in L.CHARS}
        self.moves, self.vis, self.expr, self.face = mk(), mk(), mk(), mk()
        self.wave, self.hop, self.item, self.eat, self.rides = mk(), mk(), mk(), mk(), mk()
        self.umb = mk()                              # umbrella in hand (separate from the item slot)
        self.weather, self.tod = None, None          # None | rain | storm | snow  /  None | morning | day | sunset | night
        self.explicit = dict(weather=False, tod=False, umb=False)
        self.has_rain, self.title = False, ""
        self.visits, self._scene_seen, self._w_mark = {}, None, None
        self.pops = []                               # (t0, t1, name, text)
        self.start_vis = {nm: True for nm in L.CHARS}
        self.start_x = dict(self.home)

    # -- setup
    def prescan(self, lines):
        seen = set()
        for ln in lines:
            for item in (ln.get("dirs") or []) + (ln.get("after") or []):
                if item[0] != "dir":
                    continue
                whos, verb, _ = parse_dir(item[1])
                for nm in whos:
                    if nm not in seen:
                        seen.add(nm)
                        if verb == "enter":
                            self.start_vis[nm] = False
                            self.start_x[nm] = self._off(nm, "left" if self.home[nm] < self.W / 2 else "right")

    def _off(self, nm, side):
        return -L.SPRITE_W if side == "left" else self.W + L.SPRITE_W

    def setup(self, meta, lines):
        '''Weather / time of day / umbrella bookkeeping that needs the whole script.'''
        self.title = meta.get("title", "")
        try:
            if meta.get("weather"):
                self.weather = AT.parse_weather(meta["weather"]); self.explicit["weather"] = True
            if meta.get("time"):
                self.tod = AT.parse_tod(meta["time"]); self.explicit["tod"] = True
        except ValueError as e:
            L.die(f"header: {e}")
        for ln in lines:
            for item in (ln.get("dirs") or []) + (ln.get("after") or []):
                if item[0] == "weather":
                    self.explicit["weather"] = True
                elif item[0] == "time":
                    self.explicit["tod"] = True
                elif item[0] == "dir" and re.search(r"umbrella|brolly", item[1], re.I):
                    self.explicit["umb"] = True
        w = self.weather
        self.has_rain = bool(w)
        for ln in lines:
            for item in ln.get("dirs") or []:
                if item[0] == "weather":
                    w = item[1]; self.has_rain = self.has_rain or bool(w)
            if not self.explicit["weather"]:
                w = AT.detect_weather(ln, w); self.has_rain = self.has_rain or bool(w)
            for item in ln.get("after") or []:
                if item[0] == "weather":
                    w = item[1]; self.has_rain = self.has_rain or bool(w)
        self._w_mark = self.weather

    def set_atmos(self, kind, val):
        if kind == "weather":
            self.weather = val
        else:
            self.tod = val

    def auto_stop(self, ln):
        '''Just before a line is spoken (after its directions): "the rain stopped" stops the rain.'''
        if not self.explicit["weather"]:
            w = AT.detect_weather(ln, self.weather)
            if w is None:
                self.weather = None

    def auto_line(self, ln, t):
        '''At the start of a spoken line's directions: rain starts, the time of day moves on, an umbrella appears.'''
        if not self.explicit["weather"]:
            w = AT.detect_weather(ln, self.weather)
            if w is not None:
                self.weather = w
        if not self.explicit["tod"]:
            self.tod = AT.detect_tod(ln) or self.tod
        if not self.explicit["umb"] and self.has_rain and AT.offers_umbrella(ln):
            nm = ln["speaker"]
            if not self._last(self.umb[nm], t, False):
                self.umb[nm].append((t, True))

    def look(self, scene, bump=True, settle=False):
        '''Weather, time of day and background variant for the segment that is about to be marked.'''
        if bump and scene != self._scene_seen:
            self.visits[scene] = self.visits.get(scene, 0) + 1
            self._scene_seen = scene
        kw = dict(weather=self.weather, prev_weather=self.weather if settle else self._w_mark, tod=self.tod,
                  variant=SC.variant_of(self.title, scene, self.visits.get(scene, 1)))
        self._w_mark = self.weather
        return kw

    # -- queries
    def x_at(self, nm, t):
        x = self.start_x[nm]
        for t0, t1, x0, x1 in self.moves[nm]:
            if t < t0:
                break
            x = x1 if t >= t1 else x0 + (x1 - x0) * _smooth((t - t0) / max(1e-6, t1 - t0))
        return x

    def vis_at(self, nm, t):
        v = self.start_vis[nm]
        for tt, b in self.vis[nm]:
            if tt <= t:
                v = b
        return v

    def _last(self, lst, t, default):
        v = default
        for it in lst:
            if it[0] <= t:
                v = it[1]
        return v

    def item_at(self, nm, t):
        it, bite = None, 0
        for tt, name, b in self.item[nm]:
            if tt <= t:
                it, bite = name, b
        return it, bite

    def state(self, nm, t):
        speed = 0.0
        for t0, t1, x0, x1 in self.moves[nm]:
            if t0 <= t < t1 and abs(x1 - x0) > 1:
                speed = abs(x1 - x0) / max(1e-6, t1 - t0)
        hop = next((((t - a) / (b - a), amp) for a, b, amp in self.hop[nm] if a <= t < b), None)
        ride = next(((a, b, kind, idx) for a, b, kind, idx in self.rides[nm] if a <= t < b), None)
        face = self._last(self.face[nm], t, self.dflt_face[nm])
        item, bite = self.item_at(nm, t)
        return dict(vis=self.vis_at(nm, t), x=self.x_at(nm, t), walking=speed > 0, speed=speed,
                    wave=any(a <= t < b for a, b in self.wave[nm]), hop=hop, ride=ride,
                    pop=next((txt for a, b, n, txt in self.pops if n == nm and a <= t < b), None),
                    expr=self._last(self.expr[nm], t, "neutral"), face=face, mirror=(face != self.dflt_face[nm]),
                    item=item, bite=bite, eating=any(a <= t < b for a, b in self.eat[nm]), umb=self._last(self.umb[nm], t, False))

    # -- compile directives into keyframes
    def _target(self, nm, arg, t):
        a = re.sub(r"^(to\s+)?(the\s+)?", "", arg.strip().lower()).strip()
        W = self.W
        names = _names()
        lm = LANDMARKS.get(self.scene, {})
        if a in lm:
            return lm[a] * W
        m = re.match(r"^(next to|beside|near)\s+(\w+)$", a)
        if m and m[2] in names:
            ox, cur = self.x_at(names[m[2]], t), self.x_at(nm, t)
            return ox + (-380 if cur < ox else 380)
        if a in names:
            ox = self.x_at(names[a], t)
            return ox + (-380 if self.x_at(nm, t) < ox else 380)
        table = {"left": 0.2, "center": 0.5, "centre": 0.5, "middle": 0.5, "right": 0.8, "front": 0.5,
                 "far left": 0.1, "far right": 0.9, "desk": 0.35, "door": 0.12}
        if a in table:
            return table[a] * W
        if a in ("home", "", "seat", "spot"):
            return self.home[nm]
        m = re.match(r"^(\d+)\s*%?$", a)
        if m:
            return int(m[1]) / 100 * W
        for name, frac in lm.items():           # fuzzy: 'the cotton candy' ~ 'cotton candy stall'
            if len(a) >= 4 and (a in name or name in a):
                return frac * W
        spots = ", ".join(sorted(lm)) if lm else "none in this scene"
        raise ValueError(f"don't know the place '{arg}' (scene: {self.scene}). Use left, center, right, home, 'next to Alex', a percent, "
                         f"or a spot of this scene: {spots}")

    def _move(self, nm, t, x1, dur=None, speed=SPEED):
        x0 = self.x_at(nm, t)
        d = abs(x1 - x0)
        dur = dur or max(0.6, d / speed)
        self.moves[nm].append((t, t + dur, x0, x1))
        if d > 1:
            self.face[nm].append((t, 1 if x1 > x0 else -1))
        return dur

    def _one(self, text, t):
        whos, verb, arg = parse_dir(text)
        if verb == "wait":
            return float(arg)
        dur = 0.0
        for k, nm in enumerate(whos):
            spread = (k - (len(whos) - 1) / 2) * 230 if len(whos) > 1 else 0    # 'both' do not stand on the same pixel
            if verb == "enter":
                a = arg.lower()
                side = "left" if re.search(r"\bleft\b", a) else "right" if re.search(r"\bright\b", a) else \
                    ("left" if self.home[nm] < self.W / 2 else "right")
                m = re.search(r"\bto\s+(.+)$", a)
                dest = (self._target(nm, m[1], t) + (0 if m[1].strip().lower() == "home" else spread)) if m else self.home[nm]
                x_now = self.x_at(nm, t)
                if (not self.vis_at(nm, t)) or x_now < -L.SPRITE_W * 0.5 or x_now > self.W + L.SPRITE_W * 0.5:
                    self.moves[nm].append((t, t, x_now, self._off(nm, side)))   # start from off-screen
                    self.vis[nm].append((t, True))
                d = self._move(nm, t, dest)
                end = t + d
                dur = max(dur, d)
                for other in L.CHARS:
                    if other != nm and self.vis_at(other, end) and abs(self.x_at(other, end) - dest) > 5:
                        self.face[nm].append((end, 1 if self.x_at(other, end) > dest else -1))
                        self.face[other].append((end, 1 if dest > self.x_at(other, end) else -1))
                        self.pops.append((end, end + 1.0, other, "!"))
            elif verb in ("walk", "run"):
                at = re.sub(r"^(to\s+)?(the\s+)?", "", arg.strip().lower()).strip()
                nx = self._target(nm, arg, t) + (0 if at in ("home", "") or at.startswith(("next to", "beside", "near")) or at in _names() else spread)
                d = self._move(nm, t, nx, speed=RUN_SPEED if verb == "run" else SPEED)
                dur = max(dur, d)
            elif verb == "exit":
                a = arg.lower()
                side = "left" if "left" in a else "right" if "right" in a else \
                    ("left" if self.x_at(nm, t) < self.W / 2 else "right")
                d = self._move(nm, t, self._off(nm, side))
                self.vis[nm].append((t + d, False)); self.expr[nm].append((t + d, "neutral"))
                dur = max(dur, d)
            elif verb == "look":
                self.expr[nm].append((t, EXPRS[arg])); dur = max(dur, 1.3)
            elif verb == "face":
                a = arg.lower().strip()
                names = _names()
                if a in names:
                    f = 1 if self.x_at(names[a], t) > self.x_at(nm, t) else -1
                elif a in ("left", "right"):
                    f = -1 if a == "left" else 1
                else:
                    raise ValueError(f"'{text}': face left, right or a name")
                self.face[nm].append((t, f)); dur = max(dur, 0.4)
            elif verb == "wave":
                self.wave[nm].append((t, t + 1.6)); dur = max(dur, 1.6)
            elif verb == "hop":
                self.hop[nm].append((t, t + 0.9, 150)); dur = max(dur, 0.9)
            elif verb == "cheer":
                self.hop[nm].append((t, t + 0.8, 150)); self.expr[nm].append((t, "happy")); self.wave[nm].append((t, t + 1.4))
                dur = max(dur, 1.4)
            elif verb == "laugh":
                self.expr[nm].append((t, "happy"))
                self.hop[nm].append((t, t + 0.4, 40)); self.hop[nm].append((t + 0.45, t + 0.85, 40)); dur = max(dur, 1.3)
            elif verb == "nod":
                self.hop[nm].append((t, t + 0.35, 20)); self.hop[nm].append((t + 0.4, t + 0.75, 20)); dur = max(dur, 0.9)
            elif verb in ("hold", "buy") and arg == "umbrella":
                self.umb[nm].append((t + 0.3, True)); dur = max(dur, 0.9)
            elif verb in ("hold", "buy"):
                self.item[nm].append((t + 0.3, arg, 0))
                if verb == "buy":
                    self.hop[nm].append((t, t + 0.45, 60)); self.expr[nm].append((t + 0.3, "happy"))
                dur = max(dur, 0.9)
            elif verb == "eat":
                it, bite = self.item_at(nm, t)
                if arg:
                    it = arg
                    self.item[nm].append((t, it, 0)); bite = 0
                if it not in EDIBLE:
                    raise ValueError(f"'{text}': {nm} isn't holding anything edible (hold or buy cotton candy, ice cream or popcorn first)")
                for j in range(1, 4):
                    self.item[nm].append((t + 0.5 + 0.8 * (j - 1), it, min(3, bite + j)))
                self.eat[nm].append((t, t + 2.8)); self.expr[nm].append((t, "happy")); dur = max(dur, 2.8)
            elif verb == "drink":
                self.eat[nm].append((t, t + 1.8)); self.expr[nm].append((t, "happy")); dur = max(dur, 1.8)
            elif verb == "drop":
                if re.search(r"umbrella|brolly", arg, re.I):
                    self.umb[nm].append((t, False))
                else:
                    self.item[nm].append((t, None, 0))
                dur = max(dur, 0.5)
            elif verb == "give":
                ip, recv = arg.split("|")
                if ip == "umbrella":
                    self.umb[nm].append((t + 0.45, False)); self.umb[recv].append((t + 0.45, True))
                    if recv != nm:
                        self.face[nm].append((t, 1 if self.x_at(recv, t) > self.x_at(nm, t) else -1))
                        self.face[recv].append((t, 1 if self.x_at(nm, t) > self.x_at(recv, t) else -1))
                    dur = max(dur, 1.0)
                    continue
                it, bite = self.item_at(nm, t)
                if ip:
                    it = ip
                self.item[nm].append((t + 0.45, None, 0)); self.item[recv].append((t + 0.45, it, bite))
                if recv != nm:
                    self.face[nm].append((t, 1 if self.x_at(recv, t) > self.x_at(nm, t) else -1))
                    self.face[recv].append((t, 1 if self.x_at(nm, t) > self.x_at(recv, t) else -1))
                dur = max(dur, 1.0)
            elif verb == "ride":
                kind, rd = ride_kind(arg)
                spot = RIDES.get(self.scene, {}).get(kind)
                if spot is None:
                    raise ValueError(f"'{text}': there is no {kind} in scene '{self.scene}'. Use @scene amusement park first")
                d = self._move(nm, t, spot * self.W + spread)
                self.rides[nm].append((t + d, t + d + rd, kind, k))
                dur = max(dur, d + rd)
        return dur

    def direct(self, items, t0):
        """items: [(text, parallel)] -> end time."""
        end, last = t0, t0
        for text, par in items:
            start = last if par else end
            d = self._one(text, start)
            last = start
            end = max(end, start + d)
        return end

    def line(self, speaker, a, b):
        """The speaker turns to the other visible character (and vice versa) when a line starts."""
        for other in L.CHARS:
            if other != speaker and self.vis_at(other, a) and self.vis_at(speaker, a):
                xs, xo = self.x_at(speaker, a), self.x_at(other, a)
                if abs(xs - xo) > 5:
                    self.face[speaker].append((a, 1 if xo > xs else -1))
                    self.face[other].append((a, 1 if xs > xo else -1))


def story_line(tr, stage, mark, ln, prev):
    """Directions (as animated 'act' segments), then the spoken line. Returns the current scene."""
    prev_box = [prev]

    def run(items, cur):
        group = []

        def flush(cur_scene):
            nonlocal group
            if group:
                t0 = tr.t
                stage.scene = cur_scene
                try:
                    t1 = stage.direct(group, t0)
                except ValueError as e:
                    L.die(f"stage direction: {e}")
                mark("act", t0, scene=cur_scene, prev_scene=prev_box[0], **stage.look(cur_scene))
                prev_box[0] = cur_scene
                tr.gap(max(0.05, t1 - t0))
                group = []
        for it in items:
            if it[0] == "scene":
                flush(cur)
                cur = it[1]
                group = []
            elif it[0] in ("weather", "time"):
                flush(cur)
                stage.set_atmos(it[0], it[1])
            else:
                group.append((it[1], it[2]))
        flush(cur)
        return cur

    stage.auto_line(ln, tr.t)
    cur = prev
    dirs = ln.get("dirs") or []
    if dirs:
        cur = run(dirs, prev)
    stage.scene = ln["scene"]
    stage.auto_stop(ln)
    a, b = tr.say(ln["jp"], ln["speaker"])
    ln.update(start=a, end=b)
    stage.line(ln["speaker"], a, b)
    mark("story", a - 0.02, line=ln, scene=ln["scene"], prev_scene=prev_box[0], **stage.look(ln["scene"]))
    cur = ln["scene"]
    tr.gap(0.6)
    after = ln.get("after") or []
    if after:
        prev_box[0] = cur
        cur = run(after, cur)
    return cur


# ------------------------------------------------------------------ drawing: characters
def _draw_item(d, ell, P, S, item, bite, swing):
    """Held item in the right hand (sprite coordinates)."""
    k = 1 - 0.22 * bite
    x = 383 - swing
    stick = (232, 210, 168)
    if item == "cotton_candy":
        d.line(P(x, 660, x, 545), fill=stick, width=int(8 * S))
        r = 64 * k
        for dx, dy, rr in ((0, 0, r), (-r * .55, r * .2, r * .7), (r * .55, r * .2, r * .7), (0, -r * .5, r * .7), (-r * .3, -r * .15, r * .5)):
            ell((x + dx - rr, 490 + dy - rr, x + dx + rr, 490 + dy + rr), (255, 186, 214))
        ell((x - r * .45, 490 - r * .5, x - r * .05, 490 - r * .15), (255, 220, 236))
    elif item == "ice_cream":
        d.polygon(P(x - 24, 618, x + 24, 618, x, 700), fill=(226, 176, 104))
        for j in range(3):
            d.line(P(x - 18 + j * 14, 622, x - 4 + j * 4, 690 - j * 4), fill=(200, 146, 80), width=int(3 * S))
        r = 40 * k
        ell((x - r, 580 - r, x + r, 580 + r), (255, 196, 214)); ell((x - r * .6, 548 - r * .6, x + r * .6, 548 + r * .6), (250, 236, 200))
    elif item == "balloon":
        d.line(P(x, 655, x + 80, 215), fill=(120, 110, 110), width=int(3 * S))
        ell((x + 36, 100, x + 128, 222), (240, 84, 96)); ell((x + 56, 120, x + 76, 150), (255, 190, 196))
        d.polygon(P(x + 80, 222, x + 72, 236, x + 88, 236), fill=(220, 70, 84))
    elif item == "ticket":
        d.rounded_rectangle(P(x - 34, 600, x + 34, 650), radius=int(6 * S), fill=(252, 232, 140), outline=(214, 170, 70), width=int(3 * S))
        ell((x - 30, 618, x - 22, 632), (252, 250, 240)); d.line(P(x - 12, 606, x - 12, 644), fill=(214, 170, 70), width=int(2 * S))
    elif item == "drink":
        d.polygon(P(x - 26, 590, x + 26, 590, x + 18, 662, x - 18, 662), fill=(250, 250, 252), outline=(150, 190, 220))
        d.rectangle(P(x - 24, 610, x + 24, 636), fill=(240, 120, 120))
        d.rounded_rectangle(P(x - 30, 580, x + 30, 592), radius=int(5 * S), fill=(236, 236, 240))
        d.line(P(x + 6, 584, x + 26, 520), fill=(240, 120, 120), width=int(5 * S))
    elif item == "bag":
        d.rounded_rectangle(P(x - 40, 600, x + 40, 700), radius=int(8 * S), fill=(246, 206, 150), outline=(200, 150, 96), width=int(3 * S))
        d.arc(P(x - 24, 560, x + 24, 620), 180, 360, fill=(200, 150, 96), width=int(5 * S))
    elif item == "book":
        d.rounded_rectangle(P(x - 34, 598, x + 34, 668), radius=int(6 * S), fill=(96, 140, 210))
        d.rectangle(P(x - 28, 606, x + 30, 660), fill=(250, 246, 236)); d.line(P(x - 34, 598, x - 34, 668), fill=(60, 96, 160), width=int(6 * S))
    elif item == "popcorn":
        for j, (dx, dy) in enumerate(((-24, -20), (0, -34), (24, -18), (-8, -8), (12, -6))):
            r = 20 * k
            ell((x + dx - r, 592 + dy - r, x + dx + r, 592 + dy + r), (255, 244, 196))
        d.polygon(P(x - 36, 596, x + 36, 596, x + 28, 690, x - 28, 690), fill=(240, 240, 244))
        for j in range(4):
            d.polygon(P(x - 36 + j * 18, 596, x - 36 + j * 18 + 9, 596, x - 28 + j * 14 + 7, 690, x - 28 + j * 14, 690), fill=(226, 70, 70))
    elif item == "plush":
        ell((x - 44, 610, x + 44, 700), (176, 124, 84)); ell((x - 34, 556, x + 34, 624), (190, 136, 94))
        ell((x - 40, 548, x - 16, 572), (176, 124, 84)); ell((x + 16, 548, x + 40, 572), (176, 124, 84))
        ell((x - 14, 580, x - 6, 590), (50, 36, 36)); ell((x + 6, 580, x + 14, 590), (50, 36, 36)); ell((x - 8, 592, x + 8, 604), (232, 196, 160))


def _draw_umbrella_closed(d, ell, P, S, swing):
    '''Folded umbrella held in the right hand (sprite coordinates).'''
    x = 383 - swing
    wood, col = (112, 84, 66), (74, 98, 160)
    d.line(P(x, 692, x + 12, 604), fill=wood, width=int(9 * S))
    d.arc(P(x - 26, 676, x + 4, 716), 20, 200, fill=wood, width=int(9 * S))
    d.polygon(P(x + 2, 612, x + 34, 612, x + 66, 318, x + 52, 312), fill=col)
    d.line(P(x + 14, 540, x + 44, 536), fill=(40, 56, 104), width=int(7 * S))
    d.line(P(x + 52, 312, x + 60, 290), fill=(60, 50, 50), width=int(6 * S))


@functools.lru_cache(None)
def rig(name, mouth, blink, expr, walk, arm, out, item=None, bite=0, umb=False):
    """Full-body Mika / Alex with a walk phase (0-3), a waving arm (0-2), an expression and a held item."""
    c, S = L.CHARS[name], 2 * L.CHAR_SCALE
    w, h = int(560 * S), int(960 * S)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    P = lambda *v: [int(x * S) for x in v]
    ell = lambda box, fill: d.ellipse(P(*box), fill=fill)
    ink, hair, skin, top, acc = (70, 45, 48), c["hair"], c["skin"], c["top"], c["accent"]
    brow_c, mouth_c = (86, 56, 52), (120, 40, 52)
    ll, rl = (28 if walk == 1 else 0), (28 if walk == 3 else 0)
    swing = {0: 0, 1: 8, 2: 0, 3: -8}[walk]
    if c["long_hair"]:
        d.rounded_rectangle(P(110, 170, 450, 590), radius=int(110 * S), fill=hair)
    shoe = (96, 66, 60)
    if c["long_hair"]:
        for x0, lf in ((214, ll), (306, rl)):
            d.rounded_rectangle(P(x0, 780 - lf, x0 + 42, 905 - lf), radius=int(16 * S), fill=skin)
            d.rounded_rectangle(P(x0 - 2, 862 - lf, x0 + 44, 912 - lf), radius=int(14 * S), fill=(250, 248, 246))
            ell((x0 - 14, 896 - lf, x0 + 62, 940 - lf), shoe)
        d.polygon(P(178, 640, 382, 640, 414, 805, 146, 805), fill=(122, 132, 196))
        for x in range(170, 400, 46):
            d.line(P(x, 700, x - (280 - x) * 0.08, 800), fill=(104, 114, 178), width=int(5 * S))
    else:
        for x0, lf in ((198, ll), (292, rl)):
            d.rounded_rectangle(P(x0, 640, x0 + 72, 890 - lf), radius=int(26 * S), fill=(96, 112, 150))
            ell((x0 - 10, 876 - lf, x0 + 84, 926 - lf), shoe)
        d.rounded_rectangle(P(190, 628, 370, 700), radius=int(26 * S), fill=(96, 112, 150))
    d.rounded_rectangle(P(185, 450, 375, 690), radius=int(60 * S), fill=top)
    d.polygon(P(245, 452, 280, 505, 315, 452), fill=skin)
    ell((140 + swing, 500, 210 + swing, 650), top)
    ell((148 + swing, 625, 205 + swing, 675), skin)
    if not arm:
        ell((350 - swing, 500, 420 - swing, 650), top)
        if umb:
            _draw_umbrella_closed(d, ell, P, S, swing)
        if item:
            _draw_item(d, ell, P, S, item, bite, swing)
        ell((355 - swing, 625, 412 - swing, 675), skin)
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
        if blink or expr == "happy":
            d.arc(P(ex - 26, 332, ex + 26, 376), 200, 340, fill=ink, width=int(6 * S))
        elif expr == "surprised":
            ell((ex - 30, 308, ex + 30, 392), (55, 35, 42))
            ell((ex - 18, 322, ex + 4, 346), (255, 255, 255)); ell((ex + 8, 362, ex + 20, 374), (255, 255, 255))
        else:
            ell((ex - 24, 318, ex + 24, 382), (55, 35, 42))
            sh = 8 if expr == "confused" else 0
            ell((ex - 15 + sh, 330, ex + 3 + sh, 350), (255, 255, 255)); ell((ex + 6 + sh, 358, ex + 16 + sh, 368), (255, 255, 255))
    bw = int(7 * S)
    if expr == "confused":
        d.line(P(192, 300, 252, 294), fill=brow_c, width=bw); d.line(P(312, 270, 368, 282), fill=brow_c, width=bw)
    elif expr == "surprised":
        d.arc(P(190, 270, 254, 300), 200, 340, fill=brow_c, width=bw); d.arc(P(306, 270, 370, 300), 200, 340, fill=brow_c, width=bw)
    elif expr == "sad":
        d.line(P(192, 302, 252, 284), fill=brow_c, width=bw); d.line(P(308, 284, 368, 302), fill=brow_c, width=bw)
    chk = (246, 140, 140) if expr == "shy" else (250, 172, 170)
    k = 8 if expr == "shy" else 0
    ell((168 - k, 388 - k, 215 + k, 412 + k), chk); ell((345 - k, 388 - k, 392 + k, 412 + k), chk)
    if mouth == 1:
        ell((268, 408, 292, 430), mouth_c)
    elif mouth >= 2:
        ell((258, 405, 302, 442), mouth_c); ell((266, 424, 294, 440), (236, 120, 132))
    elif expr == "happy":
        d.arc(P(248, 394, 312, 440), 20, 160, fill=ink, width=int(6 * S))
    elif expr == "surprised":
        ell((270, 410, 290, 436), mouth_c)
    elif expr == "confused":
        d.line(P(264, 424, 276, 416, 288, 426, 300, 416), fill=ink, width=int(5 * S))
    elif expr == "sad":
        d.arc(P(262, 418, 298, 446), 200, 340, fill=ink, width=int(5 * S))
    elif expr == "shy":
        d.arc(P(270, 404, 292, 424), 20, 160, fill=ink, width=int(4 * S))
    else:
        d.arc(P(262, 400, 298, 430), 20, 160, fill=ink, width=int(5 * S))
    if expr == "confused":
        d.polygon(P(430, 165, 416, 205, 444, 205), fill=(176, 216, 240)); ell((414, 192, 446, 226), (176, 216, 240))
    if arm:
        hx = 448 + (16 if arm == 1 else -6)
        d.line(P(385, 545, hx, 440), fill=top, width=int(66 * S))
        ell((352, 505, 420, 585), top)
        ell((hx - 32, 380, hx + 32, 452), skin)
    return im.resize((int(L.SPRITE_W * out), int(L.SPRITE_H * out * 960 / 760)), Image.LANCZOS)


# ------------------------------------------------------------------ drawing: rides and moving scenery
def _fer():
    return int(0.88 * L.W), 430, 230, 30.0       # centre x, centre y, radius, seconds per turn


def ferris_gondola(tt, k):
    cx, cy, R, per = _fer()
    a = 2 * math.pi * tt / per + k * math.pi / 4
    return cx + R * math.cos(a), cy + R * math.sin(a)


def ferris_bottom_k(tt):
    return max(range(8), key=lambda k: ferris_gondola(tt, k)[1])


def draw_ferris(fr, tt):
    d = ImageDraw.Draw(fr)
    cx, cy, R, per = _fer()
    for sx in (-1, 1):
        d.line([(cx, cy), (cx + sx * 140, 800)], fill=(190, 190, 208), width=16)
    d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=(238, 238, 248), width=10)
    d.ellipse((cx - R * .55, cy - R * .55, cx + R * .55, cy + R * .55), outline=(226, 226, 240), width=6)
    pal = [(244, 120, 140), (250, 196, 96), (120, 190, 240), (150, 214, 150)]
    for k in range(8):
        a = 2 * math.pi * tt / per + k * math.pi / 4
        d.line([(cx, cy), (cx + R * math.cos(a), cy + R * math.sin(a))], fill=(226, 226, 240), width=5)
    d.ellipse((cx - 22, cy - 22, cx + 22, cy + 22), fill=(244, 120, 140), outline=(255, 255, 255), width=5)
    for k in range(8):
        gx, gy = ferris_gondola(tt, k)
        d.line([(gx, gy), (gx, gy + 14)], fill=(150, 150, 170), width=4)
        d.rounded_rectangle((gx - 46, gy + 12, gx + 46, gy + 60), radius=10, fill=pal[k % 4], outline=(255, 255, 255), width=4)


def _carousel_c():
    return int(0.36 * L.W)


def carousel_horse(tt, i, n=6):
    cx = _carousel_c()
    phi = 2 * math.pi * tt / 8.0 + i * 2 * math.pi / n
    return cx + 150 * math.sin(phi), 620 + 16 * math.sin(3 * phi + i), 0.9 + 0.1 * math.cos(phi)


def draw_carousel(fr, tt):
    d = ImageDraw.Draw(fr)
    cx = _carousel_c()
    d.ellipse((cx - 240, 730, cx + 240, 800), fill=(250, 226, 200), outline=(220, 170, 150), width=5)
    d.rectangle((cx - 9, 345, cx + 9, 750), fill=(240, 214, 130))
    n, base_y = 8, 360
    sw = 2 * 260 / n
    for j in range(n):
        d.polygon([(cx, 235), (cx - 260 + j * sw, base_y), (cx - 260 + (j + 1) * sw, base_y)], fill=(246, 130, 160) if j % 2 == 0 else (255, 246, 240))
    for j in range(n):
        d.ellipse((cx - 260 + j * sw, base_y - 14, cx - 260 + (j + 1) * sw, base_y + 18), fill=(246, 130, 160) if j % 2 == 0 else (255, 246, 240))
    d.line([(cx, 235), (cx, 195)], fill=(150, 110, 90), width=6)
    d.polygon([(cx, 195), (cx + 46, 210), (cx, 225)], fill=(250, 196, 80))
    cols = [(250, 250, 250), (246, 196, 120), (190, 150, 230), (140, 200, 240), (246, 150, 160), (150, 214, 160)]
    for i in sorted(range(6), key=lambda i: carousel_horse(tt, i)[2]):
        x, y, s = carousel_horse(tt, i)
        d.line([(x, 410), (x, y + 60 * s)], fill=(240, 214, 130), width=6)
        d.ellipse((x - 40 * s, y - 20 * s, x + 40 * s, y + 20 * s), fill=cols[i])
        d.polygon([(x + 22 * s, y - 14 * s), (x + 44 * s, y - 52 * s), (x + 64 * s, y - 30 * s), (x + 40 * s, y + 6 * s)], fill=cols[i])
        d.ellipse((x + 36 * s, y - 50 * s, x + 70 * s, y - 24 * s), fill=cols[i])
        for lx in (-28, -10, 14, 30):
            d.line([(x + lx * s, y + 12 * s), (x + lx * s, y + 48 * s)], fill=cols[i], width=int(8 * s))
        d.ellipse((x - 4 * s, y - 28 * s, x + 20 * s, y - 8 * s), fill=(220, 90, 110))


def ride_pos(kind, tt, t0, idx):
    """(x, feet_y, out_scale, crop_fraction) for a rider at time tt."""
    if kind == "carousel":
        x, y, s = carousel_horse(tt, (idx * 3) % 6)
        return x, y - 8, 0.27 * s, 0.74
    k = (ferris_bottom_k(t0) + idx) % 8
    gx, gy = ferris_gondola(tt, k)
    return gx, gy + 34, 0.25, 0.60


def draw_fish(fr, tt):
    d = ImageDraw.Draw(fr)
    cols = [(255, 150, 90), (255, 210, 90), (150, 220, 250), (250, 120, 160), (170, 240, 190), (210, 170, 250), (255, 180, 120)]
    for i in range(7):
        x = 300 + ((i * 197 + tt * (34 + 9 * i)) % 1320)
        y = 270 + (i * 61) % 330 + 14 * math.sin(tt * 1.6 + i)
        s = 0.8 + (i % 3) * 0.25
        d.ellipse((x - 44 * s, y - 20 * s, x + 44 * s, y + 20 * s), fill=cols[i])
        d.polygon([(x - 40 * s, y), (x - 76 * s, y - 24 * s), (x - 76 * s, y + 24 * s)], fill=cols[i])
        d.ellipse((x + 22 * s, y - 8 * s, x + 32 * s, y + 2 * s), fill=(40, 40, 60))
    for i, jx in enumerate((420, 1500, 1260)):
        y = 330 + 50 * math.sin(tt * 1.1 + i * 2)
        d.pieslice((jx - 50, y - 50, jx + 50, y + 40), 180, 360, fill=(236, 200, 250))
        for t in range(-3, 4):
            d.line([(jx + t * 14, y), (jx + t * 14 + 6 * math.sin(tt * 3 + t), y + 56)], fill=(226, 180, 244), width=4)


def draw_dynamic(fr, scene, tt, seg=None):
    if scene == "amusement":
        draw_carousel(fr, tt); draw_ferris(fr, tt)
    elif scene == "aquarium":
        draw_fish(fr, tt)
    SC.dynamic(fr, scene, tt, seg or {})


# ------------------------------------------------------------------ drawing: new places
NEW_SCENES = {
    "amusement": dict(top=(140, 200, 250), bot=(255, 238, 222), floor=(226, 204, 170), table=(246, 150, 170), edge=(214, 110, 134)),
    "shrine": dict(top=(206, 228, 246), bot=(246, 240, 226), floor=(190, 180, 166), table=(176, 150, 120), edge=(130, 106, 84)),
    "zoo": dict(top=(190, 228, 250), bot=(238, 248, 230), floor=(170, 204, 132), table=(150, 110, 76), edge=(112, 80, 56)),
    "aquarium": dict(top=(40, 90, 150), bot=(90, 160, 200), floor=(60, 84, 116), table=(40, 62, 94), edge=(28, 44, 72)),
}
NEW_KEYWORDS = {
    "amusement": ["ゆうえんち", "遊園地", "かんらんしゃ", "観覧車", "メリーゴーラウンド", "わたあめ", "amusement", "fair", "carnival", "ferris", "carousel", "cotton candy", "theme park", "ride"],
    "shrine": ["じんじゃ", "神社", "おまいり", "とりい", "鳥居", "shrine", "temple", "torii", "pray"],
    "zoo": ["どうぶつえん", "動物園", "ぞう", "きりん", "zoo", "giraffe", "elephant"],
    "aquarium": ["すいぞくかん", "水族館", "さかな", "くらげ", "aquarium", "jellyfish", "shark"],
}
NEW_ALIASES = {"amusement park": "amusement", "theme park": "amusement", "funfair": "amusement", "fun fair": "amusement",
               "fair": "amusement", "fairground": "amusement", "carnival": "amusement", "amusement": "amusement",
               "temple": "shrine", "torii": "shrine", "aquarium": "aquarium", "zoo": "zoo"}


def _stall(d, cx, c1, c2, label, kind):
    w = 170
    d.rectangle((cx - w, 640, cx + w, 800), fill=(238, 222, 200)); d.rectangle((cx - w, 640, cx + w, 666), fill=(214, 190, 160))
    d.rectangle((cx - w, 500, cx - w + 14, 640), fill=(150, 110, 80)); d.rectangle((cx + w - 14, 500, cx + w, 640), fill=(150, 110, 80))
    n = 8; sw = 2 * w / n
    for j in range(n):
        d.polygon([(cx - w + j * sw, 500), (cx - w + (j + 1) * sw, 500), (cx - w + (j + 1) * sw + 6, 560), (cx - w + j * sw - 6, 560)], fill=c1 if j % 2 == 0 else c2)
    L.sign(d, cx, 424, 260, 66, label, c1, size=40)
    if kind == "cotton":
        d.ellipse((cx - 62, 628, cx + 62, 668), fill=(210, 210, 224))
        for dx, dy, r in ((0, 0, 46), (-40, 10, 32), (40, 10, 32), (0, -26, 32), (-18, -6, 26)):
            d.ellipse((cx + dx - r, 598 + dy - r, cx + dx + r, 598 + dy + r), fill=(255, 186, 214))
        for j in range(4):
            d.line([(cx - 120 + j * 20, 640), (cx - 120 + j * 20, 600)], fill=(232, 210, 168), width=6)
            d.ellipse((cx - 134 + j * 20, 570, cx - 106 + j * 20, 604), fill=(255, 200, 224))
    else:
        for j, col in enumerate(((176, 124, 84), (240, 200, 120), (200, 150, 220), (150, 200, 240))):
            x = cx - 110 + j * 74
            d.ellipse((x - 26, 606, x + 26, 658), fill=col); d.ellipse((x - 22, 590, x - 6, 608), fill=col); d.ellipse((x + 6, 590, x + 22, 608), fill=col)
        for j, col in enumerate(((240, 84, 96), (250, 196, 80), (110, 180, 240), (140, 210, 150), (200, 130, 230))):
            bx = cx - 120 + j * 60
            d.line([(bx, 400), (cx - 100 + j * 50, 360)], fill=(130, 120, 120), width=3)
            d.ellipse((bx - 34, 310, bx + 34, 400), fill=col)


def _amusement(d, rng):
    W = L.W
    d.ellipse((-260, 600, 760, 1100), fill=(160, 208, 156)); d.ellipse((520, 640, 1500, 1180), fill=(146, 200, 146))
    d.ellipse((1180, 590, 2200, 1150), fill=(166, 212, 160))
    d.ellipse((520, 150, 650, 280), fill=(255, 236, 140))
    for cx, cy in ((900, 230), (1250, 190)):
        d.ellipse((cx - 80, cy - 30, cx + 80, cy + 30), fill=(255, 255, 255)); d.ellipse((cx - 36, cy - 56, cx + 54, cy + 10), fill=(255, 255, 255))
    pts = [(x, 110 + 24 * math.sin(x / 150)) for x in range(0, W + 40, 40)]
    d.line(pts, fill=(96, 74, 74), width=4)
    cols = [(240, 96, 110), (250, 200, 90), (110, 180, 240), (140, 210, 150), (200, 140, 230)]
    for j, (x, y) in enumerate(pts[:-1]):
        if j % 2 == 0:
            d.polygon([(x, y), (x + 40, y + 2), (x + 20, y + 54)], fill=cols[(j // 2) % 5])
    for x in (60, 190):
        d.rectangle((x, 330, x + 26, 800), fill=(240, 120, 130))
    d.rounded_rectangle((40, 290, 230, 350), radius=18, fill=(250, 200, 90)); d.text((135, 320), "いりぐち", font=L.font(34), fill=(110, 60, 50), anchor="mm")
    cx = 326 + 40
    d.rectangle((cx - 80, 560, cx + 80, 800), fill=(250, 228, 190)); d.rectangle((cx - 50, 610, cx + 50, 700), fill=(120, 150, 190))
    d.rectangle((cx - 60, 700, cx + 60, 716), fill=(214, 170, 120))
    d.polygon([(cx - 104, 562), (cx + 104, 562), (cx, 480)], fill=(240, 96, 110))
    L.sign(d, cx, 430, 150, 50, "きっぷ", (250, 200, 90), (110, 60, 50), 32)
    _stall(d, int(0.58 * W), (246, 130, 170), (255, 246, 244), "わたあめ", "cotton")
    _stall(d, int(0.72 * W), (110, 180, 240), (255, 246, 244), "ゲーム", "prize")
    L.sign(d, 1010, 175, 520, 96, "ゆうえんち  Fun Park", (232, 84, 110), size=50)


def _shrine(d, rng):
    W = L.W
    d.ellipse((-200, 480, 900, 1000), fill=(120, 170, 130)); d.ellipse((1000, 470, 2200, 1020), fill=(104, 160, 122))
    for x in (120, 360, 1500, 1760):
        d.rectangle((x - 14, 420, x + 14, 800), fill=(110, 80, 64)); d.polygon([(x - 120, 560), (x, 200), (x + 120, 560)], fill=(70, 130, 92)); d.polygon([(x - 150, 700), (x, 340), (x + 150, 700)], fill=(60, 120, 84))
    d.rectangle((822, 330, 862, 800), fill=(206, 56, 44)); d.rectangle((1058, 330, 1098, 800), fill=(206, 56, 44))
    d.polygon([(760, 290), (1160, 290), (1130, 350), (790, 350)], fill=(34, 30, 34)); d.rectangle((800, 350, 1120, 384), fill=(206, 56, 44))
    d.rectangle((830, 420, 1090, 446), fill=(206, 56, 44)); d.rectangle((938, 384, 982, 420), fill=(34, 30, 34))
    for x in (600, 1320):
        d.rectangle((x - 22, 640, x + 22, 800), fill=(170, 170, 176)); d.rectangle((x - 46, 596, x + 46, 644), fill=(184, 184, 190)); d.polygon([(x - 62, 596), (x + 62, 596), (x, 540)], fill=(150, 150, 158))
        d.rectangle((x - 22, 608, x + 22, 632), fill=(255, 214, 120))
    d.rounded_rectangle((330, 640, 450, 740), radius=10, fill=(150, 104, 70)); d.rectangle((330, 640, 450, 662), fill=(120, 80, 54))
    for j in range(5):
        d.rectangle((344 + j * 22, 662, 350 + j * 22, 740), fill=(120, 80, 54))
    d.rectangle((420, 480, 450, 640), fill=(120, 80, 54))
    d.rounded_rectangle((520, 130, 760, 200), radius=14, fill=(236, 224, 204)); d.text((640, 166), "じんじゃ", font=L.font(46), fill=(120, 60, 50), anchor="mm")
    blossoms = getattr(L, "blossoms", None)
    if blossoms:
        blossoms(d, rng, (0, 100, W, 360), 40)


def _zoo(d, rng):
    W = L.W
    d.ellipse((-300, 560, 800, 1100), fill=(150, 200, 130)); d.ellipse((900, 600, 2200, 1150), fill=(158, 206, 136))
    d.ellipse((1620, 130, 1760, 270), fill=(255, 236, 140))
    gx = int(0.3 * W)
    for lx in (-60, -30, 30, 60):
        d.rectangle((gx + lx - 12, 600, gx + lx + 12, 800), fill=(240, 196, 90))
    d.ellipse((gx - 110, 520, gx + 110, 640), fill=(244, 202, 96))
    d.polygon([(gx + 60, 560), (gx + 120, 560), (gx + 150, 290), (gx + 100, 290)], fill=(244, 202, 96))
    d.ellipse((gx + 90, 240, gx + 196, 310), fill=(244, 202, 96)); d.ellipse((gx + 150, 258, gx + 164, 272), fill=(60, 40, 30))
    for dx, dy in ((-60, 560), (-10, 590), (50, 550), (110, 400), (118, 340)):
        d.ellipse((gx + dx - 14, dy - 12, gx + dx + 14, dy + 12), fill=(176, 120, 60))
    ex = int(0.72 * W)
    d.ellipse((ex - 170, 520, ex + 170, 730), fill=(160, 166, 180))
    for lx in (-110, -40, 40, 110):
        d.rectangle((ex + lx - 28, 680, ex + lx + 28, 800), fill=(150, 156, 170))
    d.ellipse((ex - 270, 500, ex - 100, 650), fill=(160, 166, 180)); d.ellipse((ex - 190, 500, ex - 90, 620), fill=(176, 182, 194))
    d.polygon([(ex - 262, 590), (ex - 200, 600), (ex - 230, 760), (ex - 270, 760)], fill=(160, 166, 180))
    d.ellipse((ex - 232, 540, ex - 220, 552), fill=(40, 40, 50))
    for x in range(0, W, 60):
        d.rectangle((x, 690, x + 14, 800), fill=(130, 96, 66))
    d.rectangle((0, 720, W, 736), fill=(130, 96, 66)); d.rectangle((0, 760, W, 772), fill=(130, 96, 66))
    L.sign(d, 960, 175, 560, 90, "どうぶつえん  Zoo", (96, 170, 110), size=50)


def _aquarium(d, rng):
    W = L.W
    d.rounded_rectangle((240, 180, 1680, 720), radius=40, fill=(28, 60, 100))
    d.rounded_rectangle((264, 204, 1656, 696), radius=28, fill=(70, 150, 200))
    for y in range(204, 696, 6):
        t = (y - 204) / 492
        d.line([(266, y), (1654, y)], fill=(int(90 - 50 * t), int(180 - 70 * t), int(220 - 60 * t)), width=6)
    for x in range(300, 1640, 90):
        d.polygon([(x, 696), (x + 24, 640 - (x % 7) * 8), (x + 46, 696)], fill=(60, 150, 110))
    for x, r in ((420, 60), (900, 80), (1400, 70)):
        d.ellipse((x - r, 696 - r * .7, x + r, 696 + r * .3), fill=(120, 110, 130))
    for i in range(14):
        x, y, r = 300 + (i * 97) % 1340, 260 + (i * 53) % 380, 6 + i % 4 * 3
        d.ellipse((x - r, y - r, x + r, y + r), outline=(220, 244, 255), width=3)
    L.sign(d, 960, 120, 640, 70, "すいぞくかん  Aquarium", (40, 110, 160), size=42)


SCENE_DRAW = {"amusement": _amusement, "shrine": _shrine, "zoo": _zoo, "aquarium": _aquarium}


def draw_scene(scene, d, rng):
    fn = SCENE_DRAW.get(scene)
    if fn:
        fn(d, rng)
        return True
    return False


# ------------------------------------------------------------------ drawing: per-frame characters
def atmos_frame(R, name, variant, bg, fg, seg, tt):
    return AT.frame_bg(R, name, variant, bg, fg, seg, tt)


parse_weather, parse_tod = AT.parse_weather, AT.parse_tod


def draw_characters(R, fr, seg, i, tt, who, mouth):
    """Draw moving scenery, riders, umbrellas, both characters and falling rain / snow for frame i using the stage timeline."""
    B, stage = R.B, R.B["stage"]
    scene = seg.get("scene")
    draw_dynamic(fr, scene, tt, seg)
    d = ImageDraw.Draw(fr)
    order = sorted(L.CHARS, key=lambda n: 1 if who == n else 0)
    states = {}
    for nm in order:
        st = stage.state(nm, tt)
        if seg["kind"] == "outro":
            st = dict(vis=True, x=stage.home[nm], walking=False, speed=0.0, wave=False, hop=None, ride=None, pop=None, expr="happy",
                      face=stage.dflt_face[nm], mirror=False, item=None, bite=0, eating=False, umb=st.get("umb", False))
        states[nm] = st
    kind, k = AT.weather_state(seg, tt)
    wet = bool(kind) and scene in AT.OUTDOOR
    rainy = wet and k > 0.25
    floor_y = L.FLOOR_Y - 50
    # riders first (they sit on the moving rides)
    for nm in order:
        st = states[nm]
        if not st["vis"] or not st["ride"]:
            continue
        t0, t1, kind_r, idx = st["ride"]
        px, py, out, crop = ride_pos(kind_r, tt, t0, idx)
        s = _smooth(min((tt - t0) / 0.7, (t1 - tt) / 0.7))
        X = st["x"] + (px - st["x"]) * s
        Y = floor_y + (py - floor_y) * s
        O = round((L.STAGE_OUT + (out - L.STAGE_OUT) * s) / 0.02) * 0.02
        arm = (1 + int(tt * 5) % 2) if (int(tt / 1.5) % 2 == 0 and s > 0.9) else 0
        sp = rig(nm, 2 if int(tt * 3) % 2 and s > 0.9 else 0, False, "happy", 0, arm, max(0.1, O))
        if s > 0.5:
            sp = sp.crop((0, 0, sp.width, int(sp.height * crop)))
        fr.paste(sp, (int(X - sp.width // 2), int(Y - sp.height)), sp)
    # standing characters: work out where each one is, then draw umbrellas behind them
    lay = []
    for nm in order:
        st = states[nm]
        if st["ride"] and st["vis"]:
            continue
        if not st["vis"] or st["x"] < -L.SPRITE_W * 1.2 or st["x"] > L.W + L.SPRITE_W * 1.2:
            continue
        speaking = who == nm
        blink = ((i + (0 if nm == "Mika" else 41)) % 72) < 3
        sp_k = max(0.6, st["speed"] / SPEED) if st["walking"] else 1.0
        walk = (0, 1, 0, 3)[int(tt * 7 * sp_k) % 4] if st["walking"] else 0
        arm = (1 + int(tt * 5) % 2) if st["wave"] else 0
        mth = int(mouth) if speaking else (1 if st["eating"] and int(tt * 4) % 2 else 0)
        has_umb = bool(st.get("umb"))
        is_open = has_umb and rainy
        s = rig(nm, mth, blink, st["expr"], walk, arm, L.STAGE_OUT, st["item"], min(3, st["bite"]), has_umb and not is_open)
        if st["mirror"]:
            s = ImageOps.mirror(s)
        if st["walking"]:
            bob = (12 if st["speed"] < 500 else 22) * abs(math.sin(tt * 7 * sp_k * math.pi / 2))
        elif speaking and mouth:
            bob = 6 * abs(math.sin(tt * 7))
        else:
            bob = 2 * math.sin(tt * 2 + (0 if nm == "Mika" else 1.7))
        if st["hop"] is not None:
            u, amp = st["hop"]
            bob += amp * math.sin(math.pi * u)
        lay.append(dict(nm=nm, st=st, s=s, x=int(st["x"] - s.width // 2), y=int(L.FLOOR_Y - 50 - s.height - bob),
                        cx=st["x"], mirror=st["mirror"], open=is_open, speaking=speaking))
    shelters = AT.draw_umbrellas(fr, lay) if rainy else []
    markers = []
    for e in lay:
        nm, st, s, x, y = e["nm"], e["st"], e["s"], e["x"], e["y"]
        fr.paste(s, (x, y), s)
        p = R.pills[(nm, int(e["speaking"]))]
        fr.paste(p, (int(st["x"]) - p.width // 2, int(L.FLOOR_Y - 50 - s.height + 36)), p)
        mk = st["pop"] or {"confused": "?", "surprised": "!"}.get(st["expr"])
        if mk:
            markers.append((int(st["x"] + s.width * (0.26 if not st["mirror"] else -0.26)), y, mk, nm))
    if wet:
        AT.draw_precip(fr, tt, kind, k, shelters)
    for mx, y, mk, nm in markers:
        wob = 6 * math.sin(tt * 9)
        d.text((mx, int(y - 20 + wob)), mk, font=L.font(110), fill=L.CHARS[nm]["accent"], stroke_width=10, stroke_fill=(255, 255, 255), anchor="mm")


# ------------------------------------------------------------------ forgiving script reader
_OPT = re.compile(r"^(?:[-*•]\s*)?\(?([A-Da-d])[).:：]\s*(.+)$")


def normalize(text):
    """Turn common variants of the [vocab] / [grammar] / [quiz] sections (numbered lists, 'Example 1:',
    'Answer: B', markdown bold...) into the strict one-line format. Line count is preserved so error
    messages keep their line numbers. Scripts that are already strict come back unchanged."""
    lines = text.replace("\r", "").split("\n")
    out = list(lines)
    sec, i, n = None, 0, len(lines)
    strict = re.compile(r"^(vocab|grammar|example|quiz)\s*:", re.I)
    while i < n:
        s = lines[i].strip()
        if s.startswith("```"):
            out[i] = ""; i += 1; continue
        m = re.match(r"^\[(\w+)\]$", s)
        if m:
            sec = m[1].lower(); i += 1; continue
        if sec not in ("vocab", "grammar", "quiz") or not s or s.startswith("#") or strict.match(s):
            i += 1; continue
        s = s.replace("**", "").replace("__", "")
        if sec in ("vocab", "grammar"):
            mm = re.match(r"^(?:[-*•]\s*)?(?:example|ex)(?:\s*\d+)?\s*[:：]\s*(.+)$", s, re.I)
            if mm:
                out[i] = "example: " + mm[1].strip(); i += 1; continue
            if sec == "vocab":
                mm = re.match(r"^(?:\d+[.)]\s*|[-*•]\s*)(.+?)\s*(?:[(（]([^)）]*)[)）]\s*)?(?:[—–]|\s-{1,2}\s|[:：])\s*(.+)$", s)
                if mm:
                    out[i] = f"vocab: {mm[1].strip()} | {mm[3].strip()}" + (f" | {mm[2].strip()}" if mm[2] else "")
            else:
                mm = re.match(r"^(?:\d+[.)]\s*|[-*•]\s*)(.+?)\s*(?:[—–]|\s-{1,2}\s)\s*(.+)$", s)
                if mm:
                    out[i] = f"grammar: {mm[1].strip()} | {mm[2].strip()}"
            i += 1; continue
        # quiz block: "1. Question?" then A) B) C) / Answer: B / Explanation: ...
        mq = re.match(r"^(?:\d+[.)]\s*|[-*•]\s*|Q\d*[.:)]\s*)(.+)$", s, re.I)
        if not mq or _OPT.match(s):
            i += 1; continue
        q, opts, ans, why, j = mq[1].strip(), [], None, "", i + 1
        while j < n:
            s2 = lines[j].strip().replace("**", "").replace("__", "")
            mo, ma = _OPT.match(s2), re.match(r"^(?:answer|correct(?: answer)?)\s*[:：]\s*\(?([A-Da-d])\b.*$", s2, re.I)
            me = re.match(r"^(?:explanation|why|note)\s*[:：]\s*(.+)$", s2, re.I)
            if mo and ans is None:
                opts.append(mo[2].strip())
            elif ma:
                ans = ma[1].upper()
            elif me:
                why = me[1].strip()
            elif s2 == "":
                if ans is not None:
                    break
            else:
                break
            j += 1
        if opts and ans is not None:
            out[i] = "quiz: " + " | ".join([q] + opts + [ans] + ([why] if why else ""))
            for k in range(i + 1, j):
                out[k] = ""
            i = j
        else:
            i += 1
    return "\n".join(out)
