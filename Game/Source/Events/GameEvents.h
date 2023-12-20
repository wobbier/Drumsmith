#pragma once
#include <functional>

class AudioSource;

class LaunchPlayTrackEvent
    : public Event<LaunchPlayTrackEvent>
{
public:
    LaunchPlayTrackEvent()
        : Event()
    {
    }
    std::string TrackID;
    std::function<void( AudioSource* )> Callback;
};
