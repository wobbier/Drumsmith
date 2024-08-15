#include "TrackList.h"
#include <filesystem>
#include "Core/Assert.h"
#include "CustomTrackDefineTest.h"
#include "JSON.h"
#include "Utils/StringUtils.h"
#include "CLog.h"

DISABLE_OPTIMIZATION;

TrackList::TrackList()
    : ConfigFile( Path( "Assets/TrackDatabase.json" ) )
{
    if( !m_configFile.Data.empty() )
    {
        //Save();
    }

    //Load();
}

void TrackList::OnSave( json& outJson )
{
}

void TrackList::OnLoadConfig( const json& outJson )
{
}

namespace fs = std::filesystem;

bool fileExistsInDirectory( const fs::path& dirPath, const std::string& fileName ) {
    for( const auto& entry : fs::directory_iterator( dirPath ) ) {
        if( entry.is_regular_file() && entry.path().filename() == fileName ) {
            return true;
        }
    }
    return false;
}


PadId ConvertLegacyPad( int inPad )
{
    switch( inPad )
    {
    case 0:
        return PadId::Bass;
    case 1:
        return PadId::Snare;
    case 2:
        return PadId::ClosedHiHat;
    default:
        break;
    }
    return PadId::Bass;
}


LegacySongMetaData ConvertFromLegacy( const std::string& inTrackDirectory, TrackData& outNewTrack )
{
    // bro 💀 https://xkcd.com/927/
    LegacySongMetaData metadata = CustomTrackDefineTest::GetInstance().readSongMetaData( inTrackDirectory + "/song.ini" );

    outNewTrack.m_trackName = metadata.m_name;
    outNewTrack.m_artistName = metadata.m_artist;
    outNewTrack.m_genre = metadata.m_genre;
    outNewTrack.m_year = std::stoi( metadata.m_year );
    outNewTrack.m_icon = metadata.m_icon;
    if( metadata.m_previewStartTime > 0 )
    {
        outNewTrack.m_previewPercent = ( metadata.m_previewStartTime / (float)metadata.m_songLength );
    }
    outNewTrack.m_durationMS = metadata.m_songLength;
    outNewTrack.m_duration = metadata.m_songLength / 1000.f;

    Path albumArtPath( inTrackDirectory + "/album.jpg" );
    if( !albumArtPath.Exists )
    {
        albumArtPath = Path( inTrackDirectory + "/album.png" );
    }
    ME_ASSERT( albumArtPath.Exists );
    outNewTrack.m_albumArtPath = albumArtPath.GetLocalPathString();

    // I don't know how much this differs from chart to chart

    Path songFile( inTrackDirectory + "/song.ogg" );
    if( !songFile.Exists )
    {
        // opus will require some manual converting... as fmod doesn't support this type atm
        //outNewTrack.m_trackFileName = "song.opus";
        //outNewTrack.m_trackSourcePath = inTrackDirectory + "song.opus";
    }
    else
    {
        outNewTrack.m_trackFileName = "song.ogg";
        outNewTrack.m_trackSourcePath = inTrackDirectory + "/song.ogg";
    }

    outNewTrack.m_bpm = 110;//(float)inLegacyData.syncTracks[0].value >> 3;
    outNewTrack.m_noteSpeed = 10;//(float)inLegacyData.syncTracks[0].value >> 3;

    outNewTrack.m_bpm = 180.f;

    outNewTrack.Save();
    return metadata;
}

TrackDatabase::TrackDatabase()
{
    fs::path rootPath = Path( "Assets/DLC" ).FullPath;  // Replace with your directory path
    std::vector<Path> m_drumlessSongs;
    try {
        for( const auto& entry : fs::directory_iterator( rootPath ) )
        {
            if( entry.is_directory() )
            {
                // #TODO: Support CHART DLC files
                bool chartFormat = fileExistsInDirectory( entry.path(), "notes.chart" );
                if( chartFormat )
                {
                    //Path midiPath = Path( std::string( entry.path().u8string() ) );
                    //    
                    //if( !CustomTrackDefineTest::GetInstance().ParseMidi( midiPath ) )
                    //{
                    //    m_drumlessSongs.push_back( midiPath );
                    //}
                    continue;
                }

                // #TODO: Do we even support OPUS? I would need to convert it for fmod...
                //bool opusFormat = fileExistsInDirectory( entry.path(), "song.opus" );
                //if( opusFormat )
                //{
                //    YIKES( entry.path().u8string().c_str() );
                //    continue;
                //}

                // Check for any Custom DLC from other formats
                //bool exists = fileExistsInDirectory( entry.path(), "song.ini" );
                //if( exists )
                //{
                //    Path chartFilePath = Path( entry.path().u8string() + "/notes.chart" );
                //    Song rbCustomTrack;
                //    if( chartFilePath.Exists )
                //    {
                //        rbCustomTrack = CustomTrackDefineTest::GetInstance().readSongFile( chartFilePath.FullPath );
                //    }
                //    TrackData newTrack = TrackData( Path( chartFilePath.GetDirectoryString() + "/NoteData.txt" ) );
                //
                //    m_trackList.m_tracks.push_back( ConvertFromLegacy( chartFilePath.GetDirectoryString(), rbCustomTrack, newTrack ) );
                //    //newTrack.Save();
                //}
                //else
                {
                    bool exists = fileExistsInDirectory( entry.path(), "TrackData.txt" );
                    if( exists )
                    {
                        m_trackList.m_tracks.emplace_back( TrackData( Path( entry.path().u8string() + "/TrackData.txt" ) ) );
                        m_trackList.m_tracks.back().Load();

                        Path trackPath( m_trackList.m_tracks.back().m_trackSourcePath );
                        if( !trackPath.Exists )
                        {
                            YIKES_FMT( "Song does not exist in directory: %s", m_trackList.m_tracks.back().m_trackFileName.c_str() );
                            continue;
                        }
                    }
                    else
                    {
                        YIKES_FMT( "TrackData.txt doesn't exist for: %s", entry.path().u8string().c_str() );
                    }
                }
            }
        }
    }
    catch( fs::filesystem_error& e ) {
        std::cout << e.what() << std::endl;
    }

    for( auto& path : m_drumlessSongs )
    {
        YIKES( path.FullPath.c_str() );
    }
}

void TrackDatabase::ExportMidiTrackMetaData()
{
    fs::path rootPath = Path( "Assets/DLC" ).FullPath;
    try {
        for( const auto& entry : fs::directory_iterator( rootPath ) )
        {
            if( !entry.is_directory() )
            {
                continue;
            }

            // #TODO: Support MIDI DLC files
            bool midiFormat = fileExistsInDirectory( entry.path(), "notes.mid" );
            if( midiFormat )
            {
                Path midiPath = Path( std::string( entry.path().u8string() ) );

                TrackData newTrack = TrackData( Path( midiPath.FullPath + "/NoteData.txt" ) );
                LegacySongMetaData legacyTrack = ConvertFromLegacy( midiPath.FullPath, newTrack );
                if( CustomTrackDefineTest::GetInstance().ParseMidi( midiPath, newTrack, legacyTrack ) )
                {
                    m_trackList.m_tracks.push_back( newTrack );
                }
                //LegacySongMetaData metadata = CustomTrackDefineTest::GetInstance().readSongMetaData( midiPath.FullPath + "/song.ini" );
                //
                //json iniMetaData;
                //iniMetaData["TrackName"] = metadata.m_name;
                //
                //File iniOutput( Path( midiPath.FullPath + "/TrackData.txt" ) );
                //iniOutput.Write( iniMetaData.dump( 1 ) );

                continue;
            }
        }
    }
    catch( fs::filesystem_error& e ) {
        std::cout << e.what() << std::endl;
    }
}

std::vector<unsigned int>& TrackDatabase::SortTracks( TrackListSort inSortBy )
{
    if( inSortBy != m_currentSort )
    {
        m_needsSort = true;
    }

    if( !m_needsSort && !m_pendingInitialSort )
    {
        return m_sortedIndices;
    }

    auto& trackList = m_trackList.m_tracks;
    auto& sortedTracks = m_sortedIndices;
    sortedTracks.clear();
    sortedTracks.reserve( trackList.size() );
    for( int i = 0; i < trackList.size(); ++i )
    {
        sortedTracks.push_back( i );
    }
    m_currentSort = inSortBy;

    switch( inSortBy )
    {
    case TrackListSort::Title:
        std::sort( sortedTracks.begin(), sortedTracks.end(), [trackList]( unsigned int& first, unsigned int& second ) {
            return trackList[first].m_trackName < trackList[second].m_trackName;
            } );
        break;
    case TrackListSort::Artist:
        std::sort( sortedTracks.begin(), sortedTracks.end(), [trackList]( unsigned int& first, unsigned int& second ) {
            return trackList[first].m_artistName < trackList[second].m_artistName;
            } );
        break;
    case TrackListSort::Year:
        std::sort( sortedTracks.begin(), sortedTracks.end(), [trackList]( unsigned int& first, unsigned int& second ) {
            return trackList[first].m_year < trackList[second].m_year;
            } );
        break;
    default:
    case TrackListSort::None:
        break;
    }

    m_pendingInitialSort = false;
    m_needsSort = false;

    return m_sortedIndices;
}

TrackData::TrackData( const Path& inPath )
{
    if( inPath.IsFile )
    {
        m_directory = inPath.GetDirectoryString();
    }
    else
    {
        m_directory = inPath.FullPath;
    }
}

void TrackData::Save()
{
    {
        json metaData;
        OnSaveTrackData( metaData );
        File metaFile( Path( m_directory + "/TrackData.txt" ) );
        metaFile.Write( metaData.dump( 1 ) );
    }

    if( !m_noteData.empty() )
    {
        json metaData;
        OnSaveNoteData( metaData );
        File metaFile( Path( m_directory + "/NoteData.txt" ) );
        metaFile.Write( metaData.dump( 1 ) );
    }
}

void TrackData::Load()
{
    {
        Path trackDataFile( m_directory + "/TrackData.txt" );
        if( trackDataFile.Exists )
        {
            File metaFile( trackDataFile );
            json metaData = json::parse( metaFile.Read() );
            OnLoadTrackData( metaData );
        }
    }
    //{
    //    File metaFile( Path( m_directory + "/NoteData.txt" ) );
    //    json metaData = json::parse( metaFile.Read() );
    //    OnLoadConfig( metaData );
    //}
}

void TrackData::OnSaveTrackData( json& outJson )
{
    outJson["SongName"] = m_trackName;
    outJson["SongArtist"] = m_artistName;
    outJson["AlbumName"] = m_albumName;
    outJson["Genre"] = m_genre;
    outJson["Year"] = m_year;
    outJson["Icon"] = m_icon;
    outJson["AlbumArtPath"] = m_albumArtPath;
    outJson["AlbumArtFileName"] = m_albumArtFilename;
    //m_albumArtPath = m_configFile.FilePath.GetDirectoryString() + "/Album.png";
    //m_trackSourcePath = m_configFile.FilePath.GetDirectoryString() + "/Track.mp3";
    outJson["NoteSpeed"] = m_noteSpeed;
    outJson["Duration"] = m_duration;
    outJson["BPM"] = m_bpm;
    outJson["TrackFileName"] = m_trackFileName;
    outJson["PreviewPercent"] = m_previewPercent;
    outJson["NoteCount"] = m_noteCount;
}

void TrackData::OnSaveNoteData( json& outJson )
{
    std::sort( m_noteData.begin(), m_noteData.end(), []( NoteData& first, NoteData& second )
        {
            if( first.m_triggerTime != second.m_triggerTime )
            {
                return first.m_triggerTime < second.m_triggerTime;
            }
            return first.m_editorLane < second.m_editorLane;
        } );
    m_noteData.erase( std::unique( m_noteData.begin(), m_noteData.end() ), m_noteData.end() );

    json& noteData = outJson["Notes"];
    for( NoteData& note : m_noteData )
    {
        json noteEntry;
        noteEntry["EditorLane"] = note.m_editorLane;
        noteEntry["NoteName"] = note.m_noteName;
        noteEntry["TriggerTime"] = note.m_triggerTime;
        noteEntry["TriggerTimeMS"] = (uint32_t)( note.m_triggerTime * 1000.f );

        noteData.push_back( noteEntry );
    }
}

void TrackData::OnLoadTrackData( const json& outJson )
{
    if( outJson.contains( "SongName" ) )
    {
        m_trackName = StringUtils::TrimLeadingSpaces( outJson["SongName"] );
    }
    if( outJson.contains( "SongArtist" ) )
    {
        m_artistName = StringUtils::TrimLeadingSpaces( outJson["SongArtist"] );
    }
    if( outJson.contains( "AlbumName" ) )
    {
        m_albumName = StringUtils::TrimLeadingSpaces( outJson["AlbumName"] );
    }
    if( outJson.contains( "Genre" ) )
    {
        m_genre = outJson["Genre"];
    }
    if( outJson.contains( "Year" ) )
    {
        m_year = outJson["Year"];
    }
    if( outJson.contains( "Icon" ) )
    {
        m_icon = outJson["Icon"];
    }
    if( outJson.contains( "NoteCount" ) )
    {
        m_noteCount = outJson["NoteCount"];
    }
    m_albumArtPath = m_directory + "/Album.png";
    if( outJson.contains( "AlbumArtPath" ) )
    {
        m_albumArtPath = outJson["AlbumArtPath"];
    }
    if( outJson.contains( "AlbumArtFilename" ) )
    {
        m_albumArtFilename = outJson["AlbumArtFilename"];
    }
    if( outJson.contains( "TrackFileName" ) )
    {
        m_trackFileName = outJson["TrackFileName"];
        m_trackSourcePath = m_directory + "/" + std::string( outJson["TrackFileName"] );
    }
    else
    {
        m_trackFileName = "Track.mp3";
        m_trackSourcePath = m_directory + "/" + m_trackFileName;
    }

    if( outJson.contains( "PreviewPercent" ) )
    {
        m_previewPercent = outJson["PreviewPercent"];
    }

    if( outJson.contains( "NoteSpeed" ) )
    {
        m_noteSpeed = outJson["NoteSpeed"];
    }
    if( outJson.contains( "Duration" ) )
    {
        m_duration = outJson["Duration"];
    }
    if( outJson.contains( "BPM" ) )
    {
        m_bpm = outJson["BPM"];
    }
}

void TrackData::OnLoadNoteData( const json& outJson )
{

}

void TrackData::LoadNoteData()
{
    // #TODO: Temp, might be a custom format charted file
    Path noteDataFile( m_directory + "/NoteData.txt" );
    if( !noteDataFile.Exists )
    {
        return;
    }

    File metaFile( noteDataFile );
    json Root = json::parse( metaFile.Read() );

    ME_ASSERT_MSG( !Root.empty(), "Trying to read an empty track file." );

    if( Root.contains( "Notes" ) )
    {
        json& noteData = Root["Notes"];
        m_noteData.clear();
        m_noteData.reserve( noteData.size() );
        for( json& note : noteData )
        {
            NoteData noteEntry;
            noteEntry.m_editorLane = PadUtils::GetNewPadId( note["NoteName"] );
            noteEntry.m_noteName = PadUtils::GetPadId( noteEntry.m_editorLane );
            noteEntry.m_triggerTime = note["TriggerTime"];
            if( note.contains( "TriggerTimeMS" ) )
                noteEntry.m_triggerTimeMS = note["TriggerTimeMS"];

            m_noteData.push_back( noteEntry );
        }
    }
}
