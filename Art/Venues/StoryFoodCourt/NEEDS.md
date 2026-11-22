# StoryFoodCourt: framework needs

Nothing blocks the venue. Two notes for whoever touches the tools next:

- `magick` is not on the PATH in this checkout's shell or in `Engine/Tools/NixEnv.sh` (the brief says it is). The
  generator finds the Nix store's ImageMagick 7 itself, and only needs it with `--textures`; the painted PNGs are kept.
- No FBX-to-OBJ tool ships (no Blender or assimp CLI on the machine). `Tools/Venues/story_food_court_fbx.py` is a small
  stdlib binary-FBX reader that does it for the owner's Synty packs; it could be promoted to a shared tool.
- A `VenueStory` that is only a "moved" prop needs two groups (and a three-state prop needs nested groups). A
  `VenueStory` with `FlagUntil` (shown from flag A until flag B) would halve the groups for heads like this one's.
