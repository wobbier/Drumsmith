#include "TrackRadio.h"
#include "Events/AudioEvents.h"

void TrackRadio::Play()
{
    m_currentlyPlaying = AudioSource(m_currentTrack->m_trackSourcePath);
    SharedPtr<AudioSource> source;
    PlayAudioEvent evt;
    evt.SourceName = m_currentlyPlaying.FilePath.FullPath;
    evt.StartPercent = m_currentTrack->m_previewPercent;
    evt.Volume = 0.05f;
    
    evt.Callback = [&source, this]( SharedPtr<AudioSource> loadedAudio ) { m_currentlyPlayingPtr = loadedAudio; };
    evt.Fire();
}

void TrackRadio::Stop()
{
    if( m_currentlyPlayingPtr )
    {
        m_currentlyPlayingPtr->Stop();
    }
}
