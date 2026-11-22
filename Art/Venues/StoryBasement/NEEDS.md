# StoryBasement: framework requests

1. **A gateable / movable VenueScreen.** The design has the camcorder's picture on the CRT, which is
   then turned toward the kit. A `VenueScreen` under a `VenueStory` group isn't gated (the show builds
   the quad from the plan, outside the scene hierarchy), so the CRT shows a painted still. If the show
   parented each screen quad to its marker entity (so the story scale applies) the CRT could carry a
   live `Stage` feed in both positions.
2. **HideoutMotion in venues (optional).** Rooms imported from the hideout lose their small motions
   (swinging bulb, blinking tally lamp, the cat breathing). A venue-side runner for the simple kinds
   (Sway, Pulse, Blink, Flicker, Breathe) would let the basement feel as alive as in the menu.
