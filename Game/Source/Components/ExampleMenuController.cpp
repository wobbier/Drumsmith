#include <Components/ExampleMenuController.h>

#include <Events/SceneEvents.h>
#include "CoreGame/TrackList.h"

ExampleMenuController::ExampleMenuController()
    : BasicUIView( "ExampleMenuController" )
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

void ExampleMenuController::OnUILoad( ultralight::JSObject& GlobalWindow, ultralight::View* Caller )
{
    BasicUIView::OnUILoad( GlobalWindow, Caller );

    GlobalWindow["LoadScene"] = BindJSCallback( &ExampleMenuController::LoadScene );
    ExecuteScript( "ClearTrackList();" );

    for( auto it : TrackDatabase::GetInstance().m_trackList.m_tracks )
    {
        Path dlcTest = Path( it.m_albumArtPath );
        std::string songImage = dlcTest.GetLocalPathString();
        json trackData;
        trackData["TrackName"] = it.m_trackName;
        trackData["ArtistName"] = it.m_artistName;
        trackData["AlbumArt"] = songImage;
        trackData["TrackSource"] = it.m_trackSourcePath;
        ExecuteScript( "AddTrack(" + trackData.dump() + "); " );
    }
}

void ExampleMenuController::LoadScene( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    LoadSceneEvent evt;
    ultralight::String path = args[0].ToString();
    evt.Level = std::string( path.utf8().data() );
    evt.Fire();
}