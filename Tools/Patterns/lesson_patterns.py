#!/usr/bin/env python3
"""Prototype (Docs/Hideout-and-Progression.md, Phase 4): which songs play which practice lesson.

    python3 Tools/Patterns/lesson_patterns.py [--json out.json] [--song "<folder substring>"]

Reads Assets/Practice/Lessons.json and every Assets/DLC/*/NoteData.txt, puts each chart's notes on
its own beat grid at the lesson's subdivision, and looks for the lesson's pattern bar by bar:

  * A groove (Lanes) matches a bar when, on the lesson's lanes plus the kick and snare, every step
    has exactly the lesson's strokes (accents and ghosts count as strokes). Two bars in a row make
    a section.
  * A rudiment (Sticking) can only be matched by rhythm: a chart says which drum, not which hand.
    It matches a bar whose hand drums (snare and toms together) hit exactly the steps the sticking
    strokes, tiled over the bar, with no cymbal on a step it doesn't. Singles, doubles and the
    paradiddle are all "every sixteenth", so they find the same bars; flams aren't charted, so the
    flam lessons find nothing.

Prints, per lesson, how many songs have it and the first few; --json writes every section found.
Stdlib only, read-only.
"""
import argparse
import bisect
import glob
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HANDS = {"snare1", "tom1", "tom2", "tom3"}
CYMBALS = {"closed_hh", "open_hh", "ride1", "crash1", "crash2"}
TOLERANCE = 0.22   # of a step: further off the grid than this and the note isn't on it


def steps_of(text):
    """A lane's or sticking's steps: True for a stroke. Spaces are for reading; ^ (flam) and >
    (accent) mark the next stroke."""
    out = []
    for c in text:
        if c in " ^>":
            continue
        out.append(c not in "-")
    return out


class Grid:
    def __init__(self, beats, notes, steps_per_beat):
        self.times = [b[0] for b in beats]
        self.downbeats = [i for i, b in enumerate(beats) if b[1] == 1]
        self.s = steps_per_beat
        # (beat index, step) -> lanes
        self.cells = {}
        self.off = set()
        for n in notes:
            t = n["TriggerTime"]
            i = bisect.bisect_right(self.times, t) - 1
            if i < 0 or i + 1 >= len(self.times):
                continue
            span = self.times[i + 1] - self.times[i]
            if span <= 0:
                continue
            pos = (t - self.times[i]) / span * self.s
            step = int(round(pos))
            if abs(pos - step) > TOLERANCE:
                self.off.add(i)
                continue
            if step == self.s:
                i, step = i + 1, 0
            self.cells.setdefault((i, step), set()).add(n["NoteName"])

    def bars(self, beats_per_bar):
        """Each bar of beats_per_bar beats: its first beat index."""
        for a, b in zip(self.downbeats, self.downbeats[1:]):
            if b - a == beats_per_bar:
                yield a

    def bar_cells(self, first_beat, beats):
        return [self.cells.get((first_beat + k // self.s, k % self.s), set()) for k in range(beats * self.s)]

    def clean(self, first_beat, beats):
        return not any(first_beat + k in self.off for k in range(beats))


def groove_bars(grid, lesson):
    lanes = {lane: steps_of(steps) for lane, steps in lesson["Lanes"].items()}
    length = max(len(v) for v in lanes.values())
    beats_per_bar = lesson.get("BeatsPerBar", 4)
    bar_steps = beats_per_bar * grid.s
    bars = max(1, -(-length // bar_steps))
    want = []
    for k in range(bars * bar_steps):
        want.append({lane for lane, steps in lanes.items() if steps and steps[k % len(steps)]})
    watched = set(lanes) | {"snare1", "bass1"}
    hits = []
    for first in grid.bars(beats_per_bar):
        if not grid.clean(first, beats_per_bar * bars):
            continue
        got = grid.bar_cells(first, beats_per_bar * bars)
        if all((cell & watched) == w for cell, w in zip(got, want)):
            hits.append(first)
    return hits, bars


def rudiment_bars(grid, lesson):
    strokes = steps_of(lesson["Sticking"])
    if "^" in lesson["Sticking"] or not strokes:
        return [], 1
    beats_per_bar = lesson.get("BeatsPerBar", 4)
    bar_steps = beats_per_bar * grid.s
    want = [strokes[k % len(strokes)] for k in range(bar_steps)]
    hits = []
    for first in grid.bars(beats_per_bar):
        if not grid.clean(first, beats_per_bar):
            continue
        got = grid.bar_cells(first, beats_per_bar)
        if all(bool(cell & HANDS) == w and (w or not (cell & CYMBALS)) for cell, w in zip(got, want)):
            hits.append(first)
    return hits, 1


def sections(hits, bars, beats_per_bar, need):
    """Runs of consecutive matched bars at least `need` long, as (first beat, bar count)."""
    out = []
    run = []
    step = beats_per_bar * bars
    for first in hits:
        if run and first != run[-1] + step:
            if len(run) >= need:
                out.append((run[0], len(run) * bars))
            run = []
        run.append(first)
    if len(run) >= need:
        out.append((run[0], len(run) * bars))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", help="write every section found here")
    ap.add_argument("--song", help="only songs whose folder contains this")
    args = ap.parse_args()

    lessons = json.load(open(os.path.join(ROOT, "Assets", "Practice", "Lessons.json")))["Lessons"]
    found = {l["Id"]: [] for l in lessons}
    songs = 0
    for path in sorted(glob.glob(os.path.join(ROOT, "Assets", "DLC", "*", "NoteData.txt"))):
        folder = os.path.basename(os.path.dirname(path))
        if args.song and args.song.lower() not in folder.lower():
            continue
        try:
            data = json.load(open(path))
        except (OSError, ValueError):
            continue
        beats, notes = data.get("Beats") or [], data.get("Notes") or []
        if len(beats) < 8 or not notes:
            continue
        songs += 1
        grids = {}
        for lesson in lessons:
            s = lesson.get("StepsPerBeat", 4)
            grid = grids.get(s) or grids.setdefault(s, Grid(beats, notes, s))
            if "Lanes" in lesson:
                hits, bars = groove_bars(grid, lesson)
                need = 2 if bars == 1 else 1
            else:
                hits, bars = rudiment_bars(grid, lesson)
                need = 1
            for first, count in sections(hits, bars, lesson.get("BeatsPerBar", 4), need):
                found[lesson["Id"]].append({"Song": folder, "StartMs": round(grid.times[first] * 1000),
                                            "Bars": count})

    print(f"{songs} charts")
    for lesson in lessons:
        hits = found[lesson["Id"]]
        by_song = {}
        for h in hits:
            by_song.setdefault(h["Song"], []).append(h)
        kind = "groove" if "Lanes" in lesson else "rudiment (rhythm only)"
        print(f"\n{lesson['Id']} [{kind}]: {len(by_song)} songs, {len(hits)} sections")
        for song, hs in sorted(by_song.items(), key=lambda kv: -sum(h["Bars"] for h in kv[1]))[:4]:
            bars = sum(h["Bars"] for h in hs)
            print(f"    {song}: {bars} bars, first at {hs[0]['StartMs'] / 1000:.1f} s")
    if args.json:
        with open(args.json, "w") as f:
            json.dump(found, f, indent=1)
        print("\nwrote", args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
