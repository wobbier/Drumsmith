#pragma once
#include "Components\UI\BasicUIView.h"
#include "Math\Random.h"
#include "UI\JSHelpers.h"

class TrackRadioUtils
{
public:
    TrackRadioUtils() = delete;
    TrackRadioUtils(BasicUIView& inOwningView);

    void OnUILoad( ultralight::JSObject& GlobalWindow, ultralight::View* Caller );
    void OnUpdate( float dt );
    void PlayNextRandomTrack();
    void SkipTrack( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args );
private:
    BasicUIView& m_owner;
    Random64 m_random;
};