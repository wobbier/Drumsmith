#include "AudioPack.h"

#include <algorithm>
#include <cmath>

#if USING( ME_FMOD )

#include "Cores/AudioCore.h"
#include "Engine/Engine.h"
#include "Resources/SoundResource.h"
#include "Resource/ResourceCache.h"
#include <fmod.hpp>
#include "Pointers.h"
#include <array>
#include <utility>

namespace
{
    // Long enough to smooth the step at a start or stop, short enough not to be heard as a fade.
    constexpr float kFadeInSeconds = 0.02f;

    unsigned long long MixerSamples( float inSeconds )
    {
        int rate = 48000;
        GetEngine().AudioThread->GetSystem()->getSoftwareFormat( &rate, nullptr, nullptr );
        return static_cast<unsigned long long>( static_cast<float>( rate ) * inSeconds );
    }
}

AudioPack::AudioPack( TrackData& inTrackData )
{
    // The stems are resolved here and nothing keeps a pointer to inTrackData: it lives in the
    // TrackDatabase vector, which a reload (e.g. after a DLC download) reallocates under a live pack.
    const std::string sourceDir = Path( inTrackData.m_trackSourcePath ).GetDirectoryString();
    // Create the channel group for these stems:
    FMOD::System* system = GetEngine().AudioThread->GetSystem();
    system->createChannelGroup(
        inTrackData.m_trackName.c_str(),
        &m_syncGroup
    );

    FMOD::ChannelGroup* masterGroup = nullptr;
    if( m_syncGroup && system->getMasterChannelGroup( &masterGroup ) == FMOD_OK && masterGroup )
    {
        masterGroup->addGroup( m_syncGroup );
    }

    // I should track all the needed files in the track data
    LoadStem( sourceDir, inTrackData.m_trackFileName.c_str() );
    LoadStem( sourceDir, "crowd.ogg" );
    LoadStem( sourceDir, "drums.ogg", true );
    LoadStem( sourceDir, "drums_1.ogg", true );
    LoadStem( sourceDir, "drums_2.ogg", true );
    LoadStem( sourceDir, "drums_3.ogg", true );
    LoadStem( sourceDir, "drums_4.ogg", true );
    LoadStem( sourceDir, "guitar.ogg" );
    LoadStem( sourceDir, "vocals.ogg" );
    LoadStem( sourceDir, "rhythm.ogg" );
    LoadStem( sourceDir, "keys.ogg" );
    //GetEngine().AudioThread->GetSystem()->createChannelGroup( inTrackData.m_trackName.c_str(), &syncGroup );
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

    m_sounds = std::move( other.m_sounds );
    m_drumTracks = std::move( other.m_drumTracks );
    m_metronome = other.m_metronome;
    other.m_metronome = -1;
    m_syncGroup = other.m_syncGroup;
    m_speakerEq = other.m_speakerEq;
    m_speakerDrive = other.m_speakerDrive;
    m_metering = other.m_metering;

    other.m_syncGroup = nullptr;
    other.m_metering = false;
    other.m_speakerEq = nullptr;
    other.m_speakerDrive = nullptr;

    return *this;
}


void AudioPack::Reset()
{
    Stop();
    m_sounds.clear();
    m_drumTracks.clear();
    m_metronome = -1;

    for( FMOD::DSP** dsp : { &m_speakerEq, &m_speakerDrive } )
    {
        if( *dsp )
        {
            if( m_syncGroup )
            {
                m_syncGroup->removeDSP( *dsp );
            }
            ( *dsp )->release();
            *dsp = nullptr;
        }
    }
    if( m_syncGroup )
    {
        m_syncGroup->release();
        m_syncGroup = nullptr;
    }
    m_metering = false;

}


float AudioPack::GetLevel()
{
#if USING( ME_FMOD )
    if( !m_syncGroup )
    {
        return 0.f;
    }
    FMOD::DSP* head = nullptr;
    if( m_syncGroup->getDSP( FMOD_CHANNELCONTROL_DSP_HEAD, &head ) != FMOD_OK || !head )
    {
        return 0.f;
    }
    if( !m_metering )
    {
        head->setMeteringEnabled( false, true );
        m_metering = true;
    }
    FMOD_DSP_METERING_INFO info = {};
    if( head->getMeteringInfo( nullptr, &info ) != FMOD_OK || info.numchannels <= 0 )
    {
        return 0.f;
    }
    float sum = 0.f;
    const int channels = std::min<int>( info.numchannels, 32 );
    for( int channel = 0; channel < channels; ++channel )
    {
        sum += info.rmslevel[channel];
    }
    return sum / static_cast<float>( channels );
#else
    return 0.f;
#endif
}


void AudioPack::SetSpeaker( const RoomSpeaker& inSpeaker, float inOpen, float inPan, float inLevel )
{
    if( !m_syncGroup )
    {
        return;
    }
    const RoomSpeaker::Mix mix = inSpeaker.Resolve( inOpen, inPan, inLevel );
    if( mix.Off && !m_speakerEq )
    {
        return;
    }
    FMOD::System* system = GetEngine().AudioThread->GetSystem();
    if( !m_speakerEq )
    {
        if( system->createDSPByType( FMOD_DSP_TYPE_MULTIBAND_EQ, &m_speakerEq ) != FMOD_OK || !m_speakerEq )
        {
            m_speakerEq = nullptr;
            return;
        }
        m_speakerEq->setParameterInt( FMOD_DSP_MULTIBAND_EQ_A_FILTER, FMOD_DSP_MULTIBAND_EQ_FILTER_HIGHPASS_24DB );
        m_speakerEq->setParameterInt( FMOD_DSP_MULTIBAND_EQ_B_FILTER, FMOD_DSP_MULTIBAND_EQ_FILTER_LOWPASS_24DB );
        m_speakerEq->setParameterInt( FMOD_DSP_MULTIBAND_EQ_C_FILTER, FMOD_DSP_MULTIBAND_EQ_FILTER_PEAKING );
        m_speakerEq->setParameterFloat( FMOD_DSP_MULTIBAND_EQ_C_Q, 1.f );
        m_syncGroup->addDSP( FMOD_CHANNELCONTROL_DSP_TAIL, m_speakerEq );
        // Also at the tail, so it comes first: the little amp breaks up, then the box shapes it.
        if( system->createDSPByType( FMOD_DSP_TYPE_DISTORTION, &m_speakerDrive ) == FMOD_OK && m_speakerDrive )
        {
            m_syncGroup->addDSP( FMOD_CHANNELCONTROL_DSP_TAIL, m_speakerDrive );
        }
        else
        {
            m_speakerDrive = nullptr;
        }
    }
    m_speakerEq->setParameterFloat( FMOD_DSP_MULTIBAND_EQ_A_FREQUENCY, mix.HighPass );
    m_speakerEq->setParameterFloat( FMOD_DSP_MULTIBAND_EQ_B_FREQUENCY, mix.LowPass );
    m_speakerEq->setParameterFloat( FMOD_DSP_MULTIBAND_EQ_C_FREQUENCY, mix.HonkAt );
    m_speakerEq->setParameterFloat( FMOD_DSP_MULTIBAND_EQ_C_GAIN, mix.Honk );
    m_speakerEq->setBypass( mix.HighPass <= 20.5f && mix.LowPass >= 19990.f && std::abs( mix.Honk ) < 0.05f );
    if( m_speakerDrive )
    {
        m_speakerDrive->setParameterFloat( FMOD_DSP_DISTORTION_LEVEL, mix.Drive );
        m_speakerDrive->setBypass( mix.Drive <= 0.f );
    }
    // The stereo pair through the group's matrix (width and pan); any other speakers of the mix
    // pass as they are. The group mixes at the output's speaker mode, so the matrix is that wide.
    int channels = 2;
    int rawSpeakers = 0;
    FMOD_SPEAKERMODE mode = FMOD_SPEAKERMODE_STEREO;
    if( system->getSoftwareFormat( nullptr, &mode, &rawSpeakers ) == FMOD_OK && system->getSpeakerModeChannels( mode, &channels ) != FMOD_OK )
    {
        channels = rawSpeakers;
    }
    if( channels >= 2 && channels <= FMOD_MAX_CHANNEL_WIDTH )
    {
        std::array<float, FMOD_MAX_CHANNEL_WIDTH * FMOD_MAX_CHANNEL_WIDTH> matrix{};
        for( int channel = 0; channel < channels; ++channel )
        {
            matrix[channel * channels + channel] = 1.f;
        }
        matrix[0] = mix.Matrix[0];
        matrix[1] = mix.Matrix[1];
        matrix[channels] = mix.Matrix[2];
        matrix[channels + 1] = mix.Matrix[3];
        m_syncGroup->setMixMatrix( matrix.data(), channels, channels );
    }
    m_syncGroup->setVolume( mix.Volume );
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
    FadeInAt( startDelay );

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


bool AudioPack::AddMetronome( const std::string& inFile )
{
    if( m_metronome >= 0 || m_sounds.empty() )
    {
        return m_metronome >= 0;
    }
    if( !LoadStem( "", inFile.c_str() ) )
    {
        return false;
    }
    m_metronome = static_cast<int>( m_sounds.size() ) - 1;
    return true;
}


bool AudioPack::IsMetronomePlaying() const
{
    bool playing = false;
    return m_metronome >= 0 && m_sounds[m_metronome].ChannelHandle && m_sounds[m_metronome].ChannelHandle->isPlaying( &playing ) == FMOD_OK && playing;
}


void AudioPack::SetMetronomeVolume( float inVolumePercent )
{
    if( m_metronome >= 0 )
    {
        m_sounds[m_metronome].SetVolume( inVolumePercent );
    }
}


void AudioPack::SetPlaybackSpeed( float inSpeed )
{
    // On the group, so every stem changes on one mixer tick and stays in step.
    if( m_syncGroup )
    {
        m_syncGroup->setPitch( std::max( inSpeed, 0.01f ) );
        return;
    }
    for( auto& sound : m_sounds )
    {
        sound.SetPlaybackSpeed( inSpeed );
    }
}


float AudioPack::GetVolume()
{
    return m_sounds[0].GetVolume();
}


void AudioPack::Seek( float inSeekPercent, float inFadeInSeconds )
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
        // A stem added since the song started (the metronome, switched on mid-song) has no
        // channel yet: it gets one here, held like the rest, and starts with them.
        if( !sound.ChannelHandle && m_syncGroup && m_sounds[0].ChannelHandle && sound.IsLoaded() )
        {
            sound.Play( false, true );
            if( sound.ChannelHandle )
            {
                sound.ChannelHandle->setChannelGroup( m_syncGroup );
            }
        }
        if( sound.ChannelHandle )
        {
            sound.ChannelHandle->setPaused( true );
            sound.ChannelHandle->setPosition( std::min( target, sound.GetLength() ), FMOD_TIMEUNIT_MS );
        }
    }
    m_seekTargetMs = target;
    m_seekFadeSeconds = inFadeInSeconds;
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
    FadeInAt( start );
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


void AudioPack::FadeInAt( unsigned long long inGroupClock )
{
    if( !m_syncGroup )
    {
        return;
    }
    // Fade points run on the parent's clock; the stems' delays on this group's.
    unsigned long long groupClock = 0;
    unsigned long long parentClock = 0;
    if( m_syncGroup->getDSPClock( &groupClock, &parentClock ) != FMOD_OK )
    {
        return;
    }
    const unsigned long long from = parentClock + ( inGroupClock > groupClock ? inGroupClock - groupClock : 0 );
    m_syncGroup->removeFadePoints( parentClock, ~0ULL );
    m_syncGroup->addFadePoint( parentClock, 0.f );
    m_syncGroup->addFadePoint( from, 0.f );
    m_syncGroup->addFadePoint( from + MixerSamples( std::max( kFadeInSeconds, m_seekFadeSeconds ) ), 1.f );
}


void AudioPack::FadeOut( float inSeconds )
{
    m_seekPending = false;
    if( !m_syncGroup )
    {
        Stop();
        return;
    }
    unsigned long long parentClock = 0;
    if( m_syncGroup->getDSPClock( nullptr, &parentClock ) != FMOD_OK )
    {
        Stop();
        return;
    }
    const unsigned long long end = parentClock + MixerSamples( inSeconds );
    // Keep whatever level a fade-in had reached, rather than jumping back to full.
    float level = 1.f;
    unsigned int points = 0;
    if( m_syncGroup->getFadePoints( &points, nullptr, nullptr ) == FMOD_OK && points > 0 )
    {
        std::vector<unsigned long long> clocks( points );
        std::vector<float> volumes( points );
        m_syncGroup->getFadePoints( &points, clocks.data(), volumes.data() );
        level = 0.f;
        for( unsigned int i = 0; i < points; ++i )
        {
            if( clocks[i] <= parentClock ) level = volumes[i];
        }
    }
    m_syncGroup->removeFadePoints( parentClock, ~0ULL );
    m_syncGroup->addFadePoint( parentClock, level );
    m_syncGroup->addFadePoint( end, 0.f );
    m_syncGroup->setDelay( 0, end, true );
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
    if( m_sounds.empty() )
    {
        return 0;
    }
    if( IsSeeking() )
    {
        return m_seekTargetMs;
    }
    return m_sounds[0].GetPositionMs();
}


unsigned int AudioPack::GetLength() const
{
    // A pack with nothing loaded (the radio before its first song) has no length.
    if( m_sounds.empty() )
    {
        return 0;
    }
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


bool AudioPack::LoadStem( const std::string& inDirectory, const char* inFileName, bool isDrumTrack )
{
    Path drumsPath( inDirectory + inFileName );

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

#else

#include <utility>

// No FMOD (headless server builds): a pack that never loads and plays nothing, so the code
// that holds one links and treats the song as not ready.

AudioPack::AudioPack( TrackData& inTrackData )
{
    (void)inTrackData;
}


AudioPack::~AudioPack()
{
}


AudioPack::AudioPack( AudioPack&& other ) noexcept
    : m_sounds( std::move( other.m_sounds ) )
    , m_drumTracks( std::move( other.m_drumTracks ) )
    , m_metronome( std::exchange( other.m_metronome, -1 ) )
{
}


AudioPack& AudioPack::operator=( AudioPack&& other ) noexcept
{
    m_sounds = std::move( other.m_sounds );
    m_drumTracks = std::move( other.m_drumTracks );
    m_metronome = std::exchange( other.m_metronome, -1 );
    return *this;
}


void AudioPack::Play()
{
}


void AudioPack::Pause()
{
}


void AudioPack::Resume()
{
}


void AudioPack::Stop()
{
}


void AudioPack::SetVolume( float )
{
}


void AudioPack::SetDrumVolume( float )
{
}


bool AudioPack::AddMetronome( const std::string& )
{
    return false;
}


bool AudioPack::IsMetronomePlaying() const
{
    return false;
}


void AudioPack::SetMetronomeVolume( float )
{
}


void AudioPack::SetPlaybackSpeed( float )
{
}


float AudioPack::GetVolume()
{
    return 0.f;
}


void AudioPack::Seek( float, float )
{
}


void AudioPack::Update()
{
}


bool AudioPack::IsSeeking() const
{
    return false;
}


unsigned int AudioPack::GetPositionMs() const
{
    return 0;
}


unsigned int AudioPack::GetLength() const
{
    return 0;
}


unsigned int AudioPack::StemSpreadMs() const
{
    return 0;
}


void AudioPack::FadeOut( float )
{
}


bool AudioPack::IsReady() const
{
    return false;
}


bool AudioPack::IsPlaying() const
{
    return false;
}


void AudioPack::SetSpeaker( float, float, float )
{
}


float AudioPack::GetLevel()
{
    return 0.f;
}

#endif


namespace
{
    // From inFrom to inTo on a log scale (frequencies), inT 0 to 1.
    float LogLerp( float inFrom, float inTo, float inT )
    {
        return inFrom * std::pow( inTo / inFrom, inT );
    }
}


RoomSpeaker::Mix RoomSpeaker::Resolve( float inOpen, float inPan, float inLevel ) const
{
    const float open = std::clamp( inOpen, 0.f, 1.f );
    const float pan = std::clamp( inPan, -1.f, 1.f );
    const float level = std::clamp( inLevel, 0.f, 1.f );
    Mix mix;
    // Up close, the speaker's own band. From across the room both ends go further, four tenths of
    // the way from its band toward a small speaker's 300 Hz to 3 kHz.
    const float low = std::clamp( LowCut, 20.f, 20000.f );
    const float high = std::clamp( HighCut, low, 20000.f );
    const float farLow = std::max( low, LogLerp( 300.f, low, 0.6f ) );
    const float farHigh = std::min( high, LogLerp( 3000.f, high, 0.6f ) );
    mix.HighPass = LogLerp( farLow, low, open );
    mix.LowPass = LogLerp( farHigh, high, open );
    mix.Honk = std::clamp( Honk, -24.f, 24.f );
    mix.HonkAt = std::clamp( HonkAt, 20.f, 20000.f );
    mix.Drive = std::clamp( Drive, 0.f, 0.9f );
    // Its width up close, the square of that across the room: two cones close together blur into
    // one from further off, a wide pair stays wide.
    const float width = std::clamp( Width, 0.f, 1.f );
    const float spread = width * ( width + ( 1.f - width ) * open );
    const float same = 0.5f * ( 1.f + spread );
    const float cross = 0.5f * ( 1.f - spread );
    // Panned by balance: the side away from it quieter, neither louder than it was.
    const float left = std::min( 1.f, std::sqrt( 1.f - pan ) );
    const float right = std::min( 1.f, std::sqrt( 1.f + pan ) );
    mix.Matrix[0] = left * same;
    mix.Matrix[1] = left * cross;
    mix.Matrix[2] = right * cross;
    mix.Matrix[3] = right * same;
    // FMOD's distortion is a waveshaper that lifts quiet passages by 1 + k (loud ones by less, as
    // they saturate); half of that comes back off, so a cheap speaker isn't louder for it.
    const float k = 2.f * mix.Drive / ( 1.f - mix.Drive );
    mix.Volume = level / std::sqrt( 1.f + k );
    mix.Off = mix.HighPass <= 20.5f && mix.LowPass >= 19990.f && std::abs( mix.Honk ) < 0.05f && mix.Drive <= 0.f && spread >= 0.999f
        && std::abs( pan ) < 0.001f && level >= 0.999f;
    return mix;
}
