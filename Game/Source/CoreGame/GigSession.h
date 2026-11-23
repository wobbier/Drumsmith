#pragma once
#include "Singleton.h"
#include "CoreGame/Progression.h"
#include "Venue/VenueRegistry.h"
#include <string>
#include <vector>

class PlayerProfile;

// A gig being played (Docs/Hideout-and-Progression.md → Gigs): its setlist, song by song, at the
// gig's venue. Each song's best accuracy this gig counts (Retry replaces it); when the last song
// is done, the set's average decides whether the gig is completed. Leaving mid-set abandons it.
//
// A story set (CoreGame/Progression.h) plays the same way, but each song is banked in the profile
// as it's played: the set starts at the first song not banked yet, the banked ones already
// counted, and leaving keeps what was banked. A OneSitting set banks nothing.
//
// A Continuous story set is one show: NoteHighwayCore plays each song's tail into the next song in
// the same scene (Advance), with no results screen until the last. A song may have a venue of its
// own (ProgressionStorySong::Venue), forced while it plays.
class GigSession
{
    ME_SINGLETON_DEFINITION( GigSession );

public:
    GigSession() = default;

    // Starts the gig with these songs (TrackDatabase indices) and forces its venue. False when the
    // setlist is empty.
    bool Begin( const ProgressionGig& inGig, const std::vector<int>& inSetlist );
    // Starts a story set from inSetlist (Progression::StorySetlist: one per song, none -1) at the
    // profile's next song, with its banked songs counted. False when a song is missing.
    bool BeginStory( const ProgressionStorySet& inSet, const std::vector<int>& inSetlist, const PlayerProfile& inProfile );
    // Loads the gameplay scene with the current song. False when there is none.
    bool LaunchCurrent() const;
    // Story mode's venue state for song inSong of inSet (VenueRegistry::Story): the flags of the
    // songs before it from the start, its own at its cue. A song out of range clears it.
    static void StageStory( const ProgressionStorySet& inSet, int inSong );
    // What StageStory stages: the flags set before inSong of inSet, and its own cue and moments.
    static VenueRegistry::StoryStage MakeStage( const ProgressionStorySet& inSet, int inSong );
    // Plays from song inSong instead (the debug menu's song buttons, --story-song). False when
    // there is no such song.
    bool JumpTo( int inSong );
    // Moves to the next song and launches it. False after the last one.
    bool LaunchNext();
    // A continuous show's hand-off: moves to the next song and stages it (its venue state and
    // venue) without loading anything; the caller plays it in place. Its track index, or -1 after
    // the last song or outside a continuous show.
    int Advance();
    // Abandons or closes the gig: no venue is forced any more.
    void End();

    bool IsActive() const { return m_active; }
    bool IsStory() const { return m_active && m_story; }
    bool IsOneSitting() const { return m_active && m_oneSitting; }
    bool IsContinuous() const { return m_active && m_continuous; }
    // The story song being played (its cues, venue and highway rule); null outside a story set.
    const ProgressionStorySong* CurrentStorySong() const;
    const std::string& GigId() const { return m_gigId; }
    const std::string& GigName() const { return m_gigName; }
    int SongIndex() const { return m_song; }
    int SongCount() const { return static_cast<int>( m_setlist.size() ); }
    int CurrentTrack() const;
    // The song after this one (a TrackDatabase index), -1 after the last.
    int NextTrack() const { return m_active && m_song + 1 < SongCount() ? m_setlist[m_song + 1] : -1; }
    bool IsLastSong() const { return m_song + 1 >= SongCount(); }

    // The song just played: keeps its best accuracy this gig. Returns true when that finished the
    // set (the last song, every song played).
    bool RecordSong( int inTrackIndex, double inAccuracy );
    // A story set: writes the current song's best into the profile (a OneSitting set, nothing).
    // Doesn't save the profile.
    void Bank( PlayerProfile& ioProfile ) const;
    bool SetDone() const;
    double AverageAccuracy() const;
    double PassAccuracy() const { return m_passAccuracy; }
    bool Passed() const { return SetDone() && AverageAccuracy() >= m_passAccuracy; }
    // Marks the gig (or story set) completed in the profile when the set passed. True the first time.
    bool Complete( PlayerProfile& ioProfile ) const;

private:
    // Forces the current song's venue: its own, else the set's.
    void ApplyVenue() const;

    bool m_active = false;
    bool m_story = false;
    bool m_oneSitting = false;
    bool m_continuous = false;
    std::string m_setVenue;
    // The story set being played (a copy: the session outlives a Progression reload).
    ProgressionStorySet m_storySet;
    std::string m_gigId;
    std::string m_gigName;
    std::vector<int> m_setlist;
    std::vector<double> m_accuracy;   // per song, -1 for not played
    int m_song = 0;
    double m_passAccuracy = 70.0;
};
