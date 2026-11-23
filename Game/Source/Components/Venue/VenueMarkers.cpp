#include "PCH.h"
#include "VenueMarkers.h"

ME_REFLECT_ENUM( VenueSpot::Role, { { "Drummer", VenueSpot::Role::Drummer }, { "Guitar", VenueSpot::Role::Guitar }, { "Bass", VenueSpot::Role::Bass }, { "Vocals", VenueSpot::Role::Vocals }, { "Keys", VenueSpot::Role::Keys } } )
ME_REFLECT_ENUM( VenueCameraSpot::Kind, { { "Wide", VenueCameraSpot::Kind::Wide }, { "Desk", VenueCameraSpot::Kind::Desk }, { "Crane", VenueCameraSpot::Kind::Crane }, { "Close", VenueCameraSpot::Kind::Close }, { "Custom", VenueCameraSpot::Kind::Custom } } )
ME_REFLECT_ENUM( VenueStory::Motion, { { "Show", VenueStory::Motion::Show }, { "Play", VenueStory::Motion::Play }, { "SlowMotion", VenueStory::Motion::SlowMotion } } )
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
    ME_FIELD( Footage ).Category( "Cameras" ).Tooltip( "Who filmed the live show: the crew (Broadcast), or only the guests' camcorders, flip phones or both, from the guest/ camera spots. The music video keeps the real cameras" );
ME_REFLECT_END()

ME_REFLECT_BEGIN( VenueSpot )
    ME_FIELD( Member ).Tooltip( "Which band member stands here. The performer faces local -Z (identity rotation faces the crowd); position is the feet" );
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

ME_REFLECT_BEGIN( VenueStory )
    ME_FIELD( Flag ).Tooltip( "The story flag (Design/Story-Mode-Setlists.json StateFlags) this entity follows" );
    ME_FIELD( WhenSet ).Tooltip( "On: shown once the flag is set. Off: shown until it is set (the thing that moves away)" );
    ME_FIELD( FadeSeconds ).Range( 0.f, 10.f ).Tooltip( "How long it takes to grow in or shrink away" );
    ME_FIELD( Mode ).Tooltip( "Show: shown or hidden by the flag. Play: its Sequences play once when the flag lands. SlowMotion: its Sequences run at Speed until the flag lands" );
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
