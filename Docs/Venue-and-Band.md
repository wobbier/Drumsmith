# Venue and Band

> The stage dressing, effects, hype and camera pass against 278f82b plus those changes, 2026-11-12.
> Verified against game commit 5973499 plus the venue change, 2026-11-08; the concert look against 35a9edd plus the concert look change, 2026-11-09. Engine submodule at 0c32daef. The rigged band and the crowd's character pieces against 278f82b plus those changes, 2026-11-12, engine at 78e47156 plus the FBX skin repair. The crowd's packed atlas (ME-365) against 278f82b plus that change, engine at 78e47156 plus per-instance data, 2026-11-12.

The concert under the note highway: a stage with a band playing the song, a crowd reacting to it, the light show (`Docs/Stage-Lighting.md`) and a camera crew cutting between shots, all driven by the chart's Rock Band venue data and played on the song clock. The highway is drawn over it by an overlay camera, so the venue underneath can change without touching gameplay.

## Overview

- **Layers.** The venue is built 500 m from the highway (`VenueLayout::kVenueOrigin`), past either world's far plane, so neither camera ever sees the other's world. It used to be 4 km out, where world positions only resolve to half a millimetre and close-ups showed vertices crawling; under 512 m it's 30 microns. The venue's camera becomes the main camera; the highway's camera (`Main Camera` under `TrackMover` in `Assets/Example.lvl`) becomes an engine **overlay camera** (`Camera::Overlay`, `Engine/Docs/Rendering-Pipeline.md` → Overlay cameras) composited on top. Its far end fades into the venue (`OverlayFadeStart` / `OverlayFadeEnd`) and its dark board lets the stage show through (`OverlayDarkOpacity`); its own fog is turned off while the venue runs.
- **Procedural set and performers.** The architecture and auxiliary instruments use the engine's primitives with `DiffuseMaterial`s (`VenueKit`); pieces sharing a colour instance into one draw. The band members are a rigged, skinned character (`Performer`); the crowd's figures are the same character cut into five rigid pieces that instance (`Puppet`). Both are posed procedurally every frame, with no animation clips. Arena wings and front of house also use selected Synty speaker and equipment-case models, packaged locally under `Assets/Models/Venue` with their texture atlases and provenance. Lead and backing vocal mic stands use `Assets/Models/Instruments/Runtime/MicStand.obj` through `VenueKit::Prop`, retaining each performer's placement/yaw and scaling only Y from the authored 1.47 m shaft height. Guitar and bass use the runtime OBJ exports at their original body pivots/neck lengths. The drumkit uses separate shell/cymbal exports at the strike targets, with stationary hardware and existing hit reactions. The keyboard uses `Runtime/Keyboard.obj`, including the stand and sustain pedal, with the keys at the original hand-target height. These runtime exports compensate for Assimp's Z reflection.
- **Data first, fallbacks second.** Charts converted from Rock Band `notes.mid` carry camera cuts, post-processing looks, band animation states, drum limb notes, strums and sung notes (see *What is imported*). Charts without them (`.chart` songs, sparse MIDI) get the same show built from their sections, tempo and drum notes.

## Key Files

| File | Role |
|------|------|
| `Game/Source/Venue/VenueShow.h/.cpp` | Owns the venue: builds the rooms, set, band, crowd, director, lights and effects; turns the highway camera into the overlay; updates them on the song clock; the show's hype and its big moments |
| `Game/Source/Venue/StageSet.h/.cpp` | The stage's dressing: lattice truss and hoists, backline, riser, subs and barricade, wings, LED pieces that follow the show, each room's extras |
| `Game/Source/Venue/StageFx.h/.cpp` | Effects, all particle systems: flame pots, spark fountains, CO2 jets, confetti cannons, dry ice, dust, fireworks |
| `Game/Source/Venue/VenueLayout.h` | The floor plan: venue origin, stage size, member spots, crowd area |
| `Game/Source/Venue/VenueKit.h/.cpp` | Spawns primitive pieces (full sizes in, primitive scale worked out) and deletes them on `Clear` |
| `Game/Source/Venue/Performer.h/.cpp` | A band member's body: the rigged character posed through its skeleton (spine and head by angles, arms and legs by two-bone IK, hands that turn and grip) |
| `Assets/Models/People/BodyType1_Rigged.fbx` | A character, one of eight in the folder: Synty Polygon Town figures on one Rigify human skeleton, exported from Blender; their UVs index the Town atlases in `Assets/Models/Venue` |
| `Game/Source/Venue/Puppet.h/.cpp` | A crowd figure from the character's rigid pieces: legs, torso, head and an arm each side, posed by angles |
| `Game/Tools/MakeCrowdPieces.py` | Lists the rigged characters and cuts each into those pieces (Blender): a folder of OBJs each under `Assets/Models/People/Crowd`, and the cast list with their pivots in `Game/Source/Venue/People.generated.h`; packs the atlas variants into `Assets/Models/Venue/PolygonTown_Crowd.png` and lists its tiles there too |
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

`VenueShow::BuildStage` builds the stage, the same in every room: a 1.2 m deck, a drum riser, a back wall with the LED wall and speaker stacks. Screens are planes whose emissive slot is a render texture, flipped upright with Tiling (1, -1) and Offset (0, 1).

`StageSet` dresses it (`StageSet::Build`, per song from a seed of its title):

- **Rig.** Open-web lattice truss on the old layout (three cross trusses at z 0.2 / 4.6 / 9.0, four fore-aft runs, four towers), chains up to the room's roof, cable looms into the wings. The light rig hangs under it (`Docs/Stage-Lighting.md`).
- **Backline.** A wall of guitar stacks and bass cabinets behind the players, a keys corner when the chart has keys, pedalboards, wedges, setlists and tape marks, DI boxes, cables, flight cases.
- **Riser.** Trim, skirts, a rug under the kit, steps, and an LED fascia that pulses with the player's kick.
- **Front.** Subs along the stage front, lip fills, a segmented barricade, a camera track in the pit.
- **Wings.** Guitar world on one side (a rack of spare guitars, a tool chest), the monitor desk and racks on the other.
- **Pixels.** The stage-edge strip, tubes up the towers, battens along the trusses and the LED wall's panel seams. They have no lights of their own: `StageSet::Update` tints them from the rig's colour, the beat, the kick and the hype.
- **Per room.** Arena: a front-of-house truss and cameras at the mix position. Club: posters and a merch table. Festival: scaffold PA towers, banners, festoon lights, food stalls, a truck and a tour bus behind the stage, flags in the field.

Imported props are Synty models packaged under `Assets/Models/Venue` (`README.md` there lists each source and size). Every prop the set uses is in one table at the top of `Game/Source/Venue/StageSet.cpp` with its yaw, and is skipped when its file is missing.

The room around it is a `VenueShow::Style`:

| Style | Room | Crowd |
|-------|------|-------|
| Arena | A big dark hall under a roof with a rigging grid: the floor full back to the mixing desk and past it, seven tiers of stands at the back and three along each side (aisle lights on every step), PA hangs and screens either side of the stage, exit signs | 520 posed + about 1,600 in the back of the house |
| Club | Brick walls close in, a low ceiling, neon tubes on the walls, a bar at the back; thicker haze | 240 posed, packed to the bar |
| Festival | Open air at night (the main camera's procedural sky at 22:00, a full moon), a canopy over the stage, screens on towers, delay towers and a mixing tent in the field; thinner haze | 800 posed, the field full to the delay towers and thinning out to 66 m |

`BuildArenaDetail` adds a cyan portal frame, segmented cyan/amber LED fins flanking the main screen, pleated wing curtains, stage access stairs, detailed PA grilles, open-web roof trusses, acoustic wall bays and concourse fascias. Synty speakers and cases dress the wings and mixing platform; railings and console faders detail front of house. Static accents use restrained emission and no additional lights or per-frame animation. All props are owned by `VenueKit`, so room swaps clear them with the rest of the set.

**Room** in settings picks one (or Random: one per song, repeatable by title). **F7** during a song tears the venue down and builds the next room in its place (`VenueShow::NextStyle`); the highway on top carries on, which is the point of the layering. The director keeps wide shots inside the room (`Director::SetRoomBack`).

### The band

`Band` places each member at `VenueLayout::kMemberSpots`, facing the crowd. Keys only appear when the chart has a keys part.

**The cast.** `People::kPeople` lists every rigged character in `Assets/Models/People` (the tool writes it). `Band::Build` gives each member on stage a different one, and a different atlas variant, stepping through both lists from a seed of the song, so a song always has the same band; the characters left over are the crowd's (`Band::SpareModels`, `Crowd::SetModels`). With fewer characters than members they repeat, and the crowd then draws on all of them.

**The body.** A member is a rigged character (`Performer::Look`: a model, the atlas its UVs index, and where its mouth is), loaded when the venue is built and posed by `Performer::Apply` from a `Performer::Pose`, the same kind of description the crowd's puppets take:

- **Spine and head** turn by angles (lean, side, turn; nod, head turn and tilt). The spine's turn is shared over its three bones, the head's over the neck's two and the head.
- **Arms** reach for a point (`Arm::Reach`: the palm's centre lands on `Target`, the elbow bends toward `Pole`) or swing by angles; either way the upper arm and forearm are bent by the engine's two-bone solver (`IK::SolveTwoBone`, `Engine/Docs/Animation.md` → Inverse kinematics). The hand can be told which way its fingers point and what its palm faces (`Arm::Fingers`, `Arm::Palm`; the wrist bends up to 70 degrees, and half of the hand's twist goes into the forearm), and how far its fingers curl (`Arm::Grip`). The palm's centre is what reaches the target, so a reaching arm is solved twice: once for a straight wrist, then for the wrist that puts the turned palm on its mark.
- **Legs** plant their feet (out to the side by `Leg::Spread`) and bend at the knee as the hips drop (`Pose::Crouch`, or a stance too wide for straight legs); a seated figure's feet reach for a point (`Leg::Reach`). `Leg::Toe` pitches a foot about its ball, so a pedal stroke lifts the heel.
- **The mouth** is a dark piece on the face that opens with `Pose::Mouth` and hides when shut: the character has no jaw bone.

The character's facing, limb lengths and hand layout are read from its bind pose (`Performer::Bind`), so another T-posed Rigify human can stand in by path. The pose is worked out in `Performer` and only written to the model's nodes (`Model::GetNodeTransform`); nothing is read back, and a `Performer::Stand` followed by an `Apply` of the same pose does the body once.

- **Drummer.** The stick tips follow per-limb stroke lists: the chart's animation notes when it has them (feet from its kick and hi-hat pedal gems), else `Band::DeriveStrokes` assigns its gems to limbs (notes struck together go left-most piece to the left hand; cymbals and the floor tom to the right hand, the snare to the left, alternating in fast runs and tom fills). `Band::StickTip` arcs each tip from stroke to stroke, as high as the gap allows, and lands it on the piece at the note's time; the hand sits a stick's length behind the tip, a fist palm down with the stick across it, and the arm reaches for it (IK). Struck cymbals rock, drums squash. They sit on the throne with a foot on each pedal; kick and hi-hat-pedal notes press them, heel up.
- **Guitarist and bassist.** The guitar hangs ahead of the torso with its neck yawed forward 14° and its face tilted upward 12°, leaving room for the picking forearm. Guitar and bass offsets are 0.30 m / 0.33 m in front of the spine. `Band::SwingInstrument` follows position at 14 rad/s (damping 0.75) and rotation at 10 rad/s (damping 0.65), stepped at 240 Hz. This retains strap swing while passing more torso/beat motion through to the instrument-mounted neck camera. Hands reach for the resulting instrument transform. Guitar and drummer elbows are guided outward and forward; instrument reaches use `Arm::ClearTorso` to keep wrists crossing the chest in front of it. The strumming hand moves down on even strums and up on odd ones; the fretting hand follows the chart's hand-position notes (else moves every few strums). States: `idle` (hands still, looking around), `play` (bobbing), `mellow` (swaying), `intense` (headbanging, wide stance), `play_solo` (walking out front over about a second, leaning back, neck up, a follow spot on them). During a singalong they ease in to their mic (not mid-solo). Their bob rises over the first 15% of each beat (`SoftPulse`) rather than jumping on it like the others', since their guitar necks swing with it. The guitar has frets, a nut and strings for the neck camera. The fretting hand cups the neck's lower edge from underneath, its fingers curled round onto the fretboard; the strumming hand hangs over the strings. The chart's hand maps shape the fretting hand: `HandMap_Chord_X` holds that open chord's shape in the first frets, `AllChords` wraps the hand round the neck, `NoChords` and `Solo` hop it along the neck per note (further for a solo), `DropD` / `DropD2` keep it near the nut and lift it off the strings as they're struck; `StrumMap_SlapBass` slaps over the neck pickup. Charts without maps play as `HandMap_Default`.
- **Singer.** At the mic for a whole line, a hand round the stand under it, short rests and breaths included, the mouth opening through each sung note (`Band::AwayFromMic`). Only a break between lines of about five seconds or more sends them off: they linger 0.8 s after the line, walk out over 1.2 s, and are back at the mic 1.2 s before the next line starts, all from the song clock (the same at any frame rate or after a seek). A line is the chart's phrase (notes 105/106) when it has them, else a run of sung notes; Rock Band's phrases also cover percussion sections, so the singer plays those at the mic. Out front they jump and fist-pump when it's intense; otherwise each break gets one habit: clapping over their head, an arm swept across the crowd, or just walking.
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

**The figure.** Everyone in the crowd is one of the characters the band isn't using. Hundreds of skinned figures would each be a draw of their own, so `Game/Tools/MakeCrowdPieces.py` cuts each character into rigid pieces by which bones its faces follow (the legs with the hips, the torso, the head, an arm each side), each an OBJ about its own pivot, at full detail (1,640 to 2,330 triangles a figure) and decimated (490 to 700). `Puppet` turns the pieces about those pivots: the torso leans from the hips, the head nods at the neck, the arms swing straight from the shoulder and shorten as the elbow bends. Pieces of one model instance into one draw (`VenueKit::Part`). The first 4.5 m of rows get the full pieces, the rest the decimated ones. To add or change a character, put its rigged FBX in the folder and run the tool again (two exports of one mesh count once). Figures differ by character, height, build and which of the atlas variants they wear (`VenueKit::Skin`: every `Assets/Models/Venue/PolygonTown_NN_L.png` there is, twelve today), picked per figure from its seed. The crowd draws them all from one texture, `PolygonTown_Crowd.png`: the tool packs the variants into a 4 x 3 grid of unchanged 2048 tiles (8192 x 6144; each tile's mips come out byte for byte the variant's own), and lists the tiles in `People.generated.h` (`People::kSkins`). `VenueKit::Part` gives a piece the packed atlas, a material tiling of one tile, and its tile as per-instance data (`Mesh::InstanceData`, which the engine's Standard vertex shader adds to the uv; `Engine/Docs/Rendering-Pipeline.md` → Per-instance data), so pieces batch per character and piece only, whatever the figure wears (ME-365). In the arena's crane shot that took the crowd from 404 instanced draws (about 4 instances each) to 42, twice over with the depth prepass. A variant missing from the atlas (added since the tool last ran), or a texture size cap below 8192 (a hardware profile's `MaxTextureSize`, which would shrink every tile) or a GPU that can't take it, falls back to the variant's own texture: the same picture, a batch per character, piece and atlas as before. The band's skinned members still use the separate variants.

The posed crowd stops after its few hundred figures, well short of the back of most rooms, so `VenueShow::FillHouse` fills the rest with the **back of the house** (`Crowd::AddMob`): the decimated figure with its body in one piece and its two arms (hanging, or turned up), sometimes a lighter or phone, moved as one, one transform a figure a frame, wherever the posed crowd doesn't stand (`Crowd::KeepClear` leaves the mixing desk, towers and stand aisles empty). They follow the same mood: bobbing, fists and hands up, jumping when it's intense, lights up and swaying when it's mellow. A cap thins an area evenly rather than leaving its back empty. Phone-holders film the intense parts with their phones up, now and then flashing a photo. On the chart's `crowdsurf` / `stagedive` shots (and every so often when it's intense) a crowd surfer is carried over their heads to the barricade by the hands under them. The director cuts to them as they go up (see *The cameras*).

### Hype and effects

`VenueShow::UpdateHype` keeps one number for how hot the show is running, 0 calm to 1 peak: the chart's crowd mood (mellow 0.2, normal 0.45, intense 0.75) weighted three to one against the player's streak, plus an afterglow for six seconds after each big moment. The rig, the cameras and the set's LED pieces read it every frame.

A **big moment** (`VenueShow::BigMoment`) comes in two sizes:

| | When | What goes off |
|---|---|---|
| Lift | Each chorus or intense passage as it starts; every fifty notes in a row | CO2 jets, a hit on the blinders and strobes, a camera shake, a cheer (and two fireworks out of doors) |
| Peak | The last of those in the song (the finale), the song's end, the player reaching the top multiplier (30 in a row) and every hundred, at most once in 45 s | The jets, spark fountains, confetti cannons, a flame burst, four fireworks, the whole rig to white, and the cameras cut to a hero shot for two measures (`Director::OnBigMoment`) |

Lifts are at least 12 s apart and peaks 3 s. The chart's peaks are found at build (`m_peaks`): `[crowd_intense]` as it begins and sections named chorus, merged when within 12 s of each other.

`StageFx` is the effects themselves, each an engine `ParticleSystem` on an emitter the kit owns (`Engine/Docs/Cores-and-Components-Reference.md` → ParticleSystem):

- **Flame pots** (four along the stage front): a bright core column, flame and ember particles and a point light each. They fire on the chart's `[bonusfx]` on the song clock, and on a peak.
- **CO2 jets** (six): lit alpha particles, so the plumes take the colour of the beams they rise through.
- **Spark fountains** (four): stretched additive streaks that arc over and die before they land.
- **Confetti** (four cannons on the front truss, two at the stage's front corners): square paper (`Assets/Textures/Venue/Confetti.png`), a pair of colours a cannon, drifting for five to nine seconds. Half the load in the club.
- **Dry ice**: a low lit bank over the deck, full in mellow passages and gone in intense ones.
- **Dust**: lit specks over the stage that only show where a beam finds them.
- **Fireworks** (festival only): six shells that burst in the sky behind the stage.

Stage Lights set to no flashes softens the flames and sparks. `--venue-moment N` fires a peak every N seconds, to tune them.

### The cameras

`Director` holds the cut list (VENUE's, or MV VENUE's when **Venue Camera** is Music video and the chart has one) and frames the latest cut each frame:

- `coop_<who>_<framing>`: `who` is `all`, `front` or member letters (`d`, `g`, `b`, `v`, `k`, pairs like `gv`); framing `far`, `near`, `behind`, `closeup_head`, `closeup_hand`.
- `directed_<who>[_<style>]`: `cls` a hand close-up, `kd` the kick drum, `np` / `pnt` a head close-up, `lt` from behind, `cam` handheld; `all`, `crowd`, `stagedive`, `crowdsurf`, `bre` / `brej` (the big rock ending, from high up), `duo_x`.
- RB2's `auto` cuts: a shot that fits the constraints, chosen repeatably from the cut's index; focused members are its subjects. A chart cut is one shot, held until the next cut, so an `auto` held for more than 10 s (one dropped in the Track Editor with nothing after it) hands that stretch to the director: its own shot, then the cuts a chart without cameras would get there, up to a second before the next chart cut (`Director::FillAutoCuts`). A constrained one (`auto only_close`, `auto focus_drums`) keeps its constraints on every cut of the stretch. Other shot names hold however long they're left. `--highway-log` lists the cuts as built.
- No cuts: `Director::BuildFallbackCuts` cuts on downbeats, paced by the section (every measure in choruses with half-measure flurries, two in verses, four in intros and mellow parts), opens each section wide, favours the busiest member (`Band::Activity`) and never repeats a subject and framing back to back.

**The crew's shots.** Beyond the chart's framings the director has a crane that booms up out of the pit (or down into it), a dolly trucking along the pit rail, a drone over the crowd, a slow high orbit, a long lens from the mixing desk, a crowd's-eye view from a few rows back, a profile from the wings, the kit from overhead and from low through the cymbals, reverses over a member's shoulder at the crowd, a low hero angle at a player's feet, a fast push, and an operator at a half sprint down the photo pit with the camera on their shoulder, shooting ahead and across the front row and turning at each end (`Framing::PitRun`; its footfalls jar the picture by the ground covered). `Director::Vary` picks among them for the chart's plain shots by the cut's variant (bits 2-3), so a song's third wide isn't its first again: all-far becomes a crane, drone, orbit or long lens, all-near a dolly or profile, a member's near shot a low hero, `directed_crowd` the crowd's view or the pit run. The fallback cuts' high-energy crowd shots are the pit run half the time. Authored styled shots (`directed_x_cam` and the like) and the big rock ending are shot as asked. `--venue-shot cam_<kind>[_<member letters>][_<variant>]` holds one: `cam_crane`, `cam_dolly`, `cam_drone`, `cam_orbit`, `cam_foh`, `cam_crowd`, `cam_side`, `cam_drumtop`, `cam_drumlow`, `cam_reverse`, `cam_hero_g`, `cam_push`, `cam_run`. A close-up asked to focus on two members takes one of them.

**The room.** `Director::SetRoom` gives the back wall, ceiling, half width and mixing desk; cameras stay 2 m under the ceiling and 1 m inside the walls.

**Lens.** The neck camera, the pit run and the crowd's-eye view are seen through a fisheye with colour fringing (`Director::LensFor`, the engine's `PostProcess::LensDistortion`), their field of view widened to keep the framing; the lens changes with the cut. Near shots, close-ups, the kick, the low angles and the long lens have depth of field (`Director::ApplyFocus`): the focus follows the subject and the aperture is solved per shot for the same background blur, so the lights behind a player are soft discs whatever the lens. The closer the subject, the further exposure is pulled down (to -1.1 stops at 1.5 m), since the rig is balanced for the wide picture and burns out a white shirt up close.

**Energy.** Hype scales handheld sway and how fast a move runs, and adds a small push on each beat (1.2% of the field of view at most, none while a look steps the venue). `Director::Kick` shakes the camera for pyro and big moments. Moves keep creeping for as long as a shot is held.

**The neck camera** (`Framing::Neck`) is mounted out past the guitarist's headstock and up off the fretboard, looking down the frets at an angle to the body and the player's face (`Band::NeckOf` reads the guitar's world matrix). It's bolted on like a GoPro on the headstock: no easing, drift or sway, it moves and rolls exactly as the guitar does. What keeps it from snapping is the guitar itself floating on its strap (`Band::SwingInstrument`, above), not the camera. Through a guitar solo (PART GUITAR note 103; charts without it use the guitarist's `play_solo` state or a "solo" section), every other cut of the guitarist alone becomes the neck camera, except wide, behind and `no_close` / `only_far` cuts. A marked solo of six seconds or more that never cuts to the guitarist alone gets a `solo_neck` cut for its middle third (five seconds at most), then goes back to the shot it interrupted. `--venue-shot guitar_neck` (or `bass_neck`) holds it. Charts converted before note 103 was imported need converting again (Settings > Convert Custom DLC, or `--convert-dlc`) for their solo markers.

The follow spots track their member's chest every frame, so a soloist stepping out front stays lit.

**The crowd surfer.** When a crowd surfer goes up, the main camera cuts away from whatever is scheduled to a handheld shot that follows them (`Framing::Surfer`, shot name `follow_surfer`). It sits on a camera platform at the front of the pit, across the room from where they went up, and looks down on them so they read against the crowd rather than among its raised arms. It starts zoomed in, with about four metres of crowd across the frame, and widens as they come closer. When they reach the barricade it cuts back to the scheduled shot (`Director::FollowSurfer`, fed each frame from `Crowd::SurferUp`).

**Lead room.** The highway runs up the middle of the screen, so a shot of one member (near, a head or hand close-up, or far on them) isn't centred on them: the aim is turned so they stand 60% of the way out to one side, clear of the highway at head height, looking across the frame toward it. The side is the one they're looking away from (`Band::GazeOf`, the head's facing), chosen on the cut and held for the shot, so a turn of the head doesn't swing the picture. When they look straight down the lens, their side of the stage decides. Group shots, the neck camera, shots from behind, the kick drum and the crowd stay as framed (`Director::LeadSideFor`, `LeadRoom`).

Shots track the members' live positions, eased like an operator following them (`Director::Update`; snapped on a cut) so a headbang or a strum doesn't shake the whole picture, drift (a slow orbit and push-in) while held, and sway on top of the easing when handheld. The follow spots ease onto their member the same way (`VenueShow::Update`). Post-processing looks map to the camera's grading (`Director::GradeFor`): saturation, contrast, temperature and tint, bloom, vignette, and the engine's era colour depth and dither for the TV looks; they ease in over a few frames.

**The concert look** (`concert_bw`) is modelled on an arena show's screens filmed on a phone (2026-11-09): a live camera feed in black and white, washed out, glowing and grainy, and running at a lower frame rate than the show.
- **Where it comes from.** Rock Band's black-and-white looks all play as it: `photocopy` (Everlong's opening), `film_b+w`, `video_bw` and `film_silvertone`. Charts with no looks at all get it through their intros, bridges, breakdowns and quiet / spacey sections (`Director::BuildFallbackLooks`), back to the default grade at the next section. Charts with authored looks keep only their own.
- **Tone.** Saturation 0, then the toning LUT `Assets/Textures/LUTs/ConcertScreen.cube`, faded in by the grade's `Lut`: the luma mapped to a split tone with lifted, grey-brown blacks, rose mids and cream highlights, sampled off the phone clip. White balance runs before saturation in the tonemapper, so a saturation-0 look can't be tinted any other way. The main and program cameras carry the LUT at contribution 0 for every other look.
- **Grain.** The engine's `PostProcess::FilmGrain`.
- **Frame rate.** The grade's `FrameRate` (12) steps the venue. `VenueShow::Update` updates the whole venue (crowd, band, lyric board, director, lights, pyro) once a step, on the step's time with the time since the last step, and skips the update in between. The grain's pattern (`FilmGrainFrame`) changes with the step. The highway, an overlay camera, stays smooth, and held frames cost the venue nothing on the main thread.

`--venue-look concert_bw` holds it.

Two render-texture cameras feed the screens, each every other frame (when a look steps the venue, as the concert look does at 12 fps, about once a step instead: `Director::SetFeedStepRate` sets their `UpdateInterval` to frames per step, so the screens don't re-render an unchanged picture):

- The **program feed** (`StageProgram.rendertexture`, the LED wall) films exactly what the main camera shows, graded the same, as if the show were being broadcast live. In its own shot the wall is black (a camera never samples its own image), so in a wide shot the wall shows the show one level deep.
- The **close-up feed** (`StageFeed.rendertexture`, the side screens): the main shot's member, else whoever is busiest (the singer favoured), re-chosen every two measures from a pit position, slightly handheld.

## Settings and flags

- **Venue** (`Venue` in `Settings.json`): Band and crowd (2) / Band only (1) / Off (0: the highway on black, no light show — the rig lives in the venue).
- **Room** (`VenueStyle`): Arena (0) / Club (1) / Festival (2) / Random (3). F7 swaps it mid-song.
- **Venue Camera** (`VenueCamera`): Live show (0) / Music video (1).
- **Lyrics** (`Lyrics`): Both (3) / HUD (1) / Venue (2) / Off (0).
- `VenueShow::SetPresentation` chooses what reaches the screen: `Both` (a play), `HighwayOnly` (the highway's camera takes the screen back and the venue stops updating) or `VenueOnly` (the highway overlay fades out, as `--venue-only`). The Track Editor's preview switches between them; it is kept across `Build` and `Clear`.
- `--no-venue` skips the venue; `--venue-only` fades the highway out entirely to frame the venue; `--venue-shot <name>` holds one shot (any cut name, or `debug_wall`); `--venue-look <name>` holds one post look; `--venue-time <seconds>` shows the venue that far into the song; `--venue-style N`; `--venue-swap-every <seconds>` swaps the room on a timer like F7; `--venue-moment <seconds>` fires a peak that often; `--venue-eye "x,y,z,tx,ty,tz[,fov]"` puts the main camera anywhere in venue space, to inspect the set; `--highway-log` also logs each cut and big moment; `--crowd-size N`; `--band-debug` logs the drummer's stick tips and hands twice a second. The engine's `--screenshot-every N` saves a numbered frame every N frames, to check motion headless.

```bash
# Frame a shot of Boston (track 2) a minute in, without the highway.
./Engine/Tools/NixEnv.sh env -u NIX_CC ./Engine/Tools/Headless.sh ./.build/Game_linux_Debug/Game_EntryPoint_x64 \
  --scene Assets/Example.lvl --play-track 2 --frames 150 --frame-time 0.016666667 --no-audio \
  --venue-only --venue-time 60 --venue-shot coop_g_near --screenshot shot.png --exit
```

## Caveats & Fragility

- **The dressing is placed by hand in code.** `StageSet` knows where the band stands, the light rig hangs and the effects fire only by the numbers in `VenueLayout` and comments: move a member spot or a fixture and check the set around it. Its low shots (the low hero, the profile from the wings) pass close to wedges and cases.
- **Effects run on real time.** Particles are simulated by the engine each frame, not on the song clock: a seek or the concert look's low frame rate doesn't rewind or step them.
- **The venue and highway share a world.** Separation is by distance only: anything placed near `VenueLayout::kVenueOrigin` shows in the venue, and directional lights (the rig's dim key light) light both.
- **The highway's coverage is its depth.** Transparent highway pieces that don't write depth add over the venue rather than covering it.
- **RB2 camera note meanings** (61-64, 70-73) and the spotlight slot order (37 keys, 38 vocals, 39 guitar, 40 drums, 41 bass) follow community documentation, not an official spec; a wrong guess frames the wrong member, nothing worse.
- **The cast is a generated list.** A character dropped into the folder isn't used until `Game/Tools/MakeCrowdPieces.py` has run. The same goes for an atlas variant: until the tool packs it, the crowd draws it from its own texture (correct, but a batch of its own). Rerunning the tool rewrites every character's OBJs, and the decimated pieces don't always come out the same (Son_01's differed on 2026-11-12), so check `git status` on `Assets/Models/People/Crowd` afterwards. Each model's material is set in code (`Performer::Bind`): the FBX names no texture and imports grey.
- **The rig is assumed, not checked.** `Performer` looks bones up by Rigify's names and expects a T-pose with the palms down; a model missing one logs it and stands unposed. The mouth piece's place (`People::Person::Mouth`) is the tool's guess from the face's surface beside the centre line.
- **Blender's FBX exports need the engine's skin repair.** The mesh sits at the scene root 100x and turned, which Assimp leaves out of the bone offsets; the cook puts it back (`Engine/Docs/Animation.md` → Import). A model cooked before that draws a hundredth of its size: delete its `.assbin` to cook it again.
- **Band cost.** Each member is one skinned draw a camera (three cameras; skinned meshes don't instance) and casts shadows with the rest of the set. Before shadows were enabled, in a debug build `Band::Update` went from 0.14 ms a frame with primitive figures to 0.25 ms (four members, Journey, under lavapipe).
- **The crowd's seams are open.** The pieces are cut from one skin, so a raised arm shows the hole at its shoulder from close up, and a bent elbow is a shorter straight arm.
- **Cost.** Five entities per posed crowd member (4,000 for the festival's), posed on the main thread: the front rows every frame; the middle and back every second or third frame (in turns) only when the frame rate keeps them at 60 updates a second or better, since at 60 fps the stepping showed. The back of the house adds three or four entities a figure but only one transform update. With the character's pieces the festival's update measured 4.3 ms (debug, lavapipe), as before, but the crowd is far more triangles than the boxes were: about 1.2M a camera for a full arena (120 full figures, 400 decimated, 1,600 at the back), where a whole frame used to be 150-200k. In a debug build the venue's main-thread update went from 2.0 to 3.6 ms (arena), 2.6 to 4.4 ms (festival) and 1.2 to 1.5 ms (club) at 60 fps with the back of the house and every-frame posing (`--highway-log`). Instancing keeps the draws to one batch per character and piece (and level of detail), not per figure or per atlas variant. `--crowd-size` or Venue: Band only trims it.
- The feed camera can't show its own screen: in its shot the LED wall is black (`Engine/Docs/Rendering-Pipeline.md` → Render textures).
- **Rock Band vocal data follows community documentation**: the lyric markers, phrases 105/106, percussion 96/97 and the hand/strum map names. Harmony parts to band members is a guess (HARM2 guitarist, HARM3 bassist), not chart data. The lyric atlas has no accented letters.
- **Plane primitives are 2 units across.** Size a `VenueKit` plane through `VenueKit::ScaleFor`, not `SetScale` with metres, or it draws twice the size (the lyric glyphs did).

## Related Docs

- `Docs/Stage-Lighting.md`: the light rig and its cues
- `Docs/Gameplay-Note-Highway.md`: the highway drawn over the venue
- `Docs/Songs-and-DLC.md`: the converter that writes `NoteData.txt`
- `Engine/Docs/Rendering-Pipeline.md`: overlay cameras and render textures
