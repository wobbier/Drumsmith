#pragma once
#include "Singleton.h"
#include <atomic>
#include <map>
#include <string>
#include <thread>
#include <vector>

struct PracticeLesson;

// Which songs play which practice lesson (Docs/Practice.md → Songs that use a lesson). A chart's
// notes are put on its own beat grid at the lesson's subdivision and the lesson's pattern is
// looked for bar by bar:
//   * A groove (Lanes) matches a bar when, on the lesson's lanes plus the kick and the snare,
//     every step has exactly the lesson's strokes (accents and ghosts count as strokes). Two bars
//     in a row make a section.
//   * A rudiment (Sticking) can only be matched by its rhythm: a chart says which drum, not which
//     hand. A bar matches when the hand drums (snare and toms) hit exactly the steps the sticking
//     strokes, tiled over the bar, with no cymbal where it rests. Singles, doubles and the
//     paradiddle are all "every sixteenth", so they find the same bars; flams aren't charted, so
//     the flam lessons find nothing.
// A note further than a fifth of a step off the grid spoils its beat (a fill in another feel).
struct PatternSection
{
    std::string Lesson;         // PracticeLesson::Id
    float Start = 0.f;          // seconds into the song
    int Bars = 0;
    bool RhythmOnly = false;    // a rudiment, found by its rhythm alone
};

namespace LessonPatterns
{
    struct Beat
    {
        float Time = 0.f;
        bool Downbeat = false;  // a bar starts on it
    };
    struct Note
    {
        float Time = 0.f;
        std::string Lane;       // NoteData::m_noteName: "snare1", "closed_hh", "bass1"...
    };

    // Every section of the chart that plays one of the lessons, in lesson order.
    std::vector<PatternSection> Find( const std::vector<PracticeLesson>& inLessons, const std::vector<Beat>& inBeats, const std::vector<Note>& inNotes );
    // Reads a song's NoteData.txt ({"Beats": [[seconds, downbeat], ...], "Notes": [{"TriggerTime",
    // "NoteName"}, ...]}). False when it can't.
    bool ReadChart( const std::string& inFile, std::vector<Beat>& outBeats, std::vector<Note>& outNotes );
}

// The library's sections, worked out once a session on a worker thread from each song's chart.
class LessonPatternIndex
{
    ME_SINGLETON_DEFINITION( LessonPatternIndex );

public:
    // A song that plays a lesson, and where.
    struct Use
    {
        std::string Song;       // the song's key (TrackDatabase::FavoriteKey)
        int Track = -1;         // its index in TrackDatabase, now
        std::string Name;       // its title
        PatternSection Section; // its longest section of the lesson
        int TotalBars = 0;      // every section of it, together
    };

    LessonPatternIndex() = default;
    ~LessonPatternIndex();

    // Starts reading the library on a worker thread, once a session. Main thread only.
    void Request();
    // Main thread: takes the worker's results once it's done (and gives Progression the grooves
    // each song plays, for opening lessons). True on the call they arrive.
    bool Poll();
    bool Ready() const { return m_ready; }
    bool Busy() const { return m_started && !m_ready; }
    // The songs that play a lesson, the most bars first.
    std::vector<Use> SongsFor( const std::string& inLesson ) const;
    // Each song's sections, by song key.
    const std::map<std::string, std::vector<PatternSection>>& Songs() const { return m_songs; }

private:
    std::thread m_worker;
    std::atomic<bool> m_done{ false };
    std::atomic<bool> m_stop{ false };
    bool m_started = false;
    bool m_ready = false;
    std::map<std::string, std::vector<PatternSection>> m_found;     // the worker's
    std::map<std::string, std::vector<PatternSection>> m_songs;     // the main thread's
};
