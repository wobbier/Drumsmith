# Latency and Responsiveness

> Verified against game commit 1714270, 2026-07-10. Engine submodule at 047f57b8.

The end-to-end timing story: every stage between a stick hitting a pad and the game responding, which clock each stage runs on, what compensation exists today, and the engine constraints that bound any fix. Facts only — the ranked improvement plan lives in `Docs/State-of-the-Game.md`.

## Overview

Drumsmith judges hits once per rendered frame in `NoteHighwayCore::Update`, against its own song clock: frame time steered toward FMOD's stream position. MIDI hits carry their arrival time (stamped on RtMidi's thread), so they are judged at the moment they arrived; keyboard hits are judged at the frame that saw them. `AudioLatency` and `VideoLatency` from the settings shift the judge and the highway. A hit note disappears the frame it is judged; a miss mutes the drum stems. There is still no hit sound. The engine loop is variable-timestep with vsync permanently on.

## Key Files

| Path | Role |
|------|------|
| `Game/Source/Cores/NoteHighwayCore.cpp` | Song clock, latency offsets, judging, feedback |
| `Game/Source/Midi/MidiDevice.cpp` | The RtMidi callback that stamps arrival times |
| `Game/Source/CoreGame/AudioPack.cpp` | `GetPositionMs` (what the clock steers toward), DSP-clock start scheduling |
| `Engine/Source/Engine/Engine.cpp` | `Engine::Run` — the frame phase order below |
| `Engine/Modules/Moonlight/Source/Renderer.cpp` | `BGFX_RESET_VSYNC` (unconditional) |
| `Engine/Source/Cores/AudioCore.cpp` | FMOD init (default mixer settings) + per-frame `System::update` |

## How It Works

### Frame phase order (engine loop, `Engine::Run`)

Per frame, in order: `ParseMessageQueue` (SDL pump → key events) → `FirePendingEvents` (queued events, e.g. `LoadSceneEvent`) → `GameClock.Update` → `Input::Update` (keyboard/mouse state) → `World::Simulate` (entity/core reconciliation **and destruction of entities marked last frame**) → `UpdateLoadedCores` (**`NoteHighwayCore::Update` runs here**) → `Game::OnUpdate` → `AudioThread->Update` (FMOD `System::update`) → LateUpdate block (cameras, UI) → `UI::Render` + `BGFXRenderer::Render` → input `PostUpdate`. Variable timestep; the fixed-step remnants are disabled (`Engine/Docs/Architecture.md`). Vsync is always on — frame duration is a display-refresh multiple (16.7 ms at 60 Hz, 6.9 ms at 144 Hz).

### The chain, stage by stage

```mermaid
sequenceDiagram
    participant P as Pad and MIDI driver
    participant Q as RtMidi queue
    participant U as NoteHighwayCore Update
    participant F as FMOD mixer
    participant D as Display
    P->>Q: callback stamps arrival time and queues the note-on
    U->>F: GetPositionMs steers the song clock
    U->>Q: PumpMessages every frame
    U->>U: judge at arrival time minus AudioLatency
    U->>U: hit note scaled to zero this frame
    D->>D: note visibly disappears next present plus scanout
    Note over F: a miss mutes the drum stems; no hit sound
```

| Stage | Added latency | Notes |
|-------|---------------|-------|
| Pad sensor → USB → OS MIDI driver | ~1–5 ms (typical, external) | Module-dependent; e-drum modules add their own scan time |
| Driver → `MidiDevice` queue | <1 ms | The callback stamps arrival with `steady_clock` |
| Queue → judge | 0–1 frame to read, **0 ms of judging error** | The hit is judged at its arrival time; the frame only delays the response |
| Keyboard | 0–1 frame of judging error | SDL key state, no timestamp |
| Song clock | about 10 ms of FMOD tracking error (headless measurement) | Frame-time clock steered toward FMOD's position at each mixer update |
| Visual feedback | 1 frame + display | Hit note scaled to zero in the judging frame → present (vsync) → scanout |
| Audio feedback | On a miss only | The drum stems mute on a miss and return on the next hit; there is no hit sound (`Docs/Audio.md`) |

These are derivations from the mechanics above, not measurements — see "How to measure".

### Clock inventory

| Clock | Where | Used for | Character |
|-------|-------|----------|-----------|
| FMOD channel position (`GetPositionMs`, stem 0) | `AudioPack::GetPositionMs` | **The judge clock** and highway scroll target | Millisecond units; granularity tied to FMOD internals; returns 0 on channel error; moves relative to other stems after pause/seek (`Docs/Audio.md`) |
| FMOD DSP clock (`getDSPClock`) | `AudioPack::Play` only | Sample-accurate synchronized *start* (+2048 samples) | Sample-accurate; not consulted after start |
| Engine `GameClock` (`std::chrono::high_resolution_clock`) | `UpdateContext::GetDeltaTime` | Camera smoothing, radio state machine | Variable per-frame delta; never correlated with the audio clock |
| RtMidi per-message delta time | `RtMidiIn::getMessage` return | **Discarded** in `MidiDevice::PumpMessages` | The only record of input arrival time; `MidiMessageNew` has no field for it |
| OS monotonic time | — | Unused by game code | Would be needed to correlate input stamps with audio position |

### Compensation state today

- Judge time = song clock − `AudioLatency`; the highway is drawn at judge time + `VideoLatency` (`NoteHighwayCore::JudgeTimeMs` / `VisualTimeMs`). Both settings are 0-250 ms (`GameSettings::kMaxLatencyMs`). The old hardcoded −30 ms offset is gone.
- `GameSettings::AudioLatency` / `VideoLatency`: set from the settings page and the pause options, persisted in `Settings.json`, read by `NoteHighwayCore` every frame.
- The **calibration** (below) measures both settings and writes them.
- Hit windows: Perfect ±30, Great ±60, Good ±90 ms, the same for every chart (`Docs/Gameplay-Note-Highway.md`).
- Chart-side: notes recorded in the `TrackEditor` inherit the full input→UI-frame latency at authoring time, silently baking the charter's setup latency into `NoteData.txt` (`Docs/Songs-and-DLC.md`).

### Engine constraints on any fix

Each constraint links the doc that states it:

- **Main-thread-only**: `EventManager`, `World` (entity create/destroy), `ResourceCache`, and bgfx submission must stay on the main thread (`Engine/CLAUDE.md` hard rules; `Engine/Docs/Jobs-and-Events.md`). A MIDI callback thread therefore may **not** touch note entities, fire events, or load resources — it can only enqueue into a queue the main thread drains.
- **Events are synchronous and not thread-safe** (`Engine/Docs/Jobs-and-Events.md`) — no cross-thread event delivery exists.
- **FMOD Core API is thread-safe** as initialized (`FMOD_INIT_NORMAL`, no `FMOD_INIT_THREAD_UNSAFE` — `Engine/Source/Cores/AudioCore.cpp`), so `System::playSound` on preloaded `FMOD_CREATESAMPLE` sounds is legal from a non-main thread. Preloading itself must happen on the main thread if it goes through `ResourceCache`; `Drumset::loadSound` uses raw FMOD and carries no such restriction, but is main-thread today.
- **Vsync is not optional**: `BGFX_RESET_VSYNC` is set unconditionally in `Renderer.cpp` — the poll cadence floor is the display refresh, and there is no frame-rate cap logic beyond it (the `FPS = 144` constant in `Engine/Source/Engine/Engine.h` is unused).
- **Variable timestep**: no fixed-tick simulation exists to decouple judgment cadence from render cadence (`Engine/Docs/Architecture.md`; fixed timestep is a stated engine priority motivated by this game).
- **Menus are RmlUi documents composited every frame** (`Engine/Docs/UI-RmlUi-and-ImGui.md`) — UI-side feedback (combo counters etc.) no longer has a 60 fps cap, but model values reach the screen on the frame after they are set.
- **`CameraCore` updates in LateUpdate** (`Engine/Docs/Architecture.md`) — camera-dependent visuals computed in `Update` see last frame's camera.

### Calibration

Settings > Sound & Timing > *Calibrate audio and video* (`--calibrate` from the command line) plays a 30-second session on the note highway and sets both delays from it. `CoreGame/Calibration.h/.cpp` holds the session; `NoteHighwayCore` plays its chart (`TrackData::m_calibration`) the way it plays a practice lesson's, with three differences: the two latency settings are left out of `JudgeTimeMs` / `VisualTimeMs` (they are what is being measured), hits go to `CalibrationHits` instead of the judge, and there are no beat lines.

| Part | What the player gets | What is measured |
|------|----------------------|------------------|
| **Watch** (beats 4-23) | 20 snare notes crossing the bar, in silence | hit time − note time = display delay + input delay → `VideoLatency` |
| **Listen** (beats 28-47) | 20 clicks (a WAV that is silent until then), nothing on the highway | hit time − click time = audio output delay + input delay → `AudioLatency` |

Both are at 100 BPM. Any pad, or any key bound to one, counts (hits within 80 ms of each other are one strike). A hit belongs to the nearest beat within 45% of a beat (270 ms); the first four beats of each part are warm-up and aren't measured; a beat hit twice keeps the later hit. Each part's result is the **median** of its hits (`Calibration::Summarise`), with their mean distance from it as the spread: fewer than 8 hits is no result, more than 35 ms of spread is flagged as uneven. The results screen shows both; *Use these* writes the valid ones into the settings (clamped to 0-250) and saves.

The input delay is in both numbers, which is what makes them right together: the highway is drawn at clock − `AudioLatency` + `VideoLatency`, where it cancels, and a hit is judged at its arrival − `AudioLatency`, which takes out the output delay and the input delay both. So calibrate with the input you play with: a keyboard's frame of input delay is not a MIDI kit's.

`--calibrate --highway-autoplay <ms>` hits every beat of both parts that late; the results should read that number (the headless check).

### How to measure (re-stamp numbers before relying on them)

- `System::getDSPBufferSize` / `getSoftwareFormat` at runtime for the actual mixer block/count and sample rate.
- `--highway-log` prints the song clock against FMOD's position once a second; the HUD shows each hit's offset in ms.
- Optick captures (F9; parsing recipe in `CLAUDE.md`) for frame-time distribution and update-phase costs.
- Ground truth requires a physical loopback: record pad strike audio and game audio output on one device and measure the gap (the standard rhythm-game calibration method).

## Caveats & Fragility

- Every number in the budget table above is a *derivation* from code structure, except the mechanics themselves; hardware terms are typical figures. Do not quote totals as measurements.
- The ~10 ms clock tracking figure is from headless runs on FMOD's silent output; real devices have larger mixer blocks, which the clock smooths over but which add output latency only `AudioLatency` can account for.
- The settings only allow positive offsets (0-250 ms); a setup that needs the highway drawn *later* than the audio can't be calibrated.
- **The calibration measures the player as well as the hardware.** People tapping to a click tend to land a little ahead of it, so a result can come out lower than the true delay, or negative (shown as 0 with a remark). It has only been run headless with autoplay, never by a person on real audio and display hardware.
- **A delay beyond 270 ms wraps:** the hits read as early hits on the next beat.

## Related Docs

- `Docs/State-of-the-Game.md` — the ranked plan to fix all of this
- `Docs/Gameplay-Note-Highway.md` — the judgment code in detail
- `Docs/MIDI-and-Pads.md` — the input boundary
- `Docs/Audio.md` — FMOD facts, the dormant hit-sound path
- `Engine/Docs/Jobs-and-Events.md`, `Engine/Docs/Architecture.md` — the threading and frame-loop rulebooks
