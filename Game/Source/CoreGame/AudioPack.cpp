#include "AudioPack.h"
#include "Cores\AudioCore.h"
#include "Engine\Engine.h"
#include "Resources\SoundResource.h"
#include "Resource\ResourceCache.h"

AudioPack::AudioPack( TrackData& inTrackData )
{
    m_trackData = &inTrackData;
    // I should track all the needed files in the track data
    LoadStem( m_trackData->m_trackFileName.c_str() );
    LoadStem( "crowd.ogg" );
    LoadStem( "drums.ogg" );
    LoadStem( "drums.mp3" );
    LoadStem( "drums_1.ogg" );
    LoadStem( "drums_2.ogg" );
    LoadStem( "drums_3.ogg" );
    LoadStem( "drums_4.ogg" );
    LoadStem( "guitar.ogg" );
    LoadStem( "vocals.ogg" );
    LoadStem( "rhythm.ogg" );
    LoadStem( "keys.ogg" );
}


AudioPack::~AudioPack()
{
    m_sounds.clear();
}


void AudioPack::Play()
{
    ME_ASSERT_MSG( IsReady(), "AudioPack isn't loaded yet.");
    if (!IsReady())
    {
        return;
    }

    for( auto& sound : m_sounds )
    {
        sound.Play();
    }
}


void AudioPack::Pause()
{
    for( auto& sound : m_sounds )
    {
        sound.Pause();
    }
}


void AudioPack::Resume()
{
    for( auto& sound : m_sounds )
    {
        sound.Resume();
    }
}


void AudioPack::Stop()
{
    for( auto& sound : m_sounds )
    {
        sound.Stop();
    }
}


void AudioPack::SetVolume( float inVolumePercent )
{
    for( auto& sound : m_sounds )
    {
        sound.SetVolume( inVolumePercent );
    }
}


void AudioPack::Seek( float inSeekPercent )
{
    Pause();
    float timestamp = m_sounds[0].GetLength() * inSeekPercent;
    for( auto& sound : m_sounds )
    {
        sound.SetPositionMs( timestamp );
    }
}


float AudioPack::GetPositionMs()
{
    return m_sounds[0].GetPositionMs();
}


bool AudioPack::IsPlaying() const
{
    if( m_sounds.empty() )
    {
        return false;
    }
    return m_sounds[0].IsPlaying();
}


bool AudioPack::LoadStem( const char* inFileName )
{
    Path drumsPath = Path( Path( m_trackData->m_trackSourcePath ).GetDirectoryString() + inFileName );
    
    if( drumsPath.Exists )
    {
        AudioSource audioSource( drumsPath.FullPath );
        SharedPtr<Sound> soundResource = ResourceCache::GetInstance().Get<Sound>( drumsPath, GetEngine().AudioThread->GetSystem(), SoundFlags::NonBlocking | SoundFlags::CreateStream );
        if( !soundResource )
        {
            YIKES_FMT( "Failed to load sound: %s", audioSource.FilePath.GetLocalPathString().c_str() );
            audioSource.IsInitialized = true;
        }
        audioSource.SoundInstance = soundResource;

        m_sounds.push_back( audioSource );
        return true;
    }

    return false;
}

bool AudioPack::IsReady() const
{
    if (m_sounds.empty())
    {
        return false;
    }

    for( auto& sound : m_sounds )
    {
        if( !sound.IsLoaded() )
            return false;
    }
    return true;
}
