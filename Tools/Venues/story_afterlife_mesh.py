"""Mesh and texture shop for Highway to the Afterlife (make_story_afterlife.py). Standard library
only, deterministic: a rerun writes the same bytes, and an unchanged file isn't touched.

Geometry is built in venue metres (+x crowd right, +y up, +z toward the band) and written the way
the other venues' meshes are (z mirrored, faces wound counter-clockwise seen from outside in the
file). Every file has one object and one material, so a Model's part path is predictable
(part()), which is how the generator overrides a part's material (glows, see-through, additive).

Colour comes either from a texture (uv given per vertex) or from the palette: a face painted with
an ink samples that swatch of AL_Palette.png.
"""
import math
import os
import struct
import zlib

# ---- palette --------------------------------------------------------------------------------
PALETTE = {
    'black': (0.02, 0.02, 0.025), 'rubber': (0.045, 0.045, 0.05), 'soot': (0.07, 0.06, 0.055), 'steel_dark': (0.14, 0.15, 0.17),
    'steel': (0.36, 0.38, 0.41), 'chrome': (0.72, 0.74, 0.78), 'white': (0.92, 0.92, 0.94), 'glass': (0.10, 0.16, 0.24),
    'cab_red': (0.55, 0.06, 0.05), 'cab_dark': (0.25, 0.03, 0.03), 'navy': (0.05, 0.07, 0.16), 'deck': (0.26, 0.19, 0.12),
    'deck_dark': (0.13, 0.09, 0.06), 'brass': (0.80, 0.62, 0.25), 'drum_red': (0.62, 0.07, 0.07), 'drum_skin': (0.86, 0.84, 0.76),
    'amp': (0.06, 0.06, 0.065), 'grille': (0.20, 0.19, 0.17), 'wood': (0.42, 0.26, 0.13), 'paper': (0.90, 0.88, 0.80),
    'rail': (0.55, 0.57, 0.60), 'post': (0.30, 0.31, 0.33), 'sign_green': (0.06, 0.32, 0.14), 'hivis': (0.85, 0.9, 0.1),
    'amb_red': (0.8, 0.1, 0.08), 'cone': (0.95, 0.35, 0.05), 'pine': (0.03, 0.07, 0.04), 'pine_dark': (0.015, 0.035, 0.022),
    'bark': (0.10, 0.07, 0.05), 'stone': (0.20, 0.15, 0.14), 'stone_dark': (0.09, 0.065, 0.065), 'stone_red': (0.30, 0.09, 0.07),
    'bone': (0.78, 0.72, 0.60), 'bone_dark': (0.42, 0.36, 0.28), 'horn': (0.32, 0.03, 0.03), 'iron': (0.10, 0.09, 0.09),
    'blood': (0.42, 0.02, 0.02), 'crimson': (0.65, 0.04, 0.05), 'gold': (1.0, 0.78, 0.32), 'gold_dark': (0.62, 0.42, 0.12),
    'marble': (0.93, 0.92, 0.88), 'marble_shade': (0.74, 0.74, 0.76), 'cloud': (0.96, 0.97, 1.0), 'sky': (0.45, 0.62, 0.92),
    'iris': (0.18, 0.5, 0.85), 'pupil': (0.01, 0.01, 0.03), 'ember': (1.0, 0.35, 0.05), 'fire': (1.0, 0.6, 0.15),
    'red_lamp': (1.0, 0.05, 0.05), 'blue_lamp': (0.1, 0.2, 1.0), 'lamp': (1.0, 0.92, 0.75), 'skin_red': (0.55, 0.08, 0.06),
    'wing_dark': (0.16, 0.02, 0.03), 'feather': (0.97, 0.97, 1.0), 'feather_tip': (0.82, 0.86, 0.96), 'velvet': (0.28, 0.02, 0.04),
}
NAMES = list(PALETTE)
GRID, CELL = 8, 8
PAL_W, PAL_H = GRID * CELL, ((len(NAMES) + GRID - 1) // GRID) * CELL


def ink_uv(ink):
    i = NAMES.index(ink)
    return ((i % GRID) * CELL + CELL / 2) / PAL_W, 1 - ((i // GRID) * CELL + CELL / 2) / PAL_H


# ---- files ----------------------------------------------------------------------------------
def save_bytes(path, data):
    path = str(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path) and open(path, 'rb').read() == data:
        return
    with open(path, 'wb') as f:
        f.write(data)
    # A stale cooked twin would be loaded instead of the new source.
    for twin in (path + '.assbin', path + '.dds'):
        if os.path.exists(twin):
            os.remove(twin)


def write_png(path, w, h, pixels, alpha=False):
    """pixels: a flat bytearray, w*h*(4 if alpha else 3). No metadata."""
    n = 4 if alpha else 3
    raw = b''.join(b'\x00' + bytes(pixels[y * w * n:(y + 1) * w * n]) for y in range(h))

    def chunk(tag, data):
        c = struct.pack('>I', len(data)) + tag + data
        return c + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6 if alpha else 2, 0, 0, 0))
    save_bytes(path, png + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def srgb(v):
    return int(round(255 * max(0.0, min(1.0, v)) ** (1 / 2.2)))


def palette_png(path):
    px = bytearray()
    for y in range(PAL_H):
        for x in range(PAL_W):
            i = (y // CELL) * GRID + x // CELL
            c = PALETTE[NAMES[i]] if i < len(NAMES) else (1, 0, 1)
            px += bytes(srgb(v) for v in c)
    write_png(path, PAL_W, PAL_H, px)


# ---- noise ----------------------------------------------------------------------------------
def _hash(*k):
    h = 0x9E3779B9
    for v in k:
        h = ((h ^ (int(v) & 0xFFFFFFFF)) * 0x85EBCA6B) & 0xFFFFFFFF
        h ^= h >> 13
        h = (h * 0xC2B2AE35) & 0xFFFFFFFF
        h ^= h >> 16
    return h / 4294967295.0


def noise3(x, y, z, seed=0):
    """Value noise, 0..1."""
    xi, yi, zi = math.floor(x), math.floor(y), math.floor(z)
    fx, fy, fz = x - xi, y - yi, z - zi
    fx, fy, fz = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy), fz * fz * (3 - 2 * fz)
    out = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (fx if dx else 1 - fx) * (fy if dy else 1 - fy) * (fz if dz else 1 - fz)
                out += w * _hash(xi + dx, yi + dy, zi + dz, seed)
    return out


def fbm3(x, y, z, seed=0, octaves=3):
    out, amp, total = 0.0, 1.0, 0.0
    for o in range(octaves):
        out += amp * noise3(x, y, z, seed + o * 17)
        total += amp
        amp *= 0.5
        x, y, z = x * 2.03, y * 2.03, z * 2.03
    return out / total


class Tile:
    """Tileable 2D fbm on a size x size image: lattices that wrap, bilinear with smoothstep."""

    def __init__(self, size, seed, base=4, octaves=5):
        self.size = size
        self.layers = []
        for o in range(octaves):
            n = base << o
            if n > size:
                break
            self.layers.append((n, [[_hash(i, j, seed, o) for i in range(n)] for j in range(n)], 0.5 ** o))
        self.total = sum(a for _, _, a in self.layers)

    def at(self, x, y):
        out = 0.0
        for n, lat, amp in self.layers:
            u, v = x * n / self.size, y * n / self.size
            i, j = int(u) % n, int(v) % n
            fu, fv = u - int(u), v - int(v)
            fu, fv = fu * fu * (3 - 2 * fu), fv * fv * (3 - 2 * fv)
            i1, j1 = (i + 1) % n, (j + 1) % n
            a = lat[j][i] * (1 - fu) + lat[j][i1] * fu
            b = lat[j1][i] * (1 - fu) + lat[j1][i1] * fu
            out += amp * (a * (1 - fv) + b * fv)
        return out / self.total


def cells(size, seed, n):
    """Tileable Voronoi: returns f(x, y) -> (nearest distance, second - nearest), in cell units."""
    pts = [[(_hash(i, j, seed, 1), _hash(i, j, seed, 2)) for i in range(n)] for j in range(n)]

    def at(x, y):
        u, v = x * n / size, y * n / size
        ci, cj = int(u), int(v)
        d1 = d2 = 9.0
        for dj in (-1, 0, 1):
            for di in (-1, 0, 1):
                px, py = pts[(cj + dj) % n][(ci + di) % n]
                d = math.hypot(ci + di + px - u, cj + dj + py - v)
                if d < d1:
                    d1, d2 = d, d1
                elif d < d2:
                    d2 = d
        return d1, d2 - d1
    return at


def texture(path, size, fn, alpha=False):
    """fn(x, y) -> (r, g, b[, a]) in linear 0..1; stored sRGB (alpha as is)."""
    px = bytearray()
    for y in range(size):
        for x in range(size):
            c = fn(x, y)
            px += bytes(srgb(v) for v in c[:3])     # (clamped: a sun brighter than 1 is white)
            if alpha:
                px.append(int(round(255 * max(0.0, min(1.0, c[3])))))
    write_png(path, size, size, px, alpha)


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def smooth(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


# A 5 x 7 font for the signs (capitals, digits and a little punctuation).
FONT = {
    'A': '0111010001100011111110001100011000100000', 'B': '1111010001100011111010001100011111000000', 'C': '0111010001100001000010000100010111000000',
    'D': '1111010001100011000110001100011111000000', 'E': '1111110000100001111010000100001111100000', 'F': '1111110000100001111010000100001000000000',
    'G': '0111010001100001011110001100010111100000', 'H': '1000110001100011111110001100011000100000', 'I': '0111000100001000010000100001000111000000',
    'K': '1000110010101001100010100100101000100000', 'L': '1000010000100001000010000100001111100000', 'M': '1000111011101011010110001100011000100000',
    'N': '1000111001101011001110001100011000100000', 'O': '0111010001100011000110001100010111000000', 'P': '1111010001100011111010000100001000000000',
    'R': '1111010001100011111010100100101000100000', 'S': '0111110000100000111000001000011111000000', 'T': '1111100100001000010000100001000010000000',
    'U': '1000110001100011000110001100010111000000', 'V': '1000110001100011000110001010100010000000', 'W': '1000110001100011010110101110111000100000',
    'X': '1000110001010100010001010100011000100000', 'Y': '1000110001010100010000100001000010000000', '6': '0111010000100001111010001100010111000000',
    '1': '0010001100001000010000100001000111000000', '0': '0111010001100111010111001100010111000000', '2': '0111010001000010001000100010001111100000',
    '.': '0000000000000000000000000001100011000000', ' ': '0' * 40,
}


def text_mask(lines, w, h, scale):
    """A set-pixel test for lines of text centred in a w x h image, glyphs scale px per dot."""
    lit = set()
    line_h = 9 * scale
    y0 = (h - line_h * len(lines)) // 2 + scale
    for li, line in enumerate(lines):
        x0 = (w - len(line) * 6 * scale) // 2
        for ci, ch in enumerate(line):
            bits = FONT.get(ch, FONT[' '])
            for r in range(7):
                for c in range(5):
                    if bits[r * 5 + c] == '1':
                        for dy in range(scale):
                            for dx in range(scale):
                                lit.add((x0 + (ci * 6 + c) * scale + dx, y0 + li * line_h + r * scale + dy))
    return lit


# ---- vectors --------------------------------------------------------------------------------
def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def mul(a, s): return (a[0] * s, a[1] * s, a[2] * s)
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def unit(a):
    length = math.sqrt(dot(a, a)) or 1.0
    return (a[0] / length, a[1] / length, a[2] / length)


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def rot(v, euler):
    """Euler degrees (x, y, z), applied X then Y then Z: the engine's Transform rotation."""
    x, y, z = v
    rx, ry, rz = (math.radians(a) for a in euler)
    if rx:
        c, s = math.cos(rx), math.sin(rx)
        y, z = y * c - z * s, y * s + z * c
    if ry:
        c, s = math.cos(ry), math.sin(ry)
        x, z = x * c + z * s, -x * s + z * c
    if rz:
        c, s = math.cos(rz), math.sin(rz)
        x, y = x * c - y * s, x * s + y * c
    return (x, y, z)


def basis(axis):
    a = unit(axis)
    ref = (0, 1, 0) if abs(a[1]) < 0.9 else (1, 0, 0)
    u = unit(cross(ref, a))
    return u, cross(a, u)


# ---- mesh -----------------------------------------------------------------------------------
class Mesh:
    """Triangles with a uv per corner. smooth: normals averaged at shared positions (else flat)."""

    def __init__(self, name, smooth=False):
        self.name, self.smooth = name, smooth
        self.tris = []   # ((p, p, p), (uv, uv, uv))

    # -- faces --
    def tri(self, a, b, c, ink=None, uvs=None):
        t = uvs or (ink_uv(ink),) * 3
        self.tris.append(((a, b, c), tuple(t)))

    def face(self, pts, ink=None, uvs=None, outward=None, both=False):
        """A convex polygon (fan). outward: flip it to face that direction."""
        pts = list(pts)
        uvs = list(uvs) if uvs else [ink_uv(ink)] * len(pts)
        if outward is not None:
            n = cross(sub(pts[1], pts[0]), sub(pts[2], pts[0]))
            if dot(n, outward) < 0:
                pts.reverse()
                uvs.reverse()
        for i in range(1, len(pts) - 1):
            self.tris.append(((pts[0], pts[i], pts[i + 1]), (uvs[0], uvs[i], uvs[i + 1])))
            if both:
                self.tris.append(((pts[0], pts[i + 1], pts[i]), (uvs[0], uvs[i + 1], uvs[i])))

    def merge(self, other, pos=(0, 0, 0), euler=(0, 0, 0), scale=1.0):
        s = scale if isinstance(scale, tuple) else (scale, scale, scale)
        flip = s[0] * s[1] * s[2] < 0
        for pts, uvs in other.tris:
            q = [add(rot((p[0] * s[0], p[1] * s[1], p[2] * s[2]), euler), pos) for p in pts]
            if flip:
                q, uvs = [q[0], q[2], q[1]], (uvs[0], uvs[2], uvs[1])
            self.tris.append((tuple(q), uvs))
        return self

    # -- solids --
    def box(self, c, size, ink, euler=(0, 0, 0), taper=1.0):
        """A box at c; taper scales its top (x and z)."""
        hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
        corners = {}
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    k = taper if sy > 0 else 1.0
                    corners[(sx, sy, sz)] = add(rot((sx * hx * k, sy * hy, sz * hz * k), euler), c)
        for axis in range(3):
            for sign in (-1, 1):
                others = [a for a in range(3) if a != axis]
                quad = []
                for u, v in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                    key = [0, 0, 0]
                    key[axis], key[others[0]], key[others[1]] = sign, u, v
                    quad.append(corners[tuple(key)])
                mid = mul((quad[0][0] + quad[2][0], quad[0][1] + quad[2][1], quad[0][2] + quad[2][2]), 0.5)
                self.face(quad, ink, outward=sub(mid, c))
        return self

    def loft(self, rings, ink=None, cap_start=False, cap_end=False, closed=True, v_scale=1.0, u_scale=1.0, inward=False):
        """Rings of the same point count, joined ring to ring. With no ink, uv = (around, along)."""
        n = len(rings[0])
        length = 0.0
        vs = [0.0]
        for a, b in zip(rings, rings[1:]):
            length += math.dist(a[0], b[0])
            vs.append(length)
        last = n if closed else n - 1
        for r in range(len(rings) - 1):
            for i in range(last):
                j = (i + 1) % n
                quad = [rings[r][i], rings[r][j], rings[r + 1][j], rings[r + 1][i]]
                uvs = None
                if ink is None:
                    u0, u1 = i / n * u_scale, (i + 1) / n * u_scale
                    uvs = [(u0, vs[r] * v_scale), (u1, vs[r] * v_scale), (u1, vs[r + 1] * v_scale), (u0, vs[r + 1] * v_scale)]
                if inward:
                    quad.reverse()
                    if uvs:
                        uvs.reverse()
                self._quad(quad, ink, uvs)
        for cap, ring, sign in ((cap_start, rings[0], -1), (cap_end, rings[-1], 1)):
            if cap:
                centre = mul(tuple(map(sum, zip(*ring))), 1.0 / n)
                other = rings[1] if sign < 0 else rings[-2]
                out = sub(centre, mul(tuple(map(sum, zip(*other))), 1.0 / n))
                for i in range(n):
                    self.face([centre, ring[i], ring[(i + 1) % n]], ink, uvs=None if ink else [(0.5, 0.5)] * 3, outward=out)
        return self

    def _quad(self, q, ink, uvs):
        uvs = uvs or [ink_uv(ink)] * 4
        if math.dist(q[0], q[1]) > 1e-7 and math.dist(q[1], q[2]) > 1e-7:
            self.tris.append(((q[0], q[1], q[2]), (uvs[0], uvs[1], uvs[2])))
        if math.dist(q[2], q[3]) > 1e-7 and math.dist(q[3], q[0]) > 1e-7:
            self.tris.append(((q[0], q[2], q[3]), (uvs[0], uvs[2], uvs[3])))

    def tube(self, path, radii, ink=None, sides=8, caps=True, squash=1.0, twist=0.0, **kw):
        """A tube along a path of points; radii one per point (or one for all)."""
        if not isinstance(radii, (list, tuple)):
            radii = [radii] * len(path)
        rings = []
        u = v = None
        for k, p in enumerate(path):
            a = sub(path[min(k + 1, len(path) - 1)], path[max(k - 1, 0)])
            if u is None:
                u, v = basis(a)
            else:
                a = unit(a)
                u = unit(sub(u, mul(a, dot(u, a))))
                v = cross(a, u)
            ring = []
            for i in range(sides):
                t = 2 * math.pi * i / sides + twist * k
                ring.append(add(p, add(mul(u, radii[k] * math.cos(t)), mul(v, radii[k] * squash * math.sin(t)))))
            rings.append(ring)
        return self.loft(rings, ink, cap_start=caps and radii[0] > 0, cap_end=caps and radii[-1] > 0, **kw)

    def lathe(self, c, profile, ink=None, sides=12, axis='y', **kw):
        """Rings about an axis through c: profile is [(radius, along)]."""
        rings = []
        for r, h in profile:
            ring = []
            for i in range(sides):
                t = 2 * math.pi * i / sides
                a, b = r * math.cos(t), r * math.sin(t)
                p = (a, h, -b) if axis == 'y' else ((h, a, b) if axis == 'x' else (a, b, h))
                ring.append(add(c, p))
            rings.append(ring)
        return self.loft(rings, ink, cap_start=profile[0][0] > 0, cap_end=profile[-1][0] > 0, **kw)

    def blob(self, c, radius, ink=None, detail=2, lump=0.0, freq=1.0, seed=0, scale=(1, 1, 1), uv_scale=0.25, floor=None):
        """A lumpy sphere (an icosphere pushed about by noise). floor: flatten below this y."""
        t = (1 + math.sqrt(5)) / 2
        verts = [unit(v) for v in ((-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
                                   (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1))]
        faces = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
                 (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
        for _ in range(detail):
            cache, out = {}, []

            def midpoint(a, b):
                key = (min(a, b), max(a, b))
                if key not in cache:
                    verts.append(unit(lerp(verts[a], verts[b], 0.5)))
                    cache[key] = len(verts) - 1
                return cache[key]
            for a, b, d in faces:
                ab, bd, da = midpoint(a, b), midpoint(b, d), midpoint(d, a)
                out += [(a, ab, da), (b, bd, ab), (d, da, bd), (ab, bd, da)]
            faces = out
        pts = []
        for v in verts:
            r = radius * (1 + lump * (fbm3(v[0] * freq + 7.1, v[1] * freq + 3.3, v[2] * freq + 1.7, seed) * 2 - 1))
            p = (c[0] + v[0] * r * scale[0], c[1] + v[1] * r * scale[1], c[2] + v[2] * r * scale[2])
            if floor is not None and p[1] < floor:
                p = (p[0], floor, p[2])
            pts.append(p)
        for a, b, d in faces:
            uvs = None
            if ink is None:
                uvs = [((p[0] + p[2] * 0.5) * uv_scale, (p[1] + p[2] * 0.5) * uv_scale) for p in (pts[a], pts[b], pts[d])]
            self.tri(pts[a], pts[b], pts[d], ink, uvs)
        return self

    def grid(self, x0, x1, z0, z1, nx, nz, height, ink=None, uv_scale=0.1, down=False, keep=None):
        """A height field: height(x, z) -> y. keep(x, z) -> False drops the cell (holes, round edges)."""
        def P(i, j):
            x, z = x0 + (x1 - x0) * i / nx, z0 + (z1 - z0) * j / nz
            return (x, height(x, z), z)
        for j in range(nz):
            for i in range(nx):
                q = [P(i, j), P(i, j + 1), P(i + 1, j + 1), P(i + 1, j)]
                if keep and not keep((q[0][0] + q[2][0]) / 2, (q[0][2] + q[2][2]) / 2):
                    continue
                uvs = None if ink else [(p[0] * uv_scale, p[2] * uv_scale) for p in q]
                if down:
                    q.reverse()
                    if uvs:
                        uvs.reverse()
                self._quad(q, ink, uvs)
        return self

    def card(self, a, b, c, d, ink=None, both=True):
        """A quad a-b-c-d with uv (0,0) (1,0) (1,1) (0,1) when it has no ink."""
        self.face([a, b, c, d], ink, uvs=None if ink else [(0, 0), (1, 0), (1, 1), (0, 1)], both=both)
        return self

    # -- output --
    def write(self, folder, mtl):
        """Write <folder>/<name>.obj using material library <mtl>.mtl. Returns the file name."""
        tris = []
        for pts, uvs in self.tris:
            n = cross(sub(pts[1], pts[0]), sub(pts[2], pts[0]))
            if dot(n, n) < 1e-18:
                continue
            tris.append((pts, uvs, unit(n)))
        normals_at = {}
        if self.smooth:
            for pts, _, n in tris:
                for p in pts:
                    key = (round(p[0], 4), round(p[1], 4), round(p[2], 4))
                    acc = normals_at.get(key, (0.0, 0.0, 0.0))
                    normals_at[key] = add(acc, n)
        vi, ti, ni, lines = {}, {}, {}, []
        for pts, uvs, n in tris:
            corner = []
            # Mirrored in z, so the winding is reversed to stay counter-clockwise from outside.
            for p, t in zip(reversed(pts), reversed(uvs)):
                if self.smooth:
                    n_use = unit(normals_at[(round(p[0], 4), round(p[1], 4), round(p[2], 4))])
                else:
                    n_use = n
                v = vi.setdefault((round(p[0], 4), round(p[1], 4), round(-p[2], 4)), len(vi) + 1)
                tt = ti.setdefault((round(t[0], 5), round(t[1], 5)), len(ti) + 1)
                nn = ni.setdefault((round(n_use[0], 3), round(n_use[1], 3), round(-n_use[2], 3)), len(ni) + 1)
                corner.append(f'{v}/{tt}/{nn}')
            lines.append('f ' + ' '.join(corner))
        out = [f'# {self.name}: built by Tools/Venues/story_afterlife_mesh.py', f'mtllib {mtl}.mtl', 'o ' + self.name, 's off']
        out += ['v %g %g %g' % p for p in vi]
        out += ['vt %g %g' % t for t in ti]
        out += ['vn %g %g %g' % n for n in ni]
        out += [f'usemtl {mtl}'] + lines
        save_bytes(os.path.join(folder, self.name + '.obj'), ('\n'.join(out) + '\n').encode())
        return self.name + '.obj'


def write_mtl(folder, name, texture_path):
    """<name>.mtl in folder with one material <name> on texture_path (relative to the folder)."""
    save_bytes(os.path.join(folder, name + '.mtl'), f'newmtl {name}\nKd 1 1 1\nKs 0 0 0\nNs 0\nillum 1\nmap_Kd {texture_path}\n'.encode())


def part(obj_file):
    """The part path of a mesh written by Mesh.write (its object is named after the file)."""
    return f'{obj_file}#0/{obj_file[:-4]}#0/@#0'
