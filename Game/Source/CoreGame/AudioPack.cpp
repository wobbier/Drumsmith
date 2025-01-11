#include "AudioPack.h"
#include "Cores/AudioCore.h"
#include "Engine/Engine.h"
#include "Resources/SoundResource.h"
#include "Resource/ResourceCache.h"
#include <fmod.hpp>
#include "Pointers.h"

AudioPack::AudioPack( TrackData& inTrackData )
{
    m_trackData = &inTrackData;
    // I should track all the needed files in the track data
    LoadStem( m_trackData->m_trackFileName.c_str() );
    LoadStem( "crowd.ogg" );
    LoadStem( "drums.ogg", true );
    LoadStem( "drums_1.ogg", true );
    LoadStem( "drums_2.ogg", true );
    LoadStem( "drums_3.ogg", true );
    LoadStem( "drums_4.ogg", true );
    LoadStem( "guitar.ogg" );
    LoadStem( "vocals.ogg" );
    LoadStem( "rhythm.ogg" );
    LoadStem( "keys.ogg" );
    //GetEngine().AudioThread->GetSystem()->createChannelGroup( m_trackData->m_trackName.c_str(), &syncGroup );
    //
    //for (auto& song : m_sounds)
    //{
    //    song.ChannelHandle->setChannelGroup( syncGroup );
    //}
}


AudioPack::~AudioPack()
{
    m_sounds.clear();
}


void AudioPack::Play()
{
    //ME_ASSERT_MSG( IsReady(), "AudioPack isn't loaded yet.");
    //if (!IsReady())
    //{
    //    return;
    //}

    for( auto& sound : m_sounds )
    {
        sound.Play();
    }
}


void AudioPack::Pause()
{
    //syncGroup->setPaused( true );
    for( auto& sound : m_sounds )
    {
        sound.Pause();
    }
}


void AudioPack::Resume()
{
    //syncGroup->setPaused( false );
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


void AudioPack::SetDrumVolume( float inVolumePercent )
{
    for( auto sound : m_drumTracks )
    {
        m_sounds[sound].SetVolume(inVolumePercent);
    }
}


float AudioPack::GetVolume()
{
    return m_sounds[0].GetVolume();
}


void AudioPack::Seek( float inSeekPercent )
{
    Pause();

    float timestamp = m_sounds[0].GetLength() * inSeekPercent;

    for( auto& sound : m_sounds )
    {
        sound.SetPositionMs( timestamp );

    }
    //while( !IsReady() )
    //{
    //}
    //unsigned long long dspClock1;
    //m_sounds[0].ChannelHandle->getDSPClock( nullptr, &dspClock1 );
    //unsigned long long bufferLength = 16384; // Adjust this based on your audio system
    //unsigned long long startTime = dspClock1 + bufferLength;
    //
    //
    //for( auto& sound : m_sounds )
    //{
    //    sound.ChannelHandle->setDelay( startTime, 0, false );
    //}
    //Resume();
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


bool AudioPack::LoadStem( const char* inFileName, bool isDrumTrack )
{
    Path drumsPath = Path( Path( m_trackData->m_trackSourcePath ).GetDirectoryString() + inFileName );
    
    if( drumsPath.Exists )
    {
        AudioSource audioSource( inFileName );
        SharedPtr<Sound> soundResource = ResourceCache::GetInstance().Get<Sound>( drumsPath, GetEngine().AudioThread->GetSystem(), SoundFlags::NonBlocking | SoundFlags::CreateStream );
        if( !soundResource )
        {
            YIKES_FMT( "Failed to load sound: %s", audioSource.FilePath.GetLocalPathString().c_str() );
            audioSource.IsInitialized = true;
        }
        audioSource.SoundInstance = soundResource;

        m_sounds.push_back( audioSource );
        if( isDrumTrack )
        {
            m_drumTracks.push_back( m_sounds.size() - 1 );
        }
        return true;
    }

    return false;
}


bool AudioPack::LoadURL( const char* inURL, bool isDrumTrack /*= false */ )
{
    AudioSource audioSource( inURL );
    SharedPtr<Sound> soundResource = MakeShared<Sound>( inURL, GetEngine().AudioThread->GetSystem() );
    if( !soundResource )
    {
        YIKES_FMT( "Failed to load sound: %s", audioSource.FilePath.GetLocalPathString().c_str() );
        audioSource.IsInitialized = true;
    }
    audioSource.SoundInstance = soundResource;

    m_sounds.push_back( audioSource );
    if( isDrumTrack )
    {
        m_drumTracks.push_back( m_sounds.size() - 1 );
    }
    // I might keep having to play the song if trying to stream from a URL.
    Play();
    return true;
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
