#pragma once
#include "ECS/Core.h"
#include "CoreGame/TrackList.h"
#include "Venue/VenueShow.h"
#include <string>

class World;

// Plays a venue scene opened in Havana (Docs/Venue-and-Band.md): in the editor's play mode, with a
// venue's VenueInfo in the world and no note highway, it builds the band, crowd, cameras and cued
// lights around the open scene where it stands (VenueShow::BuildAround: nothing instanced twice)
// and plays the show to a demo chart on its own clock, looping. A venue .lvl never lists it (the
// game strips a scene's cores and Tools/Venues/check_venue.py rejects them): the Track Editor adds
// it to a scene that has a VenueInfo when the scene is loaded (AttachIfVenue), and it is never
// saved with the scene. Outside the editor it does nothing.
class VenuePreviewCore final
    : public Core<VenuePreviewCore>
{
public:
    VenuePreviewCore();

    void OnStart() override;
    void OnStop() override;
    void Update( const UpdateContext& inContext ) override;

    // Adds the core to inWorld when it holds a VenueInfo and has no NoteHighwayCore. True when
    // the world has the core afterwards.
    static bool AttachIfVenue( World& inWorld );
    // The chart the show plays to: the first song in the library with a chart (its lighting and
    // band cues included), or a steady rock beat of inBars bars at inBpm when there is none.
    static TrackData DemoChart( int inBpm = 120, int inBars = 32 );
    // A plain rock beat (kick on 1 and 3, snare on 2 and 4, closed hi-hat eighths, a crash every
    // eight bars), with its beat grid.
    static TrackData RockBeat( int inBpm, int inBars );

    bool IsShowing() const { return m_show.IsActive(); }
    const std::string& GetProblem() const { return m_problem; }

private:
#if USING( ME_EDITOR )
    void OnEditorInspect() override;
#endif

    VenueShow m_show;
    TrackData m_chart;
    double m_timeMs = 0.0;
    float m_lengthMs = 0.f;
    bool m_tried = false;
    std::string m_problem;
};

ME_REGISTER_CORE( VenuePreviewCore )
