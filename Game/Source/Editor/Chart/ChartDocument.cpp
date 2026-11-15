#include "Editor/Chart/ChartDocument.h"
#include "CoreGame/BeatGrid.h"
#include <algorithm>
#include <cmath>

#if USING( ME_EDITOR )

// One undo step: the lists of the tracks it touched, before and after.
class ChartEditCommand final
    : public UndoCommand
{
public:
    struct Entry
    {
        int Track = 0;
        std::any Before;
        std::any After;
    };

    ChartEditCommand( ChartDocument& inDocument, std::string inName, std::vector<Entry> inEntries )
        : m_document( inDocument )
        , m_name( std::move( inName ) )
        , m_entries( std::move( inEntries ) )
    {
    }

    void Undo() override { Apply( false ); }
    void Redo() override { Apply( true ); }
    std::string GetName() const override { return m_name; }

private:
    void Apply( bool inAfter )
    {
        std::vector<int> tracks;
        for( const Entry& entry : m_entries )
        {
            m_document.Tracks[entry.Track]->Restore( inAfter ? entry.After : entry.Before );
            tracks.push_back( entry.Track );
        }
        m_document.OnHistoryApplied( tracks );
    }

    ChartDocument& m_document;
    std::string m_name;
    std::vector<Entry> m_entries;
};


ChartDocument::ChartDocument() = default;


ChartDocument::~ChartDocument() = default;


void ChartDocument::Open( const TrackData& inTrack )
{
    Close();
    Chart = inTrack;
    Chart.LoadNoteData();
    Rebind();
}


void ChartDocument::OpenInMemory( const TrackData& inTrack )
{
    Close();
    Chart = inTrack;
    Rebind();
}


void ChartDocument::Rebind()
{
    Tracks = EventTracks::Build( Chart );
    // Lists are kept in time order; older files and hand edits may not be.
    for( auto& track : Tracks )
    {
        std::vector<int> none;
        track->Sort( none );
    }
    m_open = true;
    for( uint32_t& version : m_versions )
    {
        ++version;
    }
}


void ChartDocument::Close()
{
    m_edit.clear();
    Selection.clear();
    History.Clear();
    History.MarkSaved();
    Tracks.clear();
    Chart = TrackData();
    MetaDirty = false;
    m_open = false;
}


void ChartDocument::Save()
{
    if( !m_open )
    {
        return;
    }
    if( HasOpenEdit() )
    {
        CommitEdit( "Edit" );
    }
    Chart.m_authored = true;
    Chart.m_noteCount = static_cast<int>( Chart.m_noteData.size() );
    Chart.Save();
    History.MarkSaved();
    MetaDirty = false;
}


int ChartDocument::FindTrack( const std::string& inName ) const
{
    for( int track = 0; track < TrackCount(); ++track )
    {
        if( Tracks[track]->Name == inName )
        {
            return track;
        }
    }
    return -1;
}


std::vector<int> ChartDocument::SelectedIn( int inTrack ) const
{
    std::vector<int> items;
    for( auto it = Selection.lower_bound( { inTrack, 0 } ); it != Selection.end() && it->Track == inTrack; ++it )
    {
        if( it->Item < Tracks[inTrack]->Count() )
        {
            items.push_back( it->Item );
        }
    }
    return items;
}


std::vector<int> ChartDocument::SelectedTracks() const
{
    std::vector<int> tracks;
    for( const ChartItemRef& ref : Selection )
    {
        if( tracks.empty() || tracks.back() != ref.Track )
        {
            tracks.push_back( ref.Track );
        }
    }
    return tracks;
}


void ChartDocument::SelectAll( const std::vector<int>& inTracks )
{
    Selection.clear();
    for( int track : inTracks )
    {
        for( int item = 0; item < Tracks[track]->Count(); ++item )
        {
            Selection.insert( { track, item } );
        }
    }
}


bool ChartDocument::SelectionSpan( double& outStart, double& outEnd ) const
{
    bool any = false;
    for( const ChartItemRef& ref : Selection )
    {
        const IEventTrack& track = *Tracks[ref.Track];
        const double start = track.Start( ref.Item );
        const double end = std::max( start, track.End( ref.Item ) );
        outStart = any ? std::min( outStart, start ) : start;
        outEnd = any ? std::max( outEnd, end ) : end;
        any = true;
    }
    return any;
}


void ChartDocument::BeginEdit( int inTrack )
{
    for( const OpenEdit& edit : m_edit )
    {
        if( edit.Track == inTrack )
        {
            return;
        }
    }
    m_edit.push_back( { inTrack, Tracks[inTrack]->Snapshot() } );
}


void ChartDocument::CommitEdit( const std::string& inName )
{
    if( m_edit.empty() )
    {
        return;
    }
    std::vector<ChartEditCommand::Entry> entries;
    for( OpenEdit& edit : m_edit )
    {
        // Back in time order, the selection following its items.
        std::vector<int> selected = SelectedIn( edit.Track );
        Selection.erase( Selection.lower_bound( { edit.Track, 0 } ), Selection.lower_bound( { edit.Track + 1, 0 } ) );
        Tracks[edit.Track]->Sort( selected );
        for( int item : selected )
        {
            Selection.insert( { edit.Track, item } );
        }
        entries.push_back( { edit.Track, std::move( edit.Before ), Tracks[edit.Track]->Snapshot() } );
        Touch( edit.Track );
    }
    m_edit.clear();
    History.Push( std::make_unique<ChartEditCommand>( *this, inName, std::move( entries ) ) );
}


void ChartDocument::CancelEdit()
{
    for( const OpenEdit& edit : m_edit )
    {
        Tracks[edit.Track]->Restore( edit.Before );
        Selection.erase( Selection.lower_bound( { edit.Track, Tracks[edit.Track]->Count() } ), Selection.lower_bound( { edit.Track + 1, 0 } ) );
        Touch( edit.Track );
    }
    m_edit.clear();
}


void ChartDocument::Touch( int inTrack )
{
    ++m_versions[static_cast<size_t>( Tracks[inTrack]->Domain )];
}


void ChartDocument::OnHistoryApplied( const std::vector<int>& inTracks )
{
    Selection.clear();
    for( int track : inTracks )
    {
        Touch( track );
    }
}


int ChartDocument::AddItem( int inTrack, double inStart, double inEnd, int inRow )
{
    BeginEdit( inTrack );
    const int item = Tracks[inTrack]->Add( inStart, inEnd, inRow );
    Selection.clear();
    Selection.insert( { inTrack, item } );
    CommitEdit( "Add " + Tracks[inTrack]->Name );
    const std::vector<int> selected = SelectedIn( inTrack );
    return selected.empty() ? -1 : selected.front();
}


void ChartDocument::DeleteSelection()
{
    const std::vector<int> tracks = SelectedTracks();
    if( tracks.empty() )
    {
        return;
    }
    for( int track : tracks )
    {
        BeginEdit( track );
        Tracks[track]->Remove( SelectedIn( track ) );
    }
    Selection.clear();
    CommitEdit( "Delete" );
}


void ChartDocument::MoveSelection( double inSeconds, int inRows )
{
    if( Selection.empty() )
    {
        return;
    }
    for( const ChartItemRef& ref : Selection )
    {
        IEventTrack& track = *Tracks[ref.Track];
        BeginEdit( ref.Track );
        const int row = std::clamp( track.Row( ref.Item ) + inRows, 0, track.Rows() - 1 );
        track.Set( ref.Item, track.Start( ref.Item ) + inSeconds, track.End( ref.Item ) + inSeconds, row );
    }
    CommitEdit( "Move" );
}


void ChartDocument::MoveSelectionBeats( double inBeats, int inRows )
{
    if( Selection.empty() )
    {
        return;
    }
    const float bpm = static_cast<float>( Chart.m_bpm );
    // The grid as it stood: moving beats themselves must not shift it under the others.
    const std::vector<BeatData> beats = Chart.m_beats;
    const auto moved = [&]( double inSeconds ) {
        return std::max( 0.0, BeatGrid::TimeOfBeat( beats, bpm, BeatGrid::BeatOfTime( beats, bpm, inSeconds ) + inBeats ) );
    };
    for( const ChartItemRef& ref : Selection )
    {
        IEventTrack& track = *Tracks[ref.Track];
        BeginEdit( ref.Track );
        const int row = std::clamp( track.Row( ref.Item ) + inRows, 0, track.Rows() - 1 );
        track.Set( ref.Item, moved( track.Start( ref.Item ) ), moved( track.End( ref.Item ) ), row );
    }
    CommitEdit( "Nudge" );
}


void ChartDocument::SnapSelection( int inDivision )
{
    if( Selection.empty() )
    {
        return;
    }
    const float bpm = static_cast<float>( Chart.m_bpm );
    const std::vector<BeatData> beats = Chart.m_beats;
    for( const ChartItemRef& ref : Selection )
    {
        IEventTrack& track = *Tracks[ref.Track];
        BeginEdit( ref.Track );
        const double length = track.End( ref.Item ) - track.Start( ref.Item );
        const double start = BeatGrid::Snap( beats, bpm, track.Start( ref.Item ), inDivision );
        double end = BeatGrid::Snap( beats, bpm, track.End( ref.Item ), inDivision );
        if( end <= start )
        {
            end = start + length;
        }
        track.Set( ref.Item, start, end, track.Row( ref.Item ) );
    }
    CommitEdit( "Snap to Grid" );
}


void ChartDocument::Copy()
{
    if( Selection.empty() )
    {
        return;
    }
    m_clipboard.clear();
    m_clipboardStart = 1e30;
    for( int track : SelectedTracks() )
    {
        const std::vector<int> items = SelectedIn( track );
        for( int item : items )
        {
            m_clipboardStart = std::min( m_clipboardStart, Tracks[track]->Start( item ) );
        }
        m_clipboard.push_back( { track, Tracks[track]->Copy( items ) } );
    }
}


void ChartDocument::Cut()
{
    Copy();
    DeleteSelection();
}


void ChartDocument::Paste( double inSeconds )
{
    if( m_clipboard.empty() )
    {
        return;
    }
    Selection.clear();
    for( const ClipboardEntry& entry : m_clipboard )
    {
        if( entry.Track >= TrackCount() )
        {
            continue;
        }
        BeginEdit( entry.Track );
        for( int item : Tracks[entry.Track]->Paste( entry.Items, inSeconds - m_clipboardStart ) )
        {
            Selection.insert( { entry.Track, item } );
        }
    }
    CommitEdit( "Paste" );
}


void ChartDocument::Duplicate()
{
    if( Selection.empty() )
    {
        return;
    }
    double start = 1e30;
    double end = 0.0;
    for( const ChartItemRef& ref : Selection )
    {
        start = std::min( start, Tracks[ref.Track]->Start( ref.Item ) );
        end = std::max( end, Tracks[ref.Track]->End( ref.Item ) );
    }
    // The copy starts on the next beat after the selection ends (a beat on for a single moment).
    const float bpm = static_cast<float>( Chart.m_bpm );
    const double firstBeat = BeatGrid::BeatOfTime( Chart.m_beats, bpm, start );
    const double beats = std::max( 1.0, std::ceil( BeatGrid::BeatOfTime( Chart.m_beats, bpm, end ) - firstBeat - 1e-4 ) );
    const double target = BeatGrid::TimeOfBeat( Chart.m_beats, bpm, firstBeat + beats );

    const std::vector<ClipboardEntry> clipboard = std::move( m_clipboard );
    const double clipboardStart = m_clipboardStart;
    Copy();
    Paste( target );
    m_clipboard = clipboard;
    m_clipboardStart = clipboardStart;
}


void ChartDocument::Undo()
{
    CancelEdit();
    History.Undo();
}


void ChartDocument::Redo()
{
    CancelEdit();
    History.Redo();
}


double ChartDocument::Duration() const
{
    double last = 0.0;
    for( const auto& track : Tracks )
    {
        // Lists are in time order, but a span early in the list may end last.
        const int count = track->Count();
        if( count > 0 )
        {
            last = std::max( last, track->Spans ? track->End( count - 1 ) : track->Start( count - 1 ) );
        }
    }
    return std::max( static_cast<double>( Chart.m_duration ), last + 4.0 );
}

#endif
