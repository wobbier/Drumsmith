#pragma once
#include "CoreGame/TrackList.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <string>
#include <vector>

// Small helpers the venue's parts share (Docs/Venue-and-Band.md).
namespace VenueTiming
{
    // The song's beat at a time: a continuous count from the chart's tempo map (or its BPM), and
    // the beat's place in its measure.
    inline void BeatAt( const std::vector<BeatData>& inBeats, float inBpm, double inSeconds, double& outBeat, int& outMeasureBeat )
    {
        if( inBeats.size() >= 2 )
        {
            auto it = std::upper_bound( inBeats.begin(), inBeats.end(), static_cast<float>( inSeconds ), []( float t, const BeatData& b ) { return t < b.m_time; } );
            size_t index = it == inBeats.begin() ? 0 : static_cast<size_t>( it - inBeats.begin() ) - 1;
            index = std::min( index, inBeats.size() - 2 );
            const double span = std::max( 0.01, static_cast<double>( inBeats[index + 1].m_time - inBeats[index].m_time ) );
            outBeat = static_cast<double>( index ) + ( inSeconds - inBeats[index].m_time ) / span;
            outMeasureBeat = 0;
            for( size_t i = index; i > 0 && !inBeats[i].m_measure; --i )
            {
                ++outMeasureBeat;
            }
            return;
        }
        outBeat = inSeconds * inBpm / 60.0;
        const long long whole = static_cast<long long>( std::floor( outBeat ) );
        outMeasureBeat = static_cast<int>( ( ( whole % 4 ) + 4 ) % 4 );
    }

    // The latest cue at or before inSeconds, or null.
    inline const TimedCueData* CueAt( const std::vector<TimedCueData>& inCues, double inSeconds, size_t* outIndex = nullptr )
    {
        auto it = std::upper_bound( inCues.begin(), inCues.end(), inSeconds, []( double t, const TimedCueData& c ) { return t < c.m_time; } );
        if( it == inCues.begin() )
        {
            return nullptr;
        }
        if( outIndex ) *outIndex = static_cast<size_t>( it - inCues.begin() ) - 1;
        return &*( it - 1 );
    }

    // The index of the first time after inSeconds in a sorted list.
    inline size_t After( const std::vector<float>& inTimes, double inSeconds )
    {
        return static_cast<size_t>( std::upper_bound( inTimes.begin(), inTimes.end(), static_cast<float>( inSeconds ) ) - inTimes.begin() );
    }

    // A repeatable pseudo-random value in [0, 1).
    inline float Noise( uint32_t inA, uint32_t inB = 0 )
    {
        uint32_t h = inA * 374761393u + inB * 668265263u + 0x9E3779B9u;
        h = ( h ^ ( h >> 13 ) ) * 1274126177u;
        return static_cast<float>( ( h ^ ( h >> 16 ) ) & 0xFFFF ) / 65536.f;
    }

    inline bool Contains( const std::string& inText, const char* inWord )
    {
        return inText.find( inWord ) != std::string::npos;
    }

    inline float Smooth( float inT )
    {
        inT = std::clamp( inT, 0.f, 1.f );
        return inT * inT * ( 3.f - 2.f * inT );
    }
}
