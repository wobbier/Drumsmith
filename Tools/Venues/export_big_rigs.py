"""blender -b --python Tools/Venues/export_big_rigs.py

Bake the two Big-Rigs review models at their authored metric scale. The band
and its instruments are played live. Keep only their rug from the fit study.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Matrix, Vector
import export_vehicles as fleet


def wreck(parts):
    # Both halves roll about the fifth wheel. Blender's Z is vertical and
    # +Y is forward after gather(). Set each half down on its lowest corner.
    hitch = Vector((0, -2.93, 1.2))
    fallen = []
    for trailer, yaw, roll in ((True, 15, -99), (False, 62, 84)):
        half = [obj for obj, src in parts if any(c.name.startswith('05 |') for c in src.users_collection) == trailer]
        broken = fleet.copies(half)
        turn = Matrix.Rotation(math.radians(-yaw), 4, 'Z') @ Matrix.Rotation(math.radians(-roll), 4, 'Y')
        for obj in broken:
            obj.data.transform(turn @ Matrix.Translation(-hitch))
        lo, _ = fleet.box(broken)
        rest = Matrix.Translation(Vector((5.2, 10.5, -lo.z)))
        for obj in broken:
            obj.data.transform(rest)
        fallen.extend(broken)
    fleet.write('BandFlatbedWreck', fallen, Vector((0, 0, 0)))


def export(source, name):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(fleet.ART, 'Big-Rigs', source, source + '.blend'))
    exclude = {o.name for c in bpy.data.collections if c.name.startswith(('06 |', '07 |'))
               for o in c.all_objects if o.name != 'Drum rug'}
    fleet.GLASS['Smoked safety glass'] = 0.18
    fleet.LIT.update({'Amber glass': 1.8, 'Ruby glass': 2.8, 'Fluted headlamp glass': 4.0})
    fleet.prepare_materials()
    parts, _ = fleet.gather(1.0, exclude)
    origin = Vector((0, 0, 0))

    if name == 'BandFlatbed':
        wreck(parts)

    # Each export contains both sides of one axle. The four tandem axles
    # share a mesh, including the inner tyres and the outer chrome hardware.
    wheels = ('Road tire', 'Pressed wheel rim', 'Wheel dish', 'Oil hub', 'Lug nut', 'Rim vent')
    body, steer, dual = [], [], []
    tractor, trailer = [], []
    for obj, src in parts:
        if not src.name.startswith(wheels):
            body.append(obj)
            # The articulated rig (the scene sways the trailer on the fifth wheel): the trailer
            # is collection 05. The rug isn't either's: the band brings its own.
            if src.name != 'Drum rug':
                (trailer if any(c.name.startswith('05 |') for c in src.users_collection) else tractor).append(obj)
            continue
        if name == 'FreightCabover':
            continue  # Both trucks use the same steer wheels and duals.
        lo, hi = fleet.box([obj])
        z = (lo.y + hi.y) * 0.5
        if abs(z - 2.62) < 0.5:
            steer.append(obj)
        elif abs(z + 2.19) < 0.5:
            dual.append(obj)
    if name == 'BandFlatbed':
        # The tractor about the rig's origin; the trailer about its kingpin, on the fifth wheel
        # (as wreck() turns it), where the scene hangs it.
        fleet.write('BandTractor', fleet.copies(tractor), origin)
        fleet.write('BandTrailer', fleet.copies(trailer), Vector((0, -2.93, 1.2)))
    fleet.write(name, body, origin)
    if name == 'FreightCabover':
        return
    fleet.write('RigSteerWheels', steer, Vector((0, 2.62, 0.55)))
    fleet.write('RigDualWheels', dual, Vector((0, -2.19, 0.55)))


export('Band-Flatbed', 'BandFlatbed')
export('Freight-Cabover', 'FreightCabover')
