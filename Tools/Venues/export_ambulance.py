"""Export the rescue ambulance from its assembled scene. Run with blender -b --python Tools/Venues/export_ambulance.py."""
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import export_vehicles as fleet


def metadata(stem):
    path = Path(fleet.OUT) / (stem + '.fbx.meta')
    if not path.exists():
        guid = hashlib.sha256(stem.encode()).hexdigest()[:16]
        path.write_text(json.dumps(dict(ConvertUnits=True, FileType='fbx', GUID=guid), indent=4) + '\n')


def breakaway(scene, source):
    """Keep the authored hinge and grip pivots and give loose meshes local origins."""
    deps = bpy.context.evaluated_depsgraph_get()
    copies = {}
    world = {}
    for obj in source:
        collection = obj.users_collection[0].name
        if 'Review' in collection or 'scale cast' in obj.name or obj.hide_render:
            continue
        if obj.type not in ('EMPTY', 'MESH', 'FONT', 'CURVE'):
            continue
        mesh = None
        transform = fleet.FACE_Z @ obj.matrix_world
        if obj.type != 'EMPTY':
            mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(deps), depsgraph=deps)
            corners = [Vector(corner) for corner in obj.evaluated_get(deps).bound_box]
            center = sum(corners, Vector()) / 8
            mesh.transform(Matrix.Translation(-center))
            transform = transform @ Matrix.Translation(center)
        copy = bpy.data.objects.new('Braun - ' + obj.name, mesh)
        scene.collection.objects.link(copy)
        copies[obj] = copy
        world[obj] = transform
    # Set local matrices directly, including assemblies whose parent origin was recentered.
    for obj, copy in copies.items():
        if obj.parent in copies:
            copy.parent = copies[obj.parent]
            copy.matrix_basis = world[obj.parent].inverted_safe() @ world[obj]
        else:
            copy.matrix_basis = world[obj]
    bpy.ops.object.select_all(action='DESELECT')
    for copy in copies.values():
        copy.select_set(True)
    path = Path(fleet.OUT) / 'BraunParts.fbx'
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'MESH', 'EMPTY'},
                             bake_anim=False, add_leaf_bones=False, path_mode='STRIP')
    path.with_suffix('.fbx.assbin').unlink(missing_ok=True)
    metadata('BraunParts')
    for copy in copies.values():
        bpy.data.objects.remove(copy, do_unlink=True)



def export():
    bpy.ops.wm.open_mainfile(filepath=str(Path(fleet.ART) / 'Ambulance/Braun-Long.blend'))
    scene = bpy.context.scene
    scene.frame_set(1)
    fleet.GLASS.update({'Clear acrylic': 0.18})
    fleet.LIT.update({'Trace green': 3.0})
    fleet.prepare_materials()
    objects = scene.objects
    source = list(objects)

    def save(name, parts, pivot=(0, 0, 0)):
        deps = bpy.context.evaluated_depsgraph_get()
        meshes = []
        for obj in parts:
            mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(deps), depsgraph=deps)
            mesh.transform(fleet.FACE_Z @ obj.matrix_world)
            if obj.matrix_world.determinant() < 0:
                mesh.flip_normals()
            copy = bpy.data.objects.new('Export part', mesh)
            scene.collection.objects.link(copy)
            meshes.append(copy)
        stem = 'Braun' + name
        fleet.write(stem, meshes, fleet.FACE_Z @ Vector(pivot))
        metadata(stem)

    breakaway(scene, source)

    groups = {name: [] for name in ('Body', 'Doors', 'Cot', 'Paddle', 'IV', 'Strap')}
    trace = objects['ECG trace - keyed pulse']
    for obj in source:
        if obj.type not in ('MESH', 'CURVE', 'FONT') or obj.hide_render:
            continue
        collection = obj.users_collection[0].name
        if 'Review' in collection or 'scale cast' in obj.name or obj.name == 'Blanket across legs':
            continue
        root = fleet.top(obj).name
        if root in ('Ventilation bag', 'Right paddle grip control') or 'flexible paddle lead' in obj.name:
            continue
        if root == 'IV hook':
            group = 'IV'
        elif root.startswith('Strap hook'):
            if root != 'Strap hook':
                continue
            group = 'Strap'
        elif root == 'Left paddle grip control':
            group = 'Paddle'
        elif collection == 'Ferno-style loading cot':
            group = 'Cot'
        elif root.endswith('rear door hinge'):
            group = 'Doors'
        else:
            group = 'Body'
        groups[group].append(obj)

    for name in ('Body', 'Cot', 'Doors'):
        save(name, groups[name])
    for name, anchor in [('Strap', 'Strap hook'), ('IV', 'IV hook'), ('Paddle', 'Left paddle face')]:
        save(name, groups[name], objects[anchor].matrix_world.translation)
    scene.frame_set(47)
    save('Pulse', [trace])
    scene.frame_set(81)
    save('OpenDoors', groups['Doors'])
    deck = set(groups['Cot'])
    for name, hinge in [('FrontLegs', 'Leg pair hinge'), ('RearLegs', 'Leg pair hinge.001')]:
        pivot = objects[hinge]
        legs = [obj for obj in groups['Cot'] if obj in pivot.children_recursive]
        save(name, legs, pivot.matrix_world.translation)
        deck.difference_update(legs)
    save('Deck', [obj for obj in groups['Cot'] if obj in deck], (4.90, 0, 0))


if __name__ == '__main__':
    export()
