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
    GlobalWindow["ViewTrackStats"] = BindJSCallback( &TrackListMenuController::ViewTrackStats );
    GlobalWindow["RequestDetailsPanelUpdate"] = BindJSCallback( &TrackListMenuController::RequestDetailsPanelUpdate );
    ExecuteScript( "ClearTrackList();" );

    auto& trackList = TrackDatabase::GetInstance().m_trackList.m_tracks;
    for( int i = 0; i < trackList.size(); ++i )
    {
        auto& trackData = trackList[i];
        Path dlcTest = Path( trackData.m_albumArtPath );
        std::string songImage = dlcTest.GetLocalPathString();
        json uiTrackData;
        uiTrackData["TrackName"] = trackData.m_trackName;
        uiTrackData["ArtistName"] = trackData.m_artistName;
        uiTrackData["AlbumName"] = trackData.m_albumName;
        uiTrackData["AlbumArt"] = songImage;
        uiTrackData["Genre"] = trackData.m_genre;
        uiTrackData["Year"] = trackData.m_year;
        uiTrackData["Icon"] = trackData.m_icon;
        uiTrackData["TrackSource"] = trackData.m_trackSourcePath;
        uiTrackData["NoteCount"] = trackData.m_noteData.size();
        uiTrackData["TrackIndex"] = i;
        ExecuteScript( "AddTrack(" + uiTrackData.dump() + "); " );
    }
    RequestDetailsPanelUpdate_Internal( 0 );
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
    if (str >= trackList.size())
    {
        return;
    }
    TrackRadio::GetInstance().Play( &trackList[str] );
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
        Path dlcTest = Path( trackData.m_albumArtPath );
        std::string songImage = dlcTest.GetLocalPathString();
        json uiTrackData;
        uiTrackData["TrackName"] = trackData.m_trackName;
        uiTrackData["ArtistName"] = trackData.m_artistName;
        uiTrackData["AlbumName"] = trackData.m_albumName;
        uiTrackData["Genre"] = trackData.m_genre;
        uiTrackData["Year"] = trackData.m_year;
        uiTrackData["Icon"] = trackData.m_icon;
        uiTrackData["AlbumArt"] = songImage;
        uiTrackData["TrackSource"] = trackData.m_trackSourcePath;
        uiTrackData["NoteCount"] = trackData.m_noteData.size();
        uiTrackData["TrackIndex"] = trackIndex;
        ExecuteScript( "UpdateDetailsPanel(" + uiTrackData.dump() + "); " );
    }
}

#endif