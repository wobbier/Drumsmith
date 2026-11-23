"""The rescue on Earth that My Hero cuts away to (Design/Highway-to-the-Afterlife.md, "5. Foo
Fighters - My Hero"), far off along +x in heaven's scene. Each cut to Earth is the next thing that
happens to the band, one place at a time, each on its own story flag:

  cpr            the crash site at night: the cop's hands on the drummer's chest (slow motion)
  loading        the same road: the drummer on a gurney going into the back of an ambulance
  ambulance_run  the highway: the ambulance at speed inside an escort of cruisers, a helicopter over it
  defib          inside that ambulance: paddles on the drummer's chest, everything on a hook or a
                 strap swinging; the shock itself is the flag 'shock'
  gurney         a hospital corridor: the four of them rushed down it on gurneys, shot from the
                 foot of the drummer's
  resurrection   a ward of the hospital in daylight: the four of them sitting up in their beds,
                 looking out of the window at the sky (the engine's procedural sky: the shot is
                 tagged sky), shot from behind them as the song rings out

A place shows only between its own flag and the next place's (VenueStory groups, no fade: they
are cuts), so its lights and particles are off the rest of the time. The camera spots can't ride
on anything (the director reads them once), so wherever the camera is "on" a vehicle the vehicle
stands still and the world goes by it on loops, as the highway does under the flatbed in
Kickstart My Heart; the shots are tagged ride (Director: the camera takes the road).
Nothing here is simulated: what dangles swings on looping clips, out of step with each other.
"""
import json
import math
import os
import random

import story_afterlife_art as A
import story_afterlife_people as P
from story_afterlife_mesh import Mesh, add, rot, save_bytes
from story_legion_people import SEATED_HIP
from venuegen import look_rotation

E = (1600.0, 0.0, 0.0)      # the crash site's stretch of road (the site itself is 6 m up it)
R = (2100.0, 0.0, 0.0)      # the highway run: the ambulance stands here and the road goes by
H = (2600.0, 0.0, 0.0)      # the hospital corridor: the drummer's gurney stands here
W = (3100.0, 0.0, 0.0)      # the hospital ward: the ground under the middle of its floor

SKY_HOUR = 12.0             # the hour of the sky out of the ward's window (VenueShow::UpdateShotSky)
STEP = 1.6                  # metres of road a frame on the run (48 m/s, as the chase)
RUN = 0.15                  # metres of corridor a frame (4.5 m/s: a run with a gurney)
AMB_X = 2.7                 # the ambulance's lane on the run
FLOOR = 0.72                # an ambulance's floor above the road
ROOM_Y = 7.2                # the ward's floor above the ground (the third storey)

LOOKS = {'drummer': ('Son_01', '01_A'), 'guitar': ('Daughter_01', '02_C'), 'bass': ('Mother_01', '03_A'), 'vocals': ('SchoolBoy_01', '04_C')}
MEDIC = ('Son_01', '02_A')
COP = ('ShopKeeper_01', '04_B')
NURSE = ('Mother_02', '01_C')

# Poses (story_legion_people.Pose: seated; torso / head Euler; arms (shoulder Euler, elbow bend)).
PUSH = P.Pose(False, (14, 0, 0), (-4, 0, 0), ((-62, 0, 8), 25), ((-62, 0, -8), 25))
PADDLES = P.Pose(False, (30, 0, 0), (12, 0, 0), ((-52, 0, 12), 12), ((-52, 0, -12), 12))
BAGGING = P.Pose(True, (22, 0, 0), (16, 0, 0), ((-48, 0, 16), 40), ((-48, 0, -16), 40))
COP_BENCH = P.Pose(True, (20, 0, 0), (10, 22, 0), ((-34, 0, 10), 55), ((-34, 0, -10), 55))
COP_HOPES = P.Pose(True, (8, 0, 0), (-8, 26, 0), ((-34, 0, 10), 55), ((-60, 0, -10), 30))
COP_WATCH = P.Pose(False, (4, 0, 0), (10, -18, 0), ((-18, 0, 10), 20), ((-72, 0, -14), 30))
COP_RUNS = P.Pose(False, (12, 0, 0), (6, -28, 0), ((-48, 0, 10), 75), ((28, 0, -10), 70))
COP_CHAIR = P.Pose(True, (4, 0, 0), (-10, 0, 0), ((-30, 0, 8), 55), ((-30, 0, -8), 55))
IV_HELD = P.Pose(False, (10, 0, 0), (2, 22, 0), ((-150, 0, 12), 25), ((-34, 0, -10), 60))
AT_WALL = P.Pose(False, (-3, 0, 0), (4, 30, 0), ((-6, 0, 22), 10), ((-6, 0, -22), 10))


def in_bed(kind, turn):
    """Sitting up in bed, turned toward the window: turn +1 when it is on their right, -1 on
    their left. kind: 'up' (upright, hands in the lap), 'back' (lying back on the raised head of
    the bed), 'forward' (leaning forward over the knees), 'easy' (back, a hand behind the head)."""
    t = turn
    if kind == 'up':
        return P.Pose(True, (2, 16 * t, 0), (-8, 30 * t, 0), ((-30, 0, 8), 50), ((-30, 0, -8), 50))
    if kind == 'back':
        return P.Pose(True, (-24, 8 * t, 0), (12, 38 * t, 0), ((-12, 0, 10), 30), ((-12, 0, -10), 30))
    if kind == 'forward':
        return P.Pose(True, (15, 22 * t, 0), (-14, 34 * t, 0), ((-52, 0, 10), 35), ((-52, 0, -10), 35))
    behind = ((-150, 0, 24), 140)
    rest = ((-12, 0, -10 * t), 30)
    return P.Pose(True, (-22, 8 * t, 0), (10, 40 * t, 0), behind if t < 0 else rest, rest if t < 0 else behind)


def at(o, p):
    return (o[0] + p[0], o[1] + p[1], o[2] + p[2])


def place_at(s, parent, name, after, before, pivot):
    """A place: shown from flag after until flag before, cut in and out, its children in venue space."""
    return P.between(s, parent, name, after, before, 0.0, pivot)


def body_of(V, who):
    return P.figure(V, f'Body_{who}', LOOKS[who][0], LOOKS[who][1], P.STANDING, f'the {who} on the asphalt')


# ---- props ----------------------------------------------------------------------------------
def _door(m, sign, angle, window):
    """One rear door of the ambulance, hinged at its outer edge, swung open by angle; with a
    window it is a frame round the hole (the generator adds the glass)."""
    hinge = (sign * 1.2, 1.85, -2.9)
    pieces = [(0.0, 1.17, 0.75, 2.95)] if not window else [(0.0, 1.17, 0.75, 2.0), (0.0, 1.17, 2.6, 2.95), (0.0, 0.25, 2.0, 2.6), (0.95, 1.17, 2.0, 2.6)]
    for u0, u1, y0, y1 in pieces:
        c = (-sign * (u0 + u1) / 2, (y0 + y1) / 2 - 1.85, 0)
        m.box(add(hinge, rot(c, (0, sign * angle, 0))), (u1 - u0, y1 - y0, 0.06), 'white', euler=(0, sign * angle, 0))


def ambulance_shell(venue, shut):
    """An ambulance facing +z like A.ambulance, but hollow: thin walls round a floor at FLOOR,
    the back doors standing open, or shut with a window in each."""
    def build(m):
        m.box((0, 0.61, -0.6), (2.4, 0.22, 4.6), 'steel')
        m.box((0, 2.97, -0.6), (2.4, 0.06, 4.6), 'white')
        m.box((0, 1.85, 1.67), (2.4, 2.26, 0.06), 'white')
        for x in (-1.0, 1.0):
            m.box((x * 1.17, 1.85, -0.6), (0.06, 2.26, 4.6), 'white')
            m.box((x * 1.205, 1.25, -0.6), (0.02, 0.3, 4.62), 'amb_red')
            m.box((x * 1.205, 2.0, -0.6), (0.02, 0.1, 4.62), 'hivis')
            m.box((x * 0.98, 0.86, -1.9), (0.3, 0.28, 1.15), 'white')        # the wheel arch, inside
            for z in (-1.9, 2.3):
                A._wheel(m, (x * 1.1, 0.45, z), 0.45, 0.3)
            m.box((x * 0.75, 0.9, 3.17), (0.4, 0.2, 0.05), 'lamp')
            m.box((x * 0.95, 1.1, -2.94), (0.2, 0.3, 0.03), 'red_lamp')
            _door(m, x, 0 if shut else 105, shut)
        m.box((0, 1.3, 2.4), (2.3, 1.6, 1.5), 'white', taper=0.9)
        m.box((0, 1.75, 3.0), (2.0, 0.6, 0.06), 'glass', euler=(-20, 0, 0))
        m.box((0, 0.5, 0), (2.2, 0.2, 6.4), 'steel_dark')
        m.box((0, 0.55, -3.08), (2.0, 0.08, 0.34), 'steel')
        m.box((0, 3.05, 1.4), (1.6, 0.14, 0.3), 'black')
    return A.prop(venue, 'AmbulanceShut' if shut else 'AmbulanceOpen', build)


def ambulance_fittings(venue, cot):
    """What is bolted down inside ambulance_shell: the bench, the cupboards, the monitor's shelf,
    the rail along the ceiling; with cot, the cot the patient rides on."""
    def build(m):
        m.box((0.87, 0.95, -0.9), (0.54, 0.46, 3.0), 'navy')
        m.box((1.1, 1.62, -0.9), (0.08, 0.8, 3.0), 'navy')
        m.box((-0.98, 2.5, -0.6), (0.32, 0.78, 4.2), 'white')
        for z in (-2.2, -1.4, -0.6, 0.2, 1.0):
            m.box((-0.815, 2.5, z), (0.02, 0.5, 0.04), 'steel')
        m.box((-1.0, 1.0, 1.0), (0.3, 0.56, 1.2), 'white')
        m.box((-0.95, 1.75, -0.9), (0.3, 0.48, 0.62), 'steel_dark')
        m.box((0.82, 1.31, 0.25), (0.36, 0.26, 0.3), 'cone')
        m.box((0.82, 1.45, 0.25), (0.2, 0.03, 0.2), 'black')
        m.lathe((-0.95, FLOOR, -2.4), [(0.1, 0), (0.1, 0.8), (0.04, 0.9)], 'sign_green', 8)
        m.tube([(0.1, 2.84, -2.7), (0.1, 2.84, 1.5)], 0.018, 'chrome', 6)
        for z in (-2.6, -0.6, 1.4):
            m.tube([(0.1, 2.84, z), (0.1, 2.94, z)], 0.012, 'chrome', 4)
        m.box((-0.3, FLOOR + 0.2, 1.1), (0.4, 0.4, 0.4), 'navy')             # the seat at the patient's head
        if cot:
            m.box((-0.3, 1.16, -0.5), (0.6, 0.08, 2.0), 'steel')
            m.box((-0.3, 1.24, -0.5), (0.56, 0.1, 1.9), 'white')
            m.box((-0.3, 1.31, 0.27), (0.44, 0.07, 0.32), 'paper')
            for z in (-1.3, 0.3):
                m.box((-0.3, 0.93, z), (0.5, 0.4, 0.06), 'steel_dark')
    return A.prop(venue, 'AmbulanceCot' if cot else 'AmbulanceBench', build)


def gurney(venue):
    """A gurney's top, along z with the pillow at +z: the mattress's top at y 0.92, an IV pole at
    the head whose hook is at (0.33, 1.95, 0.85)."""
    def build(m):
        m.box((0, 0.80, 0), (0.6, 0.06, 2.0), 'steel')
        m.box((0, 0.87, 0), (0.56, 0.1, 1.9), 'white')
        m.box((0, 0.945, 0.74), (0.44, 0.07, 0.32), 'paper')
        for x in (-0.31, 0.31):
            m.tube([(x, 0.83, -0.5), (x, 1.0, -0.45), (x, 1.0, 0.45), (x, 0.83, 0.5)], 0.015, 'chrome', 5)
        m.tube([(0.33, 0.8, 0.85), (0.33, 1.98, 0.85)], 0.014, 'chrome', 5)
        m.tube([(0.2, 1.97, 0.85), (0.46, 1.97, 0.85)], 0.01, 'chrome', 4)
    return A.prop(venue, 'Gurney', build)


def gurney_legs(venue):
    """The gurney's undercarriage, hanging from y 0 (the deck) down to the road at -0.77: scaled
    flat along y, it folds up under the deck as the gurney goes into the ambulance."""
    def build(m):
        for z0, z1 in ((-0.85, 0.2), (0.85, -0.2)):
            for x in (-0.24, 0.24):
                m.tube([(x, 0.0, z0), (x, -0.68, z1)], 0.016, 'chrome', 5)
        for z in (-0.2, 0.2):
            m.tube([(-0.24, -0.68, z), (0.24, -0.68, z)], 0.014, 'chrome', 4)
            for x in (-0.26, 0.26):
                m.lathe((x, -0.7, z), [(0.04, -0.02), (0.07, -0.015), (0.07, 0.015), (0.04, 0.02)], 'rubber', 8, 'x')
    return A.prop(venue, 'GurneyLegs', build)


def blanket(venue):
    """A blanket over a patient's legs: 0.8 long along z, its top 0.3 up, drawn in at the top."""
    return A.prop(venue, 'Blanket', lambda m: m.box((0, 0.15, 0), (0.64, 0.3, 0.84), 'sky', taper=0.66))


def run_lane(venue, half):
    """The paint on a stretch of four-lane road from -half to half along z: edge lines, the double
    yellow, a dash and a delineator post every 16 m."""
    def build(m):
        for x in (-10.63, 10.63):
            m.box((x, 0.006, 0), (0.15, 0.012, 2 * half), 'paper')
        for x in (-0.14, 0.14):
            m.box((x, 0.006, 0), (0.12, 0.012, 2 * half), 'brass')
        for k in range(int(-half // 16), int(half // 16)):
            for x in (-5.4, 5.4):
                m.box((x, 0.006, k * 16 + 2), (0.14, 0.012, 4.0), 'paper')
            for x in (-11.6, 11.6):
                m.box((x, 0.5, k * 16 + 8), (0.06, 1.0, 0.03), 'white')
                m.box((x, 0.9, k * 16 + 8), (0.07, 0.12, 0.035), 'cone')
    return A.prop(venue, 'RunLane', build)


def corridor(venue, kind):
    """Six metres of hospital corridor from z 0 to 6, 3.4 wide and 2.9 high. A: a ward door each
    side. B: double doors on the left, a row of chairs on the right. The light panels' places are
    LIGHTS (the generator puts the glowing ones there)."""
    def build(m):
        m.box((0, -0.05, 3), (3.5, 0.1, 6), 'marble')
        for z in (0.0, 1.5, 3.0, 4.5):
            m.box((0, 0.002, z), (3.4, 0.004, 0.03), 'marble_shade')
        m.box((-1.05, 0.003, 3), (0.1, 0.004, 6), 'amb_red')
        m.box((-0.9, 0.003, 3), (0.1, 0.004, 6), 'sky')
        m.box((0, 2.95, 3), (3.5, 0.1, 6), 'white')
        for z in (0.0, 3.0):
            m.box((0, 2.895, z), (3.4, 0.02, 0.05), 'steel')
        for side in (-1, 1):
            m.box((side * 1.75, 1.45, 3), (0.1, 2.9, 6), 'paper')
            m.box((side * 1.695, 1.0, 3), (0.02, 0.22, 6), 'sky')
            m.box((side * 1.695, 0.08, 3), (0.02, 0.16, 6), 'marble_shade')
            m.tube([(side * 1.62, 0.92, 0.0), (side * 1.62, 0.92, 6.0)], 0.02, 'chrome', 5)
        if kind == 'A':
            for side, z, ink in ((-1, 1.8, 'sign_green'), (1, 4.6, 'wood')):
                m.box((side * 1.69, 1.05, z), (0.04, 2.1, 1.05), ink)
                m.box((side * 1.685, 2.14, z), (0.06, 0.08, 1.2), 'steel')
                for dz in (-0.57, 0.57):
                    m.box((side * 1.685, 1.05, z + dz), (0.06, 2.1, 0.07), 'steel')
                m.box((side * 1.66, 1.45, z + 0.3), (0.02, 0.5, 0.3), 'glass')
                m.box((side * 1.68, 1.7, z + 0.9), (0.02, 0.2, 0.3), 'navy')        # a door plate
        else:
            m.box((-1.69, 1.1, 3.0), (0.04, 2.2, 2.2), 'steel')
            m.box((-1.665, 1.1, 3.0), (0.02, 2.2, 0.03), 'steel_dark')
            for dz in (-0.55, 0.55):
                m.box((-1.66, 1.5, 3.0 + dz), (0.02, 0.6, 0.5), 'glass')
            m.box((-1.685, 2.25, 3.0), (0.06, 0.1, 2.4), 'amb_red')
            for k in range(4):
                z = 1.0 + k * 0.6
                m.box((1.4, 0.45, z), (0.45, 0.05, 0.5), 'sky')
                m.box((1.62, 0.75, z), (0.05, 0.5, 0.5), 'sky')
                for dz in (-0.2, 0.2):
                    m.tube([(1.25, 0.0, z + dz), (1.25, 0.44, z + dz)], 0.015, 'chrome', 4)
            m.box((1.67, 1.5, 4.9), (0.04, 0.6, 0.45), 'paper')                     # a notice board
            m.box((1.66, 1.3, 5.6), (0.08, 0.25, 0.12), 'white')                    # hand sanitiser
    return A.prop(venue, 'Corridor' + kind, build)


LIGHTS = (1.5, 4.5)         # where a corridor segment's ceiling panels are, along z


def panel(venue):
    return A.prop(venue, 'CeilingPanel', lambda m: m.box((0, 0, 0), (1.2, 0.03, 0.6), 'white'))


def strip_sign(venue, which, band):
    """The lettering of one of the sign textures (its middle band, band of its height) on a quad
    facing +z, 2 wide and 2 * band high."""
    return A.prop(venue, which + 'Strip', lambda m: m.face([(-1, -band, 0), (1, -band, 0), (1, band, 0), (-1, band, 0)],
                                                           uvs=[(1, 0.5 - band / 2), (0, 0.5 - band / 2), (0, 0.5 + band / 2), (1, 0.5 + band / 2)]), which)


WARD = (3.4, 3.4, -3.6, 5.7)      # the ward: half its width, its height, the window wall's z and the back wall's
WARD_ROWS = (-2.45, -0.45)        # its two rows of beds (z): hard by the window, and the row behind
BED_TOP = 0.62                    # a ward bed's mattress above the floor


def ward(venue):
    """The ward: a room 6.8 m wide whose whole far wall (-z) is window from a low sill to the
    ceiling; four beds go along the side walls (ward_bed). Closed all round, to keep heaven's sun out."""
    half, high, z0, z1 = WARD

    def build(m):
        mid, deep = (z0 + z1) / 2, z1 - z0
        m.box((0, -0.05, mid), (2 * half + 0.2, 0.1, deep + 0.2), 'marble_shade')
        m.box((0, high + 0.05, mid), (2 * half + 0.2, 0.1, deep + 0.2), 'white')
        m.box((0, high / 2, z1 + 0.05), (2 * half + 0.2, high, 0.1), 'paper')
        for x in (-1, 1):
            m.box((x * (half + 0.05), high / 2, mid), (0.1, high, deep + 0.2), 'paper')
            m.box((x * (half - 0.005), 1.0, mid), (0.02, 0.22, deep), 'sky')
        m.box((0, 0.525, z0 - 0.05), (2 * half + 0.2, 1.05, 0.2), 'paper')
        m.box((0, high - 0.1, z0 - 0.05), (2 * half + 0.2, 0.2, 0.2), 'paper')
        m.box((0, 1.07, z0 + 0.1), (2 * half, 0.04, 0.4), 'white')
        # Three panes (no post up the middle: that is where the sun stands).
        for k in range(4):
            m.box((-half + k * 2 * half / 3, high / 2 + 0.42, z0 - 0.05), (0.1, high - 1.25, 0.12), 'white')
        m.box((1.6, 1.05, z1 - 0.02), (1.0, 2.1, 0.05), 'wood')
    return A.prop(venue, 'Ward', build)


def ward_bed(venue, raised):
    """A hospital bed along x, its head at -x, the mattress's top at BED_TOP; the head end raised
    for sitting up (raised: far enough to lie back on)."""
    def build(m):
        lean = 34 if raised else 14
        m.box((0, 0.24, 0), (2.1, 0.48, 0.96), 'steel')
        m.box((0, 0.55, 0), (2.06, 0.14, 0.92), 'white')
        m.box((-0.78, 0.93, 0), (0.1, 0.8, 0.9), 'white', euler=(0, 0, lean))
        m.box((-0.7, 1.02, 0), (0.1, 0.42, 0.62), 'paper', euler=(0, 0, lean))
        m.box((-1.08, 0.62, 0), (0.06, 1.24, 1.0), 'steel_dark')
        m.box((1.08, 0.36, 0), (0.06, 0.72, 1.0), 'steel_dark')
        for z in (-0.5, 0.5):
            m.tube([(-0.2, 0.6, z), (-0.2, 0.86, z), (0.7, 0.86, z), (0.7, 0.6, z)], 0.016, 'chrome', 5)
        m.box((0.4, 0.72, 0), (1.36, 0.22, 0.95), 'sky', taper=0.86)                 # the blanket over the legs
        m.box((-0.3, 0.74, 0), (0.12, 0.2, 0.95), 'white', taper=0.9)                # the sheet folded back over it
    return A.prop(venue, 'WardBedRaised' if raised else 'WardBed', build)


def ward_fittings(venue):
    """A bedside cabinet and a chair, each on the floor at the origin (the chair faces +z)."""
    def cabinet(m):
        m.box((0, 0.36, 0), (0.5, 0.72, 0.45), 'wood')
        m.box((0, 0.5, 0.23), (0.42, 0.02, 0.02), 'chrome')
        m.box((0, 0.73, 0), (0.54, 0.03, 0.49), 'marble')

    def chair(m):
        m.box((0, 0.45, 0), (0.5, 0.06, 0.5), 'navy')
        m.box((0, 0.8, -0.24), (0.5, 0.6, 0.05), 'navy')
        for x in (-0.22, 0.22):
            for z in (-0.22, 0.22):
                m.tube([(x, 0, z), (x, 0.44, z)], 0.016, 'chrome', 4)
    return A.prop(venue, 'WardCabinet', cabinet), A.prop(venue, 'WardChair', chair)


# ---- moving parts ---------------------------------------------------------------------------
def swing(venue, k):
    """One of four pendulum loops for what hangs from a hook: a swing fore and aft and another,
    out of step, from side to side."""
    frames, ax, az = ((36, 9.0, 6.0), (48, 7.0, 10.0), (60, 12.0, 5.0), (72, 6.0, 9.0))[k % 4]
    keys = []
    for i in range(13):
        t = 2 * math.pi * i / 12
        keys.append((frames * i // 12, (ax * math.sin(t + 0.7 * k), 0, az * math.sin(t + 1.3 + 0.4 * k))))
    return P.clip(venue, f'Swing{k % 4}', frames, [P.track('Rotation', keys)])


def dangle(s, parent, V, name, pivot, length, kind, k):
    """Something hanging from pivot on length of cord, swinging (see swing)."""
    body = P.looping(s, parent, name, swing(V, k), pivot, speed=0.85 + 0.11 * (k % 5))
    dark, steel = (0.05, 0.05, 0.06), (0.6, 0.62, 0.66)
    s.box('Cord', body, (0, -length / 2, 0), (0.012, length, 0.012), dark, shadows=False)
    low = (0, -length, 0)
    if kind == 'iv':
        M_see(s.box('Bag', body, at(low, (0, -0.1, 0)), (0.12, 0.2, 0.05), (0.8, 0.9, 1.0), emissive=(0.5, 0.65, 0.8), emissive_intensity=0.6, shadows=False), 0.55)
        s.box('Line', body, at(low, (0, -0.45, 0)), (0.008, 0.5, 0.008), (0.8, 0.85, 0.9), shadows=False)
    elif kind == 'strap':
        for dx in (-0.045, 0.045):
            s.box('Strap', body, at(low, (dx, -0.1, 0)), (0.02, 0.2, 0.03), (0.85, 0.9, 0.1), shadows=False)
        s.box('Strap', body, at(low, (0, -0.2, 0)), (0.11, 0.02, 0.03), (0.85, 0.9, 0.1), shadows=False)
    elif kind == 'mask':
        M_see(s.box('Mask', body, at(low, (0, -0.05, 0)), (0.12, 0.1, 0.1), (0.7, 0.95, 0.85), shape='Sphere', shadows=False), 0.5)
    elif kind == 'steth':
        for dx in (-0.04, 0.04):
            s.box('Tube', body, at(low, (dx, -0.16, 0)), (0.012, 0.32, 0.012), dark, shadows=False)
        s.box('Bell', body, at(low, (0, -0.34, 0)), (0.06, 0.02, 0.06), steel, shape='Cylinder', metallic=0.9, rough=0.3, shadows=False)
    elif kind == 'shears':
        s.box('Shears', body, at(low, (0, -0.09, 0)), (0.04, 0.18, 0.012), (0.9, 0.35, 0.05), shadows=False)
    elif kind == 'clip':
        s.box('Clipboard', body, at(low, (0, -0.16, 0)), (0.22, 0.31, 0.012), (0.42, 0.26, 0.13), shadows=False)
        s.box('Sheet', body, at(low, (0, -0.17, 0.008)), (0.19, 0.26, 0.004), (0.92, 0.9, 0.84), shadows=False)
    elif kind == 'tree':
        s.box('Air freshener', body, at(low, (0, -0.06, 0)), (0.07, 0.12, 0.006), (0.1, 0.5, 0.18), shadows=False)
    elif kind == 'buckle':
        s.box('Belt', body, at(low, (0, 0.0, 0)), (0.045, length * 2, 0.008), (0.08, 0.08, 0.1), shadows=False)
        s.box('Buckle', body, at(low, (0, -0.03, 0)), (0.06, 0.07, 0.02), steel, metallic=0.9, rough=0.3, shadows=False)
    elif kind == 'cuff':
        s.box('Cuff', body, at(low, (0, -0.08, 0)), (0.14, 0.14, 0.03), (0.1, 0.12, 0.3), shadows=False)
        s.box('Bulb', body, at(low, (0.06, -0.22, 0)), (0.05, 0.07, 0.05), dark, shape='Sphere', shadows=False)
    elif kind == 'tags':
        for dx in (-0.012, 0.012):
            s.box('Tag', body, at(low, (dx, -0.02, 0)), (0.025, 0.045, 0.003), steel, metallic=0.9, rough=0.3, shadows=False)
    return body


M_see = None        # make_story_afterlife.see_through, set by build()


def monitor(s, parent, name, where, yaw, beats=None, every=1.0, scale=1.0):
    """A heart monitor's screen at where, facing +z turned by yaw: a flat green line, and (beats:
    None always, else from that story flag on) a spike that jumps on every beat of the song
    (VenueBeat, Sharp: it stands behind the glass and comes through it on the beat, for about a
    third of it)."""
    green = (0.2, 1.0, 0.4)
    m = s.entity(name, parent, where, (0, yaw, 0), (scale, scale, scale))
    s.box('Screen', m, (0, 0, 0), (0.4, 0.3, 0.012), (0.01, 0.03, 0.02), emissive=(0.02, 0.12, 0.05), emissive_intensity=1.0, shadows=False)
    s.box('Line', m, (0, -0.05, 0.008), (0.34, 0.012, 0.004), green, emissive=green, emissive_intensity=7.0, shadows=False)
    live = P.between(s, m, 'Beating', beats, None, 0.0) if beats else m
    blip = s.entity('Beat', live, (0, -0.05, -0.004))
    blip.add({'Type': 'VenueBeat', 'Offset': [0.0, 0.0, 0.05], 'Every': every, 'Phase': 0.0, 'Sway': False, 'Sharp': True})
    for dx, y0, h in ((-0.05, -0.02, 0.03), (-0.025, 0.0, 0.17), (0.0, -0.045, 0.06), (0.03, 0.0, 0.04)):
        s.box('Spike', blip, (dx, y0 + h / 2, 0), (0.022, h, 0.004), green, emissive=green, emissive_intensity=9.0, shadows=False)
    return m


def beacon(s, parent, V, where, red=0.0, blue=0.0, reach=20.0, speed=1.0):
    """A lightbar at where: red and blue lamps, their glare turning, and (red / blue above 0) two
    spot lights sweeping round at those levels. make_story_afterlife.lightbar's, with the levels
    to choose: a dozen of the crash site's would burn the run out."""
    spin = P.clip(V, 'LightbarSpin', 24, [P.track('Rotation', [(0, (0, 0, 0)), (12, (0, 180, 0)), (24, (0, 359.9, 0))])])
    s.box('Lamp red', parent, at(where, (-0.4, 0.06, 0)), (0.45, 0.14, 0.24), (1, 0.05, 0.05), emissive=(1, 0.05, 0.05), emissive_intensity=8.0, shadows=False)
    s.box('Lamp blue', parent, at(where, (0.4, 0.06, 0)), (0.45, 0.14, 0.24), (0.1, 0.2, 1), emissive=(0.1, 0.2, 1), emissive_intensity=8.0, shadows=False)
    turning = P.looping(s, parent, 'Sweep', spin, at(where, (0, 0.2, 0)), speed=speed)
    if red > 0:
        s.light('Sweep red', turning, (0, 0, 0), 'Spot', (1.0, 0.05, 0.05), red, reach, rot=(10, 0, 0), inner=14, outer=32)
        s.light('Sweep blue', turning, (0, 0, 0), 'Spot', (0.1, 0.25, 1.0), blue, reach, rot=(10, 180, 0), inner=14, outer=32)
    for yaw, c in ((0, (1.0, 0.06, 0.05)), (180, (0.12, 0.25, 1.0))):
        A.glow_card(s, turning, V, 'Glare', rot((0, 0.05, 0.3), (0, yaw, 0)), 0.5, c, 1.2, (0, yaw, 0))


def runner(s, parent, V, name, model, pos, yaw, k):
    """A figure running on the spot (the corridor goes by): a bob and a roll from foot to foot."""
    clip = P.clip(V, 'RunBob', 10, [P.track('Position', [(0, (0, 0, 0)), (3, (0, 0.06, 0)), (5, (0, 0, 0)), (8, (0, 0.06, 0)), (10, (0, 0, 0))], 'SmoothStep'),
                                     P.track('Rotation', [(0, (0, 0, -2.5)), (5, (0, 0, 2.5)), (10, (0, 0, -2.5))], 'SmoothStep')])
    return P.place(s, P.looping(s, parent, name, clip, pos, speed=0.9 + 0.07 * (k % 4), rot=(0, yaw, 0)), name, model, (0, 0, 0), 0)


def patient(s, parent, V, who, deck=0.92, head=1):
    """A band member on their back on a gurney or cot under parent (its mattress's top at deck,
    its middle at the origin), the head toward +z or (head -1) -z, a blanket over the legs."""
    P.lie(s, parent, who.capitalize(), body_of(V, who), (0, deck, -0.85 * head), 180 if head > 0 else 0)
    A.model(s, parent, 'Blanket', blanket(V), (0, deck, -0.5 * head), material=A.mat(V, 'Palette', (1.25, 1.2, 1.1), rough=1.0))
    s.box('Strap', parent, (0, deck + 0.305, -0.5 * head), (0.46, 0.012, 0.06), (0.08, 0.08, 0.1), shadows=False)


# ---- the crash site: cpr, loading -----------------------------------------------------------
def crash(s, root, marks, V, M):
    site = (E[0], 0.0, E[2] + 6)
    # Slow motion: the fire, the lights, the compressions, the gurney going in.
    slow = P.slow_motion(s, root, 'Slow motion', 'ambulance_run', 0.25)
    earth = place_at(s, slow, 'The crash site', None, 'ambulance_run', E)
    M.road(s, earth, V, E[0] - 14, E[0] + 14, E[2] - 70, E[2] + 70)
    M.roadside(s, earth, V, E, 70.0, 14.0, torn_z=E[2] + 10.0)
    A.model(s, earth, 'Mile marker', A.sign_face(V, 'MileMarker'), (E[0] + 15.6, 1.6, E[2] + 20), (0, 180, 0), (0.45, 0.6, 1), A.mat(V, 'MileMarker', glow=(1, 1, 1), power=0.5), shadows=False)
    s.box('Mile marker post', earth, (E[0] + 15.6, 0.5, E[2] + 20.04), (0.08, 1.0, 0.05), M.STEEL)
    M.cruiser(s, earth, V, (E[0] - 7.5, 0, E[2] - 9), 24, door_open=True)
    # The cop kneels at the drummer's chest (the body lies at yaw 200 from its feet at (-1, 1)), facing across it.
    cop_at = (-1.26, 110, 2.48)
    hand = M.crash_site(s, earth, V, site, {'lifted': 'loading', 'cop': None}, cop=cop_at, ems=True, wreck_at=(4.0, 0, -2.0), ambulance=False)
    cop_eye = (E[0] + cop_at[0], 1.0, E[2] + 6 + cop_at[2])
    for i, (x, z, yaw) in enumerate(((-9.5, -20, 20), (-3.0, -24, -30), (4.5, -22, 60), (-12.0, 12, 80))):
        A.flare(s, earth, V, f'Flare {i}', (E[0] + x, 0, E[2] + z), yaw)
    M.ground_fog(s, earth, V, (E[0], 0.5, E[2]), (46, 1.0, 60), 12)
    s.light('Earth moon', earth, (E[0], 30, E[2] - 10), 'Spot', (0.4, 0.48, 0.75), 9000.0, 70, rot=(80, 0, 0), inner=35, outer=65)
    # A second crew's ambulance down the road, for the others.
    far = s.entity('Second ambulance', earth, at(site, (-9.5, 0, -5.0)), (0, 35, 0))
    A.model(s, far, 'Body', A.ambulance(V))
    M.lightbar(s, far, V, (0, 3.1, 2.2))

    # The drummer's ambulance, backed up below their feet (the road beyond their head is strewn
    # with the kit), its doors open; everything to do with
    # the loading is in its space (it faces +z: the doors are at z -2.9).
    amb_at, amb_yaw = at(site, (2.4, 0, -9.6)), 188.0
    amb = s.entity('Ambulance', earth, amb_at, (0, amb_yaw, 0))

    def w(p):
        return at(amb_at, rot(p, (0, amb_yaw, 0)))
    A.model(s, amb, 'Body', ambulance_shell(V, False))
    A.model(s, amb, 'Fittings', ambulance_fittings(V, False))
    M.lightbar(s, amb, V, (0, 3.1, 1.4))
    s.box('Ceiling light', amb, (0, 2.925, -1.0), (0.5, 0.03, 1.6), (1, 1, 1), emissive=(0.95, 0.97, 1.0), emissive_intensity=2.0, shadows=False)
    s.light('Ambulance inside', amb, (0, 2.5, -1.0), 'Point', (0.9, 0.95, 1.0), 9.0, 6)
    s.light('Ambulance work light', amb, (0, 2.9, -3.1), 'Spot', (1.0, 0.97, 0.9), 240.0, 16, rot=(62, 180, 0), inner=34, outer=60)
    for k, (pivot, length, kind) in enumerate((((0.1, 2.82, -2.3), 0.3, 'strap'), ((0.1, 2.82, -1.2), 0.3, 'strap'), ((-0.5, 2.9, -0.4), 0.35, 'iv'))):
        dangle(s, amb, V, f'Hanging {k}', pivot, length, kind, k)
    start = (0, 0, -4.9)
    waiting = P.between(s, amb, 'Gurney waiting', None, 'loading', 0.0, start)
    stood = s.entity('Gurney', waiting, (-0.9, 0, -5.3), (0, -22, 0))
    A.model(s, stood, 'Top', gurney(V))
    A.model(s, stood, 'Legs', gurney_legs(V), (0, 0.78, 0))
    s.box('Blanket, folded', stood, (0, 0.96, -0.3), (0.5, 0.08, 0.5), (0.6, 0.72, 0.84), rough=1.0)
    # loading: the gurney runs in head first (2.6 m: its foot still out of the doors at the end),
    # its legs folding up under it as they reach the bumper.
    loading = P.between(s, amb, 'Loading', 'loading', None, 0.0, start)
    go_in = P.clip(V, 'GurneyIn', 66, [P.track('Position', [(0, (0, 0, 0)), (66, (0, 0, 2.6))], 'SmoothStep')])
    fold = P.clip(V, 'GurneyFold', 66, [P.track('Scale', [(0, (1, 1, 1)), (14, (1, 1, 1)), (34, (1, 0.05, 1)), (66, (1, 0.05, 1))], 'SmoothStep')])
    moving = P.play(s, loading, 'Gurney goes in', 'loading', go_in, start)
    A.model(s, moving, 'Top', gurney(V))
    A.model(s, P.play(s, moving, 'Legs fold', 'loading', fold, (0, 0.78, 0)), 'Legs', gurney_legs(V))
    patient(s, moving, V, 'drummer')
    dangle(s, moving, V, 'IV bag', (0.33, 1.95, 0.85), 0.1, 'iv', 1)
    P.place(s, moving, 'Medic at the foot', P.figure(V, 'Medic_push', MEDIC[0], MEDIC[1], PUSH, 'an EMS worker pushing a gurney'), (0, 0, -1.6), 0)
    P.place(s, loading, 'Medic inside', P.figure(V, 'Medic', MEDIC[0], MEDIC[1], P.KNEEL_CPR, 'an EMS worker'), (0.55, FLOOR - 0.08, -1.2), 200)
    P.place(s, loading, 'Cop', P.figure(V, 'Cop_watches', COP[0], COP[1], COP_WATCH, 'the cop, a hand out as they take the drummer'), (-1.6, 0, -4.2), 75)

    cop_ground = (cop_eye[0], 0, cop_eye[2])
    cop_head = at(cop_ground, M.P_rot((0, 0.95, 0.45), cop_at[1]))      # he leans over the drummer as he pumps
    cop_hands = at(cop_ground, M.P_rot((0, 0.3, 0.75), cop_at[1]))
    M.shot(s, marks, 'cpr', (cop_hands[0] + 0.9, 0.3, cop_hands[2] - 1.5), cop_hands, 34, 8, hand=True, focus=True,
           end=((cop_eye[0] + 1.5, 0.75, cop_eye[2] - 1.0), (cop_eye[0], 1.0, cop_eye[2]), 30))
    # From the road beside the gurney as it starts to move, up to the open doors as it goes in.
    M.shot(s, marks, 'loading', w((2.7, 0.9, -5.9)), w((0, 1.1, -4.0)), 42, 8.2, hand=True, focus=True,
           end=(w((1.7, 1.55, -5.9)), w((-0.05, 1.25, -1.9)), 36))
    return hand, cop_head


# ---- the highway run and the inside of the ambulance: ambulance_run, defib, shock -----------
def inside(s, amb, V):
    """Who and what is in the back of the ambulance on the run (amb: its space, facing +z)."""
    for z in (-1.7, 0.3):
        s.box('Ceiling light', amb, (0, 2.925, z), (0.5, 0.03, 1.0), (1, 1, 1), emissive=(0.9, 0.95, 1.0), emissive_intensity=1.0, shadows=False)
    s.light('Ambulance inside', amb, (0, 2.5, -0.7), 'Point', (0.85, 0.92, 1.0), 4.0, 5.5)
    for x in (-0.6, 0.6):
        M_see(s.box('Rear glass', amb, (x, 2.3, -2.9), (0.7, 0.6, 0.02), (0.5, 0.6, 0.7), rough=0.05, shadows=False), 0.12)
    # The drummer on the cot, head to the front; the shock lifts them off it.
    chest = (-0.3, 1.29, -0.3)
    jolt = P.clip(V, 'ShockBody', 16, [P.track('Position', [(0, (0, 0, 0)), (2, (0, 0.17, 0)), (5, (0, 0.02, 0)), (8, (0, 0.05, 0)), (16, (0, 0, 0))], 'SmoothStep'),
                                       P.track('Rotation', [(0, (0, 0, 0)), (2, (-8, 0, 0)), (6, (2, 0, 0)), (16, (0, 0, 0))], 'SmoothStep')])
    lifted = P.play(s, amb, 'The shock', 'shock', jolt, chest)
    lying = s.entity('On the cot', lifted, (0, -1.29, -0.2))
    patient(s, lying, V, 'drummer', 1.29)
    for dx, dz in ((0.1, 0.42), (-0.1, 0.2)):
        s.box('Paddle', lifted, (dx, 0.33, dz), (0.1, 0.05, 0.13), (0.9, 0.35, 0.05))
        s.box('Paddle grip', lifted, (dx, 0.39, dz), (0.03, 0.08, 0.1), (0.05, 0.05, 0.06))
    recoil = P.clip(V, 'ShockRecoil', 24, [P.track('Rotation', [(0, (0, 0, 0)), (3, (-9, 0, 0)), (24, (0, 0, 0))], 'SmoothStep')])
    P.place(s, P.play(s, amb, 'Medic recoils', 'shock', recoil, (0.42, FLOOR, 0.0), (0, 270, 0)), 'Medic with the paddles',
            P.figure(V, 'Medic_paddles', MEDIC[0], MEDIC[1], PADDLES, 'an EMS worker with the paddles down'), (0, 0, 0), 0)
    P.place(s, amb, 'Medic at the head', P.figure(V, 'Medic_bagging', MEDIC[0], MEDIC[1], BAGGING, 'an EMS worker breathing for the drummer'), (-0.3, FLOOR, 1.12), 180)
    seat = (0.84, FLOOR, -1.45)
    P.place(s, P.between(s, amb, 'Cop waits', None, 'shock', 0.0, seat), 'Cop', P.figure(V, 'Cop_bench', COP[0], COP[1], COP_BENCH, 'the cop on the bench, watching'), seat, 270)
    P.place(s, P.between(s, amb, 'Cop hopes', 'shock', None, 0.0, seat), 'Cop', P.figure(V, 'Cop_hopes', COP[0], COP[1], COP_HOPES, 'the cop, looking up at the monitor'), seat, 270)
    # The flash: a light and a glare that are far overhead except for the three frames of the shock.
    flash = P.clip(V, 'ShockFlash', 6, [P.track('Position', [(0, (0, 0, 0)), (1, (0, -60, 0)), (4, (0, -60, 0)), (5, (0, 0, 0)), (6, (0, 0, 0))])])
    lit = P.play(s, amb, 'Flash', 'shock', flash, at(chest, (0, 60.6, 0)))
    s.light('Shock', lit, (0, 0, 0), 'Point', (0.8, 0.9, 1.0), 140.0, 6)
    A.glow_card(s, lit, V, 'Shock glare', (0, -0.3, 0), 0.9, (0.8, 0.9, 1.0), 5.0, (90, 0, 0))
    # The monitor: a flat line until the shock; after it a spike on every beat of the song.
    monitor(s, amb, 'Monitor', (-0.795, 1.75, -0.9), 90, 'shock', scale=1.35)
    # Everything on a hook, a strap or a lanyard.
    hung = (((-0.45, 2.9, -0.9), 0.3, 'iv'), ((-0.15, 2.9, -0.1), 0.38, 'iv'), ((-0.5, 2.9, 0.55), 0.26, 'iv'), ((0.1, 2.82, -2.3), 0.3, 'strap'),
            ((0.1, 2.82, -1.5), 0.3, 'strap'), ((0.1, 2.82, -0.7), 0.3, 'strap'), ((0.1, 2.82, 0.2), 0.3, 'strap'), ((0.1, 2.82, 1.0), 0.3, 'strap'),
            ((-0.78, 2.1, -1.9), 0.3, 'mask'), ((-0.78, 2.1, 0.45), 0.22, 'steth'), ((-0.78, 2.1, 0.9), 0.3, 'cuff'), ((0.62, 2.9, -1.9), 0.5, 'shears'),
            ((0.0, 2.6, 1.62), 0.12, 'clip'), ((0.55, 2.7, 1.62), 0.2, 'tree'), ((1.04, 2.0, -2.2), 0.28, 'buckle'), ((1.04, 2.0, -1.0), 0.28, 'buckle'),
            ((1.04, 2.0, 0.1), 0.28, 'buckle'), ((0.75, 2.9, -2.2), 0.62, 'tags'), ((-0.2, 2.9, -2.0), 0.45, 'iv'), ((0.45, 2.9, -0.4), 0.2, 'mask'))
    for k, (pivot, length, kind) in enumerate(hung):
        dangle(s, amb, V, f'Hanging {k}: {kind}', pivot, length, kind, k)


def run(s, root, marks, V, M):
    g = place_at(s, root, 'The highway run', 'ambulance_run', 'gurney', R)
    M.night_sky(s, g, V, R)
    s.slab('Ground', g, R[0] - 170, R[0] + 170, -1.2, -0.3, R[2] - 170, R[2] + 170, (0.02, 0.03, 0.02), rough=1.0, shadows=False)
    s.slab('Road bed', g, R[0] - 15, R[0] + 15, -0.3, -0.03, R[2] - 170, R[2] + 170, M.GRAVEL, shadows=False)
    rng = random.Random(77)
    for i in range(34):
        x, y = rng.uniform(-150, 150), rng.uniform(0.5, 12)
        c = rng.choice(((1.0, 0.8, 0.5), (1.0, 0.9, 0.75), (0.7, 0.85, 1.0), (1.0, 0.4, 0.3)))
        s.box('City light', g, (R[0] + x, y, R[2] + 150 + rng.uniform(0, 3)), (0.9, 0.9, 0.2), c, emissive=c, emissive_intensity=6.0, shadows=False)
    A.glow_card(s, g, V, 'Moon', (R[0] - 60, 70, R[2] + 120), 9.0, (0.8, 0.85, 1.0), 2.2, look_rotation((R[0] - 60, 70, R[2] + 120), R))
    s.light('Run moon', g, (R[0], 30, R[2] - 4), 'Spot', (0.4, 0.48, 0.75), 9000.0, 70, rot=(80, 0, 0), inner=35, outer=65)

    def scroll(name, metres):
        frames = int(round(metres / STEP))
        return P.looping(s, g, name, P.clip(V, 'Run' + name, frames, [P.track('Position', [(0, (0, 0, 0)), (frames, (0, 0, -metres))])]), R)

    lane = scroll('Dashes', 16.0)
    M.textured(s.slab('Asphalt', lane, -11, 11, -0.2, 0.0, -208, 208, (1, 1, 1), rough=0.9), V, 'Asphalt', (5.5, 104))
    A.model(s, lane, 'Paint', run_lane(V, 208.0), shadows=False)
    poles = scroll('Poles', 48.0)
    for k in range(-4, 5):
        z = k * 48 + 20
        for side in (-1, 1):
            x = side * 13
            s.box('Pole', poles, (x, 5, z), (0.25, 10, 0.25), M.STEEL, shadows=False, shape='Cylinder')
            s.box('Arm', poles, (x - side * 1.5, 9.9, z), (3.0, 0.15, 0.2), M.STEEL, shadows=False)
            s.box('Lamp', poles, (x - side * 2.8, 9.75, z), (0.6, 0.12, 0.3), (1, 0.85, 0.55), emissive=(1, 0.8, 0.5), emissive_intensity=9.0, shadows=False)
            A.glow_card(s, poles, V, 'Lamp glare', (x - side * 2.8, 9.6, z), 1.6, (1.0, 0.75, 0.4), 2.5, (90, 0, 0))
            if k in (0, 1):
                s.light('Pole light', poles, (x - side * 2.8, 9.5, z), 'Spot', (1.0, 0.78, 0.5), 320.0, 28, rot=(90, 0, 0), inner=32, outer=58)
    trees = scroll('Trees', 96.0)
    A.model(s, trees, 'Treeline', A.treeline(V, 'TreesLoop', -288, 288, 19, 80, 126, 5, period=96.0), shadows=False)
    rail = A.guardrail(V, 96.0)
    for k in range(-3, 3):
        A.model(s, trees, 'Guardrail', rail, (15.4, 0, k * 96), shadows=False)
        A.model(s, trees, 'Guardrail', rail, (-15.4, 0, k * 96 + 96), (0, 180, 0), shadows=False)
    # Traffic pulled over to let them through.
    aside = scroll('Aside', 192.0)
    for k in (-1, 0, 1):
        for z, ink, x in ((30, 'white', 12.7), (118, 'cab_red', 12.9), (160, 'steel', -12.8)):
            car = s.entity('Pulled over', aside, (x, 0, k * 192 + z), (0, 0 if x > 0 else 180, 0))
            A.model(s, car, 'Body', A.car(V, ink), shadows=False)
            for dx in (-0.65, 0.65):
                s.box('Hazard', car, (dx, 0.72, -2.24), (0.3, 0.1, 0.04), (1, 0.5, 0.05), emissive=(1, 0.5, 0.05), emissive_intensity=5.0, shadows=False)
    A.particles(s, g, 'Road grit', at(R, (0, 1.8, 34)), (-90, 0, 0), Shape='Box', BoxSize=[30, 4, 6], Lifetime=[0.9, 1.5], Speed=[44, 52], Size=[0.02, 0.06],
                StartColor=[0.9, 0.8, 0.65], StartColor2=[0.6, 0.6, 0.65], EndColor=[0.5, 0.5, 0.5], StartAlpha=0.6, EndAlpha=0.0, Intensity=1.8, Gravity=0.0, Drag=0.0,
                NoiseStrength=0.3, Blend='Additive', EmissionRate=90, MaxParticles=180, Alignment='Stretched', StretchFactor=0.07, FadeIn=0.1)

    # The ambulance: it stands (rocking on its springs) and the road goes by.
    rock = P.clip(V, 'AmbulanceRock', 96, [P.track('Position', [(0, (0, 0, 0)), (24, (0.1, 0.02, 0)), (48, (0, 0, 0)), (72, (-0.1, 0.02, 0)), (96, (0, 0, 0))], 'SmoothStep'),
                                           P.track('Rotation', [(0, (0, 0, 0)), (24, (0.3, 0, -0.9)), (48, (-0.3, 0, 0)), (72, (0.3, 0, 0.9)), (96, (0, 0, 0))], 'SmoothStep')])
    amb_at = at(R, (AMB_X, 0, 0))
    amb = P.looping(s, g, 'Ambulance', rock, amb_at)
    A.model(s, amb, 'Body', ambulance_shell(V, True))
    A.model(s, amb, 'Fittings', ambulance_fittings(V, True))
    beacon(s, amb, V, (0, 3.1, 1.4), 70.0, 95.0, 12.0)
    for x in (-0.82, 0.82):
        A.glow_card(s, amb, V, 'Headlight glare', (x, 0.9, 3.22), 0.7, (1.0, 0.95, 0.8), 3.0)
        s.box('Tail lamp', amb, (x * 1.16, 1.1, -2.96), (0.2, 0.3, 0.02), (1, 0.05, 0.05), emissive=(1, 0.05, 0.05), emissive_intensity=5.0, shadows=False)
    A.headlights(s, amb, 0.82, 0.9, 3.4, 380.0, 45, inner=14, outer=34, name='Ambulance headlight')
    inside(s, amb, V)

    # The escort: cruisers ahead, alongside and behind, each weaving in its lane.
    escort = ((AMB_X, 17.0, True), (-2.7, 11.0, True), (-2.7, -2.0, False), (8.1, 4.0, False), (AMB_X, -12.5, True), (-2.7, -16.0, True), (8.1, -11.0, False))
    for i, (x, z, full) in enumerate(escort):
        frames = 150 + 40 * (i % 3)
        side = 1 if i % 2 else -1
        weave = P.clip(V, f'EscortWeave{i % 6}', frames, [P.track('Position', [(0, (0, 0, 0)), (frames // 4, (side * 0.6, 0, 1.3)), (frames // 2, (0, 0, -0.7)), (3 * frames // 4, (-side * 0.5, 0, 0.9)), (frames, (0, 0, 0))], 'SmoothStep'),
                                                         P.track('Rotation', [(0, (0, 0, 0)), (frames // 8, (0, side * 5, 0)), (3 * frames // 8, (0, -side * 6, 0)), (5 * frames // 8, (0, side * 4, 0)), (frames, (0, 0, 0))], 'SmoothStep')])
        car = P.looping(s, g, f'Escort {i}', weave, at(R, (x, 0, z)))
        A.patrol_cruiser(s, car)
        hx, hy, hz = A.PATROL_HEADLAMP
        for dx in (-hx, hx):
            A.glow_card(s, car, V, 'Headlight glare', (dx, hy, hz + 0.05), 0.45, (1.0, 0.95, 0.8), 0.8)
            A.glow_card(s, car, V, 'Tail lamp glare', (dx * A.PATROL_TAIL_LAMP[0] / hx, A.PATROL_TAIL_LAMP[1], A.PATROL_TAIL_LAMP[2] - 0.03), 0.28, (1.0, 0.05, 0.05), 0.8, (0, 180, 0))
        if full:
            A.headlights(s, car, hx, hy, hz + 0.15, 260.0, 32)
        M.beacons(s, car, V, 110.0 if full else 0.0, 150.0, 22.0, 1.0 + 0.1 * i, glare=(0.5, 1.2))
    # The helicopter over them, its light on the ambulance's roof.
    bob = P.clip(V, 'HeliBob', 170, [P.track('Position', [(0, (0, 0, 0)), (45, (1.6, 0.9, -2.0)), (95, (-1.0, -0.7, 2.5)), (140, (0.8, 0.4, 0.6)), (170, (0, 0, 0))], 'SmoothStep'),
                                     P.track('Rotation', [(0, (0, 0, 0)), (45, (4, 6, -7)), (95, (-3, -5, 6)), (140, (2, 3, -3)), (170, (0, 0, 0))], 'SmoothStep')])
    copter_at = at(R, (-9.0, 15.0, 12.0))
    copter = P.looping(s, s.entity('Helicopter', g, copter_at, (12, 10, -6)), 'Hover', bob)
    A.model(s, copter, 'Body', A.helicopter(V), shadows=False)
    blades = P.looping(s, copter, 'Rotor', P.clip(V, 'RotorSpin', 6, [P.track('Rotation', [(0, (0, 0, 0)), (3, (0, 180, 0)), (6, (0, 359.9, 0))])]), (0, 1.52, 0))
    for yaw in (0, 90):
        s.box('Blade', blades, (0, 0, 0), (0.22, 0.04, 9.6), (0.08, 0.08, 0.09), rot=(0, yaw, 0), shadows=False)
    M_see(s.box('Rotor disc', blades, (0, 0, 0), (9.6, 0.02, 9.6), (0.3, 0.3, 0.32), shape='Cylinder', shadows=False), 0.1)
    s.box('Strobe', copter, (0, -1.1, -1.0), (0.14, 0.14, 0.14), (1, 0.1, 0.1), emissive=(1, 0.1, 0.1), emissive_intensity=9.0, shape='Sphere', shadows=False)
    beam_at = at(copter_at, (0, -1.2, 0))
    # (Until the cut to the inside: nothing here casts a shadow but the sun, so it would light the cot.)
    s.light('Helicopter searchlight', P.between(s, g, 'Searchlight', None, 'defib', 0.0, beam_at), beam_at, 'Spot', (0.85, 0.92, 1.0), 1500.0, 40, rot=look_rotation(beam_at, at(amb_at, (0, 2, 0))), inner=5, outer=10)

    # From the road ahead of the lead cruisers, back at the ambulance coming on; then up and over
    # the escort to look down on the whole run from behind.
    M.shot(s, marks, 'ambulance_run', at(R, (-0.6, 0.8, 31.0)), at(R, (AMB_X, 1.7, 2.0)), 32, 7.3, ride=0.6,
           via=[(at(R, (-8.6, 3.4, 13.0)), at(R, (AMB_X, 1.5, 0.0)), 46)], end=(at(R, (-9.5, 15.0, -27.0)), at(R, (AMB_X - 0.5, 0.5, 3.0)), 56))
    # Inside, from up in the corner by the bulkhead: the drummer under the paddles, the cop, and
    # the escort's lights in the back windows. Handheld, on the road.
    M.shot(s, marks, 'defib', at(amb_at, (0.74, 2.52, 1.3)), at(amb_at, (-0.28, 1.4, -0.7)), 74, 9.9, hand=True, ride=1.2,
           end=(at(amb_at, (0.58, 2.25, 0.85)), at(amb_at, (-0.3, 1.42, -0.35)), 62))


# ---- the corridor: gurney -------------------------------------------------------------------
def rush(s, root, marks, V, M):
    g = place_at(s, root, 'The hospital corridor', 'gurney', 'resurrection', H)
    # The rest of the building over and round the corridor (it keeps heaven's sun out).
    s.slab('Storey above', g, H[0] - 14, H[0] + 14, 3.0, 5.0, H[2] - 60, H[2] + 60, (0.5, 0.5, 0.5))
    for side in (-1, 1):
        s.slab('Building', g, H[0] + side * 1.82, H[0] + side * 9, -0.1, 3.0, H[2] - 60, H[2] + 60, (0.5, 0.5, 0.5))
    for z in (-58.5, 58.5):
        s.slab('Far wall', g, H[0] - 1.8, H[0] + 1.8, 0, 3.0, H[2] + z - 0.5, H[2] + z + 0.5, (0.75, 0.78, 0.8))
    period = 12.0
    frames = int(round(period / RUN))
    going = P.looping(s, g, 'Corridor going by', P.clip(V, 'CorridorBy', frames, [P.track('Position', [(0, (0, 0, 0)), (frames, (0, 0, -period))])]), H)
    glow = A.mat(V, 'Palette', (1, 1, 1), glow=(0.92, 0.97, 1.0), power=2.5, glow_tex=False)
    nurse = P.figure(V, 'Nurse_wall', NURSE[0], NURSE[1], AT_WALL, 'a nurse, back to the wall to let them by')
    for k in range(-4, 5):
        for half, kind in enumerate('AB'):
            z = k * period + half * 6.0
            A.model(s, going, 'Corridor', corridor(V, kind), (0, 0, z))
            for dz in LIGHTS:
                A.model(s, going, 'Ceiling panel', panel(V), (0, 2.89, z + dz), material=glow, shadows=False)
        A.model(s, going, 'Emergency sign', strip_sign(V, 'Emergency', 0.14), (0, 2.55, k * period + 9.0), (0, 0, 0), (0.85, 0.85, 1), A.mat(V, 'Emergency', glow=(1, 1, 1), power=0.9, both=True), shadows=False)
        P.place(s, going, 'Nurse', nurse, (1.38, 0, k * period + 0.7), 250)
    for i, z in enumerate((-7.5, -2.5, 2.5, 7.5)):
        s.light(f'Corridor light {i}', g, at(H, (0, 2.6, z)), 'Point', (0.9, 0.96, 1.0), 15.0, 8)
    # A panel going over every 3 m: its light runs down the gurney.
    over = P.looping(s, g, 'Light going over', P.clip(V, 'PanelOver', 20, [P.track('Position', [(0, (0, 0, 0)), (20, (0, 0, -3.0))])]), at(H, (0, 2.5, 1.5)))
    s.light('Panel light', over, (0, 0, 0), 'Point', (0.95, 0.98, 1.0), 14.0, 3.2)

    # The drummer's gurney, feet first, the camera at its foot; a medic pushing at the head, the
    # cop and a nurse with the drip running alongside; the others behind in a line.
    rattle = [P.clip(V, f'GurneyRattle{i}', 70 + 16 * i, [P.track('Position', [(0, (0, 0, 0)), (18 + 4 * i, (0.03 + 0.02 * i, 0, 0.1 * i)), (40 + 8 * i, (-0.03 - 0.02 * i, 0, -0.14 * i)), (70 + 16 * i, (0, 0, 0))], 'SmoothStep'),
                                                          P.track('Rotation', [(0, (0, 0, 0)), (20 + 4 * i, (0, 1.2 + i, 0.3)), (48 + 8 * i, (0, -1.2 - i, -0.3)), (70 + 16 * i, (0, 0, 0))], 'SmoothStep')]) for i in range(4)]
    pusher = P.figure(V, 'Medic_push', MEDIC[0], MEDIC[1], PUSH, 'an EMS worker pushing a gurney')
    for i, (who, x) in enumerate((('drummer', 0.0), ('guitar', 0.42), ('bass', -0.4), ('vocals', 0.36))):
        cart = P.looping(s, g, f'Gurney: {who}', rattle[i], at(H, (x, 0, -3.5 * i)))
        A.model(s, cart, 'Top', gurney(V), (0, 0, 0), (0, 180, 0))
        A.model(s, cart, 'Legs', gurney_legs(V), (0, 0.78, 0))
        patient(s, cart, V, who, 0.92, -1)
        dangle(s, cart, V, 'IV bag', (-0.33, 1.95, -0.85), 0.1, 'iv', i)
        runner(s, cart, V, 'Medic pushing', pusher, (0, 0, -1.62), 0, i)
        if i:
            dangle(s, cart, V, 'Chart', (0.31, 0.98, 0.3), 0.04, 'clip', i + 2)
    runner(s, g, V, 'Cop', P.figure(V, 'Cop_runs', COP[0], COP[1], COP_RUNS, 'the cop running beside the gurney'), at(H, (0.82, 0, -0.55)), 0, 1)
    runner(s, g, V, 'Nurse with the drip', P.figure(V, 'Nurse_drip', NURSE[0], NURSE[1], IV_HELD, 'a nurse running with the drip held up'), at(H, (-0.82, 0, -0.9)), 0, 2)
    M.shot(s, marks, 'gurney', at(H, (0.28, 1.7, 1.12)), at(H, (0.0, 1.05, -0.72)), 56, 8.5, hand=True, ride=0.9,
           end=(at(H, (0.44, 1.92, 1.36)), at(H, (-0.04, 1.05, -0.8)), 62))


# ---- out of the ward's window ---------------------------------------------------------------
# Everything here is in the window's own space: x across it, the ground at y 0, and depth the
# metres out from the glass (z = -depth). The eye in the ward is 8.8 m up and the sill hides the
# ground nearer than about 140 m, so close to the hospital only what stands tall shows.
STOREY = 3.1
TOWN_REACH = 540.0          # the town's edge from the window; the hills stand beyond it
WALLS = ('paper', 'marble_shade', 'bone', 'stone_red', 'bone_dark', 'rail', 'marble', 'paper', 'marble_shade', 'bone_dark')
PANES = ('glass',) * 7 + ('sky', 'steel_dark', 'paper')        # a pane: mostly dark, some sky in it, some blinds
ROOFS = ('steel_dark', 'stone', 'post', 'cab_dark', 'deck_dark')
# The MitchTree recipes (Engine/Assets/Trees) the trees are grown from, each again with other seeds.
TREES = (('WardMapleA', 'Maple', 21), ('WardMapleB', 'Maple', 4), ('WardMapleC', 'MapleGnarl', 9), ('WardPine', 'Pine', 11),
         ('WardBirch', 'Presets/Birch', 3), ('WardOak', 'Presets/Oak', 7))


def tree(venue, name, source, seed):
    """A MitchTree recipe in the venue (Engine/Docs/MitchTree.md): one of the engine's with its own
    seed, and a fuller crown (the engine's are first drafts, thin enough to see through: more and
    bigger leaf cards, and some along the limbs). A recipe is a model path: the tree is grown when
    it loads. Returns its asset path."""
    with open(os.path.join(A.ROOT, 'Engine', 'Assets', 'Trees', source + '.mtree')) as f:
        recipe = json.load(f)
    recipe['Name'], recipe['Seed'] = name, seed
    leaves = recipe['Leaves']
    broad = leaves['Kind'] == 'Broadleaf'
    leaves['PerStem'] = round(leaves['PerStem'] * (2.2 if broad else 1.5))
    leaves['Size'] = round(leaves['Size'] * (1.7 if broad else 1.3), 3)
    leaves['ParentCoverage'] = max(leaves['ParentCoverage'], 0.4 if broad else 0.6)
    save_bytes(os.path.join(A.ROOT, 'Assets', 'Venues', venue, 'Trees', name + '.mtree'), (json.dumps(recipe, indent=4) + '\n').encode())
    return f'Assets/Venues/{venue}/Trees/{name}.mtree'


def _panes(m, rng, wide, y, facing, off, w=1.35, h=1.7, pitch=2.7):
    """A row of windows, their middles at height y, on the wall facing 'facing' ((0, 0, 1) the
    front, (+-1, 0, 0) a side), wide metres of wall off from the building's middle."""
    n = max(1, int((wide - 1.6) / pitch))
    step = (wide - 1.6) / n
    for i in range(n):
        u = -wide / 2 + 0.8 + (i + 0.5) * step
        if facing[2]:
            q = [(u - w / 2, y - h / 2, off), (u + w / 2, y - h / 2, off), (u + w / 2, y + h / 2, off), (u - w / 2, y + h / 2, off)]
        else:
            x = facing[0] * off
            q = [(x, y - h / 2, u - w / 2), (x, y - h / 2, u + w / 2), (x, y + h / 2, u + w / 2), (x, y + h / 2, u - w / 2)]
        m.face(q, rng.choice(PANES), outward=facing)


def _roof_plant(m, rng, w, d, top, wall):
    """What stands on a flat roof: the stair head, air handlers, and a water tank or an aerial."""
    m.box((rng.uniform(-w / 4, w / 4), top + 1.3, rng.uniform(-d / 5, d / 5)), (3.2, 2.6, 3.6), wall)
    for _ in range(rng.randint(1, 3)):
        m.box((rng.uniform(-w / 2 + 1.6, w / 2 - 1.6), top + 0.6, rng.uniform(-d / 2 + 1.6, d / 2 - 1.6)),
              (rng.uniform(1.4, 2.6), 1.2, rng.uniform(1.4, 2.4)), rng.choice(('steel', 'rail', 'post')))
    x, z, roll = rng.uniform(-w / 2 + 2.2, w / 2 - 2.2), rng.uniform(-d / 2 + 2.2, d / 2 - 2.2), rng.random()
    if roll < 0.22:
        for dx in (-1, 1):
            for dz in (-1, 1):
                m.box((x + dx * 1.0, top + 1.1, z + dz * 1.0), (0.16, 2.2, 0.16), 'steel_dark')
        m.lathe((x, top + 2.2, z), [(1.5, 0.0), (1.5, 2.6), (0.05, 3.5)], 'wood', 10)
    elif roll < 0.45:
        m.tube([(x, top, z), (x, top + rng.uniform(5, 9), z)], 0.07, 'steel', 4)


def _apartment(m, rng, w, d, floors, proud, side):
    """A block of flats, its front toward +z: a taller ground floor under a string course, rows of
    windows on the front and on the side that shows (side: -1 / +1), a parapet, the roof's plant."""
    wall = rng.choice(WALLS)
    trim = 'marble_shade' if wall in ('paper', 'marble', 'bone') else 'paper'
    high = 4.0 + STOREY * (floors - 1)
    m.box((0, high / 2, 0), (w, high, d), wall)
    m.box((0, 3.9, 0), (w + 3 * proud, 0.25, d + 3 * proud), trim)
    m.box((0, high + 0.3, 0), (w + 0.5, 0.6, d + 0.5), trim)
    for f in range(floors):
        y = 2.1 if f == 0 else 4.0 + STOREY * (f - 1) + 1.65
        _panes(m, rng, w, y, (0, 0, 1), d / 2 + proud, 1.9 if f == 0 else 1.35, 2.3 if f == 0 else 1.7, 3.4 if f == 0 else 2.7)
        if f:
            _panes(m, rng, d, y, (side, 0, 0), w / 2 + proud)
    _roof_plant(m, rng, w, d, high + 0.6, wall)


def _office(m, rng, w, d, floors, proud, side):
    """An office block: glass between spandrels a storey apart, fins up the front, a plant room."""
    step = 3.6
    high = 4.5 + step * (floors - 1)
    frame = rng.choice(('steel', 'rail', 'marble_shade', 'paper'))
    m.box((0, high / 2, 0), (w, high, d), 'glass')
    m.box((0, 0.4, 0), (w + 2 * proud, 0.8, d + 2 * proud), frame)
    for f in range(floors):
        m.box((0, 4.5 + step * f - 0.5, 0), (w + 2 * proud, 1.0, d + 2 * proud), frame)
    n = max(2, int(w / 3.0))
    for i in range(n + 1):
        m.box((-w / 2 + w * i / n, high / 2, d / 2 + proud), (0.3, high, 2 * proud), frame)
    n = max(2, int(d / 3.0))
    for i in range(n + 1):
        m.box((side * (w / 2 + proud), high / 2, -d / 2 + d * i / n), (2 * proud, high, 0.3), frame)
    m.box((0, high + 1.3, 0), (w * 0.6, 2.6, d * 0.6), 'steel_dark')
    if rng.random() < 0.5:
        m.tube([(w * 0.2, high + 2.6, 0), (w * 0.2, high + rng.uniform(9, 16), 0)], 0.1, 'steel', 4)


def _gable(m, w, d, eave, rise, over, roof, wall):
    """A pitched roof on a w by d box, its ridge along x, and the wall up into both gables."""
    a, b, top = (-w / 2 - over, eave - 0.12, d / 2 + over), (w / 2 + over, eave - 0.12, d / 2 + over), eave + rise
    m.face([a, b, (b[0], top, 0), (a[0], top, 0)], roof, outward=(0, 1, 1), both=True)
    m.face([(a[0], a[1], -a[2]), (b[0], b[1], -b[2]), (b[0], top, 0), (a[0], top, 0)], roof, outward=(0, 1, -1), both=True)
    for sx in (-1, 1):
        m.face([(sx * w / 2, eave, d / 2), (sx * w / 2, eave, -d / 2), (sx * w / 2, eave + rise * d / (d + 2 * over), 0)], wall, outward=(sx, 0, 0))


def _house(m, rng, proud):
    w, d, floors = rng.uniform(8, 12), rng.uniform(7, 9), rng.choice((1, 2, 2))
    wall = rng.choice(('paper', 'marble', 'bone', 'marble_shade', 'stone_red', 'feather_tip'))
    high = 2.9 * floors
    m.box((0, high / 2, 0), (w, high, d), wall)
    _gable(m, w, d, high, rng.uniform(2.2, 3.4), 0.5, rng.choice(ROOFS), wall)
    m.box((rng.uniform(-w / 3, w / 3), high + 2.4, -d / 5), (0.7, 2.6, 0.7), 'stone_red')
    for f in range(floors):
        _panes(m, rng, w, 1.5 + 2.9 * f, (0, 0, 1), d / 2 + proud, 1.1, 1.2, 2.6)
        for sx in (-1, 1):
            _panes(m, rng, d, 1.5 + 2.9 * f, (sx, 0, 0), w / 2 + proud, 1.1, 1.2, 3.0)


def _church(m, rng, proud):
    """A stone church along x: nave, a square tower at one end and its spire."""
    m.box((3, 4.5, 0), (24, 9, 11), 'marble')
    _gable(m, 24, 11, 9.0, 5.5, 0.4, 'steel_dark', 'marble')
    for i in range(5):
        x = -5.5 + i * 4.2
        m.face([(x - 0.6, 3.0, 5.5 + proud), (x + 0.6, 3.0, 5.5 + proud), (x + 0.6, 6.6, 5.5 + proud), (x, 7.6, 5.5 + proud), (x - 0.6, 6.6, 5.5 + proud)], 'glass', outward=(0, 0, 1))
    m.box((-12, 10, 0), (6.5, 20, 6.5), 'marble')
    m.box((-12, 20.2, 0), (7.1, 0.5, 7.1), 'marble_shade')
    for face, off in (((0, 0, 1), 3.25 + proud), ((1, 0, 0), 3.25 + proud), ((-1, 0, 0), 3.25 + proud)):
        sub_ = Mesh('belfry')
        _panes(sub_, rng, 6.5, 16.5, face, off, 1.2, 3.0, 2.2)
        m.merge(sub_, (-12, 0, 0))
    m.box((-12, 27.5, 0), (5.6, 14.0, 5.6), 'steel_dark', taper=0.02)


def _water_tower(m, rng, proud):
    for dx in (-1, 1):
        for dz in (-1, 1):
            m.tube([(dx * 5.0, 0, dz * 5.0), (dx * 3.2, 24, dz * 3.2)], 0.28, 'steel', 5)
    m.tube([(0, 0, 0), (0, 24, 0)], 0.6, 'steel', 6)
    for y in (8, 16):
        m.box((0, y, 0), (9.2 - y * 0.15, 0.25, 9.2 - y * 0.15), 'steel')
    m.lathe((0, 22.5, 0), [(0.6, 0.0), (5.0, 1.6), (6.2, 4.0), (6.2, 8.5), (4.2, 10.6), (0.1, 11.6)], 'marble', 14)
    m.lathe((0, 28.5, 0), [(6.26, 0.0), (6.26, 1.2)], 'sky', 14)


def _stack(m, rng, proud):
    """A works: a long shed and its brick chimney, banded at the top."""
    m.box((10, 5, 0), (34, 10, 16), 'rail')
    _gable(m, 34, 16, 10.0, 3.0, 0.4, 'steel_dark', 'rail')
    m.lathe((-11, 0, 0), [(2.6, 0.0), (1.7, 44.0), (1.6, 52.0)], 'stone_red', 12)
    m.lathe((-11, 45, 0), [(1.72, 0.0), (1.66, 3.0)], 'paper', 12)


def _mast(m, rng, proud):
    """A radio mast, banded red and white."""
    for k in range(9):
        r0, r1 = 0.9 - k * 0.08, 0.9 - (k + 1) * 0.08
        m.tube([(0, k * 8.0, 0), (0, (k + 1) * 8.0, 0)], [r0, r1], 'amb_red' if k % 2 == 0 else 'white', 5, caps=False)
    m.box((0, 72.3, 0), (0.5, 0.6, 0.5), 'red_lamp')
    m.box((0, 1.5, 4), (5, 3, 4), 'paper')


LANDMARKS = {'church': _church, 'tower': _water_tower, 'stack': _stack, 'mast': _mast}


def town_plan():
    """What stands out of the window. Returns (lots, trees): a lot is (depth of its street, kind,
    x, z, yaw, seed, w, d, floors); a tree is (x, z). Streets run across the view: flats and
    offices in the middle of each (the far ones taller, towers off to the sides of the sun),
    houses out on the flanks, a landmark here and there, trees in the gaps."""
    rng = random.Random(404)
    lots, trees = [], []
    marks = {150: (-96, 'church'), 330: (150, 'tower'), 410: (-215, 'stack'), 500: (84, 'mast')}
    for depth in (105, 150, 200, 260, 330, 410, 500):
        reach = min(1.1 * depth + 20, 300)
        x = -reach
        mark = marks.get(depth)
        while x < reach:
            if mark and x >= mark[0]:
                lots.append((depth, mark[1], x + 17, -depth - 4.0, 0.0, rng.randrange(1 << 30), 0, 0, 0))
                x, mark = x + 40, None
                continue
            w, d = rng.uniform(13, 26), rng.uniform(12, 18)
            cx, z = x + w / 2, -(depth + rng.uniform(-8, 8))
            tall = depth >= 260 and abs(cx) > 60 and rng.random() < 0.2
            if tall or (depth >= 200 and rng.random() < 0.18):
                kind, floors = 'office', rng.randint(9, 15) if tall else rng.randint(4, 8)
            else:
                kind, floors = 'apartment', rng.randint(2, 4) if depth < 130 else rng.randint(3, 5 if depth < 180 else 8)
            if math.hypot(cx, depth) < TOWN_REACH:
                lots.append((depth, kind, cx, z, rng.uniform(-4, 4), rng.randrange(1 << 30), w, d, floors))
            gap = rng.choice((4, 5, 6, 8, 22))      # 22: a side street, a tree on its corner
            if gap > 20 and depth <= 260:
                trees.append((x + w + gap / 2 + rng.uniform(-3, 3), z + rng.uniform(2, 9)))
            x += w + gap
        for side in (-1, 1):
            x = reach + 14
            while x < 2.0 * depth + 30 and math.hypot(x, depth) < TOWN_REACH:
                for row in (0, 24):
                    z = -(depth + row + rng.uniform(-4, 4))
                    lots.append((depth, 'house', side * x, z, rng.choice((0, 90)) + rng.uniform(-8, 8), rng.randrange(1 << 30), 0, 0, 0))
                    if rng.random() < 0.3 and depth <= 260:
                        trees.append((side * (x + 8.5), z + rng.uniform(-6, 6)))
                x += rng.uniform(15, 21)
    return lots, trees


def town(venue, name, depths):
    """The streets of town_plan at these depths, one model."""
    def build(m):
        for depth, kind, x, z, yaw, seed, w, d, floors in town_plan()[0]:
            if depth not in depths:
                continue
            rng, one = random.Random(seed), Mesh(kind)
            proud = 0.08 + depth * 0.001        # how far a pane stands off its wall: more with distance, for the depth buffer
            if kind == 'apartment':
                _apartment(one, rng, w, d, floors, proud, -1 if x > 0 else 1)
            elif kind == 'office':
                _office(one, rng, w, d, floors, proud, -1 if x > 0 else 1)
            elif kind == 'house':
                _house(one, rng, proud)
            else:
                LANDMARKS[kind](one, rng, proud)
            m.merge(one, (x, 0, z), (0, yaw, 0))
    return A.prop(venue, name, build)


def country(venue):
    """The ground out to the hills and the hills: flat under the town, rising beyond it."""
    def build(m):
        def height(x, z):
            r = math.hypot(x, z)
            t = min(max((r - TOWN_REACH - 20) / 520.0, 0.0), 1.0)
            t = t * t * (3 - 2 * t)
            return t * (35.0 + 120.0 * (0.5 + 0.5 * math.sin(x * 0.006 + 1.3) * math.cos(z * 0.004 + x * 0.003)) * (0.6 + 0.4 * math.sin(x * 0.017 + z * 0.011)))
        m.grid(-1500, 1500, -1400, -16, 60, 36, height, 'white')
    return A.prop(venue, 'WardCountry', build, smooth_=True)


def outside(s, parent, V, origin):
    """The view from the ward: origin is the ground under the window's middle. Trees close by on
    the hospital's lawn, standing either side of where the sun is; the town; the hills."""
    g = s.entity('Out of the window', parent, origin)
    A.model(s, g, 'Country', country(V), material=A.mat(V, 'Palette', color=(0.2, 0.3, 0.16), rough=1.0), shadows=False)
    for name, depths in (('WardTownNear', (105, 150)), ('WardTownMid', (200, 260)), ('WardTownFar', (330, 410, 500))):
        A.model(s, g, name, town(V, name, depths), material=A.mat(V, 'Palette', rough=0.85), shadows=False)
    kinds = [tree(V, *t) for t in TREES]
    maple_a, maple_b, gnarl, pine, birch, oak = kinds
    rng = random.Random(77)
    # (across, metres out, which, scale): the nearest stand tall at the sides of the window and
    # the middle is kept low, under the sun.
    lawn = [(-19, 20, maple_a, 1.15), (17, 24, maple_b, 1.2), (-27, 34, pine, 1.0), (25, 40, birch, 1.0), (-11, 46, oak, 1.0),
            (9, 52, maple_a, 1.0), (-38, 30, gnarl, 1.1), (36, 28, maple_b, 1.05), (31, 60, pine, 0.95), (-33, 62, birch, 1.05),
            (1, 80, oak, 1.1), (-52, 44, maple_b, 1.2), (50, 48, gnarl, 1.15)]
    x = -130.0
    while x < 130:
        if abs(x) > 14:
            lawn.append((x, rng.uniform(64, 96), rng.choice(kinds), rng.uniform(0.85, 1.15)))
        x += rng.uniform(13, 21)
    for x, z in town_plan()[1]:
        lawn.append((x, -z, rng.choice(kinds), rng.uniform(0.85, 1.2)))
    for i, (x, depth, path, scale) in enumerate(lawn):
        A.model(s, g, f'Tree {i + 1}', path, (x, 0, -depth), (0, rng.uniform(0, 360), 0), scale)
    return g


# ---- the ward: resurrection ---------------------------------------------------------------
def morning_after(s, root, marks, V, M):
    half, high, z0, z1 = WARD
    floor = at(W, (0, ROOM_Y, 0))
    g = s.entity('Ward', place_at(s, root, 'The hospital ward', 'resurrection', None, floor), floor)

    def out(p):
        return at(floor, p)
    A.model(s, g, 'Room', ward(V), material=A.mat(V, 'Palette', rough=0.9))
    cabinet, chair = ward_fittings(V)
    # The light: the day coming in at the window (nothing but heaven's sun casts shadows, and the
    # walls keep that out), and a little of the room's own.
    sun = (0.0, 5.5, z0 - 6.0)
    s.light('Daylight', g, sun, 'Spot', (1.0, 0.93, 0.8), 450.0, 20, rot=look_rotation(sun, (0, 0.6, 1.0)), inner=34, outer=58, fog=0.0)
    for z in (-1.2, 2.6):
        s.light('Ward light', g, (0, 2.2, z), 'Point', (1.0, 0.95, 0.88), 4.0, 8)
    # Four beds along the walls, heads to the wall: the window row and the row behind it. Each of
    # the band sits up in theirs their own way, turned to the window.
    near, back = WARD_ROWS
    beds = (('drummer', -1, near, 'up'), ('guitar', 1, near, 'back'), ('bass', -1, back, 'forward'), ('vocals', 1, back, 'easy'))
    for who, side, z, kind in beds:
        bed = s.entity(f'Bed: {who}', g, (side * (half - 1.25), 0, z), (0, 0 if side < 0 else 180, 0))
        A.model(s, bed, 'Bed', ward_bed(V, kind in ('back', 'easy')), material=A.mat(V, 'Palette', rough=0.9))
        # (In the bed's space the window is on the right of someone in a left-hand bed.)
        pose = in_bed(kind, -side)
        P.place(s, bed, who.capitalize(), P.figure(V, f'Ward_{who}', LOOKS[who][0], LOOKS[who][1], pose, f'the {who} sitting up in bed, looking out of the window'),
                (-0.5 if kind in ('up', 'forward') else -0.42, BED_TOP - SEATED_HIP, 0), 90)
        A.model(s, g, 'Cabinet', cabinet, (side * (half - 0.35), 0, z - 0.85), (0, -side * 90, 0))
        stand = (side * (half - 0.3), 0, z - 0.2)
        s.box('Monitor stand', g, at(stand, (0, 0.85, 0)), (0.03, 1.7, 0.03), (0.7, 0.72, 0.76), metallic=0.9, rough=0.3, shape='Cylinder')
        s.box('Monitor', g, at(stand, (0, 1.7, -0.06)), (0.46, 0.36, 0.1), (0.14, 0.15, 0.17))
        monitor(s, g, f'Heart monitor: {who}', at(stand, (0, 1.7, 0.0)), 0)
        drip = (side * (half - 0.25), 0, z + 0.62)
        s.box('Drip stand', g, at(drip, (0, 1.0, 0)), (0.03, 2.0, 0.03), (0.7, 0.72, 0.76), metallic=0.9, rough=0.3, shape='Cylinder')
        dangle(s, g, V, 'Drip', at(drip, (0, 2.0, 0)), 0.1, 'iv', len(who))
    # Flowers on three of the cabinets.
    for i, (x, z, c) in enumerate(((-half + 0.35, near - 0.85, (0.95, 0.75, 0.2)), (half - 0.35, near - 0.85, (0.9, 0.3, 0.35)), (-half + 0.35, back - 0.85, (0.85, 0.5, 0.9)))):
        s.box('Vase', g, (x, 0.83, z), (0.1, 0.18, 0.1), (0.75, 0.85, 0.9), shape='Cylinder')
        for k in range(3):
            s.box('Flower', g, (x + 0.05 * (k - 1), 1.0 + 0.03 * (k % 2), z + 0.03 * (1 - k)), (0.09, 0.09, 0.09), c, shape='Sphere')
    for yaw in (28, -34):
        s.box('Drumstick', g, (-half + 2.0, 0.85, near), (0.03, 0.41, 0.03), (0.85, 0.7, 0.45), rot=(90, yaw, 0), shape='Cylinder')
    # A chair by each of the back row; the cop in one, hat in his lap, looking out with them.
    for side in (-1, 1):
        A.model(s, g, 'Chair', chair, (side * (half - 1.3), 0, back + 1.25), (0, 180, 0))
    P.place(s, g, 'Cop', P.figure(V, 'Cop_chair', COP[0], COP[1], COP_CHAIR, 'the cop in the chair by the bed, looking out of the window'), (-half + 1.3, 0.48 - SEATED_HIP, back + 1.2), 180)

    # Out of the window: the hospital's trees, the town beyond them, hills, and the sky (the
    # shot's own: tagged sky).
    outside(s, g, V, (0, -ROOM_Y, z0))
    # From well back in the room, all four of them in the picture from behind and the window across
    # the whole of it (the back row's heads are 2.65 m either side of the aisle: from here they
    # are in the picture on a 4:3 screen too, not only a wide one); and slowly back to the door.
    # The song rings out for 16 s of the hold: whatever comes after, the picture stays here.
    M.shot(s, marks, 'resurrection', out((0.0, 1.55, 4.3)), out((0.0, 2.15, z0)), 54, 30, sky=SKY_HOUR,
           end=(out((0.0, 1.6, z1 - 0.7)), out((0.0, 2.0, z0)), 60))


def build(s, root, marks, V, M):
    """Everything on Earth, under root. M: make_story_afterlife (its road, cruisers, crash site and
    shot()). Returns the drummer's hand on the road at the crash site."""
    global M_see
    M_see = M.see_through
    earth = s.group('Earth', root)
    hand, _ = crash(s, earth, marks, V, M)
    run(s, earth, marks, V, M)
    rush(s, earth, marks, V, M)
    morning_after(s, earth, marks, V, M)
    return hand
