#pragma once
#include <Components/UI/BasicUIView.h>

class TrackRadioUtils;

class MainMenuController final
	: public BasicUIView
{
public:
    MainMenuController();
    virtual ~MainMenuController();

#if USING( ME_UI )
    void OnJSReady( ultralight::JSObject& GlobalWindow, ultralight::View* Caller ) final;
    void OnUILoad( ultralight::JSObject& GlobalWindow, ultralight::View* Caller ) final;
    void SetRadioVolume( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
    ultralight::JSValue GetRadioVolume_Internal( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
    ultralight::JSValue GetDLCURL( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
    ultralight::JSValue GetMIDIDevices_Internal( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
    void SetDLCURL( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
    void SaveSettings( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
    void ConvertCustomDLC( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
    void SetPreferredMidiDevice_Internal( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
    void SetAudioLatency_Internal( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
    void SetVideoLatency_Internal( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
#endif

    void OnUpdate( float dt ) override;

    // should be a ref?
    TrackRadioUtils* m_radioUtils = nullptr;
};

ME_REGISTER_COMPONENT( MainMenuController );