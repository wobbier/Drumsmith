#pragma once
#include "ECS/Component.h"
#include "ECS/ComponentDetail.h"
#include "Math/Vector3.h"
#include <string>

// Markers a venue author places in a Havana scene (.lvl) to say where the game puts things. They
// are plain data: nothing here moves, spawns or draws anything; the venue loader reads them.
//
// Venue space: metres, +x is the crowd's right, +y is up, +z runs from the crowd toward the band
// and the back wall. The crowd faces +z and the band faces -z (back at the crowd). Each marker's
// position, rotation and scale come from the entity's Transform; the facing of each marker is
// stated on its own class.


// One per venue scene: names the venue and describes the room the director and lights work in. The
// room numbers mirror Director::Room. The Build toggles default off because a scene venue brings
// its own geometry; switching one on also adds the built-in version of that piece.
class VenueInfo
    : public Component<VenueInfo>
{
    ME_REFLECTABLE( VenueInfo )
public:
    VenueInfo();

    virtual void Init() final;

    std::string Name;
    std::string Author;
    bool Outdoor = false;
    // Metres, venue space. RoomBack and RoomCeiling are the back wall's z and the ceiling's y (the
    // defaults are far enough away to mean "no wall" / "no ceiling").
    float RoomBack = -1000.f;
    float RoomCeiling = 1000.f;
    float RoomHalfWidth = 30.f;
    // The sound desk's z, where the crowd's far edge and the Desk camera sit.
    float DeskZ = -22.f;
    bool BuildStage = false;    // Also add the built-in stage deck
    bool BuildSet = false;      // Also add the built-in set dressing
    bool BuildRig = false;      // Also add the built-in light rig
    bool BuildFx = false;       // Also add the built-in effects
    // The room's look, all optional. AmbientColor: indoors, the colour the camera clears to,
    // which also lights the whole room a little (black leaves a faint grey base). FogColor: the
    // light the haze scatters, which lifts whatever is far off. Haze: how thick the haze hangs
    // (1 the usual; out of doors it is already under half that). SkyTime and MoonBrightness: out
    // of doors, the night sky's hour (0-24; 20 is dusk) and its moon.
    Vector3 AmbientColor{ 0.f, 0.f, 0.f };
    Vector3 FogColor{ 0.01f, 0.01f, 0.015f };
    float Haze = 1.f;
    float SkyTime = 22.f;
    float MoonBrightness = 1.f;
};
ME_REGISTER_COMPONENT_FOLDER( VenueInfo, "Venue" )


// Where one band member stands. The entity's position is the performer's feet. The performer
// faces the entity's local -Z, so a spot with identity rotation faces the crowd; a fresh entity
// placed in Havana is already facing the right way. Yaw it to turn the performer.
class VenueSpot
    : public Component<VenueSpot>
{
    ME_REFLECTABLE( VenueSpot )
public:
    // Same order as VenueData::Member.
    enum class Role : int { Drummer = 0, Guitar, Bass, Vocals, Keys };

    VenueSpot();

    virtual void Init() final;

    Role Member = Role::Drummer;
};
ME_REGISTER_COMPONENT_FOLDER( VenueSpot, "Venue" )


// A floor rectangle the crowd fills. Position is the centre of the rectangle, scale x and z are
// its full width and depth in metres (scale y is ignored), and the crowd faces the entity's local
// +Z, so identity rotation faces the band. Yaw it for a crowd that looks somewhere else.
class VenueCrowdArea
    : public Component<VenueCrowdArea>
{
    ME_REFLECTABLE( VenueCrowdArea )
public:
    VenueCrowdArea();

    virtual void Init() final;

    // Who stands here. Mob: the cheap instanced figures that bob, jump and put their hands up, for
    // the back of a crowd. Posed: the full figures of the built-in rooms' front rows, each with its
    // own moves, cheers, phones and lighters, and the crowd surfer (from the first posed area);
    // they cost more, so keep them to the people near the stage.
    enum class Kind : int { Mob = 0, Posed };
    Kind Figures = Kind::Mob;
    bool DanceFloor = false;
    // How many people stand in the rectangle at a full house.
    int HeadCount = 60;
    // Spread of each person from their grid position, as a fraction of the grid spacing (0 is a
    // neat grid, 1 is a loose mob). Mob only: posed rows have their own looseness.
    float Jitter = 0.5f;
};
ME_REGISTER_COMPONENT_FOLDER( VenueCrowdArea, "Venue" )

class VenueAccent : public Component<VenueAccent>
{
    ME_REFLECTABLE( VenueAccent )
public:
    VenueAccent() : Component( "VenueAccent" ) {}
    void Init() final {}
    float Beats = 12.f;
    int Particles = 0;
    bool FullLightingOnly = false;
};
ME_REGISTER_COMPONENT_FOLDER( VenueAccent, "Venue" )


// A camera position the director can cut to. Position is the eye and the camera looks along the
// entity's local +Z (the engine's forward axis, same as Camera and Light), so rotate it toward the
// target as you would any camera.
// Story mode (Docs/Venue-Authoring.md -> Story props): shows this entity and its children only
// while a story flag is set, or with WhenSet off only until it is. A set's songs set the flags:
// the songs before the one playing from its start, the song's own at its cue. Hidden by scale (the
// pivot is where it grows from) and by dimming the Lights under it.
//
// Mode Play leaves it shown and plays the Sequences on it and under it once when the flag lands
// (a flag set before the song starts them at their end): the trailer slewing, a figure walking
// down the stairs. Mode SlowMotion runs those Sequences at Speed until the flag lands, then at
// full speed (the rescue in slow motion until the band wakes).
class VenueStory : public Component<VenueStory>
{
    ME_REFLECTABLE( VenueStory )
public:
    enum class Motion : int { Show = 0, Play, SlowMotion };

    VenueStory() : Component( "VenueStory" ) {}
    void Init() final {}
    std::string Flag;
    bool WhenSet = true;
    float FadeSeconds = 0.75f;
    Motion Mode = Motion::Show;
    float Speed = 0.3f;
};
ME_REGISTER_COMPONENT_FOLDER( VenueStory, "Venue" )


class VenueCameraSpot
    : public Component<VenueCameraSpot>
{
    ME_REFLECTABLE( VenueCameraSpot )
public:
    enum class Kind : int { Wide = 0, Desk, Crane, Close, Custom };

    VenueCameraSpot();

    virtual void Init() final;

    Kind Shot = Kind::Wide;
    // Degrees, vertical.
    float FieldOfView = 55.f;
    // Free text to tell Custom shots apart.
    std::string Tag;
};
ME_REGISTER_COMPONENT_FOLDER( VenueCameraSpot, "Venue" )


// A screen that shows a feed. The entity's Transform is the quad: scale x and y are its width and
// height in metres. The picture faces the entity's local -Z, the same way a VenueSpot faces, so a
// screen behind the band with identity rotation already faces the crowd.
class VenueScreen
    : public Component<VenueScreen>
{
    ME_REFLECTABLE( VenueScreen )
public:
    enum class Feed : int { Stage = 0, Program, Lyrics };

    VenueScreen();

    virtual void Init() final;

    Feed Source = Feed::Stage;
    // HDR multiplier on the picture's emitted light.
    float Emissive = 2.f;
};
ME_REGISTER_COMPONENT_FOLDER( VenueScreen, "Venue" )


// Tags a light so the show can cue it. Put it on an entity that also has a Light component; the
// light's own type, colour and cone still come from that Light.
class VenueShowLight
    : public Component<VenueShowLight>
{
    ME_REFLECTABLE( VenueShowLight )
public:
    enum class Role : int { Wash = 0, Beam, Spot, Blinder, Strobe, Static };

    VenueShowLight();

    virtual void Init() final;

    Role Kind = Role::Wash;
    // Lights in the same group are cued together; 0 is the default group.
    int Group = 0;
};
ME_REGISTER_COMPONENT_FOLDER( VenueShowLight, "Venue" )
