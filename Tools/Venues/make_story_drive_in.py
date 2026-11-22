#!/usr/bin/env python3
"""Writes Assets/Venues/StoryDriveIn/: story set 09, "Midnight at the FM Drive In".

    python3 -B Tools/Venues/make_story_drive_in.py [--textures]

A gravel lot terraced down toward a forty-foot screen at midnight. The band plays on a plywood
deck built against the projection booth in the middle of the lot: the drummer on a hybrid kit, the
festival's electronic artist at the Keys spot. The festival sends the set out over FM, so the
screen shows the station card until the last song puts the live kit feed up there.

Story flags (Design/Story-Mode-Setlists.json, s09-drive-in):
  headlights_on      every car's headlights, beams and tail lights come on together
  quilt_at_hatch     the pair under the quilt in the backwards hatchback; the pickup's cargo lamp, the thermos
  quilt_on_roof      the quilt moves to the hatchback's roof; the pair dance in the gravel and on the screen
  shadows_on_screen  a patch of dancers in the projector beam; their raised arms on the screen
  hands_on_screen    the station card rolls away to the live kit feed; forty-foot sticks cross it

Deterministic: rerun = same bytes. Pictures: story_drive_in_textures.py (run with --textures).
Props: story_drive_in_meshes.py (OBJs on one palette texture).
"""
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
from venuegen import Scene, look_rotation, repo_root, vec, _r, write_venue_json  # noqa: E402
import story_drive_in_meshes as M  # noqa: E402

ID = 'StoryDriveIn'
TEX = 'Assets/Venues/StoryDriveIn/Textures/'
VM = 'Assets/Models/Venue/'
BY = 'Assets/Venues/Backyard/Models/'
PEOPLE = 'Assets/Models/People/Crowd/'
MOTION = 'Assets/Venues/StoryDriveIn/Motion/'

AMBER = (1.0, .62, .25); WARM = (1.0, .78, .52); ICE = (.35, .75, 1.0); PINK = (1.0, .12, .55)
CYAN = (.1, .85, 1.0); VIOLET = (.55, .25, 1.0); RED = (1.0, .1, .06); HEAD = (1.0, .93, .78)

# Ground: terraces stepping down toward the screen (+z). (z_back, z_front, y)
TERRACES = [(-60, -33, 2.0), (-33, -24.5, 1.5), (-24.5, -16, 1.0), (-16, -7.5, .5), (-7.5, 11, 0.0),
            (11, 19, -.4), (19, 27, -.8), (27, 70, -1.2)]
SCREEN_Z = 40.0
SCREEN_W, SCREEN_H, SCREEN_BOTTOM = 46.0, 19.6, 6.0
SCREEN_C = (0.0, SCREEN_BOTTOM + SCREEN_H / 2, SCREEN_Z)
DECK_Y = 1.0
DRUMMER = (0.8, DECK_Y, 3.3)
KEYS = (-4.0, DECK_Y, 2.2)
PORT = (0.0, 3.35, 11.25)


def ground_y(z):
    for z0, z1, y in TERRACES:
        if z0 <= z < z1:
            return y
    return TERRACES[-1][2]


# ---- material helpers -------------------------------------------------------------------------

def mat(e):
    for c in e.components:
        if c.get('Type') == 'Mesh':
            return c['Material']


def textured(e, name, tile=(1, 1), glow=0.0):
    m = mat(e)
    m['DiffuseColor'] = [1.0, 1.0, 1.0]
    m['Textures'] = {'Diffuse': {'Path': TEX + name + '.png'}}
    if glow:
        m['Textures']['Emissive'] = {'Path': TEX + name + '.png'}
        m['EmissiveColor'] = [1.0, 1.0, 1.0]
        m['EmissiveIntensity'] = _r(glow)
    m['Tiling'] = [_r(tile[0]), _r(-tile[1])]
    m['Offset'] = [0.0, _r(tile[1])]
    return e


def glow(s, name, parent, pos, size, colour, power, shape='Cube', rot=(0, 0, 0)):
    return s.box(name, parent, pos, size, colour, rot=rot, emissive=colour, emissive_intensity=power, shadows=False, shape=shape)


def additive(s, name, parent, model, pos, rot, scale, colour, power):
    """A light shaft: the unit frustum with an additive, unlit, see-through material."""
    e = s.entity(name, parent, pos, rot, scale)
    part = {'CastShadows': False, 'Material': {'Type': 'StandardMaterial', 'RenderMode': 1, 'BlendMode': 2, 'FaceMode': 0,
            'DiffuseColor': [0.0, 0.0, 0.0], 'Roughness': 1.0, 'Opacity': 1.0,
            'EmissiveColor': vec(colour), 'EmissiveIntensity': _r(power)}}
    name_ = os.path.basename(model)
    e.add({'Type': 'Model', 'ModelPath': model, 'Compact': True,
           'Parts': {f'{name_}#0/{name_[:-4]}#0/@#0': part}})
    return e


def shaft(s, name, parent, model, a, b, half_w, half_h, colour, power):
    L = math.dist(a, b)
    return additive(s, name, parent, model, a, look_rotation(a, b), (half_w, half_h, L), colour, power)


def bar(s, name, parent, a, b, w, colour, **kw):
    L = math.dist(a, b)
    c = tuple((a[i] + b[i]) / 2 for i in range(3))
    return s.box(name, parent, c, (w, w, L), colour, rot=look_rotation(a, b), **kw)


def world(s, group, pivot):
    """A child of a story group that cancels its pivot, so props under it are placed in venue space."""
    return s.entity('(venue frame)', group, tuple(-v for v in pivot))


def seq(entity, clip, bindings, speed=1.0):
    entity.add({'Type': 'Sequence', 'Clip': MOTION + clip + '.sequence', 'PlayOnStart': True, 'Loop': True,
                'Speed': _r(speed), 'Bindings': [{'Slot': k, 'Target': v.guid} for k, v in bindings.items()]})


def quat(rot):
    x, y, z = [math.radians(a) / 2 for a in rot]
    a, b = math.sin(x), math.cos(x); c, d = math.sin(y), math.cos(y); e, f = math.sin(z), math.cos(z)
    return [round(v, 6) for v in (a*d*f - b*c*e, b*c*f + a*d*e, b*d*e - a*c*f, b*d*f + a*c*e)]


def write_clips():
    folder = M.VENUE / 'Motion'
    folder.mkdir(parents=True, exist_ok=True)

    def clip(name, frames, tracks):
        data = {'Version': 1, 'Name': name, 'FrameRate': 30, 'DurationFrames': frames, 'Tracks': tracks}
        M.save(folder / (name + '.sequence'), json.dumps(data, indent=1) + '\n')

    def pos_track(slot, keys):
        return {'Binding': slot, 'Component': 'Transform', 'Property': 'Position',
                'Keys': [{'Frame': f, 'Value': [*p, 0], 'Interpolation': 'SmoothStep'} for f, p in keys]}

    def rot_track(slot, keys):
        return {'Binding': slot, 'Component': 'Transform', 'Property': 'Rotation',
                'Keys': [{'Frame': f, 'Value': quat(r), 'Interpolation': 'SmoothStep'} for f, r in keys]}
    # A jump on the beat at ~128 bpm: up, land, settle.
    clip('Bounce', 28, [pos_track('Body', [(0, (0, 0, 0)), (8, (0, .22, 0)), (14, (0, 0, 0)), (28, (0, 0, 0))])])
    # Shadows on the screen bob bigger and slower (they're forty feet tall).
    clip('ShadowBob', 28, [pos_track('Body', [(0, (0, 0, 0)), (9, (0, .9, 0)), (16, (0, -.1, 0)), (28, (0, 0, 0))])])
    # The two shadows cross the bottom of the screen, bouncing; 24 s each way.
    keys = []
    for i in range(0, 25):
        t = i / 24
        x = -19 + 38 * (t * 2 if t <= .5 else 2 - t * 2)
        keys.append((i * 30, (x, .5 if i % 2 else 0, 0)))
    clip('ShadowCross', 720, [pos_track('Body', keys)])
    # Arms pumping (rotation about z of a raised arm).
    clip('Pump', 28, [rot_track('Left', [(0, (0, 0, -150)), (9, (0, 0, -168)), (28, (0, 0, -150))]),
                      rot_track('Right', [(0, (0, 0, 150)), (9, (0, 0, 168)), (28, (0, 0, 150))])])
    # The giant sticks: a stroke every beat.
    clip('Stroke', 28, [rot_track('Stick', [(0, (0, 0, 0)), (7, (0, 0, -7)), (14, (0, 0, 0)), (28, (0, 0, 0))])])


# ---- people -----------------------------------------------------------------------------------

def person(s, parent, label, who, pos, yaw=0.0, pose='stand', bounce=None, pump=False, scale=1.0):
    """A crowd figure from the rigid pieces (Assets/Models/People/Crowd/<who>/). pose: stand |
    arms_up | seated (Backyard's bent legs) | wave. bounce: a speed for the Bounce clip."""
    root = s.entity(label, parent, pos, (0, yaw, 0), (scale,) * 3)
    body = s.entity('Body', root) if bounce else root
    seated = pose == 'seated'
    legs = BY + f'{who}_Legs_79.obj' if seated else PEOPLE + f'{who}/Legs.obj'
    s.entity('Legs', body).add({'Type': 'Model', 'ModelPath': legs})
    torso = s.entity('Torso', body, (0, .57 if seated else .8763, 0), (-4 if seated else 0, 0, 0))
    torso.add({'Type': 'Model', 'ModelPath': PEOPLE + f'{who}/Torso.obj'})
    s.entity('Head', torso, (0, .5727, -.0242)).add({'Type': 'Model', 'ModelPath': PEOPLE + f'{who}/Head.obj'})
    arm_rot = {'stand': ((4, 0, -6), (4, 0, 6)), 'arms_up': ((0, 0, -150), (0, 0, 150)),
               'seated': ((-38, 0, -8), (-38, 0, 8)), 'wave': ((4, 0, -6), (0, 0, 160))}[pose]
    arms = []
    for i, (part, side) in enumerate((('ArmL', -1), ('ArmR', 1))):
        a = s.entity(part, torso, (side * .191, .5141, -.0484), arm_rot[i])
        a.add({'Type': 'Model', 'ModelPath': PEOPLE + f'{who}/{part}.obj'})
        arms.append(a)
    if bounce:
        seq(root, 'Bounce', {'Body': body}, bounce)
    if pump:
        seq(torso, 'Pump', {'Left': arms[0], 'Right': arms[1]}, bounce or 1.0)
    return root


def silhouette(s, parent, label, pos, height, arms='up', lean=0.0, clip='ShadowBob', speed=1.0):
    """A shadow on the screen: flat black primitives (head, shoulders, raised arms) a hair in
    front of the picture. pos is the foot of the figure on the screen plane; height in metres."""
    root = s.entity(label, parent, pos, (0, 0, lean))
    body = s.entity('Body', root)
    k = height / 1.8
    ink = (.004, .004, .006)
    flat = .04
    s.box('Shoulders', body, (0, 1.08 * k, 0), (.6 * k, .9 * k, flat), ink, rough=1, shadows=False, shape='Capsule')
    s.box('Chest', body, (0, .85 * k, 0), (.5 * k, .5 * k, flat), ink, rough=1, shadows=False)
    s.box('Head', body, (0, 1.62 * k, 0), (.36 * k, .44 * k, flat), ink, rough=1, shadows=False, shape='Sphere')
    s.box('Neck', body, (0, 1.42 * k, 0), (.2 * k, .2 * k, flat), ink, rough=1, shadows=False)
    angles = {'up': (24, -24), 'one': (160, -18), 'v': (52, -52)}[arms]
    for side, ang in zip((-1, 1), angles):
        r = math.radians(ang)
        sx, sy = side * .24 * k, 1.36 * k
        L = .95 * k
        d = (-math.sin(r), math.cos(r))
        s.box('Arm', body, (sx + d[0] * L / 2, sy + d[1] * L / 2, 0), (.16 * k, L, flat), ink, rot=(0, 0, ang), rough=1, shadows=False, shape='Capsule')
        hx, hy = sx + d[0] * L, sy + d[1] * L
        s.box('Hand', body, (hx, hy, 0), (.17 * k, .2 * k, flat), ink, rough=1, shadows=False, shape='Sphere')
    seq(root, clip, {'Body': body}, speed)
    return root


# ---- the lot ----------------------------------------------------------------------------------

def build_ground(s, parent):
    for i, (z0, z1, y) in enumerate(TERRACES):
        lower = i + 1 < len(TERRACES)
        zf = z1 - .8 if lower else z1
        e = s.slab(f'Gravel terrace {i + 1}', parent, -70, 70, y - 1.2, y, z0, zf, (.55, .52, .46), rough=1)
        textured(e, 'Gravel', ((140) / 6, (zf - z0) / 6))
        mat(e)['DiffuseColor'] = [.62, .6, .55]
        if lower:
            y2 = TERRACES[i + 1][2]
            drop = y - y2
            L = math.hypot(1.6, drop)
            ang = math.degrees(math.atan2(drop, 1.6))
            r = s.box(f'Ramp {i + 1}', parent, (0, (y + y2) / 2 - .5, z1), (140, 1.0, L), (.5, .48, .43), rot=(ang, 0, 0), rough=1)
            textured(r, 'Gravel', (140 / 6, .3))
            mat(r)['DiffuseColor'] = [.58, .56, .51]
    # Grass verges and the dark beyond the lot.
    s.slab('Field beyond', parent, -400, 400, -3.6, -1.6, -400, 400, (.03, .045, .03), rough=1)


def build_cars(s, parent, lamps, rng):
    """Rows of parked cars facing the screen. Returns where the cars stand for the crowd and posts."""
    shapes = ['Hatch', 'Sedan', 'Sedan', 'Wagon', 'Pickup', 'Van', 'Hatch', 'Wagon']
    cars = []
    rows = [  # (z, y, xs, label)
        (-36.2, 2.0, [-19.8, -16.0, -12.2, -8.4, -4.6, 4.6, 8.4, 12.2, 16.0], 'Row D'),
        (-27.7, 1.5, [-19.8, -16.0, -12.2, -8.4, -4.6, 4.6, 8.4, 12.2, 16.0, 19.8], 'Row C'),
        (-19.2, 1.0, [-19.8, -16.0, -12.2, -8.4, -4.6, 4.6, 8.4, 12.2, 16.0, 19.8], 'Row B'),
        (-11.0, .5, [-19.8, -16.0, -12.2, -8.4, -4.6, 4.6, 8.4, 12.2, 16.0, 19.8], 'Row A'),
        (16.0, -.4, [-19.8, -16.0, -12.2, -8.4, -4.6, 4.6, 8.4, 12.2, 16.0, 19.8], 'Front 1'),
        (24.0, -.8, [-19.8, -16.0, -12.2, -8.4, -4.6, 4.6, 8.4, 12.2, 16.0, 19.8], 'Front 2'),
        (32.0, -1.2, [-16.0, -12.2, -8.4, -4.6, 4.6, 8.4, 12.2, 16.0], 'Front 3'),
    ]
    special = {('Row A', -8.4): 'hatch', ('Row A', -12.2): 'pickup', ('Row D', -12.2): 'skip'}
    beams = M.beam()
    for z, y, xs, label in rows:
        group = s.group(label, parent)
        for x in xs:
            kind = special.get((label, x))
            if kind == 'skip':
                continue
            if kind == 'hatch':
                shape, paint, yaw = 'Hatch', 'teal', 180.0
            elif kind == 'pickup':
                shape, paint, yaw = 'Pickup', 'rust', 0.0
            else:
                shape = rng.choice(shapes)
                paint = rng.choice(M.PAINTS)
                yaw = rng.uniform(-3, 3)
            path, S = M.car(shape, paint, hatch_open=(kind == 'hatch'))
            jz = rng.uniform(-.35, .35) if not kind else 0
            pos = (x + rng.uniform(-.2, .2) if not kind else x, y, z + jz)
            name = f'{label} {shape.lower()} at {x:+.1f}' + (' (backed in, hatch up)' if kind == 'hatch' else '')
            car = s.prop(name, group, path, pos, yaw)
            cars.append(dict(pos=pos, yaw=yaw, shape=shape, S=S, label=label, kind=kind, entity=car))
    # Headlights: every car's lamps, beams and tail lights come on together.
    head = s.story('Headlights on (the hillside comes on together)', lamps, 'headlights_on', True, .35)
    for i, c in enumerate(cars):
        S = c['S']; x, y, z = c['pos']; yaw = c['yaw']
        g = s.entity(f'Lamps {c["label"]} {x:+.1f}', head, c['pos'], (0, yaw, 0))
        hz, hy, hx = S['head']; tz, ty, tx = S['tail']
        for sx in (-1, 1):
            glow(s, 'Headlamp', g, (sx * hx, hy, hz + .035), (.34, .16, .02), HEAD, 9.0)
            glow(s, 'Tail lamp', g, (sx * tx, ty, tz - .035), (.3, .14, .02), RED, 5.0)
        # The beam pair as one shaft, dipped toward the gravel.
        a = (0, hy, hz + .05)
        b = (0, hy - .9, hz + 9.0)
        e = additive(s, 'Low beams', g, beams, a, look_rotation(a, b), (1.25, .38, math.dist(a, b)), (1.0, .9, .7), .055)
        if i % 2 == 0 or c['kind'] == 'hatch':
            s.light('Headlight throw', g, (0, hy + .1, hz + .2), 'Spot', (1, .88, .7), 260.0, 16,
                    rot=look_rotation((0, hy, 0), (0, -.4, 7)), inner=18, outer=34)
    return cars


def build_posts(s, parent, cars):
    post = M.speaker_post()
    g = s.group('Speaker posts', parent)
    rows = {}
    for c in cars:
        rows.setdefault(c['label'], []).append(c)
    for label, cs in rows.items():
        cs.sort(key=lambda c: c['pos'][0])
        for a, b in zip(cs, cs[1:]):
            if b['pos'][0] - a['pos'][0] > 5:
                continue
            x = (a['pos'][0] + b['pos'][0]) / 2
            s.prop('Speaker post', g, post, (x, a['pos'][1], a['pos'][2] + .7), 0)


# ---- the booth and the deck --------------------------------------------------------------------

def build_booth(s, parent, story_root):
    g = s.group('Projection booth', parent)
    BLOCK = (.62, .6, .56)
    # Walls (cinder block) with the door and window openings faked by insets.
    walls = [('Front wall', -6.5, 6.5, 0, 4.2, 4.5, 4.8), ('Back wall', -6.5, 6.5, 0, 4.2, 10.7, 11.0),
             ('Left wall', -6.5, -6.2, 0, 4.2, 4.5, 11.0), ('Right wall', 6.2, 6.5, 0, 4.2, 4.5, 11.0)]
    for n, x0, x1, y0, y1, z0, z1 in walls:
        e = s.slab(n, g, x0, x1, y0, y1, z0, z1, BLOCK, rough=.95)
        textured(e, 'Block', (max(x1 - x0, z1 - z0) / 2.6, (y1 - y0) / 2.6))
        mat(e)['DiffuseColor'] = list(BLOCK)
    s.slab('Roof slab', g, -6.8, 6.8, 4.2, 4.45, 4.2, 11.3, (.2, .2, .2))
    s.slab('Parapet front', g, -6.8, 6.8, 4.45, 4.85, 4.2, 4.42, (.78, .74, .66))
    s.slab('Parapet back', g, -6.8, 6.8, 4.45, 4.85, 11.08, 11.3, (.78, .74, .66))
    s.slab('Trim stripe', g, -6.55, 6.55, 3.55, 3.85, 4.42, 4.5, (.62, .1, .1))
    # Behind the band: the open door (warm inside) and the projection-room window.
    glow(s, 'Door, propped open', g, (-1.6, 1.0 + 1.05, 4.44), (1.0, 2.1, .04), (1.0, .6, .3), 1.4)
    s.slab('Door leaf', g, -2.55, -2.1, 1.0, 3.12, 3.6, 4.44, (.42, .1, .1))
    glow(s, 'Projection room window', g, (3.6, 2.75, 4.44), (2.6, 1.0, .04), (1.0, .72, .42), 1.8)
    for x in (2.75, 3.6, 4.45):
        s.box('Mullion', g, (x, 2.75, 4.41), (.06, 1.0, .05), (.15, .14, .13))
    # The back: two projection ports facing the screen, and the projector inside one.
    for x in (-.8, .8):
        glow(s, 'Projection port', g, (x, PORT[1], 11.02), (.5, .38, .04), (.9, .95, 1.0), 6.0)
    s.prop('Projector', g, M.booth_details(), (.8, 1.65, 10.0), 0)
    s.light('Booth practical (inside)', g, (2.5, 3.2, 6.5), 'Point', (1, .7, .45), 45, 6)
    s.light('Door spill', g, (-1.6, 2.4, 3.9), 'Point', (1, .62, .35), 22, 4.5)
    # Concession counter on the left wall side facing the crowd's flank.
    glow(s, 'Concession hatch', g, (-6.52, 2.1, 7.6), (.04, 1.0, 2.6), (1.0, .82, .55), 1.3)
    s.slab('Counter', g, -7.1, -6.5, 1.05, 1.15, 6.2, 9.0, (.75, .72, .66))
    # The marquee over the deck, on two posts above the parapet.
    sign = s.box('FM Drive In marquee', g, (0, 6.15, 4.3), (8.4, 2.6, .18), (1, 1, 1), shadows=False)
    textured(sign, 'Marquee', glow=1.6)
    for x in (-3.3, 3.3):
        s.box('Marquee post', g, (x, 4.9, 4.45), (.14, 1.1, .14), (.18, .18, .2))
    s.slab('Marquee cap', g, -4.35, 4.35, 7.45, 7.6, 4.15, 4.45, (.55, .08, .08))
    s.light('Marquee glow', g, (0, 6.0, 3.0), 'Point', (1, .55, .3), 60, 9)
    # The FM transmitter mast and its aircraft light.
    s.prop('FM mast', g, M.fm_mast(15.0), (4.8, 4.45, 9.0), 30)
    glow(s, 'Mast beacon', g, (4.8, 20.15, 9.0), (.3, .3, .3), RED, 6.0, 'Sphere')
    s.light('Mast beacon glow', g, (4.8, 20.0, 9.0), 'Point', RED, 40, 7)
    s.prop('Uplink dish', g, VM + 'FloodLight.obj', (-4.6, 4.45, 9.6), 160, 2.4)
    s.prop('Roof AC unit', g, VM + 'AmpRack.obj', (-2.8, 4.45, 9.7), 90, 1.0)
    return g


def build_deck(s, parent):
    g = s.group('The deck (where the band plays)', parent)
    PLY = (.62, .46, .3)
    s.slab('Deck top', g, -7.2, 7.2, DECK_Y - .12, DECK_Y, -1.6, 4.5, PLY, rough=.9)
    s.slab('Deck skirt', g, -7.2, 7.2, 0, DECK_Y - .12, -1.6, -1.5, (.03, .03, .035))
    for x in (-7.15, 7.15):
        s.slab('Deck skirt side', g, x - .05, x + .05, 0, DECK_Y - .12, -1.6, 4.5, (.03, .03, .035))
    glow(s, 'LED edge', g, (0, DECK_Y - .02, -1.62), (14.4, .05, .04), CYAN, 3.0)
    s.slab('Stair', g, 6.0, 7.0, 0, .33, -2.2, -1.6, (.45, .34, .24))
    s.slab('Stair', g, 6.0, 7.0, 0, .66, -1.9, -1.6, (.45, .34, .24))
    # PA stacks either side.
    for x in (-8.3, 8.3):
        for k, h in enumerate((0, 1.6, 3.2)):
            s.prop('PA cabinet', g, VM + 'Speaker.obj', (x, h, -.6), 0, 1.6)
    s.prop('Rug under the kit', g, VM + 'DrumRug.obj', (DRUMMER[0], DECK_Y, 2.3), 0, 1.0)
    # The hybrid kit's electronics: a sample pad on a stand, the laptop on a flight case, trigger
    # module, the kit-cam on its tripod that ends up on the screen.
    dx, _, dz = DRUMMER
    s.box('Pad stand', g, (dx - 1.65, DECK_Y + .45, dz - .7), (.04, .9, .04), (.2, .2, .22))
    s.box('Sample pad', g, (dx - 1.65, DECK_Y + .95, dz - .7), (.42, .06, .32), (.08, .08, .09), rot=(-18, 20, 0))
    for i in range(3):
        for j in range(3):
            glow(s, 'Pad', g, (dx - 1.78 + i * .13, DECK_Y + .985 + .03 * (1 - j), dz - .8 + j * .09), (.1, .012, .07),
                 (CYAN, PINK, AMBER)[(i + j) % 3], 2.2, rot=(-18, 20, 0))
    s.prop('Laptop case', g, VM + 'FlightCaseWide.obj', (dx - 1.9, DECK_Y, dz + .6), 70, 1.0)
    s.box('Laptop base', g, (dx - 1.9, DECK_Y + .62, dz + .6), (.36, .025, .26), (.12, .12, .13), rot=(0, 70, 0))
    glow(s, 'Laptop screen', g, (dx - 1.78, DECK_Y + .76, dz + .63), (.34, .22, .015), (.45, .7, 1.0), 2.4, rot=(-10, 70 + 90, 0))
    s.prop('Kit-cam tripod', g, VM + 'CameraTripod.obj', (dx + 2.3, DECK_Y, dz - 1.6), -130, 1.0)
    glow(s, 'Tally light (live)', g, (dx + 2.3, DECK_Y + 1.62, dz - 1.6), (.06, .06, .06), RED, 6.0, 'Sphere')
    s.prop('Cable coil', g, VM + 'CableCoil.obj', (dx + 1.6, DECK_Y, dz + .8), 30)
    s.prop('Power distro', g, VM + 'PowerDistro.obj', (5.9, DECK_Y, 3.9), -90, .8)
    # The electronic artist's rig at the Keys spot: a folding table of boxes and a rack behind.
    kx, _, kz = KEYS
    s.slab('Gear table', g, kx - 2.2, kx - 1.2, DECK_Y + .78, DECK_Y + .82, kz - .6, kz + .6, (.1, .1, .11))
    for x in (kx - 2.15, kx - 1.25):
        for z in (kz - .55, kz + .55):
            s.box('Table leg', g, (x, DECK_Y + .39, z), (.03, .78, .03), (.3, .3, .32))
    for i, col in enumerate((PINK, CYAN, VIOLET)):
        s.box('Drum machine', g, (kx - 1.7, DECK_Y + .86, kz - .35 + i * .35), (.36, .06, .28), (.1, .1, .11))
        for j in range(4):
            glow(s, 'Step', g, (kx - 1.82 + j * .08, DECK_Y + .895, kz - .42 + i * .35), (.05, .01, .04), col, 2.5)
    s.prop('Synth rack', g, VM + 'AmpRack.obj', (kx - .3, DECK_Y, kz + 1.6), 0, 1.0)
    glow(s, 'Rack LEDs', g, (kx - .3, DECK_Y + .9, kz + 1.25), (.5, .05, .02), (.3, 1.0, .5), 3.0)
    for x, z, yaw in ((-6.6, 3.6, 0), (6.4, 3.0, 0)):
        s.prop('Road case', g, VM + 'RoadCase.obj', (x, DECK_Y, z), yaw, 1.0)
    s.prop('Cooler', g, VM + 'Cooler.obj', (-6.4, DECK_Y, 1.0), 20)
    return g


def build_screen(s, parent, marks, story_root):
    g = s.group('The screen', parent)
    lattice = M.screen_lattice(SCREEN_W, SCREEN_H, SCREEN_BOTTOM - ground_y(SCREEN_Z), 3.4)
    s.prop('Screen tower', g, lattice, (0, ground_y(SCREEN_Z), SCREEN_Z + .15), 0)
    # Black masking border just outside the picture.
    cx, cy, cz = SCREEN_C
    hw, hh = SCREEN_W / 2, SCREEN_H / 2
    ink = (.02, .02, .025)
    s.slab('Masking top', g, -hw - .45, hw + .45, cy + hh, cy + hh + .45, cz - .05, cz + .12, ink)
    s.slab('Masking bottom', g, -hw - .45, hw + .45, cy - hh - .45, cy - hh, cz - .05, cz + .12, ink)
    s.slab('Masking left', g, -hw - .45, -hw, cy - hh, cy + hh, cz - .05, cz + .12, ink)
    s.slab('Masking right', g, hw, hw + .45, cy - hh, cy + hh, cz - .05, cz + .12, ink)
    s.slab('Screen house', g, -9, 9, ground_y(SCREEN_Z), 3.0, cz + .6, cz + 4.0, (.5, .48, .44))
    s.screen('Live kit feed', marks, SCREEN_C, SCREEN_W, SCREEN_H, 'Stage', 1.6)
    # Until the last song, the station card fills the screen (a panel in front of the feed).
    card = s.story('FM station card (until the kit feed takes over)', story_root, 'hands_on_screen', False, 1.6, (cx, cy, cz - .25))
    c = s.box('88.9 FM card', card, (0, 0, 0), (SCREEN_W, SCREEN_H, .04), (1, 1, 1), shadows=False)
    textured(c, 'FMCard', glow=1.25)
    blue = s.story('The card lights the lot blue', story_root, 'hands_on_screen', False, 1.6, (0, 10, 40))
    blue = world(s, blue, (0, 10, 40))
    s.light('Screen spill (station card)', blue, (0, 13, 35), 'Spot', (.42, .62, 1.0), 22000, 90,
            rot=look_rotation((0, 13, 35), (0, 0, -10)), inner=40, outer=70)
    warm = s.story('The kit feed lights the lot warm', story_root, 'hands_on_screen', True, 1.6, (0, 10, 40))
    warm = world(s, warm, (0, 10, 40))
    s.light('Screen spill (kit feed)', warm, (0, 13, 35), 'Spot', (1.0, .78, .6), 26000, 90,
            rot=look_rotation((0, 13, 35), (0, 0, -10)), inner=40, outer=70)
    return g


def build_beam(s, parent, story_root):
    frustum = M.beam()
    cx, cy, cz = SCREEN_C
    L = math.dist(PORT, (cx, cy, cz))
    rot = look_rotation(PORT, (cx, cy, cz))
    pitch = math.radians(rot[0])
    hw, hh = SCREEN_W / 2, SCREEN_H / 2 * math.cos(pitch)
    a = s.story('Projector beam (station card blue)', story_root, 'hands_on_screen', False, 1.6, PORT)
    additive(s, 'Beam to the screen', a, frustum, (0, 0, 0), rot, (hw, hh, L), (.35, .55, 1.0), .03)
    additive(s, 'Beam core', a, frustum, (0, 0, 0), rot, (hw * .55, hh * .55, L), (.5, .7, 1.0), .02)
    b = s.story('Projector beam (kit feed)', story_root, 'hands_on_screen', True, 1.6, PORT)
    additive(s, 'Beam to the screen', b, frustum, (0, 0, 0), rot, (hw, hh, L), (1.0, .85, .65), .03)
    additive(s, 'Beam core', b, frustum, (0, 0, 0), rot, (hw * .55, hh * .55, L), (1.0, .9, .75), .02)


def build_story(s, root, cast, cars):
    hatch = next(c for c in cars if c['kind'] == 'hatch')
    pick = next(c for c in cars if c['kind'] == 'pickup')
    hx, hy, hz = hatch['pos']
    lip_z = hz + 2.0 + .12      # the backed-in hatch's rear faces +z
    # quilt_at_hatch: the pair in the open hatch under the quilt (gone once the quilt is on the roof).
    at_hatch = s.story('Two under the quilt in the open hatch', root, 'quilt_at_hatch', True, .9, (hx, hy + .6, lip_z))
    at_hatch = world(s, at_hatch, (hx, hy + .6, lip_z))
    still = s.story('(until the quilt goes on the roof)', at_hatch, 'quilt_on_roof', False, .9, (hx, hy + .6, lip_z))
    still = world(s, still, (hx, hy + .6, lip_z))
    for i, (who, dx) in enumerate((('Son_01', -.36), ('Daughter_01', .34))):
        person(s, still, ('Him', 'Her')[i], who, (hx + dx, hy + .08, lip_z + .05), 180, 'seated')
    q = s.box('Quilt round their shoulders', still, (hx, hy + 1.32, lip_z - .05), (1.55, .95, .16), (1, 1, 1), rot=(-8, 0, 0))
    textured(q, 'Quilt', (1.5, 1))
    q2 = s.box('Quilt over the lip', still, (hx, hy + .66, lip_z + .2), (1.55, .06, .8), (1, 1, 1))
    textured(q2, 'Quilt', (1.5, .5))
    s.prop('Thermos', at_hatch, M.thermos(), ((hx + pick['pos'][0]) / 2 + .2, hy, lip_z - .6), 0, 1.0)
    glow(s, 'Thermos gleam', at_hatch, ((hx + pick['pos'][0]) / 2 + .2, hy + .25, lip_z - .66), (.05, .05, .02), (1, .95, .8), 6.0, 'Sphere')
    s.light('Thermos gleam light', at_hatch, ((hx + pick['pos'][0]) / 2 + .2, hy + .5, lip_z - .9), 'Point', (1, .9, .7), 6, 2)
    px, py, pz = pick['pos']
    glow(s, 'Cargo lamp', at_hatch, (px, py + 1.66, pz - .7), (.36, .1, .1), (1, .85, .55), 8.0)
    s.light('Cargo lamp light', at_hatch, (px, py + 1.9, pz - 1.4), 'Point', (1, .78, .5), 55, 5.5)
    s.box('Camp chair seat', at_hatch, (px + 1.9, py + .4, pz - 2.0), (.5, .05, .45), (.15, .3, .5))
    # quilt_on_roof: the quilt on the hatchback's roof, the pair up and bouncing in the gravel.
    roof = s.story('The quilt on the roof', root, 'quilt_on_roof', True, .9, (hx, hy + 1.45, hz))
    roof = world(s, roof, (hx, hy + 1.45, hz))
    S = hatch['S']
    rz0, rz1, ry = S['roof']
    # hatch is yawed 180: its local z is mirrored.
    top = s.box('Quilt on the roof', roof, (hx, hy + ry + .1, hz + (rz0 + rz1) / -2), (2.0, .05, 2.3), (1, 1, 1))
    textured(top, 'Quilt', (1.6, 1.8))
    for sx in (-1, 1):
        f = s.box('Quilt hanging over the side', roof, (hx + sx * 1.0, hy + ry - .25, hz + (rz0 + rz1) / -2), (.05, .75, 2.3), (1, 1, 1), rot=(0, 0, sx * -12))
        textured(f, 'Quilt', (.6, 1.8))
    pair = s.story('The pair bouncing in the gravel', root, 'quilt_on_roof', True, .9, (hx + 2.0, hy, hz))
    pair = world(s, pair, (hx + 2.0, hy, hz))
    person(s, pair, 'Him, bouncing', 'Son_01', (hx + 1.95, hy, hz - .6), 170, 'arms_up', bounce=1.0, pump=True)
    person(s, pair, 'Her, bouncing', 'Daughter_01', (hx + 2.05, hy, hz + .7), 200, 'arms_up', bounce=.97, pump=True)
    # ... and their two shadows cross the bottom of the screen.
    cx, cy, cz = SCREEN_C
    base_y = SCREEN_BOTTOM
    cross = s.story('Their shadows cross the screen', root, 'quilt_on_roof', True, 1.2, (0, base_y, cz - .32))
    walk = s.entity('Crossing', cross)
    body = s.entity('Body', walk)
    for i, dx in enumerate((-1.1, 1.3)):
        h = 6.5 - i * .5
        silhouette(s, body, ('His shadow', 'Her shadow')[i], (dx, -.55 * h / 1.8, 0), h, 'up', (-4, 5)[i], 'ShadowBob', 1 + i * .06)
    seq(walk, 'ShadowCross', {'Body': body}, 1.0)
    # shadows_on_screen: a patch of dancers in the beam, and their arms forty feet tall above the cars.
    sh = s.story('Dancers find the projector beam', root, 'shadows_on_screen', True, 1.2, (0, base_y, cz - .3))
    rng = random.Random(99)
    for i in range(10):
        x = -19 + i * 4.2 + rng.uniform(-.6, .6)
        h = rng.uniform(7.0, 9.5)
        silhouette(s, sh, f'Raised arms {i + 1}', (x, -.55 * h / 1.8 - rng.uniform(0, .5), -.02 * (i % 3)),
                   h, ('up', 'one', 'up', 'v')[i % 4], rng.uniform(-8, 8), 'ShadowBob', rng.uniform(.9, 1.15))
    beam_patch = s.story('The patch of dancers in the beam', cast, 'shadows_on_screen', True, 1.0, (0, -.8, 21))
    beam_patch = world(s, beam_patch, (0, -.8, 21))
    whos = ['Son_01', 'Mother_01', 'Daughter_01', 'Rigged', 'Mother_02', 'ShopKeeper_01', 'SchoolBoy_01', 'SchoolGirl_01']
    for i in range(14):
        x = -5.5 + (i % 7) * 1.8 + rng.uniform(-.3, .3)
        z = 20.3 + (i // 7) * 1.0 + rng.uniform(-.2, .2)
        person(s, beam_patch, f'In the beam {i + 1}', whos[i % len(whos)], (x, ground_y(z), z), rng.uniform(150, 210),
               'arms_up', bounce=rng.uniform(.92, 1.1), pump=True)
    # hands_on_screen: the sticks become forty feet tall across the kit feed.
    sticks = s.story('Forty-foot sticks on the screen', root, 'hands_on_screen', True, 1.0, (0, cy, cz - .35))
    for i, (a, b) in enumerate((((-17.5, 6.8), (3.4, 25.0)), ((17.5, 6.8), (-3.4, 25.0)))):
        pivot = s.entity(('Left stick', 'Right stick')[i], sticks, (a[0], a[1] - cy, 0))
        stroke = s.entity('Stick', pivot)
        ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) - 90
        L = math.dist(a, b)
        mid = ((b[0] - a[0]) / 2, (b[1] - a[1]) / 2, 0)
        s.box('Stick', stroke, mid, (1.3, L, .04), (.004, .004, .006), rot=(0, 0, ang), rough=1, shadows=False, shape='Capsule')
        s.box('Fist', stroke, (0, -.2, 0), (3.4, 3.8, .04), (.004, .004, .006), rot=(0, 0, ang), rough=1, shadows=False, shape='Sphere')
        seq(pivot, 'Stroke', {'Stick': stroke}, 1.0 + .03 * i)


def build_surroundings(s, parent, rng):
    g = s.group('Beyond the lot', parent)
    fence = M.fence_run(40.0)
    for x0 in (-40, 0, 40):
        s.prop('Lot fence (back)', g, fence, (x0, 2.0, -52), 0)
        s.prop('Lot fence (screen end)', g, fence, (x0, -1.2, 56), 0)
    for z in (-32, 8, 48):
        for x in (-48, 48):
            e = s.prop('Lot fence (side)', g, fence, (x, ground_y(z), z), 90)
    for i in range(46):
        side = i % 2
        if i < 30:
            x = (-1 if side else 1) * rng.uniform(52, 75)
            z = rng.uniform(-60, 70)
        else:
            x = rng.uniform(-80, 80)
            z = rng.choice((rng.uniform(62, 80), rng.uniform(-80, -60)))
        s.prop('Treeline', g, BY + 'GardenTree.obj', (x, -1.6, z), rng.uniform(0, 360), rng.uniform(1.6, 2.6))
    for i, (x, z, sx, sy, sz) in enumerate([(-120, 160, 120, 30, 40), (40, 190, 160, 42, 50), (170, 120, 90, 26, 40),
                                             (-180, 60, 70, 22, 60), (180, -40, 60, 18, 60)]):
        s.box('Hills', g, (x, -6, z), (sx * 2, sy * 2, sz * 2), (.018, .026, .03), shape='Sphere', rough=1, shadows=False)
    # The town over the hill: a scatter of window lights and a water tower's red light.
    for i in range(40):
        x = rng.uniform(-150, -40); z = rng.uniform(140, 170); y = rng.uniform(4, 14)
        glow(s, 'Town light', g, (x, y, z), (.5, .4, .3), (1, .75, .4) if i % 3 else (.6, .8, 1), 4.0)
    # The entry road and its lamps, along the left side.
    for z in (-44, -24, -4, 16):
        s.prop('Lot lamp', g, BY + 'StreetLamp.obj', (-30.5, ground_y(z), z), 90, 1.3)
        s.light('Lot lamp light', g, (-30.0, ground_y(z) + 5.6, z), 'Point', (1, .66, .32), 110, 14)
    # The festival end: the artist's bus and the broadcast truck parked by the booth.
    s.prop('Artist bus', g, VM + 'TourBus.obj', (13.5, 0, 6.5), 0, 1.0)
    s.prop('Broadcast truck', g, VM + 'Truck.obj', (-13.8, 0, 5.0), 180, 1.0)
    s.prop('Truck dish', g, VM + 'FloodLight.obj', (-13.8, 3.75, 4.0), 200, 2.6)
    s.prop('Food stall', g, VM + 'FoodStall.obj', (-10.0, 0, -4.5), 30, 1.3)
    s.prop('Food stall', g, VM + 'FoodStall.obj', (10.6, 0, -4.2), -30, 1.3)
    for x in (-24, 24):
        for z in (-7, 9):
            s.prop('Festival flag', g, VM + ('FlagA.obj' if x < 0 else 'FlagB.obj'), (x, 0, z), 0, 1.6)


def build_towers(s, parent):
    tower = M.light_tower(9.0)
    g = s.group('Light towers', parent)
    spots = [(-24, -2.5), (24, -2.5), (-24, -22), (24, -22), (-24, 20), (24, 20)]
    for x, z in spots:
        s.prop('Light tower', g, tower, (x, ground_y(z), z), 0)
    return [(x, ground_y(z) + 9.0, z) for x, z in spots]


def build_festoons(s, parent):
    g = s.group('Festoons', parent)
    runs = [((-6.8, 4.7, 4.3), (-24, 8.5, -2.5), 1.4, 16), ((6.8, 4.7, 4.3), (24, 8.5, -2.5), 1.4, 16),
            ((-24, 8.5, -2.5), (-24, 8.5, -22), 1.6, 14), ((24, 8.5, -2.5), (24, 8.5, -22), 1.6, 14)]
    cols = (AMBER, PINK, CYAN, AMBER, VIOLET)
    for k, (a, b, sag, n) in enumerate(runs):
        def at(t):
            return tuple(a[i] + (b[i] - a[i]) * t - (4 * t * (1 - t) * sag if i == 1 else 0) for i in range(3))
        prev = a
        for i in range(1, n + 1):
            p = at(i / n)
            bar(s, 'Festoon wire', g, prev, p, .025, (.05, .05, .05), shadows=False)
            prev = p
            m = at((i - .5) / n)
            glow(s, 'Festoon bulb', g, (m[0], m[1] - .15, m[2]), (.16, .2, .16), cols[(i + k) % len(cols)], 5.0, 'Sphere')


def build_lights(s, parent, towers):
    g = s.group('Show lights', parent)
    s.light('Moon over the screen', g, (20, 60, 120), 'Directional', (.55, .65, 1.0), 2.6, rot=(32, 196, 0), shadows=True, show='Static')

    def spot(n, pos, to, col, power, reach, inner, outer, role, group=0):
        s.light(n, g, pos, 'Spot', col, power, reach, rot=look_rotation(pos, to), inner=inner, outer=outer, show=role, group=group)
    dx, dy, dz = DRUMMER
    kx, ky, kz = KEYS
    # Follow spots from the back of the lot and from the booth's roof.
    spot('Follow: drummer (from the back terrace)', (0, 9.5, -38), (dx, dy + 1.2, dz), (1, .95, .85), 52000, 60, 3.5, 6.5, 'Spot', 0)
    spot('Follow: electronics (from the back terrace)', (-3, 9.5, -38), (kx, ky + 1.2, kz), (.95, .9, 1.0), 42000, 60, 3.5, 6.5, 'Spot', 1)
    spot('Key: drummer from above', (dx + 1.5, 4.0, dz - 3.0), (dx, dy + 1.0, dz), (1, .85, .7), 300, 9, 20, 38, 'Spot', 2)
    # Washes along the front of the booth roof, pointing down at the deck.
    wash_cols = (PINK, CYAN, VIOLET, AMBER, PINK, CYAN, VIOLET, AMBER)
    for i in range(8):
        x = -5.6 + i * 1.6
        spot(f'Deck wash {i + 1}', (x, 4.4, 4.0), (x * .8, DECK_Y, 0.8), wash_cols[i], 520, 10, 24, 46, 'Wash', i % 3)
    # Beams: the booth roof throws them over the lot; the towers sweep the cars.
    for i in range(8):
        x = -6.2 + i * (12.4 / 7)
        to = (x * 3.0, 9 + (i % 2) * 6, -40)
        spot(f'Roof beam {i + 1}', (x, 4.95, 4.6), to, (CYAN, PINK, VIOLET, (1, 1, 1))[i % 4], 9000, 70, 1.5, 3.5, 'Beam', i % 2)
    for i, (x, y, z) in enumerate(towers):
        to = (x * .3, 0, z + (8 if z < 0 else -8))
        spot(f'Tower beam {i + 1}', (x, y + .3, z), to, (PINK, CYAN, VIOLET)[i % 3], 6000, 40, 2.5, 5, 'Beam', i % 2)
    for i, (x, y, z) in enumerate(towers[:4]):
        s.light(f'Tower strobe {i + 1}', g, (x * .97, y + .1, z), 'Point', (1, 1, 1), 1800, 30, show='Strobe', group=i)
    for i, x in enumerate((-4.5, 4.5)):
        s.light(f'Roof strobe {i + 1}', g, (x, 5.0, 4.4), 'Point', (.9, .95, 1), 900, 18, show='Strobe', group=i)
    for i, x in enumerate((-5.4, -1.8, 1.8, 5.4)):
        spot(f'Deck blinder {i + 1}', (x, DECK_Y + .3, -1.4), (x * 1.6, 1.2, -16), (1, .78, .5), 1400, 20, 22, 48, 'Blinder', i % 2)


def build_crowd(s, marks, cars):
    # The front of the deck: the posed dance floor.
    s.crowd('In front of the deck', marks, (0, 0, -4.6), 13.0, 5.0, 64, .6, 0, 'Posed').components[-1]['DanceFloor'] = True
    # Beside the booth on the flat.
    s.crowd('Flat, left of the booth', marks, (-14.5, 0, -3.8), 9.0, 6.0, 38, .9)
    s.crowd('Flat, right of the booth', marks, (14.5, 0, -3.8), 9.0, 6.0, 38, .9)
    # The drive lanes behind each row of cars, and the aisle down the middle.
    for name, z0, z1, y, n in [('Behind row A', -15.2, -13.4, .5, 34), ('Behind row B', -23.7, -21.6, 1.0, 30),
                               ('Behind row C', -32.2, -30.1, 1.5, 26), ('Back of the lot', -46, -38.8, 2.0, 40)]:
        s.crowd(name, marks, (0, y, (z0 + z1) / 2), 42, z1 - z0, n, .9)
    for name, z0, z1, y in [('Aisle, row A', -13.4, -8.4, .5), ('Aisle, row B', -21.6, -16.9, 1.0), ('Aisle, row C', -30.1, -25.4, 1.5)]:
        s.crowd(name, marks, (0, y, (z0 + z1) / 2), 4.8, z1 - z0, 12, .8)
    # Between the booth and the screen: they came for the screen; they face it.
    for name, z0, z1, y, n in [('Front lane 1', 11.8, 13.6, -.4, 26), ('Front lane 2', 19.8, 21.6, -.8, 24),
                               ('Under the screen', 34.9, 37.6, -1.2, 30)]:
        s.crowd(name, marks, (0, y, (z0 + z1) / 2), 40, z1 - z0, n, .9)
    # On the roofs of a few cars.
    picks = [c for c in cars if c['label'] in ('Row A', 'Row B', 'Row C') and c['shape'] in ('Van', 'Wagon') and not c['kind']]
    for c in picks[:7]:
        x, y, z = c['pos']
        s.crowd('On a car roof', marks, (x, y + c['S']['roof'][2] + .06, z - .4), 1.1, 1.4, 2, .3)


def build_cameras(s, marks, cars):
    g = s.group('Camera positions', marks)
    hatch = next(c for c in cars if c['kind'] == 'hatch')
    hx, hy, hz = hatch['pos']
    cams = [
        ('top-of-the-hill', 'Wide', (0, 9.0, -36), (0, 8.0, 20), 50),
        ('over-the-roofs', 'Crane', (-17, 11, -15), (1, 2.5, 6), 52),
        ('back-terrace-long-lens', 'Desk', (2.5, 5.0, -40), (.8, 2.2, 2.8), 21),
        ('quilt-in-the-hatch', 'Custom', (hx + 1.6, hy + 1.6, hz + 5.2), (hx - .1, hy + 1.0, hz + 1.6), 50),
        ('quilt-on-the-roof', 'Custom', (hx + 5.5, hy + 3.4, hz + 6.5), (hx - .3, hy + 1.2, hz - .6), 48),
        ('hillside-of-headlights', 'Custom', (21, 5.5, 1), (-6, 1.2, -26), 58),
        ('shadows-on-the-screen', 'Custom', (5, 2.0, 15), (-1, 9.5, 44), 62),
        ('down-the-beam', 'Custom', (9.5, 7.5, 6), (-1, 9.0, 40), 60),
        ('kit-and-pads', 'Close', (DRUMMER[0] + 2.4, DECK_Y + 1.8, DRUMMER[2] - 2.6), (DRUMMER[0] - .4, DECK_Y + 1.0, DRUMMER[2] - .4), 46),
        ('the-booth-from-the-flat', 'Custom', (-9, 2.2, -8), (-2.5, 2.6, 3), 54),
    ]
    for tag, kind, eye, aim, fov in cams:
        s.camera_spot(tag, g, eye, aim, kind, fov, tag)
    walk = [((-26, 3.6, -50), (-20, 3.2, -40)), ((-22, 3.6, -45), (-12, 3, -36)), ((-17, 3.5, -41), (-4, 2.6, -28)),
            ((-11, 3.4, -38), (0, 3, -10)), ((-5, 3.4, -36), (0, 4, 10)), ((-1.5, 3.6, -34), (0, 5.5, 20))]
    for i, (eye, aim) in enumerate(walk):
        s.camera_spot(f'Arrival {i + 1:02}', g, eye, aim, 'Custom', 64 - i * 2, f'arrival/{i + 1:02}')


def build():
    rng = random.Random(909)
    M.palette_mtl()
    write_clips()
    s = Scene('story-drive-in-v1')
    root = s.group('Midnight at the FM Drive In')
    ground = s.group('Gravel lot', root)
    lot = s.group('Parked cars', root)
    lamps = s.group('Car lamps', root)
    posts = s.group('Speaker posts', root)
    booth = s.group('Booth and deck', root)
    screen = s.group('Screen', root)
    story = s.group('Story', root)
    cast = s.group('People', root)
    lights = s.group('Lights', root)
    marks = s.group('Venue markers', root)
    build_ground(s, ground)
    cars = build_cars(s, lot, lamps, rng)
    build_posts(s, posts, cars)
    build_booth(s, booth, story)
    build_deck(s, booth)
    build_screen(s, screen, marks, story)
    build_beam(s, screen, story)
    build_story(s, story, cast, cars)
    build_surroundings(s, root, rng)
    towers = build_towers(s, root)
    build_festoons(s, root)
    build_lights(s, lights, towers)
    s.info(marks, 'Midnight at the FM Drive In', 'Drumsmith', outdoor=True, room_back=-48, half_width=30, desk_z=-40,
           fog_color=(.03, .035, .07), haze=.6, sky_time=23.6, moon=1.2)
    s.spot(marks, 'Drummer', DRUMMER)
    s.spot(marks, 'Keys', KEYS, 12)
    build_crowd(s, marks, cars)
    build_cameras(s, marks, cars)
    return s


def main():
    if '--textures' in sys.argv:
        import story_drive_in_textures
        story_drive_in_textures.main()
    folder = os.path.join(repo_root(), 'Assets', 'Venues', ID)
    scene = build()
    scene.write(os.path.join(folder, ID + '.lvl'))
    preview = 'Preview.jpg' if os.path.exists(os.path.join(folder, 'Preview.jpg')) else None
    write_venue_json(folder, 'Midnight at the FM Drive In', ID + '.lvl', preview=preview, ambience='Assets/Sounds/crowd.mp3')
    print(f'{len(scene.entities)} entities in {ID}')


if __name__ == '__main__':
    main()
