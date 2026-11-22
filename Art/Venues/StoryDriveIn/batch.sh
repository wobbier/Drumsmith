#!/usr/bin/env bash
# batch.sh "name song cue [args...]" ...   one capture per argument, in order
cd /home/mitch/Projects/Drumsmith
for spec in "$@"; do eval "Art/Venues/StoryDriveIn/cap.sh $spec" | grep -E "^exit|story:"; done
echo BATCH DONE
