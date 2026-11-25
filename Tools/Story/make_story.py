#!/usr/bin/env python3
"""Writes Assets/Progression/Story.json, the story mode the game loads, from the design manifest
Design/Story-Mode-Setlists.json (Docs/Hideout-and-Progression.md -> Story mode).

The manifest is the writers' copy: it carries the staging, the cues, the alternates and the
build notes. The game file keeps only what the game reads today. The manifest's ProposedSets (not
placed in the campaign yet) go to the game file's own ProposedSets, which nothing books or lists:
--gig <id> and the gig board's debug rows play them. Run it again whenever the manifest changes:

    python3 Tools/Story/make_story.py
"""
import json
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SOURCE = os.path.join(ROOT, "Design", "Story-Mode-Setlists.json")
TARGET = os.path.join(ROOT, "Assets", "Progression", "Story.json")

# Each set's own venue scene, Assets/Venues/<Id>/ (Docs/Venue-Authoring.md). A set whose folder
# isn't there yet plays in its VenueBase room when that is one the game has, else the player's own.
VENUES = {
    "s01-basement": "StoryBasement",
    "s02-busking": "StorySubway",
    "s03-coffee-shop": "StoryCoffeeShop",
    "s04-dive-bar": "StoryDiveBar",
    "s05-legion": "StoryLegion",
    "s06-roller-rink": "StoryRollerRink",
    "s07-pledge-drive": "StoryRadioStation",
    "s08-food-court": "StoryFoodCourt",
    "s09-drive-in": "StoryDriveIn",
    "s10-steel-mill": "StorySteelMill",
    "s11-gardens": "StoryGardens",
    "s12-stadium": "StoryStadium",
    "s13-event-horizon": "StoryEventHorizon",
}
GIG_VENUES = {"Club", "Festival", "Arena"}


def scene_there(scene):
    return bool(scene) and os.path.isfile(os.path.join(ROOT, "Assets", "Venues", scene, "venue.json"))


def venue(entry):
    scene = entry.get("Venue") or VENUES.get(entry["Id"])
    if scene_there(scene):
        return scene
    return entry["VenueBase"] if entry.get("VenueBase") in GIG_VENUES else ""


def song(entry):
    out = {
        "Artist": entry["Artist"],
        "Title": entry["Title"],
        "Spotify": entry.get("Spotify", ""),
        "Flags": entry.get("StateAfter", []),
        "Cue": (entry.get("Cue") or {}).get("On", ""),
    }
    # A show's song can carry more cues, its own venue and the highway's rests.
    moments = []
    for m in entry.get("Moments", []):
        if not m.get("On") or not (m.get("StateAfter") or m.get("Caption")):
            continue
        moment = {"Cue": m["On"], "Flags": m.get("StateAfter", [])}
        if m.get("Caption"):
            moment["Caption"] = m["Caption"]
            if m.get("CaptionSeconds"):
                moment["CaptionSeconds"] = m["CaptionSeconds"]
        moments.append(moment)
    if moments:
        out["Moments"] = moments
    if scene_there(entry.get("Venue")):
        out["Venue"] = entry["Venue"]
    # A continuous show holds the venue this long after the last note before the next song.
    if entry.get("OutroSeconds"):
        out["OutroSeconds"] = entry["OutroSeconds"]
    return out


def story_set(entry):
    reward = entry.get("Reward") or {}
    requires = entry.get("Requires") or {}
    out = {
        "Id": entry["Id"],
        "Act": entry.get("Act", 0),
        "Name": entry["Title"],
        "Description": entry.get("Premise", ""),
        "Venue": venue(entry),
        "VenueBase": entry.get("VenueBase", ""),
        "PassAccuracy": round(entry.get("PassAccuracy", 0.7) * 100.0, 1),
        "Requires": {"StorySets": requires.get("Sets", []), "Members": requires.get("Members", [])},
        "Songs": [song(s) for s in entry["Songs"]],
        "Rewards": [reward["Item"]] if reward.get("Item") else [],
    }
    for key in ("Credits", "PostCredits", "OneSitting", "Continuous"):
        if entry.get(key):
            out[key] = True
    if reward.get("MovesInto"):
        out["MovesInto"] = reward["MovesInto"]
    if entry.get("AuditionAfter"):
        out["Audition"] = entry["AuditionAfter"]
    return out


def item(entry):
    reward = entry["Reward"]
    return {"Id": reward["Item"], "Name": reward["Name"], "Description": reward.get("Description", ""), "Slot": reward["Item"]}


def audition(entry):
    return {
        "Id": entry["Id"],
        "Seat": entry["Seat"],
        "After": entry.get("After", ""),
        "Optional": bool(entry.get("Optional", False)),
        "Description": entry.get("Scene", ""),
        "Candidates": [
            {
                "Id": c["Id"],
                "Name": c["Name"],
                "Description": c.get("Personality", ""),
                "Leans": c.get("Leans", ""),
                "Pitch": c.get("Pitch", ""),
                "Body": (c.get("Look") or {}).get("Body", ""),
                "Clothes": (c.get("Look") or {}).get("Clothes", ""),
            }
            for c in entry.get("Candidates", [])
        ],
    }


def main():
    with open(SOURCE, encoding="utf-8") as f:
        manifest = json.load(f)
    sets = manifest["Sets"]
    out = {
        "Generated": "by Tools/Story/make_story.py from Design/Story-Mode-Setlists.json: edit those, not this",
        "Sets": [story_set(s) for s in sets],
        "ProposedSets": [story_set(s) for s in manifest.get("ProposedSets", [])],
        "Auditions": [audition(a) for a in manifest.get("Auditions", [])],
        "Items": [item(s) for s in sets if (s.get("Reward") or {}).get("Item")],
    }
    with open(TARGET, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"{os.path.relpath(TARGET, ROOT)}: {len(out['Sets'])} sets, {len(out['ProposedSets'])} proposed, {len(out['Auditions'])} auditions, {len(out['Items'])} items")
    return 0


if __name__ == "__main__":
    sys.exit(main())
