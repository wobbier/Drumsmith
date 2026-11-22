# StoryRollerRink: set 06 "Adults Only at the Roller Rink"

The Moonbeam Rollerdrome on adults' night:
- **The floor:** an oval of maple boards with a painted orange and yellow lane line and a pink and cyan centre circle.
- **The rail:** a carpeted knee wall with a walnut cap and a chrome hand rail, with cosmic arcade carpet outside it.
- **Neon:** stripes and tubes along the walls and round the rail.
- **The DJ booth (far end):** a deck 0.6 m high with a glitter front. The drummer sits on a riser behind the DJ counter and its turntables, with guitar on the left and bass on the right. Above them is a truss with lamps, and the "Moonbeam ROLLERDROME" sign is on the wall behind.
- **Skate rental (left wall):** a counter, a cubby wall full of skates, arcade cabinets and lacing benches.
- **Snack bar (right wall):** a counter and menu board, the nacho warmer, popcorn, slush and soda machines, a vending machine, stools and tables.
- **The mirror ball:** hangs over the centre of the floor.

## Files

- `Tools/Venues/make_story_roller_rink.py` is the generator. It is deterministic, and it redraws the textures when ImageMagick is available.
- `Tools/Venues/story_roller_rink_meshes.py` writes the OBJ meshes. Colours come from one small swatch texture, and glowing parts are set in the material file.
- `Tools/Venues/story_roller_rink_textures.py` draws the textures: Palette, Maple, Carpet, Glitter, the signs, the three boards, the menu and the posters. Redrawing one deletes its stale `.dds` twin.
- `Tools/Venues/story_roller_rink_skaters.py` builds the skaters from crowd figure pieces, makes the skates, and dresses the three featured skaters. It also writes the clips for laps, the wobble at the rail, hands up and the ball's spin.
- `Assets/Venues/StoryRollerRink/` holds `venue.json` (ambience `Assets/Sounds/crowd.mp3`), `StoryRollerRink.lvl`, `Models/` (with a `README.md` giving where each model came from: Synty Office FBX copies and the cast's piece copies, all under the owner's Synty licence) and `Motion/*.sequence`.
- `Art/Venues/StoryRollerRink/` holds `Previews/`, `cap.sh` (the capture helper) and `Scratch/` (logs).

## What each flag does

| Flag (song) | Visible change |
|---|---|
| Before any flag | The last orange rental pair sits on the rental counter under an amber lamp. The two silver jackets lap the outer lane side by side, under a cool light and a silver floor pool that travel with them. The board reads ALL SKATE. The mirror ball hangs still. |
| `newcomer_at_rail` (1) | The orange pair leaves the counter. The learner, in orange rentals, appears at the rail on the upper left, arms out and wobbling. |
| `rail_lit` (2) | A second pool of light lands on that stretch of rail: a lamp in the roof with a glowing lens, a real spot light (700), a big tangerine pool on the floor, and the rail's neon there turns orange. It stays lit after the rail empties. |
| `rail_empty` (3) | The learner leaves the rail and laps the inside lane with a warm pool following. The still ball is replaced by a turning one, with 8 spot lights and about 240 floor and ceiling glints turning with it. |
| `three_abreast` (4) | The silver pair is replaced by one line of three (jacket, learner, jacket) on the outer lane, with three pairs of regulars falling in behind on the same lap. The board changes to TRIO SKATE. |
| `circle_open` (5) | The laps stop. Under the ball: a glowing yellow ring, a white pool and a downlight. The learner stands in the middle with both silver jackets beside him, bouncing with hands in the air, and a ring of 10 regulars around them. The board changes to HANDS UP! On peaks, glitter bursts from the ball. |

## Band, crowd, cameras, lights

- **Band spots:** Drummer, Guitar and Bass, matching OnStage. There is no vocals spot.
- **Crowd:** 7 areas, 89 heads in all.
  - A posed knot of people at the foot of the booth.
  - Skaters standing on the floor at the far side, both ends and the near side. The skaters' lanes and the centre circle are kept clear for the story.
  - Watchers at the rail by the snack bar and behind the near rail.
- **Cameras:**
  - Wide `wide`, Crane `crane`, Desk `desk`, Close `drummer`.
  - Custom shots: `rail`, `circle`, `ball`, `snack-bar`, `over-the-counter`.
  - An intro walk-in, `arrival/01..05`, past the rental counter to the rail and the booth.
- **Lights:**
  - One shadow-casting directional key.
  - 24 show lights: 6 Wash, 10 Beam (narrow spots round the ball that sway across the floor), 3 follow Spots, 2 Blinder, 2 Strobe, and the Static key.
  - Plain lights that the show doesn't control: house lights, front fill, the counters, neon spill.
  - Plain lights inside story groups: the rail spot, the 8 turning ball spots, the circle downlight, and the lights that ride with the skaters.

## What I couldn't do and why

- **Skaters don't stride.** They are rigid crowd pieces: the body sways, the arms swing and the torso leans, but each pair of legs is one mesh.
- **The turning ball's spots aren't cued by the show.** They are plain lights inside a story group, because show lights can't be put in one. The swaying Beam lights give the cued movement.
- **The standing crowd can't make way for the circle.** Crowd areas can't be gated, so the centre is simply kept clear and the circle is its own ring of figures.
- **Retail won't show the textures and models yet.** The game cooked some texture twins during the captures, but nothing was cooked on purpose: the brief said not to build or run the tools. A cook pass is needed before Retail.
- **Some previews are weaker than I'd like.** The capture cap meant `rail_song2.png` still shows the old `rail` camera (crowd in the way; the camera was moved after). The song-title card covers the top of every preview.

## NEEDS.md

Nothing.
