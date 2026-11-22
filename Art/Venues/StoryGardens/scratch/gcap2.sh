#!/usr/bin/env bash
# gcap2.sh <name> <song> <cue> [args]: like gcap.sh but kills the game once the PNG lands.
cd /home/mitch/Projects/Drumsmith
name=$1; song=$2; cue=$3; shift 3
P=Art/Venues/StoryGardens/Previews/$name.png; L=Art/Venues/StoryGardens/scratch/$name.log
rm -f "$P"
flock /tmp/drumsmith-capture.lock bash -c '
  timeout 600 env HEADLESS_DISPLAY=:111 ./Engine/Tools/NixEnv.sh env -u NIX_CC ./Engine/Tools/Headless.sh ./.build/Game_linux_Debug/Game_EntryPoint_x64 --scene Assets/Example.lvl --play-track 0 --frames 40 --width 960 --height 540 --frame-time 0.016666667 --no-audio --venue-only --venue StoryGardens --venue-time 40 "${@:3}" > "$1" 2>&1 &
  pid=$!
  for i in $(seq 600); do [ -s "$2" ] && sleep 2 && break; kill -0 $pid 2>/dev/null || break; sleep 1; done
  pkill -f "Game_EntryPoint_x64.*$2" 2>/dev/null; wait $pid 2>/dev/null
  echo "rc done" >> "$1"' _ "$L" "$P" --story s11-gardens --story-song $song --story-cue-at $cue "$@" --screenshot "$P" --exit
ls -la "$P"
