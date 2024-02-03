#pragma once
#include <Components/UI/BasicUIView.h>
#include "CoreGame/TrackList.h"
#include "Components/Audio/AudioSource.h"

class TrackListMenuController final
	: public BasicUIView
{
public:
	TrackListMenuController();

#if USING( ME_UI )
	void OnUILoad(ultralight::JSObject& GlobalWindow, ultralight::View* Caller) final;

    void SelectTrackToPlay( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
    void PlayTrackPreview( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
    void RequestDetailsPanelUpdate( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
    void RequestDetailsPanelUpdate_Internal( int trackIndex );
#endif

	TrackDatabase m_database;

	SharedPtr<AudioSource> m_currentTrack;
};

ME_REGISTER_COMPONENT(TrackListMenuController);