#include "PCH.h"
#include "HideoutMarkers.h"

ME_REFLECT_ENUM( HideoutStation::Kind, { { "Kit", HideoutStation::Kind::Kit }, { "PracticePad", HideoutStation::Kind::PracticePad }, { "Radio", HideoutStation::Kind::Radio }, { "Laptop", HideoutStation::Kind::Laptop }, { "TrophyWall", HideoutStation::Kind::TrophyWall }, { "Mixer", HideoutStation::Kind::Mixer }, { "GigBoard", HideoutStation::Kind::GigBoard }, { "Door", HideoutStation::Kind::Door } } )

ME_REFLECT_BEGIN( HideoutStation )
    ME_FIELD( Station ).Tooltip( "What choosing it does: Kit the song library, PracticePad the lessons, Radio the radio, Laptop the DLC catalogue, TrophyWall your records, Mixer the settings, GigBoard the gigs, Door quits" );
    ME_FIELD( Label ).Tooltip( "The label shown over it; empty uses the station's usual name" );
    ME_FIELD( ViewOffset ).Unit( Reflection::Unit::Meters ).Tooltip( "Where the camera stands when the station is chosen, from the entity's position (room space)" );
    ME_FIELD( FieldOfView ).Unit( Reflection::Unit::Degrees ).Range( 10.f, 120.f ).Tooltip( "Vertical field of view while chosen" );
ME_REFLECT_END()

ME_REFLECT_BEGIN( HideoutItemSlot )
    ME_FIELD( Slot ).Tooltip( "The slot an item names (Assets/Progression/Progression.json). This entity and its children are hidden until that item is unlocked" );
ME_REFLECT_END()

ME_REFLECT_BEGIN( HideoutView )
    ME_FIELD( FieldOfView ).Unit( Reflection::Unit::Degrees ).Range( 10.f, 120.f ).Tooltip( "The overview's vertical field of view. The camera looks along local +Z" );
ME_REFLECT_END()


HideoutStation::HideoutStation()
    : Component( "HideoutStation" )
{
}


void HideoutStation::Init()
{
}


HideoutItemSlot::HideoutItemSlot()
    : Component( "HideoutItemSlot" )
{
}


void HideoutItemSlot::Init()
{
}


HideoutView::HideoutView()
    : Component( "HideoutView" )
{
}


void HideoutView::Init()
{
}
