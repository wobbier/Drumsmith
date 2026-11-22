"""StoryLegion's family: posed figures for the daughter, the uncle, the cousins and the relatives at
the tables, each baked into ONE OBJ from the crowd's rigid pieces (Assets/Models/People/Crowd/<body>/,
read in place) in a chosen pose and in the clothes of a chosen atlas variant
(Assets/Models/Venue/PolygonTown_<variant>.png). Small held things (a glass, a folded toast, a
camera) are baked in from the Legion palette. Plus the looping Sequence clips that make them sway.

A figure faces +z at yaw 0 (knees and forearms go forward). Joint rotations are Euler degrees
applied x, then y, then z (glm's Rz * Ry * Rx); a negative x swings an arm forward and up.
"""
import json
import math

from story_legion_mesh import MODELS, LOCAL, VENUE, Mesh, ink_uv, rot_x, rot_y, rot_z, save, cross, sub, unit, dot

CROWD = VENUE.parents[1] / 'Models/People/Crowd'
HIP, SEATED_HIP = .8763, .57
NECK = (0, .5727, -.0242)
SHOULDER = (.191, .5141, -.0484)
ELBOW = -.323


def _smooth(v):
    v = max(0.0, min(1.0, v))
    return v * v * (3 - 2 * v)


def _rot(p, r):
    if not r:
        return p
    return rot_z(rot_y(rot_x(p, r[0]), r[1]), r[2])


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _read(body, piece, lo):
    path = CROWD / body / (piece + ('_Lo' if lo else '') + '.obj')
    verts, uvs, faces = [], [], []
    for line in path.read_text().splitlines():
        if line.startswith('v '):
            x, y, z = map(float, line.split()[1:4])
            verts.append((x, y, -z))          # into venue space
        elif line.startswith('vt '):
            uvs.append(tuple(map(float, line.split()[1:3])))
        elif line.startswith('f '):
            faces.append([tuple(int(i) for i in c.split('/')[:2]) for c in line.split()[1:]])
    return verts, uvs, faces


def _bend_arm(p, bend):
    x, y, z = p
    if not bend:
        return p
    a = math.radians(bend)
    w = _smooth((-.23 - y) / .17)
    ty = y * (1 - w) + (ELBOW + (y - ELBOW) * math.cos(a) + z * math.sin(a)) * w
    tz = z * (1 - w) + (-(y - ELBOW) * math.sin(a) + z * math.cos(a)) * w
    return (x, ty, tz)


def _seat_legs(p):
    x, y, z = p
    knee = .46
    ang = math.radians(79)
    y1 = SEATED_HIP + (y - HIP) * math.cos(ang) + z * math.sin(ang)
    z1 = -(y - HIP) * math.sin(ang) + z * math.cos(ang)
    w = _smooth((y - .37) / .19)
    ty = (.49 + y - knee) * (1 - w) + y1 * w
    tz = (.405 + z) * (1 - w) + z1 * w
    w = _smooth((y - .81) / .10)
    ty = ty * (1 - w) + (y - HIP + SEATED_HIP) * w
    tz = tz * (1 - w) + z * w
    return (x, ty, tz)


class Pose:
    """seated; torso / head Euler; arms: (shoulder Euler, elbow bend degrees)."""

    def __init__(self, seated=False, torso=(0, 0, 0), head=(0, 0, 0), arm_l=((0, 0, 0), 0), arm_r=((0, 0, 0), 0)):
        self.seated, self.torso, self.head, self.arm_l, self.arm_r = seated, torso, head, arm_l, arm_r

    def hip(self):
        return (0, SEATED_HIP if self.seated else HIP, 0)

    def hand(self, side):
        """Where the palm of the left (-1) or right (+1) hand ends up, in figure space."""
        (rot, bend) = self.arm_l if side < 0 else self.arm_r
        a = math.radians(bend)
        palm = (0, ELBOW - .35 * math.cos(a), .35 * math.sin(a))
        p = _rot(palm, rot)
        p = _add(p, (side * SHOULDER[0], SHOULDER[1], SHOULDER[2]))
        return _add(_rot(p, self.torso), self.hip())


STANDING = Pose()
SITTING = Pose(True, (4, 0, 0), (-4, 0, 0), ((-28, 0, 6), 62), ((-28, 0, -6), 62))


def figure(name, body, variant, pose, extras=None, lo=False, note=''):
    """Bake one posed figure to Models/People/<name>.obj; extras(mesh, pose) adds held things."""
    mtl = f'People_{variant}.mtl'
    save(MODELS / 'People' / mtl,
         f'newmtl Clothes\nKd 1 1 1\nKs 0 0 0\nNs 0\nillum 1\nmap_Kd ../../../../Models/Venue/PolygonTown_{variant}.png\n\n'
         'newmtl Palette\nKd 1 1 1\nKs 0 0 0\nNs 0\nillum 1\nmap_Kd ../../Textures/Legion_Palette.png\n')
    hip = pose.hip()
    parts = []

    def place(piece, fn):
        verts, uvs, faces = _read(body, piece, lo)
        parts.append(([fn(v) for v in verts], uvs, faces))

    place('Legs', _seat_legs if pose.seated else (lambda v: v))
    place('Torso', lambda v: _add(_rot(v, pose.torso), hip))
    place('Head', lambda v: _add(_rot(_add(_rot(v, pose.head), NECK), pose.torso), hip))
    for side, piece, (rot, bend) in ((-1, 'ArmL', pose.arm_l), (1, 'ArmR', pose.arm_r)):
        offset = (side * SHOULDER[0], SHOULDER[1], SHOULDER[2])
        place(piece, lambda v, r=rot, b=bend, o=offset: _add(_rot(_add(_rot(_bend_arm(v, b), r), o), pose.torso), hip))

    lines = [f'# {note or name}: {body} in PolygonTown_{variant}, posed by Tools/Venues/story_legion_people.py',
             f'mtllib {mtl}', 'o ' + name, 's off']
    vlines, tlines, nlines, flines = [], [], [], ['usemtl Clothes']
    vbase = tbase = 0
    for verts, uvs, faces in parts:
        vlines += ['v %.5f %.5f %.5f' % (x, y, -z) for x, y, z in verts]
        tlines += ['vt %.6f %.6f' % t for t in uvs]
        for f in faces:
            a, b, c = [(verts[i - 1][0], verts[i - 1][1], -verts[i - 1][2]) for i, _ in f[:3]]
            n = cross(sub(b, a), sub(c, a))
            n = unit(n) if dot(n, n) > 1e-15 else (0, 1, 0)
            nlines.append('vn %.4f %.4f %.4f' % n)
            ni = len(nlines)
            flines.append('f ' + ' '.join(f'{v + vbase}/{t + tbase}/{ni}' for v, t in f))
        vbase += len(verts)
        tbase += len(uvs)
    if extras:
        m = Mesh(name + '_held', '')
        extras(m, pose)
        flines.append('usemtl Palette')
        for pts, _, tex in m.faces:
            xyz = [(x, y, -z) for x, y, z in reversed(pts)]
            n = cross(sub(xyz[1], xyz[0]), sub(xyz[2], xyz[0]))
            if dot(n, n) < 1e-16:
                continue
            n = unit(n)
            nlines.append('vn %.4f %.4f %.4f' % n)
            ni = len(nlines)
            ids = []
            for p, t in zip(xyz, reversed(tex)):
                vlines.append('v %.5f %.5f %.5f' % p)
                tlines.append('vt %.6f %.6f' % t)
                ids.append(f'{len(vlines)}/{len(tlines)}/{ni}')
            flines.append('f ' + ' '.join(ids))
    save(MODELS / 'People' / (name + '.obj'), '\n'.join(lines + vlines + tlines + nlines + flines) + '\n')
    return LOCAL + 'People/' + name + '.obj'


# ---- held things -------------------------------------------------------------------------------
def glass_in(side, kind='flute'):
    def add(m, pose):
        x, y, z = pose.hand(side)
        if kind == 'flute':
            m.cyl((x, y - .02, z + .03), .025, .01, 'glass', 6)
            m.cyl((x, y - .01, z + .03), .006, .09, 'glass', 5)
            m.cyl((x, y + .08, z + .03), .02, .12, 'beer', 6, radius_top=.028)
        else:
            m.cyl((x, y - .05, z + .03), .035, .1, 'beer', 7)
    return add


def paper_in(side):
    def add(m, pose):
        x, y, z = pose.hand(side)
        m.box((x, y + .02, z + .05), (.12, .16, .01), 'paper', yaw=10)
    return add


def camera_in(m, pose):
    l, r = pose.hand(-1), pose.hand(1)
    c = ((l[0] + r[0]) / 2, (l[1] + r[1]) / 2 + .04, (l[2] + r[2]) / 2 + .04)
    m.box(c, (.15, .1, .08), 'black')
    m.cyl((c[0], c[1] - .03, c[2] + .04), .03, .07, 'steel', 8)
    m.box((c[0] + .05, c[1] + .07, c[2]), (.05, .03, .03), 'white')


def both(*fns):
    def add(m, pose):
        for f in fns:
            f(m, pose)
    return add


# ---- motion ------------------------------------------------------------------------------------
def _quat(rot):
    x, y, z = [math.radians(a) / 2 for a in rot]
    a, b = math.sin(x), math.cos(x)
    c, d = math.sin(y), math.cos(y)
    e, f = math.sin(z), math.cos(z)
    return [round(v, 7) for v in (a * d * f - b * c * e, b * c * f + a * d * e, b * d * e - a * c * f, b * d * f + a * c * e)]


def clips():
    """Sway (the slow dance: a turn and a lean), Bounce (the cousins), Breathe (the seated)."""
    folder = VENUE / 'Motion'
    out = {}

    def write(name, frames, tracks):
        clip = {'Version': 1, 'Name': name, 'FrameRate': 30, 'DurationFrames': frames, 'Tracks': tracks}
        save(folder / (name + '.sequence'), json.dumps(clip, indent=1) + '\n')
        out[name] = f'Assets/Venues/StoryLegion/Motion/{name}.sequence'

    # Slow dance: one full turn in 24 s, leaning side to side on each step.
    frames = 720
    keys = []
    for i in range(17):
        t = i / 16
        keys.append({'Frame': round(t * frames), 'Value': _quat((0, -360 * t, 3.5 * math.sin(t * 2 * math.pi * 8))),
                     'Interpolation': 'Linear'})
    write('Sway', frames, [{'Binding': 'Body', 'Component': 'Transform', 'Property': 'Rotation', 'Keys': keys}])
    # The cousins: a bob on the beat-ish (about 120 bpm) with a twist.
    frames = 60
    pos = [{'Frame': f, 'Value': [0, y, 0, 0], 'Interpolation': 'SmoothStep'} for f, y in ((0, 0), (8, .09), (15, 0), (23, .07), (30, 0), (38, .09), (45, 0), (53, .07), (60, 0))]
    rot = [{'Frame': f, 'Value': _quat((0, yaw, roll)), 'Interpolation': 'SmoothStep'} for f, yaw, roll in ((0, -10, -3), (30, 12, 3), (60, -10, -3))]
    write('Bounce', frames, [{'Binding': 'Body', 'Component': 'Transform', 'Property': 'Position', 'Keys': pos},
                             {'Binding': 'Body', 'Component': 'Transform', 'Property': 'Rotation', 'Keys': rot}])
    # Seated relatives: a slow lean in and back, as if listening.
    frames = 240
    rot = [{'Frame': f, 'Value': _quat((p, y, 0)), 'Interpolation': 'SmoothStep'} for f, p, y in ((0, 0, 0), (90, 3, 6), (160, 1, -4), (240, 0, 0))]
    write('Breathe', frames, [{'Binding': 'Body', 'Component': 'Transform', 'Property': 'Rotation', 'Keys': rot}])
    return out


def place(s, parent, label, model, pos, yaw, clip=None, speed=1.0):
    """A baked figure at pos (feet, or the chair's hip point for a seated one), facing yaw."""
    root = s.entity(label, parent, pos, (0, yaw, 0))
    body = s.entity('Body', root)
    body.add({'Type': 'Model', 'ModelPath': model})
    if clip:
        root.add({'Type': 'Sequence', 'Clip': clip, 'PlayOnStart': True, 'Loop': True, 'Speed': speed,
                  'Bindings': [{'Slot': 'Body', 'Target': body.guid}]})
    return root
