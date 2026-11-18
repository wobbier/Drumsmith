# Practice

> Verified against the working tree on 2026-11-18 (game commit 35983a4 plus the uncommitted lesson-song links). Engine submodule at f401189d.

The practice page and its lessons: rudiments and grooves played on the note highway over a click, at a tempo the player chooses.

## Overview

A lesson is a short pattern in a data file. Starting one turns it into an ordinary chart (`TrackData`) in memory and writes a click track for its tempo as a WAV; the highway then plays that chart over that "song" exactly as it plays a library song. Nothing in `NoteHighwayCore` knows about lessons beyond three small switches (below), so the clock, judging, pause, the latency settings and the results all behave as in a song.

## Key Files

| Path | Role |
|------|------|
| `Assets/Practice/Lessons.json` | The lessons |
| `Game/Source/CoreGame/Practice.h/.cpp` | `PracticeLesson`, the `Practice` singleton: loading, `BuildChart`, `WriteClickTrack`, the session |
| `Game/Source/Components/PracticeMenuController.h/.cpp` | The practice page's controller |
| `Assets/Practice.lvl`, `Assets/UI/Practice.rml`, `Assets/UI/Practice.rcss` | The page |
| `Game/Tests/Source/GameHelperTests.cpp` | Chart building: paradiddle, flams, a groove |
| `Game/Tests/Source/PlayerProfileTests.cpp` | Passing a lesson, and the profile's records |
| `Game/Source/CoreGame/LessonPatterns.h/.cpp` | Which songs play which lesson: the matcher and `LessonPatternIndex` |
| `Game/Tests/Source/LessonPatternsTests.cpp` | The matcher on made-up charts, and a song opening a lesson |
| `Tools/Patterns/lesson_patterns.py` | The matcher's Python prototype, for looking over a whole library from the command line |

## How It Works

### Lessons

`Assets/Practice/Lessons.json` is `{ "Lessons": [ ... ] }`. Each lesson has `Id` (the tempo last used is remembered under it), `Name`, `Category` (the list's headings: Rudiments, Grooves, Fills), `Description`, `Bpm` (where a first-timer starts), `StepsPerBeat` (2 eighths, 3 triplets, 4 sixteenths; default 4), `BeatsPerBar` (default 4), and one of:

- **`Sticking`** (a rudiment, on `Pad`, default `snare1`): one hand per step. `R` / `L` a stroke, `r` / `l` a quiet tap (velocity 30: a ghost gem), `>` before a letter an accent (velocity 127), `^` before a letter a flam (a tap from the other hand 35 ms ahead of it), `-` a rest. Spaces are only for reading: `">Rlrr >Lrll"` is a paradiddle.
- **`Lanes`** (a groove): lane name to steps, `x` a stroke, `X` an accent, `o` a ghost, `-` a rest: `{ "closed_hh": "xxxx xxxx", "snare1": "--x- --x-", "bass1": "x--- x---" }`. Lane names are the chart's (`PadUtils::GetPadId`, `Docs/MIDI-and-Pads.md`). A lane that isn't a pad is dropped with a warning.

A pattern is rounded up to whole bars and repeats. A lesson with no name or no notes is skipped.

### The session

`Practice::Begin( lesson, bpm, bars )`:

1. `BuildChart`: one bar with no notes (the count-in), then `bars` bars of the pattern, as `NoteData` at `beat * 60 / bpm` seconds; a beat grid for the whole length (`BeatGrid::Generate`); `m_practice = true`. For a rudiment the sticking is written as the chart's lyrics, a syllable per stroke and a phrase per bar, so the HUD's karaoke line shows `R l r r L r l l` and lights each hand as it plays (`Lyrics`, `Docs/Venue-and-Band.md`).
2. `WriteClickTrack` (through `ClickTrack::Write`, `CoreGame/ClickTrack.h`): a 44.1 kHz mono WAV with a 30 ms click on every beat, higher on each bar's first, each click starting on its beat's own sample. Files go to `.tmp/Practice/click_<bpm>bpm_<beats>beats_<seconds>s.wav` and are reused: the same name always holds the same clicks.
3. The chart's `m_trackSourcePath` points at that file, so `AudioPack` loads it as the song's one stem and the highway's clock locks to it.

`PracticeMenuController::StartLesson` then loads `Assets/Example.lvl` and fires `LaunchPlayTrackEvent` with `TrackID = Practice::kTrackId`; `NoteHighwayCore` plays `Practice::Chart()` for that id.

### What the highway does differently

- `SetupTrack` doesn't call `LoadNoteData` for a chart with `m_practice` (its notes are already in memory) and builds the lyric line whatever the Lyrics setting says.
- `VenueShow::Build` builds nothing for a practice chart: no stage, band or crowd.
- The `in_game` model's `practice` value sends Retry back into the same session, and Exit, Escape on the results and the results' button to `Assets/Practice.lvl`.

The results' *Average timing* line (every song has it) says how far ahead of or behind the beat the hits were on average.

### Passing

A lesson passes at `PassAccuracy` percent (default 90) or better, at `PassBpm` or faster (0, or left out, means the lesson's `Bpm`): `PracticeLesson::Passes`. Every lesson in `Lessons.json` sets a `PassBpm` 10 to 30 BPM above where it starts. A finished lesson is recorded in `PlayerProfile` (`Docs/Game-Architecture.md` → Player profile): its best accuracy, the fastest tempo played at the pass accuracy, and whether it has passed. The results screen says *Lesson passed!* the first time, and until then what passing takes.

### The page

`Docs/UI-and-Menus.md` → Practice. Tempo is 40 to 220 BPM (`Practice::kMinBpm` / `kMaxBpm`), remembered per lesson in `GameSettings::PracticeTempos`; length is 8, 16 or 32 bars.

### Songs that use a lesson

`LessonPatterns::Find` looks for each lesson in a chart. It puts the chart's notes on the chart's own beat grid at the lesson's subdivision (a note more than 0.22 of a step off the grid spoils its beat), then goes bar by bar:
- **A groove** (`Lanes`) matches a bar when, on its lanes plus the kick and the snare, every step has exactly its strokes. Accents and ghosts count as strokes.
- **A rudiment** (`Sticking`) can only match by rhythm, because a chart says which drum and not which hand. The hand drums (the snare and the toms) must hit exactly the steps the sticking strokes, tiled over the bar, with no cymbal on a rest. Singles, doubles and the paradiddle are all "every sixteenth", so they find the same bars. Flams aren't charted, so the flam lessons find nothing.

A one-bar pattern needs two matched bars in a row to make a section.

`LessonPatternIndex` runs it over the library on a worker thread, once a session, from each song's `NoteData.txt`. The practice page and the hideout start it; it takes a second or two for a hundred songs. `Poll` (main thread) takes the results. The practice page then lists up to six songs under each lesson, *Songs with this groove* or *Songs with its rhythm*: each with its bars and where the longest run starts, and a PLAY that launches the song (`TrackRadioUtils::LaunchTrack`).

The grooves a song plays (at least two bars, not rhythm-only) go to `Progression::SongLessons`. `Progression::Evaluate` then opens such a lesson for a player who has finished the song (`lesson:<id>`, "New lesson: Rock beat (you played it in Enter Sandman)"), whatever the ladder says. A locked groove's song list says so. On the development library (2026-11-18) it found 25 songs that play a lesson, and 12 song and groove pairs that can open one (`[Patterns]` in the log).

## How to Extend

**Add a lesson:** add an entry to `Assets/Practice/Lessons.json`. No code. `--practice <index> --practice-bpm <bpm> --highway-autoplay` under `Engine/Tools/Headless.sh` plays it without a kit.
Add `--record-autoplay` to record that run in `Profile.json` (and back up or delete a real profile first).

**Add a notation mark:** `PatternSteps` in `Practice.cpp` reads both notations into `Step`s.

## Caveats & Fragility

- **The highway doesn't show which hand.** Sticking is only the lyric line; gems look the same for both hands, and nothing judges which hand played. The songs that use a lesson don't show its sticking on their highway either (only the practice session does).
- **A song's rudiments are guesses by rhythm**, so they never open a lesson; grooves match exactly but only as written (a groove with one extra kick doesn't count).
- **Lowercase `l` reads like `I`** in the HUD font.
- **The click is the only sound.** There are no hit sounds (`Docs/Audio.md`), so the player hears their own kit against the click.
- **Click files accumulate** under `.tmp/Practice/` (about 90 KB a second of lesson), one per tempo and length used.
- **A flam is two notes in one lane 35 ms apart**, judged like any two notes; a single hit takes the closer one and the other is a miss.
- **Passing is judged on accuracy and tempo only**: the length (8, 16 or 32 bars) doesn't matter, and nothing on the practice page shows a lesson's results yet.

## Related Docs

- `Docs/Gameplay-Note-Highway.md`: the highway, judging, results
- `Docs/UI-and-Menus.md`: the page and its controller
- `Docs/Audio.md`: `AudioPack`, which plays the click track
