#!/usr/bin/env python3
"""Render and upload everything in schedule.json that is coming up soon.

Every video is uploaded as PRIVATE with a publish time, so YouTube publishes it by itself at that
moment. Renders and uploads can therefore happen days ahead of the publish date.

    python scheduler.py            # render + upload what is due inside the look-ahead window
    python scheduler.py --dry-run  # only print what would happen

schedule.json:  "paused": true stops everything.  "lookahead_hours" = how far ahead to prepare videos.
Each item: kind (short | lesson | story), file (script name inside shorts/, lessons/ or stories/),
publish_at (UTC, YYYY-MM-DDTHH:MM:SSZ).  A video that already has docs/videos/<name>.youtube.txt is skipped.
"""
import argparse, datetime as dt, json, os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
FOLDERS = {"short": "shorts", "lesson": "lessons", "story": "stories"}


def parse(ts):
    return dt.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)


def sh(cmd, env=None):
    print("$", " ".join(cmd), flush=True)
    return subprocess.run(cmd, env=env).returncode


def render(kind, script, outdir):
    os.makedirs(outdir, exist_ok=True)
    stem = os.path.basename(script)[:-4]
    cover = os.path.join(outdir, stem + ".thumbnail.png")
    if kind == "short":
        return sh([sys.executable, "short.py", script, "-o", outdir])
    if kind == "lesson":
        rc = sh([sys.executable, "lesson.py", script, "-o", outdir])
        if rc == 0 and sh([sys.executable, "story/make_cover.py", script, cover]) != 0:
            sh([sys.executable, "thumb.py", script, cover])
        return rc
    rc = sh([sys.executable, "story/lesson.py", script, "-o", outdir])
    if rc == 0:
        sh([sys.executable, "story/make_cover.py", script, cover])
    return rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--now", help="pretend it is this UTC time (testing), e.g. 2026-10-31T12:00:00Z")
    ap.add_argument("--only", help="only this script file name")
    args = ap.parse_args()
    sched = json.load(open("schedule.json", encoding="utf-8"))
    if sched.get("paused"):
        print("schedule.json has paused=true - nothing to do.")
        return 0
    now = parse(args.now) if args.now else dt.datetime.now(dt.timezone.utc)
    horizon = now + dt.timedelta(hours=sched.get("lookahead_hours", 120))
    min_lead = dt.timedelta(minutes=sched.get("min_lead_minutes", 20))
    keep_mp4 = os.environ.get("KEEP_MP4_ON_SITE") == "1"
    if not args.dry_run and not os.environ.get("YT_REFRESH_TOKEN"):
        print("::error::YT_REFRESH_TOKEN is not set (repo Settings > Secrets and variables > Actions).")
        return 1
    failed, done = [], 0
    for item in sorted(sched["items"], key=lambda i: i["publish_at"]):
        kind, name, when = item["kind"], item["file"], parse(item["publish_at"])
        stem = name[:-4]
        script = os.path.join(FOLDERS[kind], name)
        if args.only and args.only != name:
            continue
        if os.path.exists(os.path.join("docs", "videos", stem + ".youtube.txt")):
            continue
        if when > horizon:
            continue
        if when < now + min_lead:
            print(f"::warning::{name}: publish time {item['publish_at']} has passed or is too close - change it in schedule.json")
            continue
        if not os.path.exists(script):
            print(f"::error::{script} is missing")
            failed.append(name)
            continue
        print(f"== {name} ({kind}) -> publishes {item['publish_at']}", flush=True)
        if args.dry_run:
            continue
        outdir = os.path.join("out", stem)
        video = os.path.join(outdir, stem + ".mp4")
        ok = False
        for attempt in range(1, 4):
            shutil.rmtree(outdir, ignore_errors=True)
            if render(kind, script, outdir) == 0 and os.path.exists(video):
                ok = True
                break
            print(f"render attempt {attempt} failed", flush=True)
        if not ok:
            failed.append(name)
            continue
        env = dict(os.environ, PUBLISH_AT=item["publish_at"])
        if sh([sys.executable, "upload.py", video], env=env) != 0 or not os.path.exists(os.path.join(outdir, stem + ".youtube.txt")):
            failed.append(name)
            continue
        site = os.path.join("docs", "videos")
        os.makedirs(site, exist_ok=True)
        for f in os.listdir(outdir):
            if f.endswith(".mp4") and not keep_mp4:
                continue
            shutil.copy2(os.path.join(outdir, f), site)
        shutil.rmtree(outdir, ignore_errors=True)
        done += 1
    print(f"Prepared {done} video(s).", "Failed: " + ", ".join(failed) if failed else "")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
