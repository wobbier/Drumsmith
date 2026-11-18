"""The party extras: a beach ball left floating in the pool, a friend on the trampoline, the paper
crates and two hand lamps. Stage coordinates are metres and the performance is keyed in song beats."""
import json
import math

from backyard_guests import quat
from backyard_meshes import MODELS, geo, mesh_file, save


LOCAL = 'Assets/Venues/Backyard/Models/'
BEATS = 16
FRAMES_PER_BEAT = 16


def beach_ball():
    m = geo.Mesh('RallyBall', 'Six broad sewn vinyl panels, white polar patches and a black valve.')
    colours = ['pink', 'white', 'aqua', 'orange', 'white', 'blue']
    def vertex(latitude, longitude):
        p, a = math.radians(latitude), math.radians(longitude)
        return (.55*math.sin(p)*math.cos(a), .55*math.cos(p), .55*math.sin(p)*math.sin(a))
    rings = [0, 15, 32, 52, 73, 95, 117, 140, 164, 180]
    for j in range(24):
        a = j*15
        for lo, hi in zip(rings, rings[1:]):
            points = [vertex(lo,a),vertex(lo,a+15),vertex(hi,a+15),vertex(hi,a)]
            if lo == 0: points.pop(0)
            if hi == 180: points.pop()
            m.face(points, 'white' if lo == 0 or hi == 180 else colours[j//4])
    m.tube((0,.541,0),(0,.559,0),.039,.026,'navy',8)
    mesh_file(m,False)


def paper_crate():
    m = geo.Mesh('PaperCrate','An old milk crate with open slats, paper rolls and gaffer-taped handles.')
    for y in (.07,.22,.38):
        for z in (-.208,.208): m.box((0,y,z),(.62,.065,.042),'teal')
        for x in (-.294,.294): m.box((x,y,0),(.044,.065,.43),'teal')
    for x in (-.273,.273):
        for z in (-.18,.18): m.box((x,.215,z),(.065,.43,.061),'navy')
    for x,z,col in [(-.14,.045,'pink'),(.03,-.05,'white'),(.17,.065,'yellow')]:
        end=(x*.69,.53,-.09+z)
        m.tube((x,.06,z),end,.081,.080,col,10)
        m.tube(end,(end[0],.535,end[2]),.053,.053,'navy',10)
    for x in (-.20,.10): m.box((x,.38,-.232),(.085,.07,.012),'tape')
    mesh_file(m,False)


def stage_drop(s,root,marks):
    beach_ball()
    paper_crate()
    show = s.group('Party extras',root)
    # Just a ball someone left in the pool: set dressing, nobody plays with it.
    ball = s.entity('Pool ball',show,(6.9,.22,-5.3),(0,25,8))
    ball.add({'Type':'Model','ModelPath':LOCAL+'RallyBall.obj'})
    bindings,tracks = {},[]

    def track(slot,component,field,keys,interp='SmoothStep'):
        tracks.append({'Binding':slot,'Component':component,'Property':field,'Keys':[
            {'Frame':round(beat*FRAMES_PER_BEAT),'Value':[round(x,6) for x in value],'Interpolation':interp}
            for beat,value in keys]})

    times = [i/8 for i in range(BEATS*8+1)]

    def piece(name,parent,offset,person,rotation=(0,0,0)):
        n=s.entity(name,parent,offset,rotation)
        n.add({'Type':'Model','ModelPath':f'Assets/Models/People/Crowd/{person}/{name}.obj'})
        return n

    # A friend on the trampoline squats into each landing, then opens up at the apex.
    s.light('Light from the torch by the trampoline',show,(12.3,1.82,-19.0),
            color=(1,.57,.31),intensity=51,range_=6.6)
    spring=s.entity('Encore on the trampoline',show,(9,.77,-17.5),(0,-28,0))
    jumper=s.entity('Jump',spring)
    bindings['Jumper']=jumper.guid
    person='Rigged'
    piece('Legs',jumper,(0,0,0),person)
    hips=piece('Torso',jumper,(0,.8763,0),person)
    piece('Head',hips,(0,.5727,-.0242),person)
    bindings['JumperHip']=hips.guid
    for side,name in [(-1,'ArmL'),(1,'ArmR')]:
        arm=piece(name,hips,(side*.191,.5141,-.0484),person,(-18,0,side*13))
        bindings['Jump'+name]=arm.guid
    jumps=[(1.5,3,.58),(3.5,5.25,.94),(5.75,7.75,1.34),(9,10.75,.86),(11.25,13.25,1.27)]
    heights=[]; hips_y=[]; arms=[[],[]]
    for t in times:
        height=load=reach=0.
        for start,end,apex in jumps:
            u=(t-start)/(end-start)
            if 0<u<1:
                reach=4*u*(1-u)
                height=reach*apex
            load=max(load, max(0,1-abs(t-start+.22)/.24),max(0,1-abs(t-end-.16)/.19))
        heights.append((t,(0,height,0,0)))
        hips_y.append((t,(0,.8763-.17*load,0,0)))
        for j,side in enumerate((-1,1)):
            arms[j].append((t,quat((-18-111*reach+14*load,side*12*reach,side*(13+38*reach)))))
    track('Jumper','Transform','Position',heights,'Linear')
    track('JumperHip','Transform','Position',hips_y,'Linear')
    for name,keys in zip(('ArmL','ArmR'),arms): track('Jump'+name,'Transform','Rotation',keys,'Linear')

    for i,(x,col,second) in enumerate([(-5.8,(1,.09,.30),(1,.74,.32)),(4.45,(.12,.86,1),(.96,.94,.67))]):
        s.prop('Crate of coloured paper',show,LOCAL+'PaperCrate.obj',(x,.36,-.08),-8 if i else 12)
        e=s.entity('Paper toss '+str(i+1),show,(x,.89,-.17),(-33,0,12 if i else -13))
        e.add({'Type':'VenueAccent','Particles':164})
        e.add({'Type':'ParticleSystem','Simulation':'CPU','SimulationSpace':'World','Shape':'Cone','ConeAngle':23,
               'ShapeRadius':.10,'Lifetime':[2.4,3.7],'Speed':[5.1,8.0],'Size':[.075,.16],
               'StartColor':list(col),'StartColor2':list(second),'EndColor':list(second),'AngularVelocity':[-245,245],
               'Gravity':.30,'Drag':.64,'NoiseStrength':1.15,'NoiseFrequency':.8,'StartAlpha':1,'EndAlpha':0,
               'FadeIn':.015,'EndSize':.78,'Intensity':1.4,'Texture':'Assets/Textures/Venue/Confetti.png','Blend':'Alpha',
               'EmissionRate':0,'BurstCount':0,'MaxParticles':256,'SoftParticleDistance':0})
        lamp=s.light('Poolside hand lamp' if i else 'Speaker-side hand lamp',show,(x,3.65,-4.05),
                     color=col,intensity=2,range_=8.6)
    show.add({'Type':'VenueAccent','Beats':BEATS,'FullLightingOnly':False})
    show.add({'Type':'Sequence','Clip':'Assets/Venues/Backyard/Motion/Trampoline.sequence','PlayOnStart':False,
              'Loop':False,'Bindings':[{'Slot':name,'Target':bindings[name]} for name in dict.fromkeys(t['Binding'] for t in tracks)]})
    clip={'Version':1,'Name':'Trampoline','FrameRate':32,'DurationFrames':BEATS*FRAMES_PER_BEAT,'Tracks':tracks}
    save(MODELS.parent/'Motion'/'Trampoline.sequence',json.dumps(clip,indent=1)+'\n')
