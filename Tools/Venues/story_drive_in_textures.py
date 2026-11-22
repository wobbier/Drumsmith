"""The drive-in's pictures, drawn with ImageMagick 7 into Assets/Venues/StoryDriveIn/Textures/:
the model palette, the FM station card on the big screen, the marquee, the quilt, gravel and
block. Deterministic (fixed seeds, metadata stripped), so a rerun gives the same bytes.
"""
import glob
import os
import shutil
import subprocess
import sys

from story_drive_in_meshes import SWATCHES, VENUE

OUT = VENUE / 'Textures'
MAGICK = shutil.which('magick') or (sorted(glob.glob('/nix/store/*imagemagick-7*/bin/magick')) or ['magick'])[-1]
BOLD = 'DejaVu-Sans-Bold'
COND = 'DejaVu-Sans-Condensed-Bold'
MONO = 'DejaVu-Sans-Mono-Bold'
SERIF = 'DejaVu-Serif-Bold-Italic'


def magick(*args):
    cmd = [MAGICK, *[str(a) for a in args]]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"magick failed: {' '.join(cmd)}\n{r.stderr}")


def out(name):
    return str(OUT / (name + '.png'))


def finish(name):
    for twin in (out(name) + '.dds', out(name) + '.dds.d'):
        if os.path.exists(twin):
            os.remove(twin)   # the game prefers a cooked twin even when it is older
    magick(out(name), '-strip', '-define', 'png:exclude-chunks=date,time', out(name))


def palette():
    draws = []
    for i, (_, hexc) in enumerate(SWATCHES):
        x, y = (i % 8) * 32, (i // 8) * 32
        draws += ['-fill', hexc, '-draw', f'rectangle {x},{y} {x + 31},{y + 31}']
    magick('-size', '256x256', 'xc:#ff00ff', *draws, out('Palette')); finish('Palette')


def fm_card():
    W, H = 2048, 872
    dial_y = 560
    draws = ['-fill', 'none', '-stroke', '#7fe8ff', '-strokewidth', '4',
             '-draw', f'roundrectangle 120,{dial_y - 70} {W - 120},{dial_y + 90} 24,24']
    for k in range(0, 201):
        x = 200 + (W - 400) * k / 200
        tall = 60 if k % 20 == 0 else (36 if k % 10 == 0 else 18)
        draws += ['-stroke', '#bff4ff', '-strokewidth', '3' if k % 10 == 0 else '2',
                  '-draw', f'line {x:.1f},{dial_y - 40} {x:.1f},{dial_y - 40 + tall}']
    labels = []
    for f in range(88, 109, 2):
        x = 200 + (W - 400) * (f - 88) / 20
        labels += ['-annotate', f'+{x - 30:.0f}+{dial_y + 70}', str(f)]
    needle = 200 + (W - 400) * (88.9 - 88) / 20
    magick('-size', f'{W}x{H}', 'gradient:#0c1640-#04050f',
           # a soft glow behind the readout
           '(', '-size', f'{W}x{H}', 'xc:none', '-fill', '#16407a', '-draw', f'ellipse {W // 2},290 700,200 0,360', '-resize', '4%', '-resize', f'{W}x{H}!', ')',
           '-compose', 'screen', '-composite',
           *draws,
           '-stroke', 'none', '-fill', '#bff4ff', '-font', MONO, '-pointsize', '40', *labels,
           '-fill', '#ff3b30', '-stroke', '#ff3b30', '-strokewidth', '10', '-draw', f'line {needle:.0f},{dial_y - 95} {needle:.0f},{dial_y + 110}',
           '-stroke', 'none',
           '-font', BOLD, '-pointsize', '330', '-fill', '#e9fbff', '-gravity', 'north', '-annotate', '-120+40', '88.9',
           '-font', BOLD, '-pointsize', '150', '-fill', '#ff5a4a', '-annotate', '+600+170', 'FM',
           '-font', COND, '-pointsize', '62', '-fill', '#ffd27a', '-gravity', 'south', '-annotate', '+0+48',
           'MIDNIGHT AT THE FM DRIVE IN  ·  TUNE YOUR CAR RADIO',
           # scan lines, the projector's grain
           '(', '-size', f'{W}x{H}', 'pattern:horizontal3', '-negate', '-alpha', 'copy', '-channel', 'A', '-evaluate', 'multiply', '.12', '+channel', ')',
           '-gravity', 'center', '-compose', 'over', '-composite',
           out('FMCard'))
    finish('FMCard')


def marquee():
    W, H = 1024, 320
    bulbs = []
    for i in range(26):
        x = 30 + i * (W - 60) / 25
        bulbs += ['-draw', f'circle {x:.0f},22 {x + 9:.0f},22', '-draw', f'circle {x:.0f},{H - 22} {x + 9:.0f},{H - 22}']
    for j in range(1, 7):
        y = 22 + j * (H - 44) / 7
        bulbs += ['-draw', f'circle 30,{y:.0f} 39,{y:.0f}', '-draw', f'circle {W - 30},{y:.0f} {W - 21},{y:.0f}']
    magick('-size', f'{W}x{H}', 'xc:#8e1418',
           '-fill', '#2a0608', '-draw', f'rectangle 52,48 {W - 52},{H - 48}',
           '-fill', '#ffe7a8', *bulbs,
           '-font', SERIF, '-pointsize', '120', '-fill', '#ffcf5a', '-stroke', '#ff7a2a', '-strokewidth', '3',
           '-gravity', 'north', '-annotate', '+0+50', 'FM Drive In',
           '-stroke', 'none', '-font', COND, '-pointsize', '50', '-fill', '#9ff3ff', '-annotate', '+0+196',
           'TONIGHT · LIVE ON 88.9', out('Marquee'))
    finish('Marquee')


def quilt():
    colours = ['#c0392b', '#e67e22', '#f1c40f', '#f5e6c8', '#2e86c1', '#8e44ad', '#27ae60', '#d35400', '#e8b4b8', '#1f618d']
    draws = []
    n, s = 8, 64
    for r in range(n):
        for c in range(n):
            a = colours[(r * 3 + c * 7) % len(colours)]
            b = colours[(r * 5 + c * 2 + 4) % len(colours)]
            x, y = c * s, r * s
            draws += ['-fill', a, '-draw', f'rectangle {x},{y} {x + s - 1},{y + s - 1}']
            if (r + c) % 3 != 1:
                tri = f'{x},{y} {x + s - 1},{y} {x},{y + s - 1}' if (r * c) % 2 else f'{x + s - 1},{y} {x + s - 1},{y + s - 1} {x},{y + s - 1}'
                draws += ['-fill', b, '-draw', f'polygon {tri}']
    stitch = []
    for k in range(1, n):
        stitch += ['-draw', f'line {k * s},0 {k * s},{n * s}', '-draw', f'line 0,{k * s} {n * s},{k * s}']
    magick('-size', f'{n * s}x{n * s}', 'xc:white', *draws, '-stroke', '#f8f1e0', '-strokewidth', '3', *stitch, out('Quilt'))
    finish('Quilt')


def gravel():
    magick('-size', '512x512', '-seed', '9', 'plasma:', '-colorspace', 'gray', '-blur', '0x1', '+level-colors', '#3e3931,#867c6a',
           '(', '-size', '512x512', '-seed', '11', 'xc:gray50', '+noise', 'Random', '-colorspace', 'gray', '-blur', '0x.6', '-level', '30%,70%', ')',
           '-compose', 'overlay', '-composite',
           out('Gravel'))
    finish('Gravel')


def block():
    W, H = 512, 512
    draws = ['-stroke', '#4a4743', '-strokewidth', '5']
    rows = 8
    for r in range(rows + 1):
        y = r * H / rows
        draws += ['-draw', f'line 0,{y:.0f} {W},{y:.0f}']
        if r < rows:
            off = 0 if r % 2 == 0 else W / 4
            for k in range(3):
                x = (off + k * W / 2) % W
                draws += ['-draw', f'line {x:.0f},{y:.0f} {x:.0f},{y + H / rows:.0f}']
    magick('-size', f'{W}x{H}', '-seed', '5', 'plasma:', '-colorspace', 'gray', '-blur', '0x2', '+level-colors', '#8a857b,#aaa498', *draws, out('Block'))
    finish('Block')


def main(names=()):
    OUT.mkdir(parents=True, exist_ok=True)
    for f in (palette, fm_card, marquee, quilt, gravel, block):
        if not names or f.__name__ in names:
            f()


if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(__file__))
    main(sys.argv[1:])
