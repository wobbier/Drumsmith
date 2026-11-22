# Food Court Farewell Show models

Made by `Tools/Venues/make_story_food_court.py` (rerun to rebuild).

## Copied from the owner's Synty packs

Licence: the owner's Synty licence. Source: `MitchGame/Assets/Models/Synty/`. Converted from FBX to OBJ by
`Tools/Venues/story_food_court_fbx.py` (node transforms applied, uniformly scaled to the stated size, floor-centred
pivot; vertices and UVs kept). The pack atlas is copied beside them.

- `VendingMachine.obj`: OfficePack/FBX/SM_Prop_VendingMachine_01.fbx, with PolygonOffice_Texture_01_A.png; 1.95 m tall (1.18 x 0.78 m footprint).
- `Arcade.obj`: OfficePack/FBX/SM_Prop_ArcadeMachine_01.fbx, with PolygonOffice_Texture_01_A.png; 1.9 m tall (0.88 x 0.99 m footprint).
- `CafeChair.obj`: OfficePack/FBX/SM_Prop_Chair_05.fbx, with PolygonOffice_Texture_01_A.png; 0.9 m tall (0.70 x 0.70 m footprint).
- `StackChair.obj`: OfficePack/FBX/SM_Prop_Chair_09.fbx, with PolygonOffice_Texture_01_A.png; 0.83 m tall (0.53 x 0.58 m footprint).
- `CafeTable.obj`: OfficePack/FBX/SM_Prop_Table_02.fbx, with PolygonOffice_Texture_01_A.png; 0.75 m tall (1.33 x 1.27 m footprint).
- `TrashBin.obj`: OfficePack/FBX/SM_Prop_Trashbin_01.fbx, with PolygonOffice_Texture_01_A.png; 1.1 m tall (0.60 x 0.46 m footprint).
- `WetFloor.obj`: OfficePack/FBX/SM_Prop_Sign_Wetfloor_01.fbx, with PolygonOffice_Texture_01_A.png; 0.75 m tall (0.41 x 0.44 m footprint).
- `JanitorCart.obj`: OfficePack/FBX/SM_Prop_Janitor_Cart_01.fbx, with PolygonOffice_Texture_01_A.png; 1.15 m tall (1.42 x 0.69 m footprint).
- `Balloon.obj`: OfficePack/FBX/SM_Prop_Balloon_01.fbx, with PolygonOffice_Texture_01_A.png; 1.8 m tall (0.46 x 0.48 m footprint).
- `SecurityCam.obj`: OfficePack/FBX/SM_Prop_Security_Camera_02.fbx, with PolygonOffice_Texture_01_A.png; 0.5 m tall (0.29 x 0.25 m footprint).
- `Planter.obj`: OfficePack/FBX/SM_Prop_Plant_07.fbx, with PolygonOffice_Texture_01_A.png; 1.5 m tall (2.42 x 1.42 m footprint).
- `PottedPalm.obj`: OfficePack/FBX/SM_Prop_Plant_01.fbx, with PolygonOffice_Texture_01_A.png; 1.4 m tall (0.94 x 1.02 m footprint).
- `NeonCactus.obj`: OfficePack/FBX/SM_Prop_Neon_Cactus_01.fbx, with PolygonOffice_Texture_01_A.png; 0.55 m tall (0.29 x 0.17 m footprint).
- `Bunting.obj`: OfficePack/FBX/SM_Prop_Bunting_01.fbx, with PolygonOffice_Texture_01_A.png; 0.63 m tall (2.81 x 0.03 m footprint).
- `PaperCup.obj`: OfficePack/FBX/SM_Prop_Cup_Paper_01.fbx, with PolygonOffice_Texture_01_A.png; 0.15 m tall (0.14 x 0.14 m footprint).
- `DonutBox.obj`: OfficePack/FBX/SM_Prop_Donut_Box_01.fbx, with PolygonOffice_Texture_01_A.png; 0.1 m tall (0.15 x 0.12 m footprint).
- `TableFootball.obj`: OfficePack/FBX/SM_Prop_TableFootball_01.fbx, with PolygonOffice_Texture_01_A.png; 0.89 m tall (1.43 x 1.50 m footprint).

## People

- `People/Kid/`: the game crowd pieces of BodyType1_SchoolGirl_01 (`Assets/Models/People/Crowd/SchoolGirl_01/`),
  bound to `Assets/Models/Venue/PolygonTown_04_A.png` (the manifest's skate-shop kid). Owner's Synty licence.
- `People/Guard/`: the crowd pieces of BodyType1_ShopKeeper_01 bound to `PolygonTown_04_B.png` (the mall guard).

## Original

Every other PNG (stall signs, menus, banners, posters, shutters, the floor tile and the four drumhead states) is
painted by `Tools/Venues/story_food_court_art.py` with ImageMagick and the repo fonts (Permanent Marker, Gochi Hand,
both OFL) or DejaVu. The shops, the mall and every name on the head are made up. The flat meshes carrying them
(Sign*, Banner*, Head*, Shutter*, Floor*) are written by the same module.
