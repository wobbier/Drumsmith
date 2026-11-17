#pragma once
#include "CoreGame/TrackList.h"
#include "ECS/EntityHandle.h"
#include "Math/Vector3.h"
#include <vector>

class Transform;
class VenueKit;
struct VenuePlan;

// The show's special effects (Docs/Venue-and-Band.md): flame pots, spark fountains, CO2 jets,
// confetti cannons, dry ice rolling over the deck, dust drifting through the beams and, out of
// doors, fireworks. All of it is the engine's particle systems (Engine/Docs/Rendering-Pipeline.md),
// plus a point light per flame pot. The chart's bonus effects fire the flames on the song clock;
// everything else is fired by VenueShow when the show enters a hype phase.
class StageFx
{
public:
    // inPlan: the stage the effects stand on and hang over, and its Style (VenueShow::Style as an
    // int: fireworks only out of doors, less confetti in a club).
    void Build( VenueKit& inKit, Transform& inRoot, const VenuePlan& inPlan, const VenueData& inVenue );
    // Forgets the emitters (the kit deletes them).
    void Clear();
    // inGentle: Stage Lights set to no flashes (flames soften). inLowFog: 0 .. 1 of dry ice.
    void Update( double inSeconds, float inDeltaTime, bool inGentle, float inLowFog );

    // A flame burst from every pot, as the chart's bonus effects fire.
    void Flames();
    // The CO2 jets along the stage's front, for this long.
    void Jets( float inSeconds );
    // The spark fountains, for this long.
    void Sparks( float inSeconds );
    // The confetti cannons: 1 is a full salvo.
    void Confetti( float inAmount );
    // A volley of fireworks behind the stage (out of doors only; nothing in a room).
    void Fireworks( int inShells );

    // How hard the flames are burning now, 0 .. 1 (the rig and the camera react).
    float Burn() const { return m_burn; }
    // True on the frame a flame burst starts.
    bool Ignited() const { return m_ignited; }

private:
    struct Pot
    {
        EntityHandle Flame;     // the hot core: a thin bright column
        EntityHandle Fire;      // flame particles
        EntityHandle Embers;
        EntityHandle Light;
        Vector3 Base;
    };

    struct Shell
    {
        EntityHandle Burst;
        float At = -1.f;        // seconds until it bursts (< 0: idle)
    };

    EntityHandle Emitter( VenueKit& inKit, Transform& inRoot, const char* inName, const Vector3& inPosition, const Vector3& inDirection );

    std::vector<Pot> m_pots;
    std::vector<EntityHandle> m_jets;
    std::vector<EntityHandle> m_sparks;
    std::vector<EntityHandle> m_confetti;
    std::vector<Shell> m_shells;
    EntityHandle m_lowFog;
    EntityHandle m_dust;
    std::vector<float> m_bonusFx;
    // Flame bursts fired by hand (Flames), on the song clock like the chart's.
    std::vector<float> m_fired;
    bool m_fireRequested = false;
    float m_jetTime = 0.f;
    float m_sparkTime = 0.f;
    float m_burn = 0.f;
    float m_lastBurn = 0.f;
    bool m_ignited = false;
    int m_style = 0;
    uint32_t m_volley = 0;
};
