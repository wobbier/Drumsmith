#pragma once
#include "Config.h"
#include "Editor/PadBindings.h"
#include <array>
#include <string>
#include <vector>

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
    std::vector<float> m_bonusFx;             // "[bonusfx]" / "[bonusfx_optional]": pyro
    std::vector<SpotlightData> m_spotlights;
    std::vector<TimedCueData> m_sections;     // EVENTS "[section x]"
    std::vector<TimedCueData> m_crowd;        // EVENTS "[crowd_x]"

    // The band (Docs/Venue-and-Band.md). Members in the order of m_bandStates.
    enum Member : int { Drums = 0, Guitar, Bass, Vocals, Keys, MemberCount };
    // A held span, of one member where it matters (singalong notes 85-87, sung vocal notes).
    struct SpanData { float m_start = 0.f; float m_end = 0.f; int m_member = 0; };
    // A drummer's stroke from PART DRUMS animation notes 24-51: which limb hits which piece.
    enum class Limb : int { LeftHand = 0, RightHand, LeftFoot, RightFoot };
    enum class DrumPiece : int { Kick = 0, HiHat, Snare, Tom1, Tom2, FloorTom, Crash1, Crash2, Ride, HiHatPedal };
    struct DrumHitData { float m_time = 0.f; Limb m_limb = Limb::RightHand; DrumPiece m_piece = DrumPiece::Snare; bool m_soft = false; };

    // Camera cuts, VENUE's and the music video's (MV VENUE). A cut is a shot name the director
    // frames: RB3 and directed cuts keep theirs ("coop_g_near", "directed_guitar_cls"), RB2 note
    // cuts become "auto" plus the constraints held with them ("auto only_close focus_drums").
    std::vector<TimedCueData> m_cameras;
    std::vector<TimedCueData> m_mvCameras;
    // Post-processing looks (RB2 notes 96-110, RB3 "[name.pp]"): "ProFilm_a", "film_b+w", ...
    std::vector<TimedCueData> m_postFx;
    std::vector<TimedCueData> m_mvPostFx;
    std::vector<SpanData> m_singalong;        // VENUE notes 85-87: bass, drums, guitar sing along
    // Each member's animation state from its PART track: "idle", "play", "mellow", "intense",
    // "idle_realtime", "idle_intense", "play_solo".
    std::array<std::vector<TimedCueData>, MemberCount> m_bandStates;
    std::vector<DrumHitData> m_drumHits;
    // Expert gem times (a chord is one strum) for the guitarist, bassist and keyboardist.
    std::vector<float> m_guitarStrums;
    std::vector<float> m_bassStrums;
    std::vector<float> m_keysStrums;
    std::vector<SpanData> m_vocalNotes;       // PART VOCALS sung notes (36-84)

    bool HasLighting() const { return !m_lighting.empty(); }
    bool IsEmpty() const
    {
        bool bandEmpty = true;
        for( const auto& states : m_bandStates ) bandEmpty = bandEmpty && states.empty();
        return m_lighting.empty() && m_keyframes.empty() && m_fog.empty() && m_bonusFx.empty() && m_spotlights.empty() && m_sections.empty() && m_crowd.empty()
            && m_cameras.empty() && m_mvCameras.empty() && m_postFx.empty() && m_mvPostFx.empty() && m_singalong.empty() && bandEmpty && m_drumHits.empty()
            && m_guitarStrums.empty() && m_bassStrums.empty() && m_keysStrums.empty() && m_vocalNotes.empty();
    }
    static const char* MemberName( int inMember );
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
