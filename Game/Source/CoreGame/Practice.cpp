#include "CoreGame/Practice.h"
#include "CoreGame/BeatGrid.h"
#include "CoreGame/ClickTrack.h"
#include "Editor/PadBindings.h"
#include "CLog.h"
#include "File.h"
#include "JSON.h"
#include "Path.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>

namespace
{
    constexpr const char* kLessonFile = "Assets/Practice/Lessons.json";
    // Click tracks are written here, one per tempo and length, and reused.
    constexpr const char* kClickFolder = ".tmp/Practice/";
    constexpr int kSampleRate = 44100;
    constexpr uint8_t kTap = 30;
    constexpr uint8_t kStroke = 100;
    constexpr uint8_t kAccent = 127;
    // A flam's grace note comes this long before its main stroke.
    constexpr double kFlamSeconds = 0.035;

    struct Step
    {
        double Beat = 0.0;          // from the start of the pattern
        PadId Pad = PadId::Snare;
        uint8_t Velocity = kStroke;
        std::string Hand;           // what the sticking line shows for it; empty for a groove
        bool Grace = false;         // a flam's grace note: played ahead of Beat
    };


    PadId PadOfLane( const std::string& inLane )
    {
        // GetNewPadId asserts on a name it doesn't know; a lesson file is hand-written.
        for( int16_t id = PadId::Invalid + 1; id < PadId::COUNT; ++id )
        {
            if( inLane == PadUtils::GetPadId( id ) )
            {
                return static_cast<PadId>( id );
            }
        }
        return PadId::Invalid;
    }


    // The lesson's pattern as steps, and its length in beats.
    double PatternSteps( const PracticeLesson& inLesson, std::vector<Step>& outSteps )
    {
        outSteps.clear();
        const double stepBeats = 1.0 / std::max( 1, inLesson.StepsPerBeat );
        int length = 0;
        if( !inLesson.Sticking.empty() )
        {
            const PadId pad = PadOfLane( inLesson.Pad );
            bool accent = false;
            bool flam = false;
            for( char c : inLesson.Sticking )
            {
                if( c == '>' ) { accent = true; continue; }
                if( c == '^' ) { flam = true; continue; }
                if( c == '-' ) { ++length; accent = flam = false; continue; }
                const bool right = c == 'R' || c == 'r';
                if( !right && c != 'L' && c != 'l' )
                {
                    continue;
                }
                const bool tap = c == 'r' || c == 'l';
                Step step;
                step.Beat = length * stepBeats;
                step.Pad = pad == PadId::Invalid ? PadId::Snare : pad;
                step.Velocity = accent ? kAccent : tap ? kTap : kStroke;
                step.Hand = std::string( flam ? ( right ? "l" : "r" ) : "" ) + c;
                if( flam )
                {
                    Step grace = step;
                    grace.Velocity = kTap;
                    grace.Hand.clear();
                    grace.Grace = true;
                    outSteps.push_back( grace );
                }
                outSteps.push_back( step );
                ++length;
                accent = flam = false;
            }
        }
        for( const auto& [lane, steps] : inLesson.Lanes )
        {
            const PadId pad = PadOfLane( lane );
            if( pad == PadId::Invalid )
            {
                YIKES( "Practice: lesson '" + inLesson.Name + "' names a lane that doesn't exist: " + lane );
                continue;
            }
            int at = 0;
            for( char c : steps )
            {
                if( c == ' ' )
                {
                    continue;
                }
                if( c == 'x' || c == 'X' || c == 'o' )
                {
                    Step step;
                    step.Beat = at * stepBeats;
                    step.Pad = pad;
                    step.Velocity = c == 'X' ? kAccent : c == 'o' ? kTap : kStroke;
                    outSteps.push_back( step );
                }
                ++at;
            }
            length = std::max( length, at );
        }
        std::stable_sort( outSteps.begin(), outSteps.end(), []( const Step& a, const Step& b ) { return a.Beat < b.Beat; } );
        // Whole bars, so the pattern starts on a bar line every time round.
        const int barSteps = std::max( 1, inLesson.StepsPerBeat * inLesson.BeatsPerBar );
        length = std::max( barSteps, ( length + barSteps - 1 ) / barSteps * barSteps );
        return length * stepBeats;
    }

}


Practice::Practice()
{
    Load();
}


void Practice::Load()
{
    m_lessons.clear();
    const Path file( kLessonFile );
    if( !file.Exists )
    {
        YIKES( "Practice: no lesson file at Assets/Practice/Lessons.json" );
        return;
    }
    const json root = json::parse( File( file ).Read(), nullptr, false );
    if( !root.is_object() || !root.contains( "Lessons" ) || !root["Lessons"].is_array() )
    {
        YIKES( "Practice: Lessons.json has no \"Lessons\" list" );
        return;
    }
    for( const json& entry : root["Lessons"] )
    {
        if( !entry.is_object() )
        {
            continue;
        }
        PracticeLesson lesson;
        lesson.Name = entry.value( "Name", std::string() );
        lesson.Id = entry.value( "Id", lesson.Name );
        lesson.Category = entry.value( "Category", std::string( "Lessons" ) );
        lesson.Description = entry.value( "Description", std::string() );
        lesson.Bpm = std::clamp( entry.value( "Bpm", 80 ), kMinBpm, kMaxBpm );
        lesson.StepsPerBeat = std::clamp( entry.value( "StepsPerBeat", 4 ), 1, 12 );
        lesson.BeatsPerBar = std::clamp( entry.value( "BeatsPerBar", 4 ), 1, 12 );
        lesson.Sticking = entry.value( "Sticking", std::string() );
        lesson.Pad = entry.value( "Pad", std::string( "snare1" ) );
        if( entry.contains( "Lanes" ) && entry["Lanes"].is_object() )
        {
            for( const auto& [lane, steps] : entry["Lanes"].items() )
            {
                // A lane the kit doesn't have is left out (and said so) rather than kept.
                if( steps.is_string() && PadOfLane( lane ) != PadId::Invalid )
                {
                    lesson.Lanes.emplace_back( lane, steps.get<std::string>() );
                }
                else
                {
                    YIKES( "Practice: lesson '" + lesson.Name + "' has a lane that isn't a pad: " + lane );
                }
            }
        }
        std::vector<Step> steps;
        PatternSteps( lesson, steps );
        if( lesson.Name.empty() || steps.empty() )
        {
            YIKES( "Practice: a lesson has no name or no notes; skipped" );
            continue;
        }
        m_lessons.push_back( std::move( lesson ) );
    }
}


TrackData Practice::BuildChart( const PracticeLesson& inLesson, int inBpm, int inBars )
{
    const int bpm = std::clamp( inBpm, kMinBpm, kMaxBpm );
    const int bars = std::clamp( inBars, 1, 128 );
    const double beatSeconds = 60.0 / bpm;
    std::vector<Step> steps;
    const double patternBeats = PatternSteps( inLesson, steps );
    // A bar of clicks alone, then the pattern over and over for inBars bars.
    const double countInBeats = inLesson.BeatsPerBar;
    const double totalBeats = countInBeats + static_cast<double>( bars ) * inLesson.BeatsPerBar;

    TrackData chart;
    chart.m_practice = true;
    chart.m_trackName = inLesson.Name;
    chart.m_artistName = std::to_string( bpm ) + " BPM";
    chart.m_albumName = "Practice";
    chart.m_genre = inLesson.Category;
    chart.m_dlcSource = "DS";
    chart.m_bpm = bpm;
    chart.m_noteSpeed = 10.f;
    chart.m_duration = static_cast<float>( ( totalBeats + 1.0 ) * beatSeconds );
    chart.m_durationMS = chart.m_duration * 1000.f;
    chart.m_beats = BeatGrid::Generate( static_cast<float>( bpm ), inLesson.BeatsPerBar, 0.0, totalBeats * beatSeconds );

    for( double start = countInBeats; start < totalBeats - 1e-6; start += patternBeats )
    {
        for( const Step& step : steps )
        {
            const double beat = start + step.Beat;
            if( beat >= totalBeats - 1e-6 )
            {
                break;
            }
            const double seconds = beat * beatSeconds - ( step.Grace ? std::min( kFlamSeconds, beatSeconds * 0.25 ) : 0.0 );
            NoteData note;
            note.m_editorLane = step.Pad;
            note.m_noteName = PadUtils::GetPadId( step.Pad );
            note.m_triggerTime = static_cast<float>( seconds );
            note.m_triggerTimeMS = static_cast<uint32_t>( std::lround( seconds * 1000.0 ) );
            note.m_velocity = step.Velocity;
            chart.m_noteData.push_back( note );
            if( !step.Hand.empty() )
            {
                // The sticking rides the lyric line: a "syllable" per stroke, a line per bar.
                chart.m_venue.m_lyrics.push_back( { static_cast<float>( seconds ), step.Hand } );
                chart.m_venue.m_vocalNotes.push_back( { static_cast<float>( seconds ), static_cast<float>( seconds + beatSeconds / inLesson.StepsPerBeat * 0.9 ), 0 } );
            }
        }
    }
    if( !chart.m_venue.m_lyrics.empty() )
    {
        for( int bar = 0; bar < bars; ++bar )
        {
            const double from = ( countInBeats + static_cast<double>( bar ) * inLesson.BeatsPerBar ) * beatSeconds;
            // A grace note ahead of the bar line belongs to the bar it leads into.
            chart.m_venue.m_vocalPhrases.push_back( { static_cast<float>( from - kFlamSeconds - 0.005 ), static_cast<float>( from + inLesson.BeatsPerBar * beatSeconds - kFlamSeconds - 0.01 ), 0 } );
        }
    }
    std::stable_sort( chart.m_noteData.begin(), chart.m_noteData.end(), []( const NoteData& a, const NoteData& b ) { return a.m_triggerTime < b.m_triggerTime; } );
    chart.m_noteCount = static_cast<int>( chart.m_noteData.size() );
    return chart;
}


bool Practice::WriteClickTrack( const std::string& inFile, int inBpm, int inBeatsPerBar, double inSeconds, int inFirstBeat, int inBeatCount )
{
    const double beatSeconds = 60.0 / std::max( 1, inBpm );
    std::vector<ClickTrack::Click> clicks;
    for( int beat = std::max( 0, inFirstBeat ); beat * beatSeconds < inSeconds && ( inBeatCount < 0 || beat < inFirstBeat + inBeatCount ); ++beat )
    {
        clicks.push_back( { beat * beatSeconds, beat % std::max( 1, inBeatsPerBar ) == 0 } );
    }
    return ClickTrack::Write( inFile, clicks, inSeconds, kSampleRate );
}


bool Practice::Begin( int inLesson, int inBpm, int inBars )
{
    m_active = false;
    if( inLesson < 0 || inLesson >= static_cast<int>( m_lessons.size() ) )
    {
        return false;
    }
    const PracticeLesson& lesson = m_lessons[inLesson];
    m_chart = BuildChart( lesson, inBpm, inBars );
    // The click track is the session's "song": the highway's clock locks to it like any other,
    // so pause, resume and the latency settings all work as in a song. One file per tempo, bar
    // length and duration; the same name always holds the same clicks.
    const int seconds = static_cast<int>( std::ceil( m_chart.m_duration ) ) + 1;
    const std::string name = "click_" + std::to_string( m_chart.m_bpm ) + "bpm_" + std::to_string( lesson.BeatsPerBar ) + "beats_" + std::to_string( seconds ) + "s.wav";
    const Path folder( kClickFolder );
    const std::string file = folder.FullPath + ( !folder.FullPath.empty() && folder.FullPath.back() == '/' ? "" : "/" ) + name;
    std::error_code error;
    if( !std::filesystem::is_regular_file( file, error ) && !WriteClickTrack( file, m_chart.m_bpm, lesson.BeatsPerBar, seconds ) )
    {
        YIKES( "Practice: couldn't write the click track to " + file );
        return false;
    }
    m_chart.m_trackFileName = name;
    m_chart.m_trackSourcePath = file;
    m_lesson = inLesson;
    m_active = true;
    return true;
}
