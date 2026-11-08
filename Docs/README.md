# Drumsmith Documentation

Technical documentation for the game side of Drumsmith — a drum rhythm game for real MIDI drum kits, built on [MitchEngine](https://github.com/wobbier/MitchEngine) (the `Engine/` git submodule). These docs cover only the game: gameplay, content, input, audio, UI, and the latency story. Engine internals are documented in `Engine/Docs/` (index: `Engine/Docs/README.md`) — game docs link there rather than re-explaining engine behavior.

## Doc Map

| Doc | What it covers |
|-----|----------------|
| [Game-Architecture.md](Game-Architecture.md) | `GameApp` lifecycle, component/core registration, game events, singletons, settings, game-side build wiring |
| [Gameplay-Note-Highway.md](Gameplay-Note-Highway.md) | `NoteHighwayCore` end to end: track setup, note spawning, hit detection, note lifecycle, pause/resume; the vocals experiment |
| [Stage-Lighting.md](Stage-Lighting.md) | The light show: VENUE cues imported from Rock Band charts, the spot-light rig in volumetric haze, cue looks, the fallback show, hit pulses |
| [Songs-and-DLC.md](Songs-and-DLC.md) | On-disk song format, chart parsing (`notes.mid` / `song.ini` / `.chart`), `TrackDatabase`, the DLC index/download flow, the in-editor track editor |
| [Audio.md](Audio.md) | `AudioPack` stem playback and sync, `TrackRadio` menu music, `Drumset` hit sounds, FMOD threading facts |
| [MIDI-and-Pads.md](MIDI-and-Pads.md) | `MidiDevice` (RtMidi) input path, pad bindings and mapping storage, platform gates |
| [UI-and-Menus.md](UI-and-Menus.md) | The RmlUi menu pages, their view models and the controller components that drive them (radio widget, DLC catalogue, latency test) |
| [Latency-and-Responsiveness.md](Latency-and-Responsiveness.md) | **The latency budget**: every millisecond from drum pad to feedback, the clock inventory, engine constraints on fixes |
| [State-of-the-Game.md](State-of-the-Game.md) | **Opinions live here**: maturity scorecard, gotchas catalog, half-finished inventory, responsiveness roadmap |
| [SharpmakeDependencies.md](SharpmakeDependencies.md) | Sharpmake project graph, binary names, per-project third-party dependencies |

**Suggested reading order:** start with [Game-Architecture.md](Game-Architecture.md), then [Gameplay-Note-Highway.md](Gameplay-Note-Highway.md) and [Songs-and-DLC.md](Songs-and-DLC.md) for the core loop and its data. [Latency-and-Responsiveness.md](Latency-and-Responsiveness.md) is the synthesis doc for anyone working on input feel; [State-of-the-Game.md](State-of-the-Game.md) is the executive summary of where things stand. Engine prerequisites: `Engine/Docs/Architecture.md`, `Engine/Docs/ECS.md`, `Engine/Docs/Jobs-and-Events.md`.

## Conventions

These rules mirror `Engine/Docs/README.md`, adapted for the game repo:

1. **Facts vs opinions.** All docs except `State-of-the-Game.md` are factual: what the code does today, including its limits and sharp edges (each doc's *Caveats & Fragility* section). All opinionated assessment — what should change, priorities, maturity ratings — lives **only** in `State-of-the-Game.md`.
2. **File references** are backticked repo-relative paths from the game root, e.g. `Game/Source/Cores/NoteHighwayCore.cpp`. Engine files are referenced through the submodule path, e.g. `Engine/Source/Engine/Engine.cpp`. A checked reference must contain at least one `/` — bare backticked filenames (`song.ini`) are just names, not checked references. Stale references are scriptable to detect:
   ```bash
   # run from the game root
   grep -rhoE '`[A-Za-z0-9_. -]+(/[A-Za-z0-9_. -]+)+\.(h|cpp|cs|md|json|nix|lvl|vue|py|mid|ogg|txt|prefab)`' Docs/ | tr -d '`' | sort -u \
     | while read -r p; do [ -e "$p" ] || echo "MISSING: $p"; done
   ```
3. **Cite symbols, not line numbers.** Behavioral claims name a function, class, or constant (`NoteHighwayCore::Update`, `MidiDevice::PumpMessages`) so they survive edits and stay greppable.
4. **Diagrams** are Mermaid, at most ~2 per doc, restricted to GitHub-supported types (`flowchart`, `sequenceDiagram`, `classDiagram`, `stateDiagram-v2`, `quadrantChart`), no `%%{init}%%` directives. Validate with the script in `Engine/Docs/README.md` (run it against `Docs/` from the game root). Known traps: `stateDiagram-v2` labels can't contain `::`; `sequenceDiagram` treats `;` as a statement separator.
5. **Verification stamp.** Each doc opens with `> Verified against game commit <hash>, <date>. Engine submodule at <hash>.` Game docs make claims about engine behavior, so the engine pin matters — if either side changes behavior a doc describes, update the doc and its stamp in the same change. Source wins over docs on conflict.
6. **Template** (factual docs): Summary → Overview → Key Files → How It Works → How to Extend (where applicable) → Caveats & Fragility → Related Docs.
7. **Engine deference.** Game docs never re-document engine internals — they state how the game *uses* the engine and link the relevant `Engine/Docs/` page for the mechanism.
