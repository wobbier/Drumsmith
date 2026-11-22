# Venue Authoring

> Verified against game commit 6840e53 (the venue scene commits DRU-57 to DRU-61), 2026-11-17. Headless (lavapipe) captures only. Engine submodule as pinned in that commit.

A venue is the room the band plays in: the stage, the crowd's floor, the lights and the camera positions. Since 2026-11-17 a venue can be a **scene**, an ordinary Havana level (`.lvl`) with a handful of marker components that say where the game puts things. This guide is for modders and artists making one. How the show behaves once a venue exists (band, crowd, hype, cameras) is in `Docs/Venue-and-Band.md`; the light cues are in `Docs/Stage-Lighting.md`.

## What a venue is

A venue is a folder with two files:

- `venue.json`: the catalogue entry. Keys: `Name` (shown in the menu), `Author`, `Scene` (the `.lvl` file name in the same folder), `Version`, and optionally `Preview` (an image in the folder), `Hidden` (true keeps it in the registry but out of the menu; the Template is hidden) and the ambience keys below.
- the scene `.lvl`: the geometry, lights and markers.

**Ambience.** A venue can play a sound while a song loads and counts in, a crowd waiting for the band, which eases out over the song's first seconds:

| Key | Default | Meaning |
|-----|---------|---------|
| `Ambience` | none | The sound: a file in the venue's folder, or an `Assets/` path for one venues share (the Backyard's is `Assets/Sounds/crowd.mp3`). Streamed and looped, and started from a random point each play, so a long recording gives variety. |
| `AmbienceVolume` | 1 | 0 to 1. |
| `AmbienceFade` | 8 | Seconds from the song's start to silence. |

It plays in a game (and Play in Havana), not in the Track Editor's preview, and pauses with the pause menu. Only scene venues have one; the three built-in rooms have none. `check_venue.py` checks the file exists. Code: `VenueAmbience` (`VenueRegistry.h`), `VenueShow::StartAmbience` / `UpdateAmbience`, and `Docs/Audio.md` → Venue ambience.

The three built-in rooms (Arena, Club, Festival) are not scenes: they are procedural, built from `VenuePlan::ForStyle(0..2)` (`Game/Source/Venue/VenuePlan.h`). A scene venue goes through the same pipeline: the loader (`VenueScene`) reads the markers into a `VenuePlan`, and the show code builds the band, crowd, lights and screens from that plan, so a scene venue is not a second code path for the show.

## Where venues live

| Place | Id | Notes |
|-------|----|-------|
| `Assets/Venues/<Id>/venue.json` | the folder name, e.g. `Backyard` | Shipped venues. Read through the virtual file system. |
| `<song folder>/Venue/venue.json` | `song:<folder>` | A venue that belongs to one song. |
| A mod's `Assets/Venues/<Id>/` | the folder name | Mods overlay `Assets/...`; see `Engine/Docs/Modding.md`. |

`VenueRegistry` (`Game/Source/Venue/VenueRegistry.h`) scans these. A folder with bad JSON or a missing scene is skipped with a log line, not an error.

## How a venue is chosen

`ChooseVenue` / `ChooseForSong` apply these rules in order and the first that gives a venue wins. The rule is logged once per build.

1. `--venue <value>`: a registry id, `Arena` / `Club` / `Festival`, or a path to a `.lvl`.
2. `--venue-style N`: a built-in room.
2a. The gig being played's venue (`Docs/Hideout-and-Progression.md` → Gigs).
3. If the **Song Venues** setting (`SongVenues`, default on) is on: the song's `Venue` field in `TrackData.txt` (a venue id or a room name), then the song's own `Venue/` folder.
4. The player's pick in Settings (`VenueId`, set from the menu's Venue tab).
5. The `VenueStyle` setting (Arena / Club / Festival / Random), as before.

Rules 4 and 5 only pick venues free play has unlocked (`Progression::VenueOpen`, `Docs/Hideout-and-Progression.md` → Venues in free play): a locked pick falls back to an open room, else the first open scene venue.

F7 and `--venue-swap-every` cycle Arena, Club, Festival, then each non-hidden scene venue, then back to Arena; an F7 pick wins over `--venue-style`.

## Units and axes

Everything is in metres, in **venue space**: positions are relative to the venue scene's root (the game parents the scene under the venue root at `VenueLayout::kVenueOrigin`, so author as if the venue sat at the origin).

- **+x** is the crowd's right.
- **+y** is up. The floor of the main crowd is usually y = 0.
- **+z** runs from the crowd toward the band and the back wall.
- The crowd faces +z. The band faces -z, back at the crowd.

```
            back wall / house            +z
   ------------------------------        ^
   |  Keys     Drums(riser)       |      |
   |       Guitar      Bass       |      |
   |            Vocals            |      |
   |------------ stage edge ------|      |
   |   crowd areas (face +z) ...  |      |
   |                              |      |
   |           desk (DeskZ)       |      |
   ------------------------------        |
   <-- -x         0         +x -->     (z = 0 near the front of the stage)
```

Each marker's position, rotation and scale come from its entity's Transform. Rotation is Euler degrees. A camera, a Light and a `VenueCameraSpot` look along local +Z (positive X rotation pitches down); a `VenueSpot` performer faces local -Z; a `VenueCrowdArea` faces local +Z. A fresh entity with identity rotation therefore already faces the right way for a spot (the crowd), an area (the band) and a screen (the crowd).

## The markers

All six are in Havana's Add Component menu under **Venue**. They are reflected components, so the inspector and the `.lvl` serialization come for free. Source: `Game/Source/Components/Venue/VenueMarkers.h`.

A scene with **no `VenueInfo` or no Drummer `VenueSpot` is not a venue**: the game logs why and uses the room it would otherwise have picked.

### VenueInfo (exactly one, required)

Names the venue and describes the room the director and lights work in (the numbers mirror `Director::Room`).

| Field | Default | Meaning |
|-------|---------|---------|
| `Name`, `Author` | | Free text. |
| `Outdoor` | false | Out of doors: sky, moon and the thinner haze. |
| `RoomBack` | -1000 | z of the back wall behind the crowd (the crowd side). The default means no wall. |
| `RoomCeiling` | 1000 | y of the ceiling. The default means none. |
| `RoomHalfWidth` | 30 | Half the room's width. |
| `DeskZ` | -22 | z of the sound desk: where the crowd's far edge and the Desk camera sit. |
| `BuildStage`, `BuildSet`, `BuildRig`, `BuildFx` | false | Also add the built-in stage deck, set dressing, light rig, or effects. Each switch defaults to false. `BuildFx` adds the stock effects at their standard positions. For an authored burst at a specific prop, add a `VenueAccent`. |
| `AmbientColor` | black | Indoors: the colour the camera clears to; also lights the room a little (black leaves a faint grey base). |
| `FogColor` | (0.01, 0.01, 0.015) | The light the haze scatters; lifts whatever is far off. |
| `Haze` | 1 | How thick the haze hangs (1 the usual; outdoors it is already under half that). |
| `SkyTime` | 22 | Outdoors: the night sky's hour, 0 to 24 (20 is dusk). The greybox Backyard uses 21. |
| `MoonBrightness` | 1 | Outdoors: the moon's brightness. |

### VenueSpot (the Drummer required, the rest optional)

`Member` is `Drummer`, `Guitar`, `Bass`, `Vocals` or `Keys`. The position is the performer's **feet** (so a raised riser's spot has the riser's top as its y). The performer faces local -Z; yaw the entity to turn them. A member with no spot is absent from the band. The drum kit arrives as one unit at the Drummer spot, about 2.5 m wide and 2 m deep in front of the throne; plan clearance for it. The instrument, mic stand, follow spot and the director's shots of that member go with the spot.

### VenueCrowdArea

A floor rectangle the crowd fills. Position is the centre and its y is the floor height (a roof or a rise works). Scale x and z are the full width and depth in metres (y is ignored). Faces local +Z, so identity faces the band.

| Field | Default | Meaning |
|-------|---------|---------|
| `Figures` | Mob | `Mob`: the cheap instanced figures (bob, jump, hands and lights up), for the back. `Posed`: the full figures the built-in rooms put in their front rows, each with its own moves, cheers, phones and lighters, and the crowd surfer (behind the first posed area's front rows). Posed figures cost more: keep them to the people near the stage (the Backyard's three front knots are 85). |
| `HeadCount` | 60 | People at a full house. |
| `DanceFloor` | false | On posed areas, alternate beat-timed jumps across the combined dance floor during loud sections and crowd lifts. Every fourth four-beat bar brings both sides up together. |
| `Jitter` | 0.5 | Spread from the grid position as a fraction of the spacing: 0 a neat grid, 1 a loose mob, 0.5 normal. |

A posed area fills the whole rectangle in rows from its +Z edge back (in venue space), so face posed areas at the stage; `Jitter` is for mobs only. A rotated area uses its axis-aligned bounds. Rectangles cannot have holes: lay several rectangles around a pool or a prop instead of excluding it.

### VenueCameraSpot

A position the director can cut to. Position is the eye; it looks along local +Z (use `look_rotation` in `Tools/Venues/venuegen.py`, or aim it in Havana).

| Field | Default | Meaning |
|-------|---------|---------|
| `Shot` | Wide | `Wide` replaces the director's band-wide shot, `Crane` its crane move, `Desk` its long-lens shot. `Close` and `Custom` become extra cuts (about 25% of the time) of the member they point at. |
| `FieldOfView` | 55 | Vertical degrees. |
| `Tag` | | Free text to tell Custom shots apart. `arrival/01`, `arrival/02`, ... on `Custom` spots make the venue's intro instead: at the start of a song, a handheld fisheye walk through the marks in tag order (1.05 s apart), then the operator stops and crash-zooms onto the band (overshoot, pull back, hold) before the director takes over. A seek past the start skips it. |

Custom shots tagged `peak/01`, `peak/02` and so on share a venue accent in tag order. With two shots the director switches halfway through. The intro, guitar-neck and crowd-surfer shots retain their usual priority.

### VenueAccent

Attach this marker to a `Sequence`, a `ParticleSystem`, or both. The show starts these cues together on a chorus, a qualifying player streak, or sustained high crowd energy. A long intense passage can start another performance after 32 beats.

| Field | Default | Meaning |
|-------|---------|---------|
| `Beats` | 12 | Duration on the chart tempo map, from 1 to 32 beats. The longest cue determines how long the peak cameras cover the event. Use matching rest poses at the first and last keys and turn off sequence autoplay and looping. |
| `Particles` | 0 | Number of particles on a major peak, up to 512. An ordinary lift uses half this count. Set the particle system’s automatic emission and startup burst to zero for isolated hits. |
| `FullLightingOnly` | false | Holds this sequence at its first key with gentle or disabled stage lighting. Keep lamp tracks on a separate marked entity when people or props should animate at every lighting setting. |

### VenueScreen

A screen that shows a feed. The entity's scale x and y are the quad's width and height in metres; the picture faces local -Z (the same way a spot faces, so identity already faces the crowd). **The game creates the quad: author only a frame** (a box or a model around it), and keep your own geometry out of the quad's volume.

| Field | Default | Meaning |
|-------|---------|---------|
| `Source` | Stage | `Stage` (the stage camera feed), `Program` (what the audience-facing director is cutting), `Lyrics` (the lyric band there; ignores yaw for now). |
| `Emissive` | 2 | HDR multiplier on the picture's light. |

### VenueShowLight

Put it on an entity that **also has an engine `Light`**; the Light still supplies type, colour, cone and range. `Kind` and `Group` decide how the show cues it.

| Kind | Behaviour |
|------|-----------|
| `Wash` | Cued colour and level. The group maps to a wash row (`group % 3`); lights in the same group are cued together. The colour shown is the cue colour mixed 30% with the authored colour. |
| `Beam` | Sways about its authored aim (pan up to 30 degrees, tilt up to 12). |
| `Spot` | A follow spot on a member: the drummer first, then the singer, guitar, bass, keys. Never below 35%. |
| `Blinder` | A low glow that flashes on peaks. |
| `Strobe` | Strobe cues, peaks and full hype; odd and even groups alternate. |
| `Static` | Never touched by the show (a moon, practicals, a house's windows). |

`Group` is any int; 0 is the default.

**Intensity units.** The authored `Intensity` is the light's level at full, in engine units, not a 0 to 1 ratio. A point or spot falls off roughly as intensity / d^2, so a few hundred lights a band from 3 to 4 m. The Template uses 1,200 for its spot washes and 80 for a point key; the greybox Backyard spans 40 to 150,000 (a directional moon and long-throw lamps). Cone angles are the engine `Light`'s `InnerConeAngle` / `OuterConeAngle`, both **half-angles** in degrees (0 to 89): full intensity inside the inner, none outside the outer.

**Budgets.** At most **one shadow-casting light**, which should be a directional one; with no directional light in the scene the game adds a key light. Keep `VenueShowLight` entities to **40 or fewer**.

### VenueStory (story mode)

Story mode (`Docs/Hideout-and-Progression.md` → Story mode) plays five songs at one venue, and the venue changes as they go: each song sets some flags (`Design/Story-Mode-Setlists.json`, each song's `StateAfter`). A `VenueStory` marker shows its entity and children only while its flag is set, or with `WhenSet` off only until it is set (the dessert table against the wall; the dessert table in the middle of the floor). The flags of the songs before the one playing are set from its start; the song's own flags land at its **cue** (its `Cue.On`: `intro`, `verse`, `first_chorus`, `bridge`, `solo`, `outro`, `song_end`), found in the chart's sections, else at a share of the song (2%, 15%, 30%, 60%, 55%, 85%, the end). A song can also carry **moments** (`ProgressionStorySong::Moments`), more flags each landing at their own cue. Besides the names above, a cue (`VenueShow::StoryCueTime`) can be `section:<name>` (the first chart section with that in its name), `at:<share>` (a share of the song, 0 to 1), `time:<seconds>`, `drums_in` (the first note), `last_note` or `start`, and any cue can be moved by seconds: `last_note+2`, `section:chorus_3+12`. It grows in or shrinks away over `FadeSeconds` from the entity's pivot, and the plain `Light`s under it dim with it. A `VenueShowLight` under it is still cued by the rig, and dimmed with the group after the cue is applied (`VenueShow::DimStoryShowLights`): that is how a venue with several places in it (Hell's crash site, shaft and cavern) gives each its own rig. A `ParticleSystem` under it emits only while every story group above it is shown, and starts over when they show, so a one-shot `BurstCount` goes off as its flag lands (a hidden group is only scaled away, which would otherwise leave its fire burning at the pivot); a system with a `VenueAccent` stays the show's.

| Field | Default | Meaning |
|-------|---------|---------|
| `Flag` | | The story flag. |
| `WhenSet` | true | Shown once set; false: shown until set. |
| `FadeSeconds` | 0.75 | Grow/shrink time (0 pops). |
| `Mode` | Show | `Show`: shown or hidden by the flag, as above. `Play`: always shown; the `Sequence`s on it and under it (author them with `PlayOnStart` off) play once when the flag lands, and a flag already set when the song starts (or a seek past it) leaves them at their end; a seek back before it, at their start. A `Sequence` under it that has `PlayOnStart` on (a looping road, beating wings) is left running. `SlowMotion`: always shown; the `Sequence`s under it run at `Speed` until the flag lands, then at full speed. |
| `Speed` | 0.3 | `SlowMotion`'s speed before the flag. |

**The band.** Flags starting `band_` move the live band rather than props (`VenueShow::UpdateStoryBand`, `Band::SetStoryState`): `band_ghost` turns them see-through and glowing pale blue over two seconds; the poses `band_down` (on their backs at their marks), `band_falling` (tumbling, settling back over about ten seconds), `band_floating`, `band_rising` (lifted off the floor and away), `band_hidden` and `band_playing` (back at their marks) hold the band from when they land, the latest landed winning and blended in from the one before over 2.5 s (into or out of `band_hidden` pops). They never carry over to the next song of a set (`GigSession::StageStory`): each song sets its own.

**Captions.** A story moment with a `Caption` shows that line over the highway for `CaptionSeconds` (4 by default) from its cue (`VenueShow::StoryCaption`, the HUD's `story_caption`).

**Story shots.** A `Custom` `VenueCameraSpot` tagged `story/<flag>` is the shot the director cuts to when that flag lands during the song (not when it was already set at the start), over every other shot, the arrival intro included (`Director::SetStoryShots`). More of the tag, separated by `/`: a number is how long it holds (5 s without one), `hand` shoots it handheld. A second spot tagged `story/<flag>/end` is where the shot moves to over the hold (eased): a pull back, a crash zoom. Spots tagged `story/<flag>/w1`, `/w2`, ... are passed through on the way, in order, on a smooth curve (a crane up the stairs, a zoom that overshoots and comes back). `f<metres>` on the first spot or the end (`story/ascent/14/f0.46`) pulls focus to that distance and softens everything off it; when the two differ the focus racks from one to the other. Story spots are never used for the director's ordinary cuts. `--venue-shot spot:<tag>` holds one to frame it.

`venuegen.Scene.story( name, parent, flag, when_set, fade, pos )` makes the group; put the props under it. Crowd areas, spots and cameras can't be gated (the show builds those once). To preview a story state headlessly add `--story <set id> --story-song N` (1-based; the songs before N have happened) and `--story-cue-at <seconds>` to move the song's cue (0: already landed). The log says `[Venues] story: P props, set ... song N, F flags set, C at the cue (...)`. In a game, `--gig <set id> --story-song N` plays that song of the set, and in non-Retail builds the gig board has DEBUG: PLAY SONG 1-5 buttons on each story set.

## What the loader strips

`VenueScene` reads the scene (`SceneStreaming::ReadScene`), remaps asset references (so mods resolve), strips unsafe content, deserializes it under the venue root with GUIDs remapped and no cores, then collects the markers into a plan. Stripped, with a logged count:

| Stripped | Why |
|----------|-----|
| Scene Cores | The game owns the cores; a venue is data, not systems. |
| `ScriptComponent` | A mod scene must not run code on load. |
| `UIDocument` | The game owns the UI. |
| `Camera` (and `PostProcess`, `FlyingCamera`, `CameraSway` on that entity) | The director owns cameras; use `VenueCameraSpot`. |
| `AudioListener` | The game already has one. |

`Tools/Venues/check_venue.py` flags all of these as errors.

## Fallbacks

- No `VenueInfo` or no Drummer spot: not a venue; the game uses the procedural room it would have picked.
- A missing optional spot (guitar, bass, vocals, keys): that member is absent.
- A shot kind with no camera spot keeps the director's own shot (a `Wide` spot replaces only the wide, and so on).
- No crowd areas: the plan has no crowd to build.
- No directional light: the game adds a key light. More than one shadowed light is not supported.
- A missing model or texture is the engine's usual asset failure (logged); `check_venue.py` catches the path first.
- Bad `venue.json` or missing scene: the folder is skipped with a log line.

## Two ways to author

### In Havana

1. Create a folder `Assets/Venues/<Id>/` with a `venue.json` (copy the Template's).
2. Make a new level and save it there as the scene named in `venue.json`.
3. Build the room from meshes and models; add `Light` components and lights.
4. Add the markers: create entities and use **Add Component, Venue** for `VenueInfo` (one), `VenueSpot` (Drummer at least), `VenueCrowdArea`, `VenueCameraSpot`, `VenueScreen`, and `VenueShowLight` beside each cued light's `Light`.
5. Run `python3 Tools/Venues/check_venue.py Assets/Venues/<Id>`, then preview it (below).

### From Python

`Tools/Venues/venuegen.py` is a small standard-library writer for the scene format. It is deterministic (GUIDs come from a seed and creation order, so rerunning gives the same bytes), which is what you want for a scene that is regenerated rather than hand-edited. Its `Scene` has `group`, `box` / `slab` (a cube is 2 m at scale 1; `box` takes metres), `prop` (a `Model`), `light`, `info`, `spot`, `crowd`, `camera_spot`, `screen`, and `write`; `write_venue_json` writes the catalogue file. A minimum, after `Tools/Venues/make_template.py`:

```python
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from venuegen import Scene, repo_root, write_venue_json

s = Scene(seed=2001)
root = s.group("My Venue")
marks = s.group("Markers", root)
s.slab("Floor", root, -12, 12, -0.2, 0.0, -16, 11, (0.3, 0.3, 0.33))
s.light("Wash", root, (0, 6, 1), "Spot", (0.4, 0.5, 1.0), 1200.0, 16, rot=(70, 0, 0),
        inner=25, outer=45, show="Wash", group=0)
s.info(marks, "My Venue", "Me", room_back=-16, room_ceiling=7, half_width=12, desk_z=-13)
s.spot(marks, "Drummer", (0, 0.5, 6.0))
s.crowd("Crowd", marks, (0, 0, -8.5), 14, 9, 60)
folder = os.path.join(repo_root(), "Assets", "Venues", "MyVenue")
os.makedirs(folder, exist_ok=True)
s.write(os.path.join(folder, "MyVenue.lvl"))
write_venue_json(folder, "My Venue", "MyVenue.lvl", author="Me")
```

`make_template.py` and `make_backyard_greybox.py` are the working examples; keep the generator beside the venue so the scene can be rebuilt.

## The Template

`Assets/Venues/Template/` is the smallest valid venue and the place to start: a floor, a back wall, a 0.5 m stage with a raised drummer platform, all five spots, one crowd area, a camera spot, two cued washes and a static key light. It is `Hidden`, so it is loadable with `--venue Template` but not in the menu. Copy the folder, rename it, rename the `.lvl`, edit `venue.json`, and open it in Havana. `make_template.py` regenerates it.

## Checking and previewing

```bash
python3 Tools/Venues/check_venue.py Assets/Venues/<Id>
```

`check_venue.py` checks `venue.json` and the scene file, scene format v2, unique GUIDs, parents existing and listed before their children, registered component names, that asset paths exist, exactly one `VenueInfo` and one Drummer spot, at most one shadowed light, at most 40 show lights, `VenueShowLight` only on an entity with a `Light`, and no current Camera, scripts, UI documents or Cores. It exits 1 on errors; warnings do not fail.

To see it, run the game headless from the repo root (this uses the DLC sandbox so `--play-track 0` is a known song; run it from `/tmp/drumsmith-baseline-sandbox` for a stable track index):

```bash
flock /tmp/drumsmith-build.lock env HEADLESS_DISPLAY=:97 ./Engine/Tools/NixEnv.sh env -u NIX_CC \
  ./Engine/Tools/Headless.sh ./.build/Game_linux_Debug/Game_EntryPoint_x64 \
  --scene Assets/Example.lvl --play-track 0 --frames 60 --frame-time 0.016666667 --no-audio \
  --venue-only --venue <Id> --venue-time 60 \
  [--venue-eye "x,y,z,tx,ty,tz,fov"] [--venue-moment 5] [--venue-shot <name>] [--highway-log] \
  --screenshot out.png --exit
```

`--venue-eye` puts the camera anywhere in venue space to inspect the set; `--venue-moment 5` fires a peak every 5 seconds so the effects and strobes show; `--venue-shot` holds a director shot. On a desktop, just run the game with `--venue <Id> --play-track N`. The other venue flags are listed in `Docs/Venue-and-Band.md` → Settings and flags; `--venue-plan-test` is a dev flag that moves the drummer to the bass spot turned 215 degrees and drops the bass and keys.

### Previewing in Havana

Two ways, both in the editor build (`.build/Editor_Debug/Havana`):

- **Play the venue scene itself.** Open the venue's `.lvl` and press Play. If the scene has a `VenueInfo`, `VenuePreviewCore` (added by the Track Editor widget whenever a scene loads, and never saved into the scene) builds the band, crowd, director cameras and cued lights around the open scene in place, playing to a demo chart (the first library song with a chart, else a built-in rock beat) on a loop. Stop puts the scene back. The Cores inspector shows "Playing to: ..." or why the scene isn't a venue. In this mode there is no highway, so F7 does nothing, and there is no audio.
- **The Track Editor's preview.** With a song open, the toolbar after the Game Preview (eye) button and the Both/Highway/Scene combo has a venue combo: the song's own pick (the default), Arena/Club/Festival, every registry venue (hidden ones marked), the song's own venue folder, and the open scene. A running preview rebuilds at once. **Reload Venue** (the refresh icon) rescans `Assets/Venues` and re-reads the `.lvl` and `venue.json` from disk, so a scene saved in Havana or regenerated by a script shows on the next click. Models and textures already loaded stay cached until the editor restarts. On a narrow window the combo can be clipped off the end of the toolbar.

Editor flows drive both: `track-preview-venue <id|room|path|song>`, `track-preview-reload-venue`, `track-assert-preview-venue <text>` and `track-assert-venue-play <0|1>`; see `Assets/Scenes/Tests/TrackEditorVenueFlows.edscript` and `VenuePlayFlows.edscript` (run with `Engine/Tools/RunEditorFlows.py --editor .build/Editor_Debug/Havana --wrapper Engine/Tools/Headless.sh --only TrackEditor` or `--only VenuePlay`).

A fixed-step venue reel can use `--venue-only --venue-capture-from 38.8 --frame-time .04`. The venue starts at that chart time and advances one simulation step per frame, including when software rendering runs slower than audio playback.

## Shipping: cooking

Retail builds never cook assets. A shipped venue, and any mod, must carry the compiled twins next to its sources: `.dds` for textures and `.assbin` for models. Run a tools build or Havana's Build Assets once and ship the results. Without them a venue works in a development build and renders without its models or textures in a Retail one. See `Engine/Docs/Cooking.md` and `Engine/Docs/Modding.md`. Models that are shared between venues belong in `Assets/Models/Venue/`, with a provenance README like that folder's (source pack, original file, licence).

## Known gaps

As of 6840e53:

- `--crowd-size` does not scale a scene's mob areas, and a posed area always fills from its +Z edge, whichever way it faces.
- The Lyrics screen ignores yaw. Director shot offsets for non-drummer members do not turn with the member's yaw, and the scene stage's shot offset is translation only. Exposure is fixed.
- Directed shots of non-drummer members in the Backyard are under-lit.
- The riser dressing (when `BuildSet` is on) stays at x = 0.
- No marker sets the sky's colours, fog density in absolute terms, or lyrics screens beyond one band.
- Nothing has been seen on a real GPU or in motion at speed, and Win64 and macOS have not been built.
- Venue packs cannot come from the DLC server (it needs an index type and an install path).
- Crowd rectangles cannot have holes.
- The fog is distance fog at a fixed density (`Director` sets 0.012 a metre): nothing shows past about 150 m, whatever `Haze` is, so a sky has to be a dome inside that with its light turned up (StoryHeaven's is 125 m). A see-through surface fogs itself, so an additive glow card far off in a bright-fog venue shows as a square: use an emissive mesh there.
- A venue's own meshes (`Tools/Venues/story_afterlife_mesh.py` is the newest writer): in the OBJ, v = 1 is the image's top row, and a card facing +z seen from in front has +x on the left. A `Model`'s part override takes a whole `StandardMaterial`.
- The renderer reserves room for 1,024 see-through meshes a view (`BGFXRenderer::kMeshTransparencyTempSize`); a debug build asserts past it.

## Key Files

- `Game/Source/Components/Venue/VenueMarkers.h`: the six markers
- `Game/Source/Venue/VenuePlan.h`: the plan a scene is read into
- `Game/Source/Venue/VenueScene.h`: the loader
- `Game/Source/Venue/VenueRegistry.h`: discovery and the choice order
- `Game/Source/Venue/VenueShow.h`: the show that builds from the plan
- `Tools/Venues/venuegen.py`: the generator library
- `Tools/Venues/check_venue.py`: the checker
- `Assets/Venues/Template/venue.json`: the starting point

## Related Docs

- `Docs/Venue-and-Band.md`: how the show behaves
- `Docs/Stage-Lighting.md`: light cues
- `Docs/Venues/Backyard-GPT-Go.md`: the brief for building the real Backyard
- `Engine/Docs/Modding.md`: the mod overlay
- `Engine/Docs/Cooking.md`: compiled twins
