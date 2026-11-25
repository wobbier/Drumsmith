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
    std::vector<std::string> StorySets;     // these story sets passed
    std::vector<std::string> Members;       // these band seats filled ("bass", "guitar"...)

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

// A song of a story set: named by the recording, since the chart may not exist yet. It is found
// in the library by its Spotify link (a chart's "Links"), else by artist and title.
struct ProgressionStorySong
{
    // More of the venue's state landing at another point of the song: Cue is a cue name as the
    // song's own (VenueShow::StoryCueTime: "solo", "section:<name>", "at:0.4", "time:95",
    // "drums_in", "song_end"...).
    // Caption: a line shown on screen for CaptionSeconds from the moment (a character's line).
    struct Moment
    {
        std::string Cue;
        std::vector<std::string> Flags;
        std::string Caption;
        double CaptionSeconds = 4.0;
    };

    std::string Artist;
    std::string Title;
    std::string Spotify;
    std::vector<std::string> Flags;     // the venue's state once this song is done
    std::string Cue;                    // where in the song its own flags land ("first_chorus"...)
    std::vector<Moment> Moments;        // flags landing at their own cues, after the song too
    std::string Venue;                  // this song's venue; empty: the set's
    // A continuous show: the venue plays on at least this long after the song's last note before
    // the next song takes over, however short the recording's tail is (the wreck burning, the
    // bodies on the road). Its moments can land in it ("last_note+6"). 0: as the recording ends.
    double OutroSeconds = 0.0;
};

// A booking of story mode (Design/Story-Mode-Setlists.md): five songs at one venue, played in
// order. Each finished song is banked, so the set can be left and resumed; it passes when every
// song is banked and their average reaches PassAccuracy. A OneSitting set banks nothing: the
// whole run counts, start to finish.
struct ProgressionStorySet
{
    std::string Id;
    int Act = 0;
    std::string Name;
    std::string Description;
    std::string Venue;          // as ProgressionGig::Venue; empty keeps the player's own
    std::string VenueBase;      // the room the venue is dressed from (Club, Basement...)
    double PassAccuracy = 70.0;
    bool OneSitting = false;
    // One continuous show: each song's last note leads straight into the next recording, with no
    // results screen until the set is over (NoteHighwayCore's hand-off).
    bool Continuous = false;
    bool Credits = false;       // passing it ends the story
    bool PostCredits = false;   // a bonus after the credits
    ProgressionRequirement Requires;
    std::vector<ProgressionStorySong> Songs;
    std::vector<std::string> Rewards;
    std::string MovesInto;      // a tier id: passing moves the hideout up to it at least
    std::string Audition;       // the audition held once it's passed
};

// Someone trying out for a seat in the band.
struct ProgressionCandidate
{
    std::string Id;
    std::string Name;
    std::string Description;
    std::string Leans;          // the music they lean toward
    std::string Pitch;          // what they say at the audition
    std::string Body;           // a People model name ("BodyType1_Mother_02")
    std::string Clothes;        // a skin name ("PolygonTown_03_B")
};

// The audition for a seat, held after a story set: the player picks one of its candidates.
struct ProgressionAudition
{
    std::string Id;
    std::string Seat;           // "bass", "guitar", "vocals", "keys"
    std::string After;          // the story set it follows
    bool Optional = false;
    std::string Description;
    std::vector<ProgressionCandidate> Candidates;
};

// One thing a call to Evaluate unlocked.
struct ProgressionUnlock
{
    std::string Kind;           // "tier", "item", "venue", "step", "milestone", "lessons", "story", "booking", "audition"
    std::string Id;
    std::string Text;           // for the player: "Moved into the Garage", "Unlocked: Practice pad"
};

class Progression
{
    ME_SINGLETON_DEFINITION( Progression );

public:
    static constexpr const char* kFile = "Assets/Progression/Progression.json";
    // Story mode, written by Tools/Story/make_story.py: its "Sets", "Auditions" and "Items".
    static constexpr const char* kStoryFile = "Assets/Progression/Story.json";

    // Loads kFile and kStoryFile; --unlock-all opens every lesson and venue (the profile is left alone).
    Progression();
    // Empty, for tests (then Load).
    explicit Progression( const json& inRoot );

    // Everything from inRoot, story included when it has "Sets" or "Auditions".
    void Load( const json& inRoot );
    // Replaces the story sets and auditions and adds the story's items.
    void LoadStory( const json& inRoot );

    const std::vector<ProgressionTier>& Tiers() const { return m_tiers; }
    const std::vector<ProgressionGig>& Gigs() const { return m_gigs; }
    const std::vector<ProgressionLessonStep>& LessonSteps() const { return m_steps; }
    const std::vector<ProgressionMilestone>& Milestones() const { return m_milestones; }
    const std::vector<ProgressionItem>& Items() const { return m_items; }

    const std::vector<ProgressionStorySet>& StorySets() const { return m_story; }
    // Story.json's "ProposedSets": sets not placed in the campaign yet. Nothing books, unlocks or
    // lists them; FindStorySet finds them, so --gig and the gig board's debug rows can play them.
    const std::vector<ProgressionStorySet>& ProposedStorySets() const { return m_proposed; }
    const std::vector<ProgressionAudition>& Auditions() const { return m_auditions; }

    const ProgressionGig* FindGig( const std::string& inId ) const;
    const ProgressionStorySet* FindStorySet( const std::string& inId ) const;
    // The story set (a proposed one too) that plays inTrack, and which of its songs it is (as
    // StorySetlist matches them: the recording's link, else artist and title); null when none does.
    const ProgressionStorySet* FindStorySong( const TrackData& inTrack, int& outSong ) const;
    const ProgressionAudition* FindAudition( const std::string& inId ) const;
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

    // Story mode. A set is open when its requirement holds; it is passed once the profile says so.
    bool StoryOpen( const ProgressionStorySet& inSet, const PlayerProfile& inProfile ) const;
    bool StoryPassed( const ProgressionStorySet& inSet, const PlayerProfile& inProfile ) const;
    // Each song of the set as an index into inTracks, -1 for one the library doesn't have (yet).
    // A real chart wins over a stand-in (DLCSource "story-stub") of the same song.
    std::vector<int> StorySetlist( const ProgressionStorySet& inSet, const std::vector<TrackData>& inTracks ) const;
    // The song to play next: the first one not banked (0 for a OneSitting set, and once all are).
    int StoryNextSong( const ProgressionStorySet& inSet, const PlayerProfile& inProfile ) const;
    // The banked songs' average, the unbanked ones counting 0.
    double StoryAverage( const ProgressionStorySet& inSet, const PlayerProfile& inProfile ) const;
    // The venue's state as song inSong starts: the flags of the songs before it that are banked.
    std::vector<std::string> StoryFlags( const ProgressionStorySet& inSet, int inSong, const PlayerProfile& inProfile ) const;
    // Whether the story's credits have rolled: a Credits set has been passed.
    bool StoryFinished( const PlayerProfile& inProfile ) const;
    // An audition to hold now: its set passed and its seat still empty. Optional ones too; null
    // when there is none.
    const ProgressionAudition* PendingAudition( const PlayerProfile& inProfile ) const;
    // Seats the candidate (false for no such audition or candidate). Doesn't save the profile.
    bool ChooseMember( const std::string& inAuditionId, const std::string& inCandidateId, PlayerProfile& ioProfile ) const;
    // Leaves an Optional audition's seat empty for good (false for one that isn't optional).
    bool DeclineAudition( const std::string& inAuditionId, PlayerProfile& ioProfile ) const;

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
    std::vector<ProgressionStorySet> m_story;
    std::vector<ProgressionStorySet> m_proposed;
    std::vector<ProgressionAudition> m_auditions;
};
