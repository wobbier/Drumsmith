"""Highway to the Afterlife's cast (Design/Highway-to-the-Afterlife.md): posed figures baked into
OBJs from the crowd's rigid pieces (Assets/Models/People/Crowd/<body>/, read in place), dressed in
a PolygonTown atlas variant, written to the venue's own Models/People/. The posing is
story_legion_people's (Pose, the arm bend, the seated legs); only the output folder differs.

A figure faces +z at yaw 0. A lying figure is a standing one turned onto its back by the entity
(lie()), its head toward the entity's -z.
"""
import json
import math
from pathlib import Path

from story_legion_people import (HIP, NECK, SHOULDER, SITTING, STANDING, Pose, _add, _bend_arm, _quat,  # noqa: F401
                                 _read, _rot, _seat_legs)
from story_legion_mesh import cross, dot, save, sub, unit

ROOT = Path(__file__).resolve().parents[2]

# Poses (see story_legion_people.Pose: torso / head Euler; arms (shoulder Euler, elbow bend)).
DRIVING = Pose(True, (2, 0, 0), (0, 0, 0), ((-40, 0, 8), 70), ((-40, 0, -8), 70))
RADIO = Pose(True, (2, 8, 0), (6, 12, 0), ((-100, 0, 40), 140), ((-40, 0, -8), 70))
NODDING = Pose(True, (2, 0, 0), (14, 0, 0), ((-40, 0, 8), 70), ((-40, 0, -8), 70))
KNEEL_CPR = Pose(True, (38, 0, 0), (18, 0, 0), ((-58, 0, 12), 10), ((-58, 0, -12), 10))
KNEEL_LOOK = Pose(True, (24, -18, 0), (-8, -30, 0), ((-40, 0, 10), 30), ((-30, 0, -10), 40))
KNEEL_NOD = Pose(True, (30, 0, 0), (24, 8, 0), ((-58, 0, 12), 10), ((-58, 0, -12), 10))
THRONE = Pose(True, (-6, 0, 0), (4, 0, 0), ((-30, 0, 20), 60), ((-30, 0, -20), 60))
BECKON = Pose(True, (-4, -6, 0), (0, 10, 0), ((-30, 0, 20), 60), ((-75, 10, -30), 55))
AIR_DRUMS = Pose(True, (6, 0, 0), (12, 0, 0), ((-55, 0, 18), 80), ((-70, 0, -18), 95))
STANDING_PROUD = Pose(False, (-4, 0, 0), (-6, 0, 0), ((-10, 0, 25), 20), ((-10, 0, -25), 20))
ON_THE_PHONE = Pose(False, (-6, 0, 0), (-28, 0, 0), ((-150, 0, 30), 150), ((-165, 0, -10), 10))
CHEER = Pose(False, (-4, 0, 0), (-10, 0, 0), ((-160, 0, 15), 20), ((-150, 0, -20), 30))
FISTS = Pose(False, (4, 0, 0), (4, 0, 0), ((-80, 0, 15), 100), ((-80, 0, -15), 100))
CROUCH_CATCH = Pose(True, (55, 0, 0), (-25, 0, 0), ((-70, 0, 10), 0), ((-70, 0, -10), 0))
TURN_BACK = Pose(False, (0, 150, 0), (-6, 20, 0), ((0, 0, 8), 10), ((0, 0, -8), 10))
ROBED = Pose(False, (-2, 0, 0), (-4, 0, 0), ((-30, 0, 35), 30), ((-30, 0, -35), 30))
TAPPING = Pose(False, (0, 0, 0), (0, -25, 0), ((0, 0, 8), 0), ((-25, 0, -60), 40))


def figure(venue, name, body, variant, pose, note=''):
    """Bake one posed figure to Assets/Venues/<venue>/Models/People/<name>.obj; returns its path."""
    folder = ROOT / 'Assets/Venues' / venue / 'Models/People'
    mtl = f'People_{variant}.mtl'
    save(folder / mtl, f'newmtl Clothes\nKd 1 1 1\nKs 0 0 0\nNs 0\nillum 1\nmap_Kd ../../../../Models/Venue/PolygonTown_{variant}.png\n')
    hip = pose.hip()
    parts = []

    def place(piece, fn):
        verts, uvs, faces = _read(body, piece, False)
        parts.append(([fn(v) for v in verts], uvs, faces))

    place('Legs', _seat_legs if pose.seated else (lambda v: v))
    place('Torso', lambda v: _add(_rot(v, pose.torso), hip))
    place('Head', lambda v: _add(_rot(_add(_rot(v, pose.head), NECK), pose.torso), hip))
    for side, piece, (rot, bend) in ((-1, 'ArmL', pose.arm_l), (1, 'ArmR', pose.arm_r)):
        offset = (side * SHOULDER[0], SHOULDER[1], SHOULDER[2])
        place(piece, lambda v, r=rot, b=bend, o=offset: _add(_rot(_add(_rot(_bend_arm(v, b), r), o), pose.torso), hip))
    lines = [f'# {note or name}: {body} in PolygonTown_{variant}, posed by Tools/Venues/story_afterlife_people.py',
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
    save(folder / (name + '.obj'), '\n'.join(lines + vlines + tlines + nlines + flines) + '\n')
    return f'Assets/Venues/{venue}/Models/People/{name}.obj'


def place(s, parent, label, model, pos, yaw=0.0, scale=1.0, pitch=0.0):
    root = s.entity(label, parent, pos, (pitch, yaw, 0), (scale, scale, scale))
    root.add({'Type': 'Model', 'ModelPath': model})
    return root


def lie(s, parent, label, model, pos, yaw=0.0):
    """A standing figure laid on its back, feet at pos, head toward the entity's -z after yaw."""
    x, y, z = pos
    return s.entity(label, parent, (x, y + .14, z), (-90, yaw, 0)).add({'Type': 'Model', 'ModelPath': model})


def clip(venue, name, frames, tracks):
    """A looping Sequence clip at Assets/Venues/<venue>/Motion/<name>.sequence; returns its path."""
    data = {'Version': 1, 'Name': name, 'FrameRate': 30, 'DurationFrames': frames, 'Tracks': tracks}
    save(ROOT / 'Assets/Venues' / venue / 'Motion' / (name + '.sequence'), json.dumps(data, indent=1) + '\n')
    return f'Assets/Venues/{venue}/Motion/{name}.sequence'


def track(prop, keys, interp='Linear'):
    """A track on the bound 'Body' entity's Transform: keys are (frame, value) with value a
    position (x, y, z), a scale (x, y, z) or, for Rotation, Euler degrees."""
    out = []
    for frame, value in keys:
        v = _quat(value) if prop == 'Rotation' else [round(c, 5) for c in value] + [0]
        out.append({'Frame': frame, 'Value': v, 'Interpolation': interp})
    return {'Binding': 'Body', 'Component': 'Transform', 'Property': prop, 'Keys': out}


def looping(s, parent, label, clip_path, pos=(0, 0, 0), speed=1.0, rot=(0, 0, 0)):
    """An entity playing clip_path on a loop, and its 'Body' child (put the moving things under it)."""
    root = s.entity(label, parent, pos, rot)
    body = s.entity('Body', root)
    root.add({'Type': 'Sequence', 'Clip': clip_path, 'PlayOnStart': True, 'Loop': True, 'Speed': round(speed, 4),
              'Bindings': [{'Slot': 'Body', 'Target': body.guid}]})
    return body


def frame(s, group, pivot):
    """A child of a story group that cancels its pivot, so what's under it is placed in venue space."""
    return s.entity('(venue frame)', group, tuple(-v for v in pivot))


def gated(s, parent, name, flag, when_set=True, fade=0.75, pivot=(0, 0, 0)):
    """A VenueStory group grown from pivot, with a child in venue space to put things under."""
    return frame(s, s.story(name, parent, flag, when_set, fade, pivot), pivot)


def between(s, parent, name, after, before, fade=0.75, pivot=(0, 0, 0)):
    """Shown once flag after is set and until flag before is (either may be None)."""
    node = parent
    if after:
        node = gated(s, node, name, after, True, fade, pivot)
    if before:
        node = gated(s, node, name + ' (until ' + before + ')', before, False, fade, pivot)
    return node


def ring(s, parent, name, centre, radius, count, size, color, axis='z', emissive=None, intensity=1.0, phase=0.0):
    """A ring of boxes about centre, in the plane across axis ('z': the x-y plane)."""
    for i in range(count):
        a = phase + 2 * math.pi * i / count
        c, d = math.cos(a) * radius, math.sin(a) * radius
        if axis == 'z':
            pos, rot = (centre[0] + c, centre[1] + d, centre[2]), (0, 0, math.degrees(a))
        elif axis == 'x':
            pos, rot = (centre[0], centre[1] + d, centre[2] + c), (-math.degrees(a), 0, 0)
        else:
            pos, rot = (centre[0] + c, centre[1], centre[2] + d), (0, -math.degrees(a), 0)
        s.box(f'{name} {i}', parent, pos, size, color, rot=rot, emissive=emissive, emissive_intensity=intensity, shadows=False)


def play(s, parent, label, flag, clip_path, pos=(0, 0, 0), rot=(0, 0, 0)):
    """An entity that plays clip_path once when the story flag lands (VenueStory Mode Play), and
    its 'Body' child: put what moves under it. A flag set before the song starts it at its end."""
    root = s.entity(label, parent, pos, rot)
    body = s.entity('Body', root)
    root.add({'Type': 'Sequence', 'Clip': clip_path, 'PlayOnStart': False, 'Loop': False, 'Speed': 1.0,
              'Bindings': [{'Slot': 'Body', 'Target': body.guid}]})
    root.add({'Type': 'VenueStory', 'Flag': flag, 'WhenSet': True, 'FadeSeconds': 0.0, 'Mode': 'Play', 'Speed': 1.0})
    return body


def slow_motion(s, parent, label, flag, speed):
    """A group whose looping clips run at speed until the story flag lands (VenueStory Mode
    SlowMotion), then at full speed."""
    g = s.entity(label, parent)
    g.add({'Type': 'VenueStory', 'Flag': flag, 'WhenSet': True, 'FadeSeconds': 0.0, 'Mode': 'SlowMotion', 'Speed': round(speed, 4)})
    return g


def turn_clip(venue, degrees, seconds=1.5, pitch=0.0):
    """A one-shot turn of the Body by degrees of yaw (and pitch), eased, rounded to 5 degrees."""
    d = int(round(degrees / 5.0)) * 5
    p = int(round(pitch / 5.0)) * 5
    frames = max(1, int(seconds * 30))
    return clip(venue, f'Turn_{d}_{p}', frames, [track('Rotation', [(0, (0, 0, 0)), (frames, (p, d, 0))], 'SmoothStep')])


def path_clip(venue, name, points, seconds, extra=None):
    """A one-shot move of the Body through points (relative to where it starts), evenly in time."""
    frames = max(1, int(seconds * 30))
    n = len(points) - 1
    keys = [(round(frames * i / n), p) for i, p in enumerate(points)]
    tracks = [track('Position', keys, 'Linear')]
    if extra:
        tracks += extra(frames)
    return clip(venue, name, frames, tracks)


def yaw_to(src, dst):
    return math.degrees(math.atan2(dst[0] - src[0], dst[2] - src[2]))


def wrap(deg):
    return (deg + 180.0) % 360.0 - 180.0
