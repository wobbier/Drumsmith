#include "CoreGame/Calibration.h"
#include "CoreGame/Practice.h"
#include "Config/GameSettings.h"
#include "Editor/PadBindings.h"
#include "CLog.h"
#include "Path.h"
#include <algorithm>
#include <cmath>
#include <filesystem>

namespace
{
    // Beside the practice click tracks; the name carries the layout, so a changed layout never
    // reuses an old file.
    constexpr const char* kClickFolder = ".tmp/Practice/";
}


TrackData Calibration::BuildChart()
{
    const double beatSeconds = kBeatMs / 1000.0;
    TrackData chart;
    chart.m_calibration = true;
    chart.m_trackName = "Calibration";
    chart.m_artistName = "Hit any pad, or any key bound to one";
    chart.m_albumName = "Drumsmith";
    chart.m_dlcSource = "DS";
    chart.m_bpm = kBpm;
    chart.m_noteSpeed = 10.f;
    chart.m_duration = static_cast<float>( kTotalBeats * beatSeconds );
    chart.m_durationMS = chart.m_duration * 1000.f;
    for( int beat = 0; beat < kPartBeats; ++beat )
    {
        const double seconds = ( kWatchFirstBeat + beat ) * beatSeconds;
        NoteData note;
        note.m_editorLane = PadId::Snare;
        note.m_noteName = PadUtils::GetPadId( PadId::Snare );
        note.m_triggerTime = static_cast<float>( seconds );
        note.m_triggerTimeMS = static_cast<uint32_t>( std::lround( seconds * 1000.0 ) );
        note.m_velocity = 100;
        chart.m_noteData.push_back( note );
    }
    chart.m_noteCount = static_cast<int>( chart.m_noteData.size() );
    return chart;
}


Calibration::Part Calibration::PartAt( double inTimeMs )
{
    // Listening starts once the last note is out of reach, a little before the first click.
    return inTimeMs < ( kListenFirstBeat - 2.5 ) * kBeatMs ? Part::Watch : Part::Listen;
}


double Calibration::BeatTimeMs( Part inPart, int inBeat )
{
    return ( ( inPart == Part::Watch ? kWatchFirstBeat : kListenFirstBeat ) + inBeat ) * kBeatMs;
}


bool Calibration::Begin()
{
    m_active = false;
    m_samples = {};
    m_chart = BuildChart();
    const double seconds = kTotalBeats * kBeatMs / 1000.0;
    const std::string name = "calibration_" + std::to_string( kBpm ) + "bpm_from" + std::to_string( kListenFirstBeat ) + "_" + std::to_string( kPartBeats ) + "clicks_" + std::to_string( kTotalBeats ) + "beats.wav";
    const Path folder( kClickFolder );
    const std::string file = folder.FullPath + ( !folder.FullPath.empty() && folder.FullPath.back() == '/' ? "" : "/" ) + name;
    std::error_code error;
    // Every click the same: there are no bars to count here.
    if( !std::filesystem::is_regular_file( file, error ) && !Practice::WriteClickTrack( file, kBpm, 1, seconds, kListenFirstBeat, kPartBeats ) )
    {
        YIKES( "Calibration: couldn't write the click track to " + file );
        return false;
    }
    m_chart.m_trackFileName = name;
    m_chart.m_trackSourcePath = file;
    m_active = true;
    return true;
}


bool Calibration::AddTap( double inTimeMs )
{
    const Part part = PartAt( inTimeMs );
    const int beat = static_cast<int>( std::lround( ( inTimeMs - BeatTimeMs( part, 0 ) ) / kBeatMs ) );
    if( beat < 0 || beat >= kPartBeats )
    {
        return false;
    }
    const double offset = inTimeMs - BeatTimeMs( part, beat );
    if( std::fabs( offset ) > kReachMs )
    {
        return false;
    }
    if( beat >= kWarmUpBeats )
    {
        Samples& samples = m_samples[static_cast<size_t>( part )];
        samples.OffsetMs[static_cast<size_t>( beat - kWarmUpBeats )] = offset;
        samples.Has[static_cast<size_t>( beat - kWarmUpBeats )] = true;
    }
    return true;
}


int Calibration::Measured( Part inPart ) const
{
    const Samples& samples = m_samples[static_cast<size_t>( inPart )];
    return static_cast<int>( std::count( samples.Has.begin(), samples.Has.end(), true ) );
}


Calibration::Result Calibration::ResultOf( Part inPart ) const
{
    const Samples& samples = m_samples[static_cast<size_t>( inPart )];
    std::vector<double> offsets;
    for( size_t i = 0; i < samples.Has.size(); ++i )
    {
        if( samples.Has[i] )
        {
            offsets.push_back( samples.OffsetMs[i] );
        }
    }
    return Summarise( std::move( offsets ) );
}


Calibration::Result Calibration::Summarise( std::vector<double> inOffsetsMs )
{
    Result result;
    result.Samples = static_cast<int>( inOffsetsMs.size() );
    if( inOffsetsMs.empty() )
    {
        return result;
    }
    // The median: one flubbed hit doesn't drag it the way it drags a mean.
    std::sort( inOffsetsMs.begin(), inOffsetsMs.end() );
    const size_t middle = inOffsetsMs.size() / 2;
    result.OffsetMs = inOffsetsMs.size() % 2 == 1 ? inOffsetsMs[middle] : ( inOffsetsMs[middle - 1] + inOffsetsMs[middle] ) * 0.5;
    double spread = 0.0;
    for( double offset : inOffsetsMs )
    {
        spread += std::fabs( offset - result.OffsetMs );
    }
    result.SpreadMs = spread / static_cast<double>( inOffsetsMs.size() );
    return result;
}


int Calibration::SettingFor( const Result& inResult )
{
    return std::clamp( static_cast<int>( std::lround( inResult.OffsetMs ) ), 0, GameSettings::kMaxLatencyMs );
}


std::string Calibration::ValueText( const Result& inResult )
{
    return inResult.Valid() ? std::to_string( SettingFor( inResult ) ) + " ms" : std::string( "--" );
}


std::string Calibration::Remark( const Result& inResult )
{
    const std::string hits = std::to_string( inResult.Samples ) + " of " + std::to_string( kMeasuredBeats ) + " hits";
    if( !inResult.Valid() )
    {
        return hits + " counted: not enough to go on";
    }
    const int measured = static_cast<int>( std::lround( inResult.OffsetMs ) );
    std::string remark = hits + ", " + std::to_string( static_cast<int>( std::lround( inResult.SpreadMs ) ) ) + " ms apart";
    if( !inResult.Steady() )
    {
        remark += ": uneven, worth another go";
    }
    // The settings only delay: hits ahead of the beat, or later than the settings reach, are said.
    if( measured < 0 )
    {
        remark += "; you were " + std::to_string( -measured ) + " ms ahead, so no delay";
    }
    else if( measured > GameSettings::kMaxLatencyMs )
    {
        remark += "; measured " + std::to_string( measured ) + " ms, more than the setting holds";
    }
    return remark;
}


bool Calibration::Apply( GameSettings& ioSettings ) const
{
    const Result video = ResultOf( Part::Watch );
    const Result audio = ResultOf( Part::Listen );
    if( video.Valid() )
    {
        ioSettings.VideoLatency = SettingFor( video );
    }
    if( audio.Valid() )
    {
        ioSettings.AudioLatency = SettingFor( audio );
    }
    return video.Valid() || audio.Valid();
}
