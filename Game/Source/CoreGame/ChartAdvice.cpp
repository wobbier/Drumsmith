#include "CoreGame/ChartAdvice.h"
#include "CoreGame/TrackList.h"
#include "Editor/PadBindings.h"
#include <algorithm>
#include <array>

std::vector<KickFeet::Foot> KickFeet::Assign( const std::vector<double>& inTimesMs, const std::vector<bool>& inSecondPedal )
{
    const size_t count = inTimesMs.size();
    std::vector<Foot> feet( count, Foot::Either );
    const auto marked = [&inSecondPedal]( size_t i ) { return i < inSecondPedal.size() && inSecondPedal[i]; };
    bool charted = false;
    for( size_t i = 0; i < count && !charted; ++i )
    {
        charted = marked( i );
    }
    if( charted )
    {
        for( size_t i = 0; i < count; ++i )
        {
            if( !marked( i ) )
            {
                continue;
            }
            feet[i] = Foot::Left;
            if( i > 0 && !marked( i - 1 ) && inTimesMs[i] - inTimesMs[i - 1] <= kSecondPedalPairMs )
            {
                feet[i - 1] = Foot::Right;
            }
            if( i + 1 < count && !marked( i + 1 ) && inTimesMs[i + 1] - inTimesMs[i] <= kSecondPedalPairMs )
            {
                feet[i + 1] = Foot::Right;
            }
        }
        return feet;
    }
    for( size_t begin = 0; begin < count; )
    {
        size_t end = begin + 1;
        while( end < count && inTimesMs[end] - inTimesMs[end - 1] <= kDoubleBassGapMs )
        {
            ++end;
        }
        if( end - begin >= 3 )
        {
            for( size_t i = begin; i < end; ++i )
            {
                feet[i] = ( i - begin ) % 2 == 0 ? Foot::Right : Foot::Left;
            }
        }
        begin = end;
    }
    return feet;
}


namespace
{
    std::string Joined( const std::vector<std::string>& inParts )
    {
        std::string text;
        for( const std::string& part : inParts )
        {
            text += ( text.empty() ? "" : ", " ) + part;
        }
        return text;
    }
}


std::vector<std::string> ChartAdvice::Build( const TrackData& inTrack )
{
    std::vector<std::string> advice;
    std::array<int, PadId::COUNT> perPad{};
    std::array<int, static_cast<size_t>( Articulation::Count )> perStroke{};
    std::vector<std::pair<double, bool>> kicks;
    for( const NoteData& note : inTrack.m_noteData )
    {
        if( note.m_editorLane < 0 || note.m_editorLane >= PadId::COUNT )
        {
            continue;
        }
        ++perPad[note.m_editorLane];
        ++perStroke[static_cast<size_t>( note.m_articulation )];
        if( note.m_editorLane == PadId::Bass )
        {
            kicks.emplace_back( static_cast<double>( note.m_triggerTime ) * 1000.0, note.m_secondPedal );
        }
    }

    std::sort( kicks.begin(), kicks.end() );
    std::vector<double> times;
    std::vector<bool> marks;
    for( const auto& [time, mark] : kicks )
    {
        times.push_back( time );
        marks.push_back( mark );
    }
    const std::vector<KickFeet::Foot> feet = KickFeet::Assign( times, marks );
    const int leftFoot = static_cast<int>( std::count( feet.begin(), feet.end(), KickFeet::Foot::Left ) );
    // A stray fast triplet isn't a reason to buy a pedal; a song with real runs is.
    if( leftFoot >= 8 )
    {
        advice.push_back( "Double bass pedal recommended (" + std::to_string( leftFoot ) + " kicks for the second pedal)" );
    }

    std::vector<std::string> kit;
    if( perPad[PadId::Crash2] > 0 ) kit.push_back( "second crash" );
    if( perPad[PadId::Splash] > 0 ) kit.push_back( "splash" );
    if( perPad[PadId::China] > 0 ) kit.push_back( "china" );
    if( perPad[PadId::HiHatPedal] > 0 ) kit.push_back( "hi-hat pedal" );
    if( !kit.empty() )
    {
        advice.push_back( "Kit: " + Joined( kit ) );
    }

    std::vector<std::string> technique;
    if( perPad[PadId::OpenHiHat] > 0 ) technique.push_back( "open hi-hat" );
    if( perStroke[static_cast<size_t>( Articulation::Rim )] > 0 ) technique.push_back( "rimshots" );
    if( perStroke[static_cast<size_t>( Articulation::CrossStick )] > 0 ) technique.push_back( "cross-stick" );
    if( perStroke[static_cast<size_t>( Articulation::Bell )] > 0 ) technique.push_back( "bell" );
    if( !technique.empty() )
    {
        advice.push_back( "Technique: " + Joined( technique ) );
    }
    return advice;
}


const std::vector<std::string>& ChartAdvice::For( TrackData& ioTrack )
{
    if( !ioTrack.m_adviceKnown )
    {
        // The library keeps charts unloaded (NoteHighwayCore loads the one being played), so read
        // this one into a copy rather than leave every browsed song's notes in memory.
        if( ioTrack.m_noteData.empty() )
        {
            TrackData chart = ioTrack;
            chart.LoadNoteData();
            ioTrack.m_advice = Build( chart );
            // Also only known from the chart file: whether it was charted in the Track Editor.
            ioTrack.m_authored = chart.m_authored;
        }
        else
        {
            ioTrack.m_advice = Build( ioTrack );
        }
        ioTrack.m_adviceKnown = true;
    }
    return ioTrack.m_advice;
}
