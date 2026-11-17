#include "CoreGame/ClickTrack.h"
#include "CLog.h"
#include "Path.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <filesystem>
#include <fstream>

namespace
{
    constexpr const char* kMetronomeFolder = ".tmp/Metronome/";
    // Half the usual rate: a song's worth of clicks is a long file, and a click doesn't need more.
    constexpr int kMetronomeRate = 22050;
    // A song's metronome is about 2.6 MB a minute; the folder keeps this many of them.
    constexpr size_t kMetronomesKept = 6;


    void PutLittle( std::vector<char>& outBytes, uint32_t inValue, int inBytes )
    {
        for( int i = 0; i < inBytes; ++i )
        {
            outBytes.push_back( static_cast<char>( ( inValue >> ( 8 * i ) ) & 0xFF ) );
        }
    }
}


bool ClickTrack::Write( const std::string& inFile, const std::vector<Click>& inClicks, double inSeconds, int inSampleRate )
{
    const int rate = std::max( 8000, inSampleRate );
    const size_t sampleCount = static_cast<size_t>( std::max( 1.0, inSeconds ) * rate );
    std::vector<int16_t> samples( sampleCount, 0 );
    constexpr double kClickSeconds = 0.03;
    constexpr double kPi = 3.14159265358979323846;
    const size_t clickSamples = static_cast<size_t>( kClickSeconds * rate );
    for( const Click& click : inClicks )
    {
        if( click.Seconds < 0.0 || click.Seconds >= inSeconds )
        {
            continue;
        }
        const size_t first = static_cast<size_t>( std::llround( click.Seconds * rate ) );
        const double pitch = click.Accent ? 1760.0 : 1175.0;
        const double level = click.Accent ? 0.7 : 0.5;
        for( size_t i = 0; i < clickSamples && first + i < sampleCount; ++i )
        {
            const double t = static_cast<double>( i ) / rate;
            const double envelope = std::exp( -t * 140.0 ) * std::min( 1.0, t * 2000.0 );
            samples[first + i] = static_cast<int16_t>( std::sin( 2.0 * kPi * pitch * t ) * envelope * level * 32767.0 );
        }
    }

    std::error_code error;
    std::filesystem::create_directories( std::filesystem::path( inFile ).parent_path(), error );
    std::ofstream file( inFile, std::ios::binary | std::ios::trunc );
    if( !file )
    {
        return false;
    }
    const uint32_t dataBytes = static_cast<uint32_t>( sampleCount * sizeof( int16_t ) );
    std::vector<char> bytes;
    bytes.reserve( 44 + dataBytes );
    bytes.insert( bytes.end(), { 'R', 'I', 'F', 'F' } );
    PutLittle( bytes, 36 + dataBytes, 4 );
    bytes.insert( bytes.end(), { 'W', 'A', 'V', 'E', 'f', 'm', 't', ' ' } );
    PutLittle( bytes, 16, 4 );                                      // fmt chunk size
    PutLittle( bytes, 1, 2 );                                       // PCM
    PutLittle( bytes, 1, 2 );                                       // mono
    PutLittle( bytes, static_cast<uint32_t>( rate ), 4 );
    PutLittle( bytes, static_cast<uint32_t>( rate ) * 2, 4 );       // bytes a second
    PutLittle( bytes, 2, 2 );                                       // bytes a frame
    PutLittle( bytes, 16, 2 );                                      // bits a sample
    bytes.insert( bytes.end(), { 'd', 'a', 't', 'a' } );
    PutLittle( bytes, dataBytes, 4 );
    for( int16_t sample : samples )
    {
        PutLittle( bytes, static_cast<uint16_t>( sample ), 2 );
    }
    file.write( bytes.data(), static_cast<std::streamsize>( bytes.size() ) );
    return static_cast<bool>( file );
}


std::string ClickTrack::MetronomeFile( const std::vector<Click>& inClicks )
{
    if( inClicks.empty() )
    {
        return {};
    }
    // FNV-1a over each click's millisecond and accent.
    uint64_t hash = 1469598103934665603ULL;
    double last = 0.0;
    for( const Click& click : inClicks )
    {
        const uint64_t value = static_cast<uint64_t>( std::llround( std::max( 0.0, click.Seconds ) * 1000.0 ) ) * 2 + ( click.Accent ? 1 : 0 );
        for( int i = 0; i < 8; ++i )
        {
            hash = ( hash ^ ( ( value >> ( 8 * i ) ) & 0xFF ) ) * 1099511628211ULL;
        }
        last = std::max( last, click.Seconds );
    }
    char name[48];
    std::snprintf( name, sizeof( name ), "metronome_%016llx.wav", static_cast<unsigned long long>( hash ) );
    const Path folder( kMetronomeFolder );
    const std::string directory = folder.FullPath + ( !folder.FullPath.empty() && folder.FullPath.back() == '/' ? "" : "/" );
    const std::string file = directory + name;
    std::error_code error;
    if( std::filesystem::is_regular_file( file, error ) )
    {
        // Used again: it counts as new when the folder is thinned.
        std::filesystem::last_write_time( file, std::filesystem::file_time_type::clock::now(), error );
        return file;
    }
    if( !Write( file, inClicks, last + 0.25, kMetronomeRate ) )
    {
        YIKES( "Metronome: couldn't write the click track to " + file );
        return {};
    }
    // Keep the newest few; a file an earlier song's sound still has open is only unlinked.
    std::vector<std::pair<std::filesystem::file_time_type, std::filesystem::path>> files;
    for( const auto& entry : std::filesystem::directory_iterator( directory, error ) )
    {
        if( entry.is_regular_file( error ) && entry.path().extension() == ".wav" )
        {
            files.emplace_back( entry.last_write_time( error ), entry.path() );
        }
    }
    std::sort( files.begin(), files.end(), []( const auto& a, const auto& b ) { return a.first > b.first; } );
    for( size_t i = kMetronomesKept; i < files.size(); ++i )
    {
        std::filesystem::remove( files[i].second, error );
        std::filesystem::remove( files[i].second.string() + ".meta", error );
    }
    return file;
}
