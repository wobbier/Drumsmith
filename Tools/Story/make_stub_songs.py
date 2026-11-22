#!/usr/bin/env python3
"""Writes a stand-in song for every story song the library hasn't got, in Assets/DLC/Story/<Artist -
Title>/, so story mode can be played before the real charts exist (Docs/Hideout-and-Progression.md
-> Story mode).

A stand-in is a click on every beat at 120 BPM for the recording's length (song.ogg, made with
ffmpeg) and a plain rock beat over it: kick on one and three, snare on two and four, closed hi-hat
eighths, a crash every eight bars. Its TrackData.txt carries the recording's Spotify link, which is
how the story finds it. To chart the real song, put the real audio and chart in that folder (or
replace the folder) and keep the link.

The manifest's ProposedSets (sets not placed in the campaign yet, so make_story.py leaves them out
of Story.json) get stand-ins too, and so does a song's Backup.

Songs already in Assets/DLC (same artist and title) get no stand-in, and a folder that's already
there is never touched: pass --force to rewrite every stand-in.

    python3 Tools/Story/make_stub_songs.py [--force]
"""
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
MANIFEST = os.path.join(ROOT, "Design", "Story-Mode-Setlists.json")
DLC = os.path.join(ROOT, "Assets", "DLC")
STORY = os.path.join(DLC, "Story")

BPM = 120.0
LEAD_IN = 3.0  # seconds of nothing before the first note
STUB_SOURCE = "story-stub"


def match_name(text, artist):
    """As Progression's MatchName: the first artist, no "- Remastered" or "(feat. ...)", a-z0-9."""
    text = text.split(",")[0] if artist else text.split(" - ")[0].split("(")[0]
    return re.sub(r"[^a-z0-9]", "", text.lower())


def folder_name(artist, title):
    name = f"{artist.split(',')[0].strip()} - {title.split(' - ')[0].split('(')[0].strip()}"
    return re.sub(r'[<>:"/\\|?*]', "", name).strip(" .")


def library():
    """(artist, title) of every song already in Assets/DLC (and real charts in Assets/DLC/Story),
    outside the stand-ins."""
    songs = set()
    folders = [e for e in os.scandir(DLC) if e.is_dir() and e.name != "Story"]
    if os.path.isdir(STORY):
        folders += [e for e in os.scandir(STORY) if e.is_dir()]
    for entry in folders:
        data = os.path.join(entry.path, "TrackData.txt")
        if os.path.isfile(data):
            try:
                with open(data, encoding="utf-8") as f:
                    track = json.load(f)
            except (OSError, ValueError):
                continue
            if track.get("DLCSource") == STUB_SOURCE:
                continue
            artist = track.get("Artist", track.get("SongArtist", ""))
            title = track.get("Title", track.get("SongName", ""))
            songs.add((match_name(artist, True), match_name(title, False)))
    return songs


def notes(duration):
    """The rock beat, as NoteData.txt's notes."""
    out = []
    beat = 60.0 / BPM

    def note(time, name, lane):
        out.append({"EditorLane": lane, "NoteName": name, "TriggerTime": round(time, 6), "TriggerTimeMS": int(time * 1000.0)})

    eighth = 0
    time = LEAD_IN
    end = duration - 2.0
    while time < end:
        in_bar = eighth % 8
        if in_bar == 0 and (eighth // 8) % 8 == 0:
            note(time, "crash2", 9)
        else:
            note(time, "closed_hh", 3)
        if in_bar in (0, 4):
            note(time, "bass1", 0)
        if in_bar in (2, 6):
            note(time, "snare1", 1)
        eighth += 1
        time = LEAD_IN + eighth * beat / 2.0
    return out


def click(path, duration):
    """A click on every beat from the first note on: mono 22 kHz Vorbis, small."""
    beat = 60.0 / BPM
    expr = f"0.4*sin(2*PI*1500*t)*exp(-80*mod(t-{LEAD_IN}\\,{beat}))*gte(t\\,{LEAD_IN})"
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"aevalsrc={expr}:s=22050:d={duration:.3f}", "-ac", "1", "-c:a", "libvorbis", "-q:a", "0", path],
        check=True,
    )


def write_stub(folder, song, set_title, duration):
    os.makedirs(folder, exist_ok=True)
    note_list = notes(duration)
    track = {
        "Title": song["Title"],
        "Artist": song["Artist"],
        "Album": "Story mode stand-in",
        "Genre": f"Story: {set_title}",
        "Year": 0,
        "Icon": "",
        "AlbumArtFileName": "",
        "DLCSource": STUB_SOURCE,
        "NoteSpeed": 10.0,
        "Duration": float(duration),
        "BPM": BPM,
        "TrackFileName": "song.ogg",
        "PreviewPercent": 0.25,
        "Links": {"Spotify": song["Spotify"]},
        "NoteCount": len(note_list),
    }
    with open(os.path.join(folder, "TrackData.txt"), "w", encoding="utf-8") as f:
        json.dump(track, f, indent=1, ensure_ascii=False)
    with open(os.path.join(folder, "NoteData.txt"), "w", encoding="utf-8") as f:
        json.dump({"Notes": note_list}, f, indent=1)
    click(os.path.join(folder, "song.ogg"), duration)


def main():
    force = "--force" in sys.argv[1:]
    if not shutil.which("ffmpeg"):
        print("make_stub_songs: needs ffmpeg on the PATH", file=sys.stderr)
        return 1
    with open(MANIFEST, encoding="utf-8") as f:
        manifest = json.load(f)
    have = library()
    made = kept = charted = 0
    for story_set in manifest["Sets"] + manifest.get("ProposedSets", []):
        songs = story_set["Songs"] + [song["Backup"] for song in story_set["Songs"] if song.get("Backup")]
        for song in songs:
            if (match_name(song["Artist"], True), match_name(song["Title"], False)) in have:
                charted += 1
                continue
            folder = os.path.join(STORY, folder_name(song["Artist"], song["Title"]))
            if os.path.exists(folder) and not force:
                kept += 1
                continue
            write_stub(folder, song, story_set["Title"], int(song.get("DurationSeconds") or 240))
            made += 1
            print(f"  {os.path.relpath(folder, ROOT)}")
    print(f"make_stub_songs: {made} written, {kept} already there, {charted} already in the library")
    return 0


if __name__ == "__main__":
    sys.exit(main())
