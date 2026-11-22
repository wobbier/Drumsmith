"""The Steel Mill Tour's paint shop: the five set sheets, the stencilled road case, the tour drop,
the mill's header plate, the changeover board and hazard stripes. Drawn with ImageMagick 7
(`magick`, from the PATH or the Nix store) into Assets/Venues/StorySteelMill/Textures/.

Deterministic (fixed seeds, metadata stripped). If magick isn't found the existing PNGs are kept,
so the scene still regenerates. The band names are made up.
"""
import glob
import os
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "Assets", "Venues", "StorySteelMill", "Textures")
REL = "Assets/Venues/StorySteelMill/Textures/"
MARKER = os.path.join(ROOT, "Assets", "Fonts", "PermanentMarker-Regular.ttf")
HAND = os.path.join(ROOT, "Assets", "Fonts", "GochiHand-Regular.ttf")

# The five acts, in running order: name, sheet paper colour, ink, a note the act scrawled.
ACTS = [
    ("SLAG CHOIR", "rgb(238,234,222)", "rgb(30,30,34)", "count in on the hats - 4"),
    ("COLDWATER STATIC", "rgb(120,170,228)", "rgb(16,22,52)", "kicks WITH the chugs"),
    ("NINTH SHIFT", "rgb(246,214,74)", "rgb(40,26,10)", "toms answer snare!!"),
    ("HOLLOW ANVIL", "rgb(244,132,92)", "rgb(48,12,10)", "don't stop under the solo"),
    ("EMBER UNION", "rgb(132,214,140)", "rgb(10,40,18)", "end on the cut. LOUD."),
]


def find_magick():
    m = shutil.which("magick")
    if m:
        return m
    hits = sorted(glob.glob("/nix/store/*-imagemagick-7*/bin/magick"))
    return hits[-1] if hits else None


def font(name):
    hits = sorted(glob.glob(f"/nix/store/*/share/fonts/truetype/{name}")) + sorted(glob.glob(f"/usr/share/fonts/**/{name}", recursive=True))
    return hits[0] if hits else "DejaVu-Sans-Bold"


BOLD = font("DejaVuSans-Bold.ttf")
COND = font("DejaVuSansCondensed-Bold.ttf")
MONO = font("LiberationMono-Bold.ttf")
M = None


def magick(*args):
    cmd = [M, *[str(a) for a in args]]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"magick failed: {' '.join(cmd)}\n{r.stderr}")


def out(name):
    return os.path.join(OUT, name + ".png")


def finish(name):
    """The engine samples PNGs bottom-up on the cube's faces: store them flipped so they read."""
    magick(out(name), "-flip", "-strip", "-define", "png:exclude-chunks=date,time", out(name))
    if os.path.exists(out(name) + ".dds"):
        os.remove(out(name) + ".dds")  # a stale cooked twin would win over the new picture


def grain(name, amount=0.3, seed=1):
    magick(out(name), "(", "+clone", "-seed", seed, "-attenuate", amount, "+noise", "Gaussian", "-colorspace", "gray", ")",
           "-compose", "overlay", "-composite", out(name))


def sheet(i):
    act, paper, ink, note = ACTS[i]
    name = f"Sheet{i + 1}"
    w, h = 512, 724
    magick("-size", f"{w}x{h}", f"xc:{paper}", out(name))
    grain(name, 0.22, 10 + i)
    lines = [
        ("-font", MARKER, "-pointsize", 50 if len(act) < 12 else 38, "-fill", ink, "-gravity", "north", "-annotate", "-2x-2+0+118", act),
        ("-font", MARKER, "-pointsize", 30, "-fill", ink, "-gravity", "north", "-annotate", "+0+196", "ONE SONG / HOUSE KIT"),
        ("-font", HAND, "-pointsize", 40, "-fill", ink, "-gravity", "northwest", "-annotate", "+46+272", "intro - 8 bars, you start"),
        ("-font", HAND, "-pointsize", 40, "-fill", ink, "-gravity", "northwest", "-annotate", "+46+326", "verse - half time"),
        ("-font", HAND, "-pointsize", 40, "-fill", ink, "-gravity", "northwest", "-annotate", "+46+380", "chorus - open it up"),
        ("-font", HAND, "-pointsize", 40, "-fill", ink, "-gravity", "northwest", "-annotate", "+46+434", "end - on the vox cue"),
        ("-font", MARKER, "-pointsize", 36, "-fill", "rgb(200,20,24)", "-gravity", "northwest", "-annotate", "-4x-4+40+516", note),
        ("-font", MARKER, "-pointsize", 86, "-fill", "rgb(200,20,24)", "-gravity", "southeast", "-annotate", "-8x-8+40+40", str(i + 1)),
    ]
    for args in lines:
        magick(out(name), *args, out(name))
    # A marker rule under the name and gaffer tape over the top corners.
    magick(out(name), "-stroke", ink, "-strokewidth", 6, "-draw", "line 60,252 452,258",
           "-stroke", "none", "-fill", "rgba(70,72,78,0.88)",
           "-draw", "polygon 0,40 40,0 150,70 110,110", "-draw", "polygon 512,40 472,0 362,70 402,110",
           "-draw", "polygon 200,724 230,680 330,690 320,724", out(name))
    finish(name)


def case_stencil():
    name = "CaseStencil"
    w, h = 1024, 640
    magick("-size", f"{w}x{h}", "xc:rgb(20,20,22)", out(name))
    grain(name, 0.35, 41)
    magick(out(name), "-font", BOLD, "-pointsize", 230, "-fill", "rgb(236,232,220)", "-gravity", "center",
           "-annotate", "+0-30", "DRUMS", out(name))
    # Stencil bridges: dark bars cut through the letters.
    magick(out(name), "-fill", "rgb(20,20,22)", "-draw", "rectangle 60,286 964,300", out(name))
    magick(out(name), "-font", COND, "-pointsize", 54, "-fill", "rgb(236,232,220)", "-gravity", "south",
           "-annotate", "+0+92", "HOUSE KIT  -  STEEL MILL TOUR", out(name))
    # Five bands' tape, each in their sheet's colour, signed.
    tapes = [(20, 14, -12), (250, 6, 4), (560, 10, -3), (800, 14, 9), (420, 574, -4)]
    for (x, y, ang), (act, paper, ink, _) in zip(tapes, ACTS):
        initials = "".join(word[0] for word in act.split())
        magick(out(name), "(", "-size", "210x56", f"xc:{paper}", "-font", MARKER, "-pointsize", 34, "-fill", ink,
               "-gravity", "center", "-annotate", "+0+0", initials + " <3", "-background", "none", "-rotate", ang, ")",
               "-gravity", "northwest", "-geometry", f"+{x}+{y}", "-composite", out(name))
    finish(name)


def tour_drop():
    name = "TourDrop"
    w, h = 2048, 1024
    magick("-size", f"{w}x{h}", "xc:rgb(10,10,12)", out(name))
    grain(name, 0.25, 51)
    # A gear ring around an anvil-ish block, in the tour's orange.
    teeth = []
    import math
    cx, cy, r0, r1 = 1024, 370, 195, 240
    for k in range(18):
        a0 = math.radians(k * 20 - 5)
        a1 = math.radians(k * 20 + 5)
        pts = [(cx + r0 * math.cos(a0), cy + r0 * math.sin(a0)), (cx + r1 * math.cos(a0), cy + r1 * math.sin(a0)),
               (cx + r1 * math.cos(a1), cy + r1 * math.sin(a1)), (cx + r0 * math.cos(a1), cy + r0 * math.sin(a1))]
        teeth += ["-draw", "polygon " + " ".join(f"{x:.0f},{y:.0f}" for x, y in pts)]
    magick(out(name), "-fill", "rgb(236,104,22)", *teeth, "-draw", f"circle {cx},{cy} {cx + r0 + 4},{cy}",
           "-fill", "rgb(10,10,12)", "-draw", f"circle {cx},{cy} {cx + 150},{cy}", out(name))
    magick(out(name), "-fill", "rgb(236,104,22)", "-draw", "polygon " + " ".join(f"{1024 + (x - 1025) * .75:.0f},{cy + (y - 470) * .75:.0f}" for x, y in
           [(880,380),(1170,380),(1130,440),(1090,440),(1090,520),(1150,560),(900,560),(960,520),(960,440),(900,420)]),
           out(name))
    magick(out(name), "-font", BOLD, "-pointsize", 190, "-fill", "rgb(236,104,22)", "-gravity", "south",
           "-annotate", "+0+150", "STEEL MILL TOUR", out(name))
    magick(out(name), "-font", COND, "-pointsize", 64, "-fill", "rgb(150,180,215)", "-gravity", "south",
           "-annotate", "+0+60", "ONE NIGHT  /  FIVE BANDS  /  ONE KIT", out(name))
    # Scuffs: the drop has done forty nights in sheds like this one.
    scuffs = []
    import random
    rnd = random.Random(7)
    for _ in range(140):
        x, y = rnd.randint(0, w), rnd.randint(0, h)
        scuffs += ["-draw", f"line {x},{y} {x + rnd.randint(-40, 40)},{y + rnd.randint(-6, 6)}"]
    magick(out(name), "-stroke", "rgba(10,10,12,0.55)", "-strokewidth", 5, *scuffs, out(name))
    finish(name)


def mill_header():
    name = "MillHeader"
    w, h = 2048, 256
    magick("-size", f"{w}x{h}", "xc:rgb(40,62,84)", out(name))
    grain(name, 0.5, 61)
    rust = []
    import random
    rnd = random.Random(3)
    for _ in range(60):
        x, y = rnd.randint(0, w), rnd.randint(0, h)
        rust += ["-draw", f"ellipse {x},{y} {rnd.randint(10, 60)},{rnd.randint(4, 24)} 0,360"]
    magick(out(name), "-fill", "rgba(118,58,26,0.55)", *rust, out(name))
    rivets = []
    for x in range(24, w, 64):
        rivets += ["-draw", f"circle {x},22 {x + 7},22", "-draw", f"circle {x},234 {x + 7},234"]
    magick(out(name), "-fill", "rgb(26,40,56)", *rivets, out(name))
    magick(out(name), "-font", BOLD, "-pointsize", 120, "-fill", "rgb(226,218,190)", "-gravity", "center",
           "-annotate", "+0+4", "ROLLING MILL No. 3", out(name))
    for x0 in (0, w - 200):
        stripes = []
        for x in range(x0 - 60, x0 + 200, 56):
            stripes += ["-draw", f"polygon {x},40 {x + 28},40 {x + 88},216 {x + 60},216"]
        magick(out(name), "(", "-size", "200x176", "xc:rgb(232,180,24)", "-fill", "rgb(20,20,20)",
               *[a if a == "-draw" else "polygon " + " ".join(f"{int(p.split(',')[0]) - x0},{int(p.split(',')[1]) - 40}"
                 for p in a[8:].split()) for a in stripes], ")", "-geometry", f"+{x0}+40", "-composite", out(name))
    finish(name)


def board():
    name = "ChangeoverBoard"
    w, h = 1024, 700
    magick("-size", f"{w}x{h}", "xc:rgb(232,234,230)", out(name))
    grain(name, 0.12, 71)
    magick(out(name), "-font", MARKER, "-pointsize", 70, "-fill", "rgb(20,24,60)", "-gravity", "north",
           "-annotate", "+0+28", "CHANGEOVERS", out(name))
    times = ["21:00", "21:35", "22:10", "22:45", "23:20"]
    for k, (t, (act, paper, _, _)) in enumerate(zip(times, ACTS)):
        y = 150 + k * 96
        magick(out(name), "-font", HAND, "-pointsize", 66, "-fill", "rgb(20,24,60)", "-gravity", "northwest",
               "-annotate", f"+70+{y}", f"{t}   {act}", out(name))
        magick(out(name), "-fill", paper, "-stroke", "rgb(30,30,30)", "-strokewidth", 2,
               "-draw", f"rectangle 20,{y + 18} 54,{y + 60}", out(name))
    magick(out(name), "-font", MARKER, "-pointsize", 32, "-fill", "rgb(190,20,24)", "-gravity", "south",
           "-annotate", "-3x-3+0+26", "SAME DRUMMER ALL NIGHT - KEEP WING CLEAR", out(name))
    finish(name)


def hazard():
    name = "Hazard"
    w, h = 256, 64
    stripes = []
    for x in range(-64, 320, 64):
        stripes += ["-draw", f"polygon {x},0 {x + 32},0 {x + 96},64 {x + 64},64"]
    magick("-size", f"{w}x{h}", "xc:rgb(230,176,22)", "-fill", "rgb(22,22,22)", *stripes, out(name))
    grain(name, 0.3, 81)
    finish(name)


def crane_plate():
    name = "CranePlate"
    w, h = 1024, 256
    magick("-size", f"{w}x{h}", "xc:rgb(230,176,22)", out(name))
    grain(name, 0.35, 91)
    magick(out(name), "-font", BOLD, "-pointsize", 130, "-fill", "rgb(22,22,22)", "-gravity", "center",
           "-annotate", "+0+0", "SWL 60 T", out(name))
    finish(name)


def corrugated():
    """Grey (tinted by the material): vertical ribs with rust runs, tiled along the mill's walls."""
    name = "Corrugated"
    w, h = 256, 256
    ribs = []
    for k in range(4):
        x = k * 64
        ribs += ["-fill", "rgb(150,150,150)", "-draw", f"rectangle {x},0 {x + 20},{h}",
                 "-fill", "rgb(210,210,210)", "-draw", f"rectangle {x + 20},0 {x + 34},{h}",
                 "-fill", "rgb(90,90,90)", "-draw", f"rectangle {x + 34},0 {x + 52},{h}"]
    magick("-size", f"{w}x{h}", "xc:rgb(120,120,120)", *ribs, "-blur", "0x3", out(name))
    import random
    rnd = random.Random(17)
    runs = []
    for _ in range(14):
        x = rnd.randint(0, w); y = rnd.randint(0, h // 2)
        runs += ["-draw", f"rectangle {x},{y} {x + rnd.randint(3, 9)},{y + rnd.randint(40, 160)}"]
    magick(out(name), "-fill", "rgba(150,70,30,0.45)", *runs, out(name))
    grain(name, 0.4, 18)
    finish(name)


def windows():
    """A mill window: 3 x 4 wired panes, a few dark (broken, boarded); diffuse and emissive."""
    name = "MillWindow"
    w, h = 384, 512
    import random
    rnd = random.Random(23)
    panes = []
    for row in range(4):
        for col in range(3):
            x0, y0 = 16 + col * 120, 16 + row * 124
            v = rnd.random()
            c = "rgb(20,22,26)" if v < .18 else "rgb(%d,%d,%d)" % (120 + int(v * 60), 150 + int(v * 60), 190 + int(v * 50))
            panes += ["-fill", c, "-draw", f"rectangle {x0},{y0} {x0 + 108},{y0 + 112}"]
    magick("-size", f"{w}x{h}", "xc:rgb(14,16,18)", *panes, out(name))
    grain(name, 0.6, 24)
    finish(name)


def build():
    global M
    M = find_magick()
    if not M:
        print("story_steel_mill_textures: magick not found; keeping the existing textures")
        return
    os.makedirs(OUT, exist_ok=True)
    for i in range(5):
        sheet(i)
    case_stencil()
    tour_drop()
    mill_header()
    board()
    hazard()
    crane_plate()
    corrugated()
    windows()


def tex(name):
    return REL + name + ".png"


if __name__ == "__main__":
    build()
