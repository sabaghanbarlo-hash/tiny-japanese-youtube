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

## Growth update (17 Nov 2026): English-first test and two Shorts a day

Why: Tiny Japanese grows slowly next to Instagram. What the data showed:
- 93% of views the country report attributes (2,181 of 2,343) come from Japan; Shorts are 98% of all views; the 7 long videos got 76 views in total. Hypothesis: the Shorts are mostly Japanese audio and text, so YouTube tests them on viewers in Japan.
- In the niche, the Shorts that broke out run 12-40 seconds around one situation or contrast and have English titles. Ours run 59-88 seconds.

What this change does:
- Adds 8 test Shorts (`shorts/20261118-...` to `shorts/20261125-...`), one a day at 14:00 UTC (9:00 ET), as a second daily Short next to the existing 22:00 UTC slot.
- Each opens with an English hook (the narrator voice speaks the English parts), runs about 20-40 seconds and ends with a comment question.
- Sets the upload language to English (`defaultLanguage` and `defaultAudioLanguage` in `upload.py`).
- 2 unpublished long videos moved from `items` to `held_items` in schedule.json (nothing deleted): 20261122-asking-for-directions.txt, 20261129-shopping-in-town.txt. Move one back into `items` with a new `publish_at` to publish it.
- Lowers `lookahead_hours` from 120 to 48. As far as I know the YouTube API allows about 6 uploads a day per Google project (1,600 units each on a 10,000 default), and a 120-hour window would try about 10 at once.

Checkpoints:
- 24 Nov: share of views outside the home country (Studio > Analytics > Audience > Geography). Keep the English-first openings if 25% or more of views come from outside Japan (Tiny Japanese) or the target countries.
- 1 Dec: median views per format, 10 Shorts each. Keep a format at 3x today's median (about 400 Japanese, 65 French) and above 50% viewed; cut one under 1x.

Not done here: weekly listen-and-repeat compilation videos (needs a new script type); the existing queued Shorts keep their current length and titles; the weekly hiragana workflow (`kana-daily-upload.yml`) still runs on Wednesdays, disable it in Actions to stop it.

## Daily story week (Nov 29 - Dec 5) - added Nov 21, 2026
One new Japanese story every day for a week, on top of the plan above. Scripts are in `stories/`, the calendar entries are in `schedule.json` (kind `story`), and the daily scheduler renders and uploads them like everything else (private + publish time).

| Date (UTC) | UTC | ET | Tehran | Title |
|---|---|---|---|---|
| Sun Nov 29 | 15:00 | 10:00 | 18:30 | Alex's Umbrella |
| Mon Nov 30 | 14:00 | 09:00 | 17:30 | Where Is My Package? |
| Tue Dec 01 | 15:00 | 10:00 | 18:30 | Alex's First Tamagoyaki |
| Wed Dec 02 | 12:00 | 07:00 | 15:30 | Mr. Sakamoto's Cat |
| Thu Dec 03 | 22:00 | 17:00 | Fri 01:30 | Study Night |
| Fri Dec 04 | 17:00 | 12:00 | 20:30 | A Present for Mom |
| Sat Dec 05 | 20:00 | 15:00 | 23:30 | First Snow |

**Why these times:** long-form slots from Buffer's July 2026 study of 1.8M videos (Sunday 10:00 ET is the strongest slot of the week; Monday 09:00; weekday mornings; Thursday 17:00; Friday near noon; Saturday afternoon). Each slot is kept at least 4 hours away from the Shorts slots in this plan (22:00-23:00 UTC weekdays, 16:00 UTC Saturday) so long videos and Shorts do not compete. These are starting guesses, not facts about your audience.

**Honest caveat:** earlier in this plan, long videos got about 10 views in total and posting too much split the audience, which is why the other long videos are held. Seven long videos in seven days is an experiment. Check YouTube Studio after the week (views, average view duration, subscribers per video). If the stories do not hold viewers, move them to `held_items` in `schedule.json` or set `"paused": true`.

**Cast:** Marinette/Adrien or Mika/Alex plus Sakamoto (older neighbour), Ono (shopkeeper), Hana (clerk). Check any new script before it is scheduled: Actions > "Check stories (no video)" (pattern e.g. `2026*.txt`).

## Extra stories before the story week (Nov 23 - 28) - added Nov 23, 2026
Six more stories, one a day, so every day until the Nov 29 story week has one. Same method as above, but because your Shorts already fill most of these days the story is placed in the gap that is at least 3 hours from every Shorts slot (usually 17:00-20:00 UTC).

| Date (UTC) | UTC | ET | Tehran | Title |
|---|---|---|---|---|
| Mon Nov 23 | 18:00 | 13:00 | 21:30 | The Wrong Train |
| Tue Nov 24 | 18:00 | 13:00 | 21:30 | A New Haircut |
| Wed Nov 25 | 18:00 | 13:00 | 21:30 | Mika Has a Cold |
| Thu Nov 26 | 22:00 | 17:00 | Fri 01:30 | At the Convenience Store |
| Fri Nov 27 | 17:00 | 12:00 | 20:30 | Weekend Plans |
| Sat Nov 28 | 20:00 | 15:00 | 23:30 | Cooking Curry Together |

Thursday Nov 26 is US Thanksgiving, so US viewing may be lower that day.

## December plan (28 Nov 2026): one more month of Shorts, built from the Nov data

Scripts for **6 Dec - 5 Jan** are in `shorts/` (62 Shorts, two a day at 14:00 UTC and 22:00 UTC) and listed in `schedule.json`. The scheduler picks them up like everything else: it renders and uploads each one as private with a publish time about 48 hours ahead.

### What the YouTube data shows (20 Oct - 27 Nov, channel analytics + per-video stats)
Channel: 51 subscribers, about 11.8k views. 63 Shorts (median 120 views, mean 189) and 14 long videos (median 7.5 views, 152 in total).

| What | Result |
|---|---|
| Where views come from | Shorts feed 91%, YouTube search 4.5%. Shorts are 97% of views, long videos about 1%. |
| Who watches | Japan 5,801 of about 9,970 views (58%), then Indonesia 777, US 331, India 164, Philippines 80. On 17 Nov Japan was 93% of views, so roughly half of the views since the English-first change are now outside Japan. |
| Top 5 Shorts | "Stop Saying Just Arigatou" 1,055 (8.8x median); "Alex got a present. Never say this" 888 (7.4x, 58% viewed, 6 subs); "Chotto Can Mean NO" 877; "Alex said this after the meal. Big mistake!" 817 (65% viewed); "2 Polite Ways Japanese People Say No" 656. |
| Hook shape | "Polite vs rude / doesn't mean" titles: median 554-766 views. "Alex did X, never say this" (character hook): median 582 and the best retention (65% viewed). Plain "How to say X": median 134. Quiz-only and Hiragana Shorts: 0-1 views. |
| Length | Under 26 seconds: 58-71% viewed. Over 62 seconds: 36% viewed, median 127 views. The three hits over 60 seconds are topic hits; the short character hooks keep viewers better. |
| Long videos | 14 videos, median 7.5 views, 12-44% viewed. Nobody finds them yet. |

**Working:** a contrast or mistake in the first line about a phrase every learner knows; Alex making the mistake on screen; 20-30 second scripts; English hook line.
**Not working:** Hiragana Shorts, quiz-only Shorts, generic "How to say X", long videos for now, Japanese script in the title (median 90 vs 120 without it), "Japanese for Beginners / JLPT N5" title prefixes (no effect: median 124 vs 120).

**Caveats:** one Short is 9% of all Shorts views, so a single title can move any average. Titles of 60 characters or fewer did better (median 448, but only 6 videos), so the new titles are kept short. 0 comments and almost no shares on most Shorts. Retention for a few Shorts is not in the API yet.

### The December mix (62 Shorts)
- survival phrase ("Ask like this"): 27
- seasonal / culture: 19
- character hook ("Alex did X..."): 8
- mistake / "doesn't mean" hook: 8

Rules used: the first line is an English hook; 20-30 seconds; one situation; one comment question at the end; no two Shorts on the same phrase inside a week; titles 60 characters or fewer. About a quarter of the month is Christmas and New Year culture (search interest peaks then; this is a guess, not measured).

### Calendar
Every day: Short A at 14:00 UTC (9:00 ET), Short B at 22:00 UTC (17:00 ET). First: Sun 6 Dec; last: Tue 5 Jan. Exact titles are the `title:` line of each file in `shorts/`.

### Checkpoints (ship it, or change it?)
- **6 Dec:** the Nov 23 - Dec 5 story week is over. If the stories averaged under 50 views each, move the rest to `held_items` and keep at most one story a week.
- **13 Dec:** median views of the first 14 December Shorts. Keep the mix if it is above 120 (the Nov median) and above 50% viewed. Replace the weakest hook type if it sits under 60.
- **3 Jan:** compare hook types over 40+ Shorts. Double the best type for the next month, cut the worst.
- Studio > Analytics > Audience > Geography: keep the English hook if at least 25% of views come from outside Japan.

### Native-speaker check
The Japanese is AI-written and not native-verified. Worth a look first: Alex/Mika's "anata" lesson (20261206-anata), the "urusai", "gomen to your boss" and "tsumaranai gift" scripts, and the "hai, hai" script. Edit the file before its upload date or change `publish_at`.
