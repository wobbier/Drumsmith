#pragma once
#include "Singleton.h"
#include "Components/Audio/AudioSource.h"
#include "CoreGame/TrackList.h"
#include "Pointers.h"
#include "CoreGame/AudioPack.h"

class TrackData;

struct RadioArgs
{
    TrackData* CurrentTrack = nullptr;
    int CurrentTrackIndex = 0;
    bool UsePreviewMarker = false;
};

enum class RadioState
{
    None = 0,
    Loading,
    Seeking,
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

    void Update( float dt );
    bool CanPlayNextTrack() const;

    TrackData* m_currentTrack = nullptr;

    AudioSource m_currentlyPlaying;
    SharedPtr<AudioSource> m_currentlyPlayingPtr;
    std::vector<SharedPtr<AudioSource>> m_currentStems;
    RadioState m_radioState = RadioState::None;
    RadioArgs m_radioArgs;
    AudioPack m_audioPack;
private:

    bool PlayStem( const char* inFileName, bool inUsePreviewMarker );
    int m_currentTrackIndex = -1;
    float m_delayTimer = 0.f;
    float m_previewPercent = 0.f;
};