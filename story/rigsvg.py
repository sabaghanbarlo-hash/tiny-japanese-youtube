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
    bk = hb+ell((108, 280, 452, 470), NV)+"".join(line(bez(r_, c_, t_, 10), NVL, 6) for r_, c_, t_ in (((200, 150), (176, 250), (206, 370)), ((290, 140), (300, 250), (284, 380)), ((372, 150), (396, 250), (366, 370))))
    tb = rrect((185, 450, 375, 800), 60, JK)+ell((246, 436, 314, 486), SK)+line([(280, 492), (280, 790)], H((62, 54, 60)), 4)
    return dict(k='fr', lash=1, br=(NVD, (211, 312), (349, 312)), hb=hb, torso=torso, hf=face+bangs, bk=bk, tb=tb, tails=(tl, tr), arms=_arm(JK, 70, 28, SK, SK),
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
    bk = hb+ell((112, 300, 448, 466), G)+"".join(line(bez(*a_, 10), GD, 6) for a_ in (((190, 150), (176, 250), (200, 380)), ((280, 130), (290, 250), (276, 390)), ((370, 150), (386, 250), (360, 380))))
    tb = rrect((185, 450, 375, 800), 60, WH)+poly([(232, 490), (328, 490), (340, 800), (220, 800)], H((42, 36, 42)))+ell((246, 436, 314, 486), SK)
    return dict(k='fr', lash=0, br=(H((206, 154, 88)), (211, 310), (349, 304)), hb=hb, torso=torso, hf=hf, bk=bk, tb=tb, tails=None, arms=_arm(WH, 70, 28, SK, SK),
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
    hk = H(tuple(max(0, int(v*0.8)) for v in c["hair"]))
    bk = ell((118, 138, 442, 464), h)+"".join(line(bez(a_, b_, d_, 10), hk, 6) for a_, b_, d_ in (((200, 170), (186, 280), (206, 400)), ((280, 150), (290, 270), (276, 410)), ((360, 170), (376, 280), (352, 400))))
    tb = rrect((185, 450, 375, 690), 60, tp)+ell((244, 436, 316, 482), sk)
    bkl = (rrect((122, 330, 438, 610), 74, h)+line([(280, 360), (280, 590)], hk, 5)) if long_ else ''
    return dict(k='jp', hb=hb, torso=torso, hf=hd, bk=bk, tb=tb, bkl=bkl, tails=None, arms=_arm(tp, 70, 28, sk, sk), A=(175, 512), B=(385, 512), low=low, legs=tuple(legs))


# ------------------------------------------------------------------ faces
INK, MC = H((70, 45, 48)), H((120, 40, 52))


def _face_jp(expr, mouth, blink):
    if expr in NEWX: return _face_jp_x(expr, mouth, blink)
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


_BR = {"neutral": (0, 0), "happy": (0, -3), "surprised": (0, -12), "confused": (-12, 0), "sad": (-12, 2), "shy": (-6, 0),
       "worried": (-16, -2), "annoyed": (8, 3), "angry": (15, 5), "smirk": (-4, 0), "joy": (0, -4), "laugh": (0, -5), "thinking": (-8, -4), "excited": (0, -9), "determined": (9, 1)}


def _face_fr(ch, expr, mouth, blink):
    c, MCf, inkf = ch, H((128, 48, 62)), H((92, 52, 56))
    eyes = ""
    for x in (214, 346):
        side = -1 if x < 280 else 1
        if blink or expr in ("happy", "joy", "laugh"):
            y = 366 if expr in ("happy", "joy", "laugh") and not blink else 361
            eyes += f'<path d="M{x-28.2} {y}A30 23 0 0 1 {x+28.2} {y}" fill="none" stroke="#3c222e" stroke-width="8" stroke-linecap="round"/>'
            if c["lash"]: eyes += f'<path d="M{x+side*30} 372L{x+side*42} 362" stroke="#341c28" stroke-width="5" stroke-linecap="round"/>'
            continue
        sc = 1.1 if expr == "surprised" else 1
        eyes += (f'<g transform="translate({x} 357) scale({sc}) translate({-x} -357)"><ellipse cx="{x}" cy="357" rx="27" ry="39" fill="#3a1e2e"/><ellipse cx="{x}" cy="381" rx="20" ry="13" fill="#6c3846"/>'
                 f'<ellipse cx="{x-6.5}" cy="341" rx="10.5" ry="13" fill="#fff"/><ellipse cx="{x+11.5}" cy="374" rx="5.5" ry="6" fill="#fff"/>'
                 f'<path d="M{x-29.9} 336.5A31 33 0 0 1 {x+29.9} 336.5" fill="none" stroke="#341c28" stroke-width="7"/>')
        if c["lash"]: eyes += f'<path d="M{x+side*28} 344L{x+side*44} 330" stroke="#341c28" stroke-width="5" stroke-linecap="round"/>'
        eyes += '</g>'
    if expr == "annoyed":
        for x in (214, 346): eyes += f'<rect x="{x-34}" y="318" width="68" height="20" fill="{SK}"/><path d="M{x-31} 338H{x+31}" stroke="#341c28" stroke-width="11" stroke-linecap="round"/>'
    cy = 426
    if expr == "laugh":
        dd = (24, 34, 46)[min(int(mouth), 2)]
        m = (f'<path d="M254 {cy-12}Q280 {cy-12+2*dd} 306 {cy-12}Z" fill="{MCf}" stroke="{MCf}" stroke-width="4" stroke-linejoin="round"/>'
             f'<path d="M259 {cy-9}H301" stroke="#fff" stroke-width="7" stroke-linecap="round"/><ellipse cx="280" cy="{cy-12+dd-9}" rx="14" ry="6" fill="#ee8090"/>')
    elif mouth == 1: m = f'<ellipse cx="280" cy="{cy}" rx="12" ry="12" fill="{MCf}"/>'
    elif mouth >= 2: m = f'<ellipse cx="280" cy="{cy+2}" rx="21" ry="18" fill="{MCf}"/><ellipse cx="280" cy="{cy+10}" rx="13" ry="7" fill="#ee8090"/>'
    elif expr in ("happy", "joy", "excited"): m = f'<path d="M{258-(6 if expr != "happy" else 0)} {cy-12}Q280 {cy+(36 if expr != "happy" else 26)} {302+(6 if expr != "happy" else 0)} {cy-12}Z" fill="{MCf}" stroke="{MCf}" stroke-width="4" stroke-linejoin="round"/>'
    elif expr == "annoyed": m = f'<path d="M262 {cy}H298" stroke="{inkf}" stroke-width="6" stroke-linecap="round"/>'
    elif expr == "angry": m = f'<path d="M260 {cy+10}Q280 {cy-8} 300 {cy+10}" fill="none" stroke="{inkf}" stroke-width="6" stroke-linecap="round"/>'
    elif expr == "smirk": m = f'<path d="M260 {cy-2}Q288 {cy+16} 312 {cy-14}" fill="none" stroke="{inkf}" stroke-width="6" stroke-linecap="round"/>'
    elif expr == "thinking": m = f'<ellipse cx="288" cy="{cy+2}" rx="8" ry="10" fill="{MCf}"/>'
    elif expr == "determined": m = f'<path d="M258 {cy-6}Q280 {cy+14} 302 {cy-6}" fill="none" stroke="{inkf}" stroke-width="6" stroke-linecap="round"/>'
    elif expr == "surprised": m = f'<ellipse cx="280" cy="{cy+2}" rx="14" ry="16" fill="{MCf}"/>'
    elif expr in ("confused", "sad", "worried"): m = f'<path d="M262 {cy+6}Q271 {cy-5} 280 {cy+2}Q289 {cy+9} 298 {cy-2}" fill="none" stroke="{inkf}" stroke-width="5" stroke-linecap="round"/>'
    else: m = f'<path d="M262.6 {cy+0.4}A18 13 0 0 0 297.4 {cy+0.4}" fill="none" stroke="{inkf}" stroke-width="5" stroke-linecap="round"/>'
    rot, dy = _BR.get(expr, (0, 0)); col, (lx, ly), (rx, ry) = c["br"]
    br = lambda cx, cyy, r: (f'<g transform="translate(0 {dy}) rotate({r} {cx} {cyy})"><path d="M{cx-31} {cyy-4.8}A33 14 0 0 1 {cx+31} {cyy-4.8}" fill="none" stroke="{col}" stroke-width="5" stroke-linecap="round"/></g>')
    sweat = '<path d="M420 250q24 38 0 52q-24-14 0-52z" fill="#7fd0ff"/>' if expr in ("confused", "worried") else ''
    if expr == "angry": sweat += '<path d="M410 250L440 280M440 250L410 280" stroke="#e25555" stroke-width="9" stroke-linecap="round"/>'
    if expr == "laugh": sweat += '<ellipse cx="170" cy="396" rx="8" ry="13" fill="#9fd8ff"/><ellipse cx="390" cy="396" rx="8" ry="13" fill="#9fd8ff"/>'
    return br(lx, ly, rot)+br(rx, ry, -rot)+eyes+m+sweat



# ------------------------------------------------------------------ v3: extra expressions, poses (hand-target IK), props
NEWX = ("worried", "annoyed", "angry", "smirk", "joy", "thinking", "excited", "determined", "laugh")
L1, L2 = 95.0, 106.0       # upper arm / forearm length (see _arm)


def _face_jp_x(expr, mouth, blink):
    s, ink, brow, dark = "", INK, H((86, 56, 52)), H((55, 35, 42))
    sh = 10 if expr == "thinking" else 0
    for ex in (222, 338):
        if blink or expr in ("joy", "laugh"):
            s += arc((ex-26, 332, ex+26, 376), 200, 340, ink, 7 if expr == "laugh" else 6)
        elif expr == "annoyed":
            s += ell((ex-24, 340, ex+24, 384), dark)+ell((ex-12, 352, ex+4, 368), "#fff")+line([(ex-30, 338), (ex+30, 338)], ink, 9)
        elif expr == "excited":
            s += ell((ex-28, 310, ex+28, 388), dark)+ell((ex-16, 322, ex+6, 348), "#fff")+ell((ex+8, 362, ex+22, 376), "#fff")
        else:
            up = -8 if expr == "thinking" else 0
            s += ell((ex-24, 318, ex+24, 382), dark)+ell((ex-15+sh, 330+up, ex+3+sh, 350+up), "#fff")+ell((ex+6+sh, 358+up, ex+16+sh, 368+up), "#fff")
    B = {"worried": [((192, 306), (252, 282)), ((308, 282), (368, 306))],
         "annoyed": [((190, 294), (252, 312)), ((308, 312), (370, 294))],
         "angry": [((188, 286), (254, 316)), ((306, 316), (372, 286))],
         "smirk": [((192, 292), (252, 284)), ((308, 296), (368, 306))],
         "joy": [((190, 276), (252, 268)), ((308, 268), (370, 276))],
         "laugh": [((190, 272), (252, 262)), ((308, 262), (370, 272))],
         "thinking": [((192, 296), (252, 296)), ((310, 268), (370, 280))],
         "excited": [((190, 266), (252, 258)), ((308, 258), (370, 266))],
         "determined": [((190, 290), (252, 304)), ((308, 304), (370, 290))]}[expr]
    for a, b in B:
        s += line([a, b], brow, 7)
    chk = H((250, 172, 170)); k = 4 if expr in ("joy", "excited", "laugh") else 0
    s += ell((168-k, 388-k, 215+k, 412+k), chk)+ell((345-k, 388-k, 392+k, 412+k), chk)
    if expr == "laugh":      # open "ha ha" mouth: a D shape that opens wider with the mouth value, teeth on top, tongue below, little tears
        dd = (34, 48, 62)[min(int(mouth), 2)]
        s += f'<path d="M242 396Q280 {396+2*dd} 318 396Z" fill="{MC}" stroke="{MC}" stroke-width="5" stroke-linejoin="round"/>'
        s += f'<path d="M250 399H310" stroke="#fff" stroke-width="9" stroke-linecap="round"/>'
        s += ell((264, 396+dd-22, 296, 396+dd-4), H((236, 120, 132)))
        for ex in (222, 338):
            tx = ex-40 if ex < 280 else ex+40
            s += ell((tx-8, 382, tx+8, 408), H((176, 216, 240)))
    elif mouth == 1: s += ell((268, 408, 292, 430), MC)
    elif mouth >= 2: s += ell((258, 405, 302, 442), MC)+ell((266, 424, 294, 440), H((236, 120, 132)))
    elif expr in ("joy", "excited"): s += f'<path d="M244 398Q280 458 316 398Z" fill="{MC}" stroke="{MC}" stroke-width="5" stroke-linejoin="round"/>'+ell((262, 424, 298, 440), H((236, 120, 132)))
    elif expr == "worried": s += line([(262, 428), (271, 420), (280, 428), (289, 420), (298, 428)], ink, 5)
    elif expr == "annoyed": s += line([(262, 424), (298, 424)], ink, 6)
    elif expr == "angry": s += arc((258, 414, 302, 446), 200, 340, ink, 6)
    elif expr == "smirk": s += f'<path d="M256 420Q286 440 312 406" fill="none" stroke="{ink}" stroke-width="6" stroke-linecap="round"/>'
    elif expr == "thinking": s += ell((284, 412, 302, 430), MC)
    else: s += arc((256, 404, 304, 440), 20, 160, ink, 6)
    if expr == "worried": s += poly([(430, 165), (416, 205), (444, 205)], H((176, 216, 240)))+ell((414, 192, 446, 226), H((176, 216, 240)))
    if expr == "angry": s += line([(424, 170), (446, 192)], H((226, 84, 84)), 8)+line([(446, 170), (424, 192)], H((226, 84, 84)), 8)
    return s


def ik(sh, target, outward):
    """Two-link arm: angles (upper, fore) in degrees so the hand reaches `target`. 0 = hanging down, + swings the hand to screen-left.
    outward = -1 for the left-screen arm (A), +1 for the right-screen arm (B); prefers a low elbow bent away from the body."""
    dx, dy = target[0]-sh[0], target[1]-sh[1]
    D = max(30.0, min(math.hypot(dx, dy), L1+L2-1.0))
    phi = math.atan2(-dx, dy)
    a = math.acos(max(-1.0, min(1.0, (L1*L1+D*D-L2*L2)/(2*L1*D))))
    best = None
    for sg in (1, -1):
        u = phi+sg*a
        ex, ey = sh[0]-L1*math.sin(u), sh[1]+L1*math.cos(u)
        sc = 0.5*outward*ex+ey
        if best is None or sc > best[0]: best = (sc, u, ex, ey)
    _, u, ex, ey = best
    n = math.hypot(dx, dy) or 1.0
    hx, hy = sh[0]+dx/n*D, sh[1]+dy/n*D
    f = math.atan2(-(hx-ex), hy-ey)-u
    wrap = lambda v: (math.degrees(v)+180) % 360-180
    return wrap(u), wrap(f)


# hand targets in drawing coordinates (shoulders A=(175,512) B=(385,512); head centre ~(280,300); mouth ~(280,420); right ear ~(440,340))
POSES = {
    "point": dict(B=(578, 500)),
    "shrug": dict(A=(66, 548), B=(494, 548), tilt=7),
    "hips": dict(A=(166, 655), B=(394, 655)),
    "phone": dict(B=(440, 348), tilt=5),
    "cover": dict(B=(292, 428)),
    "think": dict(B=(322, 444), A=(292, 592), tilt=6),
    "show": dict(B=(474, 430)),
    "cross": dict(A=(348, 586), B=(212, 586)),
    "clasp": dict(A=(272, 574), B=(292, 574)),
    "bow": dict(A=(244, 642), B=(316, 642), lean=17, tilt=9),
    "cheer": dict(A=(112, 336), B=(448, 336), tilt=-4),
    "hold_box": dict(A=(236, 612), B=(324, 612)),
}
PROP_HAND = {"phone", "broom"}          # attached to the right-screen forearm (move with the hand)
PROP_FRONT = {"box", "cake_box"}        # carried in front of the body with both hands


def _prop_hand(p):
    if p == "phone":
        return '<rect x="-17" y="82" width="34" height="64" rx="8" fill="#2c3245"/><rect x="-12" y="89" width="24" height="46" rx="4" fill="#a9dcff"/><circle cx="0" cy="141" r="2.5" fill="#6a728c"/>'
    if p == "broom":
        return ('<line x1="0" y1="-70" x2="0" y2="214" stroke="#a06f3d" stroke-width="10" stroke-linecap="round"/>'
                '<path d="M-24 206L24 206L38 266L-38 266Z" fill="#e2b94e"/><path d="M-14 210L-18 264M0 210V266M14 210L18 264" stroke="#b98a2c" stroke-width="3" fill="none"/>')
    return ""


def _prop_front(p):
    if p == "cake_box":
        return ('<rect x="204" y="560" width="152" height="82" rx="8" fill="#fff6f0" stroke="#e8c9c0" stroke-width="4"/>'
                '<rect x="224" y="574" width="112" height="40" rx="6" fill="#ffd9e2"/><ellipse cx="280" cy="590" rx="30" ry="12" fill="#fff"/><circle cx="280" cy="578" r="7" fill="#e5484d"/>'
                '<path d="M204 600H356M280 560V642" stroke="#f07a9a" stroke-width="7"/>')
    return ('<rect x="204" y="566" width="152" height="76" rx="8" fill="#d9a066" stroke="#b27a43" stroke-width="4"/>'
            '<rect x="198" y="556" width="164" height="26" rx="6" fill="#e8b57c" stroke="#b27a43" stroke-width="4"/><path d="M280 556V642" stroke="#b27a43" stroke-width="4"/>')


def _lerp_ang(a, b, k):
    d = (b-a+180) % 360-180
    return a+d*k


def hand_B(walk, pose=None, pk=1.0):
    """Right-screen hand position (drawing coordinates) while holding an item, with an optional gesture blended in."""
    swing = {0: 0, 1: 6, 2: 0, 3: -6}[int(walk)]
    bu, bf = -4-swing, -3
    if pose in POSES and "B" in POSES[pose]:
        u, f = ik((385, 512), POSES[pose]["B"], 1); k = max(0.0, min(1.0, float(pk)))
        bu, bf = _lerp_ang(bu, u, k), _lerp_ang(bf, f, k)
    r = math.radians
    ex, ey = 385-95*math.sin(r(bu)), 512+95*math.cos(r(bu)); a_ = r(bu+bf)
    return ex-106*math.sin(a_), ey+106*math.cos(a_)


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


def svg(name, c, mouth, blink, expr, walk, arm, held, t, w, h, pose=None, pk=1.0, prop=None, back=False):
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
    tilt = lean = 0.0
    if prop in PROP_FRONT and not pose: pose = "hold_box"
    if pose in POSES:
        pz = POSES[pose]; pk = max(0.0, min(1.0, float(pk)))
        if "A" in pz: Au, Af = (_lerp_ang(a0, a1, pk) for a0, a1 in zip((Au, Af), ik(ch["A"], pz["A"], -1)))
        if "B" in pz: Bu, Bf = (_lerp_ang(a0, a1, pk) for a0, a1 in zip((Bu, Bf), ik(ch["B"], pz["B"], 1)))
        tilt, lean = pz.get("tilt", 0)*pk, pz.get("lean", 0)*pk
    hT = f'rotate({lean:.2f} 280 790) translate(0 {sway*4:.2f}) rotate({sway*1.5+tilt:.2f} 280 460)'
    tT = f'rotate({lean:.2f} 280 790) translate(280 790) scale(1 {br:.4f}) translate(-280 -790)'
    ups, fos = ch["arms"]
    tails = ''
    if ch["tails"]:
        lag = math.sin(t*2.2+ph)*4+(swing*0.8)
        tails = (f'<g transform="{hT} rotate({lag:.2f} 158 462)">{ch["tails"][0]}</g><g transform="{hT} rotate({lag:.2f} 402 462)">{ch["tails"][1]}</g>')
    arm_svg = lambda pos, u, f, upsv, fosv, extra='': f'<g transform="translate({pos[0]} {pos[1]}) rotate({u:.1f})">{upsv}<g transform="translate(0 95) rotate({f:.1f})">{fosv.replace("<circle", extra+"<circle", 1) if extra else fosv}</g></g>'
    front = ''
    if prop in PROP_FRONT and pose == 'hold_box':
        sk = H(skin_rgb(name, c)); pz = POSES['hold_box']
        front = _prop_front(prop)+''.join(f'<circle cx="{p[0]}" cy="{p[1]}" r="26" fill="{sk}" stroke="{sk}" stroke-width="3"/>' for p in (pz['A'], pz['B']))
    face = '' if back else (_face_jp(expr, mouth, blink) if ch["k"] == 'jp' else _face_fr(ch, expr, mouth, blink))
    torso_s = (ch["tb"]+ch.get("bkl", '')) if back else ch["torso"]       # seen from behind: plain back, hair only, no face
    head_s = ch["bk"] if back else ch["hf"]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="-12 -10 583 1000">'
            f'<g transform="translate(0 {-lfL})">{ch["legs"][0]}</g><g transform="translate(0 {-lfR})">{ch["legs"][1]}</g>{ch["low"]}'
            f'<g transform="{hT}">{ch["hb"]}</g><g transform="{tT}">{torso_s}</g>{tails}'
            f'<g transform="{tT}">{arm_svg(ch["A"], Au, Af, ups, fos)}{arm_svg(ch["B"], Bu, Bf, ups, fos, _prop_hand(prop) if prop in PROP_HAND else "")}{front}</g>'
            f'<g transform="{hT}">{head_s}{face}</g></svg>')


def render(name, c, mouth, blink, expr, walk, arm, held, t, w, h, pose=None, pk=1.0, prop=None, back=False):
    """RGBA sprite of size (w, h), or None if this character cannot be drawn this way."""
    if resvg_py is None: return None
    s = svg(name, c, int(mouth), bool(blink), expr, int(walk), int(arm), bool(held), float(t), w, h, pose, pk, prop, back)
    if s is None: return None
    return Image.open(io.BytesIO(bytes(resvg_py.svg_to_bytes(svg_string=s, width=w, height=h)))).convert("RGBA")
