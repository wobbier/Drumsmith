#pragma once
#include "Events/Event.h"
#include <functional>
#include <string>

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

// The debug panel's scrubber (F8 in a song): jump the song to a point, 0..1 of its length.
class InGameSeekTrack
    : public Event<InGameSeekTrack>
{
public:
    InGameSeekTrack()
        : Event()
    {
    }
    float Fraction = 0.f;
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

