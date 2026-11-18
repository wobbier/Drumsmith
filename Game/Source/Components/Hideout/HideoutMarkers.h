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
    enum class Kind : int { Kit = 0, PracticePad, Radio, Laptop, TrophyWall, Mixer, GigBoard, Door };

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
// no item names stays.
class HideoutItemSlot
    : public Component<HideoutItemSlot>
{
    ME_REFLECTABLE( HideoutItemSlot )
public:
    HideoutItemSlot();

    virtual void Init() final;

    std::string Slot;
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
class HideoutMotion
    : public Component<HideoutMotion>
{
    ME_REFLECTABLE( HideoutMotion )
public:
    enum class Kind : int { Sway = 0, Flicker, Pulse, Spin, Breathe, Blink, Bob, Pass };

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
};
ME_REGISTER_COMPONENT_FOLDER( HideoutDrummer, "Hideout" )


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
