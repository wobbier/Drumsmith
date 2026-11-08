# MIDI and Pads

> Verified against game commit 1714270, 2026-07-10. Engine submodule at 047f57b8.

How drum hits get from hardware into the game: the `MidiDevice` RtMidi wrapper, the `PadId`/`PadMappingStorage` binding layer, and where each is consumed.

## Overview

Drumsmith reads MIDI input through an **RtMidi callback**: RtMidi's thread stamps each message with its arrival time (`steady_clock`) and pushes it onto a locked queue in `MidiDevice`; `MidiDevice::PumpMessages()` hands the main thread everything that arrived in the last second. A hit becomes gameplay input via two mappings: the MIDI note number → `PadId` binding in `PadMappingStorage`, and the `PadId` → lane-name mapping in `PadUtils` that ties into note data and scene lane entities. Keyboard input is a parallel path through the engine's `Input` (see `Engine/Docs/Platform-Window-Input-Config.md`), bound per pad alongside the MIDI note.

## Key Files

| Path | Role |
|------|------|
| `Game/Source/Midi/MidiDevice.h` | RtMidi singleton wrapper: enumerate/open/close/pump |
| `Game/Source/Editor/PadBindings.h` | `PadId` enum, `PadUtils` mappings, `PadDefinition`, `PadMappingStorage` — **runtime code despite living under `Editor/`** |
| `Game/Source/Editor/PadBindings.cpp` | `PadBindingWidget` (editor rebinding UI) + `PadMappingStorage` load |
| `Assets/Config/PadMappings.json` | Persisted bindings (`PadMap` array of `{ID, NAME, KB, MIDI}`) |
| `ThirdParty/rtmidi/` | RtMidi library (ALSA/CoreMIDI/WinMM backends) |

## How It Works

### MidiDevice

The constructor creates an `RtMidiIn`, calls `RefreshDevices()` (port enumeration), sets `ignoreTypes(true, true, true)` (sysex, timing clock and active sensing are dropped) and registers the callback. `OpenMidiDevice(index)` closes any open port and opens the requested one; `OpenMidiDevice(name)` searches `m_devices` by exact name and falls back to the first device. Both return false when there is nothing to open, and every entry point tolerates a missing `RtMidiIn`.

The callback (`MidiDevice::OnMessage`) keeps 3-byte messages as `MidiMessageNew{ m_status, m_data1, m_data2, m_arrival }` (the queue is capped at 4096). `PumpMessages()` swaps the queue out under the lock and drops anything older than a second, so a reader that stopped pumping (an unfocused editor window) never gets a burst of old hits. `IsOnType()` excludes velocity-0 note-ons, which are note-offs by convention.

`MidiMessageNew::IsOnType()` tests the status nibble for note-on (0x9); `m_data1` is the note number, `m_data2` the velocity (currently unused by all consumers).

### Pad bindings

`PadId` is the ten-lane drum enum: `Bass, Snare, OpenHiHat, ClosedHiHat, Crash1, HighTom, MidTom, FloorTom, Ride, Crash2`. `PadUtils` maintains **two distinct string mappings**:

- `GetPadName(PadId)` — display names (`"Bass"`, `"Snare"`, `"Crash"` for Crash1…), used in UI and `NoteTrigger::EditorLaneName`.
- `GetPadId(PadId)` ↔ `GetNewPadId(string)` — lane names (`"bass1"`, `"snare1"`, `"tom1"`, `"open_hh"`, `"crash1"`…), used in `NoteData::m_noteName`, scene lane entity lookup, and `NoteData.txt`. `GetNewPadId` asserts on unknown names and returns `PadId::COUNT`.

`GetNoteColorABGR` supplies note mesh colors; `Ride` and `Crash2` have no case and fall through to white.

`PadMappingStorage` (singleton) holds `mappedPads` — one `PadDefinition{ padId, padName, keyboardBinding, midiBinding }` per `PadId` — loaded from `Assets/Config/PadMappings.json` at first use. Unbound pads read binding 0.

### Rebinding (editor only)

`PadBindingWidget` (Havana widget, `ME_EDITOR` builds) lists all pads with a keyboard-capture button (binds `Input::GetLastKeyPressed` from the editor input context) and a MIDI-capture button (pumps messages while focused and binds the first note-on's note number; it pre-pumps once when capture starts to discard stale queued hits). "Save Pad Mappings" serializes to `Assets/Config/PadMappings.json`. **There is no in-game rebinding UI** — game builds can only consume a shipped/previously saved mapping file.

### Consumption points

| Consumer | When it pumps | Platform gate |
|----------|---------------|---------------|
| `NoteHighwayCore::Update` (gameplay) | Every frame, before judging; while paused or idle too, to discard | none: every platform |
| `TrackEditor::Render` (charting/audition) | Once per UI frame, only while the editor window is focused | editor builds |
| `PadBindingWidget::Render` (capture) | While the capture button is armed | editor builds |
| `MainMenuController::GetMIDIDevices_Internal` | Never pumps — enumerates devices for the settings UI | — |

The device is opened for gameplay in `NoteHighwayCore::OnAddedToWorld` using `GameSettings::PreferredMidiDevice`. `rtmidi` links on **all** platforms (`Game.sharpmake.cs` adds it for Win64, UWP, macOS, and Linux, with ALSA via `libasound.so` on Linux). Gameplay judges each note-on at its arrival time (`Docs/Gameplay-Note-Highway.md`).

## How to Extend

**Add a pad**: extend `PadId` (before `COUNT`), add cases to `PadUtils::GetPadName`, `GetPadId`, `GetNewPadId`, and `GetNoteColorABGR`, add a lane entity with the matching lane name to the gameplay scene (`NoteHighwayCore::OnStart` hardcodes the lookup list — update it), and rebind/save mappings. Note lane names are the serialization schema for `NoteData.txt` — renaming one breaks existing charts.

**Bind by note number without the widget**: edit `Assets/Config/PadMappings.json` directly (`"MIDI"` is the raw note number, `"KB"` the SDL scancode-based `KeyCode`).

## Caveats & Fragility

- **One queue, several readers.** Gameplay, `TrackEditor` and `PadBindingWidget` all pump the same queue; whoever pumps first gets the messages. In the editor, a focused Track Editor and a playing game would split the hits.
- **`OpenMidiDevice(name)` falls back to device 0 through a failed assert.** An unknown/empty preferred-device name (the default `GameSettings::PreferredMidiDevice` is `""`) trips `ME_ASSERT_MSG(false, ...)` and then opens port 0 — in asserts-off builds this is a silent wrong-device open, and with **zero** devices attached, `OpenMidiDevice(0)` indexes an empty vector.
- **`RefreshDevices` still dereferences `m_midiIn` unconditionally**; the open/close/pump paths check it.
- **The device is never closed on scene exit.** `NoteHighwayCore::OnAddedToWorld` opens it; `OnRemovedFromWorld` only deregisters events. `MidiDeviceInfo::IsOpen` is set but never cleared, so reopen logic can skip a real reopen.
- **Device hot-plug is unsupported**: `RefreshDevices` runs once in the constructor; devices attached later don't appear until restart (the settings UI enumerates the cached list).
- **`PadBindings.h` lives under `Editor/` but is required at runtime** by `NoteHighwayCore`, `TrackList`, and `Drumset` — only the `PadBindingWidget` half is actually editor-only.
- **`MidiDevice::IsPaused` is dead state** (all uses commented out).

## Related Docs

- `Docs/Gameplay-Note-Highway.md` — the gameplay consumer and its hit-window pump pattern
- `Docs/Latency-and-Responsiveness.md` — what polling + timestamp loss cost end to end
- `Docs/Game-Architecture.md` — build wiring (rtmidi on all platforms)
- `Engine/Docs/Platform-Window-Input-Config.md` — the keyboard input path
