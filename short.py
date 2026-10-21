#!/usr/bin/env python3
"""Tiny Japanese - YouTube Shorts generator.

One script file (.txt)  ->  one 1080x1920 vertical MP4 (about 45-58 seconds):
  hook -> mini story (Mika & Alex, Japanese / romaji / English) -> 1-2 key words -> 1 quiz question -> follow outro.
Same script format as lesson.py ([story] [vocab] [quiz]; [grammar] is ignored). Uses lesson.py for voices and characters.
"""
import argparse, bisect, math, os, random, re, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFilter
import lesson as L
from lesson import CHARS, BRAND, INK, SOFT, ROMA, GREEN, FPS, font, card, sub_blocks, example_blocks, sprite, wrap

SW, SH = 1080, 1920
MAX_STORY, MAX_VOCAB, MAX_QUIZ = 8, 2, 1
LIMIT = 58.0


def parse_short(path):
    """Dialogue-style Short script: [hook] [story] [quiz] [ending] sections, each made of 'Mika: jp | romaji | English' lines.
    Returns None if the file is in the older format (use lesson.parse_script for that)."""
    raw = open(path, encoding="utf-8").read()
    if re.search(r"^\s*(vocab|quiz)\s*:", raw, re.M | re.I):
        return None
    meta = dict(title="Tiny Short", episode="", scene="auto")
    lines, sec, pending = [], None, None
    for n, line in enumerate(raw.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = re.match(r"^\[([^\]]+)\]$", s)
        if m:
            sec = m[1].strip().lower()
            continue
        if sec is None:
            m = re.match(r"^(title|episode|scene)\s*:\s*(.+)$", s, re.I)
            if not m:
                L.die(f"line {n}: put title/episode/scene first, then [hook]: {s}")
            meta[m[1].lower()] = m[2].strip()
            continue
        m = re.match(r"^@scene\s+(.+)$", s, re.I)
        if m:
            pending = L.resolve_scene(m[1]) or pending
            continue
        m = re.match(r"^([A-Za-z]+(?:\s+(?:and|&)\s+[A-Za-z]+)?)\s*[:：]\s*(.+)$", s)
        who = m[1].strip().capitalize() if m else ""
        tag = None
        if m and (re.search(r"\s(and|&)\s", m[1]) or who == "Both"):
            who, tag = "Mika", "Mika & Alex"
        if not m or who not in CHARS:
            L.die(f"line {n}: lines look like 'Mika: こんにちは | Konnichiwa | Hello' (speakers: {', '.join(CHARS)})")
        ex = L.example_dict([x.strip() for x in m[2].split("|")])
        ln = dict(speaker=who, jp=ex["jp"], en=ex["en"], romaji=ex["romaji"], scene=pending, sec=sec)
        if tag:
            ln["tag"] = tag
        lines.append(ln); pending = None
    if not lines:
        L.die("no dialogue lines found in this Short.")
    sc = L.resolve_scene(meta.get("scene", "")) or "classroom"
    for ln in lines:
        sc = ln["scene"] or sc
        ln["scene"] = sc
    return meta, lines


def build_short_dialogue(meta, lines, rate, dummy, tmp):
    tr = L.Track(tmp, rate, dummy)
    segs = []
    mark = lambda kind, start, **kw: segs.append(dict(kind=kind, start=start, **kw))
    qidx = [i for i, ln in enumerate(lines) if ln["sec"] == "quiz"]
    tr.gap(0.2)
    prev = lines[0]["scene"]
    for i, ln in enumerate(lines):
        if qidx and i == qidx[-1] and len(qidx) >= 2:
            mark("think", tr.t, line=lines[i - 1], t0=tr.t, scene=lines[i - 1]["scene"]); tr.gap(3)
        a, b = tr.say(ln["jp"], ln["speaker"]); ln.update(start=a, end=b)
        mark("story", a - 0.02, line=ln, scene=ln["scene"], prev_scene=prev)
        prev = ln["scene"]; tr.gap(0.45)
        if re.search(r"your turn|say it|repeat after", ln["en"], re.I) and i < len(lines) - 1:   # pause so viewers can answer out loud
            mark("think", tr.t, line=ln, t0=tr.t, scene=ln["scene"]); tr.gap(3)
    total = tr.t + 1.0
    if total > LIMIT:
        print(f"::warning::This short is {total:.0f}s long. Shorts under about 60s perform best; use fewer lines.", file=sys.stderr)
    audio = tr.audio(total); n = int(total * FPS)
    mouth = L.mouth_levels(audio, n)
    spk = [None] * n
    for who, a, b in tr.talk:
        for i in range(max(0, int(a * FPS) - 1), min(n, int(b * FPS) + 2)):
            spk[i] = who
    return dict(meta=meta, story=lines, vocab=[], quiz=[], segs=segs, audio=audio, n=n, total=total, mouth=mouth, spk=spk)


def build_short(path, rate, dummy, tmp):
    new = parse_short(path)
    if new:
        return build_short_dialogue(new[0], new[1], rate, dummy, tmp)
    meta, story, vocab, _grammar, quiz = L.parse_script(path)
    story, vocab, quiz = story[:MAX_STORY], vocab[:MAX_VOCAB], quiz[:MAX_QUIZ]
    tr = L.Track(tmp, rate, dummy)
    segs = []
    mark = lambda kind, start, **kw: segs.append(dict(kind=kind, start=start, **kw))

    tr.gap(0.2)
    mark("title", 0.0, scene=story[0]["scene"])
    tr.say(f"Learn Japanese in one minute! {meta['title']}.", "Narrator"); tr.gap(0.4)
    prev = story[0]["scene"]
    for ln in story:
        a, b = tr.say(ln["jp"], ln["speaker"]); ln.update(start=a, end=b)
        mark("story", a - 0.02, line=ln, scene=ln["scene"], prev_scene=prev)
        prev = ln["scene"]; tr.gap(0.35)
    tr.gap(0.2)
    for i, v in enumerate(vocab):
        mark("vocab", tr.t, v=v, i=i, n=len(vocab), shown=0)
        if i == 0:
            tr.say("Key words.", "Narrator"); tr.gap(0.2)
        tr.say(v["jp"], "Mika", "-25%"); tr.gap(0.25)
        tr.say(v["en"].replace("~", "something"), "Narrator"); tr.gap(0.3)
        if v["examples"]:
            mark("vocab", tr.t, v=v, i=i, n=len(vocab), shown=1)
            tr.say(v["examples"][0]["jp"], "Mika", "-15%"); tr.gap(0.6)
    for i, q in enumerate(quiz):
        mark("quiz", tr.t, q=q, phase="ask")
        tr.say("Quick quiz!", "Narrator"); tr.gap(0.1)
        tr.mixed(q["q"]); tr.gap(0.25)
        for k, o in enumerate(q["opts"]):
            tr.say("ABCD"[k], "Narrator"); tr.gap(0.05); tr.mixed(o); tr.gap(0.25)
        mark("quiz", tr.t, q=q, phase="think", t0=tr.t); tr.gap(3)
        mark("quiz", tr.t, q=q, phase="answer")
        tr.say(f"The answer is {'ABCD'[q['ans']]}.", "Narrator"); tr.gap(0.1)
        tr.mixed(q["opts"][q["ans"]]); tr.gap(0.5)
    mark("outro", tr.t, scene=story[-1]["scene"])
    tr.say("Follow Tiny Japanese for a new lesson every day!", "Narrator")
    total = tr.t + 1.0
    if total > LIMIT:
        print(f"::warning::This short is {total:.0f}s long. Shorts under about 60s perform best; use fewer story lines.", file=sys.stderr)
    audio = tr.audio(total); n = int(total * FPS)
    mouth = L.mouth_levels(audio, n)
    spk = [None] * n
    for who, a, b in tr.talk:
        for i in range(max(0, int(a * FPS) - 1), min(n, int(b * FPS) + 2)):
            spk[i] = who
    return dict(meta=meta, story=story, vocab=vocab, quiz=quiz, segs=segs, audio=audio, n=n, total=total, mouth=mouth, spk=spk)


class ShortRenderer:
    def __init__(self, B):
        self.B, self.meta = B, B["meta"]
        self.starts = [s["start"] for s in B["segs"]]
        self.bgs, self.cards = {}, {}
        self.pills = {(nm, a): L.pill(nm, CHARS[nm]["accent"] if a else (226, 214, 206),
                                      (255, 255, 255) if a else (130, 112, 108), 36)
                      for nm in CHARS for a in (0, 1)}

    def bg(self, name):
        if name not in self.bgs:
            im = L.vgrad(SW, SH, (255, 246, 238), (250, 220, 232)).convert("RGB")
            dd = ImageDraw.Draw(im); rng = random.Random(4)
            L.blossoms(dd, rng, (0, 0, SW, 520), 26); L.blossoms(dd, rng, (0, 1500, SW, SH), 16)
            dd.rectangle((0, 1560, SW, SH), fill=(240, 214, 200))
            im = im.convert("RGBA")
            d = ImageDraw.Draw(im, "RGBA")
            sz = 46; ttl = self.meta["title"]; ep = (f"Ep.{self.meta['episode']}  ·  " if str(self.meta["episode"]).strip().isdigit() else f"{self.meta['episode']}  ·  ") if self.meta.get("episode") else ""
            while sz > 28 and len(wrap(ep + ttl, font(sz), 860)) > 2:
                sz -= 2
            lines = wrap(ep + ttl, font(sz), 860)
            h = 96 + int(sz * 1.25) * len(lines)
            d.rounded_rectangle((50, 90, SW - 50, 90 + h), radius=48, fill=(255, 255, 255, 238))
            d.text((90, 112), "TINY JAPANESE", font=font(34), fill=BRAND)
            for k2, ln in enumerate(lines):
                d.text((90, 160 + k2 * int(sz * 1.25)), ln, font=font(sz), fill=(60, 45, 48))
            self.bgs[name] = im
        return self.bgs[name]

    def cached(self, key, fn):
        if key not in self.cards:
            self.cards[key] = fn()
        return self.cards[key]

    def seg_at(self, tt):
        return self.B["segs"][max(0, bisect.bisect_right(self.starts, tt) - 1)]

    def card_for(self, seg):
        k = seg["kind"]
        if k == "title":
            return card("Mini lesson", BRAND, [(self.meta["title"], 76, True, INK, 14),
                                               ("Story  ·  Words  ·  Quiz", 40, False, SOFT, 0)], cw=980, min_h=420)
        if k == "outro":
            return card("Thanks for watching", BRAND, [("Follow for a new lesson every day!", 62, True, INK, 14),
                                                       ("また あした！ (mata ashita)", 40, False, SOFT, 0)], cw=980, min_h=420)
        if k in ("story", "think"):
            ln = seg["line"]
            tag = ln.get("tag", ln["speaker"])
            if ln.get("sec") == "quiz":
                tag = "Quick quiz · " + tag
            return card(tag, CHARS[ln["speaker"]]["accent"], sub_blocks(ln["jp"], ln["romaji"], ln["en"], 70, 40, 46), cw=980, min_h=470)
        if k == "vocab":
            v = seg["v"]
            b = [(v["jp"], 110, True, INK, 8), (v["romaji"], 48, False, ROMA, 6), (v["en"], 58, False, SOFT, 14)]
            if seg["shown"] and v["examples"]:
                b += example_blocks(v["examples"][0])
            return card(f"Word {seg['i'] + 1}/{seg['n']}", BRAND, b, cw=980, min_h=520)
        q, ph = seg["q"], seg["phase"]
        b = [(q["q"], 50, True, INK, 20)]
        for j, o in enumerate(q["opts"]):
            ro = L.to_romaji(o) if L.HAS_JP.search(o) else ""
            label = f"{'ABCD'[j]}.  {o}" + (f"  ({ro})" if ro else "")
            col = INK
            if ph == "answer":
                col = GREEN if j == q["ans"] else (170, 156, 162)
            b.append((label, 44, ph != "answer" or j == q["ans"], col, 8))
        return card("Quick quiz", BRAND, b, cw=980, min_h=520)

    def frame(self, i):
        tt = i / FPS; seg = self.seg_at(tt); B = self.B
        j = min(i, B["n"] - 1); who, mouth = B["spk"][j], B["mouth"][j]
        scene = seg.get("scene") or B["segs"][0]["scene"]
        if seg["kind"] in ("vocab", "quiz"):
            scene = B["story"][-1]["scene"]
        fr = self.bg(scene).copy()
        if seg["kind"] == "story" and seg["prev_scene"] != scene and tt - seg["start"] < 0.5:
            fr = Image.blend(self.bg(seg["prev_scene"]), fr, min(1, (tt - seg["start"]) / 0.5))
        for nm, cx in (("Mika", 270), ("Alex", SW - 270)):
            speaking = who == nm
            bob = 6 * abs(math.sin(tt * 7)) if speaking and mouth else 2 * math.sin(tt * 2 + (0 if nm == "Mika" else 1.7))
            blink = ((i + (0 if nm == "Mika" else 41)) % 72) < 3
            s = sprite(nm, int(mouth) if speaking else 0, blink, 0.8, True)
            fr.paste(s, (cx - s.width // 2, int(470 - bob)), s)
            p = self.pills[(nm, int(speaking))]
            fr.paste(p, (cx - p.width // 2, 520), p)
        key = ("c", seg["kind"], id(seg))
        cd = self.cached(key, lambda: self.card_for(seg))
        f = min(1, (tt - seg["start"]) / 0.2)
        if f < 1:
            cd = cd.copy(); cd.putalpha(cd.getchannel("A").point(lambda v: int(v * f)))
        fr.paste(cd, ((SW - cd.width) // 2, 1170), cd)
        if seg["kind"] == "think" or (seg["kind"] == "quiz" and seg["phase"] == "think"):
            left = max(0.0, 3 - (tt - seg["t0"]))
            d = ImageDraw.Draw(fr); cx, cy, r = SW // 2, 930, 80
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255), outline=BRAND, width=9)
            d.arc((cx - r, cy - r, cx + r, cy + r), -90, -90 + 360 * (left / 3), fill=(255, 190, 110), width=9)
            d.text((cx, cy), str(max(1, math.ceil(left))), font=font(92), fill=INK, anchor="mm")
        return fr.convert("RGB")


def write_extras(B, outdir, stem):
    m = B["meta"]
    lines = [f"{m['title']} | Learn Japanese in 1 minute #Shorts", "",
             "A tiny Japanese story, 1-2 key words and a quick quiz. Follow for a new lesson every day!", ""]
    for ln in B["story"]:
        lines.append(f"{ln['jp']} - {ln['en']}")
    if B["vocab"]:
        lines += ["", "WORDS"] + [f"{v['jp']} ({v['romaji']}) - {v['en']}" for v in B["vocab"]]
    lines += ["", "#Shorts #learnjapanese #japanese #JLPT"]
    open(os.path.join(outdir, stem + ".description.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description="Tiny Japanese YouTube Shorts generator")
    ap.add_argument("script"); ap.add_argument("-o", "--out", default="output")
    ap.add_argument("--rate", default="-12%"); ap.add_argument("--dummy-audio", action="store_true")
    ap.add_argument("--preview", metavar="DIR", help="save a few PNG frames and exit")
    a = ap.parse_args()
    stem = os.path.splitext(os.path.basename(a.script))[0]
    with tempfile.TemporaryDirectory() as tmp:
        B = build_short(a.script, a.rate, a.dummy_audio, tmp)
        R = ShortRenderer(B)
        if a.preview:
            os.makedirs(a.preview, exist_ok=True); seen = set()
            for seg in B["segs"]:
                key = seg["kind"] + str(seg.get("phase", "")) + str(seg.get("shown", ""))
                if key in seen:
                    continue
                seen.add(key); R.frame(min(int((seg["start"] + 0.6) * FPS), B["n"] - 1)).save(os.path.join(a.preview, f"{len(seen):02d}-{key}.png"))
            print(f"Wrote {len(seen)} preview frames (length {L.fmt_time(B['total'])})"); return
        os.makedirs(a.out, exist_ok=True)
        wav = os.path.join(tmp, "final.wav"); L.write_wav(wav, B["audio"])
        out = os.path.join(a.out, stem + ".mp4")
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{SW}x{SH}",
                              "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "21",
                              "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-shortest", out],
                             stdin=subprocess.PIPE)
        for i in range(B["n"]):
            p.stdin.write(R.frame(i).tobytes())
        p.stdin.close(); p.wait()
        write_extras(B, a.out, stem)
        R.frame(int(min(B["n"] - 1, 4 * FPS))).resize((540, 960), Image.LANCZOS).save(os.path.join(a.out, stem + ".thumbnail.png"))
        print(f"Wrote {out} ({L.fmt_time(B['total'])})")


if __name__ == "__main__":
    main()
