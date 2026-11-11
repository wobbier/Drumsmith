# ChartGen plan

> Research pass for `BRIEF.md`, 2026-11-11, checked against the Drumsmith working tree of that date. Nothing is built. Sources are linked inline and listed in §10. A claim marked *(unverified)* came from a secondary source or a page that could not be read in full.

## 0. Status (2026-11-11)

Phase 1 is built and passes its bars. The code is in `~/Projects/Python/ChartGen` (local commits; it has no remote yet). `STATUS.md` there records each milestone's exit test and `BASELINE.md` the frozen numbers on the 20 test songs.

| Bar (M8, test songs, real-kit view) | Result | Needed |
|---|---|---|
| Overall F1 within 50 ms | 0.814 | 0.70 |
| Kick / snare | 0.944 / 0.898 | 0.80 / 0.75 |
| Matched notes inside 30 ms | 97.1% | 80% |
| Songs that convert and play to the results screen | 20 of 20 | all |

What execution changed or settled in this plan:

- **Section 4, the three decision rules** (dev): the mix alone scores 0.825, so MP3-only stands. True stems beat separated drums by 0.029, so stems stay optional. Separated drums beat the mix by 0.045, so separation stays on the critical path and the configuration without it is the fallback, not the default.
- **Section 3.7 budgets.** With separation a five-minute song needs about a minute of model time on six threads of this machine (6 s without); peak memory is 2.6 to 2.9 GB, over the provisional 2 GB.
- **Section 6, the references.** The gems depart from the kit more than stated: two-handed 16th hi-hats are charted as alternating snare and hi-hat gems (*Everlong*, *Crazy Train*) and a snare flam as snare plus yellow tom. The real-kit view is the animation strokes plus any gem they do not cover (second-pedal kicks).
- **Section 3.5, lanes.** Ring time does not separate open from closed hi-hats, so Phase 1 writes every hi-hat closed. Tom pitch rank types only about half of tom hits as the animation track does; the animation's tom labels often disagree with pitch order. Ride versus crash by rule is right for 74% of matched hits.
- **Section 2, stored BPM.** The lead-in before the first tracked beat rarely runs at the song's tempo, so the writer puts the song's tempo first at tick 0, followed by the real lead-in tempo at the same tick. The game stores the first and times by the second.
- **Section 5, `--install`.** It converts the new folder in a sandbox copy of the project (an `Assets` of links with an empty `DLC`) and moves the finished folder in. The converter is never run over the real library.
- **Converter findings**, filed: a fresh conversion of an original CRLF folder crashes on Linux (ME-357, reproduced); the album is never copied (ME-358); the stage drummer's table misreads notes 32, 40 and 41 and has no open hi-hat (ME-359).
- **Not done:** the blind A/B needs a player (`out/ab/` holds the 20 pairs and a sheet), and the optional STRUM baseline of M3 was skipped.
- **Phase 2 has started** with step 2, the typing model: on dev it types 81% of matched cymbal hits right (rules 74%) and 78% of hi-hats as open or closed. It is trained on the DLC and stays out of git (section 9, question 3).

## 1. Summary

**Verdict: a plain MP3 is enough. Players never need to supply stems.** The best available drum transcriber is trained on full mixes, separate-then-detect pipelines have not clearly beaten it, and drums separated by Demucs transcribe almost as well as true stems. Separation stays in the pipeline as an internal step, because it gives the game a drum stem to mute on a miss and helps tell cymbals and toms apart (§4).

**Phase 1 stack:** ffmpeg decode, Demucs drum separation, ADTOF drum transcription, Beat This! beat tracking, rule-based charting, and a writer that emits the folder Drumsmith's converter accepts (§3.1).

**Decisions made with Mitch, 2026-11-11:**

- Drumsmith is free, GPL-3.0, non-profit software that teaches real drums through music the player likes. Non-commercial models may therefore be used with attribution, and a chart should follow what the drummer really played, not a simplified gameplay part.
- ChartGen is a standalone project at `~/Projects/Python/ChartGen`. Drumsmith keeps only `Tools/ChartGen/BRIEF.md` and this file.
- A song with no drum kit gets a clear "no drums found" result in Phase 1. Inventing a part for it is a Phase 2 item.

**Corrections to the brief, from the source:**

1. The game does not load `notes.mid`. It loads `TrackData.txt` and `NoteData.txt`; `notes.mid` and `song.ini` are inputs to the converter (`--convert-dlc`). ChartGen's output must pass that converter (§2).
2. Album art is not optional in practice. The converter asserts without it, which is a modal dialog on Windows dev builds and a dangling art path elsewhere.
3. Only Expert survives. The converter discards Hard, Medium and Easy, and `NoteData.txt` holds one note list, so difficulties need converter and format work as well as a selector.
4. The paired dataset is 124 songs, not 160: 129 folders have a chart, and 124 of those also have a drum stem.
5. Rock Band gems do not name the real kit piece. Measured on the 99 charts that carry both tom markers and drummer-animation notes, a blue cymbal gem is a ride 72% of the time, a crash 13% and a hi-hat 15%; a third of yellow cymbal gems are open hi-hats. The animation notes do name the piece, so they are the reference for a game that teaches real drums (§6).
6. Ghost and accent labels are nearly absent: one chart uses dynamics, and 17 have soft snare hits in their animation notes.

## 2. What the game reads

Verified in `Game/Source/CoreGame/CustomTrackDefineTest.cpp` (`readSongMetaData`, `ParseMidi`, `ReadMidiBeats`), `TrackList.cpp` (`ConvertFromLegacy`, `TrackDatabase::ExportMidiTrackMetaData`, `TrackData::OnLoadTrackData`) and `AudioPack.cpp`.

| Output | Rules the writer must follow |
|---|---|
| `song.ogg` | Always written, Vorbis (Opus is unsupported). It is the song clock and decides when the song ends. |
| `drums.ogg` | Optional. The game plays every stem it finds on top of the others and mutes the drum stems on a miss. So when `drums.ogg` exists, `song.ogg` must be the mix without drums. No other stem file may be left in the folder by accident. |
| `album.png` | Always written, re-encoded as a plain PNG (the UI decodes it directly). |
| `song.ini` | LF line endings and a first line of exactly `[song]`. The parser matches that line exactly, so a CRLF file reads as empty on Linux and macOS. Always write `name`, `artist`, `album`, `genre`, a numeric `year` (`std::stoi`, uncaught), `song_length` and `preview_start_time` in ms, and `pro_drums = True` spelled exactly so. |
| `notes.mid` | Format 1, 480 ticks per quarter note. Track 0 holds every tempo and time-signature event, with a tempo at tick 0. The first tempo event becomes the song's stored BPM, which paces the fallback light show, so the opening bar must stay near the song's tempo. End the file after the song ends; beat lines stop at the last event. |
| `PART DRUMS` | Track name matched exactly. Read: 95 and 96 kick, 97 snare, 98/99/100 yellow/blue/green, which are hi-hat, ride and crash unless a tom marker (110/111/112) covers the note, making them high, mid and floor tom. A marker must span its gem and stop before the next cymbal of that colour. A tom and a cymbal of one colour cannot share a tick. |
| Dynamics | With an `[ENABLE_CHART_DYNAMICS]` text event in the drum track, velocity 1 is a ghost and 127 an accent. Normal gems use 100. |
| The folder | ASCII name, built elsewhere and moved into `Assets/DLC` whole, since the game waits on every stem it sees. Always a fresh folder: re-converting an existing one rewrites only the notes and leaves duration, BPM and note count stale. |

Through `notes.mid` the game shows eight pads: kick, snare, closed hi-hat, ride, one crash, three toms. Open hi-hat, hi-hat pedal, second crash, splash, china and the rim, cross-stick and bell strokes exist in the game but cannot be reached from a Rock Band chart today (§9, open question 2).

What the 129 DLC charts look like (measured):

| Property | Value |
|---|---|
| Ticks per quarter note | 480 in every file |
| Tempo events per song | Median 103; only 6 songs hold one tempo; 27 change time signature |
| Expert notes on the 16th grid | 94.4% (triplets 2.4%, 32nds 0.4%, off-grid 2.7%) |
| Note count relative to Expert | Hard 0.83, Medium 0.62, Easy 0.41 (medians) |
| Tom markers / 2x kick / dynamics | 101 / 7 / 1 charts |
| Drummer-animation notes (24–51) | 103 charts; 99 also have tom markers |
| `song.ini` line endings | 128 of 129 are CRLF |
| Charters | About 99 Harmonix, 25 Neversoft, a few community |

## 3. Research answers

### 3.1 Phase 1 stack

| Stage | Pick | Why | Alternatives |
|---|---|---|---|
| Decode | ffmpeg to 44.1 kHz float PCM, once | The audio analysed must be the audio played (§9, risk 8) | soundfile |
| Separate | Demucs v4, the `htdemucs_ft` drums specialist (84 MB) | Best-supported open separator; ONNX and C++ ports exist | SCNet (42 MB, about half the CPU time); BS-RoFormer SW for comparison only |
| Transcribe | ADTOF through the ADTOF-pytorch port, on the mix and on the drum stem | Trained on Rock Band-style charts of full mixes; 5 MB | STRUM as an end-to-end baseline; Onsets and Frames (E-GMD) on the stem for velocity |
| Beats | Beat This! `final0`, with `small` measured alongside | Best published accuracy, MIT code and weights, no fixed-tempo assumption | BeatNet (CC BY 4.0); All-In-One if section labels are wanted |
| Tempo map | Constant-tempo segments fitted to the beats and the drum onsets, at most one tempo event per beat | Matches how human charts are tempo-mapped | One event per beat |
| Chart | Rules: per-beat subdivision choice, lane mapping, reductions | No training in Phase 1 | — |
| Write | `mido` for `notes.mid`; ffmpeg for Vorbis; embedded cover or a generated placeholder | Meets §2 | — |

### 3.2 A. Source separation

**A1. Best open model.** Drum quality is measured as signal-to-distortion ratio (SDR, in dB, higher is better). Numbers from different test sets are not comparable.

| Model | Drums SDR | Size | CPU cost | Weights licence |
|---|---|---|---|---|
| Demucs `htdemucs` | 10.05 (paper, with 800 extra songs) | 84 MB | README: about 1.5× the track length | Code MIT. Author: "The license of the weights is not clear" |
| Demucs `htdemucs_ft` | 10.08 | 4 × 84 MB; the drums specialist alone is one 84 MB file | Full set is 4× slower; the specialist costs about one model | Same |
| SCNet | 10.51 (MUSDB-only) | 42 MB, 10 M parameters | About half of Demucs on one thread | Code MIT; trained on MUSDB, no stated weights licence |
| SCNet-XL | 11.5–11.8 | 214 MB | Not published | Same |
| BS-RoFormer SW | 14.1 on MVSEP's own set, the best public model | About 700 MB | Not published | Unknown; one mirror labels it non-commercial |

Every strong separator is trained on MUSDB18 (research use only), on private data, or carries non-commercial terms. Meta's Demucs repository is archived; `adefossez/demucs` is the maintained copy (v4.1.0, July 2026), though its author is no longer developing it. Published timings for a 4-minute song range from 85 seconds to 6 minutes on different or unnamed hardware, so Phase 1 measures them (§7, M3).

Higher SDR does not mean cleaner drum hits: a 2026 study found SCNet-XL distorts attacks least while BS-RoFormer leads on SDR *(unverified)*. The separator is therefore chosen on transcription accuracy, not SDR.

**A2. ONNX and C++.** ONNX has no complex numbers, so the spectrogram step does not export. Two fixes exist: compute it in host code ([demucs.onnx](https://github.com/sevagh/demucs.onnx), which also builds a minimal ONNX Runtime), or rewrite it as ordinary convolutions inside the graph ([Mixxx's 2025 project](https://mixxx.org/news/2025-10-27-gsoc2025-demucs-to-onnx-dhunstack/): no quality loss, 21 s per minute of audio on an unnamed CPU). [demucs.cpp](https://github.com/sevagh/demucs.cpp) is a hand-written C++ port: 4 min 09 s for a 4-minute song on 16 threads of a Ryzen 5950X. SCNet and RoFormer have ONNX exports but no C++ port.

**A3. Separated drums or the full mix?** See §4.

### 3.3 B. Drum transcription

Scores are F1 (1.0 means no missed and no extra notes) within 50 ms unless stated.

| Model | Classes | Accuracy on real mixes | Input | Size | Licence |
|---|---|---|---|---|---|
| **ADTOF** | 5: kick, snare, toms, hi-hat, crash+ride | 0.87 MDB, 0.84 ENST in one study; 0.80 / 0.71 in another | Full mix | 5 MB, a small convolutional-recurrent net at 100 frames/s | CC BY-NC-SA 4.0 (repo and bundled weights) |
| ADTOF-pytorch | Same | 0.2 points below the original | Full mix | 3.6 MB | No licence file; weights derive from ADTOF |
| YourMT3+ | About 19, incl. open/closed hi-hat, ride, crash | 0.41 on one real-music test | Full mix | 30–46 M parameters, autoregressive | Weights Apache-2.0, code GPL-3.0 |
| Onsets and Frames (E-GMD) | 7, with velocity | Not evaluated on mixes | Drums only | Small | Apache-2.0 |
| STRUM | 8 lanes | 0.84 at a loose ±100 ms with per-song offset search; blue-lane accuracy 0.19 | Full mix (separates internally) | About 6 GB, needs CUDA | MIT |
| MT3 | General MIDI drums, no velocity | 0.70 ENST | Full mix | Autoregressive | Apache-2.0 |
| Omnizart | 13 internally, 3 written | 0.74 ENST, 0.71 MDB | Full mix | 9 M parameters | MIT |
| MuScriptor | Onsets only | 0.50 on its own test | Full mix | 60 M and up | CC BY-NC, gated |
| Noise-to-Notes | 7, with velocity | 0.88 MDB | Drums-trained | About 50 M plus a 330 M feature model | No release found |

**B2. Trained on rhythm-game charts.** ADTOF is: its two sets are ADTOF-RGW (Rhythm Gaming World charts, 89 h) and ADTOF-YT (202 h). Its converter maps gems as Drumsmith's parser does and uses the drummer-animation notes to undo known Expert simplifications. It fixes chart-to-audio alignment by comparing the chart's beats with a beat tracker and discards badly aligned tracks. Only spectrograms are shared, on request, for non-commercial internal use. STRUM (about 5,000 charts) and CloneCharter (about 42,600 charts, no accuracy reported) are also chart-trained.

**B3. Fine distinctions.**

- ADTOF per class on MDB / ENST: kick 0.85 / 0.80, snare 0.75 / 0.60, toms 0.52 / 0.58, hi-hat 0.77 / 0.78, cymbals 0.85 / 0.66. Its authors report toms as largely solved on rhythm-game data and cymbals as the weakest class, worse in dense mixes.
- Two humans charting the same song agree at only F1 0.87 overall, 0.73 on hi-hat and 0.83 on cymbals. That is the ceiling for any score against human charts.
- A finer vocabulary costs about 10 points: one model scores 0.79 on MDB with 5 classes and 0.67 with 18.
- Adding open/closed hi-hat and crash/ride by splitting the drum stem into kit pieces reached 0.84 on MDB in one study.
- Velocity comes only from the E-GMD model family. No source reports ghost or accent accuracy.

### 3.4 C. Tempo and beats

Beat scores use the field's usual ±70 ms window.

| Tracker | Beat / downbeat F1 (GTZAN) | Size | Licence | Notes |
|---|---|---|---|---|
| **Beat This!** | 89.1 / 78.3 (small: 88.8 / 77.2) | 78 MB (small: 8 MB) | MIT, code and weights | No tempo-continuity assumption, so tempo and meter changes are fine, but it can emit stray beats. A [C++ ONNX port](https://github.com/mosynthkey/beat_this_cpp) exists. |
| madmom | 79.1 / 51.4 | — | Models CC BY-NC-SA | Its tempo model assumes continuity; PyPI build needs Python below 3.10 |
| BeatNet | 80.6 / 54.1 offline | — | CC BY 4.0 | Lighter fallback |
| All-In-One | 95.8 / 91.5 on Harmonix only | 300 K parameters | MIT | Also gives song sections; needs Demucs and madmom code |
| librosa, Essentia, aubio | Weaker or unpublished | — | ISC / AGPL / GPL | No downbeats, or weak |

No source publishes CPU timings for any of them; Phase 1 measures.

**C2. The tempo map.** Rock Band's authoring rules ask for one tempo marker per measure and never more than one per beat. Our DLC agrees: a median of 103 tempo events per song. The plan:

1. Repair the tracker's output: half/double-time slips and stray beats.
2. Pull each beat onto the nearest kick or snare onset, as human charters do. Without this the grid carries the tracker's own error.
3. Fit constant-tempo segments, starting a new one only where the beats drift further than the tracker's measured error.
4. Pick the time signature from downbeat spacing.
5. Write tempo events at beat boundaries into track 0. Tick 0 is audio time 0, and the opening partial bar is given a whole number of beats at close to the song's tempo (§2).

The game's own 2-second lead-in means the audio needs no padding.

### 3.5 D. Charting

**D1. Quantization.** Each beat picks its own subdivision from 1, 2, 3, 4, 6 or 8 notes per beat. The cost is timing error, plus a preference for simple grids weighted by how human charts are distributed (§2), plus a penalty for changing grid from the previous beat; a Viterbi pass picks the cheapest path. Fills survive because a beat that needs 32nds or triplets can switch, and the triplet grids cover swing.

Snapping must not cost timing. Detected onsets are first refined against the drum stem. A note then moves by at most a tuned limit (20 ms to start); beyond that it keeps its detected time, which is legal because the game judges in seconds and 2.7% of human notes are off-grid anyway. M5 checks that the share of notes inside the game's 30 ms Perfect window does not fall after quantizing.

**D2. Lanes.** ADTOF gives five classes; the game wants eight pads. Each onset is first described from the audio (pitch, ring time, how much of it is in the drum stem), then mapped by the instrument it is:

| ADTOF class | Chart | How the split is made |
|---|---|---|
| Kick | 96; 95 for hits only a second pedal could reach | Gap to the previous kick |
| Snare | 97 | — |
| Hi-hat | 98 as cymbal | Open versus closed cannot be written yet (§9) |
| Toms | 98/99/100 under markers 110/111/112 | Pitch of each hit on the drum stem, ranked high to low within the song; kits with more than three toms are grouped into three |
| Crash + ride | 99 as cymbal for ride, 100 as cymbal for crash | Ring time and context: a steady stream is a ride, an accent on a strong beat with a kick is a crash |

This follows the kit, not Rock Band habit, which puts open hi-hats and some crashes on blue. Where a tom and a cymbal of one colour land on the same tick, the cymbal moves to a neighbouring colour. `pro_drums = True` is always written.

**D3. Reductions.** The Rock Band Network authoring docs give written rules, summarised:

- **Hard:** thin kicks on adjacent 8ths and 16ths, no kicks in fills, 16th rolls only briefly and never at 140 BPM or above.
- **Medium:** no three-limb hits, nothing between the timekeeping notes, right hand on quarter notes at 140 BPM or above, fills reduced to 8ths.
- **Easy:** nothing ever paired with a kick, no kicks on off-beats, one kick per bar at 170 BPM or above.

All 129 charts have all four difficulties, so the rules can be calibrated to the measured ratios and scored against human reductions. One paper treats reduction as translation learned from aligned difficulties ([Gold and Olivier, 2010](https://ojs.aaai.org/index.php/AIIDE/article/view/12396)); that is the Phase 2 route.

**D4. Prior art.**

- **[AutoDrums](https://github.com/CapyyC/chart)** (October 2026) is the closest: Demucs, Beat This!, ADTOF on both mix and stem plus the E-GMD model, a tree-based verifier, a cymbal classifier, per-beat subdivision, rule reductions. It reports lane F1 0.845 within 50 ms on annotated recordings, and 3–5 minutes for a 4-minute song with separation or under a minute without (hardware not stated). Its stated weak spots are ghost notes, toms buried in the mix, crash versus ride, and guitar or vocal bleed read as snare. It has no licence file, so it is a design reference only.
- **[STRUM](https://arxiv.org/abs/2605.12135)** (May 2026, MIT) charts drums, guitar, bass, vocals and keys end to end. Its accuracy claims use a loose window, and it needs a GPU.
- **[charter](https://github.com/Johan-ZeLearner/charter)**: its author paused automatic transcription because it was unreliable on dense, distorted music.
- **Other games:** Dance Dance Convolution splits the job into where to place a step and which step to place. Audiosurf analysed the whole song before play and tied speed to intensity; no algorithm is published.

### 3.6 E. Training data and licensing

| Dataset | Size | Labels | Licence |
|---|---|---|---|
| Our DLC | 124 songs with stems, mix and chart; 99 with real-kit labels | Gems, tom markers, animation notes, four difficulties | Third-party content |
| ADTOF-RGW / YT | 89 h / 202 h | 5 classes | Spectrograms on request, non-commercial, no redistribution |
| E-GMD | 444 h, drums only | 7 classes, velocity | CC BY 4.0 |
| StemGMD | 1,224 h of kit-piece stems | 9 | CC BY 4.0 |
| STAR Drums | 124 h, real music under resynthesised drums | 18 classes, velocity | BSD-3 on the record; per-track audio licences unchecked |
| Slakh2100 | 118 h, synthetic | Mapped | CC BY 4.0 |
| MDB Drums | 0.4 h, real | 6 classes, 21 subclasses | CC BY-NC-SA |
| ENST / IDMT | 1 h / 2 h, real | 20 / 3 | Research only / CC BY-NC-ND |

**E2. Fine-tune or train from scratch.** Fine-tune. Published systems used 90 to 440 hours. After the evaluation split, about 60 of our songs carry real-kit labels for training, a few hours of audio: enough to adapt a model, not to train one. Real data beats synthetic and the gap persists (Zehren 2024), while synthetic pretraining followed by real refinement has precedent. A model trained on STAR Drums alone matched ADTOF-trained models at 3 and 5 classes, which makes it the candidate for a fully free model.

**E3. Learned reductions.** There are 129 songs with three aligned reductions each, about 100 of them after the split. Whether that is enough is untested; the charts also mix Harmonix and Neversoft habits. Phase 2 trains a small keep/drop/move model and keeps it only if it beats the rules.

**E4. What can ship.** This is a reading of the licence texts, not legal advice.

| Item | Local use | Shipping with free GPL Drumsmith |
|---|---|---|
| Beat This! | Yes | Yes (MIT) |
| ADTOF weights | Yes | Allowed for non-commercial use with attribution. Adapted weights, including an ONNX export or a fine-tune, must carry the same CC BY-NC-SA licence. Ship as a separately licensed download, not inside the GPL source tree. |
| ADTOF-pytorch code | Yes | No licence, so it cannot be redistributed. Phase 2 reimplements the small network and loads the original weights. |
| Demucs weights | Yes | The author cannot grant a licence. The game needs them in ONNX form, and hosting that export is redistribution. Mitch's call (§9, open question 1). |
| Weights trained on our DLC | Yes | Unsettled. The charts and audio are third-party content. Comparable projects (ADTOF, STRUM, CloneCharter) release chart-trained weights, but none addresses the question. Mitch's call. |
| The DLC itself | Yes | Never |

Non-commercial weights are not free software in the strict sense. A model trained only on CC BY and BSD data would make the default download fully free; that is a Phase 2 stretch goal.

### 3.7 F. Shipping

**F1. ONNX Runtime.** MIT. Version 1.31.1 (October 2026) CPU library: 17 MB on Windows x64, 29 MB on Linux x64, 45 MB on macOS arm64. No CPU performance figures are published for our models; Phase 1 measures. Since 1.24 there are no Intel-Mac binaries and macOS 14 is the minimum (§9, open question 5). UWP status could not be confirmed, so ChartGen is compiled out there behind a `USING( ... )` feature flag. Inside the game, cap the thread count and turn off thread spinning. Alternatives: ggml (proven for Demucs, but every layer is hand-written), libtorch (80 MB, too heavy), LiteRT and ExecuTorch (mobile-oriented, extra conversion).

**F2. Targets** for a 4-minute song on a six-core desktop CPU from about 2019, no GPU. Provisional until Phase 1 measures; the dev machine runs them with six threads.

| Budget | Target |
|---|---|
| Chart ready to play, no separation | 60 s or less |
| Including separation | 4 minutes or less; if Demucs cannot meet it, SCNet |
| Core models (transcriber + Beat This! `small`) | 30 MB or less |
| Optional separation download | 90 MB or less |
| Peak memory | 2 GB or less |

Phase 1 baselines both configurations, with and without separation. If the fast chart is close to the full one, the game can let the player start at once and upgrade later. That upgrade must swap `song.ogg` and `drums.ogg` together, because the game sums stems.

**F3. Python first, then C++.** Yes. Models, datasets and metrics all live in Python. One bridging step makes the port safe: before any C++, make Python inference run on ONNX Runtime and NumPy alone, with no PyTorch. That proves the exported graphs. What must stay portable:

- Spectrograms sit inside the ONNX graph, as convolutions, so C++ cannot drift from Python.
- Decoding and resampling are outside any graph. The C++ decoder is compared against ffmpeg on test files, and every resampler passes an impulse test showing zero delay.
- Charting rules and onset descriptors (tom pitch, ring time) are plain functions over arrays, with golden JSON inputs and outputs the C++ port must reproduce.
- Every stage can run in chunks, so charting can later start before the whole song is processed.

## 4. Verdict: MP3 only

Stems are never required from the player. The evidence:

1. **Full-mix transcription works.** ADTOF is trained and evaluated on full mixes: F1 0.87 on MDB and 0.84 on ENST ([2509.24853](https://arxiv.org/abs/2509.24853)).
2. **Separating first has not clearly beaten it.** In the one like-for-like test, Demucs followed by ADTOF scored 0.89 against 0.87 for ADTOF alone on MDB. In another paper, ADTOF on the mix scored 0.795 (MDB) and 0.709 (ENST) overall, against 0.707 and 0.640 for a separate-then-detect pipeline and 0.613 and 0.493 for a LarsNet-based one; separation won only on kick and snare ([2608.01093](https://arxiv.org/abs/2608.01093)). That paper has no control running one detector on both inputs.
3. **Machine-separated drums are close to real stems.** Transcribing `htdemucs_ft` output agreed with transcribing the true stem at F1 0.92 ([STAR Drums](https://transactions.ismir.net/articles/10.5334/tismir.244), *unverified wording*). A player's own stems would buy little over what ChartGen can make.
4. **A working system does it.** AutoDrums takes a mixed file and reports lane F1 0.845 within 50 ms.

The evidence is thin (small test sets, one direct comparison), so M3 repeats the experiment on our songs with three inputs to the same transcriber: the mix, Demucs-separated drums, and the true drum stems. Its decision rules:

- **Floor.** If the mix alone scores below F1 0.70 on five classes within 50 ms, MP3-only is not yet good enough and this verdict is reopened.
- **Stems.** If true stems beat separated drums by more than 0.05, asking for stems would help, and the verdict is reopened.
- **Critical path.** If separated drums beat the mix by less than 0.02, transcription does not need separation and the fast configuration becomes the default.

Separation still runs for three reasons that have nothing to do with requiring stems: it produces `drums.ogg` so a miss mutes the drums, it exposes tom pitch and cymbal ring time for lane mapping, and the mix-minus-drums signal reveals guitar and vocal bleed that would otherwise read as snare. A `--stems drums=file.wav` option accepts real stems when a player has them.

## 5. Layout, CLI, interfaces

```
~/Projects/Python/ChartGen/        standalone git repo; licence GPL-3.0 to match the game (confirm)
  README.md  pyproject.toml  uv.lock  flake.nix  .gitignore
  splits.json                      frozen train/dev/test folder names, committed
  src/chartgen/
    cli.py  pipeline.py  types.py
    audio/        decode, resample, Vorbis encode
    separate/     demucs, given (player stems), none
    transcribe/   drums_adtof, ...        keyed by instrument
    describe/     drums: pitch, ring time, bleed per onset
    beats/        beat_this, repair
    tempo/        fit
    chart/        quantize, drums_lanes, reduce, playability   keyed by instrument
    write/        midi, song_ini, folder
    game/         reader that mirrors Drumsmith's ParseMidi; NoteData.txt reader; judge
    eval/         dataset, metrics, report, ab
  tests/
  data/  models/  runs/  cache/    all gitignored
```

- **Environment.** The machine is NixOS without nix-ld and its system Python is 3.14. `flake.nix` provides Python 3.12, uv, ffmpeg and the library path the wheels need (including the NVIDIA driver path for CUDA); uv installs into `.venv` using that Python.
- **Drumsmith location.** `CHARTGEN_DRUMSMITH` points at the game checkout, for the DLC dataset and for installing songs.
- **Provenance.** Every generated folder carries `chartgen.json`: generator version, model hashes, settings, and warnings. The dataset loader skips any folder that has one, so `--install` cannot pollute the evaluation set.

```
chartgen song.mp3 -o out_dir/          one song folder under out_dir/
chartgen song.mp3 --install            build the folder, move it into Drumsmith's Assets/DLC, run the converter
chartgen eval --split dev              metrics report for a split
chartgen ab make | reveal              blind A/B folders
  --stems drums=FILE   --no-separate   --difficulties x|xhme   --device cpu|cuda
```

Stage interfaces. Each stage is a function of its inputs and config, cached by content hash, exchanging plain arrays and JSON.

```
Audio      samples float32 [channels, n], sample rate
Stems      {"drums": Audio, "other": Audio, ...}
Onset      time_s, class, strength 0..1, velocity or none, features {pitch, ring time, bleed, ...}
BeatGrid   beat_times, is_downbeat, confidence
TempoMap   480 ticks/quarter, tempo events, time signatures
Chart      instrument -> difficulty -> notes (tick, lane, flags: tom, ghost, accent, second pedal)

separate(mix)                           -> Stems
detect_kit(mix, stems)                  -> present or not, with a score    ("no drums found")
transcribe[instrument](mix, stems)      -> onsets
describe[instrument](onsets, mix, stems)-> onsets with features
track_beats(mix, stems)                 -> BeatGrid
fit_tempo(beats, onsets)                -> TempoMap
chart[instrument](onsets, beats, map)   -> Chart
write(chart, map, audio, stems, meta)   -> song folder
```

The drum class list is a superset (kick, snare, closed/open/pedal hi-hat, three toms, ride, crash) so a finer Phase 2 transcriber needs no interface change; ADTOF's coarser classes pass through the lane mapper.

**Other instruments.** `transcribe`, `describe` and `chart` are keyed by instrument and the writer takes any number of `PART` tracks, so bass or guitar is a new set of modules. Demucs' six-stem model supplies the stems, and [Basic Pitch](https://github.com/spotify/basic-pitch) (Apache-2.0, about 17 K parameters, ships as ONNX) is the obvious note detector. STRUM's results set expectations: bass 0.69, guitar 0.65, vocals 0.54 against drums at 0.84. The game has no gameplay for those instruments, so none of this is scheduled.

## 6. Evaluation

**Data.** The 124 paired songs, split by song with every artist kept inside one split (16 artists account for 53 songs). Near-duplicates are merged first: two Boston entries share a recording and one artist appears under two spellings. The split is 20 test, 24 dev, 80 train, frozen in `splits.json`. The 20 test songs all have real-kit labels and are never used for tuning; thresholds, the timing-offset correction and the playability percentiles come from train and dev only.

**Inputs per song.** An MP3 of all stems summed without the crowd track; the same pushed through a limiter and a low-bitrate encode, since game stems are cleaner than a commercial master; a lossless copy; and the true drum stem. Drumless versions (the non-drum stems summed) are the negatives for "no drums found".

**Reference.**

| View | Reference | Use |
|---|---|---|
| Real kit (primary) | Kit pieces from the animation notes, on the 99 charts that have them with tom markers | The target: what the drummer played |
| Gems | Expert notes from `NoteData.txt` on the 101 charts with tom markers, regenerated with `--convert-dlc` after the CRLF fix | Shows how far a kit-true chart departs from Rock Band habit; not a target |
| Five classes | Kick, snare, hi-hat, toms, cymbals on the same charts | Comparison with published numbers |
| Kick and snare, beats | All 124 songs | Charts without tom markers are usable for these only |

| Axis | Metric |
|---|---|
| Notes | F1, precision and recall per lane within 50 ms (comparable with published work and the human ceiling) and within 25 ms (`mir_eval`). |
| Timing | Median signed offset, corrected once per model and never per song. Share of matched notes inside 30 ms. |
| Audio support | Share of generated notes within 30 ms of an onset in the true drum stem. This credits real hits a human chart left out, such as ghost notes. |
| Drummer score | Replay the real part against the generated chart with the game's judging rules. Report two numbers: the Perfect/Great/Good/Miss split of the generated notes, and the share of real hits that found a note. Either alone can be gamed. |
| Tempo | Beat and downbeat F1 against the chart's beats, median beat-line error in ms, half/double-time rate, time-signature agreement. |
| Playability | Expert: only physical impossibility (more than two hand notes at once, a same-lane repeat too fast to be a real stroke); density is reported, not enforced, since it would delete real notes in fast music. Lower difficulties: the written rules (no three-limb hits on Medium, nothing paired with a kick on Easy) and rates within the range of human charts at that difficulty. |
| Reductions | The reducer is fed the human Expert chart and scored against the human Hard, Medium and Easy, so transcription errors do not leak in. |
| Subjective | Blind A/B on the 20 test songs: human and generated notes written by the same writer over identical audio, with no lyrics or authored lighting to give the label away. Pick one and rate 1–5. With one rater this is indicative, not proof. |
| Cost | Wall time per stage, CPU-only at six threads and with GPU; peak memory; model bytes. |

**Caveats.** ADTOF and STRUM were trained on community charts that may include these songs, so their scores on our DLC may flatter them; MDB Drums serves as a second, independent check. The human-versus-human ceiling of about 0.87 bounds every score against a chart.

## 7. Phase 1 milestones

| # | Milestone | Exit test |
|---|---|---|
| M0 | Create the repo and environment. Write the reader that mirrors `ParseMidi`. Confirm what each animation note means. | In the Nix shell, PyTorch sees the GPU. The reader's Expert notes match the game's `NoteData.txt` (count, and times within 1 ms) on every chart, with the three CRLF-affected charts either fixed in the game or listed as known differences. Animation notes cover the gems on the 99 real-kit charts. |
| M1 | The writer, before any model exists. Re-emit an existing chart through ChartGen's writer with audio, `song.ini` and art. | After `--convert-dlc`, the new folder's `NoteData.txt` equals the original's, notes and beats. A headless `--scene Assets/Example.lvl --play-track N --highway-autoplay-sloppy --highway-log` run reaches the results, mutes the drums on misses and reports stems in step. |
| M2 | Evaluation harness: rendered inputs, frozen splits, metrics, lints, report, and a Python copy of the game's judge. | A human chart scored against itself gives 1.0; shifted 20 ms it still gives 1.0 at ±25 ms, and shifted 30 ms it falls to near 0. The judge copy matches the game at fixed autoplay offsets. |
| M3 | Transcription baseline and the stems experiment: ADTOF on mix, on separated drums, on true stems. Optionally STRUM. | The three decision rules in §4 each return an answer on dev. Stage timings recorded at six threads. |
| M4 | Beats and tempo map, with Beat This! `final0` and `small`. | On dev, beat F1 at least 0.85 and a half/double-time rate under 10%. A generated tempo map carrying the human notes converts and draws beat lines in-game. |
| M5 | Expert charting: onset description, quantizer, lane mapping, second-pedal split, lints. Thresholds tuned on dev only. | No lint failures on dev. The share of matched notes inside 30 ms is no lower after quantizing than before. |
| M6 | First real MP3: tags with a filename fallback, cover art, `song.ogg` as mix minus drums plus `drums.ogg`, `chartgen.json`, and "no drums found". | Five of Mitch's own songs across genres convert, load and play, and a miss mutes the drums. Drumless renders of the dev songs are rejected and their full versions accepted, at least 95% each way. |
| M7 | Hard, Medium and Easy by rule, written into `notes.mid`. | On dev, note ratios within the human 10th–90th percentile and no lint failures. Can slip to Phase 2 without blocking M8, since the game cannot load them yet. |
| M8 | Baseline: the frozen pipeline on the 20 test songs in both configurations, plus the A/B session. | `BASELINE.md` with every §6 metric. Phase 1 passes if, on the real-kit view within 50 ms, overall F1 is at least 0.70, kick at least 0.80 and snare at least 0.75; at least 80% of matched notes sit inside 30 ms; and every test song converts and plays to the results screen. |

The pass bars in M4 and M8 are proposals. They can be moved once M3 gives first numbers, but not after M8 has run.

## 8. Phase 2 outline

**Goal.** Charts that follow the real drum part closely enough to teach it, produced by small models that run in the game.

**Data.** The real-kit charts supply labels for open and closed hi-hat, ride, crash, toms and soft snare. E-GMD and STAR Drums supply velocity for ghosts and accents, which our charts almost entirely lack.

**Order of work.**

1. **Reimplement ADTOF's network** in ChartGen's own code and load the original weights. This removes the dependency on the unlicensed port and is needed before anything ships.
2. **Verifier and typing.** A small tree model per drum that keeps or rejects candidates and types cymbals, as AutoDrums does. It is the cheapest gain and trains on our songs in minutes.
3. **Transcriber.** Fine-tune the network to the real-kit classes with a velocity output, fed the mix and, when available, the separated drums. In parallel, train the same network on STAR Drums and E-GMD only, as the fully free candidate, and measure the gap. The network is about a million parameters, small for the RTX 4090 on hand; the first run sets the real cost.
4. **Reductions.** A learned keep/drop/move model, kept only if it beats the M7 rules.
5. **Invented parts** for songs with no drum kit: a part built from the beat grid and the mix's low, mid and high onsets. Design deferred until the rest works.

**Targets on the 20 test songs** (provisional; fixed once `BASELINE.md` exists). Phase 2 must beat the baseline on every row.

| Axis | Target |
|---|---|
| Real-kit F1 within 50 ms | Baseline + 0.05, aiming at 0.80 against a human ceiling near 0.87 |
| Open/closed hi-hat and ride/crash, on matched notes | 0.85 or better |
| Matched notes inside 30 ms | 90% or more |
| Drummer score | 90% of generated notes judged Good or better, and 90% of real hits finding a note |
| Playability | No hard failures at any difficulty |
| Blind A/B | Reported; the generated chart should not lose every pair |
| Runtime and size | The §3.7 budgets |

**Into the game.**

1. Export to ONNX with spectrograms inside the graph; run Python on ONNX Runtime and NumPy only.
2. Port the glue, onset descriptors and charting rules to C++ in the game, checked against the golden files.
3. Add ONNX Runtime as a prebuilt third-party library in `Game.sharpmake.cs`, as rtmidi and midifile are, behind a feature flag that is off on UWP.
4. Decode with FMOD or a single-header decoder. Encode Vorbis, or let `AudioPack` accept WAV or FLAC stems.
5. Decide the output path. Writing `notes.mid` and running the existing converter keeps one format. Writing `TrackData.txt` and `NoteData.txt` directly skips the converter and already carries open hi-hat, second crash, strokes and full velocity, but a later `--convert-dlc` would overwrite it from the poorer `notes.mid` (§9, open question 2).
6. Run on a worker thread with progress in an RmlUi page. The game has no file-drop or file-dialog support today; that is engine work.
7. Download models on first use, each with its licence notice.

## 9. Risks and open questions

**Licensing**

1. **Releasing weights trained on our DLC.** The charts and recordings are third-party. Until Mitch decides, every checkpoint records what it was trained on, and nothing DLC-trained is published.
2. **ADTOF's share-alike term.** Anything derived from its weights is CC BY-NC-SA: fine for a free game, but not free software, and a commercial fork must drop it.
3. **Separation in the game.** Demucs weights have no licence, and the game can only use them as an ONNX export that someone hosts. The transcriber is therefore designed to work on the mix alone, with separation as an optional extra.
4. **ChartGen's own licence.** GPL-3.0 matches the game and lets the C++ port move across; confirm.

**Technical**

5. **Cymbals and bleed.** Crash versus ride, quiet hi-hats, buried toms and phantom snares from guitar or vocals are the known failure modes of every existing system. Dense and distorted music is worst.
6. **Scores may flatter real use.** ADTOF may have seen our songs in training, and summed game stems are cleaner than a commercial master.
7. **A wrong chart teaches a wrong part.** `chartgen.json` records per-song confidence so the game can tell the player when a chart may be rough.
8. **MP3 decoders disagree about leading padding** by tens of milliseconds. ChartGen decodes once and writes that exact audio as `song.ogg`; the game never plays the source file.
9. **The converter is brittle.** A CRLF `song.ini` reads as empty on Linux and macOS, so three existing charts are read as all toms; a missing year throws uncaught at startup; missing art asserts. ChartGen writes compliant files, and the bugs are filed separately.
10. **Environment.** NixOS without nix-ld needs the flake to supply libraries for Python wheels; proven only when M0 passes.

**Open questions for Mitch**

1. May Drumsmith host an ONNX export of the Demucs weights, as other free projects do, or must separation stay out of the shipped game? Without it there is no miss-muting on player songs and cymbal typing is weaker.
2. How should open hi-hat, a second crash and soft snare reach gameplay? The converter already parses animation notes 24–51 for the stage drummer (`VenueData::m_drumHits`), though not the open hi-hat marker. Routing them into the notes would enrich 99 existing charts at once and give ChartGen a standard place to write the same detail. The alternative is for ChartGen to write `NoteData.txt` itself. Worth deciding before Phase 2.
3. Should weights trained on the DLC ever be published (risk 1)?
4. When do difficulties arrive in the game? They need the converter and `NoteData.txt` to keep more than Expert. Until then M7's output is checked by metrics only.
5. Is an Intel-Mac build required? Current ONNX Runtime has none and needs macOS 14.
6. Generated songs land in no library filter, because the converter writes an empty source tag. Should they get one?

## 10. Sources

**Game:** `Docs/Songs-and-DLC.md`, `Docs/Gameplay-Note-Highway.md`, `Docs/Audio.md`, `Docs/MIDI-and-Pads.md`; `Game/Source/CoreGame/CustomTrackDefineTest.cpp`, `TrackList.cpp`, `AudioPack.cpp`; the 129 `Assets/DLC/*/notes.mid` files.

**Separation:** [Demucs README](https://github.com/adefossez/demucs) · [HT Demucs paper](https://arxiv.org/abs/2211.08553) · [SCNet](https://arxiv.org/abs/2401.13276) · [ZFTurbo model list](https://github.com/ZFTurbo/Music-Source-Separation-Training/blob/main/docs/pretrained_models.md) · [MVSEP leaderboard](https://mvsep.com/quality_checker/multisong_leaderboard?sort=drums) · [demucs.cpp timings](https://github.com/sevagh/demucs.cpp/blob/main/.github/PERFORMANCE.md) · [demucs.onnx](https://github.com/sevagh/demucs.onnx) · [Mixxx ONNX export](https://mixxx.org/news/2025-10-27-gsoc2025-demucs-to-onnx-dhunstack/) · [Beyond SDR](https://arxiv.org/abs/2609.04224) · [MUSDB18 terms](https://sigsep.github.io/datasets/musdb.html)

**Transcription and data:** [ADTOF](https://github.com/MZehren/ADTOF) · [ADTOF-pytorch](https://github.com/xavriley/ADTOF-pytorch) · [Zehren et al., ISMIR 2024](https://zenodo.org/records/14877515) · [Zehren 2024, synthetic-to-real](https://arxiv.org/abs/2407.19823) · [ADTOF datasets](https://zenodo.org/records/10084511) · [Separate-and-Detect](https://arxiv.org/abs/2608.01093) · [ADT via drum stem separation](https://arxiv.org/abs/2509.24853) · [STAR Drums](https://transactions.ismir.net/articles/10.5334/tismir.244) · [Noise-to-Notes](https://arxiv.org/abs/2509.21739) · [YourMT3+](https://arxiv.org/abs/2407.04822) · [MuScriptor](https://arxiv.org/abs/2607.08168) · [E-GMD](https://magenta.tensorflow.org/datasets/e-gmd) · [StemGMD](https://zenodo.org/records/7860223) · [Slakh2100](https://zenodo.org/records/4599666) · [MDB Drums](https://github.com/CarlSouthall/MDBDrums)

**Beats:** [Beat This!](https://github.com/CPJKU/beat_this) · [paper](https://arxiv.org/abs/2407.21658) · [C++ port](https://github.com/mosynthkey/beat_this_cpp) · [madmom licence](https://github.com/CPJKU/madmom/blob/main/LICENSE) · [BeatNet](https://github.com/mjhydri/BeatNet) · [All-In-One](https://github.com/mir-aidj/all-in-one)

**Charting and prior art:** [RBN Drum Authoring](http://docs.c3universe.com/rbndocs/index.php?title=Drum_Authoring) · [RBN Mix and MIDI Setup](http://docs.c3universe.com/rbndocs/index.php?title=Mix_and_MIDI_Setup) · [chart format reference, drums](https://thenathannator.github.io/GuitarGame_ChartFormats/Chart-File-Formats/mid-format/Tracks/Drums) · [AutoDrums](https://github.com/CapyyC/chart) · [STRUM](https://arxiv.org/abs/2605.12135) · [CloneCharter](https://huggingface.co/thejorseman/CloneCharter) · [charter](https://github.com/Johan-ZeLearner/charter) · [Gold and Olivier 2010](https://ojs.aaai.org/index.php/AIIDE/article/view/12396) · [Dance Dance Convolution](https://arxiv.org/abs/1703.06891) · [PM2S](https://github.com/cheriell/PM2S)

**Runtime:** [ONNX Runtime releases](https://github.com/microsoft/onnxruntime/releases) · [threading guide](https://onnxruntime.ai/docs/performance/tune-performance/threading.html) · [Basic Pitch](https://github.com/spotify/basic-pitch)
