#!/usr/bin/env python3
"""Writes Assets/Venues/Template/: the smallest valid venue, for modders to copy.

    python3 Tools/Venues/make_template.py

A floor, a 0.5 m stage with a raised drummer platform, the five band spots, one crowd area, one
camera spot, two cued wash lights and a static key light. Deterministic: rerun = same bytes.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from venuegen import Scene, repo_root, write_venue_json  # noqa: E402

GREY = (0.32, 0.33, 0.36)
DARK = (0.12, 0.12, 0.14)
WOOD = (0.55, 0.38, 0.22)


def build():
    s = Scene(seed=1001)
    root = s.group("Template Venue")
    geo = s.group("Geometry", root)
    lights = s.group("Lights", root)
    marks = s.group("Markers", root)

    # Room: floor, back wall, stage deck 0.5 m high, drummer platform 0.3 m on top of it.
    s.slab("Floor", geo, -12, 12, -0.2, 0.0, -16, 11, GREY)
    s.slab("Back Wall", geo, -12, 12, 0, 6, 11, 11.3, DARK)
    s.slab("Stage Deck", geo, -7, 7, 0, 0.5, 0, 8, WOOD)
    s.slab("Drummer Platform", geo, -2.2, 2.2, 0.5, 0.8, 4.2, 8, WOOD)

    # Lights: two cued washes from above the front of the stage, one uncued key light.
    s.light("Wash Left", lights, (-4, 6, 1), "Spot", (0.3, 0.5, 1.0), 6.0, 16, rot=(70, 15, 0),
            inner=25, outer=45, show="Wash", group=0)
    s.light("Wash Right", lights, (4, 6, 1), "Spot", (1.0, 0.3, 0.5), 6.0, 16, rot=(70, -15, 0),
            inner=25, outer=45, show="Wash", group=0)
    s.light("Key Light", lights, (0, 5, -3), "Point", (1.0, 0.9, 0.75), 2.0, 20, show="Static")

    # Markers. VenueSpot faces local -Z (identity = faces the crowd), feet position.
    s.info(marks, "Template", "Drumsmith", outdoor=False, room_back=-16, room_ceiling=7,
           half_width=12, desk_z=-13)
    s.spot(marks, "Drummer", (0, 0.8, 6.2))
    s.spot(marks, "Guitar", (-3.4, 0.5, 3.0))
    s.spot(marks, "Bass", (3.4, 0.5, 3.2))
    s.spot(marks, "Vocals", (0, 0.5, 1.4))
    s.spot(marks, "Keys", (-5.2, 0.5, 5.6))
    # Crowd rectangle: centre, full width/depth; faces +Z (the band) at identity.
    s.crowd("Crowd", marks, (0, 0, -8.5), 14, 9, 60)
    s.camera_spot("Camera Wide", marks, (0, 3.2, -14), (0, 1.8, 4), "Wide", 55)
    return s


def main():
    folder = os.path.join(repo_root(), "Assets", "Venues", "Template")
    build().write(os.path.join(folder, "Template.lvl"))
    write_venue_json(folder, "Template", "Template.lvl")
    print("wrote", folder)


if __name__ == "__main__":
    main()
