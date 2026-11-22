# StorySubway: The Last Train Busking Pitch (s02-busking)

Bellwoods station (made up) after midnight. A tiled platform between the turnstiles (crowd's left) and the stairs up to the street (crowd's right). There's a pillar with a "BUSKING PITCH 4" plate, an amber dot-matrix departure board, and two tracks behind the drummer where two lit carriages wait and then leave. Fluorescent tube rows give a green-white light, sodium orange comes down the stairwell, and the polished terrazzo carries window reflections.

## Files

- `Tools/Venues/make_story_subway.py`: the generator. It is deterministic; rerun it to rebuild. It also synthesises `Ambience.ogg` once with ffmpeg.
- `Tools/Venues/story_subway_textures.py`: draws all 18 textures with ImageMagick 7.
  - The generator draws them only if any are missing; run this file directly to redraw them all.
  - Redrawing deletes the stale cooked `.png.dds` twins.
- `Tools/Venues/story_subway_people.py`: the named characters, built from the crowd figure pieces. Each has its own clothes atlas, elbow-bent arms where needed and a Sequence loop.
- `Assets/Venues/StorySubway/`:
  - `venue.json`, `StorySubway.lvl`, `Preview.jpg`, and `Ambience.ogg` (40 s of room tone: a rumble, the tubes' 120 Hz hum, a distant train swell).
  - `Textures/`: tile, the BELLWOODS name band, terrazzo, the tactile edge, three board states, the carriage side plus its glow mask, posters, the line map, the cardboard sign, the cafe transfer, the case lining, the tunnel.
  - `Models/`: the four characters' pieces, with `README.md` giving their provenance.
  - `Motion/*.sequence`: MugBob, HandsUp, HandsUpLate, Clap, Watch.
- `Art/Venues/StorySubway/shoot.sh`: the capture helper. It runs through the flock on display :102.
- `Art/Venues/StorySubway/Previews/`: the six previews.
- `Art/Venues/StorySubway/NEEDS.md`: one non-blocking wish.

## What each flag does

| Flag | Change |
|------|--------|
| commuter_at_pillar | The mustard-scarf commuter (Mother_02, PolygonTown_02_B) appears under the departure board beside the pitch pillar. They bob to the stomp-stomp-clap holding a steel travel mug, with a tote at their feet and a light catching the mug. |
| first_train_gone | Carriage A (near track: two lit cars, wall to wall, with passenger silhouettes) collapses over 3.5 s into the right tunnel. Its window spill and the window reflections on the floor go with it, and carriage B shows on the far track. The board changes from "1 EASTBOUND NOW" to "2 WESTBOUND 1 MIN / LAST TRAIN TONIGHT". |
| family_at_pitch | Two kids dance hands-up by the bucket. With them come a scooter, a backpack and a "patch of light" lamp. Their mum appears on the 7th step of the stairs, arms folded, with a shopping bag. |
| second_train_gone | Carriage B leaves into the left tunnel, taking its spill and reflections, which reveals the lit BELLWOODS tile wall and posters. The right signal turns from green to red. The board changes to "SERVICE ENDED / FIRST TRAIN 05:58". Mum leaves the stairs and claps by the bucket. |
| tip_in_case | The drilled loonie, the handwritten cafe transfer ("Cafe Lune, Fri 9pm, ask for Ruth, you're good -M") and four coins appear on the case's red lining, under a warm pool of light. |

## Band and kit

- **Spots:** Drummer only, at (0, 0, 3.05), which matches OnStage `drums`.
- **Kit dressing** (the kit is the fixed model; this is all to the drummer's right):
  - an upturned milk crate with the orange bucket on it;
  - a second crate with the practice pad, a phone and a speaker;
  - a stick bag;
  - a cardboard "FIRST TIME BUSKING! thank you :)" sign;
  - the open case, which starts with one seed coin.

## Crowd

There are 14 heads at a full house, arranged as a busker's semicircle that leaves a sight line to the pitch:

- 2 Posed knots of 3 each, left and right;
- a Mob of 6 "off the last train";
- a Mob of 2 by the stairs.

## Cameras

- **Main shots:**
  - Wide `platform-wide`;
  - Crane `over-the-turnstiles`;
  - Desk `booth-long-lens` (30 degrees);
  - Close `sticks-and-bucket`.
- **Custom:**
  - `commuter`;
  - `tip-case` (the final beat);
  - `along-the-train`;
  - `family`;
  - `from-the-stairs`;
  - `board-and-pillar`.
- **Intro:** `arrival/01..06`, a walk down the stairs from the street to the pitch.

## Lights

- **Show lights: 27 of the 40 allowed.**
  - 18 Static:
    - the directional "tube key", the only shadowed light;
    - 10 fluorescent Bar lights;
    - the sodium stairwell spot and its bounce;
    - the booth lamp and the vending machine glow;
    - the name-wall wash and 2 trackside lamps.
  - 4 Wash: around the pitch.
  - 1 Spot: the tube over the pitch.
  - 2 Blinder: headlamp glare from the tunnel mouths.
  - 2 Strobe: buzzing tubes.
- **Plain lights under story groups:** about 14 (train spill, signals, the mug light, the family's patch, the tip glow). The board glow is a plain light too, but it is not gated.
- No VenueShowLight is gated.

## What I couldn't do

- **The trains don't slide.** A story group can only grow or shrink from its pivot. Each carriage's pivot sits past its tunnel mouth, so it collapses toward the tunnel. That reads as pulling out, but it is not a true slide (see NEEDS.md).
- **The figures are posed rigs.** Their arms rotate at the shoulder, with the elbow bend baked into the mesh. There is no skinned animation.
- **The capture budget was tight** (8 shots in total), so there were few iteration passes.
  - `wide_song1_start` and `wide_song3` were taken before the final crowd-area move, which shifted the front knots back to clear the pitch.
  - The commuter and kids are fully visible in `wide_song5_end`, `commuter` and `drummer`.
