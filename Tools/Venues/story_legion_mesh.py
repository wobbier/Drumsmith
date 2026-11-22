"""StoryLegion's prop shop: a tiny low-poly mesh builder that writes OBJs into
Assets/Venues/StoryLegion/Models/, flat-coloured from one painted palette (Legion_Palette.png) or
mapped to one of the hall's painted textures (story_legion_textures.py).

Geometry is authored in venue space (metres, +y up, +z toward the band); faces are counter-clockwise
seen from outside. Written OBJs flip z (and the winding with it), as the Backyard's are, because the
importer turns OBJ space back into venue space. Deterministic: a rerun writes the same bytes, and a
file that hasn't changed isn't touched.
"""
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VENUE = ROOT / 'Assets/Venues/StoryLegion'
MODELS = VENUE / 'Models'
LOCAL = 'Assets/Venues/StoryLegion/Models/'

# The palette: one 16 px swatch per ink on a 256 x 256 sheet (sRGB).
INKS = {
    'cloth': '#EDEAE2', 'cloth_shade': '#D9D4CA', 'cream': '#E6D8B8', 'paper': '#F4F0E4',
    'wood_dark': '#3E2617', 'wood_mid': '#6E4428', 'wood_light': '#A2703F', 'wood_red': '#5C2A1C',
    'piano': '#1B1214', 'piano_edge': '#3A2A26', 'ivory': '#F1E9D4', 'key_black': '#121212',
    'chrome': '#B9BDC3', 'steel': '#62666C', 'chair_frame': '#B6AC98', 'chair_vinyl': '#5A3F2E',
    'red': '#A21F23', 'navy': '#1D2848', 'gold': '#C79F4A', 'brass': '#A9843B',
    'exit_green': '#2EB24A', 'lemon': '#EFD04F', 'lemon_crust': '#C99B55', 'cake': '#6A3D22',
    'pink_icing': '#E6A2B6', 'icing': '#F6F2EA', 'plate': '#FAFAF7', 'urn': '#BFC3C8',
    'tie': '#8C1C2B', 'shoe_black': '#161414', 'heel': '#5E1426', 'flower_red': '#C1243A',
    'flower_white': '#EFEFE8', 'leaf': '#3C6A34', 'candle': '#F3E9CE', 'flame': '#FFD27A',
    'napkin': '#F8F6F0', 'rubber': '#232323', 'curtain': '#5E1420', 'curtain_dark': '#3E0C15',
    'carpet': '#283656', 'glass': '#9DBEC8', 'wine': '#561020', 'beer': '#CF8E2E',
    'felt': '#1C1C1F', 'poppy': '#C70F2C', 'balloon_gold': '#D9B355', 'balloon_navy': '#2A3A6A',
    'cord': '#2B2B2B', 'bulb_warm': '#FFC978', 'bulb_pink': '#FF5A9A', 'bulb_teal': '#4FE3E0',
    'bulb_blue': '#5A78FF', 'tbar': '#D8D6D0', 'lino_a': '#CDBF9F', 'lino_b': '#8E7458',
    'coffee': '#3A2416', 'mug': '#E9E4DA', 'coat_grey': '#5A5D63', 'coat_camel': '#9B7A52',
    'coat_navy': '#22283A', 'black': '#0E0E10', 'white': '#FFFFFF', 'dart_cork': '#C9A877',
    'dart_red': '#9E1C1C', 'dart_green': '#1F5E35', 'bar_top': '#2A1A12', 'bottle_green': '#2E5A34',
    'bottle_amber': '#8A4E16', 'tap': '#C7B27A', 'mirror': '#7F8C94', 'sash': '#2C3E66',
    'night': '#141C33', 'blind': '#D8D2C2', 'linen_red': '#B83A3A', 'linen': '#EFE9DD',
}
GRID = 16
SWATCH = 256 // GRID


def ink_uv(ink):
    i = list(INKS).index(ink)
    x, y = (i % GRID) * SWATCH + SWATCH / 2, (i // GRID) * SWATCH + SWATCH / 2
    return (x / 256.0, 1.0 - y / 256.0)


def save(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = content.encode()
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)
        twin = path.with_name(path.name + '.assbin')
        if twin.exists():
            twin.unlink()


def write_mtl(textures):
    """One material library for every Legion mesh: the palette plus each painted texture."""
    lines = []
    for name, png in [('Palette', 'Textures/Legion_Palette.png')] + [(t, f'Textures/{t}.png') for t in textures]:
        lines += [f'newmtl {name}', 'Kd 1 1 1', 'Ks 0 0 0', 'Ns 0', 'illum 1', f'map_Kd ../{png}', '']
    save(MODELS / 'Legion.mtl', '\n'.join(lines))


def rot_y(p, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    x, y, z = p
    return (x * c + z * s, y, -x * s + z * c)


def rot_x(p, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    x, y, z = p
    return (x, y * c - z * s, y * s + z * c)


def rot_z(p, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    x, y, z = p
    return (x * c - y * s, x * s + y * c, z)


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def unit(a):
    l = math.sqrt(dot(a, a)) or 1.0
    return (a[0] / l, a[1] / l, a[2] / l)


class Mesh:
    """Faces in venue space. A face is (points, material, uvs); palette faces use one swatch."""

    def __init__(self, name, note):
        self.name, self.note = name, note
        self.faces = []
        self.xf = []   # a stack of transforms: (offset, yaw, pitch, roll) applied to new geometry

    # ---- transforms ------------------------------------------------------------------------
    def push(self, at=(0, 0, 0), yaw=0.0, pitch=0.0, roll=0.0):
        self.xf.append((at, yaw, pitch, roll))
        return self

    def pop(self):
        self.xf.pop()
        return self

    def _apply(self, p):
        for at, yaw, pitch, roll in reversed(self.xf):
            p = rot_z(p, roll)
            p = rot_x(p, pitch)
            p = rot_y(p, yaw)
            p = (p[0] + at[0], p[1] + at[1], p[2] + at[2])
        return p

    # ---- faces -----------------------------------------------------------------------------
    def face(self, pts, ink='white', uvs=None, mat=None):
        pts = [self._apply(p) for p in pts]
        if mat is None:
            self.faces.append((pts, 'Palette', [ink_uv(ink)] * len(pts)))
        else:
            self.faces.append((pts, mat, uvs))

    def quad(self, a, b, c, d, ink='white', mat=None, uv=((0, 0), (1, 0), (1, 1), (0, 1)), both=False):
        self.face([a, b, c, d], ink, list(uv), mat)
        if both:
            self.face([d, c, b, a], ink, list(uv)[::-1], mat)

    def box(self, centre, size, ink, yaw=0.0, top=None, inks=None):
        """An axis box (optionally yawed about its centre). inks: per side +x,-x,+y,-y,+z,-z."""
        cx, cy, cz = centre
        hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
        self.push(centre, yaw)
        P = lambda x, y, z: (x * hx, y * hy, z * hz)
        sides = inks or [ink] * 6
        if top:
            sides = list(sides)
            sides[2] = top
        self.quad(P(1, -1, 1), P(1, -1, -1), P(1, 1, -1), P(1, 1, 1), sides[0])      # +x
        self.quad(P(-1, -1, -1), P(-1, -1, 1), P(-1, 1, 1), P(-1, 1, -1), sides[1])  # -x
        self.quad(P(-1, 1, 1), P(1, 1, 1), P(1, 1, -1), P(-1, 1, -1), sides[2])      # +y
        self.quad(P(-1, -1, -1), P(1, -1, -1), P(1, -1, 1), P(-1, -1, 1), sides[3])  # -y
        self.quad(P(-1, -1, 1), P(1, -1, 1), P(1, 1, 1), P(-1, 1, 1), sides[4])      # +z
        self.quad(P(1, -1, -1), P(-1, -1, -1), P(-1, 1, -1), P(1, 1, -1), sides[5])  # -z
        self.pop()

    def slab(self, x0, x1, y0, y1, z0, z1, ink, **kw):
        self.box(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (x1 - x0, y1 - y0, z1 - z0), ink, **kw)

    def cyl(self, base, radius, height, ink, sides=10, top=None, bottom=True, radius_top=None, cap=True):
        """An upright cylinder (or cone frustum) standing on base."""
        bx, by, bz = base
        rt = radius if radius_top is None else radius_top
        ring = [(math.sin(2 * math.pi * i / sides), math.cos(2 * math.pi * i / sides)) for i in range(sides)]
        for i in range(sides):
            (s0, c0), (s1, c1) = ring[i], ring[(i + 1) % sides]
            self.quad((bx + s0 * radius, by, bz + c0 * radius), (bx + s1 * radius, by, bz + c1 * radius),
                      (bx + s1 * rt, by + height, bz + c1 * rt), (bx + s0 * rt, by + height, bz + c0 * rt), ink)
        if cap and rt > 0:
            self.face([(bx + s * rt, by + height, bz + c * rt) for s, c in ring], top or ink)
        if bottom and radius > 0:
            self.face([(bx + s * radius, by, bz + c * radius) for s, c in ring][::-1], ink)

    def tube(self, a, b, r, ink, sides=6):
        """A thin prism from a to b (legs, rails, poles)."""
        d = sub(b, a)
        axis = unit(d)
        ref = (0, 1, 0) if abs(axis[1]) < .9 else (1, 0, 0)
        u = unit(cross(axis, ref))
        v = cross(axis, u)
        ring = [tuple(u[k] * math.cos(2 * math.pi * i / sides) * r + v[k] * math.sin(2 * math.pi * i / sides) * r
                      for k in range(3)) for i in range(sides)]
        for i in range(sides):
            p0, p1 = ring[i], ring[(i + 1) % sides]
            self.quad(tuple(a[k] + p0[k] for k in range(3)), tuple(a[k] + p1[k] for k in range(3)),
                      tuple(b[k] + p1[k] for k in range(3)), tuple(b[k] + p0[k] for k in range(3)), ink)
        self.face([tuple(b[k] + p[k] for k in range(3)) for p in ring], ink)
        self.face([tuple(a[k] + p[k] for k in range(3)) for p in ring][::-1], ink)

    def sphere(self, c, r, ink, sides=8, bands=5, squash=1.0):
        pts = lambda i, j: (c[0] + r * math.sin(math.pi * j / bands) * math.sin(2 * math.pi * i / sides),
                            c[1] + r * squash * math.cos(math.pi * j / bands),
                            c[2] + r * math.sin(math.pi * j / bands) * math.cos(2 * math.pi * i / sides))
        for j in range(bands):
            for i in range(sides):
                a, b, cc, d = pts(i, j), pts(i, j + 1), pts(i + 1, j + 1), pts(i + 1, j)
                if j == 0:
                    self.face([a, b, cc], ink)
                elif j == bands - 1:
                    self.face([a, b, d], ink)
                else:
                    self.quad(a, b, cc, d, ink)

    def picture(self, centre, w, h, mat, yaw=0.0, depth=0.0, uv=((0, 0), (1, 0), (1, 1), (0, 1))):
        """A textured quad facing -z (the crowd) at yaw 0."""
        self.push(centre, yaw)
        x, y = w / 2, h / 2
        self.quad((x, -y, -depth), (-x, -y, -depth), (-x, y, -depth), (x, y, -depth), mat=mat,
                  uv=((uv[0][0], uv[0][1]), (uv[1][0], uv[1][1]), (uv[2][0], uv[2][1]), (uv[3][0], uv[3][1])))
        self.pop()

    def frame(self, centre, w, h, border, depth, ink, yaw=0.0):
        """A picture frame moulding around a w x h opening, facing -z."""
        cx, cy, cz = centre
        self.push(centre, yaw)
        b = border
        for x0, x1, y0, y1 in [(-w / 2 - b, w / 2 + b, h / 2, h / 2 + b), (-w / 2 - b, w / 2 + b, -h / 2 - b, -h / 2),
                               (-w / 2 - b, -w / 2, -h / 2, h / 2), (w / 2, w / 2 + b, -h / 2, h / 2)]:
            self.slab(x0, x1, y0, y1, -depth, depth * .3, ink)
        self.pop()

    # ---- output ----------------------------------------------------------------------------
    def write(self):
        coords, uvs, normals, by_mat = {}, {}, {}, {}
        for pts, mat, tex in self.faces:
            xyz = [(round(x, 5) + 0.0, round(y, 5) + 0.0, round(-z, 5) + 0.0) for x, y, z in reversed(pts)]
            tex = list(reversed(tex))
            n = cross(sub(xyz[1], xyz[0]), sub(xyz[2], xyz[0]))
            if dot(n, n) < 1e-16:
                continue
            n = tuple(round(v, 5) + 0.0 for v in unit(n))
            ni = normals.setdefault(n, len(normals) + 1)
            ids = []
            for p, t in zip(xyz, tex):
                vi = coords.setdefault(p, len(coords) + 1)
                ti = uvs.setdefault((round(t[0], 5), round(t[1], 5)), len(uvs) + 1)
                ids.append(f'{vi}/{ti}/{ni}')
            by_mat.setdefault(mat, []).append('f ' + ' '.join(ids))
        lines = [f'# {self.note}', '# Generated by Tools/Venues/story_legion_mesh.py (make_story_legion.py).',
                 'mtllib Legion.mtl', 'o ' + self.name, 's off']
        lines += ['v %g %g %g' % p for p in coords]
        lines += ['vt %g %g' % t for t in uvs]
        lines += ['vn %g %g %g' % n for n in normals]
        for mat in sorted(by_mat):
            lines += ['usemtl ' + mat] + by_mat[mat]
        save(MODELS / (self.name + '.obj'), '\n'.join(lines) + '\n')
        return LOCAL + self.name + '.obj'
