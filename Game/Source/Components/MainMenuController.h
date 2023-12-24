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

	void OnUILoad(ultralight::JSObject& GlobalWindow, ultralight::View* Caller) final;

	SharedPtr<AudioSource> m_currentTrack;

	void PlayNextRandomTrack();

    void SkipTrack( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );

	Random64 m_random;
};

ME_REGISTER_COMPONENT( MainMenuController );