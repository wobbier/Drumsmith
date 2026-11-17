#!/usr/bin/env python3
"""Builds a Drumsmith DLC server's catalogue (Docs/Songs-and-DLC.md).

Run it in the folder the server serves (the one holding the song folders):

    python3 DLCParser.py [root] [--output dlc_index.json]

It writes two files there:

  dlc_index.json  one entry per song folder that has a TrackData.txt
  dlc_index.hash  the SHA-256 of dlc_index.json: the game fetches this first and only
                  downloads the index again when it differs from the copy it has

Per song: the metadata the catalogue shows, the files to download with their sizes (the
game checks each download against them), and "Version", a hash of the song's files that
changes when any of them does, so installed copies can be offered an update.
"""
import argparse
import hashlib
import json
import os

IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif')
# Never served: the index itself, this script, OS droppings and dot-files (the game keeps
# its own notes in a song folder as dot-files).
SKIPPED_FILES = {'desktop.ini', 'thumbs.db', 'dlc_index.json', 'dlc_index.hash', 'dlcparser.py', 'parse_dlc.py'}


def served_files(folder):
    files = []
    for name in sorted(os.listdir(folder)):
        if name.startswith('.') or name.lower() in SKIPPED_FILES:
            continue
        if os.path.isfile(os.path.join(folder, name)):
            files.append(name)
    return files


def find_album_art(files):
    for name in files:
        if name.lower().endswith(IMAGE_EXTENSIONS):
            return name
    return None


def file_hash(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def song_version(folder, files):
    """A hash over every served file's name and contents."""
    digest = hashlib.sha256()
    for name in files:
        digest.update(name.encode('utf-8'))
        digest.update(b'\0')
        digest.update(file_hash(os.path.join(folder, name)).encode('ascii'))
        digest.update(b'\0')
    return digest.hexdigest()[:32]


def is_authored(folder):
    """Whether the chart was saved from the Track Editor (the "DS ready" badge)."""
    try:
        with open(os.path.join(folder, 'NoteData.txt'), 'r', encoding='utf-8') as handle:
            return bool(json.load(handle).get('Authored', False))
    except (OSError, ValueError):
        return False


def scan(root):
    index = []
    for subdir, dirs, _ in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.'))
        relative = os.path.relpath(subdir, root).replace(os.sep, '/')
        if relative == '.' or not os.path.isfile(os.path.join(subdir, 'TrackData.txt')):
            continue
        try:
            with open(os.path.join(subdir, 'TrackData.txt'), 'r', encoding='utf-8') as handle:
                data = json.load(handle)
        except (OSError, ValueError) as error:
            print(f'Skipping {relative}: {error}')
            continue
        files = served_files(subdir)
        index.append({
            'Album': data.get('Album'),
            'Title': data.get('Title'),
            'Artist': data.get('Artist'),
            'Year': data.get('Year', 1994),
            'Genre': data.get('Genre'),
            'DLCSource': data.get('DLCSource', 'DS'),
            'AlbumArtFileName': find_album_art(files),
            'TrackFileName': data.get('TrackFileName'),
            'PreviewPercent': data.get('PreviewPercent', 0.25),
            'NoteCount': data.get('NoteCount', 0),
            'Authored': is_authored(subdir),
            'FolderPath': relative,
            'FilesInFolder': files,
            'FileSizes': [os.path.getsize(os.path.join(subdir, name)) for name in files],
            'Version': song_version(subdir, files),
        })
    return index


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('root', nargs='?', default='.', help='the folder holding the song folders')
    parser.add_argument('--output', default=None, help='where to write the index (default: <root>/dlc_index.json)')
    args = parser.parse_args()

    output = args.output or os.path.join(args.root, 'dlc_index.json')
    index = scan(args.root)
    text = json.dumps(index, indent=4)
    with open(output, 'w', encoding='utf-8') as handle:
        handle.write(text)
    hash_path = os.path.join(os.path.dirname(output) or '.', 'dlc_index.hash')
    with open(hash_path, 'w', encoding='ascii') as handle:
        handle.write(hashlib.sha256(text.encode('utf-8')).hexdigest())
    print(f'{len(index)} songs written to {output} (hash in {hash_path})')


if __name__ == '__main__':
    main()
