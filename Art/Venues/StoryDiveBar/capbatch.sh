#!/usr/bin/env bash
# Several previews under one hold of the capture lock. Each line of the spec file:
#   <name> <song> <cueat> [extra game args...]
cd /home/mitch/Projects/Drumsmith
spec=$1
flock /tmp/drumsmith-capture.lock bash -c '
M=$(ls /nix/store/*-imagemagick-7*/bin/magick | head -1)
while read -r name song cue rest; do
  [ -z "$name" ] && continue
  log=Art/Venues/StoryDiveBar/logs/$name.log
  eval "set -- $rest"
  timeout 600 env HEADLESS_DISPLAY=:104 ./Engine/Tools/NixEnv.sh env -u NIX_CC \
    ./Engine/Tools/Headless.sh ./.build/Game_linux_Debug/Game_EntryPoint_x64 \
    --scene Assets/Example.lvl --play-track 0 --frames 40 --width 960 --height 540 --frame-time 0.016666667 --no-audio \
    --venue-only --venue StoryDiveBar --venue-time 40 --story s04-dive-bar --story-song $song --story-cue-at $cue \
    "$@" --screenshot Art/Venues/StoryDiveBar/Previews/$name.png --exit > $log 2>&1 < /dev/null
  echo "$name exit $?"
  grep -a "story:" $log | tail -1
  [ -f Art/Venues/StoryDiveBar/Previews/$name.png ] && $M Art/Venues/StoryDiveBar/Previews/$name.png Art/Venues/StoryDiveBar/logs/$name.small.jpg
done < '"$spec"'
'
echo batch done
