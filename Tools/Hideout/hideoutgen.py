"""hideoutgen: helpers for writing hideout rooms on top of Tools/Venues/venuegen.py (which this
only reads from): the hideout markers (Game/Source/Components/Hideout/HideoutMarkers.h), textured
primitives, posters, motions, lights that can be animated, and particles.

Textures are Assets/Hideout/Textures/<Name>.png (Tools/Hideout/make_textures.py writes them).
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Venues"))
from venuegen import Scene, look_rotation, vec, _r  # noqa: E402,F401

TEX = "Assets/Hideout/Textures/"

BLACK = (0.04, 0.04, 0.045)
CHROME = (0.75, 0.75, 0.78)
STEEL = (0.42, 0.43, 0.45)
BRASS = (0.78, 0.6, 0.25)
GOLD = (1.0, 0.78, 0.3)
WHITE = (0.9, 0.9, 0.88)
OFFWHITE = (0.82, 0.8, 0.74)
WOOD = (0.45, 0.3, 0.18)
CORK = (0.62, 0.45, 0.28)


# ---- markers ---------------------------------------------------------------------------------

def station(s, parent, name, kind, pos, view_offset, fov=45.0, label=""):
    e = s.entity(name, parent, pos)
    comp = {"Type": "HideoutStation", "Station": kind, "ViewOffset": [round(v, 4) for v in view_offset],
            "FieldOfView": fov}
    if label:
        comp["Label"] = label
    e.add(comp)
    return e


def slot(s, parent, name, slot_name, pos=(0, 0, 0)):
    e = s.entity(name, parent, pos)
    e.add({"Type": "HideoutItemSlot", "Slot": slot_name})
    return e


def drummer(s, parent, pos, yaw=180.0, cast=0, energy=0.55):
    """The player's drummer and kit (Band): pos is the throne, the kit is in front, yaw 180 faces -z."""
    e = s.entity("Drummer", parent, pos)
    e.add({"Type": "HideoutDrummer", "Cast": int(cast), "Yaw": _r(yaw), "Energy": _r(energy)})
    return e


def view(s, parent, eye, target, fov, intro_eye=None, intro_target=None):
    """The overview camera; intro_eye / intro_target: where the session's first visit starts from."""
    e = s.entity("Overview", parent, eye, look_rotation(eye, target))
    comp = {"Type": "HideoutView", "FieldOfView": _r(fov)}
    if intro_eye:
        comp["IntroEye"] = vec(intro_eye)
        comp["IntroTarget"] = vec(intro_target or target)
    e.add(comp)
    return e


def motion(e, kind, amount=1.0, speed=1.0, axis=(0, 0, 1), phase=0.0, music=False):
    """HideoutMotion on an entity: Sway | Flicker | Pulse | Spin | Breathe | Blink | Bob."""
    e.add({"Type": "HideoutMotion", "Motion": kind, "Amount": _r(amount), "Speed": _r(speed), "Axis": vec(axis),
           "Phase": _r(phase), "Music": bool(music)})
    return e


# ---- surfaces --------------------------------------------------------------------------------

def material(e):
    for comp in e.components:
        if comp.get("Type") == "Mesh":
            return comp["Material"]
    raise ValueError("no mesh on " + e.name)


def textured(e, name, tile=(1.0, 1.0), emissive=False, emissive_intensity=1.0, tint=(1, 1, 1)):
    """Puts Assets/Hideout/Textures/<name>.png on a primitive, upright, repeated tile times."""
    m = material(e)
    m["DiffuseColor"] = vec(tint)
    m["Textures"] = {"Diffuse": {"Path": TEX + name + ".png"}}
    if emissive:
        m["Textures"]["Emissive"] = {"Path": TEX + name + ".png"}
        m["EmissiveColor"] = [1.0, 1.0, 1.0]
        m["EmissiveIntensity"] = _r(emissive_intensity)
    m["Tiling"] = [_r(tile[0]), _r(-tile[1])]
    m["Offset"] = [0.0, _r(tile[1])]
    return e


def poster(s, parent, name, texture, center, width, height, facing, tilt=0.0, glow=0.0, thick=0.004):
    """A sheet of paper on a wall. facing: the way the picture looks, '+x' | '-x' | '+z' | '-z'
    (a poster on the back wall looks '-z', at the room). tilt: degrees off level, taped crooked."""
    if facing in ("+x", "-x"):
        size = (thick, height, width)
        rot = (tilt, 0, 0)
    else:
        size = (width, height, thick)
        rot = (0, 0, tilt)
    e = s.box(name, parent, center, size, (1, 1, 1), rot=rot, rough=0.85, shadows=False)
    textured(e, texture, emissive=glow > 0, emissive_intensity=glow)
    return e


def plank(s, parent, name, a, b, thick, width, color, texture=None, tile=(1, 1)):
    """A box from point a to point b (a rail, a pipe run, a stair stringer)."""
    dx, dy, dz = (b[i] - a[i] for i in range(3))
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    centre = tuple((a[i] + b[i]) / 2 for i in range(3))
    rot = look_rotation(a, b)    # local +Z along a->b
    e = s.box(name, parent, centre, (width, thick, length), color, rot=rot)
    if texture:
        textured(e, texture, tile)
    return e


def rod(s, parent, name, a, b, diameter, color, metallic=0.0, rough=0.6, emissive=None, emissive_intensity=1.0, shadows=True):
    """A cylinder from a to b (a pipe, a stick, a cable)."""
    dx, dy, dz = (b[i] - a[i] for i in range(3))
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    centre = tuple((a[i] + b[i]) / 2 for i in range(3))
    pitch, yaw, _ = look_rotation(a, b)
    # The cylinder's axis is local +Y; tip it forward 90 so it lies along the look direction.
    return s.box(name, parent, centre, (diameter, length, diameter), color, rot=(pitch + 90.0, yaw, 0.0), shape="Cylinder",
                 metallic=metallic, rough=rough, emissive=emissive, emissive_intensity=emissive_intensity, shadows=shadows)


# ---- light and air ---------------------------------------------------------------------------

def light(s, parent, name, pos, kind="Point", color=(1, 1, 1), intensity=1.0, range_=6.0, rot=(0, 0, 0), inner=20.0,
          outer=30.0, shadows=False, volumetric=0.0, length=None, radius=None, rect=None):
    e = s.light(name, parent, pos, kind, color, intensity, range_, rot=rot, inner=inner, outer=outer, shadows=shadows)
    comp = e.components[-1]
    comp["VolumetricMultiplier"] = _r(volumetric)
    if length is not None:
        comp["Length"] = _r(length)
    if radius is not None:
        comp["Radius"] = _r(radius)
    if rect is not None:
        comp["RectangleWidth"] = _r(rect[0])
        comp["RectangleHeight"] = _r(rect[1])
    return e


def dust(s, parent, name, center, box, count=220, rate=40.0):
    """Motes hanging in the air, lit by whatever light they drift through."""
    e = s.entity(name, parent, center)
    e.add({"Type": "ParticleSystem", "Looping": True, "EmissionRate": _r(rate), "MaxParticles": int(count),
           "SimulationSpace": "World", "Shape": "Box", "BoxSize": vec(box), "Lifetime": [6.0, 11.0], "Speed": [0.0, 0.03],
           "Size": [0.006, 0.014], "StartColor": [1.0, 0.95, 0.85], "StartColor2": [0.9, 0.9, 1.0], "StartAlpha": 0.55,
           "EndAlpha": 0.0, "FadeIn": 0.25, "Intensity": 1.0, "Gravity": -0.0015, "Drag": 0.5, "NoiseStrength": 0.04,
           "NoiseFrequency": 0.6, "Blend": "Alpha", "Lit": True, "Simulation": "CPU", "SoftParticleDistance": 0})
    return e


def glow_light(e, kind="Point", color=(1, 1, 1), intensity=1.0, range_=4.0, shadows=False, volumetric=0.0, length=None,
               radius=None, rot_light=None):
    """Adds a Light to a glowing mesh's own entity, so one HideoutMotion moves both together."""
    comp = {"Type": "Light", "LightType": kind, "Color": vec(color), "Intensity": _r(intensity), "Range": _r(range_),
            "VolumetricMultiplier": _r(volumetric)}
    if shadows:
        comp["CastShadows"] = True
    if length is not None:
        comp["Length"] = _r(length)
    if radius is not None:
        comp["Radius"] = _r(radius)
    e.add(comp)
    return e


def sound(s, parent, name, pos, clip, volume=0.5, near=0.5, far=6.0):
    """A looping 3D sound in the room (Assets/Hideout/Sounds/<clip>.wav): full volume within near
    metres, gone by far."""
    e = s.entity(name, parent, pos)
    e.add({"Type": "AudioSource", "FilePath": "Assets/Hideout/Sounds/" + clip + ".wav", "Bus": "SFX", "Volume": _r(volume),
           "PlayOnAwake": True, "Loop": True, "SpatialBlend": 1.0, "MinDistance": _r(near), "MaxDistance": _r(far),
           "Rolloff": "Linear", "Occlusion": False, "DopplerLevel": 0.0})
    return e


def band_name(e, when, fit=9):
    """HideoutBandName: shown only while the band is Unnamed, or only once it's Named."""
    e.add({"Type": "HideoutBandName", "Show": when, "FitLetters": int(fit)})
    return e


def band_name_text(s, parent, name, pos, size, colour, fit=9, weight=3):
    """The band's name as world text (TextRenderers facing -z), shown once the band has one. The
    only font is the engine's Inter regular, so `weight` copies a hair apart make the strokes
    heavier (a marker's, a spray can's). Returns the group: rotate it to tilt the lot."""
    group = s.entity(name, parent, pos)
    offsets = [(0.0, 0.0)] + [(size * 0.012 * math.cos(k * 2.1), size * 0.012 * math.sin(k * 2.1)) for k in range(weight - 1)]
    for i, (dx, dy) in enumerate(offsets):
        e = s.entity(f"{name} {i}", group, (dx, dy, -0.0005 * i))
        e.add({"Type": "TextRenderer", "Text": "", "Size": _r(size), "Alignment": "Center", "Anchor": "Middle", "Color": vec(colour),
               "Opacity": 1.0, "Lit": True})
        band_name(e, "Named", fit)
    return group
