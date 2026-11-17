#pragma once
#include <cstdint>
#include <string>
#include <vector>

class TrackData;

// Which foot plays each kick of a chart, for charts with double bass (Docs/Gameplay-Note-Highway.md).
namespace KickFeet
{
    enum class Foot : uint8_t { Either, Right, Left };

    // Kicks this close together are double bass when three or more run on (unmarked charts).
    constexpr double kDoubleBassGapMs = 150.0;
    // A kick marked for the second pedal makes the kicks this close either side of it the
    // right foot's.
    constexpr double kSecondPedalPairMs = 260.0;

    // inTimesMs: the chart's kicks in time order. inSecondPedal: which of them the chart marks for
    // the second pedal (NoteData::m_secondPedal). Where a chart marks any, the marks decide: those
    // are the left foot's and their neighbours the right's. Without marks, a run of three or more
    // fast kicks alternates, right foot first; two quick kicks are one foot's.
    std::vector<Foot> Assign( const std::vector<double>& inTimesMs, const std::vector<bool>& inSecondPedal );
}

// What a chart asks of the player's kit and hands, for the song panel: "this song recommends a
// double bass pedal".
namespace ChartAdvice
{
    // From a chart's notes; empty when it asks for nothing beyond a basic kit.
    std::vector<std::string> Build( const TrackData& inTrack );
    // For a library entry: reads its NoteData.txt the first time and keeps the answer on the track.
    const std::vector<std::string>& For( TrackData& ioTrack );
}
