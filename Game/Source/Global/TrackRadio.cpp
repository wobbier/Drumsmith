#include "TrackRadio.h"
#include "Events/AudioEvents.h"
#include "CoreGame/TrackList.h"
#include "Path.h"
#include "Mathf.h"
#include "Config/GameSettings.h"

void TrackRadio::Play( RadioArgs inTrackArgs )
{
    // remove this ptr compare and think of another way.
    if( !inTrackArgs.CurrentTrack || inTrackArgs.CurrentTrackIndex == m_currentTrackIndex )
    {
        return;
    }
    Stop();
    m_radioArgs = inTrackArgs;
    bool isAsync = true;

    m_currentTrack = inTrackArgs.CurrentTrack;
    m_currentTrackIndex = inTrackArgs.CurrentTrackIndex;
    m_previewPercent = 0.f;
    if( inTrackArgs.UsePreviewMarker )
    {
        m_previewPercent = m_currentTrack->m_previewPercent;
    }
    m_audioPack = AudioPack( *m_currentTrack );

    // Audio streams are pretty quick, why even have a preview audio file?
    //Path previewPath = Path( Path( m_currentTrack->m_trackSourcePath ).GetDirectoryString() + "preview.ogg" );
    //
    //if( !previewPath.Exists )
    //{
    //}

    m_radioState = RadioState::Loading;
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


void TrackRadio::Update( float dt )
{
    if( m_radioState == RadioState::Loading )
    {
        if( !m_audioPack.IsReady() )
        {
            // this feels weird, but okay??
            m_audioPack.Play();
            return;
        }
        else
        {
            m_audioPack.Play();
            m_audioPack.SetVolume( GameSettings::GetInstance().RadioVolume );
            if( m_radioArgs.UsePreviewMarker )
            {
                m_audioPack.Seek( m_previewPercent );
                m_delayTimer = 1;
                m_radioState = RadioState::Seeking;
            }
            else
            {
                m_radioState = RadioState::Playing;
            }
            return;
        }
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
