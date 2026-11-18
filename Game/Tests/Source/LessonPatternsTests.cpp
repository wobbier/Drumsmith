#include <doctest/doctest.h>
#include "Config/PlayerProfile.h"
#include "CoreGame/LessonPatterns.h"
#include "CoreGame/Practice.h"
#include "CoreGame/Progression.h"

namespace
{
    // A chart's beat grid: inBars bars of four beats at 120 bpm, and one more downbeat to close the last.
    std::vector<LessonPatterns::Beat> Beats( int inBars )
    {
        std::vector<LessonPatterns::Beat> beats;
        for( int i = 0; i <= inBars * 4; ++i )
        {
            beats.push_back( { 0.5f * static_cast<float>( i ), i % 4 == 0 } );
        }
        return beats;
    }


    PracticeLesson Groove( const std::string& inId, std::vector<std::pair<std::string, std::string>> inLanes )
    {
        PracticeLesson lesson;
        lesson.Id = inId;
        lesson.StepsPerBeat = 2;
        lesson.Lanes = std::move( inLanes );
        return lesson;
    }


    PracticeLesson Rudiment( const std::string& inId, const std::string& inSticking, int inStepsPerBeat = 4 )
    {
        PracticeLesson lesson;
        lesson.Id = inId;
        lesson.StepsPerBeat = inStepsPerBeat;
        lesson.Sticking = inSticking;
        return lesson;
    }


    // A rock beat: hats on the eighths, kick on 1 and 3, snare on 2 and 4, for inBars bars from inFirstBar.
    void RockBeat( std::vector<LessonPatterns::Note>& ioNotes, int inFirstBar, int inBars )
    {
        for( int bar = inFirstBar; bar < inFirstBar + inBars; ++bar )
        {
            for( int eighth = 0; eighth < 8; ++eighth )
            {
                const float t = 2.f * static_cast<float>( bar ) + 0.25f * static_cast<float>( eighth );
                ioNotes.push_back( { t, "closed_hh" } );
                if( eighth == 0 || eighth == 4 ) ioNotes.push_back( { t, "bass1" } );
                if( eighth == 2 || eighth == 6 ) ioNotes.push_back( { t, "snare1" } );
            }
        }
    }
}


TEST_CASE( "Lesson patterns: a groove is found bar by bar, two in a row at least, and nothing else matches it" )
{
    const std::vector<PracticeLesson> lessons = {
        Groove( "rock", { { "closed_hh", "xxxx xxxx" }, { "snare1", "--x- --x-" }, { "bass1", "x--- x---" } } ),
        Groove( "rock-kicks", { { "closed_hh", "xxxx xxxx" }, { "snare1", "--x- --x-" }, { "bass1", "x--- xx--" } } ),
    };
    std::vector<LessonPatterns::Note> notes;
    RockBeat( notes, 2, 4 );
    const std::vector<PatternSection> found = LessonPatterns::Find( lessons, Beats( 8 ), notes );
    REQUIRE( found.size() == 1 );
    CHECK( found[0].Lesson == "rock" );
    CHECK( found[0].Bars == 4 );
    CHECK( found[0].Start == doctest::Approx( 4.f ) );
    CHECK_FALSE( found[0].RhythmOnly );

    // One bar alone isn't a section; a note off the grid spoils its bar.
    std::vector<LessonPatterns::Note> one;
    RockBeat( one, 2, 1 );
    CHECK( LessonPatterns::Find( lessons, Beats( 8 ), one ).empty() );
    std::vector<LessonPatterns::Note> sloppy;
    RockBeat( sloppy, 0, 3 );
    sloppy.push_back( { 2.f + 0.1f, "tom1" } );
    const std::vector<PatternSection> split = LessonPatterns::Find( lessons, Beats( 8 ), sloppy );
    CHECK( split.empty() );
}


TEST_CASE( "Lesson patterns: a rudiment is found by its rhythm, and a flam never is" )
{
    const std::vector<PracticeLesson> lessons = {
        Rudiment( "singles", "RLRL RLRL RLRL RLRL" ),
        Rudiment( "five-stroke", "rrll>R--- llrr>L---" ),
        Rudiment( "flam", "^R ^L ^R ^L", 1 ),
    };
    std::vector<LessonPatterns::Note> notes;
    for( int k = 0; k < 16 * 3; ++k )
    {
        notes.push_back( { 2.f + 0.125f * static_cast<float>( k ), k % 4 == 0 ? "tom1" : "snare1" } );
    }
    const std::vector<PatternSection> found = LessonPatterns::Find( lessons, Beats( 8 ), notes );
    REQUIRE( found.size() == 1 );
    CHECK( found[0].Lesson == "singles" );
    CHECK( found[0].Bars == 3 );
    CHECK( found[0].RhythmOnly );
}


TEST_CASE( "Progression: a groove the player has played in a song opens its lesson" )
{
    Progression progression( json::parse( R"({
        "LessonSteps": [
            { "Id": "r1", "Name": "Rudiments I", "Lessons": [ "singles" ] },
            { "Id": "g1", "Name": "Grooves I", "Lessons": [ "rock" ], "Requires": { "LessonSteps": [ "r1" ] } }
        ]
    })" ) );
    PlayerProfile profile( "" );
    CHECK_FALSE( progression.LessonOpen( "rock", profile ) );
    progression.SongLessons["Metallica - Enter Sandman"] = { { "rock", "Rock beat", "Enter Sandman" } };
    // Not until the song has been played.
    CHECK( progression.Evaluate( profile ).empty() );
    PlayerProfile::SongResult result;
    result.Score = 1;
    result.TotalNotes = 10;
    profile.RecordSong( "Metallica - Enter Sandman", result );
    const std::vector<ProgressionUnlock> unlocks = progression.Evaluate( profile );
    REQUIRE( unlocks.size() == 1 );
    CHECK( unlocks[0].Kind == "lesson" );
    CHECK( unlocks[0].Text == "New lesson: Rock beat (you played it in Enter Sandman)" );
    CHECK( progression.LessonOpen( "rock", profile ) );
    CHECK( progression.Evaluate( profile ).empty() );
}
