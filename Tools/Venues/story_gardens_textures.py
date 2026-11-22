#!/usr/bin/env python3
"""Draws the Gardens' pictures into Assets/Venues/StoryGardens/Textures/ with ImageMagick 7.

    python3 Tools/Venues/story_gardens_textures.py

The ice and its markings, the rink-board ads (made-up local businesses), the centre-hung
scoreboard's faces, the generic rafter banners, the Canadian flag, the furled banner's canvas and
the dropped "YOUR BAND" banner. Deterministic (fixed seeds, metadata stripped). No real brands or
team logos: "MAPLE LEAF GARDENS" appears only as the building's name.
"""
import glob
import math
import os
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "Assets", "Venues", "StoryGardens", "Textures")

HEAVY = "DejaVu-Sans-Bold"
COND = "DejaVu-Sans-Condensed-Bold"
SERIF = "DejaVu-Serif-Condensed-Bold"
MONO = "Liberation-Mono-Bold"

BLUE = "rgb(18,44,120)"
RED = "rgb(196,22,28)"
WHITE = "rgb(244,244,238)"


def magick_bin():
    found = shutil.which("magick")
    if found:
        return found
    for path in sorted(glob.glob("/nix/store/*imagemagick-7*/bin/magick")):
        return path
    sys.exit("magick (ImageMagick 7) not found")


MAGICK = None


def magick(*args):
    global MAGICK
    MAGICK = MAGICK or magick_bin()
    cmd = [MAGICK, *[str(a) for a in args]]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"magick failed: {' '.join(cmd)}\n{r.stderr}")


def out(name):
    return os.path.join(OUT, name + ".png")


def finish(name):
    # The engine's cube faces sample the picture upside down: store it flipped so it reads.
    magick(out(name), "-flip", "-strip", "-define", "png:exclude-chunks=date,time", out(name))
    # A cooked twin older than the picture would be loaded instead of it: drop it to re-cook.
    twin = out(name) + ".dds"
    if os.path.exists(twin) and os.path.getmtime(twin) < os.path.getmtime(out(name)):
        os.remove(twin)
    if os.path.exists(twin + ".d"):
        os.remove(twin + ".d")


# ---- the ice -----------------------------------------------------------------------------------
# The picture covers the rink's box, x -26..26 by z -11.5..11.5, at 39.4 px a metre. Markings are
# symmetric both ways, so whichever way the cube face maps it the rink reads right.
IW, IH = 2048, 906
PX = IW / 52.0


def ice():
    def X(m):
        return IW / 2 + m * PX

    def Z(m):
        return IH / 2 + m * PX

    d = []

    def line(x, w, col):
        d.extend(["-fill", col, "-draw", f"rectangle {X(x) - w * PX / 2:.1f},0 {X(x) + w * PX / 2:.1f},{IH}"])

    def circle(x, z, r, col, w=0.07):
        d.extend(["-fill", "none", "-stroke", col, "-strokewidth", f"{w * PX:.1f}",
                  "-draw", f"circle {X(x):.1f},{Z(z):.1f} {X(x) + r * PX:.1f},{Z(z):.1f}", "-stroke", "none"])

    def dot(x, z, r, col):
        d.extend(["-fill", col, "-draw", f"circle {X(x):.1f},{Z(z):.1f} {X(x) + r * PX:.1f},{Z(z):.1f}"])

    line(0, 0.32, "rgb(200,40,44)")
    for s in (-1, 1):
        line(7.6 * s, 0.32, "rgb(40,80,170)")
        line(22.6 * s, 0.06, "rgb(200,40,44)")
        # Goal crease: a blue half disc in front of each goal line.
        cx = X(22.6 * s)
        r = 1.8 * PX
        a0, a1 = (90, 270) if s > 0 else (-90, 90)
        d.extend(["-fill", "rgb(140,180,225)", "-stroke", "rgb(200,40,44)", "-strokewidth", "2",
                  "-draw", f"ellipse {cx:.1f},{IH / 2:.1f} {r:.1f},{r:.1f} {a0},{a1}", "-stroke", "none"])
        for z in (-6.7, 6.7):
            circle(16.5 * s, z, 4.6, "rgb(200,40,44)")
            dot(16.5 * s, z, 0.32, "rgb(200,40,44)")
            dot(9.1 * s, z, 0.32, "rgb(200,40,44)")
    circle(0, 0, 4.6, "rgb(40,80,170)")
    dot(0, 0, 0.16, "rgb(40,80,170)")
    magick("-size", f"{IW}x{IH}", "xc:rgb(222,232,238)",
           "(", "-size", f"{IW // 4}x{IH // 4}", "-seed", 31, "plasma:fractal", "-colorspace", "gray", "-resize", f"{IW}x{IH}!",
           "-blur", "0x6", "-auto-level", "+level", "88%,100%", ")", "-compose", "multiply", "-composite",
           *d, out("Ice"))
    finish("Ice")


# ---- the boards ---------------------------------------------------------------------------------
ADS = [
    ("CARLTON ST.", "HOT DOGS & COFFEE", RED, WHITE),
    ("NORTHERN", "SKATE SHARPENING", BLUE, WHITE),
    ("MAPLE DAIRY", "SINCE 1931", WHITE, BLUE),
    ("CKHI 1050", "HOCKEY NIGHT RADIO", "rgb(232,180,20)", "rgb(20,20,20)"),
    ("BAY STREET TIRE", "WINTER READY", "rgb(20,110,70)", WHITE),
    ("WELCOME", "TO THE GARDENS", WHITE, RED),
]


def board_ads():
    """Six painted panels 2.33 m wide on the boards' white face, 2048 x 160 = 14 m x 1.07 m."""
    w, h = 2048, 160
    pw = w // len(ADS)
    draws = []
    for i, (big, small, bg, ink) in enumerate(ADS):
        x0 = i * pw + 10
        x1 = (i + 1) * pw - 10
        draws += ["-fill", bg, "-draw", f"rectangle {x0},22 {x1},128",
                  "-fill", ink, "-font", HEAVY, "-pointsize", 40 if len(big) < 12 else 30, "-gravity", "NorthWest",
                  "-annotate", f"+{x0 + 14}+30", big,
                  "-font", COND, "-pointsize", 24, "-annotate", f"+{x0 + 16}+84", small]
    magick("-size", f"{w}x{h}", "xc:" + WHITE, *draws,
           "-fill", "rgb(236,196,30)", "-draw", f"rectangle 0,136 {w},{h}", out("BoardAds"))
    finish("BoardAds")


# ---- the scoreboard -----------------------------------------------------------------------------
def scoreboard():
    w, h = 1024, 640
    amber = "rgb(255,176,60)"
    magick("-size", f"{w}x{h}", "xc:rgb(14,14,16)",
           "-fill", "rgb(150,18,22)", "-draw", f"rectangle 0,0 {w},118",
           "-fill", WHITE, "-font", SERIF, "-pointsize", 76, "-gravity", "North", "-annotate", "+0+16", "MAPLE LEAF GARDENS",
           "-fill", "rgb(40,40,46)", "-draw", "roundrectangle 40,150 330,420 14,14", "-draw", "roundrectangle 694,150 984,420 14,14",
           "-draw", "roundrectangle 380,170 644,330 14,14",
           "-fill", amber, "-font", HEAVY, "-pointsize", 44, "-annotate", "-327+160", "HOME",
           "-annotate", "+327+160", "GUEST", "-pointsize", 150, "-annotate", "-327+230", "0", "-annotate", "+327+230", "0",
           "-fill", "rgb(255,70,50)", "-font", MONO, "-pointsize", 112, "-annotate", "+0+190", "20:00",
           "-fill", amber, "-font", HEAVY, "-pointsize", 34, "-annotate", "+0+350", "PERIOD 3",
           "-fill", "rgb(30,30,34)", "-draw", f"rectangle 0,450 {w},{h}",
           "-fill", WHITE, "-font", HEAVY, "-pointsize", 58, "-annotate", "+0+470", "TONIGHT  ON HOME ICE",
           "-fill", amber, "-pointsize", 74, "-annotate", "+0+540", "YOUR BAND",
           out("Scoreboard"))
    # Bulb grain: a fine dot screen so it reads as an old lamp board.
    magick(out("Scoreboard"), "(", "-size", "6x6", "xc:white", "-fill", "rgb(150,150,150)", "-draw", "rectangle 4,0 5,5",
           "-draw", "rectangle 0,4 5,5", "-write", "mpr:dot", "+delete", "-size", f"{w}x{h}", "tile:mpr:dot", ")",
           "-compose", "multiply", "-composite", out("Scoreboard"))
    finish("Scoreboard")


def scoreboard_side():
    w, h = 1024, 320
    magick("-size", f"{w}x{h}", "xc:rgb(14,14,16)",
           "-fill", "rgb(150,18,22)", "-draw", f"rectangle 0,0 {w},90",
           "-fill", WHITE, "-font", HEAVY, "-pointsize", 54, "-gravity", "North", "-annotate", "+0+14", "CARLTON STREET",
           "-fill", "rgb(255,176,60)", "-font", MONO, "-pointsize", 120, "-annotate", "+0+130", "SOLD  OUT",
           out("ScoreboardSide"))
    finish("ScoreboardSide")


# ---- banners and the flag -----------------------------------------------------------------------
def leaf(cx, cy, s):
    """A simple eleven-point maple leaf as a polygon, centred, s = half height in px."""
    half = [(0, -1.0), (.13, -.74), (.30, -.82), (.24, -.36), (.50, -.62), (.55, -.48), (.80, -.53),
            (.70, -.27), (.84, -.18), (.46, .14), (.52, .30), (.06, .24), (.06, .62)]
    pts = half + [(-x, y) for x, y in reversed(half)]
    return " ".join(f"{cx + x * s:.1f},{cy + y * s:.1f}" for x, y in pts)


def canada_flag():
    w, h = 1024, 512
    magick("-size", f"{w}x{h}", "xc:" + WHITE, "-fill", RED, "-draw", f"rectangle 0,0 256,{h}",
           "-draw", f"rectangle 768,0 {w},{h}", "-draw", "polygon " + leaf(512, 262, 190), out("CanadaFlag"))
    finish("CanadaFlag")


BANNERS = [
    ("RafterBanner1", ["MAPLE", "LEAF", "GARDENS"], "EST. 1931", WHITE, BLUE),
    ("RafterBanner2", ["CARLTON", "STREET"], "TORONTO", BLUE, WHITE),
    ("RafterBanner3", ["HOME", "ICE"], "SINCE 1931", WHITE, BLUE),
    ("RafterBanner4", ["SOLD", "OUT"], "EVERY NIGHT", BLUE, WHITE),
    ("RafterBanner5", ["THE", "GREYS"], "TOP OF THE HOUSE", WHITE, RED),
]


def rafter_banner(name, lines, foot, bg, ink):
    w, h = 512, 1024
    draws = ["-fill", ink, "-draw", f"rectangle 18,18 {w - 18},30", "-draw", f"rectangle 18,{h - 160} {w - 18},{h - 148}"]
    y = 90
    for ln in lines:
        draws += ["-font", HEAVY, "-pointsize", 108 if len(ln) <= 5 else 88, "-gravity", "North", "-annotate", f"+0+{y}", ln]
        y += 150
    draws += ["-font", COND, "-pointsize", 46, "-annotate", f"+0+{h - 130}", foot]
    magick("-size", f"{w}x{h}", "xc:" + bg, *draws,
           "-fill", ink, "-draw", f"polygon 0,{h - 60} {w // 2},{h} {w},{h - 60} {w},{h} 0,{h}", out(name))
    finish(name)


def your_band():
    """The banner the band's name goes up on: royal blue, white letters, silver trim."""
    w, h = 768, 1280
    magick("-size", f"{w}x{h}", "xc:rgb(16,42,128)",
           "-fill", "rgb(206,210,218)", "-draw", f"rectangle 22,22 {w - 22},40", "-draw", f"rectangle 22,{h - 40} {w - 22},{h - 22}",
           "-draw", f"rectangle 22,22 40,{h - 22}", "-draw", f"rectangle {w - 40},22 {w - 22},{h - 22}",
           "-fill", WHITE, "-draw", "polygon " + leaf(w // 2, 250, 150),
           "-fill", RED, "-draw", "polygon " + leaf(w // 2, 250, 118),
           "-fill", WHITE, "-font", HEAVY, "-pointsize", 200, "-gravity", "North", "-annotate", "+0+450", "YOUR",
           "-annotate", "+0+680", "BAND",
           "-font", COND, "-pointsize", 54, "-annotate", "+0+960", "LIVE ON HOME ICE",
           "-fill", "rgb(206,210,218)", "-pointsize", 46, "-annotate", "+0+1060", "MAPLE LEAF GARDENS",
           out("YourBand"))
    finish("YourBand")


def fascia():
    """The balcony fascia's running name, cream on oxblood, 4096 x 256 = 40 m x 2.5 m."""
    w, h = 4096, 256
    magick("-size", f"{w}x{h}", "xc:rgb(96,20,24)",
           "-fill", "rgb(236,206,140)", "-draw", f"rectangle 0,14 {w},20", "-draw", f"rectangle 0,{h - 20} {w},{h - 14}",
           "-font", SERIF, "-pointsize", 150, "-gravity", "center", "-annotate", "-1024+0", "MAPLE LEAF GARDENS",
           "-annotate", "+1024+0", "MAPLE LEAF GARDENS", out("Fascia"))
    finish("Fascia")


def furled():
    """Rolled canvas: white with a blue edge peeking through the turns."""
    magick("-size", "256x256", "xc:" + WHITE, "-fill", "rgb(16,42,128)",
           *sum([["-draw", f"rectangle 0,{y} 256,{y + 8}"] for y in range(10, 256, 42)], []), out("Furled"))
    finish("Furled")


def main():
    os.makedirs(OUT, exist_ok=True)
    ice()
    board_ads()
    scoreboard()
    scoreboard_side()
    canada_flag()
    for b in BANNERS:
        rafter_banner(*b)
    your_band()
    fascia()
    furled()
    print("textures in", OUT)


if __name__ == "__main__":
    main()
