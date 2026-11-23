#!/usr/bin/env python3
"""Merges a ChartGen drum chart into somebody else's chart of the same recording, so a song that
came with guitar only gets drums and keeps everything else: the charter's tempo map, guitar and
bass parts, sections, lyrics, events and venue tracks.

    python3 Tools/Story/merge_generated_drums.py "<original chart folder>" "<ChartGen song folder>" "<output folder>"
        [--shift <seconds>] [--analyze]

The original folder is a Clone Hero song (notes.mid or notes.chart, song.ini, art). The ChartGen
folder is what `chartgen <audio>` wrote from that folder's audio (notes.mid, song.ogg, drums.ogg).
The output folder is a song folder for the game's converter (Settings > Convert Custom DLC, or
--convert-dlc): the merged notes.mid, ChartGen's stems, the original's song.ini and art.

What is merged:
  - notes.mid: every track of the original, plus ChartGen's PART DRUMS (gems of all difficulties,
    tom markers, the drummer's animation notes, the hi-hat pedal's note 102). Each drum event keeps
    its time in seconds and is written at the nearest tick of the original's tempo map.
  - A notes.chart original is turned into MIDI first (Moonscraper's conventions: PART GUITAR and
    the other five-fret parts, forced notes as HOPO / strum markers, taps and open notes as Phase
    Shift SysEx, star power 116, solos 103, [Events] as the EVENTS track, lyrics also as
    PART VOCALS with a phrase marker per phrase). The notes.chart is kept too, with the drums added
    as [ExpertDrums] ... [EasyDrums] (pro drums: cymbal flags 66-68, N 32 the second pedal, accents
    34-38, ghosts 40-44). The .chart format has no hi-hat pedal note, so the pedal is only in the
    notes.mid, which is what the game reads.

Where the chart sits against the audio: `delay` in song.ini (ms) and `Offset` in notes.chart
(seconds) both mean "the chart starts this much later than the audio". The game reads neither, so
a positive one is baked in: whole bars are put in front of the chart, at a tempo that makes them
last exactly that long. A negative one puts silence in front of the stems instead. --shift replaces
the folder's own value, and --analyze prints how well the charter's notes line up with ChartGen's
drum hits at a range of shifts, without writing anything (the right shift has the lowest number).

Needs mido (it is in ChartGen's environment: `nix develop -c uv run python ...` from
~/Projects/Python/ChartGen) and ffmpeg for a negative shift.
"""
import bisect
import json
import os
import re
import shutil
import subprocess
import sys

import mido

DIFFICULTY_BASE = {'Expert': 96, 'Hard': 84, 'Medium': 72, 'Easy': 60}
DIFFICULTY_SYSEX = {'Easy': 0, 'Medium': 1, 'Hard': 2, 'Expert': 3}
# notes.chart instrument -> the MIDI track it becomes. Six-fret parts are left out.
CHART_PARTS = {'Single': 'PART GUITAR', 'DoubleGuitar': 'PART GUITAR COOP', 'DoubleBass': 'PART BASS', 'DoubleRhythm': 'PART RHYTHM', 'Keyboard': 'PART KEYS'}
TOM_MARKERS = (110, 111, 112)
HAT_OPEN = 25
PEDAL_OFFSET = 6  # ChartGen's hi-hat pedal: six above a difficulty's kick
SECOND_PEDAL = 95
STEMS = ('song.ogg', 'drums.ogg')


class Tempo:
    """Ticks <-> seconds for a list of (tick, microseconds per quarter note)."""

    def __init__(self, tempos, resolution):
        self.res = resolution
        tempos = sorted(tempos, key=lambda item: item[0])  # stable: file order within a tick
        if not tempos or tempos[0][0] != 0:
            tempos.insert(0, (0, 500000))
        # Of several tempos at one tick the last one written governs (ChartGen writes the song's
        # BPM first and the lead-in's real tempo after it, both at tick 0).
        merged = []
        for tick, us in tempos:
            if merged and merged[-1][0] == tick:
                merged[-1] = (tick, us)
            else:
                merged.append((tick, us))
        self.tempos = merged
        self.marks, seconds, last_tick, last_us = [], 0.0, 0, merged[0][1]
        for tick, us in merged:
            seconds += (tick - last_tick) * last_us / 1e6 / self.res
            self.marks.append((tick, seconds, us))
            last_tick, last_us = tick, us
        self._ticks = [m[0] for m in self.marks]
        self._seconds = [m[1] for m in self.marks]

    def seconds(self, tick):
        tick0, seconds0, us = self.marks[max(0, bisect.bisect_right(self._ticks, tick) - 1)]
        return seconds0 + (tick - tick0) * us / 1e6 / self.res

    def tick(self, seconds):
        tick0, seconds0, us = self.marks[max(0, bisect.bisect_right(self._seconds, seconds) - 1)]
        return max(0, int(round(tick0 + (seconds - seconds0) * 1e6 / us * self.res)))


def absolute(track):
    """[(tick, message)] of a mido track."""
    out, tick = [], 0
    for message in track:
        tick += message.time
        out.append((tick, message))
    return out


def to_track(events):
    """A mido track from [(tick, order, message)]; note-offs sort before note-ons of one tick."""
    track, last = mido.MidiTrack(), 0
    for tick, _, message in sorted(events, key=lambda item: (item[0], item[1])):
        track.append(message.copy(time=tick - last))
        last = tick
    track.append(mido.MetaMessage('end_of_track', time=0))
    return track


def track_name(track):
    for message in track:
        if message.type == 'track_name':
            return message.name
    return ''


def tempo_of(midi):
    tempos = [(tick, message.tempo) for track in midi.tracks for tick, message in absolute(track) if message.type == 'set_tempo']
    return Tempo(tempos, midi.ticks_per_beat)


def read_ini(path):
    """song.ini as [(key, value)] in file order, keys lower-cased."""
    out = []
    if os.path.isfile(path):
        for line in open(path, encoding='utf-8-sig', errors='replace'):
            if '=' in line and not line.lstrip().startswith(('[', ';', '#')):
                key, value = line.split('=', 1)
                out.append((key.strip().lower(), value.strip()))
    return out


# --- notes.chart ---------------------------------------------------------------------------------

def chart_sections(text):
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


def chart_tempo(sections, resolution):
    tempos = [(int(k), int(round(6e10 / int(v.split()[1])))) for k, v in sections.get('SyncTrack', []) if v.startswith('B ')]
    return Tempo(tempos, resolution)


def chart_guitar_track(name, by_difficulty, resolution):
    """A five-fret part as MIDI. `by_difficulty` is {'Expert': [(tick, kind, a, b)], ...}."""
    events = [(0, -2, mido.MetaMessage('track_name', name=name))]
    short = max(1, resolution // 16)  # a gem that is not held
    hopo_gap = 65 * resolution // 192
    for difficulty, lines in by_difficulty.items():
        base, level = DIFFICULTY_BASE[difficulty], DIFFICULTY_SYSEX[difficulty]
        chords = {}  # tick -> {'frets': {fret: length}, 'forced': bool, 'tap': bool}
        for tick, kind, a, b in lines:
            if kind == 'N':
                chord = chords.setdefault(tick, {'frets': {}, 'forced': False, 'tap': False})
                if a in (0, 1, 2, 3, 4, 7):
                    chord['frets'][a] = max(chord['frets'].get(a, 0), b)
                elif a == 5:
                    chord['forced'] = True
                elif a == 6:
                    chord['tap'] = True
            elif kind == 'S' and a == 2:
                events.append((tick, 1, mido.Message('note_on', note=116, velocity=100)))
                events.append((tick + max(1, b), 0, mido.Message('note_off', note=116, velocity=0)))
        ticks = sorted(tick for tick, chord in chords.items() if chord['frets'])
        last_tick, last_frets = None, None
        for index, tick in enumerate(ticks):
            chord = chords[tick]
            frets = frozenset(chord['frets'])
            until = ticks[index + 1] if index + 1 < len(ticks) else None
            length = max(chord['frets'].values())
            span = length if length > 0 else short
            if until is not None:
                span = max(1, min(span, until - tick))
            for fret, fret_length in chord['frets'].items():
                held = fret_length if fret_length > 0 else short
                if until is not None:
                    held = max(1, min(held, until - tick))
                key = base + (0 if fret == 7 else fret)
                events.append((tick, 1, mido.Message('note_on', note=key, velocity=100)))
                events.append((tick + held, 0, mido.Message('note_off', note=key, velocity=0)))
            if 7 in frets:  # an open note: a green gem inside a Phase Shift "open" phrase
                events.append((tick, 0.5, mido.Message('sysex', data=[0x50, 0x53, 0, 0, level, 1, 1])))
                events.append((tick + span, -0.5, mido.Message('sysex', data=[0x50, 0x53, 0, 0, level, 1, 0])))
            if chord['tap']:
                events.append((tick, 0.5, mido.Message('sysex', data=[0x50, 0x53, 0, 0, level, 4, 1])))
                events.append((tick + span, -0.5, mido.Message('sysex', data=[0x50, 0x53, 0, 0, level, 4, 0])))
            elif chord['forced']:
                # notes.chart flips the natural strum / HOPO; MIDI names the result.
                natural = last_tick is not None and tick - last_tick <= hopo_gap and len(frets) == 1 and frets != last_frets
                marker = base + (6 if natural else 5)
                events.append((tick, 0.5, mido.Message('note_on', note=marker, velocity=100)))
                events.append((tick + span, -0.5, mido.Message('note_off', note=marker, velocity=0)))
            last_tick, last_frets = tick, frets
        # Solos: "E solo" ... "E soloend" on the Expert part.
        if difficulty == 'Expert':
            start = None
            for tick, kind, a, _ in sorted(lines):
                if kind == 'E' and a == 'solo' and start is None:
                    start = tick
                elif kind == 'E' and a == 'soloend' and start is not None:
                    events.append((start, 1, mido.Message('note_on', note=103, velocity=100)))
                    events.append((max(start + 1, tick), 0, mido.Message('note_off', note=103, velocity=0)))
                    start = None
    return to_track(events)


def chart_to_midi(sections):
    """notes.chart as a MIDI file, without drums."""
    song = dict(sections.get('Song', []))
    resolution = int(song.get('Resolution', '192'))
    midi = mido.MidiFile(type=1, ticks_per_beat=resolution, charset='utf-8')
    title = song.get('Name', 'song').strip('"').encode('ascii', 'replace').decode('ascii')
    conductor = [(0, -2, mido.MetaMessage('track_name', name=title))]
    for key, value in sections.get('SyncTrack', []):
        parts = value.split()
        if parts[0] == 'B':
            conductor.append((int(key), 0, mido.MetaMessage('set_tempo', tempo=int(round(6e10 / int(parts[1]))))))
        elif parts[0] == 'TS':
            power = int(parts[2]) if len(parts) > 2 else 2
            conductor.append((int(key), -1, mido.MetaMessage('time_signature', numerator=int(parts[1]), denominator=2 ** power, clocks_per_click=24, notated_32nd_notes_per_beat=8)))
    midi.tracks.append(to_track(conductor))

    for suffix, name in CHART_PARTS.items():
        by_difficulty = {}
        for difficulty in DIFFICULTY_BASE:
            lines = []
            for key, value in sections.get(difficulty + suffix, []):
                parts = value.split()
                if parts[0] in ('N', 'S') and len(parts) >= 3:
                    lines.append((int(key), parts[0], int(parts[1]), int(parts[2])))
                elif parts[0] == 'E' and len(parts) >= 2:
                    lines.append((int(key), 'E', parts[1].strip('"'), 0))
            if lines:
                by_difficulty[difficulty] = lines
        if by_difficulty:
            midi.tracks.append(chart_guitar_track(name, by_difficulty, resolution))

    events = [(0, -2, mido.MetaMessage('track_name', name='EVENTS'))]
    vocals = [(0, -2, mido.MetaMessage('track_name', name='PART VOCALS'))]
    lyrics, phrase = [], None
    for key, value in sections.get('Events', []):
        match = re.match(r'E\s+"(.*)"\s*$', value)
        if not match:
            continue
        tick, text = int(key), match.group(1)
        events.append((tick, 1, mido.MetaMessage('text', text='[' + text + ']')))
        if text.startswith('lyric '):
            lyrics.append(tick)
            vocals.append((tick, 1, mido.MetaMessage('lyrics', text=text[6:])))
        elif text in ('phrase_start', 'phrase_end'):
            if phrase is not None and tick > phrase:
                vocals.append((phrase, 0.5, mido.Message('note_on', note=105, velocity=100)))
                vocals.append((tick, -0.5, mido.Message('note_off', note=105, velocity=0)))
            phrase = tick if text == 'phrase_start' else None
    if phrase is not None and lyrics and lyrics[-1] >= phrase:
        vocals.append((phrase, 0.5, mido.Message('note_on', note=105, velocity=100)))
        vocals.append((lyrics[-1] + resolution, -0.5, mido.Message('note_off', note=105, velocity=0)))
    if len(events) > 1:
        midi.tracks.append(to_track(events))
    if lyrics:
        midi.tracks.append(to_track(vocals))
    return midi


# --- The drums -----------------------------------------------------------------------------------

def read_drums(midi):
    """ChartGen's PART DRUMS as (spans [(start, end, key, velocity)], texts [(tick, text)]), in its own ticks."""
    track = next((t for t in midi.tracks if track_name(t) == 'PART DRUMS'), None)
    if track is None:
        raise SystemExit('merge_generated_drums: the ChartGen folder has no PART DRUMS')
    spans, texts, held = [], [], {}
    for tick, message in absolute(track):
        if message.type == 'text':
            texts.append((tick, message.text))
        elif message.type == 'note_on' and message.velocity > 0:
            held.setdefault(message.note, []).append((tick, message.velocity))
        elif message.type in ('note_off', 'note_on') and held.get(message.note):
            start, velocity = held[message.note].pop(0)
            spans.append((start, tick, message.note, velocity))
    return sorted(spans), texts


def drums_track(spans, texts, source, target, shift):
    """PART DRUMS on the target tempo map. `shift` is seconds taken off each time first."""
    place = lambda tick: target.tick(source.seconds(tick) - shift)
    events = [(0, -2, mido.MetaMessage('track_name', name='PART DRUMS'))]
    for tick, text in texts:
        events.append((place(tick), -1, mido.MetaMessage('text', text=text)))
    gem = max(1, target.res // 8)  # a 32nd note, as ChartGen holds its gems
    by_key, merged = {}, 0
    for start, end, key, velocity in spans:
        by_key.setdefault(key, []).append((place(start), place(end), velocity))
    for key, items in by_key.items():
        items.sort()
        kept = []
        for start, end, velocity in items:
            if kept and kept[-1][0] == start:
                merged += 1  # two strokes of one piece landed on one tick
                continue
            kept.append([start, end, velocity])
        for index, (start, end, velocity) in enumerate(kept):
            if key not in TOM_MARKERS and key != HAT_OPEN:
                end = start + gem
            if index + 1 < len(kept):
                end = min(end, kept[index + 1][0])
            end = max(start + 1, end)
            events.append((start, 1, mido.Message('note_on', note=key, velocity=velocity)))
            events.append((end, 0, mido.Message('note_off', note=key, velocity=0)))
    return to_track(events), merged


def chart_drum_lines(spans, source, target, shift):
    """{'Expert': [(tick, 'N a b')]} for notes.chart, and how many pedal notes it cannot hold."""
    place = lambda tick: target.tick(source.seconds(tick) - shift)
    markers = {key: [(place(s), place(e)) for s, e, k, _ in spans if k == key] for key in TOM_MARKERS}
    under = lambda key, tick: any(start <= tick < end for start, end in markers[key])
    out, pedals = {}, 0
    for difficulty, base in DIFFICULTY_BASE.items():
        lines = set()
        for start, _, key, velocity in spans:
            tick = place(start)
            lane = key - base
            if difficulty == 'Expert' and key == SECOND_PEDAL:
                lines.add((tick, 32))
                continue
            if lane == PEDAL_OFFSET:
                pedals += difficulty == 'Expert'
                continue
            if not 0 <= lane <= 4:
                continue
            lines.add((tick, lane))
            if lane >= 2 and not under(TOM_MARKERS[lane - 2], tick):
                lines.add((tick, 64 + lane))
            if velocity >= 127:
                lines.add((tick, 34 + lane))
            elif velocity <= 1:
                lines.add((tick, 40 + lane))
        if lines:
            out[difficulty] = sorted(lines)
    return out, pedals


def add_chart_drums(text, drum_lines):
    """notes.chart with the drum sections added (any there already are replaced)."""
    newline = '\r\n' if '\r\n' in text else '\n'
    text = re.sub(r'\[(?:Expert|Hard|Medium|Easy)Drums\]\s*\{[^}]*\}\s*', '', text)
    if not text.endswith(('\n', '\r')):
        text += newline
    for difficulty in DIFFICULTY_BASE:
        if difficulty in drum_lines:
            body = ''.join(f'  {tick} = N {n} 0{newline}' for tick, n in drum_lines[difficulty])
            text += f'[{difficulty}Drums]{newline}{{{newline}{body}}}{newline}'
    return text


# --- Lining the chart up with the audio ----------------------------------------------------------

def charter_note_times(midi, tempo):
    """Seconds of every Expert gem the charter wrote, on any part but drums."""
    times = set()
    for track in midi.tracks:
        name = track_name(track)
        if not name.startswith('PART ') or name in ('PART DRUMS', 'PART VOCALS'):
            continue
        for tick, message in absolute(track):
            if message.type == 'note_on' and message.velocity > 0 and (94 <= message.note <= 102):
                times.add(round(tempo.seconds(tick), 4))
    return sorted(times)


def misfit(note_times, hit_times, shift):
    """Mean distance (ms, capped at 60) from each charter note, moved by `shift`, to the nearest drum hit."""
    if not note_times or not hit_times:
        return float('nan')
    total = 0.0
    for time in note_times:
        time += shift
        index = bisect.bisect_left(hit_times, time)
        near = min(abs(time - hit_times[j]) for j in (index - 1, index) if 0 <= j < len(hit_times))
        total += min(near, 0.06)
    return total / len(note_times) * 1000.0


def pad_front(midi, tempo, shift):
    """Put whole bars lasting `shift` seconds in front of every event. Returns the ticks added."""
    numerator = next((m.numerator for _, m in absolute(midi.tracks[0]) if m.type == 'time_signature'), 4)
    beat = tempo.tempos[0][1] / 1e6
    bars = max(1, int(round(shift / beat / numerator)))
    ticks = bars * numerator * midi.ticks_per_beat
    pad_us = int(round(shift * 1e6 / (bars * numerator)))
    for index, track in enumerate(midi.tracks):
        events = []
        for tick, message in absolute(track):
            if message.type == 'end_of_track':
                continue
            stays = tick == 0 and message.is_meta and message.type not in ('set_tempo', 'text', 'lyrics', 'marker', 'cue_marker')
            events.append((tick if stays else tick + ticks, 0 if message.type in ('note_off',) else 1, message))
        if index == 0:
            events.append((0, -1, mido.MetaMessage('set_tempo', tempo=pad_us)))
        rebuilt = mido.MidiTrack()
        last = 0
        for tick, _, message in sorted(events, key=lambda item: item[0]):  # stable: file order within a tick
            rebuilt.append(message.copy(time=tick - last))
            last = tick
        rebuilt.append(mido.MetaMessage('end_of_track', time=0))
        midi.tracks[index] = rebuilt
    return ticks


def main_tempo(tempo, end_tick):
    """The tempo (microseconds per quarter note) the song spends the most time at, to the nearest BPM."""
    spent = {}
    for index, (tick, us) in enumerate(tempo.tempos):
        until = tempo.tempos[index + 1][0] if index + 1 < len(tempo.tempos) else max(end_tick, tick)
        seconds = (until - tick) * us / 1e6 / tempo.res
        total, weighted = spent.get(round(6e7 / us), (0.0, 0.0))
        spent[round(6e7 / us)] = (total + seconds, weighted + seconds * us)
    total, weighted = max(spent.values())
    return int(round(weighted / total)) if total else tempo.tempos[0][1]


def pad_audio(source, target, seconds):
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', source, '-af', f'adelay={int(round(seconds * 1000))}:all=1', '-c:a', 'libvorbis', '-q:a', '6', target], check=True)


def main(argv):
    args, analyze, shift_arg = [], False, None
    index = 0
    while index < len(argv):
        if argv[index] == '--analyze':
            analyze = True
        elif argv[index] == '--shift' and index + 1 < len(argv):
            index += 1
            shift_arg = float(argv[index])
        else:
            args.append(argv[index])
        index += 1
    if len(args) < 2 or (len(args) < 3 and not analyze):
        print(__doc__)
        return 2
    original, generated = args[0], args[1]
    output = args[2] if len(args) > 2 else None

    ini = read_ini(os.path.join(original, 'song.ini'))
    ini_map = dict(ini)
    chart_path, midi_path = os.path.join(original, 'notes.chart'), os.path.join(original, 'notes.mid')
    chart_text = sections = None
    if os.path.isfile(midi_path):
        midi = mido.MidiFile(midi_path, clip=True)
        shift = float(ini_map.get('delay', '0') or 0) / 1000.0
    elif os.path.isfile(chart_path):
        chart_text = open(chart_path, encoding='utf-8-sig', errors='replace', newline='').read()
        sections = chart_sections(chart_text)
        midi = chart_to_midi(sections)
        shift = float(dict(sections.get('Song', [])).get('Offset', '0') or 0) + float(ini_map.get('delay', '0') or 0) / 1000.0
    else:
        raise SystemExit('merge_generated_drums: the original folder has neither notes.mid nor notes.chart')
    if any(track_name(track) == 'PART DRUMS' for track in midi.tracks):
        raise SystemExit('merge_generated_drums: the original already has a PART DRUMS track')
    if shift_arg is not None:
        shift = shift_arg

    drums_midi = mido.MidiFile(os.path.join(generated, 'notes.mid'), clip=True)
    source = tempo_of(drums_midi)
    spans, texts = read_drums(drums_midi)
    hits = sorted({round(source.seconds(start), 4) for start, _, key, _ in spans if 95 <= key <= 102})
    target = tempo_of(midi)
    notes = charter_note_times(midi, target)
    name = os.path.basename(os.path.normpath(generated))
    here = misfit(notes, hits, shift)
    if analyze:
        candidates = sorted({round(c + d, 3) for c in {0.0, shift, -shift} for d in [x / 100.0 for x in range(-8, 9)]})
        scored = [(misfit(notes, hits, c), c) for c in candidates]
        best = min(scored)
        print(f'{name}: {len(notes)} charter notes, {len(hits)} drum hits; folder says shift {shift:+.3f} s -> {here:.1f} ms; '
              f'0 -> {misfit(notes, hits, 0.0):.1f} ms; opposite {-shift:+.3f} -> {misfit(notes, hits, -shift):.1f} ms; best of the scan {best[1]:+.3f} s -> {best[0]:.1f} ms')
        return 0

    os.makedirs(output, exist_ok=False)
    audio_pad = 0.0
    pad_ticks = 0
    if shift > 0.0005:
        pad_ticks = pad_front(midi, target, shift)
        target = tempo_of(midi)
    elif shift < -0.0005:
        audio_pad = -shift
    # From here the chart's time is the audio's time, once the stems have `audio_pad` of silence in front.
    track, merged = drums_track(spans, texts, source, target, -audio_pad)
    midi.tracks.append(track)
    # Track 0 runs to the end of the song: the game stops drawing beat lines at the file's last event.
    generated_ini = dict(read_ini(os.path.join(generated, 'song.ini')))
    length = int(generated_ini.get('song_length') or ini_map.get('song_length', '0') or 0) / 1000.0 + audio_pad
    last = max(sum(m.time for m in t) for t in midi.tracks)
    end = max(last, target.tick(length + 1.0) if length else 0)
    conductor = midi.tracks[0]
    conductor[-1].time += end - sum(m.time for m in conductor)
    # The game keeps the file's first tempo event as the song's BPM (it paces the fallback light
    # show). An intro, or the bars put in front, often run at another tempo, so the tempo most of
    # the song runs at is written first at tick 0, as ChartGen does: the chart's own tick-0 tempo
    # follows it at the same tick and is the one that governs.
    main_us = main_tempo(target, end)
    if abs(6e7 / main_us - 6e7 / target.tempos[0][1]) >= 1.0:
        first = next(i for i, m in enumerate(conductor) if m.type == 'set_tempo')
        conductor.insert(first, mido.MetaMessage('set_tempo', tempo=main_us, time=conductor[first].time))
        conductor[first + 1].time = 0
    midi.save(os.path.join(output, 'notes.mid'))

    pedals = 0
    if chart_text is not None:
        # The notes.chart keeps its own Offset, so its drums go in without the shift baked in.
        own = chart_tempo(sections, int(dict(sections.get('Song', [])).get('Resolution', '192')))
        lines, pedals = chart_drum_lines(spans, source, own, shift)
        with open(os.path.join(output, 'notes.chart'), 'w', encoding='utf-8-sig', newline='') as f:
            f.write(add_chart_drums(chart_text, lines))

    for stem in STEMS:
        path = os.path.join(generated, stem)
        if os.path.isfile(path):
            if audio_pad:
                pad_audio(path, os.path.join(output, stem), audio_pad)
            else:
                shutil.copy2(path, os.path.join(output, stem))
    for extra in sorted(os.listdir(original)):
        if extra.lower() in ('album.jpg', 'album.png', 'background.jpg', 'background.png'):
            shutil.copy2(os.path.join(original, extra), os.path.join(output, extra))
    if not any(os.path.isfile(os.path.join(output, n)) for n in ('album.jpg', 'album.png')) and os.path.isfile(os.path.join(generated, 'album.png')):
        shutil.copy2(os.path.join(generated, 'album.png'), os.path.join(output, 'album.png'))

    # song.ini: the original's, with the drums declared and the shift gone (it is baked in). LF line
    # ends: a CRLF song.ini crashes a fresh conversion on Linux (ME-357).
    replaced = {'pro_drums': 'True', 'delay': '0'}
    # The length is the stems' own (ChartGen measured it): the game takes the song's duration from it.
    generated_length = generated_ini.get('song_length', '')
    stem_length = int(generated_length) + int(round(audio_pad * 1000)) if generated_length.isdigit() else 0
    if stem_length:
        replaced['song_length'] = str(stem_length)
    lines_out, seen = ['[song]'], set()
    for key, value in ini:
        if key in replaced:
            value = replaced[key]
        elif key == 'charter' and 'ChartGen' not in value:
            value = value + ', ChartGen (drums)'
        lines_out.append(f'{key} = {value}')
        seen.add(key)
    for key, value in replaced.items():
        if key not in seen:
            lines_out.append(f'{key} = {value}')
    with open(os.path.join(output, 'song.ini'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines_out) + '\n')

    record = {}
    provenance = os.path.join(generated, 'chartgen.json')
    if os.path.isfile(provenance):
        record = json.load(open(provenance, encoding='utf-8'))
    counts = {d: sum(1 for _, _, k, _ in spans if 0 <= k - b <= 4 or k - b == PEDAL_OFFSET or (d == 'Expert' and k == SECOND_PEDAL)) for d, b in DIFFICULTY_BASE.items()}
    merge = {
        'tool': 'Tools/Story/merge_generated_drums.py',
        'original': os.path.basename(os.path.normpath(original)),
        'original_chart': 'notes.chart' if chart_text is not None else 'notes.mid',
        'charter': ini_map.get('charter', ''),
        'shift_seconds': shift,
        'bars_added_in_front_ticks': pad_ticks,
        'silence_added_to_stems_seconds': audio_pad,
        'drum_notes': counts,
        'strokes_merged_on_one_tick': merged,
        'charter_notes_to_drum_hits_ms': None if here != here else round(here, 2),
    }
    # Not chartgen.json: `chartgen rechart` and `chartgen install --overwrite` replace folders that
    # hold one, and would write a drums-only notes.mid over the merge.
    with open(os.path.join(output, 'drums-merged.json'), 'w', encoding='utf-8') as f:
        json.dump({'merge': merge, 'chartgen': record}, f, indent=1, default=float)
        f.write('\n')

    tracks = ', '.join(track_name(t) or '(tempo)' for t in midi.tracks)
    print(f'{name}: {counts["Expert"]} Expert drum notes onto {merge["original_chart"]} by {merge["charter"]}; shift {shift:+.3f} s'
          + (f' (bars in front: {pad_ticks} ticks)' if pad_ticks else '') + (f' (silence in front of the stems: {audio_pad:.3f} s)' if audio_pad else '')
          + f'; charter notes to drum hits {here:.1f} ms; {merged} strokes merged'
          + (f'; {pedals} pedal notes not in notes.chart' if pedals else '') + f'; tracks: {tracks}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
