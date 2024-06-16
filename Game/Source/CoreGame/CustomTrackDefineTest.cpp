#include "CustomTrackDefineTest.h"
#include "Dementia.h"
//#include "MidiFile.h"
//#include "Options.h"
#include "Core\Assert.h"
#include "Editor\PadBindings.h"
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
            else if( key == "album" )
            {
                metadata.m_album = value;
            }
            else if( key == "genre" )
            {
                metadata.m_genre = value;
            }
            else if( key == "year" )
            {
                metadata.m_year = value;
            }
            else if( key == "icon" )
            {
                metadata.m_icon = value;
            }
            else if( key == "pro_drums" )
            {
                metadata.m_proDrums = (value == " True");
            }
            else if( key == "song_length" )
            {
                metadata.m_songLength = std::stoi( value );
            }
            else if( key == "preview_start_time" )
            {
                if( value != " " )
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
    //ParseMidi( Path( filePath ) );
    return song;
}

PadId GetNoteIdFromLegacy(int inNoteName)
{
    if( inNoteName == 96 )
    {
        return PadId::Bass;
    }
    else if( inNoteName == 97 )
    {
        return PadId::Snare;
    }
    else if( inNoteName == 98 )
    {
        return PadId::ClosedHiHat;
    }
    else if( inNoteName == 99 )
    {
        return PadId::HighTom;
    }
    return PadId::Crash2;
}

bool CustomTrackDefineTest::ParseMidi( Path& inFilePath, TrackData& outTrackData, LegacySongMetaData& inLegacyData )
{
//    smf::MidiFile midifile;
//    midifile.read( Path( inFilePath.FullPath + "/notes.mid" ).FullPath );
//    midifile.doTimeAnalysis();
//    midifile.linkNotePairs();
//    //midifile.splitTracks();
//
//    outTrackData.m_noteData.clear();
//
//    int tracks = midifile.getTrackCount();
//
//    bool hasDrums = false;
//    int drumTrackIndex = 0;
//    {
//        bool foundTrackName = false;
//        for( int track = 0; track < tracks; track++ ) {
//            if( hasDrums )
//            {
//                break;
//            }
//
//            for( int event = 0; event < midifile[track].size(); event++ ) {
//                if( midifile[track][event].isTrackName() )
//                {
//                    std::cout << midifile[track][event].getMetaContent().c_str() << std::endl;
//                    if( midifile[track][event].getMetaContent() == "PART DRUMS" )
//                    {
//                        hasDrums = true;
//                        drumTrackIndex = track;
//                        break;
//                    }
//                    foundTrackName = true;
//                }
//                else
//                {
//                    //break;
//                }
//            }
//        }
//    }
//    if( !hasDrums )
//    {
//        return false;
//    }
//
//    auto& drumTrack = midifile[drumTrackIndex];
//    std::cout << "TPQ: " << midifile.getTicksPerQuarterNote() << std::endl;
//    if( tracks > 1 ) std::cout << "\nTrack " << drumTrackIndex << std::endl;
//    std::cout << "Tick\tSeconds\tDur\tMessage" << std::endl;
//    outTrackData.m_noteCount = 0;
//
//    for( int event = 0; event < drumTrack.size(); event++ )
//    {
//        if( inLegacyData.m_proDrums )
//        {
//            //std::cout << std::dec << drumTrack[event].tick;
//            //std::cout << '\t' << std::dec << drumTrack[event].seconds;
//            //std::cout << '\t';
//            //if( drumTrack[event].isNoteOn() )
//            //    std::cout << drumTrack[event].getDurationInSeconds();
//            //std::cout << '\t' << std::hex;
//            //for( int i = 0; i < drumTrack[event].size(); i++ )
//            //    std::cout << (int)drumTrack[event][i] << ' ';
//            //std::cout << std::endl;
//            //std::cout << std::dec << drumTrack[event].getP0() << std::endl;
//            int drumNote = drumTrack[event].getP1();
//            if(drumNote > 100 || drumNote < 60 )
//            std::cout << std::dec << drumNote << std::endl;
//            //std::cout << drumTrack[event].getP2() << std::endl;
//            //std::cout << drumTrack[event].getP3() << std::endl;
//            //ME_ASSERT( drumNote >= 60 && drumNote <= 100);
//        }
//        else
//        {
//            int drumNote = drumTrack[event].getP1();
//            if( drumNote >= 96 && drumNote <= 100 )
//            {
//                outTrackData.m_noteCount++;
//                outTrackData.m_bpm = drumTrack[event].getTempoBPM();
//                NoteData newNote;
//                newNote.m_triggerTime = (float)drumTrack[event].seconds;
//                newNote.m_triggerTimeMS = newNote.m_triggerTime * 100.f;
//
//                std::cout << std::dec << drumTrack[event].tick;
//                std::cout << '\t' << std::dec << drumTrack[event].seconds;
//                std::cout << '\t';
//                if( drumTrack[event].isNoteOn() )
//                    std::cout << drumTrack[event].getDurationInSeconds();
//                //std::cout << '\t' << std::hex;
//                //for( int i = 0; i < drumTrack[event].size(); i++ )
//                //    std::cout << (int)drumTrack[event][i] << ' ';
//                std::cout << std::endl;
//                std::cout << std::dec << drumTrack[event].getP0() << std::endl;
//                std::cout << drumNote << std::endl;
//                //std::cout << drumTrack[event].getP2() << std::endl;
//                //std::cout << drumTrack[event].getP3() << std::endl;
//                //ME_ASSERT( drumNote >= 60 && drumNote <= 100);
//                newNote.m_editorLane = GetNoteIdFromLegacy( drumNote );
//                newNote.m_noteName = PadUtils::GetPadId( newNote.m_editorLane );
//                outTrackData.m_noteData.push_back( newNote );
//            }
//        }
//    }
//
    return true;
}

