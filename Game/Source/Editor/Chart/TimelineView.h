#pragma once
#include "Dementia.h"
#include "Editor/Chart/ChartDocument.h"
#include <imgui.h>
#include <array>
#include <set>
#include <vector>

#if USING( ME_EDITOR )

class Transport;

// The Track Editor's timeline: every track of a ChartDocument as rows against time, with the beat
// grid, a ruler to scrub on and the gestures that edit (Docs/Songs-and-DLC.md lists them).
class TimelineView
{
public:
    TimelineView();

    // Fills inSize (0 = what's left of the window).
    void Draw( ChartDocument& inDocument, Transport& inTransport, ImVec2 inSize );

    // inSeconds on the grid when snapping is on (and inBypass, the Alt key, isn't held).
    double SnapTime( const ChartDocument& inDocument, double inSeconds, bool inBypass = false ) const;
    // The tracks drawn as rows right now (Select All takes these).
    std::vector<int> VisibleTracks( const ChartDocument& inDocument ) const;
    // Scrolls so inSeconds is in view.
    void Reveal( double inSeconds );
    void ZoomToFit( const ChartDocument& inDocument );
    bool HasGesture() const { return m_gesture != Gesture::None; }

    bool SnapEnabled = true;
    // Grid steps per beat: 1 quarter notes in 4/4, 2 eighths, 3 triplets, 4 sixteenths, ...
    int SnapDivision = 4;
    // Keep the playhead in view while playing.
    bool Follow = true;
    float NoteRowHeight = 20.f;
    float PixelsPerSecond = 120.f;
    double ViewStart = 0.0;
    float ScrollY = 0.f;
    std::array<bool, static_cast<size_t>( TrackGroup::Count )> Collapsed{};
    std::array<bool, static_cast<size_t>( TrackGroup::Count )> Hidden{};

private:
    enum class Gesture { None, Scrub, Pan, Box, PendingMove, Move, ResizeStart, ResizeEnd, Overview, Loop };
    enum class Edge { None, Start, End };

    struct Row
    {
        int Track = -1;     // -1: a group's header
        int TrackRow = 0;
        TrackGroup Group = TrackGroup::Notes;
        float Y = 0.f;      // from the top of the rows, unscrolled
        float Height = 0.f;
    };

    struct DragItem
    {
        ChartItemRef Ref;
        double Start = 0.0;
        double End = 0.0;
        int Row = 0;
    };

    void Layout( const ChartDocument& inDocument );
    float TimeToX( double inSeconds ) const { return m_contentMin.x + static_cast<float>( ( inSeconds - ViewStart ) * PixelsPerSecond ); }
    double XToTime( float inX ) const { return ViewStart + static_cast<double>( inX - m_contentMin.x ) / PixelsPerSecond; }
    float RowTop( const Row& inRow ) const { return m_contentMin.y + inRow.Y - ScrollY; }
    int RowAt( float inY ) const;
    int RowOf( int inTrack, int inTrackRow ) const;
    float PointWidth( const IEventTrack& inTrack ) const;
    // The item's box on screen; false when its row isn't drawn.
    bool ItemBox( const ChartDocument& inDocument, int inTrack, int inItem, ImVec2& outMin, ImVec2& outMax ) const;
    bool HitTest( const ChartDocument& inDocument, ImVec2 inPos, ChartItemRef& outRef, Edge& outEdge ) const;

    void DrawGrid( const ChartDocument& inDocument, ImDrawList* inDrawList );
    void DrawRows( const ChartDocument& inDocument, ImDrawList* inDrawList );
    void DrawItems( const ChartDocument& inDocument, ImDrawList* inDrawList );
    void DrawRuler( const ChartDocument& inDocument, const Transport& inTransport, ImDrawList* inDrawList );
    void DrawGutter( const ChartDocument& inDocument, ImDrawList* inDrawList );
    void DrawOverview( const ChartDocument& inDocument, const Transport& inTransport, ImDrawList* inDrawList );
    void HandleInput( ChartDocument& inDocument, Transport& inTransport, bool inHovered );
    void BeginItemDrag( ChartDocument& inDocument, ChartItemRef inRef, Edge inEdge );
    void UpdateItemDrag( ChartDocument& inDocument );
    void UpdateBox( ChartDocument& inDocument );
    void DrawContextMenu( ChartDocument& inDocument, Transport& inTransport );
    void DrawRulerMenu( const ChartDocument& inDocument, Transport& inTransport );
    void ClampView( const ChartDocument& inDocument );

    // This frame's layout.
    ImVec2 m_min, m_max;
    ImVec2 m_contentMin, m_contentMax;
    std::vector<Row> m_rows;
    float m_rowsHeight = 0.f;
    double m_duration = 1.0;

    Gesture m_gesture = Gesture::None;
    ImVec2 m_pressPos;
    double m_pressTime = 0.0;
    ChartItemRef m_anchor;
    std::vector<DragItem> m_dragItems;
    DragItem m_anchorItem;
    Edge m_pendingEdge = Edge::None;
    // A plain click on one of several selected items selects just it, unless it turns into a drag.
    bool m_collapseOnRelease = false;
    std::set<ChartItemRef> m_boxBase;
    // Dragging out the transport's loop zone: the end that stays put, and whether looping stays
    // off (an edge of a zone that is switched off).
    double m_loopAnchor = 0.0;
    bool m_loopMoved = false;
    bool m_loopStaysOff = false;
    // Right-click target: where a context-menu paste or add lands.
    double m_contextTime = 0.0;
    int m_contextRow = -1;

    // Measure numbers: how many measures start at or before each beat of the map.
    std::vector<int> m_measureCount;
    uint32_t m_measureVersion = 0;
};

#endif
