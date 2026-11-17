# Gameplay: The Note Highway

> Verified against the working tree on 2026-11-08 (the gameplay rewrite, not yet committed). Engine submodule at 8cee2340.
>
> Updated 2026-11-17 against the working tree (the Linear ticket pass, DRU-14 to DRU-54, on game commit 4f29840; engine submodule at c5bb6135): double bass kicks, the resume run-up, the countdown's start marker, average timing and the `--practice` / `--pause-at` flags. The rest is as last verified.

`NoteHighwayCore` end to end: how a selected track becomes notes on the highway, the song clock, how hits are judged and scored, what the player sees and hears, and the end of a song. Appendix: the experimental vocals mode.

## Overview

`NoteHighwayCore` is a scene-loaded core (declared in `Assets/Example.lvl`) filtering on `Transform + NoteTrigger`. It receives `LaunchPlayTrackEvent`, builds a state per chart note (spawning gems only for the stretch of highway in view), lays the lanes out for that chart, starts the stems after a lead-in, and every frame advances its own song clock, judges keyboard and MIDI hits per lane, marks passed notes as misses, moves the highway, and fills the `in_game` view model the HUD in `Assets/UI/InGameMenu.rml` shows.

## Key Files

| Path | Role |
|------|------|
| `Game/Source/Cores/NoteHighwayCore.h` / `.cpp` | The core: clock, lanes, judging, score, HUD values |
| `Game/Source/Components/NoteTrigger.h` | Per-note data on each note entity |
| `Game/Source/Midi/MidiDevice.h` / `.cpp` | Timestamped MIDI queue (RtMidi callback) |
| `Assets/Prefabs/Notes/DrumGem.prefab`, `CymbalGem.prefab`, `CymbalRing.prefab`, `KickBar.prefab` | The note models (`Assets/Models/Notes/`), each with a diffuse and an emissive ramp texture (`Assets/Textures/Notes/`) |
| `Tools/NoteAssets/build.py` | Generates those models and textures (plain Python; see "Note models" below) |
| `Assets/Example.lvl` | Gameplay scene: lane entities, `TrackMover` (camera, its fog, the strike `Bar`), the cores |
| `Assets/Prefabs/Highway/HighwayBox.prefab` | The unit cube every highway piece and note marking is spawned from (plain white texture) |
| `Assets/UI/InGameMenu.rml` / `.rcss` | HUD, countdown, results, pause menu |

## How It Works

### Track setup

`SetupTrack( track, index )` (from `LaunchPlayTrackEvent`, or `--play-track <index>` on the command line):

1. `ShutdownTrack()` deletes the previous notes and stops audio.
2. `TrackData::LoadNoteData()` reads `NoteData.txt` (pad, stroke, velocity per note, and the beat grid); notes are sorted into one time-ordered list per lane (`m_laneNotes`). Open and closed hi-hat share a lane (the stroke tells them apart, below); the hi-hat pedal has its own.
3. `LayoutLanes()` places only the columns this chart uses (`ShowsColumn()`: the three toms appear together if any tom is charted), left to right: crash, hi-hat, splash, snare, high/mid/floor tom, ride, second crash, china. The pedal draws in the hi-hat's column. Spacing is up to 1.8 units, shrunk so the highway is at most 8 units wide with every column at full width; tom columns are then drawn at 0.7 of that (`kTomLaneScale`, `LaneWidth()`), so a kit with toms comes out narrower than the cap; the kick stays at the centre as a bar across all columns, and the strike `Bar` is scaled to the same width.
4. `BuildHighway` adds the highway pieces, and `BuildBeatLines` reads the beat grid (below).
5. Each frame `UpdateWindow` spawns the notes and beat lines on the visible highway: from the back end (`kHighwayBehind`) to the far end (`kHighwayLength`), plus half a second each side, so a gem has its colour before it comes into view. Whatever leaves that stretch is deleted. Only these have entities: the renderer visits every entity each frame, seen or not, so a dense chart (3,649 notes and 885 beat lines in Beast and the Harlot) kept around 5,000 entities alive for the whole song. Now it keeps about 150. `SpawnNote` builds each note in its lane at `Z = time × speed`, shaped by pad and stroke (the table below). Each lane keeps its live range (`LaneNotes::Live`, binary-searched by time), so a frame touches only the notes entering or leaving it.
6. The `AudioPack` starts loading the stems; the clock is set to `-kLeadInMs` (2 s).

Speed is the chart's `NoteSpeed` times the player's **Highway Speed** (`GameSettings::HighwaySpeed`, 50-200%, on the settings page and in the pause options). Changing it mid-song moves every spawned note and beat line to its new place (`ApplySpeed`); the window then spawns or deletes at the new speed.

Colours come from `PadUtils::GetNoteColor`, pushed away from grey (`Vivid`). A note shows its colour as a glow (`EmissiveColor`), since the scene has no lights; its material colour stays near white and only lights the pale base. Every colour goes through `Tint`, which applies it once the mesh's model has bound: binding (`Mesh::BindModelMesh`) rebuilds the material from the prefab's saved one, which would undo an earlier colour.

### Note shapes

| Note | Shape |
|------|-------|
| Kick | A low orange bar with pointed ends, lying on the highway under the other notes and reaching just past the rails. It is deeper front to back than a gem, so it shows either side of a note on the same beat |
| Double bass kick | The bar on its foot's half of the highway (right foot right, left foot left), with a thin line across the other half |
| Snare, toms | A rounded gem on a bright base (`DrumGem.obj`), standing on the highway |
| Hi-hat, crashes, ride, splash, china | A bowed disc with a bell (`CymbalGem.obj`), floating above the lane and the kick |
| Open hi-hat | The disc with its middle open (`CymbalRing.obj`) |
| Hi-hat pedal | A small kick-shaped bar in the hi-hat column, with its own small target pad |
| Rimshot (cymbal: edge) | White strip along the near edge |
| Cross-stick | White bar down the left side |
| Bell | White dot on the cymbal's bell |
| Ghost (velocity ≤ 40) | 70% size, lower, dim |
| Accent (velocity ≥ 120) | Taller, glows brighter |

Markings are separate entities in the note's lane (`NoteState::Decorations`), hidden, greyed and moved with their note.

**Note models.** `python3 Tools/NoteAssets/build.py` writes the four models and their textures; delete the cooked `.assbin` / `.dds` twins afterwards and a tools build recooks them. Each model is one unit wide with its base at y = 0, so a note's x scale is its width. Every vertex's v is a place on a ramp (base trim, seam, body, crest, top) and the two textures say what each place looks like: the emissive ramp is multiplied by the note's colour and by the prefab's `EmissiveIntensity` (6), so the trim and crest go past white and bloom while the body keeps its colour. Changing the look is a matter of editing the ramps in `textures()`; changing a shape means updating the heights in `NoteHighwayCore.cpp` (`kGemTop`, `kCymbalBellTop`...) that place the markings. The textures are square on purpose: as 32 × 512 strips they rendered striped wherever they were minified.

**Double bass** (`KickFeet::Assign` in `Game/Source/CoreGame/ChartAdvice.h`, called from `NoteHighwayCore::AssignKickFeet`). Where a chart marks kicks for the second pedal (`NoteData::m_secondPedal`, Rock Band's 2x kick note), those are the left foot's, and an unmarked kick within 260 ms either side of one is the right foot's. A chart with no marks is read by spacing: a run of three or more kicks no more than 150 ms apart alternates, right foot first; two quick kicks stay full bars (one foot plays those). Every other kick is a full bar. Judging doesn't know feet: either pedal hits either bar.

### The highway

The camera sits 10 units up and 16 behind the strike bar, tilted 24° down, with a 32° vertical field of view. The narrow view keeps a note's screen speed nearly even over its approach (it about quadruples between 2 s out and the bar, where the old close, wide camera multiplied it about tenfold). Black fog on the camera's `PostProcess` (from 45 units) fades the far end; bloom is on and AO off.

Built per chart from `HighwayBox.prefab`:

| Piece | Where | Shows |
|-------|-------|-------|
| Surface | Child of `TrackMover`, from 6 units behind the bar to 120 ahead | A near-black plane under the lanes |
| Rails and dividers | Same | Brighter edge rails, faint lines between lanes |
| Target pads | Same, at the bar | One per lane in its colour; a hit lights it, fading over 0.15 s. Kick hits flash the strike bar orange |
| Beat lines | Song space (under the kick lane), at each beat's time | Faint beat lines, brighter and thicker measure lines |

Beat and measure lines come from the chart's own tempo map: `notes.mid` next to the song, read with `smf::MidiFile` (tempo changes through `getTimeInSeconds`, measures from time-signature events, 4/4 until the first). Charts without a `notes.mid` (12 of the 20 in `Assets/DLC/` today, including every native chart) get none: `TrackData`'s BPM is a placeholder and wrong lines read worse than none.

### The song clock

`m_songTimeMs` is the song position the game works from:

| State | Clock |
|-------|-------|
| Loading | Held at −2000 ms until every stem is loaded |
| LeadIn | Advances by frame time; at 0 the stems start (`AudioPack::Play`, DSP-scheduled) |
| Playing | Advances by frame time (the running average while frames are steady, so vsync's measured-time wobble doesn't judder the highway and venue; the real time on a late frame); whenever FMOD's position moves (once per mixer block) it measures the gap, and the following frames close it with a 100 ms time constant instead of stepping; jumps if they are more than 120 ms apart |
| Finished | Stops |

So the clock is smooth frame to frame, never runs backwards visibly, and stays locked to the audio (the `--highway-log` flag shows them within about 10 ms headless). Frame time is clamped to 100 ms per step so a hitch can't fling it.

Two derived times use the player's calibration (`GameSettings`, set on the settings page):

- **Judge time** = clock − `AudioLatency`: the song position the player is hearing.
- **Visual time** = judge time + `VideoLatency`: what to draw, early by the display's delay.

The `TrackMover` (camera and strike bar) sits at `Z = visual time × NoteSpeed` every frame, with no smoothing: a note crosses the bar exactly when it should be hit.

### Input and judging

Each frame, `GatherHits` collects every hit as `(pad, song time)`:

- **Keyboard:** every pad whose key was pressed this frame, at the judge time.
- **MIDI:** every note-on queued since the last frame (`MidiDevice::PumpMessages`). Messages are stamped on RtMidi's thread when they arrive, so each is judged at judge time minus its age (capped at 250 ms). MIDI works on every platform.
- **Autoplay:** `--highway-autoplay [offset ms]` adds a hit for every note at its time plus the offset.

Each input is resolved to the pads and strokes it's bound to (`PadMappingStorage::Resolve`; `Docs/MIDI-and-Pads.md`) and becomes one hit per lane (`AddHits`). A hit knows its pad when the input means only one pad of the lane, and its stroke when the input says (MIDI does, a key doesn't).

Hits are judged in time order. `JudgeHit` takes the closest unjudged note in that pad's lane within the widest window; hits in different lanes never interfere, so chords (kick + cymbal) register in full. A hit with no note in reach scores nothing. Then the **technique** check: a known pad that differs (closed hi-hat for an open note) or a known stroke that differs (head for a rimshot) is a wrong technique, judged by **Technique** (`GameSettings::TechniqueStrictness`, on the settings page):

| Setting | Wrong technique |
|---------|-----------------|
| Off | A normal hit |
| Lenient (default) | One grade lower (Perfect → Great → Good), combo kept |
| Strict | A miss |

The HUD names the wanted technique ("OPEN HI-HAT!", "RIMSHOT!", "BELL!"), and the results count wrong techniques. Velocity (ghosts, accents) is drawn but not judged. `JudgeMisses` then walks each lane from its cursor and marks every note whose window has passed as missed. Both only look at notes near the cursor, so the per-frame cost no longer grows with the chart.

| Judgement | Window (either side) | Points |
|-----------|----------------------|--------|
| Perfect | 30 ms | 100 |
| Great | 60 ms | 75 |
| Good | 90 ms | 50 |
| Miss | note passed the Good window | 0, combo resets |

Points are multiplied by the combo multiplier: ×1, rising by one every 10 notes in a row to ×4. Accuracy weighs Perfect 1, Great 0.75, Good 0.5, Miss 0.

### Feedback

- **Drum stems:** a miss mutes the drum stems (`drums.ogg`, `drums_1..4.ogg`, via `AudioPack::SetDrumVolume`), and the next hit brings them back, so the player hears their part drop out. A song without separate drum stems can't do this.
- **Notes:** a hit note is scaled to zero the same frame (its entity is deleted the next); a note that goes past the Perfect window unhit dims to 40% of its colour (`DimLate`, from `JudgeMisses`) and can still be hit for Great or Good; a missed note turns grey and scrolls past, and is deleted once it is off the back of the highway.
- **HUD (`in_game` model):** score, multiplier (orange above ×1), combo from 5, accuracy; the judgement word with early/late and the offset in ms, fading after about half a second; title, artist and a countdown during the lead-in. The chart's lyrics, karaoke-style, top centre (`NoteHighwayCore::UpdateLyrics`, Settings > Lyrics; `Docs/Venue-and-Band.md` → Lyrics).
- **End:** once every note is judged and the audio has stopped, the results screen shows score, accuracy, each judgement's count, the average timing of the hits (`avg_timing`: so many ms early or late) and the best combo, with Retry (reloads the scene with the same track) and Continue (the library; after a practice lesson, Lessons). Escape on the results screen also returns there.
- **Countdown:** it counts in to the first note, or to the chart's start marker (`TrackData::m_startTime`, set in the Track Editor) when that comes first (`m_countInMs`).

### Pause

The pause menu fires `InGamePauseCurrentTrack` / `InGameResumeCurrentTrack`; the core stops its clock and pauses the stems. While paused (and when idle or finished) the MIDI queue is still drained, so nothing stale is judged on resume.

**Resume gives a run-up** (`NoteHighwayCore::ResumeWithRunUp`). The song is pulled back `kResumeRewindMs` (2 s) and the stems fade in over `kResumeFadeSeconds` (1.5 s; `AudioPack::Seek` takes the fade length). Notes judged before the pause stay judged: they come back as grey gems (`NoteState::Passed`, `GreyOut`) where the run-up passes them again, score nothing and can't be hit twice. Notes that hadn't been judged yet are live as usual. The drum stems are audible for the run-up even if a miss had muted them. During the lead-in (nothing has played) resume just carries on.

`InGameMenuController` also pauses the song when the MIDI device is unplugged mid-song (`MidiDevice::IsUnplugged`, `Docs/MIDI-and-Pads.md`); the pause menu says so, and says when it is back.

### Diagnostics

- `--play-track <index>`: start a track when `Example.lvl` is opened directly. The index is the library's scan order.
- `--practice <lesson index> [--practice-bpm <bpm>]`: start a practice lesson the same way (`Docs/Practice.md`).
- `--pause-at <seconds>`: pause there for a second and resume, to check the run-up without a hand on the keyboard.
- `--highway-log`: the lane layout, the track, a line a second comparing the clock with FMOD's position and the judged/missed counts, drum mute changes, and the final result.
- `--highway-autoplay [offset ms]`: hits every note at that offset, with its pad and stroke (the debug panel's Autoplay, started on PERFECT). Add `--highway-autoplay-sloppy` to start it on SLOPPY, and `--highway-autoplay-plain` to hit as a kit with plain strokes and one hi-hat note would (exercises technique judging). With `--frames N --screenshot` under `Engine/Tools/Headless.sh` this checks judging, the HUD and the results without a kit.

### Appendix: the vocals experiment

`VocalsTestCore` (+ `VocalsTestComponent`, `Assets/Vocals.lvl`) attaches an FMOD FFT DSP to a test vocal stem, finds the dominant frequency bin each update, converts it to a MIDI note number (`12 * log2(f/440) + 69`), and writes the result to the `vocals` view model, which `Assets/UI/Vocals.rml` shows as a meter. It is a spike, not a feature.

### Debug panel

**F8** during a song shows a panel over the bottom of the highway (`Assets/UI/InGameMenu.rml`, `#debug-panel`; `InGameMenuController` owns the `debug`, `debug_nofail`, `debug_autoplay` (+ `debug_autoplay_label`) and `debug_plain` model keys, `NoteHighwayCore` fills `song_progress` and `song_clock`):

- **Metronome.** With the Metronome setting on (or `--metronome`), a click stem written from the beat lines plays with the song (`UpdateMetronome`; `Docs/Audio.md` → Metronome).
- **Calibration.** `--calibrate` (or Settings > Sound & Timing) plays the delay calibration's chart: hits are measured against the beat instead of judged, with the latency settings left out (`CalibrationHits`; `Docs/Latency-and-Responsiveness.md` → Calibration).
- **No fail.** Misses still count in the results, but don't break the combo, mute the drum stems or deflate the crowd and lights (`ApplyJudgement`). There is no fail state yet; this is what a miss costs today. `--no-fail` starts it on.
- **Autoplay** (OFF / PERFECT / SLOPPY, `NoteHighwayCore::GatherHits`). PERFECT hits every note on time with its chart pad and stroke. SLOPPY plays like a person: each note early or late by up to 75 ms (a triangle around on time: about 64% perfect, 32% great, 4% good) and about one note in twenty-five never hit. The jitter comes from a hash of the note's time and lane, so a run, a retry or a seek plays the same way. Hits go through the normal judging, so scoring, combo, drum muting, the crowd and the lights all react. The HUD shows `AUTOPLAY <mode>` and the results say *Autoplayed*, so a demo score isn't mistaken for a real one.
- **Strokes** (CHART / PLAIN). With autoplay on, PLAIN hits as a kit that only sends plain strokes and one hi-hat note would: open hi-hats come in closed, rims and flams as plain hits. That exercises technique judging (`TechniqueStrictness`).
- **Scrubber.** Dragging it fires `InGameSeekTrack`; `NoteHighwayCore::SeekTo` seeks every stem (`AudioPack::Seek`), resets the song clock, clears the notes already past the judge without counting them, and re-arms every note still ahead; the window then spawns the ones in view (each `NoteState` keeps a copy of its chart note in `Source`). During the lead-in it starts the song first. `--seek <seconds>` does the same once the song starts; `--debug-panel` opens the panel at load.
- **Editor preview.** `BeginPreview( TrackData& )` puts the core in `SongState::Preview` for the Track Editor (`Docs/Songs-and-DLC.md`, Authoring): it builds the notes, highway, beat lines and venue from a chart the editor owns, and from then on shows whatever time `SetPreviewTime` gives, with no `AudioPack`, lead-in, latency offsets, judging or MIDI pumping. `UpdatePreview` hides notes behind that time (lighting their pads when the time is playing forward, walking only the notes that crossed since last frame); a scrub or a rebuild re-arms every note from the playhead (flags only), and the window spawns what is in view. `RefreshPreview( PreviewNotes | PreviewBeats | PreviewVenue )` rebuilds parts after an edit, and `EndPreview` shuts the track down. `SetupTrack` and the preview share `BuildNotes`, `BuildVenue`, `ClearNotes` and `ClearBeatLines`.

The song clock holds while the stems seek, and every stem restarts on the same DSP tick once all have got there (`AudioPack::Seek` / `Update`, `Docs/Audio.md`).

## Caveats & Fragility

- **Keyboard hits are frame-quantized.** Only MIDI carries an arrival time; a key press is judged at the frame that saw it.
- **The windows are fixed.** `NoteSpeed` changes scroll speed only. Every converted chart has `NoteSpeed` 10.
- **Drum muting needs drum stems.** Songs with only a full mix keep playing the drums through misses.
- **No hit sounds.** The drum stem is the audio feedback; a player on a silent kit or keyboard hears nothing extra on a hit (`Drumset` is still dormant, `Docs/Audio.md`).
- **Pause/resume can drift the stems** (`AudioPack` only DSP-schedules the first start, `Docs/Audio.md`). The clock follows stem 0.
- **Results need the audio to end.** A chart that stops long before its song waits for the song.
- **Lane entities are found by name** in `OnStart` (`open_hh`, `closed_hh`, `Snare1`, `Crash1`, `crash2`, `Bass1`, `ride1`, `tom1`-`tom3`, `TrackMover`). A missing one is logged and its notes stay unparented at the origin.
- **Mesh sizes are constants** in `NoteHighwayCore.cpp` (`kBarMeshWidth` for the strike bar, `kGemTop` and its neighbours for the note models); changing the note or bar meshes means updating them.
- **Beat lines need `notes.mid`.** A converted song whose `notes.mid` was deleted, and every native chart, has no beat lines. Storing the tempo map in `NoteData.txt` at conversion would fix both.
- **The camera is tuned for an 8-unit highway.** It's set in `Example.lvl`, not computed from the lane count.
- **Highway pieces are separate entities**, instanced by colour. Gems and beat lines exist only while in view (`UpdateWindow`); the surface, dividers and pads are a handful for the whole song. Spawning one costs a few microseconds (a whole dense chart took about 25 ms at load), so they are created and deleted rather than pooled.
- **No scores are saved.** The track stats page has nothing to show yet.

## Related Docs

- `Docs/Latency-and-Responsiveness.md`: the timing chain through this code
- `Docs/MIDI-and-Pads.md`: bindings and the MIDI queue
- `Docs/Audio.md`: `AudioPack` loading, stems and scheduling
- `Docs/UI-and-Menus.md`: the pause menu and HUD document
- `Engine/Docs/ECS.md`: cores, filters, `World::Simulate` deletion timing
