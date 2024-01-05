#include "CustomTrackDefineTest.h"
#include "Dementia.h"
DISABLE_OPTIMIZATION;


std::vector<std::string> split( const std::string& s, char delimiter ) {
    std::vector<std::string> tokens;
    std::string token;
    std::istringstream tokenStream( s );
    while( getline( tokenStream, token, delimiter ) ) {
        tokens.push_back( token );
    }
    return tokens;
}


LegacySongMetaData CustomTrackDefineTest::readSongMetaData( const std::string& filePath )
{
    std::ifstream file( filePath );
    std::string line;
    LegacySongMetaData metadata;
    std::string currentSection;

    // Check for UTF-8 BOM and skip it
    char bom[4] = { 0 };
    file.read( bom, 3 );
    if( bom[0] != (char)0xEF || bom[1] != (char)0xBB || bom[2] != (char)0xBF ) {
        // Not a BOM, rewind the file
        file.seekg( 0 );
    }

    while( getline( file, line ) ) {
        if( line.empty() || line[0] == '/' ) continue; // Skip empty lines and comments

        if( line[0] == '[' ) {
            currentSection = line;
            continue;
        }

        std::istringstream iss( line );
        if( currentSection == "[Song]" || currentSection == "[song]" ) {
            std::string key;
            std::string value;
            getline( iss, key, '=' );
            getline( iss, value );
            key.erase( remove_if( key.begin(), key.end(), isspace ), key.end() );

            // #TODO: These names seem to have different cases if included in the chart file vs the ini file, move to mainly support ini files only and use this as a fallback.
            if( key == "name" )
            {
                metadata.m_name = value;
            }
            else if( key == "artist" )
            {
                metadata.m_artist = value;
            }
            else if( key == "song_length" )
            {
                metadata.m_songLength = std::stoi( value );
            }
            else if( key == "preview_start_time" )
            {
                if (value != " " )
                {
                    metadata.m_previewStartTime = std::stoi( value );
                }
            }
        }
    }

    return metadata;
}

Song CustomTrackDefineTest::readSongFile( const std::string& filePath )
{
    std::ifstream file( filePath );
    std::string line;
    Song song;
    std::string currentSection;
    int noteTotal = 0;

    // Check for UTF-8 BOM and skip it
    char bom[4] = { 0 };
    file.read( bom, 3 );
    if( bom[0] != (char)0xEF || bom[1] != (char)0xBB || bom[2] != (char)0xBF ) {
        // Not a BOM, rewind the file
        file.seekg( 0 );
    }

    while( getline( file, line ) ) {
        if( line.empty() || line[0] == '/' ) continue; // Skip empty lines and comments

        if( line[0] == '[' ) {
            currentSection = line;
            continue;
        }

        std::istringstream iss( line );
        if( currentSection == "[Song]" ) {
            std::string key;
            std::string value;
            getline( iss, key, '=' );
            getline( iss, value );
            key.erase( remove_if( key.begin(), key.end(), isspace ), key.end() );

            // #TODO: These names seem to have different cases if included in the chart file vs the ini file, move to mainly support ini files only and use this as a fallback.
        }
        else if( currentSection == "[SyncTrack]" ) {
            // not sure what this is atm...
            int time;
            std::string value;
            iss >> time >> value;
            song.syncTracks[time] = { time, value };
        }
        else if( currentSection == "[EasyDrums]" ) {
            std::vector<std::string> parts = split( line, '=' );
            if( parts.size() < 2 ) continue; // Skip if the line is not correctly formatted

            int time = std::stoi( parts[0] );
            std::istringstream eventStream( parts[1] );
            char typeCode;
            eventStream >> typeCode;
            DrumEvent event;
            event.time = time;
            event.typeCode = typeCode;

            //TODO: Switch on event type
            int val;
            while( eventStream >> val ) {
                event.values.push_back( val );
                noteTotal++;
            }

            song.easyDrums[time].push_back( event );
        }
    }
    song.noteCount = noteTotal;

    return song;
}

