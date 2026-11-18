"""The rehearsal space, the hideout's third room (Assets/Hideout/Rehearsal.lvl): Room 14 of a
lockout complex, rented by the month after the club booking.

Black-painted block, wedge foam in squares behind the kit, moving blankets nailed up on the left,
a drop ceiling with a few tiles missing and a water stain. The kit on a carpeted riser under a
printed vinyl banner (the band's name once it has one), a guitar half-stack and a bass fridge
either side, a PA on tripods, two PAR cans on a T-bar throwing red and blue at the drummer on the
beat. The steel door is open on the hallway (a tube flickering out there, a vending machine down
the far end); a frosted transom high on the left wall shows day or the sodium night. The lounge on
the right: a beat couch, a road case for a coffee table (the laptop on it), the fridge, the radio
on top. The whiteboard has the week's bookings with the band's name on Mondays and Thursdays, the
gear list taped to its corner; the landlord's rules by the door. Through the right wall, the band
next door.

Room space as the other rooms: x across (+x the lounge side), y up, z from the door (the camera)
to the back wall.
"""
import math
import random

from hideoutgen import (band_name, band_name_text, BLACK, BRASS, CHROME, GOLD, MARKER, OFFWHITE, STEEL, WHITE, WOOD, Scene, boombox_display,
                        clock_hands, drummer, dust, glow_light, light, look_rotation, motion, poster, readout, rod, scrawl, setlist, slot, sound,
                        stand_in, station, tally, tape_outline, textured, view, when)

H = 3.9        # half the width
D = 7.4        # the back wall's face
TOP = 2.8      # the drop ceiling
RISER = 0.2    # the drum riser's height
DOOR = (-0.75, 0.35)   # the doorway in the front wall (x)

PAINT_PEN = (0.92, 0.92, 0.88)    # a white paint pen on black walls
INK = (0.12, 0.16, 0.42)
RED = (0.62, 0.08, 0.08)
TOLEX = (0.05, 0.05, 0.055)


def road_case(s, parent, name, centre, size, yaw=0.0):
    """A black road case: aluminium edging, corner caps, latches. centre is its footprint's middle."""
    group = s.group(name, parent, centre)
    group.components[0]["Rotation"] = [0.0, yaw, 0.0]
    w, h, d = size
    s.box("Body", group, (0.0, h / 2, 0.0), (w, h, d), (0.06, 0.06, 0.065), rough=0.6)
    alu = (0.7, 0.72, 0.74)
    for y in (0.02, h - 0.02):
        s.box(f"Edge Front {y}", group, (0.0, y, -d / 2 - 0.004), (w + 0.01, 0.03, 0.012), alu, metallic=0.8, rough=0.35)
        s.box(f"Edge Back {y}", group, (0.0, y, d / 2 + 0.004), (w + 0.01, 0.03, 0.012), alu, metallic=0.8, rough=0.35)
    s.box("Lid Seam", group, (0.0, h * 0.7, -d / 2 - 0.005), (w + 0.01, 0.025, 0.012), alu, metallic=0.8, rough=0.35)
    for dx in (-w / 2, w / 2):
        for dz in (-d / 2, d / 2):
            for y in (0.03, h - 0.03):
                s.box(f"Corner {dx} {dz} {y}", group, (dx, y, dz), (0.06, 0.06, 0.06), (0.8, 0.8, 0.82), shape="Sphere", metallic=0.8, rough=0.3)
    for dx in (-w / 4, w / 4):
        s.box(f"Latch {dx}", group, (dx, h * 0.7, -d / 2 - 0.012), (0.08, 0.05, 0.015), alu, metallic=0.9, rough=0.3)
    return group


def shell(s, geo):
    textured(s.slab("Floor", geo, -H, H, -0.1, 0.0, -1.6, D, (1, 1, 1), rough=0.8), "ConcreteFloor", (3.9, 4.5), tint=(0.62, 0.62, 0.66))
    textured(s.slab("Back Wall", geo, -H, H, 0.0, TOP, D, D + 0.12, (1, 1, 1), rough=0.95), "BlackWall", (4.9, 3.5))
    for name, x0, x1 in (("Left Wall", -H - 0.12, -H), ("Right Wall", H, H + 0.12)):
        textured(s.slab(name, geo, x0, x1, 0.0, TOP, -1.6, D, (1, 1, 1), rough=0.95), "BlackWall", (5.6, 3.5))
    for name, x0, x1 in (("Front Wall Left", -H, DOOR[0]), ("Front Wall Right", DOOR[1], H)):
        textured(s.slab(name, geo, x0, x1, 0.0, TOP, -1.72, -1.6, (1, 1, 1), rough=0.95), "BlackWall", ((x1 - x0) / 1.6, 3.5))
    s.slab("Door Header", geo, DOOR[0], DOOR[1], 2.1, TOP, -1.72, -1.6, (0.16, 0.16, 0.18), rough=0.9)
    # The drop ceiling: tiles in their grid, a few gone (black above), one stained. It casts
    # shadows (keeps the engine's sun out).
    textured(s.slab("Ceiling", geo, -H, H, TOP, TOP + 0.03, -1.72, D + 0.12, (1, 1, 1), rough=0.95), "CeilingTile", (13.0, 15.2))
    for i, (x, z) in enumerate(((-2.1, 1.5), (1.5, 5.1), (2.7, 0.3))):
        s.box(f"Missing Tile {i}", geo, (x, TOP - 0.002, z), (0.58, 0.004, 0.58), (0.01, 0.01, 0.012), rough=1.0, shadows=False)
    s.box("Water Stain", geo, (-0.9, TOP - 0.002, 3.2), (0.7, 0.004, 0.55), (0.55, 0.42, 0.25), shape="Cylinder", rough=1.0, shadows=False)
    # The baseboard, a cable tray along the left wall, conduit to the outlets.
    for name, x in (("Baseboard Left", -H + 0.01), ("Baseboard Right", H - 0.01)):
        s.slab(name, geo, x - 0.01, x + 0.01, 0.0, 0.1, -1.6, D, (0.12, 0.12, 0.13))
    rod(s, geo, "Conduit", (-H + 0.03, 2.6, -1.6), (-H + 0.03, 2.6, D), 0.025, STEEL, metallic=0.7)
    for z in (0.8, 3.0, 5.6):
        s.box(f"Outlet {z}", geo, (-H + 0.01, 0.4, z), (0.02, 0.12, 0.08), (0.75, 0.73, 0.68))
        rod(s, geo, f"Conduit Drop {z}", (-H + 0.03, 2.6, z), (-H + 0.03, 0.46, z), 0.02, STEEL, metallic=0.7)


def door_and_hallway(s, geo, items, lights):
    """The steel door, open; the hallway's tube flickering; the vending machine down the end."""
    door = s.group("Steel Door", geo, (DOOR[0], 0.0, -1.66))
    door.components[0]["Rotation"] = [0.0, -100.0, 0.0]
    s.box("Door Leaf", door, (0.55, 1.03, 0.0), (1.08, 2.06, 0.05), (0.32, 0.34, 0.36), metallic=0.5, rough=0.45)
    s.box("Door Window", door, (0.55, 1.5, -0.028), (0.2, 0.36, 0.006), (0.4, 0.45, 0.5), rough=0.15, metallic=0.2)
    s.box("Door Handle", door, (0.95, 1.0, -0.05), (0.14, 0.03, 0.03), CHROME, metallic=0.9)
    s.box("Kick Plate", door, (0.55, 0.12, -0.028), (1.0, 0.22, 0.006), CHROME, metallic=0.8, rough=0.3)
    scrawl(s, door, "Room Number", (0.55, 1.86, -0.032), "14", 0.12, PAINT_PEN, facing="-z", font=MARKER)
    # The hallway: linoleum, block walls, a tube over the door that won't make up its mind.
    s.slab("Hall Floor", geo, -3.0, 3.0, -0.1, 0.0, -4.6, -1.72, (0.42, 0.4, 0.36), rough=0.5)
    s.slab("Hall Ceiling", geo, -3.0, 3.0, 2.6, 2.7, -4.6, -1.72, (0.6, 0.6, 0.58))
    textured(s.slab("Hall Wall", geo, -3.0, 3.0, 0.0, 2.6, -4.7, -4.6, (1, 1, 1), rough=0.9), "ConcreteBlock", (3.75, 3.25), tint=(0.8, 0.82, 0.8))
    tube = s.box("Hall Tube", lights, (-0.2, 2.56, -2.6), (0.035, 1.2, 0.035), (0.9, 0.95, 1.0), rot=(0, 0, 90), shape="Cylinder",
                 emissive=(0.85, 0.93, 1.0), emissive_intensity=5.0, shadows=False)
    glow_light(tube, color=(0.75, 0.88, 1.0), intensity=6.0, range_=4.5)
    motion(tube, "Flicker", amount=0.85, speed=0.8)
    vend = s.group("Vending Machine", geo, (2.4, 0.0, -4.2))
    s.box("Vend Body", vend, (0.0, 0.9, 0.0), (0.9, 1.8, 0.7), (0.62, 0.08, 0.1), rough=0.4, metallic=0.2)
    panel = s.box("Vend Panel", vend, (-0.1, 1.05, 0.355), (0.55, 1.2, 0.01), (0.9, 0.9, 0.85), emissive=(1.0, 0.95, 0.85), emissive_intensity=2.5,
                  shadows=False)
    glow_light(panel, color=(1.0, 0.92, 0.8), intensity=2.0, range_=3.0)
    poster(s, items, "Rules", "RulesSign", (DOOR[1] + 0.55, 1.5, -1.59), 0.36, 0.48, "+z")


def riser_and_kit(s, geo, items, stations, lights):
    """The carpeted riser, the drummer, the banner, the foam behind them."""
    rz0, rz1 = 5.15, 7.3
    textured(s.slab("Riser", geo, -1.5, 1.5, 0.0, RISER, rz0, rz1, (1, 1, 1), rough=1.0), "CarpetDark", (1.5, 1.1))
    s.slab("Riser Edge", geo, -1.52, 1.52, 0.0, RISER, rz0 - 0.02, rz0, (0.1, 0.1, 0.11), rough=0.9)
    s.box("Riser Gaffer", geo, (0.0, RISER + 0.001, rz0 + 0.03), (2.9, 0.002, 0.05), (0.9, 0.85, 0.2), rough=0.8, shadows=False)
    throne = 6.35
    drummer(s, items, (0.0, RISER, throne), yaw=180.0)
    station(s, stations, "Kit", "Kit", (0.0, 0.78, 5.3), (0.3, 1.05, -2.1), 42)
    # The kick head: the band's name, as in the basement.
    kz = throne - 1.152
    head = textured(s.box("Kick Logo", items, (0.0, RISER + 0.31, kz), (0.56, 0.56, 0.004), (1, 1, 1), rough=0.7, shadows=False),
                    "KickHead", emissive=True, emissive_intensity=0.25)
    head.components[-1]["Material"]["AlphaCutoff"] = 0.5
    band_name(head, "Unnamed")
    blank = textured(s.box("Kick Logo Blank", items, (0.0, RISER + 0.31, kz - 0.001), (0.56, 0.56, 0.004), (1, 1, 1), rough=0.7, shadows=False),
                     "KickHeadBlank", emissive=True, emissive_intensity=0.25)
    blank.components[-1]["Material"]["AlphaCutoff"] = 0.5
    band_name(blank, "Named")
    band_name_text(s, items, "Band Name On The Kick", (0.0, RISER + 0.34, kz - 0.008), 0.07, (0.08, 0.08, 0.1), fit=9)
    # The banner: the band's name printed on vinyl (the shop's sample until there is one).
    band_name(poster(s, items, "Vinyl Banner", "VinylBanner", (0.0, 1.95, D - 0.02), 3.2, 1.2, "-z", thick=0.006), "Unnamed")
    band_name(poster(s, items, "Vinyl Banner Blank", "VinylBannerBlank", (0.0, 1.95, D - 0.021), 3.2, 1.2, "-z", thick=0.006), "Named")
    band_name_text(s, items, "Band Name On The Banner", (0.0, 2.0, D - 0.03), 0.42, (0.95, 0.95, 0.95), fit=12, weight=3,
                   font="Assets/Fonts/Inter-Regular.ttf")
    # Foam squares either side of the banner.
    for side in (-1, 1):
        for i in range(3):
            for j in range(4):
                x = side * (1.85 + i * 0.6)
                textured(s.box(f"Foam {side} {i} {j}", items, (x, 0.45 + j * 0.6, D - 0.04), (0.58, 0.58, 0.07), (1, 1, 1), rough=1.0, shadows=False),
                         "FoamWedge", (0.5, 0.5))
    # The setlist taped to the riser's carpet, the stick bag, the spare cymbal.
    setlist(s, items, (0.75, RISER + 0.002, 5.42), -15.0)
    bag = slot(s, items, "Stick Bag", "StickBag")
    s.box("Bag", bag, (0.72, RISER + 0.45, 6.05), (0.06, 0.42, 0.15), (0.1, 0.1, 0.12), rough=0.9)
    for i in range(4):
        rod(s, bag, f"Bag Stick {i}", (0.72, RISER + 0.5, 6.0 + i * 0.03), (0.72, RISER + 0.75, 6.0 + i * 0.03), 0.014, (0.86, 0.72, 0.46))
    spare = slot(s, items, "Spare Cymbal", "CymbalStand")
    rod(s, spare, "Stand", (-1.15, RISER, 6.9), (-1.15, RISER + 1.3, 6.9), 0.025, CHROME, metallic=0.9)
    s.box("Cymbal", spare, (-1.15, RISER + 1.32, 6.9), (0.46, 0.012, 0.46), BRASS, rot=(-16, 0, 0), shape="Cylinder", metallic=0.9, rough=0.25)
    rug = slot(s, items, "Rug", "Rug")
    textured(s.box("Drum Rug", rug, (0.0, RISER + 0.012, 6.2), (2.5, 0.01, 2.0), (1, 1, 1), rough=1.0, shadows=False), "RugRed")
    # The PAR cans on a T-bar either side, gelled red and blue, hitting on the beat.
    for side, colour, phase in ((-1, (1.0, 0.12, 0.08), 0.125), (1, (0.15, 0.3, 1.0), 0.625)):
        base = (side * 2.0, 0.0, 5.0)
        rod(s, items, f"T-Bar Stand {side}", base, (base[0], 2.1, base[2]), 0.035, BLACK, metallic=0.5)
        rod(s, items, f"T-Bar {side}", (base[0] - 0.3, 2.1, base[2]), (base[0] + 0.3, 2.1, base[2]), 0.03, BLACK, metallic=0.5)
        for k in (-1, 1):
            can = (base[0] + k * 0.22, 2.0, base[2])
            aim = (0.0, 1.1, 6.2)
            pitch, yaw, _ = look_rotation(can, aim)
            s.box(f"PAR {side} {k}", items, can, (0.2, 0.3, 0.2), BLACK, rot=(pitch + 90.0, yaw, 0.0), shape="Cylinder", metallic=0.6, rough=0.4)
            lens = (can[0] + (aim[0] - can[0]) * 0.03, can[1] + (aim[1] - can[1]) * 0.03, can[2] + (aim[2] - can[2]) * 0.03)
            beam = light(s, lights, f"PAR Beam {side} {k}", lens, kind="Spot", color=colour, intensity=30.0, range_=7.0,
                         rot=look_rotation(lens, aim), inner=10.0, outer=20.0, volumetric=6.0)
            motion(beam, "Pulse", amount=0.65, speed=0.3, phase=phase + 0.25 * (k + 1), music=True)
            glass = s.box(f"PAR Lens {side} {k}", lights, lens, (0.17, 0.01, 0.17), colour, rot=(pitch + 90.0, yaw, 0.0), shape="Cylinder",
                          emissive=colour, emissive_intensity=6.0, shadows=False)
            motion(glass, "Pulse", amount=0.8, speed=0.3, phase=phase + 0.25 * (k + 1), music=True)
    # A red LED strip along the top of the back wall.
    strip = s.box("LED Strip", lights, (0.0, TOP - 0.06, D - 0.02), (2 * H - 0.2, 0.02, 0.01), (1.0, 0.1, 0.12), emissive=(1.0, 0.08, 0.12),
                  emissive_intensity=6.0, shadows=False)
    motion(strip, "Pulse", amount=0.5, speed=0.15, music=True)
    for x in (-2.6, 0.0, 2.6):
        glow = light(s, lights, f"LED Wash {x}", (x, TOP - 0.15, D - 0.25), color=(1.0, 0.12, 0.15), intensity=2.5, range_=3.0)
        motion(glow, "Pulse", amount=0.5, speed=0.15, music=True)


def amps(s, geo, items, stations, lights):
    """The guitarist's half-stack on the left, the bassist's fridge on the right, the PA and its mixer."""
    def cab(name, parent, centre, size, grille=(0.16, 0.14, 0.12)):
        x, y, z = centre
        s.box(name, parent, centre, size, TOLEX, rough=0.7)
        s.box(f"{name} Grille", parent, (x, y, z - size[2] / 2 - 0.004), (size[0] - 0.08, size[1] - 0.08, 0.006), grille, rough=0.95)
        for dx in (-size[0] / 2 + 0.03, size[0] / 2 - 0.03):
            for dy in (-size[1] / 2 + 0.03, size[1] / 2 - 0.03):
                s.box(f"{name} Corner {dx} {dy}", parent, (x + dx, y + dy, z - size[2] / 2 - 0.005), (0.05, 0.05, 0.01), CHROME, metallic=0.9)

    def head(name, parent, centre, size, panel, light_colour):
        x, y, z = centre
        s.box(name, parent, centre, size, TOLEX, rough=0.7)
        s.box(f"{name} Panel", parent, (x, y + 0.02, z - size[2] / 2 - 0.004), (size[0] - 0.06, 0.07, 0.006), panel, metallic=0.7, rough=0.3)
        for i in range(6):
            s.box(f"{name} Knob {i}", parent, (x - size[0] / 2 + 0.12 + i * 0.07, y + 0.02, z - size[2] / 2 - 0.012), (0.03, 0.02, 0.03), BLACK,
                  rot=(90, 0, 0), shape="Cylinder")
        lamp = s.box(f"{name} Jewel", parent, (x + size[0] / 2 - 0.07, y + 0.02, z - size[2] / 2 - 0.01), (0.025, 0.025, 0.012), light_colour,
                     shape="Sphere", emissive=light_colour, emissive_intensity=10.0, shadows=False)
        return lamp

    # Guitar: a 4x12 and a head, a guitar on a stand.
    gx, gz = -2.5, 6.85
    cab("Guitar Cab", items, (gx, 0.39, gz), (0.76, 0.76, 0.36))
    jewel = head("Guitar Head", items, (gx, 0.92, gz), (0.74, 0.27, 0.26), GOLD, (1.0, 0.12, 0.08))
    glow_light(jewel, color=(1.0, 0.3, 0.15), intensity=1.2, range_=1.8)
    light(s, lights, "Guitar Corner", (gx + 0.5, 1.6, gz - 0.9), color=(1.0, 0.7, 0.45), intensity=2.5, range_=2.6)
    s.box("Head Logo", items, (gx, 1.0, gz - 0.135), (0.22, 0.04, 0.004), (0.9, 0.85, 0.7), metallic=0.6)
    guitar = s.entity("Guitar", items, (-1.85, 0.62, 6.55), (0.0, 160.0, -78.0))
    guitar.add({"Type": "Model", "ModelPath": "Assets/Models/Instruments/Runtime/Guitar.obj"})
    rod(s, items, "Guitar Stand", (-1.9, 0.0, 6.6), (-1.85, 0.5, 6.58), 0.02, BLACK)
    # Bass: an 8x10 fridge and a head.
    bx, bz = 2.55, 6.95
    cab("Bass Cab", items, (bx, 0.66, bz), (0.62, 1.3, 0.44))
    jewel = head("Bass Head", items, (bx, 1.45, bz), (0.6, 0.24, 0.3), (0.75, 0.75, 0.78), (0.2, 0.5, 1.0))
    glow_light(jewel, color=(0.3, 0.55, 1.0), intensity=1.2, range_=1.8)
    light(s, lights, "Bass Corner", (bx - 0.5, 1.9, bz - 0.9), color=(0.8, 0.85, 1.0), intensity=2.5, range_=2.6)
    bass = s.entity("Bass", items, (1.95, 0.64, 6.6), (0.0, 200.0, -80.0))
    bass.add({"Type": "Model", "ModelPath": "Assets/Models/Instruments/Runtime/Bass.obj"})
    # The PA: tops on tripods at the riser's corners, angled at the room.
    for side in (-1, 1):
        base = (side * 1.7, 0.0, 4.95)
        for k in range(3):
            a = math.radians(120 * k + 30)
            rod(s, items, f"PA Leg {side} {k}", (base[0] + 0.35 * math.cos(a), 0.0, base[2] + 0.35 * math.sin(a)), (base[0], 0.6, base[2]), 0.02, BLACK)
        rod(s, items, f"PA Pole {side}", (base[0], 0.6, base[2]), (base[0], 1.55, base[2]), 0.035, BLACK, metallic=0.5)
        top = s.group(f"PA Top {side}", items, (base[0], 1.95, base[2]))
        top.components[0]["Rotation"] = [0.0, round(180.0 - side * 18.0, 3), 0.0]
        s.box("Box", top, (0.0, 0.0, 0.0), (0.46, 0.75, 0.42), TOLEX, rough=0.6)
        s.box("Grille", top, (0.0, 0.0, 0.215), (0.42, 0.7, 0.01), (0.12, 0.12, 0.13), metallic=0.5, rough=0.5)
        led = s.box("Power LED", top, (0.17, -0.32, 0.222), (0.012, 0.012, 0.006), (0.1, 1.0, 0.2), shape="Sphere", emissive=(0.1, 1.0, 0.2),
                    emissive_intensity=10.0, shadows=False)
    # The mixer on a road case, right of the riser: the settings.
    mx, mz = 2.45, 5.0
    road_case(s, items, "Mixer Case", (mx, 0.0, mz), (0.75, 0.62, 0.6))
    desk = s.group("PA Mixer", stations, (mx, 0.66, mz))
    desk.components[0]["Rotation"] = [0.0, -90.0, 0.0]
    s.box("Mixer Body", desk, (0.0, 0.05, 0.0), (0.62, 0.1, 0.45), (0.16, 0.16, 0.18), rot=(-12, 0, 0), metallic=0.4, rough=0.4)
    for i in range(8):
        for j in range(4):
            s.box(f"Knob {i} {j}", desk, (-0.26 + i * 0.075, 0.115 + j * 0.018, 0.12 - j * 0.07), (0.02, 0.02, 0.02),
                  [(0.9, 0.2, 0.2), (0.9, 0.8, 0.2), (0.2, 0.6, 0.9), (0.85, 0.85, 0.85)][j], shape="Cylinder")
        meter = s.box(f"Meter {i}", desk, (-0.26 + i * 0.075, 0.11, -0.14), (0.012, 0.004, 0.08), (0.2, 1.0, 0.3), emissive=(0.2, 1.0, 0.3),
                      emissive_intensity=4.0, shadows=False)
        motion(meter, "Pulse", amount=0.9, speed=0.4, phase=((i % 4) + 0.5) / 4.0, music=True)
    station(s, stations, "Mixer", "Mixer", (mx, 0.85, mz), (-0.75, 0.6, -1.35), 45, label="SETTINGS")
    # The vocal mic in front of the riser, its cable away across the floor.
    s.prop("Vocal Mic", items, "Assets/Models/Instruments/Runtime/MicStand.obj", (0.4, 0.0, 4.4), yaw=200.0)
    s.prop("Cable Run", items, "Assets/Models/Venue/CableA.obj", (1.2, 0.0, 4.3), yaw=70.0)
    s.prop("Cable Coil", items, "Assets/Models/Venue/CableCoil.obj", (-1.25, 0.0, 4.6), yaw=15.0)
    wedge = s.group("Wedge", items, (-0.65, 0.0, 4.6))
    wedge.components[0]["Rotation"] = [0.0, 20.0, 0.0]
    s.box("Wedge Body", wedge, (0.0, 0.17, 0.0), (0.55, 0.34, 0.42), TOLEX, rot=(35, 0, 0), rough=0.7)
    s.box("Wedge Grille", wedge, (0.0, 0.2, 0.06), (0.48, 0.28, 0.01), (0.12, 0.12, 0.13), rot=(35, 0, 0), metallic=0.5)
    # The desk with the mixing desk on it, once there's one.
    desk_slot = slot(s, items, "Mixing Desk", "Desk")
    s.box("Desk Table", desk_slot, (2.75, 0.72, 3.75), (1.1, 0.04, 0.6), (0.3, 0.22, 0.16), rough=0.7)
    for dx in (-0.5, 0.5):
        rod(s, desk_slot, f"Desk Leg {dx}", (2.75 + dx, 0.0, 3.75), (2.75 + dx, 0.7, 3.75), 0.03, BLACK)
    s.box("Desk", desk_slot, (2.75, 0.8, 3.75), (1.0, 0.1, 0.5), (0.15, 0.15, 0.16), rot=(-10, 0, 0), rough=0.4)
    s.box("Desk Faders", desk_slot, (2.75, 0.86, 3.75), (0.95, 0.02, 0.42), (0.1, 0.1, 0.1), rot=(-10, 0, 0), emissive=(0.2, 0.9, 0.4),
          emissive_intensity=0.6)


def left_wall(s, geo, items, stations, lights):
    """Moving blankets, the gig board, the practice corner, the transom, the clock."""
    # Moving blankets nailed up: the front one always, the back one until there's foam there.
    for i, (z, texture) in enumerate(((0.9, "MovingBlanketBlue"), (5.4, "MovingBlanketGrey"))):
        parent = items if i == 0 else stand_in(s, items, "Blanket Until Foam", "Foam")
        textured(s.box(f"Blanket {i}", parent, (-H + 0.02, 1.35, z), (0.02, 1.9, 1.7), (1, 1, 1), rough=1.0, shadows=False), texture)
        for dz in (-0.75, 0.0, 0.75):
            s.box(f"Blanket Nail {i} {dz}", parent, (-H + 0.035, 2.27, z + dz), (0.015, 0.02, 0.02), STEEL, metallic=0.8, shadows=False)
    # The transom: frosted wire glass high on the wall. By day, white; by night, the car park's
    # sodium light.
    tz = 3.0
    s.box("Transom Frame", geo, (-H + 0.02, 2.45, tz), (0.05, 0.4, 1.9), (0.3, 0.32, 0.34), metallic=0.5)
    night = when(s.group("Night", lights), "Night")
    s.box("Transom Glass", night, (-H + 0.04, 2.45, tz), (0.01, 0.32, 1.8), (0.9, 0.55, 0.2), emissive=(1.0, 0.55, 0.18), emissive_intensity=1.6,
          rough=0.3, shadows=False)
    light(s, night, "Sodium Through The Transom", (-H + 0.25, 2.5, tz), kind="Spot", color=(1.0, 0.58, 0.22), intensity=14.0, range_=7.0,
          rot=look_rotation((-H + 0.25, 2.5, tz), (-0.8, 0.0, tz + 0.4)), inner=25.0, outer=45.0, volumetric=4.0)
    day = when(s.group("Day", lights), "Day")
    s.box("Transom Glass Day", day, (-H + 0.04, 2.45, tz), (0.01, 0.32, 1.8), (0.9, 0.95, 1.0), emissive=(0.9, 0.95, 1.0), emissive_intensity=3.0,
          rough=0.3, shadows=False)
    light(s, day, "Daylight Through The Transom", (-H + 0.25, 2.5, tz), kind="Spot", color=(0.92, 0.95, 1.0), intensity=26.0, range_=8.0,
          rot=look_rotation((-H + 0.25, 2.5, tz), (-0.5, 0.0, tz + 0.6)), inner=18.0, outer=34.0, shadows=True, volumetric=2.5)
    for k in range(6):
        s.box(f"Wire {k}", geo, (-H + 0.045, 2.45, tz - 0.75 + k * 0.3), (0.004, 0.32, 0.004), (0.2, 0.2, 0.2), shadows=False)
    # The gig board.
    gz = 3.35
    textured(s.slab("Gig Board", geo, -H, -H + 0.03, 1.12, 2.0, gz - 0.72, gz + 0.72, (1, 1, 1), rough=0.95), "Cork", (1.4, 0.9))
    s.slab("Board Frame", geo, -H, -H + 0.04, 2.0, 2.03, gz - 0.74, gz + 0.74, WOOD)
    station(s, stations, "Gig Board", "GigBoard", (-H + 0.05, 1.56, gz), (1.75, 0.0, -0.85), 45)
    poster(s, items, "Bassist Wanted", "FlyerBassist", (-H + 0.034, 1.52, gz - 0.5), 0.27, 0.36, "+x", tilt=2.5)
    poster(s, items, "Lawns", "FlyerLawns", (-H + 0.034, 1.42, gz + 0.52), 0.27, 0.36, "+x", tilt=-3.5)
    flyers = (("FlyerA", "FlyerBackyard", 1.62, -0.12, -3.0), ("FlyerB", "FlyerClub", 1.48, 0.15, 2.0), ("FlyerC", "FlyerFestival", 1.72, 0.08, -1.5))
    for slot_name, texture, y, dz, tilt in flyers:
        f = slot(s, items, f"Flyer {slot_name[-1]}", slot_name)
        poster(s, f, "Flyer", texture, (-H + 0.038, y, gz + dz), 0.27, 0.36, "+x", tilt=tilt)
    for slot_name, y, dz, text in (("FlyerA", 1.62, -0.12, "GIG #1\n???"), ("FlyerB", 1.48, 0.15, "a REAL\ngig"), ("FlyerC", 1.72, 0.08, "FEST\n(lol)")):
        card = stand_in(s, items, f"{slot_name} Card", slot_name)
        s.box("Index Card", card, (-H + 0.036, y, gz + dz), (0.003, 0.11, 0.16), (0.97, 0.96, 0.9), rot=(-3, 0, 0), shadows=False)
        scrawl(s, card, "Card Text", (-H + 0.039, y, gz + dz), text, 0.034, INK, facing="+x", tilt=-3.0, font=MARKER)
    # The practice corner: a pad on a snare stand, a chair, a music stand with the rudiments.
    px, pz = -2.55, 1.9
    station(s, stations, "Practice Pad", "PracticePad", (px, 0.78, pz), (1.35, 0.6, -0.75), 40)
    rod(s, items, "Pad Stand", (px, 0.0, pz), (px, 0.7, pz), 0.025, CHROME, metallic=0.9)
    for k in range(3):
        a = math.radians(120 * k)
        rod(s, items, f"Pad Stand Leg {k}", (px + 0.25 * math.cos(a), 0.0, pz + 0.25 * math.sin(a)), (px, 0.25, pz), 0.018, CHROME, metallic=0.9)
    pad = slot(s, items, "Practice Pad", "PracticePad")
    s.box("Pad", pad, (px, 0.74, pz), (0.32, 0.035, 0.32), (0.12, 0.12, 0.12), shape="Cylinder", rough=0.9)
    s.box("Pad Rim", pad, (px, 0.725, pz), (0.34, 0.025, 0.34), (0.1, 0.25, 0.7), shape="Cylinder", rough=0.6)
    rod(s, pad, "Pad Stick L", (px - 0.15, 0.77, pz - 0.05), (px + 0.2, 0.77, pz - 0.15), 0.014, (0.86, 0.72, 0.46))
    stand = stand_in(s, items, "No Pad Yet", "PracticePad")
    s.box("Bare Stand Basket", stand, (px, 0.71, pz), (0.3, 0.02, 0.3), CHROME, shape="Cylinder", metallic=0.9)
    scrawl(s, stand, "Pad Note", (px, 0.725, pz), "PAD?", 0.08, PAINT_PEN, facing="up", spin=90.0, font=MARKER)
    s.prop("Practice Stool", items, "Assets/Models/Venue/Stool.obj", (px + 0.45, 0.0, pz - 0.1), yaw=0.0, scale=0.8)
    ms = (px - 0.1, 0.0, pz + 0.55)
    rod(s, items, "Music Stand Pole", ms, (ms[0], 1.1, ms[2]), 0.015, BLACK, metallic=0.5)
    s.box("Music Stand Desk", items, (ms[0], 1.15, ms[2]), (0.5, 0.32, 0.01), BLACK, rot=(-20, 0, 0), metallic=0.4)
    poster(s, items, "Rudiments On The Stand", "PosterRudiments", (ms[0], 1.17, ms[2] - 0.015), 0.28, 0.42, "-z", tilt=0.0).components[0]["Rotation"] = [-20.0, 0.0, 0.0]
    met = slot(s, items, "Metronome", "Metronome")
    s.box("Metronome", met, (ms[0] + 0.32, 0.9, ms[2] - 0.05), (0.1, 0.18, 0.08), (0.45, 0.12, 0.08), rough=0.6)
    s.box("Metronome Shelf", met, (ms[0] + 0.32, 0.8, ms[2] - 0.05), (0.2, 0.02, 0.16), BLACK)
    rod(s, met, "Metronome Shelf Pole", (ms[0] + 0.32, 0.0, ms[2] - 0.05), (ms[0] + 0.32, 0.8, ms[2] - 0.05), 0.015, BLACK)
    arm = s.entity("Metronome Arm", met, (ms[0] + 0.32, 0.84, ms[2] - 0.09))
    motion(arm, "Sway", amount=25.0, speed=1.0, axis=(0, 0, 1))
    s.box("Arm", arm, (0.0, 0.08, 0.0), (0.006, 0.16, 0.006), CHROME, metallic=0.9, shadows=False)
    # The clock, a cheap office one.
    cz = 0.4
    s.box("Clock", items, (-H + 0.02, 2.25, cz), (0.3, 0.03, 0.3), OFFWHITE, rot=(0, 0, 90), shape="Cylinder", rough=0.5)
    s.box("Clock Rim", items, (-H + 0.015, 2.25, cz), (0.33, 0.02, 0.33), BLACK, rot=(0, 0, 90), shape="Cylinder", rough=0.5)
    for k in range(12):
        a = math.radians(k * 30)
        s.box(f"Clock Tick {k}", items, (-H + 0.036, 2.25 + 0.125 * math.cos(a), cz - 0.125 * math.sin(a)), (0.003, 0.02 if k % 3 == 0 else 0.01, 0.006),
              BLACK, rot=(-k * 30, 0, 0), shadows=False)
    clock_hands(s, items, (-H + 0.036, 2.25, cz), "+x", 0.14)
    # The floor lamp in the corner, a red shade.
    fl = (-3.35, 0.0, 6.5)
    rod(s, items, "Floor Lamp Pole", fl, (fl[0], 1.55, fl[2]), 0.025, BRASS, metallic=0.8)
    s.box("Floor Lamp Base", items, (fl[0], 0.02, fl[2]), (0.3, 0.04, 0.3), BRASS, shape="Cylinder", metallic=0.8)
    shade = s.box("Floor Lamp Shade", items, (fl[0], 1.6, fl[2]), (0.42, 0.3, 0.42), (0.7, 0.08, 0.06), shape="Cylinder", rough=0.9,
                  emissive=(0.9, 0.18, 0.08), emissive_intensity=0.8)
    glow_light(shade, color=(1.0, 0.35, 0.18), intensity=4.0, range_=4.0)


def lounge(s, geo, items, stations, lights):
    """The right side: the couch, the road case table with the laptop, the fridge and the radio,
    the whiteboard and the gear list, the trophies."""
    s.prop("Couch", items, "Assets/Venues/Backyard/Models/Sofa.obj", (3.4, 0.0, 1.45), yaw=-90.0)
    textured(s.box("Lounge Rug", items, (2.3, 0.006, 1.45), (1.6, 0.01, 2.2), (1, 1, 1), rough=1.0, shadows=False), "RugBlue")
    s.box("Couch Tape", items, (3.05, 0.47, 1.1), (0.05, 0.004, 0.32), (0.55, 0.55, 0.55), rot=(0, 20, 0), metallic=0.4, rough=0.4)
    # The road case coffee table: the laptop, cans, a pizza box, the lava lamp once it's earned.
    tx, tz = 2.25, 1.45
    road_case(s, items, "Coffee Case", (tx, 0.0, tz), (0.9, 0.44, 0.5), yaw=90.0)
    top = 0.45
    s.box("Laptop Base", stations, (tx, top + 0.01, tz - 0.12), (0.34, 0.02, 0.24), (0.2, 0.2, 0.22), metallic=0.6, rough=0.4)
    textured(s.box("Laptop Screen", stations, (tx + 0.0, top + 0.13, tz - 0.0), (0.34, 0.22, 0.012), (1, 1, 1), rot=(-12, 0, 0), rough=0.2,
                   shadows=False), "LaptopScreen", emissive=True, emissive_intensity=1.1)
    station(s, stations, "Laptop", "Laptop", (tx, top + 0.1, tz - 0.1), (-0.2, 0.45, -0.8), 40)
    # Fairy lights along the wall over the couch, warm white.
    prev = None
    for i in range(18):
        t = i / 17
        p = (H - 0.05, 2.05 - 0.18 * (1.0 - (2.0 * t - 1.0) ** 2), 0.3 + 2.4 * t)
        bulb = s.box(f"Fairy Light {i}", lights, p, (0.03, 0.03, 0.03), (1.0, 0.85, 0.6), shape="Sphere", emissive=(1.0, 0.8, 0.5),
                     emissive_intensity=9.0, shadows=False)
        if i % 4 == 2:
            glow_light(bulb, color=(1.0, 0.78, 0.5), intensity=1.4, range_=2.4)
        if prev:
            rod(s, lights, f"Fairy Wire {i}", prev, p, 0.004, (0.1, 0.1, 0.1), shadows=False)
        prev = p
    for i, (dx, dz, colour) in enumerate(((0.22, 0.25, (0.1, 0.65, 0.2)), (-0.2, 0.3, (0.05, 0.05, 0.06)), (0.28, -0.3, (0.9, 0.85, 0.15)))):
        s.box(f"Can {i}", items, (tx + dx, top + 0.06, tz + dz), (0.066, 0.12, 0.066), colour, shape="Cylinder", metallic=0.8, rough=0.3)
    textured(s.box("Pizza Box", items, (tx - 0.05, top + 0.02, tz + 0.55), (0.42, 0.04, 0.42), (1, 1, 1), rot=(0, 12, 0), rough=0.9), "PizzaBox")
    lamp = slot(s, items, "Lava Lamp", "Lamp")
    blob = s.box("Lava", lamp, (tx - 0.25, top + 0.17, tz - 0.4), (0.1, 0.3, 0.1), (0.9, 0.3, 0.6), shape="Capsule", emissive=(1.0, 0.25, 0.55),
                 emissive_intensity=4.0)
    glow_light(blob, color=(1.0, 0.3, 0.6), intensity=1.5, range_=2.0)
    motion(blob, "Pulse", amount=0.3, speed=0.08)
    # The fridge by the door with the radio on top (a big chrome boombox now).
    fx, fz = 3.5, 2.85
    s.box("Fridge", items, (fx, 0.45, fz), (0.55, 0.9, 0.55), (0.86, 0.86, 0.84), rough=0.35)
    for i, colour in enumerate(((0.9, 0.2, 0.2), (0.2, 0.6, 0.9), (0.95, 0.8, 0.1), (0.1, 0.1, 0.1))):
        s.box(f"Sticker {i}", items, (fx - 0.278, 0.3 + i * 0.13, fz - 0.15 + 0.1 * (i % 2)), (0.004, 0.08, 0.1), colour, rot=(i * 13 - 20, 0, 0), shadows=False)
    radio = slot(s, items, "Radio", "Radio")
    rx, ry, rz = fx, 1.05, fz
    s.box("Boombox", radio, (rx, ry, rz), (0.24, 0.3, 0.72), (0.62, 0.63, 0.66), rough=0.3, metallic=0.7)
    rod(s, radio, "Boombox Handle", (rx, ry + 0.19, rz - 0.25), (rx, ry + 0.19, rz + 0.25), 0.022, CHROME, metallic=0.9)
    boombox_display(s, radio, (rx - 0.122, ry + 0.1, rz), "-x", width=0.26)
    for i, z in enumerate((rz - 0.22, rz + 0.22)):
        cone = s.entity(f"Speaker {i}", radio, (rx - 0.122, ry - 0.02, z))
        motion(cone, "Bob", amount=0.012, speed=2.0, axis=(-1, 0, 0), music=True)
        s.box("Cone", cone, (0.0, 0.0, 0.0), (0.2, 0.012, 0.2), (0.06, 0.06, 0.06), rot=(0, 0, 90), shape="Cylinder", rough=0.7)
        s.box("Dust Cap", cone, (-0.008, 0.0, 0.0), (0.07, 0.012, 0.07), CHROME, rot=(0, 0, 90), shape="Cylinder", metallic=0.9)
    station(s, stations, "Radio", "Radio", (rx, ry, rz), (-1.45, 0.1, -0.35), 40)
    # The whiteboard: the week, with the band's nights in it; the gear list taped to its corner.
    wz = 4.05
    textured(s.box("Whiteboard", items, (H - 0.025, 1.55, wz), (0.03, 1.0, 1.6), (1, 1, 1), rough=0.25, metallic=0.05), "Whiteboard")
    s.box("Marker Tray", items, (H - 0.06, 1.03, wz), (0.06, 0.03, 1.2), (0.6, 0.6, 0.62), metallic=0.5)
    for i, colour in enumerate(((0.1, 0.2, 0.7), (0.75, 0.1, 0.1), (0.1, 0.1, 0.1))):
        s.box(f"Marker {i}", items, (H - 0.07, 1.055, wz - 0.3 + i * 0.16), (0.02, 0.02, 0.13), colour, rot=(90, 0, 0), shape="Cylinder")
    nights = {0: None, 1: "grindcore guys (LOUD)", 2: "jazz trio - quiet pls", 3: None, 4: "ROOM CHECK", 5: "cover band", 6: "open"}
    for day in range(7):
        # On the day's line (the picture's rows, 72 px apart from 132 of 640), right of the days.
        y = 1.55 + 0.5 - (128 + day * 72) / 640 * 1.0
        p = (H - 0.042, y, wz + 0.8 - 190 / 1024 * 1.6)
        e = scrawl(s, items, f"Booking {day}", p, nights[day] or "", 0.068, (0.04, 0.08, 0.4) if nights[day] else (0.7, 0.04, 0.06),
                   facing="-x", align="Left", anchor="Bottom", font=MARKER, tilt=-1.0)
        if nights[day] is None:
            readout(e, "BandName", max_letters=22)
    scrawl(s, items, "Rent Due", (H - 0.042, 1.17, wz - 0.4), "RENT DUE 1st!!", 0.05, (0.75, 0.08, 0.1), facing="-x", font=MARKER, tilt=4.0)
    page = s.group("Wishlist", items, (H - 0.045, 1.62, wz - 0.97))
    page.components[0]["Rotation"] = [0.0, 90.0, 0.0]
    textured(s.box("Wishlist Page", page, (0.0, 0.0, 0.0), (0.27, 0.35, 0.003), (1, 1, 1), rot=(0, 0, 3.0), rough=0.9, shadows=False),
             "NotebookRehearsal", emissive=True, emissive_intensity=0.25)
    s.box("Wishlist Magnet", page, (0.0, 0.16, -0.004), (0.04, 0.04, 0.012), (0.85, 0.2, 0.2), shape="Cylinder", rot=(90, 0, 0))
    wishes = ("neon-sign", "signed-snare-head", "spare-cymbal", "vinyl-shelf", "lava-lamp", "fc-plaque", "teacher-certificate", "mixing-desk", "gold-record")
    for i, item in enumerate(wishes):
        readout(scrawl(s, page, f"Wish {i}", (-0.098, 0.104 - i * 0.0202, -0.003), "", 0.017, INK, align="Left", anchor="Bottom", tilt=3.0), "Wishlist",
                item=item)
    station(s, stations, "Wishlist", "Wishlist", (H - 0.05, 1.6, wz - 0.4), (-1.6, 0.0, -0.45), 44)
    # The trophies, back right over the bass rig's shoulder.
    tz = 5.9
    station(s, stations, "Trophy Wall", "TrophyWall", (H - 0.05, 1.8, tz), (-1.9, -0.15, -0.6), 52)
    poster(s, items, "Certificate", "Certificate", (H - 0.012, 1.5, tz + 0.3), 0.5, 0.375, "-x", tilt=-1.0)
    poster(s, items, "Poster Kick Drum Kids", "PosterKickDrumKids", (H - 0.012, 2.2, tz - 0.45), 0.4, 0.6, "-x", tilt=2.0)
    band = slot(s, items, "Band Poster", "PosterA")
    poster(s, band, "Poster", "PosterGhostNotes", (H - 0.012, 1.55, tz - 0.4), 0.4, 0.6, "-x", tilt=-2.0)
    for slot_name, z in (("PlaqueA", tz + 0.75), ("PlaqueB", tz + 1.05)):
        p = slot(s, items, slot_name, slot_name)
        s.box("Plaque", p, (H - 0.03, 1.95, z), (0.03, 0.3, 0.24), WOOD, rough=0.6)
        s.box("Plate", p, (H - 0.05, 1.95, z), (0.01, 0.16, 0.16), GOLD, metallic=0.9, rough=0.25)
    rec = slot(s, items, "Gold Record", "GoldRecord")
    s.box("Frame", rec, (H - 0.03, 2.15, tz + 0.3), (0.03, 0.4, 0.34), BLACK, rough=0.5)
    s.box("Record", rec, (H - 0.05, 2.17, tz + 0.3), (0.26, 0.01, 0.26), GOLD, rot=(0, 0, 90), shape="Cylinder", metallic=1.0, rough=0.15)
    head = slot(s, items, "Signed Snare Head", "WallLeft")
    s.box("Signed Head", head, (H - 0.03, 1.2, tz + 0.85), (0.33, 0.01, 0.33), WHITE, rot=(0, 0, 90), shape="Cylinder", rough=0.6)
    scrawl(s, head, "Signature", (H - 0.04, 1.2, tz + 0.85), "rock on!\n- T.", 0.04, (0.1, 0.1, 0.12), facing="-x", font=MARKER, tilt=12.0)
    shelf = slot(s, items, "Vinyl Shelf", "Shelf")
    s.slab("Vinyl Shelf", shelf, H - 0.32, H, 0.0, 0.62, 4.85, 5.4, WOOD, rough=0.8)
    for i in range(8):
        s.box(f"Sleeve {i}", shelf, (H - 0.16, 0.45, 4.9 + i * 0.06), (0.26, 0.3, 0.02),
              [(0.8, 0.2, 0.2), (0.2, 0.5, 0.8), (0.9, 0.8, 0.2), (0.1, 0.1, 0.1)][i % 4], rough=0.7)
    tally(s, items, (H - 0.012, 1.1, tz + 0.15), "-x", ink=INK)
    # What's still to come, in paint pen on the black wall.
    for slot_name, centre, size, text in (("GoldRecord", (H - 0.012, 2.15, tz + 0.3), (0.34, 0.4), "GOLD\nRECORD"),
                                          ("PlaqueA", (H - 0.012, 1.95, tz + 0.75), (0.24, 0.3), "FC"),
                                          ("PlaqueB", (H - 0.012, 1.95, tz + 1.05), (0.24, 0.3), "cert."),
                                          ("PosterA", (H - 0.012, 1.55, tz - 0.4), (0.4, 0.6), "OUR\nPOSTER")):
        p = stand_in(s, items, f"{slot_name} Goes Here", slot_name)
        tape_outline(s, p, f"{slot_name} Outline", centre, size[0], size[1], facing="-x", colour=PAINT_PEN, tape=0.01)
        scrawl(s, p, f"{slot_name} Note", (centre[0] - 0.003, centre[1], centre[2]), text, 0.06, PAINT_PEN, facing="-x", font=MARKER, tilt=-3.0)


def neon(s, items, lights):
    """The neon sign over the bass rig, once earned: LOUD in pink, buzzing on the beat."""
    sign = slot(s, items, "Neon Sign", "Neon")
    s.box("Neon Backing", sign, (2.2, 2.42, D - 0.03), (1.1, 0.4, 0.02), (0.04, 0.03, 0.05), rough=0.3)
    scrawl(s, sign, "Neon Word", (2.2, 2.43, D - 0.045), "LOUD", 0.3, (1.0, 0.35, 0.85), facing="-z", font=MARKER, lit=False)
    glow = light(s, lights, "Neon Glow", (2.2, 2.35, D - 0.4), color=(1.0, 0.25, 0.7), intensity=3.5, range_=3.5)
    motion(glow, "Pulse", amount=0.3, speed=0.2, music=True)
    no = stand_in(s, items, "Neon Goes Here", "Neon")
    tape_outline(s, no, "Neon Outline", (2.2, 2.42, D - 0.012), 1.1, 0.4, facing="-z", colour=PAINT_PEN, tape=0.01)
    scrawl(s, no, "Neon Note", (2.2, 2.42, D - 0.016), "NEON HERE", 0.09, PAINT_PEN, facing="-z", font=MARKER, tilt=2.0)


def overhead(s, geo, items, lights):
    """The ceiling's fluorescent panels (one going), and a fill so the near things read."""
    for i, (x, z, flicker) in enumerate(((-1.8, 2.0, False), (1.8, 2.2, True), (0.0, 4.4, False))):
        s.box(f"Troffer {i}", geo, (x, TOP - 0.01, z), (0.62, 0.03, 1.22), (0.85, 0.85, 0.83), rough=0.5)
        panel = s.box(f"Troffer Panel {i}", lights, (x, TOP - 0.028, z), (0.56, 0.006, 1.16), (0.95, 0.97, 1.0), emissive=(0.9, 0.95, 1.0),
                      emissive_intensity=2.2, shadows=False)
        glow_light(panel, color=(0.88, 0.93, 1.0), intensity=6.0, range_=6.0, volumetric=0.3)
        if flicker:
            motion(panel, "Flicker", amount=0.6, speed=0.6)
    light(s, geo, "Fill", (0.3, 1.5, 0.2), color=(1.0, 0.85, 0.66), intensity=3.0, range_=6.0)
    # A pair of clamp lights on the conduit over the riser: the banner and the kit, warm.
    for x in (-1.2, 1.2):
        at = (x, TOP - 0.12, 4.6)
        s.box(f"Clamp Light {x}", items, at, (0.12, 0.16, 0.12), (0.12, 0.12, 0.13), shape="Cylinder", metallic=0.6, rough=0.4)
        light(s, lights, f"Clamp Light Beam {x}", (at[0], at[1] - 0.1, at[2]), kind="Spot", color=(1.0, 0.82, 0.6), intensity=22.0, range_=8.0,
              rot=look_rotation((at[0], at[1] - 0.1, at[2]), (x * 0.4, 1.3, D - 0.2)), inner=24.0, outer=42.0, shadows=x < 0, volumetric=2.0)
    dust(s, lights, "Dust", (0.0, 1.4, 4.6), (3.6, 2.4, 3.0), count=240, rate=30.0)


def moving_in(s, items):
    """The first visit: the gear just carried up from the van, still in its cases."""
    boxes = when(s.group("Moving In", items), "MovingIn")
    road_case(s, boxes, "Case 1", (-1.6, 0.0, 0.5), (0.8, 0.7, 0.6), yaw=12.0)
    road_case(s, boxes, "Case 2", (-1.55, 0.7, 0.5), (0.7, 0.4, 0.5), yaw=-8.0)
    textured(s.box("Box Drums", boxes, (1.2, 0.24, 0.3), (0.6, 0.48, 0.48), (1, 1, 1), rot=(0, 20, 0), rough=0.9), "BoxDrums")
    textured(s.box("Box Fragile", boxes, (1.15, 0.68, 0.32), (0.5, 0.4, 0.42), (1, 1, 1), rot=(0, -10, 0), rough=0.9), "BoxFragile")
    s.prop("Cable Coil 2", boxes, "Assets/Models/Venue/CableCoil.obj", (0.2, 0.0, 0.9), yaw=40.0)


def walls_dressed(s, items):
    """Posters and stickers from the room's other tenants."""
    poster(s, items, "Poster Death Squad", "PosterDeathSquad", (-H + 0.012, 1.7, 4.5), 0.46, 0.69, "+x", tilt=-2.0)
    poster(s, items, "Poster Metronomes", "PosterMetronomes", (-0.9, 1.8, -1.59), 0.4, 0.6, "+z", tilt=1.5)
    poster(s, items, "Poster Magazine", "PosterMagazine", (H - 0.012, 1.7, 2.75), 0.3, 0.41, "-x", tilt=-3.0)
    rnd = random.Random(1414)
    for i in range(14):
        colour = rnd.choice(((0.9, 0.2, 0.2), (0.95, 0.85, 0.1), (0.2, 0.6, 0.95), (0.95, 0.95, 0.9), (0.1, 0.8, 0.4)))
        x = rnd.uniform(-3.4, 3.4)
        y = rnd.uniform(0.6, 1.2)
        if abs(x) < 1.7:
            continue
        s.box(f"Sticker {i}", items, (x, y, D - 0.012), (rnd.uniform(0.08, 0.16), rnd.uniform(0.05, 0.1), 0.003), colour,
              rot=(0, 0, rnd.uniform(-20, 20)), shadows=False)
    scrawl(s, items, "Graffiti", (-H + 0.013, 0.7, 2.6), "ROOM 14 RULES", 0.09, PAINT_PEN, facing="+x", font=MARKER, tilt=6.0)
    scrawl(s, items, "Graffiti 2", (H - 0.013, 0.75, 4.4), "tune ur drums", 0.06, (0.85, 0.2, 0.25), facing="-x", font=MARKER, tilt=-4.0)


def build_rehearsal():
    s = Scene(seed=2103)
    root = s.group("Hideout Rehearsal")
    geo = s.group("Room", root)
    items = s.group("Things", root)
    stations = s.group("Stations", root)
    lights = s.group("Lights", root)
    marks = s.group("Markers", root)
    shell(s, geo)
    door_and_hallway(s, geo, items, lights)
    riser_and_kit(s, geo, items, stations, lights)
    amps(s, geo, items, stations, lights)
    left_wall(s, geo, items, stations, lights)
    lounge(s, geo, items, stations, lights)
    neon(s, items, lights)
    overhead(s, geo, items, lights)
    walls_dressed(s, items)
    moving_in(s, items)
    # Acoustic foam: the room's own reward, the left wall's back half covered (blankets till then).
    foam = slot(s, items, "Acoustic Foam", "Foam")
    for i in range(4):
        for j in range(4):
            textured(s.box(f"Foam {i}.{j}", foam, (-H + 0.04, 0.55 + j * 0.6, 4.55 + i * 0.6), (0.07, 0.58, 0.58), (1, 1, 1), rough=1.0,
                           shadows=False), "FoamWedge", (0.5, 0.5))
    tone = s.group("Room Tone", root)
    sound(s, tone, "Band Next Door", (H + 0.4, 1.2, 3.8), "BandNextDoor", volume=0.32, near=1.0, far=9.0)
    sound(s, tone, "Hall Tube", (-0.2, 2.5, -2.6), "TubeBuzz", volume=0.14, near=0.4, far=5.0)
    sound(s, tone, "Amp Hum", (-2.5, 0.9, 6.7), "AmpHum", volume=0.2, near=0.5, far=5.0)
    # The overview from the doorway; the way in starts out in the hallway.
    view(s, marks, (0.0, 1.65, -1.25), (0.0, 1.05, 5.6), 60.0, intro_eye=(-0.2, 1.7, -3.9), intro_target=(0.1, 1.2, 2.0))
    return s
