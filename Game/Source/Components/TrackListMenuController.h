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
    void ViewTrackStats( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
    void PlayTrackPreview( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
    void SortTracks( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
    void FilterTracks( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
    void EditTrack( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
    void RequestDetailsPanelUpdate( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
    void RequestDetailsPanelUpdate_Internal( int trackIndex );

    void DumpTrackData( json& outJson, TrackData inTrackData, int inIndex );

    void RefreshTrackList( TrackListSort inSortType, TrackListFilter inFilterType );
    void OnUpdate() override;
#endif

	SharedPtr<AudioSource> m_currentTrack;
};

ME_REGISTER_COMPONENT(TrackListMenuController);