#!/usr/bin/env python3
"""Builds Assets/Venues/StoryEventHorizon/: set 13, The Drummer Hall of Fame at the Event Horizon.

    python3 Tools/Venues/make_story_event_horizon.py

An orbital Hall of Fame rotunda beside a black hole. Five brass drive rings hang behind and over the
band, jumbled like a gyroscope; across the five songs each one swings into line until all five
stand concentric around the black disc seen through the great window, the Wide shot looking right
down their axis. Story flags (s13-event-horizon):

  first_ring_turning   the outer ring swings into line; amber light runs round its face
  second_ring_aligned  the second ring snaps in; a row of stars appears twice round the black disc
  third_ring_locked    the third ring locks; brass clamps with cyan lamps bridge rings 2-4;
                       the conductor steps back from the desk
  fourth_ring_charged  the fourth ring glows white; the black disc swells to fill the window; the
                       hall's house lights go down; the conductor turns to the drummer
  fifth_ring_armed     the innermost ring locks above the kit; charge nodes light on every ring and
                       a beam joins the rings' centre to the hole

Deterministic: rerun = same bytes. Helpers: story_event_horizon_{mesh,props,textures}.py.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from venuegen import Scene, look_rotation, repo_root, write_venue_json  # noqa: E402
import story_event_horizon_mesh as em  # noqa: E402
import story_event_horizon_props as pr  # noqa: E402
import story_event_horizon_textures as tx  # noqa: E402

VID = 'StoryEventHorizon'
FOLDER = os.path.join(repo_root(), 'Assets', 'Venues', VID)
MODELS = os.path.join(FOLDER, 'Models')
TEXTURES = os.path.join(FOLDER, 'Textures')
LOCAL = f'Assets/Venues/{VID}/Models/'
SET = 's13-event-horizon'

EYE = (0.0, 4.5, -20.0)          # the Wide shot: it looks straight down the rings' axis
HOLE = (0.0, 48.0, 125.0)        # the black hole, far outside the window
RING_C = (0.0, 13.8, 11.0)       # the rings' common centre (on the line EYE -> HOLE)
TILTS = [(68, 0, 0), (0, 62, 0), (38, -34, 18), (-52, 22, 0), (24, 70, -12)]

AMBER = (1.0, 0.55, 0.18)
GOLD = (1.0, 0.78, 0.38)
WHITE = (1.0, 0.97, 0.92)
CYAN = (0.35, 0.85, 1.0)
WARM = (1.0, 0.72, 0.42)
BRASS = (0.85, 0.62, 0.28)


def glow(scene, name, parent, obj, color, power, pos=(0, 0, 0), rot=(0, 0, 0), scale=1.0):
    """A Model whose single part is overridden with an emissive material."""
    e = scene.entity(name, parent, pos, rot, (scale,) * 3 if isinstance(scale, (int, float)) else scale)
    mat = {'Type': 'StandardMaterial', 'DiffuseColor': list(color),
           'Roughness': 0.9, 'EmissiveColor': list(color), 'EmissiveIntensity': power, 'FaceMode': 2}
    e.add({'Type': 'Model', 'ModelPath': LOCAL + obj, 'Compact': True,
           'Parts': {em.part(obj, obj[:-4]): {'CastShadows': False, 'Material': mat}}})
    return e


def model(scene, name, parent, obj, pos=(0, 0, 0), rot=(0, 0, 0), scale=1.0):
    e = scene.entity(name, parent, pos, rot, (scale,) * 3)
    e.add({'Type': 'Model', 'ModelPath': LOCAL + obj})
    return e


def meshes():
    """Write every OBJ/MTL/texture; returns nothing (files are referenced by name)."""
    os.makedirs(MODELS, exist_ok=True)
    em.palette_png(os.path.join(MODELS, 'EH_Palette.png'))
    em.write_mtl(MODELS, 'EH', 'EH_Palette.png')
    tx.make_all(TEXTURES)
    for name in ('Plaque_1', 'Plaque_2', 'Plaque_3', 'Plaque_4', 'Plaque_Blank', 'Frieze', 'FriezeBack'):
        em.write_mtl(MODELS, name, f'../Textures/{name}.png')
    out = [pr.hall(), pr.pylons(RING_C), pr.ring_clamps(), pr.clamp_lamps(), pr.music_stand(),
           pr.rehearsal_lamp(), pr.lamp_shade(), pr.podium(), pr.hat_loonie(),
           pr.pickups_and_leads(pr.STAGE_H + pr.RISER_H, RING_C)]
    out += [pr.conductor(p) for p in ('up', 'down', 'point')]
    for k in range(5):
        out += [pr.ring(k), pr.ring_glow(k), pr.ring_nodes(k)]
    out += pr.stars(tuple(h - e for h, e in zip(HOLE, EYE)))
    out += list(pr.hole_meshes().values())
    for m in out:
        m.write(MODELS, 'EH')
    for i in range(1, 5):
        pr.plaque(f'Plaque{i}', f'Plaque_{i}').write(MODELS, f'Plaque_{i}')
    pr.plaque('PlaqueBlank', 'Plaque_Blank').write(MODELS, 'Plaque_Blank')
    pr.plaque('Frieze', 'Frieze', 16.0, 2.0, 0.15).write(MODELS, 'Frieze')
    pr.plaque('FriezeBack', 'FriezeBack', 16.0, 2.0, 0.15).write(MODELS, 'FriezeBack')


def black_hole(s, parent, scale):
    """The hole's parts in a group at HOLE, its local -z toward the Wide eye."""
    g = s.entity('Black hole', parent, HOLE, look_rotation(EYE, HOLE), (scale,) * 3)
    shadow = s.box('Shadow', g, (0, 0, 0), (30.2, 30.2, 30.2), (0, 0, 0), rough=1.0, shadows=False, shape='Sphere')
    shadow.components[-1]['Material']['EmissiveColor'] = [0, 0, 0]
    glow(s, 'Photon ring', g, 'PhotonRing.obj', (1.0, 0.92, 0.78), 9.0)
    glow(s, 'Lensed disc, inner', g, 'LensInner.obj', (1.0, 0.72, 0.36), 3.0)
    glow(s, 'Lensed disc, middle', g, 'LensMid.obj', (1.0, 0.45, 0.14), 2.2)
    glow(s, 'Lensed disc, outer', g, 'LensOuter.obj', (0.75, 0.2, 0.06), 0.9)
    glow(s, 'Accretion disc, hot', g, 'DiscHot.obj', (1.0, 0.86, 0.6), 3.5)
    glow(s, 'Accretion disc, warm', g, 'DiscWarm.obj', (1.0, 0.5, 0.16), 1.7)
    glow(s, 'Accretion disc, cool', g, 'DiscCool.obj', (0.7, 0.18, 0.06), 1.0)
    bent = s.story('Bent starlight', g, 'second_ring_aligned', True, 1.5)
    glow(s, 'A row of stars, twice', bent, 'LensedStars.obj', (0.85, 0.93, 1.0), 6.0)
    return g


def build():
    meshes()
    s = Scene(seed='story-event-horizon-v1')
    root = s.group('The Drummer Hall of Fame at the Event Horizon')
    space = s.group('Space outside', root)
    hall = s.group('Rotunda', root)
    rings = s.group('Five brass rings', root)
    dress = s.group('Stage dressing', root)
    house = s.group('House', root)
    lamps = s.group('Show lights', root)
    marks = s.group('Venue markers', root)

    # ---- space: stars and the hole ---------------------------------------------------------
    for obj, col, p in (('StarsWhite.obj', (0.95, 0.97, 1.0), 5.0), ('StarsBlue.obj', (0.55, 0.72, 1.0), 6.0),
                        ('StarsWarm.obj', (1.0, 0.78, 0.55), 5.0), ('StarsDust.obj', (0.7, 0.72, 0.95), 1.6)):
        glow(s, obj[:-4], space, obj, col, p)
    opens = s.story('Hole as it opens', space, 'fourth_ring_charged', False, 2.5, HOLE)
    black_hole(s, opens, 1.35)
    fills = s.story('Hole fills the window', space, 'fourth_ring_charged', True, 3.0, HOLE)
    black_hole(s, fills, 2.2)

    # ---- the rotunda -----------------------------------------------------------------------
    model(s, 'Hall', hall, 'Hall.obj')
    model(s, 'Ring pylons', hall, 'RingPylons.obj')
    fr = pr.at(0, pr.HALL_R - 0.6, 29.0)
    model(s, 'Frieze over the window', hall, 'Frieze.obj', fr, (0, 180, 0))
    model(s, 'Frieze over the doors', hall, 'FriezeBack.obj', pr.at(180, pr.HALL_R - 0.6, 11.0), (0, 0, 0))
    # Inductee plaques round the gallery, between the columns, facing the room.
    k = 0
    for i in range(24):
        th = -180 + i * 15
        if abs(th) < pr.WINDOW_HALF + 4 or abs(th) > 170:
            continue
        for y in (9.4, 12.2):
            p = pr.at(th, pr.HALL_R - 0.25, y)
            plate = 'PlaqueBlank.obj' if (th, y) == (75, 9.4) else f'Plaque{k % 4 + 1}.obj'
            model(s, f'Inductees {k+1:02}', hall, plate, p, (0, th + 180, 0), 1.0)
            k += 1
    # Big plates either side of the window, high up: the names over the highway.
    for side in (-1, 1):
        for j, y in enumerate((17.0, 24.0)):
            th = side * (pr.WINDOW_HALF - 2)
            p = pr.at(th, pr.HALL_R - 0.9, y)
            model(s, f'Great plate {side:+d}/{j+1}', hall, f'Plaque{(j * 2 + (side > 0)) % 4 + 1}.obj', p,
                  (0, th + 180, 0), 2.0)

    # ---- the rings -------------------------------------------------------------------------
    flags = ['first_ring_turning', 'second_ring_aligned', 'third_ring_locked', 'fourth_ring_charged', 'fifth_ring_armed']
    lit = [(AMBER, 1.5), (GOLD, 1.3), (CYAN, 1.4), (WHITE, 2.4), (GOLD, 1.4)]
    for k in range(5):
        adrift = s.story(f'Ring {k+1} adrift', rings, flags[k], False, 1.2, RING_C)
        model(s, f'Ring {k+1} (tilted)', adrift, f'Ring{k+1}.obj', (0, 0, 0), TILTS[k])
        inline = s.story(f'Ring {k+1} in line', rings, flags[k], True, 1.6, RING_C)
        if k == 3:  # charged: the whole band burns white
            glow(s, 'Ring 4, white hot', inline, 'Ring4.obj', (1.0, 0.95, 0.85), 0.35)
        else:
            model(s, f'Ring {k+1}', inline, f'Ring{k+1}.obj')
        col, power = lit[k]
        glow(s, f'Ring {k+1} light', inline, f'RingGlow{k+1}.obj', col, power)
        s.light(f'Ring {k+1} spill', inline, (0, -pr.RING_R[k] + 1.0, -2.0), 'Point', col,
                120.0 if k == 3 else 45.0, 12.0 if k == 3 else 8.0)
    locked = s.story('Clamps locked', rings, 'third_ring_locked', True, 1.0, RING_C)
    model(s, 'Lock clamps', locked, 'RingClamps.obj')
    glow(s, 'Lock lamps', locked, 'ClampLamps.obj', CYAN, 3.0)
    armed = s.story('Array armed', rings, 'fifth_ring_armed', True, 1.4, RING_C)
    for k in range(5):
        glow(s, f'Charge nodes {k+1}', armed, f'RingNodes{k+1}.obj', (0.75, 0.95, 1.0), 2.0)
    d = tuple(h - c for h, c in zip(HOLE, RING_C))
    length = math.sqrt(sum(x * x for x in d)) - 18.0
    pitch = math.degrees(math.atan2(math.hypot(d[0], d[2]), d[1]))
    mid = tuple(c + x * (length / 2) / (length + 18.0) for c, x in zip(RING_C, d))
    beam = s.box('Pulse beam', armed, mid, (0.22, length, 0.22), (0.8, 0.95, 1.0), rot=(pitch, 0, 0),
                 emissive=(0.7, 0.92, 1.0), emissive_intensity=2.5, shadows=False, shape='Cylinder')
    s.box('Pulse core', armed, RING_C, (0.9, 0.9, 0.9), (1, 1, 1), emissive=(0.85, 0.97, 1.0),
          emissive_intensity=3.0, shadows=False, shape='Sphere')
    s.light('Armed core', armed, (RING_C[0], RING_C[1] - 6.0, RING_C[2] - 3.0), 'Point', CYAN, 70.0, 12.0)

    # ---- stage dressing --------------------------------------------------------------------
    top = pr.STAGE_H + pr.RISER_H
    model(s, 'Kit leads and pickups', dress, 'KitLeads.obj')
    glow(s, 'Drilled loonie on the hat stand', dress, 'HatLoonie.obj', GOLD, 1.5, (-0.95, top + 0.95, 6.55), (0, 20, 0))
    model(s, 'One plain music stand', dress, 'MusicStand.obj', (1.75, top, 6.6), (0, -25, 0))
    model(s, 'Rehearsal lamp', dress, 'RehearsalLamp.obj', (-1.9, top, 8.1), (0, 30, 0))
    glow(s, 'Rehearsal lamp shade', dress, 'LampShade.obj', (1.0, 0.7, 0.36), 5.0, (-1.9, top, 8.1), (0, 30, 0))
    s.light('Rehearsal lamp glow', dress, (-1.75, top + 1.7, 7.75), 'Point', (1.0, 0.66, 0.36), 38.0, 5.5)
    podium_at = (7.2, pr.STAGE_H, 7.0)
    model(s, 'Conductor podium', dress, 'ConductorPodium.obj', podium_at, (0, 73, 0))
    stand_y = pr.STAGE_H + 0.32
    before = s.story('Conductor at the desk', dress, 'third_ring_locked', False, 0.6, (7.2, stand_y, 7.0))
    model(s, 'Conductor, baton up', before, 'Conductor_up.obj', (7.2, stand_y, 7.0), (0, 73, 0))
    back = s.story('Conductor steps back', dress, 'third_ring_locked', True, 0.6, (7.45, stand_y, 7.25))
    back2 = s.story('...until the fourth', back, 'fourth_ring_charged', False, 0.6, (7.45, stand_y, 7.25))
    model(s, 'Conductor, listening', back2, 'Conductor_down.obj', (7.45, stand_y, 7.25), (0, 73, 0))
    turn = s.story('Conductor turns to the drummer', dress, 'fourth_ring_charged', True, 0.6, (7.2, stand_y, 7.0))
    model(s, 'Conductor, cueing the drummer', turn, 'Conductor_point.obj', (7.2, stand_y, 7.0), (0, 94, 0))
    for i, (x, z, yaw) in enumerate(((-6.4, 2.0, 20), (6.0, 2.2, -20))):
        s.prop(f'Wedge {i+1}', dress, 'Assets/Models/Venue/Wedge.obj', (x, pr.STAGE_H, z), yaw + 180)
    s.prop('Bass rig', dress, 'Assets/Models/Venue/GuitarCab.obj', (5.6, pr.STAGE_H, 6.6), 190)
    s.prop('Guitar rig', dress, 'Assets/Models/Venue/GuitarCab.obj', (-5.4, pr.STAGE_H, 6.4), 170)
    s.prop('Bass head', dress, 'Assets/Models/Venue/AmpHead.obj', (5.6, pr.STAGE_H + 0.75, 6.6), 190)
    s.prop('Guitar head', dress, 'Assets/Models/Venue/AmpHead.obj', (-5.4, pr.STAGE_H + 0.75, 6.4), 170)
    s.prop('Drum rug', dress, 'Assets/Models/Venue/DrumRug.obj', (0, top + 0.005, 6.9), 0, 0.9)

    # ---- house lights (go down when the hole fills the window) -----------------------------
    houselit = s.story('House lights', house, 'fourth_ring_charged', False, 3.0, (0, 8, -2))
    for i in range(12):
        th = -180 + i * 30 + 15
        if abs(th) < pr.WINDOW_HALF:
            continue
        p = pr.at(th, pr.HALL_R - 0.9, 6.6)
        s.box(f'Sconce {i+1}', houselit, p, (0.5, 0.7, 0.5), WARM, emissive=WARM, emissive_intensity=4.0,
              shadows=False, shape='Sphere')
        s.light(f'Sconce light {i+1}', houselit, pr.at(th, pr.HALL_R - 2.0, 6.0), 'Point', WARM, 140.0, 11.0)
    s.light('Hall glow', houselit, (0, 22, -6), 'Point', (0.55, 0.6, 0.9), 900.0, 40.0)
    for i, th in enumerate((-135, -90, -45, 0, 45, 90, 135, 180)):
        s.box(f'Oculus lamp {i+1}', house, pr.at(th, pr.OCULUS_R, pr.OCULUS_Y - 0.7), (0.6, 0.3, 0.6),
              (0.7, 0.85, 1.0), emissive=(0.7, 0.85, 1.0), emissive_intensity=3.0, shadows=False)

    # ---- show lights (never story-gated) ---------------------------------------------------
    def spot(n, pos, to, color, power, reach, inner, outer, role='Static', group=0):
        s.light(n, lamps, pos, 'Spot', color, power, reach, rot=look_rotation(pos, to), inner=inner,
                outer=outer, show=role, group=group)
    s.light('Accretion light', lamps, HOLE, 'Directional', (1.0, 0.72, 0.5), 0.9,
            rot=look_rotation(HOLE, (0, 0, 4)), shadows=True, show='Static')
    s.light('Starlight fill', lamps, (0, 30, -10), 'Point', (0.5, 0.6, 1.0), 500.0, 45.0, show='Static')
    for i, x in enumerate((-9, -5, -1.5, 1.5, 5, 9)):
        spot(f'Front wash {i+1}', (x, 13, -7), (x * 0.5, 1.0, 5), (0.75, 0.8, 1.0), 2600, 30, 20, 40, 'Wash', i % 3)
    for i, x in enumerate((-6, -2, 2, 6)):
        spot(f'Back wash {i+1}', (x, 11, 15), (x * 0.6, 0.8, 4), (1.0, 0.7, 0.4), 1600, 22, 22, 42, 'Wash', (i + 1) % 3)
    for i, (n, to) in enumerate((('Drummer', (0, 1.9, 7.6)), ('Vocals', (0, 1.6, 2.6)), ('Guitar', (-4.2, 1.6, 5.0)),
                                 ('Bass', (4.2, 1.6, 5.0)), ('Keys', (-7.0, 1.6, 6.8)))):
        spot(f'Follow spot / {n}', (to[0] * 0.3, 16, -14), to, (1.0, 0.95, 0.88), 4200, 40, 4, 7, 'Spot', i)
    for i in range(8):
        x = -8.4 + i * 2.4
        z = 6 + math.sqrt(max(0, pr.STAGE_R ** 2 - x ** 2)) - 0.6
        spot(f'Rim beam {i+1}', (x, pr.STAGE_H + 0.2, z), (x * 2.2, 30, z + 6), (0.85, 0.6, 1.0) if i % 2 else (1.0, 0.75, 0.35),
             3000, 40, 3, 6, 'Beam', i % 2)
    for i, x in enumerate((-8.2, 8.2)):
        spot(f'Blinder {i+1}', (x, 3.0, 12.0), (x * 0.3, 2.0, -12), WARM, 1800, 30, 25, 50, 'Blinder', i)
    for i, x in enumerate((-12.0, 12.0)):
        s.light(f'Strobe {i+1}', lamps, (x, 9.0, 11.0), 'Point', (0.9, 0.95, 1.0), 1500.0, 30.0, show='Strobe', group=i)
    s.light('Band key', lamps, (0, 7, -2), 'Point', (0.95, 0.88, 0.8), 160.0, 18.0, show='Static')

    # ---- markers ---------------------------------------------------------------------------
    s.info(marks, 'The Drummer Hall of Fame at the Event Horizon', 'Drumsmith', room_back=-28, room_ceiling=46,
           half_width=26, desk_z=-21, ambient=(0.004, 0.005, 0.012), fog_color=(0.012, 0.011, 0.024), haze=0.1)
    s.spot(marks, 'Drummer', (0, top, 7.9))
    s.spot(marks, 'Bass', (4.2, pr.STAGE_H, 5.0), -12)
    s.spot(marks, 'Guitar', (-4.2, pr.STAGE_H, 5.0), 12)
    s.spot(marks, 'Vocals', (0, pr.STAGE_H, 2.6))
    s.spot(marks, 'Keys', (-7.0, pr.STAGE_H, 6.8), 28)
    for name, c, w, dpt, n, kind, y in (
            ('Inductees, front rows', (0, 0, -6.5), 15, 4.0, 60, 'Posed', 0.0),
            ('Gala floor', (0, 0, -14.0), 24, 10.0, 170, 'Mob', 0.0),
            ('Gala floor, sides', (0, 0, -21.5), 18, 4.5, 50, 'Mob', 0.0),
            ('Left gallery, low', (-18.6, 0, -7.5), 1.8, 16, 26, 'Mob', 3.2),
            ('Left gallery, high', (-20.6, 0, -7.5), 1.8, 15, 24, 'Mob', 4.0),
            ('Right gallery, low', (18.6, 0, -7.5), 1.8, 16, 26, 'Mob', 3.2),
            ('Right gallery, high', (20.6, 0, -7.5), 1.8, 15, 24, 'Mob', 4.0)):
        yaw = 0.0
        s.crowd(name, marks, (c[0], y, c[2]), w, dpt, n, 0.5, yaw, kind)
    cams = s.group('Camera positions', marks)
    for tag, kind, eye, aim, fov in (
            ('down-the-rings', 'Wide', EYE, (0, 10.0, 8.0), 60),
            ('gallery-crane', 'Crane', (-15.5, 13.0, -12.0), (0, 7.0, 8.0), 58),
            ('long-lens', 'Desk', (2.5, 3.6, -21.0), (0, 2.2, 6.0), 30),
            ('under-the-rings', 'Custom', (-5.5, 2.3, -5.0), (0, 15.5, 12.0), 64),
            ('stand-and-lamp', 'Custom', (3.4, 2.4, 3.2), (0.2, 1.7, 7.6), 52),
            ('conductor', 'Custom', (2.5, 2.3, 1.6), (7.2, 1.9, 7.2), 50),
            ('sticks', 'Close', (1.5, 2.7, 4.7), (0, 1.9, 7.7), 46),
            ('bass-locks-eyes', 'Custom', (7.5, 2.4, 1.2), (1.0, 2.0, 7.2), 50),
            ('ring-window', 'Crane', (12.0, 9.0, -6.0), (-2.0, 13.0, 14.0), 60)):
        s.camera_spot(tag, cams, eye, aim, kind, fov, tag)
    for i, (eye, aim, fov) in enumerate((
            ((-3.0, 1.7, -24.0), (0, 3.0, 0), 66), ((-2.2, 1.75, -19.0), (0, 4.0, 4), 64),
            ((-1.4, 1.8, -14.0), (0, 8.0, 8), 62), ((-0.8, 1.9, -10.0), (0, 13.0, 11), 60),
            ((0.0, 2.1, -7.6), (0, 2.0, 6), 58))):
        s.camera_spot(f'Arrival {i+1:02}', cams, eye, aim, 'Custom', fov, f'arrival/{i+1:02}')
    return s


def main():
    scene = build()
    scene.write(os.path.join(FOLDER, f'{VID}.lvl'))
    preview = 'Preview.jpg' if os.path.exists(os.path.join(FOLDER, 'Preview.jpg')) else None
    write_venue_json(FOLDER, 'The Drummer Hall of Fame at the Event Horizon', f'{VID}.lvl', preview=preview,
                     ambience='Assets/Sounds/crowd.mp3')
    print(f'{len(scene.entities)} entities in {VID}')


if __name__ == '__main__':
    main()
