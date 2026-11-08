#include "Components/InGameMenuController.h"
#include "Config/GameSettings.h"
#include "Events/GameEvents.h"
#include <Cores/UI/RmlUiCore.h>
#include <Engine/Engine.h>
#include <Engine/Input.h>
#include <Events/SceneEvents.h>
#include <RmlUi/Core.h>
#include <algorithm>
#include <cstdlib>

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
        for( const char* event : { "resume", "options", "back", "exit", "save", "audio_delay", "video_delay" } )
            ui->ModelRegisterEvent( "in_game", event );
        ui->ModelSetString( "in_game", "status", "" );
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
    if( GetEngine().GetInput().WasKeyPressed( KeyCode::Escape ) )
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
        else if( event == "exit" )
        {
            LoadSceneEvent load;
            load.Level = "Assets/TrackList.lvl";
            load.Queue();
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
}
