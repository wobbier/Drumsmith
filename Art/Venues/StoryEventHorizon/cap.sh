#!/usr/bin/env bash
# cap.sh <name> <song> <cueat> [extra args...]
cd /home/mitch/Projects/Drumsmith
name=$1; song=$2; cue=$3; shift 3
flock /tmp/drumsmith-capture.lock timeout 600 env HEADLESS_DISPLAY=:113 ./Engine/Tools/NixEnv.sh env -u NIX_CC \
  ./Engine/Tools/Headless.sh ./.build/Game_linux_Debug/Game_EntryPoint_x64 \
  --scene Assets/Example.lvl --play-track 0 --frames 40 --width 960 --height 540 --frame-time 0.016666667 --no-audio \
  --venue-only --venue StoryEventHorizon --venue-time 40 --story s13-event-horizon --story-song $song --story-cue-at $cue \
  "$@" --screenshot Art/Venues/StoryEventHorizon/Previews/$name.png --exit > Art/Venues/StoryEventHorizon/Previews/$name.log 2>&1
echo exit $?
grep -i "story:\|error\|fail\|missing\|warn" Art/Venues/StoryEventHorizon/Previews/$name.log | grep -v "^\s*$" | head -20
