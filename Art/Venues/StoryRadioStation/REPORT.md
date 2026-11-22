# StoryRadioStation: The Pledge Drive Night Shift (set 07, `s07-pledge-drive`)

A campus radio station at 02:47. The band plays in a foam-lined live room with carpet tiles and fluorescent troffers (one tube dead). A big window with a red ON AIR lamp above it divides that room from the control room. On the other side of the glass, up a step, are the mixing desk and the engineer. Up a second step is a riser with five phone desks facing the glass, each with a LINE card and a call light on a stalk, and volunteers along the back wall under bunting, a PLEDGE NIGHT banner and a cork board of pledges. The header over the glass holds a LINES lamp board (1-5), the ON AIR lamp and the made-up station's banner ("89.3 THE SIGNAL"). The live-room walls carry posters for made-up campus shows, a whiteboard with the night's notes and a studio clock. Back left is a couch corner and back right a door with an EXIT sign. A rent-o-meter on an easel stands at the right of the glass.

## Files

- `Tools/Venues/make_story_radio_station.py`: the generator (deterministic). `--textures` redraws the pictures and `--sound` resynthesises the room tone.
- `Tools/Venues/story_radio_station_textures.py`: draws every picture with ImageMagick.
- `Tools/Venues/story_radio_station_people.py`: jointed volunteer figures (crowd pieces plus the Backyard's bent arm and seated leg pieces, read-only) and their Sequence clips (OnThePhone, Writing, Bounce, Jump, Faders).
- `Assets/Venues/StoryRadioStation/`: `venue.json`, `StoryRadioStation.lvl`, `Textures/`, `Motion/`, `RoomTone.wav` (ambience) and `Models/` (16 OfficePack FBX files with their `.assbin` twins and the atlas; provenance is in `Models/README.md`).
- `Art/Venues/StoryRadioStation/`: `Previews/`, `cap.sh` (the locked capture helper), the batch scripts, `textures_montage.png`.

## What each flag does

| Flag (song) | Change |
|---|---|
| first_phone_lit (1) | Line 1's red call light (far-left desk) and lamp 1 on the LINES board over the glass light up. A volunteer sits down on the phone. The first pledge slip goes up on the glass level with the presenter's head. The rent-o-meter gets its first segment. |
| second_phone_lit (2) | Line 2 lights at the far-right desk, and board lamp 2 lights. A second volunteer is on the phone. Two more slips go up on the glass. A string between the end desks gets pegged slips filling in from both ends. The meter gets a second segment. |
| pledges_cover_glass (3) | About 90 slips grow over the lower half of the window, leaving a hand-sized gap by the presenter. The pegged line fills in. Volunteers 1 and 2 get up and bounce. The meter gets a third segment. |
| all_phones_lit (4) | Lines 3-5 and their board lamps light. Three more volunteers sit at the middle desks. Slips climb the outer thirds of the glass to the top, closing a frame around the gap. The meter gets a fourth segment. |
| rent_paid (5) | A RENT PAID sheet fills the gap. A big RENT PAID!! banner drops in over the right of the glass with a light on it. The meter tops out in gold with a glow and "WE MADE IT!". The phone volunteers jump with their arms up, and balloons appear in the control room. |

## Band, crowd, cameras, lights

- Spots: Drummer at (0.9, 0, 3.25) on a rug between two foam gobos, with an overhead room mic on a boom, cans, a cable coil and a tape mark. Vocals at (-2.6, 0, 2.75) by the glass, with a lyric stand, a stool and a script table with a lamp. This matches OnStage (drums, guest-vocals).
- Crowd: one Mob area of 9 on the control-room riser, facing the glass (yaw 180). The five phone volunteers, the engineer and the producer are authored figures.
- Cameras: wide (Wide), crane (Crane), desk (Desk), sticks (Close), and the Custom shots first-slip, gap, phone-bank and rent-o-meter, plus an arrival/01-05 walk-in.
- Lights: 11 VenueShowLights (4 Wash, 2 Spot, 2 Beam, 2 Blinder, 1 Strobe), none under a story group. One shadowed directional (a cool soft key). The rest are plain practicals: the fluorescents, wall washes, the ON AIR red glow, the presenter lamp and the console glow. The story groups hold their own plain lights (the call lights, the banner light and the goal glow).

## Couldn't do / notes

- I didn't check the director's "crowd" cue shots, whose crowd stands behind the band across the glass. The capture queue was capped at about 8 shots.
- The volunteers' poses are hand-authored joint angles, seen only at a distance. They may want tweaks in `CLIPS` after a close look.
- The bounce and jump clips loop at a fixed tempo and aren't synced to the beat.
- Nothing for NEEDS.md.
