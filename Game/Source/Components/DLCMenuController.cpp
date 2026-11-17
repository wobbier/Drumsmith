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
#include "UI/MusicLinks.h"
#include "UI/UIModelUtils.h"
#include "Web/HttpDownload.h"
#include <algorithm>
#include <cctype>
#include <filesystem>
#include <fstream>
#include <iterator>

namespace
{
    constexpr const char* kModel = "dlc_store";
    // Each server's index is cached under the catalogue cache, beside the hash it had when it
    // was fetched. Downloads land in ".download" files first, so a failed fetch can't truncate
    // the cached copy.
    constexpr const char* kIndexFile = "dlc_index.json";
    constexpr const char* kHashFile = "dlc_index.hash";
    constexpr const char* kDownloadSuffix = ".download";
    // What a song folder was installed from: { "Server", "Version" } (dot-files aren't served).
    constexpr const char* kInstallNote = ".dlc.json";
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


    TrackListFilter FilterForSource( const std::string& inSource )
    {
        return TrackDatabase::FilterForSource( inSource );
    }


    // The file as it is on disk now (a Path remembers whether it existed when it was made,
    // which for a download target was before the download).
    std::string ReadText( const Path& inPath )
    {
        std::ifstream file( inPath.FullPath, std::ios::binary );
        if( !file )
        {
            return {};
        }
        return std::string( std::istreambuf_iterator<char>( file ), std::istreambuf_iterator<char>() );
    }


    // A dlc_index.hash is one short token; anything else (an error page) is no hash.
    std::string CleanHash( const std::string& inText )
    {
        const std::string hash = Trim( inText );
        if( hash.empty() || hash.size() > 128 )
        {
            return {};
        }
        for( unsigned char c : hash )
        {
            if( !std::isalnum( c ) )
            {
                return {};
            }
        }
        return hash;
    }


    // A song folder name that can only mean a folder directly under Assets/DLC.
    bool SafeFolder( const std::string& inFolder )
    {
        return !inFolder.empty() && inFolder != "." && inFolder != ".." && inFolder.front() != '.'
            && inFolder.find_first_of( "/\\" ) == std::string::npos;
    }


    bool SafeFile( const std::string& inFile )
    {
        return !inFile.empty() && inFile.find( ".." ) == std::string::npos && inFile.front() != '/' && inFile.find( '\\' ) == std::string::npos;
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
    for( const char* event : { "select", "download", "update", "play", "preview", "edit", "remove", "remove_confirm", "remove_cancel", "sort", "filter", "toggle_filters", "toggle_details", "refresh", "listen" } )
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
    for( const char* key : { "detail_title", "detail_artist", "detail_album", "detail_source", "detail_art", "detail_state", "detail_badge", "detail_server" } )
    {
        ui->ModelSetString( kModel, key, "" );
    }
    for( const char* key : { "detail_year", "detail_files", "detail_installed", "detail_busy", "detail_notes", "detail_update", "detail_ds_ready", "detail_confirm_remove" } )
    {
        ui->ModelSetNumber( kModel, key, 0 );
    }
    ui->ModelSetListCount( kModel, "tracks", 0 );
    RefreshFilters();
    RefreshRows();
    m_modelReady = true;
    BeginIndexFetch();
}


std::string DLCMenuController::ServerCacheFolder( int inServer ) const
{
    std::string name;
    for( unsigned char c : m_servers[inServer].Url )
    {
        name += std::isalnum( c ) || c == '.' || c == '-' ? static_cast<char>( c ) : '_';
    }
    return std::string( kArtCache ) + "_servers/" + name + "/";
}


void DLCMenuController::BeginIndexFetch()
{
    RmlUiCore* ui = GetEngine().RmlUi;
    m_catalogue.clear();
    m_servers.clear();
    m_selectedTrack = -1;
    m_previewTrack = -1;
    m_confirmRemove = -1;
    for( const std::string& url : GameSettings::GetInstance().DLCServers )
    {
        Server server;
        server.Url = url;
        m_servers.push_back( server );
    }
    m_pendingServers = static_cast<int>( m_servers.size() );
    RefreshFilters();
    RefreshRows();
    if( m_servers.empty() )
    {
        ui->ModelSetNumber( kModel, "loading", 0 );
        ui->ModelSetString( kModel, "server", "" );
        ui->ModelSetString( kModel, "status", "No DLC server set. Add one under Settings on the main menu." );
        return;
    }
    ui->ModelSetString( kModel, "server", m_servers.front().Url );
    ui->ModelSetNumber( kModel, "loading", 1 );
    UpdateStatus();
    // A server's index is only fetched when its hash differs from the cached copy's: the hash is
    // a few bytes, the index of a big server isn't.
    for( int i = static_cast<int>( m_servers.size() ) - 1; i >= 0; --i )
    {
        auto transfer = std::make_unique<Transfer>();
        transfer->Type = Transfer::Kind::Hash;
        transfer->Server = i;
        transfer->Files.push_back( { m_servers[i].Url + "/" + kHashFile, Path( ServerCacheFolder( i ) + kHashFile + kDownloadSuffix ), -1 } );
        m_queue.push_front( std::move( transfer ) );
    }
}


void DLCMenuController::UpdateStatus()
{
    RmlUiCore* ui = GetEngine().RmlUi;
    std::string unreachable;
    int loaded = 0;
    for( const Server& server : m_servers )
    {
        loaded += server.Loaded ? 1 : 0;
        if( server.Loaded && !server.Reached )
        {
            unreachable += ( unreachable.empty() ? "" : ", " ) + server.Url;
        }
    }
    std::string status;
    if( m_pendingServers > 0 )
    {
        status = "Loading the catalogue (" + std::to_string( loaded + 1 ) + " of " + std::to_string( m_servers.size() ) + ")...";
    }
    else if( m_servers.size() == 1 )
    {
        status = m_catalogue.empty() ? "The catalogue on " + m_servers.front().Url + " is empty" : std::to_string( m_catalogue.size() ) + " songs on " + m_servers.front().Url;
    }
    else
    {
        status = std::to_string( m_catalogue.size() ) + " songs on " + std::to_string( m_servers.size() ) + " servers";
    }
    if( !unreachable.empty() )
    {
        status += ". Couldn't reach " + unreachable + ": showing the last catalogue. Check the DLC servers under Settings.";
    }
    ui->ModelSetNumber( kModel, "loading", m_pendingServers > 0 );
    ui->ModelSetString( kModel, "status", status );
}


void DLCMenuController::LoadCachedIndex( int inServer )
{
    AppendIndex( inServer, ReadText( Path( ServerCacheFolder( inServer ) + kIndexFile ) ) );
}


void DLCMenuController::AppendIndex( int inServer, const std::string& inText )
{
    Server& server = m_servers[inServer];
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
            track.Server = inServer;
            track.Title = JsonString( entry, "Title" );
            track.Artist = JsonString( entry, "Artist" );
            track.Album = JsonString( entry, "Album" );
            track.Source = JsonString( entry, "DLCSource" );
            track.Folder = JsonString( entry, "FolderPath" );
            track.ArtFile = JsonString( entry, "AlbumArtFileName" );
            track.AudioFile = JsonString( entry, "TrackFileName" );
            track.Version = JsonString( entry, "Version" );
            const auto year = entry.find( "Year" );
            track.Year = year != entry.end() && year->is_number() ? year->get<int>() : 0;
            const auto preview = entry.find( "PreviewPercent" );
            if( preview != entry.end() && preview->is_number() )
            {
                track.PreviewPercent = std::clamp( preview->get<float>(), 0.f, 0.95f );
            }
            const auto authored = entry.find( "Authored" );
            track.Authored = authored != entry.end() && authored->is_boolean() && authored->get<bool>();
            const auto files = entry.find( "FilesInFolder" );
            const auto sizes = entry.find( "FileSizes" );
            const bool hasSizes = files != entry.end() && sizes != entry.end() && files->is_array() && sizes->is_array() && sizes->size() == files->size();
            if( files != entry.end() && files->is_array() )
            {
                for( size_t i = 0; i < files->size(); ++i )
                {
                    const json& file = ( *files )[i];
                    if( !file.is_string() || !SafeFile( file.get<std::string>() ) )
                    {
                        continue;
                    }
                    track.Files.push_back( file.get<std::string>() );
                    if( hasSizes )
                    {
                        track.FileSizes.push_back( ( *sizes )[i].is_number() ? ( *sizes )[i].get<long long>() : -1 );
                    }
                }
            }
            // The server's own index lists itself when it was generated at the DLC root, and a
            // folder name is used as a path here: only plain names are songs.
            if( !SafeFolder( track.Folder ) || track.Files.empty() || !SafeFile( track.ArtFile.empty() ? "x" : track.ArtFile ) )
            {
                continue;
            }
            // Listed by an earlier server too: the first one in the settings wins.
            if( std::any_of( m_catalogue.begin(), m_catalogue.end(), [&track]( const CatalogueTrack& t ) { return t.Folder == track.Folder; } ) )
            {
                continue;
            }
            RefreshInstallState( track );
            m_catalogue.push_back( std::move( track ) );
            ++server.Songs;
        }
    }
    else if( !inText.empty() )
    {
        YIKES( "DLC: the catalogue index of " + server.Url + " isn't a JSON array" );
    }
    server.Loaded = true;
    m_pendingServers = std::max( 0, m_pendingServers - 1 );
    UpdateStatus();
    RefreshFilters();
    RefreshRows();
    QueueMissingArt();
}


void DLCMenuController::RefreshInstallState( CatalogueTrack& ioTrack ) const
{
    ioTrack.InstalledIndex = InstalledIndexOf( ioTrack.Folder );
    ioTrack.UpdateAvailable = false;
    if( ioTrack.InstalledIndex < 0 )
    {
        if( !ioTrack.Busy )
        {
            ioTrack.State.clear();
        }
        return;
    }
    // The copy on disk says what it was installed from; a song that doesn't (converted here,
    // or downloaded before versions) is left alone.
    const json note = json::parse( ReadText( FilePath( ioTrack, kInstallNote ) ), nullptr, false );
    const std::string installed = note.is_object() ? JsonString( note, "Version" ) : std::string();
    ioTrack.UpdateAvailable = !installed.empty() && !ioTrack.Version.empty() && installed != ioTrack.Version;
    if( !ioTrack.Busy )
    {
        ioTrack.State = ioTrack.UpdateAvailable ? "Update available" : "Installed";
    }
}


void DLCMenuController::QueueMissingArt()
{
    for( int i = 0; i < static_cast<int>( m_catalogue.size() ); ++i )
    {
        CatalogueTrack& track = m_catalogue[i];
        if( track.ArtQueued || track.ArtFile.empty() || track.ArtFile.back() == '/' || track.InstalledIndex >= 0 || ArtCachePath( track ).Exists )
        {
            continue;
        }
        track.ArtQueued = true;
        auto transfer = std::make_unique<Transfer>();
        transfer->Type = Transfer::Kind::Art;
        transfer->Track = i;
        transfer->Files.push_back( { FileURL( track, track.ArtFile ), ArtCachePath( track ), -1 } );
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
    // A new song, or an installed one the server has a newer copy of.
    if( track.Busy || ( track.InstalledIndex >= 0 && !track.UpdateAvailable ) )
    {
        return;
    }
    if( m_confirmRemove == inTrack )
    {
        m_confirmRemove = -1;
    }
    auto transfer = std::make_unique<Transfer>();
    transfer->Type = Transfer::Kind::Track;
    transfer->Track = inTrack;
    for( size_t i = 0; i < track.Files.size(); ++i )
    {
        transfer->Files.push_back( { FileURL( track, track.Files[i] ), FilePath( track, track.Files[i] ), i < track.FileSizes.size() ? track.FileSizes[i] : -1 } );
    }
    track.Busy = true;
    track.State = "Queued";
    // Songs the player asked for go ahead of the art prefetch.
    auto firstArt = std::find_if( m_queue.begin(), m_queue.end(), []( const std::unique_ptr<Transfer>& t ) { return t->Type == Transfer::Kind::Art; } );
    m_queue.insert( firstArt, std::move( transfer ) );
    RefreshRow( inTrack );
}


Path DLCMenuController::PreviewPath( const CatalogueTrack& inTrack ) const
{
    // The main mix: what the index names, else song.ogg, else the first audio file listed.
    std::string audio = inTrack.AudioFile;
    const auto listed = [&inTrack]( const std::string& inFile ) { return std::find( inTrack.Files.begin(), inTrack.Files.end(), inFile ) != inTrack.Files.end(); };
    if( audio.empty() || !listed( audio ) )
    {
        audio = listed( "song.ogg" ) ? "song.ogg" : std::string();
        for( size_t i = 0; audio.empty() && i < inTrack.Files.size(); ++i )
        {
            const std::string& file = inTrack.Files[i];
            if( file.size() > 4 && ( file.rfind( ".ogg" ) == file.size() - 4 || file.rfind( ".mp3" ) == file.size() - 4 ) )
            {
                audio = file;
            }
        }
    }
    return audio.empty() ? Path() : Path( kArtCache + inTrack.Folder + "/" + audio );
}


void DLCMenuController::QueuePreview( int inTrack )
{
    if( inTrack < 0 || inTrack >= static_cast<int>( m_catalogue.size() ) )
    {
        return;
    }
    CatalogueTrack& track = m_catalogue[inTrack];
    if( track.InstalledIndex >= 0 )
    {
        PreviewInstalled( inTrack );
        return;
    }
    const Path audio = PreviewPath( track );
    if( track.Busy || audio.FullPath.empty() )
    {
        return;
    }
    // Not downloaded yet: fetch its main mix into the catalogue cache and play that. One preview
    // is kept at a time; the last one's file goes when another is asked for.
    const bool pending = std::any_of( m_queue.begin(), m_queue.end(), [inTrack]( const std::unique_ptr<Transfer>& t ) { return t->Type == Transfer::Kind::Preview && t->Track == inTrack; } )
        || ( m_active && m_active->Type == Transfer::Kind::Preview && m_active->Track == inTrack );
    if( pending )
    {
        return;
    }
    m_queue.erase( std::remove_if( m_queue.begin(), m_queue.end(), []( const std::unique_ptr<Transfer>& t ) { return t->Type == Transfer::Kind::Preview; } ), m_queue.end() );
    for( CatalogueTrack& other : m_catalogue )
    {
        if( other.State == "Fetching preview..." )
        {
            other.State.clear();
        }
    }
    auto transfer = std::make_unique<Transfer>();
    transfer->Type = Transfer::Kind::Preview;
    transfer->Track = inTrack;
    const std::string audioName = audio.GetFileNameString();
    long long size = -1;
    for( size_t i = 0; i < track.Files.size() && i < track.FileSizes.size(); ++i )
    {
        if( track.Files[i] == audioName )
        {
            size = track.FileSizes[i];
        }
    }
    transfer->Files.push_back( { FileURL( track, audioName ), audio, size } );
    track.State = "Fetching preview...";
    auto firstArt = std::find_if( m_queue.begin(), m_queue.end(), []( const std::unique_ptr<Transfer>& t ) { return t->Type == Transfer::Kind::Art; } );
    m_queue.insert( firstArt, std::move( transfer ) );
    RefreshRows();
    if( inTrack == m_selectedTrack )
    {
        SelectTrack( inTrack );
    }
}


void DLCMenuController::RemoveInstalled( int inTrack )
{
    if( inTrack < 0 || inTrack >= static_cast<int>( m_catalogue.size() ) )
    {
        return;
    }
    CatalogueTrack& track = m_catalogue[inTrack];
    if( track.Busy || track.InstalledIndex < 0 )
    {
        return;
    }
    RmlUiCore* ui = GetEngine().RmlUi;
    const std::string title = track.Title;
    if( !TrackDatabase::GetInstance().RemoveTrack( track.InstalledIndex ) )
    {
        ui->ModelSetString( kModel, "status", "Couldn't remove " + title );
        return;
    }
    // Every library index after it moved down one.
    for( CatalogueTrack& other : m_catalogue )
    {
        RefreshInstallState( other );
    }
    m_previewTrack = -1;
    RefreshRows();
    SelectTrack( inTrack );
    QueueMissingArt();
    ui->ModelSetString( kModel, "status", "Removed " + title );
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
        for( const Transfer::FileJob& file : transfer->Files )
        {
            if( transfer->Cancel )
            {
                ok = false;
                break;
            }
            bool fileOk = Web::DownloadFile( file.Url, file.Target );
            if( fileOk && file.Size >= 0 )
            {
                // The index says how big it is: a short or padded file is a broken download.
                std::error_code error;
                const auto size = std::filesystem::file_size( file.Target.FullPath, error );
                fileOk = !error && static_cast<long long>( size ) == file.Size;
            }
            ok = fileOk && ok;
            ++transfer->Done;
        }
        transfer->Succeeded = ok;
        transfer->Finished = true;
    } );
}


void DLCMenuController::FinishTransfer( Transfer& inTransfer )
{
    RmlUiCore* ui = GetEngine().RmlUi;
    std::error_code ec;
    switch( inTransfer.Type )
    {
    case Transfer::Kind::Hash:
    {
        if( inTransfer.Server < 0 || inTransfer.Server >= static_cast<int>( m_servers.size() ) )
        {
            break;
        }
        Server& server = m_servers[inTransfer.Server];
        const std::string folder = ServerCacheFolder( inTransfer.Server );
        const Path downloaded = inTransfer.Files.front().Target;
        server.RemoteHash = inTransfer.Succeeded ? CleanHash( ReadText( downloaded ) ) : std::string();
        std::filesystem::remove( downloaded.FullPath, ec );
        const std::string cachedHash = CleanHash( ReadText( Path( folder + kHashFile ) ) );
        if( !server.RemoteHash.empty() && server.RemoteHash == cachedHash && Path( folder + kIndexFile ).Exists )
        {
            // Nothing changed on the server since the cached copy.
            LoadCachedIndex( inTransfer.Server );
            break;
        }
        // Changed, never fetched, or a server without a hash file: get the index itself.
        auto transfer = std::make_unique<Transfer>();
        transfer->Type = Transfer::Kind::Index;
        transfer->Server = inTransfer.Server;
        transfer->Files.push_back( { server.Url + "/" + kIndexFile, Path( folder + kIndexFile + kDownloadSuffix ), -1 } );
        m_queue.push_front( std::move( transfer ) );
        break;
    }
    case Transfer::Kind::Index:
    {
        if( inTransfer.Server < 0 || inTransfer.Server >= static_cast<int>( m_servers.size() ) )
        {
            break;
        }
        Server& server = m_servers[inTransfer.Server];
        const std::string folder = ServerCacheFolder( inTransfer.Server );
        const Path downloaded = inTransfer.Files.front().Target;
        const std::string text = inTransfer.Succeeded ? ReadText( downloaded ) : std::string();
        if( !text.empty() && json::parse( text, nullptr, false ).is_array() )
        {
            std::filesystem::rename( downloaded.FullPath, Path( folder + kIndexFile ).FullPath, ec );
            // The hash this copy answers to, so the next visit can skip the download.
            if( server.RemoteHash.empty() )
            {
                std::filesystem::remove( Path( folder + kHashFile ).FullPath, ec );
            }
            else
            {
                File( Path( folder + kHashFile ) ).Write( server.RemoteHash );
            }
            AppendIndex( inTransfer.Server, text );
        }
        else
        {
            std::filesystem::remove( downloaded.FullPath, ec );
            server.Reached = false;
            LoadCachedIndex( inTransfer.Server );
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
    case Transfer::Kind::Preview:
        if( inTransfer.Track >= 0 && inTransfer.Track < static_cast<int>( m_catalogue.size() ) )
        {
            CatalogueTrack& track = m_catalogue[inTransfer.Track];
            const Path audio = inTransfer.Files.front().Target;
            if( track.State == "Fetching preview..." )
            {
                track.State.clear();
            }
            if( inTransfer.Succeeded && std::filesystem::is_regular_file( audio.FullPath, ec ) && track.InstalledIndex < 0 )
            {
                // The radio plays it as a guest: a song that isn't in the library.
                if( !m_previewFile.empty() && m_previewFile != audio.FullPath )
                {
                    std::filesystem::remove( m_previewFile, ec );
                }
                m_previewFile = audio.FullPath;
                TrackData guest;
                guest.m_trackName = track.Title;
                guest.m_artistName = track.Artist;
                guest.m_albumName = track.Album;
                guest.m_year = track.Year;
                guest.m_trackFileName = audio.GetFileNameString();
                guest.m_trackSourcePath = audio.FullPath;
                guest.m_albumArtFilename = track.ArtFile;
                guest.m_albumArtPath = track.ArtFile.empty() ? std::string() : ArtCachePath( track ).FullPath;
                guest.m_previewPercent = track.PreviewPercent;
                TrackRadio::GetInstance().PlayGuest( guest, true );
                m_radioUtils->Show();
            }
            else if( track.InstalledIndex < 0 )
            {
                std::filesystem::remove( audio.FullPath, ec );
                track.State = "Preview failed";
            }
            RefreshRow( inTransfer.Track );
            if( inTransfer.Track == m_selectedTrack )
            {
                SelectTrack( inTransfer.Track );
            }
        }
        break;
    case Transfer::Kind::Track:
        if( inTransfer.Track >= 0 && inTransfer.Track < static_cast<int>( m_catalogue.size() ) )
        {
            CatalogueTrack& track = m_catalogue[inTransfer.Track];
            const bool wasInstalled = track.InstalledIndex >= 0;
            track.Busy = false;
            // Every file arrived at its size, and the song's own data reads as JSON.
            const bool intact = inTransfer.Succeeded && json::parse( ReadText( FilePath( track, "TrackData.txt" ) ), nullptr, false ).is_object();
            if( intact )
            {
                json note;
                note["Server"] = m_servers[track.Server].Url;
                note["Version"] = track.Version;
                File( FilePath( track, kInstallNote ) ).Write( note.dump() );
            }
            if( intact && wasInstalled )
            {
                // An update: the files changed under the library's entry.
                TrackDatabase::GetInstance().ReloadTrack( track.InstalledIndex );
                RefreshInstallState( track );
                track.State = "Updated";
            }
            else if( intact && TrackDatabase::GetInstance().RegisterNewTrack( track.Folder ) )
            {
                RefreshInstallState( track );
                m_radioUtils->PlayLatestTrack();
            }
            else if( intact )
            {
                RefreshInstallState( track );
                if( track.InstalledIndex < 0 )
                {
                    track.State = "Failed";
                }
            }
            else if( wasInstalled )
            {
                // The old copy may be part overwritten; the update stays on offer.
                track.State = "Update failed";
            }
            else
            {
                // Half a song would show up as a playable one on the next scan: take it away.
                if( SafeFolder( track.Folder ) )
                {
                    std::filesystem::remove_all( Path( "Assets/DLC/" + track.Folder ).FullPath, ec );
                }
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
    ui->ModelSetItemNumber( kModel, "tracks", row, "update", track.UpdateAvailable && !track.Busy );
    ui->ModelSetItemString( kModel, "tracks", row, "badge", TrackDatabase::SourceBadge( FilterForSource( track.Source ) ) );
    ui->ModelSetItemNumber( kModel, "tracks", row, "ds_ready", track.Authored );
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
    if( inTrack != m_confirmRemove )
    {
        m_confirmRemove = -1;
    }
    m_selectedTrack = inTrack;
    ui->ModelSetNumber( kModel, "selected", inTrack );
    ui->ModelSetNumber( kModel, "detail_update", track.UpdateAvailable && !track.Busy );
    ui->ModelSetNumber( kModel, "detail_ds_ready", track.Authored );
    ui->ModelSetNumber( kModel, "detail_confirm_remove", m_confirmRemove == inTrack );
    ui->ModelSetString( kModel, "detail_badge", TrackDatabase::SourceBadge( FilterForSource( track.Source ) ) );
    ui->ModelSetString( kModel, "detail_server", m_servers.size() > 1 && track.Server < static_cast<int>( m_servers.size() ) ? "From " + m_servers[track.Server].Url : std::string() );
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
    TrackRadioUtils::LaunchTrack( m_catalogue[inTrack].InstalledIndex );
}


void DLCMenuController::EditInstalled( int inTrack )
{
    // The Track Editor (editor builds) opens a song by its library title, which an update may
    // have changed from the catalogue's.
    const auto& tracks = TrackDatabase::GetInstance().m_trackList.m_tracks;
    if( inTrack < 0 || inTrack >= static_cast<int>( m_catalogue.size() ) )
    {
        return;
    }
    const int index = m_catalogue[inTrack].InstalledIndex;
    if( index < 0 || index >= static_cast<int>( tracks.size() ) )
    {
        return;
    }
    EditTrackEvent edit;
    edit.FileName = tracks[index].m_trackName;
    edit.Fire();
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
    return m_servers[inTrack.Server].Url + "/" + inTrack.Folder + "/" + inFile;
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

#if USING( ME_EDITOR )
    // F4 pulls up the Track Editor on the selected song, once it is installed.
    if( GetEngine().GetInput().WasKeyPressed( KeyCode::F4 ) && m_selectedTrack >= 0 && m_selectedTrack < static_cast<int>( m_catalogue.size() ) && m_catalogue[m_selectedTrack].InstalledIndex >= 0 )
    {
        EditInstalled( m_selectedTrack );
    }
#endif

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
        else if( event == "download" || event == "update" )
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
            QueuePreview( index );
        }
        else if( event == "remove" && index >= 0 && index < static_cast<int>( m_catalogue.size() ) )
        {
            // Asked once; the details panel then offers the yes that deletes the files.
            m_confirmRemove = index;
            SelectTrack( index );
        }
        else if( event == "remove_cancel" )
        {
            m_confirmRemove = -1;
            SelectTrack( m_selectedTrack );
        }
        else if( event == "remove_confirm" )
        {
            const int track = m_confirmRemove;
            m_confirmRemove = -1;
            RemoveInstalled( track );
        }
        else if( event == "edit" && index >= 0 && index < static_cast<int>( m_catalogue.size() ) )
        {
            EditInstalled( index );
        }
        else if( event == "listen" && index >= 0 && index < static_cast<int>( MusicLinks::Service::Count ) && m_selectedTrack >= 0 && m_selectedTrack < static_cast<int>( m_catalogue.size() ) )
        {
            // The song on a streaming service, in the player's browser.
            const CatalogueTrack& track = m_catalogue[m_selectedTrack];
            MusicLinks::Open( static_cast<MusicLinks::Service>( index ), track.Artist, track.Title );
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
                    // Whatever is in flight (art, a preview, an index) belongs to the old list.
                    m_active->Track = -1;
                    m_active->Server = -1;
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
