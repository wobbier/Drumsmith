#include "GigSession.h"
#include "Config/PlayerProfile.h"
#include "CoreGame/Progression.h"
#include "UI/TrackRadioUtils.h"
#include "Venue/VenueRegistry.h"
#include <algorithm>
#include <numeric>

bool GigSession::Begin( const ProgressionGig& inGig, const std::vector<int>& inSetlist )
{
    End();
    if( inSetlist.empty() )
    {
        return false;
    }
    m_active = true;
    m_gigId = inGig.Id;
    m_gigName = inGig.Name;
    m_setlist = inSetlist;
    m_accuracy.assign( inSetlist.size(), -1.0 );
    m_song = 0;
    m_passAccuracy = inGig.PassAccuracy;
    m_setVenue = inGig.Venue;
    VenueRegistry::GigVenue() = inGig.Venue;
    return true;
}


bool GigSession::BeginStory( const ProgressionStorySet& inSet, const std::vector<int>& inSetlist, const PlayerProfile& inProfile )
{
    End();
    if( inSetlist.empty() || inSetlist.size() != inSet.Songs.size() || std::find( inSetlist.begin(), inSetlist.end(), -1 ) != inSetlist.end() )
    {
        return false;
    }
    m_active = true;
    m_story = true;
    m_oneSitting = inSet.OneSitting;
    m_continuous = inSet.Continuous;
    m_storySet = inSet;
    m_gigId = inSet.Id;
    m_gigName = inSet.Name;
    m_setlist = inSetlist;
    m_accuracy.assign( inSetlist.size(), -1.0 );
    const auto record = inProfile.Story.find( inSet.Id );
    if( !m_oneSitting && record != inProfile.Story.end() )
    {
        for( size_t i = 0; i < m_accuracy.size() && i < record->second.Banked.size(); ++i )
        {
            m_accuracy[i] = record->second.Banked[i];
        }
    }
    // The first song not banked (Progression::StoryNextSong); from the top once all are.
    const auto next = std::find_if( m_accuracy.begin(), m_accuracy.end(), []( double inAccuracy ) { return inAccuracy < 0.0; } );
    m_song = next == m_accuracy.end() ? 0 : static_cast<int>( next - m_accuracy.begin() );
    m_passAccuracy = inSet.PassAccuracy;
    m_setVenue = inSet.Venue;
    ApplyVenue();
    return true;
}


bool GigSession::LaunchCurrent() const
{
    if( !m_active )
    {
        return false;
    }
    if( m_story )
    {
        StageStory( m_storySet, m_song );
        ApplyVenue();
    }
    return TrackRadioUtils::LaunchTrack( CurrentTrack() );
}


int GigSession::Advance()
{
    if( !IsContinuous() || IsLastSong() )
    {
        return -1;
    }
    ++m_song;
    StageStory( m_storySet, m_song );
    ApplyVenue();
    return CurrentTrack();
}


const ProgressionStorySong* GigSession::CurrentStorySong() const
{
    return IsStory() && m_song >= 0 && m_song < static_cast<int>( m_storySet.Songs.size() ) ? &m_storySet.Songs[m_song] : nullptr;
}


void GigSession::ApplyVenue() const
{
    const ProgressionStorySong* song = CurrentStorySong();
    VenueRegistry::GigVenue() = song && !song->Venue.empty() ? song->Venue : m_setVenue;
}


void GigSession::StageStory( const ProgressionStorySet& inSet, int inSong )
{
    VenueRegistry::Story() = MakeStage( inSet, inSong );
}


VenueRegistry::StoryStage GigSession::MakeStage( const ProgressionStorySet& inSet, int inSong )
{
    VenueRegistry::StoryStage stage;
    if( inSong < 0 || inSong >= static_cast<int>( inSet.Songs.size() ) )
    {
        return stage;
    }
    stage.Set = inSet.Id;
    stage.Song = inSong;
    // The set is played in order, so everything before this song has happened. The band's own
    // state (band_ flags: VenueShow::UpdateStoryBand) is each song's to set.
    const auto carry = [&stage]( const std::vector<std::string>& inFlags ) {
        for( const std::string& flag : inFlags )
        {
            if( flag.rfind( "band_", 0 ) != 0 )
            {
                stage.Flags.insert( flag );
            }
        }
    };
    for( int i = 0; i < inSong; ++i )
    {
        const ProgressionStorySong& before = inSet.Songs[i];
        carry( before.Flags );
        for( const ProgressionStorySong::Moment& moment : before.Moments )
        {
            carry( moment.Flags );
        }
    }
    const ProgressionStorySong& song = inSet.Songs[inSong];
    for( const std::string& flag : song.Flags )
    {
        if( stage.Flags.count( flag ) == 0 )
        {
            stage.AtCue.insert( flag );
        }
    }
    stage.Cue = song.Cue;
    for( const ProgressionStorySong::Moment& moment : song.Moments )
    {
        VenueRegistry::StoryStage::Moment staged;
        staged.Cue = moment.Cue;
        staged.Caption = moment.Caption;
        staged.CaptionSeconds = moment.CaptionSeconds;
        for( const std::string& flag : moment.Flags )
        {
            if( stage.Flags.count( flag ) == 0 )
            {
                staged.Flags.insert( flag );
            }
        }
        if( !staged.Flags.empty() || !staged.Caption.empty() )
        {
            stage.Moments.push_back( std::move( staged ) );
        }
    }
    return stage;
}


bool GigSession::JumpTo( int inSong )
{
    if( !m_active || inSong < 0 || inSong >= SongCount() )
    {
        return false;
    }
    m_song = inSong;
    return true;
}


bool GigSession::LaunchNext()
{
    if( !m_active || IsLastSong() )
    {
        return false;
    }
    ++m_song;
    return LaunchCurrent();
}


void GigSession::End()
{
    m_active = false;
    m_story = false;
    m_oneSitting = false;
    m_continuous = false;
    m_setVenue.clear();
    m_storySet = ProgressionStorySet();
    m_setlist.clear();
    m_accuracy.clear();
    m_song = 0;
    VenueRegistry::GigVenue().clear();
    VenueRegistry::Story() = VenueRegistry::StoryStage();
}


int GigSession::CurrentTrack() const
{
    return m_active && m_song >= 0 && m_song < SongCount() ? m_setlist[m_song] : -1;
}


bool GigSession::RecordSong( int inTrackIndex, double inAccuracy )
{
    if( !m_active || inTrackIndex != CurrentTrack() )
    {
        return false;
    }
    m_accuracy[m_song] = std::max( m_accuracy[m_song], inAccuracy );
    return SetDone();
}


void GigSession::Bank( PlayerProfile& ioProfile ) const
{
    if( !IsStory() || m_oneSitting || m_song < 0 || m_song >= SongCount() || m_accuracy[m_song] < 0.0 )
    {
        return;
    }
    std::vector<double>& banked = ioProfile.Story[m_gigId].Banked;
    if( banked.size() < m_accuracy.size() )
    {
        banked.resize( m_accuracy.size(), -1.0 );
    }
    banked[m_song] = std::max( banked[m_song], m_accuracy[m_song] );
}


bool GigSession::SetDone() const
{
    return m_active && !m_accuracy.empty() && std::all_of( m_accuracy.begin(), m_accuracy.end(), []( double inAccuracy ) { return inAccuracy >= 0.0; } );
}


double GigSession::AverageAccuracy() const
{
    if( m_accuracy.empty() )
    {
        return 0.0;
    }
    double sum = 0.0;
    for( double accuracy : m_accuracy )
    {
        sum += std::max( 0.0, accuracy );
    }
    return sum / static_cast<double>( m_accuracy.size() );
}


bool GigSession::Complete( PlayerProfile& ioProfile ) const
{
    if( !Passed() )
    {
        return false;
    }
    if( m_story )
    {
        PlayerProfile::StoryRecord& record = ioProfile.Story[m_gigId];
        const bool first = !record.Passed;
        record.Passed = true;
        return first;
    }
    return ioProfile.CompletedGigs.insert( m_gigId ).second;
}
