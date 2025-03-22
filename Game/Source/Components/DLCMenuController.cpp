#include <Components/DLCMenuController.h>

#include <Events/SceneEvents.h>
#include "CoreGame/TrackList.h"
#include "Events/GameEvents.h"
#include "Global/TrackRadio.h"
#include "Web/HttpDownload.h"
#include "Config/GameSettings.h"
#include "UI/TrackRadioUtils.h"


DLCMenuController::DLCMenuController()
    : BasicUIView( "DLCMenuController" )
    , m_radioUtils( new TrackRadioUtils( *this ) )
{
    FilePath = Path( "Assets/UI/DLC_NEW.html" );
    m_playAudioCallback = [this]( SharedPtr<AudioSource> playedAudioSource )
        {
            if( m_currentTrack != playedAudioSource )
            {
                if( m_currentTrack )
                {
                    m_currentTrack->Stop( true );
                }
                m_currentTrack = playedAudioSource;
            }
            else
            {
                if( m_currentTrack && m_currentTrack->IsPlaying() )
                {
                    m_currentTrack->Stop( true );
                }
            }
        };
}

DLCMenuController::~DLCMenuController()
{
    delete m_radioUtils;
}

#if USING( ME_UI )


void DLCMenuController::OnJSReady( ultralight::JSObject& GlobalWindow, ultralight::View* Caller )
{
    BasicUIView::OnJSReady( GlobalWindow, Caller );

    GlobalWindow["GetDLCURL"] = BindJSCallbackWithRetval( &DLCMenuController::GetDLCURL );

    m_radioUtils->PlayNextRandomTrack();
}


void DLCMenuController::OnUILoad( ultralight::JSObject& GlobalWindow, ultralight::View* Caller )
{
    BasicUIView::OnUILoad( GlobalWindow, Caller );

    m_radioUtils->OnUILoad( GlobalWindow, Caller );

    GlobalWindow["SelectTrackToPlay"] = BindJSCallback( &DLCMenuController::SelectTrackToPlay );
    GlobalWindow["PlayTrackPreview"] = BindJSCallback( &DLCMenuController::PlayTrackPreview );
    GlobalWindow["FilterSortTracks"] = BindJSCallback( &DLCMenuController::SortTracks );
    GlobalWindow["FilterTracks"] = BindJSCallback( &DLCMenuController::FilterTracks );
    GlobalWindow["ViewTrackStats"] = BindJSCallback( &DLCMenuController::ViewTrackStats );
    GlobalWindow["RequestDetailsPanelUpdate"] = BindJSCallback( &DLCMenuController::RequestDetailsPanelUpdate );
    GlobalWindow["DownloadDLC"] = BindJSCallback( &DLCMenuController::DownloadDLC );

    // Move to a base Drumsmith UI class
    GlobalWindow["EditTrack"] = BindJSCallback( &DLCMenuController::EditTrack );

    //RefreshTrackList( TrackDatabase::GetInstance().m_currentSort, TrackDatabase::GetInstance().m_currentFilter );
}


void DLCMenuController::SelectTrackToPlay( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    ultralight::String path = args[0].ToString();
    int index = args[1].ToInteger();

    TrackRadio::GetInstance().Stop();
    SharedPtr<LoadSceneEvent> loadSceneEvent = MakeShared<LoadSceneEvent>();
    loadSceneEvent->Level = "Assets/Example.lvl";
    EventManager::GetInstance().QueueEvent( loadSceneEvent );

    loadSceneEvent->Callback = [path, index]()
        {
            LaunchPlayTrackEvent evt;
            evt.TrackID = std::string( path.utf8().data() );
            evt.TrackIndex = index;
            evt.Fire();
        };
}


void DLCMenuController::ViewTrackStats( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    //ultralight::String path = args[0].ToString();
    //int index = args[1].ToInteger();

    SharedPtr<LoadSceneEvent> loadSceneEvent = MakeShared<LoadSceneEvent>();
    loadSceneEvent->Level = "Assets/TrackStats.lvl";
    EventManager::GetInstance().QueueEvent( loadSceneEvent );

    //loadSceneEvent->Callback = [path, index]() {
    //    LaunchPlayTrackEvent evt;
    //    evt.TrackID = std::string( path.utf8().data() );
    //    evt.TrackIndex = index;
    //    evt.Fire();
    //    };
}


void DLCMenuController::EditTrack( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    if( args.empty() || !args[0].IsString() )
    {
        BRUH( "EditTrack(string) argument mismatch." );
        return;
    }
    ultralight::String str = args[0].ToString();
    std::string str2( str.utf8().data() );
    EditTrackEvent evt;
    evt.FileName = str2;
    evt.Fire();
}


void DownloadDLC_Internal( std::string inURL, std::string inFolder, std::string inFile )
{
    Web::DownloadFile( inURL + "/" + inFolder + "/" + inFile, Path( "Assets/DLC/" + inFolder + "/" + inFile ) );
}

void DLCMenuController::DownloadDLC( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    ultralight::JSString str = args[0].ToString();
    std::string jsonStr = ultralight::String( str ).utf8().data();
    std::string folderPath;
    //if( str.HasProperty( "FolderPath" ) )
    //{
    //    folderPath = ultralight::String(str["FolderPath"].ToString()).utf8().data();
    //}
    //std::string lmfaooo = str.utf8().data();
    //json data = json::parse( lmfaooo );
    try
    {
// Parse the JSON string
        nlohmann::json trackData = nlohmann::json::parse( jsonStr );

        // Access properties of the track object
        folderPath = trackData["FolderPath"];
        std::string songName = trackData["Title"];
        std::string songArtist = trackData["Artist"];
        //int noteCount = trackData["NoteCount"];
        // Get the list of files in the folder
        std::vector<std::string> filesInFolder = trackData["FilesInFolder"].get<std::vector<std::string>>();

        // Loop through each file in FilesInFolder and download it
        for( const auto& fileName : filesInFolder )
        {
// Download each file from the folder path
            DownloadDLC_Internal( GameSettings::GetInstance().DLCURL, folderPath, fileName );
        }

        // Optional: Log successful download
        std::cout << "Downloaded DLC for song: " << songName << " by " << songArtist << std::endl;
    }
    catch( const std::exception& e )
    {
        std::cerr << "Error parsing JSON: " << e.what() << std::endl;
    }
    //TrackRadio::GetInstance().Stop();
    bool isNew = TrackDatabase::GetInstance().RegisterNewTrack( folderPath );
    //TrackDatabase::GetInstance().Reload();
    if( isNew )
    {
        m_radioUtils->PlayLatestTrack();
    }
    else
    {
        m_radioUtils->PlayNextRandomTrack();
    }
}


ultralight::JSValue DLCMenuController::GetDLCURL( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    return ultralight::JSValue( GameSettings::GetInstance().DLCURL.c_str() );
}

void DLCMenuController::PlayTrackPreview( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    // stupid, make it not a string??
    if( args.empty() || !args[0].IsString() )
    {
        BRUH( "PlaySound(string) argument mismatch." );
        return;
    }

    int str = args[0].ToInteger();

    auto& trackList = TrackDatabase::GetInstance().m_trackList.m_tracks;
    if( str >= trackList.size() )
    {
        return;
    }
    RadioArgs radioArgs;
    radioArgs.CurrentTrack = &trackList[str];
    radioArgs.CurrentTrackIndex = str;
    radioArgs.UsePreviewMarker = true;
    TrackRadio::GetInstance().Play( radioArgs );
}

void DLCMenuController::SortTracks( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    int trackIndex = args[0].ToInteger();
    TrackListSort sortType = (TrackListSort)trackIndex;
    RefreshTrackList( sortType, TrackDatabase::GetInstance().m_currentFilter );
}

void DLCMenuController::FilterTracks( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    int trackIndex = args[0].ToInteger();
    TrackListFilter filterType = (TrackListFilter)trackIndex;
    RefreshTrackList( TrackDatabase::GetInstance().m_currentSort, filterType );
}

void DLCMenuController::RequestDetailsPanelUpdate( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    int trackIndex = args[0].ToInteger();

    RequestDetailsPanelUpdate_Internal( trackIndex );
}

void DLCMenuController::RequestDetailsPanelUpdate_Internal( int trackIndex )
{
    auto& trackList = TrackDatabase::GetInstance().m_trackList.m_tracks;
    if( trackList.size() == 0 )
    {
        return;
    }

    //for( int i = 0; i < trackList.size(); ++i )
    {
        auto& trackData = trackList[trackIndex];
        json uiTrackData;
        DumpTrackData( uiTrackData, trackData, trackIndex );
        ExecuteScript( "UpdateDetailsPanel(" + uiTrackData.dump() + "); " );
    }
}

void DLCMenuController::DumpTrackData( json& outJson, TrackData inTrackData, int inIndex )
{
    Path dlcTest = Path( inTrackData.m_albumArtPath );
    std::string songImage = dlcTest.GetLocalPathString();
    outJson["TrackName"] = inTrackData.m_trackName;
    outJson["ArtistName"] = inTrackData.m_artistName;
    outJson["AlbumName"] = inTrackData.m_albumName;
    outJson["Genre"] = inTrackData.m_genre;
    outJson["Year"] = inTrackData.m_year;
    outJson["Icon"] = inTrackData.m_icon;
    outJson["AlbumArt"] = songImage;
    outJson["TrackSource"] = inTrackData.m_trackSourcePath;
    outJson["NoteCount"] = inTrackData.m_noteData.size();
    outJson["TrackIndex"] = inIndex;
}

void DLCMenuController::RefreshTrackList( TrackListSort inSortType, TrackListFilter inFilterType )
{
    ExecuteScript( "ClearTrackList();" );

    auto& trackList = TrackDatabase::GetInstance().m_trackList.m_tracks;
    auto& sortedTracks = TrackDatabase::GetInstance().m_sortedIndices;
    TrackDatabase::GetInstance().SortTracks( inSortType, inFilterType );

    int cachedYear = -1;
    std::string cachedChar;
    std::string headerName;
    for( int i = 0; i < sortedTracks.size(); ++i )
    {
        auto& trackData = trackList[sortedTracks[i]];

        bool needsHeader = false;
        switch( inSortType )
        {
        case TrackListSort::Title:
            if( cachedChar.empty() || cachedChar[0] != trackData.m_trackName[0] )
            {
                cachedChar = trackData.m_trackName[0];
                headerName = cachedChar;
                needsHeader = true;
            }
            break;
        case TrackListSort::Artist:
            if( cachedChar.empty() || cachedChar[0] != trackData.m_artistName[0] )
            {
                cachedChar = trackData.m_artistName[0];
                headerName = cachedChar;
                needsHeader = true;
            }
            break;
        case TrackListSort::Year:
            if( cachedYear != trackData.m_year )
            {
                cachedYear = trackData.m_year;
                headerName = std::to_string( trackData.m_year );
                needsHeader = true;
            }
            break;
        case TrackListSort::None:
        default:
            break;
        }

        json uiTrackData;
        DumpTrackData( uiTrackData, trackData, sortedTracks[i] );
        if( needsHeader )
        {
            ExecuteScript( "AddCategory('" + headerName + "'); " );
        }
        ExecuteScript( "AddTrack(" + uiTrackData.dump() + "); " );
    }
    json filterData;
    json noneEntry;
    noneEntry["FilterName"] = TrackDatabase::GetInstance().GetFilterName( TrackListFilter::None );
    noneEntry["FilterID"] = 0;
    noneEntry["Count"] = TrackDatabase::GetInstance().m_trackList.m_tracks.size();
    filterData.push_back( noneEntry );
    for( int i = 0; i < TrackDatabase::GetInstance().m_filterMatches.size(); ++i )
    {
        if( TrackDatabase::GetInstance().m_filterMatches[i] > 0 )
        {
            json filterEntry;
            filterEntry["FilterName"] = TrackDatabase::GetInstance().GetFilterName( (TrackListFilter)i );
            filterEntry["FilterID"] = i;
            filterEntry["Count"] = TrackDatabase::GetInstance().m_filterMatches[i];
            filterData.push_back( filterEntry );
        }
    }
    ExecuteScript( "SetFilters(" + filterData.dump() + "); " );
    RequestDetailsPanelUpdate_Internal( 0 );
}

void DLCMenuController::OnUpdate( float dt )
{
    m_radioUtils->OnUpdate( dt );
}

#endif