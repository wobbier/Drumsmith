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
    VenueRegistry::GigVenue() = inGig.Venue;
    return true;
}


bool GigSession::LaunchCurrent() const
{
    return m_active && TrackRadioUtils::LaunchTrack( CurrentTrack() );
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
    m_setlist.clear();
    m_accuracy.clear();
    m_song = 0;
    VenueRegistry::GigVenue().clear();
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
    return Passed() && ioProfile.CompletedGigs.insert( m_gigId ).second;
}
