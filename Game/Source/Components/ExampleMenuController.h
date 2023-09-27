#pragma once
#include <Components/UI/BasicUIView.h>
#include "CoreGame/TrackList.h"
#include "Components/Audio/AudioSource.h"

class ExampleMenuController final
	: public BasicUIView
{
public:
	ExampleMenuController();

	void OnUILoad(ultralight::JSObject& GlobalWindow, ultralight::View* Caller) final;

	void LoadScene(const ultralight::JSObject& thisObject, const ultralight::JSArgs& args);
	void SelectTrackToPlay(const ultralight::JSObject& thisObject, const ultralight::JSArgs& args);

	TrackDatabase m_database;

	SharedPtr<AudioSource> m_currentTrack;
};

ME_REGISTER_COMPONENT(ExampleMenuController);