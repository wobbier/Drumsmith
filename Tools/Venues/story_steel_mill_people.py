"""The Steel Mill Tour's people off the stage: the acts who stay in the wing, the singers who come
out at the end, the crew chief. Rigid figures from the crowd's low pieces
(Assets/Models/People/Crowd/<Body>/*_Lo.obj), re-skinned with each character's manifest atlas
(the pieces are copied next to the venue with their own .mtl), and a few small looping
Sequences so nobody stands like a statue.
"""
import json
import math
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
VENUE = os.path.join(ROOT, "Assets", "Venues", "StorySteelMill")
REL = "Assets/Venues/StorySteelMill/"
PIECES = ("Legs", "Torso", "Head", "ArmL", "ArmR")
JOINTS = ("Spine", "Head", "Left", "Right")


def save(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path) and open(path, encoding="utf-8").read() == text:
        return
    with open(path, "w", newline="\n", encoding="utf-8") as f:
        f.write(text)


def skin(body, atlas):
    """Copy the body's low pieces next to the venue, bound to PolygonTown_<atlas>.png."""
    folder = f"Models/People/{body}_{atlas}"
    save(os.path.join(VENUE, folder, "Crowd.mtl"),
         f"newmtl Crowd\nKd 1 1 1\nKs 0 0 0\nmap_Kd ../../../../../Models/Venue/PolygonTown_{atlas}.png\n")
    for piece in PIECES:
        src = os.path.join(ROOT, "Assets", "Models", "People", "Crowd", body, piece + "_Lo.obj")
        lines = open(src, encoding="utf-8").read().splitlines()
        lines[0] = f"# Copied from Assets/Models/People/Crowd/{body}/{piece}_Lo.obj; skin PolygonTown_{atlas}."
        save(os.path.join(VENUE, folder, piece + ".obj"), "\n".join(lines) + "\n")
    return REL + folder + "/"


def quat(rot):
    x, y, z = [math.radians(a) / 2 for a in rot]
    a, b = math.sin(x), math.cos(x)
    c, d = math.sin(y), math.cos(y)
    e, f = math.sin(z), math.cos(z)
    return [round(v, 7) for v in (a * d * f - b * c * e, b * c * f + a * d * e, b * d * e - a * c * f, b * d * f + a * c * e)]


# name: (seconds, [(t, spine, head, armL, armR)]) Euler degrees, the pose loops back to the first key.
POSES = {
    # Watching from the wing: weight shifts, a nod on the beat of something heavy.
    "WingNod": (2.0, [(0, (2, 0, 0), (4, 0, 0), (-4, 0, -9), (-4, 0, 9)),
                      (.25, (5, 0, 1), (18, 0, 0), (-6, 0, -9), (-6, 0, 9)),
                      (.5, (2, 0, 0), (2, 0, 0), (-4, 0, -9), (-4, 0, 9)),
                      (.75, (5, 0, -1), (18, 0, 0), (-6, 0, -9), (-6, 0, 9))]),
    # Arms folded-ish, a slow sway.
    "WingSway": (4.2, [(0, (0, -4, 2), (2, -10, 0), (-55, 30, -12), (-55, -30, 12)),
                       (.5, (0, 4, -2), (2, 12, 0), (-57, 30, -12), (-57, -30, 12))]),
    # Horns up, pumping, for the singers at the end.
    "HornsUp": (1.0, [(0, (-4, 0, 0), (-8, 0, 0), (-150, 0, -22), (-40, 0, 12)),
                      (.5, (4, 0, 0), (12, 0, 0), (-165, 0, -18), (-48, 0, 12))]),
    # Both arms up and waving to the back rows.
    "Wave": (1.6, [(0, (0, 0, 2), (-6, 0, 0), (-160, 0, -28), (-160, 0, 28)),
                   (.5, (0, 0, -2), (-6, 0, 0), (-160, 0, -14), (-160, 0, 40))]),
    # Crew chief: one hand on the hip, the other pointing at the case.
    "Point": (3.0, [(0, (0, 0, 0), (6, -14, 0), (-20, 0, -40), (-80, -20, 4)),
                    (.5, (0, 0, 0), (6, -4, 0), (-20, 0, -40), (-86, -16, 4))]),
}


def clips():
    for name, (seconds, poses) in POSES.items():
        end = round(seconds * 30)
        tracks = []
        for i, joint in enumerate(JOINTS, 1):
            keys = [{"Frame": round(t[0] * end), "Value": quat(t[i]), "Interpolation": "SmoothStep"} for t in poses]
            keys.append(dict(keys[0], Frame=end))
            tracks.append({"Binding": joint, "Component": "Transform", "Property": "Rotation", "Keys": keys})
        clip = {"Version": 1, "Name": name, "FrameRate": 30, "DurationFrames": end, "Tracks": tracks}
        save(os.path.join(VENUE, "Motion", name + ".sequence"), json.dumps(clip, indent=1) + "\n")


def figure(s, parent, label, body, atlas, pos, yaw, pose="WingNod", speed=1.0, towel=None, scale=1.0):
    """A standing person. yaw 0 faces +z (the back wall); 180 faces the crowd; 90 faces +x."""
    path = skin(body, atlas)
    root = s.entity(label, parent, pos, (0, yaw, 0), (scale,) * 3)
    first = POSES[pose][1][0]

    def piece(name, where, anchor, rot=(0, 0, 0)):
        n = s.entity(name, anchor, where, rot)
        n.add({"Type": "Model", "ModelPath": path + name + ".obj"})
        return n

    piece("Legs", (0, 0, 0), root)
    spine = piece("Torso", (0, .8763, 0), root, first[1])
    head = piece("Head", (0, .5727, -.0242), spine, first[2])
    arms = [piece(part, (side * .191, .5141, -.0484), spine, first[3 + i])
            for i, (part, side) in enumerate((("ArmL", -1), ("ArmR", 1)))]
    if towel:
        # A towel round the neck: a band over the shoulders and two ends down the chest.
        s.box("Towel", spine, (0, .55, -.01), (.40, .07, .30), towel, rough=1.0)
        for side in (-1, 1):
            s.box("Towel end", spine, (side * .10, .36, .135), (.11, .36, .05), towel, rot=(-6, 0, 0), rough=1.0)
    root.add({"Type": "Sequence", "Clip": REL + "Motion/" + pose + ".sequence", "PlayOnStart": True, "Loop": True,
              "Speed": speed, "Bindings": [{"Slot": j, "Target": p.guid} for j, p in zip(JOINTS, [spine, head, *arms])]})
    return root
