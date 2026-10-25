"""Cover image (YouTube thumbnail) that shows the video's own setting and mood.

Usage (from the repository root):
    python story/make_cover.py stories/<name>.txt output/<name>.thumbnail.png

The script is read with the story engine, the most atmospheric moment is chosen (rain, snow, night, sunset, otherwise
the place the story spends most time in) and drawn as a 1280x720 picture: that place with its weather and light, Mika and
Alex big in front (sharing an umbrella when it rains), and the title on a banner. So a rainy story looks rainy, a
festival looks like a festival, and every video gets a different cover.
"""
import glob, os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_argv = sys.argv
sys.argv = sys.argv[:1]
import lesson as L          # noqa: E402  (story engine)
import acting as A          # noqa: E402
sys.argv = _argv

from PIL import Image, ImageDraw, ImageFilter, ImageFont   # noqa: E402

W, H = 1920, 1080
OUT = 0.72                                  # character size (the video uses 0.69)
INK = (44, 36, 60)

ACCENT = {"rain": (62, 108, 190), "storm": (70, 84, 160), "snow": (84, 150, 214), "night": (112, 86, 190),
          "sunset": (232, 112, 64), "morning": (236, 140, 80), None: (232, 96, 130)}


def title_font(size):
    for pat in ("/usr/share/fonts/**/NotoSansCJK-Black.ttc", "/usr/share/fonts/**/NotoSansCJK-Bold.ttc"):
        g = sorted(glob.glob(pat, recursive=True))
        if g:
            try:
                return ImageFont.truetype(g[0], size)
            except Exception:
                pass
    return L.font(size, True)


def pick_moment(B):
    """The segment that best shows the atmosphere of the story."""
    lines = {}
    for s in B["segs"]:
        if s["kind"] == "story":
            lines[s["scene"]] = lines.get(s["scene"], 0) + 1
    best, best_score = None, -1
    for s in B["segs"]:
        if s["kind"] not in ("story", "act"):
            continue
        score = lines.get(s["scene"], 0)
        if s.get("tod") in ("night", "sunset"):
            score += 6
        if s.get("weather"):
            score += 10 + (3 if s.get("tod") in ("night", "sunset") else 0)
        if s["scene"] in ("train",) and not s.get("weather"):
            score += 2
        if score > best_score:
            best, best_score = s, score
    return best or B["segs"][0]


def accent_for(seg):
    return ACCENT.get(seg.get("weather")) if seg.get("weather") else ACCENT.get(seg.get("tod")) or ACCENT[None]


def draw_umbrella(fr, cxs, y_top, k, holder_x, sheltered):
    import atmos as AT
    xs = list(cxs)
    cx = sum(xs) / len(xs) + 30
    R = max(400.0, (max(xs) - min(xs)) / 2 + 280)
    rim = y_top + 62 * k
    hgt = 0.5 * R
    d = ImageDraw.Draw(fr)
    hand = (holder_x + 64 * k, y_top + 404 * k)
    d.line([(cx, rim - hgt), hand], fill=(86, 66, 58), width=14)
    AT._canopy(d, cx, rim, R, hgt, AT._UMB_COLORS["Mika"])
    sheltered.append((cx, R, rim - hgt, rim))


def banner(fr, meta, accent):
    d = ImageDraw.Draw(fr)
    text = meta["title"]
    box_w = 1700
    size, ls, f = 118, [text], None
    while size > 64:
        f = title_font(size)
        ls = L.wrap(text, f, box_w - 140)
        if len(ls) <= 2 and max(f.getlength(x) for x in ls) <= box_w - 140:
            break
        size -= 6
    lh = int(size * 1.18)
    bh = lh * len(ls) + 70
    bw = min(box_w, int(max(f.getlength(x) for x in ls)) + 190)
    x0, y0 = (W - bw) // 2, 64
    sh = Image.new("RGBA", fr.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((x0 + 8, y0 + 18, x0 + bw + 8, y0 + bh + 18), radius=70, fill=(0, 0, 0, 110))
    fr.paste(Image.alpha_composite(Image.new("RGBA", fr.size, (0, 0, 0, 0)), sh.filter(ImageFilter.GaussianBlur(14))), (0, 0), sh.filter(ImageFilter.GaussianBlur(14)))
    d.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), radius=70, fill=(255, 253, 249), outline=accent, width=12)
    y = y0 + 35
    for x in ls:
        d.text((W // 2, y), x, font=f, fill=INK, anchor="ma")
        y += lh
    ep = f"Ep.{meta['episode']}" if meta.get("episode") else ""
    if ep:
        pf = title_font(54)
        pw = int(pf.getlength(ep)) + 64
        d.rounded_rectangle((x0 + 36, y0 - 38, x0 + 36 + pw, y0 + 38), radius=38, fill=accent, outline=(255, 255, 255), width=6)
        d.text((x0 + 36 + pw / 2, y0), ep, font=pf, fill=(255, 255, 255), anchor="mm")


def make_cover(script, out_path):
    with tempfile.TemporaryDirectory() as tmp:
        B = L.build(script, "-12%", True, tmp)
    meta = B["meta"]
    seg = dict(pick_moment(B))
    seg["prev_weather"] = seg.get("weather")
    scene, var = seg["scene"], seg.get("variant", 0)
    bg, fg = L.make_scene(scene, var)
    holder = type("R", (), {})()
    tt = seg["start"] + 3.0
    fr, fg = A.atmos_frame(holder, scene, var, bg, fg, seg, tt)
    fr = fr.convert("RGBA")
    fr.paste(fg, (0, L.FLOOR_Y - 40), fg)

    wet = seg.get("weather") in ("rain", "storm") and scene in A.AT.OUTDOOR
    snow = seg.get("weather") == "snow" and scene in A.AT.OUTDOOR
    k = OUT / L.STAGE_OUT
    cast = [("Mika", 640, "happy", 0), ("Alex", 1280, "surprised" if wet else "happy", 0)]
    if int(meta.get("episode") or 0) % 2:                      # vary who stands where
        cast = [("Alex", 640, cast[1][2], 0), ("Mika", 1280, cast[0][2], 0)]
    sprites = []
    for nm, cx, expr, arm in cast:
        s = A.rig(nm, 1 if expr == "surprised" else 0, False, expr, 0, 0, OUT)
        pad = s.height - s.getchannel("A").getbbox()[3]
        top = 1050 - (s.height - pad)
        sprites.append((nm, cx, s, top))
    shelters = []
    if wet:
        mk = next((x for x in sprites if x[0] == "Mika"), sprites[0])
        draw_umbrella(fr, [x[1] for x in sprites], min(x[3] for x in sprites), k, mk[1], shelters)
    for nm, cx, s, top in sprites:
        sh = Image.new("RGBA", fr.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).ellipse((cx - 170, 1030, cx + 170, 1075), fill=(0, 0, 0, 70))
        fr.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
        fr.paste(s, (int(cx - s.width // 2), int(top)), s)
    rgb = fr.convert("RGB")
    if wet or snow:
        kind = seg["weather"]
        for t in (0.35, 1.9, 3.4):                              # a few overlapping sheets of rain / snow = a dense downpour
            A.AT.draw_precip(rgb, t, kind, 1.0, shelters)
    fr = rgb.convert("RGBA")
    # soft vignette so the title and faces pop
    vg = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vg).ellipse((-380, -300, W + 380, H + 360), fill=255)
    vg = vg.filter(ImageFilter.GaussianBlur(200))
    dark = Image.new("RGBA", (W, H), (20, 14, 40, 90))
    fr = Image.composite(fr, Image.alpha_composite(fr, dark), vg)
    # brand
    d = ImageDraw.Draw(fr)
    bf = title_font(52)
    label = "TINY JAPANESE"
    bw = int(bf.getlength(label)) + 76
    d.rounded_rectangle((46, 960, 46 + bw, 1050), radius=45, fill=(255, 253, 249), outline=accent_for(seg), width=7)
    d.text((46 + bw / 2, 1005), label, font=bf, fill=accent_for(seg), anchor="mm")
    banner(fr, meta, accent_for(seg))
    img = fr.convert("RGB").resize((1280, 720), Image.LANCZOS)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    img.save(out_path, optimize=True)
    return seg


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python story/make_cover.py stories/<name>.txt output/<name>.thumbnail.png")
    s = make_cover(sys.argv[1], sys.argv[2])
    print(f"Wrote {sys.argv[2]} (scene {s['scene']}, weather {s.get('weather')}, time {s.get('tod')})")
