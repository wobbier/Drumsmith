#!/usr/bin/env bash
# Preview capture for the Dead End Dive Bar: cap.sh <name> <song> <cueat> [extra game args...]
cd /home/mitch/Projects/Drumsmith
name=$1; song=$2; cue=$3; shift 3
log=Art/Venues/StoryDiveBar/logs/$name.log
flock /tmp/drumsmith-capture.lock timeout 600 env HEADLESS_DISPLAY=:104 ./Engine/Tools/NixEnv.sh env -u NIX_CC \
  ./Engine/Tools/Headless.sh ./.build/Game_linux_Debug/Game_EntryPoint_x64 \
  --scene Assets/Example.lvl --play-track 0 --frames 40 --width 960 --height 540 --frame-time 0.016666667 --no-audio \
  --venue-only --venue StoryDiveBar --venue-time 40 --story s04-dive-bar --story-song $song --story-cue-at $cue \
  "$@" --screenshot Art/Venues/StoryDiveBar/Previews/$name.png --exit > $log 2>&1
echo "exit $?"
grep -a "\[Venues\]" $log | tail -6
[ -f Art/Venues/StoryDiveBar/Previews/$name.png ] || exit 1
M=$(ls /nix/store/*-imagemagick-7*/bin/magick | head -1)
$M Art/Venues/StoryDiveBar/Previews/$name.png Art/Venues/StoryDiveBar/logs/$name.small.jpg
