#include "Components/DLCMenuController.h"

#include <Cores/UI/RmlUiCore.h>
#include <Engine/Engine.h>
#include <Engine/Input.h>
#include <Events/SceneEvents.h>
#include "CLog.h"
#include "Config/GameSettings.h"
#include "Events/GameEvents.h"
#include "File.h"
#include "Global/TrackRadio.h"
#include "UI/TrackRadioUtils.h"
#include "UI/UIModelUtils.h"
#include "Web/HttpDownload.h"
#include <algorithm>
#include <cctype>
#include <filesystem>

namespace
{
    constexpr const char* kModel = "dlc_store";
    constexpr const char* kIndexFile = "Assets/DLC/dlc_index.json";
    // The index downloads here first so a failed fetch can't truncate the cached copy.
    constexpr const char* kIndexDownloadFile = "Assets/DLC/dlc_index.download";
    // Catalogue art is cached under a dot-folder the library scan skips; a song's own download
    // brings its art again, into the song's folder.
    constexpr const char* kArtCache = "Assets/DLC/.catalogue/";


    std::string Trim( std::string inText )
    {
        const size_t first = inText.find_first_not_of( " \t\r\n" );
        if( first == std::string::npos )
        {
            return {};
        }
        return inText.substr( first, inText.find_last_not_of( " \t\r\n" ) - first + 1 );
    }


    std::string JsonString( const json& inJson, const char* inKey )
    {
        const auto it = inJson.find( inKey );
        return it != inJson.end() && it->is_string() ? Trim( it->get<std::string>() ) : std::string();
    }


    // The library's filter for a DLCSource tag: the same tags TrackDatabase::GatherFilterCounts knows.
    TrackListFilter FilterForSource( const std::string& inSource )
    {
        static const std::pair<const char*, TrackListFilter> kTags[] = {
            { "DS", TrackListFilter::Drumsmith },
            { "rb1", TrackListFilter::RockBand },
            { "rb2", TrackListFilter::RockBand2 },
            { "rb3", TrackListFilter::RockBand3 },
            { "rb3dlc", TrackListFilter::RockBand3 },
            { "rb4", TrackListFilter::RockBand4 },
            { "rbb", TrackListFilter::RockBandBlitz },
            { "lrb", TrackListFilter::LegoRockBand },
            { "gdrb", TrackListFilter::GreenDayRockBand },
            { "gh", TrackListFilter::GuitarHero },
            { "ghwt", TrackListFilter::GuitarHeroWorldTour },
            { "ghwtdlc", TrackListFilter::GuitarHeroWorldTourDLC },
            { "gh5", TrackListFilter::GuitarHero5 },
            { "gh5dlc", TrackListFilter::GuitarHero5DLC },
        };
        for( const auto& [tag, filter] : kTags )
        {
            if( inSource == tag )
            {
                return filter;
            }
        }
        return TrackListFilter::Other;
    }


    bool LessCaseInsensitive( const std::string& inLeft, const std::string& inRight )
    {
        return std::lexicographical_compare( inLeft.begin(), inLeft.end(), inRight.begin(), inRight.end(),
            []( unsigned char a, unsigned char b ) { return std::tolower( a ) < std::tolower( b ); } );
    }


    std::string Initial( const std::string& inName )
    {
        return inName.empty() ? std::string( "#" ) : std::string( 1, static_cast<char>( std::toupper( static_cast<unsigned char>( inName.front() ) ) ) );
    }


    // Where a server folder's track sits in the installed library, or -1.
    int InstalledIndexOf( const std::string& inFolder )
    {
        const auto& tracks = TrackDatabase::GetInstance().m_trackList.m_tracks;
        const std::string needle = "/" + inFolder + "/";
        for( int i = 0; i < static_cast<int>( tracks.size() ); ++i )
        {
            if( tracks[i].m_trackSourcePath.find( needle ) != std::string::npos )
            {
                return i;
            }
        }
        return -1;
    }
}


DLCMenuController::DLCMenuController()
    : Component( "DLCMenuController" )
    , m_radioUtils( std::make_unique<TrackRadioUtils>( kModel ) )
{
}


DLCMenuController::~DLCMenuController()
{
    m_queue.clear();
    if( m_active )
    {
        // The worker stops between files; the file in flight finishes first.
        m_active->Cancel = true;
        if( m_active->Thread.joinable() )
        {
            m_active->Thread.join();
        }
    }
}


void DLCMenuController::PopulateModel()
{
    RmlUiCore* ui = GetEngine().RmlUi;
    if( !ui )
    {
        return;
    }
    ui->ModelEnsure( kModel );
    for( const char* event : { "select", "download", "play", "preview", "edit", "sort", "filter", "toggle_filters", "toggle_details", "refresh" } )
    {
        ui->ModelRegisterEvent( kModel, event );
    }
    m_radioUtils->RegisterEvents( *ui );
    ui->ModelSetNumber( kModel, "filters_open", 0 );
    ui->ModelSetNumber( kModel, "details_open", 1 );
    ui->ModelSetNumber( kModel, "selected", -1 );
    ui->ModelSetNumber( kModel, "loading", 0 );
    ui->ModelSetNumber( kModel, "track_count", 0 );
    ui->ModelSetString( kModel, "status", "" );
    ui->ModelSetString( kModel, "server", "" );
#if USING( ME_EDITOR )
    ui->ModelSetNumber( kModel, "tools", 1 );
#else
    ui->ModelSetNumber( kModel, "tools", 0 );
#endif
    for( const char* key : { "detail_title", "detail_artist", "detail_album", "detail_source", "detail_art", "detail_state" } )
    {
        ui->ModelSetString( kModel, key, "" );
    }
    for( const char* key : { "detail_year", "detail_files", "detail_installed", "detail_busy", "detail_notes" } )
    {
        ui->ModelSetNumber( kModel, key, 0 );
    }
    ui->ModelSetListCount( kModel, "tracks", 0 );
    RefreshFilters();
    RefreshRows();
    m_modelReady = true;
    BeginIndexFetch();
}


void DLCMenuController::BeginIndexFetch()
{
    RmlUiCore* ui = GetEngine().RmlUi;
    m_server = Trim( GameSettings::GetInstance().DLCURL );
    while( !m_server.empty() && m_server.back() == '/' )
    {
        m_server.pop_back();
    }
    ui->ModelSetString( kModel, "server", m_server );
    if( m_server.empty() )
    {
        const Path cached( kIndexFile );
        if( cached.Exists )
        {
            LoadIndex( File( cached ).Read(), "No DLC server set: showing the last catalogue. Enter a server under Settings." );
        }
        else
        {
            LoadIndex( "", "No DLC server set. Enter one under Settings on the main menu." );
        }
        return;
    }
    ui->ModelSetNumber( kModel, "loading", 1 );
    ui->ModelSetString( kModel, "status", "Loading the catalogue from " + m_server + "..." );
    auto transfer = std::make_unique<Transfer>();
    transfer->Type = Transfer::Kind::Index;
    transfer->Files.emplace_back( m_server + "/dlc_index.json", Path( kIndexDownloadFile ) );
    m_queue.push_front( std::move( transfer ) );
}


void DLCMenuController::LoadIndex( const std::string& inText, const std::string& inStatus )
{
    RmlUiCore* ui = GetEngine().RmlUi;
    m_catalogue.clear();
    m_selectedTrack = -1;
    m_previewTrack = -1;
    const json index = inText.empty() ? json() : json::parse( inText, nullptr, false );
    if( index.is_array() )
    {
        for( const json& entry : index )
        {
            if( !entry.is_object() )
            {
                continue;
            }
            CatalogueTrack track;
            track.Title = JsonString( entry, "Title" );
            track.Artist = JsonString( entry, "Artist" );
            track.Album = JsonString( entry, "Album" );
            track.Source = JsonString( entry, "DLCSource" );
            track.Folder = JsonString( entry, "FolderPath" );
            track.ArtFile = JsonString( entry, "AlbumArtFileName" );
            const auto year = entry.find( "Year" );
            track.Year = year != entry.end() && year->is_number() ? year->get<int>() : 0;
            const auto files = entry.find( "FilesInFolder" );
            if( files != entry.end() && files->is_array() )
            {
                for( const json& file : *files )
                {
                    if( file.is_string() && !file.get<std::string>().empty() )
                    {
                        track.Files.push_back( file.get<std::string>() );
                    }
                }
            }
            // The server's own index lists itself when it was generated at the DLC root.
            if( track.Folder.empty() || track.Folder == "." || track.Files.empty() )
            {
                continue;
            }
            track.InstalledIndex = InstalledIndexOf( track.Folder );
            if( track.InstalledIndex >= 0 )
            {
                track.State = "Installed";
            }
            m_catalogue.push_back( std::move( track ) );
        }
    }
    else if( !inText.empty() )
    {
        YIKES( "DLC: the catalogue index isn't a JSON array" );
    }
    ui->ModelSetNumber( kModel, "loading", 0 );
    ui->ModelSetString( kModel, "status", inStatus );
    RefreshFilters();
    RefreshRows();
    QueueMissingArt();
}


void DLCMenuController::QueueMissingArt()
{
    for( int i = 0; i < static_cast<int>( m_catalogue.size() ); ++i )
    {
        const CatalogueTrack& track = m_catalogue[i];
        if( track.ArtFile.empty() || track.ArtFile.back() == '/' || track.InstalledIndex >= 0 || ArtCachePath( track ).Exists )
        {
            continue;
        }
        auto transfer = std::make_unique<Transfer>();
        transfer->Type = Transfer::Kind::Art;
        transfer->Track = i;
        transfer->Files.emplace_back( FileURL( track, track.ArtFile ), ArtCachePath( track ) );
        m_queue.push_back( std::move( transfer ) );
    }
}


void DLCMenuController::QueueTrackDownload( int inTrack )
{
    if( inTrack < 0 || inTrack >= static_cast<int>( m_catalogue.size() ) )
    {
        return;
    }
    CatalogueTrack& track = m_catalogue[inTrack];
    if( track.Busy || track.InstalledIndex >= 0 )
    {
        return;
    }
    auto transfer = std::make_unique<Transfer>();
    transfer->Type = Transfer::Kind::Track;
    transfer->Track = inTrack;
    for( const std::string& file : track.Files )
    {
        transfer->Files.emplace_back( FileURL( track, file ), FilePath( track, file ) );
    }
    track.Busy = true;
    track.State = "Queued";
    // Songs the player asked for go ahead of the art prefetch.
    auto firstArt = std::find_if( m_queue.begin(), m_queue.end(), []( const std::unique_ptr<Transfer>& t ) { return t->Type == Transfer::Kind::Art; } );
    m_queue.insert( firstArt, std::move( transfer ) );
    RefreshRow( inTrack );
}


void DLCMenuController::PumpTransfers()
{
    if( m_active )
    {
        if( m_active->Type == Transfer::Kind::Track && m_active->Track >= 0 )
        {
            CatalogueTrack& track = m_catalogue[m_active->Track];
            const std::string state = "Downloading " + std::to_string( m_active->Done.load() ) + "/" + std::to_string( m_active->Files.size() );
            if( track.State != state )
            {
                track.State = state;
                RefreshRow( m_active->Track );
            }
        }
        if( !m_active->Finished )
        {
            return;
        }
        if( m_active->Thread.joinable() )
        {
            m_active->Thread.join();
        }
        std::unique_ptr<Transfer> finished = std::move( m_active );
        FinishTransfer( *finished );
    }
    if( m_queue.empty() )
    {
        return;
    }
    m_active = std::move( m_queue.front() );
    m_queue.pop_front();
    Transfer* transfer = m_active.get();
    transfer->Thread = std::thread( [transfer]()
    {
        bool ok = true;
        for( const auto& [url, path] : transfer->Files )
        {
            if( transfer->Cancel )
            {
                ok = false;
                break;
            }
            ok = Web::DownloadFile( url, path ) && ok;
            ++transfer->Done;
        }
        transfer->Succeeded = ok;
        transfer->Finished = true;
    } );
}


void DLCMenuController::FinishTransfer( Transfer& inTransfer )
{
    RmlUiCore* ui = GetEngine().RmlUi;
    switch( inTransfer.Type )
    {
    case Transfer::Kind::Index:
    {
        const Path downloaded( kIndexDownloadFile );
        std::string text;
        if( inTransfer.Succeeded && downloaded.Exists )
        {
            text = File( downloaded ).Read();
        }
        std::error_code ec;
        if( !text.empty() && json::parse( text, nullptr, false ).is_array() )
        {
            std::filesystem::rename( downloaded.FullPath, Path( kIndexFile ).FullPath, ec );
            LoadIndex( text, "" );
            ui->ModelSetString( kModel, "status", m_catalogue.empty() ? "The catalogue on " + m_server + " is empty" : std::to_string( m_catalogue.size() ) + " songs on " + m_server );
        }
        else
        {
            std::filesystem::remove( downloaded.FullPath, ec );
            const Path cached( kIndexFile );
            if( cached.Exists )
            {
                LoadIndex( File( cached ).Read(), "Couldn't reach " + m_server + ": showing the last catalogue" );
            }
            else
            {
                LoadIndex( "", "Couldn't reach " + m_server + ". Check the DLC server under Settings." );
            }
        }
        break;
    }
    case Transfer::Kind::Art:
        if( inTransfer.Track >= 0 && inTransfer.Track < static_cast<int>( m_catalogue.size() ) )
        {
            RefreshRow( inTransfer.Track );
            if( inTransfer.Track == m_selectedTrack )
            {
                ui->ModelSetString( kModel, "detail_art", ArtSource( m_catalogue[inTransfer.Track] ) );
            }
        }
        break;
    case Transfer::Kind::Track:
        if( inTransfer.Track >= 0 && inTransfer.Track < static_cast<int>( m_catalogue.size() ) )
        {
            CatalogueTrack& track = m_catalogue[inTransfer.Track];
            track.Busy = false;
            if( inTransfer.Succeeded && TrackDatabase::GetInstance().RegisterNewTrack( track.Folder ) )
            {
                track.InstalledIndex = static_cast<int>( TrackDatabase::GetInstance().m_trackList.m_tracks.size() ) - 1;
                track.State = "Installed";
                m_radioUtils->PlayLatestTrack();
            }
            else if( inTransfer.Succeeded )
            {
                track.InstalledIndex = InstalledIndexOf( track.Folder );
                track.State = track.InstalledIndex >= 0 ? "Installed" : "Failed";
            }
            else
            {
                track.State = "Failed";
            }
            RefreshRow( inTransfer.Track );
            if( inTransfer.Track == m_selectedTrack )
            {
                SelectTrack( inTransfer.Track );
            }
        }
        break;
    }
}


std::vector<int> DLCMenuController::SortedTracks() const
{
    std::vector<int> order;
    for( int i = 0; i < static_cast<int>( m_catalogue.size() ); ++i )
    {
        if( TrackPassesFilter( m_catalogue[i] ) )
        {
            order.push_back( i );
        }
    }
    const auto byTitle = [this]( int a, int b ) { return LessCaseInsensitive( m_catalogue[a].Title, m_catalogue[b].Title ); };
    switch( m_sort )
    {
    case TrackListSort::Title:
        std::stable_sort( order.begin(), order.end(), byTitle );
        break;
    case TrackListSort::Artist:
        std::stable_sort( order.begin(), order.end(), [this, byTitle]( int a, int b )
        {
            const std::string& left = m_catalogue[a].Artist;
            const std::string& right = m_catalogue[b].Artist;
            return LessCaseInsensitive( left, right ) || ( !LessCaseInsensitive( right, left ) && byTitle( a, b ) );
        } );
        break;
    case TrackListSort::Year:
        std::stable_sort( order.begin(), order.end(), [this, byTitle]( int a, int b )
        {
            return m_catalogue[a].Year < m_catalogue[b].Year || ( m_catalogue[a].Year == m_catalogue[b].Year && byTitle( a, b ) );
        } );
        break;
    case TrackListSort::None:
    default:
        break;
    }
    return order;
}


bool DLCMenuController::TrackPassesFilter( const CatalogueTrack& inTrack ) const
{
    return m_filter == TrackListFilter::None || FilterForSource( inTrack.Source ) == m_filter;
}


void DLCMenuController::RefreshRows()
{
    RmlUiCore* ui = GetEngine().RmlUi;
    const std::vector<int> order = SortedTracks();
    const int count = static_cast<int>( std::min<size_t>( order.size(), 4096 ) );
    m_rowOfTrack.assign( m_catalogue.size(), -1 );
    ui->ModelSetListCount( kModel, "tracks", count );
    ui->ModelSetNumber( kModel, "track_count", count );
    const char* sortNames[] = { "Default", "Title", "Artist", "Year" };
    ui->ModelSetNumber( kModel, "sort", static_cast<int>( m_sort ) );
    ui->ModelSetString( kModel, "sort_name", sortNames[static_cast<int>( m_sort ) & 3] );
    ui->ModelSetNumber( kModel, "filter", static_cast<int>( m_filter ) );
    ui->ModelSetString( kModel, "filter_name", m_filter == TrackListFilter::None ? "All songs" : TrackDatabase::GetInstance().GetFilterName( m_filter ) );
    std::string previousCategory;
    for( int row = 0; row < count; ++row )
    {
        const int index = order[row];
        const CatalogueTrack& track = m_catalogue[index];
        std::string category;
        switch( m_sort )
        {
        case TrackListSort::Title: category = Initial( track.Title ); break;
        case TrackListSort::Artist: category = Initial( track.Artist ); break;
        case TrackListSort::Year: category = std::to_string( track.Year ); break;
        default: break;
        }
        ui->ModelSetItemString( kModel, "tracks", row, "category", category != previousCategory ? category : "" );
        previousCategory = category;
        ui->ModelSetItemNumber( kModel, "tracks", row, "index", index );
        ui->ModelSetItemString( kModel, "tracks", row, "title", track.Title );
        ui->ModelSetItemString( kModel, "tracks", row, "artist", track.Artist );
        ui->ModelSetItemNumber( kModel, "tracks", row, "year", track.Year );
        m_rowOfTrack[index] = row;
        RefreshRow( index );
    }
    if( count == 0 )
    {
        m_selectedTrack = -1;
        ui->ModelSetNumber( kModel, "selected", -1 );
    }
    else if( std::find( order.begin(), order.end(), m_selectedTrack ) == order.end() )
    {
        SelectTrack( order.front() );
    }
}


void DLCMenuController::RefreshRow( int inTrack )
{
    if( inTrack < 0 || inTrack >= static_cast<int>( m_rowOfTrack.size() ) || m_rowOfTrack[inTrack] < 0 )
    {
        return;
    }
    RmlUiCore* ui = GetEngine().RmlUi;
    const int row = m_rowOfTrack[inTrack];
    const CatalogueTrack& track = m_catalogue[inTrack];
    ui->ModelSetItemString( kModel, "tracks", row, "art", ArtSource( track ) );
    ui->ModelSetItemNumber( kModel, "tracks", row, "installed", track.InstalledIndex >= 0 );
    ui->ModelSetItemNumber( kModel, "tracks", row, "busy", track.Busy );
    ui->ModelSetItemString( kModel, "tracks", row, "state", track.State );
}


void DLCMenuController::RefreshFilters()
{
    RmlUiCore* ui = GetEngine().RmlUi;
    std::vector<int> counts( static_cast<int>( TrackListFilter::Count ), 0 );
    for( const CatalogueTrack& track : m_catalogue )
    {
        ++counts[static_cast<int>( FilterForSource( track.Source ) )];
    }
    int row = 0;
    ui->ModelSetListCount( kModel, "filters", 0 );
    ui->ModelSetItemNumber( kModel, "filters", row, "index", 0 );
    ui->ModelSetItemString( kModel, "filters", row, "name", "All songs" );
    ui->ModelSetItemNumber( kModel, "filters", row++, "count", static_cast<int>( m_catalogue.size() ) );
    for( int i = 1; i < static_cast<int>( TrackListFilter::Count ); ++i )
    {
        if( counts[i] == 0 )
        {
            continue;
        }
        ui->ModelSetItemNumber( kModel, "filters", row, "index", i );
        ui->ModelSetItemString( kModel, "filters", row, "name", TrackDatabase::GetInstance().GetFilterName( static_cast<TrackListFilter>( i ) ) );
        ui->ModelSetItemNumber( kModel, "filters", row++, "count", counts[i] );
    }
}


void DLCMenuController::SelectTrack( int inTrack )
{
    if( inTrack < 0 || inTrack >= static_cast<int>( m_catalogue.size() ) )
    {
        return;
    }
    RmlUiCore* ui = GetEngine().RmlUi;
    const CatalogueTrack& track = m_catalogue[inTrack];
    if( inTrack != m_selectedTrack && track.InstalledIndex >= 0 )
    {
        // Installed songs preview on the radio like the library does, after a short hover.
        m_previewTrack = inTrack;
        m_previewDelay = 0.25f;
    }
    m_selectedTrack = inTrack;
    ui->ModelSetNumber( kModel, "selected", inTrack );
    ui->ModelSetString( kModel, "detail_title", track.Title );
    ui->ModelSetString( kModel, "detail_artist", track.Artist );
    ui->ModelSetString( kModel, "detail_album", track.Album );
    ui->ModelSetNumber( kModel, "detail_year", track.Year );
    ui->ModelSetString( kModel, "detail_source", FilterForSource( track.Source ) == TrackListFilter::Other ? track.Source : TrackDatabase::GetInstance().GetFilterName( FilterForSource( track.Source ) ) );
    ui->ModelSetString( kModel, "detail_art", ArtSource( track ) );
    ui->ModelSetNumber( kModel, "detail_files", static_cast<int>( track.Files.size() ) );
    ui->ModelSetNumber( kModel, "detail_installed", track.InstalledIndex >= 0 );
    ui->ModelSetNumber( kModel, "detail_busy", track.Busy );
    ui->ModelSetString( kModel, "detail_state", track.State );
    if( track.InstalledIndex >= 0 )
    {
        const auto& tracks = TrackDatabase::GetInstance().m_trackList.m_tracks;
        ui->ModelSetNumber( kModel, "detail_notes", track.InstalledIndex < static_cast<int>( tracks.size() ) ? tracks[track.InstalledIndex].m_noteCount : 0 );
    }
    else
    {
        ui->ModelSetNumber( kModel, "detail_notes", 0 );
    }
}


void DLCMenuController::PlayInstalled( int inTrack )
{
    if( inTrack < 0 || inTrack >= static_cast<int>( m_catalogue.size() ) )
    {
        return;
    }
    const int index = m_catalogue[inTrack].InstalledIndex;
    const auto& tracks = TrackDatabase::GetInstance().m_trackList.m_tracks;
    if( index < 0 || index >= static_cast<int>( tracks.size() ) )
    {
        return;
    }
    const std::string trackId = tracks[index].m_trackSourcePath;
    TrackRadio::GetInstance().Stop();
    LoadSceneEvent event;
    event.Level = "Assets/Example.lvl";
    event.Callback = [trackId, index]()
    {
        LaunchPlayTrackEvent play;
        play.TrackID = trackId;
        play.TrackIndex = index;
        play.Fire();
    };
    event.Queue();
}


void DLCMenuController::PreviewInstalled( int inTrack )
{
    if( inTrack < 0 || inTrack >= static_cast<int>( m_catalogue.size() ) )
    {
        return;
    }
    const int index = m_catalogue[inTrack].InstalledIndex;
    auto& tracks = TrackDatabase::GetInstance().m_trackList.m_tracks;
    if( index < 0 || index >= static_cast<int>( tracks.size() ) )
    {
        return;
    }
    RadioArgs args;
    args.CurrentTrack = &tracks[index];
    args.CurrentTrackIndex = index;
    args.UsePreviewMarker = true;
    TrackRadio::GetInstance().Play( args );
    m_radioUtils->Show();
}


std::string DLCMenuController::ArtSource( const CatalogueTrack& inTrack ) const
{
    const auto& tracks = TrackDatabase::GetInstance().m_trackList.m_tracks;
    if( inTrack.InstalledIndex >= 0 && inTrack.InstalledIndex < static_cast<int>( tracks.size() ) )
    {
        return TrackRadioUtils::ArtSource( tracks[inTrack.InstalledIndex] );
    }
    if( !inTrack.ArtFile.empty() )
    {
        const Path art = ArtCachePath( inTrack );
        if( art.Exists && art.IsFile )
        {
            return "/" + art.GetLocalPathString();
        }
    }
    return "img/track-bg.png";
}


Path DLCMenuController::ArtCachePath( const CatalogueTrack& inTrack ) const
{
    return Path( kArtCache + inTrack.Folder + "/" + inTrack.ArtFile );
}


std::string DLCMenuController::FileURL( const CatalogueTrack& inTrack, const std::string& inFile ) const
{
    return m_server + "/" + inTrack.Folder + "/" + inFile;
}


Path DLCMenuController::FilePath( const CatalogueTrack& inTrack, const std::string& inFile ) const
{
    return Path( "Assets/DLC/" + inTrack.Folder + "/" + inFile );
}


void DLCMenuController::Update( float inDeltaTime )
{
    m_radioUtils->OnUpdate( inDeltaTime );
    if( !m_modelReady )
    {
        PopulateModel();
    }
    RmlUiCore* ui = GetEngine().RmlUi;
    if( !ui )
    {
        return;
    }
    PumpTransfers();

    if( GetEngine().GetInput().WasKeyPressed( KeyCode::Escape ) )
    {
        if( ui->ModelGetNumber( kModel, "filters_open" ) != 0 )
        {
            ui->ModelSetNumber( kModel, "filters_open", 0 );
        }
        else
        {
            LoadSceneEvent event;
            event.Level = "Assets/MainMenu.lvl";
            event.Queue();
            return;
        }
    }

    for( std::string event; !( event = ui->ModelPollEvent( kModel ) ).empty(); )
    {
        const json args = UIModel::LastEventArgs( *ui, kModel );
        const int index = static_cast<int>( UIModel::ArgNumber( args, 0, -1.0 ) );
        if( m_radioUtils->HandleEvent( event, args ) )
        {
            continue;
        }
        if( event == "select" )
        {
            SelectTrack( index );
        }
        else if( event == "download" )
        {
            QueueTrackDownload( index );
            if( index == m_selectedTrack )
            {
                SelectTrack( index );
            }
        }
        else if( event == "play" )
        {
            PlayInstalled( index );
            return;
        }
        else if( event == "preview" )
        {
            m_previewTrack = -1;
            PreviewInstalled( index );
        }
        else if( event == "edit" && index >= 0 && index < static_cast<int>( m_catalogue.size() ) )
        {
            EditTrackEvent edit;
            edit.FileName = m_catalogue[index].Title;
            edit.Fire();
        }
        else if( event == "toggle_filters" )
        {
            ui->ModelSetNumber( kModel, "filters_open", ui->ModelGetNumber( kModel, "filters_open" ) == 0 );
        }
        else if( event == "toggle_details" )
        {
            ui->ModelSetNumber( kModel, "details_open", ui->ModelGetNumber( kModel, "details_open" ) == 0 );
        }
        else if( event == "sort" && index >= 0 && index <= 3 )
        {
            m_sort = static_cast<TrackListSort>( index );
            RefreshRows();
            ui->ModelSetNumber( kModel, "filters_open", 0 );
        }
        else if( event == "filter" && index >= 0 && index < static_cast<int>( TrackListFilter::Count ) )
        {
            m_filter = static_cast<TrackListFilter>( index );
            RefreshRows();
            ui->ModelSetNumber( kModel, "filters_open", 0 );
        }
        else if( event == "refresh" )
        {
            // Not while a song is downloading: its rows would be rebuilt under it.
            const bool downloading = std::any_of( m_catalogue.begin(), m_catalogue.end(), []( const CatalogueTrack& t ) { return t.Busy; } );
            if( !downloading )
            {
                m_queue.clear();
                if( m_active )
                {
                    m_active->Track = -1;   // An art prefetch in flight no longer has a row
                }
                BeginIndexFetch();
            }
        }
    }

    if( m_previewTrack >= 0 && ( m_previewDelay -= inDeltaTime ) <= 0.f )
    {
        const int track = m_previewTrack;
        m_previewTrack = -1;
        PreviewInstalled( track );
    }
}
