#!/usr/bin/env bash
# shoot.sh <name> <song> <cue-at> [extra args...]: one headless preview of the venue.
cd "$(dirname "$0")/../../.."
name=$1; song=$2; cue=$3; shift 3
flock /tmp/drumsmith-capture.lock timeout 600 env HEADLESS_DISPLAY=:102 ./Engine/Tools/NixEnv.sh env -u NIX_CC \
  ./Engine/Tools/Headless.sh ./.build/Game_linux_Debug/Game_EntryPoint_x64 \
  --scene Assets/Example.lvl --play-track 0 --frames 40 --width 960 --height 540 --frame-time 0.016666667 --no-audio \
  --venue-only --venue StorySubway --venue-time 40 --story s02-busking --story-song "$song" --story-cue-at "$cue" \
  "$@" --screenshot "Art/Venues/StorySubway/Previews/$name.png" --exit > "Art/Venues/StorySubway/Previews/$name.log" 2>&1
echo "exit $?"
grep -E "\[Venues\]|rror|story" "Art/Venues/StorySubway/Previews/$name.log" | head -20
