"""The roller rink's mesh shop: a tiny OBJ writer and the rink's own geometry (the maple oval, the
carpeted rail, the DJ booth, the mirror ball, neon tubes, skates and the sign quads).

All geometry is authored in venue metres (+x crowd's right, +y up, +z toward the booth). The OBJ
files are written the way the Backyard's are: z negated and each face reversed, because the
importer converts to left-handed (flips z and the winding back). A face is given with a hint
direction and turned so its normal points that way, so nothing is inside out.

Flat colours come from Palette.png (a 16 x 16 grid of 16 px swatches, drawn by
story_roller_rink_textures.py); a material may instead map its own texture with planar or explicit UVs.
"""
import math
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
VENUE = os.path.join(ROOT, "Assets", "Venues", "StoryRollerRink")
MODELS = os.path.join(VENUE, "Models")
LOCAL = "Assets/Venues/StoryRollerRink/Models/"

# Palette swatches: name -> (column, row) in Palette.png, and the colour drawn there (sRGB hex).
SWATCHES = [
    ("white", "#f4f1ea"), ("black", "#121014"), ("chrome", "#c9ccd6"), ("steel", "#6d7280"),
    ("maple", "#d8a55e"), ("maple_dark", "#a8743a"), ("walnut", "#5a3a22"), ("carpet", "#2a1846"),
    ("pink", "#ff2f9a"), ("hotpink", "#ff5ec4"), ("cyan", "#28e6ff"), ("teal", "#14a7b0"),
    ("orange", "#ff7a1a"), ("tangerine", "#ff9b3d"), ("yellow", "#ffd23a"), ("lime", "#8dff3a"),
    ("purple", "#8a3cff"), ("violet", "#5a1fb0"), ("navy", "#1b1f4a"), ("midnight", "#0d0f24"),
    ("red", "#e8263a"), ("cream", "#f6e2b4"), ("mustard", "#d9a520"), ("brown", "#7a4a26"),
    ("rubber", "#1d1c20"), ("silver", "#dfe3ee"), ("mirror", "#eef4ff"), ("glass", "#9fd6ff"),
    ("vinyl_red", "#b3122a"), ("vinyl_teal", "#0f8c8c"), ("formica", "#f0d9a8"), ("tile", "#e9e4f2"),
    ("wall", "#3a2252"), ("wall_hi", "#53307a"), ("ceiling", "#151226"), ("beam", "#2b2440"),
    ("grey", "#8a8796"), ("dark", "#2a2730"), ("gold", "#e9b949"), ("skin", "#d9a27c"),
]
PALETTE = {name: (i % 16, i // 16) for i, (name, _) in enumerate(SWATCHES)}
CELL = 16


def swatch_uv(name):
    """'pink' is the pink swatch; 'pink@3' is the same swatch glowing (mtl Ke 3)."""
    c, r = PALETTE[name.split("@")[0]]
    return ((c * CELL + CELL / 2) / 256.0, 1.0 - (r * CELL + CELL / 2) / 256.0)


def sub(a, b): return tuple(x - y for x, y in zip(a, b))
def add(a, b): return tuple(x + y for x, y in zip(a, b))
def mul(a, s): return tuple(x * s for x in a)
def dot(a, b): return sum(x * y for x, y in zip(a, b))
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def unit(a):
    n = math.sqrt(dot(a, a)) or 1.0
    return tuple(x / n for x in a)


class Mesh:
    """Faces in venue space. Each face: points, material name, uvs (None = palette swatch)."""

    def __init__(self, name, note=""):
        self.name = name
        self.note = note
        self.faces = []
        self.materials = {}   # name -> texture file (relative to Models/) for textured materials

    def textured(self, material, texture):
        self.materials[material] = texture

    def face(self, pts, ink, hint=None, uvs=None, both=False):
        pts = list(pts)
        uvs = list(uvs) if uvs is not None else None
        if hint is not None:
            n = cross(sub(pts[1], pts[0]), sub(pts[2], pts[0]))
            if dot(n, hint) < 0:
                pts.reverse()
                if uvs:
                    uvs.reverse()
        self.faces.append((pts, ink, uvs))
        if both:
            self.faces.append((pts[::-1], ink, uvs[::-1] if uvs else None))

    def box(self, centre, size, ink, inks=None):
        """Axis-aligned box. inks: optional dict per side (+x,-x,+y,-y,+z,-z) -> swatch."""
        cx, cy, cz = centre
        hx, hy, hz = (s / 2 for s in size)
        sides = {
            "+x": ((1, 0, 0), [(cx + hx, cy - hy, cz - hz), (cx + hx, cy + hy, cz - hz), (cx + hx, cy + hy, cz + hz), (cx + hx, cy - hy, cz + hz)]),
            "-x": ((-1, 0, 0), [(cx - hx, cy - hy, cz - hz), (cx - hx, cy - hy, cz + hz), (cx - hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz - hz)]),
            "+y": ((0, 1, 0), [(cx - hx, cy + hy, cz - hz), (cx - hx, cy + hy, cz + hz), (cx + hx, cy + hy, cz + hz), (cx + hx, cy + hy, cz - hz)]),
            "-y": ((0, -1, 0), [(cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz + hz), (cx - hx, cy - hy, cz + hz)]),
            "+z": ((0, 0, 1), [(cx - hx, cy - hy, cz + hz), (cx + hx, cy - hy, cz + hz), (cx + hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz + hz)]),
            "-z": ((0, 0, -1), [(cx - hx, cy - hy, cz - hz), (cx - hx, cy + hy, cz - hz), (cx + hx, cy + hy, cz - hz), (cx + hx, cy - hy, cz - hz)]),
        }
        for key, (n, pts) in sides.items():
            ink_here = (inks or {}).get(key, ink)
            if ink_here:
                self.face(pts, ink_here, n)

    def tube(self, a, b, r0, r1, ink, sides=8, caps=True):
        axis = sub(b, a)
        d = unit(axis)
        ref = (0, 1, 0) if abs(d[1]) < 0.9 else (1, 0, 0)
        u = unit(cross(d, ref))
        v = cross(d, u)
        ring = lambda c, r, k: add(c, add(mul(u, r * math.cos(2 * math.pi * k / sides)), mul(v, r * math.sin(2 * math.pi * k / sides))))
        for k in range(sides):
            p = [ring(a, r0, k), ring(a, r0, k + 1), ring(b, r1, k + 1), ring(b, r1, k)]
            centre = mul(add(add(p[0], p[1]), add(p[2], p[3])), 0.25)
            self.face(p, ink, sub(centre, add(a, mul(d, dot(sub(centre, a), d)))))
        if caps:
            self.face([ring(a, r0, k) for k in range(sides)], ink, mul(d, -1))
            self.face([ring(b, r1, k) for k in range(sides)], ink, d)

    def sphere(self, centre, r, inks, sides=16, bands=10, ink_fn=None):
        def p(i, j):
            th = math.pi * i / bands
            ph = 2 * math.pi * j / sides
            return add(centre, (r * math.sin(th) * math.cos(ph), r * math.cos(th), r * math.sin(th) * math.sin(ph)))
        for i in range(bands):
            for j in range(sides):
                pts = [p(i, j), p(i, j + 1), p(i + 1, j + 1), p(i + 1, j)]
                if i == 0:
                    pts = pts[1:]
                elif i == bands - 1:
                    pts = pts[:3]
                c = mul(add(add(pts[0], pts[1]), pts[-1]), 1 / 3.0)
                ink = ink_fn(i, j) if ink_fn else inks[(i + j) % len(inks)]
                self.face(pts, ink, sub(c, centre))

    def write(self, folder=MODELS, mtl_name=None):
        """Writes <name>.obj (+ <name>.mtl). Returns the project path of the .obj."""
        os.makedirs(folder, exist_ok=True)
        mtl_name = mtl_name or self.name
        inks = []
        for _, ink, _ in self.faces:
            if ink not in inks:
                inks.append(ink)
        coords, normals, texc, groups = {}, {}, {}, {i: [] for i in inks}
        for pts, ink, uvs in self.faces:
            written = [(round(x, 5), round(y, 5), round(-z, 5)) for x, y, z in reversed(pts)]
            wuv = list(reversed(uvs)) if uvs else [swatch_uv(ink)] * len(pts)
            n = cross(sub(written[1], written[0]), sub(written[2], written[0]))
            if dot(n, n) < 1e-14:
                continue
            n = tuple(round(c, 5) for c in unit(n))
            ni = normals.setdefault(n, len(normals) + 1)
            corners = []
            for p, t in zip(written, wuv):
                t = (round(t[0], 6), round(t[1], 6))
                corners.append(f"{coords.setdefault(p, len(coords) + 1)}/{texc.setdefault(t, len(texc) + 1)}/{ni}")
            groups[ink].append("f " + " ".join(corners))
        lines = [f"# {self.note}" if self.note else "# Drumsmith roller rink", f"mtllib {mtl_name}.mtl", "o " + self.name, "s off"]
        lines += ["v %g %g %g" % p for p in coords]
        lines += ["vt %.6f %.6f" % t for t in texc]
        lines += ["vn %g %g %g" % n for n in normals]
        for ink in inks:
            if groups[ink]:
                lines.append("usemtl " + mat_name(ink))
                lines += groups[ink]
        save(os.path.join(folder, self.name + ".obj"), "\n".join(lines) + "\n")
        mtl = []
        for ink in inks:
            tex = self.materials.get(ink.split("@")[0], "Palette.png")
            mtl += [f"newmtl {mat_name(ink)}", "Kd 1 1 1", "Ks 0 0 0", "Ns 0", "illum 1", f"map_Kd {tex}"]
            if "@" in ink:
                k = float(ink.split("@")[1])
                mtl += [f"Ke {k:g} {k:g} {k:g}", f"map_Ke {tex}"]
            mtl.append("")
        save(os.path.join(folder, mtl_name + ".mtl"), "\n".join(mtl))
        return LOCAL + self.name + ".obj"


def mat_name(ink):
    return ink.replace("@", "_glow").replace(".", "_")


def save(path, content):
    data = content.encode()
    if os.path.exists(path) and open(path, "rb").read() == data:
        return
    with open(path, "wb") as f:
        f.write(data)
    twin = path + ".assbin"
    if os.path.exists(twin):
        os.remove(twin)


def ellipse(cx, cz, a, b, t):
    return (cx + a * math.cos(t), cz + b * math.sin(t))
