"""The coffee shop's room tone, Assets/Venues/StoryCoffeeShop/Ambience.ogg, synthesised with ffmpeg: a
low murmur of conversation, cups on saucers now and then, the grinder once, the steam wand twice.
A seamless 24 s loop (the tail is crossfaded over the start). Deterministic seeds.
"""
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "Assets", "Venues", "StoryCoffeeShop", "Ambience.ogg")
RATE = 44100
SECONDS, FADE = 24.0, 3.0


def make():
    total = SECONDS + FADE
    # Murmur: two bands of pink noise, each breathing at its own slow rate like voices at tables.
    murmur = (f"anoisesrc=d={total}:c=pink:a=0.6:r={RATE}:s=11,bandpass=f=420:w=500,tremolo=f=0.7:d=0.5,"
              f"tremolo=f=3.1:d=0.35,volume=9")
    murmur2 = (f"anoisesrc=d={total}:c=pink:a=0.6:r={RATE}:s=23,bandpass=f=900:w=700,tremolo=f=0.45:d=0.6,"
               f"tremolo=f=4.3:d=0.4,volume=5")
    # Cups and spoons: short bright pings at fixed times.
    pings = "+".join(
        f"{a}*sin(2*PI*{f}*(t-{t0}))*exp(-30*(t-{t0}))*gte(t,{t0})*lt(t,{t0}+0.3)"
        for t0, f, a in ((1.3, 2650, 0.10), (1.42, 3900, 0.06), (5.8, 3100, 0.08), (9.2, 2400, 0.09), (9.31, 3600, 0.05),
                         (14.7, 2900, 0.08), (19.4, 3300, 0.07), (21.9, 2500, 0.09), (22.02, 3750, 0.05)))
    cups = f"aevalsrc='{pings}':d={total}:s={RATE}"
    # The steam wand (filtered hiss with a rising whine) and one burst of the grinder.
    steam = (f"anoisesrc=d={total}:c=white:a=0.5:r={RATE}:s=5,highpass=f=2500,"
             f"volume='0.11*(between(t,3,6.5)+between(t,15,17.8))':eval=frame")
    grind = (f"anoisesrc=d={total}:c=brown:a=0.7:r={RATE}:s=9,bandpass=f=300:w=400,"
             f"volume='0.5*between(t,11,13.2)':eval=frame")
    graph = ("[0][1][2][3][4]amix=inputs=5:normalize=0,lowpass=f=7000,aecho=0.8:0.4:35|70:0.25|0.12,"
             "asplit[a][b];"
             f"[a]atrim=0:{SECONDS},asetpts=PTS-STARTPTS[main];[b]atrim={SECONDS}:{total},asetpts=PTS-STARTPTS[tail];"
             f"[tail][main]acrossfade=d={FADE}:c1=tri:c2=tri,volume=5.5[out]")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
           "-f", "lavfi", "-i", murmur, "-f", "lavfi", "-i", murmur2, "-f", "lavfi", "-i", cups,
           "-f", "lavfi", "-i", steam, "-f", "lavfi", "-i", grind,
           "-filter_complex", graph, "-map", "[out]", "-ac", "2", "-ar", str(RATE), "-c:a", "libvorbis", "-q:a", "3",
           "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:a", "+bitexact", OUT]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"ffmpeg failed: {' '.join(cmd)}\n{r.stderr}")


if __name__ == "__main__":
    make()
    print("wrote", OUT)
