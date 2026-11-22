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
SKIP = set(['01-whats-your-name', '202610031047-at-the-station', '202610040937-at-the-station', '202610040939-at-the-station', '202610051708-at-the-station', '202610061831-at-the-station', '202610070951-at-the-station', '202610110748-meeting-for-the-first-time', '202610111829-meeting-for-the-first-time', '202610121218-at-the-caf', '202610121224-at-the-caf', '202610130748-ordering-food', '202610140813-at-the-bookstore', '202610151318-at-the-convenience-store', '202610161841-in-the-classroom', '202610170808-at-the-supermarket', '202610180907-buying-a-train-ticket', '202610191219-at-the-clothing-store', '202610200841-at-the-park', '202610210824-at-the-pharmacy', '202610221142-at-the-beach', '202610221204-at-the-ramen-shop', '202610230946-we-missed-the-train', '202610240820-where-is-mika', '202610250826-i-m-allergic-to', '202610261221-i-missed-the-last-train', '202610271247-i-lost-my-phone', '202610280802-my-room-key-doesn-t-work', '202610280819-taking-a-taxi', '202610280907-let-s-hang-out', '202610311022-complimenting-someone', '202611040813-where-is-the-toilet', '202611040814-ramen-ticket-machine', '202611040815-can-i-pay-by-card', '202611040816-tattoo-at-the-onsen', '202611040817-itadakimasu', '202611051450-vegetarian-in-japan', '202611061428-the-check-please', '202611071322-does-this-bus-go', '202611081343-which-thank-you', '202611091642-not-spicy-please', '202611101506-sushi-recommendation', '202611121529-take-a-photo', '202611121530-speak-slowly', '202611131446-english-menu', '202611141342-wifi-password', '202611151410-hold-my-luggage', '202611161613-water-please', '202611171620-tax-free-shopping', 'mx-01-greeting', 'mx-02-before-eating', 'mx-03-to-your-teacher', 'mx-04-at-night', 'mx-05-coming-home', 'mx-06-yes-and-no', 'mx-07-when-you-leave', 'mx-08-a-present', 'mx-09-after-the-meal', 'mx-10-at-mikas-house', 'mx-11-a-compliment', 'mx-12-leaving-work', 'mx-13-old-friend', 'mx-14-saying-no', 'px-01-introduce-yourself', 'px-02-say-thank-you', 'px-03-i-dont-understand', 'px-04-order-a-coffee', 'px-05-say-excuse-me', 'px-06-say-delicious', 'px-07-count-to-three', 'px-08-lost-in-tokyo', 'px-10-hungry-at-ramen', 'px-11-stepped-on-foot', 'px-12-freezing'])   # videos that were already posted before cross-posting started: never uploaded
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
        stems = []
        for name in ("posted-extra.txt", "posted.txt"):      # Practice / Mistake & fix hand-overs, then the original daily reels
            for l in get(raw(name)).text.splitlines():
                if l.strip() and l.strip() not in stems:
                    stems.append(l.strip())
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
    budget = int(os.environ.get("MAX_PER_DAY", "4") or 3) - uploaded_today()
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
