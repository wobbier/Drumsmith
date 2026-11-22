"""Food Court venue: the named people (the skate-shop kid, the mall guard, a second skater, the
food-court staff in their name tags) as rigid crowd pieces with looping performances.

The pieces are the game's crowd pieces (Assets/Models/People/Crowd/<body>/). The kid and the guard
wear the clothes the manifest gives them (PolygonTown_04_A / _04_B), so their pieces are copied into
the venue's Models/People/<who>/ with a local MTL that binds that atlas. Figures face local +Z, so a
yaw of 180 turns one toward the crowd.
"""
import json
import math
import os
import shutil

from story_food_court_art import LOCAL, MODELS, _save

PIECES = ('Legs', 'Torso', 'Head', 'ArmL', 'ArmR')
JOINTS = ('Spine', 'Head', 'Left', 'Right')
CROWD = os.path.join(os.path.dirname(MODELS), '..', '..', 'Models', 'People', 'Crowd')

# Clip: seconds, keys of (time share, spine, head, left arm, right arm) Euler degrees.
POSES = {
    'Idle': (4.0, [(0, (0, -3, 0), (2, 6, 0), (0, 0, -6), (0, 0, 6)),
                   (.5, (1, 3, 0), (-2, -8, 0), (-6, 0, -8), (4, 0, 7))]),
    'Bounce': (1.0, [(0, (4, 0, 0), (6, 0, 0), (-10, 0, -14), (-10, 0, 14)),
                     (.5, (-2, 0, 0), (-6, 0, 0), (-24, 0, -20), (-24, 0, 20))]),
    'Clap': (.75, [(0, (3, 0, 0), (4, 0, 0), (-62, -34, -6), (-62, 34, 6)),
                   (.5, (3, 0, 0), (8, 0, 0), (-70, -8, -2), (-70, 8, 2))]),
    'ArmsUp': (.9, [(0, (-6, 0, 0), (-14, 0, 0), (-168, 0, -14), (-168, 0, 14)),
                    (.5, (-2, 0, 0), (-8, 0, 0), (-150, 0, -26), (-150, 0, 26))]),
    'Guard': (5.0, [(0, (0, 0, 0), (4, 10, 0), (-14, 0, -22), (-14, 0, 22)),
                    (.5, (0, 0, 0), (2, -12, 0), (-16, 0, -20), (-16, 0, 20))]),
    'Point': (1.4, [(0, (-2, 0, 0), (-6, 0, 0), (-120, 0, -10), (-8, 0, 10)),
                    (.5, (0, 0, 0), (-3, 0, 0), (-104, 0, -14), (-14, 0, 12))]),
}


def quat(rot):
    x, y, z = [math.radians(a) / 2 for a in rot]
    a, b = math.sin(x), math.cos(x); c, d = math.sin(y), math.cos(y); e, f = math.sin(z), math.cos(z)
    return [round(v, 7) for v in (a*d*f - b*c*e, b*c*f + a*d*e, b*d*e - a*c*f, b*d*f + a*c*e)]


def clips():
    folder = os.path.join(os.path.dirname(MODELS), 'Motion')
    os.makedirs(folder, exist_ok=True)
    for name, (seconds, keys) in POSES.items():
        end = round(seconds * 30)
        tracks = []
        for i, joint in enumerate(JOINTS, 1):
            ks = [{'Frame': round(k[0] * end), 'Value': quat(k[i]), 'Interpolation': 'SmoothStep'} for k in keys]
            ks.append(dict(ks[0], Frame=end))
            tracks.append({'Binding': joint, 'Component': 'Transform', 'Property': 'Rotation', 'Keys': ks})
        clip = {'Version': 1, 'Name': name, 'FrameRate': 30, 'DurationFrames': end, 'Tracks': tracks}
        _save(os.path.join(folder, name + '.sequence'), json.dumps(clip, indent=1) + '\n')


def dress(who, body, atlas):
    """Copy a body's crowd pieces into Models/People/<who>/ wearing the given atlas."""
    folder = os.path.join(MODELS, 'People', who)
    os.makedirs(folder, exist_ok=True)
    for piece in PIECES:
        src = os.path.join(CROWD, body, piece + '.obj')
        text = open(src).read()
        _save(os.path.join(folder, piece + '.obj'), text)
    _save(os.path.join(folder, 'Crowd.mtl'), f'newmtl Crowd\nKd 1 1 1\nKs 0 0 0\nmap_Kd ../../../../../Models/Venue/{atlas}.png\n')
    return LOCAL + f'People/{who}/'


def person(s, parent, label, base, pose, pos, yaw=180.0, speed=1.0, scale=1.0):
    """base: a folder of pieces (venue-local dressed, or a stock crowd body name)."""
    if not base.startswith('Assets/'):
        base = f'Assets/Models/People/Crowd/{base}/'
    root = s.entity(label, parent, pos, (0, yaw, 0), (scale,) * 3)
    k = POSES[pose][1][0]

    def piece(part, where, anchor, rot=(0, 0, 0)):
        n = s.entity(part, anchor, where, rot)
        n.add({'Type': 'Model', 'ModelPath': base + part + '.obj'})
        return n
    piece('Legs', (0, 0, 0), root)
    spine = piece('Torso', (0, .8763, 0), root, k[1])
    head = piece('Head', (0, .5727, -.0242), spine, k[2])
    arm_l = piece('ArmL', (-.191, .5141, -.0484), spine, k[3])
    arm_r = piece('ArmR', (.191, .5141, -.0484), spine, k[4])
    root.add({'Type': 'Sequence', 'Clip': f'Assets/Venues/StoryFoodCourt/Motion/{pose}.sequence', 'PlayOnStart': True,
              'Loop': True, 'Speed': speed, 'Bindings': [{'Slot': j, 'Target': p.guid} for j, p in zip(JOINTS, (spine, head, arm_l, arm_r))]})
    return root, head, spine


def cap(s, head, colour=(.08, .1, .22)):
    """The guard's peaked cap (signature): a crown and a brim on the head piece."""
    s.box('Peaked cap crown', head, (0, .2, .0), (.25, .09, .27), colour, rough=.6)
    s.box('Cap badge', head, (0, .215, .136), (.05, .05, .01), (.95, .78, .2), metallic=.8, rough=.3)
    s.box('Cap brim', head, (0, .16, .13), (.23, .02, .12), (.03, .03, .04), rough=.4)


def name_tag(s, spine, colour=(.96, .96, .92)):
    s.box('Name tag', spine, (.09, .33, .135), (.08, .045, .01), colour, rough=.5, shadows=False)


def visor(s, head, colour):
    s.box('Paper visor', head, (0, .17, .03), (.25, .05, .26), colour, rough=.8)
