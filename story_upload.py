#!/usr/bin/env python3
"""Upload new story videos from the tiny-japanese-story repository to YouTube.

Runs on a schedule (see .github/workflows/story-upload.yml). It looks at docs/videos/ of the story repo,
and for every video that has no marker in story-uploads/ it uploads the video with the title/description from
<name>.description.txt and the cover image <name>.thumbnail.png, then writes story-uploads/<name>.youtube.txt.
Uses the same YT_* secrets and YT_PRIVACY variable as upload.py (which is reused, not changed).
Environment: STORY_REPO (default sabaghanbarlo-hash/tiny-japanese-story), MAX_UPLOADS (default 2), GITHUB_TOKEN (optional).
"""
import os, sys, tempfile
import requests
import upload as U

REPO = os.environ.get("STORY_REPO", "sabaghanbarlo-hash/tiny-japanese-story")
BRANCH = os.environ.get("STORY_BRANCH", "main")
MAX_UPLOADS = int(os.environ.get("MAX_UPLOADS") or 2)
MAX_TRIES = 3
OUT = "story-uploads"
HEAD = {"Accept": "application/vnd.github+json"}
if os.environ.get("GITHUB_TOKEN"):
    HEAD["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]


def listing():
    r = requests.get(f"https://api.github.com/repos/{REPO}/contents/docs/videos?ref={BRANCH}", headers=HEAD, timeout=60)
    if r.status_code == 404:
        return {}
    r.raise_for_status()
    return {f["name"]: f["download_url"] for f in r.json() if f.get("download_url")}


def fetch(url, dest):
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)


def tries(stem):
    p = os.path.join(OUT, stem + ".failed.txt")
    try:
        return int(open(p).read().split()[0])
    except Exception:
        return 0


def main():
    os.makedirs(OUT, exist_ok=True)
    files = listing()
    todo = []
    for name in sorted(files):
        if not name.endswith(".mp4"):
            continue
        stem = name[:-4]
        if stem + ".youtube.txt" in files or os.path.exists(os.path.join(OUT, stem + ".youtube.txt")):
            continue
        if stem + ".description.txt" not in files:
            continue
        if tries(stem) >= MAX_TRIES:
            continue
        todo.append(stem)
    if not todo:
        print("No new story videos to upload.")
        return 0
    if not os.environ.get("YT_REFRESH_TOKEN"):
        print("YouTube secrets are not set in this repository - nothing uploaded.")
        return 0
    privacy = (os.environ.get("YT_PRIVACY") or "private").strip().lower()
    if privacy not in ("private", "unlisted", "public"):
        print(f"YT_PRIVACY must be private, unlisted or public (got '{privacy}')")
        return 1
    status = 0
    for stem in todo[:MAX_UPLOADS]:
        print(f"== {stem}")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                for ext in (".mp4", ".description.txt", ".thumbnail.png"):
                    if stem + ext in files:
                        fetch(files[stem + ext], os.path.join(tmp, stem + ext))
                lines = open(os.path.join(tmp, stem + ".description.txt"), encoding="utf-8").read().splitlines() or [stem]
                title = U.clean(lines[0], 100) or stem
                snippet = {"title": title, "description": U.clean("\n".join(lines[1:]), 4900), "tags": U.TAGS,
                           "categoryId": os.environ.get("YT_CATEGORY") or "27"}
                token = U.access_token()
                video = os.path.join(tmp, stem + ".mp4")
                print(f"Uploading '{title}' as {privacy} ({os.path.getsize(video) / 1e6:.1f} MB)...")
                vid = U.upload_video(token, video, snippet, {"privacyStatus": privacy, "selfDeclaredMadeForKids": False})
                thumb = U.set_thumbnail(token, vid, os.path.join(tmp, stem + ".thumbnail.png"))
            open(os.path.join(OUT, stem + ".youtube.txt"), "w", encoding="utf-8").write(
                f"https://youtu.be/{vid}\nprivacy: {privacy}\nthumbnail: {thumb}\n")
            fp = os.path.join(OUT, stem + ".failed.txt")
            if os.path.exists(fp):
                os.remove(fp)
            print(f"Uploaded: https://youtu.be/{vid} (thumbnail {thumb})")
        except (SystemExit, Exception) as e:   # upload.fail() exits; keep going with the next video
            n = tries(stem) + 1
            open(os.path.join(OUT, stem + ".failed.txt"), "w").write(f"{n} failed attempt(s); gives up after {MAX_TRIES}. Last error: {e}\n")
            print(f"::warning::{stem}: upload failed ({e}); attempt {n} of {MAX_TRIES}")
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
