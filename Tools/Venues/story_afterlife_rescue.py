"""The rescue on Earth that My Hero cuts away to (Design/Highway-to-the-Afterlife.md, "5. Foo
Fighters - My Hero"), far off along +x in heaven's scene. Each cut to Earth is the next thing that
happens to the band, one place at a time, each on its own story flag:

  cpr            the crash site at night: the cop's hands on the drummer's chest (slow motion)
  innocent       the same road, a medic on the compressions now: the cop's partner holds a sheet
                 off the dispatch up to him, INNOCENT across it, and he looks from it to the drummer
  loading        the same road: the drummer on a gurney going into the back of an ambulance
  ambulance_run  the highway: the ambulance at speed inside an escort of cruisers, a helicopter over it
  defib          inside that ambulance: paddles on the drummer's chest, everything on a hook or a
                 strap swinging; the shock itself is the flag 'shock'
  gurney         a hospital corridor: the four of them rushed down it on gurneys, shot from the
                 foot of the drummer's
  surgery        an operating theatre: the drummer on the table under the lamps, the team's hands
                 at work, the next theatre through the glass and the cop at the doors' window
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
O = (3600.0, 0.0, 0.0)      # the operating theatre: the floor under the middle of the drummer's table
W = (3100.0, 0.0, 0.0)      # the hospital ward: the ground under the middle of its floor

SKY_HOUR = 12.0             # the hour of the sky out of the ward's window (VenueShow::UpdateShotSky)
STEP = 1.6                  # metres of road a frame on the run (48 m/s, as the chase)
RUN = 0.15                  # metres of corridor a frame (4.5 m/s: a run with a gurney)
AMB_X = 2.7                 # the ambulance's lane on the run
FLOOR = 0.72                # an ambulance's floor above the road
ROOM_Y = 26.0               # the ward's floor above the ground (the eighth storey: a hospital is tall)
MONITOR = (-0.84, 1.86, 0.02)   # the ambulance's heart monitor: its screen's middle, on the wall over the patient's chest
MONITOR_YAW = 62.0          # the way it faces: out from the wall (90) and turned to the bulkhead, where the camera is

LOOKS = {'drummer': ('Son_01', '01_A'), 'guitar': ('Daughter_01', '02_C'), 'bass': ('Mother_01', '03_A'), 'vocals': ('SchoolBoy_01', '04_C')}
MEDIC = ('Son_01', '02_A')
COP = ('ShopKeeper_01', '04_B')
NURSE = ('Mother_02', '01_C')
PARTNER = ('Mother_01', '04_B')         # the cop's partner: his uniform

# Poses (story_legion_people.Pose: seated; torso / head Euler; arms (shoulder Euler, elbow bend)).
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
        # The monitor's housing, on a bracket that turns it toward the front of the box.
        m.box(add(MONITOR, rot((0, 0, -0.13), (0, MONITOR_YAW, 0))), (0.62, 0.48, 0.24), 'steel_dark', euler=(0, MONITOR_YAW, 0))
        m.box((-1.08, MONITOR[1], MONITOR[2]), (0.16, 0.1, 0.1), 'steel')
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
SILL = 0.42                       # the window's sill above the floor: low, to look down on the town from
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
        m.box((0, SILL / 2, z0 - 0.05), (2 * half + 0.2, SILL, 0.2), 'paper')
        m.box((0, high - 0.1, z0 - 0.05), (2 * half + 0.2, 0.2, 0.2), 'paper')
        m.box((0, SILL + 0.02, z0 + 0.1), (2 * half, 0.04, 0.4), 'white')
        # Three panes (no post up the middle: that is where the sun stands).
        for k in range(4):
            m.box((-half + k * 2 * half / 3, (SILL + high - 0.2) / 2, z0 - 0.05), (0.1, high - 0.2 - SILL, 0.12), 'white')
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
CHARGE = 6.2        # the seconds from the flag defib to the flag shock (Tools/Story: 'section:verse_3-6.2')
# VenueFigure fields for someone sat bent over, elbows on the knees, face in both hands.
COP_CANT_WATCH = dict(Bow=34.0, Lean=24.0, Nod=26.0,
                      LeftArm=P.arm(hand=(-0.055, 1.0, 0.5), pole=(-0.5, -1, 0.2), fingers=(0.1, 1, 0.15), palm=(0.25, 0, -1), grip=0.1),
                      RightArm=P.arm(hand=(0.055, 1.0, 0.5), pole=(0.5, -1, 0.2), fingers=(-0.1, 1, 0.15), palm=(-0.25, 0, -1), grip=0.1))


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


def beacon(s, parent, V, where, red=0.0, blue=0.0, reach=20.0, speed=1.0, housings=True):
    """A lightbar at where: red and blue lamps, their glare turning, and (red / blue above 0) two
    spot lights sweeping round at those levels. make_story_afterlife.lightbar's, with the levels
    to choose: a dozen of the crash site's would burn the run out."""
    spin = P.clip(V, 'LightbarSpin', 24, [P.track('Rotation', [(0, (0, 0, 0)), (12, (0, 180, 0)), (24, (0, 359.9, 0))])])
    if housings:
        s.box('Lamp red', parent, at(where, (-0.4, 0.06, 0)), (0.45, 0.14, 0.24), (1, 0.05, 0.05), emissive=(1, 0.05, 0.05), emissive_intensity=8.0, shadows=False)
        s.box('Lamp blue', parent, at(where, (0.4, 0.06, 0)), (0.45, 0.14, 0.24), (0.1, 0.2, 1), emissive=(0.1, 0.2, 1), emissive_intensity=8.0, shadows=False)
    turning = P.looping(s, parent, 'Sweep', spin, at(where, (0, 0.2, 0)), speed=speed)
    if red > 0:
        s.light('Sweep red', turning, (0, 0, 0), 'Spot', (1.0, 0.05, 0.05), red, reach, rot=(10, 0, 0), inner=14, outer=32)
        s.light('Sweep blue', turning, (0, 0, 0), 'Spot', (0.1, 0.25, 1.0), blue, reach, rot=(10, 180, 0), inner=14, outer=32)
    for yaw, c in ((0, (1.0, 0.06, 0.05)), (180, (0.12, 0.25, 1.0))):
        A.glow_card(s, turning, V, 'Glare', rot((0, 0.05, 0.3), (0, yaw, 0)), 0.5, c, 1.2, (0, yaw, 0))


def runner(s, parent, V, name, look, pos, yaw, k, arms=('Left', 'Right'), **pose):
    """A skinned figure running on the spot (the corridor goes by). arms: the ones that swing."""
    clip = P.gait(V, 'Run' + ''.join(a[0] for a in arms), 20, 0.9, 0.32, 0.035, arms=arms)
    fields = dict(dict(Lean=10.0, Crouch=0.05), **pose)
    return P.actor(s, parent, name, look[0], look[1], pos, yaw, motion=clip, speed=0.9 + 0.07 * (k % 4), **P.striding(0.9, **fields))


def pushing(lean=12.0):
    """VenueFigure fields for someone 0.45 m behind the end of a gurney (the frame's corners at
    +-0.24 across, 0.86 up), a hand on each."""
    return dict(Lean=lean, Bow=6.0, Nod=-4.0,
                LeftArm=P.arm(hand=(-0.24, 0.9, 0.46), pole=(-1, -0.6, -0.4), palm=(0, -1, 0), grip=0.85),
                RightArm=P.arm(hand=(0.24, 0.9, 0.46), pole=(1, -0.6, -0.4), palm=(0, -1, 0), grip=0.85))


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
    hand = M.crash_site(s, earth, V, site, {'lifted': 'loading', 'relieved': 'innocent', 'cop': None}, cop=cop_at, ems=True, wreck_at=(4.0, 0, -2.0), ambulance=False)
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
    braun(s, amb, 'Body')
    braun(s, amb, 'OpenDoors')
    braun_hanging(s, amb, V)
    beacon(s, amb, V, (0, 2.11, 1.97), 450, 600, 60, housings=False)
    s.light('Ambulance inside', amb, (0, 2.45, -1.0), 'Point', (0.9, 0.95, 1.0), 9.0, 6)
    s.light('Ambulance work light', amb, (0, 2.58, -3.1), 'Spot', (1.0, 0.97, 0.9), 240.0, 16, rot=(62, 180, 0), inner=34, outer=60)
    start = (0, 0, -4.9)
    waiting = P.between(s, amb, 'Gurney waiting', None, 'loading', 0.0, start)
    stood = s.entity('Gurney', waiting, (-0.9, 0, -5.3), (0, -22, 0))
    braun(s, stood, 'Deck')
    for legs, z in [('FrontLegs', 0.57), ('RearLegs', -0.61)]:
        braun(s, stood, legs, (0, 0.774, z))
    s.box('Blanket, folded', stood, (0, 0.96, -0.3), (0.5, 0.08, 0.5), (0.6, 0.72, 0.84), rough=1.0)
    # loading: the gurney runs in head first (2.6 m: its foot still out of the doors at the end),
    # its legs folding up under it as they reach the bumper.
    loading = P.between(s, amb, 'Loading', 'loading', None, 0.0, start)
    go_in = P.clip(V, 'GurneyIn', 66, [P.track('Position', [(0, (0, 0, 0)), (66, (0, 0, 2.6))], 'SmoothStep')])
    moving = P.play(s, loading, 'Gurney goes in', 'loading', go_in, start)
    braun(s, moving, 'Deck')
    for legs, z, first, last in [('FrontLegs', 0.57, 10, 28), ('RearLegs', -0.61, 30, 59)]:
        rest, stowed = (0, 0, 0), (97, 0, 0)
        fold = P.clip(V, 'Braun' + legs, 66, [P.track('Rotation', [(0, rest), (first, rest), (last, stowed), (66, stowed)], 'SmoothStep')])
        hinge = P.play(s, moving, legs + ' fold', 'loading', fold, (0, 0.774, z))
        braun(s, hinge, legs)
    patient(s, moving, V, 'drummer')
    dangle(s, moving, V, 'IV bag', (0.33, 1.95, 0.85), 0.1, 'iv', 1)
    # The people are skinned (P.actor): the medic walks the gurney in with a hand on each corner of
    # its foot, another kneels inside with both arms out for its head, the cop stands by, a hand out.
    walk = P.gait(V, 'WalkPushing', 30, 0.5, 0.1, 0.015, arms=())
    P.actor(s, moving, 'Medic at the foot', MEDIC[0], MEDIC[1], (0, 0, -1.45), 0, motion=walk, **P.striding(0.5, **pushing(8.0)))
    P.actor(s, loading, 'Medic inside', MEDIC[0], MEDIC[1], (0.55, FLOOR, -1.2), 200, 'Kneeling', Bow=14.0, Lean=8.0, Nod=10.0, HeadTurn=-15.0,
            LeftArm=P.arm(62, 6, 25, grip=0.3), RightArm=P.arm(62, 6, 25, grip=0.3), LeftLeg=P.leg(8), RightLeg=P.leg(8))
    cop_stands = (-1.6, 0, -4.2)
    P.actor(s, loading, 'Cop', COP[0], COP[1], cop_stands, 75, Lean=4.0, Nod=8.0, HeadTurn=P.turn_to(cop_stands, 75, (0, 1.0, -3.4), 50.0),
            LeftArm=P.arm(8, 10, 18), RightArm=P.arm(68, 12, 28, grip=0.05))

    innocent(s, earth, marks, V, M, site)

    cop_ground = (cop_eye[0], 0, cop_eye[2])
    cop_head = at(cop_ground, M.P_rot((0, 0.95, 0.45), cop_at[1]))      # he leans over the drummer as he pumps
    cop_hands = at(cop_ground, M.P_rot((0, 0.3, 0.75), cop_at[1]))
    # From low beside his hands up to his face, so the driver from the chase is known; both to the
    # left of the picture while the highway is up. (The holds of the cuts to Earth run on just past
    # the chart's next camera cut, 34.3, 56.2, 74.1, 220.7 and 233.2 s in the Harmonix chart: ended
    # before it, the director put up the cut in progress for a fraction of a second.)
    M.shot(s, marks, 'cpr', (cop_hands[0] + 0.9, 0.3, cop_hands[2] - 1.5), cop_hands, 34, 9.5, hand=True, focus=True, lead='l',
           end=((cop_eye[0] + 1.5, 0.75, cop_eye[2] - 1.0), cop_head, 30))
    # From the road beside the gurney as it starts to move, up to the open doors as it goes in.
    M.shot(s, marks, 'loading', w((2.7, 0.9, -5.9)), w((0, 1.1, -4.0)), 42, 8.7, hand=True, focus=True, lead='r',
           end=(w((1.7, 1.55, -5.9)), w((-0.05, 1.25, -1.9)), 36))
    return hand, cop_head


def innocent(s, earth, marks, V, M, site):
    """The cop and his partner on the road up beyond the drummer's head, from the flag innocent
    until the loading: a medic has the compressions (make_story_afterlife.crash_site,
    'relieved'), the cop is on his feet facing the drummer, and his partner holds a sheet off the
    dispatch up to him. They stand on the far side of the site from the cruiser and the
    ambulances, so the sheet's face is away from every headlight and beacon (lit from in front it
    burns out to white) and those are the lights behind the drummer when the camera finds them.
    Everything is placed in the cop's space: his feet at the origin, the drummer straight ahead."""
    stands = at(site, (-0.2, 0, 9.8))
    chest = at(site, (-0.55, 0.3, 2.2))                     # the drummer's, where the medic's hands are
    yaw = P.yaw_to(stands, chest)

    def w(p):
        return at(stands, rot(p, (0, yaw, 0)))
    g = P.between(s, earth, 'Innocent', 'innocent', 'loading', 0.0, stands)
    sheet = (0.26, 1.37, 0.52)                               # its middle: between them, at his chest
    partner = (0.4, 0, 1.02)
    partner_yaw = P.yaw_to(partner, (0, 0, 0))
    # The cop reads it, then (a one-shot on the flag, in the site's slow motion) looks up from it
    # at the drummer.
    read = P.turn_to((0, 0, 0), 0, sheet)
    looks_up = P.clip(V, 'CopLooksUp', 60, [P.ftrack('HeadTurn', [(0, read), (22, read), (42, 0.0), (60, 0.0)], 'SmoothStep'),
                                            P.ftrack('Nod', [(0, 17), (22, 17), (42, 3), (60, 3)], 'SmoothStep')])
    cop = P.actor(s, g, 'Cop', COP[0], COP[1], stands, yaw, motion=looks_up, once=True, Lean=3.0, Nod=17.0, HeadTurn=read,
                  LeftArm=P.arm(6, 8, 14), RightArm=P.arm(24, 10, 48, grip=0.3))
    cop.add({'Type': 'VenueStory', 'Flag': 'innocent', 'WhenSet': True, 'FadeSeconds': 0.0, 'Mode': 'Play', 'Speed': 1.0})
    # The partner holds it up by its bottom edge, the palm behind it, the face of it to the cop.
    held = P.to_figure(partner, partner_yaw, at(sheet, (0.0, -0.16, 0.03)))
    P.actor(s, g, 'Partner', PARTNER[0], PARTNER[1], w(partner), yaw + partner_yaw, Lean=4.0, Nod=4.0,
            LeftArm=P.arm(6, 8, 14), RightArm=P.arm(hand=held, pole=(1, -1, -0.2), fingers=(0, 1, 0), palm=(0, 0, 1), grip=0.5))
    A.model(s, g, 'Sheet', A.sign_face(V, 'Innocent'), w(sheet), (-10, yaw + 172, 0), (0.14, 0.11, 1),
            A.mat(V, 'Innocent', (0.8, 0.8, 0.8), glow=(1, 1, 1), power=0.12, both=True, rough=1.0), shadows=False)
    s.light('Sheet light', g, w((0.7, 1.9, -0.9)), 'Point', (1.0, 0.92, 0.8), 3.0, 3.0, fog=0.0)
    # Over his right shoulder onto the sheet; then back and across behind his head to his left
    # shoulder, the focus going out to the drummer under the medic's hands. While the highway is
    # up, the sheet and then the drummer are on the right of the picture and his head on the left
    # (the lens wide enough at the start for the whole sheet to fit there).
    M.shot(s, marks, 'innocent', w((0.44, 1.6, -0.42)), w(sheet), 34, 8.3, hand=True, focus=True, lead='r',
           end=(w((-0.5, 1.66, -1.2)), chest, 20))


# ---- the highway run and the inside of the ambulance: ambulance_run, defib, shock -----------
def braun(s, parent, part, pos=(0, 0, 0)):
    return A.model(s, parent, 'Braun ' + part, 'Assets/Models/Vehicles/Braun' + part + '.fbx', pos)


def braun_hanging(s, amb, V):
    for k, (part, pos) in enumerate((('IV', (-0.49, 2.49, -0.83)), ('Strap', (0.096, 2.45, 1.23)),
                                     ('Strap', (0.096, 2.45, -0.94)), ('Strap', (0.096, 2.45, -2.26)))):
        hook = P.looping(s, amb, part + ' hook', swing(V, k), pos, speed=0.85 + 0.11 * k)
        braun(s, hook, part)


def inside(s, amb, V):
    """Who and what is in the back of the ambulance on the run (amb: its space, facing +z)."""
    s.light('Ambulance inside', amb, (0, 2.45, -0.7), 'Point', (0.85, 0.92, 1.0), 4.0, 5.5)
    # The drummer on the cot, head to the front; the shock lifts them off it.
    chest = (-0.3, 1.29, -0.3)
    jolt = P.clip(V, 'ShockBody', 16, [P.track('Position', [(0, (0, 0, 0)), (2, (0, 0.17, 0)), (5, (0, 0.02, 0)), (8, (0, 0.05, 0)), (16, (0, 0, 0))], 'SmoothStep'),
                                       P.track('Rotation', [(0, (0, 0, 0)), (2, (-8, 0, 0)), (6, (2, 0, 0)), (16, (0, 0, 0))], 'SmoothStep')])
    lifted = P.play(s, amb, 'The shock', 'shock', jolt, chest)
    lying = s.entity('On the cot', lifted, (0, -1.29, -0.2))
    patient(s, lying, V, 'drummer', 1.29)
    # The paddles, and the medic who stands in the aisle with one in each fist (the people are
    # skinned, P.actor, their hands sent to what they hold). From the cut he rubs them together,
    # face to face, in small circles; parts them and holds them over the chest; and brings them
    # down onto it just before the shock (he comes off them with the recoil). It is all one clip a
    # hand and one a paddle, the length of the wait between the flags defib and shock.
    stands = (0.27, FLOOR, 0.0)
    rest = ((-0.1, 0.33, 0.2), (0.1, 0.33, 0.42))            # on the chest: left hand's, right hand's
    over = [at(p, (0.04, 0.3, 0)) for p in rest]            # held over it
    rub_at, gap, r, turn = (-0.02, 0.6, 0.46), 0.028, 0.035, 14
    rub_end, apart, down, total = 112, 132, 170, int(round(CHARGE * 30))
    hold = 0.12                                             # a palm above a paddle's middle, on its grip

    def circle(f, side):
        a = 2 * math.pi * f / turn + (math.pi if side else 0.0)
        return at(rub_at, (r * math.cos(a), r * math.sin(a), (gap if side else -gap)))

    def to_medic(p):
        return P.to_figure(stands, 270, at(chest, p))

    hands = []
    for side, name in enumerate(('Left', 'Right')):
        sign = 1 if side else -1                            # which way along z the grip sticks out, face to face
        frames = list(range(0, rub_end + 1, 2))
        where = [(f, circle(f, side)) for f in frames] + [(apart, over[side]), (down - 12, over[side]), (down, rest[side]), (total, rest[side])]
        faced = (sign * 90, 0, 0)
        turned = [(0, faced), (rub_end, faced), (apart, (0, 0, 0)), (total, (0, 0, 0))]
        clip = P.clip(V, 'Paddle' + name, total, [P.track('Position', where, 'Linear'), P.track('Rotation', turned, 'SmoothStep')])
        paddle = P.play(s, lifted, name + ' paddle', 'defib', clip)
        braun(s, paddle, 'Paddle', (0, 0.02, 0))
        grip = [(f, to_medic(at(p, (0, 0, sign * hold)))) for f, p in where[:len(frames)]] + [(f, to_medic(at(p, (0, hold, 0)))) for f, p in where[len(frames):]]
        palm = [(0, (-sign, 0, 0)), (rub_end, (-sign, 0, 0)), (apart, (0, -1, 0)), (total, (0, -1, 0))]
        hands += [P.ftrack(name + 'Arm.Hand', grip, 'Linear'), P.ftrack(name + 'Arm.Palm', palm, 'SmoothStep')]
    hands += [P.ftrack('Bow', [(0, 12), (rub_end, 12), (apart, 16), (down - 12, 16), (down, 24), (total, 24)], 'SmoothStep'),
              P.ftrack('Nod', [(0, 22), (rub_end, 22), (apart, 16), (total, 16)], 'SmoothStep')]
    charging = P.clip(V, 'PaddlesRub', total, hands)
    recoil = P.clip(V, 'ShockRecoil', 24, [P.track('Rotation', [(0, (0, 0, 0)), (3, (-9, 0, 0)), (24, (0, 0, 0))], 'SmoothStep')])
    first = [to_medic(at(circle(0, side), (0, 0, (1 if side else -1) * hold))) for side in (0, 1)]
    medic = P.actor(s, P.play(s, amb, 'Medic recoils', 'shock', recoil, stands, (0, 270, 0)), 'Medic with the paddles', MEDIC[0], MEDIC[1], (0, 0, 0), 0,
                    motion=charging, once=True, Bow=12.0, Lean=14.0, Nod=22.0, LeftLeg=P.leg(9), RightLeg=P.leg(9),
                    LeftArm=P.arm(hand=first[0], pole=(-1, -0.3, -0.4), palm=(1, 0, 0), grip=0.9), RightArm=P.arm(hand=first[1], pole=(1, -0.3, -0.4), palm=(-1, 0, 0), grip=0.9))
    # (His clip is a one-shot of his own, on the flag defib: the recoil above him is the shock's.)
    medic.add({'Type': 'VenueStory', 'Flag': 'defib', 'WhenSet': True, 'FadeSeconds': 0.0, 'Mode': 'Play', 'Speed': 1.0})
    # Another on the seat at the drummer's head, squeezing a bag over their face.
    sits = (-0.3, FLOOR, 1.12)
    mask = (-0.3, 1.63, 0.24)
    held = P.to_figure(sits, 180, mask)
    squeeze = P.clip(V, 'BagSqueeze', 90, [P.ftrack('RightArm.Grip', [(0, 0.3), (12, 0.85), (30, 0.3), (90, 0.3)], 'SmoothStep'),
                                           P.ftrack('Lean', [(0, 10), (14, 13), (40, 10), (90, 10)], 'SmoothStep')])
    P.actor(s, amb, 'Medic at the head', MEDIC[0], MEDIC[1], sits, 180, 'Seated', SeatHeight=0.5, Bow=30.0, Lean=10.0, Nod=22.0, motion=squeeze,
            LeftArm=P.arm(hand=(held[0] - 0.07, held[1] - 0.04, held[2] + 0.02), pole=(-1, -0.3, -0.2), palm=(0.3, -1, 0), grip=0.5),
            RightArm=P.arm(hand=(held[0] + 0.07, held[1] + 0.06, held[2] - 0.12), pole=(1, -0.3, -0.2), palm=(-0.4, -1, 0), grip=0.3))
    s.box('Mask', amb, mask, (0.11, 0.06, 0.13), (0.75, 0.85, 0.9), rough=0.4, shadows=False)
    s.box('Bag', amb, at(mask, (0, 0.07, 0.14)), (0.11, 0.11, 0.2), (0.25, 0.45, 0.8), rough=0.6, shape='Sphere', shadows=False)
    # The cop on the bench, bent over with his elbows on his knees and his face in his hands: he
    # can't watch. After the shock, sat up, his eyes on the monitor.
    seat = (0.84, FLOOR, -1.45)
    P.actor(s, P.between(s, amb, 'Cop waits', None, 'shock', 0.0, seat), 'Cop', COP[0], COP[1], seat, 270, 'Seated', SeatHeight=0.55, **COP_CANT_WATCH)
    P.actor(s, P.between(s, amb, 'Cop hopes', 'shock', None, 0.0, seat), 'Cop', COP[0], COP[1], seat, 270, 'Seated', SeatHeight=0.55, Bow=6.0, Lean=2.0, Nod=-12.0,
            HeadTurn=P.turn_to(seat, 270, MONITOR, 60.0), Turn=P.turn_to(seat, 270, MONITOR, 20.0),
            LeftArm=P.arm(hand=(-0.14, 0.6, 0.36), pole=(-1, 0, -0.5), palm=(0, -1, 0), grip=0.3), RightArm=P.arm(52, 4, 105, grip=0.9))
    # The flash: a light and a glare that are far overhead except for the three frames of the shock.
    flash = P.clip(V, 'ShockFlash', 6, [P.track('Position', [(0, (0, 0, 0)), (1, (0, -60, 0)), (4, (0, -60, 0)), (5, (0, 0, 0)), (6, (0, 0, 0))])])
    lit = P.play(s, amb, 'Flash', 'shock', flash, at(chest, (0, 60.6, 0)))
    s.light('Shock', lit, (0, 0, 0), 'Point', (0.8, 0.9, 1.0), 140.0, 6)
    A.glow_card(s, lit, V, 'Shock glare', (0, -0.3, 0), 0.9, (0.8, 0.9, 1.0), 5.0, (90, 0, 0))
    # The monitor: a flat line until the shock; after it a spike on every beat of the song.
    live = P.between(s, amb, 'Monitor beating', 'shock', None, 0.0)
    # The waveform is authored in vehicle space. Move it through the CRT face on its normal.
    normal = (math.sin(math.radians(MONITOR_YAW)), 0, math.cos(math.radians(MONITOR_YAW)))
    pulse = braun(s, live, 'Pulse', tuple(-0.025 * n for n in normal))
    pulse.add({'Type': 'VenueBeat', 'Offset': [0.029 * n for n in normal], 'Every': 1.0,
               'Phase': 0.0, 'Sway': False, 'Sharp': True})
    braun_hanging(s, amb, V)
    loose = [(8, (-0.78, 2.1, -1.9), 0.3, 'mask'), (9, (-0.78, 2.1, -0.75), 0.22, 'steth'),
             (10, (-0.78, 2.1, 1.15), 0.25, 'cuff'), (11, (0.62, 2.48, -1.9), 0.5, 'shears'),
             (12, (0.0, 2.48, 1.62), 0.12, 'clip'), (13, (0.55, 2.48, 1.62), 0.2, 'tree'),
             (14, (1.04, 2.0, -2.2), 0.28, 'buckle'), (15, (1.04, 2.0, -1.0), 0.28, 'buckle'),
             (16, (1.04, 2.0, 0.1), 0.28, 'buckle'), (17, (0.75, 2.48, -2.2), 0.62, 'tags'),
             (19, (0.45, 2.48, -0.4), 0.2, 'mask')]
    for k, pivot, length, kind in loose:
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
    A.plant_roadside(s, trees, V, A.roadside_spots(-288, 288, 19, 72, 22, 5, period=96.0, y=-0.12))
    rail = A.guardrail(V, 96.0)
    for k in range(-3, 3):
        A.model(s, trees, 'Guardrail', rail, (15.4, 0, k * 96), shadows=False)
        A.model(s, trees, 'Guardrail', rail, (-15.4, 0, k * 96 + 96), (0, 180, 0), shadows=False)
    # Traffic pulled over to let them through.
    aside = scroll('Aside', 192.0)
    for k in (-1, 0, 1):
        for z, kind, x in ((30, 'Caravan', 12.7), (118, 'Civic', 12.9), (160, 'C10', -12.8)):
            car = s.entity('Pulled over', aside, (x, 0, k * 192 + z), (0, 0 if x > 0 else 180, 0))
            A.vehicle(s, car, kind)
            A.vehicle_lamps(s, car, V, kind, head=0.8, tail=1.6, hazard=True)
    A.particles(s, g, 'Road grit', at(R, (0, 1.8, 34)), (-90, 0, 0), Shape='Box', BoxSize=[30, 4, 6], Lifetime=[0.9, 1.5], Speed=[44, 52], Size=[0.02, 0.06],
                StartColor=[0.9, 0.8, 0.65], StartColor2=[0.6, 0.6, 0.65], EndColor=[0.5, 0.5, 0.5], StartAlpha=0.6, EndAlpha=0.0, Intensity=1.8, Gravity=0.0, Drag=0.0,
                NoiseStrength=0.3, Blend='Additive', EmissionRate=90, MaxParticles=180, Alignment='Stretched', StretchFactor=0.07, FadeIn=0.1)

    # The ambulance: it stands (rocking on its springs) and the road goes by.
    rock = P.clip(V, 'AmbulanceRock', 96, [P.track('Position', [(0, (0, 0, 0)), (24, (0.1, 0.02, 0)), (48, (0, 0, 0)), (72, (-0.1, 0.02, 0)), (96, (0, 0, 0))], 'SmoothStep'),
                                           P.track('Rotation', [(0, (0, 0, 0)), (24, (0.3, 0, -0.9)), (48, (-0.3, 0, 0)), (72, (0.3, 0, 0.9)), (96, (0, 0, 0))], 'SmoothStep')])
    amb_at = at(R, (AMB_X, 0, 0))
    amb = P.looping(s, g, 'Ambulance', rock, amb_at)
    for part in ('Body', 'Doors', 'Cot'):
        braun(s, amb, part)
    beacon(s, amb, V, (0, 2.11, 1.97), 70.0, 95.0, 12.0, housings=False)
    for x in (-0.836, 0.836):
        A.glow_card(s, amb, V, 'Headlight glare', (x, 1.035, 3.65), 0.7, (1.0, 0.95, 0.8), 3.0)
    A.headlights(s, amb, 0.836, 1.035, 3.65, 380.0, 45, inner=14, outer=34, name='Ambulance headlight')
    A.exhaust(s, amb, V, (0.85, 0.4, -3.15), size=1.3)
    inside(s, amb, V)

    # The escort: cruisers ahead, alongside and behind (the two on the outside lane Trail Dusters),
    # each weaving in its lane. From the helicopter a cruiser's tail could be its nose, so each
    # says which way it is going: the wheels turn, the driver has the window down and an arm
    # out on the door, and its exhaust trails behind it (the ambulance's too).
    escort = ((AMB_X, 17.0, True), (-2.7, 11.0, True), (-2.7, -2.0, False), (8.1, 4.0, False), (AMB_X, -12.5, True), (-2.7, -16.0, True), (8.1, -11.0, False))
    for i, (x, z, full) in enumerate(escort):
        frames = 150 + 40 * (i % 3)
        side = 1 if i % 2 else -1
        weave = P.clip(V, f'EscortWeave{i % 6}', frames, [P.track('Position', [(0, (0, 0, 0)), (frames // 4, (side * 0.6, 0, 1.3)), (frames // 2, (0, 0, -0.7)), (3 * frames // 4, (-side * 0.5, 0, 0.9)), (frames, (0, 0, 0))], 'SmoothStep'),
                                                         P.track('Rotation', [(0, (0, 0, 0)), (frames // 8, (0, side * 5, 0)), (3 * frames // 8, (0, -side * 6, 0)), (5 * frames // 8, (0, side * 4, 0)), (frames, (0, 0, 0))], 'SmoothStep')])
        car = P.looping(s, g, f'Escort {i}', weave, at(R, (x, 0, z)))
        kind = 'TrailDuster' if x > 5 else None
        M.rolling(s, car, V, kind)
        M.driver(s, car, kind, LeftArm=M.window_arm(kind))
        A.exhaust(s, car, V, A.tailpipe(kind))
        if kind:
            (hx, hy, hz), tail = A.lamp(kind, 'Headlamp'), A.lamp(kind, 'TailLamp')
        else:
            (hx, hy, hz), tail = A.PATROL_HEADLAMP, A.PATROL_TAIL_LAMP
        for dx in (-hx, hx):
            A.glow_card(s, car, V, 'Headlight glare', (dx, hy, hz + 0.05), 0.45, (1.0, 0.95, 0.8), 0.8)
            A.glow_card(s, car, V, 'Tail lamp glare', (dx * tail[0] / hx, tail[1], tail[2] - 0.03), 0.28, (1.0, 0.05, 0.05), 0.8, (0, 180, 0))
        if full:
            A.headlights(s, car, hx, hy, hz + 0.15, 260.0, 32)
        M.beacons(s, car, V, 110.0 if full else 0.0, 150.0, 22.0, 1.0 + 0.1 * i, glare=(0.5, 1.2), kind=kind)
    # The run is seen from a helicopter following it: astern and off to the left, high, an operator
    # in the door on a long lens. The whole escort first, then the lens goes in on the ambulance as
    # the helicopter gains on it. Aimed at the ambulance throughout: while the highway is up it is
    # on the right of the picture, the cars ahead of it above it toward the middle, and the lens
    # stops at 11 degrees so the operator's hunting doesn't carry it onto the highway.
    heli = at(R, (-30.0, 34.0, -44.0))
    M.shot(s, marks, 'ambulance_run', heli, at(R, (AMB_X, 1.5, 0.5)), 26, 7.3, heli=True, lead='r',
           via=[(at(heli, (3.0, -1.0, 6.0)), at(R, (AMB_X, 1.5, 0.5)), 14)], end=(at(heli, (8.0, -3.0, 14.0)), at(R, (AMB_X, 1.5, 0.5)), 11))
    # The helicopter itself, just above and behind that camera, so its searchlight on the
    # ambulance's roof comes from where the picture is taken. (Until the cut to the inside: nothing
    # here casts a shadow but the sun, so the light would be on the cot.)
    copter_at = at(heli, (-2.5, 5.0, -9.0))
    M.police_helicopter(s, P.between(s, g, 'Helicopter', None, 'defib', 0.0, copter_at), V, 'AS350', copter_at, (10, 34, 4), at(amb_at, (0, 2, 0)), 16000.0, 100,
                        wander=1.2, inner=3, outer=6)
    # Inside, from up by the bulkhead over the medic at the head: aimed at the drummer's chest under
    # the paddles, which the highway's lead keeps on the right of the picture with the monitor at
    # its edge, the cop on the bench in the middle and the escort's lights in the back windows
    # beyond him. Handheld, on the road.
    M.shot(s, marks, 'defib', at(amb_at, (0.35, 2.5, 1.25)), at(amb_at, (-0.3, 1.29, -0.3)), 70, 9.9, hand=True, ride=1.2, lead='r',
           end=(at(amb_at, (0.3, 2.25, 0.8)), at(amb_at, (-0.32, 1.35, -0.25)), 60))


# ---- the corridor: gurney -------------------------------------------------------------------
def rush(s, root, marks, V, M):
    g = place_at(s, root, 'The hospital corridor', 'gurney', 'surgery', H)
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
    for i, (who, x) in enumerate((('drummer', 0.0), ('guitar', 0.42), ('bass', -0.4), ('vocals', 0.36))):
        cart = P.looping(s, g, f'Gurney: {who}', rattle[i], at(H, (x, 0, -3.5 * i)))
        A.model(s, cart, 'Top', gurney(V), (0, 0, 0), (0, 180, 0))
        A.model(s, cart, 'Legs', gurney_legs(V), (0, 0.78, 0))
        patient(s, cart, V, who, 0.92, -1)
        dangle(s, cart, V, 'IV bag', (-0.33, 1.95, -0.85), 0.1, 'iv', i)
        runner(s, cart, V, 'Medic pushing', MEDIC, (0, 0, -1.45), 0, i, arms=(), **pushing())
        if i:
            dangle(s, cart, V, 'Chart', (0.31, 0.98, 0.3), 0.04, 'clip', i + 2)
    # The cop runs beside the drummer, his eyes on them; a nurse on the other side holds the drip up.
    runner(s, g, V, 'Cop', COP, at(H, (0.82, 0, -0.55)), 0, 1, Nod=10.0, HeadTurn=-38.0, Turn=-10.0)
    # (The nurse runs level with the foot, near the lens: further up the gurney she was in the
    # middle of the picture, under the highway.)
    runner(s, g, V, 'Nurse with the drip', NURSE, at(H, (-1.0, 0, 0.3)), 0, 2, arms=('Left',), HeadTurn=34.0,
           RightArm=P.arm(hand=(0.44, 1.86, 0.05), pole=(1, 0, 0.4), grip=0.8))
    M.shot(s, marks, 'gurney', at(H, (0.28, 1.7, 1.12)), at(H, (0.0, 1.05, -0.72)), 56, 9.6, hand=True, ride=0.9, lead='l',
           end=(at(H, (0.44, 1.92, 1.36)), at(H, (-0.04, 1.05, -0.8)), 62))

# ---- the operating theatre: surgery ---------------------------------------------------------
ROOM = (-3.6, 3.6, -3.4, 3.6, 3.0)    # the drummer's theatre: x from and to, z from and to, its height
NEXT = 6.6                             # the next theatre's table, along x (the glass between is at x 3.6)
TABLE = 0.85                           # an operating table's top above the floor
GLASS = (-2.2, 2.2, 1.0, 2.3)          # the window between the theatres: z from and to, y from and to
DOOR = (0.8, 2.1)                      # a leaf of the doors (at the head end, -z): its width and height
SCRUBS = (0.42, 0.95, 0.88)            # theatre green: what a staff atlas's cloth is drawn in


def scrubs(venue, body, variant):
    """body's PolygonTown atlas with everything but its skin in theatre green (the hair too: a
    cap), for the theatre's staff. The skin is the colours the head and the arms both use (the
    crowd's pieces of the body have the character's UVs), so a hood and sleeves of one cloth keep
    their colour too: Son_01's are blue. Drawn with ffmpeg the first time and kept."""
    name = f'Scrubs_{body}_{variant}.png'
    path = os.path.join(A.ROOT, 'Assets', 'Venues', venue, 'Textures', name)
    if not os.path.isfile(path):
        import subprocess
        source = os.path.join(A.ROOT, 'Assets', 'Models', 'Venue', f'PolygonTown_{variant}.png')
        size = 256
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', source, '-vf', f'scale={size}:{size}:flags=neighbor', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                             check=True, capture_output=True).stdout

        def colours(piece):
            _, uvs, faces = P._read(body, piece, False)
            found = set()
            for f in faces:
                u = sum(uvs[t - 1][0] for _, t in f) / len(f)
                v = sum(uvs[t - 1][1] for _, t in f) / len(f)
                x, y = min(size - 1, max(0, int(u * size))), min(size - 1, max(0, int((1.0 - v) * size)))
                found.add(tuple(raw[(y * size + x) * 3:(y * size + x) * 3 + 3]))
            return found
        skin = colours('Head') & (colours('ArmL') | colours('ArmR'))
        near = '+'.join(f"lt(abs(r(X\\,Y)-{r})+abs(g(X\\,Y)-{g})+abs(b(X\\,Y)-{b})\\,14)" for r, g, b in sorted(skin)) or '0'
        grey = "(40+0.75*(0.3*r(X\\,Y)+0.59*g(X\\,Y)+0.11*b(X\\,Y)))"
        geq = ':'.join(f"{c}='if({near}\\,{c}(X\\,Y)\\,{k}*{grey})'" for c, k in zip('rgb', SCRUBS))
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', source, '-vf', 'format=gbrp,geq=' + geq, '-frames:v', '1', path], check=True)
    return f'Assets/Venues/{venue}/Textures/{name}'


def staff(s, parent, V, name, look, pos, yaw, **kw):
    """One of the theatre's team: a skinned figure (P.actor) in scrubs."""
    e = P.actor(s, parent, name, look[0], look[1], pos, yaw, **kw)
    for c in e.components:
        if c.get('Type') == 'VenueFigure':
            c['Atlas'] = scrubs(V, look[0], look[1])
    return e


def theatre_walls(venue):
    """The walls of two theatres side by side and of the lobby outside the first one's doors, all
    in white (the material tints them): closed all round, to keep heaven's sun out. The first
    theatre's floor is the origin; the doors' opening is in its -z wall, the glass in its +x wall."""
    x0, x1, z0, z1, high = ROOM
    far = NEXT + 3.0

    def build(m):
        mid_x, wide = (x0 + far) / 2, far - x0 + 0.2
        mid_z, deep = (z0 + z1) / 2, z1 - z0
        m.box((x0 - 0.05, high / 2, mid_z), (0.1, high, deep + 0.2), 'white')
        m.box((far + 0.05, high / 2, mid_z), (0.1, high, deep + 0.2), 'white')
        m.box((mid_x, high / 2, z1 + 0.05), (wide, high, 0.1), 'white')
        # The head wall, round the doors.
        m.box(((x0 - DOOR[0]) / 2, high / 2, z0 - 0.05), (-DOOR[0] - x0, high, 0.1), 'white')
        m.box(((far + DOOR[0]) / 2, high / 2, z0 - 0.05), (far - DOOR[0], high, 0.1), 'white')
        m.box((0, (high + DOOR[1]) / 2, z0 - 0.05), (2 * DOOR[0], high - DOOR[1], 0.1), 'white')
        # The wall between the theatres, round its glass.
        g0, g1, y0, y1 = GLASS
        m.box((x1 + 0.05, y0 / 2, mid_z), (0.1, y0, deep), 'white')
        m.box((x1 + 0.05, (high + y1) / 2, mid_z), (0.1, high - y1, deep), 'white')
        m.box((x1 + 0.05, (y0 + y1) / 2, (z0 + g0) / 2), (0.1, y1 - y0, g0 - z0), 'white')
        m.box((x1 + 0.05, (y0 + y1) / 2, (z1 + g1) / 2), (0.1, y1 - y0, z1 - g1), 'white')
        # The lobby.
        for x in (-1.65, 1.65):
            m.box((x, high / 2, z0 - 0.8), (0.1, high, 1.4), 'white')
        m.box((0, high / 2, z0 - 1.55), (3.4, high, 0.1), 'white')
    return A.prop(venue, 'TheatreWalls', build)


def theatre_shell(venue):
    """What goes with theatre_walls in its own colours: the floor, the ceiling, the doors (each
    leaf with a tall window), the frame of the glass, the scrub-up trough and the clock."""
    x0, x1, z0, z1, high = ROOM
    far = NEXT + 3.0

    def build(m):
        mid_x, wide = (x0 + far) / 2, far - x0 + 0.2
        m.box((mid_x, -0.05, (z0 + z1) / 2 - 0.8), (wide, 0.1, z1 - z0 + 1.8), 'marble_shade')
        m.box((mid_x, high + 0.05, (z0 + z1) / 2 - 0.8), (wide, 0.1, z1 - z0 + 1.8), 'white')
        # A band of darker floor round each table.
        for x in (0.0, NEXT):
            m.box((x, 0.003, 0), (2.6, 0.004, 3.6), 'steel')
            m.box((x, 0.005, 0), (2.5, 0.004, 3.5), 'marble_shade')
        # The doors: a leaf each side of the middle, its window from 1.0 to 1.9 up.
        w, h = DOOR
        for side in (-1, 1):
            for a, b, y, tall in ((0.0, 0.24, h / 2, h), (0.56, w, h / 2, h), (0.24, 0.56, 0.5, 1.0), (0.24, 0.56, (1.9 + h) / 2, h - 1.9)):
                m.box((side * (a + b) / 2, y, z0 - 0.02), (b - a - 0.004, tall, 0.05), 'steel')
            m.box((side * 0.4, 0.2, z0 + 0.008), (0.7, 0.36, 0.006), 'chrome')
            m.box((side * 0.09, 1.05, z0 + 0.02), (0.04, 0.3, 0.03), 'chrome')
        m.box((0, h + 0.04, z0 + 0.01), (2 * w + 0.16, 0.08, 0.06), 'steel_dark')
        for side in (-1, 1):
            m.box((side * (w + 0.04), h / 2, z0 + 0.01), (0.08, h, 0.06), 'steel_dark')
        # The frame of the glass.
        g0, g1, y0, y1 = GLASS
        for y in (y0, y1):
            m.box((x1 + 0.05, y, (g0 + g1) / 2), (0.16, 0.06, g1 - g0 + 0.06), 'steel')
        for z in (g0, (g0 + g1) / 2, g1):
            m.box((x1 + 0.05, (y0 + y1) / 2, z), (0.16, y1 - y0, 0.06), 'steel')
        # A scrub trough on the far wall and a clock on the head wall.
        m.box((x0 + 0.3, 0.95, 2.0), (0.5, 0.3, 1.6), 'steel')
        m.box((x0 + 0.3, 1.09, 2.0), (0.4, 0.04, 1.5), 'steel_dark')
        for z in (1.5, 2.5):
            m.tube([(x0 + 0.06, 1.1, z), (x0 + 0.06, 1.45, z), (x0 + 0.3, 1.45, z), (x0 + 0.3, 1.36, z)], 0.015, 'chrome', 5)
        m.box((-2.2, 2.45, z0 + 0.02), (0.42, 0.42, 0.03), 'black')
        m.box((-2.2, 2.45, z0 + 0.04), (0.36, 0.36, 0.02), 'white')
        m.box((-2.2, 2.51, z0 + 0.053), (0.015, 0.13, 0.006), 'black')
        m.box((-2.15, 2.45, z0 + 0.053), (0.1, 0.015, 0.006), 'black')
    return A.prop(venue, 'TheatreShell', build)


def op_table(venue):
    """An operating table along z, the head at -z: a pedestal and a narrow padded top at TABLE."""
    def build(m):
        m.box((0, 0.04, 0.1), (0.62, 0.08, 1.0), 'steel_dark')
        m.box((0, 0.42, 0.1), (0.26, 0.7, 0.36), 'steel')
        m.box((0, TABLE - 0.07, 0), (0.56, 0.05, 2.0), 'steel')
        m.box((0, TABLE - 0.025, 0.1), (0.54, 0.05, 1.76), 'black')
        m.box((0, TABLE - 0.02, -0.9), (0.3, 0.06, 0.26), 'black')
        for x in (-0.29, 0.29):
            m.tube([(x, TABLE - 0.07, -0.7), (x, TABLE - 0.07, 0.9)], 0.012, 'chrome', 5)
    return A.prop(venue, 'OpTable', build)


LAMPS = ((-0.28, 2.05, -0.42, 0.36), (0.44, 2.22, 0.58, 0.3))      # an operating lamp's two heads: x, the face's y, z, its radius


def op_lamp(venue):
    """The pair of lamps over a table, on arms from one mount in the ceiling (the origin is the
    floor under the table's middle). Their glowing faces are LAMPS (the generator puts them there)."""
    def build(m):
        high = ROOM[4]
        m.box((0, high - 0.08, 0.1), (0.34, 0.16, 0.34), 'white')
        m.tube([(0, high - 0.1, 0.1), (0, high - 0.45, 0.1)], 0.045, 'white', 8)
        for k, (x, y, z, r) in enumerate(LAMPS):
            elbow = (x * 2.2, high - 0.42 - 0.08 * k, z * 1.3 + 0.1)
            m.tube([(0, high - 0.42 - 0.08 * k, 0.1), elbow, (x, y + 0.3, z), (x, y + 0.1, z)], 0.028, 'white', 6)
            m.lathe((x, y, z), [(r * 0.96, 0.0), (r, 0.03), (r * 0.8, 0.11), (0.1, 0.14), (0.0, 0.14)], 'white', 20, 'y')
            m.tube([(x + r, y + 0.03, z - 0.05), (x + r + 0.1, y + 0.03, z - 0.05), (x + r + 0.1, y + 0.03, z + 0.05), (x + r, y + 0.03, z + 0.05)], 0.01, 'chrome', 4)
    return A.prop(venue, 'OpLamp', build)


def theatre_kit(venue):
    """What stands round the drummer's table (the origin is the floor under its middle, the head
    at -z): the anaesthetic machine and a stool at the head, a drip stand, the instrument stand
    over the legs, a back table, a kick bucket, the monitor's trolley and a light box of films."""
    def build(m):
        # The anaesthetic machine, right of the head: a cart, its monitor, bottles on the back.
        ax, az = 1.0, -1.55
        m.box((ax, 0.5, az), (0.6, 0.8, 0.55), 'white')
        m.box((ax, 0.06, az), (0.66, 0.08, 0.6), 'steel_dark')
        for y in (0.3, 0.5, 0.7):
            m.box((ax, y, az + 0.28), (0.5, 0.16, 0.01), 'marble_shade')
            m.box((ax, y + 0.03, az + 0.29), (0.14, 0.02, 0.01), 'chrome')
        m.box((ax, 0.92, az), (0.62, 0.04, 0.57), 'steel')
        m.box((ax, 1.25, az - 0.12), (0.56, 0.6, 0.26), 'white')
        m.box((ax - 0.1, 1.33, az + 0.012), (0.26, 0.2, 0.01), 'glass')
        for k in range(3):
            m.tube([(ax + 0.14 + 0.05 * k, 1.12, az + 0.02), (ax + 0.14 + 0.05 * k, 1.46, az + 0.02)], 0.014, ('sky', 'hivis', 'chrome')[k], 5)
        for k, ink in enumerate(('sign_green', 'sky')):
            m.tube([(ax - 0.12 + 0.24 * k, 0.12, az - 0.36), (ax - 0.12 + 0.24 * k, 0.95, az - 0.36)], 0.07, ink, 8)
        m.tube([(ax - 0.28, 1.0, az + 0.2), (ax - 0.5, 1.2, az + 0.5), (ax - 0.75, 1.05, az + 0.62)], 0.014, 'sky', 5)
        # A drip stand, left of the head.
        dx, dz = -0.72, -1.25
        m.tube([(dx, 0.03, dz), (dx, 2.0, dz)], 0.014, 'chrome', 5)
        m.tube([(dx - 0.13, 1.99, dz), (dx + 0.13, 1.99, dz)], 0.01, 'chrome', 4)
        for a in range(5):
            t = 2 * math.pi * a / 5
            m.tube([(dx, 0.05, dz), (dx + 0.26 * math.cos(t), 0.03, dz + 0.26 * math.sin(t))], 0.012, 'steel_dark', 4)
        # The instrument stand: a tray over the patient's shins on one leg.
        m.tube([(0.98, 0.03, 0.9), (0.98, TABLE + 0.42, 0.9), (0.72, TABLE + 0.42, 0.9)], 0.018, 'chrome', 5)
        m.box((0.98, 0.03, 0.9), (0.5, 0.04, 0.5), 'steel_dark')
        m.box((0.36, TABLE + 0.43, 0.9), (0.74, 0.02, 0.44), 'chrome')
        m.box((0.36, TABLE + 0.445, 0.9), (0.68, 0.012, 0.38), 'sign_green')
        for k in range(7):
            m.box((0.1 + 0.075 * k, TABLE + 0.456, 0.9 + 0.03 * (k % 3 - 1)), (0.016, 0.008, 0.16 + 0.02 * (k % 2)), 'chrome', euler=(0, 6 * (k % 3 - 1), 0))
        # A back table along the far wall, draped, with basins.
        m.box((-2.7, 0.45, -0.6), (0.7, 0.9, 1.7), 'sign_green')
        m.box((-2.7, 0.91, -0.6), (0.74, 0.02, 1.74), 'sign_green')
        for z, r in ((-1.1, 0.16), (-0.6, 0.12), (-0.15, 0.1)):
            m.lathe((-2.7, 0.92, z), [(r * 0.7, 0.0), (r, 0.09), (r * 0.92, 0.09), (r * 0.64, 0.01)], 'chrome', 10, 'y')
        # A kick bucket and the surgeon's stool.
        m.lathe((-1.0, 0.0, 0.75), [(0.0, 0.02), (0.15, 0.02), (0.18, 0.3), (0.16, 0.3), (0.13, 0.04)], 'steel', 10, 'y')
        m.lathe((0.25, 0.0, -2.2), [(0.0, 0.5), (0.17, 0.5), (0.17, 0.56), (0.0, 0.56)], 'black', 10, 'y')
        m.tube([(0.25, 0.02, -2.2), (0.25, 0.5, -2.2)], 0.02, 'chrome', 5)
        # The monitor's trolley, left of the head: the screen is the generator's (monitor()).
        mx, mz = -1.45, -1.7
        m.tube([(mx, 0.03, mz), (mx, 1.45, mz)], 0.02, 'chrome', 5)
        m.box((mx, 0.03, mz), (0.44, 0.04, 0.44), 'steel_dark')
        m.box((mx, 1.62, mz - 0.07), (0.6, 0.46, 0.12), 'steel_dark')
        m.box((mx, 1.1, mz), (0.4, 0.03, 0.34), 'steel')
        # A light box on the head wall with two films up.
        m.box((2.1, 1.7, ROOM[2] + 0.03), (1.0, 0.56, 0.05), 'steel_dark')
    return A.prop(venue, 'TheatreKit', build)


def on_table(s, parent, V, who):
    """A band member on an operating table under parent (the floor under the table's middle; the
    head at -z), draped in green from the collar down, a tube taped at the mouth."""
    P.lie(s, parent, who.capitalize(), body_of(V, who), (0, TABLE, 0.88), 0)
    green = A.mat(V, 'Palette', (0.2, 0.8, 0.62), rough=1.0)
    A.model(s, parent, 'Drape', blanket(V), (0, TABLE, 0.36), (0, 0, 0), (1.2, 0.8, 1.55), green)
    s.box('Drape, chest', parent, (0, TABLE + 0.16, -0.37), (0.74, 0.3, 0.5), (0.09, 0.5, 0.57), rough=1.0)
    s.box('Cap', parent, (0, TABLE + 0.19, -0.9), (0.22, 0.2, 0.17), (0.5, 0.8, 0.78), rough=1.0, shape='Sphere', shadows=False)


def operating(venue, k, hands):
    """A surgeon's small movements over the table: the hands (left, right: the points they rest
    at, in the figure's space) working a few centimetres about them, the head following."""
    frames = (50, 64, 58)[k % 3]
    tracks = []
    for side, (x, y, z) in zip(('Left', 'Right'), hands):
        sign = -1 if side == 'Left' else 1
        keys = [(0, (x, y, z)), (frames // 4, (x + 0.02 * sign, y + 0.015, z + 0.03)), (frames // 2, (x - 0.015 * sign, y, z - 0.02)),
                (3 * frames // 4, (x + 0.01, y + 0.025, z + 0.015)), (frames, (x, y, z))]
        tracks.append(P.ftrack(f'{side}Arm.Hand', keys, 'SmoothStep'))
    tracks.append(P.ftrack('Nod', [(0, 24), (frames // 2, 28), (frames, 24)], 'SmoothStep'))
    return P.clip(venue, f'Operating{k % 3}', frames, tracks)


def surgeon(s, parent, V, name, look, pos, yaw, work, k, **pose):
    """One of the team stood at the table, both hands down at work (a point in parent's space)."""
    local = P.to_figure(pos, yaw, work)
    hands = [(local[0] + dx, local[1], local[2]) for dx in (-0.07, 0.07)]
    fields = dict(Bow=20.0, Lean=8.0, Nod=24.0, LeftLeg=P.leg(6), RightLeg=P.leg(6),
                  LeftArm=P.arm(hand=hands[0], pole=(-1, -0.5, -0.3), fingers=(0.2, -0.3, 1), palm=(0, -1, 0), grip=0.5),
                  RightArm=P.arm(hand=hands[1], pole=(1, -0.5, -0.3), fingers=(-0.2, -0.3, 1), palm=(0, -1, 0), grip=0.5))
    fields.update(pose)
    return staff(s, parent, V, name, look, pos, yaw, motion=operating(V, k, hands), speed=0.8 + 0.13 * k, **fields)


def surgery(s, root, marks, V, M):
    x0, x1, z0, z1, high = ROOM
    g = s.entity('Theatre', place_at(s, root, 'The operating theatre', 'surgery', 'resurrection', O), O)

    def out(p):
        return at(O, p)
    A.model(s, g, 'Walls', theatre_walls(V), material=A.mat(V, 'Palette', (0.56, 0.78, 0.72), rough=0.6))
    A.model(s, g, 'Room', theatre_shell(V), material=A.mat(V, 'Palette', rough=0.7))
    A.model(s, g, 'Kit', theatre_kit(V), material=A.mat(V, 'Palette', rough=0.6))
    M_see(s.box('Glass', g, (x1 + 0.05, (GLASS[2] + GLASS[3]) / 2, 0), (0.02, GLASS[3] - GLASS[2], GLASS[1] - GLASS[0]), (0.6, 0.8, 0.85), rough=0.1, shadows=False), 0.1)
    glow = A.mat(V, 'Palette', (1, 1, 1), glow=(0.9, 0.98, 1.0), power=2.2, glow_tex=False)
    # The room's own light is low and cool; the lamps make a pool of the table (no light here
    # casts a shadow: a pool is all a lamp can be).
    for x in (0.0, NEXT):
        for z in (-2.2, 2.4):
            for dx in (-1.9, 1.9):
                A.model(s, g, 'Ceiling panel', panel(V), (x + dx, high - 0.01, z), material=glow, shadows=False)
        s.light('Theatre light', g, (x, 2.6, 2.3), 'Point', (0.8, 0.95, 1.0), 5.0, 7, fog=0.0)
        s.light('Theatre light', g, (x, 2.6, -2.3), 'Point', (0.8, 0.95, 1.0), 5.0, 7, fog=0.0)
        table = s.entity('Table', g, (x, 0, 0))
        A.model(s, table, 'Table', op_table(V), material=A.mat(V, 'Palette', rough=0.5))
        A.model(s, table, 'Lamps', op_lamp(V), material=A.mat(V, 'Palette', rough=0.4))
        for lx, ly, lz, r in LAMPS:
            s.box('Lamp face', table, (lx, ly - 0.004, lz), (1.84 * r, 0.008, 1.84 * r), (1, 1, 1), emissive=(1.0, 0.97, 0.9), emissive_intensity=7.0, shadows=False, shape='Cylinder')
            s.light('Lamp', table, (lx, ly - 0.05, lz), 'Spot', (1.0, 0.97, 0.9), 4.0, 3.5, rot=look_rotation((lx, ly, lz), (0, TABLE + 0.2, -0.3)), inner=24, outer=44, fog=0.0)
        on_table(s, table, V, 'drummer' if x == 0 else 'guitar')
    s.light('Lobby light', g, (-0.2, 2.2, z0 - 0.2), 'Point', (1.0, 0.95, 0.85), 5.0, 3.0, fog=0.0)
    s.box('Light box', g, (2.1, 1.7, z0 + 0.06), (0.92, 0.48, 0.01), (1, 1, 1), emissive=(0.85, 0.93, 1.0), emissive_intensity=2.5, shadows=False)
    for dx in (-0.23, 0.23):
        s.box('Film', g, (2.1 + dx, 1.7, z0 + 0.068), (0.36, 0.42, 0.004), (0.03, 0.04, 0.06), emissive=(0.25, 0.3, 0.36), emissive_intensity=1.0, shadows=False)
        s.box('Film: ribs', g, (2.1 + dx, 1.72, z0 + 0.071), (0.2, 0.26, 0.003), (0.1, 0.12, 0.14), emissive=(0.6, 0.68, 0.75), emissive_intensity=1.4, shadows=False)

    # The drummer's team. The surgeon and the assistant face each other across the chest; the
    # anaesthetist stands at the head with the bag; the scrub nurse is at the instrument stand.
    work = (0.0, TABLE + 0.35, -0.32)
    surgeon(s, g, V, 'Surgeon', MEDIC, (-0.6, 0, -0.34), 90, at(work, (-0.05, 0, 0)), 0)
    surgeon(s, g, V, 'Assistant', ('SchoolGirl_01', '01_C'), (0.6, 0, -0.2), 270, at(work, (0.07, 0, 0.12)), 1, Bow=16.0)
    stands = (0.0, 0, -1.62)
    mask = (0.0, TABLE + 0.33, -0.86)
    held = P.to_figure(stands, 0, mask)
    squeeze = P.clip(V, 'BagSqueeze', 90, [P.ftrack('RightArm.Grip', [(0, 0.3), (12, 0.85), (30, 0.3), (90, 0.3)], 'SmoothStep'),
                                           P.ftrack('Lean', [(0, 10), (14, 13), (40, 10), (90, 10)], 'SmoothStep')])
    staff(s, g, V, 'Anaesthetist', NURSE, stands, 0, Bow=26.0, Lean=10.0, Nod=24.0, motion=squeeze,
          LeftArm=P.arm(hand=(held[0] - 0.07, held[1] - 0.04, held[2] - 0.02), pole=(-1, -0.3, -0.2), palm=(0.3, -1, 0), grip=0.5),
          RightArm=P.arm(hand=(held[0] + 0.07, held[1] + 0.06, held[2] - 0.14), pole=(1, -0.3, -0.2), palm=(-0.4, -1, 0), grip=0.3))
    s.box('Mask', g, mask, (0.11, 0.06, 0.13), (0.75, 0.85, 0.9), rough=0.4, shadows=False)
    s.box('Bag', g, at(mask, (0, 0.07, -0.14)), (0.11, 0.11, 0.2), (0.25, 0.45, 0.8), rough=0.6, shape='Sphere', shadows=False)
    tray = (0.42, TABLE + 0.5, 0.9)
    nurse_at = (0.95, 0, 0.3)
    nurse_yaw = P.yaw_to(nurse_at, (0.3, 0, 0.75))
    reach = P.to_figure(nurse_at, nurse_yaw, tray)
    staff(s, g, V, 'Scrub nurse', ('SchoolGirl_01', '02_A'), nurse_at, nurse_yaw, Bow=10.0, Nod=16.0, HeadTurn=P.turn_to(nurse_at, nurse_yaw, work, 50.0),
          LeftArm=P.arm(hand=(reach[0] - 0.12, reach[1], reach[2]), pole=(-1, -0.5, -0.3), palm=(0, -1, 0), grip=0.6), RightArm=P.arm(40, 8, 70, grip=0.6))
    dangle(s, g, V, 'Drip', (-0.72, 1.99, -1.25), 0.1, 'iv', 3)
    # The monitor on its trolley, turned to the room: a spike on every beat of the song.
    monitor(s, g, 'Heart monitor', (-1.45, 1.62, -1.7), 14, scale=1.3)
    s.light('Monitor glow', g, (-1.4, 1.6, -1.45), 'Point', (0.3, 1.0, 0.5), 0.5, 1.5, fog=0.0)
    # Through the glass, the next theatre: the guitarist's, another team at work.
    there = (NEXT, 0, 0)
    surgeon(s, g, V, 'Surgeon, next theatre', NURSE, at(there, (-0.6, 0, -0.3)), 90, at(there, at(work, (-0.05, 0, 0))), 2)
    surgeon(s, g, V, 'Assistant, next theatre', MEDIC, at(there, (0.6, 0, -0.25)), 270, at(there, at(work, (0.07, 0, 0.1))), 1, Bow=24.0)
    # The cop in the lobby, at the window of the left-hand door, as near as they will let him.
    cop_at = (-0.4, 0, z0 - 0.42)
    P.actor(s, g, 'Cop', COP[0], COP[1], cop_at, 0, Lean=5.0, Nod=6.0, HeadTurn=P.turn_to(cop_at, 0, (0, 1.2, -0.5), 30.0),
            LeftArm=P.arm(6, 8, 14), RightArm=P.arm(hand=(0.2, 1.5, 0.36), pole=(1, -1, -0.2), fingers=(0, 1, 0), palm=(0, 0, 1), grip=0.0))

    # From high over the drummer's chest, down between the surgeons' heads (over them: lower, the
    # assistant's head hides the face) onto the face under the mask; then back down the table and
    # up, to the whole theatre from beyond its foot: the lamps, the team, the glass and the next
    # table on the left, the doors and the cop at the far end.
    M.shot(s, marks, 'surgery', out((0.04, 2.15, 0.1)), out((0.0, TABLE + 0.2, -0.8)), 42, 8.1, hand=True, lead='l',
           via=[(out((0.02, 2.25, 0.9)), out((0.0, TABLE + 0.2, -0.8)), 46)], end=(out((-1.6, 2.3, 3.2)), out((0.6, 1.05, -0.9)), 54))


# ---- out of the ward's window ---------------------------------------------------------------
# Everything here is in the window's own space: x across it, the ground at y 0, and depth the
# metres out from the glass (z = -depth). The eye in the ward is 27.6 m up, eight storeys, and
# from the back of the room the sill hides whatever is more than 8 degrees under the horizon
# (CUT: the drop a metre out): the ground nearer than 200 m, and at 150 m all but the top of a
# five-storey block. So the town starts 150 m out and is looked down on, its roofs under the
# horizon; only the towers, the spire and the hills stand above it. The picture is 23 degrees
# either side of straight out (the side walls): what is to be seen stands inside that.
EYE = ROOM_Y + 1.6
CUT = 0.14
CHURCH = (-36.0, 205.0, 1.25)      # the church: across, metres out, its size
STOREY = 3.1
TOWN_REACH = 540.0          # the town's edge from the window; the hills stand beyond it
WALLS = ('paper', 'marble_shade', 'bone', 'stone_red', 'bone_dark', 'rail', 'marble', 'paper', 'marble_shade', 'bone_dark')
PANES = ('glass',) * 7 + ('sky', 'steel_dark', 'paper')        # a pane: mostly dark, some sky in it, some blinds
ROOFS = ('steel_dark', 'stone', 'post', 'cab_dark', 'deck_dark')
# The MitchTree recipes (Engine/Assets/Trees) the trees are grown from, each again with other seeds.
TREES = (('WardMapleA', 'Maple', 21), ('WardMapleB', 'Maple', 4), ('WardMapleC', 'MapleGnarl', 9), ('WardPine', 'Pine', 11),
         ('WardBirch', 'Presets/Birch', 3), ('WardOak', 'Presets/Oak', 7))


tree = A.tree     # (a MitchTree recipe in the venue)


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
    """A stone church along x: nave, a square tower at one end and its spire (CHURCH's size)."""
    one = Mesh('church')
    _church_1(one, rng, proud / CHURCH[2])
    m.merge(one, scale=CHURCH[2])


def _church_1(m, rng, proud):
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
    x, z, yaw, seed, w, d, floors); a tree is (x, z, scale). Streets run across the view: flats and
    offices in the middle of each (the far ones taller, towers off to the sides of the sun),
    houses out on the flanks, a landmark here and there, trees in the gaps. The nearest street
    is broken by two parks, and the church stands behind the left one in its yard, nothing
    between it and the window but the park's trees."""
    rng = random.Random(404)
    lots, trees = [], []
    cx, cz, k = CHURCH
    yard = (cx - 17.0 * k - 9.0, cx + 16.0 * k + 9.0)             # the church's ground, across
    parks = {150: (yard, (24.0, 62.0)), 200: (yard,)}
    marks = {330: (150, 'tower'), 410: (-215, 'stack'), 500: (84, 'mast')}
    lots.append((200, 'church', cx, -cz, 0.0, rng.randrange(1 << 30), 0, 0, 0))
    for depth in (150, 200, 260, 330, 410, 500):
        reach = min(1.1 * depth + 20, 300)
        x = -reach
        mark = marks.get(depth)
        while x < reach:
            if mark and x >= mark[0]:
                lots.append((depth, mark[1], x + 17, -depth - 4.0, 0.0, rng.randrange(1 << 30), 0, 0, 0))
                x, mark = x + 40, None
                continue
            w, d = rng.uniform(13, 26), rng.uniform(12, 18)
            open_ = next((p for p in parks.get(depth, ()) if x + w > p[0] and x < p[1]), None)
            if open_:
                x = open_[1] + rng.uniform(2, 5)
                continue
            mid, z = x + w / 2, -(depth + rng.uniform(-8, 8))
            tall = depth >= 260 and abs(mid) > 60 and rng.random() < 0.2
            if tall or (depth >= 200 and rng.random() < 0.18):
                kind, floors = 'office', rng.randint(9, 15) if tall else rng.randint(4, 8)
            else:
                kind, floors = 'apartment', rng.randint(3, 5 if depth < 180 else 8)
            if math.hypot(mid, depth) < TOWN_REACH:
                lots.append((depth, kind, mid, z, rng.uniform(-4, 4), rng.randrange(1 << 30), w, d, floors))
            gap = rng.choice((4, 5, 6, 8, 22))      # 22: a side street, a tree on its corner
            if gap > 20 and depth <= 260:
                trees.append((x + w + gap / 2 + rng.uniform(-3, 3), z + rng.uniform(2, 9), rng.uniform(0.85, 1.2)))
            x += w + gap
        for side in (-1, 1):
            x = reach + 14
            while x < 2.0 * depth + 30 and math.hypot(x, depth) < TOWN_REACH:
                for row in (0, 24):
                    z = -(depth + row + rng.uniform(-4, 4))
                    lots.append((depth, 'house', side * x, z, rng.choice((0, 90)) + rng.uniform(-8, 8), rng.randrange(1 << 30), 0, 0, 0))
                    if rng.random() < 0.3 and depth <= 260:
                        trees.append((side * (x + 8.5), z + rng.uniform(-6, 6), rng.uniform(0.85, 1.2)))
                x += rng.uniform(15, 21)
    # The parks: trees in the open ground of the nearest street, small in front of the church
    # (they stand between it and the window) and tall to either side of it; and the churchyard's.
    for x0, x1 in parks[150]:
        x = x0 + 4.0
        while x < x1 - 3.0:
            before = yard[0] + 8 < x < yard[1] - 8 and (x0, x1) == yard
            for depth in ((142,) if before else (136, 158, 178)):
                trees.append((x + rng.uniform(-2.5, 2.5), -(depth + rng.uniform(-5, 5)), rng.uniform(0.55, 0.7) if before else rng.uniform(1.0, 1.3)))
            x += rng.uniform(9, 13)
    for x in (yard[0] + 3, yard[0] + 9, yard[1] - 8, yard[1] - 2):
        trees.append((x, -(cz + rng.uniform(-10, 4)), rng.uniform(1.0, 1.25)))
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
    """The view from the ward: origin is the ground under the window's middle. The town, the
    trees in it, the hills."""
    g = s.entity('Out of the window', parent, origin)
    A.model(s, g, 'Country', country(V), material=A.mat(V, 'Palette', color=(0.2, 0.3, 0.16), rough=1.0), shadows=False)
    for name, depths in (('WardTownNear', (150,)), ('WardTownMid', (200, 260)), ('WardTownFar', (330, 410, 500))):
        A.model(s, g, name, town(V, name, depths), material=A.mat(V, 'Palette', rough=0.85), shadows=False)
    kinds = [tree(V, *t) for t in TREES]
    rng = random.Random(77)
    # (The hospital's own lawn is out of sight under the sill from eight storeys up: the trees
    # are the town's, in its parks, its churchyard and on its corners.)
    for i, (x, z, scale) in enumerate(town_plan()[1]):
        A.model(s, g, f'Tree {i + 1}', rng.choice(kinds), (x, 0, z), (0, rng.uniform(0, 360), 0), scale)
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
    P.actor(s, g, 'Cop', COP[0], COP[1], (-half + 1.3, 0, back + 1.2), 180, 'Seated', SeatHeight=0.57, Lean=4.0, Nod=-8.0,
            LeftArm=P.arm(hand=(-0.08, 0.66, 0.28), pole=(-1, -0.3, -0.4), palm=(0, -1, 0), grip=0.4), RightArm=P.arm(hand=(0.08, 0.66, 0.28), pole=(1, -0.3, -0.4), palm=(0, -1, 0), grip=0.4))

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
    surgery(s, earth, marks, V, M)
    morning_after(s, earth, marks, V, M)
    return hand
