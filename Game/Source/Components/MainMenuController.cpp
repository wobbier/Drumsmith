#include <Components/MainMenuController.h>

#include <Events/SceneEvents.h>
#include "CoreGame/TrackList.h"
#include "Events/GameEvents.h"
#include "Global/TrackRadio.h"
#include "Config/GameSettings.h"

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

#if USING( ME_UI )

void MainMenuController::OnUILoad( ultralight::JSObject& GlobalWindow, ultralight::View* Caller )
{
    BasicUIView::OnUILoad( GlobalWindow, Caller );

    PlayNextRandomTrack();
    ExecuteScript( "setRadioInitialValue(" + std::to_string( GameSettings::GetInstance().RadioVolume * 100 ) + ")" );

    GlobalWindow["SkipTrack"] = BindJSCallback( &MainMenuController::SkipTrack );
    GlobalWindow["SetRadioVolume"] = BindJSCallback( &MainMenuController::SetRadioVolume );
    GlobalWindow["SaveSettings"] = BindJSCallback( &MainMenuController::SaveSettings );
    GlobalWindow["ConvertCustomDLC"] = BindJSCallback( &MainMenuController::ConvertCustomDLC );

}

void MainMenuController::SkipTrack( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    TrackRadio::GetInstance().Stop();
    PlayNextRandomTrack();
}

void MainMenuController::SetRadioVolume( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    float volume = (float)args[0].ToNumber();
    volume = volume / 100.f;
    TrackRadio::GetInstance().SetVolume(volume);
    GameSettings::GetInstance().RadioVolume = volume;
}

void MainMenuController::SaveSettings( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    GameSettings::GetInstance().Save();
}

void MainMenuController::ConvertCustomDLC( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    TrackDatabase::GetInstance().ExportMidiTrackMetaData();
}

#endif

void MainMenuController::PlayNextRandomTrack()
{
    TrackData* randomElement = TrackRadio::GetInstance().m_currentTrack;
    if( !TrackRadio::GetInstance().m_currentlyPlayingPtr || !TrackRadio::GetInstance().m_currentlyPlayingPtr->IsPlaying() )
    {
        auto& trackExample = TrackDatabase::GetInstance().m_trackList.m_tracks;

        int randomIndex = m_random( 0, trackExample.size() - 1 );
        randomElement = &trackExample[randomIndex];
        TrackRadio::GetInstance().Play( randomElement, false );
    }

    if( randomElement )
    {
        Path dlcTest = Path( randomElement->m_albumArtPath );
        std::string songImage = dlcTest.GetLocalPathString();
        json trackData;
        trackData["TrackName"] = randomElement->m_trackName;
        trackData["ArtistName"] = randomElement->m_artistName;
        trackData["AlbumArt"] = songImage;
        trackData["TrackSource"] = randomElement->m_trackSourcePath;
        trackData["NoteCount"] = randomElement->m_noteData.size();
        ExecuteScript( "DisplayTrack(" + trackData.dump() + "); " );
    }
}
