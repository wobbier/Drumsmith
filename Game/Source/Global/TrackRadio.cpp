#include "TrackRadio.h"
#include "Events/AudioEvents.h"
#include "CoreGame/TrackList.h"
#include "Path.h"
#include "Mathf.h"
#include "Config/GameSettings.h"

void TrackRadio::Play( TrackData* inTrackData, bool inUsePreviewMarker )
{
    if( !inTrackData || inTrackData == m_currentTrack )
    {
        return;
    }

    Stop();
    m_currentTrack = inTrackData;
    Path previewPath = Path( Path( m_currentTrack->m_trackSourcePath ).GetDirectoryString() + "preview.ogg" );

    {

        m_currentlyPlaying = AudioSource( m_currentTrack->m_trackSourcePath );
        SharedPtr<AudioSource> source;
        PlayAudioEvent evt;
        if( previewPath.Exists )
        {
            evt.SourceName = previewPath.FullPath;
        }
        else
        {
            evt.SourceName = m_currentlyPlaying.FilePath.FullPath;
        }
        if( inUsePreviewMarker )
        {
            evt.StartPercent = m_currentTrack->m_previewPercent;
        }
        evt.Volume = GameSettings::GetInstance().RadioVolume;

        evt.Callback = [&source, this]( SharedPtr<AudioSource> loadedAudio ) { loadedAudio->Stop(); m_currentlyPlayingPtr = loadedAudio; };
        evt.Fire();
    }

    if( !previewPath.Exists )
    {
        PlayStem( "crowd.ogg", inUsePreviewMarker );
        PlayStem( "drums.ogg", inUsePreviewMarker );
        PlayStem( "drums_1.ogg", inUsePreviewMarker );
        PlayStem( "drums_2.ogg", inUsePreviewMarker );
        PlayStem( "drums_3.ogg", inUsePreviewMarker );
        PlayStem( "drums_4.ogg", inUsePreviewMarker );
        PlayStem( "guitar.ogg", inUsePreviewMarker );
        PlayStem( "vocals.ogg", inUsePreviewMarker );
        PlayStem( "rhythm.ogg", inUsePreviewMarker );
        PlayStem( "keys.ogg", inUsePreviewMarker );

        for( auto ptr : m_currentStems )
        {
            if( ptr )
            {
                if( inUsePreviewMarker )
                {
                    ptr->SetPositionPercent( m_currentTrack->m_previewPercent );
                }
                ptr->Play( true );
                ptr->SetVolume( GameSettings::GetInstance().RadioVolume );
                if( inUsePreviewMarker )
                {
                    ptr->SetPositionPercent( m_currentTrack->m_previewPercent );
                }
            }
        }
    }
    if( m_currentlyPlayingPtr )
    {
        if( inUsePreviewMarker )
        {
            m_currentlyPlayingPtr->SetPositionPercent( m_currentTrack->m_previewPercent );
        }
        m_currentlyPlayingPtr->Play();
        m_currentlyPlayingPtr->SetVolume( GameSettings::GetInstance().RadioVolume );
        if( inUsePreviewMarker )
        {
            m_currentlyPlayingPtr->SetPositionPercent( m_currentTrack->m_previewPercent );
        }
    }
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
    }
    for( auto ptr : m_currentStems )
    {
        if( ptr )
        {
            ptr->Stop( true );
        }
    }
    m_currentStems.clear();
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
