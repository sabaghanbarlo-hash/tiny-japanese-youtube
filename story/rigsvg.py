"""SVG-rigged characters for the story modes (drop-in look for acting.rig()).

Characters are built from separate parts (head, hair, brows, eyes, mouth, torso, two-joint arms, legs, pigtails) and posed
per frame, then rasterised with resvg (pip install resvg-py; no system libraries needed).
 - Parametric characters (anything in lesson.CHARS with hair/skin/top/accent/long_hair, e.g. Mika, Alex and every future
   one) get a rig automatically.
 - Marinette and Adrien have their own designs (ported from sprites.py).
render() returns None when a character or resvg is unavailable, so the caller falls back to the old drawing.
"""
import io, math
from PIL import Image
try:
    import resvg_py
except Exception:                                    # pragma: no cover
    resvg_py = None

H = lambda t: "#%02x%02x%02x" % tuple(int(v) for v in t)
SK, SH = "#fde3cb", "#f0cdb2"
NV, NVD, NVL = H((50, 68, 122)), H((34, 46, 92)), H((92, 112, 170))


def bez(p0, p1, p2, n=14):
    return [((1-t)**2*p0[0]+2*(1-t)*t*p1[0]+t*t*p2[0], (1-t)**2*p0[1]+2*(1-t)*t*p1[1]+t*t*p2[1]) for t in [i/n for i in range(n+1)]]


def lock(root, ctrl, tip, width, n=14):
    c = bez(root, ctrl, tip, n); L = []; R = []
    for i, (x, y) in enumerate(c):
        a = c[min(i+1, n)]; b = c[max(i-1, 0)]; dx, dy = a[0]-b[0], a[1]-b[1]; l = math.hypot(dx, dy) or 1
        nx, ny = -dy/l, dx/l
        w = width*math.sin(math.pi*(0.12+0.88*i/n)**0.9)*(1-0.15*i/n)/2
        if i == n: w = 0
        L.append((x+nx*w, y+ny*w)); R.append((x-nx*w, y-ny*w))
    return L+R[::-1]


def poly(p, f):
    d = "M"+"L".join(f"{x:.1f} {y:.1f}" for x, y in p)+"Z"
    return f'<path d="{d}" fill="{f}" stroke="{f}" stroke-width="6" stroke-linejoin="round"/>'


def ell(b, f, x=''):
    return f'<ellipse cx="{(b[0]+b[2])/2}" cy="{(b[1]+b[3])/2}" rx="{(b[2]-b[0])/2}" ry="{(b[3]-b[1])/2}" fill="{f}" {x}/>'


def rrect(b, r, f):
    return f'<rect x="{b[0]}" y="{b[1]}" width="{b[2]-b[0]}" height="{b[3]-b[1]}" rx="{r}" fill="{f}"/>'


def line(p, c, w):
    return f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in p)}" fill="none" stroke="{c}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'


def arc(b, a0, a1, c, w):
    cx, cy, rx, ry = (b[0]+b[2])/2, (b[1]+b[3])/2, (b[2]-b[0])/2, (b[3]-b[1])/2
    P = lambda a: (cx+rx*math.cos(math.radians(a)), cy+ry*math.sin(math.radians(a)))
    (x0, y0), (x1, y1) = P(a0), P(a1)
    return f'<path d="M{x0:.1f} {y0:.1f}A{rx} {ry} 0 {1 if (a1-a0) % 360 > 180 else 0} 1 {x1:.1f} {y1:.1f}" fill="none" stroke="{c}" stroke-width="{w}" stroke-linecap="round"/>'


def _arm(sleeve, w, hr, skin, hstroke, edge=None):
    e = f'<path d="M0 0V95" stroke="{edge}" stroke-width="{w+8}" stroke-linecap="round"/>' if edge else ''
    f = f'<path d="M0 0V88" stroke="{edge}" stroke-width="{w+6}" stroke-linecap="round"/>' if edge else ''
    up = e+f'<path d="M0 0V95" stroke="{sleeve}" stroke-width="{w}" stroke-linecap="round"/>'
    fo = f+f'<path d="M0 0V88" stroke="{sleeve}" stroke-width="{w-2}" stroke-linecap="round"/><circle cy="106" r="{hr}" fill="{skin}" stroke="{hstroke}" stroke-width="3"/>'
    return up, fo


def _plain_legs(col):
    sh = 'stroke="#9a8f93" stroke-width="3"'
    return (line([(232, 790), (232, 925)], col, 64)+ell((182, 925, 280, 974), "#f4eeee", sh),
            line([(328, 790), (328, 925)], col, 64)+ell((280, 925, 378, 974), "#f4eeee", sh))


# ------------------------------------------------------------------ character builders
def _marinette():
    JK, TOP = H((84, 74, 80)), H((242, 234, 234)); fl = ""
    for fx, fy in ((262, 640), (296, 660), (270, 690)):
        for a in range(5):
            ax, ay = fx+10*math.cos(a*1.2566), fy+10*math.sin(a*1.2566); fl += ell((ax-7, ay-7, ax+7, ay+7), H((238, 150, 170)))
        fl += ell((fx-4, fy-4, fx+4, fy+4), H((252, 220, 120)))
    for lx, ly, r in ((244, 668, 1), (300, 636, -1)):
        fl += poly([(lx, ly), (lx+16*r, ly-8), (lx+22*r, ly+6)], H((66, 80, 74)))
    torso = (rrect((185, 450, 375, 800), 60, JK)+poly([(238, 474), (322, 474), (334, 800), (226, 800)], TOP)+ell((246, 446, 314, 520), SK)
             + poly([(244, 462), (316, 462), (306, 500), (254, 500)], SK)+poly([(226, 468), (252, 466), (264, 560), (240, 640), (212, 540)], H((62, 54, 60)))
             + poly([(334, 468), (308, 466), (296, 560), (320, 640), (348, 540)], H((62, 54, 60)))+arc((244, 480, 316, 560), 20, 160, H((120, 110, 114)), 3)+fl)
    hb = ell((106, 106, 454, 440), NV)+poly(lock((130, 250), (112, 360), (140, 470), 80), NV)+poly(lock((430, 250), (448, 360), (420, 470), 80), NV)
    bangs = (poly([(112, 270), (118, 196), (196, 124), (330, 114), (436, 186), (448, 270), (430, 250), (300, 240), (170, 255)], NV)
             + "".join(poly(lock(r, c, t, w), NV) for r, c, t, w in (((178, 134), (140, 240), (180, 346), 84), ((262, 126), (220, 210), (222, 300), 84), ((330, 126), (372, 200), (338, 292), 84), ((404, 140), (434, 220), (404, 300), 60)))
             + "".join(line(bez(r, c, t, 10), NVL, 6) for r, c, t in (((170, 140), (130, 220), (168, 320)), ((260, 130), (222, 180), (232, 250)), ((406, 150), (432, 220), (404, 290)))))
    face = ell((136, 154, 424, 462), SK)+ell((166, 398, 210, 422), H((252, 190, 190)))+ell((350, 398, 394, 422), H((252, 190, 190)))
    tl = ell((80, 470, 206, 650), NV)+poly(lock((160, 440), (150, 470), (136, 520), 54), NV)+ell((146, 456, 170, 486), H((206, 54, 64)))+line(bez((110, 520), (100, 570), (130, 620), 10), NVL, 5)
    tr = ell((354, 470, 480, 650), NV)+poly(lock((400, 440), (410, 470), (424, 520), 54), NV)+ell((390, 456, 414, 486), H((206, 54, 64)))+line(bez((450, 520), (460, 570), (430, 620), 10), NVL, 5)
    ll, rl = _plain_legs("#3b4160")
    return dict(k='fr', lash=1, br=(NVD, (211, 312), (349, 312)), hb=hb, torso=torso, hf=face+bangs, tails=(tl, tr), arms=_arm(JK, 70, 28, SK, SK),
                A=(175, 512), B=(385, 512), low='', legs=(ll, rl))


def _adrien():
    G, GD, GL = H((247, 208, 120)), H((226, 170, 84)), H((255, 238, 176))
    hb = ell((112, 112, 448, 440), G)+"".join(poly(lock(*a), G) for a in (((150, 250), (100, 300), (74, 372), 70), ((410, 250), (462, 290), (486, 352), 64), ((262, 124), (288, 76), (338, 58), 54)))
    xl = lambda y: 232-12*(y-490)/270; xr = lambda y: 328+12*(y-490)/270
    st = ""
    for i, c in enumerate(((110, 176, 120), (150, 108, 190), (244, 202, 100))):
        y0 = 640+i*26; y1 = y0+18; st += poly([(xl(y0), y0), (xr(y0), y0), (xr(y1), y1), (xl(y1), y1)], H(c))
    WH = H((244, 238, 238))
    torso = (rrect((185, 450, 375, 800), 60, WH)+poly([(232, 490), (328, 490), (340, 800), (220, 800)], H((42, 36, 42)))+st
             + poly([(240, 462), (320, 462), (280, 548)], SK)+poly([(240, 462), (262, 470), (252, 500)], SH)
             + poly([(214, 472), (246, 462), (238, 548), (198, 520)], H((232, 224, 226)))+poly([(346, 472), (314, 462), (322, 548), (362, 520)], H((232, 224, 226))))
    fr = (poly([(118, 262), (124, 190), (196, 126), (330, 116), (432, 184), (442, 262), (430, 226), (300, 214), (180, 226)], G)
          + "".join(poly(lock(*a), G) for a in (((400, 150), (420, 215), (392, 262), 66), ((340, 140), (330, 225), (296, 276), 70), ((276, 132), (240, 215), (206, 282), 76), ((206, 140), (166, 220), (150, 310), 74), ((140, 190), (118, 240), (124, 300), 50)))
          + "".join(line(bez(*a, 10), GD, 6) for a in (((390, 150), (360, 200), (330, 232)), ((300, 140), (250, 190), (214, 236)), ((236, 132), (196, 180), (168, 232)), ((330, 120), (400, 150), (428, 214))))
          + "".join(line(bez(*a, 8), GL, 5) for a in (((340, 130), (300, 150), (268, 178)), ((240, 126), (212, 146), (196, 176)))))
    hf = ell((130, 316, 180, 396), SK)+ell((136, 154, 424, 462), SK)+ell((166, 398, 210, 422), H((252, 190, 190)))+ell((350, 398, 394, 422), H((252, 190, 190)))+fr
    ll, rl = _plain_legs("#3c4048")
    return dict(k='fr', lash=0, br=(H((206, 154, 88)), (211, 310), (349, 304)), hb=hb, torso=torso, hf=hf, tails=None, arms=_arm(WH, 70, 28, SK, SK),
                A=(175, 512), B=(385, 512), low='', legs=(ll, rl))


def _jp(c):
    """Parametric character (same fields as lesson.CHARS): hair, skin, top, accent, long_hair."""
    h, sk, tp, acc = H(c["hair"]), H(c["skin"]), H(c["top"]), H(c.get("accent", c["top"])); long_ = bool(c["long_hair"]); shoe = H((96, 66, 60))
    hb = rrect((110, 170, 450, 590), 110, h) if long_ else ''
    if long_:
        legs = []
        for x0 in (214, 306):
            legs.append(rrect((x0, 780, x0+42, 905), 16, sk)+rrect((x0-2, 862, x0+44, 912), 14, H((250, 248, 246)))+ell((x0-14, 896, x0+62, 940), shoe))
        low = poly([(178, 640), (382, 640), (414, 805), (146, 805)], H((122, 132, 196)))+"".join(
            line([(x, 700), (x-(280-x)*0.08, 800)], H((104, 114, 178)), 5) for x in range(170, 400, 46))
    else:
        legs = []
        for x0 in (198, 292):
            legs.append(rrect((x0, 640, x0+72, 890), 26, H((96, 112, 150)))+ell((x0-10, 876, x0+84, 926), shoe))
        low = rrect((190, 628, 370, 700), 26, H((96, 112, 150)))
    torso = rrect((185, 450, 375, 690), 60, tp)+poly([(245, 452), (280, 505), (315, 452)], sk)
    hd = ell((125, 145, 435, 455), sk)+f'<path d="M118 298A162 162 0 0 1 442 298Z" fill="{h}"/>'
    if long_:
        hd += "".join(ell((x-34, 225, x+34, 300+(12 if (x//48) % 2 else 0)), h) for x in range(150, 420, 48))+ell((112, 280, 168, 520), h)+ell((392, 280, 448, 520), h)
        hd += ell((340, 165, 392, 215), acc)+ell((355, 180, 377, 200), H((255, 240, 200)))
    else:
        hd += "".join(f'<path d="M{x} 225H{x+58}L{x+29} 305Z" fill="{h}"/>' for x in range(135, 420, 58))+f'<path d="M262 120H300L282 165Z" fill="{h}"/>'
    return dict(k='jp', hb=hb, torso=torso, hf=hd, tails=None, arms=_arm(tp, 70, 28, sk, sk), A=(175, 512), B=(385, 512), low=low, legs=tuple(legs))


# ------------------------------------------------------------------ faces
INK, MC = H((70, 45, 48)), H((120, 40, 52))


def _face_jp(expr, mouth, blink):
    s, ink, brow = "", INK, H((86, 56, 52))
    for ex in (222, 338):
        if blink or expr == "happy":
            s += arc((ex-26, 332, ex+26, 376), 200, 340, ink, 6)
        elif expr == "surprised":
            s += ell((ex-30, 308, ex+30, 392), H((55, 35, 42)))+ell((ex-18, 322, ex+4, 346), "#fff")+ell((ex+8, 362, ex+20, 374), "#fff")
        else:
            sh = 8 if expr == "confused" else 0
            s += ell((ex-24, 318, ex+24, 382), H((55, 35, 42)))+ell((ex-15+sh, 330, ex+3+sh, 350), "#fff")+ell((ex+6+sh, 358, ex+16+sh, 368), "#fff")
    if expr == "confused":
        s += line([(192, 300), (252, 294)], brow, 7)+line([(312, 270), (368, 282)], brow, 7)
    elif expr == "surprised":
        s += arc((190, 270, 254, 300), 200, 340, brow, 7)+arc((306, 270, 370, 300), 200, 340, brow, 7)
    elif expr == "sad":
        s += line([(192, 302), (252, 284)], brow, 7)+line([(308, 284), (368, 302)], brow, 7)
    chk = H((246, 140, 140)) if expr == "shy" else H((250, 172, 170)); k = 8 if expr == "shy" else 0
    s += ell((168-k, 388-k, 215+k, 412+k), chk)+ell((345-k, 388-k, 392+k, 412+k), chk)
    if mouth == 1: s += ell((268, 408, 292, 430), MC)
    elif mouth >= 2: s += ell((258, 405, 302, 442), MC)+ell((266, 424, 294, 440), H((236, 120, 132)))
    elif expr == "happy": s += arc((248, 394, 312, 440), 20, 160, ink, 6)
    elif expr == "surprised": s += ell((270, 410, 290, 436), MC)
    elif expr == "confused": s += line([(264, 424), (276, 416), (288, 426), (300, 416)], ink, 5)
    elif expr == "sad": s += arc((262, 418, 298, 446), 200, 340, ink, 5)
    elif expr == "shy": s += arc((270, 404, 292, 424), 20, 160, ink, 4)
    else: s += arc((262, 400, 298, 430), 20, 160, ink, 5)
    if expr == "confused":
        s += poly([(430, 165), (416, 205), (444, 205)], H((176, 216, 240)))+ell((414, 192, 446, 226), H((176, 216, 240)))
    return s


_BR = {"neutral": (0, 0), "happy": (0, -3), "surprised": (0, -12), "confused": (-12, 0), "sad": (-12, 2), "shy": (-6, 0)}


def _face_fr(ch, expr, mouth, blink):
    c, MCf, inkf = ch, H((128, 48, 62)), H((92, 52, 56))
    eyes = ""
    for x in (214, 346):
        side = -1 if x < 280 else 1
        if blink or expr == "happy":
            y = 366 if expr == "happy" and not blink else 361
            eyes += f'<path d="M{x-28.2} {y}A30 23 0 0 1 {x+28.2} {y}" fill="none" stroke="#3c222e" stroke-width="8" stroke-linecap="round"/>'
            if c["lash"]: eyes += f'<path d="M{x+side*30} 372L{x+side*42} 362" stroke="#341c28" stroke-width="5" stroke-linecap="round"/>'
            continue
        sc = 1.1 if expr == "surprised" else 1
        eyes += (f'<g transform="translate({x} 357) scale({sc}) translate({-x} -357)"><ellipse cx="{x}" cy="357" rx="27" ry="39" fill="#3a1e2e"/><ellipse cx="{x}" cy="381" rx="20" ry="13" fill="#6c3846"/>'
                 f'<ellipse cx="{x-6.5}" cy="341" rx="10.5" ry="13" fill="#fff"/><ellipse cx="{x+11.5}" cy="374" rx="5.5" ry="6" fill="#fff"/>'
                 f'<path d="M{x-29.9} 336.5A31 33 0 0 1 {x+29.9} 336.5" fill="none" stroke="#341c28" stroke-width="7"/>')
        if c["lash"]: eyes += f'<path d="M{x+side*28} 344L{x+side*44} 330" stroke="#341c28" stroke-width="5" stroke-linecap="round"/>'
        eyes += '</g>'
    cy = 426
    if mouth == 1: m = f'<ellipse cx="280" cy="{cy}" rx="12" ry="12" fill="{MCf}"/>'
    elif mouth >= 2: m = f'<ellipse cx="280" cy="{cy+2}" rx="21" ry="18" fill="{MCf}"/><ellipse cx="280" cy="{cy+10}" rx="13" ry="7" fill="#ee8090"/>'
    elif expr == "happy": m = f'<path d="M258 {cy-12}Q280 {cy+26} 302 {cy-12}Z" fill="{MCf}" stroke="{MCf}" stroke-width="4" stroke-linejoin="round"/>'
    elif expr == "surprised": m = f'<ellipse cx="280" cy="{cy+2}" rx="14" ry="16" fill="{MCf}"/>'
    elif expr in ("confused", "sad"): m = f'<path d="M262 {cy+6}Q271 {cy-5} 280 {cy+2}Q289 {cy+9} 298 {cy-2}" fill="none" stroke="{inkf}" stroke-width="5" stroke-linecap="round"/>'
    else: m = f'<path d="M262.6 {cy+0.4}A18 13 0 0 0 297.4 {cy+0.4}" fill="none" stroke="{inkf}" stroke-width="5" stroke-linecap="round"/>'
    rot, dy = _BR.get(expr, (0, 0)); col, (lx, ly), (rx, ry) = c["br"]
    br = lambda cx, cyy, r: (f'<g transform="translate(0 {dy}) rotate({r} {cx} {cyy})"><path d="M{cx-31} {cyy-4.8}A33 14 0 0 1 {cx+31} {cyy-4.8}" fill="none" stroke="{col}" stroke-width="5" stroke-linecap="round"/></g>')
    sweat = '<path d="M420 250q24 38 0 52q-24-14 0-52z" fill="#7fd0ff"/>' if expr == "confused" else ''
    return br(lx, ly, rot)+br(rx, ry, -rot)+eyes+m+sweat


# ------------------------------------------------------------------ registry + render
_CACHE = {}


def _get(name, c):
    key = (name.lower(), None if name.lower() in ("marinette", "adrien") or c is None else tuple(str(c.get(k)) for k in ("hair", "skin", "top", "accent", "long_hair")))
    if key not in _CACHE:
        n = name.lower()
        _CACHE[key] = _marinette() if n == "marinette" else _adrien() if n == "adrien" else (_jp(c) if c is not None else None)
    return _CACHE[key]


def skin_rgb(name, c=None):
    """Skin colour (r, g, b) of a character, for the hand redrawn over a held item."""
    if name.lower() in ("marinette", "adrien") or c is None:
        return (253, 227, 203)
    return tuple(int(v) for v in c["skin"])


def available(name, c=None):
    return resvg_py is not None and _get(name, c) is not None


def held_hand(walk):
    """Where the right hand is (drawing coordinates) while holding an item or umbrella."""
    swing = {0: 0, 1: 6, 2: 0, 3: -6}[int(walk)]
    bu, bf = -4-swing, -3
    r = math.radians
    ex, ey = 385-95*math.sin(r(bu)), 512+95*math.cos(r(bu))
    a = bu+bf
    return ex-106*math.sin(r(a)), ey+106*math.cos(r(a))


def svg(name, c, mouth, blink, expr, walk, arm, held, t, w, h):
    ch = _get(name, c)
    if ch is None: return None
    ph = (sum(map(ord, name)) % 7)*0.9
    sway, br = math.sin(t*1.6+ph), 1+math.sin(t*2+ph)*.012
    lfL, lfR = (28 if walk == 1 else 0), (28 if walk == 3 else 0)
    swing = {0: 0, 1: 6, 2: 0, 3: -6}[walk]
    wave = arm and 1
    Au, Af = 10+swing, 8
    if wave: Bu, Bf = -150, -10+(22 if arm == 1 else -22)
    elif held: Bu, Bf = -4-swing, -3
    else: Bu, Bf = -10-swing, -8
    hT = f'translate(0 {sway*4:.2f}) rotate({sway*1.5:.2f} 280 460)'
    tT = f'rotate(0 280 790) translate(280 790) scale(1 {br:.4f}) translate(-280 -790)'
    ups, fos = ch["arms"]
    tails = ''
    if ch["tails"]:
        lag = math.sin(t*2.2+ph)*4+(swing*0.8)
        tails = (f'<g transform="{hT} rotate({lag:.2f} 158 462)">{ch["tails"][0]}</g><g transform="{hT} rotate({lag:.2f} 402 462)">{ch["tails"][1]}</g>')
    arm_svg = lambda pos, u, f, upsv, fosv: f'<g transform="translate({pos[0]} {pos[1]}) rotate({u:.1f})">{upsv}<g transform="translate(0 95) rotate({f:.1f})">{fosv}</g></g>'
    face = _face_jp(expr, mouth, blink) if ch["k"] == 'jp' else _face_fr(ch, expr, mouth, blink)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="-12 -10 583 1000">'
            f'<g transform="translate(0 {-lfL})">{ch["legs"][0]}</g><g transform="translate(0 {-lfR})">{ch["legs"][1]}</g>{ch["low"]}'
            f'<g transform="{hT}">{ch["hb"]}</g><g transform="{tT}">{ch["torso"]}</g>{tails}'
            f'<g transform="{tT}">{arm_svg(ch["A"], Au, Af, ups, fos)}{arm_svg(ch["B"], Bu, Bf, ups, fos)}</g>'
            f'<g transform="{hT}">{ch["hf"]}{face}</g></svg>')


def render(name, c, mouth, blink, expr, walk, arm, held, t, w, h):
    """RGBA sprite of size (w, h), or None if this character cannot be drawn this way."""
    if resvg_py is None: return None
    s = svg(name, c, int(mouth), bool(blink), expr, int(walk), int(arm), bool(held), float(t), w, h)
    if s is None: return None
    return Image.open(io.BytesIO(bytes(resvg_py.svg_to_bytes(svg_string=s, width=w, height=h)))).convert("RGBA")
