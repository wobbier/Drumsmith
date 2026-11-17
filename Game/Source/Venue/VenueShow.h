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
#include "ECS/EntityHandle.h"
#include <chrono>
#include <cstdint>
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

    // inHighwayCamera: the highway's camera entity, made an overlay while the show runs. The style
    // comes from the VenueStyle setting (or --venue-style) unless one is given.
    void Build( World& inWorld, const TrackData& inTrack, const EntityHandle& inHighwayCamera, int inStyle = -1 );
    // The same from a floor plan of the caller's (a scene venue's markers): where the band, crowd
    // and screens go and which built-in pieces go up. The plan's Style is the room it dresses as.
    void Build( World& inWorld, const TrackData& inTrack, const EntityHandle& inHighwayCamera, const VenuePlan& inPlan );
    void Clear();
    // Tears the venue down and builds the next style in its place, mid-song: the highway on top
    // carries on regardless.
    void NextStyle();
    Style GetStyle() const { return m_style; }
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

    bool IsActive() const { return static_cast<bool>( m_root ); }
    const Director& GetDirector() const { return m_director; }

private:
    // Whether a show goes up at all (the Venue setting, --no-venue, a practice lesson).
    bool Wanted( const TrackData& inTrack ) const;
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
    // inLevel 1: a lift (jets, a hit on the blinders). 2: a peak (confetti, sparks, flames, a
    // hero shot). Ignored while the last one is still ringing.
    void BigMoment( double inSeconds, int inLevel );

    VenueKit m_kit;
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
};
