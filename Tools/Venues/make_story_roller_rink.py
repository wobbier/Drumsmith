#!/usr/bin/env python3
"""Writes Assets/Venues/StoryRollerRink/: story set 06, "Adults Only at the Roller Rink".

    python3 Tools/Venues/make_story_roller_rink.py

The Moonbeam Rollerdrome on adults' night: an oval maple floor with a painted lane line inside a
carpeted rail, the DJ booth at the far end where the band has squeezed in (drums behind the
turntables, bass and guitar either side), a mirror ball over the centre, neon round the walls, the
skate rental counter on the left and the snack bar on the right.

The story (Design/Story-Mode-Setlists.json, s06-roller-rink):
  newcomer_at_rail  the last orange rentals leave the counter; the learner clings to the rail
  rail_lit          a second pool of light (and the rail's neon) picks out that stretch of rail
  rail_empty        the learner is out on the inside lane; the mirror ball starts turning
  three_abreast     the silver jackets and the learner share one lap, pairs falling in behind
  circle_open       a circle opens under the ball: the learner upright in the middle, hands up
Deterministic: rerun = same bytes (textures need ImageMagick; without it the PNGs on disk stay).
"""
import hashlib
import math
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
from venuegen import Scene, look_rotation, write_venue_json  # noqa: E402
from story_roller_rink_meshes import LOCAL, MODELS, VENUE, Mesh, ellipse, save  # noqa: E402
import story_roller_rink_skaters as sk  # noqa: E402
import story_roller_rink_textures as tx  # noqa: E402

ID = "StoryRollerRink"
TITLE = "Adults Only at the Roller Rink"
SYNTY = "/home/mitch/Projects/MitchGame/Assets/Models/Synty"

# The rink: an oval centred at (CX, CZ), semi-axes A (x) and B (z).
CX, CZ, A, B = 0.0, -7.0, 12.5, 7.0
OUTER = (11.35, 5.85)        # the featured skaters' lane
INNER = (4.6, 3.1)           # the learner's inside lane
CIRCLE_R = 2.8               # the painted centre circle
RAIL_T = math.radians(148)   # where the newcomer holds the rail (upper left in the wide)
ROOM_X, ROOM_BACK, ROOM_FRONT, CEIL = 17.0, -22.0, 12.0, 8.0
DECK_Y, DECK_Z0 = 0.6, 0.9

PINK = (1.0, 0.18, 0.6)
CYAN = (0.16, 0.9, 1.0)
AMBER = (1.0, 0.62, 0.28)
VIOLET = (0.55, 0.24, 1.0)
GOLD = (1.0, 0.82, 0.35)
WARM = (1.0, 0.8, 0.6)


def tex(path):
    return {"Path": LOCAL + path, "RenderMode": "Opaque"}


def tbox(s, name, parent, pos, size, texture, tiling=(1, 1), glow=0.0, color=(1, 1, 1), rot=(0, 0, 0)):
    """A primitive box with a texture (and optionally the same texture glowing)."""
    e = s.box(name, parent, pos, size, color, rot=rot, rough=0.85,
              emissive=(1, 1, 1) if glow else None, emissive_intensity=glow, shadows=not glow)
    mat = e.components[-1]["Material"]
    mat["Textures"] = {"Diffuse": tex(texture)}
    if glow:
        mat["Textures"]["Emissive"] = tex(texture)
    mat["Tiling"] = [float(tiling[0]), float(tiling[1])]
    return e


def neon(s, name, parent, a, b, color, power=3.0, r=0.035):
    """A glowing tube from a to b (a cylinder primitive turned onto the segment)."""
    mid = tuple((x + y) / 2 for x, y in zip(a, b))
    d = [y - x for x, y in zip(a, b)]
    length = math.sqrt(sum(c * c for c in d))
    yaw = math.degrees(math.atan2(d[0], d[2]))
    pitch = math.degrees(math.atan2(math.hypot(d[0], d[2]), d[1]))
    return s.box(name, parent, mid, (r * 2, length, r * 2), color, rot=(pitch, yaw, 0), emissive=color,
                 emissive_intensity=power, shadows=False, shape="Cylinder")


def sign_quad(name, texture, w, h, glow=0.0):
    """A one-sided picture quad, w x h metres, facing -z (toward the crowd), centred on its pivot."""
    m = Mesh(name, f"{texture} on a {w} x {h} m quad facing the crowd.")
    mat = "pic"
    m.textured(mat, texture)
    pts = [(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)]
    m.face(pts, mat + (f"@{glow:g}" if glow else ""), hint=(0, 0, -1), uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    return m.write()


# ---- meshes ---------------------------------------------------------------------------------------
def rink_floor():
    x0, x1, z0, z1 = CX - A - 0.1, CX + A + 0.1, CZ - B - 0.1, CZ + B + 0.1
    m = Mesh("RinkFloor", "The maple oval: boards, the painted lane line and centre circle (Maple.png, planar).")
    m.textured("maple", "Maple.png")
    uv = lambda x, z: ((x - x0) / (x1 - x0), (z - z0) / (z1 - z0))
    n = 120
    top = 0.04
    for k in range(n):
        t0, t1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        (ax, az), (bx, bz) = ellipse(CX, CZ, A, B, t0), ellipse(CX, CZ, A, B, t1)
        m.face([(CX, top, CZ), (ax, top, az), (bx, top, bz)], "maple", (0, 1, 0),
               [uv(CX, CZ), uv(ax, az), uv(bx, bz)])
        m.face([(ax, 0, az), (bx, 0, bz), (bx, top, bz), (ax, top, az)], "maple_dark", (ax - CX, 0, az - CZ))
    return m.write()


def rail(gaps):
    """The carpeted knee wall round the oval with a walnut cap and a chrome hand rail on posts."""
    m = Mesh("RinkRail", "The carpeted rail round the oval: knee wall, walnut cap, chrome rail and posts.")
    m.textured("carpet", "Carpet.png")
    n = 160
    h, cap, rail_h = 0.92, 0.05, 1.08
    inner, outer = (A + 0.05, B + 0.05), (A + 0.27, B + 0.27)
    arc = 0.0
    prev = None
    for k in range(n):
        t0, t1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        tm = (t0 + t1) / 2
        if any(g0 <= tm % (2 * math.pi) <= g1 for g0, g1 in gaps):
            prev = None
            continue
        i0, i1 = ellipse(CX, CZ, *inner, t0), ellipse(CX, CZ, *inner, t1)
        o0, o1 = ellipse(CX, CZ, *outer, t0), ellipse(CX, CZ, *outer, t1)
        seg = math.hypot(o1[0] - o0[0], o1[1] - o0[1])
        u0, u1 = arc / 1.4, (arc + seg) / 1.4
        arc += seg
        out = (o0[0] - CX, 0, o0[1] - CZ)
        m.face([(o0[0], 0, o0[1]), (o1[0], 0, o1[1]), (o1[0], h, o1[1]), (o0[0], h, o0[1])], "carpet", out,
               [(u0, 0), (u1, 0), (u1, h / 1.4), (u0, h / 1.4)])
        m.face([(i0[0], 0.04, i0[1]), (i1[0], 0.04, i1[1]), (i1[0], h, i1[1]), (i0[0], h, i0[1])], "carpet",
               (CX - i0[0], 0, CZ - i0[1]), [(u0, 0), (u1, 0), (u1, h / 1.4), (u0, h / 1.4)])
        m.face([(i0[0], h + cap, i0[1]), (i1[0], h + cap, i1[1]), (o1[0], h + cap, o1[1]), (o0[0], h + cap, o0[1])],
               "walnut", (0, 1, 0))
        m.face([(i0[0], h, i0[1]), (i1[0], h, i1[1]), (i1[0], h + cap, i1[1]), (i0[0], h + cap, i0[1])], "walnut",
               (CX - i0[0], 0, CZ - i0[1]))
        m.face([(o0[0], h, o0[1]), (o1[0], h, o1[1]), (o1[0], h + cap, o1[1]), (o0[0], h + cap, o0[1])], "walnut", out)
        mid0, mid1 = ellipse(CX, CZ, A + 0.16, B + 0.16, t0), ellipse(CX, CZ, A + 0.16, B + 0.16, t1)
        m.tube((mid0[0], rail_h, mid0[1]), (mid1[0], rail_h, mid1[1]), 0.03, 0.03, "chrome", 6, caps=False)
        if k % 5 == 0:
            m.tube((mid0[0], h + cap, mid0[1]), (mid0[0], rail_h, mid0[1]), 0.018, 0.018, "chrome", 6)
        if prev is None:   # an end: close it
            m.face([(i0[0], 0, i0[1]), (o0[0], 0, o0[1]), (o0[0], h + cap, o0[1]), (i0[0], h + cap, i0[1])], "walnut",
                   (-(o0[1] - CZ) / B, 0, (o0[0] - CX) / A))
        prev = k
        nxt = ((k + 1.5) / n) * 2 * math.pi
        if any(g0 <= nxt % (2 * math.pi) <= g1 for g0, g1 in gaps) or k == n - 1:
            m.face([(i1[0], 0, i1[1]), (o1[0], 0, o1[1]), (o1[0], h + cap, o1[1]), (i1[0], h + cap, i1[1])], "walnut",
                   ((o1[1] - CZ) / B, 0, -(o1[0] - CX) / A))
    return m.write()


def rail_neon(t0, t1, name, ink):
    """A glowing strip along the outside face of the rail between two angles."""
    m = Mesh(name, "A neon strip along the rail's face.")
    n = 24
    for k in range(n):
        a0 = t0 + (t1 - t0) * k / n
        a1 = t0 + (t1 - t0) * (k + 1) / n
        for rr, side in ((0.30, 1), (0.02, -1)):
            p0, p1 = ellipse(CX, CZ, A + rr, B + rr, a0), ellipse(CX, CZ, A + rr, B + rr, a1)
            m.face([(p0[0], 0.74, p0[1]), (p1[0], 0.74, p1[1]), (p1[0], 0.80, p1[1]), (p0[0], 0.80, p0[1])], ink,
                   (side * (p0[0] - CX), 0, side * (p0[1] - CZ)))
    return m.write()


def mirror_ball(name):
    m = Mesh(name, "The mirror ball: faceted, alternating mirror tiles, 1.1 m across, pivot at its centre.")
    inks = ["mirror@1.4", "chrome", "silver@0.6", "glass@0.9", "steel", "mirror@2.2", "chrome", "silver"]
    m.sphere((0, 0, 0), 0.75, inks, sides=20, bands=12, ink_fn=lambda i, j: inks[(i * 3 + j * 5) % len(inks)])
    m.tube((0, 0.7, 0), (0, 0.82, 0), 0.06, 0.06, "steel", 8)
    return m.write()


def spangles():
    """The ball's reflections: little glowing squares scattered over the floor and the walls' feet,
    around the ball's axis (pivot at the ball's foot on the floor)."""
    import random
    rnd = random.Random(66)
    m = Mesh("Spangles", "Mirror-ball spangles: glowing flecks on the floor, centred on the ball's axis.")
    inks = ["white@4", "cyan@4", "hotpink@4", "yellow@3.5", "white@4", "glass@4"]
    for i in range(170):
        r = math.sqrt(rnd.random()) * 15.5
        t = rnd.uniform(0, 2 * math.pi)
        x, z = r * math.cos(t), r * math.sin(t) * 0.75
        sz = rnd.uniform(0.07, 0.15)
        y = 0.055 if (x / A) ** 2 + (z / B) ** 2 < 1 else 0.015
        rot = rnd.uniform(0, math.pi)
        c, s_ = math.cos(rot) * sz, math.sin(rot) * sz
        m.face([(x - c, y, z - s_), (x - s_, y, z + c), (x + c, y, z + s_), (x + s_, y, z - c)], inks[i % len(inks)], (0, 1, 0))
    # And a band of flecks on the ceiling.
    for i in range(70):
        r = rnd.uniform(1.5, 12)
        t = rnd.uniform(0, 2 * math.pi)
        x, z = r * math.cos(t), r * math.sin(t) * 0.8
        sz = rnd.uniform(0.08, 0.16)
        y = CEIL - 0.32
        m.face([(x - sz, y, z - sz), (x + sz, y, z - sz), (x + sz, y, z + sz), (x - sz, y, z + sz)], inks[i % len(inks)], (0, -1, 0))
    return m.write()


def floor_ring(name, r, width, ink):
    m = Mesh(name, "A glowing ring on the floor.")
    n = 64
    for k in range(n):
        t0, t1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        p = lambda rr, t: (rr * math.cos(t), 0.06, rr * math.sin(t))
        m.face([p(r - width / 2, t0), p(r - width / 2, t1), p(r + width / 2, t1), p(r + width / 2, t0)], ink, (0, 1, 0))
    return m.write()


def light_pool(name, rx, rz, ink):
    """A soft-edged pool of light as concentric glowing rings, brightest in the middle."""
    m = Mesh(name, "A pool of light on the floor (stacked glowing ellipses).")
    n = 40
    for j, (f, inkj) in enumerate([(1.0, ink + "@0.35"), (0.75, ink + "@0.6"), (0.5, ink + "@0.9")]):
        y = 0.062 + j * 0.003
        for k in range(n):
            t0, t1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
            m.face([(0, y, 0), (rx * f * math.cos(t0), y, rz * f * math.sin(t0)), (rx * f * math.cos(t1), y, rz * f * math.sin(t1))],
                   inkj, (0, 1, 0))
    return m.write()


def lamp_can(name, lens):
    m = Mesh(name, "A par can on a yoke, aimed down its local -y (lens glowing).")
    m.tube((0, 0.0, 0), (0, -0.34, 0), 0.12, 0.13, "black", 10)
    m.tube((0, -0.34, 0), (0, -0.35, 0), 0.11, 0.11, lens, 10)
    m.box((0, 0.1, 0), (0.3, 0.03, 0.04), "black")
    return m.write()


def turntable():
    m = Mesh("Turntable", "A DJ turntable: plinth, platter, a record and the arm.")
    m.box((0, 0.04, 0), (0.46, 0.08, 0.36), "black")
    m.tube((-0.04, 0.08, 0), (-0.04, 0.095, 0), 0.15, 0.15, "steel", 16)
    m.tube((-0.04, 0.095, 0), (-0.04, 0.1, 0), 0.145, 0.145, "rubber", 16)
    m.tube((-0.04, 0.1, 0), (-0.04, 0.104, 0), 0.045, 0.045, "orange", 12)
    m.tube((0.17, 0.09, 0.12), (0.09, 0.11, -0.06), 0.008, 0.008, "chrome", 5)
    return m.write()


def skate_cubbies():
    """The rental wall: a grid of cubbies, each with a pair of skates (tan, white, black)."""
    m = Mesh("SkateCubbies", "The rental counter's cubby wall with paired skates in every hole (faces +x).")
    cols, rows, w, h, d = 9, 5, 0.9, 0.48, 0.42
    import random
    rnd = random.Random(306)
    for c in range(cols + 1):
        m.box((d / 2, rows * h / 2, c * w), (d, rows * h, 0.03), "walnut")
    for r in range(rows + 1):
        m.box((d / 2, r * h, cols * w / 2), (d, 0.03, cols * w), "walnut")
    m.box((0.01, rows * h / 2, cols * w / 2), (0.02, rows * h, cols * w), "brown")
    for c in range(cols):
        for r in range(rows):
            if rnd.random() < 0.12:
                continue
            boot = rnd.choice(["cream", "cream", "brown", "black", "white", "tangerine"])
            for k in (-1, 1):
                z = c * w + w / 2 + k * 0.13
                y = r * h + 0.015
                m.box((d * 0.55, y + 0.09, z), (0.25, 0.15, 0.1), boot)
                m.box((d * 0.55, y + 0.02, z), (0.22, 0.03, 0.06), "steel")
    return m.write()


def counter(name, length, top, front, trim):
    """A service counter along local z (its front faces +x), 1.05 m tall, with a chrome kick."""
    m = Mesh(name, "A service counter, length along z, customer side +x.")
    m.box((0, 0.5, 0), (0.75, 1.0, length), front)
    m.box((0.05, 1.025, 0), (0.95, 0.05, length + 0.1), top)
    m.box((0.38, 0.08, 0), (0.02, 0.12, length), "chrome")
    m.box((0.385, 0.7, 0), (0.02, 0.06, length), trim)
    return m.write()


def drum_riser():
    m = Mesh("BoothRiser", "The drummer's little riser in the booth (glitter edge in the palette).")
    m.box((0, 0.15, 0), (3.6, 0.3, 3.4), "black", {"-z": "purple@1.5", "+x": "violet", "-x": "violet"})
    return m.write()


def popcorn():
    m = Mesh("Popcorn", "A popcorn cart's glass box on the counter.")
    m.box((0, 0.03, 0), (0.6, 0.06, 0.45), "red")
    m.box((0, 0.33, 0), (0.56, 0.54, 0.41), "glass@0.6")
    m.box((0, 0.2, 0), (0.5, 0.25, 0.36), "yellow@0.8")
    m.box((0, 0.64, 0), (0.6, 0.08, 0.45), "red")
    return m.write()


def soda_fountain():
    m = Mesh("SodaFountain", "A soda fountain with four lit flavour panels.")
    m.box((0, 0.35, 0), (0.7, 0.7, 0.45), "steel")
    for i, ink in enumerate(["red@1.6", "cyan@1.6", "lime@1.6", "orange@1.6"]):
        m.box((-0.24 + i * 0.16, 0.5, -0.231), (0.13, 0.2, 0.01), ink)
    m.box((0, 0.12, -0.2), (0.6, 0.04, 0.1), "chrome")
    return m.write()


def slush():
    m = Mesh("SlushMachine", "A two-bowl slush machine: blue and cherry.")
    m.box((0, 0.1, 0), (0.5, 0.2, 0.4), "white")
    for x, ink in ((-0.12, "cyan@1.2"), (0.12, "red@1.2")):
        m.box((x, 0.38, 0), (0.2, 0.36, 0.3), ink)
    return m.write()


def records():
    m = Mesh("RecordCrate", "A milk crate of records.")
    m.box((0, 0.17, 0), (0.36, 0.34, 0.36), "orange", {"+y": None})
    for i in range(9):
        m.box((0, 0.22, -0.15 + i * 0.035), (0.31, 0.31, 0.012), ["black", "pink", "black", "cyan", "black", "yellow", "black", "black", "purple"][i])
    return m.write()


def bench():
    m = Mesh("LacingBench", "A carpeted lacing bench.")
    m.box((0, 0.42, 0), (2.4, 0.08, 0.5), "vinyl_teal")
    for x in (-1.0, 1.0):
        m.box((x, 0.19, 0), (0.08, 0.38, 0.4), "chrome")
    return m.write()


def truss(name, length):
    m = Mesh(name, "A box truss along x, pivot at its centre.")
    for y in (-0.15, 0.15):
        for z in (-0.15, 0.15):
            m.tube((-length / 2, y, z), (length / 2, y, z), 0.025, 0.025, "steel", 6, caps=False)
    k = 0
    x = -length / 2
    while x < length / 2 - 0.01:
        x1 = min(x + 0.3, length / 2)
        for y0, z0, y1, z1 in ((-0.15, -0.15, 0.15, -0.15), (-0.15, 0.15, 0.15, 0.15), (0.15, -0.15, 0.15, 0.15), (-0.15, -0.15, -0.15, 0.15)):
            if k % 2:
                y0, y1 = y1, y0
            m.tube((x, y0, z0), (x1, y1, z1), 0.012, 0.012, "steel", 5, caps=False)
        x = x1
        k += 1
    return m.write()


def synty(name, pack="OfficePack"):
    """Copies one Synty FBX (and its atlas) into Models/Synty/ and gives it a meta of its own."""
    dst = os.path.join(MODELS, "Synty")
    os.makedirs(dst, exist_ok=True)
    src = os.path.join(SYNTY, pack, "FBX", name + ".fbx")
    out = os.path.join(dst, name + ".fbx")
    if os.path.exists(src) and (not os.path.exists(out) or open(src, "rb").read() != open(out, "rb").read()):
        shutil.copyfile(src, out)
    # The FBXs name their atlas as a working .psd (..._New / ..._Mike); the loader looks for the
    # same stem as a .png beside the model, so the atlas is copied under both names.
    texture = {"OfficePack": "PolygonOffice_Texture_01_A.png", "Town": "PolygonTown_01_A.png"}[pack]
    tsrc = os.path.join(SYNTY, pack, "Textures", texture)
    for suffix in ("_New", "_Mike"):
        tout = os.path.join(dst, texture.replace(".png", suffix + ".png"))
        if os.path.exists(tsrc) and not os.path.exists(tout):
            shutil.copyfile(tsrc, tout)
    guid = hashlib.sha1(("rollerrink:" + name).encode()).hexdigest()[:16]
    save(out + ".meta", '{\n    "ConvertUnits": true,\n    "FileType": "fbx",\n    "GUID": "%s"\n}' % guid)
    return LOCAL + "Synty/" + name + ".fbx"


# ---- the scene ------------------------------------------------------------------------------------
def build():
    tx.build((CX, CZ, A, B, CX - A - 0.1, CX + A + 0.1, CZ - B - 0.1, CZ + B + 0.1, A - OUTER[0] + 0.55, CIRCLE_R))
    s = Scene(seed="story-roller-rink-v1")
    root = s.group("Moonbeam Rollerdrome")
    room = s.group("Room", root)
    rink = s.group("Rink", root)
    booth = s.group("DJ booth", root)
    rental = s.group("Skate rental", root)
    snack = s.group("Snack bar", root)
    deco = s.group("Neon and signs", root)
    people = s.group("Regulars", root)
    lamps = s.group("Lights", root)
    story = s.group("Story", root)
    marks = s.group("Markers", root)

    # ---- room: carpet floor, carpet wainscot, purple walls, a dark ceiling with trusses ----------
    W, F, Bk = ROOM_X, ROOM_BACK, ROOM_FRONT
    tbox(s, "Carpet floor", room, (0, -0.05, (F + Bk) / 2), (2 * W, 0.1, Bk - F), "Carpet.png", (13, 13))
    for name, pos, size, tiling in [
            ("Left wall carpet", (-W - 0.1, 0.65, (F + Bk) / 2), (0.2, 1.3, Bk - F), (13, 0.5)),
            ("Right wall carpet", (W + 0.1, 0.65, (F + Bk) / 2), (0.2, 1.3, Bk - F), (13, 0.5)),
            ("Back wall carpet", (0, 0.65, F - 0.1), (2 * W, 1.3, 0.2), (13, 0.5))]:
        tbox(s, name, room, pos, size, "Carpet.png", tiling)
    s.slab("Left wall", room, -W - 0.3, -W - 0.15, 1.3, CEIL, F, Bk, (0.2, 0.09, 0.3))
    s.slab("Right wall", room, W + 0.15, W + 0.3, 1.3, CEIL, F, Bk, (0.2, 0.09, 0.3))
    s.slab("Front wall", room, -W, W, 1.3, CEIL, F - 0.3, F - 0.15, (0.2, 0.09, 0.3))
    s.slab("Booth wall", room, -W, W, 0, CEIL, Bk, Bk + 0.3, (0.13, 0.06, 0.2))
    s.slab("Ceiling", room, -W - 0.3, W + 0.3, CEIL, CEIL + 0.3, F - 0.3, Bk + 0.3, (0.05, 0.045, 0.08))
    for i, z in enumerate(range(int(F) + 3, int(Bk), 4)):
        s.slab(f"Roof beam {i + 1}", room, -W, W, CEIL - 0.45, CEIL, z - 0.12, z + 0.12, (0.12, 0.1, 0.16))
    # The stripes along the walls (the 80s band of colour) and neon above them.
    for i, (y0, y1, col) in enumerate([(2.2, 2.5, (0.95, 0.25, 0.55)), (2.5, 2.8, (1.0, 0.5, 0.15)), (2.8, 3.1, (1.0, 0.8, 0.2))]):
        for side in (-1, 1):
            x = side * (W + 0.1)
            s.slab(f"Wall stripe {i}{'LR'[side > 0]}", room, x - 0.06, x + 0.06, y0, y1, F, Bk, col)
        s.slab(f"Booth wall stripe {i}", room, -W, W, y0, y1, Bk - 0.06, Bk, col)
    for side in (-1, 1):
        x = side * (W - 0.05)
        neon(s, f"Wall neon pink {'LR'[side > 0]}", deco, (x, 3.45, F + 1), (x, 3.45, Bk - 1), PINK, 4.0, 0.04)
        neon(s, f"Wall neon cyan {'LR'[side > 0]}", deco, (x, 1.95, F + 1), (x, 1.95, Bk - 1), CYAN, 3.0, 0.03)
    neon(s, "Booth wall neon", deco, (-W + 1, 3.45, Bk - 0.05), (W - 1, 3.45, Bk - 0.05), PINK, 4.0, 0.04)

    # ---- the rink -----------------------------------------------------------------------------------
    s.prop("Maple oval", rink, rink_floor(), (0, 0, 0))
    gaps = [(math.radians(58), math.radians(122)), (math.radians(203), math.radians(214))]
    s.prop("Carpeted rail", rink, rail(gaps), (0, 0, 0))
    s.prop("Rail neon, near side", deco, rail_neon(math.radians(222), math.radians(318), "RailNeonNear", "cyan@3"), (0, 0, 0))
    s.prop("Rail neon, right", deco, rail_neon(math.radians(-38), math.radians(52), "RailNeonRight", "hotpink@3"), (0, 0, 0))
    s.prop("Rail neon, left", deco, rail_neon(math.radians(126), math.radians(140), "RailNeonLeft", "hotpink@3"), (0, 0, 0))
    s.prop("Rail neon, entrance", deco, rail_neon(math.radians(160), math.radians(200), "RailNeonEntrance", "hotpink@3"), (0, 0, 0))

    # ---- the DJ booth ---------------------------------------------------------------------------------
    s.slab("Booth deck", booth, -6.6, 6.6, 0, DECK_Y, DECK_Z0, Bk, (0.06, 0.05, 0.08))
    tbox(s, "Booth fascia", booth, (0, DECK_Y / 2, DECK_Z0 - 0.02), (13.2, DECK_Y, 0.04), "Glitter.png", (10, 0.5), glow=0.6)
    neon(s, "Deck edge neon", deco, (-6.5, DECK_Y + 0.01, DECK_Z0 - 0.04), (6.5, DECK_Y + 0.01, DECK_Z0 - 0.04), PINK, 4.0, 0.03)
    for x in (-5.2, 5.2):
        s.slab("Booth step", booth, x - 0.7, x + 0.7, 0, 0.3, DECK_Z0 - 0.45, DECK_Z0, (0.08, 0.07, 0.1))
    s.prop("Drum riser", booth, drum_riser(), (0, DECK_Y, 6.4))
    s.prop("Drum rug", booth, "Assets/Models/Venue/DrumRug.obj", (0, DECK_Y + 0.31, 6.2), 0, 0.85)
    # The DJ counter in front of the kit: glitter front, turntables on top.
    s.slab("DJ counter body", booth, -2.5, 2.5, DECK_Y, DECK_Y + 0.92, 3.3, 3.9, (0.05, 0.04, 0.07))
    tbox(s, "DJ counter glitter", booth, (0, DECK_Y + 0.46, 3.28), (5.0, 0.92, 0.04), "Glitter.png", (4, 0.8), glow=0.9)
    s.slab("DJ counter top", booth, -2.6, 2.6, DECK_Y + 0.92, DECK_Y + 0.97, 3.22, 3.95, (0.75, 0.75, 0.8), metallic=0.6, rough=0.3)
    s.prop("DJ sign", deco, sign_quad("SignDJ", "SignDJ.png", 1.5, 0.47, 2.2), (0, DECK_Y + 0.5, 3.25))
    for i, x in enumerate((-1.6, 1.25)):
        s.prop(f"Turntable {i + 1}", booth, turntable(), (x, DECK_Y + 0.97, 3.6), 180)
    s.box("Mixer", booth, (-0.15, DECK_Y + 1.02, 3.6), (0.4, 0.1, 0.32), (0.08, 0.08, 0.1), emissive=(0.2, 1, 0.5), emissive_intensity=0.4)
    s.prop("Record crate L", booth, records(), (-3.0, DECK_Y, 6.6), 20)
    s.prop("Record crate R", booth, LOCAL + "RecordCrate.obj", (2.9, DECK_Y, 7.0), -14)
    s.prop("Record crate R2", booth, LOCAL + "RecordCrate.obj", (3.25, DECK_Y, 6.6), 8)
    # Speakers, the booth's back panel and the big sign.
    for x, yaw in ((-6.0, 8), (6.0, -8)):
        s.prop("Booth speaker", booth, "Assets/Models/Venue/Speaker.obj", (x, DECK_Y, 3.2), yaw, 1.5)
        s.prop("Booth speaker top", booth, "Assets/Models/Venue/SpeakerTall.obj", (x, DECK_Y + 1.5, 3.25), yaw, 1.0)
    for x in (-4.6, 4.6):
        s.prop("Wedge", booth, "Assets/Models/Venue/Wedge.obj", (x * 0.75, DECK_Y, 1.5), 180)
    s.prop("Guitar cab", booth, "Assets/Models/Venue/GuitarCab.obj", (-4.8, DECK_Y, 5.0), 160)
    s.prop("Amp head", booth, "Assets/Models/Venue/AmpHead.obj", (-4.8, DECK_Y + 0.75, 5.0), 160)
    s.prop("Bass cab", booth, "Assets/Models/Venue/GuitarCab.obj", (4.8, DECK_Y, 5.2), 200)
    s.prop("Bass head", booth, "Assets/Models/Venue/AmpHead.obj", (4.8, DECK_Y + 0.75, 5.2), 200)
    tbox(s, "Booth back panel", booth, (0, DECK_Y + 1.6, 9.6), (13.0, 3.2, 0.1), "Glitter.png", (8, 2), glow=0.35)
    for x in (-6.5, 6.5):
        neon(s, "Booth panel edge", deco, (x, DECK_Y, 9.5), (x, DECK_Y + 3.2, 9.5), CYAN, 4.0, 0.04)
    neon(s, "Booth panel top", deco, (-6.5, DECK_Y + 3.2, 9.5), (6.5, DECK_Y + 3.2, 9.5), CYAN, 4.0, 0.04)
    s.prop("Rink sign", deco, sign_quad("SignRink", "SignRink.png", 9.0, 2.25, 2.4), (0, 5.6, Bk - 0.1))
    s.slab("Rink sign back", deco, -4.7, 4.7, 4.4, 6.8, Bk - 0.1, Bk - 0.02, (0.03, 0.02, 0.05))
    s.prop("Adults only", deco, sign_quad("SignAdults", "SignAdults.png", 4.6, 0.86, 2.2), (4.3, 6.35, 0.6))
    s.slab("Adults sign frame", deco, 1.9, 6.7, 5.85, 6.85, 0.62, 0.75, (0.03, 0.03, 0.04))
    for x in (2.4, 6.2):
        s.slab("Adults sign hanger", deco, x - 0.02, x + 0.02, 6.85, CEIL, 0.66, 0.7, (0.4, 0.4, 0.45))
    s.prop("Booth truss", booth, truss("BoothTruss", 13.4), (0, 4.75, 1.1))
    for x in (-6.7, 6.7):
        s.slab("Truss leg", booth, x - 0.12, x + 0.12, DECK_Y, 4.9, 0.98, 1.22, (0.45, 0.46, 0.5), metallic=0.5, rough=0.4)

    # ---- skate rental (left wall) -------------------------------------------------------------------
    s.prop("Skate cubbies", rental, skate_cubbies(), (-W + 0.02, 0.0, -13.4))
    s.prop("Rental counter", rental, counter("RentalCounter", 8.2, "formica", "vinyl_red", "orange@2"), (-14.8, 0, -9.4))
    s.prop("Rental sign", deco, sign_quad("SignRental", "SignRental.png", 4.0, 1.0, 2.2), (-W + 0.15, 3.9, -9.4), 90)
    s.prop("Couples skate poster", deco, sign_quad("PosterCouples", "PosterCouples.png", 0.75, 1.0), (-W + 0.12, 2.6, -2.5), 90)
    s.prop("Rules poster", deco, sign_quad("PosterRules", "PosterRules.png", 0.75, 1.0), (-W + 0.12, 2.6, -15.2), 90)
    s.prop("Rental till", rental, "Assets/Models/Venue/AmpHead.obj", (-14.8, 1.05, -6.0), 90, 0.8)
    for i, z in enumerate((-12.4, -11.1)):
        sk_obj = LOCAL + ("SkatesTan.obj" if i else "SkatesBlack.obj")
        s.prop("Skates on the counter", rental, sk_obj, (-14.75, 1.05, z), 60 + 40 * i)
    s.prop("Lacing bench", rental, bench(), (-14.2, 0, -17.6), 90)
    s.prop("Lacing bench 2", rental, LOCAL + "LacingBench.obj", (-11.0, 0, -18.8), 0)
    s.prop("Wet floor", rental, synty("SM_Prop_Sign_Wetfloor_01"), (-12.0, 0, -15.6), 30)
    for i, z in enumerate((-20.4, -19.0)):
        s.prop(f"Arcade cabinet {i + 1}", rental, synty("SM_Prop_ArcadeMachine_01"), (-W + 0.6, 0, z), 90)
    s.prop("Neon cactus", deco, synty("SM_Prop_Neon_Cactus_01"), (-15.2, 1.05, -5.8), 90)

    # ---- snack bar (right wall) ---------------------------------------------------------------------
    s.prop("Snack counter", snack, counter("SnackCounter", 8.2, "formica", "vinyl_teal", "hotpink@2"), (14.8, 0, -9.4), 180)
    s.prop("Snack sign", deco, sign_quad("SignSnack", "SignSnack.png", 3.6, 0.9, 2.2), (W - 0.15, 4.0, -9.4), -90)
    s.prop("Menu board", deco, sign_quad("MenuBoard", "MenuBoard.png", 2.4, 1.8, 1.0), (W - 0.15, 2.5, -9.4), -90)
    s.prop("Disco poster", deco, sign_quad("PosterDisco", "PosterDisco.png", 0.75, 1.0), (W - 0.12, 2.6, -2.5), -90)
    s.prop("Nacho warmer", snack, "Assets/Models/Venue/FoodStall.obj", (14.85, 1.05, -11.6), -90, 0.6)
    s.prop("Popcorn", snack, popcorn(), (14.85, 1.05, -7.2), -90)
    s.prop("Soda fountain", snack, soda_fountain(), (16.4, 1.0, -12.9), -90)
    s.slab("Back counter", snack, 16.0, 17.0, 0, 1.0, -14, -4.6, (0.1, 0.5, 0.52))
    s.prop("Slush machine", snack, slush(), (16.4, 1.0, -6.2), -90)
    s.prop("Vending machine", snack, synty("SM_Prop_VendingMachine_01"), (W - 0.6, 0, -16.2), -90)
    s.prop("Fridge", snack, synty("SM_Prop_Fridge_02"), (W - 0.6, 0, -3.6), -90)
    for i, z in enumerate((-12.6, -11.2, -9.8, -8.4, -7.0)):
        s.prop(f"Counter stool {i + 1}", snack, "Assets/Models/Venue/Stool.obj", (13.9, 0, z), 0)
    for i, (x, z) in enumerate(((14.6, -17.4), (14.2, -19.8))):
        t = s.group(f"Snack table {i + 1}", snack, (x, 0, z))
        s.prop("Table", t, synty("SM_Prop_Table_Round_01"), (0, 0, 0))
        s.prop("Chair", t, synty("SM_Prop_Chair_05"), (-0.75, 0, 0.2), 100)
        s.prop("Chair", t, LOCAL + "Synty/SM_Prop_Chair_05.fbx", (0.7, 0, -0.3), -80)
        s.prop("Cup", t, synty("SM_Prop_Cup_Paper_01"), (0.1, 0.75, 0.05))
    s.prop("Bin", snack, synty("SM_Prop_Trashbin_01"), (12.4, 0, -14.6))
    for i, (x, z, col) in enumerate(((-15.6, -4.6, "pink"), (15.8, -2.0, "cyan"), (-15.8, 1.6, "yellow"))):
        s.prop(f"Balloon {i + 1}", deco, synty("SM_Prop_Balloon_01"), (x, 1.05 if i == 0 else 0, z), 15 * i)

    # Skates for everyone.
    sk.skates("SkatesOrange", "orange", stripe="yellow")
    sk.skates("SkatesSilver", "white", stripe="chrome", wheel="hotpink")
    sk.skates("SkatesTan", "cream", wheel="red", stripe="brown")
    sk.skates("SkatesBlack", "black", wheel="yellow", stripe="pink")
    sk.skates("SkatesWhite", "white", wheel="cyan", stripe="pink")

    # ---- the cast and the regulars ----------------------------------------------------------------
    jacket = "#d4dbea"
    lead = sk.dress("SilverLead", "Mother_01", "PolygonTown_03_C", jacket)
    partner = sk.dress("SilverPartner", "Rigged", "PolygonTown_02_B", jacket)
    learner = sk.dress("Learner", "Son_01", "PolygonTown_03_B")
    extras = [sk.dress(n, p, a) for n, p, a in [
        ("PairA1", "Daughter_01", "PolygonTown_04_A"), ("PairA2", "ShopKeeper_01", "PolygonTown_01_B"),
        ("PairB1", "Mother_02", "PolygonTown_02_C"), ("PairB2", "SchoolBoy_01", "PolygonTown_04_C"),
        ("PairC1", "SchoolGirl_01", "PolygonTown_01_C"), ("PairC2", "Son_01", "PolygonTown_02_A")]]
    SO, SS = LOCAL + "SkatesOrange.obj", LOCAL + "SkatesSilver.obj"
    extra_skates = [LOCAL + n + ".obj" for n in ("SkatesTan", "SkatesBlack", "SkatesWhite", "SkatesTan", "SkatesWhite", "SkatesBlack")]

    # A few regulars who live here whatever the story: a couple lacing up, the rental attendant,
    # the snack-bar attendant.
    sk.figure(s, people, "Rental attendant", extras[1], (-15.6, 0, -9.0), 90, arms=(-40, -30))
    sk.figure(s, people, "Snack attendant", extras[2], (15.6, 0, -9.8), -90, arms=(-50, -20))
    sk.figure(s, people, "Lacing up", extras[4], (-14.2, 0.0, -17.6), 90, skate=extra_skates[2], arms=(-60, -55), lean=30, lifted=False)

    # ---- markers --------------------------------------------------------------------------------------
    s.info(marks, TITLE, "Drumsmith", outdoor=False, room_back=ROOM_BACK, room_ceiling=CEIL, half_width=ROOM_X,
           desk_z=-17.5, ambient=(0.035, 0.02, 0.06), fog_color=(0.05, 0.02, 0.07), haze=0.75)
    s.spot(marks, "Drummer", (0, DECK_Y + 0.3, 6.9))
    s.spot(marks, "Guitar", (-3.7, DECK_Y, 2.6), -10)
    s.spot(marks, "Bass", (3.7, DECK_Y, 2.7), 10)
    # The crowd: skaters standing about on the floor (the featured lanes and the centre kept clear),
    # spectators at the rail by the snack bar and a knot at the booth's foot.
    for name, x0, x1, z0, z1, n, fig in [
            ("At the booth's foot", -5.4, 5.4, -0.55, 0.7, 14, "Posed"),
            ("Floor, far side", -4.4, 4.4, -3.35, -2.45, 10, "Mob"),
            ("Floor, left end", -9.0, -5.9, -9.2, -4.8, 18, "Mob"),
            ("Floor, right end", 5.9, 9.0, -9.2, -4.8, 18, "Mob"),
            ("Floor, near side", -4.0, 4.0, -11.6, -10.7, 9, "Mob"),
            ("Rail by the snack bar", 13.2, 14.2, -4.6, 0.5, 6, "Mob"),
            ("Behind the near rail", -6.0, 6.0, -16.6, -15.2, 14, "Mob")]:
        s.crowd(name, marks, ((x0 + x1) / 2, 0.04 if name.startswith("Floor") else 0.0, (z0 + z1) / 2), x1 - x0, z1 - z0, n, 0.6, 0.0, fig)

    # ---- story ---------------------------------------------------------------------------------------
    rx, rz = ellipse(CX, CZ, A - 0.42, B - 0.42, RAIL_T)
    rail_yaw = math.degrees(math.atan2((rx - CX) / A ** 2, (rz - CZ) / B ** 2))  # facing out, at the rail
    # 1. The last orange pair sits on the rental counter until the newcomer takes it.
    g = s.story("Last orange rentals on the counter", story, "newcomer_at_rail", False, 0.6, (-14.75, 1.05, -8.6))
    s.prop("Orange rentals", g, SO, (0, 0, 0), 75)
    s.light("Counter lamp on the orange pair", g, (0.6, 1.1, 0), "Point", AMBER, 6.0, 3.0)
    # 2. ... and is at the rail, both hands on it, wobbling (until the rail is empty).
    g = s.story("Newcomer at the rail", story, "newcomer_at_rail", True, 0.8, (rx, 0.04, rz))
    g2 = s.story("Still holding on", g, "rail_empty", False, 0.9)
    clip = sk.wobble_clip("RailWobble", 2.4)
    sk.standing(s, g2, "The learner, orange rentals", learner, SO, clip, (0, 0, 0), rail_yaw)
    # 3. rail_lit: a second pool of light on that stretch of rail, and its neon lights up.
    g = s.story("Second pool on the rail", story, "rail_lit", True, 1.0, (rx, 0, rz))
    lx, lz = ellipse(CX, CZ, A - 2.6, B - 2.6, RAIL_T)
    s.light("Rail pool spot", g, (lx - rx, 6.6, lz - rz), "Spot", (1.0, 0.55, 0.3), 700.0, 12.0,
            rot=look_rotation((lx, 6.6, lz), (rx, 0.4, rz)), inner=12, outer=22)
    s.prop("Rail pool can", g, lamp_can("PoolCan", "tangerine@5"), (lx - rx, 7.0, lz - rz))
    s.prop("Rail pool on the floor", g, light_pool("RailPool", 2.6, 2.1, "tangerine"), (0, 0, 0))
    t0 = RAIL_T - 0.16
    s.prop("Rail neon at the newcomer", g, rail_neon(t0, RAIL_T + 0.16, "RailNeonLit", "orange@5"), (-rx, 0, -rz))
    # 4. rail_empty: the mirror ball turns (still ball before), spangles and spinning spots.
    BALL = (CX, 6.0, CZ)
    s.slab("Mirror ball rod", root, CX - 0.02, CX + 0.02, BALL[1] + 0.8, CEIL - 0.4, CZ - 0.02, CZ + 0.02, (0.4, 0.4, 0.45))
    s.box("Mirror ball motor", root, (CX, BALL[1] + 0.95, CZ), (0.26, 0.2, 0.26), (0.1, 0.1, 0.12))
    ball = mirror_ball("MirrorBall")
    g = s.story("Mirror ball, still", story, "rail_empty", False, 0.3, BALL)
    s.prop("Mirror ball", g, ball, (0, 0, 0), 12)
    g = s.story("Mirror ball, turning", story, "rail_empty", True, 0.3, BALL)
    spin = s.entity("Turning", g)
    s.prop("Mirror ball", spin, ball, (0, 0, 0))
    for i in range(8):
        yaw = i * 45 + 10
        pitch = 34 + 14 * (i % 2)
        col = [(1, 1, 1), CYAN, PINK, GOLD][i % 4]
        s.light(f"Ball spot {i + 1}", spin, (0, 0, 0), "Spot", col, 500.0, 16.0, rot=(pitch, yaw, 0), inner=2.5, outer=5)
    g.add({"Type": "Sequence", "Clip": sk.spin_clip("BallSpin", 9.0), "PlayOnStart": True, "Loop": True,
           "Bindings": [{"Slot": "Spin", "Target": spin.guid}]})
    gs = s.story("Spangles turning", story, "rail_empty", True, 0.6, (CX, 0, CZ))
    spang = s.entity("Turning", gs)
    s.prop("Spangles", spang, spangles(), (0, 0, 0))
    gs.add({"Type": "Sequence", "Clip": LOCAL.replace("Models/", "Motion/") + "BallSpin.sequence", "PlayOnStart": True,
            "Loop": True, "Bindings": [{"Slot": "Spin", "Target": spang.guid}]})
    silver_pool = light_pool("SilverPool", 0.9, 0.9, "glass")
    warm_pool = light_pool("WarmPool", 0.9, 0.9, "tangerine")
    # The learner out on the inside lane (from rail_empty until the trio forms).
    g = s.story("Learner on the inside lane", story, "rail_empty", True, 0.8, (CX, 0.04, CZ))
    g2 = s.story("Not yet three abreast", g, "three_abreast", False, 0.8)
    sk.lapping(s, g2, "The learner, careful laps", learner, SO,
               sk.lap_clip("InsideLane", *INNER, 10.5, 0.3, 0, strides=9, sway=9, swing=36, lean=18), 1.0,
               ((1.0, 0.62, 0.35), 40.0, 5.0), warm_pool)
    # The silver pair: lapping the outer lane together, lit together, until the trio forms.
    g = s.story("Silver pair", story, "three_abreast", False, 0.8, (CX, 0.04, CZ))
    sk.lapping(s, g, "Silver jacket, lead", lead, SS, sk.lap_clip("SilverLead", *OUTER, 12.0, 0.27, -0.38), 1.0,
               ((0.8, 0.85, 1.0), 60.0, 6.0), silver_pool)
    sk.lapping(s, g, "Silver jacket, partner", partner, SS, sk.lap_clip("SilverPartner", *OUTER, 12.0, 0.27, 0.38), 1.0, None, silver_pool)
    # 5. three_abreast: one lap, the learner between the jackets, pairs falling in behind.
    g = s.story("Three abreast", story, "three_abreast", True, 0.8, (CX, 0.04, CZ))
    g2 = s.story("Still lapping", g, "circle_open", False, 0.8)
    trio = [(lead, SS, -0.62, "TrioLead"), (learner, SO, 0.0, "TrioLearner"), (partner, SS, 0.62, "TrioPartner")]
    for i, (pieces, skate, lat, name) in enumerate(trio):
        sk.lapping(s, g2, name, pieces, skate, sk.lap_clip(name, *OUTER, 12.0, 0.3, lat, strides=12), 1.0,
                   ((0.9, 0.8, 1.0), 60.0, 6.5) if i == 1 else None, warm_pool if i == 1 else silver_pool)
    for j in range(3):
        for k in range(2):
            idx = j * 2 + k
            sk.lapping(s, g2, f"Pair {j + 1}, skater {k + 1}", extras[idx], extra_skates[idx],
                       sk.lap_clip(f"Pair{j + 1}{k + 1}", *OUTER, 12.0, 0.3 + 0.045 * (j + 1), -0.36 + 0.72 * k, strides=12, sway=5))
    # Boards over the booth: ALL SKATE, then TRIO SKATE, then HANDS UP!
    board_pos = (-4.3, 6.35, 0.6)
    s.slab("Lightboard frame", deco, -6.85, -1.75, 5.5, 7.2, 0.62, 0.75, (0.03, 0.03, 0.04))
    s.slab("Lightboard hangers", deco, -6.3, -6.26, 7.2, CEIL, 0.66, 0.7, (0.4, 0.4, 0.45))
    s.slab("Lightboard hangers 2", deco, -2.34, -2.3, 7.2, CEIL, 0.66, 0.7, (0.4, 0.4, 0.45))
    g = s.story("Board: all skate", story, "three_abreast", False, 0.4, board_pos)
    s.prop("ALL SKATE", g, sign_quad("BoardAllSkate", "BoardAllSkate.png", 4.9, 1.53, 2.6), (0, 0, 0))
    g = s.story("Board: trio skate", story, "three_abreast", True, 0.4, board_pos)
    g2 = s.story("Board: until the circle", g, "circle_open", False, 0.4)
    s.prop("TRIO SKATE", g2, sign_quad("BoardTrio", "BoardTrio.png", 4.9, 1.53, 2.6), (0, 0, 0))
    g = s.story("Board: hands up", story, "circle_open", True, 0.4, board_pos)
    s.prop("HANDS UP", g, sign_quad("BoardHandsUp", "BoardHandsUp.png", 4.9, 1.53, 2.6), (0, 0, 0))
    # 6. circle_open: the circle under the ball; the learner upright in the middle, the jackets'
    # hands in the air, a ring of regulars round them, a white pool from above.
    g = s.story("The circle opens", story, "circle_open", True, 1.2, (CX, 0.04, CZ))
    s.prop("Glowing ring", g, floor_ring("CircleRing", CIRCLE_R + 0.55, 0.16, "yellow@4"), (0, 0, 0))
    s.prop("Circle pool", g, light_pool("CirclePool", 2.8, 2.8, "white"), (0, 0, 0))
    s.light("Circle downlight", g, (0, 5.0, 0.6), "Spot", (1, 0.92, 1), 420.0, 10.0, rot=(85, 180, 0), inner=16, outer=26)
    upright = sk.wobble_clip("Upright", 1.6, arms_up=False, bounce=0.0)
    hands = sk.wobble_clip("HandsUp", 1.0, arms_up=True, bounce=0.06)
    sk.standing(s, g, "The learner, upright", learner, SO, hands, (0, 0, 0.0), 180, 0.8)
    sk.standing(s, g, "Silver jacket, hands up", lead, SS, hands, (-1.1, 0, -0.35), 150, 1.0)
    sk.standing(s, g, "Silver partner, hands up", partner, SS, hands, (1.1, 0, -0.35), 210, 1.07)
    for i in range(10):
        t = 2 * math.pi * i / 10 + 0.3
        px, pz = (CIRCLE_R + 1.15) * math.cos(t), (CIRCLE_R + 1.0) * math.sin(t)
        yaw = math.degrees(math.atan2(-px, -pz))
        pieces = extras[i % len(extras)]
        if i % 3 == 0:
            sk.standing(s, g, f"Ring skater {i + 1}", pieces, extra_skates[i % 6], hands, (px, 0, pz), yaw, 0.9 + 0.04 * i)
        else:
            sk.figure(s, g, f"Ring skater {i + 1}", pieces, (px, 0, pz), yaw, skate=extra_skates[i % 6],
                      arms=(-90 - 25 * (i % 2), -100), arm_roll=(10, 10))
    burst = s.entity("Glitter from the ball", g, (0, BALL[1] - 0.8 - 0.04, 0), (90, 0, 0))
    burst.add({"Type": "VenueAccent", "Particles": 220})
    burst.add({"Type": "ParticleSystem", "Simulation": "CPU", "SimulationSpace": "World", "Shape": "Cone", "ConeAngle": 55,
               "ShapeRadius": 0.4, "Lifetime": [2.6, 4.0], "Speed": [1.5, 3.5], "Size": [0.05, 0.11],
               "StartColor": [1, 0.85, 0.4], "StartColor2": [0.5, 0.95, 1], "EndColor": [1, 0.4, 0.85], "AngularVelocity": [-300, 300],
               "Gravity": 0.25, "Drag": 0.5, "NoiseStrength": 0.8, "NoiseFrequency": 0.7, "StartAlpha": 1, "EndAlpha": 0,
               "FadeIn": 0.02, "EndSize": 0.8, "Intensity": 2.0, "Texture": "Assets/Textures/Venue/Confetti.png", "Blend": "Alpha",
               "EmissionRate": 0, "BurstCount": 0, "MaxParticles": 320, "SoftParticleDistance": 0})

    # ---- lights ------------------------------------------------------------------------------------
    s.light("Key from the roof", lamps, (6, 20, -18), "Directional", (0.55, 0.5, 0.75), 0.55, rot=(58, -18, 0), shadows=True, show="Static")
    house = s.group("House lights (plain)", lamps)
    for i, (x, z) in enumerate(((-7, -11), (7, -11), (-7, -3), (7, -3), (0, -15), (0, 1.0))):
        s.light(f"House light {i + 1}", house, (x, CEIL - 0.6, z), "Point", WARM, 48.0, 11.0)
    s.light("Silver pool on the centre", house, (0, 7.4, -9.0), "Spot", (0.78, 0.82, 1.0), 190.0, 12, rot=look_rotation((0, 7.4, -9), (0, 0, -7)), inner=30, outer=48)
    for i, x in enumerate((-6.0, 0.0, 6.0)):
        s.light(f"Front fill {i + 1}", house, (x, 6.5, -14.0), "Point", (0.95, 0.8, 0.9), 70.0, 13.0)
    s.light("Rental counter light", house, (-14.6, 3.6, -9.4), "Point", (1.0, 0.75, 0.45), 60.0, 7.0)
    s.light("Snack bar light", house, (14.6, 3.6, -9.4), "Point", (0.7, 1.0, 0.8), 60.0, 7.0)
    s.light("Arcade glow", house, (-15.6, 2.0, -19.7), "Point", (0.4, 0.5, 1.0), 25.0, 5.0)
    s.light("Booth back glow", house, (0, 3.2, 8.8), "Point", (0.7, 0.3, 1.0), 40.0, 8.0)
    s.light("Neon spill left", house, (-15.8, 3.0, -6), "Point", PINK, 30.0, 8.0)
    s.light("Neon spill right", house, (15.8, 3.0, -6), "Point", PINK, 30.0, 8.0)
    rig = s.group("Show rig", lamps)
    # Washes over the floor and the booth.
    for i, (x, y, z, to, col) in enumerate([
            (-5.5, 4.6, 1.1, (-3.6, 1, 3.2), PINK), (5.5, 4.6, 1.1, (3.6, 1, 3.2), CYAN), (0, 4.6, 1.1, (0, 1.2, 5.5), VIOLET),
            (-8, 7.4, -7, (-8, 0, -7), PINK), (8, 7.4, -7, (8, 0, -7), CYAN), (0, 7.4, -2.5, (0, 0, -2.5), GOLD)]):
        s.light(f"Wash {i + 1}", rig, (x, y, z), "Spot", col, 950.0 if i < 3 else 1300.0, 16.0,
                rot=look_rotation((x, y, z), to), inner=24, outer=44, show="Wash", group=i % 3)
    # Spinning spots: narrow beams round the mirror ball that sway across the floor.
    for i in range(10):
        t = 2 * math.pi * i / 10
        p = (CX + 0.9 * math.cos(t), BALL[1] + 0.9, CZ + 0.9 * math.sin(t))
        to = (CX + 7.5 * math.cos(t + 0.5), 0, CZ + 4.8 * math.sin(t + 0.5))
        col = [PINK, CYAN, GOLD, (1, 1, 1), VIOLET][i % 5]
        s.light(f"Ball beam {i + 1}", rig, p, "Spot", col, 1100.0, 14.0, rot=look_rotation(p, to), inner=3, outer=7,
                show="Beam", group=i % 2)
    # Follow spots: drummer, guitar, bass.
    for i, (p, to) in enumerate([((0.5, 4.7, 1.2), (0, 1.9, 6.9)), ((-2.4, 4.7, 1.2), (-3.7, 1.6, 2.6)), ((2.4, 4.7, 1.2), (3.7, 1.6, 2.7))]):
        s.light(f"Follow {i + 1}", rig, p, "Spot", (1, 0.9, 0.82), 340.0, 12.0, rot=look_rotation(p, to), inner=10, outer=20, show="Spot", group=i)
    for i, x in enumerate((-4.0, 4.0)):
        s.light(f"Blinder {i + 1}", rig, (x, 4.5, 1.0), "Spot", (1, 0.82, 0.55), 700.0, 22.0, rot=look_rotation((x, 4.5, 1), (x * 0.5, 1, -10)),
                inner=20, outer=45, show="Blinder", group=i)
        s.light(f"Strobe {i + 1}", rig, (x * 1.5, 4.9, 1.0), "Point", (1, 1, 1), 450.0, 20.0, show="Strobe", group=i)
    for i, x in enumerate((-5.5, -2.0, 2.0, 5.5)):
        s.prop(f"Truss can {i + 1}", rig, LOCAL + "PoolCan.obj", (x, 4.55, 1.1))

    # ---- cameras ------------------------------------------------------------------------------------
    cams = s.group("Cameras", marks)
    for tag, kind, eye, aim, fov in [
            ("wide", "Wide", (0, 7.6, -21.2), (0, 1.4, 0.5), 60),
            ("crane", "Crane", (-11.5, 6.8, -15.5), (1.0, 1.2, 2.0), 56),
            ("desk", "Desk", (2.2, 3.2, -19.5), (0, 2.0, 5.5), 30),
            ("drummer", "Close", (1.7, 2.9, 2.6), (0, 1.9, 6.9), 48),
            ("rail", "Custom", (-5.5, 3.6, -1.0), (rx, 0.8, rz), 52),
            ("circle", "Custom", (5.5, 4.4, -15.5), (0, 1.0, -7.0), 48),
            ("ball", "Custom", (-6.0, 1.3, -12.0), (0, 4.8, -6.5), 62),
            ("snack-bar", "Custom", (8.5, 2.3, -15.5), (15, 1.4, -8.5), 52),
            ("over-the-counter", "Custom", (-2.2, 2.3, 4.3), (-2.0, 1.2, -6.0), 60)]:
        s.camera_spot(tag, cams, eye, aim, kind, fov, tag)
    for i, (eye, aim, fov) in enumerate([
            ((-15.5, 1.65, -21.0), (-14.5, 1.3, -14.0), 64), ((-14.0, 1.7, -17.5), (-14.8, 1.2, -9.5), 62),
            ((-12.6, 1.75, -14.0), (-6.0, 1.0, -6.0), 60), ((-11.0, 1.8, -12.0), (0, 3.5, -7.0), 58),
            ((-8.5, 1.9, -10.0), (0, 1.8, 4.5), 56)]):
        s.camera_spot(f"Arrival {i + 1:02}", cams, eye, aim, "Custom", fov, f"arrival/{i + 1:02}")
    return s


def main():
    os.makedirs(MODELS, exist_ok=True)
    s = build()
    s.write(os.path.join(VENUE, ID + ".lvl"))
    preview = "Preview.jpg" if os.path.exists(os.path.join(VENUE, "Preview.jpg")) else None
    write_venue_json(VENUE, TITLE, ID + ".lvl", preview=preview, ambience="Assets/Sounds/crowd.mp3")
    print(f"{len(s.entities)} entities -> {VENUE}")


if __name__ == "__main__":
    main()
