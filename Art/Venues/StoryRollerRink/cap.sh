#!/usr/bin/env bash
# cap.sh <out-name> <song> <cue-at> [extra args...]
cd /home/mitch/Projects/Drumsmith
name=$1; song=$2; cue=$3; shift 3
flock /tmp/drumsmith-capture.lock timeout 600 env HEADLESS_DISPLAY=:106 ./Engine/Tools/NixEnv.sh env -u NIX_CC \
  ./Engine/Tools/Headless.sh ./.build/Game_linux_Debug/Game_EntryPoint_x64 \
  --scene Assets/Example.lvl --play-track 0 --frames 40 --width 960 --height 540 --frame-time 0.016666667 --no-audio \
  --venue-only --venue StoryRollerRink --venue-time 40 --story s06-roller-rink --story-song $song --story-cue-at $cue \
  "$@" --screenshot Art/Venues/StoryRollerRink/Previews/$name.png --exit > Art/Venues/StoryRollerRink/Scratch/$name.log 2>&1
echo "exit $?"
grep -iE "story:|error|not found|fail|BRUH|warn" Art/Venues/StoryRollerRink/Scratch/$name.log | grep -v "^$" | sort | uniq -c | sort -rn | head -25
