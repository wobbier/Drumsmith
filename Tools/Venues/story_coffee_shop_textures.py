"""The Millennial Coffee Shop's painted surfaces (Assets/Venues/StoryCoffeeShop/Textures/*.png), drawn
with ImageMagick 7. Deterministic: fixed seeds and stripped metadata, so a rerun gives the same files.

The café is made up ("Second Pour"); the chalk is the game's Gochi Hand (OFL), the signwriting
Permanent Marker (Apache 2.0) and the system's Noto faces.
"""
import glob
import os
import random
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "Assets", "Venues", "StoryCoffeeShop", "Textures")
HAND = os.path.join(ROOT, "Assets", "Fonts", "GochiHand-Regular.ttf")
MARKER = os.path.join(ROOT, "Assets", "Fonts", "PermanentMarker-Regular.ttf")
SERIF = "Noto-Serif-Display-Black"
SANS = "Noto-Sans-Bold"


def _magick_bin():
    found = shutil.which("magick")
    if found:
        return found
    for path in sorted(glob.glob("/nix/store/*imagemagick-7*/bin/magick")):
        return path
    sys.exit("ImageMagick 7 (magick) not found")


MAGICK = None


def magick(*args):
    global MAGICK
    MAGICK = MAGICK or _magick_bin()
    cmd = [MAGICK, *[str(a) for a in args]]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"magick failed: {' '.join(cmd)}\n{r.stderr}")


def out(name):
    return os.path.join(OUT, name + ".png")


def tmp(name):
    return os.path.join(OUT, "_" + name + ".png")


def finish(name):
    magick(out(name), "-strip", "-define", "png:exclude-chunks=date,time", out(name))
    for t in glob.glob(os.path.join(OUT, "_*.png")):
        os.remove(t)


def mottle(name, w, h, seed, lo="80%"):
    magick("-size", f"{w}x{h}", "-seed", seed, "plasma:fractal", "-colorspace", "gray", "-blur", "0x3",
           "-auto-level", "+level", f"{lo},100%", tmp("mottle"))
    magick(out(name), tmp("mottle"), "-compose", "multiply", "-composite", out(name))


# ---- surfaces ------------------------------------------------------------------------------------

def brick():
    """Old red brick, stretcher bond, whitewash ghosting: 1024 x 512 is 2.0 x 1.0 m (16 courses)."""
    rnd = random.Random(31)
    w, h, bw, bh, m = 1024, 512, 128, 32, 4
    draws = []
    for row in range(h // bh):
        shift = 0 if row % 2 == 0 else bw // 2
        for col in range(-1, w // bw + 1):
            x0 = col * bw + shift
            base = rnd.choice([(150, 64, 44), (132, 56, 40), (164, 78, 52), (118, 50, 38), (142, 70, 50), (170, 92, 64)])
            v = rnd.randint(-12, 12)
            c = tuple(max(0, min(255, b + v)) for b in base)
            draws += ["-fill", "rgb(%d,%d,%d)" % c, "-draw",
                      f"rectangle {x0 + m},{row * bh + m} {x0 + bw - m},{row * bh + bh - m}"]
            if rnd.random() < 0.18:  # a chipped corner
                draws += ["-fill", "rgb(96,44,34)", "-draw", f"rectangle {x0 + m},{row * bh + m} {x0 + m + 9},{row * bh + m + 6}"]
    magick("-size", f"{w}x{h}", "xc:rgb(176,166,150)", *draws, out("Brick"))
    mottle("Brick", w, h, 7, "72%")
    # Whitewash left over from the last tenant, heavier toward the floor.
    magick("-size", f"{w}x{h}", "-seed", 12, "plasma:fractal", "-colorspace", "gray", "-blur", "0x6", "-auto-level",
           "-level", "55%,95%", tmp("wash"))
    magick(out("Brick"), "(", "-size", f"{w}x{h}", "xc:rgb(222,212,196)", tmp("wash"), "-alpha", "off",
           "-compose", "copy-opacity", "-composite", "-channel", "A", "-evaluate", "multiply", "0.35", "+channel", ")",
           "-compose", "over", "-composite", out("Brick"))
    finish("Brick")


def floorboards():
    """Worn oak boards along z: 1024 x 1024 is 2 x 2 m, eight boards of 0.25 m."""
    rnd = random.Random(5)
    w = h = 1024
    bw = 128
    draws = []
    for col in range(w // bw):
        y = -rnd.randint(0, 400)
        while y < h:
            length = rnd.randint(300, 700)
            tone = rnd.choice([(150, 98, 58), (138, 88, 52), (164, 110, 66), (128, 82, 50), (156, 104, 60)])
            draws += ["-fill", "rgb(%d,%d,%d)" % tone, "-draw", f"rectangle {col * bw + 3},{y + 3} {col * bw + bw - 3},{y + length - 3}"]
            y += length
    magick("-size", f"{w}x{h}", "xc:rgb(58,38,24)", *draws, out("Floor"))
    # Grain along the boards, then traffic wear down the middle of each.
    magick("-size", f"{w}x{h}", "-seed", 3, "xc:", "+noise", "Random", "-colorspace", "gray", "-motion-blur", "0x40+90",
           "-auto-level", "+level", "84%,100%", tmp("grain"))
    magick(out("Floor"), tmp("grain"), "-compose", "multiply", "-composite", out("Floor"))
    mottle("Floor", w, h, 9, "86%")
    finish("Floor")


def tiles():
    """White subway tile behind the bar: 512 x 512 is 0.6 x 0.6 m (0.15 x 0.075 m tiles)."""
    w = h = 512
    tw, th = 128, 64
    rnd = random.Random(17)
    draws = []
    for row in range(h // th):
        shift = 0 if row % 2 == 0 else tw // 2
        for col in range(-1, w // tw + 1):
            x0 = col * tw + shift
            v = rnd.randint(-6, 4)
            draws += ["-fill", "rgb(%d,%d,%d)" % (236 + v, 234 + v, 226 + v), "-draw",
                      f"roundrectangle {x0 + 3},{row * th + 3} {x0 + tw - 3},{row * th + th - 3} 6,6"]
    magick("-size", f"{w}x{h}", "xc:rgb(150,146,138)", *draws, out("Tile"))
    finish("Tile")


# ---- signs ---------------------------------------------------------------------------------------

def chalk(*args):
    """A text draw in chalk: font, size, colour, position, words."""
    return list(args)


def chalkboard():
    """The menu over the bar, 1600 x 800 = 2.8 x 1.4 m. Today's special is the gig."""
    w, h = 1600, 800
    magick("-size", f"{w}x{h}", "xc:rgb(30,36,33)", out("Chalkboard"))
    # Old chalk smudged across the slate.
    magick("-size", f"{w}x{h}", "-seed", 21, "plasma:fractal", "-colorspace", "gray", "-blur", "0x14", "-auto-level",
           "-level", "40%,100%", tmp("smudge"))
    magick(out("Chalkboard"), "(", "-size", f"{w}x{h}", "xc:rgb(120,128,124)", tmp("smudge"), "-alpha", "off",
           "-compose", "copy-opacity", "-composite", "-channel", "A", "-evaluate", "multiply", "0.22", "+channel", ")",
           "-compose", "over", "-composite", out("Chalkboard"))
    W = "rgb(236,234,224)"
    PINK = "rgb(246,160,178)"
    YEL = "rgb(250,222,120)"
    BLUE = "rgb(150,206,230)"
    menu = [("ESPRESSO", "3.00"), ("CORTADO", "3.75"), ("FLAT WHITE", "4.25"), ("OAT LATTE", "4.75"),
            ("POUR OVER", "5.00"), ("CHAI", "4.25"), ("BREAKFAST SANDWICH", "6.50")]
    draws = ["-font", MARKER, "-fill", W, "-pointsize", 74, "-annotate", "+70+120", "SECOND POUR",
             "-stroke", W, "-strokewidth", 4, "-draw", "line 70,146 650,146", "-stroke", "none",
             "-font", HAND, "-pointsize", 50]
    for i, (item, price) in enumerate(menu):
        y = 225 + i * 74
        draws += ["-fill", W, "-annotate", f"+80+{y}", item, "-fill", YEL, "-annotate", f"+600+{y}", price]
    # Right half: today.
    draws += ["-fill", YEL, "-font", MARKER, "-pointsize", 66, "-annotate", "+900+130", "TODAY",
              "-fill", PINK, "-font", HAND, "-pointsize", 100, "-annotate", "+880+265", "an intimate",
              "-annotate", "+890+380", "acoustic session",
              "-fill", W, "-pointsize", 54, "-annotate", "+930+490", "11 till the beans run out",
              "-fill", BLUE, "-pointsize", 46, "-annotate", "+930+700", "brushes only please x"]
    # A doodled snare and a steaming cup.
    draws += ["-fill", "none", "-stroke", W, "-strokewidth", 5,
              "-draw", "ellipse 1430,590 70,20 0,360", "-draw", "line 1360,590 1360,650", "-draw", "line 1500,590 1500,650",
              "-draw", "ellipse 1430,650 70,20 0,180",
              "-draw", "line 1380,520 1440,570", "-draw", "line 1490,515 1430,568",
              "-stroke", PINK, "-draw", "roundrectangle 1180,560 1260,640 10,10", "-draw", "arc 1250,575 1290,615 -90,90",
              "-draw", "bezier 1200,545 1190,520 1215,505 1205,480", "-draw", "bezier 1235,545 1225,520 1250,505 1240,480"]
    magick(out("Chalkboard"), *draws, out("Chalkboard"))
    magick(out("Chalkboard"), "-blur", "0x0.8", out("Chalkboard"))
    finish("Chalkboard")


def sandwich_board():
    """The A-board by the door, 512 x 768 = 0.6 x 0.9 m."""
    w, h = 512, 768
    W = "rgb(238,236,228)"
    magick("-size", f"{w}x{h}", "xc:rgb(32,36,34)",
           "-font", MARKER, "-fill", "rgb(250,222,120)", "-pointsize", 76, "-gravity", "north", "-annotate", "+0+60", "LIVE",
           "-annotate", "+0+150", "MUSIC",
           "-font", HAND, "-fill", W, "-pointsize", 60, "-annotate", "+0+280", "today, 11am",
           "-fill", "rgb(246,160,178)", "-pointsize", 54, "-annotate", "+0+390", "one drummer",
           "-annotate", "+0+450", "two brushes",
           "-fill", W, "-pointsize", 44, "-annotate", "+0+580", "come in, it's warm",
           "-stroke", W, "-strokewidth", 4, "-fill", "none", "-draw", "roundrectangle 24,24 488,744 18,18",
           out("SandwichBoard"))
    magick(out("SandwichBoard"), "-blur", "0x0.7", out("SandwichBoard"))
    finish("SandwichBoard")


def street():
    """The view through the front windows: a sunny street, 2048 x 640 = 14 x 4.4 m, bright (emissive)."""
    rnd = random.Random(44)
    w, h = 2048, 640
    magick("-size", f"{w}x{h}", "gradient:rgb(186,214,236)-rgb(252,236,206)", out("Street"))
    draws = []
    x = -30
    fronts = [(214, 190, 160), (176, 96, 76), (226, 214, 190), (150, 160, 150), (196, 120, 90), (232, 200, 150), (168, 140, 120)]
    while x < w:
        bw = rnd.randint(220, 360)
        top = rnd.randint(30, 150)
        c = rnd.choice(fronts)
        draws += ["-fill", "rgb(%d,%d,%d)" % c, "-draw", f"rectangle {x},{top} {x + bw},{h}"]
        draws += ["-fill", "rgb(%d,%d,%d)" % tuple(int(v * .8) for v in c), "-draw", f"rectangle {x},{top} {x + bw},{top + 14}"]
        for wy in range(top + 50, 420, 95):
            for wx in range(x + 30, x + bw - 50, 78):
                draws += ["-fill", "rgb(84,104,122)", "-draw", f"rectangle {wx},{wy} {wx + 44},{wy + 60}",
                          "-fill", "rgb(236,232,220)", "-draw", f"rectangle {wx},{wy + 54} {wx + 44},{wy + 62}"]
        # A shopfront at street level with an awning.
        aw = rnd.choice(["rgb(46,112,96)", "rgb(170,52,48)", "rgb(60,70,120)", "rgb(220,170,60)"])
        draws += ["-fill", "rgb(70,84,96)", "-draw", f"rectangle {x + 20},440 {x + bw - 20},560",
                  "-fill", aw, "-draw", f"polygon {x + 10},420 {x + bw - 10},420 {x + bw - 24},452 {x + 24},452"]
        x += bw
    # A street tree, the kerb, the road.
    draws += ["-fill", "rgb(98,74,52)", "-draw", "rectangle 1190,300 1206,580",
              "-fill", "rgb(92,140,70)", "-draw", "circle 1198,260 1290,260", "-fill", "rgb(120,168,84)", "-draw", "circle 1160,230 1220,230",
              "-fill", "rgb(170,166,156)", "-draw", f"rectangle 0,560 {w},592",
              "-fill", "rgb(90,92,96)", "-draw", f"rectangle 0,592 {w},{h}",
              "-fill", "rgb(236,226,160)", "-draw", "rectangle 200,612 330,618", "-draw", "rectangle 700,612 830,618",
              "-draw", "rectangle 1200,612 1330,618", "-draw", "rectangle 1700,612 1830,618"]
    # A bike locked to the rack.
    draws += ["-fill", "none", "-stroke", "rgb(40,44,52)", "-strokewidth", 5, "-draw", "circle 560,560 560,530",
              "-draw", "circle 650,560 650,530", "-draw", "polyline 560,560 600,520 650,560 610,560 600,520 590,505",
              "-stroke", "none"]
    magick(out("Street"), *draws, out("Street"))
    magick(out("Street"), "-blur", "0x1.2", "-modulate", "104,92", out("Street"))
    finish("Street")


def print_art(name, seed, palette):
    """Small framed prints for the brick wall, 256 x 320."""
    rnd = random.Random(seed)
    w, h = 256, 320
    draws = []
    bg = palette[0]
    for i in range(5):
        c = palette[1 + i % (len(palette) - 1)]
        kind = rnd.choice(["circle", "rect", "hill"])
        x, y = rnd.randint(20, 230), rnd.randint(30, 290)
        r = rnd.randint(30, 80)
        if kind == "circle":
            draws += ["-fill", c, "-draw", f"circle {x},{y} {x + r},{y}"]
        elif kind == "rect":
            draws += ["-fill", c, "-draw", f"rectangle {x - r},{y - r // 2} {x + r},{y + r // 2}"]
        else:
            draws += ["-fill", c, "-draw", f"polygon 0,320 {x},{y} 256,320"]
    magick("-size", f"{w}x{h}", f"xc:{bg}", *draws, "-bordercolor", "rgb(244,240,230)", "-border", 18, out(name))
    finish(name)


def setlist():
    """The setlist taped by the kit, under a foil-wrapped breakfast sandwich, 256 x 360."""
    magick("-size", "256x360", "xc:rgb(246,244,236)", "-font", MARKER, "-fill", "rgb(30,30,40)", "-pointsize", 30,
           "-annotate", "+24+60", "RAMONA", "-annotate", "+24+120", "CACTUS", "-annotate", "+24+180", "KISS ME",
           "-annotate", "+24+240", "STOLEN DANCE", "-annotate", "+24+300", "LITTLE TALKS", out("Setlist"))
    finish("Setlist")


def window_letters():
    """Gold leaf on the front glass, read from inside (mirrored), with alpha: 1024 x 256."""
    magick("-size", "1024x256", "xc:none", "-font", SERIF, "-fill", "rgb(214,170,80)", "-stroke", "rgb(120,84,30)",
           "-strokewidth", 2, "-pointsize", 120, "-gravity", "center", "-annotate", "+0-20", "Second Pour",
           "-font", SANS, "-stroke", "none", "-pointsize", 34, "-annotate", "+0+80", "COFFEE  ·  TOAST  ·  RECORDS",
           "-flop", out("WindowLetters"))
    finish("WindowLetters")


def laptop_lid():
    """The back of the laptop lid: stickers, 256 x 176."""
    magick("-size", "256x176", "xc:rgb(184,188,194)",
           "-fill", "rgb(246,160,178)", "-draw", "circle 70,70 104,70",
           "-fill", "rgb(250,222,120)", "-draw", "roundrectangle 140,40 220,90 10,10",
           "-fill", "rgb(90,170,150)", "-draw", "polygon 120,150 160,100 200,150",
           "-font", MARKER, "-fill", "rgb(40,40,48)", "-pointsize", 22, "-annotate", "+148+74", "TOAST",
           out("LaptopLid"))
    finish("LaptopLid")


def coffee_bags():
    """A shelf row of kraft coffee bags with hand-stamped labels, 512 x 160."""
    rnd = random.Random(8)
    draws = []
    for i in range(6):
        x = 8 + i * 84
        draws += ["-fill", "rgb(%d,%d,%d)" % (rnd.randint(170, 196), rnd.randint(130, 150), rnd.randint(90, 104)),
                  "-draw", f"roundrectangle {x},10 {x + 72},158 6,6",
                  "-fill", rnd.choice(["rgb(46,112,96)", "rgb(170,52,48)", "rgb(240,236,226)", "rgb(60,70,120)"]),
                  "-draw", f"rectangle {x + 10},70 {x + 62},120"]
    magick("-size", "512x168", "xc:none", *draws, out("CoffeeBags"))
    finish("CoffeeBags")


ALL = [brick, floorboards, tiles, chalkboard, sandwich_board, street, setlist, window_letters, laptop_lid, coffee_bags]


def make_all():
    os.makedirs(OUT, exist_ok=True)
    for fn in ALL:
        fn()
    print_art("PrintA", 2, ["rgb(236,222,200)", "rgb(224,120,90)", "rgb(46,112,96)", "rgb(240,190,90)"])
    print_art("PrintB", 6, ["rgb(40,52,70)", "rgb(246,160,178)", "rgb(250,222,120)", "rgb(150,206,230)"])
    print_art("PrintC", 9, ["rgb(226,214,190)", "rgb(170,52,48)", "rgb(60,70,120)", "rgb(32,36,34)"])


if __name__ == "__main__":
    make_all()
    print("wrote", OUT)
