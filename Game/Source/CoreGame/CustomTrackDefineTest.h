#include <iostream>
#include <fstream>
#include <map>
#include <vector>
#include <sstream>
#include "Singleton.h"
#include "Path.h"

struct SyncTrack
{
    int time;
    std::string value;
};

struct DrumEvent
{
    int time;
    char typeCode;
    std::vector<int> values;
};

struct LegacySongMetaData
{
    std::string m_name;
    std::string m_artist;
    std::string m_album;
    std::string m_genre;
    std::string m_year;
    int m_songLength;
    std::string m_charter;
    int m_previewStartTime = -1;
    std::string m_flavorText;
};

struct Song
{
    std::string name;
    std::string artist;
    std::string musicStream;
    std::string albumArtName;
    int noteCount = 0;
    int offset = 0;
    std::map<int, SyncTrack> syncTracks;
    std::map<int, std::vector<DrumEvent>> easyDrums;
};

class CustomTrackDefineTest
{
    ME_SINGLETON_DEFINITION( CustomTrackDefineTest );
public:
    CustomTrackDefineTest() = default;

    LegacySongMetaData readSongMetaData( const std::string& filePath );
    Song readSongFile( const std::string& filePath );
    bool ParseMidi( Path& inFilePath );
};
