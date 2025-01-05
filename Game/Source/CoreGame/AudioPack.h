#pragma once
#include "TrackList.h"
#include "Components\Audio\AudioSource.h"

namespace FMOD { class ChannelGroup; }

class AudioPack
{
public:
    AudioPack() = default;
    AudioPack( TrackData& inTrackData );
    ~AudioPack();

    void Play();
    void Pause();
    void Resume();
    void Stop();

    void SetVolume( float inVolumePercent );
    void SetDrumVolume( float inVolumePercent );
    float GetVolume();
    void Seek( float inSeekPercent );
    float GetPositionMs();

    bool IsReady() const;
    bool IsPlaying() const;

private:
    bool LoadStem( const char* inFileName, bool isDrumTrack = false );
    bool LoadURL( const char* inURL, bool isDrumTrack = false );
    // awful
    TrackData* m_trackData = nullptr;
    std::vector<AudioSource> m_sounds;
    std::vector<int> m_drumTracks;
    FMOD::ChannelGroup* syncGroup = nullptr;
};