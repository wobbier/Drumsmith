#include "PCH.h"
#include "VenueMarkers.h"

ME_REFLECT_ENUM( VenueSpot::Role, { { "Drummer", VenueSpot::Role::Drummer }, { "Guitar", VenueSpot::Role::Guitar }, { "Bass", VenueSpot::Role::Bass }, { "Vocals", VenueSpot::Role::Vocals }, { "Keys", VenueSpot::Role::Keys } } )
ME_REFLECT_ENUM( VenueCameraSpot::Kind, { { "Wide", VenueCameraSpot::Kind::Wide }, { "Desk", VenueCameraSpot::Kind::Desk }, { "Crane", VenueCameraSpot::Kind::Crane }, { "Close", VenueCameraSpot::Kind::Close }, { "Custom", VenueCameraSpot::Kind::Custom } } )
ME_REFLECT_ENUM( VenueBeat::Cue, { { "Beat", VenueBeat::Cue::Beat }, { "Hit", VenueBeat::Cue::Hit }, { "Accent", VenueBeat::Cue::Accent }, { "Miss", VenueBeat::Cue::Miss } } )
ME_REFLECT_ENUM( VenueStory::Motion, { { "Show", VenueStory::Motion::Show }, { "Play", VenueStory::Motion::Play }, { "SlowMotion", VenueStory::Motion::SlowMotion },
                                         { "Clock", VenueStory::Motion::Clock } } )
ME_REFLECT_ENUM( VenueCrowdArea::Kind, { { "Mob", VenueCrowdArea::Kind::Mob }, { "Posed", VenueCrowdArea::Kind::Posed } } )
ME_REFLECT_ENUM( VenueScreen::Feed, { { "Stage", VenueScreen::Feed::Stage }, { "Program", VenueScreen::Feed::Program }, { "Lyrics", VenueScreen::Feed::Lyrics } } )
ME_REFLECT_ENUM( VenueInfo::FootageKind, { { "Broadcast", VenueInfo::FootageKind::Broadcast }, { "Camcorder", VenueInfo::FootageKind::Camcorder }, { "Phone", VenueInfo::FootageKind::Phone }, { "Mixed", VenueInfo::FootageKind::Mixed } } )
ME_REFLECT_ENUM( VenueShowLight::Role, { { "Wash", VenueShowLight::Role::Wash }, { "Beam", VenueShowLight::Role::Beam }, { "Spot", VenueShowLight::Role::Spot }, { "Blinder", VenueShowLight::Role::Blinder }, { "Strobe", VenueShowLight::Role::Strobe }, { "Static", VenueShowLight::Role::Static } } )

ME_REFLECT_BEGIN( VenueInfo )
    ME_FIELD( Name ).Tooltip( "The venue's display name" );
    ME_FIELD( Author );
    ME_FIELD( Outdoor ).Tooltip( "Outdoor venues have no ceiling lighting and take the sky" );
    ME_FIELD( RoomBack ).Unit( Reflection::Unit::Meters ).Tooltip( "z of the back wall, venue space. The default means no wall" );
    ME_FIELD( RoomCeiling ).Unit( Reflection::Unit::Meters ).Tooltip( "y of the ceiling. The default means no ceiling" );
    ME_FIELD( RoomHalfWidth ).Unit( Reflection::Unit::Meters ).Tooltip( "Half the room's width, side wall to centre" );
    ME_FIELD( DeskZ ).Unit( Reflection::Unit::Meters ).Tooltip( "z of the sound desk, where the crowd ends and the Desk camera sits" );
    ME_FIELD( BuildStage ).Category( "Built-in pieces" ).Tooltip( "Also add the built-in stage deck. Off when the scene has its own geometry" );
    ME_FIELD( BuildSet ).Category( "Built-in pieces" ).Tooltip( "Also add the built-in set dressing" );
    ME_FIELD( BuildRig ).Category( "Built-in pieces" ).Tooltip( "Also add the built-in light rig" );
    ME_FIELD( BuildFx ).Category( "Built-in pieces" ).Tooltip( "Also add the built-in effects" );
    ME_FIELD( AmbientColor ).Category( "Look" ).Color().Tooltip( "Indoors: the colour behind everything, which also lights the whole room a little" );
    ME_FIELD( FogColor ).Category( "Look" ).HDR().Tooltip( "The light the haze scatters: lifts whatever is far off" );
    ME_FIELD( Haze ).Category( "Look" ).Unit( Reflection::Unit::Multiplier ).Range( 0.f, 4.f ).Tooltip( "How thick the haze hangs (1 the usual; out of doors it is already under half that)" );
    ME_FIELD( SkyTime ).Category( "Look" ).Unit( Reflection::Unit::Hours ).Range( 0.f, 24.f ).Tooltip( "Out of doors: the night sky's hour (20 is dusk, 22 night)" );
    ME_FIELD( MoonBrightness ).Category( "Look" ).Unit( Reflection::Unit::Multiplier ).Range( 0.f, 10.f ).Tooltip( "Out of doors: how bright the moon is" );
    ME_FIELD( CloudCoverage ).Category( "Look" ).Unit( Reflection::Unit::Percent ).Range( 0.f, 1.f ).Tooltip( "Out of doors: how much of the sky is cloud. 0 runs no cloud pass (a dark night sky shows its clouds only as missing stars)" );
    ME_FIELD( HazeFroxels ).Category( "Look" ).Display( "Haze Froxels" ).Tooltip( "Light the show's haze from a grid of cells instead of the per-pixel march: far cheaper, softer on narrow beams. Suits an outdoor haze; a club full of crisp beams looks better without" );
    ME_FIELD( Ride ).Category( "Cameras" ).Unit( Reflection::Unit::Multiplier ).Range( 0.f, 3.f ).Tooltip( "The venue is on the move: every camera but an aerial story shot rattles, heaves and takes the road's bumps this hard (0 none, 1 a fast highway)" );
    ME_FIELD( RideUntil ).Category( "Cameras" ).Tooltip( "The story flag that ends the ride (the crash). Empty: it never stops" );
    ME_FIELD( KeepRed ).Category( "Look" ).Unit( Reflection::Unit::Percent ).Range( 0.f, 1.f ).Tooltip( "How much red a black and white (or any desaturating) look leaves in colour here" );
    ME_FIELD( KeepBlue ).Category( "Look" ).Unit( Reflection::Unit::Percent ).Range( 0.f, 1.f ).Tooltip( "The same for blue" );
    ME_FIELD( KeepWarmth ).Category( "Look" ).Range( 0.f, 1.f ).Tooltip( "How far the kept reds reach: 0 pure red, 1 through orange to yellow (fire)" );
    ME_FIELD( LightsFrom ).Category( "Look" ).Tooltip( "From this story flag (empty: from the start, if Lights Until is set) every look keeps reds, blues and fire: police lights at a crash" );
    ME_FIELD( LightsUntil ).Category( "Look" ).Tooltip( "Until this story flag (empty: to the end, if Lights From is set)" );
    ME_FIELD( QuietLook ).Category( "Look" ).Tooltip( "A chart with no looks of its own plays its intro, bridges and breakdowns in the black and white concert look. Off: this venue stays in colour through them" );
    ME_FIELD( Footage ).Category( "Cameras" ).Tooltip( "Who filmed the live show: the crew (Broadcast), or only the guests' camcorders, flip phones or both, from the guest/ camera spots. The music video keeps the real cameras" );
ME_REFLECT_END()

ME_REFLECT_BEGIN( VenueSpot )
    ME_FIELD( Member ).Tooltip( "Which band member stands here. The performer faces local -Z (identity rotation faces the crowd); position is the feet" );
    ME_FIELD( SeatHeight ).Tooltip( "Seated hip height above this marker in metres. Zero uses the usual performance stance" );
    ME_FIELD( PowerStance ).Tooltip( "A guitarist or bassist planted wide, knees bent and leaning back, who never walks out front (on a roof, on a ledge)" );
    ME_FIELD( Gear ).Tooltip( "The amp, wedges and mic stand of a stage spot. Off: only the player and what they hold" );
ME_REFLECT_END()

ME_REFLECT_BEGIN( VenueCrowdArea )
    ME_FIELD( DanceFloor ).Tooltip( "Posed figures trade jumps from side to side during loud passages" );
    ME_FIELD( Figures ).Tooltip( "Mob: cheap instanced figures, for the back. Posed: the full figures of the built-in rooms' front rows (cheers, phones, the crowd surfer), filled in rows from the area's +Z edge back, so face the area at the stage" );
    ME_FIELD( HeadCount ).Range( 0, 5000 ).Tooltip( "People in the rectangle at a full house. Position is the centre, scale x/z the full width/depth in metres, local +Z the way the crowd faces" );
    ME_FIELD( Jitter ).Range( 0.f, 1.f ).Tooltip( "How far each person strays from their grid slot (0 is a neat grid)" );
ME_REFLECT_END()

ME_REFLECT_BEGIN( VenueAccent )
    ME_FIELD( FullLightingOnly ).Tooltip( "Hold the first sequence key with gentle or disabled stage lighting." );
    ME_FIELD( Beats ).Range( 1.f, 32.f ).Tooltip( "Length of the attached Sequence on the song clock. Use the same resting pose at both ends." );
    ME_FIELD( Particles ).Range( 0, 512 ).Tooltip( "Burst on the attached ParticleSystem at a peak. Ordinary lifts get half." );
ME_REFLECT_END()

ME_REFLECT_BEGIN( VenueBeat )
    ME_FIELD( Offset ).Tooltip( "Where the entity is at the peak of each move, from its resting position (metres, in its parent's space)" );
    ME_FIELD( Every ).Range( 0.25f, 16.f ).Tooltip( "One move every this many beats" );
    ME_FIELD( Phase ).Range( 0.f, 16.f ).Tooltip( "How many beats late the move starts (0.5: on the off-beat)" );
    ME_FIELD( Sway ).Tooltip( "Off: out on the beat and back, like a nod. On: smoothly to Offset and to its opposite, like a sway" );
    ME_FIELD( Sharp ).Tooltip( "Out at once on the beat and straight back, with no gathering before the next: a blip, like a heart monitor's trace" );
    ME_FIELD( Turn ).Unit( Reflection::Unit::Degrees ).Tooltip( "How far it is turned at the peak of each move (degrees about its own origin, on top of its rotation): a cage swinging from its chain" );
    ME_FIELD( Nod ).Unit( Reflection::Unit::Degrees ).Tooltip( "A VenueFigure on the same entity nods its head this far at the peak of each move, on top of its own Nod" );
    ME_FIELD( Calm ).Range( 0.f, 1.f ).Tooltip( "How much of the move there is while the player plays at their worst (1: the same whatever the playing)" );
    ME_FIELD( Trigger ).Tooltip( "What sets the move off: the song's beats, or each of the player's hits, big notes (crash or kick) or misses" );
ME_REFLECT_END()

ME_REFLECT_ENUM( VenueMood::Shown, { { "Always", VenueMood::Shown::Always }, { "Good", VenueMood::Shown::Good }, { "Bad", VenueMood::Shown::Bad } } )

ME_REFLECT_BEGIN( VenueMood )
    ME_FIELD( Offset ).Unit( Reflection::Unit::Meters ).Tooltip( "Where the entity is while the player plays at their worst, from its resting position (in its parent's space)" );
    ME_FIELD( Show ).Tooltip( "Always shown, or only while the playing is good (at or over Threshold) or bad (under it)" );
    ME_FIELD( Threshold ).Range( 0.f, 1.f ).Tooltip( "The mood (0 worst, 1 best playing) that divides good from bad" );
    ME_FIELD( Seconds ).Range( 0.05f, 30.f ).Unit( Reflection::Unit::Seconds ).Tooltip( "About how long it takes to follow a change in the playing" );
    ME_FIELD( Speed ).Range( 0.f, 4.f ).Unit( Reflection::Unit::Multiplier ).Tooltip( "The speed of the Sequence on this entity while the player plays at their worst (1 at their best)" );
ME_REFLECT_END()

ME_REFLECT_BEGIN( VenueSound )
    ME_FIELD( Flag ).Tooltip( "The story flag whose landing plays the sound, once" );
    ME_FIELD( Sound ).Tooltip( "The sound file's asset path (Assets/Venues/<venue>/Sounds/...)" );
    ME_FIELD( Volume ).Range( 0.f, 2.f ).Tooltip( "How loud it plays (1: as recorded)" );
    ME_FIELD( Delay ).Range( 0.f, 60.f ).Unit( Reflection::Unit::Seconds ).Tooltip( "How long after the flag lands the sound starts" );
ME_REFLECT_END()

ME_REFLECT_BEGIN( VenueAim )
    ME_FIELD( Target ).Tooltip( "The point the entity's local +Z is held on, in the venue's space (metres from the venue's origin)" );
    ME_FIELD( Wander ).Range( 0.f, 20.f ).Tooltip( "How far from the point the aim strays, in metres: a hand-held searchlight. 0 holds it dead on the point" );
    ME_FIELD( Seconds ).Range( 0.2f, 30.f ).Tooltip( "Roughly how long one drift across the point takes" );
ME_REFLECT_END()

ME_REFLECT_ENUM( VenueFigure::Stance, { { "Standing", VenueFigure::Stance::Standing }, { "Seated", VenueFigure::Stance::Seated }, { "Kneeling", VenueFigure::Stance::Kneeling } } )
ME_REFLECT_ENUM( VenueFigure::Dress, { { "Own", VenueFigure::Dress::Own }, { "Drummer", VenueFigure::Dress::Drummer }, { "Guitar", VenueFigure::Dress::Guitar },
    { "Bass", VenueFigure::Dress::Bass }, { "Vocals", VenueFigure::Dress::Vocals }, { "Keys", VenueFigure::Dress::Keys } } )

ME_REFLECT_BEGIN( VenueFigure::Arm )
    ME_FIELD( Raise ).Unit( Reflection::Unit::Degrees ).Tooltip( "The arm swung forward from hanging: 90 points ahead, 180 straight up" );
    ME_FIELD( Spread ).Unit( Reflection::Unit::Degrees ).Tooltip( "The arm out to the side (negative: in across the body)" );
    ME_FIELD( Elbow ).Unit( Reflection::Unit::Degrees ).Tooltip( "The forearm bent forward" );
    ME_FIELD( Reach ).Tooltip( "The palm goes to Hand, by inverse kinematics, instead of the angles above" );
    ME_FIELD( Hand ).Unit( Reflection::Unit::Meters ).Tooltip( "Where the palm's centre lands, in the figure's space (its feet at the origin, facing +Z, its right +X)" );
    ME_FIELD( Pole ).Tooltip( "The direction the elbow bends toward" );
    ME_FIELD( Fingers ).Tooltip( "The direction the fingers point (zero: a straight wrist)" );
    ME_FIELD( Palm ).Tooltip( "What the palm faces (zero: as the arm turned it)" );
    ME_FIELD( Grip ).Range( 0.f, 1.f ).Tooltip( "0 an open hand, 1 a fist" );
ME_REFLECT_END()

ME_REFLECT_BEGIN( VenueFigure::Leg )
    ME_FIELD( Spread ).Unit( Reflection::Unit::Degrees ).Tooltip( "The foot (kneeling: the knee) out to the side" );
    ME_FIELD( Toe ).Unit( Reflection::Unit::Degrees ).Tooltip( "The foot pitched down" );
    ME_FIELD( Reach ).Tooltip( "The sole goes to Foot, by inverse kinematics, instead of standing (or kneeling) on the floor" );
    ME_FIELD( Foot ).Unit( Reflection::Unit::Meters ).Tooltip( "Where the sole lands, in the figure's space" );
    ME_FIELD( Knee ).Tooltip( "The direction the knee bends toward" );
ME_REFLECT_END()

ME_REFLECT_BEGIN( VenueFigure )
    ME_FIELD( Character ).Tooltip( "The rigged character (a T-posed Rigify human from Assets/Models/People)" );
    ME_FIELD( Atlas ).Tooltip( "The PolygonTown atlas the character's UVs index: its clothes" );
    ME_FIELD( As ).Display( "Dress As" ).Tooltip( "Own: Character and Atlas. A band member: whoever plays that part in the song, in their clothes (the band's own bodies)" );
    ME_FIELD( Height ).Unit( Reflection::Unit::Multiplier ).Range( 0.2f, 3.f ).Tooltip( "A scale on the whole figure" );
    ME_FIELD( Stand ).Display( "Stance" ).Tooltip( "Standing, Seated (the hips at Seat Height) or Kneeling (the knees on the floor at the entity)" );
    ME_FIELD( SeatHeight ).Unit( Reflection::Unit::Meters ).Tooltip( "Seated: how high the hip joints are" );
    ME_FIELD( Offset ).Unit( Reflection::Unit::Meters ).Tooltip( "The whole figure moved: a bounce, a step" );
    ME_FIELD( Crouch ).Unit( Reflection::Unit::Meters ).Tooltip( "How far the hips drop, the knees bending to suit" );
    ME_FIELD( Bow ).Unit( Reflection::Unit::Degrees ).Tooltip( "The whole trunk forward from the hips" );
    ME_FIELD( Lean ).Unit( Reflection::Unit::Degrees ).Tooltip( "The spine curled forward" );
    ME_FIELD( Side ).Unit( Reflection::Unit::Degrees ).Tooltip( "The spine to the figure's right" );
    ME_FIELD( Turn ).Unit( Reflection::Unit::Degrees ).Tooltip( "The chest turned to the figure's right" );
    ME_FIELD( Nod ).Unit( Reflection::Unit::Degrees ).Tooltip( "The head down" );
    ME_FIELD( HeadTurn ).Unit( Reflection::Unit::Degrees ).Tooltip( "The head turned to the figure's right" );
    ME_FIELD( HeadTilt ).Unit( Reflection::Unit::Degrees );
    ME_FIELD( Mouth ).Range( 0.f, 1.f ).Tooltip( "0 shut, 1 wide open" );
    ME_FIELD( LeftArm ).Category( "Limbs" );
    ME_FIELD( RightArm ).Category( "Limbs" );
    ME_FIELD( LeftLeg ).Category( "Limbs" );
    ME_FIELD( RightLeg ).Category( "Limbs" );
ME_REFLECT_END()

ME_REFLECT_BEGIN( VenueStory )
    ME_FIELD( Flag ).Tooltip( "The story flag (Design/Story-Mode-Setlists.json StateFlags) this entity follows" );
    ME_FIELD( Unless ).Tooltip( "Optional: a later flag that takes Flag back. While it is set, Flag counts as not set (with When Set off: gone from Flag until this one, then back)" );
    ME_FIELD( WhenSet ).Tooltip( "On: shown once the flag is set. Off: shown until it is set (the thing that moves away)" );
    ME_FIELD( FadeSeconds ).Range( 0.f, 10.f ).Tooltip( "How long it takes to grow in or shrink away" );
    ME_FIELD( Mode ).Tooltip( "Show: shown or hidden by the flag. Play: its Sequences play once when the flag lands. SlowMotion: its Sequences run at Speed until the flag lands. Clock: its Sequences are held to the song's clock from the moment the flag lands (a loop wraps), so a story shot can be timed against them" );
    ME_FIELD( Speed ).Unit( Reflection::Unit::Multiplier ).Range( 0.01f, 1.f ).Tooltip( "SlowMotion: the Sequences' speed until the flag lands" );
ME_REFLECT_END()

ME_REFLECT_BEGIN( VenueCameraSpot )
    ME_FIELD( Shot ).Tooltip( "What kind of shot this position is for. The camera looks along local +Z" );
    ME_FIELD( FieldOfView ).Unit( Reflection::Unit::Degrees ).Range( 5.f, 140.f ).Tooltip( "Vertical field of view" );
    ME_FIELD( Tag ).Tooltip( "Free text to tell Custom shots apart. guest/<name> is a party guest's camera (footage venues); add @dv or @phone to pick the device" );
ME_REFLECT_END()

ME_REFLECT_BEGIN( VenueScreen )
    ME_FIELD( Source ).Tooltip( "The feed shown. Scale x/y is the quad size in metres; the picture faces local -Z" );
    ME_FIELD( Emissive ).Unit( Reflection::Unit::Multiplier ).Range( 0.f, 100.f ).Tooltip( "HDR multiplier on the light the picture gives off" );
ME_REFLECT_END()

ME_REFLECT_BEGIN( VenueShowLight )
    ME_FIELD( Kind ).Tooltip( "The part this light plays in the show. Put it on an entity with a Light component" );
    ME_FIELD( Group ).Range( 0, 255 ).Tooltip( "Lights in the same group are cued together" );
ME_REFLECT_END()


VenueInfo::VenueInfo()
    : Component( "VenueInfo" )
{
}


void VenueInfo::Init()
{
}


VenueSpot::VenueSpot()
    : Component( "VenueSpot" )
{
}


void VenueSpot::Init()
{
}


VenueCrowdArea::VenueCrowdArea()
    : Component( "VenueCrowdArea" )
{
}


void VenueCrowdArea::Init()
{
}


VenueCameraSpot::VenueCameraSpot()
    : Component( "VenueCameraSpot" )
{
}


void VenueCameraSpot::Init()
{
}


VenueScreen::VenueScreen()
    : Component( "VenueScreen" )
{
}


void VenueScreen::Init()
{
}


VenueShowLight::VenueShowLight()
    : Component( "VenueShowLight" )
{
}


void VenueShowLight::Init()
{
}
