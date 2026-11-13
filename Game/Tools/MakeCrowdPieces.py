"""Lists the rigged characters under Assets/Models/People and cuts each into the rigid pieces the
crowd is built from (Docs/Venue-and-Band.md -> The crowd).

The crowd is too many figures to skin (skinned meshes draw one by one), so each is five rigid
pieces of a character instead, which instance: legs (with the hips), torso, head and two arms.
A piece is the faces whose vertices mostly follow that part of the skeleton. Each is written as
an OBJ around its own pivot (feet, hips, neck, shoulder; the arms turned from the T-pose to hang
straight down), at full detail and decimated (_Lo) for figures further back, plus Body_Lo (legs,
torso and head as one) for the back of the house. Every FBX in the folder with the Rigify
skeleton gets a folder of pieces under Crowd/, and a row in
Game/Source/Venue/People.generated.h: its model (for the band), its pieces and their pivots.

It also packs the character atlas variants (Assets/Models/Venue/PolygonTown_NN_L.png) into one
texture, PolygonTown_Crowd.png beside them, and lists its tiles in the header: the crowd draws
from that atlas, each figure picking its tile through per-instance data, so figures in different
clothes still share one instanced draw (ME-365). Tiles keep their size and order, so each tile's
mips are the variant's own. Run from the repository root with Blender after adding or changing a
character or an atlas variant:

    blender -b --python Game/Tools/MakeCrowdPieces.py
"""
import glob
import math
import os
import struct
import zlib

import bpy
import numpy
from mathutils import Vector

PEOPLE = "Assets/Models/People"
HEADER = "Game/Source/Venue/People.generated.h"
ATLAS = "../../../Venue/PolygonTown_01_A.png"   # from a character's folder of pieces
SKINS = "Assets/Models/Venue"
SKIN_ATLAS = "Assets/Models/Venue/PolygonTown_Crowd.png"
LO_RATIO = 0.3
PALM = 0.07                                    # the palm's centre past the wrist, metres
NEEDED = ("spine", "spine.004", "spine.006", "upper_arm.L", "upper_arm.R", "hand.L", "hand.R", "thigh.L", "toe.L")

ARM_BONES = ("upper_arm", "forearm", "hand", "palm", "f_", "thumb")
HEAD_BONES = ("spine.004", "spine.005", "spine.006")
TORSO_BONES = ("spine.001", "spine.002", "spine.003", "shoulder", "breast")


def piece_of(bone):
    if bone.startswith(ARM_BONES):
        return "ArmL" if bone.endswith(".L") else "ArmR"
    if bone.startswith(HEAD_BONES):
        return "Head"
    if bone.startswith(TORSO_BONES):
        return "Torso"
    return "Legs"


def to_figure(v):
    # Blender: +x the character's left, +z up, facing -y. Figure space (Puppet's): +x its right
    # hand, +y up, facing +z.
    return Vector((-v.x, v.z, -v.y))


def rotation_between(a, b):
    return a.normalized().rotation_difference(b.normalized())


def vec(v):
    return "glm::vec3( %.4ff, %.4ff, %.4ff )" % (v.x, v.y, v.z)


def cut(source):
    """Writes one character's pieces; returns its row of the header, or None if it isn't rigged."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=source)
    armature = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
    body = next((o for o in bpy.data.objects if o.type == "MESH"), None)
    if not armature or not body or any(bone not in armature.data.bones for bone in NEEDED):
        return None
    # The same character exported twice (BodyType1.fbx and BodyType1_Rigged.fbx) counts once.
    if body.name in seen:
        return None
    seen.add(body.name)
    armature.data.pose_position = "REST"
    name = os.path.splitext(os.path.basename(source))[0].split("_", 1)[-1]
    out_dir = os.path.join(PEOPLE, "Crowd", name)
    os.makedirs(out_dir, exist_ok=True)

    def joint(bone):
        return to_figure(armature.matrix_world @ armature.data.bones[bone].head_local)

    hips = joint("spine")
    neck = joint("spine.004")
    head = joint("spine.006")
    shoulders = [joint("upper_arm.L"), joint("upper_arm.R")]
    wrists = [joint("hand.L"), joint("hand.R")]
    arm_length = (wrists[0] - shoulders[0]).length + PALM
    down = Vector((0.0, -1.0, 0.0))
    pivots = {
        "Legs": (Vector((0.0, 0.0, 0.0)), None),
        "Torso": (hips, None),
        "Head": (neck, None),
        "ArmL": (shoulders[0], rotation_between(wrists[0] - shoulders[0], down)),
        "ArmR": (shoulders[1], rotation_between(wrists[1] - shoulders[1], down)),
        "Body": (Vector((0.0, 0.0, 0.0)), None),
    }

    def read(decimate):
        """The mesh's triangles as (piece, [(position, normal, uv) x 3]), in figure space."""
        for modifier in list(body.modifiers):
            if modifier.type == "DECIMATE":
                body.modifiers.remove(modifier)
        if decimate:
            modifier = body.modifiers.new("Lo", "DECIMATE")
            modifier.ratio = LO_RATIO
        evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        names = [group.name for group in body.vertex_groups]
        uvs = next(layer for layer in mesh.uv_layers if layer.active_render).data
        world = body.matrix_world
        turn = world.to_3x3()
        pieces = []
        for vertex in mesh.vertices:
            weights = sorted(((g.weight, names[g.group]) for g in vertex.groups), reverse=True)
            pieces.append(piece_of(weights[0][1]) if weights else "Torso")
        triangles = []
        for triangle in mesh.loop_triangles:
            votes = [pieces[v] for v in triangle.vertices]
            piece = max(set(votes), key=votes.count)
            normal = to_figure(turn @ triangle.normal).normalized()
            corners = []
            for vertex, loop in zip(triangle.vertices, triangle.loops):
                corners.append((to_figure(world @ mesh.vertices[vertex].co), normal, tuple(uvs[loop].uv)))
            triangles.append((piece, corners))
        evaluated.to_mesh_clear()
        return triangles

    def write(piece_name, triangles, pieces):
        pivot, turn = pivots[piece_name.split("_")[0]]
        count = 0
        with open(os.path.join(out_dir, piece_name + ".obj"), "w") as out:
            out.write("# Generated by Game/Tools/MakeCrowdPieces.py from %s: a piece of a crowd figure.\n" % source)
            out.write("mtllib Crowd.mtl\nusemtl Crowd\n")
            index = 1
            for piece, corners in triangles:
                if piece not in pieces:
                    continue
                for position, normal, uv in corners:
                    p = position - pivot
                    n = normal
                    if turn:
                        p = turn @ p
                        n = turn @ n
                    # The file is right-handed (the importer flips z to the engine's left-handed space).
                    out.write("v %.5f %.5f %.5f\nvn %.4f %.4f %.4f\nvt %.5f %.5f\n" % (p.x, p.y, -p.z, n.x, n.y, -n.z, uv[0], uv[1]))
                out.write("f %d/%d/%d %d/%d/%d %d/%d/%d\n" % tuple(i for corner in range(3) for i in (index + corner,) * 3))
                index += 3
                count += 1
        return count

    with open(os.path.join(out_dir, "Crowd.mtl"), "w") as out:
        out.write("newmtl Crowd\nKd 1 1 1\nKs 0 0 0\nmap_Kd %s\n" % ATLAS)
    counts = {}
    full = read(False)
    for suffix, triangles in (("", full), ("_Lo", read(True))):
        for piece in ("Legs", "Torso", "Head", "ArmL", "ArmR"):
            counts[piece + suffix] = write(piece + suffix, triangles, (piece,))
        if suffix:
            counts["Body_Lo"] = write("Body_Lo", triangles, ("Legs", "Torso", "Head"))
    # The mouth: the face's surface beside the centre line (clear of a nose or a beard's point),
    # level with the head bone.
    lips = [p.z for piece, corners in full for p, n, uv in corners if 0.02 < abs(p.x) < 0.045 and -0.035 < p.y - head.y < 0.02]
    mouth = Vector((0.0, -0.008, (max(lips) if lips else head.z + 0.13) - head.z))
    print("PIECES", name, sum(v for k, v in counts.items() if "_" not in k), "triangles,", sum(v for k, v in counts.items() if k.endswith("_Lo") and k != "Body_Lo"), "decimated, mouth", round(mouth.z, 3))

    def both(piece):
        return '{ "%s/%s.obj", "%s/%s_Lo.obj" }' % (out_dir, piece, out_dir, piece)

    return '        { "%s", %s, %s, %s,\n            { %s, %s }, "%s/Body_Lo.obj",\n            %s, %s, { %s, %s }, %.4ff, %s },\n' % (
        source, both("Legs"), both("Torso"), both("Head"), both("ArmL"), both("ArmR"), out_dir,
        vec(hips), vec(neck), vec(shoulders[0]), vec(shoulders[1]), arm_length, vec(mouth))


def skins():
    """The atlas variants, in VenueKit::Skin's order: palette 1-9, then letter A-F, whichever exist."""
    found = []
    for palette in range(1, 10):
        for letter in "ABCDEF":
            path = os.path.join(SKINS, "PolygonTown_0%d_%s.png" % (palette, letter))
            if os.path.exists(path):
                found.append(path)
    return found


def write_png(path, pixels):
    """An 8-bit RGB PNG of pixels (rows from the top), unfiltered: the bytes go in as they are."""
    height, width, _ = pixels.shape
    raw = numpy.zeros((height, width * 3 + 1), dtype=numpy.uint8)
    raw[:, 1:] = pixels.reshape(height, width * 3)

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    with open(path, "wb") as out:
        out.write(b"\x89PNG\r\n\x1a\n")
        out.write(chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)))
        out.write(chunk(b"sRGB", b"\x00"))
        out.write(chunk(b"IDAT", zlib.compress(raw.tobytes(), 6)))
        out.write(chunk(b"IEND", b""))


def pack_skins():
    """Packs the variants into one atlas, a grid as square as fits, tiles left to right and top to
    bottom; returns (paths, columns, rows, tile size) for the header, or None without variants."""
    paths = skins()
    if not paths:
        return None
    images = [bpy.data.images.load(os.path.abspath(path)) for path in paths]
    tile = images[0].size[0]
    if any(tuple(image.size) != (tile, tile) for image in images):
        raise SystemExit("MakeCrowdPieces: the atlas variants must be square and the same size")
    columns = math.ceil(math.sqrt(len(paths)))
    rows = math.ceil(len(paths) / columns)
    atlas = numpy.zeros((rows * tile, columns * tile, 3), dtype=numpy.uint8)
    pixels = numpy.empty(tile * tile * 4, dtype=numpy.float32)
    for index, image in enumerate(images):
        # An 8-bit image's pixels are its bytes / 255, rows from the bottom.
        image.pixels.foreach_get(pixels)
        rgb = numpy.rint(pixels.reshape(tile, tile, 4)[::-1, :, :3] * 255.0).astype(numpy.uint8)
        column, row = index % columns, index // columns
        atlas[row * tile:(row + 1) * tile, column * tile:(column + 1) * tile] = rgb
        bpy.data.images.remove(image)
    write_png(SKIN_ATLAS, atlas)
    print("SKINS", len(paths), "variants packed into", SKIN_ATLAS, "%dx%d" % (columns * tile, rows * tile))
    return paths, columns, rows, tile


seen = set()
atlas = pack_skins()
if not atlas:
    raise SystemExit("MakeCrowdPieces: no atlas variants in " + SKINS)
rows = sorted(row for row in (cut(source) for source in sorted(glob.glob(os.path.join(PEOPLE, "*.fbx")), reverse=True)) if row)
with open(HEADER, "w") as out:
    out.write("""#pragma once
#include <glm/vec3.hpp>

// Generated by Game/Tools/MakeCrowdPieces.py from the rigged characters in %s: do not edit.
namespace People
{
    // A character: its rigged model (the band's Performer), and the rigid pieces a crowd figure is
    // made of (Puppet; each [0] at full detail, [1] decimated) with where they join, in figure
    // space at a scale of 1.
    struct Person
    {
        const char* Model;
        const char* Legs[2];        // pivot: the feet
        const char* Torso[2];       // pivot: the hips
        const char* Head[2];        // pivot: the neck
        const char* Arms[2][2];     // by side (0 left), hanging straight down from the shoulder
        const char* Body;           // legs, torso and head as one, decimated: the back of the house
        glm::vec3 Hips;
        glm::vec3 Neck;
        glm::vec3 Shoulders[2];
        float ArmLength;            // shoulder to the palm's centre
        glm::vec3 Mouth;            // from the head bone
    };

    inline const Person kPeople[] = {
%s    };
    constexpr int kCount = %d;

    // The atlas variants (VenueKit::Skin) packed into one texture for the crowd (VenueKit::Part):
    // kSkins[i] is the tile at column i %% kSkinColumns, row i / kSkinColumns from the top, each
    // kSkinTile texels square, so a figure picks its clothes by a uv offset instead of a texture.
    inline constexpr const char* kSkinAtlas = "%s";
    constexpr int kSkinColumns = %d;
    constexpr int kSkinRows = %d;
    constexpr int kSkinTile = %d;
    inline const char* const kSkins[] = {
%s    };
    constexpr int kSkinCount = %d;
}
""" % (PEOPLE, "".join(rows), len(rows), SKIN_ATLAS, atlas[1], atlas[2], atlas[3], "".join('        "%s",\n' % path for path in atlas[0]), len(atlas[0])))
