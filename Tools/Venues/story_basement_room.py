"""story_basement_room: the hideout basement (Tools/Hideout/basement.py), rebuilt as a venue scene.

The hideout's own builder functions write the room into a venuegen Scene (read-only import: no
bytecode is written into Tools/Hideout). Then `venue_safe()` turns the hideout-only parts into what a
venue can carry:

  * HideoutMotion / HideoutStation / HideoutView / HideoutDrummer / Camera / AudioSource go (the
    venue has no Hideout core: the band, the camera and the sound are the show's);
  * HideoutWhen Day / Night become the story flag window_well_blue (day until it is set);
  * items the player hasn't earned yet (HideoutItemSlot) go, the tape outlines that wait for them
    (WhenLocked) stay; the band is still unnamed;
  * HideoutReadouts get their words written in (this set's setlist, the wishlist, the tally);
  * no light casts shadows (the venue's one shadowed light is its own directional), and the
    practicals are turned up by light_gain (the venue's exposure is darker than the hideout's).
"""
import os
import sys

sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(1, os.path.join(_HERE, "..", "Hideout"))

import basement as B  # noqa: E402
import hideoutgen as HG  # noqa: E402

HIDEOUT_ONLY = {"HideoutMotion", "HideoutStation", "HideoutView", "HideoutDrummer", "HideoutBandName", "HideoutItemSlot",
                "HideoutReadout", "HideoutWhen", "AudioSource"}
KEEP_SLOTS = {"Radio"}

SETLIST = ["Royals", "bad guy", "Feb. Air", "Sleeping In", "Fireflies"]
WISHES = {"practice-pad": "practice pad", "metronome": "metronome", "stick-bag": "stick bag", "band-poster": "a band poster",
          "lava-lamp": "lava lamp", "vinyl-shelf": "record shelf", "spare-cymbal": "a 2nd cymbal", "neon-sign": "NEON SIGN",
          "gold-record": "gold record (ha)"}
TALLY = {"SongsPlayed": "41", "FullCombos": "0", "GigsPlayed": "0"}
# The clock over the stairs: ten past five, the light going.
CLOCK = {"Hour": 155.0, "Minute": 60.0, "Second": 200.0}


def build_room(s, geo, items, stations, lights):
    """The hideout's basement, minus what the venue story rebuilds itself (the camcorder, the TV,
    the kitchen door) and what isn't there yet (the moving boxes, the earned items)."""
    B.shell(s, geo)
    B.stairs(s, geo, items)
    B.back_wall(s, geo, items, lights)
    B.kit_corner(s, geo, items, stations, lights)
    B.couch_corner(s, geo, items, stations, lights)
    B.utilities(s, geo, items, lights)
    B.workbench(s, geo, items, stations, lights)
    B.gig_board(s, geo, items, stations)
    B.trophies(s, items, stations)
    B.front(s, geo, items, stations)
    B.wishlist(s, items, stations)
    B.stand_ins(s, items)


def comp(e, kind):
    for c in e.components:
        if c.get("Type") == kind:
            return c
    return None


def venue_safe(s, drop_names=(), when_flag="window_well_blue", light_gain=1.0):
    """Rewrites the hideout parts in place (see the module doc). drop_names: entities (and their
    children) the story rebuilds. Returns {name: entity} of what's left, the first of each name."""
    kids = {}
    for e in s.entities:
        if e.parent is not None:
            kids.setdefault(e.parent.guid, []).append(e)
    gone = set()

    def drop(e):
        gone.add(e.guid)
        for k in kids.get(e.guid, []):
            drop(k)

    for e in s.entities:
        if e.name in drop_names:
            drop(e)
        slot = comp(e, "HideoutItemSlot")
        if slot and not slot.get("WhenLocked") and slot["Slot"] not in KEEP_SLOTS:
            drop(e)
        named = comp(e, "HideoutBandName")
        if named and named["Show"] == "Named":
            drop(e)
        when = comp(e, "HideoutWhen")
        if when and when["Show"] == "MovingIn":
            drop(e)
        if comp(e, "Camera") or comp(e, "HideoutDrummer") or comp(e, "HideoutView"):
            drop(e)
        if comp(e, "AudioSource"):
            drop(e)
        station = comp(e, "HideoutStation")
        if station and len(e.components) == 2 and not kids.get(e.guid):
            drop(e)
    s.entities = [e for e in s.entities if e.guid not in gone]

    for e in s.entities:
        readout = comp(e, "HideoutReadout")
        text = comp(e, "TextRenderer")
        if readout and text is not None:
            show = readout["Show"]
            words = ""
            if show == "RecentSong":
                words = readout.get("Prefix", "") + SETLIST[readout.get("Line", 0)]
            elif show == "Wishlist":
                words = "[ ] " + WISHES.get(readout.get("Item", ""), "")
            elif show == "NowPlaying":
                words = "BT  AUX IN"
            elif show in TALLY:
                words = readout.get("Prefix", "") + TALLY[show]
            text["Text"] = words
        motion = comp(e, "HideoutMotion")
        if motion and motion["Motion"] in CLOCK:
            e.components[0]["Rotation"] = [CLOCK[motion["Motion"]], 0.0, 0.0]
        when = comp(e, "HideoutWhen")
        if when and when["Show"] in ("Day", "Night"):
            e.add({"Type": "VenueStory", "Flag": when_flag, "WhenSet": when["Show"] == "Night", "FadeSeconds": 6.0})
        for c in e.components:
            if c.get("Type") == "Light":
                c.pop("CastShadows", None)
                c["Intensity"] = round(c["Intensity"] * light_gain, 4)
        e.components = [c for c in e.components if c.get("Type") not in HIDEOUT_ONLY]

    named = {}
    for e in s.entities:
        named.setdefault(e.name, e)
    return named


def reparent(s, e, parent):
    """Moves e (and its children) under parent, keeping the file's parents-first order."""
    moving = [e]
    i = 0
    while i < len(moving):
        moving += [k for k in s.entities if k.parent is moving[i]]
        i += 1
    ids = {m.guid for m in moving}
    s.entities = [k for k in s.entities if k.guid not in ids] + moving
    e.parent = parent
    return e
