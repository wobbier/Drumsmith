#include <doctest/doctest.h>
#include "CoreGame/BeatGrid.h"
#include "CoreGame/CustomTrackDefineTest.h"
#include "CoreGame/TrackList.h"
#include "JSON.h"
#include "MidiFile.h"
#include <algorithm>
#include <sstream>

namespace
{
    // A chart with something in every list the files carry.
    TrackData FullTrack()
    {
        TrackData track;
        NoteData kick;
        kick.m_editorLane = PadId::Bass;
        kick.m_noteName = PadUtils::GetPadId( PadId::Bass );
        kick.m_triggerTime = 1.f;
        NoteData snare;
        snare.m_editorLane = PadId::Snare;
        snare.m_noteName = PadUtils::GetPadId( PadId::Snare );
        snare.m_triggerTime = 1.5f;
        snare.m_velocity = 30;
        snare.m_articulation = Articulation::Rim;
        track.m_noteData = { kick, snare };
        track.m_beats = { { 0.f, true }, { 0.5f, false }, { 1.f, false }, { 1.5f, false }, { 2.f, true } };
        track.m_starPower = { { 1.f, 2.f, 0 } };
        track.m_drumFills = { { 3.f, 4.f, 0 } };
        track.m_drumSolos = { { 5.f, 9.f, 0 } };
        track.m_authored = true;

        VenueData& venue = track.m_venue;
        const std::vector<TimedCueData> cues = { { 0.5f, "a" }, { 2.5f, "b" } };
        const std::vector<VenueData::SpanData> spans = { { 1.f, 2.f, 0 } };
        venue.m_lighting = cues;
        venue.m_keyframes = { { 1.f, VenueData::Keyframe::Previous } };
        venue.m_fog = { { 1.f, true }, { 2.f, false } };
        venue.m_bonusFx = { 3.f };
        venue.m_spotlights = { { 1.f, 2.f, 3 } };
        venue.m_sections = cues;
        venue.m_crowd = cues;
        venue.m_cameras = cues;
        venue.m_mvCameras = cues;
        venue.m_postFx = cues;
        venue.m_mvPostFx = cues;
        venue.m_singalong = { { 1.f, 2.f, 2 } };
        for( auto& states : venue.m_bandStates ) states = cues;
        venue.m_drumHits = { { 1.f, VenueData::Limb::LeftFoot, VenueData::DrumPiece::Kick, true } };
        venue.m_guitarStrums = { 1.f, 2.f };
        venue.m_bassStrums = { 1.f };
        venue.m_keysStrums = { 2.f };
        venue.m_vocalNotes = spans;
        venue.m_guitarFrets = { { 1.f, 1.f, 7 } };
        venue.m_bassFrets = { { 2.f, 2.f, 3 } };
        venue.m_guitarSolos = spans;
        venue.m_lyrics = cues;
        venue.m_vocalPhrases = spans;
        venue.m_vocalPercussion = { 4.f };
        venue.m_vocalCues = cues;
        for( auto& notes : venue.m_harmonyNotes ) notes = spans;
        for( auto& lyrics : venue.m_harmonyLyrics ) lyrics = cues;
        venue.m_guitarMaps = cues;
        venue.m_bassMaps = cues;
        venue.m_songEvents = cues;
        return track;
    }
}


TEST_CASE( "TrackData: a chart with every list survives save, load, save" )
{
    TrackData track = FullTrack();
    json first;
    track.OnSaveNoteData( first );

    TrackData loaded;
    loaded.OnLoadNoteData( first );
    json second;
    loaded.OnSaveNoteData( second );

    CHECK( first == second );
    CHECK( loaded.m_authored );
    REQUIRE( loaded.m_starPower.size() == 1 );
    CHECK( loaded.m_starPower[0].m_end == doctest::Approx( 2.f ) );
    REQUIRE( loaded.m_drumFills.size() == 1 );
    REQUIRE( loaded.m_drumSolos.size() == 1 );
    REQUIRE( loaded.m_noteData.size() == 2 );
    CHECK( loaded.m_noteData[1].m_velocity == 30 );
    CHECK( loaded.m_noteData[1].m_articulation == Articulation::Rim );
    CHECK( loaded.m_venue.m_spotlights[0].m_slot == 3 );
}


TEST_CASE( "TrackData: a chart from before drum phrases loads with none, and saves no new keys" )
{
    json old;
    old["Notes"].push_back( { { "EditorLane", 1 }, { "NoteName", PadUtils::GetPadId( PadId::Snare ) }, { "TriggerTime", 2.0 }, { "TriggerTimeMS", 2000 } } );
    TrackData track;
    track.OnLoadNoteData( old );
    CHECK( track.m_noteData.size() == 1 );
    CHECK( track.m_starPower.empty() );
    CHECK_FALSE( track.m_authored );

    json saved;
    track.OnSaveNoteData( saved );
    CHECK_FALSE( saved.contains( "StarPower" ) );
    CHECK_FALSE( saved.contains( "DrumFills" ) );
    CHECK_FALSE( saved.contains( "DrumSolos" ) );
    CHECK_FALSE( saved.contains( "Authored" ) );
}


TEST_CASE( "TrackData: notes placed without a millisecond stamp are not merged on save" )
{
    TrackData track;
    for( float time : { 1.f, 2.f, 3.f } )
    {
        NoteData note;
        note.m_editorLane = PadId::Snare;
        note.m_noteName = PadUtils::GetPadId( PadId::Snare );
        note.m_triggerTime = time;
        track.m_noteData.push_back( note );
    }
    json saved;
    track.OnSaveNoteData( saved );
    CHECK( saved["Notes"].size() == 3 );
}


TEST_CASE( "MIDI import: star power, drum solos and fills come from PART DRUMS" )
{
    smf::MidiFile midi;
    midi.absoluteTicks();
    midi.setTicksPerQuarterNote( 480 );
    const int track = midi.addTrack();
    midi.addTempo( 0, 0, 120.0 );
    midi.addTrackName( track, 0, "PART DRUMS" );
    // 120 BPM: 480 ticks is half a second.
    midi.addNoteOn( track, 960, 0, 116, 100 );
    midi.addNoteOff( track, 1920, 0, 116 );
    midi.addNoteOn( track, 1920, 0, 103, 100 );
    midi.addNoteOff( track, 3840, 0, 103 );
    for( int key = 120; key <= 124; ++key )
    {
        midi.addNoteOn( track, 4800, 0, key, 100 );
        midi.addNoteOff( track, 5760, 0, key );
    }
    midi.sortTracks();
    // Through the file format, as the importer reads charts (events learn their track on read).
    std::stringstream file;
    midi.write( file );
    smf::MidiFile read;
    REQUIRE( read.read( file ) );
    read.doTimeAnalysis();

    TrackData chart;
    chart.m_starPower = { { 9.f, 10.f, 0 } };
    CustomTrackDefineTest::ReadMidiDrumPhrases( read, track, chart );

    REQUIRE( chart.m_starPower.size() == 1 );
    CHECK( chart.m_starPower[0].m_start == doctest::Approx( 1.0 ) );
    CHECK( chart.m_starPower[0].m_end == doctest::Approx( 2.0 ) );
    REQUIRE( chart.m_drumSolos.size() == 1 );
    CHECK( chart.m_drumSolos[0].m_start == doctest::Approx( 2.0 ) );
    CHECK( chart.m_drumSolos[0].m_end == doctest::Approx( 4.0 ) );
    REQUIRE( chart.m_drumFills.size() == 1 );
    CHECK( chart.m_drumFills[0].m_start == doctest::Approx( 5.0 ) );
    CHECK( chart.m_drumFills[0].m_end == doctest::Approx( 6.0 ) );
}


TEST_CASE( "MIDI import: note 102 in PART DRUMS is the hi-hat pedal, beside Rock Band's gems" )
{
    smf::MidiFile midi;
    midi.absoluteTicks();
    midi.setTicksPerQuarterNote( 480 );
    const int track = midi.addTrack();
    midi.addTempo( 0, 0, 120.0 );
    midi.addTrackName( track, 0, "PART DRUMS" );
    // 120 BPM: 480 ticks is half a second. A crash with the foot under it, the foot alone, then
    // a five-lane chart's orange gem (101), which is not a pad here.
    const std::vector<std::pair<int, int>> notes = { { 960, 100 }, { 960, 102 }, { 1440, 102 }, { 1920, 101 }, { 1920, 97 } };
    for( const auto& [tick, key] : notes )
    {
        midi.addNoteOn( track, tick, 0, key, 100 );
        midi.addNoteOff( track, tick + 60, 0, key );
    }
    midi.sortTracks();
    std::stringstream file;
    midi.write( file );
    smf::MidiFile read;
    REQUIRE( read.read( file ) );
    read.doTimeAnalysis();

    TrackData chart;
    CustomTrackDefineTest::ReadMidiDrumNotes( read, track, true, chart );

    std::vector<std::pair<float, PadId>> found;
    for( const NoteData& note : chart.m_noteData )
    {
        found.push_back( { note.m_triggerTime, note.m_editorLane } );
    }
    std::sort( found.begin(), found.end() );
    REQUIRE( found.size() == 4 );
    CHECK( chart.m_noteCount == 4 );
    CHECK( found[0].first == doctest::Approx( 1.0 ) );
    CHECK( found[0].second == PadId::Crash1 );
    CHECK( found[1].first == doctest::Approx( 1.0 ) );
    CHECK( found[1].second == PadId::HiHatPedal );
    CHECK( found[2].first == doctest::Approx( 1.5 ) );
    CHECK( found[2].second == PadId::HiHatPedal );
    CHECK( found[3].second == PadId::Snare );

    // The pedal's notes survive the chart's own files.
    json saved;
    chart.OnSaveNoteData( saved );
    TrackData loaded;
    loaded.OnLoadNoteData( saved );
    int pedals = 0;
    for( const NoteData& note : loaded.m_noteData )
    {
        pedals += note.m_editorLane == PadId::HiHatPedal ? 1 : 0;
    }
    CHECK( pedals == 2 );
}


TEST_CASE( "BeatGrid: snapping follows a tempo change" )
{
    // Two beats at 120 BPM, then beats a second apart.
    const std::vector<BeatData> beats = { { 0.f, true }, { 0.5f, false }, { 1.f, false }, { 2.f, false }, { 3.f, true } };
    CHECK( BeatGrid::Snap( beats, 120.f, 0.3, 1 ) == doctest::Approx( 0.5 ) );
    CHECK( BeatGrid::Snap( beats, 120.f, 0.3, 2 ) == doctest::Approx( 0.25 ) );
    CHECK( BeatGrid::Snap( beats, 120.f, 1.6, 2 ) == doctest::Approx( 1.5 ) );
    CHECK( BeatGrid::Snap( beats, 120.f, 2.2, 4 ) == doctest::Approx( 2.25 ) );
    // Past the map, the last tempo carries on.
    CHECK( BeatGrid::Snap( beats, 120.f, 4.4, 2 ) == doctest::Approx( 4.5 ) );
    CHECK( BeatGrid::TimeOfBeat( beats, 120.f, BeatGrid::BeatOfTime( beats, 120.f, 1.37 ) ) == doctest::Approx( 1.37 ) );
}


TEST_CASE( "BeatGrid: without a tempo map the grid is the BPM in 4/4" )
{
    const std::vector<BeatData> none;
    CHECK( BeatGrid::Snap( none, 120.f, 0.74, 1 ) == doctest::Approx( 0.5 ) );
    CHECK( BeatGrid::Snap( none, 120.f, 0.74, 2 ) == doctest::Approx( 0.75 ) );

    std::vector<BeatGrid::Line> lines;
    BeatGrid::GridLines( none, 120.f, 0.0, 2.0, 2, lines );
    REQUIRE( lines.size() == 9 );
    CHECK( lines[0].Level == 0 );
    CHECK( lines[1].Level == 2 );
    CHECK( lines[2].Level == 1 );
    CHECK( lines[8].Level == 0 );

    const std::vector<BeatData> made = BeatGrid::Generate( 60.f, 3, 1.0, 5.0 );
    REQUIRE( made.size() == 5 );
    CHECK( made[0].m_measure );
    CHECK_FALSE( made[1].m_measure );
    CHECK( made[3].m_measure );
}
