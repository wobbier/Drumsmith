#pragma once


class LaunchPlayTrackEvent
    : public Event<LaunchPlayTrackEvent>
{
public:
    LaunchPlayTrackEvent()
        : Event()
    {
    }
    std::string TrackID;
};
