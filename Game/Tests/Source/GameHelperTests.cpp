#include <doctest/doctest.h>
#include "Config/GameSettings.h"
#include "CoreGame/Calibration.h"
#include "CoreGame/ChartAdvice.h"
#include "CoreGame/ClickTrack.h"
#include "CoreGame/Practice.h"
#include "CoreGame/TrackList.h"
#include "JSON.h"
#include "Midi/MidiDevice.h"
#include "UI/MusicLinks.h"
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iterator>

namespace
{
    NoteData Note( PadId inPad, float inSeconds, bool inSecondPedal = false )
    {
        NoteData note;
        note.m_editorLane = inPad;
        note.m_noteName = PadUtils::GetPadId( inPad );
        note.m_triggerTime = inSeconds;
        note.m_secondPedal = inSecondPedal;
        return note;
    }


    PracticeLesson Paradiddle()
    {
        PracticeLesson lesson;
        lesson.Name = "Single Paradiddle";
        lesson.StepsPerBeat = 4;
        lesson.Sticking = ">Rlrr >Lrll >Rlrr >Lrll";
        return lesson;
    }
}


TEST_CASE( "Double bass: marked kicks are the left foot's and their neighbours the right's" )
{
    // 96 95 96 95 at 100 ms, then a lone kick two seconds on.
    const std::vector<double> times = { 1000.0, 1100.0, 1200.0, 1300.0, 3300.0 };
    const std::vector<bool> marks = { false, true, false, true, false };
    const std::vector<KickFeet::Foot> feet = KickFeet::Assign( times, marks );
    REQUIRE( feet.size() == 5 );
    CHECK( feet[0] == KickFeet::Foot::Right );
    CHECK( feet[1] == KickFeet::Foot::Left );
    CHECK( feet[2] == KickFeet::Foot::Right );
    CHECK( feet[3] == KickFeet::Foot::Left );
    CHECK( feet[4] == KickFeet::Foot::Either );
}


TEST_CASE( "Double bass: an unmarked chart alternates runs of three or more fast kicks" )
{
    // Two quick kicks (one foot), a gap, then a run of four.
    const std::vector<double> times = { 0.0, 120.0, 1000.0, 1100.0, 1200.0, 1300.0, 2000.0 };
    const std::vector<KickFeet::Foot> feet = KickFeet::Assign( times, {} );
    REQUIRE( feet.size() == 7 );
    CHECK( feet[0] == KickFeet::Foot::Either );
    CHECK( feet[1] == KickFeet::Foot::Either );
    CHECK( feet[2] == KickFeet::Foot::Right );
    CHECK( feet[3] == KickFeet::Foot::Left );
    CHECK( feet[4] == KickFeet::Foot::Right );
    CHECK( feet[5] == KickFeet::Foot::Left );
    CHECK( feet[6] == KickFeet::Foot::Either );
}


TEST_CASE( "Chart advice: a double bass song, its kit and its techniques" )
{
    TrackData track;
    for( int i = 0; i < 20; ++i )
    {
        track.m_noteData.push_back( Note( PadId::Bass, 1.f + 0.1f * static_cast<float>( i ), i % 2 == 1 ) );
    }
    track.m_noteData.push_back( Note( PadId::China, 4.f ) );
    track.m_noteData.push_back( Note( PadId::OpenHiHat, 4.5f ) );
    NoteData rim = Note( PadId::Snare, 5.f );
    rim.m_articulation = Articulation::Rim;
    track.m_noteData.push_back( rim );

    const std::vector<std::string> advice = ChartAdvice::Build( track );
    REQUIRE( advice.size() == 3 );
    CHECK( advice[0].find( "Double bass pedal recommended" ) == 0 );
    CHECK( advice[0].find( "10 kicks" ) != std::string::npos );
    CHECK( advice[1] == "Kit: china" );
    CHECK( advice[2] == "Technique: open hi-hat, rimshots" );

    // A plain rock beat asks for nothing.
    TrackData plain;
    plain.m_noteData = { Note( PadId::Bass, 1.f ), Note( PadId::Snare, 1.5f ), Note( PadId::ClosedHiHat, 1.5f ) };
    CHECK( ChartAdvice::Build( plain ).empty() );
}


TEST_CASE( "The second pedal mark and the start marker round-trip" )
{
    TrackData track;
    track.m_noteData = { Note( PadId::Bass, 1.f ), Note( PadId::Bass, 1.1f, true ) };
    track.m_startTime = 2.25f;
    json notes;
    track.OnSaveNoteData( notes );
    json meta;
    track.OnSaveTrackData( meta );

    TrackData loaded;
    loaded.OnLoadNoteData( notes );
    loaded.OnLoadTrackData( meta );
    REQUIRE( loaded.m_noteData.size() == 2 );
    CHECK_FALSE( loaded.m_noteData[0].m_secondPedal );
    CHECK( loaded.m_noteData[1].m_secondPedal );
    CHECK( loaded.m_startTime == doctest::Approx( 2.25f ) );

    // A chart without a marker doesn't write one.
    TrackData unmarked;
    json unmarkedMeta;
    unmarked.OnSaveTrackData( unmarkedMeta );
    CHECK_FALSE( unmarkedMeta.contains( "StartTime" ) );
}


TEST_CASE( "Source tags map to one filter in any case, and unknown ones to Other" )
{
    CHECK( TrackDatabase::FilterForSource( "DS" ) == TrackListFilter::Drumsmith );
    CHECK( TrackDatabase::FilterForSource( "ds" ) == TrackListFilter::Drumsmith );
    CHECK( TrackDatabase::FilterForSource( " rb3dlc" ) == TrackListFilter::RockBand3 );
    CHECK( TrackDatabase::FilterForSource( "GHWT" ) == TrackListFilter::GuitarHeroWorldTour );
    CHECK( TrackDatabase::FilterForSource( "" ) == TrackListFilter::Other );
    CHECK( TrackDatabase::FilterForSource( "somebody's pack" ) == TrackListFilter::Other );
    CHECK( std::string( TrackDatabase::SourceBadge( TrackListFilter::RockBand2 ) ) == "RB2" );
    CHECK( std::string( TrackDatabase::SourceBadge( TrackListFilter::Other ) ).empty() );
}


TEST_CASE( "DLC server addresses are trimmed and lose their trailing slashes" )
{
    CHECK( GameSettings::CleanServer( "  dlc.example.com/ \n" ) == "dlc.example.com" );
    CHECK( GameSettings::CleanServer( "https://dlc.example.com/songs//" ) == "https://dlc.example.com/songs" );
    CHECK( GameSettings::CleanServer( "   " ).empty() );
}


TEST_CASE( "A MIDI device is the same one when only its port numbers changed" )
{
    CHECK( MidiDevice::SameDevice( "TD-17:TD-17 MIDI 1 28:0", "TD-17:TD-17 MIDI 1 32:0" ) );
    CHECK( MidiDevice::SameDevice( "TD-17 1", "TD-17 2" ) );
    CHECK( MidiDevice::SameDevice( "TD-17", "TD-17" ) );
    CHECK_FALSE( MidiDevice::SameDevice( "TD-17:TD-17 MIDI 1 28:0", "Scarlett 4i4 USB:Scarlett 4i4 USB MIDI 1 28:0" ) );
    CHECK_FALSE( MidiDevice::SameDevice( "", "TD-17" ) );
}


TEST_CASE( "A click track has each click on its own sample and silence between" )
{
    const std::string file = ( std::filesystem::temp_directory_path() / "drumsmith_click_test.wav" ).string();
    constexpr int kRate = 22050;
    REQUIRE( ClickTrack::Write( file, { { 0.5, true }, { 1.25, false }, { 9.0, false } }, 2.0, kRate ) );
    std::ifstream in( file, std::ios::binary );
    const std::vector<char> bytes( ( std::istreambuf_iterator<char>( in ) ), std::istreambuf_iterator<char>() );
    in.close();
    std::filesystem::remove( file );
    // A 44-byte header, then two seconds of 16-bit mono.
    REQUIRE( bytes.size() == 44u + 2u * kRate * 2u );
    const auto sample = [&bytes]( size_t inIndex ) {
        return static_cast<int16_t>( static_cast<uint8_t>( bytes[44 + inIndex * 2] ) | ( static_cast<uint8_t>( bytes[45 + inIndex * 2] ) << 8 ) );
    };
    const auto firstSound = [&sample]( size_t inFrom, size_t inTo ) {
        for( size_t i = inFrom; i < inTo; ++i )
        {
            if( sample( i ) != 0 )
            {
                return i;
            }
        }
        return inTo;
    };
    // Silence up to the first click, which starts within a sample of its time (its own first
    // sample is the sine's zero); the same for the second; the one past the end is left out.
    CHECK( firstSound( 0, 2 * kRate ) - kRate / 2 <= 1 );
    const size_t second = static_cast<size_t>( 1.25 * kRate + 0.5 );
    CHECK( firstSound( kRate / 2 + kRate / 10, 2 * kRate ) - second <= 1 );
}


TEST_CASE( "The calibration measures how late the hits land in each part" )
{
    const TrackData chart = Calibration::BuildChart();
    CHECK( chart.m_calibration );
    REQUIRE( chart.m_noteData.size() == static_cast<size_t>( Calibration::kPartBeats ) );
    // The notes are the Watch part's beats, and are over before the clicks start.
    CHECK( chart.m_noteData.front().m_triggerTime * 1000.0 == doctest::Approx( Calibration::BeatTimeMs( Calibration::Part::Watch, 0 ) ) );
    CHECK( chart.m_noteData.back().m_triggerTime * 1000.0 + Calibration::kReachMs < Calibration::BeatTimeMs( Calibration::Part::Listen, 0 ) - Calibration::kReachMs );
    CHECK( Calibration::PartAt( chart.m_noteData.back().m_triggerTime * 1000.0 + Calibration::kReachMs ) == Calibration::Part::Watch );
    CHECK( Calibration::PartAt( Calibration::BeatTimeMs( Calibration::Part::Listen, 0 ) - Calibration::kReachMs ) == Calibration::Part::Listen );

    Calibration session;
    // Every beat of both parts: 30 ms behind the notes, 70 ms behind the clicks.
    for( int beat = 0; beat < Calibration::kPartBeats; ++beat )
    {
        CHECK( session.AddTap( Calibration::BeatTimeMs( Calibration::Part::Watch, beat ) + 30.0 ) );
        CHECK( session.AddTap( Calibration::BeatTimeMs( Calibration::Part::Listen, beat ) + 70.0 ) );
    }
    // The warm-up beats count as hits but aren't measured.
    CHECK( session.Measured( Calibration::Part::Watch ) == Calibration::kMeasuredBeats );
    const Calibration::Result video = session.ResultOf( Calibration::Part::Watch );
    const Calibration::Result audio = session.ResultOf( Calibration::Part::Listen );
    CHECK( video.Steady() );
    CHECK( video.OffsetMs == doctest::Approx( 30.0 ) );
    CHECK( audio.OffsetMs == doctest::Approx( 70.0 ) );
    CHECK( Calibration::SettingFor( audio ) == 70 );
    // A hit between beats, or outside the parts, is nobody's.
    CHECK_FALSE( session.AddTap( Calibration::BeatTimeMs( Calibration::Part::Watch, 5 ) + Calibration::kBeatMs * 0.5 ) );
    CHECK_FALSE( session.AddTap( 0.0 ) );
    // A second hit for a beat replaces the first.
    CHECK( session.AddTap( Calibration::BeatTimeMs( Calibration::Part::Watch, 10 ) + 31.0 ) );
    CHECK( session.Measured( Calibration::Part::Watch ) == Calibration::kMeasuredBeats );

    GameSettings& settings = GameSettings::GetInstance();
    const int audioBefore = settings.AudioLatency;
    const int videoBefore = settings.VideoLatency;
    CHECK( session.Apply( settings ) );
    CHECK( settings.VideoLatency == 30 );
    CHECK( settings.AudioLatency == 70 );
    settings.AudioLatency = audioBefore;
    settings.VideoLatency = videoBefore;
}


TEST_CASE( "A calibration result is the median, and says when there is too little to go on" )
{
    // One wild hit doesn't move it.
    const Calibration::Result result = Calibration::Summarise( { 40.0, 42.0, 38.0, 41.0, 39.0, 40.0, 43.0, 37.0, 200.0 } );
    CHECK( result.Valid() );
    CHECK( result.OffsetMs == doctest::Approx( 40.0 ) );
    CHECK( Calibration::ValueText( result ) == "40 ms" );
    // Too few hits is no result, and applies nothing.
    const Calibration::Result few = Calibration::Summarise( { 40.0, 41.0 } );
    CHECK_FALSE( few.Valid() );
    CHECK( Calibration::ValueText( few ) == "--" );
    CHECK_FALSE( Calibration::Summarise( {} ).Valid() );
    // Hits ahead of the beat can't be made up for: the setting only delays.
    const Calibration::Result ahead = Calibration::Summarise( std::vector<double>( 10, -25.0 ) );
    CHECK( Calibration::SettingFor( ahead ) == 0 );
    // Scattered hits are a result, but not a steady one.
    const Calibration::Result scattered = Calibration::Summarise( { -90.0, 80.0, -70.0, 100.0, -60.0, 90.0, -80.0, 70.0 } );
    CHECK( scattered.Valid() );
    CHECK_FALSE( scattered.Steady() );
}


TEST_CASE( "A practice lesson becomes a chart: a bar of count-in, then the pattern" )
{
    const PracticeLesson lesson = Paradiddle();
    const TrackData chart = Practice::BuildChart( lesson, 120, 2 );
    // Two bars of sixteenths, starting after one bar (2 s at 120 BPM).
    REQUIRE( chart.m_noteData.size() == 32 );
    CHECK( chart.m_practice );
    CHECK( chart.m_bpm == 120 );
    CHECK( chart.m_noteData.front().m_triggerTime == doctest::Approx( 2.f ) );
    CHECK( chart.m_noteData[1].m_triggerTime == doctest::Approx( 2.125f ) );
    CHECK( chart.m_noteData.back().m_triggerTime == doctest::Approx( 6.f - 0.125f ) );
    // The accent leads each group of four; the rest are taps.
    CHECK( chart.m_noteData[0].m_velocity == 127 );
    CHECK( chart.m_noteData[1].m_velocity == 30 );
    CHECK( chart.m_noteData[4].m_velocity == 127 );
    for( const NoteData& note : chart.m_noteData )
    {
        CHECK( note.m_editorLane == PadId::Snare );
    }
    // The sticking rides the lyric line, a line a bar.
    REQUIRE( chart.m_venue.m_lyrics.size() == 32 );
    CHECK( chart.m_venue.m_lyrics[0].m_name == "R" );
    CHECK( chart.m_venue.m_lyrics[1].m_name == "l" );
    CHECK( chart.m_venue.m_lyrics[4].m_name == "L" );
    CHECK( chart.m_venue.m_vocalPhrases.size() == 2 );
    // A beat grid from the start to the end, a measure line every four beats.
    REQUIRE( chart.m_beats.size() >= 12 );
    CHECK( chart.m_beats[0].m_measure );
    CHECK_FALSE( chart.m_beats[1].m_measure );
    CHECK( chart.m_beats[4].m_measure );
}


TEST_CASE( "A flam is a quiet grace note just ahead of its stroke; a groove is its lanes" )
{
    PracticeLesson flams;
    flams.Name = "Flams";
    flams.StepsPerBeat = 1;
    flams.Sticking = "^R ^L ^R ^L";
    const TrackData flamChart = Practice::BuildChart( flams, 60, 1 );
    REQUIRE( flamChart.m_noteData.size() == 8 );
    CHECK( flamChart.m_noteData[0].m_velocity == 30 );
    CHECK( flamChart.m_noteData[1].m_velocity == 100 );
    CHECK( flamChart.m_noteData[1].m_triggerTime == doctest::Approx( 4.f ) );
    CHECK( flamChart.m_noteData[1].m_triggerTime - flamChart.m_noteData[0].m_triggerTime == doctest::Approx( 0.035f ).epsilon( 0.02 ) );
    CHECK( flamChart.m_venue.m_lyrics.size() == 4 );
    CHECK( flamChart.m_venue.m_lyrics[0].m_name == "lR" );

    PracticeLesson groove;
    groove.Name = "Rock";
    groove.StepsPerBeat = 2;
    groove.Lanes = { { "closed_hh", "xxxx xxxx" }, { "snare1", "--x- --x-" }, { "bass1", "x--- x---" } };
    const TrackData grooveChart = Practice::BuildChart( groove, 120, 1 );
    CHECK( grooveChart.m_noteData.size() == 12 );
    CHECK( std::count_if( grooveChart.m_noteData.begin(), grooveChart.m_noteData.end(), []( const NoteData& n ) { return n.m_editorLane == PadId::Bass; } ) == 2 );
    CHECK( grooveChart.m_venue.m_lyrics.empty() );
}


TEST_CASE( "Music links search for the artist and title unless the chart has its own" )
{
    using MusicLinks::Service;
    CHECK( MusicLinks::Url( Service::Spotify, " Foo Fighters", "Learn to Fly" ) == "https://open.spotify.com/search/Foo%20Fighters%20Learn%20to%20Fly" );
    CHECK( MusicLinks::Url( Service::AppleMusic, "AC/DC", "T.N.T." ) == "https://music.apple.com/search?term=AC%2FDC%20T.N.T." );
    CHECK( MusicLinks::Url( Service::YouTubeMusic, "", "Song 2" ) == "https://music.youtube.com/search?q=Song%202" );
    CHECK( MusicLinks::Url( Service::Spotify, "", "" ).empty() );
    const std::map<std::string, std::string> links = { { "Spotify", "https://open.spotify.com/track/abc" }, { "AppleMusic", "javascript:alert(1)" } };
    CHECK( MusicLinks::Url( Service::Spotify, "A", "B", links ) == "https://open.spotify.com/track/abc" );
    // Only web links are handed to the browser; anything else falls back to the search.
    CHECK( MusicLinks::Url( Service::AppleMusic, "A", "B", links ) == "https://music.apple.com/search?term=A%20B" );
}
