#include <iostream>
#include <fstream>
#include <map>
#include <vector>
#include <sstream>
#include "Singleton.h"
#include "Path.h"
#include "TrackList.h"

namespace smf { class MidiFile; }

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
    std::string m_icon;
    int m_songLength = 0;
    bool m_proDrums = false;
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
    bool ParseMidi( Path& inFilePath, TrackData& outTrackData, LegacySongMetaData& inLegacyData );
    // Reads a MIDI file (tolerating running status after meta events) and time-analyses it.
    static bool ReadMidi( smf::MidiFile& outMidi, const std::string& inPath );
    // The beat grid of a MIDI file's tempo map, up to inEndSeconds.
    static std::vector<BeatData> ReadMidiBeats( smf::MidiFile& inMidi, double inEndSeconds );
    static std::vector<BeatData> ReadMidiBeats( const std::string& inPath, double inEndSeconds );
    // The light show of a Rock Band chart: VENUE lighting cues, keyframes, fog, pyro and
    // spotlights, plus the EVENTS track's sections and crowd states.
    static VenueData ReadMidiVenue( smf::MidiFile& inMidi );
};
