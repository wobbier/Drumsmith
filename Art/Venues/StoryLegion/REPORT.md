# StoryLegion: Funeral Afterparty at the Legion (s05-legion)

The room reads as a Legion hall in one wide: panelled walls, checker lino, a strip of block parquet, a drop ceiling with the fluorescents dimmed, round tables in white cloths, folding chairs, the bar, the crest and two flags behind the band, an upright piano, and a memorial table with Dad's portrait on an easel. Band spots: Drummer, Guitar and Bass (matching OnStage), with a tea towel on the snare.

## Files
- `Tools/Venues/make_story_legion.py`: the generator. It is deterministic and writes the scene, `venue.json` and `Models/README.md` (provenance). It sets `sys.dont_write_bytecode`, so it doesn't touch the tracked pycache.
- `Tools/Venues/story_legion_mesh.py`: the low-poly OBJ writer and palette.
- `Tools/Venues/story_legion_props.py`: furniture and props.
- `Tools/Venues/story_legion_people.py`: posed figures baked to one OBJ each from `Assets/Models/People/Crowd` pieces (read in place) in chosen Town atlas variants, plus the Sway, Bounce and Breathe clips.
- `Tools/Venues/story_legion_textures.py`: draws every texture with ImageMagick 7. When it redraws a PNG it deletes that PNG's stale `.dds` twin.
- `Assets/Venues/StoryLegion/`: `venue.json`, `StoryLegion.lvl`, `Models/` (with `People/` and `README.md`), `Textures/`, `Motion/`. Ambience is the shared `Assets/Sounds/crowd.mp3`.
- `Art/Venues/StoryLegion/cap.sh`: the locked capture helper on display :105.
- All textures are drawn: an invented branch crest, the Canadian flag, a branch standard, a painted portrait of Dad, the honour roll, a letter board (CELEBRATION OF LIFE / DOUG / 1951-2026), a meat-draw sign, LEST WE FORGET, a CHEERS, DAD banner, the tea towel, the napkin requests.

## Flags
| Flag | Before | After |
|------|--------|-------|
| `toast_seat_empty` | Uncle standing with his glass raised and the folded toast in hand, under a narrow spot | Wider pool on the daughter and the empty chair; the toast left on the seat; the uncle seated at the same table |
| `dessert_table_moved` | Dessert cart on the parquet | Cart against the east wall under its own light; one lemon square crooked on a plate |
| `shoes_by_chair` | Daughter seated (uncle seated, in a nested group) | Daughter and uncle slow-dance under their own spot (24 s turn and sway); her heels under the empty chair |
| `portrait_on_piano` | Portrait on the easel with a picture light | Portrait on the piano with a picture light, the tie draped on the lid corner, the napkin stack |
| `family_on_floor` | (nothing) | Six cousins bouncing on the parquet; his oxfords beside her heels; a cousin on a chair at the west edge of the floor with a camera and the flash lit |

## Cameras
- Wide `hall-wide`, Crane `crane-west`, Desk `bar-long-lens`.
- Custom: `toast-table`, `portrait-piano`, `dance-floor`, `dessert-wall`, `memorial`. Close: `tea-towel`.
- `arrival/01` to `06`: a walk in through the doors, past the bar and the memorial, to the stage.

## Crowd
- About 50 Mob and Posed figures, with the area right in front of the family table kept clear so the beat can be seen.
- Eight seated relatives at the tables and a bartender, as baked figures.

## Lights
- **18 VenueShowLights:** 8 Wash (party cans on two T-bars), 4 Beam (two off the mirror ball, two uplights), 3 Spot (follow spots), 2 Blinder, 1 Strobe.
- **Plain lights:** dimmed fluorescent downlights, warm house downlights, and practicals for the crest, the bar, the exit sign, the candles, the piano sconces and the window.
- **Story lights** live inside their story groups.
- **1 directional with shadows.** The ceiling and walls are primitives with shadows off, so it reaches the room.

## Previews
`Art/Venues/StoryLegion/Previews/`: `wide_song1_start.png`, `wide_song3.png`, `wide_song5_end.png`, `drummer.png`, `beat.png`, `piano_portrait.png` (960x540). Every preview shows the song-title card, which isn't part of the venue.

## Couldn't do / notes
- The capture budget limited iteration. The lighting is deliberately warm and dim.
- The photo flash stays lit for the whole of song 5 once the flag lands. A one-shot flash at the cutoff would need a story-cue-timed accent, which the framework doesn't have (the one NEEDS item; no NEEDS.md written).
- The cousins with arms overhead show thin slivers from the shoulder caps of the crowd pieces up close. They can't be seen at wide distance.
