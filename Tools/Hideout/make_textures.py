#!/usr/bin/env python3
"""Writes the hideout's textures, Assets/Hideout/Textures/*.png, with ImageMagick 7 (`magick`).

    python3 Tools/Hideout/make_textures.py [name ...]     (no names: all of them)

Everything is drawn here: concrete block and floor, wood, cardboard, egg cartons, the bedsheet
banner, the fake bands' posters, the rudiment chart, the gig flyers, the calendar, the setlist, TV
static, the night outside the window well, sticky notes. Deterministic (fixed noise seeds), so a
rerun gives the same pictures. Fonts are the system's DejaVu, Liberation, Free and Noto faces (all
free licences); the band names are made up.
"""
import json
import os
import random
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "Assets", "Hideout", "Textures")

HEAVY = "Noto-Sans-Black"
HEAVY_ITALIC = "Noto-Sans-Black-Italic"
BOLD = "Noto-Sans-Bold"
SERIF = "Noto-Serif-Display-Black"
SERIF_ITALIC = "Noto-Serif-Display-Black-Italic"
MONO = "Liberation-Mono-Bold"
TYPE = "FreeMono-Bold"
MARKER = "DejaVu-Sans-Bold-Oblique"
HAND = "Noto-Sans-Italic"


def magick(*args):
    cmd = ["magick", *[str(a) for a in args]]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"magick failed: {' '.join(cmd)}\n{r.stderr}")


def out(name):
    return os.path.join(OUT, name + ".png")


def tmp(name):
    return os.path.join(OUT, "_" + name + ".png")


def finish(name, *extra):
    """Strip metadata so reruns are byte-identical."""
    magick(out(name), *extra, "-strip", "-define", "png:exclude-chunks=date,time", out(name))


def grain(path, amount=0.25, seed=1):
    """A fine film of noise over an image, for paper and photocopy texture."""
    magick(path, "(", "+clone", "-seed", seed, "-attenuate", amount, "+noise", "Gaussian", "-colorspace", "gray", ")",
           "-compose", "overlay", "-composite", path)


# ---------------------------------------------------------------------------------------------
# Surfaces

def concrete_block():
    """Painted concrete block, running bond: 4 blocks (0.4 m) across, 4 courses (0.2 m) down,
    so the picture is 1.6 x 0.8 m. Damp along the bottom course."""
    rnd = random.Random(11)
    w, h, bw, bh, m = 1024, 512, 256, 128, 7
    draws = []
    for row in range(4):
        shift = 0 if row % 2 == 0 else bw // 2
        for col in range(-1, 5):
            x0 = col * bw + shift
            v = rnd.randint(-10, 10)
            c = (176 + v, 172 + v, 162 + v)
            draws += ["-fill", "rgb(%d,%d,%d)" % c, "-draw", f"roundrectangle {x0 + m},{row * bh + m} {x0 + bw - m},{row * bh + bh - m} 5,5"]
    magick("-size", f"{w}x{h}", "xc:rgb(118,114,106)", *draws, out("ConcreteBlock"))
    # Pores and mottling, then damp creeping up from the floor.
    magick("-size", f"{w}x{h}", "-seed", 4, "plasma:fractal", "-colorspace", "gray", "-blur", "0x2", "-auto-level", "+level", "78%,100%", tmp("mottle"))
    magick(out("ConcreteBlock"), tmp("mottle"), "-compose", "multiply", "-composite", out("ConcreteBlock"))
    magick(out("ConcreteBlock"), "(", "-size", f"{w}x{h}", "gradient:rgba(60,55,40,0)-rgba(60,55,40,0.5)", ")",
           "-compose", "over", "-composite", out("ConcreteBlock"))
    grain(out("ConcreteBlock"), 0.6, 3)
    finish("ConcreteBlock")


def concrete_floor():
    """2 x 2 m of old slab: mottled, a hairline crack, a few stains."""
    rnd = random.Random(5)
    s = 1024
    magick("-size", f"{s}x{s}", "xc:rgb(132,127,118)", "(", "-size", f"{s}x{s}", "-seed", 21, "plasma:fractal", "-colorspace", "gray",
           "-blur", "0x3", "-auto-level", "+level", "62%,100%", ")", "-compose", "multiply", "-composite", out("ConcreteFloor"))
    # The crack: a wandering line.
    x, y = 120, 0
    pts = []
    while y < s:
        pts.append(f"{x},{y}")
        x += rnd.randint(-28, 34)
        y += rnd.randint(30, 70)
    stains = []
    for _ in range(6):
        cx, cy, r = rnd.randint(0, s), rnd.randint(0, s), rnd.randint(40, 140)
        stains += ["-draw", f"ellipse {cx},{cy} {r},{int(r * 0.7)} 0,360"]
    magick(out("ConcreteFloor"), "-stroke", "rgba(40,36,30,0.8)", "-strokewidth", 2, "-fill", "none",
           "-draw", "polyline " + " ".join(pts), out("ConcreteFloor"))
    magick(out("ConcreteFloor"), "(", "-size", f"{s}x{s}", "xc:none", "-fill", "rgba(50,44,36,0.35)", *stains, "-blur", "0x18", ")",
           "-compose", "over", "-composite", out("ConcreteFloor"))
    grain(out("ConcreteFloor"), 0.7, 6)
    finish("ConcreteFloor")


def wood(name, light, dark, seed, knots=2):
    """Planed timber: grain running along the picture's height."""
    rnd = random.Random(seed)
    magick("-size", "96x512", "-seed", seed, "plasma:fractal", "-colorspace", "gray", "-resize", "512x512!", "-motion-blur", "0x18+90",
           "-auto-level", "+level-colors", f"{dark},{light}", out(name))
    draws = []
    for _ in range(knots):
        cx, cy = rnd.randint(40, 470), rnd.randint(40, 470)
        draws += ["-draw", f"ellipse {cx},{cy} {rnd.randint(7, 14)},{rnd.randint(16, 26)} 0,360"]
    magick(out(name), "(", "-size", "512x512", "xc:none", "-fill", "rgba(60,35,15,0.7)", *draws, "-blur", "0x3", ")",
           "-compose", "over", "-composite", out(name))
    grain(out(name), 0.3, seed)
    finish(name)


def cardboard(name, label=None, font=MARKER, color="black", seed=1, size=56, angle=-3):
    """Kraft board with its flutes showing faintly, packing tape, and a scrawled label."""
    magick("-size", "512x512", "xc:rgb(168,126,80)", "(", "-size", "64x512", "-seed", seed, "plasma:fractal", "-colorspace", "gray",
           "-resize", "512x512!", "-motion-blur", "0x6+90", "-auto-level", "+level", "80%,100%", ")", "-compose", "multiply", "-composite", out(name))
    magick(out(name), "-fill", "rgba(220,200,150,0.55)", "-draw", "rectangle 0,226 512,286", out(name))
    if label:
        magick(out(name), "-gravity", "center", "-font", font, "-pointsize", size, "-fill", color, "-annotate", f"{angle}x{angle}+0+120",
               label, out(name))
    grain(out(name), 0.5, seed)
    finish(name)


def egg_carton():
    """Egg cartons stapled up as soundproofing: cups in a grid, grey pulp."""
    magick("-size", "64x64", "radial-gradient:rgb(138,131,118)-rgb(96,90,80)", "-write", "mpr:cup", "+delete",
           "-size", "512x512", "tile:mpr:cup", out("EggCarton"))
    magick(out("EggCarton"), "(", "-size", "512x512", "-seed", 31, "plasma:fractal", "-colorspace", "gray", "-blur", "0x1",
           "-auto-level", "+level", "80%,100%", ")", "-compose", "multiply", "-composite", out("EggCarton"))
    grain(out("EggCarton"), 0.8, 32)
    finish("EggCarton")


def pegboard():
    magick("-size", "32x32", "xc:rgb(141,106,70)", "-fill", "rgb(40,28,18)", "-draw", "circle 16,16 16,20",
           "-write", "mpr:hole", "+delete", "-size", "512x512", "tile:mpr:hole", out("Pegboard"))
    grain(out("Pegboard"), 0.4, 41)
    finish("Pegboard")


# ---------------------------------------------------------------------------------------------
# Paper

def banner():
    """The bedsheet behind the kit, spray-painted."""
    w, h = 1024, 512
    magick("-size", f"{w}x{h}", "xc:rgb(228,224,212)", "(", "-size", "128x512", "-seed", 51, "plasma:fractal",
           "-colorspace", "gray", "-resize", f"{w}x{h}!", "-motion-blur", "0x30+80", "-auto-level", "+level", "82%,100%", ")",
           "-compose", "multiply", "-composite", out("Banner"))
    # Overspray first, then the letters, then drips.
    text = ["-gravity", "center", "-font", HEAVY, "-pointsize", 150, "-annotate", "-4x-4+0-40", "BAND NAME"]
    text2 = ["-gravity", "center", "-font", HEAVY, "-pointsize", 170, "-annotate", "-2x-2+10+120", "TBD"]
    magick(out("Banner"), "(", "-size", f"{w}x{h}", "xc:none", "-fill", "rgba(190,20,26,0.45)", *text, *text2, "-blur", "0x9", ")",
           "-compose", "over", "-composite", "-fill", "rgb(178,14,22)", *text, *text2, out("Banner"))
    rnd = random.Random(52)
    drips = []
    for _ in range(26):
        x = rnd.randint(150, 870)
        y = rnd.choice([rnd.randint(100, 140), rnd.randint(240, 290)])
        drips += ["-draw", f"line {x},{y} {x + rnd.randint(-2, 2)},{y + rnd.randint(20, 90)}"]
    magick(out("Banner"), "-stroke", "rgba(170,12,20,0.9)", "-strokewidth", 4, *drips, out("Banner"))
    magick(out("Banner"), "-gravity", "southeast", "-font", MARKER, "-pointsize", 30, "-fill", "rgb(30,30,30)",
           "-annotate", "-6x-6+40+26", "est. in mom's basement", out("Banner"))
    grain(out("Banner"), 0.3, 53)
    finish("Banner")


def banner_blank():
    """The bedsheet with nothing sprayed on it yet but the tagline and a few drips (the band's
    name is drawn over it in the game: HideoutBandName)."""
    w, h = 1024, 512
    magick("-size", f"{w}x{h}", "xc:rgb(228,224,212)", "(", "-size", "128x512", "-seed", 51, "plasma:fractal",
           "-colorspace", "gray", "-resize", f"{w}x{h}!", "-motion-blur", "0x30+80", "-auto-level", "+level", "82%,100%", ")",
           "-compose", "multiply", "-composite", out("BannerBlank"))
    magick(out("BannerBlank"), "(", "-size", f"{w}x{h}", "xc:none", "-fill", "rgba(190,20,26,0.18)", "-draw", "ellipse 512,230 420,120 0,360",
           "-blur", "0x40", ")", "-compose", "over", "-composite", out("BannerBlank"))
    magick(out("BannerBlank"), "-gravity", "southeast", "-font", MARKER, "-pointsize", 30, "-fill", "rgb(30,30,30)",
           "-annotate", "-6x-6+40+26", "est. in mom's basement", out("BannerBlank"))
    grain(out("BannerBlank"), 0.3, 54)
    finish("BannerBlank")


def photocopy(path, seed):
    """A gig flyer's life: photocopied, slightly crooked, grainy."""
    magick(path, "-colorspace", "gray", "-contrast-stretch", "2%x2%", path)
    grain(path, 1.4, seed)


def poster_death_squad():
    n = "PosterDeathSquad"
    magick("-size", "512x768", "xc:rgb(18,18,18)", "-gravity", "north", "-font", HEAVY, "-fill", "rgb(250,214,40)",
           "-pointsize", 96, "-annotate", "+0+40", "PARA-", "-annotate", "+0+140", "DIDDLE", "-pointsize", 112,
           "-annotate", "+0+250", "DEATH", "-annotate", "+0+370", "SQUAD",
           "-font", BOLD, "-pointsize", 30, "-fill", "white", "-annotate", "+0+520", "w/ THE METRONOMES",
           "-annotate", "+0+560", "+ GHOST NOTES",
           "-fill", "rgb(250,214,40)", "-pointsize", 26, "-annotate", "+0+640", "SAT 9PM  //  VFW HALL",
           "-annotate", "+0+680", "$5  //  ALL AGES  //  NO MOSHING (PLS)", out(n))
    grain(out(n), 0.9, 61)
    finish(n)


def poster_metronomes():
    n = "PosterMetronomes"
    ticks = []
    for i in range(24):
        import math
        a = math.radians(i * 15)
        r0, r1 = (150, 180) if i % 2 else (130, 180)
        ticks += ["-draw", "line %d,%d %d,%d" % (256 + r0 * math.sin(a), 330 - r0 * math.cos(a), 256 + r1 * math.sin(a), 330 - r1 * math.cos(a))]
    magick("-size", "512x768", "xc:rgb(246,170,190)", "-fill", "none", "-stroke", "rgb(26,34,90)", "-strokewidth", 10,
           "-draw", "circle 256,330 256,140", "-strokewidth", 6, *ticks, "-strokewidth", 14,
           "-draw", "line 256,330 330,200", "-fill", "rgb(26,34,90)", "-draw", "circle 256,330 256,344", "-stroke", "none",
           "-gravity", "north", "-font", SERIF, "-pointsize", 60, "-annotate", "+0+30", "the metronomes",
           "-font", HEAVY, "-pointsize", 46, "-annotate", "+0+550", "TOUR 2026",
           "-font", HAND, "-pointsize", 28, "-annotate", "+0+620", "120 bpm and not one more", out(n))
    grain(out(n), 0.5, 62)
    finish(n)


def poster_kick_drum_kids():
    n = "PosterKickDrumKids"
    magick("-size", "512x768", "xc:rgb(196,28,32)", "-fill", "rgb(16,16,16)", "-draw", "circle 256,360 256,140",
           "-fill", "rgb(230,226,214)", "-draw", "circle 256,360 256,180",
           "-fill", "rgb(16,16,16)", "-gravity", "center", "-font", HEAVY, "-pointsize", 120, "-annotate", "+0-48", "KDK",
           "-gravity", "north", "-fill", "rgb(16,16,16)", "-font", HEAVY_ITALIC, "-pointsize", 58, "-annotate", "+0+22", "KICK DRUM",
           "-pointsize", 72, "-annotate", "+0+600", "KIDS", "-font", BOLD, "-pointsize", 26, "-fill", "rgb(240,236,226)",
           "-annotate", "+0+700", "debut EP out never", out(n))
    grain(out(n), 0.7, 63)
    finish(n)


def poster_ghost_notes():
    n = "PosterGhostNotes"
    magick("-size", "512x768", "gradient:rgb(60,24,96)-rgb(14,8,28)", "-fill", "rgba(230,224,255,0.9)",
           "-draw", "circle 256,300 256,190", "-draw", "rectangle 146,300 366,470",
           "-fill", "rgb(60,24,96)", "-draw", "circle 216,290 216,312", "-draw", "circle 296,290 296,312",
           "-fill", "rgba(230,224,255,0.9)", "-draw", "circle 173,470 173,497", "-draw", "circle 228,470 228,497",
           "-draw", "circle 284,470 284,497", "-draw", "circle 339,470 339,497",
           "-gravity", "north", "-font", SERIF_ITALIC, "-fill", "rgb(220,210,255)", "-pointsize", 76, "-annotate", "+0+30", "ghost notes",
           "-font", MONO, "-pointsize", 26, "-annotate", "+0+600", "quiet LOUD quiet", "-annotate", "+0+640", "( o X o o X o )",
           out(n))
    magick(out(n), "(", "+clone", "-blur", "0x14", ")", "-compose", "screen", "-composite", out(n))
    grain(out(n), 0.5, 64)
    finish(n)


def poster_magazine():
    n = "PosterMagazine"
    magick("-size", "512x700", "xc:rgb(244,240,226)", "-fill", "rgb(214,40,40)", "-draw", "rectangle 0,0 512,120",
           "-gravity", "north", "-font", SERIF, "-fill", "white", "-pointsize", 70, "-annotate", "+0+18", "DRUMMER",
           "-fill", "rgb(20,20,20)", "-font", HEAVY, "-pointsize", 22, "-annotate", "+0+128", "MONTHLY  //  ISSUE 412  //  $6.99",
           # A kit in silhouette.
           "-fill", "rgb(30,30,30)", "-draw", "circle 256,470 256,390", "-draw", "circle 160,380 160,345", "-draw", "circle 352,380 352,345",
           "-draw", "circle 120,470 120,425", "-draw", "rectangle 60,300 200,306", "-draw", "rectangle 312,288 470,294",
           "-gravity", "northwest", "-font", HEAVY, "-pointsize", 30, "-fill", "rgb(214,40,40)",
           "-annotate", "+22+180", "LEARN THE PARADIDDLE", "-annotate", "+22+214", "IN ONLY 30 YEARS",
           "-gravity", "southwest", "-fill", "rgb(20,20,20)", "-pointsize", 24, "-annotate", "+22+90", "BASEMENT ACOUSTICS",
           "-annotate", "+22+62", "ON A $0 BUDGET", "-fill", "rgb(214,40,40)", "-annotate", "+22+22", "IS YOUR SNARE TOO LOUD? (YES)",
           out(n))
    grain(out(n), 0.4, 65)
    finish(n)


def poster_rudiments():
    """A chart of the game's own rudiments, typed out from Assets/Practice/Lessons.json."""
    n = "PosterRudiments"
    lessons = json.load(open(os.path.join(ROOT, "Assets", "Practice", "Lessons.json")))["Lessons"]
    rows = [(l["Name"].upper(), l["Sticking"].replace(">", "").replace("^", "f")) for l in lessons if l.get("Sticking")]
    draws = []
    y = 150
    for name, sticking in rows:
        draws += ["-font", BOLD, "-pointsize", 24, "-fill", "rgb(30,30,30)", "-annotate", f"+36+{y}", name,
                  "-font", MONO, "-pointsize", 24, "-fill", "rgb(170,30,30)", "-annotate", f"+36+{y + 30}", sticking]
        y += 70
    magick("-size", "512x800", "xc:rgb(238,234,222)", "-gravity", "northwest", "-font", HEAVY, "-pointsize", 44,
           "-fill", "rgb(30,30,30)", "-annotate", "+36+30", "RUDIMENTS", "-font", HAND, "-pointsize", 22,
           "-annotate", "+38+92", "the 40 essentials (we know nine)", *draws, out(n))
    grain(out(n), 0.4, 66)
    finish(n)


def flyer(name, title, lines, seed, bg="rgb(250,250,246)"):
    magick("-size", "384x512", f"xc:{bg}", "-gravity", "north", "-font", HEAVY, "-pointsize", 54, "-fill", "black",
           "-annotate", "+0+28", title, "-font", TYPE, "-pointsize", 24,
           *sum((["-annotate", f"+0+{140 + i * 40}", line] for i, line in enumerate(lines)), []), out(name))
    magick(out(name), "-fill", "none", "-stroke", "black", "-strokewidth", 6, "-draw", "rectangle 14,14 370,498", out(name))
    photocopy(out(name), seed)
    finish(name)


def calendar():
    n = "Calendar"
    draws = []
    for row in range(5):
        for col in range(7):
            x, y = 22 + col * 49, 150 + row * 66
            day = row * 7 + col - 1
            draws += ["-fill", "none", "-stroke", "rgb(60,60,60)", "-strokewidth", 1, "-draw", f"rectangle {x},{y} {x + 49},{y + 66}"]
            if 1 <= day <= 30:
                draws += ["-stroke", "none", "-fill", "rgb(40,40,40)", "-font", BOLD, "-pointsize", 14, "-annotate", f"+{x + 5}+{y + 17}", str(day)]
                if day < 18:
                    draws += ["-stroke", "rgb(200,30,30)", "-strokewidth", 3, "-draw", f"line {x + 10},{y + 20} {x + 40},{y + 58}",
                              "-draw", f"line {x + 40},{y + 20} {x + 10},{y + 58}"]
                if day == 22:
                    draws += ["-fill", "none", "-stroke", "rgb(200,30,30)", "-strokewidth", 3, "-draw", f"ellipse {x + 25},{y + 36} 26,24 0,360",
                              "-stroke", "none", "-fill", "rgb(200,30,30)", "-font", MARKER, "-pointsize", 15, "-annotate", f"+{x + 8}+{y + 50}", "GIG!"]
    magick("-size", "384x512", "xc:rgb(250,248,240)", "-fill", "rgb(40,90,150)", "-draw", "rectangle 0,0 384,120",
           "-gravity", "northwest", "-font", HEAVY, "-pointsize", 46, "-fill", "white", "-annotate", "+24+34", "NOVEMBER",
           *draws, out(n))
    grain(out(n), 0.3, 71)
    finish(n)


def setlist():
    n = "Setlist"
    songs = ["1. the fast one", "2. the slow one", "3. COVER (watch the fill)", "4. ???", "5. drum solo (KEEP IT SHORT)",
             "6. the fast one again", "", "encore: we don't have one"]
    magick("-size", "320x448", "xc:rgb(252,252,248)", "-gravity", "northwest", "-font", MARKER, "-pointsize", 36,
           "-fill", "black", "-annotate", "-3x-3+24+20", "SETLIST", "-pointsize", 17,
           *sum((["-annotate", f"-2x-2+24+{90 + i * 40}", s] for i, s in enumerate(songs)), []), out(n))
    grain(out(n), 0.3, 72)
    finish(n)


def sticky(name, text, color, seed, size=24):
    magick("-size", "192x192", f"xc:{color}", "-gravity", "center", "-font", MARKER, "-pointsize", size, "-fill", "rgb(30,30,40)",
           "-annotate", "-4x-4+0+0", text, out(name))
    grain(out(name), 0.3, seed)
    finish(name)


def pizza():
    n = "PizzaBox"
    magick("-size", "512x512", "xc:rgb(236,230,214)", "-fill", "none", "-stroke", "rgb(196,32,32)", "-strokewidth", 10,
           "-draw", "circle 256,230 256,90", "-stroke", "none", "-fill", "rgb(196,32,32)", "-gravity", "center", "-font", HEAVY,
           "-pointsize", 70, "-annotate", "+0-26", "PIZZA", "-font", BOLD, "-pointsize", 30, "-annotate", "+0+190", "HOT  FRESH  EVENTUALLY",
           out(n))
    magick(out(n), "(", "-size", "512x512", "xc:none", "-fill", "rgba(150,110,40,0.35)", "-draw", "ellipse 380,380 70,50 0,360",
           "-blur", "0x12", ")", "-compose", "over", "-composite", out(n))
    grain(out(n), 0.4, 73)
    finish(n)


def cork():
    magick("-size", "512x512", "xc:rgb(150,104,62)", "(", "-size", "512x512", "xc:gray50", "-seed", 141, "+noise", "Random", "-colorspace", "gray",
           "-blur", "0x0.8", "-auto-level", "+level", "55%,100%", ")", "-compose", "multiply", "-composite", out("Cork"))
    grain(out("Cork"), 0.8, 142)
    finish("Cork")


def tear_off(name, title, body, tab, seed, bg="rgb(250,250,244)"):
    """A flyer with phone-number tabs along the bottom (two already torn off)."""
    tabs = []
    for i in range(8):
        x = 12 + i * 45
        if i in (2, 5):
            continue
        tabs += ["-fill", "none", "-stroke", "rgb(60,60,60)", "-strokewidth", 1, "-draw", f"rectangle {x},380 {x + 42},508",
                 "-stroke", "none", "-fill", "rgb(30,30,30)", "-font", TYPE, "-pointsize", 15,
                 "-annotate", f"90x90+{x + 16}+392", tab]
    magick("-size", "384x512", f"xc:{bg}", "-gravity", "north", "-font", HEAVY, "-pointsize", 46, "-fill", "black",
           "-annotate", "+0+20", title, "-font", HAND, "-pointsize", 22,
           *sum((["-annotate", f"+0+{150 + i * 32}", line] for i, line in enumerate(body)), []),
           "-gravity", "northwest", *tabs, "-fill", "rgb(150,104,62)", "-draw", "rectangle 102,380 144,512",
           "-draw", "rectangle 237,380 279,512", out(name))
    photocopy(out(name), seed)
    finish(name)


def certificate():
    n = "Certificate"
    magick("-size", "512x384", "xc:rgb(246,240,222)", "-fill", "none", "-stroke", "rgb(150,120,50)", "-strokewidth", 8,
           "-draw", "rectangle 14,14 498,370", "-strokewidth", 2, "-draw", "rectangle 28,28 484,356", "-stroke", "none",
           "-gravity", "north", "-font", SERIF, "-fill", "rgb(60,40,20)", "-pointsize", 40, "-annotate", "+0+46", "Certificate",
           "-font", HAND, "-pointsize", 20, "-annotate", "+0+104", "is awarded to", "-font", MARKER, "-pointsize", 30,
           "-annotate", "+0+140", "THE DRUMMER", "-font", HAND, "-pointsize", 20, "-annotate", "+0+190", "for",
           "-font", SERIF_ITALIC, "-pointsize", 32, "-annotate", "+0+220", "Most Improved Percussion",
           "-font", HAND, "-pointsize", 18, "-annotate", "+0+268", "7th Grade Winter Concert",
           "-fill", "rgb(190,40,40)", "-draw", "circle 420,300 420,340", "-fill", "rgb(150,120,50)",
           "-draw", "circle 420,300 420,330", out(n))
    grain(out(n), 0.3, 151)
    finish(n)


def laptop_screen():
    """A song shop in a browser: a header, rows of songs with download buttons."""
    n = "LaptopScreen"
    rows = []
    songs = [("the fast one", "THE METRONOMES"), ("ghost note blues", "GHOST NOTES"), ("kick it", "KICK DRUM KIDS"),
             ("paradiddle anthem", "PARADIDDLE DEATH SQUAD"), ("120 bpm", "THE METRONOMES")]
    for i, (song, band) in enumerate(songs):
        y = 92 + i * 52
        rows += ["-fill", "rgb(36,40,52)" if i % 2 else "rgb(30,33,44)", "-draw", f"rectangle 16,{y} 496,{y + 46}",
                 "-fill", "rgb(220,226,240)", "-font", BOLD, "-pointsize", 17, "-annotate", f"+28+{y + 8}", song,
                 "-fill", "rgb(140,150,175)", "-font", HAND, "-pointsize", 13, "-annotate", f"+28+{y + 28}", band,
                 "-fill", "rgb(80,200,120)", "-draw", f"roundrectangle 400,{y + 10} 484,{y + 36} 6,6",
                 "-fill", "rgb(10,30,16)", "-font", BOLD, "-pointsize", 13, "-annotate", f"+412+{y + 15}", "GET"]
    magick("-size", "512x384", "xc:rgb(22,24,32)", "-fill", "rgb(46,52,80)", "-draw", "rectangle 0,0 512,26",
           "-fill", "rgb(230,80,90)", "-draw", "circle 14,13 19,13", "-fill", "rgb(240,190,60)", "-draw", "circle 32,13 37,13",
           "-fill", "rgb(90,200,110)", "-draw", "circle 50,13 55,13", "-gravity", "northwest", "-fill", "rgb(240,240,250)",
           "-font", HEAVY, "-pointsize", 28, "-annotate", "+18+38", "SONG SHOP", "-fill", "rgb(140,150,175)", "-font", HAND,
           "-pointsize", 14, "-annotate", "+190+50", "free songs. drums included.", *rows, out(n))
    finish(n)


def drywall():
    """Painted drywall: smooth, the tape lines faintly showing every 1.2 m, a scuff or two."""
    rnd = random.Random(171)
    magick("-size", "512x512", "xc:rgb(204,198,184)", "(", "-size", "512x512", "-seed", 172, "plasma:fractal", "-colorspace", "gray",
           "-blur", "0x8", "-auto-level", "+level", "88%,100%", ")", "-compose", "multiply", "-composite",
           "-fill", "rgba(255,255,250,0.35)", "-draw", "rectangle 250,0 262,512", out("Drywall"))
    scuffs = []
    for _ in range(5):
        x, y = rnd.randint(0, 512), rnd.randint(300, 500)
        scuffs += ["-draw", f"line {x},{y} {x + rnd.randint(10, 60)},{y + rnd.randint(-6, 6)}"]
    magick(out("Drywall"), "-stroke", "rgba(60,55,50,0.25)", "-strokewidth", 2, *scuffs, out("Drywall"))
    grain(out("Drywall"), 0.25, 173)
    finish("Drywall")


def dartboard():
    import math
    n = "Dartboard"
    draws = ["-fill", "rgb(20,20,20)", "-draw", "circle 256,256 256,6"]
    for i in range(20):
        a0, a1 = math.radians(i * 18 - 9), math.radians(i * 18 + 9)
        for r0, r1, colours in ((200, 236, ("rgb(190,30,30)", "rgb(30,130,60)")), (24, 200, ("rgb(20,20,20)", "rgb(232,220,190)")),
                                (120, 136, ("rgb(190,30,30)", "rgb(30,130,60)"))):
            pts = [(256 + r0 * math.sin(a0), 256 - r0 * math.cos(a0)), (256 + r1 * math.sin(a0), 256 - r1 * math.cos(a0)),
                   (256 + r1 * math.sin(a1), 256 - r1 * math.cos(a1)), (256 + r0 * math.sin(a1), 256 - r0 * math.cos(a1))]
            draws += ["-fill", colours[i % 2], "-draw", "polygon " + " ".join("%d,%d" % p for p in pts)]
    draws += ["-fill", "rgb(30,130,60)", "-draw", "circle 256,256 256,232", "-fill", "rgb(190,30,30)", "-draw", "circle 256,256 256,244"]
    magick("-size", "512x512", "xc:none", *draws, out(n))
    finish(n)


def kick_head():
    """The kick's front head: the band's name in marker, a doodle, and nothing outside the circle
    (alpha 0 there, for a cut-out)."""
    n = "KickHead"
    magick("-size", "512x512", "xc:none", "-fill", "rgb(236,232,222)", "-draw", "circle 256,256 256,6",
           "-fill", "none", "-stroke", "rgb(30,30,30)", "-strokewidth", 5, "-draw", "circle 256,256 256,40",
           "-stroke", "none", "-fill", "rgb(24,24,28)", "-gravity", "center", "-font", MARKER, "-pointsize", 66,
           "-annotate", "-6x-6+0-60", "BAND NAME", "-pointsize", 92, "-annotate", "-4x-4+10+40", "TBD",
           "-fill", "none", "-stroke", "rgb(200,30,30)", "-strokewidth", 6,
           "-draw", "polyline 150,380 175,330 200,380 150,348 200,348 150,380",
           "-stroke", "rgb(24,24,28)", "-strokewidth", 4, "-draw", "circle 360,365 360,395", "-draw", "point 350,358",
           "-draw", "point 370,358", "-draw", "arc 345,365 375,385 20,160", out(n))
    finish(n)


def kick_head_blank():
    n = "KickHeadBlank"
    magick("-size", "512x512", "xc:none", "-fill", "rgb(236,232,222)", "-draw", "circle 256,256 256,6",
           "-fill", "none", "-stroke", "rgb(30,30,30)", "-strokewidth", 5, "-draw", "circle 256,256 256,40",
           "-stroke", "rgb(200,30,30)", "-strokewidth", 6, "-draw", "polyline 150,380 175,330 200,380 150,348 200,348 150,380",
           "-stroke", "rgb(24,24,28)", "-strokewidth", 4, "-draw", "circle 360,365 360,395", "-draw", "point 350,358",
           "-draw", "point 370,358", "-draw", "arc 345,365 375,385 20,160", out(n))
    finish(n)


# ---------------------------------------------------------------------------------------------
# Light

def tv_static():
    n = "TvStatic"
    magick("-size", "160x120", "xc:gray50", "-seed", 81, "-attenuate", 3, "+noise", "Random", "-colorspace", "gray",
           "-scale", "320x240!", "(", "-size", "320x3", "xc:white", "-fill", "gray55", "-draw", "line 0,2 320,2", "-write", "mpr:scan",
           "+delete", "-size", "320x240", "tile:mpr:scan", ")", "-compose", "multiply", "-composite",
           "+level-colors", "rgb(10,14,30),rgb(200,215,255)", out(n))
    finish(n)


def window_night():
    """Through the window well's grimy glass: grass against a streetlit night."""
    n = "WindowNight"
    rnd = random.Random(91)
    blades = []
    for _ in range(140):
        x = rnd.randint(0, 512)
        blades += ["-draw", f"line {x},256 {x + rnd.randint(-14, 14)},{rnd.randint(120, 220)}"]
    magick("-size", "512x256", "gradient:rgb(70,96,160)-rgb(24,34,70)", "(", "-size", "300x300", "radial-gradient:rgb(255,196,120)-black",
           "-background", "black", "-gravity", "center", "-extent", "512x256", "-roll", "+120-40", ")", "-compose", "screen", "-composite",
           "-stroke", "rgb(6,10,8)", "-strokewidth", 3, *blades, out(n))
    magick(out(n), "(", "-size", "512x256", "-seed", 92, "plasma:fractal", "-colorspace", "gray", "-blur", "0x4", "-auto-level", "+level", "70%,100%", ")",
           "-compose", "multiply", "-composite", out(n))
    finish(n)


ALL = {
    "ConcreteBlock": concrete_block,
    "ConcreteFloor": concrete_floor,
    "Wood": lambda: wood("Wood", "rgb(176,128,80)", "rgb(120,80,44)", 101),
    "WoodDark": lambda: wood("WoodDark", "rgb(110,74,44)", "rgb(64,40,22)", 102, 3),
    "Plywood": lambda: wood("Plywood", "rgb(214,176,124)", "rgb(176,136,88)", 103, 4),
    "Cardboard": lambda: cardboard("Cardboard", seed=111),
    "BoxXmas": lambda: cardboard("BoxXmas", "XMAS", seed=112, size=110, color="rgb(170,20,20)"),
    "BoxMoms": lambda: cardboard("BoxMoms", "MOM'S STUFF\nDO NOT TOUCH", seed=113, size=50),
    "BoxCables": lambda: cardboard("BoxCables", "CABLES (??)", seed=114, size=60),
    "EggCarton": egg_carton,
    "Pegboard": pegboard,
    "Banner": banner,
    "PosterDeathSquad": poster_death_squad,
    "PosterMetronomes": poster_metronomes,
    "PosterKickDrumKids": poster_kick_drum_kids,
    "PosterGhostNotes": poster_ghost_notes,
    "PosterMagazine": poster_magazine,
    "PosterRudiments": poster_rudiments,
    "FlyerBackyard": lambda: flyer("FlyerBackyard", "BACKYARD\nPARTY", ["", "", "", "bring a chair", "bring a friend", "don't bring", "the cops"], 121),
    "FlyerClub": lambda: flyer("FlyerClub", "CLUB\nNIGHT", ["", "", "", "doors 8pm", "$8 cover", "3 bands, 1 kit", "(yours)"], 122),
    "FlyerFestival": lambda: flyer("FlyerFestival", "FEST", ["", "second stage", "3:15 pm", "", "ACCESS: ARTIST", "lanyard", "stays on"], 123),
    "Calendar": calendar,
    "Setlist": setlist,
    "StickyPractice": lambda: sticky("StickyPractice", "PRACTICE\n!!!", "rgb(250,232,92)", 131, 34),
    "StickyDinner": lambda: sticky("StickyDinner", "mom:\ndinner at 6\nNOT 6:45", "rgb(255,160,190)", 132, 22),
    "StickyRent": lambda: sticky("StickyRent", "rent??\n$0", "rgb(150,220,250)", 133, 30),
    "PizzaBox": pizza,
    "Cork": cork,
    "FlyerBassist": lambda: tear_off("FlyerBassist", "BASSIST\nWANTED", ["", "", "must have own amp", "must have own van", "must like loud"], "555-0142", 161),
    "FlyerLawns": lambda: tear_off("FlyerLawns", "LAWNS\nMOWED", ["", "", "$10 a lawn", "(saving for cymbals)"], "555-0187", 162, "rgb(250,246,200)"),
    "Certificate": certificate,
    "LaptopScreen": laptop_screen,
    "KickHead": kick_head,
    "Drywall": drywall,
    "BannerBlank": banner_blank,
    "KickHeadBlank": kick_head_blank,
    "Dartboard": dartboard,
    "TvStatic": tv_static,
    "WindowNight": window_night,
}


def main():
    os.makedirs(OUT, exist_ok=True)
    names = sys.argv[1:] or list(ALL)
    for name in names:
        ALL[name]()
        print("wrote", out(name))
    for leftover in os.listdir(OUT):
        if leftover.startswith("_"):
            os.remove(os.path.join(OUT, leftover))


if __name__ == "__main__":
    main()
