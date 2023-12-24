#include <Components/MainMenuController.h>

#include <Events/SceneEvents.h>
#include "CoreGame/TrackList.h"
#include "Events/GameEvents.h"
#include "Global/TrackRadio.h"

MainMenuController::MainMenuController()
    : BasicUIView( "MainMenuController" )
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

MainMenuController::~MainMenuController()
{
    TrackRadio::GetInstance().Stop();
}

void MainMenuController::OnUILoad( ultralight::JSObject& GlobalWindow, ultralight::View* Caller )
{
    BasicUIView::OnUILoad( GlobalWindow, Caller );

    PlayNextRandomTrack();

    GlobalWindow["SkipTrack"] = BindJSCallback( &MainMenuController::SkipTrack );

}

void MainMenuController::PlayNextRandomTrack()
{
    auto& trackExample = TrackDatabase::GetInstance().m_trackList.m_tracks;

    int randomIndex = m_random( 0, trackExample.size() - 1 );
    auto& randomElement = trackExample[randomIndex];

    TrackRadio::GetInstance().Play( &randomElement );

    {
        Path dlcTest = Path( randomElement.m_albumArtPath );
        std::string songImage = dlcTest.GetLocalPathString();
        json trackData;
        trackData["TrackName"] = randomElement.m_trackName;
        trackData["ArtistName"] = randomElement.m_artistName;
        trackData["AlbumArt"] = songImage;
        trackData["TrackSource"] = randomElement.m_trackSourcePath;
        trackData["NoteCount"] = randomElement.m_noteData.size();
        ExecuteScript( "DisplayTrack(" + trackData.dump() + "); " );
    }
}

void MainMenuController::SkipTrack( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    PlayNextRandomTrack();
}
