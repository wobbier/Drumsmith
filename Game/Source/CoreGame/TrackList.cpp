#include "TrackList.h"
#include <filesystem>
#include "Core\Assert.h"

TrackList::TrackList()
    : ConfigFile(Path("Assets/TrackDatabase.json"))
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

TrackDatabase::TrackDatabase()
{
    fs::path rootPath = Path("Assets/DLC").FullPath;  // Replace with your directory path
    
    try {
        for( const auto& entry : fs::directory_iterator( rootPath ) ) {
            if( entry.is_directory() ) {
                bool exists = fileExistsInDirectory( entry.path(), "NoteData.txt" ); // Replace 'your_file.txt' with the file you're looking for
                if( exists ) {
                    m_trackList.m_tracks.emplace_back( TrackData( Path( entry.path().string() + "/NoteData.txt" )));
                    m_trackList.m_tracks.back().Load();
                    std::cout << "File exists in directory: " << entry.path().string() << std::endl;
                }
                else {
                    std::cout << "File does not exist in directory: " << entry.path().string() << std::endl;
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
    m_noteData.erase( std::unique( m_noteData.begin(), m_noteData.end()), m_noteData.end() );
    outJson["SongName"] = m_trackName;
    outJson["SongArtist"] = m_artistName;
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
        noteEntry["TriggerTimeMS"] = (uint32_t)(note.m_triggerTime * 1000.f);

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
    m_albumArtPath = m_configFile.FilePath.GetDirectoryString() + "Album.png";
    if ( outJson.contains("TrackFileName") )
    {
        m_trackFileName = outJson["TrackFileName"];
        m_trackSourcePath = m_configFile.FilePath.GetDirectoryString() + std::string(outJson["TrackFileName"]);
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
            if(note.contains("TriggerTimeMS") )
            noteEntry.m_triggerTimeMS = note["TriggerTimeMS"];

            m_noteData.push_back( noteEntry );
        }
    }
}
