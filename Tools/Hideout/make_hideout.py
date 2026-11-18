#!/usr/bin/env python3
"""Writes the hideout's rooms, Assets/Hideout/{Basement,Garage,Rehearsal,Studio}.lvl, with the hideout
markers (Game/Source/Components/Hideout/HideoutMarkers.h). The basement is dressed in full
(Tools/Hideout/basement.py); the garage, rehearsal space and studio are still greyboxes of
primitives. Textures come from Tools/Hideout/make_textures.py.

    python3 Tools/Hideout/make_hideout.py

Every room has the same stations and item slots (Assets/Progression/Progression.json names the
slots), so what the player unlocked comes along when they move; the rooms differ in size, walls,
floor, light and the things that make each one that place. Deterministic: rerun = same bytes.

Room space: metres, the floor at y = 0, the doorway (where the overview camera stands) at the -z
end, the kit against the +z wall. Cameras look along local +Z.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Venues"))
from venuegen import Scene, look_rotation, repo_root  # noqa: E402
from hideoutgen import drummer, slot, station  # noqa: E402
from basement import build_basement  # noqa: E402
from garage import build_garage  # noqa: E402
from rehearsal import build_rehearsal  # noqa: E402
from studio import build_studio  # noqa: E402

BLACK = (0.04, 0.04, 0.045)
CHROME = (0.75, 0.75, 0.78)
BRASS = (0.78, 0.6, 0.25)
GOLD = (1.0, 0.78, 0.3)
WHITE = (0.9, 0.9, 0.88)
WOOD = (0.45, 0.3, 0.18)
CORK = (0.62, 0.45, 0.28)


class Room:
    def __init__(self, name, seed, width, depth, height, floor, walls, ceiling, light, light_power, shell):
        self.name = name
        self.seed = seed
        self.half = width / 2.0
        self.depth = depth
        self.height = height
        self.floor = floor
        self.walls = walls
        self.ceiling = ceiling
        self.light = light
        self.light_power = light_power
        self.shell = shell      # the drum shells' colour: the kit gets better with the room


def drum(s, parent, name, pos, diameter, depth, color, axis="y"):
    """A shell with a white head on top (axis y) or facing the room (axis z)."""
    rot = (90, 0, 0) if axis == "z" else (0, 0, 0)
    s.box(name, parent, pos, (diameter, depth, diameter), color, rot=rot, shape="Cylinder", rough=0.4, metallic=0.2)
    if axis == "y":
        s.box(name + " Head", parent, (pos[0], pos[1] + depth / 2 + 0.003, pos[2]), (diameter * 0.96, 0.006, diameter * 0.96),
              WHITE, shape="Cylinder", rough=0.7)
    else:
        s.box(name + " Head", parent, (pos[0], pos[1], pos[2] - depth / 2 - 0.003), (diameter * 0.96, 0.006, diameter * 0.96),
              WHITE, rot=rot, shape="Cylinder", rough=0.7)


def cymbal(s, parent, name, pos, diameter, tilt=8.0):
    s.box(name + " Stand", parent, (pos[0], pos[1] / 2, pos[2]), (0.025, pos[1], 0.025), CHROME, shape="Cylinder", metallic=0.9, rough=0.3)
    s.box(name, parent, pos, (diameter, 0.012, diameter), BRASS, rot=(tilt, 0, 0), shape="Cylinder", metallic=0.9, rough=0.25)


def kit(s, parent, room, at):
    x, z = at
    k = slot(s, parent, "Starter Kit", "Kit")
    drum(s, k, "Kick", (x, 0.28, z), 0.56, 0.42, room.shell, axis="z")
    drum(s, k, "Snare", (x - 0.38, 0.62, z - 0.28), 0.36, 0.14, CHROME)
    drum(s, k, "Rack Tom", (x - 0.14, 0.78, z + 0.02), 0.27, 0.2, room.shell)
    drum(s, k, "Floor Tom", (x + 0.5, 0.42, z - 0.12), 0.4, 0.4, room.shell)
    s.box("Snare Stand", k, (x - 0.38, 0.27, z - 0.28), (0.03, 0.55, 0.03), CHROME, shape="Cylinder", metallic=0.9, rough=0.3)
    cymbal(s, k, "Hi-Hat", (x - 0.72, 0.85, z - 0.2), 0.36, 0.0)
    cymbal(s, k, "Crash", (x - 0.55, 1.3, z + 0.15), 0.45, -12.0)
    cymbal(s, k, "Ride", (x + 0.7, 1.15, z + 0.2), 0.5, -10.0)
    s.box("Throne", k, (x + 0.05, 0.5, z + 0.55), (0.36, 0.08, 0.36), BLACK, shape="Cylinder", rough=0.8)
    s.box("Throne Post", k, (x + 0.05, 0.24, z + 0.55), (0.04, 0.48, 0.04), CHROME, shape="Cylinder", metallic=0.9)


def build_room(room, extras):
    s = Scene(seed=room.seed)
    root = s.group(f"Hideout {room.name}")
    geo = s.group("Room", root)
    stuff = s.group("Stations", root)
    items = s.group("Items", root)
    marks = s.group("Markers", root)
    h, d, top = room.half, room.depth, room.height

    # The shell: floor, ceiling, three walls (the doorway end stays open behind the camera).
    s.slab("Floor", geo, -h, h, -0.1, 0.0, -1.5, d, room.floor, rough=0.95)
    # The ceiling casts shadows: it keeps the engine's sun (a scene with no directional gets one) out.
    s.slab("Ceiling", geo, -h, h, top, top + 0.1, -1.5, d, room.ceiling, rough=0.95)
    s.slab("Back Wall", geo, -h, h, 0, top, d, d + 0.1, room.walls)
    s.slab("Left Wall", geo, -h - 0.1, -h, 0, top, -1.5, d, room.walls)
    s.slab("Right Wall", geo, h, h + 0.1, 0, top, -1.5, d, room.walls)
    s.slab("Front Wall Left", geo, -h, -0.6, 0, top, -1.6, -1.5, room.walls)
    s.slab("Front Wall Right", geo, 0.6, h, 0, top, -1.6, -1.5, room.walls)

    # Light: a main light over the kit, a fill by the door, and the room's own.
    s.light("Main Light", geo, (0, top - 0.25, d * 0.62), "Point", room.light, room.light_power, 12, shadows=True)
    s.light("Fill Light", geo, (0, top - 0.3, 0.6), "Point", room.light, room.light_power * 0.6, 9)
    s.light("Side Light", geo, (h - 0.6, top - 0.4, d * 0.4), "Point", room.light, room.light_power * 0.35, 7)

    kit_at = (0.0, d - 1.1)
    # The player's drummer at the kit (Band), playing along with the radio.
    drummer(s, items, (kit_at[0], 0.0, kit_at[1] + 0.25))
    station(s, stuff, "Kit", "Kit", (kit_at[0], 0.9, kit_at[1]), (0.35, 0.75, -2.1), 42)

    # Left wall: the workbench with the practice pad, and the gig board.
    bench_z = d - 2.2
    s.slab("Workbench", geo, -h, -h + 0.6, 0.0, 0.85, bench_z - 0.7, bench_z + 0.7, WOOD, rough=0.85)
    station(s, stuff, "Practice Pad", "PracticePad", (-h + 0.3, 0.95, bench_z), (1.45, 0.65, -0.55), 40)
    pad = slot(s, items, "Practice Pad", "PracticePad")
    s.box("Pad", pad, (-h + 0.3, 0.88, bench_z), (0.3, 0.03, 0.3), (0.12, 0.12, 0.12), shape="Cylinder", rough=0.9)
    s.box("Sticks", pad, (-h + 0.42, 0.87, bench_z + 0.2), (0.4, 0.015, 0.015), (0.85, 0.7, 0.45), rot=(0, 20, 0))
    met = slot(s, items, "Metronome", "Metronome")
    s.box("Metronome", met, (-h + 0.3, 0.95, bench_z - 0.45), (0.1, 0.18, 0.08), (0.5, 0.15, 0.1), rough=0.6)

    board_z = d - 0.9
    s.slab("Gig Board", geo, -h, -h + 0.03, 1.1, 2.0, board_z - 0.75, board_z + 0.75, CORK, rough=0.95)
    station(s, stuff, "Gig Board", "GigBoard", (-h + 0.05, 1.55, board_z), (1.7, 0.05, -0.9), 45)
    for i, (slot_name, colour) in enumerate([("FlyerA", (1.0, 0.85, 0.3)), ("FlyerB", (0.95, 0.3, 0.5)), ("FlyerC", (0.3, 0.75, 1.0))]):
        f = slot(s, items, f"Flyer {slot_name[-1]}", slot_name)
        s.box("Flyer", f, (-h + 0.045, 1.6 - (i % 2) * 0.25, board_z - 0.45 + i * 0.42), (0.01, 0.38, 0.27), colour,
              emissive=colour, emissive_intensity=0.15, rough=0.9)

    # Right wall: the trophy wall (posters, plaques, the gold record, the shelf).
    wall_z = d - 1.5
    station(s, stuff, "Trophy Wall", "TrophyWall", (h - 0.05, 2.0, wall_z), (-2.2, -0.35, -0.6), 55)
    poster = slot(s, items, "Band Poster", "PosterA")
    s.box("Poster", poster, (h - 0.02, 1.65, wall_z - 0.9), (0.01, 0.8, 0.56), (0.15, 0.1, 0.35), emissive=(0.5, 0.2, 0.8),
          emissive_intensity=0.2, rough=0.9)
    for slot_name, z in (("PlaqueA", wall_z - 0.15), ("PlaqueB", wall_z + 0.25)):
        p = slot(s, items, slot_name, slot_name)
        s.box("Plaque", p, (h - 0.03, 1.75, z), (0.03, 0.3, 0.24), WOOD, rough=0.6)
        s.box("Plate", p, (h - 0.05, 1.75, z), (0.01, 0.16, 0.16), GOLD, metallic=0.9, rough=0.25)
    rec = slot(s, items, "Gold Record", "GoldRecord")
    s.box("Frame", rec, (h - 0.03, 1.6, wall_z + 0.85), (0.03, 0.6, 0.5), BLACK, rough=0.5)
    s.box("Record", rec, (h - 0.05, 1.62, wall_z + 0.85), (0.38, 0.01, 0.38), GOLD, rot=(0, 0, 90), shape="Cylinder", metallic=1.0, rough=0.15)
    shelf = slot(s, items, "Vinyl Shelf", "Shelf")
    s.slab("Shelf", shelf, h - 0.3, h, 0.0, 0.7, wall_z - 0.6, wall_z + 0.6, WOOD, rough=0.8)
    for i in range(9):
        s.box(f"Sleeve {i}", shelf, (h - 0.15, 0.5, wall_z - 0.5 + i * 0.12), (0.25, 0.3, 0.02),
              [(0.8, 0.2, 0.2), (0.2, 0.5, 0.8), (0.9, 0.8, 0.2), (0.1, 0.1, 0.1)][i % 4], rough=0.7)
    snare_head = slot(s, items, "Signed Snare Head", "WallLeft")
    s.box("Signed Head", snare_head, (h - 0.03, 2.05, wall_z - 0.15), (0.32, 0.01, 0.32), WHITE, rot=(0, 0, 90), shape="Cylinder", rough=0.6)

    # Front right: the radio and the laptop on a crate.
    crate = (-1.3, 0.0, 1.9)
    s.slab("Crate", geo, crate[0] - 0.35, crate[0] + 0.35, 0.0, 0.62, crate[2] - 0.3, crate[2] + 0.3, WOOD, rough=0.9)
    laptop = (crate[0] - 0.05, 0.64, crate[2] - 0.05)
    s.box("Laptop Base", stuff, (laptop[0], 0.635, laptop[2]), (0.36, 0.02, 0.25), (0.2, 0.2, 0.22), metallic=0.6, rough=0.4)
    s.box("Laptop Screen", stuff, (laptop[0], 0.77, laptop[2] + 0.12), (0.36, 0.24, 0.015), (0.05, 0.1, 0.2),
          rot=(-15, 0, 0), emissive=(0.3, 0.55, 1.0), emissive_intensity=1.5, rough=0.2)
    station(s, stuff, "Laptop", "Laptop", (laptop[0], 0.75, laptop[2]), (0.35, 0.5, -0.95), 40)

    radio_at = (h - 0.25, 1.1, d - 3.1)
    s.slab("Radio Shelf", geo, h - 0.4, h, 0.95, 0.99, radio_at[2] - 0.35, radio_at[2] + 0.35, WOOD, rough=0.8)
    radio = slot(s, items, "Radio", "Radio")
    s.box("Radio Body", radio, radio_at, (0.18, 0.2, 0.42), (0.35, 0.12, 0.08), rough=0.5)
    s.box("Radio Dial", radio, (radio_at[0] - 0.095, radio_at[1] + 0.03, radio_at[2] + 0.08), (0.01, 0.06, 0.16), (0.9, 0.6, 0.2),
          emissive=(1.0, 0.6, 0.2), emissive_intensity=2.0)
    s.box("Radio Grille", radio, (radio_at[0] - 0.095, radio_at[1] - 0.02, radio_at[2] - 0.1), (0.13, 0.01, 0.13), (0.1, 0.1, 0.1),
          shape="Cylinder", rot=(0, 0, 90))
    station(s, stuff, "Radio", "Radio", radio_at, (-1.3, 0.15, -0.5), 40)

    # Beside the kit: the amp that is the settings.
    amp_at = (kit_at[0] + 1.45, 0.0, kit_at[1] - 0.1)
    s.box("Amp", stuff, (amp_at[0], 0.32, amp_at[2]), (0.62, 0.64, 0.32), (0.08, 0.08, 0.08), rough=0.6)
    s.box("Amp Grille", stuff, (amp_at[0], 0.28, amp_at[2] - 0.165), (0.55, 0.45, 0.01), (0.18, 0.16, 0.14), rough=0.95)
    s.box("Amp Panel", stuff, (amp_at[0], 0.57, amp_at[2] - 0.165), (0.55, 0.06, 0.01), (0.7, 0.6, 0.4), metallic=0.6, rough=0.3)
    station(s, stuff, "Mixer", "Mixer", (amp_at[0], 0.45, amp_at[2]), (-0.5, 0.65, -1.4), 45, label="SETTINGS")

    # Decorations that come with unlocks.
    rug = slot(s, items, "Rug", "Rug")
    s.box("Rug", rug, (kit_at[0], 0.005, kit_at[1] + 0.05), (2.2, 0.01, 1.8), (0.45, 0.12, 0.1), rough=1.0, shadows=False)
    bag = slot(s, items, "Stick Bag", "StickBag")
    s.box("Bag", bag, (kit_at[0] + 0.78, 0.45, kit_at[1] - 0.12), (0.06, 0.4, 0.14), (0.1, 0.1, 0.12), rough=0.9)
    spare = slot(s, items, "Spare Cymbal", "CymbalStand")
    cymbal(s, spare, "Spare Cymbal", (kit_at[0] - 1.1, 1.2, kit_at[1] + 0.3), 0.42, -15.0)
    lamp = slot(s, items, "Lava Lamp", "Lamp")
    s.box("Lamp", lamp, (-h + 0.3, 1.05, bench_z + 0.5), (0.1, 0.32, 0.1), (0.9, 0.3, 0.6), shape="Capsule",
          emissive=(1.0, 0.3, 0.6), emissive_intensity=3.0)
    s.light("Lamp Glow", lamp, (-h + 0.45, 1.1, bench_z + 0.5), "Point", (1.0, 0.35, 0.6), 4.0, 3)
    neon = slot(s, items, "Neon Sign", "Neon")
    s.box("Neon", neon, (kit_at[0], 2.05 if top > 2.4 else top - 0.35, d - 0.03), (1.4, 0.3, 0.02), (0.2, 0.05, 0.1),
          emissive=(1.0, 0.15, 0.55), emissive_intensity=4.0)
    s.light("Neon Glow", neon, (kit_at[0], 1.9 if top > 2.4 else top - 0.5, d - 0.4), "Point", (1.0, 0.2, 0.6), 6.0, 4)
    foam = slot(s, items, "Acoustic Foam", "Foam")
    for i in range(6):
        for j in range(3):
            s.box(f"Foam {i}.{j}", foam, (-h + 0.04, 0.9 + j * 0.55, 1.0 + i * 0.55), (0.06, 0.5, 0.5), (0.1, 0.1, 0.12),
                  rough=1.0, shadows=False)
    desk = slot(s, items, "Mixing Desk", "Desk")
    s.box("Desk", desk, (1.5, 0.8, 1.7), (1.4, 0.1, 0.7), (0.15, 0.15, 0.16), rot=(-10, 0, 0), rough=0.4)
    s.box("Desk Faders", desk, (1.5, 0.86, 1.7), (1.3, 0.02, 0.6), (0.1, 0.1, 0.1), rot=(-10, 0, 0),
          emissive=(0.2, 0.9, 0.4), emissive_intensity=0.6)

    extras(s, geo, room)

    # The overview, from the doorway.
    eye = (0.0, 1.75, -1.4)
    target = (0.15, 0.95, d * 0.62)
    view = s.entity("Overview", marks, eye, look_rotation(eye, target))
    view.add({"Type": "HideoutView", "FieldOfView": 70.0})
    return s


def basement_extras(s, geo, room):
    h = room.half
    s.box("Boiler", geo, (-h + 0.45, 0.85, 0.2), (0.6, 1.7, 0.6), (0.55, 0.55, 0.5), shape="Cylinder", metallic=0.5, rough=0.5)
    s.box("Washing Machine", geo, (-h + 0.45, 0.42, 1.0), (0.6, 0.84, 0.6), WHITE, rough=0.4)
    s.box("Pipe", geo, (1.4, room.height - 0.12, room.depth * 0.5 + 0.8), (0.08, room.depth - 1.6, 0.08), (0.5, 0.35, 0.2), rot=(90, 0, 0),
          shape="Cylinder", metallic=0.7, rough=0.4)
    s.box("Bulb", geo, (0.0, room.height - 0.3, room.depth * 0.62), (0.08, 0.1, 0.08), (1.0, 0.9, 0.6), shape="Sphere",
          emissive=(1.0, 0.85, 0.55), emissive_intensity=6.0, shadows=False)
    s.box("Window", geo, (0.9, room.height - 0.35, room.depth - 0.02), (0.9, 0.3, 0.02), (0.3, 0.4, 0.5),
          emissive=(0.25, 0.35, 0.5), emissive_intensity=0.8)


def garage_extras(s, geo, room):
    h = room.half
    s.slab("Roll Door", geo, -1.6, 1.6, 0.0, room.height - 0.2, room.depth - 0.06, room.depth - 0.02, (0.6, 0.62, 0.6), metallic=0.4, rough=0.6)
    for i in range(8):
        s.slab(f"Door Rib {i}", geo, -1.6, 1.6, 0.25 + i * 0.32, 0.29 + i * 0.32, room.depth - 0.09, room.depth - 0.06, (0.5, 0.52, 0.5))
    s.box("Oil Stain", geo, (-1.5, 0.004, 1.6), (1.1, 0.005, 0.8), (0.05, 0.05, 0.05), shape="Cylinder", rough=0.2, shadows=False)
    s.box("Tyres", geo, (h - 0.45, 0.35, room.depth - 0.5), (0.65, 0.7, 0.65), BLACK, shape="Cylinder", rough=0.95)
    s.box("Tube Light", geo, (0.0, room.height - 0.05, room.depth * 0.5), (0.06, 1.4, 0.06), (0.95, 0.97, 1.0), rot=(90, 0, 0),
          shape="Cylinder", emissive=(0.9, 0.95, 1.0), emissive_intensity=4.0, shadows=False)


def rehearsal_extras(s, geo, room):
    h = room.half
    for side in (-1, 1):
        s.box(f"PA {side}", geo, (side * (h - 0.5), 0.75, room.depth - 0.5), (0.55, 1.5, 0.5), BLACK, rough=0.7)
        s.box(f"PA Cone {side}", geo, (side * (h - 0.5), 0.6, room.depth - 0.76), (0.4, 0.02, 0.4), (0.15, 0.15, 0.15),
              rot=(90, 0, 0), shape="Cylinder")
    s.box("Mic Stand", geo, (0.0, 0.8, room.depth - 2.4), (0.03, 1.6, 0.03), CHROME, shape="Cylinder", metallic=0.9)
    s.box("Mic", geo, (0.0, 1.62, room.depth - 2.45), (0.05, 0.16, 0.05), BLACK, shape="Capsule")
    s.box("Carpet", geo, (0.0, 0.003, room.depth * 0.5), (room.half * 2 - 0.4, 0.005, room.depth - 0.5), (0.18, 0.16, 0.22),
          rough=1.0, shadows=False)


def studio_extras(s, geo, room):
    h = room.half
    s.box("Control Room Glass", geo, (-h + 0.02, 1.5, room.depth * 0.5 - 0.4), (0.03, 1.1, 2.4), (0.2, 0.3, 0.35),
          emissive=(0.15, 0.3, 0.4), emissive_intensity=0.6, rough=0.05, metallic=0.2)
    for i in range(5):
        s.box(f"Diffuser {i}", geo, (-1.6 + i * 0.8, 2.0, room.depth - 0.06), (0.7, 0.9, 0.1), WOOD, rough=0.7)
    s.box("Overhead Mic", geo, (0.0, 2.1, room.depth - 1.1), (0.06, 0.2, 0.06), CHROME, shape="Capsule", metallic=0.9)
    s.box("Gobo", geo, (h - 0.8, 0.9, room.depth - 2.0), (1.0, 1.8, 0.08), (0.25, 0.25, 0.3), rot=(0, -30, 0), rough=0.9)


ROOMS = [
    (Room("Basement", 2101, 6.4, 6.0, 2.5, (0.36, 0.36, 0.35), (0.48, 0.47, 0.44), (0.3, 0.3, 0.3), (1.0, 0.82, 0.6), 24.0,
          (0.45, 0.08, 0.08)), basement_extras),
    (Room("Garage", 2102, 7.6, 7.2, 3.0, (0.4, 0.41, 0.42), (0.62, 0.6, 0.55), (0.45, 0.45, 0.45), (0.92, 0.95, 1.0), 34.0,
          (0.1, 0.18, 0.45)), garage_extras),
    (Room("Rehearsal", 2103, 8.4, 7.8, 3.0, (0.18, 0.16, 0.2), (0.16, 0.15, 0.2), (0.12, 0.12, 0.14), (1.0, 0.75, 0.55), 38.0,
          (0.05, 0.05, 0.05)), rehearsal_extras),
    (Room("Studio", 2104, 9.0, 8.4, 3.4, (0.5, 0.35, 0.2), (0.75, 0.72, 0.66), (0.6, 0.6, 0.6), (1.0, 0.9, 0.78), 48.0,
          (0.55, 0.38, 0.12)), studio_extras),
]


def main():
    folder = os.path.join(repo_root(), "Assets", "Hideout")
    for room, extras in ROOMS:
        dressed = {"Basement": build_basement, "Garage": build_garage, "Rehearsal": build_rehearsal, "Studio": build_studio}
        scene = dressed[room.name]() if room.name in dressed else build_room(room, extras)
        scene.write(os.path.join(folder, f"{room.name}.lvl"))
    print("wrote", folder)


if __name__ == "__main__":
    main()
