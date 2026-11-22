# StoryDiveBar: The Dead End Dive Bar (story set 04, `s04-dive-bar`)

Rebuild: `python3 -B Tools/Venues/make_story_dive_bar.py`. Add `--no-art` to skip redrawing the textures, which needs ImageMagick 7. `python3 Tools/Venues/check_venue.py Assets/Venues/StoryDiveBar` passes with no errors or warnings.

## Files made

- `Tools/Venues/make_story_dive_bar.py`: the scene generator. It builds the room, the story groups, the lights, the markers and the Clap motion. It is deterministic.
- `Tools/Venues/story_dive_bar_art.py`: draws every texture, plus the league-shirt torsos and their atlas. The textures are: floor lino, wood panel, nicotine plaster, black brick, felt and the table cover; the seven neon signs (STAG RIVER LAGER, Old Knuckle ALE, ice cold, THE DEAD END, LAST CALL, the "8" and OPEN); the league chalkboard, the dartboard and the DOOR envelope; and three gig posters for made-up bands, the house rules and the price board.
- `Assets/Venues/StoryDiveBar/`: `venue.json` (Preview.jpg, `Assets/Sounds/crowd.mp3` ambience at 55%), `StoryDiveBar.lvl`, `Textures/`, `Models/` (league torsos, `LeagueShirts.png`, `League.mtl`, provenance `README.md`) and `Motion/Clap.sequence`.
- `Art/Venues/StoryDiveBar/`: `Previews/`, the capture helpers `cap.sh` / `capbatch.sh` / `batch*.txt`, and `logs/`.

## The room

The bar is about 13 m x 19 m with a 3.4 m ceiling.

- **Crowd area and stage:** the crowd stands between the door (front left) and a tiny corner stage (back right, 0.32 m high).
- **Pool corner:** the pool table sits at the stage's left edge under a long green lamp on chains. The cue rack, the house rules and a neon "8" are on the left wall. The league chalkboard and a STAG RIVER LAGER neon are on the back wall, and there is a jukebox in the corner.
- **The bar** runs down the right wall:
  - a panelled front, brass foot rail and stools
  - a tap tower, the register and three pendants
  - two regulars on stools
  - backlit bottles in front of the long back-bar mirror, with ICE COLD, LAST CALL and the price board above
- **Front of house:** the door with an OPEN neon, an Old Knuckle Ale neon, and a dartboard under its own lamp with a throw line. There is also a booth with pints, gig posters, and holiday lights stapled across the joists.

**The mirror.** The engine has no planar reflections, so the mirror is a window in the bar wall onto a mirrored copy of the room. `furnish()` runs twice; the second pass goes through `Kit(mirror=True)`, which:

- reflects every position through x = 6.5
- flips yaws and rolls
- reverses the text on textures
- dims the plain lights

The reflected story groups use the same flags. The league, the table and its cover, the pints, the bartender, the envelope and the neons therefore all change in the glass as the set goes. The game builds the crowd and band itself, so the reflection gets stand-ins: seven listeners, a drummer behind a dark kit block, and a bassist. A faint smoky pane sits over the window. `beat.png` and `mirror.png` show it: the league round the covered table is visible behind the bottles.

## What each flag does

| Flag | Song (cue) | Visible change |
|------|------------|----------------|
| `league_at_table` | 1 (verse) | The green pool lamp comes on: a glowing underside, a green-white spot on the felt and a green bounce. Four league members in mustard league shirts gather round the scattered balls: a shooter bent over the felt with his back to the band, a chalker, a leaner on his cue (animated) and a watcher. They also appear in the mirror. |
| `first_listener` | 2 (first chorus) | A league shirt on a stool at the stage end of the bar, turned to the stage and sipping a pint (animated). His cue leans against the stool and there is a pint on the bar. |
| `eight_sunk` | 3 (first chorus) | The eight ball leaves the felt. A racked triangle waits in the ball return. Two more league shirts dance between the table and the stage (a looping two-step). |
| `pool_table_covered` | 4 (outro) | A dark vinyl cover marked DEAD END POOL LEAGUE goes over the felt, and the balls go. Nine fresh pints stand along the cover's front edge under their own light. Five cues go up in the wall rack. The playing league is replaced by the same four people turned round to watch the band. |
| `door_take_counted` | 5 (song end) | The bartender moves from wiping down the bar to the stage end, beside a bulging DOOR envelope with bills and coins under a green banker's lamp. LAST CALL lights red high on the bar wall. The league claps (`Motion/Clap.sequence`). The mirror catches the bartender, the envelope and the covered table. |

Moved things are two groups: the bartender, the league (playing / watching / clapping) and the cues (held / racked).

## Band spots

Two spots, matching OnStage:

- **Drummer** at (3.0, 0.32, 7.4).
- **Bass** at (0.75, 0.32, 5.15), turned 22 degrees toward the kit.

The bass combo and head are wedged at the hi-hat side and aimed at the drummer's knees, with a pint and a bar towel on top.

The dressing for the scuffed four-piece bar kit:

- a threadbare rug, gaffer marks, a setlist on the floor and a coiled lead
- two tired PA tops on poles and a wedge
- a road case with a spare cab

## Crowd

Kept small for a dive bar:

- 6 posed figures in front of the stage
- 3 mob figures by the bar
- 5 mob figures at the back

The story's league and regulars come on top of that.

## Cameras

- **Wide** from the door: it frames the pool corner (left), the stage (centre) and the bar and mirror (right).
- **Crane** over the pool lamp.
- **Desk:** a long lens.
- **Close** on the kit and the bass combo, and **Close** on the bassist.
- **Custom** shots: `pool-table`, `mirror`, `first-listener`, `door-take` and `crowd` (from the stage).
- **Intro walk:** `arrival/01..05`, in from the door.

## Light count

- `VenueShowLight`s: 15 of 40.
  - 6 stage washes: four cans on a pipe and two back washes.
  - 2 crowd washes.
  - 2 follow spots: drummer and bass.
  - 2 scanner beams.
  - 1 blinder at the stage lip.
  - 1 strobe.
  - The static directional.
- Shadow-casting lights: 1, a weak directional "through the vents". The ceiling and walls don't cast shadows, so it still reaches the room.
- The rest are plain lights:
  - neon spills, the bar pendants and the back-bar glow
  - the dartboard lamp, the jukebox, the booth and the door
  - fills for the mirrored room
  - story lights: the pool lamp and its bounce, the pints' light, the counting lamp and the LAST CALL spill
- No show light is under a story group.

## Previews (960x540, lavapipe)

`wide_song1_start.png`, `wide_song3.png`, `wide_song5_end.png`, `drummer.png`, `beat.png` (the door take and the mirror) and `pool_table.png` (song 3: the league mid-match, the dancers and the shooter's cue), plus `mirror.png` (song 4: the league round the covered table, in the glass). The game's song-title card sits over the centre in these short headless runs.

## What I couldn't do, and why

- **A true mirror:** see above. The stand-ins in the glass don't move with the real band, and the reflection is a little darker than the room.
- **Claps synced to the song's stops:** the league's claps and the dancers loop at a fixed speed. A `Sequence` doesn't follow the chart tempo unless it is a `VenueAccent`.
- **Small details in the wide:** at wide-shot size the eight ball and the ball-return rack are tiny. The two dancers, who arrive on the same flag, carry `eight_sunk` in the wide. The pool-table Custom shot catches the eight.
- **Few captures:** they were limited by the shared lock (about 9 runs), so some framing was checked only once.

## For NEEDS.md (nice-to-have, nothing blocking)

- A way to drive a looping `Sequence`'s speed from the chart tempo (for claps and dancers).
- An engine planar reflection or mirror probe, which would replace the mirrored-room trick.
