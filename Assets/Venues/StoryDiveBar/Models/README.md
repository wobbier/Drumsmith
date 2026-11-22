# The Dead End Dive Bar: models

Built by `Tools/Venues/make_story_dive_bar.py` (with `Tools/Venues/story_dive_bar_art.py`). Most of the room is engine primitives with textures drawn in `../Textures/` (all names on them are made up).

| File | Source and treatment |
| --- | --- |
| `League_<look>_Torso.obj` | Copies of the game's crowd pieces `Assets/Models/People/Crowd/<look>/Torso.obj` (themselves cut from the owner's Synty Polygon Town characters), with the material swapped to `League.mtl`. Geometry and UVs unchanged. Owner's Synty licence. |
| `LeagueShirts.png` | `Assets/Models/Venue/PolygonTown_01_A.png` (Synty Polygon Town atlas) with the eight 30 px shirt swatches the crowd torsos sample painted mustard: the pool league's shirts. Owner's Synty licence. |
| `League.mtl` | Binds `LeagueShirts.png`. |

Referenced in place (read-only, not copied): `Assets/Models/Venue/` (Stool, Bottle, BeerCup, Keg, GuitarCab, AmpHead, SpeakerTall, Wedge, RoadCase, DrumRug, CableCoil, WheelieBin, CardboardBox; provenance in that folder's README), the crowd pieces in `Assets/Models/People/Crowd/`, and the Backyard's bent limbs (`Assets/Venues/Backyard/Models/<look>_<piece>_<angle>.obj`) and motions (`Assets/Venues/Backyard/Motion/*.sequence`). `../Motion/Clap.sequence` is original.
