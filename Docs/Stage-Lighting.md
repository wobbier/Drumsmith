# Stage Lighting

The light show beside the note highway. Rock Band charts carry a VENUE track of lighting cues
next to their notes; the converter keeps them, and `StageLights` plays them on the song clock with
real spot lights in volumetric haze.

## Files

| File | Role |
|------|------|
| `Game/Source/CoreGame/CustomTrackDefineTest.cpp` | `ReadMidiVenue`: VENUE / EVENTS tracks → `VenueData` |
| `Game/Source/CoreGame/TrackList.h/.cpp` | `VenueData`, saved as `"Venue"` in `NoteData.txt` |
| `Game/Source/CoreGame/StageLights.h/.cpp` | The rig, the cue looks, the fallback show, hit pulses, the haze |
| `Game/Source/Cores/NoteHighwayCore.cpp` | Builds the rig in `SetupTrack`, updates it with `VisualTimeMs`, feeds hits and misses |

## What is imported

From the **VENUE** track (`MV VENUE`, camera cuts and post-processing are skipped):

| Source | Kept as |
|--------|---------|
| `[lighting (name)]`, RB2 `[verse]` / `[chorus]` | `Lighting`: `[time, name]` (empty name = default look) |
| Notes 48 / 49 / 50, or `[next]` / `[prev]` / `[first]` | `Keyframes`: `[time, 0 next / 1 previous / 2 first]` |
| `[FogOn]` / `[FogOff]` | `Fog`: `[time, 1/0]` |
| `[bonusfx]`, notes 96 / 97 | `BonusFx`: times (pyro) |
| Notes 37–41 held | `Spotlights`: `[start, end, slot 0–4]` |

From the **EVENTS** track: `[section x]` / `[prc_x]` → `Sections`, `[crowd_x]` → `Crowd`.

Re-run the converter (`--convert-dlc`, or Convert DLC in settings) to add this to existing charts.

## The rig

Built under `TrackMover`, so it rides with the camera like the highway:

- **Beams**: 8 floor cans, 4 per side at x ±6.6, with visible lenses; narrow spots that pan and tilt.
- **Washes**: 6 spots overhead, pooling colour on the floor beside the highway (never on it).
- **Spotlights**: 5 white pools, one per VENUE spotlight slot.
- A dark stage floor, and a dim Manual directional key light. Without any directional the renderer
  supplies a daylight sun, which the haze would scatter into a grey veil over everything.
- The camera's fog turns volumetric while a show runs (restored on `Clear`).

## Cues

Each Rock Band cue is a look (`StageLights::LookFor`), in the spirit of its name: `manual_cool` /
`manual_warm` / `verse` / `chorus` (palette stepped by keyframes), `dischord`, `stomp` (on/off per
keyframe), `loop_cool` / `loop_warm` (a chase a row per beat), `harmony` (crossing warm and cool),
`frenzy` / `bre`, `silhouettes` / `silhouettes_spot` (backlight only), `searchlights`, `sweep`,
`strobe_slow` / `strobe_fast`, `blackout_slow` / `blackout_fast` / `blackout_spot`, `flare_slow` /
`flare_fast` (a white flash fading back to the previous look). Unknown cues get a warm default.

Charts **without VENUE lighting** get a show built from their sections (intro → manual_cool, verse →
loop_cool, chorus → loop_warm, solo → searchlights …) or, without sections, alternating looks every
eight measures, with a keyframe every two beats.

On top of the cue, the player's judged hits pulse the rig: kick swells the washes, snare and toms
punch the beams (high tom left, floor tom right), cymbals flash them white, and a miss dims it for
a moment. Crowd state scales the overall level.

## Settings and flags

- **Stage Lights** (settings page, `StageLighting` in `Settings.json`): Full show / No strobes or
  flashes (strobes hold steady, flares and pyro soften) / Off (no rig, the camera's fog untouched).
- `--stage-cue <name>` holds one look for a whole song, to tune it (`default` for the empty cue).

## Gotchas

- **Volumetric fog must be allowed.** An enforced hardware profile without it (the built-in
  "2004 PC") leaves only analytic fog: no beams, just lenses and floor pools.
- Narrow cones under about 4° barely register in the half-resolution raymarch.
- The haze also dims the highway; density and start distance (`kHaze*`) trade beams against note
  readability.
