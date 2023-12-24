#pragma once
#include <Components/UI/BasicUIView.h>
#include "CoreGame/TrackList.h"
#include "Components/Audio/AudioSource.h"

class TrackListMenuController final
	: public BasicUIView
{
public:
	TrackListMenuController();

	void OnUILoad(ultralight::JSObject& GlobalWindow, ultralight::View* Caller) final;

    void SelectTrackToPlay( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
	void PlayTrackPreview( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );

	TrackDatabase m_database;

	SharedPtr<AudioSource> m_currentTrack;
};

ME_REGISTER_COMPONENT(TrackListMenuController);