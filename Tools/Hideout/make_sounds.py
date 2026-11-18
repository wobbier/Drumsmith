#!/usr/bin/env python3
"""Writes the basement's room tone, Assets/Hideout/Sounds/*.wav, synthesised with ffmpeg (mono 22 kHz
16-bit WAV: small enough, and ffmpeg's own Vorbis encoder only writes stereo).

    python3 Tools/Hideout/make_sounds.py

Seamless loops (each one's tail is crossfaded over its own start, so the loop point has nothing to
click on): the furnace's rumble, the dying fluorescent tube's buzz, the box fan's whir, a pipe that
drips now and then, an amp humming on standby, and the band next door to the rehearsal space
(through the wall: nothing over 250 Hz). Mono: they're placed in the rooms as 3D sources
(Tools/Hideout/basement.py, garage.py, rehearsal.py).
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
    # The band next door, through a block wall: a 120 bpm rock beat (kick, snare, a bass riff) with
    # everything over 250 Hz gone; twelve bars, then they stop for four seconds to argue.
    beat = ("aevalsrc='"
            "if(lt(t,24),"
            "0.9*sin(2*PI*(55+70*exp(-30*mod(t,0.5)))*mod(t,0.5))*exp(-9*mod(t,0.5))"
            "+0.35*gt(mod(t+0.5,1),0.5)*exp(-14*mod(t+0.5,0.5))*sin(2*PI*190*t)"
            "+0.5*sin(2*PI*(41.2*(1+0.335*gt(mod(t,4),2)+0.5*gt(mod(t,4),3)))*t)*(0.6+0.4*exp(-4*mod(t,0.25)))"
            ",0)':d=28:s={r}").format(r=RATE)
    ffmpeg(["-f", "lavfi", "-i", beat, "-af", "lowpass=f=250,lowpass=f=250,volume=0.9,aecho=0.6:0.4:35:0.25"], os.path.join(OUT, "BandNextDoor.wav"))
    # A valve amp on standby: mains hum and its harmonics, quiet.
    loop("AmpHum", "anoisesrc=d={d}:c=pink:a=0.01:r={r}:s=9",
         "aeval='val(0)+0.08*sin(2*PI*60*t)+0.05*sin(2*PI*120*t)+0.02*sin(2*PI*180*t)',lowpass=f=900,volume=0.6", seconds=6.0, fade=1.0)
    # The studio's air handling: a soft, even hiss.
    loop("StudioAir", "anoisesrc=d={d}:c=pink:a=0.3:r={r}:s=11", "highpass=f=120,lowpass=f=1800,volume=0.35")
    for name in sorted(os.listdir(OUT)):
        print("wrote", os.path.join(OUT, name), os.path.getsize(os.path.join(OUT, name)), "bytes")


if __name__ == "__main__":
    main()
