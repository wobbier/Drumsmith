#!/usr/bin/env python3
"""Writes Assets/Venues/StoryStadium/: set 12, "The Retractable Roof Is Open" (s12-stadium).

    python3 Tools/Venues/make_story_stadium.py

The hometown headline and the story's finale. A domed stadium with its roof rolled back to the
night sky: a headline stage under an arched roof with two side screens, a field packed to the far
wall (posed front rows at the barricade, instanced Mob figures behind, a floor of heads under
them), a lower bowl and an upper deck all the way round, ribbon boards, field light towers and the
FOH tower. Deterministic: rerun = same bytes.

Story flags (Design/Story-Mode-Setlists.json):
  mug_on_screen       both side screens cut to the commuter's mustard scarf and dented mug; a
                      spot finds her at the barricade.
  upper_deck_lit      the upper deck turns into a ring of phone lights, sector by sector, with
                      pairs of torches coming down the aisles.
  stands_in_dialogue  the two side stands hold up opposing card stunts (amber HEY! / cyan HO!),
                      each on its own screen, each washed in its colour.
  loonie_on_screen    a giant drilled loonie drops from the stage roof and swings over the kit;
                      the screens show the coin.
  bucket_answered     the stands' cards turn gold into one HOMETOWN bucket, gold beams go up
                      through the open roof, the bucket comes up onto a case beside the floor tom
                      under its own spot, the screens show it, and the mug goes up.
"""
import json
import math
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
import story_stadium_art as art  # noqa: E402
from story_stadium_art import LOCAL, MODELS, VENUE, Mesh, write_obj  # noqa: E402
from venuegen import Scene, look_rotation, write_venue_json  # noqa: E402

ID = "StoryStadium"
SET = "s12-stadium"
TITLE = "The Retractable Roof Is Open"

DECK = 2.2                 # stage deck height
RISER = 3.2                # drum riser top
DRUMMER = (0.0, RISER, 7.4)
LOWER_ROWS, LOWER_DEPTH, LOWER_RISE, LOWER_BASE = 24, 0.85, 0.42, 1.6
UPPER_ROWS, UPPER_DEPTH, UPPER_RISE, UPPER_BASE, UPPER_D0 = 26, 0.9, 0.62, 15.2, 18.5
ROOF_INNER, ROOF_Y_IN, ROOF_Y_OUT, ROOF_OUTER = 12.0, 41.0, 38.0, 48.0
MOSAIC_Z = (-62.0, 6.0)
TOWER = (21.0, -21.0)     # the field light towers (x either side, z)    # the straight run of each side stand that takes the card stunts

AMBER = (1.0, 0.55, 0.16)
GOLD = (1.0, 0.77, 0.3)
CYAN = (0.16, 0.8, 1.0)
WARM = (1.0, 0.84, 0.64)
ICE = (0.7, 0.86, 1.0)
MAGENTA = (0.85, 0.2, 1.0)

MATS = {"Pal": art.PAL, "Glow": art.GLOW}


def M(name):
    return LOCAL + name + ".obj"


def V(name):
    return "Assets/Models/Venue/" + name + ".obj"


# ---------------------------------------------------------------------------------------------
# Bowl meshes
def row_y_lower(r):
    return LOWER_BASE + LOWER_RISE * (r + 1)


def row_y_upper(r):
    return UPPER_BASE + UPPER_RISE * (r + 1)


def stepped(mesh, mat, rows, d0, depth, y_of, y_front, segs, uv, eps=0.0, aisle=None):
    """Seat rows over the given segments. uv(k, r, part, corner) -> (u, v); part 'tread' | 'riser'.
    aisle(k) -> True renders that segment as concrete stairs in the palette instead."""
    ts, arc = art.bowl_samples()
    for k in segs:
        t0, t1 = ts[k], ts[k + 1]
        for r in range(rows):
            a, b = d0 + depth * r, d0 + depth * (r + 1)
            y, yp = y_of(r), (y_of(r - 1) if r > 0 else y_front)
            p00, p10 = art.bowl_point(t0, a - eps), art.bowl_point(t1, a - eps)
            p01, p11 = art.bowl_point(t0, b), art.bowl_point(t1, b)
            nx, nz = (p00[2] + p10[2]) / 2, (p00[3] + p10[3]) / 2
            tread = [(p00[0], y + eps, p00[1]), (p10[0], y + eps, p10[1]), (p11[0], y + eps, p11[1]), (p01[0], y + eps, p01[1])]
            riser = [(p00[0], yp, p00[1]), (p10[0], yp, p10[1]), (p10[0], y, p10[1]), (p00[0], y, p00[1])]
            if aisle is not None and aisle(k):
                mesh.face(tread, "Pal", "stair", hint=(0, 1, 0))
                mesh.face(riser, "Pal", "concrete_dk", hint=(-nx, 0, -nz))
                continue
            mesh.face(tread, mat, uvs=[uv(k, r, "tread", c) for c in range(4)], hint=(0, 1, 0))
            mesh.face(riser, mat, uvs=[uv(k, r, "riser", c) for c in range(4)], hint=(-nx, 0, -nz))


def tile_uv(rows_per_tile=4):
    ts, arc = art.bowl_samples()

    def uv(k, r, part, c):
        u = (arc[k] if c in (0, 3) else arc[k + 1]) / 8.0
        base = r / rows_per_tile
        lo, hi = (base, base + 0.6 / rows_per_tile) if part == "tread" else (base + 0.6 / rows_per_tile, base + 1.0 / rows_per_tile)
        if part == "tread":
            v = lo if c in (0, 1) else hi
        else:
            v = hi if c in (0, 1) else lo
        return (u, 1.0 - v)
    return uv


def is_stage_end(k):
    ts, _ = art.bowl_samples()
    x, z, _, _ = art.bowl_point((ts[k] + ts[k + 1]) / 2, 0)
    return z > 10.0


def side_segments(side):
    """The straight run of one side stand (side -1 is the crowd's left, -x)."""
    ts, _ = art.bowl_samples()
    out = []
    for k in range(art.SEGMENTS):
        x, z, nx, nz = art.bowl_point((ts[k] + ts[k + 1]) / 2, 0)
        if nx * side > 0.95 and MOSAIC_Z[0] <= z <= MOSAIC_Z[1]:
            out.append(k)
    return out


def aisle_of(k):
    return k % 9 == 4


def bowl(s, root):
    """The concrete, the seats, the ribbon boards, the suites and the roof ring."""
    ts, arc = art.bowl_samples()
    allk = range(art.SEGMENTS)
    seats_tex = art.textured("Seats.png", glow=("Seats.png", 1.0))
    mats = dict(MATS, Seats=seats_tex, Tarp={"kd": "Palette.png"},
                Ribbon=art.textured("Ribbon.png", glow=True), Floor=art.textured("Floor.png"))
    mats["Ribbon"]["ke_value"] = 1.7

    # -- lower bowl
    lower = Mesh("BowlLower", "The lower bowl: 24 rows round the field; tarps over the rows behind the stage.")
    crowd_k = [k for k in allk if not is_stage_end(k)]
    tarp_k = [k for k in allk if is_stage_end(k)]
    seats_lo = Mesh("SeatsLower", "The lower bowl's seated crowd (tiling texture).")
    stepped(seats_lo, "Seats", LOWER_ROWS, 0.0, LOWER_DEPTH, row_y_lower, LOWER_BASE, [k for k in crowd_k if not aisle_of(k)], tile_uv())
    write_obj(seats_lo, mats)
    stepped(lower, "Pal", LOWER_ROWS, 0.0, LOWER_DEPTH, row_y_lower, LOWER_BASE, [k for k in crowd_k if aisle_of(k)],
            lambda k, r, p, c: art.swatch_uv("stair" if p == "tread" else "concrete_dk"))
    stepped(lower, "Pal", LOWER_ROWS, 0.0, LOWER_DEPTH, row_y_lower, LOWER_BASE, tarp_k,
            lambda k, r, p, c: art.swatch_uv("tarp"))
    # field wall with its ribbon board, and the concourse wall with the suites above the lower bowl
    d_top = LOWER_DEPTH * LOWER_ROWS
    for k in allk:
        t0, t1 = ts[k], ts[k + 1]
        p0, p1 = art.bowl_point(t0, 0), art.bowl_point(t1, 0)
        n = (-(p0[2] + p1[2]) / 2, 0, -(p0[3] + p1[3]) / 2)
        u0, u1 = -arc[k] / 16.0, -arc[k + 1] / 16.0
        lower.face([(p0[0], 0, p0[1]), (p1[0], 0, p1[1]), (p1[0], 0.25, p1[1]), (p0[0], 0.25, p0[1])], "Pal", "char", hint=n)
        if is_stage_end(k):
            lower.face([(p0[0], 0.25, p0[1]), (p1[0], 0.25, p1[1]), (p1[0], LOWER_BASE, p1[1]), (p0[0], LOWER_BASE, p0[1])], "Pal", "char", hint=n)
        else:
            lower.face([(p0[0], 0.25, p0[1]), (p1[0], 0.25, p1[1]), (p1[0], 1.35, p1[1]), (p0[0], 1.35, p0[1])], "Ribbon",
                       uvs=[(u0, 0), (u1, 0), (u1, 1), (u0, 1)], hint=n)
            lower.face([(p0[0], 1.35, p0[1]), (p1[0], 1.35, p1[1]), (p1[0], LOWER_BASE, p1[1]), (p0[0], LOWER_BASE, p0[1])], "Pal", "char", hint=n)
        # the walkway behind the top row, the suites' glass and the underside of the upper deck
        q0, q1 = art.bowl_point(t0, d_top), art.bowl_point(t1, d_top)
        w0, w1 = art.bowl_point(t0, UPPER_D0 + 3.0), art.bowl_point(t1, UPPER_D0 + 3.0)
        yt = row_y_lower(LOWER_ROWS - 1)
        lower.face([(q0[0], yt, q0[1]), (q1[0], yt, q1[1]), (w1[0], yt, w1[1]), (w0[0], yt, w0[1])], "Pal", "concrete_dk", hint=(0, 1, 0))
        lower.face([(w0[0], yt, w0[1]), (w1[0], yt, w1[1]), (w1[0], 13.0, w1[1]), (w0[0], 13.0, w0[1])], "Pal", "glass", hint=n)
        lit = "window" if (k * 7) % 5 else "dim"
        g0, g1 = art.bowl_point(t0, UPPER_D0 + 2.98), art.bowl_point(t1, UPPER_D0 + 2.98)
        a, b = 0.15, 0.85
        lower.face([(g0[0] + (g1[0] - g0[0]) * a, yt + 0.25, g0[1] + (g1[1] - g0[1]) * a),
                    (g0[0] + (g1[0] - g0[0]) * b, yt + 0.25, g0[1] + (g1[1] - g0[1]) * b),
                    (g0[0] + (g1[0] - g0[0]) * b, 12.7, g0[1] + (g1[1] - g0[1]) * b),
                    (g0[0] + (g1[0] - g0[0]) * a, 12.7, g0[1] + (g1[1] - g0[1]) * a)], "Glow", lit, hint=n)
        f0, f1 = art.bowl_point(t0, UPPER_D0), art.bowl_point(t1, UPPER_D0)
        lower.face([(f0[0], 13.0, f0[1]), (f1[0], 13.0, f1[1]), (w1[0], 13.0, w1[1]), (w0[0], 13.0, w0[1])], "Pal", "char", hint=(0, -1, 0))
    write_obj(lower, mats)

    # -- upper deck (fascia with the ribbon board, seats, back wall)
    upper = Mesh("BowlUpper", "The upper deck: 26 rows all the way round, under the roof ring.")
    seats_up = Mesh("SeatsUpper", "The upper deck's seated crowd (tiling texture).")
    stepped(seats_up, "Seats", UPPER_ROWS, UPPER_D0, UPPER_DEPTH, row_y_upper, 14.6, [k for k in allk if not aisle_of(k)], tile_uv())
    write_obj(seats_up, mats)
    stepped(upper, "Pal", UPPER_ROWS, UPPER_D0, UPPER_DEPTH, row_y_upper, 14.6, [k for k in allk if aisle_of(k)],
            lambda k, r, p, c: art.swatch_uv("stair" if p == "tread" else "concrete_dk"))
    d_back = UPPER_D0 + UPPER_DEPTH * UPPER_ROWS
    for k in allk:
        t0, t1 = ts[k], ts[k + 1]
        f0, f1 = art.bowl_point(t0, UPPER_D0), art.bowl_point(t1, UPPER_D0)
        n = (-(f0[2] + f1[2]) / 2, 0, -(f0[3] + f1[3]) / 2)
        u0, u1 = -arc[k] / 12.0, -arc[k + 1] / 12.0
        upper.face([(f0[0], 13.0, f0[1]), (f1[0], 13.0, f1[1]), (f1[0], 13.5, f1[1]), (f0[0], 13.5, f0[1])], "Pal", "char", hint=n)
        upper.face([(f0[0], 13.5, f0[1]), (f1[0], 13.5, f1[1]), (f1[0], 14.6, f1[1]), (f0[0], 14.6, f0[1])], "Ribbon",
                   uvs=[(u0, 0), (u1, 0), (u1, 1), (u0, 1)], hint=n)
        upper.face([(f0[0], 14.6, f0[1]), (f1[0], 14.6, f1[1]), (f1[0], UPPER_BASE, f1[1]), (f0[0], UPPER_BASE, f0[1])], "Pal", "char", hint=n)
        b0, b1 = art.bowl_point(t0, d_back), art.bowl_point(t1, d_back)
        yb = row_y_upper(UPPER_ROWS - 1)
        upper.face([(b0[0], yb, b0[1]), (b1[0], yb, b1[1]), (b1[0], ROOF_Y_OUT, b1[1]), (b0[0], ROOF_Y_OUT, b0[1])], "Pal", "concrete_dk", hint=n)
        # exit signs over the vomitories
        if aisle_of(k):
            e0, e1 = art.bowl_point(t0, d_back - 0.02), art.bowl_point(t1, d_back - 0.02)
            m0 = [(e0[i] * 0.62 + e1[i] * 0.38) for i in range(2)]
            m1 = [(e0[i] * 0.38 + e1[i] * 0.62) for i in range(2)]
            upper.face([(m0[0], yb + 2.4, m0[1]), (m1[0], yb + 2.4, m1[1]), (m1[0], yb + 2.9, m1[1]), (m0[0], yb + 2.9, m0[1])], "Glow", "exit", hint=n)
    write_obj(upper, mats)

    # -- roof ring: the cantilever over the upper deck, its floodlight banks, ribs and the rails
    roof = Mesh("RoofRing", "The roof ring left when the roof rolls back: cantilever, ribs, floodlight banks.")
    for k in allk:
        t0, t1 = ts[k], ts[k + 1]
        i0, i1 = art.bowl_point(t0, ROOF_INNER), art.bowl_point(t1, ROOF_INNER)
        o0, o1 = art.bowl_point(t0, ROOF_OUTER), art.bowl_point(t1, ROOF_OUTER)
        n = (-(i0[2] + i1[2]) / 2, 0, -(i0[3] + i1[3]) / 2)
        thick = 2.6
        # underside (slopes down to the back), top, inner edge
        roof.face([(i0[0], ROOF_Y_IN, i0[1]), (i1[0], ROOF_Y_IN, i1[1]), (o1[0], ROOF_Y_OUT, o1[1]), (o0[0], ROOF_Y_OUT, o0[1])], "Pal", "roof_dk", hint=(0, -1, 0))
        roof.face([(i0[0], ROOF_Y_IN + thick, i0[1]), (i1[0], ROOF_Y_IN + thick, i1[1]), (o1[0], ROOF_Y_OUT + thick + 1, o1[1]), (o0[0], ROOF_Y_OUT + thick + 1, o0[1])], "Pal", "roof", hint=(0, 1, 0))
        roof.face([(i0[0], ROOF_Y_IN, i0[1]), (i1[0], ROOF_Y_IN, i1[1]), (i1[0], ROOF_Y_IN + thick, i1[1]), (i0[0], ROOF_Y_IN + thick, i0[1])], "Pal", "steel", hint=n)
        # floodlight banks hung under the inner edge: mostly dark for the show, a few left on low
        if k % 4 == 1:
            c = art.bowl_point((t0 + t1) / 2, ROOF_INNER + 0.8)
            on = "ice" if k % 16 == 1 else "dim"
            lamp = (c[0], ROOF_Y_IN - 0.7, c[1])
            yaw = math.degrees(math.atan2(-c[2], -c[3]))
            roof.box(lamp, (2.6, 1.2, 0.5), "steel", yaw=yaw)
            for j in (-0.8, 0.0, 0.8):
                q = (c[0] + math.cos(math.radians(yaw)) * j - c[2] * 0.27, ROOF_Y_IN - 0.7, c[1] - math.sin(math.radians(yaw)) * j - c[3] * 0.27)
                roof.box(q, (0.6, 0.9, 0.04), on, mat="Glow", yaw=yaw)
        # ribs under the cantilever
        if k % 5 == 0:
            a = art.bowl_point(t0, ROOF_INNER + 0.5)
            b = art.bowl_point(t0, ROOF_OUTER - 1.0)
            ya = ROOF_Y_IN - 0.05
            yb = ROOF_Y_OUT + (ROOF_Y_IN - ROOF_Y_OUT) * (1.0 / (ROOF_OUTER - ROOF_INNER))
            roof.tube((a[0], ya - 1.3, a[1]), (b[0], yb - 0.2, b[1]), 0.22, "steel", 5)
            roof.tube((a[0], ya - 1.3, a[1]), (a[0], ya, a[1]), 0.18, "steel", 5)
    # the rails the roof panels ride on, across the open sky, and the panels parked at each end
    for x in (-31.0, 31.0):
        roof.box((x, 44.2, -26.0), (1.4, 1.6, 214.0), "steel_lt")
        for z in range(-128, 78, 12):
            roof.tube((x - 0.6, 43.4, z), (x + 0.6, 45.0, z + 6), 0.1, "steel", 4)
            roof.tube((x + 0.6, 43.4, z + 6), (x - 0.6, 45.0, z + 12), 0.1, "steel", 4)
    for z0, z1, y in ((40.0, 76.0, 45.6), (46.0, 80.0, 47.6), (-128.0, -92.0, 45.6), (-132.0, -98.0, 47.6)):
        roof.box((0, y, (z0 + z1) / 2), (68.0, 1.3, z1 - z0), "roof")
        for x in range(-30, 31, 10):
            roof.box((x, y - 0.75, (z0 + z1) / 2), (0.5, 0.25, z1 - z0 - 1), "steel")
        roof.box((0, y - 0.66, z0 if z0 > 0 else z1), (68.0, 0.2, 0.25), "red", mat="Glow")
    write_obj(roof, mats)

    # -- the field: a floor of heads under the Mob, inside the field wall
    field = Mesh("FieldFloor", "Flooring over the turf, a crowd's shoulders and heads painted on (4 m tile).")
    centre = (0.0, 0.01, art.FIELD_ZC)
    for k in allk:
        p0, p1 = art.bowl_point(ts[k], -0.05), art.bowl_point(ts[k + 1], -0.05)
        pts = [centre, (p1[0], 0.01, p1[1]), (p0[0], 0.01, p0[1])]
        field.face(pts, "Floor", uvs=[(p[0] / 4.0, p[2] / 4.0) for p in pts], hint=(0, 1, 0))
    write_obj(field, mats)

    for name in ("BowlLower", "BowlUpper", "RoofRing", "FieldFloor"):
        s.prop(name, root, M(name), (0, 0, 0))
    for name in ("SeatsLower", "SeatsUpper"):
        glowing(s.prop(name, root, M(name), (0, 0, 0)), name, 0.45 if name == "SeatsLower" else 0.8)


def overlay(name, note, segs, rows, d0, depth, y_of, y_front, mat, mats, uv, eps, extra=None):
    """A story overlay laid over seats (the phones, the card stunts). Returns its centroid."""
    mesh = Mesh(name, note)
    stepped(mesh, mat, rows, d0, depth, y_of, y_front, segs, uv, eps=eps)
    if extra:
        extra(mesh)
    write_obj(mesh, mats)
    xs = [p[0] for f in mesh.faces for p in f[0]]
    ys = [p[1] for f in mesh.faces for p in f[0]]
    zs = [p[2] for f in mesh.faces for p in f[0]]
    return (sum(xs) / len(xs), sum(ys) / len(ys), sum(zs) / len(zs))


def story_overlay(s, parent, flag, when_set, name, centroid, fade=1.2, intensity=1.0):
    g = s.story(f"{name} ({flag})", parent, flag, when_set, fade, centroid)
    glowing(s.prop(name, g, M(name), tuple(-c for c in centroid)), name, intensity)
    return g


GLOW_MAPS = {"SeatsLower": ("Seats", "Seats"), "SeatsUpper": ("Seats", "Seats"), "CardsWest": ("MosaicHey", "MosaicHey"), "CardsEast": ("MosaicHo", "MosaicHo"),
             "GoldCardsWest": ("MosaicGold", "MosaicGold"), "GoldCardsEast": ("MosaicGold", "MosaicGold")}


def glowing(entity, name, intensity):
    """A model's emissive pushed past 1 (an mtl Ke can't go over 1). The override must name its
    textures again, or the part loses them."""
    model = entity.components[-1]
    model["Compact"] = True
    kd, ke = GLOW_MAPS[name]
    tex = {"Diffuse": {"Path": LOCAL + kd + ".png"}, "Emissive": {"Path": LOCAL + ke + ".png"}}
    part = {"Material": {"Type": "StandardMaterial", "EmissiveColor": [1.0, 1.0, 1.0], "EmissiveIntensity": float(intensity),
                         "Textures": tex}}
    model["Parts"] = {f"{name}.obj#0/{name}#0/@#{i}": part for i in range(2)}


def phones(s, root):
    """upper_deck_lit: eight sectors of phone lights over every row of the upper deck, each
    sector growing out from its own middle, with pairs of torches coming down the aisles. Each
    phone is a small glowing quad held up at head height (oversized so it reads across the bowl)."""
    import random
    rnd = random.Random(1212)
    sectors = 8
    per = art.SEGMENTS // sectors
    ts, _ = art.bowl_samples()
    group = s.group("Upper deck lit (phones)", root)
    tones = ("white", "white", "ice", "warm")
    for i in range(sectors):
        mesh = Mesh(f"UpperPhones{i + 1}", "upper_deck_lit: the upper deck's phones and the torches in the aisles.")
        for k in range(i * per, (i + 1) * per):
            for r in range(UPPER_ROWS):
                if aisle_of(k):
                    if r not in (3, 7, 11, 16, 21):
                        continue
                    spots = [(0.38, 0.3), (0.62, 0.55)]  # a pair coming down the stairs
                    size = (0.26, 0.3)
                else:
                    spots = [(rnd.random(), rnd.uniform(0.2, 0.8)) for _ in range(rnd.choice((1, 2, 2, 3)))]
                    size = (0.34, 0.46)
                for f, dd in spots:
                    t = ts[k] + (ts[k + 1] - ts[k]) * f
                    x, z, nx, nz = art.bowl_point(t, UPPER_D0 + UPPER_DEPTH * (r + dd))
                    y = row_y_upper(r) + rnd.uniform(1.15, 1.6)
                    tx, tz = -nz * size[0] / 2, nx * size[0] / 2
                    mesh.face([(x - tx, y, z - tz), (x + tx, y, z + tz), (x + tx, y + size[1], z + tz), (x - tx, y + size[1], z - tz)],
                              "Glow", rnd.choice(tones), hint=(-nx, 0, -nz))
        write_obj(mesh, {"Glow": art.GLOW})
        xs = [p[0] for f in mesh.faces for p in f[0]]
        ys = [p[1] for f in mesh.faces for p in f[0]]
        zs = [p[2] for f in mesh.faces for p in f[0]]
        c = (sum(xs) / len(xs), sum(ys) / len(ys), sum(zs) / len(zs))
        g = s.story(f"{mesh.name} (upper_deck_lit)", group, "upper_deck_lit", True, 1.6, c)
        s.prop(mesh.name, g, M(mesh.name), tuple(-v for v in c))


def mosaics(s, root):
    """stands_in_dialogue / bucket_answered: card stunts on the two side stands."""
    def picture_uv(side):
        ts, _ = art.bowl_samples()
        z0, z1 = MOSAIC_Z

        def uv(k, r, part, c):
            kk = k if c in (0, 3) else k + 1
            _, z, _, _ = art.bowl_point(ts[kk], 0)
            u = (z - z0) / (z1 - z0) if side < 0 else (z1 - z) / (z1 - z0)
            base = r / LOWER_ROWS
            lo, hi = (base, base + 0.6 / LOWER_ROWS) if part == "tread" else (base + 0.6 / LOWER_ROWS, base + 1.0 / LOWER_ROWS)
            v = (lo if c in (0, 1) else hi) if part == "tread" else (hi if c in (0, 1) else lo)
            return (u, v)
        return uv

    dialogue = s.group("Stands in dialogue (card stunts)", root)
    finale = s.group("The stands answer (gold cards)", root)
    for side, word, tex in ((-1, "HEY!", "MosaicHey"), (1, "HO!", "MosaicHo")):
        segs = side_segments(side)
        mats = {"Cards": art.textured(tex + ".png", glow=(tex + ".png", 1.0))}
        name = f"Cards{'West' if side < 0 else 'East'}"
        c = overlay(name, "stands_in_dialogue: one stand calls, the other answers.", segs, LOWER_ROWS, 0.0, LOWER_DEPTH,
                    row_y_lower, LOWER_BASE, "Cards", mats, picture_uv(side), 0.035)
        story_overlay(s, dialogue, "stands_in_dialogue", True, name, c, fade=1.4, intensity=1.0)
        # (the gold cards replace them at the very end)
        gname = f"GoldCards{'West' if side < 0 else 'East'}"
        gm = {"Gold": art.textured("MosaicGold.png", glow=("MosaicGold.png", 1.0))}
        gc = overlay(gname, "bucket_answered: both stands hold up the same bucket.", segs, LOWER_ROWS, 0.0, LOWER_DEPTH,
                     row_y_lower, LOWER_BASE, "Gold", gm, picture_uv(side), 0.07)
        story_overlay(s, finale, "bucket_answered", True, gname, gc, fade=1.8, intensity=1.2)


# ---------------------------------------------------------------------------------------------
# Small generated props
def props_meshes():
    mats = dict(MATS)
    b = Mesh("Bucket", "The subway bucket: a white pail turned over, scuffed, an orange label band. Floor pivot.")
    b.cylinder((0, 0, 0), 0.165, 0.145, 0.36, "bucket", 16, caps=(False, True))
    b.cylinder((0, 0.0, 0), 0.172, 0.172, 0.03, "bucket_rim", 16, caps=(False, True))
    b.cylinder((0, 0.17, 0), 0.159, 0.155, 0.09, "label", 16, caps=(False, False))
    b.box((0.1, 0.25, -0.12), (0.06, 0.04, 0.02), "scuff", yaw=-38)
    b.box((-0.13, 0.1, 0.05), (0.03, 0.06, 0.05), "scuff", yaw=70)
    b.tube((-0.15, 0.04, 0), (-0.1, 0.02, 0.02), 0.006, "steel")
    write_obj(b, mats)

    st = Mesh("Sticks", "A pair of sticks laid across the bucket.")
    st.tube((-0.2, 0.0, -0.04), (0.2, 0.0, 0.03), 0.008, "stick", 6)
    st.tube((-0.19, 0.012, 0.05), (0.21, 0.012, -0.02), 0.008, "stick", 6)
    write_obj(st, mats)

    mug = Mesh("TravelMug", "The commuter's steel travel mug, dented. Base pivot; 0.2 m tall.")
    mug.cylinder((0, 0, 0), 0.04, 0.043, 0.17, "mug", 12)
    mug.cylinder((0, 0.17, 0), 0.045, 0.042, 0.03, "char", 12)
    mug.box((0.035, 0.09, -0.02), (0.02, 0.04, 0.03), "mug_dk", yaw=30)
    write_obj(mug, mats)

    c = Mesh("Loonie", "A drilled eleven-sided gold coin: 1 m across before scaling; hangs from its hole (pivot).")
    def coin(mesh, r, t, hole_y):
        n = 11
        pts = [(r * math.sin(2 * math.pi * i / n), -hole_y + r * math.cos(2 * math.pi * i / n)) for i in range(n)]
        for zf, hint in ((t / 2, (0, 0, 1)), (-t / 2, (0, 0, -1))):
            mesh.face([(x, y, zf) for x, y in pts], "Pal", "coin", hint=hint)
        for i in range(n):
            (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
            mid = ((x0 + x1) / 2, (y0 + y1) / 2 + hole_y)
            mesh.face([(x0, y0, -t / 2), (x1, y1, -t / 2), (x1, y1, t / 2), (x0, y0, t / 2)], "Pal", "coin_dk", hint=(mid[0], mid[1], 0))
        ri = r * 0.84
        inner = [(ri * math.sin(2 * math.pi * (i + .5) / n), -hole_y + ri * math.cos(2 * math.pi * (i + .5) / n)) for i in range(n)]
        for zf, hint in ((t / 2 + 0.002, (0, 0, 1)), (-t / 2 - 0.002, (0, 0, -1))):
            for i in range(n):
                (x0, y0), (x1, y1) = inner[i], inner[(i + 1) % n]
                d0, d1 = (x0 * 0.97, (y0 + hole_y) * 0.97 - hole_y), (x1 * 0.97, (y1 + hole_y) * 0.97 - hole_y)
                mesh.face([(x0, y0, zf), (x1, y1, zf), (d1[0], d1[1], zf), (d0[0], d0[1], zf)], "Pal", "coin_dk", hint=hint)
            # the drilled hole, read as a dark disc both sides
            hole = [(0.035 * math.cos(2 * math.pi * i / 10), -0.0 + 0.035 * math.sin(2 * math.pi * i / 10)) for i in range(10)]
            mesh.face([(x, y - 0.075, zf * 1.05) for x, y in hole], "Pal", "black", hint=hint)
            # the bird on the water (generic)
            bird = [(-0.18, -0.62), (0.2, -0.6), (0.26, -0.55), (0.06, -0.5), (-0.12, -0.5), (-0.2, -0.44), (-0.28, -0.46), (-0.24, -0.55)]
            mesh.face([(x, y, zf * 1.08) for x, y in bird], "Pal", "coin_dk", hint=hint)
            mesh.face([(-0.36, -0.68, zf * 1.08), (0.36, -0.68, zf * 1.08), (0.36, -0.66, zf * 1.08), (-0.36, -0.66, zf * 1.08)], "Pal", "coin_dk", hint=hint)
    coin(c, 0.5, 0.06, 0.08 + 0.5 - 0.0)
    write_obj(c, mats)

    stand = Mesh("LoonieStand", "The loonie's stand by the hi-hat: a short boom with a hook. Floor pivot.")
    stand.cylinder((0, 0, 0), 0.16, 0.16, 0.02, "steel", 10)
    stand.tube((0, 0, 0), (0, 1.32, 0), 0.012, "silver", 6)
    stand.tube((0, 1.32, 0), (-0.32, 1.38, 0), 0.01, "silver", 6)
    stand.tube((-0.32, 1.38, 0), (-0.32, 1.33, 0), 0.004, "silver", 4)
    write_obj(stand, mats)

    for nm in ("Insert_Mug", "Insert_Loonie", "Insert_Bucket", "Insert_StandW", "Insert_StandE", "LedWall"):
        qq = Mesh(nm, "A unit quad facing the crowd (-z).")
        qq.face([(-0.5, -0.5, 0), (0.5, -0.5, 0), (0.5, 0.5, 0), (-0.5, 0.5, 0)], "Pic",
                uvs=[(0, 0), (1, 0), (1, 1), (0, 1)], hint=(0, 0, -1))
        write_obj(qq, {"Pic": art.textured(nm + ".png", glow=(nm + ".png", 1.5 if nm != "LedWall" else 1.25))})

    beam = Mesh("SkyBeam", "A searchlight shaft, 1 m across at the base, 1 unit tall, flaring. Base pivot.")
    beam.cylinder((0, 0, 0), 0.5, 1.6, 1.0, "gold", 10, caps=(False, False))
    write_obj(beam, {"Pal": art.GLOW})

    ld = Mesh("LoonieChain", "The chain the giant loonie hangs from (unit length down from the pivot).")
    for i in range(20):
        y = -i / 20.0
        ld.box((0, y - 0.025, 0), (0.06 if i % 2 else 0.02, 0.05, 0.02 if i % 2 else 0.06), "silver")
    write_obj(ld, mats)


def textures():
    art.palette_texture()
    art.seats_texture("Seats", 1201)
    art.floor_texture("Floor", 1203)
    art.insert_mug(os.path.join(MODELS, "Insert_Mug.png"))
    art.insert_loonie(os.path.join(MODELS, "Insert_Loonie.png"))
    art.insert_bucket(os.path.join(MODELS, "Insert_Bucket.png"))
    art.insert_stand(os.path.join(MODELS, "Insert_StandW.png"), (255, 150, 40), "HEY!", 1)
    art.insert_stand(os.path.join(MODELS, "Insert_StandE.png"), (40, 200, 255), "HO!", -1)
    art.mosaic(os.path.join(MODELS, "MosaicHey.png"), (240, 132, 30), "HEY!", 1, 21)
    art.mosaic(os.path.join(MODELS, "MosaicHo.png"), (30, 170, 240), "HO!", -1, 22)
    art.mosaic(os.path.join(MODELS, "MosaicGold.png"), (236, 176, 50), "", 1, 23, bucket=True)
    art.ribbon(os.path.join(MODELS, "Ribbon.png"))
    art.backdrop(os.path.join(MODELS, "LedWall.png"))


def commuter_parts():
    """The commuter's body (Mother_02) dressed in her atlas (PolygonTown_02_B), copied locally."""
    src = os.path.join(art.ROOT, "Assets", "Models", "People", "Crowd", "Mother_02")
    dst = os.path.join(MODELS, "Commuter")
    os.makedirs(dst, exist_ok=True)
    for part in ("Legs", "Torso", "Head", "ArmL", "ArmR"):
        data = open(os.path.join(src, part + ".obj"), "rb").read()
        art.save_bytes(os.path.join(dst, part + ".obj"), data)
    art.save_text(os.path.join(dst, "Crowd.mtl"),
                  "newmtl Crowd\nKd 1 1 1\nKs 0 0 0\nmap_Kd ../../../../Models/Venue/PolygonTown_02_B.png\n")


# ---------------------------------------------------------------------------------------------
# Scene
def stage(s, root):
    g = s.group("Headline stage", root)
    deck = s.group("Deck and risers", g)
    s.slab("Deck", deck, -17, 17, DECK - 0.25, DECK, 0, 14, (0.05, 0.05, 0.055), rough=0.6)
    s.slab("Deck skirt", deck, -17, 17, 0, DECK - 0.25, 0.05, 13.9, (0.012, 0.012, 0.014))
    s.slab("Deck lip glow", deck, -17, 17, DECK - 0.06, DECK + 0.01, -0.03, 0.03, (0.2, 0.2, 0.2), emissive=GOLD,
           emissive_intensity=2.2, shadows=False)
    s.slab("Drum riser", deck, -2.8, 2.8, DECK, RISER, 5.0, 9.6, (0.04, 0.04, 0.045))
    s.slab("Drum riser lip", deck, -2.8, 2.8, RISER - 0.07, RISER - 0.02, 4.97, 5.0, (0.2, 0.2, 0.2), emissive=AMBER,
           emissive_intensity=2.5, shadows=False)
    s.slab("Riser steps", deck, 2.8, 3.6, DECK, DECK + 0.5, 7.6, 8.8, (0.05, 0.05, 0.055))
    s.slab("Keys riser", deck, -9.4, -5.2, DECK, 2.7, 4.4, 7.6, (0.04, 0.04, 0.045))
    s.slab("Keys riser lip", deck, -9.4, -5.2, 2.64, 2.69, 4.37, 4.4, (0.2, 0.2, 0.2), emissive=CYAN, emissive_intensity=2,
           shadows=False)
    # LED wall behind the band and its frame
    s.slab("LED wall frame", deck, -13.6, 13.6, DECK, 16.4, 13.55, 14.0, (0.015, 0.015, 0.018))
    led = s.prop("LED wall", deck, M("LedWall"), (0, 9.15, 13.5), 0, 1.0)
    led.components[0]["Scale"] = [26.4, 13.2, 1.0]

    # the arched roof on four lattice towers
    rig = s.group("Stage roof", g)
    for x in (-18.0, 18.0):
        for z in (0.6, 13.4):
            for dx in (-0.55, 0.55):
                for dz in (-0.55, 0.55):
                    s.box("Tower post", rig, (x + dx, 10.5, z + dz), (0.14, 21.0, 0.14), (0.42, 0.43, 0.46), metallic=0.6, rough=0.4)
            for y in range(2, 21, 3):
                s.box("Tower rung", rig, (x, y, z), (1.25, 0.08, 1.25), (0.3, 0.31, 0.34), metallic=0.6, rough=0.4)
        s.box("Side truss", rig, (x, 19.0, 7.0), (1.0, 1.0, 13.0), (0.4, 0.41, 0.44), metallic=0.6, rough=0.4)
    for z, nm in ((0.6, "Front truss"), (7.0, "Mid truss"), (13.4, "Back truss")):
        s.box(nm, rig, (0, 18.2 if z != 7.0 else 19.6, z), (36.0, 0.9, 0.9), (0.42, 0.43, 0.46), metallic=0.6, rough=0.4)
    roof = Mesh("StageArch", "The stage roof: an arched skin over the towers.")
    n = 18
    for i in range(n):
        x0, x1 = -19.0 + 38.0 * i / n, -19.0 + 38.0 * (i + 1) / n
        y0, y1 = 20.0 + 3.2 * math.cos(x0 / 19.0 * math.pi / 2), 20.0 + 3.2 * math.cos(x1 / 19.0 * math.pi / 2)
        roof.face([(x0, y0, -0.6), (x1, y1, -0.6), (x1, y1, 14.6), (x0, y0, 14.6)], "Pal", "roof", hint=(0, 1, 0))
        roof.face([(x0, y0 - 0.25, -0.6), (x1, y1 - 0.25, -0.6), (x1, y1 - 0.25, 14.6), (x0, y0 - 0.25, 14.6)], "Pal", "roof_dk", hint=(0, -1, 0))
        roof.face([(x0, y0 - 0.25, -0.6), (x1, y1 - 0.25, -0.6), (x1, y1, -0.6), (x0, y0, -0.6)], "Pal", "char", hint=(0, 0, -1))
        roof.face([(x0, y0 - 1.1, -0.62), (x1, y1 - 1.1, -0.62), (x1, y1 - 0.3, -0.62), (x0, y0 - 0.3, -0.62)], "Glow",
                  "amber" if i % 2 else "gold", hint=(0, 0, -1))
    for x in (-19.0, 19.0):
        roof.face([(x, 18.5, -0.6), (x, 18.5, 14.6), (x, 20.0, 14.6), (x, 20.0, -0.6)], "Pal", "char", hint=(math.copysign(1, x), 0, 0))
    write_obj(roof, MATS)
    s.prop("Arch", rig, M("StageArch"), (0, 0, 0))

    # line arrays and side fills
    pa = s.group("PA", g)
    for side in (-1, 1):
        for i in range(12):
            tilt = 1.5 * i * i / 11
            s.box("Line array box", pa, (side * 15.6, 17.0 - i * 0.52, 0.9 + 0.012 * i * i), (1.3, 0.48, 0.8),
                  (0.03, 0.03, 0.033), rot=(tilt, 0, 0), rough=0.8)
        s.box("Array bumper", pa, (side * 15.6, 17.45, 0.9), (1.4, 0.12, 0.9), (0.4, 0.41, 0.44), metallic=0.6)
        s.box("Array hoist", pa, (side * 15.6, 17.8, 0.9), (0.05, 0.5, 0.05), (0.4, 0.41, 0.44))
        for i in range(3):
            s.prop("Sub stack", pa, V("Speaker"), (side * (13.0 + i * 1.1), DECK, 0.8), 0, 1.0)
            s.prop("Sub stack top", pa, V("Speaker"), (side * (13.0 + i * 1.1), DECK + 1.0, 0.8), 0, 1.0)

    # backline and kit dressing
    bl = s.group("Backline", g)
    for x in (-6.4, -5.6):
        s.prop("Guitar cab", bl, V("GuitarCab"), (x, DECK, 9.2), 180, 1.3)
        s.prop("Guitar cab", bl, V("GuitarCab"), (x, DECK + 0.97, 9.2), 180, 1.3)
    s.prop("Amp head", bl, V("AmpHead"), (-6.0, DECK + 1.95, 9.2), 180, 1.3)
    for x in (5.4, 6.4):
        s.prop("Bass cab", bl, V("Speaker"), (x, DECK, 9.2), 180, 1.2)
    s.prop("Bass head", bl, V("AmpHead"), (5.9, DECK + 1.2, 9.2), 180, 1.3)
    for pos, yaw in [((-4.6, DECK, 2.3), 0), ((4.6, DECK, 2.5), 0), ((-0.6, DECK, 0.7), 8), ((0.6, DECK, 0.7), -8),
                     ((-7.2, 2.7, 4.6), 0), ((1.9, RISER, 5.4), -20)]:
        s.prop("Wedge", bl, V("Wedge"), pos, yaw + 180, 1.0)
    for x in (-3.4, 3.4):
        s.prop("Drum fill", bl, V("SpeakerTall"), (x, RISER, 7.6), 180 - 14 * x / 3.4, 1.0)
    for pos, yaw in [((-11.5, DECK, 11.5), 10), ((-10.2, DECK, 12.6), -4), ((11.0, DECK, 11.8), -12), ((12.4, DECK, 12.4), 6)]:
        s.prop("Road case", bl, V("RoadCase"), pos, yaw, 1.0)
    s.prop("Flight case", bl, V("FlightCaseWide"), (-1.8, RISER, 9.1), 90, 1.0)
    s.prop("Power distro", bl, V("PowerDistro"), (13.2, DECK, 12.6), -90, 1.0)
    s.prop("Fan", bl, V("StageFan"), (-2.3, RISER, 9.0), 160, 1.0)
    for pos in [(-12.4, DECK, 5.0), (12.6, DECK, 5.4)]:
        s.prop("Cable coil", bl, V("CableCoil"), pos, 30, 1.0)

    kit = s.group("Kit dressing", g)
    s.prop("Drum rug", kit, V("DrumRug"), (0, RISER + 0.005, 6.5), 0, 1.0)
    s.prop("Water", kit, V("Bottle"), (1.55, RISER, 7.9), 0, 1.0)
    s.prop("Water", kit, V("Bottle"), (1.66, RISER, 7.95), 0, 1.0)
    s.box("Towel over the riser rail", kit, (-1.95, RISER + 0.62, 8.4), (0.5, 0.02, 0.35), (0.85, 0.85, 0.82), rot=(0, 20, 8))
    s.box("Setlist taped to the riser", kit, (0.9, RISER + 0.006, 5.35), (0.3, 0.005, 0.42), (0.92, 0.92, 0.9), rot=(0, 6, 0))
    # the loonie on its stand by the hi-hat, swinging
    ls = s.group("Loonie on its stand", kit, (1.55, RISER, 6.55))
    s.prop("Stand", ls, M("LoonieStand"), (0, 0, 0), 90, 1.0)
    swing = s.entity("Swing", ls, (0, 1.33, 0.32))
    s.prop("Loonie", swing, M("Loonie"), (0, 0, 0), 0, 0.2)
    swing_seq(ls, swing, 2.3, 9.0)
    return g


def swing_seq(holder, target, seconds, degrees):
    frames = round(seconds * 30)
    keys = []
    for i, (t, a) in enumerate(((0, 0), (0.25, degrees), (0.5, 0), (0.75, -degrees), (1.0, 0))):
        keys.append({"Frame": round(t * frames), "Value": quat((0, 0, a)), "Interpolation": "SmoothStep"})
    name = f"Swing{int(seconds * 10)}"
    clip = {"Version": 1, "Name": name, "FrameRate": 30, "DurationFrames": frames,
            "Tracks": [{"Binding": "Swing", "Component": "Transform", "Property": "Rotation", "Keys": keys}]}
    path = os.path.join(VENUE, "Motion", name + ".sequence")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    art.save_text(path, json.dumps(clip, indent=1) + "\n")
    holder.add({"Type": "Sequence", "Clip": f"Assets/Venues/{ID}/Motion/{name}.sequence", "PlayOnStart": True, "Loop": True,
                "Speed": 1.0, "Bindings": [{"Slot": "Swing", "Target": target.guid}]})


def quat(rot):
    x, y, z = [math.radians(a) / 2 for a in rot]
    a, b = math.sin(x), math.cos(x)
    c, d = math.sin(y), math.cos(y)
    e, f = math.sin(z), math.cos(z)
    return [round(v, 7) for v in (a * d * f - b * c * e, b * c * f + a * d * e, b * d * e - a * c * f, b * d * f + a * c * e)]


SCREEN_W, SCREEN_H = 14.0, 7.875
SCREENS = [(-1, (-25.6, 12.4, 2.0), -12.0), (1, (25.6, 12.4, 2.0), 12.0)]


def local_to_venue(centre, yaw, local):
    cs, sn = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    x, y, z = local
    return (centre[0] + x * cs + z * sn, centre[1] + y, centre[2] - x * sn + z * cs)


def screens(s, root, marks):
    g = s.group("Side screens", root)
    for side, centre, yaw in SCREENS:
        rig = s.entity(f"Screen rig {'W' if side < 0 else 'E'}", g, centre, (0, yaw, 0))
        s.box("Screen backing", rig, (0, 0, 0.45), (SCREEN_W + 0.8, SCREEN_H + 0.8, 0.6), (0.012, 0.012, 0.014))
        s.box("Screen bezel top", rig, (0, SCREEN_H / 2 + 0.3, 0.1), (SCREEN_W + 0.8, 0.2, 0.3), (0.05, 0.05, 0.055))
        s.box("Screen bezel bottom", rig, (0, -SCREEN_H / 2 - 0.3, 0.1), (SCREEN_W + 0.8, 0.2, 0.3), (0.05, 0.05, 0.055))
        for x in (-SCREEN_W / 2 - 0.7, SCREEN_W / 2 + 0.7):
            for dx in (-0.35, 0.35):
                s.box("Screen tower post", rig, (x + dx, -centre[1] / 2 + 4.6, 0.6), (0.12, centre[1] + 9.0, 0.12), (0.42, 0.43, 0.46), metallic=0.6)
            for yy in range(-12, 9, 3):
                s.box("Screen tower rung", rig, (x, yy, 0.6), (0.82, 0.07, 0.3), (0.3, 0.31, 0.34), metallic=0.6)
        s.box("Screen header truss", rig, (0, SCREEN_H / 2 + 1.0, 0.6), (SCREEN_W + 2.4, 0.7, 0.7), (0.42, 0.43, 0.46), metallic=0.6)
        s.screen(f"Side screen {'W' if side < 0 else 'E'}", marks, centre, SCREEN_W, SCREEN_H, "Program" if side < 0 else "Stage", 1.9, yaw)

        # the inserts: picture-in-picture panels just in front of the screen's outer upper corner
        outer = -side
        iw, ih = 6.0, 3.375
        pip = (outer * (SCREEN_W / 2 - iw / 2 - 0.25), SCREEN_H / 2 - ih / 2 - 0.25, -0.12)

        def insert(flag, nm, when=True, parent=rig, inner_flag=None):
            grp = s.story(f"Insert {nm} ({flag})", parent, flag, when, 0.35, pip)
            if inner_flag:
                grp = s.story(f"Insert {nm} until {inner_flag}", grp, inner_flag, False, 0.35, (0, 0, 0))
            s.box("Insert keyline", grp, (0, 0, 0.04), (iw + 0.24, ih + 0.24, 0.04), (0.2, 0.15, 0.05), emissive=GOLD,
                  emissive_intensity=1.4, shadows=False)
            q = s.prop(f"Insert {nm}", grp, M("Insert_" + nm), (0, 0, 0), 0, 1.0)
            q.components[0]["Scale"] = [iw, ih, 1.0]
        insert("mug_on_screen", "Mug", inner_flag="loonie_on_screen")
        insert("loonie_on_screen", "Loonie", inner_flag="bucket_answered")
        insert("bucket_answered", "Bucket")
        # stands_in_dialogue: the screen's inner lower corner shows its own stand's card stunt
        sw, sh = 5.0, 2.8125
        lower = (side * (SCREEN_W / 2 - sw / 2 - 0.25), -SCREEN_H / 2 + sh / 2 + 0.25, -0.12)
        grp = s.story(f"Stand cam ({'W' if side < 0 else 'E'})", rig, "stands_in_dialogue", True, 0.35, lower)
        grp = s.story("Stand cam until the finale", grp, "bucket_answered", False, 0.35, (0, 0, 0))
        s.box("Stand cam keyline", grp, (0, 0, 0.04), (sw + 0.2, sh + 0.2, 0.04), (0.1, 0.1, 0.1),
              emissive=AMBER if side < 0 else CYAN, emissive_intensity=1.5, shadows=False)
        q = s.prop("Stand cam", grp, M("Insert_Stand" + ("W" if side < 0 else "E")), (0, 0, 0), 0, 1.0)
        q.components[0]["Scale"] = [sw, sh, 1.0]


def field(s, root):
    g = s.group("Field", root)
    # the barricade and the pit
    bar = s.group("Barricade", g)
    for i in range(17):
        x = -16.0 + i * 2.0
        s.box("Barricade panel", bar, (x, 0.6, -1.75), (1.96, 1.15, 0.08), (0.55, 0.56, 0.6), metallic=0.7, rough=0.35)
        s.box("Barricade foot", bar, (x, 0.04, -2.2), (1.9, 0.08, 0.9), (0.4, 0.41, 0.44), metallic=0.6)
        s.box("Barricade lip", bar, (x, 1.2, -1.85), (1.96, 0.06, 0.32), (0.62, 0.63, 0.66), metallic=0.7, rough=0.3)
    s.prop("Pit camera", g, V("CameraTripod"), (-4.6, 0, -0.9), 200, 1.0)
    s.prop("Pit camera", g, V("CameraTripod"), (7.5, 0, -1.0), 160, 1.0)
    for pos, yaw in [((-14.6, 0, -0.6), 10), ((14.0, 0, -0.7), -20)]:
        s.prop("Pit case", g, V("RoadCase"), pos, yaw, 1.0)
    # FOH tower
    foh = s.group("FOH tower", g)
    s.slab("FOH deck", foh, -4.0, 4.0, 2.9, 3.2, -45.0, -39.0, (0.06, 0.06, 0.065))
    for x in (-3.8, 3.8):
        for z in (-44.8, -39.2):
            s.box("FOH leg", foh, (x, 1.45, z), (0.14, 2.9, 0.14), (0.42, 0.43, 0.46), metallic=0.6)
            s.box("FOH upright", foh, (x, 5.4, z), (0.12, 4.4, 0.12), (0.42, 0.43, 0.46), metallic=0.6)
    s.slab("FOH roof", foh, -4.2, 4.2, 7.6, 7.9, -45.2, -38.8, (0.03, 0.03, 0.035))
    s.slab("FOH skirt", foh, -4.0, 4.0, 0, 2.9, -38.98, -38.95, (0.02, 0.02, 0.024))
    s.slab("FOH desk", foh, -2.6, 2.6, 3.2, 4.1, -41.3, -40.2, (0.05, 0.05, 0.055))
    for i in range(14):
        s.box("Desk meter", foh, (-2.3 + i * 0.35, 4.13, -40.5 + (i % 3) * 0.12), (0.12, 0.03, 0.06), (0.1, 0.1, 0.1),
              emissive=CYAN if i % 3 else AMBER, emissive_intensity=2.5, shadows=False)
    # delay / light towers on the field
    for side in (-1, 1):
        t = s.group(f"Light tower {'W' if side < 0 else 'E'}", g)
        x, z = side * TOWER[0], TOWER[1]
        for dx in (-1.3, 1.3):
            for dz in (-1.3, 1.3):
                s.box("Tower leg", t, (x + dx, 8.0, z + dz), (0.16, 16.0, 0.16), (0.42, 0.43, 0.46), metallic=0.6)
        for y in range(2, 17, 3):
            s.box("Tower deck", t, (x, y, z), (2.8, 0.08, 2.8), (0.3, 0.31, 0.34), metallic=0.6)
        for i in range(6):
            s.box("Delay array", t, (x, 14.6 - i * 0.5, z + 1.6), (1.1, 0.45, 0.7), (0.03, 0.03, 0.033), rot=(i * 1.2, 0, 0))
        for i, dx in enumerate((-1.0, -0.33, 0.33, 1.0)):
            s.box("Tower lamp", t, (x + dx, 16.4, z + 1.2), (0.5, 0.5, 0.45), (0.05, 0.05, 0.05))
            s.box("Tower lamp lens", t, (x + dx, 16.4, z + 1.44), (0.4, 0.4, 0.02), (0.2, 0.2, 0.2), emissive=WARM if i % 2 else ICE,
                  emissive_intensity=3.0, shadows=False)
        s.box("Tower banner", t, (x, 9.0, z - 1.36), (2.5, 4.0, 0.04), (0.02, 0.02, 0.025))
    return g


def commuter(s, root):
    """The mustard-scarf commuter at the barricade (Mother_02 / 02_B) and her mug."""
    g = s.group("The commuter at the barricade", root)
    base = LOCAL + "Commuter/"
    who = s.entity("Mustard-scarf commuter", g, (-6.0, 0, -2.62), (0, 8, 0))
    s.entity("Legs", who).add({"Type": "Model", "ModelPath": base + "Legs.obj"})
    torso = s.entity("Torso", who, (0, 0.8763, 0), (-4, 0, 0))
    torso.add({"Type": "Model", "ModelPath": base + "Torso.obj"})
    head = s.entity("Head", torso, (0, 0.5727, -0.0242), (-8, -6, 0))
    head.add({"Type": "Model", "ModelPath": base + "Head.obj"})
    left = s.entity("ArmL", torso, (-0.191, 0.5141, -0.0484), (6, 0, -8))
    left.add({"Type": "Model", "ModelPath": base + "ArmL.obj"})
    # scarf: a thick mustard wrap at the neck and a tail down the front
    s.box("Scarf wrap", torso, (0, 0.47, -0.02), (0.34, 0.11, 0.26), (0.62, 0.42, 0.05), rough=1.0)
    s.box("Scarf knot", torso, (0.06, 0.4, 0.12), (0.12, 0.12, 0.08), (0.55, 0.36, 0.04), rough=1.0)
    s.box("Scarf tail", torso, (0.08, 0.18, 0.15), (0.11, 0.42, 0.04), (0.62, 0.42, 0.05), rot=(-6, 0, 4), rough=1.0)
    s.box("Scarf tail stripe", torso, (0.08, 0.06, 0.172), (0.112, 0.05, 0.01), (0.4, 0.26, 0.03))

    def arm(name, parent, rot, mug_rot):
        a = s.entity(name, parent, (0.191, 0.5141, -0.0484), rot)
        a.add({"Type": "Model", "ModelPath": base + "ArmR.obj"})
        hand = s.entity("Hand", a, (0.0, -0.62, 0.02), mug_rot)
        s.prop("Travel mug", hand, M("TravelMug"), (0, -0.08, 0.0), 0, 1.0)
    held = s.story("Mug held (until the bucket answers)", torso, "bucket_answered", False, 0.3, (0, 0, 0))
    arm("ArmR", held, (-62, 0, 6), (62, 0, 0))
    up = s.story("Mug goes up (bucket_answered)", torso, "bucket_answered", True, 0.6, (0, 0, 0))
    arm("ArmR raised", up, (-172, 0, -10), (172, 0, 0))
    # the screen found her: a camera spot from the pit, gated with the story
    found = s.story("Spot finds her (mug_on_screen)", g, "mug_on_screen", True, 1.0, (-6.0, 0, -2.6))
    s.light("Pit spot on the commuter", found, (1.8, 4.5, 2.6), "Spot", WARM, 260.0, 12,
            rot=look_rotation((-4.2, 4.5, 0.0), (-6.0, 1.5, -2.6)), inner=8, outer=16)


def story_stage(s, root):
    """The loonie that drops from the rig, the bucket's two places, the beams through the roof."""
    g = s.group("Story on stage", root)
    # loonie_on_screen: a giant drilled loonie drops out of the roof, swinging over the kit
    drop = s.story("Giant loonie drops (loonie_on_screen)", g, "loonie_on_screen", True, 2.2, (0, 19.0, 11.4))
    holder = s.entity("Loonie swing", drop, (0, 0, 0))
    swing = s.entity("Swing", holder, (0, 0, 0))
    chain = s.prop("Chain", swing, M("LoonieChain"), (0, 0, 0), 0, 1.0)
    chain.components[0]["Scale"] = [3.0, 3.6, 3.0]
    s.prop("Giant loonie", swing, M("Loonie"), (0, -3.6, 0), 0, 4.6)
    swing_seq(holder, swing, 4.6, 5.0)
    s.light("Gold key on the loonie", drop, (0, -4.0, -6.0), "Spot", GOLD, 420.0, 20,
            rot=look_rotation((0, 15.0, 5.4), (0, 13.0, 11.4)), inner=12, outer=24)
    s.light("Gold rim on the loonie", drop, (0, -8.0, 1.6), "Point", (1.0, 0.7, 0.3), 30.0, 8)

    # the bucket: on the riser floor by the floor tom, then up on a case under its own spot
    floor_pos = (-1.2, RISER, 6.7)
    low = s.story("Bucket by the floor tom", g, "bucket_answered", False, 0.4, floor_pos)
    s.prop("Subway bucket", low, M("Bucket"), (0, 0, 0), 15, 1.0)
    s.prop("Sticks on the bucket", low, M("Sticks"), (0, 0.37, 0), 20, 1.0)
    up_pos = (-1.25, RISER, 6.4)
    up = s.story("Bucket answered", g, "bucket_answered", True, 0.6, up_pos)
    s.box("Case under the bucket", up, (0, 0.17, 0), (0.62, 0.34, 0.5), (0.03, 0.03, 0.035), rough=0.5)
    s.box("Case corners", up, (0, 0.34, 0), (0.64, 0.02, 0.52), (0.5, 0.5, 0.52), metallic=0.8)
    s.prop("Subway bucket", up, M("Bucket"), (0, 0.35, 0), -12, 1.0)
    s.light("Spot on the bucket", up, (0, 5.4, -2.2), "Spot", WARM, 700.0, 10,
            rot=look_rotation((-1.25, 8.6, 4.2), (-1.25, 3.8, 6.4)), inner=6, outer=13)

    # bucket_answered: gold beams up through the open roof from the roof ring and the towers
    beams = s.story("Gold beams through the roof (bucket_answered)", g, "bucket_answered", True, 2.5, (0, 0, -26))
    spots = [(-30, 41, -60), (30, 41, -60), (-34, 41, -12), (34, 41, -12), (-34, 41, 16), (34, 41, 16)]
    for i, (x, y, z) in enumerate(spots):
        tx, tz = x * 0.15, -26 + (z + 26) * 0.2
        b = s.entity(f"Beam {i + 1}", beams, (x, y, z + 26), look_rotation((x, y, z), (tx, 140.0, tz)))
        b.components[0]["Rotation"][0] += 90.0  # the beam mesh stands along +y; tip it onto local +z
        b.components[0]["Scale"] = [1.0, 120.0, 1.0]
        b.add({"Type": "Model", "ModelPath": M("SkyBeam"), "Compact": True,
               "Parts": {"SkyBeam.obj#0/SkyBeam#0/@#0": {"CastShadows": False, "Material": {
                   "Type": "StandardMaterial", "DiffuseColor": [1.0, 0.78, 0.35], "Roughness": 1.0, "RenderMode": 1, "BlendMode": 2,
                   "FaceMode": 2, "Opacity": 0.22, "EmissiveColor": [1.0, 0.75, 0.3], "EmissiveIntensity": 2.2}}}})


def fx(s, root):
    """Accents: fireworks over the open roof and confetti from the stage lip on the big peaks."""
    g = s.group("Peaks", root)
    for i, (pos, col, col2) in enumerate([((-20.0, 38.0, 22.0), (1.0, 0.75, 0.3), (1.0, 0.4, 0.1)),
                                          ((0.0, 45.0, 28.0), (0.5, 0.85, 1.0), (1.0, 1.0, 1.0)),
                                          ((20.0, 38.0, 22.0), (1.0, 0.3, 0.6), (1.0, 0.8, 0.4))]):
        e = s.entity(f"Firework {i + 1}", g, pos)
        e.add({"Type": "VenueAccent", "Particles": 360})
        e.add({"Type": "ParticleSystem", "Simulation": "CPU", "SimulationSpace": "World", "Shape": "Sphere", "ShapeRadius": 0.4,
               "EmitFromShell": True, "Lifetime": [1.6, 2.6], "Speed": [9.0, 13.0], "Size": [0.35, 0.6], "StartColor": list(col),
               "StartColor2": list(col2), "EndColor": list(col2), "Gravity": 0.12, "Drag": 0.9, "NoiseStrength": 0.2,
               "StartAlpha": 1, "EndAlpha": 0, "FadeIn": 0.02, "EndSize": 0.3, "Intensity": 3.0, "Blend": "Additive",
               "EmissionRate": 0, "BurstCount": 0, "MaxParticles": 512, "SoftParticleDistance": 0, "Alignment": "Stretched",
               "StretchFactor": 0.06})
    for i, x in enumerate((-9.0, 9.0)):
        e = s.entity(f"Confetti cannon {i + 1}", g, (x, DECK + 0.1, 0.4), (-38, 0, -10 if x > 0 else 10))
        e.add({"Type": "VenueAccent", "Particles": 300})
        e.add({"Type": "ParticleSystem", "Simulation": "CPU", "SimulationSpace": "World", "Shape": "Cone", "ConeAngle": 18,
               "ShapeRadius": 0.12, "Lifetime": [3.5, 5.5], "Speed": [11.0, 16.0], "Size": [0.08, 0.16],
               "StartColor": [1.0, 0.8, 0.3], "StartColor2": [1.0, 1.0, 1.0], "EndColor": [1.0, 0.7, 0.2],
               "AngularVelocity": [-260, 260], "Gravity": 0.25, "Drag": 0.7, "NoiseStrength": 1.2, "NoiseFrequency": 0.8,
               "StartAlpha": 1, "EndAlpha": 0, "FadeIn": 0.01, "EndSize": 0.8, "Intensity": 1.3,
               "Texture": "Assets/Textures/Venue/Confetti.png", "Blend": "Alpha", "EmissionRate": 0, "BurstCount": 0,
               "MaxParticles": 512, "SoftParticleDistance": 0})
    g.add({"Type": "VenueAccent", "Beats": 16, "FullLightingOnly": False})


def lights(s, root):
    L = s.group("Lights", root)
    s.light("Moon over the open roof", L, (-40, 80, -60), "Directional", (0.55, 0.62, 0.9), 1.3, rot=(52, 28, 0), shadows=True)
    show = s.group("Show rig", L)

    def spot(n, pos, to, col, power, reach, inner, outer, kind, group=0):
        s.light(n, show, pos, "Spot", col, power, reach, rot=look_rotation(pos, to), inner=inner, outer=outer, show=kind, group=group)
    cols = [(1.0, 0.45, 0.15), (0.3, 0.5, 1.0), (1.0, 0.3, 0.6)]
    for i, x in enumerate((-12.0, -7.0, -2.5, 2.5, 7.0, 12.0)):
        spot(f"Front wash {i + 1}", (x, 17.6, 0.6), (x * 0.35, 3.0, 4.6), cols[i % 3], 9000.0, 40, 22, 40, "Wash", i % 3)
    for i, x in enumerate((-2.5, 2.5)):
        spot(f"Back wash {i + 1}", (x, 18.6, 13.4), (0, RISER, 7.0), (0.9, 0.7, 1.0), 6000.0, 30, 18, 34, "Wash", 1)
    for i, x in enumerate((-14.0, -10.0, -6.0, -2.0, 2.0, 6.0, 10.0, 14.0)):
        spot(f"Beam {i + 1}", (x, 18.6, 13.0), (x * 2.6, 46.0, -60.0), (0.9, 0.95, 1.0) if i % 2 else MAGENTA, 30000.0, 90, 2.5, 5,
             "Beam", i % 2)
    members = [(0, 4.9, 7.4), (0, 3.6, 1.7), (-4.6, 3.6, 3.4), (4.6, 3.6, 3.6), (-7.2, 4.0, 6.0)]
    for i, (pos, tgt) in enumerate(zip([(-2.6, 8.2, -42.5), (2.6, 8.2, -42.5), (-TOWER[0], 17.2, TOWER[1]), (TOWER[0], 17.2, TOWER[1]), (0.0, 8.2, -42.5)], members)):
        spot(f"Follow spot {i + 1}", pos, tgt, (1.0, 0.95, 0.88), 60000.0, 70, 2.2, 3.6, "Spot", i)
    for i, x in enumerate((-15.0, -9.0, -3.0, 3.0, 9.0, 15.0)):
        spot(f"Blinder {i + 1}", (x, 17.2, 0.2), (x * 1.4, 0.0, -30.0), (1.0, 0.78, 0.5), 22000.0, 70, 25, 48, "Blinder", i % 2)
    for i, x in enumerate((-18.0, -6.0, 6.0, 18.0)):
        s.light(f"Strobe {i + 1}", show, (x, 18.0, 0.0), "Point", (0.95, 0.97, 1.0), 9000.0, 45, show="Strobe", group=i % 2)
    for i, (x, z) in enumerate(((-TOWER[0], TOWER[1]), (TOWER[0], TOWER[1]))):
        spot(f"Crowd wash {i + 1}", (x, 16.6, z), (x * 0.4, 0.0, -10.0), (0.4, 0.3, 1.0), 26000.0, 60, 30, 55, "Wash", 2)
        spot(f"Crowd wash back {i + 1}", (x, 16.6, z), (x * 0.8, 0.0, -62.0), (1.0, 0.4, 0.2), 26000.0, 60, 30, 55, "Wash", 0)

    # plain practicals (not cued)
    p = s.group("Practicals", L)
    s.light("LED wall spill", p, (0, 9.0, 11.6), "Point", (0.45, 0.25, 1.0), 260.0, 16)
    s.light("Stage worklight W", p, (-15.0, 6.0, 12.0), "Point", WARM, 90.0, 10)
    s.light("Stage worklight E", p, (15.0, 6.0, 12.0), "Point", WARM, 90.0, 10)
    s.light("Kit fill", p, (0.0, 7.5, 3.2), "Spot", WARM, 900.0, 14, rot=look_rotation((0, 7.5, 3.2), (0, 3.8, 7.4)), inner=18, outer=34)
    s.light("FOH lamp", p, (0, 7.2, -42.0), "Point", WARM, 30.0, 6)
    s.light("Bowl glow W", p, (-55.0, 26.0, -26.0), "Point", (0.35, 0.4, 0.7), 9000.0, 70)
    s.light("Bowl glow E", p, (55.0, 26.0, -26.0), "Point", (0.35, 0.4, 0.7), 9000.0, 70)
    s.light("Bowl glow far", p, (0.0, 26.0, -100.0), "Point", (0.35, 0.4, 0.7), 9000.0, 70)
    s.light("Bowl glow stage end", p, (0.0, 30.0, 60.0), "Point", (0.35, 0.4, 0.7), 7000.0, 60)


def markers(s, root):
    marks = s.group("Venue markers", root)
    s.info(marks, TITLE, "Drumsmith", outdoor=True, room_back=-82.0, half_width=39.0, desk_z=-42.0,
           fog_color=(0.03, 0.026, 0.05), haze=0.85, sky_time=21.7, moon=1.1)
    s.spot(marks, "Drummer", DRUMMER)
    s.spot(marks, "Vocals", (0.0, DECK, 1.7))
    s.spot(marks, "Guitar", (-4.6, DECK, 3.4), 8)
    s.spot(marks, "Bass", (4.6, DECK, 3.6), -8)
    s.spot(marks, "Keys", (-7.2, 2.7, 6.0), 14)

    crowd = s.group("Crowd", marks)
    # posed front rows at the barricade, split around the commuter's spot
    s.crowd("Front rows W", crowd, ((-15.0 - 6.7) / 2, 0, (-9.0 - 2.6) / 2), 8.3, 6.4, 90, figures="Posed")
    s.crowd("Front rows behind her", crowd, (-6.0, 0, (-9.0 - 3.5) / 2), 1.4, 5.5, 9, figures="Posed")
    s.crowd("Front rows E", crowd, ((-5.3 + 15.0) / 2, 0, (-9.0 - 2.6) / 2), 20.3, 6.4, 220, figures="Posed")
    # the field: Mob figures, densest near the stage, around the FOH and the light towers
    for name, x0, x1, z0, z1, n, j in [
            ("Wing W", -38.0, -15.0, -9.0, -2.6, 150, 0.7), ("Wing E", 15.0, 38.0, -9.0, -2.6, 150, 0.7),
            ("Front field", -38.0, 38.0, -30.0, -9.0, 760, 0.8),
            ("FOH W", -38.0, -4.6, -47.0, -30.0, 230, 0.8), ("FOH E", 4.6, 38.0, -47.0, -30.0, 230, 0.8),
            ("Before the desk", -4.6, 4.6, -38.6, -30.0, 30, 0.6),
            ("Back field", -38.0, 38.0, -80.0, -47.0, 360, 1.0)]:
        s.crowd(name, crowd, ((x0 + x1) / 2, 0, (z0 + z1) / 2), x1 - x0, z1 - z0, n, j)
    # the lower side stands: standing rows of Mob in front of the painted seats
    for side in (-1, 1):
        for r in (1, 3, 5, 7, 9):
            d = LOWER_DEPTH * r + LOWER_DEPTH * 0.55
            x = side * (39.15 + d)
            s.crowd(f"Lower {'W' if side < 0 else 'E'} row {r + 1}", crowd, (x, row_y_lower(r), -27.0), 0.6, 60.0, 34, 0.4)

    cams = s.group("Camera positions", marks)
    for tag, kind, eye, aim, lens in [
            ("foh-wide", "Wide", (0.0, 17.0, -50.0), (0.0, 11.0, 6.0), 66),
            ("upper-crane", "Crane", (-24.0, 25.0, -26.0), (0.0, 6.0, 6.0), 55),
            ("desk-long", "Desk", (2.6, 7.4, -41.0), (0.0, 4.3, 6.0), 26),
            ("sticks", "Close", (2.3, 5.0, 4.3), (0.0, 4.1, 7.4), 44),
            ("barricade-mug", "Custom", (-3.4, 2.5, -0.6), (-6.2, 1.9, -3.6), 48),
            ("upper-deck-phones", "Custom", (9.0, 5.5, 1.0), (-34.0, 22.0, -52.0), 72),
            ("stands-dialogue", "Custom", (0.0, 9.0, -60.0), (0.0, 10.0, -20.0), 80),
            ("loonie-swing", "Custom", (3.6, 9.6, 3.6), (0.0, 13.0, 11.4), 46),
            ("bucket-answer", "Custom", (-2.7, 4.4, 4.5), (-1.2, 3.7, 6.6), 40),
            ("open-roof", "Custom", (11.0, 2.6, -3.5), (-6.0, 36.0, -40.0), 76)]:
        s.camera_spot(tag, cams, eye, aim, kind, lens, tag)
    # the intro: out of the players' tunnel on the east side, onto the field, up at the bowl
    for i, (eye, aim, lens) in enumerate([
            ((41.5, 1.7, -12.0), (36.0, 1.8, -12.5), 64), ((38.6, 1.7, -12.6), (30.0, 2.4, -10.0), 63),
            ((35.8, 1.75, -12.4), (20.0, 6.0, -4.0), 62), ((33.2, 1.8, -11.4), (0.0, 14.0, 2.0), 60),
            ((30.8, 1.9, -10.2), (-30.0, 24.0, -30.0), 64), ((28.6, 2.0, -9.0), (0.0, 5.0, 6.0), 56)]):
        s.camera_spot(f"Arrival {i + 1:02}", cams, eye, aim, "Custom", lens, f"arrival/{i + 1:02}")
    return marks


def models_readme():
    text = """# StoryStadium models

Everything here is generated by `Tools/Venues/make_story_stadium.py` (with
`Tools/Venues/story_stadium_art.py`); rerun it rather than editing the files.

- `BowlLower`, `BowlUpper`, `SeatsLower`, `SeatsUpper`, `RoofRing`, `FieldFloor`, `StageArch`, `UpperPhones1-8`, `Cards*`,
  `GoldCards*`, `Bucket`, `Sticks`, `TravelMug`, `Loonie`, `LoonieStand`, `LoonieChain`,
  `SkyBeam`, `Insert_*`, `LedWall`: original geometry, written by the generator. No pack source.
- `Palette.png`, `Seats.png`, `Floor.png`: drawn by the generator (pure
  Python). `Insert_*.png`, `Mosaic*.png`, `Ribbon.png`, `LedWall.png`: drawn with ImageMagick by
  the generator (system Noto Sans Black / DejaVu Sans Bold). No real brands, logos or likenesses;
  the coin and the skyline are generic.
- `Commuter/Legs|Torso|Head|ArmL|ArmR.obj`: copied unchanged from
  `Assets/Models/People/Crowd/Mother_02/` (Synty Polygon Town BodyType1_Mother_02 pieces; the
  owner's Synty licence), with a local `Crowd.mtl` that binds `PolygonTown_02_B.png` from
  `Assets/Models/Venue/` in place (owner's Synty licence), her atlas in the venue casting.

Shared props are referenced in place, read-only, from `Assets/Models/Venue/` (see its README).
"""
    art.save_text(os.path.join(MODELS, "README.md"), text)


def build():
    os.makedirs(MODELS, exist_ok=True)
    textures()
    props_meshes()
    commuter_parts()
    models_readme()
    s = Scene(seed=12012)
    root = s.group(TITLE)
    house = s.group("The bowl, roof open", root)
    bowl(s, house)
    phones(s, house)
    mosaics(s, house)
    stage(s, root)
    marks = markers(s, root)
    screens(s, root, marks)
    field(s, root)
    commuter(s, root)
    story_stage(s, root)
    fx(s, root)
    lights(s, root)
    return s


def main():
    scene = build()
    scene.write(os.path.join(VENUE, ID + ".lvl"))
    preview = "Preview.jpg" if os.path.exists(os.path.join(VENUE, "Preview.jpg")) else None
    write_venue_json(VENUE, TITLE, ID + ".lvl", author="Drumsmith", preview=preview, version=1,
                     ambience="Assets/Sounds/crowd.mp3")
    shows = sum(1 for e in scene.entities for c in e.components if c.get("Type") == "VenueShowLight")
    print(f"{len(scene.entities)} entities, {shows} show lights -> {VENUE}")


if __name__ == "__main__":
    main()
