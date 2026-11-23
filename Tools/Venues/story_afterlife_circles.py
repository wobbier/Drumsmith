"""The nine circles the band falls through in Free Bird (Design/Highway-to-the-Afterlife.md,
"Descent"): Dante's, from Limbo down to Treachery. Under the ninth is the floor the band lands on
(make_story_afterlife.hell), whose stands have nine tiers, one for each circle.

Each circle is a tube of its own rock round the shaft's axis, dressed with what Dante found
there, streaming up past the band on a loop: its shape repeats every 'period' metres, so the loop
never jumps. The circles are stacked, as the pit is: when a circle's story flag lands (circle_1 ..
circle_9) it comes up from under the one they are in while that one goes on up, both at the same
speed, the bare rock of the deep shaft between them for a moment. Nothing pops: the whole swap is
one move, TRAVEL seconds long. The circle above stays where it went until the one after next.

The ledges are horseshoes, open toward the audience side (-z), where the venue's own cameras
(Wide, Desk, Crane) stand: nothing but the wall passes through those. Each winds down the wall
as it goes round (lift), one circle's clockwise, the next one's the other way.

The damned are not in the rock's mesh but in three meshes of their own, and their heads in three
more, each on a VenueBeat: they dip and nod with the song, the three out of step with each other.
"""
import math
import random

import story_afterlife_art as A
import story_afterlife_people as P
from story_afterlife_mesh import Mesh, fbm3, rot
from venuegen import look_rotation

AXIS = (0.0, 0.0, 3.0)      # the shaft's axis in the venue (the band falls about it)
TRAVEL = 12.0               # seconds one circle takes to come up as the one above goes
FADE = 3.0                  # seconds a circle's light and weather take over from the last one's
SHAFT = 390.0               # the height of the shaft under the road, which the first circle follows
DROP = 14.0                 # how far a ledge winds down the wall from one end of its horseshoe to the other
GROUPS = 3                  # how many ways the damned of a circle move
WALL = 16.2                 # the walls' least radius: outside the venue's cameras (the Wide stands 14.5 from the axis)
# The fall's lights are all but out of the haze: its volume is the room's box, which shows as a
# slab of light across a shaft. (Not 0: the renderer sorts lights with no haze last, and they are
# the first a full light cluster drops.)
FOG = 0.02
# The arc left open for the venue's cameras, in degrees about the axis (+z is 90, -z is -90).
OPEN = (-128.0, -34.0)

# name, the caption that names it, the cue in Free Bird's chart (Rock Band 3's sections) and its
# share of the song for a recording without sections.
CIRCLES = (
    ('Limbo', 'The First Circle: Limbo', 'section:gtr_solo', 0.522),
    ('Lust', 'The Second Circle: Lust', 'section:gtr_solo_a', 0.568),
    ('Gluttony', 'The Third Circle: Gluttony', 'section:gtr_solo_c', 0.634),
    ('Greed', 'The Fourth Circle: Greed', 'section:gtr_solo_d', 0.688),
    ('Wrath', 'The Fifth Circle: Wrath', 'section:gtr_solo_e', 0.732),
    ('Heresy', 'The Sixth Circle: Heresy', 'section:gtr_solo_f', 0.775),
    ('Violence', 'The Seventh Circle: Violence', 'section:gtr_solo_g', 0.818),
    ('Fraud', 'The Eighth Circle: Fraud', 'section:gtr_solo_h', 0.862),
    ('Treachery', 'The Ninth Circle: Treachery', 'section:gtr_solo_i', 0.907),
)


def flag(k):
    return f'circle_{k}'


# ---- placing on the ring ----------------------------------------------------------------------
def pol(a, r, y):
    return (r * math.cos(a), y, r * math.sin(a))


def is_open(a):
    d = (math.degrees(a) + 180.0) % 360.0 - 180.0
    return OPEN[0] <= d <= OPEN[1]


def arc(count, rng=None, jitter=0.0):
    """count angles spread round the closed part of the ring (the horseshoe)."""
    a0, a1 = math.radians(OPEN[1] + 6.0), math.radians(OPEN[0] + 360.0 - 6.0)
    out = []
    for i in range(count):
        t = (i + 0.5) / count
        if rng and jitter:
            t += rng.uniform(-jitter, jitter) / count
        out.append(a0 + (a1 - a0) * t)
    return out


_wind = 0.0     # the circle being built winds down this far (DROP, or -DROP the other way)


def lift(a):
    """How far the ledges (and everything on them) stand above their nominal height at angle a:
    they wind down the wall from one end of the horseshoe to the other."""
    d = (math.degrees(a) - OPEN[0]) % 360.0 + OPEN[0]
    t = (d - OPEN[1]) / (OPEN[0] + 360.0 - OPEN[1])
    return _wind * (0.5 - max(0.0, min(1.0, t)))


def spol(a, r, y):
    return pol(a, r, y + lift(a))


class Folk(Mesh):
    """A figure, or a thing with figures on it: the bodies (and whatever moves with them) are
    its own triangles, the heads a mesh of their own, so a circle can nod them separately."""

    def __init__(self, name):
        super().__init__(name)
        self.head = Mesh(name + '_head')

    def merge(self, other, pos=(0, 0, 0), euler=(0, 0, 0), scale=1.0):
        super().merge(other, pos, euler, scale)
        if isinstance(other, Folk):
            self.head.merge(other.head, pos, euler, scale)
        return self


class Dress(Mesh):
    """One period of a circle's dressing. What is put on it that is Folk goes to one of its
    GROUPS (bodies, heads) in turn instead of into the rock."""

    def __init__(self):
        super().__init__('s')
        self.folk = [(Mesh(f'b{i}'), Mesh(f'h{i}')) for i in range(GROUPS)]
        self.turn = 0


def put(m, sub, a, r, y, yaw=0.0, scale=1.0, euler=None):
    """Merge sub into m at angle a, radius r, height y (plus the ledges' lift there). sub is built
    facing the axis: its +z points inward, +x along the ring, +y up. yaw turns it about its own
    up first (degrees); euler, if given, is applied before that (to lay a figure down)."""
    ca, sa = math.cos(a), math.sin(a)
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    sc = scale if isinstance(scale, tuple) else (scale, scale, scale)
    y += lift(a)
    parts = [(sub, m)]
    if isinstance(sub, Folk):
        parts = [(sub, m), (sub.head, m)]
        if isinstance(m, Dress):
            body, head = m.folk[m.turn % GROUPS]
            m.turn += 1
            parts = [(sub, body), (sub.head, head)]
    for source, into in parts:
        for pts, uvs in source.tris:
            q = []
            for p in pts:
                x, h, z = p[0] * sc[0], p[1] * sc[1], p[2] * sc[2]
                if euler:
                    x, h, z = rot((x, h, z), euler)
                x, z = x * cy + z * sy, -x * sy + z * cy
                q.append((r * ca - x * sa - z * ca, y + h, r * sa + x * ca - z * sa))
            into.tris.append((tuple(q), uvs))


def walls(venue, name, period, copies, seed, radius=WALL, rough=0.2):
    """A circle's wall: a ragged rock tube seen from inside whose shape and texture repeat every
    period metres."""
    def build(m):
        sides = 28
        per = max(4, int(round(period / 5.0)))
        step = period / per
        rows = per * copies

        def n(a, y):
            return fbm3(math.cos(a) * 1.6 + 3 + seed, y * 0.07, math.sin(a) * 1.6 + 8, 12 + seed) + 0.35 * (
                fbm3(math.cos(a) * 6 + 1, y * 0.3 + seed, math.sin(a) * 6 + 4, 14 + seed) - 0.5)
        rings = []
        for k in range(rows + 1):
            t = (k % per) / per
            ring = []
            for i in range(sides):
                a = 2 * math.pi * i / sides
                v = (1 - t) * n(a, t * period) + t * n(a, t * period - period)
                ring.append(pol(a, radius * (1.0 + rough * max(v - 0.1, 0.0)), -period * copies / 2 + step * k))
            rings.append(ring)
        for r_ in range(rows):
            for i in range(sides):
                j = (i + 1) % sides
                q = [rings[r_][i], rings[r_][j], rings[r_ + 1][j], rings[r_ + 1][i]]
                v0, v1 = r_ * 4.0 / per, (r_ + 1) * 4.0 / per
                m.face(q, uvs=[(i / sides * 6, v0), ((i + 1) / sides * 6, v0), ((i + 1) / sides * 6, v1), (i / sides * 6, v1)])
    return A.prop(venue, name, build, 'Rock')


def ledge(m, y, r_in, ink, thick=1.4, seed=0, jag=0.5, r_out=WALL * 1.2, sides=40, whole=False):
    """A shelf of rock round the wall, its top at y, ragged along its lip."""
    def lip(a):
        return r_in + jag * (fbm3(math.cos(a) * 2.2 + seed, seed * 1.7, math.sin(a) * 2.2, 5 + seed) * 2 - 1)
    def shut(i):
        return not whole and (is_open(2 * math.pi * i / sides) or is_open(2 * math.pi * (i + 1) / sides))
    for i in range(sides):
        a0, a1 = 2 * math.pi * i / sides, 2 * math.pi * (i + 1) / sides
        if shut(i):
            continue
        r0, r1 = lip(a0), lip(a1)
        # The horseshoe's two ends are closed off.
        for a, r, other in ((a0, r0, i - 1), (a1, r1, i + 1)):
            if shut(other % sides):
                m.face([spol(a, r, y), spol(a, r_out, y), spol(a, r_out, y - thick * 3.2), spol(a, r + 0.5, y - thick)], ink, both=True)
        m.face([spol(a0, r0, y), spol(a1, r1, y), spol(a1, r_out, y), spol(a0, r_out, y)], ink, outward=(0, 1, 0))
        m.face([spol(a0, r0, y), spol(a1, r1, y), spol(a1, r1 + 0.5, y - thick), spol(a0, r0 + 0.5, y - thick)], ink,
               outward=(-math.cos(a0), -0.2, -math.sin(a0)))
        m.face([spol(a0, r0 + 0.5, y - thick), spol(a1, r1 + 0.5, y - thick), spol(a1, r_out, y - thick * 3.2), spol(a0, r_out, y - thick * 3.2)], ink,
               outward=(0, -1, 0))


def sheet(m, a, r, y_top, y_bottom, width, ink):
    """Falls down the wall (water, blood, a seam of gold), facing the axis: a few strands of
    different lengths rather than one ribbon."""
    for k in range(6):
        u = fbm3(a * 9.1 + k * 3.7, y_top * 0.37, k * 1.3, 77)
        w = width * (0.025 + 0.06 * u) / r
        at = a + (k - 2.5) * width * 0.2 / r
        bottom = y_bottom + (y_top - y_bottom) * 0.45 * fbm3(a * 5.3, k * 2.9, y_top * 0.11, 78)
        # Thinning to nothing as it falls.
        m.face([spol(at, r, bottom), spol(at + w, r + 0.3, y_top), spol(at - w, r + 0.3, y_top)], ink, both=True)


def stack(venue, name, unit, period, copies):
    """unit (one period of dressing, its heights 0..period) repeated up the tube."""
    def build(m):
        for j in range(copies):
            m.merge(unit, (0, (j - copies / 2.0) * period, 0))
    return A.prop(venue, name, build)


# ---- the damned -------------------------------------------------------------------------------
_SOULS = {}


def soul(ink='marble_shade', pose='stand'):
    """A shade: a robed figure 1.8 high standing on the origin, facing +z. Poses: stand, weep
    (hands to the face), reach (arms up), push (arms out in front), fly (arms flung wide)."""
    key = (ink, pose)
    if key not in _SOULS:
        t = Folk('soul')
        t.tube([(0, 0, 0), (0, 0.9, 0.02), (0, 1.46, 0)], [0.32, 0.23, 0.2], ink, 6)
        t.head.blob((0, 1.66, 0.02), 0.17, ink, 0)
        for side in (-1, 1):
            hand = {'stand': (side * 0.3, 0.85, 0.06), 'weep': (side * 0.09, 1.62, 0.2), 'reach': (side * 0.42, 2.05, 0.12),
                    'push': (side * 0.2, 1.22, 0.66), 'fly': (side * 0.85, 1.55, -0.1)}[pose]
            t.tube([(side * 0.23, 1.4, 0), hand], [0.075, 0.06], ink, 4)
        _SOULS[key] = t
    return _SOULS[key]


def flame(ink='fire'):
    """A tongue of flame 1 high on the origin (for a glow mesh)."""
    t = Mesh('flame')
    rings = []
    for k in range(5):
        u = k / 4
        r = 0.36 * math.sin(math.pi * (0.15 + 0.85 * u) ** 0.7) * (1 - u) ** 0.5 + 0.0001
        rings.append([(r * math.cos(2 * math.pi * i / 5 + u * 1.4) + 0.1 * math.sin(u * 5), u, r * math.sin(2 * math.pi * i / 5 + u * 1.4)) for i in range(5)])
    t.loft(rings, ink)
    return t


# ---- 1. Limbo -----------------------------------------------------------------------------------
def limbo(rng):
    """The virtuous unbaptised: no torment, only sighs. A grey twilight, the ruined colonnades
    of the noble castle with its seven gates, the shades standing about under them."""
    period = 80.0
    m, g = Dress(), Mesh('g')
    # The castle's gates (passed first: the higher ledge).
    ledge(m, 58.0, 11.6, 'stone', seed=3)
    for a in arc(7):
        gate = Mesh('gate')
        for x in (-1.5, 1.5):
            gate.box((x, 3.0, 0), (0.9, 6.0, 1.2), 'marble_shade')
        gate.box((0, 6.5, 0), (4.6, 1.0, 1.5), 'marble')
        gate.box((0, 7.4, 0), (3.4, 0.8, 1.2), 'marble_shade', taper=0.6)
        put(m, gate, a, 13.0, 58.0)
        put(m, soul('marble_shade', 'stand'), a + 0.02, 12.2, 58.0, rng.uniform(-30, 30), 1.3)
    # The colonnade.
    ledge(m, 20.0, 11.0, 'marble_shade', seed=1, jag=0.3)
    col = Mesh('col').lathe((0, 0, 0), [(0.62, 0), (0.62, 0.3), (0.42, 0.42), (0.38, 6.4), (0.56, 6.6), (0.56, 7.0)], 'marble', 8)
    stump = Mesh('stump').lathe((0, 0, 0), [(0.62, 0), (0.62, 0.3), (0.42, 0.42), (0.4, 2.2), (0.0, 2.6)], 'marble', 8)
    lintel = Mesh('lintel').box((0, 7.35, 0), (3.1, 0.7, 1.1), 'marble')
    columns = arc(22)
    whole = [rng.random() > 0.22 for _ in columns]
    for i, a in enumerate(columns):
        put(m, col if whole[i] else stump, a, 12.6, 20.0, rng.uniform(0, 360) if not whole[i] else 0.0)
        if i and whole[i] and whole[i - 1]:
            put(m, lintel, (a + columns[i - 1]) / 2, 12.6, 20.0)
    for a in arc(30, rng, 0.4):
        put(m, soul('marble_shade', rng.choice(('stand', 'stand', 'weep'))), a, rng.uniform(11.3, 12.1), 20.0, rng.uniform(-40, 40), rng.uniform(1.2, 1.4))
    # The one fire that holds back the dark.
    put(m, Mesh('bowl').lathe((0, 0, 0), [(0.2, 0), (0.25, 1.0), (0.8, 1.4), (0.7, 1.45), (0.0, 1.3)], 'marble_shade', 8), math.radians(90), 11.6, 20.0)
    put(g, flame('lamp'), math.radians(90), 11.6, 21.3, 0, (1.3, 2.2, 1.3))
    return period, m, g


# ---- 2. Lust ------------------------------------------------------------------------------------
def lust_whirl(venue, name, rng, r0, r1, count):
    """The hurricane: the lustful flung round the shaft for ever, some of them two by two. One
    mesh about the axis; the generator spins it. Returns (souls, wind streaks)."""
    def build_souls(m):
        for i in range(count):
            a, r, y = rng.uniform(0, 2 * math.pi), rng.uniform(r0, r1), rng.uniform(-42, 42)
            lay = (rng.uniform(60, 110), 0, rng.uniform(-40, 40))
            put(m, soul('bone', 'fly'), a, r, y, 90 + rng.uniform(-25, 25), 1.25, lay)
            if i % 3 == 0:      # a pair, hand in hand
                put(m, soul('bone', 'reach'), a + 1.3 / r, r + rng.uniform(-0.4, 0.4), y + 0.5, 90 + rng.uniform(-25, 25), 1.1, lay)

    def build_wind(m):
        for i in range(count // 2):
            a, r, y, sweep = rng.uniform(0, 2 * math.pi), rng.uniform(r0, r1), rng.uniform(-45, 45), rng.uniform(0.5, 1.1)
            lift, w = rng.uniform(-2.5, 2.5), rng.uniform(0.05, 0.14)
            for k in range(8):
                t0, t1 = k / 8, (k + 1) / 8
                m.face([pol(a + sweep * t0, r, y + lift * t0 - w * math.sin(math.pi * t0)), pol(a + sweep * t1, r, y + lift * t1 - w * math.sin(math.pi * t1)),
                        pol(a + sweep * t1, r, y + lift * t1 + w * math.sin(math.pi * t1)), pol(a + sweep * t0, r, y + lift * t0 + w * math.sin(math.pi * t0))], 'white', both=True)
    return A.prop(venue, name, build_souls), A.prop(venue, name + 'Wind', build_wind)


def lust(rng):
    """Bare black rock: the storm is everything here. A few torn crags for the wind to scream on."""
    period = 65.0
    m, g = Dress(), Mesh('g')
    for a in arc(9, rng, 0.45):
        y = rng.uniform(0, period)
        crag = Mesh('crag')
        crag.tube([(0, 0, -1.5), (rng.uniform(-1, 1), rng.uniform(0.5, 2.0), 1.5), (rng.uniform(-1.5, 1.5), rng.uniform(1.5, 4.0), 4.2)], [1.5, 0.9, 0.0], 'stone_dark', 5, caps=False)
        put(m, crag, a, WALL, y)
    return period, m, g


# ---- 3. Gluttony --------------------------------------------------------------------------------
def gluttony(rng):
    """The gluttons lie in freezing mire under a rain that never stops, slime hanging off every
    ledge. (Cerberus is his own prop: cerberus().)"""
    period = 70.0
    m, g = Dress(), Mesh('g')
    for y, r_in, seed, lying in ((50.0, 11.8, 4, 16), (16.0, 10.9, 6, 26)):
        ledge(m, y, r_in, 'deck_dark', thick=1.8, seed=seed, jag=0.9)
        for a in arc(lying, rng, 0.45):
            r = rng.uniform(r_in + 0.6, 14.6)
            # Face down in the mud, half sunk.
            put(m, soul('grille', rng.choice(('stand', 'reach'))), a, r, y - 0.12, rng.uniform(0, 360), rng.uniform(1.2, 1.5), (90, 0, 0))
        for a in arc(10, rng, 0.45):
            put(m, Mesh('pool').lathe((0, 0, 0), [(rng.uniform(0.8, 1.8), 0.03), (0.0, 0.05)], 'glass', 9), a, rng.uniform(r_in + 1.0, 13.5), y)
        for a in arc(34, rng, 0.5):
            r = r_in + rng.uniform(0.5, 2.5)
            h = rng.uniform(1.5, 8.0)
            put(m, Mesh('slime').tube([(0, 0, 0), (rng.uniform(-0.2, 0.2), -h * 0.6, 0), (rng.uniform(-0.3, 0.3), -h, 0)], [0.22, 0.1, 0.0], 'pine', 4, caps=False), a, r, y - 1.9)
    return period, m, g


def cerberus(venue):
    """Cerberus, out of the wall behind the band (toward +z): the chest in the rock and three
    heads on their necks, each as big as a van. Returns (the beast, its eyes and throats)."""
    a = math.radians(90)
    heads = (((-4.2, 0.6, 4.2), -24), ((0.0, 2.2, 5.6), 0), ((4.2, 0.2, 4.4), 22))

    def build(m):
        t = Mesh('c')
        t.blob((0, -1.5, 0.5), 4.2, 'grille', 1, 0.2, 1.2, 9, (1.5, 1.1, 1.0))
        for (x, y, z), yaw in heads:
            t.tube([(x * 0.45, y * 0.3 - 1.0, 0.8), (x * 0.8, y * 0.8, z * 0.55), (x, y, z - 1.0)], [1.7, 1.35, 1.2], 'grille', 7, caps=False)
            h = Mesh('h')
            h.blob((0, 0, 0), 1.55, 'grille', 1, 0.12, 1.4, 3, (1.0, 0.95, 1.1))
            h.box((0, -0.05, 1.7), (1.5, 0.75, 2.2), 'grille', taper=0.8)                       # the muzzle
            h.box((0, -1.0, 1.35), (1.3, 0.3, 2.2), 'stone_dark', euler=(18, 0, 0))             # the jaw, open
            h.blob((0, 0.25, 2.75), 0.3, 'black', 0)
            for side in (-1, 1):
                h.tube([(side * 0.9, 0.9, -0.5), (side * 1.2, 1.9, -0.9)], [0.5, 0.0], 'grille', 4, caps=False)   # ears
                for k in range(4):
                    zt = 1.0 + 0.48 * k
                    h.tube([(side * 0.55, -0.42, zt), (side * 0.55, -0.85, zt)], [0.13, 0.0], 'bone', 4, caps=False)
                    h.tube([(side * 0.5, -0.85, zt + 0.15), (side * 0.5, -0.5, zt + 0.25)], [0.12, 0.0], 'bone', 4, caps=False)
            for p, uv in h.tris:
                t.tris.append((tuple((rot(q, (10, yaw, 0))[0] + x, rot(q, (10, yaw, 0))[1] + y, rot(q, (10, yaw, 0))[2] + z) for q in p), uv))
        put(m, t, a, WALL + 3.5, 0.0, 0.0, 1.5)

    def build_eyes(m):
        t = Mesh('e')
        for (x, y, z), yaw in heads:
            for side in (-1, 1):
                p = rot((side * 0.62, 0.55, 1.05), (10, yaw, 0))
                t.blob((p[0] + x, p[1] + y, p[2] + z), 0.3, 'red_lamp', 0)
            p = rot((0, -0.55, 1.2), (10, yaw, 0))
            t.blob((p[0] + x, p[1] + y, p[2] + z), 0.5, 'ember', 0, scale=(1.0, 0.5, 1.6))
        put(m, t, a, WALL + 3.5, 0.0, 0.0, 1.5)
    return A.prop(venue, 'Cerberus', build, smooth_=True), A.prop(venue, 'CerberusEyes', build_eyes)


# ---- 4. Greed -----------------------------------------------------------------------------------
def greed(rng):
    """The hoarders and the wasters, rolling great weights round the ring with their chests, one
    crowd each way, for ever; the gold they fought over heaped against the walls."""
    period = 70.0
    m, g = Dress(), Mesh('g')
    for y, way, seed in ((48.0, 1, 2), (14.0, -1, 8)):
        ledge(m, y, 10.9, 'stone', seed=seed, jag=0.35)
        for a in arc(9, rng, 0.2):
            rad = rng.uniform(1.5, 2.1)
            w = Folk('w')
            w.blob((0, rad, 0), rad, 'stone', 1, 0.08, 1.5, int(rng.uniform(0, 99)))
            w.lathe((0, rad, 0), [(rad * 1.04, -0.28), (rad * 1.04, 0.28)], 'gold', 12, axis='x')      # banded with it
            for k in range(rng.choice((2, 3))):
                w.merge(soul('bone_dark', 'push'), ((k - 1) * 0.75, 0, -rad - 0.55 - 0.25 * (k % 2)), (14, 0, 0))
            put(m, w, a, 12.2, y, 90 * way)
        # Heaps of coin, a chest or two.
        for a in arc(13, rng, 0.45):
            size = rng.uniform(1.0, 2.6)
            put(m, Mesh('heap').blob((0, 0, 0), size, 'gold', 1, 0.25, 2.0, int(rng.uniform(0, 99)), (1.0, 0.55, 0.8), floor=0.0), a, rng.uniform(14.6, 15.8), y)
            if rng.random() < 0.4:
                chest = Mesh('chest').box((0, 0.35, 0), (1.3, 0.7, 0.8), 'wood')
                chest.box((0, 0.85, -0.25), (1.3, 0.2, 0.8), 'gold_dark', euler=(-50, 0, 0))
                chest.blob((0, 0.75, 0), 0.45, 'gold', 0, scale=(1.2, 0.5, 0.7))
                put(m, chest, a + 0.12, 13.0, y, rng.uniform(-30, 30))
    # Seams of gold in the wall between the roads.
    for a in arc(16, rng, 0.5):
        y = rng.uniform(0, period)
        sheet(g, a, WALL - 0.2, y + rng.uniform(4, 9), y, rng.uniform(0.8, 1.6), 'gold_dark')
    return period, m, g


# ---- 5. Wrath -----------------------------------------------------------------------------------
def wrath(rng):
    """The Styx: a black marsh where the wrathful tear at each other for ever and the sullen lie
    under the water; the watchtower with its two fires, and the ferryman's boat."""
    period = 65.0
    m, g = Dress(), Mesh('g')
    y = 22.0
    ledge(m, y, 10.6, 'pine_dark', thick=1.0, seed=5, jag=0.6)
    for a in arc(15, rng, 0.35):
        r = rng.uniform(11.4, 13.4)
        pair = Folk('pair')
        pair.merge(soul('stone_red', 'push'), (-0.55, 0, 0), (0, 90, 0))
        pair.merge(soul('stone_red', rng.choice(('push', 'reach'))), (0.55, 0, 0), (0, -90, 0))
        put(m, pair, a, r, y - rng.uniform(0.6, 1.0), rng.uniform(0, 360), 1.3)
    for a in arc(26, rng, 0.5):     # the sullen: no more than the tops of their heads
        sunk = Folk('sunk')
        sunk.head.blob((0, 0, 0), 0.19, 'grille', 0)
        put(m, sunk, a, rng.uniform(11.0, 14.0), y + 0.02)
    for a in arc(40, rng, 0.5):     # reeds
        r, h = rng.uniform(10.9, 14.2), rng.uniform(0.8, 2.2)
        put(m, Mesh('reed').tube([(0, 0, 0), (rng.uniform(-0.3, 0.3), h, rng.uniform(-0.3, 0.3))], [0.04, 0.0], 'pine', 3, caps=False), a, r, y)
    # The tower, and its two signal fires.
    ta = math.radians(128)
    tower = Mesh('tower').box((0, 5.5, 0), (2.8, 11.0, 2.8), 'stone_dark', taper=0.78)
    tower.box((0, 11.3, 0), (2.9, 0.6, 2.9), 'stone')
    put(m, tower, ta, 13.0, y)
    for x in (-0.7, 0.7):
        put(g, flame(), ta + x / 13.0, 13.0, y + 11.6, 0, (0.9, 2.4, 0.9))
    # Phlegyas and his boat.
    boat = Folk('boat')
    boat.box((0, 0.25, 0), (1.5, 0.5, 5.0), 'deck_dark', taper=1.25)
    boat.box((0, 0.5, 2.7), (0.5, 0.9, 0.6), 'deck_dark', taper=0.5)
    boat.merge(soul('black', 'push'), (0, 0.45, -1.4))
    boat.tube([(0.5, -0.6, -0.6), (0.3, 3.0, -1.1)], [0.05, 0.05], 'wood', 4)
    put(m, boat, math.radians(58), 11.9, y, 80)
    # The water coming down the wall into it, and going on down.
    for a in arc(9, rng, 0.4):
        sheet(g, a, WALL - 0.2, y + rng.uniform(18, 30), y + 0.1, rng.uniform(1.5, 3.0), 'navy')
        sheet(g, a + 0.2, 11.6, y - 1.0, y - rng.uniform(14, 22), rng.uniform(1.0, 2.2), 'navy')
    return period, m, g


# ---- 6. Heresy ----------------------------------------------------------------------------------
def heresy(rng):
    """The city of Dis: its iron wall and towers, red hot; inside, the heretics' tombs standing
    open, each with its fire."""
    period = 80.0
    m, g = Dress(), Mesh('g')
    # The wall of the city (passed first).
    y = 54.0
    ledge(m, y, 11.6, 'iron', seed=7, jag=0.2)
    spots = arc(26)
    for i, a in enumerate(spots):
        if i % 5 == 2:
            tower = Mesh('tower').box((0, 6.5, 0), (3.0, 13.0, 3.0), 'iron', taper=0.85)
            for k in range(4):
                tower.box((((k % 2) * 2 - 1) * 1.05, 13.5, ((k // 2) * 2 - 1) * 1.05), (0.7, 1.0, 0.7), 'iron')
            put(m, tower, a, 13.0, y)
            for h in (4.0, 7.5, 10.5):
                put(g, Mesh('slit').box((0, h, 1.46), (0.35, 1.5, 0.1), 'ember'), a, 13.0, y)
        else:
            wall = Mesh('wall').box((0, 3.5, 0), (3.3, 7.0, 1.1), 'iron')
            for x in (-1.1, 0.0, 1.1):
                wall.box((x, 7.5, 0), (0.7, 1.0, 1.1), 'iron')
            put(m, wall, a, 13.3, y)
    gate_a = spots[12]
    put(g, Mesh('gate').box((0, 2.6, 0.62), (2.2, 5.2, 0.1), 'ember'), gate_a, 13.3, y)
    # The tombs.
    y = 18.0
    ledge(m, y, 10.7, 'stone_dark', seed=9, jag=0.4)
    for a in arc(18, rng, 0.3):
        r = rng.uniform(11.6, 13.4)
        tomb = Mesh('tomb').box((0, 0.45, 0), (1.2, 0.9, 2.6), 'stone')
        tomb.box((0.5, 1.0, 0.1), (1.3, 0.22, 2.7), 'stone', euler=(0, rng.uniform(-14, 14), rng.uniform(18, 34)))
        yaw = rng.uniform(-25, 25)
        put(m, tomb, a, r, y, yaw)
        put(g, flame(), a, r, y + 0.7, yaw, (1.1, rng.uniform(2.0, 3.6), 1.6))
        put(m, soul('stone_red', rng.choice(('reach', 'weep'))), a, r, y - 0.55, yaw + rng.uniform(-40, 40), 1.25)      # the heretic, sitting up in it
    return period, m, g


# ---- 7. Violence --------------------------------------------------------------------------------
def _tree(rng):
    t = Mesh('tree')

    def branch(base, direction, length, radius, depth):
        mid = (base[0] + direction[0] * length * 0.5 + rng.uniform(-0.3, 0.3) * length, base[1] + direction[1] * length * 0.5,
               base[2] + direction[2] * length * 0.5 + rng.uniform(-0.3, 0.3) * length)
        tip = (base[0] + direction[0] * length + rng.uniform(-0.25, 0.25) * length, base[1] + direction[1] * length,
               base[2] + direction[2] * length + rng.uniform(-0.25, 0.25) * length)
        t.tube([base, mid, tip], [radius, radius * 0.7, radius * 0.4 if depth else 0.0], 'black' if depth < 2 else 'bark', 5 if depth else 4, caps=False)
        if depth:
            for _ in range(rng.choice((2, 3))):
                d = (rng.uniform(-1, 1), rng.uniform(0.2, 1.0), rng.uniform(-1, 1))
                n = math.sqrt(sum(c * c for c in d))
                branch(tip if rng.random() < 0.6 else mid, tuple(c / n for c in d), length * rng.uniform(0.5, 0.75), radius * 0.45, depth - 1)
    branch((0, -0.2, 0), (rng.uniform(-0.2, 0.2), 1, rng.uniform(-0.2, 0.2)), rng.uniform(1.8, 3.0), rng.uniform(0.28, 0.42), 2)
    return t


def _centaur():
    t = Folk('centaur')
    t.box((0, 1.25, -0.2), (0.75, 0.8, 2.0), 'stone_dark')
    for x in (-0.28, 0.28):
        for z in (-1.0, 0.6):
            t.tube([(x, 1.0, z), (x, 0.0, z + 0.08)], [0.13, 0.09], 'stone_dark', 4)
    t.tube([(0, 1.4, -1.2), (0, 1.0, -1.9)], [0.1, 0.0], 'black', 4, caps=False)       # tail
    t.merge(soul('stone_dark', 'push'), (0, 1.25, 0.65), (0, 0, 0), 0.85)
    t.tube([(0.2, 1.9, 1.3), (0.2, 2.6, 1.15), (0.2, 3.2, 1.3)], [0.03, 0.04, 0.03], 'wood', 3)      # the bow
    return t


def violence(rng):
    """Three rings, as Dante has them: the river of boiling blood with its centaurs on the bank;
    the wood of the suicides; and the burning sand under a rain of fire."""
    period = 90.0
    m, g = Dress(), Mesh('g')
    # Phlegethon.
    y = 72.0
    ledge(m, y, 10.6, 'blood', thick=1.0, seed=11, jag=0.5)
    ledge(g, y + 0.05, 10.9, 'blood', thick=0.05, seed=11, jag=0.5, r_out=13.2)
    for a in arc(24, rng, 0.5):
        put(m, soul('cab_dark', rng.choice(('reach', 'weep', 'stand'))), a, rng.uniform(11.0, 12.9), y - rng.uniform(1.1, 1.8), rng.uniform(-60, 60), 1.3)
    cent = _centaur()
    for a in arc(6, rng, 0.3):
        put(m, cent, a, 14.0, y + 0.1, rng.choice((-90, 90)) + rng.uniform(-20, 20), 1.25)
    for a in arc(7, rng, 0.4):      # the blood going over the edge, down to the sand
        sheet(g, a, 10.9, y - 0.6, y - rng.uniform(16, 26), rng.uniform(1.4, 3.0), 'cab_dark')
    # The wood of the suicides.
    y = 44.0
    ledge(m, y, 10.9, 'soot', seed=12, jag=0.8)
    for a in arc(20, rng, 0.45):
        put(m, _tree(rng), a, rng.uniform(11.5, 14.0), y, rng.uniform(0, 360), rng.uniform(1.2, 1.9))
    for a in arc(6, rng, 0.45):     # harpies in the branches
        h = Mesh('harpy').blob((0, 0, 0), 0.35, 'wing_dark', 0, scale=(0.8, 1.2, 0.8))
        h.blob((0, 0.5, 0.1), 0.16, 'bone_dark', 0)
        for side in (-1, 1):
            h.face([(side * 0.2, 0.3, 0), (side * 1.5, 0.9, -0.3), (side * 1.1, -0.1, -0.2)], 'wing_dark', both=True)
        put(m, h, a, rng.uniform(11.6, 13.5), y + rng.uniform(4.5, 6.5), rng.uniform(-40, 40), 1.4)
    # The burning sand.
    y = 14.0
    ledge(m, y, 10.6, 'bone_dark', thick=1.2, seed=13, jag=0.4)
    for a in arc(22, rng, 0.5):
        r = rng.uniform(11.2, 14.0)
        kind = rng.random()
        if kind < 0.4:      # flat on their backs
            put(m, soul('skin_red', 'reach'), a, r, y + 0.25, rng.uniform(0, 360), 1.3, (-90, 0, 0))
        elif kind < 0.7:    # huddled
            put(m, soul('skin_red', 'weep'), a, r, y - 0.9, rng.uniform(0, 360), 1.3)
        else:               # running, beating the flames off
            put(m, soul('skin_red', 'reach'), a, r, y, 90 + rng.uniform(-20, 20), 1.3, (12, 0, 0))
    for a in arc(46, rng, 0.5):
        put(g, flame(), a, rng.uniform(11.0, 14.2), y, rng.uniform(0, 360), (rng.uniform(0.3, 0.7), rng.uniform(0.4, 1.3), rng.uniform(0.3, 0.7)))
    return period, m, g


# ---- 8. Fraud -----------------------------------------------------------------------------------
def _fiend():
    """One of the Malebranche: horned, winged, a hooked pole in his hands."""
    t = Folk('fiend')
    t.merge(soul('skin_red', 'push'))
    for side in (-1, 1):
        t.tube([(side * 0.1, 1.78, 0.02), (side * 0.2, 2.05, -0.04)], [0.05, 0.0], 'horn', 4, caps=False)
        t.face([(side * 0.15, 1.4, -0.15), (side * 1.5, 2.3, -0.6), (side * 1.2, 1.0, -0.5)], 'wing_dark', both=True)
        t.face([(side * 0.15, 1.4, -0.15), (side * 1.2, 1.0, -0.5), (side * 0.6, 0.6, -0.35)], 'wing_dark', both=True)
    t.tube([(0.0, 2.3, 0.3), (0.0, 0.2, 1.3)], [0.035, 0.035], 'iron', 4)
    t.tube([(0.0, 0.2, 1.3), (0.2, 0.05, 1.2), (0.25, 0.3, 1.1)], [0.035, 0.03, 0.0], 'iron', 4, caps=False)
    return t


def fraud(rng):
    """Malebolge, the evil ditches, one under another with rock ribs bridging them: the boiling
    pitch and the fiends who guard it; the hypocrites filing by in cloaks of gilded lead; the
    thieves among the serpents, and the false counsellors, each a walking flame."""
    period = 80.0
    m, g = Dress(), Mesh('g')
    fiend = _fiend()
    # The pitch.
    y = 62.0
    ledge(m, y, 10.8, 'black', thick=1.2, seed=21, jag=0.4)
    for a in arc(30, rng, 0.5):
        r = rng.uniform(11.2, 14.5)
        put(m, Mesh('bubble').blob((0, 0, 0), rng.uniform(0.25, 0.7), 'amp', 0, scale=(1.0, 0.45, 1.0)), a, r, y)
        if rng.random() < 0.5:      # an arm, a head, up out of it
            put(m, soul('soot', 'reach'), a + 0.05, r, y - rng.uniform(1.0, 1.4), rng.uniform(0, 360), 1.2)
    for a in arc(9, rng, 0.3):
        put(m, fiend, a, 11.3, y, 180 + rng.uniform(-50, 50), 1.5)
    # The hypocrites.
    y = 40.0
    ledge(m, y, 10.9, 'stone', seed=22, jag=0.3)
    for a in arc(26, rng, 0.25):
        put(m, soul('gold', 'stand'), a, rng.uniform(11.6, 12.4), y, 90 + rng.uniform(-8, 8), 1.35, (16, 0, 0))
    # The thieves, and the flames.
    y = 18.0
    ledge(m, y, 10.7, 'stone_dark', seed=23, jag=0.5)
    for a in arc(16, rng, 0.45):
        r = rng.uniform(11.4, 14.0)
        thief = Folk('thief').merge(soul('bone_dark', rng.choice(('reach', 'weep'))))
        coil = [(0.42 * math.cos(k * 1.3), 0.15 + 0.2 * k, 0.42 * math.sin(k * 1.3)) for k in range(9)]
        thief.tube(coil, [0.1] * 8 + [0.0], 'sign_green', 4, caps=False)
        put(m, thief, a, r, y, rng.uniform(0, 360), 1.3)
    for a in arc(22, rng, 0.5):
        r = rng.uniform(11.0, 14.4)
        snake = [(0.5 * k, 0.08, 0.35 * math.sin(k * 1.7)) for k in range(7)]
        put(m, Mesh('snake').tube(snake, [0.03, 0.1, 0.11, 0.11, 0.1, 0.07, 0.0], 'sign_green', 4, caps=False), a, r, y, rng.uniform(0, 360))
    for a in arc(15, rng, 0.45):
        put(g, flame(), a, rng.uniform(11.2, 13.8), y, rng.uniform(0, 360), (0.9, rng.uniform(2.2, 3.0), 0.9))
    # The ribs of rock from ditch to ditch.
    for top, bottom, count in ((62.0, 40.0, 6), (40.0, 18.0, 6), (18.0, -18.0, 5)):
        for a in arc(count, rng, 0.3):
            rib = [(0, 0, -1.0), (0, -(top - bottom) * 0.25, 2.2), (0, -(top - bottom) * 0.55, 2.6), (0, -(top - bottom) * 0.85, 1.5), (0, -(top - bottom), -1.0)]
            put(m, Mesh('rib').tube(rib, [1.3, 0.9, 0.8, 0.9, 1.3], 'stone', 5, caps=False), a, 14.2, top - 1.0)
    return period, m, g


# ---- 9. Treachery -------------------------------------------------------------------------------
def treachery(rng):
    """Cocytus: the lake frozen hard, the traitors locked in the ice to their necks; and round
    the well above it the giants, chained where they stand."""
    period = 75.0
    m, g = Dress(), Mesh('g')
    # The giants (passed first), on their shelf, taller than the gates of Limbo.
    y = 34.0
    ledge(m, y, 12.4, 'marble_shade', thick=2.0, seed=31, jag=0.6)
    for a in arc(7, rng, 0.15):
        giant = Folk('giant').merge(soul('steel', rng.choice(('stand', 'stand', 'weep'))))
        giant.lathe((0, 0.95, 0), [(0.31, -0.06), (0.31, 0.06)], 'iron', 8)
        giant.lathe((0, 1.38, 0), [(0.3, -0.05), (0.3, 0.05)], 'iron', 8)
        put(m, giant, a, 14.4, y, rng.uniform(-15, 15), rng.uniform(8.5, 10.5))
    # The ice.
    y = 10.0
    ledge(m, y, 10.4, 'cloud', thick=2.4, seed=32, jag=0.7)
    for a in arc(44, rng, 0.5):
        r = rng.uniform(10.9, 14.8)
        if rng.random() < 0.7:
            frozen = Folk('frozen')
            frozen.head.blob((0, 0.12, 0), 0.24, 'marble_shade', 0)
            put(m, frozen, a, r, y)
        else:       # one frozen as he tried to climb out
            put(m, soul('marble_shade', 'reach'), a, r, y - rng.uniform(0.7, 1.2), rng.uniform(0, 360), 1.3)
    for a in arc(30, rng, 0.5):
        r, h = rng.uniform(10.6, 15.0), rng.uniform(0.8, 3.4)
        put(m, Mesh('shard').tube([(0, -0.2, 0), (rng.uniform(-0.5, 0.5), h, rng.uniform(-0.5, 0.5))], [0.32 * h / 2.0, 0.0], 'white', 4, caps=False), a, r, y)
    # Icicles under both shelves, lit from inside.
    for top in (34.0 - 2.0, 10.0 - 2.4):
        for a in arc(40, rng, 0.5):
            h = rng.uniform(1.5, 7.0)
            put(g, Mesh('icicle').tube([(0, 0, 0), (0, -h, 0)], [0.28, 0.0], 'sky', 4, caps=False), a, rng.uniform(11.0, 13.0) + (2.0 if top > 20 else 0.0), top)
    return period, m, g


# ---- the stands -----------------------------------------------------------------------------------
def tier_colour(k):
    """The colour of the circle tier k of the stands stands for: the top tier is Limbo, the one
    by the floor Treachery (as the pit itself narrows)."""
    return LOOKS[len(LOOKS) - 1 - k][7]


def stands_crowd(venue, name, spots, scale, seed):
    """A block of demons for an upper tier of the stands in one mesh: spots are (position, yaw).
    Far enough off that robed, horned shapes with their arms up read as the crowd."""
    def build(m):
        rng = random.Random(seed)
        for at, yaw in spots:
            d = Folk('d').merge(soul(rng.choice(('skin_red', 'crimson', 'cab_red', 'horn')), rng.choice(('reach', 'reach', 'push', 'stand'))))
            for side in (-1, 1):
                d.tube([(side * 0.1, 1.78, 0.02), (side * 0.22, 2.08, -0.03)], [0.055, 0.0], 'bone_dark', 4, caps=False)
            sc = scale * rng.uniform(0.9, 1.1)
            for pts, uvs in d.tris + d.head.tris:
                m.tris.append((tuple((rot((p[0] * sc, p[1] * sc, p[2] * sc), (0, yaw, 0))[0] + at[0], rot((p[0] * sc, p[1] * sc, p[2] * sc), (0, yaw, 0))[1] + at[1],
                                      rot((p[0] * sc, p[1] * sc, p[2] * sc), (0, yaw, 0))[2] + at[2]) for p in pts), uvs))
    return A.prop(venue, name, build)


# ---- the scene ----------------------------------------------------------------------------------
# For each circle: its builder, wall copies, the fall's speed past it (m/s), the wall's tint and
# glow, the glow its dressing gives off (the shaft is nearly unlit), its additive parts' colour and
# power, and the colours of its two lights (from below, from above).
LOOKS = (
    (limbo, 3, 11.0, (0.8, 0.9, 1.1), ((0.5, 0.62, 0.95), 1.5), ((0.6, 0.7, 0.95), 0.5), ((1.0, 0.85, 0.55), 5.0), (0.6, 0.72, 1.0), (0.75, 0.8, 1.0)),
    (lust, 4, 22.0, (0.5, 0.35, 0.55), ((0.8, 0.1, 0.55), 1.3), ((0.9, 0.5, 0.75), 0.4), ((1.0, 0.45, 0.85), 2.2), (1.0, 0.4, 0.75), (0.5, 0.3, 1.0)),
    (gluttony, 4, 12.0, (0.7, 0.7, 0.4), ((0.45, 0.55, 0.2), 2.6), ((0.5, 0.6, 0.3), 0.6), ((1.0, 0.2, 0.05), 6.0), (0.55, 0.8, 0.35), (0.5, 0.6, 0.55)),
    (greed, 4, 12.0, (0.65, 0.5, 0.25), ((1.0, 0.68, 0.18), 1.3), ((1.0, 0.8, 0.4), 0.7), ((1.0, 0.75, 0.25), 3.0), (1.0, 0.75, 0.3), (1.0, 0.6, 0.2)),
    (wrath, 4, 14.0, (0.4, 0.55, 0.55), ((0.15, 0.55, 0.45), 2.2), ((0.5, 0.7, 0.6), 0.45), ((0.9, 1.0, 1.0), 2.4), (0.2, 0.8, 0.65), (1.0, 0.15, 0.1)),
    (heresy, 3, 12.0, (0.55, 0.3, 0.25), ((1.0, 0.24, 0.06), 1.5), ((1.0, 0.35, 0.15), 0.6), ((1.0, 0.5, 0.12), 6.0), (1.0, 0.35, 0.1), (1.0, 0.2, 0.05)),
    (violence, 3, 14.0, (0.5, 0.2, 0.2), ((0.9, 0.07, 0.04), 1.4), ((1.0, 0.4, 0.3), 0.5), ((1.0, 0.85, 0.75), 2.0), (1.0, 0.12, 0.08), (1.0, 0.45, 0.1)),
    (fraud, 3, 13.0, (0.7, 0.66, 0.62), ((0.7, 0.55, 0.28), 2.4), ((1.0, 0.8, 0.5), 1.0), ((1.0, 0.9, 0.8), 3.0), (1.0, 0.7, 0.25), (0.7, 0.7, 0.85)),
    (treachery, 3, 10.0, (0.9, 1.0, 1.1), ((0.45, 0.8, 1.0), 2.6), ((0.6, 0.85, 1.0), 0.9), ((0.7, 0.95, 1.0), 1.6), (0.55, 0.9, 1.0), (0.85, 0.95, 1.0)),
)


def _weather(s, g, V, k):
    """What the air is full of in circle k."""
    at = (AXIS[0], -30.0, AXIS[2])
    puff = A.tex(V, 'Puff')

    def streaks(name, speed, size, colours, rate, most, euler=(0, 0, 0), intensity=5.0, stretch=0.06, noise=1.5, box=(24, 6, 24), pos=at, life=(1.6, 2.6)):
        A.particles(s, g, name, pos, euler, Shape='Box', BoxSize=list(box), Lifetime=list(life), Speed=list(speed), Size=list(size),
                    StartColor=list(colours[0]), StartColor2=list(colours[1]), EndColor=list(colours[2]), Intensity=intensity, Gravity=0.0, Drag=0.0,
                    NoiseStrength=noise, NoiseFrequency=0.4, Blend='Additive', EmissionRate=rate, MaxParticles=most, Alignment='Stretched',
                    StretchFactor=stretch, FadeIn=0.05)

    def mist(name, colours, alpha, rate, most, speed=(14, 22), size=(2.5, 5.0)):
        A.particles(s, g, name, at, Shape='Box', BoxSize=[24, 4, 24], Lifetime=[2.4, 3.6], Speed=list(speed), Size=list(size), EndSize=1.6,
                    StartColor=list(colours[0]), StartColor2=list(colours[1]), EndColor=list(colours[2]), StartAlpha=alpha, EndAlpha=0.0, Gravity=0.0,
                    Drag=0.0, NoiseStrength=0.8, Blend='Alpha', EmissionRate=rate, MaxParticles=most, Texture=puff, FadeIn=0.25)
    if k == 1:
        mist('Mist', ((0.6, 0.66, 0.8), (0.4, 0.45, 0.6), (0.3, 0.33, 0.45)), 0.16, 12, 50, speed=(9, 15), size=(3.5, 7.0))
        streaks('Motes', (16, 26), (0.03, 0.06), ((0.7, 0.8, 1.0), (0.5, 0.6, 0.9), (0.3, 0.4, 0.7)), 60, 180, intensity=2.5, stretch=0.04)
    elif k == 2:
        # The wind: across the shaft, not up it.
        for i, yaw in enumerate((0, 120, 240)):
            a = math.radians(yaw)
            streaks(f'Gale {i}', (30, 46), (0.03, 0.08), ((1.0, 0.6, 0.9), (0.8, 0.3, 0.9), (0.5, 0.1, 0.6)), 70, 150, euler=(0, -yaw, -78),
                    intensity=4.0, stretch=0.09, noise=4.0, box=(10, 22, 30), pos=(AXIS[0] + 16 * math.cos(a), 2.0, AXIS[2] + 16 * math.sin(a)), life=(0.8, 1.3))
        mist('Storm wrack', ((0.35, 0.1, 0.3), (0.2, 0.08, 0.25), (0.1, 0.05, 0.12)), 0.2, 12, 50, speed=(20, 30))
    elif k == 3:
        streaks('Rain', (26, 40), (0.025, 0.05), ((0.6, 0.75, 0.6), (0.45, 0.55, 0.45), (0.3, 0.4, 0.3)), 180, 440, euler=(0, 0, 9), intensity=1.8, stretch=0.1,
                noise=0.3)
        streaks('Hail', (20, 30), (0.07, 0.12), ((0.8, 0.9, 0.85), (0.6, 0.7, 0.65), (0.4, 0.5, 0.45)), 40, 110, euler=(0, 0, 9), intensity=1.6, stretch=0.0, noise=0.6)
        mist('Sleet', ((0.3, 0.36, 0.22), (0.2, 0.25, 0.15), (0.1, 0.13, 0.08)), 0.2, 10, 40)
    elif k == 4:
        streaks('Coin', (14, 24), (0.05, 0.1), ((1.0, 0.85, 0.4), (1.0, 0.7, 0.2), (0.8, 0.45, 0.05)), 80, 240, intensity=5.0, stretch=0.02, noise=2.5)
    elif k == 5:
        mist('Marsh gas', ((0.2, 0.4, 0.33), (0.12, 0.3, 0.26), (0.05, 0.14, 0.12)), 0.22, 14, 55)
        streaks('Spite', (18, 30), (0.04, 0.08), ((1.0, 0.3, 0.2), (1.0, 0.15, 0.1), (0.5, 0.05, 0.03)), 30, 90, intensity=5.0, noise=3.0)
    elif k == 6:
        streaks('Embers', (20, 36), (0.04, 0.1), ((1.0, 0.7, 0.3), (1.0, 0.35, 0.08), (1.0, 0.2, 0.03)), 110, 300, intensity=6.0)
        mist('Tomb smoke', ((0.22, 0.08, 0.04), (0.1, 0.06, 0.05), (0.05, 0.04, 0.04)), 0.24, 14, 55)
    elif k == 7:
        # The rain of fire comes down slower than they do: broad flakes, drifting up past them.
        A.particles(s, g, 'Rain of fire', at, Shape='Box', BoxSize=[26, 6, 26], Lifetime=[3.0, 4.5], Speed=[9, 16], Size=[0.12, 0.34], StartColor=[1.0, 0.7, 0.25],
                    StartColor2=[1.0, 0.4, 0.1], EndColor=[1.0, 0.15, 0.02], Intensity=7.0, Gravity=0.0, Drag=0.0, NoiseStrength=1.2, NoiseFrequency=0.3,
                    Blend='Additive', EmissionRate=90, MaxParticles=420, Texture=puff, FadeIn=0.1, AngularVelocity=[-90, 90])
        mist('Blood steam', ((0.4, 0.04, 0.03), (0.25, 0.03, 0.03), (0.1, 0.02, 0.02)), 0.22, 12, 50)
    elif k == 8:
        mist('Pitch smoke', ((0.3, 0.26, 0.12), (0.16, 0.14, 0.1), (0.06, 0.06, 0.05)), 0.26, 16, 60)
        streaks('Sparks', (18, 30), (0.04, 0.08), ((1.0, 0.85, 0.4), (1.0, 0.6, 0.15), (0.9, 0.3, 0.05)), 60, 170, intensity=5.0, noise=2.5)
    elif k == 9:
        streaks('Snow', (12, 20), (0.04, 0.09), ((0.9, 0.97, 1.0), (0.7, 0.88, 1.0), (0.5, 0.75, 1.0)), 150, 520, euler=(0, 0, 14), intensity=2.2, stretch=0.02,
                noise=2.2, life=(2.2, 3.4))
        mist('Breath of the ice', ((0.75, 0.88, 1.0), (0.55, 0.72, 0.9), (0.35, 0.5, 0.7)), 0.18, 14, 55, speed=(8, 13), size=(3.5, 7.0))


_MADE = None


def made():
    """Every circle's dressing, built once: [(period, dressing, glows, height of its tube)]."""
    global _MADE, _wind
    if _MADE is None:
        _MADE = []
        for k, look in enumerate(LOOKS, 1):
            _wind = DROP if k % 2 else -DROP
            period, solid, glow = look[0](random.Random(100 + k))
            _MADE.append((period, solid, glow, period * look[1]))
        _wind = 0.0
    return _MADE


def travel(k):
    """How far circle k comes up as it arrives (and what is above it goes on up): from tube's
    middle to tube's middle, and one of its periods more, since a tube's ends ride its loop."""
    above = SHAFT if k == 1 else made()[k - 2][3]
    period, _, _, height = made()[k - 1]
    return above / 2 + height / 2 + period


def arrives(V, k):
    """The clip circle k comes up on, and the one what is above it leaves on (the same move)."""
    frames, d = int(TRAVEL * 30), travel(k)
    return (P.clip(V, f'Circle{k}Arrives', frames, [P.track('Position', [(0, (0, -d, 0)), (frames, (0, 0, 0))], 'SmoothStep')]),
            P.clip(V, f'Circle{k}Above', frames, [P.track('Position', [(0, (0, 0, 0)), (frames, (0, d, 0))], 'SmoothStep')]))


def build(s, fall, V):
    """The nine circles under fall (the group the fall shows in)."""
    for k, (maker, copies, speed, tint, (wall_glow, wall_power), (prop_glow, prop_power), (fire_glow, fire_power), below, above) in enumerate(LOOKS, 1):
        name = CIRCLES[k - 1][0]
        period, solid, glow, height = made()[k - 1]
        # There from its flag (far below, under the circle they are in) until the one after next
        # (far above by then); it comes up on its own flag and goes on up on the next.
        g = P.gated(s, fall, f'Circle {k}: {name}', flag(k), True, 1.0, (AXIS[0], -3 * travel(k), AXIS[2]))
        if k + 2 <= len(LOOKS):
            g = P.gated(s, g, f'Circle {k} (until the one after next)', flag(k + 2), False, 1.0, (AXIS[0], 3 * travel(k + 1), AXIS[2]))
        if k < len(LOOKS):
            g = P.play(s, g, f'{name} goes on up', flag(k + 1), arrives(V, k + 1)[1])
        g = P.play(s, g, f'{name} comes up', flag(k), arrives(V, k)[0])
        frames = int(round(period / speed * 30))
        clip = P.clip(V, f'Circle{k}', frames, [P.track('Position', [(0, (0, 0, 0)), (frames, (0, period, 0))])])
        body = P.looping(s, g, 'Streaming', clip)
        solid_mat = A.mat(V, 'Palette', (1, 1, 1), glow=prop_glow, power=prop_power)
        glow_mat = A.mat(V, 'Palette', (0, 0, 0), glow=fire_glow, power=fire_power, additive=True, both=True)
        A.model(s, body, 'Walls', walls(V, f'Circle{k}Walls', period, copies, k * 7), AXIS, (0, 0, 0), 1.0,
                A.mat(V, 'Rock', tint, glow=wall_glow, power=wall_power, tiling=(2, 2)), shadows=False)
        if solid.tris:
            A.model(s, body, name, stack(V, f'Circle{k}', solid, period, copies), AXIS, (0, 0, 0), 1.0, solid_mat, shadows=False)
        if glow.tris:
            A.model(s, body, name + ' glow', stack(V, f'Circle{k}Glow', glow, period, copies), AXIS, (0, 0, 0), 1.0, glow_mat, shadows=False)
        # The damned: each group dips with the beat its own way (on it, every other one, off it),
        # and their heads nod on top of that.
        for i, (bodies, heads) in enumerate(solid.folk):
            if not bodies.tris and not heads.tris:
                continue
            dip, every, late = ((0.12, 1.0, 0.0), (0.2, 2.0, 0.0), (0.1, 1.0, 0.5))[i % 3]
            folk = s.entity(f'{name}, the damned {i}', body, AXIS)
            folk.add({'Type': 'VenueBeat', 'Offset': [0.0, -dip, 0.0], 'Every': every, 'Phase': late, 'Sway': False})
            if bodies.tris:
                A.model(s, folk, 'Bodies', stack(V, f'Circle{k}Folk{i}', bodies, period, copies), (0, 0, 0), (0, 0, 0), 1.0, solid_mat, shadows=False)
            if heads.tris:
                nod = A.model(s, folk, 'Heads', stack(V, f'Circle{k}Heads{i}', heads, period, copies), (0, 0, 0), (0, 0, 0), 1.0, solid_mat, shadows=False)
                nod.add({'Type': 'VenueBeat', 'Offset': [0.0, -0.1, 0.0], 'Every': 1.0, 'Phase': late, 'Sway': False})
        if k == 2:
            rng = random.Random(202)
            for i, (r0, r1, count, seconds) in enumerate(((6.2, 8.6, 22, 5.0), (9.0, 11.6, 34, 8.0))):
                frames = int(seconds * 30)
                spin = P.clip(V, f'Circle2Whirl{i}', frames, [P.track('Rotation', [(0, (0, 0, 0)), (frames // 3, (0, 120, 0)), (2 * frames // 3, (0, 240, 0)), (frames, (0, 359.9, 0))])])
                ring = P.looping(s, g, f'Hurricane {i}', spin, AXIS)
                souls, wind = lust_whirl(V, f'Circle2Whirl{i}', rng, r0, r1, count)
                A.model(s, ring, 'The lustful', souls, (0, 0, 0), (0, 0, 0), 1.0, solid_mat, shadows=False)
                A.model(s, ring, 'Wind', wind, (0, 0, 0), (0, 0, 0), 1.0, A.mat(V, 'Palette', (0, 0, 0), glow=(1.0, 0.5, 0.9), power=0.45, additive=True, both=True), shadows=False)
        if k == 3:
            # Cerberus comes up out of the dark behind the band once the circle is round them,
            # slowly as he passes.
            wait = int(TRAVEL * 30) - 90
            rise = P.clip(V, 'CerberusRises', wait + 450, [P.track('Position', [(0, (0, -190, 0)), (wait, (0, -190, 0)), (wait + 110, (0, -26, 0)), (wait + 350, (0, 18, 0)),
                                                                                (wait + 450, (0, 200, 0))])])
            dog = P.play(s, g, 'Cerberus', flag(3), rise, AXIS)
            beast, eyes = cerberus(V)
            A.model(s, dog, 'Cerberus', beast, (0, 0, 0), (0, 0, 0), 1.0, A.mat(V, 'Palette', (1, 1, 1), glow=(0.9, 0.75, 0.55), power=2.6), shadows=False)
            A.model(s, dog, 'Eyes', eyes, (0, 0, 0), (0, 0, 0), 1.0, A.mat(V, 'Palette', (0, 0, 0), glow=(1.0, 0.5, 0.3), power=2.2, additive=True, both=True), shadows=False)
            s.light('Cerberus glare', dog, (0, 1, 9), 'Point', (1.0, 0.45, 0.2), 700.0, 16, fog=FOG)
        # Its light and its weather don't travel with it: they take over round the band from the
        # last circle's as it comes.
        air = P.gated(s, fall, f'{name}, its air', flag(k), True, FADE, AXIS)
        if k < len(LOOKS):
            air = P.gated(s, air, f'{name}, its air (until the next)', flag(k + 1), False, FADE, AXIS)
        _weather(s, air, V, k)
        A.glow_card(s, air, V, f'{name}, the depth', (AXIS[0], -95, AXIS[2]), 70.0, below, 2.2, (90, 0, 0))
        s.light(f'{name} below', air, (AXIS[0], -12, AXIS[2]), 'Point', below, 2600.0, 45, fog=FOG)
        s.light(f'{name} above', air, (AXIS[0], 16, AXIS[2]), 'Point', above, 1300.0, 40, fog=FOG)
        # The band's own light here: the two above and below only catch the tops and soles of them.
        key = tuple(0.45 + 0.55 * c for c in below)
        for i, x in enumerate((-5.0, 5.0)):
            at = (x, 4.5 - 2.5 * i, -6.5)
            s.light(f'{name} key {i}', air, at, 'Spot', key, 1100.0 - 300.0 * i, 24, rot=look_rotation(at, (x * 0.2, 2.2, 3.5)), inner=20, outer=38, fog=FOG)
