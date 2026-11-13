"""Run with blender -b --python Tools/InstrumentAssets/build.py -- Drumkit (or Guitar/Bass/MicStand).
Authored in game coordinates: metres, Y up, audience/front +Z.
"""
import bpy, math, sys, json
from pathlib import Path
from mathutils import Vector, Matrix
ROOT = Path(__file__).resolve().parents[2]
NAME = sys.argv[sys.argv.index('--')+1]
OUT = ROOT / 'Assets/Models/Instruments' / NAME
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
def material(name, color, metal=0, rough=.4):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Metallic'].default_value=metal; p.inputs['Roughness'].default_value=rough
    return m
red=material('Oxblood lacquer',(.19,.008,.016),.25,.28)
blue=material('Midnight petrol lacquer',(.008,.055,.073),.3,.27)
chrome=material('Satin chrome',(.52,.59,.64),.85,.24)
black=material('Rubber and black hardware',(.012,.016,.02),.1,.55)
head=material('Ivory coated head',(.78,.75,.66),0,.65)
gold=material('Brushed bronze',(.62,.39,.11),.8,.32)
wood=material('Maple',(.55,.31,.12),0,.4)
board=material('Rosewood',(.055,.024,.012),0,.45)
white=material('Ivory pickguard',(.87,.84,.71),0,.3)
def finish(o,name,mat):
    o.name=name; o.data.materials.append(mat); return o
def box(name,loc,size,mat,bevel=.005):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=bpy.context.object; o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        mod=o.modifiers.new('Machined edges','BEVEL'); mod.width=bevel; mod.segments=3
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return finish(o,name,mat)
def rod(name,a,b,r,mat,vertices=16,r2=None):
    d=Vector(b)-Vector(a)
    bpy.ops.mesh.primitive_cone_add(vertices=vertices,radius1=r,radius2=r if r2 is None else r2,depth=d.length,location=(Vector(a)+Vector(b))/2)
    o=bpy.context.object; o.rotation_euler=d.to_track_quat('Z','Y').to_euler()
    for p in o.data.polygons: p.use_smooth=len(p.vertices)==4
    return finish(o,name,mat)
def ring(name,c,r,t,mat,axis='Y'):
    bpy.ops.mesh.primitive_torus_add(major_segments=48,minor_segments=6,location=c,major_radius=r,minor_radius=t)
    o=bpy.context.object
    if axis=='Y': o.rotation_euler[0]=math.pi/2
    for p in o.data.polygons:p.use_smooth=True
    return finish(o,name,mat)
def stand(name,x,z,h):
    rod(name+' lower',(x,.12,z),(x,h*.6,z),.012,chrome)
    rod(name+' upper',(x,h*.55,z),(x,h,z),.008,chrome)
    rod(name+' clutch',(x,h*.57-.025,z),(x,h*.57+.025,z),.02,black)
    for i in range(3):
        a=i*math.tau/3; foot=(x+.23*math.cos(a),.025,z+.23*math.sin(a))
        rod(name+' tripod',(x,.23,z),foot,.009,chrome)
        rod(name+' rubber foot',foot,(foot[0],.012,foot[2]),.018,black)
def drum(name,c,r,depth,kick=False):
    start=set(bpy.data.objects); x,y,z=c
    def at(a,b,v):return (x+a,y+b,z+v) if kick else (x+a,y+v,z+b)
    rod(name+' shell',at(0,0,-depth/2),at(0,0,depth/2),r,red,48)
    for side in [-1,1]:
        v=side*depth/2
        ring(name+' inner hoop',at(0,0,v),r*.94,.003,chrome,'Z' if kick else 'Y')
        rod(name+' head',at(0,0,v),at(0,0,v+side*.004),r*.96,black if kick and side==1 else head,48)
        ring(name+' hoop',at(0,0,v+side*.009),r,.009,chrome,'Z' if kick else 'Y')
        for i in range(10 if kick else 8):
            a=i*math.tau/(10 if kick else 8); xx=(r+.008)*math.cos(a); yy=(r+.008)*math.sin(a)
            rod(name+' tension lug',at(xx,yy,side*(depth/2-.055)),at(xx,yy,side*(depth/2-.02)),.009,chrome,12)
            rod(name+' tension screw',at(xx,yy,side*(depth/2-.02)),at(xx,yy,side*(depth/2+.008)),.003,chrome,12)
    # Named parent is the drum's animation pivot; children retain their world transforms.
    bpy.ops.object.empty_add(location=c); parent=bpy.context.object; parent.name=name
    for o in set(bpy.data.objects)-start-{parent}: o.parent=parent; o.matrix_parent_inverse=parent.matrix_world.inverted()
    return parent

def cymbal(name,x,y,z,r):
    stand(name+' stand',x,z,y)
    verts=[]; faces=[]; profile=[(.012,.036),(.035,.035),(.065,.012),(r*.7,.002),(r,0),(r,-.003),(r*.7,-.002),(.065,.007),(.035,.03),(.012,.03)]
    for rad,h in profile:
        verts.extend([(x+rad*math.cos(i*math.tau/64),y+h,z+rad*math.sin(i*math.tau/64)) for i in range(64)])
    for j in range(len(profile)):
        for i in range(64):faces.append((j*64+i,j*64+(i+1)%64,((j+1)%len(profile))*64+(i+1)%64,((j+1)%len(profile))*64+i))
    mesh=bpy.data.meshes.new(name); mesh.from_pydata(verts,[],faces); mesh.update()
    o=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(o); finish(o,name,gold)
    # Origin at centre for future cymbal wobble.
    for v in mesh.vertices:v.co-=Vector((x,y,z))
    o.location=(x,y,z)
    for p in mesh.polygons:p.use_smooth=True
    for rr in [.49,.56,.63,.70,.77,.84,.91,.97]:
        radius=r*rr
        h=(.012+(.002-.012)*(radius-.065)/(r*.7-.065)) if rr<.7 else .002*(1-rr)/.3
        ring(name+' lathe groove',(x,y+h,z),radius,.0002,gold)
    rod(name+' felt',(x,y+.032,z),(x,y+.048,z),.016,black)
    box(name+' wingnut',(x,y+.058,z),(.04,.006,.009),chrome,.002)

def drumkit():
    drum('Kick',(0,.31,.9),.3,.44,True)
    drum('Snare',(-.28,.65,.32),.18,.13)
    drum('Tom1',(-.24,.91,.74),.14,.2)
    drum('Tom2',(.17,.91,.76),.15,.22)
    drum('FloorTom',(.52,.56,.45),.21,.42)
    stand('Snare basket',-.28,.32,.59)
    for x in [-.24,.17]:rod('Tom mount',(0,.56,.88),(x,.86,.74),.014,chrome)
    for i in range(3):
        a=i*math.tau/3; x=.52+.22*math.cos(a); z=.45+.22*math.sin(a)
        rod('Floor tom leg',(x,.55,z),(x,.025,z),.009,chrome)
    for x in [-.28,.28]:rod('Kick spur',(x,.26,.96),(x*1.4,.025,1.1),.012,chrome)
    for args in [('HiHat',-.61,.9,.3,.18),('Crash1',-.65,1.19,.87,.23),('Crash2',.55,1.26,1.02,.24),('Ride',.79,1.02,.61,.28)]:cymbal(*args)
    rod('HiHat lower plate',(-.61,.88,.3),(-.61,.884,.3),.18,gold,64)
    for x,z in [(0,.55),(-.61,.24)]:
        box('Pedal base',(x,.018,z),(.09,.024,.23),black)
        box('Pedal footboard',(x,.04,z),(.065,.012,.18),chrome)
        for j in range(5):box('Pedal grip',(x,.048,z-.06+j*.025),(.06,.004,.004),black,.001)
    rod('Kick beater shaft',(0,.055,.65),(0,.29,.67),.005,chrome)
    rod('Kick felt beater',(0,.29,.65),(0,.29,.7),.026,head)
    stand('Throne',0,-.04,.49)
    rod('Throne cushion',(0,.49,-.04),(0,.58,-.04),.19,black,48)

# Smooth carved outline, extruded along the instrument face (+Z).
def outline(name,points,depth,mat,z=0):
    # Catmull-Rom interpolation keeps hand-authored curves editable in this script.
    pts=[]
    for i in range(len(points)):
        a,b,c,d=[Vector(points[j%len(points)]) for j in (i-1,i,i+1,i+2)]
        for k in range(12):
            t=k/12; p=.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t);pts.append(p)
    n=len(pts); vs=[(p.x,p.y,z+s*depth/2) for s in [-1,1] for p in pts]
    fs=[tuple(reversed(range(n))),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);finish(o,name,mat)
    bpy.context.view_layer.objects.active=o;o.select_set(True)
    mod=o.modifiers.new('Soft body edge','BEVEL');mod.width=.008;mod.segments=3
    bpy.ops.object.modifier_apply(modifier=mod.name)
    for face in o.data.polygons:face.use_smooth=len(face.vertices)==4
    o.select_set(False)
    return o

def stringed(bass=False):
    neck=.86 if bass else .62; nut=-.18-neck; count=4 if bass else 6
    # Neck runs through the pocket and into the body: no floating fretboard across a cutaway.
    # Guitar: rounded single-cut body. Bass: offset double-cut with restrained horns.
    points=([(.29,-.015),(.265,.09),(.19,.145),(.10,.15),(.015,.12),(-.065,.095),(-.17,.12),(-.265,.10),(-.28,.075),(-.245,.06),(-.18,.045),(-.16,.025),(-.16,-.026),(-.195,-.055),(-.23,-.075),(-.22,-.10),(-.16,-.105),(-.065,-.075),(.025,-.115),(.12,-.155),(.22,-.13)] if bass else
        [(.29,0),(.265,.10),(.19,.155),(.085,.16),(.015,.13),(-.055,.13),(-.145,.115),(-.20,.075),(-.215,.025),(-.19,-.015),(-.13,-.025),(-.105,-.055),(-.09,-.095),(-.015,-.10),(.065,-.15),(.17,-.16),(.255,-.11)])
    outline('Carved body',points,.060,blue if bass else red)
    if bass:
        guard=[(.13,.065),(.015,.088),(-.07,.063),(-.157,.03),(-.155,-.03),(-.07,-.052),(.035,-.08),(.13,-.055)]
        screws=[(.11,.055),(-.07,.05),(-.14,-.023),(.09,-.055)]
    else:
        guard=[(-.10,-.043),(-.02,-.045),(.075,-.047),(.085,-.105),(.015,-.11),(-.075,-.083)]
        screws=[(-.076,-.057),(.065,-.09)]
    outline('Inset pickguard',guard,.0025,black if bass else white,.032)
    for x,y in screws:
        rod('Pickguard screw',(x,y,.034),(x,y,.036),.0023,chrome,12)
        box('Screw slot',(x,y,.0365),(.003,.0006,.0004),black,.0001)
    joint=-.085
    box('Maple neck',((nut+joint)/2,0,.005),(joint-nut,.051,.035),wood,.008)
    box('Rosewood fingerboard',((nut+joint)/2,0,.027),(joint-nut,.052,.012),board,.002)
    box('Neck heel',(-.13,0,-.005),(.11,.056,.045),wood,.008)
    box('Neck mounting plate',(-.13,0,-.030),(.065,.045,.003),chrome,.003)
    outline('Headstock',[(nut+.016,.024),(nut-.045,.031),(nut-.15,.046),(nut-.19,.032),(nut-.195,-.011),(nut-.16,-.029),(nut-.045,-.025),(nut+.016,-.024)],.026,wood,.01)
    box('Nut',(nut,0,.038),(.006,.052,.009),white,.001)
    scale=neck/(1-2**(-16/12))
    for fret in range(1,22):
        x=nut+scale*(1-2**(-fret/12))
        if x>-.085:break
        box('Fret %02d'%fret,(x,0,.036),(.002,.052,.003),chrome,.0008)
        if fret in [3,5,7,9,12,15,17,19]:
            prev=nut+scale*(1-2**(-(fret-1)/12))
            for y in ([-.012,.012] if fret==12 else [0]):rod('Pearl inlay',((x+prev)/2,y,.033),((x+prev)/2,y,.034),.0035,white,12)
    for x in ([-.045,.075] if bass else [-.025,.095]):
        box('Pickup surround',(x,0,.043),(.025 if bass else .043,.078,.006),chrome,.003)
        box('Pickup',(x,0,.05),(.018 if bass else .033,.07,.009),black,.004)
        for j in range(count):rod('Pickup pole',(x,-.022+j*.044/(count-1),.055),(x,-.022+j*.044/(count-1),.057),.002,chrome,8)
    box('Bridge',(.17,0,.045),(.043,.08,.016),chrome,.004)
    for j in range(count):
        y=-.021+j*.042/(count-1)
        rod('String %d'%(j+1),(nut,y,.045),(.19,y,.058),.00065 if bass else .0004,chrome,6)
        box('Bridge saddle',(.17,y,.058),(.024,.008,.005),chrome,.001)
        tx=nut-.035-j*(.035 if bass else .023)
        rod('Headstock string',(nut,y,.045),(tx,.025,.04),.00065 if bass else .0004,chrome,6)
        rod('Tuner post',(tx,.025,.022),(tx,.025,.04),.004,chrome,12)
        rod('Tuner axle',(tx,.022,.015),(tx,.053,.015),.003,chrome)
        box('Tuning key',(tx,.057,.015),(.017,.012,.009),chrome,.004)
    for x,y in [(.17,-.094),(.1,-.12)]:rod('Control knob',(x,y,.034),(x,y,.055),.013,chrome,24)
    rod('Strap button',(.285,0,0),(.3,0,0),.007,chrome)
    box('Selector plate',(.01,-.079,.036),(.04,.01,.003),chrome,.003)
    rod('Selector lever',(.01,-.079,.036),(.018,-.079,.06),.002,chrome)
    rod('Selector tip',(.018,-.079,.056),(.019,-.079,.064),.0035,white)
    rod('Output jack',(.21,-.09,.034),(.21,-.09,.039),.012,chrome)

def micstand():
    # Local root at floor; microphone height follows Band::BuildMicStand default.
    rod('Weighted base',(0,.008,0),(0,.035,0),.15,black,64)
    ring('Base edge',(0,.023,0),.143,.008,black)
    rod('Lower tube',(0,.035,0),(0,.86,0),.012,black,24)
    rod('Telescoping tube',(0,.8,0),(0,1.47,0),.008,chrome,24)
    rod('Height clutch',(0,.79,0),(0,.86,0),.021,black,24)
    for y in [.8,.815,.83,.845]:ring('Clutch grip',(0,y,0),.021,.0015,black)
    rod('Mic clip',(0,1.46,.005),(0,1.50,-.055),.023,black)
    rod('Microphone body',(0,1.48,.015),(0,1.53,-.12),.021,black,32,r2=.025)
    rod('Grille',(0,1.53,-.12),(0,1.55,-.18),.029,chrome,32,r2=.023)
    axis=Vector((0,.02,-.06)).normalized(); centre=Vector((0,1.54,-.15))
    for j in range(13):
        c=centre+axis*((j-6)*.004)
        ob=ring('Grille woven ring',c,.027,.0007,chrome,'Z')
        ob.rotation_euler=axis.to_track_quat('Z','Y').to_euler()
    u=Vector((1,0,0));v=axis.cross(u)
    for i in range(24):
        off=(u*math.cos(i*math.tau/24)+v*math.sin(i*math.tau/24))*.027
        rod('Grille woven rib',centre+off-axis*.026,centre+off+axis*.026,.00065,black,6)
    # Cable drops from the mic and loops naturally onto the floor.
    cu=bpy.data.curves.new('Cable','CURVE');cu.dimensions='3D';cu.bevel_depth=.003;cu.bevel_resolution=2
    sp=cu.splines.new('BEZIER');ps=[(0,1.48,.03),(.045,1.35,.08),(.035,.8,.04),(.025,.1,.03),(.15,.008,.2),(.38,.008,.17),(.45,.008,-.05),(.3,.008,-.18),(.12,.008,-.14)]
    sp.bezier_points.add(len(ps)-1)
    for p,co in zip(sp.bezier_points,ps):p.co=co;p.handle_left_type=p.handle_right_type='AUTO'
    ob=bpy.data.objects.new('Microphone cable',cu);bpy.context.collection.objects.link(ob);ob.data.materials.append(black)

def keyboard():
    panel=material('Anodised graphite',(.035,.043,.052),.5,.38)
    led=material('Display blue',(.025,.24,.36),.15,.25)
    box('Stage piano chassis',(0,.917,.42),(1.2,.085,.34),panel,.018)
    for x in [-.583,.583]:box('Walnut end cheek',(x,.93,.42),(.034,.08,.34),wood,.009)
    # 61 keys: 36 white naturals and 25 black accidentals, front edge toward player (-Z).
    pitch=1.07/36
    for i in range(36):
        x=-.535+(i+.5)*pitch
        box('White key %02d'%i,(x,.963,.347),(pitch-.001,.018,.174),white,.002)
        if i<35 and i%7 in [0,1,3,4,5]:
            box('Black key %02d'%i,(x+pitch/2,.981,.389),(pitch*.57,.025,.092),black,.002)
    box('Control panel',(0,.963,.514),(1.09,.012,.09),panel,.004)
    box('Display bezel',(0,.972,.515),(.17,.008,.065),black,.004)
    box('LCD',(0,.977,.515),(.14,.002,.045),led,.002)
    for i in range(4):box('LCD meter',(-.05+i*.028,.979,.514),(.014,.001,.024),white,.001)
    for i in range(8):
        x=-.48+i*.035
        rod('Encoder',(x,.97,.52),(x,.99,.52),.011,black,20)
        box('Encoder indicator',(x,.991,.523),(.002,.001,.009),white,.0004)
    for i in range(8):
        x=.19+i*.042
        box('Fader track',(x,.971,.516),(.003,.002,.052),black,.001)
        box('Fader cap',(x,.979,.512),(.025,.009,.012),chrome,.002)
    for z in [.32,.52]:
        for side in [-1,1]:
            rod('Double X stand',(side*.38,.04,z),(-side*.38,.87,z),.016,black,20)
        rod('Stand pivot',(0,.455,z-.025),(0,.455,z+.025),.028,chrome,24)
    for x in [-.38,.38]:
        rod('Stand foot',(x,.025,.22),(x,.025,.62),.022,black,20)
        rod('Stand cradle',(x,.866,.27),(x,.866,.58),.018,black,20)
    box('Sustain pedal',(.16,.025,.30),(.075,.035,.18),black,.012)
    box('Sustain tread',(.16,.048,.28),(.048,.008,.11),chrome,.004)

{'Drumkit':drumkit,'Guitar':lambda:stringed(False),'Bass':lambda:stringed(True),'MicStand':micstand,'Keyboard':keyboard}[NAME]()
# Freeze only geometry modifiers, preserving named object origins and assembly parents.
bpy.ops.object.select_all(action='DESELECT')
for o in list(bpy.context.scene.objects):
    if o.type=='CURVE':
        o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.object.convert(target='MESH');o.select_set(False)
models=list(bpy.context.scene.objects)
for o in models:o.select_set(True)
bpy.ops.wm.obj_export(filepath=str(OUT/(NAME+'.obj')),export_selected_objects=True,forward_axis='Y',up_axis='Z',export_triangulated_mesh=True)
bpy.ops.export_scene.fbx(filepath=str(OUT/(NAME+'.fbx')),use_selection=True,axis_forward='-Z',axis_up='Y',add_leaf_bones=False,bake_anim=False)
# Record local transforms for eventual replacement/animation hookup.
manifest={'name':NAME,'units':'metres','coordinates':'Y up, +Z front; stringed neck along -X','objects':[]}
triangles=0
for o in models:
    if o.type=='MESH':o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
    manifest['objects'].append({'name':o.name,'parent':o.parent.name if o.parent else None,'position':list(o.location)})
manifest['triangles']=triangles
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
# Studio previews are rendered from geometry, not image-generated concepts.
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32
scene.render.resolution_x=1200;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.world.color=(.16,.16,.16);scene.render.image_settings.file_format='PNG'
if NAME=='Drumkit': target=Vector((0,.65,.6));cam=(2.8,2.4,4.5);ortho=2.8
elif NAME=='Keyboard':target=Vector((0,.55,.42));cam=(1.7,1.8,-2.3);ortho=1.65
elif NAME=='MicStand':target=Vector((.1,.8,0));cam=(2,1.9,3.5);ortho=2
else:target=Vector((-.35 if NAME=='Guitar' else -.47,0,0));cam=target+Vector((.12,.42,3));ortho=1.45 if NAME=='Guitar' else 1.7
bpy.ops.object.camera_add(location=cam);camera=bpy.context.object;camera.name='Preview camera';camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();back=(camera.location-target).normalized(); right=Vector((0,1,0)).cross(back).normalized(); up=back.cross(right); camera.rotation_euler=Matrix((right,up,back)).transposed().to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=ortho;scene.camera=camera
for loc,power,size in [((1,4,4),450,4),((-3,2,1),350,3),((0,3,-3),650,2)]:
    bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
scene.render.film_transparent=True
bpy.ops.object.select_all(action='DESELECT')
for o in models:o.select_set(True)
bpy.context.view_layer.objects.active=next(o for o in models if o.type=='MESH')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(NAME+'.blend')))
scene.render.filepath=str(OUT/'preview.png');bpy.ops.render.render(write_still=True)
print('ASSET_COMPLETE',NAME,triangles)
