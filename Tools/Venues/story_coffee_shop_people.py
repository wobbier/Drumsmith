"""The café's regulars: rigid crowd pieces (Assets/Models/People/Crowd/<who>/*.obj) re-skinned, bent to sit,
posed, and given small looping motions. Writes into Assets/Venues/StoryCoffeeShop/Models/People and
.../Motion only; the crowd pieces are read, never changed.

A figure at yaw 0 faces +z (toward the band from the crowd side); its left arm is on -x. On an arm,
negative X rotation lifts it forward and +Z swings the left arm in (the right arm out); on the spine
or head, positive X leans or looks down.
"""
import json
import math
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
VENUE = "Assets/Venues/StoryCoffeeShop"
PEOPLE_DIR = os.path.join(ROOT, VENUE, "Models", "People")
MOTION_DIR = os.path.join(ROOT, VENUE, "Motion")
CROWD = os.path.join(ROOT, "Assets", "Models", "People", "Crowd")

HIP_STAND, HIP_SEAT = 0.8763, 0.57
JOINTS = ("Spine", "Head", "Left", "Right")


def _save(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = text.encode()
    if os.path.exists(path) and open(path, "rb").read() == data:
        return
    with open(path, "wb") as f:
        f.write(data)
    twin = path + ".assbin"
    if os.path.exists(twin):
        os.remove(twin)


def _skin_mtl(skin):
    name = f"Skin_{skin}"
    _save(os.path.join(PEOPLE_DIR, name + ".mtl"),
          f"newmtl {name}\nKd 1 1 1\nKs 0 0 0\nNs 0\nillum 1\nmap_Kd ../../../../Models/Venue/PolygonTown_{skin}.png\n")
    return name


def _smooth(v):
    v = max(0.0, min(1.0, v))
    return v * v * (3 - 2 * v)


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def piece(who, part, skin="01_A", bend=0):
    """A crowd piece in this skin; Legs with bend > 0 sit (thighs forward), an arm with bend > 0
    folds its forearm forward by that many degrees. Returns the project path."""
    mtl = _skin_mtl(skin)
    name = f"{who}_{part}_{bend}_{skin}"
    path = os.path.join(PEOPLE_DIR, name + ".obj")
    src = os.path.join(CROWD, who, part + ".obj")
    verts, uvs, faces = [], [], []
    elbow, hip, knee = -0.323, 0.8763, 0.46
    for line in open(src):
        if line.startswith("v "):
            x, y, nz = map(float, line.split()[1:4])
            z = -nz
            ty, tz = y, z
            if bend and part == "Legs":
                ang = math.radians(bend)
                y1 = 0.57 + (y - hip) * math.cos(ang) + z * math.sin(ang)
                z1 = -(y - hip) * math.sin(ang) + z * math.cos(ang)
                w = _smooth((y - 0.37) / 0.19)
                ty = (0.49 + y - knee) * (1 - w) + y1 * w
                tz = (0.405 + z) * (1 - w) + z1 * w
                w = _smooth((y - 0.81) / 0.10)
                ty = ty * (1 - w) + (y - hip + 0.57) * w
                tz = tz * (1 - w) + z * w
            elif bend:
                ang = math.radians(bend)
                w = _smooth((-0.23 - y) / 0.17)
                ty = y * (1 - w) + (elbow + (y - elbow) * math.cos(ang) + z * math.sin(ang)) * w
                tz = z * (1 - w) + (-(y - elbow) * math.sin(ang) + z * math.cos(ang)) * w
            verts.append((x, ty, -tz))
        elif line.startswith("vt "):
            uvs.append(line.strip())
        elif line.startswith("f "):
            faces.append([tuple(int(i) for i in c.split("/")) for c in line.split()[1:]])
    lines = [f"# Posed from Assets/Models/People/Crowd/{who}/{part}.obj (bend {bend}) for the coffee shop",
             f"mtllib {mtl}.mtl", "o " + name, "s off", f"usemtl {mtl}"]
    lines += ["v %.5f %.5f %.5f" % v for v in verts] + uvs
    for i, face in enumerate(faces, 1):
        a, b, c = (verts[f[0] - 1] for f in face[:3])
        n = _cross(_sub(b, a), _sub(c, a))
        ln = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
        n = (n[0] / ln, n[1] / ln, n[2] / ln) if ln > 1e-12 else (0.0, 1.0, 0.0)
        lines.append("vn %.5f %.5f %.5f" % n)
        lines.append("f " + " ".join(f"{v}/{t}/{i}" for v, t, _ in face))
    _save(path, "\n".join(lines) + "\n")
    return f"{VENUE}/Models/People/{name}.obj"


# ---- motions -------------------------------------------------------------------------------------

def quat(rot):
    x, y, z = [math.radians(a) / 2 for a in rot]
    a, b = math.sin(x), math.cos(x)
    c, d = math.sin(y), math.cos(y)
    e, f = math.sin(z), math.cos(z)
    return [round(v, 7) for v in (a * d * f - b * c * e, b * c * f + a * d * e, b * d * e - a * c * f, b * d * f + a * c * e)]


# name: (seconds, [(t, spine, head, left arm, right arm), ...]); the first key is the rest pose and
# the clip loops back to it.
CLIPS = {
    # Knees and shoulders going together, the Stolen Dance lilt.
    "SeatSway": (2.2, [
        (0.00, (4, 0, 5), (0, 4, -4), (-26, 0, -6), (-24, 0, 6)),
        (0.25, (5, 3, 0), (3, 0, 0), (-28, 0, -4), (-26, 0, 4)),
        (0.50, (4, 0, -5), (0, -4, 4), (-24, 0, -6), (-28, 0, 6)),
        (0.75, (5, -3, 0), (3, 0, 0), (-26, 0, -4), (-26, 0, 4))]),
    # Elbows on the table, head tipping to the music.
    "SeatListen": (5.6, [
        (0.00, (8, 0, 0), (6, 6, -3), (-34, 0, 2), (-30, 0, -2)),
        (0.30, (9, -4, 1), (2, -6, 4), (-36, 0, 2), (-31, 0, -2)),
        (0.62, (7, 3, -1), (8, 8, -5), (-33, 0, 1), (-32, 0, -1))]),
    # Hands on the keyboard, glancing up over the screen.
    "SeatLaptop": (4.4, [
        (0.00, (10, 0, 0), (16, 0, 0), (-30, 0, 8), (-30, 0, -8)),
        (0.40, (10, 0, 0), (14, 0, 0), (-31, 0, 9), (-28, 0, -7)),
        (0.60, (6, 4, 0), (-4, 10, 0), (-30, 0, 8), (-30, 0, -8)),
        (0.85, (8, 0, 0), (8, 0, 0), (-29, 0, 8), (-31, 0, -9))]),
    # Elbows on the table, the cup up and down.
    "SeatSip": (6.0, [
        (0.00, (6, 0, 0), (4, 0, 0), (-34, 0, 4), (-36, 0, -4)),
        (0.35, (4, 0, 0), (-6, 0, 0), (-34, 0, 4), (-72, 0, -10)),
        (0.55, (4, 0, 0), (-6, 0, 0), (-34, 0, 4), (-72, 0, -10)),
        (0.75, (6, 0, 0), (4, 4, 0), (-34, 0, 4), (-36, 0, -4))]),
    # Steaming milk: the jug arm jiggles under the wand, eyes on the jug.
    "Steam": (0.9, [
        (0.00, (8, 0, 0), (22, -10, 0), (-46, 0, 16), (-40, 0, -6)),
        (0.50, (8, 0, 0), (22, -10, 0), (-50, 0, 14), (-44, 0, -8))]),
    # Clapping over the counter.
    "Clap": (0.5, [
        (0.00, (-2, 0, 0), (-6, 0, 0), (-74, 0, -12), (-74, 0, 12)),
        (0.50, (-2, 0, 0), (-6, 0, 0), (-72, 0, 14), (-72, 0, -14))]),
    # Strumming the opener on a stool.
    "Strum": (0.52, [
        (0.00, (8, 0, 0), (18, -14, 0), (-56, 0, 22), (-30, 0, -26)),
        (0.50, (8, 0, 0), (18, -14, 0), (-56, 0, 22), (-38, 0, -16))]),
}


def clips():
    for name, (seconds, keys) in CLIPS.items():
        end = round(seconds * 30)
        tracks = []
        for i, joint in enumerate(JOINTS, 1):
            ks = [{"Frame": round(k[0] * end), "Value": quat(k[i]), "Interpolation": "SmoothStep"} for k in keys]
            ks.append(dict(ks[0], Frame=end))
            tracks.append({"Binding": joint, "Component": "Transform", "Property": "Rotation", "Keys": ks})
        clip = {"Version": 1, "Name": name, "FrameRate": 30, "DurationFrames": end, "Tracks": tracks}
        _save(os.path.join(MOTION_DIR, name + ".sequence"), json.dumps(clip, indent=1) + "\n")


# ---- placing a person ----------------------------------------------------------------------------

BENDS = {"SeatSway": (72, 72), "SeatListen": (96, 96), "SeatLaptop": (78, 78), "SeatSip": (96, 118),
         "Steam": (70, 82), "Clap": (88, 88), "Strum": (70, 96)}
SEATED = {"SeatSway", "SeatListen", "SeatLaptop", "SeatSip", "Strum"}


def person(s, parent, label, who, skin, pos, yaw, clip, speed=1.0, phase_scale=1.0, held=None, still=False):
    """One regular. clip names the pose (and the motion unless still). held: 'cup' | 'jug' | None, in
    the right hand. Returns the root entity."""
    seated = clip in SEATED
    bl, br = BENDS[clip]
    rest = CLIPS[clip][1][0]
    root = s.entity(label, parent, pos, (0, yaw, 0), (phase_scale,) * 3)

    def part(name, at, anchor, rot, path):
        e = s.entity(name, anchor, at, rot)
        e.add({"Type": "Model", "ModelPath": path})
        return e

    part("Legs", (0, 0, 0), root, (0, 0, 0), piece(who, "Legs", skin, 79 if seated else 0))
    spine = part("Torso", (0, HIP_SEAT if seated else HIP_STAND, 0), root, rest[1], piece(who, "Torso", skin))
    head = part("Head", (0, 0.5727, -0.0242), spine, rest[2], piece(who, "Head", skin))
    limbs = [spine, head]
    for i, (side, sx) in enumerate((("ArmL", -1), ("ArmR", 1))):
        bend = (bl, br)[i]
        arm = part(side, (sx * 0.191, 0.5141, -0.0484), spine, rest[3 + i], piece(who, side, skin, bend))
        limbs.append(arm)
        if held and i == 1:
            a = math.radians(bend)
            palm = (0, -0.323 - 0.33 * math.cos(a), 0.33 * math.sin(a))
            hand = s.entity("In hand", arm, palm, (90 - bend, 0, 0))
            if held == "cup":
                s.prop("Cup", hand, f"{VENUE}/Models/CafeCup.fbx", (0, -0.02, 0.02), 0, 0.7)
            elif held == "jug":
                s.box("Milk jug", hand, (0, -0.04, 0.03), (0.08, 0.12, 0.08), (0.8, 0.8, 0.82), metallic=0.9, rough=0.25,
                      shape="Cylinder")
    if not still:
        root.add({"Type": "Sequence", "Clip": f"{VENUE}/Motion/{clip}.sequence", "PlayOnStart": True, "Loop": True,
                  "Speed": speed, "Bindings": [{"Slot": j, "Target": p.guid} for j, p in zip(JOINTS, limbs)]})
    return root
