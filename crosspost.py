#!/usr/bin/env python3
"""Cross-post the Practice and Mistake & fix Reels to this YouTube channel as Shorts (same video file, no extra rendering).

Runs from .github/workflows/crosspost-reels.yml. Uses this repo's own uploader (upload.py: your Google OAuth app).
  Source: the Practice / Mistake & fix list in tiny-japanese-video (posted-extra.txt); video and caption come from its output/ folder.
Each upload leaves docs/videos/xp-<stem>.youtube.txt so a video is never uploaded twice.
Safety rails: at most MAX_PER_RUN uploads per run and MAX_PER_DAY per day (YouTube's upload quota is small).

Environment: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN (already repo secrets), YT_PRIVACY (default public),
MAX_PER_RUN (2), MAX_PER_DAY (3), DRY_RUN=1 (only print the plan), ONLY_STEM (force one video), PUBLISH_AT (UTC, forces a scheduled publish).
"""
import datetime as dt, glob, json, os, re, sys, tempfile
import requests
import upload   # this repo's uploader

OWNER = "sabaghanbarlo-hash"
SRC = "tiny-japanese-video"
KIND = "jp"
SKIP = set(['px-01-introduce-yourself', 'mx-01-greeting', 'px-02-say-thank-you', 'mx-02-before-eating', 'px-03-i-dont-understand', 'mx-03-to-your-teacher', 'px-04-order-a-coffee', 'mx-04-at-night', 'px-05-say-excuse-me', 'mx-05-coming-home', 'px-06-say-delicious', 'mx-06-yes-and-no', 'px-07-count-to-three', 'mx-07-when-you-leave'])          # videos that were already posted before cross-posting started: never uploaded
MARKERS = os.path.join("docs", "videos")
NOW = dt.datetime.now(dt.timezone.utc)


def get(url, **kw):
    return requests.get(url, timeout=60, **kw)


def raw(path):
    return f"https://raw.githubusercontent.com/{OWNER}/{SRC}/main/{path}"


def marker(stem):
    return os.path.join(MARKERS, f"xp-{stem}.youtube.txt")


def uploaded_today():
    n = 0
    for p in glob.glob(os.path.join(MARKERS, "xp-*.youtube.txt")):
        m = re.search(r"^at: (\d{4}-\d{2}-\d{2})", open(p, encoding="utf-8").read(), re.M)
        n += bool(m and m.group(1) == NOW.strftime("%Y-%m-%d"))
    return n


def candidates():
    """Newest or soonest first, each as dict(stem, post_at, video_urls, caption_urls)."""
    if KIND == "jp":
        stems = [l.strip() for l in get(raw("posted-extra.txt")).text.splitlines() if l.strip()]
        return [dict(stem=s, post_at=None, video=[raw(f"output/{s}.mp4")], caption=[raw(f"output/{s}.caption.txt")]) for s in reversed(stems) if s not in SKIP]
    hdr = {"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"} if os.environ.get("GITHUB_TOKEN") else {}
    listing = get(f"https://api.github.com/repos/{OWNER}/{SRC}/contents/queue", headers=hdr).json()
    out = []
    for item in listing:
        if not item["name"].endswith(".json") or item["name"] == "schedule.json":
            continue
        j = get(item["download_url"]).json()
        if j.get("format") in ("practice", "mistake") and j.get("status") not in ("posted", "failed") and j["stem"] not in SKIP:
            out.append(dict(stem=j["stem"], post_at=j.get("post_at"), video=[raw(f"queue/videos/{j['stem']}.mp4")], caption=[raw(f"queue/videos/{j['stem']}.caption.txt")]))
    return sorted(out, key=lambda c: c["post_at"] or "")


def first_ok(urls):
    for u in urls:
        r = get(u)
        if r.status_code == 200 and r.content:
            return r
    return None


def metadata(stem, caption):
    lines = caption.splitlines() if caption else []
    head = re.sub(r"[\s\U0001F300-\U0001FAFF\u2600-\u27BF\U0001F1E6-\U0001F1FF]+$", "", lines[0]).strip() if lines else stem.replace("-", " ")
    title = upload.clean(head, 88) + " #Shorts"
    body = (caption or head).strip()
    desc = upload.clean(body + "\n\nSubscribe for a new phrase every day!\n#Shorts", 4900)
    return title, desc


def main():
    only = os.environ.get("ONLY_STEM", "").strip()
    dry = os.environ.get("DRY_RUN") == "1"
    per_run = int(os.environ.get("MAX_PER_RUN", "2") or 2)
    budget = int(os.environ.get("MAX_PER_DAY", "3") or 3) - uploaded_today()
    todo = [c for c in candidates() if (c["stem"] == only if only else not os.path.exists(marker(c["stem"])))]
    if only and not todo:     # forced by hand: allow any video that exists, even one that is not queued/posted yet
        sub = "output" if KIND == "jp" else "queue/videos"
        todo = [dict(stem=only, post_at=None, video=[raw(f"{sub}/{only}.mp4")], caption=[raw(f"{sub}/{only}.caption.txt")])]
    limit = len(todo) if only else max(0, min(per_run, budget))
    print(f"{len(todo)} video(s) waiting; uploading up to {limit} now (today's budget left: {budget}).")
    if not todo or not limit or dry:
        for c in todo[:max(limit, 3)]:
            print("  would upload:", c["stem"], c["post_at"] or "")
        return
    token = upload.access_token()
    os.makedirs(MARKERS, exist_ok=True)
    done = 0
    for c in todo[:limit]:
        stem = c["stem"]
        vr = first_ok(c["video"])
        if vr is None:
            print(f"::warning::{stem}: video file not available yet, will retry next run."); continue
        cr = first_ok(c["caption"])
        title, desc = metadata(stem, cr.text if cr else "")
        path = os.path.join(tempfile.gettempdir(), stem + ".mp4"); open(path, "wb").write(vr.content)
        publish_at = os.environ.get("PUBLISH_AT", "").strip() or ""
        if not publish_at and c["post_at"]:
            when = dt.datetime.fromisoformat(c["post_at"].replace("Z", "+00:00"))
            if when > NOW + dt.timedelta(minutes=20):
                publish_at = when.strftime("%Y-%m-%dT%H:%M:%SZ")      # YouTube publishes it by itself at the Instagram time
        privacy = (os.environ.get("YT_PRIVACY") or "public").strip().lower()
        status = {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}
        if publish_at:
            status = {"privacyStatus": "private", "publishAt": publish_at, "selfDeclaredMadeForKids": False}
        snippet = {"title": title, "description": desc, "tags": upload.TAGS + ["shorts"], "categoryId": "27"}
        print(f"Uploading {stem}: '{title}' as {status['privacyStatus']}" + (f" (goes public {publish_at})" if publish_at else ""))
        try:
            vid = upload.upload_video(token, path, snippet, status)
        except SystemExit:
            print("::error::YouTube upload stopped (see message above, usually the daily quota). Will retry on the next run."); break
        open(marker(stem), "w", encoding="utf-8").write(f"https://youtu.be/{vid}\nat: {NOW.strftime('%Y-%m-%dT%H:%M:%SZ')}\nprivacy: {status['privacyStatus']}\n" + (f"publishAt: {publish_at}\n" if publish_at else ""))
        print(f"Uploaded: https://youtu.be/{vid}"); done += 1
    print(f"Done: {done} uploaded.")


if __name__ == "__main__":
    main()
