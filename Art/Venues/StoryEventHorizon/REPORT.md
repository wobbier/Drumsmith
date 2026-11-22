# StoryEventHorizon: The Drummer Hall of Fame at the Event Horizon (set 13, `s13-event-horizon`)

## Files

- `Tools/Venues/make_story_event_horizon.py`: the generator (deterministic; rerun rebuilds everything).
- `Tools/Venues/story_event_horizon_mesh.py`: a small OBJ writer + drawn swatch palette (pure Python PNG).
- `Tools/Venues/story_event_horizon_props.py`: the rotunda, rings, star field, black hole, stand, lamp,
  podium, conductor figure, plaques, kit leads.
- `Tools/Venues/story_event_horizon_textures.py`: inductee plaques and friezes, lettered with ffmpeg drawtext
  (ImageMagick is not on this machine's PATH). All names are invented.
- `Assets/Venues/StoryEventHorizon/`: `venue.json` (Ambience `Assets/Sounds/crowd.mp3`, Preview.jpg),
  `StoryEventHorizon.lvl`, `Models/` (original OBJs + `README.md` provenance), `Textures/`.
- `Art/Venues/StoryEventHorizon/cap.sh` (capture helper), `Previews/`.

## The place

A round orbital rotunda: marble floor with brass compass inlay, a round dais and drum riser, 24 columns
to a brass ring beam and dome ribs round an oculus, side galleries (the upper bowl) with guests, two rows
of engraved inductee plates between the columns (one blank "INDUCTEE / THIS SPACE RESERVED" plate),
big plates and a "THE DRUMMER HALL OF FAME" frieze framing the great back window. Through the window and
the open dome: ~4800 emissive stars (white/blue/warm + a galactic dust band, a hole eaten round the black
hole), and the black hole high above the highway: black shadow, photon ring, lensed disc glow, a nearly
edge-on accretion disc. Five huge brass drive rings (11 m to 4.2 m radius) hang over and behind the band
on two brass pylons, centred on the Wide camera's line to the hole, so once aligned they form a bullseye
round it. By the kit: one plain music stand, a warm rehearsal lamp (emissive shade + plain point light),
five brass contact pickups and braided leads running to the pylons, a drilled loonie on the hat stand.
Stage right: the conductor's walnut podium with brass rail and score desk, and a low-poly conductor in tails.

## Flags (each a VenueStory pair: tilted copy `WhenSet=false`, aligned copy `WhenSet=true`, pivot at the ring centre)

| Flag | Visible change |
|---|---|
| `first_ring_turning` | Outer ring swings from near-horizontal into line; an amber light strip runs round its face; amber spill light. |
| `second_ring_aligned` | Second ring snaps in (gold strip); **bent starlight**: a row of stars appears twice, smeared into arcs above and below the black disc. |
| `third_ring_locked` | Third ring locks (cyan strip); brass clamps with cyan lamps bridge rings 2-4 on the diagonals; the conductor steps back from the desk, baton down. |
| `fourth_ring_charged` | Fourth ring burns white; the black hole swells (x1.35 to x2.2) to fill the window; the house lights (sconces, hall glow) go down; the conductor turns to cue the drummer. |
| `fifth_ring_armed` | Innermost ring locks above the kit (gold); charge nodes light on all five rings; a pulse core and a beam join the rings' centre to the hole. |

State only carries within the run (one sitting); nothing persists.

## Band spots

Drummer (riser, 0,1.0,7.9), Bass, Guitar, Vocals, Keys (stage left rear, yawed in). Matches OnStage + OptionalOnStage keys.
Crowd: 60 posed front rows, 220 mob on the gala floor, 100 in the side galleries.

## Cameras

Wide `down-the-rings` (looks straight down the ring axis at the hole), Crane `gallery-crane` and `ring-window`,
Desk `long-lens`, Close `sticks`, Custom `under-the-rings` (the beat), `stand-and-lamp`, `conductor`,
`bass-locks-eyes`, and an `arrival/01..05` walk from the doors up the aisle toward the rings.

## Lights

30 VenueShowLights (6 front washes, 4 back washes, 5 follow spots, 8 rim beams, 2 blinders, 2 strobes,
1 static key, 1 static starlight fill, 1 shadowed directional "accretion light" from the hole: the only shadow caster).
Plain lights: 5 ring spills, armed core, rehearsal lamp, 6 sconces + hall glow (all but the lamp story-gated).

## Previews (960x540 after the coordinator's request)

`wide_song1_start.png`, `wide_song3.png`, `wide_song5_end.png`, `drummer.png`, `beat.png` (under the rings, all armed),
`gallery_song4.png` (crane: house down, the swollen hole, the conductor's turn).

## Couldn't do / notes

- The conductor is a static low-poly figure in three poses swapped by flags, not an animated performer
  (no marker for a non-band performer). Reflected light "running round on the kicks" is static strips:
  nothing here can pulse on the beat except show lights, which can't be story-gated.
- The ring shadow passing the music stand each phrase (song 3) isn't modelled.
- The epilogue (pulse pinching the hole shut, the name engraved) is after the set; the blank plate is there for it.
- The OBJs have no cooked `.assbin` twins yet: run Build Assets before a Retail ship.
- Nothing for NEEDS.md.
