#!/usr/bin/env bash
# cap.sh <out-name> <song> <cue-at> [extra args...]  -> Art/Venues/StoryDriveIn/Previews/<out-name>.png
# Holds the shared lock only until the screenshot lands, then stops the game.
cd /home/mitch/Projects/Drumsmith
name=$1; song=$2; cue=$3; shift 3
png=Art/Venues/StoryDriveIn/Previews/$name.png
log=Art/Venues/StoryDriveIn/Scratch/$name.log
rm -f "$png"
flock /tmp/drumsmith-capture.lock bash -c '
  timeout 600 env HEADLESS_DISPLAY=:109 ./Engine/Tools/NixEnv.sh env -u NIX_CC \
    ./Engine/Tools/Headless.sh ./.build/Game_linux_Debug/Game_EntryPoint_x64 \
    --scene Assets/Example.lvl --play-track 0 --frames 40 --width 960 --height 540 --frame-time 0.016666667 --no-audio \
    --venue-only --venue StoryDriveIn --venue-time 40 --story s09-drive-in --story-song '"$song"' --story-cue-at '"$cue"' \
    "$@" --screenshot '"$png"' --exit > '"$log"' 2>&1 &
  game=$!
  for i in $(seq 600); do [ -s '"$png"' ] && { sleep 2; break; }; kill -0 $game 2>/dev/null || break; sleep 1; done
  pkill -f "venue StoryDriveIn" 2>/dev/null; wait $game 2>/dev/null' _ "$@"
echo "exit $?"
grep -i "story:" "$log" | head -3
