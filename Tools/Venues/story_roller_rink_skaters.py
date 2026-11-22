"""Skaters for the roller rink: rigid crowd-piece figures on skates, lap clips round the oval, and
the cast's own clothes (the silver jackets, the learner's orange rentals).

A figure is the crowd's five pieces (Assets/Models/People/Crowd/<person>/): legs at the feet,
torso at the hips, head and arms on the torso. The skating figures ride a 'Lap' entity that a
looping Sequence moves round an ellipse (positions relative to the story group at the rink's
centre), with the torso swaying on each stride and the arms swinging.
"""
import json
import math
import os
import shutil

from story_roller_rink_meshes import LOCAL, MODELS, VENUE, Mesh, save

CROWD = "Assets/Models/People/Crowd"
MOTION = os.path.join(VENUE, "Motion")
MOTION_LOCAL = "Assets/Venues/StoryRollerRink/Motion/"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FPS = 30
SKATE_LIFT = 0.075


def quat(rot):
    """Euler degrees (x, y, z) to (x, y, z, w), as the Backyard's clips do."""
    x, y, z = [math.radians(a) / 2 for a in rot]
    a, b = math.sin(x), math.cos(x)
    c, d = math.sin(y), math.cos(y)
    e, f = math.sin(z), math.cos(z)
    return [round(v, 6) for v in (a * d * f - b * c * e, b * c * f + a * d * e, b * d * e - a * c * f, b * d * f + a * c * e)]


def _key(frame, value, interp="Linear"):
    return {"Frame": int(frame), "Value": [round(v, 5) for v in value], "Interpolation": interp}


def write_clip(name, frames, tracks):
    os.makedirs(MOTION, exist_ok=True)
    clip = {"Version": 1, "Name": name, "FrameRate": FPS, "DurationFrames": int(frames), "Tracks": tracks}
    save(os.path.join(MOTION, name + ".sequence"), json.dumps(clip, indent=1) + "\n")
    return MOTION_LOCAL + name + ".sequence"


# ---- clothes ------------------------------------------------------------------------------------
def _uv_points(path):
    pts = {}
    vts = []
    for line in open(path):
        if line.startswith("vt "):
            vts.append(tuple(float(v) for v in line.split()[1:3]))
        elif line.startswith("f "):
            for corner in line.split()[1:]:
                t = vts[int(corner.split("/")[1]) - 1]
                pts[t] = pts.get(t, 0) + 1
    return pts


def dress(label, person, atlas, jacket=None):
    """Copies the figure's pieces into Models/Cast/<label>/ with a material on the given Town atlas
    variant. jacket (a colour) repaints every torso/arm texel the head doesn't also use (the skin
    and hair stay), as Cast/<label>/Jacket.png, for the torso and arms."""
    folder = os.path.join(MODELS, "Cast", label)
    os.makedirs(folder, exist_ok=True)
    src = os.path.join(ROOT, CROWD, person)
    atlas_rel = "../../../../../Models/Venue/" + atlas + ".png"
    save(os.path.join(folder, "Cast.mtl"), f"newmtl Crowd\nKd 1 1 1\nKs 0 0 0\nNs 0\nillum 1\nmap_Kd {atlas_rel}\n")
    if jacket:
        from story_roller_rink_textures import MAGICK, magick
        skin = _uv_points(os.path.join(src, "Head.obj"))
        legs = _uv_points(os.path.join(src, "Legs.obj"))
        cloth = {}
        for part in ("Torso", "ArmL", "ArmR"):
            for t, n in _uv_points(os.path.join(src, part + ".obj")).items():
                if t not in skin and t not in legs:
                    cloth[t] = cloth.get(t, 0) + n
        save(os.path.join(folder, "Jacket.mtl"), "newmtl Crowd\nKd 1 1 1\nKs 0 0 0\nNs 0\nillum 1\nmap_Kd Jacket.png\n")
        if MAGICK:
            draws = []
            for (u, v), _ in sorted(cloth.items()):
                x, y = u * 2048, (1 - v) * 2048
                draws += ["-draw", f"circle {x:.1f},{y:.1f} {x + 9:.1f},{y:.1f}"]
            tex = os.path.join(folder, "Jacket.png")
            magick(os.path.join(ROOT, "Assets/Models/Venue", atlas + ".png"), "-fill", jacket, *draws,
                   "-strip", "-define", "png:exclude-chunks=date,time", tex)
    for part in ("Legs", "Torso", "Head", "ArmL", "ArmR"):
        text = open(os.path.join(src, part + ".obj")).read()
        mtl = "Jacket.mtl" if jacket and part in ("Torso", "ArmL", "ArmR") else "Cast.mtl"
        save(os.path.join(folder, part + ".obj"), text.replace("mtllib Crowd.mtl", "mtllib " + mtl))
    return LOCAL + "Cast/" + label + "/"


# ---- skates -------------------------------------------------------------------------------------
def skates(name, boot, plate="steel", wheel="cream", stripe=None):
    m = Mesh(name, "A pair of quad roller skates around a figure's shoes (pivot at the floor, 0.075 m under the soles).")
    for side in (-1, 1):
        x = side * 0.118
        m.box((x, SKATE_LIFT + 0.075, 0.0), (0.12, 0.15, 0.27), boot)
        m.box((x, SKATE_LIFT + 0.165, -0.04), (0.125, 0.06, 0.14), stripe or boot)
        m.box((x, SKATE_LIFT - 0.008, 0.0), (0.085, 0.022, 0.25), plate)
        for z in (-0.085, 0.085):
            for dx in (-0.05, 0.05):
                m.tube((x + dx - 0.016, 0.03, z), (x + dx + 0.016, 0.03, z), 0.03, 0.03, wheel, sides=8)
        m.box((x, 0.03, 0.15), (0.05, 0.05, 0.04), "rubber")
    return m.write()


# ---- figures ------------------------------------------------------------------------------------
def figure(s, parent, label, pieces, pos=(0, 0, 0), yaw=0.0, skate=None, arms=(0, 0), arm_roll=(0, 0),
           lean=0.0, head=0.0, lifted=True):
    """A rigid figure. pieces: a folder ending in '/' with Legs/Torso/Head/ArmL/ArmR.obj. Returns
    (root, torso, armL, armR, head). arms: x rotation of each arm (negative swings it forward,
    -170 is straight up)."""
    root = s.entity(label, parent, pos, (0, yaw, 0))
    lift = SKATE_LIFT if (skate and lifted) else 0.0
    if skate:
        s.prop("Skates", root, skate, (0, 0, 0))
    legs = s.entity("Legs", root, (0, lift, 0))
    legs.add({"Type": "Model", "ModelPath": pieces + "Legs.obj"})
    torso = s.entity("Torso", root, (0, 0.8763 + lift, 0), (lean, 0, 0))
    torso.add({"Type": "Model", "ModelPath": pieces + "Torso.obj"})
    hd = s.entity("Head", torso, (0, 0.5727, -0.0242), (head, 0, 0))
    hd.add({"Type": "Model", "ModelPath": pieces + "Head.obj"})
    out = []
    for i, (part, side) in enumerate((("ArmL", -1), ("ArmR", 1))):
        arm = s.entity(part, torso, (side * 0.191, 0.5141, -0.0484), (arms[i], 0, side * arm_roll[i]))
        arm.add({"Type": "Model", "ModelPath": pieces + part + ".obj"})
        out.append(arm)
    return root, torso, out[0], out[1], hd


def lap_clip(name, a, b, seconds, phase=0.0, lateral=0.0, strides=12, sway=6.0, swing=24.0, lean=10.0,
             arms_up=False, keys=96):
    """A looping lap of the ellipse (a along x, b along z) counter-clockwise seen from above, the
    figure facing along the lane. Tracks: Lap (position, yaw), Torso (lean + stride sway), ArmL/ArmR."""
    frames = round(seconds * FPS)
    pos, rot, torso, arm_l, arm_r = [], [], [], [], []
    prev = None
    for k in range(keys + 1):
        u = k / keys
        t = 2 * math.pi * (phase - u)        # decreasing angle: counter-clockwise from above (x right, z up the page)
        x, z = a * math.cos(t), b * math.sin(t)
        tx, tz = a * math.sin(t), -b * math.cos(t)   # d/du direction
        nx, nz = b * math.cos(t), a * math.sin(t)
        nl = math.hypot(nx, nz)
        x += lateral * nx / nl
        z += lateral * nz / nl
        yaw = math.degrees(math.atan2(tx, tz))
        q = quat((0, yaw, 0))
        if prev is not None and sum(p * c for p, c in zip(prev, q)) < 0:
            q = [-c for c in q]
        prev = q
        f = round(u * frames)
        pos.append(_key(f, (x, 0, z, 0)))
        rot.append(_key(f, q))
    stride_keys = strides * 4
    for k in range(stride_keys + 1):
        u = k / stride_keys
        ph = 2 * math.pi * strides * u
        f = round(u * frames)
        torso.append(_key(f, quat((lean, 4 * math.sin(ph), sway * math.sin(ph))), "SmoothStep"))
        if arms_up:
            arm_l.append(_key(f, quat((-165 + 8 * math.sin(ph), 0, -14)), "SmoothStep"))
            arm_r.append(_key(f, quat((-165 - 8 * math.sin(ph), 0, 14)), "SmoothStep"))
        else:
            arm_l.append(_key(f, quat((-swing * math.sin(ph) - 8, 0, -9)), "SmoothStep"))
            arm_r.append(_key(f, quat((swing * math.sin(ph) - 8, 0, 9)), "SmoothStep"))
    tracks = [
        {"Binding": "Lap", "Component": "Transform", "Property": "Position", "Keys": pos},
        {"Binding": "Lap", "Component": "Transform", "Property": "Rotation", "Keys": rot},
        {"Binding": "Torso", "Component": "Transform", "Property": "Rotation", "Keys": torso},
        {"Binding": "ArmL", "Component": "Transform", "Property": "Rotation", "Keys": arm_l},
        {"Binding": "ArmR", "Component": "Transform", "Property": "Rotation", "Keys": arm_r},
    ]
    return write_clip(name, frames, tracks)


def lapping(s, parent, label, pieces, skate, clip, speed=1.0, light=None, pool=None):
    """A figure on a lap clip. light: (colour, intensity, range) for a plain point riding above it."""
    holder = s.entity(label, parent)
    root, torso, arm_l, arm_r, _ = figure(s, holder, "Lap", pieces, skate=skate)
    if light:
        s.light("Follow glow", root, (0, 3.2, 0), "Point", light[0], light[1], light[2])
    if pool:
        s.prop("Pool that follows", root, pool, (0, -0.02, 0))
    holder.add({"Type": "Sequence", "Clip": clip, "PlayOnStart": True, "Loop": True, "Speed": speed,
                "Bindings": [{"Slot": "Lap", "Target": root.guid}, {"Slot": "Torso", "Target": torso.guid},
                             {"Slot": "ArmL", "Target": arm_l.guid}, {"Slot": "ArmR", "Target": arm_r.guid}]})
    return holder


def wobble_clip(name, seconds=2.6, arms_up=False, bounce=0.0):
    """Standing in place: a nervous wobble at the rail, or the finale's hands-in-the-air bounce."""
    frames = round(seconds * FPS)
    torso, arm_l, arm_r, lap = [], [], [], []
    n = 16
    for k in range(n + 1):
        u = k / n
        ph = 2 * math.pi * u
        f = round(u * frames)
        if arms_up:
            torso.append(_key(f, quat((-4, 6 * math.sin(ph), 3 * math.sin(2 * ph))), "SmoothStep"))
            arm_l.append(_key(f, quat((-168 + 10 * math.sin(2 * ph), 0, -18 - 8 * math.sin(2 * ph))), "SmoothStep"))
            arm_r.append(_key(f, quat((-168 - 10 * math.sin(2 * ph), 0, 18 + 8 * math.sin(2 * ph))), "SmoothStep"))
        else:
            torso.append(_key(f, quat((14 + 5 * math.sin(2 * ph), 0, 7 * math.sin(ph))), "SmoothStep"))
            arm_l.append(_key(f, quat((-62 + 6 * math.sin(ph), 0, -10)), "SmoothStep"))
            arm_r.append(_key(f, quat((-58 - 6 * math.sin(ph + 1), 0, 12)), "SmoothStep"))
        lap.append(_key(f, (0, bounce * abs(math.sin(2 * ph)), 0, 0), "SmoothStep"))
    tracks = [
        {"Binding": "Lap", "Component": "Transform", "Property": "Position", "Keys": lap},
        {"Binding": "Torso", "Component": "Transform", "Property": "Rotation", "Keys": torso},
        {"Binding": "ArmL", "Component": "Transform", "Property": "Rotation", "Keys": arm_l},
        {"Binding": "ArmR", "Component": "Transform", "Property": "Rotation", "Keys": arm_r},
    ]
    return write_clip(name, frames, tracks)


def standing(s, parent, label, pieces, skate, clip, pos, yaw, speed=1.0):
    holder = s.entity(label, parent, pos, (0, yaw, 0))
    root, torso, arm_l, arm_r, _ = figure(s, holder, "Lap", pieces, skate=skate)
    holder.add({"Type": "Sequence", "Clip": clip, "PlayOnStart": True, "Loop": True, "Speed": speed,
                "Bindings": [{"Slot": "Lap", "Target": root.guid}, {"Slot": "Torso", "Target": torso.guid},
                             {"Slot": "ArmL", "Target": arm_l.guid}, {"Slot": "ArmR", "Target": arm_r.guid}]})
    return holder


def spin_clip(name, seconds, axis_tilt=0.0):
    """A full turn about y, looping (the mirror ball, its spangles and its spots)."""
    frames = round(seconds * FPS)
    keys = []
    prev = None
    for k in range(25):
        q = quat((axis_tilt, -360 * k / 24, 0))
        if prev is not None and sum(p * c for p, c in zip(prev, q)) < 0:
            q = [-c for c in q]
        prev = q
        keys.append(_key(round(k / 24 * frames), q))
    return write_clip(name, frames, [{"Binding": "Spin", "Component": "Transform", "Property": "Rotation", "Keys": keys}])
