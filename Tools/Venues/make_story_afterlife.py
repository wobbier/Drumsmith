#!/usr/bin/env python3
"""Builds the three venues of "Highway to the Afterlife" (Design/Highway-to-the-Afterlife.md), the
proposed story set highway-afterlife in Design/Story-Mode-Setlists.json:

    python3 Tools/Venues/make_story_afterlife.py

  StoryHighway  Kickstart My Heart: the band on a flatbed trailer down a night highway that scrolls
                past, the cruiser behind with its lightbar going; the wreck on a marked stretch of
                shoulder, and the band's bodies on the asphalt.
  StoryHell     Free Bird and Bat Country: the crash site, the fall down a shaft, and hell: a
                cavern over a lake of lava, the island the band lands on, the crowd on its
                terraces, the staircase, and Satan's throne under a horned skull.
  StoryHeaven   Stairway to Heaven and My Hero: the ascent through cloud, the cloud floor, the
                stairs, the gates and God's platform, the angel choir; and, far off in the same
                scene, the crash site on Earth for the rescue cut-aways.

The set is built from story_afterlife_art's props (meshes and textures drawn by
story_afterlife_mesh), posed figures (story_afterlife_people), particles and looping clips. Every
story beat is a story flag (the set's cues and moments in the manifest): VenueStory groups show
the props for it, and a Custom camera spot tagged story/<flag>[/<seconds>][/hand][/f<metres>]
(with optional story/<flag>/w1.. waypoints and a story/<flag>/end where it moves to) is the shot
the director cuts to when it lands (Director::SetStoryShots). Deterministic: a rerun writes the
same bytes.
"""
import json
import math
import os
import random
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import story_afterlife_art as A  # noqa: E402
import story_afterlife_people as P  # noqa: E402
from venuegen import Scene, look_rotation, repo_root, write_venue_json  # noqa: E402

# Colours.
ASPHALT = (0.07, 0.07, 0.08)
LINE_WHITE = (0.85, 0.85, 0.8)
LINE_YELLOW = (0.9, 0.7, 0.15)
GRAVEL = (0.22, 0.2, 0.18)
GRASS = (0.06, 0.1, 0.05)
STEEL = (0.35, 0.36, 0.38)
WHITE = (0.9, 0.9, 0.92)
FIRE = (1.0, 0.45, 0.08)
EMBER = (1.0, 0.2, 0.03)
STONE = (0.16, 0.12, 0.11)
STONE_DARK = (0.08, 0.06, 0.06)
LAVA = (1.0, 0.25, 0.02)
CLOUD = (0.95, 0.96, 1.0)
GOLD = (1.0, 0.8, 0.35)

# The highway's slew at the end of Kickstart My Heart: the world turns this far about the trailer.
SLEW_YAW = 26.0
SLEW_SHIFT = (2.5, 0.0, 0.0)


def slewed(p):
    """Where a point on the highway's road ends up once the slew is done (venue space)."""
    a = math.radians(SLEW_YAW)
    x, y, z = p
    return (x * math.cos(a) + z * math.sin(a) + SLEW_SHIFT[0], y + SLEW_SHIFT[1], -x * math.sin(a) + z * math.cos(a) + SLEW_SHIFT[2])


# The band: the same marks in every venue (y is the deck or floor they stand on).
DRUMMER = (0.0, 5.2)
GUITAR = (-2.1, 2.6)
BASS = (2.1, 2.8)
VOCALS = (0.0, 1.0)

SHOTS = {}    # venue -> {flag: [eye, target, fov]} for Tools' previews (written beside the scene)


def band(s, marks, y):
    s.spot(marks, 'Drummer', (DRUMMER[0], y, DRUMMER[1]))
    s.spot(marks, 'Guitar', (GUITAR[0], y, GUITAR[1]), yaw=-8)
    s.spot(marks, 'Bass', (BASS[0], y, BASS[1]), yaw=8)
    s.spot(marks, 'Vocals', (VOCALS[0], y, VOCALS[1]))


def shot(s, marks, flag, eye, target, fov=50.0, hold=None, hand=False, end=None, via=(), focus=False):
    """The story shot for flag: from eye at target; end (eye, target, fov) is where it moves to,
    by way of via [(eye, target, fov), ...]. focus: pull focus to the target (and soften the rest)."""
    def f(e, t):
        return f'/f{math.dist(e, t):.2f}' if focus else ''
    tag = 'story/' + flag + (f'/{hold:g}' if hold else '') + ('/hand' if hand else '') + f(eye, target)
    s.camera_spot('Story ' + flag, marks, eye, target, 'Custom', fov, tag)
    views = [[list(eye), list(target), fov]]
    for i, (e, t, v) in enumerate(via):
        s.camera_spot(f'Story {flag} w{i + 1}', marks, e, t, 'Custom', v, f'story/{flag}/w{i + 1}')
        views.append([list(e), list(t), v])
    if end:
        s.camera_spot('Story ' + flag + ' end', marks, end[0], end[1], 'Custom', end[2], 'story/' + flag + '/end' + f(end[0], end[1]))
        views.append([list(end[0]), list(end[1]), end[2]])
    SHOTS.setdefault(s.venue, {})[flag] = views


def write(s, venue, name, ambience=None):
    folder = os.path.join(repo_root(), 'Assets', 'Venues', venue)
    os.makedirs(folder, exist_ok=True)
    s.write(os.path.join(folder, venue + '.lvl'))
    write_venue_json(folder, name, venue + '.lvl', author='Drumsmith', ambience=ambience)
    print(f'Assets/Venues/{venue}: {len(s.entities)} entities')


def textured(e, venue, name, tiling=(1, 1), glow=None, power=1.0, glow_name=None):
    """Put one of the set's textures on a primitive (s.box / s.slab)."""
    for c in e.components:
        if c.get('Type') == 'Mesh':
            m = c['Material']
            m['Textures'] = {'Diffuse': {'Path': A.tex(venue, name)}}
            m['Tiling'] = [float(tiling[0]), float(tiling[1])]
            if glow is not None:
                m['Textures']['Emissive'] = {'Path': A.tex(venue, glow_name or name)}
                m['EmissiveColor'] = [float(v) for v in glow]
                m['EmissiveIntensity'] = float(power)
    return e


def see_through(e, opacity, additive=False):
    for c in e.components:
        if c.get('Type') == 'Mesh':
            c['CastShadows'] = False
            c['Material'].update({'RenderMode': 1, 'BlendMode': 2 if additive else 0, 'Opacity': float(opacity)})
    return e


# ---- shared pieces ------------------------------------------------------------------------------
def fire(s, parent, venue, at, size=1.0, light=500.0, smoke=True, name='Fire'):
    """A fire: tongues of flame flickering on loops, flames and sparks and smoke in the air, and an
    orange light that jumps about."""
    rng = random.Random(int(at[0] * 100 + at[2] * 7))
    flame_mat = A.mat(venue, 'Palette', (0, 0, 0), glow=(1.0, 0.5, 0.12), power=5.0, additive=True, both=True)
    core_mat = A.mat(venue, 'Palette', (0, 0, 0), glow=(1.0, 0.85, 0.45), power=7.0, additive=True, both=True)
    for i in range(6):
        clip = P.clip(venue, f'Flicker{i % 3}', 14 + 5 * (i % 3), [P.track('Scale', [(0, (1, 1, 1)), (4 + i % 3, (1.15, 1.4 - 0.1 * (i % 3), 0.9)), (9 + 2 * (i % 3), (0.85, 0.75, 1.15)),
                                                                             (14 + 5 * (i % 3), (1, 1, 1))], 'SmoothStep')])
        p = (at[0] + rng.uniform(-0.9, 0.9) * size, at[1], at[2] + rng.uniform(-0.9, 0.9) * size)
        body = P.looping(s, parent, f'{name} tongue {i}', clip, p, speed=rng.uniform(0.8, 1.5))
        h = size * rng.uniform(1.4, 3.0)
        A.model(s, body, 'Flame', A.flame(venue), (0, 0, 0), (0, rng.uniform(0, 360), 0), (size * rng.uniform(0.9, 1.5), h, size * rng.uniform(0.9, 1.5)), flame_mat, shadows=False)
        A.model(s, body, 'Flame core', A.flame(venue), (0, 0, 0), (0, rng.uniform(0, 360), 0), (size * 0.6, h * 0.6, size * 0.6), core_mat, shadows=False)
    A.fire_fx(s, parent, venue, name, (at[0], at[1] + 0.2 * size, at[2]), size, smoke)
    A.glow_card(s, parent, venue, name + ' glow', (at[0], at[1] + 0.06, at[2]), 3.2 * size, (1.0, 0.4, 0.08), 1.6, (90, 0, 0))
    jump = P.clip(venue, 'FireLight', 20, [P.track('Position', [(0, (0, 0, 0)), (3, (0.25, 0.2, -0.2)), (7, (-0.3, -0.15, 0.2)), (12, (0.2, 0.3, 0.3)), (16, (-0.15, 0.0, -0.3)), (20, (0, 0, 0))])])
    s.light(name + ' light', P.looping(s, parent, name + ' light', jump, (at[0], at[1] + 1.6 * size, at[2]), speed=1.3), (0, 0, 0), 'Point', (1.0, 0.6, 0.28), light, 20 * size)


def lightbar(s, parent, venue, at):
    """A cruiser's lightbar: red and blue lamps, their glare, and two spot lights sweeping round."""
    spin = P.clip(venue, 'LightbarSpin', 24, [P.track('Rotation', [(0, (0, 0, 0)), (12, (0, 180, 0)), (24, (0, 359.9, 0))])])
    s.box('Lamp red', parent, (at[0] - 0.4, at[1] + 0.06, at[2]), (0.45, 0.14, 0.24), (1, 0.05, 0.05), emissive=(1, 0.05, 0.05), emissive_intensity=10.0, shadows=False)
    s.box('Lamp blue', parent, (at[0] + 0.4, at[1] + 0.06, at[2]), (0.45, 0.14, 0.24), (0.1, 0.2, 1), emissive=(0.1, 0.2, 1), emissive_intensity=10.0, shadows=False)
    body = P.looping(s, parent, 'Sweep', spin, (at[0], at[1] + 0.2, at[2]))
    s.light('Sweep red', body, (0, 0, 0), 'Spot', (1.0, 0.05, 0.05), 450.0, 60, rot=(10, 0, 0), inner=14, outer=32)
    s.light('Sweep blue', body, (0, 0, 0), 'Spot', (0.1, 0.25, 1.0), 600.0, 60, rot=(10, 180, 0), inner=14, outer=32)
    for yaw, c in ((0, (1.0, 0.06, 0.05)), (180, (0.12, 0.25, 1.0))):
        A.glow_card(s, body, venue, 'Glare', add3(P_rot((0, 0.05, 0.3), yaw), (0, 0, 0)), 0.6, c, 2.0, (0, yaw, 0))


def P_rot(v, yaw):
    return A.rot(v, (0, yaw, 0))


def add3(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def cruiser(s, parent, venue, at, yaw=0.0, name='Cruiser', door_open=False, beams=True):
    """A police car facing +z at yaw 0, its centre at at (on the road). Returns its group."""
    g = s.entity(name, parent, at, (0, yaw, 0))
    A.model(s, g, 'Body', A.cruiser(venue, door_open))
    see_through(s.box('Windshield', g, (0, 1.2, 0.76), (1.5, 0.74, 0.02), (0.5, 0.6, 0.7), rot=(-40, 0, 0), rough=0.05, shadows=False), 0.12)
    for x in (-0.86, 0.86):
        see_through(s.box('Side glass', g, (x, 1.2, -0.25), (0.02, 0.56, 2.2), (0.5, 0.6, 0.7), rough=0.05, shadows=False), 0.12)
    for x in (-0.62, 0.62):
        s.box('Headlight', g, (x, 0.72, 2.45), (0.36, 0.14, 0.04), (1, 1, 0.9), emissive=(1, 1, 0.85), emissive_intensity=4.0, shadows=False)
        A.glow_card(s, g, venue, 'Headlight glare', (x, 0.72, 2.5), 0.5, (1.0, 0.95, 0.8), 1.2)
    s.light('Headlights', g, (0, 0.8, 2.6), 'Spot', (1.0, 0.95, 0.85), 1500.0, 60, rot=(5, 0, 0), inner=16, outer=36)
    lightbar(s, g, venue, (0, 1.65, -0.3))
    return g


def road(s, parent, venue, x0, x1, z0, z1, dashes=True):
    """A stretch of four-lane asphalt with its edge lines (and lane dashes)."""
    textured(s.slab('Asphalt', parent, x0, x1, -0.2, 0.0, z0, z1, (1, 1, 1), rough=0.9), venue, 'Asphalt', ((x1 - x0) / 4.0, (z1 - z0) / 4.0))
    for x in (x0 + 0.3, x1 - 0.45):
        s.slab('Edge line', parent, x, x + 0.15, 0.0, 0.012, z0, z1, LINE_WHITE, shadows=False)
    cx = (x0 + x1) / 2
    for x in (-0.2, 0.08):
        s.slab('Centre line', parent, cx + x, cx + x + 0.12, 0.0, 0.012, z0, z1, LINE_YELLOW, shadows=False)
    if dashes:
        z = z0
        while z < z1:
            for x in (-5.4, 5.4):
                s.slab('Dash', parent, cx + x - 0.07, cx + x + 0.07, 0.0, 0.012, z, z + 3.0, LINE_WHITE, shadows=False)
            z += 12.0


def burning_wreck(s, parent, venue, o):
    """The wreck at o (see A.wreck: the flatbed on its side along +z, the gear thrown toward -x),
    burning."""
    g = s.group('Wreck', parent, o)
    A.model(s, g, 'Wrecked rig', A.wreck(venue), material=A.mat(venue, 'Palette', rough=0.9))
    fire(s, g, venue, (6.6, 0.4, 14.6), 1.5, 320.0, name='Cab fire')
    fire(s, g, venue, (4.2, 0.0, 6.0), 1.1, 200.0, name='Deck fire')
    fire(s, g, venue, (1.4, 0.0, 9.2), 0.7, 80.0, smoke=False, name='Fuel fire')
    fire(s, g, venue, (2.9, 0.0, 1.0), 0.5, 50.0, smoke=False, name='Tyre fire')
    # Burning fuel across the road.
    textured(s.box('Fuel', g, (2.6, 0.006, 8.0), (5.5, 0.004, 7.5), (0.02, 0.02, 0.025), rough=0.05, metallic=0.7, shadows=False), venue, 'Asphalt', (1, 1))
    for i, (x, z) in enumerate(((0.3, 7.6), (1.9, 6.4), (3.2, 10.6), (2.4, 4.2))):
        body = P.looping(s, g, f'Fuel flame {i}', P.clip(venue, 'Flicker1', 19, [P.track('Scale', [(0, (1, 1, 1)), (5, (1.15, 1.3, 0.9)), (11, (0.85, 0.75, 1.15)), (19, (1, 1, 1))], 'SmoothStep')]), (x, 0, z), speed=1.0 + 0.2 * i)
        A.model(s, body, 'Flame', A.flame(venue), (0, 0, 0), (0, i * 70, 0), (0.5, 0.5 + 0.12 * i, 0.5), A.mat(venue, 'Palette', (0, 0, 0), glow=(1.0, 0.5, 0.12), power=5.0, additive=True, both=True), shadows=False)
    return g


def crash_site(s, parent, venue, o, flags, cop=None, ems=False, burning=True, lying=None, wreck_at=(3.0, 0.0, -2.0)):
    """The crash site around o: the wreck (burning), the band on the asphalt and a dropped stick.
    flags: the flags the figures change at ('wake': the drummer opens their eyes, 'nod': the cop
    nods). cop: (x, yaw, z) where the cop kneels giving CPR (None: no cop). ems: the medics and the
    ambulance. lying: who lies where ({member: (x, z, yaw)} relative to o) instead of the usual
    spread. Returns the drummer's hand in venue space."""
    ox, oy, oz = o
    if burning:
        burning_wreck(s, parent, venue, add3(o, wreck_at))
    g = s.group('Crash site', parent, o)
    # The band on the asphalt: the drummer nearest the shoulder, a stick beyond the fingers.
    looks = {'drummer': ('Son_01', '01_A'), 'guitar': ('Daughter_01', '02_C'), 'bass': ('Mother_01', '03_A'), 'vocals': ('SchoolBoy_01', '04_C')}
    where = lying or {'drummer': (-1.0, 1.0, 200), 'guitar': (-5.0, 4.0, 140), 'bass': (4.5, -1.5, 260), 'vocals': (-3.5, -3.0, 30)}
    lying = {who: (looks[who][0], looks[who][1], (x, 0, z), yaw) for who, (x, z, yaw) in where.items()}
    for who, (body, variant, at, yaw) in lying.items():
        model = P.figure(venue, f'Body_{who}', body, variant, P.STANDING, f'the {who} on the asphalt')
        if who == 'drummer':
            woke = P.figure(venue, 'Body_drummer_tapping', body, variant, P.TAPPING, 'the drummer, eyes open, tapping two fingers')
            P.lie(s, P.between(s, g, 'Drummer still', None, flags.get('wake'), 0.3, at), 'Drummer', model, at, yaw)
            if flags.get('wake'):
                P.lie(s, P.between(s, g, 'Drummer awake', flags['wake'], None, 0.3, at), 'Drummer awake', woke, at, yaw)
        else:
            P.lie(s, g, who.capitalize(), model, at, yaw)
    # The drummer's right hand: at the side, a little below the hip, as laid down by lie().
    drummer = lying['drummer']
    yaw = math.radians(drummer[3])
    local = (0.3, 0.06, -0.78)
    hand = (drummer[2][0] + local[0] * math.cos(yaw) + local[2] * math.sin(yaw), local[1], drummer[2][2] - local[0] * math.sin(yaw) + local[2] * math.cos(yaw))
    # The stick lies just beyond the fingers (which point at the feet), out from the body.
    stick = add3(hand, P_rot((0.14, -0.04, 0.34), drummer[3]))
    s.box('Drumstick', g, stick, (0.03, 0.41, 0.03), (0.85, 0.7, 0.45), rot=(90, drummer[3] + 24, 0), shape='Cylinder')
    s.box('Drumstick, snapped', g, add3(hand, P_rot((1.0, -0.04, 0.9), drummer[3])), (0.03, 0.2, 0.03), (0.85, 0.7, 0.45), rot=(90, drummer[3] + 80, 0), shape='Cylinder')
    s.light('Hand fill', g, (hand[0], 0.6, hand[2]), 'Point', (1.0, 0.75, 0.55), 5.0, 2.5)
    if cop:
        kneel = P.figure(venue, 'Cop_cpr', 'ShopKeeper_01', '04_B', P.KNEEL_CPR, 'the cop giving CPR')
        nod = P.figure(venue, 'Cop_cpr_nod', 'ShopKeeper_01', '04_B', P.KNEEL_NOD, 'the cop, the same small nod')
        cpos = (cop[0], -0.08, cop[2])
        # Compressions, about 110 a minute (in slow motion under a SlowMotion group).
        cpr = P.clip(venue, 'Compressions', 16, [P.track('Position', [(0, (0, 0, 0)), (5, (0, -0.07, 0.03)), (16, (0, 0, 0))], 'SmoothStep'),
                                                  P.track('Rotation', [(0, (0, 0, 0)), (5, (7, 0, 0)), (16, (0, 0, 0))], 'SmoothStep')])
        pumping = P.looping(s, P.between(s, g, 'Cop CPR', flags.get('cop'), flags.get('nod'), 0.2, cpos), 'CPR', cpr, cpos, rot=(0, cop[1], 0))
        P.place(s, pumping, 'Cop', kneel, (0, 0, 0), 0)
        if flags.get('nod'):
            P.place(s, P.between(s, g, 'Cop nod', flags['nod'], None, 0.2, cpos), 'Cop nodding', nod, cpos, cop[1])
    if ems:
        medic = P.figure(venue, 'Medic', 'Son_01', '02_A', P.KNEEL_CPR, 'an EMS worker')
        work = P.clip(venue, 'MedicWorking', 45, [P.track('Rotation', [(0, (0, 0, 0)), (20, (6, 4, 0)), (45, (0, 0, 0))], 'SmoothStep')])
        look = P.figure(venue, 'Medic_looks', 'Son_01', '02_A', P.KNEEL_LOOK, 'an EMS worker sees them stir')
        for i, (at, yaw) in enumerate((((-4.3, -0.08, 4.9), 210), ((4.0, -0.08, -2.4), 290), ((-2.8, -0.08, -3.6), 130))):
            if i == 0 and flags.get('wake'):
                P.place(s, P.looping(s, P.between(s, g, 'Medic working', None, flags['wake'], 0.2, at), 'Working', work, at, rot=(0, yaw, 0)), 'Medic', medic, (0, 0, 0), 0)
                P.place(s, P.between(s, g, 'Medic sees', flags['wake'], None, 0.2, at), 'Medic looking', look, at, yaw)
            else:
                P.place(s, P.looping(s, g, f'Medic {i}', work, at, speed=0.8 + 0.15 * i, rot=(0, yaw, 0)), 'Medic', medic, (0, 0, 0), 0)
            s.box('Kit bag', g, (at[0] + 0.5, 0.15, at[2] + 0.4), (0.5, 0.3, 0.3), (0.75, 0.1, 0.08), rot=(0, yaw, 0))
        amb = s.entity('Ambulance', g, (-9, 0, 8), (0, 160, 0))
        A.model(s, amb, 'Body', A.ambulance(venue))
        lightbar(s, amb, venue, (0, 3.1, 2.2))
        s.light('Ambulance work light', amb, (0, 2.6, -3.2), 'Spot', (1.0, 0.97, 0.9), 700.0, 22, rot=(35, 180, 0), inner=30, outer=55)
        s.box('Stretcher', g, (-6.2, 0.45, 4.2), (0.6, 0.08, 1.9), (0.85, 0.85, 0.2), rot=(0, 150, 0))
        s.box('Stretcher frame', g, (-6.2, 0.22, 4.2), (0.5, 0.4, 1.7), (0.4, 0.42, 0.45), rot=(0, 150, 0), metallic=0.8, rough=0.4)
    return (ox + hand[0], oy + hand[1], oz + hand[2])


def roadside(s, parent, venue, centre, half=60.0, shoulder_x=14.0, torn_z=None, trees=True):
    """The night around a stretch of road at centre: the stars, the treeline, the guardrails (torn
    open at torn_z on the +x side), flares set out across the lanes."""
    cx, cy, cz = centre
    A.model(s, parent, 'Night sky', A.sky_dome(venue, 'NightDome', 'Night', 170.0, 3), (cx, cy - 8, cz), (0, 0, 0), 1.0,
            A.mat(venue, 'Night', (0, 0, 0), glow=(1, 1, 1), power=1.0), shadows=False)
    s.slab('Ground', parent, cx - 170, cx + 170, cy - 1.2, cy - 0.3, cz - 170, cz + 170, (0.02, 0.03, 0.02), rough=1.0, shadows=False)
    s.slab('Shoulder R', parent, cx + shoulder_x, cx + shoulder_x + 6, -0.25, -0.02, cz - half, cz + half, GRAVEL)
    s.slab('Shoulder L', parent, cx - shoulder_x - 6, cx - shoulder_x, -0.25, -0.02, cz - half, cz + half, GRAVEL)
    s.slab('Verge R', parent, cx + shoulder_x + 6, cx + 120, -0.3, -0.06, cz - half * 2, cz + half * 2, GRASS)
    s.slab('Verge L', parent, cx - 120, cx - shoulder_x - 6, -0.3, -0.06, cz - half * 2, cz + half * 2, GRASS)
    if trees:
        A.model(s, parent, 'Treeline', A.treeline(venue, 'Treeline', -110, 110, shoulder_x + 12, 75, 110, 5), (cx, cy, cz), shadows=False)
    rail = A.guardrail(venue, 48.0, 'Guardrail48')
    for side in (-1, 1):
        x = cx + side * (shoulder_x + 1.2)
        yaw = 0 if side > 0 else 180
        if side > 0 and torn_z is not None:
            A.model(s, parent, 'Guardrail', rail, (x, 0, torn_z + 7), (0, 0, 0))
            A.model(s, parent, 'Guardrail', rail, (x, 0, torn_z - 7 - 48), (0, 0, 0))
            A.model(s, parent, 'Guardrail, torn', A.guardrail_torn(venue), (x, 0, torn_z), (0, 0, 0))
        else:
            for k in (-1, 0):
                A.model(s, parent, 'Guardrail', rail, (x, 0, cz + k * 48 + (48 if side < 0 else 0)), (0, yaw, 0))
    rng = random.Random(int(cx) + 9)
    for i in range(110):
        a, el = rng.uniform(0, 2 * math.pi), math.radians(rng.uniform(8, 80))
        size = rng.choice((0.18, 0.18, 0.25, 0.36))
        b = rng.uniform(2.0, 8.0)
        s.box('Star', parent, (cx + 160 * math.cos(el) * math.cos(a), cy - 8 + 160 * math.sin(el), cz + 160 * math.cos(el) * math.sin(a)), (size, size, size),
              (1, 1, 1), emissive=(0.9, 0.93, 1.0), emissive_intensity=b, shadows=False)
    A.glow_card(s, parent, venue, 'Moon', (cx - 60, cy + 70, cz + 120), 9.0, (0.8, 0.85, 1.0), 2.2, look_rotation((cx - 60, cy + 70, cz + 120), (cx, cy, cz)))
    A.glow_card(s, parent, venue, 'Moon halo', (cx - 60, cy + 70, cz + 120.5), 26.0, (0.3, 0.36, 0.55), 0.6, look_rotation((cx - 60, cy + 70, cz + 120), (cx, cy, cz)))


def beside_hand(hand, yaw, out=1.0, feet=0.6, up=0.18):
    """A camera position by a lying figure's hand (crash_site, the figure laid at yaw): out from the
    body, a little toward the feet, just off the road."""
    a = math.radians(yaw)
    return (hand[0] + math.cos(a) * out + math.sin(a) * feet, hand[1] + up, hand[2] - math.sin(a) * out + math.cos(a) * feet)


def ground_fog(s, parent, venue, centre, size=(40, 1.2, 40), rate=10, name='Ground fog'):
    A.particles(s, parent, name, centre, Shape='Box', BoxSize=list(size), Lifetime=[7.0, 12.0], Speed=[0.05, 0.3], Size=[2.5, 5.0], EndSize=1.6,
                StartColor=[0.55, 0.57, 0.62], StartColor2=[0.4, 0.42, 0.48], EndColor=[0.5, 0.5, 0.55], StartAlpha=0.16, EndAlpha=0.0, FadeIn=0.3,
                Intensity=1.0, Gravity=0.0, Drag=0.2, NoiseStrength=0.25, NoiseFrequency=0.2, Blend='Alpha', Lit=True, EmissionRate=rate, MaxParticles=140,
                Texture=A.tex(venue, 'Puff'), AngularVelocity=[-6, 6])


# ---- the highway --------------------------------------------------------------------------------
def highway():
    V = 'StoryHighway'
    s = Scene(seed=6601)
    s.venue = V
    root = s.group('Highway to the Afterlife: the highway')
    marks = s.group('Markers', root)
    s.info(marks, 'The Highway', 'Drumsmith', outdoor=True, half_width=60, desk_z=-30, sky_time=21.5, moon=0.8, haze=0.5)
    deck_y = 1.25
    band(s, marks, deck_y)
    s.camera_spot('Camera Wide', marks, (6.5, 4.2, -9.5), (0, 2.2, 4), 'Wide', 52)
    s.camera_spot('Camera Crane', marks, (-7, 8, -12), (0, 2, 4), 'Crane', 55)
    s.camera_spot('Camera Desk', marks, (2, 2.6, -11.0), (0, 2.4, 4), 'Desk', 28)
    s.camera_spot('Camera roadside', marks, (-9.5, 0.6, 1.0), (0, 2.6, 4.2), 'Custom', 48, 'roadside')
    s.camera_spot('Camera cab roof', marks, (0.6, 5.6, 9.6), (0, 1.6, 2.0), 'Custom', 58, 'cab')
    s.camera_spot('Camera chase bumper', marks, (-1.2, 1.1, -9.5), (0.5, 2.4, 4.5), 'Custom', 36, 'bumper')

    # The road and the shoulders, standing still; what scrolls is the markings, the rails, the poles
    # and the trees. In the closing bars the whole world turns about the trailer (trailer_slews): the
    # trailer slewing across the lane, seen from the deck. Everything on the road turns with it.
    slew_clip = P.clip(V, 'Slew', 120, [P.track('Rotation', [(0, (0, 0, 0)), (40, (0, 8, 2)), (120, (0, SLEW_YAW, 0))], 'SmoothStep'),
                                        P.track('Position', [(0, (0, 0, 0)), (120, SLEW_SHIFT)], 'SmoothStep')])
    world = s.group('World', P.play(s, root, 'Slew', 'trailer_slews', slew_clip))
    textured(s.slab('Asphalt', world, -11, 11, -0.2, 0.0, -420, 140, (1, 1, 1), rough=0.9), V, 'Asphalt', (5.5, 140))
    for x in (-10.7, 10.55):
        s.slab('Edge line', world, x, x + 0.15, 0.0, 0.01, -420, 140, LINE_WHITE, shadows=False)
    for x in (-0.2, 0.08):
        s.slab('Centre line', world, x, x + 0.12, 0.0, 0.01, -420, 140, LINE_YELLOW, shadows=False)
    s.slab('Gravel L', world, -15, -11, -0.25, -0.02, -420, 140, GRAVEL)
    s.slab('Gravel R', world, 11, 15, -0.25, -0.02, -420, 140, GRAVEL)
    s.slab('Field L', world, -260, -15, -0.4, -0.1, -420, 140, GRASS)
    s.slab('Field R', world, 15, 260, -0.4, -0.1, -420, 140, GRASS)
    rng = random.Random(7)
    for i in range(18):
        x = rng.choice((-1, 1)) * rng.uniform(150, 240)
        s.box(f'Hill {i}', world, (x, -6, rng.uniform(-400, 120)), (rng.uniform(70, 130), rng.uniform(22, 46), rng.uniform(70, 130)), (0.02, 0.03, 0.025), shape='Sphere', shadows=False)
    # A town's glow far ahead, and its lights.
    for i in range(40):
        x, y = rng.uniform(-150, 150), rng.uniform(0.5, 9)
        c = rng.choice(((1.0, 0.8, 0.5), (1.0, 0.9, 0.75), (0.7, 0.85, 1.0), (1.0, 0.4, 0.3)))
        s.box('Town light', world, (x, y, 138 + rng.uniform(0, 3)), (0.9, 0.9, 0.2), c, emissive=c, emissive_intensity=6.0, shadows=False)
    s.light('Moon', world, (0, 60, -40), 'Directional', (0.5, 0.58, 0.85), 1.6, 400, rot=(38, 25, 0), shadows=True, show='Static')

    # Moving at 30 m/s until the wreck: lane dashes and rail posts every 12 m, poles every 48 m,
    # the trees every 96 m.
    moving = P.between(s, world, 'Road moving', None, 'wreck', 0.2)
    dash_clip = P.clip(V, 'RoadDashes', 12, [P.track('Position', [(0, (0, 0, 0)), (12, (0, 0, -12))])])

    def lane(parent):
        for k in range(-34, 13):
            for x in (-5.4, 5.4):
                s.slab('Dash', parent, x - 0.07, x + 0.07, 0.0, 0.012, k * 12, k * 12 + 3, LINE_WHITE, shadows=False)
        rail = A.guardrail(V, 96.0)
        for k in range(-5, 2):
            A.model(s, parent, 'Guardrail', rail, (15.4, 0, k * 96), shadows=False)
            A.model(s, parent, 'Guardrail', rail, (-15.4, 0, k * 96 + 96), (0, 180, 0), shadows=False)
        for k in range(-17, 7):
            for side in (-1, 1):
                s.box('Delineator', parent, (side * 11.6, 0.5, k * 24), (0.06, 1.0, 0.03), (0.9, 0.9, 0.9), emissive=(1.0, 0.6, 0.1), emissive_intensity=1.2, shadows=False)

    def poles(parent):
        for k in range(-8, 4):
            z = k * 48
            for side in (-1, 1):
                x = side * 13
                s.box('Pole', parent, (x, 5, z), (0.25, 10, 0.25), STEEL, shadows=False, shape='Cylinder')
                s.box('Arm', parent, (x - side * 1.5, 9.9, z), (3.0, 0.15, 0.2), STEEL, shadows=False)
                s.box('Lamp', parent, (x - side * 2.8, 9.75, z), (0.6, 0.12, 0.3), (1, 0.85, 0.55), emissive=(1, 0.8, 0.5), emissive_intensity=9.0, shadows=False)
                A.glow_card(s, parent, V, 'Lamp glare', (x - side * 2.8, 9.6, z), 1.6, (1.0, 0.75, 0.4), 2.5, (90, 0, 0))
                if -2 <= k <= 1:
                    s.light('Pole light', parent, (x - side * 2.8, 9.5, z), 'Spot', (1.0, 0.78, 0.5), 1500.0, 28, rot=(90, 0, 0), inner=32, outer=58)

    def trees(parent):
        A.model(s, parent, 'Treeline', A.treeline(V, 'TreesLoop', -480, 192, 19, 80, 210, 5, period=96.0), shadows=False)
        # The gantry sign that comes round every 96 m would be too many: one billboard per loop.
        for k in range(-4, 2):
            s.box('Reflector post', parent, (17.5, 0.6, k * 96 + 30), (0.08, 1.2, 0.08), STEEL, shadows=False)

    lane(P.looping(s, moving, 'Dashes', dash_clip))
    pole_clip = P.clip(V, 'RoadPoles', 48, [P.track('Position', [(0, (0, 0, 0)), (48, (0, 0, -48))])])
    poles(P.looping(s, moving, 'Poles', pole_clip))
    tree_clip = P.clip(V, 'RoadTrees', 96, [P.track('Position', [(0, (0, 0, 0)), (96, (0, 0, -96))])])
    trees(P.looping(s, moving, 'Trees', tree_clip))
    # The air going by: dust and grit streaking back past the deck.
    A.particles(s, moving, 'Road grit', (0, 1.6, 30), (-90, 0, 0), Shape='Box', BoxSize=[26, 5, 4], Lifetime=[1.2, 2.0], Speed=[28, 32], Size=[0.02, 0.05],
                StartColor=[0.9, 0.8, 0.65], StartColor2=[0.6, 0.6, 0.65], EndColor=[0.5, 0.5, 0.5], StartAlpha=0.5, EndAlpha=0.0, Intensity=1.5, Gravity=0.0, Drag=0.0,
                NoiseStrength=0.3, Blend='Additive', EmissionRate=45, MaxParticles=120, Alignment='Stretched', StretchFactor=0.05, FadeIn=0.1)
    # Stopped: the markings, rails, poles and trees where they stood.
    still = P.between(s, world, 'Road stopped', 'wreck', None, 0.2)
    lane(still)
    poles(still)
    trees(still)

    # The flatbed and its tractor, the band on the deck.
    rig = s.group('Rig', root)
    A.model(s, rig, 'Flatbed', A.flatbed(V))
    wheel_clip = P.clip(V, 'WheelSpin', 6, [P.track('Rotation', [(0, (0, 0, 0)), (3, (180, 0, 0)), (6, (359.9, 0, 0))])])
    for z in (0.0, 1.3, 6.0, 7.3):
        for x in (-2.6, 2.6):
            spinner = P.looping(s, P.between(s, rig, 'Wheel', None, 'wreck', 0.2, (x, 0.55, z)), 'Wheel', wheel_clip, (x, 0.55, z))
            A.model(s, spinner, 'Tyre', A.wheel(V))
            s.box('Lug', spinner, (0.21 if x > 0 else -0.21, 0.16, 0), (0.03, 0.1, 0.1), (0.75, 0.75, 0.78), metallic=0.9, rough=0.3, shadows=False)
    for i, x in enumerate((-2.0, -0.7, 0.7, 2.0)):
        s.light(f'Truss wash {i}', rig, (x, 5.0, 8.3), 'Spot', (0.6, 0.6, 1.0) if i % 2 else (1.0, 0.5, 0.3), 1600.0, 14,
                rot=look_rotation((x, 5.0, 8.3), (x * 0.5, deck_y + 1, 2.5)), inner=22, outer=40, show='Wash', group=i)
    for i, x in enumerate((-2.6, 2.6)):
        s.light(f'Deck beam {i}', rig, (x, 5.1, 8.4), 'Spot', (1.0, 0.3, 0.2) if i else (0.3, 0.5, 1.0), 2500.0, 40, rot=(-20, 180 + x * 8, 0), inner=4, outer=9, show='Beam', group=i)
        s.light(f'Deck strobe {i}', rig, (x * 0.4, 5.0, 8.3), 'Point', (1, 1, 1), 900.0, 16, show='Strobe', group=i)
    A.model(s, rig, 'Tractor', A.tractor(V), (0, 0, 11.4))
    for x in (-0.95, 0.95):
        A.glow_card(s, rig, V, 'Tractor headlight', (x, 1.15, 15.12), 0.8, (1.0, 0.95, 0.8), 6.0)
    s.light('Tractor headlights', rig, (0, 1.3, 15.3), 'Spot', (1.0, 0.93, 0.8), 6000.0, 90, rot=(6, 0, 0), inner=14, outer=32)
    for x in (-1.38, 1.38):
        A.particles(s, P.between(s, rig, 'Exhaust', None, 'wreck', 0.2), 'Stack smoke', (x, 5.9, 10.6), Shape='Cone', ConeAngle=8, ShapeRadius=0.1, Lifetime=[0.8, 1.4],
                    Speed=[2, 4], Size=[0.3, 0.6], EndSize=4.0, StartColor=[0.12, 0.12, 0.13], StartColor2=[0.2, 0.2, 0.2], EndColor=[0.1, 0.1, 0.1], StartAlpha=0.5,
                    EndAlpha=0.0, Gravity=0.0, Drag=0.2, NoiseStrength=0.4, Blend='Alpha', EmissionRate=14, MaxParticles=40, Texture=A.tex(V, 'Puff'), SimulationSpace='Local')

    # The cruiser behind, the cop at the wheel: driving, then the radio, then the nod.
    car_at = (0.0, 0.0, -13.0)
    cruiser(s, world, V, car_at)
    seat = (car_at[0] - 0.45, 0.32, car_at[2] - 0.2)
    for flag_after, flag_before, pose, label in ((None, 'cop_radio', P.DRIVING, 'Cop_driving'), ('cop_radio', 'cop_nods', P.RADIO, 'Cop_radio'),
                                                 ('cop_nods', None, P.NODDING, 'Cop_nodding')):
        model = P.figure(V, label, 'ShopKeeper_01', '04_B', pose, 'the highway cop')
        P.place(s, P.between(s, world, label, flag_after, flag_before, 0.05, seat), 'Cop', model, seat, 0)
    s.box('Steering wheel', world, (seat[0], 0.98, seat[2] + 0.5), (0.34, 0.03, 0.34), (0.03, 0.03, 0.03), rot=(-65, 0, 0), shape='Cylinder', shadows=False)
    s.light('Dash glow', world, (seat[0], 1.0, seat[2] + 0.6), 'Point', (0.4, 0.6, 1.0), 2.5, 2.5)
    s.light('Stage spill on the cop', world, (seat[0] + 0.3, 1.5, car_at[2] + 1.3), 'Point', (1.0, 0.7, 0.6), 3.5, 3.5)
    # The helicopter's searchlight on the deck.
    heli = (-28.0, 34.0, -48.0)
    s.light('Searchlight', root, heli, 'Spot', (0.85, 0.92, 1.0), 14000.0, 90, rot=look_rotation(heli, (0, 1.5, 4)), inner=2.0, outer=4.5)

    # The marked stretch of shoulder (the finale comes back to it): mile marker 66, a billboard,
    # the rail the trailer goes through, the wreck.
    W = (21.0, 0.0, -60.0)
    A.model(s, world, 'Mile marker', A.sign_face(V, 'MileMarker'), (W[0] - 5.2, 1.6, W[2] + 13), (0, 180, 0), (0.45, 0.6, 1), A.mat(V, 'MileMarker', glow=(1, 1, 1), power=0.5), shadows=False)
    s.box('Mile marker post', world, (W[0] - 5.2, 0.5, W[2] + 13.04), (0.08, 1.0, 0.05), STEEL)
    bb = (W[0] + 15, 9.5, W[2] + 6)
    A.model(s, world, 'Billboard', A.sign_face(V, 'Billboard'), bb, (0, 180 - 25, 0), (7.5, 3.6, 1), A.mat(V, 'Billboard', glow=(1, 1, 1), power=1.1), shadows=False)
    s.box('Billboard back', world, add3(bb, P_rot((0, 0, 0.2), -25)), (15.4, 7.6, 0.3), (0.05, 0.05, 0.05), rot=(0, -25, 0))
    for dx in (-5, 0, 5):
        s.box('Billboard leg', world, add3((bb[0], 3.0, bb[2]), P_rot((dx, 0, 0.3), -25)), (0.35, 6.0, 0.35), STEEL)
    for dx in (-5, 0, 5):
        lamp = add3((bb[0], 5.6, bb[2]), P_rot((dx, 0, -2.2), -25))
        s.light('Billboard lamp', world, lamp, 'Spot', (1.0, 0.95, 0.85), 300.0, 14, rot=look_rotation(lamp, (bb[0], bb[1], bb[2])), inner=30, outer=55)
    s.slab('Shoulder asphalt', world, W[0] - 9, W[0] + 9, -0.08, 0.0, W[2] - 12, W[2] + 14, ASPHALT, rough=0.95)
    # The burning trailer shows from the crash, the bodies from the next beat.
    burning_wreck(s, P.between(s, world, 'Wreck', 'wreck', None, 0.25, W), V, add3(W, (3, 0, -2)))
    hand = slewed(crash_site(s, P.between(s, world, 'Bodies', 'bodies', None, 0.01, W), V, W, {}, burning=False))
    # The explosion: a fireball up off the trailer and gone in two seconds, a ring of fire along
    # the road, and everything it throws.
    boom = add3(W, (6, 0, 5))
    ball_clip = P.clip(V, 'Fireball', 66, [P.track('Scale', [(0, (0.05, 0.05, 0.05)), (7, (13, 10, 13)), (30, (10, 12, 10)), (66, (0.01, 0.01, 0.01))], 'SmoothStep'),
                                           P.track('Position', [(0, (0, 0, 0)), (66, (0, 9, 0))], 'SmoothStep')])
    ball = P.play(s, world, 'Fireball', 'wreck', ball_clip, (boom[0], 3.0, boom[2]))
    see_through(s.box('Fireball', ball, (0, 0, 0), (1, 1, 1), FIRE, emissive=FIRE, emissive_intensity=14.0, shape='Sphere', shadows=False), 0.85, additive=True)
    see_through(s.box('Fireball core', ball, (0, 0, 0), (0.62, 0.62, 0.62), (1, 0.9, 0.6), emissive=(1, 0.9, 0.6), emissive_intensity=24.0, shape='Sphere', shadows=False), 1.0, additive=True)
    # The blast's light: there for two seconds (the clip parks it far underground before and after).
    flash_clip = P.clip(V, 'FireballLight', 70, [P.track('Position', [(0, (0, -4000, 0)), (1, (0, 0, 0)), (20, (0, 4, 0)), (64, (0, 8, 0)), (70, (0, -4000, 0))])])
    s.light('Fireball light', P.play(s, world, 'Fireball light', 'wreck', flash_clip, (boom[0], 3.0, boom[2])), (0, 0, 0), 'Point', (1.0, 0.6, 0.25), 20000.0, 120)
    burst = P.between(s, world, 'Blast', 'wreck', None, 0.01, boom)
    A.particles(s, burst, 'Blast debris', (boom[0], 1.5, boom[2]), Looping=False, Duration=1.0, Shape='Sphere', ShapeRadius=1.5, Lifetime=[2.0, 4.5], Speed=[8, 30], Size=[0.08, 0.3],
                StartColor=[1.0, 0.8, 0.4], StartColor2=[1.0, 0.45, 0.1], EndColor=[0.6, 0.1, 0.02], Intensity=6.0, Gravity=0.9, Drag=0.2, NoiseStrength=0.5,
                Blend='Additive', EmissionRate=0, BurstCount=260, MaxParticles=300, Alignment='Stretched', StretchFactor=0.05, EndSize=0.4, FadeIn=0.01)
    A.particles(s, burst, 'Blast smoke', (boom[0], 2.5, boom[2]), Looping=False, Duration=1.0, Shape='Sphere', ShapeRadius=3.0, Lifetime=[4.0, 8.0], Speed=[2, 9], Size=[2.5, 5.0],
                StartColor=[0.3, 0.17, 0.1], StartColor2=[0.16, 0.12, 0.1], EndColor=[0.08, 0.07, 0.07], StartAlpha=0.5, EndAlpha=0.0, Gravity=-0.12, Drag=0.6,
                NoiseStrength=0.6, NoiseFrequency=0.3, Blend='Alpha', EmissionRate=0, BurstCount=70, MaxParticles=80, EndSize=3.0, FadeIn=0.05, Texture=A.tex(V, 'Puff'))

    # Story shots.
    kit = (0.0, deck_y + 0.6, 4.0)
    shot(s, marks, 'highway_open', (3.5, 0.34, -0.9), (2.62, 0.55, 0.3), 46, 12, focus=True,
         via=[((3.45, 1.0, 0.4), (2.2, 1.2, 2.2), 50), ((1.5, 1.62, 2.9), (0.2, 1.5, 4.6), 44), ((2.6, 2.6, 7.4), (0, 1.9, 2.5), 58)],
         end=((1.6, 4.6, 9.4), (0, 1.3, -5.5), 62))
    cop_face = (seat[0], 1.28, seat[2] + 0.1)
    shot(s, marks, 'cop_watching', (seat[0] + 0.3, 1.4, car_at[2] + 2.3), cop_face, 38, 6, focus=True, end=((seat[0] + 0.1, 1.36, car_at[2] + 1.75), cop_face, 30))
    shot(s, marks, 'heli_chase', heli, (0, 1.0, -6), 44, 9, hand=True,
         via=[((heli[0] + 1.5, heli[1] - 0.4, heli[2] + 2.5), (1.5, 1.0, 26), 7), ((heli[0] + 2.5, heli[1] - 0.6, heli[2] + 4.5), (0.4, 2.2, 8.5), 6.5)],
         end=((heli[0] + 4, heli[1] - 1, heli[2] + 7), (0, 2.4, 5.2), 8))
    shot(s, marks, 'foot_on_monitor', (-0.3, 1.42, -1.75), (-1.9, 2.7, 2.5), 34, 5, hand=True, end=((0.5, 1.5, -1.9), (-1.8, 2.6, 2.5), 30))
    shot(s, marks, 'cop_radio', (seat[0] + 1.75, 1.3, seat[2] + 0.75), cop_face, 34, 5, focus=True, end=((seat[0] + 1.5, 1.28, seat[2] + 0.5), cop_face, 28))
    shot(s, marks, 'cop_nods', (seat[0] - 0.2, 1.38, car_at[2] + 1.9), cop_face, 30, 5, focus=True, end=((seat[0] - 0.05, 1.34, car_at[2] + 1.5), cop_face, 22))
    shot(s, marks, 'heli_again', (40, 26, 22), (0, 1.5, 0), 34, 8, hand=True, via=[((44, 24, 2), (0, 1.5, 0), 26)], end=((36, 22, -20), (0, 1.5, 2), 20))
    shot(s, marks, 'trailer_slews', (2.7, 2.5, -1.0), (-0.5, 1.7, 4.2), 60, 4.5, hand=True, end=((3.1, 2.2, -1.9), (-0.9, 1.5, 4.6), 52))
    Ws = slewed((W[0] + 4, 1.5, W[2] + 4))
    shot(s, marks, 'wreck', (Ws[0] - 34, 24, Ws[2] - 26), Ws, 26, 7, hand=True, via=[((Ws[0] - 33, 23, Ws[2] - 28), (Ws[0], 6, Ws[2]), 40)],
         end=((Ws[0] - 30, 20, Ws[2] - 30), Ws, 24))
    lay = 200 + SLEW_YAW        # the drummer's body, turned with the road
    shot(s, marks, 'bodies', beside_hand(hand, lay, 1.5, 1.1, 0.5), hand, 34, 40, focus=True, end=(beside_hand(hand, lay, 0.95, 0.6, 0.12), (hand[0], 0.05, hand[2]), 28))
    write(s, V, 'The Highway')


# ---- hell ---------------------------------------------------------------------------------------
def hell():
    V = 'StoryHell'
    s = Scene(seed=6602)
    s.venue = V
    root = s.group('Highway to the Afterlife: hell')
    marks = s.group('Markers', root)
    s.info(marks, 'Hell', 'Drumsmith', outdoor=False, room_back=-40, room_ceiling=60, half_width=22, desk_z=-14,
           ambient=(0.012, 0.002, 0.0015), fog_color=(0.016, 0.01, 0.009), haze=0.1)
    band(s, marks, 0.0)
    s.camera_spot('Camera Wide', marks, (0, 4.6, -11.5), (0, 2.2, 4), 'Wide', 58)
    s.camera_spot('Camera Crane', marks, (8, 9, -9), (0, 1.6, 4), 'Crane', 55)
    s.camera_spot('Camera Desk', marks, (-1.5, 2.8, -10), (0, 2.0, 4), 'Desk', 30)

    # 1. The crash site, until they fall.
    crash = P.between(s, root, 'The crash site', None, 'fell', 2.5)
    # Each place has its own rig (a VenueShowLight under a story group is cued only while it shows).
    for i, x in enumerate((-3.5, 3.5, -1.2, 1.2)):
        s.light(f'Crash wash {i}', crash, (x, 7, -3), 'Spot', (0.7, 0.8, 1.0), 700.0, 18, rot=look_rotation((x, 7, -3), (x * 0.4, 1, 3.5)), inner=22, outer=42, show='Wash', group=i)
    road(s, crash, V, -14, 14, -70, 70)
    roadside(s, crash, V, (0, 0, 0), 70.0, 14.0, torn_z=6.0)
    s.light('Moon', crash, (0, 40, -20), 'Directional', (0.4, 0.5, 0.8), 2.4, 300, rot=(42, 150, 0), shadows=True)
    for x, z in ((-30, -30), (30, 30), (-30, 40), (30, -40)):
        s.light('Night fill', crash, (x, 26, z), 'Point', (0.3, 0.4, 0.75), 2600.0, 90)
    cruiser(s, crash, V, (-7.5, 0, -9), 24, door_open=True)
    burning_wreck(s, crash, V, (9.0, 0, -1.0))
    spots = {'drummer': (DRUMMER[0] + 0.3, DRUMMER[1] + 0.6, 180), 'guitar': (GUITAR[0], GUITAR[1], 172), 'bass': (BASS[0], BASS[1], 188), 'vocals': (VOCALS[0], VOCALS[1], 180)}
    hand = crash_site(s, crash, V, (0, 0, 0), {}, burning=False, lying=spots)
    for i, (x, z, yaw) in enumerate(((-9.5, -20, 20), (-3.0, -24, -30), (4.5, -22, 60), (-11.5, 6, 80))):
        A.flare(s, crash, V, f'Flare {i}', (x, 0, z), yaw)
    ground_fog(s, crash, V, (0, 0.5, 0), (46, 1.0, 60), 12)
    s.box('Hubcap', crash, (-4.6, 0.03, 0.4), (0.42, 0.04, 0.42), (0.7, 0.72, 0.75), metallic=0.95, rough=0.25, shape='Cylinder', rot=(4, 0, 3))
    # The cop: out of the car, running to the drummer, kneeling beside the body.
    car_door = (-5.6, 0, -7.4)
    kneel_at = (-0.75, -0.08, DRUMMER[1] + 1.7)      # at the chest of the drummer's body
    cop_run = P.figure(V, 'Cop_running', 'ShopKeeper_01', '04_B', P.FISTS, 'the cop running in')
    kneel = P.figure(V, 'Cop_kneeling', 'ShopKeeper_01', '04_B', P.KNEEL_LOOK, 'the cop kneeling by the drummer')
    run_yaw = P.yaw_to(car_door, kneel_at)
    run_clip = P.path_clip(V, 'CopRuns', [(0, 0, 0), (0, 0.12, 4.5), (0, 0, 9.0), (0, 0.12, math.dist(car_door, kneel_at))], 3.0)
    runner = P.play(s, P.between(s, crash, 'Cop until he kneels', None, 'cop_kneels', 0.2, car_door), 'Cop runs', 'cop_runs', run_clip, car_door, (0, run_yaw, 0))
    P.place(s, runner, 'Cop', cop_run, (0, 0, 0), 0)
    P.place(s, P.between(s, crash, 'Cop kneeling', 'cop_kneels', None, 0.3, kneel_at), 'Cop', kneel, kneel_at, 90)

    # 2. The fall: a shaft of rock streaming upward past the band, embers and ash racing up, the
    # road a slit of light above and the glow of the pit below.
    fall = P.between(s, P.between(s, root, 'The fall', 'fell', None, 1.5), 'Falling', None, 'landed', 0.3)
    rock_glow = A.mat(V, 'Rock', (1, 1, 1), glow=(0.5, 0.1, 0.03), power=0.5, tiling=None)
    shaft_glow = A.mat(V, 'Rock', (0.6, 0.5, 0.5), glow=(1.0, 0.22, 0.06), power=0.8, tiling=(2, 2))
    # The walls' shape repeats every SHAFT_PERIOD metres, so the loop never jumps.
    wall_clip = P.clip(V, 'ShaftWalls', 80, [P.track('Position', [(0, (0, 0, 0)), (80, (0, A.SHAFT_PERIOD, 0))])])
    walls = P.looping(s, fall, 'Walls', wall_clip)
    A.model(s, walls, 'Shaft', A.shaft_walls(V, 15.0, 390.0), (0, 0, 3), (0, 0, 0), 1.0, shaft_glow, shadows=False)
    # Crags off the walls, faster than the walls (nearer): the same few every 24 m.
    ledge_clip = P.clip(V, 'ShaftLedges', 20, [P.track('Position', [(0, (0, 0, 0)), (20, (0, 24, 0))])])
    ledges = P.looping(s, fall, 'Ledges', ledge_clip)
    rng = random.Random(11)
    crag = A.spikes(V, 'Crag', 5, 1.4, (2.5, 6.0), 4)
    base = [(rng.uniform(0, 2 * math.pi), rng.uniform(0, 24), rng.uniform(70, 110), rng.uniform(1.0, 2.0)) for _ in range(6)]
    for k in range(-4, 4):
        for a, y, tilt, size in base:
            A.model(s, ledges, 'Crag', crag, (math.sin(a) * 12.5, k * 24 + y, math.cos(a) * 12.5 + 3), (tilt, math.degrees(a) + 180, 0), size, shaft_glow, shadows=False)
    A.particles(s, fall, 'Embers racing up', (0, -30, 3), Shape='Box', BoxSize=[24, 6, 24], Lifetime=[1.6, 2.6], Speed=[24, 40], Size=[0.04, 0.1],
                StartColor=[1.0, 0.7, 0.3], StartColor2=[1.0, 0.35, 0.08], EndColor=[1.0, 0.2, 0.03], Intensity=6.0, Gravity=0.0, Drag=0.0, NoiseStrength=1.5,
                NoiseFrequency=0.4, Blend='Additive', EmissionRate=110, MaxParticles=320, Alignment='Stretched', StretchFactor=0.06, FadeIn=0.05)
    A.particles(s, fall, 'Smoke racing up', (0, -30, 3), Shape='Box', BoxSize=[22, 4, 22], Lifetime=[2.2, 3.2], Speed=[18, 26], Size=[2.0, 4.0], EndSize=1.6,
                StartColor=[0.25, 0.08, 0.04], StartColor2=[0.1, 0.06, 0.05], EndColor=[0.06, 0.05, 0.05], StartAlpha=0.22, EndAlpha=0.0, Gravity=0.0, Drag=0.0,
                NoiseStrength=0.8, Blend='Alpha', EmissionRate=14, MaxParticles=60, Texture=A.tex(V, 'Puff'), FadeIn=0.2)
    ash_clip = P.clip(V, 'AshRising', 30, [P.track('Position', [(0, (0, 0, 0)), (30, (0, 10, 0))])])
    ash = P.looping(s, fall, 'Ash', ash_clip)
    flakes = [(rng.uniform(0, 2 * math.pi), rng.uniform(2.5, 12), rng.uniform(0, 10), rng.uniform(0, 90), rng.uniform(0, 90)) for _ in range(22)]
    for copy in range(-3, 3):
        for a, r, y, rx, ry in flakes:
            s.box('Ash', ash, (math.sin(a) * r, copy * 10 + y, math.cos(a) * r + 3), (0.05, 0.05, 0.05), (0.5, 0.48, 0.45),
                  emissive=(0.5, 0.25, 0.15), emissive_intensity=2.0, shadows=False, rot=(rx, ry, 0))
    s.box('The road, far above', fall, (0, 150, 3), (9, 0.5, 0.5), WHITE, emissive=(1, 0.95, 0.85), emissive_intensity=30, shadows=False)
    A.model(s, fall, 'The road, its glow', A.light_card(V), (0, 149, 3), (-90, 0, 0), (26, 7, 1), A.mat(V, 'Glow', (0, 0, 0), glow=(0.9, 0.92, 1.0), power=3.0, additive=True, both=True), shadows=False)
    s.light('Slit light', fall, (0, 70, 3), 'Spot', (0.85, 0.9, 1.0), 60000.0, 110, rot=(90, 0, 0), inner=5, outer=11)
    s.light('Pit glow', fall, (0, -14, 3), 'Point', (1.0, 0.3, 0.08), 2600.0, 40)
    for i, x in enumerate((-3.0, 3.0)):
        s.light(f'Fall wash {i}', fall, (x, -7, -1), 'Spot', (1.0, 0.35, 0.1), 1500.0, 22, rot=look_rotation((x, -7, -1), (x * 0.4, 1.5, 3.5)), inner=22, outer=42, show='Wash', group=i)
        s.light(f'Fall wash {i + 2}', fall, (x * 0.5, 12, -2), 'Spot', (0.75, 0.82, 1.0), 1500.0, 24, rot=look_rotation((x * 0.5, 12, -2), (x * 0.3, 1.5, 3.5)), inner=18, outer=36, show='Wash', group=i + 2)
    A.glow_card(s, fall, V, 'The pit', (0, -70, 3), 60.0, (1.0, 0.22, 0.03), 3.0, (90, 0, 0))

    # 3. Hell.
    h = P.between(s, root, 'Hell', 'landed', None, 0.4)
    C = (0.0, 0.0, 2.0)                       # the arena's centre
    steps, rise, run, z0 = 12, 0.75, 1.5, -7.0
    top_y = steps * rise
    zt = z0 - steps * run
    A.model(s, h, 'Cavern', A.cavern(V, (0.0, 0.0, -6.0), 60.0, 44.0), (0, 0, 0), (0, 0, 0), 1.0, A.mat(V, 'Rock', (1, 1, 1), glow=(0.55, 0.09, 0.03), power=0.2), shadows=False)
    A.model(s, h, 'Lava lake', A.lava(V, 160.0), (0, -1.9, -6), (0, 0, 0), 1.0, A.mat(V, 'Lava', (0.2, 0.05, 0.02), glow=(1, 1, 1), power=2.0), shadows=False)
    drift = P.clip(V, 'LavaDrift', 900, [P.track('Position', [(0, (0, 0, 0)), (450, (9, 0, 6)), (900, (0, 0, 0))], 'SmoothStep')])
    A.model(s, P.looping(s, h, 'Lava shimmer', drift), 'Lava crust', A.lava(V, 160.0), (3, -1.86, -9), (0, 37, 0), 1.3,
            A.mat(V, 'Lava', (0, 0, 0), glow=(1.0, 0.6, 0.3), power=0.9, additive=True), shadows=False)
    A.model(s, h, 'Arena', A.arena(V, 15.5, C), (0, 0, 0), (0, 0, 0), 1.0, A.mat(V, 'HellFloor', (1, 1, 1), glow=(1.0, 0.75, 0.5), power=2.4, glow_tex='HellGlow', rough=0.85))
    terrace_model, tiers = A.terraces(V, C)
    A.model(s, h, 'Terraces', terrace_model, (0, 0, 0), (0, 0, 0), 1.0, A.mat(V, 'Rock', (1.25, 1.0, 0.95), glow=(0.5, 0.1, 0.03), power=0.1))
    A.model(s, h, 'Stairs and dais', A.hell_stairs(V, steps, rise, run, z0))
    throne_at = (0.0, top_y, zt - 5.2)
    A.model(s, h, 'Throne', A.throne(V), throne_at, (0, 0, 0), 1.3)
    # The rock the throne backs onto, and the skull carved over it.
    massif = A.rock(V, 3)
    rock_mat = A.mat(V, 'Rock', (1, 1, 1), glow=(0.55, 0.09, 0.03), power=0.2, tiling=(4, 4))
    A.model(s, h, 'Massif', massif, (0, -6, zt - 19), (0, 20, 0), (15, 40, 9), rock_mat)
    A.model(s, h, 'Massif shoulder L', massif, (-17, -6, zt - 16), (0, 80, 0), (9, 26, 8), rock_mat)
    A.model(s, h, 'Massif shoulder R', massif, (17, -6, zt - 16), (0, 140, 0), (9, 24, 8), rock_mat)
    skull_at = (0.0, top_y + 12.5, zt - 11.5)
    A.model(s, h, 'The skull', A.skull(V), skull_at, (12, 0, 0), 5.0, A.mat(V, 'Palette', (1, 1, 1), glow=(1.0, 0.35, 0.12), power=0.25))
    A.model(s, h, 'The skull, its eyes', A.skull_eyes(V), skull_at, (12, 0, 0), 5.0, A.mat(V, 'Palette', (0, 0, 0), glow=(1.0, 0.4, 0.08), power=14.0), shadows=False)
    for x in (-2.0, 2.0):
        eye = (x, skull_at[1] - 0.9, skull_at[2] + 5.1)
        A.glow_card(s, h, V, 'Skull eye glare', eye, 3.2, (1.0, 0.4, 0.1), 1.0)
        s.light('Skull eye', h, eye, 'Spot', (1.0, 0.4, 0.1), 3500.0, 70, rot=look_rotation(eye, (x * 2.2, 0, 4)), inner=4, outer=9)
    # Lava down the rock either side of the throne.
    for side in (-1, 1):
        x = side * 13.5
        fall_mat = A.mat(V, 'Lava', (0, 0, 0), glow=(1.0, 0.8, 0.6), power=5.0, tiling=(1, 6))
        A.model(s, h, 'Lava fall', A.lava(V, 160.0), (x, 12, zt - 11.4), (-84, side * 12, 0), (0.016, 1, 0.19), fall_mat, shadows=False)
        A.glow_card(s, h, V, 'Lava fall glow', (x, 10, zt - 10.8), 13.0, (1.0, 0.3, 0.05), 0.8)
        s.light('Lava fall light', h, (x, 8, zt - 8), 'Point', (1.0, 0.35, 0.08), 2200.0, 40)
        A.particles(s, h, 'Lava fall spray', (x, -1.2, zt - 9.6), Shape='Cone', ConeAngle=40, ShapeRadius=1.2, Lifetime=[0.8, 1.8], Speed=[3, 9], Size=[0.08, 0.22],
                    StartColor=[1.0, 0.75, 0.3], StartColor2=[1.0, 0.4, 0.08], EndColor=[0.8, 0.1, 0.02], Intensity=6.0, Gravity=1.0, Drag=0.2, NoiseStrength=0.5,
                    Blend='Additive', EmissionRate=40, MaxParticles=90, Alignment='Stretched', StretchFactor=0.05, FadeIn=0.02)
    s.light('Throne light', h, (0, top_y + 9, zt + 3), 'Spot', (1.0, 0.45, 0.25), 600.0, 30, rot=look_rotation((0, top_y + 9, zt + 3), (0, top_y + 2.0, zt - 5.0)), inner=14, outer=30)
    s.light('Throne rim', h, (0, top_y + 6, zt - 8.5), 'Point', (1.0, 0.5, 0.15), 250.0, 14)
    # Banners off the dais's lintels and down the massif, chains and cages from the roof.
    banner_mat = A.mat(V, 'Banner', (1, 1, 1), glow=(1, 1, 1), power=0.35, both=True)
    sway = P.clip(V, 'BannerSway', 150, [P.track('Rotation', [(0, (0, 0, 0)), (40, (3, 0, 1.5)), (110, (-3, 0, -1.5)), (150, (0, 0, 0))], 'SmoothStep')])
    for i, x in enumerate((-7.85, 7.85)):
        A.model(s, P.looping(s, h, 'Banner', sway, (x, top_y + 8.0, zt - 0.35), speed=0.8 + 0.3 * i), 'Banner', A.banner(V), (0, 0, 0), (0, 0, 0), 1.25, banner_mat)
    for i, x in enumerate((-17, 17)):
        A.model(s, P.looping(s, h, 'Great banner', sway, (x, 27, zt - 11.5), speed=0.5 + 0.2 * i), 'Banner', A.banner(V), (0, 0, 0), (0, -x * 0.8, 0), 3.2, banner_mat)
    swing = P.clip(V, 'CageSwing', 180, [P.track('Rotation', [(0, (0, 0, 0)), (45, (2.5, 0, 4)), (135, (-2.5, 0, -4)), (180, (0, 0, 0))], 'SmoothStep')])
    for i, (x, z, y) in enumerate(((-15, -3, 34), (15, -1, 33), (-22, 12, 31), (22, 10, 32), (-9, -17, 36), (10, -18, 36), (0, 20, 32))):
        A.model(s, P.looping(s, h, 'Cage', swing, (x, y, z), speed=0.6 + 0.12 * i), 'Chain and cage', A.chain_cage(V, 16.0 if i % 2 else 12.0), (0, 0, 0), (0, i * 50, 0), 1.3, shadows=False)
    # Stalactites off the roof, spires out of the lake, the arena's ragged rim.
    stal_a, stal_b, stal_c = A.spikes(V, 'SpikesA', 9, 3.2, (3.0, 9.0), 1), A.spikes(V, 'SpikesB', 6, 2.2, (2.5, 7.0), 2), A.spikes(V, 'SpikesC', 4, 1.2, (1.0, 3.2), 3)
    rng = random.Random(23)
    for i in range(26):
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(6, 46)
        x, z = math.cos(a) * r, -6 + math.sin(a) * r
        roof = -6 + 50 * math.sqrt(max(0.0, 1 - min(1.0, (r / 60.0) ** (1 / 0.75)) ** 2))
        A.model(s, h, 'Stalactites', (stal_a, stal_b)[i % 2], (x, roof + 2, z), (180, rng.uniform(0, 360), 0), rng.uniform(1.6, 3.2), rock_glow, shadows=False)
    for i in range(22):
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(24, 50)
        x, z = math.cos(a) * r, -6 + math.sin(a) * r
        if abs(x) < 13 and -44 < z < -4 or math.hypot(x - C[0], z - C[2]) < 32 and z > -6 and abs(x) > 12:
            continue
        A.model(s, h, 'Spires', (stal_a, stal_b)[i % 2], (x, -2.5, z), (0, rng.uniform(0, 360), 0), rng.uniform(1.5, 4.2), rock_glow, shadows=False)
    for i in range(16):
        a = 2 * math.pi * i / 16 + rng.uniform(-0.1, 0.1)
        x, z = C[0] + math.cos(a) * 15.6, C[2] + math.sin(a) * 15.6
        if abs(x) < 6 and z < C[2]:
            continue
        A.model(s, h, 'Rim spikes', stal_c, (x, -0.9, z), (0, rng.uniform(0, 360), 0), rng.uniform(0.9, 1.6), rock_glow)
    # Gargoyles and braziers.
    garg = A.gargoyle(V)
    for side in (-1, 1):
        for i in (0, 4, 8):
            A.model(s, h, 'Gargoyle', garg, (side * 4.45, (i + 1) * rise + 1.6, z0 - i * run - run / 2), (0, -side * 35, 0), 1.0)
        A.model(s, h, 'Great gargoyle', garg, (side * 9.6, top_y, zt - 3.2), (0, -side * 28, 0), 2.6)
    braz = A.brazier(V)
    brazier_at = [(-5.6, 0, z0 + 0.6), (5.6, 0, z0 + 0.6), (-3.6, top_y, zt - 1.0), (3.6, top_y, zt - 1.0), (-8.0, top_y, zt - 5.6), (8.0, top_y, zt - 5.6)]
    for a in (-150, -115, -65, -30):
        brazier_at.append((C[0] + 13.8 * math.cos(math.radians(a)), 0, C[2] - 13.8 * math.sin(math.radians(a))))
    for i, at in enumerate(brazier_at):
        A.model(s, h, 'Brazier', braz, at, (0, i * 40, 0), 1.25)
        top = (at[0], at[1] + 1.6, at[2])
        body = P.looping(s, h, 'Brazier flame', P.clip(V, 'Flicker0', 14, [P.track('Scale', [(0, (1, 1, 1)), (4, (1.15, 1.4, 0.9)), (9, (0.85, 0.75, 1.15)), (14, (1, 1, 1))], 'SmoothStep')]), top, speed=0.9 + 0.1 * (i % 4))
        A.model(s, body, 'Flame', A.flame(V), (0, 0, 0), (0, i * 77, 0), (0.9, 1.5, 0.9), A.mat(V, 'Palette', (0, 0, 0), glow=(1.0, 0.5, 0.12), power=6.0, additive=True, both=True), shadows=False)
        A.particles(s, h, 'Brazier sparks', top, Shape='Cone', ConeAngle=22, ShapeRadius=0.25, Lifetime=[1.0, 2.4], Speed=[1.0, 3.0], Size=[0.025, 0.06],
                    StartColor=[1.0, 0.8, 0.35], StartColor2=[1.0, 0.5, 0.1], EndColor=[0.8, 0.15, 0.02], Intensity=5.0, Gravity=-0.1, Drag=0.3, NoiseStrength=1.2,
                    Blend='Additive', EmissionRate=9, MaxParticles=30, Alignment='Stretched', StretchFactor=0.08, FadeIn=0.02)
        s.light('Brazier light', h, (top[0], top[1] + 0.8, top[2]), 'Point', (1.0, 0.45, 0.15), 240.0, 13)
    # Fire out of the lake, and the jets that go up on the big moments.
    for i, (x, z, size) in enumerate(((-30, -22, 3.0), (31, -18, 2.6), (-36, 14, 2.4), (37, 20, 3.2), (-12, -44, 3.4), (13, -45, 3.0))):
        fire(s, h, V, (x, -1.6, z), size, 700.0, smoke=False, name=f'Lake fire {i}')
    for i, (x, z) in enumerate(((-11.5, -5.5), (11.5, -5.5), (-13.5, 9.5), (13.5, 9.5))):
        jet = A.particles(s, h, f'Fire jet {i}', (x, 0.2, z), Shape='Cone', ConeAngle=6, ShapeRadius=0.25, Lifetime=[0.5, 0.9], Speed=[16, 24], Size=[0.7, 1.3], EndSize=0.4,
                          StartColor=[1.0, 0.8, 0.3], StartColor2=[1.0, 0.45, 0.08], EndColor=[0.8, 0.1, 0.01], Intensity=7.0, Gravity=0.3, Drag=0.6, NoiseStrength=0.6,
                          Blend='Additive', EmissionRate=0, BurstCount=0, MaxParticles=400, Texture=A.tex(V, 'Puff'), FadeIn=0.05)
        jet.add({'Type': 'VenueAccent', 'Beats': 4, 'Particles': 320})
    A.particles(s, h, 'Embers on the air', (0, 4, 0), Shape='Box', BoxSize=[70, 6, 70], Lifetime=[5.0, 10.0], Speed=[0.4, 1.6], Size=[0.03, 0.08],
                StartColor=[1.0, 0.7, 0.3], StartColor2=[1.0, 0.35, 0.08], EndColor=[0.9, 0.12, 0.02], Intensity=5.0, Gravity=-0.03, Drag=0.1, NoiseStrength=1.0,
                NoiseFrequency=0.3, Blend='Additive', EmissionRate=45, MaxParticles=420, FadeIn=0.1)
    A.particles(s, h, 'Heat haze off the lake', (0, -1, -6), Shape='Box', BoxSize=[100, 1, 100], Lifetime=[6.0, 10.0], Speed=[0.6, 1.5], Size=[5.0, 9.0], EndSize=1.8,
                StartColor=[0.5, 0.1, 0.03], StartColor2=[0.3, 0.05, 0.02], EndColor=[0.1, 0.02, 0.01], StartAlpha=0.12, EndAlpha=0.0, Gravity=-0.02, Drag=0.1,
                NoiseStrength=0.4, NoiseFrequency=0.2, Blend='Alpha', EmissionRate=7, MaxParticles=80, Texture=A.tex(V, 'Puff'), FadeIn=0.3)
    # Bats.
    spin = P.clip(V, 'BatsCircle', 600, [P.track('Rotation', [(0, (0, 0, 0)), (200, (0, 120, 0)), (400, (0, 240, 0)), (600, (0, 359.9, 0))])])
    flap = P.clip(V, 'BatsFlap', 8, [P.track('Scale', [(0, (1, 1, 1)), (4, (1, -0.6, 1)), (8, (1, 1, 1))], 'SmoothStep')])
    for i, (y, r, sp, tilt) in enumerate(((17, 15, 1.0, 6), (23, 24, -0.7, -9), (13, 9, 1.5, 12), (29, 32, 0.5, 4))):
        ring = P.looping(s, s.entity('Bats', h, (0, y, -2), (tilt, 0, tilt * 0.5)), 'Circling', spin, speed=sp)
        A.model(s, P.looping(s, ring, 'Flapping', flap, speed=1.0 + 0.2 * i), 'Bats', A.bats(V, 16, 3 + i), (0, 0, 0), (0, 0, 0), (r, r * 0.7, r), shadows=False)
    # The rig: beams off the terraces, blinders on the dais, strobes in the roof.
    for i, (x, c) in enumerate(((-3.5, (1.0, 0.25, 0.05)), (3.5, (1.0, 0.1, 0.05)), (-1.2, (1.0, 0.45, 0.1)), (1.2, (0.9, 0.15, 0.1)))):
        s.light(f'Wash {i}', h, (x, 7, -1), 'Spot', c, 1600.0, 18, rot=look_rotation((x, 7, -1), (x * 0.4, 1, 3.5)), inner=22, outer=42, show='Wash', group=i)
    for i, (x, z) in enumerate(((-24, 10), (24, 10), (-21, -4), (21, -4))):
        at = (x, 9, z)
        s.light(f'Beam {i}', h, at, 'Spot', (1.0, 0.2, 0.05) if i % 2 else (1.0, 0.5, 0.1), 4000.0, 50, rot=look_rotation(at, (0, 2, 3.5)), inner=3, outer=7, show='Beam', group=i)
    for i, x in enumerate((-6.2, 6.2)):
        s.light(f'Blinder {i}', h, (x, top_y + 7.6, zt - 0.3), 'Spot', (1.0, 0.6, 0.3), 2500.0, 60, rot=look_rotation((x, top_y + 7.6, zt - 0.3), (x * 0.3, 1, 3)), inner=12, outer=24, show='Blinder', group=i)
        s.light(f'Strobe {i}', h, (x * 1.6, 14, 6), 'Point', (1.0, 0.85, 0.7), 2500.0, 32, show='Strobe', group=i)
    for side in (-1, 1):
        s.light('Floor fill', h, (side * 7, 6, 2), 'Point', (1.0, 0.35, 0.15), 200.0, 18)
        s.light('Lake glow', h, (side * 24, 1.5, -22), 'Point', (1.0, 0.3, 0.05), 800.0, 40)
        s.light('Lake glow', h, (side * 30, 1.5, 22), 'Point', (1.0, 0.3, 0.05), 800.0, 40)
    s.light('Lake glow, behind', h, (0, 1.5, 24), 'Point', (1.0, 0.3, 0.05), 800.0, 40)
    s.light('Stair glow', h, (0, 5, z0 - 6), 'Point', (1.0, 0.3, 0.08), 600.0, 16)

    # Satan: on the throne, beckoning, drumming on the arms, on his feet, on the phone.
    seat = (throne_at[0], top_y + 0.63, throne_at[2] - 0.05)
    stand = (0.0, top_y, zt - 1.3)
    satan = {}
    for label, pose in (('Satan_throne', P.THRONE), ('Satan_beckon', P.BECKON), ('Satan_air_drums', P.AIR_DRUMS),
                        ('Satan_standing', P.STANDING_PROUD), ('Satan_phone', P.ON_THE_PHONE)):
        satan[label] = P.figure(V, label, 'Rigged', '04_A', pose, 'Satan')
    big_horns, wing_m = A.horns(V, True), A.devil_wing(V)
    for label, after, before, at in (('Satan_throne', None, 'encore_called', seat), ('Satan_beckon', 'encore_called', 'satan_air_drums', seat),
                                     ('Satan_air_drums', 'satan_air_drums', 'satan_stands', seat), ('Satan_standing', 'satan_stands', 'phone_call', stand),
                                     ('Satan_phone', 'phone_call', None, stand)):
        g = P.between(s, h, label, after, before, 0.08, at)
        P.place(s, g, 'Satan', satan[label], at, 0, 1.6)
        standing = at is stand
        head = at[1] + (2.78 if standing else 2.1)
        A.model(s, g, 'Horns', big_horns, (at[0], head, at[2] - 0.02), (-8, 0, 0), 1.0)
        back = (at[0], at[1] + (2.2 if standing else 1.6), at[2] - 0.3)
        spread = 4.6 if standing else 3.4
        A.model(s, g, 'Wing R', wing_m, add3(back, (0.25, 0, 0)), (0, 12, 18 if standing else 6), spread, shadows=False)
        A.model(s, g, 'Wing L', wing_m, add3(back, (-0.25, 0, 0)), (0, 168, -18 if standing else -6), spread, shadows=False)
        if label == 'Satan_phone':
            s.box('Receiver', g, (at[0] - 0.5, at[1] + 2.75, at[2]), (0.08, 0.32, 0.1), (0.6, 0.02, 0.02))
    s.box('Phone table', h, (2.4, top_y + 0.45, zt - 1.9), (0.6, 0.9, 0.6), STONE_DARK)
    s.box('Phone', h, (2.4, top_y + 0.98, zt - 1.9), (0.36, 0.14, 0.26), (0.7, 0.02, 0.02), emissive=(0.8, 0.02, 0.02), emissive_intensity=0.6)

    # Demons: on the plinths, on the floor round three sides, and up the terraces.
    demon_poses = {'cheer': P.CHEER, 'fists': P.FISTS, 'stand': P.STANDING}
    bodies = (('Daughter_01', '01_C'), ('Mother_01', '03_C'), ('SchoolGirl_01', '04_A'), ('Son_01', '03_B'), ('Mother_02', '02_B'), ('SchoolBoy_01', '02_A'))
    models = {}
    for b, v in bodies:
        for k, pose in demon_poses.items():
            models[(b, k)] = P.figure(V, f'Demon_{b}_{k}', b, v, pose, 'a demon')
    throne = (0.0, top_y + 2.0, zt - 5.0)
    horn_m = A.horns(V)
    bounce = [P.clip(V, f'DemonBounce{i}', 16 + 4 * i, [P.track('Position', [(0, (0, 0, 0)), (5 + i, (0, 0.16 + 0.05 * i, 0)), (16 + 4 * i, (0, 0, 0))], 'SmoothStep')]) for i in range(3)]

    def demon(parent, at, yaw, b, k, turns=True, scale=1.0):
        # Facing the band; on the encore (encore_called) each turns to the throne.
        g = s.entity('Demon', parent, at, (0, yaw, 0), (scale, scale, scale))
        if turns:
            g = P.play(s, g, 'Turn', 'encore_called', P.turn_clip(V, P.wrap(P.yaw_to(at, throne) - yaw), 1.2 + 0.4 * ((int(at[0] * 7) % 5) / 4.0)))
        if k != 'stand':
            g = P.looping(s, g, 'Bounce', bounce[int(abs(at[0] * 3 + at[2] * 5)) % 3], speed=0.9 + 0.05 * (int(abs(at[2] * 11)) % 6))
        g.add({'Type': 'Model', 'ModelPath': models[(b, k)]})
        A.model(s, g, 'Horns', horn_m, (0, 1.7, 0.02), (-6, 0, 0), 1.0, shadows=False)
        return g
    rng = random.Random(23)
    for side in (-1, 1):
        for i in (2, 6, 10):
            b, _ = bodies[(i + side) % len(bodies)]
            demon(h, (side * 4.45, (i + 1) * rise + 1.6, z0 - i * run - run / 2), 90 * side + 180 + rng.uniform(-30, 30), b, 'cheer' if i % 4 == 2 else 'stand')
    for i in range(60):
        side = i % 3
        if side == 0:
            at = (rng.uniform(-12, -5.0), 0, rng.uniform(-4, 8))
        elif side == 1:
            at = (rng.uniform(5.0, 12), 0, rng.uniform(-4, 8))
        else:
            # An aisle up the middle, from the band to the foot of the stairs.
            at = (rng.choice((-1, 1)) * rng.uniform(2.2, 5.5), 0, rng.uniform(-6.0, -2.2))
        yaw = math.degrees(math.atan2(-at[0], DRUMMER[1] - 1.5 - at[2])) + rng.uniform(-20, 20)
        b, _ = bodies[i % len(bodies)]
        demon(h, at, yaw, b, ('cheer', 'fists', 'stand')[rng.randrange(3)])
    for side in (-1, 1):
        for k, (r0, y) in enumerate(tiers):
            n = 12 + 3 * k
            for i in range(n):
                deg = A.TERRACE_ARC[0] + 6 + (A.TERRACE_ARC[1] - A.TERRACE_ARC[0] - 12) * (i + rng.uniform(0.1, 0.9)) / n
                at = A.terrace_point(C, side, r0 + rng.uniform(0.7, 3.2), deg, y)
                yaw = math.degrees(math.atan2(C[0] - at[0], C[2] + 1.5 - at[2])) + rng.uniform(-15, 15)
                b, _ = bodies[(i + k) % len(bodies)]
                demon(h, at, yaw, b, ('cheer', 'fists', 'cheer', 'stand')[rng.randrange(4)], turns=False, scale=1.0 + 0.12 * k)
            # Torches along each tier.
            for deg in (-60, -20, 20):
                at = A.terrace_point(C, side, r0 + 4.0, deg, y)
                s.box('Torch pole', h, (at[0], y + 1.3, at[2]), (0.1, 2.6, 0.1), (0.1, 0.08, 0.06), shape='Cylinder', shadows=False)
                A.model(s, h, 'Torch flame', A.flame(V), (at[0], y + 2.6, at[2]), (0, deg, 0), (0.6, 1.1, 0.6), A.mat(V, 'Palette', (0, 0, 0), glow=(1.0, 0.5, 0.12), power=6.0, additive=True, both=True), shadows=False)
                s.light('Torch light', h, (at[0], y + 3.2, at[2]), 'Point', (1.0, 0.45, 0.15), 170.0, 12)
    # The demon on the steps who catches a fill.
    step3 = (1.4, 3 * rise, z0 - 2.5 * run)
    catch = P.figure(V, 'Demon_catch', 'Daughter_01', '01_C', P.CROUCH_CATCH, 'the demon catching a fill')
    look = P.figure(V, 'Demon_looks_back', 'Daughter_01', '01_C', P.TURN_BACK, 'the demon looking back at the throne')
    demon_g = P.between(s, h, 'Step demon', None, 'demon_catch', 0.2, step3)
    demon(demon_g, step3, 180, 'Daughter_01', 'stand', turns=False)
    caught = P.between(s, h, 'Step demon caught', 'demon_catch', None, 0.2, step3)
    P.place(s, caught, 'Demon catching', catch, step3, 180)
    s.light('Step demon light', h, (step3[0] + 1.2, step3[1] + 1.8, step3[2] + 1.6), 'Point', (1.0, 0.6, 0.3), 90.0, 6)
    A.model(s, caught, 'Horns', horn_m, (step3[0], step3[1] + 1.05, step3[2] - 0.75), (60, 180, 0), 1.0, shadows=False)
    P.place(s, P.between(s, h, 'Step demon looks', 'satan_nods', None, 0.2, (step3[0] + 0.8, step3[1], step3[2])), 'Demon looking back', look, (step3[0] + 0.8, step3[1], step3[2]), 0)
    # The smoke that lifts them out: white, up from the floor round the band.
    smoke = P.between(s, root, 'Smoke', 'smoke_rises', None, 1.5)
    A.particles(s, smoke, 'Smoke rising', (0, 0.2, 3.2), Shape='Box', BoxSize=[12, 0.4, 10], Lifetime=[4.0, 7.0], Speed=[2.5, 5.0], Size=[1.6, 3.2], EndSize=2.6,
                StartColor=[0.9, 0.9, 0.95], StartColor2=[0.75, 0.75, 0.8], EndColor=[1.0, 1.0, 1.0], StartAlpha=0.55, EndAlpha=0.0, Gravity=-0.12, Drag=0.2,
                NoiseStrength=0.6, NoiseFrequency=0.3, Blend='Alpha', EmissionRate=38, MaxParticles=260, Texture=A.tex(V, 'Puff'), FadeIn=0.15, AngularVelocity=[-15, 15])
    A.glow_card(s, smoke, V, 'The way up, its mouth', (0, 58, 3.5), 14.0, (1.0, 0.98, 0.92), 5.0, (-90, 0, 0))
    s.light('Smoke glow', smoke, (0, 14, 3), 'Spot', (1, 0.98, 0.94), 26000.0, 40, rot=(90, 0, 0), inner=14, outer=26)

    # A few more places to shoot the show from.
    s.camera_spot('Camera behind the band', marks, (4.6, 2.4, 9.5), (0, top_y - 1, zt - 3), 'Custom', 42, 'behind')
    s.camera_spot('Camera lake', marks, (-17, 1.2, -9), (0, 2.4, 4.5), 'Custom', 40, 'lake')
    s.camera_spot('Camera terrace', marks, (21, 9.5, 14), (0, 1.2, 2.5), 'Custom', 46, 'terrace')
    s.camera_spot('Camera stair head', marks, (1.5, top_y + 2.2, zt + 1.5), (0, 1.0, 3.5), 'Custom', 38, 'stairhead')

    # Story shots.
    shot(s, marks, 'ghost_hand', beside_hand(hand, 180, 0.95, 0.6, 0.12), (hand[0], 0.05, hand[2]), 28, 9, focus=True,
         via=[(beside_hand(hand, 180, 1.1, 0.8, 0.3), (hand[0], 0.35, hand[2]), 32)],
         end=(beside_hand(hand, 180, 2.0, 1.8, 1.0), (hand[0] + 0.3, 1.1, hand[2] + 0.2), 42))
    shot(s, marks, 'crash_survey', (-11.5, 1.25, -15.5), (-6.5, 1.3, -8.5), 38, 8, hand=True,
         via=[((-9.5, 1.5, -11.0), (4.0, 1.2, 2.0), 42)], end=((-4.5, 2.3, -9.5), (10.5, 2.0, 5.5), 46))
    shot(s, marks, 'the_slit', (0.9, 1.1, 1.6), (0, 30, 3.4), 64, 8, hand=True, end=((0.5, 1.4, 2.4), (0, 148, 3), 26))
    shot(s, marks, 'hell_wide', (27, 21, 27), (0, 5, -10), 58, 12, via=[((35, 19, 6), (0, 6, -14), 60)], end=((24, 13, -15), (-2, 8, -24), 62))
    shot(s, marks, 'cavern_orbit', (7.0, 1.3, 10.8), (0, 4.5, -12), 40, 10, via=[((0.5, 1.0, 12.5), (0, 5.0, -14), 42)], end=((-7.0, 1.8, 10.8), (0, 5.5, -16), 44))
    shot(s, marks, 'ghosts_stand', (-6.5, 0.5, -3.5), (0.5, 1.2, 3.4), 40, 11,
         via=[((-2.0, 1.4, -8.5), (0.8, 1.3, 3.4), 44), ((5.0, 3.2, -11.5), (1.5, 1.2, 3.4), 48)],
         end=((-1.0, 7.5, -17.0), (2.5, 1.0, 3.0), 52))
    shot(s, marks, 'cop_runs', (-8.6, 1.0, -1.5), (car_door[0], 1.1, car_door[2]), 40, 3.2, hand=True, end=((-4.4, 1.3, 3.0), (kneel_at[0], 0.8, kneel_at[2]), 44))
    shot(s, marks, 'cop_kneels', (-3.2, 0.55, DRUMMER[1] - 0.6), (0.2, 1.3, DRUMMER[1] + 0.9), 38, 7, hand=True, focus=True,
         end=((-3.0, 0.8, kneel_at[2] - 1.6), (kneel_at[0] + 0.3, 0.7, kneel_at[2]), 30))
    shot(s, marks, 'fell', (1.5, 0.6, -1.0), (0, 1.4, 4.0), 60, 8, hand=True, via=[((1.3, 0.8, -1.2), (0, 30, 4.5), 74)], end=((1.0, 1.0, -1.4), (0, 140, 3.2), 50))
    shot(s, marks, 'tumbling', (-3.6, 2.0, 0.6), (-2.0, 1.6, 2.6), 42, 7, hand=True, focus=True, via=[((-5.5, 3.5, -4.0), (0, 1.5, 3.5), 52)],
         end=((0.0, 9.0, -8.0), (0, 0.5, 3.6), 62))
    shot(s, marks, 'landed', (1.1, 0.3, 2.2), (0.0, 0.42, 4.2), 44, 4, focus=True, end=((1.6, 0.45, 1.2), (0.0, 0.6, 4.2), 50))
    shot(s, marks, 'stairs_reveal', (0.6, 0.5, -2.6), (0, 1.6, z0 - 3), 46, 13,
         via=[((1.2, 3.2, z0 - 3.0), (-1.0, 5.2, z0 - 8.0), 48), ((-1.2, top_y - 1.0, zt + 6.5), (0, top_y + 3.0, zt - 5.0), 44),
              ((0.4, top_y + 2.2, zt + 2.2), (0, top_y + 3.2, zt - 5.2), 34)],
         end=((0, top_y + 4.5, zt + 9.0), (0, top_y + 11.0, zt - 11.0), 62))
    face = (0, seat[1] + 1.95, seat[2] + 0.2)
    shot(s, marks, 'encore_called', (1.4, face[1] - 0.5, face[2] + 4.2), face, 34, 6, focus=True, end=((0.9, face[1] - 0.3, face[2] + 3.0), face, 30))
    shot(s, marks, 'throne_view', (1.3, top_y + 4.3, zt - 5.6), (0, 0.8, 3.2), 44, 8, via=[((2.6, top_y + 5.0, zt - 2.0), (0, 0.8, 3.2), 50)],
         end=((0.6, top_y + 2.4, zt + 2.6), (0, 1.0, 3.6), 30))
    shot(s, marks, 'demon_catch', (step3[0] + 1.9, step3[1] + 0.5, step3[2] + 2.2), (step3[0], step3[1] + 0.7, step3[2]), 36, 4.5, hand=True, focus=True,
         end=((step3[0] + 1.3, step3[1] + 0.9, step3[2] + 2.6), (step3[0] + 0.3, step3[1] + 1.2, step3[2] - 0.4), 32))
    shot(s, marks, 'satan_nods', (0, face[1] + 0.05, face[2] + 4.0), face, 28, 6, focus=True, end=((0, face[1], face[2] + 3.2), face, 22))
    shot(s, marks, 'satan_air_drums', (2.9, face[1] - 0.9, face[2] + 2.4), (0, face[1] - 0.9, face[2] + 0.2), 40, 6, hand=True, end=((2.0, face[1] - 0.5, face[2] + 3.0), (0, face[1] - 0.8, face[2]), 36))
    shot(s, marks, 'satan_stands', (0.8, top_y + 0.5, zt + 3.4), (0, top_y + 2.6, zt - 1.3), 40, 6, end=((2.4, top_y + 0.3, zt + 6.5), (0, top_y + 4.5, zt - 3.0), 54))
    shot(s, marks, 'phone_call', (-1.6, top_y + 2.4, zt + 1.0), (0, top_y + 2.8, zt - 1.3), 34, 6, focus=True, end=((-1.0, top_y + 2.0, zt + 0.6), (0, top_y + 4.2, zt - 1.3), 40))
    shot(s, marks, 'smoke_rises', (1.3, 0.25, 3.4), (0.1, 0.5, 4.6), 40, 20, hand=True, via=[((1.6, 0.6, 2.2), (0, 4, 4.4), 58)], end=((1.2, 0.5, 1.8), (0, 60, 3.6), 70))
    write(s, V, 'Hell', ambience=None)


# ---- heaven -------------------------------------------------------------------------------------
def angel(s, parent, venue, centre, scale, eyes_flag=None, name='Angel', turn_flag=None, look_at=None):
    """Wheels within wheels turning about a great eye, eyes all round their rims, and three pairs of
    wings behind; it faces +z (the band). eyes_flag: until then it is only gold rings, an arch
    standing in the cloud. turn_flag: it turns to look at look_at then."""
    g = s.group(name, parent, centre)
    if turn_flag and look_at:
        flat = math.hypot(look_at[0] - centre[0], look_at[2] - centre[2])
        g = P.play(s, g, 'Turn', turn_flag, P.turn_clip(venue, P.wrap(P.yaw_to(centre, look_at)), 2.5, math.degrees(math.atan2(centre[1] - look_at[1], flat))))
    r = 3.2 * scale
    gold = A.mat(venue, 'Palette', (1, 1, 1), glow=(1, 1, 1), power=1.3, metallic=0.6, rough=0.35)
    spin_a = P.clip(venue, 'RingSpinA', 900, [P.track('Rotation', [(0, (0, 0, 0)), (300, (0, 0, 120)), (600, (0, 0, 240)), (900, (0, 0, 359.9))])])
    spin_b = P.clip(venue, 'RingSpinB', 1200, [P.track('Rotation', [(0, (0, 0, 0)), (400, (0, 120, 0)), (800, (0, 240, 0)), (1200, (0, 359.9, 0))])])
    spin_c = P.clip(venue, 'RingSpinC', 1000, [P.track('Rotation', [(0, (0, 0, 0)), (333, (120, 0, 0)), (666, (240, 0, 0)), (1000, (359.9, 0, 0))])])
    awake = P.between(s, g, 'Awake', eyes_flag, None, 2.5) if eyes_flag else g
    if eyes_flag:
        asleep = P.between(s, g, 'Asleep', None, eyes_flag, 2.5)
        plain = A.torus(venue, 'PlainRing', 1.0, 0.11)
        A.model(s, asleep, 'Ring', plain, (0, 0, 0), (0, 0, 0), r, gold, shadows=False)
        A.model(s, asleep, 'Ring', plain, (0, 0, 0), (0, 0, 14), r * 0.86, gold, shadows=False)
    A.model(s, P.looping(s, awake, 'Wheel A', spin_a), 'Wheel', A.angel_ring(venue, 'AngelRingA', 1.0, 0.11, 14, 'z'), (0, 0, 0), (0, 0, 0), r, gold, shadows=False)
    A.model(s, P.looping(s, awake, 'Wheel B', spin_b, speed=0.8), 'Wheel', A.angel_ring(venue, 'AngelRingB', 1.0, 0.1, 12, 'out'), (0, 0, 0), (0, 0, 0), r * 0.86, gold, shadows=False)
    A.model(s, P.looping(s, awake, 'Wheel C', spin_c, speed=0.7), 'Wheel', A.angel_ring(venue, 'AngelRingB', 1.0, 0.1, 12, 'out'), (0, 0, 0), (0, 90, 0), r * 0.72, gold, shadows=False)
    A.model(s, awake, 'Heart eye', A.angel_eye(venue), (0, 0, 0), (0, 0, 0), 0.95 * scale, A.mat(venue, 'Palette', (1, 1, 1), glow=(1, 1, 1), power=1.6), shadows=False)
    feather = A.mat(venue, 'Palette', (1, 1, 1), glow=(1, 1, 1), power=0.85, both=True)
    for i, (ang, length, rest) in enumerate(((34, 1.7, 0), (2, 2.0, 6), (-30, 1.5, 12))):
        beat = P.clip(venue, f'WingBeat{i}', 110 + 20 * i, [P.track('Rotation', [(0, (0, 0, 0)), (55 + 10 * i, (0, 0, 9 - 2 * i)), (110 + 20 * i, (0, 0, 0))], 'SmoothStep')])
        for side in (-1, 1):
            root = (side * r * 0.75, r * 0.3 * math.sin(math.radians(ang)), -0.5 * scale)
            flap = P.looping(s, s.entity('Wing', g, root, (0, 0 if side > 0 else 180, side * ang)), 'Beat', beat, speed=0.8 + 0.1 * (int(abs(centre[0])) % 3))
            A.model(s, flap, 'Wing', A.wing(venue), (0, 0, 0), (0, 0, 0), length * r, feather, shadows=False)
    return g


def heaven():
    V = 'StoryHeaven'
    s = Scene(seed=6603)
    s.venue = V
    root = s.group('Highway to the Afterlife: heaven')
    marks = s.group('Markers', root)
    s.info(marks, 'Heaven', 'Drumsmith', outdoor=False, half_width=60, desk_z=-20,
           ambient=(0.55, 0.66, 0.9), fog_color=(0.42, 0.5, 0.68), haze=0.035)
    band(s, marks, 0.0)
    s.camera_spot('Camera Wide', marks, (0, 4.2, -5.2), (0, 1.9, 4), 'Wide', 60)
    s.camera_spot('Camera Crane', marks, (-9, 7, 13), (0, 2, 2), 'Crane', 55)
    s.camera_spot('Camera Desk', marks, (2.4, 2.3, -4.6), (0, 2, 4), 'Desk', 34)
    s.light('Sun', marks, (0, 80, -40), 'Directional', (1.0, 0.93, 0.8), 2.8, 400, rot=(42, 150, 0), shadows=True, show='Static')
    for i, x in enumerate((-3.5, 3.5, -1.2, 1.2)):
        s.light(f'Wash {i}', marks, (x, 8, -2), 'Spot', (1.0, 0.92, 0.75), 1200.0, 18, rot=look_rotation((x, 8, -2), (x * 0.4, 1, 3.5)), inner=22, outer=42, show='Wash', group=i)
    rng = random.Random(31)
    cloud_mat = A.mat(V, 'Palette', (1, 1, 1), glow=(0.84, 0.89, 1.0), power=0.5, rough=1.0)
    cloud_gold = A.mat(V, 'Palette', (1, 0.95, 0.85), glow=(1.0, 0.84, 0.66), power=0.55, rough=1.0)
    clouds_m = [A.cloud(V, k) for k in range(1, 5)]

    # The sky everything stands in, the sun, and the sea of cloud far below.
    # The engine's fog swallows everything past about 150 m, so the sky is a dome inside that (its
    # light turned up to come through), and the far scenery stands just in front of it.
    A.model(s, root, 'Sky', A.sky_dome(V, 'SkyDome', 'Sky', 125.0), (0, 0, -10), (0, 0, 0), 1.0, A.mat(V, 'Sky', (0, 0, 0), glow=(1, 1, 1), power=1.3), shadows=False)
    A.model(s, root, 'Cloud sea', A.cloud_sea(V), (0, -52, 0), (0, 0, 0), (0.2, 0.3, 0.2), cloud_mat, shadows=False)
    for i in range(26):
        a = 2 * math.pi * i / 26 + rng.uniform(-0.1, 0.1)
        r = rng.uniform(78, 112)
        sc = rng.uniform(14, 30)
        A.model(s, root, 'Cloud tower', clouds_m[i % 4], (math.cos(a) * r, rng.uniform(-50, -12), -10 + math.sin(a) * r), (0, rng.uniform(0, 360), 0),
                (sc, sc * rng.uniform(0.8, 1.8), sc), cloud_gold if i % 3 == 0 else cloud_mat, shadows=False)
    for i in range(7):
        a = 2 * math.pi * i / 7 + 0.4
        r = rng.uniform(70, 100)
        sc = rng.uniform(3.5, 6.5)
        A.model(s, root, 'Far temple', A.island(V, 1 + i % 3), (math.cos(a) * r, rng.uniform(6, 40), -10 + math.sin(a) * r), (0, rng.uniform(0, 360), 0), sc,
                A.mat(V, 'Palette', (1, 1, 1), glow=(0.9, 0.9, 1.0), power=0.6), shadows=False)

    # The ascent: cloud streaming down past them in three depths, wisps across the lens.
    up = P.between(s, root, 'The ascent', None, 'touchdown', 1.2)
    for depth, (count, r0, r1, size0, size1, period, frames) in enumerate(((26, 5, 14, 2.0, 4.5, 90.0, 300), (26, 16, 40, 6.0, 12.0, 160.0, 800), (14, 46, 80, 14.0, 24.0, 240.0, 2400))):
        clip = P.clip(V, f'CloudsFalling{depth}', frames, [P.track('Position', [(0, (0, 0, 0)), (frames, (0, -period, 0))])])
        body = P.looping(s, up, f'Clouds {depth}', clip)
        layout = [(rng.uniform(0, 2 * math.pi), rng.uniform(r0, r1), rng.uniform(0, period), rng.uniform(size0, size1), rng.randrange(4)) for _ in range(count)]
        for copy in (-1, 0, 1):
            for a, r, y, size, kind in layout:
                A.model(s, body, 'Cloud', clouds_m[kind], (math.sin(a) * r, y + copy * period, math.cos(a) * r + 3), (0, math.degrees(a) * 3, 0),
                        (size, size * 0.8, size), cloud_gold if kind == 0 else cloud_mat, shadows=False)
    A.particles(s, up, 'Wisps', (0, 14, 3), Shape='Box', BoxSize=[26, 4, 26], Lifetime=[2.5, 4.0], Speed=[0.0, 0.5], Size=[1.5, 3.5], EndSize=1.8,
                StartColor=[1.0, 1.0, 1.0], StartColor2=[0.9, 0.93, 1.0], EndColor=[1.0, 1.0, 1.0], StartAlpha=0.26, EndAlpha=0.0, Gravity=0.75, Drag=0.0,
                NoiseStrength=0.4, NoiseFrequency=0.3, Blend='Alpha', EmissionRate=22, MaxParticles=120, Texture=A.tex(V, 'Puff'), FadeIn=0.25, AngularVelocity=[-10, 10])
    A.particles(s, up, 'Motes', (0, 2, 3), Shape='Box', BoxSize=[18, 12, 18], Lifetime=[3.0, 6.0], Speed=[0.1, 0.5], Size=[0.02, 0.05],
                StartColor=[1.0, 0.9, 0.6], StartColor2=[1.0, 1.0, 0.9], EndColor=[1.0, 0.85, 0.5], Intensity=3.0, Gravity=0.25, Drag=0.2, NoiseStrength=0.5,
                Blend='Additive', EmissionRate=30, MaxParticles=160, FadeIn=0.2)

    # The floor of cloud, the stairs, the gates and God's platform.
    floor = P.between(s, root, 'The floor', 'touchdown', None, 1.0)
    steps, rise, run, z0 = 14, 0.75, 1.4, -6.0
    top_y = steps * rise
    zt = z0 - steps * run
    plat = (0.0, top_y, zt - 9.0)

    def clear(x, z):
        pad = 1 - A.smooth(6.0, 9.5, math.hypot(x, z - 3.5))
        stairs = (1 - A.smooth(6.0, 9.0, abs(x))) * (1 - A.smooth(zt - 22.0, zt - 26.0, z)) * A.smooth(4.0, 0.0, z)
        return max(pad, stairs)
    A.model(s, floor, 'Cloud floor', A.cloud_floor(V, 85.0, clear), (0, 0, 0), (0, 0, 0), 1.0, cloud_mat, shadows=False)
    textured(s.box('Kit dais', floor, (0, -0.16, 3.5), (12.0, 0.3, 12.0), (1, 1, 1), rough=0.12, metallic=0.25, shape='Cylinder'), V, 'Marble', (3, 3))
    A.model(s, floor, 'Kit dais, its gold', A.torus(V, 'DaisRing', 1.0, 0.012, 'gold', 48, 6, 'y'), (0, -0.02, 3.5), (0, 0, 0), 6.0,
            A.mat(V, 'Palette', (1, 1, 1), glow=(1, 1, 1), power=1.2, metallic=0.8, rough=0.3), shadows=False)
    marble = A.mat(V, 'Palette', (1, 1, 1), glow=(1.0, 0.97, 0.92), power=0.28, rough=0.3, metallic=0.1)
    A.model(s, floor, 'Stairs and platform', A.heaven_stairs(V, steps, rise, run, z0), (0, 0, 0), (0, 0, 0), 1.0, marble)
    A.model(s, floor, 'The gates', A.gate(V), (0, top_y, zt - 0.6), (0, 0, 0), 1.0, A.mat(V, 'Palette', (1, 1, 1), glow=(1, 1, 1), power=0.6, metallic=0.7, rough=0.3))
    col = A.column(V)
    for side in (-1, 1):
        for k in range(6):
            z = z0 + 3.0 - k * 4.2
            A.model(s, floor, 'Column', col, (side * 8.6, -1.4, z), (0, 0, 0), 1.5, marble)
            A.model(s, floor, 'Column cloud', clouds_m[k % 4], (side * 8.6, -1.6, z), (0, k * 60, 0), (2.6, 1.6, 2.6), cloud_mat, shadows=False)
    for k in range(12):
        a = math.radians(200 + 140 * k / 11)
        if abs(math.cos(a)) < 0.2:
            continue        # the gap the way home shows through
        A.model(s, floor, 'Platform column', col, (plat[0] + 11.6 * math.cos(a), top_y, plat[2] + 11.6 * math.sin(a)), (0, 0, 0), 1.35, marble)
    A.model(s, floor, 'Entablature', A.torus(V, 'Entablature', 1.0, 0.035, 'gold', 48, 6, 'y'), (plat[0], top_y + 11.1, plat[2]), (0, 0, 0), 11.6,
            A.mat(V, 'Palette', (1, 1, 1), glow=(1, 1, 1), power=0.9, metallic=0.8, rough=0.3), shadows=False)
    for i in range(34):
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(13, 70)
        x, z = math.sin(a) * r, math.cos(a) * r - 4
        if abs(x) < 10 and zt - 24 < z < 2:
            continue
        size = rng.uniform(2.5, 7) * (1 + r / 50)
        A.model(s, floor, 'Cloud bank', clouds_m[i % 4], (x, -1.2 - rng.uniform(0, 1.2), z), (0, rng.uniform(0, 360), 0), (size, size * rng.uniform(0.45, 0.9), size),
                cloud_gold if i % 5 == 0 else cloud_mat, shadows=False)
    A.particles(s, floor, 'Mist on the floor', (0, 0.2, -4), Shape='Box', BoxSize=[60, 0.5, 70], Lifetime=[8.0, 14.0], Speed=[0.05, 0.4], Size=[2.5, 5.5], EndSize=1.5,
                StartColor=[1.0, 1.0, 1.0], StartColor2=[0.92, 0.95, 1.0], EndColor=[1.0, 1.0, 1.0], StartAlpha=0.2, EndAlpha=0.0, Gravity=0.0, Drag=0.1,
                NoiseStrength=0.3, NoiseFrequency=0.15, Blend='Alpha', EmissionRate=12, MaxParticles=170, Texture=A.tex(V, 'Puff'), FadeIn=0.3, AngularVelocity=[-5, 5])
    A.particles(s, floor, 'Motes', (0, 5, -6), Shape='Box', BoxSize=[50, 10, 60], Lifetime=[5.0, 9.0], Speed=[0.05, 0.3], Size=[0.025, 0.06],
                StartColor=[1.0, 0.9, 0.6], StartColor2=[1.0, 1.0, 0.9], EndColor=[1.0, 0.85, 0.5], Intensity=3.0, Gravity=-0.01, Drag=0.2, NoiseStrength=0.4,
                Blend='Additive', EmissionRate=40, MaxParticles=320, FadeIn=0.2)
    # God: on the platform until the final chorus, then down the stairs to the band's level.
    god_robe = P.figure(V, 'God', 'Rigged', '01_C', P.ROBED, 'God')
    god_at = (0.0, top_y + 0.9, zt - 13.0)
    walk = [(0, 0, 0), (0, -0.9, 4.5), (0, -0.9, 13.0)]
    for i in range(steps):
        walk.append((0, -0.9 - (i + 1) * rise + (0.12 if i % 2 else 0), 13.0 + (i + 1) * run))
    walk.append((0, -top_y - 0.9, -4.5 - god_at[2]))
    descend = P.path_clip(V, 'GodDescends', walk, 11.0)
    god = P.play(s, floor, 'God descends', 'god_descends', descend, god_at)
    P.place(s, god, 'God', god_robe, (0, 0, 0), 0, 2.0)
    s.box('Robe', god, (0, 0.9, 0), (1.3, 1.8, 1.0), (1, 1, 1), emissive=(0.9, 0.9, 0.85), emissive_intensity=0.5, shape='Cylinder', shadows=False)
    A.model(s, god, 'Halo', A.torus(V, 'Halo', 1.0, 0.07), (0, 4.1, -0.3), (0, 0, 0), 0.75, A.mat(V, 'Palette', (1, 1, 1), glow=(1, 1, 1), power=4.0), shadows=False)
    burst_spin = P.clip(V, 'SunburstSpin', 1800, [P.track('Rotation', [(0, (0, 0, 0)), (600, (0, 0, 120)), (1200, (0, 0, 240)), (1800, (0, 0, 359.9))])])
    A.model(s, P.looping(s, god, 'Glory', burst_spin, (0, 3.6, -0.9)), 'Sunburst', A.sunburst(V), (0, 0, 0), (0, 0, 0), 7.5,
            A.mat(V, 'Palette', (0, 0, 0), glow=(1.0, 0.86, 0.5), power=0.8, additive=True, both=True), shadows=False)
    A.glow_card(s, god, V, 'Radiance', (0, 3.2, -1.0), 7.0, (1.0, 0.92, 0.7), 0.6)
    s.light('God light', god, (0, 6, 3), 'Point', (1, 0.95, 0.8), 260.0, 18)
    # The arch: the central angel, there from the touchdown as plain gold rings, its eyes opening
    # with the choir and turning to the drummer as the song resolves.
    drummer_head = (DRUMMER[0], 1.3, DRUMMER[1])
    arch_at = (0, top_y + 17, zt - 30)
    angel(s, floor, V, arch_at, 3.2, 'choir', 'Arch angel', 'angels_turn', drummer_head)

    # The choir: angels in an arc round and above the platform, and rank on rank behind them out
    # of sight; two banks of wings in front part to show the crash site.
    choir = P.between(s, root, 'The choir', 'choir', None, 3.0, (0, top_y + 10, zt - 20))
    for i, (x, y, z, sc) in enumerate(((-30, 22, -52, 2.2), (30, 22, -52, 2.2), (-50, 30, -40, 1.9), (50, 30, -40, 1.9), (-19, 38, -62, 1.7), (19, 38, -62, 1.7), (0, 47, -68, 2.0))):
        angel(s, choir, V, (x, y, z), sc, None, f'Angel {i}', 'angels_turn', drummer_head)
    far_m = A.angel_far(V)
    far_mat = A.mat(V, 'Palette', (1, 1, 1), glow=(1, 1, 1), power=1.1, both=True)
    bob = [P.clip(V, f'AngelBob{i}', 180 + 40 * i, [P.track('Position', [(0, (0, 0, 0)), (90 + 20 * i, (0, 1.5, 0)), (180 + 40 * i, (0, 0, 0))], 'SmoothStep')]) for i in range(3)]
    ranks = [P.looping(s, choir, f'Rank {i}', bob[i]) for i in range(3)]
    for i in range(66):
        ring = i % 6
        a = math.radians(-78 + 156 * ((i // 6) + 0.5 * (ring % 2)) / 11)
        r = 62 + 8 * ring
        y = 20 + 9 * ring + rng.uniform(-3, 3)
        at = (math.sin(a) * r, y, zt - 4 - math.cos(a) * r * 0.72)
        sc = 3.0 + 0.5 * ring
        A.model(s, ranks[i % 3], 'Angel of the choir', far_m, at, look_rotation(at, drummer_head), sc, far_mat, shadows=False)
    # Two banks of wings close in front of the platform's back; on angels_part they fold aside.
    feather = A.mat(V, 'Palette', (1, 1, 1), glow=(1, 1, 1), power=0.85, both=True)
    for side in (-1, 1):
        fold = P.clip(V, f'WingsPart{"L" if side < 0 else "R"}', 90, [P.track('Position', [(0, (0, 0, 0)), (90, (side * 10.0, 0.5, 1.5))], 'SmoothStep'),
                                                                   P.track('Rotation', [(0, (0, 0, 0)), (90, (0, side * 34, -side * 14))], 'SmoothStep')])
        bank = P.play(s, choir, 'Wings ' + ('left' if side < 0 else 'right'), 'angels_part', fold, (side * 0.4, top_y + 2.5, zt - 21))
        for i in range(4):
            A.model(s, bank, 'Wing', A.wing(V), (0, i * 2.6, -0.2 * i), (0, 0 if side > 0 else 180, side * (24 - 9 * i)), 11.0 - i * 0.8, feather, shadows=False)
    opened = P.between(s, choir, 'The way home', 'angels_part', None, 1.5)
    window = (0, top_y + 7, zt - 23)
    # Through the opening: the night on the shoulder, the fire and the red and blue lights.
    s.box('The way home', opened, window, (11, 9, 0.2), (0.01, 0.015, 0.04), emissive=(0.02, 0.035, 0.12), emissive_intensity=1.0, shadows=False, shape='Sphere')
    A.model(s, opened, 'The way home, its rim', A.torus(V, 'PlainRing', 1.0, 0.11), (window[0], window[1], window[2] + 0.3), (0, 0, 0), (5.7, 4.7, 4.0),
            A.mat(V, 'Palette', (1, 1, 1), glow=(1, 1, 1), power=2.0), shadows=False)
    s.box('The road', opened, (window[0], window[1] - 2.6, window[2] + 0.2), (7.5, 0.9, 0.05), (0.05, 0.05, 0.06), shadows=False)
    for i, (c, x, size) in enumerate((((1, 0.45, 0.08), 1.6, 1.1), ((1, 0.08, 0.05), -1.8, 0.4), ((0.1, 0.25, 1), -1.1, 0.4), ((1, 0.9, 0.7), 2.9, 0.22))):
        s.box('Far light', opened, (window[0] + x, window[1] - 2.0, window[2] + 0.4), (size, size, 0.2), c, emissive=c, emissive_intensity=9.0, shape='Sphere', shadows=False)
    s.light('Choir light', choir, (0, top_y + 30, zt - 10), 'Point', (1, 0.9, 0.7), 5000.0, 90)
    turn = P.between(s, root, 'Angels gaze', 'angels_turn', None, 2.0, arch_at)
    gaze_from = (0, top_y + 15, zt - 26)
    s.light('Gaze', turn, gaze_from, 'Spot', (1, 0.95, 0.75), 9000.0, 90, rot=look_rotation(gaze_from, (0, 1.2, 5.2)), inner=5, outer=12)

    # Earth, far off in the same scene (beyond the sky): the crash site at night, the rescue.
    E = (1600.0, 0.0, 0.0)
    earth_root = s.group('Earth', root)
    # Slow motion (the fire, the lights, the compressions) until the drummer wakes.
    earth = P.slow_motion(s, earth_root, 'Slow motion', 'resurrection', 0.25)
    road(s, earth, V, E[0] - 14, E[0] + 14, E[2] - 70, E[2] + 70)
    roadside(s, earth, V, E, 70.0, 14.0, torn_z=E[2] + 10.0)
    A.model(s, earth, 'Mile marker', A.sign_face(V, 'MileMarker'), (E[0] + 15.6, 1.6, E[2] + 20), (0, 180, 0), (0.45, 0.6, 1), A.mat(V, 'MileMarker', glow=(1, 1, 1), power=0.5), shadows=False)
    s.box('Mile marker post', earth, (E[0] + 15.6, 0.5, E[2] + 20.04), (0.08, 1.0, 0.05), STEEL)
    cruiser(s, earth, V, (E[0] - 7.5, 0, E[2] - 9), 24, door_open=True)
    # The cop kneels at the drummer's chest (the body lies at yaw 200 from its feet at (-1, 1)), facing across it.
    cop_at = (-1.26, 110, 2.48)
    hand = crash_site(s, earth, V, (E[0], 0, E[2] + 6), {'wake': 'resurrection', 'cop': None, 'nod': 'cop_nod_final'}, cop=cop_at, ems=True, wreck_at=(4.0, 0, -2.0))
    cop_eye = (E[0] + cop_at[0], 1.0, E[2] + 6 + cop_at[2])
    for i, (x, z, yaw) in enumerate(((-9.5, -20, 20), (-3.0, -24, -30), (4.5, -22, 60), (-12.0, 12, 80))):
        A.flare(s, earth, V, f'Flare {i}', (E[0] + x, 0, E[2] + z), yaw)
    ground_fog(s, earth, V, (E[0], 0.5, E[2]), (46, 1.0, 60), 12)
    s.light('Earth moon', earth, (E[0], 30, E[2] - 10), 'Spot', (0.4, 0.48, 0.75), 9000.0, 70, rot=(80, 0, 0), inner=35, outer=65)

    # A few more places to shoot the show from.
    s.camera_spot('Camera behind the band', marks, (5.2, 2.6, 10.5), (0, top_y - 2, zt - 6), 'Custom', 44, 'behind')
    s.camera_spot('Camera high', marks, (-14, 16, 8), (0, 3, -8), 'Custom', 50, 'high')
    s.camera_spot('Camera stair head', marks, (1.6, top_y + 2.4, zt + 2.0), (0, 1.0, 3.5), 'Custom', 34, 'stairhead')

    # Story shots.
    face = (DRUMMER[0], 1.32, DRUMMER[1] - 0.1)
    # While they float (Band's Floating pose) everyone hangs about 0.6 m up, swaying a quarter of a metre.
    afloat = (face[0], face[1] + 0.6, face[2])
    afloat = (afloat[0], afloat[1] - 0.2, afloat[2])       # the drummer sits: the face is a little lower
    shot(s, marks, 'ascent', (afloat[0] + 0.9, afloat[1], afloat[2] - 0.95), afloat, 34, 14, focus=True,
         end=((afloat[0] + 1.25, afloat[1] + 0.05, afloat[2] - 0.7), afloat, 38))
    other = (BASS[0], 1.62 + 0.6, BASS[1])
    # Past the bass player's shoulder to the drummer: one looks down for the other, and the focus goes with the look.
    shot(s, marks, 'eyes_meet', (other[0] + 1.3, other[1] + 0.1, other[2] - 1.5), other, 38, 8, focus=True,
         end=((other[0] + 1.5, other[1] + 0.15, other[2] - 1.9), afloat, 34))
    shot(s, marks, 'horizon', (-3.0, 2.2, 9.5), (0.5, 1.2, 3.0), 40, 12,
         via=[((-7.0, 3.5, 4.0), (2, -6, -40), 52)], end=((-9.5, 5.0, -4.0), (30, -30, -200), 64))
    shot(s, marks, 'touchdown', (face[0] + 0.7, face[1] + 0.1, face[2] - 0.5), face, 40, 9,
         via=[((2.6, 0.5, 0.8), (0, 0.4, 4.0), 50), ((5.5, 2.0, -5.0), (0, 2.0, 3), 54)], end=((2.5, 6.5, -4.5), (0, top_y, zt - 6), 62))
    shot(s, marks, 'choir', (0.8, 1.7, 8.2), (0, top_y + 12, zt - 26), 34, 14,
         via=[((1.5, 3.0, 13.0), (0, top_y + 16, zt - 30), 52), ((0, 9.0, 26.0), (0, top_y + 20, zt - 30), 70)], end=((0, 22.0, 44.0), (0, top_y + 24, zt - 40), 84))
    shot(s, marks, 'heaven_wide', (0, 12, 36), (0, 20, -50), 60, 12, via=[((10, 20, 52), (0, 24, -50), 66)], end=((0, 32, 74), (0, 28, -50), 72))
    shot(s, marks, 'angels_turn', (3.5, 6, -9), arch_at, 40, 7, end=((2.0, 3.0, -1.0), (0, top_y + 14, zt - 28), 52))
    shot(s, marks, 'sticks_close', (2.5, 5, -3), (0, 1.2, 4.6), 44, 20, focus=True, via=[((1.2, 1.9, 2.6), (0, 1.0, 4.4), 36)],
         end=((0.45, 1.05, DRUMMER[1] - 1.9), (0.0, 0.85, DRUMMER[1] - 1.3), 34))
    shot(s, marks, 'drum_open', (0.9, 1.4, DRUMMER[1] - 2.0), (0, 1.1, DRUMMER[1] - 0.6), 36, 7, focus=True, end=((-1.3, 1.6, DRUMMER[1] - 2.4), (0, 1.25, DRUMMER[1] - 0.3), 40))
    cop_head = add3((cop_eye[0], 0, cop_eye[2]), P_rot((0, 0.95, 0.45), cop_at[1]))      # he leans over the drummer as he pumps
    cop_hands = add3((cop_eye[0], 0, cop_eye[2]), P_rot((0, 0.3, 0.75), cop_at[1]))
    shot(s, marks, 'cpr', (cop_hands[0] + 0.9, 0.3, cop_hands[2] - 1.5), cop_hands, 34, 8, hand=True, focus=True,
         end=((cop_eye[0] + 1.5, 0.75, cop_eye[2] - 1.0), (cop_eye[0], 1.0, cop_eye[2]), 30))
    shot(s, marks, 'earth_wide', (E[0] - 6.5, 0.9, E[2] - 4.0), (E[0] + 2.0, 1.2, E[2] + 9), 44, 8, end=((E[0] - 5.0, 1.6, E[2] - 6.0), (E[0] + 2.5, 1.0, E[2] + 9), 38))
    shot(s, marks, 'cpr_close', (cop_head[0] + 1.5, 0.8, cop_head[2] + 0.75), cop_head, 22, 5, hand=True, focus=True,
         end=((cop_head[0] + 1.35, 0.85, cop_head[2] + 0.55), cop_head, 17))
    shot(s, marks, 'god_descends', (3.2, top_y + 1.6, zt + 2.5), (0, top_y + 3.2, zt - 13), 40, 8, via=[((6.5, top_y * 0.6, z0 - 4), (0, top_y * 0.6 + 2.5, zt + 4), 46)],
         end=((5.5, 1.6, 0.5), (0, 2.6, -4.5), 44))
    shot(s, marks, 'angels_part', (1.2, 1.7, 7.4), (0, 4, -4), 46, 8, via=[((0.5, 3.0, 2.0), window, 40)], end=((0, top_y + 5.5, zt - 9), window, 30))
    shot(s, marks, 'resurrection', (hand[0] - 0.9, 1.3, hand[2] - 1.8), (hand[0] + 0.4, 0.2, hand[2] + 0.4), 40, 9, focus=True,
         end=(beside_hand(hand, 200, 0.95, 0.6, 0.12), (hand[0], 0.05, hand[2]), 28))
    shot(s, marks, 'cop_nod_final', (cop_head[0] + 1.3, 0.7, cop_head[2] - 1.9), cop_head, 30, 30, focus=True,
         end=((cop_head[0] + 1.0, 0.8, cop_head[2] - 1.4), cop_head, 22))
    write(s, V, 'Heaven')


def prune(venue):
    """Remove what earlier runs generated into the venue that its scene no longer uses: models,
    material libraries, clips and textures (with their .meta and cooked twins)."""
    import re
    folder = os.path.join(repo_root(), 'Assets', 'Venues', venue)
    prefix = f'Assets/Venues/{venue}/'
    scene = open(os.path.join(folder, venue + '.lvl'), encoding='utf-8').read()
    keep = {m[len(prefix):] for m in re.findall(re.escape(prefix) + r'[^"]+', scene)}
    for rel in list(keep):
        if rel.endswith('.obj'):
            base = os.path.dirname(rel)
            for line in open(os.path.join(folder, rel), encoding='utf-8'):
                if line.startswith('mtllib '):
                    mtl = base + '/' + line.split(None, 1)[1].strip()
                    keep.add(mtl)
                    for entry in open(os.path.join(folder, mtl), encoding='utf-8'):
                        if entry.startswith('map_Kd ') and not entry.split(None, 1)[1].startswith('../../../../'):
                            keep.add(os.path.normpath(os.path.join(base, entry.split(None, 1)[1].strip())).replace('\\', '/'))
                    break
    removed = 0
    for sub_ in ('Models/Set', 'Models/People', 'Motion', 'Textures'):
        base = os.path.join(folder, *sub_.split('/'))
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            if not name.endswith(('.obj', '.mtl', '.sequence', '.png')) or f'{sub_}/{name}' in keep:
                continue
            for extra in ('', '.meta', '.assbin', '.dds'):
                if os.path.exists(os.path.join(base, name + extra)):
                    os.remove(os.path.join(base, name + extra))
            removed += 1
    if removed:
        print(f'Assets/Venues/{venue}: {removed} unused generated files removed')


def main():
    highway()
    hell()
    heaven()
    for venue in ('StoryHighway', 'StoryHell', 'StoryHeaven'):
        prune(venue)
    # AFTERLIFE_SHOTS=<file>: the story shots as eye / target / field of view, for previews
    # (--venue-eye "x,y,z,tx,ty,tz,fov").
    out = os.environ.get('AFTERLIFE_SHOTS')
    if out:
        with open(out, 'w', newline='\n') as f:
            json.dump(SHOTS, f, indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main())
