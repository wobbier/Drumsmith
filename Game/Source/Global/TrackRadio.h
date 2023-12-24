#pragma once
#include "Singleton.h"
#include "Components/Audio/AudioSource.h"
#include "CoreGame/TrackList.h"
#include "Pointers.h"

class TrackRadio
{
    ME_SINGLETON_DEFINITION( TrackRadio );
public:
    TrackRadio() = default;

    void Play();
    void Stop();

    TrackData* m_currentTrack = nullptr;

    AudioSource m_currentlyPlaying;
    SharedPtr<AudioSource> m_currentlyPlayingPtr;
};