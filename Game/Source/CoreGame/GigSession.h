#pragma once
#include "Singleton.h"
#include <string>
#include <vector>

struct ProgressionGig;
class PlayerProfile;

// A gig being played (Docs/Hideout-and-Progression.md → Gigs): its setlist, song by song, at the
// gig's venue. Each song's best accuracy this gig counts (Retry replaces it); when the last song
// is done, the set's average decides whether the gig is completed. Leaving mid-set abandons it.
class GigSession
{
    ME_SINGLETON_DEFINITION( GigSession );

public:
    GigSession() = default;

    // Starts the gig with these songs (TrackDatabase indices) and forces its venue. False when the
    // setlist is empty.
    bool Begin( const ProgressionGig& inGig, const std::vector<int>& inSetlist );
    // Loads the gameplay scene with the current song. False when there is none.
    bool LaunchCurrent() const;
    // Moves to the next song and launches it. False after the last one.
    bool LaunchNext();
    // Abandons or closes the gig: no venue is forced any more.
    void End();

    bool IsActive() const { return m_active; }
    const std::string& GigId() const { return m_gigId; }
    const std::string& GigName() const { return m_gigName; }
    int SongIndex() const { return m_song; }
    int SongCount() const { return static_cast<int>( m_setlist.size() ); }
    int CurrentTrack() const;
    bool IsLastSong() const { return m_song + 1 >= SongCount(); }

    // The song just played: keeps its best accuracy this gig. Returns true when that finished the
    // set (the last song, every song played).
    bool RecordSong( int inTrackIndex, double inAccuracy );
    bool SetDone() const;
    double AverageAccuracy() const;
    double PassAccuracy() const { return m_passAccuracy; }
    bool Passed() const { return SetDone() && AverageAccuracy() >= m_passAccuracy; }
    // Marks the gig completed in the profile when the set passed. True the first time.
    bool Complete( PlayerProfile& ioProfile ) const;

private:
    bool m_active = false;
    std::string m_gigId;
    std::string m_gigName;
    std::vector<int> m_setlist;
    std::vector<double> m_accuracy;   // per song, -1 for not played
    int m_song = 0;
    double m_passAccuracy = 70.0;
};
