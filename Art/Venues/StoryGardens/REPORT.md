# StoryGardens: "Home Ice at Maple Leaf Gardens" (s11-gardens)

To rebuild, run `python3 Tools/Venues/make_story_gardens.py`. Add `--textures` to redraw the pictures; that needs ImageMagick 7, which the script finds on PATH or in /nix/store. The output is deterministic. `check_venue.py` passes.

## Files
- `Tools/Venues/make_story_gardens.py`: the generator. It builds the bowl, rink, riser, people, story groups, lights and markers, and writes the two motion clips.
- `Tools/Venues/story_gardens_textures.py`: draws the textures:
  - the ice markings
  - the rink-board ads, for made-up local businesses
  - the scoreboard faces
  - the generic rafter banners
  - the Canadian flag
  - the "MAPLE LEAF GARDENS" balcony fascia
  - the furled canvas
  - the YOUR BAND banner

  The pictures are stored flipped vertically, because the cube primitive samples them upside down. When a picture is redrawn, the script deletes its stale `.png.dds` / `.dds.d` twins.
- `Assets/Venues/StoryGardens/` contains:
  - `venue.json`
  - `StoryGardens.lvl`
  - `Textures/*.png`
  - `Motion/KidBounce.sequence` and `Motion/BoardWave.sequence`

  Ambience is `Assets/Sounds/crowd.mp3`.
- There are no copied Synty FBXs, so there is no Models/README. The props are primitives, the shared `Assets/Models/Venue/*` models and the crowd pieces in `Assets/Models/People/Crowd/`, all referenced in place.
- `Art/Venues/StoryGardens/scratch/gcap*.sh`: the capture scripts (`gcap2.sh` kills the game once the PNG lands).

## The place
- **Rink.** 52 x 23 m with chamfered corners and painted ice. The boards are white with a yellow kickplate, a red cap rail and ads, and the glass is seamed.
- **Riser and floor.** The riser is at centre ice, ringed by a run of rink boards and glass. The players' benches are on the far side, the goals and nets are at both ends, and FOH is at the back of the floor.
- **The bowl.** It is steep: eight two-row steps coloured in tiers, reds by the glass, then golds, blues and greens. It has row lips, aisles and vomitories. Above that are a concourse, an oxblood fascia reading MAPLE LEAF GARDENS, and six steps of greys under a stepped roof.
- **Rafters.** Steel trusses with warm hanging house lamps and five follow-spot gondolas. Six generic banners (MAPLE LEAF GARDENS / CARLTON STREET / HOME ICE / SOLD OUT / THE GREYS) and a Canadian flag hang from them.
- **Scoreboard.** A centre-hung lamp-board: MAPLE LEAF GARDENS, HOME 0 GUEST 0 20:00, TONIGHT ON HOME ICE / YOUR BAND.
- **Stage rig.** A black truss with line arrays hangs over the riser.
- **Crowd.** About 1,170 on the floor, 110 of them posed at the glass ring, and about 4,000 in the bowl.

## What each flag does
| Flag | Change |
|------|--------|
| `goal_lamp_on` | The west goal lamp on the end glass lights: a red dome and halo, a red point glow, and a red wash over the west end seats. A red twin lamp lights on the scoreboard skirt. A red spot from the west lands on the kid in the enormous blue-and-white sweater, who bounces on a crate at the riser glass, stage left. The kid is always there (`KidBounce`). |
| `both_ends_lit` | The east lamp answers: the same lamp, end wash and scoreboard twin. Two red beams from the end lamps cross in an X over the stage (lights plus additive shafts). The kid's sleeves go from hanging to straight up. |
| `board_wave` | The front row behind the west glass, from the near-west corner round the west end to the home bench, swaps arms-down figures for arms-up figures waving white towels. The `BoardWave` clip ripples them fan by fan, and three warm spots light the run. |
| `banner_rigged` | A furled white banner hangs on hoist ropes under a batten above centre ice, in front of the scoreboard. It has red ties and a loose YOUR BAND corner hanging down. A tight follow spot from the centre gondola lights it, with a beam shaft and a pool of light. |
| `banner_dropped` | The furl, its ropes and its spot go. The 4.6 x 7.6 m YOUR BAND banner hangs unfurled, facing the cheap seats: royal blue, a white and red leaf, silver trim. A gondola key and two washes light it, and red, white and blue streamers hang over the floor. |

Story groups pivot on the thing itself, so the lamps grow from the lamp and the banner from the batten. A `story_at` helper does this by adding a child at minus the pivot, so the props inside can be placed in venue coordinates.

## Band and cameras
- **Spots.** Drummer (kit riser, 2.42 m), Vocals, Guitar, Bass and Keys. The kit is dressed with a drum rug, road cases, a fan, tech and spare-kit cases, plus backline, wedges and side fills.
- **Cameras.**
  - Wide: from the near concourse, 74 degrees, framing both goal lamps, the stage, the banner and the rafters.
  - Crane.
  - Desk: at FOH.
  - Close: the sticks.
  - Custom: kid, goal-lamp, both-ends, wave, banner, rafters, bench.
  - arrival/01..06: a walk from the west net along the floor to the riser.

## Lights
- **Show lights (35 VenueShowLights).** 10 truss washes, 10 movers (Beam), 5 gondola follow spots (Spot), 6 blinders and 4 strobes. None of them is under a story group.
- **Shadowed light.** 1, a directional house key.
- **Plain lights.**
  - 8 warm house glows and 4 ice spills.
  - The story lights: lamp glows, end washes, the kid's spot, the cross beams, the wave spots, the banner spots.

## Previews (960x540)
- `wide_song1_start.png`
- `wide_song3.png`
- `wide_song5_end.png`
- `drummer.png`
- `beat.png`: the dropped banner, from the near concourse.
- `goal_lamp_west.png`: the extra shot, the lit west lamp over the floor.

`wide_song1_start` and `wide_song5_end` were taken one lighting pass before the final scene. Since then:
- The goal-lamp bloom is smaller.
- The cross beams cross high over the stage instead of running flat across it.
- A scoreboard glow light was removed.

`wide_song3` and `beat` show the final scene.

## What I couldn't do / caveats
- **The wave is weak in the wide.** The west front row sits under the red end wash and is small at that distance. It reads in the `wave` Custom shot, but I had no capture budget left to verify that shot.
- **The kid wasn't verified on camera.** No capture confirmed the kid in frame; in the goal-lamp shot the floor crowd blocks them.
- **Motion clips only seen as stills.** The kid's bounce and the wave ripple were never watched moving.
- **Corner seating is approximated.** Crowd rectangles are axis-aligned, so each corner step is three small squares.
- **Cameos aren't placed.** Rory, Bea, Kit, Sol, Dee and Otto at the benches and tunnel can't be gated on "member not selected" (see NEEDS.md).
