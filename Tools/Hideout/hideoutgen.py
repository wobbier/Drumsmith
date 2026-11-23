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


def speaker(e, low_cut=20.0, high_cut=20000.0, honk=0.0, honk_at=1500.0, width=1.0, drive=0.0):
    """HideoutSpeaker on the radio's station: what the radio plays through, heard standing at it.
    The defaults are the song as it is; the radio gets better with the room."""
    e.add({"Type": "HideoutSpeaker", "LowCut": _r(low_cut), "HighCut": _r(high_cut), "Honk": _r(honk), "HonkAt": _r(honk_at),
           "Width": _r(width), "Drive": _r(drive)})
    return e


def slot(s, parent, name, slot_name, pos=(0, 0, 0), view=None):
    """An item's place. view: where the new items' tour camera stands, from the middle of the
    item's pieces (None: worked out, back toward the doorway)."""
    e = s.entity(name, parent, pos)
    comp = {"Type": "HideoutItemSlot", "Slot": slot_name}
    if view:
        comp["ViewOffset"] = [round(v, 4) for v in view]
    e.add(comp)
    return e


def drummer(s, parent, pos, yaw=180.0, cast=0, energy=0.55, finish=None, metallic=0.0, roughness=0.4):
    """The player's drummer and kit (Band): pos is the throne, the kit is in front, yaw 180 faces -z.
    finish: the drum shells' lacquer (None keeps the kit's oxblood); the kit gets better with the room."""
    e = s.entity("Drummer", parent, pos)
    comp = {"Type": "HideoutDrummer", "Cast": int(cast), "Yaw": _r(yaw), "Energy": _r(energy)}
    if finish:
        comp.update({"Finish": vec(finish), "FinishMetallic": _r(metallic), "FinishRoughness": _r(roughness)})
    e.add(comp)
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


def band_name_text(s, parent, name, pos, size, colour, fit=9, weight=1, font=None):
    """The band's name as world text (TextRenderers facing -z), shown once the band has one, in
    marker (Permanent Marker); `weight` copies a hair apart make the strokes heavier still (a
    spray can's). Returns the group: rotate it to tilt the lot."""
    group = s.entity(name, parent, pos)
    offsets = [(0.0, 0.0)] + [(size * 0.012 * math.cos(k * 2.1), size * 0.012 * math.sin(k * 2.1)) for k in range(weight - 1)]
    for i, (dx, dy) in enumerate(offsets):
        e = s.entity(f"{name} {i}", group, (dx, dy, -0.0005 * i))
        e.add({"Type": "TextRenderer", "Text": "", "Size": _r(size), "Alignment": "Center", "Anchor": "Middle", "Color": vec(colour),
               "Opacity": 1.0, "Lit": True, "Font": font or MARKER})
        band_name(e, "Named", fit)
    return group


# ---- words in the room ------------------------------------------------------------------------

MARKER = "Assets/Fonts/PermanentMarker-Regular.ttf"     # a fat marker, spray paint, tape labels
PEN = "Assets/Fonts/GochiHand-Regular.ttf"              # a ballpoint: notes, lists, the setlist
FACING = {"-z": (0.0, 0.0), "+z": (0.0, 180.0), "+x": (0.0, -90.0), "-x": (0.0, 90.0), "up": (90.0, 0.0)}


def scrawl(s, parent, name, pos, text, size, colour, facing="-z", font=PEN, lit=True, align="Center", anchor="Middle",
           tilt=0.0, spin=0.0, spacing=1.0):
    """Writing in the room (a TextRenderer): facing is the way the words look ('-z' at the camera
    from the back wall, '+x' off the left wall, 'up' off the floor); tilt turns them on the
    surface, degrees; spin turns floor text about the vertical."""
    pitch, yaw = FACING[facing]
    if facing == "up":
        yaw = spin
    e = s.entity(name, parent, pos, (pitch, yaw, tilt))
    comp = {"Type": "TextRenderer", "Text": text, "Size": _r(size), "Alignment": align, "Anchor": anchor, "Color": vec(colour),
            "Opacity": 1.0, "Lit": bool(lit)}
    if font:
        comp["Font"] = font
    if spacing != 1.0:
        comp["LineSpacing"] = _r(spacing)
    e.add(comp)
    return e


def readout(e, show, line=0, item="", prefix="", max_letters=0, upper=False, scroll=0.0):
    """HideoutReadout on a scrawl: its words come from the player (the radio's song, the recent
    songs, a wishlist item, a count, the time)."""
    comp = {"Type": "HideoutReadout", "Show": show, "Line": int(line), "Prefix": prefix, "MaxLetters": int(max_letters),
            "Upper": bool(upper), "Scroll": _r(scroll)}
    if item:
        comp["Item"] = item
    e.add(comp)
    return e


def when(e, show):
    """HideoutWhen: only by Day or Night (the player's clock), only MovingIn (the first visit
    after moving into the room) or only once Settled."""
    e.add({"Type": "HideoutWhen", "Show": show})
    return e


def stand_in(s, parent, name, slot_name, pos=(0, 0, 0)):
    """What's there until a slot's item is unlocked (an outline in tape, a note): the slot's
    WhenLocked side."""
    e = s.entity(name, parent, pos)
    e.add({"Type": "HideoutItemSlot", "Slot": slot_name, "WhenLocked": True})
    return e


def tape_outline(s, parent, name, centre, width, depth, facing="up", colour=(0.86, 0.8, 0.62), tape=0.024):
    """A rectangle of masking tape (where something will go): on a floor or bench ('up'), or on a
    wall facing '-z', '+x' or '-x'."""
    x, y, z = centre
    pieces = []
    if facing == "up":
        for dz in (-depth / 2, depth / 2):
            pieces.append(((x, y, z + dz), (width + tape, 0.002, tape)))
        for dx in (-width / 2, width / 2):
            pieces.append(((x + dx, y, z), (tape, 0.002, depth)))
    elif facing == "-z":
        for dy in (-depth / 2, depth / 2):
            pieces.append(((x, y + dy, z), (width + tape, tape, 0.002)))
        for dx in (-width / 2, width / 2):
            pieces.append(((x + dx, y, z), (tape, depth, 0.002)))
    else:
        for dy in (-depth / 2, depth / 2):
            pieces.append(((x, y + dy, z), (0.002, tape, width + tape)))
        for dz in (-width / 2, width / 2):
            pieces.append(((x, y, z + dz), (0.002, depth, tape)))
    for i, (p, size) in enumerate(pieces):
        s.box(f"{name} {i}", parent, p, size, colour, rough=0.9, shadows=False)


def clock_hands(s, parent, centre, facing, radius, colour=(0.05, 0.05, 0.05), second=True):
    """A clock's hands on the player's time (HideoutMotion Hour / Minute / Second), turning about
    the face's normal. facing: '-z', '+x' or '-x' (the way the face looks)."""
    normal = {"-z": (0, 0, -1), "+x": (1, 0, 0), "-x": (-1, 0, 0)}[facing]
    # Clockwise to someone looking at the face (the engine turns a positive angle clockwise
    # looking down its axis, so the axis is the face's own normal).
    axis = normal
    out = 0.004
    hands = (("Hour", 0.55, 0.012, 0), ("Minute", 0.85, 0.008, 1)) + ((("Second", 0.9, 0.003, 2),) if second else ())
    for kind, length, width, layer in hands:
        pivot = s.entity(f"{kind} Hand", parent, tuple(centre[k] + normal[k] * (out + 0.003 * layer) for k in range(3)))
        motion(pivot, kind, axis=axis)
        hand_colour = (0.75, 0.08, 0.06) if kind == "Second" else colour
        size = (width, radius * length, 0.003) if facing == "-z" else (0.003, radius * length, width)
        s.box(f"{kind} Hand Bar", pivot, (0.0, radius * length * 0.4, 0.0), size, hand_colour, shadows=False)


def setlist(s, parent, centre, yaw, songs=5):
    """A setlist taped down (SetlistBlank, title only) with the last songs played written on it."""
    textured(s.box("Setlist", parent, centre, (0.24, 0.002, 0.34), (1, 1, 1), rot=(0, yaw, 0), shadows=False), "SetlistBlank")
    c, si = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    for i in range(songs):
        dx, dz = -0.1, 0.075 - i * 0.05
        p = (centre[0] + dx * c + dz * si, centre[1] + 0.002, centre[2] - dx * si + dz * c)
        readout(scrawl(s, parent, f"Setlist Song {i}", p, "", 0.034, (0.1, 0.1, 0.14), facing="up", spin=yaw, align="Left", font=MARKER),
                "RecentSong", line=i, prefix=f"{i + 1}. ", max_letters=13)
    for k, (dx, dz) in enumerate(((-0.1, 0.16), (0.1, 0.16), (-0.1, -0.16), (0.1, -0.16))):
        s.box(f"Setlist Tape {k}", parent, (centre[0] + dx * c + dz * si, centre[1] + 0.001, centre[2] - dx * si + dz * c), (0.07, 0.002, 0.025),
              (0.86, 0.8, 0.62), rot=(0, yaw + 40 * (1 if k % 3 else -1), 0), shadows=False)


def boombox_display(s, parent, centre, facing="-x", width=0.24):
    """A radio's display (a green LCD) scrolling the song it's playing (HideoutReadout NowPlaying)."""
    size = (0.004, 0.034, width) if facing in ("-x", "+x") else (width, 0.034, 0.004)
    s.box("Display", parent, centre, size, (0.02, 0.05, 0.03), emissive=(0.05, 0.25, 0.12), emissive_intensity=1.0, shadows=False)
    out = {"-x": (-0.004, 0, 0), "+x": (0.004, 0, 0), "-z": (0, 0, -0.004)}[facing]
    p = tuple(centre[k] + out[k] for k in range(3))
    readout(scrawl(s, parent, "Now Playing", p, "", 0.024, (0.55, 1.0, 0.7), facing=facing, font="Assets/Fonts/JetBrainsMono-Regular.ttf",
                   lit=False), "NowPlaying", max_letters=int(width / 0.0172), upper=True, scroll=0.22)


def tally(s, parent, centre, facing="-x", ink=(0.12, 0.16, 0.42)):
    """The counts on a scrap of paper: songs played, full combos, gigs (HideoutReadout)."""
    group = s.group("Tally", parent, centre)
    size = (0.003, 0.22, 0.3) if facing in ("-x", "+x") else (0.3, 0.22, 0.003)
    s.box("Tally Paper", group, (0.0, 0.0, 0.0), size, (0.98, 0.97, 0.92), rot=(-2, 0, 0) if facing in ("-x", "+x") else (0, 0, -2), rough=0.9,
          shadows=False)
    off = {"-x": (-0.003, 0, 0.13), "+x": (0.003, 0, -0.13), "-z": (-0.13, 0, -0.003)}[facing]
    for i, (source, prefix) in enumerate((("SongsPlayed", "songs: "), ("FullCombos", "full combos: "), ("GigsPlayed", "gigs: "))):
        p = (off[0], 0.06 - i * 0.058, off[2])
        readout(scrawl(s, group, f"Tally {source}", p, "", 0.04, ink, facing=facing, align="Left", tilt=-2.0, font=MARKER), source, prefix=prefix)
    return group


def cat(s, parent, pos, yaw=0.0, fur=(0.85, 0.48, 0.2), stripes=(0.6, 0.3, 0.1)):
    """The cat, asleep (breathing, its tail flicking). It moves with the band from room to room.
    pos: where it lies; yaw turns it (0: its head toward -z)."""
    group = s.group("Cat", parent, pos)
    group.components[0]["Rotation"] = [0.0, yaw, 0.0]
    body = s.box("Cat Body", group, (0.0, 0.08, 0.0), (0.3, 0.17, 0.44), fur, shape="Sphere", rough=0.95)
    motion(body, "Breathe", amount=0.07, speed=0.22, axis=(0.3, 1.0, 0.0))
    s.box("Cat Head", group, (0.02, 0.1, -0.24), (0.17, 0.14, 0.15), fur, shape="Sphere", rough=0.95)
    for side in (-1, 1):
        s.box(f"Cat Ear {side}", group, (0.02 + side * 0.05, 0.18, -0.25), (0.05, 0.05, 0.02), tuple(c * 0.94 for c in fur), rot=(0, 0, 45),
              rough=0.95)
    tail = s.entity("Cat Tail Root", group, (-0.05, 0.03, 0.2))
    motion(tail, "Sway", amount=14.0, speed=0.13, axis=(0, 1, 0))
    rod(s, tail, "Cat Tail", (0.0, 0.0, 0.0), (0.17, -0.01, 0.12), 0.04, tuple(c * 0.94 for c in fur))
    s.box("Cat Stripes", group, (0.0, 0.15, 0.05), (0.2, 0.04, 0.3), stripes, shape="Sphere", rough=0.95, shadows=False)
    return group


def flyer_name(s, parent, centre, facing, tilt=0.0, ink=(0.7, 0.06, 0.08)):
    """The band's name scrawled along the bottom of a gig's flyer once it's been played
    ("feat. THE RIMSHOTS"): centre is the flyer's (0.27 x 0.36 m, as gig_board makes them)."""
    out = {"+x": (0.004, 0.0, 0.0), "-x": (-0.004, 0.0, 0.0), "-z": (0.0, 0.0, -0.004)}[facing]
    p = (centre[0] + out[0], centre[1] - 0.135, centre[2] + out[2])
    readout(scrawl(s, parent, "Band On The Flyer", p, "", 0.02, ink, facing=facing, font=MARKER, tilt=tilt - 4.0), "BandName", prefix="feat. ",
            max_letters=16, upper=True)
