"""The lower circles of Free Bird's fall (story_afterlife_circles.py): the sixth to the ninth,
Heresy, Violence, Fraud and Treachery, from the burning city of Dis down to the ice of Cocytus.

Each maker returns (period, dressing, glows) the way the upper circles' do, and is called with
the circle's winding set (lift), so spol() and put() follow its ledges. What moves on its own is
dressed through the circle-denizen contract (Dress.crowd, Dress.piece): a crowd is a group of
figures that moves as one, on a VenueBeat, and is shown or hidden by how well the player is
playing (VenueMood); a piece is one thing with a pivot of its own (an iron maiden swinging from
the top of her chain, a tree lashing from its root, a demon's whip arm). The mood is 0 when the
player is missing everything and 1 when they are hitting it all: a 'Good' crowd is there only
while it is high, a 'Bad' one only while it is low, and Calm is the share of a beat's move left
at the worst playing, so the damned that only move for a good player have a low one.
"""
import math
import os
import sys

# Run as a script (story_afterlife_circles.py --manifest), the circles module is __main__: this
# module has to use that one (its winding, its Dress), not a second copy of it.
if 'story_afterlife_circles' not in sys.modules and os.path.basename(getattr(sys.modules.get('__main__'), '__file__', '') or '') == 'story_afterlife_circles.py':
    sys.modules['story_afterlife_circles'] = sys.modules['__main__']

from story_afterlife_circles import Dress, Folk, OPEN, arc, flame, ledge, put, soul, spol, _fiend
from story_afterlife_mesh import Mesh


# ---- placing ------------------------------------------------------------------------------------
def face_in(a, yaw=0.0):
    """The rest rotation (degrees) of a piece at angle a about the axis that faces it the way put()
    faces what it places: its +z toward the axis, +x along the ring; turned yaw about its up."""
    return (0.0, round(math.degrees(math.atan2(-math.cos(a), -math.sin(a))) + yaw, 3), 0.0)


def at(a, r, y):
    """A piece's position: on the ring at angle a, radius r, height y, the ledges' winding included."""
    return tuple(round(c, 3) for c in spol(a, r, y))


def turned(src, euler=(0, 0, 0), pos=(0, 0, 0), scale=1.0):
    """A copy of a figure (its head too) turned, moved and scaled."""
    return Folk(src.name).merge(src, pos, euler, scale)


# The horseshoe's wide part, in radians: a band of ground narrower than the ledge stays in it.
SHOE = (math.radians(OPEN[1] + 10.0), math.radians(OPEN[0] + 350.0))


def band(m, y, r0, r1, ink, steps=40, gaps=None):
    """A strip of ground (a river, a ring of sand) round the horseshoe between radii r0 and r1, its
    top at y, winding with the ledges. gaps(i) -> True leaves step i out (a dashed streak)."""
    a0, a1 = SHOE
    for i in range(steps):
        if gaps and gaps(i):
            continue
        u0, u1 = a0 + (a1 - a0) * i / steps, a0 + (a1 - a0) * (i + 1) / steps
        m.face([spol(u0, r0, y), spol(u1, r0, y), spol(u1, r1, y), spol(u0, r1, y)], ink, outward=(0, 1, 0))


def chain(m, top, length, ink='iron', pitch=1.15, width=0.34, bar=0.055):
    """A chain hanging straight down from top, length long: links of alternating turn."""
    n = max(1, int(math.ceil(length / pitch)))
    for i in range(n):
        cy = top[1] - length * (i + 0.5) / n
        loop = []
        for k in range(7):
            t = 2 * math.pi * k / 6
            x, h = width / 2 * math.cos(t), pitch * 0.64 * math.sin(t)
            loop.append((top[0] + (x if i % 2 == 0 else 0.0), cy + h, top[2] + (0.0 if i % 2 == 0 else x)))
        m.tube(loop, bar, ink, 3, caps=False)


def oval(m, c, rings, ink, sides=10, depth=0.75, cap=True):
    """A body of oval rings stacked down from c: rings are (half width, how far down)."""
    loops = [[(c[0] + w * math.cos(2 * math.pi * i / sides), c[1] - d, c[2] + w * depth * math.sin(2 * math.pi * i / sides)) for i in range(sides)]
             for w, d in rings]
    m.loft(loops, ink, cap_end=cap)


# ---- figures ------------------------------------------------------------------------------------
def man(ink, hands=None, feet=None, lean=0.0, head_ink=None, head=True, elbows=0.09, girth=1.0):
    """A bare figure 1.8 high on the origin facing +z, with legs (soul() is robed): hands and feet
    are where they reach to (shoulders at y 1.42, hips at 0.95); lean tips him forward (degrees)."""
    t = Folk('man')
    t.tube([(0, 0.92, 0), (0, 1.25, 0.03), (0, 1.47, 0.0)], [0.16 * girth, 0.19 * girth, 0.14 * girth], ink, 6)
    feet = feet or ((-0.14, 0.0, 0.03), (0.14, 0.0, 0.03))
    for side, f in zip((-1, 1), feet):
        hip = (side * 0.1, 0.95, 0.0)
        knee = ((hip[0] + f[0]) / 2, (hip[1] + f[1]) / 2, (hip[2] + f[2]) / 2 + 0.07)
        t.tube([hip, knee, f], [0.085 * girth, 0.07, 0.05], ink, 4, caps=False)
    hands = hands or ((-0.3, 0.84, 0.06), (0.3, 0.84, 0.06))
    for side, h in zip((-1, 1), hands):
        sh = (side * 0.21, 1.42, 0.0)
        elbow = ((sh[0] + h[0]) / 2 + side * elbows, (sh[1] + h[1]) / 2 - 0.04, (sh[2] + h[2]) / 2)
        t.tube([sh, elbow, h], [0.06, 0.05, 0.045], ink, 4, caps=False)
    if head:
        t.head.blob((0, 1.63, 0.02), 0.13, head_ink or ink, 0)
    return turned(t, (lean, 0, 0)) if lean else t


# Arms for man(): (left hand, right hand).
ARMS = {
    'down': ((-0.3, 0.84, 0.06), (0.3, 0.84, 0.06)),
    'up': ((-0.45, 2.15, 0.1), (0.45, 2.15, 0.1)),          # both up: rocking out
    'fist': ((-0.3, 0.9, 0.1), (0.22, 2.2, 0.12)),          # one fist pumping
    'claw': ((-0.42, 1.5, 0.42), (0.42, 1.55, 0.4)),        # reaching out in front
    'face': ((-0.08, 1.6, 0.2), (0.08, 1.6, 0.2)),          # hands to the face
    'swing': ((-0.25, 0.95, 0.35), (0.25, 0.9, -0.3)),      # walking
    'scratch': ((0.12, 1.25, 0.2), (-0.14, 1.05, 0.18)),    # clawing at his own skin
}
STRIDE = ((-0.13, 0.0, -0.32), (0.13, 0.0, 0.34))


def horned(src, ink='horn', wings=None, tail='skin_red'):
    """src with a demon's horns on its head (and wings, and a tail)."""
    t = turned(src)
    for side in (-1, 1):
        t.head.tube([(side * 0.08, 1.72, 0.03), (side * 0.17, 1.86, 0.0), (side * 0.15, 2.0, -0.08)], [0.05, 0.035, 0.0], ink, 4, caps=False)
        if wings:
            t.face([(side * 0.15, 1.38, -0.15), (side * 1.4, 2.25, -0.55), (side * 1.15, 1.0, -0.5)], wings, both=True)
            t.face([(side * 0.15, 1.38, -0.15), (side * 1.15, 1.0, -0.5), (side * 0.55, 0.6, -0.35)], wings, both=True)
    if tail:
        t.tube([(0, 0.95, -0.12), (0, 0.55, -0.55), (0.1, 0.25, -0.9), (0.25, 0.35, -1.15)], [0.05, 0.04, 0.03, 0.0], tail, 4, caps=False)
    return t


def skeleton(pose='dance'):
    """The bones of one of the violent against God on the burning sand, 1.8 high, facing +z:
    'dance' (arms up, a knee lifted) or 'dead' (arms flung out, to lie on its back)."""
    t = Folk('skeleton')
    ink = 'bone'
    t.tube([(0, 0.9, -0.02), (0, 1.2, -0.05), (0, 1.5, -0.01)], 0.04, ink, 3, caps=False)
    for h, r in ((1.38, 0.17), (1.24, 0.16)):       # ribs
        hoop = [(r * math.cos(2 * math.pi * k / 6), h, r * 0.8 * math.sin(2 * math.pi * k / 6)) for k in range(7)]
        t.tube(hoop, 0.03, ink, 3, caps=False)
    t.box((0, 0.95, 0), (0.34, 0.14, 0.18), ink)    # pelvis
    t.box((0, 1.45, 0), (0.44, 0.06, 0.08), ink)    # collar bones
    if pose == 'dance':
        hands, feet = ((-0.5, 2.1, 0.15), (0.42, 2.2, 0.05)), ((-0.15, 0.0, 0.0), (0.2, 0.55, 0.3))
    else:
        hands, feet = ((-0.7, 1.4, 0.05), (0.75, 1.2, 0.0)), ((-0.25, 0.0, 0.0), (0.2, 0.0, 0.05))
    for side, f in zip((-1, 1), feet):
        hip = (side * 0.12, 0.92, 0.0)
        knee = ((hip[0] + f[0]) / 2, (hip[1] + f[1]) / 2 + (0.15 if f[1] > 0.3 else 0.0), (hip[2] + f[2]) / 2 + 0.12)
        t.tube([hip, knee, f], 0.035, ink, 3, caps=False)
    for side, h in zip((-1, 1), hands):
        sh = (side * 0.22, 1.44, 0.0)
        el = ((sh[0] + h[0]) / 2 + side * 0.1, (sh[1] + h[1]) / 2, (sh[2] + h[2]) / 2)
        t.tube([sh, el, h], 0.03, ink, 3, caps=False)
    t.head.blob((0, 1.66, 0.02), 0.14, ink, 0, scale=(0.9, 1.05, 1.0))
    t.head.box((0, 1.55, 0.06), (0.15, 0.06, 0.12), ink)                     # the jaw, hanging open
    t.head.box((0, 1.69, 0.13), (0.17, 0.05, 0.03), 'black')                 # the eye sockets
    return t


def harpy(pose='perch'):
    """A harpy: a woman's head and breast on a vulture's body, great ragged wings, talons.
    'perch': clinging, wings up to strike; 'fly': wings spread wide, flung back."""
    t = Folk('harpy')
    t.blob((0, 0.75, 0), 0.42, 'bone_dark', 0, scale=(0.75, 1.15, 0.85))
    t.blob((0, 1.15, 0.12), 0.2, 'skin_red', 0, scale=(1.0, 0.8, 0.8))      # the breast
    t.head.blob((0, 1.45, 0.16), 0.15, 'bone_dark', 0)
    t.head.tube([(0, 1.55, 0.08), (0, 1.4, -0.2), (0.05, 1.1, -0.3)], [0.13, 0.1, 0.0], 'black', 4, caps=False)    # hair
    up = 1.0 if pose == 'perch' else 0.25
    for side in (-1, 1):
        root = (side * 0.25, 1.05, -0.05)
        tip = (side * 1.7, 1.05 + 1.3 * up, -0.4)
        elbow = (side * 0.95, 1.2 + 0.9 * up, -0.1)
        # Ragged: three feathered fingers along the trailing edge.
        for k, (dx, dy) in enumerate(((0.0, 0.0), (-0.35, -0.55), (-0.7, -0.9))):
            t.face([root, elbow, (tip[0] + side * dx, tip[1] + dy, tip[2])], 'bone_dark' if k == 0 else 'grille', both=True)
        t.face([root, (side * 0.5, 0.5, -0.2), (side * 1.0, 0.75 + 0.3 * up, -0.35)], 'wing_dark', both=True)
        foot = (side * 0.15, 0.1, 0.35 if pose == 'perch' else -0.2)
        t.tube([(side * 0.12, 0.5, 0.05), foot], 0.05, 'bone_dark', 3, caps=False)
        for k in (-1, 0, 1):
            t.tube([foot, (foot[0] + k * 0.1, foot[1] - 0.1, foot[2] + 0.18)], [0.03, 0.0], 'horn', 3, caps=False)
    t.face([(-0.18, 0.5, -0.2), (0.18, 0.5, -0.2), (0.0, 0.15, -0.85)], 'wing_dark', both=True)                 # tail
    return t


# ---- 6. Heresy ----------------------------------------------------------------------------------
def maiden(drop, size=1.2):
    """An iron maiden hanging from her chain: the pivot, the chain's top, at the origin, the
    maiden drop metres under it facing +z, size times a man's height and a half. Returns her
    (chain, iron and the window in her door) and the damned in her (the face looking out of the
    window, mouth open, and the hands clawing out of her sides) as two meshes in the same space:
    the shots frame the faces."""
    t, f = Mesh('maiden'), Mesh('maiden_face')
    chain(t, (0, 0, 0), drop - 0.1, 'iron')
    y0 = -drop
    s = size
    t.tube([(0, y0 + 0.12, -0.12 * s), (0, y0 + 0.22, 0), (0, y0 + 0.12, 0.12 * s), (0, y0 - 0.02, 0)], 0.04, 'iron', 3, caps=False)    # the ring she hangs by
    body = [(0.0, 0.0), (0.17, 0.04), (0.27, 0.16), (0.3, 0.34), (0.26, 0.55), (0.25, 0.62), (0.44, 0.8), (0.48, 1.1), (0.45, 1.5), (0.4, 1.9),
            (0.35, 2.3), (0.31, 2.6), (0.29, 2.72)]
    oval(t, (0, y0, 0), [(w * s, d * s) for w, d in body], 'grille')
    for d, w in ((0.8, 0.44), (1.5, 0.45), (2.3, 0.35)):      # bands of hotter iron
        oval(t, (0, y0 - d * s + 0.06, 0), [(w * s * 1.05, 0.0), (w * s * 1.05, 0.12)], 'rail', cap=False)
    face = (0, y0 - 0.36 * s, 0.22 * s)
    f.blob(face, 0.19 * s, 'bone', 1, scale=(0.85, 1.15, 0.8))
    for side in (-1, 1):
        f.blob((face[0] + side * 0.07 * s, face[1] + 0.06 * s, face[2] + 0.13 * s), 0.045 * s, 'black', 0)
    f.blob((face[0], face[1] - 0.095 * s, face[2] + 0.13 * s), 0.065 * s, 'black', 0, scale=(0.9, 1.4, 0.5))     # screaming
    frame = [(0.25 * s * math.cos(2 * math.pi * k / 8), face[1] + 0.3 * s * math.sin(2 * math.pi * k / 8), 0.27 * s) for k in range(9)]
    t.tube(frame, 0.04 * s, 'steel_dark', 3, caps=False)
    for side in (-1, 1):
        f.box((side * 0.035 * s, face[1] - 0.5 * s, 0.33 * s), (0.045 * s, 0.5 * s, 0.03 * s), 'blood')                # running from under her
        h = y0 - 1.1 * s
        f.tube([(side * 0.42 * s, h, 0.08 * s), (side * 0.66 * s, h + 0.12 * s, 0.2 * s), (side * 0.74 * s, h + 0.3 * s, 0.24 * s)], [0.055 * s, 0.05 * s, 0.03 * s],
               'bone', 4, caps=False)
    for x in (-0.15, 0.15):     # the spikes through her feet
        t.tube([(x * s, y0 - 2.6 * s, 0), (x * s, y0 - 3.05 * s, 0.04)], [0.06 * s, 0.0], 'iron', 3, caps=False)
    return t, f


def maiden_heat(drop, size=1.2):
    """The glow of a maiden's iron cooking from the feet up, in the same space as maiden(): a
    shell just outside her lower half, brightest at the feet."""
    t = Mesh('heat')
    s = size
    rings = [(0.45, 1.45), (0.4, 1.9), (0.35, 2.3), (0.31, 2.6), (0.29, 2.72)]
    oval(t, (0, -drop, 0), [(w * s * 1.06, d * s) for w, d in rings[:3]], 'crimson', cap=False)
    oval(t, (0, -drop, 0), [(w * s * 1.06, d * s) for w, d in rings[2:]], 'ember')
    return t


def heresy(rng):
    """The city of Dis, red hot: its iron wall with the fallen angels jeering from the top of it,
    iron maidens hung out over the drop on chains from gibbets along the wall, the face of one of
    the damned in each; and under them the heretics' tombs standing open, each with its fire.
    Played well, the maidens swing to the song; played badly they hang still over the tombs,
    and the fires flare up at them (and leap higher at every miss)."""
    period = 80.0
    m, g = Dress(), Mesh('g')
    # The wall of the city (passed first).
    y = 60.0
    ledge(m, y, 11.6, 'iron', thick=1.6, seed=7, jag=0.2)
    spots = arc(26)
    for i, a in enumerate(spots):
        if i % 5 == 2:
            tower = Mesh('tower').box((0, 8.0, 0), (3.2, 16.0, 3.2), 'iron', taper=0.85)
            for k in range(4):
                tower.box((((k % 2) * 2 - 1) * 1.1, 16.6, ((k // 2) * 2 - 1) * 1.1), (0.8, 1.2, 0.8), 'iron')
            put(m, tower, a, 13.0, y)
            # Red hot at the top, as Dante saw them from the marsh, and through its slits.
            put(g, Mesh('hot').box((0, 14.6, 0), (2.95, 3.0, 2.95), 'ember', taper=0.97), a, 13.0, y)
            for h in (4.0, 7.5, 11.0):
                put(g, Mesh('slit').box((0, h, 1.58), (0.4, 1.6, 0.1), 'fire'), a, 13.0, y)
        else:
            wall = Mesh('wall').box((0, 3.5, 0), (3.3, 7.0, 1.1), 'iron')
            for x in (-1.1, 0.0, 1.1):
                wall.box((x, 7.5, 0), (0.7, 1.0, 1.1), 'iron')
            put(m, wall, a, 13.3, y)
            put(g, Mesh('seam').box((0, 6.95, 0.56), (3.3, 0.12, 0.05), 'ember'), a, 13.3, y)
    put(g, Mesh('gate').box((0, 2.6, 0.62), (2.2, 5.2, 0.1), 'ember'), spots[12], 13.3, y)
    # The fallen angels who shut the gate on Virgil, on the battlements.
    fiends = m.crowd('dis_fiends', beat={'Offset': [0.0, 0.18, 0.0], 'Every': 1.0, 'Sharp': True, 'Calm': 0.5},
                     head_beat={'Offset': [0.0, -0.08, 0.06], 'Every': 1.0, 'Phase': 0.5})
    for i, a in enumerate(spots):
        if i % 5 in (0, 4) and i % 2 == 0:
            arms = ARMS['up'] if i % 4 == 0 else ARMS['fist']
            put(fiends, horned(man('skin_red', arms), wings='wing_dark'), a, 13.4, y + 7.0, rng.uniform(-20, 20), 1.25)
    # The iron maidens on their gibbets, out over the drop.
    hang, drop, tombs_y = 10.2, 26.0, 28.0
    flare, heat = Mesh('flare'), maiden_heat(drop)
    hung, damned = maiden(drop)
    for i, a in enumerate(arc(9, rng, 0.15)):
        gib = Mesh('gibbet').box((0, 7.9, 1.75), (0.32, 0.32, 3.9), 'iron')
        gib.tube([(0, 5.2, 0.4), (0, 7.75, 2.4)], 0.1, 'iron', 4)
        gib.box((0, 7.6, 3.55), (0.2, 0.45, 0.2), 'iron')
        put(m, gib, a, 13.6, y)
        side = 1 if i % 2 else -1
        # Every other one faces the shaft and the rest the wall (the ledges' cameras see those
        # faces), each swinging toward and away from the axis: across a camera standing off to
        # one side of her, not through it.
        swing = {'Turn': [7.0 * side, 0.0, 0.0], 'Sway': True, 'Every': 2.0, 'Phase': float(i % 2), 'Calm': 0.0}
        out = i % 2 == 0
        pivot, rest = at(a, hang, y + 7.4), face_in(a, (180.0 if out else 0.0) + rng.uniform(-20, 20))
        m.piece('maiden', hung, pivot, rest, beat=swing)
        m.piece('maiden_face_out' if out else 'maiden_face', damned, pivot, rest, beat=swing)
        # Red hot from the feet up while the playing is bad (on the same swing, so it stays on her).
        m.piece('maiden_heat', heat, pivot, rest, beat=swing, glow=True, mood={'Show': 'Bad', 'Seconds': 1.5})
        # A tomb under each, its fire low: flaring up the chain while the playing is bad.
        tomb = Mesh('tomb').box((0, 0.45, 0), (1.3, 0.9, 2.8), 'stone')
        tomb.box((0.6, 1.05, 0.1), (1.4, 0.22, 2.9), 'stone', euler=(0, 10, 26))
        put(m, tomb, a, 11.4, tombs_y)
        put(g, flame(), a, 11.4, tombs_y + 0.6, 0, (1.2, 2.6, 1.8))
        for k in range(3):
            put(flare, flame('ember'), a + (k - 1) * 0.04, hang + 0.6 + 0.3 * (k % 2), tombs_y + 0.4, k * 70.0, (0.6, rng.uniform(6.0, 7.5), 0.6))
    m.piece('flares', flare, (0.0, 0.0, 0.0), glow=True, mood={'Show': 'Bad', 'Seconds': 1.5},
            beat={'Offset': [0.0, 1.6, 0.0], 'Trigger': 'Miss'})
    # The tombs.
    ledge(m, tombs_y, 10.6, 'stone_dark', seed=9, jag=0.4)
    heretics = m.crowd('heretics', beat={'Offset': [0.0, 0.2, 0.0], 'Every': 2.0, 'Calm': 0.4}, head_beat={'Offset': [0.0, -0.08, 0.0], 'Every': 1.0})
    for a in arc(14, rng, 0.3):
        r = rng.uniform(12.2, 14.2)
        yaw = rng.uniform(-30, 30)
        tomb = Mesh('tomb').box((0, 0.45, 0), (1.2, 0.9, 2.6), 'stone')
        tomb.box((0.5, 1.0, 0.1), (1.3, 0.22, 2.7), 'stone', euler=(0, rng.uniform(-14, 14), rng.uniform(18, 34)))
        put(m, tomb, a, r, tombs_y, yaw)
        put(g, flame(), a, r, tombs_y + 0.7, yaw, (1.1, rng.uniform(1.6, 2.6), 1.6))
        put(heretics, man('stone_red', ARMS[rng.choice(('up', 'claw', 'face'))]), a, r, tombs_y - 0.5, yaw + rng.uniform(-40, 40), 1.25)
    return period, m, g


# ---- 7. Violence --------------------------------------------------------------------------------
def thorn_tree(rng):
    """One of the suicides' trees, its root at the origin: a dead, ashen trunk bent and knotted, its
    branches clawing up and out in a wide crown, thorns on them (and no leaves). 5 to 7 high."""
    t = Mesh('tree')
    h = rng.uniform(5.0, 7.0)
    lean = rng.uniform(-0.7, 0.7), rng.uniform(-0.9, 0.3)
    trunk = [(0, -0.4, 0)]
    for k in range(1, 5):
        u = k / 4
        trunk.append((lean[0] * u + 0.3 * math.sin(k * 2.1 + h), h * 0.55 * u, lean[1] * u + 0.3 * math.cos(k * 1.7 + h)))
    t.tube(trunk, [0.34, 0.24, 0.18, 0.13, 0.08], 'bone_dark', 5, caps=False)
    for side in (-1, 1):        # roots
        t.tube([(0, 0.3, 0), (side * 0.7, 0.05, rng.uniform(-0.4, 0.4)), (side * 1.2, -0.2, rng.uniform(-0.6, 0.6))], [0.16, 0.08, 0.0], 'bone_dark', 4, caps=False)

    def branch(base, d, length, radius, depth):
        mid = (base[0] + d[0] * length * 0.5 + rng.uniform(-0.2, 0.2) * length, base[1] + d[1] * length * 0.5 + 0.1 * length,
               base[2] + d[2] * length * 0.5 + rng.uniform(-0.2, 0.2) * length)
        tip = (base[0] + d[0] * length, base[1] + d[1] * length, base[2] + d[2] * length)
        t.tube([base, mid, tip], [radius, radius * 0.55, 0.0], 'bone_dark' if depth else 'grille', 4 if depth else 3, caps=False)
        for k in range(2 if depth else 1):
            s = 0.35 + 0.3 * k
            p = (base[0] + (tip[0] - base[0]) * s, base[1] + (tip[1] - base[1]) * s, base[2] + (tip[2] - base[2]) * s)
            t.tube([p, (p[0] + rng.uniform(-0.3, 0.3), p[1] + 0.25, p[2] + rng.uniform(-0.3, 0.3))], [0.04, 0.0], 'black', 3, caps=False)
        if depth:
            for _ in range(rng.choice((2, 3))):
                e = (d[0] + rng.uniform(-0.9, 0.9), d[1] + rng.uniform(-0.2, 0.6), d[2] + rng.uniform(-0.9, 0.9))
                n = math.sqrt(sum(c * c for c in e))
                branch(tip, tuple(c / n for c in e), length * rng.uniform(0.55, 0.75), radius * 0.5, depth - 1)
    for k in range(rng.choice((4, 5))):
        a = 2 * math.pi * k / 5 + rng.uniform(-0.4, 0.4)
        d = (math.cos(a), rng.uniform(0.25, 0.8), math.sin(a))
        n = math.sqrt(sum(c * c for c in d))
        branch(trunk[rng.choice((2, 3, 3, 4))], tuple(c / n for c in d), h * rng.uniform(0.32, 0.45), 0.1, 1)
    return t


def violence(rng):
    """The seventh circle's three rings, on two terraces of it, as the fall sees them: at the
    back, against the wall, the wood of the suicides, twisted trees the harpies tear at; in the
    middle Phlegethon, the river of boiling blood and fire, the murderers and the thugs in it to
    the waist; at the front, on the lip, the burning sand, its souls burnt to the bone.
    Played well the trees lash at the harpies and drive them off into the air over the river,
    the souls in the river rock out and the skeletons get up and dance; played badly the harpies
    are in the trees, savaging them, the souls go under the blood and the skeletons lie dead."""
    period = 90.0
    m, g = Dress(), Mesh('g')
    river = m.crowd('river', beat={'Offset': [0.0, -0.3, 0.0], 'Every': 1.0, 'Calm': 0.15},
                    head_beat={'Offset': [0.0, -0.13, 0.08], 'Every': 1.0, 'Sharp': True, 'Calm': 0.0},
                    mood={'Show': 'Always', 'Offset': [0.0, -1.7, 0.0], 'Seconds': 1.5})
    dance = m.crowd('skeletons_dance', beat={'Offset': [0.0, 0.25, 0.0], 'Turn': [0.0, 1.2, 0.0], 'Every': 1.0, 'Calm': 0.0},
                    head_beat={'Offset': [0.0, -0.06, 0.07], 'Every': 1.0, 'Phase': 0.5, 'Sharp': True}, mood={'Show': 'Good'})
    dead = m.crowd('skeletons_dead', mood={'Show': 'Bad'})
    flown = m.crowd('harpies_driven_off', beat={'Offset': [0.0, 0.6, 0.0], 'Sway': True, 'Every': 1.0}, mood={'Show': 'Good'})
    biting = m.crowd('harpies_attacking', beat={'Offset': [0.0, -0.35, 0.0], 'Every': 1.0, 'Sharp': True}, mood={'Show': 'Bad'})
    for j, (y, seed) in enumerate(((66.0, 11), (21.0, 13))):
        ledge(m, y, 9.8, 'bone_dark', thick=1.4, seed=seed, jag=0.35)
        # Phlegethon, between its banks, flames running on it.
        band(m, y + 0.15, 11.9, 13.9, 'blood')
        band(m, y + 0.3, 11.7, 11.95, 'stone_dark')
        band(m, y + 0.3, 13.85, 14.15, 'stone_dark')
        band(g, y + 0.19, 12.5, 12.65, 'crimson', 60, gaps=lambda i: (i * 7 + j) % 5 < 2)
        band(g, y + 0.19, 13.2, 13.32, 'crimson', 60, gaps=lambda i: (i * 3 + j) % 4 == 0)
        # The far bank smoulders under the wood on it, so the trees stand out against the wall.
        band(g, y + 0.32, 13.9, 14.1, 'ember', 60, gaps=lambda i: (i * 5 + j) % 3 == 0)
        for a in arc(16, rng, 0.5):
            put(g, flame(), a, rng.uniform(12.2, 13.6), y, rng.uniform(0, 360), (0.6, rng.uniform(0.8, 1.8), 0.6))
        for a in arc(13, rng, 0.45):
            arms = ARMS[rng.choice(('up', 'fist', 'fist', 'claw'))]
            put(river, man(rng.choice(('cab_red', 'skin_red', 'stone_red')), arms, girth=rng.uniform(1.0, 1.3)), a, rng.uniform(12.3, 13.5), y - 0.9,
                rng.uniform(-35, 35), 1.25)
        # The wood, on the far bank: each tree its own, lashing from the root.
        for i, a in enumerate(arc(8, rng, 0.35)):
            side = 1 if (i + j) % 2 else -1
            m.piece('tree', thorn_tree(rng), at(a, rng.uniform(13.9, 14.4), y), face_in(a, rng.uniform(0, 360)),
                    beat={'Turn': [7.0 * side, 0.0, 10.0 * side], 'Sway': True, 'Every': 2.0, 'Phase': float(i % 2), 'Calm': 0.08})
            # Played badly a harpy clings in it, wings up, tearing at it; played well she is driven
            # off, up into the air over the river.
            if i % 4 != 3:
                put(biting, harpy('perch'), a + rng.uniform(-0.05, 0.05), 13.5, y + rng.uniform(2.6, 4.2), rng.choice((-60, 60)) + rng.uniform(-20, 20), 1.35)
                put(flown, harpy('fly'), a + rng.uniform(-0.1, 0.1), rng.uniform(11.5, 13.0), y + rng.uniform(7.0, 10.0), rng.uniform(-50, 50), 1.45,
                    (rng.uniform(-20, 10), 0, rng.uniform(-15, 15)))
        # The burning sand at the front, flakes of fire on it.
        band(m, y + 0.12, 9.95, 11.7, 'bone_dark')
        for a in arc(14, rng, 0.5):
            r = rng.uniform(10.3, 11.4)
            put(dance, skeleton('dance'), a, r, y, rng.uniform(-40, 40), 1.25)
            put(dead, skeleton('dead'), a + rng.uniform(-0.04, 0.04), r, y + 0.2, rng.uniform(0, 360), 1.25, (-90, 0, 0))
        for a in arc(30, rng, 0.5):
            put(g, flame(), a, rng.uniform(10.0, 11.6), y, rng.uniform(0, 360), (rng.uniform(0.25, 0.5), rng.uniform(0.3, 0.9), rng.uniform(0.25, 0.5)))
    return period, m, g


# ---- 8. Fraud -----------------------------------------------------------------------------------
def _whipper():
    """A horned demon of the first ditch, his whip hand up and the lash curling out behind him."""
    d = horned(man('crimson', ((-0.32, 0.95, 0.15), (0.36, 1.95, -0.15)), feet=STRIDE), wings=None)
    d.tube([(0.36, 1.95, -0.15), (0.5, 2.45, -0.6), (0.75, 2.55, -1.4), (0.95, 2.0, -2.2), (1.05, 1.2, -2.5), (1.0, 0.6, -2.3)],
           [0.04, 0.035, 0.03, 0.022, 0.015, 0.0], 'black', 3, caps=False)
    return d


def _swordsman():
    """The demon of the ninth ditch who splits the sowers of discord, his sword up over his head."""
    d = horned(man('horn', ((-0.1, 2.15, 0.25), (0.1, 2.15, 0.25)), feet=STRIDE, girth=1.25), wings='wing_dark')
    d.box((0, 3.25, 0.3), (0.16, 2.1, 0.05), 'chrome')
    d.box((0, 2.25, 0.27), (0.55, 0.08, 0.1), 'iron')
    return d


def _legs():
    """A simoniac, head down in his hole in the rock: hips at the hole, legs kicking, soles up."""
    t = Folk('legs')
    t.box((0, 0.0, 0), (0.36, 0.3, 0.24), 'bone')
    for side in (-1, 1):
        t.tube([(side * 0.1, 0.0, 0), (side * 0.16, 0.48, 0.08), (side * 0.12, 0.95, 0)], [0.09, 0.07, 0.05], 'bone', 4, caps=False)
        t.box((side * 0.12, 1.0, 0.07), (0.12, 0.07, 0.28), 'bone_dark')
    return t


def _sorcerer():
    """A diviner of the fourth ditch: robe and pointed hat, his head wrung round on his neck, so
    the beard hangs down his back and he walks the way he can't see."""
    t = Folk('sorcerer')
    Mesh.merge(t, soul('iris', 'stand'))
    t.tube([(0.23, 1.4, 0), (0.42, 0.9, 0.2), (0.45, 0.6, 0.3)], [0.07, 0.06, 0.05], 'iris', 4, caps=False)
    t.tube([(0.45, -0.0, 0.3), (0.45, 2.1, 0.3)], 0.035, 'wood', 3, caps=False)                 # his staff
    t.head.blob((0, 1.64, 0.0), 0.15, 'bone_dark', 0)
    t.head.tube([(0, 1.62, -0.12), (0, 1.42, -0.2), (0, 1.15, -0.22)], [0.11, 0.08, 0.0], 'marble', 4, caps=False)     # the beard, behind
    t.head.blob((0, 1.66, -0.16), 0.035, 'bone_dark', 0)                                                      # the nose, behind
    t.head.lathe((0, 1.73, 0), [(0.32, 0.0), (0.32, 0.04)], 'navy', 8)
    t.head.tube([(0, 1.75, 0), (0, 2.1, 0.02), (0, 2.45, 0.12)], [0.2, 0.11, 0.0], 'navy', 6, caps=False)
    return t


def _hypocrite():
    """A hypocrite of the sixth ditch, bowed under a cloak gilded outside and lead within, the
    hood over his face."""
    t = Folk('hypocrite')
    t.lathe((0, 0.08, 0), [(0.48, 0.0), (0.42, 0.5), (0.36, 1.0), (0.36, 1.35), (0.22, 1.5), (0.0, 1.54)], 'gold', 9)
    for side in (-1, 1):
        t.tube([(side * 0.12, 0.1, 0.0), (side * 0.13, -0.0, 0.12)], 0.07, 'bone_dark', 3)       # feet under the hem
        t.tube([(side * 0.3, 1.3, 0.05), (side * 0.25, 1.05, 0.3), (side * 0.08, 1.0, 0.38)], [0.1, 0.09, 0.07], 'gold', 5, caps=False)    # sleeves
    t.head.blob((0, 1.66, 0.02), 0.25, 'gold', 0, scale=(0.9, 1.0, 1.1))         # the hood
    t.head.tube([(0, 1.8, -0.15), (0, 1.62, -0.32), (0, 1.4, -0.3)], [0.12, 0.1, 0.0], 'gold', 4, caps=False)
    t.head.blob((0, 1.62, 0.2), 0.12, 'black', 0, scale=(1.0, 1.2, 0.6))        # the dark of it, where his face is
    return turned(t, (16, 0, 0))


def _thief(rng):
    """A thief of the seventh ditch, a serpent wound round him (or its fangs in his neck: he
    will burn to ash and come back, or change into it)."""
    t = man('bone_dark', ARMS[rng.choice(('claw', 'up', 'face'))])
    if rng.random() < 0.5:
        coil = [(0.3 * math.cos(k * 1.4), 0.25 + 0.17 * k, 0.3 * math.sin(k * 1.4)) for k in range(9)]
        t.tube(coil, [0.08] * 8 + [0.0], 'sign_green', 4, caps=False)
    else:
        t.tube([(0.3, 0.0, -0.4), (0.4, 0.8, -0.5), (0.2, 1.4, -0.4), (0.12, 1.62, -0.12)], [0.1, 0.12, 0.1, 0.07], 'sign_green', 4, caps=False)
        t.blob((0.1, 1.6, -0.06), 0.11, 'sign_green', 0, scale=(0.8, 0.7, 1.4))
    return t


def _counsellor():
    """A false counsellor of the eighth ditch: a shape in the dark at the heart of its flame."""
    return turned(soul('soot', 'reach'))


def _sower(rng, kind):
    """A sower of discord of the ninth ditch, split open by the demon's sword: chin to fork, his
    insides hanging; or carrying his own head before him like a lantern."""
    if kind == 'head':
        t = man('skin_red', ((-0.3, 0.9, 0.1), (0.05, 1.55, 0.55)), head=False)
        t.blob((0.05, 1.38, 0.6), 0.14, 'skin_red', 0)
        t.tube([(0, 1.47, 0), (0, 1.52, 0)], 0.1, 'crimson', 4)
        return t
    t = man('skin_red', ARMS[rng.choice(('face', 'claw', 'down'))], feet=STRIDE)
    t.box((0, 1.2, 0.17), (0.12, 0.62, 0.06), 'crimson')
    for x in (-0.06, 0.05):
        t.tube([(x, 1.0, 0.18), (x + 0.05, 0.75, 0.25), (x, 0.5, 0.2)], [0.05, 0.045, 0.0], 'crimson', 4, caps=False)
    return t


def _falsifier(rng, pose):
    """One of the falsifiers in the tenth ditch, rotten with scabs: lying in the heap, or sitting
    up clawing at himself."""
    if pose == 'lie':
        hands = ((-0.7, 1.3, 0.1), (0.4, 1.0, 0.3))
    else:
        hands = ARMS['scratch']
    t = man('bone_dark', hands, feet=((-0.2, 0.0, 0.2), (0.25, 0.1, 0.25)))
    for k in range(5):
        t.blob((rng.uniform(-0.14, 0.14), rng.uniform(0.6, 1.45), 0.15 if k % 2 else -0.15), rng.uniform(0.05, 0.08), 'hivis', 0)
    return t


# Fraud's ten ditches, top (passed first) to bottom: the floor's ink and a word on who is there.
DITCHES = (
    ('stone', 'panderers and seducers, whipped along by horned demons'),
    ('deck_dark', 'flatterers, sunk in excrement'),
    ('stone_dark', 'simoniacs, upside down in holes in the rock, their soles on fire'),
    ('navy', 'sorcerers and diviners, their heads wrung round backwards'),
    ('black', 'grafters in the boiling pitch, the Malebranche over them with their hooks'),
    ('stone', 'hypocrites, trudging in cloaks of gilded lead'),
    ('pine', 'thieves among the serpents, turning into them'),
    ('stone_dark', 'false counsellors, each wrapped in a flame'),
    ('blood', 'sowers of discord, split open by a demon with a sword'),
    ('grille', 'falsifiers, diseased, scratching, lying in heaps'),
)
BOLGIA = 12.0       # metres between one ditch and the next


def fraud(rng):
    """Malebolge: all ten of its ditches, one under another down the spiral, each with its own
    sinners and the demons that drive them, each its own colour, so that each reads at the speed
    they fall past it. The sinners groove along with a good player (and barely stir for a bad
    one); the demons keep at their work on the beat whatever the playing."""
    period = BOLGIA * len(DITCHES)
    m, g = Dress(), Mesh('g')
    groove = {'Offset': [0.0, -0.14, 0.0], 'Every': 1.0, 'Calm': 0.15}
    nod = {'Offset': [0.0, -0.08, 0.05], 'Every': 1.0, 'Phase': 0.5, 'Calm': 0.0}
    tops = [period - BOLGIA / 2 - BOLGIA * i for i in range(len(DITCHES))]
    for i, (y, (ink, _)) in enumerate(zip(tops, DITCHES)):
        ledge(m, y, 10.6, ink, thick=1.1, seed=41 + i, jag=0.3)
    # 1. The panderers and the seducers, two files going opposite ways, and the demons whipping them on.
    y = tops[0]
    walkers = m.crowd('d1_panderers', beat={'Offset': [0.0, -0.1, 0.0], 'Turn': [0.0, 0.8, 0.0], 'Sway': True, 'Every': 2.0, 'Calm': 0.15}, head_beat=nod)
    for k, a in enumerate(arc(16, rng, 0.4)):
        way = 1 if k % 2 else -1
        put(walkers, man(rng.choice(('bone', 'drum_skin')), ARMS['swing'], STRIDE, lean=10), a, 11.7 if way > 0 else 13.5, y, 90 * way + rng.uniform(-10, 10), 1.2)
    whipper = _whipper()
    for k, a in enumerate(arc(3, rng, 0.2)):
        m.piece('d1_whipper', whipper, at(a, 12.6, y), face_in(a, 90 if k % 2 else -90),
                beat={'Turn': [18.0, 0.0, 0.0], 'Every': 1.0, 'Sharp': True}, scale=1.35)
    # 2. The flatterers in the dung.
    y = tops[1]
    for a in arc(14, rng, 0.5):
        put(m, Mesh('dung').blob((0, 0, 0), rng.uniform(0.9, 1.8), rng.choice(('deck', 'wood', 'deck')), 1, 0.3, 1.5, int(rng.uniform(0, 99)),
                                 (1.0, 0.45, 0.9), floor=0.0), a, rng.uniform(11.4, 14.6), y)
    flatterers = m.crowd('d2_flatterers', beat=groove, head_beat=nod)
    for a in arc(13, rng, 0.45):
        put(flatterers, man('bone_dark', ARMS[rng.choice(('up', 'face', 'claw'))]), a, rng.uniform(11.4, 14.0), y - 1.05, rng.uniform(-40, 40), 1.25)
    # 3. The simoniacs, legs up out of the rock, kicking, their soles burning.
    y = tops[2]
    kick = {'Offset': [0.0, 0.22, 0.0], 'Every': 1.0, 'Sharp': True, 'Calm': 0.2}
    legs, soles = m.crowd('d3_simoniacs', beat=kick), Mesh('soles')
    fire = Mesh('sole_fire')
    for side in (-1, 1):
        fire.merge(flame(), (side * 0.12, 1.02, 0.07), (0, 0, 0), (0.28, 0.75, 0.3))
    for a in arc(15, rng, 0.45):
        r, yaw = rng.uniform(11.3, 14.2), rng.uniform(0, 360)
        put(m, Mesh('hole').lathe((0, 0, 0), [(0.48, 0.04), (0.0, 0.06)], 'black', 9), a, r, y)
        put(legs, _legs(), a, r, y + 0.05, yaw, 1.3)
        put(soles, fire, a, r, y + 0.05, yaw, 1.3)
    m.piece('d3_soles', soles, (0.0, 0.0, 0.0), glow=True, beat=kick)
    # 4. The sorcerers and diviners, filing by with their heads on backwards.
    y = tops[3]
    sorcerers = m.crowd('d4_sorcerers', beat={'Offset': [0.0, -0.1, 0.0], 'Every': 2.0, 'Calm': 0.15}, head_beat=nod)
    for k, a in enumerate(arc(13, rng, 0.3)):
        put(sorcerers, _sorcerer(), a, rng.uniform(11.6, 13.8), y, 90 + rng.uniform(-12, 12), 1.25)
    # 5. The grafters in the pitch, and the Malebranche with their hooks.
    y = tops[4]
    band(g, y + 0.12, 11.4, 11.55, 'ember', 60, gaps=lambda n: n % 3 == 0)
    band(g, y + 0.12, 13.2, 13.3, 'ember', 60, gaps=lambda n: n % 4 == 1)
    for a in arc(26, rng, 0.5):
        put(m, Mesh('bubble').blob((0, 0, 0), rng.uniform(0.25, 0.6), 'amp', 0, scale=(1.0, 0.45, 1.0)), a, rng.uniform(11.0, 14.5), y)
    grafters = m.crowd('d5_grafters', beat={'Offset': [0.0, 0.3, 0.0], 'Every': 2.0, 'Calm': 0.2})
    for a in arc(12, rng, 0.5):
        put(grafters, soul('soot', 'reach'), a, rng.uniform(12.2, 14.6), y - 1.3, rng.uniform(0, 360), 1.25)
    # The Malebranche stand on the lip with their backs to the drop, hooking at the grafters
    # behind them, so that a camera among the grafters sees their faces and their hooks.
    hooker = _fiend()
    for k, a in enumerate(arc(4, rng, 0.3)):
        m.piece('d5_malebranche', hooker, at(a, 11.3, y), face_in(a, 180 + rng.uniform(-30, 30)),
                beat={'Turn': [22.0, 0.0, 0.0], 'Every': 1.0, 'Phase': 0.5 * (k % 2), 'Sharp': True}, scale=1.5)
    # 6. The hypocrites, crawling round in their gilded lead, and Caiaphas staked across their road.
    y = tops[5]
    hypocrites = m.crowd('d6_hypocrites', beat={'Offset': [0.0, -0.08, 0.0], 'Turn': [0.0, 0.6, 0.0], 'Every': 2.0, 'Calm': 0.1}, head_beat=nod)
    for a in arc(16, rng, 0.25):
        put(hypocrites, _hypocrite(), a, rng.uniform(11.7, 13.5), y, 90 + rng.uniform(-8, 8), 1.3)
    for a in arc(2, rng, 0.3):
        staked = man('skin_red', ((-0.95, 1.42, 0.0), (0.95, 1.42, 0.0)), feet=((-0.08, 0.0, 0.0), (0.08, 0.0, 0.0)))
        for p in ((-0.95, 1.42, 0.0), (0.95, 1.42, 0.0), (0.0, 0.0, 0.0)):
            staked.tube([(p[0], p[1], p[2] - 0.3), (p[0], p[1], p[2] + 0.3)], 0.04, 'wood', 3)
        put(m, staked, a + 0.07, 12.6, y + 0.15, 90, 1.25, (-90, 0, 0))
    # 7. The thieves and the serpents.
    y = tops[6]
    thieves = m.crowd('d7_thieves', beat=groove, head_beat=nod)
    for a in arc(13, rng, 0.45):
        put(thieves, _thief(rng), a, rng.uniform(11.4, 13.8), y, rng.uniform(-50, 50), 1.25)
    for a in arc(16, rng, 0.5):
        snake = [(0.5 * k, 0.08, 0.35 * math.sin(k * 1.7)) for k in range(7)]
        put(m, Mesh('snake').tube(snake, [0.03, 0.1, 0.11, 0.11, 0.1, 0.07, 0.0], 'sign_green', 4, caps=False), a, rng.uniform(11.0, 14.4), y, rng.uniform(0, 360))
    for a in arc(2, rng, 0.3):      # a great serpent reared up
        s = [(0, 0.0, -0.8), (0.4, 0.9, -0.2), (-0.3, 2.0, 0.1), (0.2, 3.0, 0.3), (0.0, 3.6, 0.8)]
        rear = Mesh('serpent').tube(s, [0.32, 0.3, 0.26, 0.22, 0.18], 'sign_green', 6)
        rear.blob((0.0, 3.65, 1.05), 0.28, 'sign_green', 0, scale=(0.9, 0.6, 1.4))
        put(m, rear, a, 14.6, y, rng.uniform(-20, 20), 1.2)
    # 8. The false counsellors, each in his flame.
    y = tops[7]
    counsellors = m.crowd('d8_counsellors', beat={'Offset': [0.0, 0.2, 0.0], 'Every': 1.0, 'Calm': 0.15})
    for k, a in enumerate(arc(12, rng, 0.4)):
        r = rng.uniform(11.6, 13.8)
        put(counsellors, _counsellor(), a, r, y, rng.uniform(-30, 30), 1.2)
        put(g, flame(), a, r, y - 0.2, rng.uniform(0, 360), (1.4, rng.uniform(3.2, 4.0), 1.4))
        if k == 5:      # Ulysses and Diomedes, two in one flame with two tips
            put(counsellors, _counsellor(), a + 0.06, r, y, rng.uniform(-30, 30), 1.2)
            put(g, flame(), a + 0.06, r, y - 0.2, 0, (1.3, 4.6, 1.3))
    # 9. The sowers of discord, and the demon with the sword.
    y = tops[8]
    sowers = m.crowd('d9_sowers', beat={'Offset': [0.0, -0.12, 0.0], 'Turn': [0.0, -0.8, 0.0], 'Sway': True, 'Every': 2.0, 'Calm': 0.15}, head_beat=nod)
    for k, a in enumerate(arc(13, rng, 0.35)):
        put(sowers, _sower(rng, 'head' if k == 6 else 'split'), a, rng.uniform(11.6, 13.6), y, 90 + rng.uniform(-20, 20), 1.25)
    sword = _swordsman()
    for k, a in enumerate(arc(2, rng, 0.2)):
        m.piece('d9_sword', sword, at(a, 13.9, y), face_in(a, -60 if k else 60),
                beat={'Turn': [28.0, 0.0, 0.0], 'Every': 2.0, 'Phase': float(k), 'Sharp': True}, scale=1.55)
    # 10. The falsifiers in their heaps, and those still able to sit up scratching.
    y = tops[9]
    falsifiers = m.crowd('d10_falsifiers', beat={'Offset': [0.0, 0.08, 0.0], 'Every': 1.0, 'Calm': 0.1}, head_beat=nod)
    for a in arc(5, rng, 0.3):
        r = rng.uniform(12.0, 13.6)
        for k in range(4):
            put(falsifiers, _falsifier(rng, 'lie'), a + rng.uniform(-0.05, 0.05), r + rng.uniform(-0.5, 0.5), y + 0.25 + 0.3 * k, rng.uniform(0, 360), 1.2,
                (-90 + rng.uniform(-15, 15), 0, rng.uniform(-30, 30)))
    for a in arc(7, rng, 0.5):
        put(falsifiers, _falsifier(rng, 'sit'), a, rng.uniform(11.4, 14.0), y - 0.5, rng.uniform(-40, 40), 1.25)
    return period, m, g


# ---- 9. Treachery -------------------------------------------------------------------------------
ICE_MAN = 1.5      # the traitors' scale in the ice


def _frozen(rng, arms, depth, tilt=0.0):
    """A traitor locked in the ice of Cocytus, the ice's top depth metres up him (at his scale,
    ICE_MAN): his origin depth under the ice, and a collar of ice heaped round him where he goes in.
    Blue with the cold, dark eyes and mouth, so that he reads against the white."""
    t = man('sky', ARMS[arms], lean=tilt)
    t.head.blob((0, 1.67, -0.05), 0.125, 'navy', 0, scale=(1.05, 0.75, 1.0))     # hair
    t.head.box((0, 1.65, 0.13), (0.16, 0.04, 0.03), 'navy')                       # eyes
    t.head.box((0, 1.57, 0.13), (0.07, 0.05, 0.03), 'navy')                       # mouth, open
    t.blob((0, depth / ICE_MAN, 0), 0.34, 'cloud', 0, 0.3, 2.0, int(rng.uniform(0, 99)), (1.2, 0.35, 1.1))
    return t


def _face_in_ice(rng):
    """Judecca: nothing of him out of the ice but his face, turned up, and a hand."""
    t = Folk('face')
    t.head.blob((0, 0.05, 0), 0.17, 'sky', 0, scale=(0.9, 0.55, 1.15))
    t.head.blob((0, 0.13, 0.05), 0.05, 'navy', 0, scale=(2.2, 0.6, 0.8))        # shut eyes, under frost
    t.head.blob((0, 0.12, -0.08), 0.04, 'navy', 0, scale=(1.4, 0.8, 1.0))       # the mouth
    x = rng.choice((-0.45, 0.45))
    t.tube([(x, -0.3, 0.1), (x * 1.1, 0.35, 0.2), (x * 1.2, 0.62, 0.22)], [0.07, 0.06, 0.04], 'sky', 4, caps=False)
    return t


def _horns(rng):
    """A forearm out of the ice, its hand making the horns."""
    t = Folk('horns')
    t.tube([(0, -0.4, 0), (0.05, 0.3, 0.05), (0.06, 0.55, 0.06)], [0.08, 0.065, 0.06], 'sky', 4, caps=False)
    t.box((0.06, 0.6, 0.06), (0.14, 0.12, 0.08), 'sky')
    for x in (-0.03, 0.12):
        t.tube([(x, 0.62, 0.06), (x, 0.84, 0.07)], [0.025, 0.018], 'sky', 3, caps=False)
    return t


def treachery(rng):
    """Cocytus: the giants chained round the well above it, then the lake frozen hard, terrace
    under terrace, and the traitors in it deeper the further down: chest deep in Caina, to the
    shoulders in Antenora, to the chin in Ptolomea, their faces turned up, and in Judecca only a
    face and a hand left out of it. Frozen, they still rock out for a good player, heads
    banging, a hand up out of the ice making the horns; for a bad one they are stiff, the hands
    out of the ice clawing at nothing."""
    period = 96.0
    m, g = Dress(), Mesh('g')
    # The giants (passed first), on their shelf, chained by the wrists into the dark above.
    y = 80.0
    ledge(m, y, 12.4, 'marble_shade', thick=2.0, seed=31, jag=0.6)
    giants = m.crowd('giants', beat={'Offset': [0.0, 0.15, 0.0], 'Every': 2.0, 'Calm': 0.4})
    for a in arc(5, rng, 0.15):
        s = rng.uniform(7.5, 8.5)
        giant = Folk('giant').merge(soul('steel', 'stand'))
        giant.lathe((0, 0.95, 0), [(0.31, -0.06), (0.31, 0.06)], 'iron', 8)
        giant.lathe((0, 1.38, 0), [(0.3, -0.05), (0.3, 0.05)], 'iron', 8)
        put(giants, giant, a, 14.4, y, rng.uniform(-15, 15), s)
        bonds = Mesh('bonds')
        for side in (-1, 1):
            chain(bonds, (side * 0.3 * s, y + 0.86 * s + 14.0, 0.06 * s), 14.0, 'iron', 1.3, 0.55, 0.09)
        put(m, bonds, a, 14.4, 0.0)
    # The lake: four terraces of it.
    zones = ((62.0, 'chest'), (44.0, 'shoulders'), (26.0, 'chin'), (8.0, 'face'))
    good = m.crowd('ice_horns', beat={'Offset': [0.0, 0.25, 0.0], 'Every': 1.0, 'Sharp': True}, mood={'Show': 'Good'})
    bad = m.crowd('ice_clawing', mood={'Show': 'Bad'})
    for j, (y, deep) in enumerate(zones):
        ledge(m, y, 10.4, 'feather_tip', thick=2.4, seed=32 + j, jag=0.7)
        frozen = m.crowd(f'ice_{deep}', beat={'Offset': [0.0, 0.1, 0.0], 'Every': 1.0, 'Calm': 0.0},
                         head_beat={'Offset': [0.0, -0.14, 0.1], 'Every': 1.0, 'Sharp': True, 'Calm': 0.0})
        for a in arc({'chest': 24, 'shoulders': 24, 'chin': 22, 'face': 26}[deep], rng, 0.45):
            r, yaw, k = rng.uniform(10.9, 13.8), rng.uniform(-35, 35), ICE_MAN
            if deep == 'chest':
                put(frozen, _frozen(rng, rng.choice(('up', 'fist', 'claw', 'face')), 1.1 * k), a, r, y - 1.1 * k, yaw, k)
            elif deep == 'shoulders':
                put(frozen, _frozen(rng, 'down', 1.42 * k), a, r, y - 1.42 * k, yaw, k)
            elif deep == 'chin':
                put(frozen, _frozen(rng, 'down', 1.52 * k, -28.0), a, r, y - 1.5 * k, yaw, k)
            else:
                # (Judecca's faces twice the size: all that is left of them, they have to
                # read from the shot down among them.)
                put(frozen, _face_in_ice(rng), a, r, y + 0.02, yaw, 2.0 * k)
        # Below the top terrace, a hand out of the ice for every few of them: the horns for a
        # good player, clawing for a bad one.
        if deep != 'chest':
            for a in arc(7, rng, 0.5):
                r, yaw = rng.uniform(11.0, 14.2), rng.uniform(-30, 30)
                hand = ICE_MAN * (2.0 if deep == 'face' else 1.0)
                put(good, _horns(rng), a, r, y, yaw, hand)
                put(bad, man('sky', ARMS['claw'], head=False), a, r, y - 1.3 * hand, yaw, hand, (-15, 0, 0))
        for a in arc(9, rng, 0.5):
            r, h = rng.uniform(13.8, 15.4), rng.uniform(1.2, 3.8)
            put(m, Mesh('shard').tube([(0, -0.2, 0), (rng.uniform(-0.5, 0.5), h, rng.uniform(-0.5, 0.5))], [0.32 * h / 2.0, 0.0], 'white', 4, caps=False), a, r, y)
    # Icicles under every shelf, lit from inside.
    for top, r0 in [(80.0 - 2.0, 13.0)] + [(y - 2.4, 11.0) for y, _ in zones]:
        for a in arc(26, rng, 0.5):
            h = rng.uniform(1.5, 6.0)
            put(g, Mesh('icicle').tube([(0, 0, 0), (0, -h, 0)], [0.28, 0.0], 'sky', 4, caps=False), a, rng.uniform(r0, r0 + 2.0), top)
    return period, m, g
