#include "Components/TrackListMenuController.h"
#include "Config/PlayerProfile.h"
#include <cstdio>
#include <Cores/UI/RmlUiCore.h>
#include <Engine/Engine.h>
#include <Engine/Input.h>
#include <Events/SceneEvents.h>
#include "CoreGame/TrackList.h"
#include "CoreGame/ChartAdvice.h"
#include "Events/GameEvents.h"
#include "Global/TrackRadio.h"
#include "UI/TrackRadioUtils.h"
#include "UI/MusicLinks.h"
#include <cctype>
#include <sstream>

namespace
{
    std::string Category( const TrackData& track, TrackListSort sort )
    {
        if( sort == TrackListSort::Year ) return std::to_string( track.m_year );
        const std::string& name = sort == TrackListSort::Artist ? track.m_artistName : track.m_trackName;
        if( sort == TrackListSort::None || name.empty() ) return "";
        return std::string( 1, static_cast<char>( std::toupper( static_cast<unsigned char>( name.front() ) ) ) );
    }


    std::string Lower( std::string inText )
    {
        for( char& c : inText ) c = static_cast<char>( std::tolower( static_cast<unsigned char>( c ) ) );
        return inText;
    }


    // Every word of the search must appear in the title, artist, album or genre (any case).
    bool MatchesSearch( const TrackData& track, const std::vector<std::string>& words )
    {
        if( words.empty() ) return true;
        const std::string haystack = Lower( track.m_trackName + "\n" + track.m_artistName + "\n" + track.m_albumName + "\n" + track.m_genre );
        for( const std::string& word : words )
            if( haystack.find( word ) == std::string::npos ) return false;
        return true;
    }
}


TrackListMenuController::TrackListMenuController() : Component( "TrackListMenuController" ) {}


void TrackListMenuController::PopulateModel()
{
    RmlUiCore* ui = GetEngine().RmlUi;
    if( !ui ) return;
    auto& database = TrackDatabase::GetInstance();
    auto& tracks = database.m_trackList.m_tracks;
    const auto& sorted = database.SortTracks( database.m_currentSort, database.m_currentFilter );
    // The search box and the favorites toggle narrow the sorted, filtered list further.
    std::vector<std::string> words;
    {
        std::istringstream stream( Lower( m_search ) );
        for( std::string word; stream >> word; ) words.push_back( word );
    }
    std::vector<unsigned int> indices;
    indices.reserve( sorted.size() );
    unsigned int favoriteCount = 0;
    for( const TrackData& track : tracks ) favoriteCount += database.IsFavorite( track ) ? 1 : 0;
    for( unsigned int index : sorted )
    {
        if( m_favoritesOnly && !database.IsFavorite( tracks[index] ) ) continue;
        if( !MatchesSearch( tracks[index], words ) ) continue;
        indices.push_back( index );
    }
    ui->ModelEnsure( "song_library" );
    for( const char* event : { "play", "preview", "select", "sort", "filter", "toggle_filters", "back", "stats", "favorite", "favorites_only", "clear_search", "edit", "remove", "remove_confirm", "remove_cancel", "listen" } )
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
        ui->ModelSetNumber( "song_library", "detail_favorite", 0 );
        ui->ModelSetString( "song_library", "search", m_search );
        ui->ModelSetListCount( "song_library", "advice", 0 );
        ui->ModelSetString( "song_library", "detail_badge", "" );
        ui->ModelSetString( "song_library", "detail_best", "" );
        ui->ModelSetNumber( "song_library", "detail_ds_ready", 0 );
        ui->ModelSetNumber( "song_library", "detail_confirm_remove", 0 );
        // The Track Editor lives in the editor: its button and F4 only show there.
#if USING( ME_EDITOR )
        ui->ModelSetNumber( "song_library", "tools", 1 );
#else
        ui->ModelSetNumber( "song_library", "tools", 0 );
#endif
    }
    ui->ModelSetNumber( "song_library", "favorites_only", m_favoritesOnly );
    ui->ModelSetNumber( "song_library", "favorite_count", favoriteCount );
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
        ui->ModelSetItemNumber( "song_library", "tracks", row, "favorite", database.IsFavorite( track ) );
        ui->ModelSetItemString( "song_library", "tracks", row, "badge", TrackDatabase::SourceBadge( TrackDatabase::FilterForSource( track.m_dlcSource ) ) );
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
    if( m_selectedTrack >= 0 && m_selectedTrack < static_cast<int>( tracks.size() ) )
        ui->ModelSetNumber( "song_library", "detail_favorite", database.IsFavorite( tracks[m_selectedTrack] ) );
    m_modelReady = true;
}


void TrackListMenuController::SelectTrack( int inTrackIndex )
{
    const auto& tracks = TrackDatabase::GetInstance().m_trackList.m_tracks;
    if( inTrackIndex < 0 || inTrackIndex >= static_cast<int>( tracks.size() ) || inTrackIndex == m_selectedTrack ) return;
    m_selectedTrack = inTrackIndex;
    m_confirmRemove = -1;
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
    ui->ModelSetNumber( "song_library", "detail_favorite", TrackDatabase::GetInstance().IsFavorite( track ) );
    ui->ModelSetString( "song_library", "detail_badge", TrackDatabase::SourceBadge( TrackDatabase::FilterForSource( track.m_dlcSource ) ) );
    ui->ModelSetNumber( "song_library", "detail_ds_ready", track.m_adviceKnown && track.m_authored );
    ui->ModelSetNumber( "song_library", "detail_confirm_remove", 0 );
    // The player's record of it (PlayerProfile).
    std::string best;
    if( const PlayerProfile::SongRecord* record = PlayerProfile::GetInstance().FindSong( TrackDatabase::FavoriteKey( track ) ) )
    {
        char text[112];
        std::snprintf( text, sizeof( text ), "Your best: %d, %.1f%%%s (played %d time%s)", record->BestScore, record->BestAccuracy, record->FullCombo ? ", full combo" : "", record->Plays, record->Plays == 1 ? "" : "s" );
        best = text;
    }
    ui->ModelSetString( "song_library", "detail_best", best );
    // What the chart recommends is read from its notes once the selection has settled (Update).
    ui->ModelSetListCount( "song_library", "advice", 0 );
    m_adviceTrack = inTrackIndex;
    m_adviceDelay = 0.25f;
}


void TrackListMenuController::ShowAdvice( int inTrackIndex )
{
    auto& tracks = TrackDatabase::GetInstance().m_trackList.m_tracks;
    RmlUiCore* ui = GetEngine().RmlUi;
    if( !ui || inTrackIndex != m_selectedTrack || inTrackIndex < 0 || inTrackIndex >= static_cast<int>( tracks.size() ) ) return;
    const std::vector<std::string>& advice = ChartAdvice::For( tracks[inTrackIndex] );
    ui->ModelSetListCount( "song_library", "advice", static_cast<int>( advice.size() ) );
    for( int i = 0; i < static_cast<int>( advice.size() ); ++i )
        ui->ModelSetItemString( "song_library", "advice", i, "text", advice[i] );
    ui->ModelSetNumber( "song_library", "detail_ds_ready", tracks[inTrackIndex].m_authored );
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
    TrackRadioUtils::LaunchTrack( inTrackIndex );
}


void TrackListMenuController::EditTrack( int inTrackIndex )
{
    // Opens the song in the Track Editor (editor builds; nothing listens elsewhere).
    const auto& tracks = TrackDatabase::GetInstance().m_trackList.m_tracks;
    if( inTrackIndex < 0 || inTrackIndex >= static_cast<int>( tracks.size() ) ) return;
    EditTrackEvent edit;
    edit.FileName = tracks[inTrackIndex].m_trackName;
    edit.Fire();
}


void TrackListMenuController::ToggleFavorite( int inTrackIndex )
{
    auto& database = TrackDatabase::GetInstance();
    const auto& tracks = database.m_trackList.m_tracks;
    if( inTrackIndex < 0 || inTrackIndex >= static_cast<int>( tracks.size() ) ) return;
    database.SetFavorite( tracks[inTrackIndex], !database.IsFavorite( tracks[inTrackIndex] ) );
    PopulateModel();
}


void TrackListMenuController::Update( float inDeltaTime )
{
    if( !m_modelReady ) PopulateModel();
    RmlUiCore* ui = GetEngine().RmlUi;
    if( !ui ) return;
    if( GetEngine().GetInput().WasKeyPressed( KeyCode::Escape ) )
    {
        if( ui->ModelGetNumber( "song_library", "filters_open" ) != 0 ) ui->ModelSetNumber( "song_library", "filters_open", 0 );
        else if( !m_search.empty() ) { m_search.clear(); ui->ModelSetString( "song_library", "search", "" ); PopulateModel(); }
        else { LoadSceneEvent event; event.Level = "Assets/MainMenu.lvl"; event.Queue(); }
    }
#if USING( ME_EDITOR )
    // F4 pulls up the Track Editor on the selected song.
    if( GetEngine().GetInput().WasKeyPressed( KeyCode::F4 ) ) EditTrack( m_selectedTrack );
#endif
    // The search box binds two-way and changes with every key; refilter when its text moves.
    if( const std::string search = ui->ModelGetString( "song_library", "search" ); search != m_search )
    {
        m_search = search;
        PopulateModel();
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
        else if( event == "favorite" ) ToggleFavorite( index );
        else if( event == "favorites_only" )
        {
            m_favoritesOnly = !m_favoritesOnly;
            PopulateModel();
            ui->ModelSetNumber( "song_library", "filters_open", 0 );
        }
        else if( event == "clear_search" )
        {
            m_search.clear();
            ui->ModelSetString( "song_library", "search", "" );
            PopulateModel();
        }
        else if( event == "edit" ) EditTrack( m_selectedTrack );
        else if( event == "listen" && index >= 0 && index < static_cast<int>( MusicLinks::Service::Count ) )
        {
            // Out to the real thing: the song on a streaming service, in the player's browser.
            const auto& tracks = TrackDatabase::GetInstance().m_trackList.m_tracks;
            if( m_selectedTrack >= 0 && m_selectedTrack < static_cast<int>( tracks.size() ) )
            {
                const TrackData& track = tracks[m_selectedTrack];
                MusicLinks::Open( static_cast<MusicLinks::Service>( index ), track.m_artistName, track.m_trackName, track.m_links );
            }
        }
        else if( event == "remove" )
        {
            // Asked once; the details panel then offers the yes that deletes the files.
            m_confirmRemove = m_selectedTrack;
            ui->ModelSetNumber( "song_library", "detail_confirm_remove", m_confirmRemove >= 0 );
        }
        else if( event == "remove_cancel" )
        {
            m_confirmRemove = -1;
            ui->ModelSetNumber( "song_library", "detail_confirm_remove", 0 );
        }
        else if( event == "remove_confirm" && m_confirmRemove >= 0 && m_confirmRemove == m_selectedTrack )
        {
            m_confirmRemove = -1;
            m_previewTrack = -1;
            m_adviceTrack = -1;
            if( TrackDatabase::GetInstance().RemoveTrack( m_selectedTrack ) )
            {
                // Every index after it moved: list again, and select whatever is first.
                m_selectedTrack = -1;
                PopulateModel();
            }
            ui->ModelSetNumber( "song_library", "detail_confirm_remove", 0 );
        }
        else if( event == "stats" ) { LoadSceneEvent scene; scene.Level = "Assets/TrackStats.lvl"; scene.Queue(); return; }
    }
    if( m_adviceTrack >= 0 && ( m_adviceDelay -= inDeltaTime ) <= 0.f )
    {
        ShowAdvice( m_adviceTrack );
        m_adviceTrack = -1;
    }
    if( m_previewTrack >= 0 && ( m_previewDelay -= inDeltaTime ) <= 0.f )
    {
        PreviewTrack( m_previewTrack );
        m_previewTrack = -1;
    }
}
