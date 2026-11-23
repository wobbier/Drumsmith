#!/usr/bin/env python3
"""Build the actual Last House Awake venue, its meshes and joint performances. No editor required."""
import json
import math
from collections import Counter

from backyard_drop import stage_drop
from backyard_guests import clips, place_guests
from backyard_meshes import ART, MODELS, backdrop, canopy, decks, flyers, geo, mesh_file, paper_cup, party_traces, picnic_rug, practical_glass, promote, shutter, throw, water_traces
from venuegen import Scene, look_rotation, write_venue_json


LOCAL='Assets/Venues/Backyard/Models/'
AMBER=(1,.48,.115); HONEY=(1,.76,.41); PINK=(1,.045,.245); ICE=(.055,.81,1); BLUE=(.20,.29,1)


def build():
    layout=json.loads((ART/'layout.json').read_text()); promote(layout)
    backdrop(); decks(); flyers(); canopy(); shutter(); water_traces(); party_traces(); paper_cup(); throw(); picnic_rug(); practical_glass(); clips()
    s=Scene('backyard-after-hours-v2'); root=s.group('Last House Awake')
    ground=s.group('Yard, house and kerb',root); party=s.group('Someone brought their living room',root)
    setbits=s.group('Paint, wires and practicals',root); cast=s.group('Friends of friends',root)
    lamps=s.group('Porch sockets and borrowed lights',root); marks=s.group('Venue markers',root)
    tally=Counter()
    for p in layout['primitives']:
        rgb=tuple(int(p['colour'][i:i+2],16)/255 for i in (1,3,5))
        colour=(.089,.135,.102) if p['id'].startswith('lawn') else tuple(c**1.65 for c in rgb)
        s.box(p['id'].replace('_',' '),ground,p['centre'],p['size'],colour)
    s.slab('Earth beyond the garden',ground,-64,64,-.32,-.19,-59,46,(.033,.039,.052))
    for p in layout['props']:
        name=p['asset_id'];idx=tally[name];tally[name]+=1
        if name=='Festoon2m': continue
        if name=='FloodLight' and idx in (0,3): continue
        xyz=list(p['position']); yaw=p['yaw_degrees']; scale=p['scale']; roll=p.get('roll_degrees',0)
        if name=='PatioChair' and idx==1: xyz=[-4.02,0,-17.92];yaw=136
        if name=='PatioChair' and idx==5: xyz=[5.68,.005,-15.34];yaw=-40;roll=-77;xyz[1]=.26
        if name=='PatioTable': xyz=[9.0,0,3.40];yaw=-17
        if name=='Sofa': xyz=[-2.14,0,-20.27];yaw=178
        if name=='Cooler' and xyz[2]<-19 and abs(xyz[0])<1: xyz=[-.69,0,-20.37];yaw=-15
        if name=='OneMoreSongBanner': xyz=[-5.4,.54,-21.79];yaw=176
        if name=='PartyConvertible' and idx==0: yaw=67
        if name=='PatrolLightbar': xyz[1]=1.35
        if name=='FloodLight' and idx in (1,2): xyz[1]=3.13
        if name=='NeighbourHouse': scale=.89;xyz[2]+=1.6
        path=p['path'] if p['path'].startswith('Assets/') else LOCAL+name+'.obj'
        if name=='BeerCup' and idx%3!=0: path=LOCAL+'PaperCup.obj'
        node=s.entity(f'{name} {idx+1:02}',ground if name in ('PartyHouse','PrivacyFence','FencePost','GardenTree','NeighbourHouse','PatioDeck','PoolBasin','PoolWater') else party,
                      xyz,(0,yaw,roll),(scale,)*3 if isinstance(scale,(float,int)) else scale)
        if name in ('FloatRing','FloatBed','NoveltyFloat'):
            float_mesh=s.entity('On the water',node)
            node.add({'Type':'Sequence','Clip':'Assets/Venues/Backyard/Motion/PoolDrift.sequence','PlayOnStart':True,
                      'Loop':True,'Speed':{'NoveltyFloat':.83,'FloatBed':1.06,'FloatRing':1.15-.19*idx}[name],
                      'Bindings':[{'Slot':'Float','Target':float_mesh.guid}]});node=float_mesh
        node.add({'Type':'Model','ModelPath':path})

    def model(name,parent,at,yaw=0): return s.prop(name,parent,LOCAL+name+'.obj',at,yaw)
    model('AftersDrop',setbits,(-1.45,4.40,7.70),-2.0)
    model('DoorDecks',party,(7.16,.025,1.76),-5)
    model('PatchworkFly',setbits,(7.72,3.34,2.12),-7)
    model('RadioShutter',setbits,(8.74,.18,7.969),0)
    model('BeachTowel',party,(-2.78,.008,-20.27),178)
    model('PicnicRug',party,(-2.11,.012,-19.52),-11)
    model('BeachTowel',party,(7.55,-.47,-9.68),177)
    model('PoolWakes',setbits,(0,-.078,0));model('PatioMorning',setbits,(0,0,0))
    for x,z,scale,yaw in [(-10.2,18.7,1.47,40),(-16.1,7.5,1.3,80),(3.4,22.5,1.58,-70),(13.5,16.4,1.45,21)]:
        s.prop('Trees over the fence',ground,LOCAL+'GardenTree.obj',(x,0,z),yaw,scale)
    for pos,yaw in [((1.71,.06,-22.12),-12),((-1.81,.03,-22.12),-2),((-3.80,.20,-21.82),176),((-8.19,.0,-9.85),41),((5.12,.35,7.69),-4)]:
        model('GateFlyers',setbits,pos,yaw)

    rig=geo.Mesh('GardenRigging','Installed in venue space: drooping festoons, pennants, knot poles, taped leads, patio rigging, flyer and TV supports.')
    def pole(a,b,r=.037):
        rig.tube(a,b,r,r*.92,'wood',6);x,y,z=b
        rig.tube((x,y-.16,z),(x,y-.10,z),r*1.15,r*1.15,'silver',6)
    def lit(name,pos,size,col,power,shape='Sphere',rot=(0,0,0)):
        if shape=='Sphere':
            node=s.entity(name,setbits,pos,rot,[v/2 for v in size])
            part={'CastShadows':False,'Material':{'Type':'StandardMaterial','DiffuseColor':col,
                  'Roughness':.9,'EmissiveColor':col,'EmissiveIntensity':power}}
            node.add({'Type':'Model','ModelPath':LOCAL+'PracticalGlass.obj','Compact':True,
                      'Parts':{'PracticalGlass.obj#0/PracticalGlass#0/@#0':part}})
            return node
        return s.box(name,setbits,pos,size,col,rot,emissive=col,emissive_intensity=power,shadows=False,shape=shape)
    runs=[((-12.9,4.73,-17.45),(6.08,3.98,-12.62),1.04,15), ((-7.95,4.94,-8.18),(12.55,4.82,-3.16),1.15,16),
          ((-12.9,4.73,-17.45),(-7.95,4.94,-8.18),.58,9), ((-7.95,4.94,-8.18),(3.85,4.63,3.06),.67,13),
          ((-3.04,3.95,3.61),(3.03,4.02,3.58),.32,7), ((6.08,3.98,-12.62),(12.55,4.82,-3.16),.7,9),
          ((-7.53,3.85,-21.62),(6.08,3.98,-12.62),.64,12),((-6.15,3.02,-21.56),(1.67,2.96,-20.91),.39,8)]
    sockets=set();palette=(HONEY,AMBER,HONEY,PINK,HONEY,ICE)
    for k,(a,b,sag,count) in enumerate(runs):
        def cable(t): return tuple(j+(l-j)*t-(4*t*(1-t)*sag if i==1 else 0) for i,(j,l) in enumerate(zip(a,b)))
        sockets.update((a,b));prev=a
        for i in range(1,count+1):
            end=cable(i/count); rig.tube(prev,end,.014,.014,'rubber',5);prev=end
            x,y,z=cable((i-.5)/count);drop=.09+.065*((i+k)%3);rig.tube((x,y,z),(x,y-drop,z),.018,.022,'black',6)
            col=palette[(i+2*k)%len(palette)]; lit(f'Bulb {k+1}/{i}',(x,y-drop-.05,z),(.092,.132,.092),col,3.0)
            if k in (0,1,3,6) and i%3!=0:
                t=(i-.82)/count; ax,ay,az=cable(t);bx,by,bz=cable(t+.020);tip=((ax+bx)/2+.12,min(ay,by)-.28-.10*((i+k)%3),(az+bz)/2+.14)
                tri=[(ax,ay,az),(bx,by,bz),tip];ink=('cream','pink','orange','aqua')[(i+k)%4];rig.face(tri,ink);rig.face(tri[::-1],ink)
    for x,y,z in sorted(sockets):
        if z < 0 or abs(x)>3.7: pole((x-.1,0,z+.07),(x,y+.08,z),.055)
    for a in ((4.32,4.4,.13),(11.56,4.36,.45),(3.72,4.26,3.93),(11.14,4.91,4.5)):
        pole((a[0],0,a[2]),a,.053)
    for x,z,h in [(-9.99,5.54,3),(-8.01,5.54,3),(10.4,4.63,2.14),(-6, -1,3.16),(6,-1,3.16),(-7.3,3,3.22),(-7.6,-.4,2.13),(7.6,-.4,2.13),(-8.19,-9.82,1.66)]:
        pole((x,0,z),(x,h,z),.048)
    for x in (-5.94,3.03):
        pole((x,5.12,7.77),(x,7.53,7.77),.057)
        rig.tube((x,7.45,7.77),(x-.55,5.51,8.9),.025,.025,'cream',5)
    for route in [[(6.1,.03,1.77),(5.46,.03,1.33),(5.02,.03,.55),(4.69,.03,.30),(4.41,.03,-.36)],
                  [(-9.7,.03,-5.5),(-8.3,.03,-5.75),(-7.87,.03,-4.29),(-7.91,.03,-2.45),(-7.36,.03,-.53)]]:
        for a,b in zip(route,route[1:]): rig.tube(a,b,.018,.018,'orange',5)
    mesh_file(rig,False); model('GardenRigging',setbits,(0,0,0))

    for i,(x,z,side) in enumerate([(5.19,-7.88,1),(10.82,-5.88,-1),(5.18,-3.84,1)]):
        lit(f'Submerged tile lamp {i}',(x,-.015,z),(.10,.067,.30),ICE,2.1,'Cube')
    for i,(x,z) in enumerate([(-8.2,-1),(12.2,-.9),(-7.5,-19),(12.3,-19)]):
        lit(f'Torch wick {i}',(x,1.78,z),(.095,.17,.09),AMBER,2.6)
    for i,(x,col) in enumerate(((15.69,PINK),(16.3,BLUE))): lit(f'Beyond the fence {i}',(x,1.50,18),(.22,.09,.16),col,2,'Cube')
    for i in range(3):
        lit('Receiver lamp '+str(i),(6.95+i*.09,.985,1.74),(.029,.017,.04),ICE if i==0 else AMBER,1.8,'Cube')
    for i,(x,z,yaw) in enumerate([(-6,-1,0),(6,-1,0),(-7.6,-.4,0),(7.6,-.4,0)]):
        lit(f'Work lamp glass {i}',(x,3.31 if i<2 else 2.28,z-.08),(.22,.12,.07),HONEY,1.5,'Cube',(0,yaw,0))

    def point(n,pos,color,power,reach,role='Static',group=0):
        s.light(n,lamps,pos,'Point',color,power,reach,show=role,group=group)
    def spot(n,pos,to,color,power,reach,inner,outer,role='Static',group=0):
        s.light(n,lamps,pos,'Spot',color,power,reach,rot=look_rotation(pos,to),inner=inner,outer=outer,show=role,group=group)
    s.light('Moon from over the back gate',lamps,(-12,30,-16),'Directional',(.59,.67,1),1.45,rot=(46,24,0),shadows=True,show='Static')
    point('Open kitchen door',(-5.15,2.12,7.15),HONEY,28,7)
    spot('Paint on the drop',(-2.9,5.45,2.25),(-1.35,5.95,7.68),(.74,.77,1),110,11,32,56)
    point('Turntables in the side yard',(7.15,2.53,1.3),(.95,.12,.34),44,7)
    point('Gate porch light',(1.22,2.75,-21.42),(.98,.69,.41),47,7.5)
    point('The light next to the sofa',(-3.48,2.27,-19.95),(1,.52,.32),29,6)
    point('Cool light from the open back gate',(-2.52,2.63,-16.97),(.50,.68,.94),46,7.8)
    point('Bulbs above the old couch',(-1.82,2.21,-19.26),(.97,.71,.49),14,4.7)
    point('Street spill through the branches',(-12.90,4.62,-12.30),(.31,.27,.72),61,10)
    point('Car radio spill',(-9.84,1.9,-6.21),PINK,75,7.5)
    point('Streetlamp behind the garage',(14.9,4.12,16.8),AMBER,82,13)
    point('Pool blue stays on',(7.8,1.35,-8.2),(.035,.57,.79),31,7.7)
    point('Dancing shoes',(5.62,2.86,-.53),(.07,.64,.94),49,7)
    spot('Borrowed worklight / kit',(1.8,3.68,.78),(0,1.85,5.3),(.94,.76,.66),148,13,19,37)
    spot('Borrowed worklight / band',(-3.7,3.86,-1.54),(-2.0,1.58,3.4),(.88,.76,.72),195,15,21,47)
    point('At the roof rail',(9.3,6.20,7.68),(.82,.30,.42),31,6.3)
    for i,(pos,color,power,reach) in enumerate([((-3.3,3.6,-2),AMBER,86,9),((-.9,3.8,-6.7),PINK,90,9),
             ((-3.88,3.9,-10.8),AMBER,93,10),((3.7,3.24,-13.43),ICE,80,8),((8.8,1.08,-4.55),ICE,41,7),
             ((-10.42,1.49,-14),PINK,72,7),((-4.5,2.38,5.9),PINK,45,8),((5.0,2.4,6.42),ICE,51,9)]):
        point(f'Fused party circuit {i+1}',pos,color,power,reach,'Wash',i%3)
    for i,(pos,to,col) in enumerate([((-5.2,5.54,7.8),(-4,1,-4),PINK),((5.2,5.5,7.8),(3,.6,-4),ICE),((-10.72,1.1,-13.05),(-10.98,3.15,-15.95),(.78,.13,.71))]):
        spot(f'Salvaged scanner {i+1}',pos,to,col,1850 if i<2 else 380,24 if i<2 else 9,6,13,'Beam',i%2)
    for i,(pos,to,col,intensity) in enumerate([((2.8,4.1,-.4),(0,1.9,5.3),(.93,.82,.74),332),((-.6,3.2,-2.6),(-.3,1.8,.9),(.97,.81,.68),310),
            ((-6,3.4,-1),(-3.7,1.75,2.4),(.94,.61,.48),320),((6,3.4,-1),(3.7,1.75,2.6),(.68,.79,1),365),((-7.3,3.5,3),(-5,1.8,5.2),HONEY,282)]):
        spot(f'Clamped follow {i+1}',pos,to,col,intensity,18,12,26,'Spot',i)
    for i,x in enumerate((-7.6,7.6)):
        spot(f'Rental flood {i}',(x,2.34,-.4),(x*.47,1,-7.5),HONEY,780,17,20,46,'Blinder',i)
    for i,(x,c) in enumerate(((15.68,PINK),(16.32,BLUE))): point(f'Kerb flash {i}',(x,1.58,17.9),c,390,16,'Strobe',i)

    s.info(marks,'Backyard Party','Drumsmith',outdoor=True,room_back=-25,half_width=14.4,desk_z=-19.7,
           fog_color=(.055,.035,.083),haze=.72,sky_time=20.66,moon=1.35,clouds=0,haze_froxels=True,footage='Mixed')
    for p in layout['band']: s.spot(marks,{'drums':'Drummer','vocals':'Vocals','keys':'Keys','bass':'Bass','guitar':'Guitar'}[p['id']],p['position'])
    for name,x0,x1,z0,z1,y,n,yaw in [
        ('Front rail',-5.66,3.25,-4.64,-1.4,0,45,0),('Crush by the amp',-6.38,-1.87,-7.56,-5.02,0,19,0),
        ('The hook',-.92,2.91,-8.70,-5.16,0,21,0),('Car side knot',-6.82,-2.14,-12.55,-8.35,0,25,0),
        ('Pool side knot',-.81,3.13,-13.12,-9.36,0,22,0),('People arriving',-5.87,-2.03,-16.79,-14.12,0,12,0),
        ('Somebody knows the words',.25,3.11,-16.72,-14.71,0,9,0),('Between towels and trampoline',5.6,9.55,-13.96,-11.32,0,11,0),
        ('Far coping',12.1,13.25,-8.32,-4.30,0,6,0),('Garage roof',6.45,10.65,10.43,11.66,5.5,5,180)]:
        # The three knots nearest the stage are the full figures (cheers, phones, the surfer).
        posed=name in ('Front rail','Crush by the amp','The hook')
        crowd=s.crowd(name,marks,((x0+x1)/2,y,(z0+z1)/2),x1-x0,z1-z0,n,.84,yaw,'Posed' if posed else 'Mob')
    place_guests(s,cast)
    s.screen('Bedsheet feed',marks,(-9,2.15,5.438),2.44,1.37,'Stage',1.22)
    s.screen('Scavenged patio TV',marks,(10.4,1.925,4.537),.98,.55,'Program',1.15)
    cams=s.group('Camera positions',marks)
    for tag,kind,eye,aim,lens in [
        ('back-gate','Wide',(3.85,3.50,-17.66),(-1.00,1.66,2.7),58),('roofline','Crane',(-7.68,5.88,-15.88),(1.92,1.43,-1.0),56),
        ('drum-stool','Custom',(-.48,2.40,6.91),(-.42,1.53,-5.9),67),('pool-lip','Custom',(11.39,1.23,-7.9),(-.85,2.15,3.7),60),
        ('sofa','Custom',(-1.44,1.48,-16.53),(-1.72,1.23,-19.49),53),('through-hands','Custom',(-1.41,1.82,-7.21),(-.42,2.18,5),53),
        ('roof-party','Crane',(9.01,6.98,9.16),(-1.03,1.45,-6.75),59),('sticks','Close',(1.55,2.53,3.27),(-.09,1.95,5.32),49),
        ('crate-radio','Custom',(9.47,1.67,-1.30),(6.74,1.30,2.13),46),('taped-zoom','Desk',(3.64,2.32,-14.33),(-.16,1.96,4.46),33)]:
        s.camera_spot(tag,cams,eye,aim,kind,lens,tag)
    for i,(eye,aim,lens) in enumerate([
        ((.66,1.50,-22.96),(-1.18,1.35,-19.41),62),((.68,1.55,-21.93),(-1.72,1.26,-19.53),61),
        ((1.16,1.58,-20.59),(-1.03,1.46,-18.46),60),((2.01,1.68,-19.36),(-.48,2.16,-9.30),58),
        ((3.04,1.78,-18.65),(-.58,2.46,4.26),56),((3.78,1.88,-17.96),(-.45,2.46,4.79),54)]):
        s.camera_spot(f'Arrival {i+1:02}',cams,eye,aim,'Custom',lens,f'arrival/{i+1:02}')
    stage_drop(s,root,marks)
    guest_cameras(s,marks)
    return s


# The live show as the guests filmed it (VenueInfo Footage, Docs/Venue-Authoring.md): where someone
# at the party stands with a camcorder (@dv) or a flip phone (@phone). Eye height for whoever's
# holding it, aimed at what they'd film. Added last so the scene's other GUIDs stay put.
GUESTS=[
    ('front-rail@dv',(.5,1.78,-1.15),(-.3,1.6,.9),46),('over-heads@phone',(1.4,2.05,-7.4),(0,1.9,3.0),46),
    ('amp-crush@dv',(-6.8,1.62,-4.0),(-3.7,1.45,2.4),42),('bass-side@phone',(5.0,1.55,-2.4),(3.7,1.4,2.6),48),
    ('pool-steps@dv',(11.0,1.45,-6.6),(0,1.8,3.5),38),('back-gate@dv',(3.4,1.7,-17.2),(-.5,1.8,3.0),34),
    ('sofa@phone',(-1.9,1.05,-19.6),(-.4,1.9,2.0),46),('roof@phone',(8.8,6.95,9.6),(-.5,1.6,1.5),48),
    ('behind-kit@dv',(1.2,1.7,7.0),(-.5,1.5,-6.0),50),('keys-corner@dv',(-7.2,1.6,1.0),(-3.5,1.5,3.6),46)]


def guest_cameras(s,marks):
    guests=s.group('Guest cameras',marks)
    for tag,eye,aim,lens in GUESTS:
        s.camera_spot(f'guest {tag}',guests,eye,aim,'Custom',lens,f'guest/{tag}')


if __name__=='__main__':
    scene=build();folder=MODELS.parent;scene.write(str(folder/'Backyard.lvl'))
    write_venue_json(str(folder),'Backyard Party','Backyard.lvl',preview='Preview.jpg',version=2,ambience='Assets/Sounds/crowd.mp3')
    print(f'{len(scene.entities)} entities in {folder.name}')
