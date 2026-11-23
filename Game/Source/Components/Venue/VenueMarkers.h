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
    // (1 the usual; out of doors it is already under half that). SkyTime, MoonBrightness and
    // CloudCoverage: out of doors, the night sky's hour (0-24; 20 is dusk), its moon, and how much
    // of it is cloud (0 runs no cloud pass at all).
    Vector3 AmbientColor{ 0.f, 0.f, 0.f };
    Vector3 FogColor{ 0.01f, 0.01f, 0.015f };
    float Haze = 1.f;
    float SkyTime = 22.f;
    float MoonBrightness = 1.f;
    float CloudCoverage = 0.25f;
    // Light the show's haze from the froxel grid instead of the per-pixel march: about 2 ms
    // cheaper at 5120 x 1440 on the Backyard, and suited to broad haze rather than crisp beams.
    bool HazeFroxels = false;
    // Who filmed the show when it plays as a live show (the music video always has the real
    // cameras). Broadcast: the director's crew. Camcorder / Phone: only the guests' own 2000s
    // camcorders or flip phones, from the guest/ camera spots (Docs/Venue-Authoring.md). Mixed:
    // some of each, a device per spot.
    enum class FootageKind : int { Broadcast = 0, Camcorder, Phone, Mixed };
    FootageKind Footage = FootageKind::Broadcast;
    // The whole venue is on the move (a stage on a truck at speed): every camera but an aerial
    // one rattles, heaves and takes the road's bumps, this hard (0 none, 1 a fast highway). It
    // stops once the story flag RideUntil is set (empty: it never stops).
    float Ride = 0.f;
    std::string RideUntil;
    // Colours a look that takes the colour out (black and white, sepia) leaves in, in this venue:
    // how much of the reds and the blues (0 none, 1 all), and how far the reds reach into orange
    // and yellow (0 pure red, 1 fire). Between the story flags LightsFrom and LightsUntil (either
    // may be empty; both empty: never) it keeps all three: police lights and fire.
    float KeepRed = 0.f;
    float KeepBlue = 0.f;
    float KeepWarmth = 0.f;
    std::string LightsFrom;
    std::string LightsUntil;
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


// Moves its entity in time with the song (VenueShow::UpdateBeats): out by Offset on the beat and
// back before the next, like a head nodding or a body dipping; with Sway, smoothly from side to
// side instead. For set dressing that should feel the music: figures baked into a mesh, a lamp
// on a chain. The entity's own position is where it rests.
class VenueBeat : public Component<VenueBeat>
{
    ME_REFLECTABLE( VenueBeat )
public:
    VenueBeat() : Component( "VenueBeat" ) {}
    void Init() final {}
    // Where it is at the peak of the move, from its resting position, in its parent's space.
    Vector3 Offset = Vector3( 0.f, -0.08f, 0.f );
    // One move every this many beats, and how many beats late it starts.
    float Every = 1.f;
    float Phase = 0.f;
    bool Sway = false;
    // Out at once on the beat and straight back, with no gathering before the next: a blip (the
    // trace on a heart monitor), not a nod.
    bool Sharp = false;
};
ME_REGISTER_COMPONENT_FOLDER( VenueBeat, "Venue" )


// Keeps its entity's local +Z on a point in the venue however its parents move
// (VenueShow::UpdateAims): the searchlight slung under a helicopter that hovers and turns, held
// on the stage. Put it on a Spot light, or on the parent of a lamp housing and its light. With
// Wander the aim strays about the point and is pulled back, the way a hand-held light does.
class VenueAim : public Component<VenueAim>
{
    ME_REFLECTABLE( VenueAim )
public:
    VenueAim() : Component( "VenueAim" ) {}
    void Init() final {}
    // The point it is held on, in the venue's space.
    Vector3 Target = Vector3( 0.f, 0.f, 0.f );
    // How far from the point the aim strays, in metres (0: dead on it).
    float Wander = 0.f;
    // Roughly how long one drift across the point takes.
    float Seconds = 3.f;
};
ME_REGISTER_COMPONENT_FOLDER( VenueAim, "Venue" )


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
