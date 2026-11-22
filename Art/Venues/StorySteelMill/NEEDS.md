# StorySteelMill: framework needs

1. **Cameo gating.** Song 2's cameos (Jules beside a bass case with a cafe sticker; Ness with the
   opener's bass tech, white strap on the case) are conditional on the player's audition choice
   (`"If": "not_selected"`). `VenueStory` only knows song flags, so a venue can't show a cameo only
   when it applies. A flag the gig sets from the cameo condition (e.g. `cameo_jules`) would let the
   venue gate them like any other story prop. Not built.
2. **Stale cooked textures.** A texture's `.png.dds` twin is used even when the `.png` is newer,
   so a regenerated texture keeps showing the old picture until the twin is deleted or re-cooked.
   `story_steel_mill_textures.py` now deletes its own twins when it redraws; the loader could
   compare timestamps instead.
