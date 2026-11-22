#pragma once
#include "Singleton.h"
#include "JSON.h"
#include <map>
#include <set>
#include <string>
#include <vector>

struct PracticeLesson;

// What the player has done (Docs/Game-Architecture.md → Player profile): each song's bests, each practice
// lesson's results, and the hideout's progress. Written to Profile.json the moment a result
// lands, so a crash loses nothing. Settings live in GameSettings; this is only the record.
class PlayerProfile
{
    ME_SINGLETON_DEFINITION( PlayerProfile );

public:
    // How one play of a song went, as the results screen shows it.
    struct SongResult
    {
        int Score = 0;
        double Accuracy = 0.0;  // 0 to 100
        int MaxCombo = 0;
        int Missed = 0;
        int TotalNotes = 0;
    };

    // A song's bests across every play. Each best is kept on its own: the best score and the best
    // accuracy can come from different plays.
    struct SongRecord
    {
        int Plays = 0;
        int BestScore = 0;
        double BestAccuracy = 0.0;
        int BestCombo = 0;
        bool FullCombo = false;
    };

    // A practice lesson's results: the best accuracy, and the fastest tempo it passed at.
    struct LessonRecord
    {
        int Plays = 0;
        double BestAccuracy = 0.0;
        int BestBpm = 0;        // The fastest tempo played at the pass accuracy, 0 for none
        bool Passed = false;
    };

    // A story set's progress (CoreGame/Progression.h): each song's banked best accuracy (0 to 100,
    // -1 for not banked yet), and whether the set has passed.
    struct StoryRecord
    {
        std::vector<double> Banked;
        bool Passed = false;
    };

    // What a recorded result changed, for the results screen to say so.
    struct Outcome
    {
        bool NewBestScore = false;
        bool NewBestAccuracy = false;
        bool FirstFullCombo = false;
        bool LessonPassed = false;  // Passed for the first time
    };

    // The game's profile: Profile.json in the working folder, as Settings.json is (--profile <file>
    // names another, for tests and captures).
    PlayerProfile();
    // A profile kept in inFile (tests): read when it exists, written by Save. Empty keeps it in memory only.
    explicit PlayerProfile( const std::string& inFile );

    Outcome RecordSong( const std::string& inSongKey, const SongResult& inResult );
    Outcome RecordLesson( const PracticeLesson& inLesson, int inBpm, double inAccuracy );

    const SongRecord* FindSong( const std::string& inSongKey ) const;
    const LessonRecord* FindLesson( const std::string& inLessonId ) const;
    const std::map<std::string, SongRecord>& Songs() const { return m_songs; }
    const std::map<std::string, LessonRecord>& Lessons() const { return m_lessons; }

    // The hideout's progress (filled in by the progression rules, Phase 1).
    int HideoutTier = 0;
    // What the player called the band (the bedsheet, the kick head); empty: "BAND NAME TBD".
    std::string BandName;
    std::set<std::string> CompletedGigs;
    // Story mode, by set id.
    std::map<std::string, StoryRecord> Story;
    // The band: who sits in each seat ("bass" -> a candidate id), chosen at the auditions.
    std::map<std::string, std::string> BandMembers;
    // Every unlock so far, by kind and id ("item:practice-pad", "venue:club", "tier:garage"...;
    // CoreGame/Progression.h). An id in here was already announced.
    std::set<std::string> UnlockedItems;
    // Unlocks not shown yet: the hideout shows them on its next visit and clears them.
    std::vector<std::string> Notices;
    // Items unlocked but not shown yet: the hideout's camera visits each once, then clears them.
    std::vector<std::string> NewItems;
    // The highest room the hideout has shown: a room above it is being moved into (its first
    // visit plays the way in and leaves the boxes out). -1 before the first visit.
    int SeenTier = -1;
    // The songs finished most recently, by song key, the latest first (the setlist taped to the
    // hideout's floor reads them).
    std::vector<std::string> RecentSongs;
    static constexpr size_t kRecentSongs = 12;
    // Counts over the songs, for the progression rules.
    int SongsPlayed() const { return static_cast<int>( m_songs.size() ); }
    int FullCombos() const;
    int SongsAtAccuracy( double inAccuracy ) const;
    int LessonsPassed() const;
    bool LessonPassed( const std::string& inLessonId ) const;

    // Marks a lesson passed (or not) without playing it: the hideout's debug menu.
    void SetLessonPassed( const std::string& inLessonId, bool inPassed );

    json ToJson() const;
    void FromJson( const json& inRoot );
    void Save() const;
    // Where Save writes; empty for a profile kept in memory.
    const std::string& File() const { return m_file; }

private:
    void Load();

    std::string m_file;
    std::map<std::string, SongRecord> m_songs;
    std::map<std::string, LessonRecord> m_lessons;
};
