# StoryBasement: set 01 "In the Basement with My AirPods" (s01-basement)

It is the player's own hideout basement, played as a rehearsal. The drummer is alone on the hand-me-down kit on its carpet offcut. The only audience is the cat on the couch and mom's camcorder. The room comes from the hideout's own builder functions, so it is the same basement the menu shows.

## Files
- **`Tools/Venues/make_story_basement.py`**: the generator. Deterministic; writes `Assets/Venues/StoryBasement/StoryBasement.lvl` and `venue.json` (Name = the set title, Author Drumsmith, Version 1, Preview and Ambience).
- **`Tools/Venues/story_basement_room.py`**: imports `Tools/Hideout/basement.py` read-only (bytecode writing off). Runs the basement builders, then `venue_safe()` makes the result venue-legal:
  - Removes the hideout-only parts: motion, stations, view, the hideout drummer, the camcorder Camera and the AudioSources.
  - The hideout's Day/Night groups become the `window_well_blue` flag.
  - Items not earned yet are removed; their masking-tape outlines stay. The band stays unnamed ("BAND NAME TBD").
  - Live text gets fixed words: the floor setlist is this set's five songs, plus the wishlist and the tally. The clock reads 5:10.
  - No light casts shadows, and the hideout's lamps are 2.5x brighter for the venue's exposure.
- **`Tools/Venues/story_basement_textures.py`**: draws `Textures/CrtSnow`, `CrtTake`, `CrtPause`, `KitchenLino` and `PhoneScreen` with ImageMagick, and mixes `Ambience.wav` with ffmpeg from the hideout's furnace, fan and drip room tone.
  - `CrtTake` and `CrtPause` are made from a headless capture at the camcorder's position (`Art/Venues/StoryBasement/Scratch/camcorder_raw.png`): title card smeared out, VHS scanlines, REC/PAUSE and a tape counter added.
  - Deletes each redrawn PNG's `.dds` twin so the game recooks it.
  - ImageMagick isn't on the PATH; the script falls back to the Nix store binary.
- **Models:** none copied (no `Models/README.md`). The scene references `Assets/Models/Venue/CameraTripod.obj`, `ToolBox.obj` and the Backyard's `Sofa.obj` in place, plus the hideout textures.
- **Scratch:** `Art/Venues/StoryBasement/Scratch/` holds test captures and `cap.sh`.

## What each flag does
| Flag (song, cue) | Change |
|---|---|
| `tape_rolling` (1, intro) | The camcorder's tally lamp goes from dark to glowing red, with red light spilling around it; the viewfinder lights up. The CRT by the couch goes from snow ("CH 3") to the camcorder picture with REC and the counter. |
| `crt_turned_toward_kit` (2, outro) | The CRT and its red milk crate leave the couch corner and stand at the front right of the kit, turned to the drummer. Blue TV light falls on the kit. The coax trails back to a clean square and drag marks on the floor. |
| `window_well_blue` (3, first chorus) | The window well's daylight glass and sun beam fade over 6 s to night glass, a cold streetlamp beam and a passing-car light. The kitchen door at the top of the stairs opens a crack: a narrow light and a stripe down the middle of the treads. |
| `kitchen_door_ajar` (4, verse) | The door swings wide, propped by a laundry basket with a red sock on top. A mug of tea sits on the top step. The kitchen shows through: lino, cupboards, kettle, pendant lamp. A warm beam floods the stairs, every tread gets a rectangle of light, and a pool spreads at the foot. |
| `crate_at_stairs` (5, song end) | One orange bucket leaves the kit. A blue milk crate holding the old bucket, three sticks, the phone speaker and a tape tag reading "SAT - SUBWAY" sits lit at the foot of the stairs. The turned CRT switches to the held last frame (PAUSE with a tracking band). |

The door's three states are nested story groups (shut, cracked, propped). Each light sits under only one group, so their dimming never conflicts.

## Band and crowd
- One Drummer spot at (0, 0, 5.3), the hideout drummer's place, facing the stairs (OnStage `drums`).
- No crowd areas.

## Cameras (13)
- Wide `couch-corner`: from the front right over the couch; shows the stairs, kit, window well, CRT and the crate's spot, so every flag reads here.
- Crane `joists`, Desk `top-of-stairs` (long lens down the flight), Close `snare-side`.
- Custom: `camcorder` (the tripod's view), `over-the-shoulder` (behind the drummer onto the turned CRT), `up-the-stairs` (the kitchen-light beat), `window-well` (never captured, unchecked).
- `arrival/01..05`: a walk down the stairs from the kitchen into the room.

## Lights
- 32 Lights, 12 VenueShowLights, 1 shadowed light.
- Washes: 10 Christmas-light bulbs, groups 0-2. Follow spot: a clamp lamp on the joist is the drummer's Spot.
- Shadowed light: a faint Static directional, blocked by the house; there so the game doesn't add its own key light.
- No show light is under a story group.

## Previews (960x540, `Art/Venues/StoryBasement/Previews/`)
`wide_song1_start.png`, `wide_song3.png`, `wide_song5_end.png` (also `Preview.jpg`), `drummer.png`, `beat.png` (up the stairs into the kitchen light), `over_the_shoulder.png`.

## What I couldn't do
- The CRT shows stills, not a live feed: the loader strips Cameras, and VenueScreens are built outside story groups, so they can't be gated or moved with the CRT.
- The hideout's small motions are frozen (swinging bulb, blinking tally, breathing cat, running clock are hideout-only). Only the Christmas lights move, driven by the show's washes.
- The wide can't see the kitchen door itself (above the ceiling, behind the camera); it reads through its light on the treads and floor. `up-the-stairs` shows the doorway.
- Lighting was tuned on few frames. Song 3's window well turning blue reads only faintly in the wide; in song 2 the turned CRT shows its back to the wide, reading through its glow and in the over-the-shoulder shot.

## NEEDS.md
1. A VenueScreen that story groups can gate and move, so the CRT could carry a live camcorder feed.
2. Optionally, venues running the simple hideout motions.
