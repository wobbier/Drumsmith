"""The Hall's architecture and props as meshes (StoryEventHorizon). Venue metres throughout."""
import math
import random

from story_event_horizon_mesh import Mesh, add, mul, sub, unit

HALL_C = (0.0, 0.0, -2.0)   # the rotunda's centre on the floor
HALL_R = 27.0               # the wall's radius
WINDOW_HALF = 58.0          # degrees either side of +z that are glass (the back, behind the band)
TOP_Y = 34.0                # the ring beam the dome sits on
OCULUS_Y, OCULUS_R = 46.0, 7.0
STAGE_C, STAGE_R, STAGE_H = (0.0, 0.0, 6.0), 9.5, 0.6
RISER_C, RISER_R, RISER_H = (0.0, 0.0, 7.3), 2.7, 0.4


def at(theta_deg, r, y, c=HALL_C):
    t = math.radians(theta_deg)
    return (c[0] + r * math.sin(t), y, c[2] + r * math.cos(t))


def hall():
    m = Mesh('Hall', 'The rotunda: floor, stage dais, gallery walls, columns, window frame and dome ribs.')
    # Floor and its brass inlay.
    m.tube((HALL_C[0], -0.4, HALL_C[2]), (HALL_C[0], 0.0, HALL_C[2]), HALL_R + 0.6, HALL_R + 0.6, 'marble_dark', 64)
    for r, w in ((6.0, 0.18), (12.5, 0.22), (19.0, 0.26), (24.5, 0.3)):
        m.annulus(add(HALL_C, (0, 0.012, 0)), (0, 1, 0), r, r + w, 'brass', 96, both=False)
    for k in range(16):  # compass spokes in the floor
        a, b = at(k * 22.5, 6.2, 0.01), at(k * 22.5, 24.5, 0.01)
        d = unit(sub(b, a)); n = (d[2] * 0.06, 0, -d[0] * 0.06)
        m.face([add(a, n), sub(a, n), sub(b, n), add(b, n)], 'brass_dark', (0, 1, 0))
    # Stage dais and the drum riser.
    sx, _, sz = STAGE_C
    m.tube((sx, 0, sz), (sx, STAGE_H, sz), STAGE_R, STAGE_R, 'hull', 48)
    m.torus((sx, STAGE_H - 0.02, sz), (0, 1, 0), STAGE_R + 0.02, 0.09, 0.06, 'brass', 72)
    m.torus((sx, 0.08, sz), (0, 1, 0), STAGE_R + 0.05, 0.08, 0.08, 'brass_dark', 72)
    m.annulus((sx, STAGE_H + 0.004, sz), (0, 1, 0), 0, STAGE_R - 0.4, 'navy', 48, both=False)
    m.annulus((sx, STAGE_H + 0.008, sz), (0, 1, 0), STAGE_R - 0.4, STAGE_R - 0.25, 'brass_dark', 72, both=False)
    rx, _, rz = RISER_C
    m.tube((rx, STAGE_H, rz), (rx, STAGE_H + RISER_H, rz), RISER_R, RISER_R, 'steel_dark', 32)
    m.torus((rx, STAGE_H + RISER_H - 0.02, rz), (0, 1, 0), RISER_R, 0.07, 0.05, 'brass', 48)
    m.annulus((rx, STAGE_H + RISER_H + 0.004, rz), (0, 1, 0), 0, RISER_R - 0.1, 'carpet', 32, both=False)
    # The deck behind the stage, out to the window.
    m.tube((0, 0, 14.5), (0, 0.3, 14.5), 10.5, 10.5, 'hull', 40)
    # Columns all the way round; between them a lower gallery wall except at the window.
    for k in range(24):
        th = -180 + k * 15 + 7.5
        base = at(th, HALL_R, 0)
        m.tube(base, at(th, HALL_R, TOP_Y), 0.55, 0.45, 'hull_light' if abs(th) < WINDOW_HALF else 'hull', 10)
        m.tube(at(th, HALL_R, 0), at(th, HALL_R, 1.0), 0.8, 0.8, 'brass_dark', 10)
        m.tube(at(th, HALL_R, TOP_Y - 1.2), at(th, HALL_R, TOP_Y), 0.6, 0.85, 'brass', 10)
        m.tube(at(th, HALL_R, 7.6), at(th, HALL_R, 8.2), 0.62, 0.62, 'brass', 10)
    for k in range(48):
        a0, a1 = -180 + k * 7.5, -180 + (k + 1) * 7.5
        mid = (a0 + a1) / 2
        if abs(mid) < WINDOW_HALF:
            # Window: a low sill and transoms of the frame.
            seg(m, a0, a1, HALL_R, 0, 1.2, 0.5, 'hull')
            for y in (12.0, 22.0):
                seg(m, a0, a1, HALL_R, y, y + 0.35, 0.3, 'steel')
            mull = at(mid, HALL_R, 0)
            m.tube(add(mull, (0, 1.2, 0)), add(mull, (0, TOP_Y, 0)), 0.09, 0.09, 'steel', 6)
        else:
            seg(m, a0, a1, HALL_R + 0.3, 0, 7.6, 0.6, 'hull')                 # gallery wall
            seg(m, a0, a1, HALL_R - 0.5, 7.4, 7.7, 0.9, 'brass_dark')          # parapet cap
            seg(m, a0, a1, HALL_R + 0.4, 7.7, 14.0, 0.3, 'navy')               # plaque wall
            seg(m, a0, a1, HALL_R, 14.0, 14.4, 0.5, 'brass_dark')
            for y in (20.0, 26.0):
                seg(m, a0, a1, HALL_R, y, y + 0.3, 0.3, 'steel')
    m.torus((HALL_C[0], TOP_Y + 0.4, HALL_C[2]), (0, 1, 0), HALL_R, 0.8, 0.45, 'brass', 96, inner_ink='brass_dark')
    # Dome ribs to the oculus.
    for k in range(24):
        th = -180 + k * 15 + 7.5
        prev = at(th, HALL_R, TOP_Y + 0.6)
        for i in range(1, 9):
            t = i / 8
            r = HALL_R + (OCULUS_R - HALL_R) * math.sin(t * math.pi / 2)
            y = TOP_Y + (OCULUS_Y - TOP_Y) * (1 - math.cos(t * math.pi / 2)) ** 0.8
            p = at(th, r, y)
            m.tube(prev, p, 0.28, 0.24, 'hull', 6)
            prev = p
    m.torus((HALL_C[0], OCULUS_Y, HALL_C[2]), (0, 1, 0), OCULUS_R, 0.6, 0.5, 'brass', 48)
    # Side galleries (the upper bowl) with stepped tiers for the inductees' guests.
    for side in (-1, 1):
        for x0, y in ((17.6, 3.2), (19.6, 4.0), (21.6, 4.8)):
            m.box((side * (x0 + 26.0) / 2, y / 2, -7.5), (26.0 - x0, y, 17.0), 'hull')
        m.box((side * 17.45, 3.75, -7.5), (0.25, 1.1, 17.0), 'brass_dark')
        m.box((side * 17.45, 4.33, -7.5), (0.4, 0.08, 17.1), 'brass')
    return m


def seg(m, a0, a1, r, y0, y1, depth, ink):
    """A wall panel between two angles around the hall (a flat chord), depth thick."""
    p0, p1 = at(a0, r, 0), at(a1, r, 0)
    mid = mul(add(p0, p1), 0.5)
    inward = unit(sub((HALL_C[0], 0, HALL_C[2]), mid))
    q0, q1 = add(p0, mul(inward, depth)), add(p1, mul(inward, depth))
    c = (mid[0] + inward[0] * depth / 2, (y0 + y1) / 2, mid[2] + inward[2] * depth / 2)
    quads = [[(p0[0], y0, p0[2]), (p1[0], y0, p1[2]), (p1[0], y1, p1[2]), (p0[0], y1, p0[2])],
             [(q0[0], y0, q0[2]), (q1[0], y0, q1[2]), (q1[0], y1, q1[2]), (q0[0], y1, q0[2])],
             [(p0[0], y1, p0[2]), (p1[0], y1, p1[2]), (q1[0], y1, q1[2]), (q0[0], y1, q0[2])],
             [(p0[0], y0, p0[2]), (p1[0], y0, p1[2]), (q1[0], y0, q1[2]), (q0[0], y0, q0[2])],
             [(p0[0], y0, p0[2]), (q0[0], y0, q0[2]), (q0[0], y1, q0[2]), (p0[0], y1, p0[2])],
             [(p1[0], y0, p1[2]), (q1[0], y0, q1[2]), (q1[0], y1, q1[2]), (p1[0], y1, p1[2])]]
    for q in quads:
        mq = mul(tuple(map(sum, zip(*q))), 0.25)
        m.face(q, ink, sub(mq, c))


# ---- rings ---------------------------------------------------------------------------------
RING_R = [11.0, 9.3, 7.6, 5.9, 4.2]          # first (outermost) .. fifth (innermost, over the kit)
RING_W = [0.42, 0.38, 0.33, 0.29, 0.25]      # radial half-width
RING_D = [0.30, 0.27, 0.24, 0.21, 0.18]      # half-depth


def ring(k):
    """Ring k (0-based) in local space: centred on the origin, axis +z (faces the crowd)."""
    R, w, d = RING_R[k], RING_W[k], RING_D[k]
    m = Mesh(f'Ring{k+1}', f'Brass drive ring {k+1}: a flat band with engraved tick blocks and coil housings.')
    m.torus((0, 0, 0), (0, 0, 1), R, w, d, 'brass', 96, inner_ink='brass_dark')
    m.torus((0, 0, 0), (0, 0, 1), R + w + 0.05, 0.06, d * 0.6, 'brass_pale', 96)
    for i in range(36):
        t = i * math.tau / 36
        p = (R * math.cos(t), R * math.sin(t), -d - 0.03)
        big = i % 9 == 0
        size = (0.10 if not big else 0.22, w * (1.5 if big else 0.9), 0.08)
        m.box(p, size, 'brass_dark', yaw=0) if not big else None
        if big:  # coil housing: a fat block round the band
            m.tube((p[0], p[1], -d - 0.15), (p[0], p[1], d + 0.15), w * 1.6, w * 1.6, 'bronze', 8)
    return m


def ring_glow(k):
    R, w, d = RING_R[k], RING_W[k], RING_D[k]
    m = Mesh(f'RingGlow{k+1}', f'The lit strip on ring {k+1}: a thin annulus proud of its crowd face.')
    m.annulus((0, 0, -d - 0.02), (0, 0, 1), R - w * 0.45, R + w * 0.45, 'white', 128)
    return m


def ring_nodes(k):
    R, d = RING_R[k], RING_D[k]
    m = Mesh(f'RingNodes{k+1}', f'Armed: the charge nodes on ring {k+1}.')
    for i in range(8):
        t = (i + 0.5) * math.tau / 8
        m.sphere((R * math.cos(t), R * math.sin(t), -d - 0.12), 0.22 + 0.03 * (5 - k), 'white', 8, 5)
    return m


def ring_clamps():
    """Third ring locked: brass clamps bridging rings two, three and four, at the diagonals."""
    m = Mesh('RingClamps', 'Lock clamps across rings two to four.')
    for i in range(4):
        t = math.radians(45 + 90 * i)
        u = (math.cos(t), math.sin(t), 0)
        a, b = mul(u, RING_R[3] - 0.3), mul(u, RING_R[1] + 0.3)
        m.tube(add(a, (0, 0, -0.35)), add(b, (0, 0, -0.35)), 0.2, 0.2, 'steel', 8)
        for r in (RING_R[1], RING_R[2], RING_R[3]):
            m.box(add(mul(u, r), (0, 0, -0.35)), (0.7, 0.7, 0.35), 'bronze', yaw=0)
    return m


def clamp_lamps():
    m = Mesh('ClampLamps', 'The lock lights on the clamps.')
    for i in range(4):
        t = math.radians(45 + 90 * i)
        u = (math.cos(t), math.sin(t), 0)
        for r in (RING_R[1], RING_R[2], RING_R[3]):
            m.box(add(mul(u, r), (0, 0, -0.55)), (0.34, 0.34, 0.06), 'white')
    return m


def pylons(c):
    """The two great arms that hold the first ring's pins, standing on the deck."""
    m = Mesh('RingPylons', 'Brass pylons either side of the stage holding the outer ring.')
    x = RING_R[0] + 1.3
    for s in (-1, 1):
        base = (s * x, 0, c[2])
        m.tube(base, (s * x, 0.8, c[2]), 1.2, 1.0, 'hull', 10)
        m.tube((s * x, 0.8, c[2]), (s * x * 1.0, c[1] - 0.6, c[2]), 0.55, 0.42, 'steel', 10)
        m.tube((s * x, c[1] - 0.8, c[2]), (s * x, c[1] + 0.8, c[2]), 0.75, 0.75, 'brass', 12)
        m.tube((s * x, c[1], c[2]), (s * (RING_R[0] + RING_W[0]), c[1], c[2]), 0.25, 0.25, 'brass_pale', 10)
        for y in (3, 6, 9):
            m.torus((s * x, y, c[2]), (0, 1, 0), 0.5, 0.06, 0.08, 'brass', 12)
    return m


# ---- the sky -------------------------------------------------------------------------------
def stars(hole_dir, eaten_deg=13.0):
    """Three star meshes (white, blue, warm) and one of dust along a galactic band."""
    rnd = random.Random(1313)
    out = {n: Mesh(n, 'Stars: tiny octahedra on a 230 m sphere.') for n in ('StarsWhite', 'StarsBlue', 'StarsWarm', 'StarsDust')}
    hd = unit(hole_dir)
    band = unit((0.35, 0.55, 0.76))  # the galactic plane's normal

    def place(mesh, d, size):
        if math.degrees(math.acos(max(-1, min(1, sum(a * b for a, b in zip(d, hd)))))) < eaten_deg:
            return
        if d[1] < -0.05:
            return
        p = mul(d, 230.0)
        p = (p[0], p[1], p[2] - 2)
        s = size
        pts = [add(p, o) for o in ((s, 0, 0), (-s, 0, 0), (0, s, 0), (0, -s, 0), (0, 0, s), (0, 0, -s))]
        for a, b, c in ((0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)):
            mesh.face([pts[a], pts[b], pts[c]], 'white', sub(mul(add(add(pts[a], pts[b]), pts[c]), 1 / 3), p))

    def rand_dir():
        while True:
            v = (rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))
            l = math.sqrt(sum(x * x for x in v))
            if 0.1 < l <= 1:
                return mul(v, 1 / l)

    for _ in range(1500):
        place(out['StarsWhite'], rand_dir(), rnd.choice((0.45, 0.55, 0.7, 0.7, 0.9, 1.3)))
    for _ in range(420):
        place(out['StarsBlue'], rand_dir(), rnd.choice((0.6, 0.8, 1.1, 1.6)))
    for _ in range(320):
        place(out['StarsWarm'], rand_dir(), rnd.choice((0.6, 0.8, 1.0, 1.4)))
    n = 0
    while n < 2600:
        d = rand_dir()
        if abs(sum(a * b for a, b in zip(d, band))) < rnd.uniform(0.02, 0.16):
            place(out['StarsDust'], d, rnd.choice((0.35, 0.45, 0.55)))
            n += 1
    return list(out.values())


# The black hole is built in local space facing -z (toward the crowd), radius 15.
def hole_meshes():
    ms = {}
    m = Mesh('PhotonRing', 'The thin bright ring hugging the shadow.')
    m.annulus((0, 0, 0), (0, 0, 1), 15.0, 15.8, 'white', 128)
    ms['PhotonRing'] = m
    for name, r0, r1 in (('LensInner', 15.8, 17.6), ('LensMid', 17.6, 20.8), ('LensOuter', 20.8, 26.0)):
        m = Mesh(name, 'The far side of the disc, bent up over the top and under the bottom.')
        m.annulus((0, 0, 0.5), (0, 0, 1), r0, r1, 'white', 128)
        ms[name] = m
    tilt = math.radians(9.0)
    axis = (0, math.cos(tilt), -math.sin(tilt))   # nearly edge-on, tipped toward the crowd
    for name, r0, r1 in (('DiscHot', 16.5, 23.0), ('DiscWarm', 23.0, 32.0), ('DiscCool', 32.0, 46.0)):
        m = Mesh(name, 'The accretion disc, nearly edge-on.')
        m.annulus((0, 0, 0), axis, r0, r1, 'white', 128)
        ms[name] = m
    m = Mesh('LensedStars', 'Bent starlight: one row of stars seen twice, above and below the shadow.')
    rnd = random.Random(77)
    for row, r in enumerate((28.5, 31.5)):
        for i in range(70):
            a = math.radians(rnd.uniform(25, 155))
            for sgn in (1, -1):
                p = (r * math.cos(a), sgn * r * math.sin(a) * (1.0 if sgn > 0 else 0.92), -0.5)
                s = rnd.choice((0.35, 0.45, 0.6))
                # Stretched along the ring: lensed stars smear into short arcs.
                t = (-math.sin(a), sgn * math.cos(a), 0)
                pts = [add(p, mul(t, s * 3)), add(p, (0, 0, -s)), add(p, mul(t, -s * 3)), add(p, (0, 0, s))]
                n = (math.cos(a), sgn * math.sin(a), 0)
                pts2 = [add(p, mul(t, s * 3)), add(p, mul(n, s)), add(p, mul(t, -s * 3)), add(p, mul(n, -s))]
                m.quad2(pts2, 'white')
    ms['LensedStars'] = m
    return ms


# ---- stage props ---------------------------------------------------------------------------
def music_stand():
    m = Mesh('MusicStand', 'One plain black music stand with a part open on it. Base at the origin, desk faces -z.')
    for i in range(3):
        t = i * math.tau / 3 + 0.3
        m.tube((0, 0.35, 0), (0.42 * math.cos(t), 0.0, 0.42 * math.sin(t)), 0.018, 0.018, 'rubber', 5)
    m.tube((0, 0.0, 0), (0, 1.12, 0), 0.02, 0.016, 'rubber', 6)
    desk = [(-0.27, 0.98, 0.08), (0.27, 0.98, 0.08), (0.27, 1.34, -0.04), (-0.27, 1.34, -0.04)]
    m.quad2(desk, 'rubber')
    m.box((0, 0.985, 0.04), (0.56, 0.03, 0.08), 'rubber')
    paper = [(-0.25, 1.0, 0.06), (0.0, 1.0, 0.07), (0.0, 1.33, -0.05), (-0.25, 1.33, -0.06)]
    m.face(paper, 'paper', (0, 0.3, -1))
    paper = [(0.005, 1.0, 0.07), (0.255, 1.0, 0.06), (0.255, 1.33, -0.06), (0.005, 1.33, -0.05)]
    m.face(paper, 'paper', (0, 0.3, -1))
    return m


def rehearsal_lamp():
    m = Mesh('RehearsalLamp', 'A warm rehearsal lamp: tripod foot, pole, bent arm and a cone shade. Base at origin.')
    for i in range(3):
        t = i * math.tau / 3
        m.tube((0, 0.3, 0), (0.35 * math.cos(t), 0.0, 0.35 * math.sin(t)), 0.02, 0.02, 'brass_dark', 5)
    m.tube((0, 0, 0), (0, 1.75, 0), 0.022, 0.02, 'brass_dark', 6)
    m.tube((0, 1.75, 0), (0.28, 1.95, -0.25), 0.018, 0.018, 'brass_dark', 6)
    return m


def lamp_shade():
    m = Mesh('LampShade', 'The lamp shade, lit from inside.')
    m.tube((0.28, 2.02, -0.25), (0.33, 1.78, -0.30), 0.06, 0.2, 'shade', 12)
    return m


def podium():
    m = Mesh('ConductorPodium', 'The house conductor\'s podium: octagonal walnut step, brass rail, score desk. Faces -z.')
    m.tube((0, 0, 0), (0, 0.32, 0), 0.85, 0.85, 'walnut', 8)
    m.torus((0, 0.3, 0), (0, 1, 0), 0.86, 0.05, 0.03, 'brass', 8, phase=math.pi / 8)
    m.annulus((0, 0.325, 0), (0, 1, 0), 0, 0.8, 'velvet', 8, both=False)
    for i in range(5):  # the rail round the back
        t = math.radians(200 + i * 35)
        m.tube((0.78 * math.cos(t), 0.32, 0.78 * math.sin(t)), (0.78 * math.cos(t), 1.25, 0.78 * math.sin(t)), 0.03, 0.03, 'brass', 6)
    for i in range(4):
        t0, t1 = math.radians(200 + i * 35), math.radians(200 + (i + 1) * 35)
        m.tube((0.78 * math.cos(t0), 1.25, 0.78 * math.sin(t0)), (0.78 * math.cos(t1), 1.25, 0.78 * math.sin(t1)), 0.035, 0.035, 'brass', 6)
    # Score desk in front.
    m.tube((0, 0.32, -0.62), (0, 1.15, -0.62), 0.04, 0.04, 'brass_dark', 6)
    m.box((0, 1.2, -0.66), (0.7, 0.04, 0.42), 'walnut')
    m.face([(-0.32, 1.23, -0.82), (0.32, 1.23, -0.82), (0.32, 1.24, -0.5), (-0.32, 1.24, -0.5)], 'paper', (0, 1, 0))
    return m


def conductor(pose):
    """A low-poly figure in tails, local space, feet at the origin, facing -z.
    pose: 'up' (baton raised), 'down' (stepped back, baton lowered), 'point' (baton at the drummer)."""
    m = Mesh(f'Conductor_{pose}', f'The house conductor, {pose}.')
    for s in (-1, 1):
        m.tube((s * 0.11, 0.0, 0), (s * 0.12, 0.92, 0), 0.075, 0.09, 'black', 6)
        m.box((s * 0.11, 0.04, -0.05), (0.12, 0.08, 0.28), 'black')
    m.tube((0, 0.88, 0), (0, 1.5, 0), 0.2, 0.25, 'black', 8)             # tailcoat
    m.face([(-0.2, 0.45, 0.13), (0.2, 0.45, 0.13), (0.22, 1.0, 0.16), (-0.22, 1.0, 0.16)], 'black', (0, 0, 1))
    m.box((0, 1.32, -0.2), (0.16, 0.34, 0.06), 'ivory')                  # shirt front
    m.box((0, 1.47, -0.21), (0.12, 0.05, 0.05), 'black')                 # bow tie
    m.tube((0, 1.5, 0), (0, 1.6, 0), 0.06, 0.06, 'cream', 6)             # neck
    m.sphere((0, 1.72, -0.01), 0.13, 'cream', 8, 6, squash=1.15)        # head
    m.sphere((0, 1.77, 0.03), 0.135, 'marble', 8, 5, squash=0.9)        # silver hair
    sh = 0.27
    if pose == 'up':
        r_el, r_hand, l_el, l_hand = (0.38, 1.6, -0.25), (0.33, 1.95, -0.38), (-0.35, 1.25, -0.2), (-0.3, 1.45, -0.42)
        tip = (0.28, 2.38, -0.55)
    elif pose == 'down':
        r_el, r_hand, l_el, l_hand = (0.33, 1.15, -0.05), (0.3, 0.9, -0.12), (-0.33, 1.15, -0.02), (-0.3, 0.9, -0.08)
        tip = (0.3, 0.55, -0.3)
    else:
        r_el, r_hand, l_el, l_hand = (0.36, 1.42, -0.32), (0.32, 1.5, -0.6), (-0.34, 1.2, -0.1), (-0.32, 1.05, -0.25)
        tip = (0.3, 1.62, -1.08)
    for s, el, hand in ((1, r_el, r_hand), (-1, l_el, l_hand)):
        m.tube((s * sh * 0.85, 1.43, 0), el, 0.06, 0.055, 'black', 6)
        m.tube(el, hand, 0.055, 0.045, 'black', 6)
        m.sphere(hand, 0.055, 'white', 6, 4)
    m.tube(r_hand, tip, 0.012, 0.008, 'white', 4)
    return m


def plaque(name, mtl, w=2.4, h=1.2, d=0.08):
    """A brass plate: the front (local -z) shows the whole texture; the edges take its border."""
    m = Mesh(name, f'Engraved plate, {w} x {h} m, texture {mtl}.')
    x, y, z = w / 2, h / 2, d / 2
    edge = [(0.01, 0.5)] * 4
    front = [(-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z)]
    m.face(front, None, (0, 0, -1), uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    for q, o in (([(-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)], (0, 0, 1)),
                 ([(-x, y, -z), (x, y, -z), (x, y, z), (-x, y, z)], (0, 1, 0)),
                 ([(-x, -y, -z), (x, -y, -z), (x, -y, z), (-x, -y, z)], (0, -1, 0)),
                 ([(-x, -y, -z), (-x, y, -z), (-x, y, z), (-x, -y, z)], (-1, 0, 0)),
                 ([(x, -y, -z), (x, y, -z), (x, y, z), (x, -y, z)], (1, 0, 0))):
        m.face(q, None, o, uvs=edge)
    return m


def pickups_and_leads(riser_top, ring_c):
    """The touring kit's five brass contact pickups and their leads to the pylons."""
    m = Mesh('KitLeads', 'Five brass contact pickups on the kit and braided leads back to the ring pylons.')
    y = riser_top
    for x, z, h in ((-0.55, 6.3, 0.62), (0.0, 6.0, 0.75), (0.55, 6.3, 0.62), (0.9, 6.9, 0.45), (0.25, 6.7, 0.4)):
        m.tube((x, y + h, z), (x, y + h + 0.03, z), 0.05, 0.05, 'gold', 8)
    for i, s in enumerate((-1, -1, 1, 1, 1)):
        x0 = (-0.9, -0.6, 0.6, 0.9, 1.2)[i]
        pts = [(x0, y + 0.02, 7.6), (x0 * 1.6, y + 0.02, 8.6), (s * (2.4 + 0.15 * i), 0.62, 9.2 + 0.1 * i),
               (s * (8.0 + 0.2 * i), 0.62, ring_c[2] - 0.6 + 0.12 * i), (s * (RING_R[0] + 0.5), 0.62, ring_c[2] - 0.4 + 0.12 * i)]
        for a, b in zip(pts, pts[1:]):
            m.tube(a, b, 0.03, 0.03, 'brass_dark', 5, caps=False)
    return m


def hat_loonie():
    m = Mesh('HatLoonie', 'The drilled loonie on the hi-hat stand.')
    m.tube((0, 0, -0.008), (0, 0, 0.008), 0.027, 0.027, 'gold', 11)
    return m
