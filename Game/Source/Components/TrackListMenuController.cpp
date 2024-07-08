#include <Components/TrackListMenuController.h>

#include <Events/SceneEvents.h>
#include "CoreGame/TrackList.h"
#include "Events/GameEvents.h"
#include "Global/TrackRadio.h"

TrackListMenuController::TrackListMenuController()
    : BasicUIView( "TrackListMenuController" )
{
    FilePath = Path( "Assets/UI/SongList.html" );
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

#if USING( ME_UI )

void TrackListMenuController::OnUILoad( ultralight::JSObject& GlobalWindow, ultralight::View* Caller )
{
    BasicUIView::OnUILoad( GlobalWindow, Caller );

    GlobalWindow["SelectTrackToPlay"] = BindJSCallback( &TrackListMenuController::SelectTrackToPlay );
    GlobalWindow["PlayTrackPreview"] = BindJSCallback( &TrackListMenuController::PlayTrackPreview );
    GlobalWindow["FilterSortTracks"] = BindJSCallback( &TrackListMenuController::FilterSortTracks );
    GlobalWindow["ViewTrackStats"] = BindJSCallback( &TrackListMenuController::ViewTrackStats );
    GlobalWindow["RequestDetailsPanelUpdate"] = BindJSCallback( &TrackListMenuController::RequestDetailsPanelUpdate );
    
    RefreshTrackList( TrackListSort::Artist );
}

void TrackListMenuController::SelectTrackToPlay( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    ultralight::String path = args[0].ToString();
    int index = args[1].ToInteger();

    TrackRadio::GetInstance().Stop();
    SharedPtr<LoadSceneEvent> loadSceneEvent = MakeShared<LoadSceneEvent>();
    loadSceneEvent->Level = "Assets/Example.lvl";
    EventManager::GetInstance().QueueEvent( loadSceneEvent );

    loadSceneEvent->Callback = [path, index]() {
        LaunchPlayTrackEvent evt;
        evt.TrackID = std::string( path.utf8().data() );
        evt.TrackIndex = index;
        evt.Fire();
    };
}

void TrackListMenuController::ViewTrackStats( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
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

void TrackListMenuController::PlayTrackPreview( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
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
    radioArgs.UsePreviewMarker = true;
    TrackRadio::GetInstance().Play( radioArgs );
}

void TrackListMenuController::FilterSortTracks( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    int trackIndex = args[0].ToInteger();
    TrackListSort sortType = (TrackListSort)trackIndex;
    RefreshTrackList( sortType );
}

void TrackListMenuController::RequestDetailsPanelUpdate( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    int trackIndex = args[0].ToInteger();

    RequestDetailsPanelUpdate_Internal( trackIndex );
}

void TrackListMenuController::RequestDetailsPanelUpdate_Internal( int trackIndex )
{
    auto& trackList = TrackDatabase::GetInstance().m_trackList.m_tracks;
    //for( int i = 0; i < trackList.size(); ++i )
    {
        auto& trackData = trackList[trackIndex];
        json uiTrackData;
        DumpTrackData( uiTrackData, trackData, trackIndex );
        ExecuteScript( "UpdateDetailsPanel(" + uiTrackData.dump() + "); " );
    }
}

void TrackListMenuController::DumpTrackData( json& outJson, TrackData inTrackData, int inIndex )
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

void TrackListMenuController::RefreshTrackList( TrackListSort inSortType )
{
    ExecuteScript( "ClearTrackList();" );

    auto& trackList = TrackDatabase::GetInstance().m_trackList.m_tracks;
    auto& sortedTracks = TrackDatabase::GetInstance().m_sortedIndices;
    TrackDatabase::GetInstance().SortTracks( inSortType );

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
    RequestDetailsPanelUpdate_Internal( 0 );
}

void TrackListMenuController::OnUpdate()
{
    TrackRadio::GetInstance().Update();
}

#endif