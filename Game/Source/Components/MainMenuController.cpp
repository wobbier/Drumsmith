#include <Components/MainMenuController.h>

#include <Events/SceneEvents.h>
#include "CoreGame/TrackList.h"
#include "Events/GameEvents.h"
#include "Global/TrackRadio.h"
#include "Config/GameSettings.h"
#include "Web/HttpDownload.h"

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


void MainMenuController::OnJSReady( ultralight::JSObject& GlobalWindow, ultralight::View* Caller )
{
    BasicUIView::OnJSReady( GlobalWindow, Caller );

    GlobalWindow["GetDLCURL_Internal"] = BindJSCallbackWithRetval( &MainMenuController::GetDLCURL );
    GlobalWindow["GetMIDIDevices_Internal"] = BindJSCallbackWithRetval( &MainMenuController::GetMIDIDevices_Internal );
}


void MainMenuController::OnUILoad( ultralight::JSObject& GlobalWindow, ultralight::View* Caller )
{
    BasicUIView::OnUILoad( GlobalWindow, Caller );

    PlayNextRandomTrack();
    ExecuteScript( "setRadioInitialValue(" + std::to_string( GameSettings::GetInstance().RadioVolume * 100 ) + ")" );

    GlobalWindow["SkipTrack"] = BindJSCallback( &MainMenuController::SkipTrack );
    GlobalWindow["SetRadioVolume"] = BindJSCallback( &MainMenuController::SetRadioVolume );
    GlobalWindow["SetDLCURL_Internal"] = BindJSCallback( &MainMenuController::SetDLCURL );
    GlobalWindow["SaveSettings"] = BindJSCallback( &MainMenuController::SaveSettings );
    GlobalWindow["ConvertCustomDLC"] = BindJSCallback( &MainMenuController::ConvertCustomDLC );
    GlobalWindow["SetPreferredMidiDevice_Internal"] = BindJSCallback( &MainMenuController::SetPreferredMidiDevice_Internal );
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
    TrackRadio::GetInstance().SetVolume( volume );
    GameSettings::GetInstance().RadioVolume = volume;
}


ultralight::JSValue MainMenuController::GetDLCURL( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    return ultralight::JSValue( GameSettings::GetInstance().DLCURL.c_str() );
}


ultralight::JSValue MainMenuController::GetMIDIDevices_Internal( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    auto& devices = MidiDevice::GetInstance().GetDevices();
    json deviceList;
    for( auto& device : devices )
    {
        json deviceEntry;
        deviceEntry["Port"] = device.Port;
        deviceEntry["Name"] = device.Name;
        deviceList.push_back( deviceEntry );
    }
    auto ogDum = deviceList.dump();
    const char* dumped = ogDum.c_str();
    return ultralight::JSValue( dumped );
}


void MainMenuController::SetDLCURL( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    ultralight::String url = args[0].ToString();
    std::string urlConv( url.utf8().data() );

    if( Web::DownloadFile( urlConv + "/dlc_index.json", Path("Assets/DLC/dlc_index.json")) )
    {
        GameSettings::GetInstance().DLCURL = urlConv;
    }
}


void MainMenuController::SaveSettings( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    GameSettings::GetInstance().Save();
}


void MainMenuController::ConvertCustomDLC( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    TrackDatabase::GetInstance().ExportMidiTrackMetaData();
}


void MainMenuController::SetPreferredMidiDevice_Internal( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    ultralight::String arg = args[0].ToString();
    std::string argConv( arg.utf8().data() );

    GameSettings::GetInstance().PreferredMidiDevice = argConv;
}


#endif

void MainMenuController::PlayNextRandomTrack()
{
    TrackData* randomElement = TrackRadio::GetInstance().m_currentTrack;

    if( !TrackRadio::GetInstance().IsPlaying() )
    {
        auto& trackExample = TrackDatabase::GetInstance().m_trackList.m_tracks;
        if( trackExample.empty() )
        {
            return;
        }
        int randomIndex = m_random( 0, trackExample.size() - 1 );
        randomElement = &trackExample[randomIndex];

        RadioArgs radioArgs;
        radioArgs.CurrentTrack = randomElement;
        radioArgs.UsePreviewMarker = false;
        TrackRadio::GetInstance().Play( radioArgs );
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
        ExecuteScript( "window.DisplayTrack(" + trackData.dump() + "); " );
    }
}

void MainMenuController::OnUpdate( float dt )
{
    TrackRadio::GetInstance().Update(dt);
    if( TrackRadio::GetInstance().CanPlayNextTrack() )
    {
        PlayNextRandomTrack();
    }
}