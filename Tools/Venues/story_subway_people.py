"""The named people on the Bellwoods platform: the mustard-scarf commuter, the two kids and their mum.

Each is built from the game's crowd figure pieces (Assets/Models/People/Crowd/<Body>/, the owner's
Synty Town characters cut by Game/Tools/MakeCrowdPieces.py), copied into the venue's Models folder
with an .mtl that binds the character's own clothes atlas (Design/Story-Mode-Setlists.json,
Characters). Arms that hold something or clap are re-bent at the elbow here. Loops are Sequence
clips in Assets/Venues/StorySubway/Motion/.
"""
import json
import math
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
VENUE = os.path.join(ROOT, "Assets", "Venues", "StorySubway")
MODELS = os.path.join(VENUE, "Models")
MOTION = os.path.join(VENUE, "Motion")
LOCAL = "Assets/Venues/StorySubway/Models/"
CROWD = os.path.join(ROOT, "Assets", "Models", "People", "Crowd")
PIECES = ("Legs", "Torso", "Head", "ArmL", "ArmR")
JOINTS = ("Spine", "Head", "Left", "Right")

# name: (seconds, (left elbow bend, right elbow bend), keys of (t, spine, head, armL, armR) in Euler degrees)
POSES = {
    # Two stomps and a clap, felt in the shoulders; the mug stays level in the right hand.
    "MugBob": (1.48, (0, 96), [
        (0.00, (4, 0, 0), (8, -6, 0), (-4, 0, -5), (-16, -6, 4)),
        (0.17, (-1, 2, 0), (-3, -4, 0), (-2, 0, -4), (-12, -6, 4)),
        (0.33, (4, 0, 0), (8, -6, 0), (-4, 0, -5), (-16, -6, 4)),
        (0.50, (-1, -2, 0), (-3, -8, 0), (-2, 0, -4), (-12, -6, 4)),
        (0.67, (3, 0, 1), (6, -10, 2), (-6, 0, -6), (-18, -6, 4)),
        (0.84, (-2, 2, 0), (-4, -5, 0), (-2, 0, -4), (-12, -6, 4))]),
    # Both hands up on the hook, pumping.
    "HandsUp": (0.92, (0, 0), [
        (0.00, (-4, 0, 0), (-12, 0, 0), (-168, 0, 14), (-168, 0, -14)),
        (0.50, (2, 0, 0), (-4, 0, 0), (-140, 0, 26), (-140, 0, -26))]),
    "HandsUpLate": (0.92, (0, 0), [
        (0.00, (2, 3, 0), (-4, 6, 0), (-146, 0, 24), (-150, 0, -22)),
        (0.50, (-5, -3, 0), (-14, -4, 0), (-170, 0, 12), (-172, 0, -12))]),
    # Clapping on two and four.
    "Clap": (0.84, (64, 64), [
        (0.00, (2, 0, 0), (4, 0, 0), (-38, 30, 0), (-38, -30, 0)),
        (0.25, (-1, 0, 0), (-2, 0, 0), (-44, 9, 0), (-44, -9, 0)),
        (0.50, (2, 0, 0), (4, 0, 0), (-38, 30, 0), (-38, -30, 0)),
        (0.75, (-1, 0, 0), (-2, 0, 0), (-44, 9, 0), (-44, -9, 0))]),
    # Arms folded on the stairs, keeping half an eye on the kids.
    "Watch": (5.0, (104, 104), [
        (0.00, (2, 0, 0), (6, 8, 0), (-14, 24, 0), (-18, -22, 0)),
        (0.50, (1, -4, 0), (2, -10, 0), (-14, 24, 0), (-18, -22, 0))]),
}


def quat(rot):
    x, y, z = [math.radians(a) / 2 for a in rot]
    a, b = math.sin(x), math.cos(x)
    c, d = math.sin(y), math.cos(y)
    e, f = math.sin(z), math.cos(z)
    return [round(v, 7) for v in (a * d * f - b * c * e, b * c * f + a * d * e, b * d * e - a * c * f, b * d * f + a * c * e)]


def save(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = text.encode()
    if os.path.exists(path) and open(path, "rb").read() == data:
        return
    with open(path, "wb") as f:
        f.write(data)
    twin = path + ".assbin"
    if os.path.exists(twin):
        os.remove(twin)


def clips():
    for name, (seconds, _, keys) in POSES.items():
        end = max(2, round(seconds * 30))
        tracks = []
        for i, joint in enumerate(JOINTS, 1):
            ks = [{"Frame": round(k[0] * end), "Value": quat(k[i]), "Interpolation": "SmoothStep"} for k in keys]
            ks.append(dict(ks[0], Frame=end))
            tracks.append({"Binding": joint, "Component": "Transform", "Property": "Rotation", "Keys": ks})
        clip = {"Version": 1, "Name": name, "FrameRate": 30, "DurationFrames": end, "Tracks": tracks}
        save(os.path.join(MOTION, name + ".sequence"), json.dumps(clip, indent=1) + "\n")


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(v):
    n = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    return (0.0, 1.0, 0.0) if n < 1e-9 else (v[0] / n, v[1] / n, v[2] / n)


def piece(body, clothes, part, bend=0):
    """Copies one crowd piece with the clothes atlas; bend > 0 folds the forearm forward at the elbow."""
    tag = f"{body}_{clothes}"
    name = f"{tag}_{part}" + (f"_{bend}" if bend else "")
    save(os.path.join(MODELS, tag + ".mtl"),
         f"newmtl Crowd\nKd 1 1 1\nKs 0 0 0\nmap_Kd ../../../Models/Venue/PolygonTown_{clothes}.png\n")
    src = os.path.join(CROWD, body, part + ".obj")
    lines = open(src).read().splitlines()
    if not bend:
        body_lines = [ln for ln in lines if ln.startswith(("v ", "vn ", "vt ", "f ", "s "))]
        text = [f"# Copied from Assets/Models/People/Crowd/{body}/{part}.obj with the PolygonTown_{clothes} atlas.",
                f"mtllib {tag}.mtl", f"o {name}", "usemtl Crowd"] + body_lines
        save(os.path.join(MODELS, name + ".obj"), "\n".join(text) + "\n")
        return LOCAL + name + ".obj"
    elbow = -0.323
    ang = math.radians(bend)

    def smooth(v):
        v = max(0.0, min(1.0, v))
        return v * v * (3 - 2 * v)

    verts, uv, faces = [], [], []
    for ln in lines:
        if ln.startswith("v "):
            x, y, nz = map(float, ln.split()[1:])
            z = -nz
            w = smooth((-0.23 - y) / 0.17)
            ty = y * (1 - w) + (elbow + (y - elbow) * math.cos(ang) + z * math.sin(ang)) * w
            tz = z * (1 - w) + (-(y - elbow) * math.sin(ang) + z * math.cos(ang)) * w
            verts.append((x, ty, -tz))
        elif ln.startswith("vt "):
            uv.append(ln)
        elif ln.startswith("f "):
            faces.append([tuple(map(int, c.split("/"))) for c in ln.split()[1:]])
    out = [f"# Copied from Assets/Models/People/Crowd/{body}/{part}.obj with the PolygonTown_{clothes} atlas, elbow bent {bend} deg.",
           f"mtllib {tag}.mtl", f"o {name}", "s off", "usemtl Crowd"]
    out += ["v %.5f %.5f %.5f" % p for p in verts] + uv
    for i, face in enumerate(faces, 1):
        a, b, c = [verts[f[0] - 1] for f in face]
        n = _unit(_cross(_sub(b, a), _sub(c, a)))
        out += ["vn %.5f %.5f %.5f" % n, "f " + " ".join(f"{v}/{t}/{i}" for v, t, _ in face)]
    save(os.path.join(MODELS, name + ".obj"), "\n".join(out) + "\n")
    return LOCAL + name + ".obj"


def person(s, parent, label, body, clothes, role, pos, yaw, scale=1.0, speed=1.0, held=None, scarf=None):
    """A posed, looping figure. held: 'mug' (steel travel mug in the right hand). scarf: an RGB."""
    _, bends, keys = POSES[role]
    r = keys[0]
    root = s.entity(label, parent, pos, (0, yaw, 0), (scale,) * 3)

    def part(name, where, anchor, rot=(0, 0, 0), bend=0):
        n = s.entity(name, anchor, where, rot)
        n.add({"Type": "Model", "ModelPath": piece(body, clothes, name, bend)})
        return n

    part("Legs", (0, 0, 0), root)
    spine = part("Torso", (0, 0.8763, 0), root, r[1])
    head = part("Head", (0, 0.5727, -0.0242), spine, r[2])
    limbs = [spine, head]
    for i, (name, side) in enumerate((("ArmL", -1), ("ArmR", 1))):
        arm = part(name, (side * 0.191, 0.5141, -0.0484), spine, r[3 + i], bends[i])
        limbs.append(arm)
        if held == "mug" and i == 1:
            a = math.radians(bends[i])
            palm = (0, -0.323 - 0.33 * math.cos(a), 0.33 * math.sin(a))
            hand = s.entity("Steel travel mug", arm, palm, (-r[4][0], 0, 0))
            s.box("Mug body", hand, (0, 0.04, 0.02), (0.08, 0.17, 0.08), (0.78, 0.8, 0.84), rough=0.22, metallic=0.9,
                  shape="Cylinder")
            s.box("Mug lid", hand, (0, 0.135, 0.02), (0.084, 0.025, 0.084), (0.06, 0.06, 0.07), rough=0.5, shape="Cylinder")
    if scarf:
        wrap = s.entity("Mustard scarf", spine, (0, 0.5, -0.02))
        s.box("Scarf wrap", wrap, (0, 0, 0), (0.29, 0.1, 0.27), scarf, rough=0.95, shape="Cylinder")
        s.box("Scarf knot", wrap, (0.05, -0.02, 0.12), (0.1, 0.09, 0.07), scarf, rough=0.95)
        s.box("Scarf tail", wrap, (0.07, -0.2, 0.13), (0.085, 0.32, 0.03), scarf, rot=(-6, 0, 4), rough=0.95)
        s.box("Scarf fringe", wrap, (0.08, -0.37, 0.135), (0.085, 0.03, 0.025), [c * 0.7 for c in scarf], rough=0.95)
    root.add({"Type": "Sequence", "Clip": f"Assets/Venues/StorySubway/Motion/{role}.sequence", "PlayOnStart": True,
              "Loop": True, "Speed": speed, "Bindings": [{"Slot": j, "Target": p.guid} for j, p in zip(JOINTS, limbs)]})
    return root
