"""Highway to the Afterlife's set: the textures, the prop meshes and the effects the three venues
are dressed with (make_story_afterlife.py). Built with story_afterlife_mesh; each venue gets its
own copies under Assets/Venues/<venue>/Models/Set and /Textures, so a venue stands alone.

A prop function returns the model's asset path; model() places it, with mat() to override its
material (a glow, see-through, additive light).
"""
import json
import math
import os
import random

from story_afterlife_mesh import (FONT, Mesh, Tile, add, cells, ink_uv, lerp, mix, mul, palette_png, part, rot, save_bytes, smooth,  # noqa: F401
                                  sub, text_mask, texture, unit, write_mtl, fbm3)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
_BYTES = {}     # texture name -> its PNG bytes (drawn once, copied to each venue)
_MESHES = {}    # (venue, name) -> asset path


def _folder(venue, sub_):
    return os.path.join(ROOT, 'Assets', 'Venues', venue, sub_)


# ---- textures -------------------------------------------------------------------------------
SUN_U, SUN_V = 0.68, 0.6     # where the heaven sky's sun sits (sky_dome's u, v)


def _draw(name, path):
    S = 256
    if name == 'Asphalt':
        n, fine, cr = Tile(S, 11, 4, 5), Tile(S, 12, 64, 2), cells(S, 13, 5)

        def f(x, y):
            v = 0.035 + 0.035 * n.at(x, y) + 0.03 * fine.at(x, y)
            return (v, v, v * 1.06)
    elif name == 'Rock':
        n, c = Tile(S, 21, 4, 6), cells(S, 22, 7)

        def f(x, y):
            d1, edge = c(x, y)
            v = 0.07 + 0.16 * n.at(x, y) + 0.06 * d1
            if edge < 0.06:
                v *= 0.55
            strata = 0.85 + 0.15 * math.sin((y + 30 * n.at(x, y)) * 0.2)
            return (v * 1.15 * strata, v * 0.85 * strata, v * 0.8 * strata)
    elif name in ('HellFloor', 'HellGlow'):
        n, c, big = Tile(S, 31, 4, 5), cells(S, 32, 6), Tile(S, 33, 2, 2)

        def f(x, y):
            wx, wy = x + 10 * n.at(x, y + 50), y + 10 * n.at(x + 70, y)
            d1, edge = c(wx, wy)
            heat = smooth(0.42, 0.7, big.at(x, y))
            if name == 'HellGlow':
                g = (1 - smooth(0.0, 0.09, edge)) * (0.25 + 0.75 * heat)
                return (g, g * 0.32, g * 0.04)
            v = 0.05 + 0.09 * n.at(x, y) + 0.05 * d1
            if edge < 0.05:
                v *= 0.3
            return (v * 1.25, v * 0.8, v * 0.75)
    elif name == 'Lava':
        n, m = Tile(S, 41, 4, 5), Tile(S, 42, 8, 4)

        def f(x, y):
            w = n.at(x + 40 * m.at(x, y), y + 40 * m.at(y, x))
            crust = smooth(0.42, 0.62, w)
            hot = mix((1.0, 0.75, 0.2), (1.0, 0.22, 0.02), smooth(0.2, 0.45, w))
            return mix(hot, (0.10, 0.015, 0.01), crust)
    elif name == 'Marble':
        n, m = Tile(S, 51, 4, 5), Tile(S, 52, 8, 3)

        def f(x, y):
            vein = abs(math.sin((x + y * 0.6) * 0.045 + 7 * n.at(x, y)))
            v = 0.86 + 0.08 * m.at(x, y)
            c = (v, v, v * 0.98)
            c = mix((0.55, 0.52, 0.5), c, smooth(0.0, 0.12, vein))
            gold = abs(math.sin((x * 0.5 - y) * 0.03 + 9 * m.at(y, x)))
            return mix((0.9, 0.68, 0.25), c, smooth(0.0, 0.035, gold))
    elif name == 'Sky':
        n = Tile(S, 61, 4, 5)

        def f(x, y):
            v = 1 - y / (S - 1)     # 0 at the bottom of the dome, 1 at the zenith (v = 1 is the image's top row)
            c = mix((1.0, 0.86, 0.6), (0.52, 0.72, 1.0), smooth(0.36, 0.56, v))
            c = mix(c, (0.1, 0.2, 0.55), smooth(0.6, 1.0, v))
            c = mix((0.8, 0.8, 0.86), c, smooth(0.0, 0.36, v))
            streak = smooth(0.5, 0.75, n.at(x, y * 5)) * (1 - smooth(0.4, 0.75, v)) * smooth(0.3, 0.4, v)
            c = mix(c, (1.0, 0.97, 0.9), 0.7 * streak)
            # The sun: at u = SUN_U round the dome, v = SUN_V up it (the dome's u wraps once).
            du = min(abs(x / S - SUN_U), 1 - abs(x / S - SUN_U)) * 2.2
            d = math.hypot(du, (v - SUN_V))
            sun = max(0.0, 1 - d / 0.02) ** 0.5 * 3.0 + max(0.0, 1 - d / 0.16) ** 3 * 0.7 + max(0.0, 1 - d / 0.5) ** 2 * 0.2
            return (c[0] + sun, c[1] + sun * 0.93, c[2] + sun * 0.75)
    elif name == 'Night':
        n = Tile(S, 71, 4, 4)
        from story_afterlife_mesh import _hash

        def f(x, y):
            v = 1 - y / (S - 1)
            glow = (1 - smooth(0.3, 0.5, v))
            c = mix((0.004, 0.006, 0.014), (0.05, 0.035, 0.05), glow * (0.4 + 0.6 * n.at(x, 0)))
            return c
    elif name == 'Puff':
        n = Tile(S, 81, 4, 5)

        def f(x, y):
            d = math.hypot(x - S / 2, y - S / 2) / (S / 2)
            a = (1 - smooth(0.15, 1.0, d)) * smooth(0.2, 0.75, n.at(x, y) + 0.35 * (1 - d))
            return (1, 1, 1, a)
    elif name == 'Earth':
        S = EARTH_PIXELS

        def f(x, y):
            return earth_at(x + 0.5, y + 0.5)[0]
    elif name == 'Glow':
        def f(x, y):
            d = math.hypot(x - S / 2 + 0.5, y - S / 2 + 0.5) / (S / 2)
            g = max(0.0, 1 - d) ** 2.2
            return (g, g, g)
    elif name == 'Ray':
        n = Tile(S, 91, 16, 3)

        def f(x, y):
            across = 1 - abs(x / (S - 1) * 2 - 1)
            along = 1 - y / (S - 1)       # v: 0 at the source, 1 at the far end
            g = (across ** 1.6) * (1 - along) ** 1.2 * (0.6 + 0.4 * n.at(x, 0))
            return (g, g, g)
    elif name == 'Banner':
        n = Tile(S, 95, 8, 4)
        star = []
        for k in range(5):
            a0 = math.radians(90 + 180 + k * 144)
            a1 = math.radians(90 + 180 + (k + 1) * 144)
            star.append(((128 + 70 * math.cos(a0), 110 - 70 * math.sin(a0)), (128 + 70 * math.cos(a1), 110 - 70 * math.sin(a1))))

        def f(x, y):
            c = mix((0.42, 0.02, 0.03), (0.2, 0.01, 0.02), n.at(x, y))
            d = abs(math.hypot(x - 128, y - 110) - 84)
            for (ax, ay), (bx, by) in star:
                t = max(0, min(1, ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2)))
                d = min(d, math.hypot(x - ax - t * (bx - ax), y - ay - t * (by - ay)))
            if d < 4.5:
                c = (0.95, 0.7, 0.2)
            if y > 236 and (x // 16) % 2:
                c = (0.95, 0.7, 0.2)
            return c
    elif name in ('Billboard', 'BillboardHell', 'RoadWork', 'MileMarker', 'Emergency'):
        if name == 'Emergency':
            lit, bg, fg, small = text_mask(['EMERGENCY'], S, S, 4), (0.6, 0.03, 0.03), (0.95, 0.95, 0.95), set()
        elif name == 'BillboardHell':
            lit, bg, fg, small = text_mask(['HELL', 'IS REAL'], S, S, 5), (0.012, 0.012, 0.012), (0.95, 0.95, 0.95), set()
        elif name == 'RoadWork':
            lit, bg, fg, small = text_mask(['ROAD', 'WORK', 'AHEAD'], S, S, 6), (0.95, 0.42, 0.04), (0.02, 0.02, 0.02), set()
        elif name == 'Billboard':
            lit, bg, fg = text_mask(['PREPARE', 'TO MEET GOD'], S, S, 3), (0.02, 0.03, 0.12), (0.95, 0.93, 0.8)
            small = text_mask(['', '', '', '', '', 'NEXT EXIT'], S, S, 2)
        else:
            lit, bg, fg, small = text_mask(['MILE', '66'], S, S, 7), (0.03, 0.22, 0.09), (0.92, 0.92, 0.9), set()

        def f(x, y):
            if (x, y) in lit:
                return fg
            if (x, y) in small:
                return (0.95, 0.75, 0.2)
            if min(x, y, S - 1 - x, S - 1 - y) in (6, 7, 8):
                return fg
            return bg
    elif name == 'Innocent':
        # The sheet the cop is shown at the crash site (My Hero): a line or two of a typed
        # dispatch, and across the middle of it, as tall as will go, the one word.
        typed = text_mask(['STATE POLICE DISPATCH', '', 'RE. PURSUIT MILE 66', '', '', '', '', '', '', '', '',
                           'WRONG VEHICLE', 'CALL OFF PURSUIT', ''], S, S, 2)
        word, px, py = set(), 5, 11
        for ci, ch in enumerate('INNOCENT'):
            bits = FONT[ch]
            for r in range(7):
                for c in range(5):
                    if bits[r * 5 + c] == '1':
                        for dy in range(py):
                            for dx in range(px):
                                word.add((10 + (ci * 6 + c) * px + dx, 92 + r * py + dy))

        def f(x, y):
            if (x, y) in word:
                return (0.5, 0.0, 0.0)
            if 78 <= y <= 182 and (y < 83 or y > 177):
                return (0.5, 0.0, 0.0)
            if (x, y) in typed:
                return (0.2, 0.2, 0.22)
            return (0.93, 0.92, 0.86)
    else:
        raise KeyError(name)
    texture(path, S, f, alpha=(name == 'Puff'))


def tex(venue, name):
    """The texture's asset path in the venue (drawn on first use)."""
    path = os.path.join(_folder(venue, 'Textures'), 'AL_' + name + '.png')
    if name not in _BYTES:
        if name == 'Palette':
            palette_png(path)
        else:
            _draw(name, path)
        _BYTES[name] = open(path, 'rb').read()
    else:
        save_bytes(path, _BYTES[name])
    return f'Assets/Venues/{venue}/Textures/AL_{name}.png'


def _write(venue, mesh, texture_name='Palette'):
    """Write a mesh into the venue with its material library; returns the model's asset path."""
    folder = _folder(venue, os.path.join('Models', 'Set'))
    tex(venue, texture_name)
    write_mtl(folder, 'AL_' + texture_name, f'../../Textures/AL_{texture_name}.png')
    return f'Assets/Venues/{venue}/Models/Set/' + mesh.write(folder, 'AL_' + texture_name)


def prop(venue, name, build, texture_name='Palette', smooth_=False):
    """A prop's asset path in the venue: build(mesh) fills it the first time."""
    key = (venue, name)
    if key not in _MESHES:
        m = Mesh(name, smooth_)
        build(m)
        _MESHES[key] = (_write(venue, m, texture_name), texture_name)
    return _MESHES[key][0]


# ---- placing --------------------------------------------------------------------------------
def mat(venue, texture_name='Palette', color=(1, 1, 1), glow=None, power=1.0, glow_tex=True, opacity=None, additive=False,
        rough=0.9, metallic=0.0, both=False, tiling=None):
    """A StandardMaterial for a model part. glow: the emissive colour (through the texture when
    glow_tex: True the diffuse texture, or another texture's name). opacity / additive: see-through."""
    m = {'Type': 'StandardMaterial', 'DiffuseColor': [round(float(c), 4) for c in color], 'Roughness': rough, 'Metallic': metallic}
    if texture_name:
        m['Textures'] = {'Diffuse': {'Path': tex(venue, texture_name)}}
    if glow is not None:
        if glow_tex and texture_name:
            m['Textures']['Emissive'] = {'Path': tex(venue, glow_tex if isinstance(glow_tex, str) else texture_name)}
        m['EmissiveColor'] = [round(float(c), 4) for c in glow]
        m['EmissiveIntensity'] = round(float(power), 4)
    if opacity is not None or additive:
        m['RenderMode'] = 1
        m['BlendMode'] = 2 if additive else 0
        m['Opacity'] = 1.0 if opacity is None else round(float(opacity), 4)
    if both:
        m['FaceMode'] = 2
    if tiling:
        m['Tiling'] = [float(tiling[0]), float(tiling[1])]
    return m


def model(s, parent, name, path, pos=(0, 0, 0), euler=(0, 0, 0), scale=1.0, material=None, shadows=True):
    sc = scale if isinstance(scale, (tuple, list)) else (scale, scale, scale)
    e = s.entity(name, parent, pos, euler, sc)
    comp = {'Type': 'Model', 'ModelPath': path}
    if material is not None or not shadows:
        p = {'CastShadows': bool(shadows) and material is not None and material.get('RenderMode') != 1}
        if material is not None:
            p['Material'] = material
        comp['Compact'] = True
        comp['Parts'] = {part(os.path.basename(path)): p}
    e.add(comp)
    return e


def light_card(venue):
    """A unit quad facing +z (uv across it) for additive glows: flares, the sun, halos."""
    return prop(venue, 'GlowCard', lambda m: m.card((-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)), 'Glow')


def glow_card(s, parent, venue, name, pos, size, color, power, euler=(0, 0, 0)):
    return model(s, parent, name, light_card(venue), pos, euler, (size, size, 1),
                 mat(venue, 'Glow', (0, 0, 0), glow=color, power=power, additive=True, both=True), shadows=False)


def headlights(s, parent, x, y, z, level, reach, inner=16, outer=36, name='Headlight'):
    """A vehicle's two headlight beams, one from each lamp at (-x and +x, y, z), sharing level
    between them: a single light on the centre line shines out of the grille."""
    for side, dx in (('left', -x), ('right', x)):
        s.light(f'{name} {side}', parent, (dx, y, z), 'Spot', (1.0, 0.95, 0.85), level / 2, reach, rot=(5, 0, 0), inner=inner, outer=outer)


def ray(venue):
    """A shaft of light: two crossed quads from the origin along +z, 1 long and 1 wide at the far end."""
    def build(m):
        for a in (0, 90):
            c, sn = math.cos(math.radians(a)), math.sin(math.radians(a))
            m.face([(-0.12 * c, -0.12 * sn, 0), (0.12 * c, 0.12 * sn, 0), (0.5 * c, 0.5 * sn, 1), (-0.5 * c, -0.5 * sn, 1)],
                   uvs=[(0, 0), (1, 0), (1, 1), (0, 1)], both=True)
    return prop(venue, 'Ray', build, 'Ray')


def shaft(s, parent, venue, name, a, b, width, color, power):
    """A light shaft from a to b, width across at b."""
    from venuegen import look_rotation
    return model(s, parent, name, ray(venue), a, look_rotation(a, b), (width, width, math.dist(a, b)),
                 mat(venue, 'Ray', (0, 0, 0), glow=color, power=power, additive=True, both=True), shadows=False)


def particles(s, parent, name, pos, euler=(0, 0, 0), **kw):
    e = s.entity(name, parent, pos, euler)
    comp = {'Type': 'ParticleSystem', 'Simulation': 'CPU', 'SimulationSpace': 'World', 'Looping': True, 'SoftParticleDistance': 0}
    comp.update(kw)
    e.add(comp)
    return e


def fire_fx(s, parent, venue, name, pos, size=1.0, smoke=True):
    """Flames, sparks and (smoke) a column of black smoke at pos."""
    particles(s, parent, name + ' flames', pos, Shape='Cone', ConeAngle=14, ShapeRadius=0.45 * size, Lifetime=[0.5, 1.1], Speed=[1.2 * size, 3.0 * size],
              Size=[0.5 * size, 1.1 * size], EndSize=0.25, StartColor=[1.0, 0.75, 0.25], StartColor2=[1.0, 0.45, 0.08], EndColor=[0.7, 0.08, 0.01],
              StartAlpha=0.9, EndAlpha=0.0, FadeIn=0.12, Intensity=2.6, Gravity=-0.35, Drag=0.4, NoiseStrength=0.9, NoiseFrequency=1.4,
              Blend='Additive', EmissionRate=38, MaxParticles=90, Texture=tex(venue, 'Puff'))
    particles(s, parent, name + ' sparks', pos, Shape='Cone', ConeAngle=30, ShapeRadius=0.4 * size, Lifetime=[1.2, 3.0], Speed=[2.0, 6.0],
              Size=[0.03, 0.07], EndSize=0.4, StartColor=[1.0, 0.8, 0.35], StartColor2=[1.0, 0.5, 0.1], EndColor=[0.8, 0.15, 0.02], Intensity=5.0,
              Gravity=-0.12, Drag=0.25, NoiseStrength=1.6, NoiseFrequency=0.8, Blend='Additive', EmissionRate=22, MaxParticles=90,
              Alignment='Stretched', StretchFactor=0.08, FadeIn=0.02)
    if smoke:
        particles(s, parent, name + ' smoke', (pos[0], pos[1] + 1.2 * size, pos[2]), Shape='Cone', ConeAngle=10, ShapeRadius=0.5 * size,
                  Lifetime=[5.0, 8.0], Speed=[1.6, 2.6], Size=[1.2 * size, 2.0 * size], EndSize=4.5, StartColor=[0.09, 0.07, 0.06],
                  StartColor2=[0.16, 0.1, 0.07], EndColor=[0.03, 0.03, 0.035], StartAlpha=0.75, EndAlpha=0.0, FadeIn=0.15, Intensity=1.0,
                  Gravity=-0.05, Drag=0.15, NoiseStrength=0.7, NoiseFrequency=0.25, Blend='Alpha', Lit=False, EmissionRate=7, MaxParticles=70,
                  Texture=tex(venue, 'Puff'), AngularVelocity=[-20, 20])


def tailpipe(kind=None):
    """Where a police car's exhaust comes out (the patrol cruiser's, or kind's of the fleet): under
    the back bumper on the passenger's side. (None of the models has a pipe: this is where one
    would be.)"""
    facts = VEHICLES[kind or 'PatrolCruiser']
    if kind:
        return (round(0.6 * facts['Max'][0], 3), 0.4, round(facts['Min'][2] + 0.05, 3))
    return (round(0.57 * _PS, 3), round(0.3 * _PS, 3), round(-2.66 * _PS, 3))


def exhaust(s, parent, venue, at, name='Exhaust', size=1.0, alpha=0.5):
    """The exhaust of a vehicle at speed, from at under parent (its group, facing +z): pale puffs
    blown straight back down the road, swelling and thinning out over about five metres. On the
    afterlife's roads the vehicles stand and the road goes by, so the trail is what says which end
    is the back. Lit, so it shows in the headlights and beacons of whatever follows (alpha: thinner
    where those are bright). Under a story group it stops with the group."""
    return particles(s, parent, name, at, (-86, 0, 0), Shape='Cone', ConeAngle=5, ShapeRadius=0.04 * size, Lifetime=[0.45, 0.75], Speed=[7, 10],
                     Size=[0.2 * size, 0.3 * size], EndSize=4.5, StartColor=[0.8, 0.8, 0.82], StartColor2=[0.6, 0.6, 0.63], EndColor=[0.5, 0.5, 0.52],
                     StartAlpha=alpha, EndAlpha=0.0, FadeIn=0.08, Intensity=1.0, Gravity=-0.04, Drag=0.1, NoiseStrength=0.5, NoiseFrequency=0.8,
                     Blend='Alpha', Lit=True, EmissionRate=40, MaxParticles=48, Texture=tex(venue, 'Puff'), AngularVelocity=[-40, 40])


# ---- shared prop parts ----------------------------------------------------------------------
def _wheel(m, c, r=0.55, w=0.4, axis='x'):
    m.lathe(c, [(r * 0.5, -w / 2), (r, -w * 0.42), (r, w * 0.42), (r * 0.5, w / 2)], 'rubber', 12, axis)
    m.lathe(c, [(r * 0.5, -w / 2 - 0.01), (r * 0.5, w / 2 + 0.01)], 'steel', 8, axis)


def _tractor(m):
    """A highway tractor facing +z, on the ground, its fifth wheel over z = -3."""
    m.box((0, 0.75, -1.2), (1.9, 0.35, 7.4), 'steel_dark')
    m.box((0, 1.7, 2.45), (2.0, 1.3, 2.3), 'cab_red', taper=0.92)
    m.box((0, 1.55, 3.63), (1.5, 1.05, 0.08), 'chrome')
    for i in range(6):
        m.box((-0.6 + i * 0.24, 1.55, 3.68), (0.05, 0.95, 0.04), 'steel_dark')
    m.box((0, 0.72, 3.75), (2.6, 0.38, 0.32), 'chrome')
    for x in (-0.95, 0.95):
        m.box((x, 1.15, 3.66), (0.4, 0.25, 0.08), 'lamp')
        m.box((x * 1.32, 1.05, 2.5), (0.5, 0.12, 1.5), 'cab_dark')
        m.lathe((x * 1.3, 0.95, 0.0), [(0.36, -0.9), (0.42, -0.8), (0.42, 0.8), (0.36, 0.9)], 'chrome', 10, 'z')
        m.tube([(x * 1.38, 0.9, -0.55), (x * 1.38, 4.3, -0.55), (x * 1.38, 4.75, -0.75)], [0.11, 0.11, 0.12], 'chrome', 8)
        m.box((x * 1.34, 2.5, 1.2), (0.06, 0.4, 0.25), 'chrome')
    m.box((0, 2.45, 0.45), (2.5, 2.2, 1.9), 'cab_red')
    m.box((0, 2.85, 1.42), (2.2, 0.85, 0.06), 'glass')
    for x in (-1.26, 1.26):
        m.box((x, 2.85, 0.6), (0.04, 0.75, 1.1), 'glass')
    m.box((0, 3.75, 0.2), (2.3, 0.5, 2.2), 'cab_red', taper=0.7)
    m.box((0, 2.6, -1.3), (2.5, 2.5, 1.6), 'cab_dark')
    for i in range(5):
        m.box((-0.8 + i * 0.4, 3.72, 1.2), (0.12, 0.1, 0.1), 'lamp')
    m.lathe((0, 1.0, -3.0), [(0.6, 0), (0.6, 0.08)], 'steel', 10)
    for x in (-1.12, 1.12):
        _wheel(m, (x, 0.55, 2.55))
        for z in (-2.3, -3.6):
            _wheel(m, (x, 0.55, z), w=0.7)


def _flatbed(m, wheels=False):
    """The flatbed the band rides: its deck top at y = 1.25, from z = -1.2 to 9."""
    m.box((0, 1.1, 3.9), (6.0, 0.3, 10.2), 'deck')
    for i in range(9):
        m.box((-2.7 + i * 0.675, 1.252, 3.9), (0.03, 0.005, 10.2), 'deck_dark')
    m.box((0, 0.88, 3.9), (6.1, 0.16, 10.3), 'steel')
    for x in (-0.9, 0.9):
        m.box((x, 0.65, 3.9), (0.25, 0.4, 10.0), 'steel_dark')
    for z in (-0.6, 2.0, 4.6, 7.2):
        m.box((0, 0.7, z), (5.6, 0.2, 0.15), 'steel_dark')
    m.box((0, 0.85, -1.27), (5.6, 0.14, 0.06), 'red_lamp')
    for x in (-2.7, 2.7):
        m.box((x, 0.45, -1.05), (0.5, 0.7, 0.04), 'rubber')
        for z in (0.3, 2.7, 5.1, 7.5):
            m.box((x * 1.12, 0.92, z), (0.06, 0.08, 0.12), 'cone')
    if wheels:
        for z in (0.0, 1.3, 6.0, 7.3):
            for x in (-2.6, 2.6):
                _wheel(m, (x, 0.55, z))


def _truss(m, bent=0.0):
    """The lighting goalpost at the back of the deck (z = 8.5); bent leans and twists it."""
    for x in (-2.82, 2.82):
        top = (x + bent * 1.5, 5.25 - abs(bent) * 0.6, 8.5 + bent * 1.2)
        for dx, dz in ((-0.1, -0.1), (0.1, -0.1), (0.1, 0.1), (-0.1, 0.1)):
            m.tube([(x + dx, 1.25, 8.5 + dz), (top[0] + dx, top[1], top[2] + dz)], 0.03, 'steel', 5)
        for k in range(8):
            y0, y1 = 1.25 + k * 0.5, 1.75 + k * 0.5
            t0, t1 = k / 8, (k + 1) / 8
            a = lerp((x, 1.25, 8.5), top, t0)
            b = lerp((x, 1.25, 8.5), top, t1)
            sgn = 1 if k % 2 else -1
            m.tube([(a[0] - 0.1 * sgn, a[1], a[2] - 0.1), (b[0] + 0.1 * sgn, b[1], b[2] - 0.1)], 0.018, 'steel', 4)
    for dy in (-0.1, 0.1):
        for dz in (-0.1, 0.1):
            m.tube([(-2.82 + bent * 1.5, 5.25 - abs(bent) * 0.6 + dy, 8.5 + bent * 1.2 + dz), (2.82 + bent * 1.5, 5.25 - abs(bent) * 0.6 + dy - bent * 0.8, 8.5 + bent * 1.2 + dz)],
                   0.03, 'steel', 5)
    for i, x in enumerate((-2.0, -0.7, 0.7, 2.0)):
        m.lathe((x + bent * 1.5, 5.0 - abs(bent) * 0.6 - bent * 0.8 * (x + 2.82) / 5.64, 8.4 + bent * 1.2), [(0.12, -0.2), (0.17, 0.1), (0.0, 0.1)], 'black', 8)


def tractor(venue):
    return prop(venue, 'Tractor', _tractor)


def flatbed(venue):
    def build(m):
        _flatbed(m)
        _truss(m)
        for x in (-1.2, 1.2):
            m.box((x, 1.5, -0.6), (0.7, 0.45, 0.55), 'amp', euler=(-25, 0, 0))
            m.box((x, 1.53, -0.84), (0.6, 0.35, 0.04), 'grille', euler=(-25, 0, 0))
        for x, z in ((-2.3, 6.6), (2.3, 6.6)):
            m.box((x, 2.0, z), (0.8, 1.5, 0.45), 'amp')
            m.box((x, 2.0, z - 0.24), (0.7, 1.35, 0.03), 'grille')
            m.box((x, 2.95, z), (0.75, 0.35, 0.4), 'amp')
    return prop(venue, 'Flatbed', build)


def wheel(venue):
    return prop(venue, 'Wheel', lambda m: _wheel(m, (0, 0, 0)))


# The patrol cruiser (Assets/Models/CopCar, exported from its .blend by export_patrol_cruiser.py):
# 5.9 m long facing +z (a tenth larger than modelled, like the fleet), its wheels on y = 0, the
# driver's side at -x. One model for all three venues.
def patrol_cruiser(s, parent, name='Body', door_open=False):
    """The patrol cruiser's model under parent: drawn by the Model itself, a part for each material."""
    e = s.entity(name, parent)
    e.add({'Type': 'Model', 'ModelPath': 'Assets/Models/CopCar/PatrolCruiser%s.fbx' % ('DoorOpen' if door_open else ''), 'Compact': True})
    return e


# The highway fleet (Assets/Models/Vehicles, exported from Art/Vehicles by export_vehicles.py): the
# traffic (Caprice, Civic, Corvette, Caravan, C10), the police (TrailDuster, Ranger) and the police
# helicopters (JetRanger, AS350, each with a Rotor and a TailRotor model to spin). Each faces +z
# with its wheels or skids on y = 0 and the driver's side at -x. The export writes where each
# one's lamps, beacons, steering wheel and rotor hubs are: VEHICLES[kind], the +x side's for a pair.
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'story_vehicles.json'), encoding='utf-8') as _f:
    VEHICLES = json.load(_f)
TRAFFIC = ('Caprice', 'Civic', 'Corvette', 'Caravan', 'C10')
# The patrol cruiser's own (its export writes Scale, Seat, Heel and SteeringWheel; the lamps are
# as modelled, times the scale it is exported at).
_PS = VEHICLES['PatrolCruiser']['Scale']
PATROL_HEADLAMP = (round(0.71 * _PS, 3), round(0.78 * _PS, 3), round(2.66 * _PS, 3))
PATROL_TAIL_LAMP = (round(0.58 * _PS, 3), round(0.81 * _PS, 3), round(-2.6 * _PS, 3))
PATROL_BEACON = (round(0.513 * _PS, 3), round(1.74 * _PS, 3), round(-0.2 * _PS, 3))


def vehicle(s, parent, kind, name='Body'):
    """One of the fleet's models under parent (kind: a VEHICLES key, or a helicopter's with Rotor
    or TailRotor after it): drawn by the Model itself, a part for each material."""
    e = s.entity(name, parent)
    e.add({'Type': 'Model', 'ModelPath': f'Assets/Models/Vehicles/{kind}.fbx', 'Compact': True})
    return e


def rolling_part(s, parent, kind, part, name, rot=(0, 0, 0)):
    """A driving police car's model under parent (kind: None the patrol cruiser, or TrailDuster;
    part: Rolling, the body without wheels and the driver's window down, or Wheel, the driver's
    side front wheel about its hub)."""
    e = s.entity(name, parent, (0, 0, 0), rot)
    path = f'Assets/Models/Vehicles/{kind}{part}.fbx' if kind else f'Assets/Models/CopCar/PatrolCruiser{part}.fbx'
    e.add({'Type': 'Model', 'ModelPath': path, 'Compact': True})
    return e


def lamp(kind, which):
    """Where kind's Headlamp or TailLamp is on its +x side (mirror x for the other)."""
    facts = VEHICLES[kind]
    if which in facts:
        return tuple(facts[which])
    # The Corvette's headlamps are folded away: light it from where they would stand, over the
    # indicators.
    x, y, z = facts['Indicator']
    return (x, y + 0.14, z)


def vehicle_lamps(s, parent, venue, kind, head=1.5, tail=1.0, hazard=False):
    """The glare on kind's four lamps (its lenses glow on their own): the level of each pair, 0 to
    leave one out. hazard: the tail pair amber."""
    hx, hy, hz = lamp(kind, 'Headlamp')
    tx, ty, tz = lamp(kind, 'TailLamp')
    for side in (-1, 1):
        if head > 0:
            glow_card(s, parent, venue, 'Headlight glare', (side * hx, hy, hz + 0.05), 0.5, (1.0, 0.95, 0.8), head)
        if tail > 0:
            glow_card(s, parent, venue, 'Hazard glare' if hazard else 'Tail lamp glare', (side * tx, ty, tz - 0.04), 0.34,
                      (1.0, 0.5, 0.05) if hazard else (1.0, 0.05, 0.05), tail, (0, 180, 0))


def semi(venue):
    """A tractor and box trailer facing +z, 17 m long, its middle on the origin."""
    def build(m):
        t = Mesh('t')
        _tractor(t)
        m.merge(t, (0, 0, 4.6))
        m.box((0, 2.75, -3.2), (2.6, 3.0, 11.0), 'white')
        m.box((0, 1.1, -3.2), (2.4, 0.3, 11.0), 'steel_dark')
        m.box((0, 2.6, -8.72), (2.3, 2.6, 0.04), 'steel')
        for x in (-1.1, 1.1):
            for z in (-6.2, -7.5):
                _wheel(m, (x, 0.55, z), w=0.7)
            m.box((x, 1.0, -8.74), (0.3, 0.16, 0.04), 'red_lamp')
    return prop(venue, 'Semi', build)


def overpass(venue, half=22.0):
    """A road bridge across the highway at z = 0: deck from y = 7.2, piers outside the shoulders."""
    def build(m):
        m.box((0, 7.9, 0), (half * 2, 1.4, 9.0), 'steel_dark')
        m.box((0, 7.15, 0), (half * 2, 0.12, 8.0), 'soot')
        for z in (-4.4, 4.4):
            m.box((0, 9.0, z), (half * 2, 0.9, 0.3), 'post')
        for x in (-13.6, 13.6, -half + 0.8, half - 0.8):
            m.box((x, 3.6, 0), (1.4, 7.2, 5.0), 'post', taper=0.85)
        for x in (-7.0, 0.0, 7.0):
            m.box((x, 7.06, 0), (0.5, 0.06, 6.0), 'lamp')
        m.box((6.5, 8.2, -4.56), (7.0, 1.6, 0.06), 'sign_green')
    return prop(venue, 'Overpass', build)

def work_zone(venue, width=9.6, length=12.0, height=1.7):
    """Road works in the middle lanes, what the rig takes off from: a ramp of spoil under steel
    plates, its foot across z = 0 and its lip height up at z = length (the rig comes at it from
    -z), the heap falling away behind the lip, a line of barrels down each side leading up to it,
    an excavator parked beyond on the left and two lighting masts on that side. Its lamps and signs are
    the venue's own."""
    def build(m):
        w = width / 2
        m.face([(-w, 0.02, 0), (w, 0.02, 0), (w, height, length), (-w, height, length)], 'steel', outward=(0, 1, 0))
        for k in range(1, 4):       # the plates' joints
            z = length * k / 4
            y = 0.02 + (height - 0.02) * k / 4 + 0.012
            m.face([(-w, y, z - 0.05), (w, y, z - 0.05), (w, y + 0.014, z + 0.05), (-w, y + 0.014, z + 0.05)], 'steel_dark', outward=(0, 1, 0))
        for sx in (-1, 1):
            m.face([(sx * w, 0, 0), (sx * w, height, length), (sx * w, 0, length)], 'deck_dark', outward=(sx, 0, 0))
            m.face([(sx * w, height, length), (sx * w, 0, length + 3.5), (sx * w, 0, length)], 'deck_dark', outward=(sx, 0, 0))
            # A yellow kerb up each edge of the plates.
            m.face([(sx * w, 0.05, 0), (sx * (w - 0.3), 0.05, 0), (sx * (w - 0.3), height + 0.03, length), (sx * w, height + 0.03, length)], 'hivis', outward=(0, 1, 0))
            # Spoil heaped against the sides.
            for k, (z, r) in enumerate(((length * 0.45, 1.0), (length * 0.8, 1.4), (length + 1.5, 1.3))):
                m.blob((sx * (w + 0.7), 0.1, z), r, 'deck_dark', 1, 0.3, 1.0, 40 + k + (7 if sx > 0 else 0), (0.9, 0.55, 1.5), floor=0.0)
            # Barrels down each side, from 100 m out.
            for k in range(11):
                x, z = sx * (w + 0.55), -4.0 - k * 9.6
                m.lathe((x, 0, z), [(0.3, 0.0), (0.33, 0.45), (0.29, 1.0)], 'cone', 8)
                m.lathe((x, 0, z), [(0.335, 0.5), (0.335, 0.66)], 'white', 8)
                m.box((x, 0.03, z), (0.8, 0.06, 0.8), 'rubber')
        m.face([(-w, height, length), (w, height, length), (w, 0, length + 3.5), (-w, 0, length + 3.5)], 'deck_dark', outward=(0, 1, 1))
        # Two lighting masts, on the oncoming side (the verge side is where the jump is shot from).
        for z in (1.0, 10.0):
            m.box((-(w + 3.2), 3.6, z), (0.16, 7.2, 0.16), 'post')
            m.box((-(w + 3.2), 0.25, z), (1.6, 0.5, 1.2), 'steel_dark')
            m.box((-(w + 3.0), 7.2, z), (1.5, 0.5, 0.25), 'steel_dark', euler=(0, 20, 0))
        # The excavator: tracks, house, cab, boom, stick and bucket.
        ex, ez = -(w + 4.6), length + 5.0
        for dx in (-1.0, 1.0):
            m.box((ex + dx, 0.4, ez), (0.6, 0.8, 4.2), 'rubber')
        m.box((ex, 1.45, ez - 0.3), (2.5, 1.3, 3.2), 'brass')
        m.box((ex - 0.6, 2.5, ez + 0.6), (1.1, 1.0, 1.4), 'glass')
        m.box((ex + 0.5, 3.4, ez + 2.6), (0.45, 0.55, 4.6), 'brass', euler=(-48, 0, 0))
        m.box((ex + 0.5, 3.9, ez + 5.6), (0.36, 0.42, 3.4), 'brass', euler=(52, 0, 0))
        m.box((ex + 0.5, 2.3, ez + 6.9), (1.0, 0.9, 0.9), 'steel_dark', euler=(25, 0, 0))
    return prop(venue, 'WorkZone', build)


def ambulance(venue):
    def build(m):
        m.box((0, 1.75, -0.6), (2.4, 2.5, 4.6), 'white')
        m.box((0, 1.3, 2.4), (2.3, 1.6, 1.5), 'white', taper=0.9)
        m.box((0, 1.75, 3.0), (2.0, 0.6, 0.06), 'glass', euler=(-20, 0, 0))
        m.box((0, 1.25, -0.6), (2.42, 0.3, 4.62), 'amb_red')
        m.box((0, 2.0, -0.6), (2.42, 0.1, 4.62), 'hivis')
        m.box((0, 0.6, 0), (2.2, 0.3, 6.4), 'steel_dark')
        for x in (-1.1, 1.1):
            for z in (-1.9, 2.3):
                _wheel(m, (x, 0.45, z), 0.45, 0.3)
            m.box((x * 0.75, 0.9, 3.17), (0.4, 0.2, 0.05), 'lamp')
            hinge = (x * 1.2, 1.75, -2.9)
            m.box(add(hinge, rot((-x * 0.55 / 1.1, 0, 0), (0, x * 100, 0))), (1.1, 2.2, 0.06), 'white', euler=(0, x * 100, 0))
        m.box((0, 0.55, -2.4), (2.0, 0.08, 1.2), 'steel')
        m.box((0, 3.05, 2.2), (1.6, 0.14, 0.3), 'black')
    return prop(venue, 'Ambulance', build)


def guardrail(venue, length=96.0, name='Guardrail'):
    """A run of W-beam guardrail along +z from 0, on posts every 2 m."""
    def build(m):
        for k in range(int(length / 2) + 1):
            m.box((0.08, 0.38, k * 2.0), (0.1, 0.76, 0.14), 'post')
        for y, d in ((0.62, 0.0), (0.52, 0.045), (0.72, 0.045)):
            m.box((-0.02 + d, y, length / 2), (0.04, 0.11 if d == 0 else 0.09, length), 'rail')
    return prop(venue, name, build)


def guardrail_torn(venue):
    """The rail where the trailer went through: both ends peeled back, posts knocked flat."""
    def build(m):
        for side in (-1, 1):
            path = [(0, 0.62, side * 7), (0.1, 0.64, side * 5), (0.9, 0.75, side * 3.4), (2.3, 0.5, side * 2.6), (3.0, 0.15, side * 3.0)]
            m.tube(path, 0.16, 'rail', 4, squash=0.2)
            for z in (5.0, 7.0):
                m.box((0.08, 0.38, side * z), (0.1, 0.76, 0.14), 'post')
        for (x, z, yaw) in ((1.4, 1.2, 30), (2.2, -1.0, 100), (0.9, -2.4, 65)):
            m.box((x, 0.07, z), (0.1, 0.76, 0.14), 'post', euler=(88, yaw, 0))
    return prop(venue, 'GuardrailTorn', build)


# The MitchTree recipes (Engine/Assets/Trees) a roadside is planted with: (name, the engine's recipe,
# seed, how often it is picked). Conifers mostly: this was a wall of pines.
ROAD_TREES = (('RoadPineA', 'Pine', 11, 3), ('RoadPineB', 'Pine', 5, 3), ('RoadSpruce', 'Presets/Spruce', 2, 3), ('RoadMaple', 'Maple', 21, 2),
              ('RoadBirch', 'Presets/Birch', 3, 1), ('RoadOak', 'Presets/Oak', 7, 2))
_TREE_HEIGHT = {}       # a recipe's asset path -> its trunk's height at scale 1, metres
TREE_PARTS = ('MitchTree#0/@Bark#0', 'MitchTree#0/@Leaves#0')     # a grown tree's parts in a compact Model


def tree(venue, name, source, seed):
    """A MitchTree recipe in the venue (Engine/Docs/MitchTree.md): one of the engine's with its own
    seed, and a fuller crown (the engine's are first drafts, thin enough to see through: more and
    bigger leaf cards, and some along the limbs). A recipe is a model path: the tree is grown when
    it loads. Returns its asset path."""
    with open(os.path.join(ROOT, 'Engine', 'Assets', 'Trees', source + '.mtree')) as f:
        recipe = json.load(f)
    recipe['Name'], recipe['Seed'] = name, seed
    leaves = recipe['Leaves']
    broad = leaves['Kind'] == 'Broadleaf'
    leaves['PerStem'] = round(leaves['PerStem'] * (2.2 if broad else 1.5))
    leaves['Size'] = round(leaves['Size'] * (1.7 if broad else 1.3), 3)
    leaves['ParentCoverage'] = max(leaves['ParentCoverage'], 0.4 if broad else 0.6)
    save_bytes(os.path.join(ROOT, 'Assets', 'Venues', venue, 'Trees', name + '.mtree'), (json.dumps(recipe, indent=4) + '\n').encode())
    _TREE_HEIGHT[f'Assets/Venues/{venue}/Trees/{name}.mtree'] = recipe['Trunk']['Height']
    return f'Assets/Venues/{venue}/Trees/{name}.mtree'


def plant(s, parent, name, path, pos, yaw=0.0, scale=1.0, shadows=False):
    """A tree (a .mtree recipe's path) standing at pos: one entity, its bark and leaves the Model's
    own parts."""
    e = s.entity(name, parent, pos, (0, yaw, 0), (scale, scale, scale))
    comp = {'Type': 'Model', 'ModelPath': path, 'Compact': True}
    if not shadows:
        comp['Parts'] = {key: {'CastShadows': False} for key in TREE_PARTS}
    e.add(comp)
    return e


def plant_roadside(s, parent, venue, spots, seed=5, name='Tree', shadows=False, tall=(8.0, 13.0)):
    """Trees of the roadside's kinds at spots [(x, y, z)], each turned its own way and between
    tall[0] and tall[1] metres high (the recipes grow taller than that: a crane or a helicopter
    shot looks over a roadside's trees, and must not find itself in one's crown)."""
    kinds = [tree(venue, n, source, sd) for n, source, sd, _ in ROAD_TREES]
    weights = [w for _, _, _, w in ROAD_TREES]
    rng = random.Random(seed)
    for i, at in enumerate(spots):
        kind = rng.choices(kinds, weights)[0]
        plant(s, parent, f'{name} {i + 1}', kind, at, round(rng.uniform(0, 360), 1), round(rng.uniform(*tall) / _TREE_HEIGHT[kind], 3), shadows)


def roadside_spots(z0, z1, near, far, count, seed, period=None, y=-0.3, gap=7.0):
    """Where a roadside's trees stand, both sides of a road along z: between near and far metres
    out from its middle, more of them close to the road, none within gap metres of another.
    period: the pattern is one period long and repeats along z (count is then the trees in one)."""
    rng = random.Random(seed)
    span = period or (z1 - z0)
    base, tries = [], 0
    while len(base) < count and tries < count * 60:
        tries += 1
        x, z = rng.choice((-1, 1)) * (near + (far - near) * rng.random() ** 1.6), rng.random() * span

        def apart(o):
            dz = abs(o[1] - z)
            return math.hypot(o[0] - x, min(dz, span - dz) if period else dz)
        if all(apart(o) >= gap for o in base):
            base.append((x, z))
    copies = int(round((z1 - z0) / period)) if period else 1
    return [(round(x, 2), y, round(z0 + k * span + z, 2)) for k in range(copies) for x, z in base]


# ---- the Earth from above -------------------------------------------------------------------
# The country the highway runs through, for the daylight Free Bird rises into: fields, woods and
# hedges drawn into one texture that repeats every EARTH_TILE metres, and the same function says
# where the woods stand (earth_woods), so that crowns can be stood on them.
EARTH_TILE, EARTH_PIXELS = 1536.0, 512
BELT = (22.0, 84.0)             # the trees along the highway: this far out from its middle, both sides
_EARTH = {}
FIELDS = ((0.085, 0.15, 0.05), (0.11, 0.17, 0.06), (0.06, 0.125, 0.045), (0.27, 0.23, 0.1), (0.15, 0.105, 0.065), (0.2, 0.2, 0.085),
          (0.1, 0.16, 0.055), (0.075, 0.135, 0.05))
WOODS = (0.028, 0.062, 0.03)


def earth_at(px, py):
    """The ground at a pixel of the Earth texture: (colour, how wooded 0..1)."""
    S, N = EARTH_PIXELS, 11
    if not _EARTH:
        _EARTH.update(n=Tile(S, 301, 8, 5), big=Tile(S, 302, 3, 3), fine=Tile(S, 304, 128, 2),
                      pts=[[(_hash2(i, j, 303, 1), _hash2(i, j, 303, 2)) for i in range(N)] for j in range(N)])
    n, big = _EARTH['n'].at(px, py), _EARTH['big'].at(px, py)
    # The fields: Voronoi plots, each its own crop, hedges where two meet.
    u, v = px * N / S, py * N / S
    ci, cj = int(u), int(v)
    d1 = d2 = 9.0
    plot = (0, 0)
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            qx, qy = _EARTH['pts'][(cj + dj) % N][(ci + di) % N]
            d = math.hypot(ci + di + qx - u, cj + dj + qy - v)
            if d < d1:
                d1, d2, plot = d, d1, ((ci + di) % N, (cj + dj) % N)
            elif d < d2:
                d2 = d
    kind = _hash2(plot[0], plot[1], 305, 0)
    c = FIELDS[int(kind * len(FIELDS)) % len(FIELDS)]
    # Rows across a plot (the plough's or the crop's), each plot at its own angle.
    a = _hash2(plot[0], plot[1], 305, 1) * math.pi
    rows = math.sin((px * math.cos(a) + py * math.sin(a)) * 1.9)
    c = mul(c, 0.93 + 0.07 * rows + 0.3 * (n - 0.5) + 0.1 * (_EARTH['fine'].at(px, py) - 0.5))
    hedge = 1 - smooth(0.02, 0.05, d2 - d1)
    # The woods: big soft shapes with ragged edges, and the belt along the highway (x = 0, and
    # again a tile away).
    metres = (px / S) * EARTH_TILE
    off = min(metres, EARTH_TILE - metres)
    belt = smooth(BELT[0] - 4, BELT[0] + 4, off + 10 * (n - 0.5)) * (1 - smooth(BELT[1] - 8, BELT[1] + 8, off + 30 * (n - 0.5)))
    woods = max(smooth(0.5, 0.56, big * 0.72 + n * 0.28), belt)
    # The verge: mown grass between the road and the trees.
    verge = 1 - smooth(BELT[0] - 6, BELT[0] + 2, off)
    c = mix(c, (0.07, 0.115, 0.045), verge)
    c = mix(c, WOODS, max(woods, hedge * 0.85 * (1 - verge)))
    if woods > 0.5:
        c = mul(c, 0.8 + 0.5 * _EARTH['fine'].at(px + 91, py + 37))
    return c, woods


def _hash2(*k):
    from story_afterlife_mesh import _hash
    return _hash(*k)


def earth_woods(x, z):
    """How wooded the Earth is at (x, z) metres from the crash site, 0..1 (the texture's own woods)."""
    S = EARTH_PIXELS
    return earth_at((x / EARTH_TILE % 1.0) * S, ((1 - z / EARTH_TILE) % 1.0) * S)[1]


def earth_height(x, z, reach):
    """The Earth's ground: level along the highway (it runs along z at x = 0), rolling away from
    it, and hills standing all round the horizon (reach metres out)."""
    off = smooth(120.0, 520.0, abs(x))
    roll = 22.0 * (fbm3(x * 0.0021, 0.0, z * 0.0021, 311, 3) - 0.5) + 6.0 * (fbm3(x * 0.009, 0.0, z * 0.009, 312, 2) - 0.5)
    r = math.hypot(x, z)
    rim = smooth(reach * 0.5, reach * 0.95, r)
    hills = rim * rim * (70.0 + 260.0 * fbm3(x * 0.0011, 0.0, z * 0.0011, 313, 3))
    return -0.3 + off * (roll + hills)


def earth_ground(venue, reach=3072.0, gap=20.0):
    """The Earth's ground out to reach metres, in two halves either side of the highway's gap
    (the road is its own mesh, so that nothing lies on top of anything else far off)."""
    def build(m):
        for side in (-1, 1):
            # (Finer near the road, where the rolling starts.)
            xs = [gap, 60.0, 120.0, 200.0, 300.0, 420.0, 560.0] + [560.0 + (reach - 560.0) * k / 34 for k in range(1, 35)]
            nz = 84
            for i in range(len(xs) - 1):
                for j in range(nz):
                    z0, z1 = -reach + 2 * reach * j / nz, -reach + 2 * reach * (j + 1) / nz
                    q = [(side * xa, earth_height(side * xa, zz, reach), zz) for xa, zz in ((xs[i], z0), (xs[i], z1), (xs[i + 1], z1), (xs[i + 1], z0))]
                    if side < 0:
                        q.reverse()
                    m._quad(q, None, [(p[0] / EARTH_TILE, p[2] / EARTH_TILE) for p in q])
    return prop(venue, 'EarthGround', build, 'Earth', smooth_=True)


def earth_road(venue, near=70.0, far=2900.0, half=14.0, gap=20.0, rails_to=900.0):
    """The highway beyond the crash site's own stretch, both ways: asphalt, its lines and dashes,
    the gravel shoulders and the rails, every strip beside the next (never on top of it)."""
    def build(m):
        def strip(x0, x1, z0, z1, ink, y=0.0):
            m.face([(x0, y, z0), (x0, y, z1), (x1, y, z1), (x1, y, z0)], ink, outward=(0, 1, 0))
        # Across the road: (from x, to x, what).
        bands = [(-gap, -half, 'grille'), (-half, -half + 0.3, 'soot'), (-half + 0.3, -half + 0.45, 'paper'), (-half + 0.45, -5.47, 'soot'), (-5.47, -5.33, 'dash'),
                 (-5.33, -0.2, 'soot'), (-0.2, -0.08, 'brass'), (-0.08, 0.08, 'soot'), (0.08, 0.2, 'brass'), (0.2, 5.33, 'soot'), (5.33, 5.47, 'dash'),
                 (5.47, half - 0.45, 'soot'), (half - 0.45, half - 0.3, 'paper'), (half - 0.3, half, 'soot'), (half, gap, 'grille')]
        for end in (-1, 1):
            for x0, x1, ink in bands:
                if ink != 'dash':
                    strip(x0, x1, end * near, end * far, ink)
                    continue
                # A dash every 12 m for as far as one can be told from the next, then plain.
                z, told = near, 700.0
                while z < told:
                    strip(x0, x1, end * z, end * (z + 3.0), 'paper')
                    strip(x0, x1, end * (z + 3.0), end * (z + 12.0), 'soot')
                    z += 12.0
                strip(x0, x1, end * z, end * far, 'soot')
            # The gravel's edge, down to the ground, and the rails.
            for side in (-1, 1):
                m.face([(side * gap, 0.0, end * near), (side * gap, 0.0, end * far), (side * gap, -0.6, end * far), (side * gap, -0.6, end * near)], 'grille', outward=(side, 0, 0))
                mid, long = end * (near + rails_to) / 2, rails_to - near
                for y, d in ((0.62, 0.0), (0.52, 0.045), (0.72, 0.045)):
                    m.box((side * (half + 1.2) + d, y, mid), (0.04, 0.11 if d == 0 else 0.09, long), 'rail')
                for k in range(int(long / 4)):
                    m.box((side * (half + 1.28), 0.38, end * (near + 2.0 + k * 4.0)), (0.1, 0.76, 0.14), 'post')
    return prop(venue, 'EarthRoad', build)


def earth_crowns(venue, reach=760.0, clear=170.0, spacing=15.0, seed=31):
    """The woods' crowns, where earth_woods says there are woods (out to reach metres; beyond
    that the ground's colour is enough): low lumps and a few conifers, one mesh, painted in
    greys for the material's green to colour. clear: the stretch by the crash site (along z)
    where the roadside's real trees stand instead."""
    def build(m):
        rng = random.Random(seed)
        n = int(reach / spacing)
        for j in range(-n, n + 1):
            for i in range(-n, n + 1):
                x, z = (i + rng.uniform(-0.4, 0.4)) * spacing, (j + rng.uniform(-0.4, 0.4)) * spacing
                size, pick, shade = rng.uniform(0.75, 1.3), rng.random(), rng.choice(('white', 'marble_shade', 'marble_shade', 'rail'))
                if math.hypot(x, z) > reach or abs(x) < BELT[0] - 1 or (abs(x) < BELT[1] + 12 and abs(z) < clear):
                    continue
                if earth_woods(x, z) < 0.6:
                    continue
                y = earth_height(x, z, 3072.0)
                if pick < 0.3:
                    h = 15.0 * size
                    m.lathe((x, y + 1.5, z), [(h * 0.26, 0), (h * 0.1, h * 0.55), (0.0, h)], shade, 5)
                else:
                    r = 6.6 * size
                    m.blob((x, y + r * 0.95, z), r, shade, 0, 0.35, 1.3, rng.randrange(999), (1.0, 0.85, 1.0))
    return prop(venue, 'EarthCrowns', build)


def sign_face(venue, which):
    # v = 1 is the image's top row; seen from in front (from +z) +x is to the left, so u runs back along x.
    return prop(venue, which + 'Face', lambda m: m.face([(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)], uvs=[(1, 0), (0, 0), (0, 1), (1, 1)]), which)


def flame(venue):
    """A tongue of flame 1 high, for additive glowing material."""
    def build(m):
        rings = []
        for k in range(7):
            t = k / 6
            r = 0.34 * math.sin(math.pi * (0.15 + 0.85 * t) ** 0.7) * (1 - t) ** 0.5 + 0.0001
            ring = [(r * math.cos(2 * math.pi * i / 6 + t * 1.4) + 0.12 * math.sin(t * 5), t, r * math.sin(2 * math.pi * i / 6 + t * 1.4) + 0.1 * math.sin(t * 3.3)) for i in range(6)]
            rings.append(ring)
        m.loft(rings, 'fire')
    return prop(venue, 'Flame', build, smooth_=True)


def rock(venue, seed):
    return prop(venue, f'Rock{seed}', lambda m: m.blob((0, 0.25, 0), 1.0, None, 1, 0.45, 1.3, seed, (1.2, 0.8, 1.0), 0.3, floor=0.0), 'Rock')


def spikes(venue, name, count, spread, heights, seed, lean=0.25, base=0.9):
    """A cluster of stone spikes growing up from y = 0 (turn it over for stalactites)."""
    def build(m):
        rng = random.Random(seed)
        for i in range(count):
            a, r = rng.uniform(0, 2 * math.pi), spread * math.sqrt(rng.random())
            h = rng.uniform(*heights) * (1.25 - 0.6 * r / max(spread, 0.01))
            x, z = math.cos(a) * r, math.sin(a) * r
            lx, lz = rng.uniform(-lean, lean) * h, rng.uniform(-lean, lean) * h
            rad = base * h / heights[1] * rng.uniform(0.7, 1.1)
            path, radii = [], []
            for k in range(5):
                t = k / 4
                path.append((x + lx * t * t + rng.uniform(-0.05, 0.05) * h * (k % 4 > 0), h * t - 0.3, z + lz * t * t))
                radii.append(rad * (1 - t) ** 1.3 + (0.0 if k == 4 else 0.02))
            m.tube(path, radii, None, 6, caps=False, v_scale=0.25, u_scale=2.0)
    return prop(venue, name, build, 'Rock')


# ---- the wreck ------------------------------------------------------------------------------
def _drum(m, c, r, depth, euler, shell='drum_red'):
    d = Mesh('d')
    d.lathe((0, 0, 0), [(r, -depth / 2), (r, depth / 2)], shell, 12)
    d.lathe((0, 0, 0), [(r * 1.04, -depth / 2 - 0.01), (r * 1.04, -depth / 2 + 0.03)], 'chrome', 12)
    d.lathe((0, 0, 0), [(r * 1.04, depth / 2 - 0.03), (r * 1.04, depth / 2 + 0.01)], 'chrome', 12)
    d.lathe((0, 0, 0), [(0.0, depth / 2 + 0.005), (r, depth / 2 + 0.005)], 'drum_skin', 12)
    m.merge(d, c, euler)


def wreck(venue):
    """The jackknifed tractor, the flatbed on its side, its truss folded, and the band's gear
    thrown across the road. Around the origin: the flatbed lies along +z at x = 2.5."""
    def build(m):
        if venue != 'StoryHighway':
            t = Mesh('t')
            _tractor(t)
            m.merge(t, (6.8, 1.2, 13.6), (0, 118, 84))
            f = Mesh('f')
            _flatbed(f, wheels=True)
            _truss(f, bent=0.9)
            m.merge(f, (4.4, 3.0, 2.0), (0, 24, -102))
        # The kit.
        _drum(m, (-0.6, 0.3, 6.6), 0.3, 0.45, (74, 30, 0))
        _drum(m, (0.9, 0.36, 4.6), 0.36, 0.42, (8, 0, 88))
        _drum(m, (-2.2, 0.21, 8.9), 0.2, 0.3, (0, 0, 97))
        _drum(m, (1.7, 0.42, 8.2), 0.42, 0.5, (0, 60, 90), 'drum_red')
        _drum(m, (-3.4, 0.09, 4.2), 0.18, 0.16, (3, 0, 0), 'chrome')
        for (x, z, r, tilt) in ((-1.5, 5.4, 0.28, 4), (0.2, 9.6, 0.24, 7), (-3.9, 7.2, 0.2, 86), (2.6, 6.2, 0.26, 12)):
            m.lathe((x, 0.03 + r * math.sin(math.radians(tilt)) * 0.9, z), [(0.0, 0.03), (r * 0.25, 0.03), (r, 0.0)], 'brass', 12)
        rng = random.Random(77)
        for i in range(7):
            x, z, yaw = rng.uniform(-5, 2.5), rng.uniform(3, 11), rng.uniform(0, 180)
            L = rng.uniform(0.6, 1.3)
            a = (x, 0.03, z)
            b = add(a, rot((0, rng.uniform(0, 0.25), L), (0, yaw, 0)))
            m.tube([a, b], 0.018, 'chrome', 5)
            m.tube([b, add(b, rot((0.3, 0.02, 0.2), (0, yaw, 0)))], 0.012, 'chrome', 4)
        # Amps, wedges, cases.
        m.box((-4.6, 0.38, 9.6), (0.8, 1.5, 0.45), 'amp', euler=(86, 40, 0))
        m.box((-4.42, 0.63, 9.75), (0.7, 1.35, 0.03), 'grille', euler=(86, 40, 0))
        m.box((-1.9, 0.75, 11.4), (0.8, 1.5, 0.45), 'amp', euler=(0, -20, 14))
        m.box((-2.0, 0.75, 11.15), (0.7, 1.35, 0.03), 'grille', euler=(0, -20, 14))
        m.box((0.6, 0.22, 2.2), (0.7, 0.45, 0.55), 'amp', euler=(170, 50, 0))
        m.box((-5.6, 0.3, 5.9), (1.1, 0.6, 0.6), 'steel_dark', euler=(0, 70, 0))
        m.box((-5.6, 0.62, 5.9), (1.14, 0.05, 0.64), 'chrome', euler=(0, 70, 0))
        m.box((-6.3, 0.2, 7.5), (1.1, 0.06, 0.62), 'steel_dark', euler=(14, 30, 0))
        # A guitar, the mic stand, sticks, set lists.
        g = Mesh('g')
        g.box((0, 0, 0), (0.34, 0.05, 0.42), 'cab_red')
        g.box((0, 0, 0.16), (0.26, 0.05, 0.2), 'cab_red')
        g.box((0, 0.01, 0.62), (0.05, 0.03, 0.75), 'wood')
        g.box((0, 0.01, 1.03), (0.08, 0.03, 0.16), 'black')
        m.merge(g, (-2.9, 0.04, 2.6), (0, 125, 0))
        m.merge(g, (2.3, 0.3, 10.4), (-50, 20, 30))
        m.tube([(-0.8, 0.03, 2.9), (0.5, 0.05, 3.5)], 0.015, 'chrome', 5)
        m.lathe((-0.8, 0.02, 2.9), [(0.0, 0.02), (0.16, 0.0)], 'steel_dark', 8)
        for i in range(5):
            x, z, yaw = rng.uniform(-5, 1), rng.uniform(2.5, 10), rng.uniform(0, 180)
            m.tube([(x, 0.015, z), add((x, 0.015, z), rot((0, 0, 0.2 if i % 2 else 0.4), (0, yaw, 0)))], 0.008, 'wood', 4)
        for i in range(12):
            x, z, yaw = rng.uniform(-7, 3), rng.uniform(0, 13), rng.uniform(0, 180)
            c = (x, 0.012 + 0.001 * i, z)
            q = [add(c, rot(p, (rng.uniform(-4, 4), yaw, 0))) for p in ((-0.11, 0, -0.14), (0.11, 0, -0.14), (0.11, 0, 0.14), (-0.11, 0, 0.14))]
            m.face(q, 'paper', both=True)
        # Glass and bits of light housing, and the tyre marks into the wreck.
        for i in range(90):
            x, z = rng.gauss(0.5, 3.2), rng.gauss(6.5, 3.5)
            sz = rng.uniform(0.02, 0.07)
            a = rng.uniform(0, 6.28)
            m.tri((x, 0.012, z), (x + sz * math.cos(a), 0.012 + rng.uniform(0, 0.03), z + sz * math.sin(a)),
                  (x + sz * math.cos(a + 2), 0.012, z + sz * math.sin(a + 2)), 'chrome' if i % 3 else 'glass')
        for off in (-1.3, 1.3):
            prev = None
            for k in range(15):
                t = k / 14
                p = (-9.0 + off * 0.9 + 9.5 * t * t, 0.011, -26 + 30 * t)
                if prev:
                    d = unit(sub(p, prev))
                    side = (d[2] * 0.22, 0, -d[0] * 0.22)
                    m.face([sub(prev, side), add(prev, side), add(p, side), sub(p, side)], 'black', outward=(0, 1, 0))
                prev = p
        for i in range(8):
            x, z, r = rng.uniform(-2, 5), rng.uniform(2, 11), rng.uniform(0.8, 2.2)
            m.face([(x + r * math.cos(k * math.pi / 4) * rng.uniform(0.7, 1.1), 0.009, z + r * math.sin(k * math.pi / 4) * rng.uniform(0.7, 1.1)) for k in range(8)],
                   'soot', outward=(0, 1, 0))
    return prop(venue, 'Wreck', build)


def flare(s, parent, venue, name, pos, yaw=0.0):
    """A road flare: the stick, its red light and its sparks."""
    s.box(name, parent, (pos[0], 0.02, pos[2]), (0.03, 0.03, 0.26), (0.5, 0.05, 0.05), rot=(0, yaw, 0))
    tip = add((pos[0], 0.05, pos[2]), rot((0, 0, 0.14), (0, yaw, 0)))
    glow_card(s, parent, venue, name + ' glow', (tip[0], 0.12, tip[2]), 0.5, (1.0, 0.12, 0.08), 9.0, (90, 0, 0))
    particles(s, parent, name + ' sparks', tip, Shape='Cone', ConeAngle=35, ShapeRadius=0.01, Lifetime=[0.25, 0.7], Speed=[0.6, 2.2], Size=[0.02, 0.05],
              StartColor=[1.0, 0.35, 0.25], StartColor2=[1.0, 0.7, 0.6], EndColor=[1.0, 0.05, 0.02], Intensity=7.0, Gravity=0.35, Drag=0.4,
              NoiseStrength=0.6, Blend='Additive', EmissionRate=40, MaxParticles=50, Alignment='Stretched', StretchFactor=0.05, FadeIn=0.02)
    s.light(name + ' light', parent, (tip[0], 0.35, tip[2]), 'Point', (1.0, 0.1, 0.06), 28.0, 7)


# ---- hell -----------------------------------------------------------------------------------
def cavern(venue, centre, radius=52.0, height=60.0):
    """The cavern: a ragged wall right round and a vaulted roof, seen from inside."""
    def build(m):
        rings, sides = [], 36
        for k in range(11):
            t = k / 10
            y = -6 + (height + 6) * math.sin(t * math.pi / 2)
            shrink = math.cos(t * math.pi / 2) ** 0.75
            ring = []
            for i in range(sides):
                a = 2 * math.pi * i / sides
                r = radius * shrink * (0.82 + 0.36 * fbm3(math.cos(a) * 2.2 + 5, y * 0.05, math.sin(a) * 2.2 + 9, 3)) + 0.5
                ring.append((centre[0] + r * math.cos(a), y, centre[2] + r * math.sin(a)))
            rings.append(ring)
        # Rings wound this way (x = cos, z = sin, rising) already face inward.
        m.loft(rings, None, v_scale=0.05, u_scale=14.0)
    return prop(venue, 'Cavern', build, 'Rock')


def arena(venue, radius=15.5, centre=(0.0, 0.0, 2.0)):
    """The island of cracked basalt the band lands on: flat where they stand, ragged at the rim."""
    def build(m):
        def h(x, z):
            d = math.hypot(x - centre[0], z - centre[2]) / radius
            return -0.02 - 0.8 * smooth(0.82, 1.0, d) + 0.25 * smooth(0.6, 0.95, d) * (fbm3(x * 0.4, 0, z * 0.4, 9) - 0.5)
        m.grid(centre[0] - radius - 2, centre[0] + radius + 2, centre[2] - radius - 2, centre[2] + radius + 2, 44, 44, h, None, 0.11,
               keep=lambda x, z: math.hypot(x - centre[0], z - centre[2]) < radius * (0.98 + 0.1 * fbm3(x * 0.3, 2, z * 0.3, 4)))
        # The rim's skirt down into the lava.
        ring_top, ring_bot = [], []
        for i in range(48):
            a = 2 * math.pi * i / 48
            r = radius * (0.98 + 0.1 * fbm3(math.cos(a) * radius * 0.3, 2, math.sin(a) * radius * 0.3, 4))
            ring_top.append((centre[0] + r * math.cos(a), -0.6, centre[2] + r * math.sin(a)))
            ring_bot.append((centre[0] + (r + 1.5) * math.cos(a), -3.0, centre[2] + (r + 1.5) * math.sin(a)))
        m.loft([ring_top, ring_bot], None, v_scale=0.2, u_scale=10)
    return prop(venue, 'Arena', build, 'HellFloor')


def lava(venue, size=150.0):
    return prop(venue, 'LavaLake', lambda m: m.grid(-size / 2, size / 2, -size / 2, size / 2, 2, 2, lambda x, z: 0.0, None, 0.04), 'Lava')


def terraces(venue, centre=(0.0, 0.0, 2.0)):
    """Nine rock tiers round each side of the arena for the crowd, one for each circle of hell;
    returns (path, [(radius, y, first degree, last degree)]). The upper tiers sweep less far, to
    stay inside the cavern behind the band and clear of the lake's fires by the stairs."""
    tiers = [(18.5 + TIER_STEP * k, 1.3 + 1.45 * k, TERRACE_ARC[0] + 4.0 * k, TERRACE_ARC[1] - 3.0 * k) for k in range(9)]

    def build(m):
        for side in (-1, 1):
            for k, (r0, y, arc0, arc1) in enumerate(tiers):
                r1, y_below = r0 + TIER_STEP + 0.4, (tiers[k - 1][1] if k else -1.5)
                seg = 14
                top_in, top_out, bot = [], [], []
                for i in range(seg + 1):
                    a = math.radians(arc0 + (arc1 - arc0) * i / seg)
                    wob = 0.5 * (fbm3(i * 0.7, k, side, 6) - 0.5)
                    dx, dz = side * math.cos(a), math.sin(a) * -1
                    top_in.append((centre[0] + dx * (r0 + wob), y, centre[2] + dz * (r0 + wob)))
                    top_out.append((centre[0] + dx * r1, y, centre[2] + dz * r1))
                    bot.append((centre[0] + dx * (r0 - 0.5 + wob), y_below - 1.0, centre[2] + dz * (r0 - 0.5 + wob)))
                for i in range(seg):
                    uv = lambda p: (p[0] * 0.12, p[2] * 0.12)
                    q = [top_in[i], top_in[i + 1], top_out[i + 1], top_out[i]]
                    m.face(q, uvs=[uv(p) for p in q], outward=(0, 1, 0))
                    q = [bot[i], bot[i + 1], top_in[i + 1], top_in[i]]
                    a = math.radians(arc0 + (arc1 - arc0) * i / seg)
                    m.face(q, uvs=[(i * 0.4, 0), (i * 0.4 + 0.4, 0), (i * 0.4 + 0.4, 0.5), (i * 0.4, 0.5)], outward=(-side * math.cos(a), 0.2, math.sin(a)))
    return prop(venue, 'Terraces', build, 'Rock'), tiers


# The terraces' sweep each side of the arena, in degrees: 0 is straight out to the side, -90 is
# behind the band, +90 would be the stairs.
TERRACE_ARC = (-80.0, 38.0)
TIER_STEP = 2.6     # from one tier's lip out to the next


def terrace_point(centre, side, radius, degrees, y=0.0):
    a = math.radians(degrees)
    return (centre[0] + side * math.cos(a) * radius, y, centre[2] - math.sin(a) * radius)


def hell_stairs(venue, steps, rise, run, z0, half=4.0):
    """The staircase from the arena up to the throne's dais, its cheek walls and plinths."""
    def build(m):
        top_y, zt = steps * rise, z0 - steps * run
        for i in range(steps):
            z = z0 - i * run
            m.box((0, (i + 1) * rise / 2 - 1.5, z - run / 2), (half * 2, (i + 1) * rise + 3.0, run), 'stone')
            m.box((0, (i + 1) * rise - 0.04, z - 0.06), (half * 2 + 0.02, 0.08, 0.14), 'stone_red')
            m.box((0, (i + 1) * rise + 0.004, z - run / 2), (2.2, 0.01, run), 'crimson')
            for side in (-1, 1):
                m.box((side * (half + 0.45), (i + 1) * rise / 2 - 1.1, z - run / 2), (0.9, (i + 1) * rise + 3.8, run), 'stone_dark')
                if i % 2 == 0:
                    m.box((side * (half + 0.45), (i + 1) * rise + 1.15, z - run / 2), (0.7, 0.9, 0.7), 'stone', taper=0.75)
        # The dais and the wall the throne stands against.
        m.box((0, top_y / 2 - 1.5, zt - 5.5), (22, top_y + 3.0, 11), 'stone')
        m.box((0, top_y - 0.1, zt - 0.1), (22.2, 0.22, 0.3), 'stone_red')
        m.box((0, top_y + 0.004, zt - 3.0), (2.2, 0.01, 6.0), 'crimson')
        for x in (-9.5, -6.2, 6.2, 9.5):
            m.lathe((x, top_y, zt - 1.2), [(0.75, 0), (0.75, 0.4), (0.5, 0.6), (0.5, 7.4), (0.8, 7.7), (0.8, 8.1)], 'stone_dark', 8)
        for x in (-7.85, 7.85):
            m.box((x, top_y + 8.5, zt - 1.2), (4.4, 0.9, 1.5), 'stone_dark')
            m.box((x, top_y + 9.3, zt - 1.2), (3.0, 0.7, 1.2), 'stone', taper=0.5)
    return prop(venue, 'HellStairs', build)


def throne(venue):
    """Satan's throne, its seat at y = 0.9: a fan of iron spikes for a back, skulls on the arms."""
    def build(m):
        m.box((0, 0.2, 0.4), (4.4, 0.4, 4.6), 'stone_dark')
        m.box((0, 0.5, 0.2), (3.6, 0.3, 3.8), 'stone_red')
        m.box((0, 0.78, -0.2), (2.6, 0.26, 1.9), 'velvet')
        m.box((0, 2.6, -1.25), (3.0, 4.2, 0.5), 'stone_red', taper=0.8)
        m.box((0, 2.4, -0.98), (2.2, 3.0, 0.08), 'velvet', taper=0.8)
        for i in range(9):
            a = math.radians(-64 + 16 * i)
            L = 5.2 + 2.2 * math.cos(a * 1.4)
            base = (math.sin(a) * 1.0, 3.6, -1.3)
            tip = (math.sin(a) * L * 0.75, 3.6 + math.cos(a) * L, -1.5 - 0.4 * abs(math.sin(a)))
            m.tube([base, lerp(base, tip, 0.5), tip], [0.2, 0.13, 0.0], 'iron', 5, caps=False)
        for x in (-1.5, 1.5):
            m.box((x, 1.25, -0.15), (0.45, 0.95, 2.0), 'stone_red')
            m.blob((x, 1.95, 0.75), 0.3, 'bone', 1, 0.08, 1.5, 3, (1, 1.05, 1.15))
            m.box((x, 1.72, 0.92), (0.28, 0.16, 0.2), 'bone_dark')
            for e in (-0.11, 0.11):
                m.blob((x + e, 1.98, 1.02), 0.075, 'pupil', 0)
    return prop(venue, 'Throne', build)


def skull(venue):
    """A horned skull the size of a house, carved over the throne: 1 unit is its radius."""
    def build(m):
        m.blob((0, 0.15, 0), 1.0, 'bone', 2, 0.07, 1.6, 5, (1.0, 1.02, 1.12))
        m.box((0, -0.72, 0.42), (1.05, 0.62, 0.9), 'bone', taper=0.82)
        m.box((0, -1.2, 0.4), (0.86, 0.3, 0.8), 'bone_dark', taper=0.9)
        for x in (-0.4, 0.4):
            m.blob((x, 0.02, 0.95), 0.31, 'pupil', 1, 0.1, 2.0, 8, (1.05, 1.0, 0.5))
            m.blob((x * 1.7, -0.38, 0.55), 0.3, 'bone_dark', 1, 0.1, 2.0, 2, (0.6, 0.8, 1.0))
        m.face([(-0.13, -0.5, 1.05), (0.13, -0.5, 1.05), (0, -0.18, 1.12)], 'pupil', outward=(0, 0, 1))
        for i in range(8):
            x = -0.385 + i * 0.11
            m.box((x, -0.98, 0.86), (0.09, 0.22, 0.08), 'bone', taper=0.6)
            m.box((x, -1.14, 0.82), (0.085, 0.16, 0.08), 'bone', euler=(0, 0, 180), taper=0.6)
        for side in (-1, 1):
            path = [(side * 0.72, 0.62, 0.1), (side * 1.45, 0.95, 0.15), (side * 2.05, 1.65, 0.3), (side * 2.15, 2.5, 0.55), (side * 1.8, 3.2, 0.85)]
            m.tube(path, [0.36, 0.33, 0.25, 0.14, 0.0], 'horn', 7, caps=False)
    return prop(venue, 'Skull', build)


def skull_eyes(venue):
    """The fire in the great skull's sockets (additive)."""
    def build(m):
        for x in (-0.4, 0.4):
            m.blob((x, 0.02, 1.0), 0.16, 'ember', 1)
    return prop(venue, 'SkullEyes', build)


def gargoyle(venue):
    """A crouched stone demon for the plinths, facing +z, about 1.7 tall."""
    def build(m):
        m.blob((0, 0.65, 0), 0.5, 'stone', 1, 0.15, 1.6, 4, (0.9, 1.1, 0.9))
        m.blob((0, 1.3, 0.28), 0.27, 'stone', 1, 0.1, 2.0, 7, (1.0, 1.0, 1.15))
        m.box((0, 1.2, 0.56), (0.2, 0.14, 0.2), 'stone_dark', taper=0.6)
        for side in (-1, 1):
            m.tube([(side * 0.16, 1.48, 0.25), (side * 0.36, 1.72, 0.2), (side * 0.42, 1.98, 0.32)], [0.07, 0.05, 0.0], 'stone_dark', 5, caps=False)
            m.tube([(side * 0.38, 0.9, 0.1), (side * 0.52, 0.5, 0.45), (side * 0.4, 0.08, 0.55)], [0.13, 0.1, 0.09], 'stone', 5)
            m.tube([(side * 0.3, 0.35, -0.05), (side * 0.5, 0.42, 0.4), (side * 0.48, 0.05, 0.42)], [0.16, 0.12, 0.1], 'stone', 5)
            root = (side * 0.2, 1.05, -0.3)
            tips = [(side * 0.95, 2.2, -0.75), (side * 1.25, 1.5, -0.95), (side * 1.05, 0.75, -0.85)]
            for a, b in zip(tips, tips[1:]):
                m.face([root, a, b], 'stone_dark', both=True)
            for tp in tips:
                m.tube([root, tp], [0.04, 0.0], 'stone', 4, caps=False)
    return prop(venue, 'Gargoyle', build)


def devil_wing(venue):
    """A bat wing, its root at the origin, spreading to +x and up: about 1 across."""
    def build(m):
        root = (0, 0, 0)
        wrist = (0.38, 0.5, -0.05)
        tips = [(0.62, 1.0, -0.1), (1.0, 0.55, -0.12), (0.95, 0.0, -0.1), (0.6, -0.42, -0.06), (0.18, -0.5, -0.02)]
        m.tube([root, wrist], [0.035, 0.025], 'horn', 5)
        prev = None
        for tp in tips:
            m.tube([wrist, tp], [0.022, 0.0], 'horn', 4, caps=False)
            if prev:
                mid = lerp(prev, tp, 0.5)
                sag = lerp(mid, wrist, 0.22)
                m.face([wrist, prev, sag], 'wing_dark', both=True)
                m.face([wrist, sag, tp], 'wing_dark', both=True)
            prev = tp
        m.face([root, wrist, tips[-1]], 'wing_dark', both=True)
    return prop(venue, 'DevilWing', build)


def horns(venue, big=False):
    """A pair of horns to sit on a head at the origin (the head's top)."""
    def build(m):
        k = 2.6 if big else 1.0
        for side in (-1, 1):
            path = [(side * 0.07 * k, -0.04 * k, 0.02), (side * 0.11 * k, 0.05 * k, 0.03), (side * 0.13 * k, 0.14 * k, 0.0), (side * 0.1 * k, 0.22 * k, -0.04 * k)]
            m.tube(path, [0.028 * k, 0.024 * k, 0.015 * k, 0.0], 'horn', 5, caps=False)
    return prop(venue, 'HornsBig' if big else 'Horns', build)


def brazier(venue):
    def build(m):
        m.lathe((0, 0, 0), [(0.1, 0.9), (0.42, 1.05), (0.55, 1.3), (0.5, 1.32), (0.3, 1.12), (0.0, 1.1)], 'iron', 8)
        for k in range(3):
            a = 2 * math.pi * k / 3
            m.tube([(0.5 * math.cos(a), 0, 0.5 * math.sin(a)), (0.08 * math.cos(a), 0.95, 0.08 * math.sin(a))], 0.035, 'iron', 4)
        m.lathe((0, 1.24, 0), [(0.0, 0.05), (0.4, 0.0)], 'ember', 8)
    return prop(venue, 'Brazier', build)


def chain_cage(venue, length=14.0):
    """A chain hanging down from the origin with an iron cage on its end."""
    def build(m):
        n = int(length / 0.36)
        for k in range(n):
            m.box((0, -0.18 - k * 0.36, 0), (0.05, 0.3, 0.16) if k % 2 else (0.16, 0.3, 0.05), 'iron')
        y = -length
        m.lathe((0, y, 0), [(0.0, 0.0), (0.5, -0.35), (0.75, -0.9)], 'iron', 8)
        for k in range(8):
            a = 2 * math.pi * k / 8
            m.tube([(0.75 * math.cos(a), y - 0.9, 0.75 * math.sin(a)), (0.75 * math.cos(a), y - 2.9, 0.75 * math.sin(a))], 0.03, 'iron', 4)
        m.lathe((0, y - 2.9, 0), [(0.8, 0.0), (0.8, -0.12), (0.0, -0.12)], 'iron', 8)
        m.blob((0.1, y - 2.55, 0.05), 0.2, 'bone', 1, 0.08)
        m.tube([(0.1, y - 2.4, 0.05), (0.0, y - 1.7, 0.0), (-0.05, y - 1.5, 0.1)], 0.05, 'bone', 4)
    return prop(venue, 'ChainCage', build)


def banner(venue):
    def build(m):
        for k in range(6):
            y0, y1 = -k * 1.0, -(k + 1) * 1.0
            z0, z1 = 0.08 * math.sin(k * 1.1), 0.08 * math.sin((k + 1) * 1.1)
            m.face([(-0.9, y1, z1), (0.9, y1, z1), (0.9, y0, z0), (-0.9, y0, z0)],
                   uvs=[(1, 1 - (k + 1) / 6), (0, 1 - (k + 1) / 6), (0, 1 - k / 6), (1, 1 - k / 6)], both=True)
    return prop(venue, 'Banner', build, 'Banner')


def bats(venue, count=14, seed=3, part='Bodies'):
    """A ring of bats 1 across, flying anticlockwise seen from above; turn the entity to fly them.
    part: 'Bodies' (each a small dark body along its line of flight) or 'Wings' (their wings, each
    pair hinged along the body's line, the tips raised): every bat's body is on the ring's plane,
    so a scale of the Wings ring's height through 1 and below 0 beats the wings about their roots
    and leaves the bodies where they are. (A ring is one height: stack a few for a flock.)"""
    def build(m):
        rng = random.Random(seed)
        for i in range(count):
            a = 2 * math.pi * i / count + rng.uniform(-0.2, 0.2)
            r = rng.uniform(0.75, 1.0)
            c = (r * math.cos(a), 0.0, r * math.sin(a))
            fwd = (-math.sin(a), 0, math.cos(a))
            out = (math.cos(a), 0, math.sin(a))
            sz = rng.uniform(0.018, 0.03)
            if part == 'Bodies':
                m.blob(add(c, mul(fwd, sz * 0.1)), sz * 0.35, 'black', 0)
                m.blob(add(c, mul(fwd, sz * 0.5)), sz * 0.2, 'black', 0)        # the head
                continue
            lift = rng.uniform(0.35, 0.8) * sz                                  # the tips' rest above the body
            for side in (-1, 1):
                wrist = add(c, add(mul(out, side * sz * 0.8), (0, lift * 0.55, 0)))
                tip = add(c, add(mul(out, side * sz * 1.7), (0, lift, 0)))
                root_f, root_b = add(c, mul(fwd, sz * 0.3)), add(c, mul(fwd, -sz * 0.35))
                m.face([root_f, wrist, root_b], 'black', both=True)
                m.face([root_f, add(tip, mul(fwd, sz * 0.15)), wrist], 'wing_dark', both=True)
                m.face([root_b, wrist, add(tip, mul(fwd, -sz * 0.75))], 'wing_dark', both=True)
                m.face([wrist, add(tip, mul(fwd, sz * 0.15)), add(tip, mul(fwd, -sz * 0.75))], 'wing_dark', both=True)
    return prop(venue, 'Bats' if part == 'Bodies' else 'BatWings', build)


def road_break(venue, half_long=15.0, wide=2.3):
    """The break in the road they fell through, seen from far below: the road's dark underside
    and, just under it, the tear across it (along x) as a shape of its own to be given a glow: a
    kinked fissure widest in the middle, thinner cracks forking off it. Two models about the
    origin, both facing down."""
    def under(m):
        outer, sides = 26.0, 24
        ring = [(outer * math.cos(2 * math.pi * i / sides), 0, outer * math.sin(2 * math.pi * i / sides)) for i in range(sides)]
        m.face(ring, 'black', outward=(0, -1, 0))

    def light(m):
        rng = random.Random(77)

        def run(x, z, course, length, width, depth):
            """One crack from (x, z) along course: kinked lengths (a zigzag about the course, so
            that it holds its line) thinning to a point, forking now and then."""
            steps = max(2, int(length / 2.0))
            heading = course + rng.uniform(-0.5, 0.5)
            last = None
            for n in range(steps + 1):
                w = width * (1 - n / steps) ** 0.8
                sx, sz = -math.sin(course), math.cos(course)
                here = ((x - sx * w, -0.05 - 0.02 * depth, z - sz * w), (x + sx * w, -0.05 - 0.02 * depth, z + sz * w))
                if last:
                    m.face([last[0], last[1], here[1], here[0]], 'white', outward=(0, -1, 0))
                last = here
                if n == steps:
                    break
                if depth < 2 and n and rng.random() < (0.8 if depth == 0 else 0.45):
                    side = rng.choice((-1, 1))
                    run(x, z, course + side * rng.uniform(0.6, 1.2), length * (1 - n / steps) * rng.uniform(0.45, 0.8) + 2.0, w * rng.uniform(0.35, 0.6), depth + 1)
                step = length / steps * rng.uniform(0.75, 1.25)
                heading = course + rng.uniform(0.25, 0.7) * (-1 if heading > course else 1)
                x, z = x + math.cos(heading) * step, z + math.sin(heading) * step
        run(0.0, 0.0, 0.2, half_long, wide, 0)
        run(0.0, 0.0, 0.2 + math.pi, half_long, wide, 0)
    return prop(venue, 'RoadBreak', under), prop(venue, 'RoadBreakLight', light)


SHAFT_PERIOD = 65.0


def shaft_walls(venue, radius=15.0, height=260.0):
    """The shaft they fall down: a ragged rock tube seen from inside, centred on the origin. Its
    shape and its texture repeat every SHAFT_PERIOD metres, so it can stream past on a loop."""
    def build(m):
        rings, sides = [], 30
        count = int(height / 5.0)

        def wall(a, y):
            return fbm3(math.cos(a) * 1.6 + 3, y * 0.07, math.sin(a) * 1.6 + 8, 12) + 0.35 * (fbm3(math.cos(a) * 6 + 1, y * 0.3, math.sin(a) * 6 + 4, 14) - 0.5)
        for k in range(count + 1):
            y = -height / 2 + 5.0 * k
            t = (y % SHAFT_PERIOD) / SHAFT_PERIOD
            ring = []
            for i in range(sides):
                a = 2 * math.pi * i / sides
                n = (1 - t) * wall(a, t * SHAFT_PERIOD) + t * wall(a, t * SHAFT_PERIOD - SHAFT_PERIOD)
                r = radius * (0.8 + 0.45 * n)
                ring.append((r * math.cos(a), y, r * math.sin(a)))
            rings.append(ring)
        # v by height (not by the wall's own run), so the texture repeats with the shape.
        for r_ in range(count):
            for i in range(sides):
                j = (i + 1) % sides
                q = [rings[r_][i], rings[r_][j], rings[r_ + 1][j], rings[r_ + 1][i]]
                v0, v1 = (-height / 2 + 5.0 * r_) * 4 / SHAFT_PERIOD, (-height / 2 + 5.0 * (r_ + 1)) * 4 / SHAFT_PERIOD
                uv = [(i / sides * 6, v0), ((i + 1) / sides * 6, v0), ((i + 1) / sides * 6, v1), (i / sides * 6, v1)]
                m.face(q, uvs=uv)
    return prop(venue, 'Shaft', build, 'Rock')


# ---- heaven ---------------------------------------------------------------------------------
def cloud(venue, seed):
    """A cumulus about 2 across and 1 high, flat underneath, on the origin."""
    def build(m):
        rng = random.Random(seed * 13 + 1)
        n = 6 + seed % 3
        for i in range(n):
            a = rng.uniform(0, 6.28)
            r = rng.uniform(0.25, 0.7) if i else 0.0
            size = rng.uniform(0.26, 0.46) if i else 0.62
            lift = rng.uniform(0.0, 0.35) if i else 0.12
            m.blob((r * math.cos(a), size * 0.6 + lift, r * math.sin(a) * 0.8), size, 'cloud', 2, 0.07, 1.4, seed * 31 + i, (1.1, 0.92, 1.0), floor=0.0)
    return prop(venue, f'Cloud{seed}', build, smooth_=True)


def cloud_floor(venue, half=75.0, clear=None):
    """The floor of cloud: billows right out to the edge, level where the band and the stairs stand.
    clear(x, z) -> 0..1: how flat to keep it there."""
    def build(m):
        def h(x, z):
            b = fbm3(x * 0.09, 0, z * 0.09, 21, 4)
            billow = abs(b * 2 - 1) ** 0.8
            y = -0.25 - 1.9 * billow + 0.9 * fbm3(x * 0.03, 5, z * 0.03, 22, 2)
            flat = clear(x, z) if clear else 0.0
            edge = smooth(half * 0.75, half, math.hypot(x, z))
            return (y * (1 - flat) + (-0.3) * flat) - 9.0 * edge
        m.grid(-half, half, -half, half, 70, 70, h, 'cloud', keep=lambda x, z: math.hypot(x, z) < half)
    return prop(venue, 'CloudFloor', build, smooth_=True)


def cloud_sea(venue, half=900.0):
    def build(m):
        def h(x, z):
            return 26.0 * abs(fbm3(x * 0.006, 0, z * 0.006, 41, 4) * 2 - 1) + 30 * fbm3(x * 0.002, 3, z * 0.002, 42, 2)
        m.grid(-half, half, -half, half, 64, 64, h, 'cloud')
    return prop(venue, 'CloudSea', build, smooth_=True)


def sky_dome(venue, name='SkyDome', texture_name='Sky', radius=950.0, wrap=1):
    """The sky, seen from inside: v runs from the bottom of the dome (0) to the zenith (1)."""
    def build(m):
        rings, sides, bands = [], 24, 12
        for k in range(bands + 1):
            el = math.radians(-35 + 125 * k / bands)
            rings.append([(radius * math.cos(el) * math.cos(2 * math.pi * i / sides), radius * math.sin(el), radius * math.cos(el) * math.sin(2 * math.pi * i / sides))
                          for i in range(sides)])
        for r in range(bands):
            for i in range(sides):
                j = (i + 1) % sides
                q = [rings[r][i], rings[r][j], rings[r + 1][j], rings[r + 1][i]]
                uv = [(i / sides * wrap, r / bands), ((i + 1) / sides * wrap, r / bands), ((i + 1) / sides * wrap, (r + 1) / bands), (i / sides * wrap, (r + 1) / bands)]
                m.face(q, uvs=uv)
    return prop(venue, name, build, texture_name)


def column(venue):
    """A fluted marble column 8 high with a gold capital."""
    def build(m):
        m.box((0, 0.15, 0), (1.5, 0.3, 1.5), 'marble_shade')
        m.lathe((0, 0.3, 0), [(0.68, 0), (0.68, 0.18), (0.56, 0.3)], 'gold', 12)
        rings = []
        for y in (0.6, 7.2):
            # Wound the way lathe winds its rings (z = -sin), so loft faces the flutes outward.
            rings.append([((0.5 if i % 2 else 0.44) * math.cos(2 * math.pi * i / 24), y, (0.5 if i % 2 else 0.44) * -math.sin(2 * math.pi * i / 24)) for i in range(24)])
        m.loft(rings, 'marble')
        m.lathe((0, 7.2, 0), [(0.52, 0), (0.62, 0.2), (0.82, 0.45), (0.82, 0.55)], 'gold', 12)
        m.box((0, 7.88, 0), (1.8, 0.26, 1.8), 'marble')
    return prop(venue, 'Column', build)


def heaven_stairs(venue, steps, rise, run, z0, half=5.0):
    """The broad stairs up to God's platform: marble, gold on every nosing, cheek walls."""
    def build(m):
        top_y, zt = steps * rise, z0 - steps * run
        for i in range(steps):
            z = z0 - i * run
            m.box((0, (i + 1) * rise / 2 - 2.0, z - run / 2), (half * 2, (i + 1) * rise + 4.0, run), 'marble')
            m.box((0, (i + 1) * rise - 0.03, z - 0.05), (half * 2 + 0.02, 0.06, 0.12), 'gold')
            for side in (-1, 1):
                m.box((side * (half + 0.4), (i + 1) * rise / 2 - 1.7, z - run / 2), (0.8, (i + 1) * rise + 4.6, run), 'marble_shade')
                m.box((side * (half + 0.4), (i + 1) * rise + 0.33, z - run / 2), (0.86, 0.06, run + 0.02), 'gold')
        m.lathe((0, 0, zt - 9), [(13.0, -4.0), (13.0, top_y - 0.25), (12.8, top_y)], 'marble', 40)
        m.lathe((0, top_y - 0.25, zt - 9), [(13.05, 0.0), (13.05, 0.2)], 'gold', 40)
        m.lathe((0, top_y, zt - 9), [(0.0, 0.004), (12.8, 0.0)], 'marble', 40)
        for k in range(3):
            m.lathe((0, top_y + k * 0.3, zt - 13), [(4.6 - k * 0.9, 0.0), (4.6 - k * 0.9, 0.3), (0.0, 0.3)], 'marble_shade' if k % 2 else 'marble', 24)
            m.lathe((0, top_y + k * 0.3 + 0.27, zt - 13), [(4.63 - k * 0.9, 0.0), (4.63 - k * 0.9, 0.04)], 'gold', 24)
    return prop(venue, 'HeavenStairs', build)


def gate(venue):
    """The gates at the head of the stairs: two leaves of gold bars standing open under an arch,
    12 wide and 13 high, the opening along x at z = 0."""
    def build(m):
        for side in (-1, 1):
            m.box((side * 6.6, 5.0, 0), (1.6, 10.0, 1.6), 'marble')
            m.box((side * 6.6, 10.2, 0), (2.0, 0.5, 2.0), 'gold')
            m.blob((side * 6.6, 11.2, 0), 0.75, 'gold', 1)
            hinge = (side * 5.8, 0, 0)
            yaw = side * 62
            for k in range(9):
                p = add(hinge, rot((-side * (0.3 + k * 0.6), 0, 0), (0, yaw, 0)))
                h = 8.2 + 1.6 * math.sin(math.pi * k / 16)
                m.tube([(p[0], 0.2, p[2]), (p[0], h, p[2])], 0.06, 'gold', 5)
                m.lathe((p[0], h, p[2]), [(0.11, 0.0), (0.0, 0.35)], 'gold', 5)
            for y in (0.5, 4.3, 7.6):
                a = add(hinge, rot((-side * 0.2, y, 0), (0, yaw, 0)))
                b = add(hinge, rot((-side * 5.2, y, 0), (0, yaw, 0)))
                m.tube([a, b], 0.07, 'gold', 5)
        arch = [(7.0 * math.cos(math.pi * k / 16), 10.2 + 3.6 * math.sin(math.pi * k / 16), 0) for k in range(17)]
        m.tube(arch, 0.32, 'gold', 6, caps=False)
        m.tube([(p[0] * 0.9, p[1] - 0.5 + (p[1] - 10.2) * -0.08, 0) for p in arch], 0.12, 'gold', 5, caps=False)
    return prop(venue, 'Gate', build)


def torus(venue, name, radius=1.0, thick=0.07, ink='gold', seg=48, sides=6, axis='z'):
    def build(m):
        path = []
        for k in range(seg + 1):
            a = 2 * math.pi * k / seg
            path.append((radius * math.cos(a), radius * math.sin(a), 0) if axis == 'z' else (radius * math.cos(a), 0, radius * math.sin(a)))
        m.tube(path, thick, ink, sides, caps=False)
    return prop(venue, name, build, smooth_=True)


def _eye(m, c, r, toward):
    """An eyeball at c looking along toward."""
    d = unit(toward)
    m.blob(c, r, 'white', 1)
    u_, v_ = None, None
    from story_afterlife_mesh import basis
    u_, v_ = basis(d)
    for rad, depth, ink in ((r * 0.62, r * 0.86, 'iris'), (r * 0.3, r * 0.93, 'pupil')):
        centre = add(c, mul(d, depth))
        ring = [add(centre, add(mul(u_, rad * math.cos(2 * math.pi * i / 10)), mul(v_, rad * math.sin(2 * math.pi * i / 10)))) for i in range(10)]
        for i in range(10):
            m.face([add(c, mul(d, depth + r * 0.1)), ring[i], ring[(i + 1) % 10]], ink, outward=d)


def angel_ring(venue, name, radius, thick, eyes, facing='z'):
    """One of an angel's wheels: a gold ring 'radius' round with eyes set along it. facing 'z':
    the ring lies in the x-y plane, its eyes looking along +z; 'out': eyes look outward."""
    def build(m):
        path = [(radius * math.cos(2 * math.pi * k / 48), radius * math.sin(2 * math.pi * k / 48), 0) for k in range(49)]
        m.tube(path, thick, 'gold', 6, caps=False)
        for off in (-1, 1):
            m.tube([(p[0] * (1 + off * thick * 1.2 / radius), p[1] * (1 + off * thick * 1.2 / radius), 0) for p in path], thick * 0.25, 'gold_dark', 4, caps=False)
        for i in range(eyes):
            a = 2 * math.pi * (i + 0.5) / eyes
            c = (radius * math.cos(a), radius * math.sin(a), 0)
            if facing == 'z':
                _eye(m, add(c, (0, 0, thick * 0.55)), thick * 0.8, (0, 0, 1))
            else:
                _eye(m, add(c, mul(unit(c), thick * 0.55)), thick * 0.8, c)
    return prop(venue, name, build)


def angel_eye(venue):
    """The great eye at an angel's heart, 1 in radius, looking along +z."""
    def build(m):
        m.blob((0, 0, 0), 1.0, 'white', 2)
        for rad, depth, ink, n in ((0.66, 0.78, 'iris', 20), (0.5, 0.86, 'sky', 20), (0.28, 0.93, 'pupil', 14)):
            ring = [(rad * math.cos(2 * math.pi * i / n), rad * math.sin(2 * math.pi * i / n), depth) for i in range(n)]
            for i in range(n):
                m.face([(0, 0, depth + 0.08), ring[i], ring[(i + 1) % n]], ink, outward=(0, 0, 1))
    return prop(venue, 'AngelEye', build, smooth_=False)


def wing(venue):
    """A feathered wing: its root at the origin, sweeping out along +x and up, 1 long. Three rows of
    feathers off an arched arm."""
    def build(m):
        def arm(t):
            return (t, 0.34 * math.sin(t * math.pi * 0.85) + 0.1 * t, -0.03 * math.sin(t * 3))
        m.tube([arm(k / 8) for k in range(9)], [0.045 - 0.004 * k for k in range(9)], 'feather', 5)
        for row, (count, length, ink, lift) in enumerate(((16, 0.62, 'feather_tip', 0.0), (13, 0.4, 'feather', 0.014), (10, 0.22, 'feather', 0.028))):
            for i in range(count):
                t = 0.04 + 0.96 * i / (count - 1)
                root = arm(t)
                fan = math.radians(-96 + 78 * t ** 1.3)        # near the body they hang down, the tips reach out
                L = length * (0.75 + 0.55 * t) * (1.0 if row else 1.0 + 0.35 * t)
                d = (math.cos(fan), math.sin(fan), 0)
                side = (-d[1], d[0], 0)
                w = 0.05 + 0.012 * row
                z = lift + 0.006 * (i % 2)
                p0 = (root[0], root[1], root[2] + z)
                mid = add(p0, mul(d, L * 0.55))
                tip = add(p0, mul(d, L))
                m.face([p0, add(mid, mul(side, -w)), tip, add(mid, mul(side, w))], ink, both=True)
    return prop(venue, 'Wing', build)


def angel_far(venue):
    """A whole angel in one mesh for the far ranks of the choir: wheels, wings, eye. 1 = ring radius."""
    def build(m):
        for radius, tilt in ((1.0, (0, 0, 0)), (0.86, (0, 62, 0)), (0.72, (58, 0, 20))):
            t = Mesh('t')
            t.tube([(radius * math.cos(2 * math.pi * k / 24), radius * math.sin(2 * math.pi * k / 24), 0) for k in range(25)], 0.06, 'gold', 4, caps=False)
            m.merge(t, (0, 0, 0), tilt)
        m.blob((0, 0, 0), 0.34, 'white', 1)
        m.face([(0.16 * math.cos(2 * math.pi * i / 8), 0.16 * math.sin(2 * math.pi * i / 8), 0.33) for i in range(8)], 'iris', outward=(0, 0, 1))
        m.face([(0.07 * math.cos(2 * math.pi * i / 8), 0.07 * math.sin(2 * math.pi * i / 8), 0.345) for i in range(8)], 'pupil', outward=(0, 0, 1))
        for side in (-1, 1):
            for k, (ang, L) in enumerate(((38, 2.6), (8, 2.9), (-24, 2.3))):
                a = math.radians(ang)
                root = (side * 0.9 * math.cos(a), 0.9 * math.sin(a), -0.15)
                for f in range(7):
                    fa = a + math.radians(-30 + 10 * f) * 0.9
                    tip = (root[0] + side * L * (0.55 + 0.07 * f) * math.cos(fa), root[1] + L * (0.55 + 0.07 * f) * math.sin(fa) - 0.12 * f, -0.2)
                    w = (-(tip[1] - root[1]), side * (tip[0] - root[0]) * side, 0)
                    w = mul(unit(w), 0.16)
                    mid = lerp(root, tip, 0.5)
                    m.face([root, add(mid, w), tip, sub(mid, w)], 'feather' if f % 2 else 'feather_tip', both=True)
    return prop(venue, 'AngelFar', build)


def sunburst(venue):
    """Rays out from the origin in the x-y plane, 1 long (additive)."""
    def build(m):
        for i in range(36):
            a = 2 * math.pi * i / 36
            L = 1.0 if i % 3 == 0 else (0.72 if i % 3 == 1 else 0.5)
            w = 0.035 if i % 3 == 0 else 0.02
            d = (math.cos(a), math.sin(a), 0)
            sd = (-d[1] * w, d[0] * w, 0)
            m.face([mul(d, 0.12), add(mul(d, 0.2), sd), mul(d, L), sub(mul(d, 0.2), sd)], 'gold', both=True)
    return prop(venue, 'Sunburst', build)


def island(venue, seed):
    """A far cloud with a little temple on it, 1 = about 10 m."""
    def build(m):
        rng = random.Random(seed)
        for i in range(6):
            a, r = rng.uniform(0, 6.28), rng.uniform(0, 0.8)
            m.blob((r * math.cos(a), -0.2, r * math.sin(a) * 0.7), rng.uniform(0.45, 0.75), 'cloud', 1, 0.18, 1.6, seed + i, (1.2, 0.6, 1.0))
        m.box((0, 0.28, 0), (1.3, 0.1, 0.8), 'marble')
        for x in (-0.5, -0.17, 0.17, 0.5):
            for z in (-0.3, 0.3):
                m.lathe((x, 0.33, z), [(0.05, 0.0), (0.045, 0.7)], 'marble', 6)
        m.box((0, 1.08, 0), (1.3, 0.1, 0.8), 'marble')
        m.box((0, 1.28, 0), (1.3, 0.3, 0.8), 'gold', taper=0.05)
    return prop(venue, f'Island{seed}', build)
