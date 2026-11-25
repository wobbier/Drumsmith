"""The nine circles the band falls through in Free Bird (Design/Highway-to-the-Afterlife.md,
"The nine circles"): Dante's, from Limbo straight under the road they smash through down to
Treachery. Under the ninth is the frozen heart of hell they land in (make_story_afterlife.hell,
story_afterlife_heart), whose stands have nine tiers, one for each circle. Circles 6 to 9 are made
by story_afterlife_lower_circles (lower()); the rest of this module is the machinery they share.

Each circle is a tube of its own rock round the shaft's axis, dressed with what Dante found
there, streaming up past the band on a loop: its shape repeats every 'period' metres, so the loop
never jumps. The circles are stacked, as the pit is: when a circle's story flag lands (circle_1 ..
circle_9) it comes up from under the one they are in while that one goes on up, both at the same
speed, the bare rock of the deep shaft between them for a moment. Nothing pops: the whole swap is
one move, TRAVEL seconds long. The circle above stays where it went until the one after next.

The fall gets faster circle by circle with the guitar (SPEED: 45 m/s in Limbo to 105 in the
ice); each circle streams up past them at its own, and its air (streaks, embers, rain, snow) races
up as much faster.

The ledges go all the way round: each is one whole turn of a spiral, winding down the wall as it
goes (lift), one circle's clockwise, the next one's the other way, its end under its own start.
Three quarters of the turn is the ledge proper, where the damned are (the horseshoe: arc()). The
rest, on the audience side (-z), is no wider than a path along the wall (PATH), bare, because the
venue's own cameras (Wide, Desk, Crane) stand inside it: only the wall goes through those.

The damned are not in the rock's mesh but in crowds of their own (Dress.crowd: bodies and heads,
each on a VenueBeat) and pieces on their own pivots (Dress.piece), and they answer the player:
VenueBeat Calm holds them back while the drums are wrong, Trigger sets them off on the player's
hits, big notes or misses, and a crowd's good and bad twins show by VenueMood. Cerberus sits on
Gluttony's ledge, then runs after the band, level with them, falling behind on bad playing.

The fall never slows for the scenery. The scenery gets its own shots instead (shots()): a camera
riding up with the rock over a knot of each circle's damned, framed to one side clear of the note
highway (the shot's lead), as the band zips down through the shaft beside them and is gone. Such
a camera has to rise with the rock at exactly the rock's speed, so each circle's stream is held
to the song's clock from its flag (VenueStory Mode Clock) and the shot's cue is worked out from
where its ledge then is (pass_time): every moment of the fall in the story manifest is this
module's, written there by running it (python3 Tools/Venues/story_afterlife_circles.py
--manifest). In Lust the camera also goes round the band with the hurricane, as one of the
lustful; in Gluttony it watches over Cerberus's shoulder and then follows his chase.
"""
import json
import os
import sys
import math
import random

import story_afterlife_art as A
import story_afterlife_people as P
from story_afterlife_mesh import Mesh, fbm3, rot
from venuegen import look_rotation

AXIS = (0.0, 0.0, 3.0)      # the shaft's axis in the venue (the band falls about it)
TRAVEL = 5.0                # seconds one circle takes to come up as the one above goes
FADE = 3.0                  # seconds a circle's light and weather take over from the last one's
SHAFT = 390.0               # the height of the shaft under the road, which the first circle follows
DROP = 14.0                 # how far a ledge winds down the wall from one end of its horseshoe to the other
GROUPS = 3                  # how many ways the damned of a circle move
WALL = 16.2                 # the walls' least radius: outside the venue's cameras (the Wide stands 14.5 from the axis)
# The fall's lights are all but out of the haze: its volume is the room's box, which shows as a
# slab of light across a shaft. (Not 0: the renderer sorts lights with no haze last, and they are
# the first a full light cluster drops.)
FOG = 0.02
# How fast the band falls through each circle, m/s: faster circle by circle as the guitar takes
# off, from Limbo to the ice. Each circle streams up past them at its own.
SPEED = (45.0, 52.0, 59.0, 66.0, 73.0, 81.0, 89.0, 97.0, 105.0)
BAND_Y = 2.0                # the height of the middle of the band above the venue's floor
# About when the band passes a circle's two cameras, seconds after its flag (they are timed to
# the nearest moment its ledge is level with them: pass_time).
PASS_AT = {1: (10.5, 20.5), 2: (8.0, None), 3: (8.6, None), 4: (11.0, 24.0), 5: (10.0, 19.5),
           6: (10.0, 19.5), 7: (10.0, 19.5), 8: (7.4, 10.8), 9: (7.2, 10.4)}
ORBIT = (11.5, 7.0, 7.0, 8.8)    # Lust's second shot: seconds after its flag, how long, seconds a lap (the outer ring's), radius
# The arc the venue's cameras stand in, in degrees about the axis (+z is 90, -z is -90): the
# ledges are bare through it and, for most of it, only a path along the wall, this far out.
OPEN = (-128.0, -34.0)
PATH = 15.2
TURN = 360.0 / (OPEN[0] + 360.0 - OPEN[1])     # a ledge's whole turn, in horseshoes

# name, the caption that names it, the section of Free Bird's chart (Rock Band 3's) it comes on
# and how many seconds after that section starts. The guitar solo's sections, one circle each:
# Limbo straight under the road they smash through at the solo's first riff, Treachery thirteen
# seconds into Fraud's (the ice is brief: they are pressing deeper), and the landing in the frozen
# heart of hell on gtr_solo_h (make_story_afterlife.hell and story_afterlife_heart from there).
CIRCLES = (
    ('Limbo', 'The First Circle: Limbo', 'gtr_solo', 0.0),
    ('Lust', 'The Second Circle: Lust', 'gtr_solo_a', 0.0),
    ('Gluttony', 'The Third Circle: Gluttony', 'gtr_solo_b', 0.0),
    ('Greed', 'The Fourth Circle: Greed', 'gtr_solo_c', 0.0),
    ('Wrath', 'The Fifth Circle: Wrath', 'gtr_solo_d', 0.0),
    ('Heresy', 'The Sixth Circle: Heresy', 'gtr_solo_e', 0.0),
    ('Violence', 'The Seventh Circle: Violence', 'gtr_solo_f', 0.0),
    ('Fraud', 'The Eighth Circle: Fraud', 'gtr_solo_g', 0.0),
    ('Treachery', 'The Ninth Circle: Treachery', 'gtr_solo_g', 13.0),
)
# Those sections in the Rock Band 3 chart (seconds), and the recording's length: the cues' at:
# fallback is the share of it, for a recording without sections.
SECTIONS = {'gtr_solo': 304.22, 'gtr_solo_a': 331.23, 'gtr_solo_b': 350.46, 'gtr_solo_c': 369.67, 'gtr_solo_d': 401.32,
            'gtr_solo_e': 426.54, 'gtr_solo_f': 452.0, 'gtr_solo_g': 477.0, 'gtr_solo_h': 502.56}
SONG = 583.07
LANDING = 'gtr_solo_h'      # the section the fall ends on (the landing's own moments are hell's)
CAPTION_AT = 2.0            # seconds after its flag a circle's name comes up, as it closes round them


def flag(k):
    return f'circle_{k}'


def starts(k):
    """Seconds into the chart circle k's flag lands."""
    _, _, section, offset = CIRCLES[k - 1]
    return SECTIONS[section] + offset


def lasts(k):
    """Seconds from circle k's flag to the next one's (the last: to the landing)."""
    return (starts(k + 1) if k < len(CIRCLES) else SECTIONS[LANDING]) - starts(k)


def cue(k, plus=0.0):
    """The manifest's cue for plus seconds after circle k's flag: section, else share of the song."""
    _, _, section, offset = CIRCLES[k - 1]
    share = round(SECTIONS[section] / SONG, 3)
    at = round(offset + plus, 3)
    return f'section:{section}+{at:g}|at:{share}+{at:g}' if at else f'section:{section}|at:{share}'


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


def lift(a, wind=None):
    """How far the ledges (and everything on them) stand above their nominal height at angle a:
    they wind down the wall, by the wind from one end of the horseshoe to the other and on at
    the same slope along the path behind the cameras, a whole turn from the horseshoe's top."""
    t = ((math.degrees(a) - OPEN[1]) % 360.0) / (OPEN[0] + 360.0 - OPEN[1])
    return (_wind if wind is None else wind) * (0.5 - t)


def narrow(a):
    """How much of a path the ledge is at angle a: 0 in the horseshoe, 1 behind the cameras."""
    d = (math.degrees(a) + 180.0) % 360.0 - 180.0
    t = max(0.0, min(1.0, min(d - OPEN[0], OPEN[1] - d) / 12.0))
    return t * t * (3.0 - 2.0 * t)


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
    GROUPS (bodies, heads) in turn instead of into the rock.

    The damned who answer the playing are in crowds and pieces of their own instead:
    crowd(key, beat, head_beat, mood) is a Folk to put figures into (put(folk, soul(), a, r, y)
    as into the dressing), one entity in the scene (VenueBeat from beat, its heads on a child
    with head_beat, VenueMood from mood: dicts of those markers' fields); piece(key, mesh, at,
    euler, scale, beat, mood, glow) is one thing with its own pivot at at (circle space: spol()),
    mesh in its own space about that pivot, euler its rest rotation, its own entity. Both are
    repeated with the tube's copies. A crowd's entity stands on the axis, so its Turn turns it
    about the axis (along the ring) and its Offset moves the whole ring one way; a piece's turn
    about its own pivot (a cage on its chain, a soul leaning into a push)."""

    def __init__(self):
        super().__init__('s')
        self.folk = [(Mesh(f'b{i}'), Mesh(f'h{i}')) for i in range(GROUPS)]
        self.turn = 0
        self.crowds = {}        # key -> (Folk, beat, head_beat, mood), in the order made
        self.pieces = []        # (key, mesh, at, euler, scale, beat, mood, glow)

    def crowd(self, key, beat=None, head_beat=None, mood=None):
        """The crowd key (the same Folk for the same key: its markers are the first call's)."""
        if key not in self.crowds:
            self.crowds[key] = (Folk(f'c{len(self.crowds)}'), beat, head_beat, mood)
        return self.crowds[key][0]

    def piece(self, key, mesh, at, euler=(0, 0, 0), scale=1.0, beat=None, mood=None, glow=False):
        """One thing on its own pivot. Pieces under one key that are the same mesh share its
        model file; keep a circle to about 40 of them (each is an entity, in every copy)."""
        self.pieces.append((key, mesh, tuple(at), tuple(euler), scale, beat, mood, glow))


def put(m, sub, a, r, y, yaw=0.0, scale=1.0, euler=None):
    """Merge sub into m at angle a, radius r, height y (plus the ledges' lift there). sub is built
    facing the axis: its +z points inward, +x along the ring, +y up. yaw turns it about its own
    up first (degrees); euler, if given, is applied before that (to lay a figure down). Into a
    Folk (a crowd), a Folk's heads go to the crowd's heads."""
    ca, sa = math.cos(a), math.sin(a)
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    sc = scale if isinstance(scale, tuple) else (scale, scale, scale)
    y += lift(a)
    parts = [(sub, m)]
    if isinstance(sub, Folk):
        parts = [(sub, m), (sub.head, m.head if isinstance(m, Folk) else m)]
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
    """A shelf of rock round the wall, its top at y, ragged along its lip: one whole turn of a
    spiral from the horseshoe's top, down round it and on along the path behind the cameras to
    under where it began (whole: a level ring, as wide all the way round)."""
    start = 0.0 if whole else math.radians(OPEN[1])

    def lip(a):
        r = r_in + jag * (fbm3(math.cos(a) * 2.2 + seed, seed * 1.7, math.sin(a) * 2.2, 5 + seed) * 2 - 1)
        return r if whole else r + (max(PATH, r) - r) * narrow(a)

    def at(i, r, h):
        # (Not spol: the turn's last corner is a whole turn down from its first, at the same angle.)
        a = start + 2 * math.pi * i / sides
        return pol(a, r, h if whole else h + _wind * (0.5 - TURN * i / sides))
    for i in range(sides):
        r0, r1 = lip(start + 2 * math.pi * i / sides), lip(start + 2 * math.pi * (i + 1) / sides)
        # The turn's two ends are closed off.
        for j, r, end in ((i, r0, i == 0), (i + 1, r1, i == sides - 1)):
            if end and not whole:
                m.face([at(j, r, y), at(j, r_out, y), at(j, r_out, y - thick * 3.2), at(j, r + 0.5, y - thick)], ink, both=True)
        a0 = start + 2 * math.pi * i / sides
        m.face([at(i, r0, y), at(i + 1, r1, y), at(i + 1, r_out, y), at(i, r_out, y)], ink, outward=(0, 1, 0))
        m.face([at(i, r0, y), at(i + 1, r1, y), at(i + 1, r1 + 0.5, y - thick), at(i, r0 + 0.5, y - thick)], ink,
               outward=(-math.cos(a0), -0.2, -math.sin(a0)))
        m.face([at(i, r0 + 0.5, y - thick), at(i + 1, r1 + 0.5, y - thick), at(i + 1, r_out, y - thick * 3.2), at(i, r_out, y - thick * 3.2)], ink,
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
    (hands to the face), reach (arms up), push (arms out in front), fly (arms flung wide), dance
    (one fist up, the other out), swim (both arms up over the head, reaching on), mosh (elbows
    out, fists up)."""
    key = (ink, pose)
    if key not in _SOULS:
        t = Folk('soul')
        t.tube([(0, 0, 0), (0, 0.9, 0.02), (0, 1.46, 0)], [0.32, 0.23, 0.2], ink, 6)
        t.head.blob((0, 1.66, 0.02), 0.17, ink, 0)
        for side in (-1, 1):
            hand = {'stand': (side * 0.3, 0.85, 0.06), 'weep': (side * 0.09, 1.62, 0.2), 'reach': (side * 0.42, 2.05, 0.12),
                    'push': (side * 0.2, 1.22, 0.66), 'fly': (side * 0.85, 1.55, -0.1),
                    'dance': (-0.3, 2.15, 0.1) if side < 0 else (0.75, 1.25, 0.25), 'swim': (side * 0.22, 2.2, 0.35),
                    'mosh': (side * 0.3, 1.75, 0.3)}[pose]
            if pose == 'mosh':
                t.tube([(side * 0.23, 1.4, 0), (side * 0.55, 1.3, 0.1), hand], [0.075, 0.07, 0.06], ink, 4)
            else:
                t.tube([(side * 0.23, 1.4, 0), hand], [0.075, 0.06], ink, 4)
        _SOULS[key] = t
    return _SOULS[key]


def glutton(ink='drum_skin', pose='feast'):
    """A glutton: a fat figure 1.8 high (its feet on the origin, to be sunk to the waist in the
    mire), facing +z, its double chin with its head. Poses: feast (a joint of meat to the mouth),
    wallow (hands on the belly), reach (arms up for more)."""
    key = ('glutton', ink, pose)
    if key not in _SOULS:
        t = Folk('glutton')
        t.blob((0, 0.88, 0.12), 0.56, ink, 1, 0.06, 1.0, 3, (1.15, 0.95, 1.05))
        t.tube([(0, 0.7, 0), (0, 1.2, 0.02), (0, 1.5, 0)], [0.44, 0.42, 0.26], ink, 7)
        t.head.blob((0, 1.7, 0.04), 0.21, ink, 1)
        t.head.blob((0, 1.56, 0.12), 0.15, ink, 0, scale=(1.2, 0.8, 1.0))
        for side in (-1, 1):
            hand = {'feast': (side * 0.14, 1.6, 0.36) if side > 0 else (-0.45, 1.0, 0.5), 'wallow': (side * 0.36, 0.98, 0.58),
                    'reach': (side * 0.48, 2.1, 0.22)}[pose]
            t.tube([(side * 0.36, 1.42, 0), (side * 0.52, 1.15, 0.22), hand], [0.13, 0.12, 0.1], ink, 5)
        if pose == 'feast':
            t.blob((0.16, 1.55, 0.52), 0.13, 'wood', 0, scale=(1.0, 0.8, 1.6))
            t.tube([(0.16, 1.5, 0.66), (0.17, 1.47, 0.84)], [0.03, 0.03], 'bone', 3)
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


# ---- the damned and the playing ---------------------------------------------------------------
# The crowds of circles 1 to 5 answer the player (VenueMood, VenueBeat Calm and Trigger): a good
# crowd shown while the mood is at or over GOOD, its bad twin under it.
GOOD = 0.55


def good(threshold=GOOD):
    return {'Show': 'Good', 'Threshold': threshold, 'Seconds': 1.0}


def bad(threshold=GOOD):
    return {'Show': 'Bad', 'Threshold': threshold, 'Seconds': 1.0}


def along(degrees):
    """A crowd's Turn that moves it this far along the ring, toward the higher angles (a turn
    about +y takes a point the other way round)."""
    return (0.0, -degrees, 0.0)


def _apart(rng, count, avoid=()):
    """count angles over the horseshoe, jittered, none within avoid's (centre, half width) arcs
    (radians)."""
    out = []
    for a in arc(count * 2, rng, 0.8):
        if any(abs(a - c) < w for c, w in avoid):
            continue
        out.append(a)
    rng.shuffle(out)
    return sorted(out[:count])


# ---- 1. Limbo -----------------------------------------------------------------------------------
def limbo(rng):
    """The virtuous unbaptised: no torment, only sighs. A grey twilight, the ruined colonnades
    of the noble castle with its seven gates, and the shades in droves lining both ledges to watch
    the band go by: wallflowers back against the wall, swaying to the music but holding back
    (Calm: they hardly move unless the drums are right); while the player plays well they come
    forward to the lip and dance instead. (The two read apart from across the shaft by where
    they stand: a crowd along the lip for a good player, the lip bare and the shades back
    among the columns for a bad one.)"""
    period = 80.0
    m, g = Dress(), Mesh('g')
    nod = {'Offset': (0, -0.07, 0), 'Every': 1.0, 'Calm': 0.3}
    walls_ = [m.crowd(f'wallflowers {i}', {'Turn': along(0.8 if i else -0.8), 'Sway': True, 'Every': 2.0, 'Phase': 0.5 * i, 'Calm': 0.25}, nod, bad())
              for i in range(2)]
    dancers = [m.crowd(f'dancers {i}', {'Offset': (0, 0.5, 0), 'Every': 1.0, 'Phase': 0.5 * i, 'Calm': 1.0},
                       {'Offset': (0, -0.14, 0), 'Every': 0.5, 'Phase': 0.25 * i}, good()) for i in range(2)]

    def shades(y, r_lip, front, back):
        """front shades packed two deep along the lip (watching the shaft the band comes down:
        weeping, hands to their mouths, or just looking), back more against the wall; the dancers
        on the same spots."""
        rows = [(a, r_lip + 0.35 + 0.65 * (i % 2) + rng.uniform(-0.1, 0.1)) for i, a in enumerate(arc(front, rng, 0.3))]
        rows += [(a, rng.uniform(13.6, 15.3)) for a in _apart(rng, back)]
        for i, (a, r) in enumerate(rows):
            # (Robes of a few greys, so that one shade reads against the next.)
            ink = rng.choice(('marble_shade', 'marble_shade', 'stone', 'bone_dark', 'steel'))
            put(walls_[i % 2], soul(ink, rng.choice(('stand', 'weep', 'weep', 'stand', 'weep'))), a, max(r, rng.uniform(13.4, 15.2)), y, rng.uniform(-20, 20), rng.uniform(1.4, 1.6))
            put(dancers[i % 2], soul(ink, rng.choice(('dance', 'reach', 'fly', 'reach'))), a + rng.uniform(-0.01, 0.01), r, y, rng.uniform(-40, 40), rng.uniform(1.4, 1.6))
    # The castle's gates (passed first: the higher ledge).
    ledge(m, 58.0, 11.6, 'stone', seed=3)
    for a in arc(7):
        gate = Mesh('gate')
        for x in (-1.5, 1.5):
            gate.box((x, 3.0, 0), (0.9, 6.0, 1.2), 'marble_shade')
        gate.box((0, 6.5, 0), (4.6, 1.0, 1.5), 'marble')
        gate.box((0, 7.4, 0), (3.4, 0.8, 1.2), 'marble_shade', taper=0.6)
        put(m, gate, a, 13.0, 58.0)
    shades(58.0, 11.6, 60, 0)
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
    shades(20.0, 11.0, 110, 30)
    # The one fire that holds back the dark.
    put(m, Mesh('bowl').lathe((0, 0, 0), [(0.2, 0), (0.25, 1.0), (0.8, 1.4), (0.7, 1.45), (0.0, 1.3)], 'marble_shade', 8), math.radians(90), 11.6, 20.0)
    put(g, flame('lamp'), math.radians(90), 11.6, 21.3, 0, (1.3, 2.2, 1.3))
    return period, m, g


# ---- 2. Lust ------------------------------------------------------------------------------------
def lust_whirl(venue, name, rng, r0, r1, count, rise=0.0):
    """The hurricane: the lustful flung round the shaft for ever, some of them two by two. One
    mesh about the axis; the generator spins it. rise: the souls repeat every rise metres up it
    (a whirl that carries them up and away on a loop), else they are spread 84 m deep. Returns
    (souls, wind streaks)."""
    def build_souls(m):
        for i in range(count):
            a, r, y = rng.uniform(0, 2 * math.pi), rng.uniform(r0, r1), rng.uniform(0, rise) if rise else rng.uniform(-42, 42)
            lay = (rng.uniform(60, 110), 0, rng.uniform(-40, 40))
            for copy in ((-1, 0, 1, 2) if rise else (0,)):
                put(m, soul('bone', 'fly'), a, r, y + copy * rise, 90 + rng.uniform(-25, 25), 1.25, lay)
                if i % 3 == 0:      # a pair, hand in hand
                    put(m, soul('bone', 'reach'), a + 1.3 / r, r + 0.3, y + copy * rise + 0.5, 90, 1.1, lay)

    def build_wind(m):
        for i in range(count // 2):
            a, r, y, sweep = rng.uniform(0, 2 * math.pi), rng.uniform(r0, r1), rng.uniform(-45, 45), rng.uniform(0.5, 1.1)
            lift, w = rng.uniform(-2.5, 2.5), rng.uniform(0.05, 0.14)
            for k in range(8):
                t0, t1 = k / 8, (k + 1) / 8
                m.face([pol(a + sweep * t0, r, y + lift * t0 - w * math.sin(math.pi * t0)), pol(a + sweep * t1, r, y + lift * t1 - w * math.sin(math.pi * t1)),
                        pol(a + sweep * t1, r, y + lift * t1 + w * math.sin(math.pi * t1)), pol(a + sweep * t0, r, y + lift * t0 + w * math.sin(math.pi * t0))], 'white', both=True)
    return A.prop(venue, name, build_souls), A.prop(venue, name + 'Wind', build_wind)


LUST_FLOCK = 30.0           # the height in Lust's period the swimmers are thickest about (its first shot's)


def lust(rng):
    """Bare black rock: the storm is everything here. A few torn crags for the wind to scream on,
    and the lustful along the wall, swimming up against the wind that drags them down, trying to
    get out. While the player plays well they give it up and dance in it instead; while they
    don't, the storm has them, flung every way (and the hurricane round the band whips its own
    souls round faster and up and away: build())."""
    period = 65.0
    m, g = Dress(), Mesh('g')
    for a in arc(9, rng, 0.45):
        y = rng.uniform(0, period)
        crag = Mesh('crag')
        crag.tube([(0, 0, -1.5), (rng.uniform(-1, 1), rng.uniform(0.5, 2.0), 1.5), (rng.uniform(-1.5, 1.5), rng.uniform(1.5, 4.0), 4.2)], [1.5, 0.9, 0.0], 'stone_dark', 5, caps=False)
        put(m, crag, a, WALL, y)
    # Thick about LUST_FLOCK (where the first shot is), thinner up and down the rest of the period.
    def heights(count):
        return [LUST_FLOCK + rng.uniform(-4.5, 5.5) if i % 5 else rng.uniform(0, period) for i in range(count)]
    # Swimming up the wind, arms over their heads, a stroke and a surge up on every beat (two
    # crowds, a half beat apart), dragged back down between.
    swim = [m.crowd(f'swimmers {i}', {'Offset': (0, 1.1, 0), 'Turn': (-6.0 if i else 6.0, 0.0, 0.0), 'Every': 1.0, 'Phase': 0.5 * i, 'Sharp': True, 'Calm': 0.5},
                    {'Offset': (0, 0.1, 0), 'Every': 1.0, 'Phase': 0.5 * i + 0.1}) for i in range(2)]
    for i, (a, y) in enumerate(zip(arc(70, rng, 0.8), heights(70))):
        put(swim[i % 2], soul('bone', 'swim'), a, rng.uniform(12.6, 15.2), y, rng.uniform(-35, 35), rng.uniform(1.45, 1.7), (rng.uniform(-22, 8), 0, rng.uniform(-15, 15)))
    revel = [m.crowd(f'revellers {i}', {'Offset': (0, 0.45, 0), 'Turn': along(1.2 if i else -1.2), 'Every': 1.0, 'Phase': 0.5 * i},
                     {'Offset': (0, -0.15, 0), 'Every': 0.5}, good()) for i in range(2)]
    for i, (a, y) in enumerate(zip(arc(50, rng, 0.8), heights(50))):
        put(revel[i % 2], soul('bone', rng.choice(('dance', 'fly', 'reach'))), a, rng.uniform(12.0, 14.8), y, rng.uniform(-40, 40), rng.uniform(1.4, 1.6), (rng.uniform(-15, 15), 0, rng.uniform(-20, 20)))
    tossed = [m.crowd(f'tossed {i}', {'Turn': (6.0, 0.0, 5.0) if i else (-5.0, 3.0, -6.0), 'Sway': True, 'Every': 1.5 + i, 'Phase': 0.3 * i},
                      {'Offset': (0, 0.25, 0.0), 'Every': 0.5, 'Sharp': True}, bad()) for i in range(2)]
    for i, (a, y) in enumerate(zip(arc(60, rng, 0.8), heights(60))):
        put(tossed[i % 2], soul('bone', rng.choice(('fly', 'swim', 'reach'))), a, rng.uniform(11.8, 15.0), y, rng.uniform(0, 360), rng.uniform(1.4, 1.6),
            (rng.uniform(-150, 150), rng.uniform(-60, 60), rng.uniform(-150, 150)))
    return period, m, g


# ---- 3. Gluttony --------------------------------------------------------------------------------
CERBERUS_AT = 75.0          # degrees: where on Gluttony's lower ledge Cerberus sits (in the horseshoe, toward +z)


def gluttony(rng):
    """The gluttons sit sunk to the waist in freezing mire under a rain that never stops, slime
    hanging off every ledge: fat, still feasting, rocking with the music in the mud (the more,
    the better the playing). Cerberus sits on the lower ledge (his own props: cerberus())."""
    period = 70.0
    m, g = Dress(), Mesh('g')
    # A bad player: sunk to the chin in it, feeding, hardly moving. A good one: up out of it to
    # the belly, arms in the air, bouncing to the beat (so the two read apart from across the
    # shaft).
    fat = [m.crowd(f'gluttons {i}', {'Offset': (0, -0.1, 0), 'Turn': along(0.3 if i else -0.3), 'Every': 2.0, 'Phase': 0.5 * i, 'Calm': 0.3},
                   {'Offset': (0, -0.05, 0), 'Every': 1.0, 'Phase': 0.5 * i, 'Calm': 0.3}, bad()) for i in range(2)]
    up = [m.crowd(f'gluttons up {i}', {'Offset': (0, 0.45, 0), 'Turn': along(1.0 if i else -1.0), 'Every': 1.0, 'Phase': 0.5 * i, 'Calm': 1.0},
                  {'Offset': (0, -0.15, 0), 'Every': 0.5, 'Phase': 0.25 * i}, good()) for i in range(2)]
    dog = math.radians(CERBERUS_AT)
    for y, r_in, seed, sitting in ((50.0, 11.8, 4, 24), (16.0, 10.9, 6, 30)):
        ledge(m, y, r_in, 'deck_dark', thick=1.8, seed=seed, jag=0.9)
        clear = ((dog, math.radians(26)),) if y < 30 else ()
        for i, a in enumerate(_apart(rng, sitting, clear)):
            r, ink, yaw, size = rng.uniform(r_in + 0.7, 15.0), rng.choice(('drum_skin', 'drum_skin', 'skin_red')), rng.uniform(-50, 50), rng.uniform(1.25, 1.5)
            put(fat[i % 2], glutton(ink, rng.choice(('feast', 'feast', 'wallow'))), a, r, y - rng.uniform(1.0, 1.2) * size, yaw, size)
            put(up[i % 2], glutton(ink, rng.choice(('reach', 'reach', 'feast'))), a, r, y - rng.uniform(0.35, 0.5) * size, yaw, size)
        for a in arc(10, rng, 0.45):
            if not any(abs(a - c) < w for c, w in clear):
                put(m, Mesh('pool').lathe((0, 0, 0), [(rng.uniform(0.8, 1.8), 0.03), (0.0, 0.05)], 'glass', 9), a, rng.uniform(r_in + 1.0, 13.5), y)
        for a in arc(34, rng, 0.5):
            r = r_in + rng.uniform(0.5, 2.5)
            h = rng.uniform(1.5, 8.0)
            put(m, Mesh('slime').tube([(0, 0, 0), (rng.uniform(-0.2, 0.2), -h * 0.6, 0), (rng.uniform(-0.3, 0.3), -h, 0)], [0.22, 0.1, 0.0], 'pine', 4, caps=False), a, r, y - 1.9)
    return period, m, g


# Cerberus, built in his own space: facing +z, up +y, his paws on y = 0 standing; his three heads
# on their necks, each as big as a van. The heads are (offset from the neck's root, yaw, the
# tilt of a head cocked at something).
_HEADS = (((-1.9, 0.0, 0.6), -24, 22), ((0.0, 0.9, 1.2), 0, -26), ((1.9, -0.1, 0.6), 22, 30))
CERBERUS_SIZE = 1.4


def _dog_head(m, at, yaw, tilt, ink='grille'):
    """One of his heads at at, looking yaw from +z, cocked by tilt degrees (ears up)."""
    h = Mesh('h')
    h.blob((0, 0, 0), 1.05, ink, 1, 0.12, 1.4, 3, (1.0, 0.95, 1.1))
    h.box((0, -0.05, 1.2), (1.0, 0.55, 1.6), ink, taper=0.8)                          # the muzzle
    h.box((0, -0.68, 0.95), (0.9, 0.22, 1.5), 'stone_dark', euler=(18, 0, 0))         # the jaw, open
    h.blob((0, 0.17, 1.95), 0.22, 'black', 0)
    for side in (-1, 1):
        h.tube([(side * 0.55, 0.55, -0.25), (side * 0.75, 1.65, -0.35)], [0.36, 0.0], ink, 4, caps=False)      # ears, pricked up
        for k in range(3):
            zt = 0.7 + 0.35 * k
            h.tube([(side * 0.38, -0.3, zt), (side * 0.38, -0.62, zt)], [0.09, 0.0], 'bone', 4, caps=False)
    for p, uv in h.tris:
        m.tris.append((tuple(tuple(a + b for a, b in zip(rot(q, (0, yaw, tilt)), at)) for q in p), uv))


def _dog_eyes(m, at, yaw, tilt):
    for side in (-1, 1):
        m.blob(tuple(a + b for a, b in zip(rot((side * 0.42, 0.38, 0.78), (0, yaw, tilt)), at)), 0.2, 'red_lamp', 0)
    m.blob(tuple(a + b for a, b in zip(rot((0, -0.42, 0.95), (0, yaw, tilt)), at)), 0.34, 'ember', 0, scale=(1.0, 0.5, 1.6))


def cerberus(venue):
    """Cerberus as he sits on Gluttony's ledge, his three heads cocked at the band going by, ears
    up (one model), and his eyes and throats (another, to glow). The same beast running is
    cerberus_running()."""
    def build(m):
        m.blob((0, 2.4, -0.6), 1.8, 'grille', 1, 0.15, 1.2, 9, (1.0, 1.15, 1.6))          # haunches and back, sat down
        m.blob((0, 3.3, 1.2), 1.7, 'grille', 1, 0.15, 1.2, 4, (1.15, 1.2, 1.1))            # the chest, up
        for side in (-1, 1):
            m.tube([(side * 0.8, 2.8, 1.6), (side * 0.85, 1.2, 2.1), (side * 0.85, 0.15, 2.3)], [0.55, 0.42, 0.45], 'grille', 6)     # forelegs
            m.blob((side * 1.2, 0.7, -0.8), 1.0, 'grille', 1, 0.1, 1.0, 5, (0.8, 0.8, 1.4))                                       # the hind leg folded
        m.tube([(0, 1.0, -2.3), (0.4, 0.4, -3.6), (1.4, 0.2, -4.4)], [0.35, 0.25, 0.0], 'grille', 5, caps=False)                      # the tail on the ground
        for (x, y, z), yaw, tilt in _HEADS:
            m.tube([(x * 0.35, 3.9, 1.3), (x * 0.8, 4.9 + y * 0.5, 1.8 + z * 0.5)], [0.9, 0.75], 'grille', 7, caps=False)
            _dog_head(m, (x, 5.4 + y, 2.1 + z), yaw, tilt)

    def build_eyes(m):
        for (x, y, z), yaw, tilt in _HEADS:
            _dog_eyes(m, (x, 5.4 + y, 2.1 + z), yaw, tilt)
    return A.prop(venue, 'CerberusSits', build, smooth_=True), A.prop(venue, 'CerberusSitsEyes', build_eyes)


# The running beast's hips and shoulders (its legs' pivots, in its own space) and a leg's length.
_LEGS = {'FrontLeft': (-0.95, 3.0, 2.4), 'FrontRight': (0.95, 3.0, 2.4), 'BackLeft': (-1.0, 3.1, -2.6), 'BackRight': (1.0, 3.1, -2.6)}


def cerberus_running(venue):
    """Cerberus at full stretch: the body (a model about his own origin), one leg (about its
    hip, hanging down to the paw), the eyes. Returns (body, leg, eyes)."""
    def body(m):
        m.blob((0, 3.6, 0), 1.9, 'grille', 1, 0.15, 1.2, 9, (1.05, 0.95, 2.1))                   # a long barrel of a body
        m.blob((0, 3.9, 2.4), 1.7, 'grille', 1, 0.15, 1.2, 4, (1.15, 1.1, 1.0))                  # the chest
        m.tube([(0, 3.9, -3.6), (0, 4.6, -5.2), (0, 5.4, -6.4)], [0.4, 0.28, 0.0], 'grille', 5, caps=False)     # the tail, up
        for (x, y, z), yaw, _ in _HEADS:
            m.tube([(x * 0.35, 4.3, 3.2), (x * 0.9, 4.6 + y * 0.4, 4.6 + z * 0.4)], [0.9, 0.75], 'grille', 7, caps=False)
            _dog_head(m, (x * 1.05, 4.7 + y * 0.5, 5.3 + z), yaw * 0.5, 0.0)

    def leg(m):
        m.tube([(0, 0.3, 0), (0, -1.4, 0.35), (0, -2.6, -0.2), (0, -3.1, 0.25)], [0.6, 0.45, 0.32, 0.42], 'grille', 6)
        m.blob((0, -3.1, 0.45), 0.45, 'grille', 0, scale=(1.0, 0.6, 1.4))
        for k in (-1, 0, 1):
            m.tube([(k * 0.2, -3.2, 0.75), (k * 0.22, -3.35, 1.0)], [0.07, 0.0], 'bone', 3, caps=False)

    def eyes(m):
        for (x, y, z), yaw, _ in _HEADS:
            _dog_eyes(m, (x * 1.05, 4.7 + y * 0.5, 5.3 + z), yaw * 0.5, 0.0)
    return (A.prop(venue, 'CerberusRuns', body, smooth_=True), A.prop(venue, 'CerberusLeg', leg, smooth_=True), A.prop(venue, 'CerberusRunsEyes', eyes))


def gallop(venue, frames=18):
    """The run: a stride every frames (a rotary gallop: the forelegs a little apart, the hind legs
    the other way), the body pitching and heaving with it. Tracks bound to Body and to each leg."""
    def turns(name, phase, reach):
        keys = []
        for f in range(0, frames + 1, 3):
            a = reach * math.sin(2 * math.pi * (f / frames + phase))
            keys.append((f, (a, 0, 0)))
        out = P.track('Rotation', keys)
        out['Binding'] = name
        return out
    heave = [(f, (0, 0.35 * math.sin(4 * math.pi * f / frames), 0.25 * math.sin(2 * math.pi * f / frames))) for f in range(0, frames + 1, 3)]
    pitch = [(f, (4.0 * math.sin(2 * math.pi * (f / frames + 0.25)), 0, 0)) for f in range(0, frames + 1, 3)]
    tracks = [P.track('Position', heave), P.track('Rotation', pitch)]
    tracks += [turns('FrontLeft', 0.0, 38), turns('FrontRight', 0.08, 38), turns('BackLeft', 0.5, 34), turns('BackRight', 0.58, 34)]
    return P.clip(venue, 'CerberusGallop', frames, tracks)


# ---- 4. Greed -----------------------------------------------------------------------------------
def greed(rng):
    """The hoarders and the wasters, rolling great weights for ever up the spiral of their ledge
    with their chests, Sisyphus's work, the gold they fought over heaped against the walls. They
    heave on each big note the player hits (a crash, a kick: VenueBeat Trigger Accent). While the
    playing is good they go up in step, an even column; while it isn't they straggle and bump
    into one another, and slip back on every miss."""
    period = 70.0
    m, g = Dress(), Mesh('g')
    way = 1 if _wind < 0 else -1                 # up the slope: toward the higher angles where the ledge climbs
    rise = abs(_wind) / (OPEN[0] + 360.0 - OPEN[1])      # metres it climbs a degree
    heave = {'Trigger': 'Accent', 'Turn': along(way * 1.6), 'Offset': (0, 1.6 * rise, 0)}
    step = {'Turn': along(way * 0.35), 'Offset': (0, 0.35 * rise, 0), 'Every': 1.0}
    column = m.crowd('the column', heave, {'Offset': (0, -0.1, 0), 'Every': 1.0}, good())
    column_b = m.crowd('the column in step', step, None, good())
    rabble = m.crowd('the rabble', {'Trigger': 'Miss', 'Turn': along(-way * 1.4), 'Offset': (0, -1.4 * rise - 0.15, 0)}, {'Offset': (0.0, -0.2, 0.0), 'Every': 0.75}, bad())
    rabble_b = m.crowd('the rabble bumping', {'Turn': (2.0, along(way * 0.6)[1], -2.0), 'Sway': True, 'Every': 1.5, 'Phase': 0.3}, None, bad())

    def weight(rad, pushers, ink='bone_dark', fallen=False, jumble=None):
        w = Folk('w')
        w.blob((0, rad, 0), rad, 'stone', 1, 0.08, 1.5, int(rng.uniform(0, 99)))
        w.lathe((0, rad, 0), [(rad * 1.04, -0.28), (rad * 1.04, 0.28)], 'gold', 12, axis='x')      # banded with it
        for k in range(pushers):
            x, back, lean = (k - (pushers - 1) / 2) * 0.75, -rad - 0.55 - 0.2 * (k % 2), 16
            yaw = 0
            if jumble:
                x, back, lean, yaw = x + jumble.uniform(-0.6, 0.6), back + jumble.uniform(-1.2, 0.3), jumble.uniform(-10, 40), jumble.uniform(-50, 50)
            if fallen and k == 0:
                w.merge(soul(ink, 'reach'), (x, 0.25, back - 0.6), (-90, yaw, 0))
            else:
                w.merge(soul(ink, 'push'), (x, 0, back), (lean, yaw, 0))
        return w
    for y, seed in ((48.0, 2), (14.0, 8)):
        ledge(m, y, 10.9, 'stone', seed=seed, jag=0.35)
        # In step: one size of weight, three to each, evenly spaced, all facing up the slope. (The
        # weights stand about as high as the men pushing them: bigger, they hid the men.)
        for i, a in enumerate(arc(8)):
            put(column if i % 2 else column_b, weight(0.95, 3), a, 12.3, y, 90 * way)
        # Straggling: about the same places as the column (so a shot finds one or the other), any
        # size, out of line, two or four to a weight, one down.
        spots = [a + rng.uniform(-0.1, 0.1) for a in arc(8)]
        for i, a in enumerate(spots):
            put(rabble if i % 2 else rabble_b, weight(rng.uniform(0.85, 1.15), rng.choice((2, 3, 4)), fallen=rng.random() < 0.35, jumble=rng), a,
                rng.uniform(11.8, 13.0), y, 90 * way + rng.uniform(-25, 25))
        # Heaps of coin, a chest or two.
        for a in arc(13, rng, 0.45):
            size = rng.uniform(1.0, 2.6)
            put(m, Mesh('heap').blob((0, 0, 0), size, 'gold', 1, 0.25, 2.0, int(rng.uniform(0, 99)), (1.0, 0.55, 0.8), floor=0.0), a, rng.uniform(14.6, 15.8), y)
            if rng.random() < 0.4:
                chest = Mesh('chest').box((0, 0.35, 0), (1.3, 0.7, 0.8), 'wood')
                chest.box((0, 0.85, -0.25), (1.3, 0.2, 0.8), 'gold_dark', euler=(-50, 0, 0))
                chest.blob((0, 0.75, 0), 0.45, 'gold', 0, scale=(1.2, 0.5, 0.7))
                put(m, chest, a + 0.12, 14.4, y, rng.uniform(-30, 30))
    # Seams of gold in the wall between the roads.
    for a in arc(16, rng, 0.5):
        y = rng.uniform(0, period)
        sheet(g, a, WALL - 0.2, y + rng.uniform(4, 9), y, rng.uniform(0.8, 1.6), 'gold_dark')
    return period, m, g


# ---- 5. Wrath -----------------------------------------------------------------------------------
def wrath(rng):
    """The Styx: the spiral of the ledge is a river running down round the wall, and the
    wrathful in it a pool party gone to a mosh pit, waist deep, shoving each other about on the
    beat while the player hits (it dies down to sullen shuffling while they miss: Calm), and
    shoved again on every note hit; rubber rings and a ball bobbing among them, the sullen under
    the water; the watchtower with its two fires, and the ferryman's boat."""
    period = 65.0
    m, g = Dress(), Mesh('g')
    y = 22.0
    ledge(m, y, 10.6, 'pine_dark', thick=1.0, seed=5, jag=0.6)
    ledge(g, y + 0.06, 10.8, 'navy', thick=0.05, seed=5, jag=0.6, r_out=15.6)       # the river's skin, lit
    pit = [m.crowd('mosh pit', {'Turn': along(1.6), 'Offset': (0, 0.25, 0), 'Every': 1.0, 'Calm': 0.1}, {'Offset': (0, -0.16, 0), 'Every': 0.5, 'Calm': 0.15}),
           m.crowd('mosh pit back', {'Turn': along(-1.6), 'Offset': (0, 0.2, 0), 'Every': 1.0, 'Phase': 0.5, 'Calm': 0.1}, {'Offset': (0, -0.16, 0), 'Every': 0.5, 'Phase': 0.25, 'Calm': 0.15}),
           m.crowd('mosh pit jumping', {'Offset': (0, 0.55, 0), 'Every': 1.0, 'Phase': 0.25, 'Calm': 0.05}, {'Offset': (0, -0.12, 0), 'Every': 0.5, 'Calm': 0.15}),
           m.crowd('mosh pit shoved', {'Trigger': 'Hit', 'Turn': (1.5, along(0.9)[1], -1.5), 'Offset': (0, 0.2, 0)}, {'Offset': (0, -0.1, 0), 'Every': 1.0})]
    for i, a in enumerate(arc(46, rng, 0.6)):
        r = rng.uniform(11.2, 14.6)
        pose = rng.choice(('mosh', 'mosh', 'push', 'reach', 'mosh'))
        put(pit[i % 4], soul('stone_red', pose), a, r, y - rng.uniform(0.7, 1.0), rng.uniform(0, 360), rng.uniform(1.25, 1.4))
    floats = m.crowd('floats', {'Offset': (0, 0.18, 0), 'Sway': True, 'Every': 2.0, 'Calm': 0.4})
    for i, a in enumerate(arc(12, rng, 0.8)):
        r = rng.uniform(11.4, 14.2)
        if i % 3 == 2:
            put(floats, Mesh('ball').blob((0, 0.32, 0), 0.38, rng.choice(('gold', 'white', 'drum_red')), 1), a, r, y)
        else:
            put(floats, Mesh('ring').lathe((0, 0.1, 0), [(0.45, 0.0), (0.62, 0.16), (0.8, 0.0), (0.62, -0.16), (0.45, 0.0)], rng.choice(('drum_red', 'white', 'hivis')), 10), a, r, y,
                0, 1.0, (rng.uniform(-12, 12), 0, rng.uniform(-12, 12)))
    for a in arc(22, rng, 0.5):     # the sullen: no more than the tops of their heads
        sunk = Folk('sunk')
        sunk.head.blob((0, 0, 0), 0.19, 'grille', 0)
        put(m, sunk, a, rng.uniform(11.0, 14.0), y + 0.02)
    for a in arc(30, rng, 0.5):     # reeds
        r, h = rng.uniform(13.6, 15.2), rng.uniform(0.8, 2.2)
        put(m, Mesh('reed').tube([(0, 0, 0), (rng.uniform(-0.3, 0.3), h, rng.uniform(-0.3, 0.3))], [0.04, 0.0], 'pine', 3, caps=False), a, r, y)
    # The tower, and its two signal fires.
    ta = math.radians(128)
    tower = Mesh('tower').box((0, 5.5, 0), (2.8, 11.0, 2.8), 'stone_dark', taper=0.78)
    tower.box((0, 11.3, 0), (2.9, 0.6, 2.9), 'stone')
    put(m, tower, ta, 14.0, y)
    for x in (-0.7, 0.7):
        put(g, flame(), ta + x / 14.0, 14.0, y + 11.6, 0, (0.9, 2.4, 0.9))
    # Phlegyas and his boat.
    boat = Folk('boat')
    boat.box((0, 0.25, 0), (1.5, 0.5, 5.0), 'deck_dark', taper=1.25)
    boat.box((0, 0.5, 2.7), (0.5, 0.9, 0.6), 'deck_dark', taper=0.5)
    boat.merge(soul('black', 'push'), (0, 0.45, -1.4))
    boat.tube([(0.5, -0.6, -0.6), (0.3, 3.0, -1.1)], [0.05, 0.05], 'wood', 4)
    put(m, boat, math.radians(58), 11.9, y, 80)
    # The water coming down the wall into it, and going on down over the lip.
    for a in arc(9, rng, 0.4):
        sheet(g, a, WALL - 0.2, y + rng.uniform(18, 30), y + 0.1, rng.uniform(1.5, 3.0), 'navy')
        sheet(g, a + 0.2, 11.0, y - 1.0, y - rng.uniform(14, 22), rng.uniform(1.0, 2.2), 'navy')
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
    return LOOKS[len(LOOKS) - 1 - k][5]


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
_LOWER = {}


def lower(name):
    """Circle 6..9's maker (heresy, violence, fraud, treachery): story_afterlife_lower_circles'
    once that module is there and imports (it imports this one, so it is looked up only when the
    circle is built), until then the one in this module."""
    def make(rng):
        if 'module' not in _LOWER:
            try:
                import story_afterlife_lower_circles as module
            except Exception as e:      # not written yet, or half written
                if not isinstance(e, ModuleNotFoundError) or e.name != 'story_afterlife_lower_circles':
                    print(f'story_afterlife_lower_circles does not import ({type(e).__name__}: {e}): circles 6 to 9 are the old ones', file=sys.stderr)
                module = None
            _LOWER['module'] = module
        maker = getattr(_LOWER['module'], name, None) if _LOWER['module'] else None
        return (maker or globals()[name])(rng)
    make.__name__ = name
    return make


# For each circle: its builder, the wall's tint and glow, the glow its dressing gives off (the
# shaft is nearly unlit), its additive parts' colour and power, and the colours of its two lights
# (from below, from above). (Its speed is SPEED's; its copies are copies(k).) Rows 6 to 9 are
# story_afterlife_lower_circles' (lower(): its makers once it is there and imports).
LOOKS = (
    (limbo, (0.8, 0.9, 1.1), ((0.5, 0.62, 0.95), 1.5), ((0.6, 0.7, 0.95), 0.5), ((1.0, 0.85, 0.55), 5.0), (0.6, 0.72, 1.0), (0.75, 0.8, 1.0)),
    (lust, (0.5, 0.35, 0.55), ((0.8, 0.1, 0.55), 1.3), ((0.9, 0.5, 0.75), 0.4), ((1.0, 0.45, 0.85), 2.2), (1.0, 0.4, 0.75), (0.5, 0.3, 1.0)),
    (gluttony, (0.7, 0.7, 0.4), ((0.45, 0.55, 0.2), 2.6), ((0.5, 0.6, 0.3), 0.6), ((1.0, 0.2, 0.05), 6.0), (0.55, 0.8, 0.35), (0.5, 0.6, 0.55)),
    (greed, (0.65, 0.5, 0.25), ((1.0, 0.68, 0.18), 1.3), ((1.0, 0.8, 0.4), 0.7), ((1.0, 0.75, 0.25), 3.0), (1.0, 0.75, 0.3), (1.0, 0.6, 0.2)),
    (wrath, (0.4, 0.55, 0.55), ((0.15, 0.55, 0.45), 2.2), ((0.5, 0.7, 0.6), 0.45), ((0.9, 1.0, 1.0), 2.4), (0.2, 0.8, 0.65), (1.0, 0.15, 0.1)),
    (lower('heresy'), (0.55, 0.3, 0.25), ((1.0, 0.24, 0.06), 1.5), ((1.0, 0.4, 0.2), 0.9), ((1.0, 0.5, 0.12), 3.5), (1.0, 0.35, 0.1), (1.0, 0.2, 0.05)),
    (lower('violence'), (0.5, 0.2, 0.2), ((0.9, 0.07, 0.04), 0.9), ((1.0, 0.5, 0.4), 1.0), ((1.0, 0.85, 0.75), 2.0), (1.0, 0.12, 0.08), (1.0, 0.45, 0.1)),
    (lower('fraud'), (0.55, 0.5, 0.48), ((0.7, 0.55, 0.28), 1.5), ((1.0, 0.92, 0.82), 1.1), ((1.0, 0.9, 0.8), 3.0), (1.0, 0.7, 0.25), (0.7, 0.7, 0.85)),
    (lower('treachery'), (0.9, 1.0, 1.1), ((0.45, 0.8, 1.0), 2.6), ((0.6, 0.85, 1.0), 0.6), ((0.7, 0.95, 1.0), 1.6), (0.55, 0.9, 1.0), (0.85, 0.95, 1.0)),
)


def _weather(s, g, V, k):
    """What the air is full of in circle k. Its streaks and mist were set for a fall of 32 m/s:
    they race up past the band as many times faster as the fall through k is (living as much
    shorter, so they still reach as high, and coming as much thicker, so there are as many)."""
    at = (AXIS[0], -30.0, AXIS[2])
    puff = A.tex(V, 'Puff')
    rush = SPEED[k - 1] / 32.0

    def streaks(name, speed, size, colours, rate, most, euler=(0, 0, 0), intensity=5.0, stretch=0.06, noise=1.5, box=(24, 6, 24), pos=at, life=(1.6, 2.6)):
        speed, life, rate = [v * rush for v in speed], [v / rush for v in life], rate * rush
        A.particles(s, g, name, pos, euler, Shape='Box', BoxSize=list(box), Lifetime=list(life), Speed=list(speed), Size=list(size),
                    StartColor=list(colours[0]), StartColor2=list(colours[1]), EndColor=list(colours[2]), Intensity=intensity, Gravity=0.0, Drag=0.0,
                    NoiseStrength=noise, NoiseFrequency=0.4, Blend='Additive', EmissionRate=rate, MaxParticles=most, Alignment='Stretched',
                    StretchFactor=stretch, FadeIn=0.05)

    def mist(name, colours, alpha, rate, most, speed=(14, 22), size=(2.5, 5.0)):
        speed, rate = [v * rush for v in speed], rate * rush
        A.particles(s, g, name, at, Shape='Box', BoxSize=[24, 4, 24], Lifetime=[round(2.4 / rush, 3), round(3.6 / rush, 3)], Speed=list(speed), Size=list(size), EndSize=1.6,
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


def clocked(s, parent, label, on, clip_path, pos=(0, 0, 0), loop=True):
    """An entity whose clip is held to the song's clock from the moment the story flag lands
    (VenueStory Mode Clock), and its 'Body' child: put what moves under it."""
    root = s.entity(label, parent, pos)
    body = s.entity('Body', root)
    root.add({'Type': 'Sequence', 'Clip': clip_path, 'PlayOnStart': False, 'Loop': loop, 'Speed': 1.0,
              'Bindings': [{'Slot': 'Body', 'Target': body.guid}]})
    root.add({'Type': 'VenueStory', 'Flag': on, 'WhenSet': True, 'FadeSeconds': 0.0, 'Mode': 'Clock', 'Speed': 1.0})
    return body


_MADE = None


def hold(k):
    """Seconds a shot riding up with circle k's rock holds: shorter as the fall gets faster, so
    that the ride stays inside the tube."""
    return round(max(2.6, min(3.6, 270.0 / SPEED[k - 1])), 2)


def copies(k, period=None):
    """How many periods of circle k are stacked up its tube: enough that a camera riding up with
    the rock for a whole shot (the band level with it half way) has rock round it from start to
    end whatever the loop's phase, and some to spare above and below."""
    period = period or made()[k - 1][0]
    ride = SPEED[k - 1] * hold(k)
    return max(4, int(math.ceil((ride + period + 34.0) / period)))


def made():
    """Every circle's dressing, built once: [(period, dressing, glows, height of its tube)]."""
    global _MADE, _wind
    if _MADE is None:
        _MADE = []
        for k, look in enumerate(LOOKS, 1):
            _wind = DROP if k % 2 else -DROP
            period, solid, glow = look[0](random.Random(100 + k))
            _MADE.append((period, solid, glow, period * copies(k, period)))
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


def _markers(e, beat, mood):
    """Put a VenueBeat (beat: its fields) and a VenueMood (mood: its fields) on e."""
    if beat:
        e.add(dict({'Type': 'VenueBeat', 'Offset': [0.0, 0.0, 0.0], 'Sway': False}, **{f: list(v) if isinstance(v, tuple) else v for f, v in beat.items()}))
    if mood:
        e.add(dict({'Type': 'VenueMood'}, **{f: list(v) if isinstance(v, tuple) else v for f, v in mood.items()}))
    return e


def _moves(beat, mood):
    """Whether beat and mood both move their entity (so the mood needs a parent of its own)."""
    def moved(d, f):
        return d and any(abs(c) > 1e-9 for c in d.get(f, (0, 0, 0)))
    return bool(mood and (moved(mood, 'Offset')) and beat)


def _model_with(s, parent, label, path, pos, euler, material, beat, mood):
    """A model at pos carrying beat and mood (the mood on a parent at pos when both move it)."""
    if _moves(beat, mood):
        parent = _markers(s.entity(label + ' (as the playing goes)', parent, pos), None, mood)
        pos, mood = (0, 0, 0), None
    if path is None:
        return _markers(s.entity(label, parent, pos, euler), beat, mood)
    return _markers(A.model(s, parent, label, path, pos, euler, 1.0, material, shadows=False), beat, mood)


def build(s, fall, V):
    """The nine circles under fall (the group the fall shows in)."""
    for k, (maker, tint, (wall_glow, wall_power), (prop_glow, prop_power), (fire_glow, fire_power), below, above) in enumerate(LOOKS, 1):
        name = CIRCLES[k - 1][0]
        period, solid, glow, height = made()[k - 1]
        n = copies(k, period)
        # There from its flag (far below, under the circle they are in) until the one after next
        # (far above by then); it comes up on its own flag and goes on up on the next.
        g = P.gated(s, fall, f'Circle {k}: {name}', flag(k), True, 1.0, (AXIS[0], -3 * travel(k), AXIS[2]))
        if k + 2 <= len(LOOKS):
            g = P.gated(s, g, f'Circle {k} (until the one after next)', flag(k + 2), False, 1.0, (AXIS[0], 3 * travel(k + 1), AXIS[2]))
        if k < len(LOOKS):
            g = P.play(s, g, f'{name} goes on up', flag(k + 1), arrives(V, k + 1)[1])
        g = P.play(s, g, f'{name} comes up', flag(k), arrives(V, k)[0])
        frames = stream(k)[0]
        clip = P.clip(V, f'Circle{k}', frames, [P.track('Position', [(0, (0, 0, 0)), (frames, (0, period, 0))])])
        # On the song's clock from its flag, so that the shots from its ledges know where they are.
        body = clocked(s, g, 'Streaming', flag(k), clip)
        solid_mat = A.mat(V, 'Palette', (1, 1, 1), glow=prop_glow, power=prop_power)
        glow_mat = A.mat(V, 'Palette', (0, 0, 0), glow=fire_glow, power=fire_power, additive=True, both=True)
        A.model(s, body, 'Walls', walls(V, f'Circle{k}Walls', period, n, k * 7), AXIS, (0, 0, 0), 1.0,
                A.mat(V, 'Rock', tint, glow=wall_glow, power=wall_power, tiling=(2, 2)), shadows=False)
        if solid.tris:
            A.model(s, body, name, stack(V, f'Circle{k}', solid, period, n), AXIS, (0, 0, 0), 1.0, solid_mat, shadows=False)
        if glow.tris:
            A.model(s, body, name + ' glow', stack(V, f'Circle{k}Glow', glow, period, n), AXIS, (0, 0, 0), 1.0, glow_mat, shadows=False)
        # The damned not in a crowd of their own: each group dips with the beat its own way (on
        # it, every other one, off it), and their heads nod on top of that.
        for i, (bodies, heads) in enumerate(solid.folk):
            if not bodies.tris and not heads.tris:
                continue
            dip, every, late = ((0.12, 1.0, 0.0), (0.2, 2.0, 0.0), (0.1, 1.0, 0.5))[i % 3]
            folk = s.entity(f'{name}, the damned {i}', body, AXIS)
            folk.add({'Type': 'VenueBeat', 'Offset': [0.0, -dip, 0.0], 'Every': every, 'Phase': late, 'Sway': False})
            if bodies.tris:
                A.model(s, folk, 'Bodies', stack(V, f'Circle{k}Folk{i}', bodies, period, n), (0, 0, 0), (0, 0, 0), 1.0, solid_mat, shadows=False)
            if heads.tris:
                nod = A.model(s, folk, 'Heads', stack(V, f'Circle{k}Heads{i}', heads, period, n), (0, 0, 0), (0, 0, 0), 1.0, solid_mat, shadows=False)
                nod.add({'Type': 'VenueBeat', 'Offset': [0.0, -0.1, 0.0], 'Every': 1.0, 'Phase': late, 'Sway': False})
        # The crowds (Dress.crowd): one entity each on the axis, their heads on a child.
        for i, (key, (crowd, beat, head_beat, mood)) in enumerate(solid.crowds.items()):
            if not crowd.tris and not crowd.head.tris:
                continue
            file = f'Circle{k}Crowd{i}'
            e = _model_with(s, body, f'{name}: {key}', stack(V, file, crowd, period, n) if crowd.tris else None, AXIS, (0, 0, 0), solid_mat, beat, mood)
            if crowd.head.tris:
                _markers(A.model(s, e, 'Heads', stack(V, file + 'Heads', crowd.head, period, n), (0, 0, 0), (0, 0, 0), 1.0, solid_mat, shadows=False), head_beat, None)
        # The pieces (Dress.piece): each on its own pivot, once in every copy of the period.
        files = {}
        for key, mesh, at, euler, scale, beat, mood, lit in solid.pieces:
            known = files.setdefault(key, [])
            for j, (seen, _) in enumerate(known):
                if seen is mesh:
                    path = known[j][1]
                    break
            else:
                whole = Mesh(mesh.name)
                whole.merge(mesh)
                if isinstance(mesh, Folk):
                    whole.merge(mesh.head)
                path = A.prop(V, f'Circle{k}Piece_{"".join(c for c in key.title() if c.isalnum())}{len(known) or ""}', lambda m, w=whole: m.merge(w))
                known.append((mesh, path))
            for j in range(n):
                pos = (AXIS[0] + at[0], AXIS[1] + at[1] + (j - n / 2.0) * period, AXIS[2] + at[2])
                e = _model_with(s, body, f'{name}: {key}', path, pos, euler, glow_mat if lit else solid_mat, beat, mood)
                if scale != 1.0:
                    sc = scale if isinstance(scale, tuple) else (scale, scale, scale)
                    for c in e.components:
                        if c.get('Type') == 'Transform':
                            c['Scale'] = [float(v) for v in sc]
        if k == 2:
            # The hurricane round the band (not on the rock: it goes round with them, as fast as
            # they fall). While the playing is bad it whips them round faster (VenueMood Speed),
            # and a third whirl takes souls up and away off it, out of the crowd.
            rng = random.Random(202)
            wind_mat = A.mat(V, 'Palette', (0, 0, 0), glow=(1.0, 0.5, 0.9), power=0.45, additive=True, both=True)
            for i, (r0, r1, count, seconds) in enumerate(((6.2, 8.6, 22, 5.0), (9.0, 11.6, 34, 8.0))):
                frames = int(seconds * 30)
                spin = P.clip(V, f'Circle2Whirl{i}', frames, [P.track('Rotation', [(0, (0, 0, 0)), (frames // 3, (0, 120, 0)), (2 * frames // 3, (0, 240, 0)), (frames, (0, 359.9, 0))])])
                ring = P.looping(s, g, f'Hurricane {i}', spin, AXIS)
                _markers(s.entities[-2], None, {'Speed': 2.4, 'Seconds': 1.5})
                souls, wind = lust_whirl(V, f'Circle2Whirl{i}', rng, r0, r1, count)
                A.model(s, ring, 'The lustful', souls, (0, 0, 0), (0, 0, 0), 1.0, solid_mat, shadows=False)
                A.model(s, ring, 'Wind', wind, (0, 0, 0), (0, 0, 0), 1.0, wind_mat, shadows=False)
            rise, frames = 36.0, 75
            away = P.clip(V, 'Circle2Away', frames, [P.track('Position', [(0, (0, 0, 0)), (frames, (0, rise, 0))]),
                                                      P.track('Rotation', [(0, (0, 0, 0)), (frames // 3, (0, -120, 0)), (2 * frames // 3, (0, -240, 0)), (frames, (0, -359.9, 0))])])
            cycled = _markers(s.entity('Hurricane, taking them away', g, AXIS), None, bad())
            ring = P.looping(s, cycled, 'Up and away', away)
            souls, _ = lust_whirl(V, 'Circle2Away', rng, 4.5, 12.0, 26, rise)
            A.model(s, ring, 'The lustful, going', souls, (0, -1.5 * rise, 0), (0, 0, 0), 1.0, solid_mat, shadows=False)
        if k == 3:
            # Cerberus: sat on the lower ledge going up with it (his own clip, as fast as the
            # rock), until in_circle_3_c; then running after the band, his own clip from that
            # flag, under a VenueMood that leaves him behind them while the playing is bad.
            sits, runs = cerberus_clips(V)
            glow_eyes = A.mat(V, 'Palette', (0, 0, 0), glow=(1.0, 0.5, 0.3), power=2.2, additive=True, both=True)
            hide = A.mat(V, 'Palette', (1, 1, 1), glow=(0.9, 0.75, 0.55), power=2.6)
            sat = clocked(s, P.between(s, g, 'Cerberus, sitting', None, 'in_circle_3_c', 0.0, AXIS), 'Cerberus sits', flag(3), sits, loop=False)
            beast, eyes = cerberus(V)
            A.model(s, sat, 'Cerberus', beast, (0, 0, 0), (0, 0, 0), CERBERUS_SIZE, hide, shadows=False)
            A.model(s, sat, 'Eyes', eyes, (0, 0, 0), (0, 0, 0), CERBERUS_SIZE, glow_eyes, shadows=False)
            behind = _markers(s.entity('Cerberus, as the playing goes', g), None, {'Offset': (0.0, 26.0, 0.0), 'Seconds': 1.5})
            run = clocked(s, P.between(s, behind, 'Cerberus, running', 'in_circle_3_c', None, 0.0, AXIS), 'Cerberus runs', 'in_circle_3_c', runs, loop=False)
            body, leg, run_eyes = cerberus_running(V)
            stride = s.entity('Gallop', run, (0, 0, 0), (0, 0, 0), (CERBERUS_RUN_SIZE,) * 3)
            torso = s.entity('Body', stride)
            A.model(s, torso, 'Cerberus', body, (0, 0, 0), (0, 0, 0), 1.0, hide, shadows=False)
            A.model(s, torso, 'Eyes', run_eyes, (0, 0, 0), (0, 0, 0), 1.0, glow_eyes, shadows=False)
            bindings = [{'Slot': 'Body', 'Target': torso.guid}]
            for slot, hip in _LEGS.items():
                limb = A.model(s, torso, slot, leg, hip, (0, 0, 0), 1.0, hide, shadows=False)
                bindings.append({'Slot': slot, 'Target': limb.guid})
            stride.add({'Type': 'Sequence', 'Clip': gallop(V), 'PlayOnStart': True, 'Loop': True, 'Speed': 1.0, 'Bindings': bindings})
            s.light('Cerberus glare', torso, (0, 4.5, 7), 'Point', (1.0, 0.45, 0.2), 900.0, 18, fog=FOG)
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


# ---- the shots from inside the circles ----------------------------------------------------------
# Each circle's two shots are of its damned: a camera standing among them on a ledge, riding up
# with the rock (bolted: tagged lin), framing a knot of them doing what they do there, the shaft
# off to one side (the story tag's lead turns the picture so they sit clear of the note highway);
# the band drops through the shaft side of the picture half way through and is gone. VIEWS[k]
# says what each one is of, a dict:
#   y        the ledge's top in the period (where the subject stands; Lust's: where its swimmers are thickest)
#   subject  the crowds' and pieces' keys (Dress.crowd, Dress.piece) to frame (None: all of the circle's)
#   eye      the camera's height above the ledge (1.6): over the heads of a crowd, looking down into it
#   near     (least, most) metres from the camera to the figures it frames (5, 9)
#   stand    (least, most) radius the camera may stand at (11.6, WALL - 0.9)
#   depth    (below, above) the ledge's top the figures framed may be (-1, 4.5)
#   fov      the field of view (55)
#   lead     'l' or 'r' (None: toward the side the figures are on, the shaft on the other)
#   at, look the camera set by hand instead: at (radius, height over the ledge) and looking at look
#            (degrees on round the ring from it, radius, height over the ledge), shooting along a line
#            of them or close on a few; the ring is searched for where that frames the most of them
#   clear    no figure nearer than this in the picture (5 m; less for a shot close among them)
#   nudge    degrees the picture is turned on past the lead, away from its side (the subject further out)
#   do       what the shot shows (the manifest's Do)
# VIEWS[6] .. VIEWS[9] are story_afterlife_lower_circles' (it may set them on this module).
VIEWS = {
    1: ({'y': 20.0, 'at': (10.0, 2.0), 'look': (28.0, 11.8, 1.9), 'subject': ('wallflowers 0', 'wallflowers 1', 'dancers 0', 'dancers 1'), 'near': (3.0, 16.0), 'clear': 2.6, 'fov': 52.0,
         'do': 'Low along the lip of Limbo\'s colonnade, the shades packed two deep down the line of it, a wall of sad watchers: weeping, hands to their faces, swaying and holding back (dancing when the drums are good); the band drops past them and is gone.'},
        {'y': 20.0, 'eye': 8.4, 'subject': ('wallflowers 0', 'wallflowers 1', 'dancers 0', 'dancers 1'), 'near': (6.0, 13.0),
         'do': 'Over the colonnade, the castle\'s gates above it: the shades in droves along the ledge, watching them go by.'}),
    2: ({'y': LUST_FLOCK, 'at': (11.6, 0.5), 'look': (30.0, 14.0, 2.5), 'subject': ('swimmers 0', 'swimmers 1', 'revellers 0', 'revellers 1', 'tossed 0', 'tossed 1'),
         'near': (2.5, 13.0), 'clear': 2.4, 'depth': (-8.0, 9.0),
         'do': 'In the storm among the lustful along the wall, swimming up against the wind that drags them down (dancing in it when the drums are good, flung about by it when not): the band streaks down past them.'},),
    3: ({'y': 50.0, 'at': (10.4, 1.9), 'look': (30.0, 13.4, 0.8), 'subject': ('gluttons 0', 'gluttons 1', 'gluttons up 0', 'gluttons up 1'), 'near': (4.0, 12.0), 'clear': 4.0,
         'do': 'Low over the mire, the gluttons sunk to the waist in it, fat, still feasting, rocking to the music under the rain: the band falls past them.'},),
    4: ({'y': 48.0, 'at': (7.2, 1.5), 'look': (-7.0, 12.3, 1.2), 'subject': ('the column', 'the column in step', 'the rabble', 'the rabble bumping'), 'near': (5.0, 10.0), 'clear': 3.8, 'fov': 52.0, 'nudge': 16.0,
         'do': 'Side on to a team of the hoarders from out in the shaft, a little below them: three men shoving a boulder up the slope with their chests, heaving on the big notes (in step when the drums are good, bumping into each other when not); the band falls past behind.'},
        {'y': 14.0, 'at': (10.0, 3.2), 'look': (40.0, 12.3, 1.2), 'subject': ('the column', 'the column in step', 'the rabble', 'the rabble bumping'), 'near': (4.0, 22.0), 'clear': 3.5,
         'do': 'Along the wasters\' road, up the slope: the whole column of boulders and pushers winding up it into the distance.'}),
    5: ({'y': 22.0, 'eye': 5.0, 'subject': ('mosh pit', 'mosh pit back', 'mosh pit jumping', 'mosh pit shoved'), 'near': (4.5, 9.0),
         'do': 'Waist deep in the Styx among the wrathful: the river is a pool party and a mosh pit, shoving each other about on the beat (it dies down when the drums are wrong): the band falls past the watchtower\'s fires.'},
        {'y': 22.0, 'eye': 5.5, 'subject': ('mosh pit', 'mosh pit back', 'mosh pit jumping', 'floats'), 'near': (5.0, 10.0),
         'do': 'The pit from over the reeds on its other side, rings and a ball bobbing in it: the band drops through the marsh gas.'}),
    # 6 to 9 are story_afterlife_lower_circles' (lower).
    6: ({'y': 40.5, 'eye': 0.0, 'subject': ('maiden_face_out',), 'near': (3.5, 6.5), 'depth': (-1.5, 1.5), 'stand': (12.4, 15.4), 'fov': 50.0,
         'do': 'Out among the chains hung from the wall of Dis, beside a maiden as she swings, the face of the damned screaming out of her window, the line of them going on round the ring: swinging to the music when the drums are good, hanging still and red hot when not. The band drops past.'},
        {'y': 44.0, 'eye': 0.0, 'subject': ('maiden', 'maiden_heat', 'flares'), 'near': (5.0, 10.0), 'depth': (-9.0, -2.0), 'stand': (12.4, 15.4),
         'do': 'Looking down past the maidens to the heretics\' burning tombs under them: swinging in time when the drums are good, hanging still while the fires flare up the chains at them when not. The band falls through the smoke.'}),
    7: ({'y': 66.0, 'eye': 2.5, 'subject': ('tree', 'harpies_attacking', 'harpies_driven_off'), 'near': (3.0, 9.0), 'depth': (-1.0, 10.0), 'stand': (14.9, 15.6),
         'do': 'From behind the wood of the suicides, the river glowing beyond it: the twisted trees lashing at the harpies and driving them off over the river when the drums are good, the harpies in them tearing at them when not. The band falls past the branches.'},
        {'y': 21.0, 'eye': 1.3, 'subject': ('river', 'skeletons_dance', 'skeletons_dead'), 'near': (2.5, 5.5), 'stand': (12.0, 15.0),
         'do': 'On the bank of Phlegethon, the murderers in the boiling blood to the waist rocking out and the skeletons on the burning sand up and dancing (under the blood and lying dead when the drums are bad): the band comes down through the rain of fire.'}),
    8: ({'y': 66.0, 'eye': 1.6, 'subject': ('d5_malebranche', 'd5_grafters'), 'near': (2.5, 6.0), 'stand': (12.8, 15.3),
         'do': 'The fifth ditch of Malebolge, a Malebranche\'s hook jabbing in the near side and the grafters coming up out of the boiling pitch: the band falls past the ditches stacked down the spiral.'},
        {'y': 114.0, 'eye': 1.7, 'subject': ('d1_whipper', 'd1_panderers'), 'near': (2.5, 6.0), 'stand': (12.0, 15.3),
         'do': 'The first ditch: the panderers and seducers filing round, a horned demon cracking his whip at them on the beat.'}),
    9: ({'y': 62.0, 'eye': 1.3, 'subject': ('ice_chest',), 'near': (3.0, 6.5), 'fov': 50.0,
         'do': 'Low over the ice of Caina among the traitors frozen in it to the chest: they still rock out, heads banging, when the drums are good (stiff as the ice when not). The band drops through the snow.'},
        {'y': 8.0, 'eye': 2.4, 'subject': ('ice_face', 'ice_horns', 'ice_clawing'), 'near': (2.0, 4.0), 'fov': 36.0,
         'do': 'Deeper, in Judecca: only faces left out of the ice, and a hand making the horns (clawing at nothing when the drums are bad): the band presses on down toward the heart of hell.'}),
}


def stream(k):
    """Circle k's loop: its length in frames, and the speed that comes to (m/s, near its SPEED)."""
    period = made()[k - 1][0]
    frames = int(round(period / SPEED[k - 1] * 30))
    return frames, period * 30.0 / frames


def pass_time(k, y, want):
    """Seconds after circle k's flag at which height y of its period is level with the band, the
    time nearest want. (Its stream starts from nothing on the flag and is under way all through
    the circle's arrival; it is where this says once it has arrived, TRAVEL seconds in.)"""
    period = made()[k - 1][0]
    v = stream(k)[1]
    lap = period / v
    base = ((BAND_Y - y + copies(k) / 2.0 * period) % period) / v
    return base + round((want - base) / lap) * lap


def _right(eye, target):
    """The picture's right, flat (the engine's camera: +x to the right looking down +z)."""
    f = (target[0] - eye[0], target[2] - eye[2])
    n = math.hypot(*f) or 1.0
    return (f[1] / n, -f[0] / n)


def _lead_side(eye, target, other):
    """'l' or 'r': the side of the picture target is on, from eye, with other on the far side."""
    rx, rz = _right(eye, other)
    return 'r' if (target[0] - eye[0]) * rx + (target[2] - eye[2]) * rz > 0 else 'l'


def _points(k):
    """Circle k's dressing as points about the axis: (the solid rock and dressing, corners and
    the middles of faces; {crowd or piece key: the middles of its faces}; every figure's middles)."""
    period, solid, glow, _ = made()[k - 1]
    rock, folk = [], []
    for mesh in [solid, glow]:
        for tri, _ in mesh.tris:
            rock.extend(tri)
            rock.append(tuple(sum(p[i] for p in tri) / len(tri) for i in range(3)))
    keyed = {}
    for key, (crowd, *_) in solid.crowds.items():
        keyed[key] = [tuple(sum(p[i] for p in tri) / len(tri) for i in range(3)) for tri, _ in crowd.tris + crowd.head.tris]
    for key, mesh, at, euler, scale, *_ in solid.pieces:
        sc = scale if isinstance(scale, tuple) else (scale, scale, scale)
        tris = mesh.tris + (mesh.head.tris if isinstance(mesh, Folk) else [])
        keyed.setdefault(key, []).extend(
            tuple(a + b for a, b in zip(rot(tuple(sum(p[i] for p in tri) / len(tri) * sc[i] for i in range(3)), euler), at)) for tri, _ in tris)
    for bodies, heads in solid.folk:
        for tri, _ in bodies.tris + heads.tris:
            folk.append(tuple(sum(p[i] for p in tri) / len(tri) for i in range(3)))
    return rock, keyed, folk


def _frame(k, view, avoid=None):
    """Where the camera for view stands and what it looks at: the spot on its ledge, clear of
    everything, with the most of its subject in a knot 20 to 50 degrees off its line to the axis
    (so the shaft, where the band comes down, is in the other side of the picture), and nothing
    solid between it and them or it and the axis. Returns (its angle in degrees, eye, aim, the
    eye's height in the period, lead); eye and aim are about the axis, heights in the period."""
    period = made()[k - 1][0]
    wind = DROP if k % 2 else -DROP
    rock, keyed, folk = _points(k)
    y_l, eye_h = view['y'], view.get('eye', 1.6)
    near = view.get('near', (5.0, 9.0))
    stand = view.get('stand', (11.6, WALL - 0.9))
    keys = view.get('subject') or list(keyed)

    def dy(a, b):
        return (a - b + period / 2.0) % period - period / 2.0

    def level(p):
        return dy(p[1], y_l + lift(math.atan2(p[2], p[0]), wind))
    subject = [p for key in keys for p in keyed.get(key, [])] or folk
    lo, hi = view.get('depth', (-1.0, 4.5))
    subject = [p for p in subject if lo < level(p) < hi]
    if not subject:
        raise RuntimeError(f'circle {k}: no one to frame on the ledge at {y_l}')
    solid = [p for p in rock if -2.5 < level(p) < 8.0]
    everyone = [p for pts in keyed.values() for p in pts] + folk
    standing = [p for p in solid if level(p) > 0.4]       # what stands up off the ledge (columns, gates, towers)
    a_lo, a_hi = OPEN[1] + 12.0, OPEN[0] + 360.0 - 12.0
    ideal, spread = (near[0] + near[1]) / 2.0, (near[1] - near[0]) / 2.0
    found = []
    for step in range(int((a_hi - a_lo) / 3.0) + 1):
        deg = a_lo + 3.0 * step
        if avoid is not None and abs(deg - avoid) < 45.0:
            continue
        a = math.radians(deg)
        if 'look' in view:
            # Set by hand: from at, toward look (along the ring from the camera), wherever along
            # the ring that frames the most of the subject round look.
            (r, h), (turn, r_look, h_look) = view['at'], view['look']
            c = pol(a, r, y_l + lift(a, wind) + h)
            b = a + math.radians(turn)
            t = pol(b, r_look, y_l + lift(b, wind) + h_look)
            if not is_open(b) and not is_open(a):
                f = A_unit((t[0] - c[0], t[1] - c[1], t[2] - c[2]))
                seen = 0.0
                for p in subject:
                    q = (p[0] - c[0], dy(p[1], c[1]), p[2] - c[2])
                    d = math.sqrt(sum(v * v for v in q))
                    if near[0] < d < near[1] and sum(q[i] * f[i] for i in range(3)) / d > 0.9:
                        seen += math.exp(-((d - ideal) / spread) ** 2)
                if seen > 0:
                    found.append((seen, deg, c, 1, t))
            continue
        r = stand[0]
        while r <= stand[1] + 1e-6:
            c = pol(a, r, y_l + lift(a, wind) + eye_h)
            ax, az = -c[0] / r, -c[2] / r
            for side in (-1, 1):
                seen, sum_ = 0.0, [0.0, 0.0, 0.0]
                for p in subject:
                    px, py, pz = p[0] - c[0], dy(p[1], c[1]), p[2] - c[2]
                    d = math.hypot(px, pz)
                    if not near[0] < d < near[1] or not -0.7 * d - 1.0 < py < 0.35 * d + 0.5:
                        continue
                    off = math.degrees(math.atan2(px * az - pz * ax, px * ax + pz * az)) * side
                    if 18.0 < off < 52.0:
                        w = math.exp(-((d - ideal) / spread) ** 2) * (1.0 - abs(off - 34.0) / 30.0)
                        seen += w
                        for i, q in enumerate((p[0], c[1] + py, p[2])):
                            sum_[i] += q * w
                if seen > 0:
                    found.append((seen, deg, c, side, tuple(v / seen for v in sum_)))
            r += 0.7
    found.sort(key=lambda f: -f[0])

    def clear_of(c, pts, room):
        return not any(abs(p[0] - c[0]) < room and abs(p[2] - c[2]) < room and math.hypot(p[0] - c[0], dy(p[1], c[1]), p[2] - c[2]) < room for p in pts)

    def sightline(c, t, pts, lane, upto=0.85):
        d = (t[0] - c[0], t[1] - c[1], t[2] - c[2])
        n2 = sum(v * v for v in d) or 1.0
        for p in pts:
            q = (p[0] - c[0], dy(p[1], c[1]), p[2] - c[2])
            u = sum(q[i] * d[i] for i in range(3)) / n2
            if 0.08 < u < upto and math.dist(q, tuple(d[i] * u for i in range(3))) < lane:
                return False
        return True
    fov = view.get('fov', 55.0)
    tan_v = math.tan(math.radians(fov / 2.0))
    # Wide enough for 16:9 and the lead's turn either way (about a third of the width).
    tan_h = math.tan(math.atan(tan_v * 16.0 / 9.0) + math.radians(20.0))

    def foreground_clear(c, t, pts, least, cone=None):
        """Nothing in pts nearer than least in the picture (a head or a column filling it):
        within cone (a cosine) of the middle of it, or anywhere in it with no cone."""
        d = (t[0] - c[0], t[1] - c[1], t[2] - c[2])
        n = math.sqrt(sum(v * v for v in d)) or 1.0
        f = tuple(v / n for v in d)
        r = A_unit((f[2], 0.0, -f[0]))
        u = (r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0])
        for p in pts:
            q = (p[0] - c[0], dy(p[1], c[1]), p[2] - c[2])
            m = math.sqrt(sum(v * v for v in q))
            if not 0.0 < m < least:
                continue
            z = sum(q[i] * f[i] for i in range(3))
            if z <= 0.0:
                continue
            if cone is not None:
                if z / m > cone:
                    return False
            elif abs(sum(q[i] * r[i] for i in range(3))) < z * tan_h and abs(sum(q[i] * u[i] for i in range(3))) < z * tan_v:
                return False
        return True
    # Less room about the camera and its lines where a ledge is crowded.
    for room in (1.0, 0.7, 0.5, 0.35):
        for seen, deg, c, side, aim in found[:1500]:
            if not clear_of(c, solid, 0.8 * room) or not clear_of(c, everyone, 2.0 * room):
                continue
            if not sightline(c, aim, solid, 0.3 * room):
                continue
            if not foreground_clear(c, aim, everyone, near[0] * 0.8 * room, 0.85) or not foreground_clear(c, aim, solid, 3.0 * room, 0.85):
                continue
            # (The lead turns the picture half its width off the aim: the whole of it clear close by.)
            if not foreground_clear(c, aim, everyone, view.get('clear', 5.0) * room) or not foreground_clear(c, aim, standing, 4.5 * room):
                continue
            if not sightline(c, (0.0, c[1] - 1.0, 0.0), solid, 0.45 * room, 0.95):
                continue
            lead = view.get('lead') or _lead_side(c, aim, (0.0, c[1], 0.0))
            if '--where' in sys.argv:
                print(f'circle {k} ledge {y_l:g}: at {deg:g} degrees, {math.hypot(c[0], c[2]):.1f} m out, framing {seen:.1f} of them, lead {lead}')
            return deg, c, aim, c[1], lead
    raise RuntimeError(f'circle {k}: nowhere to stand on the ledge at {y_l}')


def _ride(k, eye, aim, fov, seconds, after=0.0):
    """The two ends of a camera's ride up with circle k's rock, seconds long, the band level with
    its eye half way (and after seconds more on the end): eye and aim are in the period (about
    the axis); the views are in the venue."""
    v = stream(k)[1]
    half = v * seconds / 2.0
    out = []
    for sign in (-1, 1):
        y = BAND_Y + sign * half + (v * after if sign > 0 else 0.0)
        at = (AXIS[0] + eye[0], y, AXIS[2] + eye[2])
        to = (AXIS[0] + aim[0], y + aim[1] - eye[1], AXIS[2] + aim[2])
        out.append((tuple(round(c, 3) for c in at), tuple(round(c, 3) for c in to), fov))
    return out


# ---- Cerberus ---------------------------------------------------------------------------------
# He sits on Gluttony's lower ledge (CERBERUS_AT degrees, this far out, this big), going up with
# the rock, his heads cocked at the band as they fall past (in_circle_3_b: over his shoulder);
# then he leaps off it after them and runs head first down through the shaft, level with them,
# between them and the ledges' lips, going round the outside of the fall (in_circle_3_c, the flag he leaps on, follows him) until the next circle takes him away
# above (Gluttony's tube goes on up, and he with it). He falls behind while the player misses
# (VenueMood Offset). He keeps pace with the band, not with the rock: his run is his own clip.
CERBERUS_R = 14.4
CERBERUS_HEADS = 8.8        # his heads' height over his paws, sitting
CERBERUS_RUN_R = 7.4        # his middle's radius as he runs (inside the ledges' lips, outside the band)
CERBERUS_RUN_SIZE = 1.0     # his scale running (sitting: CERBERUS_SIZE)
CERBERUS_TURN = 9.0         # degrees a second he goes round the wall as he runs
CERBERUS_CATCH = 1.7        # seconds from his leap to being level with them
CERBERUS_WATCH = (2.4, 0.9)  # the over-the-shoulder shot: seconds before the band is level with his heads (from the end of the mire's), and after
CERBERUS_CHASE = 5.6        # the chase shot's length


def _euler(forward, up):
    """Euler degrees (rot()'s order) turning +z to forward and +y to up (up made square to it)."""
    f = A_unit(forward)
    u = A_unit(tuple(up[i] - f[i] * sum(up[j] * f[j] for j in range(3)) for i in range(3)))
    x = (u[1] * f[2] - u[2] * f[1], u[2] * f[0] - u[0] * f[2], u[0] * f[1] - u[1] * f[0])
    # R = [x u f] (columns) = Rz Ry Rx.
    b = math.asin(max(-1.0, min(1.0, -x[2])))
    a = math.atan2(u[2], f[2])
    g = math.atan2(x[1], x[0])
    return tuple(round(math.degrees(v), 3) for v in (a, b, g))


def A_unit(v):
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / n for c in v)


def cerberus_times():
    """When the band is level with his heads, and when he leaps: seconds after Gluttony's flag."""
    a = math.radians(CERBERUS_AT)
    t_p = pass_time(3, 16.0 + lift(a, DROP) + CERBERUS_HEADS, PASS_AT[3][0] + 3.0)
    return t_p, t_p + CERBERUS_WATCH[1]


def cerberus_sits(t):
    """Where his paws are (venue, the circle at rest) t seconds after Gluttony's flag, and the
    turn that faces him at the axis."""
    a = math.radians(CERBERUS_AT)
    t_p, _ = cerberus_times()
    v = stream(3)[1]
    x, _, z = pol(a, CERBERUS_R, 0.0)
    return (AXIS[0] + x, BAND_Y - CERBERUS_HEADS + v * (t - t_p), AXIS[2] + z), (0.0, math.degrees(math.atan2(-x, -z)), 0.0)


def cerberus_runs(t):
    """Where he is and how he is turned t seconds after he leaps (his origin, under his paws),
    his angle round the shaft (radians) and where his middle is. He runs head first down through the air inside the
    ledges' lips, his back turned the way he goes round."""
    _, leap = cerberus_times()
    v = stream(3)[1]
    a = math.radians(CERBERUS_AT + CERBERUS_TURN * max(t, 0.0))
    start, sat = cerberus_sits(leap)
    y0 = start[1] + 3.6 * CERBERUS_RUN_SIZE
    # Up off the ledge with the rock's speed, over, and down after them: a curve from going up at
    # v to level with the band at rest, then level (heaving a little as he runs).
    u = min(max(t, 0.0) / CERBERUS_CATCH, 1.0)
    h00, h10, h01 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u, -2 * u ** 3 + 3 * u ** 2
    y = h00 * y0 + h10 * v * CERBERUS_CATCH + h01 * (BAND_Y + 1.0)
    if t > CERBERUS_CATCH:
        y += 1.2 * math.sin((t - CERBERUS_CATCH) * 1.3)
    s = min(max(t, 0.0) / 0.7, 1.0)
    s = s * s * (3 - 2 * s)
    inward = (-math.cos(a), 0.0, -math.sin(a))
    ahead = (-math.sin(a), 0.0, math.cos(a))
    # From sat up facing the axis to head down, his back the way he goes round.
    face = A_unit(tuple(inward[i] * (1 - s) + (-1.0 if i == 1 else 0.0) * s + ahead[i] * 0.25 * s for i in range(3)))
    up = A_unit(tuple((1.0 if i == 1 else 0.0) * (1 - s) + ahead[i] * s for i in range(3)))
    r = CERBERUS_R + (CERBERUS_RUN_R - CERBERUS_R) * s
    x, _, z = pol(a, r, 0.0)
    # (r and y are his middle's: the origin is under his paws.)
    lift_ = 3.6 * CERBERUS_RUN_SIZE
    return (AXIS[0] + x - up[0] * lift_, y - up[1] * lift_, AXIS[2] + z - up[2] * lift_), _euler(face, up), a, (AXIS[0] + x, y, AXIS[2] + z)


def cerberus_clips(V):
    """His two clips: sitting (from Gluttony's flag, going up with the rock until he leaps) and
    running (from the leap, on until the circle has gone)."""
    _, leap = cerberus_times()
    last = int(math.ceil((leap + 1.0) * 30))
    sits = P.clip(V, 'CerberusSits', last, [P.track('Position', [(0, cerberus_sits(0)[0]), (last, cerberus_sits(last / 30.0)[0])]),
                                            P.track('Rotation', [(0, cerberus_sits(0)[1]), (last, cerberus_sits(0)[1])])])
    frames = int(math.ceil((lasts(3) - leap + TRAVEL + 1.0) * 30))
    keys = [(f, cerberus_runs(f / 30.0)) for f in list(range(0, frames, 3)) + [frames]]
    runs = P.clip(V, 'CerberusRuns', frames, [P.track('Position', [(f, r[0]) for f, r in keys]), P.track('Rotation', [(f, r[1]) for f, r in keys])])
    return sits, runs


def cerberus_shots():
    """Over his shoulder as he sits and watches them go by (his heads cocked), then after him as
    he runs down the shaft beside them."""
    t_p, leap = cerberus_times()
    watch = []
    for t in (t_p - CERBERUS_WATCH[0], leap):
        paws, yaw = cerberus_sits(t)
        s = CERBERUS_SIZE

        def local(p):
            q = rot((p[0] * s, p[1] * s, p[2] * s), yaw)
            return (paws[0] + q[0], paws[1] + q[1], paws[2] + q[2])
        eye = local((-5.2, 9.6, -4.6))
        head = local((0.0, 6.0, 4.2))
        # At his middle head (all of it going up with him), turned out to its side of the picture
        # by the lead, so that the heads are clear of the note highway and the shaft the band
        # drops down is the other side. (Aimed between the two, he sat under the highway.)
        watch.append((tuple(round(c, 3) for c in eye), tuple(round(c, 3) for c in head), 52.0))
    out = [{'flag': 'in_circle_3_b', 'circle': 3, 'at': round(t_p - CERBERUS_WATCH[0], 3), 'hold': round(sum(CERBERUS_WATCH), 3), 'views': watch,
            'lead': _lead_side(watch[0][0], watch[0][1], AXIS),
            'do': 'Over Cerberus\'s shoulder on the ledge: the band catches his eye; he stops dead, all three heads cocked, ears up, like a dog, as they drop past his noses.'}]
    chase = []
    steps = 16
    for i in range(steps + 1):
        t = CERBERUS_CHASE * i / steps
        _, _, a, mid = cerberus_runs(t)
        # From well round the shaft from him, a little above his middle, looking across at him
        # with the band between (the shaft, and the band in it, the other side of the picture).
        c = pol(a - math.radians(72.0), 9.0, 0.0)
        eye = (AXIS[0] + c[0], max(mid[1], BAND_Y) + 1.5, AXIS[2] + c[2])
        aim = (mid[0], mid[1] - 1.0, mid[2])
        chase.append((tuple(round(v, 3) for v in eye), tuple(round(v, 3) for v in aim), 62.0))
    lead = _lead_side(chase[-1][0], chase[-1][1], (AXIS[0], BAND_Y, AXIS[2]))
    out.append({'flag': 'in_circle_3_c', 'circle': 3, 'at': round(leap, 3), 'hold': CERBERUS_CHASE, 'views': chase, 'lead': lead,
                'do': 'Cerberus gives chase: off the ledge and head first down the shaft after them, round the outside of the fall, keeping level with the band (falling behind while the drums go wrong).'})
    return out


_SHOTS = None


def shots():
    """The story shots of the fall, two or three to a circle: [{flag, circle, at (seconds after
    the circle's flag), hold, views [(eye, target, fov), ...], lead, hand, do}]. All of them run
    at one speed (the story shot tag 'lin')."""
    global _SHOTS
    if _SHOTS is not None:
        return _SHOTS
    out = []
    for k in range(1, len(LOOKS) + 1):
        stood = None
        for i, view in enumerate(VIEWS[k]):
            try:
                deg, eye, aim, y, lead = _frame(k, view, stood)
                if view.get('nudge'):
                    # Turned on past the lead: the picture swings that many degrees away from
                    # the lead's side, so the subject goes further out to it.
                    fx, fz = aim[0] - eye[0], aim[2] - eye[2]
                    turn = math.radians(view['nudge']) * (1 if lead == 'l' else -1)
                    rx, rz = fz, -fx
                    c, s_ = math.cos(turn), math.sin(turn)
                    aim = (eye[0] + fx * c + rx * s_, aim[1], eye[2] + fz * c + rz * s_)
            except RuntimeError as e:
                if k < 6:
                    raise
                # (Circles 6 to 9 are another module's, and may be half made: a plain look in
                # at the axis over its ledge until its own views find their figures.)
                print(f'{e}: looking in from the wall instead', file=sys.stderr)
                a = math.radians(90.0 + 120.0 * i)
                deg, eye, aim, lead = 90.0 + 120.0 * i, pol(a, 14.5, view['y'] + lift(a, DROP if k % 2 else -DROP) + view.get('eye', 1.6)), None, None
                aim, y = (0.0, eye[1] - 1.0, 0.0), eye[1]
            stood = deg if i == 0 and len(VIEWS[k]) > 1 and VIEWS[k][1]['y'] == view['y'] else None
            seconds = hold(k)
            out.append({'flag': f'in_circle_{k}' + ('_b' if i else ''), 'circle': k, 'at': round(pass_time(k, y, PASS_AT[k][i]) - seconds / 2.0, 3), 'hold': seconds,
                        'views': _ride(k, eye, aim, view.get('fov', 55.0), seconds), 'lead': lead, 'do': view['do'],
                        'ride': (eye, aim, view.get('fov', 55.0))})
        if k == 2:
            # Round the band with the hurricane, in the gap between its two rings and at the
            # outer one's pace: the lustful beside the camera hang there with it, the inner ring
            # overtakes, the band turns in the middle and the wall goes round behind.
            at, held, lap, radius = ORBIT
            steps = int(round(held / lap * 8))
            views = []
            for i in range(steps + 1):
                a = math.radians(-90.0) - 2 * math.pi * i / 8
                eye = (AXIS[0] + radius * math.cos(a), BAND_Y + 0.6 - 1.3 * math.cos(2 * math.pi * i / steps), AXIS[2] + radius * math.sin(a))
                views.append((tuple(round(c, 3) for c in eye), (AXIS[0], BAND_Y, AXIS[2] + 0.4), 60.0))
            out.append({'flag': 'in_circle_2_b', 'circle': k, 'at': at, 'hold': held, 'views': views,
                        'do': 'Round and round the band with the hurricane, as one of the lustful: the others flung past the lens (whipped round faster, and away up the shaft, when the drums go wrong), the band turning in the eye of it.'})
        if k == 3:
            out.extend(cerberus_shots())
    out.sort(key=lambda s: (s['circle'], s['at']))
    # A ride that ends less than a second before the next look in its circle rides on up to it
    # (a little past: the later shot takes the screen), rather than leave the director's own cut
    # a flash of half a second between them; as far as the tube has rock to spare.
    for a, b in zip(out, out[1:]):
        gap = b['at'] - (a['at'] + a['hold'])
        k = a['circle']
        if 'ride' in a and b['circle'] == k and 0.0 < gap < 1.0:
            after = round(gap + 0.05, 3)
            if SPEED[k - 1] * (a['hold'] + after) + made()[k - 1][0] + 34.0 <= made()[k - 1][3]:
                a['views'] = _ride(k, *a['ride'], a['hold'], after)
                a['hold'] = round(a['hold'] + after, 3)
    _SHOTS = out
    return _SHOTS


# What each circle's flag moment says in the manifest.
ARRIVALS = {
    1: 'Straight out from under the road into Limbo: it comes up round them as the shaft goes on up, one move, no cut.',
}


def moments():
    """Every moment of the fall in the story manifest, in order: each circle's flag, its name and
    its shots from inside."""
    out = []
    for k in range(1, len(CIRCLES) + 1):
        name, caption = CIRCLES[k - 1][:2]
        speed = f'{SPEED[k - 1]:g} m/s'
        out.append({'On': cue(k), 'StateAfter': [flag(k)],
                    'Do': ARRIVALS.get(k, f'{name} comes up from under them as the circle above goes on up: one move, {TRAVEL:g} seconds, no cut.') + f' They fall through it at {speed}.'})
        out.append({'On': cue(k, CAPTION_AT), 'StateAfter': [], 'Caption': caption, 'CaptionSeconds': 4, 'Do': 'Its name, as it closes round them.'})
        for shot in (shot for shot in shots() if shot['circle'] == k):
            out.append({'On': cue(k, shot['at']), 'StateAfter': [shot['flag']], 'Shot': 'story/' + shot['flag'], 'Do': shot['do']})
    return out


def sync_manifest(path):
    """Write the fall's moments into the story manifest (Free Bird in highway-afterlife): every
    circle's flag, caption and shot moment is replaced by moments(), where the first of them was."""
    with open(path, encoding='utf-8') as f:
        text = f.read()
    data = json.loads(text)
    tail = '\n' if text.endswith('\n') else ''
    if json.dumps(data, indent=2, ensure_ascii=False) + tail != text:
        raise RuntimeError('the manifest is not laid out the way json.dumps writes it: not touching it')
    captions = {c[1] for c in CIRCLES}
    done = 0
    for song in (song for st in data.get('Sets', []) + data.get('ProposedSets', []) for song in st.get('Songs', [])):
        moments_ = song.get('Moments') or []
        if not any(flag(1) in m.get('StateAfter', []) for m in moments_):
            continue

        def ours(m):
            return m.get('Caption') in captions or any(f.startswith('in_circle_') or f in {flag(k) for k in range(1, len(CIRCLES) + 1)} for f in m.get('StateAfter', []))
        at = next(i for i, m in enumerate(moments_) if ours(m))
        kept = [m for m in moments_ if not ours(m)]
        song['Moments'] = kept[:at] + moments() + kept[at:]
        done += 1
    if done != 1:
        raise RuntimeError(f'found {done} songs with the circles in the manifest')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, indent=2, ensure_ascii=False) + tail)


if __name__ == '__main__':
    for shot in shots():
        print(f"{shot['flag']:16s} +{shot['at']:7.3f} s for {shot['hold']:g} s  from {shot['views'][0][0]} toward {shot['views'][0][1]}")
    if '--manifest' in sys.argv:
        sync_manifest(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Design', 'Story-Mode-Setlists.json'))
        print('Design/Story-Mode-Setlists.json: the circles\' shots written; now run Tools/Story/make_story.py')
