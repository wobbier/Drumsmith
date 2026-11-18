#pragma once

#include "TrackList.h"
#include "Components/Audio/AudioSource.h"
#include <chrono>

#if USING( ME_FMOD )
namespace FMOD { class ChannelGroup; class DSP; }
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
    // A click track laid over the song as one more stem (ClickTrack::MetronomeFile), so it
    // starts, pauses and seeks with the rest. Added after the song has started, it joins at the
    // next Seek. False when the file isn't there.
    bool AddMetronome( const std::string& inFile );
    bool HasMetronome() const { return m_metronome >= 0; }
    void SetMetronomeVolume( float inVolumePercent );
    // The metronome's stem has a channel and it is playing (--highway-log).
    bool IsMetronomePlaying() const;
    // The song came with its drums on stems of their own.
    bool HasDrumStems() const { return !m_drumTracks.empty(); }
    // Plays every stem faster or slower (pitch follows); 1 is normal. For the Track Editor.
    void SetPlaybackSpeed( float inSpeed );
    float GetVolume();
    // Seeks every stem and restarts them together (see Update). Asynchronous: the stems are
    // non-blocking streams, so each seek completes on FMOD's loader thread in its own time.
    // inFadeInSeconds: how long the stems take to come back up (0: the short anti-click ramp).
    void Seek( float inSeekPercent, float inFadeInSeconds = 0.f );
    // Starts the stems of a finished seek on one shared DSP tick. Call every frame.
    void Update();
    // A seek hasn't been heard yet (a stem is still seeking, or the shared start is still
    // ahead); the position holds at the target until then.
    bool IsSeeking() const;
    unsigned int GetPositionMs() const;
    unsigned int GetLength() const;
    // How far apart the stems still playing are, in ms (--highway-log; 0 when in step).
    unsigned int StemSpreadMs() const;

    // Ramps the stems to silence over inSeconds, then stops them; for handing over to another
    // pack without cutting the waveform mid-cycle (a click). Keep the pack alive until it's done.
    void FadeOut( float inSeconds );

    bool IsReady() const;
    bool IsPlaying() const;
    // The song as a speaker somewhere in a room plays it (the hideout's radio): inOpen 0 is a
    // small speaker across the room (no lows, no highs), 1 the song as it is; inPan -1 left to 1
    // right; inLevel 0 to 1 on top of the volume. 1, 0, 1 takes the effect off.
    void SetSpeaker( float inOpen, float inPan, float inLevel );
    // How loud the pack is coming out right now: the RMS of its group's output, 0 (silence) to
    // about 1 (full scale), averaged over the channels. Turns FMOD's metering on at the first call.
    float GetLevel();

private:
    void Reset();
    bool StemsSeeked() const;
    // Ramps the group up from silence starting at inGroupClock (the stems' start tick), so a
    // start mid-song doesn't step from zero to a full-scale sample.
    void FadeInAt( unsigned long long inGroupClock );

    bool LoadStem( const std::string& inDirectory, const char* inFileName, bool isDrumTrack = false );
    bool LoadURL( const char* inURL, bool isDrumTrack = false );
    std::vector<AudioSource> m_sounds;
    std::vector<int> m_drumTracks;
    int m_metronome = -1;

#if USING( ME_FMOD )
    // Add a channel group
    FMOD::ChannelGroup* m_syncGroup = nullptr;
    // SetSpeaker's band limit, made on first use.
    FMOD::DSP* m_speakerEq = nullptr;
    // GetLevel's meter: the group's head DSP, metering its output.
    bool m_metering = false;
#endif
    bool m_seekPending = false;
    unsigned long long m_seekStartClock = 0;   // the group DSP tick the stems restart on
    unsigned int m_seekTargetMs = 0;
    float m_seekFadeSeconds = 0.f;
    std::chrono::steady_clock::time_point m_seekStarted;
};
