#pragma once
#include "CoreGame/TrackList.h"
#include "ECS/EntityHandle.h"
#include "Editor/PadBindings.h"
#include "Math/Vector3.h"
#include <array>
#include <functional>
#include <string>
#include <vector>

class Transform;
class World;
struct VenuePlan;

// The light show on the venue's stage (Docs/Stage-Lighting.md): a rig of real spot lights in
// volumetric haze that plays a chart's VENUE lighting cues on the song clock, falls back to a show
// built from the song's sections or tempo, and pulses with the player's hits. VenueShow owns it;
// the rig is built in venue space (Venue/VenuePlan.h) under the venue's root.
class StageLights
{
public:
    // Spawns a box mesh (the highway's prefab) under a parent, and recolours one.
    using SpawnBoxFn = std::function<EntityHandle( const Vector3& inPosition, const Vector3& inScale, const Vector3& inColor, const Vector3& inEmissive, Transform* inParent )>;
    using TintFn = std::function<void( const EntityHandle& inTarget, const Vector3& inColor, const Vector3& inEmissive )>;

    // inCamera is the venue's camera, whose fog the rig turns into haze while the show runs.
    // inPlan: the stage the rig hangs over (its deck and truss heights) and the members the follow
    // spots light; a member the plan leaves out gets no follow spot.
    void Build( World& inWorld, Transform* inParent, const EntityHandle& inCamera, const TrackData& inTrack, const VenuePlan& inPlan, const SpawnBoxFn& inSpawnBox, const TintFn& inTint );
    void Clear();
    void Update( double inSongTimeMs, float inDeltaTime );

    // The player's judged hits and misses.
    void OnHit( PadId inPad );
    void OnMiss();

    bool IsActive() const { return !m_fixtures.empty(); }
    // The crowd's hype, 0 .. 1 (Venue/Crowd.h), for the blinders.
    void SetCrowdEnergy( float inEnergy ) { m_crowdEnergy = inEnergy; }
    // Holds a follow spot (0 keys, 1 vocals, 2 guitar, 3 drums, 4 bass) at least this bright, for
    // a solo or a big moment the chart's spotlight notes don't cover.
    void SetSpotlightFloor( int inSlot, float inLevel ) { if( inSlot >= 0 && inSlot < 5 ) m_spotFloor[inSlot] = inLevel; }
    // Aims a follow spot at a point (the rig's space) from now on.
    void SetSpotlightTarget( int inSlot, const Vector3& inTarget ) { if( inSlot >= 0 && inSlot < 5 ) { m_spotTargets[inSlot] = inTarget; m_spotTracked[inSlot] = true; } }
    // The washes' colour and level now, for set pieces that glow along with them.
    Vector3 WashGlow() const;
    // Scales the haze (an open-air venue holds less of it).
    void SetHazeScale( float inScale ) { m_hazeScale = inScale; }
    // A soloist (a follow-spot slot, -1 for nobody): the front truss's moving heads swing onto them.
    void SetSoloist( int inSlot ) { m_soloist = inSlot; }
    // The show's hype, 0 calm .. 1 peak: the rig runs hotter and faster, and the lasers come out.
    void SetHype( float inHype ) { m_hype = inHype; }
    // A hit on the whole rig for a big moment: the blinders and strobes flash and the moving heads
    // jump to white, fading over half a second. inStrength 0 .. 1.
    void Accent( float inStrength );
    // The flame pots' burn, 0 .. 1 (Venue/StageFx.h): the rig goes hot orange with them.
    void SetBurn( float inBurn ) { m_burn = inBurn; }
    // A low ceiling (the club): the overhead rig hangs this far below the usual truss height.
    void SetTrussDrop( float inDrop ) { m_trussDrop = inDrop; }

private:
    // Beam: moving heads on the deck. Wash: fixed cans over the band. Spot: follow spots. Crowd:
    // audience blinders. Mover: moving heads under the trusses. Side: cross light from the wings.
    enum class Group { Beam, Wash, Spot, Crowd, Mover, Side };

    struct Fixture
    {
        Group Kind = Group::Beam;
        int Side = 1;          // -1 left of the highway, 1 right
        int Row = 0;           // 0 nearest the strike bar
        int Index = 0;         // within its group
        int Column = 0;        // movers: its place along its truss, from the crowd's left
        float Spread = 0.f;    // movers: the same as -1 (far left) .. 1 (far right)
        EntityHandle Light;    // the light; a moving head's tilting head too
        EntityHandle Yoke;     // moving heads: the fork that pans under the head
        std::vector<EntityHandle> Lenses;   // the visible lamp faces
        float MaxIntensity = 1.f;
        // Shown state, eased toward each frame's look.
        Vector3 Color{ 0.f, 0.f, 0.f };
        float Level = 0.f;
        float Yaw = 0.f;       // beams: degrees around vertical, positive leaning right
        float Pitch = 60.f;    // beams: degrees above horizontal
    };

    // What a fixture should show this frame.
    struct Look
    {
        Vector3 Color{ 0.f, 0.f, 0.f };
        float Level = 0.f;
        float Yaw = 0.f;
        float Pitch = 60.f;
    };

    // The cue in effect at a time, with the time it started and how far its keyframes stepped.
    struct CueState
    {
        std::string Name;
        double Start = 0.0;
        int Keyframe = 0;
    };

    Fixture* SpawnFixture( Group inKind, int inSide, int inRow, int inIndex, const Vector3& inPosition, const Vector3& inAim, float inInner, float inOuter, float inRange, float inIntensity, Transform* inParent, const EntityHandle& inLens );
    // A moving head: a base on its mount (hung under a truss, or standing on the deck), a yoke
    // that pans and a head that tilts with the light in it.
    Fixture* SpawnMovingHead( Group inKind, int inSide, int inRow, int inIndex, const Vector3& inPivot, bool inHung, const Vector3& inAim, float inInner, float inOuter, float inRange, float inIntensity, Transform* inParent, const SpawnBoxFn& inSpawnBox );
    Look MoverLook( const Fixture& inFixture, const CueState& inCue, double inSeconds, double inBeat ) const;
    void UpdateLasers( const CueState& inCue, double inSeconds, double inBeat, float inDeltaTime );
    static Vector3 AimOf( const Fixture& inFixture );
    void BuildFallbackShow( const TrackData& inTrack );
    CueState CueAt( double inSeconds, size_t inBefore ) const;
    void BeatAt( double inSeconds, double& outBeat, int& outMeasureBeat ) const;
    Look LookFor( const Fixture& inFixture, const CueState& inCue, double inSeconds, double inBeat ) const;
    float EaseRate( const std::string& inCue ) const;
    void SetFog( double inSeconds, float inDeltaTime );

    World* m_world = nullptr;
    TintFn m_tint;
    std::vector<Fixture> m_fixtures;
    std::vector<EntityHandle> m_props;
    EntityHandle m_camera;
    Transform* m_root = nullptr;
    // Strobe bars on the trusses (lamp faces only), and the laser fans over the crowd: each a
    // thin bright bar from its projector, hidden (scaled to nothing) while the lasers are off.
    std::vector<EntityHandle> m_strobes;
    struct Laser
    {
        EntityHandle Bar;
        Vector3 Origin;
        int Projector = 0;
        int Ray = 0;
    };
    std::vector<Laser> m_lasers;
    float m_laserLevel = 0.f;
    // The song's colours (three cool, three warm, two clashing), picked by its title.
    Vector3 m_cool[3];
    Vector3 m_warm[3];
    Vector3 m_clash[2];

    // The show: the chart's venue, or one built from its sections / tempo.
    VenueData m_venue;
    std::vector<BeatData> m_beats;
    float m_bpm = 120.f;
    bool m_gentle = false;     // StageLighting 1: no strobes or flashes

    // Player-driven pulses, 1 at a hit and decaying.
    float m_kickPulse = 0.f;
    float m_snarePulse = 0.f;
    float m_crashFlash = 0.f;
    std::array<float, 2> m_tomPulse{ 0.f, 0.f };
    float m_missDip = 0.f;
    float m_crowdEnergy = 0.5f;
    float m_hazeScale = 1.f;
    int m_soloist = -1;
    float m_hype = 0.f;
    float m_accent = 0.f;
    float m_burn = 0.f;
    float m_trussDrop = 0.f;
    std::array<float, 5> m_spotFloor{};
    std::array<Vector3, 5> m_spotTargets{};
    std::array<bool, 5> m_spotTracked{};

    // The camera's fog before the show changed it, restored by Clear.
    bool m_savedFog = false;
    bool m_fogWasVolumetric = false;
    float m_fogDensity = 0.f;
    float m_fogStart = 0.f;
    float m_fogScatter = 0.f;
    int m_fogSteps = 0;
    float m_fogDistance = 0.f;
    int m_fogLightSamples = 0;
    float m_hazeLevel = 0.f;
};
