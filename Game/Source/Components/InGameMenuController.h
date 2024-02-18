#pragma once
#include <Components/UI/BasicUIView.h>
#include "CoreGame/TrackList.h"
#include "Components/Audio/AudioSource.h"
#include "Math/Random.h"

class InGameMenuController final
	: public BasicUIView
{
public:
    InGameMenuController();
    virtual ~InGameMenuController();

#if USING( ME_UI )
	void OnUILoad(ultralight::JSObject& GlobalWindow, ultralight::View* Caller) final;
    void Internal_Pause( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
    void Internal_Resume( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
#endif

	SharedPtr<AudioSource> m_currentTrack;
	Random64 m_random;
};

ME_REGISTER_COMPONENT( InGameMenuController );