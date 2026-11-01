# Tiny Japanese - YouTube plan (Nov 2026)

Written Nov 1, 2026 after reading the live channel's analytics. Everything below is already wired up:
the scripts are in `shorts/`, `lessons/`, `stories/`, the calendar is `schedule.json`, and
`.github/workflows/scheduled-publish.yml` renders and uploads each video a few days early. YouTube then
publishes it by itself at the time listed.

## What the first 9 days showed (Oct 22-30, 20 videos, 11 of them already in YouTube Analytics)
Total: about 1,370 views. **Shorts 1,356, long videos 10.**

| Video | Views | x channel median (18) | Avg viewed |
|---|---|---|---|
| Short "Stop Saying Arigatou" | 1,046 | 58x | 33% |
| Short "I'm Hungry" | 181 | 10x | 40% |
| Short "I Don't Understand" | 54 | 3x | 36% |
| Short "Order a Drink" | 34 | 1.9x | **66%** |
| Short "3 Natural Phrases" | 18 | 1x | 56% |
| Story Ep.1 / Ep.2, Hiragana, quiz Shorts | 1-8 each | under 0.5x | - |

**Working**
- One Short took off: the one titled as a mistake ("Stop saying...") about a phrase every learner knows.
  The niche's top recent Shorts use the same shape ("Stop saying X", "X doesn't mean Y", "Y is a soft no").
- Short scripts with a real mini-scene and a clear payoff hold viewers best (56-66% watched).
- 93% of views come from the Shorts feed, so Shorts are the discovery engine right now.

**Not working**
- Long videos (stories, lessons, hiragana): 10 views in total. Nobody finds them yet; the channel is too small.
- Quiz-only Shorts ("Guess the word"): 1 view. Generic "How to say X" titles: 18-54 views.
- Posting 20 videos in 9 days, with several near-duplicate topics (hello x2, hungry x3). Same topic twice splits the audience.
- Daily hiragana long videos: about 1 view each, so they were pausing the feed instead of building it.

**Caveats (honest ones)**
- 100% of views are reported from Japan. Those viewers may be Japanese people or learners living in Japan, not the
  English-speaking learners you want. This is the biggest open question; the checkpoints below test it.
- 0 comments and 0 shares so far. 9 days of data on a new channel is thin; treat the numbers as a first read.
- Niche comparison used the titles of the most-viewed recent Japanese-learning Shorts. The detailed stats call
  was out of API quota, so there is no per-video multiple for the niche.
- Posting times are starting guesses, not measured.

## The plan: ship the winner, test one idea at a time
**Rhythm (5 Shorts + 1 long per week)**
- Shorts Mon / Tue / Wed / Fri at 22:00 UTC (5pm New York, 7am Tokyo next day). Sat at 16:00 UTC (11am New York).
- One long video every Sunday at 14:00 UTC (9am New York): lesson, story, lesson, story.
- 2-3 of every 5 Shorts use the "mistake" hook (Stop saying X / X does NOT mean Y / X can mean NO). The rest are
  survival phrases (excuse me, where is the station, how much). No more quiz-only Shorts.
- Each Short: mistake or question in the first line, one clean fix, 2 words, a quiz at the end, about 35-50 seconds.
- The daily hiragana upload (`kana-daily-upload.yml`) now runs **once a week (Wednesdays)** instead of daily.
  To change it back, edit the `cron` line in that file.

**Calendar** (Tehran time shown because that's where you are; ET is New York)

| Date (UTC) | Type | ET | Tehran | Title |
|---|---|---|---|---|
| Mon Nov 02 | Short | 17:00 | Tue 01:30 | “Kudasai” Sounds Too Direct! Say This Instead |
| Tue Nov 03 | Short | 17:00 | Wed 01:30 | Stop Saying “Sayonara” — Say This Instead |
| Wed Nov 04 | Short | 17:00 | Thu 01:30 | 3 Ways to Say “Excuse Me” in Japanese |
| Fri Nov 06 | Short | 17:00 | Sat 01:30 | “Daijoubu” Can Mean Yes AND No! |
| Sat Nov 07 | Short | 11:00 | Sat 19:30 | How to Ask “Where Is the Station?” in Japanese |
| Sun Nov 08 | Lesson | 09:00 | Sun 17:30 | Ordering at a Cafe |
| Mon Nov 09 | Short | 17:00 | Tue 01:30 | Stop Saying “Watashi wa” in Every Sentence |
| Tue Nov 10 | Short | 17:00 | Wed 01:30 | Stop Saying “Konnichiwa” at Night! |
| Wed Nov 11 | Short | 17:00 | Thu 01:30 | 3 Ways to Say “I’m Sorry” in Japanese |
| Fri Nov 13 | Short | 17:00 | Sat 01:30 | “Itadakimasu” Does NOT Mean “Thank You” |
| Sat Nov 14 | Short | 11:00 | Sat 19:30 | How to Ask “How Much Is This?” in Japanese |
| Sun Nov 15 | Story | 09:00 | Sun 17:30 | A Night at the Festival |
| Mon Nov 16 | Short | 17:00 | Tue 01:30 | “Hai” Doesn’t Always Mean “Yes” in Japanese |
| Tue Nov 17 | Short | 17:00 | Wed 01:30 | 3 Ways to Say “Delicious!” in Japanese |
| Wed Nov 18 | Short | 17:00 | Thu 01:30 | How to Say “My Japanese Is Not Good Yet” |
| Fri Nov 20 | Short | 17:00 | Sat 01:30 | “Chotto” Can Mean NO in Japanese (Polite Refusal) |
| Sat Nov 21 | Short | 11:00 | Sat 19:30 | How to Ask “Where Is the Toilet?” in Japanese |
| Sun Nov 22 | Lesson | 09:00 | Sun 17:30 | Asking for Directions |
| Mon Nov 23 | Short | 17:00 | Tue 01:30 | “Suki” Can Sound Like a Confession! |
| Tue Nov 24 | Short | 17:00 | Wed 01:30 | How to Say “I’m Full!” in Japanese |
| Wed Nov 25 | Short | 17:00 | Thu 01:30 | 3 Ways to Say “Yes” in Japanese |
| Fri Nov 27 | Short | 17:00 | Sat 01:30 | Stop Saying “Kawaii” for Everything! Say These |
| Sat Nov 28 | Short | 11:00 | Sat 19:30 | Count to 10 in Japanese in 30 Seconds |
| Sun Nov 29 | Story | 09:00 | Sun 17:30 | Shopping in Town |

## How the automation works
- `schedule.json` lists every video and its publish time. `paused: true` stops everything.
- Every day at 04:17 UTC `scheduler.py` looks 5 days ahead, renders anything due, and uploads it as private with a
  publish time. Renders retry 3 times. Uploads are marked in `docs/videos/<name>.youtube.txt`, so nothing uploads twice.
- Videos stay private until YouTube publishes them at the set time. You can watch them in YouTube Studio before then.
- To move or cancel a video: change its `publish_at` or delete the item in `schedule.json` (before it uploads), or
  change the date in YouTube Studio (after it uploads).
- Run it by hand: GitHub > Actions > Scheduled publishing > Run workflow.

## Checkpoints (ship it, or change it?)
- **Nov 8:** are the first 5 scheduled Shorts getting more than about 100 views each, and are Shorts still above 50%
  watched? If yes, keep going. If the "mistake" Shorts sit at 20-50 views, the Arigatou hit was mostly the topic - rewrite titles.
- **Nov 15:** check the country split. If it is still 100% Japan after 10+ Shorts, test one Short with a bigger English
  hook on screen and an English-learner title; the goal is learners abroad, not viewers in Japan.
- **Nov 22:** first read on the long videos. If lessons/stories are still under 20 views, stop stories and run lessons
  as search-style videos ("Japanese for ordering at a cafe") with searchable titles; keep the Shorts.

## December outline
Repeat the 3 mistake + 2 survival rhythm. Convert the best 3 Shorts into longer search-friendly lessons. Keep one story a
month. Move hiragana back to more frequent only if the weekly ones reach 20+ views each.

## Things to do by hand
- Nothing for the schedule itself. Check YouTube Studio > Content once a week for failed uploads (the GitHub Actions run turns red).
- Keep the Google OAuth app "In production" or the upload login expires after 7 days.
