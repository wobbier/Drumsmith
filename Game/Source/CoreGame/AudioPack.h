#pragma once

#include "TrackList.h"
#include "Components/Audio/AudioSource.h"

#if USING( ME_FMOD )
namespace FMOD { class ChannelGroup; }
#endif

class AudioPack
{
public:
    AudioPack() = default;
    AudioPack( TrackData& inTrackData );
    ~AudioPack();

    AudioPack( const AudioPack& ) = delete;
    AudioPack& operator=( const AudioPack& ) = delete;
    AudioPack( AudioPack&& other ) noexcept;
    AudioPack& operator=( AudioPack&& other ) noexcept;

    void Play();
    void Pause();
    void Resume();
    void Stop();

    void SetVolume( float inVolumePercent );
    void SetDrumVolume( float inVolumePercent );
    float GetVolume();
    void Seek( float inSeekPercent );
    unsigned int GetPositionMs() const;
    unsigned int GetLength() const;

    bool IsReady() const;
    bool IsPlaying() const;

private:
    void Reset();

    bool LoadStem( const char* inFileName, bool isDrumTrack = false );
    bool LoadURL( const char* inURL, bool isDrumTrack = false );
    // awful
    TrackData* m_trackData = nullptr;
    std::vector<AudioSource> m_sounds;
    std::vector<int> m_drumTracks;

#if USING( ME_FMOD )
    // Add a channel group
    FMOD::ChannelGroup* m_syncGroup = nullptr;
#endif
};
