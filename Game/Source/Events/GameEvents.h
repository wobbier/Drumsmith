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

class InGamePauseCurrentTrack
    : public Event<InGamePauseCurrentTrack>
{
public:
    InGamePauseCurrentTrack()
        : Event()
    {
    }
};

class InGameResumeCurrentTrack
    : public Event<InGameResumeCurrentTrack>
{
public:
    InGameResumeCurrentTrack()
        : Event()
    {
    }
};


class EditTrackEvent
    : public Event<EditTrackEvent>
{
public:
    EditTrackEvent()
        : Event()
    {
    }
    std::string FileName;
};

