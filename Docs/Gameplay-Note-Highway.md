# Gameplay: The Note Highway

> Verified against the working tree on 2026-11-08 (the gameplay rewrite, not yet committed). Engine submodule at 8cee2340.

`NoteHighwayCore` end to end: how a selected track becomes notes on the highway, the song clock, how hits are judged and scored, what the player sees and hears, and the end of a song. Appendix: the experimental vocals mode.

## Overview

`NoteHighwayCore` is a scene-loaded core (declared in `Assets/Example.lvl`) filtering on `Transform + NoteTrigger`. It receives `LaunchPlayTrackEvent`, spawns one entity per chart note, lays the lanes out for that chart, starts the stems after a lead-in, and every frame advances its own song clock, judges keyboard and MIDI hits per lane, marks passed notes as misses, moves the highway, and fills the `in_game` view model the HUD in `Assets/UI/InGameMenu.rml` shows.

## Key Files

| Path | Role |
|------|------|
| `Game/Source/Cores/NoteHighwayCore.h` / `.cpp` | The core: clock, lanes, judging, score, HUD values |
| `Game/Source/Components/NoteTrigger.h` | Per-note data on each note entity |
| `Game/Source/Midi/MidiDevice.h` / `.cpp` | Timestamped MIDI queue (RtMidi callback) |
| `Assets/Prefabs/Notes/NewBaseNote.prefab` | Note gem (Transform + textured Mesh, `NewNote.obj`, 2 units wide) |
| `Assets/Prefabs/Notes/BassNotePrefab.prefab` | Kick note: an orange bar (`Engine/Assets/cube.obj`, 1 unit wide) |
| `Assets/Example.lvl` | Gameplay scene: lane entities, `TrackMover` (camera, its fog, the strike `Bar`), the cores |
| `Assets/Prefabs/Highway/HighwayBox.prefab` | The unit cube every highway piece is spawned from |
| `Assets/UI/InGameMenu.rml` / `.rcss` | HUD, countdown, results, pause menu |

## How It Works

### Track setup

`SetupTrack( track, index )` (from `LaunchPlayTrackEvent`, or `--play-track <index>` on the command line):

1. `ShutdownTrack()` deletes the previous notes and stops audio.
2. `TrackData::LoadNoteData()` reads `NoteData.txt`; notes are sorted into one time-ordered list per lane (`m_laneNotes`). Open and closed hi-hat share a list, so either pad hits either.
3. `LayoutLanes()` places only the columns this chart uses, left to right as a kit sits: crash, hi-hat, snare, high/mid/floor tom, ride, second crash. Spacing is up to 1.8 units, shrunk so the highway is at most 8 units wide; the kick stays at the centre as a bar across all columns, and the strike `Bar` is scaled to the same width.
4. Each note is spawned from its prefab, scaled to 90% of the lane spacing, taller and deeper than the prefab (`kGemHeight`, `kGemDepth`), parented to its lane entity and placed at `Z = time × speed`. The kick is a bar the highway's width.
5. `BuildHighway` and `BuildBeatLines` add the highway pieces (below).
6. The `AudioPack` starts loading the stems; the clock is set to `-kLeadInMs` (2 s).

Speed is the chart's `NoteSpeed` times the player's **Highway Speed** (`GameSettings::HighwaySpeed`, 50-200%, on the settings page and in the pause options). Changing it mid-song moves every note and beat line to its new place (`ApplySpeed`).

Colours come from `PadUtils::GetNoteColor`; gems also glow in their colour (`EmissiveColor`), since the scene has no lights. Every colour goes through `Tint`, which applies it once the mesh's model has bound: binding (`Mesh::BindModelMesh`) rebuilds the material from the prefab's saved one, which would undo an earlier colour.

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
| Playing | Advances by frame time; whenever FMOD's position moves (once per mixer block), the clock closes 20% of the gap to it, or jumps if they are more than 120 ms apart |
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

Hits are judged in time order. `JudgeHit` takes the closest unjudged note in that pad's lane within the widest window; hits in different lanes never interfere, so chords (kick + cymbal) register in full. A hit with no note in reach scores nothing. `JudgeMisses` then walks each lane from its cursor and marks every note whose window has passed as missed. Both only look at notes near the cursor, so the per-frame cost no longer grows with the chart.

| Judgement | Window (either side) | Points |
|-----------|----------------------|--------|
| Perfect | 30 ms | 100 |
| Great | 60 ms | 75 |
| Good | 90 ms | 50 |
| Miss | note passed the Good window | 0, combo resets |

Points are multiplied by the combo multiplier: ×1, rising by one every 10 notes in a row to ×4. Accuracy weighs Perfect 1, Great 0.75, Good 0.5, Miss 0.

### Feedback

- **Drum stems:** a miss mutes the drum stems (`drums.ogg`, `drums_1..4.ogg`, via `AudioPack::SetDrumVolume`), and the next hit brings them back, so the player hears their part drop out. A song without separate drum stems can't do this.
- **Notes:** a hit note is scaled to zero the same frame (its entity is deleted the next); a missed note turns grey and scrolls past.
- **HUD (`in_game` model):** score, multiplier (orange above ×1), combo from 5, accuracy; the judgement word with early/late and the offset in ms, fading after about half a second; title, artist and a countdown during the lead-in.
- **End:** once every note is judged and the audio has stopped, the results screen shows score, accuracy, each judgement's count and the best combo, with Retry (reloads the scene with the same track) and Continue (the library). Escape on the results screen also returns to the library.

### Pause

The pause menu fires `InGamePauseCurrentTrack` / `InGameResumeCurrentTrack`; the core stops its clock and pauses the stems. While paused (and when idle or finished) the MIDI queue is still drained, so nothing stale is judged on resume.

### Diagnostics

- `--play-track <index>`: start a track when `Example.lvl` is opened directly. The index is the library's scan order.
- `--highway-log`: the lane layout, the track, a line a second comparing the clock with FMOD's position and the judged/missed counts, drum mute changes, and the final result.
- `--highway-autoplay [offset ms]`: hits every note at that offset. With `--frames N --screenshot` under `Engine/Tools/Headless.sh` this checks judging, the HUD and the results without a kit.

### Appendix: the vocals experiment

`VocalsTestCore` (+ `VocalsTestComponent`, `Assets/Vocals.lvl`) attaches an FMOD FFT DSP to a test vocal stem, finds the dominant frequency bin each update, converts it to a MIDI note number (`12 * log2(f/440) + 69`), and writes the result to the `vocals` view model, which `Assets/UI/Vocals.rml` shows as a meter. It is a spike, not a feature.

## Caveats & Fragility

- **Keyboard hits are frame-quantized.** Only MIDI carries an arrival time; a key press is judged at the frame that saw it.
- **The windows are fixed.** `NoteSpeed` changes scroll speed only. Every converted chart has `NoteSpeed` 10.
- **Drum muting needs drum stems.** Songs with only a full mix keep playing the drums through misses.
- **No hit sounds.** The drum stem is the audio feedback; a player on a silent kit or keyboard hears nothing extra on a hit (`Drumset` is still dormant, `Docs/Audio.md`).
- **Pause/resume can drift the stems** (`AudioPack` only DSP-schedules the first start, `Docs/Audio.md`). The clock follows stem 0.
- **Results need the audio to end.** A chart that stops long before its song waits for the song.
- **Lane entities are found by name** in `OnStart` (`open_hh`, `closed_hh`, `Snare1`, `Crash1`, `crash2`, `Bass1`, `ride1`, `tom1`-`tom3`, `TrackMover`). A missing one is logged and its notes stay unparented at the origin.
- **Mesh widths are constants** in `NoteHighwayCore.cpp` (`kNoteMeshWidth`, `kKickMeshWidth`, `kBarMeshWidth`); changing the note or bar meshes means updating them.
- **Beat lines need `notes.mid`.** A converted song whose `notes.mid` was deleted, and every native chart, has no beat lines. Storing the tempo map in `NoteData.txt` at conversion would fix both.
- **The camera is tuned for an 8-unit highway.** It's set in `Example.lvl`, not computed from the lane count.
- **Highway pieces are separate entities**: a song with many beats adds several hundred meshes; they're instanced by colour.
- **No scores are saved.** The track stats page has nothing to show yet.

## Related Docs

- `Docs/Latency-and-Responsiveness.md`: the timing chain through this code
- `Docs/MIDI-and-Pads.md`: bindings and the MIDI queue
- `Docs/Audio.md`: `AudioPack` loading, stems and scheduling
- `Docs/UI-and-Menus.md`: the pause menu and HUD document
- `Engine/Docs/ECS.md`: cores, filters, `World::Simulate` deletion timing
