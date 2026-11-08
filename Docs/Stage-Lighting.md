# Stage Lighting

The light show on the venue's stage (`Docs/Venue-and-Band.md`). Rock Band charts carry a VENUE
track of lighting cues next to their notes; the converter keeps them, and `StageLights` plays them
on the song clock with real spot lights in volumetric haze.

## Files

| File | Role |
|------|------|
| `Game/Source/CoreGame/CustomTrackDefineTest.cpp` | `ReadMidiVenue`: VENUE / EVENTS tracks → `VenueData` |
| `Game/Source/CoreGame/TrackList.h/.cpp` | `VenueData`, saved as `"Venue"` in `NoteData.txt` |
| `Game/Source/CoreGame/StageLights.h/.cpp` | The rig, the cue looks, the fallback show, hit pulses, the haze |
| `Game/Source/Venue/VenueShow.cpp` | Builds the rig in the venue, updates it with the song clock, feeds hits, misses, crowd energy and the follow spots' floor |

## What is imported

From the **VENUE** track (camera cuts, post-processing and singalongs: `Docs/Venue-and-Band.md`):

| Source | Kept as |
|--------|---------|
| `[lighting (name)]`, RB2 `[verse]` / `[chorus]` | `Lighting`: `[time, name]` (empty name = default look) |
| Notes 48 / 49 / 50, or `[next]` / `[prev]` / `[first]` | `Keyframes`: `[time, 0 next / 1 previous / 2 first]` |
| `[FogOn]` / `[FogOff]` | `Fog`: `[time, 1/0]` |
| `[bonusfx]`, `[bonusfx_optional]` | `BonusFx`: times (pyro) |
| Notes 37–41 held | `Spotlights`: `[start, end, slot 0–4]` (keys, vocals, guitar, drums, bass) |

From the **EVENTS** track: `[section x]` / `[prc_x]` → `Sections`, `[crowd_x]` → `Crowd`.

Re-run the converter (`--convert-dlc`, or Convert DLC in settings) to add this to existing charts.

## The rig

Built in venue space under the venue's root (`Game/Source/Venue/VenueLayout.h`):

- **Beams**: 8 floor cans with visible lenses on the stage deck, rows 0-1 along its front edge
  throwing up and back over the band, rows 2-3 along the back throwing up and out over the crowd
  (the silhouette lights); narrow spots that pan and tilt.
- **Washes**: 6 spots on the overhead truss, pooling colour on the band, with lenses.
- **Spotlights**: 5 narrow white follow spots from the front-of-house truss, one per member (VENUE
  slots 37-41: keys, vocals, guitar, drums, bass). `VenueShow` holds each at a low floor as front
  light on the band in every look (mostly gone in a blackout), and full on a soloist.
- **Crowd blinders**: 4 wide lights on the front truss aimed at the audience: a low warm glow that
  swells with the crowd's energy, flashes on flares and strobes, and pyro.
- A dim Manual directional key light. Without any directional the renderer supplies a daylight
  sun, which the haze would scatter into a grey veil; this one also lights the highway's notes.
- The venue camera's fog turns volumetric while a show runs.

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
  flashes (strobes hold steady, flares and pyro soften) / Off (no rig). The rig lives in the venue,
  so **Venue: Off** turns it off too.
- `--stage-cue <name>` holds one look for a whole song, to tune it (`default` for the empty cue).
- `--stage-lights N` overrides the setting for a run (0 off, 1 no strobes or flashes, 2 full).

## Gotchas

- **Volumetric fog must be allowed.** An enforced hardware profile without it (the built-in
  "2004 PC") leaves only analytic fog: no beams, just lenses and floor pools.
- Narrow cones under about 4° barely register in the half-resolution raymarch.
- The haze is the venue camera's; the highway is drawn over it and stays clear.
