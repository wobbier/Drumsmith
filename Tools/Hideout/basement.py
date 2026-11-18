"""The broke-drummer basement, the hideout's first room (Assets/Hideout/Basement.lvl).

Unfinished concrete block, open joists with pink insulation, a duct and copper pipe, the stairs
up to the kitchen, a window well with the streetlight coming through it and dust in the beam.
The kit (and the player's drummer, playing along with the radio) on a carpet offcut in front of
egg cartons and a spray-painted bedsheet; Christmas lights chasing the beat along the back wall.
A couch with the cat asleep on it, the boombox above it pumping, a CRT showing static, the
furnace with its pilot light. The workbench with a dying fluorescent tube and a desk lamp, the
gig board, posters for bands that don't exist. Bucket drums from before there was a kit.

Room space: x across (+x the couch side), y up, z from the stairs (the camera) to the back wall.
"""
import math
import random

from hideoutgen import (sound, BLACK, BRASS, CHROME, CORK, GOLD, OFFWHITE, STEEL, WHITE, WOOD, Scene, drummer, dust, glow_light,
                        light, motion, poster, rod, slot, station, textured, view)

H = 3.2        # half the width
D = 6.0        # the back wall's face
TOP = 2.35     # the subfloor overhead
JOIST = 2.15   # the joists' undersides

PLASTIC_RED = (0.62, 0.08, 0.07)
PLASTIC_BLUE = (0.08, 0.2, 0.55)
COPPER = (0.72, 0.42, 0.25)
ORANGE = (0.95, 0.42, 0.08)
PINK = (0.6, 0.4, 0.43)
BULB_COLOURS = [(1.0, 0.12, 0.08), (0.1, 0.9, 0.2), (0.15, 0.35, 1.0), (1.0, 0.65, 0.08), (1.0, 0.25, 0.7)]


def shell(s, geo):
    # Slab and block walls; the front wall stands either side of the stairs' opening.
    textured(s.slab("Floor", geo, -H, H, -0.1, 0.0, -1.6, D, (1, 1, 1), rough=0.92), "ConcreteFloor", (3.2, 3.8))
    textured(s.slab("Back Wall", geo, -H, H, 0.0, TOP, D, D + 0.12, (1, 1, 1), rough=0.95), "ConcreteBlock", (4.0, 2.94))
    for name, x0, x1 in (("Left Wall", -H - 0.12, -H), ("Right Wall", H, H + 0.12)):
        textured(s.slab(name, geo, x0, x1, 0.0, TOP, -1.6, D, (1, 1, 1), rough=0.95), "ConcreteBlock", (4.75, 2.94))
    textured(s.slab("Front Wall", geo, -2.2, H, 0.0, TOP, -1.72, -1.6, (1, 1, 1), rough=0.95), "ConcreteBlock", (3.4, 2.94))
    # Overhead: the subfloor, joists every 40 cm, insulation in some bays (one batt sagging).
    # The subfloor casts shadows: it's what keeps the sky (the engine's sun, when a scene has no
    # directional of its own) out; through the joists alone it falls in stripes.
    textured(s.slab("Subfloor", geo, -H, H, TOP, TOP + 0.04, -1.6, D, (1, 1, 1), rough=0.9), "Plywood", (4, 4), tint=(0.45, 0.4, 0.36))
    rnd = random.Random(7)
    z = -1.4
    bay = 0
    while z < D:
        textured(s.slab(f"Joist {bay}", geo, -H, H, JOIST, TOP, z - 0.025, z + 0.025, (1, 1, 1), rough=0.85), "Wood", (8, 0.4), tint=(0.62, 0.56, 0.5))
        if z + 0.4 < D and rnd.random() < 0.55:
            sag = 6.0 if rnd.random() < 0.15 else 0.0
            s.box(f"Insulation {bay}", geo, (0.0, TOP - 0.045 - (0.03 if sag else 0.0), z + 0.2), (2 * H - 0.1, 0.07, 0.33), PINK,
                  rot=(sag, 0, 0), rough=1.0, shadows=False)
        z += 0.4
        bay += 1
    # The duct from the furnace to the front, the copper and the wiring.
    s.slab("Duct", geo, 1.75, 2.07, 1.93, 2.15, -1.6, 5.3, (0.62, 0.63, 0.66), metallic=0.85, rough=0.35)
    s.slab("Duct Elbow", geo, 1.75, 2.9, 1.93, 2.15, 5.15, 5.45, (0.62, 0.63, 0.66), metallic=0.85, rough=0.35)
    for i, x in enumerate((-0.92, -0.84)):
        rod(s, geo, f"Copper Pipe {i}", (x, 2.1, -1.6), (x, 2.1, D), 0.022, COPPER, metallic=0.85, rough=0.3)
    rod(s, geo, "Cable Run", (0.42, 2.13, -1.6), (0.42, 2.13, D), 0.012, BLACK)
    s.box("Junction Box", geo, (0.42, 2.09, 2.4), (0.1, 0.06, 0.1), STEEL, metallic=0.6)
    # The steel post holding the house up, rust at its foot.
    rod(s, geo, "Lally Column", (-1.65, 0.0, 2.65), (-1.65, JOIST, 2.65), 0.09, (0.5, 0.14, 0.1), metallic=0.5, rough=0.5)
    s.box("Column Foot", geo, (-1.65, 0.01, 2.65), (0.2, 0.02, 0.2), (0.28, 0.16, 0.1), metallic=0.4, rough=0.8)
    s.box("Column Cap", geo, (-1.65, JOIST - 0.01, 2.65), (0.2, 0.02, 0.2), STEEL, metallic=0.6)
    # A floor drain and an old oil stain.
    s.box("Drain", geo, (0.95, 0.002, 2.9), (0.18, 0.004, 0.18), (0.05, 0.05, 0.05), shape="Cylinder", metallic=0.6, rough=0.4,
          shadows=False)


def stairs(s, geo, items):
    """Open wooden stairs up to the kitchen, by the camera, with the light from upstairs."""
    for i in range(11):
        y = 0.2 * (i + 1)
        z = 1.62 - 0.27 * i
        textured(s.box(f"Tread {i}", geo, (-2.7, y - 0.02, z), (0.9, 0.04, 0.28), (1, 1, 1), rough=0.8), "WoodDark", (1, 0.3))
    for x in (-3.13, -2.27):
        textured(s.box(f"Stringer {x}", geo, (x, 1.1, 0.27), (0.05, 0.25, 3.35), (1, 1, 1), rot=(-36.5, 0, 0)), "WoodDark", (0.2, 3))
    rod(s, geo, "Handrail", (-2.22, 0.95, 1.85), (-2.22, 2.12, 0.25), 0.04, (0.35, 0.22, 0.12))
    # Up there, the kitchen light (warm through the open door).
    light(s, geo, "Upstairs", (-2.7, 2.15, -1.3), color=(1.0, 0.76, 0.48), intensity=2.2, range_=3.2)
    # Under the stairs: the boxes.
    textured(s.box("Box Xmas", items, (-2.78, 0.25, 1.0), (0.5, 0.5, 0.5), (1, 1, 1), rot=(0, 8, 0), rough=0.9), "BoxXmas")
    textured(s.box("Box Moms", items, (-2.74, 0.72, 1.05), (0.46, 0.44, 0.46), (1, 1, 1), rot=(0, -6, 0), rough=0.9), "BoxMoms")
    textured(s.box("Box Cables", items, (-2.7, 0.2, 0.42), (0.42, 0.4, 0.42), (1, 1, 1), rot=(0, 15, 0), rough=0.9), "BoxCables")


def back_wall(s, geo, items, lights):
    # The bedsheet, and egg cartons stapled up round it (a few missing, one hanging off).
    poster(s, items, "Banner", "Banner", (0.0, 1.62, D - 0.012), 2.3, 1.15, "-z", tilt=-1.5)
    for x in (-1.12, 1.1):
        s.box(f"Thumbtack {x}", items, (x, 2.17, D - 0.016), (0.02, 0.02, 0.01), (0.8, 0.1, 0.1), shape="Sphere", shadows=False)
    rnd = random.Random(23)
    y = 0.72
    while y < 2.08:
        x = -2.12
        while x < 2.14:
            behind_banner = abs(x) < 1.22 and y > 0.98
            if not behind_banner and rnd.random() > 0.08:
                crooked = rnd.uniform(-2.5, 2.5) if rnd.random() > 0.05 else 14.0
                textured(s.box(f"Egg Carton {x:.2f} {y:.2f}", items, (x, y, D - 0.02), (0.3, 0.3, 0.035), (1, 1, 1),
                               rot=(0, 0, crooked), rough=1.0, shadows=False), "EggCarton")
            x += 0.31
        y += 0.31
    # Christmas lights along the top, chasing the beat: one beat in four each.
    string = s.group("Christmas Lights", lights)
    count = 28
    prev = None
    for i in range(count):
        t = i / (count - 1)
        x = -3.0 + 6.0 * t
        y = 2.08 - 0.2 * (1.0 - (2.0 * t - 1.0) ** 2) + (0.03 if i % 2 else 0.0)
        p = (x, y, D - 0.05)
        colour = BULB_COLOURS[i % len(BULB_COLOURS)]
        bulb = s.box(f"Bulb {i}", string, p, (0.05, 0.068, 0.05), colour, shape="Sphere", emissive=colour, emissive_intensity=10.0,
                     shadows=False)
        if i % 3 == 0:
            glow_light(bulb, color=colour, intensity=1.6, range_=2.4)
        motion(bulb, "Pulse", amount=0.85, speed=0.25, phase=((i % 4) + 0.5) / 4.0, music=True)
        if prev:
            rod(s, string, f"Wire {i}", prev, (p[0], p[1] + 0.02, p[2]), 0.006, (0.05, 0.18, 0.06), shadows=False)
        prev = (p[0], p[1] + 0.02, p[2])
    # The window well: the night outside, the streetlight through grimy glass, dust in the beam.
    wx, wy = 1.9, 2.0
    s.box("Window Frame", geo, (wx, wy, D - 0.03), (0.98, 0.44, 0.06), (0.32, 0.22, 0.14), rough=0.8)
    textured(s.box("Window Glass", geo, (wx, wy, D - 0.064), (0.86, 0.32, 0.01), (1, 1, 1), rough=0.15, shadows=False),
             "WindowNight", emissive=True, emissive_intensity=1.6)
    s.box("Window Bar", geo, (wx, wy, D - 0.07), (0.03, 0.32, 0.012), (0.3, 0.2, 0.12))
    eye = (wx, wy - 0.05, D - 0.18)
    target = (0.3, 0.0, 3.9)
    from hideoutgen import look_rotation
    light(s, lights, "Streetlight Through The Window", eye, kind="Spot", color=(0.6, 0.72, 1.0), intensity=40.0, range_=8.0,
          rot=look_rotation(eye, target), inner=12.0, outer=24.0, shadows=True, volumetric=7.0)
    dust(s, lights, "Dust", (0.9, 1.15, 4.4), (2.6, 2.1, 2.6), count=260, rate=36.0)
    # Now and then a car goes by up on the street: its headlights sweep the ceiling through the glass.
    car = (wx, wy + 0.05, D - 0.25)
    sweep = light(s, lights, "Passing Car", car, kind="Spot", color=(1.0, 0.95, 0.82), intensity=26.0, range_=7.0,
                  rot=look_rotation(car, (wx - 1.2, TOP, 2.6)), inner=10.0, outer=22.0, volumetric=5.0)
    motion(sweep, "Pass", amount=0.45, speed=1.0 / 23.0, axis=(1, 0, 0), phase=0.6)
    # The power strip that powers everything (and one more strip plugged into it).
    s.box("Outlet", geo, (-2.2, 0.35, D - 0.01), (0.08, 0.12, 0.02), OFFWHITE)
    s.box("Power Strip", items, (-2.0, 0.03, 5.75), (0.36, 0.04, 0.07), WHITE)
    s.box("Power Strip 2", items, (-1.55, 0.03, 5.55), (0.36, 0.04, 0.07), WHITE, rot=(0, 30, 0))
    rod(s, items, "Cord Wall", (-2.2, 0.3, D - 0.02), (-2.0, 0.02, 5.78), 0.012, BLACK)
    rod(s, items, "Cord Amp", (-1.82, 0.02, 5.72), (1.2, 0.02, 4.85), 0.012, (0.85, 0.45, 0.08))
    rod(s, items, "Cord Fan", (-1.7, 0.02, 5.5), (-1.55, 0.02, 4.75), 0.012, BLACK)
    # Posters either side.
    poster(s, items, "Poster Kick Drum Kids", "PosterKickDrumKids", (2.78, 1.72, D - 0.012), 0.42, 0.63, "-z", tilt=2.5)
    poster(s, items, "Calendar", "Calendar", (-2.62, 1.5, D - 0.012), 0.36, 0.48, "-z", tilt=-1.0)


def kit_corner(s, geo, items, stations, lights):
    drummer(s, items, (0.0, 0.0, 5.3), yaw=180.0)
    # The kick's front head with the band's name on it: Band builds the kick 0.9 m ahead of the
    # throne, its front head 0.24 m further (Kick.obj), so 4.16 here; a cut-out disc just proud of it.
    head = textured(s.box("Kick Logo", items, (0.0, 0.31, 4.148), (0.56, 0.56, 0.004), (1, 1, 1), rough=0.7, shadows=False),
                    "KickHead", emissive=True, emissive_intensity=0.25)
    head.components[-1]["Material"]["AlphaCutoff"] = 0.5
    # Somebody's guitar, leaning on the amp.
    guitar = s.entity("Guitar", items, (1.9, 0.31, 4.45), (0.0, -25.0, -78.0))
    guitar.add({"Type": "Model", "ModelPath": "Assets/Models/Instruments/Runtime/Guitar.obj"})
    station(s, stations, "Kit", "Kit", (0.0, 0.95, 4.55), (0.3, 0.7, -2.1), 42)
    # The box fan on a milk crate, blowing at the drummer.
    fan = s.group("Box Fan", items, (-1.55, 0.0, 4.75))
    s.box("Fan Crate", fan, (0.0, 0.16, 0.0), (0.34, 0.32, 0.34), PLASTIC_BLUE, rough=0.6)
    s.box("Fan Frame", fan, (0.0, 0.6, 0.0), (0.12, 0.52, 0.52), (0.82, 0.8, 0.76), rough=0.5)
    hub = s.entity("Fan Blades", fan, (0.07, 0.6, 0.0))
    motion(hub, "Spin", speed=720.0, axis=(1, 0, 0))
    for k in range(3):
        s.box(f"Blade {k}", hub, (0.0, 0.0, 0.0), (0.01, 0.42, 0.09), (0.72, 0.75, 0.8), rot=(k * 60.0, 0, 0), shadows=False)
    s.box("Fan Grille", fan, (0.075, 0.6, 0.0), (0.005, 0.46, 0.46), (0.2, 0.2, 0.2), rough=0.4, shadows=False)
    # Bucket drums: where it started.
    for i, (x, z) in enumerate(((-1.0, 3.75), (-0.62, 3.52), (-1.28, 3.38))):
        s.box(f"Bucket {i}", items, (x, 0.19, z), (0.3, 0.38, 0.3), ORANGE, shape="Cylinder", rough=0.55)
        s.box(f"Bucket Rim {i}", items, (x, 0.012, z), (0.32, 0.024, 0.32), (0.85, 0.35, 0.06), shape="Cylinder")
    rod(s, items, "Bucket Stick L", (-1.1, 0.385, 3.65), (-0.78, 0.385, 3.85), 0.014, (0.86, 0.72, 0.46))
    rod(s, items, "Bucket Stick R", (-1.05, 0.39, 3.62), (-0.74, 0.4, 3.8), 0.014, (0.86, 0.72, 0.46))
    # The setlist, taped to the floor.
    textured(s.box("Setlist", items, (0.62, 0.003, 3.72), (0.24, 0.002, 0.34), (1, 1, 1), rot=(0, -12, 0), shadows=False), "Setlist")
    # The amp the settings live in, its power light on.
    amp = (1.45, 0.0, 4.65)
    s.box("Amp", stations, (amp[0], 0.32, amp[2]), (0.62, 0.64, 0.32), (0.07, 0.07, 0.07), rough=0.6)
    s.box("Amp Grille", stations, (amp[0], 0.28, amp[2] - 0.165), (0.55, 0.45, 0.01), (0.16, 0.14, 0.12), rough=0.95)
    s.box("Amp Panel", stations, (amp[0], 0.57, amp[2] - 0.165), (0.55, 0.06, 0.01), (0.7, 0.6, 0.4), metallic=0.6, rough=0.3)
    s.box("Amp Light", stations, (amp[0] + 0.22, 0.57, amp[2] - 0.172), (0.016, 0.016, 0.006), (1, 0.1, 0.05), shape="Sphere",
          emissive=(1.0, 0.1, 0.05), emissive_intensity=8.0, shadows=False)
    station(s, stations, "Mixer", "Mixer", (amp[0], 0.45, amp[2]), (-0.5, 0.65, -1.4), 45, label="SETTINGS")
    # The bare bulb over the kit, swinging a little on its cord (the fan).
    pivot = s.entity("Bulb Pivot", lights, (0.85, JOIST, 3.65))
    motion(pivot, "Sway", amount=5.0, speed=0.33, axis=(1, 0, 0.35))
    rod(s, pivot, "Bulb Cord", (0.0, 0.0, 0.0), (0.0, -0.36, 0.0), 0.01, BLACK, shadows=False)
    s.box("Bulb Socket", pivot, (0.0, -0.39, 0.0), (0.05, 0.07, 0.05), (0.15, 0.13, 0.1), shape="Cylinder")
    bulb = s.box("Bare Bulb", pivot, (0.0, -0.46, 0.0), (0.07, 0.09, 0.07), (1.0, 0.85, 0.6), shape="Sphere",
                 emissive=(1.0, 0.78, 0.45), emissive_intensity=14.0, shadows=False)
    glow_light(bulb, color=(1.0, 0.72, 0.42), intensity=10.0, range_=6.5, shadows=True, volumetric=1.0)
    rod(s, pivot, "Pull Chain", (0.03, -0.42, 0.0), (0.03, -0.75, 0.0), 0.004, BRASS, metallic=0.9, shadows=False)


def camcorder(s, items, lights):
    """Mom's camcorder on its tripod at the front of the kit, filming practice for the TV."""
    from hideoutgen import look_rotation
    base = (-0.95, 0.0, 3.05)
    s.prop("Tripod", items, "Assets/Models/Venue/CameraTripod.obj", base, yaw=30.0, scale=0.82)
    lens = (base[0] + 0.02, 1.32, base[2] + 0.05)
    target = (0.0, 0.95, 5.15)
    rig = s.entity("Camcorder", items, lens, look_rotation(lens, target))
    s.box("Camcorder Body", rig, (0.0, 0.0, -0.08), (0.09, 0.11, 0.2), (0.12, 0.12, 0.13), rough=0.4)
    s.box("Camcorder Lens", rig, (0.0, 0.0, 0.04), (0.06, 0.05, 0.06), (0.05, 0.05, 0.06), rot=(90, 0, 0), shape="Cylinder", metallic=0.4)
    rec = s.box("Rec Light", rig, (0.03, 0.06, 0.0), (0.012, 0.012, 0.012), (1, 0.05, 0.05), shape="Sphere",
                emissive=(1.0, 0.05, 0.05), emissive_intensity=10.0, shadows=False)
    motion(rec, "Blink", amount=0.5, speed=1.0)
    eye = s.entity("Camcorder View", lights, lens, look_rotation(lens, target))
    eye.add({"Type": "Camera", "IsCurrent": False, "TargetTexture": "Assets/Hideout/Camcorder.rendertexture", "UpdateInterval": 4,
             "FieldOfView": 40.0, "Near": 0.05, "Far": 14.0, "ClearType": "Color", "ClearColor": [0.02, 0.02, 0.02],
             "AmbientOcclusion": False, "VolumetricFog": False, "SunShadows": False})


def couch_corner(s, geo, items, stations, lights):
    # The couch, against the wall, facing the room; the cat asleep at the near end.
    s.prop("Couch", items, "Assets/Venues/Backyard/Models/Sofa.obj", (2.66, 0.0, 2.15), yaw=-90.0)
    cat = s.group("Cat", items, (2.5, 0.5, 1.55))
    body = s.box("Cat Body", cat, (0.0, 0.08, 0.0), (0.3, 0.17, 0.44), (0.85, 0.48, 0.2), shape="Sphere", rough=0.95)
    motion(body, "Breathe", amount=0.07, speed=0.22, axis=(0.3, 1.0, 0.0))
    s.box("Cat Head", cat, (0.02, 0.1, -0.24), (0.17, 0.14, 0.15), (0.85, 0.48, 0.2), shape="Sphere", rough=0.95)
    for side in (-1, 1):
        s.box(f"Cat Ear {side}", cat, (0.02 + side * 0.05, 0.18, -0.25), (0.05, 0.05, 0.02), (0.8, 0.42, 0.18), rot=(0, 0, 45),
              rough=0.95)
    tail = s.entity("Cat Tail Root", cat, (-0.05, 0.03, 0.2))
    motion(tail, "Sway", amount=14.0, speed=0.13, axis=(0, 1, 0))
    rod(s, tail, "Cat Tail", (0.0, 0.0, 0.0), (0.17, -0.01, 0.12), 0.04, (0.8, 0.44, 0.18))
    s.box("Cat Stripes", cat, (0.0, 0.15, 0.05), (0.2, 0.04, 0.3), (0.6, 0.3, 0.1), shape="Sphere", rough=0.95, shadows=False)
    s.box("Blanket", items, (2.66, 0.66, 1.02), (0.55, 0.03, 0.5), (0.24, 0.38, 0.3), rot=(18, 0, 6), rough=1.0)
    # The boombox on its shelf over the couch, speakers pumping.
    shelf_x = H - 0.18
    s.slab("Radio Shelf", geo, H - 0.36, H, 1.34, 1.38, 2.3, 3.3, WOOD, rough=0.8)
    for z in (2.42, 3.18):
        s.box(f"Shelf Bracket {z}", geo, (H - 0.1, 1.25, z), (0.18, 0.16, 0.02), STEEL, metallic=0.6)
    radio = slot(s, items, "Radio", "Radio")
    rx, ry, rz = shelf_x, 1.52, 2.8
    s.box("Boombox", radio, (rx, ry, rz), (0.22, 0.26, 0.66), (0.14, 0.14, 0.15), rough=0.45, metallic=0.2)
    s.box("Boombox Deck", radio, (rx - 0.111, ry + 0.02, rz), (0.005, 0.1, 0.16), (0.05, 0.05, 0.06), rough=0.2)
    s.box("Boombox Dial", radio, (rx - 0.112, ry + 0.095, rz), (0.004, 0.025, 0.2), (0.9, 0.6, 0.2), emissive=(1.0, 0.55, 0.15),
          emissive_intensity=4.0, shadows=False)
    rod(s, radio, "Boombox Handle", (rx, ry + 0.17, rz - 0.22), (rx, ry + 0.17, rz + 0.22), 0.02, CHROME, metallic=0.9)
    for i, z in enumerate((rz - 0.2, rz + 0.2)):
        cone = s.entity(f"Speaker {i}", radio, (rx - 0.112, ry - 0.01, z))
        motion(cone, "Bob", amount=0.012, speed=2.0, axis=(-1, 0, 0), music=True)
        s.box("Cone", cone, (0.0, 0.0, 0.0), (0.18, 0.012, 0.18), (0.06, 0.06, 0.06), rot=(0, 0, 90), shape="Cylinder", rough=0.7)
        s.box("Dust Cap", cone, (-0.008, 0.0, 0.0), (0.06, 0.012, 0.06), (0.2, 0.2, 0.2), rot=(0, 0, 90), shape="Cylinder")
    station(s, stations, "Radio", "Radio", (rx, ry, rz), (-1.45, 0.05, -0.35), 40)
    # Posters over the couch.
    poster(s, items, "Poster Death Squad", "PosterDeathSquad", (H - 0.012, 1.78, 1.55), 0.46, 0.69, "-x", tilt=3.0)
    poster(s, items, "Poster Magazine", "PosterMagazine", (H - 0.012, 1.86, 3.48), 0.3, 0.41, "-x", tilt=-4.0)
    # The CRT on a milk crate, static on, rabbit ears up; the console under it.
    tv = s.group("TV", items, (2.15, 0.0, 3.82))
    s.box("TV Crate", tv, (0.0, 0.16, 0.0), (0.46, 0.32, 0.36), PLASTIC_RED, rough=0.6)
    s.box("Console", tv, (0.0, 0.345, 0.0), (0.3, 0.05, 0.22), (0.16, 0.16, 0.18), rough=0.4)
    screen_dir = (-0.6, -0.8)
    yaw = math.degrees(math.atan2(screen_dir[0], screen_dir[1]))
    body = s.group("TV Body", tv, (0.0, 0.0, 0.0))
    body.components[0]["Rotation"] = [0.0, round(yaw, 4), 0.0]
    s.box("Tube", body, (0.0, 0.58, 0.0), (0.52, 0.44, 0.46), (0.22, 0.21, 0.19), rough=0.55)
    # The picture is mom's camcorder's, on the tripod by the kit (camcorder() below), a few frames
    # a second like a tape.
    screen = s.box("Screen", body, (0.0, 0.59, 0.232), (0.42, 0.32, 0.01), (1, 1, 1), rough=0.1, shadows=False)
    feed = "Assets/Hideout/Camcorder.rendertexture"
    m = screen.components[-1]["Material"]
    m["Textures"] = {"Diffuse": {"Path": feed}, "Emissive": {"Path": feed}}
    m["EmissiveColor"] = [0.85, 0.9, 1.0]
    m["EmissiveIntensity"] = 1.3
    m["Tiling"] = [1.0, -1.0]
    m["Offset"] = [0.0, 1.0]
    motion(screen, "Flicker", amount=0.35, speed=3.0)
    for side in (-1, 1):
        rod(s, body, f"Rabbit Ear {side}", (0.0, 0.8, -0.05), (side * 0.22, 1.18, -0.08), 0.008, CHROME, metallic=0.9)
    tvlight = s.entity("TV Glow", lights, (2.15 + 0.6 * 0.5, 0.65, 3.82 - 0.8 * 0.5))
    tvlight.add({"Type": "Light", "LightType": "Point", "Color": [0.55, 0.7, 1.0], "Intensity": 2.6, "Range": 3.0,
                 "VolumetricMultiplier": 0.0})
    motion(tvlight, "Flicker", amount=0.4, speed=3.0)
    # The space heater by the couch, glowing.
    s.box("Heater", items, (1.75, 0.17, 1.9), (0.26, 0.34, 0.14), (0.75, 0.72, 0.66), rot=(0, -25, 0), rough=0.5)
    coils = s.box("Heater Coils", items, (1.782, 0.17, 1.832), (0.2, 0.24, 0.01), (1.0, 0.4, 0.1), rot=(0, -25, 0),
                  emissive=(1.0, 0.32, 0.06), emissive_intensity=3.0, shadows=False)
    glow_light(coils, color=(1.0, 0.42, 0.12), intensity=1.6, range_=2.2)
    motion(coils, "Pulse", amount=0.25, speed=0.12)


def utilities(s, geo, items, lights):
    """Back right: the furnace (pilot light flickering) and the water heater."""
    s.box("Furnace", geo, (2.75, 0.675, 5.45), (0.62, 1.35, 0.82), (0.6, 0.58, 0.53), metallic=0.3, rough=0.55)
    s.box("Furnace Panel", geo, (2.75, 0.6, 5.035), (0.5, 0.7, 0.01), (0.5, 0.48, 0.44), metallic=0.3, rough=0.5)
    pilot = s.box("Pilot Light", lights, (2.75, 0.22, 5.03), (0.08, 0.05, 0.005), (0.3, 0.5, 1.0), emissive=(0.35, 0.55, 1.0),
                  emissive_intensity=8.0, shadows=False)
    glow_light(pilot, color=(0.4, 0.55, 1.0), intensity=0.5, range_=1.2)
    motion(pilot, "Flicker", amount=0.5, speed=4.0)
    s.slab("Furnace Flue", geo, 2.62, 2.88, 1.35, 1.93, 5.32, 5.58, (0.62, 0.63, 0.66), metallic=0.85, rough=0.35)
    s.box("Water Heater", geo, (2.02, 0.76, 5.62), (0.55, 1.52, 0.55), OFFWHITE, shape="Cylinder", metallic=0.2, rough=0.4)
    for i, x in enumerate((1.94, 2.1)):
        rod(s, geo, f"Heater Pipe {i}", (x, 1.52, 5.62), (x, JOIST, 5.62), 0.022, COPPER, metallic=0.85, rough=0.3)


def workbench(s, geo, items, stations, lights):
    """Left wall: the bench (the practice pad), the pegboard, the lamp, the dying tube; the fridge."""
    bz = 3.8
    textured(s.slab("Bench Top", geo, -H, -H + 0.62, 0.82, 0.87, bz - 0.72, bz + 0.72, (1, 1, 1), rough=0.8), "Wood", (1, 2))
    for dz in (-0.66, 0.66):
        s.box(f"Bench Leg {dz}", geo, (-H + 0.55, 0.41, bz + dz), (0.06, 0.82, 0.06), WOOD)
    textured(s.slab("Bench Shelf", geo, -H, -H + 0.6, 0.2, 0.23, bz - 0.7, bz + 0.7, (1, 1, 1)), "WoodDark", (1, 2))
    s.prop("Toolbox", items, "Assets/Models/Venue/ToolBox.obj", (-H + 0.3, 0.23, bz - 0.35), yaw=90.0)
    textured(s.slab("Pegboard", geo, -H, -H + 0.02, 1.0, 1.9, bz - 0.7, bz + 0.7, (1, 1, 1), rough=0.9), "Pegboard", (2.8, 1.8))
    rod(s, items, "Hammer Handle", (-H + 0.04, 1.55, bz + 0.45), (-H + 0.04, 1.25, bz + 0.45), 0.025, (0.6, 0.42, 0.22))
    s.box("Hammer Head", items, (-H + 0.04, 1.57, bz + 0.45), (0.03, 0.04, 0.13), STEEL, metallic=0.8, rough=0.35)
    s.box("Wrench", items, (-H + 0.035, 1.45, bz + 0.25), (0.01, 0.24, 0.035), CHROME, metallic=0.9, rough=0.3, rot=(10, 0, 0))
    for i, z in enumerate((bz - 0.05, bz + 0.0, bz + 0.05)):
        rod(s, items, f"Spare Stick {i}", (-H + 0.05, 1.82, z), (-H + 0.05, 1.42, z + 0.03), 0.014, (0.86, 0.72, 0.46))
    poster(s, items, "Sticky Practice", "StickyPractice", (-H + 0.025, 1.76, bz - 0.5), 0.09, 0.09, "+x", tilt=-6.0)
    poster(s, items, "Sticky Rent", "StickyRent", (-H + 0.025, 1.2, bz - 0.55), 0.09, 0.09, "+x", tilt=5.0)
    poster(s, items, "Rudiment Chart", "PosterRudiments", (-H + 0.012, 1.5, 2.45), 0.44, 0.69, "+x", tilt=1.5)
    # The coffee can of sticks.
    s.box("Stick Can", items, (-H + 0.42, 0.955, bz - 0.55), (0.12, 0.17, 0.12), (0.35, 0.12, 0.1), shape="Cylinder", metallic=0.5)
    for i, (dx, dz) in enumerate(((0.02, 0.0), (-0.02, 0.02), (0.0, -0.025), (0.03, 0.03))):
        rod(s, items, f"Can Stick {i}", (-H + 0.42 + dx, 0.9, bz - 0.55 + dz), (-H + 0.42 + dx * 4, 1.3, bz - 0.55 + dz * 4), 0.013,
            (0.86, 0.72, 0.46))
    # Before there was a pad: a phone book with gaffer tape on it. And the magazines.
    s.box("Phone Book", items, (-H + 0.33, 0.915, bz + 0.05), (0.24, 0.07, 0.3), (0.85, 0.75, 0.25), rot=(0, 8, 0), rough=0.9)
    s.box("Gaffer Tape", items, (-H + 0.33, 0.951, bz + 0.05), (0.1, 0.003, 0.3), (0.12, 0.12, 0.12), rot=(0, 8, 0), rough=0.6)
    for i in range(4):
        s.box(f"Magazine {i}", items, (-H + 0.42, 0.885 + i * 0.012, bz + 0.48), (0.21, 0.01, 0.28),
              [(0.8, 0.2, 0.2), (0.9, 0.9, 0.85), (0.2, 0.3, 0.6), (0.85, 0.7, 0.2)][i], rot=(0, 10 * i - 12, 0), rough=0.7)
    # The practice pad's station, and the things the ladder gives (pad, metronome, lamp).
    station(s, stations, "Practice Pad", "PracticePad", (-H + 0.3, 0.95, bz), (1.45, 0.65, -0.55), 40)
    pad = slot(s, items, "Practice Pad", "PracticePad")
    s.box("Pad", pad, (-H + 0.32, 0.965, bz - 0.25), (0.3, 0.03, 0.3), (0.12, 0.12, 0.12), shape="Cylinder", rough=0.9)
    s.box("Pad Rim", pad, (-H + 0.32, 0.955, bz - 0.25), (0.32, 0.02, 0.32), (0.75, 0.1, 0.1), shape="Cylinder", rough=0.6)
    rod(s, pad, "Pad Stick L", (-H + 0.18, 0.99, bz - 0.2), (-H + 0.56, 0.99, bz - 0.3), 0.014, (0.86, 0.72, 0.46))
    rod(s, pad, "Pad Stick R", (-H + 0.2, 0.995, bz - 0.15), (-H + 0.58, 0.995, bz - 0.24), 0.014, (0.86, 0.72, 0.46))
    met = slot(s, items, "Metronome", "Metronome")
    s.box("Metronome", met, (-H + 0.3, 0.96, bz + 0.27), (0.1, 0.18, 0.08), (0.45, 0.12, 0.08), rough=0.6)
    arm = s.entity("Metronome Arm", met, (-H + 0.3, 0.9, bz + 0.23))
    motion(arm, "Sway", amount=25.0, speed=1.0, axis=(1, 0, 0))
    s.box("Arm", arm, (0.0, 0.08, 0.0), (0.006, 0.16, 0.006), CHROME, metallic=0.9, shadows=False)
    lamp = slot(s, items, "Lava Lamp", "Lamp")
    blob = s.box("Lava", lamp, (-H + 0.3, 1.05, bz + 0.55), (0.1, 0.3, 0.1), (0.9, 0.3, 0.6), shape="Capsule",
                 emissive=(1.0, 0.25, 0.55), emissive_intensity=4.0)
    glow_light(blob, color=(1.0, 0.3, 0.6), intensity=1.5, range_=2.0)
    motion(blob, "Pulse", amount=0.3, speed=0.08)
    # The desk lamp clamped to the bench, pooled on the pad.
    from hideoutgen import look_rotation
    base = (-H + 0.12, 0.87, bz + 0.55)
    elbow = (-H + 0.2, 1.38, bz + 0.4)
    head = (-H + 0.32, 1.32, bz + 0.12)
    rod(s, items, "Lamp Arm 1", base, elbow, 0.02, (0.15, 0.15, 0.16), metallic=0.6)
    rod(s, items, "Lamp Arm 2", elbow, head, 0.02, (0.15, 0.15, 0.16), metallic=0.6)
    s.box("Lamp Shade", items, head, (0.15, 0.13, 0.15), (0.12, 0.25, 0.18), shape="Cylinder", rot=(20, 0, -20), metallic=0.4, rough=0.4)
    target = (-H + 0.32, 0.88, bz)
    light(s, lights, "Desk Lamp", (head[0], head[1] - 0.05, head[2]), kind="Spot", color=(1.0, 0.8, 0.52), intensity=4.5,
          range_=2.4, rot=look_rotation((head[0], head[1] - 0.05, head[2]), target), inner=22.0, outer=48.0, shadows=True,
          volumetric=0.6)
    # The shop light over the bench: a fluorescent tube on its last legs.
    tx, ty = -H + 0.55, 1.98
    rod(s, items, "Shop Light Chain A", (tx, JOIST, bz - 0.5), (tx, ty + 0.03, bz - 0.5), 0.006, STEEL, metallic=0.8, shadows=False)
    rod(s, items, "Shop Light Chain B", (tx, JOIST, bz + 0.5), (tx, ty + 0.03, bz + 0.5), 0.006, STEEL, metallic=0.8, shadows=False)
    s.box("Shop Light", items, (tx, ty + 0.02, bz), (0.17, 0.05, 1.25), (0.85, 0.85, 0.82), rough=0.5)
    tube = s.box("Tube", lights, (tx, ty - 0.012, bz), (0.035, 1.18, 0.035), (0.9, 0.95, 1.0), rot=(90, 0, 0), shape="Cylinder",
                 emissive=(0.85, 0.93, 1.0), emissive_intensity=5.0, shadows=False)
    glow_light(tube, color=(0.82, 0.92, 1.0), intensity=7.0, range_=4.5, volumetric=0.4)
    motion(tube, "Flicker", amount=0.95, speed=1.2)
    # The mini fridge (mom's note on it), and the trash.
    s.box("Fridge", items, (-H + 0.27, 0.42, 1.95), (0.5, 0.84, 0.5), (0.86, 0.86, 0.84), rough=0.35)
    s.box("Fridge Handle", items, (-H + 0.525, 0.6, 2.15), (0.02, 0.3, 0.025), CHROME, metallic=0.9)
    poster(s, items, "Sticky Dinner", "StickyDinner", (-H + 0.523, 0.62, 1.92), 0.11, 0.11, "+x", tilt=-4.0)
    for i, (x, z) in enumerate(((-2.35, 3.05), (-2.2, 2.92), (-2.42, 2.8))):
        s.box(f"Paper Ball {i}", items, (x, 0.04, z), (0.08, 0.075, 0.08), (0.92, 0.92, 0.88), shape="Sphere", rough=1.0)


def gig_board(s, geo, items, stations):
    gz = 5.1
    textured(s.slab("Gig Board", geo, -H, -H + 0.03, 1.12, 2.0, gz - 0.72, gz + 0.72, (1, 1, 1), rough=0.95), "Cork", (1.4, 0.9))
    s.slab("Board Frame Top", geo, -H, -H + 0.04, 1.99, 2.02, gz - 0.74, gz + 0.74, WOOD)
    s.slab("Board Frame Bottom", geo, -H, -H + 0.04, 1.1, 1.13, gz - 0.74, gz + 0.74, WOOD)
    station(s, stations, "Gig Board", "GigBoard", (-H + 0.05, 1.56, gz), (1.75, 0.0, -0.85), 45)
    # Always up: the ads the kid put up and answered.
    poster(s, items, "Bassist Wanted", "FlyerBassist", (-H + 0.034, 1.52, gz - 0.48), 0.27, 0.36, "+x", tilt=2.5)
    poster(s, items, "Lawns Mowed", "FlyerLawns", (-H + 0.034, 1.5, gz + 0.5), 0.27, 0.36, "+x", tilt=-3.5)
    for z, y in ((gz - 0.48, 1.69), (gz + 0.5, 1.67)):
        s.box(f"Pin {z}", items, (-H + 0.042, y, z), (0.018, 0.018, 0.018), (0.1, 0.35, 0.85), shape="Sphere", shadows=False)
    # The gigs, as they're played.
    flyers = (("FlyerA", "FlyerBackyard", 1.62, -0.08, -3.0), ("FlyerB", "FlyerClub", 1.45, 0.18, 2.0), ("FlyerC", "FlyerFestival", 1.7, 0.05, -1.5))
    for slot_name, texture, y, dz, tilt in flyers:
        f = slot(s, items, f"Flyer {slot_name[-1]}", slot_name)
        poster(s, f, "Flyer", texture, (-H + 0.038, y, gz + dz), 0.27, 0.36, "+x", tilt=tilt)
        s.box("Pin", f, (-H + 0.046, y + 0.16, gz + dz), (0.018, 0.018, 0.018), (0.85, 0.12, 0.1), shape="Sphere", shadows=False)


def trophies(s, items, stations):
    """Right wall, back: what the player has earned (and the 7th-grade certificate, always)."""
    wz = 4.35
    station(s, stations, "Trophy Wall", "TrophyWall", (H - 0.05, 1.6, wz), (-1.75, -0.05, -0.45), 52)
    poster(s, items, "Certificate", "Certificate", (H - 0.012, 1.45, wz + 0.25), 0.5, 0.375, "-x", tilt=-1.0)
    ribbon = s.group("Ribbon", items, (H - 0.03, 1.1, wz - 0.1))
    s.box("Rosette", ribbon, (0.0, 0.0, 0.0), (0.12, 0.02, 0.12), (0.15, 0.3, 0.75), rot=(0, 0, 90), shape="Cylinder", rough=0.8)
    s.box("Rosette Middle", ribbon, (-0.012, 0.0, 0.0), (0.06, 0.012, 0.06), (0.85, 0.75, 0.3), rot=(0, 0, 90), shape="Cylinder")
    for side in (-1, 1):
        s.box(f"Tail {side}", ribbon, (-0.005, -0.1, side * 0.025), (0.004, 0.16, 0.04), (0.15, 0.3, 0.75), rot=(side * 8, 0, 0))
    band = slot(s, items, "Band Poster", "PosterA")
    poster(s, band, "Poster", "PosterGhostNotes", (H - 0.012, 1.55, wz - 0.42), 0.4, 0.6, "-x", tilt=-2.0)
    for slot_name, z in (("PlaqueA", wz + 0.62), ("PlaqueB", wz + 0.92)):
        p = slot(s, items, slot_name, slot_name)
        s.box("Plaque", p, (H - 0.03, 1.82, z), (0.03, 0.3, 0.24), WOOD, rough=0.6)
        s.box("Plate", p, (H - 0.05, 1.82, z), (0.01, 0.16, 0.16), GOLD, metallic=0.9, rough=0.25)
    rec = slot(s, items, "Gold Record", "GoldRecord")
    s.box("Frame", rec, (H - 0.03, 1.78, wz + 0.25), (0.03, 0.4, 0.34), BLACK, rough=0.5)
    s.box("Record", rec, (H - 0.05, 1.8, wz + 0.25), (0.26, 0.01, 0.26), GOLD, rot=(0, 0, 90), shape="Cylinder", metallic=1.0,
          rough=0.15)
    head = slot(s, items, "Signed Snare Head", "WallLeft")
    s.box("Signed Head", head, (H - 0.03, 2.0, wz - 0.42), (0.3, 0.01, 0.3), WHITE, rot=(0, 0, 90), shape="Cylinder", rough=0.6)
    shelf = slot(s, items, "Vinyl Shelf", "Shelf")
    s.slab("Shelf", shelf, H - 0.3, H, 0.0, 0.62, 3.25, 3.75, WOOD, rough=0.8)
    for i in range(7):
        s.box(f"Sleeve {i}", shelf, (H - 0.15, 0.45, 3.3 + i * 0.065), (0.25, 0.3, 0.02),
              [(0.8, 0.2, 0.2), (0.2, 0.5, 0.8), (0.9, 0.8, 0.2), (0.1, 0.1, 0.1)][i % 4], rough=0.7)


def front(s, geo, items, stations):
    """By the camera: the laptop on its milk crate (the DLC), the beanbag, the cans, the pizza."""
    cx, cz = -1.3, 1.9
    s.box("Laptop Crate", items, (cx, 0.165, cz), (0.36, 0.33, 0.36), PLASTIC_RED, rough=0.6)
    s.box("Crate Inside", items, (cx, 0.2, cz), (0.3, 0.27, 0.3), (0.3, 0.04, 0.03), rough=0.7)
    s.box("Laptop Base", stations, (cx, 0.345, cz - 0.02), (0.34, 0.02, 0.24), (0.2, 0.2, 0.22), metallic=0.6, rough=0.4)
    textured(s.box("Laptop Screen", stations, (cx, 0.46, cz + 0.1), (0.34, 0.22, 0.012), (1, 1, 1), rot=(-12, 0, 0), rough=0.2,
                   shadows=False), "LaptopScreen", emissive=True, emissive_intensity=1.1)
    station(s, stations, "Laptop", "Laptop", (cx, 0.45, cz), (0.35, 0.5, -0.95), 40)
    cans = ((cx + 0.12, 0.395, cz - 0.12, (0.1, 0.65, 0.2)), (cx - 0.14, 0.395, cz - 0.1, (0.05, 0.05, 0.06)),
            (-0.75, 0.06, 1.55, (0.1, 0.65, 0.2)), (-0.68, 0.03, 1.4, (0.15, 0.3, 0.8)), (-0.4, 0.06, 2.3, (0.05, 0.05, 0.06)))
    for i, (x, y, z, colour) in enumerate(cans):
        rot = (90, 30 * i, 0) if y < 0.05 else (0, 0, 0)
        s.box(f"Can {i}", items, (x, y, z), (0.066, 0.12, 0.066), colour, shape="Cylinder", rot=rot, metallic=0.8, rough=0.3)
    s.box("Beanbag", items, (-0.75, 0.24, 1.4), (0.85, 0.46, 0.8), (0.5, 0.2, 0.55), shape="Sphere", rough=0.95)
    for i in range(3):
        textured(s.box(f"Pizza Box {i}", items, (0.42, 0.025 + i * 0.045, 1.1), (0.42, 0.04, 0.42), (1, 1, 1), rot=(0, 7 * i - 5, 0),
                       rough=0.9), "PizzaBox")
    # The smoke detector, its light blinking.
    s.box("Smoke Detector", geo, (0.65, JOIST - 0.02, 2.0), (0.13, 0.04, 0.13), OFFWHITE, shape="Cylinder")
    led = s.box("Smoke Detector Light", geo, (0.68, JOIST - 0.045, 2.0), (0.012, 0.012, 0.012), (1, 0.05, 0.05), shape="Sphere",
                emissive=(1.0, 0.05, 0.05), emissive_intensity=12.0, shadows=False)
    motion(led, "Blink", amount=0.06, speed=0.5)
    # Laundry drying on a line across the corner, nodding in the fan's draught.
    a, b = (0.95, 2.04, 1.15), (3.15, 2.04, 1.95)
    rod(s, items, "Clothesline", a, b, 0.006, OFFWHITE, shadows=False)
    laundry = (("Sock", 0.12, (0.15, 0.24, 0.05), (0.8, 0.15, 0.15)), ("Sock 2", 0.22, (0.15, 0.22, 0.05), (0.85, 0.85, 0.8)),
               ("Band Tee", 0.42, (0.5, 0.55, 0.02), (0.08, 0.08, 0.09)), ("Towel", 0.72, (0.45, 0.6, 0.02), (0.2, 0.45, 0.65)),
               ("Boxers", 0.9, (0.3, 0.24, 0.03), (0.75, 0.3, 0.55)))
    for i, (name, t, size, colour) in enumerate(laundry):
        hook = tuple(a[k] + (b[k] - a[k]) * t for k in range(3))
        pin = s.entity(f"{name} Peg", items, hook)
        motion(pin, "Sway", amount=3.0, speed=0.4 + 0.07 * i, axis=(1, 0, -0.4), phase=0.17 * i)
        yaw = math.degrees(math.atan2(b[0] - a[0], b[2] - a[2])) - 90.0
        cloth = s.box(name, pin, (0.0, -size[1] / 2 - 0.01, 0.0), size, colour, rot=(0, yaw, 0), rough=1.0)
        if name == "Band Tee":
            poster(s, pin, "Tee Print", "KickHead", (0.0, -0.22, 0.0), 0.22, 0.22, "-z", glow=0.0, thick=0.026)
    # The clock over the stairs, five minutes fast since forever.
    s.box("Clock", geo, (-H + 0.02, 1.95, 0.6), (0.3, 0.03, 0.3), OFFWHITE, rot=(0, 0, 90), shape="Cylinder", rough=0.5)
    s.box("Clock Rim", geo, (-H + 0.015, 1.95, 0.6), (0.33, 0.02, 0.33), BLACK, rot=(0, 0, 90), shape="Cylinder", rough=0.5)
    s.box("Hour Hand", geo, (-H + 0.04, 1.98, 0.62), (0.006, 0.08, 0.012), BLACK, rot=(-30, 0, 0))
    s.box("Minute Hand", geo, (-H + 0.042, 1.95, 0.55), (0.006, 0.012, 0.11), BLACK, rot=(15, 0, 0))
    # A carpet offcut where the laptop lives.
    s.box("Offcut", items, (-1.05, 0.006, 1.6), (1.5, 0.012, 1.1), (0.3, 0.32, 0.26), rot=(0, 9, 0), rough=1.0, shadows=False)
    # A dim fill from the stairs side, so the near things read.
    light(s, geo, "Fill", (0.3, 1.3, 0.3), color=(1.0, 0.82, 0.62), intensity=1.4, range_=4.0)


def unlocked_extras(s, items):
    """The rest of the items' slots, so they appear here too once earned."""
    rug = slot(s, items, "Rug", "Rug")
    s.box("Rug", rug, (0.0, 0.013, 4.75), (2.5, 0.01, 2.2), (0.35, 0.18, 0.12), rough=1.0, shadows=False)
    bag = slot(s, items, "Stick Bag", "StickBag")
    s.box("Bag", bag, (0.72, 0.45, 4.55), (0.06, 0.4, 0.14), (0.1, 0.1, 0.12), rough=0.9)
    spare = slot(s, items, "Spare Cymbal", "CymbalStand")
    rod(s, spare, "Stand", (-1.0, 0.0, 5.55), (-1.0, 1.18, 5.55), 0.025, CHROME, metallic=0.9)
    s.box("Cymbal", spare, (-1.0, 1.2, 5.55), (0.42, 0.012, 0.42), BRASS, rot=(-14, 0, 0), shape="Cylinder", metallic=0.9, rough=0.25)
    neon = slot(s, items, "Neon Sign", "Neon")
    sign = s.box("Neon", neon, (-1.55, 2.0, D - 0.04), (0.7, 0.16, 0.02), (0.2, 0.05, 0.1), emissive=(1.0, 0.15, 0.55),
                 emissive_intensity=5.0, shadows=False)
    glow_light(sign, color=(1.0, 0.2, 0.6), intensity=2.0, range_=3.0)
    foam = slot(s, items, "Acoustic Foam", "Foam")
    for i in range(4):
        for j in range(3):
            s.box(f"Foam {i}.{j}", foam, (H - 0.04, 0.9 + j * 0.5, 0.6 + i * 0.5), (0.06, 0.46, 0.46), (0.1, 0.1, 0.12), rough=1.0,
                  shadows=False)
    desk = slot(s, items, "Mixing Desk", "Desk")
    s.box("Desk", desk, (1.0, 0.8, 1.9), (1.0, 0.1, 0.55), (0.15, 0.15, 0.16), rot=(-10, 0, 0), rough=0.4)


def build_basement():
    s = Scene(seed=2101)
    root = s.group("Hideout Basement")
    geo = s.group("Room", root)
    items = s.group("Things", root)
    stations = s.group("Stations", root)
    lights = s.group("Lights", root)
    marks = s.group("Markers", root)
    shell(s, geo)
    stairs(s, geo, items)
    back_wall(s, geo, items, lights)
    kit_corner(s, geo, items, stations, lights)
    couch_corner(s, geo, items, stations, lights)
    camcorder(s, items, lights)
    utilities(s, geo, items, lights)
    workbench(s, geo, items, stations, lights)
    gig_board(s, geo, items, stations)
    trophies(s, items, stations)
    front(s, geo, items, stations)
    unlocked_extras(s, items)
    # Room tone: the furnace, the tube, the fan, the drip (Tools/Hideout/make_sounds.py).
    tone = s.group("Room Tone", root)
    sound(s, tone, "Furnace Hum", (2.75, 0.6, 5.4), "Furnace", volume=0.55, near=1.0, far=9.0)
    sound(s, tone, "Tube Buzz", (-H + 0.55, 1.98, 3.8), "TubeBuzz", volume=0.18, near=0.4, far=4.5)
    sound(s, tone, "Fan Whir", (-1.55, 0.6, 4.75), "FanWhir", volume=0.4, near=0.6, far=6.0)
    sound(s, tone, "Drip", (1.94, 1.9, 5.5), "Drip", volume=0.35, near=0.5, far=6.0)
    # The overview; the session's first visit starts at the top of the stairs, looking down at the kit.
    view(s, marks, (0.15, 1.5, -1.3), (0.05, 0.92, 4.4), 56.0, intro_eye=(-2.6, 2.2, -0.9), intro_target=(-0.6, 0.6, 3.2))
    return s
