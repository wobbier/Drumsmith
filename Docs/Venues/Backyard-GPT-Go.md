# Backyard: the "OK GO" prompt

This is the morning prompt for the assistant that prepared `Art/Venues/Backyard/` overnight (a coding-capable assistant working in this same checkout). Paste everything inside the fenced block below. Before sending, fill in or delete each line that starts with **OWNER:**, and glance at the "Conflicts to expect" list at the end of this note, which is for you and is not part of the prompt.

````text
GO. The venue-scene framework you were waiting for is built. Please build the real Backyard now.

## 1. Context

Drumsmith is a free, GPL, non-profit drum rhythm game on MitchEngine (C++20). Venues are now scenes: a folder `Assets/Venues/<Id>/` with a `venue.json` and a Havana level (.lvl) holding geometry, lights and a few marker components that tell the game where the band, crowd, screens and cameras go. The framework is committed on branch `overhaul`:

  0e84c48 markers (DRU-58)    3248b46 VenuePlan (DRU-57)    6840e53 scene loader (DRU-59)
  80a995c registry/settings/menu (DRU-60)    fd14c0c Template + greybox Backyard + generator (DRU-61)

Read these before you start (in this order): `Docs/Venue-Authoring.md` (the guide, and the contract below in prose), `Game/Source/Components/Venue/VenueMarkers.h` (exact fields), `Tools/Venues/venuegen.py`, `Tools/Venues/make_template.py`, `Tools/Venues/make_backyard_greybox.py`, `Tools/Venues/check_venue.py`, `Assets/Models/Venue/README.md`.

What you prepared overnight in `Art/Venues/Backyard/` (LAST HOUSE AWAKE): 31 new OBJ/MTL models (19 imported Synty pieces, 6 original party/pergola/practical meshes, 6 original architecture meshes) with local atlas copies and provenance; a 53-kind asset schedule and 312 prop placements in `layout.json`; five band spots; 226 ground spectators in five rectangles (C1-C5) plus 10 optional roof spectators (R1); a 32-light fixture schedule plus one moon; ten camera compositions (C01-C10); an effects plan; and static validation (83,864 triangles). What is READY: the models, the layout, the lights and cameras as design data. What was BLOCKED on the framework and is now answerable: the scene schema, per-venue band spots, crowd rectangles and roof height, light roles, screens, camera import (all in section 3). What the framework still CANNOT do is listed in section 3 and 4 (effect emitters, circular crowd exclusions, absolute fog density, per-venue exposure).

The goal: replace the greybox `Assets/Venues/Backyard/Backyard.lvl` with the real low-poly Synty-style scene from your design, keeping the folder, `venue.json` and Id `Backyard` (Name may stay "Backyard Party" or become "Last House Awake": OWNER: pick one, or delete this line to keep "Backyard Party").

## 2. Answers to your QUESTIONS.md

1. "What exact scene schema and asset loader does the framework expose?" Scene format v2 `.lvl`, written by `Tools/Venues/venuegen.py`; no guessed layout.json loader. `layout.json` stays art data and a new generator reads it (section 5). Models load by `ModelPath` ("Type":"Model") relative to the repo root (`Assets/...`).
2. "Can member placements replace kMemberSpots per venue, including support Y?" Yes: one `VenueSpot` per member; the entity position is the performer's feet, so the riser's top is the spot's y (drums y 0.80). Facing: identity rotation faces the crowd (-Z), yaw to turn. Your five spots are usable as written. A missing spot removes that member.
3. "Can crowd rectangles specify floor height, facing and exclusions?" Floor height yes (the area's y). Facing: identity faces +Z (the band); R1 on the roof faces -z, so yaw it 180 degrees. Exclusions NO: rectangles are plain boxes and circles cannot be cut out. Split a rectangle around obstacles instead, or shrink it. Scene crowds are instanced "Mob" figures only; no posed front rows. Rotated areas use their axis-aligned bounds. R1 is supported; keep it, and check at preview that the 10 figures stand on y 5.5. Scale x/z are the full width/depth.
4. "Can lights bind existing cue roles while replacing the default rig?" Yes: `VenueShowLight` on an entity that also has an engine `Light`. Roles Wash/Beam/Spot/Blinder/Strobe/Static (section 3). A scene brings its own rig (`BuildRig` false). The five Spot lights are assigned to members in the order Drummer, Vocals, Guitar, Bass, Keys by role, so author S01 drums, then the vocals light, then guitar, bass, keys (your S04 is the vocals light and your S02/S03 the guitar/bass). Intensities are ENGINE UNITS, not your relative levels: see section 3 for a conversion.
5. "Can FX locations/counts be replaced and the existing flame lights reused?" NO. There are no effect-emitter markers. `VenueInfo.BuildFx = true` adds the built-in effects at the built-in positions only. Decision: leave `BuildFx` false for the first build (no pyro, no confetti, no CO2) and keep the static scenery (torches, pool, festoons) plus F01/F02 as ordinary cued Wash lights if you want a flame glow. Write your FX plan down in `Art/Venues/Backyard/FX.md` as "future; needs emitter markers". OWNER: say here if a built-in-position BuildFx stage show is acceptable instead.
6. "Can screens share an existing feed with recursion excluded?" Yes: `VenueScreen` with Source Stage, Program or Lyrics; several screens may use the same source. The game creates the quad (its scale x/y is the size; the picture faces local -Z), so you author only the frame. Sheet (ProjectionSheet) and TV (PatioTV): put a VenueScreen marker where the picture goes, with Source Program for the sheet and the TV (or Stage for one). Do not model the picture surface. If you want the dark/cream placeholder look, leave the screens out.
7. "Does the director accept authored eyes/targets and a non-Y up vector?" Authored eyes and targets: yes, as `VenueCameraSpot` (position = eye, looks along local +Z, FieldOfView is VERTICAL degrees, so your FOVs are right). Up is not a field: the camera's roll comes from the entity's rotation, so C10's up (0,0,-1) needs a rotation with a roll about the view axis; if you cannot produce it with the Euler helper in venuegen.py, omit C10. Shot mapping: use Shot Wide for your opening wide (C01) (it REPLACES the director's wide), Crane for C02 (replaces the crane move), Desk for the long-lens-from-the-desk analogue; every other composition is `Close` (pointing at a member, becomes a ~25% extra cut of that member) or `Custom` with a Tag. OWNER: the exact mapping of C01-C10 is yours to confirm; the default above is acceptable.
8. "How should no-flash / lights-off apply to venue-specific FX?" The global Stage Lights "no flashes" option softens the built-in flames and sparks and the Strobe role; a Static-role light is never touched. Nothing in a scene's own geometry reacts. Avoid emissive flashing in textures; use Static for everything that should not pulse (practicals, windows, lightbar patrol, searchlight).
9. "Should a proper police sedan and visible helicopter be commissioned?" No, as you recommend. OWNER: confirm or overrule.

Other decisions the framework makes for you:
- Sky/time: `VenueInfo.SkyTime` is an hour 0-24 (your 00:40 is 0.67) and `MoonBrightness` a scalar; there is no manual sky colour. Use `Outdoor` true.
- Fog: there is no absolute density. `Haze` (1 = the indoor usual; outdoors the game already scales it by 0.45) and `FogColor` (your #1D2340 as linear-ish floats). Start Haze at 1.
- Exposure is fixed; you cannot set it. Tune light intensities instead.
- Moon: one Directional light with CastShadows true, role Static, ray direction (0.28,-0.84,-0.46) from rotation; the only shadow caster. No other light may cast shadows.

## 3. The technical contract (exact)

Venue space: metres, +x the crowd's right, +y up, +z from the crowd toward the house/band. The crowd faces +z; the band faces -z. Positions are relative to the scene root; the game applies the venue origin once, so do NOT add any origin offset. Euler rotations are degrees (glm Rz*Ry*Rx; positive X pitches DOWN for things that look along +Z). A primitive cube is 2 m at scale 1.

Markers (add to entities; exact names and defaults from `Game/Source/Components/Venue/VenueMarkers.h`):
- `VenueInfo` (exactly one): Name, Author, Outdoor (true), RoomBack (z of the back wall behind the crowd; here the rear fence, -22), RoomCeiling (1000, none), RoomHalfWidth (14), DeskZ (the desk and crowd's far edge: -19 or so; the Desk camera sits there), BuildStage/BuildSet/BuildRig/BuildFx (all false), AmbientColor (unused outdoors), FogColor, Haze, SkyTime, MoonBrightness.
- `VenueSpot` (Drummer REQUIRED; Guitar, Bass, Vocals, Keys optional): `Member`, feet position, faces local -Z. The drum kit arrives as a unit at the Drummer spot, about 2.5 m wide by 2 m deep; keep it clear.
- `VenueCrowdArea`: centre position (y = floor height), scale x/z = full width/depth, `HeadCount`, `Jitter` (0 grid to 1 mob; 0.5 normal). Faces local +Z.
- `VenueCameraSpot`: eye position, `Shot` (Wide/Desk/Crane/Close/Custom), `FieldOfView` (vertical degrees), `Tag`; looks along local +Z.
- `VenueScreen`: quad size = scale x/y; the picture faces local -Z; `Source` Stage/Program/Lyrics; `Emissive`. The game makes the quad; you author only a frame around it.
- `VenueShowLight` on an entity with an engine `Light`: `Kind` Wash/Beam/Spot/Blinder/Strobe/Static, `Group`.
  Wash: cued colour and level; `Group % 3` picks the wash row; the same group is cued together; shown colour = cue colour mixed 30% with the authored colour. Beam: sways about its authored aim (pan <= 30, tilt <= 12 degrees). Spot: follow spot on a member (drummer first, then singer, guitar, bass, keys), never below 35%. Blinder: low glow that flashes on peaks. Strobe: strobe cues, peaks, full hype; odd/even groups alternate. Static: never touched.
- Each light's type, colour, cone (`InnerConeAngle`/`OuterConeAngle` are HALF-angles in degrees, 0-89: full intensity inside the inner, none outside the outer; halve any full beam angle from your LIGHTING.md) and `Range` come from its engine `Light`.

Intensity units: a point or spot's `Intensity` is the level at full in ENGINE units and falls off about I/d^2; a few hundred lights a band from 3-4 m; the Template uses 1200 for wash spots and 80 for a point key; the greybox Backyard spans 40 to 150000. Your LIGHTING.md levels are relative (1.0 = neutral key): convert with `Intensity = level * K / ...`, calibrating K from the greybox's drummer-spot value and checking headless shots. Record the K you chose in the generator.

Budgets: AT MOST ONE shadow-casting light (the moon). At most 40 `VenueShowLight` entities in total (you have 32 + the moon = 33). Crowd areas are axis-aligned rectangles, no holes.

What the loader strips (do not rely on any of these): scene Cores, `ScriptComponent`, `UIDocument`, `Camera` (and PostProcess/FlyingCamera/CameraSway on that entity), `AudioListener`. Do not put a Camera in the scene; cameras are `VenueCameraSpot`s.

Fallbacks: a scene with no `VenueInfo` or no Drummer `VenueSpot` is not a venue and the game uses a procedural room instead (check the log). No directional light: the game adds a key light.

## 4. Known gaps you must design around

- Scene crowds are Mob figures only (no posed front rows, no crowd surfer); `--crowd-size` does not scale them.
- No effect emitters (see answer 5).
- Directed shots of non-drummer members are under-lit in the greybox Backyard: add fill (Spot lights near member positions) when you tune.
- Lyrics screen ignores yaw; director shot offsets for non-drummer members do not turn with the member's yaw.
- Retail builds do not cook assets: ship compiled twins (.dds for textures, .assbin for models) for every model/texture you add (run the tools build / Havana Build Assets; see `Engine/Docs/Cooking.md`). If you cannot run a cook, say so in your report and list what needs it.
- Nothing has been checked on a real GPU. Keep triangle count modest (your 85k static is fine).

## 5. Recommended workflow

1. Write `Tools/Venues/make_backyard.py` (new; keep `make_backyard_greybox.py` untouched). It uses `venuegen.py` (deterministic: same seed, same bytes) and reads `Art/Venues/Backyard/layout.json` for props, band spots, crowd, lights and cameras where that is suitable. Where layout.json cannot be used as is (circular crowd exclusions, FX), do the adapter in Python and say what you changed.
2. Move or copy the finished props from `Art/Venues/Backyard/Models/` into `Assets/Venues/Backyard/Models/` (venue-specific) or `Assets/Models/Venue/` (shared with other venues; existing props already live there and stay referenced from there). Keep one copy of each atlas texture (`PolygonTown_01_A.png`) rather than the three your package has; point the MTLs/materials at the single copy.
3. Add a provenance README (`Assets/Venues/Backyard/Models/README.md`, in the style of `Assets/Models/Venue/README.md`): every model, its source pack and original file, transforms applied, licence.
4. Generate `Assets/Venues/Backyard/Backyard.lvl` (and keep `venue.json` valid: Name, Author, Scene "Backyard.lvl", Version incremented to 2).
5. Iterate with the checker and headless previews until it reads well.

## 6. Rules

You may write only: `Assets/Venues/Backyard/`, `Tools/Venues/make_backyard*.py` (never edit `make_backyard_greybox.py`), and `Art/Venues/Backyard/`. Do NOT touch `Game/`, `Engine/`, any other `Assets/` folder, `Settings.json`, or anything in `Docs/` (write notes in `Art/Venues/Backyard/` instead). Git: no commit, no stash, no reset, no checkout, no add; the checkout has the owner's uncommitted work and the owner reviews and commits. Do not build the game.

Licence bar: Drumsmith is a free, GPL, non-profit game that teaches real drums. CC0, CC-BY and CC-BY-NC are fine with attribution; anything with an unclear or commercial-only licence is not. Record every source (pack, file, licence, URL or "owner-owned Synty") in the provenance README. No third-party logos, brands, film characters or likenesses.

## 7. Verification (do this before you report)

```
python3 Tools/Venues/check_venue.py Assets/Venues/Backyard
```
It must pass with no errors.

Then four headless shots from the repo root (use `/tmp/drumsmith-baseline-sandbox` as the working directory if track indexes look wrong; the game binary is `./.build/Game_linux_Debug/Game_EntryPoint_x64`; do not rebuild it; if it is missing or stale, stop and tell me):
```
flock /tmp/drumsmith-build.lock env HEADLESS_DISPLAY=:97 ./Engine/Tools/NixEnv.sh env -u NIX_CC ./Engine/Tools/Headless.sh ./.build/Game_linux_Debug/Game_EntryPoint_x64 --scene Assets/Example.lvl --play-track 0 --frames 60 --frame-time 0.016666667 --no-audio --venue-only --venue Backyard --venue-time 60 <shot flags> --screenshot <out>.png --exit
```
Shots (save to `Art/Venues/Backyard/Previews/Game/`):
1. wide: `--venue-eye "-1,3.3,-21.5,0,1.75,2.2,58"` (your C01)
2. drummer close: `--venue-eye "0,2.45,7.15,0,1.35,-5,66"` (your C03), or a close director shot
3. peak: add `--venue-moment 5` and `--venue-time 62` with the wide eye
4. one directed shot: no `--venue-eye`, let the director cut (e.g. `--venue-shot cam_crane`) and look at the log with `--highway-log` that a Wide spot was used

Look at each image. If the venue does not load, read the log for lines starting `[Venues]` (they say why). Fix and re-shoot.

## 8. Report

When done, reply with: the files you created or changed; the K you chose for intensities and why; what from DESIGN/ASSETS/LIGHTING/CAMERAS you could not honour and why; anything over a budget; the licence/provenance status; the four preview paths with one sentence each on what is wrong with them; and a list of anything that needs a cook or a framework change. Do not claim it looks good on a real GPU: it was judged from software-rendered headless images only.
````

## Conflicts to expect (for the owner)

- GPT's light levels are relative (1.0 = neutral key) and its cones are described as full outer angles; the engine takes absolute intensities (hundreds to thousands) and half-angle cones (halve GPT's full outer angles). The prompt has GPT calibrate against the greybox.
- The five spotlight order in GPT's plan is drums, guitar, bass, vocals, keys; the game's follow-spot order is drummer, singer, guitar, bass, keys.
- No effect emitter markers exist, so FX.md's emitter map cannot be built; only `BuildFx` at the built-in positions.
- Crowd rectangles C1-C3 carry circular exclusions; the framework has no exclusions.
- GPT specifies absolute fog density (0.007 to 0.012); the framework has only `Haze` and `FogColor`. Exposure is fixed.
- C10's up vector (0,0,-1) and the 00:40 time need checking (time is fine as 0.67).
- 31 models ship three copies of the Town atlas; the prompt asks for one.
