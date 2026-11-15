#pragma once
#include "Dementia.h"
#include "CoreGame/AudioPack.h"
#include "Pointers.h"

#if USING( ME_EDITOR )

// The Track Editor's playhead: the song's stems (all of them, as in a play) and where in the song
// the editor is. The playhead moves on its own clock, steered to the audio, and keeps its place
// while paused; without audio (headless, a missing file) it still runs, silently.
class Transport
{
public:
    void Open( TrackData& inChart, double inFallbackLength );
    void Close();

    void Play();
    void Pause();
    void Toggle();
    // Back to the start, stopped.
    void Stop();
    void Seek( double inSeconds );
    // Call once a frame.
    void Update( float inDeltaSeconds );

    double Seconds() const { return m_seconds; }
    double Length() const { return m_length; }
    bool IsPlaying() const { return m_playing; }
    bool HasAudio() const;

    void SetSpeed( float inSpeed );
    float Speed() const { return m_speed; }
    void SetVolume( float inVolume );
    float Volume() const { return m_volume; }
    // Only the drum stems are heard (songs that have them: HasDrumStems).
    void SetDrumsOnly( bool inDrumsOnly );
    bool DrumsOnly() const { return m_drumsOnly; }
    bool HasDrumStems() const;

    // A loop zone: playing into its end goes back to its start. It belongs to the editor, not the
    // chart, and is dropped when the song closes. Setting one turns looping on.
    void SetLoop( double inStart, double inEnd );
    void ClearLoop();
    bool HasLoop() const { return m_loopEnd > m_loopStart; }
    double LoopStart() const { return m_loopStart; }
    double LoopEnd() const { return m_loopEnd; }
    // The zone stays where it is while looping is off.
    void SetLooping( bool inLooping ) { m_looping = inLooping; }
    bool IsLooping() const { return m_looping && HasLoop(); }

    static constexpr double kMinLoop = 0.25;

private:
    void ApplySeek();
    void ApplyVolume();

    TrackData* m_chart = nullptr;
#if USING( ME_FMOD )
    UniquePtr<AudioPack> m_pack;
#endif
    double m_seconds = 0.0;
    double m_length = 1.0;
    float m_speed = 1.f;
    float m_volume = 1.f;
    bool m_playing = false;
    bool m_drumsOnly = false;
    double m_loopStart = 0.0;
    double m_loopEnd = 0.0;
    bool m_looping = false;
    // The stems have been started once (their channels exist; from then on they pause and seek).
    bool m_started = false;
    // The playhead moved since the stems were last told where to be.
    bool m_seekDirty = false;
    float m_sinceSeek = 1.f;
};

#endif
