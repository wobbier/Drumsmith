#!/usr/bin/env python3
"""Writes Assets/Venues/StoryRadioStation/: set 07, The Pledge Drive Night Shift.

    python3 Tools/Venues/make_story_radio_station.py [--textures] [--sound]

A campus radio station at 02:47. The band plays in the live room (foam, carpet tiles, one vocal
mic, a session kit on a rug). Behind them a big window looks up a step into the control room: the
mixing desk, then a riser with five phone desks facing the glass, and the volunteers. As the set
goes by the phones light one by one, pledge slips climb the glass, and the rent gets paid.

Story flags (s07-pledge-drive): first_phone_lit, second_phone_lit, pledges_cover_glass,
all_phones_lit, rent_paid. Deterministic: rerun = same bytes. --textures redraws the pictures
(slow; ImageMagick), --sound resynthesises the room tone (ffmpeg).
"""
import math
import os
import random
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from venuegen import Scene, look_rotation, repo_root, write_venue_json, _r, vec  # noqa: E402
import story_radio_station_people as people  # noqa: E402

ID = "StoryRadioStation"
VENUE = f"Assets/Venues/{ID}/"
TEX = VENUE + "Textures/"
MODELS = VENUE + "Models/"

# ---- the room, in metres (venue space: +z from the camera toward the band and the glass) ------
HW = 6.0            # live room half width
LR_BACK = -4.6      # the live room's back wall, behind the cameras
CEIL = 3.6          # live room ceiling
GZ = 4.6            # the glass's plane
WALL_T = 0.2        # the glass wall's thickness (4.5 .. 4.7)
WIN_X = 5.4         # window half width
WIN_Y0, WIN_Y1 = 0.9, 2.8
CR_HW = 6.6         # control room half width
CR_BACK = 10.6
CR_CEIL = 3.9
TIER0, TIER1 = 0.45, 0.95       # control room floor heights: console row, phone riser
TIER_Z = 6.7                    # where the riser starts
DESK_Z = 7.45                   # phone desks' centre
DESK_X = (-4.6, -2.3, 0.0, 2.3, 4.6)
DESK_TOP = TIER1 + 0.74

DRUMMER = (0.9, 0.0, 3.25)
VOCALS = (-2.6, 0.0, 2.75)
WIDE_EYE, WIDE_AIM = (0.2, 2.15, -3.0), (-0.3, 1.85, 4.6)

FLAGS = ("first_phone_lit", "second_phone_lit", "pledges_cover_glass", "all_phones_lit", "rent_paid")

# colours
CHARCOAL = (0.07, 0.075, 0.09)
FRAME = (0.16, 0.16, 0.18)
ALU = (0.55, 0.56, 0.58)
BEIGE = (0.62, 0.56, 0.45)
DESK_TOP_C = (0.66, 0.6, 0.5)
DESK_BODY = (0.24, 0.24, 0.27)
RED = (1.0, 0.12, 0.08)
AMBER = (1.0, 0.55, 0.12)
FLUO = (0.82, 0.93, 1.0)
CR_FLUO = (0.86, 1.0, 0.9)


def textured(e, path, tile=(1.0, 1.0), emissive=0.0, tint=(1, 1, 1)):
    for comp in e.components:
        if comp.get("Type") == "Mesh":
            m = comp["Material"]
            m["DiffuseColor"] = vec(tint)
            m["Textures"] = {"Diffuse": {"Path": path}}
            if emissive > 0:
                m["Textures"]["Emissive"] = {"Path": path}
                m["EmissiveColor"] = [1.0, 1.0, 1.0]
                m["EmissiveIntensity"] = _r(emissive)
            m["Tiling"] = [_r(tile[0]), _r(-tile[1])]
            m["Offset"] = [0.0, _r(tile[1])]
            return e
    raise ValueError(e.name)


def sheet(s, parent, name, tex, center, w, h, facing="-z", tilt=0.0, glow=0.0, thick=0.006):
    """A flat picture: facing is the way it looks ('-z' toward the cameras, '+x' off the left wall)."""
    if facing in ("+x", "-x"):
        size, rot = (thick, h, w), (tilt, 0, 0)
    else:
        size, rot = (w, h, thick), (0, 0, tilt)
    e = s.box(name, parent, center, size, (1, 1, 1), rot=rot, rough=0.85, shadows=False)
    return textured(e, TEX + tex + ".png", emissive=glow)


def text(s, parent, name, pos, words, size, colour, rot=(0, 0, 0), font="Assets/Fonts/PermanentMarker-Regular.ttf", lit=True):
    e = s.entity(name, parent, pos, rot)
    e.add({"Type": "TextRenderer", "Text": words, "Size": _r(size), "Alignment": "Center", "Anchor": "Middle",
           "Color": vec(colour), "Opacity": 1.0, "Lit": bool(lit), "Font": font})
    return e


def rod(s, parent, name, a, b, d, colour, **kw):
    length = math.dist(a, b)
    centre = tuple((a[i] + b[i]) / 2 for i in range(3))
    pitch, yaw, _ = look_rotation(a, b)
    return s.box(name, parent, centre, (d, length, d), colour, rot=(pitch + 90.0, yaw, 0.0), shape="Cylinder", **kw)


def model(s, parent, name, file, pos, yaw=0.0, scale=1.0):
    path = file if file.startswith("Assets/") else MODELS + "SM_" + file + ".fbx"
    return s.prop(name, parent, path, pos, yaw, scale)


def glow(s, parent, name, pos, size, colour, power, shape="Cube", rot=(0, 0, 0)):
    return s.box(name, parent, pos, size, colour, rot=rot, emissive=colour, emissive_intensity=power, shadows=False, shape=shape)


def plain_light(s, parent, name, pos, colour, intensity, reach, kind="Point", rot=(0, 0, 0), inner=30, outer=60):
    return s.light(name, parent, pos, kind, colour, intensity, reach, rot=rot, inner=inner, outer=outer)


def project_to_glass(p, eye=WIDE_EYE, z=GZ + 0.04):
    t = (z - eye[2]) / (p[2] - eye[2])
    return tuple(eye[i] + (p[i] - eye[i]) * t for i in range(3))


# ---- the live room ----------------------------------------------------------------------------

def live_room(s, geo, dress):
    floor = s.slab("Carpet tiles", geo, -HW, HW, -0.1, 0.0, LR_BACK, GZ - 0.1, (1, 1, 1), rough=0.95)
    textured(floor, TEX + "Carpet.png", (HW, (GZ - LR_BACK) / 2), tint=(1.5, 1.5, 1.5))
    ceil = s.slab("Ceiling tiles", geo, -HW, HW, CEIL, CEIL + 0.1, LR_BACK, GZ - 0.1, (1, 1, 1), rough=0.9, shadows=False)
    textured(ceil, TEX + "CeilingTile.png", (HW / 0.6 * 2 / 2, (GZ - LR_BACK) / 0.6), tint=(0.7, 0.7, 0.7))
    # Walls: dark under foam.
    s.slab("Left wall", geo, -HW - 0.2, -HW, 0, CEIL, LR_BACK, GZ, CHARCOAL, shadows=False)
    s.slab("Right wall", geo, HW, HW + 0.2, 0, CEIL, LR_BACK, GZ, CHARCOAL, shadows=False)
    s.slab("Back wall", geo, -HW, HW, 0, CEIL, LR_BACK - 0.2, LR_BACK, CHARCOAL, shadows=False)
    s.slab("Skirting L", geo, -HW, -HW + 0.03, 0, 0.12, LR_BACK, GZ - 0.1, (0.03, 0.03, 0.035))
    s.slab("Skirting R", geo, HW - 0.03, HW, 0, 0.12, LR_BACK, GZ - 0.1, (0.03, 0.03, 0.035))

    # Foam panels in frames down both side walls, and across the back.
    foam = s.group("Acoustic foam", dress)
    for side in (-1, 1):
        x = side * (HW - 0.06)
        for i, z in enumerate((-3.4, -1.9, -0.4, 1.1, 2.6, 3.85)):
            if side == 1 and z > 3.5:
                continue
            w = 1.2 if z < 3.5 else 0.9
            for k, y in enumerate((0.95, 2.35)):
                if side == -1 and k == 1 and i == 2:
                    continue    # the whiteboard goes there
                p = s.box(f"Foam {side} {i} {k}", foam, (x, y, z), (0.1, 1.2, w), (1, 1, 1), rough=1.0)
                textured(p, TEX + "Foam.png", (w, 1.2))
    for i, x in enumerate((-4.6, -3.0, -1.4, 1.4, 3.0, 4.6)):
        p = s.box(f"Foam back {i}", foam, (x, 1.9, LR_BACK + 0.06), (1.4, 2.0, 0.1), (1, 1, 1), rough=1.0)
        textured(p, TEX + "Foam.png", (1.4, 2.0))

    # Posters for the station's shows, between the foam.
    names = ["PosterNightOwl", "PosterThesis", "PosterSoulKitchen", "PosterDormDemos", "PosterProfVinyl", "PosterGrooveCo"]
    spots = [(-1, -2.65, 1.75, 3), (-1, 0.35, 1.7, -2), (-1, 1.85, 1.68, 4), (1, -2.65, 1.75, -3), (1, -1.15, 1.7, 2), (1, 0.35, 1.72, -1)]
    for name, (side, z, y, tilt) in zip(names, spots):
        sheet(s, dress, name, name, (side * (HW - 0.02), y, z), 0.6, 0.9, "+x" if side < 0 else "-x", tilt)
    sheet(s, dress, "Whiteboard", "Whiteboard", (-HW + 0.03, 2.25, -0.4), 1.5, 1.0, "+x")
    s.box("Whiteboard frame", dress, (-HW + 0.02, 2.25, -0.4), (0.02, 1.06, 1.56), ALU, metallic=0.6, rough=0.4)
    s.box("Marker tray", dress, (-HW + 0.07, 1.72, -0.4), (0.08, 0.03, 1.2), ALU, metallic=0.6, rough=0.4)
    clock = s.box("Studio clock", dress, (-HW + 0.04, 2.95, 3.0), (0.36, 0.05, 0.36), (1, 1, 1), rot=(0, 0, 90), shape="Cylinder", shadows=False)
    textured(clock, TEX + "Clock.png")

    # The door out (back right) with the exit sign and its own little ON AIR warning.
    s.slab("Door", dress, HW - 0.04, HW - 0.01, 0, 2.1, -3.7, -2.7, (0.32, 0.22, 0.14), rough=0.6)
    s.slab("Door frame", dress, HW - 0.05, HW - 0.02, 0, 2.18, -3.78, -2.62, (0.1, 0.1, 0.11))
    s.box("Door handle", dress, (HW - 0.09, 1.05, -2.85), (0.06, 0.04, 0.16), ALU, metallic=0.8, rough=0.3)
    s.box("Door glass", dress, (HW - 0.045, 1.55, -3.2), (0.01, 0.5, 0.2), (0.25, 0.3, 0.35), rough=0.1)
    model(s, dress, "Exit sign", "Prop_Sign_Exit_01", (HW - 0.06, 2.35, -3.2), -90)
    model(s, dress, "Extinguisher", "Prop_Fire_Extinguisher_01", (HW - 0.2, 0.0, -2.2), -90)

    # The couch corner (where the waiting voices sit), back left.
    model(s, dress, "Green room couch", "Prop_Couch_01", (-HW + 0.6, 0.0, -2.6), 90)
    model(s, dress, "Water cooler", "Prop_WaterCooler_01", (-HW + 0.4, 0.0, -4.05), 90)
    model(s, dress, "Plant", "Prop_Plant_02", (-HW + 0.45, 0.0, -0.9), 0)
    s.box("Side table", dress, (-HW + 0.6, 0.25, -1.45), (0.5, 0.5, 0.5), (0.3, 0.22, 0.15), rough=0.7)
    model(s, dress, "Donuts", "Prop_Donut_Box_01", (-HW + 0.6, 0.5, -1.45), 70)
    model(s, dress, "Clipboard", "Prop_Clipboard_01", (-HW + 0.95, 0.42, -2.25), 20)


def kit_corner(s, dress):
    """The station session kit: a rug, two foam gobos, an overhead room mic, phones on a hook."""
    kit = s.group("Session kit dressing", dress)
    dx, _, dz = DRUMMER
    s.prop("Kit rug", kit, "Assets/Models/Venue/DrumRug.obj", (dx, 0.005, dz - 0.9), 0.0, 1.0)
    for i, (x, z, yaw) in enumerate(((dx + 2.2, dz - 0.6, -35), (dx - 1.9, dz + 0.2, 35))):
        g = s.entity(f"Gobo {i}", kit, (x, 0, z), (0, yaw, 0))
        s.box("Gobo frame", g, (0, 0.75, 0), (1.2, 1.1, 0.12), FRAME, rough=0.6)
        f = s.box("Gobo foam", g, (0, 0.75, -0.07), (1.1, 1.0, 0.04), (1, 1, 1), rough=1.0)
        textured(f, TEX + "Foam.png", (1.1, 1.0))
        for k in (-0.5, 0.5):
            s.box("Gobo foot", g, (k, 0.1, 0), (0.08, 0.2, 0.5), FRAME)
            rod(s, g, "Gobo caster", (k, 0.02, -0.2), (k, 0.02, 0.2), 0.05, (0.05, 0.05, 0.05))
    # Overhead room mic on a boom, over the kit from stage right.
    base = (dx + 1.55, 0, dz + 0.55)
    rod(s, kit, "Boom stand", base, (base[0], 2.05, base[2]), 0.03, (0.06, 0.06, 0.07), metallic=0.5)
    rod(s, kit, "Boom arm", (base[0], 2.05, base[2]), (dx + 0.35, 2.3, dz - 0.6), 0.022, (0.06, 0.06, 0.07), metallic=0.5)
    s.box("Room mic", kit, (dx + 0.35, 2.24, dz - 0.6), (0.06, 0.16, 0.06), (0.75, 0.75, 0.78), shape="Cylinder", metallic=0.8, rough=0.3)
    for k in range(3):
        a = math.radians(k * 120)
        rod(s, kit, f"Boom leg {k}", (base[0], 0.35, base[2]), (base[0] + 0.32 * math.sin(a), 0.01, base[2] + 0.32 * math.cos(a)), 0.02, (0.06, 0.06, 0.07))
    model(s, kit, "Drummer's cans", "Chr_Attachment_Headset_01", (base[0] + 0.06, 1.35, base[2] - 0.02), 0, 1.0)
    s.prop("Cable coil", kit, "Assets/Models/Venue/CableCoil.obj", (dx - 1.4, 0.0, dz - 1.5), 30.0)
    s.prop("Cable run", kit, "Assets/Models/Venue/CableA.obj", (dx - 0.9, 0.0, dz - 2.1), 80.0)
    # Gaffer-tape mark and a setlist on the floor.
    s.box("Tape X a", kit, (dx + 0.0, 0.012, dz - 2.25), (0.5, 0.004, 0.05), (0.85, 0.8, 0.2), rot=(0, 45, 0), shadows=False)
    s.box("Tape X b", kit, (dx + 0.0, 0.012, dz - 2.25), (0.5, 0.004, 0.05), (0.85, 0.8, 0.2), rot=(0, -45, 0), shadows=False)
    s.box("Water bottle", kit, (dx + 1.25, 0.12, dz - 0.15), (0.07, 0.24, 0.07), (0.5, 0.7, 0.9), shape="Cylinder", rough=0.2)


def presenter_corner(s, dress, lamps):
    """The guest's corner by the glass: a lyric stand, a stool, a desk lamp on a little table."""
    c = s.group("Presenter corner", dress)
    vx, _, vz = VOCALS
    tx, tz = vx - 1.05, vz + 0.75
    s.box("Script table", c, (tx, 0.36, tz), (0.6, 0.04, 0.45), (0.3, 0.22, 0.15), rough=0.6)
    for k in ((-0.26, -0.18), (0.26, -0.18), (-0.26, 0.18), (0.26, 0.18)):
        s.box("Table leg", c, (tx + k[0], 0.17, tz + k[1]), (0.03, 0.34, 0.03), FRAME)
    model(s, c, "Spare cans", "Chr_Attachment_Headset_01", (tx - 0.12, 0.38, tz), 30)
    model(s, c, "Pledge pile", "Prop_Paper_Pile_02", (tx + 0.15, 0.38, tz - 0.05), 10)
    # Lamp: a warm practical on the table.
    rod(s, c, "Lamp stem", (tx + 0.18, 0.38, tz + 0.12), (tx + 0.1, 0.78, tz + 0.05), 0.02, FRAME)
    glow(s, c, "Lamp shade", (tx + 0.1, 0.8, tz + 0.05), (0.18, 0.12, 0.18), (1.0, 0.7, 0.4), 2.0, "Cylinder")
    plain_light(s, lamps, "Presenter lamp", (tx + 0.1, 0.7, tz + 0.05), (1.0, 0.66, 0.38), 6.0, 3.0)
    # Lyric stand beside the mic.
    st = (vx + 0.75, 0, vz - 0.35)
    rod(s, c, "Lyric stand", st, (st[0], 1.05, st[2]), 0.025, FRAME, metallic=0.4)
    s.box("Lyric desk", c, (st[0], 1.12, st[2] - 0.02), (0.45, 0.32, 0.02), FRAME, rot=(-25, -20, 0))
    sheet(s, c, "Lyric sheet", "Pledge2", (st[0], 1.13, st[2] - 0.035), 0.24, 0.3, tilt=0, thick=0.004)
    s.prop("Guest stool", c, "Assets/Models/Venue/Stool.obj", (vx - 0.55, 0.0, vz + 0.55), 20.0)


# ---- the glass wall ---------------------------------------------------------------------------

def glass_wall(s, geo, dress, lamps):
    z0, z1 = GZ - WALL_T / 2, GZ + WALL_T / 2
    wall = (0.11, 0.11, 0.13)
    s.slab("Glass wall sill", geo, -HW, HW, 0, WIN_Y0, z0, z1, wall)
    s.slab("Glass wall header", geo, -HW, HW, WIN_Y1, CEIL, z0, z1, wall, shadows=False)
    s.slab("Glass wall pier L", geo, -HW, -WIN_X, WIN_Y0, WIN_Y1, z0, z1, wall)
    s.slab("Glass wall pier R", geo, WIN_X, HW, WIN_Y0, WIN_Y1, z0, z1, wall)
    s.slab("Sill ledge", geo, -WIN_X, WIN_X, WIN_Y0 - 0.03, WIN_Y0, z0 - 0.1, z1, (0.35, 0.3, 0.25), rough=0.5)
    for x in (-1.8, 1.8):
        s.slab(f"Mullion {x}", geo, x - 0.05, x + 0.05, WIN_Y0, WIN_Y1, z0 + 0.02, z1 - 0.02, (0.2, 0.2, 0.22), metallic=0.4, rough=0.4)
    for name, y in (("Frame top", WIN_Y1), ("Frame bottom", WIN_Y0)):
        s.slab(name, geo, -WIN_X, WIN_X, y - 0.03, y + 0.03, z0 - 0.01, z0 + 0.03, (0.2, 0.2, 0.22), metallic=0.4, rough=0.4)
    pane = s.box("Window glass", geo, (0, (WIN_Y0 + WIN_Y1) / 2, GZ), (2 * WIN_X, WIN_Y1 - WIN_Y0, 0.02), (0.6, 0.75, 0.85),
                 rough=0.05, metallic=0.1, shadows=False)
    m = pane.components[-1]["Material"]
    m["Opacity"] = 0.1
    m["RenderMode"] = 1
    # Two faint streaks of reflection, so the pane reads as glass.
    for i, (x, w) in enumerate(((-3.6, 0.5), (2.6, 0.32))):
        st = s.box(f"Glass streak {i}", geo, (x, (WIN_Y0 + WIN_Y1) / 2, GZ - 0.015), (w, 2.4, 0.004), (0.9, 0.95, 1.0),
                   rot=(0, 0, 32), rough=0.05, shadows=False)
        sm = st.components[-1]["Material"]
        sm["Opacity"] = 0.05
        sm["RenderMode"] = 1

    # ON AIR, centre of the header, and its red glow on the backs of the band.
    s.box("On Air housing", dress, (0, 3.18, z0 - 0.06), (1.1, 0.42, 0.12), (0.05, 0.05, 0.05), rough=0.4)
    sheet(s, dress, "On Air", "OnAir", (0, 3.18, z0 - 0.125), 0.98, 0.34, glow=3.2)
    plain_light(s, lamps, "On Air glow", (0, 3.05, z0 - 0.5), RED, 26.0, 6.5)

    # The phone-line lamp board, header left. Lamps for lines 1-5 (lit ones are story props).
    bx0, bw = -5.1, 2.8
    sheet(s, dress, "Line board", "LineBoard", (bx0 + bw / 2, 3.18, z0 - 0.02), bw, bw * 160 / 1024)
    lamps_at = []
    for i in range(5):
        u = (300 + i * 150 + 56) / 1024.0
        p = (bx0 + bw * u, 3.18, z0 - 0.05)
        s.box(f"Line lamp {i+1} (off)", dress, p, (0.12, 0.12, 0.06), (0.22, 0.06, 0.04), shape="Sphere", rough=0.3)
        lamps_at.append(p)
    # Station banner, header right.
    sheet(s, dress, "Station banner", "StationBanner", (3.25, 3.18, z0 - 0.02), 2.4, 0.6)
    return lamps_at


# ---- the control room -------------------------------------------------------------------------

def control_room(s, geo, dress, lamps, cast):
    z0 = GZ + WALL_T / 2
    s.slab("CR floor (console row)", geo, -CR_HW, CR_HW, 0, TIER0, z0, TIER_Z, (0.18, 0.16, 0.14), rough=0.8)
    s.slab("CR riser", geo, -CR_HW, CR_HW, 0, TIER1, TIER_Z, CR_BACK, (0.2, 0.18, 0.15), rough=0.8)
    s.slab("Riser nosing", geo, -CR_HW, CR_HW, TIER1 - 0.04, TIER1 + 0.005, TIER_Z - 0.03, TIER_Z + 0.04, (0.75, 0.6, 0.15), rough=0.5)
    s.slab("CR ceiling", geo, -CR_HW, CR_HW, CR_CEIL, CR_CEIL + 0.1, z0, CR_BACK, (0.55, 0.55, 0.52), shadows=False)
    back = s.slab("CR back wall", geo, -CR_HW, CR_HW, 0, CR_CEIL, CR_BACK, CR_BACK + 0.2, (1, 1, 1), shadows=False)
    textured(back, TEX + "CRWall.png", (CR_HW * 2 / 1.6, CR_CEIL / 0.8))
    for side in (-1, 1):
        x0, x1 = (CR_HW, CR_HW + 0.2) if side > 0 else (-CR_HW - 0.2, -CR_HW)
        w = s.slab(f"CR side wall {side}", geo, x0, x1, 0, CR_CEIL, z0, CR_BACK, (1, 1, 1), shadows=False)
        textured(w, TEX + "CRWall.png", ((CR_BACK - z0) / 1.6, CR_CEIL / 0.8))

    # Fluorescent troffers.
    for i, (x, z) in enumerate(((-3.6, 5.6), (0.0, 5.6), (3.6, 5.6), (-3.6, 8.6), (0.0, 8.6), (3.6, 8.6))):
        s.box(f"CR troffer {i}", dress, (x, CR_CEIL - 0.01, z), (1.2, 0.03, 0.6), (0.6, 0.6, 0.6), rough=0.4, shadows=False)
        glow(s, dress, f"CR tube {i}", (x, CR_CEIL - 0.03, z), (1.1, 0.02, 0.5), CR_FLUO, 2.2)
    for i, (x, z) in enumerate(((-3.2, 6.6), (3.2, 6.6), (-2.6, 9.2), (2.6, 9.2))):
        plain_light(s, lamps, f"CR fluorescent {i}", (x, CR_CEIL - 0.35, z), CR_FLUO, 16.0, 7.0)

    # Back wall: the pledge banner, a cork board, bunting across.
    sheet(s, dress, "Pledge banner", "PledgeBanner", (-3.3, 3.05, CR_BACK - 0.02), 3.2, 0.8)
    s.box("Cork board", dress, (3.2, 2.5, CR_BACK - 0.03), (2.2, 1.2, 0.04), (0.6, 0.45, 0.28), rough=0.95)
    rnd = random.Random(707)
    for i in range(9):
        sheet(s, dress, f"Cork note {i}", f"Pledge{rnd.randrange(10)}", (2.3 + (i % 5) * 0.42 + rnd.uniform(-0.05, 0.05),
              2.75 - (i // 5) * 0.48 + rnd.uniform(-0.04, 0.04), CR_BACK - 0.055), 0.26, 0.33, tilt=rnd.uniform(-8, 8))
    sheet(s, dress, "CR poster", "PosterSoulKitchen", (-0.2, 2.5, CR_BACK - 0.02), 0.6, 0.9, tilt=2)
    for i, x in enumerate((-4.6, -1.6, 1.4, 4.4)):
        model(s, dress, f"Bunting {i}", "Prop_Bunting_01", (x, CR_CEIL - 0.25, 9.6), 0)
    model(s, dress, "Shelf", "Prop_Shelf_01", (CR_HW - 0.3, TIER1, 9.6), -90)
    model(s, dress, "CR plant", "Prop_Plant_02", (-CR_HW + 0.4, TIER1, 10.1), 0)
    model(s, dress, "CR cooler", "Prop_WaterCooler_01", (CR_HW - 0.4, TIER0, 5.2), -90)

    # The mixing desk on the console row, facing the glass.
    con = s.group("Mixing desk", dress)
    cz = 5.75
    s.box("Console body", con, (0, TIER0 + 0.38, cz), (3.0, 0.76, 0.9), (0.2, 0.17, 0.14), rough=0.5)
    s.box("Console surface", con, (0, TIER0 + 0.82, cz + 0.02), (2.9, 0.06, 0.86), (0.12, 0.12, 0.14), rot=(-10, 0, 0), metallic=0.3, rough=0.4)
    rnd = random.Random(31)
    for i in range(24):
        x = -1.3 + i * 0.113
        s.box(f"Fader {i}", con, (x, TIER0 + 0.88, cz - 0.18 + rnd.uniform(-0.08, 0.08)), (0.035, 0.03, 0.05), (0.85, 0.85, 0.85), metallic=0.5)
        for k in range(3):
            s.box(f"Knob {i} {k}", con, (x, TIER0 + 0.9 + k * 0.025, cz + 0.08 + k * 0.1), (0.025, 0.03, 0.025),
                  ((0.8, 0.2, 0.15), (0.2, 0.5, 0.9), (0.9, 0.85, 0.8))[k], shape="Cylinder")
    for i, x in enumerate((-0.9, 0.9)):
        m = s.box(f"Meter screen {i}", con, (x, TIER0 + 1.12, cz + 0.4), (0.7, 0.36, 0.04), (1, 1, 1), shadows=False)
        textured(m, TEX + "ConsoleScreen.png", emissive=1.4)
        s.box(f"Screen back {i}", con, (x, TIER0 + 1.12, cz + 0.43), (0.74, 0.4, 0.03), (0.05, 0.05, 0.06))
    for x in (-1.75, 1.75):
        s.prop("Nearfield", con, "Assets/Models/Venue/Wedge.obj", (x, TIER0 + 0.82, cz + 0.2), 180.0)
    plain_light(s, lamps, "Console glow", (0, TIER0 + 1.5, cz - 0.3), (0.4, 0.95, 0.75), 4.0, 2.5)
    model(s, con, "Engineer chair", "Prop_Chair_02", (0.2, TIER0, 6.45), 180)
    people.person(s, cast, "Engineer riding the faders", "Mother_02", (0.2, TIER0, 6.42), 180, "Faders", seated=True, speed=1.0)
    # The producer at the side, clipboard in hand.
    people.person(s, cast, "Producer with the run sheet", "ShopKeeper_01", (-5.4, TIER0, 5.9), 150, "Writing", speed=0.7,
                  sheet=TEX + "Pledge4.png")

    # The phone bank on the riser: five desks facing the glass.
    beacons = []
    for i, x in enumerate(DESK_X):
        d = s.group(f"Phone desk {i+1}", dress, (x, 0, DESK_Z))
        s.box("Desk top", d, (0, DESK_TOP - 0.02, 0), (1.7, 0.04, 0.75), DESK_TOP_C, rough=0.6)
        s.box("Modesty panel", d, (0, TIER1 + 0.38, -0.33), (1.66, 0.7, 0.03), DESK_BODY, rough=0.7)
        for k in (-0.8, 0.8):
            s.box("Desk end", d, (k, TIER1 + 0.36, 0), (0.04, 0.72, 0.72), DESK_BODY, rough=0.7)
        line = (1, 3, 4, 5, 2)[i]
        s.box("Line card", d, (0, TIER1 + 0.5, -0.35), (0.62, 0.24, 0.01), (0.95, 0.93, 0.86), shadows=False)
        text(s, d, "Line number", (0, TIER1 + 0.5, -0.36), f"LINE {line}", 0.16, (0.7, 0.08, 0.08), lit=True)
        model(s, d, "Desk phone", "Prop_Phone_Desk_01", (-0.25, DESK_TOP, -0.05), 180)
        model(s, d, "Pledge pile", "Prop_Paper_Pile_02", (0.35, DESK_TOP, 0.05), 180 + i * 17)
        model(s, d, "Volunteer chair", "Prop_Chair_02", (0.0, TIER1, 0.75), 180)
        # The call light on a stalk at the back corner (off dome; the lit one is a story prop).
        pole = (0.68, DESK_TOP, 0.22)
        rod(s, d, "Call light stalk", pole, (pole[0], DESK_TOP + 0.5, pole[2]), 0.03, ALU, metallic=0.6)
        s.box("Call light base", d, (pole[0], DESK_TOP + 0.53, pole[2]), (0.16, 0.06, 0.16), (0.08, 0.08, 0.08), shape="Cylinder")
        s.box("Call light (off)", d, (pole[0], DESK_TOP + 0.62, pole[2]), (0.15, 0.17, 0.15), (0.25, 0.06, 0.05), shape="Sphere", rough=0.3)
        beacons.append((x + pole[0], DESK_TOP + 0.62, DESK_Z + pole[2]))
    return beacons


# ---- story ------------------------------------------------------------------------------------

def phone_lit(s, story, flag, beacon, board_lamp, n):
    """One phone line lighting: the call light on its stalk and its lamp on the board over the glass."""
    g = s.story(f"Line {n} lit ({flag})", story, flag, True, 0.35, beacon)
    glow(s, g, "Call light lit", (0, 0, 0), (0.17, 0.19, 0.17), (1.0, 0.18, 0.06), 9.0, "Sphere")
    glow(s, g, "Call light halo", (0, 0, 0), (0.34, 0.34, 0.34), (1.0, 0.3, 0.1), 0.6, "Sphere")
    s.light("Call light", g, (0, 0.12, -0.2), "Point", (1.0, 0.25, 0.08), 7.0, 3.2)
    b = s.story(f"Board lamp {n} lit ({flag})", story, flag, True, 0.3, board_lamp)
    glow(s, b, "Board lamp lit", (0, 0, -0.01), (0.14, 0.14, 0.07), (1.0, 0.55, 0.1), 7.0, "Sphere")


def pledge_slip(s, parent, name, tex, center, w=0.36, h=0.45, tilt=0.0, fade=0.75):
    """A slip taped to the control-room side of the glass, facing the band. It grows from its tape
    (the top edge), so the group's pivot is there."""
    top = (center[0], center[1] + h / 2, center[2])
    return top, (lambda g: sheet(s, g, name, tex, (0, -h / 2, 0), w, h, tilt=tilt, thick=0.004))


def story_props(s, root, cast, beacons, board_lamps):
    story = s.group("Story: the pledge drive", root)
    rnd = random.Random(2470)
    zs = GZ + 0.035
    vx, _, vz = VOCALS
    head = project_to_glass((vx, 1.62, vz))
    # The hand-sized gap: just above and to the band-side of the presenter's head in the wide.
    gap = (head[0] + 0.42, head[1] + 0.2)
    # The grid the slips fill across the lower glass.
    cols = [-WIN_X + 0.18 + k * 0.335 for k in range(int((2 * WIN_X - 0.36) / 0.335) + 1)]
    rows = [WIN_Y0 + 0.24, WIN_Y0 + 0.6, WIN_Y0 + 0.96]
    cells = [(cx, cy) for cy in rows for cx in cols]
    gap_cell = min(cells, key=lambda c: (c[0] - gap[0]) ** 2 + (c[1] - gap[1]) ** 2)
    first_cell = min(cells, key=lambda c: (c[0] - (head[0] - 0.35)) ** 2 + (c[1] - head[1]) ** 2)
    early = sorted((c for c in cells if c not in (gap_cell, first_cell)),
                   key=lambda c: (c[0] - first_cell[0]) ** 2 + (c[1] - first_cell[1]) ** 2)[:3]

    def slip_group(name, flag, cell, k, fade=0.75, w=0.36, h=0.45, tex=None):
        cx, cy = cell
        jx, jy, tilt = rnd.uniform(-0.04, 0.04), rnd.uniform(-0.04, 0.04), rnd.uniform(-7, 7)
        g = s.story(name, story, flag, True, fade, (cx + jx, cy + jy + h / 2, zs + 0.002 * (k % 5)))
        sheet(s, g, "Slip", tex or f"Pledge{rnd.randrange(10)}", (0, -h / 2, 0), w, h, tilt=tilt, thick=0.004)
        s.box("Tape", g, (0, -0.01, 0.003), (0.12, 0.035, 0.002), (0.92, 0.9, 0.8), shadows=False)
        return g

    # 1. first_phone_lit: line 1 rings (desk far left); the first slip goes up level with the presenter.
    phone_lit(s, story, "first_phone_lit", beacons[0], board_lamps[0], 1)
    slip_group("First slip", "first_phone_lit", first_cell, 0, 1.2, tex="Pledge0")

    # 2. second_phone_lit: line 2 at the other end; a line of slips pegged between the two desks,
    # filling in from both ends; two more slips on the glass.
    phone_lit(s, story, "second_phone_lit", beacons[4], board_lamps[1], 2)
    for k, cell in enumerate(early[:2]):
        slip_group(f"Second slip {k}", "second_phone_lit", cell, k + 1, 1.0)
    a = (DESK_X[0] + 0.68, DESK_TOP + 0.45, DESK_Z + 0.22)
    b = (DESK_X[4] + 0.68 - 1.36, DESK_TOP + 0.45, DESK_Z + 0.22)
    line_g = s.story("Pledge line", story, "second_phone_lit", True, 1.5, ((a[0] + b[0]) / 2, a[1], a[2]))
    mid = ((a[0] + b[0]) / 2, a[1], a[2])
    n = 14
    prev = None
    for k in range(n + 1):
        t = k / n
        p = (a[0] + (b[0] - a[0]) * t - mid[0], -0.18 * 4 * t * (1 - t), 0)
        if prev:
            rod(s, line_g, f"String {k}", prev, p, 0.008, (0.9, 0.9, 0.85), shadows=False)
        prev = p
    for k in range(n + 1):
        t = k / n
        if 0.3 < t < 0.7:
            continue        # filling from both ends: a gap in the middle until it's full
        p = (a[0] + (b[0] - a[0]) * t - mid[0], -0.18 * 4 * t * (1 - t) - 0.14, 0)
        sheet(s, line_g, f"Pegged slip {k}", f"Pledge{(k * 3) % 10}", p, 0.2, 0.25, tilt=rnd.uniform(-10, 10), thick=0.004)
        s.box(f"Peg {k}", line_g, (p[0], p[1] + 0.13, p[2]), (0.02, 0.05, 0.02), (0.75, 0.55, 0.3))

    # 3. pledges_cover_glass: the lower half of the glass disappears under slips (the gap stays
    # open by the presenter), and the pegged line fills in. Volunteers 1 and 2 are on their feet.
    taken = {first_cell, gap_cell, *early[:2]}
    rest = [c for c in cells if c not in taken]
    for k, cell in enumerate(rest):
        slip_group(f"Cover slip {k}", "pledges_cover_glass", cell, k, 0.4 + 0.035 * k)
    fill = s.story("Pledge line fills", story, "pledges_cover_glass", True, 1.2, mid)
    for k in range(n + 1):
        t = k / n
        if not 0.3 < t < 0.7:
            continue
        p = (a[0] + (b[0] - a[0]) * t - mid[0], -0.18 * 4 * t * (1 - t) - 0.14, 0)
        sheet(s, fill, f"Pegged slip {k}", f"Pledge{(k * 7) % 10}", p, 0.2, 0.25, tilt=rnd.uniform(-10, 10), thick=0.004)

    # 4. all_phones_lit: lines 3-5 light; slips climb the outer glass to the top.
    for line, desk in ((3, 1), (4, 2), (5, 3)):
        phone_lit(s, story, "all_phones_lit", beacons[desk], board_lamps[line - 1], line)
    upper_rows = [WIN_Y0 + 1.32, WIN_Y0 + 1.68]
    k = 0
    for cy in upper_rows:
        for cx in cols:
            if abs(cx) < 3.7 and not (gap_cell[0] - 0.9 < cx < gap_cell[0] + 0.5 and cy < WIN_Y0 + 1.5):
                continue
            slip_group(f"Climbing slip {k}", "all_phones_lit", (cx, cy), k, 0.5 + 0.05 * k)
            k += 1

    # 5. rent_paid: the RENT PAID sheet fills the gap; the banner goes up over the glass; the
    # rent-o-meter tops out (see rent_meter); balloons in the control room.
    slip_group("RENT PAID sheet", "rent_paid", gap_cell, 3, 0.6, w=0.52, h=0.42, tex="RentSheet")
    ban = s.story("RENT PAID banner", story, "rent_paid", True, 1.4, (3.1, CEIL - 0.05, GZ - 0.35))
    sheet(s, ban, "Banner", "RentBanner", (0, -0.62, 0), 3.9, 1.22, glow=0.35)
    for x in (-1.9, 1.9):
        rod(s, ban, "Banner string", (x, -0.02, 0), (x * 0.98, 0.04, 0.1), 0.01, (0.9, 0.9, 0.85))
    s.light("Banner light", ban, (0, -0.5, -1.2), "Point", (1.0, 0.8, 0.4), 14.0, 4.0)
    bal = s.story("Balloons", story, "rent_paid", True, 2.0, (0, TIER1, 9.3))
    for i in range(7):
        x = -5 + i * 1.6 + rnd.uniform(-0.3, 0.3)
        model(s, bal, f"Balloon {i}", "Prop_Balloon_01", (x, rnd.uniform(1.6, 2.2), rnd.uniform(-0.4, 0.5)), rnd.uniform(0, 360))

    volunteers(s, cast)
    return gap_cell


def rent_meter(s, dress):
    """The rent-o-meter on an easel at the right of the glass; a red segment per flag."""
    pos, yaw = (4.55, 0.0, 3.0), 29.0
    e = s.entity("Rent-o-meter easel", dress, pos, (0, yaw, 0))
    for k in (-0.36, 0.36):
        rod(s, e, "Easel leg", (k, 0, -0.15), (k * 0.5, 2.55, 0.02), 0.04, (0.45, 0.32, 0.2))
    rod(s, e, "Easel back leg", (0, 0, 0.55), (0, 2.4, 0.06), 0.04, (0.45, 0.32, 0.2))
    s.box("Easel ledge", e, (0, 0.98, -0.1), (0.95, 0.04, 0.12), (0.45, 0.32, 0.2))
    W, H, CY = 0.9, 1.8, 1.9
    board = s.entity("Board", e, (0, CY, -0.06), (-6, 0, 0))
    sheet(s, board, "Rent-o-meter", "RentMeter", (0, 0, 0), W, H)
    u = lambda px: (px / 512 - 0.5) * W
    v = lambda py: (0.5 - py / 1024) * H
    tube_x, tube_w = u(246), 0.1
    glow(s, board, "Bulb", (tube_x, v(930), -0.008), (0.12, 0.12, 0.01), (0.9, 0.08, 0.06), 0.6, "Cylinder", rot=(90, 0, 0))
    seg = (v(160) - v(860)) / 5
    for i, flag in enumerate(FLAGS):
        y0 = v(860) + i * seg
        g = s.story(f"Rent-o-meter {i+1} ({flag})", board, flag, True, 1.5, (tube_x, y0, -0.008))
        colour = (1.0, 0.75, 0.1) if flag == "rent_paid" else (0.9, 0.08, 0.06)
        glow(s, g, "Fill", (0, seg / 2, 0), (tube_w * 0.8, seg + 0.01, 0.01), colour, 0.6 if i < 4 else 2.5)
    pk = s.story("Rent-o-meter glow (rent_paid)", board, "rent_paid", True, 1.0, (0, 0, -0.4))
    s.light("Goal glow", pk, (0, 0.3, 0), "Point", (1.0, 0.85, 0.3), 10.0, 2.5)
    text(s, pk, "MADE IT", (0, v(150) + 0.16, -0.01), "WE MADE IT!", 0.13, (0.1, 0.5, 0.15))


def volunteers(s, cast):
    """Five phone volunteers, each arriving with their line. Lines 1 and 2 get up and bounce when the
    glass fills; everyone jumps when the rent's paid."""
    vol = s.group("Volunteers on the phones", cast)
    seat_z = DESK_Z + 0.72
    stand_z = DESK_Z + 0.55
    plan = [
        # desk, flag, who, seated clip, arm_l, arm_r, handset
        (0, "first_phone_lit", "Son_01", "OnThePhone", 67, 93, True),
        (4, "second_phone_lit", "Mother_02", "OnThePhone", 66, 93, True),
        (1, "all_phones_lit", "Son_01", "Writing", 67, 61, False),
        (2, "all_phones_lit", "Daughter_01", "OnThePhone", 62, 76, True),
        (3, "all_phones_lit", "Mother_02", "OnThePhone", 66, 93, True),
    ]
    for n, (desk, flag, who, clip, al, ar, hs) in enumerate(plan):
        x = DESK_X[desk]
        g = s.story(f"Volunteer {n+1} ({flag})", vol, flag, True, 0.6, (x, TIER1, seat_z))
        early = n < 2
        sit_until = "pledges_cover_glass" if early else "rent_paid"
        sit = s.story(f"Seated until {sit_until}", g, sit_until, False, 0.4, (0, 0, 0))
        people.person(s, sit, "On the line", who, (0, 0, 0), 180, clip, seated=True, arm_l=al, arm_r=ar, handset=hs,
                      speed=0.9 + 0.07 * n, sheet=None)
        if early:
            up = s.story("On their feet", g, "pledges_cover_glass", True, 0.4, (0, 0, stand_z - seat_z))
            bounce = s.story("Bouncing", up, "rent_paid", False, 0.3, (0, 0, 0))
            people.person(s, bounce, "Bouncing to the bassline", who, (0, 0, 0), 180, "Bounce", speed=1.0 + 0.04 * n)
        jump = s.story("Jumping (rent_paid)", g, "rent_paid", True, 0.3, (0, 0, stand_z - seat_z))
        people.person(s, jump, "RENT PAID", who, (0, 0, 0), 180, "Jump", speed=0.95 + 0.06 * n)


# ---- lights -----------------------------------------------------------------------------------

def lighting(s, lamps):
    # A cool, soft key from above (the ceilings don't block it), the one shadowed light.
    s.light("Night key", lamps, (0, 12, -2), "Directional", (0.72, 0.82, 1.0), 0.9, 100, rot=(62, 12, 0), shadows=True)
    # Live-room fluorescents: two rows of troffers, one tube dead.
    for i, (x, z) in enumerate(((-3.0, -2.2), (0.0, -2.2), (3.0, -2.2), (-3.0, 1.3), (0.0, 1.3), (3.0, 1.3))):
        s.box(f"Troffer {i}", lamps, (x, CEIL - 0.01, z), (0.62, 0.03, 1.22), (0.6, 0.6, 0.6), rough=0.4, shadows=False)
        dead = i == 2
        glow(s, lamps, f"Tube {i}", (x, CEIL - 0.03, z), (0.56, 0.02, 1.14), (0.35, 0.38, 0.4) if dead else FLUO, 0.05 if dead else 1.8)
        if not dead:
            plain_light(s, lamps, f"Fluorescent {i}", (x, CEIL - 0.3, z), FLUO, 13.0, 6.5)
    # Wall washes so the foam and the show posters read at night.
    for side in (-1, 1):
        for z in (-2.4, 0.9):
            plain_light(s, lamps, f"Wall wash {side} {z}", (side * (HW - 1.2), 2.9, z), (1.0, 0.78, 0.55), 9.0, 4.5)
    # The show's lights: a small studio rig.
    def spot(name, pos, aim, colour, power, reach, inner, outer, role, group=0):
        s.light(name, lamps, pos, "Spot", colour, power, reach, rot=look_rotation(pos, aim), inner=inner, outer=outer,
                show=role, group=group)
    spot("Wash amber", (-2.4, 3.45, -0.6), (-1.2, 1.0, 2.8), (1.0, 0.62, 0.3), 380, 9, 22, 46, "Wash", 0)
    spot("Wash magenta", (0.9, 3.45, -1.0), (0.9, 1.0, 3.0), (0.9, 0.25, 0.7), 380, 9, 22, 46, "Wash", 1)
    spot("Wash teal", (3.6, 3.45, -0.6), (1.6, 1.0, 2.8), (0.25, 0.75, 0.9), 380, 9, 22, 46, "Wash", 2)
    spot("Back wash", (-0.6, 3.45, 4.2), (-0.6, 0.6, 1.2), (0.9, 0.3, 0.25), 300, 7, 26, 50, "Wash", 1)
    spot("Follow drummer", (3.0, 3.45, -1.6), (DRUMMER[0], 1.2, DRUMMER[2]), (1.0, 0.92, 0.82), 420, 10, 9, 18, "Spot", 0)
    spot("Follow voice", (-0.8, 3.45, -1.8), (VOCALS[0], 1.5, VOCALS[2]), (1.0, 0.9, 0.8), 380, 10, 8, 16, "Spot", 1)
    spot("Floor beam L", (-5.5, 0.2, 4.0), (-3.5, 3.6, 0.5), (0.6, 0.2, 1.0), 260, 8, 6, 14, "Beam", 0)
    spot("Floor beam R", (5.5, 0.2, 4.0), (3.5, 3.6, 0.5), (1.0, 0.3, 0.2), 260, 8, 6, 14, "Beam", 1)
    spot("Blinder L", (-3.5, 3.4, 4.25), (-2.0, 0.5, -1.0), (1.0, 0.85, 0.6), 500, 9, 25, 55, "Blinder", 0)
    spot("Blinder R", (3.5, 3.4, 4.25), (2.0, 0.5, -1.0), (1.0, 0.85, 0.6), 500, 9, 25, 55, "Blinder", 1)
    s.light("Strobe", lamps, (0, 3.4, 0.5), "Point", (1, 1, 1), 300, 9, show="Strobe", group=0)


# ---- markers and cameras ----------------------------------------------------------------------

def markers(s, marks, gap_cell):
    s.info(marks, "The Pledge Drive Night Shift", "Drumsmith", outdoor=False, room_back=LR_BACK, room_ceiling=CEIL,
           half_width=HW, desk_z=-4.2, ambient=(0.025, 0.028, 0.04), fog_color=(0.03, 0.03, 0.04), haze=0.45)
    s.spot(marks, "Drummer", DRUMMER)
    s.spot(marks, "Vocals", VOCALS, -14.0)
    # The volunteers who aren't on a phone: on the riser at the back, facing the glass.
    s.crowd("Volunteers behind the glass", marks, (0, TIER1, 9.75), 9.6, 1.3, 9, 0.7, 180.0)
    cams = s.group("Cameras", marks)
    gx, gy = gap_cell
    shots = [
        ("wide", "Wide", WIDE_EYE, WIDE_AIM, 58),
        ("crane", "Crane", (4.6, 3.3, -3.4), (-0.6, 1.5, 3.8), 56),
        ("desk", "Desk", (-1.4, 1.85, -4.3), (0.3, 1.7, 4.0), 34),
        ("sticks", "Close", (2.5, 1.65, 0.6), (DRUMMER[0], 1.05, DRUMMER[2] - 0.6), 48),
        ("first-slip", "Custom", (-0.9, 1.75, -0.3), (VOCALS[0] - 0.5, 1.65, GZ), 46),
        ("gap", "Custom", (-1.3, 1.85, -1.4), (gx, gy, GZ), 38),
        ("phone-bank", "Custom", (2.6, 2.3, 1.6), (-0.8, 2.0, DESK_Z), 50),
        ("rent-o-meter", "Custom", (2.4, 1.75, 0.0), (4.55, 1.8, 3.0), 50),
    ]
    for tag, kind, eye, aim, fov in shots:
        s.camera_spot(f"Camera {tag}", cams, eye, aim, kind, fov, tag)
    walk = [((-4.9, 1.65, -3.9), (-3.2, 1.6, -1.0), 70), ((-4.2, 1.68, -3.2), (-1.8, 1.6, 0.6), 68),
            ((-3.2, 1.72, -2.6), (-1.0, 1.7, 2.4), 66), ((-2.0, 1.78, -2.1), (-0.3, 1.8, 4.0), 64),
            ((-0.8, 1.85, -1.8), (0.4, 1.9, 4.6), 62)]
    for i, (eye, aim, fov) in enumerate(walk):
        s.camera_spot(f"Arrival {i+1:02}", cams, eye, aim, "Custom", fov, f"arrival/{i+1:02}")


def build():
    s = Scene("story-radio-station-s07")
    root = s.group("The Pledge Drive Night Shift")
    geo = s.group("Rooms", root)
    dress = s.group("Dressing", root)
    lamps = s.group("Lights", root)
    cast = s.group("Volunteers", root)
    marks = s.group("Venue markers", root)
    live_room(s, geo, dress)
    kit_corner(s, dress)
    presenter_corner(s, dress, lamps)
    board_lamps = glass_wall(s, geo, dress, lamps)
    beacons = control_room(s, geo, dress, lamps, cast)
    lighting(s, lamps)
    gap = story_props(s, root, cast, beacons, board_lamps)
    rent_meter(s, dress)
    markers(s, marks, gap)
    return s


def make_sound(folder):
    """Room tone: the building's air handling, a faint fluorescent buzz. 24 s, loops."""
    path = os.path.join(folder, "RoomTone.wav")
    graph = ("anoisesrc=d=24:c=brown:a=0.35:r=22050:s=7,lowpass=f=420[a];"
             "sine=f=120:d=24:r=22050,volume=0.018[b];anoisesrc=d=24:c=white:a=0.01:r=22050:s=9,highpass=f=5000[c];"
             "[a][b][c]amix=inputs=3:normalize=0,afade=t=in:d=0.5,afade=t=out:st=23.5:d=0.5[out]")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-filter_complex", graph, "-map", "[out]",
           "-ac", "1", "-ar", "22050", "-c:a", "pcm_s16le", "-fflags", "+bitexact", "-flags:a", "+bitexact", path]
    subprocess.run(cmd, check=True)


def main():
    folder = os.path.join(repo_root(), "Assets", "Venues", ID)
    if "--textures" in sys.argv:
        import story_radio_station_textures
        story_radio_station_textures.make_all()
    if "--sound" in sys.argv or not os.path.exists(os.path.join(folder, "RoomTone.wav")):
        make_sound(folder)
    people.write_clips(repo_root())
    scene = build()
    scene.write(os.path.join(folder, ID + ".lvl"))
    preview = "Preview.jpg" if os.path.exists(os.path.join(folder, "Preview.jpg")) else None
    write_venue_json(folder, "The Pledge Drive Night Shift", ID + ".lvl", preview=preview, ambience="RoomTone.wav")
    print(f"{len(scene.entities)} entities in {folder}")


if __name__ == "__main__":
    main()
