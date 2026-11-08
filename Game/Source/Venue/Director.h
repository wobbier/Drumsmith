#pragma once
#include "CoreGame/TrackList.h"
#include "ECS/EntityHandle.h"
#include "Math/Vector3.h"
#include <string>
#include <vector>

class Band;
class World;

// The venue's camera crew (Docs/Venue-and-Band.md). The main camera cuts between shots on the
// chart's camera cuts: Rock Band 3's "[coop_x]" and "[directed_x]" shots, RB2's note cuts with
// their constraints, or, for charts without any, cuts every couple of measures to whoever is
// busiest. Each shot drifts while it's held; handheld ones shake. The chart's post-processing
// looks grade the image. A second camera films the band for the LED wall behind the stage: a
// close-up of whoever the main shot is on, else whoever's carrying the song.
class Director
{
public:
    // inMusicVideo: play MV VENUE's cuts and looks when the chart has them.
    void Build( World& inWorld, const VenueData& inVenue, const std::vector<BeatData>& inBeats, float inBpm, float inSongLength, bool inMusicVideo, const Band* inBand );
    void Clear();
    void Update( double inSeconds, float inDeltaTime );

    const EntityHandle& MainCamera() const { return m_main; }
    const EntityHandle& FeedCamera() const { return m_feed; }
    // The shot the main camera holds now ("coop_g_near"), for logs and tests.
    const std::string& CurrentShot() const { return m_shotName; }
    const std::string& CurrentLook() const { return m_lookName; }
    size_t CutCount() const { return m_cuts.size(); }

    static constexpr const char* kFeedTexture = "Assets/Textures/Venue/StageFeed.rendertexture";

private:
    enum class Framing { Far, Near, Behind, CloseHead, CloseHand, Kick, Crowd, Overhead, Wall };

    struct Plan
    {
        std::vector<int> Subjects;     // members; empty is the whole band
        Framing Frame = Framing::Far;
        bool Handheld = false;
        bool Static = false;
        int Variant = 0;
    };

    struct Cut
    {
        float Time = 0.f;
        std::string Name;
        Plan Shot;
    };

    // A graded look (one per post-processing name).
    struct Grade
    {
        float Saturation = 1.f;
        float Contrast = 1.f;
        float Temperature = 0.f;
        float Tint = 0.f;
        float Bloom = 1.f;
        float Vignette = 0.35f;
        float Exposure = 0.f;
        int ColorBits = 0;
        float Dither = 0.f;
    };

    Plan PlanFor( const std::string& inName, int inIndex ) const;
    Plan PlanAuto( const std::string& inConstraints, int inIndex, float inTime ) const;
    void BuildFallbackCuts( const VenueData& inVenue, float inSongLength );
    void Frame( const Plan& inPlan, float inHeld, double inSeconds, Vector3& outEye, Vector3& outTarget, float& outFov ) const;
    Vector3 SubjectPoint( const Plan& inPlan, bool inHead ) const;
    static Grade GradeFor( const std::string& inLook );
    void ApplyGrade( float inDeltaTime );
    void UpdateFeed( double inSeconds, int inCutIndex );

    World* m_world = nullptr;
    const Band* m_band = nullptr;
    EntityHandle m_main;
    EntityHandle m_feed;
    std::vector<Cut> m_cuts;
    std::vector<TimedCueData> m_looks;
    std::vector<BeatData> m_beats;
    float m_bpm = 120.f;
    std::string m_shotName;
    std::string m_lookName;
    Grade m_grade;
    Grade m_gradeTarget;
    // The feed's own shot, changed every couple of bars.
    int m_feedSubject = 3;
    int m_feedVariant = 0;
    double m_feedSince = -100.0;
    Vector3 m_feedEye;
    Vector3 m_feedTarget;
};
