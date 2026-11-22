#!/usr/bin/env python3
"""Builds Assets/Venues/StorySubway/: story set 02, "The Last Train Busking Pitch" (s02-busking).

    python3 Tools/Venues/make_story_subway.py

Bellwoods station after midnight: a tiled platform between the turnstiles (crowd's left) and the
stairs up to the street (crowd's right), a pillar with the licensed busking-pitch plate, the
departure board, and two tracks behind the drummer where two lit carriages wait and leave. The
drummer busks alone on the kit with an orange bucket and a practice pad on upturned crates and an
open case for tips. Story flags (Design/Story-Mode-Setlists.json):

  commuter_at_pillar  the mustard-scarf commuter stops under the board, mug in hand
  first_train_gone    carriage A on the near track pulls out into the right tunnel; board 1 -> 2
  family_at_pitch     two kids dance by the bucket; their mum watches from the stairs
  second_train_gone   carriage B on the far track leaves to the left, the BELLWOODS wall shows,
                      the signal turns red, board 2 -> 3, mum comes down to clap by the bucket
  tip_in_case         the drilled loonie and the cafe transfer in the case, in a warm pool of light

Deterministic: rerunning gives the same bytes (textures need ImageMagick 7; without it the PNGs
on disk are kept).
"""
import math
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from venuegen import Scene, look_rotation, repo_root, write_venue_json, vec, _r  # noqa: E402
import story_subway_textures as textures  # noqa: E402
import story_subway_people as people  # noqa: E402

ID = "StorySubway"
TEX = "Assets/Venues/StorySubway/Textures/"
VM = "Assets/Models/Venue/"

# Palette
CEIL = (0.11, 0.115, 0.12)
CONCRETE = (0.2, 0.2, 0.2)
STEEL = (0.5, 0.52, 0.55)
DARK = (0.03, 0.03, 0.035)
TEAL = (0.06, 0.3, 0.3)
MUSTARD = (0.85, 0.58, 0.08)
FLUO = (0.82, 1.0, 0.9)
SODIUM = (1.0, 0.55, 0.16)
WARM = (1.0, 0.86, 0.62)

# Plan (venue metres). Platform floor y 0 from z -13 to the edge at z 4.6; tracks beyond.
X0, X1 = -11.0, 11.0
ZBACK, ZEDGE, ZFAR = -13.0, 4.6, 14.0
CEIL_Y = 4.6
BED_Y = -1.3
NEAR_Z, FAR_Z = 6.5, 10.7         # track centres
STAIR_Z0, STAIR_Z1 = -3.6, -0.4   # the stair's width (along z)
STAIR_X0, STEP_RUN, STEP_RISE, STEPS = 4.6, 0.31, 0.18, 21


# ---- helpers ---------------------------------------------------------------------------------

def material(e):
    for comp in e.components:
        if comp.get("Type") == "Mesh":
            return comp["Material"]
    raise ValueError(e.name)


def textured(e, name, tile=(1.0, 1.0), emissive=None, emissive_intensity=1.0, tint=(1, 1, 1), glow_map=None):
    m = material(e)
    m["DiffuseColor"] = vec(tint)
    m["Textures"] = {"Diffuse": {"Path": TEX + name + ".png"}}
    if emissive is not None:
        m["Textures"]["Emissive"] = {"Path": TEX + (glow_map or name) + ".png"}
        m["EmissiveColor"] = vec(emissive)
        m["EmissiveIntensity"] = _r(emissive_intensity)
    m["Tiling"] = [_r(tile[0]), _r(-tile[1])]
    m["Offset"] = [0.0, _r(tile[1])]
    return e


def panel(s, parent, name, tex, center, width, height, facing="-z", thick=0.02, glow=None, glow_i=1.0, tilt=0.0,
          glow_map=None, rough=0.8):
    """A flat picture: facing is the way it looks ('-z' toward the crowd, '+x' off the left wall)."""
    if facing in ("+x", "-x"):
        size, rot = (thick, height, width), (tilt, 0, 0)
    else:
        size, rot = (width, height, thick), (0, 0, tilt)
    e = s.box(name, parent, center, size, (1, 1, 1), rot=rot, rough=rough, shadows=False)
    return textured(e, tex, emissive=glow, emissive_intensity=glow_i, glow_map=glow_map)


def glow_box(s, parent, name, center, size, color, power, rot=(0, 0, 0)):
    return s.box(name, parent, center, size, color, rot=rot, emissive=color, emissive_intensity=power, shadows=False, rough=0.6)


def plain_light(s, parent, name, pos, color, power, reach, kind="Point", rot=(0, 0, 0), inner=30, outer=60, **extra):
    e = s.light(name, parent, pos, kind, color, power, reach, rot=rot, inner=inner, outer=outer)
    e.components[-1].update({k: _r(v) for k, v in extra.items()})
    return e


def tiled_wall(s, parent, name, x0, x1, y0, y1, z0, z1, axis):
    """A wall faced in cream tile (1.2 m repeat) with the teal band at dado height."""
    e = s.slab(name, parent, x0, x1, y0, y1, z0, z1, (1, 1, 1), rough=0.35, shadows=False)
    along = (z1 - z0) if axis == "x" else (x1 - x0)
    textured(e, "WallTile", (along / 1.2, (y1 - y0) / 1.2))
    return e


# ---- the room --------------------------------------------------------------------------------

def station(s, root):
    g = s.group("Bellwoods station", root)
    floor = s.slab("Platform floor", g, X0, X1, -0.3, 0.0, ZBACK, ZEDGE, (1, 1, 1), rough=0.28, shadows=False)
    textured(floor, "Floor", ((X1 - X0) / 2, (ZEDGE - ZBACK) / 2))
    edge = s.slab("Tactile edge", g, X0, X1, 0.0, 0.012, ZEDGE - 0.62, ZEDGE - 0.02, (1, 1, 1), rough=0.6, shadows=False)
    textured(edge, "EdgeStrip", ((X1 - X0) / 0.5, 1.2))
    s.slab("Edge coping", g, X0, X1, -0.06, 0.016, ZEDGE - 0.02, ZEDGE + 0.12, (0.6, 0.58, 0.52), rough=0.5)
    s.slab("Platform face", g, X0, X1, BED_Y, -0.06, ZEDGE + 0.02, ZEDGE + 0.12, (0.09, 0.09, 0.09), shadows=False)

    # Track bed, rails and sleepers.
    bed = s.slab("Track bed", g, X0 - 3, X1 + 3, BED_Y - 0.2, BED_Y, ZEDGE, ZFAR, (0.5, 0.5, 0.5), shadows=False)
    textured(bed, "Tunnel", (14, 5))
    for tz in (NEAR_Z, FAR_Z):
        for side in (-0.72, 0.72):
            s.slab("Rail", g, X0 - 3, X1 + 3, BED_Y + 0.1, BED_Y + 0.24, tz + side - 0.04, tz + side + 0.04, (0.42, 0.4, 0.38),
                   metallic=0.8, rough=0.35, shadows=False)
        s.slab("Third rail cover", g, X0 - 3, X1 + 3, BED_Y, BED_Y + 0.34, tz + 1.28, tz + 1.5, (0.62, 0.5, 0.12), shadows=False)
        x = X0 - 2.6
        while x < X1 + 3:
            s.slab("Sleeper", g, x, x + 0.24, BED_Y, BED_Y + 0.1, tz - 1.25, tz + 1.25, (0.13, 0.11, 0.1), shadows=False)
            x += 0.75

    # Trackside wall, with the name band and the posters between the trains and the vault.
    tiled_wall(s, g, "Trackside wall", X0 - 3, X1 + 3, BED_Y, 6.4, ZFAR, ZFAR + 0.3, "z")
    name = s.box("BELLWOODS name band", g, (0, 2.35, ZFAR - 0.03), (12.8, 2.4, 0.04), (1, 1, 1), rough=0.35, shadows=False)
    textured(name, "NameWall")
    for x0, x1 in ((X0 - 3, -6.4), (6.4, X1 + 3)):
        band = s.slab("Teal band", g, x0, x1, 1.75, 2.95, ZFAR - 0.05, ZFAR - 0.01, (1, 1, 1), rough=0.35, shadows=False)
        textured(band, "BandTile", ((x1 - x0) / 1.2, 1))
    for i, (tex, x, w, h) in enumerate((("AdNightLine", -8.4, 1.3, 1.95), ("LineMap", 8.6, 3.0, 1.12))):
        s.box("Poster frame", g, (x, 1.0 + h / 2 + 3.05 - 1.0, ZFAR - 0.06), (w + 0.12, h + 0.12, 0.03), (0.08, 0.08, 0.09))
        panel(s, g, "Poster " + tex, tex, (x, 1.0 + h / 2 + 3.05 - 1.0, ZFAR - 0.08), w, h)
    # Vault over the tracks.
    s.slab("Track vault", g, X0 - 3, X1 + 3, 6.4, 6.7, ZEDGE, ZFAR + 0.3, CEIL, shadows=False)
    s.slab("Vault lip", g, X0, X1, CEIL_Y - 0.5, 6.4, ZEDGE - 0.1, ZEDGE + 0.25, (0.16, 0.16, 0.17), shadows=False)
    sign = s.box("Lip band", g, (0, CEIL_Y - 0.25, ZEDGE - 0.12), (X1 - X0, 0.42, 0.02), (1, 1, 1), shadows=False, rough=0.35)
    textured(sign, "BandTile", ((X1 - X0) / 1.2, 1))

    # Side walls: tiled, with the tunnel portals over the tracks.
    for sx, side in ((X0, -1), (X1, 1)):
        xa, xb = (sx - 0.3, sx) if side < 0 else (sx, sx + 0.3)
        tiled_wall(s, g, "Side wall", xa, xb, 0, CEIL_Y, ZBACK, ZEDGE, "x")
        b = s.slab("Side band", g, xa - 0.02 * side, xb - 0.02 * side, 1.05, 1.47, ZBACK, ZEDGE, (1, 1, 1), shadows=False, rough=0.35)
        textured(b, "BandTile", ((ZEDGE - ZBACK) / 1.2, 1))
        # Portal: a lintel over the tracks, a pier between them, and the tunnel's dark beyond.
        lx = (sx, sx + 0.3) if side > 0 else (sx - 0.3, sx)
        s.slab("Portal lintel", g, lx[0], lx[1], 3.7, 6.4, ZEDGE, ZFAR, (0.14, 0.14, 0.15), shadows=False)
        s.slab("Portal pier", g, lx[0], lx[1], BED_Y, 3.7, (NEAR_Z + FAR_Z) / 2 - 0.3, (NEAR_Z + FAR_Z) / 2 + 0.3,
               (0.16, 0.16, 0.17), shadows=False)
        tx = (sx, sx + 4.2) if side > 0 else (sx - 4.2, sx)
        s.slab("Tunnel roof", g, tx[0], tx[1], 3.7, 3.9, ZEDGE, ZFAR, DARK, shadows=False)
        cap = (sx + 4.0, sx + 4.3) if side > 0 else (sx - 4.3, sx - 4.0)
        s.slab("Tunnel dark", g, cap[0], cap[1], BED_Y - 0.2, 3.9, ZEDGE, ZFAR, DARK, shadows=False)
        s.slab("Tunnel wall", g, tx[0], tx[1], BED_Y - 0.2, 3.9, ZEDGE - 0.3, ZEDGE, DARK, shadows=False)
    tiled_wall(s, g, "Back wall", X0, X1, 0, CEIL_Y, ZBACK - 0.3, ZBACK, "z")

    # Ceiling, open over the stairwell.
    sx0 = STAIR_X0 + 9 * STEP_RUN
    s.slab("Ceiling", g, X0, X1, CEIL_Y, CEIL_Y + 0.25, ZBACK, STAIR_Z0, CEIL, shadows=False)
    s.slab("Ceiling", g, X0, X1, CEIL_Y, CEIL_Y + 0.25, STAIR_Z1, ZEDGE, CEIL, shadows=False)
    s.slab("Ceiling", g, X0, sx0, CEIL_Y, CEIL_Y + 0.25, STAIR_Z0, STAIR_Z1, CEIL, shadows=False)
    for z in (-10.5, -6.5, -2.5, 1.5):
        s.slab("Ceiling beam", g, X0, X1, CEIL_Y - 0.32, CEIL_Y, z - 0.18, z + 0.18, (0.15, 0.15, 0.16), shadows=False)
    return g


def pillar(s, parent, name, x, z, sign=None):
    g = s.group(name, parent, (x, 0, z))
    e = s.slab("Pillar tile", g, -0.38, 0.38, 0, CEIL_Y, -0.38, 0.38, (1, 1, 1), rough=0.32)
    textured(e, "WallTile", (0.65, CEIL_Y / 1.2))
    b = s.slab("Pillar band", g, -0.4, 0.4, 1.05, 1.47, -0.4, 0.4, (1, 1, 1), rough=0.35, shadows=False)
    textured(b, "BandTile", (0.7, 1))
    s.slab("Pillar foot", g, -0.41, 0.41, 0, 0.14, -0.41, 0.41, (0.1, 0.1, 0.1))
    if sign:
        panel(s, g, "Pitch plate", sign, (0, 2.05, -0.395), 0.56, 0.56, rough=0.3)
    return g


def stairs(s, parent):
    """Twenty-one steps from the platform up to the street, rising toward the crowd's right."""
    g = s.group("Stairs to the street", parent)
    for i in range(STEPS):
        x0 = STAIR_X0 + i * STEP_RUN
        top = (i + 1) * STEP_RISE
        s.slab(f"Step {i + 1}", g, x0, X1 + 0.3, 0, top, STAIR_Z0, STAIR_Z1, (0.36, 0.35, 0.33), rough=0.7, shadows=False)
        s.slab("Nosing", g, x0, x0 + 0.05, top - 0.01, top + 0.006, STAIR_Z0, STAIR_Z1, (0.82, 0.62, 0.1), shadows=False)
    # Stringer wall on the crowd side, tiled, and the steel handrail on posts.
    top_x = STAIR_X0 + STEPS * STEP_RUN
    for i in range(0, STEPS + 1, 4):
        x = STAIR_X0 + i * STEP_RUN + 0.1
        y = (i + 1) * STEP_RISE
        s.box("Rail post", g, (x, y + 0.45, STAIR_Z0 + 0.06), (0.05, 0.9, 0.05), STEEL, metallic=0.8, rough=0.3)
    run = STEPS * STEP_RUN
    rise = STEPS * STEP_RISE
    length = math.hypot(run, rise)
    ang = math.degrees(math.atan2(rise, run))
    s.box("Handrail bar", g, (STAIR_X0 + run / 2 + 0.1, rise / 2 + 1.05, STAIR_Z0 + 0.06), (length, 0.06, 0.06), STEEL,
          rot=(0, 0, ang), metallic=0.8, rough=0.3)
    side = s.slab("Stair side wall", g, STAIR_X0 + 2.6, X1, CEIL_Y - 0.9, CEIL_Y, STAIR_Z0 - 0.02, STAIR_Z0 + 0.02, (1, 1, 1),
                  shadows=False, rough=0.35)
    textured(side, "BandTile", (5, 1))
    # The stairwell above: walls up to the street, lit sodium orange.
    sx0 = STAIR_X0 + 9 * STEP_RUN
    s.slab("Stairwell wall", g, sx0, X1 + 2.5, CEIL_Y, 9.5, STAIR_Z0 - 0.3, STAIR_Z0, (0.3, 0.28, 0.25), shadows=False)
    s.slab("Stairwell wall", g, sx0, X1 + 2.5, CEIL_Y, 9.5, STAIR_Z1, STAIR_Z1 + 0.3, (0.3, 0.28, 0.25), shadows=False)
    s.slab("Stairwell head", g, sx0 - 0.3, sx0, CEIL_Y, 9.5, STAIR_Z0, STAIR_Z1, (0.3, 0.28, 0.25), shadows=False)
    s.slab("Upper steps", g, top_x, X1 + 2.5, 0, rise + 0.9, STAIR_Z0, STAIR_Z1, (0.3, 0.29, 0.27), shadows=False)
    s.slab("Street landing", g, top_x, X1 + 2.5, rise + 0.9, rise + 1.0, STAIR_Z0, STAIR_Z1, (0.24, 0.23, 0.22), shadows=False)
    s.slab("Stairwell roof", g, sx0 - 0.3, X1 + 2.5, 9.5, 9.7, STAIR_Z0 - 0.3, STAIR_Z1 + 0.3, (0.05, 0.05, 0.06), shadows=False)
    glow_box(s, g, "Street lamp glass", (X1 + 0.6, 7.6, (STAIR_Z0 + STAIR_Z1) / 2), (0.5, 0.18, 0.5), SODIUM, 5.0)
    s.box("EXIT sign", g, (sx0 + 0.6, CEIL_Y - 0.25, (STAIR_Z0 + STAIR_Z1) / 2), (0.05, 0.28, 0.9), (0.05, 0.4, 0.15),
          emissive=(0.1, 1.0, 0.35), emissive_intensity=2.2, shadows=False)
    return g


def turnstiles(s, parent):
    g = s.group("Turnstiles and the booth", parent)
    z = -4.6
    for i, x in enumerate((-10.2, -9.0, -7.8, -6.6, -5.4)):
        s.box("Turnstile cabinet", g, (x, 0.5, z), (0.28, 1.0, 1.1), (0.55, 0.56, 0.58), metallic=0.7, rough=0.35)
        s.box("Cabinet top", g, (x, 1.01, z), (0.3, 0.03, 1.12), (0.12, 0.12, 0.13))
        glow_box(s, g, "Go arrow", (x + 0.15, 1.04, z - 0.42), (0.02, 0.06, 0.12), (0.2, 1.0, 0.3) if i % 2 == 0 else (1.0, 0.2, 0.12), 2.5)
        if i < 4:
            for k, a in enumerate((0, 120, 240)):
                s.box("Tripod arm", g, (x + 0.42, 0.85, z), (0.5, 0.04, 0.04), STEEL, rot=(a, 0, -20), metallic=0.8, rough=0.3)
    s.slab("Fare line", g, -11, -4.9, 0.0, 0.006, z - 0.65, z - 0.55, (0.8, 0.6, 0.1), shadows=False)
    # The collector's booth, empty, its lamp left on.
    b = s.group("Collector's booth", g, (-9.6, 0, -8.6))
    s.slab("Booth base", b, -1.2, 1.2, 0, 1.0, -0.9, 0.9, (0.3, 0.32, 0.33))
    s.slab("Booth roof", b, -1.25, 1.25, 2.3, 2.45, -0.95, 0.95, (0.25, 0.27, 0.28))
    for xx in (-1.2, 1.15):
        s.slab("Booth post", b, xx, xx + 0.05, 1.0, 2.3, -0.9, 0.9, (0.2, 0.2, 0.22))
    glow_box(s, b, "Booth window", (0, 1.65, 0.0), (2.3, 1.25, 1.75), (0.55, 0.5, 0.36), 0.35)
    glow_box(s, b, "Booth lamp", (0, 2.2, 0), (0.35, 0.05, 0.12), WARM, 4.0)
    return g


def dressing(s, parent):
    """Benches, a bin, a vending machine, posters on the side walls, the clock."""
    g = s.group("Platform furniture", parent)
    for x in (-8.8, 7.6):
        s.box("Bench seat", g, (x, 0.45, 2.7), (2.2, 0.06, 0.45), (0.5, 0.32, 0.16), rough=0.6)
        s.box("Bench back", g, (x, 0.8, 2.95), (2.2, 0.4, 0.05), (0.5, 0.32, 0.16), rough=0.6, rot=(-12, 0, 0))
        for dx in (-0.9, 0.9):
            s.box("Bench leg", g, (x + dx, 0.22, 2.75), (0.06, 0.44, 0.4), (0.15, 0.15, 0.16), metallic=0.6)
    s.box("Bin", g, (-6.2, 0.45, 2.9), (0.55, 0.9, 0.55), (0.2, 0.22, 0.22), shape="Cylinder", metallic=0.5, rough=0.5)
    s.box("Bin lid", g, (-6.2, 0.92, 2.9), (0.6, 0.06, 0.6), (0.08, 0.08, 0.09), shape="Cylinder")
    vend = s.group("Vending machine", g, (-10.45, 0, -1.6))
    s.box("Vending body", vend, (0, 0.95, 0), (0.8, 1.9, 1.0), (0.55, 0.08, 0.1), rough=0.5)
    glow_box(s, vend, "Vending front", (0.41, 1.15, -0.12), (0.02, 1.25, 0.62), (1.0, 0.86, 0.7), 1.6)
    glow_box(s, vend, "Vending slot", (0.41, 1.2, 0.33), (0.02, 0.3, 0.12), (0.4, 0.8, 1.0), 2.0)
    # Side-wall posters.
    panel(s, g, "Poster gig", "AdGig", (X0 + 0.02, 2.1, -3.2), 1.0, 1.5, facing="+x")
    panel(s, g, "Poster night line", "AdNightLine", (X0 + 0.02, 2.1, 0.8), 1.0, 1.5, facing="+x")
    panel(s, g, "Line map", "LineMap", (X1 - 0.02, 2.4, 2.4), 2.4, 0.9, facing="-x")
    # The clock on the vault lip.
    s.box("Clock", g, (6.2, CEIL_Y - 0.25, ZEDGE - 0.2), (0.55, 0.55, 0.08), (0.9, 0.9, 0.86), shape="Cylinder",
          rot=(90, 0, 0), emissive=(0.5, 0.5, 0.46), emissive_intensity=0.7)
    s.box("Clock hand", g, (6.2, CEIL_Y - 0.2, ZEDGE - 0.25), (0.02, 0.2, 0.01), (0.02, 0.02, 0.02), rot=(0, 0, 8))
    s.box("Clock hand", g, (6.24, CEIL_Y - 0.25, ZEDGE - 0.25), (0.13, 0.02, 0.01), (0.02, 0.02, 0.02), rot=(0, 0, 12))
    # Signal heads at the tunnel mouths (the right one changes, below).
    s.box("Signal head", g, (X0 - 0.6, 3.1, NEAR_Z - 1.55), (0.3, 0.75, 0.25), (0.04, 0.04, 0.04))
    glow_box(s, g, "Left signal red", (X0 - 0.6, 3.25, NEAR_Z - 1.69), (0.12, 0.12, 0.02), (1.0, 0.08, 0.05), 4.0)
    s.box("Signal head", g, (X1 + 0.6, 3.1, NEAR_Z - 1.55), (0.3, 0.75, 0.25), (0.04, 0.04, 0.04))
    return g


def fixtures(s, parent):
    """Fluorescent tube fittings in rows along the platform ceiling."""
    g = s.group("Fluorescent fittings", parent)
    for z in (-10.5, -6.5, -2.5, 1.5, 3.7):
        for x in (-8.5, -4.25, 0, 4.25, 8.5):
            if z == 3.7 and abs(x) > 8:
                continue
            if x > 4 and -4.0 < z < 0 and z != 1.5:
                continue
            y = CEIL_Y - (0.36 if z != 3.7 else 0.55)
            s.box("Fitting", g, (x, y, z), (1.4, 0.07, 0.24), (0.32, 0.33, 0.33), shadows=False, metallic=0.4)
            # One tube is out near the turnstiles.
            dead = (x, z) == (-8.5, -6.5)
            for dz in (-0.05, 0.05):
                if dead and dz > 0:
                    s.box("Dead tube", g, (x, y - 0.05, z + dz), (1.3, 0.04, 0.04), (0.3, 0.3, 0.28), shape="Cylinder",
                          rot=(0, 0, 90), shadows=False)
                    continue
                glow_box(s, g, "Tube", (x, y - 0.05, z + dz), (1.3, 0.04, 0.04), FLUO, 5.5 if (x, z) != (4.25, -6.5) else 2.0,
                         rot=(0, 0, 0))
    return g


def board_states(s, parent):
    """The departure board over the pillar side: three faces for the night's three states."""
    g = s.group("Departure board", parent, (-3.0, 3.35, 0.15))
    s.box("Board housing", g, (0, 0, 0.06), (2.62, 0.92, 0.18), (0.06, 0.06, 0.07), rough=0.5)
    for dx in (-1.0, 1.0):
        s.box("Hanger", g, (dx, 0.86, 0.06), (0.04, 0.8, 0.04), STEEL, metallic=0.8)
    plain_light(s, g, "Board glow", (0, -0.4, -0.5), (1.0, 0.6, 0.2), 6.0, 3.0)
    one = s.story("Board: trains due", g, "first_train_gone", when_set=False, fade=0.4)
    panel(s, one, "Board face 1", "Board1", (0, 0, -0.04), 2.4, 0.75, glow=(1, 1, 1), glow_i=2.2)
    mid = s.story("Board: one more train", g, "first_train_gone", when_set=True, fade=0.4)
    mid2 = s.story("Board: until the last one goes", mid, "second_train_gone", when_set=False, fade=0.4)
    panel(s, mid2, "Board face 2", "Board2", (0, 0, -0.04), 2.4, 0.75, glow=(1, 1, 1), glow_i=2.2)
    three = s.story("Board: service ended", g, "second_train_gone", when_set=True, fade=0.4)
    panel(s, three, "Board face 3", "Board3", (0, 0, -0.04), 2.4, 0.75, glow=(1, 1, 1), glow_i=2.2)
    return g


def carriage(s, parent, name, z, lamp_side=-1):
    """Two lit carriages end to end along x, at track centre z, faces textured on the platform side."""
    g = s.group(name, parent)
    yb, yt = -0.95, 2.95
    for k, (xa, xb) in enumerate(((-11.6, -0.2), (0.2, 11.6))):
        s.slab("Carriage shell", g, xa, xb, yb, yt, z - 1.35, z + 1.35, (0.36, 0.37, 0.39), metallic=0.6, rough=0.4)
        face = s.box("Carriage side", g, ((xa + xb) / 2, (yb + yt) / 2, z - 1.37), (xb - xa, yt - yb, 0.02), (1, 1, 1),
                     rough=0.35, shadows=False)
        textured(face, "TrainSide", emissive=(1, 1, 1), emissive_intensity=1.3, glow_map="TrainGlow")
        s.box("Roof", g, ((xa + xb) / 2, yt + 0.05, z), (xb - xa, 0.3, 2.5), (0.3, 0.31, 0.33), metallic=0.5, rough=0.5)
        s.slab("Bogie skirt", g, xa + 0.3, xb - 0.3, BED_Y + 0.1, yb, z - 1.2, z + 1.2, (0.05, 0.05, 0.05), shadows=False)
    s.slab("Gangway", g, -0.2, 0.2, yb + 0.3, yt - 0.2, z - 1.0, z + 1.0, (0.08, 0.08, 0.08), shadows=False)
    return g


def train_spill(s, parent, z, power, reflections=True):
    """Window light falling on the platform, and its reflection in the polished floor."""
    for x in (-8.0, -3.0, 3.0, 8.0):
        plain_light(s, parent, "Window spill", (x, 1.4, z - 1.6), WARM, power, 7.5)
    if reflections:
        for x0 in range(-10, 11, 1):
            xc = x0 + 0.35
            if abs(xc) < 0.5:
                continue
            glow_box(s, parent, "Window reflection", (xc, 0.004, ZEDGE - 1.6), (0.42, 0.004, 1.6), (0.6, 0.52, 0.38), 0.55)


def trains(s, parent):
    g = s.group("Trains", parent)
    # Carriage A, near track: waiting at the platform until first_train_gone; it leaves into the right tunnel.
    a = s.story("Carriage A (near track)", g, "first_train_gone", when_set=False, fade=3.5, pos=(X1 + 1.5, 1.0, NEAR_Z))
    car = carriage(s, a, "Carriage A", NEAR_Z)
    car.components[0]["Position"] = vec((-(X1 + 1.5), -1.0, -NEAR_Z))
    spill = s.group("Carriage A light", a, (-(X1 + 1.5), -1.0, -NEAR_Z))
    train_spill(s, spill, NEAR_Z, 26.0)
    # Carriage B, far track: there until second_train_gone; leaves into the left tunnel.
    b = s.story("Carriage B (far track)", g, "second_train_gone", when_set=False, fade=3.5, pos=(X0 - 1.5, 1.0, FAR_Z))
    car = carriage(s, b, "Carriage B", FAR_Z)
    car.components[0]["Position"] = vec((-(X0 - 1.5), -1.0, -FAR_Z))
    bl = s.group("Carriage B light", b, (-(X0 - 1.5), -1.0, -FAR_Z))
    for x in (-6.0, 0.0, 6.0):
        plain_light(s, bl, "Far window spill", (x, 1.6, FAR_Z - 1.7), WARM, 30.0, 6.0)
    refl = s.story("Far train's reflection", g, "second_train_gone", when_set=False, fade=3.5, pos=(X0, 0, ZEDGE - 1.6))
    for x0 in range(-10, 11, 2):
        glow_box(s, refl, "Far reflection", (x0 + 0.6 - X0, 0.003, 0.4), (0.3, 0.004, 0.9), (0.42, 0.38, 0.3), 0.4)
    # The right signal: green while trains are due, red once the last one has gone.
    go = s.story("Signal green", g, "second_train_gone", when_set=False, fade=0.3, pos=(X1 + 0.6, 2.95, NEAR_Z - 1.69))
    glow_box(s, go, "Signal green lamp", (0, 0, 0), (0.12, 0.12, 0.02), (0.1, 1.0, 0.35), 5.0)
    plain_light(s, go, "Signal green spill", (0, 0, -0.3), (0.1, 1.0, 0.35), 3.0, 2.5)
    stop = s.story("Signal red", g, "second_train_gone", when_set=True, fade=0.3, pos=(X1 + 0.6, 3.25, NEAR_Z - 1.69))
    glow_box(s, stop, "Signal red lamp", (0, 0, 0), (0.12, 0.12, 0.02), (1.0, 0.08, 0.05), 5.0)
    plain_light(s, stop, "Signal red spill", (0, 0, -0.3), (1.0, 0.1, 0.05), 3.0, 2.5)
    return g


def the_pitch(s, parent):
    """The busker's things beside the fixed kit: crates, the orange bucket, the practice pad, the
    phone speaker, the cardboard sign and the open case (whose tip arrives at the end)."""
    g = s.group("The pitch", parent)
    crate = (0.12, 0.14, 0.16)

    def milk_crate(name, cx, cz, yaw=0):
        c = s.group(name, g, (cx, 0, cz))
        c.components[0]["Rotation"] = vec((0, yaw, 0))
        w, d, h = 0.46, 0.34, 0.3
        s.box("Crate top (upturned base)", c, (0, h - 0.02, 0), (w, 0.04, d), crate, rough=0.7)
        for sx in (-1, 1):
            s.box("Crate side", c, (sx * (w / 2 - 0.02), h / 2, 0), (0.04, h, d), crate, rough=0.7)
            s.box("Crate end", c, (0, h / 2, sx * (d / 2 - 0.02)), (w, h, 0.04), crate, rough=0.7)
            s.box("Handle hole", c, (0, h * 0.62, sx * (d / 2 - 0.01)), (0.14, 0.05, 0.03), (0.02, 0.02, 0.02))
        return c

    a = milk_crate("Upturned crate (bucket)", 1.95, 2.3, 8)
    s.box("Orange bucket", a, (0, 0.3 + 0.19, 0), (0.31, 0.38, 0.31), (0.95, 0.36, 0.04), shape="Cylinder", rough=0.45)
    s.box("Bucket rim", a, (0, 0.3 + 0.36, 0), (0.33, 0.03, 0.33), (0.85, 0.3, 0.03), shape="Cylinder", rough=0.45)
    s.box("Bucket base (played)", a, (0, 0.3 + 0.385, 0), (0.25, 0.012, 0.25), (0.98, 0.5, 0.18), shape="Cylinder", rough=0.4)
    b = milk_crate("Upturned crate (pad)", 1.85, 1.55, -12)
    s.box("Practice pad", b, (0, 0.3 + 0.02, 0), (0.3, 0.03, 0.3), (0.1, 0.1, 0.1), shape="Cylinder", rough=0.6)
    s.box("Pad gum", b, (0, 0.3 + 0.04, 0), (0.24, 0.01, 0.24), (0.35, 0.36, 0.38), shape="Cylinder", rough=0.9)
    s.box("Phone speaker", b, (0.15, 0.3 + 0.06, 0.1), (0.16, 0.07, 0.06), (0.05, 0.05, 0.06), rough=0.5)
    glow_box(s, b, "Speaker light", (0.15, 0.3 + 0.06, 0.068), (0.02, 0.02, 0.005), (0.2, 0.6, 1.0), 3.0)
    s.box("Phone", b, (-0.12, 0.3 + 0.03, 0.08), (0.075, 0.01, 0.15), (0.02, 0.02, 0.03), rot=(0, 20, 0))
    glow_box(s, b, "Phone screen", (-0.12, 0.3 + 0.036, 0.08), (0.065, 0.002, 0.135), (0.5, 0.7, 1.0), 1.4, rot=(0, 20, 0))
    s.box("Stick bag", g, (2.3, 0.06, 1.95), (0.18, 0.12, 0.6), (0.2, 0.08, 0.06), rot=(0, 18, 0), rough=0.85)
    sign = s.group("Cardboard sign", g, (2.45, 0, 1.0))
    sign.components[0]["Rotation"] = vec((-14, -25, 0))
    panel(s, sign, "Sign face", "CardSign", (0, 0.27, 0), 0.62, 0.46, thick=0.008, rough=0.95)
    # The open case for tips, lid up behind it.
    c = s.group("Open case", g, (1.75, 0, 0.35))
    c.components[0]["Rotation"] = vec((0, -14, 0))
    s.box("Case shell", c, (0, 0.06, 0), (0.95, 0.12, 0.42), (0.06, 0.06, 0.07), rough=0.5)
    lin = s.box("Case lining", c, (0, 0.121, 0), (0.88, 0.004, 0.36), (1, 1, 1), rough=1.0, shadows=False)
    textured(lin, "Lining", (2, 1))
    lid = s.group("Case lid", c, (0, 0.12, 0.21))
    lid.components[0]["Rotation"] = vec((-72, 0, 0))
    s.box("Lid shell", lid, (0, 0.03, 0.21), (0.95, 0.06, 0.42), (0.06, 0.06, 0.07), rough=0.5)
    lin2 = s.box("Lid lining", lid, (0, -0.002, 0.21), (0.88, 0.004, 0.36), (1, 1, 1), rough=1.0, shadows=False)
    textured(lin2, "Lining", (2, 1))
    s.box("Seed coin", c, (-0.3, 0.128, -0.06), (0.026, 0.004, 0.026), (0.72, 0.72, 0.74), shape="Cylinder", metallic=1, rough=0.3,
          emissive=(0.6, 0.6, 0.58), emissive_intensity=1.0)

    tip = s.story("The first tip", c, "tip_in_case", when_set=True, fade=0.6, pos=(0, 0.13, 0))
    s.box("Drilled loonie", tip, (0.05, 0.0, -0.03), (0.06, 0.006, 0.06), (0.95, 0.68, 0.2), shape="Cylinder", metallic=1.0,
          rough=0.25, emissive=(1.0, 0.7, 0.22), emissive_intensity=2.2)
    s.box("Drill hole", tip, (0.05, 0.0035, -0.012), (0.012, 0.004, 0.012), (0.02, 0.02, 0.02), shape="Cylinder")
    xfer = s.box("Cafe transfer", tip, (-0.12, 0.004, 0.02), (0.11, 0.003, 0.22), (1, 1, 1), rot=(0, 72, 0), rough=0.9, shadows=False)
    textured(xfer, "Transfer")
    for i, (x, z) in enumerate(((0.22, 0.08), (0.3, -0.07), (-0.34, 0.1), (0.16, -0.12))):
        s.box("Coin", tip, (x, 0.0, z), (0.026, 0.004, 0.026), (0.75, 0.74, 0.7) if i % 2 else (0.9, 0.64, 0.2), shape="Cylinder",
              metallic=1, rough=0.3, emissive=(0.7, 0.7, 0.66) if i % 2 else (0.9, 0.62, 0.2), emissive_intensity=1.2)
    plain_light(s, tip, "Tip glow", (0, 0.9, -0.5), (1.0, 0.72, 0.34), 16.0, 3.2)
    return g


def cast(s, parent):
    g = s.group("The regulars", parent)
    c = s.story("Commuter at the pillar", g, "commuter_at_pillar", when_set=True, fade=1.2, pos=(-3.75, 0, 0.05))
    people.person(s, c, "Mustard-scarf commuter", "Mother_02", "02_B", "MugBob", (0, 0, 0), 78, 1.0, 1.0, held="mug",
                  scarf=MUSTARD)
    s.box("Commuter's tote", c, (-0.32, 0.2, 0.1), (0.36, 0.38, 0.12), (0.18, 0.2, 0.25), rot=(0, 70, 6), rough=0.9)
    plain_light(s, c, "Light catching the mug", (0.5, 2.1, -0.7), (1.0, 0.9, 0.75), 16.0, 3.5)

    fam = s.story("Family at the pitch", g, "family_at_pitch", when_set=True, fade=1.0, pos=(3.3, 0, 0.9))
    people.person(s, fam, "Kid in the yellow coat", "Daughter_01", "01_A", "HandsUp", (-0.45, 0, 0.45), -128, 0.68, 1.0)
    people.person(s, fam, "Kid with the scooter", "Son_01", "03_B", "HandsUpLate", (0.35, 0, -0.25), -112, 0.72, 1.0)
    s.box("Scooter deck", fam, (0.9, 0.06, -0.55), (0.12, 0.04, 0.55), (0.1, 0.5, 0.9), rot=(0, 30, 0))
    s.box("Scooter stem", fam, (0.78, 0.4, -0.75), (0.03, 0.72, 0.03), STEEL, rot=(0, 30, 10), metallic=0.8)
    s.box("Backpack", fam, (0.95, 0.15, 0.2), (0.28, 0.32, 0.18), (0.85, 0.2, 0.3), rot=(0, -20, 8), rough=0.9)
    plain_light(s, fam, "Patch of light", (0.0, 3.0, -1.0), (1.0, 0.92, 0.8), 10.0, 4.0)
    # Mum on the stairs until the last train goes, then by the bucket clapping.
    step = 7
    sx = STAIR_X0 + (step - 1) * STEP_RUN + STEP_RUN / 2
    stairs_mum = s.story("Mum watching from the stairs", fam, "second_train_gone", when_set=False, fade=1.0,
                         pos=(sx - 3.3, step * STEP_RISE, -2.6 - 0.9))
    people.person(s, stairs_mum, "Mum on the stairs", "Mother_01", "04_A", "Watch", (0, 0, 0), -118, 1.0, 1.0)
    s.box("Shopping bag", stairs_mum, (0.35, 0.18, 0.15), (0.3, 0.34, 0.14), (0.85, 0.82, 0.74), rough=0.9)
    clap = s.story("Mum clapping by the bucket", g, "second_train_gone", when_set=True, fade=1.0, pos=(3.75, 0, 1.75))
    people.person(s, clap, "Mum clapping", "Mother_01", "04_A", "Clap", (0, 0, 0), -122, 1.0, 1.0)
    s.box("Shopping bag", clap, (0.3, 0.17, 0.35), (0.3, 0.34, 0.14), (0.85, 0.82, 0.74), rough=0.9, rot=(0, 20, 0))
    return g


def lights(s, parent):
    g = s.group("Lights", parent)
    # The one shadowed light: a dim cool key straight down, as if from the tube rows (the ceiling doesn't cast).
    s.light("Tube key", g, (0, 8, -2), "Directional", (0.78, 0.95, 0.88), 0.32, rot=(72, 18, 0), shadows=True, show="Static")
    # Fluorescent rows: bar lights along the fittings, the room's light.
    for (x, z, p) in ((-4.25, -6.5, 34), (4.25, -6.5, 20), (-4.25, -2.5, 34), (0, -2.5, 40), (-4.25, 1.5, 40),
                      (4.25, 1.5, 36), (-8.5, 1.5, 30), (8.5, -10.5, 24), (-8.5, -10.5, 24), (0, -10.5, 28)):
        e = s.light("Tube row", g, (x, CEIL_Y - 0.45, z), "Bar", FLUO, p, 9.0, show="Static")
        e.components[-2].update({"Length": 1.3, "Radius": 0.03})
    # Sodium from the street, down the stairs.
    s.light("Sodium down the stairwell", g, (X1 - 0.5, 7.2, -2.0), "Spot", SODIUM, 520.0, 16.0,
            rot=look_rotation((X1 - 0.5, 7.2, -2.0), (5.5, 0.0, -1.6)), inner=22, outer=48, show="Static")
    s.light("Sodium bounce", g, (7.5, 2.4, -2.0), "Point", SODIUM, 26.0, 6.0, show="Static")
    for x in (-7.5, 7.5):
        s.light("Trackside work lamp", g, (x, 4.6, ZFAR - 1.2), "Point", (0.9, 1.0, 0.92), 70.0, 7.0, show="Static")
    s.light("Booth lamp", g, (-9.6, 2.0, -8.6), "Point", WARM, 18.0, 5.0, show="Static")
    s.light("Vending glow", g, (-9.7, 1.2, -1.8), "Point", (1.0, 0.75, 0.6), 10.0, 3.5, show="Static")
    s.light("Name wall wash", g, (0, 5.9, ZFAR - 2.5), "Spot", (0.85, 1.0, 0.92), 1400.0, 12.0,
            rot=look_rotation((0, 5.9, ZFAR - 2.5), (0, 1.8, ZFAR)), inner=40, outer=70, show="Static")
    # The pitch: the cued washes and the drummer's follow.
    for i, (pos, col) in enumerate((((-2.2, 3.4, -0.6), (0.9, 0.95, 1.0)), ((2.2, 3.4, -0.6), (1.0, 0.8, 0.55)),
                                    ((0.0, 3.6, 3.8), (0.6, 0.9, 1.0)), ((-1.0, 2.2, -3.4), (1.0, 0.7, 0.4)))):
        s.light(f"Pitch wash {i + 1}", g, pos, "Point", col, 48.0, 7.0, show="Wash", group=i % 3)
    s.light("Tube over the pitch", g, (0.4, CEIL_Y - 0.4, 0.2), "Spot", (0.95, 1.0, 0.95), 420.0, 9.0,
            rot=look_rotation((0.4, CEIL_Y - 0.4, 0.2), (0, 1.1, 2.4)), inner=20, outer=42, show="Spot")
    # The tunnel mouths: headlamp glare that flashes on peaks.
    for i, x in enumerate((X0 - 1.2, X1 + 1.2)):
        s.light(f"Headlamp glare {i + 1}", g, (x, 0.6, NEAR_Z), "Spot", (1.0, 0.95, 0.85), 500.0, 18.0,
                rot=look_rotation((x, 0.6, NEAR_Z), (0, 0.8, -4.0)), inner=10, outer=34, show="Blinder", group=i)
    # The tube that buzzes: strobes on cue.
    s.light("Buzzing tube", g, (-8.5, CEIL_Y - 0.5, -6.5), "Point", FLUO, 120.0, 9.0, show="Strobe", group=0)
    s.light("Buzzing tube 2", g, (4.25, CEIL_Y - 0.5, -6.5), "Point", FLUO, 120.0, 9.0, show="Strobe", group=1)
    return g


def markers(s, parent):
    m = s.group("Venue markers", parent)
    s.info(m, "The Last Train Busking Pitch", "Drumsmith", room_back=ZBACK, room_ceiling=CEIL_Y, half_width=X1, desk_z=-11.6,
           ambient=(0.006, 0.008, 0.008), fog_color=(0.02, 0.026, 0.024), haze=0.9)
    s.spot(m, "Drummer", (0, 0, 3.05))
    # A small knot of commuters that grows: full figures close to the pitch, a few more at the back.
    s.crowd("Left of the pitch", m, (-2.3, 0, -3.9), 2.6, 1.2, 3, 0.6, figures="Posed")
    s.crowd("Right of the pitch", m, (2.1, 0, -4.1), 2.4, 1.2, 3, 0.6, figures="Posed")
    s.crowd("Off the last train", m, (-0.6, 0, -7.0), 6.0, 2.6, 6, 0.9)
    s.crowd("Hanging back by the stairs", m, (4.0, 0, -5.6), 1.6, 1.2, 2, 0.8)
    cams = s.group("Camera positions", m)
    for tag, kind, eye, aim, fov in [
            ("platform-wide", "Wide", (0.0, 3.5, -9.4), (0.0, 1.25, 4.0), 56),
            ("over-the-turnstiles", "Crane", (-8.2, 3.9, -6.6), (0.4, 1.0, 2.2), 54),
            ("booth-long-lens", "Desk", (-2.5, 1.9, -12.2), (0.0, 1.45, 2.4), 30),
            ("commuter", "Custom", (-1.2, 1.65, -2.2), (-3.75, 1.45, 0.35), 44),
            ("tip-case", "Custom", (1.55, 1.05, -0.9), (1.8, 0.1, 0.4), 42),
            ("along-the-train", "Custom", (-9.6, 1.7, 3.3), (4.0, 1.4, 5.2), 52),
            ("family", "Custom", (5.2, 1.7, -1.8), (2.6, 0.9, 1.4), 50),
            ("from-the-stairs", "Custom", (8.8, 3.4, -2.0), (0.5, 1.0, 2.0), 50),
            ("sticks-and-bucket", "Close", (2.9, 1.5, 0.3), (0.7, 0.9, 2.5), 46),
            ("board-and-pillar", "Custom", (-0.6, 1.2, -4.8), (-3.2, 2.6, 0.6), 50)]:
        s.camera_spot(tag, cams, eye, aim, kind, fov, tag)
    walk = [((10.3, 5.0, -2.0), (5.0, 1.2, -2.0), 70), ((9.0, 4.15, -2.1), (3.0, 1.3, -0.6), 68),
            ((7.6, 3.2, -2.2), (1.0, 1.4, 1.0), 66), ((6.0, 2.35, -2.4), (0.5, 1.4, 2.0), 64),
            ((4.2, 1.8, -2.9), (0.2, 1.3, 2.4), 62), ((2.4, 1.7, -3.8), (0.0, 1.3, 2.6), 60)]
    for i, (eye, aim, fov) in enumerate(walk):
        s.camera_spot(f"Arrival {i + 1:02}", cams, eye, aim, "Custom", fov, f"arrival/{i + 1:02}")
    return m


def build():
    textures.make_all()
    people.clips()
    s = Scene(seed="story-subway-bellwoods-v1")
    root = s.group("Bellwoods: The Last Train Busking Pitch")
    station(s, root)
    pillars = s.group("Pillars", root)
    pillar(s, pillars, "Pitch pillar", -4.75, 0.9, sign="PitchSign")
    pillar(s, pillars, "Pillar", -9.0, 0.9)
    pillar(s, pillars, "Pillar", 9.6, 0.9)
    pillar(s, pillars, "Pillar", -4.75, -7.6)
    pillar(s, pillars, "Pillar", 4.75, -7.6)
    stairs(s, root)
    turnstiles(s, root)
    dressing(s, root)
    fixtures(s, root)
    board_states(s, root)
    trains(s, root)
    the_pitch(s, root)
    cast(s, root)
    lights(s, root)
    markers(s, root)
    return s


def ambience(folder):
    """Platform room tone: lowpassed brown noise, the tubes' 120 Hz hum, a train rumbling somewhere
    under the city halfway through the 40 s loop. Synthesised with ffmpeg (once; kept if present)."""
    path = os.path.join(folder, "Ambience.ogg")
    if os.path.exists(path) or not shutil.which("ffmpeg"):
        return
    graph = ("[0]lowpass=f=260,volume=0.9,volume='0.55+0.45*pow(sin(PI*t/40),6)':eval=frame[n];[1]volume=0.025[h];"
             "[2]volume=0.012[h2];[n][h][h2]amix=inputs=3:normalize=0,afade=t=in:d=1.5,afade=t=out:st=38.5:d=1.5")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", "anoisesrc=color=brown:amplitude=0.5:seed=7:duration=40:sample_rate=44100",
                    "-f", "lavfi", "-i", "sine=frequency=120:duration=40:sample_rate=44100",
                    "-f", "lavfi", "-i", "sine=frequency=240:duration=40:sample_rate=44100",
                    "-filter_complex", graph, "-c:a", "libvorbis", "-q:a", "3", "-map_metadata", "-1",
                    "-fflags", "+bitexact", "-flags:a", "+bitexact", path], check=True)


def main():
    folder = os.path.join(repo_root(), "Assets", "Venues", ID)
    ambience(folder)
    scene = build()
    scene.write(os.path.join(folder, ID + ".lvl"))
    preview = "Preview.jpg" if os.path.exists(os.path.join(folder, "Preview.jpg")) else None
    sound = "Ambience.ogg" if os.path.exists(os.path.join(folder, "Ambience.ogg")) else None
    write_venue_json(folder, "The Last Train Busking Pitch", ID + ".lvl", preview=preview, ambience=sound)
    print(f"{len(scene.entities)} entities in {folder}")


if __name__ == "__main__":
    main()
