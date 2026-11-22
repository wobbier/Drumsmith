#!/usr/bin/env bash
# cap.sh <out.png> <song> <cue-at> [extra args...]
cd /home/mitch/Projects/Drumsmith
out=$1; song=$2; cue=$3; shift 3
flock /tmp/drumsmith-capture.lock timeout 600 env HEADLESS_DISPLAY=:101 ./Engine/Tools/NixEnv.sh env -u NIX_CC \
  ./Engine/Tools/Headless.sh ./.build/Game_linux_Debug/Game_EntryPoint_x64 \
  --scene Assets/Example.lvl --play-track 0 --frames 40 --width 960 --height 540 --frame-time 0.016666667 --no-audio \
  --venue-only --venue StoryBasement --venue-time 40 --story s01-basement --story-song $song --story-cue-at $cue \
  "$@" --screenshot "$out" --exit > /tmp/claude-1000/sb_last.log 2>&1
echo "exit $?"; grep -E "\[Venues\]|ERROR|rror" /tmp/claude-1000/sb_last.log | head -20
