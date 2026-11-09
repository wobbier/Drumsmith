#include "AudioPack.h"

#if USING( ME_FMOD )

#include "Cores/AudioCore.h"
#include "Engine/Engine.h"
#include "Resources/SoundResource.h"
#include "Resource/ResourceCache.h"
#include <fmod.hpp>
#include "Pointers.h"
#include <algorithm>
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

    // The stems' delays count on their parent's clock: this group's.
    unsigned long long groupClock = 0;
    m_syncGroup->getDSPClock( &groupClock, nullptr );

    // Add a small buffer so playback is not in the past when we set the delay.
    unsigned long long startDelay = groupClock + 2048;

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
    // The whole group stops on one mixer tick; pausing stem by stem could split them a block.
    if( m_syncGroup )
    {
        m_syncGroup->setPaused( true );
        return;
    }
    for( auto& sound : m_sounds )
    {
        sound.Pause();
    }
}


void AudioPack::Resume()
{
    if( m_syncGroup )
    {
        m_syncGroup->setPaused( false );
        return;
    }
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
    if( m_sounds.empty() )
    {
        return;
    }
    // Hold every stem, move each to the new position, and start none until all have got there
    // (Update): a stream's seek finishes on FMOD's loader thread, each stem in its own time, and
    // unpausing them straight away started each one whenever its seek landed, out of step.
    const unsigned int target = static_cast<unsigned int>( static_cast<float>( m_sounds[0].GetLength() ) * std::clamp( inSeekPercent, 0.f, 1.f ) );
    for( auto& sound : m_sounds )
    {
        if( sound.ChannelHandle )
        {
            sound.ChannelHandle->setPaused( true );
            sound.ChannelHandle->setPosition( std::min( target, sound.GetLength() ), FMOD_TIMEUNIT_MS );
        }
    }
    m_seekTargetMs = target;
    m_seekPending = true;
    m_seekStartClock = 0;
    m_seekStarted = std::chrono::steady_clock::now();
    Update();
}


bool AudioPack::StemsSeeked() const
{
    for( const auto& sound : m_sounds )
    {
        if( !sound.SoundInstance || !sound.SoundInstance->Handle || !sound.ChannelHandle )
        {
            continue;
        }
        FMOD_OPENSTATE state = FMOD_OPENSTATE_READY;
        if( sound.SoundInstance->Handle->getOpenState( &state, nullptr, nullptr, nullptr ) != FMOD_OK )
        {
            continue;
        }
        if( state == FMOD_OPENSTATE_SETPOSITION || state == FMOD_OPENSTATE_SEEKING || state == FMOD_OPENSTATE_BUFFERING || state == FMOD_OPENSTATE_LOADING )
        {
            return false;
        }
    }
    return true;
}


void AudioPack::Update()
{
    if( !m_seekPending )
    {
        return;
    }
    // Half a second is far longer than a seek takes; past it, start anyway rather than hang.
    const bool timedOut = std::chrono::steady_clock::now() - m_seekStarted > std::chrono::milliseconds( 500 );
    if( !StemsSeeked() && !timedOut )
    {
        return;
    }
    m_seekPending = false;
    // One start for all, a little ahead so none is already past it when it's set. The group's
    // clock stands still while the game has it paused, so this also holds through a pause.
    unsigned long long groupClock = 0;
    if( m_syncGroup )
    {
        m_syncGroup->getDSPClock( &groupClock, nullptr );
    }
    const unsigned long long start = groupClock + 2048;
    m_seekStartClock = m_syncGroup ? start : 0;
    for( auto& sound : m_sounds )
    {
        if( sound.ChannelHandle )
        {
            if( m_syncGroup )
            {
                sound.ChannelHandle->setDelay( start, 0, false );
            }
            sound.ChannelHandle->setPaused( false );
        }
    }
}


unsigned int AudioPack::StemSpreadMs() const
{
    unsigned int lowest = ~0u;
    unsigned int highest = 0;
    for( const auto& sound : m_sounds )
    {
        if( !sound.ChannelHandle )
        {
            continue;
        }
        unsigned int position = 0;
        bool playing = false;
        // Stems that ran out (a shorter crowd track) don't count.
        if( sound.ChannelHandle->isPlaying( &playing ) != FMOD_OK || !playing || sound.ChannelHandle->getPosition( &position, FMOD_TIMEUNIT_MS ) != FMOD_OK )
        {
            continue;
        }
        lowest = std::min( lowest, position );
        highest = std::max( highest, position );
    }
    return highest >= lowest ? highest - lowest : 0u;
}


bool AudioPack::IsSeeking() const
{
    if( m_seekPending )
    {
        return true;
    }
    if( m_seekStartClock == 0 || !m_syncGroup )
    {
        return false;
    }
    unsigned long long groupClock = 0;
    m_syncGroup->getDSPClock( &groupClock, nullptr );
    return groupClock < m_seekStartClock;
}


unsigned int AudioPack::GetPositionMs() const
{
    if( IsSeeking() )
    {
        return m_seekTargetMs;
    }
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
