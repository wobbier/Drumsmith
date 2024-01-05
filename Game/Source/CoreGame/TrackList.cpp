#include "TrackList.h"
#include <filesystem>
#include "Core\Assert.h"
#include "CustomTrackDefineTest.h"

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


TrackData ConvertFromLegacy( const std::string& inTrackDirectory, Song& inLegacyData, TrackData& outNewTrack )
{
    // bro 💀 https://xkcd.com/927/
    LegacySongMetaData metadata = CustomTrackDefineTest::GetInstance().readSongMetaData( inTrackDirectory + "/song.ini" );

    // We want a clean file for now.
    outNewTrack.Clear();

    outNewTrack.m_trackName = metadata.m_name;
    outNewTrack.m_artistName = metadata.m_artist;
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
    outNewTrack.m_albumArtPath = albumArtPath.GetLocalPathString();

    // I don't know how much this differs from chart to chart

    Path songFile( inTrackDirectory + "song.ogg" );
    if( !songFile.Exists )
    {
        // opus will require some manual converting... as fmod doesn't support this type atm
        outNewTrack.m_trackFileName = "song.opus";
        outNewTrack.m_trackSourcePath = inTrackDirectory + "song.opus";
    }
    else
    {
        outNewTrack.m_trackFileName = "song.ogg";
        outNewTrack.m_trackSourcePath = inTrackDirectory + "song.ogg";
    }

    outNewTrack.m_bpm = 110;//(float)inLegacyData.syncTracks[0].value >> 3;
    outNewTrack.m_noteSpeed = 10;//(float)inLegacyData.syncTracks[0].value >> 3;


    for (auto& mapIt : inLegacyData.easyDrums)
    {
        for( auto& it : mapIt.second )
        {
            NoteData newNote;
            newNote.m_triggerTime = it.time / 1000.f;
            newNote.m_triggerTimeMS = it.time;
            newNote.m_editorLane = ConvertLegacyPad(it.values[0]);
            newNote.m_noteName = PadUtils::GetPadId( newNote.m_editorLane );
            outNewTrack.m_noteData.emplace_back( newNote );
        }
    }
    outNewTrack.m_bpm = 180.f;

    outNewTrack.Save();
    return outNewTrack;
}

TrackDatabase::TrackDatabase()
{
    fs::path rootPath = Path( "Assets/DLC" ).FullPath;  // Replace with your directory path

    try {
        for( const auto& entry : fs::directory_iterator( rootPath ) )
        {
            if( entry.is_directory() )
            {
                // Check for any Custom DLC from other formats
                bool exists = fileExistsInDirectory( entry.path(), "song.ini" );
                if( exists )
                {
                    Path chartFilePath = Path( entry.path().u8string() + "/notes.chart" );
                    Song rbCustomTrack;
                    if( chartFilePath.Exists )
                    {
                        rbCustomTrack = CustomTrackDefineTest::GetInstance().readSongFile( chartFilePath.FullPath );
                    }
                    TrackData newTrack = TrackData( Path( chartFilePath.GetDirectoryString() + "/NoteData.txt" ) );
                    
                    m_trackList.m_tracks.push_back( ConvertFromLegacy( chartFilePath.GetDirectoryString(), rbCustomTrack, newTrack ) );
                    //newTrack.Save();
                }
                else
                {
                    bool exists = fileExistsInDirectory( entry.path(), "NoteData.txt" );
                    if( exists )
                    {
                        m_trackList.m_tracks.emplace_back( TrackData( Path( entry.path().u8string() + "/NoteData.txt" ) ) );
                        m_trackList.m_tracks.back().Load();
                        std::cout << "File exists in directory: " << entry.path().u8string() << std::endl;
                    }
                    else
                    {
                        std::cout << "File does not exist in directory: " << entry.path().u8string() << std::endl;
                    }
                }
            }
        }
    }
    catch( fs::filesystem_error& e ) {
        std::cout << e.what() << std::endl;
    }

}

TrackData::TrackData( const Path& inPath )
    : ConfigFile( inPath )
{

}

void TrackData::OnSave( json& outJson )
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
    outJson["SongName"] = m_trackName;
    outJson["SongArtist"] = m_artistName;
    outJson["AlbumName"] = m_albumName;
    //m_albumArtPath = m_configFile.FilePath.GetDirectoryString() + "/Album.png";
    //m_trackSourcePath = m_configFile.FilePath.GetDirectoryString() + "/Track.mp3";
    outJson["NoteSpeed"] = m_noteSpeed;
    outJson["Duration"] = m_duration;
    outJson["BPM"] = m_bpm;
    outJson["TrackFileName"] = m_trackFileName;
    outJson["PreviewPercent"] = m_previewPercent;

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

void TrackData::OnLoadConfig( const json& outJson )
{
    if( outJson.contains( "SongName" ) )
    {
        m_trackName = outJson["SongName"];
    }
    if( outJson.contains( "SongArtist" ) )
    {
        m_artistName = outJson["SongArtist"];
    }
    if( outJson.contains( "AlbumName" ) )
    {
        m_albumName = outJson["AlbumName"];
    }
    m_albumArtPath = m_configFile.FilePath.GetDirectoryString() + "Album.png";
    if( outJson.contains( "TrackFileName" ) )
    {
        m_trackFileName = outJson["TrackFileName"];
        m_trackSourcePath = m_configFile.FilePath.GetDirectoryString() + std::string( outJson["TrackFileName"] );
    }
    else
    {
        m_trackFileName = "Track.mp3";
        m_trackSourcePath = m_configFile.FilePath.GetDirectoryString() + m_trackFileName;
    }

    if( outJson.contains( "PreviewPercent" ) )
    {
        m_previewPercent = outJson["PreviewPercent"];
    }

    m_noteSpeed = outJson["NoteSpeed"];
    m_duration = outJson["Duration"];
    m_bpm = outJson["BPM"];
}

void TrackData::LoadNoteData()
{
    // #TODO: Temp, might be a custom format charted file
    if( !m_configFile.FilePath.Exists )
    {
        return;
    }

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
