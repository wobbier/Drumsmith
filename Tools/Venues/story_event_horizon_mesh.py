"""Mesh shop for the Hall of Fame at the Event Horizon (StoryEventHorizon).

A tiny OBJ writer: geometry is built in venue metres (+x crowd right, +y up, +z toward the band),
coloured by picking texels out of a small drawn palette (EH_Palette.png), and written the way the
Backyard's meshes are (z mirrored, faces wound counter-clockwise seen from outside in the file).
Every file has exactly one object and one material, so a Model's part path is predictable:
    "<File>.obj#0/<Object>#0/@#0"
which is what the generator uses to override a part's material (the glowing rings, the stars).
"""
import math
import os
import struct
import zlib

# Palette: a 16 x 16 grid of 16 px swatches in a 256 px texture.
PALETTE = {
    'brass': (0.78, 0.56, 0.24), 'brass_dark': (0.42, 0.28, 0.11), 'brass_pale': (0.95, 0.80, 0.47),
    'bronze': (0.55, 0.33, 0.17), 'steel': (0.36, 0.39, 0.45), 'steel_dark': (0.16, 0.18, 0.23),
    'navy': (0.07, 0.09, 0.17), 'hull': (0.24, 0.26, 0.33), 'hull_light': (0.55, 0.58, 0.64),
    'marble': (0.80, 0.78, 0.74), 'marble_dark': (0.30, 0.29, 0.31), 'black': (0.02, 0.02, 0.025),
    'wine': (0.36, 0.06, 0.10), 'velvet': (0.22, 0.04, 0.08), 'walnut': (0.30, 0.17, 0.09),
    'ivory': (0.93, 0.89, 0.80), 'cream': (1.0, 0.93, 0.74), 'cyan': (0.30, 0.86, 1.0),
    'amber': (1.0, 0.62, 0.22), 'white': (1.0, 1.0, 1.0), 'rubber': (0.06, 0.06, 0.07),
    'paper': (0.92, 0.90, 0.84), 'glass': (0.10, 0.16, 0.24), 'teal': (0.10, 0.32, 0.36),
    'carpet': (0.18, 0.05, 0.08), 'gold': (1.0, 0.78, 0.30), 'shade': (1.0, 0.80, 0.50),
}
NAMES = list(PALETTE)
GRID, CELL = 16, 16
SIZE = GRID * CELL


def uv(ink):
    i = NAMES.index(ink)
    x, y = (i % GRID) * CELL + CELL / 2, (i // GRID) * CELL + CELL / 2
    return (x / SIZE, 1 - y / SIZE)


def write_png(path, w, h, rgb_rows):
    """rgb_rows: list of bytes rows (w*3 each). Deterministic, no metadata."""
    raw = b''.join(b'\x00' + row for row in rgb_rows)
    def chunk(tag, data):
        c = struct.pack('>I', len(data)) + tag + data
        return c + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b'')
    save_bytes(path, png)


def palette_png(path):
    rows = []
    for py in range(SIZE):
        row = bytearray()
        for px in range(SIZE):
            i = (py // CELL) * GRID + px // CELL
            c = PALETTE[NAMES[i]] if i < len(NAMES) else (1, 0, 1)
            # The palette is authored in linear-ish colour; store as sRGB.
            row += bytes(int(round(255 * max(0, min(1, v)) ** (1 / 2.2))) for v in c)
        rows.append(bytes(row))
    write_png(path, SIZE, SIZE, rows)


def save_bytes(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path) and open(path, 'rb').read() == data:
        return
    with open(path, 'wb') as f:
        f.write(data)
    # A stale cooked twin would be loaded instead of the new source.
    for twin in (path + '.assbin', path + '.dds'):
        if os.path.exists(twin):
            os.remove(twin)


# ---- vector helpers ------------------------------------------------------------------------
def add(a, b): return tuple(x + y for x, y in zip(a, b))
def sub(a, b): return tuple(x - y for x, y in zip(a, b))
def mul(a, s): return tuple(x * s for x in a)
def dot(a, b): return sum(x * y for x, y in zip(a, b))
def cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def unit(a):
    l = math.sqrt(dot(a, a)) or 1.0
    return mul(a, 1 / l)


def basis(axis):
    """Two unit vectors perpendicular to axis."""
    a = unit(axis)
    ref = (0, 1, 0) if abs(a[1]) < 0.9 else (1, 0, 0)
    u = unit(cross(a, ref))
    v = cross(a, u)
    return u, v


class Mesh:
    def __init__(self, name, note=''):
        self.name, self.note = name, note
        self.faces = []  # (points, ink or uv list)

    def face(self, pts, ink, outward=None, uvs=None):
        """pts in venue space. outward: a direction the face should point (else as wound, CCW)."""
        if outward is not None:
            n = cross(sub(pts[1], pts[0]), sub(pts[2], pts[0]))
            if dot(n, outward) < 0:
                pts = list(reversed(pts))
                if uvs:
                    uvs = list(reversed(uvs))
        self.faces.append((list(pts), ink, uvs))

    def quad2(self, pts, ink):
        """A double-sided quad (cards, paper, flat glows)."""
        self.faces.append((list(pts), ink, None))
        self.faces.append((list(reversed(pts)), ink, None))

    def box(self, c, size, ink, yaw=0.0):
        hx, hy, hz = (s / 2 for s in size)
        cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        def P(x, y, z):
            return (c[0] + x * cy + z * sy, c[1] + y, c[2] - x * sy + z * cy)
        corners = [P(x, y, z) for x in (-hx, hx) for y in (-hy, hy) for z in (-hz, hz)]
        for idx in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
            pts = [corners[i] for i in idx]
            mid = mul(tuple(map(sum, zip(*pts))), 0.25)
            self.face(pts, ink, sub(mid, c))

    def tube(self, a, b, r0, r1, ink, sides=8, caps=True):
        axis = sub(b, a)
        u, v = basis(axis)
        ring = lambda p, r, k: add(p, add(mul(u, r * math.cos(k * math.tau / sides)), mul(v, r * math.sin(k * math.tau / sides))))
        mid = mul(add(a, b), 0.5)
        for k in range(sides):
            pts = [ring(a, r0, k), ring(a, r0, k + 1), ring(b, r1, k + 1), ring(b, r1, k)]
            m = mul(tuple(map(sum, zip(*pts))), 0.25)
            self.face(pts, ink, sub(m, add(a, mul(axis, dot(sub(m, a), axis) / max(dot(axis, axis), 1e-9)))))
        if caps:
            for p, r, d in ((a, r0, mul(axis, -1)), (b, r1, axis)):
                if r > 0:
                    for k in range(sides):
                        self.face([p, ring(p, r, k), ring(p, r, k + 1)], ink, d)

    def sphere(self, c, r, ink, sides=10, bands=6, squash=1.0):
        def P(i, j):
            th, ph = j * math.pi / bands, i * math.tau / sides
            return (c[0] + r * math.sin(th) * math.cos(ph), c[1] + r * squash * math.cos(th), c[2] + r * math.sin(th) * math.sin(ph))
        for i in range(sides):
            for j in range(bands):
                pts = [P(i, j), P(i + 1, j), P(i + 1, j + 1), P(i, j + 1)]
                if j == 0: pts = [pts[0], pts[2], pts[3]]
                elif j == bands - 1: pts = [pts[0], pts[1], pts[2]]
                m = mul(tuple(map(sum, zip(*pts))), 1 / len(pts))
                self.face(pts, ink, sub(m, c))

    def torus(self, c, axis, R, half_w, half_d, ink, seg=72, inner_ink=None, phase=0.0):
        """A ring with a rectangular section: R the centre radius, half_w its radial half-width,
        half_d its half-depth along the axis. inner_ink colours the inside face (the bore)."""
        ax = unit(axis)
        u, v = basis(ax)
        def P(k, rr, dd):
            t = phase + k * math.tau / seg
            d = add(mul(u, math.cos(t)), mul(v, math.sin(t)))
            return add(c, add(mul(d, rr), mul(ax, dd))), d
        for k in range(seg):
            o0, d0 = P(k, R + half_w, -half_d); o1, d1 = P(k + 1, R + half_w, -half_d)
            o2, _ = P(k + 1, R + half_w, half_d); o3, _ = P(k, R + half_w, half_d)
            i0, _ = P(k, R - half_w, -half_d); i1, _ = P(k + 1, R - half_w, -half_d)
            i2, _ = P(k + 1, R - half_w, half_d); i3, _ = P(k, R - half_w, half_d)
            dm = unit(add(d0, d1))
            self.face([o0, o1, o2, o3], ink, dm)                       # outer rim
            self.face([i0, i1, i2, i3], inner_ink or ink, mul(dm, -1))  # bore
            self.face([o0, o1, i1, i0], ink, mul(ax, -1))             # back face
            self.face([o3, o2, i2, i3], ink, ax)                      # front face

    def annulus(self, c, axis, r0, r1, ink, seg=72, both=True):
        ax = unit(axis)
        u, v = basis(ax)
        for k in range(seg):
            t0, t1 = k * math.tau / seg, (k + 1) * math.tau / seg
            d0 = add(mul(u, math.cos(t0)), mul(v, math.sin(t0)))
            d1 = add(mul(u, math.cos(t1)), mul(v, math.sin(t1)))
            pts = [add(c, mul(d0, r0)), add(c, mul(d1, r0)), add(c, mul(d1, r1)), add(c, mul(d0, r1))]
            if r0 <= 0:
                pts = pts[1:]
            self.face(pts, ink, ax)
            if both:
                self.face(list(reversed(pts)), ink, mul(ax, -1))

    def write(self, folder, mtl, texture=None):
        """Write <folder>/<name>.obj (and <mtl>.mtl if texture given). Returns the file name."""
        coords, normals, uvs, lines_f = {}, {}, {}, []
        for pts, ink, fuv in self.faces:
            xyz = [(round(x, 5), round(y, 5), round(-z, 5)) for x, y, z in reversed(pts)]
            fu = list(reversed(fuv)) if fuv else [uv(ink)] * len(pts)
            n = cross(sub(xyz[1], xyz[0]), sub(xyz[2], xyz[0]))
            if dot(n, n) < 1e-16:
                continue
            n = tuple(round(x, 5) for x in unit(n))
            ni = normals.setdefault(n, len(normals) + 1)
            corner = []
            for p, t in zip(xyz, fu):
                vi = coords.setdefault(p, len(coords) + 1)
                ti = uvs.setdefault((round(t[0], 6), round(t[1], 6)), len(uvs) + 1)
                corner.append(f'{vi}/{ti}/{ni}')
            lines_f.append('f ' + ' '.join(corner))
        out = [f'# {self.note}', f'mtllib {mtl}.mtl', 'o ' + self.name, 's off']
        out += ['v %g %g %g' % p for p in coords]
        out += ['vt %.6f %.6f' % t for t in uvs]
        out += ['vn %g %g %g' % n for n in normals]
        out += [f'usemtl {mtl}'] + lines_f
        save_bytes(os.path.join(folder, self.name + '.obj'), ('\n'.join(out) + '\n').encode())
        return self.name + '.obj'


def write_mtl(folder, name, texture):
    text = f'newmtl {name}\nKd 1 1 1\nKs 0 0 0\nNs 0\nillum 1\nmap_Kd {texture}\n'
    save_bytes(os.path.join(folder, name + '.mtl'), text.encode())


def part(obj_file, obj_name):
    return f'{obj_file}#0/{obj_name}#0/@#0'
