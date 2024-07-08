#pragma once
#include "Singleton.h"
#include "Components/Audio/AudioSource.h"
#include "CoreGame/TrackList.h"
#include "Pointers.h"

class TrackData;

struct RadioArgs
{
    TrackData* CurrentTrack = nullptr;
    bool UsePreviewMarker = false;
};

enum class RadioState
{
    None = 0,
    Loading,
    Playing,
    Paused
};

class TrackRadio
{
    ME_SINGLETON_DEFINITION( TrackRadio );
public:
    TrackRadio() = default;

    void Play( RadioArgs inTrackArgs );
    bool IsPlaying() const;
    void Stop();
    void SetVolume( float inVolume );

    void TryPlayNextTrack();
    void Update();
    bool CanPlayNextTrack() const;

    TrackData* m_currentTrack = nullptr;

    AudioSource m_currentlyPlaying;
    SharedPtr<AudioSource> m_currentlyPlayingPtr;
    std::vector<SharedPtr<AudioSource>> m_currentStems;
    RadioState m_radioState = RadioState::None;
    RadioArgs m_radioArgs;
private:

    bool PlayStem( const char* inFileName, bool inUsePreviewMarker );

};