#pragma once
#include <Components/UI/BasicUIView.h>
#include "CoreGame/TrackList.h"
#include "Components/Audio/AudioSource.h"

class MainMenuController final
	: public BasicUIView
{
public:
    MainMenuController();
    virtual ~MainMenuController();

	void OnUILoad(ultralight::JSObject& GlobalWindow, ultralight::View* Caller) final;

	SharedPtr<AudioSource> m_currentTrack;

	void PlayNextRandomTrack();
};

ME_REGISTER_COMPONENT( MainMenuController );