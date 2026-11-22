#!/usr/bin/env python3
"""Writes Assets/Venues/StoryGardens/: story set 11, "Home Ice at Maple Leaf Gardens" (s11-gardens).

    python3 Tools/Venues/make_story_gardens.py [--textures]

The old hockey palace in concert configuration: the riser at centre ice ringed by a run of rink
glass, the floor crowd standing on the painted ice inside the boards, the steep colour-coded bowl
(reds, golds, blues, greens, then the greys up under the roof), a centre-hung lamp scoreboard,
red goal lamps on the end glass, banners in the rafters and follow spots from the gondolas.

Story flags (Design/Story-Mode-Setlists.json, s11-gardens):
  goal_lamp_on    the west goal lamp comes on red and a red spill picks out the kid in the sweater.
  both_ends_lit   the east lamp answers; red cross-beams trade over the stage; the kid's sleeves go up.
  board_wave      the front row behind the west glass is up: arms and white towels rippling to the bench.
  banner_rigged   a furled banner goes up on ropes above centre ice, a follow spot on it, a corner loose.
  banner_dropped  the furl is gone: the YOUR BAND banner hangs unfurled under the scoreboard, lit.

Deterministic: rerun = same bytes. --textures redraws the pictures first (needs ImageMagick 7).
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from venuegen import Scene, look_rotation, repo_root, write_venue_json  # noqa: E402

ID = "StoryGardens"
VPATH = f"Assets/Venues/{ID}/"
TEX = VPATH + "Textures/"
MOTION = VPATH + "Motion/"
VM = "Assets/Models/Venue/"
CROWD = "Assets/Models/People/Crowd/"

# The rink: x -26..26 (west / east ends), z -11.5..11.5 (near / far side), corners chamfered 7 m.
HX, HZ, CH = 26.0, 11.5, 7.0

ICEBLUE = (0.86, 0.9, 0.94)
BOARD = (0.93, 0.93, 0.9)
KICK = (0.92, 0.72, 0.1)
CAP = (0.62, 0.08, 0.08)
CONCRETE = (0.24, 0.22, 0.21)
STEEL = (0.16, 0.16, 0.18)
BLACK = (0.035, 0.035, 0.04)
GOALRED = (1.0, 0.07, 0.04)
AMBER = (1.0, 0.62, 0.28)
WARM = (1.0, 0.82, 0.6)
JERSEY = (0.06, 0.16, 0.55)

# Seat colours by tier, the old Gardens way: reds by the glass, then golds, blues, greens; greys up top.
TIERS = [(0.55, 0.06, 0.06), (0.55, 0.06, 0.06), (0.75, 0.55, 0.1), (0.75, 0.55, 0.1),
         (0.1, 0.22, 0.55), (0.1, 0.22, 0.55), (0.1, 0.38, 0.18), (0.1, 0.38, 0.18)]
GREYS = (0.36, 0.36, 0.38)


# ---- small helpers ----------------------------------------------------------------------------
def material(e):
    for c in e.components:
        if c.get("Type") == "Mesh":
            return c["Material"]
    raise KeyError("no mesh")


def textured(e, path, tiling=(1, 1), emissive=None, intensity=1.0):
    m = material(e)
    m["Textures"] = {"Diffuse": {"Path": path}}
    if emissive is not None:
        m["Textures"]["Emissive"] = {"Path": path}
        m["EmissiveColor"] = [float(v) for v in emissive]
        m["EmissiveIntensity"] = float(intensity)
    m["Tiling"] = [float(tiling[0]), float(tiling[1])]
    return e


def see_through(e, opacity, additive=False):
    m = material(e)
    m["RenderMode"] = 1
    m["BlendMode"] = 2 if additive else 0
    m["Opacity"] = float(opacity)
    for c in e.components:
        if c.get("Type") == "Mesh":
            c["CastShadows"] = False
    return e


def yaw_of(dx, dz):
    """Yaw (deg) that turns a box's local +x along (dx, dz)."""
    return math.degrees(math.atan2(-dz, dx))


def quat(rot):
    x, y, z = [math.radians(a) / 2 for a in rot]
    a, b = math.sin(x), math.cos(x)
    c, d = math.sin(y), math.cos(y)
    e, f = math.sin(z), math.cos(z)
    return [round(v, 7) for v in (a * d * f - b * c * e, b * c * f + a * d * e, b * d * e - a * c * f, b * d * f + a * c * e)]


def octagon(d):
    """The rink outline pushed out by d metres: 8 corners, counter-clockwise seen from above."""
    base = [(HX - CH, HZ), (-(HX - CH), HZ), (-HX, HZ - CH), (-HX, -(HZ - CH)),
            (-(HX - CH), -HZ), (HX - CH, -HZ), (HX, -(HZ - CH)), (HX, HZ - CH)]
    n = len(base)
    lines = []
    for i in range(n):
        (ax, az), (bx, bz) = base[i], base[(i + 1) % n]
        ex, ez = bx - ax, bz - az
        ln = math.hypot(ex, ez)
        nx, nz = ez / ln, -ex / ln  # outward for CCW (x right, z up when seen from +y... checked below)
        # make sure the normal points away from the centre
        mx, mz = (ax + bx) / 2, (az + bz) / 2
        if nx * mx + nz * mz < 0:
            nx, nz = -nx, -nz
        lines.append(((ax + nx * d, az + nz * d), (ex / ln, ez / ln)))
    pts = []
    for i in range(n):
        (p, u), (q, v) = lines[i - 1], lines[i]
        # p + s u = q + t v
        det = u[0] * (-v[1]) - u[1] * (-v[0])
        s = ((q[0] - p[0]) * (-v[1]) - (q[1] - p[1]) * (-v[0])) / det
        pts.append((p[0] + s * u[0], p[1] + s * u[1]))
    return pts  # pts[i] is the start of edge i


def edges(d):
    pts = octagon(d)
    return [(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]


def ring_box(s, name, parent, d0, d1, y0, y1, color, overlap=0.0, skip=(), **kw):
    """A band of the octagon between offsets d0 and d1 (metres out from the boards), y0..y1."""
    out = []
    for i, (a, b) in enumerate(edges((d0 + d1) / 2)):
        if i in skip:
            continue
        ex, ez = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(ex, ez)
        c = ((a[0] + b[0]) / 2, (y0 + y1) / 2, (a[1] + b[1]) / 2)
        out.append(s.box(f"{name} {i}", parent, c, (ln + overlap, y1 - y0, d1 - d0), color, rot=(0, yaw_of(ex, ez), 0), **kw))
    return out


def story_at(s, name, parent, flag, when_set, fade, pos):
    """A story group whose pivot (what it grows from) is pos, returning a child at venue-space
    identity, so the props under it are placed with venue coordinates (parent must be at identity)."""
    g = s.story(name, parent, flag, when_set, fade, pos)
    return s.group(name + " / venue space", g, (-pos[0], -pos[1], -pos[2]))


# ---- people -------------------------------------------------------------------------------------
SHOULDER = 0.191, 1.3904, -0.0484
UP_L, UP_R = (-170, 0, -14), (-170, 0, 14)


def fan(s, parent, name, person, pos, yaw, scale=1.0):
    root = s.entity(name, parent, pos, (0, yaw, 0), (scale,) * 3)
    s.entity("Body", root).add({"Type": "Model", "ModelPath": f"{CROWD}{person}/Body_Lo.obj"})
    return root


def arm(s, parent, person, side, rot, lo=True):
    x, y, z = SHOULDER
    part = ("ArmL" if side < 0 else "ArmR") + ("_Lo" if lo else "")
    e = s.entity(part, parent, (side * x, y, z), rot)
    e.add({"Type": "Model", "ModelPath": f"{CROWD}{person}/{part}.obj"})
    return e


def write_clip(folder, name, frames, tracks):
    clip = {"Version": 1, "Name": name, "FrameRate": 30, "DurationFrames": frames, "Tracks": tracks}
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, name + ".sequence"), "w", newline="\n") as f:
        json.dump(clip, f, indent=1)
        f.write("\n")


# ---- the build ----------------------------------------------------------------------------------
def build(folder):
    s = Scene(seed="story-gardens-v1")
    root = s.group("Maple Leaf Gardens")
    bowl = s.group("Bowl and roof", root)
    rink = s.group("Ice, boards and glass", root)
    stage = s.group("Centre-ice riser", root)
    people = s.group("People at the glass", root)
    story = s.group("Story", root)
    lights = s.group("Lights", root)
    marks = s.group("Markers", root)

    # ---- the floor and the ice
    s.slab("Event level", bowl, -60, 60, -0.4, -0.02, -45, 45, CONCRETE)
    ice = s.box("Ice", rink, (0, -0.01, 0), (2 * HX, 0.02, 2 * HZ), (1.0, 1.0, 1.0), rough=0.25)
    textured(ice, TEX + "Ice.png")

    # ---- boards, kickplate, cap rail and glass around the octagon
    for i, (a, b) in enumerate(edges(0.08)):
        ex, ez = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(ex, ez)
        yaw = yaw_of(ex, ez)
        cx, cz = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        brd = s.box(f"Boards {i}", rink, (cx, 0.535, cz), (ln + 0.16, 1.07, 0.16), (1, 1, 1), rot=(0, yaw, 0), rough=0.6)
        textured(brd, TEX + "BoardAds.png", (max(1.0, round(ln / 14.0, 2)), 1))
        s.box(f"Cap rail {i}", rink, (cx, 1.09, cz), (ln + 0.2, 0.05, 0.22), CAP, rot=(0, yaw, 0))
        g = s.box(f"Glass {i}", rink, (cx, 1.77, cz), (ln, 1.36, 0.03), (0.7, 0.85, 0.92), rot=(0, yaw, 0), rough=0.05)
        see_through(g, 0.16)
        s.box(f"Glass top rail {i}", rink, (cx, 2.46, cz), (ln, 0.04, 0.05), (0.75, 0.78, 0.8), rot=(0, yaw, 0), metallic=0.6, rough=0.3)
        posts = max(2, int(ln / 2.45))
        for k in range(posts + 1):
            t = k / posts
            s.box(f"Glass seam {i}.{k}", rink, (a[0] + ex * t, 1.77, a[1] + ez * t), (0.05, 1.36, 0.05), (0.78, 0.8, 0.82),
                  rot=(0, yaw, 0), metallic=0.5, shadows=False)

    # ---- the bowl: lower bowl eight steps of two rows, the concourse and fascia, then the greys
    seat_tops = []
    for k in range(8):
        d0, d1 = 0.25 + k * 1.7, 0.25 + (k + 1) * 1.7
        top = 1.45 + k * 1.02
        ring_box(s, f"Lower bowl {k}", bowl, d0, d1 + 0.05, 0, top, TIERS[k], overlap=2.2 + k * 0.9)
        # The row's lip in a lighter shade so the steps read at distance.
        lip = tuple(min(1, c * 1.5 + 0.05) for c in TIERS[k])
        ring_box(s, f"Row lip {k}", bowl, d0, d0 + 0.12, top, top + 0.05, lip, overlap=2.2 + k * 0.9, shadows=False)
        seat_tops.append((d0, d1, top))
    walk_d0, walk_d1 = 0.25 + 8 * 1.7, 0.25 + 8 * 1.7 + 1.8
    walk_y = 1.45 + 7 * 1.02 + 0.3
    ring_box(s, "Concourse walk", bowl, walk_d0, walk_d1, 0, walk_y, (0.2, 0.19, 0.18), overlap=10)
    fascia_y0, fascia_y1 = walk_y, walk_y + 2.4
    for i, (a, b) in enumerate(edges(walk_d1 + 0.1)):
        ex, ez = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(ex, ez)
        f = s.box(f"Balcony fascia {i}", bowl, ((a[0] + b[0]) / 2, (fascia_y0 + fascia_y1) / 2, (a[1] + b[1]) / 2),
                  (ln + 10, fascia_y1 - fascia_y0, 0.2), (1, 1, 1), rot=(0, yaw_of(ex, ez), 0), rough=0.7)
        textured(f, TEX + "Fascia.png", (max(1.0, round((ln + 10) / 40.0, 2)), 1))
    upper = []
    for k in range(6):
        d0, d1 = walk_d1 + 0.2 + k * 1.55, walk_d1 + 0.2 + (k + 1) * 1.55
        top = fascia_y1 + 0.4 + k * 1.1
        shade = tuple(c * (0.85 + 0.05 * k) for c in GREYS)
        ring_box(s, f"The greys {k}", bowl, d0, d1 + 0.05, fascia_y0, top, shade, overlap=12 + k)
        upper.append((d0, d1, top))
    back_d = upper[-1][1]
    ring_box(s, "Back wall", bowl, back_d, back_d + 0.6, 0, 27, (0.13, 0.11, 0.1), overlap=16)

    # Aisles: concrete stairs cutting the lower bowl on each long side and end.
    for i, (a, b) in enumerate(edges(0.25 + 4 * 1.7)):
        if i % 2:
            continue
        ex, ez = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(ex, ez)
        nx, nz = (ez / ln, -ex / ln)
        mx, mz = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        if nx * mx + nz * mz < 0:
            nx, nz = -nx, -nz
        for t in ((0.2, 0.5, 0.8) if ln > 30 else (0.5,)):
            px, pz = a[0] + ex * t, a[1] + ez * t
            for k in range(8):
                d0, d1, top = seat_tops[k]
                off = (d0 + d1) / 2 - (0.25 + 4 * 1.7)
                s.box(f"Aisle {i}.{t}.{k}", bowl, (px + nx * off, top + 0.03, pz + nz * off), (1.1, 0.08, 1.72),
                      (0.42, 0.4, 0.38), rot=(0, yaw_of(ex, ez), 0), shadows=False)
            # A vomitory: the dark mouth of the tunnel under the bowl, halfway up.
            d0, d1, top = seat_tops[3]
            s.box(f"Vomitory {i}.{t}", bowl, (px + nx * (d0 - 0.25 - 4 * 1.7 + 0.02), top - 1.0, pz + nz * (d0 - 0.25 - 4 * 1.7 + 0.02)),
                  (2.6, 2.0, 0.1), (0.01, 0.01, 0.012), rot=(0, yaw_of(ex, ez), 0), shadows=False)

    # ---- the roof: a shallow dome of steel on trusses, house lamps hung under it
    for k, (r, y) in enumerate([(1.0, 30.0), (0.75, 31.4), (0.48, 32.4), (0.22, 33.0)]):
        s.box(f"Roof deck {k}", bowl, (0, y, 0), (2 * (HX + back_d) * r + 1, 0.4, 2 * (HZ + back_d) * r + 1), (0.08, 0.075, 0.07))
    for k in range(-4, 5):
        x = k * 9.5
        s.box(f"Truss chord N {k}", bowl, (x, 26.2, 0), (0.5, 0.5, 2 * (HZ + back_d)), STEEL, metallic=0.4)
        s.box(f"Truss chord S {k}", bowl, (x, 28.4, 0), (0.4, 0.4, 2 * (HZ + back_d)), STEEL, metallic=0.4)
        for j in range(-8, 9):
            z = j * 4.2
            s.box(f"Truss web {k}.{j}", bowl, (x, 27.3, z + 1.05), (0.18, 2.6, 0.18), STEEL, rot=(40 if j % 2 else -40, 0, 0), shadows=False)
    for j in (-24, -12, 0, 12, 24):
        s.box(f"Purlin {j}", bowl, (0, 26.0, j), (2 * (HX + back_d), 0.3, 0.3), STEEL, metallic=0.4)
    for kx in range(-3, 4):
        for kz in (-2, -1, 1, 2):
            x, z = kx * 11.0 + 5.5 * (kz % 2), kz * 11.5
            s.box(f"House lamp {kx}.{kz}", bowl, (x, 25.3, z), (0.6, 0.3, 0.6), (0.2, 0.18, 0.15),
                  emissive=WARM, emissive_intensity=2.2, shadows=False)
            s.box(f"House lamp cord {kx}.{kz}", bowl, (x, 25.65, z), (0.04, 0.5, 0.04), BLACK, shadows=False)

    # ---- rafter banners (always there) and the flag
    hang = s.group("Rafter banners", bowl)
    spots = [(-22, 16.5), (-14, 18.0), (14, 18.0), (22, 16.5)]
    for n, (x, z) in enumerate(spots):
        name = f"RafterBanner{n + 1}"
        b = s.box(name, hang, (x, 21.0, z + 8), (3.0, 6.0, 0.06), (1, 1, 1), rot=(0, 180 + (x * 0.6), 0), rough=0.9)
        textured(b, TEX + name + ".png")
        s.box(name + " batten", hang, (x, 24.1, z + 8), (3.3, 0.12, 0.12), STEEL, rot=(0, 180 + x * 0.6, 0))
        s.box(name + " drop", hang, (x, 25.1, z + 8), (0.04, 2.0, 0.04), BLACK, shadows=False)
    b = s.box("RafterBanner5", hang, (-40, 20.0, 0), (3.0, 6.0, 0.06), (1, 1, 1), rot=(0, 90, 0))
    textured(b, TEX + "RafterBanner5.png")
    b = s.box("RafterBanner5 east", hang, (40, 20.0, 0), (3.0, 6.0, 0.06), (1, 1, 1), rot=(0, -90, 0))
    textured(b, TEX + "RafterBanner5.png")
    flag = s.box("Flag of Canada", hang, (0, 21.5, 27), (10.0, 5.0, 0.06), (1, 1, 1), rot=(0, 180, 0))
    textured(flag, TEX + "CanadaFlag.png")
    s.box("Flag batten", hang, (0, 24.1, 27), (10.4, 0.14, 0.14), STEEL)
    for n, (x, z) in enumerate([(-30, -26), (30, -26)]):
        b = s.box(f"Near banner {n}", hang, (x, 21.5, z), (3.0, 6.0, 0.06), (1, 1, 1), rot=(0, 35 if x < 0 else -35, 0))
        textured(b, TEX + ("RafterBanner3.png" if n == 0 else "RafterBanner2.png"))

    # ---- the centre-hung scoreboard
    sb = s.group("Scoreboard", bowl, (0, 21.0, 0.5))
    s.box("Scoreboard case", sb, (0, 0, 0), (6.2, 4.2, 6.2), (0.05, 0.05, 0.055), metallic=0.3)
    for n, yaw in enumerate((0, 90, 180, 270)):
        r = math.radians(yaw)
        face = s.box(f"Scoreboard face {n}", sb, (-3.12 * math.sin(r), -0.1, -3.12 * math.cos(r)), (5.8, 3.6, 0.04), (1, 1, 1),
                     rot=(0, yaw, 0))
        textured(face, TEX + ("Scoreboard.png" if n % 2 == 0 else "ScoreboardSide.png"), emissive=(1, 1, 1), intensity=1.6)
    s.box("Scoreboard skirt", sb, (0, -2.4, 0), (6.6, 0.6, 6.6), (0.5, 0.06, 0.06), emissive=(0.9, 0.1, 0.08), emissive_intensity=0.6)
    s.box("Scoreboard crown", sb, (0, 2.35, 0), (5.0, 0.5, 5.0), STEEL)
    for x in (-2.4, 2.4):
        for z in (-2.4, 2.4):
            s.box("Scoreboard cable", sb, (x, 4.4, z), (0.05, 4.0, 0.05), BLACK, shadows=False)

    # ---- the goals and the goal lamps on the end glass
    lamps = {}
    for side, label in ((-1, "West"), (1, "East")):
        gx = 22.6 * side
        net = s.group(f"{label} goal", rink, (gx, 0, 0))
        for z in (-0.915, 0.915):
            s.box("Post", net, (0, 0.61, z), (0.09, 1.22, 0.09), (0.85, 0.08, 0.06), shape="Cylinder", metallic=0.4)
        s.box("Crossbar", net, (0, 1.2, 0), (0.09, 0.09, 1.92), (0.85, 0.08, 0.06), metallic=0.4)
        s.box("Base", net, (side * 0.55, 0.03, 0), (1.1, 0.06, 1.9), (0.85, 0.08, 0.06))
        mesh = s.box("Net", net, (side * 0.5, 0.6, 0), (1.0, 1.2, 1.83), (0.95, 0.95, 0.95))
        see_through(mesh, 0.45)
        # The lamp: a red dome on a grey box above the glass behind the net.
        lx = (HX + 0.3) * side
        lamp = s.group(f"{label} goal lamp", rink, (lx, 2.5, 0))
        s.box("Lamp housing", lamp, (0, 0.22, 0), (0.5, 0.44, 0.5), (0.3, 0.3, 0.32), metallic=0.5)
        s.box("Lamp dome (dark)", lamp, (0, 0.8, 0), (0.9, 0.9, 0.9), (0.35, 0.03, 0.03), shape="Sphere", rough=0.3)
        s.box("Lamp bracket", lamp, (0, -0.35, 0), (0.12, 0.7, 0.12), STEEL)
        lamps[side] = lamp

    # ---- the centre-ice riser
    s.slab("Stage deck", stage, -7.6, 7.6, 0, 1.8, 0.5, 9.8, (0.06, 0.06, 0.07))
    s.slab("Stage floor", stage, -7.6, 7.6, 1.8, 1.82, 0.5, 9.8, (0.1, 0.1, 0.11), rough=0.7)
    s.slab("Stage lip", stage, -7.6, 7.6, 1.72, 1.86, 0.42, 0.58, (0.25, 0.25, 0.27), metallic=0.4)
    s.slab("Kit riser", stage, -2.6, 2.6, 1.82, 2.42, 5.4, 9.2, (0.08, 0.08, 0.09))
    s.slab("Kit riser edge", stage, -2.62, 2.62, 2.36, 2.44, 5.36, 5.46, (0.85, 0.85, 0.82), emissive=(0.6, 0.6, 0.55),
           emissive_intensity=0.6, shadows=False)
    s.prop("Drum rug", stage, VM + "DrumRug.obj", (0, 2.43, 7.0), 0, 1.25)
    for i, (x, z, yaw) in enumerate([(-2.0, 8.7, 10), (2.0, 8.7, -10)]):
        s.prop(f"Kit road case {i}", stage, VM + "RoadCase.obj", (x, 2.42, z), yaw, 0.9)
    s.prop("Drum tech case", stage, VM + "FlightCaseWide.obj", (3.3, 1.82, 9.0), -8, 1.0)
    s.prop("Spare kit case", stage, VM + "FlightCaseWide.obj", (-3.4, 1.82, 9.1), 12, 1.0)
    s.prop("Power distro", stage, VM + "PowerDistro.obj", (6.6, 1.82, 9.3), -90, 1.0)
    s.prop("Drum fan", stage, VM + "StageFan.obj", (-2.2, 2.42, 6.0), 150, 1.0)
    # Backline: amp lines either side of the riser, wedges at the lip, side fills.
    for x, yaw in ((-5.0, 0), (5.0, 0)):
        for k in (-0.75, 0.75):
            s.prop("Cab", stage, VM + "GuitarCab.obj", (x + k, 1.82, 7.6), 180 + yaw, 1.4)
            s.prop("Head", stage, VM + "AmpHead.obj", (x + k, 1.82 + 1.05, 7.6), 180 + yaw, 1.4)
    s.prop("Keys rack", stage, VM + "AmpRack.obj", (-6.4, 1.82, 8.6), 180, 1.0)
    for x, yaw in ((-4.2, 8), (-1.0, 0), (1.0, 0), (4.2, -8), (0, 0)):
        z = 0.95 if x != 0 or yaw else 4.7
        s.prop("Wedge", stage, VM + "Wedge.obj", (x, 1.82, z), 180 + yaw, 1.5)
    for x in (-7.0, 7.0):
        s.prop("Side fill", stage, VM + "SpeakerTall.obj", (x, 1.82, 1.6), 180, 1.6)
    # Under-stage skirt of black scrim and the steps at the back.
    s.slab("Stage steps", stage, 7.6, 9.2, 0, 0.9, 7.5, 9.0, (0.1, 0.1, 0.11))
    s.slab("Stage steps upper", stage, 7.6, 8.4, 0.9, 1.8, 7.5, 9.0, (0.1, 0.1, 0.11))

    # The truss: a box of black truss over the riser with line arrays on its front corners.
    ty = 11.2
    for name, x0, x1, z0, z1 in [("Truss front", -9, 9, -0.6, -0.1), ("Truss back", -9, 9, 9.5, 10.0),
                                 ("Truss west", -9, -8.5, -0.6, 10.0), ("Truss east", 8.5, 9, -0.6, 10.0),
                                 ("Truss mid", -9, 9, 4.5, 5.0)]:
        s.slab(name, stage, x0, x1, ty, ty + 0.5, z0, z1, (0.07, 0.07, 0.08), metallic=0.5)
    for x in (-8.75, 8.75):
        for z in (-0.35, 9.75):
            s.box("Truss chain", stage, (x, (ty + 0.5 + 25.5) / 2, z), (0.04, 25.5 - ty - 0.5, 0.04), BLACK, shadows=False)
    for x in (-10.2, 10.2):
        for k in range(8):
            s.box("Line array box", stage, (x, ty - 0.45 - k * 0.52, 0.4), (1.2, 0.48, 0.8), (0.05, 0.05, 0.055),
                  rot=(-2 - k * 2.2, 8 if x < 0 else -8, 0))
        s.box("Line array frame", stage, (x, ty + 0.1, 0.4), (1.4, 0.2, 1.0), STEEL)
    for k in range(10):
        x = -8 + k * (16 / 9)
        s.box("Par can", stage, (x, ty - 0.25, -0.35), (0.3, 0.4, 0.3), BLACK, shape="Cylinder", shadows=False)

    # The glass ring round the riser: a run of rink boards and glass as the barricade.
    ring = [((-8.8, -0.9), (8.8, -0.9)), ((-8.8, -0.9), (-8.8, 9.2)), ((8.8, -0.9), (8.8, 9.2))]
    for i, (a, b) in enumerate(ring):
        ex, ez = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(ex, ez)
        yaw = yaw_of(ex, ez)
        cx, cz = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        brd = s.box(f"Riser boards {i}", rink, (cx, 0.535, cz), (ln, 1.07, 0.14), (1, 1, 1), rot=(0, yaw, 0), rough=0.6)
        textured(brd, TEX + "BoardAds.png", (max(1.0, round(ln / 14.0, 2)), 1))
        s.box(f"Riser cap {i}", rink, (cx, 1.09, cz), (ln + 0.1, 0.05, 0.2), CAP, rot=(0, yaw, 0))
        g = s.box(f"Riser glass {i}", rink, (cx, 1.6, cz), (ln, 1.0, 0.03), (0.7, 0.85, 0.92), rot=(0, yaw, 0), rough=0.05)
        see_through(g, 0.14)

    # Players' benches on the far side, either side of the riser, and the penalty box.
    for side, label in ((-1, "Home"), (1, "Visitors")):
        x0, x1 = sorted((side * 10.5, side * 18.5))
        s.slab(f"{label} bench floor", rink, x0, x1, 0, 0.18, 9.7, 11.4, (0.08, 0.08, 0.09))
        s.slab(f"{label} bench", rink, x0 + 0.2, x1 - 0.2, 0.18, 0.62, 10.9, 11.35, (0.45, 0.28, 0.14))
        s.slab(f"{label} bench boards", rink, x0, x1, 0, 1.07, 9.55, 9.7, BOARD)
        s.slab(f"{label} bench kick", rink, x0, x1, 0, 0.22, 9.5, 9.55, KICK)
        s.slab(f"{label} bench cap", rink, x0, x1, 1.05, 1.11, 9.48, 9.75, CAP)
        for k in range(3):
            s.prop(f"{label} water bottles", rink, VM + "Bottle.obj", (x0 + 1.5 + k * 2.6, 1.11, 9.62), 0, 1.0)

    # FOH: the desk on a low riser at the back of the floor.
    s.slab("FOH riser", stage, -2.2, 2.2, 0, 0.45, -11.2, -8.9, (0.08, 0.08, 0.09))
    s.slab("FOH desk", stage, -1.6, 1.6, 0.45, 1.3, -10.4, -9.6, (0.12, 0.12, 0.13))
    s.slab("FOH desk glow", stage, -1.5, 1.5, 1.3, 1.33, -10.3, -9.7, (0.1, 0.2, 0.3), emissive=(0.2, 0.45, 0.9),
           emissive_intensity=0.9, shadows=False)
    s.prop("FOH rack", stage, VM + "AmpRack.obj", (1.8, 0.45, -10.8), 180, 0.8)

    # Follow-spot gondolas hung in the near rafters, the operators' perches.
    gondolas = [(-14, 22.5, -30), (0, 23.5, -32), (14, 22.5, -30), (-34, 22.5, -12), (34, 22.5, -12)]
    for i, (x, y, z) in enumerate(gondolas):
        g = s.group(f"Gondola {i}", bowl, (x, y, z))
        s.box("Floor", g, (0, -0.6, 0), (3.0, 0.15, 2.0), STEEL, metallic=0.4)
        s.box("Rail", g, (0, 0, -0.95), (3.0, 1.0, 0.06), STEEL, metallic=0.4)
        s.box("Hanger", g, (0, 1.9, 0), (0.08, 3.8, 0.08), BLACK, shadows=False)
        s.box("Follow spot body", g, (0, 0.3, 0.2), (0.4, 0.4, 1.3), (0.12, 0.12, 0.13), rot=look_rotation((x, y, z), (0, 3, 4)), metallic=0.4)
        s.box("Follow spot lens", g, (0, 0.3, 0.2), (0.3, 0.3, 0.3), WARM, shape="Sphere", emissive=WARM, emissive_intensity=3, shadows=False)

    # ---- the kid in the enormous sweater, bouncing at the riser glass (stage left of the riser)
    kid_pos = (-9.75, 0.0, 0.6)
    kid = s.entity("The kid in the sweater", people, kid_pos, (0, 70, 0), (0.74,) * 3)
    bounce = s.entity("Bounce", kid)
    p = "SchoolBoy_01"
    s.entity("Legs", bounce).add({"Type": "Model", "ModelPath": f"{CROWD}{p}/Legs.obj"})
    torso = s.entity("Torso", bounce, (0, 0.8763, 0))
    torso.add({"Type": "Model", "ModelPath": f"{CROWD}{p}/Torso.obj"})
    s.entity("Head", torso, (0, 0.5727, -0.0242)).add({"Type": "Model", "ModelPath": f"{CROWD}{p}/Head.obj"})
    s.box("Sweater", torso, (0, 0.2, 0), (0.66, 0.78, 0.44), JERSEY, rough=0.95)
    s.box("Sweater stripe", torso, (0, -0.06, 0), (0.67, 0.12, 0.45), (0.95, 0.95, 0.93), rough=0.95)
    s.box("Sweater yoke", torso, (0, 0.53, 0), (0.6, 0.14, 0.42), (0.95, 0.95, 0.93), rough=0.95)
    s.box("Sweater number", torso, (0, 0.27, -0.225), (0.22, 0.26, 0.01), (0.95, 0.95, 0.93), rough=0.95)

    def sleeves(group, rot_l, rot_r):
        for side, rot in ((-1, rot_l), (1, rot_r)):
            a = s.entity("Sleeve arm", group, (side * 0.24, 0.5141, -0.0484), rot)
            s.box("Sleeve", a, (0, -0.42, 0), (0.2, 0.92, 0.2), JERSEY, rough=0.95)
            s.box("Sleeve stripe", a, (0, -0.7, 0), (0.21, 0.1, 0.21), (0.95, 0.95, 0.93), rough=0.95)
            s.box("Sleeve cuff", a, (0, -0.86, 0), (0.18, 0.06, 0.18), (0.95, 0.95, 0.93), rough=0.95)

    down = s.story("Sleeves hanging (until both ends are lit)", torso, "both_ends_lit", False, 0.25)
    sleeves(down, (0, 0, -6), (0, 0, 6))
    up = s.story("Sleeves up (both ends lit)", torso, "both_ends_lit", True, 0.25)
    sleeves(up, (-168, 0, -16), (-168, 0, 16))
    write_clip(os.path.join(folder, "Motion"), "KidBounce", 16, [
        {"Binding": "Kid", "Component": "Transform", "Property": "Position", "Keys": [
            {"Frame": 0, "Value": [0, 0, 0, 0], "Interpolation": "SmoothStep"},
            {"Frame": 8, "Value": [0, 0.16, 0, 0], "Interpolation": "SmoothStep"},
            {"Frame": 16, "Value": [0, 0, 0, 0], "Interpolation": "SmoothStep"}]}])
    kid.add({"Type": "Sequence", "Clip": MOTION + "KidBounce.sequence", "PlayOnStart": True, "Loop": True, "Speed": 1.0,
             "Bindings": [{"Slot": "Kid", "Target": bounce.guid}]})
    # A step stool the kid's standing on so the sweater clears the boards.
    s.prop("Milk crate", people, VM + "RoadCase.obj", (kid_pos[0], 0, kid_pos[2]), 20, 0.42)
    kid.add  # (the crate's 0.36 m high; lift the kid onto it)
    kid.components[0]["Position"][1] = 0.36

    # ---- the front row behind the west glass: the wave runs from the near corner to the home bench
    wave = s.group("The wave", people)
    seat = seat_tops[0]
    row_d = (seat[0] + seat[1]) / 2 - 0.25
    fans = []
    for i, (a, b) in enumerate(edges(row_d)):
        if i not in (1, 2, 3, 4):
            continue
        ex, ez = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(ex, ez)
        if i == 1:  # far side: from the corner along to the home bench only
            t0, t1 = 0.55, 1.0
        elif i == 4:  # near side: just the corner run
            t0, t1 = 0.0, 0.35
        else:
            t0, t1 = 0.0, 1.0
        n = max(2, int(ln * (t1 - t0) / 1.05))
        for k in range(n):
            t = t0 + (t1 - t0) * (k + 0.5) / n
            fans.append((i, a[0] + ex * t, a[1] + ez * t))
    # Order the run from the near-side corner (nearest the kid) round to the home bench.
    order = {4: 0, 3: 1, 2: 2, 1: 3}
    fans.sort(key=lambda f: (order[f[0]], f[2] if f[0] == 3 else (-f[2] if f[0] == 2 else (f[1] if f[0] == 4 else -f[1]))))
    fans.sort(key=lambda f: order[f[0]])
    fans = [f for f in fans]
    people_cast = ["Mother_01", "Son_01", "Daughter_01", "ShopKeeper_01", "Mother_02", "Rigged", "SchoolGirl_01", "SchoolBoy_01"]
    wave_frames = 150
    tracks = []
    bindings = []
    for k, (edge, x, z) in enumerate(fans):
        person = people_cast[(k * 5 + 3) % len(people_cast)]
        facing = math.degrees(math.atan2(0 - x, 3 - z))
        f = fan(s, wave, f"Front row {k + 1:02}", person, (x, seat[2], z), facing, 0.95 + 0.08 * ((k * 7) % 3) / 2)
        still = s.story("Arms down", f, "board_wave", False, 0.2)
        for side in (-1, 1):
            arm(s, still, person, side, (0, 0, side * 6))
        going = s.story("Arms up for the wave", f, "board_wave", True, 0.2)
        pair = []
        for side in (-1, 1):
            a = arm(s, going, person, side, (0, 0, side * 6))
            if (k + side) % 2 == 0:
                towel = s.entity("Towel", a, (0, -0.7, 0))
                s.box("Towel cloth", towel, (0, -0.3, 0.03), (0.55, 0.8, 0.02), (0.97, 0.97, 0.95), rough=1.0,
                      emissive=(1, 1, 1), emissive_intensity=0.35)
            pair.append(a)
        # The wave: each fan's arms go up a few frames after the last one's.
        t0 = 4 + k * 3
        for side, a in zip((-1, 1), pair):
            slot = f"Fan{k:02}{'L' if side < 0 else 'R'}"
            bindings.append({"Slot": slot, "Target": a.guid})
            down_q = quat((0, 0, side * 6))
            up_q = quat((-165, 0, side * 18))
            keys = [{"Frame": 0, "Value": down_q, "Interpolation": "SmoothStep"},
                    {"Frame": t0, "Value": down_q, "Interpolation": "SmoothStep"},
                    {"Frame": t0 + 7, "Value": up_q, "Interpolation": "SmoothStep"},
                    {"Frame": t0 + 15, "Value": up_q, "Interpolation": "SmoothStep"},
                    {"Frame": t0 + 24, "Value": down_q, "Interpolation": "SmoothStep"},
                    {"Frame": wave_frames, "Value": down_q, "Interpolation": "SmoothStep"}]
            keys = sorted({kk["Frame"]: kk for kk in keys if kk["Frame"] <= wave_frames}.values(), key=lambda kk: kk["Frame"])
            tracks.append({"Binding": slot, "Component": "Transform", "Property": "Rotation", "Keys": keys})
    wave_light = story_at(s, "Light on the wave", story, "board_wave", True, 0.5, (-HX, 2.0, 0))
    for i, (src, to) in enumerate([((-14.0, 9.0, -6.0), (-27.5, 2.0, -6.0)), ((-14.0, 9.0, 4.0), (-27.5, 2.0, 4.0)),
                                   ((-15.0, 9.0, 4.0), (-14.0, 2.0, 12.5))]):
        s.light(f"Warm on the front row {i}", wave_light, src, "Spot", (1.0, 0.88, 0.7), 1600.0, 22,
                rot=look_rotation(src, to), inner=18, outer=32)
    wave_frames = max(wave_frames, 4 + len(fans) * 3 + 30)
    for t in tracks:
        t["Keys"][-1]["Frame"] = wave_frames
    write_clip(os.path.join(folder, "Motion"), "BoardWave", wave_frames, tracks)
    wave.add({"Type": "Sequence", "Clip": MOTION + "BoardWave.sequence", "PlayOnStart": True, "Loop": True, "Speed": 1.0,
              "Bindings": bindings})

    # ---- story: the goal lamps
    for side, flag, label in ((-1, "goal_lamp_on", "West"), (1, "both_ends_lit", "East")):
        lx = (HX + 0.3) * side
        g = story_at(s, f"{label} goal lamp lit ({flag})", story, flag, True, 0.35, (lx, 3.2, 0))
        s.box("Lamp dome (lit)", g, (lx, 3.3, 0), (1.0, 1.0, 1.0), GOALRED, shape="Sphere", emissive=GOALRED, emissive_intensity=6.0, shadows=False)
        halo = s.box("Lamp halo", g, (lx, 3.3, 0), (3.0, 3.0, 3.0), GOALRED, shape="Sphere", emissive=GOALRED, emissive_intensity=2.0, shadows=False)
        see_through(halo, 0.25, additive=True)
        s.light("Goal lamp glow", g, (lx - side * 0.8, 3.4, 0), "Point", GOALRED, 900.0, 22)
        s.light("Goal lamp on the end seats", g, (lx - side * 1.0, 3.0, 0), "Spot", GOALRED, 2600.0, 30,
                rot=look_rotation((lx, 3, 0), (lx + side * 12, 8, 0)), inner=40, outer=70)
        # A red goal-light pole lamp up on the scoreboard skirt too, so the light reads from the high seats.
        s.box("Scoreboard goal light", g, (side * 3.0, 18.2, 0.5), (0.5, 0.5, 0.5), GOALRED, shape="Sphere",
              emissive=GOALRED, emissive_intensity=6.0, shadows=False)
        if side < 0:
            # The west lamp's red finds the kid at the riser glass.
            s.light("Red on the kid", g, (-15.5, 5.5, -3.0), "Spot", GOALRED, 2400.0, 16,
                    rot=look_rotation((-15.5, 5.5, -3.0), (kid_pos[0], 1.1, kid_pos[2])), inner=8, outer=16)
        else:
            # Both ends lit: red beams trade across the stage from each end.
            for sx in (-1, 1):
                src = (sx * 25.0, 3.8, 0.0)
                to = (-sx * 6.0, 10.0, 5.0)
                aim = look_rotation(src, to)
                s.light(f"Cross beam from {'west' if sx < 0 else 'east'}", g, src, "Spot", GOALRED, 6000.0, 34,
                        rot=aim, inner=6, outer=12)
                mid = tuple((src[i] + to[i]) / 2 for i in range(3))
                shaft = s.box("Cross beam shaft", g, mid, (0.6, math.dist(src, to) * 0.96, 0.6),
                              GOALRED, rot=(aim[0] + 90, aim[1], 0), shape="Cylinder", emissive=GOALRED,
                              emissive_intensity=1.0, shadows=False)
                see_through(shaft, 0.06, additive=True)

    # ---- story: the banner going up, then dropping
    bx, bz = 0.0, -3.4
    batten_y = 18.0
    s.box("Banner batten", bowl, (bx, batten_y + 0.1, bz), (5.0, 0.16, 0.16), STEEL, metallic=0.5)
    for x in (-2.3, 2.3):
        s.box("Batten cable", bowl, (x, (batten_y + 25.8) / 2, bz), (0.03, 25.8 - batten_y, 0.03), BLACK, shadows=False)
    rigged = story_at(s, "Banner rigged (banner_rigged)", story, "banner_rigged", True, 1.2, (bx, batten_y, bz))
    furl = story_at(s, "The furl, until it drops", rigged, "banner_dropped", False, 0.35, (bx, batten_y - 3.0, bz))
    roll_y = batten_y - 3.0
    roll = s.box("Furled banner", furl, (bx, roll_y, bz), (4.4, 0.55, 0.55), (1, 1, 1), rot=(0, 0, 90), shape="Cylinder")
    material(roll)  # the cylinder's axis is local y: turned 90 about z it lies along x
    textured(roll, TEX + "Furled.png", (1, 3))
    for x in (-1.6, 0, 1.6):
        s.box("Furl tie", furl, (bx + x, roll_y, bz), (0.08, 0.6, 0.6), (0.55, 0.1, 0.08), rot=(0, 0, 90), shape="Cylinder", shadows=False)
    for x in (-1.9, 1.9):
        s.box("Hoist rope", furl, (bx + x, (roll_y + batten_y) / 2, bz), (0.035, batten_y - roll_y, 0.035), (0.8, 0.72, 0.55), shadows=False)
    corner = s.box("Loose corner", furl, (bx + 1.85, roll_y - 0.75, bz - 0.05), (0.7, 1.2, 0.03), (1, 1, 1), rot=(0, 0, 12))
    textured(corner, TEX + "YourBand.png", (0.25, 0.3))
    spot_src = (0.0, 23.5, -32.0)
    s.light("Follow spot on the furl", furl, spot_src, "Spot", (1.0, 0.92, 0.8), 30000.0, 40,
            rot=look_rotation(spot_src, (bx, roll_y, bz)), inner=2.5, outer=4.5)
    shaft = s.box("Follow spot shaft", furl, ((spot_src[0] + bx) / 2, (spot_src[1] + roll_y) / 2, (spot_src[2] + bz) / 2),
                  (1.0, math.dist(spot_src, (bx, roll_y, bz)) * 0.9, 1.0), (1.0, 0.92, 0.8),
                  rot=[look_rotation(spot_src, (bx, roll_y, bz))[0] + 90, look_rotation(spot_src, (bx, roll_y, bz))[1], 0], shape="Cylinder",
                  emissive=(1.0, 0.92, 0.8), emissive_intensity=1.0, shadows=False)
    see_through(shaft, 0.06, additive=True)
    pool = s.box("Spot pool on the furl", furl, (bx, roll_y, bz - 0.35), (2.6, 2.6, 0.02), (1, 0.95, 0.85), shape="Sphere",
                 emissive=(1, 0.95, 0.85), emissive_intensity=1.0, shadows=False)
    see_through(pool, 0.12, additive=True)

    dropped = story_at(s, "Banner dropped (banner_dropped)", story, "banner_dropped", True, 0.6, (bx, batten_y, bz))
    bw, bh = 4.6, 7.6
    ban = s.box("YOUR BAND banner", dropped, (bx, batten_y - bh / 2, bz), (bw, bh, 0.05), (1, 1, 1), rough=0.9)
    textured(ban, TEX + "YourBand.png", emissive=(0.22, 0.22, 0.25), intensity=1.0)
    s.box("Banner bottom bar", dropped, (bx, batten_y - bh - 0.05, bz), (bw + 0.2, 0.12, 0.12), STEEL)
    s.light("Banner key from the gondola", dropped, spot_src, "Spot", (1.0, 0.95, 0.88), 1400.0, 45,
            rot=look_rotation(spot_src, (bx, batten_y - bh / 2, bz)), inner=5, outer=8)
    s.light("Banner wash west", dropped, (-12, 14, -16), "Spot", (0.85, 0.9, 1.0), 900.0, 26,
            rot=look_rotation((-12, 14, -16), (bx, batten_y - bh / 2, bz)), inner=6, outer=12)
    s.light("Banner wash east", dropped, (12, 14, -16), "Spot", (1.0, 0.85, 0.75), 900.0, 26,
            rot=look_rotation((12, 14, -16), (bx, batten_y - bh / 2, bz)), inner=6, outer=12)
    # Streamers coming down with it.
    cols = [(0.95, 0.1, 0.1), (0.95, 0.95, 0.95), (0.1, 0.25, 0.8)]
    for k in range(36):
        x = -9 + (k * 37 % 19)
        z = -9 + (k * 23 % 13)
        y = 5.0 + (k * 13 % 9)
        s.box("Streamer", dropped, (x, y, z), (0.08, 0.9, 0.01), cols[k % 3], rot=(k * 31 % 60 - 30, k * 47 % 180, k * 17 % 50 - 25),
              emissive=cols[k % 3], emissive_intensity=0.6, shadows=False)

    # ---- lights: one shadowed key, the house glow, the show rig
    s.light("House key from the roof", lights, (0, 40, 0), "Directional", (1.0, 0.86, 0.7), 0.55, rot=(62, 28, 0), shadows=True)
    for i, (x, z) in enumerate([(-30, 0), (30, 0), (0, 26), (0, -26), (-20, -18), (20, -18), (-20, 18), (20, 18)]):
        s.light(f"House glow {i}", lights, (x, 22, z), "Point", WARM, 700.0, 34)
    for i, (x, z) in enumerate([(-14, -6), (14, -6), (-18, 6), (18, 6)]):
        s.light(f"Ice spill {i}", lights, (x, 9, z), "Point", (0.75, 0.85, 1.0), 260.0, 16)
    # Washes from the truss (10).
    for i in range(10):
        x = -7.5 + i * (15 / 9)
        z = -0.35 if i % 2 == 0 else 4.75
        col = [(1.0, 0.55, 0.25), (0.35, 0.5, 1.0), (1.0, 0.3, 0.45)][i % 3]
        s.light(f"Truss wash {i}", lights, (x, ty - 0.2, z), "Spot", col, 2600.0, 18,
                rot=look_rotation((x, ty, z), (x * 0.6, 1.8, z + 2.5)), inner=22, outer=40, show="Wash", group=i % 3)
    # Movers on the truss sweeping out over the crowd (10).
    for i in range(10):
        x = -8 + i * (16 / 9)
        z = 9.75 if i % 2 else -0.35
        to = (x * 2.2, 6.0 + (i % 3) * 4, -20 if i % 2 == 0 else -12)
        col = [(0.6, 0.75, 1.0), (1.0, 0.8, 0.55)][i % 2]
        s.light(f"Mover {i}", lights, (x, ty - 0.3, z), "Spot", col, 9000.0, 40, rot=look_rotation((x, ty, z), to),
                inner=3, outer=7, show="Beam", group=i % 2)
    # Follow spots from the gondolas (5).
    for i, (x, y, z) in enumerate(gondolas):
        s.light(f"Follow spot {i}", lights, (x, y + 0.3, z + 0.6), "Spot", (1.0, 0.93, 0.84), 14000.0, 60,
                rot=look_rotation((x, y, z), (0, 2.5, 4)), inner=3.5, outer=6, show="Spot", group=i)
    # Blinders on the truss front and the end glass (6).
    for i, (pos, to) in enumerate([((-6, ty - 0.5, -0.6), (-8, 2, -10)), ((6, ty - 0.5, -0.6), (8, 2, -10)),
                                   ((-2, ty - 0.5, -0.6), (-2, 2, -10)), ((2, ty - 0.5, -0.6), (2, 2, -10)),
                                   ((-24, 3, -6), (-8, 3, -6)), ((24, 3, -6), (8, 3, -6))]):
        s.light(f"Blinder {i}", lights, pos, "Spot", (1.0, 0.8, 0.55), 3500.0, 22, rot=look_rotation(pos, to),
                inner=25, outer=50, show="Blinder", group=i % 2)
    # Strobes (4).
    for i, x in enumerate((-7, -2.5, 2.5, 7)):
        s.light(f"Strobe {i}", lights, (x, ty - 0.4, 9.75), "Point", (0.9, 0.95, 1.0), 2500.0, 20, show="Strobe", group=i % 2)
    # The scoreboard's own glow down onto the stage (static, cued only by itself).

    # ---- markers
    s.info(marks, "Home Ice at Maple Leaf Gardens", "Drumsmith", room_back=-(HZ + back_d) + 0.5, room_ceiling=25.5,
           half_width=HX + back_d - 0.5, desk_z=-10.0, ambient=(0.03, 0.022, 0.016), fog_color=(0.025, 0.02, 0.016), haze=0.55)
    s.spot(marks, "Drummer", (0, 2.42, 7.6))
    s.spot(marks, "Vocals", (0, 1.82, 2.2))
    s.spot(marks, "Guitar", (-4.3, 1.82, 3.6))
    s.spot(marks, "Bass", (4.3, 1.82, 3.8))
    s.spot(marks, "Keys", (-6.2, 1.82, 7.2), -20)

    # The floor: posed front rows at the glass ring, mobs behind and down the sides of the riser.
    crowd = s.group("Crowd", marks)
    s.crowd("Front of the glass", crowd, (0, 0, -3.4), 17.0, 4.0, 110, figures="Posed")
    s.crowd("Floor middle", crowd, (0, 0, -7.0), 34.0, 3.2, 300)
    s.crowd("Floor back west", crowd, (-10.5, 0, -9.8), 16.0, 2.6, 130)
    s.crowd("Floor back east", crowd, (10.5, 0, -9.8), 16.0, 2.6, 130)
    s.crowd("Floor front west", crowd, (-13.2, 0, -3.4), 8.8, 4.0, 90)
    s.crowd("Floor front east", crowd, (13.2, 0, -3.4), 8.8, 4.0, 90)
    s.crowd("Beside the riser west", crowd, (-14.6, 0, 3.6), 7.0, 8.4, 110)
    s.crowd("Beside the riser east", crowd, (14.6, 0, 3.6), 7.0, 8.4, 110)

    # The bowl, sold out. Long sides and ends per step; the corners as squares along the diagonal.
    # The first west row and its corners are the wave's people, not the mob's.
    bowl_marks = s.group("Bowl crowd", marks)
    total = 0

    def seat_area(name, x0, x1, z0, z1, y, density=1.0):
        nonlocal total
        w, d = x1 - x0, z1 - z0
        if w < 0.8 or d < 0.8:
            return
        heads = int(w * d / (0.58 * 0.85) * 0.92 * density)
        total += heads
        s.crowd(name, bowl_marks, ((x0 + x1) / 2, y, (z0 + z1) / 2), w, d, heads, 0.25)

    rows = [(d0, d1, top, k) for k, (d0, d1, top) in enumerate(seat_tops)] + \
           [(d0, d1, top, 8 + k) for k, (d0, d1, top) in enumerate(upper)]
    for d0, d1, top, k in rows:
        a0, a1 = d0 + 0.15, d1 - 0.15
        sx = HX - CH  # straight run of the long sides
        sz = HZ - CH  # straight run of the ends
        dens = 1.0 if k < 8 else 0.85
        # Long sides: split by aisles.
        for zs, label in ((1, "far"), (-1, "near")):
            z0, z1 = sorted((zs * (HZ + a0), zs * (HZ + a1)))
            cuts = [-sx, -sx * 0.6 + 0.6, -sx * 0.6 - 0.6 + 1.2, 0.6 - 0.6, 0.0, sx * 0.6 - 0.6, sx * 0.6 + 0.6, sx]
            for x0, x1 in [(-sx, -sx * 0.6 - 0.6), (-sx * 0.6 + 0.6, -0.6), (0.6, sx * 0.6 - 0.6), (sx * 0.6 + 0.6, sx)]:
                if k == 0 and label == "far" and x1 < -8:
                    continue  # the home-bench end of the front row is the wave's
                if k == 0 and label == "near" and x1 < -8:
                    continue
                seat_area(f"Bowl {label} {k} {x0:.0f}", x0, x1, z0, z1, top, dens)
            del cuts
        for xs, label in ((-1, "west"), (1, "east")):
            if k == 0 and label == "west":
                continue
            x0, x1 = sorted((xs * (HX + a0), xs * (HX + a1)))
            for z0, z1 in [(-sz, -0.6), (0.6, sz)]:
                seat_area(f"Bowl {label} {k} {z0:.0f}", x0, x1, z0, z1, top, dens)
        # Corners: squares stepped along the chamfer.
        mid = (a0 + a1) / 2
        for cx, cz in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
            if k == 0 and cx < 0:
                continue
            for t in (0.18, 0.5, 0.82):
                # point on the chamfer edge at offset mid
                ax, az = cx * (HX - CH), cz * HZ
                bx_, bz_ = cx * HX, cz * (HZ - CH)
                px = ax + (bx_ - ax) * t + cx * mid * 0.7071
                pz = az + (bz_ - az) * t + cz * mid * 0.7071
                half = 1.15
                seat_area(f"Bowl corner {cx}{cz} {k} {t}", px - half, px + half, pz - half, pz + half, top, dens)

    # ---- cameras
    cams = s.group("Cameras", marks)
    shots = [
        ("Wide from the reds", "Wide", (0, 11.8, -24.6), (0, 5.4, 3.0), 74, ""),
        ("Crane over the floor", "Crane", (-17, 14.5, -19), (0, 3.5, 4.5), 56, ""),
        ("Desk long lens", "Desk", (1.2, 3.2, -10.0), (0, 3.4, 6.0), 30, ""),
        ("Sticks", "Close", (2.3, 3.7, 4.6), (0, 3.0, 7.6), 44, "drummer"),
        ("Kid at the glass", "Custom", (-5.6, 2.8, -6.2), (-12.5, 2.2, 1.0), 48, "kid"),
        ("Goal lamp west", "Custom", (-11.0, 6.0, -9.0), (-26.0, 3.0, 0.0), 52, "goal-lamp"),
        ("Across both ends", "Custom", (0, 20.0, -35.0), (0, 3.0, 1.0), 74, "both-ends"),
        ("Along the west glass", "Custom", (-17.0, 3.2, -9.5), (-26.5, 2.0, 6.0), 58, "wave"),
        ("Up at the banner", "Custom", (6.0, 12.5, -24.6), (0.0, 17.5, -3.4), 50, "banner"),
        ("Rafters and scoreboard", "Custom", (14.0, 11.2, -22.0), (0.0, 17.0, 0.0), 50, "rafters"),
        ("From the home bench", "Custom", (-14.0, 2.0, 10.4), (-1.0, 3.0, 4.0), 50, "bench"),
    ]
    for name, kind, eye, aim, fov, tag in shots:
        s.camera_spot(name, cams, eye, aim, kind, fov, tag)
    walk = [((-24.2, 1.7, -7.8), (-22.6, 1.0, -1.0), 70), ((-22.0, 1.7, -7.0), (-14.0, 2.4, 0.0), 68),
            ((-19.0, 1.75, -6.0), (-6.0, 3.0, 4.0), 66), ((-16.0, 1.8, -4.6), (-2.0, 3.2, 5.0), 64),
            ((-13.0, 1.85, -3.6), (0.0, 3.2, 6.0), 62), ((-11.0, 1.9, -2.4), (0.0, 3.0, 6.5), 60)]
    for i, (eye, aim, fov) in enumerate(walk):
        s.camera_spot(f"Arrival {i + 1:02}", cams, eye, aim, "Custom", fov, f"arrival/{i + 1:02}")
    return s, total


def main():
    folder = os.path.join(repo_root(), "Assets", "Venues", ID)
    if "--textures" in sys.argv or not os.path.exists(os.path.join(folder, "Textures", "Ice.png")):
        import story_gardens_textures
        story_gardens_textures.main()
    scene, heads = build(folder)
    scene.write(os.path.join(folder, f"{ID}.lvl"))
    preview = "Preview.jpg" if os.path.exists(os.path.join(folder, "Preview.jpg")) else None
    write_venue_json(folder, "Home Ice at Maple Leaf Gardens", f"{ID}.lvl", preview=preview, ambience="Assets/Sounds/crowd.mp3")
    shows = sum(1 for e in scene.entities for c in e.components if c.get("Type") == "VenueShowLight")
    print(f"{len(scene.entities)} entities, {shows} show lights, {heads} seated heads -> {folder}")


if __name__ == "__main__":
    main()
