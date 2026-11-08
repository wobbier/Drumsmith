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

// The light show beside the note highway (Docs/Stage-Lighting.md): a rig of real spot lights in
// volumetric haze that plays a chart's VENUE lighting cues on the song clock, falls back to a show
// built from the song's sections or tempo, and pulses with the player's hits. NoteHighwayCore owns
// it; the rig rides with the camera like the highway.
class StageLights
{
public:
    // Spawns a box mesh (the highway's prefab) under a parent, and recolours one.
    using SpawnBoxFn = std::function<EntityHandle( const Vector3& inPosition, const Vector3& inScale, const Vector3& inColor, const Vector3& inEmissive, Transform* inParent )>;
    using TintFn = std::function<void( const EntityHandle& inTarget, const Vector3& inColor, const Vector3& inEmissive )>;

    // inCamera is the highway camera, whose fog the rig turns into haze while the show runs.
    void Build( World& inWorld, Transform* inParent, const EntityHandle& inCamera, const TrackData& inTrack, const SpawnBoxFn& inSpawnBox, const TintFn& inTint );
    void Clear();
    void Update( double inSongTimeMs, float inDeltaTime );

    // The player's judged hits and misses.
    void OnHit( PadId inPad );
    void OnMiss();

    bool IsActive() const { return !m_fixtures.empty(); }

private:
    enum class Group { Beam, Wash, Spot };

    struct Fixture
    {
        Group Kind = Group::Beam;
        int Side = 1;          // -1 left of the highway, 1 right
        int Row = 0;           // 0 nearest the strike bar
        int Index = 0;         // within its group
        EntityHandle Light;
        EntityHandle Lens;     // the visible lamp face, if the fixture is on screen
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

    void SpawnFixture( Group inKind, int inSide, int inRow, int inIndex, const Vector3& inPosition, const Vector3& inAim, float inInner, float inOuter, float inRange, float inIntensity, Transform* inParent, const EntityHandle& inLens );
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

    // The camera's fog before the show changed it, restored by Clear.
    bool m_savedFog = false;
    bool m_fogWasVolumetric = false;
    float m_fogDensity = 0.f;
    float m_fogStart = 0.f;
    float m_fogScatter = 0.f;
    int m_fogSteps = 0;
    float m_fogDistance = 0.f;
    float m_hazeLevel = 0.f;
};
