#!/usr/bin/env python3
"""Tiny Japanese - YouTube Shorts generator (Reels look).

One script file (.txt)  ->  one 1080x1920 vertical MP4 (about 30-58 seconds).
Renders with the same engine as the Instagram Reels project (tinyvideo.py): 33 hand-drawn places,
animated weather, 31 anime characters with their own voices, big Japanese / romaji / English cards.

Script format (dialogue style, sections are optional):

    title: 3 Japanese Phrases That Make You Sound Natural
    scene: park                 # auto, a place name, or change mid-short with "@scene cafe" on its own line
    weather: auto               # optional: petals leaves snow rain wind none
    cast: mika, alex            # optional: any two characters from the roster

    [hook]
    Mika: にほんごを もっと はなしたい？ | Nihongo o motto hanashitai? | Want to speak more Japanese?
    [story]
    Alex: いいね！ | That's nice!               # romaji is added automatically when there are only 2 parts
    [quiz]
    ...
    [ending]
    Mika and Alex: またね！ | Mata ne! | See you!

Scripts written as [story] + [vocab] (vocab:/example:) + [quiz] (quiz: ...) also render in this look.
"""
import argparse, bisect, math, os, re, subprocess, sys, tempfile
import numpy as np
from PIL import Image, ImageDraw
import tinyvideo as T

W, H, FPS, SR = T.W, T.H, T.FPS, T.SR
LEAD, GAP, THINK = 0.3, 0.4, 3.0
LIMIT = 58.0
HAS_JP = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
INK, SOFT, ROMA = (52, 40, 44), (90, 78, 80), (176, 110, 128)
THINK_RE = re.compile(r"your turn|say it|repeat after", re.I)

JP_RUN = re.compile(r"([\u3040-\u30ff\u3400-\u9fff][\u3040-\u30ff\u3400-\u9fff、。！？ー・\s]*)")
GREEN, MAX_STORY, MAX_VOCAB, MAX_QUIZ = (58, 158, 96), 8, 2, 1


def default_segs(text, who):
    """Japanese parts are spoken by the character, English parts by the narrator."""
    segs = []
    for k, run in enumerate(JP_RUN.split(text)):
        if not run.strip() or not re.search(r"[A-Za-z0-9\u3040-\u30ff\u3400-\u9fff]", run):
            continue
        segs.append((run.strip(), who, None) if k % 2 else (run.strip(), "Narrator", None))
    return segs


def parse_classic(path):
    """Scripts written as [story] + [vocab] (vocab:/example:) + [quiz] (quiz: ...) lines -> the same line model."""
    import lesson as L
    meta, story, vocab, _grammar, quiz = L.parse_script(path)
    story, vocab, quiz = story[:MAX_STORY], vocab[:MAX_VOCAB], quiz[:MAX_QUIZ]
    lines, sc = [], None
    for ln in story:
        sc = resolve_scene(ln.get("scene") or "") or sc
        both = ln.get("tag") is not None
        lines.append(dict(speaker="Both" if both else ln["speaker"], tag=ln.get("tag"), jp=ln["jp"], en=ln["en"],
                          romaji=ln["romaji"], scene=sc, sec="story", segs=default_segs(ln["jp"], "Mika" if both else ln["speaker"])))
    base = resolve_scene(meta.get("scene", "")) or T.pick_scene(meta, lines)
    for ln in lines:
        ln["scene"] = ln["scene"] or base
    last = lines[-1]["scene"]
    for i, v in enumerate(vocab):
        segs = ([("Key words.", "Narrator", None)] if i == 0 else []) + [(v["jp"], "Mika", "-25%"), (v["en"].replace("~", "something"), "Narrator", None)]
        lines.append(dict(speaker="Mika", jp=v["jp"], en=v["en"], romaji=v["romaji"], scene=last, sec="vocab", kind="vocab",
                          tag=f"Word {i + 1}/{len(vocab)}", segs=segs))
        if v["examples"]:
            e = v["examples"][0]
            lines.append(dict(speaker="Alex", jp=e["jp"], en=e["en"], romaji=e["romaji"], scene=last, sec="vocab", tag="Example",
                              segs=[(e["jp"], "Alex", "-15%")]))
    for q in quiz:
        ask = [("Quick quiz!", "Narrator", None)] + default_segs(q["q"], "Mika")
        for k, o in enumerate(q["opts"]):
            ask += [("ABCD"[k], "Narrator", None)] + default_segs(o, "Mika")
        lines.append(dict(speaker="Mika", jp=q["q"], en="", romaji="", scene=last, sec="quiz", kind="quizq", q=q, segs=ask))
        ans = [(f"The answer is {'ABCD'[q['ans']]}.", "Narrator", None)] + default_segs(q["opts"][q["ans"]], "Alex")
        lines.append(dict(speaker="Alex", jp=q["opts"][q["ans"]], en="", romaji="", scene=last, sec="quiz", kind="quizans", q=q, segs=ans))
    lines.append(dict(speaker="Both", tag="Tiny Japanese", jp="Follow for a new lesson every day!", en="", romaji="", scene=last,
                      sec="outro", kind="outro", segs=[("Follow Tiny Japanese for a new lesson every day!", "Narrator", None)]))
    meta["scene"] = base
    return meta, lines



def die(msg):
    sys.exit(f"::error::{msg}")


def is_classic(path):
    raw = open(path, encoding="utf-8").read()
    return bool(re.search(r"^\s*(vocab|quiz)\s*:", raw, re.M | re.I))


# ---------- script parsing ----------
def resolve_scene(name):
    """A place name / alias -> a scene key, or None."""
    sc = T.SCENE_ALIASES.get((name or "").strip().lower(), (name or "").strip().lower())
    if sc in T.SCENES:
        return sc
    for key, val in list(T.SCENE_ALIASES.items()) + [(k, k) for k in T.SCENES]:
        if sc and key in sc:
            return val
    return None


def parse_short(path):
    meta = dict(title="Tiny Short", scene="auto", episode="")
    raw_lines, sec, pending = [], None, None
    pat = re.compile(r"^([A-Za-z]+(?:\s+(?:and|&)\s+[A-Za-z]+)?)\s*[:：]\s*(.+)$")
    for n, raw in enumerate(open(path, encoding="utf-8"), 1):
        s = raw.replace("\ufeff", "").strip()
        if not s or s.startswith("#"):
            continue
        m = re.match(r"^\[([^\]]+)\]$", s)
        if m:
            sec = m[1].strip().lower(); continue
        m = re.match(r"^(title|episode|scene|weather|cast)\s*:\s*(.+)$", s, re.I)
        if m and sec is None:
            meta[m[1].lower()] = m[2].strip(); continue
        m = re.match(r"^@scene\s+(.+)$", s, re.I)
        if m:
            pending = resolve_scene(m[1]) or pending; continue
        m = pat.match(s)
        if not m:
            die(f"line {n}: lines look like 'Mika: こんにちは | Konnichiwa | Hello' - got: {s}")
        who = m[1].strip()
        both = bool(re.search(r"\s(and|&)\s", who)) or who.lower() == "both"
        parts = [x.strip() for x in m[2].split("|")]
        if len(parts) >= 3:
            jp, ro, en = parts[0], parts[1], parts[2]        # Shorts format: Japanese | romaji | English
        elif len(parts) == 2:
            jp, en = parts; ro = T.to_romaji(jp) if HAS_JP.search(jp) else ""
        else:
            jp, en, ro = parts[0], "", (T.to_romaji(parts[0]) if HAS_JP.search(parts[0]) else "")
        raw_lines.append(dict(who=who, both=both, jp=jp, en=en, romaji=ro, scene=pending, sec=sec or "story"))
        pending = None
    if not raw_lines:
        die("no dialogue lines found in this Short.")
    # speakers -> left (Mika slot) / right (Alex slot), same rules as the Reels engine
    order = []
    for l in raw_lines:
        if not l["both"] and l["who"].lower() not in order:
            order.append(l["who"].lower())
    for who in order:
        if who not in T.ROSTER:
            die(f"unknown speaker '{who}'. Use Mika, Alex or a character from the roster: {', '.join(T.ROSTER)}")
    if len(order) > 2:
        die("a Short can only have two speakers (left and right).")
    if not meta.get("cast") and any(s not in ("mika", "alex") for s in order):
        meta["cast"] = ", ".join(order)
    left, right = T.cast_ids(meta)
    slots = {"mika": "Mika", "alex": "Alex"} if all(s in ("mika", "alex") for s in order) else {"mika": "Mika", "alex": "Alex", left: "Mika", right: "Alex"}
    used = {slots[s] for s in order if s in slots}
    for s in order:
        if s not in slots:
            free = [x for x in ("Mika", "Alex") if x not in used]
            slots[s] = free[0]; used.add(free[0])
    T.apply_cast(meta)
    lines = []
    for l in raw_lines:
        if l["both"]:
            l["speaker"], l["tag"] = "Both", f"{T.CHARS['Mika']['label']} & {T.CHARS['Alex']['label']}"
        else:
            l["speaker"] = slots[l["who"].lower()]
        lines.append(l)
    base = resolve_scene(meta.get("scene", "")) or T.pick_scene(meta, lines)
    sc = base
    for l in lines:
        sc = l["scene"] or sc
        l["scene"] = sc
    meta["scene"] = base
    return meta, lines


# ---------- audio / timing ----------
def speak(ln, tmp, i, rate, dummy):
    xs = []
    for k, (text, who, r) in enumerate(ln["segs"]):
        wav = os.path.join(tmp, f"l{i}_{k}.wav")
        if who == "Narrator":
            T.synth(text, "Narrator", wav, "+0%", dummy, voice="en-US-AriaNeural", lang="en")
        else:
            T.synth(text, who, wav, r or rate, dummy)
        xs += [T.read_wav(wav), np.zeros(int(0.12 * SR), np.float32)]
    return np.concatenate(xs)


def build(path, rate, dummy, tmp):
    meta, lines = parse_classic(path) if is_classic(path) else parse_short(path)
    for ln in lines:
        if "segs" not in ln:
            ln["segs"] = default_segs(ln["jp"], "Mika" if ln["speaker"] == "Both" else ln["speaker"])
    qidx = [i for i, l in enumerate(lines) if l["sec"] == "quiz"]
    chunks, t = [np.zeros(int(LEAD * SR), np.float32)], LEAD
    talk, thinks = [], []
    for i, ln in enumerate(lines):
        if qidx and i == qidx[-1] and len(qidx) >= 2:            # give viewers a few seconds before the answer
            thinks.append((t, t + THINK, i - 1))
            chunks.append(np.zeros(int(THINK * SR), np.float32)); t += THINK
        x = speak(ln, tmp, i, rate, dummy)
        ln["start"], ln["end"] = t, t + len(x) / SR
        talk.append(dict(speaker=ln["speaker"], start=ln["start"], end=ln["end"]))
        chunks += [x, np.zeros(int(GAP * SR), np.float32)]; t = ln["end"] + GAP
        if THINK_RE.search(ln["en"]) and i < len(lines) - 1:     # "your turn!" -> pause so viewers can answer out loud
            thinks.append((t, t + THINK, i))
            chunks.append(np.zeros(int(THINK * SR), np.float32)); t += THINK
    total = t + 0.8
    if total > LIMIT:
        print(f"::warning::This short is {total:.0f}s long. Shorts under about 60s perform best; use fewer lines.", file=sys.stderr)
    chunks.append(np.zeros(int((total - t) * SR) + SR, np.float32))
    audio = np.concatenate(chunks); audio = audio / max(0.01, np.abs(audio).max()) * 0.9
    n = int(total * FPS)
    return dict(meta=meta, lines=lines, audio=audio, n=n, total=total, talk=talk, thinks=thinks, mouth=T.mouth_levels(audio, n))


# ---------- cards ----------
def card_for(ln):
    kind = ln.get("kind")
    if kind == "vocab":
        return T.card_image(ln["tag"], T.BRAND, [(ln["jp"], T.font(96), INK, 112), (ln["romaji"], T.font(46, False), ROMA, 62), ("", None, None, 8)]
                            + [(x, T.font(54, False), SOFT, 68) for x in T.wrap(ln["en"], T.font(54, False), 840)])
    if kind in ("quizq", "quizans"):
        q, ans = ln["q"], kind == "quizans"
        qf, of = T.font(50), T.font(44)
        parts = [(x, qf, INK, 64) for x in T.wrap(q["q"], qf, 840)] + [("", None, None, 12)]
        for j, o in enumerate(q["opts"]):
            ro = T.to_romaji(o) if HAS_JP.search(o) else ""
            lab = f"{'ABCD'[j]}.  {o}" + (f"  ({ro})" if ro else "")
            col = INK if not ans else (GREEN if j == q["ans"] else (170, 156, 162))
            parts += [(x, of, col, 60) for x in T.wrap(lab, of, 840)]
        return T.card_image("Quick quiz", T.BRAND, parts)
    if kind == "outro":
        return T.card_image(ln["tag"], T.BRAND, [("New lesson", T.font(76), INK, 96), ("every day!", T.font(76), INK, 100),
                                                 ("", None, None, 10), ("Follow Tiny Japanese", T.font(44, False), SOFT, 60)])
    tag = ln.get("tag") or (T.CHARS[ln["speaker"]]["label"] if ln["speaker"] != "Both" else "Mika & Alex")
    color = T.CHARS["Mika" if ln["speaker"] == "Both" else ln["speaker"]]["accent"]
    if ln["sec"] == "quiz":
        tag = "Quick quiz · " + tag
    maxw, jp = 840, ln["jp"]
    if not HAS_JP.search(jp):                                    # English-only line, e.g. "A、Really? B、Goodbye. C、Thank you."
        opts = [o.strip() for o in re.split(r"\s*(?=\b[A-D][、,.．:：])", jp) if o.strip()]
        f = T.font(48)
        if len(opts) >= 2:
            parts = [(t, f, INK, 68) for o in opts for t in T.wrap(re.sub(r"^([A-D])[、,.．:：]\s*", r"\1.  ", o), f, maxw)]
        else:
            parts = [(t, f, INK, 64) for t in T.wrap(jp, f, maxw)]
        return T.card_image(tag, color, parts)
    jf = next((T.font(s) for s in (62, 56, 50) if T.font(s).getlength(jp) <= maxw), T.font(56))
    ro, en = T.font(36, False), T.font(40, False)
    parts = [(t, jf, INK, 82) for t in T.balanced(jp, jf, maxw)]
    if ln["romaji"] and ln["romaji"].strip().lower() != jp.strip().lower():
        parts += [("", None, None, 14)] + [(t, ro, ROMA, 49) for t in T.wrap(ln["romaji"], ro, maxw)]
    if ln["en"] and ln["en"].strip().lower() not in (jp.strip().lower(), ln["romaji"].strip().lower()):
        parts += [("", None, None, 18)] + [(t, en, SOFT, 54) for t in T.wrap(ln["en"], en, maxw)]
    return T.card_image(tag, color, parts)


# ---------- frames ----------
class Renderer:
    def __init__(self, B):
        self.B, self.meta, self.lines = B, B["meta"], B["lines"]
        self.starts = [l["start"] - 0.02 for l in self.lines]
        self.cards = [card_for(l) for l in self.lines]
        self.S = {}
        for sc in dict.fromkeys(l["scene"] for l in self.lines):
            m = dict(self.meta, scene=sc)
            bg, fg = T.make_scene(sc, m)
            wx = T.pick_weather(self.meta, self.lines, sc)
            self.S[sc] = dict(bg=bg, fg=fg, wx=wx, wxp=T.make_weather(wx, sc) if wx else None)
            print("Scene:", sc, "| Weather:", wx or "none")
        self.pills = {(nm, a): T.pill(T.CHARS[nm]["label"], T.CHARS[nm]["accent"] if a else (226, 214, 206),
                                      (255, 255, 255) if a else (130, 112, 108)) for nm in T.CHARS for a in (0, 1)}

    def back(self, sc, tt):
        s = self.S[sc]; fr = s["bg"].copy()
        if s["wx"]:
            fr.alpha_composite(T.wx_layer(s["wx"], s["wxp"], tt, False), (0, T.WX_Y0))
        return fr

    def line_at(self, tt):
        return max(0, bisect.bisect_right(self.starts, tt) - 1)

    def frame(self, i):
        B, tt = self.B, i / FPS
        j = min(i, B["n"] - 1)
        k = self.line_at(tt); ln = self.lines[k]; sc = ln["scene"]
        fr = self.back(sc, tt)
        if k > 0 and self.lines[k - 1]["scene"] != sc and tt - ln["start"] < 0.5:      # crossfade between places
            fr = Image.blend(self.back(self.lines[k - 1]["scene"], tt), fr, max(0.0, min(1.0, (tt - ln["start"] + 0.02) / 0.5)))
        cur = next((q for q, tk in enumerate(B["talk"]) if tk["start"] - 0.02 <= tt <= tk["end"] + 0.1), None)
        for nm, c in T.CHARS.items():
            sp = cur is not None and B["talk"][cur]["speaker"] in (nm, "Both")
            mo = int(B["mouth"][j]) if sp else 0
            bob = 6 * abs(math.sin(tt * 7)) if sp and mo else 2 * math.sin(tt * 2 + (0 if nm == "Mika" else 1.7))
            blink = ((i + (0 if nm == "Mika" else 41)) % 97) < 4
            s = T.sprite(nm, mo, blink)
            fr.paste(s, (c["x"], int(T.CHAR_Y - bob)), s)
            p = self.pills[(nm, int(sp))]; fr.paste(p, (c["x"] + s.width // 2 - p.width // 2, 330), p)
        S = self.S[sc]
        fr.paste(S["fg"], (0, T.TABLE_TOP - 55), S["fg"])
        if S["wx"]:
            fr.alpha_composite(T.wx_layer(S["wx"], S["wxp"], tt, True), (0, T.WX_Y0))
        cd = self.cards[k]; f = min(1, (tt - ln["start"]) / 0.2); dy = int(24 * (1 - f))
        if f < 1:
            cd = cd.copy(); cd.putalpha(cd.getchannel("A").point(lambda v: int(v * f)))
        fr.paste(cd, (20, T.CARD_Y - 40 + dy), cd)
        for a, b, kk in B["thinks"]:                              # 3-2-1 timer while viewers think
            if a <= tt < b:
                left = max(0.0, b - tt); d = ImageDraw.Draw(fr); cx, cy, r = W // 2, 905, 74
                d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255), outline=T.BRAND, width=9)
                d.arc((cx - r, cy - r, cx + r, cy + r), -90, -90 + 360 * (left / THINK), fill=(255, 190, 110), width=9)
                d.text((cx, cy), str(max(1, math.ceil(left))), font=T.font(86), fill=INK, anchor="mm")
        return fr.convert("RGB")


def write_extras(B, outdir, stem):
    m = B["meta"]
    out = [f"{m['title']} | Learn Japanese in 1 minute #Shorts", "",
           "A tiny Japanese story and a quick quiz with Mika and Alex. Follow for a new lesson every day!", ""]
    for ln in B["lines"]:
        if ln["sec"] in ("hook", "story", "practice", "ending") and HAS_JP.search(ln["jp"]):
            out.append(f"{ln['jp']} - {ln['en']}")
    words = [l for l in B["lines"] if l.get("kind") == "vocab"]
    if words:
        out += ["", "WORDS"] + [f"{l['jp']} ({l['romaji']}) - {l['en']}" for l in words]
    out += ["", "#Shorts #learnjapanese #japanese #JLPT"]
    open(os.path.join(outdir, stem + ".description.txt"), "w", encoding="utf-8").write("\n".join(out) + "\n")


def main():
    ap = argparse.ArgumentParser(description="Tiny Japanese YouTube Shorts generator (Reels look)")
    ap.add_argument("script"); ap.add_argument("-o", "--out", default="output")
    ap.add_argument("--rate", default="-12%"); ap.add_argument("--dummy-audio", action="store_true")
    ap.add_argument("--preview", metavar="DIR", help="save a few PNG frames and exit")
    a = ap.parse_args()
    stem = os.path.splitext(os.path.basename(a.script))[0]
    with tempfile.TemporaryDirectory() as tmp:
        B = build(a.script, a.rate, a.dummy_audio, tmp)
        R = Renderer(B)
        if a.preview:
            os.makedirs(a.preview, exist_ok=True); seen = set()
            for k, ln in enumerate(B["lines"]):
                if ln["sec"] in seen:
                    continue
                seen.add(ln["sec"]); R.frame(min(int((ln["start"] + 0.6) * FPS), B["n"] - 1)).save(os.path.join(a.preview, f"{len(seen):02d}-{ln['sec']}.png"))
            for q, (x0, x1, kk) in enumerate(B["thinks"][:1]):
                R.frame(min(int((x0 + 1.0) * FPS), B["n"] - 1)).save(os.path.join(a.preview, "99-think.png"))
            print(f"Wrote preview frames (length {B['total']:.0f}s)"); return
        os.makedirs(a.out, exist_ok=True)
        wav = os.path.join(tmp, "final.wav"); T.write_wav(wav, B["audio"])
        out = os.path.join(a.out, stem + ".mp4")
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                              "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                              "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", out],
                             stdin=subprocess.PIPE)
        for i in range(B["n"]):
            p.stdin.write(R.frame(i).tobytes())
        p.stdin.close(); p.wait()
        write_extras(B, a.out, stem)
        k1 = min(1, len(B["lines"]) - 1)
        R.frame(min(B["n"] - 1, int((B["lines"][k1]["start"] + 0.5) * FPS))).resize((540, 960), Image.LANCZOS).save(os.path.join(a.out, stem + ".thumbnail.png"))
        print(f"Wrote {out} ({B['total']:.0f}s)")


if __name__ == "__main__":
    main()
