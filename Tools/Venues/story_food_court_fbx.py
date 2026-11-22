"""Food Court venue: a stdlib-only binary FBX (7.x) to OBJ converter for the owner's Synty packs.

Reads the mesh geometry of every Model in the file, applies the node transforms (Lcl and Pre
rotation, translation, scaling; the Synty files are exported Y-up in centimetres with a root
rotation), merges them into one mesh, normalises the result to a requested size with a
floor-centred pivot, and writes an OBJ that binds the pack's atlas through a local MTL.
Deterministic: the same FBX gives the same bytes.
"""
import math
import struct
import zlib


# ---- binary FBX reader -------------------------------------------------------------------------
class Node:
    __slots__ = ('name', 'props', 'children')

    def __init__(self, name, props, children):
        self.name, self.props, self.children = name, props, children

    def find(self, name):
        for c in self.children:
            if c.name == name:
                return c
        return None

    def all(self, name):
        return [c for c in self.children if c.name == name]


def _array(data, off, code):
    n, enc, clen = struct.unpack_from('<III', data, off)
    off += 12
    raw = data[off:off + clen]
    off += clen
    if enc == 1:
        raw = zlib.decompress(raw)
    fmt = {'f': 'f', 'd': 'd', 'l': 'q', 'i': 'i', 'b': 'b'}[code]
    return list(struct.unpack('<%d%s' % (n, fmt), raw[:n * struct.calcsize(fmt)])), off


def _props(data, off, count):
    out = []
    for _ in range(count):
        code = chr(data[off]); off += 1
        if code == 'Y': out.append(struct.unpack_from('<h', data, off)[0]); off += 2
        elif code == 'C': out.append(bool(data[off])); off += 1
        elif code == 'I': out.append(struct.unpack_from('<i', data, off)[0]); off += 4
        elif code == 'F': out.append(struct.unpack_from('<f', data, off)[0]); off += 4
        elif code == 'D': out.append(struct.unpack_from('<d', data, off)[0]); off += 8
        elif code == 'L': out.append(struct.unpack_from('<q', data, off)[0]); off += 8
        elif code in 'fdlib':
            v, off = _array(data, off, code); out.append(v)
        elif code in 'SR':
            n = struct.unpack_from('<I', data, off)[0]; off += 4
            b = data[off:off + n]; off += n
            out.append(b.decode('utf-8', 'replace') if code == 'S' else b)
        else:
            raise ValueError('bad FBX property type %r' % code)
    return out


def _node(data, off, wide):
    if wide:
        end, nprops, plen = struct.unpack_from('<QQQ', data, off); off += 24
    else:
        end, nprops, plen = struct.unpack_from('<III', data, off); off += 12
    if end == 0:
        return None, off
    nlen = data[off]; off += 1
    name = data[off:off + nlen].decode(); off += nlen
    props = _props(data, off, nprops); off += plen
    children = []
    while off < end:
        child, off = _node(data, off, wide)
        if child is None:
            break
        children.append(child)
    return Node(name, props, children), end


def read_fbx(path):
    data = open(path, 'rb').read()
    if not data.startswith(b'Kaydara FBX Binary'):
        raise ValueError(path + ': not a binary FBX')
    version = struct.unpack_from('<I', data, 23)[0]
    wide = version >= 7500
    off, top = 27, []
    while off < len(data):
        n, off = _node(data, off, wide)
        if n is None:
            break
        top.append(n)
    return Node('', [], top)


# ---- maths -------------------------------------------------------------------------------------
def _mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def _translate(t):
    return [[1, 0, 0, t[0]], [0, 1, 0, t[1]], [0, 0, 1, t[2]], [0, 0, 0, 1]]


def _scale(s):
    return [[s[0], 0, 0, 0], [0, s[1], 0, 0], [0, 0, s[2], 0], [0, 0, 0, 1]]


def _euler_xyz(r):
    """FBX eEulerXYZ: R = Rz * Ry * Rx (x applied first)."""
    x, y, z = (math.radians(a) for a in r)
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    rx = [[1, 0, 0, 0], [0, cx, -sx, 0], [0, sx, cx, 0], [0, 0, 0, 1]]
    ry = [[cy, 0, sy, 0], [0, 1, 0, 0], [-sy, 0, cy, 0], [0, 0, 0, 1]]
    rz = [[cz, -sz, 0, 0], [sz, cz, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    return _mat_mul(rz, _mat_mul(ry, rx))


def _apply(m, p, w=1.0):
    return tuple(m[i][0] * p[0] + m[i][1] * p[1] + m[i][2] * p[2] + m[i][3] * w for i in range(3))


def _p70(node):
    out = {}
    p = node.find('Properties70') if node else None
    for c in (p.children if p else []):
        if c.name == 'P' and len(c.props) >= 5:
            out[c.props[0]] = c.props[4:]
    return out


# ---- conversion --------------------------------------------------------------------------------
def load_meshes(path, skip=()):
    """Return a list of triangles [(p0, p1, p2), (uv0, uv1, uv2), (n0, n1, n2)] in metres, Y-up."""
    root = read_fbx(path)
    objects = root.find('Objects')
    conns = root.find('Connections')
    geoms, models = {}, {}
    for o in objects.children:
        if o.name == 'Geometry' and len(o.props) > 2 and o.props[2] == 'Mesh':
            geoms[o.props[0]] = o
        elif o.name == 'Model':
            models[o.props[0]] = o
    parent, geom_of = {}, {}
    for c in conns.children:
        if c.props[0] != 'OO':
            continue
        child, par = c.props[1], c.props[2]
        if child in geoms and par in models:
            geom_of[par] = child
        elif child in models:
            parent[child] = par

    def local(mid):
        p = _p70(models[mid])
        t = p.get('Lcl Translation', [0, 0, 0])
        r = p.get('Lcl Rotation', [0, 0, 0])
        s = p.get('Lcl Scaling', [1, 1, 1])
        pre = p.get('PreRotation', [0, 0, 0])
        post = p.get('PostRotation', [0, 0, 0])
        m = _translate(t)
        m = _mat_mul(m, _euler_xyz(pre))
        m = _mat_mul(m, _euler_xyz(r))
        if any(post):
            # Post rotation is applied inverted (FBX: R * Rpost^-1); Synty files leave it zero.
            inv = _euler_xyz(post)
            inv = [[inv[j][i] for j in range(3)] + [0] for i in range(3)] + [[0, 0, 0, 1]]
            m = _mat_mul(m, inv)
        m = _mat_mul(m, _scale(s))
        gt = p.get('GeometricTranslation', [0, 0, 0])
        gr = p.get('GeometricRotation', [0, 0, 0])
        gs = p.get('GeometricScaling', [1, 1, 1])
        geo = _mat_mul(_translate(gt), _mat_mul(_euler_xyz(gr), _scale(gs)))
        return m, geo

    def world(mid):
        m, geo = local(mid)
        cur = parent.get(mid)
        while cur in models:
            pm, _ = local(cur)
            m = _mat_mul(pm, m)
            cur = parent.get(cur)
        return _mat_mul(m, geo)

    settings = _p70(root.find('GlobalSettings'))
    unit = settings.get('UnitScaleFactor', [1.0])[0] / 100.0  # to metres
    tris = []
    for mid, gid in sorted(geom_of.items()):
        name = models[mid].props[1].split('\x00')[0]
        if any(k in name for k in skip):
            continue
        g = geoms[gid]
        m = world(mid)
        verts = g.find('Vertices').props[0]
        pvi = g.find('PolygonVertexIndex').props[0]
        pts = [_apply(m, verts[i:i + 3]) for i in range(0, len(verts), 3)]
        pts = [(x * unit, y * unit, z * unit) for x, y, z in pts]
        uvl = g.find('LayerElementUV')
        uvs, uvidx, uvmap = None, None, None
        if uvl:
            uvs = uvl.find('UV').props[0]
            uvmap = uvl.find('MappingInformationType').props[0]
            ref = uvl.find('ReferenceInformationType').props[0]
            uvidx = uvl.find('UVIndex').props[0] if ref == 'IndexToDirect' else None
        poly, corner = [], 0
        for raw in pvi:
            end = raw < 0
            vi = ~raw if end else raw
            if uvs is not None:
                if uvmap == 'ByPolygonVertex':
                    k = uvidx[corner] if uvidx is not None else corner
                else:
                    k = uvidx[vi] if uvidx is not None else vi
                uv = (uvs[2 * k], uvs[2 * k + 1])
            else:
                uv = (0.0, 0.0)
            poly.append((pts[vi], uv))
            corner += 1
            if end:
                for i in range(1, len(poly) - 1):
                    tris.append((poly[0], poly[i], poly[i + 1]))
                poly = []
    return tris


def _sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def convert(src, dst_obj, mtl_name, note, size=None, axis='y', skip=(), rotate_x=0.0, yaw=0.0):
    """Write dst_obj (and returns its bounds). size: the target extent in metres along axis
    ('y' height or 'max' the longest side), uniform scale; pivot is the floor centre."""
    tris = load_meshes(src, skip)
    if rotate_x or yaw:
        rx = _euler_xyz((rotate_x, yaw, 0))
        tris = [tuple((_apply(rx, p), uv) for p, uv in t) for t in tris]
    xs = [p[0] for t in tris for p, _ in t]
    ys = [p[1] for t in tris for p, _ in t]
    zs = [p[2] for t in tris for p, _ in t]
    lo, hi = (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))
    ext = [hi[i] - lo[i] for i in range(3)]
    k = 1.0
    if size:
        k = size / (ext[1] if axis == 'y' else max(ext))
    cx, cz = (lo[0] + hi[0]) / 2, (lo[2] + hi[2]) / 2
    coords, uvs, normals, faces = {}, {}, {}, []
    for t in tris:
        p = [((q[0] - cx) * k, (q[1] - lo[1]) * k, (q[2] - cz) * k) for q, _ in t]
        n = _cross(_sub(p[1], p[0]), _sub(p[2], p[0]))
        ln = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
        if ln < 1e-12:
            continue
        n = tuple(round(v / ln, 5) for v in n)
        ni = normals.setdefault(n, len(normals) + 1)
        idx = []
        for q, (_, uv) in zip(p, t):
            qi = coords.setdefault(tuple(round(v, 5) for v in q), len(coords) + 1)
            ti = uvs.setdefault((round(uv[0], 6), round(uv[1], 6)), len(uvs) + 1)
            idx.append(f'{qi}/{ti}/{ni}')
        faces.append('f ' + ' '.join(idx))
    lines = ['# ' + note, f'mtllib {mtl_name}.mtl', 'o ' + mtl_name, 's off']
    lines += ['v %g %g %g' % p for p in coords]
    lines += ['vt %g %g' % t for t in uvs]
    lines += ['vn %g %g %g' % n for n in normals]
    lines += [f'usemtl {mtl_name}'] + faces
    content = '\n'.join(lines) + '\n'
    old = None
    try:
        old = open(dst_obj, 'rb').read()
    except OSError:
        pass
    if old != content.encode():
        with open(dst_obj, 'w', newline='\n') as f:
            f.write(content)
    return [e * k for e in ext]
