#include "PCH.h"
#include "HideoutMarkers.h"

ME_REFLECT_ENUM( HideoutStation::Kind, { { "Kit", HideoutStation::Kind::Kit }, { "PracticePad", HideoutStation::Kind::PracticePad }, { "Radio", HideoutStation::Kind::Radio }, { "Laptop", HideoutStation::Kind::Laptop }, { "TrophyWall", HideoutStation::Kind::TrophyWall }, { "Mixer", HideoutStation::Kind::Mixer }, { "GigBoard", HideoutStation::Kind::GigBoard }, { "Door", HideoutStation::Kind::Door }, { "Wishlist", HideoutStation::Kind::Wishlist } } )

ME_REFLECT_BEGIN( HideoutStation )
    ME_FIELD( Station ).Tooltip( "What choosing it does: Kit the song library, PracticePad the lessons, Radio the radio, Laptop the DLC catalogue, TrophyWall your records, Mixer the settings, GigBoard the gigs, Door quits, Wishlist the gear still to come and how to get it" );
    ME_FIELD( Label ).Tooltip( "The label shown over it; empty uses the station's usual name" );
    ME_FIELD( ViewOffset ).Unit( Reflection::Unit::Meters ).Tooltip( "Where the camera stands when the station is chosen, from the entity's position (room space)" );
    ME_FIELD( FieldOfView ).Unit( Reflection::Unit::Degrees ).Range( 10.f, 120.f ).Tooltip( "Vertical field of view while chosen" );
ME_REFLECT_END()

ME_REFLECT_BEGIN( HideoutItemSlot )
    ME_FIELD( Slot ).Tooltip( "The slot an item names (Assets/Progression/Progression.json). This entity and its children are hidden until that item is unlocked" );
    ME_FIELD( WhenLocked ).Tooltip( "A stand-in instead: shown only until the slot's item is unlocked" );
    ME_FIELD( ViewOffset ).Unit( Reflection::Unit::Meters ).Tooltip( "Where the new items' tour camera stands, from the middle of the item's pieces; all zero picks a spot toward the doorway" );
ME_REFLECT_END()

ME_REFLECT_ENUM( HideoutMotion::Kind, { { "Sway", HideoutMotion::Kind::Sway }, { "Flicker", HideoutMotion::Kind::Flicker }, { "Pulse", HideoutMotion::Kind::Pulse }, { "Spin", HideoutMotion::Kind::Spin }, { "Breathe", HideoutMotion::Kind::Breathe }, { "Blink", HideoutMotion::Kind::Blink }, { "Bob", HideoutMotion::Kind::Bob }, { "Pass", HideoutMotion::Kind::Pass }, { "Hour", HideoutMotion::Kind::Hour }, { "Minute", HideoutMotion::Kind::Minute }, { "Second", HideoutMotion::Kind::Second } } )

ME_REFLECT_BEGIN( HideoutMotion )
    ME_FIELD( Motion ).Tooltip( "Sway: swings about Axis. Flicker: the Light dips at random. Pulse: the Light (or scale) jumps on each beat. Spin: turns about Axis. Breathe: scales along Axis. Blink: on and off. Bob: moves along Axis on each beat. Pass: sweeps along Axis now and then. Hour/Minute/Second: a clock hand on the player's clock" );
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
    ME_FIELD( Finish ).Color().Tooltip( "The drum shells' lacquer; black (all zero) keeps the kit's own oxblood" );
    ME_FIELD( FinishMetallic ).Range( 0.f, 1.f ).Tooltip( "The lacquer's metal flake" );
    ME_FIELD( FinishRoughness ).Range( 0.f, 1.f ).Tooltip( "How glossy the lacquer is (low: glossy)" );
ME_REFLECT_END()

ME_REFLECT_BEGIN( HideoutSpeaker )
    ME_FIELD( LowCut ).Unit( Reflection::Unit::Hertz ).Range( 20.f, 2000.f ).Tooltip( "The lowest it plays, standing at it; 20 Hz is all of it" );
    ME_FIELD( HighCut ).Unit( Reflection::Unit::Hertz ).Range( 1000.f, 20000.f ).Tooltip( "The highest it plays, standing at it; 20 kHz is all of it" );
    ME_FIELD( Honk ).Unit( Reflection::Unit::Decibels ).Range( -12.f, 12.f ).Tooltip( "The box's bump in the mids, at HonkAt; 0 for none" );
    ME_FIELD( HonkAt ).Unit( Reflection::Unit::Hertz ).Range( 200.f, 6000.f ).Tooltip( "Where the honk is" );
    ME_FIELD( Width ).Range( 0.f, 1.f ).Tooltip( "Stereo width: 0 one cone (mono), 1 as recorded. Across the room it's this squared" );
    ME_FIELD( Drive ).Range( 0.f, 0.9f ).Tooltip( "How hard the little amp breaks up; 0 clean" );
ME_REFLECT_END()

ME_REFLECT_ENUM( HideoutBandName::When, { { "Unnamed", HideoutBandName::When::Unnamed }, { "Named", HideoutBandName::When::Named } } )

ME_REFLECT_BEGIN( HideoutBandName )
    ME_FIELD( Show ).Tooltip( "Unnamed: shown while the band has no name. Named: shown once it has one (a TextRenderer here shows it)" );
    ME_FIELD( FitLetters ).Range( 1, 64 ).Tooltip( "A longer name shrinks the text to keep it this wide" );
ME_REFLECT_END()

ME_REFLECT_ENUM( HideoutWhen::When, { { "Day", HideoutWhen::When::Day }, { "Night", HideoutWhen::When::Night }, { "MovingIn", HideoutWhen::When::MovingIn }, { "Settled", HideoutWhen::When::Settled } } )

ME_REFLECT_BEGIN( HideoutWhen )
    ME_FIELD( Show ).Tooltip( "Day or Night: by the player's clock. MovingIn: only the first visit after moving into the room. Settled: every visit after" );
ME_REFLECT_END()

ME_REFLECT_ENUM( HideoutReadout::Source, { { "NowPlaying", HideoutReadout::Source::NowPlaying }, { "RecentSong", HideoutReadout::Source::RecentSong }, { "SongsPlayed", HideoutReadout::Source::SongsPlayed }, { "FullCombos", HideoutReadout::Source::FullCombos }, { "GigsPlayed", HideoutReadout::Source::GigsPlayed }, { "LessonsPassed", HideoutReadout::Source::LessonsPassed }, { "Wishlist", HideoutReadout::Source::Wishlist }, { "NextGoal", HideoutReadout::Source::NextGoal }, { "BandName", HideoutReadout::Source::BandName }, { "Clock", HideoutReadout::Source::Clock } } )

ME_REFLECT_BEGIN( HideoutReadout )
    ME_FIELD( Show ).Tooltip( "What the TextRenderer on this entity says: the radio's song, a recent song, a count, a wishlist line, the next goal, the band's name or the time" );
    ME_FIELD( Line ).Range( 0, 64 ).Tooltip( "RecentSong: how many songs back. Wishlist: which item, when Item is empty" );
    ME_FIELD( Item ).Tooltip( "Wishlist: the item's id" );
    ME_FIELD( Prefix ).Tooltip( "Text before the value" );
    ME_FIELD( MaxLetters ).Range( 0, 200 ).Tooltip( "Cut longer text to this many letters; 0 for no limit" );
    ME_FIELD( Upper ).Tooltip( "In capitals" );
    ME_FIELD( Scroll ).Range( 0.f, 2.f ).Tooltip( "NowPlaying: seconds a letter, scrolling a long title through MaxLetters; 0 cuts it instead" );
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


HideoutSpeaker::HideoutSpeaker()
    : Component( "HideoutSpeaker" )
{
}


void HideoutSpeaker::Init()
{
}


HideoutBandName::HideoutBandName()
    : Component( "HideoutBandName" )
{
}


void HideoutBandName::Init()
{
}


HideoutView::HideoutView()
    : Component( "HideoutView" )
{
}


void HideoutView::Init()
{
}


HideoutWhen::HideoutWhen()
    : Component( "HideoutWhen" )
{
}


void HideoutWhen::Init()
{
}


HideoutReadout::HideoutReadout()
    : Component( "HideoutReadout" )
{
}


void HideoutReadout::Init()
{
}
