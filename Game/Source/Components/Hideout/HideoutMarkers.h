#pragma once
#include "ECS/Component.h"
#include "ECS/ComponentDetail.h"
#include "Math/Vector3.h"
#include <string>

// Markers placed in a hideout room scene (Assets/Hideout/*.lvl; Docs/Hideout-and-Progression.md),
// read by the main menu's Hideout. Plain data, like the venue markers.


// Something in the room the player can go to: the kit plays a song, the practice pad opens the
// lessons and so on. The entity's position is what the camera looks at; ViewOffset is where the
// camera stands, relative to it, when the station is chosen.
class HideoutStation
    : public Component<HideoutStation>
{
    ME_REFLECTABLE( HideoutStation )
public:
    enum class Kind : int { Kit = 0, PracticePad, Radio, Laptop, TrophyWall, Mixer, GigBoard, Door, Wishlist };

    HideoutStation();

    virtual void Init() final;

    Kind Station = Kind::Kit;
    // The label over it; empty uses the station's usual name.
    std::string Label;
    Vector3 ViewOffset{ 0.f, 0.6f, -1.6f };
    float FieldOfView = 45.f;
};
ME_REGISTER_COMPONENT_FOLDER( HideoutStation, "Hideout" )


// Where an unlockable item stands (CoreGame/Progression.h: an item's Slot). The entity and its
// children are the item: they are taken out of the room until the item is unlocked. A slot that
// no item names stays. WhenLocked turns it around: a stand-in for the item (an outline in tape on
// the bench, a note saying what goes there) shown only until the item is unlocked.
class HideoutItemSlot
    : public Component<HideoutItemSlot>
{
    ME_REFLECTABLE( HideoutItemSlot )
public:
    HideoutItemSlot();

    virtual void Init() final;

    std::string Slot;
    bool WhenLocked = false;
};
ME_REGISTER_COMPONENT_FOLDER( HideoutItemSlot, "Hideout" )


// Life for a prop (Hideout::UpdateMotions): the entity's local rotation, scale or Light is moved
// every frame around how the scene left it. Most kinds can follow the radio instead of a clock
// (Music): the beat of the song it's playing (from the chart's beat grid) and how loud it is.
//   Sway     swings Amount degrees about Axis, Speed swings a second (a hanging bulb: put the
//            entity at the hook and the bulb below it). With Music, it nods on each beat instead.
//   Flicker  the Light dips at random by up to Amount (0..1); Speed is how restless it is. A
//            fluorescent tube: Amount 1 drops out completely now and then.
//   Pulse    the Light (or, without one, the scale) jumps by Amount on each beat and decays; with
//            no music, a slow glow at Speed.
//   Spin     turns about Axis at Speed degrees a second (a record, a fan).
//   Breathe  scales by Amount along Axis, Speed breaths a second (a sleeping cat).
//   Blink    the Light (or the scale, to nothing) on for Amount of every 1 / Speed seconds.
//   Bob      moves Amount metres along Axis on each beat (a speaker cone, a dancing toy), or
//            Speed bobs a second without music.
//   Pass     every 1 / Speed seconds (Phase: how far into that wait it starts), sweeps Amount
//            metres either way along Axis in 2.5 s while its Light swells and fades: a car's
//            headlights going past the window.
//   Hour, Minute, Second  a clock's hands: turned about Axis to the player's own clock (a full
//            turn is 12 hours, an hour, a minute). Put the entity at the clock's middle.
class HideoutMotion
    : public Component<HideoutMotion>
{
    ME_REFLECTABLE( HideoutMotion )
public:
    enum class Kind : int { Sway = 0, Flicker, Pulse, Spin, Breathe, Blink, Bob, Pass, Hour, Minute, Second };

    HideoutMotion();

    virtual void Init() final;

    Kind Motion = Kind::Sway;
    float Amount = 1.f;
    float Speed = 1.f;
    Vector3 Axis{ 0.f, 0.f, 1.f };
    // 0..1: where in its cycle it starts, so a row of the same thing doesn't move as one.
    float Phase = 0.f;
    bool Music = false;
};
ME_REGISTER_COMPONENT_FOLDER( HideoutMotion, "Hideout" )


// Where the player's drummer sits (the throne's position; the kit is built in front of them, the
// way Yaw faces: 180 faces -z). The drummer plays along with whatever the radio is playing, from that
// song's chart (Band), and sits idle at the kit between songs.
class HideoutDrummer
    : public Component<HideoutDrummer>
{
    ME_REFLECTABLE( HideoutDrummer )
public:
    HideoutDrummer();

    virtual void Init() final;

    // Which character plays (Band::CastSeed): the same one whatever the song.
    int Cast = 0;
    // Degrees about +y (Band: 180 faces -z). A field rather than the entity's rotation, which
    // comes back from its quaternion as whichever Euler angles it likes.
    float Yaw = 180.f;
    // How hard they go at it, 0 to 1 (Band::Update's energy).
    float Energy = 0.55f;
    // The kit gets better with the room: the drum shells' lacquer (the kick, snare and toms),
    // its metallic and roughness. All zero keeps the kit's own oxblood.
    Vector3 Finish{ 0.f, 0.f, 0.f };
    float FinishMetallic = 0.f;
    float FinishRoughness = 0.4f;
};
ME_REGISTER_COMPONENT_FOLDER( HideoutDrummer, "Hideout" )


// Part of the band's name in the room (the bedsheet, the kick head): shown only while the band has
// no name (Unnamed: the "BAND NAME TBD" pictures) or only once it has one (Named: a blank sheet,
// and a TextRenderer, whose Text becomes the name). PlayerProfile::BandName.
class HideoutBandName
    : public Component<HideoutBandName>
{
    ME_REFLECTABLE( HideoutBandName )
public:
    enum class When : int { Unnamed = 0, Named };

    HideoutBandName();

    virtual void Init() final;

    When Show = When::Named;
    // A TextRenderer's size is cut down so a name this many letters long (or longer) still fits.
    int FitLetters = 9;
};
ME_REGISTER_COMPONENT_FOLDER( HideoutBandName, "Hideout" )


// The room's overview: where the camera stands when no station is chosen. It looks along the
// entity's local +Z. One per room.
class HideoutView
    : public Component<HideoutView>
{
    ME_REFLECTABLE( HideoutView )
public:
    HideoutView();

    virtual void Init() final;

    float FieldOfView = 55.f;
    // The first time the menu opens in a session, the camera starts here (looking at IntroTarget)
    // and comes to the overview: down the stairs, into the room. Off when IntroEye is all zero.
    Vector3 IntroEye{ 0.f, 0.f, 0.f };
    Vector3 IntroTarget{ 0.f, 0.f, 0.f };
};
ME_REGISTER_COMPONENT_FOLDER( HideoutView, "Hideout" )


// Part of the room that is only there sometimes. Day and Night follow the player's clock (day is
// 7:00 to 19:00; the hideout debug menu and --hideout-time day|night override it): the sun through
// the window by day, the streetlight by night. MovingIn is the first visit after moving into the
// room (boxes not unpacked yet), Settled every visit after.
class HideoutWhen
    : public Component<HideoutWhen>
{
    ME_REFLECTABLE( HideoutWhen )
public:
    enum class When : int { Day = 0, Night, MovingIn, Settled };

    HideoutWhen();

    virtual void Init() final;

    When Show = When::Night;
};
ME_REGISTER_COMPONENT_FOLDER( HideoutWhen, "Hideout" )


// Words in the room that come from the player (a TextRenderer on the same entity; Hideout keeps
// its Text up to date): the song on the radio's display, the songs on the setlist taped to the
// floor, the wishlist on the wall with what's been ticked off.
//   NowPlaying   the radio's song: "TITLE - ARTIST"
//   RecentSong   the Line-th song played most recently (0 the latest), else what the radio played
//   SongsPlayed, FullCombos, GigsPlayed, LessonsPassed   a count
//   Wishlist     the item named by Item (or the Line-th unlockable one): "[x] Practice pad" once
//                it's in, "[ ] ..." before
//   NextGoal     what to do next, as the header says it
//   BandName     the band's name, or "BAND NAME TBD"
//   Clock        the time, "21:47"
class HideoutReadout
    : public Component<HideoutReadout>
{
    ME_REFLECTABLE( HideoutReadout )
public:
    enum class Source : int { NowPlaying = 0, RecentSong, SongsPlayed, FullCombos, GigsPlayed, LessonsPassed, Wishlist, NextGoal, BandName, Clock };

    HideoutReadout();

    virtual void Init() final;

    Source Show = Source::NowPlaying;
    int Line = 0;
    // Wishlist: the item's id (Assets/Progression/Progression.json).
    std::string Item;
    // Put before the value ("SONGS: ").
    std::string Prefix;
    // Longer text is cut to this many letters (with "..."), 0 for no limit.
    int MaxLetters = 0;
    bool Upper = false;
    // NowPlaying: scrolls through a longer title instead of cutting it, a letter every this many seconds.
    float Scroll = 0.f;
};
ME_REGISTER_COMPONENT_FOLDER( HideoutReadout, "Hideout" )
