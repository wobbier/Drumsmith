#!/usr/bin/env python3
"""Builds Assets/Venues/StoryDiveBar/: story set 04, "The Dead End Dive Bar" (s04-dive-bar).

    python3 Tools/Venues/make_story_dive_bar.py            (textures too, needs ImageMagick 7)
    python3 Tools/Venues/make_story_dive_bar.py --no-art   (scene only)

A small grimy bar. The crowd stands between the door and a corner stage (back right); the pool
table sits at the stage's left edge under a green lamp; the bar runs down the right wall, and
behind its bottles is the long back-bar mirror. The mirror is a window into a mirrored copy of
the room (furnish() is run twice, once through Kit(mirror=True)), so the league, the table, the
bartender and the stools all show up in it, reversed, as the story goes.

Story flags (manifest s04-dive-bar), each a visible change:
  league_at_table    the green pool lamp lights and four league shirts gather round the felt
  first_listener     a league shirt on the stool at the stage end of the bar, cue against it
  eight_sunk         the eight ball leaves the felt, a rack waits in the return, two shirts dance
  pool_table_covered the felt goes under a dark cover with a row of pints, cues go up in the
                     rack and the league turns round to watch the band
  door_take_counted  the bartender moves to the stage end beside a bulging DOOR envelope, LAST
                     CALL lights over the mirror and the league claps

Venue space: metres, +x the crowd's right, +y up, +z toward the stage. Deterministic.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from venuegen import Scene, look_rotation, repo_root, write_venue_json, _r, vec  # noqa: E402
import story_dive_bar_art as art  # noqa: E402

ID = "StoryDiveBar"
FOLDER = os.path.join(repo_root(), "Assets", "Venues", ID)
TEX = art.TEX_REL
LOCAL = art.MODELS_REL
SHARED = "Assets/Models/Venue/"
YARD = "Assets/Venues/Backyard/Models/"
CROWD = "Assets/Models/People/Crowd/"
MOTION = "Assets/Venues/StoryDiveBar/Motion/"
YARD_MOTION = "Assets/Venues/Backyard/Motion/"

# Room
X0, X1 = -6.5, 6.5          # side walls (the bar's wall, x = X1, holds the mirror)
Z0, Z1 = -10.5, 8.6         # front wall (behind the crowd) and back wall
CEIL = 3.4
STAGE_Y = 0.32
STAGE_X0, STAGE_Z0 = -0.6, 3.3
MIRROR = dict(z0=-6.2, z1=1.4, y0=1.05, y1=2.5)

# Pool table
PT = (-3.3, 0.0, 4.9)       # centre on the floor
PT_L, PT_W, PT_TOP = 2.6, 1.42, 0.80

# Colours
BLACK = (0.03, 0.03, 0.035)
DARKWOOD = (0.16, 0.09, 0.05)
WOOD = (0.36, 0.2, 0.1)
BRASS = (0.75, 0.55, 0.22)
CHROME = (0.7, 0.7, 0.72)
GREEN_SHADE = (0.06, 0.32, 0.12)
LAMP = (1.0, 0.93, 0.72)
WARM = (1.0, 0.62, 0.3)
AMBER = (1.0, 0.5, 0.1)
PINK = (1.0, 0.16, 0.65)
RED = (1.0, 0.12, 0.1)
ICE = (0.2, 0.6, 1.0)
FELTLIGHT = (0.72, 1.0, 0.7)

BALLS = [((0.95, 0.8, 0.1), 1), ((0.1, 0.2, 0.8), 2), ((0.85, 0.1, 0.1), 3), ((0.4, 0.1, 0.5), 4),
         ((0.95, 0.45, 0.05), 5), ((0.05, 0.45, 0.2), 6), ((0.45, 0.1, 0.08), 7)]


# ---- motion -----------------------------------------------------------------------------------

def quat(rot):
    x, y, z = [math.radians(a) / 2 for a in rot]
    a, b = math.sin(x), math.cos(x)
    c, d = math.sin(y), math.cos(y)
    e, f = math.sin(z), math.cos(z)
    return [round(v, 7) for v in (a * d * f - b * c * e, b * c * f + a * d * e, b * d * e - a * c * f, b * d * f + a * c * e)]


def write_motion():
    """Clap: straight arms up in front, hands meeting twice a second, the head nodding along."""
    folder = os.path.join(FOLDER, "Motion")
    os.makedirs(folder, exist_ok=True)
    end = 30
    keys = {
        "Spine": [(0, (2, 0, 0)), (7, (5, 0, 0)), (15, (2, 0, 0)), (22, (5, 0, 0))],
        "Head": [(0, (-6, 0, 0)), (7, (4, 0, 0)), (15, (-6, 0, 0)), (22, (4, 0, 0))],
        "Left": [(0, (-68, 0, -28)), (7, (-74, 0, 6)), (15, (-68, 0, -28)), (22, (-74, 0, 6))],
        "Right": [(0, (-68, 0, 28)), (7, (-74, 0, -6)), (15, (-68, 0, 28)), (22, (-74, 0, -6))],
    }
    tracks = []
    for joint, ks in keys.items():
        k = [{"Frame": f, "Value": quat(r), "Interpolation": "SmoothStep"} for f, r in ks]
        k.append(dict(k[0], Frame=end))
        tracks.append({"Binding": joint, "Component": "Transform", "Property": "Rotation", "Keys": k})
    clip = {"Version": 1, "Name": "Clap", "FrameRate": 30, "DurationFrames": end, "Tracks": tracks}
    data = json.dumps(clip, indent=1) + "\n"
    path = os.path.join(folder, "Clap.sequence")
    if not os.path.exists(path) or open(path).read() != data:
        with open(path, "w", newline="\n") as f:
            f.write(data)


# ---- the kit: everything placed in venue (world) space, optionally through the mirror ----------

class Kit:
    """Places things by world position. With mirror=True every position is reflected through the
    back-bar mirror's plane (x = X1), yaws and rolls flip, plain lights dim and text on textures is
    reversed, so the same furnishing code builds the room seen in the glass."""

    def __init__(self, s, mirror=False, dim=0.9):
        self.s, self.mirror, self.dim = s, mirror, dim
        self.origin = {}

    def X(self, p):
        return (2 * X1 - p[0], p[1], p[2]) if self.mirror else tuple(p)

    def R(self, r):
        return (r[0], -r[1], -r[2]) if self.mirror else tuple(r)

    def local(self, parent, world):
        o = self.origin.get(parent.guid, (0.0, 0.0, 0.0)) if parent is not None else (0.0, 0.0, 0.0)
        return tuple(world[i] - o[i] for i in range(3))

    def _track(self, e, world):
        self.origin[e.guid] = world
        return e

    def group(self, name, parent, at=(0, 0, 0)):
        w = self.X(at)
        e = self.s.entity(name, parent, self.local(parent, w))
        return self._track(e, w)

    def story(self, name, parent, flag, when_set=True, at=(0, 0, 0), fade=0.9):
        w = self.X(at)
        e = self.s.story(name, parent, flag, when_set, fade, self.local(parent, w))
        return self._track(e, w)

    def box(self, name, parent, center, size, color, rot=(0, 0, 0), tex=None, tile=(1, 1), glow=0.0, opacity=None,
            **kw):
        w = self.X(center)
        e = self.s.box(name, parent, self.local(parent, w), size, color, rot=self.R(rot), **kw)
        if tex:
            self.texture(e, tex, tile, glow)
        if opacity is not None:
            m = e.components[-1]["Material"]
            m["RenderMode"] = 1
            m["BlendMode"] = 0
            m["Opacity"] = _r(opacity)
            e.components[-1]["CastShadows"] = False
        return self._track(e, w)

    def slab(self, name, parent, x0, x1, y0, y1, z0, z1, color, **kw):
        return self.box(name, parent, ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (x1 - x0, y1 - y0, z1 - z0), color, **kw)

    def ball(self, name, parent, center, diameter, color, **kw):
        return self.box(name, parent, center, (diameter,) * 3, color, shape="Sphere", rough=0.25, **kw)

    def texture(self, e, name, tile=(1, 1), glow=0.0):
        m = e.components[-1]["Material"]
        m["DiffuseColor"] = [1.0, 1.0, 1.0] if glow else m["DiffuseColor"]
        m["Textures"] = {"Diffuse": {"Path": TEX + name + ".png"}}
        if glow:
            m["Textures"]["Emissive"] = {"Path": TEX + name + ".png"}
            m["EmissiveColor"] = [1.0, 1.0, 1.0]
            m["EmissiveIntensity"] = _r(glow)
            e.components[-1]["CastShadows"] = False
        tx = -tile[0] if self.mirror else tile[0]
        m["Tiling"] = [_r(tx), _r(-tile[1])]
        m["Offset"] = [_r(tile[0] if self.mirror else 0.0), _r(tile[1])]

    def sign(self, name, parent, tex, center, width, height, facing, glow=0.0, thick=0.03, tilt=0.0):
        """A board on a wall. facing: '+x' | '-x' | '-z' (the way the picture looks)."""
        if self.mirror and facing in ("+x", "-x"):
            facing = "-x" if facing == "+x" else "+x"
        yaw = {"-z": 0.0, "+x": -90.0, "-x": 90.0, "+z": 180.0}[facing]
        # Through the kit the yaw flips again, so hand it the pre-mirror value.
        yaw_in = -yaw if self.mirror else yaw
        e = self.box(name, parent, center, (width, height, thick), (1, 1, 1) if not glow else (1, 1, 1),
                     rot=(0, yaw_in, tilt), tex=tex, glow=glow, rough=0.8, shadows=False)
        return e

    def rod(self, name, parent, a, b, diameter, color, **kw):
        a, b = self.X(a), self.X(b)
        length = math.dist(a, b)
        centre = tuple((a[i] + b[i]) / 2 for i in range(3))
        pitch, yaw, _ = look_rotation(a, b)
        e = self.s.box(name, parent, self.local(parent, centre), (diameter, length, diameter), color,
                       rot=(pitch + 90.0, yaw, 0.0), shape="Cylinder", **kw)
        return self._track(e, centre)

    def prop(self, name, parent, model, pos, yaw=0.0, scale=1.0):
        w = self.X(pos)
        y = -yaw if self.mirror else yaw
        e = self.s.entity(name, parent, self.local(parent, w), (0, y, 0), (scale, scale, scale) if not isinstance(scale, tuple) else scale)
        e.add({"Type": "Model", "ModelPath": model})
        return self._track(e, w)

    def light(self, name, parent, pos, kind="Point", color=(1, 1, 1), intensity=10.0, range_=6.0, to=None,
              inner=20.0, outer=35.0, show=None, group=0, shadows=False, rot=(0, 0, 0)):
        if self.mirror and show is not None:
            return None
        w = self.X(pos)
        if to is not None:
            rot = look_rotation(w, self.X(to))
        else:
            rot = self.R(rot)
        e = self.s.light(name, parent, self.local(parent, w), kind, color, intensity * (self.dim if self.mirror else 1.0),
                         range_, rot=rot, inner=inner, outer=outer, shadows=shadows, show=show, group=group)
        return self._track(e, w)

    def glowbox(self, name, parent, center, size, color, power=2.0, shape="Cube", rot=(0, 0, 0)):
        return self.box(name, parent, center, size, color, rot=rot, emissive=color, emissive_intensity=power,
                        shadows=False, shape=shape)

    # ---- people --------------------------------------------------------------------------------
    def figure(self, name, parent, person, pos, yaw=0.0, torso=(0, 0, 0), head=(0, 0, 0), arm_l=(0, 0, 0),
               arm_r=(0, 0, 0), bend_l=None, bend_r=None, seated=False, league=False, motion=None, speed=1.0,
               held=None, scale=1.0):
        """A rigid crowd figure from the game's pieces (they face local +Z). yaw: atan2 style, 0 faces
        the stage (+z). bend_*: a bent arm from the Backyard's tailor (e.g. 93 for a pint hand).
        league: the mustard league shirt. motion: a .sequence clip path played on loop."""
        w = self.X(pos)
        y = -yaw if self.mirror else yaw
        root = self.s.entity(name, parent, self.local(parent, w), (0, y, 0), (scale,) * 3)
        self._track(root, w)

        def piece(part, at, anchor, rot, path):
            n = self.s.entity(part, anchor, at, rot)
            n.add({"Type": "Model", "ModelPath": path})
            return n
        legs = YARD + f"{person}_Legs_79.obj" if seated else CROWD + f"{person}/Legs.obj"
        piece("Legs", (0, 0, 0), root, (0, 0, 0), legs)
        tpath = LOCAL + f"League_{person}_Torso.obj" if league else CROWD + f"{person}/Torso.obj"
        spine = piece("Torso", (0, 0.57 if seated else 0.8763, 0), root, torso, tpath)
        hd = piece("Head", (0, 0.5727, -0.0242), spine, head, CROWD + f"{person}/Head.obj")
        arms = []
        for part, side, rot, bend in (("ArmL", -1, arm_l, bend_l), ("ArmR", 1, arm_r, bend_r)):
            path = YARD + f"{person}_{part}_{bend}.obj" if bend else CROWD + f"{person}/{part}.obj"
            arm = piece(part, (side * 0.191, 0.5141, -0.0484), spine, rot, path)
            arms.append(arm)
            if held and part == "ArmR":
                a = math.radians(bend or 0)
                palm = (0, -0.323 - 0.35 * math.cos(a), 0.35 * math.sin(a))
                hand = self.s.entity("Hand", arm, palm, (34, 0, 0))
                if held == "pint":
                    self.s.prop("Pint", hand, SHARED + "BeerCup.obj", (0, -0.05, 0.02), 0, 1.15)
        if motion:
            root.add({"Type": "Sequence", "Clip": motion, "PlayOnStart": True, "Loop": True, "Speed": _r(speed),
                      "Bindings": [{"Slot": j, "Target": p.guid} for j, p in zip(("Spine", "Head", "Left", "Right"),
                                                                                  [spine, hd] + arms)]})
        return root


def face(frm, to):
    """The figure yaw that turns local +Z from frm toward to."""
    return math.degrees(math.atan2(to[0] - frm[0], to[2] - frm[2]))


# ---- the room (built twice: in the room, and in the glass) -------------------------------------

def shell(k, root):
    g = k.group("Shell", root)
    k.slab("Sticky floor", g, X0, X1, -0.2, 0.0, Z0, Z1, (0.85, 0.85, 0.85), tex="Floor", tile=(5.5, 8.0), rough=0.35)
    k.slab("Ceiling", g, X0, X1, CEIL, CEIL + 0.15, Z0, Z1, (0.09, 0.075, 0.065), shadows=False)
    for i, z in enumerate((-8.0, -4.6, -1.2, 2.2, 5.6)):
        k.slab(f"Ceiling joist {i}", g, X0, X1, CEIL - 0.22, CEIL, z - 0.1, z + 0.1, (0.11, 0.08, 0.06), shadows=False)
    # Left wall: wood wainscot, nicotine paint above.
    k.slab("Left wall wainscot", g, X0 - 0.2, X0, 0, 1.15, Z0, Z1, (1, 1, 1), tex="Panel", tile=(10, 1), shadows=False)
    k.slab("Left wall paint", g, X0 - 0.2, X0, 1.15, CEIL, Z0, Z1, (1, 1, 1), tex="Plaster", tile=(8, 1.2), shadows=False)
    k.slab("Left wall chair rail", g, X0, X0 + 0.05, 1.12, 1.2, Z0, Z1, DARKWOOD, shadows=False)
    # Back wall: the stage part is black brick, the pool part panelled.
    k.slab("Back wall brick", g, STAGE_X0, X1, 0, CEIL, Z1, Z1 + 0.2, (1, 1, 1), tex="Brick", tile=(5, 2.5), shadows=False)
    k.slab("Back wall wainscot", g, X0, STAGE_X0, 0, 1.15, Z1, Z1 + 0.2, (1, 1, 1), tex="Panel", tile=(4.5, 1), shadows=False)
    k.slab("Back wall paint", g, X0, STAGE_X0, 1.15, CEIL, Z1, Z1 + 0.2, (1, 1, 1), tex="Plaster", tile=(3.5, 1.2), shadows=False)
    k.slab("Back chair rail", g, X0, STAGE_X0, 1.12, 1.2, Z1 - 0.05, Z1, DARKWOOD, shadows=False)
    k.slab("Front wall", g, X0, X1, 0, CEIL, Z0 - 0.2, Z0, (1, 1, 1), tex="Plaster", tile=(8, 1.2), shadows=False)


def string_lights(k, root):
    """Leftover holiday lights stapled across the joists, never taken down."""
    g = k.group("Holiday lights that never came down", root)
    cols = [(1.0, 0.25, 0.2), (1.0, 0.75, 0.2), (0.25, 0.9, 0.35), (0.3, 0.5, 1.0), (1.0, 0.35, 0.8)]
    runs = [((-6.3, 3.2, -8.0), (4.0, 3.2, -4.6)), ((-6.3, 3.2, -4.6), (4.0, 3.2, -1.2)), ((-6.3, 3.2, -1.2), (4.0, 3.2, 2.2))]
    n = 0
    for r, (a, b) in enumerate(runs):
        count = 12
        prev = a
        for i in range(1, count + 1):
            t = i / count
            sag = 0.35 * 4 * t * (1 - t)
            p = (a[0] + (b[0] - a[0]) * t, a[1] - sag, a[2] + (b[2] - a[2]) * t)
            k.rod(f"Light cord {r}/{i}", g, prev, p, 0.012, BLACK, shadows=False)
            mid = tuple((prev[j] + p[j]) / 2 for j in range(3))
            k.glowbox(f"Bulb {r}/{i}", g, (mid[0], mid[1] - 0.07, mid[2]), (0.06, 0.09, 0.06), cols[n % len(cols)], 3.0,
                      "Sphere")
            prev = p
            n += 1


def stage(k, root):
    g = k.group("Corner stage", root)
    k.slab("Stage deck", g, STAGE_X0, X1, 0, STAGE_Y - 0.02, STAGE_Z0, Z1, (0.13, 0.1, 0.09))
    k.slab("Stage carpet", g, STAGE_X0, X1, STAGE_Y - 0.02, STAGE_Y, STAGE_Z0, Z1, (0.17, 0.05, 0.05), rough=1.0)
    k.slab("Stage lip", g, STAGE_X0, X1, 0, STAGE_Y + 0.01, STAGE_Z0 - 0.06, STAGE_Z0, (0.06, 0.05, 0.05), tex="Rail",
           tile=(6, 1))
    k.slab("Stage side", g, STAGE_X0 - 0.06, STAGE_X0, 0, STAGE_Y + 0.01, STAGE_Z0, Z1, (0.06, 0.05, 0.05), tex="Rail",
           tile=(5, 1))
    for i, (x, z, w) in enumerate([(0.6, 3.55, 0.5), (1.9, 3.45, 0.3), (4.4, 3.6, 0.6)]):
        k.slab(f"Gaffer mark {i}", g, x, x + w, STAGE_Y, STAGE_Y + 0.004, z, z + 0.05, (0.75, 0.7, 0.2), shadows=False)
    # The kit's world: a threadbare rug, a towel over the floor tom's corner, a setlist.
    k.prop("Drum rug", g, SHARED + "DrumRug.obj", (3.0, STAGE_Y + 0.005, 6.5), 90, 0.85)
    k.box("Setlist", g, (1.7, STAGE_Y + 0.006, 6.0), (0.21, 0.004, 0.3), (0.9, 0.9, 0.86), rot=(0, 18, 0), shadows=False)
    # Bass rig: a combo wedged against the drummer's knees, aimed at them.
    amp_at = (1.45, STAGE_Y, 7.45)
    k.prop("Bass combo", g, SHARED + "GuitarCab.obj", amp_at, face(amp_at, (3.0, 0, 7.3)) + 180, 1.0)
    k.prop("Bass amp head", g, SHARED + "AmpHead.obj", (1.45, STAGE_Y + 0.75, 7.45), face(amp_at, (3.0, 0, 7.3)) + 180, 1.2)
    k.prop("Pint on the amp", g, SHARED + "BeerCup.obj", (1.3, STAGE_Y + 0.75, 7.25), 0, 1.15)
    k.box("Bar towel on the amp", g, (1.6, STAGE_Y + 0.76, 7.6), (0.3, 0.02, 0.22), (0.85, 0.82, 0.7), rot=(0, 20, 0))
    k.prop("Bass cable", g, SHARED + "CableCoil.obj", (0.9, STAGE_Y, 6.6), 40, 1.0)
    # A pair of tired PA tops on poles and one wedge.
    for i, x in enumerate((STAGE_X0 + 0.35, 6.05)):
        k.rod(f"PA pole {i}", g, (x, STAGE_Y, 3.75), (x, 1.7, 3.75), 0.04, CHROME, metallic=0.8, rough=0.3)
        k.prop(f"PA top {i}", g, SHARED + "SpeakerTall.obj", (x, 1.7, 3.75), 0 if i else 0, 0.75)
    k.prop("Wedge", g, SHARED + "Wedge.obj", (0.6, STAGE_Y, 3.75), 180, 1.0)
    k.prop("Road case", g, SHARED + "RoadCase.obj", (5.6, STAGE_Y, 7.9), 10, 0.8)
    k.prop("Spare cab", g, SHARED + "GuitarCab.obj", (5.6, STAGE_Y + 0.68, 7.95), 175, 0.8)
    # The sign over the stage.
    k.sign("THE DEAD END neon", g, "NeonDeadEnd", (2.9, 2.62, Z1 - 0.03), 3.4, 0.68, "-z", glow=2.6)
    k.light("Dead End neon spill", g, (2.9, 2.45, Z1 - 0.5), "Point", PINK, 7.0, 4.5)


def pool(k, root):
    """The table, its lamp, the cue rack and the league's board."""
    g = k.group("Pool corner", root)
    x, _, z = PT
    hl, hw = PT_L / 2, PT_W / 2
    k.slab("Table body", g, x - hl + 0.1, x + hl - 0.1, 0.5, PT_TOP - 0.03, z - hw + 0.1, z + hw - 0.1, DARKWOOD)
    for i, (dx, dz) in enumerate([(-1, -1), (1, -1), (-1, 1), (1, 1)]):
        k.slab(f"Leg {i}", g, x + dx * (hl - 0.32) - 0.09, x + dx * (hl - 0.32) + 0.09, 0, 0.55,
               z + dz * (hw - 0.25) - 0.09, z + dz * (hw - 0.25) + 0.09, DARKWOOD)
    k.slab("Felt", g, x - hl + 0.12, x + hl - 0.12, PT_TOP - 0.04, PT_TOP, z - hw + 0.12, z + hw - 0.12, (1, 1, 1),
           tex="Felt", tile=(2, 1), rough=1.0)
    rails = [(x - hl, x + hl, z - hw, z - hw + 0.13), (x - hl, x + hl, z + hw - 0.13, z + hw),
             (x - hl, x - hl + 0.13, z - hw, z + hw), (x + hl - 0.13, x + hl, z - hw, z + hw)]
    for i, (a, b, c, d) in enumerate(rails):
        k.slab(f"Rail {i}", g, a, b, PT_TOP - 0.06, PT_TOP + 0.05, c, d, WOOD, tex="Rail", tile=(3, 1))
    for i, (px, pz) in enumerate([(x - hl + 0.1, z - hw + 0.1), (x, z - hw + 0.08), (x + hl - 0.1, z - hw + 0.1),
                                  (x - hl + 0.1, z + hw - 0.1), (x, z + hw - 0.08), (x + hl - 0.1, z + hw - 0.1)]):
        k.box(f"Pocket {i}", g, (px, PT_TOP + 0.03, pz), (0.13, 0.06, 0.13), BLACK, shape="Cylinder")
    # The ball return at the foot of the table.
    k.slab("Ball return", g, x - hl - 0.02, x - hl + 0.2, 0.28, 0.4, z - 0.35, z + 0.35, (0.05, 0.04, 0.035))
    # Lamp: a long green shade on chains.
    ly = 1.95
    k.slab("Lamp shade", g, x - 0.85, x + 0.85, ly, ly + 0.2, z - 0.24, z + 0.24, GREEN_SHADE, rough=0.4, metallic=0.2)
    k.slab("Lamp shade cap", g, x - 0.8, x + 0.8, ly + 0.2, ly + 0.24, z - 0.12, z + 0.12, BRASS, metallic=0.8, rough=0.3)
    for dx in (-0.6, 0.6):
        k.rod(f"Lamp chain {dx}", g, (x + dx, ly + 0.24, z), (x + dx, CEIL - 0.2, z), 0.018, BRASS, metallic=0.8, rough=0.4,
              shadows=False)
    # Cue rack on the left wall and the board.
    k.slab("Cue rack", g, X0, X0 + 0.06, 0.6, 1.9, 5.7, 6.9, DARKWOOD)
    k.sign("League board", g, "Chalk", (x, 1.78, Z1 - 0.03), 1.5, 1.0, "-z")
    k.sign("STAG RIVER neon", g, "NeonStag", (-5.35, 2.62, Z1 - 0.04), 1.6, 0.5, "-z", glow=2.4)
    k.light("Stag neon spill", g, (-5.35, 2.5, Z1 - 0.5), "Point", AMBER, 6.0, 4.0)
    k.sign("House rules", g, "Rules", (X0 + 0.02, 1.55, 4.6), 0.5, 0.38, "+x", tilt=-3)
    k.sign("Neon 8", g, "NeonPool", (X0 + 0.04, 2.55, 4.4), 0.55, 0.55, "+x", glow=2.4)
    k.light("Neon 8 spill", g, (X0 + 0.5, 2.5, 4.4), "Point", (0.3, 1.0, 0.45), 4.0, 3.5)
    # Jukebox in the corner.
    j = (X0 + 0.5, 0, Z1 - 0.45)
    k.box("Jukebox", g, (j[0], 0.75, j[2]), (0.8, 1.5, 0.55), (0.25, 0.08, 0.05), rot=(0, 35, 0), rough=0.4)
    k.box("Jukebox arch", g, (j[0] + 0.12, 1.25, j[2] - 0.2), (0.62, 0.42, 0.05), (1.0, 0.45, 0.15), rot=(0, 35, 0),
          emissive=(1.0, 0.45, 0.15), emissive_intensity=2.2, shadows=False)
    k.box("Jukebox grille", g, (j[0] + 0.12, 0.55, j[2] - 0.2), (0.55, 0.45, 0.05), (0.6, 0.12, 0.55), rot=(0, 35, 0),
          emissive=(0.6, 0.12, 0.55), emissive_intensity=1.4, shadows=False)
    k.light("Jukebox glow", g, (j[0] + 0.5, 1.0, j[2] - 0.5), "Point", (1.0, 0.45, 0.25), 4.0, 3.0)


def balls(k, parent, x, z, scattered=True):
    """Seven coloured balls and the cue ball scattered across the felt (the eight is separate)."""
    spots = [(-0.8, -0.3), (-0.35, 0.28), (0.05, -0.12), (0.45, 0.33), (0.75, -0.26), (-0.55, 0.05), (0.25, 0.1)]
    for (col, n), (dx, dz) in zip(BALLS, spots):
        k.ball(f"Ball {n}", parent, (x + dx, PT_TOP + 0.045, z + dz), 0.09, col)
    k.ball("Cue ball", parent, (x + 0.95, PT_TOP + 0.045, z + 0.05), 0.09, (0.95, 0.93, 0.85))


def league_playing(k, parent):
    """Mid-match: a shooter down on the felt with his back to the stage, a chalker, a leaner, a
    watcher with a pint."""
    x, _, z = PT
    shooter = (x + PT_L / 2 + 0.55, 0.0, z + 0.15)
    k.figure("Shooter (back to the band)", parent, "Son_01", shooter, -90, torso=(48, 0, 0), head=(-38, 0, 0),
             arm_l=(-58, 0, 8), arm_r=(-30, 0, -6), league=True)
    k.rod("Shooter's cue", parent, (shooter[0] + 0.5, 1.02, shooter[2] - 0.05), (x + 0.55, PT_TOP + 0.06, z + 0.1), 0.028,
          (0.75, 0.55, 0.3))
    chalker = (x - 0.2, 0.0, z + PT_W / 2 + 0.55)
    k.figure("Chalking up", parent, "Mother_01", chalker, 180, head=(12, 0, 0), arm_l=(-35, 0, 12), arm_r=(-62, 0, -18),
             league=True)
    k.rod("Upright cue", parent, (chalker[0] - 0.28, 0.0, chalker[2] - 0.2), (chalker[0] - 0.25, 1.45, chalker[2] - 0.25),
          0.028, (0.75, 0.55, 0.3))
    leaner = (x - PT_L / 2 - 0.5, 0.0, z - 0.25)
    k.figure("Leaning on a cue", parent, "ShopKeeper_01", leaner, 75, motion=YARD_MOTION + "TellTheStory.sequence",
             bend_l=66, bend_r=38, league=True, speed=0.8)
    k.rod("Leaner's cue", parent, (leaner[0] + 0.15, 0.0, leaner[2] - 0.35), (leaner[0] + 0.12, 1.45, leaner[2] - 0.12),
          0.028, (0.75, 0.55, 0.3))
    watcher = (x + 0.35, 0.0, z - PT_W / 2 - 0.6)
    k.figure("Watching the shot", parent, "Rigged", watcher, 10, arm_l=(-8, 0, 6), arm_r=(-8, 0, -6), head=(14, 0, 0),
             league=True)


def league_watching(k, parent, clapping):
    """After the match: the league stands round the covered table and turns to the band."""
    x, _, z = PT
    spots = [("Son_01", (x + PT_L / 2 + 0.45, 0.0, z - 0.45)), ("Mother_01", (x + 0.5, 0.0, z - PT_W / 2 - 0.5)),
             ("ShopKeeper_01", (x - 0.65, 0.0, z - PT_W / 2 - 0.55)), ("Rigged", (x - PT_L / 2 + 0.05, 0.0, z + PT_W / 2 + 0.45))]
    band = (2.4, 0.0, 6.0)
    for i, (person, at) in enumerate(spots):
        yaw = face(at, band)
        if clapping:
            k.figure(f"League clapping {i + 1}", parent, person, at, yaw, league=True, motion=MOTION + "Clap.sequence",
                     speed=0.9 + 0.07 * i)
        elif person in ("Son_01",):
            k.figure(f"League watching {i + 1}", parent, person, at, yaw, league=True, bend_r=93,
                     motion=YARD_MOTION + "ListenAndSip.sequence", held="pint", speed=0.9)
        else:
            k.figure(f"League watching {i + 1}", parent, person, at, yaw, league=True, arm_l=(-6, 0, 5), arm_r=(-6, 0, -5),
                     head=(-4, 0, 0))


def pool_story(k, root):
    g = k.group("Pool story", root)
    x, _, z = PT
    ly = 1.95
    # league_at_table: the lamp comes on, the league gathers.
    lamp = k.story("Pool lamp on [league_at_table]", g, "league_at_table", True, (x, ly, z))
    k.slab("Lamp glow", lamp, x - 0.8, x + 0.8, ly - 0.01, ly + 0.01, z - 0.2, z + 0.2, LAMP, emissive=LAMP,
           emissive_intensity=3.0, shadows=False)
    k.light("Green felt lamp", lamp, (x, ly - 0.05, z), "Spot", FELTLIGHT, 110.0, 5.0, to=(x, 0, z), inner=40, outer=70)
    k.light("Green felt bounce", lamp, (x, 1.2, z - 1.4), "Point", (0.45, 1.0, 0.5), 6.0, 4.0)
    league = k.story("League at the table [league_at_table]", g, "league_at_table", True, (x, 0, z))
    playing = k.story("Still playing [until pool_table_covered]", league, "pool_table_covered", False, (x, 0, z))
    league_playing(k, playing)
    # The balls: the colours stay until the cover goes on; the eight goes when it's sunk.
    on_felt = k.story("Balls on the felt [until pool_table_covered]", g, "pool_table_covered", False, (x, PT_TOP, z))
    balls(k, on_felt, x, z)
    eight = k.story("The eight [until eight_sunk]", g, "eight_sunk", False, (x - 0.15, PT_TOP, z + 0.4))
    k.ball("Eight ball", eight, (x - 0.15, PT_TOP + 0.045, z + 0.4), 0.09, (0.02, 0.02, 0.02))
    k.ball("Eight ball spot", eight, (x - 0.15, PT_TOP + 0.06, z + 0.37), 0.04, (0.95, 0.95, 0.9))
    # eight_sunk: a fresh rack in the return; two shirts dance to the riff.
    rack = k.story("Rematch rack in the return [eight_sunk]", g, "eight_sunk", True, (x - PT_L / 2, 0.4, z))
    n = 0
    for row in range(3):
        for col in range(row + 1):
            col_, cnum = BALLS[n % len(BALLS)]
            k.ball(f"Racked {n}", rack, (x - PT_L / 2 + 0.06 + row * 0.08, 0.44, z - row * 0.045 + col * 0.09), 0.09, col_)
            n += 1
    k.box("Wooden triangle", rack, (x - PT_L / 2 + 0.14, 0.45, z), (0.3, 0.05, 0.3), WOOD, rot=(0, 45, 0))
    dance = k.story("Two shirts dancing [eight_sunk]", g, "eight_sunk", True, (-2.2, 0, 2.4))
    k.figure("Dancing shirt 1", dance, "Mother_01", (-1.75, 0, 2.55), 40, league=True, bend_l=40, bend_r=74,
             motion=YARD_MOTION + "KitchenTwoStep.sequence", speed=1.0)
    k.figure("Dancing shirt 2", dance, "Rigged", (-2.85, 0, 2.2), 25, league=True, bend_l=40, bend_r=74,
             motion=YARD_MOTION + "KitchenTwoStep.sequence", speed=1.08)
    # pool_table_covered: the cover, a row of pints, cues up in the rack, the league turns round.
    cov = k.story("Table cover [pool_table_covered]", g, "pool_table_covered", True, (x, PT_TOP, z), fade=1.4)
    hl, hw = PT_L / 2 + 0.04, PT_W / 2 + 0.04
    k.slab("Cover top", cov, x - hl, x + hl, PT_TOP + 0.05, PT_TOP + 0.1, z - hw, z + hw, (1, 1, 1), tex="Cover",
           tile=(1, 1), rough=0.6)
    k.slab("Cover skirt front", cov, x - hl, x + hl, PT_TOP - 0.22, PT_TOP + 0.1, z - hw - 0.02, z - hw, (0.16, 0.12, 0.1))
    k.slab("Cover skirt back", cov, x - hl, x + hl, PT_TOP - 0.22, PT_TOP + 0.1, z + hw, z + hw + 0.02, (0.16, 0.12, 0.1))
    k.slab("Cover skirt foot", cov, x - hl - 0.02, x - hl, PT_TOP - 0.22, PT_TOP + 0.1, z - hw, z + hw, (0.16, 0.12, 0.1))
    k.slab("Cover skirt head", cov, x + hl, x + hl + 0.02, PT_TOP - 0.22, PT_TOP + 0.1, z - hw, z + hw, (0.16, 0.12, 0.1))
    for i in range(9):
        k.prop(f"Fresh pint {i + 1}", cov, SHARED + "BeerCup.obj", (x - 1.1 + i * 0.27, PT_TOP + 0.1, z - hw + 0.12), i * 23, 1.45)
    k.light("Pints catching the lamp", cov, (x, 1.3, z - 1.2), "Point", (1.0, 0.75, 0.4), 16.0, 3.5)
    cues = k.story("Cues in the rack [pool_table_covered]", g, "pool_table_covered", True, (X0 + 0.1, 1.2, 6.3))
    for i in range(5):
        cz = 5.85 + i * 0.22
        k.rod(f"Racked cue {i + 1}", cues, (X0 + 0.1, 0.62, cz), (X0 + 0.1, 1.95, cz + 0.02), 0.028, (0.75, 0.55, 0.3))
    watching = k.story("League watching [pool_table_covered]", league, "pool_table_covered", True, (x, 0, z))
    still = k.story("Listening [until door_take_counted]", watching, "door_take_counted", False, (x, 0, z))
    league_watching(k, still, clapping=False)
    claps = k.story("Clapping through the stops [door_take_counted]", watching, "door_take_counted", True, (x, 0, z))
    league_watching(k, claps, clapping=True)


def bar(k, root):
    g = k.group("The bar", root)
    zb0, zb1 = -7.4, 1.9
    k.slab("Bar front", g, 4.3, 4.42, 0, 1.06, zb0, zb1, (1, 1, 1), tex="Panel", tile=(9, 1))
    k.slab("Bar body", g, 4.42, 5.0, 0, 1.0, zb0, zb1, (0.12, 0.07, 0.04))
    k.slab("Bar end", g, 4.3, 5.0, 0, 1.06, zb1, zb1 + 0.1, (1, 1, 1), tex="Panel", tile=(1, 1))
    k.slab("Bar top", g, 4.2, 5.1, 1.06, 1.12, zb0, zb1 + 0.12, (1, 1, 1), tex="BarTop", tile=(1, 6), rough=0.25)
    k.slab("Bar top lip", g, 4.15, 4.22, 1.04, 1.12, zb0, zb1 + 0.12, (0.2, 0.1, 0.05), rough=0.3)
    k.rod("Foot rail", g, (4.18, 0.2, zb0), (4.18, 0.2, zb1), 0.05, BRASS, metallic=0.9, rough=0.3)
    # Back bar: a low cabinet, glass shelves across the mirror, bottles, a register and the taps.
    k.slab("Back-bar cabinet", g, 6.0, X1, 0, 0.95, MIRROR["z0"] - 0.6, MIRROR["z1"] + 0.4, (0.1, 0.06, 0.035))
    k.slab("Back-bar top", g, 5.95, X1, 0.95, 1.0, MIRROR["z0"] - 0.6, MIRROR["z1"] + 0.4, (1, 1, 1), tex="BarTop",
           tile=(1, 4), rough=0.3)
    for y in (1.88,):
        k.slab(f"Glass shelf {y}", g, 6.22, X1, y - 0.015, y, MIRROR["z0"] + 0.1, MIRROR["z1"] - 0.1, (0.6, 0.75, 0.75),
               rough=0.1, shadows=False)
    glass = [(0.62, 0.3, 0.06), (0.12, 0.36, 0.14), (0.75, 0.78, 0.76), (0.45, 0.06, 0.05), (0.85, 0.6, 0.2),
             (0.1, 0.15, 0.4)]
    n = 0
    z = MIRROR["z0"] + 0.2
    while z < MIRROR["z1"] - 0.12:
        for j, y in enumerate((1.0, 1.88)):
            if (n + j) % 6 == 4:
                continue
            col = glass[(n * 5 + j * 2) % len(glass)]
            tall = 0.2 + 0.06 * ((n + j) % 3)
            bx = 6.34 + 0.05 * ((n + j) % 2)
            k.box(f"Bottle {n}-{j}", g, (bx, y + tall / 2, z), (0.085, tall, 0.085), col, shape="Cylinder", rough=0.15,
                  emissive=col, emissive_intensity=0.35)
            k.box(f"Bottle neck {n}-{j}", g, (bx, y + tall + 0.05, z), (0.032, 0.1, 0.032), col, shape="Cylinder",
                  rough=0.15, shadows=False)
        n += 1
        z += 0.23
    for y in (1.0, 1.88):
        k.glowbox(f"Shelf light {y}", g, (X1 - 0.03, y + 0.02, (MIRROR["z0"] + MIRROR["z1"]) / 2), (0.03, 0.02,
                  MIRROR["z1"] - MIRROR["z0"] - 0.2), (1.0, 0.72, 0.4), 2.5)
    k.slab("Mirror frame top", g, 6.42, X1, MIRROR["y1"], MIRROR["y1"] + 0.1, MIRROR["z0"] - 0.1, MIRROR["z1"] + 0.1,
           DARKWOOD)
    k.slab("Mirror frame left", g, 6.42, X1, MIRROR["y0"], MIRROR["y1"], MIRROR["z0"] - 0.1, MIRROR["z0"], DARKWOOD)
    k.slab("Mirror frame right", g, 6.42, X1, MIRROR["y0"], MIRROR["y1"], MIRROR["z1"], MIRROR["z1"] + 0.1, DARKWOOD)
    k.box("Register", g, (4.72, 1.25, -6.6), (0.42, 0.26, 0.36), (0.2, 0.2, 0.22), rot=(0, 90, 0), metallic=0.4,
          rough=0.4)
    k.box("Register display", g, (4.6, 1.42, -6.6), (0.3, 0.09, 0.03), (0.2, 1.0, 0.3), rot=(0, 90, 0),
          emissive=(0.2, 1.0, 0.3), emissive_intensity=2.0, shadows=False)
    tap_z = -2.9
    k.slab("Tap tower", g, 4.62, 4.78, 1.12, 1.48, tap_z - 0.55, tap_z + 0.55, CHROME, metallic=0.9, rough=0.25)
    for i in range(4):
        tz = tap_z - 0.42 + i * 0.28
        k.rod(f"Tap handle {i}", g, (4.62, 1.38, tz), (4.62, 1.62, tz), 0.04,
              [(0.9, 0.45, 0.1), (0.1, 0.1, 0.1), (0.8, 0.1, 0.1), (0.9, 0.8, 0.5)][i])
    k.sign("Price board", g, "Menu", (X1 - 0.03, 2.78, -4.4), 1.4, 0.46, "-x")
    k.sign("ice cold neon", g, "NeonCold", (X1 - 0.04, 2.8, -1.9), 1.3, 0.33, "-x", glow=2.4)
    k.light("Ice cold spill", g, (X1 - 0.5, 2.6, -1.9), "Point", ICE, 5.0, 3.5)
    # Glasses upside down on a drip mat, a bowl of limes, the bar's beer stack.
    for i in range(6):
        k.prop(f"Drying glass {i}", g, SHARED + "BeerCup.obj", (4.75 + 0.1 * (i % 2), 1.12, -5.4 + 0.13 * i), 0, 1.2)
    k.prop("Keg", g, SHARED + "Keg.obj", (5.5, 0, MIRROR["z0"] - 1.0), 0, 1.0)
    k.prop("Keg 2", g, SHARED + "Keg.obj", (5.55, 0, MIRROR["z0"] - 1.6), 40, 1.0)
    # Stools down the bar (the first listener's is in the story).
    for i, sz in enumerate((-6.6, -5.4, -4.2, -3.0, -1.8, -0.6)):
        k.prop(f"Bar stool {i + 1}", g, SHARED + "Stool.obj", (3.88, 0, sz), i * 31, 1.05)
    # Hanging pendants over the bar.
    for i, pz in enumerate((-5.6, -2.6, 0.4)):
        k.rod(f"Pendant cord {i}", g, (4.75, 2.3, pz), (4.75, CEIL - 0.2, pz), 0.015, BLACK, shadows=False)
        k.box(f"Pendant shade {i}", g, (4.75, 2.25, pz), (0.32, 0.18, 0.32), (0.55, 0.25, 0.08), shape="Cylinder",
              rough=0.5)
        k.glowbox(f"Pendant bulb {i}", g, (4.75, 2.14, pz), (0.12, 0.1, 0.12), WARM, 3.0, "Sphere")
        k.light(f"Pendant {i}", g, (4.75, 2.05, pz), "Point", WARM, 6.0, 4.0)
    k.light("Back-bar glow", g, (5.5, 0.9, -2.4), "Point", (1.0, 0.6, 0.3), 4.0, 4.0)
    # Two regulars who were here before the band and will be here after.
    k.figure("Regular, hunched", g, "Daughter_01", (3.82, 0.17, -5.4), 95, seated=True, torso=(20, 0, 0),
             head=(-6, 0, 0), arm_l=(-58, 0, -12), arm_r=(-58, 0, 12))
    k.figure("Regular with a pint", g, "Mother_02", (3.82, 0.17, -3.0), 70, seated=True, bend_r=93,
             motion=YARD_MOTION + "ListenAndSip.sequence", held="pint", speed=0.8)


def bar_story(k, root):
    g = k.group("Bar story", root)
    # first_listener: a league shirt on the stool at the stage end, cue against it.
    st = (3.88, 0.0, 1.25)
    fl = k.story("First listener [first_listener]", g, "first_listener", True, st)
    k.prop("Listener's stool", fl, SHARED + "Stool.obj", st, 20, 1.05)
    k.figure("First listener", fl, "Son_01", (st[0], 0.17, st[2]), face(st, (1.6, 0, 6.0)), seated=True, league=True,
             bend_r=93, motion=YARD_MOTION + "ListenAndSip.sequence", held="pint", speed=0.75)
    k.rod("Cue against the stool", fl, (4.3, 0.0, 1.55), (4.12, 1.5, 1.05), 0.03, (0.75, 0.55, 0.3))
    k.prop("Listener's pint", fl, SHARED + "BeerCup.obj", (4.4, 1.12, 1.3), 0, 1.2)
    # The bartender: down the bar wiping until the door take is counted, then by the envelope.
    away = k.story("Bartender down the bar [until door_take_counted]", g, "door_take_counted", False, (5.6, 0, -4.2))
    k.figure("Bartender wiping", away, "ShopKeeper_01", (5.6, 0.0, -4.2), -90, torso=(14, 0, 0), arm_l=(-50, 0, -14),
             arm_r=(-42, 0, 14), head=(10, 0, 0))
    k.box("Bar rag", away, (4.85, 1.13, -4.15), (0.25, 0.02, 0.2), (0.85, 0.85, 0.75), rot=(0, 25, 0))
    take = k.story("Door take counted [door_take_counted]", g, "door_take_counted", True, (5.2, 1.1, 0.4), fade=1.2)
    k.figure("Bartender with the envelope", take, "ShopKeeper_01", (5.55, 0.0, 0.55), -110, arm_l=(-38, 0, -8),
             arm_r=(-62, 0, -18), head=(8, 0, 0))
    k.box("Bulging DOOR envelope", take, (4.72, 1.2, 0.35), (0.42, 0.16, 0.28), (1, 1, 1), rot=(0, 78, 0), tex="Envelope")
    for i in range(5):
        k.box(f"Bills {i}", take, (4.82 + 0.02 * i, 1.29, 0.22 + 0.06 * i), (0.16, 0.012, 0.08), (0.5, 0.7, 0.45),
              rot=(0, 30 + 17 * i, 8 * (i % 2)), shadows=False)
    k.box("Coin stack", take, (4.6, 1.15, 0.75), (0.06, 0.06, 0.06), BRASS, shape="Cylinder", metallic=0.9, rough=0.3)
    k.glowbox("Desk lamp bulb", take, (5.0, 1.5, 0.95), (0.1, 0.06, 0.1), WARM, 3.5, "Sphere")
    k.box("Desk lamp shade", take, (5.0, 1.55, 0.95), (0.26, 0.12, 0.26), (0.05, 0.3, 0.12), shape="Cylinder")
    k.rod("Desk lamp stem", take, (5.05, 1.12, 1.0), (5.0, 1.55, 0.95), 0.025, BRASS, metallic=0.8)
    k.light("Counting light", take, (4.95, 1.45, 0.7), "Point", WARM, 12.0, 3.0)
    lc = k.story("LAST CALL lit [door_take_counted]", g, "door_take_counted", True, (X1 - 0.04, 2.85, 0.4), fade=0.4)
    k.sign("LAST CALL neon", lc, "NeonLastCall", (X1 - 0.04, 2.85, 0.4), 1.9, 0.48, "-x", glow=2.8)
    k.light("Last call spill", lc, (X1 - 0.6, 2.6, 0.4), "Point", RED, 10.0, 5.0)


def front(k, root):
    """The crowd's end: the door, the dartboard, a booth, the posters."""
    g = k.group("Front of house", root)
    # Door on the left wall near the front, with the OPEN sign beside it.
    k.slab("Door", g, X0, X0 + 0.06, 0, 2.15, -9.6, -8.6, (0.18, 0.06, 0.04))
    k.slab("Door frame", g, X0, X0 + 0.08, 2.15, 2.25, -9.7, -8.5, DARKWOOD)
    k.box("Door push plate", g, (X0 + 0.07, 1.1, -8.8), (0.01, 0.3, 0.1), BRASS, metallic=0.9)
    k.sign("OPEN neon", g, "NeonOpen", (X0 + 0.05, 1.9, -7.6), 0.8, 0.4, "+x", glow=2.4)
    k.light("Open spill", g, (X0 + 0.5, 1.8, -7.6), "Point", RED, 4.0, 3.0)
    k.sign("Old Knuckle neon", g, "NeonKnuckle", (X0 + 0.04, 2.55, -0.8), 1.5, 0.47, "+x", glow=2.4)
    k.light("Knuckle spill", g, (X0 + 0.6, 2.45, -0.8), "Point", RED, 6.0, 4.0)
    # Dartboard with its own little lamp and a chalk throw line.
    k.box("Dart cabinet", g, (X0 + 0.04, 1.73, -3.6), (0.06, 0.72, 0.72), DARKWOOD)
    k.sign("Dartboard", g, "Dartboard", (X0 + 0.08, 1.73, -3.6), 0.5, 0.5, "+x")
    k.light("Dart lamp", g, (X0 + 0.7, 2.4, -3.6), "Spot", LAMP, 18.0, 3.0, to=(X0, 1.73, -3.6), inner=18, outer=32)
    k.slab("Oche", g, X0 + 2.3, X0 + 2.35, 0.0, 0.005, -4.1, -3.1, (0.85, 0.85, 0.8), shadows=False)
    for i, (tex, z) in enumerate([("PosterA", -5.6), ("PosterB", -6.3), ("PosterC", 1.4)]):
        k.sign(f"Poster {i}", g, tex, (X0 + 0.02, 1.62, z), 0.42, 0.6, "+x", tilt=(-2, 3, -1)[i])
    # A booth along the left wall.
    for i, bz in enumerate((-6.9, -5.3)):
        k.slab(f"Booth bench {i}", g, X0, X0 + 0.55, 0.0, 0.45, bz - 0.25, bz + 0.25, (0.35, 0.07, 0.05), rough=0.5)
        k.slab(f"Booth back {i}", g, X0, X0 + 0.55, 0.45, 1.05, bz - 0.25 + (0.4 if i == 0 else 0.0),
               bz - 0.15 + (0.4 if i == 0 else 0.0), (0.35, 0.07, 0.05), rough=0.5)
    k.slab("Booth table", g, X0, X0 + 0.75, 0.72, 0.76, -6.6, -5.6, (1, 1, 1), tex="BarTop", tile=(1, 1), rough=0.3)
    k.rod("Booth table leg", g, (X0 + 0.4, 0, -6.1), (X0 + 0.4, 0.72, -6.1), 0.08, BLACK)
    for i, (x, z) in enumerate([(X0 + 0.3, -6.3), (X0 + 0.45, -5.9)]):
        k.prop(f"Booth pint {i}", g, SHARED + "BeerCup.obj", (x, 0.76, z), i * 40, 1.2)
    # A high-top by the pool corner and a bin.
    k.rod("High-top post", g, (-5.4, 0, 1.9), (-5.4, 1.05, 1.9), 0.07, BLACK)
    k.box("High-top", g, (-5.4, 1.07, 1.9), (0.62, 0.04, 0.62), DARKWOOD, shape="Cylinder")
    k.prop("High-top stool", g, SHARED + "Stool.obj", (-5.0, 0, 2.5), 15, 1.05)
    k.prop("Bin", g, SHARED + "WheelieBin.obj", (X0 + 0.4, 0, 7.1), 80, 0.7)
    k.prop("Empties", g, SHARED + "CardboardBox.obj", (X0 + 0.35, 0, -2.2), 20, 1.0)
    k.light("Over the booth", g, (X0 + 0.6, 2.4, -6.1), "Point", WARM, 6.0, 3.5)
    k.light("Over the door", g, (X0 + 0.6, 2.6, -9.1), "Point", (1.0, 0.85, 0.6), 4.0, 3.0)


def reflected_audience(k, root):
    """In the glass only: stand-ins for the people in the room the mirror catches (the game's
    crowd and band aren't scene geometry, so the reflection gets its own)."""
    g = k.group("Reflected regulars", root)
    for i, (person, at) in enumerate([("Mother_02", (-0.6, 0, -1.4)), ("Son_01", (0.6, 0, -0.6)),
                                      ("Daughter_01", (1.7, 0, -1.6)), ("SchoolBoy_01", (-1.4, 0, -3.4)),
                                      ("Rigged", (0.2, 0, -3.0)), ("Mother_01", (1.4, 0, -3.8)),
                                      ("ShopKeeper_01", (2.4, 0, 0.6))]):
        k.figure(f"Reflected listener {i + 1}", g, person, at, face(at, (2.0, 0, 6.0)), arm_l=(-6, 0, 5), arm_r=(-6, 0, -5),
                 head=(-5, 0, 0))
    # The band's shapes in the glass: a drummer behind a dark kit block, the bassist.
    k.figure("Reflected drummer", g, "Son_01", (3.0, STAGE_Y - 0.25, 7.4), 180, torso=(10, 0, 0), arm_l=(-50, 0, 12),
             arm_r=(-50, 0, -12))
    k.slab("Reflected kit", g, 1.9, 4.1, STAGE_Y, STAGE_Y + 0.75, 5.7, 6.9, (0.12, 0.1, 0.1), rough=0.4)
    k.figure("Reflected bassist", g, "Rigged", (0.7, STAGE_Y, 5.2), 155, arm_l=(-40, 0, 15), arm_r=(-60, 0, -25))
    k.light("Stage in the glass", g, (2.0, 2.8, 3.6), "Spot", (0.9, 0.6, 0.8), 160.0, 8.0, to=(2.0, 0.8, 6.5), inner=30,
            outer=60)


def furnish(k, root):
    shell(k, root)
    string_lights(k, root)
    stage(k, root)
    pool(k, root)
    pool_story(k, root)
    bar(k, root)
    bar_story(k, root)
    front(k, root)


# ---- only in the room --------------------------------------------------------------------------

def right_wall(s, root):
    k = Kit(s)
    g = k.group("Bar wall with the mirror", root)
    m = MIRROR
    for name, (z0, z1, y0, y1) in {"below": (Z0, Z1, 0, m["y0"]), "above": (Z0, Z1, m["y1"], CEIL),
                                   "front": (Z0, m["z0"], m["y0"], m["y1"]), "back": (m["z1"], Z1, m["y0"], m["y1"])}.items():
        k.slab(f"Bar wall {name}", g, X1, X1 + 0.2, y0, y1, z0, z1, (1, 1, 1), tex="Plaster",
               tile=(max(1, (z1 - z0) / 2.2), max(0.4, (y1 - y0) / 2.2)), shadows=False)
    # The glass: a faint smoky film over the reflected room.
    k.slab("Mirror glass", g, X1 - 0.012, X1 - 0.004, m["y0"], m["y1"], m["z0"], m["z1"], (0.55, 0.6, 0.62), opacity=0.16,
           rough=0.05, metallic=0.6)
    # Close the reflected room's far side so nothing beyond it shows through the window.
    k.slab("Reflection's end wall", g, 2 * X1 - X0, 2 * X1 - X0 + 0.2, 0, CEIL, Z0, Z1, (0.05, 0.04, 0.035), shadows=False)


def show_lights(s, root):
    k = Kit(s)
    g = k.group("Show lights (cued)", root)
    # A short pipe over the stage's front edge with four cans.
    k.rod("Lighting pipe", g, (STAGE_X0 - 0.3, CEIL - 0.3, STAGE_Z0 - 0.4), (X1 - 0.2, CEIL - 0.3, STAGE_Z0 - 0.4), 0.05,
          BLACK, shadows=False)
    cans = [((0.0, 3.0, 2.9), (0.8, 0.8, 5.3), (1.0, 0.25, 0.35), 0), ((1.5, 3.0, 2.9), (3.0, 1.0, 6.9), (0.3, 0.45, 1.0), 1),
            ((3.6, 3.0, 2.9), (3.0, 1.0, 6.9), (1.0, 0.55, 0.15), 2), ((5.2, 3.0, 2.9), (4.2, 0.7, 6.0), (0.75, 0.25, 1.0), 0)]
    for i, (pos, to, col, grp) in enumerate(cans):
        k.box(f"Can {i}", g, (pos[0], pos[1] + 0.12, pos[2]), (0.2, 0.28, 0.2), BLACK, shape="Cylinder", shadows=False)
        k.light(f"Stage can {i}", g, pos, "Spot", col, 420.0, 9.0, to=to, inner=18, outer=38, show="Wash", group=grp)
    k.light("Back wash left", g, (0.2, 3.0, 8.2), "Spot", (0.9, 0.2, 0.7), 260.0, 8.0, to=(1.0, 1.0, 4.5), inner=25,
            outer=50, show="Wash", group=1)
    k.light("Back wash right", g, (5.8, 3.0, 8.2), "Spot", (0.2, 0.5, 1.0), 260.0, 8.0, to=(3.0, 1.0, 4.5), inner=25,
            outer=50, show="Wash", group=2)
    k.light("Follow on the drummer", g, (2.2, 3.15, 1.4), "Spot", (1.0, 0.88, 0.75), 360.0, 10.0, to=(3.0, 1.3, 7.2),
            inner=9, outer=17, show="Spot", group=0)
    k.light("Follow on the bass", g, (-0.5, 3.15, 1.2), "Spot", (0.95, 0.85, 0.8), 320.0, 9.0, to=(0.7, 1.3, 5.2),
            inner=9, outer=17, show="Spot", group=1)
    for i, (pos, to, col) in enumerate([((0.0, 3.1, 8.3), (-1.5, 0.5, -4.0), (1.0, 0.3, 0.5)),
                                        ((6.0, 3.1, 8.3), (3.0, 0.5, -4.0), (0.3, 0.6, 1.0))]):
        k.light(f"Bar-room scanner {i}", g, pos, "Spot", col, 900.0, 16.0, to=to, inner=5, outer=11, show="Beam", group=i)
    k.light("Blinder", g, (2.9, 0.55, 3.45), "Spot", (1.0, 0.8, 0.55), 520.0, 12.0, to=(0.5, 1.4, -6.0), inner=25, outer=55,
            show="Blinder", group=0)
    k.box("Blinder housing", g, (2.9, 0.45, 3.4), (0.4, 0.22, 0.14), BLACK)
    k.light("Strobe", g, (2.9, 3.15, 3.0), "Point", (1.0, 1.0, 1.0), 220.0, 12.0, show="Strobe", group=0)
    k.light("Crowd wash", g, (0.0, 3.1, -4.0), "Point", (1.0, 0.6, 0.35), 60.0, 9.0, show="Wash", group=0)
    k.light("Crowd wash back", g, (0.0, 3.1, -8.0), "Point", (0.6, 0.4, 0.9), 50.0, 8.0, show="Wash", group=2)


def house_lights(s, root):
    k = Kit(s)
    g = k.group("House", root)
    k.light("Smoky key through the vents", g, (0, 8, -6), "Directional", (1.0, 0.86, 0.7), 0.35, rot=(52, 18, 0),
            shadows=True, show="Static")
    k.light("Room fill", g, (0.0, 3.0, -3.0), "Point", (1.0, 0.72, 0.48), 22.0, 12.0)
    k.light("Room fill back", g, (-2.0, 3.0, 3.0), "Point", (1.0, 0.7, 0.5), 12.0, 8.0)
    # The mirror room's fill (its own lights are dimmed copies; this evens it out).
    k.light("Glass fill", g, (2 * X1 + 3.0, 3.0, -1.0), "Point", (0.85, 0.75, 0.7), 40.0, 12.0)
    k.light("Glass fill, pool end", g, (2 * X1 - PT[0] - 1.5, 2.9, 3.6), "Point", (0.8, 0.9, 0.75), 25.0, 8.0)
    k.light("Glass fill, stage end", g, (2 * X1 - 2.5, 2.9, 5.0), "Point", (0.9, 0.6, 0.8), 25.0, 8.0)


def markers(s, root):
    k = Kit(s)
    marks = k.group("Venue markers", root)
    s.info(marks, "The Dead End Dive Bar", "Drumsmith", outdoor=False, room_back=Z0, room_ceiling=CEIL, half_width=6.5,
           desk_z=-8.6, ambient=(0.022, 0.016, 0.012), fog_color=(0.035, 0.024, 0.016), haze=1.15)
    s.spot(marks, "Drummer", (3.0, STAGE_Y, 7.4))
    s.spot(marks, "Bass", (0.75, STAGE_Y, 5.15), -22)
    s.crowd("Front of the stage", marks, (0.9, 0, 0.2), 3.6, 2.4, 6, figures="Posed")
    s.crowd("By the bar", marks, (2.6, 0, -3.2), 1.6, 3.0, 3, jitter=0.8)
    s.crowd("Back of the room", marks, (-0.4, 0, -4.2), 4.4, 3.0, 5, jitter=0.9)
    cams = k.group("Cameras", marks)
    for name, kind, eye, aim, fov, tag in [
        ("Wide from the door", "Wide", (-2.2, 3.05, -9.7), (0.9, 0.7, 4.6), 60, "wide"),
        ("Crane over the pool lamp", "Crane", (-5.2, 3.1, -1.6), (1.8, 0.9, 5.6), 58, "crane"),
        ("Desk long lens", "Desk", (1.0, 2.0, -9.8), (2.2, 1.6, 6.5), 30, "desk"),
        ("Kit and the bass combo", "Close", (1.3, 1.55, 4.7), (3.0, 1.0, 7.1), 50, "kit"),
        ("Bassist", "Close", (-0.4, 1.5, 3.4), (0.75, 1.3, 5.15), 50, "bass"),
        ("The pool table", "Custom", (-0.9, 2.2, 1.4), (-3.3, 0.8, 5.0), 52, "pool-table"),
        ("The mirror", "Custom", (2.2, 1.75, -5.6), (6.5, 1.65, -0.8), 50, "mirror"),
        ("First listener", "Custom", (2.0, 1.6, -1.6), (3.9, 1.15, 1.3), 46, "first-listener"),
        ("The door take", "Custom", (3.0, 1.85, -2.6), (5.0, 1.3, 0.4), 44, "door-take"),
        ("Crowd from the stage", "Custom", (1.6, 2.1, 4.6), (-0.5, 1.0, -6.0), 60, "crowd"),
    ]:
        s.camera_spot(name, cams, eye, aim, kind, fov, tag)
    for i, (eye, aim, fov) in enumerate([((-5.7, 1.65, -9.6), (-4.6, 1.5, -6.0), 64), ((-4.9, 1.7, -8.4), (-2.0, 1.55, -3.0), 62),
                                         ((-3.9, 1.72, -6.9), (0.6, 1.5, 0.0), 60), ((-2.6, 1.78, -5.2), (2.0, 1.4, 4.5), 58),
                                         ((-1.4, 1.85, -3.6), (2.6, 1.35, 6.4), 56)]):
        s.camera_spot(f"Arrival {i + 1:02}", cams, eye, aim, "Custom", fov, f"arrival/{i + 1:02}")


def build():
    write_motion()
    s = Scene("story-dive-bar-s04")
    root = s.group("The Dead End Dive Bar")
    room = s.group("The room", root)
    furnish(Kit(s), room)
    right_wall(s, root)
    glass = s.group("In the back-bar mirror", root)
    mk = Kit(s, mirror=True)
    furnish(mk, glass)
    reflected_audience(mk, glass)
    house_lights(s, root)
    show_lights(s, root)
    markers(s, root)
    return s


def main():
    if "--no-art" not in sys.argv:
        art.all_textures()
    art.league_torsos()
    scene = build()
    scene.write(os.path.join(FOLDER, ID + ".lvl"))
    write_venue_json(FOLDER, "The Dead End Dive Bar", ID + ".lvl", preview="Preview.jpg" if os.path.exists(
        os.path.join(FOLDER, "Preview.jpg")) else None, ambience="Assets/Sounds/crowd.mp3")
    meta = json.load(open(os.path.join(FOLDER, "venue.json")))
    meta["AmbienceVolume"] = 0.55
    with open(os.path.join(FOLDER, "venue.json"), "w", newline="\n") as f:
        json.dump(meta, f, indent=1)
        f.write("\n")
    print(f"{len(scene.entities)} entities in {FOLDER}")


if __name__ == "__main__":
    main()
