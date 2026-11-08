#include "CustomTrackDefineTest.h"
#include "Dementia.h"
//#include "MidiFile.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <map>
#include <sstream>
//#include "Options.h"
#include "Core/Assert.h"
#include "Editor/PadBindings.h"
#include "MidiFile.h"
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



namespace
{
    // Rock Band exports often continue running status after a meta event, which smf::MidiFile
    // rejects ("running status not permitted with meta and sysex"), dropping the rest of the
    // track. Rewrite every channel event with an explicit status byte before parsing.
    bool ReadVarLen( const std::vector<uint8_t>& inBytes, size_t& ioPos, size_t inEnd, uint32_t& outValue )
    {
        outValue = 0;
        for( int i = 0; i < 4 && ioPos < inEnd; ++i )
        {
            const uint8_t byte = inBytes[ioPos++];
            outValue = ( outValue << 7 ) | ( byte & 0x7F );
            if( !( byte & 0x80 ) )
            {
                return true;
            }
        }
        return false;
    }


    void WriteVarLen( std::string& ioOut, uint32_t inValue )
    {
        uint8_t buffer[5];
        int count = 0;
        do
        {
            buffer[count++] = inValue & 0x7F;
            inValue >>= 7;
        } while( inValue && count < 5 );
        for( int i = count - 1; i >= 0; --i )
        {
            ioOut.push_back( static_cast<char>( buffer[i] | ( i ? 0x80 : 0 ) ) );
        }
    }


    bool NormalizeRunningStatus( const std::vector<uint8_t>& inBytes, std::string& outBytes )
    {
        if( inBytes.size() < 14 || std::memcmp( inBytes.data(), "MThd", 4 ) != 0 )
        {
            return false;
        }
        const uint32_t headerLength = ( inBytes[4] << 24 ) | ( inBytes[5] << 16 ) | ( inBytes[6] << 8 ) | inBytes[7];
        size_t pos = 8 + headerLength;
        outBytes.assign( reinterpret_cast<const char*>( inBytes.data() ), std::min( pos, inBytes.size() ) );
        while( pos + 8 <= inBytes.size() )
        {
            const uint32_t length = ( inBytes[pos + 4] << 24 ) | ( inBytes[pos + 5] << 16 ) | ( inBytes[pos + 6] << 8 ) | inBytes[pos + 7];
            const size_t start = pos + 8;
            const size_t end = std::min( inBytes.size(), start + length );
            if( std::memcmp( &inBytes[pos], "MTrk", 4 ) != 0 )
            {
                outBytes.append( reinterpret_cast<const char*>( &inBytes[pos] ), end - pos );
                pos = end;
                continue;
            }
            std::string track;
            uint8_t running = 0;
            size_t i = start;
            while( i < end )
            {
                uint32_t delta = 0;
                if( !ReadVarLen( inBytes, i, end, delta ) || i >= end )
                {
                    break;
                }
                WriteVarLen( track, delta );
                uint8_t status = inBytes[i];
                if( status == 0xFF || status == 0xF0 || status == 0xF7 )
                {
                    const size_t eventStart = i;
                    i += status == 0xFF ? 2 : 1;
                    uint32_t dataLength = 0;
                    if( !ReadVarLen( inBytes, i, end, dataLength ) )
                    {
                        break;
                    }
                    i = std::min<size_t>( end, i + dataLength );
                    track.append( reinterpret_cast<const char*>( &inBytes[eventStart] ), i - eventStart );
                    continue;
                }
                if( status & 0x80 )
                {
                    running = status;
                    ++i;
                }
                else if( !running )
                {
                    break;
                }
                const uint8_t type = running & 0xF0;
                const size_t dataBytes = type == 0xC0 || type == 0xD0 ? 1 : 2;
                if( i + dataBytes > end )
                {
                    break;
                }
                track.push_back( static_cast<char>( running ) );
                track.append( reinterpret_cast<const char*>( &inBytes[i] ), dataBytes );
                i += dataBytes;
            }
            outBytes.append( "MTrk", 4 );
            const uint32_t newLength = static_cast<uint32_t>( track.size() );
            const char lengthBytes[4] = { static_cast<char>( newLength >> 24 ), static_cast<char>( newLength >> 16 ), static_cast<char>( newLength >> 8 ), static_cast<char>( newLength ) };
            outBytes.append( lengthBytes, 4 );
            outBytes += track;
            pos = start + length;
        }
        return true;
    }
}


bool CustomTrackDefineTest::ReadMidi( smf::MidiFile& outMidi, const std::string& inPath )
{
    std::ifstream file( inPath, std::ios::binary );
    if( !file )
    {
        return false;
    }
    const std::vector<uint8_t> bytes( ( std::istreambuf_iterator<char>( file ) ), std::istreambuf_iterator<char>() );
    std::string normalized;
    if( !NormalizeRunningStatus( bytes, normalized ) )
    {
        return false;
    }
    std::istringstream stream( normalized );
    if( !outMidi.read( stream ) )
    {
        return false;
    }
    outMidi.doTimeAnalysis();
    return true;
}

bool CustomTrackDefineTest::ParseMidi( Path& inFilePath, TrackData& outTrackData, LegacySongMetaData& inLegacyData )
{
    smf::MidiFile midifile;
    if( !ReadMidi( midifile, Path( inFilePath.FullPath + "/notes.mid" ).FullPath ) )
    {
        return false;
    }
    //midifile.linkNotePairs();
    //midifile.splitTracks();

    if( false )
    {
        int tracks = midifile.getTrackCount();
        std::cout << "TPQ: " << midifile.getTicksPerQuarterNote() << std::endl;
        if( tracks > 1 ) std::cout << "TRACKS: " << tracks << std::endl;
        for( int track = 0; track < tracks; track++ )
        {
            if( tracks > 1 ) std::cout << "\nTrack " << track << std::endl;
            std::cout << "Tick\tSeconds\tDur\tMessage" << std::endl;
            for( int event = 0; event < midifile[track].size(); event++ )
            {
                std::cout << std::dec << midifile[track][event].tick;
                std::cout << '\t' << std::dec << midifile[track][event].seconds;
                std::cout << '\t';
                if( midifile[track][event].isNoteOn() )
                    std::cout << midifile[track][event].getDurationInSeconds();
                std::cout << '\t' << std::hex;
                for( int i = 0; i < midifile[track][event].size(); i++ )
                    std::cout << (int)midifile[track][event][i] << ' ';
                std::cout << std::endl;
            }
        }
    }

    outTrackData.m_noteData.clear();
    outTrackData.m_beats.clear();
    outTrackData.m_noteCount = 0;

    const int tracks = midifile.getTrackCount();
    int drumTrackIndex = -1;
    for( int track = 0; track < tracks && drumTrackIndex < 0; ++track )
    {
        for( int event = 0; event < midifile[track].size(); ++event )
        {
            if( midifile[track][event].isTrackName() && midifile[track][event].getMetaContent() == "PART DRUMS" )
            {
                drumTrackIndex = track;
                break;
            }
        }
    }
    if( drumTrackIndex < 0 )
    {
        return false;
    }
    auto& drumTrack = midifile[drumTrackIndex];

    // Rock Band pro drums: yellow, blue and green gems are cymbals unless a tom marker (110, 111,
    // 112) covers them. Collect those spans, and whether the chart marks dynamics (velocity 1 is a
    // ghost note, 127 an accent, after an "[ENABLE_CHART_DYNAMICS]" text event).
    struct Span { int Start; int End; };
    std::map<int, std::vector<Span>> tomMarkers;
    std::map<int, int> openMarker;
    bool dynamics = false;
    for( int event = 0; event < drumTrack.size(); ++event )
    {
        const smf::MidiEvent& message = drumTrack[event];
        if( message.isMetaMessage() && message.getMetaContent().find( "ENABLE_CHART_DYNAMICS" ) != std::string::npos )
        {
            dynamics = true;
        }
        const int key = message.isNoteOn() || message.isNoteOff() ? message.getKeyNumber() : -1;
        if( key < 110 || key > 112 )
        {
            continue;
        }
        if( message.isNoteOn() )
        {
            openMarker[key] = message.tick;
        }
        else if( openMarker.count( key ) )
        {
            tomMarkers[key].push_back( { openMarker[key], message.tick } );
            openMarker.erase( key );
        }
    }
    const bool pro = inLegacyData.m_proDrums || !tomMarkers.empty();
    const auto underTomMarker = [&tomMarkers]( int inMarker, int inTick ) {
        for( const Span& span : tomMarkers[inMarker] )
        {
            if( inTick >= span.Start && inTick < span.End )
            {
                return true;
            }
        }
        return false;
    };

    // Expert notes: 95 double-kick, 96 kick, 97 snare, 98 yellow, 99 blue, 100 green.
    for( int event = 0; event < drumTrack.size(); ++event )
    {
        const smf::MidiEvent& message = drumTrack[event];
        if( !message.isNoteOn() )
        {
            continue;
        }
        const int key = message.getKeyNumber();
        PadId pad = PadId::Invalid;
        switch( key )
        {
        case 95:
        case 96: pad = PadId::Bass; break;
        case 97: pad = PadId::Snare; break;
        case 98: pad = !pro || underTomMarker( 110, message.tick ) ? PadId::HighTom : PadId::ClosedHiHat; break;
        case 99: pad = !pro || underTomMarker( 111, message.tick ) ? PadId::MidTom : PadId::Ride; break;
        case 100: pad = !pro || underTomMarker( 112, message.tick ) ? PadId::FloorTom : PadId::Crash1; break;
        default: break;
        }
        if( pad == PadId::Invalid )
        {
            continue;
        }
        NoteData note;
        note.m_triggerTime = static_cast<float>( message.seconds );
        note.m_triggerTimeMS = static_cast<uint32_t>( std::lround( message.seconds * 1000.0 ) );
        note.m_editorLane = pad;
        note.m_noteName = PadUtils::GetPadId( pad );
        const int velocity = message.getVelocity();
        note.m_velocity = !dynamics ? 100 : velocity <= 1 ? 30 : velocity >= 127 ? 127 : 100;
        outTrackData.m_noteData.push_back( note );
        ++outTrackData.m_noteCount;
    }
    if( outTrackData.m_noteData.empty() )
    {
        return false;
    }

    // Tempo: the first tempo event, and the beat grid for the highway.
    for( int event = 0; event < midifile[0].size(); ++event )
    {
        if( midifile[0][event].isTempo() )
        {
            outTrackData.m_bpm = static_cast<int>( std::lround( midifile[0][event].getTempoBPM() ) );
            break;
        }
    }
    double lastNote = 0.0;
    for( const NoteData& note : outTrackData.m_noteData )
    {
        lastNote = std::max( lastNote, static_cast<double>( note.m_triggerTime ) );
    }
    outTrackData.m_beats = ReadMidiBeats( midifile, lastNote + 4.0 );
    outTrackData.m_venue = ReadMidiVenue( midifile );
    return true;
}


VenueData CustomTrackDefineTest::ReadMidiVenue( smf::MidiFile& inMidi )
{
    // Rock Band venue authoring (Docs/Stage-Lighting.md, Docs/Venue-and-Band.md):
    //   VENUE / MV VENUE: lighting cues, keyframes, fog, pyro, spotlights, camera cuts (RB2 notes
    //   60-64 + 70-73, "[do_directed_cut x]", RB3 "[coop_x]" / "[directed_x]"), post-processing
    //   (RB2 notes 96-110, RB3 "[x.pp]") and singalongs (85-87). MV VENUE is the music video's cut.
    //   EVENTS: sections and crowd states.
    //   PART DRUMS / GUITAR / BASS / VOCALS / KEYS: the band's animation states ("[idle]", "[play]"
    //   ...), the drummer's limb notes (24-51), expert strums and sung notes.
    VenueData venue;
    const auto strip = []( std::string inText ) {
        while( !inText.empty() && ( inText.back() == ' ' || inText.back() == '\t' ) ) inText.pop_back();
        if( !inText.empty() && inText.front() == '[' ) inText.erase( 0, 1 );
        if( !inText.empty() && inText.back() == ']' ) inText.pop_back();
        return inText;
    };
    const auto startsWith = []( const std::string& inText, const char* inPrefix ) {
        return inText.rfind( inPrefix, 0 ) == 0;
    };
    // RB2's post-processing notes, in order from 96.
    static const char* kPostNotes[] = { "ProFilm_a", "ProFilm_b", "video_a", "film_16mm", "shitty_tv", "bloom", "film_sepia_ink", "film_silvertone",
        "film_b+w", "video_bw", "contrast_a", "photocopy", "film_blue_filter", "desat_blue", "video_trails" };
    // RB2 camera notes held with a cut (60): its constraints.
    static const std::map<int, const char*> kCameraNotes = { { 61, "no_close" }, { 62, "only_close" }, { 63, "only_far" }, { 64, "no_behind" },
        { 70, "focus_bass" }, { 71, "focus_drums" }, { 72, "focus_guitar" }, { 73, "focus_vocals" } };
    const auto isCameraCut = [&startsWith]( const std::string& inText ) {
        return startsWith( inText, "coop_" ) || startsWith( inText, "directed_" ) || startsWith( inText, "do_directed_cut " );
    };

    for( int track = 0; track < inMidi.getTrackCount(); ++track )
    {
        std::string name;
        for( int i = 0; i < inMidi[track].size() && name.empty(); ++i )
        {
            if( inMidi[track][i].isTrackName() )
            {
                name = inMidi[track][i].getMetaContent();
            }
        }
        const bool isMv = name == "MV VENUE";
        const bool isVenue = name == "VENUE" || isMv;
        const bool isEvents = name == "EVENTS";
        int member = -1;
        if( name == "PART DRUMS" ) member = VenueData::Drums;
        else if( name == "PART GUITAR" ) member = VenueData::Guitar;
        else if( name == "PART BASS" ) member = VenueData::Bass;
        else if( name == "PART VOCALS" ) member = VenueData::Vocals;
        else if( name == "PART KEYS" ) member = VenueData::Keys;
        if( !isVenue && !isEvents && member < 0 )
        {
            continue;
        }
        std::vector<TimedCueData>& cameras = isMv ? venue.m_mvCameras : venue.m_cameras;
        std::vector<TimedCueData>& postFx = isMv ? venue.m_mvPostFx : venue.m_postFx;
        std::map<int, float> held;
        // RB2 note cuts: the notes struck together at one tick make one cut.
        int cutTick = -1;
        float cutTime = 0.f;
        std::string cutTags;
        bool cutHasCut = false;
        const auto flushCut = [&]() {
            if( cutTick >= 0 && cutHasCut )
            {
                cameras.push_back( { cutTime, "auto" + cutTags } );
            }
            cutTick = -1;
            cutTags.clear();
            cutHasCut = false;
        };
        float lastStrum = -1.f;
        for( int i = 0; i < inMidi[track].size(); ++i )
        {
            const smf::MidiEvent& event = inMidi[track][i];
            const float time = static_cast<float>( event.seconds );
            if( event.isMetaMessage() )
            {
                const int type = event.getMetaType();
                if( type != 0x01 && type != 0x05 && type != 0x06 && type != 0x07 )
                {
                    continue;
                }
                const std::string text = strip( event.getMetaContent() );
                if( member >= 0 )
                {
                    if( text == "idle" || text == "play" || text == "mellow" || text == "intense" || startsWith( text, "idle_" ) || startsWith( text, "play_" ) )
                    {
                        venue.m_bandStates[member].push_back( { time, text } );
                    }
                    continue;
                }
                if( isEvents )
                {
                    if( startsWith( text, "section " ) ) venue.m_sections.push_back( { time, text.substr( 8 ) } );
                    else if( startsWith( text, "prc_" ) ) venue.m_sections.push_back( { time, text.substr( 4 ) } );
                    else if( startsWith( text, "crowd_" ) ) venue.m_crowd.push_back( { time, text.substr( 6 ) } );
                    else if( text == "music_start" || text == "music_end" || text == "end" || text == "coda" ) venue.m_songEvents.push_back( { time, text } );
                    continue;
                }
                if( isCameraCut( text ) )
                {
                    cameras.push_back( { time, startsWith( text, "do_directed_cut " ) ? text.substr( 16 ) : text } );
                }
                else if( text.size() > 3 && text.compare( text.size() - 3, 3, ".pp" ) == 0 )
                {
                    postFx.push_back( { time, text.substr( 0, text.size() - 3 ) } );
                }
                else if( isMv )
                {
                    continue;
                }
                else if( startsWith( text, "lighting (" ) && text.back() == ')' )
                {
                    venue.m_lighting.push_back( { time, text.substr( 10, text.size() - 11 ) } );
                }
                else if( text == "verse" || text == "chorus" )
                {
                    venue.m_lighting.push_back( { time, text } );
                }
                else if( text == "FogOn" || text == "FogOff" )
                {
                    venue.m_fog.push_back( { time, text == "FogOn" } );
                }
                else if( startsWith( text, "bonusfx" ) )
                {
                    venue.m_bonusFx.push_back( time );
                }
                else if( text == "next" || text == "prev" || text == "first" )
                {
                    venue.m_keyframes.push_back( { time, text == "next" ? VenueData::Keyframe::Next : text == "prev" ? VenueData::Keyframe::Previous : VenueData::Keyframe::First } );
                }
                continue;
            }
            if( !( event.isNoteOn() || event.isNoteOff() ) )
            {
                continue;
            }
            const int key = event.getKeyNumber();
            if( member >= 0 )
            {
                if( !event.isNoteOn() )
                {
                    if( member == VenueData::Vocals && key >= 36 && key <= 84 && held.count( key ) )
                    {
                        venue.m_vocalNotes.push_back( { held[key], time, VenueData::Vocals } );
                        held.erase( key );
                    }
                    continue;
                }
                if( member == VenueData::Vocals )
                {
                    if( key >= 36 && key <= 84 ) held[key] = time;
                }
                else if( member == VenueData::Drums )
                {
                    using Limb = VenueData::Limb;
                    using Piece = VenueData::DrumPiece;
                    struct Stroke { Limb L; Piece P; bool Soft; };
                    static const std::map<int, Stroke> kStrokes = {
                        { 24, { Limb::RightFoot, Piece::Kick, false } },
                        { 26, { Limb::LeftHand, Piece::Snare, false } }, { 27, { Limb::RightHand, Piece::Snare, false } },
                        { 28, { Limb::LeftHand, Piece::Snare, true } }, { 29, { Limb::RightHand, Piece::Snare, true } },
                        { 30, { Limb::LeftHand, Piece::HiHat, false } }, { 31, { Limb::RightHand, Piece::HiHat, false } },
                        { 32, { Limb::RightHand, Piece::HiHat, true } },
                        { 34, { Limb::LeftHand, Piece::Crash1, false } }, { 35, { Limb::LeftHand, Piece::Crash1, true } },
                        { 36, { Limb::RightHand, Piece::Crash1, false } }, { 37, { Limb::RightHand, Piece::Crash1, true } },
                        { 38, { Limb::RightHand, Piece::Crash2, false } }, { 39, { Limb::RightHand, Piece::Crash2, true } },
                        { 40, { Limb::LeftHand, Piece::Crash1, true } }, { 41, { Limb::LeftHand, Piece::Crash2, true } },
                        { 42, { Limb::RightHand, Piece::Ride, false } }, { 43, { Limb::LeftHand, Piece::Ride, false } },
                        { 44, { Limb::LeftHand, Piece::Crash2, false } }, { 45, { Limb::LeftHand, Piece::Crash2, true } },
                        { 46, { Limb::LeftHand, Piece::Tom1, false } }, { 47, { Limb::RightHand, Piece::Tom1, false } },
                        { 48, { Limb::LeftHand, Piece::Tom2, false } }, { 49, { Limb::RightHand, Piece::Tom2, false } },
                        { 50, { Limb::LeftHand, Piece::FloorTom, false } }, { 51, { Limb::RightHand, Piece::FloorTom, false } },
                    };
                    const auto stroke = kStrokes.find( key );
                    if( stroke != kStrokes.end() )
                    {
                        venue.m_drumHits.push_back( { time, stroke->second.L, stroke->second.P, stroke->second.Soft } );
                    }
                }
                else if( key >= 40 && key <= 59 && ( member == VenueData::Guitar || member == VenueData::Bass ) )
                {
                    ( member == VenueData::Guitar ? venue.m_guitarFrets : venue.m_bassFrets ).push_back( { time, time, key - 40 } );
                }
                else if( key >= 96 && key <= 100 && time - lastStrum > 0.01f )
                {
                    // Expert gems; a chord's notes land together and strum once.
                    lastStrum = time;
                    ( member == VenueData::Guitar ? venue.m_guitarStrums : member == VenueData::Bass ? venue.m_bassStrums : venue.m_keysStrums ).push_back( time );
                }
                continue;
            }
            if( isEvents )
            {
                continue;
            }
            if( event.isNoteOn() && event.tick != cutTick && ( key == 60 || kCameraNotes.count( key ) ) )
            {
                flushCut();
            }
            if( key == 60 || kCameraNotes.count( key ) )
            {
                if( event.isNoteOn() )
                {
                    cutTick = event.tick;
                    cutTime = time;
                    if( key == 60 ) cutHasCut = true;
                    else cutTags += std::string( " " ) + kCameraNotes.at( key );
                }
                continue;
            }
            if( key >= 96 && key <= 110 )
            {
                if( event.isNoteOn() ) postFx.push_back( { time, kPostNotes[key - 96] } );
                continue;
            }
            if( isMv )
            {
                continue;
            }
            if( ( key >= 37 && key <= 41 ) || ( key >= 85 && key <= 87 ) )
            {
                if( event.isNoteOn() )
                {
                    held[key] = time;
                }
                else if( held.count( key ) )
                {
                    if( key <= 41 ) venue.m_spotlights.push_back( { held[key], time, key - 37 } );
                    // 85 bass, 86 drums, 87 guitar.
                    else venue.m_singalong.push_back( { held[key], time, key == 85 ? VenueData::Bass : key == 86 ? VenueData::Drums : VenueData::Guitar } );
                    held.erase( key );
                }
            }
            else if( event.isNoteOn() )
            {
                switch( key )
                {
                case 48: venue.m_keyframes.push_back( { time, VenueData::Keyframe::Next } ); break;
                case 49: venue.m_keyframes.push_back( { time, VenueData::Keyframe::Previous } ); break;
                case 50: venue.m_keyframes.push_back( { time, VenueData::Keyframe::First } ); break;
                default: break;
                }
            }
        }
        flushCut();
    }
    const auto byTime = []( const auto& a, const auto& b ) { return a.m_time < b.m_time; };
    const auto byStart = []( const auto& a, const auto& b ) { return a.m_start < b.m_start; };
    std::stable_sort( venue.m_lighting.begin(), venue.m_lighting.end(), byTime );
    std::stable_sort( venue.m_sections.begin(), venue.m_sections.end(), byTime );
    std::stable_sort( venue.m_crowd.begin(), venue.m_crowd.end(), byTime );
    std::stable_sort( venue.m_keyframes.begin(), venue.m_keyframes.end(), byTime );
    std::stable_sort( venue.m_fog.begin(), venue.m_fog.end(), byTime );
    for( auto* cues : { &venue.m_cameras, &venue.m_mvCameras, &venue.m_postFx, &venue.m_mvPostFx } )
    {
        std::stable_sort( cues->begin(), cues->end(), byTime );
    }
    for( auto& states : venue.m_bandStates )
    {
        std::stable_sort( states.begin(), states.end(), byTime );
    }
    std::stable_sort( venue.m_drumHits.begin(), venue.m_drumHits.end(), byTime );
    std::sort( venue.m_bonusFx.begin(), venue.m_bonusFx.end() );
    venue.m_bonusFx.erase( std::unique( venue.m_bonusFx.begin(), venue.m_bonusFx.end(), []( float a, float b ) { return b - a < 0.05f; } ), venue.m_bonusFx.end() );
    std::sort( venue.m_spotlights.begin(), venue.m_spotlights.end(), byStart );
    std::sort( venue.m_singalong.begin(), venue.m_singalong.end(), byStart );
    std::sort( venue.m_vocalNotes.begin(), venue.m_vocalNotes.end(), byStart );
    std::stable_sort( venue.m_guitarFrets.begin(), venue.m_guitarFrets.end(), byStart );
    std::stable_sort( venue.m_bassFrets.begin(), venue.m_bassFrets.end(), byStart );
    std::stable_sort( venue.m_songEvents.begin(), venue.m_songEvents.end(), byTime );
    return venue;
}


std::vector<BeatData> CustomTrackDefineTest::ReadMidiBeats( smf::MidiFile& inMidi, double inEndSeconds )
{
    std::vector<BeatData> beats;
    const int ticksPerQuarter = inMidi.getTicksPerQuarterNote();
    if( ticksPerQuarter <= 0 )
    {
        return beats;
    }
    // Time signature changes (tick, beats per measure, beat length in ticks); 4/4 until the first.
    struct Signature { int Tick; int Beats; int BeatTicks; };
    std::vector<Signature> signatures{ { 0, 4, ticksPerQuarter } };
    for( int track = 0; track < inMidi.getTrackCount(); ++track )
    {
        for( int i = 0; i < inMidi[track].size(); ++i )
        {
            const smf::MidiEvent& event = inMidi[track][i];
            if( event.isTimeSignature() && event.size() >= 5 )
            {
                const int count = std::max( 1, static_cast<int>( event[3] ) );
                const int beatTicks = std::max( 1, ticksPerQuarter * 4 / ( 1 << std::min( 6, static_cast<int>( event[4] ) ) ) );
                if( event.tick == 0 )
                {
                    signatures[0] = { 0, count, beatTicks };
                }
                else
                {
                    signatures.push_back( { event.tick, count, beatTicks } );
                }
            }
        }
    }
    std::sort( signatures.begin(), signatures.end(), []( const Signature& a, const Signature& b ) { return a.Tick < b.Tick; } );

    size_t signature = 0;
    int beatInMeasure = 0;
    for( int tick = 0; tick >= 0 && beats.size() < 4000; tick += signatures[signature].BeatTicks )
    {
        while( signature + 1 < signatures.size() && tick >= signatures[signature + 1].Tick )
        {
            ++signature;
            tick = signatures[signature].Tick;
            beatInMeasure = 0;
        }
        // The library answers -1 past the file's last event (it doesn't extrapolate the tempo).
        const double seconds = inMidi.getTimeInSeconds( tick );
        if( ( tick > 0 && seconds < 0.0 ) || seconds > inEndSeconds )
        {
            break;
        }
        beats.push_back( BeatData{ static_cast<float>( seconds ), beatInMeasure == 0 } );
        beatInMeasure = ( beatInMeasure + 1 ) % signatures[signature].Beats;
    }
    return beats;
}


std::vector<BeatData> CustomTrackDefineTest::ReadMidiBeats( const std::string& inPath, double inEndSeconds )
{
    smf::MidiFile midi;
    if( !ReadMidi( midi, inPath ) )
    {
        return {};
    }
    return ReadMidiBeats( midi, inEndSeconds );
}

