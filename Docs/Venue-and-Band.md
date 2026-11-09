# Venue and Band

> Verified against game commit 5973499 plus the venue change, 2026-11-08; the concert look against 35a9edd plus the concert look change, 2026-11-09. Engine submodule at 0c32daef.

The concert under the note highway: a stage with a band playing the song, a crowd reacting to it, the light show (`Docs/Stage-Lighting.md`) and a camera crew cutting between shots, all driven by the chart's Rock Band venue data and played on the song clock. The highway is drawn over it by an overlay camera, so the venue underneath can change without touching gameplay.

## Overview

- **Layers.** The venue is built 500 m from the highway (`VenueLayout::kVenueOrigin`), past either world's far plane, so neither camera ever sees the other's world. It used to be 4 km out, where world positions only resolve to half a millimetre and close-ups showed vertices crawling; under 512 m it's 30 microns. The venue's camera becomes the main camera; the highway's camera (`Main Camera` under `TrackMover` in `Assets/Example.lvl`) becomes an engine **overlay camera** (`Camera::Overlay`, `Engine/Docs/Rendering-Pipeline.md` → Overlay cameras) composited on top. Its far end fades into the venue (`OverlayFadeStart` / `OverlayFadeEnd`) and its dark board lets the stage show through (`OverlayDarkOpacity`); its own fog is turned off while the venue runs.
- **Everything is primitives.** No meshes or clips: the set, instruments and people are the engine's cube, sphere, cylinder, capsule and plane primitives with `DiffuseMaterial`s (`VenueKit`), posed procedurally every frame (`Puppet`). Pieces sharing a colour instance into one draw.
- **Data first, fallbacks second.** Charts converted from Rock Band `notes.mid` carry camera cuts, post-processing looks, band animation states, drum limb notes, strums and sung notes (see *What is imported*). Charts without them (`.chart` songs, sparse MIDI) get the same show built from their sections, tempo and drum notes.

## Key Files

| File | Role |
|------|------|
| `Game/Source/Venue/VenueShow.h/.cpp` | Owns the venue: builds the set, band, crowd, director and lights; turns the highway camera into the overlay; updates them on the song clock; pyro and the stage-edge LED strip |
| `Game/Source/Venue/VenueLayout.h` | The floor plan: venue origin, stage size, member spots, crowd area |
| `Game/Source/Venue/VenueKit.h/.cpp` | Spawns primitive pieces (full sizes in, primitive scale worked out) and deletes them on `Clear` |
| `Game/Source/Venue/Puppet.h/.cpp` | A figure from primitives: joints from angles (FK) or a reach target (two-bone IK), capsules laid between joints |
| `Game/Source/Venue/Band.h/.cpp` | Drummer, guitarist, bassist, singer, keyboard player: instruments and their animation |
| `Game/Source/Venue/Crowd.h/.cpp` | The audience and its moods |
| `Game/Source/Venue/Director.h/.cpp` | Camera cuts → shots, post-processing looks, the LED wall's feed camera |
| `Game/Source/CoreGame/Lyrics.h/.cpp` | Karaoke lines from the chart's lyric events and phrases, for the HUD and the LED wall |
| `Game/Source/Venue/LyricBoard.h/.cpp` | The lyrics on the LED wall: one plane per character, its glyph picked from the font atlas |
| `Game/Tools/MakeLyricFont.py` | Builds the lyric font atlas `Assets/Textures/Venue/LyricFont.png` (Inter) and `Game/Source/Venue/LyricFont.generated.h` |
| `Game/Source/Venue/VenueTiming.h` | Shared helpers: beat lookup, cue lookup, repeatable noise |
| `Game/Source/CoreGame/CustomTrackDefineTest.cpp` | `ReadMidiVenue`: VENUE / MV VENUE / EVENTS / PART tracks → `VenueData` |
| `Game/Source/CoreGame/TrackList.h/.cpp` | `VenueData` and its `"Venue"` block in `NoteData.txt` |
| `Assets/Textures/Venue/StageProgram.rendertexture` | The LED wall's program feed (640 × 320) |
| `Assets/Textures/Venue/StageFeed.rendertexture` | The side screens' close-up feed (480 × 272) |

## What is imported

`CustomTrackDefineTest::ReadMidiVenue` reads, beyond the lighting in `Docs/Stage-Lighting.md`:

| Track | Source | Kept as (`VenueData`) |
|-------|--------|------------------------|
| VENUE | RB2 camera notes: 60 cut, with 61 no close, 62 only close, 63 only far, 64 no behind, 70-73 focus bass / drums / guitar / vocals struck at the same tick | `m_cameras`: `"auto <constraints>"` |
| VENUE | `[do_directed_cut x]`, RB3 `[coop_x]` / `[directed_x]` | `m_cameras`: the shot name |
| VENUE | RB2 post notes 96-110 (ProFilm_a, ProFilm_b, video_a, film_16mm, shitty_tv, bloom, film_sepia_ink, film_silvertone, film_b+w, video_bw, contrast_a, photocopy, film_blue_filter, desat_blue, video_trails), RB3 `[x.pp]` | `m_postFx` |
| VENUE | Notes 85 / 86 / 87 held | `m_singalong`: bass / drums / guitar sing along |
| MV VENUE | The same cuts and looks | `m_mvCameras`, `m_mvPostFx` (the music video) |
| PART DRUMS / GUITAR / BASS / VOCALS / KEYS | `[idle]`, `[play]`, `[mellow]`, `[intense]`, `[idle_*]`, `[play_*]` | `m_bandStates[member]` |
| PART DRUMS | Animation notes 24-51 (kick, snare, hi-hat, toms, crashes, ride by hand, hard or soft) | `m_drumHits`: time, limb, piece, soft |
| PART GUITAR / BASS / KEYS | Expert gems 96-100 (a chord strums once) | `m_guitarStrums`, `m_bassStrums`, `m_keysStrums` |
| PART GUITAR / BASS | Fret-hand positions 40-59 (0 at the nut) | `m_guitarFrets`, `m_bassFrets` |
| PART VOCALS | Sung notes 36-84 | `m_vocalNotes` |
| PART GUITAR | Solo markers, note 103 | `m_guitarSolos` (the neck camera) |
| PART VOCALS | Lyrics: unbracketed text and lyric events, one per syllable, Rock Band's markers kept | `m_lyrics` |
| PART VOCALS | Phrases, notes 105/106 held (a line each; duplicates of the same line dropped) | `m_vocalPhrases` |
| PART VOCALS | Percussion hits 96/97, and `[tambourine_start]` / `_end` (also cowbell, clap) | `m_vocalPercussion`, `m_vocalCues` |
| HARM1-3 (or PART HARM1-3) | Each harmony part's sung notes 36-84 and lyrics | `m_harmonyNotes`, `m_harmonyLyrics` |
| PART GUITAR / BASS | `[map HandMap_x]` and `[map StrumMap_x]` | `m_guitarMaps`, `m_bassMaps` |
| EVENTS | `[music_start]`, `[music_end]`, `[end]`, `[coda]` | `m_songEvents` |

RB2 notes 96 / 97 used to be read as pyro; they are post-processing. Pyro comes only from `[bonusfx]` / `[bonusfx_optional]`. Re-run the converter (`--convert-dlc`, or Convert DLC in settings) to add the new data to existing charts.

## How It Works

### The set and the rooms

`VenueShow::BuildStage` builds the stage, the same in every room: a 1.2 m deck, a drum riser, a back wall with the LED wall, speaker stacks, truss towers and an overhead truss (where the washes hang), a barricade, a front-edge LED strip that glows with the washes and chases on the beat, and four pyro emitters whose flame columns and point lights fire on the chart's bonus effects. Screens are planes whose emissive slot is a render texture, flipped upright with Tiling (1, -1) and Offset (0, 1).

The room around it is a `VenueShow::Style`:

| Style | Room | Crowd |
|-------|------|-------|
| Arena | A big dark hall under a roof with a rigging grid: the floor full back to the mixing desk and past it, seven tiers of stands at the back and three along each side (aisle lights on every step), PA hangs and screens either side of the stage, exit signs | 520 posed + about 1,600 in the back of the house |
| Club | Brick walls close in, a low ceiling, neon tubes on the walls, a bar at the back; thicker haze | 240 posed, packed to the bar |
| Festival | Open air at night (the main camera's procedural sky at 22:00, a full moon), a canopy over the stage, screens on towers, delay towers and a mixing tent in the field; thinner haze | 800 posed, the field full to the delay towers and thinning out to 66 m |

**Room** in settings picks one (or Random: one per song, repeatable by title). **F7** during a song tears the venue down and builds the next room in its place (`VenueShow::NextStyle`); the highway on top carries on, which is the point of the layering. The director keeps wide shots inside the room (`Director::SetRoomBack`).

### The band

`Band` places each member at `VenueLayout::kMemberSpots`, facing the crowd. Keys only appear when the chart has a keys part.

- **Drummer.** The stick tips follow per-limb stroke lists: the chart's animation notes when it has them (feet from its kick and hi-hat pedal gems), else `Band::DeriveStrokes` assigns its gems to limbs (notes struck together go left-most piece to the left hand; cymbals and the floor tom to the right hand, the snare to the left, alternating in fast runs and tom fills). `Band::StickTip` arcs each tip from stroke to stroke, as high as the gap allows, and lands it on the piece at the note's time; the hand sits a stick's length behind the tip and the arm reaches for it (IK). Struck cymbals rock, drums squash. Feet press the pedals on kick and hi-hat-pedal notes.
- **Guitarist and bassist.** The guitar hangs off the torso; the strumming hand moves down on even strums and up on odd ones; the fretting hand follows the chart's hand-position notes (else moves every few strums). States: `idle` (hands still, looking around), `play` (bobbing), `mellow` (swaying), `intense` (headbanging, wide stance), `play_solo` (walking out front over about a second, leaning back, neck up, a follow spot on them). During a singalong they ease in to their mic (not mid-solo). Their bob rises over the first 15% of each beat (`SoftPulse`) rather than jumping on it like the others', since their guitar necks swing with it. The guitar has frets, a nut and strings for the neck camera. The chart's hand maps shape the fretting hand: `HandMap_Chord_X` holds that open chord's shape in the first frets, `AllChords` wraps the hand round the neck, `NoChords` and `Solo` hop it along the neck per note (further for a solo), `DropD` / `DropD2` keep it near the nut and lift it off the strings as they're struck; `StrumMap_SlapBass` slaps over the neck pickup. Charts without maps play as `HandMap_Default`.
- **Singer.** At the mic for a whole line, short rests and breaths included, the mouth opening through each sung note (`Band::AwayFromMic`). Only a break between lines of about five seconds or more sends them off: they linger 0.8 s after the line, walk out over 1.2 s, and are back at the mic 1.2 s before the next line starts, all from the song clock (the same at any frame rate or after a seek). A line is the chart's phrase (notes 105/106) when it has them, else a run of sung notes; Rock Band's phrases also cover percussion sections, so the singer plays those at the mic. Out front they jump and fist-pump when it's intense; otherwise each break gets one habit: clapping over their head, an arm swept across the crowd, or just walking.
- **The singer's percussion.** In the vocal part's tambourine, cowbell and clap sections, whenever they aren't singing, the singer plays it, struck on the chart's hits (notes 96/97; on the beat in a section without hits): a tambourine shaken in the free hand, a cowbell held and struck, or claps. Hits outside any section get a tambourine section of their own. The tambourine and cowbell appear in the hand only while played (`Band::DerivePercussion`, `UpdateVocals`).
- **Backing vocals.** Charts whose VENUE has no singalong notes (85-87) get them from the harmony parts: HARM2 goes to the guitarist, HARM3 to the bassist (else the keyboard player or drummer), each run of notes without a 0.6 s rest one singalong (`Band::DeriveHarmonies`). HARM1 is the lead line, the same as PART VOCALS.
- **The end.** After `[music_end]` / `[end]` everyone but the drummer throws their arms up and bounces, and the crowd roars.
- **Fallbacks.** States from section names (choruses intense, intros mellow, solos to the guitarist); strums on the half beat (guitar) and beat (bass) wherever the drums play; the singer sings three beats of four through verses and choruses.

### Lyrics

Charts with lyrics show them karaoke-style, on the HUD and on the LED wall (Settings > Lyrics). `Lyrics::Build` turns the syllables into lines: Rock Band's markers are resolved at display time, so the rules can change without converting again (`-` joins the next syllable, `=` joins it with a hyphen shown, `+` carries the last syllable through a slide, `#` `^` `*` `%` `$` `/` are dropped, `§` and `_` are spaces). A line is a phrase; without phrases a rest of over 1.2 s starts a new one. Lines over 44 characters split at the word nearest their middle. A line comes up 3 s before it's sung and stays 0.6 s after; the next line previews under it when it's within 10 s. Sung syllables light up as each starts.

- **HUD.** Top centre, over the far end of the highway (`#hud-lyrics` in `Assets/UI/InGameMenu.rml`): the line with its sung part gold, the next line smaller and dim. `NoteHighwayCore::UpdateLyrics` sets `lyric_sung`, `lyric_rest`, `lyric_next` and `lyrics_shown` when they change; `InGameMenuController` registers them up front so the document never reloads for them.
- **The LED wall.** `LyricBoard` puts a dark band across the wall's lower part (4-5.5 m, above the drummer's head) with the line on it, sung syllables gold, and the next line under it, grey. Each character is a plane (`Lyrics::kMaxLine` + 8 per row, built once) with the font atlas as its emissive texture; the material's Tiling and Offset pick its glyph, and planes one advance wide abut without overlapping. Glyphs that look the same share an instance batch (the batch key includes Tiling, Offset and the emissive colour). Lines too wide for the band shrink to fit. The atlas is printable ASCII: curly quotes and dashes are straightened, other characters dropped. The wall's program feed films the band too, so in wide shots the lyrics show on the wall one level deep.

### The crowd

`Crowd` fills the floor with the room's crowd of five-piece figures (`--crowd-size N`), keener toward the front, each with its own lag behind the beat, enthusiasm and habit (jumper, pumper, swayer, clapper). The mood comes from `[crowd_x]` (or the sections): standing about, bobbing and fist pumps (`normal`), jumping with their hands up (`intense`), swaying with lighters and phones up (`mellow`). `[crowd_clap]` has them clap on the beat. `realtime` follows the player: the core's streak (`NoteHighwayCore` → `VenueShow::SetPerformance`) gets them going; misses take the wind out of them; every fifty in a row and the chart's pyro get a cheer. Their energy also drives the light rig's crowd blinders.

The posed crowd stops after its few hundred figures, well short of the back of most rooms, so `VenueShow::FillHouse` fills the rest with the **back of the house** (`Crowd::AddMob`): figures of four or five boxes (legs, torso, head, arms, sometimes a lighter or phone) moved as one, one transform a figure a frame, wherever the posed crowd doesn't stand (`Crowd::KeepClear` leaves the mixing desk, towers and stand aisles empty). They follow the same mood: bobbing, fists and hands up, jumping when it's intense, lights up and swaying when it's mellow. A cap thins an area evenly rather than leaving its back empty. Phone-holders film the intense parts with their phones up, now and then flashing a photo. On the chart's `crowdsurf` / `stagedive` shots (and every so often when it's intense) a crowd surfer is carried over their heads to the barricade by the hands under them.

### The cameras

`Director` holds the cut list (VENUE's, or MV VENUE's when **Venue Camera** is Music video and the chart has one) and frames the latest cut each frame:

- `coop_<who>_<framing>`: `who` is `all`, `front` or member letters (`d`, `g`, `b`, `v`, `k`, pairs like `gv`); framing `far`, `near`, `behind`, `closeup_head`, `closeup_hand`.
- `directed_<who>[_<style>]`: `cls` a hand close-up, `kd` the kick drum, `np` / `pnt` a head close-up, `lt` from behind, `cam` handheld; `all`, `crowd`, `stagedive`, `crowdsurf`, `bre` / `brej` (the big rock ending, from high up), `duo_x`.
- RB2's `auto` cuts: a shot that fits the constraints, chosen repeatably from the cut's index; focused members are its subjects.
- No cuts: one every two measures (`Director::BuildFallbackCuts`), wide at each new section, else on the busiest member (`Band::Activity`).

**The neck camera** (`Framing::Neck`) is mounted out past the guitarist's headstock and up off the fretboard, looking down the frets at an angle to the body and the player's face (`Band::NeckOf` reads the guitar's world matrix). It rolls with the guitar and has no drift or sway, but is steadied like a stabilised mount (eye, aim and roll eased at 5/s), so the beat's bob doesn't shake it. Through a guitar solo (PART GUITAR note 103; charts without it use the guitarist's `play_solo` state or a "solo" section), every other cut of the guitarist alone becomes the neck camera, except wide, behind and `no_close` / `only_far` cuts. A marked solo of six seconds or more that never cuts to the guitarist alone gets a `solo_neck` cut for its middle third (five seconds at most), then goes back to the shot it interrupted. `--venue-shot guitar_neck` (or `bass_neck`) holds it. Charts converted before note 103 was imported need converting again (Settings > Convert Custom DLC, or `--convert-dlc`) for their solo markers.

The follow spots track their member's chest every frame, so a soloist stepping out front stays lit.

Shots track the members' live positions, eased like an operator following them (`Director::Update`; snapped on a cut) so a headbang or a strum doesn't shake the whole picture, drift (a slow orbit and push-in) while held, and sway on top of the easing when handheld. The follow spots ease onto their member the same way (`VenueShow::Update`). Post-processing looks map to the camera's grading (`Director::GradeFor`): saturation, contrast, temperature and tint, bloom, vignette, and the engine's era colour depth and dither for the TV looks; they ease in over a few frames.

**The concert look** (`concert_bw`) is modelled on an arena show's screens filmed on a phone (2026-11-09): a live camera feed in black and white, washed out, glowing and grainy, and running at a lower frame rate than the show.
- **Where it comes from.** Rock Band's black-and-white looks all play as it: `photocopy` (Everlong's opening), `film_b+w`, `video_bw` and `film_silvertone`. Charts with no looks at all get it through their intros, bridges, breakdowns and quiet / spacey sections (`Director::BuildFallbackLooks`), back to the default grade at the next section. Charts with authored looks keep only their own.
- **Tone.** Saturation 0, then the toning LUT `Assets/Textures/LUTs/ConcertScreen.cube`, faded in by the grade's `Lut`: the luma mapped to a split tone with lifted, grey-brown blacks, rose mids and cream highlights, sampled off the phone clip. White balance runs before saturation in the tonemapper, so a saturation-0 look can't be tinted any other way. The main and program cameras carry the LUT at contribution 0 for every other look.
- **Grain.** The engine's `PostProcess::FilmGrain`.
- **Frame rate.** The grade's `FrameRate` (12) steps the venue. `VenueShow::Update` updates the whole venue (crowd, band, lyric board, director, lights, pyro) once a step, on the step's time with the time since the last step, and skips the update in between. The grain's pattern (`FilmGrainFrame`) changes with the step. The highway, an overlay camera, stays smooth, and held frames cost the venue nothing on the main thread.

`--venue-look concert_bw` holds it.

Two render-texture cameras feed the screens, each every other frame:

- The **program feed** (`StageProgram.rendertexture`, the LED wall) films exactly what the main camera shows, graded the same, as if the show were being broadcast live. In its own shot the wall is black (a camera never samples its own image), so in a wide shot the wall shows the show one level deep.
- The **close-up feed** (`StageFeed.rendertexture`, the side screens): the main shot's member, else whoever is busiest (the singer favoured), re-chosen every two measures from a pit position, slightly handheld.

## Settings and flags

- **Venue** (`Venue` in `Settings.json`): Band and crowd (2) / Band only (1) / Off (0: the highway on black, no light show — the rig lives in the venue).
- **Room** (`VenueStyle`): Arena (0) / Club (1) / Festival (2) / Random (3). F7 swaps it mid-song.
- **Venue Camera** (`VenueCamera`): Live show (0) / Music video (1).
- **Lyrics** (`Lyrics`): Both (3) / HUD (1) / Venue (2) / Off (0).
- `--no-venue` skips the venue; `--venue-only` fades the highway out entirely to frame the venue; `--venue-shot <name>` holds one shot (any cut name, or `debug_wall`); `--venue-look <name>` holds one post look; `--venue-time <seconds>` shows the venue that far into the song; `--venue-style N`; `--venue-swap-every <seconds>` swaps the room on a timer like F7; `--crowd-size N`; `--band-debug` logs the drummer's stick tips and hands twice a second. The engine's `--screenshot-every N` saves a numbered frame every N frames, to check motion headless.

```bash
# Frame a shot of Boston (track 2) a minute in, without the highway.
./Engine/Tools/NixEnv.sh env -u NIX_CC ./Engine/Tools/Headless.sh ./.build/Game_linux_Debug/Game_EntryPoint_x64 \
  --scene Assets/Example.lvl --play-track 2 --frames 150 --frame-time 0.016666667 --no-audio \
  --venue-only --venue-time 60 --venue-shot coop_g_near --screenshot shot.png --exit
```

## Caveats & Fragility

- **The venue and highway share a world.** Separation is by distance only: anything placed near `VenueLayout::kVenueOrigin` shows in the venue, and directional lights (the rig's dim key light) light both.
- **The highway's coverage is its depth.** Transparent highway pieces that don't write depth add over the venue rather than covering it.
- **RB2 camera note meanings** (61-64, 70-73) and the spotlight slot order (37 keys, 38 vocals, 39 guitar, 40 drums, 41 bass) follow community documentation, not an official spec; a wrong guess frames the wrong member, nothing worse.
- **Cost.** Five entities per posed crowd member (4,000 for the festival's), posed on the main thread: the front rows every frame; the middle and back every second or third frame (in turns) only when the frame rate keeps them at 60 updates a second or better, since at 60 fps the stepping showed. The back of the house adds four or five entities a figure but only one transform update. In a debug build the venue's main-thread update went from 2.0 to 3.6 ms (arena), 2.6 to 4.4 ms (festival) and 1.2 to 1.5 ms (club) at 60 fps with the back of the house and every-frame posing (`--highway-log`). Instancing keeps the draws to a few dozen batches. The engine's spheres and capsules are about 2,300 triangles each, so crowd arms are boxes and only the first rows get round heads (`Puppet::Look::Blocky`): a typical frame is 150-200k triangles across the three cameras, about 1.3M at the peak. `--crowd-size` or Venue: Band only trims it.
- The feed camera can't show its own screen: in its shot the LED wall is black (`Engine/Docs/Rendering-Pipeline.md` → Render textures).
- **Rock Band vocal data follows community documentation**: the lyric markers, phrases 105/106, percussion 96/97 and the hand/strum map names. Harmony parts to band members is a guess (HARM2 guitarist, HARM3 bassist), not chart data. The lyric atlas has no accented letters.
- **Plane primitives are 2 units across.** Size a `VenueKit` plane through `VenueKit::ScaleFor`, not `SetScale` with metres, or it draws twice the size (the lyric glyphs did).

## Related Docs

- `Docs/Stage-Lighting.md`: the light rig and its cues
- `Docs/Gameplay-Note-Highway.md`: the highway drawn over the venue
- `Docs/Songs-and-DLC.md`: the converter that writes `NoteData.txt`
- `Engine/Docs/Rendering-Pipeline.md`: overlay cameras and render textures
