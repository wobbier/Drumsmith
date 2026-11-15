#include "Editor/Chart/Transport.h"
#include <algorithm>
#include <cmath>

#if USING( ME_EDITOR )

void Transport::Open( TrackData& inChart, double inFallbackLength )
{
    Close();
    m_chart = &inChart;
    m_length = std::max( 1.0, inFallbackLength );
#if USING( ME_FMOD )
    m_pack = MakeUnique<AudioPack>( inChart );
#endif
}


void Transport::Close()
{
#if USING( ME_FMOD )
    m_pack.reset();
#endif
    m_chart = nullptr;
    m_seconds = 0.0;
    m_playing = false;
    m_started = false;
    m_seekDirty = false;
    ClearLoop();
}


bool Transport::HasAudio() const
{
#if USING( ME_FMOD )
    return m_pack && m_pack->IsReady() && m_pack->GetLength() > 0;
#else
    return false;
#endif
}


void Transport::Play()
{
    if( !m_chart || m_playing )
    {
        return;
    }
    if( m_seconds >= m_length - 0.05 )
    {
        m_seconds = 0.0;
        m_seekDirty = true;
    }
    m_playing = true;
#if USING( ME_FMOD )
    if( HasAudio() )
    {
        if( m_started && !m_pack->IsPlaying() )
        {
            // The stems were stopped under us (the editor entering or leaving play stops all
            // audio) or ran out: start them again, at the playhead.
            m_started = false;
        }
        if( !m_started )
        {
            m_pack->Play();
            ApplyVolume();
            m_pack->SetPlaybackSpeed( m_speed );
            m_started = true;
            m_seekDirty = m_seconds > 0.0;
        }
        ApplySeek();
        m_pack->Resume();
    }
#endif
}


void Transport::Pause()
{
    if( !m_playing )
    {
        return;
    }
    m_playing = false;
#if USING( ME_FMOD )
    if( m_pack && m_started )
    {
        m_pack->Pause();
    }
#endif
}


void Transport::Toggle()
{
    if( m_playing )
    {
        Pause();
    }
    else
    {
        Play();
    }
}


void Transport::Stop()
{
    Pause();
    Seek( 0.0 );
}


void Transport::Seek( double inSeconds )
{
    m_seconds = std::clamp( inSeconds, 0.0, m_length );
    m_seekDirty = true;
}


void Transport::ApplySeek()
{
#if USING( ME_FMOD )
    if( m_seekDirty && m_started && HasAudio() )
    {
        m_pack->Seek( static_cast<float>( m_seconds * 1000.0 / static_cast<double>( m_pack->GetLength() ) ) );
        m_sinceSeek = 0.f;
    }
#endif
    m_seekDirty = false;
}


void Transport::Update( float inDeltaSeconds )
{
    if( !m_chart )
    {
        return;
    }
    m_sinceSeek += inDeltaSeconds;
    bool audio = false;
#if USING( ME_FMOD )
    audio = HasAudio();
    if( audio )
    {
        m_length = static_cast<double>( m_pack->GetLength() ) / 1000.0;
        m_pack->Update();
    }
#endif
    if( !m_playing )
    {
        return;
    }
    const double before = m_seconds;
    if( m_seekDirty && !audio )
    {
        // No stems to move: the playhead is already there.
        m_seekDirty = false;
    }
#if USING( ME_FMOD )
    // Stopped under us while playing (see Play); at the very end they have simply run out.
    bool alive = audio && m_started && ( m_pack->IsSeeking() || m_pack->IsPlaying() );
    if( audio && m_started && !alive && m_seconds < m_length - 0.25 )
    {
        m_started = false;
    }
    if( audio && !m_started )
    {
        // Play was pressed before the stems had loaded, or they have to start again.
        m_playing = false;
        Play();
        alive = m_started;
    }
    // A scrub while playing: the stems follow, a few times a second at most (each seek is a
    // stream reposition).
    if( audio && m_seekDirty && m_sinceSeek > 0.12f )
    {
        ApplySeek();
    }
    if( alive && !m_seekDirty )
    {
        if( m_pack->IsSeeking() )
        {
            return;
        }
        // The frame clock, steered to the audio: FMOD's position comes in mixer blocks, which
        // would make the playhead (and the preview's highway) step.
        m_seconds += static_cast<double>( inDeltaSeconds ) * m_speed;
        const double heard = static_cast<double>( m_pack->GetPositionMs() ) / 1000.0;
        const double error = heard - m_seconds;
        m_seconds = std::abs( error ) > 0.08 ? heard : m_seconds + error * 0.1;
    }
    else
#endif
    if( !m_seekDirty )
    {
        m_seconds += static_cast<double>( inDeltaSeconds ) * m_speed;
    }
    // Only on playing into the zone's end: a playhead put past it plays on.
    if( IsLooping() && before < m_loopEnd && m_seconds >= m_loopEnd )
    {
        Seek( m_loopStart );
        return;
    }
    if( m_seconds >= m_length )
    {
        m_seconds = m_length;
        Pause();
    }
}


void Transport::SetLoop( double inStart, double inEnd )
{
    const double start = std::clamp( std::min( inStart, inEnd ), 0.0, std::max( 0.0, m_length - kMinLoop ) );
    m_loopStart = start;
    m_loopEnd = std::clamp( std::max( inStart, inEnd ), start + kMinLoop, std::max( start + kMinLoop, m_length ) );
    m_looping = true;
}


void Transport::ClearLoop()
{
    m_loopStart = 0.0;
    m_loopEnd = 0.0;
    m_looping = false;
}


void Transport::SetSpeed( float inSpeed )
{
    m_speed = std::clamp( inSpeed, 0.25f, 2.f );
#if USING( ME_FMOD )
    if( m_pack && m_started )
    {
        m_pack->SetPlaybackSpeed( m_speed );
    }
#endif
}


void Transport::SetVolume( float inVolume )
{
    m_volume = std::clamp( inVolume, 0.f, 1.f );
    ApplyVolume();
}


void Transport::SetDrumsOnly( bool inDrumsOnly )
{
    m_drumsOnly = inDrumsOnly;
    ApplyVolume();
}


bool Transport::HasDrumStems() const
{
#if USING( ME_FMOD )
    return m_pack && m_pack->HasDrumStems();
#else
    return false;
#endif
}


void Transport::ApplyVolume()
{
#if USING( ME_FMOD )
    if( m_pack && m_started )
    {
        const bool drumsOnly = m_drumsOnly && m_pack->HasDrumStems();
        m_pack->SetVolume( drumsOnly ? 0.f : m_volume );
        if( drumsOnly )
        {
            m_pack->SetDrumVolume( m_volume );
        }
    }
#endif
}

#endif
