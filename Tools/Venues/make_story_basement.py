#!/usr/bin/env python3
"""Writes Assets/Venues/StoryBasement/: story set 01, "In the Basement with My AirPods" (s01-basement).

    python3 Tools/Venues/make_story_basement.py

The player's own hideout basement (Tools/Hideout/basement.py, imported read-only through
story_basement_room.py), played as a rehearsal: the drummer alone on the hand-me-down kit, the cat
on the couch and mom's camcorder for an audience. Across the five songs (Design/Story-Mode-Setlists.json):

  tape_rolling           the camcorder's red tally lamp comes on; the CRT by the couch goes from snow to the take
  crt_turned_toward_kit  the CRT, crate and all, is dragged over and turned to face the kit
  window_well_blue       daylight in the window well goes to streetlamp blue; the kitchen door upstairs opens a crack
  kitchen_door_ajar      the door propped wide (the laundry basket): kitchen light all the way down the stairs
  crate_at_stairs        the milk crate, the old orange bucket and sticks in it, waits in that light at the foot
                         of the stairs; the CRT holds the take's last frame (PAUSE)

Room space is the hideout's, which is already venue space: +z from the stairs to the back wall, the
drummer at the back facing -z. Deterministic: rerun = same bytes.
"""
import math
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import story_basement_room as R  # noqa: E402
from story_basement_room import B, HG  # noqa: E402
from venuegen import Scene, look_rotation, repo_root, write_venue_json  # noqa: E402

ID = "StoryBasement"
TITLE = "In the Basement with My AirPods"
LOCAL = f"Assets/Venues/{ID}/"
TEX = LOCAL + "Textures/"
H, D, TOP, JOIST = B.H, B.D, B.TOP, B.JOIST

ORANGE = B.ORANGE
PLASTIC_RED = B.PLASTIC_RED
STICK = (0.86, 0.72, 0.46)
KITCHEN = (1.0, 0.78, 0.5)
STREET = (0.45, 0.6, 1.0)
CRT_A = ((2.15, 0.0, 3.82), (-0.6, -0.8))       # by the couch, facing the room (the hideout's)
CRT_B = ((1.62, 0.0, 3.02), None)               # dragged over to the kit, facing the drummer
DRUMMER = (0.0, 0.0, 5.3)
DRUMMER_HEAD = (0.0, 1.25, 5.25)
HINGE = (-3.1, TOP + 0.04, -1.72)
GAIN = 2.5   # the hideout's practicals, turned up for the venue's exposure


def own_tex(e, name, emissive=0.0, tile=(1, 1)):
    m = HG.material(e)
    m["DiffuseColor"] = [1.0, 1.0, 1.0]
    m["Textures"] = {"Diffuse": {"Path": TEX + name + ".png"}}
    if emissive:
        m["Textures"]["Emissive"] = {"Path": TEX + name + ".png"}
        m["EmissiveColor"] = [1.0, 1.0, 1.0]
        m["EmissiveIntensity"] = round(emissive, 4)
    m["Tiling"] = [tile[0], -tile[1]]
    m["Offset"] = [0.0, tile[1]]
    return e


def yaw_of(direction):
    return math.degrees(math.atan2(direction[0], direction[1]))


# ---- the camcorder ---------------------------------------------------------------------------

def camcorder(s, items, lights):
    """Mom's camcorder on its tripod at the front of the kit (the hideout's), its tally lamp gated."""
    base = (-0.95, 0.0, 3.05)
    target = (0.0, 0.95, 5.15)
    yaw = look_rotation(base, target)[1]
    tripod = s.prop("Tripod", items, "Assets/Models/Venue/CameraTripod.obj", base, yaw=yaw + 180.0, scale=0.82)
    lamp = (0.055, 1.32, -0.13)
    off = s.story("Tally Off", tripod, "tape_rolling", when_set=False, fade=0.0, pos=lamp)
    s.box("Tally Lamp (dark)", off, (0, 0, 0), (0.026, 0.026, 0.026), (0.2, 0.03, 0.03), shape="Sphere", shadows=False)
    on = s.story("Tape Rolling", tripod, "tape_rolling", fade=0.25, pos=lamp)
    s.box("Tally Lamp", on, (0, 0, 0), (0.03, 0.03, 0.03), (1, 0.05, 0.04), shape="Sphere", emissive=(1.0, 0.04, 0.03),
          emissive_intensity=40.0, shadows=False)
    s.box("Tally Halo", on, (0, 0, 0), (0.07, 0.07, 0.07), (1, 0.05, 0.04), shape="Sphere", emissive=(1.0, 0.03, 0.02),
          emissive_intensity=2.5, shadows=False)
    s.light("Tally Glow", on, (0.0, 0.05, -0.05), "Point", (1.0, 0.06, 0.04), 3.5, 2.4)
    # The flip-out viewfinder screen: dark, then the take.
    side = (-0.11, 1.27, -0.02)
    s.box("Viewfinder", tripod, side, (0.012, 0.07, 0.09), (0.05, 0.05, 0.055), shadows=False)
    vf = s.story("Viewfinder Live", tripod, "tape_rolling", fade=0.25, pos=side)
    own_tex(s.box("Viewfinder Picture", vf, (-0.007, 0, 0), (0.002, 0.058, 0.078), (1, 1, 1), shadows=False), "CrtTake", 1.6)
    return tripod


# ---- the CRT ---------------------------------------------------------------------------------

def crt(s, parent, name, pos, yaw, pictures, glow=5.0):
    """The TV on its milk crate (the hideout's): the picture is up to `pictures`, a list of
    (story args or None, texture, emissive)."""
    tv = s.group(name, parent, pos)
    s.box("TV Crate", tv, (0.0, 0.16, 0.0), (0.46, 0.32, 0.36), PLASTIC_RED, rough=0.6)
    s.box("Console", tv, (0.0, 0.345, 0.0), (0.3, 0.05, 0.22), (0.16, 0.16, 0.18), rough=0.4)
    body = s.entity("TV Body", tv, (0.0, 0.0, 0.0), (0.0, yaw, 0.0))
    s.box("Tube", body, (0.0, 0.58, 0.0), (0.52, 0.44, 0.46), (0.22, 0.21, 0.19), rough=0.55)
    s.box("Tube Back", body, (0.0, 0.57, -0.3), (0.38, 0.32, 0.18), (0.2, 0.19, 0.17), rough=0.6)
    s.box("Bezel", body, (0.0, 0.59, 0.231), (0.46, 0.36, 0.006), (0.08, 0.08, 0.085), rough=0.5, shadows=False)
    for i, (story, texture, emissive) in enumerate(pictures):
        holder = body
        if story:
            holder = s.story(f"Picture {i}", body, *story, pos=(0.0, 0.59, 0.236))
            at = (0.0, 0.0, 0.0)
        else:
            at = (0.0, 0.59, 0.236)
        own_tex(s.box("Screen", holder, at, (0.42, 0.32, 0.006), (1, 1, 1), rough=0.1, shadows=False), texture, emissive)
    for side in (-1, 1):
        HG.rod(s, body, f"Rabbit Ear {side}", (0.0, 0.8, -0.05), (side * 0.22, 1.18, -0.08), 0.008, HG.CHROME, metallic=0.9)
    s.box("Power Light", body, (0.18, 0.4, 0.232), (0.012, 0.012, 0.004), (0.1, 1, 0.2), emissive=(0.1, 1.0, 0.2),
          emissive_intensity=6.0, shadows=False)
    glow_at = s.entity("TV Glow", body, (0.0, 0.65, 0.55))
    glow_at.add({"Type": "Light", "LightType": "Point", "Color": [0.55, 0.7, 1.0], "Intensity": glow, "Range": 3.6,
                 "VolumetricMultiplier": 0.0})
    return tv, body


def crts(s, items):
    # By the couch, facing the room: snow until the tape rolls, then the take (the hideout's place).
    a = s.story("CRT By The Couch", items, "crt_turned_toward_kit", when_set=False, fade=0.9, pos=CRT_A[0])
    crt(s, a, "TV", (0, 0, 0), yaw_of(CRT_A[1]),
        [(("tape_rolling", False, 0.0), "CrtSnow", 0.7), (("tape_rolling", True, 0.0), "CrtTake", 0.9)])
    # Dragged to the front of the kit and turned so the drummer can watch the take while playing;
    # at the end it holds the last frame.
    pos = CRT_B[0]
    face = (DRUMMER_HEAD[0] - pos[0], DRUMMER_HEAD[2] - pos[2])
    b = s.story("CRT Turned To The Kit", items, "crt_turned_toward_kit", fade=0.9, pos=pos)
    crt(s, b, "TV", (0, 0, 0), yaw_of(face),
        [(("crate_at_stairs", False, 0.0), "CrtTake", 0.9), (("crate_at_stairs", True, 0.0), "CrtPause", 0.9)], glow=14.0)
    # Its coax, stretched back to the old spot, and the clean square of floor the crate left.
    HG.rod(s, b, "Coax", (0.12, 0.03, 0.1), (CRT_A[0][0] - pos[0] + 0.1, 0.02, CRT_A[0][2] - pos[2] + 0.15), 0.012, (0.05, 0.05, 0.05),
           shadows=False)
    s.box("Clean Square", b, (CRT_A[0][0] - pos[0], 0.0015, CRT_A[0][2] - pos[2]), (0.47, 0.002, 0.37), (0.62, 0.6, 0.57),
          rough=0.95, shadows=False)
    for k in range(4):
        dx, dz = (-0.22 + 0.44 * (k % 2), -0.2 + 0.4 * (k // 2))
        s.box(f"Drag Mark {k}", b, (CRT_A[0][0] - pos[0] + dx - 0.25, 0.0012, CRT_A[0][2] - pos[2] + dz - 0.36), (0.02, 0.002, 0.9),
              (0.14, 0.13, 0.12), rot=(0, 34, 0), rough=1.0, shadows=False)


# ---- the kitchen door at the top of the stairs ------------------------------------------------

def kitchen(s, geo, lights):
    """The doorway with the kitchen behind it (out of sight until the door opens)."""
    y0, y1 = TOP, 4.5
    plaster = (0.67, 0.61, 0.48)
    s.slab("Landing Wall Left", geo, -H, -3.1, y0, y1, -1.82, -1.72, plaster)
    s.slab("Landing Wall Right", geo, -2.28, B.STAIR_EDGE, y0, y1, -1.82, -1.72, plaster)
    s.slab("Landing Wall Header", geo, -3.1, -2.28, 4.38, y1, -1.82, -1.72, plaster)
    s.slab("Door Casing Head", geo, -3.16, -2.22, 4.38, 4.44, -1.7, -1.66, HG.OFFWHITE)
    for x in (-3.13, -2.25):
        s.slab(f"Door Casing {x}", geo, x - 0.03, x + 0.03, TOP + 0.04, 4.44, -1.7, -1.66, HG.OFFWHITE)
    s.slab("Threshold", geo, -3.1, -2.28, TOP, TOP + 0.045, -1.84, -1.7, (0.5, 0.4, 0.28))
    k = s.group("Kitchen", geo)
    lino = s.slab("Kitchen Floor", k, -4.6, -0.8, TOP, TOP + 0.04, -4.4, -1.82, (0.85, 0.82, 0.7))
    own_tex(lino, "KitchenLino", tile=(5, 4))
    warm = (0.93, 0.83, 0.58)
    s.slab("Kitchen Far Wall", k, -4.6, -0.8, TOP, 4.9, -4.5, -4.4, warm, emissive=warm, emissive_intensity=0.35)
    s.slab("Kitchen Left Wall", k, -4.7, -4.6, TOP, 4.9, -4.5, -1.82, warm, emissive=warm, emissive_intensity=0.25)
    s.slab("Kitchen Right Wall", k, -0.8, -0.7, TOP, 4.9, -4.5, -1.82, warm, emissive=warm, emissive_intensity=0.25)
    s.slab("Kitchen Ceiling", k, -4.7, -0.7, 4.9, 4.95, -4.5, -1.82, (0.9, 0.88, 0.8))
    # Cupboards and the counter along the far wall, the fridge, a calendar, the window over the sink.
    s.slab("Counter Base", k, -4.0, -1.4, TOP, TOP + 0.9, -4.4, -3.8, (0.62, 0.42, 0.25))
    s.slab("Counter Top", k, -4.05, -1.35, TOP + 0.9, TOP + 0.94, -4.42, -3.76, (0.85, 0.85, 0.82), rough=0.4)
    s.slab("Wall Cupboards", k, -4.0, -1.4, TOP + 1.45, TOP + 2.1, -4.4, -4.05, (0.62, 0.42, 0.25))
    s.slab("Fridge", k, -1.38, -0.82, TOP, TOP + 1.75, -4.4, -3.75, (0.9, 0.9, 0.88), rough=0.35)
    s.box("Kettle", k, (-2.4, TOP + 1.04, -4.1), (0.16, 0.2, 0.16), (0.75, 0.15, 0.12), shape="Cylinder", rough=0.4)
    s.box("Mug", k, (-2.15, TOP + 0.99, -3.95), (0.08, 0.1, 0.08), (0.95, 0.95, 0.9), shape="Cylinder")
    win = s.slab("Kitchen Window", k, -3.4, -2.6, TOP + 1.0, TOP + 1.5, -4.395, -4.385, STREET, emissive=(0.12, 0.2, 0.42),
                 emissive_intensity=1.0, shadows=False)
    s.slab("Chair", k, -2.0, -1.6, TOP, TOP + 0.45, -2.9, -2.5, (0.55, 0.36, 0.2))
    s.slab("Chair Back", k, -2.0, -1.96, TOP + 0.45, TOP + 0.95, -2.9, -2.5, (0.55, 0.36, 0.2))
    pendant = s.box("Kitchen Pendant", k, (-2.7, 4.55, -3.0), (0.32, 0.14, 0.32), KITCHEN, shape="Sphere", emissive=KITCHEN,
                    emissive_intensity=6.0, shadows=False)
    HG.rod(s, k, "Pendant Cord", (-2.7, 4.9, -3.0), (-2.7, 4.6, -3.0), 0.01, HG.BLACK, shadows=False)
    s.light("Kitchen Light", k, (-2.7, 4.3, -3.0), "Point", KITCHEN, 9.0, 4.0)
    del win, pendant


def door(s, parent, name, angle):
    pivot = s.entity(name, parent, HINGE, (0.0, angle, 0.0))
    s.slab("Door", pivot, 0.0, 0.82, 0.0, 1.99, -0.04, 0.0, HG.OFFWHITE, rough=0.6)
    for y in (0.55, 1.45):
        s.slab(f"Door Panel {y}", pivot, 0.12, 0.7, y - 0.33, y + 0.33, 0.0, 0.006, (0.76, 0.74, 0.68), rough=0.6)
    s.box("Door Knob", pivot, (0.72, 0.97, 0.03), (0.055, 0.055, 0.07), HG.BRASS, shape="Sphere", metallic=0.7)
    s.box("Door Knob Back", pivot, (0.72, 0.97, -0.07), (0.055, 0.055, 0.07), HG.BRASS, shape="Sphere", metallic=0.7)
    return pivot


def kitchen_door(s, items, lights):
    closed = s.story("Kitchen Door Shut", items, "window_well_blue", when_set=False, fade=0.0, pos=HINGE)
    door(s, closed, "Kitchen Door", 0.0)
    # The crack (song 3): the door has come open a hand's width, a sliver of kitchen down the stairs.
    rel = lambda p: (p[0] - HINGE[0], p[1] - HINGE[1], p[2] - HINGE[2])  # noqa: E731
    crack = s.story("Kitchen Door Cracked", items, "window_well_blue", fade=1.5, pos=HINGE)
    only = s.story("Until It's Propped", crack, "kitchen_door_ajar", when_set=False, fade=0.0, pos=(0, 0, 0))
    door(s, only, "Kitchen Door", 16.0)
    eye = (-2.62, 3.75, -2.05)
    s.light("Kitchen Sliver", crack, (eye[0] - HINGE[0], eye[1] - HINGE[1], eye[2] - HINGE[2]), "Spot", KITCHEN, 70.0, 7.5,
            rot=look_rotation(eye, (-2.62, 0.7, 1.1)), inner=5.0, outer=10.0)
    # Where the sliver lands: a thin stripe of light down the middle of the treads.
    for i in range(2, 10):
        y, z = 0.2 * (i + 1), 1.62 - 0.27 * i
        s.box(f"Sliver On Tread {i}", crack, rel((-2.62, y + 0.002, z)), (0.09 + 0.012 * (10 - i), 0.004, 0.25), KITCHEN,
              emissive=KITCHEN, emissive_intensity=0.9, shadows=False)
    # Propped open (song 4): someone upstairs wants to hear the take. The laundry basket holds it.
    ajar = s.story("Kitchen Door Propped", items, "kitchen_door_ajar", fade=1.5, pos=HINGE)
    door(s, ajar, "Kitchen Door", 78.0)
    basket = s.group("Laundry Basket", ajar, rel((-2.92, TOP + 0.04, -2.12)))
    s.box("Basket", basket, (0.0, 0.14, 0.0), (0.42, 0.28, 0.32), (0.25, 0.45, 0.75), rough=0.6)
    s.box("Towels", basket, (0.0, 0.29, 0.0), (0.38, 0.08, 0.28), (0.92, 0.9, 0.84), shape="Sphere", rough=1.0)
    s.box("Red Sock", basket, (0.1, 0.33, 0.06), (0.12, 0.04, 0.06), (0.8, 0.15, 0.15), rough=1.0)
    eye = (-2.68, 4.0, -2.35)
    s.light("Kitchen Down The Stairs", ajar, rel(eye), "Spot", KITCHEN, 160.0, 9.0, rot=look_rotation(eye, (-2.55, 0.0, 2.0)),
            inner=13.0, outer=24.0)
    s.light("Kitchen Spill", ajar, rel((-2.7, 2.9, -1.2)), "Point", KITCHEN, 10.0, 3.5)
    # The rectangle of kitchen light, all the way down the flight and out across the floor.
    for i in range(0, 10):
        y, z = 0.2 * (i + 1), 1.62 - 0.27 * i
        s.box(f"Light On Tread {i}", ajar, rel((-2.66, y + 0.003, z + 0.02)), (0.5 + 0.03 * (10 - i), 0.004, 0.22), KITCHEN,
              emissive=KITCHEN, emissive_intensity=0.55, shadows=False)
    pool = s.box("Light On The Floor", ajar, rel((-2.35, 0.003, 2.25)), (1.1, 0.004, 1.0), KITCHEN, rot=(0, 6, 0),
                 emissive=KITCHEN, emissive_intensity=0.8, shadows=False)
    HG.material(pool)["Roughness"] = 1.0
    # A mug of tea left on the top step: whoever it was sat and listened for a while.
    mug = s.group("Tea On The Top Step", ajar, rel((-2.95, 2.2, -1.06)))
    s.box("Tea Mug", mug, (0.0, 0.05, 0.0), (0.085, 0.1, 0.085), (0.25, 0.5, 0.38), shape="Cylinder", rough=0.5)
    s.box("Tea", mug, (0.0, 0.098, 0.0), (0.07, 0.004, 0.07), (0.42, 0.25, 0.12), shape="Cylinder")


# ---- the crate at the foot of the stairs ------------------------------------------------------

def bucket(s, parent, name, pos):
    s.box(name, parent, pos, (0.3, 0.38, 0.3), ORANGE, shape="Cylinder", rough=0.55)
    s.box(name + " Rim", parent, (pos[0], pos[1] - 0.178, pos[2]), (0.32, 0.024, 0.32), (0.85, 0.35, 0.06), shape="Cylinder")


def milk_crate(s, parent, pos, yaw):
    c = s.entity("Milk Crate", parent, pos, (0.0, yaw, 0.0))
    blue = (0.1, 0.24, 0.62)
    w, h = 0.37, 0.29
    s.box("Crate Floor", c, (0, 0.012, 0), (w, 0.024, w), blue, rough=0.6)
    for x in (-1, 1):
        for z in (-1, 1):
            s.box(f"Crate Post {x}{z}", c, (x * (w / 2 - 0.015), h / 2, z * (w / 2 - 0.015)), (0.03, h, 0.03), blue, rough=0.6)
    for y in (0.03, 0.13, 0.27):
        for k, (dx, dz, sx, sz) in enumerate(((0, w / 2 - 0.01, w, 0.02), (0, -w / 2 + 0.01, w, 0.02), (w / 2 - 0.01, 0, 0.02, w),
                                               (-w / 2 + 0.01, 0, 0.02, w))):
            s.box(f"Crate Rail {y} {k}", c, (dx, y, dz), (sx, 0.035 if y > 0.2 else 0.025, sz), blue, rough=0.6)
    for k in range(5):
        x = -w / 2 + 0.06 + k * (w - 0.12) / 4
        for dz in (w / 2 - 0.01, -w / 2 + 0.01):
            s.box(f"Crate Bar {k} {dz}", c, (x, 0.2, dz), (0.018, 0.12, 0.02), blue, rough=0.6)
    return c


def crate_at_stairs(s, items, named):
    # The old bucket leaves the kit...
    home = (-1.0, 0.0, 3.75)
    stays = s.story("Bucket By The Kit", items, "crate_at_stairs", when_set=False, fade=0.9, pos=home)
    for nm in ("Bucket 0", "Bucket Rim 0", "Bucket Stick L", "Bucket Stick R"):
        e = named[nm]
        R.reparent(s, e, stays)
        p = e.components[0]["Position"]
        e.components[0]["Position"] = [round(p[0] - home[0], 4), round(p[1] - home[1], 4), round(p[2] - home[2], 4)]
    # ...and waits in a milk crate in the kitchen light at the foot of the stairs, sticks in it,
    # the phone speaker on top: ready for the station.
    at = (-2.1, 0.0, 2.35)
    g = s.story("The Crate At The Stairs", items, "crate_at_stairs", fade=1.2, pos=at)
    c = milk_crate(s, g, (0, 0, 0), 9.0)
    s.light("On The Crate", g, (0.25, 1.1, -0.5), "Point", KITCHEN, 8.0, 2.2)
    bucket(s, c, "Old Orange Bucket", (0.0, 0.215, 0.0))
    for k, (dx, dz, lean) in enumerate(((0.03, 0.02, 12), (-0.02, 0.04, 18), (0.0, -0.03, 8))):
        top = (dx + math.sin(math.radians(lean)) * 0.4, 0.35 + 0.38, dz + 0.1)
        HG.rod(s, c, f"Stick {k}", (dx, 0.08, dz), top, 0.015, STICK)
    s.box("Phone Speaker", c, (0.1, 0.43, -0.06), (0.15, 0.07, 0.07), (0.07, 0.07, 0.08), rot=(0, 20, 0), rough=0.5)
    s.box("Speaker Grille", c, (0.1, 0.43, -0.096), (0.13, 0.05, 0.004), (0.2, 0.2, 0.22), rot=(0, 20, 0), rough=0.8)
    s.box("Tag Tape", c, (0.0, 0.2, -0.19), (0.2, 0.06, 0.004), (0.86, 0.8, 0.62), rough=0.9, shadows=False)
    HG.scrawl(s, c, "Tag", (0.0, 0.2, -0.193), "SAT - SUBWAY", 0.032, (0.12, 0.16, 0.42), facing="-z", font=HG.MARKER)


# ---- the kit's corner -------------------------------------------------------------------------

def kit_dressing(s, items):
    """The hand-me-down kit on its carpet offcut; the phone and earbuds it's playing along to."""
    off = s.box("Carpet Offcut", items, (0.05, 0.007, 4.35), (2.7, 0.014, 2.35), (0.62, 0.55, 0.5), rot=(0, -4, 0), rough=1.0, shadows=False)
    HG.textured(off, "CarpetDark", (3, 2.6))
    for k, (x, z, w, d, yaw) in enumerate(((-1.25, 3.25, 0.3, 0.2, 20), (1.32, 5.48, 0.25, 0.3, -15))):
        s.box(f"Frayed Corner {k}", items, (x, 0.006, z), (w, 0.012, d), (0.55, 0.5, 0.46), rot=(0, yaw, 0), rough=1.0, shadows=False)
    tape = (0.75, 0.74, 0.7)
    for k, (x, z) in enumerate(((-0.55, 3.62), (0.62, 3.7))):
        for r in (45, -45):
            s.box(f"Spike Tape {k} {r}", items, (x, 0.016, z), (0.14, 0.002, 0.025), tape, rot=(0, r, 0), rough=0.9, shadows=False)
    # The phone on the amp, earbuds case open beside it.
    amp_top = 0.64
    s.box("Phone", items, (1.36, amp_top + 0.006, 4.6), (0.075, 0.009, 0.15), (0.05, 0.05, 0.06), rot=(0, 12, 0), rough=0.3)
    own_tex(s.box("Phone Screen", items, (1.36, amp_top + 0.0115, 4.6), (0.066, 0.002, 0.135), (1, 1, 1), rot=(0, 12, 0), shadows=False),
            "PhoneScreen", 1.2)
    s.box("Earbud Case", items, (1.6, amp_top + 0.02, 4.62), (0.06, 0.04, 0.05), (0.95, 0.95, 0.94), shape="Capsule", rot=(0, 0, 90), rough=0.3)
    s.box("Earbud", items, (1.66, amp_top + 0.012, 4.52), (0.018, 0.024, 0.018), (0.95, 0.95, 0.94), shape="Sphere", rough=0.3)
    # A spare pair of sticks and a towel on the floor by the throne.
    HG.rod(s, items, "Spare Stick A", (0.72, 0.012, 5.62), (1.08, 0.012, 5.4), 0.015, STICK)
    HG.rod(s, items, "Spare Stick B", (0.74, 0.012, 5.66), (1.1, 0.012, 5.46), 0.015, STICK)
    s.box("Towel", items, (-0.85, 0.02, 5.75), (0.38, 0.04, 0.3), (0.85, 0.3, 0.25), rot=(0, 18, 0), shape="Sphere", rough=1.0)


# ---- the build ---------------------------------------------------------------------------------

def build():
    s = Scene(seed="story-basement-v1")
    root = s.group(TITLE)
    geo = s.group("Room", root)
    items = s.group("Things", root)
    stations = s.group("Hideout Props", root)
    lights = s.group("Lights", root)
    marks = s.group("Venue markers", root)
    R.build_room(s, geo, items, stations, lights)
    named = R.venue_safe(s, drop_names=("Kitchen Door", "Kitchen Door Knob", "Landing Wall", "Kick Logo", "Kick Logo Blank",
                                        "Band Name On The Kick", "TV", "Upstairs"), light_gain=GAIN)
    story = s.group("Story", root)
    camcorder(s, story, lights)
    crts(s, story)
    kitchen(s, geo, lights)
    kitchen_door(s, story, lights)
    crate_at_stairs(s, story, named)
    kit_dressing(s, items)

    # Light: the hideout's practicals stay (the bare bulb, the tube, the desk lamp, the heater, the
    # window well); the Christmas lights chase the show's washes; a clamp light on the joist is the
    # drummer's follow spot. The one shadowed light is a faint directional, which the house blocks.
    s.light("Upstairs Hall", lights, (-2.7, 3.45, -0.8), "Point", (1.0, 0.76, 0.48), 5.0, 3.5)
    s.light("Stairwell Fill", lights, (-2.2, 1.3, 0.9), "Point", (1.0, 0.8, 0.6), 3.0, 3.2)
    for i, e in enumerate(k for k in s.entities if k.name.startswith("Bulb ") and R.comp(k, "Light") and k.parent.name == "Christmas Lights"):
        e.add({"Type": "VenueShowLight", "Kind": "Wash", "Group": i % 3})
    clamp = (0.95, JOIST - 0.08, 2.75)
    s.box("Clamp Light", lights, clamp, (0.14, 0.14, 0.14), (0.75, 0.6, 0.3), shape="Cylinder",
          rot=(look_rotation(clamp, DRUMMER_HEAD)[0] + 90, look_rotation(clamp, DRUMMER_HEAD)[1], 0), metallic=0.6, rough=0.4)
    s.light("Clamp Light Beam", lights, clamp, "Spot", (1.0, 0.86, 0.7), 14.0, 6.0, rot=look_rotation(clamp, DRUMMER_HEAD),
            inner=16.0, outer=34.0, show="Spot")
    s.light("Sky Over The House", lights, (0, 20, 0), "Directional", (0.6, 0.7, 1.0), 0.2, rot=(55, -30, 0), shadows=True, show="Static")

    s.info(marks, TITLE, "Drumsmith", room_back=-1.6, room_ceiling=JOIST, half_width=H, desk_z=-1.4,
           ambient=(0.012, 0.01, 0.008), fog_color=(0.02, 0.017, 0.014), haze=0.5)
    s.spot(marks, "Drummer", DRUMMER)
    cams = s.group("Camera positions", marks)
    shots = [
        ("couch-corner", "Wide", (2.6, 1.75, -1.25), (-1.0, 0.85, 3.6), 68),
        ("joists", "Crane", (0.35, 2.05, 0.4), (-0.1, 0.85, 5.0), 60),
        ("top-of-stairs", "Desk", (-2.7, 2.5, -0.9), (0.0, 0.95, 5.1), 34),
        ("snare-side", "Close", (0.95, 1.35, 3.35), DRUMMER_HEAD, 50),
        ("camcorder", "Custom", (-0.78, 1.05, 3.3), (0.0, 1.0, 5.15), 44),
        ("over-the-shoulder", "Custom", (0.55, 1.5, 5.75), (1.62, 0.62, 3.02), 55),
        ("up-the-stairs", "Custom", (-2.0, 1.2, 2.45), (-2.75, 3.1, -1.6), 62),
        ("window-well", "Custom", (-0.6, 0.9, 2.1), (1.9, 1.9, 6.0), 50),
    ]
    for tag, kind, eye, aim, lens in shots:
        s.camera_spot(tag, cams, eye, aim, kind, lens, tag)
    # Down the stairs from the kitchen: the hideout's way in.
    walk = [((-2.7, 3.3, -1.4), (-2.7, 2.2, 1.2), 70), ((-2.7, 2.85, -0.75), (-2.3, 1.6, 2.4), 68),
            ((-2.65, 2.3, 0.1), (-1.6, 1.1, 3.4), 66), ((-2.3, 1.75, 1.05), (-0.6, 1.0, 4.4), 64),
            ((-1.5, 1.5, 1.7), (0.0, 1.0, 5.0), 60)]
    for i, (eye, aim, lens) in enumerate(walk):
        s.camera_spot(f"Arrival {i + 1:02}", cams, eye, aim, "Custom", lens, f"arrival/{i + 1:02}")
    return s


def main():
    folder = os.path.join(repo_root(), "Assets", "Venues", ID)
    scene = build()
    scene.write(os.path.join(folder, ID + ".lvl"))
    preview = "Preview.jpg" if os.path.isfile(os.path.join(folder, "Preview.jpg")) else None
    ambience = "Ambience.wav" if os.path.isfile(os.path.join(folder, "Ambience.wav")) else None
    write_venue_json(folder, TITLE, ID + ".lvl", preview=preview, ambience=ambience)
    print(f"{len(scene.entities)} entities in {folder}")


if __name__ == "__main__":
    main()
