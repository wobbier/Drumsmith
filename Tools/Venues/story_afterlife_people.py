"""Highway to the Afterlife's cast (Design/Highway-to-the-Afterlife.md). Two kinds of figure:

- Baked (figure, place, lie): posed in OBJs from the crowd's rigid pieces
  (Assets/Models/People/Crowd/<body>/, read in place), dressed in a PolygonTown atlas variant,
  written to the venue's own Models/People/. The posing is story_legion_people's (Pose, the arm
  bend, the seated legs). For the many: demons, the damned, drivers behind glass, the band lying
  on the road.
- Skinned (actor, arm, leg, ftrack, gait): a VenueFigure marker the game poses through the rigged
  character's skeleton, hands and feet by inverse kinematics. For the few a shot is about: the
  cop, the EMS crews, the nurse.

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


# ---- skinned figures (VenueFigure: Docs/Venue-Authoring.md -> People) ----------------------
# The few people a shot is about are the rigged character itself, posed in the game through its
# skeleton, where the figures above are its rigid crowd pieces baked into a mesh. Everything is in
# the figure's own space: its feet (kneeling: the floor under its knees) at the origin, facing +z,
# its right hand +x.
def arm(lift=5.0, spread=8.0, elbow=12.0, hand=None, pole=None, fingers=None, palm=None, grip=0.15):
    """An arm by angles (lift forward from hanging, spread to the side, elbow bend), or with hand
    set the point its palm reaches (pole: the way the elbow bends; fingers / palm: the hand's turn)."""
    d = {'Raise': float(lift), 'Spread': float(spread), 'Elbow': float(elbow), 'Grip': float(grip)}
    if hand is not None:
        d['Reach'] = True
        d['Hand'] = [round(float(c), 4) for c in hand]
    for key, v in (('Pole', pole), ('Fingers', fingers), ('Palm', palm)):
        if v is not None:
            d[key] = [round(float(c), 4) for c in v]
    return d


def leg(spread=3.0, toe=0.0, foot=None, knee=None):
    """A leg planted (out by spread), or with foot set the point its sole reaches."""
    d = {'Spread': float(spread), 'Toe': float(toe)}
    if foot is not None:
        d['Reach'] = True
        d['Foot'] = [round(float(c), 4) for c in foot]
    if knee is not None:
        d['Knee'] = [round(float(c), 4) for c in knee]
    return d


def actor(s, parent, label, body, variant, pos, yaw=0.0, stance='Standing', motion=None, speed=1.0, once=False, dress=None, **pose):
    """A skinned figure: body in PolygonTown_variant at pos, facing yaw. pose: VenueFigure's
    fields (Bow, Lean, Turn, Nod, HeadTurn, Crouch, SeatHeight, LeftArm=arm(...), RightLeg=leg(...)).
    motion: a clip of ftrack()s, looping from the start (once: played by a VenueStory Play group
    above it when its flag lands). dress: 'Drummer', 'Guitar', 'Bass' or 'Vocals' to wear that
    band member's look as cast for the song instead (body and variant are then only a stand-in)."""
    e = s.entity(label, parent, pos, (0, yaw, 0))
    comp = {'Type': 'VenueFigure', 'Character': f'Assets/Models/People/BodyType1_{body}.fbx',
            'Atlas': f'Assets/Models/Venue/PolygonTown_{variant}.png', 'Stand': stance}
    if dress:
        comp['As'] = dress
    comp.update(pose)
    e.add(comp)
    if motion:
        e.add({'Type': 'Sequence', 'Clip': motion, 'PlayOnStart': not once, 'Loop': not once, 'Speed': round(speed, 4),
               'Bindings': [{'Slot': 'Body', 'Target': e.guid}]})
    return e


def ftrack(prop, keys, interp='Linear'):
    """A track on the bound figure's VenueFigure: prop is a field (Bow, LeftArm.Hand,
    RightLeg.Foot ...), keys (frame, value) with value a number or a point."""
    out = []
    for frame, value in keys:
        v = [round(float(c), 5) for c in value] + [0] if isinstance(value, (tuple, list)) else [round(float(value), 5), 0, 0, 0]
        out.append({'Frame': frame, 'Value': v, 'Interpolation': interp})
    return {'Binding': 'Body', 'Component': 'VenueFigure', 'Property': prop, 'Keys': out}


def to_figure(pos, yaw, point):
    """A point in the figure's parent's space, in the space of a figure standing at pos facing yaw."""
    a = math.radians(yaw)
    dx, dy, dz = point[0] - pos[0], point[1] - pos[1], point[2] - pos[2]
    return (dx * math.cos(a) - dz * math.sin(a), dy, dx * math.sin(a) + dz * math.cos(a))


def turn_to(pos, yaw, point, most=70.0):
    """The degrees a figure standing at pos facing yaw turns its head (to its right) to face point."""
    x, _, z = to_figure(pos, yaw, point)
    return max(-most, min(most, math.degrees(math.atan2(x, z))))


def kneeling_over(reach=0.53, top=0.29, bow=35.0, nod=15.0):
    """VenueFigure fields for someone on their knees with both hands, one on the other, on the
    chest of a patient lying across in front of them: reach ahead of the knees, top off the floor."""
    return dict(stance='Kneeling', Bow=bow, Lean=15.0, Nod=nod, LeftLeg=leg(8), RightLeg=leg(8),
                LeftArm=arm(hand=(-0.015, top, reach), pole=(-1, -0.1, -0.3), fingers=(0.35, 0, 1), palm=(0, -1, 0), grip=0.1),
                RightArm=arm(hand=(0.015, top + 0.03, reach), pole=(1, -0.1, -0.3), fingers=(-0.35, 0, 1), palm=(0, -1, 0), grip=0.3))


def compressions(venue, reach=0.53, top=0.29, bow=35.0, frames=16):
    """Chest compressions for kneeling_over (about 110 a minute at 16 frames): the shoulders come
    down over the hands and the hands go 5 cm into the chest."""
    def down(x, y):
        return [(0, (x, y, reach)), (5, (x, y - 0.05, reach)), (frames, (x, y, reach))]
    return clip(venue, 'Compressions', frames, [ftrack('Bow', [(0, bow), (5, bow + 6), (frames, bow)], 'SmoothStep'),
                                                ftrack('Nod', [(0, 15), (6, 19), (frames, 15)], 'SmoothStep'),
                                                ftrack('LeftArm.Hand', down(-0.015, top), 'SmoothStep'),
                                                ftrack('RightArm.Hand', down(0.015, top + 0.03), 'SmoothStep')])


def gait(venue, name, frames, stride, lift, bob=0.03, swing=35.0, elbow=80.0, arms=('Left', 'Right'), hip=0.09, cycles=0):
    """A stride on the spot (the ground goes by, or the figure's parent moves): each foot lands
    stride/2 ahead, pushes off as far behind, kicks up by lift and comes through; the body drops
    onto each landing. frames: one cycle (two steps). arms: the ones swung by angles (leave out a
    hand that holds something). cycles: 0 a loop; else a one-shot of that many cycles (and four
    frames more: it starts from standing)."""
    half = stride / 2.0
    # (share of the cycle, forward, height, toes down)
    path = ((0.0, half, 0.0, -8.0), (0.32, -half, 0.02, 35.0), (0.48, -half * 1.15, lift, 65.0), (0.72, half * 0.15, lift * 0.75, 15.0),
            (0.9, half * 1.05, lift * 0.3, -10.0), (1.0, half, 0.0, -8.0))
    cycle = []      # (property, keys, interpolation) over one cycle
    for side, x, late in (('Left', -hip, 0.0), ('Right', hip, 0.5)):
        feet, toes = [], []
        for k in range(-1, 2):
            for share, z, y, toe in path:
                f = round((share + late + k) * frames)
                if 0 <= f <= frames and not (feet and feet[-1][0] == f):
                    feet.append((f, (x, y, z)))
                    toes.append((f, toe))
        # The ends of the cycle: the same point, taken from where the wrapped path crosses them.
        for keys, at in ((feet, lambda u: _along(path, u, x)), (toes, lambda u: _toe(path, u))):
            if keys[0][0] != 0:
                keys.insert(0, (0, at((0.0 - late) % 1.0)))
            if keys[-1][0] != frames:
                keys.append((frames, at((1.0 - late) % 1.0)))
        cycle += [(f'{side}Leg.Foot', feet, 'Linear'), (f'{side}Leg.Toe', toes, 'Linear')]
        if side in arms:
            # The arm opposite the leading foot is forward.
            a, b = (swing, -swing * 0.6) if side == 'Right' else (-swing * 0.6, swing)
            cycle.append((f'{side}Arm.Raise', [(0, a), (frames // 2, b), (frames, a)], 'SmoothStep'))
            cycle.append((f'{side}Arm.Elbow', [(0, elbow), (frames, elbow)], 'Linear'))
    q = frames / 4.0
    cycle.append(('Offset', [(0, (0, -bob, 0)), (round(q), (0, 0, 0)), (round(2 * q), (0, -bob, 0)), (round(3 * q), (0, 0, 0)), (frames, (0, -bob, 0))], 'SmoothStep'))
    cycle.append(('Side', [(0, -2.0), (frames // 2, 2.0), (frames, -2.0)], 'SmoothStep'))
    # A one-shot starts from standing still (where a Play group holds it until its flag), four
    # frames before the first stride.
    lead = 4 if cycles else 0
    still = {'LeftLeg.Foot': (-hip, 0, 0), 'RightLeg.Foot': (hip, 0, 0), 'LeftLeg.Toe': 0.0, 'RightLeg.Toe': 0.0, 'LeftArm.Raise': 5.0, 'RightArm.Raise': 5.0,
             'Offset': (0, 0, 0), 'Side': 0.0}
    tracks = []
    for prop, keys, interp in cycle:
        tiled = [(f + lead, v) for f, v in keys]
        for c in range(1, max(cycles, 1)):
            tiled += [(f + lead + c * frames, v) for f, v in keys[1:]]
        if lead:
            tiled.insert(0, (0, still.get(prop, keys[0][1])))
        tracks.append(ftrack(prop, tiled, interp))
    return clip(venue, name, lead + frames * max(cycles, 1), tracks)


def striding(stride, **pose):
    """VenueFigure fields for a figure that gait() moves: both feet sent where the clip says (the
    first frame's, until it plays)."""
    return dict(dict(LeftLeg=leg(foot=(-0.09, 0, stride / 2.0)), RightLeg=leg(foot=(0.09, 0, -stride / 2.0), toe=35.0)), **pose)


def _span(path, u):
    for (u0, *a), (u1, *b) in zip(path, path[1:]):
        if u0 <= u <= u1:
            return (u - u0) / (u1 - u0), a, b
    return 0.0, path[0][1:], path[0][1:]


def _along(path, u, x):
    w, a, b = _span(path, u)
    return (x, a[1] + (b[1] - a[1]) * w, a[0] + (b[0] - a[0]) * w)


def _toe(path, u):
    w, a, b = _span(path, u)
    return a[2] + (b[2] - a[2]) * w


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
