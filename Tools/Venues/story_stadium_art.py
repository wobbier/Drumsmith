"""StoryStadium's prop shop: a tiny OBJ writer (venue metres, the importer's Z flip handled), the
palette atlas, the bowl generator, and the textures (pure-Python PNGs for the tiling crowd and
seats, ImageMagick for the drawn screen inserts, mosaics, ribbon boards and the LED backdrop).

Everything is deterministic: fixed seeds, sorted output, metadata stripped from the PNGs.
"""
import math
import os
import random
import shutil
import struct
import subprocess
import sys
import zlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
VENUE = os.path.join(ROOT, "Assets", "Venues", "StoryStadium")
MODELS = os.path.join(VENUE, "Models")
LOCAL = "Assets/Venues/StoryStadium/Models/"

# ---------------------------------------------------------------------------------------------
# Palette atlas: 8 x 8 swatches of 64 px (512 px), so a distant mip still lands on its colour.
PALETTE = {
    # concrete, steel and seats
    "black": (10, 10, 12), "char": (26, 27, 31), "steel": (58, 61, 68), "steel_lt": (112, 116, 124),
    "concrete": (92, 92, 96), "concrete_dk": (52, 52, 56), "stair": (128, 128, 132), "tarp": (16, 17, 22),
    "seat_blue": (22, 46, 104), "seat_red": (120, 24, 30), "navy": (14, 20, 44), "roof": (40, 43, 50),
    "roof_dk": (22, 24, 29), "glass": (30, 46, 60), "silver": (170, 174, 182), "white": (225, 225, 220),
    # stage
    "deck": (34, 34, 38), "skirt": (8, 8, 10), "riser": (30, 30, 34), "truss": (150, 152, 158),
    "speaker": (18, 18, 20), "grille": (36, 36, 40), "rug": (110, 30, 26), "wood": (120, 80, 46),
    # glows (also used by the Glow material)
    "amber": (255, 150, 40), "gold": (255, 196, 70), "cyan": (40, 210, 255), "ice": (180, 225, 255),
    "warm": (255, 214, 160), "red": (255, 40, 40), "green": (40, 255, 120), "pink": (255, 60, 150),
    "blue": (60, 110, 255), "dim": (90, 80, 60), "window": (255, 200, 120), "exit": (60, 255, 90),
    # props
    "bucket": (232, 230, 220), "bucket_rim": (200, 198, 188), "label": (232, 120, 30), "scuff": (150, 150, 140),
    "coin": (212, 160, 52), "coin_dk": (150, 104, 30), "mustard": (214, 160, 30), "mustard_dk": (170, 120, 20),
    "mug": (176, 182, 190), "mug_dk": (96, 100, 108), "stick": (214, 180, 120), "towel": (210, 210, 205),
    "turf": (30, 60, 32), "floor": (40, 40, 44), "cable": (12, 12, 12), "rubber": (20, 20, 20),
}
_NAMES = list(PALETTE)
assert len(_NAMES) <= 64, len(_NAMES)


def swatch_uv(name):
    i = _NAMES.index(name)
    return ((i % 8) * 64 + 32) / 512.0, 1.0 - ((i // 8) * 64 + 32) / 512.0


# ---------------------------------------------------------------------------------------------
# PNG / magick
def write_png(path, w, h, rows):
    """rows: list of h bytearrays, each w*3 RGB bytes."""
    raw = b"".join(b"\x00" + bytes(r) for r in rows)
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    save_bytes(path, png)


def save_bytes(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path) and open(path, "rb").read() == data:
        return
    with open(path, "wb") as f:
        f.write(data)
    twin = path + ".dds" if path.endswith(".png") else path + ".assbin"
    for stale in (twin, twin + ".d"):  # the game prefers a cooked twin even when it is older
        if os.path.exists(stale):
            os.unlink(stale)


def save_text(path, text):
    save_bytes(path, text.encode())


def _magick_bin():
    found = shutil.which("magick")
    if found:
        return found
    store = "/nix/store"
    if os.path.isdir(store):
        for d in sorted(os.listdir(store), reverse=True):
            if "imagemagick-7" in d and not d.endswith((".drv", "-doc", "-dev")):
                cand = os.path.join(store, d, "bin", "magick")
                if os.path.exists(cand):
                    return cand
    sys.exit("ImageMagick 7 (magick) not found")


def magick(*args):
    cmd = [_magick_bin(), *[str(a) for a in args]]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"magick failed: {' '.join(cmd)}\n{r.stderr}")


def magick_png(path, *args):
    """Draw to a scratch file, then strip and keep it only if it changed (stable reruns)."""
    tmp = path + ".tmp.png"
    magick(*args, "-strip", "-define", "png:exclude-chunks=date,time,tIME", tmp)
    data = open(tmp, "rb").read()
    os.unlink(tmp)
    save_bytes(path, data)


# ---------------------------------------------------------------------------------------------
# Mesh + OBJ
class Mesh:
    """Faces in venue space. Each face: points, uvs, material, normal hint (venue space)."""

    def __init__(self, name, note=""):
        self.name = name
        self.note = note
        self.faces = []

    def face(self, pts, mat="Pal", colour=None, uvs=None, hint=None):
        if uvs is None:
            uv = swatch_uv(colour)
            uvs = [uv] * len(pts)
        self.faces.append((list(pts), list(uvs), mat, hint))

    def quad(self, a, b, c, d, colour, mat="Pal", hint=None):
        self.face([a, b, c, d], mat, colour, hint=hint)

    def box(self, centre, size, colour, mat="Pal", yaw=0.0, skip=()):
        cx, cy, cz = centre
        hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
        cs, sn = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))

        def p(x, y, z):  # yaw about +y: +z toward +x
            return (cx + x * cs + z * sn, cy + y, cz - x * sn + z * cs)

        def n(x, y, z):
            return (x * cs + z * sn, y, -x * sn + z * cs)
        sides = {
            "+y": ([(-hx, hy, -hz), (hx, hy, -hz), (hx, hy, hz), (-hx, hy, hz)], (0, 1, 0)),
            "-y": ([(-hx, -hy, -hz), (-hx, -hy, hz), (hx, -hy, hz), (hx, -hy, -hz)], (0, -1, 0)),
            "+x": ([(hx, -hy, -hz), (hx, -hy, hz), (hx, hy, hz), (hx, hy, -hz)], (1, 0, 0)),
            "-x": ([(-hx, -hy, -hz), (-hx, hy, -hz), (-hx, hy, hz), (-hx, -hy, hz)], (-1, 0, 0)),
            "+z": ([(-hx, -hy, hz), (-hx, hy, hz), (hx, hy, hz), (hx, -hy, hz)], (0, 0, 1)),
            "-z": ([(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz)], (0, 0, -1)),
        }
        for key, (pts, hint) in sides.items():
            if key in skip:
                continue
            self.face([p(*q) for q in pts], mat, colour, hint=n(*hint))

    def cylinder(self, base, r0, r1, h, colour, sides=12, caps=(True, True), mat="Pal", axis="y"):
        """A tapered cylinder standing on base (axis y), or lying along +x / +z."""
        bx, by, bz = base

        def at(r, a, t):
            u, v = r * math.cos(a), r * math.sin(a)
            if axis == "y":
                return (bx + u, by + t, bz + v)
            if axis == "x":
                return (bx + t, by + u, bz + v)
            return (bx + u, by + v, bz + t)

        def out(a):
            u, v = math.cos(a), math.sin(a)
            return {"y": (u, 0, v), "x": (0, u, v), "z": (u, v, 0)}[axis]
        up = {"y": (0, 1, 0), "x": (1, 0, 0), "z": (0, 0, 1)}[axis]
        for i in range(sides):
            a0, a1 = 2 * math.pi * i / sides, 2 * math.pi * (i + 1) / sides
            self.face([at(r0, a0, 0), at(r0, a1, 0), at(r1, a1, h), at(r1, a0, h)], mat, colour,
                      hint=out((a0 + a1) / 2))
        if caps[0]:
            self.face([at(r0, 2 * math.pi * i / sides, 0) for i in range(sides)], mat, colour,
                      hint=tuple(-v for v in up))
        if caps[1]:
            self.face([at(r1, 2 * math.pi * i / sides, h) for i in range(sides)], mat, colour, hint=up)

    def tube(self, a, b, r, colour, sides=6, mat="Pal"):
        """A thin strut from a to b."""
        ax, ay, az = a
        d = [b[i] - a[i] for i in range(3)]
        length = math.sqrt(sum(v * v for v in d))
        if length < 1e-6:
            return
        w = [v / length for v in d]
        ref = (0, 1, 0) if abs(w[1]) < 0.9 else (1, 0, 0)
        u = _unit(_cross(w, ref))
        v = _cross(w, u)
        for i in range(sides):
            a0, a1 = 2 * math.pi * i / sides, 2 * math.pi * (i + 1) / sides

            def ring(t, ang):
                c, s = math.cos(ang) * r, math.sin(ang) * r
                return tuple(a[k] + d[k] * t + u[k] * c + v[k] * s for k in range(3))
            mid = (a0 + a1) / 2
            hint = tuple(u[k] * math.cos(mid) + v[k] * math.sin(mid) for k in range(3))
            self.face([ring(0, a0), ring(0, a1), ring(1, a1), ring(1, a0)], mat, colour, hint=hint)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _sub(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def _dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def _unit(a):
    l = math.sqrt(_dot(a, a))
    return tuple(v / l for v in a) if l > 1e-12 else (0.0, 1.0, 0.0)


def write_obj(mesh, materials, folder=MODELS):
    """materials: {name: dict(kd=texture file or None, ke=texture file or None, ke_value=float,
    kd_colour=(r,g,b))}. Writes <name>.obj and <name>.mtl beside it."""
    coords, uvs, normals, out = {}, {}, {}, {}
    for pts, tex, mat, hint in mesh.faces:
        xyz = [(round(x, 4), round(y, 4), round(-z, 4)) for x, y, z in pts]
        if len(xyz) < 3:
            continue
        cr = _cross(_sub(xyz[1], xyz[0]), _sub(xyz[2], xyz[0]))
        if len(xyz) > 3:  # a sturdier normal for quads/polygons
            cr = (0.0, 0.0, 0.0)
            for i in range(len(xyz)):
                a, b = xyz[i], xyz[(i + 1) % len(xyz)]
                cr = (cr[0] + (a[1] - b[1]) * (a[2] + b[2]), cr[1] + (a[2] - b[2]) * (a[0] + b[0]),
                      cr[2] + (a[0] - b[0]) * (a[1] + b[1]))
        if _dot(cr, cr) < 1e-14:
            continue
        order = list(range(len(xyz)))
        if hint is not None:
            hw = (hint[0], hint[1], -hint[2])
            if _dot(cr, hw) < 0:
                order.reverse()
                cr = tuple(-v for v in cr)
        nrm = tuple(round(v, 5) for v in _unit(cr))
        ni = normals.setdefault(nrm, len(normals) + 1)
        idx = []
        for k in order:
            vi = coords.setdefault(xyz[k], len(coords) + 1)
            t = (round(tex[k][0], 5), round(tex[k][1], 5))
            ti = uvs.setdefault(t, len(uvs) + 1)
            idx.append(f"{vi}/{ti}/{ni}")
        out.setdefault(mat, []).append("f " + " ".join(idx))
    lines = [f"# {mesh.note}" if mesh.note else f"# {mesh.name}", f"mtllib {mesh.name}.mtl", f"o {mesh.name}"]
    lines += ["v %g %g %g" % p for p in coords]
    lines += ["vt %.5f %.5f" % t for t in uvs]
    lines += ["vn %g %g %g" % n for n in normals]
    for mat in sorted(out):
        lines += [f"usemtl {mat}", "s off"] + out[mat]
    save_text(os.path.join(folder, mesh.name + ".obj"), "\n".join(lines) + "\n")
    mtl = []
    for mat in sorted(out):
        m = materials[mat]
        mtl += [f"newmtl {mat}", "Kd %g %g %g" % m.get("kd_colour", (1, 1, 1)), "Ks 0 0 0", "Ns 0", "illum 1"]
        if m.get("kd"):
            mtl.append("map_Kd " + m["kd"])
        if m.get("ke"):
            v = m.get("ke_value", 1.0)
            mtl += ["Ke %g %g %g" % (v, v, v), "map_Ke " + m["ke"]]
        mtl.append("")
    save_text(os.path.join(folder, mesh.name + ".mtl"), "\n".join(mtl))
    return mesh


PAL = {"kd": "Palette.png"}
GLOW = {"kd": "Palette.png", "ke": "Palette.png", "ke_value": 2.2}


def textured(png, glow=None):
    m = {"kd": png}
    if glow is not None:
        m["ke"] = png if glow is True else glow[0]
        m["ke_value"] = 1.0 if glow is True else glow[1]
    return m


# ---------------------------------------------------------------------------------------------
# The bowl: a rounded-rectangle (superellipse) around the field, offset outward per row.
FIELD_A, FIELD_B, FIELD_ZC, FIELD_N = 40.0, 58.0, -26.0, 4.0
SEGMENTS = 160


def bowl_point(t, d):
    """Point and outward normal (x, z) on the field edge offset outward by d metres."""
    c, s = math.cos(t), math.sin(t)
    e = 2.0 / FIELD_N
    x = FIELD_A * math.copysign(abs(c) ** e, c)
    z = FIELD_B * math.copysign(abs(s) ** e, s)
    gx = (FIELD_N / FIELD_A) * math.copysign(abs(x / FIELD_A) ** (FIELD_N - 1), x)
    gz = (FIELD_N / FIELD_B) * math.copysign(abs(z / FIELD_B) ** (FIELD_N - 1), z)
    l = math.hypot(gx, gz) or 1.0
    nx, nz = gx / l, gz / l
    return x + nx * d, FIELD_ZC + z + nz * d, nx, nz


def bowl_samples():
    ts = [2 * math.pi * i / SEGMENTS for i in range(SEGMENTS + 1)]
    pts = [bowl_point(t, 0) for t in ts]
    arc = [0.0]
    for a, b in zip(pts, pts[1:]):
        arc.append(arc[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    return ts, arc


# ---------------------------------------------------------------------------------------------
# Tiling textures (pure Python)
def _clamp(v):
    return max(0, min(255, int(v)))


def _blob(img, w, h, cx, cy, rx, ry, col, wrap=True):
    for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            dx, dy = (x - cx) / rx, (y - cy) / ry
            if dx * dx + dy * dy <= 1.0:
                xx, yy = (x % w, y % h) if wrap else (x, y)
                if 0 <= xx < w and 0 <= yy < h:
                    i = xx * 3
                    img[yy][i:i + 3] = bytes(col)


SHIRTS = [(150, 30, 34), (30, 60, 140), (230, 230, 225), (25, 25, 28), (200, 150, 30), (40, 110, 60),
          (90, 90, 96), (180, 60, 120), (60, 150, 190), (130, 70, 40), (220, 110, 40), (70, 40, 110)]
SKIN = [(236, 196, 160), (210, 160, 120), (170, 120, 84), (120, 80, 56), (86, 56, 40), (246, 210, 180)]
HAIR = [(30, 22, 16), (60, 40, 24), (110, 80, 40), (200, 170, 110), (20, 20, 22), (140, 60, 30)]


def seats_texture(name, seed, rows=4, phones=False, dark=1.0):
    """A tile of 8 m x <rows> rows of seated, standing people (256 x 256). With phones, a second
    texture <name>_Glow.png carries just the lit screens (an emissive map)."""
    W = H = 256
    rnd = random.Random(seed)
    band = H // rows
    img = [bytearray(W * 3) for _ in range(H)]
    glow = [bytearray(W * 3) for _ in range(H)] if phones else None
    for y in range(H):
        r = (y % band) / band
        base = (int(14 + 10 * r), int(18 + 12 * r), int(36 + 26 * r))  # seat backs: navy, lit at the lip
        img[y][:] = bytes(base) * W
    for row in range(rows):
        y0 = row * band
        x = rnd.uniform(0, 6)
        while x < W + 4:
            if rnd.random() < 0.93:
                shirt = rnd.choice(SHIRTS)
                k = (0.55 + 0.35 * rnd.random()) * dark
                shirt = tuple(_clamp(c * k) for c in shirt)
                skin = tuple(_clamp(c * (0.7 + 0.25 * rnd.random()) * dark) for c in rnd.choice(SKIN))
                cx = x + rnd.uniform(-1.5, 1.5)
                top = y0 + band * rnd.uniform(0.18, 0.34)
                _blob(img, W, H, cx, top + band * 0.42, 6.0, band * 0.30, shirt)
                _blob(img, W, H, cx, top + band * 0.10, 3.6, 4.2, skin)
                if rnd.random() < 0.6:
                    _blob(img, W, H, cx, top + band * 0.02, 3.6, 2.2, tuple(_clamp(c * dark) for c in rnd.choice(HAIR)))
                if rnd.random() < 0.18:  # hands up
                    _blob(img, W, H, cx + rnd.choice((-5, 5)), top - band * 0.08, 1.6, 4.5, skin)
                if phones:  # the glow map carries the people faintly, so the deck reads, and the phones hard
                    _blob(glow, W, H, cx, top + band * 0.42, 6.0, band * 0.30, tuple(c // 9 for c in shirt))
                if phones and rnd.random() < 0.72:
                    px, py = cx + rnd.uniform(-4, 4), top - band * rnd.uniform(0.0, 0.16)
                    col = rnd.choice([(255, 255, 250), (230, 240, 255), (255, 236, 200), (200, 225, 255)])
                    _blob(glow, W, H, px, py, 6.0, 7.0, tuple(c // 5 for c in col))
                    _blob(glow, W, H, px, py, 2.6, 3.4, col)
            x += rnd.uniform(7.0, 9.5)
    write_png(os.path.join(MODELS, name + ".png"), W, H, glow if phones else img)


def floor_texture(name, seed):
    """The field from above at a low angle: a packed floor of shoulders and heads (4 m tile)."""
    W = H = 256
    rnd = random.Random(seed)
    img = [bytearray(bytes((24, 24, 28)) * W) for _ in range(H)]
    for _ in range(1500):
        cx, cy = rnd.uniform(0, W), rnd.uniform(0, H)
        shirt = tuple(_clamp(c * (0.35 + 0.3 * rnd.random())) for c in rnd.choice(SHIRTS))
        _blob(img, W, H, cx, cy, 5.5, 4.0, shirt)
        _blob(img, W, H, cx + 0.5, cy - 2.0, 2.6, 2.4, tuple(_clamp(c * 0.55) for c in rnd.choice(HAIR + SKIN[:2])))
    write_png(os.path.join(MODELS, name + ".png"), W, H, img)


def palette_texture():
    W = H = 512
    img = [bytearray(W * 3) for _ in range(H)]
    for i, name in enumerate(_NAMES):
        col = bytes(PALETTE[name])
        x0, y0 = (i % 8) * 64, (i // 8) * 64
        for y in range(y0, y0 + 64):
            img[y][x0 * 3:(x0 + 64) * 3] = col * 64
    write_png(os.path.join(MODELS, "Palette.png"), W, H, img)


# ---------------------------------------------------------------------------------------------
# Drawn textures (ImageMagick)
HEAVY = "Noto-Sans-Black"
BOLD = "DejaVu-Sans-Bold"


def _poly(cx, cy, r, n, rot=0.0):
    pts = []
    for i in range(n):
        a = rot + 2 * math.pi * i / n
        pts.append(f"{cx + r * math.sin(a):.1f},{cy - r * math.cos(a):.1f}")
    return " ".join(pts)


def _bug(label, sub):
    """The broadcast furniture on every insert: a LIVE tag and a lower third."""
    return ["-fill", "rgb(220,30,30)", "-draw", "roundrectangle 40,36 190,92 8,8",
            "-fill", "white", "-font", HEAVY, "-pointsize", 40, "-draw", "text 58,80 'LIVE'",
            "-fill", "rgba(0,0,0,0.72)", "-draw", "rectangle 0,590 1280,690",
            "-fill", "rgb(255,196,70)", "-draw", "rectangle 0,590 18,690",
            "-fill", "white", "-font", HEAVY, "-pointsize", 46, "-draw", f"text 46,640 '{label}'",
            "-fill", "rgb(200,200,200)", "-font", BOLD, "-pointsize", 28, "-draw", f"text 48,676 '{sub}'",
            "-fill", "none", "-stroke", "rgb(255,196,70)", "-strokewidth", 10, "-draw", "rectangle 5,5 1274,714",
            "-stroke", "none"]


def _crowd_bokeh(seed, tint):
    rnd = random.Random(seed)
    args = []
    for _ in range(90):
        x, y, r = rnd.uniform(0, 1280), rnd.uniform(0, 720), rnd.uniform(10, 46)
        a = rnd.uniform(0.08, 0.3)
        args += ["-fill", f"rgba({tint[0]},{tint[1]},{tint[2]},{a:.2f})", "-draw", f"circle {x:.0f},{y:.0f} {x + r:.0f},{y:.0f}"]
    return args


def insert_mug(path):
    """The side screen finds her: mustard scarf, the dented steel travel mug."""
    a = ["-size", "1280x720", "gradient:rgb(30,22,40)-rgb(8,8,14)"] + _crowd_bokeh(11, (255, 190, 120))
    # coat and shoulders
    a += ["-fill", "rgb(46,52,66)", "-draw", "ellipse 640,820 420,330 180,360"]
    # scarf: a thick knitted band round the neck, a tail down the front, stripes
    a += ["-fill", "rgb(214,160,30)", "-draw", "roundrectangle 400,430 880,540 60,50",
          "-draw", "polygon 560,500 690,500 720,720 590,720"]
    for i in range(8):
        y = 450 + i * 12
        a += ["-fill", "rgb(170,120,20)", "-draw", f"line 420,{y} 860,{y}"]
    for i in range(6):
        y = 560 + i * 26
        a += ["-fill", "rgb(170,120,20)", "-draw", f"rectangle {596 + i * 3},{y} {706 + i * 3},{y + 8}"]
    # face (lower half in frame) and hand
    a += ["-fill", "rgb(222,182,150)", "-draw", "ellipse 640,330 150,170 0,360",
          "-fill", "rgb(70,46,30)", "-draw", "ellipse 640,190 170,90 180,360",
          "-fill", "rgb(40,28,22)", "-draw", "ellipse 590,320 14,9 0,360", "-draw", "ellipse 690,320 14,9 0,360",
          "-fill", "rgb(180,90,80)", "-draw", "ellipse 640,420 46,14 0,180"]
    # the mug, held up beside the face
    a += ["-fill", "rgb(150,156,166)", "-draw", "roundrectangle 880,200 1040,560 22,22",
          "-fill", "rgb(196,202,210)", "-draw", "rectangle 900,210 940,550",
          "-fill", "rgb(40,40,44)", "-draw", "roundrectangle 870,170 1050,225 16,16",
          "-fill", "rgb(96,100,108)", "-draw", "ellipse 1000,380 26,44 0,360",
          "-fill", "rgb(222,182,150)", "-draw", "roundrectangle 850,400 1070,470 30,30"]
    a += _bug("THE BARRICADE  /  FLOOR", "Mustard scarf, steel mug: she was there on the platform")
    magick_png(path, *a)


def insert_loonie(path):
    a = ["-size", "1280x720", "radial-gradient:rgb(60,40,10)-rgb(6,6,8)"]
    a += ["-fill", "rgb(120,120,126)", "-draw", "line 640,0 640,140", "-draw", "line 641,0 641,140"]
    a += ["-fill", "rgb(150,104,30)", "-draw", "polygon " + _poly(640, 360, 238, 11)]
    a += ["-fill", "rgb(222,170,60)", "-draw", "polygon " + _poly(640, 362, 226, 11)]
    a += ["-fill", "none", "-stroke", "rgb(160,112,34)", "-strokewidth", 6, "-draw", "polygon " + _poly(640, 362, 196, 11),
          "-stroke", "none"]
    # a bird on water, the coin's face (generic)
    a += ["-fill", "rgb(150,104,30)", "-draw", "ellipse 650,400 110,42 0,360", "-draw", "ellipse 560,372 34,30 0,360",
          "-draw", "polygon 530,372 490,382 532,384", "-draw", "rectangle 470,450 820,458",
          "-draw", "rectangle 520,470 770,476"]
    a += ["-fill", "rgb(6,6,8)", "-draw", "circle 640,170 640,192",
          "-fill", "rgb(120,120,126)", "-draw", "rectangle 636,120 644,172"]
    a += ["-fill", "rgba(255,240,200,0.35)", "-draw", "polygon 520,200 600,170 470,460 440,430"]
    a += _bug("THE FIRST LOONIE", "Drilled on day one. Swinging on its stand all night")
    magick_png(path, *a)


def insert_bucket(path):
    a = ["-size", "1280x720", "gradient:rgb(26,20,10)-rgb(4,4,6)"]
    a += ["-fill", "rgba(255,220,150,0.18)", "-draw", "polygon 560,0 720,0 1000,720 280,720"]
    a += ["-fill", "rgb(70,30,26)", "-draw", "ellipse 640,640 420,70 0,360"]
    # the inverted bucket: wide at the floor, scuffed, an orange label band
    a += ["-fill", "rgb(222,220,210)", "-draw", "polygon 470,640 810,640 770,260 510,260",
          "-fill", "rgb(240,238,230)", "-draw", "ellipse 640,260 130,30 0,360",
          "-fill", "rgb(232,120,30)", "-draw", "polygon 490,470 790,470 783,400 497,400",
          "-fill", "rgb(150,150,140)", "-draw", "polygon 540,560 600,520 610,540 560,580",
          "-draw", "polygon 700,320 740,300 742,312 704,334",
          "-fill", "rgb(190,190,180)", "-draw", "ellipse 640,640 170,24 0,360"]
    # sticks crossed on top
    a += ["-fill", "rgb(214,180,120)", "-draw", "polygon 470,210 486,198 820,286 812,300",
          "-draw", "polygon 800,196 816,208 470,300 462,286"]
    # a raised mug at the corner, the reply
    a += ["-fill", "rgb(222,182,150)", "-draw", "roundrectangle 1040,300 1110,560 26,26",
          "-fill", "rgb(150,156,166)", "-draw", "roundrectangle 1010,150 1140,330 18,18",
          "-fill", "rgb(214,160,30)", "-draw", "roundrectangle 1000,540 1160,600 20,20"]
    a += _bug("THE BUCKET ANSWERS", "Same bucket. Platform 2 to the hometown stadium")
    magick_png(path, *a)


def insert_stand(path, col, word, arrow):
    """A stand's card stunt, as its screen shows it."""
    r, g, b = col
    a = ["-size", "1280x720", f"xc:rgb({r // 6},{g // 6},{b // 6})"]
    rnd = random.Random(7 if arrow > 0 else 9)
    for row in range(14):
        for c in range(30):
            k = rnd.uniform(0.75, 1.0)
            x, y = 20 + c * 42, 110 + row * 33
            a += ["-fill", f"rgb({int(r * k)},{int(g * k)},{int(b * k)})", "-draw", f"rectangle {x},{y} {x + 36},{y + 28}"]
    a += ["-fill", "white", "-font", HEAVY, "-pointsize", 240, "-gravity", "center", "-draw", f"text 0,20 '{word}'",
          "-gravity", "northwest"]
    a += _bug("LOWER BOWL  /  " + ("WEST" if arrow > 0 else "EAST"), "Call... and answer")
    magick_png(path, *a)


def mosaic(path, col, word, arrow, seed, bucket=False):
    """Card stunt across a side stand (2048 x 512: 8 m tiles become one picture)."""
    r, g, b = col
    a = ["-size", "2048x512", f"xc:rgb({r},{g},{b})"]
    rnd = random.Random(seed)
    for y in range(0, 512, 16):
        for x in range(0, 2048, 16):
            k = rnd.uniform(0.7, 1.0)
            a += ["-fill", f"rgb({int(r * k)},{int(g * k)},{int(b * k)})", "-draw", f"rectangle {x},{y} {x + 14},{y + 14}"]
    if bucket:
        a += ["-fill", "white", "-draw", "polygon 860,460 1188,460 1150,130 898,130",
              "-fill", "rgb(232,120,30)", "-draw", "polygon 880,330 1168,330 1160,260 888,260",
              "-fill", "white", "-draw", "polygon 820,90 840,70 1230,170 1220,190", "-draw", "polygon 1210,70 1230,90 840,190 820,170",
              "-fill", "white", "-font", HEAVY, "-pointsize", 230, "-draw", "text 120,390 'HOME'", "-draw", "text 1300,390 'TOWN'"]
    else:
        tip = 1900 if arrow > 0 else 148
        back = 1500 if arrow > 0 else 548
        a += ["-fill", "white", "-draw", f"polygon {back},80 {tip},256 {back},432",
              "-font", HEAVY, "-pointsize", 300, "-draw", f"text {260 if arrow > 0 else 700},400 '{word}'"]
    magick_png(path, *a)


def ribbon(path):
    """The LED ribbon boards on the upper deck fascia: one 2048 x 128 tile, repeated round the bowl."""
    a = ["-size", "2048x128", "xc:rgb(4,4,6)"]
    a += ["-font", HEAVY, "-pointsize", 80,
          "-fill", "rgb(255,150,40)", "-draw", "text 30,98 'WELCOME HOME'",
          "-fill", "rgb(40,210,255)", "-draw", "text 770,98 'ONE NIGHT ONLY'",
          "-fill", "rgb(255,196,70)", "-draw", "text 1590,98 'TONIGHT'",
          "-fill", "rgb(255,255,255)", "-draw", "circle 730,64 744,64", "-draw", "circle 1550,64 1564,64",
          "-draw", "circle 2010,64 2024,64"]
    magick_png(path, *a)


def backdrop(path, seed=3):
    """The LED wall behind the band: the hometown skyline at night, a gold coin of a moon."""
    W, H = 2048, 1024
    a = ["-size", f"{W}x{H}", "gradient:rgb(36,12,70)-rgb(6,8,26)"]
    a += ["-fill", "rgb(230,225,200)", "-draw", "circle 360,230 360,330",
          "-fill", "rgb(200,195,175)", "-draw", "circle 330,210 330,226", "-draw", "circle 392,262 392,276"]
    rnd = random.Random(seed)
    x = 0
    towers = []
    while x < W:
        w = rnd.randint(60, 170)
        h = rnd.randint(140, 470)
        towers.append((x, w, h))
        x += w + rnd.randint(0, 12)
    for x, w, h in towers:
        a += ["-fill", "rgb(10,10,22)", "-draw", f"rectangle {x},{H - h} {x + w},{H}"]
        for yy in range(H - h + 20, H - 10, 26):
            for xx in range(x + 10, x + w - 10, 20):
                if rnd.random() < 0.34:
                    c = rnd.choice(["rgb(255,200,120)", "rgb(255,230,170)", "rgb(140,200,255)"])
                    a += ["-fill", c, "-draw", f"rectangle {xx},{yy} {xx + 8},{yy + 12}"]
    # a needle tower (generic) and a bridge line
    a += ["-fill", "rgb(12,12,26)", "-draw", "polygon 1530,1024 1556,330 1566,330 1592,1024",
          "-draw", "ellipse 1561,520 40,22 0,360", "-fill", "rgb(255,60,60)", "-draw", "circle 1561,320 1561,326"]
    magick_png(path, *a)
