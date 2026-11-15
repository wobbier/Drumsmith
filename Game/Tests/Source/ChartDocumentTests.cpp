#include <doctest/doctest.h>
#include "Editor/Chart/ChartDocument.h"

#if USING( ME_EDITOR )

namespace
{
    // Four snare hits on the beat at 120 BPM, and a lighting cue.
    TrackData SmallChart()
    {
        TrackData track;
        track.m_bpm = 120;
        for( float time : { 0.f, 0.5f, 1.f, 1.5f } )
        {
            NoteData note;
            note.m_editorLane = PadId::Snare;
            note.m_noteName = PadUtils::GetPadId( PadId::Snare );
            note.m_triggerTime = time;
            track.m_noteData.push_back( note );
        }
        track.m_venue.m_lighting = { { 1.f, "verse" } };
        return track;
    }
}


TEST_CASE( "ChartDocument: a move is one undo step and the selection follows its notes" )
{
    ChartDocument document;
    document.OpenInMemory( SmallChart() );
    CHECK_FALSE( document.IsDirty() );

    // The first note, moved past the second.
    document.Selection.insert( { ChartDocument::kNoteTrack, 0 } );
    document.MoveSelection( 0.75, 1 );
    REQUIRE( document.Chart.m_noteData.size() == 4 );
    CHECK( document.Chart.m_noteData[0].m_triggerTime == doctest::Approx( 0.5f ) );
    CHECK( document.Chart.m_noteData[1].m_triggerTime == doctest::Approx( 0.75f ) );
    CHECK( document.Chart.m_noteData[1].m_editorLane == PadId::OpenHiHat );
    CHECK( document.Chart.m_noteData[1].m_triggerTimeMS == 750 );
    CHECK( document.IsSelected( ChartDocument::kNoteTrack, 1 ) );
    CHECK( document.IsDirty() );

    document.Undo();
    CHECK( document.Chart.m_noteData[0].m_triggerTime == doctest::Approx( 0.f ) );
    CHECK( document.Chart.m_noteData[0].m_editorLane == PadId::Snare );
    CHECK_FALSE( document.IsDirty() );
    document.Redo();
    CHECK( document.Chart.m_noteData[1].m_triggerTime == doctest::Approx( 0.75f ) );
}


TEST_CASE( "ChartDocument: add, delete, cut and paste across tracks" )
{
    ChartDocument document;
    document.OpenInMemory( SmallChart() );
    const int lighting = document.FindTrack( "Lighting" );
    REQUIRE( lighting > 0 );
    const uint32_t venueVersion = document.Version( ChartDomain::Venue );

    const int added = document.AddItem( lighting, 0.25, 0.25, 0 );
    CHECK( added == 0 );
    CHECK( document.Chart.m_venue.m_lighting.size() == 2 );
    CHECK( document.Version( ChartDomain::Venue ) != venueVersion );

    // The two notes and the cue at one second and after, cut and pasted two seconds on.
    document.Selection.clear();
    document.Selection.insert( { ChartDocument::kNoteTrack, 2 } );
    document.Selection.insert( { ChartDocument::kNoteTrack, 3 } );
    document.Selection.insert( { lighting, 1 } );
    document.Cut();
    CHECK( document.Chart.m_noteData.size() == 2 );
    CHECK( document.Chart.m_venue.m_lighting.size() == 1 );
    document.Paste( 3.0 );
    REQUIRE( document.Chart.m_noteData.size() == 4 );
    CHECK( document.Chart.m_noteData[2].m_triggerTime == doctest::Approx( 3.f ) );
    CHECK( document.Chart.m_noteData[3].m_triggerTime == doctest::Approx( 3.5f ) );
    CHECK( document.Chart.m_venue.m_lighting[1].m_time == doctest::Approx( 3.f ) );
    CHECK( document.Selection.size() == 3 );

    // Paste is one step back, the cut another.
    document.Undo();
    CHECK( document.Chart.m_noteData.size() == 2 );
    document.Undo();
    CHECK( document.Chart.m_noteData.size() == 4 );
    CHECK( document.Chart.m_venue.m_lighting.size() == 2 );
}


TEST_CASE( "ChartDocument: duplicate repeats the selection on the next beat, nudges follow the grid" )
{
    ChartDocument document;
    document.OpenInMemory( SmallChart() );
    document.Selection.insert( { ChartDocument::kNoteTrack, 0 } );
    document.Selection.insert( { ChartDocument::kNoteTrack, 1 } );
    document.Duplicate();
    // Beats 0 and 1 repeat at beats 1 and 2 (a beat is half a second), beside the notes there.
    REQUIRE( document.Chart.m_noteData.size() == 6 );
    CHECK( document.Selection.size() == 2 );

    document.Selection.clear();
    document.Selection.insert( { ChartDocument::kNoteTrack, 5 } );
    document.MoveSelectionBeats( 0.5, 0 );
    CHECK( document.Chart.m_noteData[5].m_triggerTime == doctest::Approx( 1.75f ) );
}


TEST_CASE( "ChartDocument: a cancelled edit leaves the chart and history alone" )
{
    ChartDocument document;
    document.OpenInMemory( SmallChart() );
    document.BeginEdit( ChartDocument::kNoteTrack );
    document.Tracks[ChartDocument::kNoteTrack]->Add( 9.0, 9.0, 0 );
    document.Tracks[ChartDocument::kNoteTrack]->Set( 0, 5.0, 5.0, 3 );
    document.CancelEdit();
    CHECK( document.Chart.m_noteData.size() == 4 );
    CHECK( document.Chart.m_noteData[0].m_triggerTime == doctest::Approx( 0.f ) );
    CHECK_FALSE( document.History.CanUndo() );
    CHECK_FALSE( document.IsDirty() );
}


TEST_CASE( "ChartDocument: spans keep their length when moved and their rows when they have them" )
{
    ChartDocument document;
    document.OpenInMemory( SmallChart() );
    const int starPower = document.FindTrack( "Star Power" );
    const int spotlights = document.FindTrack( "Spotlights" );
    REQUIRE( starPower > 0 );
    REQUIRE( spotlights > 0 );
    document.AddItem( starPower, 1.0, 3.0, 0 );
    document.AddItem( spotlights, 1.0, 2.0, 3 );
    CHECK( document.Chart.m_venue.m_spotlights[0].m_slot == 3 );
    document.Selection.insert( { starPower, 0 } );
    document.MoveSelection( 0.5, 1 );
    CHECK( document.Chart.m_starPower[0].m_start == doctest::Approx( 1.5f ) );
    CHECK( document.Chart.m_starPower[0].m_end == doctest::Approx( 3.5f ) );
    CHECK( document.Chart.m_venue.m_spotlights[0].m_slot == 4 );
    CHECK( document.Version( ChartDomain::Phrases ) > 1 );
}

#endif
