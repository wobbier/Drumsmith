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

ME_REFLECT_ENUM( HideoutMotion::Kind, { { "Sway", HideoutMotion::Kind::Sway }, { "Flicker", HideoutMotion::Kind::Flicker }, { "Pulse", HideoutMotion::Kind::Pulse }, { "Spin", HideoutMotion::Kind::Spin }, { "Breathe", HideoutMotion::Kind::Breathe }, { "Blink", HideoutMotion::Kind::Blink }, { "Bob", HideoutMotion::Kind::Bob }, { "Pass", HideoutMotion::Kind::Pass } } )

ME_REFLECT_BEGIN( HideoutMotion )
    ME_FIELD( Motion ).Tooltip( "Sway: swings about Axis. Flicker: the Light dips at random. Pulse: the Light (or scale) jumps on each beat. Spin: turns about Axis. Breathe: scales along Axis. Blink: on and off. Bob: moves along Axis on each beat" );
    ME_FIELD( Amount ).Tooltip( "Degrees for Sway, 0..1 for Flicker/Pulse/Breathe/Blink (Blink: the share of each cycle it's on), metres for Bob" );
    ME_FIELD( Speed ).Tooltip( "Cycles a second (Spin: degrees a second)" );
    ME_FIELD( Axis ).Tooltip( "Local axis for Sway, Spin, Breathe and Bob" );
    ME_FIELD( Phase ).Range( 0.f, 1.f ).Tooltip( "Where in its cycle it starts" );
    ME_FIELD( Music ).Tooltip( "Follow the radio: its beat and how loud it is, instead of a clock" );
ME_REFLECT_END()

ME_REFLECT_BEGIN( HideoutDrummer )
    ME_FIELD( Cast ).Range( 0, 1000 ).Tooltip( "Which character plays; the same one whatever the song" );
    ME_FIELD( Yaw ).Unit( Reflection::Unit::Degrees ).Tooltip( "Which way the drummer faces (180: -z); the kit is in front of them" );
    ME_FIELD( Energy ).Range( 0.f, 1.f ).Tooltip( "How hard the drummer goes at it" );
ME_REFLECT_END()

ME_REFLECT_BEGIN( HideoutView )
    ME_FIELD( FieldOfView ).Unit( Reflection::Unit::Degrees ).Range( 10.f, 120.f ).Tooltip( "The overview's vertical field of view. The camera looks along local +Z" );
    ME_FIELD( IntroEye ).Unit( Reflection::Unit::Meters ).Tooltip( "The first time the menu opens in a session, the camera starts here and comes to the overview. All zero: no intro" );
    ME_FIELD( IntroTarget ).Unit( Reflection::Unit::Meters ).Tooltip( "What the camera looks at as the intro starts" );
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


HideoutMotion::HideoutMotion()
    : Component( "HideoutMotion" )
{
}


void HideoutMotion::Init()
{
}


HideoutDrummer::HideoutDrummer()
    : Component( "HideoutDrummer" )
{
}


void HideoutDrummer::Init()
{
}


HideoutView::HideoutView()
    : Component( "HideoutView" )
{
}


void HideoutView::Init()
{
}
