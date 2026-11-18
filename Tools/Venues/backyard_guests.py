"""Joint performances for the friends who didn't come here to stand in the front row."""
import json
import math
from functools import lru_cache

from backyard_meshes import MODELS, bent_part, save


POSES = {
    'TellTheStory': (5.8, (66,38), [
        (0,  (2,-8,-3), (-3,12,3), (-21,-15,-11), (-8,4,9)),
        (.24,(7,11,4), (-9,-15,-7), (-48,-20,-27), (-16,2,18)),
        (.37,(9,15,2), (4,-12,-4), (-38,-4,-13), (-24,8,32)),
        (.56,(1,-9,-6), (-6,25,8), (-15,-8,-5), (-59,4,38)),
        (.67,(2,-6,-4), (1,19,7), (-20,1,-10), (-43,3,30)),
        (.84,(-4,-16,-3), (-12,8,4), (-14,-3,-14), (-9,4,10))]),
    'ListenAndSip': (7.1, (0,93), [
        (0,(-2,6,5),(1,-12,-4),(-5,4,-8),(-11,5,9)),
        (.20,(-2,10,4),(8,-14,-3),(-4,2,-7),(-12,3,7)),
        (.29,(-3,6,5),(-4,-12,-6),(-6,3,-6),(-13,4,9)),
        (.50,(1,-2,3),(0,3,-5),(-9,2,-8),(-54,-14,4)),
        (.59,(-3,-3,4),(-12,2,-5),(-9,2,-6),(-66,-17,3)),
        (.70,(-3,-2,3),(-10,2,-4),(-9,2,-6),(-63,-17,4)),
        (.85,(-1,3,4),(7,-14,-3),(-6,2,-8),(-15,2,8))]),
    'SofaLaugh': (5.3, (62,0), [
        (0,(-13,-9,6),(4,13,-6),(-21,4,-16),(-16,4,18)),
        (.23,(-8,4,3),(6,24,-4),(-33,1,-10),(-22,8,20)),
        (.42,(-21,8,9),(-19,22,12),(-53,5,-28),(-10,9,32)),
        (.50,(-16,8,6),(-8,25,6),(-46,4,-23),(-14,8,28)),
        (.59,(-20,7,7),(-14,22,8),(-49,4,-25),(-12,8,30)),
        (.80,(-10,-2,4),(9,16,-6),(-17,4,-11),(-20,4,17))]),
    'FrameTheShot': (6.7, (73,76), [
        (0,(2,-9,-3),(3,-12,5),(-24,-7,-12),(-56,-13,11)),
        (.27,(4,-2,1),(-10,2,-4),(-55,14,-6),(-84,-10,12)),
        (.42,(3,5,0),(-14,10,-6),(-62,12,-4),(-91,-6,9)),
        (.61,(3,5,-1),(-13,9,-4),(-60,11,-4),(-90,-6,8)),
        (.79,(1,11,3),(8,12,1),(-36,5,-10),(-60,-4,6))]),
    'CueTheRecord': (4.4, (67,61), [
        (0,(13,6,-3),(18,-12,-4),(-25,13,-14),(-18,-9,18)),
        (.21,(20,-8,6),(26,-15,4),(-33,-6,-28),(-13,-9,7)),
        (.39,(15,-10,4),(12,-19,6),(-28,-4,-24),(-12,-9,9)),
        (.64,(11,14,-8),(-5,21,-6),(-12,9,-9),(-52,-7,19)),
        (.79,(13,9,-5),(15,17,-4),(-21,12,-12),(-36,-7,23))]),
    'KitchenTwoStep': (2.9, (40,74), [
        (0,(3,-13,-7),(3,18,7),(-28,-9,-15),(-16,5,22)),
        (.24,(9,-3,-2),(12,4,2),(-38,4,-26),(-22,3,15)),
        (.50,(-4,17,8),(-9,-19,-10),(-17,6,-9),(-56,-8,31)),
        (.76,(6,4,2),(5,-9,-3),(-24,3,-13),(-35,-5,18))]),
    'FeetInPool': (8.2, (0,0), [
        (0,(-10,5,-3),(-4,-24,5),(-5,5,-14),(-8,0,22)),
        (.28,(-12,14,-2),(-8,-34,7),(-8,9,-21),(-6,3,19)),
        (.53,(4,-4,4),(18,-9,-3),(-26,1,-7),(-19,0,8)),
        (.72,(2,-8,3),(9,19,-3),(-19,5,-11),(-21,4,9)),
        (.86,(-9,-9,-2),(-7,25,3),(-6,5,-14),(-9,3,21))]),
}

JOINTS=('Spine','Head','Left','Right')
local_part = lru_cache(maxsize=None)(bent_part)


def quat(rot):
    x,y,z = [math.radians(a)/2 for a in rot]
    a,b=math.sin(x),math.cos(x);c,d=math.sin(y),math.cos(y);e,f=math.sin(z),math.cos(z)
    return [round(v,7) for v in (a*d*f-b*c*e,b*c*f+a*d*e,b*d*e-a*c*f,b*d*f+a*c*e)]


def clips():
    folder=MODELS.parent/'Motion';folder.mkdir(exist_ok=True)
    for name,(seconds,_,poses) in POSES.items():
        end=round(seconds*30); tracks=[]
        for i,joint in enumerate(JOINTS,1):
            keys=[{'Frame':round(t[0]*end),'Value':quat(t[i]),'Interpolation':'SmoothStep'} for t in poses]
            keys.append(dict(keys[0],Frame=end))
            tracks.append({'Binding':joint,'Component':'Transform','Property':'Rotation','Keys':keys})
        clip={'Version':1,'Name':name,'FrameRate':30,'DurationFrames':end,'Tracks':tracks}
        save(folder/(name+'.sequence'),json.dumps(clip,indent=1)+'\n')
    floats=[(0,(0,0,0),(0,0,0)),(36,(.020,.012,.009),(1.4,1.1,-.7)),(74,(-.009,-.010,.014),(-.8,.6,1.6)),
            (115,(-.018,.009,-.008),(.6,-1.4,-.3)),(152,(.006,-.006,-.012),(-1.0,-.6,-1.4)),(185,(0,0,0),(0,0,0))]
    tracks=[{'Binding':'Float','Component':'Transform','Property':field,'Keys':[
        {'Frame':frame,'Value':([*pos,0] if field=='Position' else quat(rot)),'Interpolation':'SmoothStep'} for frame,pos,rot in floats]} for field in ('Position','Rotation')]
    save(folder/'PoolDrift.sequence',json.dumps({'Version':1,'Name':'PoolDrift','FrameRate':30,'DurationFrames':185,'Tracks':tracks},indent=1)+'\n')


def guest(s,parent,label,person,role,pos,yaw,scale=1,speed=1,held=None):
    _,bends,poses=POSES[role]; r=poses[0];seated=role in ('SofaLaugh','FeetInPool')
    root=s.entity(label,parent,pos,(0,yaw,0),(scale,)*3)
    def piece(part,where,anchor,rot=(0,0,0),path=None):
        n=s.entity(part,anchor,where,rot)
        n.add({'Type':'Model','ModelPath':path or f'Assets/Models/People/Crowd/{person}/{part}.obj'})
        return n
    piece('Legs',(0,0,0),root,path=local_part(person,'Legs',79) if seated else None)
    spine=piece('Torso',(0,.57 if seated else .8763,0),root,r[1]);head=piece('Head',(0,.5727,-.0242),spine,r[2])
    limbs = [spine,head]
    for i,(part,side) in enumerate((('ArmL',-1),('ArmR',1))):
        bend=bends[i];arm=piece(part,(side*.191,.5141,-.0484),spine,r[3+i],local_part(person,part,bend) if bend else None);limbs.append(arm)
        if held and i==1:
            a=math.radians(bend); palm=(0,-.323-.35*math.cos(a),.35*math.sin(a))
            hand=s.entity('Gripped '+held,arm,palm,(34 if held=='cup' else 72,0,0))
            if held=='cup': s.prop('Paper cup',hand,'Assets/Venues/Backyard/Models/PaperCup.obj',(0,-.045,.016))
            else:
                s.box('Phone case',hand,(0,.03,0),(.084,.155,.016),(.03,.025,.034),rough=.65)
                s.box('Lit glass',hand,(0,.032,-.010),(.072,.135,.003),(.17,.47,.65),emissive=(.19,.69,.93),emissive_intensity=1.7,shadows=False)
    root.add({'Type':'Sequence','Clip':f'Assets/Venues/Backyard/Motion/{role}.sequence',
              'PlayOnStart':True,'Loop':True,'Speed':speed,'Bindings':[{'Slot':j,'Target':p.guid} for j,p in zip(JOINTS,limbs)]})


def place_guests(s,parent):
    cast=[
        ('Mara, halfway through the story','Mother_01','TellTheStory',(-.70,0,-18.43),-118,1.02,.93,None),
        ('Inez on the sofa','Daughter_01','SofaLaugh',(-2.22,.108,-19.94),20,1.00,1.07,None),
        ('Sol on the arm of the conversation','Son_01','ListenAndSip',(-2.81,0,-18.46),125,1.035,.91,'cup'),
        ('The cooler confession','ShopKeeper_01','TellTheStory',(-10.12,0,-4.42),75,1.05,1.14,None),
        ('One more sip','Mother_02','ListenAndSip',(-8.86,0,-4.18),-112,.98,1.11,'cup'),
        ('Feet on the first step','Mother_02','FeetInPool',(7.59,-.415,-9.55),22,1.01,.89,None),
        ('Zero interest in getting up','Son_01','FeetInPool',(8.65,-.426,-9.53),-27,1.04,1.12,None),
        ('Recording from the pool lip','Daughter_01','FrameTheShot',(10.91,.045,-8.86),-42,.99,1.03,'phone'),
        ('The crate DJ','Son_01','CueTheRecord',(7.17,.03,2.46),182,1.02,1.00,None),
        ('Offbeat / left foot','Mother_01','KitchenTwoStep',(6.22,0,.30),90,.98,.94,None),
        ('Offbeat / right foot','Rigged','KitchenTwoStep',(7.56,0,.16),-82,1.06,1.18,None),
        ('Phone over the parapet','ShopKeeper_01','FrameTheShot',(7.62,5.50,8.90),-159,1.03,.84,'phone'),
        ('Calling across the roof','Mother_02','TellTheStory',(9.47,5.5,9.14),-100,1.00,1.06,None),
    ]
    for args in cast: guest(s,parent,*args)
