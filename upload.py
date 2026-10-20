#!/usr/bin/env python3
"""Upload a rendered lesson to YouTube using your own Google OAuth app.

Usage: python upload.py output/<lesson>.mp4
Reads <lesson>.description.txt (first line = title) and <lesson>.thumbnail.png next to the video.
Needs these environment variables (GitHub Actions secrets):
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
Optional:
  YT_PRIVACY   private (default) | unlisted | public
  YT_CATEGORY  YouTube category id (default 27 = Education)
  FORCE_UPLOAD 1 = upload even if this lesson was already uploaded
"""
import json, os, re, sys, time
import requests

TOKEN_URL = os.environ.get("YT_TOKEN_URL", "https://oauth2.googleapis.com/token")
UPLOAD_API = os.environ.get("YT_UPLOAD_API", "https://www.googleapis.com/upload/youtube/v3")
CHUNK = 8 * 1024 * 1024            # must be a multiple of 256 KiB
TAGS = ["learn japanese", "japanese lesson", "japanese story", "JLPT", "beginner japanese", "tiny japanese"]


def fail(msg):
    print(f"::error::{msg}", file=sys.stderr)
    sys.exit(1)


def clean(text, limit):
    text = re.sub(r"[<>]", "", text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit - 1].rsplit(" ", 1)[0] or text[:limit - 1]
    return cut.rstrip(" |,-") + "…"


def access_token():
    for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"):
        if not os.environ.get(k):
            fail(f"{k} is not set. Add it under repo Settings > Secrets and variables > Actions.")
    r = requests.post(TOKEN_URL, data={
        "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=60)
    if r.status_code != 200:
        hint = ""
        if "invalid_grant" in r.text:
            hint = (" The login was cancelled or expired. Check that the app is 'In production' (not Testing), "
                    "then repeat the OAuth Playground step to get a new refresh token.")
        fail(f"Google refused the login ({r.status_code}): {r.text[:300]}.{hint}")
    return r.json()["access_token"]


def upload_video(token, path, snippet, status):
    size = os.path.getsize(path)
    meta = {"snippet": snippet, "status": status}
    r = requests.post(f"{UPLOAD_API}/videos?uploadType=resumable&part=snippet,status",
                      headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8",
                               "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)},
                      data=json.dumps(meta), timeout=60)
    if r.status_code != 200:
        if "quotaExceeded" in r.text or "uploadLimitExceeded" in r.text:
            fail("YouTube says the daily upload limit has been reached. Try again tomorrow.")
        fail(f"Could not start the upload ({r.status_code}): {r.text[:400]}")
    session = r.headers["Location"]
    sent, tries = 0, 0
    with open(path, "rb") as f:
        while True:
            f.seek(sent)
            chunk = f.read(CHUNK)
            end = sent + len(chunk) - 1
            try:
                r = requests.put(session, data=chunk, timeout=300, headers={
                    "Content-Length": str(len(chunk)), "Content-Type": "video/mp4",
                    "Content-Range": f"bytes {sent}-{end}/{size}"})
            except requests.RequestException as e:
                r = None
                print(f"upload chunk error: {e}", file=sys.stderr)
            if r is not None and r.status_code in (200, 201):
                return r.json()["id"]
            if r is not None and r.status_code == 308:
                rng = r.headers.get("Range")
                sent = int(rng.split("-")[1]) + 1 if rng else 0
                tries = 0
                continue
            tries += 1
            if tries > 6 or (r is not None and r.status_code in (400, 401, 403, 404)):
                fail(f"Upload failed ({r.status_code if r is not None else 'no response'}): {(r.text[:400] if r is not None else '')}")
            time.sleep(5 * tries)
            try:   # ask YouTube how much it already has, then continue from there
                q = requests.put(session, headers={"Content-Length": "0", "Content-Range": f"bytes */{size}"}, timeout=60)
                if q.status_code in (200, 201):
                    return q.json()["id"]
                rng = q.headers.get("Range")
                sent = int(rng.split("-")[1]) + 1 if rng else 0
            except requests.RequestException:
                pass


def set_thumbnail(token, video_id, path):
    if not os.path.exists(path):
        return "no thumbnail file"
    with open(path, "rb") as f:
        r = requests.post(f"{UPLOAD_API}/thumbnails/set?videoId={video_id}&uploadType=media", data=f.read(), timeout=120,
                          headers={"Authorization": f"Bearer {token}", "Content-Type": "image/png"})
    if r.status_code == 200:
        return "set"
    return f"not set ({r.status_code}): the channel may need phone verification for custom thumbnails"


def main():
    if len(sys.argv) != 2 or not sys.argv[1].endswith(".mp4"):
        fail("usage: python upload.py output/<lesson>.mp4")
    video = sys.argv[1]
    folder, stem = os.path.dirname(video) or ".", os.path.basename(video)[:-4]
    marker = os.path.join("docs", "videos", stem + ".youtube.txt")
    if os.path.exists(marker) and os.environ.get("FORCE_UPLOAD") != "1":
        print(f"{stem} was already uploaded ({marker}); skipping. Set FORCE_UPLOAD=1 to upload again.")
        return
    desc_path = os.path.join(folder, stem + ".description.txt")
    lines = open(desc_path, encoding="utf-8").read().splitlines() if os.path.exists(desc_path) else [stem]
    title = clean(lines[0], 100) or stem
    description = clean("\n".join(lines[1:]), 4900)
    privacy = (os.environ.get("YT_PRIVACY") or "private").strip().lower()
    if privacy not in ("private", "unlisted", "public"):
        fail(f"YT_PRIVACY must be private, unlisted or public (got '{privacy}')")
    token = access_token()
    snippet = {"title": title, "description": description, "tags": TAGS,
               "categoryId": os.environ.get("YT_CATEGORY") or "27"}
    status = {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}
    print(f"Uploading '{title}' as {privacy} ({os.path.getsize(video) / 1e6:.1f} MB)…")
    vid = upload_video(token, video, snippet, status)
    thumb = set_thumbnail(token, vid, os.path.join(folder, stem + ".thumbnail.png"))
    url = f"https://youtu.be/{vid}"
    open(os.path.join(folder, stem + ".youtube.txt"), "w", encoding="utf-8").write(f"{url}\nprivacy: {privacy}\nthumbnail: {thumb}\n")
    print(f"Uploaded: {url} (thumbnail {thumb})")


if __name__ == "__main__":
    main()
