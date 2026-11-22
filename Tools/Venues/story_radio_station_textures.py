"""Textures for the StoryRadioStation venue (set 07, The Pledge Drive Night Shift), drawn with
ImageMagick 7 into Assets/Venues/StoryRadioStation/Textures/. Deterministic (fixed seeds, metadata
stripped). The station, its shows, its hosts and every pledge are made up; 555-01xx is a fiction
number range.
"""
import glob
import os
import random
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "Assets", "Venues", "StoryRadioStation", "Textures")

HEAVY = "Noto-Sans-Black"
HEAVY_ITALIC = "Noto-Sans-Black-Italic"
BOLD = "Noto-Sans-Bold"
SERIF = "Noto-Serif-Display-Black"
MONO = "Liberation-Mono-Bold"
MARKER = os.path.join(ROOT, "Assets", "Fonts", "PermanentMarker-Regular.ttf")
HAND = os.path.join(ROOT, "Assets", "Fonts", "GochiHand-Regular.ttf")


def _magick_bin():
    found = shutil.which("magick")
    if found:
        return found
    for path in sorted(glob.glob("/nix/store/*-imagemagick-7*/bin/magick")):
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


def finish(name):
    magick(out(name), "-strip", "-define", "png:exclude-chunks=date,time", out(name))


def grain(name, amount=0.3, seed=1):
    p = out(name)
    magick(p, "(", "+clone", "-seed", seed, "-attenuate", amount, "+noise", "Gaussian", "-colorspace", "gray", ")",
           "-compose", "overlay", "-composite", p)


# ---- surfaces --------------------------------------------------------------------------------

def foam():
    """Acoustic wedge foam, 4 x 4 tiles of alternating ridges (one picture = 1 m square)."""
    n = "Foam"
    magick("-size", "256x256", "xc:", "-fx",
           "kc=(floor(i/64)+floor(j/64))%2; kw=kc<1?abs(sin(i*pi/16)):abs(sin(j*pi/16)); 0.12+0.55*kw",
           "+level-colors", "rgb(14,15,20),rgb(64,66,78)", out(n))
    grain(n, 0.35, 3)
    finish(n)


def carpet():
    """Office carpet tiles, 4 x 4 per picture (2 m)."""
    n = "Carpet"
    rnd = random.Random(7)
    draws = []
    for r in range(4):
        for c in range(4):
            v = rnd.randint(-6, 6)
            draws += ["-fill", "rgb(%d,%d,%d)" % (38 + v, 42 + v, 56 + v), "-draw", f"rectangle {c*128+1},{r*128+1} {c*128+126},{r*128+126}"]
    magick("-size", "512x512", "xc:rgb(24,26,32)", *draws, out(n))
    grain(n, 0.9, 8)
    finish(n)


def ceiling_tile():
    n = "CeilingTile"
    magick("-size", "256x256", "xc:rgb(196,196,188)", "-fill", "rgb(150,150,144)", "-draw", "rectangle 0,0 255,3",
           "-draw", "rectangle 0,0 3,255", out(n))
    magick(out(n), "(", "+clone", "-seed", 11, "-attenuate", 1.6, "+noise", "Impulse", "-colorspace", "gray", ")",
           "-compose", "multiply", "-composite", out(n))
    finish(n)


def cr_wall():
    """The control room's painted block wall, warm institutional beige."""
    n = "CRWall"
    draws = []
    for row in range(4):
        shift = 0 if row % 2 == 0 else 64
        for col in range(-1, 5):
            x0 = col * 128 + shift
            draws += ["-draw", f"line {x0},{row*64} {x0},{row*64+63}"]
        draws += ["-draw", f"line 0,{row*64} 511,{row*64}"]
    magick("-size", "512x256", "xc:rgb(176,162,132)", "-stroke", "rgb(140,128,104)", "-strokewidth", 3, *draws, out(n))
    grain(n, 0.5, 12)
    finish(n)


# ---- signs and posters -----------------------------------------------------------------------

def on_air():
    n = "OnAir"
    magick("-size", "512x180", "xc:rgb(150,6,8)", "-fill", "rgb(255,236,226)", "-font", HEAVY, "-pointsize", 128,
           "-gravity", "center", "-annotate", "+0+4", "ON AIR", out(n))
    magick(out(n), "(", "+clone", "-blur", "0x10", ")", "-compose", "screen", "-composite", out(n))
    finish(n)


def station_banner():
    n = "StationBanner"
    magick("-size", "1024x256", "xc:rgb(20,26,48)", "-fill", "rgb(255,196,48)", "-font", HEAVY, "-pointsize", 112,
           "-gravity", "west", "-annotate", "+36-8", "89.3", "-fill", "white", "-font", HEAVY_ITALIC, "-pointsize", 92,
           "-annotate", "+330-18", "THE SIGNAL", "-font", BOLD, "-pointsize", 25, "-fill", "rgb(160,190,255)",
           "-annotate", "+336+70", "CAMPUS RADIO  //  ALL NIGHT  //  LISTENER SUPPORTED", out(n))
    grain(n, 0.4, 13)
    finish(n)


def pledge_banner():
    n = "PledgeBanner"
    magick("-size", "1024x256", "xc:rgb(242,236,220)", "-fill", "rgb(200,30,40)", "-font", MARKER, "-pointsize", 96,
           "-gravity", "center", "-annotate", "+0-30", "PLEDGE NIGHT!", "-fill", "rgb(30,40,110)", "-pointsize", 50,
           "-annotate", "+0+70", "keep the signal on  -  555-0193", out(n))
    grain(n, 0.5, 14)
    finish(n)


def rent_banner():
    n = "RentBanner"
    magick("-size", "1024x320", "xc:rgb(255,214,60)", "-fill", "rgb(190,20,30)", "-font", MARKER, "-pointsize", 150,
           "-gravity", "center", "-annotate", "+0-6", "RENT PAID!!", "-fill", "rgb(40,30,20)", "-pointsize", 40,
           "-annotate", "+0+122", "thank you, night owls  <3  -  the volunteers", out(n))
    grain(n, 0.4, 15)
    finish(n)


def rent_sheet():
    n = "RentSheet"
    magick("-size", "320x256", "xc:rgb(255,226,80)", "-fill", "rgb(190,20,30)", "-font", MARKER, "-pointsize", 92,
           "-gravity", "center", "-annotate", "+0-48", "RENT", "-annotate", "+0+52", "PAID", out(n))
    grain(n, 0.4, 16)
    finish(n)


def rent_meter():
    """The rent-o-meter board: an empty thermometer drawn on card (the red fill is geometry)."""
    n = "RentMeter"
    ticks = []
    for i in range(6):
        y = 860 - i * 140
        ticks += ["-draw", f"line 300,{y} 350,{y}"]
    labels = []
    for i, t in enumerate(["$0", "$1k", "$2k", "$3k", "$4k", "$4.8k"]):
        labels += ["-annotate", f"+360+{860 - i*140 - 20}", t]
    magick("-size", "512x1024", "xc:rgb(238,234,222)", "-fill", "none", "-stroke", "rgb(30,30,40)", "-strokewidth", 10,
           "-draw", "roundrectangle 196,150 296,900 50,50", "-draw", "circle 246,930 246,860",
           "-strokewidth", 6, *ticks, "-stroke", "none", "-fill", "rgb(30,30,40)",
           "-font", MARKER, "-pointsize", 40, "-gravity", "northwest", *labels,
           "-gravity", "north", "-pointsize", 54, "-fill", "rgb(190,20,30)", "-annotate", "+0+24", "RENT-O-METER",
           "-font", HAND, "-pointsize", 34, "-fill", "rgb(30,40,110)", "-annotate", "+0+96", "goal: $4,800 by sign-off", out(n))
    grain(n, 0.5, 17)
    finish(n)


POSTERS = {
    "PosterNightOwl": ("rgb(18,22,60)", "rgb(255,220,90)", ["THE", "NIGHT OWL", "HOUR"], "TUES 2-4 AM  w/ DEE & MOSS", "requests: 555-0193"),
    "PosterThesis": ("rgb(16,16,16)", "rgb(230,40,40)", ["THESIS", "DEFENSE"], "METAL  //  WED MIDNIGHT", "no talking. only riffs."),
    "PosterSoulKitchen": ("rgb(230,120,40)", "rgb(40,16,8)", ["SOUL", "KITCHEN"], "SUNDAYS 9 PM  //  HOT 45s", "cold coffee provided"),
    "PosterDormDemos": ("rgb(120,200,170)", "rgb(16,40,50)", ["DORM", "ROOM", "DEMOS"], "SEND US YOUR TAPE", "studio B  //  mon-fri"),
    "PosterProfVinyl": ("rgb(236,226,200)", "rgb(90,30,90)", ["PROF.", "VINYL'S", "OFFICE HRS"], "THURS 11 PM  //  DEEP CUTS", "attendance optional"),
    "PosterGrooveCo": ("rgb(160,40,120)", "rgb(255,240,250)", ["CAMPUS", "GROOVE", "CO-OP"], "FRIDAYS LATE  //  BRING SNACKS", "est. a while ago"),
}


def posters():
    for n, (bg, ink, title, line1, line2) in POSTERS.items():
        args = ["-size", "512x768", f"xc:{bg}", "-gravity", "north", "-fill", ink, "-font", HEAVY]
        for i, word in enumerate(title):
            args += ["-pointsize", min(104, int(470 / (0.66 * len(word)))), "-annotate", f"+0+{50 + i*120}", word]
        args += ["-font", BOLD, "-pointsize", 32, "-annotate", "+0+560", line1, "-font", HAND, "-pointsize", 40,
                 "-annotate", "+0+630", line2, "-font", MONO, "-pointsize", 26, "-annotate", "+0+700", "89.3 THE SIGNAL"]
        magick(*args, out(n))
        grain(n, 0.7, sum(map(ord, n)) % 97)
        finish(n)


PLEDGES = [
    ("rgb(255,236,120)", "$20", "Priya - Res Hall B"),
    ("rgb(255,170,200)", "$50!!", "keep it weird"),
    ("rgb(245,245,238)", "$10", "the night bus driver"),
    ("rgb(170,230,160)", "$35", "Room 214 (all of us)"),
    ("rgb(160,200,255)", "$100", "Alumni '09 <3"),
    ("rgb(255,190,110)", "$5", "+ a coffee for Dee"),
    ("rgb(255,236,120)", "$25", "Mrs. K at the library"),
    ("rgb(245,245,238)", "$15", "Chem lab, night shift"),
    ("rgb(255,170,200)", "$40", "play more soul pls"),
    ("rgb(170,230,160)", "$60", "the pizza place"),
]


def pledges():
    for i, (paper, amount, who) in enumerate(PLEDGES):
        n = f"Pledge{i}"
        magick("-size", "256x320", f"xc:{paper}", "-fill", "rgb(30,36,100)" if i % 3 else "rgb(170,20,30)",
               "-font", MARKER, "-pointsize", 96, "-gravity", "north", "-annotate", "+0+30", amount,
               "-font", HAND, "-pointsize", 27, "-fill", "rgb(30,30,40)", "-annotate", "+0+175", who,
               "-pointsize", 28, "-annotate", "+0+240", "PLEDGED - line %d" % (i % 5 + 1), out(n))
        grain(n, 0.5, 40 + i)
        finish(n)


def whiteboard():
    n = "Whiteboard"
    magick("-size", "768x512", "xc:rgb(240,242,240)", "-fill", "rgb(30,60,170)", "-font", MARKER, "-pointsize", 60,
           "-gravity", "northwest", "-annotate", "+30+20", "TONIGHT:", "-font", HAND, "-pointsize", 44,
           "-annotate", "+40+110", "- sampler is DEAD (again)", "-annotate", "+40+170", "- live drums all night!!",
           "-annotate", "+40+230", "- 5 guest voices, 1 mic", "-fill", "rgb(200,30,40)", "-annotate", "+40+290", "- RENT DUE AT SIGN-OFF",
           "-fill", "rgb(20,120,60)", "-annotate", "+40+360", "phones: 555-0193  lines 1-5", "-fill", "rgb(30,30,30)",
           "-annotate", "+430+430", "- mgmt (us)", out(n))
    grain(n, 0.25, 18)
    finish(n)


def clock():
    n = "Clock"
    import math
    ticks = []
    for i in range(12):
        a = math.radians(i * 30)
        ticks += ["-draw", "line %d,%d %d,%d" % (128 + 96 * math.sin(a), 128 - 96 * math.cos(a), 128 + 112 * math.sin(a), 128 - 112 * math.cos(a))]
    # 2:47 in the morning.
    ha, ma = math.radians((2 + 47 / 60) * 30), math.radians(47 * 6)
    magick("-size", "256x256", "xc:rgb(20,20,22)", "-fill", "rgb(244,244,236)", "-draw", "circle 128,128 128,6",
           "-stroke", "rgb(20,20,22)", "-strokewidth", 8, *ticks, "-strokewidth", 10,
           "-draw", "line 128,128 %d,%d" % (128 + 60 * math.sin(ha), 128 - 60 * math.cos(ha)), "-strokewidth", 6,
           "-draw", "line 128,128 %d,%d" % (128 + 96 * math.sin(ma), 128 - 96 * math.cos(ma)), out(n))
    finish(n)


def line_label():
    """The phone-line lamp board's face over the glass."""
    n = "LineBoard"
    args = ["-size", "1024x160", "xc:rgb(26,26,30)", "-fill", "rgb(220,220,210)", "-font", HEAVY, "-pointsize", 54,
            "-gravity", "west", "-annotate", "+28+0", "LINES", "-font", BOLD, "-pointsize", 40]
    for i in range(5):
        args += ["-annotate", f"+{300 + i*150}+0", str(i + 1)]
    magick(*args, out(n))
    finish(n)


def console_screen():
    n = "ConsoleScreen"
    rnd = random.Random(19)
    bars = []
    for i in range(48):
        h = rnd.randint(20, 150)
        bars += ["-draw", f"rectangle {20 + i*10},{230 - h} {27 + i*10},230"]
    magick("-size", "512x256", "xc:rgb(6,14,20)", "-fill", "rgb(60,230,140)", *bars, "-font", MONO, "-pointsize", 28,
           "-gravity", "northwest", "-annotate", "+20+12", "PGM OUT  -  LIVE  -  02:47", out(n))
    finish(n)


ALL = [foam, carpet, ceiling_tile, cr_wall, on_air, station_banner, pledge_banner, rent_banner, rent_sheet, rent_meter,
       posters, pledges, whiteboard, clock, line_label, console_screen]


def make_all(names=None):
    os.makedirs(OUT, exist_ok=True)
    for f in ALL:
        if not names or f.__name__ in names:
            f()


if __name__ == "__main__":
    make_all(sys.argv[1:])
    print("wrote", OUT)
