#pragma once
#include <Components/UI/BasicUIView.h>
#include "CoreGame/TrackList.h"
#include "Components/Audio/AudioSource.h"

class TrackStatsMenuController final
	: public BasicUIView
{
public:
    TrackStatsMenuController();

#if USING( ME_UI )
	void OnUILoad(ultralight::JSObject& GlobalWindow, ultralight::View* Caller) final;
#endif
};

ME_REGISTER_COMPONENT( TrackStatsMenuController );