#pragma once
#include <Components/UI/BasicUIView.h>
#include "CoreGame/TrackList.h"
#include "Components/Audio/AudioSource.h"
#include "Math/Random.h"

class MainMenuController final
	: public BasicUIView
{
public:
    MainMenuController();
    virtual ~MainMenuController();

#if USING( ME_UI )
    void OnJSReady( ultralight::JSObject& GlobalWindow, ultralight::View* Caller ) final;
    void OnUILoad( ultralight::JSObject& GlobalWindow, ultralight::View* Caller ) final;
    void SkipTrack( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
    void SetRadioVolume( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
    ultralight::JSValue GetDLCURL( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
    void SetDLCURL( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
    void SaveSettings( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
    void ConvertCustomDLC( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
#endif

	void PlayNextRandomTrack();

    void OnUpdate( float dt ) override;

    SharedPtr<AudioSource> m_currentTrack;
	Random64 m_random;
};

ME_REGISTER_COMPONENT( MainMenuController );