# Audio

> Verified against game commit 1714270, 2026-07-10. Engine submodule at 047f57b8.
>
> Updated 2026-11-17 against the working tree (the Linear ticket pass, DRU-14 to DRU-54, on game commit 4f29840; engine submodule at c5bb6135): the `TrackRadio` section and its caveats; later that day, Venue ambience (game commit 44f9469 plus the working tree). The rest is as last verified.

The game's three audio systems — `AudioPack` (synchronized stem playback for gameplay and radio), `TrackRadio` (menu background music), and `Drumset` (pad hit sounds, currently dormant) — plus a venue's ambience before the song, and the FMOD facts underneath them.

## Overview

All game audio goes through FMOD Core via the engine's `AudioCore` (`Engine/Source/Cores/AudioCore.cpp`), reached as `GetEngine().AudioThread` — a misleading name: it is a regular core whose `Update` runs on the **main thread** each frame and pumps `FMOD::System::update()`. FMOD's actual mixer runs on FMOD-internal threads. The engine initializes FMOD with `FMOD_INIT_NORMAL`, 512 channels, a 64 KB stream buffer, and **default DSP buffer settings** (no `setDSPBufferSize` call), logging to `fmod_log.txt`.

`AudioPack::GetPositionMs` is *the* gameplay clock — `NoteHighwayCore` judges every hit against it — so this doc is a prerequisite for `Docs/Latency-and-Responsiveness.md`.

## Key Files

| Path | Role |
|------|------|
| `Game/Source/CoreGame/AudioPack.h` | Multi-stem playback wrapper (gameplay + radio) |
| `Game/Source/Global/TrackRadio.h` | Menu music singleton state machine |
| `Game/Source/UI/TrackRadioUtils.cpp` | Starts the next random song and fills the radio widget's view-model values |
| `Game/Source/CoreGame/Drumset.h` | Pad→sample hit-sound player (unused at runtime) |
| `Game/Source/Venue/VenueShow.cpp` | A venue's ambience: `StartAmbience`, `UpdateAmbience` |
| `Engine/Source/Cores/AudioCore.cpp` | FMOD system init/update (engine) |
| `Engine/Source/Components/Audio/AudioSource.cpp` | Per-sound channel wrapper: play/pause/seek/position (engine) |

## How It Works

### AudioPack — synchronized stems

Constructed from a `TrackData`, an `AudioPack`:

1. Creates an `FMOD::ChannelGroup` named after the track and parents it to the master group.
2. Calls `LoadStem` for the main track file plus a **hardcoded stem list**: `crowd.ogg`, `drums.ogg`, `drums_1.ogg`–`drums_4.ogg`, `guitar.ogg`, `vocals.ogg`, `rhythm.ogg`, `keys.ogg`. Missing files are skipped silently (`Path::Exists` check); drum stems are remembered by index in `m_drumTracks`.
3. Each stem loads through `ResourceCache::Get<Sound>` with `SoundFlags::NonBlocking | SoundFlags::CreateStream` — loading is asynchronous, and `IsReady()` polls until every `AudioSource::IsLoaded()` is true.

**Playback start is sample-accurate**: `AudioPack::Play` reads the group's DSP clock (`getDSPClock`), starts every stem paused, assigns it to the group, schedules `setDelay(groupClock + 2048, 0)` on each channel (a channel's delay counts on its parent's clock: the group's), then unpauses — all stems begin together 2048 samples (~43 ms at 48 kHz) in the future.

**Pause and seek keep the stems together**:

- `Pause`/`Resume` pause and unpause the group (`ChannelGroup::setPaused`), so every stem stops and starts on the same mixer tick.
- `Seek` pauses each stem's channel and `setPosition`s it. The stems are non-blocking streams, so each seek completes on FMOD's loader thread in its own time (the sound's open state reads `FMOD_OPENSTATE_SETPOSITION` until then); unpausing them straight away, as the old `Seek` did, started each stem whenever its seek landed. `AudioPack::Update` (called every frame by `NoteHighwayCore` and `TrackRadio`) waits until every stem has finished seeking (or 500 ms have passed), then schedules all of them on one `setDelay(groupClock + 2048)` and unpauses them, as `Play` does. `IsSeeking()` stays true until that tick; meanwhile `GetPositionMs` reports the seek target and the song clock holds.
- `StemSpreadMs` measures how far apart the playing stems are; `--highway-log` prints it with the clock. Seeking Foreplay / Long Time (eight stems) to 4:10 headless reads 0 ms apart.

`GetPositionMs`/`GetLength`/`GetVolume` delegate to `m_sounds[0]` — the main track stem — via `AudioSource::GetPositionMs`, which is `FMOD::Channel::getPosition(FMOD_TIMEUNIT_MS)` and returns 0 on error or missing channel.

`LoadURL` (streaming a remote file) exists but is only lightly used; it calls `Play()` immediately per stem added.

### Metronome

With **Metronome** on (`GameSettings::Metronome`; Settings > Sound & Timing, or the pause options), a song plays with a click on every beat of its beat grid, higher on each bar's first. The click is one more stem, so it starts, pauses, seeks and fades with the song and can't drift from it:

1. `NoteHighwayCore::UpdateMetronome` turns the chart's beat lines into clicks and asks `ClickTrack::MetronomeFile` (`CoreGame/ClickTrack.h/.cpp`) for their file: a 22.05 kHz mono WAV under `.tmp/Metronome/`, named by a hash of the click times, written if it isn't there (about 2.6 MB a minute of song; the folder keeps the newest six).
2. `AudioPack::AddMetronome` loads it like any stem. At song start that is before `Play`, so it starts on the shared tick. Switched on mid-song (the pause options), the stem has no channel until the next `Seek`, which gives it one held with the rest; the resume's run-up is that seek, so the click comes in when the song does.
3. `SetMetronomeVolume` silences it when the setting goes off; the stem stays loaded.

A practice lesson and the calibration are click tracks already and get none. A chart with no beat grid (no beat lines on the highway) has nothing to click on. `--metronome [seconds]` forces it on from that point of the song; `--highway-log` says whether its stem is playing. Headless (FMOD's silent output), Gimme Shelter's 544 clicks read 0 ms apart from the other stems, both from the start and switched on at 4 s with a pause at 6 s.

`ClickTrack::Write` is also what writes a practice lesson's and the calibration's click (`Practice::WriteClickTrack`).

### TrackRadio — menu music

A singleton state machine (`None → Loading → Seeking → Playing`) that owns its own `AudioPack`. `Play(RadioArgs)` selects a library track (ignoring requests for the already-playing index); `PlayGuest(track, usePreviewMarker)` plays a song that isn't in the library from the radio's own copy of its `TrackData` (the DLC page's preview of a song not downloaded yet; `GetCurrentTrack` returns that copy and `GetCurrentTrackIndex` -1). Opening a song's stems takes about 0.2 ms (they are non-blocking streams; measured 2026-11-17), so nothing here needs a thread of its own. `Update` is called once a frame by `MenuCore::Update`, on every page, and walks the states:

- `Loading`: waits for every stem to load (`AudioPack::IsReady`); then plays, applies `GameSettings::RadioVolume`, and either starts playing or seeks to the track's `PreviewPercent` marker first. A song that hasn't loaded after 10 s (a broken file) is given up on, so the next can play.
- `Seeking`: waits for readiness, then `Resume()`.
- `Playing`: when playback ends, returns to `None`, which lets `TrackRadioUtils` auto-play the next random track.

`TrackRadioUtils` also fills the radio widget's model values (title, art, position/duration, visibility) and handles its `skip`/`seek` events — see `Docs/UI-and-Menus.md`.

### Venue ambience

A venue scene's `venue.json` can name a sound to play before the song (`Ambience`, `AmbienceVolume`, `AmbienceFade`; `Docs/Venue-Authoring.md`). The Backyard's is `Assets/Sounds/crowd.mp3`. `VenueRegistry::LoadFolder` reads it into the entry's `VenueAmbience` and the pick carries it (`VenueChoice::Ambience`). When `VenueShow` builds a scene venue for a play (`NoteHighwayCore::SetupTrack` sets `SetAmbienceWanted( true )`; `BeginPreview`, the Track Editor's, sets it false), `StartAmbience` makes a "Venue ambience" entity under the venue root with an engine `AudioSource`: `Stream`, `Loop`, 2D, on the SFX bus, not part of the `AudioPack`. `AudioCore` opens the stream in the background; once it is ready, `UpdateAmbience` starts the voice paused, moves it to a random point in the clip (a fresh one each play, so a long crowd recording doesn't open on the same few seconds every song) and unpauses it. In practice that is inside the load and the 2 s lead-in.

`VenueShow::Update` sets its volume from the song clock: full while the clock is negative (loading, lead-in), then a cosine ease to zero over `AmbienceFade` seconds from the song's start, when it is stopped. `NoteHighwayCore::Pause` / `Resume` pause it with the song. It goes with the venue (`VenueKit::Clear`), so a Restart or F7 starts it again; past the fade, F7's rebuild stops it on the next update. Headless on the Backyard (2026-11-17): playing from the first frame of the lead-in (two runs started 4:23 and 6:15 into the 10:14 clip), 0.92 at 1.5 s, 0.55 at 3.8 s, 0.12 at 6.2 s, stopped at 8.2 s.

### Drumset — hit sounds (dormant)

`Drumset` maps `PadId → FMOD::Sound*` loaded with `FMOD_CREATESAMPLE` (fully decoded into memory — the right choice for low-latency one-shots). `hitPad(pad, velocity)` plays the sample immediately via `System::playSound` and scales volume by clamped velocity. `loadFromJson` can populate a kit from a `{"kits": {"default": {padName: filePath}}}` JSON.

**Current reality:** the only instantiation is in `TrackEditor::Init` (`ME_EDITOR` builds), and its `loadSound` calls are commented out — `loadFromJson` has no callers. The sound map is always empty, so every `hitPad` call early-returns. **No hit sound plays anywhere in the game or editor today.** The sample assets exist (`Assets/Drums/Basic/Bass.wav`, `Assets/Drums/Basic/Snare.wav`). Gameplay (`NoteHighwayCore`) has no `Drumset` at all — the only audible feedback during play is the pre-mixed song itself.

### FMOD threading facts

- `FMOD::System::update()` is pumped once per frame from `AudioCore::Update` on the main thread; mixing/streaming happen on FMOD's own threads regardless.
- FMOD Core is initialized without `FMOD_INIT_THREAD_UNSAFE`, so its API is **thread-safe by default** — `playSound` may legally be called from any thread (relevant to latency work; see `Docs/Latency-and-Responsiveness.md`). Engine-side objects (`ResourceCache`, entities, events) remain main-thread-only per `Engine/Docs/Jobs-and-Events.md`.
- No `setDSPBufferSize`/`setSoftwareFormat` calls: mixer granularity and output latency are FMOD defaults (verify at runtime via `System::getDSPBufferSize` — nominally 1024-sample blocks, 4 buffers).

## Caveats & Fragility

- **A seek waits for every stem.** A stem whose seek never completes holds the restart for up to 500 ms, then everything starts anyway, possibly that stem out of step.
- **Only a page with the radio widget starts the next song.** `MenuCore` ticks the radio everywhere, but picking the next random track is `TrackRadioUtils`' job; on the library, stats and practice pages a song that ends is followed by silence until a preview or another page.
- **`TrackDatabase::RemoveTrack` shifts indices under the radio**; `TrackRadio::OnTrackRemoved` keeps its index right and drops the song if it was the one removed.
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
