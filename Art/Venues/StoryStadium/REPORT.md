# StoryStadium: "The Retractable Roof Is Open" (s12-stadium)

The hometown headline and the story's finale: a domed stadium with its roof rolled back to the
night sky. Built by `python3 Tools/Venues/make_story_stadium.py` (deterministic: a rerun gives
the same bytes; helper module `Tools/Venues/story_stadium_art.py`). `check_venue.py` passes.

## Files

- `Assets/Venues/StoryStadium/venue.json`: Name "The Retractable Roof Is Open", Author Drumsmith,
  Scene `StoryStadium.lvl`, Version 1, `Preview.jpg` (a crop of the payoff wide), Ambience
  `Assets/Sounds/crowd.mp3`.
- `Assets/Venues/StoryStadium/StoryStadium.lvl`: the scene (530 entities).
- `Assets/Venues/StoryStadium/Models/`: generated OBJ/MTL meshes and textures (palette atlas,
  seat crowd tile, field floor tile, screen inserts, card mosaics, ribbon board, LED wall) and
  `Commuter/` (Mother_02 crowd pieces copied, bound to `PolygonTown_02_B.png` in place).
  Provenance in `Models/README.md`.
- `Assets/Venues/StoryStadium/Motion/Swing23.sequence`, `Swing46.sequence`: the loonie swings.
- `Tools/Venues/make_story_stadium.py`, `Tools/Venues/story_stadium_art.py`.
- `Art/Venues/StoryStadium/cap.sh` (the capture script: holds the lock only until the PNG lands),
  `Previews/`, this report.

## The place

- **Bowl** (a few models, so a few draw calls): a rounded-rectangle bowl round an 80 x 116 m
  field. Lower bowl: 24 rows of painted seated crowd (a tiling texture with a faint self-glow),
  concrete aisles, a field-wall LED ribbon ("WELCOME HOME / ONE NIGHT ONLY / TONIGHT"); the rows
  behind the stage are tarped. Suites with lit glass. Upper deck: 26 rows all the way round, its
  own ribbon fascia, exit signs at the vomitories. Roof ring: the cantilever over the upper deck
  with floodlight banks (mostly dark for the show), ribs, the two roof rails crossing the open
  sky and the retracted panels parked at each end. Outdoor: the night sky and moon show through.
- **Field**: a floor of painted heads under the Mob; the barricade (17 panels); the pit with two
  cameras; the FOH tower with a lit desk; two light/delay towers with lamp heads and delay hangs.
- **Stage**: a 34 x 14 m deck at 2.2 m with a gold lip, a 1 m drum riser (amber lip), a keys
  riser (cyan lip), an arched roof on four lattice towers with a gold LED edge, line arrays and
  sub stacks, an LED wall of the hometown skyline under a moon, backline, wedges and road cases.
- **Side screens**: two 14 x 7.9 m `VenueScreen`s on truss towers (W: Program, E: Stage), with
  picture-in-picture story inserts laid just in front of their corners.
- **Kit look**: drum rug, the subway bucket (sticks across it) beside the floor tom, the drilled
  loonie swinging on its little stand by the hi-hat, setlist, towel, water, drum fills, a fan.
- **Band spots**: Drummer, Bass, Guitar, Vocals, Keys (the optional keys seat), matching OnStage.
- **Crowd**: Posed front rows at the barricade (319, split round the commuter's spot); Mob on the
  field (~1940: wings, front field, around the FOH, back field) and five standing rows on each
  side of the lower bowl (340). The painted seats carry the rest of the 60 000.
- **The commuter** (Mother_02 / 02_B): front row at the barricade, mustard scarf, steel mug.

## What each flag does

| Flag | What changes |
|------|--------------|
| `mug_on_screen` | Both side screens cut to a "LIVE / THE BARRICADE" insert (upper outer corner) of her mustard scarf and dented mug; a pit spot comes up on her. The insert gives way to the loonie's later. |
| `upper_deck_lit` | The upper deck lights up with ~8 000 phone lights in eight sectors, each growing out from its own middle, plus pairs of torches coming down every aisle. The biggest change in the wide. |
| `stands_in_dialogue` | The two side stands of the lower bowl hold up opposing card stunts: amber "HEY! ▶" (west) and cyan "◀ HO!" (east); each screen's inner lower corner shows its own stand. |
| `loonie_on_screen` | A 4.6 m drilled loonie drops out of the stage roof on its chain and swings over the kit under a gold key light; both screens show "THE FIRST LOONIE". |
| `bucket_answered` | Both stands' cards turn gold into one "HOME [bucket] TOWN"; six gold searchlight beams rise from the roof ring through the open roof; the bucket comes up off the riser floor onto a case beside the floor tom under its own spot; the screens show "THE BUCKET ANSWERS"; the commuter's mug goes up. |

## Cameras (16)

`foh-wide` (Wide, high behind the FOH tower), `upper-crane` (Crane), `desk-long` (Desk),
`sticks` (Close, the drummer). Custom: `barricade-mug`, `upper-deck-phones`,
`stands-dialogue`, `loonie-swing`, `bucket-answer`, `open-roof`. `arrival/01..06`: out of the east
players' tunnel onto the field, up at the bowl, then the crash zoom to the band.

## Lights

35 `VenueShowLight`s (12 wash, 8 beam, 5 follow spots from the FOH tower and the light towers,
6 blinders, 4 strobes). One shadowed light: the moon (directional). Plain practicals: LED wall
spill, kit fill, worklights, the FOH lamp, four dim bowl glows. The story's own plain lights:
the pit spot on the commuter, the loonie's key and rim, the spot on the bucket.

## Peaks

`VenueAccent`s: three firework bursts above the stage roof against the open sky and two confetti
cannons on the stage lip, on a 16-beat group.

## Frame rate

The bowl, seats, roof and field are 6 models; each story overlay is one model (the phones are 8);
props are instanced boxes in few colours. Crowd ~2600 figures, about the built-in Arena's count,
with fewer Posed figures (319 against the Arena's 520).

## Previews (960 x 540)

`wide_song1_start.png`, `wide_song3.png`, `wide_song5_end.png`, `drummer.png` (song 4),
`beat.png` (song 5 from the pit: the commuter with her mug up, the lit upper deck and the gold
cards behind), `upper_deck_phones.png` (song 2, the moment the upper deck lights).

## What I couldn't do

- "A whole stand claps the old bucket pattern": no per-area crowd animation hook, so the stands'
  side of the story is told by the cards and the screens.
- The live screens can't be told what to show, so the story inserts are separate emissive panels
  in front of a corner of each screen.
- A plain light can't be gated by two flags (nested story groups both drive its intensity), so
  the stands' colours come from their cards' own glow rather than coloured floods (which also
  tinted the gold finale green).
- The commuter's mug is small at wide distance; the screens carry it.
- I took ~11 captures against the coordinator's revised cap of ~8; the extra ones chased the
  emissive problems below.

## Notes for NEEDS (nothing blocking)

- An MTL `Ke` above 1 seems to be clamped (emissive goes through `SrgbToLinear`), so a texture's
  glow can't be pushed past 1 from the MTL.
- A Model `Parts` material override that sets only `EmissiveIntensity` loses the imported
  textures; the override has to name `Textures` (Diffuse/Emissive) again.
- A texture's cooked `.dds` twin wins over a newer `.png`; the generator deletes stale twins.
