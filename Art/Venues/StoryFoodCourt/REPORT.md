# StoryFoodCourt: set 08 "Food Court Farewell Show"

A mall food court on its last weekend: a terrazzo floor and a drained octagonal fountain with the kids standing in it. The drum riser is three orange cafeteria tables with gaffer tape, a tray, a towel and a setlist. Six made-up stalls line the back wall with their shutters half down (Juice Junction, Golden Wok, Pretzel Twist, Taco Loco, Big Scoop, Hot Dog Hut). Above that: a U-shaped mezzanine with paired escalators either side of the stage, a long skylight, "EVERYTHING MUST GO" and "THANK YOU FOR 31 YEARS" banners, and a "DROP-IN SKATE SUPPLY FAREWELL MATINEE" banner. Along the walls: a closing department store, the skate shop, a security desk, vending machines and arcade cabinets. It starts with bright fluorescents and sun, and ends at dusk with party lights.

## Files

- `Tools/Venues/make_story_food_court.py` is the generator. It is deterministic (two reruns give the same `.lvl` md5), and `--textures` repaints the PNGs.
- `Tools/Venues/story_food_court_art.py` paints the textures with ImageMagick and writes the flat OBJs: signs, banners, shutters, the tiled floor and four drumhead states. A repaint deletes the stale `.png.dds` twins.
- `Tools/Venues/story_food_court_fbx.py` is a stdlib binary-FBX to OBJ converter for the Synty props.
- `Tools/Venues/story_food_court_people.py` builds the named figures from crowd pieces, with six looping `.sequence` poses.
- `Assets/Venues/StoryFoodCourt/` holds `venue.json`, `StoryFoodCourt.lvl`, `Preview.jpg`, `Models/` (OBJ/MTL/PNG plus `README.md` provenance) and `Motion/`. The ambience is `Assets/Sounds/crowd.mp3`.
- Copied from the owner's Synty OfficePack (owner's Synty licence), listed in `Models/README.md`: vending machines, arcade cabinets, cafe chairs and tables, stacking chairs, bins, a wet-floor sign, a janitor cart, balloons, a security camera, planters, a neon cactus, bunting, paper cups and table football.
- The kid and the guard wear the manifest's clothes: their crowd pieces are copied into `Models/People/Kid` and `Models/People/Guard`, bound to `PolygonTown_04_A` and `_04_B`.

## Flags

A moved prop is two paired groups, and the head's four states are nested groups so exactly one shows at a time.

- **`one_signature`:** the head (one signature, "Kit") appears on the fountain lip, the hoodie kid stands beside it, and a cardboard "SIGN THE HEAD!" goes up on the spout.
- **`guard_drawn`:** a cap is drawn on the head, two boards lean on the rim, a second skater arrives, and the guard leaves his desk to stand behind them.
- **`guard_signed`:** a moustache is added, the guard moves beside the kid and claps, a bunch of balloons goes up on the spout, and half the fluorescents go off.
- **`shutters_down`:** all seven shutters roll fully down (two with CLOSED notes), and the stall lights, the rest of the fluorescents and the sun go off. The skylight turns to dusk and fairy lights and party lamps come on. Eight staff in name tags line the fountain rim, and the head comes back nearly black with signatures.
- **`head_on_riser`:** the head moves to the front of the riser and the kid stands on the rim with both arms up.

## Band and crowd

- Spots: Drummer on the tables (y 0.76), plus Guitar, Bass and Vocals on the floor. There is no Keys spot.
- Crowd: 12 areas, about 340 people at a full house. Posed areas are in and around the fountain and along the front rail. Mobs fill the back of the floor, both mezzanine rails, the back mezzanine and the escalator landings.

## Cameras (16)

- Director shots: Wide `food-court-wide`, Crane `skylight-crane`, Desk `desk`.
- Close: `sticks`.
- Custom: `fountain-lip` (the head beat), `head-on-the-riser`, `mezzanine-rail`, `escalator-ride`, `over-the-kit`, `security-desk`.
- Intro: `arrival/01..06`, a walk in from the doors.

## Lights

47 Lights, 24 of them VenueShowLights:
- 10 Wash, 4 Beam, 4 Spot (follow spots from the mezzanines), 2 Blinder, 2 Strobe, 2 Static.
- The one shadow-casting light is the directional sun, which sits in the "afternoon" story group and fades out at `shutters_down`.
- No show light is under a story group.

## Couldn't do / caveats

- The capture budget left `head-on-the-riser` (moved after its preview because a front-row figure blocked it) and the mezzanine, escalator, over-the-kit, security-desk and arrival cameras unverified.
- The head is 0.8 m across, a little oversized so it reads in crowd shots, but it is still small in the far wide. Each head beat is therefore paired with a bigger change: the guard moving, the balloons, the shutters and lights, the staff on the rim.
- The Clap pose looks like open arms.

## NEEDS.md

- `magick` is not on the PATH. The generator finds ImageMagick in the Nix store itself, and only needs it for `--textures`.
- No shared FBX converter exists; mine could be promoted.
- A from/until story flag would cut down the nested groups.
