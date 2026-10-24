# Kana lessons

One character per video, with stroke-by-stroke writing animation and an animated memory trick.

    python kana.py kana/hira-a.txt                       # landscape 1920x1080 (YouTube), output/
    python kana.py kana/hira-a.txt --format vertical     # 1080x1920
    python kana.py kana/hira-a.txt --preview prev --dummy-audio   # check frames fast
    python kana.py kana/hira-a.txt --lean                # low-memory encode for small machines

Stroke data lives in data/strokes.json (key: script -> romaji -> list of strokes).
It is derived from KanjiVG (c) Ulrich Apel, CC BY-SA 3.0, https://kanjivg.tagaini.net - keep the credit
in video descriptions (kana.py adds it automatically).

Memory-trick animations are original artwork drawn in code (kana.py, SCENES). A new character without a scene
falls back to a plain writing animation; add a scene_xxx function and register it in SCENES.
