#pragma once
#include "CoreGame/TrackList.h"
#include "Singleton.h"
#include <string>
#include <utility>
#include <vector>

// A practice lesson (Docs/Practice.md): a rudiment or a groove, written as a short pattern that
// repeats. Lessons are data: Assets/Practice/Lessons.json.
struct PracticeLesson
{
    std::string Id;            // Stable name: the tempo last used is remembered under it
    std::string Name;
    std::string Category;      // "Rudiments", "Grooves", ...: the list's headings
    std::string Description;
    int Bpm = 80;              // Where a first-timer starts
    int StepsPerBeat = 4;      // 2 eighths, 3 triplets, 4 sixteenths
    int BeatsPerBar = 4;
    // A rudiment: one hand per step, played on Pad. R / L a stroke, r / l a tap (quiet), ">" before
    // a letter an accent, "^" before a letter a flam (a quiet grace note from the other hand just
    // ahead of it), "-" a rest. Spaces are only for reading.
    std::string Sticking;
    std::string Pad = "snare1";
    // A groove: lane name ("closed_hh", "snare1", "bass1", ...) and its steps: x a stroke, X an
    // accent, o a ghost note, - a rest.
    std::vector<std::pair<std::string, std::string>> Lanes;
};

// The lessons, and the session being played: a lesson turned into a chart the highway plays like
// any song, over a click track written for its tempo.
class Practice
{
    ME_SINGLETON_DEFINITION( Practice );

public:
    // What LaunchPlayTrackEvent::TrackID carries to play the session's chart.
    static constexpr const char* kTrackId = "practice";
    static constexpr int kMinBpm = 40;
    static constexpr int kMaxBpm = 220;

    Practice();

    const std::vector<PracticeLesson>& Lessons() const { return m_lessons; }

    // A lesson as a chart: a bar of count-in, then inBars bars of its pattern at inBpm, with a
    // beat grid, and for a rudiment its sticking as the HUD's karaoke line. No audio.
    static TrackData BuildChart( const PracticeLesson& inLesson, int inBpm, int inBars );
    // Writes a click on every beat (a higher one on each bar's first) for inSeconds as a WAV.
    // With inFirstBeat / inBeatCount only those beats click and the rest is silence.
    static bool WriteClickTrack( const std::string& inFile, int inBpm, int inBeatsPerBar, double inSeconds, int inFirstBeat = 0, int inBeatCount = -1 );

    // Makes lesson inLesson the session: its chart and its click track. False when there is no
    // such lesson or the click track can't be written.
    bool Begin( int inLesson, int inBpm, int inBars );
    bool IsActive() const { return m_active; }
    TrackData& Chart() { return m_chart; }
    int LessonIndex() const { return m_lesson; }

private:
    void Load();

    std::vector<PracticeLesson> m_lessons;
    TrackData m_chart;
    int m_lesson = -1;
    bool m_active = false;
};
