#include "CoreGame/BeatGrid.h"
#include "Venue/VenueTiming.h"
#include <algorithm>
#include <cmath>

namespace
{
    float SafeBpm( float inBpm )
    {
        return inBpm > 1.f ? inBpm : 120.f;
    }


    bool IsMeasure( const std::vector<BeatData>& inBeats, long long inBeat )
    {
        if( inBeats.size() >= 2 )
        {
            return inBeat >= 0 && inBeat < static_cast<long long>( inBeats.size() ) && inBeats[static_cast<size_t>( inBeat )].m_measure;
        }
        return ( ( inBeat % 4 ) + 4 ) % 4 == 0;
    }
}


double BeatGrid::BeatOfTime( const std::vector<BeatData>& inBeats, float inBpm, double inSeconds )
{
    double beat = 0.0;
    int measureBeat = 0;
    VenueTiming::BeatAt( inBeats, SafeBpm( inBpm ), inSeconds, beat, measureBeat );
    return beat;
}


double BeatGrid::TimeOfBeat( const std::vector<BeatData>& inBeats, float inBpm, double inBeat )
{
    if( inBeats.size() >= 2 )
    {
        const double last = static_cast<double>( inBeats.size() - 2 );
        const size_t index = static_cast<size_t>( std::clamp( std::floor( inBeat ), 0.0, last ) );
        const double span = std::max( 0.01, static_cast<double>( inBeats[index + 1].m_time - inBeats[index].m_time ) );
        return static_cast<double>( inBeats[index].m_time ) + ( inBeat - static_cast<double>( index ) ) * span;
    }
    return inBeat * 60.0 / SafeBpm( inBpm );
}


double BeatGrid::Snap( const std::vector<BeatData>& inBeats, float inBpm, double inSeconds, int inDivision )
{
    const double division = static_cast<double>( std::max( 1, inDivision ) );
    const double beat = std::round( BeatOfTime( inBeats, inBpm, inSeconds ) * division ) / division;
    return std::max( 0.0, TimeOfBeat( inBeats, inBpm, beat ) );
}


void BeatGrid::GridLines( const std::vector<BeatData>& inBeats, float inBpm, double inStart, double inEnd, int inDivision, std::vector<Line>& outLines )
{
    outLines.clear();
    if( inEnd < inStart )
    {
        return;
    }
    const int division = std::max( 1, inDivision );
    const long long first = static_cast<long long>( std::floor( BeatOfTime( inBeats, inBpm, inStart ) * division ) );
    const long long last = static_cast<long long>( std::ceil( BeatOfTime( inBeats, inBpm, inEnd ) * division ) );
    // A sane ceiling: a zoomed-out view asks for fewer divisions, not a million lines.
    if( last - first > 20000 )
    {
        return;
    }
    for( long long step = first; step <= last; ++step )
    {
        const double time = TimeOfBeat( inBeats, inBpm, static_cast<double>( step ) / division );
        if( time < inStart || time > inEnd || time < 0.0 )
        {
            continue;
        }
        Line line;
        line.Time = time;
        if( step % division != 0 )
        {
            line.Level = 2;
        }
        else
        {
            line.Level = IsMeasure( inBeats, step / division ) ? 0 : 1;
        }
        outLines.push_back( line );
    }
}


std::vector<BeatData> BeatGrid::Generate( float inBpm, int inBeatsPerMeasure, double inStart, double inEnd )
{
    std::vector<BeatData> beats;
    const double step = 60.0 / SafeBpm( inBpm );
    const int perMeasure = std::max( 1, inBeatsPerMeasure );
    for( int beat = 0; beat < 20000; ++beat )
    {
        const double time = inStart + step * beat;
        if( time > inEnd )
        {
            break;
        }
        beats.push_back( BeatData{ static_cast<float>( time ), beat % perMeasure == 0 } );
    }
    return beats;
}
