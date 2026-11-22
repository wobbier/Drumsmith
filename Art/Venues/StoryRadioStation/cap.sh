#!/usr/bin/env bash
# cap.sh <out-name> <song> <cue-at> [extra args...]   (waits for the shared lock, then runs at most 600 s)
cd /home/mitch/Projects/Drumsmith
name=$1; song=$2; cue=$3; shift 3
flock /tmp/drumsmith-capture.lock timeout 600 env HEADLESS_DISPLAY=:107 ./Engine/Tools/NixEnv.sh env -u NIX_CC \
  ./Engine/Tools/Headless.sh ./.build/Game_linux_Debug/Game_EntryPoint_x64 \
  --scene Assets/Example.lvl --play-track 0 --frames 40 --width 960 --height 540 --frame-time 0.016666667 --no-audio \
  --venue-only --venue StoryRadioStation --venue-time 40 --story s07-pledge-drive --story-song $song --story-cue-at $cue \
  "$@" --screenshot Art/Venues/StoryRadioStation/Previews/$name.png --exit > Art/Venues/StoryRadioStation/run_$name.log 2>&1
echo "$name exit $? $(date +%T)"
grep -i "not found\|failed" Art/Venues/StoryRadioStation/run_$name.log | sort | uniq -c | head -10
