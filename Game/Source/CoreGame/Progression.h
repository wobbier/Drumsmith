#pragma once
#include "Singleton.h"
#include "JSON.h"
#include <map>
#include <string>
#include <vector>

class PlayerProfile;
class TrackData;

// The zero-to-hero journey (Docs/Hideout-and-Progression.md), as data in
// Assets/Progression/Progression.json: the hideout's rooms, the gigs that move the player from one
// to the next, the lesson ladder, milestones, and the items and venues they unlock. Library songs
// are never locked; free play only ever loses venues it hasn't earned yet.
//
// Everything is decided from PlayerProfile: Evaluate turns what the player has done into unlocks
// (kept in PlayerProfile::UnlockedItems with a kind prefix, so a new one is noticed once).

// What has to be true. Every field that is set must hold; an empty requirement always holds.
struct ProgressionRequirement
{
    int Tier = 0;                           // the hideout's tier at least this
    std::vector<std::string> Gigs;          // these gigs completed
    std::vector<std::string> LessonSteps;   // every lesson of these ladder steps passed
    int LessonsPassed = 0;
    int SongsPlayed = 0;                    // different songs finished at least once
    int FullCombos = 0;                     // different songs full-comboed
    int SongsAtAccuracy = 0;                // different songs with a best accuracy of...
    double Accuracy = 0.0;                  // ...at least this

    bool Empty() const;
};

// A room of the hideout. The first needs nothing; each one after it is moved into when its
// requirement holds, and the player never moves back down.
struct ProgressionTier
{
    std::string Id;
    std::string Name;
    std::string Description;
    std::string Scene;          // the room's .lvl
    ProgressionRequirement Requires;
    std::vector<std::string> Rewards;   // item ids given on moving in
};

// A short set at a venue. Its songs are picked from the player's library by the rules (or listed
// by song folder), the same ones every time for a given library.
struct ProgressionGig
{
    std::string Id;
    std::string Name;
    std::string Description;
    std::string Venue;          // a registry id ("Backyard") or a room name ("Club")
    int Songs = 3;
    double MinNotesPerSecond = 0.0;
    double MaxNotesPerSecond = 1000.0;
    std::vector<std::string> SongKeys;  // song folders to use first, when the player has them
    double PassAccuracy = 70.0;         // the set's average accuracy to complete it
    ProgressionRequirement Requires;
    std::vector<std::string> Rewards;
};

// A rung of the lesson ladder: a handful of lessons that open together once the step before is passed.
struct ProgressionLessonStep
{
    std::string Id;
    std::string Name;
    std::vector<std::string> Lessons;   // PracticeLesson ids
    ProgressionRequirement Requires;    // to open the step
    std::vector<std::string> Rewards;   // given when every lesson in it has passed
};

struct ProgressionMilestone
{
    std::string Id;
    std::string Name;
    std::string Description;
    ProgressionRequirement Requires;
    std::vector<std::string> Rewards;
};

// Something for the hideout: shown at the room's slot of that name once unlocked (Phase 2).
struct ProgressionItem
{
    std::string Id;
    std::string Name;
    std::string Description;
    std::string Slot;
};

// A venue free play may only use once its requirement holds. Venues with no gate are always open.
struct ProgressionVenue
{
    std::string Id;             // as ProgressionGig::Venue
    std::string Name;
    ProgressionRequirement Requires;
};

// A groove a song plays (LessonPatternIndex): a player who has finished the song gets the lesson
// opened, whatever the ladder says.
struct ProgressionSongLesson
{
    std::string Lesson;         // PracticeLesson::Id
    std::string LessonName;
    std::string SongName;
};

// One thing a call to Evaluate unlocked.
struct ProgressionUnlock
{
    std::string Kind;           // "tier", "item", "venue", "step", "milestone", "lessons"
    std::string Id;
    std::string Text;           // for the player: "Moved into the Garage", "Unlocked: Practice pad"
};

class Progression
{
    ME_SINGLETON_DEFINITION( Progression );

public:
    static constexpr const char* kFile = "Assets/Progression/Progression.json";

    // Loads kFile; --unlock-all opens every lesson and venue (the profile is left alone).
    Progression();
    // Empty, for tests (then Load).
    explicit Progression( const json& inRoot );

    void Load( const json& inRoot );

    const std::vector<ProgressionTier>& Tiers() const { return m_tiers; }
    const std::vector<ProgressionGig>& Gigs() const { return m_gigs; }
    const std::vector<ProgressionLessonStep>& LessonSteps() const { return m_steps; }
    const std::vector<ProgressionMilestone>& Milestones() const { return m_milestones; }
    const std::vector<ProgressionItem>& Items() const { return m_items; }

    const ProgressionGig* FindGig( const std::string& inId ) const;
    const ProgressionItem* FindItem( const std::string& inId ) const;
    const ProgressionTier* TierAt( int inTier ) const;

    bool Holds( const ProgressionRequirement& inRequirement, const PlayerProfile& inProfile ) const;
    // Whether every lesson in the step has passed.
    bool StepDone( const ProgressionLessonStep& inStep, const PlayerProfile& inProfile ) const;
    bool StepOpen( const ProgressionLessonStep& inStep, const PlayerProfile& inProfile ) const;
    // A lesson in no step is always open; one in a step opens with it.
    bool LessonOpen( const std::string& inLessonId, const PlayerProfile& inProfile ) const;
    // The step a lesson belongs to, or nullptr.
    const ProgressionLessonStep* StepOf( const std::string& inLessonId ) const;
    // A venue with no gate is open; ids compare in any case.
    bool VenueOpen( const std::string& inVenue, const PlayerProfile& inProfile ) const;
    bool GigOpen( const ProgressionGig& inGig, const PlayerProfile& inProfile ) const;

    // The gig's songs from inTracks (TrackDatabase's list) as indices into it: its SongKeys first,
    // then songs in its notes-per-second range, picked the same way every time for the same
    // library. Fewer than Songs when the library is too small; the range widens before that.
    std::vector<int> Setlist( const ProgressionGig& inGig, const std::vector<TrackData>& inTracks ) const;
    static double NotesPerSecond( const TrackData& inTrack );

    // What a requirement still asks of the player, in words with progress ("play Club Night",
    // "pass Rudiments II (1 of 3 lessons)", "10 songs played (4 so far)"), joined by "and";
    // empty when it holds.
    std::string Describe( const ProgressionRequirement& inRequirement, const PlayerProfile& inProfile ) const;
    // How an item is got: "Comes with the Basement", "Play Backyard Party", "Pass Rudiments I on
    // the practice pad (1 of 2 lessons)", "Ten songs played (4 of 10)". Empty for no such item.
    std::string HowToUnlock( const std::string& inItemId, const PlayerProfile& inProfile ) const;

    // Moves the hideout up, grants rewards and records new unlocks in the profile until nothing
    // more changes. Returns what was new; their texts are also queued on the profile's Notices.
    // Doesn't save the profile.
    std::vector<ProgressionUnlock> Evaluate( PlayerProfile& ioProfile ) const;

    bool UnlockAll = false;
    // The grooves each song plays, by song key (TrackDatabase::FavoriteKey); LessonPatternIndex
    // fills it once it has read the library. A song in the profile opens its lessons.
    std::map<std::string, std::vector<ProgressionSongLesson>> SongLessons;

private:
    std::vector<ProgressionTier> m_tiers;
    std::vector<ProgressionGig> m_gigs;
    std::vector<ProgressionLessonStep> m_steps;
    std::vector<ProgressionMilestone> m_milestones;
    std::vector<ProgressionItem> m_items;
    std::vector<ProgressionVenue> m_venues;
};
