#!/usr/bin/env python3
"""Writes the basement's room tone, Assets/Hideout/Sounds/*.wav, synthesised with ffmpeg (mono 22 kHz
16-bit WAV: small enough, and ffmpeg's own Vorbis encoder only writes stereo).

    python3 Tools/Hideout/make_sounds.py

Seamless loops (each one's tail is crossfaded over its own start, so the loop point has nothing to
click on): the furnace's rumble, the dying fluorescent tube's buzz, the box fan's whir, and a pipe
that drips now and then. Mono: they're placed in the room as 3D sources (Tools/Hideout/basement.py).
"""
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "Assets", "Hideout", "Sounds")
RATE = 22050


def ffmpeg(args, path):
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args, "-ac", "1", "-ar", str(RATE), "-c:a", "pcm_s16le",
           "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:a", "+bitexact", path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"ffmpeg failed: {' '.join(cmd)}\n{r.stderr}")


def loop(name, source, chain, seconds=10.0, fade=2.0):
    """source: a lavfi source lasting seconds + fade; chain: filters on it. The last fade seconds
    are crossfaded over the start, so the file loops without a seam."""
    total = seconds + fade
    graph = (f"[0]{chain},asplit[a][b];[a]atrim=0:{seconds},asetpts=PTS-STARTPTS[main];"
             f"[b]atrim={seconds}:{total},asetpts=PTS-STARTPTS[tail];[tail][main]acrossfade=d={fade}:c1=tri:c2=tri[out]")
    ffmpeg(["-f", "lavfi", "-i", source.format(d=total, r=RATE), "-filter_complex", graph, "-map", "[out]"], os.path.join(OUT, name + ".wav"))


def main():
    os.makedirs(OUT, exist_ok=True)
    # The furnace: a low rumble with the burner's hum in it.
    loop("Furnace", "anoisesrc=d={d}:c=brown:a=0.7:r={r}:s=3",
         "lowpass=f=160,lowpass=f=160,volume=0.45,aeval='val(0)+0.05*sin(2*PI*55*t)+0.03*sin(2*PI*110*t)'")
    # The tube: mains buzz (120 Hz and its harmonics), a little rough.
    loop("TubeBuzz", "anoisesrc=d={d}:c=white:a=0.02:r={r}:s=5",
         "aeval='val(0)+0.12*sin(2*PI*120*t)+0.07*sin(2*PI*240*t)+0.02*gt(sin(2*PI*120*t),0)+0.03*sin(2*PI*360*t)',"
         "highpass=f=90,volume=0.5")
    # The box fan: air, chopped by the blades.
    loop("FanWhir", "anoisesrc=d={d}:c=pink:a=0.5:r={r}:s=7",
         "bandpass=f=700:w=900,tremolo=f=19:d=0.25,lowpass=f=2500,volume=28")
    # A drip from the pipes: two drops in eight seconds, a bright plink each, into near silence.
    drip = ("aevalsrc='0.35*sin(2*PI*(1400-500*mod(t,8))*mod(t,8))*exp(-38*mod(t,8))*lt(mod(t,8),0.15)"
            "+0.25*sin(2*PI*(1700-600*(mod(t,8)-5.3))*(mod(t,8)-5.3))*exp(-42*(mod(t,8)-5.3))*gte(mod(t,8),5.3)*lt(mod(t,8),5.45)'"
            ":d=8:s={r}".format(r=RATE))
    ffmpeg(["-f", "lavfi", "-i", drip, "-af", "aecho=0.8:0.5:60|140:0.3|0.15"], os.path.join(OUT, "Drip.wav"))
    for name in sorted(os.listdir(OUT)):
        print("wrote", os.path.join(OUT, name), os.path.getsize(os.path.join(OUT, name)), "bytes")


if __name__ == "__main__":
    main()
