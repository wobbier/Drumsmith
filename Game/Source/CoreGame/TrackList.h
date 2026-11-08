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
    // How the pad is struck (rim, bell, ...), and how hard: 0-127, 100 when the chart doesn't say.
    // Ghost notes are quiet (<= 40), accents loud (>= 120).
    Articulation m_articulation = Articulation::Normal;
    uint8_t m_velocity = 100;

    bool operator==( const NoteData& other ) const
    {
        return m_triggerTime == other.m_triggerTime && m_editorLane == other.m_editorLane;
    }
};

// A beat of the chart's tempo map, for the highway's beat and measure lines.
struct BeatData
{
    float m_time = 0.f;
    bool m_measure = false;
};

// A timed text event from the chart's VENUE or EVENTS track: a lighting cue ("strobe_fast"; empty
// for the default look), a section name ("chorus_1") or a crowd state ("intense").
struct TimedCueData
{
    float m_time = 0.f;
    std::string m_name;
};

// The light show a Rock Band chart carries beside its notes (Docs/Stage-Lighting.md). Times are
// seconds into the song. Every list is empty for charts without a VENUE / EVENTS track.
struct VenueData
{
    enum class Keyframe : int { Next = 0, Previous = 1, First = 2 };
    struct KeyframeData { float m_time = 0.f; Keyframe m_step = Keyframe::Next; };
    struct FogData { float m_time = 0.f; bool m_on = false; };
    // A spotlight on one band member (VENUE notes 37-41 give the slot, 0-4) while the note is held.
    struct SpotlightData { float m_start = 0.f; float m_end = 0.f; int m_slot = 0; };

    std::vector<TimedCueData> m_lighting;     // "[lighting (x)]", and RB2's "[verse]" / "[chorus]"
    std::vector<KeyframeData> m_keyframes;    // notes 48 / 49 / 50: step the manual cues
    std::vector<FogData> m_fog;               // "[FogOn]" / "[FogOff]"
    std::vector<float> m_bonusFx;             // "[bonusfx]" and notes 96 / 97: pyro
    std::vector<SpotlightData> m_spotlights;
    std::vector<TimedCueData> m_sections;     // EVENTS "[section x]"
    std::vector<TimedCueData> m_crowd;        // EVENTS "[crowd_x]"

    bool HasLighting() const { return !m_lighting.empty(); }
    bool IsEmpty() const { return m_lighting.empty() && m_keyframes.empty() && m_fog.empty() && m_bonusFx.empty() && m_spotlights.empty() && m_sections.empty() && m_crowd.empty(); }
    void Clear() { *this = VenueData(); }
    void Save( json& outJson ) const;
    void Load( const json& inJson );
};

class TrackData
{
public:
    TrackData() = default;
    TrackData( const Path& inPath );

    void Save();
    // Writes NoteData.txt only (notes and beats), leaving TrackData.txt alone.
    void SaveNoteData();
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
    // Empty when the chart has no tempo map (native charts; conversions before beats were kept).
    std::vector<BeatData> m_beats;
    VenueData m_venue;

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
