"""Exports the patrol cruiser for the story venues from its .blend. Run it in Blender:

    blender -b ~/Downloads/PatrolCruiser.blend --python Tools/Venues/export_patrol_cruiser.py

Writes Assets/Models/CopCar/PatrolCruiser.fbx and PatrolCruiserDoorOpen.fbx (the driver's door
swung open, for the crash site). Both are the whole car joined into one object, so the engine draws
one part for each material instead of one for each panel's, turned to face +z in the engine with
the wheels on y = 0 and the car's centre over the origin. Delete the .assbin beside an FBX after
exporting it again, or the engine keeps the old cook.

The .blend has the nose along +x, z up, the driver's side at +y; nothing in it is changed or saved.
"""
import math
import os

import bpy
from mathutils import Matrix, Vector

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'Assets', 'Models', 'CopCar'))
# The driver's door and its glass, the hinge line at the door's leading edge, and how far it swings.
DOOR = ('SM_FrontDoorLeft', 'SM_PaneFrontLeft')
HINGE = Vector((0.84, 0.95, 0.0))
SWING = 62.0
# Blender's FBX exporter (-Z forward, Y up) and the engine's left-handed import put Blender's +y on
# the engine's +z: turn the nose from +x round to +y.
FACE_Z = Matrix.Rotation(math.radians(90.0), 4, 'Z')


def export(name, door_open):
    bpy.ops.object.select_all(action='DESELECT')
    parts = []
    for src in [o for o in bpy.data.objects if o.type == 'MESH']:
        o = src.copy()
        o.data = src.data.copy()
        bpy.context.scene.collection.objects.link(o)
        world = src.matrix_world.copy()
        if door_open and src.name in DOOR:
            world = Matrix.Translation(HINGE) @ Matrix.Rotation(math.radians(-SWING), 4, 'Z') @ Matrix.Translation(-HINGE) @ world
        o.parent = None
        o.data.transform(FACE_Z @ world)
        o.matrix_world = Matrix.Identity(4)
        parts.append(o)
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    car = bpy.context.view_layer.objects.active
    car.name = car.data.name = name
    lo = [min(v.co[i] for v in car.data.vertices) for i in range(3)]
    hi = [max(v.co[i] for v in car.data.vertices) for i in range(3)]
    bpy.ops.object.select_all(action='DESELECT')
    car.select_set(True)
    path = os.path.join(OUT, name + '.fbx')
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={'MESH'}, use_mesh_modifiers=True, bake_anim=False,
                             add_leaf_bones=False, path_mode='STRIP')
    print(f'{path}: {len(car.data.vertices)} vertices, {len(car.material_slots)} materials, '
          f'{hi[0] - lo[0]:.2f} wide, {hi[1] - lo[1]:.2f} long, {hi[2] - lo[2]:.2f} tall, wheels at z = {lo[2]:.3f}')
    bpy.data.objects.remove(car)


export('PatrolCruiser', False)
export('PatrolCruiserDoorOpen', True)
