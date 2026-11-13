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

- **Beams**: 8 moving heads standing on the stage deck, rows 0-1 along its front edge throwing up
  and back over the band, rows 2-3 along the back throwing up and out over the crowd (the
  silhouette lights); narrow spots that pan and tilt.
- **Movers**: 16 moving heads hung under the three cross trusses (`StageLights::MoverLook`). The
  front truss's four light the band from the front or turn out and sweep the crowd, the middle's
  four drop columns around the band, the back truss's eight fan forward over the band's heads into
  the audience. Each cue gives them a move of their own (a fan, a wave along the truss, crossing
  sides, a ballyhoo, a pan together). They swing to a new aim on motors rather than jumping. Through
  a solo the front truss swings onto the soloist (`SetSoloist`).
- **Washes**: 6 spots on the overhead truss, pooling colour on the band, with lenses.
- **Side light**: 2 wide cans on each wing, cross-lighting the band in the colour the washes
  aren't (cool under a warm look, warm under a cool one), so faces keep a lit edge.
- **Spotlights**: 5 narrow white follow spots from the front-of-house truss, one per member (VENUE
  slots 37-41: keys, vocals, guitar, drums, bass). `VenueShow` holds each at a low floor as front
  light on the band in every look (mostly gone in a blackout), and higher on a soloist.
- **Crowd blinders**: 4 eight-lamp blinders on the front truss aimed at the audience: a low warm
  glow that swells with the crowd's energy, and a white hit on pyro and on big moments (`Accent`).
- **Strobe bars**: 6 lamp faces under the middle and back trusses (no light of their own): they
  flash with the strobe cues and stutter on an accent.
- **Lasers**: 3 projectors on the back truss, each a fan of 7 rays thrown high over the crowd to
  the back of the room. They are thin emissive bars, not lights, scaled to nothing when off. On
  for `frenzy`, `bre`, `searchlights`, `sweep` and `dischord`, and whenever the show's hype is
  above 0.72 (`UpdateLasers`).
- A dim Manual directional key light. Without any directional the renderer supplies a daylight
  sun, which the haze would scatter into a grey veil; this one also lights the highway's notes.
- The venue camera's fog turns volumetric while a show runs, with the engine's
  `VolumetricLightSamples` at 8 (`kHazeLightSamples`): each fixture is integrated along the part
  of a view ray inside its own beam instead of at every step of the fog's march
  (`Engine/Docs/Rendering-Pipeline.md` → Fog). `StageLights::Clear` puts the camera's fog back.

A moving head is a base on its mount, a yoke that pans and a head that tilts
(`SpawnMovingHead`): the head is the light's own entity, with its body and lens as children, so
the fixture visibly points where its beam goes.

**Colours.** Rock Band's cues say cool or warm, not which blue or red. Each song takes one of
five palettes by its title (three cool, three warm, two clashing: classic, neon, ice and fire,
emerald, synthwave); `--stage-palette N` picks one.

**Levels.** A beam's level falls as its colour pales (white is three colours' worth of light and
whites out the haze), and heads pointed down at the deck run at 60%. The intensities were
balanced by eye against 43 spot lights in haze: raising one group usually means lowering another.

The front and rear wash rows cast shadows (four spots, matching the renderer's local spotlight
shadow budget). The directional key also casts shadows. The house light used with stage lighting
off does not: every room has a roof or a canopy, and a shadowed house light left the band in the
dark. Solid venue pieces, crowd parts and animated performers cast shadows; fixture housings/lenses
and pyro flames do not. The main venue camera enables ambient occlusion for contact shading; screen
feeds retain their cheaper settings.

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

The show's hype (`Docs/Venue-and-Band.md` → Hype and effects) runs the rig a little hotter and
its heads faster, brings the lasers out at its peak, and hits the blinders, strobes and moving
heads white on each big moment. The flame pots turn the washes and side light orange while they
burn (`SetBurn`).

## Settings and flags

- **Stage Lights** (settings page, `StageLighting` in `Settings.json`): Full show / No strobes or
  flashes (strobes hold steady, flares and pyro soften) / Off (no rig). The rig lives in the venue,
  so **Venue: Off** turns it off too.
- `--stage-cue <name>` holds one look for a whole song, to tune it (`default` for the empty cue).
- `--stage-lights N` overrides the setting for a run (0 off, 1 no strobes or flashes, 2 full).
- `--stage-palette N` picks the song's colours (0-4).
- `--haze-light-samples N` sets the haze's samples per fixture for a run (default 8, up to 32).
  0 is the old path, every march step lit from its cluster: the reference picture, at about 17
  times the cost.

## Gotchas

- **Volumetric fog must be allowed.** An enforced hardware profile without it (the built-in
  "2004 PC") leaves only analytic fog: no beams, just lenses and floor pools.
- The haze is half resolution, so a beam narrower than a couple of its pixels still softens. The
  per-fixture samples do land inside it however thin it is; the old march (`--haze-light-samples
  0`) took metre-long steps far from the camera, where cones under about 4° barely registered.
- **Beams far from the camera are slightly fuller than under the old march.** The per-fixture
  picture is the one the march converges to with more steps: a 256-step march matches it, while at
  64 steps a beam seen from the mixing desk came out a few percent dimmer and lopsided across its
  width (peak 151 against 158 of 255 on screen), where its steps were longest. Close and mid shots
  differ by less than that. The levels above were balanced against the old picture; if the long
  shots now read hot, `kHazeScatter` is the one knob.
- The haze is the venue camera's; the highway is drawn over it and stays clear.
- **A beam through the lens whites the picture out.** In-scattering is strongest looking down a
  beam, so a head aimed level down the room saturates any camera flying over the crowd. The
  `frenzy` look keeps its heads at least 32 degrees down for that reason, and the lasers are
  thrown above the cameras.
- **Cost.** The rig is 43 spot lights (46 local lights with the venue's own). Measured in
  RenderDoc on an RTX 4090 at 5120 x 1440 (the crowd shot, `concert_bw`; RenderDoc serialises the
  frame, so read the ratios), the haze's scatter pass was 24.1 ms of a 38 ms frame while every one
  of the march's 64 steps lit itself from its cluster: a step visited 45.8 lights on average and
  4.2 of them reached it. With the per-fixture samples it is 1.4 ms (4 samples 1.2 ms, 16 samples
  2.0 ms); the directional key and ambient haze, still marched at 64 steps, are 0.4 ms of that.
  The cost now grows with the lights in the rig (one cone test each per haze pixel) and the beams
  a ray crosses, not with steps x lights. Shadowed fixtures take one shadow tap a sample in the
  haze (surfaces still take nine).
