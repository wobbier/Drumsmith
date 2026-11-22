# StorySteelMill: report

Set 10, "One Night on the Steel Mill Tour" (`s10-steel-mill`). Venue id `StorySteelMill`.
`python3 Tools/Venues/check_venue.py Assets/Venues/StorySteelMill`: ok (1824 entities).

## Files

- `Tools/Venues/make_story_steel_mill.py`: the generator. It is deterministic. `--textures` redraws the PNGs, and the generator also redraws them when they are missing.
- `Tools/Venues/story_steel_mill_textures.py` draws the textures with ImageMagick: set sheets 1-5, the DRUMS road-case stencil, the STEEL MILL TOUR drop, the ROLLING MILL No. 3 header plate, the changeover board, hazard stripes, the crane's SWL plate, corrugated wall and mill windows. The PNGs are stored flipped vertically because the cube faces sample them that way. Each redraw deletes the stale `.dds` twin.
- `Tools/Venues/story_steel_mill_people.py` builds rigid figures from the crowd's low pieces, re-skinned with each character's manifest atlas. It also writes five looping Sequences: WingNod, WingSway, HornsUp, Wave and Point.
- `Assets/Venues/StorySteelMill/` holds `venue.json`, `StorySteelMill.lvl`, `Preview.jpg`, `Textures/`, `Motion/`, `Models/People/<Body>_<atlas>/` (copied crowd pieces with their own `.mtl`) and `Models/README.md` (provenance; the owner's Synty licence). The ambience is the shared `Assets/Sounds/crowd.mp3`.
- `Art/Venues/StorySteelMill/Previews/` holds the previews. `NEEDS.md` holds the framework requests.

## The room

A festival stage stands inside a decommissioned rolling mill.

- **Walls and roof:** I-section columns run down both corrugated walls, with crane runways on corbels. Roof trusses carry a shallow gable roof with skylights. The roof casts no shadow, so the moon gets in. High mill windows glow steel-blue, and sodium high-bay lamps hang under the trusses.
- **Cranes:** there are two gantry cranes.
  - The rusted crane over the stage carries both lighting trusses on chains.
  - The yellow crane over the pit hangs an old ladle full of orange light. The ladle drips sparks all night and pours a burst on peaks (a `VenueAccent` particle system).
- **Mill dressing:** down the right wall, a roller table runs through two rusted roll stands with a glowing slab on it. On the left are steel coils, scrap skips and a catwalk crowd.
- **Stage:** a rusted girder portal frames the stage, with the ROLLING MILL No. 3 plate on it. Line arrays hang either side, subs sit on the floor, there is a steel barricade, and front of house stands mid-floor.
- **Changeover wing:** stage left (the crowd's left), on the same deck. It has work tubes, a worklight, road-case stacks and a changeover board naming the five acts. All the band names are made up.

## What each flag does

| Flag | Change |
|------|--------|
| `sheet_one` | Sheet 1 (white, SLAG CHOIR) is taped to the riser face by the floor tom. Act lamp 1 of five on the portal header comes on (amber glow and a light). |
| `sheet_two` | Sheet 2 (blue) and lamp 2. The opener's bass player stands in the wing with a white towel round their neck, beside their case. |
| `sheet_three` | Sheet 3 and lamp 3. The first two acts watch from the wing, with a roll of gaffer tape on the wing monitor. The crew stop clearing: the dolly with a case and the KEEP CLEAR A-frame leave, and stools, a cooler and cans arrive. |
| `sheet_four` | Sheet 4 and lamp 4. A yellow tripod work lamp comes on beyond the sheets with the big drum case under it, stencil turned to the back wall. The mill crew chief points at it, and act 3 joins the wing. |
| `case_faces_house` | The case turns into the work light, with an extra key light on it, so "DRUMS / HOUSE KIT - STEEL MILL TOUR" and the five bands' tape read from the house. Sheet 5 and lamp 5 arrive. The singers of acts 1-4 leave the wing and come out beside the sheets (horns up or waving). Act 4's bass and guitar take their place in the wing. |

The five act lamps across the top of the portal are the wide-shot read of the sheets. The sheets themselves sit lower-centre on the riser face.

## Band, crowd, cameras, lights

- **Spots** match OnStage: Drummer on the riser, Bass, Guitar and Vocals. There is no Keys spot.
- **Crowd** is about 890 heads:
  - 96 Posed figures in the pit, with DanceFloor on.
  - Mob areas on the pit edges, the floor, and around and behind front of house.
  - 32 on the catwalk.
- **Cameras:**
  - Wide `mill-wide`, Crane `crane-over-the-pit`, Desk `foh-long-lens` and Close `kit-close`.
  - Custom shots: `the-sheets-and-the-case`, `from-the-wing`, `the-wing-from-the-house`, `catwalk` and `ladle-and-girders`.
  - An `arrival/01..06` walk comes in through the rolling door, under the ladle, to the barricade.
- **Lights:** 31 `VenueShowLight`s:
  - 8 Wash, 8 Beam, 4 Spot, 4 Blinder and 6 Strobe.
  - 1 Static: the moon, a directional light and the only shadowed light.
  - The other 31 lights are plain practicals: the ladle, slab heat, high-bays, column uplights, drop wash, wing tubes and worklight, house fills, plus the story lights (five act lamps, the work lamp and the key on the case). No show light is under a story group.

## Previews (960x540)

- `wide_song1_start.png`: the empty mill stage as the set opens, with no sheets and dark lamps.
- `wide_song3.png`: three sheets and three lamps lit, with people in the wing.
- `wide_song5_end.png`: the payoff, with all five lamps lit, the singers out and the case lit. It is also `Preview.jpg`.
- `drummer.png`: the house kit on the riser rug.
- `beat.png`: the five sheets, the four singers, the DRUMS case under the work lamp, and the wing full of bands.
- `wing_song4.png`: the wing from the house at song 4, with the case still turned away and the changeover board.

## What I couldn't do, and known issues

- **Stale textures in four previews.** `wide_song1_start`, `wide_song3`, `drummer` and `wing_song4` were shot while a stale cooked `.dds` was still in use. Their header and drop text shows upside down. The cooked twins have since been rebuilt and `beat` / `wide_song5_end` show it correctly. I did not reshoot the four to stay inside the capture budget. The drum rug was scaled down after `drummer.png` was taken.
- **Wing camera blocked.** In `wing_song4.png` the portal column partly blocks the wing. The `the-wing-from-the-house` camera has since been moved to clear it, but that version was not captured.
- **No cameos.** The conditional song-2 cameos (Jules, Ness) are not built, because story groups can't see audition choices (see `NEEDS.md`).
- **Crowd is not the cast.** The trios on stage are whatever figures the show builds. The venue only dresses the off-stage people with the manifest bodies and atlases.
- **No real-GPU check.** The scene has 62 lights and haze, and has only been seen in headless lavapipe.
