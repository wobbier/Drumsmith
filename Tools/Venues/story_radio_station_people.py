"""The volunteers of the StoryRadioStation venue: jointed crowd figures (the Backyard's method:
legs, torso, head and two arms from Assets/Models/People/Crowd/<person>/, with the Backyard's bent
arm and seated leg pieces referenced read-only) and the looping Sequence clips that move them.

A figure faces local +Z as built; yaw 180 turns it to look at the glass and the band (-z).
"""
import json
import math
import os

CROWD = "Assets/Models/People/Crowd/"
BENT = "Assets/Venues/Backyard/Models/"
MOTION = "Assets/Venues/StoryRadioStation/Motion/"
JOINTS = ("Body", "Spine", "Head", "Left", "Right")

# Bent pieces that exist in the Backyard folder.
BENDS = {
    "Son_01": {"ArmL": (67,), "ArmR": (61, 93), "Legs": (79,)},
    "Mother_02": {"ArmL": (66,), "ArmR": (38, 93), "Legs": (79,)},
    "Daughter_01": {"ArmL": (62, 73), "ArmR": (76,), "Legs": (79,)},
    "Mother_01": {"ArmL": (40, 66), "ArmR": (38, 74)},
    "ShopKeeper_01": {"ArmL": (66, 73), "ArmR": (38, 76)},
    "Rigged": {"ArmL": (40,), "ArmR": (74,)},
}


def quat(rot):
    x, y, z = [math.radians(a) / 2 for a in rot]
    a, b = math.sin(x), math.cos(x)
    c, d = math.sin(y), math.cos(y)
    e, f = math.sin(z), math.cos(z)
    return [round(v, 7) for v in (a * d * f - b * c * e, b * c * f + a * d * e, b * d * e - a * c * f, b * d * f + a * c * e)]


# name: (seconds, [(t, body_offset_y, spine, head, left, right), ...])
CLIPS = {
    # On the phone: a slow nod, the free hand tapping the desk.
    "OnThePhone": (3.2, [
        (0.00, 0.0, (4, 0, 0), (-6, 8, 4), (-38, 6, -4), (-72, -28, 14)),
        (0.30, 0.0, (6, -4, 1), (2, 12, 6), (-44, 6, -4), (-74, -30, 15)),
        (0.55, 0.0, (3, 2, 0), (-8, 4, 2), (-36, 4, -6), (-70, -26, 13)),
        (0.80, 0.0, (5, -2, 0), (0, 14, 5), (-42, 8, -4), (-73, -29, 14))]),
    # Writing a pledge slip, head down.
    "Writing": (2.6, [
        (0.00, 0.0, (10, 0, 0), (18, -4, 0), (-46, 10, -6), (-50, -8, 6)),
        (0.35, 0.0, (12, 3, 0), (22, 4, 0), (-46, 10, -6), (-54, -14, 8)),
        (0.70, 0.0, (10, -2, 0), (16, -6, 0), (-46, 10, -6), (-48, -4, 4))]),
    # On their feet, bouncing to the bassline.
    "Bounce": (0.64, [
        (0.00, 0.00, (0, 0, -2), (-4, 0, -3), (-6, 0, -12), (-6, 0, 12)),
        (0.50, -0.07, (6, 0, 2), (10, 0, 3), (-24, 0, -16), (-24, 0, 16))]),
    # RENT PAID: jumping with both arms up.
    "Jump": (0.62, [
        (0.00, 0.00, (4, 0, 0), (6, 0, 0), (-160, 0, -18), (-160, 0, 18)),
        (0.45, 0.30, (-6, 0, 0), (-14, 0, 0), (-175, 0, -28), (-175, 0, 28)),
        (0.75, 0.10, (0, 0, 0), (-4, 0, 0), (-168, 0, -22), (-168, 0, 22))]),
    # The engineer at the desk, riding the faders and nodding along.
    "Faders": (1.28, [
        (0.00, 0.0, (14, 0, 0), (6, 0, 0), (-52, 6, -6), (-50, -6, 6)),
        (0.25, 0.0, (17, 2, 0), (16, 0, 0), (-56, 6, -6), (-48, -6, 6)),
        (0.50, 0.0, (14, 0, 0), (6, 0, 0), (-52, 4, -6), (-54, -8, 6)),
        (0.75, 0.0, (17, -2, 0), (16, 0, 0), (-50, 6, -6), (-50, -6, 6))]),
}


def write_clips(root):
    folder = os.path.join(root, MOTION)
    os.makedirs(folder, exist_ok=True)
    for name, (seconds, poses) in CLIPS.items():
        end = round(seconds * 30)
        tracks = [{"Binding": "Body", "Component": "Transform", "Property": "Position",
                   "Keys": [{"Frame": round(p[0] * end), "Value": [0.0, p[1], 0.0, 0.0], "Interpolation": "SmoothStep"} for p in poses]}]
        for i, joint in enumerate(JOINTS[1:], 2):
            tracks.append({"Binding": joint, "Component": "Transform", "Property": "Rotation",
                           "Keys": [{"Frame": round(p[0] * end), "Value": quat(p[i]), "Interpolation": "SmoothStep"} for p in poses]})
        for t in tracks:
            t["Keys"].append(dict(t["Keys"][0], Frame=end))
        clip = {"Version": 1, "Name": name, "FrameRate": 30, "DurationFrames": end, "Tracks": tracks}
        with open(os.path.join(folder, name + ".sequence"), "w", newline="\n") as f:
            json.dump(clip, f, indent=1)
            f.write("\n")


def _part(person, part, bend=None):
    if bend:
        assert bend in BENDS[person][part], (person, part, bend)
        return f"{BENT}{person}_{part}_{bend}.obj"
    return f"{CROWD}{person}/{part}.obj"


def person(s, parent, label, who, pos, yaw=180.0, clip="Bounce", seated=False, arm_l=None, arm_r=None,
           speed=1.0, scale=1.0, handset=False, sheet=None):
    """A figure: pos is the feet (seated: the floor under the chair). clip names a CLIPS entry; its
    first pose is also the authored rest pose. handset: a phone receiver at the right ear.
    sheet: a texture path for a pledge slip in the left hand."""
    seconds, poses = CLIPS[clip]
    p0 = poses[0]
    root = s.entity(label, parent, pos, (0, yaw, 0), (scale,) * 3)
    body = s.entity("Body", root, (0, 0, 0))

    def piece(name, at, anchor, rot=(0, 0, 0), path=None):
        n = s.entity(name, anchor, at, rot)
        n.add({"Type": "Model", "ModelPath": path})
        return n

    piece("Legs", (0, 0, 0), body, path=_part(who, "Legs", 79 if seated else None))
    spine = piece("Torso", (0, 0.57 if seated else 0.8763, 0), body, p0[2], _part(who, "Torso"))
    head = piece("Head", (0, 0.5727, -0.0242), spine, p0[3], _part(who, "Head"))
    left = piece("ArmL", (-0.191, 0.5141, -0.0484), spine, p0[4], _part(who, "ArmL", arm_l))
    right = piece("ArmR", (0.191, 0.5141, -0.0484), spine, p0[5], _part(who, "ArmR", arm_r))
    if handset:
        s.box("Handset", head, (0.11, 0.07, 0.03), (0.05, 0.06, 0.2), (0.09, 0.09, 0.1), rot=(70, 0, 0), rough=0.5)
    if sheet:
        hand = s.entity("Slip in hand", left, (0, -0.55, 0.12), (60, 0, 0))
        e = s.box("Slip", hand, (0, 0, 0), (0.2, 0.26, 0.004), (1, 1, 1), shadows=False)
        mat = e.components[-1]["Material"]
        mat["Textures"] = {"Diffuse": {"Path": sheet}}
        mat["Tiling"] = [1.0, -1.0]
        mat["Offset"] = [0.0, 1.0]
    root.add({"Type": "Sequence", "Clip": MOTION + clip + ".sequence", "PlayOnStart": True, "Loop": True, "Speed": speed,
              "Bindings": [{"Slot": j, "Target": p.guid} for j, p in zip(JOINTS, (body, spine, head, left, right))]})
    return root
