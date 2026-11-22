"""Food Court venue: the sign shop. Paints the venue's textures with ImageMagick 7 and writes the
flat meshes that carry them (signs, banners, the drumhead discs, shutters, the tiled floor).

Textures are only repainted with --textures (or when one is missing), so the generator reruns
without ImageMagick; the PNGs it made are kept beside the meshes in Assets/Venues/StoryFoodCourt/Models.
Mesh convention (as the Backyard's): build in venue space, faces wound counter-clockwise seen from
the front, and written as (x, y, -z) reversed, because the OBJ importer flips z.
"""
import glob
import math
import os
import random
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MODELS = os.path.join(ROOT, 'Assets', 'Venues', 'StoryFoodCourt', 'Models')
LOCAL = 'Assets/Venues/StoryFoodCourt/Models/'
MARKER = os.path.join(ROOT, 'Assets', 'Fonts', 'PermanentMarker-Regular.ttf')
HAND = os.path.join(ROOT, 'Assets', 'Fonts', 'GochiHand-Regular.ttf')
BOLD = 'DejaVu-Sans-Bold'
COND = 'DejaVu-Sans-Condensed-Bold'
SERIF = 'DejaVu-Serif-Bold'


def _magick_bin():
    found = shutil.which('magick')
    if found:
        return found
    for path in sorted(glob.glob('/nix/store/*imagemagick-7*/bin/magick')):
        return path
    return None


def magick(*args):
    exe = _magick_bin()
    if not exe:
        sys.exit('ImageMagick 7 (magick) not found: run without --textures to keep the painted PNGs')
    r = subprocess.run([exe, *[str(a) for a in args]], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit('magick failed: %s\n%s' % (' '.join(str(a) for a in args), r.stderr))


def out(name):
    return os.path.join(MODELS, name + '.png')


def finish(name):
    # The game prefers a cooked .dds twin even when the PNG is newer: drop it so the new picture loads.
    for twin in (out(name) + '.dds', out(name) + '.dds.d'):
        if os.path.exists(twin):
            os.remove(twin)
    magick(out(name), '-strip', '-define', 'png:exclude-chunks=date,time', out(name))


def grain(name, amount=.3, seed=1):
    magick(out(name), '(', '+clone', '-seed', seed, '-attenuate', amount, '+noise', 'Gaussian', '-colorspace', 'gray', ')',
           '-compose', 'overlay', '-composite', out(name))


# ---- textures ---------------------------------------------------------------------------------
# (name, background, ink, text, font, size, accent stripe)
FASCIAS = [
    ('SignGoldenWok', 'rgb(176,22,26)', 'rgb(255,206,64)', 'GOLDEN WOK', SERIF, 150, 'rgb(255,206,64)'),
    ('SignPretzel', 'rgb(20,42,110)', 'rgb(255,226,90)', 'PRETZEL TWIST', BOLD, 128, 'rgb(240,120,30)'),
    ('SignTaco', 'rgb(240,120,20)', 'rgb(255,250,235)', 'TACO LOCO', MARKER, 150, 'rgb(40,150,60)'),
    ('SignScoop', 'rgb(250,150,190)', 'rgb(120,40,90)', 'BIG SCOOP', MARKER, 150, 'rgb(255,255,255)'),
    ('SignHotDog', 'rgb(255,214,40)', 'rgb(200,30,30)', 'HOT DOG HUT', BOLD, 132, 'rgb(200,30,30)'),
    ('SignJuice', 'rgb(40,150,70)', 'rgb(255,255,240)', 'JUICE JUNCTION', BOLD, 116, 'rgb(255,200,40)'),
    ('SignSkate', 'rgb(18,18,20)', 'rgb(120,255,90)', 'DROP-IN SKATE', MARKER, 140, 'rgb(255,60,140)'),
    ('SignDept', 'rgb(235,232,225)', 'rgb(60,60,70)', 'HARTLEY & SONS', SERIF, 120, 'rgb(150,30,40)'),
    ('SignFoodCourt', 'rgb(30,110,120)', 'rgb(255,255,255)', 'FOOD COURT', BOLD, 160, 'rgb(250,190,60)'),
]


def fascia(name, bg, ink, text, font, size, accent):
    magick('-size', '1024x256', f'xc:{bg}', '-fill', accent, '-draw', 'rectangle 0,0 1024,14', '-draw', 'rectangle 0,242 1024,256',
           '(', '-background', 'none', '-fill', ink, '-font', font, '-size', '930x170', '-gravity', 'center', f'label:{text}', ')',
           '-gravity', 'center', '-compose', 'over', '-composite', out(name))
    finish(name)


def menu(name, seed, bg, ink):
    rnd = random.Random(seed)
    items = ['COMBO #1', 'COMBO #2', 'FAMILY BOX', 'KIDS MEAL', 'LARGE FRIES', 'FOUNTAIN POP', 'SIDE SALAD', 'ONION RINGS']
    draws = []
    for i in range(4):
        x = 20 + i * 250
        c = 'rgb(%d,%d,%d)' % (rnd.randint(150, 255), rnd.randint(80, 200), rnd.randint(20, 120))
        draws += ['-fill', c, '-draw', f'roundrectangle {x},24 {x+230},170 18,18',
                  '-fill', 'rgba(255,255,255,0.55)', '-draw', f'ellipse {x+115},100 70,40 0,360']
    magick('-size', '1024x384', f'xc:{bg}', *draws, out(name))
    for i, item in enumerate(rnd.sample(items, 6)):
        col, row = i % 2, i // 2
        price = '%d.%02d' % (rnd.randint(3, 11), rnd.choice((29, 49, 79, 99)))
        magick(out(name), '-font', COND, '-pointsize', 34, '-fill', ink, '-annotate', f'+{40+col*500}+{225+row*52}', item,
               '-annotate', f'+{380+col*500}+{225+row*52}', price, out(name))
    finish(name)


def banner(name, bg, ink, lines, font, sizes, w=1024, h=256, edge=None, seed=1, tilt=0):
    args = ['-size', f'{w}x{h}', f'xc:{bg}']
    if edge:
        args += ['-fill', edge, '-draw', f'rectangle 0,0 {w},12', '-draw', f'rectangle 0,{h-12} {w},{h}']
    magick(*args, out(name))
    total = sum(sizes)
    usable = h - 40
    y = 20
    for text, size in zip(lines, sizes):
        lh = int(usable * size / total)
        magick(out(name), '(', '-background', 'none', '-fill', ink, '-font', font, '-size', f'{int(w*.9)}x{int(lh*.92)}',
               '-gravity', 'center', f'label:{text}', '-rotate', tilt, ')', '-gravity', 'north', '-geometry', f'+0+{y}',
               '-compose', 'over', '-composite', out(name))
        y += lh
    grain(name, .25, seed)
    finish(name)


def no_skate():
    magick('-size', '256x320', 'xc:rgb(245,245,240)', '-stroke', 'rgb(200,20,20)', '-strokewidth', 18, '-fill', 'none',
           '-draw', 'circle 128,128 128,30', '-draw', 'line 60,60 196,196',
           '-stroke', 'none', '-fill', 'rgb(30,30,30)', '-draw', 'roundrectangle 78,118 178,132 6,6',
           '-draw', 'circle 92,142 92,134', '-draw', 'circle 164,142 164,134',
           '-gravity', 'south', '-font', BOLD, '-pointsize', 30, '-annotate', '+0+22', 'NO SKATING', out('NoSkate'))
    finish('NoSkate')


def cardboard(name, label, size=70, seed=3):
    magick('-size', '512x384', 'xc:rgb(168,126,80)', '(', '-size', '64x384', '-seed', seed, 'plasma:fractal', '-colorspace', 'gray',
           '-resize', '512x384!', '-motion-blur', '0x6+90', '-auto-level', '+level', '80%,100%', ')', '-compose', 'multiply', '-composite',
           '-fill', 'rgba(220,200,150,0.6)', '-draw', 'rectangle 0,0 512,26', out(name))
    magick(out(name), '-gravity', 'center', '-font', MARKER, '-pointsize', size, '-fill', 'rgb(20,20,20)', '-annotate', '-4x-4+0+0', label, out(name))
    grain(name, .4, seed)
    finish(name)


def shutter(name, note=None):
    draws = []
    for y in range(0, 512, 16):
        draws += ['-fill', 'rgb(150,152,156)', '-draw', f'rectangle 0,{y} 256,{y+9}', '-fill', 'rgb(98,100,106)', '-draw', f'rectangle 0,{y+9} 256,{y+12}']
    magick('-size', '256x512', 'xc:rgb(124,126,130)', *draws, '-fill', 'rgb(70,70,74)', '-draw', 'rectangle 0,494 256,512',
           '-fill', 'rgb(200,170,40)', '-draw', 'rectangle 112,470 144,494', out(name))
    if note:
        magick(out(name), '-fill', 'rgb(250,248,236)', '-draw', 'polygon 40,150 214,140 220,330 46,338',
               '-fill', 'rgba(230,220,170,0.8)', '-draw', 'rectangle 100,132 156,152',
               '-gravity', 'center', '-font', MARKER, '-pointsize', 34, '-fill', 'rgb(20,20,30)', '-annotate', '-2x-2+0-40', note[0],
               '-pointsize', 26, '-annotate', '-2x-2+0+10', note[1], '-pointsize', 26, '-annotate', '-2x-2+0+50', note[2], out(name))
    grain(name, .35, 7)
    finish(name)


def floor():
    """Two by two metres of terrazzo-look tile: 4 x 4 tiles, cream with terracotta inlay."""
    rnd = random.Random(9)
    s, t = 512, 128
    draws = []
    for r in range(4):
        for c in range(4):
            v = rnd.randint(-8, 8)
            col = (222 + v, 214 + v, 196 + v) if (r + c) % 2 == 0 else (196 + v, 120 + v, 88 + v)
            draws += ['-fill', 'rgb(%d,%d,%d)' % col, '-draw', f'rectangle {c*t+2},{r*t+2} {c*t+t-3},{r*t+t-3}']
    magick('-size', f'{s}x{s}', 'xc:rgb(150,140,128)', *draws, out('FloorTile'))
    magick(out('FloorTile'), '(', '-size', f'{s}x{s}', '-seed', 12, 'plasma:fractal', '-colorspace', 'gray', '-blur', '0x1',
           '-auto-level', '+level', '84%,100%', ')', '-compose', 'multiply', '-composite', out('FloorTile'))
    grain('FloorTile', .5, 4)
    finish('FloorTile')


SCRAWLS = ['Jess', 'Dana!', 'Marco', 'Priya', 'Tomo', 'K.J.', 'Bee', 'Luis', 'Ana', 'Sam xo', 'Rudy', 'Ollie', 'Mei',
           'Deshawn', 'Ari', 'Nat', 'Gus', 'Ivy', 'Raj', 'Tess', 'Wes', 'Lou', 'Fern', 'Jun', 'Max', 'Zoe', 'Theo',
           'Rosa', 'Eli', 'Kim', '31 YRS', 'RIP MALL', 'Hot Dog Hut 4ever', 'Golden Wok crew', 'thx 4 the fries',
           'BIG SCOOP <3', 'skate or die', 'last day!!', 'Pretzel gang']


def drumhead(name, stage):
    """The spare kick head: 0 one signature; 1 + a peaked cap; 2 + the guard's moustache; 3 nearly black."""
    rnd = random.Random(31)
    s = 512
    magick('-size', f'{s}x{s}', 'xc:rgb(20,20,22)', '-fill', 'rgb(244,242,234)', '-draw', 'circle 256,256 256,10',
           '-fill', 'none', '-stroke', 'rgba(200,196,186,0.8)', '-strokewidth', 3, '-draw', 'circle 256,256 256,30',
           '-stroke', 'rgba(120,120,120,0.6)', '-strokewidth', 2, '-draw', 'circle 256,256 256,14', out(name))
    if stage >= 3:
        # Dozens of signatures, every pen in the mall, then more over the top.
        args = []
        for i in range(110):
            word = rnd.choice(SCRAWLS)
            ang = math.radians(rnd.uniform(0, 360)); rad = rnd.uniform(0, 205)
            x, y = 256 + rad * math.cos(ang), 256 + rad * math.sin(ang)
            ink = rnd.choice(['rgb(10,10,12)'] * 5 + ['rgb(20,40,140)', 'rgb(170,20,30)', 'rgb(20,110,40)', 'rgb(110,20,120)'])
            t = rnd.randint(-40, 40)
            args += ['-font', rnd.choice((MARKER, HAND)), '-pointsize', rnd.randint(22, 46), '-fill', ink,
                     '-annotate', '%dx%d+%d+%d' % (t, t, x - 50, y), word]
        magick(out(name), *args, out(name))
    # The first signature, big, across the lower left.
    magick(out(name), '-font', MARKER, '-pointsize', 64, '-fill', 'rgb(8,8,10)', '-annotate', '-14x-14+92+420', 'Kit', out(name))
    if stage >= 3:
        magick(out(name), '-fill', 'rgba(244,242,234,0.55)', '-draw', 'ellipse 256,250 170,150 0,360', out(name))
    if stage >= 1:
        # A broad cartoon of a peaked cap, the guard's, high on the head.
        cap = ('-fill', 'rgb(30,38,80)' if stage >= 3 else 'none', '-stroke', 'rgb(8,8,10)', '-strokewidth', 11,
               '-draw', 'path "M 136,214 C 150,96 362,96 376,214 Z"',
               '-draw', 'path "M 108,222 C 200,250 330,250 420,214 C 380,268 160,276 108,222 Z"',
               '-fill', 'rgb(250,210,40)', '-strokewidth', 6, '-draw', 'polygon 256,128 276,160 256,190 236,160')
        magick(out(name), *cap, out(name))
    if stage >= 2:
        # The gigantic moustache under the cap, and two dot eyes between.
        magick(out(name), '-fill', 'rgb(8,8,10)', '-stroke', 'rgb(8,8,10)', '-strokewidth', 4,
               '-draw', 'circle 206,286 206,300', '-draw', 'circle 306,286 306,300',
               '-draw', 'path "M 256,330 C 214,300 150,316 120,360 C 104,384 74,384 62,362 C 86,378 104,350 128,330 C 170,296 230,300 256,318 Z"',
               '-draw', 'path "M 256,330 C 298,300 362,316 392,360 C 408,384 438,384 450,362 C 426,378 408,350 384,330 C 342,296 282,300 256,318 Z"',
               out(name))
        if stage < 3:
            magick(out(name), '-font', HAND, '-pointsize', 40, '-fill', 'rgb(20,40,140)', '-annotate', '+300+440', 'Officer Ray', out(name))
    grain(name, .2, 5 + stage)
    finish(name)


def paint_textures(force=False):
    os.makedirs(MODELS, exist_ok=True)
    wanted = [f[0] for f in FASCIAS] + ['MenuA', 'MenuB', 'MenuC', 'BannerMustGo', 'BannerMustGo2', 'BannerThanks', 'BannerSkate',
                                       'PosterClosing', 'NoSkate', 'SignTheHead', 'Shutter', 'ShutterNote', 'FloorTile',
                                       'SignSecurity', 'HeadA', 'HeadB', 'HeadC', 'HeadD', 'Directory', 'BannerLastDay']
    if not force and all(os.path.exists(out(n)) for n in wanted):
        return
    for f in FASCIAS:
        fascia(*f)
    menu('MenuA', 1, 'rgb(250,244,226)', 'rgb(60,30,20)')
    menu('MenuB', 2, 'rgb(30,30,36)', 'rgb(255,240,200)')
    menu('MenuC', 3, 'rgb(255,236,200)', 'rgb(120,20,20)')
    banner('BannerMustGo', 'rgb(214,24,30)', 'rgb(255,236,40)', ['EVERYTHING', 'MUST GO!'], BOLD, [118, 118], 1024, 384, 'rgb(255,236,40)', 2)
    banner('BannerMustGo2', 'rgb(255,226,30)', 'rgb(200,20,26)', ['EVERYTHING MUST GO', 'ALL SALES FINAL  -  70% OFF'], BOLD, [92, 54], 1024, 256, 'rgb(200,20,26)', 3)
    banner('BannerThanks', 'rgb(16,96,110)', 'rgb(255,255,255)', ['THANK YOU FOR 31 YEARS', 'MALL CLOSES SUNDAY 6PM'], BOLD, [84, 54], 1024, 256, 'rgb(250,190,60)', 4)
    banner('BannerSkate', 'rgb(16,16,18)', 'rgb(120,255,90)', ['DROP-IN SKATE SUPPLY', 'FAREWELL MATINEE * ALL AGES * SAT 2PM'], MARKER, [96, 48], 1024, 320, 'rgb(255,60,140)', 5, -2)
    banner('BannerLastDay', 'rgb(250,248,240)', 'rgb(214,24,30)', ['LAST WEEKEND!', 'everything 70% off'], MARKER, [120, 64], 1024, 384, None, 6, -3)
    banner('PosterClosing', 'rgb(255,226,30)', 'rgb(20,20,20)', ['STORE', 'CLOSING', 'ALL SALES FINAL'], BOLD, [96, 96, 44], 512, 512, 'rgb(214,24,30)', 7)
    banner('SignSecurity', 'rgb(20,30,70)', 'rgb(255,255,255)', ['SECURITY'], BOLD, [96], 512, 160, 'rgb(250,190,60)', 8)
    banner('Directory', 'rgb(30,40,48)', 'rgb(230,240,240)', ['MALL DIRECTORY', '1 Golden Wok  2 Pretzel Twist', '3 Taco Loco  4 Big Scoop',
                                                             '5 Hot Dog Hut  6 Juice Junction', 'L2  Drop-In Skate'], COND, [44, 30, 30, 30, 30], 512, 640, 'rgb(250,190,60)', 9)
    cardboard('SignTheHead', 'SIGN THE\nHEAD!', 84)
    no_skate()
    shutter('Shutter')
    shutter('ShutterNote', ('CLOSED', 'thanks for', '31 years!'))
    floor()
    for i, n in enumerate(('HeadA', 'HeadB', 'HeadC', 'HeadD')):
        drumhead(n, i)


# ---- flat meshes ------------------------------------------------------------------------------
def write_mtl(name, texture, emissive=0.0):
    lines = [f'newmtl {name}', 'Kd 1 1 1', 'Ks 0 0 0', 'Ns 0', 'illum 1', f'map_Kd {texture}']
    if emissive:
        lines += ['Ke %g %g %g' % (emissive, emissive, emissive), f'map_Ke {texture}']
    _save(os.path.join(MODELS, name + '.mtl'), '\n'.join(lines) + '\n')


def _save(path, content):
    old = None
    if os.path.exists(path):
        old = open(path, 'rb').read()
    if old != content.encode():
        with open(path, 'w', newline='\n') as f:
            f.write(content)
        twin = path + '.assbin'
        if os.path.exists(twin):
            os.remove(twin)


def write_obj(name, faces, note, mtl=None, double=False):
    """faces: [[(x, y, z), (u, v)], ...] polygons in venue space, CCW seen from the front."""
    mtl = mtl or name
    coords, uvs, normals, out_faces = {}, {}, {}, []
    polys = list(faces) + ([list(reversed(f)) for f in faces] if double else [])
    for face in polys:
        pts = [(p[0], p[1], -p[2]) for p, _ in face]
        tex = [uv for _, uv in face]
        a, b, c = pts[0], pts[1], pts[2]
        u = (b[0]-a[0], b[1]-a[1], b[2]-a[2]); v = (c[0]-a[0], c[1]-a[1], c[2]-a[2])
        n = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
        ln = math.sqrt(sum(x*x for x in n)) or 1
        n = tuple(round(x/ln, 5) for x in n)
        ni = normals.setdefault(n, len(normals) + 1)
        idx = []
        for p, t in zip(pts, tex):
            qi = coords.setdefault(tuple(round(x, 5) for x in p), len(coords) + 1)
            ti = uvs.setdefault((round(t[0], 5), round(t[1], 5)), len(uvs) + 1)
            idx.append(f'{qi}/{ti}/{ni}')
        out_faces.append('f ' + ' '.join(idx))
    lines = ['# ' + note, f'mtllib {mtl}.mtl', 'o ' + name, 's off']
    lines += ['v %g %g %g' % p for p in coords] + ['vt %g %g' % t for t in uvs] + ['vn %g %g %g' % n for n in normals]
    lines += [f'usemtl {mtl}'] + out_faces
    _save(os.path.join(MODELS, name + '.obj'), '\n'.join(lines) + '\n')
    return LOCAL + name + '.obj'


def quad(name, w, h, texture, emissive=0.0, repeat=(1, 1), double=False, note=None):
    """A w x h picture facing -Z (the crowd) at identity, pivot at its centre."""
    write_mtl(name, texture, emissive)
    ru, rv = repeat
    face = [((-w/2, -h/2, 0), (0, 0)), ((w/2, -h/2, 0), (ru, 0)), ((w/2, h/2, 0), (ru, rv)), ((-w/2, h/2, 0), (0, rv))]
    return write_obj(name, [face], note or f'Food Court: {texture} on a {w} x {h} m card. Faces -Z.', double=double)


def floor_quad(name, x0, x1, z0, z1, texture, metres=2.0):
    write_mtl(name, texture)
    ru, rv = (x1 - x0) / metres, (z1 - z0) / metres
    face = [((x0, 0, z0), (0, 0)), ((x0, 0, z1), (0, rv)), ((x1, 0, z1), (ru, rv)), ((x1, 0, z0), (ru, 0))]
    return write_obj(name, [face], f'Food Court: tiled floor, {texture} every {metres} m. Faces up.')


def disc(name, radius, texture, sides=28):
    """A drumhead: a disc facing -Z, its texture's inscribed circle mapped on, pivot at the bottom."""
    write_mtl(name, texture)
    ring = []
    for i in range(sides):
        a = 2 * math.pi * i / sides
        ring.append(((radius * math.cos(a), radius + radius * math.sin(a), 0), (.5 + .48 * math.cos(a), .5 + .48 * math.sin(a))))
    centre = ((0, radius, 0), (.5, .5))
    faces = [[centre, ring[i], ring[(i + 1) % sides]] for i in range(sides)]
    return write_obj(name, faces, f'Food Court: the signed kick head ({texture}), {2*radius:.2f} m across. Faces -Z.')
