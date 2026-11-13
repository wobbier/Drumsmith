"""blender -b --python Tools/InstrumentAssets/prepare_runtime.py
Export game-coordinate meshes with Z pre-flipped for Assimp ConvertToLeftHanded.
Drums use local animation origins; static hardware is exported separately.
"""
import bpy, json, secrets
from pathlib import Path
from mathutils import Vector, Matrix
ROOT=Path(__file__).resolve().parents[2]/'Assets/Models/Instruments'
def export(name, objects, pivot=(0,0,0), offsets=None, scales=None):
    dest=ROOT/'Runtime';dest.mkdir(exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    copies=[]
    for src in objects:
        ob=bpy.data.objects.new(src.name,src.data.copy());bpy.context.collection.objects.link(ob)
        mat=Matrix.Translation(-Vector(pivot)) @ src.matrix_world
        if scales and src.name in scales:mat=Matrix.Diagonal((1,scales[src.name],1,1)) @ mat
        if offsets and src.name in offsets:mat=Matrix.Translation(Vector(offsets[src.name])) @ mat
        ob.data.transform(Matrix.Diagonal((1,1,-1,1)) @ mat)
        # Reflection changes orientation; restore outward winding before the importer reflection.
        for poly in ob.data.polygons:poly.flip()
        ob.data.update();ob.select_set(True);copies.append(ob)
    # Join the rigid assembly to keep imports grouped by material rather than tiny objects.
    bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join()
    bpy.ops.wm.obj_export(filepath=str(dest/(name+'.obj')),export_selected_objects=True,forward_axis='Y',up_axis='Z',export_triangulated_mesh=True)
    meta=dest/(name+'.obj.meta')
    if not meta.exists():meta.write_text(json.dumps({'ConvertUnits':False,'FileType':'obj','GUID':secrets.token_hex(8)},indent=4)+'\n')
    bpy.data.objects.remove(bpy.context.object,do_unlink=True)
for name in ['MicStand','Guitar','Bass','Keyboard']:
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/name/(name+'.blend')))
    export(name,[o for o in bpy.context.scene.objects if o.type=='MESH'])
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Drumkit/Drumkit.blend'))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];used=set()
# Centres place top heads on the established Band::kStrike targets.
centres={'Kick':(0,.31,.9),'Snare':(-.16,.671,.6),'Tom1':(-.15,.846,.82),'Tom2':(.18,.836,.82),'FloorTom':(.52,.466,.52)}
offsets={};scales={}
for name,c in centres.items():
    parent=bpy.data.objects[name]; objects=[o for o in meshes if o.parent==parent];used.update(objects)
    export(name,objects,parent.location)
    if name=='Snare':
        delta=Vector(c)-parent.location
        for o in meshes:
            if o.name.startswith('Snare basket'):offsets[o.name]=(delta.x,0,delta.z)
# Upper cymbals move with all their hardware; their stands stay fixed.
for name,target in {'HiHat':(-.44,.97,.56),'Crash1':(-.6,1.26,.98),'Crash2':(.55,1.3,1.04),'Ride':(.72,1.04,.76)}.items():
    pivot=bpy.data.objects[name].location.copy()
    objects=[o for o in meshes if o.name==name or o.name.startswith(name+' lathe') or o.name.startswith(name+' felt') or o.name.startswith(name+' wingnut')]
    used.update(objects);export(name,objects,pivot)
    delta=Vector(target)-pivot
    for o in meshes:
        if o.name.startswith(name+' stand') or (name=='HiHat' and o.name.startswith('HiHat lower')):offsets[o.name]=(delta.x,0,delta.z);scales[o.name]=target[1]/pivot.y
# Pedal footboards follow the unchanged foot IK targets.
for o in meshes:
    if o.name.startswith('Pedal'):
        offsets[o.name]=(.35,0,.20) if o.location.x < -.3 else (.12,0,-.03)
export('DrumHardware',[o for o in meshes if o not in used],offsets=offsets,scales=scales)
print('Runtime exports complete')
