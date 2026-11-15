#include "Editor/TrackEditor.h"
#include <cmath>
#include <cstdlib>
#include <filesystem>

#if USING( ME_EDITOR )

// The Track Editor in --editor-exec scripts (Assets/Scenes/Tests/TrackEditorFlows.edscript).
// Arguments are separated by " | "; a track is named as the timeline names it ("Notes",
// "Lighting", "Star Power").
//
//   track-open <song title>                 a song of the library
//   track-open-copy <folder> | <folder>     copies a song folder (a fixture) and opens the copy
//   track-save
//   track-select <track> | <item>|all [| add]
//   track-deselect
//   track-add <track> | <start> | <end> | <row>
//   track-move <seconds> | <rows>
//   track-nudge <beats>
//   track-delete, track-copy, track-cut, track-duplicate, track-undo, track-redo
//   track-paste <seconds>
//   track-seek <seconds>, track-play, track-pause
//   track-loop <start> | <end>              the loop zone, on; track-loop off clears it
//   track-follow <0|1>                      the timeline follows the playhead
//   track-view <notes|venue|all>            the View menu's presets
//   track-zoom-fit
//   track-preview <start|stop>
//   track-preview-mode <highway|scene|both>
//   track-assert-count <track> | <n>
//   track-assert-time <track> | <item> | <seconds>
//   track-assert-row <track> | <item> | <row>
//   track-assert-playhead <min> | <max>     seconds
//   track-assert-dirty <0|1>
//   track-assert-preview <0|1>              a preview session is running

namespace
{
    std::vector<std::string> SplitArgs( const std::string& inArgs )
    {
        std::vector<std::string> parts;
        size_t start = 0;
        while( start <= inArgs.size() )
        {
            size_t bar = inArgs.find( '|', start );
            if( bar == std::string::npos )
            {
                bar = inArgs.size();
            }
            std::string part = inArgs.substr( start, bar - start );
            while( !part.empty() && part.front() == ' ' ) part.erase( 0, 1 );
            while( !part.empty() && part.back() == ' ' ) part.pop_back();
            parts.push_back( part );
            start = bar + 1;
        }
        return parts;
    }
}


bool TrackEditor::ExecuteAutomation( const std::string& inCommand, const std::string& inArgs, std::string& outError )
{
    const std::vector<std::string> args = SplitArgs( inArgs );
    const auto arg = [&args]( size_t inIndex ) { return inIndex < args.size() ? args[inIndex] : std::string(); };
    const auto number = [&arg]( size_t inIndex ) { return std::atof( arg( inIndex ).c_str() ); };

    IsOpen = true;
    if( inCommand == "track-open" )
    {
        const auto& tracks = TrackDatabase::GetInstance().m_trackList.m_tracks;
        for( const TrackData& track : tracks )
        {
            if( track.m_trackName == arg( 0 ) )
            {
                OpenTrack( track );
                return true;
            }
        }
        outError = "no song titled " + arg( 0 );
        return false;
    }
    if( inCommand == "track-open-copy" )
    {
        const Path source( arg( 0 ) );
        const Path target( arg( 1 ) );
        std::error_code error;
        std::filesystem::remove_all( target.FullPath, error );
        std::filesystem::create_directories( target.FullPath, error );
        std::filesystem::copy( source.FullPath, target.FullPath, std::filesystem::copy_options::recursive | std::filesystem::copy_options::overwrite_existing, error );
        if( error )
        {
            outError = "couldn't copy " + arg( 0 ) + ": " + error.message();
            return false;
        }
        TrackData track( Path( arg( 1 ) + "/TrackData.txt" ) );
        track.Load();
        OpenTrack( track );
        if( m_document.Chart.m_noteData.empty() )
        {
            outError = "the copy has no notes";
            return false;
        }
        return true;
    }

    if( !m_document.IsOpen() )
    {
        outError = "no song is open";
        return false;
    }
    const auto trackOf = [&]( size_t inIndex ) {
        const int track = m_document.FindTrack( arg( inIndex ) );
        if( track < 0 )
        {
            outError = "no track named " + arg( inIndex );
        }
        return track;
    };

    if( inCommand == "track-save" ) Save();
    else if( inCommand == "track-deselect" ) m_document.Selection.clear();
    else if( inCommand == "track-delete" ) m_document.DeleteSelection();
    else if( inCommand == "track-copy" ) m_document.Copy();
    else if( inCommand == "track-cut" ) m_document.Cut();
    else if( inCommand == "track-duplicate" ) m_document.Duplicate();
    else if( inCommand == "track-undo" ) m_document.Undo();
    else if( inCommand == "track-redo" ) m_document.Redo();
    else if( inCommand == "track-paste" ) m_document.Paste( number( 0 ) );
    else if( inCommand == "track-move" ) m_document.MoveSelection( number( 0 ), static_cast<int>( number( 1 ) ) );
    else if( inCommand == "track-nudge" ) m_document.MoveSelectionBeats( number( 0 ), 0 );
    else if( inCommand == "track-seek" ) { m_transport.Seek( number( 0 ) ); m_timeline.Reveal( number( 0 ) ); }
    else if( inCommand == "track-play" ) m_transport.Play();
    else if( inCommand == "track-pause" ) m_transport.Pause();
    else if( inCommand == "track-loop" )
    {
        if( arg( 0 ) == "off" ) m_transport.ClearLoop();
        else m_transport.SetLoop( number( 0 ), number( 1 ) );
    }
    else if( inCommand == "track-follow" ) m_timeline.Follow = number( 0 ) != 0.0;
    else if( inCommand == "track-zoom-fit" ) m_timeline.ZoomToFit( m_document );
    else if( inCommand == "track-view" )
    {
        const bool notes = arg( 0 ) == "notes";
        const bool venue = arg( 0 ) == "venue";
        for( int group = 0; group < static_cast<int>( TrackGroup::Count ); ++group )
        {
            const bool charting = group == static_cast<int>( TrackGroup::Notes ) || group == static_cast<int>( TrackGroup::Gameplay );
            m_timeline.Hidden[group] = notes ? !( charting || group == static_cast<int>( TrackGroup::Structure ) ) : venue ? charting : false;
            if( venue ) m_timeline.Collapsed[group] = false;
        }
    }
    else if( inCommand == "track-preview" )
    {
        if( arg( 0 ) == "start" )
        {
            if( !m_preview.Start( m_document ) )
            {
                outError = "the preview didn't start";
                return false;
            }
        }
        else
        {
            m_preview.Stop();
        }
    }
    else if( inCommand == "track-preview-mode" )
    {
        m_preview.SetMode( arg( 0 ) == "highway" ? PreviewSession::Mode::Highway : arg( 0 ) == "scene" ? PreviewSession::Mode::Scene : PreviewSession::Mode::Both );
    }
    else if( inCommand == "track-select" )
    {
        const int track = trackOf( 0 );
        if( track < 0 ) return false;
        if( arg( 2 ) != "add" ) m_document.Selection.clear();
        if( arg( 1 ) == "all" )
        {
            for( int item = 0; item < m_document.Tracks[track]->Count(); ++item ) m_document.Selection.insert( { track, item } );
        }
        else
        {
            const int item = static_cast<int>( number( 1 ) );
            if( item < 0 || item >= m_document.Tracks[track]->Count() )
            {
                outError = arg( 0 ) + " has no item " + arg( 1 );
                return false;
            }
            m_document.Selection.insert( { track, item } );
        }
    }
    else if( inCommand == "track-add" )
    {
        const int track = trackOf( 0 );
        if( track < 0 ) return false;
        m_document.AddItem( track, number( 1 ), std::max( number( 1 ), number( 2 ) ), static_cast<int>( number( 3 ) ) );
    }
    else if( inCommand == "track-assert-count" )
    {
        const int track = trackOf( 0 );
        if( track < 0 ) return false;
        if( m_document.Tracks[track]->Count() != static_cast<int>( number( 1 ) ) )
        {
            outError = arg( 0 ) + " has " + std::to_string( m_document.Tracks[track]->Count() ) + " items, not " + arg( 1 );
            return false;
        }
    }
    else if( inCommand == "track-assert-time" || inCommand == "track-assert-row" )
    {
        const int track = trackOf( 0 );
        if( track < 0 ) return false;
        const int item = static_cast<int>( number( 1 ) );
        if( item < 0 || item >= m_document.Tracks[track]->Count() )
        {
            outError = arg( 0 ) + " has no item " + arg( 1 );
            return false;
        }
        if( inCommand == "track-assert-time" && std::abs( m_document.Tracks[track]->Start( item ) - number( 2 ) ) > 0.002 )
        {
            outError = arg( 0 ) + " item " + arg( 1 ) + " is at " + std::to_string( m_document.Tracks[track]->Start( item ) ) + " s, not " + arg( 2 );
            return false;
        }
        if( inCommand == "track-assert-row" && m_document.Tracks[track]->Row( item ) != static_cast<int>( number( 2 ) ) )
        {
            outError = arg( 0 ) + " item " + arg( 1 ) + " is on row " + std::to_string( m_document.Tracks[track]->Row( item ) ) + ", not " + arg( 2 );
            return false;
        }
    }
    else if( inCommand == "track-assert-playhead" )
    {
        if( m_transport.Seconds() < number( 0 ) || m_transport.Seconds() > number( 1 ) )
        {
            outError = "the playhead is at " + std::to_string( m_transport.Seconds() ) + " s";
            return false;
        }
    }
    else if( inCommand == "track-assert-dirty" )
    {
        if( m_document.IsDirty() != ( number( 0 ) != 0.0 ) )
        {
            outError = m_document.IsDirty() ? "the chart has unsaved changes" : "the chart has no unsaved changes";
            return false;
        }
    }
    else if( inCommand == "track-assert-preview" )
    {
        if( m_preview.IsActive() != ( number( 0 ) != 0.0 ) )
        {
            outError = m_preview.IsActive() ? "a preview is running" : "no preview is running";
            return false;
        }
    }
    else
    {
        outError = "unknown command";
        return false;
    }
    return true;
}

#endif
