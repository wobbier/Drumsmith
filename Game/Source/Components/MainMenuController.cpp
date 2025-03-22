#include <Components/MainMenuController.h>

#include "Config/GameSettings.h"
#include <Events/SceneEvents.h>
#include "Events/GameEvents.h"
#include "Global/TrackRadio.h"
#include "UI/TrackRadioUtils.h"
#include "Web/HttpDownload.h"

MainMenuController::MainMenuController()
    : BasicUIView( "MainMenuController" )
    , m_radioUtils( new TrackRadioUtils( *this ) )
{
    FilePath = Path( "Assets/UI/SongList.html" );
}

MainMenuController::~MainMenuController()
{
    delete m_radioUtils;
}

#if USING( ME_UI )


void MainMenuController::OnJSReady( ultralight::JSObject& GlobalWindow, ultralight::View* Caller )
{
    BasicUIView::OnJSReady( GlobalWindow, Caller );

    GlobalWindow["GetRadioVolume_Internal"] = BindJSCallbackWithRetval( &MainMenuController::GetRadioVolume_Internal );
    GlobalWindow["GetDLCURL_Internal"] = BindJSCallbackWithRetval( &MainMenuController::GetDLCURL );
    GlobalWindow["GetMIDIDevices_Internal"] = BindJSCallbackWithRetval( &MainMenuController::GetMIDIDevices_Internal );

    m_radioUtils->PlayNextRandomTrack();
}


void MainMenuController::OnUILoad( ultralight::JSObject& GlobalWindow, ultralight::View* Caller )
{
    BasicUIView::OnUILoad( GlobalWindow, Caller );

    m_radioUtils->OnUILoad( GlobalWindow, Caller );
    //ExecuteScript( "setRadioInitialValue(" + std::to_string( GameSettings::GetInstance().RadioVolume * 100 ) + ")" );

    GlobalWindow["SetRadioVolume"] = BindJSCallback( &MainMenuController::SetRadioVolume );
    GlobalWindow["SetDLCURL_Internal"] = BindJSCallback( &MainMenuController::SetDLCURL );
    GlobalWindow["SaveSettings"] = BindJSCallback( &MainMenuController::SaveSettings );
    GlobalWindow["ConvertCustomDLC"] = BindJSCallback( &MainMenuController::ConvertCustomDLC );
    GlobalWindow["SetPreferredMidiDevice_Internal"] = BindJSCallback( &MainMenuController::SetPreferredMidiDevice_Internal );
    GlobalWindow["SetAudioLatency_Internal"] = BindJSCallback( &MainMenuController::SetAudioLatency_Internal );
    GlobalWindow["SetVideoLatency_Internal"] = BindJSCallback( &MainMenuController::SetVideoLatency_Internal );
}

void MainMenuController::SetRadioVolume( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    float volume = (float)args[0].ToNumber();
    volume = volume / 100.f;
    TrackRadio::GetInstance().SetVolume( volume );
    GameSettings::GetInstance().RadioVolume = volume;
}


ultralight::JSValue MainMenuController::GetRadioVolume_Internal( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    return ultralight::JSValue( GameSettings::GetInstance().RadioVolume );
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

    if( Web::DownloadFile( urlConv + "/dlc_index.json", Path( "Assets/DLC/dlc_index.json" ) ) )
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


void MainMenuController::SetAudioLatency_Internal( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    int arg = args[0].ToInteger();
    GameSettings::GetInstance().AudioLatency = arg;
}


void MainMenuController::SetVideoLatency_Internal( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    int arg = args[0].ToInteger();
    GameSettings::GetInstance().VideoLatency = arg;
}


#endif


void MainMenuController::OnUpdate( float dt )
{
    m_radioUtils->OnUpdate( dt );
}