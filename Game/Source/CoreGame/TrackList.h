#pragma once
#include "Config.h"
#include "Editor/PadBindings.h"

struct NoteData
{
    //"EditorLane": 1,
    //    "TriggerTime" : 4.6472392082214359,
    //    "NoteName" : "snare1",
    //    "NoteObject" : {
    //    "instanceID": -53520
    //}

    PadId m_editorLane = PadId::Invalid;
    float   m_triggerTime = 0.f;
    uint32_t   m_triggerTimeMS = 0u;
    // delete this
    std::string m_noteName;

    bool operator==( const NoteData& other ) const
    {
        return m_triggerTime == other.m_triggerTime && m_editorLane == other.m_editorLane;
    }
};

class TrackData
{
public:
    TrackData() = default;
    TrackData( const Path& inPath );

    void Save();
    void Load();

    void OnSaveTrackData( json& outJson );
    void OnSaveNoteData( json& outJson );

    void OnLoadTrackData( const json& inJson );
    void OnLoadNoteData( const json& inJson );

    void LoadNoteData();

    std::string m_trackName;
    std::string m_artistName;
    std::string m_albumName;
    std::string m_genre;
    std::string m_icon;
    int m_year = 1994;
    std::string m_albumArtPath;
    std::string m_albumArtFilename;
    std::string m_trackSourcePath;
    std::string m_trackFileName;
    std::string m_dlcSource;
    float m_noteSpeed = 1.f;
    float m_duration = 1.f;
    float m_durationMS = 1.f;
    float m_previewPercent = 0.f;
    int m_bpm = 69;
    int m_noteCount = 0;
    bool m_proDrums = false;

    std::vector<NoteData> m_noteData;

private:
    std::string m_directory;
};

class TrackList
    : public ConfigFile
{
public:
    TrackList();

    void OnSave( json& outJson ) override;
    void OnLoadConfig( const json& outJson ) override;

    std::vector<TrackData> m_tracks;
};

enum class TrackListSort : uint32_t
{
    None = 0,
    Title,
    Artist,
    Year,
};

enum class TrackListFilter : uint32_t
{
    // This isn't gonna work
    None = 0,
    Drumsmith = 1,
    RockBand,
    RockBand2,
    RockBand3,
    RockBand4,
    RockBandBlitz,
    GuitarHero,
    GuitarHero2,
    GuitarHero3,
    GuitarHero4,
    GuitarHero5,
    GuitarHero5DLC,
    GreenDayRockBand,
    GuitarHeroWorldTour,
    GuitarHeroWorldTourDLC, // maybe group this?
    LegoRockBand,
    Other,
    Count
};

class TrackDatabase
{
    ME_SINGLETON_DEFINITION( TrackDatabase );
public:
    TrackDatabase();

    void Reload();
    bool RegisterNewTrack( const std::string& inDirectory );
    void ExportMidiTrackMetaData();

    std::vector<unsigned int>& SortTracks( TrackListSort inSortBy, TrackListFilter inFilterBy );
    std::vector<unsigned int>& FilterTracks( TrackListFilter inFilterBy );

    void GatherFilterCounts();

    std::string GetFilterName( TrackListFilter inFilter );

    TrackListSort m_currentSort = TrackListSort::None;
    TrackListFilter m_currentFilter = TrackListFilter::None;
    bool m_needsSort = true;
    bool m_pendingInitialSort = true;
    TrackList m_trackList;

    int m_sortedSize = 0;
    std::vector<unsigned int> m_sortedIndices;
    std::vector<unsigned int> m_filterMatches;
};
