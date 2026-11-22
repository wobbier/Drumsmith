# StoryCoffeeShop: set 03 "The Millennial Coffee Shop"

"Second Pour", a made-up café on a sunny morning. The house kit sits on a rug where a two-top used to be; that table is pushed against the bar end with its chairs stacked on it. Regulars sit close on three sides. Behind the kit is the bar with an espresso machine, steam wand, pastry case and till. The chalkboard over the bar reads "TODAY: an intimate acoustic session". Edison bulbs, plants, an exposed brick wall with prints, a banquette, a window bar, and big front windows with sun on the floor and a drawn street outside. Band: a Drummer spot only (Jules is a prop with a guitar, not a spot). Ambience: a looping café room tone, `Ambience.ogg`.

## Files
- Generator: `Tools/Venues/make_story_coffee_shop.py` (`--textures` redraws the textures and the sound).
- `Tools/Venues/story_coffee_shop_textures.py`: the drawn textures.
- `Tools/Venues/story_coffee_shop_people.py`: re-skinned and bent crowd pieces, plus 7 motion clips.
- `Tools/Venues/story_coffee_shop_sound.py`: the ambience.
- `Assets/Venues/StoryCoffeeShop/`: `venue.json`, `StoryCoffeeShop.lvl`, `Preview.jpg`, `Ambience.ogg`, `Textures/`, `Motion/`, `Models/`, `Models/People/`. `Models/` has 14 Synty FBX files and 2 atlases copied from Office and Explorer Kit; `Models/README.md` records their provenance under the owner's Synty licence.

## Flags
| Flag | Change |
|------|--------|
| `guitar_at_counter` | Jules, playing guitar on a stool by the kit, disappears. The guitar appears on a stand by the till and Jules appears behind the bar at the steam wand. The stool stays, empty. |
| `laptop_lowered` | The laptop lid on the window two-top drops from 105° to 38°. The couple switch from heads-down typing to looking up at the kit. |
| `chairs_turned` | The pair at the right-hand table turn their chairs to the kit and sway. The backpack moves from the third chair to under the table, and that chair reappears in the warm light pool by the kit. |
| `spare_chair_filled` | A new regular sits in that chair, swaying with the pair. |
| `wand_off` | The steam (particles and see-through clouds above the machine) stops. Jules switches from steaming to clapping, and an untouched latte appears on the pass under a small lamp. |

## Cameras
- Wide `door-corner`, Crane `over-the-window-bar`, Desk `from-the-door`.
- Custom: `laptop-two-top`, `the-bar`, `spare-chair`, `over-the-hats` (reverse shot from behind the kit). Close: `brushes`.
- Intro: `arrival/01`–`06`, a walk in from the front door to the kit.

## Lights
- 1 shadow-casting directional (the sun); 26 VenueShowLights, none under a story group.
- Static (21): the sun, 4 window daylight spots, 8 Edison bulbs, the kit bulbs, 3 bar pendants, 4 brick grazers. Wash (4): 2 clamp lamps (groups 0 and 1), 2 side washes (group 2). Spot (1): a follow light on the drummer.
- Plain lights: the warm pool by the spare chair, the chalkboard picture light, the pastry case, the laptop screen glow and the lamp on the pass (the last two under story groups, so they fade with them).

## Crowd
4 small standing groups (16 people) and 13 seated regulars, plus the people who come and go with the story.

## Previews (960x540, `Art/Venues/StoryCoffeeShop/Previews/`)
`wide_song1_start.png`, `wide_song3.png`, `wide_song5_end.png`, `drummer.png`, `beat.png` (the laptop two-top after the lid drops, guitar on its stand at right), `the_bar.png` (steam, pastry case and chalkboard in song 4).

## Known issues
- The bar camera was moved higher after `the_bar.png`; in that preview the espresso machine hides Jules. Not re-shot (capture cap).
- The chalkboard's "acoustic session" ran off the edge; it was redrawn and its stale `.dds` deleted, but the captures show the old clipped board.
- In the wide, the guitar on its stand and the untouched cup sit under the song-title card at song start.
- One standing person sits large in the lower-left corner of the wide.
- The espresso machine shows its plain back to the room.
- Retail: the copied FBX and PNG files have no cooked twins (`.assbin`, `.dds`) yet; Retail needs a Build Assets pass.

## NEEDS.md
None.
