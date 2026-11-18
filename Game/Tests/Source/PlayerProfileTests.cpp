#include <doctest/doctest.h>
#include "Config/PlayerProfile.h"
#include "CoreGame/Practice.h"
#include <filesystem>
#include <fstream>

namespace
{
    PlayerProfile::SongResult Result( int inScore, double inAccuracy, int inMaxCombo, int inMissed, int inTotal )
    {
        PlayerProfile::SongResult result;
        result.Score = inScore;
        result.Accuracy = inAccuracy;
        result.MaxCombo = inMaxCombo;
        result.Missed = inMissed;
        result.TotalNotes = inTotal;
        return result;
    }


    PracticeLesson Lesson()
    {
        PracticeLesson lesson;
        lesson.Id = "single-paradiddle";
        lesson.Bpm = 60;
        lesson.PassBpm = 80;
        lesson.PassAccuracy = 90.0;
        return lesson;
    }
}


TEST_CASE( "Profile: each song best is kept on its own, and a full combo stays" )
{
    PlayerProfile profile( "" );
    PlayerProfile::Outcome first = profile.RecordSong( "Song A", Result( 1000, 80.0, 50, 3, 100 ) );
    CHECK( first.NewBestScore );
    CHECK_FALSE( first.FirstFullCombo );

    // Higher accuracy, lower score: only the accuracy best moves.
    PlayerProfile::Outcome second = profile.RecordSong( "Song A", Result( 900, 85.0, 40, 2, 100 ) );
    CHECK_FALSE( second.NewBestScore );
    CHECK( second.NewBestAccuracy );

    PlayerProfile::Outcome full = profile.RecordSong( "Song A", Result( 1500, 99.0, 100, 0, 100 ) );
    CHECK( full.FirstFullCombo );
    profile.RecordSong( "Song A", Result( 10, 5.0, 1, 99, 100 ) );

    const PlayerProfile::SongRecord* record = profile.FindSong( "Song A" );
    REQUIRE( record );
    CHECK( record->Plays == 4 );
    CHECK( record->BestScore == 1500 );
    CHECK( record->BestAccuracy == doctest::Approx( 99.0 ) );
    CHECK( record->BestCombo == 100 );
    CHECK( record->FullCombo );
    CHECK( profile.FindSong( "Song B" ) == nullptr );
    CHECK_FALSE( profile.RecordSong( "", Result( 1, 1.0, 1, 0, 1 ) ).NewBestScore );
}


TEST_CASE( "Profile: a lesson passes at its tempo and accuracy, once" )
{
    PlayerProfile profile( "" );
    const PracticeLesson lesson = Lesson();
    CHECK( lesson.PassTempo() == 80 );

    // Clean but too slow, then fast but sloppy: neither passes.
    CHECK_FALSE( profile.RecordLesson( lesson, 70, 98.0 ).LessonPassed );
    CHECK_FALSE( profile.RecordLesson( lesson, 90, 85.0 ).LessonPassed );
    const PlayerProfile::LessonRecord* record = profile.FindLesson( lesson.Id );
    REQUIRE( record );
    CHECK_FALSE( record->Passed );
    CHECK( record->BestBpm == 70 );

    CHECK( profile.RecordLesson( lesson, 84, 92.0 ).LessonPassed );
    CHECK_FALSE( profile.RecordLesson( lesson, 100, 95.0 ).LessonPassed );
    record = profile.FindLesson( lesson.Id );
    CHECK( record->Passed );
    CHECK( record->BestBpm == 100 );
    CHECK( record->Plays == 4 );

    // PassBpm 0 means the lesson's own starting tempo.
    PracticeLesson easy = lesson;
    easy.PassBpm = 0;
    CHECK( easy.Passes( 60, 90.0 ) );
    CHECK_FALSE( easy.Passes( 59, 100.0 ) );
}


TEST_CASE( "Profile: it round-trips through its file, and a broken file starts fresh" )
{
    const std::filesystem::path file = std::filesystem::temp_directory_path() / "drumsmith_profile_test.json";
    std::filesystem::remove( file );
    {
        PlayerProfile profile( file.string() );
        profile.RecordSong( "Song A", Result( 1234, 91.5, 77, 0, 77 ) );
        profile.RecordLesson( Lesson(), 80, 95.0 );
        profile.HideoutTier = 2;
        profile.CompletedGigs.insert( "backyard-party" );
        profile.UnlockedItems.insert( "practice-pad" );
        profile.Save();
    }
    {
        PlayerProfile profile( file.string() );
        const PlayerProfile::SongRecord* song = profile.FindSong( "Song A" );
        REQUIRE( song );
        CHECK( song->BestScore == 1234 );
        CHECK( song->BestAccuracy == doctest::Approx( 91.5 ) );
        CHECK( song->FullCombo );
        const PlayerProfile::LessonRecord* lesson = profile.FindLesson( "single-paradiddle" );
        REQUIRE( lesson );
        CHECK( lesson->Passed );
        CHECK( lesson->BestBpm == 80 );
        CHECK( profile.HideoutTier == 2 );
        CHECK( profile.CompletedGigs.count( "backyard-party" ) == 1 );
        CHECK( profile.UnlockedItems.count( "practice-pad" ) == 1 );
    }
    {
        std::ofstream( file, std::ios::trunc ) << "{ not json";
    }
    {
        PlayerProfile profile( file.string() );
        CHECK( profile.Songs().empty() );
        CHECK( std::filesystem::exists( file.string() + ".bad" ) );
    }
    std::filesystem::remove( file );
    std::filesystem::remove( file.string() + ".bad" );
}


TEST_CASE( "Profile: the recent songs are the latest first, each once, and SeenTier round-trips" )
{
    PlayerProfile profile( "" );
    for( const char* song : { "A", "B", "C", "A" } )
    {
        profile.RecordSong( song, Result( 10, 50.0, 1, 1, 2 ) );
    }
    REQUIRE( profile.RecentSongs.size() == 3 );
    CHECK( profile.RecentSongs[0] == "A" );
    CHECK( profile.RecentSongs[1] == "C" );
    CHECK( profile.RecentSongs[2] == "B" );
    for( int i = 0; i < 20; ++i )
    {
        profile.RecordSong( "Song " + std::to_string( i ), Result( 10, 50.0, 1, 1, 2 ) );
    }
    CHECK( profile.RecentSongs.size() == PlayerProfile::kRecentSongs );
    CHECK( profile.RecentSongs[0] == "Song 19" );

    // A new profile hasn't seen a room; one from before SeenTier existed has seen its own.
    PlayerProfile fresh( "" );
    CHECK( fresh.SeenTier == -1 );
    PlayerProfile old( "" );
    old.FromJson( json::parse( R"({ "HideoutTier": 1 })" ) );
    CHECK( old.SeenTier == 1 );
    old.SeenTier = 0;
    PlayerProfile copy( "" );
    copy.FromJson( old.ToJson() );
    CHECK( copy.SeenTier == 0 );
    CHECK( copy.RecentSongs.empty() );
}


TEST_CASE( "Profile: a lesson can be marked passed and unpassed without playing it" )
{
    PlayerProfile profile( "" );
    profile.SetLessonPassed( "flam", true );
    CHECK( profile.LessonPassed( "flam" ) );
    CHECK( profile.LessonsPassed() == 1 );
    profile.SetLessonPassed( "flam", false );
    CHECK_FALSE( profile.LessonPassed( "flam" ) );
    profile.SetLessonPassed( "", true );
    CHECK( profile.LessonsPassed() == 0 );
}
