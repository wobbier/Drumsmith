"""The Dead End Dive Bar's paint shop: every texture the room uses, drawn with ImageMagick 7, and
the league shirts (copies of the game's crowd torsos bound to a recoloured atlas).

Deterministic (fixed seeds, metadata stripped), so a rerun gives the same files. Called from
make_story_dive_bar.py; run on its own to redraw only the pictures:

    python3 Tools/Venues/story_dive_bar_art.py

All names are made up (the beers, the bands, the league)."""
import glob
import os
import random
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
VENUE = os.path.join(ROOT, "Assets", "Venues", "StoryDiveBar")
TEX = os.path.join(VENUE, "Textures")
MODELS = os.path.join(VENUE, "Models")
TEX_REL = "Assets/Venues/StoryDiveBar/Textures/"
MODELS_REL = "Assets/Venues/StoryDiveBar/Models/"

MARKER = os.path.join(ROOT, "Assets", "Fonts", "PermanentMarker-Regular.ttf")
HAND = os.path.join(ROOT, "Assets", "Fonts", "GochiHand-Regular.ttf")
HEAVY = "DejaVu-Sans-Condensed-Bold"
SERIF = "DejaVu-Serif-Condensed-Bold-Italic"
SCRIPT = "FreeSerif-Bold-Italic"


def _magick_bin():
    found = shutil.which("magick")
    if found:
        return found
    for path in sorted(glob.glob("/nix/store/*-imagemagick-7*/bin/magick")):
        return path
    return None


MAGICK = _magick_bin()


def magick(*args):
    cmd = [MAGICK, *[str(a) for a in args]]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"magick failed: {' '.join(cmd)}\n{r.stderr}")


def out(name):
    return os.path.join(TEX, name + ".png")


def tmp(name):
    return os.path.join(TEX, "_" + name + ".png")


def finish(name):
    magick(out(name), "-strip", "-define", "png:exclude-chunks=date,time", out(name))
    for t in glob.glob(os.path.join(TEX, "_*.png")):
        os.remove(t)


def grain(path, amount=0.3, seed=1):
    magick(path, "(", "+clone", "-seed", seed, "-attenuate", amount, "+noise", "Gaussian", "-colorspace", "gray", ")",
           "-compose", "overlay", "-composite", path)


def mottle(path, w, h, seed, lo="70%"):
    magick("-size", f"{w}x{h}", "-seed", seed, "plasma:fractal", "-colorspace", "gray", "-blur", "0x4", "-auto-level",
           "+level", f"{lo},100%", tmp("mottle"))
    magick(path, tmp("mottle"), "-compose", "multiply", "-composite", path)


# ---- surfaces ---------------------------------------------------------------------------------

def floor():
    """Worn oxblood-and-black lino squares (8 x 8 over 2.4 m), scuffed paths, sticky rings."""
    rnd = random.Random(7)
    s, n = 1024, 8
    cell = s // n
    draws = []
    for i in range(n):
        for j in range(n):
            v = rnd.randint(-8, 8)
            c = (128 + v, 40 + v // 2, 34 + v // 2) if (i + j) % 2 else (44 + v // 2, 40 + v // 2, 38 + v // 2)
            draws += ["-fill", "rgb(%d,%d,%d)" % c, "-draw", f"rectangle {i*cell+2},{j*cell+2} {i*cell+cell-2},{j*cell+cell-2}"]
    magick("-size", f"{s}x{s}", "xc:rgb(40,34,30)", *draws, out("Floor"))
    mottle(out("Floor"), s, s, 9, "55%")
    rings, blots = [], []
    for _ in range(14):
        cx, cy, r = rnd.randint(0, s), rnd.randint(0, s), rnd.randint(14, 26)
        rings += ["-draw", f"circle {cx},{cy} {cx+r},{cy}"]
    for _ in range(9):
        cx, cy, r = rnd.randint(0, s), rnd.randint(0, s), rnd.randint(40, 130)
        blots += ["-draw", f"ellipse {cx},{cy} {r},{int(r*.6)} 0,360"]
    magick(out("Floor"), "(", "-size", f"{s}x{s}", "xc:none", "-fill", "rgba(70,48,18,0.40)", *blots, "-blur", "0x14", ")",
           "-compose", "over", "-composite", "-fill", "none", "-stroke", "rgba(120,90,40,0.45)", "-strokewidth", 3, *rings,
           out("Floor"))
    grain(out("Floor"), 0.6, 8)
    finish("Floor")


def wood(name, light, dark, seed, w=512, h=512, planks=0):
    """Grain running down the picture; planks: vertical tongue-and-groove lines."""
    magick("-size", f"96x{h}", "-seed", seed, "plasma:fractal", "-colorspace", "gray", "-resize", f"{w}x{h}!",
           "-motion-blur", "0x18+90", "-auto-level", "+level-colors", f"{dark},{light}", out(name))
    if planks:
        step = w // planks
        lines = []
        for i in range(planks):
            lines += ["-draw", f"rectangle {i*step},0 {i*step+5},{h}"]
        magick(out(name), "-fill", "rgba(10,6,4,0.85)", *lines, out(name))
    grain(out(name), 0.35, seed)
    finish(name)


def plaster():
    """Nicotine-cream paint gone brown towards the ceiling, a hundred thumbtack holes."""
    rnd = random.Random(21)
    s = 512
    magick("-size", f"{s}x{s}", "gradient:rgb(96,74,48)-rgb(150,120,78)", out("Plaster"))
    mottle(out("Plaster"), s, s, 22, "62%")
    holes = []
    for _ in range(90):
        x, y = rnd.randint(0, s), rnd.randint(0, s)
        holes += ["-draw", f"point {x},{y}"]
    magick(out("Plaster"), "-fill", "rgb(30,22,14)", *holes, out("Plaster"))
    grain(out("Plaster"), 0.5, 23)
    finish("Plaster")


def brick():
    """Brick painted black behind the stage, scuffed at shoulder height."""
    w, h, bw, bh = 512, 512, 128, 42
    draws = []
    rnd = random.Random(31)
    for row in range(h // bh + 1):
        shift = 0 if row % 2 == 0 else bw // 2
        for col in range(-1, w // bw + 1):
            v = rnd.randint(-6, 8)
            draws += ["-fill", "rgb(%d,%d,%d)" % (34 + v, 32 + v, 34 + v), "-draw",
                      f"rectangle {col*bw+shift+3},{row*bh+3} {col*bw+shift+bw-3},{row*bh+bh-3}"]
    magick("-size", f"{w}x{h}", "xc:rgb(14,13,14)", *draws, out("Brick"))
    mottle(out("Brick"), w, h, 32, "60%")
    grain(out("Brick"), 0.5, 33)
    finish("Brick")


def felt():
    magick("-size", "256x256", "xc:rgb(28,112,58)", out("Felt"))
    mottle(out("Felt"), 256, 256, 41, "84%")
    grain(out("Felt"), 0.4, 42)
    finish("Felt")


def cover():
    """The table cover: heavy black-brown vinyl with creases."""
    magick("-size", "512x256", "xc:rgb(46,34,30)", "(", "-size", "64x256", "-seed", 51, "plasma:fractal", "-colorspace",
           "gray", "-resize", "512x256!", "-motion-blur", "0x30+0", "-auto-level", "+level", "62%,100%", ")",
           "-compose", "multiply", "-composite", out("Cover"))
    magick(out("Cover"), "-gravity", "center", "-font", HEAVY, "-pointsize", 34, "-fill", "rgba(200,170,90,0.55)",
           "-annotate", "+0+0", "DEAD END POOL LEAGUE", out("Cover"))
    grain(out("Cover"), 0.4, 52)
    finish("Cover")


# ---- neon -------------------------------------------------------------------------------------

def neon(name, lines, color, w=1024, h=320, border=None, font=HEAVY):
    """Glowing tube letters on a black board. lines: [(text, pointsize, y offset, font or None)].
    The same picture is the diffuse and the emissive map, so the board stays black."""
    text = []
    for t, size, dy, f in lines:
        text += ["-font", f or font, "-pointsize", size, "-annotate", f"+0{dy:+d}", t]
    frame = []
    if border:
        frame = ["-draw", f"roundrectangle 18,18 {w-18},{h-18} 40,40"]
    magick("-size", f"{w}x{h}", "xc:black", "-gravity", "center", "-fill", "none", "-stroke", color, "-strokewidth", 26,
           *text, *frame, "-blur", "0x18", tmp("glow"))
    magick("-size", f"{w}x{h}", "xc:black", "-gravity", "center", "-fill", "none", "-stroke", color, "-strokewidth", 9,
           *text, *frame, tmp("tube"))
    magick("-size", f"{w}x{h}", "xc:black", "-gravity", "center", "-fill", "none", "-stroke", "rgb(255,245,235)",
           "-strokewidth", 3, *text, *frame, tmp("core"))
    magick(tmp("glow"), tmp("tube"), "-compose", "screen", "-composite", tmp("core"), "-compose", "screen", "-composite",
           out(name))
    finish(name)


def neons():
    neon("NeonStag", [("STAG RIVER", 120, -40, None), ("LAGER", 92, 82, SERIF)], "rgb(255,150,20)", border=True)
    neon("NeonKnuckle", [("Old Knuckle", 132, -30, SCRIPT), ("ALE", 80, 92, None)], "rgb(255,40,60)")
    neon("NeonCold", [("ice cold", 150, -6, SCRIPT)], "rgb(40,170,255)", h=256)
    neon("NeonDeadEnd", [("THE DEAD END", 140, 0, None)], "rgb(255,40,190)", w=1280, h=256, border=True)
    neon("NeonLastCall", [("LAST CALL", 150, 0, None)], "rgb(255,30,24)", h=256)
    neon("NeonPool", [("8", 190, 0, None)], "rgb(80,255,120)", w=256, h=256, border=True)
    neon("NeonOpen", [("OPEN", 130, 0, None)], "rgb(255,70,40)", w=512, h=256, border=True)


# ---- paper and paint --------------------------------------------------------------------------

def chalkboard():
    """The league's board above the table."""
    w, h = 768, 512
    magick("-size", f"{w}x{h}", "xc:rgb(26,34,30)", out("Chalk"))
    mottle(out("Chalk"), w, h, 61, "72%")
    rows = [("THURSDAY", 60, 30), ("8-BALL LEAGUE", 52, 100)]
    ann = []
    for t, size, y in rows:
        ann += ["-pointsize", size, "-annotate", f"+0+{y}", t]
    magick(out("Chalk"), "-gravity", "north", "-font", MARKER, "-fill", "rgb(232,232,220)", *ann, out("Chalk"))
    teams = [("CUE BALLS", "IIII I"), ("SCRATCH CATS", "IIII"), ("RACK CITY", "III"), ("8 & OUT", "II")]
    ann = []
    for i, (team, tally) in enumerate(teams):
        y = 205 + i * 66
        ann += ["-pointsize", 54, "-annotate", f"+44+{y}", team, "-annotate", f"+520+{y}", tally]
    magick(out("Chalk"), "-gravity", "northwest", "-font", HAND, "-fill", "rgb(250,240,170)", *ann, out("Chalk"))
    magick(out("Chalk"), "-stroke", "rgb(220,220,210)", "-strokewidth", 3, "-draw", "line 40,190 728,190", out("Chalk"))
    grain(out("Chalk"), 0.5, 62)
    magick(out("Chalk"), "-bordercolor", "rgb(92,60,32)", "-border", 22, out("Chalk"))
    finish("Chalk")


def dartboard():
    s, c = 512, 256
    rings = [(250, "rgb(12,12,12)")]
    draws = ["-fill", "rgb(12,12,12)", "-draw", f"circle {c},{c} {c+250},{c}"]
    import math
    for r_out, r_in, alt in [(196, 182, ("rgb(190,30,30)", "rgb(30,140,60)")), (182, 118, ("rgb(20,20,20)", "rgb(230,220,190)")),
                             (118, 104, ("rgb(190,30,30)", "rgb(30,140,60)")), (104, 24, ("rgb(20,20,20)", "rgb(230,220,190)"))]:
        for k in range(20):
            a0, a1 = (k - .5) * 18 - 90, (k + .5) * 18 - 90
            pts = []
            for a in (a0, a1):
                pts.append((c + r_out * math.cos(math.radians(a)), c + r_out * math.sin(math.radians(a))))
            for a in (a1, a0):
                pts.append((c + r_in * math.cos(math.radians(a)), c + r_in * math.sin(math.radians(a))))
            draws += ["-fill", alt[k % 2], "-draw", "polygon " + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)]
    draws += ["-fill", "rgb(30,140,60)", "-draw", f"circle {c},{c} {c+24},{c}", "-fill", "rgb(190,30,30)",
              "-draw", f"circle {c},{c} {c+10},{c}"]
    magick("-size", f"{s}x{s}", "xc:rgb(60,40,24)", *draws, out("Dartboard"))
    grain(out("Dartboard"), 0.4, 71)
    finish("Dartboard")


def envelope():
    w, h = 512, 320
    magick("-size", f"{w}x{h}", "xc:rgb(196,160,104)", out("Envelope"))
    mottle(out("Envelope"), w, h, 81, "82%")
    magick(out("Envelope"), "-stroke", "rgba(120,90,50,0.8)", "-strokewidth", 4, "-fill", "none",
           "-draw", f"polyline 0,0 {w//2},{int(h*.55)} {w},0", "-stroke", "none", "-gravity", "center", "-font", MARKER,
           "-fill", "rgb(30,30,40)", "-pointsize", 96, "-annotate", "-6x-6+0+40", "DOOR",
           "-pointsize", 40, "-annotate", "-4x-4+150+-110", "$$$", out("Envelope"))
    grain(out("Envelope"), 0.3, 82)
    finish("Envelope")


def poster(name, band, line2, date, bg, ink, seed):
    w, h = 512, 720
    magick("-size", f"{w}x{h}", f"xc:{bg}", "-gravity", "north", "-font", HEAVY, "-fill", ink, "-pointsize", 74,
           "-annotate", "+0+60", band.replace(" ", "\n"), "-font", MARKER, "-pointsize", 46, "-annotate", "+0+420", line2,
           "-font", HEAVY, "-pointsize", 40, "-annotate", "+0+560", date, out(name))
    grain(out(name), 0.8, seed)
    finish(name)


def posters():
    poster("PosterA", "FERAL MAILBOX", "w/ guests", "FRI - $5 AT THE DOOR", "rgb(240,200,60)", "black", 91)
    poster("PosterB", "THE CRANKY SAINTS", "LIVE!", "SAT NITE - NO COVER", "rgb(230,90,70)", "black", 92)
    poster("PosterC", "SLOW LORIS", "+ the Mopes", "SUN - ALL AGES MATINEE", "rgb(120,200,210)", "black", 93)
    # The house rules: printed, sun-bleached, taped by the table.
    magick("-size", "512x384", "xc:rgb(236,230,214)", "-gravity", "north", "-font", HEAVY, "-fill", "rgb(20,20,20)",
           "-pointsize", 46, "-annotate", "+0+28", "HOUSE RULES", "-font", HAND, "-pointsize", 36, "-gravity", "northwest",
           "-annotate", "+40+110", "1. NO DANCING ON THE TABLE", "-annotate", "+40+160", "2. LOSER RACKS",
           "-annotate", "+40+210", "3. TAB CLOSES AT LAST CALL", "-annotate", "+40+260", "4. BAND GETS THE DOOR",
           out("Rules"))
    grain(out("Rules"), 0.6, 94)
    finish("Rules")


def menu():
    """The price board over the taps."""
    w, h = 768, 256
    magick("-size", f"{w}x{h}", "xc:rgb(16,14,12)", "-gravity", "west", "-font", HEAVY, "-fill", "rgb(240,230,200)",
           "-pointsize", 44, "-annotate", "+30-62", "PINTS  .......  $5", "-annotate", "+30+0", "PITCHERS  ...  $14",
           "-annotate", "+30+62", "SHOTS  .......  $4", out("Menu"))
    grain(out("Menu"), 0.4, 101)
    finish("Menu")


def labels():
    """A strip of made-up liquor labels, so the bottles in front of the mirror aren't all the same."""
    w, h = 512, 128
    cols = ["rgb(200,40,30)", "rgb(230,200,80)", "rgb(40,90,170)", "rgb(240,240,230)", "rgb(30,120,60)", "rgb(20,20,20)"]
    draws = []
    for i, c in enumerate(cols):
        x0 = i * (w // len(cols))
        draws += ["-fill", c, "-draw", f"rectangle {x0},20 {x0 + w // len(cols) - 4},108"]
    magick("-size", f"{w}x{h}", "xc:rgb(60,40,20)", *draws, out("Labels"))
    finish("Labels")


def all_textures():
    if not MAGICK:
        print("ImageMagick 7 not found: keeping the textures already in", TEX)
        return
    os.makedirs(TEX, exist_ok=True)
    floor()
    wood("Panel", "rgb(92,56,30)", "rgb(40,22,12)", 11, planks=6)
    wood("BarTop", "rgb(120,66,30)", "rgb(58,28,12)", 12)
    wood("Rail", "rgb(70,40,22)", "rgb(28,16,8)", 13)
    plaster()
    brick()
    felt()
    cover()
    neons()
    chalkboard()
    dartboard()
    envelope()
    posters()
    menu()
    labels()


# ---- league shirts ----------------------------------------------------------------------------

# The crowd pieces' torsos sample one 30 px swatch each from the Town atlas; the league shirt is
# that swatch (and the sleeve swatch next to it) painted mustard in a copy of the atlas.
SHIRT_CELLS = [(625, 1728), (685, 1728), (685, 1788), (655, 1758), (655, 1788), (715, 1758), (715, 1818), (565, 1728)]
SHIRT = "rgb(226,168,34)"


def league_atlas():
    src = os.path.join(ROOT, "Assets", "Models", "Venue", "PolygonTown_01_A.png")
    dst = os.path.join(MODELS, "LeagueShirts.png")
    draws = []
    for x, y in SHIRT_CELLS:
        draws += ["-draw", f"rectangle {x},{y} {x+29},{y+29}"]
    magick(src, "-fill", SHIRT, *draws, "-strip", "-define", "png:exclude-chunks=date,time", dst)


LEAGUE_PEOPLE = ("Son_01", "Mother_01", "Rigged", "ShopKeeper_01", "Daughter_01")


def league_torsos():
    """Torso copies that read the league atlas. Returns nothing; files land in Models/."""
    os.makedirs(MODELS, exist_ok=True)
    with open(os.path.join(MODELS, "League.mtl"), "w", newline="\n") as f:
        f.write("newmtl League\nKd 1 1 1\nKs 0 0 0\nNs 0\nillum 1\nmap_Kd LeagueShirts.png\n")
    for person in LEAGUE_PEOPLE:
        src = os.path.join(ROOT, "Assets", "Models", "People", "Crowd", person, "Torso.obj")
        lines = open(src).read().splitlines()
        lines = ["mtllib League.mtl" if l.startswith("mtllib") else "usemtl League" if l.startswith("usemtl") else l
                 for l in lines]
        lines.insert(0, f"# League shirt copy of Assets/Models/People/Crowd/{person}/Torso.obj (material swapped)")
        data = "\n".join(lines) + "\n"
        path = os.path.join(MODELS, f"League_{person}_Torso.obj")
        if not os.path.exists(path) or open(path).read() != data:
            with open(path, "w", newline="\n") as f:
                f.write(data)
    if MAGICK:
        league_atlas()


if __name__ == "__main__":
    all_textures()
    league_torsos()
    print("textures in", TEX)
