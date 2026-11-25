"""Highway to the Afterlife's sounds, synthesised with ffmpeg (deterministic: fixed seeds).

Assets/Venues/StoryHighway/Sounds/Wreck.ogg: what Kickstart My Heart's outro is heard by, from
the moment the rig goes over (the venue's VenueSound on the story flag wreck). The crunch of the
trailer, the blast a beat after it and what it throws; then the fire, the ears ringing, and the
pursuit's sirens coming up out of the ringing and dying away, down to nothing by the time the
next song starts (LENGTH seconds: keep it no longer than the song's OutroSeconds less the half
second the wreck lands after the last note).

    python3 Tools/Venues/story_afterlife_sound.py
"""
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "Assets", "Venues", "StoryHighway", "Sounds", "Wreck.ogg")
RATE = 44100
LENGTH = 15.0
BLAST = 0.35        # seconds after the crunch


def ramp(t0, t1):
    """0 before t0, 1 after t1 (an ffmpeg expression in t)."""
    return f"min(1,max(0,(t-{t0})/{t1 - t0}))"


def make():
    d = LENGTH
    b = BLAST
    sources = [
        # The trailer going over: torn metal, half a second of it, and a second hit as it lands.
        (f"anoisesrc=d={d}:c=white:a=0.9:r={RATE}:s=3,bandpass=f=1400:t=h:w=2400,"
         f"volume='1.3*(exp(-7*t)+0.7*exp(-9*max(t-0.22,0))*gte(t,0.22))*lt(t,1.5)':eval=frame"),
        # The blast: a thump falling from 95 Hz to 35, and the air behind it.
        (f"aevalsrc='0.95*sin(2*PI*(35*(t-{b})+15*(1-exp(-4*(t-{b})))))*exp(-1.5*(t-{b}))*gte(t,{b})':d={d}:s={RATE}"),
        (f"anoisesrc=d={d}:c=brown:a=0.9:r={RATE}:s=7,lowpass=f=240,"
         f"volume='3*exp(-1.0*max(t-{b},0))*gte(t,{b})':eval=frame"),
        # What it throws, coming down on the road for a few seconds.
        (f"aevalsrc='gt(random(3),0.9972)*(2*random(4)-1)*exp(-0.9*(t-{b}))*gte(t,{b})*lt(t,6)':d={d}:s={RATE},"
         f"bandpass=f=2400:t=h:w=2600,aecho=0.8:0.5:23|61:0.4|0.25,volume=4"),
        # The fire: its roar, breathing, and its crackle.
        (f"anoisesrc=d={d}:c=brown:a=0.8:r={RATE}:s=11,bandpass=f=320:t=h:w=560,tremolo=f=0.37:d=0.5,tremolo=f=5.3:d=0.3,"
         f"volume='0.7*{ramp(b, b + 1.2)}':eval=frame"),
        (f"aevalsrc='gt(random(1),0.9989)*(2*random(2)-1)*{ramp(b, b + 1.0)}':d={d}:s={RATE},"
         f"highpass=f=900,lowpass=f=5200,volume=0.6"),
        # The ears ringing after the blast, gone by ten seconds.
        (f"aevalsrc='0.035*(sin(2*PI*6180*t)+0.6*sin(2*PI*6247*t))*{ramp(b + 0.1, b + 0.9)}*min(1,max(0,(10-t)/6))':d={d}:s={RATE}"),
        # Two of the pursuit's sirens, a way off: each a wail of its own length, heard from under
        # the ringing as it thins.
        (f"aevalsrc='(sin(2*PI*930*t-350*3.6*cos(2*PI*t/3.6))+0.35*sin(2*(2*PI*930*t-350*3.6*cos(2*PI*t/3.6))))"
         f"*{ramp(1.5, 5.5)}':d={d}:s={RATE},lowpass=f=1700,aecho=0.8:0.6:110|230:0.45|0.3,volume=0.07"),
        (f"aevalsrc='(sin(2*PI*1010*t-300*2.9*cos(2*PI*t/2.9+1.3))+0.35*sin(2*(2*PI*1010*t-300*2.9*cos(2*PI*t/2.9+1.3))))"
         f"*{ramp(3.0, 7.0)}':d={d}:s={RATE},lowpass=f=1400,aecho=0.8:0.6:170|310:0.45|0.3,volume=0.05"),
    ]
    mix = "".join(f"[{i}]" for i in range(len(sources)))
    graph = (f"{mix}amix=inputs={len(sources)}:normalize=0,highpass=f=40,alimiter=limit=0.89:level=disabled,"
             f"afade=t=out:st={d - 4.0}:d=4.0:curve=qsin[out]")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for source in sources:
        cmd += ["-f", "lavfi", "-i", source]
    cmd += ["-filter_complex", graph, "-map", "[out]", "-t", str(d), "-ac", "2", "-ar", str(RATE), "-c:a", "libvorbis", "-q:a", "4",
            "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:a", "+bitexact", OUT]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"ffmpeg failed: {' '.join(cmd)}\n{r.stderr}")


if __name__ == "__main__":
    make()
    print("wrote", OUT)
