#include <doctest/doctest.h>
#include "Config/PlayerProfile.h"
#include "CoreGame/GigSession.h"
#include "CoreGame/Practice.h"
#include "CoreGame/Progression.h"
#include "CoreGame/TrackList.h"
#include "Venue/VenueRegistry.h"
#include <filesystem>
#include <fstream>
#include <set>
#include <sstream>

namespace
{
    // A small journey: two rooms, a gig between them, a two-step ladder, a milestone and a venue gate.
    json Journey()
    {
        return json::parse( R"({
            "Tiers": [
                { "Id": "basement", "Name": "the Basement", "Rewards": [ "radio" ] },
                { "Id": "garage", "Name": "the Garage", "Requires": { "Gigs": [ "backyard" ] }, "Rewards": [ "rug" ] }
            ],
            "Gigs": [
                { "Id": "backyard", "Name": "Backyard", "Venue": "Backyard", "Songs": 2, "MaxNotesPerSecond": 4, "Rewards": [ "flyer" ] },
                { "Id": "club", "Name": "Club Night", "Venue": "Club", "Requires": { "Tier": 1, "LessonSteps": [ "r1" ] } }
            ],
            "LessonSteps": [
                { "Id": "r1", "Name": "Rudiments I", "Lessons": [ "singles", "doubles" ], "Rewards": [ "pad" ] },
                { "Id": "g1", "Name": "Grooves I", "Lessons": [ "rock" ], "Requires": { "LessonSteps": [ "r1" ] } }
            ],
            "Milestones": [ { "Id": "fc", "Name": "First full combo", "Requires": { "FullCombos": 1 }, "Rewards": [ "plaque" ] } ],
            "Items": [ { "Id": "radio", "Name": "Radio" }, { "Id": "rug", "Name": "Rug" }, { "Id": "pad", "Name": "Practice pad" } ],
            "Venues": [ { "Id": "Club", "Name": "the Club", "Requires": { "Gigs": [ "club" ] } } ]
        })" );
    }


    PracticeLesson Lesson( const std::string& inId )
    {
        PracticeLesson lesson;
        lesson.Id = inId;
        lesson.Bpm = 60;
        return lesson;
    }


    bool Has( const std::vector<ProgressionUnlock>& inUnlocks, const std::string& inKind, const std::string& inId )
    {
        for( const ProgressionUnlock& unlock : inUnlocks )
        {
            if( unlock.Kind == inKind && unlock.Id == inId )
            {
                return true;
            }
        }
        return false;
    }


    TrackData Song( const std::string& inFolder, int inNotes, float inSeconds )
    {
        TrackData track;
        track.m_trackName = inFolder;
        track.m_trackSourcePath = "/songs/" + inFolder + "/song.ogg";
        track.m_noteCount = inNotes;
        track.m_duration = inSeconds;
        return track;
    }
}


TEST_CASE( "Progression: the lesson ladder opens a step when the one before it has passed" )
{
    const Progression progression( Journey() );
    PlayerProfile profile( "" );
    CHECK( progression.LessonOpen( "singles", profile ) );
    CHECK_FALSE( progression.LessonOpen( "rock", profile ) );
    CHECK( progression.LessonOpen( "not-in-any-step", profile ) );

    // The first room's rewards come with the first look.
    std::vector<ProgressionUnlock> unlocks = progression.Evaluate( profile );
    CHECK( Has( unlocks, "item", "radio" ) );
    CHECK_FALSE( Has( unlocks, "step", "r1" ) );  // open from the start: nothing to announce

    profile.RecordLesson( Lesson( "singles" ), 60, 95.0 );
    CHECK( progression.Evaluate( profile ).empty() );
    profile.RecordLesson( Lesson( "doubles" ), 60, 95.0 );
    unlocks = progression.Evaluate( profile );
    CHECK( Has( unlocks, "lessons", "r1" ) );
    CHECK( Has( unlocks, "item", "pad" ) );
    CHECK( Has( unlocks, "step", "g1" ) );
    CHECK( progression.LessonOpen( "rock", profile ) );
    // Announced once.
    CHECK( progression.Evaluate( profile ).empty() );
    CHECK( profile.Notices.size() == unlocks.size() + 1 );
}


TEST_CASE( "Progression: a gig moves the hideout up, and that chains into the next gig and its venue" )
{
    const Progression progression( Journey() );
    PlayerProfile profile( "" );
    progression.Evaluate( profile );
    const ProgressionGig* club = progression.FindGig( "club" );
    REQUIRE( club );
    CHECK_FALSE( progression.GigOpen( *club, profile ) );
    CHECK_FALSE( progression.VenueOpen( "club", profile ) );
    CHECK( progression.VenueOpen( "Backyard", profile ) );  // no gate

    profile.RecordLesson( Lesson( "singles" ), 60, 95.0 );
    profile.RecordLesson( Lesson( "doubles" ), 60, 95.0 );
    profile.CompletedGigs.insert( "backyard" );
    std::vector<ProgressionUnlock> unlocks = progression.Evaluate( profile );
    CHECK( profile.HideoutTier == 1 );
    CHECK( Has( unlocks, "tier", "garage" ) );
    CHECK( Has( unlocks, "item", "rug" ) );
    CHECK( Has( unlocks, "item", "flyer" ) );
    CHECK( Has( unlocks, "gig", "club" ) );
    CHECK( progression.GigOpen( *club, profile ) );

    profile.CompletedGigs.insert( "club" );
    unlocks = progression.Evaluate( profile );
    CHECK( Has( unlocks, "venue", "Club" ) );
    CHECK( progression.VenueOpen( "CLUB", profile ) );

    // Never moves back down.
    profile.CompletedGigs.clear();
    progression.Evaluate( profile );
    CHECK( profile.HideoutTier == 1 );
}


TEST_CASE( "Progression: milestones read the songs, and --unlock-all opens everything" )
{
    Progression progression( Journey() );
    PlayerProfile profile( "" );
    PlayerProfile::SongResult result;
    result.Score = 100;
    result.Accuracy = 100.0;
    result.MaxCombo = 10;
    result.TotalNotes = 10;
    profile.RecordSong( "Song", result );
    CHECK( Has( progression.Evaluate( profile ), "item", "plaque" ) );

    PlayerProfile fresh( "" );
    progression.UnlockAll = true;
    CHECK( progression.LessonOpen( "rock", fresh ) );
    CHECK( progression.VenueOpen( "Club", fresh ) );
    CHECK( progression.GigOpen( *progression.FindGig( "club" ), fresh ) );
}


TEST_CASE( "Progression: an item says how it's got, with what's still missing" )
{
    Progression progression( Journey() );
    PlayerProfile profile( "" );
    CHECK( progression.HowToUnlock( "radio", profile ) == "Comes with the Basement" );
    CHECK( progression.HowToUnlock( "rug", profile ) == "Move into the Garage: play Backyard" );
    CHECK( progression.HowToUnlock( "pad", profile ) == "Pass Rudiments I on the practice pad (0 of 2 lessons)" );
    profile.SetLessonPassed( "singles", true );
    CHECK( progression.HowToUnlock( "pad", profile ) == "Pass Rudiments I on the practice pad (1 of 2 lessons)" );
    CHECK( progression.HowToUnlock( "flyer", profile ) == "Play Backyard (the gig board)" );
    CHECK( progression.HowToUnlock( "plaque", profile ) == "1 full combo (0 so far)" );
    CHECK( progression.HowToUnlock( "nothing", profile ).empty() );

    // A requirement in words: only what's still missing, joined up.
    ProgressionRequirement need;
    need.Tier = 1;
    need.Gigs = { "backyard" };
    need.LessonSteps = { "r1" };
    need.SongsPlayed = 3;
    CHECK( progression.Describe( need, profile ) == "move into the Garage, play Backyard, pass Rudiments I (1 of 2 lessons) and 3 songs played (0 so far)" );
    profile.HideoutTier = 1;
    profile.CompletedGigs.insert( "backyard" );
    profile.SetLessonPassed( "doubles", true );
    CHECK( progression.Describe( need, profile ) == "3 songs played (0 so far)" );
    need.SongsPlayed = 0;
    CHECK( progression.Describe( need, profile ).empty() );
}


TEST_CASE( "Progression: a setlist takes the named songs, then the range, the same every time" )
{
    const Progression progression( Journey() );
    std::vector<TrackData> tracks;
    tracks.push_back( Song( "Fast", 1000, 100.f ) );    // 10 nps
    tracks.push_back( Song( "Slow A", 200, 100.f ) );   // 2 nps
    tracks.push_back( Song( "Slow B", 300, 100.f ) );   // 3 nps
    tracks.push_back( Song( "Medium", 500, 100.f ) );   // 5 nps
    tracks.push_back( Song( "Empty", 0, 100.f ) );

    ProgressionGig gig = *progression.FindGig( "backyard" );
    std::vector<int> setlist = progression.Setlist( gig, tracks );
    REQUIRE( setlist.size() == 2 );
    CHECK( std::set<int>( setlist.begin(), setlist.end() ) == std::set<int>{ 1, 2 } );
    CHECK( progression.Setlist( gig, tracks ) == setlist );

    // Named songs first; the range widens to the nearest when it runs out.
    gig.SongKeys = { "Fast" };
    gig.Songs = 4;
    setlist = progression.Setlist( gig, tracks );
    REQUIRE( setlist.size() == 4 );
    CHECK( setlist[0] == 0 );
    CHECK( setlist[3] == 3 );  // Medium: 1 nps out of range, the last in
}


TEST_CASE( "Progression: the shipped journey names only lessons, items and gigs that exist" )
{
    // The tests run from the build's folder or the project's; look up from there for the game's Assets.
    std::filesystem::path root = std::filesystem::current_path();
    for( int up = 0; up < 8 && !std::filesystem::exists( root / "Assets/Progression/Progression.json" ) && root.has_parent_path() && root != root.parent_path(); ++up )
    {
        root = root.parent_path();
    }
    std::ifstream file( root / "Assets/Progression/Progression.json" );
    std::ifstream lessonsFile( root / "Assets/Practice/Lessons.json" );
    if( !file || !lessonsFile )
    {
        MESSAGE( "Progression.json or Lessons.json not reachable from the test's working folder; skipped" );
        return;
    }
    std::stringstream text;
    text << file.rdbuf();
    const Progression progression( json::parse( text.str() ) );
    std::stringstream lessonsText;
    lessonsText << lessonsFile.rdbuf();
    std::set<std::string> lessonIds;
    const json lessons = json::parse( lessonsText.str() );
    for( const json& lesson : lessons["Lessons"] )
    {
        lessonIds.insert( lesson["Id"].get<std::string>() );
    }

    CHECK( progression.Tiers().size() >= 2 );
    std::set<std::string> laddered;
    for( const ProgressionLessonStep& step : progression.LessonSteps() )
    {
        for( const std::string& lesson : step.Lessons )
        {
            CHECK_MESSAGE( lessonIds.count( lesson ) == 1, "step ", step.Id, " names an unknown lesson ", lesson );
            CHECK_MESSAGE( laddered.insert( lesson ).second, "lesson ", lesson, " is in two steps" );
        }
    }
    CHECK( laddered == lessonIds );
    const auto checkRewards = [&progression]( const std::vector<std::string>& inRewards ) {
        for( const std::string& id : inRewards )
        {
            CHECK_MESSAGE( progression.FindItem( id ), "unknown item ", id );
        }
    };
    for( const ProgressionTier& tier : progression.Tiers() )
    {
        checkRewards( tier.Rewards );
        for( const std::string& gig : tier.Requires.Gigs )
        {
            CHECK_MESSAGE( progression.FindGig( gig ), "unknown gig ", gig );
        }
    }
    for( const ProgressionGig& gig : progression.Gigs() )
    {
        checkRewards( gig.Rewards );
        CHECK( ( VenueStyleFromName( gig.Venue ) >= 0 || gig.Venue == "Backyard" ) );
    }
    for( const ProgressionLessonStep& step : progression.LessonSteps() )
    {
        checkRewards( step.Rewards );
    }
    for( const ProgressionMilestone& milestone : progression.Milestones() )
    {
        checkRewards( milestone.Rewards );
    }

    // Played straight through, every room, gig and step is reachable.
    PlayerProfile profile( "" );
    for( const std::string& lesson : lessonIds )
    {
        PracticeLesson passed;
        passed.Id = lesson;
        profile.RecordLesson( passed, 300, 100.0 );
    }
    for( const ProgressionGig& gig : progression.Gigs() )
    {
        progression.Evaluate( profile );
        CHECK_MESSAGE( progression.GigOpen( gig, profile ), "gig ", gig.Id, " never opens" );
        profile.CompletedGigs.insert( gig.Id );
    }
    progression.Evaluate( profile );
    CHECK( profile.HideoutTier == static_cast<int>( progression.Tiers().size() ) - 1 );
    for( const char* venue : { "Club", "Festival", "Arena", "Backyard" } )
    {
        CHECK( progression.VenueOpen( venue, profile ) );
    }
}


TEST_CASE( "Venues: free play skips a locked pick for an open room, else the first open scene" )
{
    std::vector<VenueEntry> registry( 1 );
    registry[0].Id = "Backyard";
    registry[0].ScenePath = "Assets/Venues/Backyard/Backyard.lvl";
    VenueChoiceInputs inputs;
    inputs.Registry = &registry;
    inputs.VenueStyle = 0;  // the Arena
    std::set<std::string> open = { "backyard" };
    inputs.VenueOpen = [&open]( const std::string& inId ) {
        std::string lower = inId;
        for( char& c : lower )
        {
            c = static_cast<char>( std::tolower( static_cast<unsigned char>( c ) ) );
        }
        return open.count( lower ) > 0;
    };
    VenueChoice choice = ChooseVenue( inputs );
    CHECK( choice.IsScene );
    CHECK( choice.Id == "Backyard" );

    open.insert( "club" );
    choice = ChooseVenue( inputs );
    CHECK_FALSE( choice.IsScene );
    CHECK( choice.Style == 1 );

    // A gig's venue isn't gated.
    inputs.GigVenue = "Arena";
    choice = ChooseVenue( inputs );
    CHECK_FALSE( choice.IsScene );
    CHECK( choice.Style == 0 );
}


TEST_CASE( "Gigs: the set's average of each song's best decides it, and it forces its venue" )
{
    const Progression progression( Journey() );
    const ProgressionGig& gig = *progression.FindGig( "backyard" );
    GigSession session;
    REQUIRE( session.Begin( gig, { 4, 7 } ) );
    CHECK( VenueRegistry::GigVenue() == "Backyard" );
    CHECK( session.CurrentTrack() == 4 );
    CHECK_FALSE( session.RecordSong( 7, 99.0 ) );  // not the song being played
    CHECK_FALSE( session.RecordSong( 4, 40.0 ) );
    CHECK_FALSE( session.RecordSong( 4, 60.0 ) );  // a retry: the better one counts
    CHECK_FALSE( session.SetDone() );
    // Moving on without launching (no scene loads in a test).
    PlayerProfile profile( "" );
    session.End();
    CHECK( VenueRegistry::GigVenue().empty() );

    // One song, 70% needed (the default): 65 isn't enough, a retry at 75 is, and completes it once.
    REQUIRE( session.Begin( gig, { 4 } ) );
    CHECK( session.IsLastSong() );
    CHECK( session.RecordSong( 4, 65.0 ) );
    CHECK_FALSE( session.Passed() );
    CHECK_FALSE( session.Complete( profile ) );
    CHECK( session.RecordSong( 4, 75.0 ) );
    CHECK( session.Passed() );
    CHECK( session.Complete( profile ) );
    CHECK_FALSE( session.Complete( profile ) );
    CHECK( profile.CompletedGigs.count( "backyard" ) == 1 );
    session.End();
}
