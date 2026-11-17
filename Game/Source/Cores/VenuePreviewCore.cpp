#include "Cores/VenuePreviewCore.h"
#include "Cores/NoteHighwayCore.h"
#include "Components/Transform.h"
#include "Components/Venue/VenueMarkers.h"
#include "Engine/World.h"
#include "File.h"
#include "Path.h"
#include "CLog.h"
#include <algorithm>
#include <cmath>

#if USING( ME_EDITOR )
#include <Editor/HostedPlay.h>
#include <imgui.h>
#endif


VenuePreviewCore::VenuePreviewCore()
    : Base( ComponentFilter().Requires<VenueInfo>() )
{
    // Added by the editor to the scene it has open: never written into the venue's .lvl.
    SetIsSerializable( false );
}


bool VenuePreviewCore::AttachIfVenue( World& inWorld )
{
#if USING( ME_EDITOR )
    if( inWorld.HasCore<VenuePreviewCore>() )
    {
        return true;
    }
    if( inWorld.HasCore<NoteHighwayCore>() )
    {
        // The gameplay scene builds its own show (a venue scene there is the game's).
        return false;
    }
    bool venue = false;
    inWorld.ForEachEntity( [&venue]( Entity& inEntity ) { venue = venue || inEntity.HasComponent<VenueInfo>(); } );
    if( !venue )
    {
        return false;
    }
    return inWorld.AddCoreByName( "VenuePreviewCore" ) != nullptr;
#else
    (void)inWorld;
    return false;
#endif
}


TrackData VenuePreviewCore::RockBeat( int inBpm, int inBars )
{
    TrackData chart;
    chart.m_trackName = "Venue Preview Beat";
    chart.m_artistName = "Drumsmith";
    chart.m_bpm = std::max( inBpm, 40 );
    const float beat = 60.f / static_cast<float>( chart.m_bpm );
    const int beats = std::max( inBars, 1 ) * 4;
    const auto note = [&chart]( PadId inPad, float inTime, uint8_t inVelocity ) {
        NoteData data;
        data.m_editorLane = inPad;
        data.m_triggerTime = inTime;
        data.m_triggerTimeMS = static_cast<uint32_t>( inTime * 1000.f );
        data.m_velocity = inVelocity;
        chart.m_noteData.push_back( data );
    };
    for( int i = 0; i < beats; ++i )
    {
        const float time = static_cast<float>( i ) * beat;
        BeatData grid;
        grid.m_time = time;
        grid.m_measure = i % 4 == 0;
        chart.m_beats.push_back( grid );
        if( i % 32 == 0 )
        {
            note( PadId::Crash1, time, 120 );
        }
        else
        {
            note( PadId::ClosedHiHat, time, 100 );
        }
        note( PadId::ClosedHiHat, time + beat * 0.5f, 80 );
        note( i % 2 == 0 ? PadId::Bass : PadId::Snare, time, 110 );
    }
    std::sort( chart.m_noteData.begin(), chart.m_noteData.end(), []( const NoteData& a, const NoteData& b ) { return a.m_triggerTime < b.m_triggerTime; } );
    chart.m_noteCount = static_cast<int>( chart.m_noteData.size() );
    chart.m_duration = static_cast<float>( beats ) * beat;
    chart.m_durationMS = chart.m_duration * 1000.f;
    return chart;
}


TrackData VenuePreviewCore::DemoChart( int inBpm, int inBars )
{
    // A real chart has the lighting, band and crowd cues a venue is cued by.
    for( const TrackData& track : TrackDatabase::GetInstance().m_trackList.m_tracks )
    {
        if( track.m_practice || track.m_calibration )
        {
            continue;
        }
        TrackData chart = track;
        if( chart.m_noteData.empty() )
        {
            File file( Path( chart.GetDirectory() + "/NoteData.txt" ) );
            const std::string text = file.Read();
            const json root = text.empty() ? json() : json::parse( text, nullptr, false );
            if( root.is_discarded() || !root.is_object() || root.empty() )
            {
                continue;
            }
            chart.OnLoadNoteData( root );
        }
        if( !chart.m_noteData.empty() )
        {
            float last = 0.f;
            for( const NoteData& note : chart.m_noteData ) last = std::max( last, note.m_triggerTime );
            chart.m_duration = std::max( chart.m_duration, last + 2.f );
            return chart;
        }
    }
    return RockBeat( inBpm, inBars );
}


void VenuePreviewCore::OnStart()
{
    m_tried = false;
    m_problem.clear();
    m_timeMs = 0.0;
}


void VenuePreviewCore::OnStop()
{
    m_show.Clear();
    m_tried = false;
}


void VenuePreviewCore::Update( const UpdateContext& inContext )
{
#if USING( ME_EDITOR )
    if( !m_tried )
    {
        m_tried = true;
        World& world = GetWorld();
        if( world.HasCore<NoteHighwayCore>() || HostedPlay::Active() )
        {
            // The game's own show, or the Track Editor's preview, which loads the gameplay scene.
            return;
        }
        // Every top-level entity of the open scene: the markers can be anywhere in it.
        std::vector<EntityHandle> roots;
        world.ForEachEntity( [&roots, &world]( Entity& inEntity ) {
            Transform* transform = inEntity.TryGetComponent<Transform>();
            if( transform && !transform->GetParentTransform() )
            {
                roots.emplace_back( inEntity.GetId(), &world );
            }
        } );
        m_chart = DemoChart();
        m_lengthMs = std::max( m_chart.m_duration, 1.f ) * 1000.f;
        m_timeMs = 0.0;
        if( !m_show.BuildAround( world, m_chart, roots, m_problem ) )
        {
            YIKES_FMT( "[Venues] The open scene can't be played as a venue: %s", m_problem.c_str() );
            return;
        }
        INFO_FMT( "[Venues]", "Venue preview: playing the open scene to \"%s - %s\" (%.0f s, looping)", m_chart.m_artistName.c_str(), m_chart.m_trackName.c_str(), m_lengthMs / 1000.f );
    }
    if( !m_show.IsActive() )
    {
        return;
    }
    const float delta = inContext.GetDeltaTime();
    m_timeMs += static_cast<double>( delta ) * 1000.0;
    if( m_timeMs >= m_lengthMs )
    {
        // Round again, from the top of the chart.
        m_timeMs = 0.0;
    }
    m_show.SetPerformance( 0.8f );
    m_show.Update( m_timeMs, delta );
#else
    (void)inContext;
#endif
}


#if USING( ME_EDITOR )
void VenuePreviewCore::OnEditorInspect()
{
    Base::OnEditorInspect();
    if( !m_problem.empty() )
    {
        ImGui::TextWrapped( "Not a venue: %s", m_problem.c_str() );
    }
    else if( m_show.IsActive() )
    {
        ImGui::Text( "Playing to: %s - %s", m_chart.m_artistName.c_str(), m_chart.m_trackName.c_str() );
        ImGui::Text( "%.1f / %.0f s", m_timeMs / 1000.0, m_lengthMs / 1000.f );
    }
    else
    {
        ImGui::TextWrapped( "In play, builds the band, crowd, cameras and cued lights around this venue scene." );
    }
}
#endif
