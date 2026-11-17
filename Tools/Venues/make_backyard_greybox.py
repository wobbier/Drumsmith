#!/usr/bin/env python3
"""Writes Assets/Venues/Backyard/: a greybox suburban backyard house party at night.

    python3 Tools/Venues/make_backyard_greybox.py

Coloured boxes and existing Assets/Models/Venue props; real metres. Axes: the crowd stands at
z < 0 facing +z, the band faces -z, z = 0 is the front edge of the patio. The house is behind the
band (z 11..20), the lawn and pool in front, fences at x = +-14.2 and z = -30, the street beyond.
Deterministic: rerun = same bytes. The final art replaces the boxes; the markers stay.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
from venuegen import Scene, repo_root, write_venue_json  # noqa: E402

M = "Assets/Models/Venue/"

# Palette (sRGB, dark and night-lit; the lights do the colouring).
LAWN = (0.16, 0.32, 0.15)
DECK = (0.34, 0.26, 0.18)
WOOD = (0.42, 0.29, 0.17)
PALLET = (0.50, 0.38, 0.24)
WALL = (0.72, 0.68, 0.60)
TRIM = (0.85, 0.85, 0.82)
ROOF = (0.20, 0.16, 0.15)
BRICK = (0.45, 0.22, 0.16)
GLASS = (0.06, 0.08, 0.12)
WARM = (1.0, 0.68, 0.30)
FENCE = (0.30, 0.24, 0.18)
CONCRETE = (0.45, 0.45, 0.47)
ASPHALT = (0.08, 0.08, 0.09)
WATER = (0.02, 0.28, 0.40)
TILE = (0.55, 0.78, 0.82)
BLACK = (0.04, 0.04, 0.045)


def build():
    s = Scene(seed=2024)
    rng = random.Random(7)
    root = s.group("Backyard Party")
    house = s.group("House", root)
    patio = s.group("Patio", root)
    pool = s.group("Pool", root)
    lawn = s.group("Lawn", root)
    props = s.group("Props", root)
    lights = s.group("Lights", root)
    marks = s.group("Markers", root)

    # ---- Lawn, fences, street, neighbours ------------------------------------------------
    # The lawn is four slabs with a hole for the pool (x 4.7..12.3, z -9.3..-1.7).
    s.slab("Lawn West", lawn, -14.2, 4.7, -0.3, 0.0, -30, 11, LAWN, rough=1.0)
    s.slab("Lawn East", lawn, 12.3, 14.2, -0.3, 0.0, -30, 11, LAWN, rough=1.0)
    s.slab("Lawn Far", lawn, 4.7, 12.3, -0.3, 0.0, -30, -9.3, LAWN, rough=1.0)
    s.slab("Lawn Near", lawn, 4.7, 12.3, -0.3, 0.0, -1.7, 11, LAWN, rough=1.0)
    fence = s.group("Fences", lawn)
    for side, x in (("West", -14.2), ("East", 14.2)):
        s.slab(f"Fence {side}", fence, x - 0.07, x + 0.07, 0, 1.9, -30, 11, FENCE)
        for i in range(6):
            z = -28 + i * 7.6
            s.slab(f"Fence Post {side} {i}", fence, x - 0.12, x + 0.12, 0, 2.1, z - 0.1, z + 0.1, WOOD)
    s.slab("Fence Back", fence, -14.2, 14.2, 0, 1.9, -30.07, -29.93, FENCE)
    s.slab("Gate", fence, -1.2, 1.2, 0, 2.0, -30.2, -30.0, WOOD)
    street = s.group("Street", lawn)
    s.slab("Street Road", street, -60, 60, -0.35, -0.05, -46, -33, ASPHALT, rough=0.8)
    s.slab("Street Verge", street, -60, 60, -0.3, 0.0, -33, -30, LAWN, rough=1.0)
    s.slab("Kerb", street, -60, 60, -0.3, 0.12, -33.4, -33, CONCRETE)
    s.slab("Street Far Side", street, -60, 60, -0.3, 0.0, -60, -46, LAWN, rough=1.0)
    # Neighbours beyond the side fences, and across the street: boxes with pitched roofs.
    nb = s.group("Neighbours", lawn)
    for i, (x, z0, z1, h, c) in enumerate([(-22, -8, 6, 5.6, (0.55, 0.55, 0.6)),
                                           (-24, -26, -12, 5.0, BRICK),
                                           (22, -6, 8, 6.0, (0.6, 0.58, 0.5)),
                                           (24, -24, -10, 5.4, (0.45, 0.5, 0.58))]):
        wd = 12.0
        s.slab(f"Neighbour {i} Body", nb, x - wd / 2, x + wd / 2, 0, h, z0, z1, c)
        # Ridge along z; roof halves tilt about Z.
        half = wd / 2 / math.cos(math.radians(24))
        for sign in (-1, 1):
            e = s.box(f"Neighbour {i} Roof {'W' if sign < 0 else 'E'}", nb,
                      (x + sign * wd / 4, h + math.tan(math.radians(24)) * wd / 4, (z0 + z1) / 2),
                      (half, 0.25, z1 - z0 + 0.6), ROOF, rot=(0, 0, -sign * 24.0))
        if i % 2 == 0:  # a lit window or two
            face = x + (wd / 2 + 0.02) * (1 if x < 0 else -1)  # the wall facing the yard
            s.box(f"Neighbour {i} Window", nb, (face, 2.6, z0 + 4), (0.05, 1.2, 1.6), WARM,
                  emissive=WARM, emissive_intensity=1.5)
    # Trees: trunk + canopy
    for i, (x, z) in enumerate([(-17, -18), (17, -14), (-18, 10), (17, 12), (-6, -38), (9, -40)]):
        s.box(f"Tree {i} Trunk", nb, (x, 1.6, z), (0.45, 3.2, 0.45), (0.22, 0.14, 0.08))
        s.box(f"Tree {i} Canopy", nb, (x, 5.0, z), (4.2, 3.6, 4.2), (0.07, 0.2, 0.08), shape="Sphere", rough=1.0)

    # ---- House ----------------------------------------------------------------------------
    # Back wall of the stage area is the house's rear facade at z = 11.
    s.slab("House Body", house, -12, 12, 0, 6.2, 11, 20, WALL)
    s.slab("Foundation", house, -12.1, 12.1, 0, 0.5, 10.9, 20.1, CONCRETE)
    s.slab("Floor Band", house, -12.1, 12.1, 2.9, 3.1, 10.9, 20.1, TRIM)
    # Ridge along x: front/back roof halves tilt about X.
    half = 5.0 / math.cos(math.radians(25))
    rise = 6.2 + math.tan(math.radians(25)) * 2.5
    s.box("Roof Front", house, (0, rise, 13.0), (24.8, 0.25, half), ROOF, rot=(-25.0, 0, 0))
    s.box("Roof Back", house, (0, rise, 18.0), (24.8, 0.25, half), ROOF, rot=(25.0, 0, 0))
    s.slab("Chimney", house, 7.5, 8.7, 6.0, 10.0, 15.4, 16.6, BRICK)
    # Sliding door (ground floor) and windows. Warm light in the windows.
    s.slab("Sliding Door Frame", house, 4.9, 8.6, 0.5, 2.7, 10.92, 11.0, TRIM)
    s.slab("Sliding Door Glass", house, 5.05, 8.45, 0.6, 2.6, 10.88, 10.95, (0.10, 0.13, 0.18),
           emissive=(1.0, 0.7, 0.4), emissive_intensity=0.6)
    s.slab("Door Divider", house, 6.7, 6.8, 0.6, 2.6, 10.86, 10.93, TRIM)
    for i, x in enumerate([-10.0, -3.0, 2.5]):
        w = 2.0
        s.slab(f"Ground Window {i} Frame", house, x - w / 2 - 0.1, x + w / 2 + 0.1, 0.9, 2.5, 10.93, 11.0, TRIM)
        s.slab(f"Ground Window {i}", house, x - w / 2, x + w / 2, 1.0, 2.4, 10.88, 10.95, GLASS,
               emissive=WARM if i != 1 else (0.3, 0.4, 0.9), emissive_intensity=0.8)
    for i, x in enumerate([-9.5, -6.0, -2.0, 2.0, 6.0, 9.5]):
        w = 1.6
        s.slab(f"Upper Window {i} Frame", house, x - w / 2 - 0.1, x + w / 2 + 0.1, 3.7, 5.5, 10.93, 11.0, TRIM)
        lit = i in (0, 2, 3, 5)
        s.slab(f"Upper Window {i}", house, x - w / 2, x + w / 2, 3.8, 5.4, 10.88, 10.95, GLASS,
               emissive=WARM if lit else None, emissive_intensity=1.0)
    s.slab("Eave Trim", house, -12.4, 12.4, 6.0, 6.2, 10.4, 11.0, TRIM)
    # Projector sheet on the wall (frame + the screen marker lives under Markers)
    s.slab("Projector Sheet Frame", house, -11.2, -6.8, 3.55, 6.05, 10.93, 11.0, BLACK)
    # Downpipe, porch light box and a back step
    s.slab("Downpipe", house, 11.0, 11.15, 0, 6.1, 10.8, 10.95, (0.5, 0.5, 0.52))
    s.slab("Back Step", house, 4.6, 8.9, 0, 0.25, 9.5, 11.0, CONCRETE)

    # ---- Patio / pool deck ----------------------------------------------------------------
    s.slab("Patio Deck", patio, -8, 8, 0, 0.25, 0, 11, DECK)
    s.slab("Patio Step", patio, -2.5, 2.5, 0, 0.12, -0.7, 0, DECK)
    # Drummer riser on pallets: 0.3 m high platform under the pergola.
    s.slab("Drummer Riser", patio, -2.1, 2.1, 0.25, 0.55, 4.5, 8.1, PALLET)
    for i in range(4):
        s.slab(f"Riser Slat {i}", patio, -2.1, 2.1, 0.55, 0.57, 4.7 + i * 0.95, 5.35 + i * 0.95, WOOD)
    # Pergola: four posts, two beams along x, slats along z, over x +-3.6, z 3.8..8.4.
    pg = s.group("Pergola", patio)
    for x in (-3.5, 3.5):
        for z in (3.9, 8.3):
            s.slab(f"Pergola Post {x:+.1f},{z:.1f}", pg, x - 0.1, x + 0.1, 0.25, 3.3, z - 0.1, z + 0.1, WOOD)
    for z in (3.9, 8.3):
        s.slab(f"Pergola Beam {z:.1f}", pg, -3.9, 3.9, 3.3, 3.55, z - 0.1, z + 0.1, WOOD)
    for i in range(9):
        z = 3.9 + i * 0.55
        s.slab(f"Pergola Slat {i}", pg, -3.7, 3.7, 3.55, 3.62, z - 0.05, z + 0.05, WOOD)

    # ---- Pool -----------------------------------------------------------------------------
    px0, px1, pz0, pz1 = 5.0, 12.0, -9.0, -2.0
    s.slab("Pool Floor", pool, px0, px1, -1.3, -1.2, pz0, pz1, TILE)
    for name, a in (("N", (px0, px1, pz1 - 0.3, pz1)), ("S", (px0, px1, pz0, pz0 + 0.3)),
                    ("W", (px0, px0 + 0.3, pz0, pz1)), ("E", (px1 - 0.3, px1, pz0, pz1))):
        s.slab(f"Pool Wall {name}", pool, a[0], a[1], -1.3, 0.0, a[2], a[3], TILE)
    s.slab("Pool Water", pool, px0 + 0.3, px1 - 0.3, -0.5, -0.12, pz0 + 0.3, pz1 - 0.3, WATER,
           rough=0.2, emissive=(0.0, 0.55, 0.75), emissive_intensity=0.7, shadows=False)
    for name, a in (("N", (px0 - 0.3, px1 + 0.3, pz1, pz1 + 0.3)), ("S", (px0 - 0.3, px1 + 0.3, pz0 - 0.3, pz0)),
                    ("W", (px0 - 0.3, px0, pz0, pz1)), ("E", (px1, px1 + 0.3, pz0, pz1))):
        s.slab(f"Pool Coping {name}", pool, a[0], a[1], 0, 0.07, a[2], a[3], CONCRETE)
    # a marooned inflatable ring and a lounger
    s.box("Pool Ring", pool, (8.5, -0.1, -5.5), (1.1, 0.25, 1.1), (1.0, 0.45, 0.6), shape="Cylinder", rough=0.5)
    s.slab("Lounger Base", pool, 12.7, 13.6, 0.0, 0.3, -9.0, -6.6, (0.85, 0.85, 0.8))
    s.slab("Lounger Back", pool, 12.7, 13.6, 0.3, 0.9, -6.8, -6.6, (0.85, 0.85, 0.8))

    # ---- Props (existing Assets/Models/Venue) ----------------------------------------------
    pr = s.group("Party Props", props)
    # PA stacks and wedges on the patio
    s.prop("PA Left", pr, M + "SpeakerTall.obj", (-7.0, 0.25, 0.9), yaw=0)
    s.prop("PA Right", pr, M + "SpeakerTall.obj", (7.0, 0.25, 0.9), yaw=0)
    s.prop("Speaker Left", pr, M + "Speaker.obj", (-7.0, 0.25, 2.1), yaw=0)
    s.prop("Speaker Right", pr, M + "Speaker.obj", (7.0, 0.25, 2.1), yaw=0)
    s.prop("Wedge Vocals", pr, M + "Wedge.obj", (0.0, 0.25, 0.3), yaw=0)
    s.prop("Guitar Amp", pr, M + "GuitarCab.obj", (-4.4, 0.25, 4.6), yaw=0)
    s.prop("Drum Rug", pr, M + "DrumRug.obj", (0.0, 0.57, 6.3))
    s.prop("Pallet A", pr, M + "Pallet.obj", (-3.2, 0.25, 9.6), yaw=10)
    s.prop("Pallet B", pr, M + "Pallet.obj", (3.4, 0.25, 9.8), yaw=-8)
    # Snack island, left of the patio
    s.prop("Umbrella Table L", pr, M + "UmbrellaTable.obj", (-10.8, 0, 0.5))
    s.prop("Umbrella Table R", pr, M + "UmbrellaTable.obj", (-10.6, 0, 6.5))
    for i, (x, z) in enumerate([(-9.6, 2.9), (-9.2, 3.5), (-9.9, 3.8)]):
        s.prop(f"Keg {i}", pr, M + "Keg.obj", (x, 0, z))
    for i, (x, z) in enumerate([(-9.3, -1.2), (-8.6, 9.2), (9.5, 0.8)]):
        s.prop(f"Cooler {i}", pr, M + "Cooler.obj", (x, 0 if abs(x) > 8 else 0.25, z), yaw=rng.uniform(-30, 30))
    s.prop("Barrel A", pr, M + "Barrel.obj", (10.3, 0, 9.4))
    s.prop("Barrel B", pr, M + "Barrel.obj", (11.1, 0, 8.5))
    s.prop("Wheelie Bin A", pr, M + "WheelieBin.obj", (11.8, 0, 9.8), yaw=-15)
    s.prop("Wheelie Bin B", pr, M + "WheelieBin.obj", (-11.5, 0, 9.9), yaw=5)
    s.prop("Ladder", pr, M + "Ladder.obj", (6.6, 0, 10.7), yaw=180)
    for i in range(18):  # red cups: scattered with a seeded RNG, on the patio, tables and pool coping
        if i < 8:
            x, z, y = rng.uniform(-7.5, 7.5), rng.uniform(0.2, 10.5), 0.25
        elif i < 12:
            x, z, y = rng.uniform(-11.5, -10.0), rng.uniform(-0.5, 7.5), 0.0
        else:
            x, z, y = rng.uniform(4.7, 12.3), rng.uniform(-9.3, -1.7), 0.07
            if 5.3 < x < 11.7 and -8.7 < z < -2.3:
                x, z = (12.4, rng.uniform(-9, -2))
        s.prop(f"Cup {i}", pr, M + "BeerCup.obj", (x, y, z), yaw=rng.uniform(0, 360))
    for i in range(4):
        s.prop(f"Bottle {i}", pr, M + "Bottle.obj", (rng.uniform(-9.8, -9.0), 0, rng.uniform(3.0, 4.0)), yaw=rng.uniform(0, 360))
    # Flood lights bolted to the eave (the Blinder lights live in Lights)
    s.prop("Flood Light L", pr, M + "FloodLight.obj", (-3.2, 5.2, 10.6), yaw=180)
    s.prop("Flood Light R", pr, M + "FloodLight.obj", (3.2, 5.2, 10.6), yaw=180)
    # Sound desk at the back of the crowd (the Desk camera sits behind it)
    desk = s.group("Sound Desk", pr)
    s.slab("Desk Table", desk, -1.4, 1.4, 0.7, 0.78, -21.2, -20.4, (0.7, 0.7, 0.72))
    for x in (-1.2, 1.2):
        s.slab(f"Desk Leg {x:+.1f}", desk, x - 0.04, x + 0.04, 0, 0.7, -21.0, -20.9, (0.3, 0.3, 0.32))
    s.slab("Desk Mixer", desk, -0.5, 0.5, 0.78, 0.9, -21.1, -20.5, BLACK)
    # Party car on the lawn (greybox), nose toward the house, parked along the west fence.
    car = s.group("Party Car", pr)
    cx, cz = -12.3, -21.0
    s.slab("Car Body", car, cx - 0.95, cx + 0.95, 0.35, 0.95, cz - 2.2, cz + 2.2, (0.65, 0.12, 0.12), rough=0.4, metallic=0.3)
    s.slab("Car Cabin", car, cx - 0.85, cx + 0.85, 0.95, 1.45, cz - 1.0, cz + 1.0, (0.55, 0.1, 0.1), rough=0.4, metallic=0.3)
    s.slab("Car Windows", car, cx - 0.88, cx + 0.88, 1.0, 1.4, cz - 0.85, cz + 0.85, GLASS)
    for i, (dx, dz) in enumerate([(-0.9, -1.4), (0.9, -1.4), (-0.9, 1.4), (0.9, 1.4)]):
        s.slab(f"Car Wheel {i}", car, cx + dx - 0.12, cx + dx + 0.12, 0, 0.7, cz + dz - 0.35, cz + dz + 0.35, BLACK)
    s.box("Car Headlight L", car, (cx - 0.55, 0.65, cz + 2.22), (0.3, 0.2, 0.05), (1, 1, 0.8), emissive=(1, 1, 0.8), emissive_intensity=2.0)
    s.box("Car Headlight R", car, (cx + 0.55, 0.65, cz + 2.22), (0.3, 0.2, 0.05), (1, 1, 0.8), emissive=(1, 1, 0.8), emissive_intensity=2.0)
    # Patrol car at the kerb (greybox) with its light bar
    pc = s.group("Patrol Car", pr)
    qx, qz = -9.0, -35.4
    s.slab("Patrol Body", pc, qx - 2.3, qx + 2.3, 0.35, 0.95, qz - 0.95, qz + 0.95, (0.08, 0.08, 0.1), rough=0.4, metallic=0.3)
    s.slab("Patrol Door Stripe", pc, qx - 1.4, qx + 1.4, 0.35, 0.8, qz + 0.94, qz + 0.97, (0.9, 0.9, 0.9))
    s.slab("Patrol Cabin", pc, qx - 1.0, qx + 1.0, 0.95, 1.45, qz - 0.85, qz + 0.85, (0.06, 0.06, 0.08))
    for i, (dx, dz) in enumerate([(-1.5, -0.9), (1.5, -0.9), (-1.5, 0.9), (1.5, 0.9)]):
        s.slab(f"Patrol Wheel {i}", pc, qx + dx - 0.35, qx + dx + 0.35, 0, 0.7, qz + dz - 0.12, qz + dz + 0.12, BLACK)
    s.slab("Light Bar Red", pc, qx - 0.6, qx - 0.02, 1.45, 1.6, qz - 0.2, qz + 0.2, (1.0, 0.05, 0.05), emissive=(1, 0.05, 0.05), emissive_intensity=3.0)
    s.slab("Light Bar Blue", pc, qx + 0.02, qx + 0.6, 1.45, 1.6, qz - 0.2, qz + 0.2, (0.05, 0.1, 1.0), emissive=(0.05, 0.1, 1), emissive_intensity=3.0)

    # ---- Lights ---------------------------------------------------------------------------
    # String lights: three runs; cable = thin boxes along a sagging curve, bulbs = small emissive.
    sl = s.group("String Lights", lights)

    def run(name, a, b, sag, group, colors, n_seg=8, bulbs_every=2):
        pts = []
        for i in range(n_seg + 1):
            t = i / n_seg
            p = [a[k] + (b[k] - a[k]) * t for k in range(3)]
            p[1] -= sag * 4 * t * (1 - t)
            pts.append(p)
        g = s.group(name, sl)
        for i in range(n_seg):
            p, q = pts[i], pts[i + 1]
            mid = [(p[k] + q[k]) / 2 for k in range(3)]
            d = [q[k] - p[k] for k in range(3)]
            ln = math.sqrt(sum(v * v for v in d))
            # a thin box along local Z, aimed from p to q
            rot = [math.degrees(math.atan2(-d[1], math.hypot(d[0], d[2]))), math.degrees(math.atan2(d[0], d[2])), 0.0]
            s.box(f"{name} Cable {i}", g, mid, (0.02, 0.02, ln), BLACK, rot=rot, shadows=False)
        for i in range(0, n_seg + 1, bulbs_every):
            c = colors[(i // bulbs_every) % len(colors)]
            s.box(f"{name} Bulb {i}", g, (pts[i][0], pts[i][1] - 0.1, pts[i][2]), (0.14, 0.14, 0.14), c,
                  shape="Sphere", emissive=c, emissive_intensity=3.0, shadows=False)
        return pts

    warm = [(1.0, 0.75, 0.4), (1.0, 0.55, 0.25)]
    mixed = [(1.0, 0.3, 0.5), (0.3, 0.8, 1.0), (1.0, 0.85, 0.3), (0.5, 1.0, 0.5)]
    # Run 1: pergola corner to the west fence post across the lawn.
    r1 = run("Run West", (-3.9, 3.3, 3.9), (-14.1, 3.0, -14.0), 0.9, 0, warm, 10, 2)
    # Run 2: pergola corner to the east fence across the pool.
    r2 = run("Run East", (3.9, 3.3, 3.9), (14.1, 3.0, -12.0), 0.9, 1, mixed, 10, 2)
    # Run 3: across the lawn, fence to fence.
    r3 = run("Run Lawn", (-14.1, 3.2, -8.0), (14.1, 3.2, -8.0), 1.2, 2, mixed + warm, 14, 2)
    for tag, (px, py, pz) in (("W", (-14.1, 0, -14.0)), ("E", (14.1, 0, -12.0)), ("L", (-14.1, 0, -8.0)), ("R", (14.1, 0, -8.0))):
        s.slab(f"Pole {tag}", sl, px - 0.07, px + 0.07, 0, 3.4, pz - 0.07, pz + 0.07, WOOD)
    # Show lights for the strings: wash points under the cable, three per run.
    s.light("String Wash W0", lights, (-9.0, 2.6, -2.5), "Point", (1.0, 0.7, 0.35), 5.0, 9, show="Wash", group=0)
    s.light("String Wash W1", lights, (-11.0, 2.4, -8.5), "Point", (1.0, 0.6, 0.3), 5.0, 9, show="Wash", group=0)
    s.light("String Wash W2", lights, (-12.0, 2.4, -13.0), "Point", (1.0, 0.7, 0.35), 5.0, 9, show="Wash", group=0)
    s.light("String Wash E0", lights, (9.0, 2.6, 0.5), "Point", (1.0, 0.3, 0.6), 5.0, 9, show="Wash", group=1)
    s.light("String Wash E1", lights, (12.0, 2.4, -6.0), "Point", (0.4, 0.8, 1.0), 5.0, 9, show="Wash", group=1)
    s.light("String Wash E2", lights, (13.0, 2.4, -11.0), "Point", (1.0, 0.85, 0.3), 5.0, 9, show="Wash", group=1)
    s.light("String Wash L0", lights, (-6.0, 2.6, -8.3), "Point", (0.4, 1.0, 0.6), 6.0, 10, show="Wash", group=2)
    s.light("String Wash L1", lights, (0.0, 2.2, -8.3), "Point", (1.0, 0.5, 0.7), 6.0, 10, show="Wash", group=2)
    s.light("String Wash L2", lights, (6.0, 2.6, -8.3), "Point", (0.4, 0.7, 1.0), 6.0, 10, show="Wash", group=2)
    # Pool glow: a cyan wash just above the water (a light under an opaque water slab would light nothing).
    s.light("Pool Glow", lights, (8.5, 0.35, -5.5), "Point", (0.1, 0.85, 1.0), 6.0, 9, show="Wash", group=3)
    # Band washes from the pergola's front beam, warm and magenta.
    s.light("Band Wash L", lights, (-2.6, 3.2, 3.8), "Spot", (1.0, 0.45, 0.2), 6.0, 14, rot=(55, -12, 0), inner=25, outer=50, show="Wash", group=4)
    s.light("Band Wash R", lights, (2.6, 3.2, 3.8), "Spot", (0.9, 0.2, 0.7), 6.0, 14, rot=(55, 12, 0), inner=25, outer=50, show="Wash", group=4)
    # Beams: narrow coloured spots from the eave over the crowd.
    for i, (x, col) in enumerate([(-9.0, (0.2, 0.5, 1.0)), (-3.0, (1.0, 0.2, 0.4)), (3.0, (0.3, 1.0, 0.5)), (9.0, (1.0, 0.8, 0.2))]):
        s.light(f"Eave Beam {i}", lights, (x, 5.6, 10.0), "Spot", col, 8.0, 30, rot=(35 + 4 * (i % 2), (-1 if x < 0 else 1) * 10, 0),
                inner=6, outer=12, show="Beam", group=i % 2)
    # Blinders: wide white floods at the eave aimed at the crowd.
    for i, x in enumerate((-3.2, 3.2)):
        s.light(f"Blinder {i}", lights, (x, 5.0, 10.4), "Spot", (1.0, 0.95, 0.85), 10.0, 26, rot=(28, 0, 0), inner=30, outer=60, show="Blinder", group=0)
    # Searchlight from above ("helicopter"), a narrow follow spot on the drummer.
    s.light("Searchlight", lights, (-6.0, 40.0, -30.0), "Spot", (0.9, 0.95, 1.0), 20.0, 90,
            rot=look_at((-6.0, 40.0, -30.0), (0.0, 0.8, 6.2)), inner=2.5, outer=4.0, show="Spot", group=0)
    # Strobes: the patrol car's red/blue pair.
    s.light("Patrol Red", lights, (qx - 0.3, 1.9, qz), "Point", (1.0, 0.05, 0.05), 14.0, 22, show="Strobe", group=0)
    s.light("Patrol Blue", lights, (qx + 0.3, 1.9, qz), "Point", (0.1, 0.2, 1.0), 14.0, 22, show="Strobe", group=1)
    # Tiki torches: static warm points (the flame is a small emissive box).
    tk = s.group("Tiki Torches", lights)
    for i, (x, z) in enumerate([(-8.5, 0.8), (8.5, 0.8), (-12.5, -6.0), (4.0, -1.2), (12.8, -1.5), (0.0, -10.5)]):
        s.slab(f"Torch {i} Pole", tk, x - 0.04, x + 0.04, 0, 1.8, z - 0.04, z + 0.04, WOOD)
        s.box(f"Torch {i} Flame", tk, (x, 1.95, z), (0.14, 0.26, 0.14), (1.0, 0.5, 0.1), shape="Sphere",
              emissive=(1.0, 0.5, 0.1), emissive_intensity=4.0, shadows=False)
        s.light(f"Torch {i} Light", tk, (x, 2.0, z), "Point", (1.0, 0.55, 0.2), 2.0, 6.5, show="Static")
    # Moonlight: the only shadowed light. Travels from the street side over the crowd toward the
    # house, so it rims the crowd and lights the band's front. Manual so it keeps this rotation.
    s.light("Moon", lights, (0, 30, -40), "Directional", (0.55, 0.65, 1.0), 1.6,
            rot=(48, 18, 0), shadows=True, show="Static")

    # ---- Markers --------------------------------------------------------------------------
    s.info(marks, "Backyard Party", "Drumsmith", outdoor=True, room_back=-30.0, half_width=14.0, desk_z=-20.0)
    s.spot(marks, "Drummer", (0.0, 0.55, 6.2))
    s.spot(marks, "Guitar", (-3.6, 0.25, 2.9))
    s.spot(marks, "Bass", (3.6, 0.25, 3.1))
    s.spot(marks, "Vocals", (0.0, 0.25, 1.4))
    s.spot(marks, "Keys", (-5.6, 0.25, 5.2))
    cr = s.group("Crowd Areas", marks)
    s.crowd("Crowd Front", cr, (-3.0, 0.0, -5.5), 14.0, 6.0, 70, jitter=0.6)
    s.crowd("Crowd Mid", cr, (-3.5, 0.0, -13.0), 15.0, 8.0, 75, jitter=0.7)
    s.crowd("Crowd Back", cr, (-2.0, 0.0, -19.5), 16.0, 4.0, 40, jitter=0.7)
    s.crowd("Crowd Pool Side", cr, (8.5, 0.0, -14.5), 7.0, 6.0, 30, jitter=0.7)
    cm = s.group("Camera Spots", marks)
    s.camera_spot("Cam Wide Lawn", cm, (0.0, 4.6, -28.8), (0.0, 2.0, 6.0), "Wide", 52)
    s.camera_spot("Cam Crane Crowd", cm, (3.0, 8.5, -9.0), (0.0, 1.4, 5.0), "Crane", 55)
    s.camera_spot("Cam Behind Drummer", cm, (-0.8, 2.0, 9.6), (0.0, 1.6, -6.0), "Custom", 60, "behind-drummer")
    s.camera_spot("Cam Roof", cm, (-4.0, 7.6, 12.6), (0.0, 1.0, -8.0), "Crane", 60, "roof")
    s.camera_spot("Cam Through Crowd", cm, (-2.0, 1.8, -10.5), (0.0, 1.8, 5.0), "Custom", 38, "through-crowd")
    s.camera_spot("Cam Desk", cm, (0.0, 2.2, -22.0), (0.0, 1.8, 4.0), "Desk", 30)
    s.camera_spot("Cam Vocal Close", cm, (1.6, 1.6, -1.4), (0.0, 1.5, 1.4), "Close", 40)
    s.camera_spot("Cam Drummer Close", cm, (3.6, 1.6, 2.2), (0.0, 1.1, 6.2), "Close", 38)
    s.camera_spot("Cam Pool Side", cm, (13.4, 1.8, -0.8), (0.0, 1.5, 4.0), "Custom", 50, "pool-side")
    # Projector sheet on the house wall: shows the Program feed to the crowd. The picture faces -Z.
    s.screen("Projector Sheet", marks, (-9.0, 4.8, 10.9), 4.0, 2.25, "Program", 2.0)
    return s


def look_at(eye, target):
    from venuegen import look_rotation
    return look_rotation(eye, target)


def main():
    folder = os.path.join(repo_root(), "Assets", "Venues", "Backyard")
    build().write(os.path.join(folder, "Backyard.lvl"))
    write_venue_json(folder, "Backyard Party", "Backyard.lvl")
    print("wrote", folder)


if __name__ == "__main__":
    main()
