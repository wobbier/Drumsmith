"""The roller rink's textures, drawn with ImageMagick 7 into Assets/Venues/StoryRollerRink/Models/.

Palette.png (the flat swatches every rink mesh samples), Maple.png (the oval's boards with the
painted lane line and centre circle, mapped across the oval's bounding box), Carpet.png (the
cosmic carpet on the rail and the walls, tiled), Glitter.png (the booth's fascia) and the signs.
All names are made up. Deterministic: fixed seeds, metadata stripped.
"""
import glob
import os
import random
import shutil
import subprocess
import sys

from story_roller_rink_meshes import MODELS, SWATCHES, CELL

HEAVY = "Noto-Sans-Black"
HEAVY_ITALIC = "Noto-Sans-Black-Italic"
SERIF = "Noto-Serif-Display-Black-Italic"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MARKER = os.path.join(ROOT, "Assets", "Fonts", "PermanentMarker-Regular.ttf")


def magick_bin():
    found = shutil.which("magick")
    if found:
        return found
    cands = sorted(glob.glob("/nix/store/*-imagemagick-7*/bin/magick"))
    return cands[-1] if cands else None


MAGICK = magick_bin()


def magick(*args):
    cmd = [MAGICK, *[str(a) for a in args]]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"magick failed: {' '.join(cmd)}\n{r.stderr}")


def out(name):
    return os.path.join(MODELS, name + ".png")


def finish(name):
    for twin in (out(name) + ".dds", out(name) + ".dds.d"):
        if os.path.exists(twin):
            os.remove(twin)   # the game prefers a cooked twin even when the .png is newer
    magick(out(name), "-strip", "-define", "png:exclude-chunks=date,time", out(name))


def palette():
    draws = []
    for i, (_, hexc) in enumerate(SWATCHES):
        c, r = i % 16, i // 16
        draws += ["-fill", hexc, "-draw", f"rectangle {c*CELL},{r*CELL} {c*CELL+CELL-1},{r*CELL+CELL-1}"]
    magick("-size", "256x256", "xc:#808080", *draws, out("Palette"))
    finish("Palette")


def maple(cx, cz, a, b, x0, x1, z0, z1, lane, centre_r):
    """The boards. The image spans x0..x1 (left to right) and z1..z0 (top to bottom)."""
    W, H = 1536, 768
    sx, sz = W / (x1 - x0), H / (z1 - z0)
    px = lambda x: (x - x0) * sx
    pz = lambda z: (z1 - z) * sz
    rnd = random.Random(606)
    tmp = out("_maple_grain")
    # Grain: noise stretched along the boards (x).
    magick("-size", f"{W}x{H}", "xc:#c98f4a", "-seed", 61, "-attenuate", 0.35, "+noise", "Gaussian",
           "-motion-blur", "0x40+0", "-modulate", "100,85", tmp)
    draws = []
    plank = 0.085 * sz
    y = 0.0
    while y < H:
        shade = rnd.choice(["#e0ad66", "#d49c55", "#c88d48", "#dba862", "#bf8443"])
        draws += ["-fill", shade + "70", "-draw", f"rectangle 0,{y:.1f} {W},{y+plank:.1f}"]
        draws += ["-fill", "#6e4420a0", "-draw", f"line 0,{y:.1f} {W},{y:.1f}"]
        xj = rnd.uniform(0, 300)
        while xj < W:
            draws += ["-draw", f"line {xj:.1f},{y:.1f} {xj:.1f},{y+plank:.1f}"]
            xj += rnd.uniform(240, 520)
        y += plank
    magick(tmp, *draws, tmp)
    # Paint: the lane line, the centre circle and its dot, a little star at each end.
    paint = []
    for la, lb, col, w in [(a - lane, b - lane, "#ff6a14", 0.11), (a - lane - 0.25, b - lane - 0.25, "#ffd23a", 0.05)]:
        paint += ["-fill", "none", "-stroke", col, "-strokewidth", f"{w*sz:.1f}",
                  "-draw", f"ellipse {px(cx):.1f},{pz(cz):.1f} {la*sx:.1f},{lb*sz:.1f} 0,360"]
    paint += ["-fill", "none", "-stroke", "#ff2f9a", "-strokewidth", f"{0.12*sz:.1f}",
              "-draw", f"ellipse {px(cx):.1f},{pz(cz):.1f} {centre_r*sx:.1f},{centre_r*sz:.1f} 0,360"]
    paint += ["-stroke", "#28e6ff", "-strokewidth", f"{0.05*sz:.1f}",
              "-draw", f"ellipse {px(cx):.1f},{pz(cz):.1f} {(centre_r-0.2)*sx:.1f},{(centre_r-0.2)*sz:.1f} 0,360"]
    paint += ["-stroke", "none", "-fill", "#ff2f9a", "-draw",
              f"ellipse {px(cx):.1f},{pz(cz):.1f} {0.35*sx:.1f},{0.35*sz:.1f} 0,360"]
    magick(tmp, *paint, "-alpha", "off", out("Maple"))
    os.remove(tmp)
    finish("Maple")


def carpet():
    """Cosmic arcade carpet: midnight purple, neon squiggles, rings, triangles and stars. Tiles."""
    S = 512
    rnd = random.Random(1986)
    cols = ["#ff2f9a", "#28e6ff", "#ffd23a", "#8dff3a", "#ff7a1a", "#b45cff"]
    d = []
    for _ in range(44):
        x, y = rnd.uniform(0, S), rnd.uniform(0, S)
        c = rnd.choice(cols)
        kind = rnd.random()
        for ox in (-S, 0, S):
            for oy in (-S, 0, S):
                X, Y = x + ox, y + oy
                if X < -60 or X > S + 60 or Y < -60 or Y > S + 60:
                    continue
                if kind < 0.3:
                    d += ["-fill", "none", "-stroke", c, "-strokewidth", 5, "-draw", f"circle {X:.0f},{Y:.0f} {X+16:.0f},{Y:.0f}"]
                elif kind < 0.55:
                    d += ["-fill", c, "-stroke", "none", "-draw",
                          f"polygon {X:.0f},{Y-18:.0f} {X+16:.0f},{Y+12:.0f} {X-16:.0f},{Y+12:.0f}"]
                elif kind < 0.8:
                    pts = " ".join(f"{X+k*9:.0f},{Y+(8 if k%2 else -8):.0f}" for k in range(6))
                    d += ["-fill", "none", "-stroke", c, "-strokewidth", 5, "-draw", f"polyline {pts}"]
                else:
                    d += ["-fill", c, "-stroke", "none", "-draw", f"circle {X:.0f},{Y:.0f} {X+5:.0f},{Y:.0f}"]
    magick("-size", f"{S}x{S}", "xc:#1c1036", "-seed", 7, "-attenuate", 0.25, "+noise", "Gaussian", *d,
           "-alpha", "off", out("Carpet"))
    finish("Carpet")


def glitter():
    S = 256
    magick("-size", f"{S}x{S}", "xc:#5a1fb0", "-seed", 11, "-attenuate", 1.0, "+noise", "Random",
           "-channel", "RGB", "-threshold", "88%", "+channel", "(", "-size", f"{S}x{S}", "xc:#5a1fb0", ")",
           "-compose", "lighten", "-composite", "-alpha", "off", out("Glitter"))
    finish("Glitter")


def sign(name, w, h, bg, parts):
    """parts: (text, font, pointsize, fill, stroke, gravity, dx, dy)."""
    args = ["-size", f"{w}x{h}", f"xc:{bg}"]
    for text, font, size, fill, stroke, grav, dx, dy in parts:
        args += ["-gravity", grav, "-font", font, "-pointsize", size]
        if stroke:
            args += ["-fill", "none", "-stroke", stroke, "-strokewidth", max(4, size // 10),
                     "-annotate", f"+{dx}+{dy}", text]
        args += ["-stroke", "none", "-fill", fill, "-annotate", f"+{dx}+{dy}", text]
    magick(*args, "-alpha", "off", out(name))
    finish(name)


def signs():
    sign("SignRink", 1024, 256, "#0a0614", [
        ("Moonbeam", SERIF, 140, "#ffd6f0", "#ff2f9a", "NorthWest", 40, 0),
        ("ROLLERDROME", HEAVY, 66, "#d8fbff", "#28e6ff", "SouthEast", 40, 14)])
    sign("SignAdults", 1024, 192, "#0a0614", [
        ("ADULTS ONLY  21+", HEAVY_ITALIC, 96, "#fff1b8", "#ff7a1a", "Center", 0, -20),
        ("THURSDAYS  9PM - 1AM  ·  LIVE BAND IN THE BOOTH", HEAVY, 34, "#d8fbff", None, "South", 0, 10)])
    sign("SignRental", 768, 192, "#0a0614", [
        ("SKATE RENTAL", HEAVY_ITALIC, 104, "#fff1b8", "#ff7a1a", "Center", 0, 0)])
    sign("SignSnack", 768, 192, "#0a0614", [
        ("SNACK BAR", HEAVY_ITALIC, 112, "#e8fff0", "#8dff3a", "Center", 0, 0)])
    sign("MenuBoard", 512, 384, "#1a1424", [
        ("NACHOS ......... 3.50", "Liberation-Mono-Bold", 32, "#ffd23a", None, "NorthWest", 26, 30),
        ("HOT DOG ........ 2.75", "Liberation-Mono-Bold", 32, "#f4f1ea", None, "NorthWest", 26, 80),
        ("POPCORN ........ 2.00", "Liberation-Mono-Bold", 32, "#f4f1ea", None, "NorthWest", 26, 130),
        ("SLUSH  (BLUE) .. 1.50", "Liberation-Mono-Bold", 32, "#28e6ff", None, "NorthWest", 26, 180),
        ("PIZZA SLICE .... 3.00", "Liberation-Mono-Bold", 32, "#f4f1ea", None, "NorthWest", 26, 230),
        ("nacho warmer is downstairs!", MARKER, 34, "#ff5ec4", None, "South", 0, 22)])
    for name, top, sub, col, glow in [
            ("BoardAllSkate", "ALL SKATE", "everybody on the floor", "#fff1b8", "#ff2f9a"),
            ("BoardTrio", "TRIO SKATE", "grab two friends", "#d8fbff", "#28e6ff"),
            ("BoardHandsUp", "HANDS UP!", "circle in the middle", "#fff1b8", "#ffd23a")]:
        sign(name, 1024, 320, "#07040f", [
            (top, HEAVY_ITALIC, 170, col, glow, "North", 0, 20),
            (sub, MARKER, 64, glow, None, "South", 0, 18)])
    sign("PosterCouples", 384, 512, "#ff5ec4", [
        ("COUPLES", HEAVY_ITALIC, 70, "#1b1f4a", None, "North", 0, 40),
        ("SKATE", HEAVY_ITALIC, 90, "#ffffff", "#1b1f4a", "North", 0, 120),
        ("10:30", HEAVY, 110, "#ffd23a", "#1b1f4a", "Center", 0, 70),
        ("lights down. hold hands.", MARKER, 30, "#1b1f4a", None, "South", 0, 30)])
    sign("PosterRules", 384, 512, "#f6e2b4", [
        ("RINK RULES", HEAVY, 52, "#b3122a", None, "North", 0, 30),
        ("1. skate counter-clockwise\n2. no backwards after 11\n3. no food on the floor\n4. help the new guy up\n5. have fun",
         "Liberation-Sans-Bold", 26, "#1b1f4a", None, "NorthWest", 30, 120)])
    sign("PosterDisco", 384, 512, "#28e6ff", [
        ("DISCO", HEAVY_ITALIC, 100, "#ffffff", "#8a3cff", "North", 0, 50),
        ("NIGHT", HEAVY_ITALIC, 100, "#ffd23a", "#8a3cff", "North", 0, 160),
        ("every thursday\nsince '79", MARKER, 44, "#1b1f4a", None, "South", 0, 50)])
    sign("SignDJ", 512, 160, "#0a0614", [("DJ BOOTH", HEAVY_ITALIC, 96, "#ffd6f0", "#ff2f9a", "Center", 0, 0)])


def build(rink):
    if not MAGICK:
        print("magick not found: keeping the textures already on disk")
        return
    os.makedirs(MODELS, exist_ok=True)
    palette()
    maple(*rink)
    carpet()
    glitter()
    signs()
