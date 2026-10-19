# Tiny Japanese – YouTube Lessons

Turn one script file into a **landscape (1920×1080) YouTube lesson** with Mika & Alex:

1. **Story** – animated dialogue with Japanese, romaji and English subtitles
2. **Vocabulary** – each word spoken, translated, with example sentences
3. **Grammar** – the pattern, its meaning and spoken examples
4. **Quiz** – question, 5-second timer, then the answer

Separate from the Instagram Reels project (`tiny-japanese-video`), but uses the same characters, voices and look.
A lesson of about 12–16 story lines + 4 words + 2 grammar points + 3 quiz questions lands around 4–6 minutes.

## Make a video
1. Add a script in `lessons/`, e.g. `02-at-the-station.txt` (copy `01-first-day-at-school.txt` as a template).
2. Commit it. **Actions → Render YouTube lesson** renders it (or run the workflow by hand).
3. Download the `youtube-lessons` artifact: `.mp4`, `.thumbnail.png`, `.srt`, `.description.txt` (title, chapters, vocab, hashtags – paste into YouTube).

Locally: `pip install -r requirements.txt` (plus ffmpeg and a Japanese font), then
`python lesson.py lessons/01-first-day-at-school.txt`.
Quick checks: `--preview folder/` saves one image per section, `--dummy-audio` skips the voices.

## Script format
```
title: Alex's First Day at School
episode: 1
scene: classroom            # or auto

[story]
@scene home                 # optional: change background mid-story
Mika: おはよう！ | Good morning!              # romaji is automatic
Alex: ありがとう | Thanks | Arigatou          # optional 3rd part overrides romaji

[vocab]
vocab: となり | next to | tonari               # romaji part optional
example: ミカの となりに すわります。 | I sit next to Mika.

[grammar]
grammar: Noun + が すき | Use this to say you like something
example: わたしは ねこが すきです。 | I like cats.

[quiz]
quiz: Question? | option A | option B | option C | B | optional explanation
```
Speakers: `Mika`, `Alex`. Scenes: cafe, station, sakura, restaurant, store, bookstore, classroom, home, airport, street, park, beach, hospital.
Everything except `[story]` is optional.

## Notes
- Voices are Microsoft Edge neural voices (Nanami, Keita, Aria). On Actions the render stops rather than using the low-quality fallback voice (`STRICT_VOICE=1`); just re-run.
- Mika says each vocab/grammar example slowly; English is read by a narrator voice.
