#!/usr/bin/env python3
"""Tiny Japanese - Kana lesson generator (hiragana / katakana, one character per video).

One kana script (.txt) -> one 1080x1920 vertical MP4 (about 60-90 seconds):
  hear it -> see it in 3 fonts -> write it (countdown) -> picture mnemonic -> 2-3 real words (kana highlighted)
  -> look-alike warning -> 2 quiz questions (5s timer) -> outro.
Reuses lesson.py (voices, Mika, cards, audio track). Same look as short.py.

Script format (kana/hira-a.txt):
    title: Hiragana A
    kana: あ
    script: hiragana            # or katakana
    romaji: a
    sound: like the "a" in father
    strokes: 3
    mnemonic_word: Apple        # optional picture: assets/mnemonics/<script>-<romaji>.png
    mnemonic: あ looks like an apple with a little stem. A for Apple!
    [words]
    あめ | ame | rain
    [similar]
    お | o | how to tell them apart
    [distractors]
    i, u
"""
import argparse, bisect, glob, math, os, random, re, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont
import lesson as L
from lesson import BRAND, INK, SOFT, ROMA, GREEN, FPS, font, card, sprite

SW, SH = 1080, 1920
PANEL = (80, 300, SW - 80, 1060)
THINK = 5


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
    if meta["script"].lower() not in ("hiragana", "katakana"): L.die("script must be hiragana or katakana")
    meta["script"] = meta["script"].lower()
    if not meta["title"]: meta["title"] = f"{meta['script'].title()} {meta['romaji'].upper()}"
    if not words: L.die("add at least one word under [words]")
    if len(distractors) < 2: distractors = [r for r in ("a", "i", "u", "e", "o", "ka", "ki", "ku", "ke", "ko") if r != meta["romaji"]][:3]
    return meta, words[:3], similar[:2], distractors[:3]


def make_quiz(meta, words, distractors):
    rng = random.Random(meta["kana"])
    qs = []
    opts = [meta["romaji"]] + distractors[:2]; rng.shuffle(opts)
    qs.append(dict(q=f"Which sound is {meta['kana']}?", opts=opts, ans=opts.index(meta["romaji"]), glyph=meta["kana"], jp=None))
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


def build(path, rate, dummy, tmp):
    meta, words, similar, distractors = parse_kana(path)
    quiz = make_quiz(meta, words, distractors)
    K, R = meta["kana"], meta["romaji"]
    tr = L.Track(tmp, rate, dummy); segs = []
    mark = lambda kind, start, **kw: segs.append(dict(kind=kind, start=start, **kw))
    SLOW = "-35%"
    tr.gap(0.3)
    mark("title", 0.0)
    tr.say(f"Learn {meta['script']} in one minute. Today: {R.upper()}.", "Narrator"); tr.gap(0.4)
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
    st = f" in {meta['strokes']} strokes" if meta["strokes"] else ""
    mark("write", tr.t, t0=tr.t)
    tr.say(f"Now write it{st}. Trace the character in the air or on paper.", "Narrator"); tr.gap(0.2)
    mark("write", tr.t, t0=tr.t, timer=True); tr.gap(THINK)
    if meta["mnemonic"]:
        mark("mnemonic", tr.t)
        tr.say("A trick to remember it.", "Narrator"); tr.gap(0.2)
        tr.say(meta["mnemonic"], "Narrator"); tr.gap(0.6)
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
    return dict(meta=meta, words=words, similar=similar, quiz=quiz, segs=segs, audio=audio, n=n, total=total, mouth=mouth, spk=spk)


class Renderer:
    def __init__(self, B, assets="assets"):
        self.B, self.meta, self.assets = B, B["meta"], assets
        self.starts = [s["start"] for s in B["segs"]]
        self.cache = {}
        self.bg = self._bg()

    def _bg(self):
        im = L.vgrad(SW, SH, (255, 246, 238), (250, 220, 232)).convert("RGB")
        dd = ImageDraw.Draw(im); rng = random.Random(4)
        L.blossoms(dd, rng, (0, 0, SW, 280), 20); L.blossoms(dd, rng, (0, 1560, SW, SH), 16)
        dd.rectangle((0, 1620, SW, SH), fill=(240, 214, 200))
        im = im.convert("RGBA"); d = ImageDraw.Draw(im, "RGBA")
        d.rounded_rectangle((50, 80, SW - 50, 250), radius=48, fill=(255, 255, 255, 238))
        d.text((90, 104), "TINY JAPANESE", font=font(34), fill=BRAND)
        d.text((90, 160), self.meta["title"], font=font(56), fill=(60, 45, 48))
        d.rounded_rectangle(PANEL, radius=64, fill=(255, 255, 255, 245), outline=(240, 214, 220), width=6)
        return im

    def memo(self, key, fn):
        if key not in self.cache: self.cache[key] = fn()
        return self.cache[key]

    def put(self, d, text, f, cx, cy, fill):
        d.text((cx, cy), text, font=f, fill=fill, anchor="mm")

    def panel(self, seg):
        im = Image.new("RGBA", (SW, SH), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        cx, cy = (PANEL[0] + PANEL[2]) // 2, (PANEL[1] + PANEL[3]) // 2
        K, Rm, k = self.meta["kana"], self.meta["romaji"], seg["kind"]
        if k in ("title", "sound", "think"):
            self.put(d, K, MK("sans", 560), cx, cy - 40, INK)
            if k != "title": self.put(d, Rm, font(130), cx, PANEL[3] - 100, BRAND)
        elif k == "fonts":
            for dx, kind, lab in ((-270, "sans", "gothic"), (0, "serif", "mincho"), (270, "light", "light")):
                self.put(d, K, MK(kind, 290), cx + dx, cy - 80, INK); self.put(d, lab, font(34, False), cx + dx, cy + 120, SOFT)
            self.put(d, Rm, font(130), cx, PANEL[3] - 100, BRAND)
        elif k == "write":
            self.put(d, K, MK("light", 560), cx, cy - 40, (225, 214, 218))
            self.put(d, "trace it!", font(64), cx, PANEL[3] - 90, BRAND)
        elif k == "mnemonic":
            pics = glob.glob(os.path.join(self.assets, "mnemonics", f"{self.meta['script']}-{Rm}.*"))
            if pics:
                p = Image.open(pics[0]).convert("RGBA"); p.thumbnail((620, 520)); im.paste(p, (cx - p.width // 2, cy - 330), p)
            else:
                self.put(d, self.meta["mnemonic_word"] or Rm.upper(), font(150), cx, cy - 230, BRAND)
            self.put(d, K, MK("sans", 340), cx, cy + 150, INK)
        elif k == "word":
            w = seg["w"]["jp"]; f = MK("sans", 230 if len(w) <= 3 else 170)
            x = cx - sum(f.getlength(c) for c in w) / 2
            for c in w:
                d.text((x, cy - 140), c, font=f, fill=BRAND if c == K else INK, anchor="lm"); x += f.getlength(c)
            if seg["shown"]:
                self.put(d, seg["w"]["romaji"], font(84), cx, cy + 90, ROMA); self.put(d, seg["w"]["en"], font(96), cx, cy + 230, SOFT)
        elif k == "similar":
            s = seg["s"]
            self.put(d, K, MK("sans", 400), cx - 230, cy - 60, BRAND); self.put(d, s["kana"], MK("sans", 400), cx + 230, cy - 60, INK)
            self.put(d, Rm, font(100), cx - 230, cy + 200, BRAND); self.put(d, s["romaji"], font(100), cx + 230, cy + 200, SOFT)
        elif k == "quiz":
            g = seg["q"]["glyph"]; self.put(d, g, MK("sans", 420 if len(g) == 1 else 220), cx, cy - 40, INK)
        elif k == "outro":
            self.put(d, K, MK("sans", 420), cx, cy - 80, BRAND); self.put(d, "また あした！", font(90), cx, cy + 260, INK)
        return im

    def card_for(self, seg):
        k, M = seg["kind"], self.meta
        if k == "title":
            return card(M["script"].title(), BRAND, [(M["title"], 70, True, INK, 10), (f"{M['kana']}  =  {M['romaji']}", 52, False, ROMA, 0)], cw=980, min_h=330)
        if k == "sound":
            b = [(f"“{M['romaji']}”", 110, True, INK, 8)]
            if M["sound"]: b.append((f"sounds {M['sound']}", 44, False, SOFT, 0))
            return card("Listen", BRAND, b, cw=980, min_h=330)
        if k == "think":
            return card("Your turn", BRAND, [("Say it out loud!", 70, True, INK, 8), (M["romaji"], 52, False, ROMA, 0)], cw=980, min_h=330)
        if k == "fonts":
            return card("Same character", BRAND, [("Many fonts, one sound", 58, True, INK, 8)], cw=980, min_h=260)
        if k == "write":
            st = f"{M['strokes']} strokes" if M["strokes"] else "Write it"
            return card("Write it", BRAND, [(st, 76, True, INK, 8), ("Trace it in the air or on paper", 40, False, SOFT, 0)], cw=980, min_h=330)
        if k == "mnemonic":
            return card("Memory trick", BRAND, [(M["mnemonic"], 48, True, INK, 0)], cw=980, min_h=330)
        if k == "word":
            w = seg["w"]
            return card(f"Word {seg['i'] + 1}/{seg['n']}", BRAND, [(w["jp"], 100, True, INK, 8), (w["romaji"], 48, False, ROMA, 6), (w["en"] if seg["shown"] else "...", 56, False, SOFT, 0)], cw=980, min_h=420)
        if k == "similar":
            return card("Look-alike", (214, 110, 90), [(seg["s"]["tip"], 46, True, INK, 0)], cw=980, min_h=330)
        if k == "outro":
            return card("Thanks for watching", BRAND, [("Follow for the next character!", 60, True, INK, 8), ("また あした！ (mata ashita)", 40, False, SOFT, 0)], cw=980, min_h=330)
        q, ph = seg["q"], seg["phase"]; b = [(q["q"], 56, True, INK, 16)]
        for j, o in enumerate(q["opts"]):
            col = INK
            if ph == "answer": col = GREEN if j == q["ans"] else (170, 156, 162)
            b.append((f"{'ABC'[j]}.   {o}", 52, ph != "answer" or j == q["ans"], col, 8))
        return card("Quick quiz", BRAND, b, cw=980, min_h=520)

    def seg_at(self, tt):
        return self.B["segs"][max(0, bisect.bisect_right(self.starts, tt) - 1)]

    def frame(self, i):
        tt = i / FPS; seg = self.seg_at(tt); B = self.B
        j = min(i, B["n"] - 1); speaking, mouth = B["spk"][j] == "Mika", B["mouth"][j]
        fr = self.bg.copy()
        ident = (seg["kind"], seg.get("i"), seg.get("shown"), seg.get("phase"), id(seg.get("s")), id(seg.get("q")))
        fr.alpha_composite(self.memo(("p",) + ident, lambda: self.panel(seg)))
        bob = 6 * abs(math.sin(tt * 7)) if speaking and mouth else 2 * math.sin(tt * 2)
        s = sprite("Mika", int(mouth) if speaking else 0, (i % 72) < 3, 0.62, False)
        fr.paste(s, (SW - s.width - 10, int(1190 - s.height - bob)), s)
        cd = self.memo(("c",) + ident, lambda: self.card_for(seg))
        f = min(1, (tt - seg["start"]) / 0.2)
        if f < 1:
            cd = cd.copy(); cd.putalpha(cd.getchannel("A").point(lambda v: int(v * f)))
        fr.paste(cd, ((SW - cd.width) // 2, 1210), cd)
        if seg["kind"] == "think" or seg.get("timer") or (seg["kind"] == "quiz" and seg["phase"] == "think"):
            total = seg.get("n", 3) if seg["kind"] == "think" else THINK
            left = max(0.0, total - (tt - seg["t0"]))
            d = ImageDraw.Draw(fr); cx, cy, r = SW - 190, 400, 70
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255), outline=BRAND, width=9)
            d.arc((cx - r, cy - r, cx + r, cy + r), -90, -90 + 360 * (left / total), fill=(255, 190, 110), width=9)
            d.text((cx, cy), str(max(1, math.ceil(left))), font=font(80), fill=INK, anchor="mm")
        return fr.convert("RGB")


def write_extras(B, outdir, stem):
    m = B["meta"]
    lines = [f"{m['title']} ({m['kana']}) | Learn {m['script'].title()} in 1 minute #Shorts", "",
             f"How to read and write {m['kana']} ({m['romaji']}): sound, 3 fonts, writing practice, memory trick, real words and a quiz.", ""]
    lines += [f"{w['jp']} ({w['romaji']}) - {w['en']}" for w in B["words"]]
    lines += ["", f"#Shorts #{m['script']} #learnjapanese #japanese #kana"]
    open(os.path.join(outdir, stem + ".description.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description="Tiny Japanese kana lesson generator")
    ap.add_argument("script"); ap.add_argument("-o", "--out", default="output")
    ap.add_argument("--rate", default="-12%"); ap.add_argument("--dummy-audio", action="store_true")
    ap.add_argument("--assets", default="assets"); ap.add_argument("--preview", metavar="DIR")
    a = ap.parse_args()
    stem = os.path.splitext(os.path.basename(a.script))[0]
    with tempfile.TemporaryDirectory() as tmp:
        B = build(a.script, a.rate, a.dummy_audio, tmp)
        R = Renderer(B, a.assets)
        if a.preview:
            os.makedirs(a.preview, exist_ok=True); seen = set()
            for seg in B["segs"]:
                key = seg["kind"] + str(seg.get("phase", "")) + str(seg.get("shown", "")) + str(seg.get("timer", ""))
                if key in seen: continue
                seen.add(key); R.frame(min(int((seg["start"] + 0.8) * FPS), B["n"] - 1)).save(os.path.join(a.preview, f"{len(seen):02d}-{key}.png"))
            print(f"Wrote {len(seen)} preview frames (length {L.fmt_time(B['total'])})"); return
        os.makedirs(a.out, exist_ok=True)
        wav = os.path.join(tmp, "final.wav"); L.write_wav(wav, B["audio"])
        out = os.path.join(a.out, stem + ".mp4")
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{SW}x{SH}",
                              "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "21",
                              "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-shortest", out], stdin=subprocess.PIPE)
        for i in range(B["n"]):
            p.stdin.write(R.frame(i).tobytes())
        p.stdin.close(); p.wait()
        write_extras(B, a.out, stem)
        R.frame(int(min(B["n"] - 1, 1.5 * FPS))).resize((540, 960), Image.LANCZOS).save(os.path.join(a.out, stem + ".thumbnail.png"))
        print(f"Wrote {out} ({L.fmt_time(B['total'])})")


if __name__ == "__main__":
    main()
