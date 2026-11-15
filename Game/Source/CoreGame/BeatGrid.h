#pragma once
#include "CoreGame/TrackList.h"
#include <vector>

// The chart's beat grid as math: where beats and their subdivisions fall, and the nearest one to a
// time. Works from the chart's tempo map (TrackData::m_beats), or its BPM in 4/4 when it has none.
// Beats are counted from the first beat of the map (or from 0 s), fractional between beats and
// carried on at the edge tempo before the first and after the last.
namespace BeatGrid
{
    struct Line
    {
        double Time = 0.0;
        // 0: a measure line, 1: a beat, 2: a subdivision.
        int Level = 0;
    };

    double BeatOfTime( const std::vector<BeatData>& inBeats, float inBpm, double inSeconds );
    double TimeOfBeat( const std::vector<BeatData>& inBeats, float inBpm, double inBeat );

    // The nearest grid time to inSeconds, at inDivision steps per beat (1 beats, 2 eighths in 4/4,
    // 3 triplets, 4 sixteenths). Never negative.
    double Snap( const std::vector<BeatData>& inBeats, float inBpm, double inSeconds, int inDivision );

    // The grid lines in [inStart, inEnd], in time order.
    void GridLines( const std::vector<BeatData>& inBeats, float inBpm, double inStart, double inEnd, int inDivision, std::vector<Line>& outLines );

    // A constant-tempo map from inStart to inEnd, a measure line every inBeatsPerMeasure beats.
    std::vector<BeatData> Generate( float inBpm, int inBeatsPerMeasure, double inStart, double inEnd );
}
