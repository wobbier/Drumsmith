#include "TrackRadio.h"
#include "Events/AudioEvents.h"
#include "CoreGame/TrackList.h"
#include "Path.h"
#include "Mathf.h"
#include "Config/GameSettings.h"
#include "CLog.h"

namespace
{
    constexpr float kHandOverFadeSeconds = 0.03f;
    constexpr float kLoadTimeoutSeconds = 10.f;
}

const TrackData* TrackRadio::GetCurrentTrack() const
{
    if( m_guest )
    {
        return m_guest.get();
    }
    const auto& tracks = TrackDatabase::GetInstance().m_trackList.m_tracks;
    if( m_currentTrackIndex < 0 || m_currentTrackIndex >= static_cast<int>( tracks.size() ) )
    {
        return nullptr;
    }
    return &tracks[m_currentTrackIndex];
}


void TrackRadio::Play( RadioArgs inTrackArgs )
{
    if( !inTrackArgs.CurrentTrack || ( !m_guest && inTrackArgs.CurrentTrackIndex == m_currentTrackIndex ) )
    {
        return;
    }
    m_guest.reset();
    Start( *inTrackArgs.CurrentTrack, inTrackArgs.CurrentTrackIndex, inTrackArgs.UsePreviewMarker );
}


void TrackRadio::PlayGuest( const TrackData& inTrack, bool inUsePreviewMarker )
{
    m_guest = std::make_unique<TrackData>( inTrack );
    Start( *m_guest, -1, inUsePreviewMarker );
}


void TrackRadio::Start( TrackData& inTrack, int inTrackIndex, bool inUsePreviewMarker )
{
    // Fade the old song out under the new one's load rather than cutting it off.
    m_audioPack.FadeOut( kHandOverFadeSeconds );
    m_fadingPack = std::move( m_audioPack );
    m_fadingTimer = kHandOverFadeSeconds + 0.05f;
    m_radioArgs = RadioArgs();
    m_radioArgs.CurrentTrackIndex = inTrackIndex;
    m_radioArgs.UsePreviewMarker = inUsePreviewMarker;

    m_currentTrackIndex = inTrackIndex;
    m_previewPercent = inUsePreviewMarker ? inTrack.m_previewPercent : 0.f;
    // The stems are non-blocking streams: this opens them and returns; Update waits for them.
    m_audioPack = AudioPack( inTrack );
    m_loadingFor = 0.f;
    m_radioState = RadioState::Loading;
}


void TrackRadio::OnTrackRemoved( int inIndex )
{
    if( m_guest )
    {
        return;
    }
    if( inIndex == m_currentTrackIndex )
    {
        // Let go of its files before they are deleted.
        m_audioPack = AudioPack();
        m_fadingPack = AudioPack();
        m_fadingTimer = 0.f;
        m_currentTrackIndex = -1;
        m_radioState = RadioState::None;
    }
    else if( inIndex < m_currentTrackIndex )
    {
        --m_currentTrackIndex;
    }
}


bool TrackRadio::IsPlaying() const
{
    return m_audioPack.IsPlaying();
}


void TrackRadio::Stop()
{
    m_audioPack.Stop();
    m_radioState = RadioState::None;
}


void TrackRadio::SetVolume( float inVolume )
{
    float volumeClamped = Mathf::Clamp( 0.f, 1.f, inVolume );
    m_audioPack.SetVolume( volumeClamped );
}


float TrackRadio::GetTotalLength() const
{
    return m_audioPack.GetLength();
}


float TrackRadio::GetPositionMS() const
{
    return m_audioPack.GetPositionMs();
}


void TrackRadio::Seek( float inPercent )
{
    m_audioPack.Seek( inPercent );
}


float TrackRadio::GetLevel()
{
    return m_radioState == RadioState::Playing ? m_audioPack.GetLevel() : 0.f;
}


void TrackRadio::SetSpeaker( const RoomSpeaker& inSpeaker, float inOpen, float inPan, float inLevel )
{
    m_speaker = inSpeaker;
    m_speakerOpen = inOpen;
    m_speakerPan = inPan;
    m_speakerLevel = inLevel;
    m_audioPack.SetSpeaker( inSpeaker, inOpen, inPan, inLevel );
    m_fadingPack.SetSpeaker( inSpeaker, inOpen, inPan, inLevel );
}


void TrackRadio::Update( float dt )
{
    // A new song's pack plays from the same place as the last.
    m_audioPack.SetSpeaker( m_speaker, m_speakerOpen, m_speakerPan, m_speakerLevel );
    if( m_fadingTimer > 0.f )
    {
        m_fadingTimer -= dt;
        if( m_fadingTimer <= 0.f )
        {
            m_fadingPack = AudioPack();
        }
    }
    m_audioPack.Update();
    if( m_radioState == RadioState::Loading )
    {
        // Streams open on FMOD's loader thread; nothing is started until every stem is in.
        if( !m_audioPack.IsReady() )
        {
            m_loadingFor += dt;
            if( m_loadingFor > kLoadTimeoutSeconds )
            {
                // A file that won't open (a broken download): give up so the next song can play.
                YIKES( "TrackRadio: a song didn't load; skipping it" );
                Stop();
            }
            return;
        }
        m_audioPack.Play();
        m_audioPack.SetVolume( GameSettings::GetInstance().RadioVolume );
        if( m_radioArgs.UsePreviewMarker )
        {
            m_audioPack.Seek( m_previewPercent );
            m_radioState = RadioState::Seeking;
        }
        else
        {
            m_radioState = RadioState::Playing;
        }
        return;
    }

    if( m_radioState == RadioState::Seeking )
    {
        if( !m_audioPack.IsReady() )
        {
            return;
        }
        else
        {
            //if( m_delayTimer >= 0 )
            //{
            //    m_delayTimer -= dt;
            //    return;
            //}
            m_audioPack.Resume();
            m_radioState = RadioState::Playing;
        }
        return;
    }

    if( m_radioState == RadioState::Playing )
    {
        if( !m_audioPack.IsPlaying() )
        {
            m_radioState = RadioState::None;
        }
    }
}


bool TrackRadio::CanPlayNextTrack() const
{
    return m_radioState == RadioState::None;
}


void TrackRadio::Resume()
{
    m_audioPack.Resume();
}
