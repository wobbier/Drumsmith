"""venuegen: a tiny stdlib-only writer for MitchEngine scene format v2 (.lvl), used to generate
venue scenes (Assets/Venues/<Id>/). Output is deterministic: GUIDs derive from a seed and the
entity's creation order, and JSON is dumped with a fixed layout, so rerunning a generator gives
byte-identical files.

Conventions (see Game/Source/Components/Venue/VenueMarkers.h):
  metres; +x is the crowd's right, +y up, +z from the crowd toward the band and back wall.
  Transform "Rotation" is Euler DEGREES (x, y, z); glm applies them as Rz * Ry * Rx, so a
  yaw+pitch pair is "pitch first, then yaw", which is what look_at() produces.
  A camera, Light or VenueCameraSpot looks along local +Z; positive X rotation pitches DOWN.
  A VenueSpot (performer) faces local -Z; a VenueCrowdArea faces local +Z.
  The engine's primitive cube is 2 m on each side (half extent 1), so box() takes metres and
  halves them into Transform.Scale.
"""
import hashlib
import json
import math
import os


def _r(v):
    """Round floats so the file doesn't carry 0.30000000000000004 noise."""
    return round(float(v), 4) + 0.0


def vec(v):
    return [_r(x) for x in v]


def look_rotation(eye, target):
    """Euler degrees [pitch, yaw, 0] that make local +Z point from eye to target."""
    dx, dy, dz = (target[i] - eye[i] for i in range(3))
    horiz = math.hypot(dx, dz)
    yaw = math.degrees(math.atan2(dx, dz))
    pitch = math.degrees(math.atan2(-dy, horiz))  # positive = look down
    return [pitch, yaw, 0.0]


def yaw_rotation(deg):
    return [0.0, deg, 0.0]


class Entity:
    def __init__(self, scene, name, parent, guid):
        self.scene = scene
        self.name = name
        self.parent = parent
        self.guid = guid
        self.components = []

    def add(self, comp):
        self.components.append(comp)
        return self

    def to_json(self):
        d = {"GUID": self.guid, "Name": self.name, "DestroyOnLoad": True}
        if self.parent is not None:
            d["Parent"] = self.parent.guid
        d["Components"] = self.components
        return d


class Scene:
    def __init__(self, seed):
        self.seed = seed
        self.entities = []
        self._guids = set()

    # ---- entities --------------------------------------------------------------------------
    def _guid(self, name):
        n = 0
        while True:
            h = hashlib.sha1(f"{self.seed}:{len(self.entities)}:{name}:{n}".encode()).hexdigest()[:16]
            # Keep the top bit clear so a signed 64-bit read never goes negative.
            h = format(int(h, 16) & 0x7FFFFFFFFFFFFFFF, "016x")
            if h not in self._guids and h != "0" * 16:
                self._guids.add(h)
                return h
            n += 1

    def entity(self, name, parent=None, pos=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
        e = Entity(self, name, parent, self._guid(name))
        e.add(transform(pos, rot, scale))
        self.entities.append(e)
        return e

    def group(self, name, parent=None, pos=(0, 0, 0)):
        """An empty named parent so the hierarchy is navigable in Havana."""
        return self.entity(name, parent, pos)

    # ---- geometry --------------------------------------------------------------------------
    def box(self, name, parent, pos, size, color, rot=(0, 0, 0), rough=0.9, metallic=0.0,
            emissive=None, emissive_intensity=1.0, shadows=True, shape="Cube"):
        """A coloured primitive (shape Cube | Sphere | Cylinder | Capsule | Plane; all are 2 m across
        at scale 1, so the size is the full extent in metres). pos is the CENTRE."""
        e = self.entity(name, parent, pos, rot, [s / 2.0 for s in size])
        mat = {"Type": "StandardMaterial", "DiffuseColor": vec(color), "Metallic": _r(metallic),
               "Roughness": _r(rough)}
        if emissive is not None:
            mat["EmissiveColor"] = vec(emissive)
            mat["EmissiveIntensity"] = _r(emissive_intensity)
        e.add({"Type": "Mesh", "MeshType": shape, "CastShadows": shadows, "Material": mat})
        return e

    def slab(self, name, parent, x0, x1, y0, y1, z0, z1, color, **kw):
        """A box from min/max corners (handy for floors and walls)."""
        return self.box(name, parent, ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2),
                        (x1 - x0, y1 - y0, z1 - z0), color, **kw)

    def prop(self, name, parent, model, pos, yaw=0.0, scale=1.0):
        """A model prop by project-relative path (e.g. Assets/Models/Venue/Keg.obj). The Model
        component builds its own Mesh children from the file and its .mtl."""
        e = self.entity(name, parent, pos, yaw_rotation(yaw), (scale, scale, scale))
        e.add({"Type": "Model", "ModelPath": model})
        return e

    # ---- lights ----------------------------------------------------------------------------
    def light(self, name, parent, pos, kind="Point", color=(1, 1, 1), intensity=1.0, range_=10.0,
              rot=(0, 0, 0), inner=20.0, outer=30.0, shadows=False, show=None, group=0):
        """An engine Light. show = None for a plain light, or a VenueShowLight role name.
        intensity is the engine's (a point or spot falls off as intensity / d^2: a few hundred
        lights a band from 3-4 m); for a cued light it is its level at full."""
        e = self.entity(name, parent, pos, rot)
        comp = {"Type": "Light", "LightType": kind, "Color": vec(color), "Intensity": _r(intensity),
                "Range": _r(range_)}
        if kind == "Spot":
            comp["InnerConeAngle"] = _r(inner)
            comp["OuterConeAngle"] = _r(outer)
        if kind == "Directional":
            comp["DirectionalSource"] = "Manual"
        if shadows:
            comp["CastShadows"] = True
        e.add(comp)
        if show is not None:
            e.add({"Type": "VenueShowLight", "Kind": show, "Group": int(group)})
        return e

    # ---- markers ---------------------------------------------------------------------------
    def info(self, parent, name, author, outdoor=False, room_back=-1000.0, room_ceiling=1000.0,
             half_width=30.0, desk_z=-22.0, build_stage=False, build_set=False, build_rig=False,
             build_fx=False, entity_name="VenueInfo", ambient=(0.0, 0.0, 0.0),
             fog_color=(0.01, 0.01, 0.015), haze=1.0, sky_time=22.0, moon=1.0):
        """The room and its look. ambient: indoors, the colour behind everything (it also lights
        the room a little). fog_color: the light the haze scatters. haze: its thickness (1 the
        usual). sky_time / moon: out of doors, the night sky's hour and the moon's brightness."""
        e = self.entity(entity_name, parent)
        e.add({"Type": "VenueInfo", "Name": name, "Author": author, "Outdoor": bool(outdoor),
               "RoomBack": _r(room_back), "RoomCeiling": _r(room_ceiling),
               "RoomHalfWidth": _r(half_width), "DeskZ": _r(desk_z),
               "BuildStage": build_stage, "BuildSet": build_set, "BuildRig": build_rig,
               "BuildFx": build_fx, "AmbientColor": vec(ambient), "FogColor": vec(fog_color),
               "Haze": _r(haze), "SkyTime": _r(sky_time), "MoonBrightness": _r(moon)})
        return e

    def spot(self, parent, member, pos, yaw=0.0):
        """member: Drummer | Guitar | Bass | Vocals | Keys. pos is the feet; yaw 0 faces the crowd."""
        e = self.entity(f"Spot_{member}", parent, pos, yaw_rotation(yaw))
        e.add({"Type": "VenueSpot", "Member": member})
        return e

    def crowd(self, name, parent, center, width, depth, heads, jitter=0.5, yaw=0.0, figures="Mob"):
        """A crowd rectangle: centre, full width (x) and depth (z) in metres. figures: Mob (cheap
        instanced figures) | Posed (the full front-row figures; fill from the +Z edge back)."""
        e = self.entity(name, parent, center, yaw_rotation(yaw), (width, 1.0, depth))
        c = {"Type": "VenueCrowdArea"}
        if figures != "Mob":
            c["Figures"] = figures
        c.update({"HeadCount": int(heads), "Jitter": _r(jitter)})
        e.add(c)
        return e

    def camera_spot(self, name, parent, eye, target, shot="Wide", fov=55.0, tag=""):
        """shot: Wide | Desk | Crane | Close | Custom. Aimed at target."""
        e = self.entity(name, parent, eye, look_rotation(eye, target))
        e.add({"Type": "VenueCameraSpot", "Shot": shot, "FieldOfView": _r(fov), "Tag": tag})
        return e

    def screen(self, name, parent, center, width, height, feed="Stage", emissive=2.0, yaw=0.0):
        """A feed quad. The picture faces local -Z, so yaw 0 faces the crowd. Also gets a Plane-less
        dark Cube backing is NOT added: put a box behind it if you want a frame."""
        e = self.entity(name, parent, center, yaw_rotation(yaw), (width, height, 1.0))
        e.add({"Type": "VenueScreen", "Source": feed, "Emissive": _r(emissive)})
        return e

    def story(self, name, parent, flag, when_set=True, fade=0.75, pos=(0, 0, 0)):
        """A story-mode group (VenueStory): its children show only while the story flag is set
        (when_set False: only until it is set). They grow from the group's pivot, so put pos where
        the thing stands. Plain Lights under it dim with it; a VenueShowLight under it is cued only
        while it shows, and a ParticleSystem under it emits only while it shows."""
        e = self.entity(name, parent, pos)
        e.add({"Type": "VenueStory", "Flag": flag, "WhenSet": bool(when_set), "FadeSeconds": _r(fade)})
        return e

    def camera(self, name, parent, eye, target, fov=55.0, far=400.0):
        """A real engine Camera (for debug renders only; venue scenes must not ship a current one)."""
        e = self.entity(name, parent, eye, look_rotation(eye, target))
        e.add({"Type": "Camera", "ClearType": "Color", "ClearColor": [0.02, 0.03, 0.06],
               "IsCurrent": True, "Near": 0.1, "Far": _r(far), "FieldOfView": _r(fov)})
        return e

    # ---- output ----------------------------------------------------------------------------
    def to_json(self):
        return {"Version": 2, "Cores": [], "Entities": [e.to_json() for e in self.entities]}

    def write(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="\n") as f:
            json.dump(self.to_json(), f, indent=1)
            f.write("\n")


def transform(pos=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    return {"Type": "Transform", "Position": vec(pos), "Rotation": vec(rot), "Scale": vec(scale)}


def write_venue_json(folder, name, scene_file, author="Drumsmith", preview=None, version=1, ambience=None):
    d = {"Name": name, "Author": author, "Scene": scene_file}
    if preview:
        d["Preview"] = preview
    if ambience:
        d["Ambience"] = ambience
    d["Version"] = version
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "venue.json"), "w", newline="\n") as f:
        json.dump(d, f, indent=1)
        f.write("\n")


def repo_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
