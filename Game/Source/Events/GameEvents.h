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
    int TrackIndex = 0;
    std::function<void( AudioSource* )> Callback;
};
