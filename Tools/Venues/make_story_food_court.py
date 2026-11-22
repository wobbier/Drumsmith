#!/usr/bin/env python3
"""Writes Assets/Venues/StoryFoodCourt/: story set 08, "Food Court Farewell Show" (s08-food-court).

    python3 Tools/Venues/make_story_food_court.py [--textures]

A dying mall's food court on its last Saturday. The band plays on the floor in front of a riser of
three cafeteria tables; the kids stand in the drained fountain; the stall fronts behind have their
shutters half down; escalators climb to a mezzanine under a skylight hung with closing-down banners.

Story flags (Design/Story-Mode-Setlists.json, s08-food-court):
  one_signature  the spare kick head appears on the fountain lip with one signature; the skate-shop
                 kid claims the spot beside it; a cardboard SIGN THE HEAD! goes up on the spout.
  guard_drawn    a cartoon peaked cap on the head; two boards lean beside it with a second skater;
                 the mall guard leaves his security desk and stands behind them.
  guard_signed   a moustache under the cap; the guard moves beside the kid, clapping; a bunch of
                 balloons from the card shop goes up on the spout; half the fluorescents go off.
  shutters_down  every stall shutter rolls down; the stall and mall lights go off and the skylight
                 turns to dusk; party lights come on; staff in name tags fill the fountain rim; the
                 head comes back almost black with signatures.
  head_on_riser  the head leaves the fountain and stands on the drum riser; the kid stands on the
                 rim with both arms up.
Deterministic: rerun = same bytes. --textures repaints the PNGs with ImageMagick.
"""
import math
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
from venuegen import Scene, look_rotation, repo_root, write_venue_json  # noqa: E402
import story_food_court_art as art  # noqa: E402
import story_food_court_fbx as fbx  # noqa: E402
import story_food_court_people as people  # noqa: E402

ID = 'StoryFoodCourt'
FOLDER = os.path.join(repo_root(), 'Assets', 'Venues', ID)
L = art.LOCAL
SYNTY = '/home/mitch/Projects/MitchGame/Assets/Models/Synty'
VENUE = 'Assets/Models/Venue/'

# Palette (sRGB).
TILE_WALL = (.80, .76, .68)
CREAM = (.86, .82, .72)
TERRA = (.66, .36, .24)
TEAL = (.12, .42, .46)
CHROME = (.72, .74, .78)
DARK = (.10, .10, .12)
LAMINATE = (.90, .52, .18)
CEILING = (.78, .78, .76)
FLUO = (.92, .97, 1.0)

# (name, pack folder, fbx, size m along y, atlas)
SYNTY_MODELS = [
    ('VendingMachine', 'OfficePack', 'SM_Prop_VendingMachine_01', 1.95),
    ('Arcade', 'OfficePack', 'SM_Prop_ArcadeMachine_01', 1.9),
    ('CafeChair', 'OfficePack', 'SM_Prop_Chair_05', .9),
    ('StackChair', 'OfficePack', 'SM_Prop_Chair_09', .83),
    ('CafeTable', 'OfficePack', 'SM_Prop_Table_02', .75),
    ('TrashBin', 'OfficePack', 'SM_Prop_Trashbin_01', 1.1),
    ('WetFloor', 'OfficePack', 'SM_Prop_Sign_Wetfloor_01', .75),
    ('JanitorCart', 'OfficePack', 'SM_Prop_Janitor_Cart_01', 1.15),
    ('Balloon', 'OfficePack', 'SM_Prop_Balloon_01', 1.8),
    ('SecurityCam', 'OfficePack', 'SM_Prop_Security_Camera_02', .5),
    ('Planter', 'OfficePack', 'SM_Prop_Plant_07', 1.5),
    ('PottedPalm', 'OfficePack', 'SM_Prop_Plant_01', 1.4),
    ('NeonCactus', 'OfficePack', 'SM_Prop_Neon_Cactus_01', .55),
    ('Bunting', 'OfficePack', 'SM_Prop_Bunting_01', .63),
    ('PaperCup', 'OfficePack', 'SM_Prop_Cup_Paper_01', .15),
    ('DonutBox', 'OfficePack', 'SM_Prop_Donut_Box_01', .1),
    ('TableFootball', 'OfficePack', 'SM_Prop_TableFootball_01', .89),
]
ATLAS = {'OfficePack': 'PolygonOffice_Texture_01_A.png', 'Town': 'PolygonTown_01_A.png'}


def import_synty():
    """Copy the Synty props this venue uses into Models/ as OBJs (with their atlas) + provenance."""
    rows = []
    for name, pack, src, size in SYNTY_MODELS:
        path = os.path.join(SYNTY, pack, 'FBX', src + '.fbx')
        dst = os.path.join(art.MODELS, name + '.obj')
        if not os.path.exists(path):
            if not os.path.exists(dst):
                sys.exit(f'missing Synty source {path}')
            continue
        tex = ATLAS[pack]
        tex_src = os.path.join(SYNTY, pack, 'Textures', tex)
        if not os.path.exists(os.path.join(art.MODELS, tex)):
            shutil.copyfile(tex_src, os.path.join(art.MODELS, tex))
        art._save(os.path.join(art.MODELS, name + '.mtl'), f'newmtl {name}\nKd 1 1 1\nKs 0 0 0\nNs 0\nillum 1\nmap_Kd {tex}\n')
        ext = fbx.convert(path, dst, name, f'Synty {pack}/FBX/{src}.fbx; {size} m tall, floor-centred pivot.', size)
        rows.append(f'- `{name}.obj`: {pack}/FBX/{src}.fbx, with {tex}; {size} m tall ({ext[0]:.2f} x {ext[2]:.2f} m footprint).')
    if rows:
        readme = ['# Food Court Farewell Show models', '',
                  'Made by `Tools/Venues/make_story_food_court.py` (rerun to rebuild).', '',
                  '## Copied from the owner\'s Synty packs', '',
                  'Licence: the owner\'s Synty licence. Source: `MitchGame/Assets/Models/Synty/`. Converted from FBX to OBJ by',
                  '`Tools/Venues/story_food_court_fbx.py` (node transforms applied, uniformly scaled to the stated size, floor-centred',
                  'pivot; vertices and UVs kept). The pack atlas is copied beside them.', ''] + rows + [
                  '', '## People', '',
                  '- `People/Kid/`: the game crowd pieces of BodyType1_SchoolGirl_01 (`Assets/Models/People/Crowd/SchoolGirl_01/`),',
                  '  bound to `Assets/Models/Venue/PolygonTown_04_A.png` (the manifest\'s skate-shop kid). Owner\'s Synty licence.',
                  '- `People/Guard/`: the crowd pieces of BodyType1_ShopKeeper_01 bound to `PolygonTown_04_B.png` (the mall guard).', '',
                  '## Original', '',
                  'Every other PNG (stall signs, menus, banners, posters, shutters, the floor tile and the four drumhead states) is',
                  'painted by `Tools/Venues/story_food_court_art.py` with ImageMagick and the repo fonts (Permanent Marker, Gochi Hand,',
                  'both OFL) or DejaVu. The shops, the mall and every name on the head are made up. The flat meshes carrying them',
                  '(Sign*, Banner*, Head*, Shutter*, Floor*) are written by the same module.', '']
        art._save(os.path.join(art.MODELS, 'README.md'), '\n'.join(readme))


def octagon(r, cx, cz, a0=22.5):
    return [(cx + r * math.cos(math.radians(a0 + 45 * i)), cz + r * math.sin(math.radians(a0 + 45 * i))) for i in range(8)]


def build():
    art.paint_textures('--textures' in sys.argv)
    import_synty()
    people.clips()
    kid_base = people.dress('Kid', 'SchoolGirl_01', 'PolygonTown_04_A')
    guard_base = people.dress('Guard', 'ShopKeeper_01', 'PolygonTown_04_B')

    # Flat meshes.
    signs = {}
    for f in art.FASCIAS:
        signs[f[0]] = art.quad(f[0], 4.2, 1.05, f[0] + '.png', emissive=.85)
    menus = [art.quad(m, 3.0, 1.12, m + '.png', emissive=.75) for m in ('MenuA', 'MenuB', 'MenuC')]
    must_go = art.quad('BannerMustGo', 4.2, 1.58, 'BannerMustGo.png', double=True)
    must_go2 = art.quad('BannerMustGo2', 6.0, 1.5, 'BannerMustGo2.png', double=True)
    thanks = art.quad('BannerThanks', 7.0, 1.75, 'BannerThanks.png')
    skate_banner = art.quad('BannerSkate', 8.0, 2.5, 'BannerSkate.png')
    last_day = art.quad('BannerLastDay', 3.6, 1.35, 'BannerLastDay.png')
    poster = art.quad('PosterClosing', 1.1, 1.1, 'PosterClosing.png')
    no_skate = art.quad('NoSkate', .5, .62, 'NoSkate.png')
    sign_head = art.quad('SignTheHead', .9, .68, 'SignTheHead.png')
    security = art.quad('SignSecurity', 1.6, .5, 'SignSecurity.png', emissive=.6)
    directory = art.quad('Directory', 1.2, 1.5, 'Directory.png', emissive=.7)
    shut_half = art.quad('ShutterHalf', 4.4, 1.45, 'Shutter.png', repeat=(4, .66))
    shut_full = art.quad('ShutterFull', 4.4, 3.4, 'Shutter.png', repeat=(4, 1.55))
    shut_note = art.quad('ShutterNote', 1.1, 2.2, 'ShutterNote.png')
    heads = {k: art.disc('Head' + k, .4, 'Head' + k + '.png') for k in 'ABCD'}
    floor_mesh = art.floor_quad('FloorTiles', -16, 16, -22, 13, 'FloorTile.png', 2.0)

    s = Scene(seed=8008)
    root = s.group('Food Court Farewell Show')
    shell = s.group('Mall shell', root)
    court = s.group('Food court floor', root)
    stalls = s.group('Stall fronts', root)
    stage = s.group('Stage and riser', root)
    dress = s.group('Closing-down dressing', root)
    lamps = s.group('Mall lights', root)
    rig = s.group('Band rig', root)
    story = s.group('Story', root)
    marks = s.group('Venue markers', root)

    def sg(name, parent, flag, when_set=True, fade=.75, pos=(0, 0, 0)):
        """A story group pivoted at pos (it grows from there) whose contents are authored in venue
        space: the returned child undoes the pivot's offset. Every parent here sits at the origin."""
        g = s.story(name, parent, flag, when_set, fade, pos)
        return s.group('(venue space)', g, tuple(-v for v in pos))

    def model(name, parent, file, pos, yaw=0.0, scale=1.0):
        return s.prop(name, parent, file if file.startswith('Assets/') else L + file + '.obj', pos, yaw, scale)

    # ---- the shell --------------------------------------------------------------------------
    s.slab('Slab under the tiles', shell, -16.5, 16.5, -.3, -.01, -22.5, 13.5, (.35, .32, .3))
    s.prop('Terrazzo tiles', shell, floor_mesh, (0, .0, 0))
    s.slab('Back wall', shell, -16.5, 16.5, 0, 10.4, 13, 13.4, TILE_WALL)
    s.slab('Wall left', shell, -16.5, -16, 0, 10.4, -22.5, 13.4, TILE_WALL)
    s.slab('Wall right', shell, 16, 16.5, 0, 10.4, -22.5, 13.4, TILE_WALL)
    s.slab('Wall behind the crowd (lower)', shell, -16.5, 16.5, 0, 4.5, -22.9, -22.5, TILE_WALL)
    s.slab('Wall behind the crowd (upper)', shell, -16.5, 16.5, 4.5, 10.4, -22.9, -22.5, (.7, .66, .6))
    # Ceiling at 10 m with the skylight well in the middle.
    sx0, sx1, sz0, sz1 = -8.5, 8.5, -15, 7.5
    s.slab('Ceiling front', shell, -16.5, 16.5, 10, 10.4, sz1, 13.4, CEILING)
    s.slab('Ceiling back', shell, -16.5, 16.5, 10, 10.4, -22.9, sz0, CEILING)
    s.slab('Ceiling left', shell, -16.5, sx0, 10, 10.4, sz0, sz1, CEILING)
    s.slab('Ceiling right', shell, sx1, 16.5, 10, 10.4, sz0, sz1, CEILING)
    # The skylight: a lantern of glass panes on a white steel grid, lit as day (or dusk, later).
    sky = s.group('Skylight', shell)
    for x in [sx0 + i * (sx1 - sx0) / 6 for i in range(7)]:
        s.slab('Skylight rib', sky, x - .09, x + .09, 11.2, 11.42, sz0, sz1, (.92, .92, .9))
    for z in [sz0 + i * (sz1 - sz0) / 8 for i in range(9)]:
        s.slab('Skylight purlin', sky, sx0, sx1, 11.25, 11.42, z - .07, z + .07, (.92, .92, .9))
    s.slab('Skylight upstand', sky, sx0 - .3, sx1 + .3, 10.0, 11.4, sz0 - .3, sz0, CEILING)
    s.slab('Skylight upstand', sky, sx0 - .3, sx1 + .3, 10.0, 11.4, sz1, sz1 + .3, CEILING)

    # Mezzanine: a U of walkway at 4.8 m, back and both sides, with a balustrade and fascia.
    MZ = 4.8
    s.slab('Mezzanine back', shell, -16, 16, MZ - .4, MZ, 8.7, 13, CEILING)
    s.slab('Mezzanine left', shell, -16, -10.6, MZ - .4, MZ, -18, 8.7, CEILING)
    s.slab('Mezzanine right', shell, 10.6, 16, MZ - .4, MZ, -18, 8.7, CEILING)
    s.slab('Mezzanine floor tiles back', shell, -16, 16, MZ, MZ + .02, 8.7, 13, (.62, .58, .52))
    s.slab('Mezzanine floor tiles left', shell, -16, -10.6, MZ, MZ + .02, -18, 8.7, (.62, .58, .52))
    s.slab('Mezzanine floor tiles right', shell, 10.6, 16, MZ, MZ + .02, -18, 8.7, (.62, .58, .52))
    # Fascia band (teal) and the glass balustrade: a steel rail, posts and a smoky glass panel.
    def balustrade(x0, x1, z0, z1):
        s.slab('Mezzanine fascia', shell, x0, x1, MZ - .62, MZ - .4, z0, z1, TEAL)
        horizontal = abs(x1 - x0) > abs(z1 - z0)
        n = int((abs(x1 - x0) if horizontal else abs(z1 - z0)) / 1.6)
        s.slab('Handrail', shell, x0, x1, MZ + 1.02, MZ + 1.1, z0, z1, CHROME, metallic=.8, rough=.3)
        s.slab('Glass', shell, x0, x1, MZ + .08, MZ + .95, z0 + .02, z1 - .02, (.55, .7, .72), rough=.1, metallic=.3)
        for i in range(n + 1):
            t = i / n
            x = x0 + (x1 - x0) * t if horizontal else (x0 + x1) / 2
            z = (z0 + z1) / 2 if horizontal else z0 + (z1 - z0) * t
            s.box('Baluster', shell, (x, MZ + .55, z), (.06, 1.1, .06), CHROME, metallic=.8, rough=.3)
    balustrade(-10.6, 10.6, 8.55, 8.7)
    balustrade(-10.75, -10.6, -18, 8.7)
    balustrade(10.6, 10.75, -18, 8.7)
    # Columns under the mezzanine edge.
    for x in (-10.7, 10.7):
        for z in (-15, -9, -3, 3, 8.6):
            s.box('Column', shell, (x, 2.1, z), (.6, 4.2, .6), CREAM, shape='Cylinder')
            s.box('Column foot', shell, (x, .15, z), (.75, .3, .75), TERRA, shape='Cylinder')
    for x in (-5.3, 5.3):
        s.box('Column', shell, (x, 2.1, 8.6), (.6, 4.2, .6), CREAM, shape='Cylinder')
    # Upper-level shop fronts (dark glass, a couple lit, a couple papered over).
    for i, (x0, x1) in enumerate([(-15.5, -11), (-10, -5.5), (-4.5, 4.5), (5.5, 10), (11, 15.5)]):
        s.slab('Upper shopfront', shell, x0, x1, MZ, MZ + 3.0, 12.7, 12.9, (.16, .2, .24) if i % 2 else (.3, .27, .22), rough=.2, metallic=.2)
        s.slab('Upper shop header', shell, x0, x1, MZ + 3.0, MZ + 3.6, 12.6, 12.9, (.92, .9, .86))
    for z0, z1 in [(-17, -11), (-9, -3), (-1, 6)]:
        for side in (-1, 1):
            x = side * 15.95
            s.slab('Upper shopfront', shell, min(x, x - side * .2), max(x, x - side * .2), MZ, MZ + 3, z0, z1, (.18, .22, .26), rough=.2, metallic=.2)

    # ---- escalators: one pair each side, climbing toward the stage to the side mezzanines ------
    def escalator(x0, label):
        g = s.group(label, shell)
        zb, zt = -3.8, 4.5
        run, rise = zt - zb, MZ
        ang = math.degrees(math.atan2(rise, run))
        length = math.hypot(run, rise)
        cz, cy = (zb + zt) / 2, rise / 2
        for lane, dx in enumerate((0.0, 1.15)):
            xc = x0 + dx + .5
            s.box('Escalator truss', g, (xc, cy - .35, cz), (1.0, .7, length + .6), (.55, .56, .6), rot=(-ang, 0, 0), metallic=.6, rough=.4)
            for k in range(22):
                t = (k + .5) / 22
                s.box('Step', g, (xc, rise * t - .02, zb + run * t), (.86, .04, run / 22 + .02), (.25, .25, .27), metallic=.5, rough=.5)
            for side in (-.48, .48):
                s.box('Balustrade glass', g, (xc + side, cy + .55, cz), (.05, .85, length), (.62, .72, .74), rot=(-ang, 0, 0), rough=.1, metallic=.3)
                s.box('Rubber handrail', g, (xc + side, cy + 1.02, cz), (.08, .08, length + .3), DARK, rot=(-ang, 0, 0), rough=.5)
            s.slab('Comb plate (bottom)', g, xc - .5, xc + .5, 0, .06, zb - 1.2, zb, CHROME, metallic=.8, rough=.3)
        s.slab('Top landing', g, x0 - .2, x0 + 2.4, MZ - .4, MZ, zt, 8.7, CEILING)
        s.slab('Top landing tiles', g, x0 - .2, x0 + 2.4, MZ, MZ + .02, zt, 8.7, (.62, .58, .52))
    escalator(-10.55, 'Escalators left')
    escalator(8.1, 'Escalators right')

    # ---- the fountain: drained, kids inside --------------------------------------------------
    FX, FZ, FR = 0.0, -5.0, 3.7
    ftn = s.group('Drained fountain', court)
    pts = octagon(FR, FX, FZ)
    for i in range(8):
        (ax, az), (bx, bz) = pts[i], pts[(i + 1) % 8]
        mx, mz = (ax + bx) / 2, (az + bz) / 2
        seg = math.hypot(bx - ax, bz - az)
        yaw = math.degrees(math.atan2(bx - ax, bz - az))
        s.box('Fountain wall', ftn, (mx, .27, mz), (.42, .54, seg + .36), TERRA, rot=(0, yaw, 0))
        s.box('Fountain lip', ftn, (mx, .57, mz), (.58, .07, seg + .5), CREAM, rot=(0, yaw, 0))
    s.box('Dry basin', ftn, (FX, .04, FZ), (2 * FR * .93, .08, 2 * FR * .93), (.38, .55, .58), rot=(0, 22.5, 0), shape='Cylinder')
    s.box('Water stain', ftn, (FX, .085, FZ), (2 * FR * .8, .01, 2 * FR * .8), (.30, .42, .42), shape='Cylinder', shadows=False)
    s.box('Spout plinth', ftn, (FX, .45, FZ - .6), (.9, .9, .9), CREAM, shape='Cylinder')
    s.box('Spout bowl', ftn, (FX, 1.0, FZ - .6), (1.7, .22, 1.7), TERRA, shape='Cylinder')
    s.box('Spout stem', ftn, (FX, 1.35, FZ - .6), (.25, .55, .25), CHROME, metallic=.8, rough=.3, shape='Cylinder')
    s.box('Spout cap', ftn, (FX, 1.68, FZ - .6), (.45, .12, .45), CHROME, metallic=.8, rough=.3, shape='Sphere')
    for i, (x, z) in enumerate([(-1.6, -6.5), (1.2, -3.6), (-.8, -3.2), (2.1, -6.1), (.4, -7.4)]):
        s.box('Coin', ftn, (x, .09, z), (.03, .005, .03), (.85, .7, .3), metallic=.9, rough=.3, shape='Cylinder', shadows=False)
    s.box('Paper cup in the basin', ftn, (-2.2, .14, -5.8), (.09, .12, .09), (.95, .95, .92), shape='Cylinder')
    model('Directory board legs', court, 'Assets/Venues/StoryFoodCourt/Models/Directory.obj', (-6.2, 1.35, -11.6), 20)
    s.box('Directory frame', court, (-6.2, 1.35, -11.55), (1.32, 1.62, .08), (.15, .17, .2), rot=(0, 20, 0), metallic=.4, rough=.4)
    s.box('Directory post', court, (-6.2, .3, -11.55), (.2, .6, .2), (.15, .17, .2), metallic=.4)

    # ---- stall fronts along the back, under the mezzanine ------------------------------------
    stall_names = ['SignJuice', 'SignGoldenWok', 'SignPretzel', 'SignTaco', 'SignScoop', 'SignHotDog']
    stall_x = [-12.9, -7.8, -2.6, 2.6, 7.8, 12.9]
    stall_light = []
    stall_shutters = []
    for i, (x, sign) in enumerate(zip(stall_x, stall_names)):
        g = s.group(sign.replace('Sign', 'Stall '), stalls)
        w = 4.6
        # Party walls, counter, back wall, the lit menu, the sign on the fascia above.
        s.slab('Party wall', g, x - w / 2 - .25, x - w / 2, 0, MZ - .4, 8.8, 13, CREAM)
        s.slab('Party wall', g, x + w / 2, x + w / 2 + .25, 0, MZ - .4, 8.8, 13, CREAM)
        tint = [(.9, .85, .4), (.85, .2, .15), (.25, .35, .7), (.95, .55, .15), (.95, .6, .75), (.95, .8, .2)][i]
        s.slab('Stall back wall', g, x - w / 2, x + w / 2, 0, MZ - .4, 12.8, 13, tuple(.35 + .55 * c for c in tint))
        s.slab('Counter', g, x - w / 2, x + w / 2, 0, 1.0, 9.0, 9.7, tuple(.25 + .6 * c for c in tint))
        s.slab('Counter top', g, x - w / 2 - .05, x + w / 2 + .05, 1.0, 1.06, 8.92, 9.75, (.85, .85, .82), metallic=.5, rough=.3)
        s.slab('Kick strip', g, x - w / 2, x + w / 2, 0, .15, 8.98, 9.0, CHROME, metallic=.8, rough=.3)
        s.slab('Bulkhead', g, x - w / 2, x + w / 2, 3.45, MZ - .4, 8.75, 9.0, (.94, .92, .88))
        s.prop('Stall sign', g, signs[sign], (x, 3.95, 8.73))
        s.prop('Menu board', g, menus[i % 3], (x, 2.55, 12.75))
        s.slab('Roller box', g, x - w / 2, x + w / 2, 3.25, 3.45, 8.8, 9.0, (.55, .56, .6), metallic=.6, rough=.4)
        if i in (1, 3, 5):
            model('Hot cabinet', g, VENUE + 'FoodStall.obj', (x - 1.1, 1.06, 9.35), 180, .8)
        model('Cup stack', g, 'PaperCup', (x + 1.2, 1.06, 9.3))
        model('Cup stack', g, 'PaperCup', (x + 1.35, 1.06, 9.4))
        s.box('Till', g, (x + .4, 1.2, 9.45), (.4, .26, .32), DARK, rough=.4)
        stall_light.append((x, tint))
        stall_shutters.append(x)
    # The left and right walls: a department store closing, the skate shop, a vending corner.
    dept = s.group('Hartley & Sons (closing)', stalls)
    s.slab('Store front', dept, -16, -15.8, 0, 4.0, -15, -4, (.9, .9, .86))
    s.box('Store sign', dept, (-15.75, 3.95, -9.5), (.04, .8, 3.6), (.96, .95, .92), rot=(0, 0, 0))
    s.prop('Store sign text', dept, signs['SignDept'], (-15.7, 3.95, -9.5), -90)
    for j, z in enumerate((-13.8, -12.2, -6.8, -5.2)):
        s.prop('Closing poster', dept, poster, (-15.74, 1.6, z), -90)
    s.slab('Store doors (dark)', dept, -15.82, -15.78, 0, 3.0, -11.0, -8.0, (.08, .1, .12), rough=.15, metallic=.3)
    s.prop('Last weekend banner', dept, last_day, (-15.72, 2.4, -9.5), -90)
    skate = s.group('Drop-In Skate (the shop throwing the matinee)', stalls)
    s.slab('Shop front', skate, 15.8, 16, 0, 4.0, -12, -2, (.1, .1, .11))
    s.prop('Shop sign', skate, signs['SignSkate'], (15.72, 3.95, -7), 90)
    s.slab('Shop window', skate, 15.76, 15.8, .4, 3.1, -11.4, -8.0, (.25, .5, .3), rough=.1, metallic=.2,
           emissive=(.25, .55, .35), emissive_intensity=.4)
    for k in range(7):
        z = -6.8 + k * .62
        col = [(.9, .2, .5), (.2, .8, .3), (.95, .8, .1), (.2, .4, .9), (.95, .45, .1), (.6, .2, .8), (.1, .8, .8)][k]
        s.box('Deck on the wall', skate, (15.7, 1.9 + .18 * (k % 2), z), (.04, 1.0, .22), col, rough=.6)
    model('Neon cactus', skate, 'NeonCactus', (15.4, 1.4, -10.5), -90)
    s.prop('No skating', skate, no_skate, (15.72, 1.6, -1.4), 90)
    # Vending corner and the arcade.
    model('Vending machine', court, 'VendingMachine', (-15.2, 0, -1.5), 90)
    model('Vending machine', court, 'VendingMachine', (-15.2, 0, .1), 90)
    model('Arcade cabinet', court, 'Arcade', (15.2, 0, -14.2), -90)
    model('Arcade cabinet', court, 'Arcade', (15.2, 0, -13.2), -90)
    model('Table football', court, 'TableFootball', (13.4, 0, -16.5), 10)

    # ---- the stage: three cafeteria tables for the kit, the band on the floor ------------------
    riser = s.group('Riser of three cafeteria tables', stage)
    TOP = .76
    for i, x in enumerate((-1.27, 0.0, 1.27)):
        s.slab('Cafeteria table top', riser, x - .62, x + .62, TOP - .05, TOP, 3.95, 7.15, LAMINATE, rough=.35)
        s.slab('Table edge trim', riser, x - .63, x + .63, TOP - .07, TOP - .04, 3.94, 7.16, CHROME, metallic=.8, rough=.3)
        for dz in (4.4, 6.7):
            s.box('Table pedestal', riser, (x, (TOP - .07) / 2, dz), (.1, TOP - .07, .1), CHROME, metallic=.8, rough=.3, shape='Cylinder')
            s.box('Table foot', riser, (x, .02, dz), (.9, .04, .1), CHROME, metallic=.8, rough=.3)
    for x in (-.635, .635):
        s.slab('Gaffer tape over the seam', riser, x - .05, x + .05, TOP, TOP + .005, 3.96, 7.14, (.13, .13, .14), shadows=False)
    s.slab('Gaffer tape across the front', riser, -1.9, 1.9, TOP, TOP + .005, 4.05, 4.15, (.13, .13, .14), shadows=False)
    model('Drum rug', riser, VENUE + 'DrumRug.obj', (0, TOP + .006, 5.55), 0, .95)
    s.box('Cafeteria tray', riser, (-1.6, TOP + .02, 6.85), (.45, .03, .34), (.75, .25, .15), rough=.4)
    model('Drink on the tray', riser, 'PaperCup', (-1.65, TOP + .04, 6.82))
    model('Drink on the tray', riser, 'PaperCup', (-1.5, TOP + .04, 6.9))
    s.box('Napkin dispenser', riser, (1.75, TOP + .09, 6.9), (.16, .18, .12), CHROME, metallic=.8, rough=.3)
    s.box('Setlist taped down', riser, (1.4, TOP + .004, 4.3), (.21, .003, .3), (.97, .97, .94), shadows=False, rot=(0, 12, 0))
    s.box('Towel', riser, (-1.55, TOP + .02, 4.35), (.4, .02, .3), (.2, .55, .8), rough=.9)
    model('Stick bag road case', riser, VENUE + 'RoadCase.obj', (1.55, TOP, 7.0), 90, .55)
    model('Spare stool', stage, 'StackChair', (-2.3, 0, 7.2), 30)
    # Amps, PA, wedges for the floor-level band.
    model('Guitar cab', stage, VENUE + 'GuitarCab.obj', (-3.7, 0, 5.0), 180)
    model('Guitar head', stage, VENUE + 'AmpHead.obj', (-3.7, .75, 5.0), 180)
    model('Bass cab', stage, VENUE + 'GuitarCab.obj', (3.7, 0, 5.0), 180, 1.15)
    model('Bass head', stage, VENUE + 'AmpHead.obj', (3.7, .86, 5.0), 180)
    for x in (-5.8, 5.8):
        model('PA on a road case', stage, VENUE + 'RoadCase.obj', (x, 0, 2.2), 0)
        model('PA speaker', stage, VENUE + 'Speaker.obj', (x, .85, 2.2), 180, 1.1)
    for x, yaw in ((-3.0, 15), (0, 0), (3.0, -15)):
        model('Wedge', stage, VENUE + 'Wedge.obj', (x, 0, 1.1), 180 + yaw)
    model('Power distro', stage, VENUE + 'PowerDistro.obj', (5.2, 0, 6.8), -90, .8)
    model('Cable coil', stage, VENUE + 'CableCoil.obj', (-1.5, 0, 3.3))
    model('Cable run', stage, VENUE + 'CableA.obj', (1.6, 0, 3.0), 70)
    model('Cable run', stage, VENUE + 'CableB.obj', (-2.4, 0, 2.6), -20)
    # Lighting trees either side of the stage (the rig's washes and blinders hang on them).
    for x in (-5.2, 5.2):
        s.box('Lighting stand', stage, (x, 1.75, 3.4), (.06, 3.5, .06), DARK, metallic=.5, shape='Cylinder')
        s.box('Lighting stand T-bar', stage, (x, 3.45, 3.4), (1.6, .06, .06), DARK, metallic=.5)
        s.box('Lighting stand foot', stage, (x, .05, 3.4), (.9, .06, .9), DARK, metallic=.5, rot=(0, 45, 0))
        for dx in (-.6, 0, .6):
            s.box('PAR can', stage, (x + dx, 3.3, 3.35), (.22, .22, .3), DARK, rot=(25, 0, 0), metallic=.5, shape='Cylinder')

    # ---- the pushed-back food court: tables, chairs, bins, planters ---------------------------
    for i, (x, z, yaw) in enumerate([(-13.2, -16.5, 8), (-13.0, -12.2, -12), (13.0, -11.4, 20), (12.6, -19.5, -6),
                                     (-12.8, -20.0, 33), (-13.4, -7.0, 0), (13.4, -5.5, 15)]):
        model('Food court table', court, 'CafeTable', (x, 0, z), yaw)
        for k in range(4):
            a = math.radians(yaw + 90 * k)
            model('Food court chair', court, 'CafeChair', (x + .95 * math.sin(a), 0, z + .95 * math.cos(a)), yaw + 90 * k + 180)
    for i, (x, z) in enumerate([(-14.6, 4.0), (14.6, 4.2), (-14.8, -19.2), (14.7, -9.4)]):
        for k in range(5):
            model('Stacked chair', court, 'StackChair', (x, .11 * k, z), 15 + 2 * k)
    for x, z in ((-9.6, -16.8), (9.6, -16.8), (-9.4, -9.0), (9.4, -9.0)):
        model('Mall planter', court, 'Planter', (x, 0, z), 0)
    for x, z in ((-14.9, 7.8), (14.9, 7.8)):
        model('Potted palm', court, 'PottedPalm', (x, 0, z), 0)
    for x, z in ((-10.0, -12.8), (10.0, -12.8), (-7.2, 6.8), (7.0, 7.0)):
        model('Bin', court, 'TrashBin', (x, 0, z), 180)
    model('Wet floor sign', court, 'WetFloor', (-8.6, 0, 1.6), 30)
    model('Janitor cart', court, 'JanitorCart', (-14.6, 0, -3.4), 90)
    for x, z in ((-10.65, 5.5), (10.65, -7.5)):
        model('Security camera', shell, 'SecurityCam', (x, 3.75, z), 180)

    # ---- the closing-down dressing up high ---------------------------------------------------
    s.prop('Skate shop banner', dress, skate_banner, (0, MZ + .25, 8.5))
    for x in (-7.8, 7.8):
        s.prop('Thank you banner', dress, thanks, (x, MZ + .55, 8.5))
    for z in (-13.5, -1.5):
        s.prop('Everything must go (left)', dress, must_go, (-10.52, MZ - 1.5, z), -90)
        s.prop('Everything must go (right)', dress, must_go, (10.52, MZ - 1.5, z), 90)
    s.prop('Everything must go (over the doors)', dress, must_go2, (0, 6.2, -22.4), 180)
    for x in (-5.2, 5.2):
        s.box('Hanging sign wire', dress, (x - 1.6, 8.8, 0), (.01, 2.4, .01), DARK, shadows=False)
        s.box('Hanging sign wire', dress, (x + 1.6, 8.8, 0), (.01, 2.4, .01), DARK, shadows=False)
    s.prop('FOOD COURT hanging sign', dress, signs['SignFoodCourt'], (-5.2, 7.3, 0), 0)
    s.box('Hanging sign back', dress, (-5.2, 7.3, .03), (4.3, 1.12, .05), (.9, .9, .9))
    s.prop('FOOD COURT hanging sign', dress, signs['SignFoodCourt'], (5.2, 7.3, 0), 0)
    s.box('Hanging sign back', dress, (5.2, 7.3, .03), (4.3, 1.12, .05), (.9, .9, .9))
    for x0, x1, y, z in [(-10.6, 10.6, MZ + 1.1, 8.48)]:
        for k in range(7):
            model('Bunting', dress, 'Bunting', (x0 + 1.5 + k * 3.0, y - .65, z), 0)

    # ---- mall lights: fluorescent troffers; two banks go dark as the set goes ---------------
    def troffer(parent, pos, length=2.4, rot=0):
        s.box('Fluorescent tube', parent, pos, (length if rot == 0 else .32, .05, .32 if rot == 0 else length), FLUO,
              emissive=FLUO, emissive_intensity=2.2, shadows=False)
    bank_a = sg('Mall lights, bank A (off once the guard has signed)', lamps, 'guard_signed', False, 2.5, (0, 9.0, 0))
    bank_b = sg('Mall lights, bank B (off when the shutters come down)', lamps, 'shutters_down', False, 3.0, (0, 9.0, 0))
    for i, z in enumerate((-19.5, -15.5, -11.5, -7.5, -3.5, .5, 4.5, 11)):
        for x in (-13.3, 13.3):
            bank = bank_a if (i % 2 == 0) else bank_b
            troffer(bank, (x, MZ - .43, z) if z < 8.7 else (x, MZ - .43, z))
    for x in (-10.5, -5.2, 0, 5.2, 10.5):
        troffer(bank_b if x != 0 else bank_a, (x, MZ - .43, 11.0))
    for x, z in ((-12, -18), (0, -20.5), (12, -18)):
        troffer(bank_a, (x, 9.95, z))
    # The light those tubes give: plain points (they dim with their bank).
    for i, (pos, bank) in enumerate([((-13, 4.0, -12), bank_a), ((13, 4.0, -12), bank_b), ((-13, 4.0, 0), bank_b), ((13, 4.0, 0), bank_a),
                                     ((-6, 4.2, 11), bank_a), ((6, 4.2, 11), bank_b), ((0, 8.5, -18), bank_a), ((-6, 8.0, -8), bank_b),
                                     ((6, 8.0, -8), bank_a)]):
        s.light(f'Fluorescent fill {i + 1}', bank, pos, 'Point', (.88, .95, 1.0), 420 if pos[1] > 6 else 200, 15)

    # Stall interiors: warm lights inside, off when the shutters come down.
    stall_on = sg('Stalls open (until the shutters come down)', stalls, 'shutters_down', False, 1.5, (0, 3.3, 9))
    for x, tint in stall_light:
        s.light('Stall lamp', stall_on, (x, 3.0, 11.0), 'Point', (1.0, .86, .66), 110, 7)
        s.box('Stall downlight', stall_on, (x, MZ - .41, 11.0), (1.6, .03, .3), (1, .95, .85), emissive=(1, .92, .78),
              emissive_intensity=2.0, shadows=False)

    # Daylight: the sun through the skylight; at shutters_down it goes and dusk comes in.
    day = sg('Afternoon through the skylight', lamps, 'shutters_down', False, 4.0, (0, 10.8, -4))
    s.light('Sun through the skylight', day, (0, 20, -10), 'Directional', (1.0, .95, .86), 4.0, rot=(62, 18, 0), shadows=True)
    for z in [sz0 + (k + .5) * (sz1 - sz0) / 8 for k in range(8)]:
        s.slab('Skylight pane (day)', day, sx0 + .1, sx1 - .1, 11.42, 11.46, z - 1.2, z + 1.2, (.8, .9, 1.0),
               emissive=(.78, .88, 1.0), emissive_intensity=3.0, shadows=False)
    s.light('Sky fill', day, (0, 9.5, -4), 'Point', (.75, .85, 1.0), 900, 26)
    dusk = sg('Dusk through the skylight', lamps, 'shutters_down', True, 4.0, (0, 10.8, -4))
    for k, z in enumerate([sz0 + (k + .5) * (sz1 - sz0) / 8 for k in range(8)]):
        col = [(.95, .45, .35), (.85, .38, .45), (.7, .32, .5), (.5, .28, .55), (.4, .25, .55), (.32, .22, .5), (.26, .2, .45), (.22, .18, .4)][k]
        s.slab('Skylight pane (dusk)', dusk, sx0 + .1, sx1 - .1, 11.42, 11.46, z - 1.2, z + 1.2, col,
               emissive=col, emissive_intensity=1.1, shadows=False)
    s.light('Dusk glow', dusk, (0, 9.5, -6), 'Point', (.85, .45, .5), 160, 20)
    # Party lights: the skate shop's fairy lights on the balustrade and coloured lamps on the rim.
    party = sg('Party lights (once the mall lights are off)', lamps, 'shutters_down', True, 2.0, (0, MZ + 1, 0))
    cols = [(1, .3, .5), (.3, .8, 1), (1, .8, .3), (.5, 1, .4)]
    for k in range(40):
        t = k / 39
        s.box('Fairy light', party, (-10.4 + 20.8 * t, MZ + .98 - .18 * math.sin(math.pi * ((t * 8) % 1)), 8.45), (.07, .07, .07),
              cols[k % 4], emissive=cols[k % 4], emissive_intensity=3.0, shadows=False, shape='Sphere')
    for side in (-1, 1):
        for k in range(26):
            z = -17.5 + k * 1.0
            s.box('Fairy light', party, (side * 10.5, MZ + .98 - .16 * math.sin(math.pi * ((k / 3) % 1)), z), (.07, .07, .07),
                  cols[(k + side) % 4], emissive=cols[(k + side) % 4], emissive_intensity=3.0, shadows=False, shape='Sphere')
    for i, (pos, col) in enumerate([((-8, 5.4, -6), (1, .25, .55)), ((8, 5.4, -6), (.25, .7, 1)), ((0, 5.6, 8.2), (1, .7, .25)),
                                    ((-8, 5.4, 4), (.45, 1, .4)), ((8, 5.4, 4), (1, .3, .6))]):
        s.light(f'Party lamp {i + 1}', party, pos, 'Point', col, 110, 12)

    # ---- story beats around the fountain -----------------------------------------------------
    HX, HZ = 3.32, -4.35   # the head's spot on the fountain lip (right face of the octagon)
    lip = .605
    head_yaw = -12.0

    def head(parent, kind, pos, yaw, tilt=-11.0):
        g = s.entity(f'Kick head ({kind})', parent, pos, (tilt, yaw, 0))
        s.prop('Head film', g, heads[kind], (0, .02, 0))
        s.box('Head hoop', g, (0, .4, .025), (.87, .04, .87), DARK, shape='Cylinder', rot=(90, 0, 0), metallic=.6, rough=.35)
        return g

    # one_signature: the head (one signature), the kid beside it, SIGN THE HEAD! on the spout.
    on_ftn = sg('Head on the fountain (until it goes to the riser)', story, 'head_on_riser', False, .9, (HX, lip, HZ))
    sig1 = sg('one_signature: the spare head on the fountain lip', on_ftn, 'one_signature', True, 1.0, (HX, lip, HZ))
    stage_a = sg('Head, one signature (until the cap is drawn)', sig1, 'guard_drawn', False, .5, (HX, lip, HZ))
    head(stage_a, 'A', (HX, lip, HZ), head_yaw)
    drawn = sg('Head with the cap (guard_drawn)', sig1, 'guard_drawn', True, .5, (HX, lip, HZ))
    stage_b = sg('Head with the cap, not yet the moustache', drawn, 'guard_signed', False, .5, (HX, lip, HZ))
    head(stage_b, 'B', (HX, lip, HZ), head_yaw)
    signed = sg('Head with the moustache (guard_signed)', drawn, 'guard_signed', True, .5, (HX, lip, HZ))
    stage_c = sg('Head with the moustache, before the staff sign', signed, 'shutters_down', False, .5, (HX, lip, HZ))
    head(stage_c, 'C', (HX, lip, HZ), head_yaw)
    stage_d = sg('Head nearly black (shutters_down)', signed, 'shutters_down', True, .5, (HX, lip, HZ))
    head(stage_d, 'D', (HX, lip, HZ), head_yaw)

    sign_grp = sg('SIGN THE HEAD! on the spout', story, 'one_signature', True, 1.0, (FX, 1.0, FZ - .6))
    s.prop('Cardboard sign', sign_grp, sign_head, (FX + .1, 1.5, FZ - 1.08), -8)
    model('Marker cup', sign_grp, 'PaperCup', (HX - .05, lip - .03, HZ + .35))

    kid_here = sg('The kid beside the head (until the finale)', story, 'head_on_riser', False, .8, (4.15, 0, -4.0))
    kid_in = sg('one_signature: the kid in the shop hoodie claims the spot', kid_here, 'one_signature', True, .8, (4.15, 0, -4.0))
    people.person(s, kid_in, 'Skate-shop kid', kid_base, 'Bounce', (4.15, 0, -4.0), 200, .5)

    # guard_drawn: two boards, a second skater, the guard behind them (leaving his desk).
    boards = sg('guard_drawn: two boards beside the head', story, 'guard_drawn', True, .8, (3.75, 0, -5.4))
    for k, (z, col) in enumerate(((-5.25, (.9, .2, .45)), (-5.7, (.2, .7, .9)))):
        b = s.entity('Skateboard', boards, (3.88, .42, z), (0, 90, 14))
        s.box('Deck', b, (0, 0, 0), (.21, .8, .02), col, rough=.6)
        s.box('Grip', b, (0, 0, -.012), (.2, .78, .005), DARK, rough=.9, shadows=False)
        for wy in (-.28, .28):
            s.box('Wheels', b, (0, wy, .04), (.2, .05, .05), (.95, .92, .8), shape='Cylinder', rot=(0, 0, 90))
    friend = sg('guard_drawn: the second skater', story, 'guard_drawn', True, .8, (4.75, 0, -5.0))
    people.person(s, friend, 'Second skater', 'Son_01', 'Bounce', (4.75, 0, -5.0), 215, .52)
    behind = sg('guard_drawn: the guard behind the skaters', story, 'guard_drawn', True, .8, (4.75, 0, -2.75))
    behind_only = sg('... until he signs and moves over', behind, 'guard_signed', False, .6, (4.75, 0, -2.75))
    _, gh, _ = people.person(s, behind_only, 'Mall guard (watching)', guard_base, 'Guard', (4.75, 0, -2.75), 195)
    people.cap(s, gh)
    # The security desk he leaves.
    desk = s.group('Security desk', court)
    s.slab('Desk', desk, 12.0, 13.6, 0, 1.05, -2.2, -.9, (.2, .24, .32))
    s.slab('Desk top', desk, 11.95, 13.65, 1.05, 1.1, -2.25, -.85, (.8, .8, .78))
    s.prop('Desk sign', desk, security, (12.8, .7, -2.24), 0)
    s.box('Desk monitor', desk, (12.9, 1.3, -1.3), (.45, .32, .08), DARK)
    s.box('Desk monitor glow', desk, (12.9, 1.3, -1.35), (.4, .27, .01), (.3, .6, .7), emissive=(.3, .7, .8), emissive_intensity=1.2, shadows=False)
    at_desk = sg('The guard at his desk (until he comes over)', desk, 'guard_drawn', False, .8, (12.8, 0, -.4))
    _, gh, _ = people.person(s, at_desk, 'Mall guard (at the desk)', guard_base, 'Idle', (12.8, 0, -.4), 182)
    people.cap(s, gh)

    # guard_signed: the guard beside the kid, clapping; balloons on the spout.
    clap = sg('guard_signed: the guard claps beside the kid', story, 'guard_signed', True, .8, (4.8, 0, -3.35))
    _, gh, _ = people.person(s, clap, 'Mall guard (clapping)', guard_base, 'Clap', (4.8, 0, -3.35), 205)
    people.cap(s, gh)
    balloons = sg('guard_signed: balloons from the card shop on the spout', story, 'guard_signed', True, 1.2, (FX, 1.75, FZ - .6))
    for k, (dx, dz, sc, yaw) in enumerate([(0, 0, 1.0, 0), (.3, .15, .95, 40), (-.28, .1, 1.05, 80), (.1, -.3, .9, 120), (-.15, .3, 1.1, 160)]):
        model('Balloon', balloons, 'Balloon', (FX + dx, 1.72, FZ - .6 + dz), yaw, sc * 1.25)

    # shutters_down: the shutters (half -> full), the staff on the rim.
    half = sg('Shutters half down (until the last ones roll)', stalls, 'shutters_down', False, 1.2, (0, 3.3, 8.9))
    full = sg('shutters_down: every shutter rolled down', stalls, 'shutters_down', True, 1.6, (0, 3.3, 8.9))
    for i, x in enumerate(stall_shutters):
        s.prop('Shutter (half)', half, shut_half, (x, 3.3 - .725, 8.86))
        s.prop('Shutter (down)', full, shut_full, (x, 1.7, 8.86))
        if i in (1, 4):
            s.prop('Taped note', full, shut_note, (x + .9, 1.5, 8.84))
    skate_shut = sg('shutters_down: the skate shop shutter', stalls, 'shutters_down', True, 1.6, (15.7, 3.3, -9.7))
    s.prop('Shutter (skate shop)', skate_shut, shut_full, (15.68, 1.7, -9.7), 90, 1.0)
    staff = sg('shutters_down: staff in name tags fill the fountain rim', story, 'shutters_down', True, 1.2, (FX, .6, FZ))
    crew = [('Golden Wok cook', 'Mother_01', (.85, .2, .15)), ('Pretzel Twist', 'Son_01', (.25, .35, .7)),
            ('Taco Loco', 'Daughter_01', (.95, .55, .15)), ('Big Scoop', 'Mother_02', (.95, .6, .75)),
            ('Hot Dog Hut', 'Rigged', (.95, .8, .2)), ('Juice Junction', 'SchoolBoy_01', (.3, .75, .3)),
            ('Golden Wok owner', 'ShopKeeper_01', (.85, .2, .15)), ('Pretzel Twist manager', 'Mother_01', (.25, .35, .7))]
    for k, (who, body, col) in enumerate(crew):
        a = math.radians(122 + k * 21.5)   # the rim's back and left, facing the stage
        x, z = FX + (FR - .02) * math.cos(a), FZ + (FR - .02) * math.sin(a)
        x, z = (x, z) if k < 6 else (FX - FR * .97 + .0, FZ + (k - 6.5) * 1.6 - 1.2)
        _, hd, sp = people.person(s, staff, f'{who} (name tag)', body, 'Clap' if k % 3 == 0 else 'Bounce', (x, lip, z),
                                  0 if k < 6 else 20, .55 + .07 * k)
        people.name_tag(s, sp)
        people.visor(s, hd, col)

    # head_on_riser: the head on the riser; the kid on the rim, arms up.
    riser_head = sg('head_on_riser: the signed head stands on the riser', story, 'head_on_riser', True, 1.0, (1.45, TOP, 4.25))
    head(riser_head, 'D', (1.45, TOP + .005, 4.25), -14, -9)
    kid_up = sg('head_on_riser: the kid on the rim, both arms up', story, 'head_on_riser', True, .8, (3.15, lip, -3.2))
    people.person(s, kid_up, 'Skate-shop kid (arms up)', kid_base, 'ArmsUp', (3.15, lip, -3.2), 196)

    # ---- the band rig (show lights; never under a story group) ---------------------------------
    def spot(name, pos, to, col, power, reach, inner, outer, kind, group=0):
        s.light(name, rig, pos, 'Spot', col, power, reach, rot=look_rotation(pos, to), inner=inner, outer=outer, show=kind, group=group)
    wash_cols = [(1, .45, .3), (.35, .55, 1), (1, .3, .65)]
    for side in (-1, 1):
        for k, dx in enumerate((-.6, 0, .6)):
            p = (side * 5.2 + dx, 3.3, 3.35)
            spot(f'Tree PAR {side:+d}/{k}', p, (side * 1.2 + dx * .5, 1.2, 4.6 - k * .9), wash_cols[k], 900, 14, 18, 38, 'Wash', k)
    for side in (-1, 1):
        spot(f'Back wash {side:+d}', (side * 4, MZ + 1.3, 8.4), (side * .8, 1.0, 2.6), (.6, .5, 1), 1100, 14, 20, 42, 'Wash', 0)
        spot(f'Rail wash {side:+d}', (side * 9.5, MZ + 1.3, -4), (side * 1.5, 1.2, 3.5), (1, .7, .5), 1300, 20, 16, 30, 'Wash', 1)
    for k, x in enumerate((-2.6, -1.0, 1.0, 2.6)):
        spot(f'Floor beam {k + 1}', (x, .25, 7.7), (x * 3.2, 9.5, -6 + abs(x)), (.6, .8, 1) if k % 2 else (1, .4, .8), 2200, 22, 4, 9, 'Beam', k % 2)
    follow = [((0, 1.9, 6.4), (-11.5, MZ + 2.0, -7.5)), ((0, 1.6, 2.2), (11.5, MZ + 2.0, -7.5)),
              ((-3.3, 1.6, 3.2), (-11.5, MZ + 2.0, -1)), ((3.3, 1.6, 3.4), (11.5, MZ + 2.0, -1))]
    for k, (to, at) in enumerate(follow):
        spot(f'Follow spot from the mezzanine {k + 1}', at, to, (1, .93, .82), 2600, 24, 5, 10, 'Spot', k)
    for side in (-1, 1):
        spot(f'Blinder {side:+d}', (side * 5.2, 3.6, 3.3), (side * 4, 1.4, -8), (1, .82, .6), 900, 18, 22, 48, 'Blinder', 0 if side < 0 else 1)
        s.light(f'Strobe {side:+d}', rig, (side * 9.0, MZ + 1.5, 8.3), 'Point', (.95, .95, 1), 900, 22, show='Strobe', group=0 if side < 0 else 1)
    s.light('House fill', rig, (0, 7.5, -12), 'Point', (1, .95, .88), 420, 24, show='Static')
    s.light('Stage fill', rig, (0, 6.5, -1.5), 'Point', (1, .9, .8), 380, 14, show='Static')

    # ---- markers -----------------------------------------------------------------------------
    s.info(marks, 'Food Court Farewell Show', 'Drumsmith', outdoor=False, room_back=-22.5, room_ceiling=10.0,
           half_width=16.0, desk_z=-18.5, ambient=(.2, .19, .18), fog_color=(.05, .045, .04), haze=.55)
    s.spot(marks, 'Drummer', (0, TOP, 6.45))
    s.spot(marks, 'Guitar', (-3.1, 0, 3.0), 8)
    s.spot(marks, 'Bass', (3.1, 0, 3.15), -8)
    s.spot(marks, 'Vocals', (0, 0, 2.2))
    crowd = s.group('Crowd', marks)
    s.crowd('In the fountain', crowd, (-.3, .09, -4.1), 4.6, 2.6, 14, figures='Posed')
    s.crowd('Fountain, far half', crowd, (-.6, .09, -6.9), 4.0, 2.0, 9, figures='Posed')
    s.crowd('Front, against the wedges', crowd, (-1.6, 0, -.25), 8.6, 2.1, 22, figures='Posed', )
    s.crowd('Front left', crowd, (-6.2, 0, -4.6), 4.6, 6.4, 28, figures='Posed')
    s.crowd('Front right', crowd, (7.0, 0, -4.2), 3.6, 5.6, 18, figures='Posed')
    s.crowd('Behind the fountain', crowd, (0, 0, -12.5), 17, 6.6, 110, .7)
    s.crowd('Back by the doors', crowd, (0, 0, -17.6), 15, 3.2, 40, .8)
    s.crowd('Mezzanine left rail', crowd, (-12.0, MZ, -6.5), 20, 2.2, 34, .6, 90)
    s.crowd('Mezzanine right rail', crowd, (12.0, MZ, -6.5), 20, 2.2, 34, .6, -90)
    s.crowd('Mezzanine back rail', crowd, (0, MZ, 9.6), 14, 1.4, 22, .5, 180)
    s.crowd('On the escalator landing', crowd, (-9.4, MZ, 6.3), 2.0, 2.4, 6, .6, 120)
    s.crowd('Kids on the escalator landing', crowd, (9.3, MZ, 6.3), 2.0, 2.4, 6, .6, -120)

    cams = s.group('Cameras', marks)
    for tag, kind, eye, aim, fov in [
        ('food-court-wide', 'Wide', (0, 5.0, -18.6), (0, 2.0, 5.0), 56),
        ('skylight-crane', 'Crane', (-9.0, 8.6, -11.5), (.5, 1.4, 3.5), 56),
        ('desk', 'Desk', (2.6, 2.7, -19.5), (0, 2.0, 5.0), 30),
        ('fountain-lip', 'Custom', (3.0, 1.9, -8.8), (3.6, 1.0, -4.2), 48),
        ('head-on-the-riser', 'Custom', (3.7, 1.85, 1.5), (.9, 1.25, 4.6), 50),
        ('sticks', 'Close', (1.7, 2.5, 3.7), (0, 1.75, 6.2), 48),
        ('mezzanine-rail', 'Custom', (12.4, MZ + 1.8, -3.5), (0, 1.4, 3.5), 54),
        ('escalator-ride', 'Custom', (-9.4, 3.1, .4), (-1.0, 1.4, 3.6), 56),
        ('over-the-kit', 'Custom', (.6, 2.7, 8.4), (1.5, .8, -6.0), 62),
        ('security-desk', 'Custom', (9.6, 1.7, -5.6), (4.3, 1.1, -3.6), 50),
    ]:
        s.camera_spot(tag, cams, eye, aim, kind, fov, tag)
    for i, (eye, aim, fov) in enumerate([
            ((-1.2, 1.65, -21.6), (-.6, 1.8, -12.0), 64), ((-2.6, 1.7, -19.8), (-.5, 1.8, -8.0), 62),
            ((-4.6, 1.72, -17.0), (-1.0, 1.6, -5.0), 60), ((-6.6, 1.75, -13.6), (-1.0, 1.5, -2.0), 58),
            ((-7.6, 1.8, -10.0), (-.4, 1.7, 3.0), 56), ((-7.9, 1.85, -7.2), (0, 1.9, 5.0), 54)]):
        s.camera_spot(f'Arrival {i + 1:02}', cams, eye, aim, 'Custom', fov, f'arrival/{i + 1:02}')
    return s


def main():
    os.makedirs(FOLDER, exist_ok=True)
    scene = build()
    scene.write(os.path.join(FOLDER, ID + '.lvl'))
    preview = 'Preview.jpg' if os.path.exists(os.path.join(FOLDER, 'Preview.jpg')) else None
    write_venue_json(FOLDER, 'Food Court Farewell Show', ID + '.lvl', preview=preview, ambience='Assets/Sounds/crowd.mp3')
    print(f'{len(scene.entities)} entities in {FOLDER}')


if __name__ == '__main__':
    main()
