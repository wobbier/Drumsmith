"""Exports the highway fleet (Art/Vehicles/<Name>/<Name>.blend) for the story venues. Run it in
Blender; it opens each .blend itself and saves none of them:

    blender -b --python Tools/Venues/export_vehicles.py            (the whole fleet)
    blender -b --python Tools/Venues/export_vehicles.py -- Civic   (only the ones named)

Writes Assets/Models/Vehicles/<Name>.fbx, each the whole vehicle joined into one object (so the
engine draws one part for each material, not one for each panel's), turned to face +z in the
engine with its wheels or skids on y = 0 and the driver's side at -x. A helicopter's main and tail
rotors go to <Name>Rotor.fbx and <Name>TailRotor.fbx, each about its own hub, for the venue to
spin. Where each vehicle's lamps, beacons, steering wheel (its centre, rim radius and axis) and hubs ended up is written to
Tools/Venues/story_vehicles.json, which story_afterlife_art reads (A.vehicle): the venues never
carry a hand-copied lamp position. Delete the .assbin beside an FBX after exporting it again, or
the engine keeps the old cook (this script does it).

The road vehicles are exported a tenth larger than they were modelled (SCALE; the helicopters as
they are), and the police trucks' front seats are lowered until a driver's head clears the roof
lining (fit_driver): the band's character is 1.82 m, 1.08 m from the seat to the top of the cap,
and sat with only a head above the sill. Where the driver's hips and heels go is written with the
rest (Seat, Heel). A vehicle the story shows driving (ROLLING) also gets <Name>Rolling.fbx (no
wheels, the driver's window wound down) and <Name>Wheel.fbx (the driver's side front wheel about
its hub, for the venue to spin at each corner: turned half round for the other side), with the
+x side's hubs and the driver's window sill in the facts (WheelFront, WheelRear, Sill). The patrol
cruiser has its own script (export_patrol_cruiser.py) and the same
rules.

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
from mathutils.bvhtree import BVHTree

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
# How much larger than modelled the road vehicles are exported, and which are helicopters (not).
SCALE = 1.1
AIRCRAFT = ('JetRanger', 'AS350')
# What a seated driver needs from the cushion to the roof lining, in exported metres.
SITS = 1.11
# The vehicles the story puts a driver in: the front seats' parts (they all go down), and of those
# the cushion and the backrest (which stretches down, its top staying put).
DRIVERS = {
    'TrailDuster': {'seat': r'^Front (cushion|backrest|seat runner)', 'cushion': r'^Front cushion', 'back': r'^Front backrest'},
    'Ranger': {'seat': r'^Front seat', 'cushion': r'^Front seat cushion', 'back': r'^Front seatback'},
}


# The vehicles also exported rolling, the assemblies that are their wheels, and the driver's glass.
ROLLING = ('TrailDuster',)
TIRE = re.compile(r'^Assembly \| ([LR]) (front|rear) tire')
WINDOW = 'L door glazing'


def copies(objects):
    """Copies of objects (write() consumes what it is given)."""
    out = []
    for o in objects:
        c = o.copy()
        c.data = o.data.copy()
        bpy.context.scene.collection.objects.link(c)
        out.append(c)
    return out


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


def steering(rim):
    """A steering wheel's rim (after FACE_Z): the radius of its centreline, and its axis, the
    unit vector out of the wheel's face toward the driver."""
    import numpy as np
    pts = np.array([list(v.co) for o in rim for v in o.data.vertices])
    centre = (pts.min(0) + pts.max(0)) / 2
    axis = np.linalg.svd(pts - centre)[2][2]
    if axis[1] > 0:
        axis = -axis
    flat = (pts - centre) - np.outer((pts - centre) @ axis, axis)
    spans = np.linalg.norm(flat, axis=1)
    radius = (spans.max() + np.percentile(spans, 60)) / 2 if len(spans) else 0.0
    return round(float(radius), 3), Vector([float(c) for c in axis])


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


def gather(scale, exclude=()):
    """Every drawn object as a mesh in the engine's facing, scale times its size, with what it
    was: (object, source)."""
    studio = bpy.data.collections.get('Review studio')
    skip = set(studio.all_objects) if studio else set()
    cabin = bpy.data.collections.get('Cabin')
    cabin = set(cabin.all_objects) if cabin else set()
    deps = bpy.context.evaluated_depsgraph_get()
    parts = []
    dropped = 0
    for src in list(bpy.data.objects):
        if src in skip or src.name in exclude or src.type not in ('MESH', 'CURVE', 'FONT') or src.hide_render:
            continue
        mesh = bpy.data.meshes.new_from_object(src.evaluated_get(deps), depsgraph=deps)
        if not mesh.polygons:
            bpy.data.meshes.remove(mesh)
            continue
        o = bpy.data.objects.new('part', mesh)
        mesh.transform(Matrix.Scale(scale, 4) @ FACE_Z @ src.matrix_world)
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


def fit_driver(name, parts):
    """Lowers the front seats of a vehicle the story puts a driver in until SITS clears the roof
    lining over the driver's (the -x) seat. parts are in the engine's facing (x right, y to the
    nose, z up), already scaled. Returns the hip joints and the heels' floor there: (Vector, z)."""
    rule = DRIVERS[name]
    seat = [o for o, src in parts if re.match(rule['seat'], src.name)]
    rest = [o for o, src in parts if not re.match(rule['seat'], src.name)]
    cushion = next(o for o, src in parts if re.match(rule['cushion'], src.name) and box([o])[0][0] + box([o])[1][0] < 0)
    back = next(o for o, src in parts if re.match(rule['back'], src.name) and box([o])[0][0] + box([o])[1][0] < 0)
    verts, faces = [], []
    for o in rest:
        base = len(verts)
        verts += [v.co.copy() for v in o.data.vertices]
        faces += [[base + i for i in f.vertices] for f in o.data.polygons]
    tree = BVHTree.FromPolygons(verts, faces)
    lo, hi = box([cushion])
    top = hi[2]
    x = (lo[0] + hi[0]) / 2
    low = [v.co[1] for v in back.data.vertices if v.co[2] < box([back])[0][2] + 0.15]
    hips = max(low) + 0.12
    roof = tree.ray_cast(Vector((x, hips, top + 0.3)), Vector((0, 0, 1)))[0]
    floor = tree.ray_cast(Vector((x, hips + 0.45, top)), Vector((0, 0, -1)))[0]
    floor = floor[2] if floor else lo[2] - 0.05
    drop = max(0.0, top + SITS - roof[2]) if roof else 0.0
    if top - drop < floor + 0.04:
        print(f'{name}: the seat would need to go {drop:.2f} down, into the floor; held 4 cm over it')
        drop = top - floor - 0.04
    for o, src in parts:
        if o not in seat:
            continue
        a, b = box([o])
        for v in o.data.vertices:
            if re.match(rule['back'], src.name):
                v.co[2] = b[2] - (b[2] - v.co[2]) * (b[2] - a[2] + drop) / (b[2] - a[2])
            else:
                v.co[2] = max(floor + 0.005, v.co[2] - drop)
    print(f'{name}: roof lining {roof[2] if roof else 0:.2f}, cushion {top:.2f} -> {top - drop:.2f}, floor {floor:.2f}')
    return Vector((x, hips, top - drop + 0.09)), floor


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
    parts, dropped = gather(1.0 if name in AIRCRAFT else SCALE)
    sits = fit_driver(name, parts) if name in DRIVERS else None
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
        facts['SteeringRadius'], axis = steering(wheel)
        facts['SteeringAxis'] = engine(axis)
    if sits:
        facts['Seat'] = engine(sits[0] - pivot)
        facts['Heel'] = round(sits[1] - pivot[2], 3)
    facts['Scale'] = 1.0 if name in AIRCRAFT else SCALE
    if name in ROLLING:
        wheels = {}
        for o, src in body:
            found = TIRE.match(top(src).name)
            if found:
                wheels.setdefault(found.groups(), []).append(o)
        hubs = {}
        for key, group in wheels.items():
            a, b = box(group)
            hubs[key] = (a + b) / 2
        # The driver's side is -x: the other side's hubs are the ones written.
        far = 'R' if hubs[('R', 'front')][0] > 0 else 'L'
        near = 'L' if far == 'R' else 'R'
        facts['WheelFront'], facts['WheelRear'] = engine(hubs[(far, 'front')]), engine(hubs[(far, 'rear')])
        glass = next(o for o, src in body if src.name == WINDOW)
        a, b = box([glass])
        facts['Sill'] = engine(Vector((a[0], (a[1] + b[1]) / 2, a[2])))
        tyres = {o for group in wheels.values() for o in group}
        rolling = copies([o for o, _ in body if o not in tyres and o is not glass])
        wheel = copies(wheels[(near, 'front')])
        write(name + 'Rolling', rolling, Vector((0, 0, 0)))
        write(name + 'Wheel', wheel, hubs[(near, 'front')])
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


if __name__ == "__main__":
    main()
