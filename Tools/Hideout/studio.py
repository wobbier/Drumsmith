"""The studio, the hideout's last room (Assets/Hideout/Studio.lvl): the live room of a real
recording studio, the band's for the album after the festival.

An oak floor and a slatted oak wall behind the kit, fabric absorbers and skyline diffusers down the
sides, wooden clouds overhead and three Edison bulbs on long cords over the kit, which sits on a
big old rug among gobos, overheads and room mics. Through the glass on the left, the control room:
the console glowing, the session up on the big screen, monitors either side, a rack of outboard
blinking. The vocal booth in the back left corner (the gig board on its front, RECORDING over its
door). On the right: the lounge under a window with blinds (sun through them in stripes by day,
the city by night), the turntable that is the radio (its record turning, its meters bouncing), the
gold and platinum on the wall, the guitars, and the Hammond with its Leslie spinning in the corner.

Room space as the other rooms: x across (+x the lounge side), y up, z from the door (the camera)
to the back wall.
"""
import math
import random

from hideoutgen import (band_name, band_name_text, BLACK, BRASS, CHROME, GOLD, MARKER, OFFWHITE, STEEL, WHITE, WOOD, Scene, boombox_display,
                        clock_hands, drummer, dust, glow_light, light, look_rotation, motion, poster, readout, rod, scrawl, setlist, slot, sound,
                        stand_in, station, tally, tape_outline, textured, view, when)

H = 4.6        # half the width
D = 8.2        # the back wall's face
TOP = 3.6      # the ceiling
WIN = (3.2, 6.0, 0.95, 2.35)      # the control room window in the left wall: z from, z to, y from, y to
CR = 4.2       # the control room's depth behind the left wall
BOOTH = (2.0, 2.0)                # the vocal booth in the back left corner: across, deep
LOUNGE_WIN = (1.6, 3.2, 1.1, 2.5)  # the lounge window in the right wall

WALNUT = (0.32, 0.2, 0.12)
INK = (0.12, 0.16, 0.42)
PLATINUM = (0.86, 0.87, 0.9)


def shell(s, geo):
    textured(s.slab("Floor", geo, -H, H, -0.1, 0.0, -1.6, D, (1, 1, 1), rough=0.45), "OakFloor", (7.7, 8.2))
    textured(s.slab("Back Wall", geo, -H, H, 0.0, TOP, D, D + 0.12, (1, 1, 1), rough=0.7), "WoodSlats", (11.5, 4.5))
    side = (0.2, 0.19, 0.18)
    z0, z1, y0, y1 = WIN
    # The left wall, round the control room window.
    s.slab("Left Wall Front", geo, -H - 0.3, -H, 0.0, TOP, -1.6, z0, side, rough=0.9)
    s.slab("Left Wall Back", geo, -H - 0.3, -H, 0.0, TOP, z1, D, side, rough=0.9)
    s.slab("Left Wall Under", geo, -H - 0.3, -H, 0.0, y0, z0, z1, side, rough=0.9)
    s.slab("Left Wall Over", geo, -H - 0.3, -H, y1, TOP, z0, z1, side, rough=0.9)
    for name, a, b in (("Sill", (y0 - 0.04, y0), None), ("Head", (y1, y1 + 0.04), None)):
        s.slab(f"Window {name}", geo, -H - 0.32, -H + 0.04, a[0], a[1], z0 - 0.04, z1 + 0.04, WALNUT, rough=0.5)
    for z in (z0, z1):
        s.slab(f"Window Jamb {z}", geo, -H - 0.32, -H + 0.04, y0, y1, z - 0.04, z + 0.04, WALNUT, rough=0.5)
    s.slab("Window Mullion", geo, -H - 0.32, -H + 0.02, y0, y1, (z0 + z1) / 2 - 0.03, (z0 + z1) / 2 + 0.03, WALNUT, rough=0.5)
    # The right wall, round the lounge window.
    w0, w1, v0, v1 = LOUNGE_WIN
    s.slab("Right Wall Front", geo, H, H + 0.15, 0.0, TOP, -1.6, w0, side, rough=0.9)
    s.slab("Right Wall Back", geo, H, H + 0.15, 0.0, TOP, w1, D, side, rough=0.9)
    s.slab("Right Wall Under", geo, H, H + 0.15, 0.0, v0, w0, w1, side, rough=0.9)
    s.slab("Right Wall Over", geo, H, H + 0.15, v1, TOP, w0, w1, side, rough=0.9)
    s.slab("Front Wall", geo, -H, H, 0.0, TOP, -1.72, -1.6, side, rough=0.9)
    # The ceiling (it casts shadows: the engine's sun stays out), and the wooden clouds under it.
    s.slab("Ceiling", geo, -H - CR - 0.3, H + 0.15, TOP, TOP + 0.1, -1.72, D + 0.12, (0.07, 0.07, 0.075), rough=0.95)
    for i, (x, z, w, d) in enumerate(((-1.6, 2.4, 2.2, 1.6), (1.8, 2.6, 2.2, 1.6), (0.3, 5.6, 3.2, 2.0))):
        textured(s.box(f"Cloud {i}", geo, (x, TOP - 0.45, z), (w, 0.06, d), (1, 1, 1), rough=0.7), "WoodSlats", (w / 0.8, d / 0.8))
        for dx in (-w / 2 + 0.1, w / 2 - 0.1):
            for dz in (-d / 2 + 0.1, d / 2 - 0.1):
                rod(s, geo, f"Cloud Wire {i} {dx} {dz}", (x + dx, TOP, z + dz), (x + dx, TOP - 0.42, z + dz), 0.006, STEEL, metallic=0.8, shadows=False)
    s.slab("Skirting", geo, -H, H, 0.0, 0.08, D - 0.02, D, WALNUT)


def side_walls(s, geo, items, lights):
    """Fabric absorbers (the foam, grown up) and skyline diffusers down both sides; uplights."""
    foam = slot(s, items, "Acoustic Panels", "Foam")
    panels = (("-x", 0.6, "FabricCharcoal"), ("-x", 6.6, "FabricTeal"), ("+x", 7.0, "FabricTeal"), ("+x", 0.2, "FabricCharcoal"))
    for facing, z, texture in panels:
        x = -H + 0.05 if facing == "-x" else H - 0.05
        if facing == "+x" and z < 1.0:
            continue
        textured(s.box(f"Panel {facing} {z}", foam, (x, 1.7, z), (0.1, 1.8, 1.0), (1, 1, 1), rough=1.0), texture)
        s.box(f"Panel Frame {facing} {z}", foam, (x, 1.7, z), (0.08, 1.86, 1.06), WALNUT, rough=0.6)
    for i, z in enumerate((1.1, 2.3)):
        textured(s.box(f"Panel Front {i}", foam, (-H + 0.05, 1.7, -0.3 + i * 1.2 if i else -0.3), (0.1, 1.8, 1.0), (1, 1, 1), rough=1.0), "FabricTeal")
    bare = stand_in(s, items, "No Panels Yet", "Foam")
    s.box("Bare Wall Note", bare, (-H + 0.01, 1.6, 0.6), (0.01, 0.2, 0.3), (0.95, 0.95, 0.9))
    # Skyline diffusers: 6 x 6 blocks of different depths (a fixed random field, so it reads as one).
    rnd = random.Random(808)
    depths = [[rnd.choice((0.02, 0.05, 0.08, 0.11, 0.14)) for _ in range(6)] for _ in range(6)]
    for name, x, z, sign in (("Diffuser L1", -H, 2.1, 1), ("Diffuser R1", H, 6.05, -1)):
        for row in range(2):
            for col in range(2):
                for i in range(6):
                    for j in range(6):
                        d = depths[i][j]
                        y = 1.2 + row * 0.62 + i * 0.1 + 0.05
                        zz = z - 0.6 + col * 0.62 + j * 0.1 + 0.05
                        s.box(f"{name} {row}{col} {i}{j}", geo, (x + sign * d / 2, y, zz), (d, 0.096, 0.096), (0.62, 0.45, 0.3) if (i + j) % 2 else (0.55, 0.4, 0.26),
                              rough=0.7, shadows=False)
    # Uplights on the floor, washing the slat wall and the sides.
    for i, x in enumerate((-3.6, -1.8, 1.8, 3.6)):
        at = (x, 0.06, D - 0.35)
        s.box(f"Uplight {i}", items, at, (0.12, 0.1, 0.12), BLACK, shape="Cylinder", metallic=0.6)
        light(s, lights, f"Uplight Beam {i}", (at[0], 0.12, at[2]), kind="Spot", color=(1.0, 0.62, 0.3), intensity=9.0, range_=4.5,
              rot=look_rotation((at[0], 0.12, at[2]), (x, 3.0, D)), inner=18.0, outer=34.0, volumetric=0.6)


def kit(s, geo, items, stations, lights):
    """The rug, the drummer, the mics round the kit, the gobos, the bulbs, the neon name."""
    throne = 6.55
    kx = 0.4
    rug = slot(s, items, "Rug", "Rug")
    textured(s.box("Persian Rug", rug, (kx, 0.006, 6.0), (3.4, 0.01, 2.9), (1, 1, 1), rot=(0, 90, 0), rough=1.0, shadows=False), "RugRed")
    drummer(s, items, (kx, 0.0, throne), yaw=180.0)
    station(s, stations, "Kit", "Kit", (kx, 1.15, 5.35), (0.3, 0.8, -2.4), 42)
    kz = throne - 1.152
    head = textured(s.box("Kick Logo", items, (kx, 0.31, kz), (0.56, 0.56, 0.004), (1, 1, 1), rough=0.7, shadows=False), "KickHead", emissive=True,
                    emissive_intensity=0.25)
    head.components[-1]["Material"]["AlphaCutoff"] = 0.5
    band_name(head, "Unnamed")
    blank = textured(s.box("Kick Logo Blank", items, (kx, 0.31, kz - 0.001), (0.56, 0.56, 0.004), (1, 1, 1), rough=0.7, shadows=False), "KickHeadBlank",
                     emissive=True, emissive_intensity=0.25)
    blank.components[-1]["Material"]["AlphaCutoff"] = 0.5
    band_name(blank, "Named")
    band_name_text(s, items, "Band Name On The Kick", (kx, 0.34, kz - 0.008), 0.07, (0.08, 0.08, 0.1), fit=9)
    # Overheads on booms, a kick mic, a pair of room mics out front.
    for side in (-1, 1):
        base = (kx + side * 1.3, 0.0, throne + 0.2)
        rod(s, items, f"Overhead Stand {side}", base, (base[0], 1.7, base[2]), 0.025, BLACK, metallic=0.5)
        tip = (kx + side * 0.35, 2.05, throne - 0.75)
        rod(s, items, f"Overhead Boom {side}", (base[0], 1.7, base[2]), tip, 0.02, BLACK, metallic=0.5)
        s.box(f"Overhead Mic {side}", items, (tip[0], tip[1] - 0.06, tip[2]), (0.045, 0.16, 0.045), (0.75, 0.75, 0.78), shape="Capsule", metallic=0.8)
    for side in (-1, 1):
        base = (kx + side * 1.0, 0.0, 4.3)
        rod(s, items, f"Room Mic Stand {side}", base, (base[0], 1.55, base[2]), 0.02, BLACK, metallic=0.5)
        s.box(f"Room Mic {side}", items, (base[0], 1.62, base[2]), (0.06, 0.18, 0.06), (0.2, 0.2, 0.22), shape="Capsule", metallic=0.7)
    s.box("Kick Mic", items, (kx + 0.05, 0.25, kz - 0.18), (0.07, 0.07, 0.16), BLACK, rot=(90, 0, 0), shape="Capsule", metallic=0.6)
    for k in range(3):
        a = math.radians(120 * k)
        rod(s, items, f"Headphone Stand Leg {k}", (-1.4 + 0.2 * math.cos(a), 0.0, 6.9 + 0.2 * math.sin(a)), (-1.4, 0.3, 6.9), 0.015, BLACK)
    rod(s, items, "Headphone Stand", (-1.4, 0.3, 6.9), (-1.4, 1.2, 6.9), 0.02, BLACK)
    s.box("Headphones", items, (-1.4, 1.2, 6.9), (0.2, 0.2, 0.06), (0.08, 0.08, 0.09), shape="Sphere", rough=0.5)
    # Gobos either side, on wheels.
    for side, yaw in ((-1, 25.0), (1, -25.0)):
        g = s.group(f"Gobo {side}", items, (kx + side * 2.0, 0.0, 6.4))
        g.components[0]["Rotation"] = [0.0, yaw, 0.0]
        textured(s.box("Gobo Panel", g, (0.0, 1.0, 0.0), (1.1, 1.6, 0.1), (1, 1, 1), rough=1.0), "FabricTeal")
        s.box("Gobo Frame", g, (0.0, 1.0, 0.0), (1.15, 1.65, 0.08), WALNUT, rough=0.6)
        for dx in (-0.45, 0.45):
            s.box(f"Gobo Wheel {dx}", g, (dx, 0.06, 0.0), (0.1, 0.04, 0.1), BLACK, rot=(0, 0, 90), shape="Cylinder")
    # The Edison bulbs on their cords, swaying a little.
    for i, (x, z, drop) in enumerate(((kx - 0.9, 5.6, 1.1), (kx + 0.15, 6.0, 1.35), (kx + 1.0, 5.4, 0.95))):
        pivot = s.entity(f"Pendant {i}", lights, (x, TOP, z))
        motion(pivot, "Sway", amount=1.5, speed=0.2 + 0.03 * i, axis=(1, 0, 0.4), phase=0.3 * i)
        rod(s, pivot, "Cord", (0.0, 0.0, 0.0), (0.0, -drop, 0.0), 0.01, BLACK, shadows=False)
        s.box("Socket", pivot, (0.0, -drop - 0.03, 0.0), (0.05, 0.07, 0.05), BRASS, shape="Cylinder", metallic=0.8)
        bulb = s.box("Edison Bulb", pivot, (0.0, -drop - 0.13, 0.0), (0.1, 0.15, 0.1), (1.0, 0.7, 0.35), shape="Capsule", emissive=(1.0, 0.62, 0.28),
                     emissive_intensity=9.0, shadows=False)
        glow_light(bulb, color=(1.0, 0.66, 0.34), intensity=5.0, range_=5.0, shadows=i == 1, volumetric=0.6)
    # A key light from the front, soft, on the drummer.
    key = (kx - 1.2, TOP - 0.3, 3.2)
    light(s, lights, "Key Light", key, kind="Spot", color=(1.0, 0.88, 0.74), intensity=26.0, range_=9.0, rot=look_rotation(key, (kx, 1.0, throne)),
          inner=18.0, outer=36.0, shadows=True, volumetric=1.0)
    # The setlist (taped to the rug's edge), the stick bag, the spare cymbal.
    setlist(s, items, (kx + 0.9, 0.013, 4.75), -10.0)
    bag = slot(s, items, "Stick Bag", "StickBag")
    s.box("Bag", bag, (kx + 0.72, 0.45, 6.25), (0.06, 0.42, 0.15), (0.35, 0.2, 0.1), rough=0.8)
    for i in range(4):
        rod(s, bag, f"Bag Stick {i}", (kx + 0.72, 0.5, 6.2 + i * 0.03), (kx + 0.72, 0.75, 6.2 + i * 0.03), 0.014, (0.86, 0.72, 0.46))
    spare = slot(s, items, "Spare Cymbal", "CymbalStand")
    rod(s, spare, "Stand", (kx - 1.15, 0.0, 7.1), (kx - 1.15, 1.35, 7.1), 0.025, CHROME, metallic=0.9)
    s.box("Cymbal", spare, (kx - 1.15, 1.37, 7.1), (0.5, 0.012, 0.5), BRASS, rot=(-16, 0, 0), shape="Cylinder", metallic=0.9, rough=0.25)
    # The neon: the band's own name, in pink, on the slat wall over the kit.
    sign = slot(s, items, "Neon Sign", "Neon")
    neon_text = scrawl(s, sign, "Neon Name", (kx, 2.75, D - 0.03), "", 0.36, (1.0, 0.3, 0.8), facing="-z", font=MARKER, lit=False)
    readout(neon_text, "BandName", max_letters=18)
    glow = light(s, lights, "Neon Glow", (kx, 2.7, D - 0.5), color=(1.0, 0.25, 0.7), intensity=4.0, range_=4.0)
    motion(glow, "Pulse", amount=0.25, speed=0.2, music=True)
    s.box("Neon Backer", sign, (kx, 2.75, D - 0.015), (2.6, 0.5, 0.01), (0.03, 0.02, 0.04), rough=0.2)


def control_room(s, geo, items, stations, lights):
    """Through the glass: the console, the big screen with the session, the monitors, the rack."""
    x0 = -H - 0.3            # the control room's side of the wall
    xb = x0 - CR             # its far wall
    z0, z1 = 1.8, 7.6
    s.slab("CR Floor", geo, xb, x0, -0.1, 0.0, z0, z1, (0.2, 0.17, 0.15), rough=0.6)
    textured(s.slab("CR Far Wall", geo, xb - 0.12, xb, 0.0, TOP, z0, z1, (1, 1, 1), rough=0.8), "WoodSlats", (7.25, 4.5))
    s.slab("CR Front", geo, xb, x0, 0.0, TOP, z0 - 0.12, z0, (0.12, 0.12, 0.13), rough=0.9)
    s.slab("CR Back", geo, xb, x0, 0.0, TOP, z1, z1 + 0.12, (0.12, 0.12, 0.13), rough=0.9)
    # The console (the room's own reward: the mixing desk), facing the big screen.
    desk = slot(s, items, "Console", "Desk")
    cx, cz0, cz1 = x0 - 1.5, 3.3, 5.9
    s.box("Console Body", desk, (cx, 0.42, (cz0 + cz1) / 2), (1.1, 0.84, cz1 - cz0), WALNUT, rough=0.5)
    s.box("Console Surface", desk, (cx - 0.05, 0.9, (cz0 + cz1) / 2), (1.0, 0.06, cz1 - cz0 - 0.1), (0.14, 0.14, 0.16), rot=(0, 0, -8), metallic=0.3,
          rough=0.4)
    rnd = random.Random(909)
    strips = int((cz1 - cz0 - 0.2) / 0.075)
    for i in range(strips):
        z = cz0 + 0.15 + i * 0.075
        s.box(f"Fader {i}", desk, (cx - 0.38, 0.95, z), (0.03, 0.02, 0.015), (0.85, 0.85, 0.85), metallic=0.5)
        s.box(f"Fader Slot {i}", desk, (cx - 0.3, 0.935, z), (0.22, 0.004, 0.006), BLACK)
        for k in range(4):
            s.box(f"Knob {i} {k}", desk, (cx - 0.05 + k * 0.09, 0.96 - k * 0.012, z), (0.018, 0.022, 0.018),
                  [(0.9, 0.2, 0.2), (0.2, 0.6, 0.95), (0.95, 0.8, 0.2), (0.85, 0.85, 0.85)][k], shape="Cylinder")
        meter = s.box(f"Meter {i}", desk, (cx + 0.45, 1.12, z), (0.01, 0.12, 0.04), (0.2, 1.0, 0.35), emissive=(0.2, 1.0, 0.35),
                      emissive_intensity=4.0, shadows=False)
        motion(meter, "Pulse", amount=0.9, speed=0.5, phase=((i % 4) + 0.5) / 4.0, music=True)
    s.box("Meter Bridge", desk, (cx + 0.5, 1.12, (cz0 + cz1) / 2), (0.08, 0.2, cz1 - cz0), (0.1, 0.1, 0.11), metallic=0.4)
    empty = stand_in(s, items, "Empty Desk", "Desk")
    s.box("Plain Desk", empty, (cx, 0.75, (cz0 + cz1) / 2), (1.0, 0.05, cz1 - cz0), WALNUT, rough=0.6)
    # The big screen on the far wall, monitors either side, a rack.
    screen = textured(s.box("Session Screen", items, (xb + 0.05, 1.75, 4.6), (0.04, 0.95, 1.7), (1, 1, 1), rough=0.2, shadows=False), "DawScreen",
                      emissive=True, emissive_intensity=1.6)
    glow_light(screen, color=(0.55, 0.7, 1.0), intensity=3.0, range_=4.0)
    for side, z in ((-1, 3.4), (1, 5.8)):
        rod(s, items, f"Monitor Stand {side}", (xb + 0.6, 0.0, z), (xb + 0.6, 1.0, z), 0.06, BLACK, metallic=0.4)
        s.box(f"Monitor {side}", items, (xb + 0.6, 1.3, z), (0.38, 0.55, 0.32), (0.92, 0.92, 0.9), rough=0.4)
        s.box(f"Woofer {side}", items, (xb + 0.79, 1.2, z), (0.22, 0.012, 0.22), (0.15, 0.15, 0.16), rot=(0, 0, 90), shape="Cylinder")
        cone = s.entity(f"Woofer Cone {side}", items, (xb + 0.8, 1.2, z))
        motion(cone, "Bob", amount=0.006, speed=2.0, axis=(1, 0, 0), music=True)
        s.box("Cone", cone, (0.0, 0.0, 0.0), (0.12, 0.01, 0.12), (0.85, 0.75, 0.2), rot=(0, 0, 90), shape="Cylinder", metallic=0.5)
    s.prop("Outboard Rack", items, "Assets/Models/Venue/AmpRack.obj", (xb + 0.5, 0.0, 6.9), yaw=90.0)
    for i in range(10):
        led = s.box(f"Rack LED {i}", lights, (xb + 0.83, 0.25 + i * 0.1, 6.75 + (i % 3) * 0.1), (0.01, 0.012, 0.012),
                    [(1.0, 0.2, 0.1), (0.2, 1.0, 0.3), (1.0, 0.8, 0.2)][i % 3], shape="Sphere", emissive=[(1.0, 0.2, 0.1), (0.2, 1.0, 0.3), (1.0, 0.8, 0.2)][i % 3],
                    emissive_intensity=10.0, shadows=False)
        motion(led, "Blink", amount=0.6, speed=0.3 + 0.17 * i, phase=0.13 * i)
    # The engineer's chair, the producer's couch along the back, a desk lamp.
    s.box("Chair Seat", items, (x0 - 0.6, 0.5, 4.6), (0.5, 0.08, 0.5), BLACK, rough=0.5)
    s.box("Chair Back", items, (x0 - 0.38, 0.85, 4.6), (0.06, 0.6, 0.45), BLACK, rough=0.5)
    rod(s, items, "Chair Post", (x0 - 0.6, 0.08, 4.6), (x0 - 0.6, 0.48, 4.6), 0.04, CHROME, metallic=0.9)
    s.prop("Producer Couch", items, "Assets/Venues/Backyard/Models/Sofa.obj", (x0 - 2.0, 0.0, z1 - 0.5), yaw=180.0)
    lamp = (cx + 0.45, 1.3, cz1 + 0.2)
    shade = s.box("Desk Lamp", items, lamp, (0.18, 0.12, 0.18), (0.15, 0.3, 0.2), shape="Cylinder", metallic=0.5, emissive=(1.0, 0.7, 0.4),
                  emissive_intensity=0.6)
    glow_light(shade, color=(1.0, 0.72, 0.42), intensity=2.5, range_=3.0)
    light(s, lights, "CR Fill", (x0 - 1.5, 2.8, 4.6), color=(0.75, 0.8, 1.0), intensity=7.0, range_=6.0)
    light(s, lights, "CR Warm", (x0 - 0.8, 2.2, 6.6), color=(1.0, 0.7, 0.42), intensity=5.0, range_=4.5)
    for z in (2.6, 6.8):
        sconce = s.box(f"CR Sconce {z}", items, (xb + 0.08, 2.3, z), (0.08, 0.2, 0.14), (1.0, 0.75, 0.45), emissive=(1.0, 0.7, 0.4),
                       emissive_intensity=4.0, shadows=False)
        glow_light(sconce, color=(1.0, 0.72, 0.45), intensity=2.5, range_=3.0)
    # The settings live at the console; the label sits at the glass.
    station(s, stations, "Mixer", "Mixer", (-H - 0.1, 1.45, 4.6), (1.75, 0.45, -1.3), 46, label="SETTINGS")


def booth(s, geo, items, stations, lights):
    """The vocal booth in the back left corner: the gig board on its front, RECORDING over its door."""
    bw, bd = BOOTH
    bx1 = -H + bw          # its side wall (the door's)
    bz0 = D - bd           # its front wall (the gig board's)
    textured(s.slab("Booth Front", geo, -H, bx1, 0.0, 2.6, bz0 - 0.12, bz0, (1, 1, 1), rough=0.95), "FabricRust", (2, 2.6))
    s.slab("Booth Side Front", geo, bx1, bx1 + 0.12, 0.0, 2.6, bz0 - 0.12, bz0 + 0.4, (0.16, 0.15, 0.15), rough=0.9)
    s.slab("Booth Side Back", geo, bx1, bx1 + 0.12, 0.0, 2.6, bz0 + 1.3, D, (0.16, 0.15, 0.15), rough=0.9)
    s.slab("Booth Side Header", geo, bx1, bx1 + 0.12, 2.1, 2.6, bz0 + 0.4, bz0 + 1.3, (0.16, 0.15, 0.15), rough=0.9)
    s.slab("Booth Roof", geo, -H, bx1 + 0.12, 2.6, 2.7, bz0 - 0.12, D, (0.12, 0.11, 0.11), rough=0.9)
    door = s.group("Booth Door", geo, (bx1 + 0.06, 0.0, bz0 + 0.4))
    door.components[0]["Rotation"] = [0.0, -70.0, 0.0]
    s.box("Booth Door Leaf", door, (0.0, 1.03, 0.45), (0.06, 2.06, 0.9), WALNUT, rough=0.5)
    s.box("Booth Door Glass", door, (0.035, 1.45, 0.45), (0.01, 0.5, 0.3), (0.3, 0.35, 0.4), rough=0.1, metallic=0.2)
    # Inside: the mic with its pop filter, a stool, a warm light.
    mic = (-H + 1.0, 0.0, bz0 + 1.0)
    rod(s, items, "Booth Mic Stand", mic, (mic[0], 1.5, mic[2]), 0.025, BLACK, metallic=0.5)
    s.box("Booth Mic", items, (mic[0], 1.6, mic[2] - 0.05), (0.07, 0.2, 0.07), (0.85, 0.85, 0.88), shape="Capsule", metallic=0.8)
    s.box("Pop Filter", items, (mic[0], 1.6, mic[2] - 0.2), (0.16, 0.16, 0.01), (0.1, 0.1, 0.1), rot=(90, 0, 0), shape="Cylinder", rough=0.5)
    s.prop("Booth Stool", items, "Assets/Models/Venue/Stool.obj", (mic[0] + 0.1, 0.0, mic[2] + 0.5), scale=0.9)
    light(s, lights, "Booth Light", (-H + 1.0, 2.4, bz0 + 1.0), color=(1.0, 0.72, 0.45), intensity=4.0, range_=3.0)
    # RECORDING, over the door: lit while the radio plays.
    sign = s.box("Recording Sign", items, (bx1 + 0.13, 2.35, bz0 + 0.85), (0.05, 0.18, 0.62), (0.4, 0.02, 0.02), emissive=(1.0, 0.06, 0.04),
                 emissive_intensity=4.0, shadows=False)
    motion(sign, "Pulse", amount=0.35, speed=0.25, music=True)
    scrawl(s, items, "Recording Word", (bx1 + 0.16, 2.35, bz0 + 0.85), "RECORDING", 0.1, (1.0, 0.92, 0.88), facing="+x", lit=False)
    glow = light(s, lights, "Recording Glow", (bx1 + 0.5, 2.3, bz0 + 0.85), color=(1.0, 0.1, 0.06), intensity=1.6, range_=2.5)
    motion(glow, "Pulse", amount=0.35, speed=0.25, music=True)
    # The gig board on the booth's front: the tour so far.
    gx = -H + 1.0
    textured(s.slab("Gig Board", geo, gx - 0.75, gx + 0.75, 1.1, 2.0, bz0 - 0.15, bz0 - 0.12, (1, 1, 1), rough=0.95), "Cork", (1.5, 0.9))
    s.slab("Gig Board Frame", geo, gx - 0.78, gx + 0.78, 2.0, 2.04, bz0 - 0.16, bz0 - 0.12, WALNUT)
    station(s, stations, "Gig Board", "GigBoard", (gx, 1.55, bz0 - 0.16), (0.3, 0.05, -1.7), 45)
    flyers = (("FlyerA", "FlyerBackyard", -0.45, 1.6, -3.0), ("FlyerB", "FlyerClub", -0.05, 1.5, 2.0), ("FlyerC", "FlyerFestival", 0.38, 1.62, -1.5))
    for slot_name, texture, dx, y, tilt in flyers:
        f = slot(s, items, f"Flyer {slot_name[-1]}", slot_name)
        poster(s, f, "Flyer", texture, (gx + dx, y, bz0 - 0.158), 0.27, 0.36, "-z", tilt=tilt)
        card = stand_in(s, items, f"{slot_name} Card", slot_name)
        s.box("Index Card", card, (gx + dx, y, bz0 - 0.158), (0.16, 0.11, 0.003), (0.97, 0.96, 0.9), rot=(0, 0, tilt), shadows=False)
        scrawl(s, card, "Card Text", (gx + dx, y, bz0 - 0.161), "TBA", 0.04, INK, font=MARKER, tilt=tilt)


def lounge(s, geo, items, stations, lights):
    """The right side: the couch under the window, the coffee table and the laptop, the turntable."""
    w0, w1, v0, v1 = LOUNGE_WIN
    wz = (w0 + w1) / 2
    # The window: blinds, half open, and the city beyond (day or night).
    for i in range(14):
        y = v0 + 0.05 + i * 0.1
        s.box(f"Blind Slat {i}", items, (H - 0.04, y, wz), (0.06, 0.008, w1 - w0 - 0.04), (0.9, 0.88, 0.82), rot=(0, 0, 35), rough=0.6, shadows=True)
    for z in (w0 + 0.3, w1 - 0.3):
        rod(s, items, f"Blind Cord {z}", (H - 0.06, v1, z), (H - 0.06, v0 - 0.3, z), 0.004, OFFWHITE, shadows=False)
    s.box("Blind Head", items, (H - 0.05, v1 + 0.03, wz), (0.08, 0.06, w1 - w0), (0.9, 0.88, 0.82))
    night = when(s.group("Night", lights), "Night")
    textured(s.box("City Night", night, (H + 3.0, 1.8, wz), (0.02, 3.0, 4.6), (1, 1, 1), shadows=False), "CityNight", emissive=True, emissive_intensity=1.2)
    light(s, night, "City Glow", (H - 0.5, 1.9, wz), color=(0.55, 0.62, 1.0), intensity=2.2, range_=4.0)
    day = when(s.group("Day", lights), "Day")
    textured(s.box("City Day", day, (H + 3.0, 1.8, wz), (0.02, 3.0, 4.6), (1, 1, 1), shadows=False), "CityDay", emissive=True, emissive_intensity=1.8)
    sun = (H + 2.6, 3.9, wz - 0.4)
    light(s, day, "Sun Through The Blinds", sun, kind="Spot", color=(1.0, 0.9, 0.72), intensity=140.0, range_=12.0,
          rot=look_rotation(sun, (H - 2.6, 0.0, wz + 0.4)), inner=12.0, outer=22.0, shadows=True, volumetric=7.0)
    light(s, day, "Sky Fill", (H - 0.6, 2.0, wz), color=(0.75, 0.85, 1.0), intensity=3.0, range_=5.0)
    # The couch under it, the rug, the coffee table with the laptop (and the lava lamp, once earned).
    s.prop("Couch", items, "Assets/Venues/Backyard/Models/Sofa.obj", (H - 0.5, 0.0, wz), yaw=-90.0)
    textured(s.box("Lounge Rug", items, (H - 1.5, 0.006, wz), (1.8, 0.01, 2.6), (1, 1, 1), rough=1.0, shadows=False), "RugBlue")
    tx, tz = H - 1.55, wz
    s.box("Coffee Table", items, (tx, 0.4, tz), (0.6, 0.05, 1.1), WALNUT, rough=0.4)
    for dx in (-0.25, 0.25):
        for dz in (-0.5, 0.5):
            s.box(f"Table Leg {dx} {dz}", items, (tx + dx, 0.19, tz + dz), (0.04, 0.38, 0.04), WALNUT)
    s.box("Laptop Base", stations, (tx, 0.435, tz - 0.15), (0.24, 0.02, 0.34), (0.75, 0.75, 0.78), metallic=0.8, rough=0.3)
    scr = s.group("Laptop Lid", stations, (tx - 0.12, 0.55, tz - 0.15))
    scr.components[0]["Rotation"] = [0.0, -90.0, 0.0]
    textured(s.box("Laptop Screen", scr, (0.0, 0.0, 0.0), (0.34, 0.22, 0.012), (1, 1, 1), rot=(-12, 0, 0), rough=0.2, shadows=False), "LaptopScreen",
             emissive=True, emissive_intensity=1.1)
    station(s, stations, "Laptop", "Laptop", (tx, 0.5, tz - 0.15), (-0.95, 0.5, -0.2), 40)
    for i, (dz, colour) in enumerate(((0.25, (0.6, 0.12, 0.1)), (0.38, (0.92, 0.9, 0.85)))):
        s.box(f"Mug {i}", items, (tx + 0.1, 0.47, tz + dz), (0.08, 0.1, 0.08), colour, shape="Cylinder", rough=0.4)
    lamp = slot(s, items, "Lava Lamp", "Lamp")
    blob = s.box("Lava", lamp, (tx, 0.58, tz + 0.42), (0.1, 0.3, 0.1), (0.9, 0.3, 0.6), shape="Capsule", emissive=(1.0, 0.25, 0.55), emissive_intensity=4.0)
    glow_light(blob, color=(1.0, 0.3, 0.6), intensity=1.5, range_=2.0)
    motion(blob, "Pulse", amount=0.3, speed=0.08)
    s.prop("Plant", items, "Assets/Venues/Backyard/Models/PottedPlant.obj", (H - 0.45, 0.0, 0.6), scale=1.3)
    s.box("Fig Trunk", items, (H - 0.45, 1.0, 0.6), (0.04, 1.2, 0.04), (0.35, 0.25, 0.15), shape="Cylinder")
    rnd = random.Random(717)
    for i in range(14):
        s.box(f"Fig Leaf {i}", items, (H - 0.45 + rnd.uniform(-0.3, 0.3), 1.3 + rnd.uniform(0, 0.6), 0.6 + rnd.uniform(-0.3, 0.3)), (0.22, 0.03, 0.15),
              (0.18, 0.4, 0.15), rot=(rnd.uniform(-30, 30), rnd.uniform(0, 180), rnd.uniform(-20, 20)), shape="Sphere", rough=0.7)
    # The turntable on its cabinet (the radio): the record turns, the meters bounce; records below.
    rx, rz = H - 0.4, 3.95
    s.box("Cabinet", items, (rx, 0.36, rz), (0.6, 0.72, 0.9), WALNUT, rough=0.5)
    radio = slot(s, items, "Turntable", "Radio")
    s.box("Plinth", radio, (rx, 0.77, rz - 0.15), (0.4, 0.08, 0.46), (0.18, 0.12, 0.08), rough=0.4)
    platter = s.entity("Platter", radio, (rx, 0.82, rz - 0.15))
    motion(platter, "Spin", speed=200.0, axis=(0, 1, 0))
    s.box("Record", platter, (0.0, 0.0, 0.0), (0.3, 0.008, 0.3), (0.04, 0.04, 0.045), shape="Cylinder", metallic=0.3, rough=0.25)
    s.box("Label", platter, (0.0, 0.005, 0.0), (0.1, 0.004, 0.1), (0.85, 0.2, 0.15), shape="Cylinder")
    s.box("Label Stripe", platter, (0.025, 0.008, 0.0), (0.04, 0.003, 0.01), (0.95, 0.9, 0.8))
    rod(s, radio, "Tonearm", (rx + 0.15, 0.86, rz + 0.02), (rx + 0.03, 0.84, rz - 0.2), 0.008, CHROME, metallic=0.9)
    amp = (rx, 0.84, rz + 0.3)
    s.box("Tube Amp", radio, amp, (0.36, 0.14, 0.26), (0.2, 0.2, 0.22), metallic=0.5, rough=0.4)
    for k, dz in enumerate((-0.07, 0.07)):
        tube = s.box(f"Valve {k}", radio, (amp[0] + 0.05, amp[1] + 0.12, amp[2] + dz), (0.04, 0.1, 0.04), (1.0, 0.6, 0.25), shape="Capsule",
                     emissive=(1.0, 0.5, 0.15), emissive_intensity=3.0, shadows=False)
        motion(tube, "Pulse", amount=0.3, speed=0.1, music=True)
    for k, dz in enumerate((-0.06, 0.06)):
        s.box(f"VU {k}", radio, (amp[0] - 0.181, amp[1], amp[2] + dz), (0.004, 0.06, 0.09), (1.0, 0.85, 0.5), emissive=(1.0, 0.75, 0.35),
              emissive_intensity=2.5, shadows=False)
        needle = s.entity(f"VU Needle {k}", radio, (amp[0] - 0.185, amp[1] - 0.025, amp[2] + dz))
        motion(needle, "Sway", amount=22.0, speed=0.6, axis=(1, 0, 0), music=True, phase=0.5 * k)
        s.box("Needle", needle, (0.0, 0.025, 0.0), (0.002, 0.05, 0.003), BLACK, shadows=False)
    boombox_display(s, radio, (rx - 0.302, 0.6, rz), "-x", width=0.36)
    station(s, stations, "Radio", "Radio", (rx, 0.85, rz), (-1.4, 0.55, -0.4), 40)
    shelf = slot(s, items, "Records", "Shelf")
    for i in range(12):
        s.box(f"Sleeve {i}", shelf, (rx - 0.05, 0.3, rz - 0.4 + i * 0.065), (0.32, 0.31, 0.02),
              [(0.8, 0.2, 0.2), (0.2, 0.5, 0.8), (0.9, 0.8, 0.2), (0.1, 0.1, 0.1), (0.9, 0.9, 0.85)][i % 5], rough=0.7)
    # A floor lamp by the couch.
    fl = (H - 0.5, 0.0, w0 - 0.35)
    rod(s, items, "Floor Lamp Pole", fl, (fl[0], 1.6, fl[2]), 0.025, BRASS, metallic=0.8)
    shade = s.box("Floor Lamp Shade", items, (fl[0], 1.65, fl[2]), (0.4, 0.3, 0.4), (0.9, 0.85, 0.72), shape="Cylinder", rough=0.9,
                  emissive=(1.0, 0.82, 0.55), emissive_intensity=0.9)
    glow_light(shade, color=(1.0, 0.78, 0.5), intensity=7.0, range_=5.0)


def right_wall(s, geo, items, stations, lights):
    """The gold and platinum, the trophies, the guitars, the Hammond and its Leslie."""
    tz = 3.95
    station(s, stations, "Trophy Wall", "TrophyWall", (H - 0.05, 2.15, tz), (-2.0, -0.25, -0.5), 50)
    # Platinum, always (the studio's own), and the band's gold once they have it.
    for i, (z, y) in enumerate(((tz - 0.55, 2.45), (tz + 0.55, 2.45))):
        s.box(f"Plat Frame {i}", items, (H - 0.03, y, z), (0.04, 0.5, 0.42), BLACK, rough=0.4)
        s.box(f"Plat Mat {i}", items, (H - 0.052, y, z), (0.004, 0.44, 0.36), (0.92, 0.9, 0.86))
        s.box(f"Plat Record {i}", items, (H - 0.058, y + 0.04, z), (0.28, 0.006, 0.28), PLATINUM, rot=(0, 0, 90), shape="Cylinder", metallic=0.75, rough=0.35, emissive=(0.5, 0.5, 0.55), emissive_intensity=0.25)
        s.box(f"Plat Plate {i}", items, (H - 0.058, y - 0.18, z), (0.004, 0.04, 0.16), GOLD, metallic=0.9, rough=0.25)
    rec = slot(s, items, "Gold Record", "GoldRecord")
    s.box("Gold Frame", rec, (H - 0.03, 2.45, tz), (0.04, 0.56, 0.46), BLACK, rough=0.4)
    s.box("Gold Mat", rec, (H - 0.052, 2.45, tz), (0.004, 0.5, 0.4), (0.92, 0.9, 0.86))
    s.box("Gold Disc", rec, (H - 0.058, 2.49, tz), (0.32, 0.006, 0.32), GOLD, rot=(0, 0, 90), shape="Cylinder", metallic=0.8, rough=0.3, emissive=(0.6, 0.45, 0.15), emissive_intensity=0.3)
    readout(scrawl(s, rec, "Gold Plate", (H - 0.06, 2.24, tz), "", 0.022, (0.1, 0.08, 0.04), facing="-x"), "BandName", max_letters=20, upper=True)
    gold_slot = stand_in(s, items, "Gold Goes Here", "GoldRecord")
    s.box("Empty Frame", gold_slot, (H - 0.03, 2.45, tz), (0.04, 0.56, 0.46), BLACK, rough=0.4)
    s.box("Empty Mat", gold_slot, (H - 0.052, 2.45, tz), (0.004, 0.5, 0.4), (0.92, 0.9, 0.86))
    scrawl(s, gold_slot, "Empty Note", (H - 0.056, 2.45, tz), "reserved:\nYOUR\nFIRST GOLD", 0.045, (0.3, 0.3, 0.32), facing="-x")
    for slot_name, z in (("PlaqueA", tz - 0.55), ("PlaqueB", tz + 0.55)):
        p = slot(s, items, slot_name, slot_name)
        s.box("Plaque", p, (H - 0.03, 1.7, z), (0.03, 0.32, 0.26), WALNUT, rough=0.5)
        s.box("Plate", p, (H - 0.05, 1.7, z), (0.01, 0.18, 0.18), GOLD, metallic=0.9, rough=0.25)
    head = slot(s, items, "Signed Snare Head", "WallLeft")
    s.box("Signed Head", head, (H - 0.03, 1.72, tz), (0.36, 0.01, 0.36), WHITE, rot=(0, 0, 90), shape="Cylinder", rough=0.6)
    scrawl(s, head, "Signature", (H - 0.04, 1.72, tz), "rock on!\n- T.", 0.045, (0.1, 0.1, 0.12), facing="-x", font=MARKER, tilt=12.0)
    band = slot(s, items, "Band Poster", "PosterA")
    s.box("Poster Frame", band, (H - 0.03, 1.85, 1.05), (0.03, 0.66, 0.46), BLACK)
    poster(s, band, "Poster", "PosterGhostNotes", (H - 0.05, 1.85, 1.05), 0.4, 0.6, "-x")
    poster(s, items, "Certificate", "Certificate", (H - 0.012, 1.65, 0.3), 0.4, 0.3, "-x", tilt=0.0)
    tally(s, items, (H - 0.012, 1.15, tz + 0.95), "-x", ink=INK)
    # The guitars, on stands along the wall.
    for i, (z, model) in enumerate(((5.0, "Guitar"), (5.45, "Guitar"), (5.9, "Bass"), (6.35, "Guitar"))):
        g = s.entity(f"Wall {model} {i}", items, (H - 0.32, 0.62 if model == "Guitar" else 0.66, z), (0.0, -100.0 + 8 * i, -80.0))
        g.add({"Type": "Model", "ModelPath": f"Assets/Models/Instruments/Runtime/{model}.obj"})
        rod(s, items, f"Guitar Stand {i}", (H - 0.35, 0.0, z), (H - 0.32, 0.5, z), 0.02, BLACK)
    # The Hammond and its Leslie in the back right corner.
    hx, hz = 2.75, D - 0.45
    s.box("Hammond", items, (hx, 0.5, hz), (1.25, 0.95, 0.6), WALNUT, rough=0.45)
    for k, y in enumerate((0.93, 1.03)):
        s.box(f"Manual {k}", items, (hx, y, hz - 0.2 + k * 0.08), (1.1, 0.04, 0.18), (0.95, 0.94, 0.9), rough=0.3)
        for n in range(15):
            if n % 7 not in (2, 6):
                s.box(f"Sharp {k} {n}", items, (hx - 0.5 + n * 0.07, y + 0.025, hz - 0.17 + k * 0.08), (0.03, 0.02, 0.1), BLACK)
    for n in range(9):
        s.box(f"Drawbar {n}", items, (hx - 0.2 + n * 0.05, 1.12, hz + 0.05), (0.02, 0.08 + 0.02 * (n % 3), 0.02),
              [(0.5, 0.25, 0.1), (0.1, 0.1, 0.1), (0.9, 0.9, 0.88)][n % 3])
    s.box("Hammond Bench", items, (hx, 0.3, hz - 0.75), (0.9, 0.06, 0.35), WALNUT)
    lx, lz = 3.95, D - 0.5
    s.box("Leslie", items, (lx, 0.6, lz), (0.6, 1.2, 0.55), WALNUT, rough=0.45)
    s.box("Leslie Louvre", items, (lx, 0.95, lz - 0.28), (0.5, 0.3, 0.01), (0.08, 0.06, 0.04))
    horn = s.entity("Leslie Horn", items, (lx, 0.95, lz))
    motion(horn, "Spin", speed=420.0, axis=(0, 1, 0))
    for k in (-1, 1):
        s.box(f"Horn {k}", horn, (k * 0.15, 0.0, 0.0), (0.24, 0.07, 0.07), (0.6, 0.6, 0.62), rot=(0, 0, 90), shape="Cylinder", metallic=0.7)


def practice_corner(s, items, stations):
    """Front left: the pad on its stand, the metronome, and the wishlist on the chart stand."""
    px, pz = -2.6, 2.3
    station(s, stations, "Practice Pad", "PracticePad", (px, 0.78, pz), (1.35, 0.6, -0.75), 40)
    rod(s, items, "Pad Stand", (px, 0.0, pz), (px, 0.7, pz), 0.025, CHROME, metallic=0.9)
    for k in range(3):
        a = math.radians(120 * k)
        rod(s, items, f"Pad Stand Leg {k}", (px + 0.25 * math.cos(a), 0.0, pz + 0.25 * math.sin(a)), (px, 0.25, pz), 0.018, CHROME, metallic=0.9)
    pad = slot(s, items, "Practice Pad", "PracticePad")
    s.box("Pad", pad, (px, 0.74, pz), (0.32, 0.035, 0.32), (0.12, 0.12, 0.12), shape="Cylinder", rough=0.9)
    s.box("Pad Rim", pad, (px, 0.725, pz), (0.34, 0.025, 0.34), (0.75, 0.1, 0.1), shape="Cylinder", rough=0.6)
    rod(s, pad, "Pad Stick", (px - 0.15, 0.77, pz - 0.05), (px + 0.2, 0.77, pz - 0.15), 0.014, (0.86, 0.72, 0.46))
    bare = stand_in(s, items, "No Pad Yet", "PracticePad")
    s.box("Bare Basket", bare, (px, 0.71, pz), (0.3, 0.02, 0.3), CHROME, shape="Cylinder", metallic=0.9)
    s.prop("Practice Stool", items, "Assets/Models/Venue/Stool.obj", (px + 0.45, 0.0, pz - 0.1), scale=0.8)
    met = slot(s, items, "Metronome", "Metronome")
    s.box("Metronome Table", met, (px - 0.5, 0.6, pz + 0.1), (0.35, 0.03, 0.35), WALNUT)
    rod(s, met, "Metronome Table Leg", (px - 0.5, 0.0, pz + 0.1), (px - 0.5, 0.6, pz + 0.1), 0.03, BLACK)
    s.box("Metronome", met, (px - 0.5, 0.71, pz + 0.1), (0.1, 0.18, 0.08), (0.45, 0.12, 0.08), rough=0.6)
    arm = s.entity("Metronome Arm", met, (px - 0.5, 0.65, pz + 0.05))
    motion(arm, "Sway", amount=25.0, speed=1.0, axis=(0, 0, 1))
    s.box("Arm", arm, (0.0, 0.08, 0.0), (0.006, 0.16, 0.006), CHROME, metallic=0.9, shadows=False)
    # The wishlist: on the chart stand by the kit, where the drummer would read it.
    ms = (-1.55, 0.0, 4.7)
    rod(s, items, "Chart Stand Pole", ms, (ms[0], 1.1, ms[2]), 0.015, BLACK, metallic=0.5)
    stand = s.group("Chart Stand", items, (ms[0], 1.22, ms[2]))
    stand.components[0]["Rotation"] = [-20.0, 0.0, 0.0]
    s.box("Chart Stand Desk", stand, (0.0, 0.0, 0.01), (0.5, 0.34, 0.01), BLACK, metallic=0.4)
    textured(s.box("Wishlist Page", stand, (0.0, 0.02, 0.0), (0.27, 0.35, 0.003), (1, 1, 1), rough=0.9, shadows=False), "NotebookRehearsal",
             emissive=True, emissive_intensity=0.25)
    wishes = ("gold-record", "teacher-certificate", "fc-plaque", "signed-snare-head", "neon-sign", "lava-lamp", "vinyl-shelf", "spare-cymbal", "stick-bag")
    for i, item in enumerate(wishes):
        readout(scrawl(s, stand, f"Wish {i}", (-0.098, 0.124 - i * 0.0202, -0.003), "", 0.017, INK, align="Left", anchor="Bottom"), "Wishlist", item=item)
    station(s, stations, "Wishlist", "Wishlist", (ms[0], 1.25, ms[2]), (0.2, 0.2, -0.85), 40)


def moving_in(s, items):
    """The first visit: flight cases from the van by the door."""
    cases = when(s.group("Moving In", items), "MovingIn")
    for i, (x, z, y, yaw) in enumerate(((-1.4, 0.4, 0.0, 10.0), (-1.3, 0.45, 0.62, -6.0), (1.3, 0.6, 0.0, -14.0))):
        g = s.group(f"Case {i}", cases, (x, y, z))
        g.components[0]["Rotation"] = [0.0, yaw, 0.0]
        s.box("Body", g, (0.0, 0.31, 0.0), (0.9, 0.62, 0.55), (0.06, 0.06, 0.065), rough=0.6)
        for yy in (0.02, 0.6):
            s.box(f"Edge {yy}", g, (0.0, yy, -0.28), (0.91, 0.03, 0.012), (0.7, 0.72, 0.74), metallic=0.8)
        scrawl(s, g, "Stencil", (0.0, 0.35, -0.282), "FRAGILE", 0.09, (0.95, 0.95, 0.92), font=MARKER)


def build_studio():
    s = Scene(seed=2104)
    root = s.group("Hideout Studio")
    geo = s.group("Room", root)
    items = s.group("Things", root)
    stations = s.group("Stations", root)
    lights = s.group("Lights", root)
    marks = s.group("Markers", root)
    shell(s, geo)
    side_walls(s, geo, items, lights)
    kit(s, geo, items, stations, lights)
    control_room(s, geo, items, stations, lights)
    booth(s, geo, items, stations, lights)
    lounge(s, geo, items, stations, lights)
    right_wall(s, geo, items, stations, lights)
    practice_corner(s, items, stations)
    moving_in(s, items)
    light(s, geo, "Fill", (0.4, 2.0, 0.4), color=(1.0, 0.86, 0.7), intensity=5.0, range_=8.0)
    # Track lights on a rail across the room, aimed at the walls: the trophies, the guitars, the
    # gig board, the glass.
    rod(s, geo, "Track Rail", (-3.4, TOP - 0.05, 3.0), (3.4, TOP - 0.05, 3.0), 0.04, BLACK, metallic=0.6)
    for i, (x, aim) in enumerate(((2.9, (H, 2.1, 3.95)), (3.3, (H, 1.2, 5.6)), (-2.6, (-H + 1.0, 1.5, D - 2.2)), (-3.2, (-H, 1.6, 2.4)))):
        at = (x, TOP - 0.15, 3.0)
        pitch, yaw, _ = look_rotation(at, aim)
        s.box(f"Track Head {i}", lights, at, (0.09, 0.16, 0.09), BLACK, rot=(pitch + 90.0, yaw, 0.0), shape="Cylinder", metallic=0.6)
        light(s, lights, f"Track Beam {i}", at, kind="Spot", color=(1.0, 0.86, 0.66), intensity=18.0, range_=8.0, rot=look_rotation(at, aim),
              inner=14.0, outer=28.0, volumetric=0.5)
    dust(s, lights, "Dust", (0.4, 1.6, 5.0), (4.0, 2.6, 3.2), count=200, rate=24.0)
    # The clock over the control room glass.
    cz, cy = 4.6, 2.95
    s.box("Clock", items, (-H + 0.02, cy, cz), (0.32, 0.03, 0.32), OFFWHITE, rot=(0, 0, 90), shape="Cylinder", rough=0.5)
    s.box("Clock Rim", items, (-H + 0.015, cy, cz), (0.35, 0.02, 0.35), BLACK, rot=(0, 0, 90), shape="Cylinder", rough=0.5)
    for k in range(12):
        a = math.radians(k * 30)
        s.box(f"Clock Tick {k}", items, (-H + 0.036, cy + 0.13 * math.cos(a), cz - 0.13 * math.sin(a)), (0.003, 0.02 if k % 3 == 0 else 0.01, 0.006),
              BLACK, rot=(-k * 30, 0, 0), shadows=False)
    clock_hands(s, items, (-H + 0.036, cy, cz), "+x", 0.15)
    tone = s.group("Room Tone", root)
    sound(s, tone, "Air", (0.0, TOP - 0.2, 3.0), "StudioAir", volume=0.2, near=1.0, far=10.0)
    sound(s, tone, "Leslie", (3.95, 0.9, D - 0.5), "AmpHum", volume=0.12, near=0.5, far=4.0)
    # The way in: from the drummer's shoulder, back out to the door.
    view(s, marks, (0.1, 1.75, -1.35), (0.2, 1.2, 6.0), 58.0, intro_eye=(0.75, 1.3, 4.5), intro_target=(0.4, 1.0, 6.4))
    return s
