#!/usr/bin/env python3
"""Draws Assets/Venues/StoryBasement/Textures/*.png with ImageMagick 7.

    python3 Tools/Venues/story_basement_textures.py

  CrtSnow      the CRT with no tape playing: snow and scanlines
  CrtTake      the camcorder's picture on the CRT: a still of the kit from the tripod (made from
               Art/Venues/StoryBasement/Scratch/camcorder_raw.png, a headless capture from the
               camcorder's spot; a dark stand-in if that isn't there), with REC and the counter
  CrtPause     the same frame held at the end of the take: PAUSE, a tracking band
  KitchenLino  the kitchen floor at the top of the stairs
  PhoneScreen  the phone on the amp, playing along
and the venue's ambience, Assets/Venues/StoryBasement/Ambience.wav: the hideout basement's own room
tone (Assets/Hideout/Sounds: the furnace, the box fan, the drip) mixed down with ffmpeg.
Deterministic (fixed noise seeds, metadata stripped).
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "Assets", "Venues", "StoryBasement", "Textures")
RAW = os.path.join(ROOT, "Art", "Venues", "StoryBasement", "Scratch", "camcorder_raw.png")
MAGICK = shutil.which("magick") or "/nix/store/s13s3r3pi67vj27s6ca7pbrxs2z4zjf6-imagemagick-7.1.2-31/bin/magick"


def font(spec, fallback):
    try:
        return subprocess.run(["fc-match", "-f", "%{file}", spec], capture_output=True, text=True).stdout.strip() or fallback
    except OSError:
        return fallback


OSD = font("DejaVu Sans Mono:bold", "DejaVu-Sans-Mono-Bold")
MARKER = os.path.join(ROOT, "Assets", "Fonts", "PermanentMarker-Regular.ttf")


def magick(*args):
    cmd = [MAGICK, *[str(a) for a in args]]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"magick failed: {' '.join(cmd)}\n{r.stderr}")


def out(name):
    return os.path.join(OUT, name + ".png")


def finish(name):
    # The game loads a cooked .dds twin even when the .png is newer: drop it so it's recooked.
    for twin in (out(name) + ".dds", out(name) + ".dds.d"):
        if os.path.isdir(twin):
            shutil.rmtree(twin)
        elif os.path.exists(twin):
            os.remove(twin)
    magick(out(name), "-strip", "-define", "png:exclude-chunks=date,time", out(name))


def scan(path, dark="gray60"):
    """Scanlines over a 320x240 picture."""
    magick(path, "(", "-size", "320x2", "xc:white", "-fill", dark, "-draw", "line 0,1 320,1", "-write", "mpr:scan", "+delete",
           "-size", "320x240", "tile:mpr:scan", ")", "-compose", "multiply", "-composite", path)


def snow():
    n = "CrtSnow"
    magick("-size", "160x120", "xc:gray50", "-seed", 4401, "-attenuate", 3, "+noise", "Random", "-colorspace", "gray",
           "-scale", "320x240!", "+level-colors", "rgb(16,18,30),rgb(205,212,235)", out(n))
    scan(out(n))
    magick(out(n), "-fill", "rgba(255,255,255,0.0)", "-stroke", "none", "-font", OSD, "-pointsize", 20, "-fill", "rgb(120,240,140)",
           "-annotate", "+18+34", "CH 3", out(n))
    finish(n)


def take_base(path):
    if os.path.isfile(RAW):
        # 4:3 from the middle of the capture, soft like tape, a little warm and saturated.
        # The capture carries the song's title card over the middle: smear it out first.
        magick(RAW, "-resize", "1920x1080!", "-region", "380x110+770+232", "-blur", "0x24", "+region", "-crop", "1200x900+360+40", "+repage",
               "-resize", "320x240!",
               "-modulate", "112,125,100", "-blur", "0x0.7", "-level", "4%,92%", path)
    else:
        magick("-size", "320x240", "gradient:rgb(70,50,40)-rgb(18,14,12)", path)


def take():
    n = "CrtTake"
    take_base(out(n))
    scan(out(n), "gray72")
    magick(out(n), "-font", OSD, "-pointsize", 19, "-fill", "rgb(255,40,30)", "-draw", "circle 26,25 33,25",
           "-fill", "white", "-stroke", "black", "-strokewidth", 1, "-annotate", "+40+32", "REC",
           "-annotate", "+214+222", "0:04:17", "-pointsize", 13, "-annotate", "+18+222", "SP", out(n))
    finish(n)


def pause():
    n = "CrtPause"
    take_base(out(n))
    magick(out(n), "-modulate", "100,70,100", "(", "-size", "320x14", "xc:gray50", "-seed", 4402, "-attenuate", 2, "+noise", "Random",
           "-colorspace", "gray", ")", "-geometry", "+0+176", "-compose", "screen", "-composite", out(n))
    scan(out(n), "gray66")
    magick(out(n), "-font", OSD, "-pointsize", 19, "-fill", "white", "-stroke", "black", "-strokewidth", 1, "-annotate", "+22+32",
           "PAUSE", "-fill", "white", "-draw", "rectangle 96,16 101,33 rectangle 106,16 111,33",
           "-annotate", "+214+222", "0:21:44", "-pointsize", 13, "-annotate", "+18+222", "SP", out(n))
    finish(n)


def lino():
    n = "KitchenLino"
    magick("-size", "64x64", "pattern:checkerboard", "-scale", "256x256", "+level-colors", "rgb(70,110,90),rgb(225,214,180)",
           "(", "+clone", "-seed", 4403, "-attenuate", 0.35, "+noise", "Gaussian", "-colorspace", "gray", ")", "-compose", "overlay",
           "-composite", out(n))
    finish(n)


def phone():
    n = "PhoneScreen"
    bars = " ".join(f"rectangle {14 + i * 10},{150 - h} {20 + i * 10},150" for i, h in enumerate((20, 46, 30, 64, 40, 72, 52, 28, 58, 34)))
    magick("-size", "128x256", "gradient:rgb(40,30,80)-rgb(10,10,22)", "-fill", "rgb(120,200,255)", "-draw", bars,
           "-fill", "rgb(230,230,240)", "-draw", "rectangle 14,190 114,194", "-fill", "rgb(120,200,255)", "-draw", "rectangle 14,190 60,194",
           "-draw", "circle 64,226 64,212", "-fill", "rgb(10,10,22)", "-draw", "polygon 60,218 60,234 72,226", out(n))
    finish(n)


def ambience():
    snd = os.path.join(ROOT, "Assets", "Hideout", "Sounds")
    path = os.path.join(os.path.dirname(OUT), "Ambience.wav")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for clip in ("Furnace", "FanWhir", "Drip"):
        cmd += ["-stream_loop", "2", "-i", os.path.join(snd, clip + ".wav")]
    cmd += ["-filter_complex", "[0]volume=0.9[a];[1]volume=0.55[b];[2]volume=0.5[c];[a][b][c]amix=inputs=3:normalize=0,atrim=0:24",
            "-ac", "1", "-ar", "22050", "-c:a", "pcm_s16le", "-fflags", "+bitexact", "-flags:a", "+bitexact", "-map_metadata", "-1", path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"ffmpeg failed: {r.stderr}")


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in (snow, take, pause, lino, phone, ambience):
        f()
    print("textures in", OUT, "(camcorder still from capture)" if os.path.isfile(RAW) else "(camcorder still: stand-in)")


if __name__ == "__main__":
    main()
