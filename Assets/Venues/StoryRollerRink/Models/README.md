# Roller rink models

Everything here is written by `Tools/Venues/make_story_roller_rink.py` (and its helpers
`story_roller_rink_meshes.py`, `story_roller_rink_textures.py`, `story_roller_rink_skaters.py`).

## Drawn here (no source asset)

- The `.obj` meshes at this level (the maple oval, the carpeted rail, the booth riser and truss, the
  counters, the cubby wall, turntables, the mirror ball and its spangles, skates, neon strips, light
  pools and the sign quads) are generated geometry.
- The `.png` textures at this level (`Palette`, `Maple`, `Carpet`, `Glitter`, the signs, boards,
  menu and posters) are drawn with ImageMagick. The names on them (Moonbeam Rollerdrome and so on)
  are made up. Fonts: Noto Sans / Noto Serif Display (OFL), Liberation Mono (OFL) and the game's
  Permanent Marker (Apache 2.0).

## Synty (owner's Synty licence)

Copied unchanged from `/home/mitch/Projects/MitchGame/Assets/Models/Synty/`; subject to the owner's
Synty licence.

| File | Pack | Original |
|------|------|----------|
| `Synty/SM_Prop_ArcadeMachine_01.fbx` | POLYGON Office | `OfficePack/FBX/SM_Prop_ArcadeMachine_01.fbx` |
| `Synty/SM_Prop_VendingMachine_01.fbx` | POLYGON Office | `OfficePack/FBX/SM_Prop_VendingMachine_01.fbx` |
| `Synty/SM_Prop_Fridge_02.fbx` | POLYGON Office | `OfficePack/FBX/SM_Prop_Fridge_02.fbx` |
| `Synty/SM_Prop_Neon_Cactus_01.fbx` | POLYGON Office | `OfficePack/FBX/SM_Prop_Neon_Cactus_01.fbx` |
| `Synty/SM_Prop_Balloon_01.fbx` | POLYGON Office | `OfficePack/FBX/SM_Prop_Balloon_01.fbx` |
| `Synty/SM_Prop_Table_Round_01.fbx` | POLYGON Office | `OfficePack/FBX/SM_Prop_Table_Round_01.fbx` |
| `Synty/SM_Prop_Chair_05.fbx` | POLYGON Office | `OfficePack/FBX/SM_Prop_Chair_05.fbx` |
| `Synty/SM_Prop_Cup_Paper_01.fbx` | POLYGON Office | `OfficePack/FBX/SM_Prop_Cup_Paper_01.fbx` |
| `Synty/SM_Prop_Trashbin_01.fbx` | POLYGON Office | `OfficePack/FBX/SM_Prop_Trashbin_01.fbx` |
| `Synty/SM_Prop_Sign_Wetfloor_01.fbx` | POLYGON Office | `OfficePack/FBX/SM_Prop_Sign_Wetfloor_01.fbx` |
| `Synty/PolygonOffice_Texture_01_A.png` | POLYGON Office | `OfficePack/Textures/PolygonOffice_Texture_01_A.png` |

The `.fbx.meta` files are written by the generator (`ConvertUnits` on, a GUID of their own).

## The cast (`Cast/<name>/`)

Copies of the crowd's rigid pieces (`Assets/Models/People/Crowd/<person>/*.obj`, cut from the
Synty POLYGON Town characters by `Game/Tools/MakeCrowdPieces.py`; owner's Synty licence) with a
material on another Town atlas variant from `Assets/Models/Venue/` (the set's `Characters` looks:
the silver jackets on `PolygonTown_03_C` / `PolygonTown_02_B`, the learner on `PolygonTown_03_B`).
`SilverLead/Jacket.png` and `SilverPartner/Jacket.png` are that atlas with the torso and arm
clothing texels repainted silver.

Models elsewhere are referenced in place, read-only: `Assets/Models/Venue/` (Speaker, SpeakerTall,
Wedge, GuitarCab, AmpHead, DrumRug, Stool, FoodStall: the nacho warmer).
