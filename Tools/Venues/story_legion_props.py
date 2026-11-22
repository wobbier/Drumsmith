"""StoryLegion's furniture: the builders that add a prop to a Mesh at the mesh's current transform
(push an offset and a yaw first). Each prop's origin is on the floor; "front" is noted per prop."""
import math
import random


def folding_chair(m, folded_toast=False):
    """Beige steel folding chair, brown vinyl seat. Origin under the seat; the sitter faces +z."""
    for x in (-.2, .2):
        m.tube((x, 0, .2), (x, .45, .15), .012, 'chair_frame', 5)
        m.tube((x, 0, -.22), (x, .9, -.19), .012, 'chair_frame', 5)
        m.tube((x, .45, .17), (x, .45, -.2), .011, 'chair_frame', 4)
    m.tube((-.2, .12, -.21), (.2, .12, -.21), .009, 'chair_frame', 4)
    m.tube((-.2, .12, .19), (.2, .12, .19), .009, 'chair_frame', 4)
    m.box((0, .47, -.01), (.42, .035, .4), 'chair_vinyl')
    m.push((0, .76, -.2), 0, -8)
    m.box((0, 0, 0), (.42, .18, .025), 'chair_vinyl')
    m.pop()
    if folded_toast:
        m.push((.05, .495, .02), 25)
        m.box((0, 0, 0), (.15, .012, .1), 'paper')
        m.pop()


def round_table(m, seed, settings=6):
    """A 1.6 m round table in a floor-length white cloth, with cups, plates, a bud vase."""
    rnd = random.Random(seed)
    m.cyl((0, .0, 0), .82, .74, 'cloth', 14, top='cloth', radius_top=.8)
    m.cyl((0, .74, 0), .84, .025, 'cloth_shade', 14, top='cloth')
    top = .765
    # bud vase with a carnation
    m.cyl((0, top, 0), .035, .16, 'glass', 6)
    m.tube((0, top + .1, 0), (.02, top + .3, .01), .004, 'leaf', 4)
    m.sphere((.02, top + .31, .01), .035, 'flower_red' if seed % 3 else 'flower_white', 6, 3)
    for i in range(settings):
        a = 2 * math.pi * (i + rnd.random() * .3) / settings
        r = .58
        x, z = math.sin(a) * r, math.cos(a) * r
        if rnd.random() < .8:
            m.cyl((x, top, z), .1, .012, 'plate', 10)
            if rnd.random() < .5:
                m.box((x + .02, top + .025, z), (.07, .03, .05), rnd.choice(['cake', 'lemon', 'pink_icing']))
        kind = rnd.random()
        cx, cz = math.sin(a + .35) * (r - .12), math.cos(a + .35) * (r - .12)
        if kind < .45:
            m.cyl((cx, top, cz), .07, .008, 'mug', 8)
            m.cyl((cx, top + .008, cz), .04, .07, 'mug', 8, top='coffee')
        elif kind < .75:
            m.cyl((cx, top, cz), .033, .12, 'glass', 6, top='beer')
        else:
            m.cyl((cx, top, cz), .028, .01, 'glass', 6)
            m.cyl((cx, top + .01, cz), .006, .08, 'glass', 4)
            m.cyl((cx, top + .09, cz), .032, .07, 'wine', 6)
        if rnd.random() < .5:
            m.box((x * .7, top + .004, z * .7), (.12, .008, .12), 'napkin', yaw=rnd.random() * 90)


def upright_piano(m):
    """A black upright, keyboard facing -z, with its bench. Origin at the floor under the case."""
    m.slab(-.76, .76, .06, 1.26, -.05, .3, 'piano')                  # case
    m.slab(-.79, .79, 1.26, 1.3, -.09, .32, 'piano_edge')             # lid
    m.slab(-.74, .74, .88, 1.24, -.1, -.05, 'piano')                  # upper panel
    m.slab(-.6, .6, .98, 1.16, -.105, -.1, 'piano_edge')              # music desk
    m.slab(-.76, .76, .64, .72, -.36, -.05, 'piano')                  # key bed
    m.slab(-.72, .72, .72, .745, -.34, -.12, 'ivory')                 # white keys
    for i in range(36):
        x = -.7 + i * .04
        if i % 7 in (0, 1, 3, 4, 5):
            m.box((x + .02, .755, -.2), (.018, .02, .12), 'key_black')
    m.slab(-.76, .76, .745, .82, -.11, -.05, 'piano')                 # fallboard
    for x in (-.76, .7):
        m.slab(x, x + .06, .0, .82, -.42, -.05, 'piano')              # cheeks
    for x in (-.7, .7):
        m.slab(x - .04, x + .04, 0, .64, -.4, -.33, 'piano')          # front legs
    m.slab(-.76, .76, 0, .06, -.42, .3, 'piano_edge')                 # plinth
    for x in (-.15, .15):
        m.slab(x - .03, x + .03, .04, .07, -.18, -.08, 'brass')       # pedals
    for x in (-.62, .62):
        m.tube((x, 1.06, -.11), (x, 1.06, -.2), .01, 'brass', 4)      # candle sconces
        m.cyl((x, 1.06, -.22), .025, .012, 'brass', 6)
    # bench
    m.slab(-.42, .42, .46, .52, -.88, -.56, 'piano')
    for x in (-.38, .38):
        for z in (-.84, -.6):
            m.slab(x - .025, x + .025, 0, .46, z - .025, z + .025, 'piano')


def dessert_cart(m, seed, crooked=False):
    """A banquet cart on casters, 1.8 x 0.7 m, front -z. Squares, cakes, a coffee urn."""
    rnd = random.Random(seed)
    top = .82
    m.slab(-.9, .9, top - .03, top, -.35, .35, 'cloth')
    for z0, z1 in ((-.36, -.35), (.35, .36)):
        m.slab(-.91, .91, .58, top, z0, z1, 'cloth_shade')
    for x0, x1 in ((-.91, -.9), (.9, .91)):
        m.slab(x0, x1, .58, top, -.36, .36, 'cloth_shade')
    m.slab(-.86, .86, .2, .23, -.32, .32, 'steel')                     # lower shelf
    for x in (-.84, .84):
        for z in (-.3, .3):
            m.tube((x, .1, z), (x, top - .03, z), .015, 'chrome', 5)
            m.cyl((x, 0, z), .045, .07, 'rubber', 6)
    # coffee urn and cups
    m.cyl((-.68, top, -.05), .13, .42, 'urn', 10, top='steel')
    m.box((-.68, top + .12, -.19), (.03, .03, .06), 'key_black')
    for i in range(3):
        m.cyl((-.42, top + i * .06, .18), .045, .06, 'mug', 8)
    # two cakes on stands
    for x, ink in ((-.2, 'pink_icing'), (.62, 'icing')):
        m.cyl((x, top, .05), .03, .12, 'plate', 6)
        m.cyl((x, top + .12, .05), .17, .012, 'plate', 12)
        m.cyl((x, top + .13, .05), .13, .1, ink, 12, top=ink)
        if ink == 'icing':
            for k in range(8):
                a = k * math.pi / 4
                m.sphere((x + .1 * math.sin(a), top + .245, .05 + .1 * math.cos(a)), .015, 'flower_red', 4, 2)
    # trays of lemon squares and brownies
    for x, ink, crust in ((.2, 'lemon', 'lemon_crust'), (.22, 'cake', 'cake')):
        z0 = -.17 if ink == 'lemon' else .2
        m.slab(x - .2, x + .2, top, top + .015, z0 - .12, z0 + .12, 'chrome')
        for i in range(4):
            for j in range(3):
                if crooked and ink == 'lemon' and (i, j) == (2, 1):
                    continue
                m.box((x - .15 + i * .1, top + .03, z0 - .075 + j * .075), (.075, .03, .06), crust, top=ink,
                      yaw=rnd.uniform(-6, 6))
    # plates and napkins
    m.cyl((.75, top, -.2), .1, .06, 'plate', 10)
    m.box((-.4, top + .01, -.2), (.16, .02, .16), 'napkin', yaw=12)
    if crooked:
        # the one lemon square, crooked on its own plate at the front corner
        m.cyl((.62, top, -.25), .085, .012, 'plate', 10)
        m.push((.6, top + .03, -.25), 31, 0, 14)
        m.box((0, 0, 0), (.08, .03, .065), 'lemon_crust', top='lemon')
        m.pop()


def easel(m):
    """A wooden display easel; the picture rests on the ledge at about 1.05 m, front -z."""
    m.tube((-.32, 0, -.12), (-.04, 1.95, .02), .02, 'wood_light', 5)
    m.tube((.32, 0, -.12), (.04, 1.95, .02), .02, 'wood_light', 5)
    m.tube((0, 0, .45), (0, 1.8, .04), .018, 'wood_light', 5)
    m.slab(-.42, .42, 1.0, 1.04, -.16, -.04, 'wood_light')


def portrait(m, glow=False):
    """Dad's portrait in a gilt frame: picture 0.6 x 0.75 m, front -z, origin at the bottom edge."""
    m.picture((0, .45, -.03), .6, .75, 'Portrait')
    m.frame((0, .45, 0), .6, .75, .07, .03, 'gold')
    m.slab(-.37, .37, .04, .86, 0, .02, 'wood_dark')
    if glow:
        m.slab(-.06, .06, .82, .86, -.02, .0, 'brass')
    # black ribbon across the corner
    m.push((.27, .77, -.045), 0, 0, -45)
    m.box((0, 0, 0), (.22, .035, .01), 'black')
    m.pop()


def memorial_table(m):
    """A cloth-covered side table: flowers, two candles, the guest book, the card. Front -z."""
    m.slab(-.55, .55, 0, .74, -.28, .28, 'cloth')
    m.slab(-.57, .57, .74, .76, -.3, .3, 'cloth_shade')
    top = .76
    # flowers in a vase at the back
    m.cyl((.32, top, .12), .07, .2, 'glass', 8)
    rnd = random.Random(3)
    for k in range(11):
        a = k * 2.4
        r = .05 + .07 * rnd.random()
        x, y, z = .32 + r * math.sin(a), top + .3 + .12 * rnd.random(), .12 + r * math.cos(a)
        m.tube((.32, top + .18, .12), (x, y, z), .005, 'leaf', 3)
        m.sphere((x, y, z), .04, rnd.choice(['flower_red', 'flower_white', 'flower_white', 'poppy']), 5, 3)
    for x in (-.4, -.25):
        m.cyl((x, top, .1), .035, .02, 'brass', 6)
        m.cyl((x, top + .02, .1), .022, .2, 'candle', 6)
    # guest book, open, with a pen
    m.push((0, top + .01, -.08), 8)
    m.slab(-.22, 0, 0, .02, -.14, .14, 'paper')
    m.slab(0, .22, 0, .02, -.14, .14, 'paper')
    m.slab(-.23, .23, -.01, 0, -.15, .15, 'navy')
    m.tube((.05, .025, -.05), (.17, .025, .06), .005, 'black', 4)
    m.pop()
    # the In Loving Memory card on a little stand
    m.push((-.32, top, -.1), -8, -12)
    m.picture((0, .12, 0), .27, .18, 'MemorialCard')
    m.slab(-.14, .14, 0, .24, .0, .01, 'gold')
    m.pop()


def flag_pole(m, mat, fly=1):
    """A flag in a floor stand, 2.6 m tall, flown stiff with a few folds; picture faces -z."""
    m.cyl((0, 0, 0), .2, .05, 'brass', 8, radius_top=.12)
    m.tube((0, 0, 0), (0, 2.6, 0), .02, 'wood_mid', 6)
    m.sphere((0, 2.67, 0), .05, 'gold', 6, 3)
    folds = 6
    w, h = 1.25, .62
    pts = [(.03 + w * i / folds, .06 * math.sin(i * 1.7)) for i in range(folds + 1)]
    for i in range(folds):
        (x0, z0), (x1, z1) = pts[i], pts[i + 1]
        y0, y1 = 2.55 - h - .05 * i / folds, 2.55 - .03 * i / folds
        y2, y3 = 2.55 - h - .05 * (i + 1) / folds, 2.55 - .03 * (i + 1) / folds
        u0, u1 = i / folds, (i + 1) / folds
        if fly > 0:
            m.quad((x1, y2, z1), (x0, y0, z0), (x0, y1, z0), (x1, y3, z1), mat=mat,
                   uv=((1 - u1, 0), (1 - u0, 0), (1 - u0, 1), (1 - u1, 1)))
            m.quad((x0, y0, z0 + .002), (x1, y2, z1 + .002), (x1, y3, z1 + .002), (x0, y1, z0 + .002), mat=mat,
                   uv=((u0, 0), (u1, 0), (u1, 1), (u0, 1)))
        else:
            m.quad((-x0, y0, z0), (-x1, y2, z1), (-x1, y3, z1), (-x0, y1, z0), mat=mat,
                   uv=((u0, 0), (u1, 0), (u1, 1), (u0, 1)))
            m.quad((-x1, y2, z1 + .002), (-x0, y0, z0 + .002), (-x0, y1, z0 + .002), (-x1, y3, z1 + .002), mat=mat,
                   uv=((1 - u1, 0), (1 - u0, 0), (1 - u0, 1), (1 - u1, 1)))


def tbar_stand(m, cans=4):
    """A party-light T-bar on a tripod, bar at 2.3 m running along x, cans aimed toward +z."""
    for a in (0, 120, 240):
        r = math.radians(a)
        m.tube((0, .5, 0), (.55 * math.sin(r), 0, .55 * math.cos(r)), .015, 'black', 5)
    m.tube((0, 0.45, 0), (0, 2.3, 0), .025, 'black', 6)
    m.tube((-.65, 2.3, 0), (.65, 2.3, 0), .02, 'black', 5)
    for i in range(cans):
        x = -.5 + i / (cans - 1)
        m.push((x, 2.22, 0), 0, 120)
        m.cyl((0, -.1, 0), .08, .2, 'black', 8, top='steel')
        m.pop()


def stacked_chairs(m, count):
    """Folded chairs stacked against a wall on a dolly; leans on -z... stands upright, faces -z."""
    m.slab(-.3, .3, 0, .1, -.55, .55, 'steel')
    for i in range(count):
        z = -.45 + i * .06
        m.slab(-.22, .22, .1, 1.0, z, z + .03, 'chair_frame')
        m.slab(-.2, .2, .55, .95, z - .005, z + .035, 'chair_vinyl')


def bar(m):
    """The bar along the west wall: counter, back shelves of bottles, taps. Customer side +x."""
    m.slab(-.35, .35, 0, 1.05, -2.2, 2.2, 'wood_red')
    m.slab(-.45, .45, 1.05, 1.1, -2.3, 2.3, 'bar_top')
    m.slab(.34, .36, .1, 1.0, -2.2, 2.2, 'wood_dark')
    m.slab(-.38, .38, 0, .1, -2.2, 2.2, 'black')
    for z in (-1.4, -.5, .4):
        m.cyl((.1, 1.1, z), .025, .32, 'tap', 6)
        m.box((.1, 1.45, z), (.05, .12, .05), 'red')
    m.slab(-.9, -.7, 1.1, 2.5, -2.2, 2.2, 'wood_dark')
    m.slab(-.7, -.68, 1.35, 2.45, -1.9, 1.9, 'mirror')
    rnd = random.Random(9)
    for y in (1.4, 1.85):
        m.slab(-.7, -.45, y - .02, y, -2.1, 2.1, 'wood_light')
        for k in range(16):
            z = -1.95 + k * .26
            ink = rnd.choice(['bottle_green', 'bottle_amber', 'glass', 'bottle_amber'])
            m.cyl((-.57, y, z), .035, .2, ink, 6)
            m.cyl((-.57, y + .2, z), .012, .07, ink, 4)


def dartboard(m):
    """A dartboard in a cabinet, face -x... faces -z; yaw it to the wall."""
    m.slab(-.42, .42, -.42, .42, .0, .06, 'wood_dark')
    m.push((0, 0, 0), 0, -90)
    m.cyl((0, 0, 0), .23, .04, 'dart_cork', 16)
    for r, ink in ((.21, 'black'), (.17, 'dart_red'), (.1, 'black'), (.04, 'dart_green'), (.015, 'dart_red')):
        m.cyl((0, .041, 0), r, .003, ink, 16)
    m.pop()


def coat_rack(m):
    m.cyl((0, 0, 0), .25, .04, 'black', 8)
    m.tube((0, 0, 0), (0, 1.8, 0), .02, 'chrome', 6)
    rnd = random.Random(4)
    for k in range(6):
        a = k * math.pi / 3
        m.tube((0, 1.7, 0), (.2 * math.sin(a), 1.75, .2 * math.cos(a)), .01, 'chrome', 4)
        if k % 2 == 0 or k == 3:
            ink = rnd.choice(['coat_grey', 'coat_camel', 'coat_navy', 'black'])
            m.push((.22 * math.sin(a), 1.2, .22 * math.cos(a)), math.degrees(a))
            m.box((0, 0, 0), (.42, 1.0, .14), ink)
            m.pop()


def shoes(m, kind):
    """A pair of shoes, toes to -z. kind: heels (hers) or oxfords (his)."""
    for x in (-.06, .06):
        if kind == 'heels':
            m.push((x, 0, 0), -8 if x < 0 else 12)
            m.slab(-.035, .035, .0, .03, -.12, .08, 'heel')
            m.slab(-.03, .03, .03, .08, .05, .09, 'heel')
            m.slab(-.01, .01, 0, .08, .07, .09, 'heel')
            m.pop()
        else:
            m.push((x * 1.3, 0, 0), 6 if x < 0 else -20)
            m.slab(-.045, .045, 0, .07, -.14, .14, 'shoe_black')
            m.pop()


def tie_draped(m):
    """The uncle's tie over the corner of the piano lid: two tails hanging, one front, one side."""
    m.slab(-.03, .03, -.32, 0, -.012, 0, 'tie')
    m.slab(-.045, .045, -.42, -.3, -.012, 0, 'tie')
    m.slab(0, .012, -.24, 0, .01, .07, 'tie')
    m.slab(-.03, .1, 0, .012, -.012, .08, 'tie')


def napkin_stack(m, seed):
    rnd = random.Random(seed)
    for k in range(5):
        m.push((rnd.uniform(-.03, .03), .006 * k, rnd.uniform(-.03, .03)), rnd.uniform(-25, 25))
        m.box((0, .003, 0), (.15, .006, .15), 'napkin')
        m.pop()
    m.push((0, .034, 0), 14)
    m.quad((.075, 0, -.075), (-.075, 0, -.075), (-.075, 0, .075), (.075, 0, .075), mat='Napkins',
           uv=((1, 0), (0, 0), (0, 1), (1, 1)))
    m.pop()
