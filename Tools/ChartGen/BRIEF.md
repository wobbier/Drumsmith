# ChartGen — Research & Planning Brief

**Audience:** the agent picking this up (research first, then a concrete plan).
**Status:** pre-research. Nothing is built. Do not write implementation code until the plan in §6 is reviewed.

## 1. Goal

Let players drop in **a plain MP3 of any song** and get a playable Drumsmith drum chart, all on their own machine with no server.

- **End-state input:** a single mixed audio file (mp3/ogg/wav/flac).
- **Fallback input:** separated stems (at minimum a drums stem). Accept this only if research shows that mixed-audio quality can't be good enough, or that it needs more training than is practical. If you go this way, say so explicitly and give the reason.
- **Output:** a song folder the game already loads, i.e. the same layout as an existing `Assets/DLC/*` entry (`notes.mid`, `song.ini`, audio, optional `album.png`). The output must not need a new file format.

## 2. Two phases

**Phase 1: "by any means necessary."** Get MP3 → loadable chart working end to end using pretrained, off-the-shelf models and rule-based charting. No training. Quality only needs to be playable. This phase sets the baseline numbers.

**Phase 2: "Drumsmith-grade."** Refine or train models so the charts read like a human charted them: tom vs. cymbal, accents and ghost notes, 2x kick, sensible difficulty reductions. Shipped as small, local, ONNX-exportable models.

Both phases must share one pipeline interface, so that Phase 2 only replaces stages and never forces a rewrite:
`audio → [separate] → [transcribe → onsets per lane] → [tempo map] → [chart: quantize, lanes, difficulties] → [write notes.mid/song.ini]`

## 3. Read first (in-repo)

- `Docs/Songs-and-DLC.md`: song folder layout, `song.ini`, how songs load.
- `Docs/Gameplay-Note-Highway.md`: lanes, note types, how `notes.mid` is interpreted.
- `Docs/MIDI-and-Pads.md`: pad/lane semantics.
- `Docs/Audio.md`: stem handling and supported formats.
- `Assets/DLC/*`: about 160 existing songs. Each has drum stems (`drums_1..3.ogg`), a full mix, and a hand-authored `notes.mid`. This is a ready-made paired dataset **and** the evaluation set.
- `Game/Source/CoreGame/` (song/track parsing): the ground truth for what the game actually reads.

## 4. Research questions

Answer each one with sources, a recommendation, and its tradeoffs.

### A. Source separation (MP3 → drums)
1. Current best open model for drum separation: Demucs (htdemucs / htdemucs_ft), BS-RoFormer / Mel-RoFormer, others? Compare quality, model size, and CPU inference time for a 4-minute song.
2. Can it be exported to ONNX and run from C++ on Win64/macOS/Linux? Are there existing ports?
3. Does transcription work better on the separated drums or straight on the full mix? This decides whether we ever need stems.

### B. Drum transcription
1. Survey the pretrained automatic drum transcription (ADT) models: ADTOF, Omnizart drums, MT3 / multi-instrument transformers, recent 2025–26 work. Record each one's class vocabulary, reported F1, license, and weight availability.
2. Which models were trained on Rock Band / Clone Hero-style charts (ADTOF was)? Their label space is closest to ours.
3. How well can they separate tom vs. cymbal, hi-hat open vs. closed, and ghost notes from accents?

### C. Tempo and beat tracking
1. Beat This!, madmom, BeatNet, or others: accuracy on rock/pop, tempo-change handling, downbeats, licenses.
2. How should a variable-tempo map go into `notes.mid`? Check against existing DLC files.

### D. Charting (onsets → playable chart)
1. Quantization: which grid, how to handle triplets/swing, and how to snap without destroying fills.
2. Lane mapping from transcription classes to Drumsmith lanes, including pro-drums tom/cymbal markers.
3. Difficulty reduction (Expert → Hard/Medium/Easy): are there documented community conventions? Can the rules be inferred from our 160 charts?
4. Prior art: existing auto-charters for Clone Hero / Rock Band drums (open-source tools, papers). What do they get wrong?

### E. Training (Phase 2)
1. Datasets: ADTOF, E-GMD, MDB-Drums, ENST, Slakh, plus our DLC. Record size, labels, and licenses.
2. Fine-tuning versus training from scratch, given about 160 in-house songs plus public data.
3. Learned difficulty reduction: is there enough paired Expert/Hard/Medium/Easy data in our charts to train on?
4. **Licensing:** what we can ship. Our DLC charts and audio are third-party content. Keep "train locally" and "ship weights" as separate questions, and flag anything risky.

### F. Shipping
1. ONNX Runtime integration cost (binary size, CPU-only performance, all three desktop platforms). UWP only needs to stay unbroken.
2. Total model size budget and processing time for one song on a mid-range CPU. Set target numbers.
3. A Python prototype first, then a C++ port: confirm this is the right order, and say what must stay portable.

## 5. Evaluation

Define it before building.

- **Onset F1 per lane** at ±25 ms (`mir_eval`) against held-out DLC charts, split **by song**.
- **Tempo map accuracy** compared with the DLC charts.
- **Playability:** no physically impossible patterns per difficulty, and note density within human-chart ranges.
- **Subjective:** a small blind A/B against human charts, played in-game.
- Phase 1 sets the baseline. Phase 2 has to beat it on every axis that matters.

## 6. Deliverable of this research pass

One document, `Tools/ChartGen/PLAN.md`, containing:

1. Recommended stack per pipeline stage for Phase 1, with alternatives.
2. A verdict on the **MP3-only vs. stems-required** question, with evidence.
3. Proposed `Tools/ChartGen/` layout (Python package, `uv`/Nix-friendly, `data/` gitignored), CLI shape (`chartgen in.mp3 -o out_dir/`), and the stage interfaces.
4. The Phase 1 milestone list, ending at "random MP3 loads and plays in Drumsmith" plus baseline metrics on 20 held-out DLC songs.
5. The Phase 2 outline: data, model changes, evaluation targets, ONNX/C++ integration.
6. Risks and open questions (licensing first).

## 7. Constraints

- Everything runs locally and offline at play time. No cloud inference for players.
- The final runtime has to work on Win64, macOS and Linux (see the root `CLAUDE.md`).
- Generated build files and data/model artifacts stay out of git.
- Follow the repo's git rules: stage changes only, never commit or push.
