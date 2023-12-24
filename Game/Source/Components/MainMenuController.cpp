#include <Components/MainMenuController.h>

#include <Events/SceneEvents.h>
#include "CoreGame/TrackList.h"
#include "Events/GameEvents.h"
#include "Global/TrackRadio.h"
#include <random>

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

    //GlobalWindow["SelectTrackToPlay"] = BindJSCallback( &ExampleMenuController::SelectTrackToPlay );

}

void MainMenuController::PlayNextRandomTrack()
{
    auto& trackExample = TrackDatabase::GetInstance().m_trackList.m_tracks;

    std::random_device rd;
    std::mt19937 gen( rd() );
    std::uniform_int_distribution<> distrib( 0, trackExample.size() - 1 );

    int randomIndex = distrib( gen );
    auto& randomElement = trackExample[randomIndex];


    TrackRadio::GetInstance().m_currentTrack = &randomElement;
    TrackRadio::GetInstance().Play();

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
