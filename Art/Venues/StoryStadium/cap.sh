#!/usr/bin/env bash
# StoryStadium headless capture: cap.sh <out-name> <song> <cue-at> [extra args...]
# Holds the shared lock only until the PNG is written, then ends the game.
cd /home/mitch/Projects/Drumsmith
out=$1; song=$2; cue=$3; shift 3
png="Art/Venues/StoryStadium/Previews/$out.png"
log="Art/Venues/StoryStadium/Previews/_$out.log"
flock /tmp/drumsmith-capture.lock bash -c '
  png=$1; log=$2; song=$3; cue=$4; shift 4
  rm -f "$png"
  setsid timeout 600 env HEADLESS_DISPLAY=:112 ./Engine/Tools/NixEnv.sh env -u NIX_CC \
    ./Engine/Tools/Headless.sh ./.build/Game_linux_Debug/Game_EntryPoint_x64 \
    --scene Assets/Example.lvl --play-track 0 --frames 40 --width 960 --height 540 --frame-time 0.016666667 --no-audio \
    --venue-only --venue StoryStadium --venue-time 40 --story s12-stadium --story-song "$song" --story-cue-at "$cue" \
    "$@" --screenshot "$png" --exit > "$log" 2>&1 &
  pid=$!
  while kill -0 $pid 2>/dev/null; do
    if [ -s "$png" ]; then sleep 2; kill -- -$pid 2>/dev/null; break; fi
    sleep 1
  done
  wait $pid 2>/dev/null
' _ "$png" "$log" "$song" "$cue" "$@"
[ -s "$png" ] && echo "ok $png" || echo "FAILED $png"
grep -a "story:" "$log" | cut -c1-160
