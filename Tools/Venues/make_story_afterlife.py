#!/usr/bin/env python3
"""Builds the three venues of "Highway to the Afterlife" (Design/Highway-to-the-Afterlife.md), the
proposed story set highway-afterlife in Design/Story-Mode-Setlists.json:

    python3 Tools/Venues/make_story_afterlife.py

  StoryHighway  Kickstart My Heart: the band on a flatbed trailer down a night highway that scrolls
                past, the cruiser behind with its lightbar going; the wreck on a marked stretch of
                shoulder, and the band's bodies on the asphalt.
  StoryHell     Free Bird and Bat Country: the crash site, the fall down a shaft, and hell: a stone
                floor, the staircase, demons on the balustrades and in the crowd, Satan's throne.
  StoryHeaven   Stairway to Heaven and My Hero: the ascent through cloud, the cloud floor, the
                stairs and God's platform, the angel choir; and, far off in the same scene, the
                crash site on Earth for the rescue cut-aways.

Greybox: primitives, posed figures (story_afterlife_people) and looping clips. Every story beat
is a story flag (the set's cues and moments in the manifest): VenueStory groups show the props
for it, and a Custom camera spot tagged story/<flag>[/<seconds>][/hand] (with an optional
story/<flag>/end where it moves to) is the shot the director cuts to when it lands
(Director::SetStoryShots). Deterministic: a rerun writes the same bytes.
"""
import math
import os
import random
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import story_afterlife_people as P  # noqa: E402
from venuegen import Scene, look_rotation, repo_root, write_venue_json  # noqa: E402

# Colours.
ASPHALT = (0.07, 0.07, 0.08)
LINE_WHITE = (0.85, 0.85, 0.8)
LINE_YELLOW = (0.9, 0.7, 0.15)
GRAVEL = (0.22, 0.2, 0.18)
GRASS = (0.06, 0.1, 0.05)
STEEL = (0.35, 0.36, 0.38)
DECK = (0.24, 0.18, 0.12)
RUBBER = (0.05, 0.05, 0.05)
CAB_RED = (0.55, 0.06, 0.05)
NAVY = (0.05, 0.07, 0.16)
WHITE = (0.9, 0.9, 0.92)
FIRE = (1.0, 0.45, 0.08)
EMBER = (1.0, 0.2, 0.03)
STONE = (0.16, 0.12, 0.11)
STONE_DARK = (0.08, 0.06, 0.06)
LAVA = (1.0, 0.25, 0.02)
HORN = (0.35, 0.02, 0.02)
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


def band(s, marks, y):
    s.spot(marks, 'Drummer', (DRUMMER[0], y, DRUMMER[1]))
    s.spot(marks, 'Guitar', (GUITAR[0], y, GUITAR[1]), yaw=-8)
    s.spot(marks, 'Bass', (BASS[0], y, BASS[1]), yaw=8)
    s.spot(marks, 'Vocals', (VOCALS[0], y, VOCALS[1]))


def shot(s, marks, flag, eye, target, fov=50.0, hold=None, hand=False, end=None):
    """The story shot for flag: from eye at target; end (eye, target, fov) is where it moves to."""
    tag = 'story/' + flag + (f'/{hold:g}' if hold else '') + ('/hand' if hand else '')
    s.camera_spot('Story ' + flag, marks, eye, target, 'Custom', fov, tag)
    if end:
        s.camera_spot('Story ' + flag + ' end', marks, end[0], end[1], 'Custom', end[2], 'story/' + flag + '/end')


def write(s, venue, name, ambience=None):
    folder = os.path.join(repo_root(), 'Assets', 'Venues', venue)
    os.makedirs(folder, exist_ok=True)
    s.write(os.path.join(folder, venue + '.lvl'))
    write_venue_json(folder, name, venue + '.lvl', author='Drumsmith', ambience=ambience)
    print(f'Assets/Venues/{venue}: {len(s.entities)} entities')


# ---- shared pieces ------------------------------------------------------------------------------
def fire(s, parent, venue, at, size=1.0, light=500.0):
    """A fire: flame boxes flickering on a loop, embers, and an orange light."""
    flicker = P.clip(venue, 'Flicker', 18, [P.track('Scale', [(0, (1, 1, 1)), (5, (1.1, 1.35, 1.05)), (11, (0.92, 0.85, 1.1)), (18, (1, 1, 1))], 'SmoothStep')])
    body = P.looping(s, parent, 'Fire', flicker, at)
    rng = random.Random(int(at[0] * 100 + at[2] * 7))
    for i in range(7):
        h = size * rng.uniform(0.8, 2.2)
        s.box(f'Flame {i}', body, (rng.uniform(-1, 1) * size, h / 2, rng.uniform(-1, 1) * size), (0.5 * size, h, 0.5 * size),
              FIRE if i % 2 else EMBER, rot=(0, rng.uniform(0, 90), rng.uniform(-10, 10)), emissive=FIRE if i % 2 else EMBER, emissive_intensity=6.0, shadows=False)
    s.light('Fire light', parent, (at[0], at[1] + 2.0 * size, at[2]), 'Point', (1.0, 0.5, 0.15), light, 18 * size)


def lightbar(s, parent, venue, at):
    """A cruiser's lightbar: red and blue lamps and two spot lights sweeping round."""
    spin = P.clip(venue, 'LightbarSpin', 24, [P.track('Rotation', [(0, (0, 0, 0)), (12, (0, 180, 0)), (24, (0, 359.9, 0))])])
    s.box('Lightbar', parent, at, (1.3, 0.12, 0.28), (0.1, 0.1, 0.1))
    s.box('Lamp red', parent, (at[0] - 0.4, at[1] + 0.06, at[2]), (0.45, 0.14, 0.24), (1, 0.05, 0.05), emissive=(1, 0.05, 0.05), emissive_intensity=8.0, shadows=False)
    s.box('Lamp blue', parent, (at[0] + 0.4, at[1] + 0.06, at[2]), (0.45, 0.14, 0.24), (0.1, 0.2, 1), emissive=(0.1, 0.2, 1), emissive_intensity=8.0, shadows=False)
    body = P.looping(s, parent, 'Sweep', spin, (at[0], at[1] + 0.2, at[2]))
    s.light('Sweep red', body, (0, 0, 0), 'Spot', (1.0, 0.05, 0.05), 350.0, 40, rot=(12, 0, 0), inner=12, outer=28)
    s.light('Sweep blue', body, (0, 0, 0), 'Spot', (0.1, 0.25, 1.0), 350.0, 40, rot=(12, 180, 0), inner=12, outer=28)


def cruiser(s, parent, venue, at, yaw=0.0, name='Cruiser'):
    """A police car facing +z at yaw 0, its centre at at (on the road). Returns its group."""
    g = s.entity(name, parent, at, (0, yaw, 0))
    s.box('Body', g, (0, 0.7, 0), (1.9, 0.75, 4.9), NAVY, rough=0.4, metallic=0.3)
    s.box('Door stripe', g, (0, 0.72, 0), (1.92, 0.22, 2.2), WHITE)
    s.box('Cabin', g, (0, 1.3, -0.3), (1.7, 0.55, 2.4), (0.04, 0.05, 0.07), rough=0.2)
    s.box('Windshield', g, (0, 1.3, 0.95), (1.6, 0.5, 0.06), (0.15, 0.22, 0.3), rot=(-35, 0, 0), rough=0.05)
    for x in (-0.85, 0.85):
        for z in (-1.5, 1.5):
            s.box('Wheel', g, (x, 0.35, z), (0.7, 0.3, 0.7), RUBBER, rot=(0, 0, 90), shape='Cylinder')
    for x in (-0.6, 0.6):
        s.box('Headlight', g, (x, 0.75, 2.46), (0.35, 0.15, 0.05), (1, 1, 0.9), emissive=(1, 1, 0.85), emissive_intensity=5.0, shadows=False)
    s.light('Headlights', g, (0, 0.8, 2.6), 'Spot', (1.0, 0.95, 0.85), 500.0, 45, rot=(4, 0, 0), inner=18, outer=34)
    lightbar(s, g, venue, (0, 1.65, -0.3))
    return g


def asphalt(s, parent, x0, x1, z0, z1, dashes=True):
    s.slab('Asphalt', parent, x0, x1, -0.2, 0.0, z0, z1, ASPHALT, rough=0.95)
    s.slab('Edge line L', parent, x0 + 0.3, x0 + 0.45, 0.0, 0.01, z0, z1, LINE_WHITE, shadows=False)
    s.slab('Edge line R', parent, x1 - 0.45, x1 - 0.3, 0.0, 0.01, z0, z1, LINE_WHITE, shadows=False)
    if dashes:
        z = z0
        while z < z1:
            for x in (-3.6, 3.6):
                if x0 < x < x1:
                    s.slab('Dash', parent, x - 0.07, x + 0.07, 0.0, 0.01, z, z + 3.0, LINE_YELLOW, shadows=False)
            z += 12.0


def wreck(s, parent, venue, o):
    """The trailer slewed across the lane onto its side on the shoulder at o, burning."""
    g = s.group('Wreck', parent, o)
    t = s.entity('Wrecked trailer', g, (2.5, 0, 6.5), (0, 38, 0))
    s.box('Deck', t, (0, 1.3, 0), (0.35, 2.6, 9.0), (0.08, 0.06, 0.05), rot=(0, 0, 8))
    s.box('Frame', t, (0.5, 0.5, 0), (0.6, 0.6, 9.0), (0.1, 0.1, 0.1))
    for z in (-3.5, -2.2, 2.2, 3.5):
        s.box('Wheel', t, (-0.4, 2.4, z), (1.0, 0.35, 1.0), RUBBER, shape='Cylinder')
    s.box('Kit case', g, (0.9, 0.4, 5.5), (1.0, 0.8, 1.0), (0.1, 0.1, 0.1), rot=(0, 25, 0))
    s.box('Floor tom', g, (0.1, 0.3, 8.5), (0.5, 0.45, 0.5), (0.5, 0.1, 0.1), rot=(70, 0, 20), shape='Cylinder')
    s.box('Cymbal', g, (-0.7, 0.03, 7.0), (0.9, 0.02, 0.9), (0.75, 0.6, 0.25), metallic=0.9, rough=0.3, shape='Cylinder')
    fire(s, g, venue, (3.2, 0, 5.0), 1.2, 700.0)
    fire(s, g, venue, (1.0, 0, 9.0), 0.8, 300.0)
    return g


def crash_site(s, parent, venue, o, flags, cop=None, ems=False, burning=True, lying=None):
    """The crash site around o: the wreck (burning), the band on the asphalt and a dropped stick.
    flags: the flags the figures change at ('wake': the drummer opens their eyes, 'nod': the cop
    nods). cop: (x, yaw, z) where the cop kneels giving CPR (None: no cop). ems: the medics and the
    ambulance. lying: who lies where ({member: (x, z, yaw)} relative to o) instead of the usual
    spread. Returns the drummer's hand in venue space."""
    ox, oy, oz = o
    if burning:
        wreck(s, parent, venue, o)
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
    s.box('Drumstick', g, (hand[0] + 0.3, 0.02, hand[2] + 0.12), (0.03, 0.41, 0.03), (0.85, 0.7, 0.45), rot=(90, 70, 0), shape='Cylinder')
    s.box('Glass', g, (0.5, 0.01, 2.5), (2.5, 0.01, 1.6), (0.3, 0.32, 0.35), rough=0.1, metallic=0.6, shadows=False)
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
            s.box('Hi-vis', g, (at[0], 1.0, at[2]), (0.05, 0.05, 0.05), (0.9, 0.9, 0.1), shadows=False)
        amb = s.entity('Ambulance', g, (-9, 0, 8), (0, 160, 0))
        s.box('Box', amb, (0, 1.5, 0), (2.4, 2.6, 6.0), WHITE)
        s.box('Stripe', amb, (0, 1.6, 0), (2.42, 0.3, 6.02), (0.8, 0.1, 0.1), shadows=False)
        lightbar(s, amb, venue, (0, 2.95, 2.4))
    return (ox + hand[0], oy + hand[1], oz + hand[2])


def sky_dome(s, parent, centre, half, color=(0.01, 0.012, 0.02)):
    """A closed dark room around centre: the Earth set inside the bright heaven scene."""
    cx, cy, cz = centre
    for name, a in (('N', (cx - half, cx + half, cy - 2, cy + half, cz + half, cz + half + 1)),
                    ('S', (cx - half, cx + half, cy - 2, cy + half, cz - half - 1, cz - half)),
                    ('E', (cx + half, cx + half + 1, cy - 2, cy + half, cz - half, cz + half)),
                    ('W', (cx - half - 1, cx - half, cy - 2, cy + half, cz - half, cz + half)),
                    ('Top', (cx - half, cx + half, cy + half, cy + half + 1, cz - half, cz + half)),
                    ('Ground', (cx - half, cx + half, cy - 3, cy - 0.25, cz - half, cz + half))):
        s.slab('Night ' + name, parent, *a, color, rough=1.0, shadows=False)


# ---- the highway --------------------------------------------------------------------------------
def highway():
    V = 'StoryHighway'
    s = Scene(seed=6601)
    root = s.group('Highway to the Afterlife: the highway')
    marks = s.group('Markers', root)
    s.info(marks, 'The Highway', 'Drumsmith', outdoor=True, half_width=60, desk_z=-30, sky_time=21.5, moon=0.6, haze=0.6)
    deck_y = 1.25
    band(s, marks, deck_y)
    s.camera_spot('Camera Wide', marks, (6, 7, -26), (0, 2, 4), 'Wide', 50)
    s.camera_spot('Camera Crane', marks, (-5, 9, -16), (0, 2, 4), 'Crane', 55)
    s.camera_spot('Camera Desk', marks, (2, 2.6, -13.5), (0, 2.2, 4), 'Desk', 30)

    # The road and the shoulders, standing still; what scrolls is the markings and the poles. In the
    # closing bars the whole world turns about the trailer (trailer_slews): the trailer slewing
    # across the lane, seen from the deck. Everything on the road turns with it.
    slew_clip = P.clip(V, 'Slew', 120, [P.track('Rotation', [(0, (0, 0, 0)), (40, (0, 8, 2)), (120, (0, SLEW_YAW, 0))], 'SmoothStep'),
                                        P.track('Position', [(0, (0, 0, 0)), (120, SLEW_SHIFT)], 'SmoothStep')])
    world = s.group('World', P.play(s, root, 'Slew', 'trailer_slews', slew_clip))
    s.slab('Asphalt', world, -11, 11, -0.2, 0.0, -420, 140, ASPHALT, rough=0.95)
    for x in (-10.7, 10.55):
        s.slab('Edge line', world, x, x + 0.15, 0.0, 0.01, -420, 140, LINE_WHITE, shadows=False)
    s.slab('Gravel L', world, -14, -11, -0.25, -0.02, -420, 140, GRAVEL)
    s.slab('Gravel R', world, 11, 14, -0.25, -0.02, -420, 140, GRAVEL)
    s.slab('Field L', world, -120, -14, -0.4, -0.1, -420, 140, GRASS)
    s.slab('Field R', world, 14, 120, -0.4, -0.1, -420, 140, GRASS)
    rng = random.Random(7)
    for i in range(14):
        x = rng.choice((-1, 1)) * rng.uniform(140, 220)
        s.box(f'Hill {i}', world, (x, 0, rng.uniform(-400, 120)), (rng.uniform(40, 90), rng.uniform(8, 22), rng.uniform(40, 90)), (0.03, 0.04, 0.03), shadows=False)
    s.light('Moon', world, (0, 60, -40), 'Directional', (0.55, 0.6, 0.8), 1.2, 400, rot=(40, 25, 0), shadows=True, show='Static')

    # Moving at 30 m/s until the wreck: lane dashes every 12 m, poles every 48 m.
    moving = P.between(s, world, 'Road moving', None, 'wreck', 0.2)
    dash_clip = P.clip(V, 'RoadDashes', 12, [P.track('Position', [(0, (0, 0, 0)), (12, (0, 0, -12))])])
    dashes = P.looping(s, moving, 'Dashes', dash_clip)
    for k in range(-34, 13):
        for x in (-3.6, 3.6):
            s.slab('Dash', dashes, x - 0.07, x + 0.07, 0.0, 0.012, k * 12, k * 12 + 3, LINE_YELLOW, shadows=False)
    def poles(parent):
        for k in range(-8, 4):
            z = k * 48
            for side in (-1, 1):
                x = side * 13
                s.box('Pole', parent, (x, 5, z), (0.25, 10, 0.25), STEEL, shadows=False)
                s.box('Arm', parent, (x - side * 1.5, 9.9, z), (3.0, 0.15, 0.2), STEEL, shadows=False)
                s.box('Lamp', parent, (x - side * 2.8, 9.75, z), (0.6, 0.12, 0.3), (1, 0.85, 0.55), emissive=(1, 0.8, 0.5), emissive_intensity=6.0, shadows=False)
                if -2 <= k <= 1:
                    s.light('Pole light', parent, (x - side * 2.8, 9.5, z), 'Spot', (1.0, 0.78, 0.5), 1100.0, 26, rot=(90, 0, 0), inner=30, outer=55)
    pole_clip = P.clip(V, 'RoadPoles', 48, [P.track('Position', [(0, (0, 0, 0)), (48, (0, 0, -48))])])
    poles(P.looping(s, moving, 'Poles', pole_clip))
    # Stopped: the markings and poles where they stood.
    still = P.between(s, world, 'Road stopped', 'wreck', None, 0.2)
    poles(still)
    for k in range(-34, 13):
        for x in (-3.6, 3.6):
            s.slab('Dash', still, x - 0.07, x + 0.07, 0.0, 0.012, k * 12, k * 12 + 3, LINE_YELLOW, shadows=False)

    # The flatbed and its tractor, the band on the deck.
    rig = s.group('Rig', root)
    s.slab('Deck', rig, -3.0, 3.0, 0.95, deck_y, -1.2, 9.0, DECK)
    s.slab('Deck edge', rig, -3.05, 3.05, 0.75, 0.95, -1.25, 9.05, STEEL)
    wheel_clip = P.clip(V, 'WheelSpin', 6, [P.track('Rotation', [(0, (0, 0, 0)), (3, (180, 0, 0)), (6, (359.9, 0, 0))])])
    for z in (0.0, 1.3, 6.0, 7.3):
        for x in (-2.6, 2.6):
            spinner = P.looping(s, P.between(s, rig, 'Wheel', None, 'wreck', 0.2, (x, 0.55, z)), 'Wheel', wheel_clip, (x, 0.55, z))
            s.box('Tyre', spinner, (0, 0, 0), (1.1, 0.4, 1.1), RUBBER, rot=(0, 0, 90), shape='Cylinder')
            s.box('Hub', spinner, (0, 0, 0.3), (0.42, 0.42, 0.12), STEEL, metallic=0.8)
    for x in (-2.0, 2.0):
        s.box('Monitor', rig, (x * 0.6, deck_y + 0.25, -0.6), (0.7, 0.5, 0.55), (0.05, 0.05, 0.05), rot=(-25, 0, 0))
    s.slab('Truss L', rig, -2.9, -2.75, deck_y, deck_y + 4.0, 8.4, 8.6, STEEL)
    s.slab('Truss R', rig, 2.75, 2.9, deck_y, deck_y + 4.0, 8.4, 8.6, STEEL)
    s.slab('Truss top', rig, -2.9, 2.9, deck_y + 3.9, deck_y + 4.1, 8.4, 8.6, STEEL)
    for i, x in enumerate((-2.0, -0.7, 0.7, 2.0)):
        s.light(f'Truss wash {i}', rig, (x, deck_y + 3.8, 8.3), 'Spot', (0.6, 0.6, 1.0) if i % 2 else (1.0, 0.5, 0.3), 1400.0, 14,
                rot=look_rotation((x, deck_y + 3.8, 8.3), (x * 0.5, deck_y + 1, 2.5)), inner=22, outer=40, show='Wash', group=i)
    cab = s.group('Tractor', rig, (0, 0, 13.5))
    s.box('Cab', cab, (0, 2.0, 0), (2.6, 2.8, 3.2), CAB_RED, rough=0.35, metallic=0.4)
    s.box('Sleeper', cab, (0, 2.3, -2.2), (2.6, 2.6, 1.4), CAB_RED, rough=0.35, metallic=0.4)
    s.box('Stack L', cab, (-1.2, 4.0, -1.0), (0.25, 2.5, 0.25), STEEL, metallic=0.9, shape='Cylinder')
    s.box('Stack R', cab, (1.2, 4.0, -1.0), (0.25, 2.5, 0.25), STEEL, metallic=0.9, shape='Cylinder')
    s.box('Tail lights', rig, (0, 0.85, -1.27), (5.6, 0.12, 0.05), (1, 0.05, 0.05), emissive=(1, 0.05, 0.05), emissive_intensity=4.0, shadows=False)

    # The cruiser behind, the cop at the wheel: driving, then the radio, then the nod.
    car_at = (0.0, 0.0, -13.0)
    cruiser(s, world, V, car_at)
    seat = (car_at[0] - 0.45, 0.32, car_at[2] - 0.2)
    for flag_after, flag_before, pose, label in ((None, 'cop_radio', P.DRIVING, 'Cop_driving'), ('cop_radio', 'cop_nods', P.RADIO, 'Cop_radio'),
                                                 ('cop_nods', None, P.NODDING, 'Cop_nodding')):
        model = P.figure(V, label, 'ShopKeeper_01', '04_B', pose, 'the highway cop')
        P.place(s, P.between(s, world, label, flag_after, flag_before, 0.05, seat), 'Cop', model, seat, 0)
    s.box('Steering wheel', world, (seat[0], 1.05, seat[2] + 0.45), (0.38, 0.04, 0.38), (0.05, 0.05, 0.05), rot=(-60, 0, 0), shape='Cylinder')
    s.light('Dash glow', world, (seat[0], 1.0, seat[2] + 0.6), 'Point', (0.4, 0.6, 1.0), 6.0, 2)

    # The marked stretch of shoulder (the finale comes back to it): mile marker 66, a sign, the wreck.
    W = (21.0, 0.0, -60.0)
    s.box('Mile marker', world, (W[0] - 6, 0.7, W[2] + 10), (0.3, 1.4, 0.08), (0.1, 0.4, 0.15))
    s.box('Mile marker number', world, (W[0] - 6, 1.1, W[2] + 9.95), (0.22, 0.25, 0.01), WHITE, emissive=WHITE, emissive_intensity=0.4, shadows=False)
    s.box('Billboard', world, (W[0] + 14, 7, W[2] + 4), (12, 5, 0.3), (0.7, 0.65, 0.4), rot=(0, -20, 0))
    s.box('Billboard legs', world, (W[0] + 14, 2.2, W[2] + 4), (8, 4.4, 0.2), STEEL, rot=(0, -20, 0))
    s.slab('Shoulder asphalt', world, W[0] - 9, W[0] + 9, -0.08, 0.0, W[2] - 12, W[2] + 14, ASPHALT, rough=0.95)
    # The burning trailer shows from the crash, the bodies from the next beat.
    wreck(s, P.between(s, world, 'Wreck', 'wreck', None, 0.25, W), V, W)
    hand = slewed(crash_site(s, P.between(s, world, 'Bodies', 'bodies', None, 0.01, W), V, W, {}, burning=False))
    # The explosion: a fireball up off the trailer and gone in two seconds.
    ball_clip = P.clip(V, 'Fireball', 66, [P.track('Scale', [(0, (0.05, 0.05, 0.05)), (7, (13, 10, 13)), (30, (10, 9, 10)), (66, (0.01, 0.01, 0.01))], 'SmoothStep')])
    ball = P.play(s, world, 'Fireball', 'wreck', ball_clip, (W[0] + 3, 3.0, W[2] + 5))
    s.box('Fireball', ball, (0, 0, 0), (1, 1, 1), FIRE, emissive=FIRE, emissive_intensity=12.0, shape='Sphere', shadows=False)
    s.box('Fireball core', ball, (0, 0, 0), (0.6, 0.6, 0.6), (1, 0.9, 0.6), emissive=(1, 0.9, 0.6), emissive_intensity=20.0, shape='Sphere', shadows=False)

    # Story shots.
    shot(s, marks, 'highway_open', (2.95, 0.32, 0.4), (2.6, 0.55, 1.2), 62, 8, end=((0.7, 1.55, 2.2), (0.0, 1.55, 4.3), 50))
    shot(s, marks, 'cop_watching', (seat[0], 1.32, car_at[2] + 2.6), (seat[0], 1.25, seat[2]), 34, 5)
    shot(s, marks, 'heli_chase', (-28, 34, -48), (0, 1.0, -4), 48, 8, hand=True, end=((-27, 33, -46), (0, 2.4, 5.2), 9))
    shot(s, marks, 'foot_on_monitor', (3.6, 1.6, 0.6), (1.9, 2.3, 2.6), 44, 4, hand=True)
    shot(s, marks, 'cop_radio', (seat[0] + 1.6, 1.45, seat[2] + 0.5), (seat[0], 1.3, seat[2]), 36, 4)
    shot(s, marks, 'cop_nods', (seat[0], 1.32, car_at[2] + 2.2), (seat[0], 1.27, seat[2]), 24, 4)
    shot(s, marks, 'heli_again', (38, 30, 18), (0, 1.5, 0), 40, 6, hand=True, end=((34, 28, -12), (0, 1.5, 0), 34))
    Ws = slewed((W[0], 1, W[2] + 4))
    shot(s, marks, 'trailer_slews', (2.6, 2.4, -1.6), (-0.4, 1.6, 4.0), 56, 4, hand=True)
    shot(s, marks, 'wreck', (Ws[0] - 30, 26, Ws[2] - 30), Ws, 42, 7, hand=True, end=((Ws[0] - 26, 22, Ws[2] - 26), Ws, 30))
    shot(s, marks, 'bodies', (hand[0] - 0.5, 0.18, hand[2] - 0.7), (hand[0] + 0.3, 0.05, hand[2] + 0.4), 40, 40)
    write(s, V, 'The Highway')


# ---- hell ---------------------------------------------------------------------------------------
def hell():
    V = 'StoryHell'
    s = Scene(seed=6602)
    root = s.group('Highway to the Afterlife: hell')
    marks = s.group('Markers', root)
    s.info(marks, 'Hell', 'Drumsmith', outdoor=False, room_back=-40, room_ceiling=60, half_width=22, desk_z=-14,
           ambient=(0.02, 0.003, 0.002), fog_color=(0.05, 0.012, 0.005), haze=0.7)
    band(s, marks, 0.0)
    s.camera_spot('Camera Wide', marks, (0, 5.5, -13), (0, 1.6, 4), 'Wide', 55)
    s.camera_spot('Camera Crane', marks, (6, 8, -10), (0, 1.6, 4), 'Crane', 55)
    s.camera_spot('Camera Desk', marks, (-1.5, 2.8, -11), (0, 2.0, 4), 'Desk', 30)
    for i, (x, c) in enumerate(((-3.5, (1.0, 0.25, 0.05)), (3.5, (1.0, 0.1, 0.05)), (-1.2, (1.0, 0.45, 0.1)), (1.2, (0.9, 0.15, 0.1)))):
        s.light(f'Wash {i}', marks, (x, 7, -1), 'Spot', c, 1600.0, 18, rot=look_rotation((x, 7, -1), (x * 0.4, 1, 3.5)), inner=22, outer=42, show='Wash', group=i)

    # 1. The crash site, until they fall.
    crash = P.between(s, root, 'The crash site', None, 'fell', 2.5)
    asphalt(s, crash, -14, 14, -30, 24)
    s.slab('Shoulder', crash, 14, 40, -0.25, -0.02, -30, 24, GRAVEL)
    s.slab('Field', crash, -40, -14, -0.3, -0.05, -30, 24, GRASS)
    s.light('Moon', crash, (0, 40, -20), 'Directional', (0.45, 0.5, 0.7), 0.6, 300, rot=(50, 20, 0), shadows=True)
    cruiser(s, crash, V, (-7.5, 0, -9), 20)
    wreck(s, crash, V, (7.0, 0, 9.0))
    spots = {'drummer': (DRUMMER[0] + 0.3, DRUMMER[1] + 0.6, 180), 'guitar': (GUITAR[0], GUITAR[1], 172), 'bass': (BASS[0], BASS[1], 188), 'vocals': (VOCALS[0], VOCALS[1], 180)}
    hand = crash_site(s, crash, V, (0, 0, 0), {}, burning=False, lying=spots)
    # The cop: out of the car, running to the drummer, kneeling beside the body.
    car_door = (-5.6, 0, -7.4)
    kneel_at = (-1.0, -0.08, DRUMMER[1] + 0.2)
    cop_run = P.figure(V, 'Cop_running', 'ShopKeeper_01', '04_B', P.FISTS, 'the cop running in')
    kneel = P.figure(V, 'Cop_kneeling', 'ShopKeeper_01', '04_B', P.KNEEL_LOOK, 'the cop kneeling by the drummer')
    run_yaw = P.yaw_to(car_door, kneel_at)
    run_clip = P.path_clip(V, 'CopRuns', [(0, 0, 0), (0, 0.12, 4.5), (0, 0, 9.0), (0, 0.12, math.dist(car_door, kneel_at))], 3.0)
    runner = P.play(s, P.between(s, crash, 'Cop until he kneels', None, 'cop_kneels', 0.2, car_door), 'Cop runs', 'cop_runs', run_clip, car_door, (0, run_yaw, 0))
    P.place(s, runner, 'Cop', cop_run, (0, 0, 0), 0)
    P.place(s, P.between(s, crash, 'Cop kneeling', 'cop_kneels', None, 0.3, kneel_at), 'Cop', kneel, kneel_at, 90)

    # 2. The fall: a shaft whose ledges stream upward past the band, ash rising, the road a slit above.
    fall = P.between(s, P.between(s, root, 'The fall', 'fell', None, 1.5), 'Falling', None, 'landed', 0.3)
    for i in range(10):
        a = 2 * math.pi * i / 10
        s.box(f'Shaft wall {i}', fall, (math.sin(a) * 16, 0, math.cos(a) * 16 + 3), (11, 200, 1.5), STONE_DARK, rot=(0, math.degrees(a), 0), rough=1.0, shadows=False)
    ledge_clip = P.clip(V, 'ShaftLedges', 20, [P.track('Position', [(0, (0, 0, 0)), (20, (0, 12, 0))])])
    ledges = P.looping(s, fall, 'Ledges', ledge_clip)
    rng = random.Random(11)
    for k in range(-8, 9):
        for i in range(4):
            a = rng.uniform(0, 2 * math.pi)
            s.box('Ledge', ledges, (math.sin(a) * 14.8, k * 12 + rng.uniform(0, 12), math.cos(a) * 14.8 + 3), (rng.uniform(1.5, 4), rng.uniform(0.4, 1.2), 1.6),
                  STONE, rot=(0, math.degrees(a), 0), shadows=False)
    ash_clip = P.clip(V, 'AshRising', 30, [P.track('Position', [(0, (0, 0, 0)), (30, (0, 10, 0))])])
    ash = P.looping(s, fall, 'Ash', ash_clip)
    for i in range(160):
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(2.5, 13)
        s.box('Ash', ash, (math.sin(a) * r, rng.uniform(-30, 30), math.cos(a) * r + 3), (0.06, 0.06, 0.06), (0.5, 0.48, 0.45),
              emissive=(0.35, 0.2, 0.15), emissive_intensity=1.5, shadows=False)
    s.box('The road, far above', fall, (0, 150, 3), (9, 0.5, 0.35), WHITE, emissive=(1, 0.95, 0.85), emissive_intensity=20, shadows=False)
    s.light('Slit light', fall, (0, 60, 3), 'Spot', (1.0, 0.95, 0.85), 30000.0, 90, rot=(90, 0, 0), inner=8, outer=20)
    s.light('Fall glow', fall, (0, -10, 3), 'Point', (1.0, 0.25, 0.05), 800.0, 30)

    # 3. Hell: the stone floor, the staircase up to the throne, the crowd pressed close on three sides.
    h = P.between(s, root, 'Hell', 'landed', None, 0.4)
    s.slab('Floor', h, -22, 22, -0.3, 0.0, -40, 14, STONE, rough=0.95)
    for x0, x1 in ((-22, -20), (20, 22)):
        s.slab('Wall', h, x0, x1, 0, 30, -40, 14, STONE_DARK)
    s.slab('Back wall', h, -22, 22, 0, 30, 12, 14, STONE_DARK)
    s.slab('Far wall', h, -22, 22, 0, 40, -42, -40, STONE_DARK)
    for x in (-18.5, 18.5):
        s.slab('Lava', h, x - 1.2, x + 1.2, -0.2, 0.05, -38, 12, LAVA, emissive=LAVA, emissive_intensity=5.0, shadows=False)
        for z in (-30, -14, 2):
            s.light('Lava glow', h, (x, 1.5, z), 'Point', (1.0, 0.3, 0.05), 500.0, 16)
    steps, rise, run, z0 = 11, 0.75, 1.5, -6.0
    for i in range(steps):
        z = z0 - i * run
        s.slab(f'Step {i}', h, -3.0, 3.0, 0, (i + 1) * rise, z - run, z, STONE)
    top_y = steps * rise
    zt = z0 - steps * run
    s.slab('Throne dais', h, -6, 6, 0, top_y, zt - 8, zt, STONE)
    s.slab('Throne seat', h, -1.2, 1.2, top_y, top_y + 0.9, zt - 4.2, zt - 2.6, (0.25, 0.03, 0.03))
    s.slab('Throne back', h, -1.4, 1.4, top_y, top_y + 6.0, zt - 4.8, zt - 4.2, (0.2, 0.02, 0.02))
    for x in (-1.3, 1.3):
        s.slab('Armrest', h, x - 0.15, x + 0.15, top_y + 0.9, top_y + 1.2, zt - 4.2, zt - 2.7, (0.3, 0.04, 0.04))
        s.box('Throne horn', h, (x * 1.15, top_y + 6.6, zt - 4.5), (0.3, 1.6, 0.3), HORN, rot=(0, 0, -x * 12), shape='Cylinder')
    s.box('Phone table', h, (2.2, top_y + 0.45, zt - 3.2), (0.6, 0.9, 0.6), STONE_DARK)
    s.box('Phone', h, (2.2, top_y + 1.0, zt - 3.2), (0.35, 0.15, 0.25), (0.6, 0.02, 0.02))
    s.light('Throne light', h, (0, top_y + 8, zt + 2), 'Spot', (1.0, 0.2, 0.08), 1500.0, 20, rot=look_rotation((0, top_y + 8, zt + 2), (0, top_y + 1.5, zt - 3.5)), inner=15, outer=30)
    for side in (-1, 1):
        for i in range(0, steps, 2):
            z = z0 - i * run - run / 2
            y = (i + 1) * rise
            s.box('Baluster', h, (side * 3.3, y + 0.5, z), (0.4, 1.0, 0.4), STONE_DARK)
    # Braziers up the stairs and round the floor, so the climb to the throne reads.
    for side in (-1, 1):
        for i in (1, 5, 9):
            at = (side * 3.3, (i + 1) * rise + 1.0, z0 - i * run - run / 2)
            s.box('Brazier', h, (at[0], at[1] + 0.3, at[2]), (0.5, 0.35, 0.5), (0.1, 0.08, 0.06), shape='Cylinder')
            s.box('Brazier flame', h, (at[0], at[1] + 0.75, at[2]), (0.35, 0.6, 0.35), FIRE, emissive=FIRE, emissive_intensity=6.0, shadows=False)
            s.light('Brazier light', h, (at[0], at[1] + 1.4, at[2]), 'Point', (1.0, 0.45, 0.15), 350.0, 12)
        s.light('Floor fill', h, (side * 7, 6, 2), 'Point', (1.0, 0.35, 0.15), 600.0, 18)
    seat = (0.0, top_y + 0.35, zt - 3.3)
    satan = {}
    for label, pose in (('Satan_throne', P.THRONE), ('Satan_beckon', P.BECKON), ('Satan_air_drums', P.AIR_DRUMS),
                        ('Satan_standing', P.STANDING_PROUD), ('Satan_phone', P.ON_THE_PHONE)):
        satan[label] = P.figure(V, label, 'Rigged', '04_A', pose, 'Satan')
    stand = (0.0, top_y, zt - 2.6)
    for label, after, before, at in (('Satan_throne', None, 'encore_called', seat), ('Satan_beckon', 'encore_called', 'satan_air_drums', seat),
                                     ('Satan_air_drums', 'satan_air_drums', 'satan_stands', seat), ('Satan_standing', 'satan_stands', 'phone_call', stand),
                                     ('Satan_phone', 'phone_call', None, stand)):
        g = P.between(s, h, label, after, before, 0.08, at)
        P.place(s, g, 'Satan', satan[label], at, 0, 1.6)
        hy = at[1] + (2.95 if at is stand else 2.25)
        for x in (-0.13, 0.13):
            s.box('Horn', g, (at[0] + x * 1.6, hy, at[2] - 0.05), (0.07, 0.3, 0.07), HORN, rot=(0, 0, -x * 160), shape='Cylinder')
        if label == 'Satan_phone':
            s.box('Receiver', g, (at[0] - 0.5, at[1] + 2.75, at[2]), (0.08, 0.32, 0.1), (0.6, 0.02, 0.02))
    # Demons on the balustrades and in the crowd, each a figure with horns.
    demon_poses = {'cheer': P.CHEER, 'fists': P.FISTS, 'stand': P.STANDING}
    bodies = (('Daughter_01', '01_C'), ('Mother_01', '03_C'), ('SchoolGirl_01', '04_A'), ('Son_01', '03_B'), ('Mother_02', '02_B'), ('SchoolBoy_01', '02_A'))
    models = {}
    for b, v in bodies:
        for k, pose in demon_poses.items():
            models[(b, k)] = P.figure(V, f'Demon_{b}_{k}', b, v, pose, 'a demon')

    throne = (0.0, top_y + 2.0, zt - 3.3)

    def demon(parent, at, yaw, b, k, turns=True):
        # Facing the band; on the encore (encore_called) each turns to the throne.
        g = s.entity('Demon', parent, at, (0, yaw, 0))
        if turns:
            g = P.play(s, g, 'Turn', 'encore_called', P.turn_clip(V, P.wrap(P.yaw_to(at, throne) - yaw), 1.2 + 0.4 * ((int(at[0] * 7) % 5) / 4.0)))
        g.add({'Type': 'Model', 'ModelPath': models[(b, k)]})
        for x in (-0.07, 0.07):
            s.box('Horn', g, (x, 1.72, 0.03), (0.04, 0.16, 0.04), HORN, rot=(0, 0, -x * 200), shape='Cylinder', shadows=False)
        return g
    rng = random.Random(23)
    for side in (-1, 1):
        for i in range(1, steps, 2):
            z = z0 - i * run - run / 2
            y = (i + 1) * rise + 1.0
            b, _ = bodies[(i + side) % len(bodies)]
            demon(h, (side * 3.3, y, z), 90 * side + 180 + rng.uniform(-30, 30), b, 'cheer' if i % 4 == 1 else 'stand')
    for i in range(44):
        side = i % 3
        if side == 0:
            at = (rng.uniform(-11, -5.5), 0, rng.uniform(-3, 7))
        elif side == 1:
            at = (rng.uniform(5.5, 11), 0, rng.uniform(-3, 7))
        else:
            at = (rng.uniform(-5, 5), 0, rng.uniform(-5.5, -2.0))
        yaw = math.degrees(math.atan2(-at[0], DRUMMER[1] - 1.5 - at[2])) + rng.uniform(-20, 20)
        b, _ = bodies[i % len(bodies)]
        demon(h, at, yaw, b, ('cheer', 'fists', 'stand')[rng.randrange(3)])
    # The demon on the steps who catches a fill.
    step3 = (1.2, 3 * rise, z0 - 2.5 * run)
    catch = P.figure(V, 'Demon_catch', 'Daughter_01', '01_C', P.CROUCH_CATCH, 'the demon catching a fill')
    look = P.figure(V, 'Demon_looks_back', 'Daughter_01', '01_C', P.TURN_BACK, 'the demon looking back at the throne')
    demon_g = P.between(s, h, 'Step demon', None, 'demon_catch', 0.2, step3)
    demon(demon_g, step3, 180, 'Daughter_01', 'stand', turns=False)
    caught = P.between(s, h, 'Step demon caught', 'demon_catch', None, 0.2, step3)
    P.place(s, caught, 'Demon catching', catch, step3, 180)
    P.place(s, P.between(s, h, 'Step demon looks', 'satan_nods', None, 0.2, (step3[0] + 0.8, step3[1], step3[2])), 'Demon looking back', look, (step3[0] + 0.8, step3[1], step3[2]), 0)
    # The smoke that lifts them out.
    smoke = P.between(s, root, 'Smoke', 'smoke_rises', None, 1.5)
    smoke_clip = P.clip(V, 'SmokeRising', 60, [P.track('Position', [(0, (0, 0, 0)), (60, (0, 8, 0))])])
    rising = P.looping(s, smoke, 'Rising', smoke_clip)
    for i in range(90):
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(0.5, 7)
        grey = 0.55 + 0.4 * rng.random()
        s.box('Smoke puff', rising, (math.sin(a) * r, rng.uniform(-6, 30), math.cos(a) * r + 3), (rng.uniform(1, 3),) * 3,
              (grey, grey, grey), emissive=(grey * 0.6,) * 3, emissive_intensity=1.0, shape='Sphere', shadows=False)
    s.light('Smoke glow', smoke, (0, 12, 3), 'Point', (1, 1, 1), 1200.0, 40)

    # Story shots.
    shot(s, marks, 'ghost_hand', (hand[0] - 0.45, 0.2, hand[2] - 0.6), (hand[0] + 0.2, 0.15, hand[2] + 0.3), 42, 7, end=((hand[0] - 0.4, 0.6, hand[2] - 0.7), (hand[0] + 0.1, 1.1, hand[2] + 0.4), 46))
    shot(s, marks, 'ghosts_stand', (9, 3.5, -10), (0, 1.0, 3.5), 50, 8, end=((11, 5.0, -13), (0, 1.0, 3.5), 56))
    shot(s, marks, 'cop_runs', (-9.0, 1.6, -2.0), car_door, 46, 3, hand=True, end=((-6.0, 1.5, 1.5), kneel_at, 50))
    shot(s, marks, 'cop_kneels', (-3.0, 1.0, DRUMMER[1] - 1.6), (-0.8, 0.7, DRUMMER[1] + 0.3), 40, 6, hand=True)
    shot(s, marks, 'fell', (1.2, 1.0, -1.5), (0, 60, 6), 72, 7, hand=True)
    shot(s, marks, 'tumbling', (-3.4, 2.2, 1.0), (-2.0, 1.6, 2.6), 46, 5, hand=True)
    shot(s, marks, 'landed', (1.1, 0.35, 2.3), (0.0, 0.4, 4.2), 48, 4)
    shot(s, marks, 'stairs_reveal', (0, 1.0, -3.5), (0, 2.5, -10), 50, 10, end=((0, top_y + 1.6, zt + 3.5), (0, top_y + 2.2, zt - 3.4), 38))
    face = (0, seat[1] + 1.95, seat[2] + 0.2)
    shot(s, marks, 'encore_called', (0.8, face[1] - 0.2, face[2] + 3.6), face, 38, 6)
    shot(s, marks, 'throne_view', (0.9, top_y + 3.4, zt - 4.0), (0, 1.2, 3), 50, 6)
    shot(s, marks, 'demon_catch', (step3[0] + 2.2, step3[1] + 1.2, step3[2] + 2.5), step3, 42, 4)
    shot(s, marks, 'satan_nods', (0, face[1], face[2] + 3.0), face, 34, 5)
    shot(s, marks, 'satan_air_drums', (2.6, face[1] - 0.6, face[2] + 2.0), (0, face[1] - 1.0, face[2]), 44, 5)
    shot(s, marks, 'satan_stands', (0, top_y + 1.0, zt + 6), (0, top_y + 2.6, zt - 2.6), 44, 5)
    shot(s, marks, 'phone_call', (1.0, top_y + 2.9, zt + 1.2), (0, top_y + 2.8, zt - 2.6), 36, 5)
    shot(s, marks, 'smoke_rises', (1.4, 0.6, 1.2), (0, 30, 4), 76, 20, hand=True)
    write(s, V, 'Hell', ambience=None)


# ---- heaven -------------------------------------------------------------------------------------
def angel(s, parent, venue, centre, scale, eyes_flag=None, name='Angel', turn_flag=None, look_at=None):
    """Interlocking rings turning about a great eye, more eyes on the rings, and banks of wings
    behind; it faces +z (the band). eyes_flag: the eyes open then. turn_flag: it turns to look at
    look_at then."""
    g = s.group(name, parent, centre)
    if turn_flag and look_at:
        flat = math.hypot(look_at[0] - centre[0], look_at[2] - centre[2])
        g = P.play(s, g, 'Turn', turn_flag, P.turn_clip(venue, P.wrap(P.yaw_to(centre, look_at)), 2.5, math.degrees(math.atan2(centre[1] - look_at[1], flat))))
    r = 3.2 * scale
    spin_a = P.clip(venue, 'RingSpinA', 900, [P.track('Rotation', [(0, (0, 0, 0)), (300, (0, 0, 120)), (600, (0, 0, 240)), (900, (0, 0, 359.9))])])
    spin_b = P.clip(venue, 'RingSpinB', 1200, [P.track('Rotation', [(0, (0, 0, 0)), (400, (0, 120, 0)), (800, (0, 240, 0)), (1200, (0, 359.9, 0))])])
    P.ring(s, P.looping(s, g, 'Ring A', spin_a), 'Ring A', (0, 0, 0), r, 28, (0.5 * scale, 0.5 * scale, 1.25 * scale), GOLD, 'z', GOLD, 2.0)
    P.ring(s, P.looping(s, g, 'Ring B', spin_b, speed=0.8), 'Ring B', (0, 0, 0), r * 0.92, 26, (0.45 * scale, 1.2 * scale, 0.45 * scale), GOLD, 'x', GOLD, 2.0)
    eyes = P.between(s, g, 'Eyes', eyes_flag, None, 2.0) if eyes_flag else g
    for i in range(8):
        a = 2 * math.pi * i / 8 + 0.2
        at = (math.cos(a) * r, math.sin(a) * r, 0.5 * scale)
        s.box('Eye', eyes, at, (0.7 * scale,) * 3, WHITE, emissive=WHITE, emissive_intensity=1.5, shape='Sphere', shadows=False)
        s.box('Pupil', eyes, (at[0], at[1], at[2] + 0.3 * scale), (0.3 * scale,) * 3, (0.02, 0.02, 0.05), shape='Sphere', shadows=False)
    s.box('Heart eye', eyes, (0, 0, 0), (1.6 * scale,) * 3, WHITE, emissive=(1, 0.95, 0.8), emissive_intensity=3.0, shape='Sphere', shadows=False)
    s.box('Heart pupil', eyes, (0, 0, 0.7 * scale), (0.6 * scale,) * 3, (0.02, 0.02, 0.05), shape='Sphere', shadows=False)
    beat = P.clip(venue, 'WingBeat', 120, [P.track('Scale', [(0, (1, 1, 1)), (60, (1.06, 1.12, 1)), (120, (1, 1, 1))], 'SmoothStep')])
    wings = P.looping(s, g, 'Wings', beat, speed=0.7 + 0.1 * (int(centre[0]) % 3))
    for side in (-1, 1):
        for i in range(5):
            ang = -50 + i * 25
            s.box('Wing', wings, (side * (r + 1.5 * scale), (i - 2) * 1.2 * scale, -1.2 * scale), (5.5 * scale, 0.9 * scale, 0.15 * scale), WHITE,
                  rot=(0, side * 15, side * ang), emissive=(0.8, 0.82, 0.9), emissive_intensity=0.8, shadows=False)
    return g


def heaven():
    V = 'StoryHeaven'
    s = Scene(seed=6603)
    root = s.group('Highway to the Afterlife: heaven')
    marks = s.group('Markers', root)
    s.info(marks, 'Heaven', 'Drumsmith', outdoor=False, half_width=60, desk_z=-20,
           ambient=(0.62, 0.7, 0.86), fog_color=(0.5, 0.55, 0.65), haze=0.35)
    band(s, marks, 0.0)
    s.camera_spot('Camera Wide', marks, (0, 6, -16), (0, 2, 3), 'Wide', 55)
    s.camera_spot('Camera Crane', marks, (-8, 9, -12), (0, 2, 3), 'Crane', 55)
    s.camera_spot('Camera Desk', marks, (2, 2.5, -12), (0, 2, 4), 'Desk', 30)
    s.light('Sun', marks, (0, 80, -40), 'Directional', (1.0, 0.95, 0.85), 2.5, 400, rot=(55, 160, 0), shadows=True, show='Static')
    for i, x in enumerate((-3.5, 3.5, -1.2, 1.2)):
        s.light(f'Wash {i}', marks, (x, 8, -2), 'Spot', (1.0, 0.92, 0.75), 1200.0, 18, rot=look_rotation((x, 8, -2), (x * 0.4, 1, 3.5)), inner=22, outer=42, show='Wash', group=i)
    rng = random.Random(31)

    # The ascent: clouds streaming down past them, the cloud sea and the horizon far below.
    up = P.between(s, root, 'The ascent', None, 'touchdown', 1.2)
    period = 30.0
    cloud_clip = P.clip(V, 'CloudsFalling', 150, [P.track('Position', [(0, (0, 0, 0)), (150, (0, -period, 0))])])
    clouds = P.looping(s, up, 'Clouds', cloud_clip)
    layout = [(rng.uniform(0, 2 * math.pi), rng.uniform(5, 40), rng.uniform(0, period), rng.uniform(3, 9)) for _ in range(40)]
    for copy in (-1, 0, 1, 2):
        for a, r, y, size in layout:
            s.box('Cloud', clouds, (math.sin(a) * r, y + copy * period, math.cos(a) * r + 3), (size * 1.6, size * 0.6, size * 1.2), CLOUD,
                  emissive=(0.7, 0.72, 0.8), emissive_intensity=0.7, shape='Sphere', shadows=False)
    s.slab('Cloud sea', up, -400, 400, -62, -60, -400, 400, CLOUD, emissive=(0.75, 0.78, 0.85), emissive_intensity=0.8, shadows=False)
    s.slab('Horizon', up, -400, 400, -60, -57, -402, -398, GOLD, emissive=GOLD, emissive_intensity=3.0, shadows=False)

    # The floor of cloud, the stairs and God's platform.
    floor = P.between(s, root, 'The floor', 'touchdown', None, 1.0)
    for i in range(70):
        a, r = rng.uniform(0, 2 * math.pi), math.sqrt(rng.random()) * 30
        size = rng.uniform(3, 7)
        s.box('Cloud floor', floor, (math.sin(a) * r, -0.6 - rng.uniform(0, 0.6), math.cos(a) * r - 4), (size * 1.5, 1.4, size * 1.3), CLOUD,
              emissive=(0.75, 0.77, 0.85), emissive_intensity=0.6, shape='Sphere', shadows=False)
    s.slab('Kit pad', floor, -3.5, 3.5, -0.25, -0.02, 0.0, 7.0, (0.92, 0.93, 0.97), rough=0.15, metallic=0.2)
    steps, rise, run, z0 = 14, 0.75, 1.4, -6.0
    for i in range(steps):
        z = z0 - i * run
        s.slab(f'Step {i}', floor, -4.5, 4.5, 0, (i + 1) * rise, z - run, z, (0.96, 0.95, 0.9), emissive=(0.3, 0.3, 0.28), emissive_intensity=0.6)
    top_y = steps * rise
    zt = z0 - steps * run
    s.slab('Platform', floor, -8, 8, 0, top_y, zt - 10, zt, (0.98, 0.96, 0.9), emissive=(0.35, 0.33, 0.3), emissive_intensity=0.6)
    for x in (-7, -3.5, 3.5, 7):
        s.box('Pillar', floor, (x, top_y + 4, zt - 9), (0.9, 8, 0.9), (0.98, 0.97, 0.92), shape='Cylinder')
    # God: on the platform until the final chorus, then down the stairs to the band's level.
    god_robe = P.figure(V, 'God', 'Rigged', '01_C', P.ROBED, 'God')
    god_at = (0.0, top_y, zt - 5)
    walk = [(0, 0, 0), (0, 0.15, 2.5), (0, 0, 5.3)]
    for i in range(steps):
        walk.append((0, -(i + 1) * rise + (0.12 if i % 2 else 0), 5.3 + (i + 1) * run))
    walk.append((0, -top_y, -4.5 - god_at[2]))
    descend = P.path_clip(V, 'GodDescends', walk, 9.0)
    god = P.play(s, floor, 'God descends', 'god_descends', descend, god_at)
    P.place(s, god, 'God', god_robe, (0, 0, 0), 0, 2.0)
    s.box('Robe', god, (0, 0.9, 0), (1.3, 1.8, 1.0), (1, 1, 1), emissive=(0.9, 0.9, 0.85), emissive_intensity=1.2, shape='Cylinder', shadows=False)
    P.ring(s, god, 'Halo', (0, 4.1, -0.4), 0.7, 16, (0.12, 0.12, 0.2), GOLD, 'z', GOLD, 5.0)
    s.light('God light', god, (0, 6, 3), 'Point', (1, 0.95, 0.8), 500.0, 14)
    # The arch: the central angel, there from the touchdown, its eyes opening with the choir and
    # turning to the drummer as the song resolves.
    drummer_head = (DRUMMER[0], 1.3, DRUMMER[1])
    angel(s, floor, V, (0, top_y + 16, zt - 22), 3.0, 'choir', 'Arch angel', 'angels_turn', drummer_head)

    # The choir: angels in an arc round and above the platform; two in front, wings closed,
    # part to show the crash site.
    choir = P.between(s, root, 'The choir', 'choir', None, 3.0, (0, top_y + 10, zt - 20))
    for i, (x, y, z, sc) in enumerate(((-34, 24, -50, 2.6), (34, 24, -50, 2.6), (-56, 34, -38, 2.2), (56, 34, -38, 2.2), (-22, 42, -62, 2.0), (22, 42, -62, 2.0), (0, 52, -70, 2.4))):
        angel(s, choir, V, (x, y, z), sc, None, f'Angel {i}', 'angels_turn', drummer_head)
    # Two banks of wings close in front of the platform's back; on angels_part they fold aside.
    for side in (-1, 1):
        fold = P.clip(V, f'WingsPart{"L" if side < 0 else "R"}', 75, [P.track('Position', [(0, (0, 0, 0)), (75, (side * 9.0, 0.5, 1.5))], 'SmoothStep'),
                                                                   P.track('Rotation', [(0, (0, 0, 0)), (75, (0, side * 30, -side * 12))], 'SmoothStep')])
        bank = P.play(s, choir, 'Wings ' + ('left' if side < 0 else 'right'), 'angels_part', fold, (side * 4.0, top_y + 4, zt - 14))
        for i in range(6):
            s.box('Wing', bank, (side * 0.5, i * 2.2, 0), (8.5, 1.8, 0.3), WHITE, rot=(0, 0, -side * (8 + i * 4)),
                  emissive=(0.85, 0.86, 0.92), emissive_intensity=0.9, shadows=False)
    opened = P.between(s, choir, 'The way home', 'angels_part', None, 1.5)
    window = (0, top_y + 7, zt - 16)
    # Through the opening: the night on the shoulder, the fire and the red and blue lights.
    s.box('The way home', opened, window, (10, 8, 0.2), (0.01, 0.015, 0.04), emissive=(0.02, 0.035, 0.12), emissive_intensity=1.0, shadows=False)
    s.box('The road', opened, (window[0], window[1] - 3.2, window[2] + 0.15), (10, 1.2, 0.05), (0.05, 0.05, 0.06), shadows=False)
    for i, (c, x, size) in enumerate((((1, 0.45, 0.08), 1.6, 1.1), ((1, 0.08, 0.05), -1.8, 0.45), ((0.1, 0.25, 1), -1.1, 0.45), ((1, 0.9, 0.7), 3.2, 0.25))):
        s.box('Far light', opened, (window[0] + x, window[1] - 2.4, window[2] + 0.2), (size, size, 0.1), c, emissive=c, emissive_intensity=10.0, shape='Sphere', shadows=False)
    s.light('Choir light', choir, (0, top_y + 30, zt - 10), 'Point', (1, 0.9, 0.7), 5000.0, 90)
    turn = P.between(s, root, 'Angels gaze', 'angels_turn', None, 2.0, (0, top_y + 16, zt - 22))
    s.light('Gaze', turn, (0, top_y + 14, zt - 18), 'Spot', (1, 0.95, 0.75), 6000.0, 80, rot=look_rotation((0, top_y + 14, zt - 18), (0, 1.2, 5.2)), inner=6, outer=14)

    # Earth, far off in the same scene: the crash site at night, the rescue.
    E = (400.0, 0.0, 0.0)
    earth_root = s.group('Earth', root)
    sky_dome(s, earth_root, (E[0], 0, E[2] + 4), 40)
    # Slow motion (the fire, the lights, the compressions) until the drummer wakes.
    earth = P.slow_motion(s, earth_root, 'Slow motion', 'resurrection', 0.25)
    asphalt(s, earth, E[0] - 14, E[0] + 14, E[2] - 30, E[2] + 30)
    s.slab('Shoulder', earth, E[0] + 14, E[0] + 38, -0.25, -0.02, E[2] - 30, E[2] + 30, GRAVEL)
    s.box('Mile marker', earth, (E[0] + 15, 0.7, E[2] + 16), (0.3, 1.4, 0.08), (0.1, 0.4, 0.15))
    cruiser(s, earth, V, (E[0] - 7.5, 0, E[2] - 9), 20)
    hand = crash_site(s, earth, V, (E[0], 0, E[2] + 6), {'wake': 'resurrection', 'cop': None, 'nod': 'cop_nod_final'}, cop=(-1.65, 100, 0), ems=True)
    cop_eye = (E[0] - 1.65, 1.0, E[2] + 6)
    s.light('Earth moon', earth, (E[0], 30, E[2] - 10), 'Spot', (0.45, 0.5, 0.7), 4000.0, 60, rot=(80, 0, 0), inner=30, outer=60)

    # Story shots.
    face = (DRUMMER[0], 1.32, DRUMMER[1] - 0.1)
    shot(s, marks, 'ascent', (face[0] + 0.42, face[1] + 0.02, face[2] - 0.05), (face[0] - 0.6, face[1] - 0.05, face[2] - 0.2), 40, 12, end=((face[0] + 0.7, face[1] + 0.1, face[2] - 0.3), (face[0] - 0.6, face[1], face[2] - 0.3), 44))
    shot(s, marks, 'eyes_meet', (BASS[0] + 0.7, 1.75, BASS[1] - 0.9), (BASS[0] - 0.2, 1.65, BASS[1] + 0.3), 38, 6)
    shot(s, marks, 'horizon', (-6, 3, -6), (0, -12, -80), 60, 8, end=((-8, 4, -9), (0, -10, -80), 66))
    shot(s, marks, 'touchdown', (face[0] + 0.6, face[1] + 0.1, face[2] - 0.4), face, 44, 6, end=((7, 5, -10), (0, 1, 3), 55))
    shot(s, marks, 'choir', (0, 1.5, -3), (0, top_y + 14, zt - 24), 50, 10, end=((0, 4, 16), (0, top_y + 14, zt - 24), 78))
    shot(s, marks, 'angels_turn', (0, 5, -6), (0, top_y + 16, zt - 22), 46, 5)
    shot(s, marks, 'sticks_close', (0.45, 1.05, DRUMMER[1] - 1.9), (0.0, 0.85, DRUMMER[1] - 1.4), 40, 20)
    shot(s, marks, 'drum_open', (0.9, 1.5, DRUMMER[1] - 2.0), (0, 1.1, DRUMMER[1] - 0.6), 40, 6)
    shot(s, marks, 'cpr', (cop_eye[0] + 1.3, 0.8, cop_eye[2] - 0.9), (cop_eye[0] + 0.1, 0.65, cop_eye[2]), 40, 7, hand=True)
    shot(s, marks, 'earth_wide', (E[0] - 5.0, 1.5, E[2] - 3.0), (E[0] + 1.5, 0.6, E[2] + 8), 52, 6, end=((E[0] - 4.0, 1.4, E[2] - 2.0), (E[0] + 1.5, 0.6, E[2] + 8), 46))
    shot(s, marks, 'cpr_close', (cop_eye[0] + 0.9, 1.1, cop_eye[2] + 0.5), (cop_eye[0] + 0.4, 0.5, cop_eye[2] - 0.1), 34, 4)
    shot(s, marks, 'god_descends', (9, 4, -2), (0, 4, -10), 54, 6, end=((8, 2.5, 0), (0, 2.5, -5), 50))
    shot(s, marks, 'angels_part', (0, 3, 7), window, 50, 6, end=((0, 4, 4), window, 30))
    shot(s, marks, 'resurrection', (hand[0] - 0.3, 0.45, hand[2] - 0.9), (hand[0] + 0.6, 0.15, hand[2] + 0.6), 42, 8)
    shot(s, marks, 'cop_nod_final', (cop_eye[0] - 1.6, 1.1, cop_eye[2] - 1.2), (cop_eye[0], 0.95, cop_eye[2]), 36, 30)
    write(s, V, 'Heaven')


def main():
    highway()
    hell()
    heaven()
    return 0


if __name__ == '__main__':
    sys.exit(main())
