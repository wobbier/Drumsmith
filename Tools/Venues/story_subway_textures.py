"""Draws the Last Train Busking Pitch's textures into Assets/Venues/StorySubway/Textures/ with
ImageMagick 7 (`magick`). Deterministic (fixed seeds, stripped metadata), so reruns give the same
bytes. Everything is drawn here: the subway tile, the terrazzo, the tactile edge, the station-name
band, the departure board's three states, the carriage flats (diffuse + window glow), the posters,
the busker's cardboard sign and the handwritten cafe transfer. Bellwoods is a made-up station; no
real brands or logos.

    python3 Tools/Venues/story_subway_textures.py   (redraws all; make_story_subway.py draws only if any is missing)
"""
import glob
import os
import random
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "Assets", "Venues", "StorySubway", "Textures")
TEX = "Assets/Venues/StorySubway/Textures/"
MARKER = os.path.join(ROOT, "Assets", "Fonts", "PermanentMarker-Regular.ttf")
HAND = os.path.join(ROOT, "Assets", "Fonts", "GochiHand-Regular.ttf")
HEAVY = "Noto-Sans-Black"
BOLD = "Noto-Sans-Bold"
MONO = "Liberation-Mono-Bold"

NAMES = ["WallTile", "BandTile", "NameWall", "Floor", "EdgeStrip", "Board1", "Board2", "Board3",
         "TrainSide", "TrainGlow", "PitchSign", "AdNightLine", "AdGig", "LineMap", "CardSign",
         "Transfer", "Tunnel", "Lining"]


def _magick_bin():
    found = shutil.which("magick")
    if found:
        return found
    for cand in sorted(glob.glob("/nix/store/*imagemagick-7*/bin/magick")):
        return cand
    return None


MAGICK = _magick_bin()


def magick(*args):
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


def grain(path, amount=0.25, seed=1):
    magick(path, "(", "+clone", "-seed", seed, "-attenuate", amount, "+noise", "Gaussian", "-colorspace", "gray", ")",
           "-compose", "overlay", "-composite", path)


def rgb(c):
    return "rgb(%d,%d,%d)" % tuple(int(max(0, min(255, v))) for v in c)


# ---- surfaces ---------------------------------------------------------------------------------

def tiles(name, w, h, cols, rows, base, var, grout, seed, bevel=True):
    """A grid of glazed tiles; each tile its own shade, a bright glaze lip on the top edge."""
    rnd = random.Random(seed)
    tw, th = w // cols, h // rows
    draws = []
    for r in range(rows):
        for c in range(cols):
            v = rnd.randint(-var, var)
            col = [base[i] + v + rnd.randint(-3, 3) for i in range(3)]
            x0, y0 = c * tw + 3, r * th + 3
            draws += ["-fill", rgb(col), "-draw", f"roundrectangle {x0},{y0} {x0 + tw - 6},{y0 + th - 6} 3,3"]
            if bevel:
                draws += ["-fill", rgb([min(255, k + 22) for k in col]), "-draw", f"rectangle {x0 + 3},{y0 + 1} {x0 + tw - 9},{y0 + 4}"]
    magick("-size", f"{w}x{h}", f"xc:{rgb(grout)}", *draws, out(name))


def wall_tile():
    """1.2 x 1.2 m of cream subway tile, 8 across and 16 down, grimy."""
    tiles("WallTile", 512, 512, 8, 16, (214, 208, 188), 9, (92, 90, 84), 3)
    magick(out("WallTile"), "(", "-size", "512x512", "-seed", 7, "plasma:fractal", "-colorspace", "gray", "-blur", "0x6",
           "-auto-level", "+level", "80%,100%", ")", "-compose", "multiply", "-composite", out("WallTile"))
    grain(out("WallTile"), 0.35, 4)
    finish("WallTile")


def band_tile():
    """The line's colour band: deep teal tile with a mustard pinstripe top and bottom."""
    tiles("BandTile", 512, 128, 8, 2, (28, 104, 104), 8, (24, 40, 40), 5)
    magick(out("BandTile"), "-fill", rgb((196, 150, 46)), "-draw", "rectangle 0,0 512,9", "-draw", "rectangle 0,118 512,128",
           out("BandTile"))
    grain(out("BandTile"), 0.3, 6)
    finish("BandTile")


def name_wall():
    """The trackside wall's name band: BELLWOODS in cream tile on teal, 12 m long."""
    w, h = 2048, 384
    tiles("NameWall", w, h, 64, 6, (26, 98, 100), 7, (20, 36, 38), 8)
    magick(out("NameWall"), "-fill", rgb((196, 150, 46)), "-draw", f"rectangle 0,0 {w},12", "-draw", f"rectangle 0,{h - 12} {w},{h}",
           "-gravity", "center", "-font", HEAVY, "-pointsize", 250, "-fill", rgb((226, 218, 196)),
           "-annotate", "+0+10", "BELLWOODS", out("NameWall"))
    # Re-cut the grout through the letters so they read as tile, not paint.
    lines = []
    for c in range(1, 64):
        lines += ["-draw", f"line {c * 32},0 {c * 32},{h}"]
    for r in range(1, 6):
        lines += ["-draw", f"line 0,{r * 64} {w},{r * 64}"]
    magick(out("NameWall"), "-stroke", "rgba(20,36,38,0.85)", "-strokewidth", 4, *lines, out("NameWall"))
    grain(out("NameWall"), 0.3, 9)
    finish("NameWall")


def floor():
    """2 x 2 m of worn terrazzo in 0.5 m squares, darker where the feet go."""
    s = 512
    magick("-size", f"{s}x{s}", "xc:rgb(112,110,104)", "(", "-size", f"{s}x{s}", "-seed", 12, "plasma:fractal", "-colorspace", "gray",
           "-blur", "0x4", "-auto-level", "+level", "72%,100%", ")", "-compose", "multiply", "-composite", out("Floor"))
    rnd = random.Random(13)
    chips = []
    for _ in range(900):
        x, y, r = rnd.randint(0, s), rnd.randint(0, s), rnd.choice((1, 1, 2, 2, 3))
        c = rnd.choice(((170, 166, 156), (58, 56, 52), (140, 120, 96), (190, 186, 176)))
        chips += ["-fill", rgb(c), "-draw", f"circle {x},{y} {x + r},{y}"]
    joints = []
    for k in range(1, 4):
        joints += ["-draw", f"line {k * 128},0 {k * 128},{s}", "-draw", f"line 0,{k * 128} {s},{k * 128}"]
    magick(out("Floor"), *chips, "-stroke", "rgb(60,58,54)", "-strokewidth", 3, *joints, out("Floor"))
    grain(out("Floor"), 0.5, 14)
    finish("Floor")


def edge_strip():
    """The platform edge: safety yellow with raised tactile dots."""
    s = 256
    magick("-size", "32x32", "xc:rgb(214,170,24)", "-fill", "rgb(236,196,52)", "-draw", "circle 16,16 16,24",
           "-fill", "rgb(150,116,14)", "-draw", "arc 8,8 24,24 20,110",
           "-write", "mpr:dot", "+delete", "-size", f"{s}x{s}", "tile:mpr:dot", out("EdgeStrip"))
    grain(out("EdgeStrip"), 0.45, 15)
    finish("EdgeStrip")


def tunnel():
    """Sooty concrete of the tunnel and track bed."""
    s = 256
    magick("-size", f"{s}x{s}", "xc:rgb(40,38,36)", "(", "-size", f"{s}x{s}", "-seed", 16, "plasma:fractal", "-colorspace", "gray",
           "-blur", "0x2", "-auto-level", "+level", "55%,100%", ")", "-compose", "multiply", "-composite", out("Tunnel"))
    grain(out("Tunnel"), 0.7, 17)
    finish("Tunnel")


def lining():
    """Crushed red plush for the inside of the open case."""
    s = 128
    magick("-size", f"{s}x{s}", "xc:rgb(122,14,30)", "(", "-size", f"{s}x{s}", "-seed", 18, "plasma:fractal", "-colorspace", "gray",
           "-blur", "0x1", "-auto-level", "+level", "65%,100%", ")", "-compose", "multiply", "-composite", out("Lining"))
    finish("Lining")


# ---- the departure board ----------------------------------------------------------------------

def board(name, rows, seed):
    """Amber dot-matrix on black, three rows; a glow under the letters."""
    w, h = 1024, 320
    text = []
    for i, (left, right) in enumerate(rows):
        y = 34 + i * 96
        text += ["-gravity", "northwest", "-annotate", f"+40+{y}", left]
        if right:
            text += ["-gravity", "northeast", "-annotate", f"+40+{y}", right]
    font = ["-font", MONO, "-pointsize", 68]
    magick("-size", f"{w}x{h}", "xc:rgb(6,6,8)", "(", "-size", f"{w}x{h}", "xc:none", *font, "-fill", "rgb(255,150,30)", *text,
           "-blur", "0x7", ")", "-compose", "screen", "-composite", *font, "-fill", "rgb(255,176,60)", *text, out(name))
    # The dot matrix: a black grid laid over everything breaks the strokes into LEDs.
    magick("-size", "8x8", "xc:black", "-fill", "white", "-draw", "circle 4,4 4,7", "-write", "mpr:led", "+delete",
           "-size", f"{w}x{h}", "tile:mpr:led", tmp("led"))
    magick(out(name), tmp("led"), "-compose", "multiply", "-composite", out(name))
    magick(out(name), "-fill", "rgb(70,70,76)", "-draw", f"rectangle 0,0 {w},6", "-draw", f"rectangle 0,{h - 6} {w},{h}",
           "-draw", "rectangle 0,0 6,320", "-draw", f"rectangle {w - 6},0 {w},{h}", out(name))
    finish(name)


def boards():
    board("Board1", [("BELLWOODS", "23:52"), ("1 EASTBOUND", "NOW"), ("2 WESTBOUND", "9 MIN")], 21)
    board("Board2", [("BELLWOODS", "00:07"), ("2 WESTBOUND", "1 MIN"), ("LAST TRAIN", "TONIGHT")], 22)
    board("Board3", [("BELLWOODS", "00:31"), ("SERVICE ENDED", ""), ("FIRST TRAIN", "05:58")], 23)


# ---- the carriage flats -----------------------------------------------------------------------

def train():
    """One carriage side, 10.4 x 3.2 m: brushed steel, a teal stripe, four doors, windows lit warm
    from inside with a few passengers' silhouettes. TrainGlow is the same layout as an emissive
    mask (windows and the door lamps lit, everything else black)."""
    w, h = 2048, 640
    rnd = random.Random(31)
    body = ["-fill", "rgb(150,152,156)", "-draw", f"rectangle 0,0 {w},{h}"]
    glow = []
    seams = []
    for k in range(0, w, 128):
        seams += ["-draw", f"line {k},40 {k},{h - 40}"]
    stripe = ["-fill", "rgb(26,110,112)", "-draw", f"rectangle 0,{h - 170} {w},{h - 130}",
              "-fill", "rgb(196,150,46)", "-draw", f"rectangle 0,{h - 128} {w},{h - 120}"]
    roof = ["-fill", "rgb(86,88,92)", "-draw", f"rectangle 0,0 {w},38", "-fill", "rgb(46,46,50)", "-draw", f"rectangle 0,{h - 40} {w},{h}"]
    doors = [160, 680, 1240, 1760]
    win = []
    people = []
    for d in doors:
        body += ["-fill", "rgb(120,122,128)", "-draw", f"rectangle {d},80 {d + 150},{h - 44}",
                 "-fill", "rgb(70,72,76)", "-draw", f"line {d + 75},80 {d + 75},{h - 44}"]
        for dx in (14, 89):
            win.append((d + dx, 118, d + dx + 47, 330))
        glow += ["-fill", "rgb(255,120,40)", "-draw", f"rectangle {d + 64},54 {d + 86},70"]
    spans = [(0, 160), (310, 680), (830, 1240), (1390, 1760), (1910, w)]
    for a, b in spans:
        x = a + 24
        while x + 150 < b - 10:
            win.append((x, 110, x + 150, 300))
            x += 182
    for x0, y0, x1, y1 in win:
        body += ["-fill", "rgb(40,40,44)", "-draw", f"roundrectangle {x0 - 6},{y0 - 6} {x1 + 6},{y1 + 6} 10,10",
                 "-fill", "rgb(252,232,186)", "-draw", f"roundrectangle {x0},{y0} {x1},{y1} 8,8"]
        glow += ["-fill", "rgb(255,236,190)", "-draw", f"roundrectangle {x0},{y0} {x1},{y1} 8,8"]
        # Grab rails and the odd passenger, dark against the lit glass.
        people += ["-fill", "rgb(150,140,120)", "-draw", f"rectangle {x0},{y0 + 22} {x1},{y0 + 26}"]
        if x1 - x0 > 100 and rnd.random() < 0.45:
            cx = rnd.randint(x0 + 30, x1 - 30)
            top = rnd.randint(y0 + 50, y0 + 90)
            people += ["-fill", "rgb(52,44,40)", "-draw", f"circle {cx},{top} {cx + 18},{top}",
                       "-draw", f"roundrectangle {cx - 34},{top + 18} {cx + 34},{y1} 18,18"]
    magick("-size", f"{w}x{h}", "xc:black", *body, *roof, *stripe, "-stroke", "rgba(90,92,96,0.7)", "-strokewidth", 2, *seams,
           "-stroke", "none", *people, out("TrainSide"))
    magick(out("TrainSide"), "(", "-size", f"{w}x{h}", "-seed", 32, "plasma:fractal", "-colorspace", "gray", "-blur", "0x3",
           "-auto-level", "+level", "84%,100%", ")", "-compose", "multiply", "-composite", out("TrainSide"))
    magick(out("TrainSide"), "-gravity", "northwest", "-font", HEAVY, "-pointsize", 46, "-fill", "rgb(26,110,112)",
           "-annotate", f"+1460+{h - 118}", "5127", out("TrainSide"))
    finish("TrainSide")
    magick("-size", f"{w}x{h}", "xc:black", *glow, *people, out("TrainGlow"))
    finish("TrainGlow")


# ---- paper ------------------------------------------------------------------------------------

def pitch_sign():
    """The enamel plate on the pillar that makes this a licensed pitch."""
    s = 512
    magick("-size", f"{s}x{s}", "xc:rgb(26,104,106)", "-fill", "none", "-stroke", "rgb(232,224,200)", "-strokewidth", 14,
           "-draw", "roundrectangle 18,18 494,494 30,30", "-stroke", "none", "-fill", "rgb(232,224,200)",
           "-draw", "circle 256,214 256,92", "-fill", "rgb(26,104,106)",
           "-draw", "ellipse 226,262 40,28 0,360", "-draw", "rectangle 254,140 268,262",
           "-draw", "polygon 268,140 318,170 318,196 268,168",
           "-gravity", "south", "-font", HEAVY, "-pointsize", 66, "-fill", "rgb(232,224,200)",
           "-annotate", "+0+92", "BUSKING", "-font", BOLD, "-pointsize", 46, "-annotate", "+0+40", "PITCH 4", out("PitchSign"))
    grain(out("PitchSign"), 0.25, 41)
    finish("PitchSign")


def ad_night_line():
    """A transit poster: the night bus line, sodium orange on navy."""
    w, h = 512, 768
    rnd = random.Random(42)
    stars = []
    for _ in range(40):
        x, y = rnd.randint(0, w), rnd.randint(0, 360)
        stars += ["-draw", f"point {x},{y}"]
    magick("-size", f"{w}x{h}", "gradient:rgb(18,24,58)-rgb(52,30,70)", "-fill", "rgb(240,220,180)", *stars,
           "-fill", "rgb(250,170,60)", "-draw", "circle 360,200 360,140",
           "-fill", "rgb(20,18,30)", "-draw", "polygon 0,470 60,420 120,440 160,380 230,400 300,350 380,390 440,360 512,400 512,768 0,768",
           "-fill", "rgb(250,170,60)", "-draw", "rectangle 0,560 512,572",
           "-gravity", "north", "-font", HEAVY, "-pointsize", 70, "-fill", "rgb(250,190,90)", "-annotate", "+0+600", "NIGHT LINE",
           "-font", BOLD, "-pointsize", 30, "-fill", "rgb(230,226,214)", "-annotate", "+0+690", "every 30 min after the last train",
           out("AdNightLine"))
    grain(out("AdNightLine"), 0.4, 43)
    finish("AdNightLine")


def ad_gig():
    """A made-up band's gig poster, half torn."""
    w, h = 512, 768
    magick("-size", f"{w}x{h}", "xc:rgb(222,58,46)", "-fill", "rgb(30,20,26)", "-draw", "circle 256,300 256,120",
           "-fill", "rgb(222,58,46)", "-draw", "circle 256,300 256,200", "-fill", "rgb(30,20,26)", "-draw", "circle 256,300 256,280",
           "-gravity", "north", "-font", HEAVY, "-pointsize", 76, "-fill", "rgb(250,236,210)", "-annotate", "+0+30", "PAPER",
           "-annotate", "+0+520", "LANTERNS", "-font", BOLD, "-pointsize", 34, "-fill", "rgb(30,20,26)",
           "-annotate", "+0+630", "LIVE AT THE BACK ROOM", "-annotate", "+0+680", "SAT 14 DEC",
           out("AdGig"))
    magick(out("AdGig"), "-fill", "rgb(214,208,188)", "-draw", "polygon 380,768 420,700 470,720 512,650 512,768", out("AdGig"))
    grain(out("AdGig"), 0.5, 44)
    finish("AdGig")


def line_map():
    """The line map: one teal line, made-up stops, Bellwoods ringed."""
    w, h = 1024, 384
    stops = ["HARBOUR", "MARKET", "LINDEN", "BELLWOODS", "GRANGE", "ASHDALE", "MAPLE", "WESTWAY"]
    dots, labels = [], []
    for i, n in enumerate(stops):
        x = 70 + i * 116
        big = n == "BELLWOODS"
        dots += ["-fill", "white", "-stroke", "rgb(20,20,24)", "-strokewidth", 6, "-draw", f"circle {x},190 {x + (22 if big else 14)},190"]
        labels += ["-stroke", "none", "-fill", "rgb(196,40,30)" if big else "rgb(20,20,24)", "-annotate", f"-30x-30+{x - 8}+{150}", n]
    magick("-size", f"{w}x{h}", "xc:rgb(238,234,222)", "-fill", "rgb(26,110,112)", "-draw", "rectangle 60,180 900,200", *dots,
           "-font", BOLD, "-pointsize", 26, *labels, "-gravity", "northwest", "-font", HEAVY, "-pointsize", 40, "-fill", "rgb(20,20,24)",
           "-annotate", "+40+300", "LINE 2  WESTBOUND", "-fill", "rgb(196,40,30)", "-font", BOLD, "-pointsize", 28,
           "-annotate", "+560+312", "YOU ARE HERE: BELLWOODS", out("LineMap"))
    grain(out("LineMap"), 0.3, 45)
    finish("LineMap")


def card_sign():
    """Cardboard torn off a box, propped against the bucket."""
    w, h = 512, 384
    magick("-size", f"{w}x{h}", "xc:rgb(168,126,80)", "(", "-size", "64x384", "-seed", 51, "plasma:fractal", "-colorspace", "gray",
           "-resize", f"{w}x{h}!", "-motion-blur", "0x6+90", "-auto-level", "+level", "80%,100%", ")", "-compose", "multiply",
           "-composite", "-gravity", "center", "-font", MARKER, "-pointsize", 62, "-fill", "rgb(20,18,16)",
           "-annotate", "-4x-4+0-80", "FIRST TIME", "-annotate", "-3x-3+0+0", "BUSKING!", "-pointsize", 40,
           "-fill", "rgb(170,30,30)", "-annotate", "-2x-2+0+90", "thank you :)", out("CardSign"))
    grain(out("CardSign"), 0.5, 52)
    finish("CardSign")


def transfer():
    """A paper transfer with a cafe's name and a time written across it by hand."""
    w, h = 256, 512
    magick("-size", f"{w}x{h}", "xc:rgb(238,226,200)", "-fill", "rgb(196,60,50)", "-draw", "rectangle 0,0 256,70",
           "-gravity", "north", "-font", HEAVY, "-pointsize", 44, "-fill", "rgb(250,240,220)", "-annotate", "+0+10", "TRANSFER",
           "-font", MONO, "-pointsize", 22, "-fill", "rgb(80,70,60)", "-annotate", "+0+86", "LINE 2  00:14",
           "-font", HAND, "-pointsize", 52, "-fill", "rgb(30,40,110)", "-annotate", "-8x-8+0+170", "Cafe Lune",
           "-pointsize", 44, "-annotate", "-6x-6+0+250", "Fri 9pm", "-annotate", "-6x-6+0+320", "ask for Ruth",
           "-pointsize", 40, "-annotate", "-4x-4+0+410", "you're good -M", out("Transfer"))
    grain(out("Transfer"), 0.4, 61)
    finish("Transfer")


DRAW = {"WallTile": wall_tile, "BandTile": band_tile, "NameWall": name_wall, "Floor": floor, "EdgeStrip": edge_strip,
        "Board1": boards, "TrainSide": train, "PitchSign": pitch_sign, "AdNightLine": ad_night_line, "AdGig": ad_gig,
        "LineMap": line_map, "CardSign": card_sign, "Transfer": transfer, "Tunnel": tunnel, "Lining": lining}


def make_all(force=False):
    """Draws every texture; without magick it keeps what is on disk (and fails if any is missing)."""
    os.makedirs(OUT, exist_ok=True)
    if MAGICK is None:
        missing = [n for n in NAMES if not os.path.exists(out(n))]
        if missing:
            sys.exit("magick not found and textures missing: " + ", ".join(missing))
        print("magick not found; keeping the textures on disk")
        return
    missing = [n for n in NAMES if not os.path.exists(out(n))]
    if not force and not missing:
        return
    for fn in DRAW.values():
        fn()
    # The game prefers a cooked .dds twin even when the .png is newer: drop them so they re-cook.
    for n in NAMES:
        for twin in (out(n) + ".dds", out(n) + ".dds.d"):
            if os.path.isdir(twin):
                shutil.rmtree(twin)
            elif os.path.exists(twin):
                os.remove(twin)


if __name__ == "__main__":
    make_all(force=True)
    print("wrote", OUT)
