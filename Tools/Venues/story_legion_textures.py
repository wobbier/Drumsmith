"""StoryLegion's sign painter: every texture in Assets/Venues/StoryLegion/Textures/, drawn with
ImageMagick 7. Deterministic (fixed noise seeds, metadata stripped). No real logos or likenesses:
the crest is a made-up branch crest, Dad's portrait is a painted cartoon, the names are invented.
"""
import glob
import math
import os
import random
import re
import shutil
import subprocess
import sys

from story_legion_mesh import GRID, INKS, SWATCH, VENUE

OUT = VENUE / 'Textures'
SERIF = 'DejaVu-Serif-Bold'
SANS = 'DejaVu-Sans-Bold'
COND = 'DejaVu-Sans-Condensed-Bold'
ROOT = VENUE.parents[2]
HAND = str(ROOT / 'Assets/Fonts/GochiHand-Regular.ttf')
MARKER = str(ROOT / 'Assets/Fonts/PermanentMarker-Regular.ttf')


def _magick_bin():
    found = shutil.which('magick')
    if found:
        return found
    for path in sorted(glob.glob('/nix/store/*-imagemagick-7*/bin/magick')):
        return path
    sys.exit('story_legion_textures: ImageMagick 7 (magick) not found')


MAGICK = _magick_bin()


def magick(*args):
    cmd = [MAGICK, *[str(a) for a in args]]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"magick failed: {' '.join(cmd)}\n{r.stderr}")


def out(name):
    return str(OUT / (name + '.png'))


def finish(name):
    magick(out(name), '-depth', '8', '-strip', '-define', 'png:exclude-chunks=date,time', out(name))


def grain(size, seed, extra, amount=.18):
    """A little Gaussian noise straight onto the picture (size and extra kept for the call sites)."""
    return ['-seed', seed, '-attenuate', amount, '+noise', 'Gaussian']


def palette():
    draws = []
    for i, (ink, hexc) in enumerate(INKS.items()):
        x, y = (i % GRID) * SWATCH, (i // GRID) * SWATCH
        draws += ['-fill', hexc, '-draw', f'rectangle {x},{y} {x + SWATCH - 1},{y + SWATCH - 1}']
    magick('-size', '256x256', 'xc:#FF00FF', *draws, out('Legion_Palette'))
    finish('Legion_Palette')


def parquet():
    """Block parquet: 4 x 4 squares of five oak fingers, each square turned 90 degrees (1.2 m)."""
    rnd = random.Random(5)
    draws = []
    size, cells, fingers = 512, 4, 5
    cell = size // cells
    for cy in range(cells):
        for cx in range(cells):
            for f in range(fingers):
                tone = rnd.choice(['#A8743E', '#B27D45', '#9C6834', '#B9864E', '#A06C38', '#8F5E2E'])
                a = f * cell // fingers
                b = (f + 1) * cell // fingers - 1
                x0, y0 = cx * cell, cy * cell
                if (cx + cy) % 2 == 0:
                    r = (x0 + a, y0, x0 + b, y0 + cell - 1)
                else:
                    r = (x0, y0 + a, x0 + cell - 1, y0 + b)
                draws += ['-fill', tone, '-draw', 'rectangle %d,%d %d,%d' % r]
    magick('-size', f'{size}x{size}', 'xc:#A0703C', *draws,
           *grain(f'{size}x{size}', 11, ['-motion-blur', '0x6+0', '-level', '30%,70%']),
           '-stroke', '#4A2E18', '-strokewidth', '1', '-fill', 'none',
           *sum([['-draw', f'line {i},0 {i},{size}', '-draw', f'line 0,{i} {size},{i}'] for i in range(0, size, cell)], []),
           out('Parquet'))
    finish('Parquet')


def panelling():
    """Dark-stained wall panelling: vertical boards with V grooves (1.2 m square)."""
    size = 512
    draws = []
    rnd = random.Random(7)
    boards = 6
    w = size // boards
    for i in range(boards):
        tone = rnd.choice(['#5C3620', '#643B23', '#56321D', '#6A4026', '#5F3820'])
        draws += ['-fill', tone, '-draw', f'rectangle {i * w},0 {(i + 1) * w - 1},{size}']
        draws += ['-fill', '#2A160C', '-draw', f'rectangle {i * w},0 {i * w + 3},{size}']
        draws += ['-fill', '#7A4C2E', '-draw', f'rectangle {i * w + 4},0 {i * w + 5},{size}']
    magick('-size', f'{size}x{size}', 'xc:#5C3620', *draws,
           *grain(f'{size}x{size}', 3, ['-motion-blur', '0x24+90', '-level', '35%,65%']), out('Panelling'))
    finish('Panelling')


def lino():
    """Worn cream-and-tan floor tiles, 2 x 2 of 30 cm (0.6 m)."""
    size = 256
    h = size // 2
    magick('-size', f'{size}x{size}', 'xc:#CBBE9E',
           '-fill', '#A28A6A', '-draw', f'rectangle {h},0 {size},{h - 1}', '-draw', f'rectangle 0,{h} {h - 1},{size}',
           *grain(f'{size}x{size}', 19, ['-blur', '0x1.2', '-level', '40%,60%']),
           '-stroke', '#6E604C', '-strokewidth', '2', '-fill', 'none',
           '-draw', f'line 0,0 {size},0', '-draw', f'line 0,0 0,{size}', '-draw', f'line {h},0 {h},{size}',
           '-draw', f'line 0,{h} {size},{h}', out('Lino'))
    finish('Lino')


def ceiling():
    """Drop-ceiling tiles (two 0.6 m squares across 1.2 x 0.6 m) with the white T-bar grid."""
    w, h = 512, 256
    magick('-size', f'{w}x{h}', 'xc:#D9D4C8',
           *grain(f'{w}x{h}', 23, ['-blur', '0x.8', '-level', '20%,80%']),
           '-fill', '#EEEDE8', '-draw', f'rectangle 0,0 {w},6', '-draw', f'rectangle 0,0 6,{h}',
           '-draw', f'rectangle {w // 2 - 3},0 {w // 2 + 3},{h}',
           '-fill', '#BDB8AC', '-draw', f'rectangle 0,7 {w},8', '-draw', f'rectangle 7,0 8,{h}', out('Ceiling'))
    finish('Ceiling')


def crest():
    """A made-up branch crest: a navy shield, gold chevron and maple sprig in a laurel, on a wooden
    roundel, with a ribbon reading BRANCH 112."""
    s = 512
    c = s // 2
    laurel = []
    for side in (-1, 1):
        for k in range(10):
            a = math.radians(-50 + k * 14)
            x, y = c + side * 196 * math.cos(a), c - 196 * math.sin(a)
            laurel += ['-draw', f'ellipse {x:.0f},{y:.0f} 24,11 {(-1 if side > 0 else 1) * (90 - k * 14) - 90 * side},360']
    magick('-size', f'{s}x{s}', 'xc:none',
           '-fill', '#4A2B18', '-draw', f'circle {c},{c} {c},8',
           '-fill', '#6B4127', '-draw', f'circle {c},{c} {c},22',
           '-fill', '#B8933F', *laurel,
           '-fill', '#C9A24A', '-draw', f'path "M {c - 120},{c - 150} L {c + 120},{c - 150} L {c + 120},{c + 10} Q {c + 110},{c + 120} {c},{c + 170} Q {c - 110},{c + 120} {c - 120},{c + 10} Z"',
           '-fill', '#1E2A4C', '-draw', f'path "M {c - 104},{c - 136} L {c + 104},{c - 136} L {c + 104},{c + 8} Q {c + 96},{c + 108} {c},{c + 152} Q {c - 96},{c + 108} {c - 104},{c + 8} Z"',
           '-fill', '#C9A24A', '-draw', f'path "M {c - 104},{c + 30} L {c},{c - 40} L {c + 104},{c + 30} L {c + 104},{c + 62} L {c},{c - 8} L {c - 104},{c + 62} Z"',
           '-fill', '#B3242B', '-draw', f'path "M {c},{c - 120} L {c + 14},{c - 92} L {c + 38},{c - 100} L {c + 30},{c - 74} L {c + 52},{c - 70} L {c + 18},{c - 50} L {c + 6},{c - 56} L {c + 4},{c - 40} L {c - 4},{c - 40} L {c - 6},{c - 56} L {c - 18},{c - 50} L {c - 52},{c - 70} L {c - 30},{c - 74} L {c - 38},{c - 100} L {c - 14},{c - 92} Z"',
           '-fill', '#E9E1CC', '-draw', f'path "M {c - 190},{c + 150} L {c + 190},{c + 150} L {c + 170},{c + 205} L {c - 170},{c + 205} Z"',
           '-font', SERIF, '-pointsize', '40', '-fill', '#1E2A4C', '-gravity', 'center',
           '-annotate', '+0+178', 'BRANCH 112', '-pointsize', '30', '-fill', '#E9D9A6', '-annotate', '+0-188', 'LEGION',
           out('Crest'))
    finish('Crest')


def flag_canada():
    w, h = 512, 256
    c, m = w // 2, h // 2
    leaf = (f'M {c},{m - 92} L {c + 18},{m - 56} L {c + 40},{m - 66} L {c + 30},{m - 14} L {c + 62},{m - 48} '
            f'L {c + 68},{m - 32} L {c + 96},{m - 38} L {c + 86},{m - 6} L {c + 100},{m + 2} L {c + 44},{m + 46} '
            f'L {c + 52},{m + 64} L {c + 6},{m + 58} L {c + 8},{m + 100} L {c - 8},{m + 100} L {c - 6},{m + 58} '
            f'L {c - 52},{m + 64} L {c - 44},{m + 46} L {c - 100},{m + 2} L {c - 86},{m - 6} L {c - 96},{m - 38} '
            f'L {c - 68},{m - 32} L {c - 62},{m - 48} L {c - 30},{m - 14} L {c - 40},{m - 66} L {c - 18},{m - 56} Z')
    magick('-size', f'{w}x{h}', 'xc:#F4F1EA', '-fill', '#C8202C', '-draw', f'rectangle 0,0 {w // 4},{h}',
           '-draw', f'rectangle {3 * w // 4},0 {w},{h}', '-draw', f'path "{leaf}"', out('FlagCanada'))
    finish('FlagCanada')


def flag_branch():
    """The branch's own standard: navy with a gold border and the crest's chevron."""
    w, h = 512, 256
    magick('-size', f'{w}x{h}', 'xc:#1E2A4C', '-fill', 'none', '-stroke', '#C9A24A', '-strokewidth', '10',
           '-draw', f'rectangle 14,14 {w - 15},{h - 15}', '-stroke', 'none', '-fill', '#C9A24A',
           '-draw', f'path "M 160,170 L 256,96 L 352,170 L 352,196 L 256,124 L 160,196 Z"',
           '-font', SERIF, '-pointsize', '34', '-gravity', 'north', '-annotate', '+0+34', 'BRANCH 112', out('FlagBranch'))
    finish('FlagBranch')


def portrait():
    """Dad: a painted studio portrait. Grey hair, glasses, a moustache, navy blazer, a poppy."""
    w, h = 400, 500
    c = w // 2
    magick('-size', f'{w}x{h}', 'radial-gradient:#9A7A55-#3B2A1C',
           # blazer and shirt
           '-fill', '#1F2A44', '-draw', f'path "M 30,500 Q 40,380 120,350 L {c},390 L 280,350 Q 360,380 370,500 Z"',
           '-fill', '#F2EEE6', '-draw', f'path "M 150,352 L {c},420 L 250,352 L 236,340 L {c},372 L 164,340 Z"',
           '-fill', '#8C1C2B', '-draw', f'path "M {c - 12},378 L {c + 12},378 L {c + 18},470 L {c},492 L {c - 18},470 Z"',
           '-fill', '#C70F2C', '-draw', 'circle 290,410 290,394', '-fill', '#111111', '-draw', 'circle 290,410 290,404',
           # neck, ears, face
           '-fill', '#D9A383', '-draw', f'rectangle {c - 38},300 {c + 38},360',
           '-draw', f'ellipse {c - 92},220 16,26 0,360', '-draw', f'ellipse {c + 92},220 16,26 0,360',
           '-fill', '#E3AE8C', '-draw', f'ellipse {c},210 92,118 0,360',
           # hair
           '-fill', '#C9C6C0', '-draw', f'path "M {c - 96},200 Q {c - 100},90 {c},86 Q {c + 100},90 {c + 96},200 Q {c + 86},140 {c + 40},126 Q {c},150 {c - 50},128 Q {c - 86},140 {c - 96},200 Z"',
           # brows, glasses, eyes
           '-fill', '#9E9A94', '-draw', f'rectangle {c - 62},176 {c - 20},184', '-draw', f'rectangle {c + 20},176 {c + 62},184',
           '-fill', 'none', '-stroke', '#3A2A20', '-strokewidth', '5',
           '-draw', f'roundrectangle {c - 70},190 {c - 12},228 10,10', '-draw', f'roundrectangle {c + 12},190 {c + 70},228 10,10',
           '-draw', f'line {c - 12},204 {c + 12},204', '-stroke', 'none',
           '-fill', '#2A1E16', '-draw', f'circle {c - 40},210 {c - 40},203', '-draw', f'circle {c + 40},210 {c + 40},203',
           # nose, moustache, smile
           '-fill', '#C98F70', '-draw', f'path "M {c},214 L {c + 14},262 L {c - 10},264 Z"',
           '-fill', '#B5B0A8', '-draw', f'path "M {c - 52},284 Q {c},262 {c + 52},284 Q {c},296 {c - 52},284 Z"',
           '-fill', 'none', '-stroke', '#7A3A2E', '-strokewidth', '5', '-draw', f'path "M {c - 34},298 Q {c},318 {c + 34},298"',
           '-stroke', 'none',
           *grain(f'{w}x{h}', 29, ['-blur', '0x1',
           '-level', '42%,58%']), out('Portrait'))
    finish('Portrait')


def honour_roll():
    w, h = 384, 512
    rnd = random.Random(41)
    first = 'ABCDEGHJLMNPRSTW'
    last = ['MACLEOD', 'TREMBLAY', 'OKAFOR', 'BOUCHARD', 'KOWALSKI', 'FRASER', 'NGUYEN', 'GAGNON', 'MURRAY',
            'BELANGER', 'SINGH', 'CAMPBELL', 'ROY', 'LAVOIE', 'STEWART', 'PELLETIER', 'MCKAY', 'HUNTER']
    draws = []
    for i, name in enumerate(last):
        draws += ['-annotate', f'+{40 if i % 2 == 0 else 206}+{150 + (i // 2) * 36}', f'{rnd.choice(first)}. {name}']
    magick('-size', f'{w}x{h}', 'xc:#4A2A16', '-fill', '#6B3E22', '-draw', f'rectangle 14,14 {w - 15},{h - 15}',
           '-fill', '#D8B860', '-font', SERIF, '-pointsize', '40', '-gravity', 'north', '-annotate', '+0+34', 'HONOUR ROLL',
           '-pointsize', '20', '-annotate', '+0+86', 'LEST WE FORGET', '-gravity', 'northwest', '-font', COND,
           '-pointsize', '17', *draws, out('HonourRoll'))
    finish('HonourRoll')


def letter_board():
    w, h = 512, 320
    lines = ['CELEBRATION OF LIFE', 'DOUG', '1951 - 2026', 'ALL WELCOME  -  BAR OPEN']
    draws = []
    for i, t in enumerate(lines):
        draws += ['-pointsize', '58' if i == 1 else '34', '-annotate', f'+0+{38 + i * 66 + (14 if i > 1 else 0)}', t]
    magick('-size', f'{w}x{h}', 'xc:#18181A',
           '(', '-size', f'{w}x{h}', 'pattern:horizontal3', '-negate', '-level', '0%,900%', ')', '-compose', 'multiply', '-composite',
           '-fill', '#ECE8DE', '-font', COND, '-gravity', 'north', *draws, out('LetterBoard'))
    finish('LetterBoard')


def meat_draw():
    w, h = 384, 256
    magick('-size', f'{w}x{h}', 'xc:#F1E3B0', '-fill', '#B3242B', '-draw', f'rectangle 0,0 {w},54',
           '-fill', '#F6EED8', '-font', SANS, '-pointsize', '34', '-gravity', 'north', '-annotate', '+0+8', 'MEAT DRAW',
           '-fill', '#1E2A4C', '-pointsize', '40', '-annotate', '+0+76', 'SATURDAYS 3PM',
           '-font', COND, '-pointsize', '26', '-annotate', '+0+140', 'DARTS LEAGUE THURS',
           '-annotate', '+0+180', 'BINGO SUN  -  EUCHRE TUES', out('MeatDraw'))
    finish('MeatDraw')


def memorial_card():
    w, h = 384, 256
    magick('-size', f'{w}x{h}', 'xc:#F5F0E4', '-fill', 'none', '-stroke', '#B89A52', '-strokewidth', '6',
           '-draw', f'rectangle 12,12 {w - 13},{h - 13}', '-stroke', 'none', '-fill', '#3A2A20', '-font', SERIF,
           '-pointsize', '36', '-gravity', 'center', '-annotate', '+0-50', 'In Loving Memory',
           '-font', HAND, '-pointsize', '64', '-annotate', '+0+20', 'Dad', '-font', SERIF, '-pointsize', '22',
           '-annotate', '+0+80', 'he would have wanted a party', out('MemorialCard'))
    finish('MemorialCard')


def exit_sign():
    magick('-size', '256x96', 'xc:#14381F', '-fill', '#7DF59A', '-font', SANS, '-pointsize', '64', '-gravity', 'center',
           '-annotate', '+0+0', 'EXIT', out('Exit'))
    finish('Exit')


def lest_we_forget():
    magick('-size', '512x128', 'xc:#6B4A1E', '-fill', '#D9B860', '-draw', 'rectangle 6,6 505,121', '-fill', '#5A3C16',
           '-draw', 'rectangle 12,12 499,115', '-fill', '#E8CF84', '-font', SERIF, '-pointsize', '44', '-gravity', 'center',
           '-annotate', '+0+0', 'LEST WE FORGET', out('LestWeForget'))
    finish('LestWeForget')


def old_photos():
    """Four sepia photos of nobody in particular: hockey teams, a parade, a ribbon cutting."""
    w, h = 512, 384
    rnd = random.Random(53)
    draws = []
    for k, (x0, y0) in enumerate([(0, 0), (256, 0), (0, 192), (256, 192)]):
        draws += ['-fill', '#E8DCC0', '-draw', f'rectangle {x0 + 8},{y0 + 8} {x0 + 247},{y0 + 183}',
                  '-fill', '#8C6E4A', '-draw', f'rectangle {x0 + 18},{y0 + 18} {x0 + 237},{y0 + 160}',
                  '-fill', '#B49A74', '-draw', f'rectangle {x0 + 18},{y0 + 18} {x0 + 237},{y0 + 80}']
        for p in range(6 + k):
            px = x0 + 34 + p * (190 // (6 + k))
            py = y0 + 70 + rnd.randint(0, 20)
            draws += ['-fill', '#4E3A26', '-draw', f'circle {px},{py} {px},{py - 10}',
                      '-draw', f'rectangle {px - 11},{py + 10} {px + 11},{py + 70}']
    magick('-size', f'{w}x{h}', 'xc:#2A1C12', *draws, out('OldPhotos'))
    finish('OldPhotos')


def tea_towel():
    magick('-size', '256x256', 'xc:#EFE9DD', '-fill', '#B83A3A', '-draw', 'rectangle 0,22 256,40',
           '-draw', 'rectangle 0,216 256,234', '-fill', '#2C3E66', '-draw', 'rectangle 0,46 256,52',
           '-draw', 'rectangle 0,204 256,210',
           *grain('256x256', 61, ['-blur', '0x.6',
           '-level', '40%,60%']), out('TeaTowel'))
    finish('TeaTowel')


def napkins():
    """Request napkins, written in a hurry."""
    magick('-size', '256x256', 'xc:#F8F6F0', '-fill', '#2A3A8A', '-font', HAND, '-pointsize', '34', '-gravity', 'center',
           '-annotate', '-8-54', 'play Helena!!', '-fill', '#8C1C2B', '-annotate', '+10+0', 'something Dad',
           '-annotate', '+10+36', 'would dance to', '-fill', '#222222', '-annotate', '+0+86', 'MY WAY again?', out('Napkins'))
    finish('Napkins')


def banner():
    """A hand-painted bedsheet banner the cousins taped over the bar hatch."""
    magick('-size', '1024x192', 'xc:#F2EEE4', '-fill', '#1E2A4C', '-font', MARKER, '-pointsize', '104', '-gravity', 'center',
           '-annotate', '+0+0', 'CHEERS, DAD', '-fill', '#C70F2C', '-draw', 'circle 70,96 70,60', '-draw', 'circle 954,96 954,60',
           '-fill', '#111111', '-draw', 'circle 70,96 70,84', '-draw', 'circle 954,96 954,84', out('Banner'))
    finish('Banner')


def window_blind():
    magick('-size', '256x256', 'xc:#141C33', '-fill', '#D8D2C2',
           *sum([['-draw', f'rectangle 0,{y} 256,{y + 9}'] for y in range(0, 150, 14)], []),
           '-fill', '#3A4A70', '-draw', 'rectangle 0,160 256,256', '-fill', '#FFD27A', '-draw', 'circle 190,196 190,188',
           out('WindowBlind'))
    finish('WindowBlind')


def all_textures():
    OUT.mkdir(parents=True, exist_ok=True)
    before = {f.name: f.read_bytes() for f in OUT.glob('*.png')}
    for f in (palette, parquet, panelling, lino, ceiling, crest, flag_canada, flag_branch, portrait, honour_roll,
              letter_board, meat_draw, memorial_card, exit_sign, lest_we_forget, old_photos, tea_towel, napkins,
              banner, window_blind):
        f()
    # The game prefers a cooked .dds twin even when the .png is newer: drop twins of redrawn pictures.
    for f in OUT.glob('*.png'):
        if before.get(f.name) != f.read_bytes():
            for twin in (f.with_name(f.name + '.dds'), f.with_name(f.name + '.dds.d')):
                if twin.exists():
                    twin.unlink() if twin.is_file() else shutil.rmtree(twin)
    return ['Parquet', 'Panelling', 'Lino', 'Ceiling', 'Crest', 'FlagCanada', 'FlagBranch', 'Portrait', 'HonourRoll',
            'LetterBoard', 'MeatDraw', 'MemorialCard', 'Exit', 'LestWeForget', 'OldPhotos', 'TeaTowel', 'Napkins',
            'Banner', 'WindowBlind']


if __name__ == '__main__':
    all_textures()
