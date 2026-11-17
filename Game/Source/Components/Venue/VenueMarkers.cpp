#include "PCH.h"
#include "VenueMarkers.h"

ME_REFLECT_ENUM( VenueSpot::Role, { { "Drummer", VenueSpot::Role::Drummer }, { "Guitar", VenueSpot::Role::Guitar }, { "Bass", VenueSpot::Role::Bass }, { "Vocals", VenueSpot::Role::Vocals }, { "Keys", VenueSpot::Role::Keys } } )
ME_REFLECT_ENUM( VenueCameraSpot::Kind, { { "Wide", VenueCameraSpot::Kind::Wide }, { "Desk", VenueCameraSpot::Kind::Desk }, { "Crane", VenueCameraSpot::Kind::Crane }, { "Close", VenueCameraSpot::Kind::Close }, { "Custom", VenueCameraSpot::Kind::Custom } } )
ME_REFLECT_ENUM( VenueScreen::Feed, { { "Stage", VenueScreen::Feed::Stage }, { "Program", VenueScreen::Feed::Program }, { "Lyrics", VenueScreen::Feed::Lyrics } } )
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
ME_REFLECT_END()

ME_REFLECT_BEGIN( VenueSpot )
    ME_FIELD( Member ).Tooltip( "Which band member stands here. The performer faces local -Z (identity rotation faces the crowd); position is the feet" );
ME_REFLECT_END()

ME_REFLECT_BEGIN( VenueCrowdArea )
    ME_FIELD( HeadCount ).Range( 0, 5000 ).Tooltip( "People in the rectangle at a full house. Position is the centre, scale x/z the full width/depth in metres, local +Z the way the crowd faces" );
    ME_FIELD( Jitter ).Range( 0.f, 1.f ).Tooltip( "How far each person strays from their grid slot (0 is a neat grid)" );
ME_REFLECT_END()

ME_REFLECT_BEGIN( VenueCameraSpot )
    ME_FIELD( Shot ).Tooltip( "What kind of shot this position is for. The camera looks along local +Z" );
    ME_FIELD( FieldOfView ).Unit( Reflection::Unit::Degrees ).Range( 5.f, 140.f ).Tooltip( "Vertical field of view" );
    ME_FIELD( Tag ).Tooltip( "Free text to tell Custom shots apart" );
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
