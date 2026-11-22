# StoryDriveIn: Midnight at the FM Drive In (set 09, `s09-drive-in`)

## Files

- `Tools/Venues/make_story_drive_in.py`: the generator (deterministic). Run it with `--textures` to also redraw the pictures.
- `Tools/Venues/story_drive_in_meshes.py`: the OBJ prop shop, all on one palette texture. It writes:
  - cars in 5 shapes (hatch, sedan, wagon, pickup, van) and 13 paints, plus the backed-in hatchback with its tailgate up;
  - speaker posts, the 15 m FM mast, the screen lattice, light towers, the lot fence, the projector and a thermos;
  - a unit light-shaft frustum for the beams.
- `Tools/Venues/story_drive_in_textures.py`: ImageMagick drawings (palette, the 88.9 FM station card, marquee, quilt, gravel, cinder block). It deletes stale `.dds` twins when it redraws.
- `Assets/Venues/StoryDriveIn/`:
  - `venue.json` and `StoryDriveIn.lvl`; ambience is `Assets/Sounds/crowd.mp3`;
  - `Models/`: the generated OBJs, `Palette.mtl` and a provenance `README.md`. No Synty files are copied; Synty-derived models are referenced in place, read-only;
  - `Textures/`: the drawn pictures;
  - `Motion/`: the Bounce, ShadowBob, ShadowCross, Pump and Stroke sequences.
- `Art/Venues/StoryDriveIn/`: `cap.sh` and `batch.sh` (captures through the lock), `Previews/`, `Scratch/` (logs).

## The place

- **The lot.** Gravel terraces step down toward a 46 x 19.6 m screen: a Stage-feed `VenueScreen` with black masking, standing on a steel lattice.
- **The deck and booth.** The band plays on a plywood deck built against the cinder-block projection booth in the middle of the lot.
  - Behind the drummer are the booth's lit window and a propped-open door.
  - The "FM Drive In" marquee sits on the parapet.
  - A red-and-white FM mast with a beacon stands on the roof.
  - An additive projector beam runs from the rear ports to the screen.
- **The cars.** About 63 parked cars in seven rows all face the screen: four rows on the rising terraces behind the crowd, three in the low field in front of the screen. Speaker posts stand between them.
- **The festival end.** The artist's bus, a broadcast truck with a dish, food stalls, flags, six light towers and festoons.
- **Beyond the lot.** Lot lamps, the fence, a treeline, hills and a far town's lights.
- **Sky and light.** Outdoor night sky at 23.6 h. The moon (the one shadowed light) comes from over the screen.

## Band spots (OnStage: drums, guest-electronics)

- **Drummer** at (0.8, 1.0, 3.3) on the deck, with hybrid-kit dressing:
  - a sample pad on a stand with lit pads;
  - a laptop on a flight case;
  - cables and a power distro on a rug;
  - the kit-cam tripod with a red tally light (the camera whose feed ends up on the screen).
- **Keys** (the festival's electronic artist) at (-4.0, 1.0, 2.2), with a gear table of drum machines with lit steps and a synth rack with LEDs.
- No other spots.

## Story flags

| Flag | Change |
|------|--------|
| `headlights_on` | Every car's headlamps, tail lamps and a dipped additive beam pair come on together, with about 30 real spot lights throwing onto the gravel. The backed-in hatchback's lamps face the crowd and the wide. Before the cue, the lot is dark. |
| `quilt_at_hatch` | Two people sit on the lip of the backed-in teal hatchback, with the tailgate up and a patchwork quilt round their shoulders and over the lip. The next-door rust pickup's cargo lamp comes on (an emissive lamp and a point light), a thermos gleams between the two, and a camp chair appears. A nested `quilt_on_roof` (WhenSet false) group takes the pair and the quilt away later. |
| `quilt_on_roof` | The quilt lies over the hatchback's roof and hangs down both sides. The pair stand and bounce in the gravel beside the car, pumping their arms. Their two giant shadows bounce back and forth across the bottom of the screen (24 s each way). |
| `shadows_on_screen` | 14 dancers with raised arms appear in the front field, in the projector beam. Ten giant raised-arm silhouettes bob along the lower screen. |
| `hands_on_screen` | The 88.9 FM station card in front of the screen shrinks away, revealing the live kit feed. Two forty-foot drumstick silhouettes with fists cross over the feed in an X, stroking on the beat. The beam and the screen's spill on the lot change from the card's blue to warm white. |

## Cameras

| Camera | Shot |
|--------|------|
| `top-of-the-hill` | Wide |
| `over-the-roofs` | Crane |
| `back-terrace-long-lens` | Desk |
| `kit-and-pads` | Close |
| `quilt-in-the-hatch` | Custom |
| `quilt-on-the-roof` | Custom |
| `hillside-of-headlights` | Custom |
| `shadows-on-the-screen` | Custom |
| `down-the-beam` | Custom |
| `the-booth-from-the-flat` | Custom |
| `arrival/01` to `arrival/06` | The walk in from the back corner of the lot |

## Lights

- **36 `VenueShowLight`s:**
  - 3 Spot: two long-throw follows from the back terrace and a key on the kit;
  - 8 Wash: along the booth roof;
  - 14 Beam: 8 sweeping from the booth roof, 6 from the towers;
  - 6 Strobe;
  - 4 Blinder.
- **1 shadowed light:** the directional moon.
- **About 46 plain lights:** headlights, the booth, the marquee, the mast beacon, lot lamps, screen spill and story lamps.
- No show light sits under a story group.

## Crowd

- A posed dance floor in front of the deck: 64 heads.
- Mobs:
  - on the flat either side of the booth;
  - in each row's drive lane and centre aisle;
  - in the two front lanes;
  - under the screen.
- Two heads each on the roofs of seven wagons and vans.

## Previews (960x540)

- `wide_song1_start.png`
- `wide_song3.png`
- `wide_song5_end.png`
- `drummer.png`
- `beat.png`: the kit feed with the forty-foot sticks and the shadows
- `quilt_in_the_hatch.png`: the song 2 beat, my extra preview

`wide_song1_start`, `wide_song3`, `drummer` and `quilt_in_the_hatch` were shot before the last tweak. That tweak moved the screen-spill light off the card, which had left a hotspot on it, and lifted the screen silhouettes 0.15 of their height. `wide_song5_end` and `beat` were reshot after it. The bright spot that is still at the middle of the screen is the haze glow of the screen-spill light; it reads like a projector hotspot, so I left it. `Preview.jpg` is cropped from `wide_song5_end`.

## Couldn't do / notes

- Crowd areas can't be gated, so the "people between and on cars" are fixed. The story pair and the dancers in the beam are hand-placed crowd-piece figures with my own Sequence clips.
- A `VenueScreen` can't switch feeds or be gated. The card-to-kit-feed switch is a station-card panel in front of a Stage screen, removed by a `WhenSet: false` group. For songs 1 to 4 the screen therefore shows the card, not a live feed.
- `magick` isn't on the PATH. The texture script falls back to the copy in `/nix/store`.
- A gotcha for other builders: story-group children are local to the group's pivot. The generator adds a `(venue frame)` child under each pivoted group to place props in venue space. A line in `venuegen.Scene.story`'s docstring would help.
- Faint horizontal banding shows on the Stage feed in the captures. It looks like the feed's own scan or haze, not the scene.
- Nothing for `NEEDS.md`.
