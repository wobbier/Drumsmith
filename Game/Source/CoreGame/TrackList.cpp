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
    m_albumArtPath = m_configFile.FilePath.GetDirectoryString() + "/Album.png";
    m_trackSourcePath = m_configFile.FilePath.GetDirectoryString() + "/Track.mp3";
    m_noteSpeed = outJson["NoteSpeed"];
}

void TrackData::LoadNoteData()
{
    ME_ASSERT_MSG( !Root.empty(), "Trying to read an empty track file." );

    if( Root.contains( "Notes" ) )
    {
        json& noteData = Root["Notes"];
        m_noteData.reserve( noteData.size() );
        for( json& note : noteData )
        {
            NoteData noteEntry;
            noteEntry.m_editorLane = note["EditorLane"];
            noteEntry.m_noteName = note["NoteName"];
            noteEntry.m_triggerTime = note["TriggerTime"];

            m_noteData.push_back( noteEntry );
        }
    }
}
