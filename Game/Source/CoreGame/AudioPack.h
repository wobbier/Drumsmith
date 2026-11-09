#pragma once

#include "TrackList.h"
#include "Components/Audio/AudioSource.h"
#include <chrono>

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
    // Seeks every stem and restarts them together (see Update). Asynchronous: the stems are
    // non-blocking streams, so each seek completes on FMOD's loader thread in its own time.
    void Seek( float inSeekPercent );
    // Starts the stems of a finished seek on one shared DSP tick. Call every frame.
    void Update();
    // A seek hasn't been heard yet (a stem is still seeking, or the shared start is still
    // ahead); the position holds at the target until then.
    bool IsSeeking() const;
    unsigned int GetPositionMs() const;
    unsigned int GetLength() const;
    // How far apart the stems still playing are, in ms (--highway-log; 0 when in step).
    unsigned int StemSpreadMs() const;

    bool IsReady() const;
    bool IsPlaying() const;

private:
    void Reset();
    bool StemsSeeked() const;

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
    bool m_seekPending = false;
    unsigned long long m_seekStartClock = 0;   // the group DSP tick the stems restart on
    unsigned int m_seekTargetMs = 0;
    std::chrono::steady_clock::time_point m_seekStarted;
};
