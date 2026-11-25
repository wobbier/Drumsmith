#!/usr/bin/env python3
"""Builds the three venues of "Highway to the Afterlife" (Design/Highway-to-the-Afterlife.md), the
proposed story set highway-afterlife in Design/Story-Mode-Setlists.json:

    python3 Tools/Venues/make_story_afterlife.py

  StoryHighway  Kickstart My Heart: the band on a flatbed trailer down a night highway that scrolls
                past, the cruiser behind with its lightbar going; the wreck on a marked stretch of
                shoulder, and the band's bodies on the asphalt.
  StoryHell     Free Bird and Bat Country: the crash site, the fall down a shaft and through
                Dante's nine circles (story_afterlife_circles), and hell: a cavern over a lake of
                lava, the island the band lands on, the crowd on its nine tiers, the staircase,
                and Satan's throne under a horned skull.
  StoryHeaven   Stairway to Heaven and My Hero: the ascent through cloud, the cloud floor, the
                stairs, the gates and God's platform, the angel choir; and, far off in the same
                scene, the rescue on Earth that My Hero cuts away to (story_afterlife_rescue).

The set is built from story_afterlife_art's props (meshes and textures drawn by
story_afterlife_mesh), posed figures (story_afterlife_people), particles and looping clips. Every
story beat is a story flag (the set's cues and moments in the manifest): VenueStory groups show
the props for it, and a Custom camera spot tagged story/<flag>[/<seconds>][/hand][/f<metres>]
(with optional story/<flag>/w1.. waypoints and a story/<flag>/end where it moves to) is the shot
the director cuts to when it lands (Director::SetStoryShots). Deterministic: a rerun writes the
same bytes.
"""
import json
import math
import os
import random
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import story_afterlife_art as A  # noqa: E402
import story_afterlife_circles as CIR  # noqa: E402
import story_afterlife_heart as HT  # noqa: E402
import story_afterlife_people as P  # noqa: E402
import story_afterlife_rescue as RES  # noqa: E402
from venuegen import Scene, look_rotation, repo_root, write_venue_json  # noqa: E402

# Colours.
ASPHALT = (0.07, 0.07, 0.08)
LINE_WHITE = (0.85, 0.85, 0.8)
LINE_YELLOW = (0.9, 0.7, 0.15)
GRAVEL = (0.22, 0.2, 0.18)
GRASS = (0.06, 0.1, 0.05)
STEEL = (0.35, 0.36, 0.38)
WHITE = (0.9, 0.9, 0.92)
FIRE = (1.0, 0.45, 0.08)
EMBER = (1.0, 0.2, 0.03)
STONE = (0.16, 0.12, 0.11)
STONE_DARK = (0.08, 0.06, 0.06)
LAVA = (1.0, 0.25, 0.02)
CLOUD = (0.95, 0.96, 1.0)
GOLD = (1.0, 0.8, 0.35)

# The highway's slew at the end of Kickstart My Heart: the world turns this far about the trailer.
SLEW_YAW = 26.0
SLEW_SHIFT = (2.5, 0.0, 0.0)


def slewed(p):
    """Where a point on the highway's road ends up once the slew is done (venue space)."""
    a = math.radians(SLEW_YAW)
    x, y, z = p
    return (x * math.cos(a) + z * math.sin(a) + SLEW_SHIFT[0], y + SLEW_SHIFT[1], -x * math.sin(a) + z * math.cos(a) + SLEW_SHIFT[2])


# The band: the same marks in every venue (y is the deck or floor they stand on).
DRUMMER = (0.0, 5.2)
GUITAR = (-2.1, 2.6)
BASS = (2.1, 2.8)
VOCALS = (0.0, 1.0)

SHOTS = {}    # venue -> {flag: [eye, target, fov]} for Tools' previews (written beside the scene)

# The crash site, the same place at the end of Kickstart My Heart and the start of Free Bird: the
# band on the road where they came down, about where they stood (relative to the site: x across
# the road, z along it, and the yaw each body lies at, the feet at (x, z)), and the overturned rig
# burning at the road's right edge beside them, through the guardrail.
CRASH_LYING = {'drummer': (DRUMMER[0] + 0.3, DRUMMER[1] + 0.6, 180), 'guitar': (GUITAR[0], GUITAR[1], 172), 'bass': (BASS[0], BASS[1], 188), 'vocals': (VOCALS[0], VOCALS[1], 180)}
# The cop's cruiser pulled up short of them, angled across the lane: where, and its yaw.
COP_CAR = ((-7.5, 0.0, -9.0), 24.0)


def band(s, marks, y):
    s.spot(marks, 'Drummer', (DRUMMER[0], y, DRUMMER[1]))
    s.spot(marks, 'Guitar', (GUITAR[0], y, GUITAR[1]), yaw=-8)
    s.spot(marks, 'Bass', (BASS[0], y, BASS[1]), yaw=8)
    s.spot(marks, 'Vocals', (VOCALS[0], y, VOCALS[1]))


def shot(s, marks, flag, eye, target, fov=50.0, hold=None, hand=False, end=None, via=(), focus=False, heli=False, ride=0.0, sky=None, lin=False, lead=None):
    """The story shot for flag: from eye at target; end (eye, target, fov) is where it moves to,
    by way of via [(eye, target, fov), ...]. focus: pull focus to the target (and soften the rest).
    heli: shot from a helicopter on a long lens (the aim hunts, the zoom punches in). ride: the
    camera is bolted to something on the move and takes the road this hard (1 a fast highway). sky: the
    hour of the procedural sky the shot is under, whatever the venue has behind it. lin: the move
    runs at one speed, not eased (a camera keeping pace with something). lead: 'l' or 'r', the
    side of the picture the subject (the middle of the spot's view) is turned to while the
    highway is up, clear of it (Director: the story tag's leadl / leadr). A shot on
    Earth (far out along x, beyond heaven's sky) is tagged lights: the police lights and the fire
    stay in colour through a black and white look."""
    def f(e, t):
        return f'/f{math.dist(e, t):.2f}' if focus else ''
    tag = 'story/' + flag + (f'/{hold:g}' if hold else '') + ('/hand' if hand else '') + ('/heli' if heli else '') + ('/lin' if lin else '') + (f'/ride{ride:g}' if ride else '') + (f'/sky{sky:g}' if sky is not None else '') + (f'/lead{lead}' if lead else '') + ('/lights' if eye[0] > 1000 else '') + f(eye, target)
    s.camera_spot('Story ' + flag, marks, eye, target, 'Custom', fov, tag)
    views = [[list(eye), list(target), fov]]
    for i, (e, t, v) in enumerate(via):
        s.camera_spot(f'Story {flag} w{i + 1}', marks, e, t, 'Custom', v, f'story/{flag}/w{i + 1}')
        views.append([list(e), list(t), v])
    if end:
        s.camera_spot('Story ' + flag + ' end', marks, end[0], end[1], 'Custom', end[2], 'story/' + flag + '/end' + f(end[0], end[1]))
        views.append([list(end[0]), list(end[1]), end[2]])
    SHOTS.setdefault(s.venue, {})[flag] = views


def write(s, venue, name, ambience=None):
    folder = os.path.join(repo_root(), 'Assets', 'Venues', venue)
    os.makedirs(folder, exist_ok=True)
    s.write(os.path.join(folder, venue + '.lvl'))
    write_venue_json(folder, name, venue + '.lvl', author='Drumsmith', ambience=ambience)
    print(f'Assets/Venues/{venue}: {len(s.entities)} entities')


def textured(e, venue, name, tiling=(1, 1), glow=None, power=1.0, glow_name=None):
    """Put one of the set's textures on a primitive (s.box / s.slab)."""
    for c in e.components:
        if c.get('Type') == 'Mesh':
            m = c['Material']
            m['Textures'] = {'Diffuse': {'Path': A.tex(venue, name)}}
            m['Tiling'] = [float(tiling[0]), float(tiling[1])]
            if glow is not None:
                m['Textures']['Emissive'] = {'Path': A.tex(venue, glow_name or name)}
                m['EmissiveColor'] = [float(v) for v in glow]
                m['EmissiveIntensity'] = float(power)
    return e


def see_through(e, opacity, additive=False):
    for c in e.components:
        if c.get('Type') == 'Mesh':
            c['CastShadows'] = False
            c['Material'].update({'RenderMode': 1, 'BlendMode': 2 if additive else 0, 'Opacity': float(opacity)})
    return e


# ---- shared pieces ------------------------------------------------------------------------------
FLAME = 3.2     # a flame's glow (its core a little more): bright enough to bloom, not to burn out to a white blob


def fire(s, parent, venue, at, size=1.0, light=500.0, smoke=True, name='Fire'):
    """A fire: tongues of flame flickering on loops, flames and sparks and smoke in the air, and an
    orange light that jumps about."""
    rng = random.Random(int(at[0] * 100 + at[2] * 7))
    flame_mat = A.mat(venue, 'Palette', (0, 0, 0), glow=(1.0, 0.5, 0.12), power=FLAME, additive=True, both=True)
    core_mat = A.mat(venue, 'Palette', (0, 0, 0), glow=(1.0, 0.85, 0.45), power=FLAME * 1.3, additive=True, both=True)
    for i in range(6):
        clip = P.clip(venue, f'Flicker{i % 3}', 14 + 5 * (i % 3), [P.track('Scale', [(0, (1, 1, 1)), (4 + i % 3, (1.15, 1.4 - 0.1 * (i % 3), 0.9)), (9 + 2 * (i % 3), (0.85, 0.75, 1.15)),
                                                                             (14 + 5 * (i % 3), (1, 1, 1))], 'SmoothStep')])
        p = (at[0] + rng.uniform(-0.9, 0.9) * size, at[1], at[2] + rng.uniform(-0.9, 0.9) * size)
        body = P.looping(s, parent, f'{name} tongue {i}', clip, p, speed=rng.uniform(0.8, 1.5))
        h = size * rng.uniform(1.4, 3.0)
        A.model(s, body, 'Flame', A.flame(venue), (0, 0, 0), (0, rng.uniform(0, 360), 0), (size * rng.uniform(0.9, 1.5), h, size * rng.uniform(0.9, 1.5)), flame_mat, shadows=False)
        A.model(s, body, 'Flame core', A.flame(venue), (0, 0, 0), (0, rng.uniform(0, 360), 0), (size * 0.6, h * 0.6, size * 0.6), core_mat, shadows=False)
    A.fire_fx(s, parent, venue, name, (at[0], at[1] + 0.2 * size, at[2]), size, smoke)
    A.glow_card(s, parent, venue, name + ' glow', (at[0], at[1] + 0.06, at[2]), 3.2 * size, (1.0, 0.4, 0.08), 1.1, (90, 0, 0))
    jump = P.clip(venue, 'FireLight', 20, [P.track('Position', [(0, (0, 0, 0)), (3, (0.25, 0.2, -0.2)), (7, (-0.3, -0.15, 0.2)), (12, (0.2, 0.3, 0.3)), (16, (-0.15, 0.0, -0.3)), (20, (0, 0, 0))])])
    s.light(name + ' light', P.looping(s, parent, name + ' light', jump, (at[0], at[1] + 1.6 * size, at[2]), speed=1.3), (0, 0, 0), 'Point', (1.0, 0.6, 0.28), light, 20 * size)


def lightbar(s, parent, venue, at):
    """A cruiser's lightbar: red and blue lamps, their glare, and two spot lights sweeping round."""
    spin = P.clip(venue, 'LightbarSpin', 24, [P.track('Rotation', [(0, (0, 0, 0)), (12, (0, 180, 0)), (24, (0, 359.9, 0))])])
    s.box('Lamp red', parent, (at[0] - 0.4, at[1] + 0.06, at[2]), (0.45, 0.14, 0.24), (1, 0.05, 0.05), emissive=(1, 0.05, 0.05), emissive_intensity=10.0, shadows=False)
    s.box('Lamp blue', parent, (at[0] + 0.4, at[1] + 0.06, at[2]), (0.45, 0.14, 0.24), (0.1, 0.2, 1), emissive=(0.1, 0.2, 1), emissive_intensity=10.0, shadows=False)
    body = P.looping(s, parent, 'Sweep', spin, (at[0], at[1] + 0.2, at[2]))
    s.light('Sweep red', body, (0, 0, 0), 'Spot', (1.0, 0.05, 0.05), 450.0, 60, rot=(10, 0, 0), inner=14, outer=32)
    s.light('Sweep blue', body, (0, 0, 0), 'Spot', (0.1, 0.25, 1.0), 600.0, 60, rot=(10, 180, 0), inner=14, outer=32)
    for yaw, c in ((0, (1.0, 0.06, 0.05)), (180, (0.12, 0.25, 1.0))):
        A.glow_card(s, body, venue, 'Glare', add3(P_rot((0, 0.05, 0.3), yaw), (0, 0, 0)), 0.6, c, 2.0, (0, yaw, 0))


def P_rot(v, yaw):
    return A.rot(v, (0, yaw, 0))


def add3(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def beacons(s, parent, venue, red=450.0, blue=600.0, reach=60.0, speed=1.0, glare=(0.6, 2.0), kind=None):
    """A police car's two roof beacons turning (the patrol cruiser's, or kind's of the fleet): a
    glare going round each, and (red / blue above 0) a spot light sweeping from each at those
    levels, opposite one another."""
    spin = P.clip(venue, 'LightbarSpin', 24, [P.track('Rotation', [(0, (0, 0, 0)), (12, (0, 180, 0)), (24, (0, 359.9, 0))])])
    x, y, z = A.VEHICLES[kind]['Beacons'][-1] if kind else A.PATROL_BEACON
    for side, yaw, name, c, lamp, level in ((-1, 0, 'red', (1.0, 0.06, 0.05), (1.0, 0.05, 0.05), red), (1, 180, 'blue', (0.12, 0.25, 1.0), (0.1, 0.25, 1.0), blue)):
        body = P.looping(s, parent, f'Beacon {name}', spin, (side * x, y, z), speed=speed)
        if level > 0:
            s.light(f'Sweep {name}', body, (0, 0, 0), 'Spot', lamp, level, reach, rot=(10, yaw, 0), inner=14, outer=32)
        A.glow_card(s, body, venue, 'Glare', P_rot((0, 0, 0.14), yaw), glare[0], c, glare[1], (0, yaw, 0))


def cruiser(s, parent, venue, at, yaw=0.0, name='Cruiser', door_open=False, beams=True, kind=None):
    """A police car facing +z at yaw 0, its centre at at (on the road): the patrol cruiser, or
    kind of the fleet (TrailDuster, Ranger). Returns its group."""
    g = s.entity(name, parent, at, (0, yaw, 0))
    # The model brings its own glass, lamps and beacons: only their light is added.
    if kind:
        A.vehicle(s, g, kind)
        hx, hy, hz = A.lamp(kind, 'Headlamp')
    else:
        A.patrol_cruiser(s, g, door_open=door_open)
        hx, hy, hz = A.PATROL_HEADLAMP
    for x in (-hx, hx):
        A.glow_card(s, g, venue, 'Headlight glare', (x, hy, hz + 0.05), 0.5, (1.0, 0.95, 0.8), 1.2)
    A.headlights(s, g, hx, hy, hz + 0.15, 1500.0, 60)
    beacons(s, g, venue, kind=kind)
    return g


def driver(s, parent, kind=None, name='Cop', **pose):
    """The cop at the wheel of a police car (the patrol cruiser, or kind of the fleet), under the
    car's group: skinned (P.actor), sat where the car's export says the driver's hips and heels
    go, both hands on the wheel, the feet out at the pedals. pose: VenueFigure fields over that."""
    facts = A.VEHICLES[kind or 'PatrolCruiser']
    (sx, sy, sz), heel, wheel = facts['Seat'], facts['Heel'], facts['SteeringWheel']
    at = (sx, heel, sz)
    wx, wy, wz = P.to_figure(at, 0, wheel)
    reach = min(0.66, wz + 0.2)

    # The rim: its radius and its axis (out of its face toward the driver), from the export. The
    # hands hold it at ten and two, each wrapped round the outside of the rim: the palm against
    # the rim's outer edge facing the hub, the fingers going over it away from the driver.
    radius, axis = facts.get('SteeringRadius', 0.2), facts.get('SteeringAxis', (0.0, 0.5, -0.87))
    lean = -axis[1] * axis[1], 1.0 - axis[1] * axis[1], -axis[1] * axis[2]      # up the wheel's face
    n = math.sqrt(sum(c * c for c in lean))
    up = tuple(c / n for c in lean)

    def on_wheel(side, clock=55.0):
        sin, cos = math.sin(math.radians(clock)), math.cos(math.radians(clock))
        out = (side * sin + cos * up[0], cos * up[1], cos * up[2])       # from the hub to the hand
        hand = tuple(w + (radius + 0.02) * o for w, o in zip((wx, wy, wz), out))
        return P.arm(hand=hand, pole=(side, -1, -0.3), fingers=tuple(-c for c in axis), palm=tuple(-c for c in out), grip=0.9)
    fields = dict(SeatHeight=round(sy - heel, 3), Lean=-4.0, LeftArm=on_wheel(-1), RightArm=on_wheel(1),
                  LeftLeg=P.leg(foot=(-0.11, 0, reach - 0.06), knee=(-0.25, 1, 0.3)), RightLeg=P.leg(foot=(0.1, 0, reach), knee=(0.25, 1, 0.3)))
    fields.update(pose)
    return P.actor(s, parent, name, *COP_LOOK, at, 0, 'Seated', **fields)


WHEEL_FRAMES = 15       # frames (at 30 a second) a wheel takes to go round: two turns a second


def wheel_spin(venue):
    """A wheel going round forwards (+x rotation: its top toward +z, the way a vehicle facing +z
    drives). Not at its road speed: at 48 m/s a truck's wheel turns 14 times a second, which a
    frame rate samples as anything (a wheel whose spokes or lug nuts repeat every 36 to 72
    degrees and turns 80 a frame at 60 fps reads as turning slowly backwards: the rig's did). At
    about two turns a second a frame never turns it more than half the way to the next spoke at
    60 fps and up, so it is always seen going forwards."""
    third = WHEEL_FRAMES // 3
    return P.clip(venue, 'WheelSpin', WHEEL_FRAMES, [P.track('Rotation', [(0, (0, 0, 0)), (third, (120, 0, 0)), (2 * third, (240, 0, 0)), (WHEEL_FRAMES, (359.9, 0, 0))])])


def rolling(s, parent, venue, kind=None):
    """A police car driving, under parent (its group, facing +z): the body with the driver's
    window wound down, and the four wheels turning (the export's Rolling and Wheel models)."""
    A.rolling_part(s, parent, kind, 'Rolling', 'Body')
    facts = A.VEHICLES[kind or 'PatrolCruiser']
    spin = wheel_spin(venue)
    for end in ('WheelFront', 'WheelRear'):
        x, y, z = facts[end]
        for side in (-1, 1):
            hub = P.looping(s, parent, 'Wheel', spin, (side * x, y, z))
            A.rolling_part(s, hub, kind, 'Wheel', 'Tyre', (0, 0 if side < 0 else 180, 0))


def window_arm(kind=None):
    """The driver's left arm out of the wound-down window (driver(LeftArm=...)): the elbow out
    over the sill, the forearm lying forward along it, the hand flat on the door's top."""
    facts = A.VEHICLES[kind or 'PatrolCruiser']
    (sx, sy, sz), heel, (wx, wy, wz) = facts['Seat'], facts['Heel'], facts['Sill']
    hand = P.to_figure((sx, heel, sz), 0, (wx + 0.03, wy + 0.05, sz + 0.36))
    return P.arm(hand=hand, pole=(-1, 0.15, -0.5), fingers=(0, 0, 1), palm=(0, -1, 0), grip=0.3)


def head_bang(figure, degrees, calm=0.35):
    """A skinned figure's head going with the band on every beat (VenueBeat Nod on it), the more
    so as the playing is better (calm: how much of it is left at the worst)."""
    figure.add({'Type': 'VenueBeat', 'Offset': [0.0, 0.0, 0.0], 'Nod': float(degrees), 'Calm': float(calm)})
    return figure


def driver_face(kind=None):
    """About where the driver's face is, from the car's centre."""
    x, y, z = A.VEHICLES[kind or 'PatrolCruiser']['Seat']
    return (x, y + 0.85, z + 0.08)


def police_helicopter(s, parent, venue, kind, at, rot, target, level, reach, name='Helicopter', wander=1.5, inner=4.0, outer=8.0, pace=1.0):
    """A police helicopter of the fleet (JetRanger, AS350) hovering with its skids at at, its nose
    (+z) turned by rot, its rotors turning; and the searchlight under its belly, which rides with it
    and is held on target (venue space) by hand: it strays up to about wander metres off it and is
    pulled back (VenueAim). pace: its hover's speed, so two of them don't move as one. Returns the
    body, for anything else that should ride with it."""
    facts = A.VEHICLES[kind]
    bob = P.clip(venue, 'HeliBob', 170, [P.track('Position', [(0, (0, 0, 0)), (45, (1.6, 0.9, -2.0)), (95, (-1.0, -0.7, 2.5)), (140, (0.8, 0.4, 0.6)), (170, (0, 0, 0))], 'SmoothStep'),
                                         P.track('Rotation', [(0, (0, 0, 0)), (45, (4, 6, -7)), (95, (-3, -5, 6)), (140, (2, 3, -3)), (170, (0, 0, 0))], 'SmoothStep')])
    copter = P.looping(s, s.entity(name, parent, at, rot), 'Hover', bob, speed=pace)
    A.vehicle(s, copter, kind)
    span = facts['RotorSpan']
    blades = P.looping(s, copter, 'Rotor', P.clip(venue, 'RotorSpin', 6, [P.track('Rotation', [(0, (0, 0, 0)), (3, (0, 180, 0)), (6, (0, 359.9, 0))])]), tuple(facts['Rotor']))
    A.vehicle(s, blades, kind + 'Rotor', 'Blades')
    see_through(s.box('Rotor disc', blades, (0, 0, 0), (span, 0.02, span), (0.3, 0.3, 0.32), shape='Cylinder', shadows=False), 0.1)
    tail = P.looping(s, copter, 'Tail rotor', P.clip(venue, 'TailRotorSpin', 4, [P.track('Rotation', [(0, (0, 0, 0)), (2, (180, 0, 0)), (4, (359.9, 0, 0))])]), tuple(facts['TailRotor']))
    A.vehicle(s, tail, kind + 'TailRotor', 'Blades')
    see_through(s.box('Tail rotor disc', tail, (0, 0, 0), (1.5, 0.02, 1.5), (0.3, 0.3, 0.32), rot=(0, 0, 90), shape='Cylinder', shadows=False), 0.1)
    bx, by, bz = facts['Beacons'][0]
    A.glow_card(s, copter, venue, 'Beacon glare', (bx, by + 0.03, bz), 0.4, (1.0, 0.08, 0.06), 1.5, (0, 90, 0))
    # The searchlight: a yoke under the belly forward of the skids' cross tubes, and in it the lamp
    # housing, which is what the aim turns (its lens and its beam with it).
    belly = (0.0, 0.5, round(facts['Max'][2] * 0.42, 3))
    s.box('Searchlight yoke', copter, (belly[0], belly[1] + 0.2, belly[2]), (0.1, 0.24, 0.1), (0.05, 0.05, 0.06), metallic=0.6, shadows=False)
    lamp = s.entity('Searchlight', copter, belly, (60, 0, 0))
    lamp.add({'Type': 'VenueAim', 'Target': [round(float(c), 3) for c in target], 'Wander': float(wander), 'Seconds': 3.4})
    s.box('Housing', lamp, (0, 0, 0), (0.34, 0.4, 0.34), (0.05, 0.05, 0.06), rot=(90, 0, 0), metallic=0.6, rough=0.5, shape='Cylinder', shadows=False)
    s.box('Lens', lamp, (0, 0, 0.2), (0.3, 0.02, 0.3), (1, 1, 1), rot=(90, 0, 0), emissive=(0.85, 0.92, 1.0), emissive_intensity=14.0, shape='Cylinder', shadows=False)
    A.glow_card(s, lamp, venue, 'Lens glare', (0, 0, 0.24), 1.3, (0.85, 0.92, 1.0), 4.0)
    s.light('Beam', lamp, (0, 0, 0.26), 'Spot', (0.85, 0.92, 1.0), level, reach, inner=inner, outer=outer)
    return copter


def road(s, parent, venue, x0, x1, z0, z1, dashes=True):
    """A stretch of four-lane asphalt with its edge lines (and lane dashes)."""
    textured(s.slab('Asphalt', parent, x0, x1, -0.2, 0.0, z0, z1, (1, 1, 1), rough=0.9), venue, 'Asphalt', ((x1 - x0) / 4.0, (z1 - z0) / 4.0))
    for x in (x0 + 0.3, x1 - 0.45):
        s.slab('Edge line', parent, x, x + 0.15, 0.0, 0.012, z0, z1, LINE_WHITE, shadows=False)
    cx = (x0 + x1) / 2
    for x in (-0.2, 0.08):
        s.slab('Centre line', parent, cx + x, cx + x + 0.12, 0.0, 0.012, z0, z1, LINE_YELLOW, shadows=False)
    if dashes:
        z = z0
        while z < z1:
            for x in (-5.4, 5.4):
                s.slab('Dash', parent, cx + x - 0.07, cx + x + 0.07, 0.0, 0.012, z, z + 3.0, LINE_WHITE, shadows=False)
            z += 12.0


def burning_wreck(s, parent, venue, o):
    """The wreck at o (see A.wreck: the flatbed on its side along +z, the gear thrown toward -x),
    burning."""
    g = s.group('Wreck', parent, o)
    name = 'Wrecked rig'
    if venue == 'StoryHighway':
        A.vehicle(s, g, 'BandFlatbedWreck', 'Overturned rig')
        name = 'Crash debris'
    A.model(s, g, name, A.wreck(venue), material=A.mat(venue, 'Palette', rough=0.9))
    fire(s, g, venue, (6.6, 0.4, 14.6), 1.5, 320.0, name='Cab fire')
    fire(s, g, venue, (4.2, 0.0, 6.0), 1.1, 200.0, name='Deck fire')
    fire(s, g, venue, (1.4, 0.0, 9.2), 0.7, 80.0, smoke=False, name='Fuel fire')
    fire(s, g, venue, (2.9, 0.0, 1.0), 0.5, 50.0, smoke=False, name='Tyre fire')
    # Burning fuel across the road.
    textured(s.box('Fuel', g, (2.6, 0.006, 8.0), (5.5, 0.004, 7.5), (0.02, 0.02, 0.025), rough=0.05, metallic=0.7, shadows=False), venue, 'Asphalt', (1, 1))
    for i, (x, z) in enumerate(((0.3, 7.6), (1.9, 6.4), (3.2, 10.6), (2.4, 4.2))):
        body = P.looping(s, g, f'Fuel flame {i}', P.clip(venue, 'Flicker1', 19, [P.track('Scale', [(0, (1, 1, 1)), (5, (1.15, 1.3, 0.9)), (11, (0.85, 0.75, 1.15)), (19, (1, 1, 1))], 'SmoothStep')]), (x, 0, z), speed=1.0 + 0.2 * i)
        A.model(s, body, 'Flame', A.flame(venue), (0, 0, 0), (0, i * 70, 0), (0.5, 0.5 + 0.12 * i, 0.5), A.mat(venue, 'Palette', (0, 0, 0), glow=(1.0, 0.5, 0.12), power=FLAME, additive=True, both=True), shadows=False)
    return g


# The cop and the EMS crews: a character and its PolygonTown atlas (skinned: P.actor).
COP_LOOK = ('ShopKeeper_01', '04_B')
MEDIC_LOOK = ('Son_01', '02_A')
# Who lies where at the crash site, relative to it: (x, z, yaw), the feet at (x, z).
LYING = {'drummer': (-1.0, 1.0, 200), 'guitar': (-5.0, 4.0, 140), 'bass': (4.5, -1.5, 260), 'vocals': (-3.5, -3.0, 30)}
# The side of each of the others their medic kneels on (the bass player's is away from the wreck).
MEDICS = (('guitar', -1), ('bass', 1), ('vocals', 1))


def beside_chest(lying, side, out=0.75, up_body=1.3):
    """Where someone kneels at the chest of a body lying at (x, z, yaw), and the yaw that faces
    them across it: up_body from the feet toward the head, out to one side (+1 or -1)."""
    bx, bz, byaw = lying
    d = P_rot((side * out, 0, -up_body), byaw)
    return (bx + d[0], bz + d[2]), byaw - side * 90


# The band as they lie on the road, skinned and dressed as the band (VenueFigure As: whoever plays
# each part in the song, in their clothes; the stand-in looks are for outside one), each flung
# their own way: VenueFigure fields, in the figure's own space as it stood. (The drummer's right
# arm stays by their side, the stick just beyond its fingers.)
BAND_LOOKS = {'drummer': ('Son_01', '01_A'), 'guitar': ('Daughter_01', '02_C'), 'bass': ('Mother_01', '03_A'), 'vocals': ('SchoolBoy_01', '04_C')}
BAND_DRESS = {'drummer': 'Drummer', 'guitar': 'Guitar', 'bass': 'Bass', 'vocals': 'Vocals'}
SPRAWL = {
    'drummer': dict(HeadTurn=-18.0, HeadTilt=6.0, LeftArm=P.arm(-4, 38, 30, grip=0.3), RightArm=P.arm(-3, 12, 8, grip=0.4), LeftLeg=P.leg(9), RightLeg=P.leg(4)),
    'guitar': dict(HeadTurn=24.0, Side=6.0, LeftArm=P.arm(-4, 72, 55, grip=0.2), RightArm=P.arm(-4, 24, 15, grip=0.5), LeftLeg=P.leg(12), RightLeg=P.leg(3)),
    'bass': dict(HeadTurn=-30.0, Side=-5.0, LeftArm=P.arm(-4, 18, 12, grip=0.5), RightArm=P.arm(-4, 86, 40, grip=0.2), LeftLeg=P.leg(5), RightLeg=P.leg(14)),
    'vocals': dict(HeadTurn=15.0, HeadTilt=-8.0, LeftArm=P.arm(-4, 52, 70, grip=0.3), RightArm=P.arm(-4, 30, 20, grip=0.4), LeftLeg=P.leg(10), RightLeg=P.leg(7)),
}


def dead(s, parent, label, who, at, yaw, **pose):
    """One of the band lying on their back, the feet at at, the head toward -z after yaw (as
    P.lie lays a baked figure)."""
    x, y, z = at
    laid = s.entity(label, parent, (x, y + 0.14, z), (-90, yaw, 0))
    fields = dict(SPRAWL[who])
    fields.update(pose)
    return P.actor(s, laid, label, *BAND_LOOKS[who], (0, 0, 0), 0, dress=BAND_DRESS[who], **fields)


def crash_site(s, parent, venue, o, flags, cop=None, ems=False, burning=True, lying=None, wreck_at=(3.0, 0.0, -2.0), ambulance=True):
    """The crash site around o: the wreck (burning), the band on the asphalt and a dropped stick.
    flags: the flags the figures change at ('wake': the drummer opens their eyes, 'nod': the cop
    nods, 'relieved': a medic takes the compressions over from the cop, 'lifted': the drummer is
    off the road, on the gurney, and the cop with them). cop: (x, yaw,
    z) where the cop kneels giving CPR (None: no cop). ems: the medics and (ambulance) their
    ambulance and stretcher. lying: who lies where ({member: (x, z, yaw)} relative to o) instead of the usual
    spread. Returns the drummer's hand in venue space."""
    ox, oy, oz = o
    if burning:
        burning_wreck(s, parent, venue, add3(o, wreck_at))
    g = s.group('Crash site', parent, o)
    # The band on the asphalt (dead(): the band's own bodies), a stick beyond the drummer's fingers.
    where = lying or LYING
    lying = {who: (None, None, (x, 0, z), yaw) for who, (x, z, yaw) in where.items()}
    for who, (_, _, at, yaw) in lying.items():
        if who == 'drummer':
            dead(s, P.between(s, g, 'Drummer still', None, flags.get('lifted') or flags.get('wake'), 0.0 if flags.get('lifted') else 0.3, at), 'Drummer', who, at, yaw)
            if flags.get('wake'):
                # Eyes on their own hand, its fingers lifting off the road.
                dead(s, P.between(s, g, 'Drummer awake', flags['wake'], None, 0.3, at), 'Drummer awake', who, at, yaw, HeadTurn=28.0, HeadTilt=-4.0,
                     RightArm=P.arm(4, 14, 30, grip=0.1))
        else:
            dead(s, g, who.capitalize(), who, at, yaw)
    # The drummer's right hand: at the side, a little below the hip, as laid down by lie().
    drummer = lying['drummer']
    yaw = math.radians(drummer[3])
    local = (0.3, 0.06, -0.78)
    hand = (drummer[2][0] + local[0] * math.cos(yaw) + local[2] * math.sin(yaw), local[1], drummer[2][2] - local[0] * math.sin(yaw) + local[2] * math.cos(yaw))
    # The stick lies just beyond the fingers (which point at the feet), out from the body.
    stick = add3(hand, P_rot((0.14, -0.04, 0.34), drummer[3]))
    s.box('Drumstick', g, stick, (0.03, 0.41, 0.03), (0.85, 0.7, 0.45), rot=(90, drummer[3] + 24, 0), shape='Cylinder')
    s.box('Drumstick, snapped', g, add3(hand, P_rot((1.0, -0.04, 0.9), drummer[3])), (0.03, 0.2, 0.03), (0.85, 0.7, 0.45), rot=(90, drummer[3] + 80, 0), shape='Cylinder')
    s.light('Hand fill', g, (hand[0], 0.6, hand[2]), 'Point', (1.0, 0.75, 0.55), 5.0, 2.5)
    if cop:
        # Skinned (VenueFigure): on his knees 0.53 m from the breastbone, his hands on it.
        ahead = P_rot((0, 0, 0.22), cop[1])
        cpos = (cop[0] + ahead[0], 0, cop[2] + ahead[2])
        # Compressions, about 110 a minute (in slow motion under a SlowMotion group).
        P.actor(s, P.between(s, g, 'Cop CPR', flags.get('cop'), flags.get('relieved') or flags.get('lifted') or flags.get('nod'), 0.0 if flags.get('lifted') else 0.2, cpos), 'Cop',
                *COP_LOOK, cpos, cop[1], motion=P.compressions(venue), **P.kneeling_over())
        if flags.get('relieved'):
            # A medic has the compressions from then on, in the cop's place (a cut: no fade).
            P.actor(s, P.between(s, g, 'Medic CPR', flags['relieved'], flags.get('lifted'), 0.0, cpos), 'Medic',
                    *MEDIC_LOOK, cpos, cop[1], motion=P.compressions(venue), **P.kneeling_over())
        if flags.get('nod'):
            P.actor(s, P.between(s, g, 'Cop nod', flags['nod'], None, 0.2, cpos), 'Cop nodding', *COP_LOOK, cpos, cop[1], **P.kneeling_over(bow=30.0, nod=28.0))
    if ems:
        # Each kneels at their patient's chest as the cop does at the drummer's: 1.3 m up the body
        # from the feet, half a metre out to one side, facing across it; one hand on the chest,
        # the other working at the neck.
        def working(side):
            return dict(stance='Kneeling', Bow=28.0, Lean=12.0, Nod=18.0, LeftLeg=P.leg(8), RightLeg=P.leg(8),
                        LeftArm=P.arm(hand=(-0.1 - 0.12 * (side > 0), 0.28, 0.5), pole=(-1, -0.2, -0.3), palm=(0, -1, 0), grip=0.2),
                        RightArm=P.arm(hand=(0.1 + 0.12 * (side < 0), 0.28, 0.5), pole=(1, -0.2, -0.3), palm=(0, -1, 0), grip=0.2))
        work = P.clip(venue, 'MedicWorking', 45, [P.ftrack('Bow', [(0, 28), (20, 34), (45, 28)], 'SmoothStep'), P.ftrack('Turn', [(0, 0), (20, 7), (45, 0)], 'SmoothStep'),
                                                  P.ftrack('Nod', [(0, 18), (26, 10), (45, 18)], 'SmoothStep')])
        for i, (who, side) in enumerate(MEDICS):
            bx, bz, byaw = where[who]
            (mx, mz), yaw = beside_chest(where[who], side, 0.53)
            at = (mx, 0, mz)
            if i == 0 and flags.get('wake'):
                P.actor(s, P.between(s, g, 'Medic working', None, flags['wake'], 0.2, at), 'Medic', *MEDIC_LOOK, at, yaw, motion=work, **working(side))
                seen = dict(working(side), Bow=16.0, Lean=6.0, Nod=-6.0, Turn=P.turn_to(at, yaw, drummer[2], 30.0), HeadTurn=P.turn_to(at, yaw, drummer[2], 60.0))
                P.actor(s, P.between(s, g, 'Medic sees', flags['wake'], None, 0.2, at), 'Medic looking', *MEDIC_LOOK, at, yaw, **seen)
            else:
                P.actor(s, g, f'Medic {i}', *MEDIC_LOOK, at, yaw, motion=work, speed=0.8 + 0.15 * i, **working(side))
            bag = P_rot((side * 1.25, 0, -2.0), byaw)       # out past the patient's shoulder, on the medic's side
            s.box('Kit bag', g, (bx + bag[0], 0.15, bz + bag[2]), (0.5, 0.3, 0.3), (0.75, 0.1, 0.08), rot=(0, yaw + 20, 0))
        if ambulance:
            amb = s.entity('Ambulance', g, (-9, 0, 8), (0, 160, 0))
            A.model(s, amb, 'Body', A.ambulance(venue))
            lightbar(s, amb, venue, (0, 3.1, 2.2))
            s.light('Ambulance work light', amb, (0, 2.6, -3.2), 'Spot', (1.0, 0.97, 0.9), 700.0, 22, rot=(35, 180, 0), inner=30, outer=55)
            s.box('Stretcher', g, (-6.2, 0.45, 4.2), (0.6, 0.08, 1.9), (0.85, 0.85, 0.2), rot=(0, 150, 0))
            s.box('Stretcher frame', g, (-6.2, 0.22, 4.2), (0.5, 0.4, 1.7), (0.4, 0.42, 0.45), rot=(0, 150, 0), metallic=0.8, rough=0.4)
    return (ox + hand[0], oy + hand[1], oz + hand[2])


def night_sky(s, parent, venue, centre):
    A.model(s, parent, 'Night sky', A.sky_dome(venue, 'NightDome', 'Night', 170.0, 3), (centre[0], centre[1] - 8, centre[2]), (0, 0, 0), 1.0,
            A.mat(venue, 'Night', (0, 0, 0), glow=(1, 1, 1), power=1.0), shadows=False)


def earth(s, parent, venue):
    """The country round the crash site, for when it is seen from the air by day (Free Bird's way
    up, and the fall back): the ground out to hills on the horizon, the highway running on both
    ways, woods and fields, and real trees (MitchTree) along the road where the cameras stand."""
    g = s.group('The Earth', parent)
    A.model(s, g, 'Ground', A.earth_ground(venue), material=A.mat(venue, 'Earth', rough=1.0), shadows=False)
    A.model(s, g, 'Highway', A.earth_road(venue), material=A.mat(venue, 'Palette', rough=0.9), shadows=False)
    A.model(s, g, 'Woods', A.earth_crowns(venue), material=A.mat(venue, 'Palette', color=(0.17, 0.3, 0.11), rough=1.0), shadows=False)
    A.plant_roadside(s, s.group('Roadside trees', g), venue, A.roadside_spots(-175, 175, A.BELT[0] + 3, A.BELT[1] + 4, 125, 5), shadows=True, tall=(9.0, 15.0))
    return g


def roadside(s, parent, venue, centre, half=60.0, shoulder_x=14.0, torn_z=None, trees=True, sky=True, earth_too=False):
    """The night around a stretch of road at centre: the stars, the trees, the guardrails (torn
    open at torn_z on the +x side). earth_too: the whole country round it (earth), instead of
    a patch of ground that ends in the dark."""
    cx, cy, cz = centre
    if sky:
        night_sky(s, parent, venue, centre)
    if earth_too:
        earth(s, parent, venue)
    else:
        s.slab('Ground', parent, cx - 170, cx + 170, cy - 1.2, cy - 0.3, cz - 170, cz + 170, (0.02, 0.03, 0.02), rough=1.0, shadows=False)
        s.slab('Verge R', parent, cx + shoulder_x + 6, cx + 120, -0.3, -0.06, cz - half * 2, cz + half * 2, GRASS)
        s.slab('Verge L', parent, cx - 120, cx - shoulder_x - 6, -0.3, -0.06, cz - half * 2, cz + half * 2, GRASS)
        if trees:
            A.plant_roadside(s, s.entity('Roadside trees', parent, (cx, cy, cz)), venue, A.roadside_spots(-110, 110, shoulder_x + 12, 75, 70, 5, y=-0.06))
    s.slab('Shoulder R', parent, cx + shoulder_x, cx + shoulder_x + 6, -0.25, -0.02, cz - half, cz + half, GRAVEL)
    s.slab('Shoulder L', parent, cx - shoulder_x - 6, cx - shoulder_x, -0.25, -0.02, cz - half, cz + half, GRAVEL)
    rail = A.guardrail(venue, 48.0, 'Guardrail48')
    for side in (-1, 1):
        x = cx + side * (shoulder_x + 1.2)
        yaw = 0 if side > 0 else 180
        if side > 0 and torn_z is not None:
            A.model(s, parent, 'Guardrail', rail, (x, 0, torn_z + 7), (0, 0, 0))
            A.model(s, parent, 'Guardrail', rail, (x, 0, torn_z - 7 - 48), (0, 0, 0))
            A.model(s, parent, 'Guardrail, torn', A.guardrail_torn(venue), (x, 0, torn_z), (0, 0, 0))
        else:
            for k in (-1, 0):
                A.model(s, parent, 'Guardrail', rail, (x, 0, cz + k * 48 + (48 if side < 0 else 0)), (0, yaw, 0))
    if not sky:
        return      # (under the engine's own sky, which has its own stars and moon)
    rng = random.Random(int(cx) + 9)
    for i in range(110):
        a, el = rng.uniform(0, 2 * math.pi), math.radians(rng.uniform(8, 80))
        size = rng.choice((0.18, 0.18, 0.25, 0.36))
        b = rng.uniform(2.0, 8.0)
        s.box('Star', parent, (cx + 160 * math.cos(el) * math.cos(a), cy - 8 + 160 * math.sin(el), cz + 160 * math.cos(el) * math.sin(a)), (size, size, size),
              (1, 1, 1), emissive=(0.9, 0.93, 1.0), emissive_intensity=b, shadows=False)
    A.glow_card(s, parent, venue, 'Moon', (cx - 60, cy + 70, cz + 120), 9.0, (0.8, 0.85, 1.0), 2.2, look_rotation((cx - 60, cy + 70, cz + 120), (cx, cy, cz)))
    A.glow_card(s, parent, venue, 'Moon halo', (cx - 60, cy + 70, cz + 120.5), 26.0, (0.3, 0.36, 0.55), 0.6, look_rotation((cx - 60, cy + 70, cz + 120), (cx, cy, cz)))


def beside_hand(hand, yaw, out=1.0, feet=0.6, up=0.18):
    """A camera position by a lying figure's hand (crash_site, the figure laid at yaw): out from the
    body, a little toward the feet, just off the road."""
    a = math.radians(yaw)
    return (hand[0] + math.cos(a) * out + math.sin(a) * feet, hand[1] + up, hand[2] - math.sin(a) * out + math.cos(a) * feet)


def ground_fog(s, parent, venue, centre, size=(40, 1.2, 40), rate=10, name='Ground fog'):
    A.particles(s, parent, name, centre, Shape='Box', BoxSize=list(size), Lifetime=[7.0, 12.0], Speed=[0.05, 0.3], Size=[2.5, 5.0], EndSize=1.6,
                StartColor=[0.55, 0.57, 0.62], StartColor2=[0.4, 0.42, 0.48], EndColor=[0.5, 0.5, 0.55], StartAlpha=0.16, EndAlpha=0.0, FadeIn=0.3,
                Intensity=1.0, Gravity=0.0, Drag=0.2, NoiseStrength=0.25, NoiseFrequency=0.2, Blend='Alpha', Lit=True, EmissionRate=rate, MaxParticles=140,
                Texture=A.tex(venue, 'Puff'), AngularVelocity=[-6, 6])


# ---- the highway --------------------------------------------------------------------------------
def highway():
    V = 'StoryHighway'
    s = Scene(seed=6601)
    s.venue = V
    root = s.group('Highway to the Afterlife: the highway')
    marks = s.group('Markers', root)
    s.info(marks, 'The Highway', 'Drumsmith', outdoor=True, half_width=60, desk_z=-30, sky_time=21.5, moon=0.8, haze=0.5, ride=1.0, ride_until='wreck', lights_from='wreck', quiet_look=False)
    # What the outro is heard by (the song's OutroSeconds in the manifest: the venue plays on that
    # long after the last note): Tools/Venues/story_afterlife_sound.py.
    s.entity('Wreck sound', marks).add({'Type': 'VenueSound', 'Flag': 'wreck', 'Sound': f'Assets/Venues/{V}/Sounds/Wreck.ogg', 'Volume': 0.7})
    deck_y = 1.25
    # The rig is Big-Rigs' band flatbed: +z the bonnet, the tractor's origin at z 11.6, the
    # trailer's kingpin on the fifth wheel at HITCH, its deck 1.25 up and the cab's roof 3.34. The
    # band's spots are on it (placed with the rig, below), so it carries them: the singer at the
    # wheel and the bassist at the passenger window in the cab, the guitarist standing on the
    # cab's roof facing back over the trailer, and the drummer on the deck, toward its front,
    # facing back down the road at the cops.
    HITCH = (0.0, 1.2, 8.67)
    DRUM_AT = (0.0, deck_y + 0.02, 4.7)
    ROOF_AT = (0.0, 3.34, 11.75)
    s.camera_spot('Camera Wide', marks, (12, 4.8, -4.2), (0, 2.2, 7.2), 'Wide', 60)
    s.camera_spot('Camera Crane', marks, (-10, 8.4, 1), (0, 2, 8), 'Crane', 58)
    s.camera_spot('Camera Desk', marks, (4.2, 4.0, 15.7), (0.8, 2.9, 11.9), 'Desk', 28)
    # (Low cameras keep inside the rig's own lanes: the oncoming lane on the left and the slow
    # lane on the right both have traffic coming through them.)
    s.camera_spot('Camera roadside', marks, (4.9, 0.35, -2.5), (-0.5, 2.6, 5.0), 'Custom', 64, 'roadside')
    s.camera_spot('Camera cab roof', marks, (1.6, 4.93, 10.7), (0, 2.0, 2.5), 'Custom', 62, 'cab')
    s.camera_spot('Camera chase bumper', marks, (-1.2, 1.1, -9.5), (0.5, 2.4, 4.5), 'Custom', 40, 'bumper')
    s.camera_spot('Camera grille', marks, (4.4, 0.8, 19.5), (0, 2.8, 6.0), 'Custom', 58, 'grille')
    s.camera_spot('Camera wheel', marks, (2.4, 0.42, 0.93), (1.12, 0.62, 2.2), 'Custom', 66, 'wheel')
    # The singer at the wheel and the bassist at the passenger window are boxed into the cab:
    # the director's own close framings (placed for a stage, from the crowd's side) would be in
    # its walls or behind them. Their close cuts come from these (own/: Director::KeepToOwnSpots),
    # out past the windows, ahead and behind.
    wheel_head, window_head = (-0.62, 2.6, 12.04), (1.25, 2.85, 12.02)
    for i, (eye, fov) in enumerate((((-2.5, 2.75, 13.3), 38), ((-2.7, 3.05, 10.9), 42), ((-3.7, 3.4, 14.8), 30))):
        s.camera_spot(f'Camera singer {i}', marks, eye, wheel_head, 'Close', fov, f'own/vocals_{i}')
    for i, (eye, fov) in enumerate((((3.4, 2.65, 13.2), 38), ((3.1, 3.45, 11.0), 42), ((4.3, 3.1, 14.9), 30))):
        s.camera_spot(f'Camera bassist {i}', marks, eye, window_head, 'Close', fov, f'own/bass_{i}')

    # The road goes by at 48 m/s (1.6 m a frame) until the wreck: what scrolls is the asphalt, its
    # lines, the rails, the poles, the bridges and the trees, each on a loop its own length, and
    # the lot swerves from side to side under the rig (the rig and the band stand still: the
    # world moves). The gig's big moments are one-shots: the rig goes airborne (big_air: the world
    # drops away and comes back), and in the closing bars the world turns about the trailer
    # (trailer_slews). Everything on the road turns with it.
    STEP = 1.6
    # The jump: the rig goes up a ramp of road works (A.work_zone, below) and flies. What it
    # rides is worked out, not drawn: up the ramp to its lip in the first RAMP_FRAMES, then a
    # ballistic arc from there (the peak AIR over the road), the wheels down again at LAND, the
    # springs after that. The world goes down by as much as the rig goes up.
    RAMP, LIP = 12.0, 1.7                               # the ramp's length and the height of its lip
    RAMP_FRAMES, PEAK, AIR = 15, 34, 3.6
    fall = 2.0 * (AIR - LIP) / (PEAK - RAMP_FRAMES) ** 2      # gravity, metres a frame a frame
    LAND = PEAK + math.sqrt(2.0 * AIR / fall)
    JUMP_FRAMES = 86

    def ride(f):
        """How high the rig is off the road, f frames after its nose reaches the ramp's foot."""
        if f <= 0:
            return 0.0
        if f <= RAMP_FRAMES:
            push = fall * (PEAK - RAMP_FRAMES)          # the climb it leaves the lip with
            a = (push * RAMP_FRAMES - LIP) / RAMP_FRAMES ** 2
            return a * f * f + (push - 2 * a * RAMP_FRAMES) * f
        if f < LAND:
            return max(0.0, AIR - 0.5 * fall * (f - PEAK) ** 2)
        t = f - LAND                                    # the springs: down, up, still
        return -0.26 * math.exp(-t / 5.0) * math.sin(t * math.pi / 7.0) if t < 21 else 0.0

    def ride_keys(delay=0, sign=-1.0, frames=JUMP_FRAMES):
        return [(f, (0, round(sign * ride(f - delay), 4), 0)) for f in list(range(0, frames, 2)) + [frames]]
    jump_clip = P.clip(V, 'Jump', JUMP_FRAMES, [P.track('Position', ride_keys()),
                                                P.track('Rotation', [(0, (0, 0, 0)), (6, (3.5, 0, 0)), (RAMP_FRAMES, (5.5, 0, 0)), (PEAK, (1.5, 0, 0.8)), (int(LAND), (-3.5, 0, 0)), (int(LAND) + 7, (0.9, 0, 0)), (JUMP_FRAMES, (0, 0, 0))], 'SmoothStep')])
    slew_clip = P.clip(V, 'Slew', 120, [P.track('Rotation', [(0, (0, 0, 0)), (40, (0, 8, 2)), (120, (0, SLEW_YAW, 0))], 'SmoothStep'),
                                        P.track('Position', [(0, (0, 0, 0)), (120, SLEW_SHIFT)], 'SmoothStep')])
    world = s.group('World', P.play(s, CIR.clocked(s, root, 'Jump', 'big_air', jump_clip, loop=False), 'Slew', 'trailer_slews', slew_clip))
    s.slab('Road bed', world, -11, 11, -0.3, -0.03, -420, 140, ASPHALT, rough=0.95, shadows=False)
    s.slab('Gravel L', world, -15, -11, -0.25, -0.02, -420, 140, GRAVEL)
    s.slab('Gravel R', world, 11, 15, -0.25, -0.02, -420, 140, GRAVEL)
    s.slab('Field L', world, -260, -15, -0.4, -0.1, -420, 140, GRASS)
    s.slab('Field R', world, 15, 260, -0.4, -0.1, -420, 140, GRASS)
    rng = random.Random(7)
    for i in range(18):
        x = rng.choice((-1, 1)) * rng.uniform(150, 240)
        s.box(f'Hill {i}', world, (x, -6, rng.uniform(-400, 120)), (rng.uniform(70, 130), rng.uniform(22, 46), rng.uniform(70, 130)), (0.02, 0.03, 0.025), shape='Sphere', shadows=False)
    # A town's lights far ahead.
    for i in range(40):
        x, y = rng.uniform(-150, 150), rng.uniform(0.5, 9)
        c = rng.choice(((1.0, 0.8, 0.5), (1.0, 0.9, 0.75), (0.7, 0.85, 1.0), (1.0, 0.4, 0.3)))
        s.box('Town light', world, (x, y, 138 + rng.uniform(0, 3)), (0.9, 0.9, 0.2), c, emissive=c, emissive_intensity=6.0, shadows=False)
    s.light('Moon', world, (0, 60, -40), 'Directional', (0.5, 0.58, 0.85), 1.6, 400, rot=(38, 25, 0), shadows=True, show='Static')

    moving = P.between(s, world, 'Road moving', None, 'wreck', 0.2)
    swerve_clip = P.clip(V, 'Swerve', 210, [P.track('Position', [(0, (0, 0, 0)), (45, (2.1, 0, 0)), (110, (-1.9, 0, 0)), (160, (0.9, 0, 0)), (210, (0, 0, 0))], 'SmoothStep'),
                                             P.track('Rotation', [(0, (0, 0, 0)), (22, (0, -1.6, -0.4)), (44, (0, -0.3, -1.4)), (78, (0, 1.5, 0.4)), (106, (0, 0.4, 1.6)), (135, (0, -1.1, 0)), (158, (0, -0.4, -0.9)), (185, (0, 0.5, 0.4)), (210, (0, 0, 0))], 'SmoothStep')])
    swerving = P.looping(s, moving, 'Swerve', swerve_clip)

    # Keep the work-zone lane and overhead clearance free for the ramp jump.
    normal_traffic = s.story('Outside the work zone', swerving, 'ramp_ahead', False, 0.1, unless='jump_clear')

    def scroll(name, metres, parent=swerving):
        """A body under the swerve that runs back past the rig, looping every metres."""
        frames = int(round(metres / STEP))
        return P.looping(s, parent, name, P.clip(V, 'Road' + name, frames, [P.track('Position', [(0, (0, 0, 0)), (frames, (0, 0, -metres))])]))

    def lane(parent, torn_z=None):
        """The asphalt, its lines, delineators and guardrails (torn_z: the right-hand rail torn
        open there, where the rig went through)."""
        # The asphalt goes by with the lines: its texture repeats every 4 m, the loop is 16.
        textured(s.slab('Asphalt', parent, -11, 11, -0.2, 0.0, -432, 152, (1, 1, 1), rough=0.9), V, 'Asphalt', (5.5, 146))
        for x in (-10.7, 10.55):
            s.slab('Edge line', parent, x, x + 0.15, 0.0, 0.01, -432, 152, LINE_WHITE, shadows=False)
        for x in (-0.2, 0.08):
            s.slab('Centre line', parent, x, x + 0.12, 0.0, 0.01, -432, 152, LINE_YELLOW, shadows=False)
        for k in range(-26, 10):
            for x in (-5.4, 5.4):
                s.slab('Dash', parent, x - 0.07, x + 0.07, 0.0, 0.012, k * 16, k * 16 + 4, LINE_WHITE, shadows=False)
            for side in (-1, 1):
                if side > 0 and torn_z is not None and abs(k * 16 + 8 - torn_z) < 10:
                    continue        # (flattened by the rig)
                s.box('Delineator', parent, (side * 11.6, 0.5, k * 16 + 8), (0.06, 1.0, 0.03), (0.9, 0.9, 0.9), emissive=(1.0, 0.6, 0.1), emissive_intensity=1.6, shadows=False)
        rail = A.guardrail(V, 96.0)
        for k in range(-5, 2):
            if torn_z is not None and k * 96 + 7 < torn_z < k * 96 + 89:
                before, after = torn_z - 7 - k * 96, k * 96 + 96 - (torn_z + 7)
                A.model(s, parent, 'Guardrail', A.guardrail(V, before, f'Guardrail{before:g}'), (15.4, 0, k * 96), shadows=False)
                A.model(s, parent, 'Guardrail, torn', A.guardrail_torn(V), (15.4, 0, torn_z))
                A.model(s, parent, 'Guardrail', A.guardrail(V, after, f'Guardrail{after:g}'), (15.4, 0, torn_z + 7), shadows=False)
            else:
                A.model(s, parent, 'Guardrail', rail, (15.4, 0, k * 96), shadows=False)
            A.model(s, parent, 'Guardrail', rail, (-15.4, 0, k * 96 + 96), (0, 180, 0), shadows=False)

    def poles(parent):
        for k in range(-8, 4):
            z = k * 48
            for side in (-1, 1):
                x = side * 13
                s.box('Pole', parent, (x, 5, z), (0.25, 10, 0.25), STEEL, shadows=False, shape='Cylinder')
                s.box('Arm', parent, (x - side * 1.5, 9.9, z), (3.0, 0.15, 0.2), STEEL, shadows=False)
                s.box('Lamp', parent, (x - side * 2.8, 9.75, z), (0.6, 0.12, 0.3), (1, 0.85, 0.55), emissive=(1, 0.8, 0.5), emissive_intensity=9.0, shadows=False)
                A.glow_card(s, parent, V, 'Lamp glare', (x - side * 2.8, 9.6, z), 1.6, (1.0, 0.75, 0.4), 2.5, (90, 0, 0))
                if -2 <= k <= 1:
                    s.light('Pole light', parent, (x - side * 2.8, 9.5, z), 'Spot', (1.0, 0.78, 0.5), 1500.0, 28, rot=(90, 0, 0), inner=32, outer=58)

    # Mile 66, where it ends: the crash site (CRASH_LYING), on the road a few seconds on from
    # where the rig was, the cops pulled up behind it. The rig goes over at the right edge and
    # through the guardrail there (WRECK_AT, TORN_Z), the band thrown onto the road beside it. The
    # billboard stands in a clearing off the right shoulder, past the torn rail.
    W = (-2.5, 0.0, 34.0)
    WRECK_AT = (9.0, 0.0, -1.0)         # (as Free Bird has it: the wreck's gear thrown short of the bodies)
    TORN_Z = W[2] + 8.0
    # The pursuit pulled up behind it, strung out across the lanes ((x, z, yaw) from the site).
    PULLED_UP = ((-3.5, -19.0, 14), (5.5, -16.0, -20), (-1.0, -28.0, 6), (6.5, -31.0, -12))

    def trees(parent, clearing=False):
        # Real trees (MitchTree), the same twenty-two every 96 m.
        spots = A.roadside_spots(-480, 192, 19, 72, 22, 5, period=96.0, y=-0.12)
        if clearing:
            spots = [at for at in spots if not (13 < at[0] < 40 and W[2] - 10 < at[2] < W[2] + 30)]
        A.plant_roadside(s, parent, V, spots)
        for k in range(-4, 2):
            s.box('Reflector post', parent, (17.5, 0.6, k * 96 + 30), (0.08, 1.2, 0.08), STEEL, shadows=False)

    lane(scroll('Dashes', 16.0))
    poles(scroll('Poles', 48.0))
    trees(scroll('Trees', 96.0))
    # A bridge overhead every 192 m: its lights flick down the deck as it goes over.
    bridges = scroll('Bridges', 192.0, normal_traffic)
    for k in (-2, -1, 0, 1):
        z = k * 192 + 120
        A.model(s, bridges, 'Overpass', A.overpass(V), (0, 0, z), shadows=False)
        for x in (-7.0, 0.0, 7.0):
            s.box('Bridge lamp', bridges, (x, 7.02, z), (0.5, 0.05, 6.0), (1, 0.95, 0.8), emissive=(1, 0.93, 0.75), emissive_intensity=7.0, shadows=False)
        if k in (-1, 0):
            s.light('Bridge light', bridges, (0, 6.8, z), 'Point', (1.0, 0.92, 0.75), 900.0, 16)
    # The air going by: dust and grit streaking back past the deck.
    A.particles(s, moving, 'Road grit', (0, 1.8, 34), (-90, 0, 0), Shape='Box', BoxSize=[30, 4, 6], Lifetime=[0.9, 1.5], Speed=[44, 52], Size=[0.02, 0.06],
                StartColor=[0.9, 0.8, 0.65], StartColor2=[0.6, 0.6, 0.65], EndColor=[0.5, 0.5, 0.5], StartAlpha=0.6, EndAlpha=0.0, Intensity=1.8, Gravity=0.0, Drag=0.0,
                NoiseStrength=0.3, Blend='Additive', EmissionRate=90, MaxParticles=180, Alignment='Stretched', StretchFactor=0.07, FadeIn=0.1)

    # Traffic. Oncoming, down the far lane at the two speeds added together: headlights out of the
    # dark and gone. The slow lane on the right, falling behind.
    wheel_clip = wheel_spin(V)

    def truck_axle(parent, index, z, y=0.55):
        # (Every wheel turns as wheel_spin says, whatever its road speed: see there.)
        wheels = P.looping(s, parent, 'Axle wheels', wheel_clip, (0, y, z))
        A.vehicle(s, wheels, 'RigDualWheels' if index else 'RigSteerWheels')

    def vehicle(parent, name, kind, at, yaw, lights=True):
        """kind: 'semi', or one of the fleet's cars (A.TRAFFIC)."""
        g = s.entity(name, parent, at, (0, yaw, 0))
        if kind == 'semi':
            A.vehicle(s, g, 'FreightCabover')
            for i, z in enumerate((1.08, -2.19, -3.48, -10.55, -11.84)):
                truck_axle(g, i, z)
            head = (0.97, 1.31, 2.38)
        else:
            A.vehicle(s, g, kind)
            A.vehicle_lamps(s, g, V, kind)
            head = A.lamp(kind, 'Headlamp')
        if lights:
            A.headlights(s, g, head[0], head[1], head[2] + 0.2, 2200.0, 70, inner=14, outer=34)
        return g

    oncoming = P.looping(s, swerving, 'Oncoming', P.clip(V, 'RoadOncoming', 240, [P.track('Position', [(0, (0, 0, 0)), (240, (0, 0, -624))])]))
    for i, (z, kind, x) in enumerate(((-250, 'Caprice', -8.6), (-120, 'semi', -8.7), (40, 'Corvette', -8.4), (150, 'Civic', -8.7), (280, 'Caravan', -8.5))):
        for copy in (0, 1):
            vehicle(oncoming, f'Oncoming {i}', kind, (x, 0, z + copy * 624), 180, lights=copy == 0 or i % 2 == 0)
    slow = P.looping(s, normal_traffic, 'Slow lane', P.clip(V, 'RoadSlow', 600, [P.track('Position', [(0, (0, 0, 0)), (600, (0, 0, -360))])]))
    for i, (z, kind) in enumerate(((-150, 'C10'), (-30, 'semi'), (110, 'Caprice'))):
        for copy in (0, 1):
            vehicle(slow, f'Slow traffic {i}', kind, (8.7, 0, z + copy * 360), 0, lights=False)

    # An opposing cabover in the inside lane. Cue both its headlights and
    # the pan from the bridge so a seek lands on the same pass as a playthrough.
    freight_at = (-4.35, 0, 274)
    freight_clip = P.clip(V, 'FreightPass', 300, [
        P.track('Position', [(0, (0, 0, 0)), (300, (0, 0, -760))]),
        P.track('Rotation', [(0, (0, 0, 0)), (86, (0, 0, 0)), (100, (0.25, -1.6, 0)),
                             (107, (0.15, -1.1, 1.1)), (119, (-0.2, 0.7, -0.45)),
                             (135, (0, 0, 0))], 'SmoothStep')])
    pass_by = CIR.clocked(s, P.between(s, moving, 'Freight pass', 'freight_pass', None, 0.02, freight_at),
                     'Passing freight', 'freight_pass', freight_clip, freight_at, loop=False)
    cabover = vehicle(pass_by, 'Pacific Freight', 'semi', (0, 0, 0), 180)
    P.actor(s, cabover, 'Freight driver', 'Son_01', '02_A', (-0.59, 1.70, 1.10), 0, 'Seated',
            SeatHeight=0.61, LeftArm=P.arm(hand=(-0.17, 1.01, 0.47), grip=0.85),
            RightArm=P.arm(hand=(0.17, 1.01, 0.47), grip=0.85))
    s.light('Freight dash', cabover, (-0.59, 2.85, 1.82), 'Point', (1, 0.73, 0.48), 4.0, 1.7)

    # Stopped: the markings, rails, poles and trees where they stood.
    still = P.between(s, world, 'Road stopped', 'wreck', None, 0.2)
    lane(still, TORN_Z)
    poles(still)
    trees(still, clearing=True)

    # The rig: the tractor, and the flatbed trailer hung on the tractor's fifth wheel. The wheels
    # keep to the road (each axle's own travel through the jump); each body rides its springs over
    # them: bumps in the road on a loop (the trailer's tandem takes each a moment after the
    # tractor's drive axles), a dip as the ramp loads them and a slam as the rig lands. The
    # trailer swings on the kingpin after the road's curves, with a wobble of its own on top. The
    # band's spots are on the bodies, so the members ride all of it, each on a spring of their
    # own (Band::Carry: a jolt throws them a little and they come down again).
    rig = P.between(s, root, 'Band rig', None, 'wreck', 0.05)

    def rel(p, o):
        return (p[0] - o[0], p[1] - o[1], p[2] - o[2])

    BUMPS = 300
    BUMP_AT = ((10, 0.7), (31, 1.0), (47, 0.5), (78, 0.9), (109, 0.6), (124, 1.0), (160, 0.7), (190, 0.5), (205, 0.9), (238, 0.8), (262, 0.6), (280, 0.4))

    def bumps(name, height, pitch, roll, delay=0):
        """A loop of road bumps for a body on its springs: each kicks it up, drops it past rest and
        lets it settle, pitching it (the end over the axles that hit) and rolling it a little,
        one way then the other. Sharp (joined straight), so that the band's springs feel them."""
        heave, turn = [(0, (0, 0, 0))], [(0, (0, 0, 0))]
        for i, (f, a) in enumerate(BUMP_AT):
            side = 1 if i % 2 else -1
            for df, h in ((0, 0.0), (2, 1.0), (5, -0.5), (9, 0.15), (13, 0.0)):
                heave.append((f + delay + df, (0, round(height * a * h, 4), 0)))
                turn.append((f + delay + df, (round(pitch * a * h, 3), 0, round(side * roll * a * h, 3))))
        heave.append((BUMPS, (0, 0, 0)))
        turn.append((BUMPS, (0, 0, 0)))
        return P.clip(V, name, BUMPS, [P.track('Position', heave), P.track('Rotation', turn)])

    def loaded(name, delay, depth):
        """A body through the jump (big_air, delay frames after the tractor's nose): it squats as
        its axles go up the ramp, slams down as they land and bounces out of it."""
        t, land = RAMP_FRAMES + delay, int(LAND) + delay
        keys = ((0, 0.0), (t - 4, 0.0), (t - 1, -0.45), (t + 3, 0.25), (t + 8, 0.0), (land - 1, 0.0), (land + 2, -1.0), (land + 6, 0.5),
                (land + 11, -0.18), (land + 17, 0.06), (land + 23, 0.0), (JUMP_FRAMES + 10, 0.0))
        return P.clip(V, name, JUMP_FRAMES + 10, [P.track('Position', [(f, (0, round(depth * h, 4), 0)) for f, h in keys])])

    def smooth_at(keys, f):
        """A SmoothStep-keyed track's value at frame f (keys (frame, value), looping)."""
        period = keys[-1][0]
        f %= period
        for (f0, v0), (f1, v1) in zip(keys, keys[1:]):
            if f0 <= f <= f1:
                u = (f - f0) / max(f1 - f0, 1)
                return v0 + (v1 - v0) * u * u * (3 - 2 * u)
        return keys[-1][1]

    # The trailer's swing on the kingpin: the road's swerve (the world's yaw, which is the rig
    # steering the other way), the trailer a beat behind the tractor through each curve and
    # leaning out of it.
    SWERVE_YAW = [(0, 0.0), (22, -1.6), (44, -0.3), (78, 1.5), (106, 0.4), (135, -1.1), (158, -0.4), (185, 0.5), (210, 0.0)]
    LAG = 12
    sway_keys = [(f, (0, round(0.75 * smooth_at(SWERVE_YAW, f - LAG), 3), round(-0.45 * smooth_at(SWERVE_YAW, f - LAG - 4), 3))) for f in range(0, 211, 6)]
    sway_clip = P.clip(V, 'TrailerSway', 210, [P.track('Rotation', sway_keys, 'SmoothStep')])
    wobble_clip = P.clip(V, 'TrailerWobble', 46, [P.track('Rotation', [(0, (0, 0, 0)), (11, (0, 0.45, -0.3)), (23, (0, 0, 0)), (34, (0, -0.45, 0.3)), (46, (0, 0, 0))], 'SmoothStep')])
    trailer = P.looping(s, P.looping(s, rig, 'Trailer swing', sway_clip, HITCH), 'Trailer wobble', wobble_clip)

    # The tractor: its axles on the road, its body on its springs.
    TRACTOR_MID = (0.0, 1.0, 11.6)
    # (The cab leans out of each of the road's curves on its springs, as the trailer swings.)
    lean_clip = P.clip(V, 'TractorLean', 210, [P.track('Rotation', [(f, (0, 0, round(-0.7 * smooth_at(SWERVE_YAW, f - 6), 3))) for f in range(0, 211, 6)], 'SmoothStep')])
    tractor = P.looping(s, P.looping(s, CIR.clocked(s, rig, 'Tractor through the jump', 'big_air', loaded('TractorLoaded', 2, 0.1), loop=False), 'Tractor leaning', lean_clip, TRACTOR_MID),
                        'Tractor on its springs', bumps('TractorBumps', 0.03, -0.5, 0.6))
    A.vehicle(s, s.entity('Tractor origin', tractor, rel((0, 0, 11.6), TRACTOR_MID)), 'BandTractor')
    # The trailer: its tandem on the road (swinging with it), its body on its springs, pitching
    # about the kingpin.
    trailer_body = P.looping(s, CIR.clocked(s, trailer, 'Trailer through the jump', 'big_air', loaded('TrailerLoaded', 7, 0.12), loop=False), 'Trailer on its springs',
                             bumps('TrailerBumps', 0.035, 0.6, 0.5, delay=4))
    A.vehicle(s, s.entity('Trailer at the kingpin', trailer_body), 'BandTrailer')
    for i, z in enumerate((14.22, 9.41, 8.12, 3.37, 2.08)):
        delay = round((14.22 - z) / STEP)
        contact = round(LAND) + delay
        travel = P.clip(V, f'AxleTravel{i}', JUMP_FRAMES, [P.track('Position', [
            (0, (0, 0, 0)), (RAMP_FRAMES + delay, (0, 0, 0)), (PEAK + delay, (0, -0.08, 0)),
            (contact, (0, -0.08, 0)), (contact + 3, (0, 0.13, 0)), (contact + 9, (0, -0.04, 0)),
            (contact + 16, (0, 0.015, 0)), (JUMP_FRAMES, (0, 0, 0))], 'SmoothStep')])
        if z > HITCH[2] - 1.0:
            truck_axle(CIR.clocked(s, rig, 'Axle suspension', 'big_air', travel, loop=False), i, z)
        else:
            truck_axle(CIR.clocked(s, trailer, 'Axle suspension', 'big_air', travel, loop=False), i, z - HITCH[2], 0.55 - HITCH[1])

    # The band on it.
    s.spot(trailer_body, 'Drummer', rel(DRUM_AT, HITCH))
    # The singer leaves the wheel near the end (pedal_jammed): a mic stand jammed down on the gas
    # pedal, wedged against the seat back, and out through the window onto the bonnet, one foot on
    # it and the other at the foot of the windscreen, leaning into the wind with a stand in both
    # hands. The band's singer goes from the seat (their spot dropped far underground, which
    # Band::Carry takes as a jump, not a throw) and a figure dressed as them stands on the bonnet.
    leaves = P.clip(V, 'SingerLeavesTheWheel', 2, [P.track('Position', [(0, (0, 0, 0)), (1, (0, -4000, 0)), (2, (0, -4000, 0))])])
    s.spot(CIR.clocked(s, tractor, 'Singer at the wheel', 'pedal_jammed', leaves, loop=False), 'Vocals', rel((-0.59, 1.40, 12.04), TRACTOR_MID), yaw=180, seat_height=0.61)
    s.spot(tractor, 'Bass', rel((1.13, 1.73, 12.02), TRACTOR_MID), yaw=-90, seat_height=0.56)
    s.spot(tractor, 'Guitar', rel(ROOF_AT, TRACTOR_MID), power=True, gear=False)

    # The stand on the gas (BandTractor, measured: the floor 1.38 up, the pedals' pads at z 12.67,
    # the gas the right-hand one at x -0.45; the seat's cushion 1.93 up to z 12.34, its back's top
    # 2.5 up at z 11.8). Its base is down on the pad, its pole up over the cushion's front edge to
    # the top of the back.
    MIC_STAND = 'Assets/Models/Instruments/Runtime/MicStand.obj'

    def stand_turn(u):
        """Euler degrees turning a stand's pole (its +y) along the direction u."""
        n = math.sqrt(sum(c * c for c in u))
        x, y, z = (c / n for c in u)
        return (math.degrees(math.acos(max(-1.0, min(1.0, y)))), math.degrees(math.atan2(x, z)), 0.0)

    jammed = P.between(s, tractor, 'Mic stand on the gas', 'pedal_jammed', None, 0.01)
    A.model(s, jammed, 'Mic stand, jammed', MIC_STAND, rel((-0.42, 1.43, 12.74), TRACTOR_MID), stand_turn((-0.05, 1.0, -0.8)))
    # (The footwell is black at night: a warm lamp from the passenger side onto the pedals.)
    s.light('Footwell', jammed, rel((0.3, 1.95, 12.8), TRACTOR_MID), 'Spot', (1.0, 0.68, 0.45), 30.0, 2.5,
            rot=look_rotation((0.3, 1.95, 12.8), (-0.45, 1.45, 12.67)), inner=26, outer=50)

    # The singer on the bonnet (its top 2.2 up at the windscreen's foot, z 13.26, falling 9.6 cm a
    # metre to 2.02 at its nose; the windscreen leans back about 18 degrees from there).
    def hood_y(z):
        return 2.20 - 0.096 * (z - 13.26)
    HOOD_AT = (0.0, hood_y(13.85), 13.85)
    # A deep lunge into the wind: the front foot on the bonnet a little ahead of the hips, the
    # knee well bent over it; the back leg reaching straight back, the ball of the foot pushed
    # against the windscreen's foot, the heel up. (The legs are IK: the hips go no higher than
    # the back leg reaches, so that leg is the straight one.)
    front = P.to_figure(HOOD_AT, 0, (0.14, hood_y(14.15), 14.15))
    back = P.to_figure(HOOD_AT, 0, (-0.15, 2.24, 13.12))
    # The mic in the right hand, up under the chin (about where the mouth is with the trunk bowed
    # 40 degrees and the head up), the handle pointing back up at the lips; the left arm out wide
    # for balance.
    mouth = (0.0, 1.0, 0.6)
    mic_hand = (0.04, 0.88, 0.72)
    aim = tuple(m - h for m, h in zip(mouth, mic_hand))
    surfing = P.between(s, tractor, 'Singer on the bonnet', 'pedal_jammed', None, 0.01)
    # Riding the bonnet: on the tractor's bumps (its TractorBumps loop, the same 300 frames from
    # the start) the body is thrown off its planted feet (Offset moves the hips and all above;
    # the feet and the mic hand stay where they are) and comes back, and the wind leans them
    # back and forth on a loop of its own (six to the bumps' one).
    bob = [(0, (0, 0, 0))]
    for f, a in BUMP_AT:
        for df, (dy, dz) in ((0, (0, 0)), (2, (-0.04, -0.015)), (5, (0.02, 0.02)), (9, (-0.012, -0.006)), (14, (0, 0))):
            bob.append((f + df, (0, round(a * dy, 4), round(a * dz, 4))))
    bob.append((BUMPS, (0, 0, 0)))
    gust = [(k * 50 + df, v) for k in range(6) for df, v in ((0, 26.0), (12, 31.0), (24, 25.0), (37, 29.5))] + [(BUMPS, 26.0)]
    sway = [(k * 50 + df, v) for k in range(6) for df, v in ((0, 0.0), (17, -2.5), (33, 2.0))] + [(BUMPS, 0.0)]
    ride_clip = P.clip(V, 'BonnetRide', BUMPS, [P.ftrack('Offset', bob), P.ftrack('Lean', gust, 'SmoothStep'), P.ftrack('Side', sway, 'SmoothStep')])
    singer = P.actor(s, surfing, 'Singer on the bonnet', 'Rigged', '01_A', rel(HOOD_AT, TRACTOR_MID), 0, 'Standing', motion=ride_clip, dress='Vocals',
                     Crouch=0.2, Bow=30.0, Lean=26.0, Nod=-35.0, Mouth=0.65,
                     RightLeg=P.leg(foot=front, knee=(0.25, 0.4, 1)),
                     LeftLeg=P.leg(toe=55.0, foot=back, knee=(-0.2, -0.3, 1)),
                     RightArm=P.arm(hand=mic_hand, pole=(1, -1, 0), fingers=(-0.79, 0.47, 0.4), palm=(-0.61, -0.61, -0.51), grip=0.9),
                     LeftArm=P.arm(hand=(-0.72, 0.95, 0.2), pole=(-0.3, -1, -0.5), fingers=(-1, 0, 0.2), palm=(0, -1, 0), grip=0.2))
    head_bang(singer, 8.0, 0.5)
    # (The band's own hand mic: a handle and a ball grille 11 cm up it.)
    mic = s.entity('Hand mic', surfing, rel(add3(HOOD_AT, mic_hand), TRACTOR_MID), stand_turn(aim))
    s.box('Mic handle', mic, (0, 0, 0), (0.032, 0.17, 0.032), (0.05, 0.05, 0.06), shape='Cylinder', shadows=False)
    s.box('Mic grille', mic, (0, 0.11, 0), (0.062, 0.062, 0.062), (0.75, 0.75, 0.78), shape='Sphere', metallic=0.8, shadows=False)
    # Lit from the cab roof's front edge and, cooler, from ahead (the road's own lights).
    bonnet_chest = add3(HOOD_AT, (0, 1.0, 0.35))
    for name, at, c, level in (('Bonnet key', (-1.2, 3.9, 12.9), (1.0, 0.74, 0.52), 120.0), ('Bonnet fill', (1.1, 2.4, 16.8), (0.6, 0.72, 1.0), 45.0)):
        s.light(name, surfing, rel(at, TRACTOR_MID), 'Spot', c, level, 7, rot=look_rotation(at, bonnet_chest), inner=24, outer=46)

    # A cool spill over the passenger door, a warm key on the roof guitarist from over the deck,
    # and the drummer lit from the deck's back corners (they face the cops, away from the truss):
    # the faces stay readable as the overhead street lights sweep past.
    s.light('Dash glow on the singer', tractor, rel((-0.45, 2.35, 12.85), TRACTOR_MID), 'Point', (1.0, 0.72, 0.5), 9.0, 1.8)
    s.light('Cab side fill', tractor, rel((3.0, 3.7, 12.9), TRACTOR_MID), 'Spot', (0.68, 0.80, 1.0), 56, 7, rot=look_rotation((3.0, 3.7, 12.9), (1.1, 2.7, 12.0)), inner=26, outer=49)
    roof_key = (-1.6, 5.4, 8.9)
    s.light('Roof key', trailer_body, rel(roof_key, HITCH), 'Spot', (1.0, 0.74, 0.52), 90, 8, rot=look_rotation(roof_key, (0, 4.4, ROOF_AT[2])), inner=24, outer=46)
    for i, x in enumerate((-1.05, 1.05)):
        lamp = (x, deck_y + 0.35, 1.25)
        s.light(f'Deck footlight {i}', trailer_body, rel(lamp, HITCH), 'Spot', (1.0, 0.55, 0.32) if i else (0.55, 0.6, 1.0), 260.0, 9,
                rot=look_rotation(lamp, (0, 2.1, DRUM_AT[2])), inner=24, outer=46, show='Wash', group=i + 4)
    for i, x in enumerate((-1.0, -0.35, 0.35, 1.0)):
        lamp = (x, 4.42, 8.74)
        s.light(f'Truss wash {i}', trailer_body, rel(lamp, HITCH), 'Spot', (0.6, 0.6, 1.0) if i % 2 else (1.0, 0.5, 0.3), 650.0, 14,
                rot=look_rotation(lamp, (x * 0.5, deck_y + 1, DRUM_AT[2] - 1.5)), inner=22, outer=40, show='Wash', group=i)
    for i, x in enumerate((-1.20, 1.20)):
        s.light(f'Deck beam {i}', trailer_body, rel((x, 4.44, 8.74), HITCH), 'Spot', (1.0, 0.3, 0.2) if i else (0.3, 0.5, 1.0), 2500.0, 40, rot=(-20, 180 + x * 8, 0), inner=4, outer=9, show='Beam', group=i)
        s.light(f'Deck strobe {i}', trailer_body, rel((x * 0.4, 4.42, 8.74), HITCH), 'Point', (1, 1, 1), 900.0, 16, show='Strobe', group=i)
    for x in (-0.98, 0.98):
        A.glow_card(s, tractor, V, 'Tractor headlight', rel((x, 1.23, 15.51), TRACTOR_MID), 0.8, (1.0, 0.95, 0.8), 6.0)
    s.light('Tractor headlights', tractor, rel((0, 1.23, 15.55), TRACTOR_MID), 'Spot', (1.0, 0.93, 0.8), 6000.0, 90, rot=(6, 0, 0), inner=14, outer=32)
    for x in (-1.01, 1.01):
        A.particles(s, tractor, 'Stack smoke', rel((x, 3.96, 10.81), TRACTOR_MID), Shape='Cone', ConeAngle=8, ShapeRadius=0.1, Lifetime=[0.8, 1.4],
                    Speed=[2, 4], Size=[0.3, 0.6], EndSize=4.0, StartColor=[0.12, 0.12, 0.13], StartColor2=[0.2, 0.2, 0.2], EndColor=[0.1, 0.1, 0.1], StartAlpha=0.5,
                    EndAlpha=0.0, Gravity=0.0, Drag=0.2, NoiseStrength=0.4, Blend='Alpha', EmissionRate=14, MaxParticles=40, Texture=A.tex(V, 'Puff'), SimulationSpace='Local')
        # Fire out of the stacks and up off the deck's corners on the big moments.
        for name, parent, at, speed in (('Stack fire', tractor, rel((x, 3.96, 10.81), TRACTOR_MID), (9, 14)), ('Deck jet', trailer_body, rel((x * 1.17, deck_y + 0.06, 6.8), HITCH), (14, 20))):
            jet = A.particles(s, parent, name, at, Shape='Cone', ConeAngle=7, ShapeRadius=0.12, Lifetime=[0.35, 0.7], Speed=list(speed), Size=[0.5, 0.9], EndSize=0.4,
                              StartColor=[1.0, 0.8, 0.3], StartColor2=[1.0, 0.45, 0.08], EndColor=[0.8, 0.1, 0.01], Intensity=7.0, Gravity=0.2, Drag=0.6, NoiseStrength=0.5,
                              Blend='Additive', EmissionRate=0, BurstCount=0, MaxParticles=300, Texture=A.tex(V, 'Puff'), FadeIn=0.05)
            jet.add({'Type': 'VenueAccent', 'Beats': 4, 'Particles': 220})
    # A chain dragging off each back corner, throwing sparks down the road (swinging with the
    # trailer, not bouncing with its body: it lies on the road).
    ground_contact = P.clip(V, 'ChainContact', JUMP_FRAMES, [P.track('Position', [
        (0, (0, 0, 0)), (RAMP_FRAMES, (0, 0, 0)), (RAMP_FRAMES + 1, (0, -1000, 0)),
        (int(LAND), (0, -1000, 0)), (int(LAND) + 1, (0, 0, 0)), (JUMP_FRAMES, (0, 0, 0))])])
    scrape = CIR.clocked(s, trailer, 'Chains against asphalt', 'big_air', ground_contact, loop=False)
    for x in (-1.22, 1.22):
        s.box('Drag chain', trailer, rel((x, 0.42, 0.8), HITCH), (0.05, 0.9, 0.05), (0.2, 0.2, 0.22), rot=(-35, 0, 0), metallic=0.8, shadows=False)
        A.particles(s, scrape, 'Chain sparks', rel((x, 0.06, 0.52), HITCH), (-78, 0, 0), Shape='Cone', ConeAngle=16, ShapeRadius=0.05, Lifetime=[0.35, 0.9], Speed=[14, 34], Size=[0.03, 0.07],
                    StartColor=[1.0, 0.85, 0.5], StartColor2=[1.0, 0.55, 0.15], EndColor=[0.9, 0.2, 0.02], Intensity=7.0, Gravity=0.6, Drag=0.1, NoiseStrength=0.8,
                    Blend='Additive', EmissionRate=70, MaxParticles=90, Alignment='Stretched', StretchFactor=0.035, FadeIn=0.02)
        s.light('Spark light', scrape, rel((x, 0.5, 0.40), HITCH), 'Point', (1.0, 0.6, 0.2), 30.0, 5)

    # The cruiser behind, the cop at the wheel: driving, then the radio, then the nod. (It holds
    # its place behind the rig, so the shots through its windscreen hold theirs.)
    car_at = (0.0, 0.0, -13.0)
    # It takes the ramp after the rig does (big_air): the same ride, as much later as it is behind.
    HOP_LATER = int(round((15.5 - (car_at[2] + 2.8)) / STEP))
    # (Gone at the wreck: it pulls up by it, with the rest of the pursuit, below.)
    chasing = P.between(s, world, 'Cruiser chasing', None, 'wreck', 0.05, car_at)
    hop = CIR.clocked(s, chasing, 'Cruiser hop', 'big_air', P.clip(V, 'CruiserHop', JUMP_FRAMES + HOP_LATER, [P.track('Position', ride_keys(HOP_LATER, 1.0, JUMP_FRAMES + HOP_LATER))]), loop=False)
    cruiser(s, hop, V, car_at)
    # Its exhaust while the road is going by (every police car's here: it says which way it is
    # going). Thin: each trail hangs in the full headlights of the car behind.
    EXHAUST = 0.28
    A.exhaust(s, P.between(s, hop, 'Cruiser exhaust', None, 'wreck', 0.2, car_at), V, add3(car_at, A.tailpipe()), alpha=EXHAUST)
    # The cop at the wheel (skinned: driver()): driving, then the radio's handset up at his mouth
    # in the right hand, then the nod, and from it to the end his head going with the band on
    # every beat (head_bang), more as the playing is better.
    face = driver_face()
    seat = (car_at[0] + face[0], 0.0, car_at[2] + face[2])
    car = s.entity('The cop', hop, car_at)
    for flag_after, flag_before, pose, label in ((None, 'cop_radio', {}, 'Cop driving'),
                                                 ('cop_radio', 'cop_nods', dict(Nod=6.0, HeadTurn=12.0, RightArm=P.arm(hand=(0.07, face[1] - A.VEHICLES['PatrolCruiser']['Heel'] - 0.1, 0.2), pole=(1, -0.6, 0), grip=0.9)), 'Cop on the radio'),
                                                 ('cop_nods', None, dict(Nod=4.0), 'Cop nodding')):
        cop = driver(s, P.between(s, car, label, flag_after, flag_before, 0.05, face), **pose)
        if flag_after == 'cop_nods':
            head_bang(cop, 20.0)
    s.light('Dash glow', hop, (seat[0], 1.0, seat[2] + 0.6), 'Point', (0.4, 0.6, 1.0), 2.5, 2.5)
    s.light('Stage spill on the cop', hop, (seat[0] + 0.3, 1.5, car_at[2] + 1.3), 'Point', (1.0, 0.7, 0.6), 3.5, 3.5)
    def manned(parent, name, yaw=0.0, kind=None, driving=False, rocking=None):
        """A police car with its cop at the wheel; rocking: the flag from which the cop's head goes
        with the band on the beat."""
        car = cruiser(s, parent, V, (0, 0, 0), yaw, name=name, kind=kind)
        if rocking:
            driver(s, P.between(s, car, 'Cop driving', None, rocking, 0.05), kind)
            head_bang(driver(s, P.between(s, car, 'Cop rocking', rocking, None, 0.05), kind), 24.0)
        else:
            driver(s, car, kind)
        if driving:
            A.exhaust(s, car, V, A.tailpipe(kind), alpha=EXHAUST)
        return car

    # The rest of the pursuit: four more strung out behind (two cruisers, two of the highway
    # patrol's Trail Dusters), fighting for a way past: they surge up level with the deck and fall
    # back. They pull up where they are when the rig goes over.
    stopped = P.between(s, world, 'Pursuit, pulled up', 'wreck', None, 0.2)
    for i, (x, z, yaw, park, surge) in enumerate(((-5.6, -20.0, 3, -24, 13.0), (5.0, -17.0, -4, 18, 10.0), (-2.4, -29.0, 2, 30, 7.0), (5.4, -34.0, -3, -14, 10.0))):
        frames = 150 + 34 * i
        side = 1 if x > 0 else -1
        weave = P.clip(V, f'Weave{i}', frames, [P.track('Position', [(0, (0, 0, 0)), (frames // 4, (-side * 1.2, 0, surge * 0.5)), (frames // 2, (side * 0.6, 0, surge)),
                                                                    (3 * frames // 4, (-side * 0.9, 0, surge * 0.3)), (frames, (0, 0, 0))], 'SmoothStep'),
                                                 P.track('Rotation', [(0, (0, 0, 0)), (frames // 8, (-1.4, -side * 7, side * 1.8)), (3 * frames // 8, (1.1, side * 8, -side * 2.5)), (5 * frames // 8, (1.6, -side * 6, side * 2.1)),
                                                                    (7 * frames // 8, (-0.8, side * 5, -side * 1.3)), (frames, (0, 0, 0))], 'SmoothStep')])
        kind = 'TrailDuster' if i % 2 else None
        # (By the guitar solo the whole pursuit is rocking out at the wheel.)
        manned(P.looping(s, swerving, f'Pursuit {i}', weave, (x, 0, z)), f'Cruiser {i + 2}', yaw, kind, driving=True, rocking='heli_again')
        px, pz, ppark = PULLED_UP[i]
        manned(s.entity(f'Pursuit {i}, pulled up', stopped, (W[0] + px, 0, W[2] + pz), (0, ppark, 0)), f'Cruiser {i + 2}', kind=kind)
    # And the cop's own, nearest the wreck, where Free Bird finds it (its door open there).
    manned(s.entity('The cop, pulled up', stopped, add3(W, COP_CAR[0]), (0, COP_CAR[1], 0)), 'Cruiser')

    # The police helicopters, each flying the road with its searchlight held on the deck: a JetRanger
    # off the left bow, and an AS350 high astern (the one the helicopter shots are taken from: it hangs above
    # and behind where their camera starts, out of its picture).
    copter_at = (-13.5, 11.2, 17.0)
    police_helicopter(s, P.between(s, root, 'Helicopter', None, 'wreck', 0.5, copter_at), V, 'JetRanger', copter_at, (9, 16, -5), (0, 1.5, 4), 5000.0, 40, wander=1.5)

    # --- the stunts ---
    def parked(flag, clip_name, frames, on, at, keys_in=None):
        """A body that sits far underground except from frame on[0] to on[1] of a one-shot at flag,
        when it is at at: for an effect that should run for a moment mid-clip."""
        clip = P.clip(V, clip_name, frames, [P.track('Position', [(0, (0, -4000, 0)), (on[0] - 1, (0, -4000, 0)), (on[0], (0, 0, 0)), (on[1], (0, 0, 0)), (on[1] + 1, (0, -4000, 0)), (frames, (0, -4000, 0))])])
        return P.play(s, root, clip_name, flag, clip, at)

    def sparks(parent, name, at, euler=(0, 0, 0), rate=260, speed=(8, 26), cone=60):
        A.particles(s, parent, name, at, euler, Shape='Cone', ConeAngle=cone, ShapeRadius=0.6, Lifetime=[0.5, 1.3], Speed=list(speed), Size=[0.04, 0.1],
                    StartColor=[1.0, 0.85, 0.5], StartColor2=[1.0, 0.55, 0.15], EndColor=[0.9, 0.2, 0.02], Intensity=7.0, Gravity=0.9, Drag=0.15, NoiseStrength=0.8,
                    Blend='Additive', EmissionRate=rate, MaxParticles=240, Alignment='Stretched', StretchFactor=0.04, FadeIn=0.02)

    # 1. cruiser_flips: the cruiser up on the left quarter clips the oncoming lane, goes over and
    # over and is left behind burning.
    flip_at = (-6.8, 0.0, -7.5)
    nudge = P.clip(V, 'WeaveClose', 110, [P.track('Position', [(0, (0, 0, 0)), (30, (0.8, 0, 2.5)), (70, (-0.5, 0, -1.0)), (110, (0, 0, 0))], 'SmoothStep'),
                                          P.track('Rotation', [(0, (0, 0, 0)), (30, (0, 6, 0)), (70, (0, -6, 0)), (110, (0, 0, 0))], 'SmoothStep')])
    manned(P.looping(s, P.between(s, swerving, 'Close cruiser', None, 'cruiser_flips', 0.01, flip_at), 'Close cruiser', nudge, flip_at), 'Cruiser 6', driving=True)
    flip = P.clip(V, 'CruiserFlips', 400, [
        P.track('Position', [(0, (0, 0, 0)), (12, (-1.0, 0, -3)), (24, (-2.2, 1.4, -9)), (36, (-3.0, 2.6, -18)), (48, (-3.6, 1.9, -30)), (60, (-4.0, 1.6, -45)), (90, (-4.4, 1.6, -90)), (400, (-4.6, 1.6, -586))]),
        P.track('Rotation', [(0, (0, 0, 0)), (12, (0, -35, 0)), (24, (0, -70, 70)), (36, (20, -100, 170)), (48, (0, -130, 280)), (60, (0, -150, 350)), (72, (0, -165, 80)), (90, (0, -170, 178)), (400, (0, -170, 180))])])
    tumbling = P.play(s, P.between(s, swerving, 'Flipped cruiser', 'cruiser_flips', None, 0.01, flip_at), 'Cruiser flips', 'cruiser_flips', flip, flip_at)
    A.patrol_cruiser(s, tumbling)
    sparks(tumbling, 'Flip sparks', (0, 0.6, 0), rate=140, speed=(4, 16), cone=80)
    fire(s, tumbling, V, (0, 0.6, 0.8), 0.9, 500.0, smoke=False, name='Flip fire')

    # 2. roadblock: two cruisers nose to nose across the road, barrels and trestles: the rig goes
    # straight through it. It comes down the road from 200 m out and is hit 3.9 s after the flag.
    HIT = int(round((200 - 15.5) / STEP))
    run = P.play(s, P.between(s, swerving, 'Roadblock', 'roadblock', None, 0.01, (0, 0, 200)), 'Roadblock run', 'roadblock',
                 P.clip(V, 'RoadblockRun', 400, [P.track('Position', [(0, (0, 0, 0)), (400, (0, 0, -640))])]), (0, 0, 200))

    def flung(name, rest, yaw, out, spin):
        """A piece of the roadblock at rest (in the block's own frame) until the hit, then thrown
        out by out (x, up, z along the road) and spun by spin (degrees of yaw and roll)."""
        k = [(0, 0.0), (HIT, 0.0), (HIT + 8, 0.45), (HIT + 22, 0.85), (HIT + 50, 1.0), (400, 1.0)]
        up = {0.0: 0.0, 0.45: 1.0, 0.85: 0.25, 1.0: 0.0}
        clip = P.clip(V, 'Flung_' + name.replace(' ', ''), 400, [
            P.track('Position', [(f, (out[0] * t, out[1] * up[t], out[2] * t)) for f, t in k]),
            P.track('Rotation', [(f, (spin[1] * t * 0.4, spin[0] * t, spin[1] * t)) for f, t in k[:2]] +
                    [(HIT + 6, (spin[1] * 0.2, spin[0] * 0.3, spin[1] * 0.35)), (HIT + 14, (spin[1] * 0.3, spin[0] * 0.6, spin[1] * 0.7)), (HIT + 30, (0, spin[0], spin[1])), (400, (0, spin[0], spin[1]))])])
        return P.play(s, s.entity(name, run, rest, (0, yaw, 0)), 'Flung', 'roadblock', clip)

    cruiser(s, flung('Block cruiser L', (-3.5, 0, 0), 82, (-6.5, 2.2, 16), (-150, 170)), V, (0, 0, 0), 0, name='Cruiser 7')
    cruiser(s, flung('Block cruiser R', (3.5, 0, 0.6), -98, (7.0, 1.6, 20), (140, -100)), V, (0, 0, 0), 0, name='Cruiser 8', kind='Ranger')
    for i, x in enumerate((-9.5, -7.6, 7.6, 9.5)):
        horse = flung(f'Trestle {i}', (x, 0, -1.5), 0, (x * 0.35, 2.5, 26 + 5 * i), (220 - 90 * i, 150))
        s.box('Trestle bar', horse, (0, 0.95, 0), (1.9, 0.22, 0.06), (0.95, 0.5, 0.05), emissive=(0.95, 0.5, 0.05), emissive_intensity=0.8)
        for dx in (-0.8, 0.8):
            s.box('Trestle leg', horse, (dx, 0.45, 0), (0.06, 0.9, 0.5), (0.3, 0.3, 0.32))
        s.box('Trestle lamp', horse, (0.7, 1.15, 0), (0.14, 0.14, 0.14), (1, 0.5, 0), emissive=(1, 0.5, 0.0), emissive_intensity=8.0, shape='Sphere', shadows=False)
    for i, (x, z) in enumerate(((-1.6, -4.0), (-0.5, -4.6), (0.6, -4.3), (1.7, -3.9), (-2.6, -3.0), (2.7, -3.2), (0, -6.0), (-1.1, -6.4), (1.2, -6.2))):
        barrel = flung(f'Barrel {i}', (x, 0, z), 0, (x * 3.5 + (2.5 if i % 2 else -2.5), 3.0 + 0.5 * (i % 3), 22 + 4 * (i % 4)), (200 + 60 * i, 170 - 50 * (i % 3)))
        s.box('Barrel', barrel, (0, 0.5, 0), (0.6, 1.0, 0.6), (0.95, 0.4, 0.05), shape='Cylinder')
        s.box('Barrel band', barrel, (0, 0.6, 0), (0.62, 0.16, 0.62), (0.95, 0.95, 0.95), shape='Cylinder', shadows=False)
    sparks(parked('roadblock', 'RoadblockHit', 400, (HIT - 1, HIT + 14), (0, 0.9, 15.6)), 'Roadblock sparks', (0, 0, 0), (-60, 0, 0), rate=420, speed=(10, 30), cone=75)
    s.light('Roadblock flash', parked('roadblock', 'RoadblockFlash', 400, (HIT, HIT + 5), (0, 2.0, 15.5)), (0, 0, 0), 'Point', (1.0, 0.8, 0.5), 9000.0, 40)

    # 3. big_air: road works in the middle lanes, and the rig goes up the ramp of spoil and steel
    # plates in the middle of them (the jump itself is the world's Jump clip: ride()). The works
    # come down the road from ramp_ahead, AHEAD seconds before the rig's nose is at the ramp's
    # foot (the manifest's cue for ramp_ahead is big_air less that): signs on both shoulders,
    # barrels with flashing lamps, the ramp under its lighting masts, an excavator beyond.
    AHEAD = 6.0
    works_at = (0, 0, 15.5 + AHEAD * 30 * STEP)
    works = CIR.clocked(s, P.between(s, swerving, 'Road works', 'ramp_ahead', None, 0.01, works_at), 'Road works run', 'ramp_ahead',
                   P.clip(V, 'RoadWorksRun', 600, [P.track('Position', [(0, (0, 0, 0)), (600, (0, 0, -600 * STEP))])]), works_at, loop=False)
    A.model(s, works, 'Road works', A.work_zone(V, length=RAMP, height=LIP))
    for side in (-1, 1):
        for z in (-150.0, -75.0):
            A.model(s, works, 'Road work sign', A.sign_face(V, 'RoadWork'), (side * 12.6, 2.7, z), (0, 180, 0), (1.5, 1.5, 1), A.mat(V, 'RoadWork', glow=(1, 1, 1), power=0.9), shadows=False)
            s.box('Road work sign post', works, (side * 12.6, 0.6, z + 0.05), (0.1, 1.3, 0.06), STEEL, shadows=False)
    for z in (1.0, 10.0):
        mast = (-7.8, 7.15, z - 0.2)
        s.box('Work lamp', works, mast, (1.4, 0.4, 0.12), (1, 0.97, 0.9), rot=(0, 20, 0), emissive=(1, 0.96, 0.88), emissive_intensity=8.0, shadows=False)
        A.glow_card(s, works, V, 'Work lamp glare', (mast[0], mast[1], mast[2] - 0.2), 2.2, (1.0, 0.95, 0.85), 2.2, (0, 180, 0))
        s.light('Work light', works, mast, 'Spot', (1.0, 0.95, 0.85), 260.0, 30, rot=look_rotation(mast, (0.5, 0.8, z + 2.0)), inner=30, outer=62)
    # The barrels' lamps, every other one, flashing in two alternating sets.
    for phase in (0, 1):
        on, off = (1, 1, 1), (0.001, 0.001, 0.001)
        keys = [(0, on), (11, on), (12, off), (23, off), (24, on)] if phase == 0 else [(0, off), (11, off), (12, on), (23, on), (24, off)]
        for k in range(phase, 11, 2):
            for side in (-1, 1):
                flasher = P.looping(s, works, 'Barrel lamp', P.clip(V, f'Flasher{phase}', 24, [P.track('Scale', keys)]), (side * 5.35, 1.12, -4.0 - k * 9.6))
                s.box('Barrel lamp', flasher, (0, 0, 0), (0.16, 0.2, 0.16), (1, 0.55, 0.0), emissive=(1.0, 0.5, 0.0), emissive_intensity=10.0, shape='Sphere', shadows=False)
    # The landing.
    sparks(parked('big_air', 'JumpLanding', JUMP_FRAMES, (int(LAND), int(LAND) + 11), (0, 0.15, 3.5)), 'Landing sparks', (0, 0, 0), (-80, 0, 0), rate=420, speed=(6, 24), cone=85)
    # The second helicopter and its searchlight on the deck.
    heli = (-28.0, 34.0, -48.0)
    police_helicopter(s, root, V, 'AS350', (heli[0] - 2.5, heli[1] + 5.0, heli[2] - 9.0), (10, 24, 4), (0, 1.5, 4), 14000.0, 95, name='Helicopter astern',
                      wander=1.8, inner=2.0, outer=4.5, pace=0.8)

    # The marked stretch (the finale comes back to it): mile marker 66 on the shoulder short of the
    # rail the trailer goes through, the billboard beyond it, the wreck.
    A.model(s, still, 'Mile marker', A.sign_face(V, 'MileMarker'), (13.3, 1.6, W[2] - 6), (0, 180, 0), (0.45, 0.6, 1), A.mat(V, 'MileMarker', glow=(1, 1, 1), power=0.5), shadows=False)
    s.box('Mile marker post', still, (13.3, 0.5, W[2] - 5.96), (0.08, 1.0, 0.05), STEEL)
    def billboard(parent, at, face='Billboard', lamps=True, power=1.1):
        """A billboard off the right shoulder, turned in toward the traffic coming up the road."""
        A.model(s, parent, 'Billboard', A.sign_face(V, face), at, (0, 180 - 25, 0), (7.5, 3.6, 1), A.mat(V, face, glow=(1, 1, 1), power=power), shadows=False)
        s.box('Billboard back', parent, add3(at, P_rot((0, 0, 0.2), -25)), (15.4, 7.6, 0.3), (0.05, 0.05, 0.05), rot=(0, -25, 0))
        legs = at[1] - 3.5
        for dx in (-5, 0, 5):
            s.box('Billboard leg', parent, add3((at[0], legs / 2, at[2]), P_rot((dx, 0, 0.3), -25)), (0.35, legs, 0.35), STEEL)
            lamp = add3((at[0], at[1] - 3.9, at[2]), P_rot((dx, 0, -2.2), -25))
            if lamps:
                s.light('Billboard lamp', parent, lamp, 'Spot', (1.0, 0.95, 0.85), 300.0, 14, rot=look_rotation(lamp, at), inner=30, outer=55)
            else:
                s.box('Billboard lamp', parent, lamp, (0.5, 0.12, 0.3), (1, 0.95, 0.8), emissive=(1.0, 0.95, 0.8), emissive_intensity=6.0, shadows=False)

    # The marked shoulder's own (PREPARE TO MEET GOD) stands where the rig stops: it and the mile
    # marker are there from the wreck. On the way, billboards go by with the road, one every
    # twenty seconds: HELL IS REAL, then the one the band will die under.
    bb = (26.0, 9.5, W[2] + 18)
    billboard(still, bb)
    signs = scroll('Signs', 1920.0)
    # (No lamps of their own to light them as they pass: their faces glow more than the marked one's.)
    billboard(signs, (30.0, 11.5, 640.0), 'BillboardHell', lamps=False, power=2.4)
    billboard(signs, (30.0, 11.5, 1600.0), 'Billboard', lamps=False, power=2.4)
    # The burning trailer shows from the crash, the bodies from the next beat.
    burning_wreck(s, P.between(s, world, 'Wreck', 'wreck', None, 0.25, W), V, add3(W, WRECK_AT))
    hand = slewed(crash_site(s, P.between(s, world, 'Bodies', 'bodies', None, 0.01, W), V, W, {}, burning=False, lying=CRASH_LYING))
    # The explosion: a fireball up off the trailer and gone in two seconds, a ring of fire along
    # the road, and everything it throws.
    boom = add3(W, add3(WRECK_AT, (4.0, 0, 6)))
    ball_clip = P.clip(V, 'Fireball', 66, [P.track('Scale', [(0, (0.05, 0.05, 0.05)), (7, (13, 10, 13)), (30, (10, 12, 10)), (66, (0.01, 0.01, 0.01))], 'SmoothStep'),
                                           P.track('Position', [(0, (0, 0, 0)), (66, (0, 9, 0))], 'SmoothStep')])
    ball = P.play(s, world, 'Fireball', 'wreck', ball_clip, (boom[0], 3.0, boom[2]))
    see_through(s.box('Fireball', ball, (0, 0, 0), (1, 1, 1), FIRE, emissive=FIRE, emissive_intensity=14.0, shape='Sphere', shadows=False), 0.85, additive=True)
    see_through(s.box('Fireball core', ball, (0, 0, 0), (0.62, 0.62, 0.62), (1, 0.9, 0.6), emissive=(1, 0.9, 0.6), emissive_intensity=24.0, shape='Sphere', shadows=False), 1.0, additive=True)
    # The blast's light: there for two seconds (the clip parks it far underground before and after).
    flash_clip = P.clip(V, 'FireballLight', 70, [P.track('Position', [(0, (0, -4000, 0)), (1, (0, 0, 0)), (20, (0, 4, 0)), (64, (0, 8, 0)), (70, (0, -4000, 0))])])
    s.light('Fireball light', P.play(s, world, 'Fireball light', 'wreck', flash_clip, (boom[0], 3.0, boom[2])), (0, 0, 0), 'Point', (1.0, 0.6, 0.25), 20000.0, 120)
    burst = P.between(s, world, 'Blast', 'wreck', None, 0.01, boom)
    A.particles(s, burst, 'Blast debris', (boom[0], 1.5, boom[2]), Looping=False, Duration=1.0, Shape='Sphere', ShapeRadius=1.5, Lifetime=[2.0, 4.5], Speed=[8, 30], Size=[0.08, 0.3],
                StartColor=[1.0, 0.8, 0.4], StartColor2=[1.0, 0.45, 0.1], EndColor=[0.6, 0.1, 0.02], Intensity=6.0, Gravity=0.9, Drag=0.2, NoiseStrength=0.5,
                Blend='Additive', EmissionRate=0, BurstCount=260, MaxParticles=300, Alignment='Stretched', StretchFactor=0.05, EndSize=0.4, FadeIn=0.01)
    A.particles(s, burst, 'Blast smoke', (boom[0], 2.5, boom[2]), Looping=False, Duration=1.0, Shape='Sphere', ShapeRadius=3.0, Lifetime=[4.0, 8.0], Speed=[2, 9], Size=[2.5, 5.0],
                StartColor=[0.3, 0.17, 0.1], StartColor2=[0.16, 0.12, 0.1], EndColor=[0.08, 0.07, 0.07], StartAlpha=0.5, EndAlpha=0.0, Gravity=-0.12, Drag=0.6,
                NoiseStrength=0.6, NoiseFrequency=0.3, Blend='Alpha', EmissionRate=0, BurstCount=70, MaxParticles=80, EndSize=3.0, FadeIn=0.05, Texture=A.tex(V, 'Puff'))

    # Story shots.
    kit = (0, 2.22, DRUM_AT[2] - 0.45)            # the drums in front of the drummer, toward the cops
    kick = (0.1, 1.45, DRUM_AT[2] - 0.55)
    roof = (0.0, 4.45, ROOF_AT[2])                # the roof guitarist's chest
    window = (1.20, 2.83, 12.02)
    wheelman = (-0.59, 2.59, 12.04)
    # Low on the rear tandem's wheel, up past the deck's edge to the kick pedal, then out to the
    # side and up: the whole kit on the deck, the drummer facing down the road at the cops, whose
    # lights are closing behind.
    shot(s, marks, 'highway_open', (2.18, 0.37, 1.42), (1.17, 0.55, 2.08), 48, 12,
         via=[((2.05, 1.50, 3.0), (kick[0] + 0.3, kick[1], kick[2]), 48),
              ((2.7, 2.4, 2.6), kit, 52)], lead='l',
         end=((7.2, 4.4, 6.6), (0, 1.6, -5.0), 60))
    shot(s, marks, 'driver_window', (-3.4, 1.91, 13.9), wheelman, 40, 5, ride=0.35, lead='r',
         end=((-2.12, 2.68, 12.32), wheelman, 34))
    shot(s, marks, 'freight_pass', (-2.2, 2.5, 12.6), (-4.35, 1.9, 100), 41, 6, lin=True,
         via=[((-2.4, 2.4, 13.2), (-4.35, 2.1, 74), 39),
              ((-2.5, 2.4, 13.5), (-4.35, 2.0, 26), 62),
              ((-2.35, 2.8, 13.0), (-4.35, 2.0, -8), 79)],
         end=((-2.1, 3.15, 13.1), (-0.6, 2.55, 12.05), 43))
    shot(s, marks, 'roof_solo', (2.75, 4.55, 8.45), roof, 54, 9, lead='r',
         via=[((1.6, 4.7, 9.5), roof, 42)],
         end=((-1.9, 5.6, 9.8), roof, 48))
    # The stand on the gas, up it to the empty seat, out through the windscreen at the singer on
    # the bonnet; then the singer there, and over their shoulder down the road (pedal_jammed,
    # hood_surf, hood_wind: they hold until the next lands).
    bonnet = (0.0, 3.05, 14.2)
    # (From the passenger footwell across to the pedals; up under the dash, whose face is 12.69
    # from 2.05 up; and the driver's eyes, the singer through the left pane, clear of the pillar.)
    shot(s, marks, 'pedal_jammed', (0.25, 1.8, 12.78), (-0.45, 1.5, 12.62), 50, 11, ride=0.25,
         via=[((0.15, 2.0, 12.5), (-0.55, 2.1, 11.95), 56)],
         end=((-0.45, 2.62, 12.35), (0.05, 3.0, 14.2), 58))
    shot(s, marks, 'hood_surf', (3.1, 2.55, 14.1), bonnet, 46, 9.2, ride=0.45, lead='l',
         via=[((2.6, 2.4, 15.9), bonnet, 44)], end=((1.4, 2.5, 17.6), (0.0, 3.15, 14.3), 40))
    # (Off to the side of the nose, out of the headlights' beams; ending over the right shoulder,
    # the singer low on the left of the picture.)
    shot(s, marks, 'hood_wind', (2.2, 2.0, 18.5), bonnet, 52, 16, ride=0.5,
         via=[((3.4, 4.6, 15.2), (0.0, 2.9, 13.6), 50)], end=((0.85, 3.85, 12.75), (-0.3, 2.6, 19.0), 60))
    cop_face = (seat[0], face[1], seat[2])
    fy = face[1]
    shot(s, marks, 'cop_watching', (seat[0] + 0.3, fy + 0.12, car_at[2] + 2.55), cop_face, 38, 6, focus=True, end=((seat[0] + 0.1, fy + 0.08, car_at[2] + 1.95), cop_face, 30))
    shot(s, marks, 'heli_chase', heli, (0, 1.0, -6), 44, 9, heli=True,
         via=[((heli[0] + 1.5, heli[1] - 0.4, heli[2] + 2.5), (1.5, 1.0, 26), 7), ((heli[0] + 2.5, heli[1] - 0.6, heli[2] + 4.5), (0.4, 2.2, 8.5), 6.5)],
         end=((heli[0] + 4, heli[1] - 1, heli[2] + 7), kit, 8))
    shot(s, marks, 'foot_on_monitor', (3.6, 1.65, 14.7), window, 48, 6, ride=0.45, lead='l',
         via=[((2.7, 2.75, 12.7), window, 40)], end=((3.6, 4.2, 10.0), roof, 44))
    shot(s, marks, 'cop_radio', (seat[0] + 1.9, fy + 0.02, seat[2] + 0.8), cop_face, 34, 5, focus=True, end=((seat[0] + 1.65, fy, seat[2] + 0.55), cop_face, 28))
    shot(s, marks, 'cop_nods', (seat[0] - 0.2, fy + 0.1, car_at[2] + 2.1), cop_face, 30, 5, focus=True, end=((seat[0] - 0.05, fy + 0.06, car_at[2] + 1.7), cop_face, 22))
    shot(s, marks, 'heli_again', (40, 26, 22), (0, 1.5, 0), 34, 8, heli=True, via=[((44, 24, 2), (0, 1.5, 0), 26)], end=((36, 22, -20), (0, 1.5, 2), 20))
    shot(s, marks, 'cruiser_flips', (-3.5, 2.7, -0.4), (-7.6, 1.0, -11.0), 64, 5, hand=True, end=((-3.3, 2.9, -0.8), (-11.0, 1.6, -70.0), 40))
    shot(s, marks, 'roadblock', (0.6, 5.9, 9.2), (0, 1.0, 90.0), 58, 5.5, hand=True, end=((1.4, 6.0, 8.6), (0, 0.5, 24.0), 74))
    shot(s, marks, 'ramp_ahead', (-0.9, 6.3, 9.4), (0, 0.8, 120.0), 46, AHEAD - 0.4, hand=True, end=((-0.6, 6.0, 9.0), (0, 1.0, 26.0), 64))
    shot(s, marks, 'big_air', (15.8, 0.65, 13.1), (0, 1.9, 7.8), 60, 4, hand=True, end=((13.4, 0.7, 3.6), (0, 2.3, 7.2), 58))
    shot(s, marks, 'trailer_slews', (2.7, 2.5, -1.0), kit, 60, 4.5, hand=True, end=((3.1, 2.2, -1.9), kit, 52))
    Ws = slewed(add3(W, add3(WRECK_AT, (4.5, 1.5, 6.0))))
    shot(s, marks, 'wreck', (Ws[0] - 34, 24, Ws[2] - 26), Ws, 26, 7, hand=True, via=[((Ws[0] - 33, 23, Ws[2] - 28), (Ws[0], 6, Ws[2]), 40)],
         end=((Ws[0] - 22, 15, Ws[2] - 23), Ws, 24))
    lay = CRASH_LYING['drummer'][2] + SLEW_YAW        # the drummer's body, turned with the road
    shot(s, marks, 'bodies', beside_hand(hand, lay, 1.5, 1.1, 0.5), hand, 34, 40, focus=True, end=(beside_hand(hand, lay, 0.95, 0.6, 0.12), (hand[0], 0.05, hand[2]), 28))
    write(s, V, 'The Highway')


# ---- hell ---------------------------------------------------------------------------------------
def hell():
    V = 'StoryHell'
    s = Scene(seed=6602)
    s.venue = V
    root = s.group('Highway to the Afterlife: hell')
    marks = s.group('Markers', root)
    s.info(marks, 'Hell', 'Drumsmith', outdoor=False, room_back=-40, room_ceiling=60, half_width=22, desk_z=-14,
           ambient=(0.012, 0.002, 0.0015), fog_color=(0.016, 0.01, 0.009), haze=0.1,
           keep_red=1.0, keep_warmth=0.3, lights_until='fell', quiet_look=False)
    band(s, marks, 0.0)
    HEAD_ALOFT = 2.85    # a standing member's head while aloft (band_aloft lifts them 1.2 m)
    s.camera_spot('Camera Wide', marks, (0, 4.6, -11.5), (0, 2.2, 4), 'Wide', 58)
    s.camera_spot('Camera Crane', marks, (8, 9, -9), (0, 1.6, 4), 'Crane', 55)
    s.camera_spot('Camera Desk', marks, (-1.5, 2.8, -10), (0, 2.0, 4), 'Desk', 30)

    # 1. The crash site, until they go through the road. The tease: from 'ascent' the ghosts rise
    # (the Earth sinks away under them, EARTH_DROP metres), through cloud, into a light from above, up to the gates; at
    # 'denied' the light goes out, at 'apex' they turn over and fall, back down through the cloud:
    # from 'earth_back' (out under its base) the Earth comes up at them, faster and faster, and
    # they smash through the road at 'fell', PLUNGE seconds later (the manifest's cues for the two
    # are that far apart).
    # The cloud is the sky's own (the song's alt_ flags: how high the sky is seen from, so its
    # cloud base comes down to them, they go through the layer and it lies below them as a sea;
    # cover_ flags fill the sky as they go up). The set's Earth is a couple of hundred metres down
    # and would stand in front of that cloud: it is hidden from 'earth_lost' (they are inside the
    # layer) until 'earth_back' (they have been thrown back down through it, under its base again).
    EARTH_DROP, PLUNGE = 400.0, 5.44
    # The singer's eyes while they hang there reaching (aloft, the head tipped back), and the light
    # they reach up into: 8 m out just past their raised fingertips, 47 degrees up, ahead and to
    # their left.
    PLEA_EYES = (VOCALS[0], 2.92, VOCALS[1])
    PLEA_TOWARD = (0.1936, 0.7314, -0.6539)
    PLEA_LIGHT = tuple(e + 8.0 * d for e, d in zip(PLEA_EYES, PLEA_TOWARD))
    BREAK_GLOW = 4.5                 # the night through the break in the road, seen from 150 m down the shaft's haze
    crash = P.between(s, root, 'The crash site', None, 'fell', 0.0)
    # (No dome of stars here: this stretch is under the engine's own sky, which the song's sky_
    # flags turn from the night of the crash to day as they rise and back as they fall.)
    # Each place has its own rig (a VenueShowLight under a story group is cued only while it shows).
    for i, x in enumerate((-3.5, 3.5, -1.2, 1.2)):
        s.light(f'Crash wash {i}', crash, (x, 7, -3), 'Spot', (0.7, 0.8, 1.0), 700.0, 18, rot=look_rotation((x, 7, -3), (x * 0.4, 1, 3.5)), inner=22, outer=42, show='Wash', group=i)
    # And from behind them, the moon's side: the director's shots from behind the band had them
    # as black shapes against the cruiser's headlights.
    s.light('Crash back light', crash, (1.5, 5.5, 10.0), 'Point', (0.55, 0.65, 1.0), 650.0, 15)
    sink = P.clip(V, 'EarthSinks', 1080, [P.track('Position', [(0, (0, 0, 0)), (90, (0, -1.5, 0)), (240, (0, -10, 0)), (480, (0, -45, 0)), (1080, (0, -EARTH_DROP, 0))])])
    hit = int(PLUNGE * 30)
    # Falling, so it comes on faster all the way (the height covered goes as the time to the 1.25th
    # power: about 90 m/s at the road), and on up past them at that speed once they are through.
    # earth_y(s): where the Earth is s seconds into it (the keys are joined straight).
    PLUNGE_KEYS = [(round(hit * u), EARTH_DROP * u ** 1.25) for u in (0, 0.2, 0.4, 0.6, 0.75, 0.88, 1.0)]
    plunge = P.clip(V, 'EarthComesBack', hit + 45, [P.track('Position', [(f, (0, y, 0)) for f, y in PLUNGE_KEYS] + [(hit + 45, (0, EARTH_DROP + 135, 0))])])

    def earth_y(sec):
        f = min(max(sec * 30, 0), hit)
        for (f0, y0), (f1, y1) in zip(PLUNGE_KEYS, PLUNGE_KEYS[1:]):
            if f <= f1:
                return -EARTH_DROP + y0 + (y1 - y0) * (f - f0) / max(f1 - f0, 1)
        return 0.0
    # (Hidden is shrunk to nothing about its pivot: far below, or a toy Earth would hang at their
    # feet. At once both ways: it goes inside the cloud, and is back as they come out under it.)
    away = (0, -3000, 0)
    crash = P.frame(s, s.story('The Earth (not from in or over the cloud)', crash, 'earth_lost', False, 0.0, away, unless='earth_back'), away)
    # (From here on 'crash' is the Earth: everything on it goes down with it and comes back.)
    # (The way back is held to the song's clock, not played: the shots that ride on it, and the
    # band's impact, are timed to the song.)
    crash = CIR.clocked(s, P.play(s, crash, 'The Earth sinks away', 'ascent', sink), 'The Earth comes back', 'earth_back', plunge, loop=False)
    road(s, crash, V, -14, 14, -70, 70)
    roadside(s, crash, V, (0, 0, 0), 70.0, 14.0, torn_z=6.0, sky=False, earth_too=True)
    s.light('Moon', crash, (0, 40, -20), 'Directional', (0.4, 0.5, 0.8), 2.4, 300, rot=(42, 150, 0), shadows=True)
    for x, z in ((-30, -30), (30, 30), (-30, 40), (30, -40)):
        s.light('Night fill', crash, (x, 26, z), 'Point', (0.3, 0.4, 0.75), 2600.0, 90)
    cruiser(s, crash, V, COP_CAR[0], COP_CAR[1], door_open=True)
    burning_wreck(s, crash, V, (9.0, 0, -1.0))
    hand = crash_site(s, crash, V, (0, 0, 0), {}, burning=False, lying=CRASH_LYING)
    for i, (x, z, yaw) in enumerate(((-9.5, -20, 20), (-3.0, -24, -30), (4.5, -22, 60), (-11.5, 6, 80))):
        A.flare(s, crash, V, f'Flare {i}', (x, 0, z), yaw)
    ground_fog(s, crash, V, (0, 0.5, 0), (46, 1.0, 60), 12)
    # Seen from the fall ('earth_back' until they hit): the crash has to read from 400 m up. The
    # land under a high moon, the burning truck a beacon (a glow on the ground round it and a light
    # up into its smoke), the cruiser's beacons and the flares bright points.
    seen = P.between(s, crash, 'The crash, seen from the fall', 'earth_back', 'fell', 0.4)
    s.light('Moon over the fall', seen, (0, 60, -20), 'Directional', (0.55, 0.65, 1.0), 9.0, 400, rot=(62, 150, 0))
    for x, z in ((-40, -50), (40, -40), (-40, 50), (40, 60)):
        s.light('Land under the moon', seen, (x, 45, z), 'Point', (0.45, 0.55, 0.9), 4000.0, 140)
    A.glow_card(s, seen, V, 'The fire, from above', (13.0, 0.12, 7.0), 22.0, (1.0, 0.42, 0.08), 2.2, (90, 0, 0))
    s.light('The fire up into its smoke', seen, (14.0, 12.0, 9.0), 'Point', (1.0, 0.45, 0.12), 5000.0, 40)
    for i, (x, z, c) in enumerate(((-7.9, -9.4, (1.0, 0.08, 0.06)), (-7.1, -8.6, (0.15, 0.3, 1.0)))):
        A.glow_card(s, seen, V, f'Beacon from above {i}', (x, 1.9, z), 2.4, c, 6.0, (90, 0, 0))
    for i, (x, z) in enumerate(((-9.5, -20), (-3.0, -24), (4.5, -22), (-11.5, 6))):
        A.glow_card(s, seen, V, f'Flare from above {i}', (x, 0.2, z), 1.8, (1.0, 0.12, 0.08), 6.0, (90, 0, 0))
    s.box('Hubcap', crash, (-4.6, 0.03, 0.4), (0.42, 0.04, 0.42), (0.7, 0.72, 0.75), metallic=0.95, rough=0.25, shape='Cylinder', rot=(4, 0, 3))
    # The cop: out of the car, running to the drummer, kneeling beside the body.
    car_door = (-5.6, 0, -7.4)
    kneel_at = (-0.75, -0.08, DRUMMER[1] + 1.7)      # at the chest of the drummer's body
    # Skinned (P.actor): he strides as the clip carries him (nine strides in the three seconds),
    # then is on his knees by the drummer, his hands on his thighs, looking down at them.
    run_yaw = P.yaw_to(car_door, kneel_at)
    run_clip = P.path_clip(V, 'CopRuns', [(0, 0, 0), (0, 0, math.dist(car_door, kneel_at))], 3.0)
    runner = P.play(s, P.between(s, crash, 'Cop until he kneels', None, 'cop_kneels', 0.2, car_door), 'Cop runs', 'cop_runs', run_clip, car_door, (0, run_yaw, 0))
    # The cruiser's spotlight, swung onto the road where he runs (from 'cop_runs' on).
    lamp = (-7.2, 1.6, -9.0)
    s.light('Cruiser spotlight on the road', P.between(s, crash, 'Cruiser spotlight', 'cop_runs', None, 0.3), lamp, 'Spot', (0.85, 0.9, 1.0), 4500.0, 28,
            rot=look_rotation(lamp, (-2.6, 0.6, 1.0)), inner=16, outer=34)
    P.actor(s, runner, 'Cop', *COP_LOOK, (0, 0, 0), 0, motion=P.gait(V, 'CopStrides', 20, 0.9, 0.32, 0.035, cycles=5), speed=1.1556, once=True, Lean=10.0, Crouch=0.05,
            LeftLeg=P.leg(4), RightLeg=P.leg(4), LeftArm=P.arm(10, 8, 40, grip=0.8), RightArm=P.arm(10, 8, 40, grip=0.8))
    kneels = (kneel_at[0], 0, kneel_at[2])
    P.actor(s, P.between(s, crash, 'Cop kneeling', 'cop_kneels', None, 0.3, kneels), 'Cop', *COP_LOOK, kneels, 90, 'Kneeling', Bow=18.0, Lean=10.0, Nod=24.0,
            HeadTurn=P.turn_to(kneels, 90, (DRUMMER[0] + 0.3, 0.2, DRUMMER[1] + 2.0), 45.0), LeftLeg=P.leg(8), RightLeg=P.leg(8),
            LeftArm=P.arm(hand=(-0.16, 0.5, 0.22), pole=(-1, 0, -0.6), palm=(0, -1, 0), grip=0.3), RightArm=P.arm(hand=(0.16, 0.5, 0.22), pole=(1, 0, -0.6), palm=(0, -1, 0), grip=0.3))

    # 1b. The way up. (The cloud itself is the sky's, above, and the haze inside it the game's.)
    tease = P.between(s, root, 'The way up', 'ascent', 'fell', 0.0)
    # Their own pale light while they go up in the dark, until the light from above takes over:
    # the crash's lights go down with the Earth, and by the moon alone the band was a dark blue
    # shape against the night.
    pale = P.between(s, tease, 'Their own light (the climb by night)', None, 'heavens_light', 4.0)
    s.light('Their own light', pale, (0, 6.5, -3.0), 'Point', (0.7, 0.8, 1.0), 900.0, 16)
    s.light('Their own light, behind', pale, (0, 5.0, 9.0), 'Point', (0.6, 0.72, 1.0), 450.0, 13)
    # The light from above, growing; then the gates themselves coming down to meet them.
    glory = P.gated(s, P.gated(s, tease, 'The light from above', 'heavens_light', True, 9.0, (0, 320, 3)), 'The light (until denied)', 'denied', False, 0.12, (0, 320, 3))
    gold = (1.0, 0.86, 0.58)
    A.glow_card(s, glory, V, 'Glory', (0, 135, 3), 120.0, gold, 2.6, (90, 0, 0))
    for i in range(7):
        a = 2 * math.pi * i / 7 + 0.3
        x, z = math.cos(a) * 16, math.sin(a) * 16
        A.shaft(s, glory, V, f'Sunbeam {i}', (x * 0.25, 150, z * 0.25 + 3), (x, -30, z + 3), 7.0, gold, 0.14)
    s.light('Glory light', glory, (0, 34, 3), 'Point', gold, 5200.0, 80, fog=CIR.FOG)
    for i, x in enumerate((-5.0, 5.0)):
        at = (x, 9, -6)
        s.light(f'Glory key {i}', glory, at, 'Spot', gold, 1500.0, 26, rot=look_rotation(at, (x * 0.2, 2.4, 3.5)), inner=20, outer=38, fog=CIR.FOG)
    A.particles(s, glory, 'Motes', (0, 4, 3), Shape='Box', BoxSize=[18, 14, 18], Lifetime=[3.0, 6.0], Speed=[0.1, 0.5], Size=[0.02, 0.05],
                StartColor=[1.0, 0.9, 0.6], StartColor2=[1.0, 1.0, 0.9], EndColor=[1.0, 0.85, 0.5], Intensity=3.0, Gravity=0.25, Drag=0.2, NoiseStrength=0.5,
                Blend='Additive', EmissionRate=30, MaxParticles=160, FadeIn=0.2)
    gates = P.gated(s, P.gated(s, tease, 'The gates', 'gates', True, 2.0, (0, 420, 3)), 'The gates (until denied)', 'denied', False, 0.12, (0, 60, 3))
    gates = P.play(s, gates, 'The gates come down to them', 'gates', P.clip(V, 'GatesComeDown', 1020, [P.track('Position', [(0, (0, 250, 0)), (400, (0, 120, 0)), (800, (0, 35, 0)), (1020, (0, 0, 0))])]))
    # Lying open overhead, so that they rise up into the opening.
    A.model(s, gates, 'The gates', A.gate(V), (0, 30, 3 - 14.3), (90, 0, 0), 2.2, A.mat(V, 'Palette', (1, 1, 1), glow=(1.0, 0.9, 0.6), power=1.3, metallic=0.7, rough=0.3), shadows=False)
    burst_spin = P.clip(V, 'GlorySpin', 1800, [P.track('Rotation', [(0, (0, 0, 0)), (600, (0, 120, 0)), (1200, (0, 240, 0)), (1800, (0, 359.9, 0))])])
    A.model(s, P.looping(s, gates, 'Glory', burst_spin, (0, 44, 3)), 'Sunburst', A.sunburst(V), (0, 0, 0), (90, 0, 0), 46.0,
            A.mat(V, 'Palette', (0, 0, 0), glow=gold, power=1.6, additive=True, both=True), shadows=False)
    # The plea (from 'reach', seen through the singer's eyes): the light just beyond the hand they
    # reach up into it, its rays pouring down past the fingers, until the hand shuts it out.
    plea = P.between(s, tease, 'The light over the hand', 'reach', 'band_shield', 0.6, PLEA_LIGHT)
    A.glow_card(s, plea, V, 'The light over the hand', PLEA_LIGHT, 1.5, (1.0, 0.93, 0.75), 5.0, (47, -16.5, 0))
    across = (0.959, 0.0, 0.284)                                    # square to PLEA_TOWARD, level
    upward = (-0.208, 0.682, 0.702)                                 # square to both
    for i in range(9):
        a = 2 * math.pi * i / 9 + 0.2
        past = tuple(e - 1.5 * d + 1.1 * (math.cos(a) * c + math.sin(a) * u) for e, d, c, u in zip(PLEA_EYES, PLEA_TOWARD, across, upward))
        A.shaft(s, plea, V, f'Ray past the fingers {i}', PLEA_LIGHT, past, 0.5, gold, 0.3)
    s.light('The light on the hand', plea, (PLEA_EYES[0], PLEA_EYES[1] + 2.0, PLEA_EYES[2] - 2.0), 'Point', (1.0, 0.92, 0.75), 300.0, 6)
    # Denied: the light is gone at a stroke, and what comes down instead is red. From the apex it
    # goes on up away from them as they fall.
    no = P.between(s, root, 'Denied', 'denied', 'fell', 0.05)
    no = P.play(s, no, 'The refusal, left above', 'apex', P.clip(V, 'RefusalGoesUp', 330, [P.track('Position', [(0, (0, 0, 0)), (60, (0, 2, 0)), (150, (0, 40, 0)), (240, (0, 160, 0)), (330, (0, 420, 0))])]))
    A.glow_card(s, no, V, 'The refusal', (0, 60, 3), 150.0, (1.0, 0.08, 0.03), 3.5, (90, 0, 0))
    s.light('Refusal', no, (0, 18, 3), 'Point', (1.0, 0.12, 0.06), 7000.0, 70, fog=CIR.FOG)
    bolt = [(0.0, 60.0), (2.2, 44.0), (-1.4, 33.0), (1.8, 22.0), (-0.9, 13.0), (0.4, 4.5)]
    for i, ((x0, y0), (x1, y1)) in enumerate(zip(bolt, bolt[1:])):
        length = math.hypot(x1 - x0, y1 - y0)
        s.box(f'Bolt {i}', no, ((x0 + x1) / 2, (y0 + y1) / 2, 3.2), (0.3, length + 0.2, 0.3), (1, 0.9, 0.85), rot=(0, 0, math.degrees(math.asin((x0 - x1) / length))),
              emissive=(1.0, 0.35, 0.25), emissive_intensity=40, shadows=False)

    # The free fall ('free_fall' until they hit): the air tearing up past them, a pale trail over each of
    # them, so they show as streaks against the night from the ground.
    rush = P.between(s, root, 'The air tearing past', 'free_fall', 'fell', 0.5)
    # (And, seen from the ground at the crash, a pale glow under them: they come in like a falling star.)
    A.glow_card(s, P.between(s, rush, 'Falling star', 'crash_returns', None, 0.3), V, 'Falling star', (0, 0.3, 3), 4.0, (0.6, 0.78, 1.0), 3.0, (90, 0, 0))
    for i, (x, z) in enumerate((DRUMMER, GUITAR, BASS, VOCALS)):
        A.particles(s, rush, f'Trail {i}', (x, 1.6, z), Shape='Cone', ConeAngle=6, ShapeRadius=0.5, Lifetime=[0.2, 0.3], Speed=[16, 22], Size=[0.03, 0.07],
                    StartColor=[0.75, 0.88, 1.0], StartColor2=[0.55, 0.7, 1.0], EndColor=[0.4, 0.55, 1.0], Intensity=2.0, Gravity=-3.0, Drag=0.0,
                    Blend='Additive', EmissionRate=50, MaxParticles=30, Alignment='Stretched', StretchFactor=0.08, FadeIn=0.05)

    # The impact ('fell'): they smash through the road. A flash, and the asphalt bursting up and
    # out round them, chunks and dust, as the road goes on up past them.
    smash = P.between(s, root, 'The impact', 'fell', None, 0.0, (0, 1, 3))
    flash = P.play(s, smash, 'The impact, its flash', 'fell', P.clip(V, 'ImpactFlash', 18, [P.track('Scale', [(0, (1, 1, 1)), (4, (1.3, 1.3, 1.3)), (18, (0.001, 0.001, 0.001))])]), (0, 1.0, 3))
    A.glow_card(s, flash, V, 'Impact flash', (0, 0, 0), 9.0, (1.0, 0.85, 0.6), 4.0, (90, 0, 0))
    A.particles(s, smash, 'Asphalt thrown up', (0, 0.6, 3), Shape='Sphere', ShapeRadius=3.0, Lifetime=[1.0, 2.2], Speed=[8, 26], Size=[0.12, 0.45], StartColor=[0.1, 0.1, 0.11],
                StartColor2=[0.32, 0.3, 0.27], EndColor=[0.06, 0.06, 0.06], Gravity=2.5, Drag=0.3, NoiseStrength=1.0, Blend='Alpha', Lit=False, EmissionRate=0, BurstCount=220,
                MaxParticles=240, Looping=False, Duration=30.0)
    A.particles(s, smash, 'Sparks off the road', (0, 0.6, 3), Shape='Sphere', ShapeRadius=2.0, Lifetime=[0.4, 1.0], Speed=[14, 34], Size=[0.03, 0.08],
                StartColor=[1.0, 0.85, 0.5], StartColor2=[1.0, 0.5, 0.15], EndColor=[1.0, 0.2, 0.03], Intensity=6.0, Gravity=1.5, Drag=0.2, Blend='Additive',
                EmissionRate=0, BurstCount=160, MaxParticles=170, Looping=False, Duration=30.0, Alignment='Stretched', StretchFactor=0.05)
    A.particles(s, smash, 'Dust of the road', (0, 0.4, 3), Shape='Sphere', ShapeRadius=3.5, Lifetime=[1.5, 3.0], Speed=[3, 9], Size=[1.5, 3.5], EndSize=2.0,
                StartColor=[0.35, 0.32, 0.3], StartColor2=[0.2, 0.19, 0.18], EndColor=[0.1, 0.09, 0.09], StartAlpha=0.5, EndAlpha=0.0, Gravity=-0.5, Drag=0.6,
                Blend='Alpha', EmissionRate=0, BurstCount=40, MaxParticles=45, Looping=False, Duration=30.0, Texture=A.tex(V, 'Puff'))

    # 2. The fall. They smash through the road on the guitar's first riff and are straight into
    # Dante's nine circles (story_afterlife_circles), one after another, faster and faster, down to
    # the frozen heart of hell they land in. Between the road and Limbo there is only the throat of
    # the shaft, a few seconds of rock streaming up past them, embers racing up, the road a slit of
    # light above.
    fall = P.between(s, P.between(s, root, 'The fall', 'fell', None, 0.0), 'Falling', None, 'landed', 0.3)
    rock_glow = A.mat(V, 'Rock', (1, 1, 1), glow=(0.5, 0.1, 0.03), power=0.5, tiling=None)
    shaft_glow = A.mat(V, 'Rock', (0.6, 0.5, 0.5), glow=(1.0, 0.22, 0.06), power=0.8, tiling=(2, 2))
    # The walls' shape repeats every SHAFT_PERIOD metres, so the loop never jumps. The throat goes
    # by as fast as Limbo will; the deep shaft (behind every circle, and all there is between two
    # of them for a moment) at about the fall's speed half way down.
    throat = CIR.SPEED[0]
    wall_frames, deep_frames = int(round(A.SHAFT_PERIOD / throat * 30)), int(round(A.SHAFT_PERIOD / 72.0 * 30))
    wall_clip = P.clip(V, 'ShaftWalls', wall_frames, [P.track('Position', [(0, (0, 0, 0)), (wall_frames, (0, A.SHAFT_PERIOD, 0))])])
    deep_clip = P.clip(V, 'DeepShaft', deep_frames, [P.track('Position', [(0, (0, 0, 0)), (deep_frames, (0, A.SHAFT_PERIOD, 0))])])
    A.model(s, P.looping(s, fall, 'Deep shaft', deep_clip), 'Shaft', A.shaft_walls(V, 15.0, 390.0), (0, 0, 3), (0, 40, 0), (1.9, 1.0, 1.9),
            A.mat(V, 'Rock', (0.45, 0.4, 0.38), glow=(0.75, 0.4, 0.28), power=1.7, tiling=(3, 2)), shadows=False)
    # The throat under the road. It comes up with the road as they go through it (the road was at
    # their feet; it ends a slit of light far above), and goes on up as Limbo comes.
    upper = P.gated(s, fall, 'The shaft under the road', CIR.flag(2), False, 1.0, (0, 3 * CIR.travel(1), 3))
    upper = P.play(s, upper, 'The shaft goes on up', CIR.flag(1), CIR.arrives(V, 1)[1])
    upper = P.play(s, upper, 'Through the road', 'fell', P.clip(V, 'ThroughTheRoad', 48, [P.track('Position', [(0, (0, -150, 0)), (15, (0, -80, 0)), (30, (0, -30, 0)), (48, (0, 0, 0))])]))
    A.particles(s, fall, 'Asphalt', (0, 1.0, 3), Shape='Sphere', ShapeRadius=3.5, Lifetime=[0.8, 1.8], Speed=[10, 34], Size=[0.08, 0.3], StartColor=[0.12, 0.12, 0.13],
                StartColor2=[0.3, 0.28, 0.25], EndColor=[0.05, 0.05, 0.05], Gravity=-1.5, Drag=0.2, NoiseStrength=1.0, Blend='Alpha', Lit=False, EmissionRate=0, BurstCount=140,
                MaxParticles=160, Looping=False, Duration=30.0)
    walls = P.looping(s, upper, 'Walls', wall_clip)
    # (A little wider than it was built, so that no part of it comes inside the Wide camera.)
    A.model(s, walls, 'Shaft', A.shaft_walls(V, 15.0, 390.0), (0, 0, 3), (0, 0, 0), (1.14, 1.0, 1.14), shaft_glow, shadows=False)
    # Crags off the walls, as fast as the walls: the same few every 24 m.
    ledge_frames = int(round(24.0 / throat * 30))
    ledge_clip = P.clip(V, 'ShaftLedges', ledge_frames, [P.track('Position', [(0, (0, 0, 0)), (ledge_frames, (0, 24, 0))])])
    ledges = P.looping(s, upper, 'Ledges', ledge_clip)
    rng = random.Random(11)
    crag = A.spikes(V, 'Crag', 5, 1.4, (2.5, 6.0), 4)
    base = [(rng.uniform(0, 2 * math.pi), rng.uniform(0, 24), rng.uniform(70, 110), rng.uniform(1.0, 2.0)) for _ in range(6)]
    for k in range(-3, 3):
        for a, y, tilt, size in base:
            A.model(s, ledges, 'Crag', crag, (math.sin(a) * 12.5, k * 24 + y, math.cos(a) * 12.5 + 3), (tilt, math.degrees(a) + 180, 0), size, shaft_glow, shadows=False)
    A.particles(s, upper, 'Embers racing up', (0, -30, 3), Shape='Box', BoxSize=[24, 6, 24], Lifetime=[0.9, 1.4], Speed=[42, 64], Size=[0.04, 0.1],
                StartColor=[1.0, 0.7, 0.3], StartColor2=[1.0, 0.35, 0.08], EndColor=[1.0, 0.2, 0.03], Intensity=6.0, Gravity=0.0, Drag=0.0, NoiseStrength=1.5,
                NoiseFrequency=0.4, Blend='Additive', EmissionRate=200, MaxParticles=320, Alignment='Stretched', StretchFactor=0.06, FadeIn=0.05)
    A.particles(s, upper, 'Smoke racing up', (0, -30, 3), Shape='Box', BoxSize=[22, 4, 22], Lifetime=[1.2, 1.8], Speed=[34, 46], Size=[2.0, 4.0], EndSize=1.6,
                StartColor=[0.25, 0.08, 0.04], StartColor2=[0.1, 0.06, 0.05], EndColor=[0.06, 0.05, 0.05], StartAlpha=0.22, EndAlpha=0.0, Gravity=0.0, Drag=0.0,
                NoiseStrength=0.8, Blend='Alpha', EmissionRate=26, MaxParticles=60, Texture=A.tex(V, 'Puff'), FadeIn=0.2)
    # The break in the road, far above: a ragged fissure in the dark with the night they fell out
    # of showing through it, moonlight coming down. (Its glow is kept under white so that its
    # shape and colour read from the bottom of the shaft: a soft white glow card was a blank pill.)
    night = (0.42, 0.6, 1.0)
    under, through = A.road_break(V)
    A.model(s, upper, 'The road, far above', under, (0, 150, 3), (0, 0, 0), 1.0, A.mat(V, 'Palette', (1, 1, 1), rough=1.0), shadows=False)
    A.model(s, upper, 'The night through the road', through, (0, 150, 3), (0, 0, 0), 1.0, A.mat(V, 'Palette', (0, 0, 0), glow=night, power=BREAK_GLOW, glow_tex=False), shadows=False)
    s.light('Slit light', upper, (0, 70, 3), 'Spot', (0.7, 0.82, 1.0), 60000.0, 110, rot=(90, 0, 0), inner=5, outer=11)
    s.light('Pit glow', upper, (0, -14, 3), 'Point', (1.0, 0.3, 0.08), 2600.0, 40)
    A.glow_card(s, upper, V, 'The pit', (0, -70, 3), 60.0, (1.0, 0.22, 0.03), 3.0, (90, 0, 0))
    for i, x in enumerate((-3.0, 3.0)):
        s.light(f'Fall wash {i}', fall, (x, -7, -1), 'Spot', (1.0, 0.35, 0.1), 1500.0, 22, rot=look_rotation((x, -7, -1), (x * 0.4, 1.5, 3.5)), inner=22, outer=42, show='Wash', group=i, fog=CIR.FOG)
        s.light(f'Fall wash {i + 2}', fall, (x * 0.5, 12, -2), 'Spot', (0.75, 0.82, 1.0), 1500.0, 24, rot=look_rotation((x * 0.5, 12, -2), (x * 0.3, 1.5, 3.5)), inner=18, outer=36, show='Wash', group=i + 2, fog=CIR.FOG)
    CIR.build(s, fall, V)

    # 3. Hell. They land in its heart frozen ('landed'), and the playing thaws it: Satan's
    # heart kindles and the ice lets go of him and of the stands a tier at a time ('thaw_1' to
    # 'thaw_4'), and on 'thawed' the fire is back (story_afterlife_heart). What only the cold
    # has is under 'frost' (until 'thawed'); what only the fire has is under 'burning' (from it).
    h = P.between(s, root, 'Hell', 'landed', None, 0.4)
    frost = P.between(s, h, 'Frozen', None, 'thawed', 0.0)
    burning = P.between(s, h, 'Fire', 'thawed', None, 0.0)
    C = (0.0, 0.0, 2.0)                       # the arena's centre
    steps, rise, run, z0 = 12, 0.75, 1.5, -7.0
    CAVERN = 64.0                             # its radius: room for the nine tiers of the stands
    top_y = steps * rise
    zt = z0 - steps * run
    A.model(s, h, 'Cavern', A.cavern(V, (0.0, 0.0, -6.0), CAVERN, 44.0), (0, 0, 0), (0, 0, 0), 1.0, A.mat(V, 'Rock', (1, 1, 1), glow=(0.55, 0.09, 0.03), power=0.2), shadows=False)
    A.model(s, h, 'Lava lake', A.lava(V, 160.0), (0, -1.9, -6), (0, 0, 0), 1.0, A.mat(V, 'Lava', (0.2, 0.05, 0.02), glow=(1, 1, 1), power=2.0), shadows=False)
    drift = P.clip(V, 'LavaDrift', 900, [P.track('Position', [(0, (0, 0, 0)), (450, (9, 0, 6)), (900, (0, 0, 0))], 'SmoothStep')])
    A.model(s, P.looping(s, h, 'Lava shimmer', drift), 'Lava crust', A.lava(V, 160.0), (3, -1.86, -9), (0, 37, 0), 1.3,
            A.mat(V, 'Lava', (0, 0, 0), glow=(1.0, 0.6, 0.3), power=0.9, additive=True), shadows=False)
    A.model(s, h, 'Arena', A.arena(V, 15.5, C), (0, 0, 0), (0, 0, 0), 1.0, A.mat(V, 'HellFloor', (1, 1, 1), glow=(1.0, 0.75, 0.5), power=2.4, glow_tex='HellGlow', rough=0.85))
    terrace_model, tiers = A.terraces(V, C)
    A.model(s, h, 'Terraces', terrace_model, (0, 0, 0), (0, 0, 0), 1.0, A.mat(V, 'Rock', (1.25, 1.0, 0.95), glow=(0.5, 0.1, 0.03), power=0.1))
    A.model(s, h, 'Stairs and dais', A.hell_stairs(V, steps, rise, run, z0))
    # Satan on his throne at the back of the dais, the size of the stands (HT.SCALE), frozen
    # into the ice to the waist; his wings beat all along.
    satan = HT.satan(s, h, V, (0.0, top_y, zt - 8.0))
    throne = satan['chest']
    # The rock the throne backs onto.
    massif = A.rock(V, 3)
    rock_mat = A.mat(V, 'Rock', (1, 1, 1), glow=(0.55, 0.09, 0.03), power=0.2, tiling=(4, 4))
    A.model(s, h, 'Massif', massif, (0, -6, zt - 21), (0, 20, 0), (15, 40, 9), rock_mat)
    A.model(s, h, 'Massif shoulder L', massif, (-17, -6, zt - 16), (0, 80, 0), (9, 26, 8), rock_mat)
    A.model(s, h, 'Massif shoulder R', massif, (17, -6, zt - 16), (0, 140, 0), (9, 24, 8), rock_mat)
    # Lava down the rock either side of the throne (ice falls, while it is frozen).
    ice_fall = A.mat(V, 'Lava', (0.5, 0.7, 0.9), glow=(0.3, 0.55, 0.9), power=0.5, tiling=(1, 6))
    for side in (-1, 1):
        x = side * 13.5
        fall_mat = A.mat(V, 'Lava', (0, 0, 0), glow=(1.0, 0.8, 0.6), power=5.0, tiling=(1, 6))
        A.model(s, burning, 'Lava fall', A.lava(V, 160.0), (x, 12, zt - 11.4), (-84, side * 12, 0), (0.016, 1, 0.19), fall_mat, shadows=False)
        A.model(s, frost, 'Ice fall', A.lava(V, 160.0), (x, 12, zt - 11.4), (-84, side * 12, 0), (0.016, 1, 0.19), ice_fall, shadows=False)
        A.glow_card(s, burning, V, 'Lava fall glow', (x, 10, zt - 10.8), 13.0, (1.0, 0.3, 0.05), 0.8)
        s.light('Lava fall light', burning, (x, 8, zt - 8), 'Point', (1.0, 0.35, 0.08), 1400.0, 26, fog=0.1)
        A.particles(s, burning, 'Lava fall spray', (x, -1.2, zt - 9.6), Shape='Cone', ConeAngle=40, ShapeRadius=1.2, Lifetime=[0.8, 1.8], Speed=[3, 9], Size=[0.08, 0.22],
                    StartColor=[1.0, 0.75, 0.3], StartColor2=[1.0, 0.4, 0.08], EndColor=[0.8, 0.1, 0.02], Intensity=6.0, Gravity=1.0, Drag=0.2, NoiseStrength=0.5,
                    Blend='Additive', EmissionRate=40, MaxParticles=90, Alignment='Stretched', StretchFactor=0.05, FadeIn=0.02)
    # Satan in the fire: a key from high on his right, a deep red rim from behind and above, and
    # only a little fill from the lava below, so his red, the three faces and the eyes read. The
    # key is near white (a warm white, half the power it was): with every light on him red or
    # orange the yellow-white and black faces went the red's orange and the close-ups were one
    # bright orange; and the rims are a deep red, not orange, so the edges glow without flooding
    # him. (A strong warm fill washed him out to a pale orange too.)
    face = (0, top_y + 14.5, zt - 8)
    at = (0, 2.5, -13)
    s.light('Satan, from the lava', burning, at, 'Spot', (1.0, 0.3, 0.1), 600.0, 55, rot=look_rotation(at, (0, top_y + 11, zt - 8)), inner=16, outer=30, fog=0.02)
    at = (17, top_y + 26, zt + 14)
    s.light('Satan, key', burning, at, 'Spot', (1.0, 0.78, 0.66), 3800.0, 60, rot=look_rotation(at, face), inner=12, outer=26, fog=0.02)
    for side in (-1, 1):
        at = (side * 9, top_y + 26, zt - 22)
        s.light('Satan, rim', burning, at, 'Spot', (1.0, 0.16, 0.05), 4000.0, 40, rot=look_rotation(at, (0, top_y + 12, zt - 6)), inner=14, outer=30, fog=0.02)
    HT.thaw_lights(s, h, V, throne)
    # Banners off the dais's lintels and down the massif, chains and cages from the roof.
    banner_mat = A.mat(V, 'Banner', (1, 1, 1), glow=(1, 1, 1), power=0.35, both=True)
    sway = P.clip(V, 'BannerSway', 150, [P.track('Rotation', [(0, (0, 0, 0)), (40, (3, 0, 1.5)), (110, (-3, 0, -1.5)), (150, (0, 0, 0))], 'SmoothStep')])
    for i, x in enumerate((-7.85, 7.85)):
        A.model(s, P.looping(s, h, 'Banner', sway, (x, top_y + 8.0, zt - 0.35), speed=0.8 + 0.3 * i), 'Banner', A.banner(V), (0, 0, 0), (0, 0, 0), 1.25, banner_mat)
    for i, x in enumerate((-19, 19)):
        A.model(s, P.looping(s, h, 'Great banner', sway, (x, 27, zt - 11.5), speed=0.5 + 0.2 * i), 'Banner', A.banner(V), (0, 0, 0), (0, -x * 0.8, 0), 3.2, banner_mat)
    swing = P.clip(V, 'CageSwing', 180, [P.track('Rotation', [(0, (0, 0, 0)), (45, (2.5, 0, 4)), (135, (-2.5, 0, -4)), (180, (0, 0, 0))], 'SmoothStep')])
    for i, (x, z, y) in enumerate(((-15, -3, 34), (15, -1, 33), (-22, 12, 31), (22, 10, 32), (-12, -17, 36), (13, -18, 36), (0, 20, 32))):
        A.model(s, P.looping(s, h, 'Cage', swing, (x, y, z), speed=0.6 + 0.12 * i), 'Chain and cage', A.chain_cage(V, 16.0 if i % 2 else 12.0), (0, 0, 0), (0, i * 50, 0), 1.3, shadows=False)
    # Stalactites off the roof, spires out of the lake, the arena's ragged rim.
    stal_a, stal_b, stal_c = A.spikes(V, 'SpikesA', 9, 3.2, (3.0, 9.0), 1), A.spikes(V, 'SpikesB', 6, 2.2, (2.5, 7.0), 2), A.spikes(V, 'SpikesC', 4, 1.2, (1.0, 3.2), 3)
    rng = random.Random(23)
    for i in range(26):
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(6, 46)
        x, z = math.cos(a) * r, -6 + math.sin(a) * r
        roof = -6 + 50 * math.sqrt(max(0.0, 1 - min(1.0, (r / CAVERN) ** (1 / 0.75)) ** 2))
        if abs(x) < 16 and -46 < z < -20:
            continue        # (over Satan's head and wings)
        A.model(s, h, 'Stalactites', (stal_a, stal_b)[i % 2], (x, roof + 2, z), (180, rng.uniform(0, 360), 0), rng.uniform(1.6, 3.2), rock_glow, shadows=False)
    for i in range(22):
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(24, 50)
        x, z = math.cos(a) * r, -6 + math.sin(a) * r
        if abs(x) < 13 and -44 < z < -4 or math.hypot(x - C[0], z - C[2]) < 45 and z > -22 and abs(x) > 12:
            continue
        A.model(s, h, 'Spires', (stal_a, stal_b)[i % 2], (x, -2.5, z), (0, rng.uniform(0, 360), 0), rng.uniform(1.5, 4.2), rock_glow, shadows=False)
    for i in range(16):
        a = 2 * math.pi * i / 16 + rng.uniform(-0.1, 0.1)
        x, z = C[0] + math.cos(a) * 15.6, C[2] + math.sin(a) * 15.6
        if abs(x) < 6 and z < C[2]:
            continue
        A.model(s, h, 'Rim spikes', stal_c, (x, -0.9, z), (0, rng.uniform(0, 360), 0), rng.uniform(0.9, 1.6), rock_glow)
    # Gargoyles and braziers (cold until 'thaw_4', when the braziers catch).
    garg = A.gargoyle(V)
    for side in (-1, 1):
        for i in (0, 4, 8):
            A.model(s, h, 'Gargoyle', garg, (side * 4.45, (i + 1) * rise + 1.6, z0 - i * run - run / 2), (0, -side * 35, 0), 1.0)
    braz = A.brazier(V)
    brazier_at = [(-5.6, 0, z0 + 0.6), (5.6, 0, z0 + 0.6)]
    for a in (-150, -115, -65, -30):
        brazier_at.append((C[0] + 13.8 * math.cos(math.radians(a)), 0, C[2] - 13.8 * math.sin(math.radians(a))))
    for i, at in enumerate(brazier_at):
        A.model(s, h, 'Brazier', braz, at, (0, i * 40, 0), 1.25)
        top = (at[0], at[1] + 1.6, at[2])
        lit = P.between(s, h, 'Brazier alight', 'thaw_4', None, 0.6, top)
        body = P.looping(s, lit, 'Brazier flame', P.clip(V, 'Flicker0', 14, [P.track('Scale', [(0, (1, 1, 1)), (4, (1.15, 1.4, 0.9)), (9, (0.85, 0.75, 1.15)), (14, (1, 1, 1))], 'SmoothStep')]), top, speed=0.9 + 0.1 * (i % 4))
        A.model(s, body, 'Flame', A.flame(V), (0, 0, 0), (0, i * 77, 0), (0.9, 1.5, 0.9), A.mat(V, 'Palette', (0, 0, 0), glow=(1.0, 0.5, 0.12), power=6.0, additive=True, both=True), shadows=False)
        A.particles(s, lit, 'Brazier sparks', top, Shape='Cone', ConeAngle=22, ShapeRadius=0.25, Lifetime=[1.0, 2.4], Speed=[1.0, 3.0], Size=[0.025, 0.06],
                    StartColor=[1.0, 0.8, 0.35], StartColor2=[1.0, 0.5, 0.1], EndColor=[0.8, 0.15, 0.02], Intensity=5.0, Gravity=-0.1, Drag=0.3, NoiseStrength=1.2,
                    Blend='Additive', EmissionRate=9, MaxParticles=30, Alignment='Stretched', StretchFactor=0.08, FadeIn=0.02)
        s.light('Brazier light', lit, (top[0], top[1] + 0.8, top[2]), 'Point', (1.0, 0.45, 0.15), 240.0, 13)
    # Fire out of the lake, and the jets that go up on the big moments. (A jet is the show's,
    # whatever group it is under: until 'thawed' they are held out of sight, far under the floor.)
    for i, (x, z, size) in enumerate(((-30, -24, 3.0), (31, -24, 2.6), (-47, 6, 2.4), (47, 12, 3.2), (-12, -44, 3.4), (13, -45, 3.0))):
        fire(s, burning, V, (x, -1.6, z), size, 700.0, smoke=False, name=f'Lake fire {i}')
    jets = P.play(s, h, 'Fire jets (from thawed)', 'thawed', P.clip(V, 'JetsUp', 2, [P.track('Position', [(0, (0, -300, 0)), (1, (0, 0, 0)), (2, (0, 0, 0))])]))
    for i, (x, z) in enumerate(((-11.5, -5.5), (11.5, -5.5), (-13.5, 9.5), (13.5, 9.5))):
        jet = A.particles(s, jets, f'Fire jet {i}', (x, 0.2, z), Shape='Cone', ConeAngle=6, ShapeRadius=0.25, Lifetime=[0.5, 0.9], Speed=[16, 24], Size=[0.7, 1.3], EndSize=0.4,
                          StartColor=[1.0, 0.8, 0.3], StartColor2=[1.0, 0.45, 0.08], EndColor=[0.8, 0.1, 0.01], Intensity=7.0, Gravity=0.3, Drag=0.6, NoiseStrength=0.6,
                          Blend='Additive', EmissionRate=0, BurstCount=0, MaxParticles=400, Texture=A.tex(V, 'Puff'), FadeIn=0.05)
        jet.add({'Type': 'VenueAccent', 'Beats': 4, 'Particles': 320})
    A.particles(s, burning, 'Embers on the air', (0, 4, 0), Shape='Box', BoxSize=[70, 6, 70], Lifetime=[5.0, 10.0], Speed=[0.4, 1.6], Size=[0.03, 0.08],
                StartColor=[1.0, 0.7, 0.3], StartColor2=[1.0, 0.35, 0.08], EndColor=[0.9, 0.12, 0.02], Intensity=5.0, Gravity=-0.03, Drag=0.1, NoiseStrength=1.0,
                NoiseFrequency=0.3, Blend='Additive', EmissionRate=45, MaxParticles=420, FadeIn=0.1)
    A.particles(s, burning, 'Heat haze off the lake', (0, -1, -6), Shape='Box', BoxSize=[100, 1, 100], Lifetime=[6.0, 10.0], Speed=[0.6, 1.5], Size=[5.0, 9.0], EndSize=1.8,
                StartColor=[0.5, 0.1, 0.03], StartColor2=[0.3, 0.05, 0.02], EndColor=[0.1, 0.02, 0.01], StartAlpha=0.12, EndAlpha=0.0, Gravity=-0.02, Drag=0.1,
                NoiseStrength=0.4, NoiseFrequency=0.2, Blend='Alpha', EmissionRate=7, MaxParticles=80, Texture=A.tex(V, 'Puff'), FadeIn=0.3)
    HT.eruption(s, h, V)
    # Bats, back with the fire.
    spin = P.clip(V, 'BatsCircle', 600, [P.track('Rotation', [(0, (0, 0, 0)), (200, (0, 120, 0)), (400, (0, 240, 0)), (600, (0, 359.9, 0))])])
    # The wings beat about their roots (the Wings ring's height scaled through 0: up, down past
    # level, up), the bodies holding their line; each ring a few layers a little above one another,
    # out of step, for a flock rather than a disc.
    flap = P.clip(V, 'BatsFlap', 8, [P.track('Scale', [(0, (1, 1, 1)), (3, (1, -1.1, 1)), (8, (1, 1, 1))], 'SmoothStep')])
    for i, (y, r, sp, tilt) in enumerate(((17, 15, 1.0, 6), (23, 24, -0.7, -9), (13, 9, 1.5, 12), (29, 32, 0.5, 4))):
        ring = P.looping(s, s.entity('Bats', burning, (0, y, 2), (tilt, 0, tilt * 0.5)), 'Circling', spin, speed=sp)
        # (One ring of six is drawn once, A.prop's cache, and each layer turned round from the last.)
        for k, dy in enumerate((-0.9, 0.0, 0.8)):
            layer = s.entity(f'Bats {k}', ring, (0, dy * r / 15.0, 0), (0, 40 * k + 17 * i, 0))
            A.model(s, layer, 'Bats', A.bats(V, 6), (0, 0, 0), (0, 0, 0), (r, r, r), shadows=False)
            A.model(s, P.looping(s, layer, 'Flapping', flap, speed=(1.0 + 0.2 * i) * (1.0 + 0.13 * k)), 'Wings', A.bats(V, 6, part='Wings'), (0, 0, 0), (0, 0, 0), (r, r, r), shadows=False)
    # The rig, back with the fire: beams off the terraces, blinders on the dais, strobes in the
    # roof. (While it is frozen the light is the cold's, HT.frozen_floor.)
    for i, (x, c) in enumerate(((-3.5, (1.0, 0.25, 0.05)), (3.5, (1.0, 0.1, 0.05)), (-1.2, (1.0, 0.45, 0.1)), (1.2, (0.9, 0.15, 0.1)))):
        s.light(f'Wash {i}', burning, (x, 7, -1), 'Spot', c, 1600.0, 18, rot=look_rotation((x, 7, -1), (x * 0.4, 1, 3.5)), inner=22, outer=42, show='Wash', group=i)
    for i, (x, z) in enumerate(((-24, 10), (24, 10), (-21, -4), (21, -4))):
        at = (x, 9, z)
        s.light(f'Beam {i}', burning, at, 'Spot', (1.0, 0.2, 0.05) if i % 2 else (1.0, 0.5, 0.1), 4000.0, 50, rot=look_rotation(at, (0, 2, 3.5)), inner=3, outer=7, show='Beam', group=i)
    for i, x in enumerate((-6.2, 6.2)):
        s.light(f'Blinder {i}', burning, (x, top_y + 7.6, zt - 0.3), 'Spot', (1.0, 0.6, 0.3), 2500.0, 60, rot=look_rotation((x, top_y + 7.6, zt - 0.3), (x * 0.3, 1, 3)), inner=12, outer=24, show='Blinder', group=i)
        s.light(f'Strobe {i}', burning, (x * 1.6, 14, 6), 'Point', (1.0, 0.85, 0.7), 2500.0, 32, show='Strobe', group=i)
    for side in (-1, 1):
        s.light('Floor fill', burning, (side * 7, 6, 2), 'Point', (1.0, 0.35, 0.15), 200.0, 18)
        s.light('Lake glow', burning, (side * 24, 1.5, -22), 'Point', (1.0, 0.3, 0.05), 800.0, 40)
        s.light('Lake glow', burning, (side * 30, 1.5, 22), 'Point', (1.0, 0.3, 0.05), 800.0, 40)
    s.light('Lake glow, behind', burning, (0, 1.5, 24), 'Point', (1.0, 0.3, 0.05), 800.0, 40)
    s.light('Stair glow', burning, (0, 5, z0 - 6), 'Point', (1.0, 0.3, 0.08), 600.0, 16)
    HT.frozen_floor(s, frost, V, C, 15.5, satan['feet'])

    # Demons: on the plinths, on the floor round three sides, and up the terraces. Each tier
    # (and the floor) stands frozen in statues of ice until it thaws (HT.frozen_crowd): then the
    # statues slide off them, and they dance with the beat as much as the playing moves them.
    demon_poses = {'cheer': P.CHEER, 'fists': P.FISTS, 'stand': P.STANDING}
    bodies = (('Daughter_01', '01_C'), ('Mother_01', '03_C'), ('SchoolGirl_01', '04_A'), ('Son_01', '03_B'), ('Mother_02', '02_B'), ('SchoolBoy_01', '02_A'))
    models = {}
    for b, v in bodies:
        for k, pose in demon_poses.items():
            models[(b, k)] = P.figure(V, f'Demon_{b}_{k}', b, v, pose, 'a demon')
    horn_m = A.horns(V)
    crowds = {}
    thawed = {}

    def thawed_in(key):
        # Where a tier's demons are: out of sight under the floor until the moment their statues
        # start to slide off them (HT.thawed_clip), then in their places, dancing.
        if key not in thawed:
            flag, delay = HT.THAW_AT[key]
            thawed[key] = P.play(s, h, f'Thawed {"floor" if key == "floor" else f"tier {key + 1}"}', flag, HT.thawed_clip(V, delay))
        return thawed[key]

    def demon(parent, at, yaw, b, k, turns=True, scale=1.0, tier='floor'):
        # Facing the band; on the encore (encore_called) each turns to the throne.
        g = s.entity('Demon', parent, at, (0, yaw, 0), (scale, scale, scale))
        if turns:
            g = P.play(s, g, 'Turn', 'encore_called', P.turn_clip(V, P.wrap(P.yaw_to(at, throne) - yaw), 1.2 + 0.4 * ((int(at[0] * 7) % 5) / 4.0)))
        g = s.entity('Dancing', g)
        if k != 'stand':
            # Down into the knees on the beat (inside the statue while frozen): every one or two
            # beats, on or off it, by where it stands.
            n = int(abs(at[0] * 3 + at[2] * 5))
            g.add({'Type': 'VenueBeat', 'Offset': [0.0, -0.16 - 0.04 * (n % 3), 0.0], 'Every': (1.0, 2.0, 1.0)[n % 3], 'Phase': (0.0, 0.0, 0.5)[n % 3], 'Calm': 0.25})
        g.add({'Type': 'Model', 'ModelPath': models[(b, k)]})
        A.model(s, g, 'Horns', horn_m, (0, 1.7, 0.02), (-6, 0, 0), 1.0, shadows=False)
        if tier is not None:
            crowds.setdefault(tier, {}).setdefault('figures', []).append((b, demon_poses[k], at, yaw, scale))
        return g
    rng = random.Random(23)
    for side in (-1, 1):
        for i in (2, 6, 10):
            b, _ = bodies[(i + side) % len(bodies)]
            demon(thawed_in('floor'), (side * 4.45, (i + 1) * rise + 1.6, z0 - i * run - run / 2), 90 * side + 180 + rng.uniform(-30, 30), b, 'cheer' if i % 4 == 2 else 'stand')
    for i in range(60):
        side = i % 3
        if side == 0:
            at = (rng.uniform(-12, -5.0), 0, rng.uniform(-4, 8))
        elif side == 1:
            at = (rng.uniform(5.0, 12), 0, rng.uniform(-4, 8))
        else:
            # An aisle up the middle, from the band to the foot of the stairs.
            at = (rng.choice((-1, 1)) * rng.uniform(2.2, 5.5), 0, rng.uniform(-6.0, -2.2))
        yaw = math.degrees(math.atan2(-at[0], DRUMMER[1] - 1.5 - at[2])) + rng.uniform(-20, 20)
        b, _ = bodies[i % len(bodies)]
        demon(thawed_in('floor'), at, yaw, b, ('cheer', 'fists', 'stand')[rng.randrange(3)])
    # The stands: nine tiers, one for each circle they fell through, the first circle's at the top.
    # The three by the floor are demons like the floor's; above them each tier's crowd is three
    # blocks of one mesh each (dipping out of step), and every tier's torches burn its circle's
    # colour (lit as the tier thaws).
    block_mat = A.mat(V, 'Palette', (1, 1, 1), glow=(1.0, 0.45, 0.25), power=0.45)
    for side in (-1, 1):
        for k, (r0, y, arc0, arc1) in enumerate(tiers):
            n = 12 + 3 * k
            spots = []
            for i in range(n):
                deg = arc0 + 6 + (arc1 - arc0 - 12) * (i + rng.uniform(0.1, 0.9)) / n
                at = A.terrace_point(C, side, r0 + rng.uniform(0.5, 2.0), deg, y)
                yaw = math.degrees(math.atan2(C[0] - at[0], C[2] + 1.5 - at[2])) + rng.uniform(-15, 15)
                if k < 3:
                    b, _ = bodies[(i + k) % len(bodies)]
                    demon(thawed_in(k), at, yaw, b, ('cheer', 'fists', 'cheer', 'stand')[rng.randrange(4)], turns=False, scale=1.0 + 0.12 * k, tier=k)
                else:
                    spots.append((at, yaw))
            for j in range(3 if spots else 0):
                name, seed, size = f'Stands_{k}_{0 if side < 0 else 1}_{j}', 500 + k * 10 + j + (side > 0) * 5, 1.3 + 0.07 * k
                block = A.model(s, thawed_in(k), f'Tier {k + 1} crowd', CIR.stands_crowd(V, name, spots[j::3], size, seed), (0, 0, 0), (0, 0, 0), 1.0, block_mat, shadows=False)
                block.add({'Type': 'VenueBeat', 'Offset': [0.0, -0.22, 0.0], 'Every': (1.0, 2.0, 1.0)[(j + k) % 3], 'Phase': (0.0, 0.0, 0.5)[(j + k) % 3], 'Calm': 0.25})
                crowds.setdefault(k, {}).setdefault('blocks', []).append(CIR.stands_crowd(V, name + '_Ice', spots[j::3], size * 1.05, seed))
            # Torches along each tier, their flames its circle's colour (the three tiers by the floor are lit by theirs).
            colour = CIR.tier_colour(k)
            flame_mat = A.mat(V, 'Palette', (0, 0, 0), glow=(0.25 + 0.75 * colour[0], 0.25 + 0.75 * colour[1], 0.25 + 0.75 * colour[2]), power=6.0, additive=True, both=True)
            alight = P.between(s, h, f'Tier {k + 1} torches', HT.THAW_AT[k][0], None, 0.0)
            for deg in ((-60, -20, 20) if k < 3 else (arc0 + 14, arc1 - 10)):
                at = A.terrace_point(C, side, r0 + A.TIER_STEP - 0.25, deg, y)
                s.box('Torch pole', h, (at[0], y + 1.3, at[2]), (0.1, 2.6, 0.1), (0.1, 0.08, 0.06), shape='Cylinder', shadows=False)
                A.model(s, alight, 'Torch flame', A.flame(V), (at[0], y + 2.6, at[2]), (0, deg, 0), (0.6, 1.1, 0.6) if k < 3 else (1.0, 2.0, 1.0), flame_mat, shadows=False)
                if k < 3:
                    s.light('Torch light', alight, (at[0], y + 3.2, at[2]), 'Point', (1.0, 0.45, 0.15), 170.0, 12)
    HT.guests(s, burning, V, tiers, C, random.Random(77))
    # The demon on the steps who catches a fill.
    step3 = (1.4, 3 * rise, z0 - 2.5 * run)
    catch = P.figure(V, 'Demon_catch', 'Daughter_01', '01_C', P.CROUCH_CATCH, 'the demon catching a fill')
    look = P.figure(V, 'Demon_looks_back', 'Daughter_01', '01_C', P.TURN_BACK, 'the demon looking back at the throne')
    demon_g = P.between(s, h, 'Step demon', None, 'demon_catch', 0.2, step3)
    demon(demon_g, step3, 180, 'Daughter_01', 'stand', turns=False, tier=None)
    caught = P.between(s, h, 'Step demon caught', 'demon_catch', None, 0.2, step3)
    P.place(s, caught, 'Demon catching', catch, step3, 180)
    s.light('Step demon light', h, (step3[0] + 1.2, step3[1] + 1.8, step3[2] + 1.6), 'Point', (1.0, 0.6, 0.3), 90.0, 6)
    A.model(s, caught, 'Horns', horn_m, (step3[0], step3[1] + 1.05, step3[2] - 0.75), (60, 180, 0), 1.0, shadows=False)
    P.place(s, P.between(s, h, 'Step demon looks', 'satan_nods', None, 0.2, (step3[0] + 0.8, step3[1], step3[2])), 'Demon looking back', look, (step3[0] + 0.8, step3[1], step3[2]), 0)
    HT.frozen_crowd(s, frost, V, crowds, tiers, C)
    # The smoke that lifts them out: white, up from the floor round the band.
    smoke = P.between(s, root, 'Smoke', 'smoke_rises', None, 1.5)
    A.particles(s, smoke, 'Smoke rising', (0, 0.2, 3.2), Shape='Box', BoxSize=[12, 0.4, 10], Lifetime=[4.0, 7.0], Speed=[2.5, 5.0], Size=[1.6, 3.2], EndSize=2.6,
                StartColor=[0.9, 0.9, 0.95], StartColor2=[0.75, 0.75, 0.8], EndColor=[1.0, 1.0, 1.0], StartAlpha=0.55, EndAlpha=0.0, Gravity=-0.12, Drag=0.2,
                NoiseStrength=0.6, NoiseFrequency=0.3, Blend='Alpha', EmissionRate=38, MaxParticles=260, Texture=A.tex(V, 'Puff'), FadeIn=0.15, AngularVelocity=[-15, 15])
    A.glow_card(s, smoke, V, 'The way up, its mouth', (0, 58, 3.5), 14.0, (1.0, 0.98, 0.92), 5.0, (-90, 0, 0))
    s.light('Smoke glow', smoke, (0, 14, 3), 'Spot', (1, 0.98, 0.94), 26000.0, 40, rot=(90, 0, 0), inner=14, outer=26)

    # A few more places to shoot the show from. The director cuts to them all song, the crash
    # site and the fall too, so they stand within 9 m of the shaft's axis, inside the lips of
    # every circle's ledges (out over the lake, on the terraces or at the head of the stairs they
    # were outside the shaft's wall all down the fall, and shot the band through it, small, from
    # beyond it). Behind the band, toward the throne up the stairs (not up at it: at the crash and
    # in the sky that was a picture of the night with the band small in a corner); low on the
    # island's edge, side on to the band; high over the island behind it; high in front of it,
    # over the foot of the stairs.
    s.camera_spot('Camera behind the band', marks, (4.6, 2.4, 9.5), (0, 4.0, -16.0), 'Custom', 42, 'behind')
    s.camera_spot('Camera low, side on', marks, (-8.6, 1.0, 0.4), (0, 2.0, 3.4), 'Custom', 44, 'side')
    s.camera_spot('Camera high behind', marks, (6.5, 9.5, 9.0), (0, 1.2, 2.5), 'Custom', 46, 'high')
    s.camera_spot('Camera over the stairs', marks, (1.0, 10.5, -5.0), (0, 1.0, 3.5), 'Custom', 40, 'stairs')

    # Story shots.
    shot(s, marks, 'ghost_hand', beside_hand(hand, 180, 0.95, 0.6, 0.12), (hand[0], 0.05, hand[2]), 28, 9, focus=True,
         via=[(beside_hand(hand, 180, 1.1, 0.8, 0.3), (hand[0], 0.35, hand[2]), 32)],
         end=(beside_hand(hand, 180, 2.0, 1.8, 1.0), (hand[0] + 0.3, 1.1, hand[2] + 0.2), 42))
    # (Past the cruiser high and to the outside of it, toward the burning rig: low and aimed at the
    # band, the move went straight through its light bar, which filled the picture.)
    shot(s, marks, 'crash_survey', (-11.5, 1.25, -15.5), (-6.5, 1.3, -8.5), 38, 8, hand=True, lead='r',
         via=[((-11.0, 3.0, -12.5), (10.0, 1.5, 0.0), 42)], end=((-3.5, 2.8, -11.0), (10.5, 2.0, 5.5), 46))
    # The tease: down past the drummer to the cop as the road drops away; up into the light. Then
    # the last chorus, one of them at a time, close and from below with the light over them
    # (aloft: their heads are about LIFT over the floor's): the singer, the guitarist, the bassist,
    # and the drummer at the kit, tilting up off them to the gates. The singer's plea through
    # their own eyes, their hand up into the light. The light out; the apex, wide and held; the
    # free fall back down onto the crash; the road. From the singer to the free fall each holds a
    # little past the next one's cue (the later shot takes the screen where two overlap): ending
    # on the cue to the hundredth left a frame or two of the director's own cut between them.
    shot(s, marks, 'ascent', (1.6, 5.5, 1.0), (kneel_at[0], -5, kneel_at[2]), 50, 10, hand=True, end=((1.0, 8.0, 0.5), (kneel_at[0], -40, kneel_at[2]), 40))
    shot(s, marks, 'heavens_light', (-3.5, 0.8, -2.5), (0.5, 12, 4), 52, 9, end=((-2.5, 1.2, -4.0), (0, 40, 3), 60))
    head = {k: (x, HEAD_ALOFT, z) for k, (x, z) in (('vocals', VOCALS), ('guitar', GUITAR), ('bass', BASS))}
    v, g, b = head['vocals'], head['guitar'], head['bass']
    shot(s, marks, 'chorus_singer', (v[0] + 0.75, v[1] - 0.95, v[2] - 1.7), (v[0] + 0.1, v[1], v[2]), 50, 8.05, hand=True, lead='l',
         end=((v[0] + 0.65, v[1] - 0.85, v[2] - 1.55), (v[0] + 0.15, v[1], v[2]), 44))
    shot(s, marks, 'chorus_guitar', (g[0] - 1.3, g[1] - 0.9, g[2] - 1.6), g, 38, 7.65, hand=True, lead='l',
         end=((g[0] - 1.05, g[1] - 0.75, g[2] - 1.3), (g[0] + 0.15, g[1], g[2]), 34))
    shot(s, marks, 'chorus_bass', (b[0] - 0.9, b[1] - 1.1, b[2] - 1.6), b, 38, 7.4, hand=True, lead='r',
         end=((b[0] - 0.75, b[1] - 0.95, b[2] - 1.3), b, 34))
    kit = (DRUMMER[0] - 0.05, HEAD_ALOFT - 0.2, DRUMMER[1] + 0.3)     # the drummer's head, on the throne
    shot(s, marks, 'chorus_drums', (kit[0] + 1.3, kit[1] - 0.5, kit[2] - 2.3), kit, 44, 7.8, hand=True, lead='r',
         end=((kit[0] + 1.3, kit[1] - 0.15, kit[2] - 1.6), (0.2, 45, 6.0), 56))
    # (The eyes: at the face, not in the head: from inside it a ghost's shell is its own head, and
    # nothing of it behind that is drawn. Up 28 degrees, so the hand and the light
    # just beyond it, 43 and 47 degrees up, sit high in the picture, out to the left.)
    shot(s, marks, 'reach', PLEA_EYES, (PLEA_EYES[0], PLEA_EYES[1] + 18.8, PLEA_EYES[2] - 35.3), 72, 6.35, hand=True,
         end=(PLEA_EYES, (PLEA_EYES[0], PLEA_EYES[1] + 20.6, PLEA_EYES[2] - 34.3), 66))
    shot(s, marks, 'denied', (2.5, 1.2, -4.0), (0, 9, 3), 70, 1.55, hand=True, lead='l', end=((2.3, 1.3, -3.6), (0, 10, 3), 72))
    shot(s, marks, 'apex', (-11.0, 1.0, -7.0), (0, 3.0, 3.0), 46, 4.85, lead='r', end=((-10.5, 1.4, -6.6), (0, 3.0, 3.0), 44))
    # (Out to the side of them and tipped 18 degrees off straight down toward them: that near
    # straight down the Director keeps the picture's top toward +z, so they are to one side of it
    # and the crash, almost straight down under the lens, to the other.)
    shot(s, marks, 'free_fall', (-4.5, 8.5, 3.0), (10.3, -37.1, 3.0), 70, 3.85, hand=True, end=((-4.2, 8.0, 3.0), (10.6, -37.1, 3.0), 74))
    # Back at the crash, on the shoulder behind the burning truck as they come down at it: the
    # camera stands on the Earth, so it rides up with it (EarthComesBack, from 'earth_back'; this
    # shot is RETURNS_AT seconds into that, and lasts until the road reaches them), low by the
    # burning truck, up at the sky where they streak in, tilting down with them to the road (the
    # lead keeps the truck to one side and them to the other).
    RETURNS_AT = PLUNGE - 2.24
    views = []
    eye_at = (11.5, 1.0, -5.0)                       # low by the truck's near end (on the Earth)
    toward = (VOCALS[0] - eye_at[0], VOCALS[1] + 2.0 - eye_at[2])
    flat = math.hypot(*toward)
    for k in range(9):
        t = RETURNS_AT + (PLUNGE - RETURNS_AT) * k / 8
        y = earth_y(t)
        up = math.radians(34 - 26 * k / 8)          # up at the sky they come out of, down with them
        eye = (eye_at[0], y + eye_at[1], eye_at[2])
        views.append((eye, (eye[0] + 10 * math.cos(up) * toward[0] / flat, eye[1] + 10 * math.sin(up), eye[2] + 10 * math.cos(up) * toward[1] / flat), 74))
    shot(s, marks, 'crash_returns', *views[0], PLUNGE - RETURNS_AT, hand=True, lin=True, lead='l', via=views[1:-1], end=views[-1])
    shot(s, marks, 'ghosts_stand', (-6.5, 0.5, -3.5), (0.5, 1.2, 3.4), 40, 11, lead='l',
         via=[((-2.0, 1.4, -8.5), (0.8, 1.3, 3.4), 44), ((5.0, 3.2, -11.5), (1.5, 1.2, 3.4), 48)],
         end=((-1.0, 7.5, -17.0), (2.5, 1.0, 3.0), 52))
    shot(s, marks, 'cop_runs', (-8.6, 1.0, -1.5), (car_door[0], 1.1, car_door[2]), 40, 3.2, hand=True, end=((-4.4, 1.3, 3.0), (kneel_at[0], 0.8, kneel_at[2]), 44))
    shot(s, marks, 'cop_kneels', (-3.2, 0.55, DRUMMER[1] - 0.6), (0.2, 1.3, DRUMMER[1] + 0.9), 38, 7, hand=True, focus=True, lead='l',
         end=((-3.0, 0.8, kneel_at[2] - 1.6), (kneel_at[0] + 0.3, 0.7, kneel_at[2]), 30))
    shot(s, marks, 'fell', (2.2, 0.4, -0.8), (0, 2.0, 3.0), 66, 4, hand=True, ride=3, lead='r', via=[((1.6, 0.7, -1.1), (0, 20, 4.0), 72)], end=((1.0, 1.0, -1.4), (0, 140, 3.2), 50))
    # The circles: no cut as one comes (the swap is the show), and the fall never slows to look.
    # The looking is done from inside them (CIR.shots): a camera among each circle's damned,
    # going up with the rock, framing them clear of the note highway as the band zips past; in
    # Lust also round the band with the hurricane, in Gluttony over Cerberus's shoulder and after
    # him as he gives chase. Each runs at one speed, timed to where its ledge is.
    for view in CIR.shots():
        views = view['views']
        shot(s, marks, view['flag'], *views[0], view['hold'], end=views[-1], via=views[1:-1], lin=True, hand=view.get('hand', False), lead=view.get('lead'))
    # The floor's: Free Bird's from the landing on, and Bat Country's (story_afterlife_heart).
    HT.shots(shot, s, marks, satan, z0, top_y, zt, step3)
    write(s, V, 'Hell', ambience=None)


# ---- heaven -------------------------------------------------------------------------------------
SKY_RADIUS = 185.0      # heaven's sky dome
SKY_POWER = 1.3         # its glow


def angel(s, parent, venue, centre, scale, eyes_flag=None, name='Angel', turn_flag=None, look_at=None, fade=2.5, bright=1.0):
    """Wheels within wheels turning about a great eye, eyes all round their rims, and three pairs of
    wings behind; it faces +z (the band). The inner wheels are tipped out of the face's plane and
    wheel round its axis like a coin settling; they never turn edge on to whoever it faces, so no
    rim crosses the eye. eyes_flag: until then it is only gold rings, an arch
    standing in the cloud (fade: how long the change takes; 0 for a cut). turn_flag: it turns to
    look at look_at then. bright: its glow, turned up for one far off in the haze."""
    g = s.group(name, parent, centre)
    if turn_flag and look_at:
        flat = math.hypot(look_at[0] - centre[0], look_at[2] - centre[2])
        g = P.play(s, g, 'Turn', turn_flag, P.turn_clip(venue, P.wrap(P.yaw_to(centre, look_at)), 2.5, math.degrees(math.atan2(centre[1] - look_at[1], flat))))
    r = 3.2 * scale
    gold = A.mat(venue, 'Palette', (1, 1, 1), glow=(1, 1, 1), power=1.3 * bright, metallic=0.6, rough=0.35)
    spin_a = P.clip(venue, 'RingSpinA', 900, [P.track('Rotation', [(0, (0, 0, 0)), (300, (0, 0, 120)), (600, (0, 0, 240)), (900, (0, 0, 359.9))])])
    spin_b = P.clip(venue, 'RingSpinB', 1200, [P.track('Rotation', [(0, (0, 0, 0)), (400, (0, 0, -120)), (800, (0, 0, -240)), (1200, (0, 0, -359.9))])])
    spin_c = P.clip(venue, 'RingSpinC', 1000, [P.track('Rotation', [(0, (0, 0, 0)), (333, (0, 0, 120)), (666, (0, 0, 240)), (1000, (0, 0, 359.9))])])
    awake = P.between(s, g, 'Awake', eyes_flag, None, fade) if eyes_flag else g
    if eyes_flag:
        asleep = P.between(s, g, 'Asleep', None, eyes_flag, fade)
        plain = A.torus(venue, 'PlainRing', 1.0, 0.11)
        A.model(s, asleep, 'Ring', plain, (0, 0, 0), (0, 0, 0), r, gold, shadows=False)
        A.model(s, asleep, 'Ring', plain, (0, 0, 0), (0, 0, 14), r * 0.86, gold, shadows=False)
    A.model(s, P.looping(s, awake, 'Wheel A', spin_a), 'Wheel', A.angel_ring(venue, 'AngelRingA', 1.0, 0.11, 14, 'z'), (0, 0, 0), (0, 0, 0), r, gold, shadows=False)
    A.model(s, P.looping(s, awake, 'Wheel B', spin_b, speed=0.8), 'Wheel', A.angel_ring(venue, 'AngelRingB', 1.0, 0.1, 12, 'out'), (0, 0, 0), (34, 0, 0), r * 0.86, gold, shadows=False)
    A.model(s, P.looping(s, awake, 'Wheel C', spin_c, speed=0.7), 'Wheel', A.angel_ring(venue, 'AngelRingB', 1.0, 0.1, 12, 'out'), (0, 0, 0), (0, 26, 0), r * 0.72, gold, shadows=False)
    A.model(s, awake, 'Heart eye', A.angel_eye(venue), (0, 0, 0), (0, 0, 0), 0.95 * scale, A.mat(venue, 'Palette', (1, 1, 1), glow=(1, 1, 1), power=1.6 * bright), shadows=False)
    feather = A.mat(venue, 'Palette', (1, 1, 1), glow=(1, 1, 1), power=0.85 * bright, both=True)
    for i, (ang, length, rest) in enumerate(((34, 1.7, 0), (2, 2.0, 6), (-30, 1.5, 12))):
        beat = P.clip(venue, f'WingBeat{i}', 110 + 20 * i, [P.track('Rotation', [(0, (0, 0, 0)), (55 + 10 * i, (0, 0, 9 - 2 * i)), (110 + 20 * i, (0, 0, 0))], 'SmoothStep')])
        for side in (-1, 1):
            root = (side * r * 0.75, r * 0.3 * math.sin(math.radians(ang)), -0.5 * scale)
            flap = P.looping(s, s.entity('Wing', g, root, (0, 0 if side > 0 else 180, side * ang)), 'Beat', beat, speed=0.8 + 0.1 * (int(abs(centre[0])) % 3))
            A.model(s, flap, 'Wing', A.wing(venue), (0, 0, 0), (0, 0, 0), length * r, feather, shadows=False)
    return g


def heaven():
    V = 'StoryHeaven'
    s = Scene(seed=6603)
    s.venue = V
    root = s.group('Highway to the Afterlife: heaven')
    marks = s.group('Markers', root)
    s.info(marks, 'Heaven', 'Drumsmith', outdoor=False, half_width=60, desk_z=-20,
           ambient=(0.55, 0.66, 0.9), fog_color=(0.42, 0.5, 0.68), haze=0.035, quiet_look=False)
    band(s, marks, 0.0)
    s.camera_spot('Camera Wide', marks, (0, 4.2, -5.2), (0, 1.9, 4), 'Wide', 60)
    s.camera_spot('Camera Crane', marks, (-9, 7, 13), (0, 2, 2), 'Crane', 55)
    s.camera_spot('Camera Desk', marks, (2.4, 2.3, -4.6), (0, 2, 4), 'Desk', 34)
    s.light('Sun', marks, (0, 80, -40), 'Directional', (1.0, 0.93, 0.8), 2.8, 400, rot=(42, 150, 0), shadows=True, show='Static')
    for i, x in enumerate((-3.5, 3.5, -1.2, 1.2)):
        s.light(f'Wash {i}', marks, (x, 8, -2), 'Spot', (1.0, 0.92, 0.75), 1200.0, 18, rot=look_rotation((x, 8, -2), (x * 0.4, 1, 3.5)), inner=22, outer=42, show='Wash', group=i)
    rng = random.Random(31)
    cloud_mat = A.mat(V, 'Palette', (1, 1, 1), glow=(0.84, 0.89, 1.0), power=0.5, rough=1.0)
    cloud_gold = A.mat(V, 'Palette', (1, 0.95, 0.85), glow=(1.0, 0.84, 0.66), power=0.55, rough=1.0)
    clouds_m = [A.cloud(V, k) for k in range(1, 5)]

    # The sky everything stands in, the sun, and the sea of cloud far below.
    # The engine's fog thickens with distance, so the sky is a dome only as far out as it has to
    # be (its light turned up to come through): past the tips of the great angel's wings and its
    # glory, which reach 155 m from the dome's middle. The far scenery stands well inside it.
    A.model(s, root, 'Sky', A.sky_dome(V, 'SkyDome', 'Sky', SKY_RADIUS), (0, 0, -10), (0, 0, 0), 1.0, A.mat(V, 'Sky', (0, 0, 0), glow=(1, 1, 1), power=SKY_POWER), shadows=False)
    A.model(s, root, 'Cloud sea', A.cloud_sea(V), (0, -52, 0), (0, 0, 0), (0.2, 0.3, 0.2), cloud_mat, shadows=False)
    for i in range(26):
        a = 2 * math.pi * i / 26 + rng.uniform(-0.1, 0.1)
        r = rng.uniform(78, 112)
        sc = rng.uniform(14, 30)
        A.model(s, root, 'Cloud tower', clouds_m[i % 4], (math.cos(a) * r, rng.uniform(-50, -12), -10 + math.sin(a) * r), (0, rng.uniform(0, 360), 0),
                (sc, sc * rng.uniform(0.8, 1.8), sc), cloud_gold if i % 3 == 0 else cloud_mat, shadows=False)
    for i in range(7):
        a = 2 * math.pi * i / 7 + 0.4
        r = rng.uniform(70, 100)
        sc = rng.uniform(3.5, 6.5)
        A.model(s, root, 'Far temple', A.island(V, 1 + i % 3), (math.cos(a) * r, rng.uniform(6, 40), -10 + math.sin(a) * r), (0, rng.uniform(0, 360), 0), sc,
                A.mat(V, 'Palette', (1, 1, 1), glow=(0.9, 0.9, 1.0), power=0.6), shadows=False)

    # The ascent: cloud streaming down past them in three depths, wisps across the lens.
    up = P.between(s, root, 'The ascent', None, 'touchdown', 1.2)
    for depth, (count, r0, r1, size0, size1, period, frames) in enumerate(((26, 5, 14, 2.0, 4.5, 90.0, 300), (26, 16, 40, 6.0, 12.0, 160.0, 800), (14, 46, 80, 14.0, 24.0, 240.0, 2400))):
        clip = P.clip(V, f'CloudsFalling{depth}', frames, [P.track('Position', [(0, (0, 0, 0)), (frames, (0, -period, 0))])])
        body = P.looping(s, up, f'Clouds {depth}', clip)
        layout = [(rng.uniform(0, 2 * math.pi), rng.uniform(r0, r1), rng.uniform(0, period), rng.uniform(size0, size1), rng.randrange(4)) for _ in range(count)]
        for copy in (-1, 0, 1):
            for a, r, y, size, kind in layout:
                A.model(s, body, 'Cloud', clouds_m[kind], (math.sin(a) * r, y + copy * period, math.cos(a) * r + 3), (0, math.degrees(a) * 3, 0),
                        (size, size * 0.8, size), cloud_gold if kind == 0 else cloud_mat, shadows=False)
    A.particles(s, up, 'Wisps', (0, 14, 3), Shape='Box', BoxSize=[26, 4, 26], Lifetime=[2.5, 4.0], Speed=[0.0, 0.5], Size=[1.5, 3.5], EndSize=1.8,
                StartColor=[1.0, 1.0, 1.0], StartColor2=[0.9, 0.93, 1.0], EndColor=[1.0, 1.0, 1.0], StartAlpha=0.26, EndAlpha=0.0, Gravity=0.75, Drag=0.0,
                NoiseStrength=0.4, NoiseFrequency=0.3, Blend='Alpha', EmissionRate=22, MaxParticles=120, Texture=A.tex(V, 'Puff'), FadeIn=0.25, AngularVelocity=[-10, 10])
    A.particles(s, up, 'Motes', (0, 2, 3), Shape='Box', BoxSize=[18, 12, 18], Lifetime=[3.0, 6.0], Speed=[0.1, 0.5], Size=[0.02, 0.05],
                StartColor=[1.0, 0.9, 0.6], StartColor2=[1.0, 1.0, 0.9], EndColor=[1.0, 0.85, 0.5], Intensity=3.0, Gravity=0.25, Drag=0.2, NoiseStrength=0.5,
                Blend='Additive', EmissionRate=30, MaxParticles=160, FadeIn=0.2)

    # The floor of cloud, the stairs, the gates and God's platform.
    floor = P.between(s, root, 'The floor', 'touchdown', None, 1.0)
    steps, rise, run, z0 = 14, 0.75, 1.4, -6.0
    top_y = steps * rise
    zt = z0 - steps * run
    plat = (0.0, top_y, zt - 9.0)

    def clear(x, z):
        pad = 1 - A.smooth(6.0, 9.5, math.hypot(x, z - 3.5))
        stairs = (1 - A.smooth(6.0, 9.0, abs(x))) * (1 - A.smooth(zt - 22.0, zt - 26.0, z)) * A.smooth(4.0, 0.0, z)
        return max(pad, stairs)
    A.model(s, floor, 'Cloud floor', A.cloud_floor(V, 85.0, clear), (0, 0, 0), (0, 0, 0), 1.0, cloud_mat, shadows=False)
    textured(s.box('Kit dais', floor, (0, -0.16, 3.5), (12.0, 0.3, 12.0), (1, 1, 1), rough=0.12, metallic=0.25, shape='Cylinder'), V, 'Marble', (3, 3))
    A.model(s, floor, 'Kit dais, its gold', A.torus(V, 'DaisRing', 1.0, 0.012, 'gold', 48, 6, 'y'), (0, -0.02, 3.5), (0, 0, 0), 6.0,
            A.mat(V, 'Palette', (1, 1, 1), glow=(1, 1, 1), power=1.2, metallic=0.8, rough=0.3), shadows=False)
    marble = A.mat(V, 'Palette', (1, 1, 1), glow=(1.0, 0.97, 0.92), power=0.28, rough=0.3, metallic=0.1)
    A.model(s, floor, 'Stairs and platform', A.heaven_stairs(V, steps, rise, run, z0), (0, 0, 0), (0, 0, 0), 1.0, marble)
    A.model(s, floor, 'The gates', A.gate(V), (0, top_y, zt - 0.6), (0, 0, 0), 1.0, A.mat(V, 'Palette', (1, 1, 1), glow=(1, 1, 1), power=0.6, metallic=0.7, rough=0.3))
    col = A.column(V)
    for side in (-1, 1):
        for k in range(6):
            z = z0 + 3.0 - k * 4.2
            # 8.2 m to the top of the capital: the director's orbit flies round the band at 10 m and
            # crosses this line (at 1.5 times the size it went through a capital).
            A.model(s, floor, 'Column', col, (side * 8.6, -1.4, z), (0, 0, 0), 1.2, marble)
            A.model(s, floor, 'Column cloud', clouds_m[k % 4], (side * 8.6, -1.6, z), (0, k * 60, 0), (2.6, 1.6, 2.6), cloud_mat, shadows=False)
    for k in range(12):
        a = math.radians(200 + 140 * k / 11)
        if abs(math.cos(a)) < 0.2:
            continue        # the gap the way home shows through
        A.model(s, floor, 'Platform column', col, (plat[0] + 11.6 * math.cos(a), top_y, plat[2] + 11.6 * math.sin(a)), (0, 0, 0), 1.35, marble)
    A.model(s, floor, 'Entablature', A.torus(V, 'Entablature', 1.0, 0.035, 'gold', 48, 6, 'y'), (plat[0], top_y + 11.1, plat[2]), (0, 0, 0), 11.6,
            A.mat(V, 'Palette', (1, 1, 1), glow=(1, 1, 1), power=0.9, metallic=0.8, rough=0.3), shadows=False)
    for i in range(34):
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(13, 70)
        x, z = math.sin(a) * r, math.cos(a) * r - 4
        if abs(x) < 10 and zt - 24 < z < 2:
            continue
        size = rng.uniform(2.5, 7) * (1 + r / 50)
        A.model(s, floor, 'Cloud bank', clouds_m[i % 4], (x, -1.2 - rng.uniform(0, 1.2), z), (0, rng.uniform(0, 360), 0), (size, size * rng.uniform(0.45, 0.9), size),
                cloud_gold if i % 5 == 0 else cloud_mat, shadows=False)
    A.particles(s, floor, 'Mist on the floor', (0, 0.2, -4), Shape='Box', BoxSize=[60, 0.5, 70], Lifetime=[8.0, 14.0], Speed=[0.05, 0.4], Size=[2.5, 5.5], EndSize=1.5,
                StartColor=[1.0, 1.0, 1.0], StartColor2=[0.92, 0.95, 1.0], EndColor=[1.0, 1.0, 1.0], StartAlpha=0.2, EndAlpha=0.0, Gravity=0.0, Drag=0.1,
                NoiseStrength=0.3, NoiseFrequency=0.15, Blend='Alpha', EmissionRate=12, MaxParticles=170, Texture=A.tex(V, 'Puff'), FadeIn=0.3, AngularVelocity=[-5, 5])
    A.particles(s, floor, 'Motes', (0, 5, -6), Shape='Box', BoxSize=[50, 10, 60], Lifetime=[5.0, 9.0], Speed=[0.05, 0.3], Size=[0.025, 0.06],
                StartColor=[1.0, 0.9, 0.6], StartColor2=[1.0, 1.0, 0.9], EndColor=[1.0, 0.85, 0.5], Intensity=3.0, Gravity=-0.01, Drag=0.2, NoiseStrength=0.4,
                Blend='Additive', EmissionRate=40, MaxParticles=320, FadeIn=0.2)
    # The way they came, behind the band: gold arches standing in the cloud like the far one, out
    # to where the wide shots pull back to.
    arch_gold = A.mat(V, 'Palette', (1, 1, 1), glow=(1, 1, 1), power=1.2, metallic=0.7, rough=0.3)
    for k in range(6):
        z = 24.0 + 10.0 * k
        A.model(s, floor, 'Way arch', A.torus(V, 'WayArch', 1.0, 0.04), (0, -0.6, z), (0, 0, 0), 7.0 + 0.5 * k, arch_gold, shadows=False)
        for side in (-1, 1):
            A.model(s, floor, 'Way cloud', clouds_m[(k + side) % 4], (side * (7.4 + 0.5 * k), -1.3, z), (0, k * 70, 0), (3.4, 1.7, 3.4), cloud_mat, shadows=False)
    # Round temples out on the cloud to either side, each with its own light.
    temple_gold = A.mat(V, 'Palette', (1, 1, 1), glow=(1, 1, 1), power=0.9, metallic=0.8, rough=0.3)
    for i, (x, z, sc) in enumerate(((-30, -14, 1.0), (30, -14, 1.0), (-52, 6, 1.25), (52, 6, 1.25), (-38, 34, 1.1), (38, 34, 1.1), (-66, -36, 1.4), (66, -36, 1.4))):
        base = 1.2 + 0.8 * (i // 2 % 2)
        textured(s.box('Temple floor', floor, (x, base - 0.25, z), (11.0 * sc, 0.5, 11.0 * sc), (1, 1, 1), rough=0.12, metallic=0.25, shape='Cylinder'), V, 'Marble', (3, 3))
        for k in range(8):
            a = 2 * math.pi * (k + 0.5) / 8
            A.model(s, floor, 'Temple column', col, (x + 4.6 * sc * math.cos(a), base, z + 4.6 * sc * math.sin(a)), (0, 0, 0), sc, marble)
        A.model(s, floor, 'Temple ring', A.torus(V, 'Entablature', 1.0, 0.035, 'gold', 48, 6, 'y'), (x, base + 8.2 * sc, z), (0, 0, 0), 4.9 * sc, temple_gold, shadows=False)
        A.model(s, floor, 'Temple halo', A.torus(V, 'Halo', 1.0, 0.07), (x, base + 11.5 * sc, z), (90, 0, 0), 2.6 * sc, A.mat(V, 'Palette', (1, 1, 1), glow=(1, 1, 1), power=2.5), shadows=False)
        A.glow_card(s, floor, V, 'Temple light', (x, base + 4.5 * sc, z), 7.0 * sc, (1.0, 0.9, 0.65), 0.5, look_rotation((x, 0, z), (0, 0, 40)))
        A.model(s, floor, 'Temple cloud', clouds_m[i % 4], (x, base - 2.6, z), (0, i * 50, 0), (9.0 * sc, 2.6, 9.0 * sc), cloud_mat, shadows=False)
    # Cumulus piled high at the edges of the floor, and temples adrift over them, to close the sides in.
    for i in range(14):
        side = -1 if i % 2 else 1
        a = math.radians(rng.uniform(28, 150))
        r = rng.uniform(58, 80)
        x, z = side * math.sin(a) * r, -8 + math.cos(a) * r
        sc = rng.uniform(11, 19)
        A.model(s, floor, 'Cloud tower, near', clouds_m[i % 4], (x, -3.0, z), (0, rng.uniform(0, 360), 0), (sc, sc * rng.uniform(1.3, 2.4), sc),
                cloud_gold if i % 4 == 0 else cloud_mat, shadows=False)
    for i, (x, y, z, sc) in enumerate(((-44, 26, -24, 2.6), (47, 31, -18, 2.9), (-58, 44, 2, 3.4), (60, 40, 10, 3.2), (-36, 52, -40, 2.4), (38, 56, -44, 2.6),
                                       (-50, 30, 40, 3.0), (48, 36, 46, 3.2), (-24, 62, 30, 2.2), (26, 66, 22, 2.4))):
        drift = P.looping(s, floor, f'Adrift {i}', P.clip(V, f'IslandDrift{i % 3}', 420 + 90 * (i % 3), [P.track('Position', [(0, (0, 0, 0)), (210 + 45 * (i % 3), (0, 1.2, 0)), (420 + 90 * (i % 3), (0, 0, 0))], 'SmoothStep')]))
        A.model(s, drift, 'Temple adrift', A.island(V, 1 + i % 3), (x, y, z), (0, rng.uniform(0, 360), 0), sc,
                A.mat(V, 'Palette', (1, 1, 1), glow=(0.95, 0.93, 1.0), power=0.7), shadows=False)
    # Light coming down through the sky onto the floor.
    for i, (x, z, w) in enumerate(((-34, -30, 16), (36, -24, 18), (-14, -62, 14), (16, -58, 15), (-52, 14, 20), (54, 20, 20), (-20, 44, 16), (22, 50, 17))):
        A.shaft(s, floor, V, f'Sunbeam {i}', (x * 0.35, 118, z * 0.35 - 30), (x, -2, z), w, (1.0, 0.9, 0.68), 0.16)

    # God: on the platform until the final chorus, then down the stairs to the band's level.
    god_robe = P.figure(V, 'God', 'Rigged', '01_C', P.ROBED, 'God')
    god_at = (0.0, top_y + 0.9, zt - 13.0)
    # He does not tread the steps, he floats down over them: hover above the line through the
    # dais's edges and then the stairs' nosings (a straight line from the platform to the floor
    # runs a riser deep inside every step). The robe is a metre through, so its back hangs over
    # the step behind: hover clears that.
    hover = 0.35
    walk = [(0, 0, 0), (0, hover, 2.8), (0, hover - 0.9, 5.5), (0, hover - 0.9, 13.0 + run)]
    for i in range(1, steps):
        walk.append((0, hover - 0.9 - i * rise + (0.12 if i % 2 else 0), 13.0 + run + i * run))
    walk.append((0, -top_y - 0.9, -4.5 - god_at[2]))
    descend = P.path_clip(V, 'GodDescends', walk, 11.0)
    god = P.play(s, floor, 'God descends', 'god_descends', descend, god_at)
    P.place(s, god, 'God', god_robe, (0, 0, 0), 0, 2.0)
    s.box('Robe', god, (0, 0.9, 0), (1.3, 1.8, 1.0), (1, 1, 1), emissive=(0.9, 0.9, 0.85), emissive_intensity=0.5, shape='Cylinder', shadows=False)
    A.model(s, god, 'Halo', A.torus(V, 'Halo', 1.0, 0.07), (0, 4.1, -0.3), (0, 0, 0), 0.75, A.mat(V, 'Palette', (1, 1, 1), glow=(1, 1, 1), power=4.0), shadows=False)
    burst_spin = P.clip(V, 'SunburstSpin', 1800, [P.track('Rotation', [(0, (0, 0, 0)), (600, (0, 0, 120)), (1200, (0, 0, 240)), (1800, (0, 0, 359.9))])])
    A.model(s, P.looping(s, god, 'Glory', burst_spin, (0, 3.6, -0.9)), 'Sunburst', A.sunburst(V), (0, 0, 0), (0, 0, 0), 7.5,
            A.mat(V, 'Palette', (0, 0, 0), glow=(1.0, 0.86, 0.5), power=0.8, additive=True, both=True), shadows=False)
    A.glow_card(s, god, V, 'Radiance', (0, 3.2, -1.0), 7.0, (1.0, 0.92, 0.7), 0.6)
    s.light('God light', god, (0, 6, 3), 'Point', (1, 0.95, 0.8), 260.0, 18)
    # The arch: the central angel, there from the touchdown as plain gold rings, its eyes opening
    # with the choir and turning to the drummer as the song resolves.
    drummer_head = (DRUMMER[0], 1.3, DRUMMER[1])
    arch_at = (0, top_y + 17, zt - 30)
    angel(s, floor, V, arch_at, 3.2, 'choir', 'Arch angel', 'angels_turn', drummer_head, fade=0.0)

    # The choir: angels in an arc round and above the platform, and rank on rank behind them out
    # of sight; two banks of wings in front part to show the crash site. It is there all at once:
    # the choir shot cuts to it (no fade).
    choir = P.between(s, root, 'The choir', 'choir', None, 0.0, (0, top_y + 10, zt - 20))
    for i, (x, y, z, sc) in enumerate(((-30, 22, -52, 2.2), (30, 22, -52, 2.2), (-50, 30, -40, 1.9), (50, 30, -40, 1.9), (-19, 38, -62, 1.7), (19, 38, -62, 1.7), (0, 47, -68, 2.0))):
        angel(s, choir, V, (x, y, z), sc, None, f'Angel {i}', 'angels_turn', drummer_head)
    far_m = A.angel_far(V)
    far_mat = A.mat(V, 'Palette', (1, 1, 1), glow=(1, 1, 1), power=1.1, both=True)
    bob = [P.clip(V, f'AngelBob{i}', 180 + 40 * i, [P.track('Position', [(0, (0, 0, 0)), (90 + 20 * i, (0, 1.5, 0)), (180 + 40 * i, (0, 0, 0))], 'SmoothStep')]) for i in range(3)]
    ranks = [P.looping(s, choir, f'Rank {i}', bob[i]) for i in range(3)]
    for i in range(66):
        ring = i % 6
        a = math.radians(-78 + 156 * ((i // 6) + 0.5 * (ring % 2)) / 11)
        r = 62 + 8 * ring
        y = 20 + 9 * ring + rng.uniform(-3, 3)
        at = (math.sin(a) * r, y, zt - 4 - math.cos(a) * r * 0.72)
        sc = 3.0 + 0.5 * ring
        A.model(s, ranks[i % 3], 'Angel of the choir', far_m, at, look_rotation(at, drummer_head), sc, far_mat, shadows=False)
    # Higher and nearer, more of them over the platform and out to either side, and two flocks
    # wheeling slowly round it all.
    for i in range(44):
        tier = i % 4
        a = math.radians(-112 + 224 * ((i // 4) + 0.5 * (tier % 2)) / 10.5)
        r = 40 + 7 * tier + rng.uniform(-3, 3)
        at = (math.sin(a) * r, 44 + 11 * tier + rng.uniform(-4, 4), zt - 8 - math.cos(a) * r * 0.8)
        A.model(s, ranks[i % 3], 'Angel of the choir', far_m, at, look_rotation(at, drummer_head), 1.5 + 0.3 * tier, far_mat, shadows=False)
    wheel_at = (0, 0, zt - 10)
    for k, (r, y, count, frames, sc) in enumerate(((34, 58, 9, 5400, 1.3), (56, 78, 13, 7800, 1.7))):
        turn_y = 359.9 if k == 0 else -359.9
        circling = P.clip(V, f'FlockWheel{k}', frames, [P.track('Rotation', [(0, (0, 0, 0)), (frames // 3, (0, turn_y / 3, 0)), (2 * frames // 3, (0, 2 * turn_y / 3, 0)), (frames, (0, turn_y, 0))])])
        flock = P.looping(s, choir, f'Flock {k}', circling, wheel_at)
        for i in range(count):
            a = 2 * math.pi * i / count
            at = (math.sin(a) * r, y + 5 * math.sin(3 * a), math.cos(a) * r)
            A.model(s, flock, 'Angel on the wing', far_m, at, look_rotation(at, (0, y - 30, 0)), sc, far_mat, shadows=False)
    # Behind and over all of them, one vast enough to be taken for the sky: the wheels and wings
    # of it loom through the haze, its glory behind it.
    great_at = (0, 70, zt - 62)
    angel(s, choir, V, great_at, 8.0, None, 'The great angel', 'angels_turn', drummer_head, bright=2.2)
    A.model(s, P.looping(s, choir, 'Great glory', burst_spin, (great_at[0], great_at[1], great_at[2] - 4)), 'Sunburst', A.sunburst(V), (0, 0, 0), (0, 0, 0), 62.0,
            A.mat(V, 'Palette', (0, 0, 0), glow=(1.0, 0.86, 0.5), power=0.55, additive=True, both=True), shadows=False)
    A.glow_card(s, choir, V, 'Great radiance', (great_at[0], great_at[1], great_at[2] - 3), 70.0, (1.0, 0.92, 0.7), 0.45)
    # Two banks of wings close in front of the platform's back; on angels_part they fold aside.
    feather = A.mat(V, 'Palette', (1, 1, 1), glow=(1, 1, 1), power=0.85, both=True)
    for side in (-1, 1):
        fold = P.clip(V, f'WingsPart{"L" if side < 0 else "R"}', 90, [P.track('Position', [(0, (0, 0, 0)), (90, (side * 10.0, 0.5, 1.5))], 'SmoothStep'),
                                                                   P.track('Rotation', [(0, (0, 0, 0)), (90, (0, side * 34, -side * 14))], 'SmoothStep')])
        bank = P.play(s, choir, 'Wings ' + ('left' if side < 0 else 'right'), 'angels_part', fold, (side * 0.4, top_y + 2.5, zt - 21))
        for i in range(4):
            A.model(s, bank, 'Wing', A.wing(V), (0, i * 2.6, -0.2 * i), (0, 0 if side > 0 else 180, side * (24 - 9 * i)), 11.0 - i * 0.8, feather, shadows=False)
    opened = P.between(s, choir, 'The way home', 'angels_part', None, 1.5)
    window = (0, top_y + 7, zt - 23)
    # Through the opening: the night on the shoulder, the fire and the red and blue lights.
    s.box('The way home', opened, window, (11, 9, 0.2), (0.01, 0.015, 0.04), emissive=(0.02, 0.035, 0.12), emissive_intensity=1.0, shadows=False, shape='Sphere')
    A.model(s, opened, 'The way home, its rim', A.torus(V, 'PlainRing', 1.0, 0.11), (window[0], window[1], window[2] + 0.3), (0, 0, 0), (5.7, 4.7, 4.0),
            A.mat(V, 'Palette', (1, 1, 1), glow=(1, 1, 1), power=2.0), shadows=False)
    s.box('The road', opened, (window[0], window[1] - 2.6, window[2] + 0.2), (7.5, 0.9, 0.05), (0.05, 0.05, 0.06), shadows=False)
    for i, (c, x, size) in enumerate((((1, 0.45, 0.08), 1.6, 1.1), ((1, 0.08, 0.05), -1.8, 0.4), ((0.1, 0.25, 1), -1.1, 0.4), ((1, 0.9, 0.7), 2.9, 0.22))):
        s.box('Far light', opened, (window[0] + x, window[1] - 2.0, window[2] + 0.4), (size, size, 0.2), c, emissive=c, emissive_intensity=9.0, shape='Sphere', shadows=False)
    s.light('Choir light', choir, (0, top_y + 30, zt - 10), 'Point', (1, 0.9, 0.7), 5000.0, 90)
    turn = P.between(s, root, 'Angels gaze', 'angels_turn', None, 2.0, arch_at)
    gaze_from = (0, top_y + 15, zt - 26)
    s.light('Gaze', turn, gaze_from, 'Spot', (1, 0.95, 0.75), 9000.0, 90, rot=look_rotation(gaze_from, (0, 1.2, 5.2)), inner=5, outer=12)

    # Earth, far off in the same scene (beyond the sky): the rescue, a place for each cut to it
    # (story_afterlife_rescue), with its own shots.
    RES.build(s, root, marks, V, sys.modules[__name__])

    # A few more places to shoot the show from.
    s.camera_spot('Camera behind the band', marks, (5.2, 2.6, 10.5), (0, top_y - 2, zt - 6), 'Custom', 44, 'behind')
    s.camera_spot('Camera high', marks, (-14, 16, 8), (0, 3, -8), 'Custom', 50, 'high')
    # From the head of the stairs down the colonnade, the dais on the left of the picture (aimed
    # straight at it, the band sat small under the middle of the note highway).
    s.camera_spot('Camera stair head', marks, (4.0, top_y + 2.4, zt + 2.0), (8.5, 1.0, 3.5), 'Custom', 34, 'stairhead')

    # Story shots.
    face = (DRUMMER[0], 1.32, DRUMMER[1] - 0.1)
    # While they float (Band's Floating pose) everyone hangs about 0.6 m up, swaying a quarter of a metre.
    afloat = (face[0], face[1] + 0.6, face[2])
    afloat = (afloat[0], afloat[1] - 0.2, afloat[2])       # the drummer sits: the face is a little lower
    shot(s, marks, 'ascent', (afloat[0] + 0.9, afloat[1], afloat[2] - 0.95), afloat, 34, 14, focus=True,
         end=((afloat[0] + 1.25, afloat[1] + 0.05, afloat[2] - 0.7), afloat, 38))
    other = (BASS[0], 1.62 + 0.6, BASS[1])
    # Past the bass player's shoulder to the drummer: one looks down for the other, and the focus goes with the look.
    shot(s, marks, 'eyes_meet', (other[0] + 1.3, other[1] + 0.1, other[2] - 1.5), other, 38, 8, focus=True,
         end=((other[0] + 1.5, other[1] + 0.15, other[2] - 1.9), afloat, 34))
    shot(s, marks, 'horizon', (-3.0, 2.2, 9.5), (0.5, 1.2, 3.0), 40, 12,
         via=[((-7.0, 3.5, 4.0), (2, -6, -40), 52)], end=((-9.5, 5.0, -4.0), (30, -30, -200), 64))
    # The highway comes back for the touchdown, so from here on the shots under it turn their
    # subject out to one side of it (lead). The touchdown pulls back from the face past the kit
    # to the dais from the side: the band on the right, the stairs going up to the gates on the left.
    shot(s, marks, 'touchdown', (face[0] + 0.7, face[1] + 0.1, face[2] - 0.5), face, 40, 9, lead='r',
         via=[((2.6, 0.5, 0.8), (0, 0.4, 4.0), 50), ((5.5, 2.0, -5.0), (0, 2.0, 3), 54)], end=((8.0, 2.4, 6.8), (0, 1.4, 2.8), 56))
    # The reveal is a cut: the choir is whole in the first frame, from low behind the band, and
    # the camera only rises and widens from there.
    shot(s, marks, 'choir', (1.4, 2.6, 13.5), (0, top_y + 22, zt - 34), 66, 16, lead='l',
         via=[((0.6, 8.0, 25.0), (0, top_y + 24, zt - 36), 74)], end=((0, 22.0, 44.0), (0, top_y + 26, zt - 40), 84))
    shot(s, marks, 'heaven_wide', (0, 12, 36), (0, 20, -50), 60, 12, lead='r', via=[((10, 20, 52), (0, 24, -50), 66)], end=((0, 32, 74), (0, 28, -50), 72))
    shot(s, marks, 'angels_turn', (3.5, 6, -9), arch_at, 40, 7, end=((2.0, 3.0, -1.0), (0, top_y + 14, zt - 28), 52))
    shot(s, marks, 'sticks_close', (2.5, 5, -3), (0, 1.2, 4.6), 44, 20, focus=True, via=[((1.2, 1.9, 2.6), (0, 1.0, 4.4), 36)],
         end=((0.45, 1.05, DRUMMER[1] - 1.9), (0.0, 0.85, DRUMMER[1] - 1.3), 34))
    shot(s, marks, 'drum_open', (0.9, 1.4, DRUMMER[1] - 2.0), (0, 1.1, DRUMMER[1] - 0.6), 36, 7, focus=True, lead='r', end=((-1.3, 1.6, DRUMMER[1] - 2.4), (0, 1.25, DRUMMER[1] - 0.3), 40))
    # God's descent, whole (it takes 11 s): each view aimed at where he is then (the waypoint at
    # its middle, half way down the stairs), so the lead keeps him on the left; held to the angels
    # parting, past the chart's quick cuts in between.
    shot(s, marks, 'god_descends', (5.0, top_y + 1.2, zt + 3.5), (0, top_y + 3.2, zt - 13), 40, 12, lead='l', via=[((6.5, top_y * 0.6, z0 - 4), (0, 7.2, zt + 10.2), 46)],
         end=((5.5, 1.6, 0.5), (0, 2.6, -4.5), 44))
    shot(s, marks, 'angels_part', (1.2, 1.7, 7.4), (0, 4, -4), 46, 9.2, lead='l', via=[((0.5, 3.0, 2.0), window, 40)], end=((0, top_y + 5.5, zt - 9), window, 30))
    write(s, V, 'Heaven')


def prune(venue):
    """Remove what earlier runs generated into the venue that its scene no longer uses: models,
    material libraries, clips and textures (with their .meta and cooked twins)."""
    import re
    folder = os.path.join(repo_root(), 'Assets', 'Venues', venue)
    prefix = f'Assets/Venues/{venue}/'
    scene = open(os.path.join(folder, venue + '.lvl'), encoding='utf-8').read()
    keep = {m[len(prefix):] for m in re.findall(re.escape(prefix) + r'[^"]+', scene)}
    for rel in list(keep):
        if rel.endswith('.obj'):
            base = os.path.dirname(rel)
            for line in open(os.path.join(folder, rel), encoding='utf-8'):
                if line.startswith('mtllib '):
                    mtl = base + '/' + line.split(None, 1)[1].strip()
                    keep.add(mtl)
                    for entry in open(os.path.join(folder, mtl), encoding='utf-8'):
                        if entry.startswith('map_Kd ') and not entry.split(None, 1)[1].startswith('../../../../'):
                            keep.add(os.path.normpath(os.path.join(base, entry.split(None, 1)[1].strip())).replace('\\', '/'))
                    break
    removed = 0
    for sub_ in ('Models/Set', 'Models/People', 'Motion', 'Textures'):
        base = os.path.join(folder, *sub_.split('/'))
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            if not name.endswith(('.obj', '.mtl', '.sequence', '.png')) or f'{sub_}/{name}' in keep:
                continue
            for extra in ('', '.meta', '.assbin', '.dds'):
                if os.path.exists(os.path.join(base, name + extra)):
                    os.remove(os.path.join(base, name + extra))
            removed += 1
    if removed:
        print(f'Assets/Venues/{venue}: {removed} unused generated files removed')


def main():
    highway()
    hell()
    heaven()
    for venue in ('StoryHighway', 'StoryHell', 'StoryHeaven'):
        prune(venue)
    # AFTERLIFE_SHOTS=<file>: the story shots as eye / target / field of view, for previews
    # (--venue-eye "x,y,z,tx,ty,tz,fov").
    out = os.environ.get('AFTERLIFE_SHOTS')
    if out:
        with open(out, 'w', newline='\n') as f:
            json.dump(SHOTS, f, indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main())
