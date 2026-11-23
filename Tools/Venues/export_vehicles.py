"""Exports the highway fleet (Art/Vehicles/<Name>/<Name>.blend) for the story venues. Run it in
Blender; it opens each .blend itself and saves none of them:

    blender -b --python Tools/Venues/export_vehicles.py            (the whole fleet)
    blender -b --python Tools/Venues/export_vehicles.py -- Civic   (only the ones named)

Writes Assets/Models/Vehicles/<Name>.fbx, each the whole vehicle joined into one object (so the
engine draws one part for each material, not one for each panel's), turned to face +z in the
engine with its wheels or skids on y = 0 and the driver's side at -x. A helicopter's main and tail
rotors go to <Name>Rotor.fbx and <Name>TailRotor.fbx, each about its own hub, for the venue to
spin. Where each vehicle's lamps, beacons, steering wheel and hubs ended up is written to
Tools/Venues/story_vehicles.json, which story_afterlife_art reads (A.vehicle): the venues never
carry a hand-copied lamp position. Delete the .assbin beside an FBX after exporting it again, or
the engine keeps the old cook (this script does it).

The .blend files have the nose along -x, z up, the driver's side at -y, the wheels on z = 0, and a
'Review studio' collection (backdrop, cameras, softboxes) that is left out. Their window glass is
a mix shader the FBX exporter writes as opaque, and their lamps are unlit: both are set here.
"""
import json
import math
import os
import re
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.abspath(os.path.join(HERE, '..', '..', 'Art', 'Vehicles'))
OUT = os.path.abspath(os.path.join(HERE, '..', '..', 'Assets', 'Models', 'Vehicles'))
FACTS = os.path.join(HERE, 'story_vehicles.json')

# Name -> its .blend under Art/Vehicles.
FLEET = {
    'Caprice': 'Caprice/Caprice.blend',
    'Civic': 'Civic/Civic.blend',
    'Corvette': 'Corvette/Corvette.blend',
    'Caravan': 'Caravan/Caravan.blend',
    'C10': 'C10/C10.blend',
    'TrailDuster': 'TrailDuster/TrailDuster.blend',
    'Ranger': 'Ranger/Ranger.blend',
    'JetRanger': 'JetRanger/JetRanger.blend',
    'AS350': 'AS350/AS350-B1.blend',
}
# Blender's FBX exporter (-Z forward, Y up) and the engine's left-handed import put Blender's +y on
# the engine's +z: turn the nose from -x round to +y.
FACE_Z = Matrix.Rotation(math.radians(-90.0), 4, 'Z')
# The top-level assemblies that turn (a helicopter's): the main rotor's and the tail rotor's.
ROTOR = re.compile(r'^Assembly \| (Main rotor blade|Main rotor head|Main blade|Rotor head)')
TAIL_ROTOR = re.compile(r'^Assembly \| (Tail rotor blade|Tail blade)')
ROTOR_HUB = re.compile(r'^Assembly \| (Main rotor head|Rotor head)')
TAIL_HUB = re.compile(r'^Assembly \| Tail rotor shaft')
# Material name -> (emission strength, alpha): the lamps lit, the glass see-through.
LIT = {'Headlamps': 4.0, 'Ruby lenses': 2.5, 'Ruby beacon': 4.0, 'Amber lenses': 1.2, 'Starboard green': 4.0}
GLASS = {'Window glass': 0.22}
# Fittings smaller than this (metres across) are left out, in the cabin and outside it: needle,
# tick, knob and wheel nut are a third of a car's vertices and nothing a venue's camera can see.
SMALL_CABIN = 0.11
SMALL = 0.045


def engine(p):
    """A Blender point (after FACE_Z) as the engine's (x, y, z)."""
    return [round(p[0], 3), round(p[2], 3), round(p[1], 3)]


def top(o):
    while o.parent:
        o = o.parent
    return o


def box(objects):
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for o in objects:
        for v in o.data.vertices:
            for i in range(3):
                lo[i] = min(lo[i], v.co[i])
                hi[i] = max(hi[i], v.co[i])
    return lo, hi


def prepare_materials():
    for m in bpy.data.materials:
        shader = m.node_tree.nodes.get('Principled BSDF') if m.use_nodes and m.node_tree else None
        if not shader:
            continue
        if m.name in LIT:
            shader.inputs['Emission Color'].default_value = shader.inputs['Base Color'].default_value
            shader.inputs['Emission Strength'].default_value = LIT[m.name]
        else:
            shader.inputs['Emission Strength'].default_value = 0.0
        if m.name in GLASS:
            # Only the Principled shader is left wired to the output: the exporter reads its alpha.
            out = next(n for n in m.node_tree.nodes if n.type == 'OUTPUT_MATERIAL')
            m.node_tree.links.new(shader.outputs['BSDF'], out.inputs['Surface'])
            shader.inputs['Alpha'].default_value = GLASS[m.name]
            m.blend_method = 'BLEND'


def gather():
    """Every drawn object as a mesh in the engine's facing, with what it was: (object, source)."""
    studio = bpy.data.collections.get('Review studio')
    skip = set(studio.all_objects) if studio else set()
    cabin = bpy.data.collections.get('Cabin')
    cabin = set(cabin.all_objects) if cabin else set()
    deps = bpy.context.evaluated_depsgraph_get()
    parts = []
    dropped = 0
    for src in list(bpy.data.objects):
        if src in skip or src.type not in ('MESH', 'CURVE', 'FONT') or src.hide_render:
            continue
        mesh = bpy.data.meshes.new_from_object(src.evaluated_get(deps), depsgraph=deps)
        if not mesh.polygons:
            bpy.data.meshes.remove(mesh)
            continue
        o = bpy.data.objects.new('part', mesh)
        mesh.transform(FACE_Z @ src.matrix_world)
        if src.matrix_world.determinant() < 0:
            mesh.flip_normals()
        lo, hi = box([o])
        if (hi - lo).length < (SMALL_CABIN if src in cabin else SMALL):
            bpy.data.objects.remove(o)
            bpy.data.meshes.remove(mesh)
            dropped += 1
            continue
        bpy.context.scene.collection.objects.link(o)
        parts.append((o, src))
    return parts, dropped


def write(name, objects, pivot):
    """Joins objects into one, moves pivot to the origin and exports it. Returns its facts."""
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    if len(objects) > 1:
        bpy.ops.object.join()
    whole = bpy.context.view_layer.objects.active
    whole.name = whole.data.name = name
    whole.data.transform(Matrix.Translation(-pivot))
    lo, hi = box([whole])
    bpy.ops.object.select_all(action='DESELECT')
    whole.select_set(True)
    path = os.path.join(OUT, name + '.fbx')
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'MESH'}, use_mesh_modifiers=True, bake_anim=False,
                             add_leaf_bones=False, path_mode='STRIP')
    if os.path.exists(path + '.assbin'):
        os.remove(path + '.assbin')
    facts = {'Vertices': len(whole.data.vertices), 'Materials': len(whole.material_slots), 'Min': engine(lo), 'Max': engine(hi)}
    print(f'{name}.fbx: {facts["Vertices"]} vertices, {facts["Materials"]} materials, {hi[0] - lo[0]:.2f} wide, {hi[1] - lo[1]:.2f} long, {hi[2] - lo[2]:.2f} tall')
    bpy.data.objects.remove(whole)
    return facts


def lamps(parts, material, end, lo, hi, within=0.25):
    """The middle of the lamps of that material at the nose (end 1) or tail (-1), one for each
    side: [(x, y, z) at -x, (x, y, z) at +x] in Blender's axes after FACE_Z, or None."""
    edge = hi[1] if end > 0 else lo[1]
    sides = {-1: [], 1: []}
    for o, src in parts:
        if not src.material_slots or not src.material_slots[0].material or src.material_slots[0].material.name != material:
            continue
        a, b = box([o])
        c = (a + b) / 2
        if abs(c[1] - edge) > within or (b - a).length < 0.08 or abs(c[0]) < 0.05:
            continue
        sides[1 if c[0] > 0 else -1].append(c)
    if not sides[-1] or not sides[1]:
        # (A lamp set back from the bumper: the armoured truck's tail lamps on its door hinges.)
        return lamps(parts, material, end, lo, hi, 0.45) if within < 0.45 else None
    return [sum(sides[s], Vector()) / len(sides[s]) for s in (-1, 1)]


def export(name):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(ART, FLEET[name]))
    prepare_materials()
    parts, dropped = gather()
    body = [(o, src) for o, src in parts if not ROTOR.match(top(src).name) and not TAIL_ROTOR.match(top(src).name)]
    rotor = [o for o, src in parts if ROTOR.match(top(src).name)]
    tail = [o for o, src in parts if TAIL_ROTOR.match(top(src).name)]
    lo, hi = box([o for o, _ in body])
    # The vehicle's middle over the origin (a helicopter's rotor mast), what it stands on at 0.
    pivot = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]))
    facts = {}
    hub = next((o for o in bpy.data.objects if ROTOR_HUB.match(o.name)), None)
    if rotor and hub:
        at = FACE_Z @ hub.matrix_world.translation
        pivot = Vector((at[0], at[1], lo[2]))
        facts['Rotor'] = engine(at - pivot)
        facts['RotorSpan'] = round(max((box([o])[1] - at).length for o in rotor) * 2, 2)
    shaft = next((o for o in bpy.data.objects if TAIL_HUB.match(o.name)), None)
    if tail and shaft:
        a, b = box(tail)
        tail_at = Vector(((a[0] + b[0]) / 2, (FACE_Z @ shaft.matrix_world.translation)[1], (FACE_Z @ shaft.matrix_world.translation)[2]))
        facts['TailRotor'] = engine(tail_at - pivot)
    lo, hi = lo - pivot, hi - pivot
    for o, _ in body:
        o.data.transform(Matrix.Translation(-pivot))
    for key, material, end in (('Headlamp', 'Headlamps', 1), ('TailLamp', 'Ruby lenses', -1), ('Indicator', 'Amber lenses', 1)):
        found = lamps(body, material, end, lo, hi)
        if found:
            facts[key] = engine(found[1])
    beacons = []
    for o, src in body:
        if re.match(r'^(Red beacon|Beacon housing|Fin beacon (dome|lens))(\.\d+)?$', src.name):
            a, b = box([o])
            beacons.append(engine(Vector(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, b[2]))))
    if beacons:
        facts['Beacons'] = sorted(beacons)
    wheel = [o for o, src in body if re.match(r'^Steering (wheel( rim)?|rim)$', src.name)]
    if wheel:
        a, b = box(wheel)
        facts['SteeringWheel'] = engine((a + b) / 2)
    facts.update(write(name, [o for o, _ in body], Vector((0, 0, 0))))
    if rotor and hub:
        write(name + 'Rotor', rotor, FACE_Z @ hub.matrix_world.translation)
    if tail and shaft:
        write(name + 'TailRotor', tail, tail_at)
    facts['Dropped'] = dropped
    return facts


def main():
    names = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else list(FLEET)
    os.makedirs(OUT, exist_ok=True)
    facts = {}
    if os.path.exists(FACTS):
        with open(FACTS, encoding='utf-8') as f:
            facts = json.load(f)
    for name in names:
        facts[name] = export(name)
    with open(FACTS, 'w', newline='\n', encoding='utf-8') as f:
        json.dump(facts, f, indent=1, sort_keys=True)
        f.write('\n')


main()
