#!/usr/bin/env python3
"""Structural check of a venue folder (venue.json + its .lvl). Stdlib only.

    python3 Tools/Venues/check_venue.py Assets/Venues/Backyard [more folders...]

Checks: venue.json keys and files, scene format v2, unique GUIDs, every Parent exists (and comes
before its child), registered component type names, asset paths exist (relative to the repo
root, Engine/ for engine assets, or the venue folder), exactly one VenueInfo, exactly one Drummer
VenueSpot, no more than one shadowed light, no more than 40 VenueShowLights, no current Camera,
no scripts / UI documents / Cores. Exits 1 on any error; warnings don't fail.
"""
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ASSET_EXT = {".obj", ".fbx", ".png", ".jpg", ".jpeg", ".dds", ".tga", ".hdr", ".wav", ".ogg", ".mp3",
             ".mat", ".prefab", ".rml", ".assbin", ".glb", ".gltf"}
MAX_SHOW_LIGHTS = 40
MAX_SHADOWED = 1
BANNED = {"ScriptComponent", "UIDocument"}
SCAN_DIRS = ["Engine/Source", "Engine/Modules", "Game/Source"]
REG = re.compile(r"ME_REGISTER_COMPONENT\w*\s*\(\s*(\w+)")


def registered_components():
    names = set()
    for d in SCAN_DIRS:
        for base, _, files in os.walk(os.path.join(ROOT, d)):
            for f in files:
                if f.endswith((".h", ".hpp", ".cpp")):
                    try:
                        text = open(os.path.join(base, f), encoding="utf-8", errors="ignore").read()
                    except OSError:
                        continue
                    for m in REG.finditer(text):
                        names.add(m.group(1))
    names.discard("T")
    names.discard("TYPE")
    return names


def strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from strings(v)


def resolve(path, folder):
    for base in (ROOT, os.path.join(ROOT, "Engine"), folder):
        if os.path.exists(os.path.join(base, path)):
            return True
    return False


def check(folder):
    errors, warnings = [], []
    folder = os.path.abspath(folder)

    def err(m):
        errors.append(m)

    vj = os.path.join(folder, "venue.json")
    if not os.path.isfile(vj):
        err("venue.json missing")
        return errors, warnings, {}
    try:
        info = json.load(open(vj))
    except Exception as e:  # noqa: BLE001
        err(f"venue.json: {e}")
        return errors, warnings, {}
    for k in ("Name", "Author", "Scene", "Version"):
        if k not in info:
            err(f"venue.json: missing {k}")
    if "Preview" in info and not os.path.isfile(os.path.join(folder, info["Preview"])):
        err(f"venue.json: Preview file {info['Preview']} missing")
    if "Ambience" in info:
        amb = str(info["Ambience"]).replace("\\", "/")
        if not os.path.isfile(os.path.join(ROOT, amb) if amb.startswith("Assets/") else os.path.join(folder, amb)):
            err(f"venue.json: Ambience file {info['Ambience']} missing")
        vol = info.get("AmbienceVolume", 1)
        if not isinstance(vol, (int, float)) or not 0 <= vol <= 1:
            warnings.append(f"venue.json: AmbienceVolume {vol} is not a number from 0 to 1 (clamped)")
        fade = info.get("AmbienceFade", 8)
        if not isinstance(fade, (int, float)) or fade < 0:
            warnings.append(f"venue.json: AmbienceFade {fade} is not a number of seconds")
    scene_path = os.path.join(folder, info.get("Scene", ""))
    if not os.path.isfile(scene_path):
        err(f"scene {info.get('Scene')} missing")
        return errors, warnings, {}
    try:
        scene = json.load(open(scene_path))
    except Exception as e:  # noqa: BLE001
        err(f"{info['Scene']}: {e}")
        return errors, warnings, {}

    if scene.get("Version") != 2:
        err(f"scene Version is {scene.get('Version')}, expected 2")
    if scene.get("Cores"):
        err(f"scene lists Cores {scene['Cores']} (a venue scene must not)")
    ents = scene.get("Entities", [])
    seen = {}
    registered = registered_components()
    counts = {"entities": len(ents), "VenueShowLight": 0, "shadowed": 0}
    comp_counts = {}
    drummers = infos = 0
    group_children = {}
    for idx, e in enumerate(ents):
        g = e.get("GUID")
        name = e.get("Name", "?")
        if not g or not re.fullmatch(r"[0-9a-f]{16}", g):
            err(f"entity {idx} '{name}': bad GUID {g!r}")
        if g in seen:
            err(f"entity {idx} '{name}': duplicate GUID {g} (also '{seen[g]}')")
        seen[g] = name
        p = e.get("Parent")
        if p is not None:
            if p not in seen:
                err(f"entity {idx} '{name}': Parent {p} missing or not before the child")
            else:
                group_children[p] = group_children.get(p, 0) + 1
        has_light = has_show = False
        for c in e.get("Components", []):
            t = c.get("Type")
            comp_counts[t] = comp_counts.get(t, 0) + 1
            if t not in registered:
                err(f"entity '{name}': unknown component type {t!r}")
            if t in BANNED:
                err(f"entity '{name}': {t} is not allowed in a venue scene")
            if t == "Camera" and c.get("IsCurrent"):
                err(f"entity '{name}': Camera marked current")
            if t == "Light":
                has_light = True
                if c.get("CastShadows"):
                    counts["shadowed"] += 1
            if t == "VenueShowLight":
                has_show = True
                counts["VenueShowLight"] += 1
            if t == "VenueInfo":
                infos += 1
            if t == "VenueSpot" and c.get("Member", "Drummer") == "Drummer":
                drummers += 1
            if t == "VenueSpot" and c.get("Member") not in ("Drummer", "Guitar", "Bass", "Vocals", "Keys"):
                err(f"entity '{name}': bad VenueSpot Member {c.get('Member')!r}")
            for s in strings({k: v for k, v in c.items() if k != "Type"}):
                if os.path.splitext(s)[1].lower() in ASSET_EXT and "/" in s and not resolve(s, folder):
                    err(f"entity '{name}': asset not found: {s}")
        if has_show and not has_light:
            err(f"entity '{name}': VenueShowLight without a Light")
        if not any(c.get("Type") == "Transform" for c in e.get("Components", [])):
            warnings.append(f"entity '{name}': no Transform")
    if infos != 1:
        err(f"expected exactly one VenueInfo, found {infos}")
    if drummers != 1:
        err(f"expected exactly one Drummer VenueSpot, found {drummers}")
    if counts["shadowed"] > MAX_SHADOWED:
        err(f"{counts['shadowed']} shadowed lights (max {MAX_SHADOWED})")
    if counts["VenueShowLight"] > MAX_SHOW_LIGHTS:
        err(f"{counts['VenueShowLight']} VenueShowLights (max {MAX_SHOW_LIGHTS})")
    counts["components"] = comp_counts
    return errors, warnings, counts


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    bad = 0
    for folder in sys.argv[1:]:
        errors, warnings, counts = check(folder)
        print(f"== {folder}")
        if counts:
            c = counts["components"]
            print(f"   entities {counts['entities']}, VenueShowLights {counts['VenueShowLight']}, "
                  f"shadowed lights {counts['shadowed']}")
            print("   " + ", ".join(f"{k} {v}" for k, v in sorted(c.items())))
        for w in warnings:
            print("   warning:", w)
        for e in errors:
            print("   ERROR:", e)
        print("   " + ("FAILED" if errors else "ok"))
        bad += bool(errors)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
