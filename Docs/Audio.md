# Audio

> Verified against game commit 1714270, 2026-07-10. Engine submodule at 047f57b8.

The game's three audio systems — `AudioPack` (synchronized stem playback for gameplay and radio), `TrackRadio` (menu background music), and `Drumset` (pad hit sounds, currently dormant) — and the FMOD facts underneath them.

## Overview

All game audio goes through FMOD Core via the engine's `AudioCore` (`Engine/Source/Cores/AudioCore.cpp`), reached as `GetEngine().AudioThread` — a misleading name: it is a regular core whose `Update` runs on the **main thread** each frame and pumps `FMOD::System::update()`. FMOD's actual mixer runs on FMOD-internal threads. The engine initializes FMOD with `FMOD_INIT_NORMAL`, 512 channels, a 64 KB stream buffer, and **default DSP buffer settings** (no `setDSPBufferSize` call), logging to `fmod_log.txt`.

`AudioPack::GetPositionMs` is *the* gameplay clock — `NoteHighwayCore` judges every hit against it — so this doc is a prerequisite for `Docs/Latency-and-Responsiveness.md`.

## Key Files

| Path | Role |
|------|------|
| `Game/Source/CoreGame/AudioPack.h` | Multi-stem playback wrapper (gameplay + radio) |
| `Game/Source/Global/TrackRadio.h` | Menu music singleton state machine |
| `Game/Source/UI/TrackRadioUtils.cpp` | Drives `TrackRadio::Update` and the radio widget's view-model values |
| `Game/Source/CoreGame/Drumset.h` | Pad→sample hit-sound player (unused at runtime) |
| `Engine/Source/Cores/AudioCore.cpp` | FMOD system init/update (engine) |
| `Engine/Source/Components/Audio/AudioSource.cpp` | Per-sound channel wrapper: play/pause/seek/position (engine) |

## How It Works

### AudioPack — synchronized stems

Constructed from a `TrackData`, an `AudioPack`:

1. Creates an `FMOD::ChannelGroup` named after the track and parents it to the master group.
2. Calls `LoadStem` for the main track file plus a **hardcoded stem list**: `crowd.ogg`, `drums.ogg`, `drums_1.ogg`–`drums_4.ogg`, `guitar.ogg`, `vocals.ogg`, `rhythm.ogg`, `keys.ogg`. Missing files are skipped silently (`Path::Exists` check); drum stems are remembered by index in `m_drumTracks`.
3. Each stem loads through `ResourceCache::Get<Sound>` with `SoundFlags::NonBlocking | SoundFlags::CreateStream` — loading is asynchronous, and `IsReady()` polls until every `AudioSource::IsLoaded()` is true.

**Playback start is sample-accurate**: `AudioPack::Play` reads the group's DSP clock (`getDSPClock`), starts every stem paused, assigns it to the group, schedules `setDelay(parentClock + 2048, 0)` on each channel, then unpauses — all stems begin together 2048 samples (~43 ms at 48 kHz) in the future.

**Nothing after start is re-synchronized**:

- `Pause`/`Resume` loop over stems calling `Channel::setPaused` individually (the commented-out `syncGroup->setPaused` would have been atomic).
- `Seek` pauses, then calls `AudioSource::SetPositionMs` per stem — the DSP-clock re-sync block below it is commented out, and playback resumes wherever each stream lands.

`GetPositionMs`/`GetLength`/`GetVolume` delegate to `m_sounds[0]` — the main track stem — via `AudioSource::GetPositionMs`, which is `FMOD::Channel::getPosition(FMOD_TIMEUNIT_MS)` and returns 0 on error or missing channel.

`LoadURL` (streaming a remote file) exists but is only lightly used; it calls `Play()` immediately per stem added.

### TrackRadio — menu music

A singleton state machine (`None → Loading → Seeking → Playing`) that owns its own `AudioPack`. `Play(RadioArgs)` selects a track (ignoring requests for the already-playing index), and `Update` — called **not by the engine loop but by `TrackRadioUtils::OnUpdate`, i.e. only while a menu controller with a radio widget is alive** — walks the states:

- `Loading`: while `!IsReady()` it calls `Play()` every frame ("this feels weird, but okay??" — see Caveats); once ready, plays, applies `GameSettings::RadioVolume`, and either starts playing or seeks to the track's `PreviewPercent` marker first.
- `Seeking`: waits for readiness, then `Resume()`.
- `Playing`: when playback ends, returns to `None`, which lets `TrackRadioUtils` auto-play the next random track.

`TrackRadioUtils` also fills the radio widget's model values (title, art, position/duration, visibility) and handles its `skip`/`seek` events — see `Docs/UI-and-Menus.md`.

### Drumset — hit sounds (dormant)

`Drumset` maps `PadId → FMOD::Sound*` loaded with `FMOD_CREATESAMPLE` (fully decoded into memory — the right choice for low-latency one-shots). `hitPad(pad, velocity)` plays the sample immediately via `System::playSound` and scales volume by clamped velocity. `loadFromJson` can populate a kit from a `{"kits": {"default": {padName: filePath}}}` JSON.

**Current reality:** the only instantiation is in `TrackEditor::Init` (`ME_EDITOR` builds), and its `loadSound` calls are commented out — `loadFromJson` has no callers. The sound map is always empty, so every `hitPad` call early-returns. **No hit sound plays anywhere in the game or editor today.** The sample assets exist (`Assets/Drums/Basic/Bass.wav`, `Assets/Drums/Basic/Snare.wav`). Gameplay (`NoteHighwayCore`) has no `Drumset` at all — the only audible feedback during play is the pre-mixed song itself.

### FMOD threading facts

- `FMOD::System::update()` is pumped once per frame from `AudioCore::Update` on the main thread; mixing/streaming happen on FMOD's own threads regardless.
- FMOD Core is initialized without `FMOD_INIT_THREAD_UNSAFE`, so its API is **thread-safe by default** — `playSound` may legally be called from any thread (relevant to latency work; see `Docs/Latency-and-Responsiveness.md`). Engine-side objects (`ResourceCache`, entities, events) remain main-thread-only per `Engine/Docs/Jobs-and-Events.md`.
- No `setDSPBufferSize`/`setSoftwareFormat` calls: mixer granularity and output latency are FMOD defaults (verify at runtime via `System::getDSPBufferSize` — nominally 1024-sample blocks, 4 buffers).

## Caveats & Fragility

- **Pause/Resume and Seek desynchronize stems.** Only the initial `Play` is DSP-clock-scheduled; per-channel `setPaused(false)` calls resume stems a mixer block apart at worst, and `Seek` has no re-sync at all (the fix is present but commented out in `AudioPack::Seek`). Multi-stem songs can drift audibly after any pause or scrub. This also moves the judge clock (`m_sounds[0]` position) relative to the other stems.
- **`TrackRadio::Update` calls `Play()` every frame while loading.** Each call walks all stems calling `AudioSource::Play` again; it converges once loaded, but it papers over the `AudioPack` readiness model rather than waiting for it.
- **`GetPositionMs` conflates errors with position 0** (`AudioSource::GetPositionMs` returns 0 when the channel is missing or `getPosition` fails, in a variable misnamed `isPlaying`). During gameplay, a transient channel error reads as "song at 0:00" to hit detection.
- **`m_sounds[0]` is assumed to be the main track.** `LoadStem` order guarantees it today (main file loads first), but nothing enforces it; `GetVolume`/`GetPositionMs`/`GetLength` index it unchecked (safe only behind `IsReady()`/`IsPlaying()` empty-checks).
- **The `AudioPack` copy hazard**: it holds a raw `TrackData* m_trackData` into `TrackDatabase::m_trackList.m_tracks` — any database `Reload()` while a pack is alive leaves it dangling.
- **`Drumset::hitPad` leaks channel bookkeeping**: `channels[pad]` stores the last channel per pad but is never used or cleared; `stringToPadID` throws (`map::at`) on unknown pad names in kit JSON.
- **The engine's `AudioThread` name is a lie** — treat it as "the FMOD core"; there is no game-visible audio thread to schedule work on.
- **FMOD debug logging writes `fmod_log.txt`** into the working directory on every run (`FMOD::Debug_Initialize(FMOD_DEBUG_LEVEL_LOG, FMOD_DEBUG_MODE_FILE)`).

## Related Docs

- `Docs/Latency-and-Responsiveness.md` — the position query as judge clock, FMOD latency budget
- `Docs/Gameplay-Note-Highway.md` — the `AudioPack` consumer during play
- `Docs/Songs-and-DLC.md` — where stems come from
- `Engine/Docs/Cores-and-Components-Reference.md` — engine `AudioCore`/`AudioSource` details
