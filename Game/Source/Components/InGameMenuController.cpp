#include <Components/InGameMenuController.h>

#include <Events/SceneEvents.h>
#include "CoreGame/TrackList.h"
#include "Events/GameEvents.h"
#include "Global/TrackRadio.h"
#include "Config/GameSettings.h"

InGameMenuController::InGameMenuController()
    : BasicUIView( "InGameMenuController" )
{
    FilePath = Path( "Assets/UI/InGameMenu.html" );
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

InGameMenuController::~InGameMenuController()
{
    TrackRadio::GetInstance().Stop();
}

#if USING( ME_UI )

void InGameMenuController::OnUILoad( ultralight::JSObject& GlobalWindow, ultralight::View* Caller )
{
    BasicUIView::OnUILoad( GlobalWindow, Caller );

    //PlayNextRandomTrack();
    //ExecuteScript( "setRadioInitialValue(" + std::to_string( GameSettings::GetInstance().RadioVolume * 100 ) + ")" );

    GlobalWindow["Internal_Pause"] = BindJSCallback( &InGameMenuController::Internal_Pause );
    GlobalWindow["Internal_Resume"] = BindJSCallback( &InGameMenuController::Internal_Resume );

}

void InGameMenuController::Internal_Pause( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    InGamePauseCurrentTrack evt;
    evt.Fire();
}

void InGameMenuController::Internal_Resume( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    InGameResumeCurrentTrack evt;
    evt.Fire();
}

#endif
