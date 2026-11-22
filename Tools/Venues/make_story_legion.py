#!/usr/bin/env python3
"""Builds Assets/Venues/StoryLegion/: story set 05, "Funeral Afterparty at the Legion" (s05-legion).

    python3 Tools/Venues/make_story_legion.py

A Legion branch's small hall after a funeral: dark wood panelling, a drop ceiling with the
fluorescents dimmed, a strip of block parquet in front of a low stage, round tables in white
cloths and folding chairs, the bar along the west wall, the branch crest and two flags behind the
band, an upright piano in the east corner, a memorial table with Dad's portrait on an easel, a
dessert cart parked on the dance floor, and a few coloured party lights somebody's nephew brought.

The five story flags (Design/Story-Mode-Setlists.json, s05-legion):
  toast_seat_empty     the uncle stops standing for the toast; the light widens to the daughter and
                       the empty chair beside her (the folded toast left on its seat); he sits.
  dessert_table_moved  the dessert cart leaves the parquet for the east wall (a lemon square crooked).
  shoes_by_chair       the daughter and her uncle slow-dance on the floor; her shoes under the chair.
  portrait_on_piano    the portrait leaves the easel for the piano, his tie on its corner, napkins.
  family_on_floor      the cousins fill the parquet, his shoes join hers, a cousin on a chair takes
                       the photo (the flash is lit).

Writes the textures, the models (Models/, Models/People/), the motion clips, the scene and
venue.json. Deterministic: a rerun writes the same bytes.
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import math  # noqa: E402

import story_legion_props as P  # noqa: E402
from story_legion_mesh import LOCAL, MODELS, VENUE, Mesh, rot_y, write_mtl  # noqa: E402
from story_legion_people import (SITTING, STANDING, Pose, both, camera_in, clips, figure, glass_in,  # noqa: E402
                                 paper_in, place)
from story_legion_textures import all_textures  # noqa: E402
from venuegen import Scene, look_rotation, vec, write_venue_json  # noqa: E402

ID = 'StoryLegion'
TEX = 'Assets/Venues/StoryLegion/Textures/'
VM = 'Assets/Models/Venue/'

# The room.
X0, X1 = -9.0, 9.0          # west and east walls (inner faces)
Z0, Z1 = -15.0, 8.5         # the doors' wall (behind the crowd) and the wall behind the band
CEIL = 3.6
STAGE_H, STAGE_Z = .4, 2.7  # the low stage: x -5..5, z 2.7..8.5
RISER_H = .25
DRUMMER = (0.0, STAGE_H + RISER_H, 6.75)
PARQUET = (-3.2, 3.2, -5.6, 2.7)

# Lineup of tables: (x, z, seed); T1 is the family's.
T1 = (-6.3, -.5)
TABLES = [(T1[0], T1[1], 1), (-6.7, -4.7, 2), (-5.7, -9.0, 3), (6.6, -4.3, 4), (6.7, -8.6, 5)]
DAUGHTER_CHAIR = (-5.25, .28, 62)       # x, z, the way she faces (yaw)
EMPTY_CHAIR = (-4.95, -.42, 62)
UNCLE_SEAT = (-7.25, -1.2, 54)          # where he sits once the toast is done, at the same table
PIANO = (7.65, 2.55, 45)
CART_ON_FLOOR = (.9, -2.0, 12)
CART_AT_WALL = (8.4, -.45, 90)
EASEL = (-7.25, 3.15, -30)
MEMORIAL = (-7.15, 2.2, -35)

AMBER = (1.0, .55, .18)
WARM = (1.0, .78, .52)
MAGENTA = (1.0, .18, .55)
TEAL = (.15, .85, .9)
BLUE = (.3, .38, 1.0)
FLUO = (.82, .9, 1.0)


def chair_hip(x, z, yaw):
    """A sitter's root for a chair at x, z facing yaw: a little behind the seat's centre."""
    dx, _, dz = rot_y((0, 0, -.17), yaw)
    return (x + dx, 0, z + dz)


# ---- textured primitives -------------------------------------------------------------------------
def tex_slab(s, name, parent, x0, x1, y0, y1, z0, z1, texture, tiling, color=(1, 1, 1), shadows=False, rough=.85):
    e = s.entity(name, parent, ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (0, 0, 0),
                 ((x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2))
    mat = {'Type': 'StandardMaterial', 'DiffuseColor': vec(color), 'Metallic': 0.0, 'Roughness': rough,
           'Tiling': vec(tiling), 'Textures': {'Diffuse': {'Path': TEX + texture + '.png'}}}
    e.add({'Type': 'Mesh', 'MeshType': 'Cube', 'CastShadows': shadows, 'Material': mat})
    return e


# ---- meshes --------------------------------------------------------------------------------------
def build_meshes():
    textures = all_textures()
    write_mtl(textures)
    out = {}

    def mesh(name, note, fn):
        m = Mesh(name, note)
        fn(m)
        out[name] = m.write()

    mesh('FoldingChair', 'Beige steel folding chair; the sitter faces +z.', P.folding_chair)
    mesh('ToastChair', 'The empty chair with the folded toast on its seat.', lambda m: P.folding_chair(m, True))
    mesh('UprightPiano', 'Black upright with bench, keyboard facing -z.', P.upright_piano)
    mesh('DessertCart', 'Banquet cart of squares, cakes and coffee, front -z.', lambda m: P.dessert_cart(m, 7))
    mesh('DessertCartPushed', 'The same cart against the wall: one lemon square crooked on its own plate.',
         lambda m: P.dessert_cart(m, 7, True))
    mesh('Easel', 'Wooden display easel, front -z.', P.easel)
    mesh('Portrait', "Dad's portrait in a gilt frame with a black ribbon, front -z.", P.portrait)
    mesh('MemorialTable', 'Flowers, candles, the guest book and the In Loving Memory card, front -z.', P.memorial_table)
    mesh('FlagCanada', 'Canadian flag in a floor stand.', lambda m: P.flag_pole(m, 'FlagCanada'))
    mesh('FlagBranch', "The branch's standard in a floor stand, flying west.", lambda m: P.flag_pole(m, 'FlagBranch', -1))
    mesh('TBarStand', 'Party-light T-bar on a tripod, four cans.', P.tbar_stand)
    mesh('StackedChairs', 'Folded chairs on a dolly.', lambda m: P.stacked_chairs(m, 12))
    mesh('Bar', 'The bar along the west wall, customer side +x.', P.bar)
    mesh('Dartboard', 'Dartboard in its cabinet, face -z.', P.dartboard)
    mesh('CoatRack', 'Coat rack with the mourners’ coats.', P.coat_rack)
    mesh('Heels', 'Her good shoes.', lambda m: P.shoes(m, 'heels'))
    mesh('Oxfords', 'His shoes.', lambda m: P.shoes(m, 'oxfords'))
    mesh('Tie', "The uncle's tie, draped.", P.tie_draped)
    mesh('Napkins', 'A little stack of napkin requests.', lambda m: P.napkin_stack(m, 3))

    def table_set(m, seed):
        P.round_table(m, seed)
    for x, z, seed in TABLES:
        mesh(f'Table{seed}', 'Round table in a white cloth with its settings.', lambda m, sd=seed: table_set(m, sd))

    def wall_art(m):
        W, E = -90, 90   # yaws that face the west wall's art east (+x) and the east wall's west (-x)
        m.picture((X0 + .03, 1.75, -6.4), .9, 1.2, 'HonourRoll', yaw=W)
        m.frame((X0 + .04, 1.75, -6.4), .9, 1.2, .04, .03, 'gold', yaw=W)
        m.picture((X0 + .03, 1.75, -2.2), 1.0, .75, 'OldPhotos', yaw=W)
        m.picture((X0 + .03, 2.75, -12.3), 1.6, .4, 'LestWeForget', yaw=W)
        m.picture((X1 - .03, 1.7, -2.6), 1.2, .75, 'LetterBoard', yaw=E)
        m.frame((X1 - .04, 1.7, -2.6), 1.2, .75, .05, .03, 'wood_light', yaw=E)
        m.picture((X1 - .03, 1.55, -11.0), .75, .5, 'MeatDraw', yaw=E)
        m.picture((X1 - .03, 2.0, -6.4), 1.0, .75, 'OldPhotos', yaw=E, uv=((.5, 0), (1, 0), (1, 1), (.5, 1)))
        for z in (-13.2, -9.6):
            m.picture((X1 - .03, 2.0, z), 1.3, 1.0, 'WindowBlind', yaw=E)
            m.frame((X1 - .04, 2.0, z), 1.3, 1.0, .06, .04, 'cloth_shade', yaw=E)
        # The crest behind the drummer.
        m.picture((0, 2.72, Z1 - .04), 1.05, 1.05, 'Crest')
        # A hand-painted bedsheet banner above the doors.
        m.picture((0, 2.65, Z0 + .04), 3.2, .6, 'Banner', yaw=180)
        # Exit signs (a lit box sits behind each).
        m.picture((-3.2, 2.55, Z0 + .075), .45, .17, 'Exit', yaw=180)
        m.picture((X1 - .075, 2.65, 5.2), .45, .17, 'Exit', yaw=E)
    mesh('WallArt', 'Signs, the honour roll, photos, the crest, the banner.', wall_art)

    def doors(m):
        # Double doors in the south wall, a fire door in the east wall by the stage.
        m.slab(-1.2, 1.2, 0, 2.2, Z0, Z0 + .06, 'wood_mid')
        m.slab(-.02, .02, 0, 2.2, Z0 + .06, Z0 + .07, 'black')
        for x in (-.3, .3):
            m.slab(x - .15, x + .15, 1.4, 1.95, Z0 + .06, Z0 + .065, 'glass')
            m.slab(x * 2.2 - .01, x * 2.2 + .01, .9, 1.1, Z0 + .06, Z0 + .1, 'chrome')
        m.slab(-1.35, 1.35, 2.2, 2.32, Z0, Z0 + .08, 'wood_dark')
        m.slab(X1 - .06, X1, 0, 2.1, 4.6, 5.8, 'steel')
        m.slab(X1 - .1, X1 - .06, .95, 1.05, 4.75, 5.65, 'chrome')
    mesh('Doors', 'Doors.', doors)

    def stage_dress(m):
        # The stage's front skirt, the steps, the drum riser's carpet edge.
        m.slab(-5.0, 5.0, 0, STAGE_H, STAGE_Z - .02, STAGE_Z, 'carpet')
        for i, (h, z) in enumerate(((.13, STAGE_Z - .6), (.27, STAGE_Z - .3))):
            m.slab(-4.4, -3.4, 0, h, z, z + .3, 'wood_dark')
        # curtains at the stage's sides, and the valance with a gold fringe
        for x in (-5.25, 5.25):
            for k in range(5):
                zz = STAGE_Z + .1 + k * .14
                m.slab(x - .09, x + .09, STAGE_H, CEIL - .02, zz, zz + .13, 'curtain' if k % 2 else 'curtain_dark')
        for k in range(36):
            x = -5.4 + k * .3
            m.slab(x, x + .3, CEIL - .42, CEIL - .02, STAGE_Z - .02 + .04 * (k % 2), STAGE_Z + .06 + .04 * (k % 2),
                   'curtain' if k % 2 else 'curtain_dark')
        m.slab(-5.4, 5.4, CEIL - .45, CEIL - .42, STAGE_Z - .05, STAGE_Z + .1, 'gold')
    mesh('StageDress', 'The stage skirt, steps, side curtains and valance.', stage_dress)
    return out


# ---- the scene -----------------------------------------------------------------------------------
def build():
    models = build_meshes()
    motion = clips()
    s = Scene('story-legion-s05')
    root = s.group('Funeral Afterparty at the Legion')
    hall = s.group('The hall', root)
    dress = s.group('Tables, bar and dressing', root)
    stage = s.group('Stage', root)
    family = s.group('The family', root)
    story = s.group('Story: how the night turns over', root)
    lamps = s.group('Lights', root)
    marks = s.group('Venue markers', root)

    def model(name, parent, path, pos, yaw=0.0, scale=1.0):
        return s.prop(name, parent, path, pos, yaw, scale)

    # The shell: lino floor, parquet strip, panelled walls, the drop ceiling.
    tex_slab(s, 'Lino floor', hall, X0, X1, -.1, 0, Z0, Z1, 'Lino', ((X1 - X0) / .6, (Z1 - Z0) / .6), rough=.6)
    px0, px1, pz0, pz1 = PARQUET
    tex_slab(s, 'Parquet strip', hall, px0, px1, 0, .012, pz0, pz1, 'Parquet', ((px1 - px0) / 1.2, (pz1 - pz0) / 1.2), rough=.45)
    s.slab('Parquet edge', hall, px0 - .05, px1 + .05, 0, .008, pz0 - .05, pz1 + .05, (.08, .05, .03), shadows=False)
    tex_slab(s, 'Panelling behind the band', hall, X0, X1, 0, CEIL, Z1, Z1 + .1, 'Panelling', ((X1 - X0) / 1.2, CEIL / 1.2))
    tex_slab(s, 'Panelling, doors wall', hall, X0, X1, 0, CEIL, Z0 - .1, Z0, 'Panelling', ((X1 - X0) / 1.2, CEIL / 1.2))
    tex_slab(s, 'Panelling, west wall', hall, X0 - .1, X0, 0, CEIL, Z0, Z1, 'Panelling', ((Z1 - Z0) / 1.2, CEIL / 1.2))
    tex_slab(s, 'Panelling, east wall', hall, X1, X1 + .1, 0, CEIL, Z0, Z1, 'Panelling', ((Z1 - Z0) / 1.2, CEIL / 1.2))
    for name, x0, x1, z0, z1 in (('west', X0, X0 + .03, Z0, Z1), ('east', X1 - .03, X1, Z0, Z1),
                                 ('south', X0, X1, Z0, Z0 + .03), ('north', X0, X1, Z1 - .03, Z1)):
        s.slab(f'Chair rail, {name}', hall, x0, x1, .95, 1.0, z0, z1, (.12, .06, .03), shadows=False)
        s.slab(f'Baseboard, {name}', hall, x0, x1, 0, .12, z0, z1, (.06, .035, .02), shadows=False)
    tex_slab(s, 'Drop ceiling', hall, X0, X1, CEIL, CEIL + .05, Z0, Z1, 'Ceiling', ((X1 - X0) / 1.2, (Z1 - Z0) / .6),
             color=(.78, .76, .72))
    # Fluorescent troffers, dimmed for the party; a couple off altogether.
    k = 0
    for x in (-6.0, -2.0, 2.0, 6.0):
        for z in (-12.6, -8.4, -4.2, 0.0):
            k += 1
            off = (x, z) in ((-2.0, -4.2), (2.0, 0.0), (6.0, -8.4), (-6.0, 0.0))
            s.box(f'Troffer {k}', hall, (x, CEIL - .015, z), (.62, .03, 1.22), (.75, .78, .8) if off else (.9, .94, 1),
                  emissive=None if off else (.75, .85, 1.0), emissive_intensity=.55, shadows=False)
    # The stage and the drum riser.
    s.slab('Stage deck', stage, -5.0, 5.0, 0, STAGE_H, STAGE_Z, Z1, (.16, .09, .05), rough=.55)
    s.slab('Drum riser', stage, -1.7, 1.7, STAGE_H, STAGE_H + RISER_H, 4.75, 7.8, (.05, .06, .09), rough=.9)
    model('Stage skirt and curtains', stage, models['StageDress'], (0, 0, 0))
    model('Kit rug', stage, VM + 'DrumRug.obj', (0, STAGE_H + RISER_H + .005, 6.0), 0, .8)
    # Tea towel on the snare (the Legion kit's one costume note), a mug and a setlist by the throne.
    towel = s.entity('Tea towel on the snare', stage, (DRUMMER[0] + .16, DRUMMER[1] + .745, DRUMMER[2] - .6), (0, -90, 0))
    s.box('Towel on the head', towel, (0, .004, 0), (.4, .01, .34), (1, 1, 1), shadows=False)
    s.box('Towel tail', towel, (0, -.11, -.17), (.4, .22, .01), (1, 1, 1), rot=(-8, 0, 0), shadows=False)
    for e in s.entities[-2:]:
        e.components[-1]['Material']['Textures'] = {'Diffuse': {'Path': TEX + 'TeaTowel.png'}}
    model('Mug by the throne', stage, VM + 'BeerCup.obj', (DRUMMER[0] - .85, DRUMMER[1], DRUMMER[2] + .1), 0, .9)
    s.box('Setlist taped down', stage, (.9, DRUMMER[1] + .003, DRUMMER[2] - 1.45), (.21, .004, .29), (.95, .93, .88), rot=(0, 14, 0), shadows=False)
    # Backline.
    model('Guitar cab', stage, VM + 'GuitarCab.obj', (-3.1, STAGE_H, 6.6), 180)
    model('Guitar head', stage, VM + 'AmpHead.obj', (-3.1, STAGE_H + .75, 6.6), 180)
    model('Bass rig', stage, VM + 'AmpRack.obj', (3.2, STAGE_H, 6.7), 180)
    for i, (x, z) in enumerate(((-2.6, 3.15), (2.6, 3.15))):
        model(f'Wedge {i + 1}', stage, VM + 'Wedge.obj', (x, STAGE_H, z), 180)
    for i, x in enumerate((-4.4, 4.4)):
        model(f'PA {i + 1}', stage, VM + 'SpeakerTall.obj', (x, STAGE_H, 3.3), 0 if x < 0 else 0)
    model('Cable coil', stage, VM + 'CableCoil.obj', (-1.9, STAGE_H, 7.6))
    # Flags and the crest behind the band.
    model('Flag of Canada', stage, models['FlagCanada'], (-4.4, STAGE_H, 7.9), 0)
    model('Branch standard', stage, models['FlagBranch'], (4.4, STAGE_H, 7.9), 0)
    model('Signs, crest and photos', hall, models['WallArt'], (0, 0, 0))
    model('Doors', hall, models['Doors'], (0, 0, 0))
    s.box('Exit glow, doors', hall, (-3.2, 2.55, Z0 + .055), (.5, .22, .02), (.2, .9, .4), emissive=(.3, 1, .5),
          emissive_intensity=1.2, shadows=False)
    s.box('Exit glow, fire door', hall, (X1 - .055, 2.65, 5.2), (.02, .22, .5), (.2, .9, .4), emissive=(.3, 1, .5),
          emissive_intensity=1.2, shadows=False)
    # Tables, chairs and the people at them.
    rel = [('Aunt with the cardigan', 'Mother_02', '02_C'), ('Great-uncle', 'ShopKeeper_01', '04_C'),
           ('Neighbour', 'Mother_01', '01_B'), ('Old Legion friend', 'Rigged', '03_C'), ('Cousin-in-law', 'Son_01', '04_B'),
           ('Grandmother', 'Mother_02', '01_A'), ('Family friend', 'SchoolBoy_01', '02_B'), ('The minister', 'ShopKeeper_01', '01_A')]
    seated = {}
    for name, body, variant in rel:
        seated[name] = figure('Seated_' + name.replace(' ', '').replace('-', ''), body, variant, SITTING, lo=True,
                              note=f'{name}, seated')
    seated_at = {2: [(200, 0), (300, 1)], 3: [(40, 2), (170, 3)], 4: [(130, 4), (250, 5)], 5: [(80, 6), (220, 7)]}
    for x, z, seed in TABLES:
        t = s.group(f'Table {seed}', dress, (x, 0, z))
        model('Table and settings', t, models[f'Table{seed}'], (0, 0, 0))
        n = 7 if seed == 1 else 6
        people = dict(seated_at.get(seed, []))
        for c in range(n):
            ang = (360.0 / n) * c + seed * 17
            if seed == 1 and c in (0, 1, 2, 4):
                continue      # T1's chairs on the floor side are the family's, placed below
            a = math.radians(ang)
            cx, cz = math.sin(a) * 1.05, math.cos(a) * 1.05
            face = ang + 180   # toward the table
            chair_yaw = face + (8 if c % 2 else -6)
            model(f'Chair {c + 1}', t, models['FoldingChair'], (cx, 0, cz), chair_yaw)
            for want, who in seated_at.get(seed, []):
                if abs(((ang - want + 180) % 360) - 180) < 360.0 / n / 2:
                    hx, _, hz = chair_hip(cx, cz, chair_yaw)
                    place(s, t, rel[who][0], seated[rel[who][0]], (hx, 0, hz), chair_yaw, motion['Breathe'],
                          .8 + .07 * who)
    # The family table's floor side: her chair, the empty chair, and one more.
    ft = s.group('Family table, floor side', dress)
    model("Her chair", ft, models['FoldingChair'], (DAUGHTER_CHAIR[0], 0, DAUGHTER_CHAIR[1]), DAUGHTER_CHAIR[2])
    model('The empty chair', ft, models['FoldingChair'], (EMPTY_CHAIR[0], 0, EMPTY_CHAIR[1]), EMPTY_CHAIR[2])
    model('Chair 3', ft, models['FoldingChair'], (-5.45, 0, .95), 120)
    model('Uncle’s chair', ft, models['FoldingChair'], (UNCLE_SEAT[0], 0, UNCLE_SEAT[1]), UNCLE_SEAT[2])

    model('The bar', dress, models['Bar'], (X0 + .45, 0, -12.3))
    for i, z in enumerate((-13.6, -12.8, -12.0, -11.2)):
        model(f'Bar stool {i + 1}', dress, VM + 'Stool.obj', (X0 + 1.25, 0, z), 15 * i)
    model('Dartboard', dress, models['Dartboard'], (X1 - .03, 1.73, -11.9), -90)
    model('Coat rack', dress, models['CoatRack'], (3.0, 0, Z0 + .5))
    model('Coat rack 2', dress, models['CoatRack'], (4.2, 0, Z0 + .45))
    model('Stacked chairs', dress, models['StackedChairs'], (X1 - .45, 0, -14.0), 90)
    model('Stacked chairs 2', dress, models['StackedChairs'], (X1 - .45, 0, -6.6), 90)
    model('Party T-bar west', dress, models['TBarStand'], (-5.9, 0, 2.2), 0)
    model('Party T-bar east', dress, models['TBarStand'], (5.9, 0, 1.6), 0)
    model('Memorial table', dress, models['MemorialTable'], (MEMORIAL[0], 0, MEMORIAL[1]), MEMORIAL[2])
    model('Easel', dress, models['Easel'], (EASEL[0], 0, EASEL[1]), EASEL[2])
    model('Upright piano', dress, models['UprightPiano'], (PIANO[0], 0, PIANO[1]), PIANO[2])
    model('Cooler of pop', dress, VM + 'Cooler.obj', (X0 + .6, 0, -9.2), 80)
    model('Recycling bin', dress, VM + 'CardboardBox.obj', (X0 + .55, 0, -8.5), 10)
    # Mirror ball over the parquet.
    s.box('Mirror ball chain', dress, (0, CEIL - .2, -1.4), (.015, .4, .015), (.4, .4, .42), shadows=False)
    s.box('Mirror ball', dress, (0, CEIL - .55, -1.4), (.36, .36, .36), (.85, .87, .9), rough=.12, metallic=1.0,
          shape='Sphere', shadows=False)
    # Coloured party bulbs along the valance.
    for i in range(22):
        x = -5.2 + i * (10.4 / 21)
        col = (AMBER, MAGENTA, TEAL, BLUE)[i % 4]
        s.box(f'Party bulb {i + 1}', stage, (x, CEIL - .5 - .05 * math.sin(i * math.pi / 3.5) ** 2, STAGE_Z - .06),
              (.06, .08, .06), col, emissive=col, emissive_intensity=2.4, shadows=False, shape='Sphere')
    # Candle flames on the memorial table.
    for i, lx in enumerate((-.4, -.25)):
        fx, _, fz = rot_y((lx, 0, .1), MEMORIAL[2])
        s.box(f'Candle flame {i + 1}', dress, (MEMORIAL[0] + fx, .76 + .25, MEMORIAL[1] + fz), (.022, .045, .022), (1, .8, .4),
              emissive=(1, .7, .3), emissive_intensity=3.0, shadows=False, shape='Sphere')
    # Piano sconce glow.
    for i, lx in enumerate((-.62, .62)):
        fx, _, fz = rot_y((lx, 1.13, -.22), PIANO[2])
        s.box(f'Piano sconce bulb {i + 1}', dress, (PIANO[0] + fx, 1.12, PIANO[1] + fz), (.03, .06, .03), (1, .8, .5),
              emissive=(1, .75, .4), emissive_intensity=2.0, shadows=False, shape='Sphere')

    # ---- people who don't move with the story -------------------------------------------------------
    # The bartender behind the bar.
    keep = figure('Bartender', 'Mother_01', '04_A', Pose(arm_r=((-35, 0, -10), 70), arm_l=((-20, 0, 8), 40)), lo=True)
    place(s, family, 'Bartender', keep, (X0 + .35, 0, -11.6), 90)

    # ---- story: toast_seat_empty -------------------------------------------------------------------
    # Before: the uncle on his feet behind the empty chair, glass up, a narrow light on him.
    toast_pose = Pose(torso=(-3, 0, 0), head=(-8, 0, 0), arm_r=((-128, 0, -8), 35), arm_l=((-30, 0, 8), 75))
    uncle_toast = figure('Uncle_Toast', 'ShopKeeper_01', '03_A', toast_pose, both(glass_in(1), paper_in(-1)),
                         note='The uncle making the toast')
    g = s.story('Toast: the uncle on his feet', story, 'toast_seat_empty', False, 1.2, (-5.35, 0, -1.05))
    place(s, g, 'The uncle, toasting', uncle_toast, (0, 0, 0), 70)
    s.light('A narrow light on the toast', g, (1.15, CEIL - .1, -.55), 'Spot', WARM, 210, 7,
            rot=look_rotation((-4.2, CEIL - .1, -1.6), (-5.4, 1.2, -1.0)), inner=8, outer=16)
    # After: the pool widens to her and the empty chair; his folded toast left on its seat; he sits.
    g = s.story('Toast done: the pool on her and the empty chair', story, 'toast_seat_empty', True, 2.5,
                (EMPTY_CHAIR[0], 0, EMPTY_CHAIR[1]))
    model('The folded toast on the seat', g, models['ToastChair'], (0, 0, 0), EMPTY_CHAIR[2])
    pool = (-3.6, CEIL - .1, -1.3)
    s.light('The pool widens', g, (pool[0] - EMPTY_CHAIR[0], pool[1], pool[2] - EMPTY_CHAIR[1]), 'Spot', WARM, 300, 9,
            rot=look_rotation(pool, (-5.1, .4, -.05)), inner=14, outer=30)
    # (the couple's own light is with them on the floor)
    sat = s.story('Uncle seated (until he gets up to dance)', story, 'toast_seat_empty', True, 1.5,
                  (UNCLE_SEAT[0], 0, UNCLE_SEAT[1]))
    sat2 = s.story('...he gets up to dance', sat, 'shoes_by_chair', False, 1.0, (0, 0, 0))
    uncle_sat = figure('Uncle_Seated', 'ShopKeeper_01', '03_A', Pose(True, (6, 0, 0), (-6, -15, 0), ((-30, 0, 6), 70), ((-38, 0, -6), 88)),
                       glass_in(1, 'tumbler'), note='The uncle, sitting down after the toast')
    hx, _, hz = chair_hip(0, 0, UNCLE_SEAT[2])
    place(s, sat2, 'The uncle, seated', uncle_sat, (hx, 0, hz), UNCLE_SEAT[2], motion['Breathe'], .9)

    # ---- story: the daughter at the table until she dances (shoes_by_chair) ------------------------------
    daughter_sat = figure('Daughter_Seated', 'Daughter_01', '01_C', Pose(True, (2, 0, 0), (-3, 10, 4), ((-24, 0, 6), 70), ((-24, 0, -6), 66)),
                          note='Dad’s daughter at the family table')
    g = s.story('Daughter at the table', story, 'shoes_by_chair', False, 1.0, (DAUGHTER_CHAIR[0], 0, DAUGHTER_CHAIR[1]))
    hx, _, hz = chair_hip(0, 0, DAUGHTER_CHAIR[2])
    place(s, g, 'Dad’s daughter, seated', daughter_sat, (hx, 0, hz), DAUGHTER_CHAIR[2], motion['Breathe'], 1.1)
    # The slow dance on the open floor.
    g = s.story('Daughter and uncle sway on the floor', story, 'shoes_by_chair', True, 1.5, (-.9, 0, -.7))
    couple = s.entity('Couple', g)
    body = s.entity('Body', couple)
    couple.add({'Type': 'Sequence', 'Clip': motion['Sway'], 'PlayOnStart': True, 'Loop': True, 'Speed': 1.0,
                'Bindings': [{'Slot': 'Body', 'Target': body.guid}]})
    d_dance = figure('Daughter_Dancing', 'Daughter_01', '01_C', Pose(torso=(4, 0, 0), head=(6, 0, -10), arm_l=((-95, 0, 22), 55), arm_r=((-95, 0, -22), 55)),
                     note='Dad’s daughter, slow-dancing')
    u_dance = figure('Uncle_Dancing', 'ShopKeeper_01', '03_A', Pose(torso=(3, 0, 0), head=(10, 0, 8), arm_l=((-55, 0, 18), 75), arm_r=((-60, 0, -14), 80)),
                     note='The uncle, slow-dancing')
    s.entity('Her', body, (0, 0, -.27), (0, 0, 0)).add({'Type': 'Model', 'ModelPath': d_dance})
    s.entity('Him', body, (0, 0, .29), (0, 180, 0)).add({'Type': 'Model', 'ModelPath': u_dance})
    s.light('A light finds them on the floor', g, (0, CEIL - .1, 0), 'Spot', WARM, 260, 6, rot=(90, 0, 0), inner=12, outer=26)
    # Her good shoes under the empty chair, in the light they just left.
    g = s.story('Her shoes under the empty chair', story, 'shoes_by_chair', True, .6, (EMPTY_CHAIR[0], 0, EMPTY_CHAIR[1]))
    model('Her good shoes', g, models['Heels'], (.05, 0, .05), EMPTY_CHAIR[2] + 160)

    # ---- story: dessert_table_moved ----------------------------------------------------------------------
    g = s.story('Dessert cart on the dance floor', story, 'dessert_table_moved', False, 1.0, (CART_ON_FLOOR[0], 0, CART_ON_FLOOR[1]))
    model('Dessert cart', g, models['DessertCart'], (0, 0, 0), CART_ON_FLOOR[2])
    g = s.story('Dessert cart pushed to the east wall', story, 'dessert_table_moved', True, 1.0, (CART_AT_WALL[0], 0, CART_AT_WALL[1]))
    model('Dessert cart, against the wall', g, models['DessertCartPushed'], (0, 0, 0), CART_AT_WALL[2])
    s.light('Over the desserts', g, (-1.2, 2.7, 0), 'Point', WARM, 18, 3.2)

    # ---- story: portrait_on_piano ------------------------------------------------------------------------
    g = s.story('Portrait on the easel', story, 'portrait_on_piano', False, 1.2, (EASEL[0], 0, EASEL[1]))
    ep = s.entity('On the ledge', g, rot_y((0, 1.04, -.08), EASEL[2]), (-8, EASEL[2], 0))
    ep.add({'Type': 'Model', 'ModelPath': models['Portrait']})
    s.light('Picture light on the easel', g, (-5.6 - EASEL[0], CEIL - .1, 1.6 - EASEL[1]), 'Spot', WARM, 160, 6,
            rot=look_rotation((-5.6, CEIL - .1, 1.6), (EASEL[0], 1.5, EASEL[1])), inner=7, outer=15)
    g = s.story('Portrait on the piano', story, 'portrait_on_piano', True, 1.2, (PIANO[0], 1.3, PIANO[1]))
    px, _, pz = rot_y((0, 0, .05), PIANO[2])
    pp = s.entity('Leaning on the wall', g, (px, 0, pz), (-6, PIANO[2], 0))
    pp.add({'Type': 'Model', 'ModelPath': models['Portrait']})
    tx, _, tz = rot_y((.7, 0, -.11), PIANO[2])
    model('His tie on the corner', g, models['Tie'], (tx, 0, tz), PIANO[2])
    nx, _, nz = rot_y((-.5, 0, .08), PIANO[2])
    model('Napkin requests', g, models['Napkins'], (nx, 0, nz), PIANO[2] + 10)
    s.light('Picture light on the piano', g, (5.4 - PIANO[0], CEIL - .1 - 1.3, .4 - PIANO[1]), 'Spot', WARM, 190, 6.5,
            rot=look_rotation((5.4, CEIL - .1, .4), (PIANO[0], 1.65, PIANO[1])), inner=8, outer=17)

    # ---- story: family_on_floor ----------------------------------------------------------------------------
    g = s.story('Cousins fill the parquet', story, 'family_on_floor', True, 1.5, (.8, 0, -1.0))
    cousins = [('Cousin_Arms_Up', 'Son_01', '02_A', Pose(head=(-8, 0, 0), arm_l=((-165, 0, 12), 15), arm_r=((-165, 0, -12), 15)), (1.2, 0, .6), 200),
               ('Cousin_Twirl', 'SchoolGirl_01', '04_A', Pose(head=(-4, 0, 6), arm_l=((-150, 0, 20), 25), arm_r=((-40, 0, -30), 50)), (2.1, 0, -.6), 235),
               ('Cousin_Point', 'Mother_01', '03_B', Pose(torso=(-4, 0, 0), arm_r=((-120, 0, -10), 10), arm_l=((-40, 0, 20), 70)), (.2, 0, -2.0), 160),
               ('Cousin_Clap', 'SchoolBoy_01', '02_C', Pose(arm_l=((-70, 0, 25), 70), arm_r=((-70, 0, -25), 70)), (2.4, 0, 1.3), 215),
               ('Cousin_Jump', 'Rigged', '04_C', Pose(head=(-12, 0, 0), arm_l=((-170, 0, 25), 5), arm_r=((-170, 0, -25), 5)), (-.4, 0, .9), 170),
               ('Cousin_Sway', 'Mother_02', '01_B', Pose(head=(5, 0, -8), arm_l=((-100, 0, 10), 60), arm_r=((-30, 0, -10), 40)), (1.6, 0, -1.9), 250)]
    for i, (name, body_, variant, pose, at, yaw) in enumerate(cousins):
        path = figure(name, body_, variant, pose, lo=True, note=name.replace('_', ' '))
        place(s, g, name.replace('_', ' '), path, (at[0] - .8, 0, at[2] + 1.0), yaw, motion['Bounce'], .9 + .08 * i)
    # His shoes join hers.
    g = s.story('His shoes join hers', story, 'family_on_floor', True, .6, (EMPTY_CHAIR[0], 0, EMPTY_CHAIR[1]))
    model('His shoes', g, models['Oxfords'], (-.18, 0, -.12), EMPTY_CHAIR[2] + 200)
    # The photo: a cousin up on a chair by the piano, the flash lit.
    g = s.story('The family photo', story, 'family_on_floor', True, .8, (-2.7, 0, -2.6))
    model('Chair she stands on', g, models['FoldingChair'], (0, 0, 0), 70)
    snap = figure('Cousin_Camera', 'Mother_02', '02_B', Pose(head=(6, 0, 0), arm_l=((-80, 0, 20), 95), arm_r=((-80, 0, -20), 95)), camera_in,
                  note='The cousin taking the family photo')
    place(s, g, 'Cousin with the camera', snap, (0, .49, 0), 70)
    fx, _, fz = rot_y((0, 0, .3), 70)
    s.box('The flash', g, (fx, 2.12, fz), (.07, .05, .05), (1, 1, 1), emissive=(1, 1, 1), emissive_intensity=2.0, shadows=False)
    s.light('Photo flash', g, (fx - .2, 2.2, fz), 'Point', (1, .97, .92), 30, 5)

    # ---- lights -------------------------------------------------------------------------------------------
    s.light('Hall key (through the ceiling)', lamps, (0, 12, -8), 'Directional', (1.0, .86, .7), .55,
            rot=(58, 18, 0), shadows=True)
    for i, (x, z) in enumerate(((-5.5, -11.5), (0, -11.5), (5.5, -11.5), (-5.5, -6.0), (5.5, -6.0), (0, -6.0))):
        s.light(f'Fluorescents, dimmed {i + 1}', lamps, (x, CEIL - .1, z), 'Spot', FLUO, 110, 7.5, rot=(90, 0, 0),
                inner=40, outer=75)
    s.light('Behind the bar', lamps, (X0 + .9, 2.4, -12.3), 'Point', AMBER, 40, 4.5)
    s.light('Exit green', lamps, (-3.2, 2.4, Z0 + .3), 'Point', (.3, 1, .5), 6, 2.5)
    s.light('Memorial candles', lamps, (MEMORIAL[0] + .15, 1.2, MEMORIAL[1] - .2), 'Point', (1, .62, .3), 9, 2.6)
    s.light('Piano sconces', lamps, (PIANO[0] - .5, 1.35, PIANO[1] - .5), 'Point', (1, .7, .4), 10, 2.8)
    s.light('Window spill', lamps, (X1 - .5, 2.2, -11.4), 'Point', (.4, .5, .9), 8, 4.5)
    s.light('Warm house light over the family table', lamps, (-6.3, CEIL - .2, -1.5), 'Spot', WARM, 170, 7, rot=(90, 0, 0), inner=35, outer=72)
    s.light('Warm house light, east tables', lamps, (6.6, CEIL - .2, -6.4), 'Spot', WARM, 170, 7, rot=(90, 0, 0), inner=35, outer=72)
    s.light('Warm house light, memorial corner', lamps, (-6.6, CEIL - .2, 2.4), 'Spot', WARM, 170, 7, rot=(90, 0, 0), inner=35, outer=72)
    s.light('Warm house light, west tables', lamps, (-6.2, CEIL - .2, -7.0), 'Spot', WARM, 170, 7, rot=(90, 0, 0), inner=35, outer=72)
    s.light('Warm house light, piano corner', lamps, (6.6, CEIL - .15, 1.2), 'Spot', WARM, 170, 7, rot=(90, 0, 0), inner=35, outer=72)
    s.light('Crest light', lamps, (0, CEIL - .15, 3.6), 'Spot', WARM, 140, 7, rot=look_rotation((0, CEIL - .15, 3.6), (0, 2.7, Z1)), inner=10, outer=20)

    def spot(name, pos, to, color, power, reach, inner, outer, role, group=0):
        s.light(name, lamps, pos, 'Spot', color, power, reach, rot=look_rotation(pos, to), inner=inner, outer=outer,
                show=role, group=group)
    # The nephew's party lights: four cans on each T-bar, washing the stage.
    for side, (tx, tz) in ((-1, (-5.9, 2.2)), (1, (5.9, 1.6))):
        for i, col in enumerate((AMBER, MAGENTA, TEAL, BLUE)):
            x = tx - .5 + i / 3
            spot(f'Party can {"W" if side < 0 else "E"}{i + 1}', (x, 2.2, tz + .05), (-side * 1.2 + (i - 1.5) * .7, 1.0, 5.6),
                 col, 650, 11, 14, 30, 'Wash', i % 3)
    # Beams: two off the mirror ball onto the floor, two from the stage lip up the back wall.
    for i, (to, col) in enumerate((((-2.4, 0, -3.5), MAGENTA), ((2.6, 0, .6), TEAL))):
        spot(f'Mirror ball beam {i + 1}', (0, CEIL - .7, -1.4), to, col, 420, 6, 3, 7, 'Beam', i)
    for i, (x, col) in enumerate(((-3.6, AMBER), (3.6, BLUE))):
        spot(f'Uplight {i + 1}', (x, STAGE_H + .1, 3.0), (x * .4, 3.0, Z1), col, 700, 8, 5, 12, 'Beam', i)
    # Follow spots from the ceiling over the floor.
    for i, (pos, to) in enumerate((((0, CEIL - .15, -1.0), (0, 1.8, DRUMMER[2] - .3)), ((-1.5, CEIL - .15, -1.2), (-2.6, 1.4, 4.3)),
                                   ((1.5, CEIL - .15, -1.2), (2.6, 1.4, 4.4)))):
        spot(f'Follow {i + 1}', pos, to, (1, .9, .8), 560, 12, 7, 15, 'Spot', i)
    for i, (tx, tz) in enumerate(((-5.9, 2.2), (5.9, 1.6))):
        spot(f'Blinder {i + 1}', (tx, 2.35, tz - .1), (tx * .3, 1.4, -8), WARM, 520, 14, 18, 40, 'Blinder', i)
    spot('Strobe on the lip', (0, STAGE_H + .1, 3.0), (0, 1.5, -6), (1, 1, 1), 600, 12, 30, 55, 'Strobe', 0)

    # ---- markers ----------------------------------------------------------------------------------------
    s.info(marks, 'Funeral Afterparty at the Legion', 'Drumsmith', outdoor=False, room_back=Z0, room_ceiling=CEIL,
           half_width=X1, desk_z=-13.0, ambient=(.06, .045, .035), fog_color=(.03, .022, .016), haze=.45)
    s.spot(marks, 'Drummer', DRUMMER)
    s.spot(marks, 'Guitar', (-2.6, STAGE_H, 4.3), 8)
    s.spot(marks, 'Bass', (2.6, STAGE_H, 4.4), -8)
    for name, x0, x1, z0, z1, n, fig in [
            ('Standing at the back', -4.2, 5.4, -13.2, -10.6, 20, 'Mob'),
            ('At the bar', -8.0, -5.8, -13.6, -10.6, 7, 'Mob'),
            ('Watching the floor', -3.0, 3.0, -10.0, -8.0, 9, 'Posed'),
            ('West, between the tables', -4.8, -3.4, -9.2, -5.6, 6, 'Mob'),
            ('East of the floor', 3.4, 5.2, -1.6, 1.8, 7, 'Posed'),
            ('Between the east tables', 3.5, 5.3, -9.6, -5.2, 7, 'Mob')]:
        s.crowd(name, marks, ((x0 + x1) / 2, 0, (z0 + z1) / 2), x1 - x0, z1 - z0, n, .6, 0, fig)
    cams = s.group('Camera positions', marks)
    for tag, kind, eye, aim, fov in [
            ('hall-wide', 'Wide', (.4, 3.25, -14.6), (0, 1.1, 2.5), 60),
            ('crane-west', 'Crane', (-7.4, 3.25, -8.6), (.6, 1.0, 2.2), 56),
            ('bar-long-lens', 'Desk', (-4.2, 2.05, -13.2), (0, 1.75, 6.5), 30),
            ('toast-table', 'Custom', (.5, 1.9, -5.2), (-2.9, .9, -.5), 58),
            ('portrait-piano', 'Custom', (3.4, 1.85, -2.6), (7.5, 1.55, 2.4), 46),
            ('dance-floor', 'Custom', (-1.6, 1.65, -6.9), (.3, 1.15, -.6), 55),
            ('dessert-wall', 'Custom', (4.6, 1.75, -4.6), (8.3, .95, -.4), 50),
            ('memorial', 'Custom', (-3.8, 1.7, -1.4), (-7.2, 1.45, 3.0), 50),
            ('tea-towel', 'Close', (1.7, 2.0, 5.0), (.1, 1.3, 6.1), 44)]:
        s.camera_spot(tag, cams, eye, aim, kind, fov, tag)
    for i, (eye, aim, fov) in enumerate([
            ((-.3, 1.62, -14.6), (-.2, 1.6, -9.0), 64), ((.2, 1.66, -13.2), (-8.0, 1.6, -12.0), 62),
            ((.6, 1.7, -11.0), (-6.5, 1.3, -4.6), 60), ((-.9, 1.72, -8.4), (-7.2, 1.4, 2.6), 58),
            ((-.6, 1.78, -6.5), (5.5, 1.4, -.5), 58), ((0, 1.85, -5.0), (0, 1.8, 5.5), 56)]):
        s.camera_spot(f'Arrival {i + 1:02}', cams, eye, aim, 'Custom', fov, f'arrival/{i + 1:02}')
    return s


def readme():
    text = """# StoryLegion models

Everything here is generated by `Tools/Venues/make_story_legion.py` (with `story_legion_mesh.py`,
`story_legion_props.py`, `story_legion_people.py`, `story_legion_textures.py`). Rerun it to rebuild.

- Furniture, piano, dessert cart, easel, flags, bar, wall art and the rest are original low-poly
  meshes written by `story_legion_props.py`, coloured from `../Textures/Legion_Palette.png` and the
  painted textures in `../Textures/` (all drawn by `story_legion_textures.py`; the crest, the names on
  the honour roll and Dad's portrait are invented).
- `People/*.obj` are posed from the crowd's rigid pieces in `Assets/Models/People/Crowd/<body>/`
  (cut from the owner's Synty Polygon character FBXs by `Game/Tools/MakeCrowdPieces.py`), each baked
  into one mesh. They read the owner's Synty Town atlas variants in `Assets/Models/Venue/`
  (`PolygonTown_<variant>.png`) in place. Licence: owner's Synty licence.
- The scene also references, in place and read-only, these models from `Assets/Models/Venue/`:
  DrumRug, BeerCup, GuitarCab, AmpHead, AmpRack, Wedge, SpeakerTall, CableCoil, Stool, Cooler,
  CardboardBox (see that folder's README for their Synty sources; owner's Synty licence).
"""
    (MODELS / 'README.md').write_text(text)


def main():
    scene = build()
    scene.write(str(VENUE / f'{ID}.lvl'))
    preview = 'Preview.jpg' if (VENUE / 'Preview.jpg').exists() else None
    write_venue_json(str(VENUE), 'Funeral Afterparty at the Legion', f'{ID}.lvl', preview=preview,
                     ambience='Ambience.ogg' if (VENUE / 'Ambience.ogg').exists() else 'Assets/Sounds/crowd.mp3')
    readme()
    print(f'{len(scene.entities)} entities in {ID}')


if __name__ == '__main__':
    main()
