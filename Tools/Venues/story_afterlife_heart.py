"""The heart of hell, where the band lands in Free Bird and plays Bat Country
(Design/Highway-to-the-Afterlife.md, "Arrival in hell"): built into make_story_afterlife.hell().

They land at 'landed' (Free Bird's gtr_solo_h) and the place is frozen. Satan, monumental, three
faces on one head (Dante's: red in front, yellow-white on his right, black on his left), sits
waist deep in a block of ice on his rock-and-roll throne (amp cabinets for arms and back, a fan of
iron spikes over it), and his wings beat on a loop: their wind is what keeps the place frozen,
snow and frost blowing down the stairs at the band. The nine tiers of the stands are under snow
and every demon in them stands frozen stiff, a statue of ice. The lake of lava is a sheet of ice.

The playing thaws it. 'thaw_1': a glow kindles in his chest, his heart, beating on the song's
beats (VenueBeat Sharp: it pushes out through his chest on each). 'thaw_2': the ice cracks and
starts to melt back, the demons on the floor and the three lowest tiers thaw one tier after
another (the statue slides down off each demon, who is dancing inside it already), and he nods.
'thaw_3': the next three tiers, the lake breaks up, he rocks his shoulders. 'thaw_4': the top
three tiers, the braziers catch, he air-drums with the player's hits. 'thawed' (Free Bird's bre,
the big ending): fire and brimstone, the hell everyone thinks of: the lava, the falls, the jets,
the bats, the red rig, an eruption out of the lake, and the spirits they fell past dropping into
the stands for the party. Bat Country starts with all of that set (a song's earlier flags count
as set), so it plays in the fire with Satan as its host: beckoning on 'encore_called' (Free Bird's
own cue), nodding along on 'satan_nods', drumming on the arms of the throne on 'satan_air_drums',
on his feet on 'satan_stands', on the phone on 'phone_call'.

How much he and the thawed demons move follows the playing (VenueBeat Calm, and his drumming is
on the player's own hits: Trigger Hit / Accent). The thaw itself runs on the flags, whatever the
playing, so that Bat Country always finds it done.

Satan is built here from the set's primitives (story_afterlife_mesh), in a man's units (1 is a
metre on a man) and scaled up by SCALE: a rig of pivots (hips, torso, neck, shoulders, elbows),
one rig for each way he moves, each shown between its flags (they swap at rest, so nothing pops).
"""
import math
import random

import story_afterlife_art as A
import story_afterlife_circles as CIR
import story_afterlife_people as P
from story_afterlife_mesh import Mesh, fbm3, rot, add, lerp
from story_legion_people import _read, _rot, _add, _bend_arm, _seat_legs, NECK, SHOULDER
from venuegen import look_rotation as _look

SCALE = 10.0                # Satan and his throne: a man's units to the venue's metres
SEAT_HIP, STAND_HIP = 0.62, 0.98
STAND_Z = 0.55              # standing, his feet are this far in front of where his seated hips were
SHOULDER_AT = 0.33          # the shoulders' half width (torso space: y 0.56)
NECK_AT = (0.0, 0.7, 0.01)
HEAD = 1.3                  # his head on that neck, larger than a man's would be on that body
ELBOW = (0.0, -0.32, 0.0)
CHEST = (-0.07, 0.45, 0.115)    # his heart, in torso space (his left of the middle)
ICE_TOP = 0.88              # the ice block's top: waist deep, seated
THAW_FLAGS = ('thaw_1', 'thaw_2', 'thaw_3', 'thaw_4')

# The stands thaw from the floor up: the floor's demons and each tier in turn (0 by the floor,
# 8 the top): the flag that starts it and the seconds after it.
THAW_AT = {'floor': ('thaw_2', 1.0), 0: ('thaw_2', 2.5), 1: ('thaw_2', 4.0), 2: ('thaw_2', 5.5),
           3: ('thaw_3', 0.5), 4: ('thaw_3', 2.5), 5: ('thaw_3', 4.5),
           6: ('thaw_4', 0.5), 7: ('thaw_4', 2.5), 8: ('thaw_4', 4.5)}
# Seconds from each thaw flag to the next and to 'thawed' (Free Bird's chart: gtr_solo_i - 6,
# gtr_solo_i, +8, +17, bre): the slow melts are timed to end on 'thawed'.
TO_THAWED = {'thaw_1': 31.2, 'thaw_2': 25.2, 'thaw_3': 17.2, 'thaw_4': 8.2}


class Stance:
    """seated; torso and head Euler; each arm (shoulder Euler, elbow bend), left first."""

    def __init__(self, seated, torso, head, left, right):
        self.seated, self.torso, self.head, self.arms = seated, torso, head, (left, right)

    def hip(self):
        return (0.0, SEAT_HIP, 0.0) if self.seated else (0.0, STAND_HIP, STAND_Z)


# Positive x on a joint pitches it forward and down; a shoulder's negative x swings the arm
# forward and up; z swings it out (negative on the left arm, positive on the right).
FROZEN = Stance(True, (-3, 0, 0), (12, 0, 0), ((-18, 0, -14), 78), ((-18, 0, 14), 78))
JAMMING = Stance(True, (7, 0, 0), (16, 0, 0), ((-48, 0, -16), 62), ((-48, 0, 16), 62))
ON_THE_ARMS = Stance(True, (4, 0, 0), (14, 0, 0), ((-22, 0, -14), 118), ((-22, 0, 14), 118))
STANDING = Stance(False, (-4, 0, 0), (14, 0, 0), ((-8, 0, -30), 48), ((-8, 0, 30), 48))
ON_THE_PHONE = Stance(False, (-6, 0, 0), (-30, 0, 0), ((-130, 30, -20), 120), ((-165, 0, 22), 15))


def shoulder(side):
    return (side * SHOULDER_AT, 0.56, -0.01)


def in_figure(stance, p, part='torso', side=0, bend_from=None):
    """A point in the figure's space (feet at the origin): p in torso space, or on the head
    (head space, about the top of the neck), or on an arm (shoulder space)."""
    if part == 'head':
        p = add(rot(p, stance.head), NECK_AT)
    elif part == 'arm':
        r, bend = stance.arms[0 if side < 0 else 1]
        p = add(rot(p, r), shoulder(side))
    return add(rot(p, stance.torso), stance.hip())


def hand(stance, side):
    r, bend = stance.arms[0 if side < 0 else 1]
    tip = add(rot((0, -0.36, 0), (-bend, 0, 0)), ELBOW)
    return in_figure(stance, tip, 'arm', side)


# ---- his body -------------------------------------------------------------------------------
def _torso(m):
    """Chest, belly and shoulders about the hips (torso space), a ridge of spines down his back."""
    m.blob((0, 0.17, 0.02), 1.0, 'skin_red', 2, 0.05, 2.0, 41, (0.17, 0.16, 0.14))
    m.blob((0, 0.43, 0.0), 1.0, 'skin_red', 2, 0.04, 2.0, 42, (0.29, 0.2, 0.17))
    for side in (-1, 1):
        m.blob((side * 0.11, 0.47, 0.085), 1.0, 'skin_red', 1, 0.0, 1.0, 43, (0.12, 0.08, 0.07))
        m.blob(shoulder(side), 0.11, 'skin_red', 1, 0.05, 2.0, 44)
        m.tube([(side * 0.06, 0.64, -0.03), (side * 0.27, 0.6, -0.02)], [0.075, 0.06], 'skin_red', 6)
        for k in range(3):
            m.blob((side * 0.06, 0.27 - 0.07 * k, 0.13), 1.0, 'skin_red', 0, 0.0, 1.0, 45, (0.05, 0.03, 0.03))
    m.tube([(0, 0.58, 0.0), (0, 0.74, 0.02)], [0.09, 0.08], 'skin_red', 8)
    for k in range(6):
        y = 0.62 - 0.1 * k
        m.tube([(0, y, -0.15 + 0.01 * k), (0, y + 0.03, -0.24 + 0.01 * k)], [0.025, 0.0], 'bone_dark', 4, caps=False)


def _upper_arm(m):
    m.tube([(0, 0, 0), (0, -0.16, 0.01), ELBOW], [0.095, 0.085, 0.065], 'skin_red', 7)
    m.blob((0, -0.14, 0.035), 1.0, 'skin_red', 1, 0.0, 1.0, 46, (0.07, 0.1, 0.065))


def _forearm(m, grip='open', receiver=False):
    """Hanging from the elbow (its origin): the forearm, the hand and its claws."""
    m.tube([(0, 0, 0), (0, -0.14, 0.01), (0, -0.29, 0)], [0.07, 0.068, 0.048], 'skin_red', 7)
    m.blob((0, -0.34, 0.01), 1.0, 'skin_red', 1, 0.05, 2.0, 47, (0.055, 0.07, 0.04))
    for i in range(4):
        x = -0.036 + 0.024 * i
        if grip == 'fist':
            path = [(x, -0.39, 0.02), (x, -0.41, 0.05), (x, -0.385, 0.065)]
        else:
            path = [(x, -0.39, 0.012), (x, -0.45, 0.03), (x, -0.49, 0.055)]
        m.tube(path, [0.016, 0.013, 0.01], 'skin_red', 4)
        m.tube([path[-1], add(path[-1], (0, -0.01, 0.03))], [0.009, 0.0], 'black', 3, caps=False)
    m.tube([(0.05, -0.33, 0.03), (0.07, -0.38, 0.06)], [0.016, 0.012], 'skin_red', 4)
    if receiver:
        m.box((0, -0.38, 0.07), (0.05, 0.2, 0.06), 'red_lamp')


def _arm(m, bend, grip='open', receiver=False):
    """The whole arm in shoulder space, bent at the elbow."""
    _upper_arm(m)
    f = Mesh('forearm')
    _forearm(f, grip, receiver)
    m.merge(f, ELBOW, (-bend, 0, 0))


def _face(m, ink):
    """One face, looking down +z from the middle of the head."""
    m.blob((0, 0.12, 0.085), 1.0, ink, 2, 0.03, 2.0, 51, (0.095, 0.115, 0.07))
    m.box((0, 0.172, 0.142), (0.165, 0.035, 0.05), ink, euler=(-12, 0, 0))
    m.box((0, 0.125, 0.16), (0.035, 0.065, 0.045), ink, taper=0.55, euler=(-8, 0, 0))
    for side in (-1, 1):
        m.blob((side * 0.05, 0.115, 0.135), 0.032, ink, 1)
        m.blob((side * 0.044, 0.147, 0.14), 0.024, 'black', 1)
        m.tube([(side * 0.026, 0.066, 0.152), (side * 0.022, 0.03, 0.156)], [0.008, 0.0], 'bone', 4, caps=False)
    m.box((0, 0.04, 0.115), (0.12, 0.06, 0.08), ink, taper=0.8)
    m.box((0, 0.068, 0.155), (0.07, 0.012, 0.012), 'black')
    m.tube([(0, 0.02, 0.14), (0, -0.03, 0.15), (0, -0.075, 0.13)], [0.024, 0.014, 0.0], 'black', 5, caps=False)


FACES = ((0, 'crimson'), (66, 'bone'), (-66, 'soot'))     # front, his right (+x), his left


def _head(m):
    """His head about the top of his neck: one skull and three faces on it, the horns."""
    m.blob((0, 0.15, -0.025), 1.0, 'horn', 2, 0.04, 2.0, 52, (0.15, 0.15, 0.125))
    for yaw, ink in FACES:
        f = Mesh('face')
        _face(f, ink)
        m.merge(f, (0, 0, 0), (0, yaw, 0))
    for side in (-1, 1):
        path = [(side * 0.07, 0.26, -0.02), (side * 0.18, 0.32, -0.03), (side * 0.25, 0.43, 0.0), (side * 0.23, 0.56, 0.05), (side * 0.17, 0.63, 0.08)]
        m.tube(path, [0.05, 0.043, 0.032, 0.018, 0.0], 'bone_dark', 7, caps=False)


def _eyes(m):
    for yaw, _ in FACES:
        f = Mesh('eyes')
        for side in (-1, 1):
            f.blob((side * 0.044, 0.148, 0.155), 0.013, 'ember', 1)
        m.merge(f, (0, 0, 0), (0, yaw, 0))


def _legs(m, seated):
    """His hips and legs, cloven hooves, in the figure's space."""
    if seated:
        m.blob((0, SEAT_HIP, -0.02), 1.0, 'skin_red', 1, 0.05, 2.0, 61, (0.2, 0.12, 0.15))
        for side in (-1, 1):
            knee = (side * 0.16, 0.6, 0.47)
            m.tube([(side * 0.12, SEAT_HIP, 0.0), knee], [0.115, 0.085], 'skin_red', 7)
            m.blob(knee, 0.085, 'skin_red', 1)
            m.tube([knee, (side * 0.165, 0.32, 0.53), (side * 0.17, 0.09, 0.56)], [0.08, 0.065, 0.045], 'skin_red', 7)
            m.box((side * 0.17, 0.045, 0.59), (0.1, 0.09, 0.14), 'black', taper=0.85)
    else:
        m.blob((0, STAND_HIP, STAND_Z - 0.02), 1.0, 'skin_red', 1, 0.05, 2.0, 61, (0.2, 0.12, 0.15))
        for side in (-1, 1):
            knee = (side * 0.14, 0.52, STAND_Z + 0.05)
            m.tube([(side * 0.12, STAND_HIP - 0.02, STAND_Z), knee], [0.115, 0.085], 'skin_red', 7)
            m.blob(knee, 0.085, 'skin_red', 1)
            m.tube([knee, (side * 0.15, 0.3, STAND_Z - 0.02), (side * 0.16, 0.09, STAND_Z - 0.02)], [0.08, 0.065, 0.045], 'skin_red', 7)
            m.box((side * 0.16, 0.045, STAND_Z + 0.02), (0.1, 0.09, 0.14), 'black', taper=0.85)


# ---- his throne and the ice --------------------------------------------------------------------
def armrest_top():
    """The arms of the throne are as high as his forearms rest, frozen."""
    p = hand(FROZEN, 1)
    e = in_figure(FROZEN, ELBOW, 'arm', 1)
    return min(p[1], e[1]) - 0.075, (e[0] + p[0]) / 2


def _throne(m):
    """A rock-and-roll throne, in his units (his seated hips at the origin's height SEAT_HIP):
    amp cabinets for arms and for the back, amp heads over them, a fan of iron spikes on top, a
    skull on the front of each arm, and his red phone on the right one."""
    top, arm_x = armrest_top()
    m.box((0, 0.04, -0.02), (1.75, 0.08, 1.3), 'stone_dark')
    m.box((0, 0.3, -0.06), (0.8, 0.5, 0.62), 'stone_red')
    m.box((0, 0.56, -0.06), (0.74, 0.03, 0.58), 'velvet')
    for side in (-1, 1):
        x = side * (arm_x + 0.04)
        m.box((x, top / 2 + 0.04, 0.06), (0.3, top - 0.08, 0.84), 'amp')
        m.box((x, top / 2 + 0.03, 0.485), (0.26, top - 0.26, 0.012), 'grille')
        m.box((x, top - 0.02, 0.06), (0.31, 0.03, 0.85), 'chrome')
        m.blob((x, top - 0.1, 0.5), 0.065, 'bone', 1, 0.08, 1.5, 3, (1, 1.05, 1.15))
        for e in (-0.022, 0.022):
            m.blob((x + e, top - 0.09, 0.555), 0.014, 'pupil', 0)
    for col in (-1, 1):
        for row in range(3):
            c = (col * 0.215, 0.74 + row * 0.4, -0.44)
            m.box(c, (0.41, 0.38, 0.3), 'amp')
            m.box((c[0], c[1], -0.287), (0.36, 0.33, 0.012), 'grille')
    for col in (-1, 1):
        m.box((col * 0.215, 1.97, -0.44), (0.41, 0.16, 0.26), 'amp')
        m.box((col * 0.215, 1.97, -0.307), (0.36, 0.03, 0.012), 'chrome')
        for k in range(5):
            m.blob((col * 0.215 - 0.12 + 0.06 * k, 1.94, -0.305), 0.01, 'brass', 0)
    for i in range(11):
        a = math.radians(-75 + 15 * i)
        length = 0.55 + 0.35 * math.cos(a * 1.3)
        base = (math.sin(a) * 0.3, 2.04, -0.46)
        tip = (math.sin(a) * (0.3 + length * 0.8), 2.04 + math.cos(a) * length, -0.5)
        m.tube([base, lerp(base, tip, 0.5), tip], [0.035, 0.022, 0.0], 'iron', 5, caps=False)
    # The phone on the right arm (its receiver is apart: he picks it up).
    m.box((arm_x + 0.04, top + 0.035, -0.18), (0.13, 0.05, 0.1), 'red_lamp')


def _receiver(m):
    top, arm_x = armrest_top()
    m.box((arm_x + 0.04, top + 0.075, -0.18), (0.15, 0.03, 0.04), 'red_lamp')


def _throne_frost(m, rng):
    """Snow on the throne's tops and icicles off its arms, until it thaws."""
    top, arm_x = armrest_top()
    for side in (-1, 1):
        x = side * (arm_x + 0.04)
        m.box((x, top + 0.02, 0.06), (0.33, 0.04, 0.87), 'cloud')
        for k in range(6):
            m.tube([(x + rng.uniform(-0.12, 0.12), top, 0.495), (x + rng.uniform(-0.12, 0.12), top - rng.uniform(0.08, 0.22), 0.495)], [0.012, 0.0], 'sky', 4, caps=False)
    for col in (-1, 1):
        m.box((col * 0.215, 2.06, -0.44), (0.42, 0.03, 0.27), 'cloud')
        for k in range(5):
            x = col * 0.215 - 0.16 + 0.08 * k
            m.tube([(x, 1.89, -0.29), (x + 0.01, 1.89 - rng.uniform(0.1, 0.3), -0.29)], [0.014, 0.0], 'sky', 4, caps=False)
    m.box((0, 0.1, 0.36), (1.7, 0.03, 0.55), 'cloud')


def _ice(m, rng):
    """The block he is frozen into, to the waist: a lumpy core and crystals standing out of it."""
    m.blob((0, 0.36, 0.2), 1.0, 'sky', 2, 0.16, 1.6, 71, (0.86, ICE_TOP - 0.36 + 0.06, 0.66), floor=0.0)
    for i in range(46):
        a = rng.uniform(0, 2 * math.pi)
        r = math.sqrt(rng.uniform(0.15, 1.0))
        x, z = math.cos(a) * r * 0.9, 0.2 + math.sin(a) * r * 0.7
        h = (ICE_TOP + 0.05) * (1.1 - 0.75 * r * r) * rng.uniform(0.75, 1.15)
        tilt = (rng.uniform(-22, 22) + math.sin(a) * 20 * r, rng.uniform(0, 90), rng.uniform(-22, 22) - math.cos(a) * 20 * r)
        w = rng.uniform(0.08, 0.2)
        m.box((x, h / 2, z), (w, h, w * rng.uniform(0.7, 1.2)), rng.choice(('cloud', 'sky', 'white')), euler=tilt, taper=rng.uniform(0.15, 0.5))


def _cracks(m, rng):
    """Red cracks across the ice's front where his heart's heat comes through ('thaw_2')."""
    for i in range(9):
        a = math.radians(-70 + 140 * i / 8 + rng.uniform(-6, 6))
        pts = []
        for k in range(6):
            t = k / 5
            y = ICE_TOP - 0.02 - t * (ICE_TOP - 0.06)
            reach = 0.62 + 0.3 * t
            pts.append((math.sin(a) * 0.86 * reach + rng.uniform(-0.04, 0.04), y, 0.2 + math.cos(a) * 0.66 * reach + rng.uniform(-0.02, 0.02)))
        m.tube(pts, [0.012, 0.012, 0.01, 0.009, 0.006, 0.0], 'ember', 3, caps=False)


def _heart(m):
    m.blob((0, 0, 0), 0.055, 'ember', 2, 0.15, 3.0, 81, (1.0, 1.15, 0.8))


# ---- placing him ---------------------------------------------------------------------------
_PARTS = {}


def _prop(V, name, build):
    return A.prop(V, name, build)


def _mats(V):
    return {'skin': A.mat(V, 'Palette', (1, 1, 1), glow=(0.55, 0.12, 0.08), power=0.06, rough=0.5),
            'eyes': A.mat(V, 'Palette', (0, 0, 0), glow=(1.0, 0.45, 0.1), power=9.0, additive=True),
            'cold eyes': A.mat(V, 'Palette', (0, 0, 0), glow=(0.45, 0.75, 1.0), power=5.0, glow_tex=False, additive=True),
            'wing': A.mat(V, 'Palette', (1, 1, 1), glow=(0.35, 0.05, 0.05), power=0.25, rough=0.7, both=True),
            'throne': A.mat(V, 'Palette', (1, 1, 1), rough=0.6, metallic=0.2),
            'ice': A.mat(V, 'Palette', (0.75, 0.9, 1.05), glow=(0.35, 0.6, 1.0), power=0.35, rough=0.15, metallic=0.35),
            'frost': A.mat(V, 'Palette', (1, 1, 1), glow=(0.5, 0.65, 0.9), power=0.25, rough=0.5),
            'cracks': A.mat(V, 'Palette', (0, 0, 0), glow=(1.0, 0.3, 0.06), power=7.0, additive=True),
            'heart': A.mat(V, 'Palette', (0, 0, 0), glow=(1.0, 0.25, 0.05), power=5.0, additive=True)}


def _beat(e, **kw):
    d = {'Type': 'VenueBeat', 'Offset': [0.0, 0.0, 0.0]}
    for k, v in kw.items():
        d[k] = [float(c) for c in v] if isinstance(v, (tuple, list)) else v
    e.add(d)
    return e


def _rig(s, base, V, mats, label, stance, after, before, moves=(), cold=False, phone=False):
    """One way Satan moves, shown from after to before: the torso on his hips, the head on its
    neck, the arms on their shoulders (one mesh with the torso unless they move)."""
    g = P.between(s, base, label, after, before, 0.0)
    torso = s.entity('Torso', g, stance.hip(), stance.torso)
    if 'sway' in moves:
        _beat(torso, Turn=(0, 0, 5), Every=2.0, Sway=True, Calm=0.3)
    loose = bool({'drums', 'arms', 'beckon', 'phone'} & set(moves))
    key = {FROZEN: 'Frozen', JAMMING: 'Jamming', ON_THE_ARMS: 'OnTheArms', STANDING: 'Standing', ON_THE_PHONE: 'Phone'}[stance]

    def body(m):
        _torso(m)
        if not loose:
            for side, (r, bend) in zip((-1, 1), stance.arms):
                a = Mesh('arm')
                _arm(a, bend, 'fist' if stance is STANDING else 'open')
                m.merge(a, shoulder(side), r)
    A.model(s, torso, 'Body', _prop(V, 'SatanTorso' if loose else f'SatanTorso{key}', body), (0, 0, 0), (0, 0, 0), 1.0, mats['skin'])
    neck = s.entity('Neck', torso, NECK_AT, stance.head)
    if 'nod' in moves:
        _beat(neck, Turn=(13, 0, 0), Every=1.0, Calm=0.35)
    A.model(s, neck, 'Three faces', _prop(V, 'SatanHead', _head), (0, 0, 0), (0, 0, 0), HEAD, mats['skin'])
    A.model(s, neck, 'Eyes', _prop(V, 'SatanEyes', _eyes), (0, 0, 0), (0, 0, 0), HEAD, mats['cold eyes' if cold else 'eyes'], shadows=False)
    if loose:
        grip = 'fist' if moves and ('drums' in moves or 'arms' in moves) else 'open'
        for side, (r, bend) in zip((-1, 1), stance.arms):
            name = 'Left' if side < 0 else 'Right'
            arm = s.entity(f'{name} shoulder', torso, shoulder(side), r)
            beckons = 'beckon' in moves and side > 0
            if beckons:
                # He lifts his right hand toward the band, rolls it at them twice and lays it back.
                arm = P.play(s, arm, 'Reaches', 'encore_called', P.clip(V, 'SatanReaches', 150, [
                    P.track('Rotation', [(0, (0, 0, 0)), (22, (-38, 0, 6)), (118, (-38, 0, 6)), (150, (0, 0, 0))], 'SmoothStep')]))
            A.model(s, arm, 'Upper arm', _prop(V, 'SatanUpperArm', _upper_arm), (0, 0, 0), (0, 0, 0), 1.0, mats['skin'])
            elbow = s.entity(f'{name} elbow', arm, ELBOW, (-bend, 0, 0))
            if beckons:
                elbow = P.play(s, elbow, 'Beckons', 'encore_called', P.clip(V, 'SatanBeckons', 150, [
                    P.track('Rotation', [(0, (0, 0, 0)), (22, (14, 0, 0)), (46, (-40, 0, 0)), (70, (10, 0, 0)), (94, (-40, 0, 0)), (118, (10, 0, 0)), (150, (0, 0, 0))],
                            'SmoothStep')]))
            if 'drums' in moves or 'arms' in moves:
                _beat(elbow, Turn=(34, 0, 0), Trigger='Hit' if side > 0 else 'Accent', Calm=0.2)
            receiver = phone and side < 0
            fist = grip if not receiver else 'fist'
            A.model(s, elbow, 'Forearm', _prop(V, 'SatanForearm' + ('Phone' if receiver else fist.title()), lambda m, f=fist, rc=receiver: _forearm(m, f, rc)),
                    (0, 0, 0), (0, 0, 0), 1.0, mats['skin'])
    return g


def satan(s, h, V, feet):
    """Satan, his throne and the ice he is frozen into, his feet at feet (venue space). Returns
    the venue points the shots are framed on."""
    mats = _mats(V)
    rng = random.Random(66)
    base = s.entity('Satan (his scale)', h, feet, (0, 0, 0), (SCALE, SCALE, SCALE))
    A.model(s, base, 'Throne', _prop(V, 'RockThrone', _throne), (0, 0, 0), (0, 0, 0), 1.0, mats['throne'])
    A.model(s, P.between(s, base, 'Receiver', None, 'phone_call', 0.0), 'Receiver', _prop(V, 'ThroneReceiver', _receiver), (0, 0, 0), (0, 0, 0), 1.0, mats['throne'])
    A.model(s, P.between(s, base, 'Frost on the throne', None, 'thawed', 1.5, (0, 1.0, 0)), 'Frost', _prop(V, 'ThroneFrost', lambda m: _throne_frost(m, random.Random(67))),
            (0, 0, 0), (0, 0, 0), 1.0, mats['frost'], shadows=False)
    # The ice: cracks from 'thaw_2', and it melts down to nothing by 'thawed'.
    melt = int(TO_THAWED['thaw_2'] * 30)
    ice = P.between(s, base, 'The ice', None, 'thawed', 1.0)
    ice = P.play(s, ice, 'Melts', 'thaw_2', P.clip(V, 'SatanIceMelts', melt, [P.track('Scale', [(0, (1, 1, 1)), (150, (1.0, 0.94, 1.0)), (int(melt * 0.6), (0.96, 0.55, 0.95)),
                                                                                                    (melt, (0.9, 0.04, 0.9))], 'SmoothStep')]))
    A.model(s, ice, 'Ice', _prop(V, 'SatanIce', lambda m: _ice(m, random.Random(68))), (0, 0, 0), (0, 0, 0), 1.0, mats['ice'])
    A.model(s, P.between(s, ice, 'Cracks', 'thaw_2', None, 0.6, (0, ICE_TOP, 0.6)), 'Cracks', _prop(V, 'SatanIceCracks', lambda m: _cracks(m, random.Random(69))),
            (0, 0, 0), (0, 0, 0), 1.0, mats['cracks'], shadows=False)
    # Legs (seated until he stands).
    A.model(s, P.between(s, base, 'Seated legs', None, 'satan_stands', 0.0), 'Legs', _prop(V, 'SatanLegsSeated', lambda m: _legs(m, True)), (0, 0, 0), (0, 0, 0), 1.0, mats['skin'])
    A.model(s, P.between(s, base, 'Standing legs', 'satan_stands', None, 0.0), 'Legs', _prop(V, 'SatanLegsStanding', lambda m: _legs(m, False)), (0, 0, 0), (0, 0, 0), 1.0, mats['skin'])
    # The ways he moves.
    _rig(s, base, V, mats, 'Satan, frozen', FROZEN, None, 'thaw_2', cold=True)
    _rig(s, base, V, mats, 'Satan nods', FROZEN, 'thaw_2', 'thaw_3', ('nod',))
    _rig(s, base, V, mats, 'Satan rocks', FROZEN, 'thaw_3', 'thaw_4', ('nod', 'sway'))
    _rig(s, base, V, mats, 'Satan jams', JAMMING, 'thaw_4', 'encore_called', ('nod', 'sway', 'drums'))
    _rig(s, base, V, mats, 'Satan beckons', FROZEN, 'encore_called', 'satan_nods', ('nod', 'beckon'))
    _rig(s, base, V, mats, 'Satan nods along', FROZEN, 'satan_nods', 'satan_air_drums', ('nod', 'sway'))
    _rig(s, base, V, mats, 'Satan drums on the arms', ON_THE_ARMS, 'satan_air_drums', 'satan_stands', ('nod', 'sway', 'arms'))
    _rig(s, base, V, mats, 'Satan stands', STANDING, 'satan_stands', 'phone_call', ('nod', 'sway'))
    _rig(s, base, V, mats, 'Satan on the phone', ON_THE_PHONE, 'phone_call', None, ('phone',), phone=True)
    # His wings, beating on a loop all along: their wind is what freezes the place.
    wing = A.devil_wing(V)
    for label, after, before, stance in (('Wings', None, 'satan_stands', FROZEN), ('Wings, standing', 'satan_stands', None, STANDING)):
        g = P.between(s, base, label, after, before, 0.0)
        for side in (-1, 1):
            root = in_figure(stance, (side * 0.12, 0.5, -0.17))
            keys = [(0, (-6, 30, -14)), (45, (8, 42, 22)), (90, (-6, 30, -14))]
            if side < 0:
                keys = [(f, (x, 180 - y, -z)) for f, (x, y, z) in keys]
            beat = P.clip(V, 'SatanWingL' if side < 0 else 'SatanWingR', 90, [P.track('Rotation', keys, 'SmoothStep')])
            A.model(s, P.looping(s, g, 'Wing', beat, root), 'Wing', wing, (0, 0, 0), (0, 0, 0), 2.0, mats['wing'], shadows=False)
    # His heart: kindling at 'thaw_1', on the beats (out through his chest on each).
    for label, after, before, stance in (('Heart', 'thaw_1', 'satan_stands', FROZEN), ('Heart, standing', 'satan_stands', None, STANDING)):
        at = in_figure(stance, CHEST)
        g = P.between(s, base, label, after, before, 4.0 if after == 'thaw_1' else 0.0, at)
        e = A.model(s, g, 'Heart', _prop(V, 'SatanHeart', _heart), at, (0, 0, 0), 1.0, mats['heart'], shadows=False)
        _beat(e, Offset=(0, 0, 0.045), Sharp=True)
    face = add(feet, tuple(SCALE * c for c in in_figure(FROZEN, (0, 0.13 * HEAD, 0.06), 'head')))
    chest = add(feet, tuple(SCALE * c for c in in_figure(FROZEN, CHEST)))
    stand_face = add(feet, tuple(SCALE * c for c in in_figure(STANDING, (0, 0.13 * HEAD, 0.06), 'head')))
    phone_face = add(feet, tuple(SCALE * c for c in in_figure(ON_THE_PHONE, (0, 0.13 * HEAD, 0.06), 'head')))
    right_hand = add(feet, tuple(SCALE * c for c in hand(ON_THE_ARMS, 1)))
    return {'face': face, 'chest': chest, 'stand_face': stand_face, 'phone_face': phone_face, 'right_hand': right_hand,
            'feet': feet, 'ice_top': feet[1] + SCALE * ICE_TOP}


# ---- the floor, frozen ----------------------------------------------------------------------
def _posed(body, pose):
    """A crowd figure in pose from its low pieces (story_afterlife_people.figure's posing): its
    triangles, feet at the origin, facing +z."""
    hip = pose.hip()
    out = []

    def place(piece, fn):
        verts, _, faces = _read(body, piece, True)
        pts = [fn(v) for v in verts]
        for f in faces:
            for i in range(1, len(f) - 1):
                out.append((pts[f[0][0] - 1], pts[f[i][0] - 1], pts[f[i + 1][0] - 1]))
    place('Legs', _seat_legs if pose.seated else (lambda v: v))
    place('Torso', lambda v: _add(_rot(v, pose.torso), hip))
    place('Head', lambda v: _add(_rot(_add(_rot(v, pose.head), NECK), pose.torso), hip))
    for side, piece, (r, bend) in ((-1, 'ArmL', pose.arm_l), (1, 'ArmR', pose.arm_r)):
        o = (side * SHOULDER[0], SHOULDER[1], SHOULDER[2])
        place(piece, lambda v, r=r, b=bend, o=o: _add(_rot(_add(_rot(_bend_arm(v, b), r), o), pose.torso), hip))
    return out


_POSED = {}


def _statues(m, figures, rng):
    """Demons frozen stiff: each a little larger than the demon inside it, horns and all, on a
    crust of ice. figures: (body, pose, at, yaw, scale)."""
    for body, pose, at, yaw, scale in figures:
        key = (body, id(pose))
        if key not in _POSED:
            _POSED[key] = _posed(body, pose)
        k = 1.05 * scale
        f = Mesh('statue')
        for a, b, c in _POSED[key]:
            f.tri(a, b, c, 'white')
        for side in (-1, 1):
            f.tube([(side * 0.07, 1.63, 0.02), (side * 0.12, 1.8, 0.0), (side * 0.11, 1.95, -0.04)], [0.04, 0.03, 0.0], 'white', 4, caps=False)
        f.blob((0, 0.02, 0), 1.0, 'white', 0, 0.3, 2.0, rng.randrange(99), (0.36, 0.16, 0.36))
        m.merge(f, at, (0, yaw, 0), k)


def _drifts(m, tier, rng, centre):
    """Snow along one tier of the stands, both sides: heaped against the back, patchy at the lip."""
    r0, y, arc0, arc1 = tier
    seg, rows = 22, 3
    for side in (-1, 1):
        def at(i, j):
            deg = arc0 + (arc1 - arc0) * i / seg
            r = r0 + 0.15 + (A.TIER_STEP + 0.1) * j / rows
            p = A.terrace_point(centre, side, r, deg, 0.0)
            lift = 0.03 + 0.26 * (j / rows) ** 1.5 + 0.16 * (fbm3(p[0] * 0.35, y, p[2] * 0.35, 13) - 0.5)
            return (p[0], y + lift, p[2])
        for i in range(seg):
            for j in range(rows):
                q = [at(i, j), at(i + 1, j), at(i + 1, j + 1), at(i, j + 1)]
                m.face(q, 'cloud', outward=(0, 1, 0))


def _thaw_clip(V, delay, drop=2.8):
    """The statues (and the snow under them) slide down off the demons, delay seconds after the
    flag: as if the ice let go of them all at once."""
    d = int(round(delay * 30))
    return P.clip(V, f'Thaw_{d}', d + 80, [P.track('Position', [(0, (0, 0, 0)), (d, (0, 0, 0)), (d + 12, (0, -0.12, 0)), (d + 80, (0, -drop, 0))], 'SmoothStep')])


def thawed_clip(V, delay):
    """Where a tier's live demons wait: far under the floor until their statues start to slide
    (_thaw_clip), then at once in their places, inside the ice as it goes."""
    d = int(round(delay * 30))
    return P.clip(V, f'Thawed_{d}', d + 5, [P.track('Position', [(0, (0, -80, 0)), (d + 3, (0, -80, 0)), (d + 4, (0, 0, 0)), (d + 5, (0, 0, 0))])])


def frozen_crowd(s, frost, V, crowds, tiers, centre):
    """The stands' statues of ice and their snow, a Play group for each tier on its thaw flag.
    crowds: {'floor' or tier index: {'figures': [(body, pose, at, yaw, scale)],
    'blocks': [(prop path, ...)]}} (a block is a stands crowd mesh drawn again in ice)."""
    mats = _mats(V)
    statue = A.mat(V, None, (0.62, 0.78, 0.95), glow=(0.22, 0.42, 0.75), power=0.3, glow_tex=False, rough=0.22, metallic=0.3)
    for key in ['floor'] + list(range(len(tiers))):
        flag, delay = THAW_AT[key]
        crowd = crowds.get(key, {})
        g = P.play(s, frost, f'Frozen {"floor" if key == "floor" else f"tier {key + 1}"}', flag, _thaw_clip(V, delay))
        if crowd.get('figures'):
            A.model(s, g, 'Statues', _prop(V, f'Statues_{key}', lambda m, fs=crowd['figures'], k=key: _statues(m, fs, random.Random(str(k)))),
                    (0, 0, 0), (0, 0, 0), 1.0, statue, shadows=False)
        for path in crowd.get('blocks', ()):
            A.model(s, g, 'Statues', path, (0, 0, 0), (0, 0, 0), 1.0, statue, shadows=False)
        if key != 'floor':
            A.model(s, g, 'Snow', _prop(V, f'Drifts_{key}', lambda m, t=tiers[key], k=key: _drifts(m, t, random.Random(k), centre)),
                    (0, 0, 0), (0, 0, 0), 1.0, mats['frost'], shadows=False)


def _sheet(m, x0, x1, z0, z1, n, height, keep=None):
    m.grid(x0, x1, z0, z1, n, n, height, 'sky', keep=keep)


def frozen_floor(s, frost, V, centre, arena_radius, feet):
    """The ice over the lake of lava and the frost over the island, melting away; the cold air:
    snow and frost on the wind off his wings, down the stairs at the band; the cold light."""
    mats = _mats(V)
    lake = A.mat(V, 'Palette', (0.55, 0.7, 0.85), glow=(0.15, 0.35, 0.6), power=0.35, rough=0.12, metallic=0.4)
    # The lake: a sheet of ice over the lava, bumpy, so that as it sinks the lava breaks through
    # in patches ('thaw_3' to 'thawed').
    sink = int(TO_THAWED['thaw_3'] * 30)
    g = P.play(s, frost, 'The lake thaws', 'thaw_3', P.clip(V, 'LakeThaws', sink, [P.track('Position', [(0, (0, 0, 0)), (int(sink * 0.45), (0, -0.1, 0)),
                                                                                                       (int(sink * 0.85), (0, -0.32, 0)), (sink, (0, -0.7, 0))], 'SmoothStep')]))
    A.model(s, g, 'Frozen lake', _prop(V, 'FrozenLake', lambda m: _sheet(m, -80, 80, -86, 74, 72,
                                                                         lambda x, z: -1.7 + 0.2 * (fbm3(x * 0.07, 0, z * 0.07, 21) - 0.5) + 0.07 * (fbm3(x * 0.4, 1, z * 0.4, 22) - 0.5))),
            (0, 0, 0), (0, 0, 0), 1.0, lake, shadows=False)
    # The island: frost over the floor (the glowing cracks show again as it goes).
    sink = int(TO_THAWED['thaw_2'] * 30)
    g = P.play(s, frost, 'The frost melts', 'thaw_2', P.clip(V, 'FrostMelts', sink, [P.track('Position', [(0, (0, 0, 0)), (int(sink * 0.5), (0, -0.04, 0)),
                                                                                                         (sink, (0, -0.16, 0))], 'SmoothStep')]))
    A.model(s, g, 'Frost', _prop(V, 'IslandFrost', lambda m: m.grid(centre[0] - arena_radius, centre[0] + arena_radius, centre[2] - arena_radius, centre[2] + arena_radius,
                                                                    40, 40, lambda x, z: 0.005 + 0.11 * (fbm3(x * 0.3, 3, z * 0.3, 23) - 0.38), 'cloud',
                                                                    keep=lambda x, z: math.hypot(x - centre[0], z - centre[2]) < arena_radius * 0.8)),
            (0, 0, 0), (0, 0, 0), 1.0, mats['frost'], shadows=False)
    # The wind off his wings: snow and frost blowing down the stairs and over the band.
    wind = (100, 0, 0)          # the emitters' +y turned to blow toward +z, a little downward
    A.particles(s, frost, 'Snow on the wind', (0, 16, feet[2] + 6), wind, Shape='Box', BoxSize=[70, 22, 8], Lifetime=[5.0, 8.0], Speed=[7, 13], Size=[0.04, 0.1],
                StartColor=[0.9, 0.95, 1.0], StartColor2=[0.7, 0.82, 1.0], EndColor=[0.6, 0.75, 1.0], Intensity=1.4, Gravity=0.08, Drag=0.05, NoiseStrength=1.6,
                NoiseFrequency=0.3, Blend='Additive', EmissionRate=260, MaxParticles=1800, FadeIn=0.1)
    A.particles(s, frost, 'Snow past the band', (0, 5, -6), wind, Shape='Box', BoxSize=[26, 9, 4], Lifetime=[1.2, 2.0], Speed=[9, 15], Size=[0.02, 0.05],
                StartColor=[0.95, 0.97, 1.0], StartColor2=[0.75, 0.85, 1.0], EndColor=[0.7, 0.8, 1.0], Intensity=1.6, Gravity=0.1, Drag=0.0, NoiseStrength=2.0,
                Blend='Additive', EmissionRate=140, MaxParticles=320, Alignment='Stretched', StretchFactor=0.05, FadeIn=0.05)
    A.particles(s, frost, 'Frost on the wind', (0, 8, feet[2] + 8), wind, Shape='Box', BoxSize=[50, 10, 6], Lifetime=[6.0, 9.0], Speed=[4, 7], Size=[3.0, 7.0], EndSize=1.8,
                StartColor=[0.7, 0.8, 0.95], StartColor2=[0.55, 0.65, 0.85], EndColor=[0.45, 0.55, 0.75], StartAlpha=0.13, EndAlpha=0.0, Gravity=0.0, Drag=0.05,
                NoiseStrength=0.5, NoiseFrequency=0.2, Blend='Alpha', EmissionRate=9, MaxParticles=80, Texture=A.tex(V, 'Puff'), FadeIn=0.3)
    # The cold light: no show rig until the fire comes back, only this (plain lights), and beams.
    cold = (0.62, 0.78, 1.0)
    for i, x in enumerate((-4.5, 4.5)):
        at = (x, 8.5, -4.5)
        s.light(f'Cold key {i}', frost, at, 'Spot', cold, 1000.0 - 200 * i, 24, rot=_look(at, (x * 0.2, 1.5, 3.5)), inner=22, outer=42, fog=0.3)
    s.light('Cold fill', frost, (0, 9, 12), 'Point', (0.5, 0.62, 0.95), 500.0, 30)
    for i, (x, z) in enumerate(((-24, 10), (24, 10), (-21, -4), (21, -4))):
        at = (x, 9, z)
        s.light(f'Cold beam {i}', frost, at, 'Spot', (0.7, 0.85, 1.0), 3000.0, 50, rot=_look(at, (0, 2, 3.5)), inner=3, outer=7, show='Beam', group=i)
    for side in (-1, 1):
        s.light('Ice glow', frost, (side * 26, 1.0, -18), 'Point', (0.4, 0.6, 1.0), 700.0, 40)
        s.light('Ice glow', frost, (side * 30, 1.0, 22), 'Point', (0.4, 0.6, 1.0), 700.0, 40)
        # The frozen stands: a cold flood from high over the floor out across each side's tiers,
        # and one up the far end of them (without these the wide and the thaw's shots had the
        # nine tiers of frozen demons as a black mass).
        for k, (z, to_z) in enumerate(((8.0, 2.0), (-6.0, -14.0))):
            at = (side * 3.0, 30.0, z)
            s.light(f'Cold flood {k}', frost, at, 'Spot', (0.6, 0.75, 1.0), 16000.0 if k == 0 else 11000.0, 70,
                    rot=_look(at, (side * 29.0, 5.0, to_z)), inner=24, outer=46, fog=0.05)
    # Satan in the cold: lit from below, off the ice, and from behind.
    at = (0, 2.5, -13)
    s.light('Satan, from the ice', frost, at, 'Spot', (0.65, 0.8, 1.0), 7000.0, 55, rot=_look(at, (0, feet[1] + 11, feet[2])), inner=16, outer=30, fog=0.08)
    s.light('Satan, rim', frost, (0, feet[1] + 22, feet[2] - 12), 'Point', (0.5, 0.7, 1.0), 5000.0, 30)
    # They hit the snow: a burst of it round the kit on the landing.
    land = P.between(s, frost, 'The landing', 'landed', None, 0.0)
    # (Against the frost a white burst is lost: ice shards glinting blue, thrown up high against
    # the dark of the stands, a grey-blue cloud of powder, and a cold flash off the ice.)
    A.particles(s, land, 'Ice thrown up', (0, 0.3, 3.6), Shape='Cone', ConeAngle=55, ShapeRadius=2.4, Lifetime=[1.6, 3.2], Speed=[4, 11],
                Size=[0.05, 0.12], StartColor=[0.55, 0.85, 1.0], StartColor2=[0.35, 0.6, 1.0], EndColor=[0.2, 0.4, 0.9], Intensity=6.0, Gravity=0.9, Drag=0.5,
                NoiseStrength=0.8, Blend='Additive', EmissionRate=0, BurstCount=320, MaxParticles=340, Looping=False, Duration=30.0, Alignment='Stretched',
                StretchFactor=0.05)
    A.particles(s, land, 'Powder thrown up', (0, 0.4, 3.6), Shape='Sphere', ShapeRadius=2.2, Lifetime=[3.0, 5.0], Speed=[2, 6], Size=[1.5, 3.2], EndSize=2.4,
                StartColor=[0.45, 0.55, 0.72], StartColor2=[0.35, 0.44, 0.6], EndColor=[0.3, 0.38, 0.52], StartAlpha=0.6, EndAlpha=0.0, Gravity=0.15, Drag=0.8,
                NoiseStrength=0.6, Blend='Alpha', Lit=False, EmissionRate=0, BurstCount=46, MaxParticles=46, Looping=False, Duration=30.0, Texture=A.tex(V, 'Puff'), FadeIn=0.05)
    flash = P.play(s, land, 'Cold flash', 'landed', P.clip(V, 'LandingFlash', 60, [P.track('Position', [(0, (0, 0, 0)), (1, (0, 0, 0)), (45, (0, -60, 0)), (60, (0, -60, 0))])]))
    s.light('Cold flash', flash, (0, 2.5, 3.6), 'Point', (0.55, 0.75, 1.0), 900.0, 14, fog=0.2)


def thaw_lights(s, h, V, chest):
    """Warm light coming back: his heart's, from 'thaw_1' on. (Kept low: the fire's own light is
    on him from 'thawed', and more of it in front of him washes him out.)"""
    for flag, power, reach, size, fade in (('thaw_1', 300.0, 10, 0.5, 4.0),):
        g = P.between(s, h, f'Heart light ({flag})', flag, None, fade, chest)
        s.light('Heart light', g, (chest[0], chest[1] - 1.0, chest[2] + 6.0), 'Point', (1.0, 0.3, 0.08), power, reach, fog=0.1)
        A.glow_card(s, g, V, 'Heart glow', (chest[0], chest[1], chest[2] + 1.3), size, (1.0, 0.3, 0.06), 0.35)


def guests(s, fire, V, tiers, centre, rng):
    """At 'thawed', the spirits they fell past drop into the stands for the party: shades in the
    circles' colours among the demons, dancing to the beat as well as the playing lets them."""
    inks = ('marble_shade', 'crimson', 'bone', 'gold', 'steel', 'stone_red', 'bone_dark', 'cloud', 'sky')
    for j in range(3):
        def build(m, j=j):
            r = random.Random(900 + j)
            for k in range(3, 9):
                r0, y, arc0, arc1 = tiers[k]
                for side in (-1, 1):
                    for i in range(3):
                        deg = r.uniform(arc0 + 8, arc1 - 8)
                        at = A.terrace_point(centre, side, r0 + r.uniform(0.6, 1.8), deg, y)
                        yaw = math.degrees(math.atan2(centre[0] - at[0], centre[2] + 1.5 - at[2])) + r.uniform(-20, 20)
                        f = CIR.soul(r.choice(inks), r.choice(('reach', 'reach', 'fly', 'push')))
                        m.merge(f, at, (0, yaw, 0), 1.35)
                        m.merge(f.head, at, (0, yaw, 0), 1.35)
        delay = int(30 * (0.4 + 1.1 * j))
        drop = P.clip(V, f'GuestsDrop{j}', delay + 60, [P.track('Position', [(0, (0, 40, 0)), (delay, (0, 40, 0)), (delay + 60, (0, 0, 0))], 'SmoothStep')])
        g = P.play(s, fire, 'The spirits come down', 'thawed', drop)
        e = A.model(s, g, 'Spirits', _prop(V, f'Guests{j}', build), (0, 0, 0), (0, 0, 0), 1.0,
                    A.mat(V, 'Palette', (1, 1, 1), glow=(0.55, 0.65, 0.9), power=0.55), shadows=False)
        _beat(e, Offset=(0, -0.22, 0), Every=1.0, Phase=0.5 * (j % 2), Calm=0.25)


def eruption(s, h, V):
    """The fire back at a stroke on 'thawed': lava thrown up out of the lake round the island.
    (Only in Free Bird: in Bat Country 'encore_called' is set from the start.)"""
    g = P.between(s, h, 'The eruption', 'thawed', 'encore_called', 0.0)
    for i, (x, z) in enumerate(((-24, -14), (25, -12), (-30, 14), (31, 16), (0, 26), (-14, -34), (15, -34))):
        A.particles(s, g, f'Lava thrown up {i}', (x, -1.5, z), Shape='Cone', ConeAngle=18, ShapeRadius=1.5, Lifetime=[1.6, 3.0], Speed=[14, 26], Size=[0.15, 0.45],
                    StartColor=[1.0, 0.75, 0.3], StartColor2=[1.0, 0.35, 0.05], EndColor=[0.6, 0.06, 0.01], Intensity=7.0, Gravity=1.0, Drag=0.1,
                    NoiseStrength=0.4, Blend='Additive', EmissionRate=0, BurstCount=220, MaxParticles=240, Looping=False, Duration=30.0, FadeIn=0.02)
        A.particles(s, g, f'Steam {i}', (x, -1.0, z), Shape='Cone', ConeAngle=30, ShapeRadius=3.0, Lifetime=[3.0, 5.0], Speed=[4, 9], Size=[3.0, 6.0], EndSize=2.0,
                    StartColor=[0.6, 0.25, 0.12], StartColor2=[0.4, 0.15, 0.08], EndColor=[0.15, 0.06, 0.04], StartAlpha=0.35, EndAlpha=0.0, Gravity=-0.1, Drag=0.4,
                    Blend='Alpha', EmissionRate=0, BurstCount=26, MaxParticles=26, Looping=False, Duration=30.0, Texture=A.tex(V, 'Puff'), FadeIn=0.1)


# ---- the shots ------------------------------------------------------------------------------
def shots(shot, s, marks, pts, z0, top_y, zt, step):
    """The floor's story shots, Free Bird's from the landing on and all of Bat Country's. shot is
    make_story_afterlife.shot. He is huge, so he sits high in the picture, over where the note
    highway has faded; a subject lower down is led to one side of it (lead)."""
    F, H = pts['face'], pts['chest']
    SF, PF, RH = pts['stand_face'], pts['phone_face'], pts['right_hand']

    def up(p, dy):
        return (p[0], p[1] + dy, p[2])
    # Free Bird. They hit the snow: low by the kick drum as it goes up round them.
    shot(s, marks, 'landed', (2.4, 0.45, 1.2), (0.2, 0.7, 4.4), 52, 4, hand=True, lead='r', end=((2.8, 1.2, 0.6), (0.2, 1.1, 4.4), 56))
    # The frozen amphitheatre, wide, from over the band: him towering over the dais.
    shot(s, marks, 'frozen_wide', (15, 7, 19), up(F, -2), 62, 10, lead='r', end=((9, 11, 24), up(F, -1), 58))
    # His three faces.
    shot(s, marks, 'satan_faces', (F[0] + 6, F[1] - 2, F[2] + 18), F, 56, 6, lead='l', end=((F[0] + 4.5, F[1] - 1.5, F[2] + 15), F, 50))
    # The heart kindles.
    shot(s, marks, 'thaw_1', (H[0] - 7, H[1] - 3, H[2] + 16), H, 58, 6, focus=True, lead='r', end=((H[0] - 5.5, H[1] - 2.5, H[2] + 13), H, 52))
    # The ice cracks, and he nods: from the side of the island, him on the left and the stands
    # across the floor on the right, thawing tier by tier, the camera only a little tipped up
    # (from the head of the stairs, or tipped up at him from close, half the picture was the
    # dark of the cavern over the stands).
    shot(s, marks, 'thaw_2', (11, 5.5, 4), up(F, -9), 54, 6, lead='l', end=((10, 5.0, 2.0), up(F, -8), 52))
    # The thaw going up the stands, across the floor from one side to the other (until thaw_4's
    # cue, a second after its eight: no cut away for that second).
    shot(s, marks, 'thaw_3', (-17, 13, -2), (26, 5, 4), 58, 9.05, end=((-15, 13, 4), (24, 6, -6), 58))
    # He jams: from behind the drummer, low and well back, the band low in the picture and him
    # high over them. (Closer and aimed at his face, the band fell out of the bottom of it.)
    shot(s, marks, 'thaw_4', (2.2, 2.0, 14.5), up(F, -8), 58, 6, lead='l', end=((1.6, 1.8, 12.5), up(F, -7), 60))
    # Fire and brimstone: high and wide over the lake as it erupts.
    shot(s, marks, 'thawed', (24, 22, 24), H, 64, 8, lead='l', end=((20, 17, 27), H, 60))
    # (Nine seconds: hell_wide's cue comes nine after this one's, and the crane has to be at the
    # top by then, not three quarters of the way up.)
    shot(s, marks, 'stairs_reveal', (0.6, 0.5, -2.6), (0, 3.0, z0 - 3), 46, 9.05,
         via=[((1.2, 3.2, z0 - 3.0), (0, 9.0, z0 - 14.0), 48), ((-1.2, top_y + 1.0, zt + 5.0), up(F, -2), 50)],
         end=((0.0, top_y + 2.5, zt + 9.0), up(F, 0), 58), lead='l')
    shot(s, marks, 'hell_wide', (27, 21, 27), H, 58, 12, lead='l', via=[((35, 19, 6), H, 60)], end=((24, 13, -15), H, 62))
    # The encore: his hand rolls toward the band.
    shot(s, marks, 'encore_called', (F[0] + 11, F[1] - 5, F[2] + 18), (F[0] + 2, F[1] - 3.5, F[2] + 4), 66, 6, lead='l',
         end=((F[0] + 9, F[1] - 4.5, F[2] + 15), (F[0] + 1.5, F[1] - 3, F[2] + 3), 62))
    # Bat Country. From his throne looking down, over his shoulder.
    shot(s, marks, 'throne_view', (F[0] + 4.2, F[1] + 0.6, F[2] - 1.0), (0, 1.0, 3.6), 34, 8, lead='r', end=((F[0] + 3.6, F[1] - 1.2, F[2] + 2.5), (0, 1.0, 3.6), 26))
    shot(s, marks, 'demon_catch', (step[0] + 1.9, step[1] + 0.5, step[2] + 2.2), (step[0], step[1] + 0.7, step[2]), 36, 4.5, hand=True, focus=True, lead='l',
         end=((step[0] + 1.3, step[1] + 0.9, step[2] + 2.6), (step[0] + 0.3, step[1] + 1.2, step[2] - 0.4), 32))
    # Each return to the riff a step closer to him: head-on, nodding along; from the kit; up the
    # stairs.
    shot(s, marks, 'satan_nods', (0, F[1] + 0.3, F[2] + 16), F, 54, 6, focus=True, lead='r', end=((0, F[1], F[2] + 13), F, 50))
    shot(s, marks, 'closer_1', (-2.5, 2.8, 9.0), up(F, -4), 50, 6, lead='r', end=((-2.0, 3.2, 8.0), up(F, -3.5), 48))
    shot(s, marks, 'cavern_orbit', (7.0, 1.3, 10.8), up(H, -4), 46, 10, lead='r', via=[((0.5, 1.0, 12.5), up(H, -3), 48)], end=((-7.0, 1.8, 10.8), up(H, -2), 50))
    shot(s, marks, 'satan_air_drums', (RH[0] + 11, RH[1] + 1, RH[2] + 13), lerp(RH, F, 0.35), 60, 6, hand=True, lead='l',
         end=((RH[0] + 9, RH[1] + 1.5, RH[2] + 11), lerp(RH, F, 0.4), 56))
    shot(s, marks, 'closer_2', (-3.5, 6.5, -13), up(F, -1), 46, 6, lead='r', end=((-3.0, 7.5, -15), up(F, -1), 44))
    shot(s, marks, 'satan_stands', (9, 10, -10), up(SF, -5), 68, 6, lead='l', end=((12, 8, -2), up(SF, -4), 70))
    shot(s, marks, 'phone_call', (-7, PF[1] - 2, PF[2] + 24), up(PF, -2), 52, 6, lead='r', end=((-6, PF[1] - 3, PF[2] + 21), up(PF, 1), 56))
    shot(s, marks, 'smoke_rises', (1.3, 0.25, 3.4), (0.1, 0.5, 4.6), 40, 20, hand=True, via=[((1.6, 0.6, 2.2), (0, 4, 4.4), 58)], end=((1.2, 0.5, 1.8), (0, 60, 3.6), 70))
