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
// looks grade the image (charts without any get the concert look in their quiet sections). The LED wall behind the stage shows the program feed, the main camera's
// shot as it's being filmed; the side screens a close-up of whoever the main shot is on, else
// whoever's carrying the song.
class Director
{
public:
    // inMusicVideo: play MV VENUE's cuts and looks when the chart has them.
    void Build( World& inWorld, const VenueData& inVenue, const std::vector<BeatData>& inBeats, float inBpm, float inSongLength, bool inMusicVideo, const Band* inBand );
    void Clear();
    void Update( double inSeconds, float inDeltaTime );
    // A crowd surfer going up cuts to them: a handheld camera in the photo pit follows them over
    // the crowd's heads until they reach the barricade, then cuts back to the scheduled shot.
    // Called each frame before Update (inPosition in venue space).
    void FollowSurfer( bool inUp, const Vector3& inPosition );

    const EntityHandle& MainCamera() const { return m_main; }
    // The back of the room (venue z): wide shots stay in front of it.
    void SetRoomBack( float inZ ) { m_roomBack = inZ; }
    const EntityHandle& FeedCamera() const { return m_feed; }
    const EntityHandle& ProgramCamera() const { return m_program; }
    // The shot the main camera holds now ("coop_g_near"), for logs and tests.
    const std::string& CurrentShot() const { return m_shotName; }
    const std::string& CurrentLook() const { return m_lookName; }
    // The frame rate the look live at inSeconds steps the venue at (0: smooth). VenueShow holds
    // the venue between steps, like a camera feed running at a low frame rate.
    float FrameRateAt( double inSeconds ) const;
    // The venue's step while stepping (-1 when not): the film grain holds still between steps.
    void SetGrainFrame( int inFrame );
    size_t CutCount() const { return m_cuts.size(); }

    // The side screens' close-ups, and the LED wall's program feed (what the main camera shows).
    static constexpr const char* kFeedTexture = "Assets/Textures/Venue/StageFeed.rendertexture";
    static constexpr const char* kProgramTexture = "Assets/Textures/Venue/StageProgram.rendertexture";
    // The concert look's toning: black and white split to rose mids and cream highlights.
    static constexpr const char* kConcertLut = "Assets/Textures/LUTs/ConcertScreen.cube";
    // The look charts' black-and-white looks map to, and quiet sections get when a chart has none.
    static constexpr const char* kConcertLook = "concert_bw";

private:
    // Neck: mounted on the subject's headstock, looking down the frets (guitar solos).
    // Surfer: from the photo pit, following the crowd surfer (FollowSurfer).
    enum class Framing { Far, Near, Behind, CloseHead, CloseHand, Kick, Crowd, Overhead, Wall, Neck, Surfer };

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
        float Lut = 0.f;          // the concert LUT's contribution
        float Grain = 0.f;        // film grain
        float FrameRate = 0.f;    // venue steps a second (0: smooth); not eased
    };

    Plan PlanFor( const std::string& inName, int inIndex ) const;
    Plan PlanAuto( const std::string& inConstraints, int inIndex, float inTime ) const;
    void BuildFallbackCuts( const VenueData& inVenue, float inSongLength );
    // Charts without looks: the concert look through intros, bridges, breakdowns and quiet parts.
    void BuildFallbackLooks( const VenueData& inVenue );
    void AddNeckShots( const VenueData& inVenue );
    // outUp is world up, except for the neck camera, which rolls with the guitar.
    void Frame( const Plan& inPlan, float inHeld, Vector3& outEye, Vector3& outTarget, float& outFov, Vector3* outUp = nullptr ) const;
    Vector3 SubjectPoint( const Plan& inPlan, bool inHead ) const;
    // Lead room: a one-member shot is turned so its subject stands off to one side, clear of the
    // highway drawn up the middle of the screen, looking across the frame (0: the shot has none).
    float LeadSideFor( const Plan& inPlan, const Vector3& inEye, const Vector3& inTarget ) const;
    static Vector3 LeadRoom( const Vector3& inEye, const Vector3& inTarget, float inSide, float inFov, float inAspect );
    static Grade GradeFor( const std::string& inLook );
    void ApplyGrade( float inDeltaTime );
    void UpdateFeed( double inSeconds, float inDeltaTime, int inCutIndex );

    World* m_world = nullptr;
    const Band* m_band = nullptr;
    EntityHandle m_main;
    EntityHandle m_feed;
    EntityHandle m_program;
    std::vector<Cut> m_cuts;
    std::vector<TimedCueData> m_looks;
    std::vector<BeatData> m_beats;
    float m_bpm = 120.f;
    float m_roomBack = -1000.f;
    std::string m_shotName;
    std::string m_lookName;
    Grade m_grade;
    Grade m_gradeTarget;
    // FrameRateAt's last answer, by look cue (it's asked every frame).
    mutable int m_rateCue = -2;
    mutable float m_rate = 0.f;
    // The feed's own shot, changed every couple of bars.
    int m_feedSubject = 3;
    int m_feedVariant = 0;
    double m_feedSince = -100.0;
    Vector3 m_feedEye;
    Vector3 m_feedTarget;
    // The main camera as framed, eased toward each frame's framing so it follows the members
    // like an operator would, rather than every bob and headbang; snapped on a cut.
    Vector3 m_eye;
    Vector3 m_target;
    Vector3 m_up = Vector3::Up;     // rolled only by the neck camera
    float m_fov = 45.f;
    int m_framedCut = -2;
    std::string m_framedShot;
    float m_leadSide = 0.f;    // this shot's lead room (LeadSideFor), chosen on the cut
    // The crowd surfer being followed (FollowSurfer); the pit camera's side is chosen as they go up.
    bool m_surferUp = false;
    Vector3 m_surferPosition;
    float m_surferSide = 1.f;
};
