"""The garage, the hideout's second room (Assets/Hideout/Garage.lvl): the kit has moved out of the
basement into the parents' garage after the first gig.

Painted drywall and a bigger slab, the roll-up door propped open a foot at the back with the
streetlight coming in under it behind the drummer, the opener's light on the ceiling, party
lights strung across. The workbench grew a vise and a proper pegboard; bikes hang from the
ceiling, the lawnmower that paid for the cymbals sits in the corner, paint and junk on the
shelves. The couch and the cat came too, with the boombox (its display scrolling the song), the
CRT and mom's camcorder; there's a dartboard now, and a soda fridge. The house door at the front,
the kitchen light on. By day the driveway's in the sun under the door; by night the streetlight.
The gear list is taped over the bike, the setlist to the floor, tape where the gear will go.

Room space as the basement: x across (+x the couch side), y up, z from the camera to the door.
"""
import math
import random

from hideoutgen import (band_name, band_name_text, BLACK, BRASS, CHROME, CORK, GOLD, MARKER, OFFWHITE, STEEL, WHITE, WOOD, Scene, boombox_display,
                        clock_hands, drummer, dust, glow_light, light, look_rotation, motion, poster, readout, rod, scrawl, setlist, slot, sound,
                        stand_in, station, tally, tape_outline, textured, view, when)

H = 3.8        # half the width
D = 7.2        # the back wall's face (the door)
TOP = 2.9      # the ceiling
DOOR = 1.75    # half the door's width
GAP = 0.42     # how far the door is propped open at night
GAP_DAY = 1.1  # and by day, for the air

PLASTIC_RED = (0.62, 0.08, 0.07)
PLASTIC_BLUE = (0.08, 0.2, 0.55)
GREEN = (0.15, 0.45, 0.2)
PAINT = [(0.8, 0.2, 0.15), (0.9, 0.85, 0.75), (0.2, 0.35, 0.7), (0.9, 0.7, 0.15), (0.3, 0.6, 0.3), (0.55, 0.55, 0.58)]
PARTY = [(1.0, 0.85, 0.55), (1.0, 0.3, 0.2), (0.3, 0.8, 1.0), (1.0, 0.85, 0.55), (0.6, 1.0, 0.4)]


def shell(s, geo):
    textured(s.slab("Floor", geo, -H, H, -0.1, 0.0, -1.6, D + 0.2, (1, 1, 1), rough=0.75), "ConcreteFloor", (3.8, 4.4),
             tint=(1.18, 1.18, 1.16))
    for name, x0, x1 in (("Left Wall", -H - 0.12, -H), ("Right Wall", H, H + 0.12)):
        textured(s.slab(name, geo, x0, x1, 0.0, TOP, -1.6, D, (1, 1, 1), rough=0.9), "Drywall", (7.4, 2.4))
    textured(s.slab("Front Wall", geo, -H, H, 0.0, TOP, -1.72, -1.6, (1, 1, 1), rough=0.9), "Drywall", (6.3, 2.4))
    # The back wall round the door's opening.
    for name, x0, x1 in (("Back Wall Left", -H, -DOOR - 0.12), ("Back Wall Right", DOOR + 0.12, H)):
        textured(s.slab(name, geo, x0, x1, 0.0, TOP, D, D + 0.12, (1, 1, 1), rough=0.9), "Drywall", (1.7, 2.4))
    textured(s.slab("Back Wall Header", geo, -DOOR - 0.12, DOOR + 0.12, 2.4, TOP, D, D + 0.12, (1, 1, 1), rough=0.9), "Drywall", (3, 0.4))
    for x in (-DOOR - 0.06, DOOR + 0.06):
        s.slab(f"Door Jamb {x}", geo, x - 0.06, x + 0.06, 0.0, 2.4, D - 0.02, D + 0.12, (0.85, 0.84, 0.8), rough=0.6)
    textured(s.slab("Ceiling", geo, -H, H, TOP, TOP + 0.08, -1.6, D + 0.12, (1, 1, 1), rough=0.95), "Drywall", (6, 7))
    # The oil stain where a car used to be, and the drain.
    s.box("Oil Stain", geo, (-1.25, 0.002, 3.0), (0.9, 0.003, 0.6), (0.2, 0.19, 0.18), shape="Cylinder", rough=0.25, shadows=False)
    s.box("Drain", geo, (1.1, 0.002, 3.4), (0.18, 0.004, 0.18), (0.05, 0.05, 0.05), shape="Cylinder", metallic=0.6, rough=0.4,
          shadows=False)


def door(s, geo, lights, items):
    """The roll-up door, propped up a foot at night and higher by day; the driveway outside."""
    for when_, gap in (("Night", GAP), ("Day", GAP_DAY)):
        panels = when(s.group(f"Roll Door {when_}", geo), when_)
        y = gap
        i = 0
        while y < 2.4:
            s.slab(f"Door Panel {i}", panels, -DOOR, DOOR, y, min(2.4, y + 0.48), D + 0.02, D + 0.06, (0.86, 0.86, 0.83), metallic=0.3, rough=0.5)
            s.slab(f"Door Rib {i}", panels, -DOOR, DOOR, y + 0.22, y + 0.26, D - 0.0, D + 0.02, (0.78, 0.78, 0.75), metallic=0.3, rough=0.5)
            y += 0.48
            i += 1
        s.box("Door Handle", panels, (0.0, gap + 0.18, D - 0.01), (0.18, 0.03, 0.03), STEEL, metallic=0.8)
    # The tracks the door runs up into, and the opener.
    for x in (-DOOR - 0.04, DOOR + 0.04):
        s.slab(f"Door Track {x}", geo, x - 0.03, x + 0.03, 0.0, 2.5, D - 0.05, D, STEEL, metallic=0.7, rough=0.4)
        s.slab(f"Ceiling Track {x}", geo, x - 0.03, x + 0.03, 2.5, 2.56, 4.2, D, STEEL, metallic=0.7, rough=0.4)
    rod(s, geo, "Opener Rail", (0.0, 2.78, 3.4), (0.0, 2.78, D), 0.05, STEEL, metallic=0.7)
    s.box("Opener", geo, (0.0, 2.7, 3.3), (0.42, 0.18, 0.55), (0.82, 0.82, 0.8), rough=0.5)
    opener_bulb = s.box("Opener Light", lights, (0.0, 2.59, 3.3), (0.3, 0.02, 0.2), (1.0, 0.9, 0.7), emissive=(1.0, 0.85, 0.6),
                        emissive_intensity=4.0, shadows=False)
    glow_light(opener_bulb, color=(1.0, 0.82, 0.58), intensity=6.0, range_=6.0, shadows=True, volumetric=0.8)
    led = s.box("Opener LED", lights, (0.18, 2.62, 3.04), (0.014, 0.014, 0.014), (0.1, 1.0, 0.2), shape="Sphere",
                emissive=(0.1, 1.0, 0.2), emissive_intensity=10.0, shadows=False)
    motion(led, "Blink", amount=0.08, speed=0.6)
    # Outside: the driveway, the street's glow, the lamp over it shining in under the door. By
    # day, the driveway in the afternoon sun and the light off it coming in low.
    s.slab("Driveway", geo, -H - 2.0, H + 2.0, -0.12, -0.02, D + 0.12, D + 7.0, (0.25, 0.25, 0.27), rough=0.8)
    night = when(s.group("Night", lights), "Night")
    s.slab("Night Sky", night, -H - 4.0, H + 4.0, -0.2, 6.0, D + 9.0, D + 9.2, (0.02, 0.03, 0.06), emissive=(0.03, 0.05, 0.1),
           emissive_intensity=1.0)
    lamp = (1.4, 3.6, D + 5.5)
    light(s, night, "Streetlight Under The Door", lamp, kind="Spot", color=(0.95, 0.75, 0.45), intensity=90.0, range_=14.0,
          rot=look_rotation(lamp, (0.2, 0.0, D - 1.2)), inner=16.0, outer=30.0, shadows=True, volumetric=6.0)
    # Now and then a car goes past out there.
    car = (-4.5, 0.6, D + 3.0)
    sweep = light(s, night, "Passing Car", car, kind="Spot", color=(1.0, 0.95, 0.85), intensity=60.0, range_=14.0,
                  rot=look_rotation(car, (0.0, 0.2, D - 2.0)), inner=10.0, outer=20.0, volumetric=4.0)
    motion(sweep, "Pass", amount=4.0, speed=1.0 / 19.0, axis=(1, 0, 0), phase=0.3)
    day = when(s.group("Day", lights), "Day")
    s.slab("Day Sky", day, -H - 4.0, H + 4.0, -0.2, 6.0, D + 9.0, D + 9.2, (0.62, 0.74, 0.9), emissive=(0.62, 0.76, 0.98),
           emissive_intensity=2.2)
    s.slab("Lawn", day, -H - 4.0, H + 4.0, -0.11, -0.03, D + 4.0, D + 9.0, (0.22, 0.42, 0.14), rough=0.9)
    sun = (-2.6, 3.2, D + 6.0)
    light(s, day, "Sun Under The Door", sun, kind="Spot", color=(1.0, 0.88, 0.68), intensity=170.0, range_=16.0,
          rot=look_rotation(sun, (0.6, 0.0, D - 1.6)), inner=16.0, outer=28.0, shadows=True, volumetric=8.0)
    light(s, day, "Daylight Bounce", (0.0, 0.5, D - 0.6), color=(0.85, 0.9, 1.0), intensity=4.0, range_=5.5)
    # The neighbour's fence and a tree across the street, so the gap isn't just sky.
    for i in range(14):
        x = -H - 1.5 + i * 0.75
        s.box(f"Fence Board {i}", day, (x, 0.75, D + 4.2), (0.7, 1.5, 0.04), (0.78, 0.68, 0.52), rough=0.9)
    s.box("Tree Trunk", day, (2.6, 1.4, D + 6.5), (0.35, 2.8, 0.35), (0.35, 0.25, 0.16), shape="Cylinder", rough=0.9)
    s.box("Tree Crown", day, (2.6, 3.4, D + 6.5), (2.6, 2.2, 2.4), (0.25, 0.45, 0.18), shape="Sphere", rough=0.9)
    s.box("Bin", day, (-1.2, 0.5, D + 2.2), (0.6, 1.0, 0.7), (0.1, 0.3, 0.15), rough=0.6)
    dust(s, lights, "Dust", (0.0, 0.7, D - 1.5), (3.4, 1.4, 2.6), count=220, rate=30.0)
    # The bedsheet came too, hung off the door tracks.
    band_name(poster(s, items, "Banner", "Banner", (0.0, 2.05, D - 0.25), 2.6, 1.1, "-z", tilt=1.0, thick=0.006), "Unnamed")
    band_name(poster(s, items, "Banner Blank", "BannerBlank", (0.0, 2.05, D - 0.252), 2.6, 1.1, "-z", tilt=1.0, thick=0.006), "Named")
    sheet = band_name_text(s, items, "Band Name On The Sheet", (0.0, 2.15, D - 0.27), 0.32, (0.6, 0.05, 0.07), fit=12)
    sheet.components[0]["Rotation"] = [0.0, 0.0, 1.0]


def kit_area(s, geo, items, stations, lights):
    drummer(s, items, (0.0, 0.0, 5.25), yaw=180.0)
    head = textured(s.box("Kick Logo", items, (0.0, 0.31, 4.098), (0.56, 0.56, 0.004), (1, 1, 1), rough=0.7, shadows=False),
                    "KickHead", emissive=True, emissive_intensity=0.25)
    head.components[-1]["Material"]["AlphaCutoff"] = 0.5
    band_name(head, "Unnamed")
    blank = textured(s.box("Kick Logo Blank", items, (0.0, 0.31, 4.097), (0.56, 0.56, 0.004), (1, 1, 1), rough=0.7, shadows=False),
                     "KickHeadBlank", emissive=True, emissive_intensity=0.25)
    blank.components[-1]["Material"]["AlphaCutoff"] = 0.5
    band_name(blank, "Named")
    band_name_text(s, items, "Band Name On The Kick", (0.0, 0.34, 4.09), 0.07, (0.08, 0.08, 0.1), fit=9)
    station(s, stations, "Kit", "Kit", (0.0, 0.95, 4.5), (0.3, 0.7, -2.1), 42)
    # The amp, a real PA wedge now, the mic stand the singer never uses.
    amp = (1.6, 0.0, 4.75)
    s.box("Amp", stations, (amp[0], 0.38, amp[2]), (0.72, 0.76, 0.36), (0.07, 0.07, 0.07), rough=0.6)
    s.box("Amp Grille", stations, (amp[0], 0.33, amp[2] - 0.185), (0.64, 0.52, 0.01), (0.16, 0.14, 0.12), rough=0.95)
    s.box("Amp Panel", stations, (amp[0], 0.68, amp[2] - 0.185), (0.64, 0.07, 0.01), (0.7, 0.6, 0.4), metallic=0.6, rough=0.3)
    s.box("Amp Light", stations, (amp[0] + 0.26, 0.68, amp[2] - 0.192), (0.016, 0.016, 0.006), (1, 0.1, 0.05), shape="Sphere",
          emissive=(1.0, 0.1, 0.05), emissive_intensity=8.0, shadows=False)
    station(s, stations, "Mixer", "Mixer", (amp[0], 0.5, amp[2]), (-0.5, 0.65, -1.45), 45, label="SETTINGS")
    s.prop("Wedge", items, "Assets/Models/Venue/Wedge.obj", (-1.1, 0.0, 3.7), yaw=150.0)
    guitar = s.entity("Guitar", items, (2.05, 0.31, 4.55), (0.0, -25.0, -78.0))
    guitar.add({"Type": "Model", "ModelPath": "Assets/Models/Instruments/Runtime/Guitar.obj"})
    bass = s.entity("Bass", items, (2.3, 0.33, 4.75), (0.0, -35.0, -80.0))
    bass.add({"Type": "Model", "ModelPath": "Assets/Models/Instruments/Runtime/Bass.obj"})
    setlist(s, items, (0.62, 0.003, 3.5), -12.0)
    # The box fan, on a bucket now.
    fan = s.group("Box Fan", items, (-1.6, 0.0, 4.9))
    s.box("Fan Bucket", fan, (0.0, 0.19, 0.0), (0.3, 0.38, 0.3), (0.95, 0.42, 0.08), shape="Cylinder", rough=0.55)
    s.box("Fan Frame", fan, (0.0, 0.64, 0.0), (0.12, 0.52, 0.52), (0.82, 0.8, 0.76), rough=0.5)
    hub = s.entity("Fan Blades", fan, (0.07, 0.64, 0.0))
    motion(hub, "Spin", speed=720.0, axis=(1, 0, 0))
    for k in range(3):
        s.box(f"Blade {k}", hub, (0.0, 0.0, 0.0), (0.01, 0.42, 0.09), (0.72, 0.75, 0.8), rot=(k * 60.0, 0, 0), shadows=False)
    # Mom's camcorder, still on duty.
    base = (-0.95, 0.0, 2.95)
    s.prop("Tripod", items, "Assets/Models/Venue/CameraTripod.obj", base, yaw=30.0, scale=0.82)
    lens = (base[0] + 0.02, 1.32, base[2] + 0.05)
    target = (0.0, 0.95, 5.1)
    rig = s.entity("Camcorder", items, lens, look_rotation(lens, target))
    s.box("Camcorder Body", rig, (0.0, 0.0, -0.08), (0.09, 0.11, 0.2), (0.12, 0.12, 0.13), rough=0.4)
    rec = s.box("Rec Light", rig, (0.03, 0.06, 0.0), (0.012, 0.012, 0.012), (1, 0.05, 0.05), shape="Sphere",
                emissive=(1.0, 0.05, 0.05), emissive_intensity=10.0, shadows=False)
    motion(rec, "Blink", amount=0.5, speed=1.0)
    eye = s.entity("Camcorder View", lights, lens, look_rotation(lens, target))
    eye.add({"Type": "Camera", "IsCurrent": False, "TargetTexture": "Assets/Hideout/Camcorder.rendertexture", "UpdateInterval": 4,
             "FieldOfView": 40.0, "Near": 0.05, "Far": 14.0, "ClearType": "Color", "ClearColor": [0.02, 0.02, 0.02],
             "AmbientOcclusion": False, "VolumetricFog": False, "SunShadows": False})


def party_lights(s, lights):
    """Two strings of big bulbs across the ceiling, chasing the beat."""
    for row, (a, b) in enumerate((((-H + 0.1, 2.75, 1.4), (H - 0.1, 2.75, 2.6)), ((-H + 0.1, 2.75, 3.9), (H - 0.1, 2.75, 5.2)))):
        string = s.group(f"Party Lights {row}", lights)
        count = 16
        prev = None
        for i in range(count):
            t = i / (count - 1)
            p = tuple(a[k] + (b[k] - a[k]) * t for k in range(3))
            p = (p[0], p[1] - 0.32 * (1.0 - (2.0 * t - 1.0) ** 2), p[2])
            colour = PARTY[(i + row) % len(PARTY)]
            bulb = s.box(f"Bulb {i}", string, p, (0.07, 0.09, 0.07), colour, shape="Sphere", emissive=colour, emissive_intensity=8.0,
                         shadows=False)
            if i % 4 == 1:
                glow_light(bulb, color=colour, intensity=2.2, range_=3.0)
            motion(bulb, "Pulse", amount=0.75, speed=0.2, phase=((i % 4) + 0.5) / 4.0, music=True)
            if prev:
                rod(s, string, f"Wire {i}", prev, (p[0], p[1] + 0.04, p[2]), 0.008, (0.08, 0.08, 0.08), shadows=False)
            prev = (p[0], p[1] + 0.04, p[2])


def workbench(s, geo, items, stations, lights):
    """Left wall: the bench (the practice pad, the real one now), a big pegboard, a vise."""
    bz = 4.3
    textured(s.slab("Bench Top", geo, -H, -H + 0.7, 0.86, 0.92, bz - 0.95, bz + 0.95, (1, 1, 1), rough=0.8), "Wood", (1, 2.5))
    for dz in (-0.88, 0.88):
        s.box(f"Bench Leg {dz}", geo, (-H + 0.62, 0.43, bz + dz), (0.07, 0.86, 0.07), WOOD)
    textured(s.slab("Bench Shelf", geo, -H, -H + 0.68, 0.22, 0.25, bz - 0.9, bz + 0.9, (1, 1, 1)), "WoodDark", (1, 2.5))
    textured(s.slab("Pegboard", geo, -H, -H + 0.02, 1.05, 2.2, bz - 0.95, bz + 0.95, (1, 1, 1), rough=0.9), "Pegboard", (3.8, 2.3))
    s.prop("Toolbox", items, "Assets/Models/Venue/ToolBox.obj", (-H + 0.3, 0.25, bz - 0.5), yaw=90.0)
    s.prop("Tool Chest", items, "Assets/Models/Venue/ToolChest.obj", (-H + 0.35, 0.0, bz + 1.55), yaw=90.0)
    s.box("Vise", items, (-H + 0.62, 1.0, bz + 0.7), (0.14, 0.14, 0.2), (0.25, 0.3, 0.45), metallic=0.6, rough=0.4)
    for i, (z, colour) in enumerate(((bz - 0.7, (0.75, 0.15, 0.1)), (bz - 0.45, (0.15, 0.3, 0.7)), (bz + 0.2, (0.2, 0.2, 0.2)))):
        s.box(f"Tool {i}", items, (-H + 0.035, 1.6 + 0.1 * (i % 2), z), (0.02, 0.3, 0.05), colour, rot=(8 * (i - 1), 0, 0), metallic=0.4)
    for i, z in enumerate((bz + 0.45, bz + 0.5, bz + 0.55, bz + 0.6)):
        rod(s, items, f"Spare Stick {i}", (-H + 0.05, 1.95, z), (-H + 0.05, 1.5, z + 0.03), 0.014, (0.86, 0.72, 0.46))
    poster(s, items, "Rudiment Chart", "PosterRudiments", (-H + 0.025, 1.65, bz - 0.15), 0.4, 0.62, "+x", tilt=1.0)
    poster(s, items, "Sticky Practice", "StickyPractice", (-H + 0.03, 1.32, bz + 0.25), 0.09, 0.09, "+x", tilt=-6.0)
    station(s, stations, "Practice Pad", "PracticePad", (-H + 0.32, 1.0, bz), (1.5, 0.65, -0.6), 40)
    pad = slot(s, items, "Practice Pad", "PracticePad")
    s.box("Pad", pad, (-H + 0.34, 0.94, bz), (0.3, 0.03, 0.3), (0.12, 0.12, 0.12), shape="Cylinder", rough=0.9)
    s.box("Pad Rim", pad, (-H + 0.34, 0.93, bz), (0.32, 0.02, 0.32), (0.75, 0.1, 0.1), shape="Cylinder", rough=0.6)
    rod(s, pad, "Pad Stick L", (-H + 0.2, 0.965, bz + 0.05), (-H + 0.58, 0.965, bz - 0.05), 0.014, (0.86, 0.72, 0.46))
    met = slot(s, items, "Metronome", "Metronome")
    s.box("Metronome", met, (-H + 0.32, 1.01, bz + 0.38), (0.1, 0.18, 0.08), (0.45, 0.12, 0.08), rough=0.6)
    arm = s.entity("Metronome Arm", met, (-H + 0.32, 0.95, bz + 0.34))
    motion(arm, "Sway", amount=25.0, speed=1.0, axis=(1, 0, 0))
    s.box("Arm", arm, (0.0, 0.08, 0.0), (0.006, 0.16, 0.006), CHROME, metallic=0.9, shadows=False)
    lamp = slot(s, items, "Lava Lamp", "Lamp")
    blob = s.box("Lava", lamp, (-H + 0.3, 1.1, bz + 0.75), (0.1, 0.3, 0.1), (0.9, 0.3, 0.6), shape="Capsule",
                 emissive=(1.0, 0.25, 0.55), emissive_intensity=4.0)
    glow_light(blob, color=(1.0, 0.3, 0.6), intensity=1.5, range_=2.0)
    motion(blob, "Pulse", amount=0.3, speed=0.08)
    # Two shop lights that work (mostly).
    for i, (x, z, flicker) in enumerate(((-H + 0.6, bz, False), (1.4, 2.2, True))):
        rod(s, items, f"Shop Light Chain {i}A", (x, TOP, z - 0.5), (x, 2.48, z - 0.5), 0.006, STEEL, metallic=0.8, shadows=False)
        rod(s, items, f"Shop Light Chain {i}B", (x, TOP, z + 0.5), (x, 2.48, z + 0.5), 0.006, STEEL, metallic=0.8, shadows=False)
        s.box(f"Shop Light {i}", items, (x, 2.47, z), (0.17, 0.05, 1.25), (0.85, 0.85, 0.82), rough=0.5)
        tube = s.box(f"Tube {i}", lights, (x, 2.437, z), (0.035, 1.18, 0.035), (0.9, 0.95, 1.0), rot=(90, 0, 0), shape="Cylinder",
                     emissive=(0.85, 0.93, 1.0), emissive_intensity=5.0, shadows=False)
        glow_light(tube, color=(0.84, 0.92, 1.0), intensity=5.0 if flicker else 4.0, range_=5.0, volumetric=0.3)
        if flicker:
            motion(tube, "Flicker", amount=0.5, speed=0.5)


def left_side(s, geo, items, stations):
    """The gig board, the bikes overhead, the lawnmower, the laptop on its folding table."""
    gz = 2.6
    textured(s.slab("Gig Board", geo, -H, -H + 0.03, 1.12, 2.0, gz - 0.72, gz + 0.72, (1, 1, 1), rough=0.95), "Cork", (1.4, 0.9))
    station(s, stations, "Gig Board", "GigBoard", (-H + 0.05, 1.56, gz), (1.75, 0.0, -0.85), 45)
    poster(s, items, "Bassist Wanted", "FlyerBassist", (-H + 0.034, 1.52, gz - 0.5), 0.27, 0.36, "+x", tilt=2.5)
    poster(s, items, "Calendar", "Calendar", (-H + 0.034, 1.55, gz + 0.5), 0.3, 0.4, "+x", tilt=-1.5)
    flyers = (("FlyerA", "FlyerBackyard", 1.6, -0.1, -3.0), ("FlyerB", "FlyerClub", 1.45, 0.16, 2.0), ("FlyerC", "FlyerFestival", 1.7, 0.05, -1.5))
    for slot_name, texture, y, dz, tilt in flyers:
        f = slot(s, items, f"Flyer {slot_name[-1]}", slot_name)
        poster(s, f, "Flyer", texture, (-H + 0.038, y, gz + dz), 0.27, 0.36, "+x", tilt=tilt)
    # A bike leaning on the back wall by the mower.
    bike = s.group("Bike", items, (-2.75, 0.0, D - 0.18))
    for w in (-0.52, 0.52):
        s.box(f"Wheel {w}", bike, (w, 0.33, 0.0), (0.66, 0.03, 0.66), (0.08, 0.08, 0.08), rot=(90, 0, 0), shape="Cylinder", rough=0.7)
        s.box(f"Rim {w}", bike, (w, 0.33, 0.0), (0.5, 0.032, 0.5), CHROME, rot=(90, 0, 0), shape="Cylinder", metallic=0.9)
    rod(s, bike, "Frame Top", (-0.3, 0.75, 0.0), (0.35, 0.78, 0.0), 0.04, (0.75, 0.12, 0.1), metallic=0.5)
    rod(s, bike, "Frame Down", (-0.3, 0.75, 0.0), (0.0, 0.35, 0.0), 0.04, (0.75, 0.12, 0.1), metallic=0.5)
    rod(s, bike, "Frame Seat", (0.0, 0.35, 0.0), (0.35, 0.78, 0.0), 0.04, (0.75, 0.12, 0.1), metallic=0.5)
    rod(s, bike, "Bars", (-0.42, 0.95, -0.2), (-0.42, 0.95, 0.2), 0.03, BLACK)
    s.box("Seat", bike, (0.38, 0.84, 0.0), (0.24, 0.05, 0.1), BLACK, rough=0.8)
    # The lawnmower that paid for the cymbals, the gas can, the hose.
    mower = s.group("Lawnmower", items, (-3.0, 0.0, 6.3))
    s.box("Mower Deck", mower, (0.0, 0.18, 0.0), (0.55, 0.22, 0.6), (0.15, 0.45, 0.2), rough=0.5, metallic=0.3)
    s.box("Mower Engine", mower, (0.0, 0.38, 0.05), (0.26, 0.2, 0.26), (0.2, 0.2, 0.2), shape="Cylinder", metallic=0.5)
    rod(s, mower, "Mower Handle L", (-0.2, 0.25, -0.3), (-0.2, 1.0, -0.7), 0.025, BLACK)
    rod(s, mower, "Mower Handle R", (0.2, 0.25, -0.3), (0.2, 1.0, -0.7), 0.025, BLACK)
    for wx, wz in ((-0.28, -0.25), (0.28, -0.25), (-0.28, 0.25), (0.28, 0.25)):
        s.box(f"Mower Wheel {wx} {wz}", mower, (wx, 0.08, wz), (0.16, 0.05, 0.16), BLACK, rot=(0, 0, 90), shape="Cylinder")
    s.box("Gas Can", items, (-2.4, 0.18, 6.6), (0.25, 0.32, 0.16), (0.8, 0.12, 0.08), rough=0.5)
    s.prop("Hose", items, "Assets/Models/Venue/CableCoil.obj", (-3.3, 0.0, 5.7), yaw=20.0, scale=1.2)
    rod(s, items, "Rake", (-2.1, 0.0, 7.15), (-2.25, 1.75, 7.1), 0.03, (0.55, 0.4, 0.25))
    rod(s, items, "Shovel", (-2.35, 0.0, 7.15), (-2.45, 1.4, 7.1), 0.03, (0.55, 0.4, 0.25))
    # The laptop on a folding table, a camping chair at it.
    cx, cz = -1.6, 1.3
    s.box("Table Top", items, (cx, 0.72, cz), (0.8, 0.03, 0.55), (0.85, 0.85, 0.82), rough=0.5)
    for dx in (-0.35, 0.35):
        rod(s, items, f"Table Leg {dx}", (cx + dx, 0.0, cz - 0.2), (cx + dx, 0.71, cz + 0.2), 0.02, STEEL, metallic=0.7)
        rod(s, items, f"Table Leg B {dx}", (cx + dx, 0.0, cz + 0.2), (cx + dx, 0.71, cz - 0.2), 0.02, STEEL, metallic=0.7)
    s.box("Laptop Base", stations, (cx, 0.745, cz - 0.02), (0.34, 0.02, 0.24), (0.2, 0.2, 0.22), metallic=0.6, rough=0.4)
    textured(s.box("Laptop Screen", stations, (cx, 0.86, cz + 0.1), (0.34, 0.22, 0.012), (1, 1, 1), rot=(-12, 0, 0), rough=0.2,
                   shadows=False), "LaptopScreen", emissive=True, emissive_intensity=1.1)
    station(s, stations, "Laptop", "Laptop", (cx, 0.85, cz), (0.35, 0.5, -0.95), 40)
    s.prop("Chair", items, "Assets/Venues/Backyard/Models/PatioChair.obj", (cx + 0.1, 0.0, cz - 0.6), yaw=10.0)
    for i, (x, z, colour) in enumerate(((cx + 0.25, cz + 0.1, (0.1, 0.65, 0.2)), (cx - 0.28, cz - 0.08, (0.05, 0.05, 0.06)))):
        s.box(f"Can {i}", items, (x, 0.795, z), (0.066, 0.12, 0.066), colour, shape="Cylinder", metallic=0.8, rough=0.3)


def right_side(s, geo, items, stations, lights):
    """The couch and the cat, the boombox, the CRT, the dartboard, the fridge, the shelves, the trophies."""
    s.prop("Couch", items, "Assets/Venues/Backyard/Models/Sofa.obj", (3.2, 0.0, 2.1), yaw=-90.0)
    cat = s.group("Cat", items, (3.05, 0.5, 2.8))
    body = s.box("Cat Body", cat, (0.0, 0.08, 0.0), (0.3, 0.17, 0.44), (0.85, 0.48, 0.2), shape="Sphere", rough=0.95)
    motion(body, "Breathe", amount=0.07, speed=0.22, axis=(0.3, 1.0, 0.0))
    s.box("Cat Head", cat, (0.02, 0.1, 0.24), (0.17, 0.14, 0.15), (0.85, 0.48, 0.2), shape="Sphere", rough=0.95)
    for side in (-1, 1):
        s.box(f"Cat Ear {side}", cat, (0.02 + side * 0.05, 0.18, 0.25), (0.05, 0.05, 0.02), (0.8, 0.42, 0.18), rot=(0, 0, 45), rough=0.95)
    tail = s.entity("Cat Tail Root", cat, (-0.05, 0.03, -0.2))
    motion(tail, "Sway", amount=14.0, speed=0.13, axis=(0, 1, 0))
    rod(s, tail, "Cat Tail", (0.0, 0.0, 0.0), (0.17, -0.01, -0.12), 0.04, (0.8, 0.44, 0.18))
    # The boombox on its shelf over the couch.
    s.slab("Radio Shelf", geo, H - 0.36, H, 1.44, 1.48, 2.0, 3.0, WOOD, rough=0.8)
    radio = slot(s, items, "Radio", "Radio")
    rx, ry, rz = H - 0.18, 1.62, 2.5
    s.box("Boombox", radio, (rx, ry, rz), (0.22, 0.26, 0.66), (0.14, 0.14, 0.15), rough=0.45, metallic=0.2)
    boombox_display(s, radio, (rx - 0.112, ry + 0.095, rz), "-x")
    rod(s, radio, "Boombox Handle", (rx, ry + 0.17, rz - 0.22), (rx, ry + 0.17, rz + 0.22), 0.02, CHROME, metallic=0.9)
    for i, z in enumerate((rz - 0.2, rz + 0.2)):
        cone = s.entity(f"Speaker {i}", radio, (rx - 0.112, ry - 0.01, z))
        motion(cone, "Bob", amount=0.012, speed=2.0, axis=(-1, 0, 0), music=True)
        s.box("Cone", cone, (0.0, 0.0, 0.0), (0.18, 0.012, 0.18), (0.06, 0.06, 0.06), rot=(0, 0, 90), shape="Cylinder", rough=0.7)
    station(s, stations, "Radio", "Radio", (rx, ry, rz), (-1.45, 0.05, -0.35), 40)
    # The CRT, now on a cooler, showing the camcorder.
    tv = s.group("TV", items, (2.45, 0.0, 3.5))
    s.prop("Cooler", tv, "Assets/Models/Venue/Cooler.obj", (0.0, 0.0, 0.0), yaw=90.0, scale=0.85)
    body = s.group("TV Body", tv, (0.0, 0.0, 0.0))
    body.components[0]["Rotation"] = [0.0, -125.0, 0.0]
    s.box("Tube", body, (0.0, 0.62, 0.0), (0.52, 0.44, 0.46), (0.22, 0.21, 0.19), rough=0.55)
    screen = s.box("Screen", body, (0.0, 0.63, 0.232), (0.42, 0.32, 0.01), (1, 1, 1), rough=0.1, shadows=False)
    feed = "Assets/Hideout/Camcorder.rendertexture"
    m = screen.components[-1]["Material"]
    m["Textures"] = {"Diffuse": {"Path": feed}, "Emissive": {"Path": feed}}
    m["EmissiveColor"] = [0.85, 0.9, 1.0]
    m["EmissiveIntensity"] = 1.3
    m["Tiling"] = [1.0, -1.0]
    m["Offset"] = [0.0, 1.0]
    motion(screen, "Flicker", amount=0.35, speed=3.0)
    for side in (-1, 1):
        rod(s, body, f"Rabbit Ear {side}", (0.0, 0.84, -0.05), (side * 0.22, 1.22, -0.08), 0.008, CHROME, metallic=0.9)
    # The dartboard (darts in it, and in the wall round it).
    board = textured(s.box("Dartboard", items, (H - 0.03, 1.72, 3.85), (0.03, 0.46, 0.46), (1, 1, 1), rough=0.8), "Dartboard")
    board.components[-1]["Material"]["AlphaCutoff"] = 0.5
    for i, (y, z) in enumerate(((1.75, 3.8), (1.62, 3.95), (2.05, 4.2))):
        rod(s, items, f"Dart {i}", (H - 0.05, y, z), (H - 0.2, y + 0.02, z - 0.03), 0.012, (0.2, 0.6, 0.9))
    # The soda fridge by the house door.
    s.box("Fridge", items, (H - 0.32, 0.6, 0.2), (0.6, 1.2, 0.6), (0.86, 0.86, 0.84), rough=0.35)
    s.box("Fridge Handle", items, (H - 0.635, 0.8, 0.35), (0.02, 0.4, 0.025), CHROME, metallic=0.9)
    # Metal shelving by the door: paint cans, boxes, the Christmas decorations.
    sx = 2.75
    for level, y in enumerate((0.05, 0.6, 1.15, 1.7)):
        s.slab(f"Shelf {level}", geo, sx - 0.45, sx + 0.45, y, y + 0.03, D - 0.45, D - 0.05, STEEL, metallic=0.6, rough=0.4)
    for corner_x in (sx - 0.44, sx + 0.44):
        for corner_z in (D - 0.44, D - 0.06):
            s.box(f"Shelf Post {corner_x} {corner_z}", geo, (corner_x, 0.9, corner_z), (0.03, 1.8, 0.03), STEEL, metallic=0.6)
    rnd = random.Random(31)
    for i in range(7):
        y = 0.6 + 0.55 * (i % 2) + 0.03
        x = sx - 0.32 + 0.12 * (i % 6)
        s.box(f"Paint Can {i}", items, (x, y + 0.09, D - 0.25), (0.16, 0.18, 0.16), PAINT[i % len(PAINT)], shape="Cylinder", metallic=0.6, rough=0.4)
    textured(s.box("Box Xmas", items, (sx - 0.15, 1.15 + 0.25, D - 0.25), (0.5, 0.44, 0.36), (1, 1, 1), rot=(0, rnd.uniform(-6, 6), 0)), "BoxXmas")
    textured(s.box("Box Cables", items, (sx + 0.1, 1.7 + 0.2, D - 0.25), (0.4, 0.36, 0.34), (1, 1, 1), rot=(0, rnd.uniform(-6, 6), 0)), "BoxCables")
    textured(s.box("Box Moms", items, (sx, 0.05 + 0.24, D - 0.25), (0.6, 0.45, 0.36), (1, 1, 1)), "BoxMoms")
    # The trophy wall: the certificate, the ribbon, and room for more.
    wz = 5.0
    station(s, stations, "Trophy Wall", "TrophyWall", (H - 0.05, 1.6, wz), (-1.8, -0.05, -0.5), 52)
    poster(s, items, "Certificate", "Certificate", (H - 0.012, 1.45, wz + 0.25), 0.5, 0.375, "-x", tilt=-1.0)
    poster(s, items, "Poster Death Squad", "PosterDeathSquad", (H - 0.012, 1.95, wz - 0.85), 0.46, 0.69, "-x", tilt=2.0)
    band = slot(s, items, "Band Poster", "PosterA")
    poster(s, band, "Poster", "PosterGhostNotes", (H - 0.012, 1.55, wz - 0.4), 0.4, 0.6, "-x", tilt=-2.0)
    for slot_name, z in (("PlaqueA", wz + 0.65), ("PlaqueB", wz + 0.95)):
        p = slot(s, items, slot_name, slot_name)
        s.box("Plaque", p, (H - 0.03, 1.85, z), (0.03, 0.3, 0.24), WOOD, rough=0.6)
        s.box("Plate", p, (H - 0.05, 1.85, z), (0.01, 0.16, 0.16), GOLD, metallic=0.9, rough=0.25)
    rec = slot(s, items, "Gold Record", "GoldRecord")
    s.box("Frame", rec, (H - 0.03, 2.2, wz + 0.25), (0.03, 0.4, 0.34), BLACK, rough=0.5)
    s.box("Record", rec, (H - 0.05, 2.22, wz + 0.25), (0.26, 0.01, 0.26), GOLD, rot=(0, 0, 90), shape="Cylinder", metallic=1.0, rough=0.15)
    head = slot(s, items, "Signed Snare Head", "WallLeft")
    s.box("Signed Head", head, (H - 0.03, 2.25, wz - 0.4), (0.3, 0.01, 0.3), WHITE, rot=(0, 0, 90), shape="Cylinder", rough=0.6)
    shelf = slot(s, items, "Vinyl Shelf", "Shelf")
    s.slab("Vinyl Shelf", shelf, H - 0.3, H, 0.0, 0.62, 4.1, 4.6, WOOD, rough=0.8)
    for i in range(7):
        s.box(f"Sleeve {i}", shelf, (H - 0.15, 0.45, 4.15 + i * 0.065), (0.25, 0.3, 0.02),
              [(0.8, 0.2, 0.2), (0.2, 0.5, 0.8), (0.9, 0.8, 0.2), (0.1, 0.1, 0.1)][i % 4], rough=0.7)


def wishlist(s, items, stations):
    """The gear list, taped to the back wall over the bike (HideoutReadout Wishlist)."""
    x, y, z = -2.62, 1.5, D - 0.012
    page = s.group("Wishlist", items, (x, y, z))
    textured(s.box("Wishlist Page", page, (0.0, 0.0, 0.0), (0.27, 0.35, 0.003), (1, 1, 1), rot=(0, 0, -2.0), rough=0.9, shadows=False),
             "Notebook", emissive=True, emissive_intensity=0.3)
    for k, dx in enumerate((-0.09, 0.09)):
        s.box(f"Wishlist Tape {k}", page, (dx, 0.17, -0.002), (0.08, 0.025, 0.002), (0.86, 0.8, 0.62), rot=(0, 0, 18 - 36 * k), shadows=False)
    wishes = ("practice-pad", "metronome", "stick-bag", "spare-cymbal", "neon-sign", "lava-lamp", "vinyl-shelf", "acoustic-foam", "gold-record")
    for i, item in enumerate(wishes):
        readout(scrawl(s, page, f"Wish {i}", (-0.098, 0.104 - i * 0.0202, -0.003), "", 0.017, (0.12, 0.16, 0.42), align="Left", anchor="Bottom",
                       tilt=-2.0), "Wishlist", item=item)
    scrawl(s, page, "Wishlist Footnote", (0.02, -0.165, -0.003), "(birthday??)", 0.014, (0.55, 0.08, 0.08), tilt=3.0)
    station(s, stations, "Wishlist", "Wishlist", (x, y, z), (0.3, 0.05, -0.85), 38)


def stand_ins(s, items):
    """Where the gear will go, until it comes."""
    tape = (0.86, 0.8, 0.62)
    ink = (0.12, 0.16, 0.42)
    red = (0.62, 0.08, 0.08)
    bz = 4.3
    pad = stand_in(s, items, "Practice Pad Goes Here", "PracticePad")
    tape_outline(s, pad, "Pad Tape", (-H + 0.34, 0.9215, bz), 0.3, 0.3)
    scrawl(s, pad, "Pad Note", (-H + 0.34, 0.923, bz), "PAD\nhere", 0.075, (0.05, 0.05, 0.06), facing="up", spin=-90.0, font=MARKER)
    met = stand_in(s, items, "Metronome Note", "Metronome")
    s.box("Sticky", met, (-H + 0.026, 1.25, bz + 0.6), (0.003, 0.09, 0.09), (0.98, 0.9, 0.36), rot=(5, 0, 0), shadows=False)
    scrawl(s, met, "Sticky Text", (-H + 0.029, 1.25, bz + 0.6), "buy a\nMETRONOME", 0.016, ink, facing="+x", tilt=5.0)
    neon = stand_in(s, items, "Neon Goes Here", "Neon")
    tape_outline(s, neon, "Neon Tape", (-2.6, 2.3, D - 0.03), 0.84, 0.22, facing="-z", colour=tape)
    scrawl(s, neon, "Neon Note", (-2.6, 2.3, D - 0.035), "NEON (SOMEDAY)", 0.06, red, font=MARKER, tilt=2.0)
    wz = 5.0
    record = stand_in(s, items, "Gold Record Goes Here", "GoldRecord")
    tape_outline(s, record, "Record Tape", (H - 0.012, 2.2, wz + 0.25), 0.34, 0.4, facing="-x", colour=tape)
    scrawl(s, record, "Record Note", (H - 0.015, 2.21, wz + 0.25), "GOLD\nRECORD\nhere", 0.075, red, facing="-x", font=MARKER, tilt=3.0)
    for slot_name, z, text in (("PlaqueA", wz + 0.65, "FC\nplaque"), ("PlaqueB", wz + 0.95, "teacher\ncert.")):
        p = stand_in(s, items, f"{slot_name} Goes Here", slot_name)
        tape_outline(s, p, f"{slot_name} Tape", (H - 0.012, 1.85, z), 0.24, 0.3, facing="-x", colour=tape, tape=0.018)
        scrawl(s, p, f"{slot_name} Note", (H - 0.015, 1.85, z), text, 0.05, ink, facing="-x", font=MARKER)
    band = stand_in(s, items, "Band Poster Goes Here", "PosterA")
    tape_outline(s, band, "Poster Tape", (H - 0.012, 1.55, wz - 0.4), 0.4, 0.6, facing="-x", colour=tape)
    scrawl(s, band, "Poster Note", (H - 0.015, 1.58, wz - 0.4), "OUR\nPOSTER\nHERE", 0.1, red, facing="-x", font=MARKER, tilt=-4.0)
    gz = 2.6
    for slot_name, y, dz, text in (("FlyerA", 1.6, -0.1, "GIG #1\n???"), ("FlyerB", 1.45, 0.16, "a REAL\ngig"), ("FlyerC", 1.7, 0.05, "FEST\n(lol)")):
        card = stand_in(s, items, f"{slot_name} Card", slot_name)
        s.box("Index Card", card, (-H + 0.036, y, gz + dz), (0.003, 0.11, 0.16), (0.97, 0.96, 0.9), rot=(-3, 0, 0), shadows=False)
        scrawl(s, card, "Card Text", (-H + 0.039, y, gz + dz), text, 0.034, ink, facing="+x", tilt=-3.0, font=MARKER)
    tally(s, items, (H - 0.012, 1.1, wz + 0.62), "-x")
    # A clock over the shelves, on the player's time.
    cx, cy, cz = 2.75, 2.45, D - 0.02
    s.box("Clock", items, (cx, cy, cz), (0.32, 0.32, 0.03), OFFWHITE, rot=(90, 0, 0), shape="Cylinder", rough=0.5)
    s.box("Clock Rim", items, (cx, cy, cz + 0.005), (0.35, 0.35, 0.02), BLACK, rot=(90, 0, 0), shape="Cylinder", rough=0.5)
    import math
    for k in range(12):
        a = math.radians(k * 30)
        s.box(f"Clock Tick {k}", items, (cx + 0.13 * math.sin(a), cy + 0.13 * math.cos(a), cz - 0.016), (0.006, 0.02 if k % 3 == 0 else 0.01, 0.003),
              BLACK, rot=(0, 0, -k * 30), shadows=False)
    clock_hands(s, items, (cx, cy, cz - 0.016), "-z", 0.15)


def moving_in(s, items):
    """The first visit: the basement's boxes by the house door, and the dolly that brought them."""
    boxes = when(s.group("Moving Boxes", items), "MovingIn")
    textured(s.box("Box Drums", boxes, (-1.95, 0.24, 0.3), (0.6, 0.48, 0.48), (1, 1, 1), rot=(0, 10, 0), rough=0.9), "BoxDrums")
    textured(s.box("Box Stuff", boxes, (-1.9, 0.66, 0.32), (0.44, 0.36, 0.4), (1, 1, 1), rot=(0, -6, 0), rough=0.9), "BoxStuff")
    textured(s.box("Box Fragile", boxes, (0.5, 0.2, 1.3), (0.5, 0.4, 0.42), (1, 1, 1), rot=(0, 25, 0), rough=0.9), "BoxFragile")
    textured(s.box("Box Cables 2", boxes, (0.95, 0.2, 1.05), (0.42, 0.4, 0.42), (1, 1, 1), rot=(0, -15, 0), rough=0.9), "BoxCables")
    dolly = s.group("Dolly", boxes, (-1.2, 0.0, 0.7))
    rod(s, dolly, "Dolly Rail L", (-0.18, 0.05, 0.0), (-0.18, 1.2, 0.25), 0.03, (0.75, 0.1, 0.08), metallic=0.5)
    rod(s, dolly, "Dolly Rail R", (0.18, 0.05, 0.0), (0.18, 1.2, 0.25), 0.03, (0.75, 0.1, 0.08), metallic=0.5)
    s.box("Dolly Plate", dolly, (0.0, 0.03, -0.1), (0.42, 0.02, 0.22), STEEL, metallic=0.7)
    for w in (-0.22, 0.22):
        s.box(f"Dolly Wheel {w}", dolly, (w, 0.1, 0.05), (0.2, 0.05, 0.2), BLACK, rot=(0, 0, 90), shape="Cylinder")


def front(s, geo, items, lights):
    """The house door (open a crack, the kitchen light on), the extras, a fill."""
    s.slab("House Door Frame", geo, -3.2, -2.3, 0.0, 2.1, -1.62, -1.55, (0.75, 0.7, 0.62), rough=0.6)
    door = s.group("House Door", geo, (-3.15, 0.0, -1.55))
    door.components[0]["Rotation"] = [0.0, 35.0, 0.0]
    s.box("Door", door, (0.42, 1.03, 0.0), (0.84, 2.05, 0.04), (0.72, 0.68, 0.6), rough=0.6)
    light(s, lights, "Kitchen", (-2.75, 1.8, -2.1), color=(1.0, 0.82, 0.58), intensity=6.0, range_=4.5)
    light(s, geo, "Fill", (0.3, 1.4, 0.4), color=(1.0, 0.85, 0.66), intensity=1.6, range_=4.5)
    rug = slot(s, items, "Rug", "Rug")
    s.box("Rug", rug, (0.0, 0.013, 4.7), (2.6, 0.01, 2.3), (0.35, 0.18, 0.12), rough=1.0, shadows=False)
    bag = slot(s, items, "Stick Bag", "StickBag")
    s.box("Bag", bag, (0.72, 0.45, 4.5), (0.06, 0.4, 0.14), (0.1, 0.1, 0.12), rough=0.9)
    spare = slot(s, items, "Spare Cymbal", "CymbalStand")
    rod(s, spare, "Stand", (-1.0, 0.0, 5.5), (-1.0, 1.18, 5.5), 0.025, CHROME, metallic=0.9)
    s.box("Cymbal", spare, (-1.0, 1.2, 5.5), (0.42, 0.012, 0.42), BRASS, rot=(-14, 0, 0), shape="Cylinder", metallic=0.9, rough=0.25)
    neon = slot(s, items, "Neon Sign", "Neon")
    sign = s.box("Neon", neon, (-2.6, 2.3, D - 0.04), (0.8, 0.18, 0.02), (0.2, 0.05, 0.1), emissive=(1.0, 0.15, 0.55),
                 emissive_intensity=5.0, shadows=False)
    glow_light(sign, color=(1.0, 0.2, 0.6), intensity=2.0, range_=3.0)
    foam = slot(s, items, "Acoustic Foam", "Foam")
    for i in range(4):
        for j in range(3):
            s.box(f"Foam {i}.{j}", foam, (-H + 0.04, 1.0 + j * 0.5, 0.6 + i * 0.5), (0.06, 0.46, 0.46), (0.1, 0.1, 0.12), rough=1.0, shadows=False)
    desk = slot(s, items, "Mixing Desk", "Desk")
    s.box("Desk", desk, (1.1, 0.8, 1.2), (1.0, 0.1, 0.55), (0.15, 0.15, 0.16), rot=(-10, 0, 0), rough=0.4)


def build_garage():
    s = Scene(seed=2102)
    root = s.group("Hideout Garage")
    geo = s.group("Room", root)
    items = s.group("Things", root)
    stations = s.group("Stations", root)
    lights = s.group("Lights", root)
    marks = s.group("Markers", root)
    shell(s, geo)
    door(s, geo, lights, items)
    kit_area(s, geo, items, stations, lights)
    party_lights(s, lights)
    workbench(s, geo, items, stations, lights)
    left_side(s, geo, items, stations)
    right_side(s, geo, items, stations, lights)
    front(s, geo, items, lights)
    wishlist(s, items, stations)
    stand_ins(s, items)
    moving_in(s, items)
    tone = s.group("Room Tone", root)
    sound(s, tone, "Tube Buzz", (1.4, 2.44, 2.2), "TubeBuzz", volume=0.12, near=0.4, far=4.5)
    sound(s, tone, "Fan Whir", (-1.6, 0.64, 4.9), "FanWhir", volume=0.35, near=0.6, far=6.0)
    view(s, marks, (0.2, 1.62, -1.5), (0.0, 1.0, 5.2), 60.0, intro_eye=(-2.75, 1.65, -1.9), intro_target=(-0.4, 1.0, 3.0))
    return s
