"""The drive-in's prop shop: low-poly cars, speaker posts, the FM mast, the projector beam and the
screen's lattice, written as OBJs on one palette texture (Assets/Venues/StoryDriveIn/Textures/
Palette.png, drawn by story_drive_in_textures.py). All geometry is authored in venue metres with
the model's front toward +z and its pivot on the floor; mesh_file() mirrors z on the way out
because Assimp reflects it on the way in (the same as the Backyard's exporter).
"""
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VENUE = ROOT / 'Assets/Venues/StoryDriveIn'
MODELS = VENUE / 'Models'
PALETTE_PNG = '../Textures/Palette.png'

# 8 x 8 swatches on a 256 px texture: name -> (column, row), colour (sRGB hex).
SWATCHES = [
    ('black', '#141416'), ('tyre', '#1d1d20'), ('chrome', '#b9bcc2'), ('steel', '#6c7077'),
    ('glass', '#1f2c3d'), ('glass_lit', '#3a5674'), ('head_lens', '#f2ecd0'), ('tail_lens', '#8a1414'),
    ('cream', '#e3d6b4'), ('teal', '#3f8a86'), ('maroon', '#7a2230'), ('mustard', '#c99a2e'),
    ('navy', '#27365c'), ('silver', '#9aa2ab'), ('olive', '#5e6b3a'), ('rust', '#b0532a'),
    ('powder', '#8fb5cf'), ('white', '#e8e8e4'), ('mint', '#9fcfb0'), ('plum', '#5b3a6b'),
    ('block', '#8d8a82'), ('block_dark', '#5d5b56'), ('roof', '#3b3a38'), ('wood', '#7a5434'),
    ('ply', '#b58c5c'), ('screen_back', '#5a5f66'), ('red_paint', '#b3262a'), ('signal', '#ff3a2a'),
    ('gravel', '#6e6658'), ('grass', '#2f3d27'), ('rubber', '#2b2b2b'), ('amber', '#ffb347'),
    ('bed', '#2a2622'), ('interior', '#3a3330'), ('canvas', '#c9c0a8'), ('orange', '#e06a1c'),
]
UV = {name: ((i % 8 + .5) / 8, 1 - (i // 8 + .5) / 8) for i, (name, _) in enumerate(SWATCHES)}
PAINTS = ['cream', 'teal', 'maroon', 'mustard', 'navy', 'silver', 'olive', 'rust', 'powder', 'white', 'mint', 'plum', 'red_paint']


def sub(a, b): return tuple(x - y for x, y in zip(a, b))
def cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def dot(a, b): return sum(x * y for x, y in zip(a, b))
def unit(v):
    n = math.sqrt(dot(v, v))
    return tuple(x / n for x in v) if n > 1e-12 else (0, 1, 0)


class Mesh:
    """Faces are lists of venue-space points, counter-clockwise seen from outside."""
    def __init__(self, name, note):
        self.name, self.note, self.faces = name, note, []

    def face(self, pts, ink):
        self.faces.append((list(pts), ink))

    def quad(self, a, b, c, d, ink):
        self.face([a, b, c, d], ink)

    def box(self, lo, hi, ink, top=None):
        (x0, y0, z0), (x1, y1, z1) = lo, hi
        t = top or ink
        P = lambda x, y, z: (x, y, z)
        self.quad(P(x0,y0,z1), P(x1,y0,z1), P(x1,y1,z1), P(x0,y1,z1), ink)   # +z
        self.quad(P(x1,y0,z0), P(x0,y0,z0), P(x0,y1,z0), P(x1,y1,z0), ink)   # -z
        self.quad(P(x1,y0,z1), P(x1,y0,z0), P(x1,y1,z0), P(x1,y1,z1), ink)   # +x
        self.quad(P(x0,y0,z0), P(x0,y0,z1), P(x0,y1,z1), P(x0,y1,z0), ink)   # -x
        self.quad(P(x0,y1,z1), P(x1,y1,z1), P(x1,y1,z0), P(x0,y1,z0), t)     # +y
        self.quad(P(x0,y0,z0), P(x1,y0,z0), P(x1,y0,z1), P(x0,y0,z1), ink)   # -y

    def extrude_x(self, profile, x0, x1, ink, cap=None):
        """A convex side profile [(z, y), ...] (counter-clockwise seen from +x) swept from x0 to x1."""
        cap = cap or ink
        n = len(profile)
        side_p = [(x1, y, z) for z, y in profile]
        side_n = [(x0, y, z) for z, y in profile]
        self._oriented(side_p, (1, 0, 0), cap)
        self._oriented(side_n, (-1, 0, 0), cap)
        cz = sum(z for z, _ in profile) / n
        cy = sum(y for _, y in profile) / n
        for i in range(n):
            (za, ya), (zb, yb) = profile[i], profile[(i + 1) % n]
            quad = [(x0, ya, za), (x1, ya, za), (x1, yb, zb), (x0, yb, zb)]
            mid = ((za + zb) / 2 - cz, (ya + yb) / 2 - cy)
            self._oriented(quad, (0, mid[1], mid[0]), ink)

    def _oriented(self, pts, outward, ink):
        n = cross(sub(pts[1], pts[0]), sub(pts[2], pts[0]))
        if dot(n, n) < 1e-14 and len(pts) > 3:
            n = cross(sub(pts[2], pts[0]), sub(pts[3], pts[0]))
        self.face(pts if dot(n, outward) >= 0 else pts[::-1], ink)

    def prism(self, centre, axis, radius, half, ink, sides=8, cap=None):
        """A cylinder of `sides` faces along axis 'x' | 'y' | 'z' (a wheel, a pole)."""
        cx, cy, cz = centre
        ring = []
        for i in range(sides):
            a = 2 * math.pi * (i + .5) / sides
            u, v = radius * math.cos(a), radius * math.sin(a)
            ring.append((u, v))
        def pt(u, v, h):
            if axis == 'x': return (cx + h, cy + u, cz + v)
            if axis == 'y': return (cx + u, cy + h, cz + v)
            return (cx + u, cy + v, cz + h)
        ax = {'x': (1, 0, 0), 'y': (0, 1, 0), 'z': (0, 0, 1)}[axis]
        self._oriented([pt(u, v, half) for u, v in ring], ax, cap or ink)
        self._oriented([pt(u, v, -half) for u, v in ring], tuple(-a for a in ax), cap or ink)
        for i in range(sides):
            (ua, va), (ub, vb) = ring[i], ring[(i + 1) % sides]
            q = [pt(ua, va, -half), pt(ub, vb, -half), pt(ub, vb, half), pt(ua, va, half)]
            mu, mv = (ua + ub) / 2, (va + vb) / 2
            self._oriented(q, sub(pt(mu, mv, 0), pt(0, 0, 0)), ink)

    def strut(self, a, b, w, ink):
        """A square bar from a to b, w across (lattice members, pipes)."""
        d = unit(sub(b, a))
        up = (0, 1, 0) if abs(d[1]) < .9 else (1, 0, 0)
        u = unit(cross(d, up)); v = unit(cross(u, d))
        h = w / 2
        corners = [(u[i]*h*su + v[i]*h*sv) for su, sv in ((1,1),(-1,1),(-1,-1),(1,-1)) for i in range(3)]
        offs = [tuple(corners[k*3:k*3+3]) for k in range(4)]
        A = [tuple(a[i] + o[i] for i in range(3)) for o in offs]
        B = [tuple(b[i] + o[i] for i in range(3)) for o in offs]
        for k in range(4):
            q = [A[k], A[(k+1) % 4], B[(k+1) % 4], B[k]]
            mid = tuple((offs[k][i] + offs[(k+1) % 4][i]) for i in range(3))
            self._oriented(q, mid, ink)
        self._oriented(A, tuple(-x for x in d), ink)
        self._oriented(B, d, ink)


def save(path, content):
    data = content.encode()
    if path.exists() and path.read_bytes() == data:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    twin = path.with_name(path.name + '.assbin')
    if twin.exists():
        twin.unlink()   # stale cook: the game re-cooks it from the new OBJ


def mesh_file(mesh, mtl='Palette'):
    coords, normals, faces = {}, {}, []
    names = [n for n, _ in SWATCHES]
    for pts, ink in mesh.faces:
        xyz = [(round(x, 5) + 0.0, round(y, 5) + 0.0, round(-z, 5) + 0.0) for x, y, z in reversed(pts)]
        n = cross(sub(xyz[1], xyz[0]), sub(xyz[2], xyz[0]))
        if dot(n, n) < 1e-14:
            continue
        n = tuple(round(v, 5) + 0.0 for v in unit(n))
        ni = normals.setdefault(n, len(normals) + 1)
        ti = names.index(ink) + 1
        faces.append('f ' + ' '.join(f'{coords.setdefault(p, len(coords) + 1)}/{ti}/{ni}' for p in xyz))
    lines = [f'# {mesh.note}', f'mtllib {mtl}.mtl', 'o ' + mesh.name, 's off']
    lines += ['v %g %g %g' % p for p in coords]
    lines += ['vt %.6f %.6f' % UV[n] for n in names]
    lines += ['vn %g %g %g' % n for n in normals] + [f'usemtl {mtl}'] + faces
    save(MODELS / (mesh.name + '.obj'), '\n'.join(lines) + '\n')
    return 'Assets/Venues/StoryDriveIn/Models/' + mesh.name + '.obj'


def palette_mtl():
    save(MODELS / 'Palette.mtl', 'newmtl Palette\nKd 1 1 1\nKs 0 0 0\nNs 0\nillum 1\nmap_Kd ' + PALETTE_PNG + '\n')


# ---- cars ------------------------------------------------------------------------------------
# Each shape: length, half-width, body profile, greenhouse profile, roof (z0, z1, y), wheel z's,
# wheel radius, and where its lamps sit (for the emissive lenses the scene adds).
SHAPES = {
    'Hatch': dict(body=[(-2.0,.30),(2.0,.30),(2.0,.62),(1.85,.84),(.9,.96),(-1.95,.96),(-2.0,.86)],
                  glass=[(-1.93,.96),(.9,.96),(.32,1.40),(-1.72,1.40)], roof=(-1.72,.32,1.40), hw=.86,
                  wheels=(-1.28,1.28), r=.31, head=(2.0,.66,.62), tail=(-2.0,.78,.66)),
    'Sedan': dict(body=[(-2.25,.30),(2.25,.30),(2.25,.60),(2.05,.84),(1.0,.96),(-1.25,.96),(-1.95,.92),(-2.25,.80)],
                  glass=[(-1.25,.96),(1.0,.96),(.42,1.38),(-.78,1.38)], roof=(-.78,.42,1.38), hw=.9,
                  wheels=(-1.42,1.42), r=.32, head=(2.25,.66,.64), tail=(-2.25,.74,.66)),
    'Wagon': dict(body=[(-2.3,.38),(2.3,.38),(2.3,.72),(2.1,.95),(1.15,1.05),(-2.3,1.05)],
                  glass=[(-2.25,1.05),(1.15,1.05),(.55,1.58),(-2.1,1.58)], roof=(-2.1,.55,1.58), hw=.92,
                  wheels=(-1.5,1.5), r=.36, head=(2.3,.80,.66), tail=(-2.3,.88,.70)),
    'Pickup': dict(body=[(-2.5,.42),(2.5,.42),(2.5,.78),(2.3,1.0),(1.3,1.08),(-2.5,1.08)],
                   glass=[(-.62,1.08),(1.3,1.08),(.78,1.62),(-.56,1.62)], roof=(-.56,.78,1.62), hw=.95,
                   wheels=(-1.65,1.6), r=.38, head=(2.5,.84,.68), tail=(-2.5,.92,.74)),
    'Van': dict(body=[(-2.45,.36),(2.45,.36),(2.45,.82),(2.2,1.06),(1.6,1.16),(-2.45,1.16)],
                glass=[(-2.4,1.16),(1.6,1.16),(1.0,1.98),(-2.4,1.98)], roof=(-2.4,1.0,1.98), hw=.95,
                wheels=(-1.6,1.6), r=.35, head=(2.45,.84,.66), tail=(-2.45,1.1,.72)),
}


def car(shape, paint, hatch_open=False):
    S = SHAPES[shape]
    name = f'Car{shape}{paint.title().replace("_", "")}' + ('Open' if hatch_open else '')
    m = Mesh(name, f'Drive-in {shape.lower()} in {paint}; front toward +z, floor pivot.')
    hw = S['hw']
    m.extrude_x(S['body'], -hw, hw, paint)
    glass = S['glass']
    m.extrude_x(glass, -hw + .07, hw - .07, 'glass')
    z0, z1, y = S['roof']
    m.box((-hw + .05, y - .01, z0 + .02), (hw - .05, y + .06, z1 - .02), paint)
    # A pillars and B pillar in paint so the glass reads as windows.
    zb = (z0 + z1) / 2 - .1
    m.box((-hw + .045, glass[0][1], zb - .07), (hw - .045, y, zb + .07), paint)
    if shape == 'Pickup':
        m.box((-hw + .1, .98, -2.42), (hw - .1, 1.1, -.7), 'bed')
        m.box((-hw, 1.08, -2.5), (hw, 1.3, -2.42), paint)
        for sx in (-1, 1):
            a, b = sorted((sx * hw, sx * (hw - .08)))
            m.box((a, 1.08, -2.5), (b, 1.3, -.62), paint)
    if shape == 'Van':
        m.box((-hw + .04, 1.16, -2.42), (hw - .04, 1.97, -.15), paint)
    L = S['body'][1][0]; R = S['body'][0][0]
    m.box((-hw - .02, .26, L - .06), (hw + .02, .48, L + .1), 'chrome')      # front bumper
    m.box((-hw - .02, .26, R - .1), (hw + .02, .48, R + .06), 'chrome')      # rear bumper
    m.box((-hw * .55, .5, L - .02), (hw * .55, .66, L + .03), 'black')       # grille
    hz, hy, hx = S['head']
    for sx in (-1, 1):
        m.box((sx * hx - .17, hy - .08, hz - .03), (sx * hx + .17, hy + .08, hz + .02), 'head_lens')
    tz, ty, tx = S['tail']
    for sx in (-1, 1):
        m.box((sx * tx - .15, ty - .07, tz - .02), (sx * tx + .15, ty + .07, tz + .03), 'tail_lens')
    for wz in S['wheels']:
        for sx in (-1, 1):
            m.prism((sx * (hw - .06), S['r'], wz), 'x', S['r'], .13, 'tyre', sides=8)
            m.prism((sx * (hw + .075), S['r'], wz), 'x', S['r'] * .55, .012, 'chrome', sides=8)
    if hatch_open:
        # The tailgate swung up past the roof line: a lid of paint with its glass, propped open.
        zr, yr = glass[3]
        lid_end = (zr - 1.05, yr + .55)
        a = (zr, yr); b = lid_end
        m.extrude_x([(a[0], a[1]), (b[0], b[1]), (b[0] - .04, b[1] - .07), (a[0] - .02, a[1] - .08)], -hw + .03, hw - .03, paint)
        m.extrude_x([(a[0] - .15, a[1] + .06), (b[0] + .1, b[1] - .02), (b[0] + .08, b[1] - .05), (a[0] - .16, a[1] + .02)],
                    -hw + .18, hw - .18, 'glass_lit')
        m.box((-hw + .1, .56, R - .28), (hw - .1, .64, R + .05), 'interior')   # the cargo lip they sit on
    return mesh_file(m), S


def speaker_post():
    m = Mesh('SpeakerPost', 'Drive-in speaker post: pipe, junction box, two window speakers on hooks. 1.25 m.')
    m.prism((0, .62, 0), 'y', .045, .62, 'steel', sides=6)
    m.box((-.12, 1.0, -.07), (.12, 1.22, .07), 'steel')
    for sx in (-1, 1):
        m.strut((sx * .1, 1.15, 0), (sx * .26, 1.15, 0), .03, 'steel')
        m.box((sx * .26 - .09, .92, -.06), (sx * .26 + .09, 1.12, .06), 'roof')
        m.box((sx * .26 - .075, .94, .06), (sx * .26 + .075, 1.10, .065), 'black')
    m.box((-.18, 0, -.18), (.18, .06, .18), 'block_dark')
    return mesh_file(m)


def fm_mast(height=15.0):
    m = Mesh('FMMast', f'Triangular lattice FM mast, {height:g} m, three legs and zigzag bracing; base pivot.')
    r0, r1 = .55, .28
    legs = []
    for k in range(3):
        a = math.radians(90 + 120 * k)
        legs.append((math.cos(a), math.sin(a)))
    def at(k, t):
        r = r0 + (r1 - r0) * t
        return (legs[k][0] * r, height * t, legs[k][1] * r)
    for k in range(3):
        m.strut(at(k, 0), at(k, 1), .07, 'red_paint' if k == 0 else 'white')
    steps = 14
    for i in range(steps):
        t0, t1 = i / steps, (i + 1) / steps
        for k in range(3):
            j = (k + 1) % 3
            m.strut(at(k, t0), at(j, t1), .035, 'white' if i % 2 else 'red_paint')
            m.strut(at(k, t1), at(j, t1), .03, 'steel')
    m.prism((0, height + .6, 0), 'y', .035, .6, 'steel', sides=6)
    for h in (.55, .8):   # dipole arms
        m.strut((-.9, height * h, 0), (.9, height * h, 0), .04, 'steel')
    return mesh_file(m)


def beam(name='Beam'):
    """A unit light cone, a square frustum: apex 0.04 wide at the origin, 2 x 2 at z = 1."""
    m = Mesh(name, 'Unit beam frustum: near end at the origin, far end 2 x 2 at z = 1. Scale x/y for the spread, z for the throw.')
    n, f = .02, 1.0
    A = [(-n, -n, 0), (n, -n, 0), (n, n, 0), (-n, n, 0)]
    B = [(-f, -f, 1), (f, -f, 1), (f, f, 1), (-f, f, 1)]
    for k in range(4):
        q = [A[k], A[(k + 1) % 4], B[(k + 1) % 4], B[k]]
        m.face(q, 'white'); m.face(q[::-1], 'white')
    return mesh_file(m)


def screen_lattice(width, height, base, depth=3.2):
    """The steel frame behind the screen face: columns, horizontal girts and back raking struts.
    Local: the face plane is z = 0 (the scene puts it just behind the picture), the frame is +z."""
    m = Mesh('ScreenLattice', f'Drive-in screen back frame for a {width:g} x {height:g} m face, {base:g} m legs.')
    cols = 9
    xs = [-width / 2 + width * i / (cols - 1) for i in range(cols)]
    top = base + height
    for x in xs:
        m.strut((x, 0, .25), (x, top + .3, .25), .26, 'screen_back')
        m.strut((x, 0, depth), (x, top * .82, depth), .2, 'screen_back')
        m.strut((x, top * .82, depth), (x, top + .3, .25), .16, 'screen_back')
        for t in (.2, .45, .7):
            y = top * t
            m.strut((x, y, .25), (x, y + top * .14, depth), .1, 'steel')
    for y in [base + height * t for t in (0, .25, .5, .75, 1)] + [base * .5]:
        m.strut((xs[0], y, .38), (xs[-1], y, .38), .14, 'screen_back')
    for i in range(cols - 1):
        m.strut((xs[i], base, .4), (xs[i + 1], top, .4), .08, 'steel')
    # The face boards between the picture and the frame: a pale skin a little bigger than the picture.
    m.box((-width / 2 - .6, base - .6, .05), (width / 2 + .6, top + .6, .2), 'block', top='block')
    return mesh_file(m)


def light_tower(height=9.0):
    m = Mesh('LightTower', f'Festival light tower: a square lattice column with a head bar, {height:g} m.')
    w = .32
    corners = [(-w, -w), (w, -w), (w, w), (-w, w)]
    for x, z in corners:
        m.strut((x, 0, z), (x, height, z), .05, 'steel')
    for i in range(int(height / .8)):
        y0, y1 = i * .8, (i + 1) * .8
        for k in range(4):
            a, b = corners[k], corners[(k + 1) % 4]
            m.strut((a[0], y0, a[1]), (b[0], y1, b[1]), .025, 'chrome')
    m.box((-1.6, height - .1, -.12), (1.6, height + .1, .12), 'black')
    m.box((-.7, 0, -.7), (.7, .25, .7), 'block_dark')
    return mesh_file(m)


def fence_run(length=40.0):
    m = Mesh('Fence', f'Post-and-wire lot fence, {length:g} m along x, posts every 4 m. 1.4 m tall.')
    n = int(length / 4)
    for i in range(n + 1):
        x = -length / 2 + i * 4
        m.box((x - .06, 0, -.06), (x + .06, 1.4, .06), 'wood')
    for y in (.45, .9, 1.32):
        m.box((-length / 2, y - .015, -.015), (length / 2, y + .015, .015), 'steel')
    return mesh_file(m)


def booth_details():
    """The booth's projection hardware: a projector body with its lens and reels."""
    m = Mesh('Projector', 'Carbon-arc style projector on a pedestal, lens toward +z, two reels on top. 1.7 m tall.')
    m.box((-.18, 0, -.25), (.18, .9, .25), 'steel')
    m.box((-.3, .9, -.55), (.3, 1.35, .5), 'roof')
    m.prism((0, 1.12, .62), 'z', .13, .14, 'chrome', sides=10)
    for z, y, r in ((-.2, 1.62, .32), (.2, 1.58, .28)):
        m.prism((0, y, z), 'x', r, .03, 'steel', sides=12)
    m.box((-.32, 1.2, -.75), (.32, 1.32, -.55), 'black')
    return mesh_file(m)


def thermos():
    m = Mesh('Thermos', 'A tartan-free steel thermos, 0.32 m, with its cup on top.')
    m.prism((0, .14, 0), 'y', .05, .14, 'chrome', sides=10)
    m.prism((0, .3, 0), 'y', .052, .025, 'red_paint', sides=10)
    return mesh_file(m)
