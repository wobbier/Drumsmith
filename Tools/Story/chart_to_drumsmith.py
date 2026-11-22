#!/usr/bin/env python3
"""Converts a Clone Hero / Moonscraper song folder (notes.chart, song.ini, Opus or Ogg stems) into a
Drumsmith song in place: TrackData.txt and NoteData.txt beside the chart, and Ogg copies of Opus
stems (FMOD here plays Ogg Vorbis, not Opus). The game's own converter (Settings > Convert Custom
DLC) reads only notes.mid (Docs/Songs-and-DLC.md).

    python3 Tools/Story/chart_to_drumsmith.py "<song folder>" [--spotify <track url>] [--offset <s>]

Drums are the [ExpertDrums] track, read as Rock Band pro drums are by the MIDI importer
(CustomTrackDefineTest::ReadMidiDrumNotes): N 0 kick (N 32 the second pedal), 1 snare, 2 yellow,
3 blue, 4 green; a yellow, blue or green gem is a tom unless N 66, 67 or 68 marks it a cymbal (the
.chart convention, the other way round from notes.mid); N 34-38 accents, N 40-44 ghosts. The
tempo map becomes the beats, "section" events the sections and "end" the song's end.

The chart's [Song] Offset (seconds) shifts every note, beat and section; --offset replaces it.
Check it against the drum stem: the first drum note should land where the stem's drums start. The main track is song.ogg, else the first of bass, rhythm or keys: the
game loads drums, guitar, vocals and rhythm stems by name (AudioPack).
"""
import json
import os
import re
import shutil
import subprocess
import sys

PADS = {  # (gem, cymbal) -> (EditorLane, NoteName)
    ('kick', False): (0, 'bass1'),
    ('red', False): (1, 'snare1'),
    ('yellow', True): (3, 'closed_hh'),
    ('yellow', False): (5, 'tom1'),
    ('blue', True): (8, 'ride1'),
    ('blue', False): (6, 'tom2'),
    ('green', True): (4, 'crash1'),
    ('green', False): (7, 'tom3'),
}
GEMS = {0: 'kick', 32: 'kick', 1: 'red', 2: 'yellow', 3: 'blue', 4: 'green'}
CYMBAL_MARKS = {66: 'yellow', 67: 'blue', 68: 'green'}


def sections_of(text):
    out, name = {}, None
    for line in text.splitlines():
        line = line.strip().lstrip('﻿')
        if line.startswith('[') and line.endswith(']'):
            name = line[1:-1]
            out[name] = []
        elif name and '=' in line and line not in ('{', '}'):
            key, value = line.split('=', 1)
            out[name].append((key.strip(), value.strip()))
    return out


def read_ini(path):
    out = {}
    if os.path.isfile(path):
        for line in open(path, encoding='utf-8-sig', errors='replace'):
            if '=' in line:
                k, v = line.split('=', 1)
                out[k.strip().lower()] = v.strip()
    return out


class TempoMap:
    def __init__(self, sync, resolution):
        self.res = resolution
        self.tempos = sorted((int(k), int(v.split()[1]) / 1000.0) for k, v in sync if v.startswith('B '))
        self.signatures = sorted((int(k), int(v.split()[1])) for k, v in sync if v.startswith('TS '))
        if not self.tempos or self.tempos[0][0] != 0:
            self.tempos.insert(0, (0, 120.0))
        self.marks = []  # (tick, seconds, bpm)
        seconds, last_tick, bpm = 0.0, 0, self.tempos[0][1]
        for tick, new_bpm in self.tempos:
            seconds += (tick - last_tick) / self.res * 60.0 / bpm
            self.marks.append((tick, seconds, new_bpm))
            last_tick, bpm = tick, new_bpm

    def seconds(self, tick):
        mark = self.marks[0]
        for m in self.marks:
            if m[0] > tick:
                break
            mark = m
        return mark[1] + (tick - mark[0]) / self.res * 60.0 / mark[2]

    def beats(self, end_tick):
        out, tick, beat_in_bar = [], 0, 0
        sig = self.signatures[0][1] if self.signatures else 4
        sig_i = 0
        while tick <= end_tick:
            while sig_i < len(self.signatures) and self.signatures[sig_i][0] <= tick:
                if self.signatures[sig_i][0] == tick:
                    beat_in_bar = 0
                sig = max(1, self.signatures[sig_i][1])
                sig_i += 1
            out.append((self.seconds(tick), beat_in_bar == 0))
            beat_in_bar = (beat_in_bar + 1) % sig
            tick += self.res
        return out


def transcode(folder):
    for name in sorted(os.listdir(folder)):
        if name.endswith('.opus'):
            target = os.path.join(folder, name[:-5] + '.ogg')
            if not os.path.exists(target):
                subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', os.path.join(folder, name), '-c:a', 'libvorbis', '-q:a', '6', target], check=True)


def duration_of(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path], capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def main(argv):
    if not argv or argv[0].startswith('-'):
        print(__doc__)
        return 2
    folder = argv[0]
    spotify = argv[argv.index('--spotify') + 1] if '--spotify' in argv else ''
    offset_arg = float(argv[argv.index('--offset') + 1]) if '--offset' in argv else None
    if not shutil.which('ffmpeg'):
        print('chart_to_drumsmith: needs ffmpeg on the PATH', file=sys.stderr)
        return 1
    chart = sections_of(open(os.path.join(folder, 'notes.chart'), encoding='utf-8-sig', errors='replace').read())
    song = dict(chart.get('Song', []))
    resolution = int(song.get('Resolution', '192'))
    offset = offset_arg if offset_arg is not None else float(song.get('Offset', '0') or 0)
    tempo = TempoMap(chart.get('SyncTrack', []), resolution)
    ini = read_ini(os.path.join(folder, 'song.ini'))

    # Drums.
    gems, cymbal_ticks, accents, ghosts = [], {g: set() for g in CYMBAL_MARKS.values()}, set(), set()
    for key, value in chart.get('ExpertDrums', []):
        parts = value.split()
        if parts[0] != 'N':
            continue
        tick, n = int(key), int(parts[1])
        if n in GEMS:
            gems.append((tick, n))
        elif n in CYMBAL_MARKS:
            cymbal_ticks[CYMBAL_MARKS[n]].add(tick)
        elif 34 <= n <= 38:
            accents.add((tick, n - 34))
        elif 40 <= n <= 44:
            ghosts.add((tick, n - 40))
    notes = []
    for tick, n in sorted(gems):
        gem = GEMS[n]
        cymbal = gem in cymbal_ticks and tick in cymbal_ticks[gem]
        lane, name = PADS[(gem, cymbal)]
        t = tempo.seconds(tick) + offset
        note = {'EditorLane': lane, 'NoteName': name, 'TriggerTime': round(t, 6), 'TriggerTimeMS': int(round(t * 1000))}
        lane_index = 0 if n in (0, 32) else n
        if (tick, lane_index) in accents:
            note['Velocity'] = 127
        elif (tick, lane_index) in ghosts:
            note['Velocity'] = 30
        if n == 32:
            note['SecondPedal'] = True
        notes.append(note)

    # Sections, the end, and the beats.
    sections, end_tick = [], 0
    for key, value in chart.get('Events', []):
        m = re.match(r'E "(.*)"', value)
        if not m:
            continue
        text, tick = m.group(1), int(key)
        if text.startswith('section '):
            sections.append([round(tempo.seconds(tick) + offset, 4), text[8:].strip()])
        elif text == 'end':
            end_tick = max(end_tick, tick)
    last_tick = max([t for t, _ in gems] + [end_tick, 0])
    beats = [[round(t + offset, 4), 1 if bar else 0] for t, bar in tempo.beats(last_tick + resolution * 4) if t + offset >= 0]
    venue = {'Sections': sections}
    if end_tick:
        venue['SongEvents'] = [[round(tempo.seconds(end_tick) + offset, 4), 'end']]

    transcode(folder)
    main_track = next((n for n in ('song.ogg', 'bass.ogg', 'rhythm.ogg', 'keys.ogg', 'guitar.ogg') if os.path.isfile(os.path.join(folder, n))), 'song.ogg')
    length = max(duration_of(os.path.join(folder, n)) for n in os.listdir(folder) if n.endswith('.ogg')) if any(n.endswith('.ogg') for n in os.listdir(folder)) else 0.0
    if not length and ini.get('song_length', '').isdigit():
        length = int(ini['song_length']) / 1000.0
    title = song.get('Name', ini.get('name', '')).strip('"')
    artist = song.get('Artist', ini.get('artist', '')).strip('"')
    art = next((n for n in ('album.png', 'album.jpg') if os.path.isfile(os.path.join(folder, n))), '')
    preview = int(ini.get('preview_start_time', '0') or 0) / 1000.0
    track = {
        'Album': song.get('Album', ini.get('album', '')).strip('"'),
        'AlbumArtFileName': art,
        'Artist': artist,
        'BPM': int(round(tempo.tempos[0][1])),
        'DLCSource': '',
        'Duration': round(length, 3),
        'Genre': song.get('Genre', ini.get('genre', '')).strip('"'),
        'Icon': ini.get('icon', ''),
        'NoteCount': len(notes),
        'NoteSpeed': 10.0,
        'PreviewPercent': preview / length if length else 0.0,
        'Title': title,
        'TrackFileName': main_track,
        'Year': int(re.sub(r'\D', '', ini.get('year', '') or song.get('Year', '')) or 0),
    }
    if spotify:
        track['Links'] = {'Spotify': spotify}
    with open(os.path.join(folder, 'TrackData.txt'), 'w', encoding='utf-8') as f:
        json.dump(track, f, indent=1, ensure_ascii=False)
    with open(os.path.join(folder, 'NoteData.txt'), 'w', encoding='utf-8') as f:
        json.dump({'Beats': beats, 'Notes': notes, 'Venue': venue}, f, indent=1)
    times = [n['TriggerTime'] for n in notes]
    print(f'{os.path.basename(folder.rstrip("/"))}: {len(notes)} notes ({min(times):.1f} s to {max(times):.1f} s), {len(sections)} sections, {len(beats)} beats, '
          f'main track {main_track}, {length:.1f} s')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
