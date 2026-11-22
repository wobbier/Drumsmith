#!/usr/bin/env python3
"""Writes Assets/Venues/StorySteelMill/: story set 10, "One Night on the Steel Mill Tour".

    python3 Tools/Venues/make_story_steel_mill.py

A metal package tour in a decommissioned rolling mill. A festival stage is built inside Rolling
Mill No. 3, framed by the mill's own girders: columns down both walls, roof trusses, two gantry
cranes (one carries the lighting trusses on chains, the other hangs an old ladle full of orange
light over the mosh pit), the rusted roll stands and roller table down the right wall, steel coils
on the left. The changeover wing is stage left (the crowd's left, -x), lit by work tubes, full of
road cases and, as the night goes on, of the other bands.

The story (Design/Story-Mode-Setlists.json, s10-steel-mill), one change per flag:
  sheet_one   sheet 1 (white) taped by the floor tom; the first of five act lamps on the
              mill header comes on.
  sheet_two   the blue sheet; lamp 2; the opener's bass player in the wing with a towel round
              their neck, beside the opener's cases.
  sheet_three sheet 3; lamp 3; the first two acts watch from the wing, a roll of tape on the
              wing monitor; the crew stop clearing the wing (the dolly and KEEP CLEAR sign go,
              stools and a cooler arrive).
  sheet_four  sheet 4; lamp 4; a work lamp comes on beyond the sheets with a big road case
              under it, its stencil still turned to the back wall; the crew chief beside it;
              act 3 in the wing.
  case_faces_house  the case turns into the work light so DRUMS reads from the back rows;
              sheet 5 and lamp 5; the four earlier singers come out beside the sheets.

Deterministic: rerun = same bytes. Textures: story_steel_mill_textures.py; the figures:
story_steel_mill_people.py.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from venuegen import Scene, look_rotation, repo_root, write_venue_json  # noqa: E402
import story_steel_mill_people as people  # noqa: E402
import story_steel_mill_textures as paint  # noqa: E402

VID = "StorySteelMill"
TITLE = "One Night on the Steel Mill Tour"
VM = "Assets/Models/Venue/"

# Palette: the mill's painted steel, its rust, the tour's orange and steel-blue.
STEEL = (0.15, 0.21, 0.29)
STEEL_DK = (0.07, 0.085, 0.11)
STEEL_LT = (0.36, 0.40, 0.45)
RUST = (0.36, 0.15, 0.06)
RUST_DK = (0.18, 0.08, 0.04)
CONCRETE = (0.19, 0.19, 0.20)
BLACK = (0.025, 0.025, 0.03)
DECK = (0.06, 0.055, 0.05)
YELLOW = (0.85, 0.60, 0.05)
ORANGE = (1.0, 0.42, 0.08)
AMBER = (1.0, 0.62, 0.25)
BLUE = (0.30, 0.55, 1.0)
ICE = (0.62, 0.78, 1.0)
WHITE = (0.92, 0.92, 0.90)

STAGE_Y = 1.6
RISER_Y = 2.3
WING_X0, WING_X1 = -17.0, -10.4


def build():
    if "--textures" in sys.argv or not os.path.exists(os.path.join(paint.OUT, "MillWindow.png")):
        paint.build()
    people.clips()
    s = Scene(seed="steel-mill-s10")
    root = s.group(TITLE)
    mill = s.group("Rolling Mill No. 3", root)
    stage = s.group("Festival stage", root)
    wing = s.group("Changeover wing", root)
    story = s.group("Story: five sheets and a road case", root)
    lights = s.group("Lights", root)
    marks = s.group("Venue markers", root)

    def box(name, parent, pos, size, col, **kw):
        return s.box(name, parent, pos, size, col, **kw)

    def slab(name, parent, x0, x1, y0, y1, z0, z1, col, **kw):
        return s.slab(name, parent, x0, x1, y0, y1, z0, z1, col, **kw)

    def textured(name, parent, pos, size, tex, col=(1, 1, 1), rot=(0, 0, 0), tiling=None, emissive=None,
                 emissive_intensity=1.0, rough=0.85, shadows=True, emissive_tex=False):
        e = s.box(name, parent, pos, size, col, rot=rot, rough=rough, emissive=emissive,
                  emissive_intensity=emissive_intensity, shadows=shadows)
        mat = e.components[-1]["Material"]
        mat["Textures"] = {"Diffuse": {"Path": paint.tex(tex), "RenderMode": "Opaque"}}
        if emissive_tex:
            mat["Textures"]["Emissive"] = {"Path": paint.tex(tex), "RenderMode": "Opaque"}
        if tiling:
            mat["Tiling"] = [round(tiling[0], 4), round(tiling[1], 4)]
        return e

    def strut(name, parent, a, b, t, col, **kw):
        """A member from a to b in a plane of constant z (rotation about z only)."""
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, a[2])
        return box(name, parent, mid, (length, t, t), col, rot=(0, 0, math.degrees(math.atan2(dy, dx))), **kw)

    def column(name, parent, x, z, y0, y1, d=0.9, w=0.6, col=STEEL):
        """An I-section column: web along z, flanges facing the crowd and the back wall."""
        g = s.group(name, parent, (x, 0, z))
        h = y1 - y0
        box("Web", g, (0, y0 + h / 2, 0), (0.07, h, d), col)
        for side in (-1, 1):
            box("Flange", g, (0, y0 + h / 2, side * d / 2), (w, h, 0.06), col)
        box("Base plate", g, (0, y0 + 0.04, 0), (w + 0.4, 0.08, d + 0.4), STEEL_DK)
        return g

    def beam_x(name, parent, x0, x1, y, z, d=0.9, w=0.5, col=STEEL, shadows=True):
        """An I-beam along x, its top at y + d/2."""
        g = s.group(name, parent, ((x0 + x1) / 2, y, z))
        L = x1 - x0
        box("Web", g, (0, 0, 0), (L, d, 0.06), col, shadows=shadows)
        for side in (-1, 1):
            box("Flange", g, (0, side * d / 2, 0), (L, 0.06, w), col, shadows=shadows)
        return g

    def beam_z(name, parent, x, y, z0, z1, d=0.9, w=0.5, col=STEEL):
        g = s.group(name, parent, (x, y, (z0 + z1) / 2))
        L = z1 - z0
        box("Web", g, (0, 0, 0), (0.06, d, L), col)
        for side in (-1, 1):
            box("Flange", g, (0, side * d / 2, 0), (w, 0.06, L), col)
        return g

    def chain(name, parent, top, length, link=0.13, col=STEEL_DK):
        """A hanging chain of alternating links from top downwards."""
        g = s.group(name, parent, top)
        n = max(2, int(length / link))
        for i in range(n):
            box("Link", g, (0, -link * (i + 0.5), 0), (0.05, link * 1.25, 0.022), col,
                rot=(0, 90 if i % 2 else 0, 0), metallic=0.6, rough=0.5, shadows=False)
        return g

    def cyl(name, parent, pos, radius, length, col, axis="y", **kw):
        rot = {"y": (0, 0, 0), "x": (0, 0, 90), "z": (90, 0, 0)}[axis]
        return box(name, parent, pos, (radius * 2, length, radius * 2), col, rot=rot, shape="Cylinder", **kw)

    # ------------------------------------------------------------------------------------------
    # The mill: floor, walls, windows, roof, columns, trusses, crane runways.
    hall = s.group("Hall", mill)
    slab("Mill floor", hall, -27.5, 27.5, -0.3, 0.0, -47, 17, CONCRETE, rough=0.95)
    for x in (-16.0, -15.2, 15.2, 16.0):
        slab("Old rail in the floor", hall, x - 0.06, x + 0.06, 0.0, 0.03, -46, -1.8, STEEL_LT, metallic=0.8, rough=0.35)
    for x in (-19.0, 19.0):
        textured("Walkway line", hall, (x, 0.012, -22), (0.22, 0.02, 46), "Hazard", tiling=(1, 60))
    # Walls: corrugated steel, the windows high in each bay.
    for side in (-1, 1):
        textured("Side wall", hall, (side * 27.2, 12, -15), (0.3, 24, 64), "Corrugated", STEEL, tiling=(64, 12))
    textured("Back wall", hall, (0, 12, 16.9), (55, 24, 0.3), "Corrugated", STEEL, tiling=(55, 12))
    textured("Doors wall", hall, (0, 12, -47), (55, 24, 0.3), "Corrugated", STEEL, tiling=(55, 12))
    textured("Big rolling door", hall, (8, 4.5, -46.8), (9, 9, 0.2), "Corrugated", STEEL_LT, tiling=(9, 4))
    textured("Door hazard head", hall, (8, 9.25, -46.75), (9.4, 0.5, 0.2), "Hazard", tiling=(8, 1))
    box("Exit sign", hall, (-14, 3.2, -46.75), (1.0, 0.36, 0.08), (0.1, 0.8, 0.3), emissive=(0.1, 1, 0.35),
        emissive_intensity=3, shadows=False)
    wins = s.group("Mill windows", hall)
    for side in (-1, 1):
        for z in (-37, -27, -17, -7, 3, 12):
            textured("Window", wins, (side * 27.0, 13, z), (0.12, 6.0, 7.0), "MillWindow", (0.7, 0.8, 1.0),
                     emissive=(0.20, 0.30, 0.48), emissive_intensity=1.0, emissive_tex=True, shadows=False)
    for x in (-15, -5, 5, 15):
        textured("High window", wins, (x, 18, 16.7), (8.0, 9.0, 0.12), "MillWindow", (0.7, 0.8, 1.0),
                 emissive=(0.20, 0.30, 0.48), emissive_intensity=1.0, emissive_tex=True, shadows=False)
    # Roof: a shallow gable on trusses; it casts no shadow so the moon reaches the floor through
    # the skylights.
    roof = s.group("Roof", mill)
    for side in (-1, 1):
        box("Roof sheet", roof, (side * 13.7, 25.2, -15), (27.8, 0.25, 64), (0.05, 0.055, 0.065),
            rot=(0, 0, -side * 7), shadows=False)
        for z in (-36, -22, -8, 6):
            box("Skylight", roof, (side * 9, 24.65, z), (4, 0.12, 6), (0.3, 0.4, 0.6), rot=(0, 0, -side * 7),
                emissive=(0.22, 0.32, 0.55), emissive_intensity=0.8, shadows=False)
    girders = s.group("Columns and trusses", mill)
    bays = (-42, -32, -22, -12, -2, 8, 15.6)
    for z in bays:
        for side in (-1, 1):
            column("Column", girders, side * 25.6, z, 0, 23.2, col=STEEL if z % 20 else RUST)
            # Crane corbel under the runway.
            box("Corbel", girders, (side * 24.8, 15.0, z), (1.4, 0.8, 0.7), STEEL_DK)
        # Roof truss: bottom chord, peaked top chord, verticals and diagonals.
        tg = s.group("Roof truss", girders)
        box("Bottom chord", tg, (0, 21.6, z), (51, 0.35, 0.35), STEEL, shadows=False)
        for side in (-1, 1):
            strut("Top chord", tg, (side * 25.4, 23.2, z), (0, 26.3, z), 0.38, STEEL, shadows=False)
        for k in range(-6, 7):
            x = k * 4.0
            top = 26.3 - abs(x) / 25.4 * 3.1
            strut("Vertical", tg, (x, 21.6, z), (x, top, z), 0.16, STEEL_DK, shadows=False)
            if k < 6:
                x2 = x + 4.0
                top2 = 26.3 - abs(x2) / 25.4 * 3.1
                if x >= 0:
                    strut("Diagonal", tg, (x, top, z), (x2, 21.6, z), 0.14, STEEL_DK, shadows=False)
                else:
                    strut("Diagonal", tg, (x, 21.6, z), (x2, top2, z), 0.14, STEEL_DK, shadows=False)
    for side in (-1, 1):
        beam_z("Crane runway", girders, side * 24.5, 15.9, -46, 16.5, d=1.0, col=RUST)
        slab("Crane rail", girders, side * 24.5 - 0.06, side * 24.5 + 0.06, 16.4, 16.52, -46, 16.5, STEEL_LT, metallic=0.8)
    # Chains hanging from the trusses where hoists used to be.
    for x, z, L in [(-17, -22, 5.5), (-9, -32, 3.5), (13, -32, 6.0), (19, -12, 4.0), (-21, -2, 7.5), (7, -42, 4.5)]:
        chain("Hanging chain", girders, (x, 21.4, z), L)
        box("Chain hook", girders, (x, 21.4 - L - 0.12, z), (0.08, 0.26, 0.2), RUST_DK, shadows=False)

    # Gantry crane over the pit: a double box girder with an old ladle on the hook, rigged with
    # orange light and the occasional shower of sparks.
    crane = s.group("Gantry crane over the pit", mill)
    cz = -16.0
    for dz in (-0.7, 0.7):
        box("Bridge girder", crane, (0, 16.9, cz + dz), (49, 1.5, 0.6), YELLOW, rough=0.7)
        textured("Bridge stripes", crane, (0, 16.15, cz + dz), (49, 0.1, 0.62), "Hazard", tiling=(40, 1))
    for side in (-1, 1):
        box("End truck", crane, (side * 24.5, 16.9, cz), (1.0, 0.9, 4.2), YELLOW)
    textured("Capacity plate", crane, (0, 16.9, cz - 1.02), (4.4, 1.1, 0.06), "CranePlate")
    box("Trolley", crane, (9.0, 18.0, cz), (3.0, 0.8, 2.6), (0.7, 0.5, 0.06))
    box("Hoist drum", crane, (9.0, 18.6, cz), (1.0, 1.0, 2.0), STEEL_DK, shape="Cylinder", rot=(90, 0, 0))
    for dx in (-0.35, 0.35):
        for dz in (-0.3, 0.3):
            box("Hoist rope", crane, (9.0 + dx, 15.6, cz + dz), (0.05, 4.6, 0.05), STEEL_DK, shape="Cylinder", shadows=False)
    box("Hook block", crane, (9.0, 12.9, cz), (1.1, 0.9, 0.7), YELLOW)
    box("Hook", crane, (9.0, 12.2, cz), (0.25, 0.6, 0.25), STEEL_DK)
    for side in (-1, 1):
        strut("Ladle bail", crane, (9.0, 12.0, cz), (9.0 + side * 1.75, 9.9, cz), 0.16, RUST_DK)
    ladle = s.group("Old ladle", crane, (9.0, 8.9, cz))
    cyl("Ladle shell", ladle, (0, 0, 0), 1.6, 2.2, RUST, rough=0.95)
    cyl("Ladle rim", ladle, (0, 1.1, 0), 1.72, 0.2, RUST_DK)
    cyl("Ladle glow", ladle, (0, 1.15, 0), 1.45, 0.08, ORANGE, emissive=ORANGE, emissive_intensity=6, shadows=False)
    cyl("Ladle lip", ladle, (1.6, 0.9, 0), 0.3, 0.5, RUST_DK, axis="x")
    sparks = s.entity("Ladle sparks", ladle, (1.85, 0.9, 0), (0, 0, -100))
    sparks.add({"Type": "ParticleSystem", "Simulation": "CPU", "SimulationSpace": "World", "Shape": "Cone",
                "ConeAngle": 28, "ShapeRadius": 0.15, "Lifetime": [0.9, 1.8], "Speed": [1.5, 4.0],
                "Size": [0.035, 0.07], "StartColor": [1.0, 0.75, 0.3], "StartColor2": [1.0, 0.5, 0.12],
                "EndColor": [0.8, 0.18, 0.02], "Intensity": 3.0, "Gravity": 0.9, "Drag": 0.3,
                "NoiseStrength": 0.3, "EmissionRate": 34, "MaxParticles": 160, "Alignment": "Stretched",
                "StretchFactor": 0.12, "EndSize": 0.6, "FadeIn": 0.02, "SoftParticleDistance": 0})
    burst = s.entity("Ladle pour on the peaks", ladle, (1.85, 0.95, 0), (0, 0, -95))
    burst.add({"Type": "VenueAccent", "Beats": 8, "Particles": 380})
    burst.add({"Type": "ParticleSystem", "Simulation": "CPU", "SimulationSpace": "World", "Shape": "Cone",
               "ConeAngle": 35, "ShapeRadius": 0.25, "Lifetime": [1.2, 2.4], "Speed": [3.0, 7.0],
               "Size": [0.04, 0.09], "StartColor": [1.0, 0.8, 0.35], "StartColor2": [1.0, 0.45, 0.1],
               "EndColor": [0.8, 0.15, 0.02], "Intensity": 4.0, "Gravity": 0.8, "Drag": 0.35,
               "NoiseStrength": 0.4, "EmissionRate": 0, "BurstCount": 0, "MaxParticles": 512,
               "Alignment": "Stretched", "StretchFactor": 0.14, "EndSize": 0.6, "FadeIn": 0.02,
               "SoftParticleDistance": 0})
    s.light("Ladle glow", ladle, (0, 2.4, 0), "Point", ORANGE, 900, 16)

    # The stage crane: its bridge carries the two lighting trusses on chains.
    crane2 = s.group("Gantry crane over the stage", mill)
    for dz in (-0.6, 0.6):
        box("Bridge girder", crane2, (0, 17.4, 6.0 + dz), (49, 1.3, 0.5), RUST, rough=0.9)
    for side in (-1, 1):
        box("End truck", crane2, (side * 24.5, 17.2, 6.0), (1.0, 0.9, 3.8), RUST_DK)

    # The rolling line down the right wall: roller table, two roll stands, a glowing slab.
    line = s.group("Roll stands and roller table", mill)
    lx = 20.0
    for side in (-1, 1):
        slab("Table rail", line, lx + side * 1.6 - 0.15, lx + side * 1.6 + 0.15, 0, 1.0, -40, 6, RUST_DK)
    for k in range(58):
        z = -39.4 + k * 0.78
        cyl("Table roller", line, (lx, 1.05, z), 0.22, 3.0, RUST if k % 3 else STEEL_LT, axis="x", rough=0.6, metallic=0.3)
    for z0 in (-12.0, -5.0):
        st = s.group("Roll stand", line, (lx, 0, z0))
        for side in (-1, 1):
            box("Housing post", st, (side * 2.4, 4.2, 0), (1.1, 8.4, 1.6), RUST)
        box("Crosshead", st, (0, 8.8, 0), (6.0, 1.0, 1.8), RUST_DK)
        box("Screwdown", st, (0, 9.8, 0), (1.2, 1.0, 1.2), STEEL_DK, shape="Cylinder")
        for y, r in [(1.9, 0.8), (3.55, 0.65), (5.0, 0.65), (6.75, 0.8)]:
            cyl("Roll", st, (0, y, 0), r, 4.4, STEEL_LT if r < 0.7 else RUST, axis="x", rough=0.4, metallic=0.5)
        for side in (-1, 1):
            cyl("Spindle", st, (side * 3.6, 4.3, 0), 0.25, 1.5, STEEL_DK, axis="x")
        box("Motor housing", st, (-4.6, 2.2, 0), (1.6, 4.4, 2.4), STEEL)
    box("Hot slab", line, (lx, 1.4, -23), (2.2, 0.35, 6.0), ORANGE, emissive=(1.0, 0.35, 0.05), emissive_intensity=4.5,
        shadows=False)
    box("Cooling slab", line, (lx, 1.4, -30), (2.2, 0.35, 5.0), RUST, emissive=(0.8, 0.18, 0.03), emissive_intensity=1.2)
    s.light("Heat off the slab", line, (lx - 1.5, 2.6, -23), "Point", ORANGE, 520, 14)
    s.light("Heat between the stands", line, (lx - 2.5, 3.0, -8.5), "Point", (1.0, 0.36, 0.08), 380, 11)
    # Left side: coils, scrap skips and the catwalk where people climb for a view.
    store = s.group("Coil store and catwalk", mill)
    for i, (x, z, y) in enumerate([(-21.0, -40, 1.0), (-21.0, -37.6, 1.0), (-21.0, -35.2, 1.0), (-21.0, -38.8, 2.9),
                                   (-21.0, -36.4, 2.9), (-21.5, -30, 1.0), (-21.5, -27.6, 1.0)]):
        cyl("Steel coil", store, (x, y, z), 1.0, 2.0, STEEL_LT if i % 2 else RUST, axis="x", metallic=0.6, rough=0.45)
        cyl("Coil eye", store, (x, y, z), 0.42, 2.04, BLACK, axis="x")
    for z in (-12.0, -6.5):
        slab("Scrap skip", store, -23.5, -19.5, 0, 1.8, z - 1.4, z + 1.4, YELLOW)
        slab("Scrap", store, -23.2, -19.8, 1.8, 2.3, z - 1.1, z + 1.1, RUST_DK)
    cw_y = 6.0
    slab("Catwalk grating", store, -26.9, -23.0, cw_y - 0.12, cw_y, -38, -4, STEEL_DK)
    for z in range(-38, -3, 2):
        box("Rail post", store, (-23.05, cw_y + 0.55, z), (0.06, 1.1, 0.06), YELLOW, shadows=False)
    box("Hand rail", store, (-23.05, cw_y + 1.1, -21), (0.08, 0.08, 34), YELLOW, shadows=False)
    box("Knee rail", store, (-23.05, cw_y + 0.55, -21), (0.06, 0.06, 34), YELLOW, shadows=False)
    for z in (-34, -20, -8):
        box("Catwalk hanger", store, (-23.2, (cw_y + 21.6) / 2, z), (0.08, 21.6 - cw_y, 0.08), STEEL_DK, shadows=False)
    for k in range(14):
        box("Stair tread", store, (-24.4, cw_y * (13 - k) / 14 + 0.2, -3.8 + k * 0.32), (1.2, 0.06, 0.3), STEEL_DK)
    for x in (-25.0, -23.8):
        box("Stair stringer", store, (x, cw_y / 2, -1.7), (0.08, 0.3, math.hypot(cw_y, 4.5)), YELLOW,
            rot=(math.degrees(math.atan2(cw_y, 4.5)), 0, 0))

    # ------------------------------------------------------------------------------------------
    # The festival stage, built into the mill's girders.
    slab("Stage deck", stage, -10.4, 10.4, 0, STAGE_Y, 0, 12.4, DECK)
    slab("Stage skirt", stage, -10.4, 10.4, 0.0, STAGE_Y - 0.02, -0.05, 0.0, BLACK)
    slab("Stage-right deck", stage, 10.4, 16.0, 0, STAGE_Y, 0, 12.4, DECK)
    slab("Lip edge", stage, -10.4, 10.4, STAGE_Y - 0.04, STAGE_Y + 0.02, -0.05, 0.12, (0.6, 0.6, 0.6),
         emissive=(0.6, 0.6, 0.6), emissive_intensity=0.4)
    slab("Riser", stage, -3.4, 3.4, STAGE_Y, RISER_Y, 5.2, 9.6, BLACK)
    slab("Riser carpet", stage, -3.3, 3.3, RISER_Y, RISER_Y + 0.02, 5.3, 9.5, (0.09, 0.05, 0.05))
    slab("Riser face", stage, -3.4, 3.4, STAGE_Y, RISER_Y, 5.17, 5.2, (0.05, 0.05, 0.055))
    for x in (-3.3, 3.3):
        slab("Riser edge tape", stage, x - 0.04, x + 0.04, RISER_Y - 0.02, RISER_Y + 0.025, 5.15, 9.6, WHITE)
    slab("Riser front tape", stage, -3.4, 3.4, RISER_Y - 0.02, RISER_Y + 0.025, 5.15, 5.23, WHITE)
    # The backdrop and the mill's own portal of girders around the stage.
    textured("Tour drop", stage, (0, 7.05, 12.3), (20.8, 10.9, 0.1), "TourDrop", (0.85, 0.85, 0.85))
    portal = s.group("Mill girder portal", stage)
    for side in (-1, 1):
        g = s.group("Portal column", portal, (side * 11.2, 0, 0.4))
        for dx in (-0.45, 0.45):
            box("Flange", g, (dx, 7.4, 0), (0.08, 14.8, 0.9), RUST)
        box("Web", g, (0, 7.4, 0), (0.9, 14.8, 0.06), RUST_DK)
        for y in range(1, 14, 2):
            box("Batten", g, (0, y, 0), (0.95, 0.12, 0.95), STEEL_DK)
        box("Base plate", g, (0, 0.05, 0), (1.6, 0.1, 1.6), STEEL_DK)
        strut("Knee brace", portal, (side * 10.8, 10.2, 0.4), (side * 8.2, 13.2, 0.4), 0.3, RUST)
    beam_x("Portal header", portal, -11.8, 11.8, 13.9, 0.4, d=1.6, w=0.9, col=RUST)
    textured("Header plate", portal, (0, 13.9, -0.07), (14.0, 1.5, 0.05), "MillHeader")
    for x in range(-11, 12, 1):
        box("Rivet row", portal, (x + 0.5, 14.62, -0.06), (0.06, 0.06, 0.04), STEEL_DK, shadows=False)
    # Lighting trusses hung from the stage crane on chains.
    for tz, ty in ((3.2, 10.6), (9.4, 11.6)):
        tg = s.group("Lighting truss", stage, (0, ty, tz))
        for dy in (-0.25, 0.25):
            for dz in (-0.25, 0.25):
                box("Chord", tg, (0, dy, dz), (21.0, 0.06, 0.06), (0.55, 0.56, 0.58), metallic=0.7, rough=0.4, shadows=False)
        for k in range(21):
            x = -10.0 + k
            strut("Lattice", tg, (x, -0.25, -0.25), (x + 1, 0.25, -0.25), 0.04, (0.55, 0.56, 0.58), shadows=False)
        for x in (-8.0, 0.0, 8.0):
            chain("Truss chain", tg, (x, 17.4 - 0.65 - ty, 0), 17.4 - 0.65 - ty - 0.25)
    # PA: hung line arrays at the portal, sub stacks on the floor, side fills.
    pa = s.group("PA", stage)
    for side in (-1, 1):
        g = s.group("Line array", pa, (side * 12.6, 13.0, 0.0))
        box("Array bumper", g, (0, 0.1, 0), (1.4, 0.12, 0.9), STEEL_DK)
        chain("Array chain", g, (0, 1.05, 0), 0.9)
        for k in range(10):
            ang = 2 + k * 2.2
            y = -0.25 - k * 0.42
            box("Array box", g, (0, y, -0.01 * k * k), (1.3, 0.40, 0.75), BLACK, rot=(ang, 0, 0))
            box("Array grille", g, (0, y, -0.38 - 0.01 * k * k), (1.2, 0.30, 0.02), (0.1, 0.1, 0.11), rot=(ang, 0, 0),
                shadows=False)
        for k, x in enumerate((7.0, 8.3, 9.6)):
            for y in (0.0, 0.75):
                box("Sub", pa, (side * x, y + 0.37, -0.9), (1.25, 0.74, 0.9), BLACK)
                box("Sub grille", pa, (side * x, y + 0.37, -1.36), (1.1, 0.6, 0.02), (0.09, 0.09, 0.1))
    for x in (12.2, 13.5):
        for y in (STAGE_Y, STAGE_Y + 1.0):
            s.prop("Side fill", pa, VM + "Speaker.obj", (x, y, 1.4), yaw=200)
    # Barricade and the photo pit.
    bar = s.group("Barricade", stage)
    for k in range(10):
        x = -9.0 + k * 2.0
        box("Barrier top", bar, (x, 1.15, -1.8), (1.95, 0.1, 0.1), STEEL_LT, metallic=0.7, rough=0.4)
        box("Barrier face", bar, (x, 0.6, -1.85), (1.95, 1.0, 0.04), (0.28, 0.30, 0.33), metallic=0.5)
        box("Barrier foot", bar, (x, 0.03, -1.35), (1.95, 0.06, 1.0), STEEL_DK)
    # Monitor world and amps.
    gear = s.group("Backline", stage)
    for x in (-5.6, -4.0):
        s.prop("Guitar cab", gear, VM + "GuitarCab.obj", (x, STAGE_Y, 8.6), yaw=180, scale=1.4)
        s.prop("Amp head", gear, VM + "AmpHead.obj", (x, STAGE_Y + 1.05, 8.6), yaw=180, scale=1.4)
    for x in (4.0, 5.6):
        s.prop("Bass cab", gear, VM + "SpeakerTall.obj", (x, STAGE_Y, 8.7), yaw=180, scale=1.3)
    for x, z, yaw in [(-4.8, 2.2, 0), (4.8, 2.4, 0), (-1.0, 0.9, 10), (1.0, 0.9, -10), (1.9, 5.0, 30)]:
        s.prop("Wedge", gear, VM + "Wedge.obj", (x, STAGE_Y, z), yaw=yaw, scale=1.1)
    s.prop("Drum rug", gear, VM + "DrumRug.obj", (0, RISER_Y + 0.02, 7.3), yaw=0, scale=0.8)
    s.prop("Stage fan", gear, VM + "StageFan.obj", (2.9, RISER_Y, 8.6), yaw=210)
    s.prop("Amp rack", gear, VM + "AmpRack.obj", (13.2, STAGE_Y, 9.5), yaw=270)
    s.prop("Power distro", gear, VM + "PowerDistro.obj", (14.6, STAGE_Y, 7.6), yaw=270)
    for x, z, yaw in [(12.0, 6.0, 10), (13.4, 4.6, -20), (14.8, 10.8, 90)]:
        s.prop("Flight case", gear, VM + "FlightCaseWide.obj", (x, STAGE_Y, z), yaw=yaw)
    s.prop("Cable coil", gear, VM + "CableCoil.obj", (6.5, STAGE_Y, 6.0), yaw=40)
    s.prop("Cable", gear, VM + "CableA.obj", (-2.6, STAGE_Y + 0.01, 3.6), yaw=70)
    s.prop("Cable", gear, VM + "CableB.obj", (2.8, STAGE_Y + 0.01, 3.4), yaw=-60)
    # The shared house kit: hardware cases behind the riser, a towel on the throne side.
    s.prop("Hardware case", gear, VM + "RoadCase.obj", (-2.4, RISER_Y, 9.0), yaw=8)
    box("Drummer towel", gear, (2.0, RISER_Y + 0.86, 8.94), (0.55, 0.03, 0.32), (0.12, 0.12, 0.13), rot=(0, 20, 0))
    s.prop("Water bottle", gear, VM + "Bottle.obj", (1.7, RISER_Y, 8.4))
    s.prop("Water bottle", gear, VM + "Bottle.obj", (1.85, RISER_Y, 8.5))
    # Stage-left steps down to the floor and a ramp up from the right.
    for k in range(6):
        slab("Wing step", stage, -16.2, -14.6, 0, STAGE_Y * (k + 1) / 6, -0.6 - (5 - k) * 0.32, -0.28 - (5 - k) * 0.32,
             STEEL_DK)

    # ------------------------------------------------------------------------------------------
    # The changeover wing: stage left, open to the house, lit by work tubes.
    slab("Wing deck", wing, WING_X0, WING_X1, 0, STAGE_Y, 0, 12.4, (0.075, 0.07, 0.065))
    slab("Wing skirt", wing, WING_X0, WING_X1, 0, STAGE_Y - 0.02, -0.05, 0.0, BLACK)
    textured("Wing edge stripe", wing, ((WING_X0 + WING_X1) / 2, STAGE_Y + 0.01, 0.15), (WING_X1 - WING_X0, 0.02, 0.25),
             "Hazard", tiling=(10, 1))
    slab("Wing drape", wing, WING_X0 - 0.1, WING_X0, STAGE_Y, 10.5, 1.0, 12.4, (0.03, 0.03, 0.035))
    for z in (3.2, 8.4):
        box("Work-light pipe", wing, ((WING_X0 + WING_X1) / 2, 6.2, z), (6.8, 0.08, 0.08), STEEL_LT, shadows=False)
        for x in (-15.6, -12.4):
            box("Tube fitting", wing, (x, 6.05, z), (1.5, 0.12, 0.22), STEEL_DK, shadows=False)
            box("Tube", wing, (x, 5.97, z), (1.4, 0.05, 0.08), ICE, emissive=(0.85, 0.92, 1.0), emissive_intensity=5,
                shadows=False)
        chain("Pipe chain", wing, (-13.7, 17.4 - 0.65, z), 17.4 - 0.65 - 6.25)
    # Cases: the tour's stacks along the drape and the back.
    cases = [(-16.2, 11.4, 0, 2), (-14.9, 11.5, 4, 3), (-13.5, 11.4, -3, 2), (-12.1, 11.6, 2, 1),
             (-16.3, 9.8, 90, 2), (-16.3, 8.4, 92, 1)]
    for x, z, yaw, n in cases:
        for k in range(n):
            s.prop("Road case", wing, VM + "RoadCase.obj", (x, STAGE_Y + k * 0.85, z), yaw=yaw + k * 3)
    for x, z, yaw in [(-15.0, 10.0, 0), (-13.0, 10.1, 4)]:
        s.prop("Wide case", wing, VM + "FlightCaseWide.obj", (x, STAGE_Y, z), yaw=yaw)
    s.prop("Wing tool chest", wing, VM + "ToolChest.obj", (-16.3, STAGE_Y, 6.2), yaw=90)
    s.prop("Wing ladder", wing, VM + "Ladder.obj", (-16.7, STAGE_Y, 4.6), yaw=90)
    s.prop("Wing power", wing, VM + "PowerDistro.obj", (-16.4, STAGE_Y, 2.4), yaw=90)
    s.prop("Wing wedge", wing, VM + "Wedge.obj", (-11.0, STAGE_Y, 2.6), yaw=-110, scale=1.1)
    # The changeover board, angled to the house.
    bg = s.group("Changeover board", wing, (-14.6, STAGE_Y, 3.2))
    bg.components[0]["Rotation"] = [0.0, 32.0, 0.0]
    for dx in (-0.8, 0.8):
        box("Easel leg", bg, (dx, 1.0, 0.1), (0.06, 2.0, 0.06), STEEL_DK)
    textured("Board", bg, (0, 1.75, 0), (2.2, 1.5, 0.05), "ChangeoverBoard")
    # "Halfway through the night, the crew stops clearing the wing": the clearing kit until
    # sheet three lands.
    clearing = s.story("Crew still clearing the wing", wing, "sheet_three", when_set=False, pos=(-12.6, STAGE_Y, 5.6))
    s.prop("Case on the dolly", clearing, VM + "FlightCaseWide.obj", (0.2, 0.12, 0), yaw=95)
    slab("Dolly", clearing, -0.5, 0.9, 0.0, 0.12, -0.7, 0.7, (0.2, 0.2, 0.22))
    sign = s.group("KEEP CLEAR sign", clearing, (1.2, 0, -2.2))
    for dz in (-0.25, 0.25):
        box("A-frame", sign, (0, 0.55, dz), (0.7, 1.1, 0.04), YELLOW, rot=(dz * 40, 0, 0))
    textured("Sign stripes", sign, (0, 0.86, -0.29), (0.66, 0.3, 0.02), "Hazard", rot=(-10, 0, 0))
    stools = s.story("The bands pull up stools", wing, "sheet_three", pos=(-13.0, STAGE_Y, 5.0))
    for x, z, yaw in [(0, 0, 0), (-1.2, 1.4, 30), (0.3, 2.8, -10)]:
        s.prop("Stool", stools, VM + "Stool.obj", (x, 0, z), yaw=yaw)
    s.prop("Cooler", stools, VM + "Cooler.obj", (-1.6, 0, -0.9), yaw=20)
    for k in range(3):
        s.prop("Can", stools, VM + "BeerCup.obj", (-1.75 + k * 0.12, 0.45, -0.9))

    # ------------------------------------------------------------------------------------------
    # The story.
    sheet_x = (-3.05, -2.5, -1.95, -1.4, -0.85)
    sheet_flags = ("sheet_one", "sheet_two", "sheet_three", "sheet_four", "case_faces_house")
    lamp_x = (-8.0, -4.0, 0.0, 4.0, 8.0)
    lamps = s.group("Act lamps (always hung)", story)
    for x in lamp_x:
        box("Lamp drop rod", lamps, (x, 12.75, 0.0), (0.05, 0.6, 0.05), STEEL_DK, shadows=False)
        box("Lamp shade", lamps, (x, 12.3, 0.0), (0.95, 0.32, 0.95), (0.12, 0.17, 0.22), shape="Cylinder", metallic=0.5)
        box("Lamp cage", lamps, (x, 12.0, 0.0), (0.55, 0.3, 0.55), (0.08, 0.08, 0.09), shape="Sphere", shadows=False)
    for i, (flag, x, lx_) in enumerate(zip(sheet_flags, sheet_x, lamp_x)):
        g = s.story(f"Sheet {i + 1}", story, flag, pos=(x, STAGE_Y + 0.35, 5.14))
        textured("Set sheet", g, (0, 0, 0), (0.46, 0.62, 0.01), f"Sheet{i + 1}", rot=(0, 0, (-4, 3, -2, 5, -3)[i]))
        lamp = s.story(f"Act lamp {i + 1}", story, flag, fade=0.4, pos=(lx_, 12.0, 0.0))
        box("Lamp glow", lamp, (0, 0, 0), (0.48, 0.26, 0.48), AMBER, shape="Sphere", emissive=AMBER,
            emissive_intensity=9, shadows=False)
        box("Lamp disc", lamp, (0, 0.13, 0), (0.86, 0.02, 0.86), AMBER, shape="Cylinder", emissive=AMBER,
            emissive_intensity=3, shadows=False)
        s.light("Act lamp", lamp, (0, -0.3, -0.2), "Point", AMBER, 260, 9)
    # A roll of tape on the wing monitor, from sheet three.
    tape = s.story("Roll of tape on the wing monitor", wing, "sheet_three", pos=(-11.0, STAGE_Y + 0.44, 2.6))
    cyl("Gaffer roll", tape, (0, 0.03, 0), 0.07, 0.05, (0.15, 0.15, 0.16))
    cyl("Gaffer core", tape, (0, 0.031, 0), 0.04, 0.052, (0.7, 0.62, 0.45))
    # The work lamp and the road case, from sheet four.
    work = s.story("Work lamp beyond the fourth sheet", story, "sheet_four", pos=(-10.0, STAGE_Y, 4.9))
    for k in range(3):
        a = math.radians(k * 120 + 20)
        tilt = math.degrees(math.atan2(0.5, 2.0))
        box("Tripod leg", work, (0.25 * math.cos(a), 1.0, 0.25 * math.sin(a)), (0.045, 2.05, 0.045), YELLOW,
            rot=(-tilt * math.sin(a), 0, tilt * math.cos(a)))
    box("Lamp mast", work, (0, 2.2, 0), (0.05, 0.6, 0.05), STEEL_DK)
    head = s.group("Lamp heads", work, (0, 2.55, 0))
    head.components[0]["Rotation"] = look_rotation((-10.0, 4.15, 4.9), (-8.6, 2.1, 6.7))
    for dx in (-0.28, 0.28):
        box("Lamp housing", head, (dx, 0, 0), (0.46, 0.36, 0.2), YELLOW)
        box("Lamp lens", head, (dx, 0, 0.105), (0.38, 0.28, 0.02), (1.0, 0.9, 0.7), emissive=(1.0, 0.85, 0.6),
            emissive_intensity=10, shadows=False)
    s.light("Work lamp", work, (0.0, 2.6, 0.3), "Spot", (1.0, 0.86, 0.66), 520, 12,
            rot=look_rotation((-10.0, 4.2, 5.2), (-8.6, 2.0, 6.8)), inner=24, outer=48)
    s.light("Work lamp spill", work, (0.4, 2.3, 0.6), "Point", (1.0, 0.8, 0.55), 40, 5)
    case_pos = (-8.6, STAGE_Y, 6.8)

    def road_case(parent, facing):
        """The big drum case. facing True: the stencilled lid faces the house (-z)."""
        g = s.group("Stencilled road case", parent, (0, 0, 0))
        g.components[0]["Rotation"] = [0.0, 0.0 if facing else 180.0, 0.0]
        box("Case body", g, (0, 0.62, 0), (1.7, 1.06, 1.0), (0.04, 0.04, 0.045), rough=0.6)
        for y in (0.1, 1.15):
            box("Edge extrusion", g, (0, y, 0), (1.74, 0.05, 1.04), (0.6, 0.62, 0.65), metallic=0.8, rough=0.35)
        for x in (-0.86, 0.86):
            for z in (-0.5, 0.5):
                box("Corner", g, (x, 0.62, z), (0.06, 1.1, 0.06), (0.6, 0.62, 0.65), metallic=0.8, rough=0.35)
        for x in (-0.6, 0.6):
            cyl("Caster", g, (x, 0.05, 0.3), 0.06, 0.05, BLACK, axis="x")
            cyl("Caster", g, (x, 0.05, -0.3), 0.06, 0.05, BLACK, axis="x")
        textured("Stencil lid", g, (0, 0.63, -0.505), (1.6, 1.0, 0.01), "CaseStencil")
        for x in (-0.5, 0.5):
            box("Handle", g, (x, 0.85, 0.51), (0.3, 0.08, 0.04), (0.5, 0.5, 0.52), metallic=0.7)
            box("Latch", g, (x, 0.35, 0.51), (0.12, 0.12, 0.03), (0.6, 0.62, 0.65), metallic=0.8)
        return g

    turned_away = s.story("Case under the lamp (turned away)", work, "case_faces_house", when_set=False,
                          fade=0.6, pos=(case_pos[0] + 10.0, 0, case_pos[2] - 4.9))
    road_case(turned_away, False)
    faces = s.story("The case turns to the house", story, "case_faces_house", fade=0.9, pos=case_pos)
    road_case(faces, True)
    s.light("Name in the light", faces, (0.3, 2.4, -2.2), "Spot", (1.0, 0.88, 0.7), 260, 7,
            rot=look_rotation((-8.3, 4.0, 4.6), (-8.6, 2.2, 6.3)), inner=16, outer=34)

    # People: the acts who stay to watch, the crew chief, the singers at the end.
    cast = s.group("Bands in the wing", wing)
    wing_y = STAGE_Y
    a2 = s.story("Opener's bass stays (song 2)", cast, "sheet_two", pos=(-11.8, wing_y, 4.2))
    people.figure(s, a2, "Act 1 bass, towel round the neck", "Mother_01", "01_C", (0, 0, 0), 112, "WingNod", 0.95,
                  towel=(0.85, 0.85, 0.82))
    s.prop("Act 1 bass case", a2, VM + "FlightCaseWide.obj", (-1.6, 0, 1.0), yaw=70)
    a3 = s.story("First two acts watch (song 3)", cast, "sheet_three", pos=(-12.4, wing_y, 6.4))
    people.figure(s, a3, "Act 1 guitar", "Daughter_01", "02_A", (-0.4, 0, -0.6), 100, "WingSway", 1.0)
    people.figure(s, a3, "Act 2 bass", "Son_01", "02_B", (0.4, 0.75, -1.4), 96, "WingNod", 1.05)
    people.figure(s, a3, "Act 2 guitar", "Mother_02", "02_C", (1.0, 0, 1.0), 118, "WingNod", 0.9)
    a3v = s.story("Singers 1 and 2 in the wing until the end", a3, "case_faces_house", when_set=False, pos=(0, 0, 0))
    people.figure(s, a3v, "Act 1 vocals", "ShopKeeper_01", "02_B", (-1.4, 0, 1.6), 106, "WingSway", 0.85)
    people.figure(s, a3v, "Act 2 vocals", "SchoolGirl_01", "03_A", (0.0, 0, 2.4), 125, "WingNod", 1.1)
    a4 = s.story("Act 3 joins the wing (song 4)", cast, "sheet_four", pos=(-14.2, wing_y, 7.6))
    people.figure(s, a4, "Act 3 bass", "Daughter_01", "03_A", (0, 0, 0), 95, "WingNod", 1.0)
    people.figure(s, a4, "Act 3 guitar", "ShopKeeper_01", "03_B", (-0.8, 0, -1.6), 105, "WingSway", 0.9)
    a4v = s.story("Singer 3 in the wing until the end", a4, "case_faces_house", when_set=False, pos=(0, 0, 0))
    people.figure(s, a4v, "Act 3 vocals", "SchoolBoy_01", "03_C", (0.9, 0, 1.2), 100, "WingNod", 1.15)
    chief = s.story("Crew chief by the case", story, "sheet_four", pos=(-9.9, STAGE_Y, 7.9))
    people.figure(s, chief, "Mill crew chief", "ShopKeeper_01", "04_C", (0, 0, 0), 150, "Point", 1.0)
    a5 = s.story("Act 4 in the wing (song 5)", cast, "case_faces_house", pos=(-13.6, wing_y, 3.0))
    people.figure(s, a5, "Act 4 bass", "Mother_02", "03_C", (0, 0, 0), 100, "WingNod", 1.0)
    people.figure(s, a5, "Act 4 guitar", "SchoolGirl_01", "04_A", (0.6, 0, -1.2), 110, "HornsUp", 0.95)
    singers = s.story("Four singers come out beside the sheets", story, "case_faces_house", fade=1.2,
                      pos=(-6.8, STAGE_Y, 5.7))
    for k, (body, atlas, pose) in enumerate([("ShopKeeper_01", "02_B", "HornsUp"), ("SchoolGirl_01", "03_A", "Wave"),
                                             ("SchoolBoy_01", "03_C", "HornsUp"), ("Rigged", "04_B", "Wave")]):
        people.figure(s, singers, f"Act {k + 1} vocals", body, atlas, (-1.6 + k * 0.95, 0, 0.25 * (k % 2)), 180 + (k - 1.5) * 8,
                      pose, 0.9 + 0.07 * k)

    # ------------------------------------------------------------------------------------------
    # Lights. One shadowed directional (the moon through the skylights), the show rig (40 max),
    # and plain practicals.
    def spot(name, pos, to, color, power, reach, inner, outer, role=None, group=0):
        return s.light(name, lights, pos, "Spot", color, power, reach, rot=look_rotation(pos, to), inner=inner,
                       outer=outer, show=role, group=group)

    def point(name, pos, color, power, reach, role=None, group=0):
        return s.light(name, lights, pos, "Point", color, power, reach, show=role, group=group)

    s.light("Moon through the skylights", lights, (0, 30, 0), "Directional", (0.50, 0.62, 1.0), 0.9,
            rot=(58, -28, 0), shadows=True, show="Static")
    # Washes from the front truss, orange and steel-blue.
    for i, x in enumerate((-9.0, -6.5, -4.0, -1.5, 1.5, 4.0, 6.5, 9.0)):
        col = ORANGE if i % 2 == 0 else BLUE
        spot(f"Front wash {i + 1}", (x, 10.2, 3.2), (x * 0.6, STAGE_Y, 5.0), col, 4200, 20, 22, 40, "Wash", i % 3)
    # Beams: four from the stage floor behind the band into the haze, four from the back truss.
    for i, x in enumerate((-8.5, -3.0, 3.0, 8.5)):
        spot(f"Floor beam {i + 1}", (x, STAGE_Y + 0.3, 11.5), (x * 2.2, 18.0, -30.0), ORANGE if i % 2 else BLUE,
             16000, 60, 3, 6, "Beam", i % 2)
    for i, x in enumerate((-7.0, -2.5, 2.5, 7.0)):
        spot(f"Truss beam {i + 1}", (x, 11.2, 9.4), (x * 1.8, 0.0, -14.0), BLUE if i % 2 else ORANGE,
             14000, 50, 3, 6, "Beam", (i + 1) % 2)
    # Follow spots from the pit crane.
    for i, x in enumerate((-4.0, -1.5, 1.5, 4.0)):
        spot(f"Follow spot {i + 1}", (x, 15.6, -15.2), (0, 2.5, 6.0), (1.0, 0.95, 0.9), 26000, 45, 3, 6, "Spot", i)
    # Blinders on the portal header, strobes on the trusses and the pit crane.
    for i, x in enumerate((-7.0, -2.5, 2.5, 7.0)):
        spot(f"Blinder {i + 1}", (x, 13.0, -0.4), (x * 1.4, 1.5, -14.0), AMBER, 2600, 30, 30, 55, "Blinder", i % 2)
        box("Blinder face", lights, (x, 13.0, -0.25), (0.9, 0.45, 0.2), (0.08, 0.08, 0.09))
    for i, (x, y, z) in enumerate([(-6.0, 10.2, 3.0), (0.0, 10.2, 3.0), (6.0, 10.2, 3.0),
                                   (-12.0, 16.0, -16.8), (0.0, 16.0, -16.8), (12.0, 16.0, -16.8)]):
        point(f"Strobe {i + 1}", (x, y - 0.4, z), (0.9, 0.95, 1.0), 2200, 26, "Strobe", i % 2)
        box("Strobe face", lights, (x, y - 0.25, z), (0.7, 0.2, 0.25), (0.1, 0.1, 0.11), shadows=False)
    # Uplights on the mill (static show lights would count; these are plain).
    for x in (-24.5, 24.5):
        for z in (-32.0, -12.0, 8.0):
            spot("Column uplight", (x, 0.4, z - 1.2), (x, 18.0, z - 0.4), BLUE if z != -12.0 else ORANGE, 3600, 24, 8, 22)
    spot("Drop wash", (0, STAGE_Y + 0.2, 11.0), (0, 9.0, 12.3), (0.45, 0.55, 0.9), 900, 14, 30, 60)
    point("Wing tubes 1", (-13.8, 5.7, 3.2), (0.78, 0.86, 1.0), 520, 11)
    point("Wing tubes 2", (-13.8, 5.7, 8.4), (0.78, 0.86, 1.0), 520, 11)
    spot("Wing worklight", (-11.2, 6.0, -1.0), (-14.0, STAGE_Y, 6.5), (1.0, 0.8, 0.55), 1400, 16, 30, 55)
    # High-bay sodium lamps under the trusses: the mill's own light, low and orange.
    for z in (-36.0, -24.0, -12.0):
        for x in (-12.0, 12.0):
            box("High-bay lamp", lights, (x, 20.9, z), (0.9, 0.5, 0.9), (0.1, 0.1, 0.1), shape="Cylinder", shadows=False)
            box("High-bay glass", lights, (x, 20.6, z), (0.7, 0.12, 0.7), AMBER, shape="Cylinder", emissive=(1.0, 0.55, 0.2),
                emissive_intensity=6, shadows=False)
            point("High-bay", (x, 20.2, z), (1.0, 0.55, 0.25), 700, 22)
    point("House fill over the floor", (0, 14.0, -22.0), (0.35, 0.45, 0.7), 3200, 42)
    point("House fill over the pit", (0, 12.0, -8.0), (0.45, 0.5, 0.75), 1200, 22)
    point("Catwalk caged lamp", (-24.0, 8.0, -21.0), AMBER, 120, 10)
    point("Exit glow", (-14.0, 3.0, -45.5), (0.1, 1.0, 0.35), 25, 5)

    # ------------------------------------------------------------------------------------------
    # Markers.
    s.info(marks, TITLE, "Drumsmith", outdoor=False, room_back=-47, room_ceiling=24, half_width=27, desk_z=-26,
           ambient=(0.010, 0.013, 0.02), fog_color=(0.030, 0.040, 0.062), haze=1.2)
    s.spot(marks, "Drummer", (0.0, RISER_Y, 7.6))
    s.spot(marks, "Guitar", (-4.8, STAGE_Y, 3.4), yaw=-6)
    s.spot(marks, "Bass", (4.8, STAGE_Y, 3.6), yaw=6)
    s.spot(marks, "Vocals", (0.0, STAGE_Y, 1.8))
    pit = s.crowd("Mosh pit", marks, (0, 0, -4.0), 18, 3.6, 96, figures="Posed")
    pit.components[-1]["DanceFloor"] = True
    s.crowd("Pit edge left", marks, (-12.5, 0, -6.2), 5.0, 6.0, 26, 0.6)
    s.crowd("Pit edge right", marks, (12.0, 0, -6.2), 5.0, 6.0, 26, 0.6)
    s.crowd("Floor", marks, (0, 0, -14.0), 33, 12.0, 330, 0.55)
    s.crowd("Back floor left", marks, (-10.8, 0, -25.0), 12.6, 10.0, 110, 0.6)
    s.crowd("Back floor right", marks, (10.8, 0, -25.0), 12.6, 10.0, 110, 0.6)
    s.crowd("Behind the desk", marks, (0, 0, -32.5), 34, 5.0, 120, 0.7)
    s.crowd("On the catwalk", marks, (-25.0, cw_y, -21.0), 2.6, 30.0, 32, 0.4, yaw=0)
    # FOH riser in the gap.
    foh = s.group("Front of house", stage, (0, 0, -26.0))
    slab("FOH riser", foh, -4.2, 4.2, 0, 0.6, -2.4, 2.4, STEEL_DK)
    box("Desk", foh, (0, 1.05, 0.3), (3.0, 0.9, 1.2), (0.08, 0.08, 0.09))
    box("Desk faders", foh, (0, 1.52, 0.3), (2.8, 0.06, 1.0), (0.2, 0.25, 0.3), emissive=(0.1, 0.25, 0.5),
        emissive_intensity=1.5, shadows=False)
    for x in (-4.0, 4.0):
        for z in (-2.2, 2.2):
            box("FOH pole", foh, (x, 2.0, z), (0.1, 4.0, 0.1), (0.55, 0.56, 0.58), metallic=0.7, shadows=False)
    box("FOH roof", foh, (0, 4.05, 0), (8.4, 0.12, 4.8), BLACK)
    # Cameras.
    cams = s.group("Camera positions", marks)
    for tag, kind, eye, aim, fov in [
        ("mill-wide", "Wide", (-2.0, 7.5, -24.0), (-2.0, 5.2, 6.0), 50),
        ("crane-over-the-pit", "Crane", (13.0, 13.0, -13.0), (-3.0, 3.0, 6.0), 56),
        ("foh-long-lens", "Desk", (0.6, 4.4, -25.0), (-1.5, 3.4, 6.0), 26),
        ("the-sheets-and-the-case", "Custom", (-3.0, 3.6, -1.2), (-5.4, 2.4, 6.0), 55),
        ("from-the-wing", "Custom", (-15.6, 3.6, 1.0), (-1.0, 2.8, 7.0), 52),
        ("the-wing-from-the-house", "Custom", (-15.5, 4.2, -6.5), (-13.0, 2.6, 6.5), 50),
        ("catwalk", "Custom", (-24.0, 8.2, -24.0), (-2.0, 4.0, 4.0), 46),
        ("ladle-and-girders", "Custom", (9.0, 2.2, -30.0), (2.0, 8.0, -8.0), 58),
        ("kit-close", "Close", (2.2, 3.6, 3.6), (0.0, 2.9, 7.4), 46),
    ]:
        s.camera_spot(tag, cams, eye, aim, kind, fov, tag)
    # Arrival: in through the big door, under the ladle, to the barricade.
    for i, (eye, aim, fov) in enumerate([
            ((8.0, 1.7, -44.5), (6.0, 3.0, -30.0), 64), ((7.0, 1.7, -40.0), (4.0, 5.5, -18.0), 62),
            ((5.5, 1.75, -34.0), (4.5, 8.0, -16.0), 60), ((4.0, 1.75, -27.0), (1.0, 4.0, 2.0), 58),
            ((2.5, 1.8, -19.0), (-2.0, 3.0, 6.0), 56), ((1.0, 1.85, -10.0), (-1.0, 3.0, 6.0), 54)]):
        s.camera_spot(f"Arrival {i + 1:02}", cams, eye, aim, "Custom", fov, f"arrival/{i + 1:02}")
    return s


def write_readme(folder):
    text = """# StorySteelMill models: provenance

The people are the crowd's low pieces (`Assets/Models/People/Crowd/<Body>/*_Lo.obj`, generated by
`Game/Tools/MakeCrowdPieces.py` from the owner's Synty Polygon Town characters), copied into
`People/<Body>_<atlas>/` with a `.mtl` that binds the manifest's clothing atlas
(`Assets/Models/Venue/PolygonTown_<atlas>.png`, referenced in place). Licence: the owner's Synty
licence. Written by `Tools/Venues/story_steel_mill_people.py`; no geometry is changed.

Everything else in the venue is engine primitives or models referenced in place from
`Assets/Models/Venue/` (see that folder's README).
"""
    path = os.path.join(folder, "Models", "README.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="\n") as f:
        f.write(text)


def main():
    folder = os.path.join(repo_root(), "Assets", "Venues", VID)
    scene = build()
    scene.write(os.path.join(folder, VID + ".lvl"))
    write_readme(folder)
    preview = "Preview.jpg" if os.path.exists(os.path.join(folder, "Preview.jpg")) else None
    write_venue_json(folder, TITLE, VID + ".lvl", preview=preview, ambience="Assets/Sounds/crowd.mp3")
    print(f"{len(scene.entities)} entities in {VID}")


if __name__ == "__main__":
    main()
