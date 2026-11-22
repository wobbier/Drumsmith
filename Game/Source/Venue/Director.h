#pragma once
#include "CoreGame/TrackList.h"
#include "Venue/VenuePlan.h"
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
    // inMusicVideo: play MV VENUE's cuts and looks when the chart has them. inPlan: where the
    // members stand (the shots of them follow their spots; a member the plan leaves out is never
    // a shot's subject), the barricade and the crowd's front, the back wall.
    void Build( World& inWorld, const VenuePlan& inPlan, const VenueData& inVenue, const std::vector<BeatData>& inBeats, float inBpm, float inSongLength, bool inMusicVideo, const Band* inBand );
    void Clear();
    void Update( double inSeconds, float inDeltaTime );
    // A crowd surfer going up cuts to them: a handheld camera in the photo pit follows them over
    // the crowd's heads until they reach the barricade, then cuts back to the scheduled shot.
    // Called each frame before Update (inPosition in venue space).
    void FollowSurfer( bool inUp, const Vector3& inPosition );

    const EntityHandle& MainCamera() const { return m_main; }
    // The room the cameras work in (venue space): every shot stays inside it. Back is the back
    // wall's z, Ceiling the lowest thing overhead (the rigging grid), HalfWidth the side walls,
    // DeskZ the mixing desk the long lens shoots from. An open-air venue leaves the defaults.
    // (A plan carries one: VenuePlan::Bounds.)
    using Room = VenuePlan::Room;
    void SetRoom( const Room& inRoom ) { m_room = inRoom; }
    // The back of the room (venue z): wide shots stay in front of it.
    void SetRoomBack( float inZ ) { m_room.Back = inZ; }
    // How worked up the show is, 0 calm .. 1 peak (set every frame): handheld shots sway more,
    // moves run faster and the picture pushes a touch on each beat.
    void SetHype( float inHype ) { m_hype = inHype < 0.f ? 0.f : inHype > 1.f ? 1.f : inHype; }
    // A jolt (pyro, a CO2 jet, a big hit): the camera shakes and settles in under half a second.
    void Kick( float inAmount ) { if( inAmount > m_kick ) m_kick = inAmount; }
    // The show just went up a gear: a hero shot (a crane up over the crowd, a fast push to the
    // band, or over the band at the crowd; the same one for the same moment) takes the scheduled
    // cut's place for inHoldSeconds. The neck camera and the crowd surfer's shot keep the screen.
    void OnBigMoment( double inSeconds, float inHoldSeconds );
    void SetAccentPhase( float inPhase ) { m_accentPhase = inPhase; }
    // Story mode's shots (VenueShow::BuildStory): a story flag landing at a time (song seconds)
    // cuts to the venue's camera spot tagged "story/<flag>" and holds it, over everything else.
    // More of the tag, by '/': a number is the hold in seconds (5 without one), "hand" shoots it
    // handheld. A second spot tagged "story/<flag>/end" is where the shot has moved to by the
    // end of the hold (a pull back, a zoom). Flags with no spot get no shot.
    void SetStoryShots( const std::vector<std::pair<std::string, double>>& inLanding );
    int StoryShotCount() const { return static_cast<int>( m_storyShots.size() ); }
    bool HasPeakShots() const { return !m_peakSpots.empty(); }
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
    // Screens' feeds re-render about as often as the venue steps (every other frame when it runs smooth):
    // a stepped venue shows the same picture in between. inFrameSeconds is the game's frame time.
    void SetFeedStepRate( float inStepRate, float inFrameSeconds );
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
    // Crane: a jib from the pit up over the crowd's heads (or back down). Dolly: a track along
    // the pit rail, low, looking up at the front line. Drone: flown in from the back of the house.
    // Orbit: high and slow round the front of the stage. LongLens: from the mixing desk, the
    // crowd's heads in the foreground. CrowdPov: among the crowd, a few rows back. Profile: from
    // the wings across the stage. DrumTop / DrumLow: straight down on the kit, and low through
    // the cymbals. LowHero: from the deck by a member's monitor, looking up. Push: a fast run in
    // from over the crowd (big moments). PitRun: an operator at a half sprint down the photo pit,
    // camera on the shoulder, shooting along the front row of the crowd.
    enum class Framing { Far, Near, Behind, CloseHead, CloseHand, Kick, Crowd, Overhead, Wall, Neck, Surfer,
        Crane, Dolly, Drone, Orbit, LongLens, CrowdPov, Profile, DrumTop, DrumLow, LowHero, Push, PitRun,
        // Spot: one of the venue's own close or custom camera positions (VenuePlan::Cameras), the
        // plan's Variant its index.
        Spot, Arrival,
        // Story: a story shot (SetStoryShots), the plan's Variant its index.
        Story };

    struct Plan
    {
        std::vector<int> Subjects;     // members; empty is the whole band
        Framing Frame = Framing::Far;
        bool Handheld = false;
        bool Static = false;
        // Bit 0 the side, bit 1 an alternate take, bits 2-3 the treatment (Vary).
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
        float Grain = 0.03f;      // film grain: a touch on every look
        float FrameRate = 0.f;    // venue steps a second (0: smooth); not eased
    };

    Plan PlanFor( const std::string& inName, int inIndex ) const;
    // Takes the members the plan leaves out off a shot; a shot only of them (or of the kit with
    // no drummer) becomes a wide of whoever's there.
    void DropAbsent( Plan& ioPlan ) const;
    // A point placed for the drummer facing the crowd, turned with the drummer's spot (the kit
    // is built in their frame).
    Vector3 AtDrums( const Vector3& inPoint ) const { return m_plan.TurnWith( VenueData::Drums, inPoint ); }
    Plan PlanAuto( const std::string& inConstraints, int inIndex, float inTime ) const;
    // A point placed for the procedural rooms' stage, moved to this venue's (VenuePlan::ShotOffset).
    Vector3 OnStage( const Vector3& inPoint ) const { return inPoint + m_plan.ShotOffset; }
    // The venue's camera spots: the inPick'th of a kind (wrapping), null when it has none.
    const VenuePlan::CameraSpot* SpotFor( VenuePlan::CameraSpot::Kind inKind, int inPick ) const;
    // Where a camera spot looks: along its aim, as far off as inSubject (or the band's middle).
    Vector3 SpotTarget( const VenuePlan::CameraSpot& inSpot, const Vector3* inSubject ) const;
    // Turns some of the cuts over to the venue's close and custom camera spots.
    void AddSpotCuts();
    // Gives a chart's plain shot one of its treatments (a wide becomes a crane, a drone or the
    // long lens; a near shot a low hero angle...), by the plan's Variant.
    static void Vary( Plan& ioPlan );
    static const char* FramingName( Framing inFraming );
    // Keeps a camera in the room, and out of the audience unless the shot belongs there.
    void Contain( Vector3& ioEye, bool inAmongCrowd ) const;
    // Depth of field for the shot: the background blur it wants (pixels at 1080p; 0: everything sharp).
    static float BlurFor( const Plan& inPlan );
    // The fisheye the shot is seen through (PostProcess::LensDistortion; 0: a straight lens): the
    // small cameras, the one bolted to the guitar, the one run down the pit and the one held up in the crowd.
    static float LensFor( const Plan& inPlan );
    void ApplyFocus( const Plan& inPlan, const Vector3& inEye, const Vector3& inSubject, float inFov, bool inCut, float inDeltaTime );
    void BuildFallbackCuts( const VenueData& inVenue, float inSongLength );
    // Charts without looks: the concert look through intros, bridges, breakdowns and quiet parts.
    void BuildFallbackLooks( const VenueData& inVenue );
    void FillAutoCuts( const VenueData& inVenue, float inSongLength );
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
    VenuePlan m_plan;
    std::vector<VenuePlan::CameraSpot> m_arrival;
    std::vector<int> m_peakSpots;
    // A story shot: when it holds, its spot in m_plan.Cameras and where it ends up (-1: stays).
    struct StoryShot
    {
        double From = 0.0;
        double Until = 0.0;
        int Spot = -1;
        int End = -1;
        bool Handheld = false;
    };
    std::vector<StoryShot> m_storyShots;
    float m_accentPhase = -1.f;
    float m_arrivalElapsed = -1.f;
    double m_arrivalLastSongTime = 0.;
    EntityHandle m_main;
    EntityHandle m_feed;
    EntityHandle m_program;
    std::vector<Cut> m_cuts;
    std::vector<TimedCueData> m_looks;
    std::vector<BeatData> m_beats;
    float m_bpm = 120.f;
    Room m_room;
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
    float m_closeExposure = 0.f;   // stops taken off for a close subject (ApplyFocus)
    float m_fov = 45.f;
    int m_framedCut = -2;
    std::string m_framedShot;
    float m_leadSide = 0.f;    // this shot's lead room (LeadSideFor), chosen on the cut
    // How long the shot's move has run: the time since the cut, running faster with the hype.
    float m_moveTime = 0.f;
    float m_hype = 0.f;
    float m_kick = 0.f;        // a jolt, decaying
    // A big moment's hero shot (OnBigMoment), from m_bigStart until m_bigEnd.
    double m_bigStart = -1000.0;
    double m_bigEnd = -1000.0;
    // The lens: the focus distance and background blur, eased; snapped on a cut.
    float m_focus = 8.f;
    float m_blur = 0.f;
    // The crowd surfer being followed (FollowSurfer); the pit camera's side is chosen as they go up.
    bool m_surferUp = false;
    Vector3 m_surferPosition;
    float m_surferSide = 1.f;
};
