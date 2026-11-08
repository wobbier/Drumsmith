# Venue and Band

> Verified against game commit 5973499 plus the venue change, 2026-11-08. Engine submodule at 0c32daef.

The concert under the note highway: a stage with a band playing the song, a crowd reacting to it, the light show (`Docs/Stage-Lighting.md`) and a camera crew cutting between shots, all driven by the chart's Rock Band venue data and played on the song clock. The highway is drawn over it by an overlay camera, so the venue underneath can change without touching gameplay.

## Overview

- **Layers.** The venue is built kilometres from the highway (`VenueLayout::kVenueOrigin`), so neither camera ever sees the other's world. The venue's camera becomes the main camera; the highway's camera (`Main Camera` under `TrackMover` in `Assets/Example.lvl`) becomes an engine **overlay camera** (`Camera::Overlay`, `Engine/Docs/Rendering-Pipeline.md` → Overlay cameras) composited on top. Its far end fades into the venue (`OverlayFadeStart` / `OverlayFadeEnd`) and its dark board lets the stage show through (`OverlayDarkOpacity`); its own fog is turned off while the venue runs.
- **Everything is primitives.** No meshes or clips: the set, instruments and people are the engine's cube, sphere, cylinder, capsule and plane primitives with `DiffuseMaterial`s (`VenueKit`), posed procedurally every frame (`Puppet`). Pieces sharing a colour instance into one draw.
- **Data first, fallbacks second.** Charts converted from Rock Band `notes.mid` carry camera cuts, post-processing looks, band animation states, drum limb notes, strums and sung notes (see *What is imported*). Charts without them (`.chart` songs, sparse MIDI) get the same show built from their sections, tempo and drum notes.

## Key Files

| File | Role |
|------|------|
| `Game/Source/Venue/VenueShow.h/.cpp` | Owns the venue: builds the set, band, crowd, director and lights; turns the highway camera into the overlay; updates them on the song clock; pyro and the stage-edge LED strip |
| `Game/Source/Venue/VenueLayout.h` | The floor plan: venue origin, stage size, member spots, crowd area |
| `Game/Source/Venue/VenueKit.h/.cpp` | Spawns primitive pieces (full sizes in, primitive scale worked out) and deletes them on `Clear` |
| `Game/Source/Venue/Puppet.h/.cpp` | A figure from primitives: joints from angles (FK) or a reach target (two-bone IK), capsules laid between joints |
| `Game/Source/Venue/Band.h/.cpp` | Drummer, guitarist, bassist, singer, keyboard player: instruments and their animation |
| `Game/Source/Venue/Crowd.h/.cpp` | The audience and its moods |
| `Game/Source/Venue/Director.h/.cpp` | Camera cuts → shots, post-processing looks, the LED wall's feed camera |
| `Game/Source/Venue/VenueTiming.h` | Shared helpers: beat lookup, cue lookup, repeatable noise |
| `Game/Source/CoreGame/CustomTrackDefineTest.cpp` | `ReadMidiVenue`: VENUE / MV VENUE / EVENTS / PART tracks → `VenueData` |
| `Game/Source/CoreGame/TrackList.h/.cpp` | `VenueData` and its `"Venue"` block in `NoteData.txt` |
| `Assets/Textures/Venue/StageProgram.rendertexture` | The LED wall's program feed (640 × 320) |
| `Assets/Textures/Venue/StageFeed.rendertexture` | The side screens' close-up feed (480 × 272) |

## What is imported

`CustomTrackDefineTest::ReadMidiVenue` reads, beyond the lighting in `Docs/Stage-Lighting.md`:

| Track | Source | Kept as (`VenueData`) |
|-------|--------|------------------------|
| VENUE | RB2 camera notes: 60 cut, with 61 no close, 62 only close, 63 only far, 64 no behind, 70-73 focus bass / drums / guitar / vocals struck at the same tick | `m_cameras`: `"auto <constraints>"` |
| VENUE | `[do_directed_cut x]`, RB3 `[coop_x]` / `[directed_x]` | `m_cameras`: the shot name |
| VENUE | RB2 post notes 96-110 (ProFilm_a, ProFilm_b, video_a, film_16mm, shitty_tv, bloom, film_sepia_ink, film_silvertone, film_b+w, video_bw, contrast_a, photocopy, film_blue_filter, desat_blue, video_trails), RB3 `[x.pp]` | `m_postFx` |
| VENUE | Notes 85 / 86 / 87 held | `m_singalong`: bass / drums / guitar sing along |
| MV VENUE | The same cuts and looks | `m_mvCameras`, `m_mvPostFx` (the music video) |
| PART DRUMS / GUITAR / BASS / VOCALS / KEYS | `[idle]`, `[play]`, `[mellow]`, `[intense]`, `[idle_*]`, `[play_*]` | `m_bandStates[member]` |
| PART DRUMS | Animation notes 24-51 (kick, snare, hi-hat, toms, crashes, ride by hand, hard or soft) | `m_drumHits`: time, limb, piece, soft |
| PART GUITAR / BASS / KEYS | Expert gems 96-100 (a chord strums once) | `m_guitarStrums`, `m_bassStrums`, `m_keysStrums` |
| PART GUITAR / BASS | Fret-hand positions 40-59 (0 at the nut) | `m_guitarFrets`, `m_bassFrets` |
| PART VOCALS | Sung notes 36-84 | `m_vocalNotes` |
| EVENTS | `[music_start]`, `[music_end]`, `[end]`, `[coda]` | `m_songEvents` |

RB2 notes 96 / 97 used to be read as pyro; they are post-processing. Pyro comes only from `[bonusfx]` / `[bonusfx_optional]`. Re-run the converter (`--convert-dlc`, or Convert DLC in settings) to add the new data to existing charts.

## How It Works

### The set and the rooms

`VenueShow::BuildStage` builds the stage, the same in every room: a 1.2 m deck, a drum riser, a back wall with the LED wall, speaker stacks, truss towers and an overhead truss (where the washes hang), a barricade, a front-edge LED strip that glows with the washes and chases on the beat, and four pyro emitters whose flame columns and point lights fire on the chart's bonus effects. Screens are planes whose emissive slot is a render texture, flipped upright with Tiling (1, -1) and Offset (0, 1).

The room around it is a `VenueShow::Style`:

| Style | Room | Crowd |
|-------|------|-------|
| Arena | A big dark hall, walls far off in the haze, exit signs, screens either side of the stage | 520 |
| Club | Brick walls close in, a low ceiling, neon tubes on the walls, a bar at the back; thicker haze | 240 |
| Festival | Open air at night (the main camera's procedural sky at 22:00, a full moon), a canopy over the stage, screens on towers, delay towers and a mixing tent in the field; thinner haze | 800 |

**Room** in settings picks one (or Random: one per song, repeatable by title). **F7** during a song tears the venue down and builds the next room in its place (`VenueShow::NextStyle`); the highway on top carries on, which is the point of the layering. The director keeps wide shots inside the room (`Director::SetRoomBack`).

### The band

`Band` places each member at `VenueLayout::kMemberSpots`, facing the crowd. Keys only appear when the chart has a keys part.

- **Drummer.** The stick tips follow per-limb stroke lists: the chart's animation notes when it has them (feet from its kick and hi-hat pedal gems), else `Band::DeriveStrokes` assigns its gems to limbs (notes struck together go left-most piece to the left hand; cymbals and the floor tom to the right hand, the snare to the left, alternating in fast runs and tom fills). `Band::StickTip` arcs each tip from stroke to stroke, as high as the gap allows, and lands it on the piece at the note's time; the hand sits a stick's length behind the tip and the arm reaches for it (IK). Struck cymbals rock, drums squash. Feet press the pedals on kick and hi-hat-pedal notes.
- **Guitarist and bassist.** The guitar hangs off the torso; the strumming hand moves down on even strums and up on odd ones; the fretting hand follows the chart's hand-position notes (else moves every few strums). States: `idle` (hands still, looking around), `play` (bobbing), `mellow` (swaying), `intense` (headbanging, wide stance), `play_solo` (stepping out, leaning back, neck up, a follow spot on them). During a singalong they lean into their mic.
- **Singer.** A hand on the mic and the mouth opening through each sung note; between lines they wander the front of the stage, clap over their head, or jump and fist-pump when it's intense.
- **The end.** After `[music_end]` / `[end]` everyone but the drummer throws their arms up and bounces, and the crowd roars.
- **Fallbacks.** States from section names (choruses intense, intros mellow, solos to the guitarist); strums on the half beat (guitar) and beat (bass) wherever the drums play; the singer sings three beats of four through verses and choruses.

### The crowd

`Crowd` fills the floor with the room's crowd of five-piece figures (`--crowd-size N`), keener toward the front, each with its own lag behind the beat, enthusiasm and habit (jumper, pumper, swayer, clapper). The mood comes from `[crowd_x]` (or the sections): standing about, bobbing and fist pumps (`normal`), jumping with their hands up (`intense`), swaying with lighters and phones up (`mellow`). `[crowd_clap]` has them clap on the beat. `realtime` follows the player: the core's streak (`NoteHighwayCore` → `VenueShow::SetPerformance`) gets them going; misses take the wind out of them; every fifty in a row and the chart's pyro get a cheer. Their energy also drives the light rig's crowd blinders. Phone-holders film the intense parts with their phones up, now and then flashing a photo. On the chart's `crowdsurf` / `stagedive` shots (and every so often when it's intense) a crowd surfer is carried over their heads to the barricade by the hands under them.

### The cameras

`Director` holds the cut list (VENUE's, or MV VENUE's when **Venue Camera** is Music video and the chart has one) and frames the latest cut each frame:

- `coop_<who>_<framing>`: `who` is `all`, `front` or member letters (`d`, `g`, `b`, `v`, `k`, pairs like `gv`); framing `far`, `near`, `behind`, `closeup_head`, `closeup_hand`.
- `directed_<who>[_<style>]`: `cls` a hand close-up, `kd` the kick drum, `np` / `pnt` a head close-up, `lt` from behind, `cam` handheld; `all`, `crowd`, `stagedive`, `crowdsurf`, `bre` / `brej` (the big rock ending, from high up), `duo_x`.
- RB2's `auto` cuts: a shot that fits the constraints, chosen repeatably from the cut's index; focused members are its subjects.
- No cuts: one every two measures (`Director::BuildFallbackCuts`), wide at each new section, else on the busiest member (`Band::Activity`).

The follow spots track their member's chest every frame, so a soloist stepping out front stays lit.

Shots track the members' live positions, drift (a slow orbit and push-in) while held, and shake when handheld. Post-processing looks map to the camera's grading (`Director::GradeFor`): saturation, contrast, temperature and tint, bloom, vignette, and the engine's era colour depth and dither for the TV and photocopy looks; they ease in over a few frames.

Two render-texture cameras feed the screens, each every other frame:

- The **program feed** (`StageProgram.rendertexture`, the LED wall) films exactly what the main camera shows, graded the same, as if the show were being broadcast live. In its own shot the wall is black (a camera never samples its own image), so in a wide shot the wall shows the show one level deep.
- The **close-up feed** (`StageFeed.rendertexture`, the side screens): the main shot's member, else whoever is busiest (the singer favoured), re-chosen every two measures from a pit position, slightly handheld.

## Settings and flags

- **Venue** (`Venue` in `Settings.json`): Band and crowd (2) / Band only (1) / Off (0: the highway on black, no light show — the rig lives in the venue).
- **Room** (`VenueStyle`): Arena (0) / Club (1) / Festival (2) / Random (3). F7 swaps it mid-song.
- **Venue Camera** (`VenueCamera`): Live show (0) / Music video (1).
- `--no-venue` skips the venue; `--venue-only` fades the highway out entirely to frame the venue; `--venue-shot <name>` holds one shot (any cut name, or `debug_wall`); `--venue-look <name>` holds one post look; `--venue-time <seconds>` shows the venue that far into the song; `--venue-style N`; `--venue-swap-every <seconds>` swaps the room on a timer like F7; `--crowd-size N`; `--band-debug` logs the drummer's stick tips and hands twice a second. The engine's `--screenshot-every N` saves a numbered frame every N frames, to check motion headless.

```bash
# Frame a shot of Boston (track 2) a minute in, without the highway.
./Engine/Tools/NixEnv.sh env -u NIX_CC ./Engine/Tools/Headless.sh ./.build/Game_linux_Debug/Game_EntryPoint_x64 \
  --scene Assets/Example.lvl --play-track 2 --frames 150 --frame-time 0.016666667 --no-audio \
  --venue-only --venue-time 60 --venue-shot coop_g_near --screenshot shot.png --exit
```

## Caveats & Fragility

- **The venue and highway share a world.** Separation is by distance only: anything placed near `VenueLayout::kVenueOrigin` shows in the venue, and directional lights (the rig's dim key light) light both.
- **The highway's coverage is its depth.** Transparent highway pieces that don't write depth add over the venue rather than covering it.
- **RB2 camera note meanings** (61-64, 70-73) and the spotlight slot order (37 keys, 38 vocals, 39 guitar, 40 drums, 41 bass) follow community documentation, not an official spec; a wrong guess frames the wrong member, nothing worse.
- **Cost.** Five entities per crowd member (4,000 for the festival's), posed on the main thread: the front rows every frame, the middle every second frame and the back every third, in turns. Instancing keeps the draws to a few dozen batches. The engine's spheres and capsules are about 2,300 triangles each, so crowd arms are boxes and only the first rows get round heads (`Puppet::Look::Blocky`): a typical frame is 150-200k triangles across the three cameras, about 1.3M at the peak. `--crowd-size` or Venue: Band only trims it.
- The feed camera can't show its own screen: in its shot the LED wall is black (`Engine/Docs/Rendering-Pipeline.md` → Render textures).

## Related Docs

- `Docs/Stage-Lighting.md`: the light rig and its cues
- `Docs/Gameplay-Note-Highway.md`: the highway drawn over the venue
- `Docs/Songs-and-DLC.md`: the converter that writes `NoteData.txt`
- `Engine/Docs/Rendering-Pipeline.md`: overlay cameras and render textures
