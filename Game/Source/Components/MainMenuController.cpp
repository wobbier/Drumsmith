#include "Components/MainMenuController.h"

#include <Cores/UI/RmlUiCore.h>
#include <Engine/Engine.h>
#include <Engine/Input.h>
#include "Config/GameSettings.h"
#include "CoreGame/Calibration.h"
#include "CoreGame/TrackList.h"
#include "Events/GameEvents.h"
#include <Events/SceneEvents.h>
#include "Global/TrackRadio.h"
#include "Midi/MidiDevice.h"
#include "Editor/PadBindings.h"
#include "UI/TrackRadioUtils.h"
#include "UI/UIModelUtils.h"
#include "Web/HttpDownload.h"
#include "JSON.h"
#include <filesystem>
#include <fstream>
#include <iterator>
#include <algorithm>
#include <cmath>
#include <numeric>

namespace
{
    constexpr const char* kModel = "main_menu";


    // The kit page's rows, as a kit is laid out rather than in PadId order.
    struct KitRow
    {
        PadId Pad;
        const char* Name;
    };
    constexpr KitRow kKitRows[] = {
        { PadId::Bass, "Kick" }, { PadId::Snare, "Snare" }, { PadId::ClosedHiHat, "Hi-hat (closed)" }, { PadId::OpenHiHat, "Hi-hat (open)" },
        { PadId::HiHatPedal, "Hi-hat pedal" }, { PadId::HighTom, "High tom" }, { PadId::MidTom, "Mid tom" }, { PadId::FloorTom, "Floor tom" },
        { PadId::Crash1, "Crash" }, { PadId::Crash2, "Second crash" }, { PadId::Ride, "Ride" }, { PadId::Splash, "Splash" }, { PadId::China, "China" },
    };


    const char* KitName( PadId inPad )
    {
        for( const KitRow& row : kKitRows )
        {
            if( row.Pad == inPad )
            {
                return row.Name;
            }
        }
        return "";
    }


    const char* StrokeName( Articulation inStroke )
    {
        switch( inStroke )
        {
        case Articulation::Rim: return "rim";
        case Articulation::CrossStick: return "cross-stick";
        case Articulation::Bell: return "bell";
        default: return "";
        }
    }
}


MainMenuController::MainMenuController()
    : Component( "MainMenuController" )
    , m_radioUtils( std::make_unique<TrackRadioUtils>( kModel ) )
{
}


MainMenuController::~MainMenuController()
{
    // A check in flight finishes its download first (Web::DownloadFile has no cancel).
    if( m_serverCheck && m_serverCheck->Thread.joinable() )
    {
        m_serverCheck->Thread.join();
    }
}


void MainMenuController::RefreshServers()
{
    RmlUiCore* ui = GetEngine().RmlUi;
    if( !ui )
    {
        return;
    }
    const auto& servers = GameSettings::GetInstance().DLCServers;
    ui->ModelSetListCount( kModel, "servers", static_cast<int>( servers.size() ) );
    for( int i = 0; i < static_cast<int>( servers.size() ); ++i )
    {
        const auto result = std::find_if( m_serverResults.begin(), m_serverResults.end(), [&]( const ServerResult& r ) { return r.Url == servers[i]; } );
        ui->ModelSetItemNumber( kModel, "servers", i, "index", i );
        ui->ModelSetItemString( kModel, "servers", i, "url", servers[i] );
        ui->ModelSetItemNumber( kModel, "servers", i, "state", result != m_serverResults.end() ? result->State : 0 );
        ui->ModelSetItemString( kModel, "servers", i, "status", result != m_serverResults.end() ? result->Message : std::string() );
    }
}


void MainMenuController::QueueServerCheck( const std::string& inServer )
{
    if( inServer.empty() || std::find( m_serverChecks.begin(), m_serverChecks.end(), inServer ) != m_serverChecks.end() || ( m_serverCheck && m_serverCheck->Url == inServer ) )
    {
        return;
    }
    m_serverChecks.push_back( inServer );
    m_serverResults.erase( std::remove_if( m_serverResults.begin(), m_serverResults.end(), [&]( const ServerResult& r ) { return r.Url == inServer; } ), m_serverResults.end() );
    m_serverResults.push_back( { inServer, 1, "Checking..." } );
    RefreshServers();
}


void MainMenuController::PumpServerChecks()
{
    if( m_serverCheck )
    {
        if( !m_serverCheck->Finished )
        {
            return;
        }
        m_serverCheck->Thread.join();
        for( ServerResult& result : m_serverResults )
        {
            if( result.Url == m_serverCheck->Url )
            {
                result.State = m_serverCheck->Works ? 2 : 3;
                result.Message = m_serverCheck->Message;
            }
        }
        m_serverCheck.reset();
        RefreshServers();
    }
    if( m_serverChecks.empty() )
    {
        return;
    }
    m_serverCheck = std::make_unique<ServerCheck>();
    m_serverCheck->Url = m_serverChecks.front();
    m_serverChecks.pop_front();
    ServerCheck* check = m_serverCheck.get();
    check->Thread = std::thread( [check]()
    {
        // A valid server answers <server>/dlc_index.json with the catalogue: a JSON array of
        // songs, each with its folder and files (Assets/DLC/DLCParser.py writes it).
        const Path target( "Assets/DLC/.catalogue/_verify.download" );
        const bool fetched = Web::DownloadFile( check->Url + "/dlc_index.json", target );
        std::string text;
        if( fetched )
        {
            std::ifstream file( target.FullPath, std::ios::binary );
            text.assign( std::istreambuf_iterator<char>( file ), std::istreambuf_iterator<char>() );
        }
        std::error_code error;
        std::filesystem::remove( target.FullPath, error );
        const json index = text.empty() ? json() : json::parse( text, nullptr, false );
        if( !fetched || text.empty() )
        {
            check->Message = "Couldn't reach it";
        }
        else if( !index.is_array() )
        {
            check->Message = "Answers, but has no Drumsmith catalogue";
        }
        else
        {
            int songs = 0;
            for( const json& entry : index )
            {
                songs += entry.is_object() && entry.contains( "FolderPath" ) && entry.contains( "FilesInFolder" ) && entry["FilesInFolder"].is_array() ? 1 : 0;
            }
            check->Works = songs > 0 || index.empty();
            check->Message = check->Works ? "Works: " + std::to_string( songs ) + ( songs == 1 ? " song" : " songs" ) : "Answers, but has no Drumsmith catalogue";
        }
        check->Finished = true;
    } );
}


void MainMenuController::PopulateModel()
{
    RmlUiCore* ui = GetEngine().RmlUi;
    if( !ui )
    {
        return;
    }
    const GameSettings& settings = GameSettings::GetInstance();
    ui->ModelEnsure( kModel );
    for( const char* event : { "open_settings", "close_settings", "save_settings", "select_device", "refresh_devices", "convert_dlc", "calibrate", "bind_key", "bind_midi", "kit_clear", "kit_standard", "settings_tab", "server_add", "server_remove", "server_test", "technique", "stage_lighting", "venue", "venue_camera", "venue_style", "lyrics", "metronome" } )
    {
        ui->ModelRegisterEvent( kModel, event );
    }
    m_radioUtils->RegisterEvents( *ui );
    ui->ModelSetNumber( kModel, "settings_open", 0 );
    ui->ModelSetNumber( kModel, "settings_tab", 0 );
    ui->ModelSetNumber( kModel, "radio_volume", std::round( settings.RadioVolume * 100.f ) );
    ui->ModelSetNumber( kModel, "audio_delay", settings.AudioLatency );
    ui->ModelSetNumber( kModel, "video_delay", settings.VideoLatency );
    ui->ModelSetNumber( kModel, "highway_speed", std::round( settings.HighwaySpeed * 100.f ) );
    ui->ModelSetNumber( kModel, "technique", settings.TechniqueStrictness );
    ui->ModelSetNumber( kModel, "stage_lighting", settings.StageLighting );
    ui->ModelSetNumber( kModel, "venue", settings.Venue );
    ui->ModelSetNumber( kModel, "venue_camera", settings.VenueCamera );
    ui->ModelSetNumber( kModel, "venue_style", settings.VenueStyle );
    ui->ModelSetNumber( kModel, "lyrics", settings.Lyrics );
    ui->ModelSetNumber( kModel, "metronome", settings.Metronome );
    // The text box is for a server to add; the ones already set are the rows above it.
    ui->ModelSetString( kModel, "dlc_url", "" );
    ui->ModelSetString( kModel, "midi_device", settings.PreferredMidiDevice );
    ui->ModelSetString( kModel, "settings_status", "" );
    ui->ModelSetString( kModel, "kit_last", "--" );
    ui->ModelSetString( kModel, "midi_open", "" );
    RefreshDevices();
    RefreshPads();
    RefreshServers();
    m_modelReady = true;
}


void MainMenuController::RefreshPads()
{
    RmlUiCore* ui = GetEngine().RmlUi;
    if( !ui )
    {
        return;
    }
    const PadMappingStorage& storage = PadMappingStorage::GetInstance();
    Input& input = GetEngine().GetInput();
    const int count = static_cast<int>( std::size( kKitRows ) );
    ui->ModelSetListCount( kModel, "pads", count );
    for( int row = 0; row < count; ++row )
    {
        const PadDefinition& pad = storage.mappedPads[kKitRows[row].Pad];
        const bool armed = m_bindPad == kKitRows[row].Pad;
        std::string key = "Press a key...";
        if( !armed || m_bindKind != 1 )
        {
            key = pad.keyboardBinding > 0 ? std::string( "Key: " ) + input.GetKeyCodeName( static_cast<KeyCode>( pad.keyboardBinding ) ) : std::string( "Key: none" );
        }
        std::string midi = "Hit the pad...";
        if( !armed || m_bindKind != 2 )
        {
            midi = pad.midiBinding > 0 ? "MIDI: " + std::to_string( pad.midiBinding ) : std::string( "MIDI: none" );
        }
        std::string extra;
        for( const MidiNoteBinding& note : pad.extraMidi )
        {
            const char* stroke = StrokeName( note.articulation );
            extra += ( extra.empty() ? "also " : ", " ) + std::to_string( note.note ) + ( *stroke ? std::string( " " ) + stroke : std::string() );
        }
        ui->ModelSetItemNumber( kModel, "pads", row, "id", kKitRows[row].Pad );
        ui->ModelSetItemString( kModel, "pads", row, "name", kKitRows[row].Name );
        ui->ModelSetItemString( kModel, "pads", row, "key", key );
        ui->ModelSetItemString( kModel, "pads", row, "midi", midi );
        ui->ModelSetItemString( kModel, "pads", row, "extra", extra );
        ui->ModelSetItemNumber( kModel, "pads", row, "binding", armed ? m_bindKind : 0 );
    }
}


void MainMenuController::StopBinding()
{
    if( m_bindKind != 0 )
    {
        m_bindKind = 0;
        m_bindPad = -1;
        RefreshPads();
    }
}


void MainMenuController::UpdateKitBinding( float dt )
{
    RmlUiCore* ui = GetEngine().RmlUi;
    if( !ui )
    {
        return;
    }
    m_bindIgnore = std::max( 0.f, m_bindIgnore - dt );
    PadMappingStorage& storage = PadMappingStorage::GetInstance();

    // Every hit while the page is open shows what it is bound to; the first one after a MIDI
    // button was armed becomes that pad's note.
    std::vector<PadMappingStorage::Resolved> resolved;
    for( const MidiMessageNew& message : MidiDevice::GetInstance().PumpMessages() )
    {
        if( !message.IsOnType() )
        {
            continue;
        }
        const int note = message.m_data1;
        if( m_bindKind == 2 && m_bindPad >= 0 && m_bindPad < PadId::COUNT )
        {
            PadDefinition& pad = storage.mappedPads[m_bindPad];
            pad.midiBinding = note;
            // The note is the pad's plain stroke now, not also one of its other strokes.
            pad.extraMidi.erase( std::remove_if( pad.extraMidi.begin(), pad.extraMidi.end(), [note]( const MidiNoteBinding& b ) { return b.note == note; } ), pad.extraMidi.end() );
            m_kitDirty = true;
            ui->ModelSetString( kModel, "settings_status", std::string( KitName( static_cast<PadId>( m_bindPad ) ) ) + " is MIDI note " + std::to_string( note ) + "; save to keep it" );
            StopBinding();
        }
        storage.Resolve( note, resolved );
        std::string meaning;
        for( const auto& hit : resolved )
        {
            const char* stroke = StrokeName( hit.articulation );
            meaning += ( meaning.empty() ? "" : ", " ) + std::string( KitName( hit.pad ) ) + ( *stroke ? std::string( " (" ) + stroke + ")" : std::string() );
        }
        ui->ModelSetString( kModel, "kit_last", "note " + std::to_string( note ) + ", velocity " + std::to_string( message.m_data2 ) + ": " + ( meaning.empty() ? std::string( "not bound" ) : meaning ) );
    }

    if( m_bindKind == 1 && m_bindPad >= 0 && m_bindPad < PadId::COUNT )
    {
        Input& input = GetEngine().GetInput();
        for( uint32_t key = static_cast<uint32_t>( KeyCode::A ); key < static_cast<uint32_t>( SDL_NUM_SCANCODES ); ++key )
        {
            const KeyCode code = static_cast<KeyCode>( key );
            if( code == KeyCode::Escape || !input.WasKeyPressed( code ) )
            {
                continue;
            }
            storage.mappedPads[m_bindPad].keyboardBinding = static_cast<int32_t>( key );
            m_kitDirty = true;
            if( code == KeyCode::Space || code == KeyCode::Enter )
            {
                m_bindIgnore = 0.3f;
            }
            ui->ModelSetString( kModel, "settings_status", std::string( KitName( static_cast<PadId>( m_bindPad ) ) ) + " is the " + input.GetKeyCodeName( code ) + " key; save to keep it" );
            StopBinding();
            break;
        }
    }
}


void MainMenuController::RefreshDevices()
{
    RmlUiCore* ui = GetEngine().RmlUi;
    if( !ui )
    {
        return;
    }
    MidiDevice& midi = MidiDevice::GetInstance();
    midi.RefreshDevices();
    m_midiGeneration = midi.GetGeneration();
    ui->ModelSetString( kModel, "midi_open", midi.GetOpenDeviceName() );
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
    settings.AudioLatency = static_cast<int>( std::clamp( ui->ModelGetNumber( kModel, "audio_delay" ), 0.0, static_cast<double>( GameSettings::kMaxLatencyMs ) ) );
    settings.VideoLatency = static_cast<int>( std::clamp( ui->ModelGetNumber( kModel, "video_delay" ), 0.0, static_cast<double>( GameSettings::kMaxLatencyMs ) ) );
    settings.HighwaySpeed = static_cast<float>( std::clamp( ui->ModelGetNumber( kModel, "highway_speed" ), 50.0, 200.0 ) / 100.0 );
    settings.PreferredMidiDevice = ui->ModelGetString( kModel, "midi_device" );
    if( inSave )
    {
        // A server typed but not added yet is added: saving shouldn't lose it.
        const std::string typed = GameSettings::CleanServer( ui->ModelGetString( kModel, "dlc_url" ) );
        if( settings.AddDLCServer( typed ) )
        {
            QueueServerCheck( typed );
        }
        ui->ModelSetString( kModel, "dlc_url", "" );
        RefreshServers();
        settings.Save();
        if( m_kitDirty )
        {
            PadMappingStorage::GetInstance().Save();
            m_kitDirty = false;
        }
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
        // Open the player's device so the kit page hears it (a no-op when it already is).
        MidiDevice::GetInstance().OpenMidiDevice( GameSettings::GetInstance().PreferredMidiDevice );
        RefreshDevices();
        RefreshPads();
        ui->ModelSetString( kModel, "settings_status", "" );
    }
    else
    {
        StopBinding();
        ApplySettings( true );
    }
    ui->ModelSetNumber( kModel, "settings_open", inOpen );
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
        // Escape first cancels a pad being bound, then closes the panel.
        if( m_bindKind != 0 )
        {
            StopBinding();
        }
        else
        {
            OpenSettings( false );
        }
    }
    // A device was plugged in or unplugged (MidiDevice::Poll): list them again.
    if( settingsOpen && MidiDevice::GetInstance().GetGeneration() != m_midiGeneration )
    {
        RefreshDevices();
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
        else if( event == "venue" )
        {
            const int venue = std::clamp( static_cast<int>( UIModel::ArgNumber( args, 0, 2.0 ) ), 0, 2 );
            GameSettings::GetInstance().Venue = venue;
            ui->ModelSetNumber( kModel, "venue", venue );
            ui->ModelSetString( kModel, "settings_status", "" );
        }
        else if( event == "venue_style" )
        {
            const int style = std::clamp( static_cast<int>( UIModel::ArgNumber( args, 0, 0.0 ) ), 0, 3 );
            GameSettings::GetInstance().VenueStyle = style;
            ui->ModelSetNumber( kModel, "venue_style", style );
            ui->ModelSetString( kModel, "settings_status", "" );
        }
        else if( event == "metronome" )
        {
            const bool metronome = UIModel::ArgNumber( args, 0, 0.0 ) != 0.0;
            GameSettings::GetInstance().Metronome = metronome;
            ui->ModelSetNumber( kModel, "metronome", metronome );
            ui->ModelSetString( kModel, "settings_status", "" );
        }
        else if( event == "lyrics" )
        {
            const int lyrics = std::clamp( static_cast<int>( UIModel::ArgNumber( args, 0, 0.0 ) ), 0, 3 );
            GameSettings::GetInstance().Lyrics = lyrics;
            ui->ModelSetNumber( kModel, "lyrics", lyrics );
            ui->ModelSetString( kModel, "settings_status", "" );
        }
        else if( event == "venue_camera" )
        {
            const int camera = std::clamp( static_cast<int>( UIModel::ArgNumber( args, 0, 0.0 ) ), 0, 1 );
            GameSettings::GetInstance().VenueCamera = camera;
            ui->ModelSetNumber( kModel, "venue_camera", camera );
            ui->ModelSetString( kModel, "settings_status", "" );
        }
        else if( event == "refresh_devices" )
        {
            RefreshDevices();
        }
        else if( event == "select_device" )
        {
            const std::string device = UIModel::ArgString( args, 0 );
            ui->ModelSetString( kModel, "midi_device", device );
            ui->ModelSetString( kModel, "settings_status", "" );
            // Opened at once, so the kit rows below can hear it.
            MidiDevice::GetInstance().OpenMidiDevice( device );
            ui->ModelSetString( kModel, "midi_open", MidiDevice::GetInstance().GetOpenDeviceName() );
        }
        else if( ( event == "bind_key" || event == "bind_midi" ) && m_bindIgnore <= 0.f )
        {
            const int pad = static_cast<int>( UIModel::ArgNumber( args, 0, -1.0 ) );
            const int kind = event == "bind_key" ? 1 : 2;
            if( pad < 0 || pad >= PadId::COUNT || ( pad == m_bindPad && kind == m_bindKind ) )
            {
                StopBinding();
            }
            else
            {
                m_bindPad = pad;
                m_bindKind = kind;
                // Hits from before the button was pressed aren't the answer.
                MidiDevice::GetInstance().PumpMessages();
                RefreshPads();
            }
        }
        else if( event == "kit_clear" )
        {
            const int pad = static_cast<int>( UIModel::ArgNumber( args, 0, -1.0 ) );
            if( pad >= 0 && pad < PadId::COUNT )
            {
                PadDefinition& definition = PadMappingStorage::GetInstance().mappedPads[pad];
                definition.keyboardBinding = 0;
                definition.midiBinding = 0;
                definition.extraMidi.clear();
                m_kitDirty = true;
                StopBinding();
                RefreshPads();
                ui->ModelSetString( kModel, "settings_status", "" );
            }
        }
        else if( event == "settings_tab" )
        {
            StopBinding();
            ui->ModelSetNumber( kModel, "settings_tab", std::clamp( static_cast<int>( UIModel::ArgNumber( args, 0, 0.0 ) ), 0, 4 ) );
        }
        else if( event == "server_add" )
        {
            const std::string typed = GameSettings::CleanServer( ui->ModelGetString( kModel, "dlc_url" ) );
            GameSettings& settings = GameSettings::GetInstance();
            if( typed.empty() )
            {
                ui->ModelSetString( kModel, "settings_status", "Type a server's address first" );
            }
            else if( settings.AddDLCServer( typed ) )
            {
                settings.Save();
                ui->ModelSetString( kModel, "dlc_url", "" );
                ui->ModelSetString( kModel, "settings_status", "Added " + typed );
                QueueServerCheck( typed );
            }
            else
            {
                ui->ModelSetString( kModel, "settings_status", typed + " is already in the list" );
            }
            RefreshServers();
        }
        else if( event == "server_remove" || event == "server_test" )
        {
            GameSettings& settings = GameSettings::GetInstance();
            const int index = static_cast<int>( UIModel::ArgNumber( args, 0, -1.0 ) );
            if( index >= 0 && index < static_cast<int>( settings.DLCServers.size() ) )
            {
                const std::string server = settings.DLCServers[index];
                if( event == "server_test" )
                {
                    QueueServerCheck( server );
                }
                else if( settings.RemoveDLCServer( server ) )
                {
                    settings.Save();
                    ui->ModelSetString( kModel, "settings_status", "Removed " + server );
                    RefreshServers();
                }
            }
        }
        else if( event == "kit_standard" )
        {
            PadMappingStorage::GetInstance().ApplyStandardKitMidi();
            m_kitDirty = true;
            StopBinding();
            RefreshPads();
            ui->ModelSetString( kModel, "settings_status", "Standard e-kit notes set; save to keep them" );
        }
        else if( event == "calibrate" )
        {
            // The calibration is a session on the highway (CoreGame/Calibration.h). What the
            // panel holds is saved first: the session's results are written over those.
            if( !Calibration::GetInstance().Begin() )
            {
                ui->ModelSetString( kModel, "settings_status", "Couldn't start the calibration: its click track wasn't written" );
                continue;
            }
            StopBinding();
            ApplySettings( true );
            TrackRadio::GetInstance().Stop();
            LoadSceneEvent load;
            load.Level = "Assets/Example.lvl";
            load.Callback = []()
            {
                LaunchPlayTrackEvent play;
                play.TrackID = Calibration::kTrackId;
                play.TrackIndex = -1;
                play.Fire();
            };
            load.Queue();
            return;
        }
        else if( event == "convert_dlc" )
        {
            TrackDatabase::GetInstance().ExportMidiTrackMetaData();
            ui->ModelSetString( kModel, "settings_status", "Custom DLC metadata exported" );
        }
    }
    PumpServerChecks();
    if( settingsOpen )
    {
        ApplySettings( false );
        UpdateKitBinding( dt );
    }
}
