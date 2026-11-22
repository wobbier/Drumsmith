#!/usr/bin/env bash
# gcap.sh <out name> <song> <cue-at> [extra args...]
cd /home/mitch/Projects/Drumsmith
name=$1; song=$2; cue=$3; shift 3
L=Art/Venues/StoryGardens/scratch/$name.log
flock /tmp/drumsmith-capture.lock bash -c 'date +%T > "$0"; timeout 600 env HEADLESS_DISPLAY=:111 ./Engine/Tools/NixEnv.sh env -u NIX_CC ./Engine/Tools/Headless.sh ./.build/Game_linux_Debug/Game_EntryPoint_x64 --scene Assets/Example.lvl --play-track 0 --frames 40 --width 960 --height 540 --frame-time 0.016666667 --no-audio --venue-only --venue StoryGardens --venue-time 40 "$@" >> "$0" 2>&1; echo "rc $?" >> "$0"; date +%T >> "$0"' "$L" --story s11-gardens --story-song $song --story-cue-at $cue "$@" --screenshot Art/Venues/StoryGardens/Previews/$name.png --exit
head -1 $L; tail -2 $L; grep -E "story:" $L
