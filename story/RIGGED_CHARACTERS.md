# Rigged characters (story mode)

Story characters are now drawn from separate parts (head, hair, brows, eyes, mouth, torso, two-joint arms, legs) by
`story/rigsvg.py` and posed every frame, instead of the old flat sprite. Everything else in story mode (director scripts,
places, weather, items, rides, walking) is unchanged: only `acting.rig()` draws the characters differently.

- Any character in `lesson.CHARS` (hair / skin / top / accent / long_hair) gets a rig automatically, so new characters added
  later need no extra drawing code. Marinette and Adrien have their own designs (used by the Tiny French project).
- Needs `resvg-py` (in requirements.txt; no system packages needed). If it is missing or anything fails for a character, that
  character falls back to the old drawing, so a render never breaks.
- `STORY_RIG=classic python story/lesson.py ...` renders with the old characters (for comparing).
- Held items (cotton candy, balloon, umbrella...) are still drawn by the original helpers, placed at the rig's right hand.
- Lower bodies of Marinette / Adrien are placeholders.
