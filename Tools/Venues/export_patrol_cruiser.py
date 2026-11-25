"""Exports the patrol cruiser for the story venues from its .blend. Run it in Blender:

    blender -b ~/Downloads/PatrolCruiser.blend --python Tools/Venues/export_patrol_cruiser.py

Writes Assets/Models/CopCar/PatrolCruiser.fbx and PatrolCruiserDoorOpen.fbx (the driver's door
swung open, for the crash site). Both are the whole car joined into one object, so the engine draws
one part for each material instead of one for each panel's, turned to face +z in the engine with
the wheels on y = 0 and the car's centre over the origin. Delete the .assbin beside an FBX after
exporting it again, or the engine keeps the old cook.

For a car seen driving it also writes PatrolCruiserRolling.fbx (no wheels, the driver's window
wound down) and PatrolCruiserWheel.fbx (the driver's side front wheel about its hub, for the venue
to spin at each corner: turned half round for the other side). Where the hubs and the driver's
window sill are goes to story_vehicles.json (WheelFront, WheelRear: the +x side's; Sill).

The car is exported a tenth larger than it was modelled, and its front bench is refitted, because
the people who drive it (the band's character: 1.82 m, and 1.08 m from the seat to the top of the
cap) did not fit a cabin 0.73 m from cushion to roof: the bench goes back 0.2 m and down until the
driver's head clears the lining, and the floor under it and ahead of it is cut down to a well for
the legs. Where the driver's hips and heels go is written to story_vehicles.json (PatrolCruiser),
with the steering wheel's centre, rim radius and axis.

The .blend has the nose along +x, z up, the driver's side at +y; nothing in it is changed or saved.
"""
import json
import math
import os

import bpy
from mathutils import Matrix, Vector

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'Assets', 'Models', 'CopCar'))
# The driver's door and its glass, the hinge line at the door's leading edge, and how far it swings.
DOOR = ('SM_FrontDoorLeft', 'SM_PaneFrontLeft')
HINGE = Vector((0.84, 0.95, 0.0))
SWING = 62.0
# The rolling car's: its wheels (one is exported for all four) and the glass that is wound down.
WHEELS = ('SM_FrontWheelLeft', 'SM_FrontWheelRight', 'SM_RearWheelLeft', 'SM_RearWheelRight')
WHEEL = 'SM_FrontWheelLeft'
WINDOW = 'SM_PaneFrontLeft'
# Blender's FBX exporter (-Z forward, Y up) and the engine's left-handed import put Blender's +y on
# the engine's +z: turn the nose from +x round to +y.
FACE_Z = Matrix.Rotation(math.radians(90.0), 4, 'Z')
FACTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'story_vehicles.json')
# How much larger than modelled the car is exported (the highway fleet's is the same:
# export_vehicles.py), and what a seated driver needs from the cushion to the roof lining, in the
# exported car's metres.
SCALE = 1.1
SITS = 1.11
# The cabin as modelled (the .blend's axes): the roof lining's underside, the front bench's
# cushion top and the front of its backrest, the underside of the floor, and the steering wheel.
ROOF = 1.47
CUSHION = 0.75
BACKREST = -0.02
UNDERSIDE = 0.345
STEERING = Vector((0.328, 0.438, 0.975))
# Its rim (the centreline's radius) and its axis, out of the wheel's face toward the driver.
STEERING_RADIUS = 0.19
STEERING_AXIS = Vector((-0.821, 0.0, 0.571))
# The refit: the bench goes this far back; the well cut in the floor reaches from behind the
# bench to the firewall, between the sills.
BENCH_BACK = 0.2
WELL = ((-0.45, 0.97), (-0.8, 0.8))
PAD = 0.1       # what is left of the cushion's depth over the well's floor


def refit_cabin(o, name):
    """The front bench and the floor under it, in the .blend's axes (before FACE_Z)."""
    seat = ROOF - SITS / SCALE                  # where the cushion's top has to be
    well = max(UNDERSIDE + 0.015, seat - PAD)   # the well's floor
    if name == 'SM_FrontBench':
        top = max(v.co.z for v in o.data.vertices)
        for v in o.data.vertices:
            v.co.x -= BENCH_BACK
            if v.co.z > CUSHION:
                # The backrest stretches down to the cushion: its top stays where it was.
                v.co.z = seat + (v.co.z - CUSHION) * (top - seat) / (top - CUSHION)
            else:
                v.co.z = max(well + 0.004, v.co.z - (CUSHION - seat))
    elif name == 'SM_Floor':
        (x0, x1), (y0, y1) = WELL
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        cutter = bpy.context.active_object
        cutter.scale = (x1 - x0, y1 - y0, 2.0)
        cutter.location = ((x0 + x1) / 2, (y0 + y1) / 2, well + 1.0)
        cut = o.modifiers.new('Well', 'BOOLEAN')
        cut.operation = 'DIFFERENCE'
        cut.solver = 'EXACT'
        cut.object = cutter
        bpy.context.view_layer.update()
        mesh = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get()))
        o.modifiers.remove(cut)
        o.data = mesh
        bpy.data.objects.remove(cutter)
        # The floor is a shell, so the cut leaves it open to the road: a plate closes the well.
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        plate = bpy.context.active_object
        plate.data.transform(Matrix.Translation(((x0 + x1) / 2, (y0 + y1) / 2, (UNDERSIDE + well) / 2))
                             @ Matrix.Diagonal((x1 - x0 + 0.02, y1 - y0 + 0.02, well - UNDERSIDE, 1.0)))
        plate.data.materials.append(o.material_slots[0].material)
        return [plate]
    return []


def middle(name):
    """The middle of a part's box, and the box, in the .blend's axes."""
    src = bpy.data.objects[name]
    pts = [src.matrix_world @ v.co for v in src.data.vertices]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return (lo + hi) / 2, lo, hi


def export(name, door_open, leave=(), only=None):
    """The car as name.fbx, without the parts in leave; or with only, that one part about its
    own middle."""
    bpy.ops.object.select_all(action='DESELECT')
    parts = []
    pivot = middle(only)[0] if only else Vector((0, 0, 0))
    for src in [o for o in bpy.data.objects if o.type == 'MESH']:
        if src.name in leave or (only and src.name != only):
            continue
        o = src.copy()
        o.data = src.data.copy()
        bpy.context.scene.collection.objects.link(o)
        world = src.matrix_world.copy()
        o.parent = None
        o.data.transform(Matrix.Translation(-pivot) @ world)
        o.matrix_world = Matrix.Identity(4)
        extra = refit_cabin(o, src.name) if src.name in ('SM_FrontBench', 'SM_Floor') else []
        for e in extra:
            e.data.transform(Matrix.Scale(SCALE, 4) @ FACE_Z)
            parts.append(e)
        if door_open and src.name in DOOR:
            o.data.transform(Matrix.Translation(HINGE) @ Matrix.Rotation(math.radians(-SWING), 4, 'Z') @ Matrix.Translation(-HINGE))
        o.data.transform(Matrix.Scale(SCALE, 4) @ FACE_Z)
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
          f'{hi[0] - lo[0]:.2f} wide, {hi[1] - lo[1]:.2f} long, {hi[2] - lo[2]:.2f} tall, lowest at z = {lo[2]:.3f}')
    bpy.data.objects.remove(car)
    if os.path.exists(path + '.assbin'):
        os.remove(path + '.assbin')


def facts():
    """Where the driver sits, in the engine's axes (x to the car's right, y up, z to its nose) and
    the exported car's metres: the hip joints (9 cm over the cushion, 12 cm ahead of the
    backrest), the floor under the heels, and the steering wheel's centre."""
    seat = ROOF - SITS / SCALE
    well = max(UNDERSIDE + 0.015, seat - PAD)

    def engine(x, y, z):
        return [round(-y * SCALE, 3), round(z * SCALE, 3), round(x * SCALE, 3)]
    out = {'Seat': engine(BACKREST - BENCH_BACK + 0.12 / SCALE, STEERING.y, seat + 0.09 / SCALE), 'Heel': round(well * SCALE, 3),
           'SteeringWheel': engine(*STEERING), 'SteeringRadius': round(STEERING_RADIUS * SCALE, 3),
           'SteeringAxis': [round(-STEERING_AXIS.y, 3), round(STEERING_AXIS.z, 3), round(STEERING_AXIS.x, 3)], 'Scale': SCALE}
    # The hubs on the passenger's (+x) side, and the driver's window: the outside of the sill, at
    # the middle of the opening's length.
    for key, part in (('WheelFront', 'SM_FrontWheelRight'), ('WheelRear', 'SM_RearWheelRight')):
        out[key] = engine(*middle(part)[0])
    mid, lo, hi = middle(WINDOW)
    out['Sill'] = engine(mid.x, hi.y, lo.z)
    data = {}
    if os.path.exists(FACTS):
        with open(FACTS, encoding='utf-8') as f:
            data = json.load(f)
    data['PatrolCruiser'] = out
    with open(FACTS, 'w', newline='\n', encoding='utf-8') as f:
        json.dump(data, f, indent=1, sort_keys=True)
        f.write('\n')
    print('PatrolCruiser:', out)


export('PatrolCruiser', False)
export('PatrolCruiserDoorOpen', True)
export('PatrolCruiserRolling', False, leave=WHEELS + (WINDOW,))
export('PatrolCruiserWheel', False, only=WHEEL)
facts()
