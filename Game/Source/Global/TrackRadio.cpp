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

    //if( m_currentlyPlayingPtr && !m_currentlyPlayingPtr->IsLoaded() )
    //{
    //    return;
    //}
    m_currentTrack = inTrackArgs.CurrentTrack;
    Path previewPath = Path( Path( m_currentTrack->m_trackSourcePath ).GetDirectoryString() + "preview.ogg" );

    {

        m_currentlyPlaying = AudioSource( m_currentTrack->m_trackSourcePath );
        SharedPtr<AudioSource> source;
        PlayAudioEvent evt;
        evt.Immediate = true;
        if( previewPath.Exists )
        {
            evt.SourceName = previewPath.FullPath;
        }
        else
        {
            evt.SourceName = m_currentlyPlaying.FilePath.FullPath;
        }
        if( inTrackArgs.UsePreviewMarker )
        {
            evt.StartPercent = m_currentTrack->m_previewPercent;
        }
        evt.Volume = GameSettings::GetInstance().RadioVolume;

        evt.Callback = [&source, this]( SharedPtr<AudioSource> loadedAudio ) { loadedAudio->Stop(); m_currentlyPlayingPtr = loadedAudio; };
        evt.Fire();
    }

    if( !previewPath.Exists )
    {
        PlayStem( "crowd.ogg", inTrackArgs.UsePreviewMarker );
        PlayStem( "drums.ogg", inTrackArgs.UsePreviewMarker );
        PlayStem( "drums_1.ogg", inTrackArgs.UsePreviewMarker );
        PlayStem( "drums_2.ogg", inTrackArgs.UsePreviewMarker );
        PlayStem( "drums_3.ogg", inTrackArgs.UsePreviewMarker );
        PlayStem( "drums_4.ogg", inTrackArgs.UsePreviewMarker );
        PlayStem( "guitar.ogg", inTrackArgs.UsePreviewMarker );
        PlayStem( "vocals.ogg", inTrackArgs.UsePreviewMarker );
        PlayStem( "rhythm.ogg", inTrackArgs.UsePreviewMarker );
        PlayStem( "keys.ogg", inTrackArgs.UsePreviewMarker );

        for( auto ptr : m_currentStems )
        {
            if( ptr )
            {
                if( inTrackArgs.UsePreviewMarker )
                {
                    ptr->SetPositionPercent( m_currentTrack->m_previewPercent );
                }
                ptr->Play( true );
                ptr->SetVolume( GameSettings::GetInstance().RadioVolume );
                if( inTrackArgs.UsePreviewMarker )
                {
                    ptr->SetPositionPercent( m_currentTrack->m_previewPercent );
                }
            }
        }
    }
    if( m_currentlyPlayingPtr )
    {
        if( inTrackArgs.UsePreviewMarker )
        {
            m_currentlyPlayingPtr->SetPositionPercent( m_currentTrack->m_previewPercent );
        }
        m_currentlyPlayingPtr->Play();
        m_currentlyPlayingPtr->SetVolume( GameSettings::GetInstance().RadioVolume );
        if( inTrackArgs.UsePreviewMarker )
        {
            m_currentlyPlayingPtr->SetPositionPercent( m_currentTrack->m_previewPercent );
        }
    }
    m_radioState = RadioState::Loading;
}


bool TrackRadio::IsPlaying() const
{
    if( m_currentlyPlayingPtr )
    {
        return m_currentlyPlayingPtr->IsPlaying();
    }
    return false;
}


bool TrackRadio::PlayStem( const char* inFileName, bool inUsePreviewMarker )
{
    Path drumsPath = Path( Path( m_currentTrack->m_trackSourcePath ).GetDirectoryString() + inFileName );
    if( drumsPath.Exists )
    {
        SharedPtr<AudioSource> source;
        PlayAudioEvent evt;
        evt.SourceName = drumsPath.FullPath;
        evt.Immediate = true;
        if( inUsePreviewMarker )
        {
            evt.StartPercent = m_currentTrack->m_previewPercent;
        }
        evt.Volume = GameSettings::GetInstance().RadioVolume;

        evt.Callback = [&source, this]( SharedPtr<AudioSource> loadedAudio ) { loadedAudio->Stop();  m_currentStems.push_back( loadedAudio ); };
        evt.Fire();
        return true;
    }
    return false;
}

void TrackRadio::Stop()
{
    if( m_currentlyPlayingPtr )
    {
        m_currentlyPlayingPtr->Stop();
        StopAudioEvent evt;
        evt.SourceName = m_currentTrack->m_trackSourcePath;
        evt.Fire();
        m_currentlyPlayingPtr.reset();
    }
    for( auto ptr : m_currentStems )
    {
        if( ptr )
        {
            ptr->Stop( true );
            ptr.reset();
        }
    }
    m_currentStems.clear();
    m_radioState = RadioState::None;
}

void TrackRadio::SetVolume( float inVolume )
{
    float volumeClamped = Mathf::Clamp( 0.f, 1.f, inVolume );
    if( m_currentlyPlayingPtr && m_currentlyPlayingPtr->IsPlaying() )
    {
        m_currentlyPlayingPtr->SetVolume( volumeClamped );
    }

    for( auto ptr : m_currentStems )
    {
        if( ptr && ptr->IsPlaying() )
        {
            ptr->SetVolume( volumeClamped );
        }
    }
}

void TrackRadio::TryPlayNextTrack()
{
    if( !m_currentlyPlayingPtr )
    {
        return;
    }
    else
    {
        bool loaded = m_currentlyPlayingPtr->IsLoaded();

        for( auto ptr : m_currentStems )
        {
            if( ptr )
            {
                loaded = loaded && ptr->IsLoaded();
            }
        }

        if (loaded)
        {
            m_currentlyPlayingPtr->Play();
            m_currentlyPlayingPtr->SetVolume( GameSettings::GetInstance().RadioVolume );
            if( m_radioArgs.UsePreviewMarker )
            {
                m_currentlyPlayingPtr->SetPositionPercent( m_currentTrack->m_previewPercent );
            }

            for( auto ptr : m_currentStems )
            {
                if( ptr )
                {
                    ptr->Play();
                    ptr->SetVolume( GameSettings::GetInstance().RadioVolume );
                    if( m_radioArgs.UsePreviewMarker )
                    {
                        ptr->SetPositionPercent( m_currentTrack->m_previewPercent );
                    }
                }
            }
            m_radioState = RadioState::Playing;
        }
    }
}

void TrackRadio::Update()
{
    if( m_radioState == RadioState::Loading )
    {
        if( m_currentlyPlayingPtr && !m_currentlyPlayingPtr->IsPlaying() )
        {
            TryPlayNextTrack();
        }
    }

    if( m_radioState == RadioState::Playing )
    {
        if( m_currentlyPlayingPtr && !m_currentlyPlayingPtr->IsPlaying() )
        {
            m_radioState = RadioState::None;
        }
    }
}

bool TrackRadio::CanPlayNextTrack() const
{
    return m_radioState == RadioState::None;
}
