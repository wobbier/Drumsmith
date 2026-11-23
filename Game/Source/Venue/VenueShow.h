#pragma once
#include "CoreGame/StageLights.h"
#include "CoreGame/TrackList.h"
#include "Venue/Band.h"
#include "Venue/Crowd.h"
#include "Venue/Director.h"
#include "Venue/LyricBoard.h"
#include "Venue/StageFx.h"
#include "Venue/StageSet.h"
#include "Venue/VenueKit.h"
#include "Venue/VenuePlan.h"
#include "Venue/VenueRegistry.h"
#include "Venue/VenueScene.h"
#include "Components/Venue/VenueMarkers.h"
#include "ECS/EntityHandle.h"
#include "Camera/ProceduralSkySettings.h"
#include <chrono>
#include <cstdint>
#include <set>
#include <string>
#include <vector>

class World;

// The venue under the note highway (Docs/Venue-and-Band.md): a stage with its band, a crowd, the
// light show and a camera crew, all built from a chart's venue data and played on the song clock.
// It lives far from the highway; its camera becomes the screen's main camera and the highway's
// camera turns into an overlay drawn on top (Camera::Overlay), so the venue can change underneath
// without touching the highway. NoteHighwayCore owns it.
class VenueShow
{
public:
    // The room around the stage. The stage, band and rig are the same in each
    // (VenuePlan::ForStyle).
    enum class Style : int { Arena = 0, Club, Festival, Count };
    static const char* StyleName( Style inStyle );

    // inHighwayCamera: the highway's camera entity, made an overlay while the show runs. Without
    // a style the venue is the registry's pick (VenueRegistry::ChooseForSong: --venue, a venue
    // scene, --venue-style, the song's, the player's, the VenueStyle setting); with one, that room.
    void Build( World& inWorld, const TrackData& inTrack, const EntityHandle& inHighwayCamera, int inStyle = -1 );
    // The same from a floor plan of the caller's (a scene venue's markers): where the band, crowd
    // and screens go and which built-in pieces go up. The plan's Style is the room it dresses as.
    void Build( World& inWorld, const TrackData& inTrack, const EntityHandle& inHighwayCamera, const VenuePlan& inPlan );
    // The show around a venue scene that is already in the world, where it stands (a venue .lvl
    // played in Havana: Cores/VenuePreviewCore): its markers read in place, the band, crowd,
    // cameras and cued lights built around it at the world's origin, no highway. Ignores the
    // Venue setting (it was asked for). False, with the reason, when the scene isn't a venue.
    bool BuildAround( World& inWorld, const TrackData& inTrack, const std::vector<EntityHandle>& inSceneRoots, std::string& outProblem );
    void Clear();

    // A venue that wins over the registry's pick for every Build without a style, process-wide:
    // the Track Editor's preview showing the venue its author picked (Editor/Chart/PreviewSession).
    // inVenue is what --venue takes: a registry id (hidden ones too), a room name (Arena, Club,
    // Festival) or a .lvl path. It's resolved at each Build, so a registry Reload in between is
    // seen. F7 steps on from it as usual. Empty clears it.
    static void SetOverride( const std::string& inVenue );
    static const std::string& GetOverride();
    // What the last Build under the override came to: the scene or room built, or why the scene
    // couldn't be a venue and which room stood in. Empty until one is built.
    static const std::string& GetOverrideOutcome();
    // The last Build under the override couldn't build what it named (no such venue, or a scene
    // that can't be one) and built a room instead.
    static bool OverrideFellBack();
    // Tears the venue down and builds the next one in its place, mid-song (F7): Arena, Club,
    // Festival, then each venue scene the menu lists, and round again. The highway on top carries
    // on regardless.
    void NextStyle();
    // The room, or the room a scene venue dresses as.
    Style GetStyle() const { return m_style; }
    // The venue scene showing (its registry id or path); empty for a procedural room.
    const std::string& GetSceneId() const { return m_sceneId; }
    // The floor plan the show was built from (an empty default before Build).
    const VenuePlan& GetPlan() const { return m_plan; }
    void Update( double inSongTimeMs, float inDeltaTime );

    void OnHit( PadId inPad );
    void OnMiss();
    // The player's form: 0 struggling .. 1 on a long streak (the crowd reads it).
    void SetPerformance( float inPerformance ) { m_performance = inPerformance; }
    void OnStreak( int inCombo );

    // What reaches the screen: the highway over the venue (a play), or one of them alone (the
    // Track Editor's preview: a charter watches the notes, a venue author the show). Kept across
    // Build and Clear.
    enum class Presentation : int { Both = 0, HighwayOnly, VenueOnly };
    void SetPresentation( Presentation inPresentation );
    Presentation GetPresentation() const { return m_presentation; }
    // How much of the highway shows over the venue, 0 to 1: below 1 it melts away from its far end
    // toward the strike bar (a story song's long rests: ProgressionStorySong::HighwayRests). Only
    // over a venue (Presentation::Both); kept across Build.
    void SetHighwayShown( float inShown );

    // Whether a venue scene's ambience (venue.json's Ambience: a crowd waiting for the band) plays:
    // on for a play, off for the Track Editor's preview. Kept across Build and Clear. It plays from
    // the Build and fades out over the song's first seconds (Update); the pause menu holds it.
    void SetAmbienceWanted( bool inWanted ) { m_ambienceWanted = inWanted; }
    void SetAmbiencePaused( bool inPaused );

    bool IsActive() const { return static_cast<bool>( m_root ); }
    const Director& GetDirector() const { return m_director; }
    // A story moment's caption showing at inSeconds (a line said on screen), else empty.
    std::string StoryCaption( double inSeconds ) const;
    // When a story cue falls in a chart (seconds): a song cue ("intro", "solo", "song_end"...),
    // "section:<name>", "at:<share of the song>", "time:<seconds>", "drums_in" (the first note),
    // "last_note" or "start", each optionally moved by "+<seconds>" or "-<seconds>". An unknown
    // one is halfway.
    static double StoryCueTime( const VenueData& inVenue, const std::string& inCue, double inLength, double inFirstNote, double inLastNote );
    // When a story moment lands: where the chart's own Story cues put one of its flags
    // (VenueData::m_story, the Track Editor's Story track), else at the set's cue.
    static double StoryMomentTime( const VenueData& inVenue, const std::set<std::string>& inFlags, const std::string& inCue, double inLength, double inFirstNote, double inLastNote );

private:
    // Whether a show goes up at all (the Venue setting, --no-venue, a practice lesson).
    bool Wanted( const TrackData& inTrack ) const;
    // Builds the venue a pick came to: its scene (falling back to a room when the scene can't be
    // a venue) or a room.
    void BuildChoice( World& inWorld, const TrackData& inTrack, const EntityHandle& inHighwayCamera, const VenueChoice& inChoice );
    // A crowd stands, posed or mob (a scene's may be all mob).
    bool CrowdUp() const { return m_crowd.Size() + m_crowd.MobSize() > 0; }
    // Build's work once the plan is settled.
    void BuildShow( World& inWorld, const TrackData& inTrack, const EntityHandle& inHighwayCamera, const VenuePlan& inPlan );
    void BuildStage( Transform& inRoot );
    void BuildArena( Transform& inRoot );
    void BuildArenaDetail( Transform& inRoot );
    void BuildClub( Transform& inRoot );
    void BuildFestival( Transform& inRoot );
    void FillHouse( Transform& inRoot, float inScale );
    // --highway-log: the venue's main-thread cost, every five seconds.
    void LogUpdateCost( std::chrono::steady_clock::time_point inStarted );
    void BuildScreen( Transform& inRoot, const VenuePlan::Screen& inScreen );
    // The show's hype (Docs/Venue-and-Band.md, Hype): how hot it's running now, and the big
    // moments that set off the effects.
    void UpdateHype( double inSeconds, float inDeltaTime );
    void StartAccent( double inSeconds, int inLevel );
    // Story mode's props (VenueStory markers): what each was authored as, read once the scene is
    // in, and each frame shown or hidden by the story's flags (VenueRegistry::Story).
    void BuildStory( double inLength, double inFirstNote, double inLastNote );
    void UpdateStory( double inSeconds, float inDeltaTime );
    // Whether a story flag is set at inSeconds: before the song, at its cue, or at a moment.
    bool StoryFlagSet( const std::string& inFlag, double inSeconds ) const;

    void SampleAccents( double inBeat );
    // inLevel 1: a lift (jets, a hit on the blinders). 2: a peak (confetti, sparks, flames, a
    // hero shot). Ignored while the last one is still ringing.
    void BigMoment( double inSeconds, int inLevel );

    // The ambience's looping, streamed AudioSource under the venue root, faded on the song clock.
    void StartAmbience( const VenueAmbience& inAmbience );
    void UpdateAmbience( double inSongTimeMs );

    // This build is the override's (SetOverride): BuildChoice reports what it came to.
    bool m_fromOverride = false;
    bool m_ambienceWanted = false;
    // Until it has faded out (then it's stopped and let go; the kit deletes it with the venue).
    EntityHandle m_ambience;
    // Its voice is going (from a random point in the clip).
    bool m_ambienceStarted = false;
    VenueAmbience m_ambienceSettings;
    VenueKit m_kit;
    // The venue scene showing (none in a procedural room), and its registry id.
    VenueScene m_scene;
    std::string m_sceneId;
    // Entities with a VenueBeat marker, and where each rests.
    struct BeatProp
    {
        EntityHandle Entity;
        Vector3 Rest;
    };
    std::vector<BeatProp> m_beatProps;
    void UpdateBeats( double inSeconds );
    struct StoryProp
    {
        EntityHandle Entity;
        std::string Flag;
        bool WhenSet = true;
        float Fade = 0.75f;
        Vector3 Scale;
        float Shown = -1.f;     // 0 hidden to 1 shown; -1 before the first update (it snaps)
        VenueStory::Motion Mode = VenueStory::Motion::Show;
        float Speed = 0.3f;
        // Mode Play / SlowMotion: the entities with a Sequence under it, and whether it's played.
        std::vector<EntityHandle> Sequences;
        bool Played = false;
    };
    // A ParticleSystem under Show props: it emits only while every one of them is shown (a hidden
    // prop is only scaled away, which would leave its fire burning at its pivot), and starts over
    // when they show, so a one-shot burst goes off as its flag lands.
    struct StoryParticles
    {
        EntityHandle Entity;
        std::vector<size_t> Props;
        int On = -1;            // -1 before the first update
    };
    std::vector<StoryParticles> m_storyParticles;
    // A VenueShowLight under Show props: the rig still cues it, and it is dimmed with the props
    // after the cue is applied (hell's red washes stay dark until the band lands there).
    struct StoryShowLight
    {
        EntityHandle Entity;
        std::vector<size_t> Props;
        float Cued = 0.f;       // the level the rig last gave it
        float Written = -1.f;   // what was left in the Light after dimming
    };
    std::vector<StoryShowLight> m_storyShowLights;
    // A scene light (not the rig's) under Show props, and its own intensity: it shines by the
    // least shown of every prop above it. (One group nested in another: a light of the fall is
    // out until they fall, though its inner "until they land" group is showing all along.)
    struct StoryLight
    {
        EntityHandle Entity;
        float Intensity = 0.f;
        std::vector<size_t> Props;
    };
    std::vector<StoryLight> m_storyLights;
    void DimStoryShowLights();
    // A story shot's own sky (Director::ShotSky): on the main camera while the shot holds.
    void UpdateShotSky();
    bool m_shotSkyOn = false;
    int m_shotSkyClear = 0;
    Moonlight::ProceduralSkySettings m_shotSkySaved;
    void UpdateStoryMotion( StoryProp& ioProp, bool inSet );
    // The band_ story flags on the band (Band::SetStoryState).
    void UpdateStoryBand( double inSeconds, float inDeltaTime );
    // Every flag landing this song (flags set before it at -1e9), for the band's pose.
    std::vector<std::pair<std::string, double>> m_storyLanding;
    // The band has been put in a story pose this song (so it's kept up to date from then on).
    bool m_bandStoried = false;
    struct StoryCaptionLine
    {
        double From = 0.0;
        double Until = 0.0;
        std::string Text;
    };
    std::vector<StoryCaptionLine> m_storyCaptions;
    std::vector<StoryProp> m_storyProps;
    // When the song's own flags land (its cue), in song seconds; -1 for no story.
    double m_storyCue = -1.0;
    // The song's moments: when each lands, and its flags.
    std::vector<std::pair<double, std::set<std::string>>> m_storyMoments;
    // How much of the highway shows (SetHighwayShown), as last put on its camera.
    float m_highwayShown = 1.f;
    Band m_band;
    Crowd m_crowd;
    Director m_director;
    StageLights m_lights;
    EntityHandle m_root;
    EntityHandle m_highwayCamera;
    World* m_world = nullptr;
    const TrackData* m_track = nullptr;
    Style m_style = Style::Arena;
    VenuePlan m_plan;
    VenueData m_venue;
    Lyrics m_lyrics;
    LyricBoard m_lyricBoard;
    std::vector<BeatData> m_beats;
    float m_bpm = 120.f;
    float m_performance = 0.5f;
    // Where the follow spots aim, eased toward the members (VenueShow::Update).
    Vector3 m_spotAims[5] = { Vector3( 1e4f, 0.f, 0.f ), Vector3( 1e4f, 0.f, 0.f ), Vector3( 1e4f, 0.f, 0.f ), Vector3( 1e4f, 0.f, 0.f ), Vector3( 1e4f, 0.f, 0.f ) };
    double m_updateMs = 0.0;
    int m_updateFrames = 0;
    // Looks with a frame rate (the concert look) step the venue: it's updated once a step, on the
    // step's time, and held in between, like a camera feed at a low frame rate. The highway, an
    // overlay camera, stays smooth.
    int64_t m_lastStep = INT64_MIN;
    float m_stepDelta = 0.f;
    float m_frameSeconds = 1.f / 60.f;

    StageSet m_set;
    StageFx m_fx;
    // Hype: eased 0 calm .. 1 peak, from the chart's energy and the player's streak.
    float m_hype = 0.f;
    double m_lastMoment = -1000.0;
    double m_accentBeat = -10000.;
    bool m_accentPlaying = false;
    int m_accentLevel = 0;
    double m_captureElapsed = 0.;
    double m_lastSeconds = -1000.0;
    double m_lastPlayerPeak = -1000.0;   // the last peak the player's streak set off
    int m_pendingMoment = 0;       // a big moment asked for off the song clock (OnStreak)
    float m_kick = 0.f;            // 1 on the player's kick, decaying (the riser's fascia)
    // The chart's own peaks, found at build: when each chorus or intense passage starts.
    std::vector<float> m_peaks;
    float m_finale = 1e9f;         // the last chorus, or the big rock ending

    // Puts m_presentation on the cameras.
    void ApplyPresentation();
    Presentation m_presentation = Presentation::Both;
    // The highway's camera has the screen to itself (Presentation::HighwayOnly).
    bool m_highwayAlone = false;

    // The highway camera as it was.
    bool m_savedHighway = false;
    bool m_highwayFog = false;
    bool m_highwaySunShadows = true;
};
