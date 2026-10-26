#!/usr/bin/env python3
"""Put the horizontal thumbnails from docs/videos/ onto the Shorts that are already on YouTube.

Usage: python set_thumbnails.py            (all uploaded Shorts)
       python set_thumbnails.py <stem>     (one, e.g. short-202610261837-guess-the-japanese-word)
Needs the same YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN secrets as upload.py.
"""
import glob, os, re, sys
import upload

def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    token = upload.access_token()
    for marker in sorted(glob.glob("docs/videos/short-*.youtube.txt")):
        stem = os.path.basename(marker)[:-len(".youtube.txt")]
        if only and stem != only:
            continue
        m = re.search(r"youtu\.be/([\w-]+)", open(marker, encoding="utf-8").read())
        if not m:
            print(f"{stem}: no video id in {marker}"); continue
        print(f"{stem}: thumbnail {upload.set_thumbnail(token, m.group(1), f'docs/videos/{stem}.thumbnail.png')}")

if __name__ == "__main__":
    main()
