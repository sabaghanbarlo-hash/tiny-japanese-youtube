# Tiny Japanese – YouTube Lessons

Turn one script file into a **landscape (1920×1080) YouTube lesson** with Mika & Alex:

1. **Story** – animated dialogue with Japanese, romaji and English subtitles
2. **Vocabulary** – each word spoken, translated, with example sentences
3. **Grammar** – the pattern, its meaning and spoken examples
4. **Quiz** – question, 5-second timer, then the answer

Separate from the Instagram Reels project (`tiny-japanese-video`), but uses the same characters, voices and look.
A lesson of about 12–16 story lines + 4 words + 2 grammar points + 3 quiz questions lands around 4–6 minutes.

## Make a video
1. Open the studio page, pick **Lesson video** or **Short (vertical)**, paste a script, press the button (or add a script to `lessons/` or `shorts/` and run the matching workflow with the file name).
2. The job renders the video, uploads it to YouTube (if the secrets below are set) and publishes it on the site.
3. Outputs: `.mp4`, `.thumbnail.png`, `.srt` (lessons), `.description.txt` (title, chapters, vocab, hashtags) and `.youtube.txt` (the YouTube link).

Locally: `pip install -r requirements.txt` (plus ffmpeg and a Japanese font), then
`python lesson.py lessons/01-first-day-at-school.txt` or `python short.py shorts/short-01-first-day.txt`.
Quick checks: `--preview folder/` saves frames, `--dummy-audio` skips the voices.

## Thumbnails
Lesson thumbnails use the approved illustration in `assets/thumbnail_template.png` (chalkboard, Mika & Alex, brush-stroke banner). `thumb.py` paints each episode's `Ep.N · Title` onto it (the workflow runs it after rendering). Replace the template image to change the look for all future videos. If the file is missing, the built-in drawn cover is used.

## Shorts
`short.py` makes a **vertical 1080×1920 Short** (about 45 seconds): hook → mini story (4–6 lines) → 1–2 key words → one quick quiz question (3-second timer) → "follow" outro. Same script format as lessons; `[grammar]` is ignored and the story is capped at 8 lines. Example: `shorts/short-01-first-day.txt`. Run it from the studio page's **Short** tab or via **Actions → Render YouTube Short**. The description includes `#Shorts`.

## Automatic YouTube upload
Uses your own Google Cloud OAuth app (no shared quota). Add these under **Settings → Secrets and variables → Actions**:

| Kind | Name | Value |
|---|---|---|
| Secret | `YT_CLIENT_ID` | OAuth client ID |
| Secret | `YT_CLIENT_SECRET` | OAuth client secret |
| Secret | `YT_REFRESH_TOKEN` | refresh token (from the OAuth Playground, scope `youtube.upload`) |
| Variable (optional) | `YT_PRIVACY` | `private` (default), `unlisted` or `public` |

Keep the Google consent screen **In production**, otherwise the refresh token expires after 7 days.
A video is uploaded once; its `docs/videos/<name>.youtube.txt` marks it as done. If the upload fails the video is still published on the site and the job is marked failed so you notice.
Custom thumbnails need a phone-verified YouTube channel.

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

## Three kinds of video
The studio page has three tabs:

| Tab | What you get | Script folder | Job |
|---|---|---|---|
| **Short** | vertical 1080x1920 Short, about 45 seconds | `shorts/` | Render YouTube Short |
| **Long** | landscape lesson: story, vocabulary, grammar, quiz | `lessons/` | Render YouTube lesson |
| **Story** | like Long, but Mika and Alex *act out* the story: they walk, react, hold things, change places; rain, snow, umbrellas, day and night, 26 places with several looks | `stories/` | Render story video |

All three upload to YouTube the same way (see above) and publish on the studio page. The story engine lives in `story/` (`lesson.py`, `acting.py`, `atmos.py`, `scenery.py`, `make_cover.py`) and shares `thumb.py` and `upload.py` with the other two. How to write a directed story script: `story/DIRECTING.md`; the prompt to give Claude so it writes one for you is `story/DIRECTOR_PROMPT.md` (also on the Story tab of the studio page). Run it by hand: `python story/lesson.py stories/<name>.txt -o output`, then `python story/make_cover.py stories/<name>.txt output/<name>.thumbnail.png`.

Story videos are made and uploaded from this repository only. The older `tiny-japanese-story` repository is no longer needed.
