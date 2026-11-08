#include "Components/MainMenuController.h"

#include <Cores/UI/RmlUiCore.h>
#include <Engine/Engine.h>
#include <Engine/Input.h>
#include "Config/GameSettings.h"
#include "CoreGame/TrackList.h"
#include "Global/TrackRadio.h"
#include "Midi/MidiDevice.h"
#include "UI/TrackRadioUtils.h"
#include "UI/UIModelUtils.h"
#include <algorithm>
#include <cmath>
#include <numeric>

namespace
{
    constexpr const char* kModel = "main_menu";
    // One sweep of the latency marker across its box.
    constexpr float kLatencySweepSeconds = 2.f;


    std::string FormatMilliseconds( float inMilliseconds )
    {
        const int rounded = static_cast<int>( std::lround( inMilliseconds ) );
        return ( rounded > 0 ? "+" : "" ) + std::to_string( rounded ) + " ms";
    }
}


MainMenuController::MainMenuController()
    : Component( "MainMenuController" )
    , m_radioUtils( std::make_unique<TrackRadioUtils>( kModel ) )
{
}


MainMenuController::~MainMenuController() = default;


void MainMenuController::PopulateModel()
{
    RmlUiCore* ui = GetEngine().RmlUi;
    if( !ui )
    {
        return;
    }
    const GameSettings& settings = GameSettings::GetInstance();
    ui->ModelEnsure( kModel );
    for( const char* event : { "open_settings", "close_settings", "save_settings", "select_device", "refresh_devices", "convert_dlc", "latency_toggle", "latency_apply", "technique", "stage_lighting" } )
    {
        ui->ModelRegisterEvent( kModel, event );
    }
    m_radioUtils->RegisterEvents( *ui );
    ui->ModelSetNumber( kModel, "settings_open", 0 );
    ui->ModelSetNumber( kModel, "radio_volume", std::round( settings.RadioVolume * 100.f ) );
    ui->ModelSetNumber( kModel, "audio_delay", settings.AudioLatency );
    ui->ModelSetNumber( kModel, "video_delay", settings.VideoLatency );
    ui->ModelSetNumber( kModel, "highway_speed", std::round( settings.HighwaySpeed * 100.f ) );
    ui->ModelSetNumber( kModel, "technique", settings.TechniqueStrictness );
    ui->ModelSetNumber( kModel, "stage_lighting", settings.StageLighting );
    ui->ModelSetString( kModel, "dlc_url", settings.DLCURL );
    ui->ModelSetString( kModel, "midi_device", settings.PreferredMidiDevice );
    ui->ModelSetString( kModel, "settings_status", "" );
    ui->ModelSetNumber( kModel, "latency_active", 0 );
    ui->ModelSetString( kModel, "latency_marker", "0%" );
    ui->ModelSetString( kModel, "latency_last", "--" );
    ui->ModelSetString( kModel, "latency_average", "--" );
    ui->ModelSetNumber( kModel, "latency_samples", 0 );
    RefreshDevices();
    m_modelReady = true;
}


void MainMenuController::RefreshDevices()
{
    RmlUiCore* ui = GetEngine().RmlUi;
    if( !ui )
    {
        return;
    }
    MidiDevice& midi = MidiDevice::GetInstance();
    if( midi.m_midiIn )
    {
        midi.RefreshDevices();
    }
    const auto& devices = midi.GetDevices();
    ui->ModelSetListCount( kModel, "devices", static_cast<int>( devices.size() ) );
    for( int i = 0; i < static_cast<int>( devices.size() ); ++i )
    {
        ui->ModelSetItemString( kModel, "devices", i, "name", devices[i].Name );
    }
}


void MainMenuController::ApplySettings( bool inSave )
{
    RmlUiCore* ui = GetEngine().RmlUi;
    if( !ui )
    {
        return;
    }
    GameSettings& settings = GameSettings::GetInstance();
    const float volume = static_cast<float>( std::clamp( ui->ModelGetNumber( kModel, "radio_volume" ), 0.0, 100.0 ) / 100.0 );
    if( volume != settings.RadioVolume )
    {
        settings.RadioVolume = volume;
        TrackRadio::GetInstance().SetVolume( volume );
        ui->ModelSetString( kModel, "settings_status", "" );
    }
    settings.AudioLatency = static_cast<int>( std::clamp( ui->ModelGetNumber( kModel, "audio_delay" ), 0.0, 100.0 ) );
    settings.VideoLatency = static_cast<int>( std::clamp( ui->ModelGetNumber( kModel, "video_delay" ), 0.0, 100.0 ) );
    settings.HighwaySpeed = static_cast<float>( std::clamp( ui->ModelGetNumber( kModel, "highway_speed" ), 50.0, 200.0 ) / 100.0 );
    settings.PreferredMidiDevice = ui->ModelGetString( kModel, "midi_device" );
    if( inSave )
    {
        std::string url = ui->ModelGetString( kModel, "dlc_url" );
        const size_t first = url.find_first_not_of( " \t\r\n" );
        url = first == std::string::npos ? std::string() : url.substr( first, url.find_last_not_of( " \t\r\n" ) - first + 1 );
        while( !url.empty() && url.back() == '/' )
        {
            url.pop_back();
        }
        settings.DLCURL = url;
        ui->ModelSetString( kModel, "dlc_url", url );
        settings.Save();
        ui->ModelSetString( kModel, "settings_status", "Settings saved" );
    }
}


void MainMenuController::OpenSettings( bool inOpen )
{
    RmlUiCore* ui = GetEngine().RmlUi;
    if( !ui )
    {
        return;
    }
    if( inOpen )
    {
        RefreshDevices();
        ui->ModelSetString( kModel, "settings_status", "" );
    }
    else
    {
        StopLatencyTest();
        ApplySettings( true );
    }
    ui->ModelSetNumber( kModel, "settings_open", inOpen );
}


void MainMenuController::UpdateLatencyTest( float dt )
{
    RmlUiCore* ui = GetEngine().RmlUi;
    if( !ui || !m_latencyTestActive )
    {
        return;
    }
    m_latencySweep = std::fmod( m_latencySweep + dt, kLatencySweepSeconds );
    ui->ModelSetString( kModel, "latency_marker", std::to_string( static_cast<int>( std::lround( m_latencySweep / kLatencySweepSeconds * 1000.f ) ) / 10.f ) + "%" );

    // Any key counts, except the ones the UI itself reacts to (focus, activation, closing).
    Input& input = GetEngine().GetInput();
    for( uint32_t key = static_cast<uint32_t>( KeyCode::A ); key < static_cast<uint32_t>( SDL_NUM_SCANCODES ); ++key )
    {
        const KeyCode code = static_cast<KeyCode>( key );
        if( code == KeyCode::Escape || code == KeyCode::Tab || code == KeyCode::Enter || code == KeyCode::Space )
        {
            continue;
        }
        if( input.WasKeyPressed( code ) )
        {
            RecordLatencySample();
            break;
        }
    }
}


void MainMenuController::RecordLatencySample()
{
    RmlUiCore* ui = GetEngine().RmlUi;
    if( !ui )
    {
        return;
    }
    // Positive: the key came after the marker crossed the centre line.
    const float offsetMs = ( m_latencySweep - kLatencySweepSeconds * 0.5f ) * 1000.f;
    m_latencySamples[m_latencyNextSample] = offsetMs;
    m_latencyNextSample = ( m_latencyNextSample + 1 ) % static_cast<int>( m_latencySamples.size() );
    m_latencySampleCount = std::min( m_latencySampleCount + 1, static_cast<int>( m_latencySamples.size() ) );
    const float average = std::accumulate( m_latencySamples.begin(), m_latencySamples.begin() + m_latencySampleCount, 0.f ) / static_cast<float>( m_latencySampleCount );
    ui->ModelSetString( kModel, "latency_last", FormatMilliseconds( offsetMs ) );
    ui->ModelSetString( kModel, "latency_average", FormatMilliseconds( average ) );
    ui->ModelSetNumber( kModel, "latency_samples", m_latencySampleCount );
}


void MainMenuController::StopLatencyTest()
{
    m_latencyTestActive = false;
    m_latencySweep = 0.f;
    if( RmlUiCore* ui = GetEngine().RmlUi )
    {
        ui->ModelSetNumber( kModel, "latency_active", 0 );
        ui->ModelSetString( kModel, "latency_marker", "0%" );
    }
}


void MainMenuController::Update( float dt )
{
    m_radioUtils->OnUpdate( dt );
    if( !m_modelReady )
    {
        PopulateModel();
    }
    RmlUiCore* ui = GetEngine().RmlUi;
    if( !ui )
    {
        return;
    }
    const bool settingsOpen = ui->ModelGetNumber( kModel, "settings_open" ) != 0;
    if( settingsOpen && GetEngine().GetInput().WasKeyPressed( KeyCode::Escape ) )
    {
        OpenSettings( false );
    }
    for( std::string event; !( event = ui->ModelPollEvent( kModel ) ).empty(); )
    {
        const json args = UIModel::LastEventArgs( *ui, kModel );
        if( m_radioUtils->HandleEvent( event, args ) )
        {
            continue;
        }
        if( event == "open_settings" )
        {
            OpenSettings( true );
        }
        else if( event == "close_settings" )
        {
            OpenSettings( false );
        }
        else if( event == "save_settings" )
        {
            ApplySettings( true );
        }
        else if( event == "technique" )
        {
            const int strictness = std::clamp( static_cast<int>( UIModel::ArgNumber( args, 0, 1.0 ) ), 0, 2 );
            GameSettings::GetInstance().TechniqueStrictness = strictness;
            ui->ModelSetNumber( kModel, "technique", strictness );
            ui->ModelSetString( kModel, "settings_status", "" );
        }
        else if( event == "stage_lighting" )
        {
            const int lighting = std::clamp( static_cast<int>( UIModel::ArgNumber( args, 0, 2.0 ) ), 0, 2 );
            GameSettings::GetInstance().StageLighting = lighting;
            ui->ModelSetNumber( kModel, "stage_lighting", lighting );
            ui->ModelSetString( kModel, "settings_status", "" );
        }
        else if( event == "refresh_devices" )
        {
            RefreshDevices();
        }
        else if( event == "select_device" )
        {
            ui->ModelSetString( kModel, "midi_device", UIModel::ArgString( args, 0 ) );
            ui->ModelSetString( kModel, "settings_status", "" );
        }
        else if( event == "convert_dlc" )
        {
            TrackDatabase::GetInstance().ExportMidiTrackMetaData();
            ui->ModelSetString( kModel, "settings_status", "Custom DLC metadata exported" );
        }
        else if( event == "latency_toggle" )
        {
            if( m_latencyTestActive )
            {
                StopLatencyTest();
            }
            else
            {
                m_latencyTestActive = true;
                m_latencySweep = 0.f;
                ui->ModelSetNumber( kModel, "latency_active", 1 );
            }
        }
        else if( event == "latency_apply" && m_latencySampleCount > 0 )
        {
            const float average = std::accumulate( m_latencySamples.begin(), m_latencySamples.begin() + m_latencySampleCount, 0.f ) / static_cast<float>( m_latencySampleCount );
            ui->ModelSetNumber( kModel, "video_delay", std::clamp( static_cast<double>( std::lround( average ) ), 0.0, 100.0 ) );
            ui->ModelSetString( kModel, "settings_status", "Visual delay set from the latency test; save to keep it" );
        }
    }
    if( settingsOpen )
    {
        ApplySettings( false );
        UpdateLatencyTest( dt );
    }
}
