# StorySubway: framework wishes (none blocking)

- **A moving story group.** `VenueStory` can only grow or shrink from its pivot. The design wants "lit carriage windows sweep past the pillar". Today each carriage shrinks toward its tunnel mouth over 3.5 s, with the pivot set past the portal. That reads as pulling out, but it is not a slide. Either of these would make it a real sweep:
  - an optional `Offset` / `MoveFrom` vector on `VenueStory`, so the group slides from or to a point instead of scaling;
  - a way to start a `Sequence` when the flag lands. Today `PlayOnStart` runs at venue load.
