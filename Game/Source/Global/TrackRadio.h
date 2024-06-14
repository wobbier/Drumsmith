#pragma once
#include "Singleton.h"
#include "Components/Audio/AudioSource.h"
#include "CoreGame/TrackList.h"
#include "Pointers.h"

class TrackData;

struct RadioArgs
{

};

class TrackRadio
{
    ME_SINGLETON_DEFINITION( TrackRadio );
public:
    TrackRadio() = default;

    void Play( TrackData* inTrackData, bool inUsePreviewMarker = true );
    bool IsPlaying() const;
    void Stop();
    void SetVolume( float inVolume );

    TrackData* m_currentTrack = nullptr;

    AudioSource m_currentlyPlaying;
    SharedPtr<AudioSource> m_currentlyPlayingPtr;
    std::vector<SharedPtr<AudioSource>> m_currentStems;
private:

    bool PlayStem( const char* inFileName, bool inUsePreviewMarker );

};