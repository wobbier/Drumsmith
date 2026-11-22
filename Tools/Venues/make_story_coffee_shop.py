#!/usr/bin/env python3
"""Writes Assets/Venues/StoryCoffeeShop/: story set 03, "The Millennial Coffee Shop" (s03-coffee-shop).

    python3 Tools/Venues/make_story_coffee_shop.py [--textures]

A small third-wave café, Second Pour, on a sunny morning. The house kit sits on a rug where a two-top
used to be, the regulars close on three sides, the bar behind it with the espresso machine and its
steam wand, the chalkboard over the bar announcing "an intimate acoustic session", Edison bulbs,
plants, a brick wall and big front windows letting the sun in across the floor.

The five story flags (Design/Story-Mode-Setlists.json):
  guitar_at_counter   Jules leaves the stool by the kit; the guitar goes on a stand by the till and
                      Jules goes back behind the bar to the steam wand.
  laptop_lowered      On the two-top by the window the laptop lid drops to half mast; the couple
                      look up over it at the kit.
  chairs_turned       The pair at the right-hand table turn their chairs to the kit; the backpack
                      goes under the table and its chair is pulled into the light by the kit.
  spare_chair_filled  Someone sits in that chair, swaying with the other two.
  wand_off            The steam cuts out; Jules claps over the bar; an untouched cup waits on the pass.

Deterministic: rerun = same bytes. Textures (story_coffee_shop_textures.py) are drawn when missing
or with --textures; posed people and motions come from story_coffee_shop_people.py.
"""
import math
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
from venuegen import Scene, look_rotation, repo_root, vec, write_venue_json, _r  # noqa: E402
import story_coffee_shop_people as people  # noqa: E402
import story_coffee_shop_sound as sound  # noqa: E402
import story_coffee_shop_textures as textures  # noqa: E402

ID = "StoryCoffeeShop"
VENUE = f"Assets/Venues/{ID}"
TEX = f"{VENUE}/Textures/"
MOD = f"{VENUE}/Models/"
SYNTY = "/home/mitch/Projects/MitchGame/Assets/Models/Synty"

# Synty props copied into Models/ (pack file -> our name). See Models/README.md.
SYNTY_PROPS = {
    "OfficePack/FBX/SM_Prop_CoffeeMachine_01.fbx": "EspressoMachine.fbx",
    "OfficePack/FBX/SM_Prop_Chair_09.fbx": "CafeChair.fbx",
    "OfficePack/FBX/SM_Prop_Chair_05.fbx": "CafeChairArm.fbx",
    "OfficePack/FBX/SM_Prop_Table_Round_01.fbx": "TwoTop.fbx",
    "OfficePack/FBX/SM_Prop_Cup_01.fbx": "CafeCup.fbx",
    "OfficePack/FBX/SM_Prop_Plant_01.fbx": "PlantTall.fbx",
    "OfficePack/FBX/SM_Prop_Plant_02.fbx": "PlantSnake.fbx",
    "OfficePack/FBX/SM_Prop_Plant_03.fbx": "PlantTrough.fbx",
    "OfficePack/FBX/SM_Prop_Plant_07.fbx": "PlantBig.fbx",
    "OfficePack/FBX/SM_Prop_Plant_09.fbx": "PlantPot.fbx",
    "OfficePack/FBX/SM_Prop_Plant_11.fbx": "PlantSmall.fbx",
    "OfficePack/FBX/SM_Prop_Kettle_01.fbx": "Kettle.fbx",
    "ExplorerKit/FBX/SM_Prop_Bag_01.fbx": "Bag.fbx",
    "ExplorerKit/FBX/SM_Chr_Attach_Backpack_01.fbx": "Backpack.fbx",
}
SYNTY_TEXTURES = {
    "OfficePack/Textures/PolygonOffice_Texture_01_A.png": "PolygonOffice_Texture_01_A_New.png",
    "ExplorerKit/Textures/PolygonExplorers_Texture_01_A.png": "PolygonExplorers_Texture_01_A.png",
}

# Shared, read-only.
STOOL = "Assets/Models/Venue/Stool.obj"
RUG = "Assets/Models/Venue/DrumRug.obj"
GUITAR = "Assets/Models/Instruments/Runtime/Guitar.obj"
CABLE = "Assets/Models/Venue/CableCoil.obj"

# Room, venue space (crowd faces +z; the band faces -z).
X0, X1, Z0, Z1, H = -6.0, 6.0, -7.5, 6.5, 3.8
DRUMMER = (0.0, 0.0, 2.75)
KIT_CENTRE = (0.0, 1.0, 1.8)

# Palette.
GREEN = (0.08, 0.2, 0.16)
CREAM = (0.78, 0.71, 0.58)
WALNUT = (0.26, 0.15, 0.09)
OAK = (0.62, 0.44, 0.27)
BUTCHER = (0.7, 0.52, 0.32)
BRASS = (0.8, 0.6, 0.28)
CHROME = (0.8, 0.8, 0.82)
BLACK = (0.04, 0.04, 0.045)
AMBER = (1.0, 0.7, 0.4)
SUN = (1.0, 0.86, 0.66)


def textured(e, name, tile=(1.0, 1.0), emissive=0.0, tint=(1, 1, 1), cutoff=None):
    """A drawn texture (Textures/<name>.png) on a primitive, upright, repeated tile times."""
    for comp in e.components:
        if comp.get("Type") == "Mesh":
            m = comp["Material"]
    m["DiffuseColor"] = vec(tint)
    m["Textures"] = {"Diffuse": {"Path": TEX + name + ".png"}}
    if emissive:
        m["Textures"]["Emissive"] = {"Path": TEX + name + ".png"}
        m["EmissiveColor"] = [1.0, 1.0, 1.0]
        m["EmissiveIntensity"] = _r(emissive)
    if cutoff is not None:
        m["AlphaCutoff"] = _r(cutoff)
    m["Tiling"] = [_r(tile[0]), _r(-tile[1])]
    m["Offset"] = [0.0, _r(tile[1])]
    return e


def see_through(e, opacity):
    for comp in e.components:
        if comp.get("Type") == "Mesh":
            comp["Material"]["RenderMode"] = 1
            comp["Material"]["Opacity"] = _r(opacity)
            comp["CastShadows"] = False
    return e


def rod(s, parent, name, a, b, d, color, metallic=0.0, rough=0.6, emissive=None, ei=1.0, shadows=True):
    """A cylinder from a to b."""
    length = math.dist(a, b)
    centre = tuple((a[i] + b[i]) / 2 for i in range(3))
    pitch, yaw, _ = look_rotation(a, b)
    return s.box(name, parent, centre, (d, length, d), color, rot=(pitch + 90.0, yaw, 0.0), shape="Cylinder",
                 metallic=metallic, rough=rough, emissive=emissive, emissive_intensity=ei, shadows=shadows)


def model(s, parent, name, file, pos, yaw=0.0, scale=1.0):
    path = file if file.startswith("Assets/") else MOD + file
    if isinstance(scale, (int, float)):
        return s.prop(name, parent, path, pos, yaw, scale)
    e = s.entity(name, parent, pos, (0, yaw, 0), scale)
    e.add({"Type": "Model", "ModelPath": path})
    return e


def facing(frm, to):
    """Yaw that turns a regular (who faces +z at 0) at frm toward to."""
    return math.degrees(math.atan2(to[0] - frm[0], to[2] - frm[2]))


# ---- the room ------------------------------------------------------------------------------------

def shell(s, root):
    g = s.group("Room", root)
    floor = s.slab("Oak floor", g, X0, X1, -0.2, 0.0, Z0, Z1, (1, 1, 1))
    textured(floor, "Floor", ((X1 - X0) / 2, (Z1 - Z0) / 2), tint=(0.9, 0.93, 1.0))
    s.slab("Ceiling", g, X0 - 0.2, X1 + 0.2, H, H + 0.15, Z0 - 0.2, Z1 + 0.2, (0.62, 0.56, 0.48))
    for i, z in enumerate((-6.0, -3.6, -1.2, 1.2, 3.6, 5.8)):
        s.slab(f"Beam {i + 1}", g, X0, X1, H - 0.22, H, z - 0.09, z + 0.09, (0.2, 0.12, 0.07))
    rod(s, g, "Duct", (3.4, H - 0.42, Z0), (3.4, H - 0.42, Z1), 0.36, (0.36, 0.36, 0.37), metallic=0.2, rough=0.9)

    # Brick down the right-hand side.
    brick = s.slab("Brick wall", g, X1, X1 + 0.25, 0, H, Z0, Z1, (1, 1, 1))
    textured(brick, "Brick", ((Z1 - Z0) / 2, H))
    # The back wall: painted green, subway tile behind the bar.
    s.slab("Back wall", g, X0, X1, 0, H, Z1, Z1 + 0.2, GREEN)
    tile = s.slab("Bar tile", g, -4.2, 3.6, 0.9, 2.05, Z1 - 0.02, Z1, (1, 1, 1), shadows=False)
    textured(tile, "Tile", (7.8 / 0.6, 1.15 / 0.6))
    # The front wall behind the crowd: cream plaster, wainscot.
    s.slab("Front wall", g, X0, X1, 0, H, Z0 - 0.2, Z0, CREAM)
    s.slab("Front wainscot", g, X0, X1, 0, 1.0, Z0, Z0 + 0.03, GREEN)

    # The storefront down the left: a green-painted frame, big panes, the door at the front.
    sf = s.group("Storefront", g)
    s.slab("Stallriser", sf, X0 - 0.12, X0 + 0.05, 0, 0.5, Z0, Z1, GREEN)
    s.slab("Fascia", sf, X0 - 0.12, X0 + 0.05, 3.0, H, Z0, Z1, GREEN)
    s.slab("Back pier", sf, X0 - 0.12, X0 + 0.05, 0, H, 5.6, Z1, GREEN)
    s.slab("Transom bar", sf, X0 - 0.1, X0 + 0.04, 2.5, 2.6, Z0, 5.6, GREEN)
    for z in (-7.5, -5.6, -2.9, -0.2, 2.6, 5.6):
        s.slab(f"Mullion {z:+.1f}", sf, X0 - 0.12, X0 + 0.06, 0, 3.0, z - 0.07, z + 0.07, GREEN)
    s.slab("Sill", sf, X0, X0 + 0.32, 0.5, 0.55, -5.55, 5.55, (0.86, 0.82, 0.74))
    # Glass: thin and faint so the street shows through.
    for i, (za, zb) in enumerate(((-5.53, -2.97), (-2.83, -0.27), (-0.13, 2.53), (2.67, 5.53))):
        see_through(s.slab(f"Pane {i + 1}", sf, X0 - 0.05, X0 - 0.04, 0.55, 2.5, za, zb, (0.8, 0.9, 0.95), rough=0.05), 0.08)
    letters = s.box("Window gold leaf", sf, (X0 - 0.02, 1.85, -1.6), (0.004, 0.62, 2.5), (1, 1, 1), rot=(0, 0, 0), shadows=False)
    textured(letters, "WindowLetters", cutoff=0.5)
    for comp in letters.components:
        if comp.get("Type") == "Mesh":
            comp["Material"]["Metallic"] = 0.6
            comp["Material"]["Roughness"] = 0.35
    # The front door.
    s.slab("Door rail", sf, X0 - 0.1, X0 + 0.02, 0.0, 0.12, -7.43, -5.67, BRASS, metallic=0.9, rough=0.3)
    rod(s, sf, "Door push bar", (X0 + 0.06, 1.05, -6.9), (X0 + 0.06, 1.05, -6.2), 0.03, BRASS, metallic=0.9, rough=0.3)

    # Outside: the pavement in the sun and the street across the road.
    out = s.group("Street", g)
    s.slab("Pavement", out, -16, X0 - 0.12, -0.25, -0.05, Z0 - 4, Z1 + 4, (0.62, 0.6, 0.56))
    s.slab("Kerb", out, -16.2, -16, -0.25, 0.05, Z0 - 4, Z1 + 4, (0.5, 0.5, 0.48))
    view = s.box("Across the road", out, (-17.5, 2.6, -0.5), (0.05, 6.4, 22), (1, 1, 1), shadows=False)
    textured(view, "Street", emissive=1.15)
    for i, z in enumerate((-4.6, 3.4)):
        s.box(f"Bike rack {i + 1}", out, (-7.8, 0.4, z), (0.06, 0.8, 0.9), (0.2, 0.22, 0.24), metallic=0.7)
    model(s, out, "Planter by the door", "PlantBig.fbx", (-7.0, -0.05, -6.6), 0, 0.7)
    return g


# ---- the bar -------------------------------------------------------------------------------------

def bar(s, root):
    g = s.group("The bar", root)
    zf, zb = 4.3, 5.0
    front = s.slab("Bar front", g, -3.7, 3.3, 0, 1.0, zf, zb, (1, 1, 1))
    textured(front, "Floor", (3.5, 0.5), tint=(0.62, 0.5, 0.42))
    s.slab("Kick plate", g, -3.7, 3.3, 0, 0.12, zf - 0.02, zf + 0.01, BLACK, metallic=0.5)
    s.slab("Bar top", g, -3.78, 3.38, 1.0, 1.06, zf - 0.08, zb + 0.06, BUTCHER, rough=0.5)
    s.slab("Back counter", g, -4.2, 3.6, 0, 0.92, Z1 - 0.62, Z1, WALNUT)
    s.slab("Back counter top", g, -4.2, 3.6, 0.92, 0.96, Z1 - 0.65, Z1, (0.32, 0.33, 0.34), metallic=0.4, rough=0.4)

    # The espresso machine and its steam wand (right of the kit as the crowd sees it).
    model(s, g, "Espresso machine", "EspressoMachine.fbx", (1.55, 1.06, 4.62), 180, 0.82)
    rod(s, g, "Steam wand", (1.02, 1.62, 4.5), (0.92, 1.24, 4.22), 0.025, CHROME, metallic=1.0, rough=0.2)
    rod(s, g, "Hot water spout", (2.1, 1.6, 4.5), (2.12, 1.32, 4.3), 0.025, CHROME, metallic=1.0, rough=0.2)
    for i, x in enumerate((1.25, 1.85)):
        s.box(f"Cups warming {i + 1}", g, (x, 1.78, 4.72), (0.32, 0.08, 0.2), (0.95, 0.94, 0.9), rough=0.3)
    # Grinder.
    s.box("Grinder body", g, (0.55, 1.28, 4.7), (0.2, 0.44, 0.26), BLACK, metallic=0.4, rough=0.35)
    s.box("Grinder hopper", g, (0.55, 1.62, 4.7), (0.2, 0.26, 0.2), (0.35, 0.22, 0.12), rough=0.15, shape="Cylinder")
    # Pastry case.
    see_through(s.slab("Pastry case glass", g, -1.3, -0.25, 1.06, 1.46, 4.3, 4.85, (0.85, 0.92, 0.95), rough=0.05), 0.18)
    s.slab("Pastry shelf", g, -1.28, -0.27, 1.22, 1.24, 4.32, 4.83, (0.9, 0.9, 0.9))
    for i in range(8):
        x = -1.18 + (i % 4) * 0.25
        y = 1.1 if i < 4 else 1.27
        col = [(0.84, 0.6, 0.3), (0.72, 0.42, 0.2), (0.92, 0.78, 0.52), (0.55, 0.3, 0.2)][i % 4]
        s.box(f"Pastry {i + 1}", g, (x, y, 4.55), (0.14, 0.07, 0.1), col, rough=0.8, shape="Sphere")
    s.light("Pastry case lamp", g, (-0.78, 1.42, 4.58), "Point", (1.0, 0.85, 0.6), 1.2, 1.2)
    # The till, tip jar, card reader.
    s.box("Till base", g, (-2.35, 1.12, 4.62), (0.4, 0.12, 0.34), BLACK)
    s.box("Till screen", g, (-2.35, 1.32, 4.55), (0.36, 0.24, 0.03), (0.08, 0.1, 0.12), rot=(-15, 0, 0),
          emissive=(0.5, 0.75, 0.9), emissive_intensity=0.6)
    see_through(s.box("Tip jar", g, (-1.9, 1.16, 4.45), (0.14, 0.2, 0.14), (0.85, 0.95, 0.9), shape="Cylinder", rough=0.05), 0.35)
    s.box("Tips", g, (-1.9, 1.1, 4.45), (0.1, 0.06, 0.1), (0.45, 0.62, 0.4), shape="Cylinder")
    model(s, g, "Kettle", "Kettle.fbx", (-0.1, 1.06, 4.75), 200, 1.0)
    # A stack of cups on the bar.
    for i in range(3):
        model(s, g, f"Stacked cup {i + 1}", "CafeCup.fbx", (2.75, 1.06 + i * 0.1, 4.7), 30 * i, 0.75)

    # Back counter: grinder number two, milk fridge, bottles of syrup, a record player.
    s.box("Fridge door", g, (2.4, 0.46, Z1 - 0.63), (1.0, 0.8, 0.02), (0.75, 0.76, 0.78), metallic=0.8, rough=0.3)
    for i, c in enumerate([(0.6, 0.2, 0.15), (0.75, 0.5, 0.15), (0.35, 0.18, 0.1), (0.5, 0.6, 0.3), (0.65, 0.3, 0.4)]):
        s.box(f"Syrup {i + 1}", g, (-3.9 + i * 0.12, 1.1, Z1 - 0.3), (0.07, 0.28, 0.07), c, rough=0.15, shape="Cylinder")
    s.box("Record player", g, (-1.8, 1.0, Z1 - 0.3), (0.45, 0.1, 0.35), (0.3, 0.2, 0.12))
    s.box("Record", g, (-1.85, 1.06, Z1 - 0.3), (0.3, 0.01, 0.3), BLACK, shape="Cylinder", rough=0.3)
    model(s, g, "Back-bar plant", "PlantSnake.fbx", (3.3, 0.96, Z1 - 0.3), 0, 0.6)

    # Shelves of coffee bags and cups to the right of the chalkboard.
    for j, y in enumerate((2.2, 2.75)):
        s.slab(f"Shelf {j + 1}", g, 1.0, 3.4, y - 0.03, y, Z1 - 0.28, Z1, OAK)
        for k, x in enumerate((1.15, 3.25)):
            s.box(f"Shelf bracket {j}{k}", g, (x, y - 0.1, Z1 - 0.12), (0.03, 0.16, 0.2), BLACK, metallic=0.6)
        bags = s.box(f"Coffee bags {j + 1}", g, (1.85, y + 0.17, Z1 - 0.14), (1.1, 0.34, 0.12), (1, 1, 1), shadows=False)
        textured(bags, "CoffeeBags", cutoff=0.5)
        for k in range(4):
            model(s, g, f"Shelf cup {j}{k}", "CafeCup.fbx", (2.6 + k * 0.17, y, Z1 - 0.15), 90 + 20 * k, 0.8)
    model(s, g, "Shelf trailing plant", "PlantSmall.fbx", (3.2, 2.75, Z1 - 0.15), 0, 1.4)
    books(s, g, "Shelf books", (1.45, 2.2, Z1 - 0.14), 7)

    # The chalkboard over the bar.
    s.slab("Chalkboard frame", g, -2.65, 0.65, 2.0, 3.6, Z1 - 0.08, Z1 - 0.02, (0.42, 0.28, 0.16))
    board = s.box("Chalkboard", g, (-1.0, 2.8, Z1 - 0.09), (3.08, 1.54, 0.02), (1, 1, 1), shadows=False)
    textured(board, "Chalkboard", emissive=0.4)
    s.light("Chalkboard picture light", g, (-1.0, 3.7, Z1 - 0.7), "Spot", (1.0, 0.85, 0.65), 70.0, 4.5,
            rot=look_rotation((-1.0, 3.7, Z1 - 0.7), (-1.0, 2.6, Z1)), inner=40, outer=70)

    # The kitchen door, back right.
    s.slab("Kitchen door", g, 4.1, 5.1, 0, 2.15, Z1 - 0.04, Z1, (0.3, 0.42, 0.36))
    s.box("Kitchen porthole", g, (4.6, 1.55, Z1 - 0.05), (0.34, 0.34, 0.02), (0.9, 0.82, 0.6), shape="Cylinder",
          rot=(90, 0, 0), emissive=(1.0, 0.85, 0.6), emissive_intensity=0.8)
    return g


# ---- furniture -----------------------------------------------------------------------------------

def books(s, parent, name, pos, n):
    """A row of spines standing on a shelf."""
    g = s.group(name, parent, pos)
    cols = [(0.62, 0.2, 0.16), (0.16, 0.3, 0.42), (0.86, 0.78, 0.6), (0.2, 0.38, 0.28), (0.78, 0.55, 0.2), (0.3, 0.2, 0.3)]
    x = 0.0
    for i in range(n):
        w, h = 0.03 + 0.012 * (i % 3), 0.2 + 0.03 * ((i * 7) % 4)
        s.box(f"Book {i + 1}", g, (x, h / 2, 0), (w, h, 0.14), cols[i % len(cols)], rough=0.85)
        x += w + 0.004
    return g


def two_top(s, parent, name, pos, yaw=0.0):
    """A small round café table: the pack's round table cut down to 0.72 m across."""
    return model(s, parent, name, "TwoTop.fbx", pos, yaw, (0.62, 1.0, 0.62))


def chair(s, parent, name, pos, yaw, arm=False):
    """A café chair whose seat faces the way a regular at yaw would."""
    return model(s, parent, name, "CafeChairArm.fbx" if arm else "CafeChair.fbx", pos, yaw + CHAIR_YAW, 1.0)


CHAIR_YAW = 180.0  # the pack's chair faces -z; a regular faces +z


def furniture(s, root):
    g = s.group("Tables and regulars", root)
    # The two-top that made room for the kit, pushed against the bar end with its chairs stacked on.
    two_top(s, g, "The two-top that moved", (4.4, 0, 3.4))
    for i, y in enumerate((0.75, 1.15)):
        e = s.entity(f"Stacked chair {i + 1}", g, (4.4, y + 0.86, 3.4 + 0.05 * i), (180, 20 * i, 0))
        e.add({"Type": "Model", "ModelPath": MOD + "CafeChair.fbx"})

    # Front left: two regulars sipping.
    t = (-1.75, 0, -1.6)
    two_top(s, g, "Front left two-top", t)
    for i, (dx, who, skin, clip, speed) in enumerate(((-0.42, "Mother_02", "02_B", "SeatSip", 0.93), (0.42, "Son_01", "03_A", "SeatListen", 1.06))):
        p = (t[0] + dx, 0, t[2] - 0.35)
        yaw = facing(p, KIT_CENTRE)
        chair(s, g, f"Front left chair {i + 1}", p, yaw)
        people.person(s, g, f"Front left regular {i + 1}", who, skin, p, yaw, clip, speed, held="cup" if clip == "SeatSip" else None)
    model(s, g, "Front left cups", "CafeCup.fbx", (t[0] - 0.12, 0.75, t[2] + 0.1), 40, 0.7)

    # Front right: someone with a book.
    t = (2.1, 0, -2.5)
    two_top(s, g, "Front right two-top", t)
    p = (t[0] + 0.1, 0, t[2] - 0.45)
    chair(s, g, "Front right chair", p, facing(p, KIT_CENTRE))
    people.person(s, g, "Reading, mostly", "SchoolGirl_01", "02_A", p, facing(p, KIT_CENTRE), "SeatListen", 0.88)
    chair(s, g, "Front right empty chair", (t[0] + 0.4, 0, t[2] + 0.42), -150)
    s.box("Paperback", g, (t[0] + 0.1, 0.765, t[2] + 0.1), (0.13, 0.03, 0.2), (0.7, 0.25, 0.2), rot=(0, 30, 0))
    model(s, g, "Front right cup", "CafeCup.fbx", (t[0] - 0.18, 0.75, t[2] - 0.05), 0, 0.7)

    # Back by the door: a table of two who came for the music.
    t = (-0.2, 0, -4.2)
    two_top(s, g, "Door two-top", t)
    for i, (dx, who, skin) in enumerate(((-0.42, "Mother_01", "04_A"), (0.42, "Daughter_01", "03_B"))):
        p = (t[0] + dx, 0, t[2] - 0.3)
        yaw = facing(p, KIT_CENTRE)
        chair(s, g, f"Door chair {i + 1}", p, yaw)
        people.person(s, g, f"Door regular {i + 1}", who, skin, p, yaw, "SeatSway" if i else "SeatListen", 0.97 + 0.08 * i)

    # The window bar: a ledge and stools along the front glass.
    s.slab("Window ledge", g, X0, X0 + 0.42, 1.02, 1.07, -5.4, -0.4, OAK)
    for i, z in enumerate((-4.8, -3.9, -3.0, -1.9, -1.0)):
        model(s, g, f"Window stool {i + 1}", STOOL, (X0 + 0.75, 0, z), 0, 1.0)
    for i, (z, who, skin, clip) in enumerate(((-3.9, "Son_01", "01_B", "SeatListen"), (-1.9, "Mother_02", "04_B", "SeatSip"))):
        p = (X0 + 0.75, 0.16, z)
        people.person(s, g, f"Window regular {i + 1}", who, skin, p, facing(p, KIT_CENTRE), clip, 0.9 + 0.1 * i,
                      held="cup" if clip == "SeatSip" else None)
    for i, z in enumerate((-4.8, -1.0)):
        model(s, g, f"Window cup {i + 1}", "CafeCup.fbx", (X0 + 0.22, 1.07, z), 20 * i, 0.7)
    model(s, g, "Window laptop bag", "Bag.fbx", (X0 + 0.55, 0, -3.3), 60, 1.6)

    # The banquette along the brick.
    s.slab("Banquette", g, X1 - 0.6, X1, 0, 0.45, -6.4, -0.4, WALNUT)
    s.slab("Banquette cushion", g, X1 - 0.58, X1 - 0.02, 0.45, 0.55, -6.35, -0.45, (0.56, 0.2, 0.14), rough=0.95)
    s.slab("Banquette back", g, X1 - 0.16, X1 - 0.02, 0.55, 1.05, -6.35, -0.45, (0.56, 0.2, 0.14), rough=0.95)
    for i, z in enumerate((-5.4, -3.4, -1.4)):
        two_top(s, g, f"Banquette table {i + 1}", (X1 - 1.05, 0, z))
    for i, (z, who, skin, clip) in enumerate(((-5.2, "ShopKeeper_01", "02_C", "SeatListen"), (-3.3, "Daughter_01", "01_C", "SeatSip"),
                                             (-1.5, "Son_01", "04_C", "SeatListen"))):
        p = (X1 - 0.48, 0.02, z)
        people.person(s, g, f"Banquette regular {i + 1}", who, skin, p, facing(p, KIT_CENTRE), clip, 0.95 + 0.07 * i,
                      held="cup" if clip == "SeatSip" else None)
    for i, z in enumerate((-5.5, -3.2, -1.3)):
        model(s, g, f"Banquette cup {i + 1}", "CafeCup.fbx", (X1 - 1.0, 0.75, z), 50 * i, 0.7)

    # Plants: the big ones in the corners, troughs on the sill, pots along the bar.
    model(s, g, "Corner fig", "PlantBig.fbx", (X1 - 0.7, 0, Z0 + 0.7), 30, 0.85)
    model(s, g, "Window palm", "PlantTall.fbx", (X0 + 0.5, 0, 4.8), 0, 1.2)
    model(s, g, "Kitchen door plant", "PlantTall.fbx", (X1 - 0.5, 0, 5.6), 70, 1.1)
    model(s, g, "Snake plant by the brick", "PlantSnake.fbx", (X1 - 0.35, 0, 1.4), 0, 1.1)
    for i, z in enumerate((-5.0, -2.1, 0.9, 3.8)):
        model(s, g, f"Sill trough {i + 1}", "PlantTrough.fbx", (X0 + 0.16, 0.55, z), 90, 1.1)
    for i, x in enumerate((-3.4, 3.05)):
        model(s, g, f"Bar pot {i + 1}", "PlantPot.fbx", (x, 1.06, 4.6), 30 * i, 0.9)
    # Hanging plants on the beams.
    for i, (x, z) in enumerate(((-4.9, -3.6), (-4.9, 1.2), (5.0, -1.2), (5.0, 3.6), (-2.6, -6.0))):
        rod(s, g, f"Hanger {i + 1}", (x, H - 0.22, z), (x, 2.75, z), 0.012, (0.6, 0.55, 0.45), shadows=False)
        s.box(f"Hanging pot {i + 1}", g, (x, 2.66, z), (0.26, 0.2, 0.26), (0.78, 0.5, 0.34), shape="Cylinder")
        model(s, g, f"Hanging plant {i + 1}", "PlantSmall.fbx", (x, 2.72, z), 40 * i, 1.6)

    # Framed prints on the brick.
    for i, (z, name) in enumerate(((-4.4, "PrintA"), (-2.4, "PrintB"), (0.2, "PrintC"))):
        s.box(f"Print frame {i + 1}", g, (X1 - 0.03, 1.9, z), (0.04, 0.78, 0.64), BLACK)
        e = s.box(f"Print {i + 1}", g, (X1 - 0.055, 1.9, z), (0.01, 0.7, 0.56), (1, 1, 1), shadows=False)
        textured(e, name)
    # The A-board by the door, and the coat rack.
    textured(s.box("A-board", g, (-4.6, 0.46, -6.9), (0.62, 0.92, 0.05), (1, 1, 1), rot=(-8, 30, 0)), "SandwichBoard")
    rod(s, g, "Coat rack", (-2.6, 0, -7.25), (-2.6, 1.8, -7.25), 0.05, WALNUT)
    s.box("Coat", g, (-2.6, 1.35, -7.15), (0.4, 0.8, 0.18), (0.55, 0.35, 0.2), rough=0.95)
    return g


# ---- the kit's corner ----------------------------------------------------------------------------

def kit_corner(s, root):
    g = s.group("The kit where a two-top was", root)
    model(s, g, "Rug", RUG, (0, 0.004, 1.85), 90, 0.82)
    # A little side table with the house brushes in their espresso tin and a tea towel.
    s.box("Side stool", g, (1.62, 0.3, 2.45), (0.34, 0.6, 0.34), WALNUT, shape="Cylinder")
    s.box("Espresso tin", g, (1.6, 0.68, 2.42), (0.12, 0.16, 0.12), (0.62, 0.16, 0.12), metallic=0.6, rough=0.4, shape="Cylinder")
    s.box("Tin label", g, (1.6, 0.68, 2.42), (0.125, 0.07, 0.125), (0.92, 0.86, 0.66), shape="Cylinder")
    for i, (dx, dz, lean) in enumerate(((-0.02, 0.0, 8), (0.025, 0.01, -6), (0.0, -0.025, 4))):
        rod(s, g, f"Brush {i + 1}", (1.6 + dx, 0.7, 2.42 + dz), (1.6 + dx + lean * 0.004, 0.98, 2.42 + dz), 0.016, BLACK)
        s.box(f"Brush fan {i + 1}", g, (1.6 + dx + lean * 0.005, 1.03, 2.42 + dz), (0.06, 0.1, 0.01), (0.7, 0.7, 0.72),
              metallic=0.9, rot=(0, 30 * i, lean))
    s.box("Tea towel", g, (1.68, 0.61, 2.5), (0.3, 0.012, 0.26), (0.9, 0.86, 0.8), rot=(0, 20, 0))
    s.box("Tea towel stripe", g, (1.68, 0.617, 2.5), (0.3, 0.004, 0.04), (0.2, 0.35, 0.6), rot=(0, 20, 0))
    model(s, g, "Drummer's cup", "CafeCup.fbx", (1.52, 0.6, 2.56), 200, 0.7)
    # The setlist taped down, flattened by a foil-wrapped breakfast sandwich.
    sheet = s.box("Setlist", g, (-0.95, 0.006, 0.55), (0.21, 0.004, 0.3), (1, 1, 1), rot=(0, -12, 0), shadows=False)
    textured(sheet, "Setlist")
    s.box("Breakfast sandwich in foil", g, (-0.93, 0.045, 0.62), (0.13, 0.07, 0.1), (0.85, 0.86, 0.88), metallic=0.85,
          rough=0.35, rot=(4, 25, -3))
    s.box("Gaffer tape", g, (-0.95, 0.006, 0.39), (0.12, 0.004, 0.03), (0.15, 0.15, 0.16), rot=(0, -12, 0))
    # Jules's stool stays by the floor tom when the guitar goes back to the bar.
    model(s, g, "Jules's stool", STOOL, JULES_STOOL, 0, 1.0)
    model(s, g, "Amp cable", CABLE, (-1.4, 0.0, 1.0), 30, 0.8)
    return g


JULES_STOOL = (-1.85, 0, 1.75)


# ---- the story -----------------------------------------------------------------------------------

def guitar(s, parent, name, pos, rot):
    e = s.entity(name, parent, pos, rot)
    e.add({"Type": "Model", "ModelPath": GUITAR})
    return e


def story(s, root):
    g = s.group("Story", root)

    # 1. guitar_at_counter --------------------------------------------------------------------
    opener = s.story("Jules sits in for the opener", g, "guitar_at_counter", False, 0.9, JULES_STOOL)
    jy = facing(JULES_STOOL, (0.6, 0, -1.5))
    j = people.person(s, opener, "Jules on the stool", "ShopKeeper_01", "01_A", (0, 0.16, 0), jy, "Strum", 1.0)
    apron(s, j, seated=True)
    lap = s.entity("Lap", j, (0.04, 0.84, 0.22), (0, 0, 0))
    guitar(s, lap, "Jules's guitar", (0.0, 0, 0), (0, 180, 160))
    stand_at = (-3.25, 0, 3.92)
    stand = s.story("The guitar on its stand by the till", g, "guitar_at_counter", True, 0.9, stand_at)
    for i, (dx, dz) in enumerate(((-0.16, -0.12), (0.16, -0.12), (0.0, 0.16))):
        rod(s, stand, f"Stand leg {i + 1}", (dx, 0.0, dz), (0, 0.32, 0), 0.02, BLACK, metallic=0.5)
    rod(s, stand, "Stand neck", (0, 0.32, 0.0), (0, 0.95, 0.12), 0.02, BLACK, metallic=0.5)
    tilt = s.entity("Leaning back", stand, (0, 0.06, -0.04), (-12, -25, 0))
    guitar(s, tilt, "The barista's guitar", (0, 0.36, 0), (0, 0, -90))

    behind = s.story("Jules back behind the bar", g, "guitar_at_counter", True, 0.9, (1.15, 0, 5.45))
    steaming = s.story("Pulling shots", behind, "wand_off", False, 0.5, (0, 0, 0))
    j = people.person(s, steaming, "Jules at the steam wand", "ShopKeeper_01", "01_A", (0, 0, 0), 180, "Steam", 1.0, held="jug")
    apron(s, j)
    clapping = s.story("Clapping over the bar", behind, "wand_off", True, 0.5, (0, 0, 0))
    j = people.person(s, clapping, "Jules clapping", "ShopKeeper_01", "01_A", (-0.1, 0, -0.1), 180, "Clap", 1.0)
    apron(s, j)

    # 2. laptop_lowered -----------------------------------------------------------------------
    t = (-3.0, 0, 0.75)
    two_top(s, g, "The laptop two-top", t)
    seats = [(t[0] - 0.55, 0, t[2] - 0.3), (t[0] - 0.55, 0, t[2] + 0.32)]
    for i, p in enumerate(seats):
        chair(s, g, f"Laptop chair {i + 1}", p, facing(p, KIT_CENTRE))
    lap_at = (t[0] - 0.08, 0.75, t[2])
    up = s.story("Laptop open", g, "laptop_lowered", False, 0.6, lap_at)
    laptop(s, up, 105)
    half = s.story("Laptop at half mast", g, "laptop_lowered", True, 0.6, lap_at)
    laptop(s, half, 38)
    couple = (("Son_01", "02_A"), ("Daughter_01", "01_A"))
    heads_down = s.story("The couple, heads in the screen", g, "laptop_lowered", False, 0.6, t)
    heads_up = s.story("The couple, looking up", g, "laptop_lowered", True, 0.6, t)
    for i, p in enumerate(seats):
        local = (p[0] - t[0], 0, p[2] - t[2])
        yaw = facing(p, (lap_at[0] + 0.3, 0, lap_at[2]))
        people.person(s, heads_down, f"Laptop {('one', 'two')[i]}", *couple[i], local, yaw, "SeatLaptop", 1.0 + 0.1 * i)
        people.person(s, heads_up, f"Laptop {('one', 'two')[i]}, watching", *couple[i], local, facing(p, KIT_CENTRE),
                      "SeatSway" if i else "SeatListen", 1.0)
    model(s, g, "Their cups", "CafeCup.fbx", (t[0] + 0.2, 0.75, t[2] + 0.22), 120, 0.7)

    # 3. chairs_turned / 4. spare_chair_filled ---------------------------------------------------
    t = (2.9, 0, 0.45)
    two_top(s, g, "The right-hand two-top", t)
    model(s, g, "Two flat whites", "CafeCup.fbx", (t[0] - 0.1, 0.75, t[2] + 0.1), 70, 0.7)
    talk = s.story("Facing each other", g, "chairs_turned", False, 0.8, t)
    turned = s.story("Turned to the kit", g, "chairs_turned", True, 0.8, t)
    pair = (("Mother_01", "03_C"), ("Son_01", "01_C"))
    for i, (before, after) in enumerate((((0.05, 0, -0.55), (-0.05, 0, -0.6)), ((0.05, 0, 0.55), (0.35, 0, 0.5)))):
        by = 0.0 if i == 0 else 180.0
        chair(s, talk, f"Chair {i + 1}", before, by)
        people.person(s, talk, f"Talking {i + 1}", *pair[i], before, by, "SeatListen", 0.9 + 0.15 * i)
        world = (t[0] + after[0], 0, t[2] + after[2])
        ay = facing(world, KIT_CENTRE)
        chair(s, turned, f"Chair {i + 1}, turned", after, ay)
        people.person(s, turned, f"Turned {i + 1}", *pair[i], after, ay, "SeatSway", 1.0)
    pack_on = s.story("Backpack on the third chair", g, "chairs_turned", False, 0.8, (t[0] + 0.62, 0, t[2]))
    chair(s, pack_on, "Third chair", (0, 0, 0), -90)
    model(s, pack_on, "Backpack", "Backpack.fbx", (0.02, 0.78, 0.02), 90, 1.0)
    pack_under = s.story("Backpack under the table", g, "chairs_turned", True, 0.8, (t[0], 0, t[2]))
    model(s, pack_under, "Backpack, under", "Backpack.fbx", (0.05, 0.3, 0.05), -30, 1.0)
    spare = (1.75, 0, -0.35)
    sy = facing(spare, KIT_CENTRE)
    in_pool = s.story("The spare chair in the light", g, "chairs_turned", True, 0.8, spare)
    chair(s, in_pool, "Spare chair", (0, 0, 0), sy)
    filled = s.story("Someone took the spare chair", g, "spare_chair_filled", True, 0.9, spare)
    people.person(s, filled, "The new regular", "Daughter_01", "04_B", (0, 0, 0), sy, "SeatSway", 1.0, held="cup")

    # 5. wand_off ---------------------------------------------------------------------------
    wand_tip = (0.92, 1.24, 4.22)
    steam = s.story("Steam", g, "wand_off", False, 0.4, wand_tip)
    e = s.entity("Steam off the wand", steam, (0, 0, 0))
    e.add({"Type": "ParticleSystem", "Looping": True, "EmissionRate": 34.0, "MaxParticles": 160, "SimulationSpace": "Local",
           "Shape": "Cone", "ConeAngle": 18, "ShapeRadius": 0.03, "Lifetime": [1.4, 2.4], "Speed": [0.35, 0.6],
           "Size": [0.07, 0.14], "EndSize": 4.0, "StartColor": [1.0, 0.98, 0.95], "StartColor2": [0.92, 0.92, 0.95],
           "EndColor": [1.0, 1.0, 1.0], "StartAlpha": 0.55, "EndAlpha": 0.0, "FadeIn": 0.08, "Intensity": 1.0,
           "Gravity": -0.25, "Drag": 0.6, "NoiseStrength": 0.25, "NoiseFrequency": 0.9, "Blend": "Alpha", "Lit": True,
           "Simulation": "CPU", "SoftParticleDistance": 0})
    for i, (dx, dy, dz, r) in enumerate(((0.0, 0.14, 0.0, 0.22), (0.07, 0.4, 0.02, 0.36), (-0.06, 0.72, 0.08, 0.46),
                                         (0.1, 1.05, 0.04, 0.54), (-0.08, 1.38, 0.12, 0.5))):
        puff = s.box(f"Steam cloud {i + 1}", steam, (dx, dy, dz), (r, r * 0.8, r), (1, 1, 1), shape="Sphere", shadows=False,
                     emissive=(1.0, 0.97, 0.92), emissive_intensity=0.5, rough=1.0)
        see_through(puff, 0.42 - 0.05 * i)
    cup = s.story("The untouched cup on the pass", g, "wand_off", True, 0.6, (2.55, 1.06, 4.38))
    s.box("Saucer", cup, (0, 0.006, 0), (0.15, 0.012, 0.15), (0.96, 0.95, 0.92), shape="Cylinder", rough=0.3)
    model(s, cup, "Cup", "CafeCup.fbx", (0, 0.012, 0), 210, 0.75)
    s.box("Latte art", cup, (-0.008, 0.112, 0), (0.085, 0.004, 0.085), (0.86, 0.72, 0.5), shape="Cylinder", rough=0.6,
          emissive=(0.3, 0.22, 0.15), emissive_intensity=0.2)
    s.light("A lamp on the pass", cup, (0, 0.7, -0.1), "Point", (1.0, 0.8, 0.55), 1.4, 1.6)
    return g


def apron(s, person, seated=False):
    """A green bib apron over Jules's front (the person faces +z)."""
    torso = next(e for e in s.entities if e.parent is person and e.name == "Torso")
    s.box("Apron bib", torso, (0, 0.24, 0.135), (0.3, 0.36, 0.02), (0.12, 0.3, 0.22), rough=0.95)
    s.box("Apron strap", torso, (0, 0.47, 0.12), (0.16, 0.04, 0.02), (0.12, 0.3, 0.22))
    legs = next(e for e in s.entities if e.parent is person and e.name == "Legs")
    if seated:
        s.box("Apron skirt", legs, (0, 0.56, 0.3), (0.38, 0.02, 0.42), (0.12, 0.3, 0.22), rough=0.95)
    else:
        s.box("Apron skirt", legs, (0, 0.6, 0.16), (0.38, 0.5, 0.02), (0.12, 0.3, 0.22), rough=0.95)


def laptop(s, parent, lid_deg):
    """A laptop at the parent's pivot, base on the table, the screen facing -x (at the couple) and the
    stickered lid toward the kit. lid_deg: 0 shut, 90 upright, 105 open wide."""
    s.box("Base", parent, (0, 0.01, 0), (0.25, 0.02, 0.36), (0.72, 0.74, 0.77), metallic=0.7, rough=0.35)
    s.box("Keys", parent, (-0.02, 0.021, 0), (0.12, 0.002, 0.3), (0.1, 0.1, 0.11))
    hinge = s.entity("Hinge", parent, (0.12, 0.02, 0), (0, 0, -lid_deg))
    s.box("Lid", hinge, (-0.125, 0.006, 0), (0.25, 0.012, 0.36), (0.72, 0.74, 0.77), metallic=0.7, rough=0.35)
    back = s.box("Stickers", hinge, (-0.125, 0.0125, 0), (0.24, 0.002, 0.34), (1, 1, 1), shadows=False)
    textured(back, "LaptopLid")
    s.box("Screen", hinge, (-0.125, -0.0005, 0), (0.22, 0.002, 0.32), (0.1, 0.12, 0.16), emissive=(0.55, 0.7, 0.95),
          emissive_intensity=1.4, shadows=False)
    s.light("Screen glow", hinge, (-0.125, -0.15, 0), "Point", (0.55, 0.7, 1.0), 0.5, 0.9)


# ---- light ---------------------------------------------------------------------------------------

def lights(s, root):
    g = s.group("Light", root)
    # The morning sun through the front windows: the one shadowed light.
    sun = s.light("Sun through the front windows", g, (-9, 8, -3), "Directional", SUN, 14.0,
                  rot=look_rotation((0, 0, 0), (0.78, -0.5, 0.36)), shadows=True, show="Static")
    sun.components[-2]["VolumetricMultiplier"] = 0.6
    # Daylight spilling in off the street (no shadows, wide and soft).
    for i, z in enumerate((-4.2, -1.5, 1.2, 4.0)):
        s.light(f"Window daylight {i + 1}", g, (X0 - 1.5, 2.2, z), "Spot", (0.85, 0.9, 1.0), 140.0, 10.0,
                rot=look_rotation((X0 - 1.5, 2.2, z), (X0 + 4.0, 0.6, z + 0.5)), inner=35, outer=75, show="Static")
    # Edison bulbs on cords from the beams: the glass is emissive, every other one a real light.
    bulbs = s.group("Edison bulbs", g)
    n = 0
    for zi, z in enumerate((-4.8, -2.4, 0.0, 3.0)):
        for xi, x in enumerate((-3.9, -1.6, 1.6, 3.9)):
            drop = 0.7 + 0.25 * ((xi + zi) % 3)
            y = H - 0.22 - drop
            rod(s, bulbs, f"Cord {zi}{xi}", (x, H - 0.22, z), (x, y + 0.1, z), 0.01, BLACK, shadows=False)
            s.box(f"Socket {zi}{xi}", bulbs, (x, y + 0.08, z), (0.05, 0.07, 0.05), BRASS, metallic=0.9, shape="Cylinder", shadows=False)
            s.box(f"Bulb {zi}{xi}", bulbs, (x, y - 0.02, z), (0.09, 0.14, 0.09), AMBER, shape="Sphere", shadows=False,
                  emissive=AMBER, emissive_intensity=5.0, rough=0.2)
            if (xi + zi) % 2 == 0:
                n += 1
                s.light(f"Bulb light {zi}{xi}", bulbs, (x, y - 0.1, z), "Point", AMBER, 34.0, 5.5, show="Static")
    # Three hung low over the kit.
    for i, (x, z) in enumerate(((-0.7, 1.4), (0.0, 2.1), (0.7, 1.4))):
        y = 2.55 + 0.1 * i
        rod(s, bulbs, f"Kit cord {i + 1}", (x, H - 0.22, z), (x, y + 0.1, z), 0.01, BLACK, shadows=False)
        s.box(f"Kit bulb {i + 1}", bulbs, (x, y - 0.02, z), (0.1, 0.16, 0.1), AMBER, shape="Sphere", shadows=False,
              emissive=AMBER, emissive_intensity=6.0, rough=0.2)
    s.light("Kit bulbs", bulbs, (0, 2.4, 1.7), "Point", AMBER, 40.0, 5.0, show="Static")

    # Pendants over the bar and grazers down the brick.
    for i, x in enumerate((-2.6, -0.6, 1.4)):
        rod(s, bulbs, f"Pendant cord {i + 1}", (x, H, 4.6), (x, 2.55, 4.6), 0.01, BLACK, shadows=False)
        s.box(f"Pendant shade {i + 1}", bulbs, (x, 2.45, 4.6), (0.34, 0.22, 0.34), (0.1, 0.24, 0.2), metallic=0.4,
              shape="Cylinder", shadows=False)
        s.box(f"Pendant glow {i + 1}", bulbs, (x, 2.33, 4.6), (0.2, 0.04, 0.2), AMBER, shape="Cylinder", shadows=False,
              emissive=AMBER, emissive_intensity=4.0)
        s.light(f"Pendant {i + 1}", bulbs, (x, 2.3, 4.6), "Spot", (1.0, 0.8, 0.55), 60.0, 4.0,
                rot=(90, 0, 0), inner=30, outer=60, show="Static")
    for i, z in enumerate((-5.0, -2.2, 0.6, 3.4)):
        at = (X1 - 0.6, H - 0.15, z)
        s.light(f"Brick grazer {i + 1}", bulbs, at, "Spot", (1.0, 0.75, 0.5), 45.0, 5.0,
                rot=look_rotation(at, (X1, 0.8, z)), inner=30, outer=65, show="Static")

    # The gig's own light: two clamp lamps on the beam and a follow on the drummer, all warm.
    rig = s.group("Clamp lamps", g)
    for i, x in enumerate((-1.6, 1.6)):
        at = (x, H - 0.3, -1.2)
        s.box(f"Clamp lamp {i + 1}", rig, at, (0.16, 0.16, 0.2), BLACK, rot=look_rotation(at, KIT_CENTRE), metallic=0.6)
        s.light(f"Clamp wash {i + 1}", rig, at, "Spot", (1.0, 0.7, 0.45), 160.0, 9.0, rot=look_rotation(at, KIT_CENTRE),
                inner=22, outer=44, show="Wash", group=i)
    s.light("Follow on the drummer", rig, (0.0, H - 0.25, -3.6), "Spot", (1.0, 0.84, 0.68), 220.0, 11.0,
            rot=look_rotation((0.0, H - 0.25, -3.6), (0, 1.1, 2.6)), inner=10, outer=20, show="Spot")
    for i, (x, z) in enumerate(((-3.6, -1.2), (3.6, -1.2))):
        at = (x, H - 0.3, z)
        to = (x * 0.8, 0.6, 0.6)
        s.light(f"Side wash {i + 1}", rig, at, "Spot", (1.0, 0.78, 0.55), 50.0, 7.0, rot=look_rotation(at, to),
                inner=30, outer=60, show="Wash", group=2)
    # The warm pool by the kit where the spare chair goes (plain, so the show leaves it be).
    at = (2.0, H - 0.3, -0.9)
    s.light("The warm pool", rig, at, "Spot", (1.0, 0.66, 0.38), 70.0, 6.0, rot=look_rotation(at, (1.7, 0, -0.2)),
            inner=18, outer=36)
    # Dust in the sun.
    e = s.entity("Dust in the sun", g, (-3.5, 1.6, -1.0))
    e.add({"Type": "ParticleSystem", "Looping": True, "EmissionRate": 30.0, "MaxParticles": 220, "SimulationSpace": "World",
           "Shape": "Box", "BoxSize": [4.0, 2.4, 9.0], "Lifetime": [6.0, 11.0], "Speed": [0.0, 0.03],
           "Size": [0.006, 0.014], "StartColor": [1.0, 0.95, 0.85], "StartColor2": [0.95, 0.9, 0.8], "StartAlpha": 0.55,
           "EndAlpha": 0.0, "FadeIn": 0.25, "Intensity": 1.0, "Gravity": -0.0015, "Drag": 0.5, "NoiseStrength": 0.04,
           "NoiseFrequency": 0.6, "Blend": "Alpha", "Lit": True, "Simulation": "CPU", "SoftParticleDistance": 0})
    return g


# ---- markers -------------------------------------------------------------------------------------

def markers(s, root):
    m = s.group("Venue markers", root)
    s.info(m, "The Millennial Coffee Shop", "Drumsmith", room_back=Z0, room_ceiling=H, half_width=6.0, desk_z=-7.0,
           ambient=(0.2, 0.16, 0.12), fog_color=(0.09, 0.075, 0.06), haze=0.45)
    s.spot(m, "Drummer", DRUMMER)
    # Standing room: three sides of the kit.
    s.crowd("By the door", m, (-4.3, 0, -6.6), 2.2, 1.2, 6, figures="Posed")
    s.crowd("Waiting on oat lattes", m, (-5.0, 0, 1.9), 1.2, 1.4, 3, figures="Posed", yaw=70)
    s.crowd("Leaning on the bar end", m, (4.0, 0, 1.9), 1.2, 1.4, 3, figures="Posed", yaw=-80)
    s.crowd("In the aisle", m, (1.6, 0, -6.4), 1.4, 1.2, 3, figures="Posed")

    cams = s.group("Camera positions", m)
    for tag, kind, eye, aim, lens in [
        ("door-corner", "Wide", (3.6, 2.35, -5.4), (-0.9, 1.05, 2.8), 60),
        ("over-the-window-bar", "Crane", (-4.9, 1.75, -6.2), (0.6, 1.1, 2.8), 56),
        ("from-the-door", "Desk", (-1.2, 1.55, -7.1), (0.0, 1.15, 2.7), 32),
        ("laptop-two-top", "Custom", (-1.35, 1.35, -0.25), (-3.35, 0.95, 0.85), 48),
        ("the-bar", "Custom", (2.9, 2.15, 1.5), (1.2, 1.45, 4.9), 50),
        ("spare-chair", "Custom", (3.9, 1.45, -1.9), (1.4, 0.85, 0.5), 50),
        ("over-the-hats", "Custom", (0.6, 1.75, 3.9), (-0.2, 0.9, -3.0), 66),
        ("brushes", "Close", (1.05, 1.45, 0.55), (0.0, 0.85, 2.1), 44)]:
        s.camera_spot(tag, cams, eye, aim, kind, lens, tag)
    walk = [((-5.3, 1.62, -6.4), (-3.0, 1.4, -3.0), 66), ((-4.6, 1.62, -5.6), (-1.0, 1.3, 0.0), 64),
            ((-3.6, 1.6, -4.8), (-0.5, 1.25, 1.2), 62), ((-2.6, 1.58, -3.6), (0.0, 1.2, 2.0), 60),
            ((-1.6, 1.56, -2.8), (0.0, 1.15, 2.6), 58), ((-0.9, 1.55, -2.1), (0.0, 1.1, 2.7), 56)]
    for i, (eye, aim, lens) in enumerate(walk):
        s.camera_spot(f"Arrival {i + 1:02}", cams, eye, aim, "Custom", lens, f"arrival/{i + 1:02}")
    return m


# ---- assets --------------------------------------------------------------------------------------

def copy_synty(folder):
    models = os.path.join(folder, "Models")
    os.makedirs(models, exist_ok=True)
    for src, dst in list(SYNTY_PROPS.items()) + list(SYNTY_TEXTURES.items()):
        a = os.path.join(SYNTY, src)
        b = os.path.join(models, dst)
        if not os.path.exists(b) or os.path.getsize(a) != os.path.getsize(b):
            shutil.copyfile(a, b)


def build():
    s = Scene(seed="story-coffee-shop-v1")
    root = s.group("Second Pour")
    shell(s, root)
    bar(s, root)
    furniture(s, root)
    kit_corner(s, root)
    story(s, root)
    lights(s, root)
    markers(s, root)
    return s


def main():
    folder = os.path.join(repo_root(), "Assets", "Venues", ID)
    if "--textures" in sys.argv or not os.path.exists(os.path.join(folder, "Textures", "Chalkboard.png")):
        textures.make_all()
    if "--textures" in sys.argv or not os.path.exists(os.path.join(folder, "Ambience.ogg")):
        sound.make()
    copy_synty(folder)
    people.clips()
    s = build()
    s.write(os.path.join(folder, f"{ID}.lvl"))
    preview = "Preview.jpg" if os.path.exists(os.path.join(folder, "Preview.jpg")) else None
    write_venue_json(folder, "The Millennial Coffee Shop", f"{ID}.lvl", preview=preview, ambience="Ambience.ogg"
                     if os.path.exists(os.path.join(folder, "Ambience.ogg")) else None)
    print(f"{len(s.entities)} entities in {folder}")


if __name__ == "__main__":
    main()
