#pragma once
#include "CoreGame/StageLights.h"
#include "CoreGame/TrackList.h"
#include "Venue/Band.h"
#include "Venue/Crowd.h"
#include "Venue/Director.h"
#include "Venue/VenueKit.h"
#include "ECS/EntityHandle.h"
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
    // The room around the stage. The stage, band and rig are the same in each.
    enum class Style : int { Arena = 0, Club, Festival, Count };
    static const char* StyleName( Style inStyle );

    // inHighwayCamera: the highway's camera entity, made an overlay while the show runs. The style
    // comes from the VenueStyle setting (or --venue-style) unless one is given.
    void Build( World& inWorld, const TrackData& inTrack, const EntityHandle& inHighwayCamera, int inStyle = -1 );
    void Clear();
    // Tears the venue down and builds the next style in its place, mid-song: the highway on top
    // carries on regardless.
    void NextStyle();
    Style GetStyle() const { return m_style; }
    void Update( double inSongTimeMs, float inDeltaTime );

    void OnHit( PadId inPad );
    void OnMiss();
    // The player's form: 0 struggling .. 1 on a long streak (the crowd reads it).
    void SetPerformance( float inPerformance ) { m_performance = inPerformance; }
    void OnStreak( int inCombo );

    bool IsActive() const { return static_cast<bool>( m_root ); }
    const Director& GetDirector() const { return m_director; }

private:
    void BuildStage( Transform& inRoot );
    void BuildArena( Transform& inRoot );
    void BuildClub( Transform& inRoot );
    void BuildFestival( Transform& inRoot );
    void BuildScreen( Transform& inRoot, const Vector3& inCentre, const Vector3& inSize, float inYaw, const char* inTexture );
    void UpdateSet( double inSeconds, float inDeltaTime );

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
    VenueData m_venue;
    std::vector<BeatData> m_beats;
    float m_bpm = 120.f;
    float m_performance = 0.5f;

    // Set pieces that move: the LED strip along the stage's edge, pyro.
    std::vector<EntityHandle> m_edgeStrip;
    struct Pyro
    {
        EntityHandle Flame;
        EntityHandle Light;
        Vector3 Base;
    };
    std::vector<Pyro> m_pyro;

    // The highway camera as it was.
    bool m_savedHighway = false;
    bool m_highwayFog = false;
};
