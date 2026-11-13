#include "Components/InGameMenuController.h"
#include "Config/GameSettings.h"
#include "Events/GameEvents.h"
#include "UI/UIModelUtils.h"
#include "Core/CommandLine.h"
#include <Cores/UI/RmlUiCore.h>
#include <Engine/Engine.h>
#include <Engine/Input.h>
#include <Engine/PlayerSettings.h>
#include <Events/SceneEvents.h>
#include <RmlUi/Core.h>
#include <algorithm>
#include <cstdlib>
#include <cmath>

namespace
{
    // The debug panel's autoplay modes, by debug_autoplay (NoteHighwayCore::GatherHits).
    constexpr const char* kAutoplayLabels[3] = { "OFF", "PERFECT", "SLOPPY" };


    // The menu key. In the editor plain Escape belongs to Havana (it frees the mouse and hands
    // input back to the editor while the song keeps playing), so the menu takes Shift+Escape there.
    bool MenuKeyPressed( Input& inInput )
    {
        if( !inInput.WasKeyPressed( KeyCode::Escape ) ) return false;
#if USING( ME_EDITOR )
        return inInput.IsKeyDown( KeyCode::LeftShift ) || inInput.IsKeyDown( KeyCode::RightShift );
#else
        return true;
#endif
    }


#if USING( ME_EDITOR )
    constexpr const char* kPauseHint = "Shift+Esc \xE2\x80\x94 Pause";
#else
    constexpr const char* kPauseHint = "Esc \xE2\x80\x94 Pause";
#endif
}

InGameMenuController::InGameMenuController()
    : Component( "InGameMenuController" )
{
}


void InGameMenuController::SetPaused( bool inPaused )
{
    if( m_paused == inPaused ) return;
    m_paused = inPaused;
    m_options = false;
    if( m_paused )
    {
        InGamePauseCurrentTrack().Fire();
        m_focusTarget = "resume";
    }
    else
    {
        InGameResumeCurrentTrack().Fire();
        m_focusTarget = nullptr;
    }
}


void InGameMenuController::Update( float inDeltaTime )
{
    RmlUiCore* ui = GetEngine().RmlUi;
    if( !ui ) return;
    auto& settings = GameSettings::GetInstance();
    if( !m_modelReady )
    {
        ui->ModelEnsure( "in_game" );
        for( const char* event : { "resume", "options", "back", "exit", "save", "audio_delay", "video_delay", "highway_speed", "retry", "debug_nofail", "debug_autoplay", "debug_plain", "debug_seek", "master_volume" } )
            ui->ModelRegisterEvent( "in_game", event );
        ui->ModelSetString( "in_game", "status", "" );
        ui->ModelSetString( "in_game", "pause_hint", kPauseHint );
        // The debug panel (F8): no fail, and a scrubber over the song.
        ui->ModelSetNumber( "in_game", "debug", CommandLine::Has( "--debug-panel" ) ? 1 : 0 );
        ui->ModelSetNumber( "in_game", "debug_nofail", CommandLine::Has( "--no-fail" ) ? 1 : 0 );
        // Autoplay: off, perfect, sloppy (--highway-autoplay, --highway-autoplay-sloppy), and
        // plain strokes (--highway-autoplay-plain).
        const int autoplay = CommandLine::Has( "--highway-autoplay" ) ? ( CommandLine::Has( "--highway-autoplay-sloppy" ) ? 2 : 1 ) : 0;
        ui->ModelSetNumber( "in_game", "debug_autoplay", autoplay );
        ui->ModelSetString( "in_game", "debug_autoplay_label", kAutoplayLabels[autoplay] );
        ui->ModelSetNumber( "in_game", "debug_plain", CommandLine::Has( "--highway-autoplay-plain" ) ? 1 : 0 );
        // The karaoke line (NoteHighwayCore::UpdateLyrics), registered up front so setting it
        // later doesn't reload the document.
        ui->ModelSetNumber( "in_game", "lyrics_shown", 0 );
        ui->ModelSetString( "in_game", "lyric_sung", "" );
        ui->ModelSetString( "in_game", "lyric_rest", "" );
        ui->ModelSetString( "in_game", "lyric_next", "" );
        m_modelReady = true;
    }

    // Focus after the preceding frame has shown the requested panel.
    if( m_focusTarget )
    {
        for( const auto& loaded : ui->GetLoadedDocuments() )
        {
            auto* element = loaded.Document->GetElementById( m_focusTarget );
            if( element && element->IsVisible() )
            {
                element->Focus();
                m_focusTarget = nullptr;
                break;
            }
        }
    }
    // On the results screen Escape leaves for the library instead of pausing.
    const bool finished = ui->ModelGetNumber( "in_game", "finished" ) != 0;
    const bool menuKey = MenuKeyPressed( GetEngine().GetInput() );
    if( finished && menuKey )
    {
        LoadSceneEvent load;
        load.Level = "Assets/TrackList.lvl";
        load.Queue();
    }
    else if( GetEngine().GetInput().WasKeyPressed( KeyCode::F8 ) )
    {
        ui->ModelSetNumber( "in_game", "debug", ui->ModelGetNumber( "in_game", "debug" ) == 0 );
    }
    else if( menuKey )
    {
        if( m_options )
        {
            settings.Save();
            m_options = false;
            m_focusTarget = "options";
        }
        else SetPaused( !m_paused );
    }
    for( std::string event; !( event = ui->ModelPollEvent( "in_game" ) ).empty(); )
    {
        if( event == "resume" ) SetPaused( false );
        else if( event == "options" )
        {
            m_options = true;
            m_focusTarget = "options-back";
        }
        else if( event == "back" )
        {
            settings.Save();
            m_options = false;
            m_focusTarget = "options";
        }
        else if( event == "save" )
        {
            settings.Save();
            ui->ModelSetString( "in_game", "status", "Settings saved" );
        }
        else if( event == "retry" )
        {
            const int trackIndex = static_cast<int>( ui->ModelGetNumber( "in_game", "track_index" ) );
            LoadSceneEvent load;
            load.Level = "Assets/Example.lvl";
            load.Callback = [trackIndex]()
            {
                LaunchPlayTrackEvent play;
                play.TrackIndex = trackIndex;
                play.Fire();
            };
            load.Queue();
        }
        else if( event == "exit" )
        {
            LoadSceneEvent load;
            load.Level = "Assets/TrackList.lvl";
            load.Queue();
        }
        else if( event == "debug_nofail" )
        {
            ui->ModelSetNumber( "in_game", "debug_nofail", ui->ModelGetNumber( "in_game", "debug_nofail" ) == 0 );
        }
        else if( event == "debug_autoplay" )
        {
            const int autoplay = ( static_cast<int>( ui->ModelGetNumber( "in_game", "debug_autoplay" ) ) + 1 ) % 3;
            ui->ModelSetNumber( "in_game", "debug_autoplay", autoplay );
            ui->ModelSetString( "in_game", "debug_autoplay_label", kAutoplayLabels[autoplay] );
        }
        else if( event == "debug_plain" )
        {
            ui->ModelSetNumber( "in_game", "debug_plain", ui->ModelGetNumber( "in_game", "debug_plain" ) == 0 );
        }
        else if( event == "debug_seek" )
        {
            // The slider also reports the value the HUD moves it to; only a real drag seeks.
            const double value = UIModel::ArgNumber( UIModel::LastEventArgs( *ui, "in_game" ), 0 );
            if( value >= 0.0 && std::fabs( value - ui->ModelGetNumber( "in_game", "song_progress" ) ) > 2.0 )
            {
                InGameSeekTrack seek;
                seek.Fraction = static_cast<float>( std::clamp( value, 0.0, 1000.0 ) / 1000.0 );
                seek.Fire();
            }
        }
        else if( event == "master_volume" )
        {
            // The engine's player settings own it: applied to the master bus, saved once it settles.
            const double percent = UIModel::ArgNumber( UIModel::LastEventArgs( *ui, "in_game" ), 0 );
            if( percent >= 0.0 )
                PlayerSettings::Get().SetValue( "Audio.Master", std::clamp( percent, 0.0, 100.0 ) / 100.0 );
        }
        else if( event == "highway_speed" )
        {
            const json args = json::parse( ui->ModelLastEventArgs( "in_game" ), nullptr, false );
            if( args.is_array() && !args.empty() )
            {
                const double percent = args[0].is_number() ? args[0].get<double>() : std::atof( args[0].is_string() ? args[0].get<std::string>().c_str() : "100" );
                settings.HighwaySpeed = static_cast<float>( std::clamp( percent, 50.0, 200.0 ) / 100.0 );
            }
        }
        else if( event == "audio_delay" || event == "video_delay" )
        {
            const json args = json::parse( ui->ModelLastEventArgs( "in_game" ), nullptr, false );
            if( !args.is_array() || args.empty() ) continue;
            const int value = std::clamp( args[0].is_number() ? args[0].get<int>() :
                std::atoi( args[0].is_string() ? args[0].get<std::string>().c_str() : "0" ), 0, 100 );
            if( event == "audio_delay" ) settings.AudioLatency = value;
            else settings.VideoLatency = value;
            ui->ModelSetString( "in_game", "status", "" );
        }
    }
    ui->ModelSetNumber( "in_game", "paused", m_paused );
    ui->ModelSetNumber( "in_game", "options", m_options );
    ui->ModelSetNumber( "in_game", "audio_delay", settings.AudioLatency );
    ui->ModelSetNumber( "in_game", "video_delay", settings.VideoLatency );
    const json master = PlayerSettings::Get().GetValue( "Audio.Master" );
    ui->ModelSetNumber( "in_game", "master_volume", std::round( ( master.is_number() ? master.get<double>() : 1.0 ) * 100.0 ) );
    ui->ModelSetNumber( "in_game", "highway_speed", std::round( settings.HighwaySpeed * 100.f ) );
}
