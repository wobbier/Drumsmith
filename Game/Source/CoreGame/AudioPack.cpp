#include "AudioPack.h"

#if USING( ME_FMOD )

#include "Cores/AudioCore.h"
#include "Engine/Engine.h"
#include "Resources/SoundResource.h"
#include "Resource/ResourceCache.h"
#include <fmod.hpp>
#include "Pointers.h"
#include <utility>

AudioPack::AudioPack( TrackData& inTrackData )
{
    m_trackData = &inTrackData;
    // Create the channel group for these stems:
    FMOD::System* system = GetEngine().AudioThread->GetSystem();
    system->createChannelGroup(
        m_trackData->m_trackName.c_str(),
        &m_syncGroup
    );

    FMOD::ChannelGroup* masterGroup = nullptr;
    if( m_syncGroup && system->getMasterChannelGroup( &masterGroup ) == FMOD_OK && masterGroup )
    {
        masterGroup->addGroup( m_syncGroup );
    }

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
    Reset();
}


AudioPack::AudioPack( AudioPack&& other ) noexcept
{
    *this = std::move( other );
}


AudioPack& AudioPack::operator=( AudioPack&& other ) noexcept
{
    if( this == &other )
    {
        return *this;
    }

    Reset();

    m_trackData = other.m_trackData;
    m_sounds = std::move( other.m_sounds );
    m_drumTracks = std::move( other.m_drumTracks );
    m_syncGroup = other.m_syncGroup;

    other.m_trackData = nullptr;
    other.m_syncGroup = nullptr;

    return *this;
}


void AudioPack::Reset()
{
    Stop();
    m_sounds.clear();
    m_drumTracks.clear();

    if( m_syncGroup )
    {
        m_syncGroup->release();
        m_syncGroup = nullptr;
    }

    m_trackData = nullptr;
}


void AudioPack::Play()
{
    if( !IsReady() || !m_syncGroup )
        return;

    unsigned long long groupClock = 0;
    unsigned long long parentClock = 0;
    m_syncGroup->getDSPClock( &groupClock, &parentClock );

    // Add a small buffer so playback is not in the past when we set the delay.
    unsigned long long startDelay = parentClock + 2048;

    // 2. Play each sound in paused mode, assign to channel group, and schedule
    for( auto& sound : m_sounds )
    {
        // Let AudioSource::Play() create an FMOD::Channel if it's not created yet
        // Make sure your AudioSource::Play() calls:
        //   system->playSound(soundResource, nullptr, true, &ChannelHandle);
        // (i.e., "paused = true" in the call)

        sound.Play(false, true );  // This should set sound.ChannelHandle internally

        if( sound.ChannelHandle )
        {
            // Assign to our channel group
            sound.ChannelHandle->setChannelGroup( m_syncGroup );

            // Schedule the exact start time
            // First param = DSP clock to start, second param = DSP clock to stop (0 = no stop)
            sound.ChannelHandle->setDelay( startDelay, 0, false );

            // Finally unpause it so it is ready to go at that DSP time.
            sound.ChannelHandle->setPaused( false );
        }
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


unsigned int AudioPack::GetPositionMs() const
{
    return m_sounds[0].GetPositionMs();
}


unsigned int AudioPack::GetLength() const
{
    return m_sounds[0].GetLength();
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
    Path drumsPath(
        Path( m_trackData->m_trackSourcePath ).GetDirectoryString() +
        inFileName
    );

    if( !drumsPath.Exists )
    {
        return false;
    }

    SharedPtr<Sound> soundResource =
        ResourceCache::GetInstance().Get<Sound>(
            drumsPath,
            GetEngine().AudioThread->GetSystem(),
            SoundFlags::NonBlocking |
            SoundFlags::CreateStream
        );

    const size_t soundIndex = m_sounds.size();

    AudioSource& audioSource = m_sounds.emplace_back( drumsPath.FullPath );

    audioSource.SoundInstance = soundResource;

    if( !soundResource )
    {
        YIKES_FMT(
            "Failed to load sound: %s",
            audioSource.FilePath.GetLocalPathString().c_str()
        );

        audioSource.IsInitialized = true;
    }

    if( isDrumTrack )
    {
        m_drumTracks.push_back( soundIndex );
    }

    return true;
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

#endif
