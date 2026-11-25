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
| `CloudCoverage` | 0.25 | Outdoors: how much of the sky is cloud. 0 runs no cloud pass, which saves about 0.24 ms at 5120x1440 on an RTX 4090. At night the clouds light almost nothing and only hide stars. The Backyard uses 0. |
| `HazeFroxels` | false | Light the show's haze from the froxel grid (compute) instead of the per-pixel march. On the Backyard at 5120x1440 on an RTX 4090 the frame went from 5.3 to 3.1 ms (RenderDoc-serialised), and the haze looked nearly the same (RMSE 0.004; the glow under the canopy is a little softer and wider). Narrow beams come out softer, so it suits an outdoor haze more than a club full of crisp beams. Backends without compute fall back to the march. The Backyard uses it. |
| `Footage` | Broadcast | Who filmed the live show. `Broadcast`: the director's crew. `Camcorder`, `Phone` or `Mixed`: only the guests, from the `guest/` camera spots, on 2000s camcorders, flip phones or both (`Docs/Venue-and-Band.md`, Found footage). The music video always has the real cameras. The Backyard is `Mixed`. |
| `Ride` / `RideUntil` | 0 / empty | The venue is on the move (a stage on a truck at speed). Every camera rattles with the road, heaves and leans on its suspension and takes a bump about once a second, this hard (1: a fast highway), until the story flag `RideUntil` is set (empty: always). Aerial (`heli`) story shots are left out (`Director::SetRide`). |
| `KeepRed` / `KeepBlue` / `KeepWarmth` | 0 | What a look that takes the colour out (the black and white concert look, sepia) leaves in colour in this venue: how much of the reds and blues, and how far the reds reach into orange and yellow (0 pure red, 1 fire). Hell keeps its reds (`Director::SetColorKeep`, the engine's `SaturationKeep*`). |
| `LightsFrom` / `LightsUntil` | empty | Story flags between which every look keeps reds, blues and fire together: the police lights and the burning rig at a crash. Either may be empty (from the start, to the end). |
| `QuietLook` | true | A chart with no looks of its own plays its intro, bridges and breakdowns in the black and white concert look (`Director::BuildFallbackLooks`). Off: this venue stays in colour through them. The three afterlife venues turn it off: black and white with the police lights and the fire let through looked bad on Free Bird's opening. A chart's own looks still play. |

### VenueSpot (the Drummer required, the rest optional)

`Member` is `Drummer`, `Guitar`, `Bass`, `Vocals` or `Keys`. The position is the performer's **feet** (so a raised riser's spot has the riser's top as its y). The performer faces local -Z; yaw the entity to turn them. A member with no spot is absent from the band. The drum kit arrives as one unit at the Drummer spot, about 2.5 m wide and 2 m deep in front of the throne; plan clearance for it. The instrument, mic stand, follow spot and the director's shots of that member go with the spot.

For a seated guitarist, bassist or singer, set `SeatHeight` on the spot to the height of the hip joints above its feet, in metres. The player stays on that mark through solos and vocal gaps. String players keep their instruments, and the singer uses a handheld mic and reaches forward with the other hand. These marks omit the standing backline.

`PowerStance` plants a standing guitarist or bassist wide (feet well apart, knees bent and dipping on the beat, leaning back into it) and keeps them on their mark through solos: for a spot with nowhere to walk, like Kickstart's guitarist on the truck's roof. `Gear` off leaves out the amp, wedges and mic stand of a stage spot (only the player and what they hold).

**A spot that moves.** A spot under something that moves (a looping clip, a story clip) carries its member with it: the body, the instrument and the kit or amp go where the marker is each frame and turn with it (`VenueShow::CarrySpots`, `Band::Carry`). The body rides it on a spring: when the marker jolts, the member is a moment behind, thrown a little up off it and swayed against the lurch, and comes back (the drummer half as much, over a kit that stays put). Kickstart's rig works this way: the drummer's spot is on the trailer, which swings on the tractor's fifth wheel, and the others are on the tractor; both bodies bounce over road bumps and the jump's landing on clips of their own. Spots that never move cost nothing: they are left to the plan.

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
| `Tag` | | Free text to tell Custom shots apart. `own/<name>` on a `Close` spot aimed at a member: that member's close cuts (the director's near, behind, head, hands, side, hero and push framings, and a close one of nobody in particular) all come from their `own/` spots in turn (`Director::KeepToOwnSpots`), for a member the director's framings can't reach, which are placed for a stage from the crowd's side (Kickstart's singer at the wheel and bassist at the passenger window, boxed into the cab). `arrival/01`, `arrival/02`, ... on `Custom` spots make the venue's intro instead: at the start of a song, a handheld fisheye walk through the marks in tag order (1.05 s apart), then the operator stops and crash-zooms onto the band (overshoot, pull back, hold) before the director takes over. A seek past the start skips it. |

Spots tagged `guest/<name>` (any `Shot`, usually `Custom`) are the guests' cameras in a found-footage venue (`VenueInfo.Footage`), and the only places its live show is filmed from. Broadcast venues and the music video never cut to them. Put them where someone at the party would stand with a camera, at the height they'd hold it (about 1.6 m, nearer 2 m held up over heads, 1 m sat down), aimed at what they'd film; crowds, posts and other people in the way are part of the look. Add `@dv` or `@phone` to the tag to pick the device (`guest/sofa@phone`); without it a Mixed venue picks one from the tag. Camcorders zoom (narrower than the spot's field of view, never wider than 1.25 times it), so give them a fairly wide one. Check each with `--venue-shot spot:guest/<name>` (the whole tag). The Backyard has ten (`GUESTS` in `Tools/Venues/make_backyard.py`).

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

### VenueBeat

Moves its entity with the song's beat (`VenueShow::UpdateBeats`), for dressing that should feel the music: figures baked into a mesh, a lamp on a chain. The entity's own position is where it rests; put it on a parent that does any other moving. It works in any venue, story or not.

| Field | Default | Meaning |
|-------|---------|---------|
| `Offset` | (0, -0.08, 0) | Where it is at the peak of each move, from rest, in metres in its parent's space. |
| `Every` | 1 | One move every this many beats. |
| `Phase` | 0 | How many beats late it starts (0.5: the off-beat). |
| `Sway` | false | Off: out on the beat and easing back, like a nod. On: smoothly to `Offset` and to its opposite. |
| `Sharp` | false | Out at once on the beat and straight back, with no gathering before the next: a blip. A heart monitor's spike stands just behind its screen and comes through it on the beat (My Hero's ambulance and ward). |
| `Turn` | (0, 0, 0) | How far it is turned at the peak of the move, in degrees about its own origin, on top of its own rotation: a cage swinging from its chain (the pivot at the top of the chain, `Sway` on), a tree lashing from its root, a shove leaning in. With `Offset` the two go together. |
| `Nod` | 0 | Degrees: a `VenueFigure` on the same entity nods its head this far at the peak of each move, on top of its own `Nod` (set `Offset` to zero to keep the figure where it is). The highway's cops bang their heads to the band this way (`make_story_afterlife.head_bang`). |
| `Calm` | 1 | How much of the move is left while the player plays at their worst (`VenueShow::Mood`, below): 1 the same whatever the playing, 0.2 a wallflower who hardly moves unless the drums are right. |
| `Trigger` | Beat | What sets the move off. `Beat`: the song's beats (`Every`, `Phase`). `Hit`: each note the player hits. `Accent`: each crash, china, splash or kick they hit (the big notes). `Miss`: each note they miss (a stumble, a bump). On one of the player's it goes out at once and eases back over about half a second; `Every` and `Phase` are not used. |

Hell's circles put their damned in crowds (`Dress.crowd` in `Tools/Venues/story_afterlife_circles.py`): one mesh for a crowd's bodies on its own `VenueBeat` and its heads on a child with another, so that two crowds on one ledge move out of step. A crowd's entity stands on the shaft's axis, so its `Turn` about y moves the whole crowd along the ring (Greed's boulders heaved up the spiral on the player's big notes, `Trigger` `Accent`; slipping back on a miss) and a `Turn` about x or z tilts the ring (Lust's souls tossed about). A good crowd and its bad twin are two crowds with `VenueMood` `Show` `Good` and `Bad` (Limbo's dancers and wallflowers, Greed's column and rabble), and `Calm` holds a crowd back while the drums are wrong (Wrath's mosh pit). A thing with a pivot of its own (an iron maiden on its chain, a tree lashing) is a piece (`Dress.piece`), one entity in every copy of the period. The lower circles (`Tools/Venues/story_afterlife_lower_circles.py`) use a few more: a `VenueMood` `Offset` sinks a crowd as the playing goes bad (Violence's murderers go under the blood); a glow piece given the same `VenueBeat` as a crowd or another piece moves with it exactly (the simoniacs' burning soles on their kicking legs, a maiden's red-hot shell swinging with her); and a `Bad` glow piece with `Trigger` `Miss` (the fires under Dis's iron maidens) flares on every miss. What is not in a crowd or a piece dips in three meshes on the beat, as before.

On hell's floor (`Tools/Venues/story_afterlife_heart.py`) the demons dip on the beat with `Calm` 0.25, each on its own `Every` and `Phase`, so they barely stir unless the drums are right. Satan is rigid parts on pivots, and each pivot is a `VenueBeat` with a `Turn`: his neck nods on the beat, his waist rocks his shoulders (`Sway`, every two beats), his forearms come down on the player's hits (`Trigger` `Hit` on the right, `Accent` on the left), and his heart, inside his chest, comes out through it on each beat (`Sharp`). One rig of him for each way he moves, each shown between two story flags; they swap at rest, with no fade.

### VenueMood

Answers to how well the player is playing (`VenueShow::UpdateMoods`). The mood (`VenueShow::Mood`) is 0 at their worst and 1 at their best: a running share of the notes they hit, each note counting for about a tenth, with their streak since the last miss on top (thirty clean notes in a row win it back); a miss costs most of it at once. Until a note has been judged (the Track Editor's preview, a venue capture) it is 0.8. `--venue-mood <0..1>` holds it, to see a venue's good and bad sides.

| Field | Default | Meaning |
|-------|---------|---------|
| `Offset` | (0, 0, 0) | Where the entity is while the player plays at their worst, from its resting position, in its parent's space; back at rest at their best, and in between in between: a hound that keeps pace with the band falls behind as the notes go. |
| `Show` | Always | `Good`: shown only while the mood is at or over `Threshold`; `Bad`: only while it is under. Scaled from its pivot over a third of a second, as a `VenueStory` is. A crowd that dances when the drums are right, and its twin that is thrown about when they aren't: switched on the mood itself, so the two never both stand. |
| `Threshold` | 0.5 | The mood that divides good from bad. |
| `Seconds` | 1 | About how long `Offset` and `Speed` take to follow a change in the playing. |
| `Speed` | 1 | The speed of the `Sequence` on this entity while the player plays at their worst, of its own (1 at their best). Not for a sequence under a `Clock` story group, which is seeked, not played. |

Particles and lights under a `Good` or `Bad` group are not switched with it (a `VenueStory` switches its own): keep such a group to meshes and motion. A `VenueBeat` reads the same mood through its `Calm`.

### VenueAim

Keeps its entity's local +Z on a point in the venue however its parents move (`VenueShow::UpdateAims`): a searchlight slung under a helicopter that hovers and turns, held on the stage. Put it on a Spot light, or on the parent of a lamp housing and its light, so the housing turns with the beam. The entity's own rotation is only what the editor shows; in a show it is overwritten every frame.

| Field | Default | Meaning |
|-------|---------|---------|
| `Target` | (0, 0, 0) | The point it is held on, in venue space. |
| `Wander` | 0 | How far the aim strays from the point, in metres, before it is pulled back: a light held by hand. 0 holds it dead on the point. |
| `Seconds` | 3 | Roughly how long one drift across the point takes. A faster correction and a slight tremor ride on top of it. |

The afterlife highway's two police helicopters and the one over My Hero's ambulance hold their searchlights this way (`make_story_afterlife.police_helicopter`).

### VenueSound

Plays a sound once when a story flag lands (`VenueShow::BuildSounds`, `UpdateSounds`): a crash, sirens, what a song's outro is heard by. 2D and streamed. It starts only if the song reaches the moment (a song picked up later doesn't play it late), pauses with the game, and stops with the venue: at a hand-off to a song in another venue it is cut, so keep it shorter than what is left of the song.

| Field | Default | Meaning |
|-------|---------|---------|
| `Flag` | empty | The story flag whose landing plays it. A flag set before the song has had its sound. |
| `Sound` | empty | The sound file's asset path (`Assets/Venues/<Venue>/Sounds/Wreck.ogg`). |
| `Volume` | 1 | How loud, 0 to 2. |
| `Delay` | 0 | Seconds after the flag. |

The afterlife highway's `Wreck.ogg` is the only one so far: the trailer going over, the blast, the fire, ears ringing and the pursuit's sirens, 15 s, on the flag `wreck`. It is synthesised by `Tools/Venues/story_afterlife_sound.py` (ffmpeg, fixed seeds) and covers Kickstart My Heart's outro (the song's `OutroSeconds`, `Docs/Hideout-and-Progression.md` → Continuous sets). Nobody has listened to it yet: it was balanced from level readings and a spectrogram.

### VenueFigure

A person in the scene: one of the band's rigged characters (`Performer`, `Docs/Venue-and-Band.md` → The body), skinned and posed from this marker's fields every frame (`VenueShow::BuildFigures`, `UpdateFigures`). The entity is the figure's feet (kneeling: the floor under its knees) and it faces local +Z. Every point and direction below is in that space, in metres: the feet at the origin, the right hand toward +X.

It exists because a figure baked from the crowd's rigid pieces has no shoulder, wrist or fingers and can't put a hand on anything. A `VenueFigure` reaches by inverse kinematics, so a palm lands on the point it is given.

| Field | Default | Meaning |
|-------|---------|---------|
| `Character` | `BodyType1_Rigged.fbx` | A T-posed Rigify character from `Assets/Models/People`. |
| `Atlas` | `PolygonTown_01_A.png` | The atlas the character's UVs index: its clothes. |
| `As` | Own | Whose look it wears. `Own`: `Character` and `Atlas`. `Drummer`, `Guitar`, `Bass`, `Vocals`, `Keys`: whoever plays that part in the song, in their clothes (`Band::LookOf`; its own look when nobody does). The band's bodies on the road are dressed this way, so they are the band. |
| `Height` | 1 | A scale on the whole figure. |
| `Stand` | Standing | `Standing`, `Seated` (the hip joints at `SeatHeight`, the feet flat ahead) or `Kneeling` (the knees on the floor under the hips, the shins laid back). |
| `Offset`, `Crouch` | 0 | The whole figure moved; how far the hips drop. |
| `Bow`, `Lean`, `Side`, `Turn` | 0 | Degrees: the trunk forward from the hips, the spine curled forward, to the right, the chest turned right. |
| `Nod`, `HeadTurn`, `HeadTilt`, `Mouth` | 0 | The head down and turned right, in degrees; the mouth from shut to open. |
| `LeftArm`, `RightArm` | hanging | `Raise`, `Spread`, `Elbow` in degrees; or with `Reach` on, the palm goes to `Hand` and the elbow bends toward `Pole`. `Fingers` and `Palm` turn the hand, `Grip` closes it. |
| `LeftLeg`, `RightLeg` | planted | `Spread`, `Toe`; or with `Reach` on, the sole goes to `Foot` and the knee bends toward `Knee`. |

- **Motion.** A Sequence can key any number or vector here by its path (`Bow`, `LeftArm.Hand`, `RightLeg.Foot`), so it moves under a `VenueStory` group like any other clip: slow motion, or once on a flag. Flags such as `Reach` can't be keyed.
- **Cost.** Each is a skinned draw of its own for every camera and shadow cascade, and its skeleton is posed every frame. Use it for the few people a shot is about. One hidden by a `VenueStory` group is switched off until it shows.
- **The editor.** Havana shows only the marker: the figure is built with the show.
- **From Python.** `story_afterlife_people.actor` places one, with `arm`, `leg`, `ftrack` (a track on the figure), `gait` (a stride on the spot), `to_figure` and `turn_to` (a venue point in the figure's space, and the head turn that faces it).

- **Drivers.** The band's character is 1.82 m and 1.08 m from a seat to the top of its cap, more than the modelled cars had between cushion and roof (0.71 to 0.75 m). So the vehicle exports (`Tools/Venues/export_patrol_cruiser.py`, `export_vehicles.py`) write the road vehicles a tenth larger than modelled and lower the front seats of the ones the story mans (the patrol cruiser, whose floor is also cut down to a well, and the Trail Duster and Ranger) until a driver clears the lining. They record where the hips and heels go (`Seat`, `Heel` in `Tools/Venues/story_vehicles.json`), and `make_story_afterlife.driver` seats a `VenueFigure` there with its hands on the wheel. A new manned vehicle needs an entry in `export_vehicles.DRIVERS`.

The afterlife's cop, EMS crews and nurse are these: the compressions and the medics at the crash site, the gurney going into the ambulance, the paddles and the bag in the back of it, the run down the corridor, the cop at the wheel and by the ward's window, the drivers of the pursuit. The band lying on the road at the crash (Kickstart's outro, Free Bird's opening, My Hero's CPR) are these too, laid on their backs and dressed `As` the band (`make_story_afterlife.dead`). Demons, the damned, the nurses along the corridor wall, and the band on the gurney, the operating table and in the ward are still baked.

### VenueStory (story mode)

Story mode (`Docs/Hideout-and-Progression.md` → Story mode) plays five songs at one venue, and the venue changes as they go: each song sets some flags (`Design/Story-Mode-Setlists.json`, each song's `StateAfter`). A `VenueStory` marker shows its entity and children only while its flag is set, or with `WhenSet` off only until it is set (the dessert table against the wall; the dessert table in the middle of the floor). The flags of the songs before the one playing are set from its start; the song's own flags land at its **cue** (its `Cue.On`: `intro`, `verse`, `first_chorus`, `bridge`, `solo`, `outro`, `song_end`), found in the chart's sections, else at a share of the song (2%, 15%, 30%, 60%, 55%, 85%, the end). A song can also carry **moments** (`ProgressionStorySong::Moments`), more flags each landing at their own cue. Besides the names above, a cue (`VenueShow::StoryCueTime`) can be `section:<name>` (the chart section of that name, else the first with that in its name: `verse_1` is never Bat Country's `preverse_1`), `at:<share>` (a share of the song, 0 to 1), `time:<seconds>`, `drums_in` (the first note), `last_note` or `start`, and any cue can be moved by seconds: `last_note+2`, `section:chorus_3+12`. `a|b` is cue `a` when the chart has the section it names, else `b` (`section:bre+4|at:0.957`), so a set bound to one chart still plays in order on a stand-in with no sections. A chart can move a moment itself: a cue on its **Story** track named for one of the moment's flags (`VenueData::m_story`, saved as `Venue.Story` in `NoteData.txt`) is when that moment lands in that chart, whatever the set's cue says (`VenueShow::StoryMomentTime`). In the Track Editor, *Story > Place the Set's Moments* lays a story song's moments out on that track where the set has them, to drag; with the preview's venue on *Song's Venue* the preview builds the set's venue and plays its story, and rebuilds as they move. It grows in or shrinks away over `FadeSeconds` from the entity's pivot, and the plain `Light`s under it dim with it. A `VenueShowLight` under it is still cued by the rig, and dimmed with the group after the cue is applied (`VenueShow::DimStoryShowLights`): that is how a venue with several places in it (Hell's crash site, shaft and cavern) gives each its own rig. A `ParticleSystem` under it emits only while every story group above it is shown, and starts over when they show, so a one-shot `BurstCount` goes off as its flag lands (a hidden group is only scaled away, which would otherwise leave its fire burning at the pivot); a system with a `VenueAccent` stays the show's.

| Field | Default | Meaning |
|-------|---------|---------|
| `Flag` | | The story flag. |
| `WhenSet` | true | Shown once set; false: shown until set. |
| `Unless` | empty | A later flag that takes `Flag` back: while it is set, `Flag` counts as not set. With `WhenSet` false: gone from `Flag` until `Unless`, then back (Free Bird's Earth, hidden from `earth_lost` inside the cloud until `earth_back`). `Scene.story(..., unless=)`. |
| `FadeSeconds` | 0.75 | Grow/shrink time (0 pops). |
| `Mode` | Show | `Show`: shown or hidden by the flag, as above. `Play`: always shown; the `Sequence`s on it and under it (author them with `PlayOnStart` off) play once when the flag lands, and a flag already set when the song starts (or a seek past it) leaves them at their end; a seek back before it, at their start. A `Sequence` under it that has `PlayOnStart` on (a looping road, beating wings) is left running. A `Play` group inside another is its own: the outer one leaves what is under it alone (a circle of hell arrives on one flag inside the group that carries it away on the next). `SlowMotion`: always shown; the `Sequence`s under it run at `Speed` until the flag lands, then at full speed. `Clock`: always shown; the `Sequence`s on it and under it (`PlayOnStart` off) are held to the song's clock from the moment the flag lands, a looping one wrapping, whatever a pause, a seek or the frame rate did, so a story shot can be timed against them (each circle of hell streams on its flag's clock, and the cameras on its ledges are cued from where a ledge then is: `Tools/Venues/story_afterlife_circles.py`, `pass_time`). |
| `Speed` | 0.3 | `SlowMotion`'s speed before the flag. |

**The band.** Flags starting `band_` move the live band rather than props (`VenueShow::UpdateStoryBand`, `Band::SetStoryState`): `band_ghost` turns them and everything they play (kit, guitars, stands, amps) into ghosts over two seconds: see-through, all of one pale blue with their clothes showing only as light and dark in it, glowing at the edges, and taking only a share of the venue's light (`StandardMaterial::Rim`; `Band::GatherGhosted` finds the materials, the players' own inside their compact models). Only a ghost's outside is drawn (`StandardMaterial::Shell`, `Engine/Docs/Rendering-Pipeline.md` → Shell): the world shows through them, but not their own far side, the arm behind the chest or the ghost standing behind; the poses `band_down` (on their backs at their marks), `band_falling` (tumbling for the first seconds, then from two to nine seconds in straightening out into a head-first dive for as long as the fall lasts: guitarist, bassist and singer pitched past flat about their hips, legs trailing and kicking, still playing; the keyboard player leaning out over the keys, which dive with them; the drummer stays on the throne with the kit. The amps and wedges come loose and tumble beside them, each its own way (`Member::Loose`), the mic stands are gone and the singer has a mic in hand; all of it eases back as they land. `Band::DivePose`, `DivePitch`), `band_floating`, `band_aloft` (lifted a little off the floor with everything they play, riding the air there; as in a fall there is no floor under them, so the drum rug and the mic stands are gone and the singer has the mic in hand, `Band::m_air`), `band_reach` and `band_shield` (aloft and hanging still, the singer's head tipped back to look up and their free hand at work, `Band::m_reach`, `m_shield`: `band_reach` takes it up ahead of them to full stretch over about a second and a half, open, straining; `band_shield` pulls it in across their eyes in about half a second, the palm to their face; whatever pose comes next takes it down as it blends in. Free Bird's plea, seen through the singer's eyes; for as long as it lasts the singer's own ghost is backlit, nearly solid and dark with little glow, `Band::m_backlit`, so the hand stands against the light from heaven instead of glowing pale in it), `band_rising` (lifted off the floor and away), `band_hidden` and `band_playing` (back at their marks) hold the band from when they land, the latest landed winning and blended in from the one before over 2.5 s (into or out of `band_hidden` pops). They never carry over to the next song of a set (`GigSession::StageStory`): each song sets its own. What stands on the floor (the kit, rug, amps, wedges, mic stands, keyboard: each member's `Backline` group) doesn't lift with them: it stays put through `band_rising` and is gone while `band_floating`, back when they play again. Guitars and sticks go with their players.

**Captions.** A story moment with a `Caption` shows that line over the highway for `CaptionSeconds` (4 by default) from its cue (`VenueShow::StoryCaption`, the HUD's `story_caption`).

**The sky.** Flags starting `sky_` put the venue under the engine's procedural sky and turn its hour (`VenueShow::UpdateStorySky`), indoors or out: `sky_<hour>` is the hour as that flag lands, and between two such flags the hour turns steadily from one to the other. Hours run on past 24 (`sky_30` is six the next morning), so a night turns to day through its dawn and goes back the way it came: Free Bird's ghosts rise from the crash at `sky_21.5` through `sky_30.2`, `sky_31` and `sky_34` to `sky_36` at the gates, and fall back to `sky_21.5` in the three seconds before they go through the road. Two flags with the same hour hold it between them. `sky_off` gives the venue's own background back. Under the sky, `alt_<metres>` flags are how high the sky is seen from (the engine's `ProceduralSky.ViewerAltitude`), turning from one flag to the next the same way: the set stays where it is while the sky's own cloud base comes down to it, goes by and lies below as a sea of cloud. A song with `alt_` flags gets a low, shallow layer (`kClimbCloudBase` 400 m, `kClimbCloudThickness` 600 m), so the climb from the ground to over the tops is a few hundred metres and can be slow; `cover_<percent>` flags turn the cloud cover likewise, `towers_<percent>` the sky's `Convection` (heaped tops, and cumulonimbus with anvils standing up out of the cloud sea far off) and `clear_<percent>` its `CloudClearing` (a gap in the layer round the camera, `kClimbClearingRadius` 380 m, to climb up with the ground in view; close it before they fall back through). Such a song's set is also under the cloud (`SceneUnderClouds`): everything more than 30 m under the stage (`kClimbGroundBelow`) has the sky's cloud laid over it, so the Earth below shows only through the gaps, and toward the horizon gives way to the sky's own ground. The cloud is sky to the renderer (drawn behind the scene), so while the camera is inside it the game makes the scene's haze the cloud (`DynamicSky::SampleCloudDensity`, `kCloudHazeScale`), and above a few hundred metres the day's haze is taken off (it would paint out the cloud below the horizon). Scenery that is not really that far down has to be hidden while the sky says it is (`Unless`, above). Free Bird: `alt_0` at `ascent`, `alt_330` at `clouds` (just under the base; `towers_0` at `ascent` to `towers_100` at `clouds`, `clear_0` at `clouds` to `clear_100` 8 s later), `alt_1050` at `heavens_light` (over every top), `alt_1250` at `gates`, `alt_1400` at `denied`, `alt_0` at `fell`. The sky's sun and moon light the scene while it is on (the venue's own directionals are Manual and stay as they are), its stars and clouds come from `VenueInfo` (`MoonBrightness`, `CloudCoverage`), and the haze takes the day's colour as the sun comes up. By day the haze also becomes the open air's (`kDayHazeScale`, `kDayHazeFalloff`, `kDayHazeOpacity` in `VenueShow.cpp`: thin, thinning slowly with height, and taking the far distance whole), the camera's far plane goes from 400 m to `kDayFar` (4.5 km) as soon as there is light to see by, and the director takes most of the bloom off (`Director::SetDaylight`): a daylit picture is past a night's bloom threshold everywhere. So what is under a story sky by day has to reach the horizon. Free Bird's crash site does (`earth` in `make_story_afterlife.py`): the ground runs 3 km out to a rim of hills, in two halves either side of the road so that nothing far off lies on top of anything else, its fields, hedges and woods are one texture that repeats every 1536 m (`A.earth_at`, which also says where the woods' crowns stand), and the highway runs on both ways as its own mesh. A venue that uses the sky needs no sky dome over that stretch (a dome would hide it), and no stars or moon of its own. A story shot's own `sky<hour>` tag takes over while that shot holds.

**Story shots.** A `Custom` `VenueCameraSpot` tagged `story/<flag>` is the shot the director cuts to when that flag lands during the song (not when it was already set at the start), over every other shot, the arrival intro included (`Director::SetStoryShots`). More of the tag, separated by `/`: a number is how long it holds (5 s without one), `hand` shoots it handheld, `lin` runs its move at one speed from first frame to last instead of easing it, and bolts the camera to that move (a camera keeping pace with something on a `Clock`: the framing's usual easing leaves it 0.4 s behind, which at hell's 32 m/s was 13 m under the ledge it was meant to stand on). With waypoints a `lin` move carries its first and last steps on past the ends, so evenly spaced spots in a line are passed at exactly one speed. `lights` keeps reds, blues and fire in colour through any look for that shot alone (heaven's cuts to the crash on Earth). `heli` shoots it from a helicopter on a long lens: the aim hunts and overshoots (by a share of the frame, so a tight lens keeps its subject), the airframe buzzes, the horizon rolls, and the zoom breathes and now and then punches in. `ride` (or `ride0.6`, an amount) bolts the camera to something on the move for that shot: it rattles, heaves and takes the bumps as every camera does in a venue with `Ride` set (1 a fast highway). The spot itself can't move with anything, so stand the vehicle still and run the world past it on loops (the inside of the ambulance and the gurney in My Hero's cut-aways, `Tools/Venues/story_afterlife_rescue.py`). `sky<hour>` (`sky12`) puts the shot under the engine's procedural sky (its clouds and sun) at that hour for as long as it holds, whatever the venue has behind it, and gives the venue's own back after (`VenueShow::UpdateShotSky`; the sun is kept low and due -z at midday, so a window facing -z has it). A second spot tagged `story/<flag>/end` is where the shot moves to over the hold (eased): a pull back, a crash zoom. Spots tagged `story/<flag>/w1`, `/w2`, ... are passed through on the way, in order, on a smooth curve (a crane up the stairs, a zoom that overshoots and comes back). `f<metres>` on the first spot or the end (`story/ascent/14/f0.46`) pulls focus to that distance and softens everything off it; when the two differ the focus racks from one to the other. `leadl` / `leadr` keep the shot's subject clear of the note highway, which runs up the middle of the screen: aim the spot at the subject, and while the highway is up the camera turns so that the middle of its view sits 60% of the way out to the left / right of the picture (the director's lead room, `Director::LeadRoom`), through the whole move; as the highway goes down for a rest and comes back, the turn eases out and in again. The turn is an angle from the lens's width, so it holds on any screen from 4:3 to 32:9. It turns about the vertical: no use on a shot looking straight up or down. Story spots are never used for the director's ordinary cuts. `--venue-shot spot:<tag>` holds one to frame it.

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

`--venue-eye` puts the camera anywhere in venue space to inspect the set; with `--venue-only`, `--venue-capture-highway` keeps the highway's board and rails drawn over the venue (and story shots take their `leadl` / `leadr` turn), to judge a shot's framing against it, and `--venue-lead` takes the turn without drawing the highway (the board darkens what is under it); `--venue-mood <0..1>` holds the player's mood (`VenueMood`); `--venue-moment 5` fires a peak every 5 seconds so the effects and strobes show; `--venue-shot` holds a director shot. On a desktop, just run the game with `--venue <Id> --play-track N`. The other venue flags are listed in `Docs/Venue-and-Band.md` → Settings and flags; `--venue-plan-test` is a dev flag that moves the drummer to the bass spot turned 215 degrees and drops the bass and keys.

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
- The fog is distance fog at a fixed density (`Director` sets 0.012 a metre): nothing shows past about 150 m, whatever `Haze` is, so a sky has to be a dome about that far out with its light turned up (StoryHeaven's is 185 m: it has to clear the wings of the great angel, and whatever stands outside a dome is cut off by it). A see-through surface fogs itself, so an additive glow card far off in a bright-fog venue shows as a square: use an emissive mesh there.
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
