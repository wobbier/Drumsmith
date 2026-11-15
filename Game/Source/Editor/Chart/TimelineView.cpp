#include "Editor/Chart/TimelineView.h"
#include "CoreGame/BeatGrid.h"
#include "Editor/Chart/Transport.h"
#include "Editor/PadBindings.h"
#include <algorithm>
#include <cmath>

#if USING( ME_EDITOR )

namespace
{
    constexpr float kGutter = 150.f;
    constexpr float kRuler = 38.f;
    constexpr float kOverview = 14.f;
    constexpr float kHeaderHeight = 18.f;
    constexpr float kEventRowHeight = 18.f;
    constexpr float kDragThreshold = 3.f;
    constexpr double kMinSpan = 0.02;

    constexpr ImU32 kBackground = 0xFF1B1B1D;
    constexpr ImU32 kHeaderFill = 0xFF2B2B2F;
    constexpr ImU32 kGutterFill = 0xFF232326;
    constexpr ImU32 kText = 0xFFD8D8D8;
    constexpr ImU32 kTextDim = 0xFF8C8C8C;
    constexpr ImU32 kPlayhead = 0xFFFFFFFF;
    constexpr ImU32 kSelected = 0xFFFFFFFF;
    constexpr ImU32 kLoop = 0xFF78D060;
    constexpr ImU32 kLoopOff = 0xFF8C8C8C;
    constexpr float kLoopEdgeGrab = 5.f;

    ImU32 WithAlpha( ImU32 inColor, ImU32 inAlpha )
    {
        return ( inColor & 0x00FFFFFF ) | ( inAlpha << 24 );
    }
}


TimelineView::TimelineView()
{
    // The band's states and the lyrics are the busiest and least edited; they start folded.
    Collapsed[static_cast<size_t>( TrackGroup::Band )] = true;
    Collapsed[static_cast<size_t>( TrackGroup::Lyrics )] = true;
}


double TimelineView::SnapTime( const ChartDocument& inDocument, double inSeconds, bool inBypass ) const
{
    if( !SnapEnabled || inBypass )
    {
        return std::max( 0.0, inSeconds );
    }
    return BeatGrid::Snap( inDocument.Chart.m_beats, static_cast<float>( inDocument.Chart.m_bpm ), inSeconds, SnapDivision );
}


std::vector<int> TimelineView::VisibleTracks( const ChartDocument& inDocument ) const
{
    std::vector<int> tracks;
    for( int track = 0; track < inDocument.TrackCount(); ++track )
    {
        const size_t group = static_cast<size_t>( inDocument.Tracks[track]->Group );
        if( !Hidden[group] && !Collapsed[group] )
        {
            tracks.push_back( track );
        }
    }
    return tracks;
}


void TimelineView::Reveal( double inSeconds )
{
    const double span = static_cast<double>( m_contentMax.x - m_contentMin.x ) / PixelsPerSecond;
    if( inSeconds < ViewStart || inSeconds > ViewStart + span )
    {
        ViewStart = inSeconds - span * 0.25;
    }
}


void TimelineView::ZoomToFit( const ChartDocument& inDocument )
{
    const float width = std::max( 100.f, m_contentMax.x - m_contentMin.x );
    PixelsPerSecond = std::clamp( width / static_cast<float>( std::max( 1.0, inDocument.Duration() ) ), 2.f, 3000.f );
    ViewStart = 0.0;
}


void TimelineView::Layout( const ChartDocument& inDocument )
{
    m_rows.clear();
    float y = 0.f;
    for( int group = 0; group < static_cast<int>( TrackGroup::Count ); ++group )
    {
        if( Hidden[group] )
        {
            continue;
        }
        bool any = false;
        for( int track = 0; track < inDocument.TrackCount(); ++track )
        {
            const IEventTrack& eventTrack = *inDocument.Tracks[track];
            if( static_cast<int>( eventTrack.Group ) != group )
            {
                continue;
            }
            if( !any )
            {
                m_rows.push_back( { -1, 0, static_cast<TrackGroup>( group ), y, kHeaderHeight } );
                y += kHeaderHeight;
                any = true;
            }
            if( Collapsed[group] )
            {
                continue;
            }
            const float height = eventTrack.Group == TrackGroup::Notes ? NoteRowHeight : kEventRowHeight;
            for( int row = 0; row < eventTrack.Rows(); ++row )
            {
                m_rows.push_back( { track, row, static_cast<TrackGroup>( group ), y, height } );
                y += height;
            }
        }
    }
    m_rowsHeight = y;
}


int TimelineView::RowAt( float inY ) const
{
    for( int row = 0; row < static_cast<int>( m_rows.size() ); ++row )
    {
        const float top = RowTop( m_rows[row] );
        if( inY >= top && inY < top + m_rows[row].Height )
        {
            return row;
        }
    }
    return -1;
}


int TimelineView::RowOf( int inTrack, int inTrackRow ) const
{
    for( int row = 0; row < static_cast<int>( m_rows.size() ); ++row )
    {
        if( m_rows[row].Track == inTrack && m_rows[row].TrackRow == inTrackRow )
        {
            return row;
        }
    }
    return -1;
}


float TimelineView::PointWidth( const IEventTrack& inTrack ) const
{
    if( inTrack.Group == TrackGroup::Notes )
    {
        return std::clamp( PixelsPerSecond * 0.045f, 5.f, 14.f );
    }
    return inTrack.Domain == ChartDomain::Beats ? 3.f : 5.f;
}


bool TimelineView::ItemBox( const ChartDocument& inDocument, int inTrack, int inItem, ImVec2& outMin, ImVec2& outMax ) const
{
    const IEventTrack& track = *inDocument.Tracks[inTrack];
    const int rowIndex = RowOf( inTrack, track.Rows() > 1 ? track.Row( inItem ) : 0 );
    if( rowIndex < 0 )
    {
        return false;
    }
    const Row& row = m_rows[rowIndex];
    const float top = RowTop( row );
    outMin = { TimeToX( track.Start( inItem ) ), top + 2.f };
    outMax = { outMin.x + PointWidth( track ), top + row.Height - 2.f };
    if( track.Spans )
    {
        outMax.x = std::max( outMin.x + 3.f, TimeToX( track.End( inItem ) ) );
    }
    else if( track.Group != TrackGroup::Notes )
    {
        // A marker and its name, up to the next item in the row.
        const std::string label = track.Label( inItem );
        if( !label.empty() )
        {
            outMax.x += ImGui::CalcTextSize( label.c_str() ).x + 6.f;
            if( track.Rows() == 1 && inItem + 1 < track.Count() )
            {
                outMax.x = std::max( outMin.x + PointWidth( track ), std::min( outMax.x, TimeToX( track.Start( inItem + 1 ) ) - 1.f ) );
            }
        }
    }
    return true;
}


bool TimelineView::HitTest( const ChartDocument& inDocument, ImVec2 inPos, ChartItemRef& outRef, Edge& outEdge ) const
{
    outEdge = Edge::None;
    const int rowIndex = RowAt( inPos.y );
    if( rowIndex < 0 || m_rows[rowIndex].Track < 0 )
    {
        return false;
    }
    const Row& row = m_rows[rowIndex];
    const IEventTrack& track = *inDocument.Tracks[row.Track];
    bool hit = false;
    for( int item = 0; item < track.Count(); ++item )
    {
        if( track.Rows() > 1 && track.Row( item ) != row.TrackRow )
        {
            continue;
        }
        if( TimeToX( track.Start( item ) ) > inPos.x )
        {
            continue;
        }
        ImVec2 min, max;
        if( ItemBox( inDocument, row.Track, item, min, max ) && inPos.x >= min.x && inPos.x <= max.x )
        {
            outRef = { row.Track, item };
            hit = true;
            outEdge = Edge::None;
            if( track.Spans && max.x - min.x > 14.f )
            {
                outEdge = inPos.x < min.x + 5.f ? Edge::Start : inPos.x > max.x - 5.f ? Edge::End : Edge::None;
            }
        }
    }
    return hit;
}


void TimelineView::ClampView( const ChartDocument& inDocument )
{
    PixelsPerSecond = std::clamp( PixelsPerSecond, 2.f, 3000.f );
    const double span = static_cast<double>( m_contentMax.x - m_contentMin.x ) / PixelsPerSecond;
    const double lead = 20.0 / PixelsPerSecond;
    ViewStart = std::clamp( ViewStart, -lead, std::max( -lead, m_duration - span * 0.2 ) );
    ScrollY = std::clamp( ScrollY, 0.f, std::max( 0.f, m_rowsHeight - ( m_contentMax.y - m_contentMin.y ) ) );
}


void TimelineView::Draw( ChartDocument& inDocument, Transport& inTransport, ImVec2 inSize )
{
    const ImVec2 available = ImGui::GetContentRegionAvail();
    ImVec2 size = { inSize.x > 0.f ? inSize.x : available.x, inSize.y > 0.f ? inSize.y : available.y };
    size.x = std::max( size.x, kGutter + 100.f );
    size.y = std::max( size.y, kRuler + kOverview + 60.f );

    m_min = ImGui::GetCursorScreenPos();
    m_max = { m_min.x + size.x, m_min.y + size.y };
    m_contentMin = { m_min.x + kGutter, m_min.y + kRuler };
    m_contentMax = { m_max.x, m_max.y - kOverview };
    m_duration = std::max( inDocument.Duration(), inTransport.Length() );
    Layout( inDocument );

    ImGui::InvisibleButton( "##timeline", size, ImGuiButtonFlags_MouseButtonLeft | ImGuiButtonFlags_MouseButtonRight | ImGuiButtonFlags_MouseButtonMiddle );
    const bool hovered = ImGui::IsItemHovered();
    HandleInput( inDocument, inTransport, hovered );

    if( Follow && inTransport.IsPlaying() && m_gesture == Gesture::None )
    {
        const double span = static_cast<double>( m_contentMax.x - m_contentMin.x ) / PixelsPerSecond;
        if( inTransport.Seconds() > ViewStart + span * 0.85 || inTransport.Seconds() < ViewStart )
        {
            ViewStart = inTransport.Seconds() - span * 0.15;
        }
    }
    ClampView( inDocument );

    ImDrawList* drawList = ImGui::GetWindowDrawList();
    drawList->AddRectFilled( m_min, m_max, kBackground );

    drawList->PushClipRect( m_contentMin, m_contentMax, true );
    DrawRows( inDocument, drawList );
    DrawGrid( inDocument, drawList );
    if( inTransport.HasLoop() )
    {
        const ImU32 color = inTransport.IsLooping() ? kLoop : kLoopOff;
        const float x0 = TimeToX( inTransport.LoopStart() );
        const float x1 = TimeToX( inTransport.LoopEnd() );
        drawList->AddRectFilled( { x0, m_contentMin.y }, { x1, m_contentMax.y }, WithAlpha( color, 0x12 ) );
        drawList->AddLine( { x0, m_contentMin.y }, { x0, m_contentMax.y }, WithAlpha( color, 0x90 ) );
        drawList->AddLine( { x1, m_contentMin.y }, { x1, m_contentMax.y }, WithAlpha( color, 0x90 ) );
    }
    DrawItems( inDocument, drawList );
    if( m_gesture == Gesture::Box )
    {
        const ImVec2 mouse = ImGui::GetIO().MousePos;
        const ImVec2 a = { std::min( m_pressPos.x, mouse.x ), std::min( m_pressPos.y, mouse.y ) };
        const ImVec2 b = { std::max( m_pressPos.x, mouse.x ), std::max( m_pressPos.y, mouse.y ) };
        drawList->AddRectFilled( a, b, 0x30FFC878 );
        drawList->AddRect( a, b, 0xC0FFC878 );
    }
    const float playheadX = TimeToX( inTransport.Seconds() );
    drawList->AddLine( { playheadX, m_contentMin.y }, { playheadX, m_contentMax.y }, kPlayhead, 1.5f );
    drawList->PopClipRect();

    DrawRuler( inDocument, inTransport, drawList );
    DrawGutter( inDocument, drawList );
    DrawOverview( inDocument, inTransport, drawList );
    drawList->AddRect( m_min, m_max, 0xFF3A3A3E );
    DrawContextMenu( inDocument, inTransport );
    DrawRulerMenu( inDocument, inTransport );
}


void TimelineView::DrawRows( const ChartDocument& inDocument, ImDrawList* inDrawList )
{
    const float mouseY = ImGui::GetIO().MousePos.y;
    const bool mouseInside = ImGui::IsItemHovered();
    int stripe = 0;
    for( const Row& row : m_rows )
    {
        const float top = RowTop( row );
        if( top > m_contentMax.y || top + row.Height < m_contentMin.y )
        {
            ++stripe;
            continue;
        }
        if( row.Track < 0 )
        {
            inDrawList->AddRectFilled( { m_contentMin.x, top }, { m_contentMax.x, top + row.Height }, kHeaderFill );
            stripe = 0;
            // A folded group shows where its events are.
            if( Collapsed[static_cast<size_t>( row.Group )] )
            {
                for( const auto& track : inDocument.Tracks )
                {
                    if( track->Group != row.Group )
                    {
                        continue;
                    }
                    for( int item = 0; item < track->Count(); ++item )
                    {
                        const float x = TimeToX( track->Start( item ) );
                        if( x >= m_contentMin.x && x <= m_contentMax.x )
                        {
                            inDrawList->AddLine( { x, top + 4.f }, { x, top + row.Height - 4.f }, WithAlpha( track->Color, 0x90 ) );
                        }
                    }
                }
            }
            continue;
        }
        if( stripe++ % 2 == 1 )
        {
            inDrawList->AddRectFilled( { m_contentMin.x, top }, { m_contentMax.x, top + row.Height }, 0x08FFFFFF );
        }
        if( mouseInside && mouseY >= top && mouseY < top + row.Height )
        {
            inDrawList->AddRectFilled( { m_contentMin.x, top }, { m_contentMax.x, top + row.Height }, 0x0CFFFFFF );
        }
    }
}


void TimelineView::DrawGrid( const ChartDocument& inDocument, ImDrawList* inDrawList )
{
    const TrackData& chart = inDocument.Chart;
    const float bpm = static_cast<float>( chart.m_bpm );
    const double start = std::max( 0.0, XToTime( m_contentMin.x ) );
    const double end = XToTime( m_contentMax.x );
    // As fine as the snap while the lines stay apart; coarser as the view zooms out.
    const double middle = ( start + end ) * 0.5;
    const double beat = BeatGrid::BeatOfTime( chart.m_beats, bpm, middle );
    const float beatWidth = static_cast<float>( BeatGrid::TimeOfBeat( chart.m_beats, bpm, beat + 1.0 ) - BeatGrid::TimeOfBeat( chart.m_beats, bpm, beat ) ) * PixelsPerSecond;
    if( beatWidth * 4.f < 6.f )
    {
        return;
    }
    const int division = beatWidth / static_cast<float>( SnapDivision ) >= 7.f ? SnapDivision : 1;
    const bool beatLines = beatWidth >= 7.f;
    static std::vector<BeatGrid::Line> lines;
    BeatGrid::GridLines( chart.m_beats, bpm, start, end, division, lines );
    const float top = m_contentMin.y;
    const float bottom = std::min( m_contentMax.y, m_contentMin.y + m_rowsHeight - ScrollY );
    for( const BeatGrid::Line& line : lines )
    {
        if( line.Level > 0 && !beatLines )
        {
            continue;
        }
        const float x = TimeToX( line.Time );
        inDrawList->AddLine( { x, top }, { x, bottom }, line.Level == 0 ? 0x58FFFFFF : line.Level == 1 ? 0x26FFFFFF : 0x10FFFFFF );
    }
}


void TimelineView::DrawItems( const ChartDocument& inDocument, ImDrawList* inDrawList )
{
    for( int trackIndex = 0; trackIndex < inDocument.TrackCount(); ++trackIndex )
    {
        const IEventTrack& track = *inDocument.Tracks[trackIndex];
        const size_t group = static_cast<size_t>( track.Group );
        if( Hidden[group] || Collapsed[group] )
        {
            continue;
        }
        const bool notes = track.Group == TrackGroup::Notes;
        for( int item = 0; item < track.Count(); ++item )
        {
            const float x = TimeToX( track.Start( item ) );
            if( x > m_contentMax.x || ( !track.Spans && x < m_contentMin.x - 300.f ) || ( track.Spans && TimeToX( track.End( item ) ) < m_contentMin.x ) )
            {
                continue;
            }
            ImVec2 min, max;
            if( !ItemBox( inDocument, trackIndex, item, min, max ) || max.y < m_contentMin.y || min.y > m_contentMax.y )
            {
                continue;
            }
            const bool selected = inDocument.IsSelected( trackIndex, item );
            const ImU32 color = track.ItemColor( item );
            if( track.Spans )
            {
                inDrawList->AddRectFilled( min, max, WithAlpha( color, selected ? 0xB0 : 0x70 ), 2.f );
                inDrawList->AddRect( min, max, selected ? kSelected : color, 2.f, 0, selected ? 2.f : 1.f );
            }
            else if( notes )
            {
                inDrawList->AddRectFilled( min, max, color, 2.f );
                const NoteData& note = inDocument.Chart.m_noteData[item];
                if( note.m_velocity >= 120 )
                {
                    // An accent: a white cap.
                    inDrawList->AddRectFilled( min, { max.x, min.y + 3.f }, 0xFFFFFFFF );
                }
                const std::string label = track.Label( item );
                if( !label.empty() && max.x - min.x >= 8.f )
                {
                    inDrawList->AddText( { min.x + 1.f, min.y }, 0xFF000000, label.c_str() );
                }
                if( selected )
                {
                    inDrawList->AddRect( { min.x - 1.f, min.y - 1.f }, { max.x + 1.f, max.y + 1.f }, kSelected, 2.f, 0, 2.f );
                }
            }
            else
            {
                const float marker = PointWidth( track );
                if( selected )
                {
                    inDrawList->AddRectFilled( min, max, 0x40FFFFFF, 2.f );
                    inDrawList->AddRect( min, max, kSelected, 2.f );
                }
                inDrawList->AddRectFilled( min, { min.x + marker, max.y }, color, 1.f );
                const std::string label = track.Label( item );
                if( !label.empty() && max.x - min.x > marker + 8.f )
                {
                    inDrawList->PushClipRect( { std::max( min.x, m_contentMin.x ), std::max( min.y, m_contentMin.y ) }, { std::min( max.x, m_contentMax.x ), std::min( max.y + 2.f, m_contentMax.y ) }, false );
                    inDrawList->AddText( { min.x + marker + 3.f, min.y - 1.f }, selected ? kSelected : kText, label.c_str() );
                    inDrawList->PopClipRect();
                }
            }
        }
    }
}


void TimelineView::DrawRuler( const ChartDocument& inDocument, const Transport& inTransport, ImDrawList* inDrawList )
{
    const TrackData& chart = inDocument.Chart;
    const float bpm = static_cast<float>( chart.m_bpm );
    const float split = m_min.y + kRuler * 0.5f;
    inDrawList->AddRectFilled( { m_min.x, m_min.y }, { m_max.x, m_contentMin.y }, kGutterFill );
    inDrawList->AddText( { m_min.x + 6.f, m_min.y + 2.f }, kTextDim, "Measure" );
    inDrawList->AddText( { m_min.x + 6.f, split + 1.f }, kTextDim, "Section" );

    inDrawList->PushClipRect( { m_contentMin.x, m_min.y }, { m_max.x, m_contentMin.y }, true );

    // Measure numbers.
    if( m_measureVersion != inDocument.Version( ChartDomain::Beats ) || m_measureCount.size() != chart.m_beats.size() )
    {
        m_measureVersion = inDocument.Version( ChartDomain::Beats );
        m_measureCount.resize( chart.m_beats.size() );
        int count = 0;
        for( size_t i = 0; i < chart.m_beats.size(); ++i )
        {
            count += chart.m_beats[i].m_measure ? 1 : 0;
            m_measureCount[i] = count;
        }
    }
    static std::vector<BeatGrid::Line> lines;
    BeatGrid::GridLines( chart.m_beats, bpm, std::max( 0.0, XToTime( m_contentMin.x ) ), XToTime( m_max.x ), 1, lines );
    float lastLabel = -1000.f;
    for( const BeatGrid::Line& line : lines )
    {
        if( line.Level != 0 )
        {
            continue;
        }
        const float x = TimeToX( line.Time );
        if( x - lastLabel < 34.f )
        {
            continue;
        }
        lastLabel = x;
        const long long beat = std::llround( BeatGrid::BeatOfTime( chart.m_beats, bpm, line.Time ) );
        int measure = static_cast<int>( beat / 4 ) + 1;
        if( chart.m_beats.size() >= 2 && beat >= 0 && beat < static_cast<long long>( m_measureCount.size() ) )
        {
            measure = m_measureCount[static_cast<size_t>( beat )];
        }
        char text[16];
        snprintf( text, sizeof( text ), "%d", measure );
        inDrawList->AddLine( { x, split - 5.f }, { x, split }, kTextDim );
        inDrawList->AddText( { x + 3.f, m_min.y + 2.f }, kText, text );
    }

    // The song's sections, each to the next.
    const std::vector<TimedCueData>& sections = chart.m_venue.m_sections;
    for( size_t i = 0; i < sections.size(); ++i )
    {
        const float x0 = TimeToX( sections[i].m_time );
        const float x1 = TimeToX( i + 1 < sections.size() ? sections[i + 1].m_time : m_duration );
        if( x1 < m_contentMin.x || x0 > m_max.x )
        {
            continue;
        }
        inDrawList->AddRectFilled( { x0, split + 1.f }, { x1 - 1.f, m_contentMin.y - 1.f }, i % 2 == 0 ? 0xFF3C3A34 : 0xFF34373C );
        inDrawList->PushClipRect( { std::max( x0, m_contentMin.x ), split }, { std::min( x1 - 2.f, m_max.x ), m_contentMin.y }, true );
        inDrawList->AddText( { std::max( x0, m_contentMin.x ) + 4.f, split + 1.f }, kText, sections[i].m_name.c_str() );
        inDrawList->PopClipRect();
    }

    // The loop zone: a bar along the top, between its two edges.
    if( inTransport.HasLoop() )
    {
        const ImU32 color = inTransport.IsLooping() ? kLoop : kLoopOff;
        const float x0 = TimeToX( inTransport.LoopStart() );
        const float x1 = TimeToX( inTransport.LoopEnd() );
        inDrawList->AddRectFilled( { x0, m_min.y }, { x1, split }, WithAlpha( color, 0x28 ) );
        inDrawList->AddRectFilled( { x0, m_min.y }, { x1, m_min.y + 3.f }, color );
        inDrawList->AddLine( { x0, m_min.y }, { x0, m_contentMin.y }, color, 2.f );
        inDrawList->AddLine( { x1, m_min.y }, { x1, m_contentMin.y }, color, 2.f );
    }

    // The song-select preview's start, and the playhead.
    if( chart.m_previewPercent > 0.f )
    {
        const float x = TimeToX( inTransport.Length() * chart.m_previewPercent );
        inDrawList->AddLine( { x, m_min.y }, { x, m_contentMin.y }, 0xFFF040F0, 2.f );
    }
    const float playheadX = TimeToX( inTransport.Seconds() );
    inDrawList->AddTriangleFilled( { playheadX - 6.f, m_min.y }, { playheadX + 6.f, m_min.y }, { playheadX, m_min.y + 9.f }, kPlayhead );
    inDrawList->AddLine( { playheadX, m_min.y }, { playheadX, m_contentMin.y }, kPlayhead, 1.5f );
    inDrawList->PopClipRect();
    inDrawList->AddLine( { m_min.x, m_contentMin.y }, { m_max.x, m_contentMin.y }, 0xFF3A3A3E );
}


void TimelineView::DrawGutter( const ChartDocument& inDocument, ImDrawList* inDrawList )
{
    inDrawList->PushClipRect( { m_min.x, m_contentMin.y }, { m_contentMin.x, m_contentMax.y }, true );
    inDrawList->AddRectFilled( { m_min.x, m_contentMin.y }, { m_contentMin.x, m_contentMax.y }, kGutterFill );
    for( const Row& row : m_rows )
    {
        const float top = RowTop( row );
        if( top > m_contentMax.y || top + row.Height < m_contentMin.y )
        {
            continue;
        }
        const float textY = top + ( row.Height - ImGui::GetFontSize() ) * 0.5f;
        if( row.Track < 0 )
        {
            inDrawList->AddRectFilled( { m_min.x, top }, { m_contentMin.x, top + row.Height }, kHeaderFill );
            const bool folded = Collapsed[static_cast<size_t>( row.Group )];
            const ImVec2 centre = { m_min.x + 10.f, top + row.Height * 0.5f };
            if( folded )
            {
                inDrawList->AddTriangleFilled( { centre.x - 3.f, centre.y - 4.f }, { centre.x - 3.f, centre.y + 4.f }, { centre.x + 4.f, centre.y }, kText );
            }
            else
            {
                inDrawList->AddTriangleFilled( { centre.x - 4.f, centre.y - 3.f }, { centre.x + 4.f, centre.y - 3.f }, { centre.x, centre.y + 4.f }, kText );
            }
            inDrawList->AddText( { m_min.x + 20.f, textY }, kText, TrackGroupName( row.Group ) );
            continue;
        }
        const IEventTrack& track = *inDocument.Tracks[row.Track];
        if( track.Group == TrackGroup::Notes )
        {
            const ImU32 color = static_cast<ImU32>( PadUtils::GetNoteColorABGR( static_cast<PadId>( row.TrackRow ) ) );
            inDrawList->AddRectFilled( { m_min.x + 6.f, top + 4.f }, { m_min.x + 10.f, top + row.Height - 4.f }, color );
            inDrawList->AddText( { m_min.x + 16.f, textY }, kText, track.RowNames[row.TrackRow].c_str() );
        }
        else
        {
            inDrawList->AddRectFilled( { m_min.x + 6.f, top + 4.f }, { m_min.x + 10.f, top + row.Height - 4.f }, track.Color );
            if( row.TrackRow == 0 )
            {
                inDrawList->AddText( { m_min.x + 16.f, textY }, kText, track.Name.c_str() );
            }
            if( track.Rows() > 1 )
            {
                const char* name = track.RowNames[row.TrackRow].c_str();
                inDrawList->AddText( { m_contentMin.x - ImGui::CalcTextSize( name ).x - 6.f, textY }, kTextDim, name );
            }
        }
    }
    inDrawList->PopClipRect();
    inDrawList->AddLine( { m_contentMin.x, m_min.y }, { m_contentMin.x, m_contentMax.y }, 0xFF3A3A3E );
}


void TimelineView::DrawOverview( const ChartDocument& inDocument, const Transport& inTransport, ImDrawList* inDrawList )
{
    const float left = m_contentMin.x;
    const float width = m_max.x - left;
    const float top = m_contentMax.y;
    inDrawList->AddRectFilled( { m_min.x, top }, { m_max.x, m_max.y }, kGutterFill );
    const auto x = [&]( double inSeconds ) { return left + static_cast<float>( std::clamp( inSeconds / m_duration, 0.0, 1.0 ) ) * width; };
    for( const TimedCueData& section : inDocument.Chart.m_venue.m_sections )
    {
        inDrawList->AddLine( { x( section.m_time ), top + 2.f }, { x( section.m_time ), m_max.y - 2.f }, 0xFF606060 );
    }
    const double span = static_cast<double>( m_contentMax.x - m_contentMin.x ) / PixelsPerSecond;
    inDrawList->AddRectFilled( { x( ViewStart ), top + 2.f }, { std::max( x( ViewStart ) + 3.f, x( ViewStart + span ) ), m_max.y - 2.f }, 0x60FFFFFF, 2.f );
    if( inTransport.HasLoop() )
    {
        inDrawList->AddRectFilled( { x( inTransport.LoopStart() ), m_max.y - 3.f }, { std::max( x( inTransport.LoopStart() ) + 2.f, x( inTransport.LoopEnd() ) ), m_max.y - 1.f }, inTransport.IsLooping() ? kLoop : kLoopOff );
    }
    inDrawList->AddLine( { x( inTransport.Seconds() ), top }, { x( inTransport.Seconds() ), m_max.y }, kPlayhead );
}


void TimelineView::BeginItemDrag( ChartDocument& inDocument, ChartItemRef inRef, Edge inEdge )
{
    m_anchor = inRef;
    m_dragItems.clear();
    if( inEdge != Edge::None )
    {
        // Resizing takes the one span.
        inDocument.Selection.clear();
        inDocument.Selection.insert( inRef );
        m_collapseOnRelease = false;
    }
    for( const ChartItemRef& ref : inDocument.Selection )
    {
        const IEventTrack& track = *inDocument.Tracks[ref.Track];
        if( ref.Item < track.Count() )
        {
            m_dragItems.push_back( { ref, track.Start( ref.Item ), track.End( ref.Item ), track.Row( ref.Item ) } );
        }
    }
    const IEventTrack& track = *inDocument.Tracks[inRef.Track];
    m_anchorItem = { inRef, track.Start( inRef.Item ), track.End( inRef.Item ), track.Row( inRef.Item ) };
    m_gesture = Gesture::PendingMove;
    m_pendingEdge = inEdge;
}


void TimelineView::UpdateItemDrag( ChartDocument& inDocument )
{
    const ImGuiIO& io = ImGui::GetIO();
    const IEventTrack& anchorTrack = *inDocument.Tracks[m_anchor.Track];
    // The beats are the grid; they move freely.
    const bool bypass = io.KeyAlt || anchorTrack.Domain == ChartDomain::Beats;
    const double moved = XToTime( io.MousePos.x ) - m_pressTime;

    if( m_gesture == Gesture::ResizeStart || m_gesture == Gesture::ResizeEnd )
    {
        IEventTrack& track = *inDocument.Tracks[m_anchor.Track];
        if( m_gesture == Gesture::ResizeStart )
        {
            const double start = std::min( SnapTime( inDocument, m_anchorItem.Start + moved, bypass ), m_anchorItem.End - kMinSpan );
            track.Set( m_anchor.Item, start, m_anchorItem.End, m_anchorItem.Row );
        }
        else
        {
            const double end = std::max( SnapTime( inDocument, m_anchorItem.End + moved, bypass ), m_anchorItem.Start + kMinSpan );
            track.Set( m_anchor.Item, m_anchorItem.Start, end, m_anchorItem.Row );
        }
        return;
    }

    // The grabbed item lands on the grid; the rest keep their distance from it.
    double delta = SnapTime( inDocument, m_anchorItem.Start + moved, bypass ) - m_anchorItem.Start;
    int rows = 0;
    const int rowIndex = RowAt( io.MousePos.y );
    if( rowIndex >= 0 && m_rows[rowIndex].Track == m_anchor.Track )
    {
        rows = m_rows[rowIndex].TrackRow - m_anchorItem.Row;
    }
    for( const DragItem& item : m_dragItems )
    {
        delta = std::max( delta, -item.Start );
        const int trackRows = inDocument.Tracks[item.Ref.Track]->Rows();
        if( trackRows > 1 )
        {
            rows = std::clamp( rows, -item.Row, trackRows - 1 - item.Row );
        }
    }
    for( const DragItem& item : m_dragItems )
    {
        IEventTrack& track = *inDocument.Tracks[item.Ref.Track];
        track.Set( item.Ref.Item, item.Start + delta, item.End + delta, item.Row + ( track.Rows() > 1 ? rows : 0 ) );
    }
}


void TimelineView::UpdateBox( ChartDocument& inDocument )
{
    const ImVec2 mouse = ImGui::GetIO().MousePos;
    const double t0 = XToTime( std::min( m_pressPos.x, mouse.x ) );
    const double t1 = XToTime( std::max( m_pressPos.x, mouse.x ) );
    const float y0 = std::min( m_pressPos.y, mouse.y );
    const float y1 = std::max( m_pressPos.y, mouse.y );
    inDocument.Selection = m_boxBase;
    for( const Row& row : m_rows )
    {
        const float top = RowTop( row );
        if( row.Track < 0 || top > y1 || top + row.Height < y0 )
        {
            continue;
        }
        const IEventTrack& track = *inDocument.Tracks[row.Track];
        for( int item = 0; item < track.Count(); ++item )
        {
            if( track.Rows() > 1 && track.Row( item ) != row.TrackRow )
            {
                continue;
            }
            if( track.Start( item ) <= t1 && std::max( track.End( item ), track.Start( item ) ) >= t0 )
            {
                inDocument.Selection.insert( { row.Track, item } );
            }
        }
    }
}


void TimelineView::HandleInput( ChartDocument& inDocument, Transport& inTransport, bool inHovered )
{
    ImGuiIO& io = ImGui::GetIO();
    const ImVec2 mouse = io.MousePos;
    const bool inRuler = mouse.y < m_contentMin.y && mouse.x >= m_contentMin.x;
    const bool inOverview = mouse.y >= m_contentMax.y;
    const bool inGutter = !inOverview && mouse.x < m_contentMin.x && mouse.y >= m_contentMin.y;
    const bool inContent = !inRuler && !inOverview && !inGutter && mouse.y >= m_contentMin.y;

    if( inHovered && io.MouseWheel != 0.f )
    {
        if( io.KeyCtrl || inGutter )
        {
            ScrollY -= io.MouseWheel * 40.f;
        }
        else if( io.KeyShift )
        {
            ViewStart -= static_cast<double>( io.MouseWheel ) * 80.0 / PixelsPerSecond;
        }
        else
        {
            // Zoom about the pointer.
            const double anchor = XToTime( mouse.x );
            PixelsPerSecond = std::clamp( PixelsPerSecond * std::pow( 1.15f, io.MouseWheel ), 2.f, 3000.f );
            ViewStart = anchor - static_cast<double>( mouse.x - m_contentMin.x ) / PixelsPerSecond;
        }
    }
    if( inHovered && io.MouseWheelH != 0.f )
    {
        ViewStart -= static_cast<double>( io.MouseWheelH ) * 80.0 / PixelsPerSecond;
    }

    // A gesture in progress.
    switch( m_gesture )
    {
    case Gesture::Scrub:
        if( ImGui::IsMouseDown( ImGuiMouseButton_Left ) )
        {
            inTransport.Seek( SnapTime( inDocument, XToTime( mouse.x ), !io.KeyShift ) );
        }
        else
        {
            m_gesture = Gesture::None;
        }
        return;
    case Gesture::Loop:
        if( ImGui::IsMouseDown( ImGuiMouseButton_Left ) )
        {
            ImGui::SetMouseCursor( ImGuiMouseCursor_ResizeEW );
            m_loopMoved = m_loopMoved || std::abs( mouse.x - m_pressPos.x ) > kDragThreshold;
            const double time = SnapTime( inDocument, XToTime( mouse.x ), io.KeyAlt );
            if( m_loopMoved && std::abs( time - m_loopAnchor ) >= Transport::kMinLoop )
            {
                inTransport.SetLoop( m_loopAnchor, time );
                if( m_loopStaysOff )
                {
                    inTransport.SetLooping( false );
                }
            }
        }
        else
        {
            m_gesture = Gesture::None;
        }
        return;
    case Gesture::Pan:
        if( ImGui::IsMouseDown( ImGuiMouseButton_Middle ) )
        {
            ViewStart -= static_cast<double>( io.MouseDelta.x ) / PixelsPerSecond;
            ScrollY -= io.MouseDelta.y;
        }
        else
        {
            m_gesture = Gesture::None;
        }
        return;
    case Gesture::Overview:
        if( ImGui::IsMouseDown( ImGuiMouseButton_Left ) )
        {
            const double span = static_cast<double>( m_contentMax.x - m_contentMin.x ) / PixelsPerSecond;
            ViewStart = static_cast<double>( mouse.x - m_contentMin.x ) / static_cast<double>( m_max.x - m_contentMin.x ) * m_duration - span * 0.5;
        }
        else
        {
            m_gesture = Gesture::None;
        }
        return;
    case Gesture::Box:
        if( ImGui::IsMouseDown( ImGuiMouseButton_Left ) )
        {
            UpdateBox( inDocument );
        }
        else
        {
            // A click on empty timeline puts the playhead there.
            if( std::abs( mouse.x - m_pressPos.x ) < kDragThreshold && std::abs( mouse.y - m_pressPos.y ) < kDragThreshold )
            {
                inTransport.Seek( SnapTime( inDocument, XToTime( mouse.x ), io.KeyAlt ) );
            }
            m_gesture = Gesture::None;
        }
        return;
    case Gesture::PendingMove:
        if( !ImGui::IsMouseDown( ImGuiMouseButton_Left ) )
        {
            if( m_collapseOnRelease )
            {
                inDocument.Selection.clear();
                inDocument.Selection.insert( m_anchor );
            }
            m_gesture = Gesture::None;
        }
        else if( std::abs( mouse.x - m_pressPos.x ) > kDragThreshold || std::abs( mouse.y - m_pressPos.y ) > kDragThreshold )
        {
            for( const DragItem& item : m_dragItems )
            {
                inDocument.BeginEdit( item.Ref.Track );
            }
            m_gesture = m_pendingEdge == Edge::Start ? Gesture::ResizeStart : m_pendingEdge == Edge::End ? Gesture::ResizeEnd : Gesture::Move;
        }
        return;
    case Gesture::Move:
    case Gesture::ResizeStart:
    case Gesture::ResizeEnd:
        if( ImGui::IsKeyPressed( ImGuiKey_Escape ) )
        {
            inDocument.CancelEdit();
            m_gesture = Gesture::None;
        }
        else if( ImGui::IsMouseDown( ImGuiMouseButton_Left ) )
        {
            UpdateItemDrag( inDocument );
            ImGui::SetMouseCursor( m_gesture == Gesture::Move ? ImGuiMouseCursor_ResizeAll : ImGuiMouseCursor_ResizeEW );
        }
        else
        {
            inDocument.CommitEdit( m_gesture == Gesture::Move ? "Move" : "Resize" );
            m_gesture = Gesture::None;
        }
        return;
    default:
        break;
    }

    if( !inHovered )
    {
        return;
    }

    ChartItemRef hit;
    Edge edge = Edge::None;
    const bool onItem = inContent && HitTest( inDocument, mouse, hit, edge );
    if( onItem && edge != Edge::None )
    {
        ImGui::SetMouseCursor( ImGuiMouseCursor_ResizeEW );
    }
    if( onItem && !ImGui::IsAnyMouseDown() )
    {
        const IEventTrack& track = *inDocument.Tracks[hit.Track];
        const std::string label = track.Label( hit.Item );
        if( track.Spans )
        {
            ImGui::SetTooltip( "%s  %.3f - %.3f s", track.Name.c_str(), track.Start( hit.Item ), track.End( hit.Item ) );
        }
        else
        {
            ImGui::SetTooltip( "%s%s%s  %.3f s", track.Group == TrackGroup::Notes ? track.RowNames[track.Row( hit.Item )].c_str() : track.Name.c_str(), label.empty() ? "" : ": ", label.c_str(), track.Start( hit.Item ) );
        }
    }

    // An edge of the loop zone, in the ruler: it drags.
    Edge loopEdge = Edge::None;
    if( inRuler && inTransport.HasLoop() )
    {
        const float toStart = std::abs( mouse.x - TimeToX( inTransport.LoopStart() ) );
        const float toEnd = std::abs( mouse.x - TimeToX( inTransport.LoopEnd() ) );
        if( std::min( toStart, toEnd ) <= kLoopEdgeGrab )
        {
            loopEdge = toStart < toEnd ? Edge::Start : Edge::End;
            ImGui::SetMouseCursor( ImGuiMouseCursor_ResizeEW );
        }
    }

    if( ImGui::IsMouseClicked( ImGuiMouseButton_Middle ) )
    {
        m_gesture = Gesture::Pan;
        return;
    }

    if( ImGui::IsMouseClicked( ImGuiMouseButton_Right ) && inRuler )
    {
        m_contextTime = XToTime( mouse.x );
        ImGui::OpenPopup( "##ruler-context" );
        return;
    }

    if( ImGui::IsMouseClicked( ImGuiMouseButton_Right ) && inContent )
    {
        if( onItem && !inDocument.IsSelected( hit.Track, hit.Item ) )
        {
            inDocument.Selection.clear();
            inDocument.Selection.insert( hit );
        }
        m_contextTime = XToTime( mouse.x );
        m_contextRow = RowAt( mouse.y );
        ImGui::OpenPopup( "##chart-context" );
        return;
    }

    if( ImGui::IsMouseDoubleClicked( ImGuiMouseButton_Left ) && inContent )
    {
        if( onItem )
        {
            // Double-click removes, as it always has here.
            inDocument.Selection.clear();
            inDocument.Selection.insert( hit );
            inDocument.DeleteSelection();
        }
        else
        {
            const int rowIndex = RowAt( mouse.y );
            if( rowIndex >= 0 && m_rows[rowIndex].Track >= 0 )
            {
                const Row& row = m_rows[rowIndex];
                const IEventTrack& track = *inDocument.Tracks[row.Track];
                const bool bypass = io.KeyAlt || track.Domain == ChartDomain::Beats;
                const double start = SnapTime( inDocument, XToTime( mouse.x ), bypass );
                double end = start;
                if( track.Spans )
                {
                    // A measure of 4/4 to start with.
                    const float bpm = static_cast<float>( inDocument.Chart.m_bpm );
                    end = BeatGrid::TimeOfBeat( inDocument.Chart.m_beats, bpm, BeatGrid::BeatOfTime( inDocument.Chart.m_beats, bpm, start ) + 4.0 );
                }
                inDocument.AddItem( row.Track, start, end, row.TrackRow );
            }
        }
        m_gesture = Gesture::None;
        return;
    }

    if( !ImGui::IsMouseClicked( ImGuiMouseButton_Left ) )
    {
        return;
    }
    m_pressPos = mouse;
    m_pressTime = XToTime( mouse.x );
    if( inRuler && ( loopEdge != Edge::None || io.KeyCtrl ) )
    {
        // Ctrl-drag marks out a new loop zone; an edge of the one there moves.
        m_gesture = Gesture::Loop;
        m_loopMoved = false;
        m_loopStaysOff = loopEdge != Edge::None && !inTransport.IsLooping();
        m_loopAnchor = loopEdge == Edge::Start ? inTransport.LoopEnd() : loopEdge == Edge::End ? inTransport.LoopStart() : SnapTime( inDocument, m_pressTime, io.KeyAlt );
    }
    else if( inRuler )
    {
        m_gesture = Gesture::Scrub;
        inTransport.Seek( SnapTime( inDocument, m_pressTime, !io.KeyShift ) );
    }
    else if( inOverview )
    {
        m_gesture = Gesture::Overview;
    }
    else if( inGutter )
    {
        const int rowIndex = RowAt( mouse.y );
        if( rowIndex >= 0 && m_rows[rowIndex].Track < 0 )
        {
            bool& folded = Collapsed[static_cast<size_t>( m_rows[rowIndex].Group )];
            folded = !folded;
        }
    }
    else if( onItem )
    {
        m_collapseOnRelease = false;
        const bool selected = inDocument.IsSelected( hit.Track, hit.Item );
        if( io.KeyCtrl )
        {
            if( selected )
            {
                inDocument.Selection.erase( hit );
                return;
            }
            inDocument.Selection.insert( hit );
        }
        else if( io.KeyShift )
        {
            inDocument.Selection.insert( hit );
        }
        else if( !selected )
        {
            inDocument.Selection.clear();
            inDocument.Selection.insert( hit );
        }
        else
        {
            m_collapseOnRelease = inDocument.Selection.size() > 1;
        }
        BeginItemDrag( inDocument, hit, edge );
    }
    else if( inContent )
    {
        if( !io.KeyCtrl && !io.KeyShift )
        {
            inDocument.Selection.clear();
        }
        m_boxBase = inDocument.Selection;
        m_gesture = Gesture::Box;
    }
}


void TimelineView::DrawContextMenu( ChartDocument& inDocument, Transport& inTransport )
{
    if( !ImGui::BeginPopup( "##chart-context" ) )
    {
        return;
    }
    const bool any = !inDocument.Selection.empty();
    if( ImGui::MenuItem( "Cut", nullptr, false, any ) ) inDocument.Cut();
    if( ImGui::MenuItem( "Copy", nullptr, false, any ) ) inDocument.Copy();
    if( ImGui::MenuItem( "Paste Here", nullptr, false, inDocument.CanPaste() ) ) inDocument.Paste( SnapTime( inDocument, m_contextTime ) );
    if( ImGui::MenuItem( "Duplicate", nullptr, false, any ) ) inDocument.Duplicate();
    if( ImGui::MenuItem( "Snap to Grid", nullptr, false, any ) ) inDocument.SnapSelection( SnapDivision );
    if( ImGui::MenuItem( "Delete", nullptr, false, any ) ) inDocument.DeleteSelection();
    ImGui::Separator();
    if( m_contextRow >= 0 && m_contextRow < static_cast<int>( m_rows.size() ) && m_rows[m_contextRow].Track >= 0 )
    {
        const Row& row = m_rows[m_contextRow];
        const IEventTrack& track = *inDocument.Tracks[row.Track];
        const std::string label = "Add " + ( track.Group == TrackGroup::Notes ? track.RowNames[row.TrackRow] + " Note" : track.Name ) + " Here";
        if( ImGui::MenuItem( label.c_str() ) )
        {
            const double start = SnapTime( inDocument, m_contextTime, track.Domain == ChartDomain::Beats );
            const float bpm = static_cast<float>( inDocument.Chart.m_bpm );
            const double end = track.Spans ? BeatGrid::TimeOfBeat( inDocument.Chart.m_beats, bpm, BeatGrid::BeatOfTime( inDocument.Chart.m_beats, bpm, start ) + 4.0 ) : start;
            inDocument.AddItem( row.Track, start, end, row.TrackRow );
        }
    }
    if( ImGui::MenuItem( "Move Playhead Here" ) ) inTransport.Seek( SnapTime( inDocument, m_contextTime ) );
    double loopStart = 0.0;
    double loopEnd = 0.0;
    if( ImGui::MenuItem( "Loop Selection", nullptr, false, any ) && inDocument.SelectionSpan( loopStart, loopEnd ) )
    {
        inTransport.SetLoop( loopStart, loopEnd );
    }
    ImGui::EndPopup();
}


void TimelineView::DrawRulerMenu( const ChartDocument& inDocument, Transport& inTransport )
{
    if( !ImGui::BeginPopup( "##ruler-context" ) )
    {
        return;
    }
    const double time = std::clamp( SnapTime( inDocument, m_contextTime ), 0.0, m_duration );
    const bool has = inTransport.HasLoop();
    if( ImGui::MenuItem( "Loop Starts Here" ) )
    {
        inTransport.SetLoop( time, has && inTransport.LoopEnd() > time ? inTransport.LoopEnd() : m_duration );
    }
    if( ImGui::MenuItem( "Loop Ends Here" ) )
    {
        inTransport.SetLoop( has && inTransport.LoopStart() < time ? inTransport.LoopStart() : 0.0, time );
    }
    // The section under the pointer, to the next one.
    const std::vector<TimedCueData>& sections = inDocument.Chart.m_venue.m_sections;
    int section = -1;
    for( size_t i = 0; i < sections.size() && sections[i].m_time <= m_contextTime; ++i )
    {
        section = static_cast<int>( i );
    }
    if( ImGui::MenuItem( "Loop This Section", nullptr, false, section >= 0 ) )
    {
        inTransport.SetLoop( sections[section].m_time, section + 1 < static_cast<int>( sections.size() ) ? sections[section + 1].m_time : m_duration );
    }
    double start = 0.0;
    double end = 0.0;
    if( ImGui::MenuItem( "Loop Selection", nullptr, false, !inDocument.Selection.empty() ) && inDocument.SelectionSpan( start, end ) )
    {
        inTransport.SetLoop( start, end );
    }
    ImGui::Separator();
    bool looping = inTransport.IsLooping();
    if( ImGui::MenuItem( "Loop", "L", &looping, has ) )
    {
        inTransport.SetLooping( looping );
    }
    if( ImGui::MenuItem( "Clear Loop", nullptr, false, has ) )
    {
        inTransport.ClearLoop();
    }
    if( ImGui::MenuItem( "Move Playhead Here" ) ) inTransport.Seek( time );
    ImGui::EndPopup();
}

#endif
