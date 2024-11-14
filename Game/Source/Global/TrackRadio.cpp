#include "TrackRadio.h"
#include "Events/AudioEvents.h"
#include "CoreGame/TrackList.h"
#include "Path.h"
#include "Mathf.h"
#include "Config/GameSettings.h"

void TrackRadio::Play( RadioArgs inTrackArgs )
{
    if( !inTrackArgs.CurrentTrack || inTrackArgs.CurrentTrack == m_currentTrack )
    {
        return;
    }
    Stop();
    m_radioArgs = inTrackArgs;
    bool isAsync = true;

    m_currentTrack = inTrackArgs.CurrentTrack;
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


void TrackRadio::Update()
{
    if( m_radioState == RadioState::Loading )
    {
        if( !m_audioPack.IsReady() )
        {
            return;
        }
        else
        {
            m_audioPack.Play();
            m_audioPack.SetVolume( GameSettings::GetInstance().RadioVolume );
            if( m_radioArgs.UsePreviewMarker )
            {
                m_audioPack.Seek( m_currentTrack->m_previewPercent );
                m_radioState = RadioState::Seeking;
            }
            else
            {
                m_radioState = RadioState::Playing;
            }
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
            m_audioPack.Resume();
            m_radioState = RadioState::Playing;
        }
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
