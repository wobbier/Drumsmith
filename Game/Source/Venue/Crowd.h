#pragma once
#include "CoreGame/TrackList.h"
#include "Venue/Puppet.h"
#include "Venue/VenueLayout.h"
#include "ECS/EntityHandle.h"
#include <string>
#include <vector>

class Transform;
class VenueKit;

// The audience (Docs/Venue-and-Band.md): a few hundred five-piece figures on the floor in front
// of the stage. They follow the chart's crowd states ("[crowd_intense]", "[crowd_normal]",
// "[crowd_mellow]", "[crowd_realtime]") and claps ("[crowd_clap]" / "[crowd_noclap]") on the
// song's beat: idle swaying, bobbing and fist pumps, jumping with their hands up, lighters and
// phones in the air for the slow parts. "realtime" follows the player instead: a long streak
// gets them jumping, misses take the wind out of them. Pyro sets everyone off.
class Crowd
{
public:
    // inBackZ / inHalfWidth: how far back and wide the floor fills (VenueLayout's by default).
    void Build( VenueKit& inKit, Transform* inFloor, const VenueData& inVenue, const std::vector<BeatData>& inBeats, float inBpm, int inCount,
        float inBackZ = VenueLayout::kCrowdBackZ, float inHalfWidth = VenueLayout::kCrowdHalfWidth );
    void Clear();
    // inPerformance: 0 (the player's struggling) .. 1 (on a long streak).
    void Update( double inSeconds, float inDeltaTime, float inPerformance );

    void OnMiss();
    void OnCheer( float inAmount );
    // A crowd surfer passes overhead toward the stage while this is on (the chart's crowd-surf and
    // stage-dive shots, or now and then when it's intense); the people under them hold them up.
    void SetSurfing( bool inSurfing ) { m_surfRequested = inSurfing; }

    // 0 .. 1: how hyped the crowd is now (the lights and band use it).
    float Energy() const { return m_energy; }
    std::string Mood( double inSeconds ) const;
    bool Clapping( double inSeconds ) const;
    size_t Size() const { return m_people.size(); }

private:
    struct Person
    {
        Puppet Body;
        Puppet::Pose Pose;
        float Phase = 0.f;         // seconds of lag behind the beat, and idle offsets
        float Enthusiasm = 0.5f;
        int Kind = 0;              // 0 jumper, 1 pumper, 2 swayer, 3 clapper
        int Item = 0;              // 0 nothing, 1 lighter, 2 phone
        EntityHandle ItemPiece;
        float Depth = 0.f;         // metres back from the barricade
    };

    void BuildFallbackMoods();

    std::vector<Person> m_people;
    std::vector<TimedCueData> m_moods;
    std::vector<TimedCueData> m_claps;
    std::vector<float> m_bonusFx;
    std::vector<BeatData> m_beats;
    std::vector<TimedCueData> m_sections;
    float m_bpm = 120.f;
    float m_energy = 0.5f;
    float m_missDip = 0.f;
    float m_cheer = 0.f;
    uint32_t m_frame = 0;

    // The crowd surfer: a figure carried over the heads from the back toward the barricade.
    Puppet m_surfer;
    bool m_surfRequested = false;
    float m_surfProgress = -1.f;   // < 0: nobody up
    float m_surfX = 0.f;
    Vector3 m_surfPosition;
    int m_surfCount = 0;
};
