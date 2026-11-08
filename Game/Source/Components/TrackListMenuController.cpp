#include "Components/TrackListMenuController.h"
#include <Cores/UI/RmlUiCore.h>
#include <Engine/Engine.h>
#include <Engine/Input.h>
#include <Events/SceneEvents.h>
#include "CoreGame/TrackList.h"
#include "Events/GameEvents.h"
#include "Global/TrackRadio.h"
#include "UI/TrackRadioUtils.h"
#include <cctype>

namespace
{
    std::string Category( const TrackData& track, TrackListSort sort )
    {
        if( sort == TrackListSort::Year ) return std::to_string( track.m_year );
        const std::string& name = sort == TrackListSort::Artist ? track.m_artistName : track.m_trackName;
        if( sort == TrackListSort::None || name.empty() ) return "";
        return std::string( 1, static_cast<char>( std::toupper( static_cast<unsigned char>( name.front() ) ) ) );
    }
}


TrackListMenuController::TrackListMenuController() : Component( "TrackListMenuController" ) {}


void TrackListMenuController::PopulateModel()
{
    RmlUiCore* ui = GetEngine().RmlUi;
    if( !ui ) return;
    auto& database = TrackDatabase::GetInstance();
    auto& tracks = database.m_trackList.m_tracks;
    const auto& indices = database.SortTracks( database.m_currentSort, database.m_currentFilter );
    ui->ModelEnsure( "song_library" );
    for( const char* event : { "play", "preview", "select", "sort", "filter", "toggle_filters", "back", "stats" } )
        ui->ModelRegisterEvent( "song_library", event );
    if( !m_modelReady )
    {
        ui->ModelSetNumber( "song_library", "filters_open", 0 );
        ui->ModelSetNumber( "song_library", "selected", -1 );
        // Every value the document binds exists before it loads, so it never reloads for one.
        for( const char* key : { "detail_title", "detail_artist", "detail_album", "detail_genre", "detail_art" } )
        {
            ui->ModelSetString( "song_library", key, "" );
        }
        ui->ModelSetNumber( "song_library", "detail_year", 0 );
        ui->ModelSetNumber( "song_library", "detail_notes", 0 );
    }
    ui->ModelSetNumber( "song_library", "sort", static_cast<int>( database.m_currentSort ) );
    ui->ModelSetNumber( "song_library", "filter", static_cast<int>( database.m_currentFilter ) );
    const char* sortNames[] = { "Default", "Title", "Artist", "Year" };
    ui->ModelSetString( "song_library", "sort_name", sortNames[static_cast<int>( database.m_currentSort )] );
    ui->ModelSetString( "song_library", "filter_name", database.m_currentFilter == TrackListFilter::None ? "All songs" : database.GetFilterName( database.m_currentFilter ) );
    const int count = static_cast<int>( std::min<size_t>( indices.size(), 4096 ) );
    ui->ModelSetNumber( "song_library", "track_count", count );
    ui->ModelSetListCount( "song_library", "tracks", count );
    std::string previousCategory;
    for( int row = 0; row < count; ++row )
    {
        const int index = static_cast<int>( indices[row] );
        const TrackData& track = tracks[index];
        const std::string category = Category( track, database.m_currentSort );
        ui->ModelSetItemString( "song_library", "tracks", row, "category", category != previousCategory ? category : "" );
        previousCategory = category;
        ui->ModelSetItemNumber( "song_library", "tracks", row, "index", index );
        ui->ModelSetItemString( "song_library", "tracks", row, "title", track.m_trackName );
        ui->ModelSetItemString( "song_library", "tracks", row, "artist", track.m_artistName );
        ui->ModelSetItemString( "song_library", "tracks", row, "art", TrackRadioUtils::ArtSource( track ) );
        ui->ModelSetItemNumber( "song_library", "tracks", row, "year", track.m_year );
        ui->ModelSetItemNumber( "song_library", "tracks", row, "notes", track.m_noteCount );
    }
    int filterRow = 0;
    ui->ModelSetListCount( "song_library", "filters", 0 );
    for( int i = 0; i < static_cast<int>( TrackListFilter::Count ); ++i )
    {
        const unsigned int matches = i == 0 ? static_cast<unsigned int>( tracks.size() ) : database.m_filterMatches[i];
        if( i != 0 && matches == 0 ) continue;
        ui->ModelSetItemNumber( "song_library", "filters", filterRow, "index", i );
        ui->ModelSetItemString( "song_library", "filters", filterRow, "name", i == 0 ? "All songs" : database.GetFilterName( static_cast<TrackListFilter>( i ) ) );
        ui->ModelSetItemNumber( "song_library", "filters", filterRow++, "count", matches );
    }
    if( count == 0 )
    {
        m_selectedTrack = -1;
        m_previewTrack = -1;
        ui->ModelSetNumber( "song_library", "selected", -1 );
    }
    else if( std::find( indices.begin(), indices.end(), m_selectedTrack ) == indices.end() )
    {
        SelectTrack( static_cast<int>( indices.front() ) );
        m_previewTrack = -1;
    }
    m_modelReady = true;
}


void TrackListMenuController::SelectTrack( int inTrackIndex )
{
    const auto& tracks = TrackDatabase::GetInstance().m_trackList.m_tracks;
    if( inTrackIndex < 0 || inTrackIndex >= static_cast<int>( tracks.size() ) || inTrackIndex == m_selectedTrack ) return;
    m_selectedTrack = inTrackIndex;
    m_previewTrack = inTrackIndex;
    m_previewDelay = 0.25f;
    const TrackData& track = tracks[inTrackIndex];
    RmlUiCore* ui = GetEngine().RmlUi;
    ui->ModelSetNumber( "song_library", "selected", inTrackIndex );
    ui->ModelSetString( "song_library", "detail_title", track.m_trackName );
    ui->ModelSetString( "song_library", "detail_artist", track.m_artistName );
    ui->ModelSetString( "song_library", "detail_album", track.m_albumName );
    ui->ModelSetString( "song_library", "detail_genre", track.m_genre );
    ui->ModelSetString( "song_library", "detail_art", TrackRadioUtils::ArtSource( track ) );
    ui->ModelSetNumber( "song_library", "detail_year", track.m_year );
    ui->ModelSetNumber( "song_library", "detail_notes", track.m_noteCount );
}


void TrackListMenuController::PreviewTrack( int inTrackIndex )
{
    auto& tracks = TrackDatabase::GetInstance().m_trackList.m_tracks;
    if( inTrackIndex < 0 || inTrackIndex >= static_cast<int>( tracks.size() ) ) return;
    RadioArgs args;
    args.CurrentTrack = &tracks[inTrackIndex];
    args.CurrentTrackIndex = inTrackIndex;
    args.UsePreviewMarker = true;
    TrackRadio::GetInstance().Play( args );
}


void TrackListMenuController::PlayTrack( int inTrackIndex )
{
    auto& tracks = TrackDatabase::GetInstance().m_trackList.m_tracks;
    if( inTrackIndex < 0 || inTrackIndex >= static_cast<int>( tracks.size() ) ) return;
    const std::string trackId = tracks[inTrackIndex].m_trackSourcePath;
    TrackRadio::GetInstance().Stop();
    LoadSceneEvent event;
    event.Level = "Assets/Example.lvl";
    event.Callback = [trackId, inTrackIndex]() {
        LaunchPlayTrackEvent play;
        play.TrackID = trackId;
        play.TrackIndex = inTrackIndex;
        play.Fire();
    };
    event.Queue();
}


void TrackListMenuController::Update( float inDeltaTime )
{
    TrackRadio::GetInstance().Update( inDeltaTime );
    if( !m_modelReady ) PopulateModel();
    RmlUiCore* ui = GetEngine().RmlUi;
    if( !ui ) return;
    if( GetEngine().GetInput().WasKeyPressed( KeyCode::Escape ) )
    {
        if( ui->ModelGetNumber( "song_library", "filters_open" ) != 0 ) ui->ModelSetNumber( "song_library", "filters_open", 0 );
        else { LoadSceneEvent event; event.Level = "Assets/MainMenu.lvl"; event.Queue(); }
    }
    for( std::string event; !( event = ui->ModelPollEvent( "song_library" ) ).empty(); )
    {
        const json arguments = json::parse( ui->ModelLastEventArgs( "song_library" ), nullptr, false );
        const int index = arguments.is_array() && !arguments.empty() && arguments[0].is_number() ? arguments[0].get<int>() : -1;
        if( event == "play" ) { PlayTrack( index ); return; }
        else if( event == "select" ) SelectTrack( index );
        else if( event == "preview" ) { m_previewTrack = -1; PreviewTrack( index ); }
        else if( event == "toggle_filters" ) ui->ModelSetNumber( "song_library", "filters_open", !ui->ModelGetNumber( "song_library", "filters_open" ) );
        else if( event == "sort" && index >= 0 && index <= 3 )
        {
            auto& database = TrackDatabase::GetInstance();
            database.SortTracks( static_cast<TrackListSort>( index ), database.m_currentFilter );
            PopulateModel();
            ui->ModelSetNumber( "song_library", "filters_open", 0 );
        }
        else if( event == "filter" && index >= 0 && index < static_cast<int>( TrackListFilter::Count ) )
        {
            auto& database = TrackDatabase::GetInstance();
            database.SortTracks( database.m_currentSort, static_cast<TrackListFilter>( index ) );
            PopulateModel();
            ui->ModelSetNumber( "song_library", "filters_open", 0 );
        }
        else if( event == "stats" ) { LoadSceneEvent scene; scene.Level = "Assets/TrackStats.lvl"; scene.Queue(); return; }
    }
    if( m_previewTrack >= 0 && ( m_previewDelay -= inDeltaTime ) <= 0.f )
    {
        PreviewTrack( m_previewTrack );
        m_previewTrack = -1;
    }
}
