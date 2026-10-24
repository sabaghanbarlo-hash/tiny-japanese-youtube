# Directing guide (Tiny Japanese Story)

The studio does not guess a story from plain text: it plays a **directed script**. The usual workflow is to tell Claude the story idea ("Mika and Alex go to an amusement park, buy cotton candy, come back and ride the rides") and paste the directed script Claude writes into the studio page. This guide is the full vocabulary, so any story can be written with it.

## Script skeleton
```
title: A Day at the Amusement Park
episode: 2
scene: amusement park        # starting place

[story]
@scene amusement park        # change place (also allowed between directions)
> Mika enters left           # direction lines start with ">"; "&" = at the same time as the line above
Mika: こんにちは！ | Hello!   # spoken line: Speaker: Japanese | English | (optional romaji)
[vocab] [grammar] [quiz]     # same as the original generator
```
Directions run in order; then the next spoken line plays. Speech cannot happen during a direction (a ride or a walk), so put the comment *after* it.

## Directions (who = Mika, Alex, both)
| Direction | Notes |
|---|---|
| `enters left` / `enters right` / `enters left to center` | walks in from off-screen to home (or the spot) |
| `walks to <spot>` / `runs to <spot>` | spot: left, center, right, home, `next to Alex`, a percent (40), or a named spot of the place |
| `exits left` / `exits right` | walks off-screen |
| `looks <feeling>` | confused, surprised, happy, sad, shy, neutral (also: excited, worried, embarrassed...) |
| `faces <name / left / right>`, `looks at <name>` | |
| `waves`, `jumps`, `laughs`, `nods`, `cheers` | |
| `holds <item>`, `buys <item>`, `picks up <item>` | `buys` adds a little hop |
| `eats`, `eats <item>`, `drinks` | edible: cotton candy, ice cream, popcorn (3 bites, the item shrinks) |
| `drops` / `finishes` | puts the item away (an open umbrella stays open; `closes the umbrella` folds it) |
| `gives <item> to <name>` | `gives it to Alex` also works |
| `rides the carousel` / `rides the ferris wheel [for 8]` | amusement park only; walks to the ride, boards, rides, steps off |
| `opens the umbrella` / `closes the umbrella` | umbrella shown open over the character(s), or folded in the hand; `gives the umbrella to Alex` hands it over |
| `wait 1.5` | pause (seconds) |

`both` does the same for both characters and spreads them out so they do not stand on the same spot. When two characters meet, they turn toward each other and the one already there gets a "!". Expressions stay until changed (`looks neutral` resets).

## Weather and time of day
Rain, storm, snow, and time of day are drawn over any outdoor place (street, park, sakura, beach, amusement park, shrine, zoo, airport, town, mountain, river, schoolyard, bus stop, festival). Indoor places only get the light tint.

| Direction | Effect |
|---|---|
| `@weather rain` / `storm` / `snow` / `clear` | falling rain (with ripples and a grey sky), a storm (heavier rain, lightning), snow, or back to dry; fades in and out over about a second |
| `@time morning` / `day` / `sunset` / `night` | colour grading of the whole picture; night adds stars and a moon |
| header lines `weather: rain` and `time: night` | same thing for the whole story from the first frame |

**Automatic:** when you do not set weather yourself, the studio reads the story. A line that says "It's raining!" (or あめだ / あめが ふって いる) starts the rain a moment *before* that line, so it is already falling when someone notices it. "The rain stopped!" (あめが やんだ) ends it, "It's snowing!" starts snow, and words like "night", "sunset" or "morning" change the light. If a character says "I have an umbrella!" or "Let's share my umbrella", they open one in the rain, and both stay under it (no rain falls on them) until someone closes it. Anything you write with `@weather`, `@time` or `opens/closes the umbrella` wins over the automatic reading.

Characters keep an open umbrella while walking and between places, so write `> Mika closes the umbrella` when they go inside.

## Items
cotton candy, ice cream, balloon, ticket, drink, bag, book, popcorn, plush (prize toy), umbrella. Items are not drawn while riding.

## Places and their spots
| Place (`@scene ...`) | Named spots |
|---|---|
| amusement park (fair, funfair, carnival) | entrance, ticket booth, carousel, cotton candy stall, prize stall (game stall), ferris wheel, bench. Rides: carousel, ferris wheel |
| shrine (temple, torii) | torii gate, offering box, lantern, steps |
| zoo | entrance, giraffe, elephant, fence |
| aquarium | big tank, jellyfish, shark, entrance (fish and jellyfish swim) |
| classroom | door, blackboard, desk |
| cafe | counter, window, door |
| station | platform, ticket gate, ticket machine |
| store | register, shelf, door |
| town (shopping street) | vending machine, bakery, fruit shop, flower shop |
| mountain (Mt. Fuji, lake) | pine tree, bench, lake |
| river (riverside, bridge) | willow tree, bridge, riverbank |
| train (subway) | door, window, seat (the scenery scrolls past the windows) |
| bedroom | bed, window, desk |
| kitchen | counter, stove, window, fridge (steam from the pot) |
| schoolyard (playground, school gate) | gate, door, flagpole |
| festival (matsuri, fireworks) | takoyaki stall, goldfish stall, shaved ice stall (night, fireworks) |
| bus stop | bus stop, bench, sign, bus |
| home, bookstore, restaurant, airport, street (night), park, beach, hospital, sakura | no named spots yet (use left / center / right / percent) |

**Variety:** every place has three looks (normal, warm, cool). Which one is used depends on the story title and on how many times the place has been visited, so the same place does not look identical when the story comes back to it, and a different story gets different colours. Use two or three different places (and times of day) in one story so the video does not feel flat.

## Adding things (for whoever extends the engine)
- New place: add its colors, keywords, aliases, spots and a drawing function in `scenery.py` (the 9 newest places live there; the older ones are in `NEW_SCENES` / `SCENE_DRAW` in `acting.py`). Add it to `OUTDOOR` in `atmos.py` if weather should fall on it. Animated parts go in `dynamic()`.
- Weather, time-of-day grading, umbrella drawing and precipitation: `atmos.py`.
- New item: draw it in `_draw_item` and add it to `ITEMS` (and `EDIBLE` if it can be eaten).
- New ride: moving scenery goes in `draw_dynamic`, rider position in `ride_pos`, spot in `RIDES`.
- New verb: add the word to `VERBS`, then handle it in `Stage._one`.
