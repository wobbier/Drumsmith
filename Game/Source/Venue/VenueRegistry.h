#pragma once
#include "Singleton.h"
#include "JSON.h"
#include <cstdint>
#include <functional>
#include <set>
#include <string>
#include <vector>

class TrackData;

// The sound a venue plays while the song loads and counts in (a crowd waiting for the band), faded
// out over the song's first seconds (VenueShow). venue.json: Ambience, AmbienceVolume, AmbienceFade.
struct VenueAmbience
{
    std::string SoundPath;      // logical; empty when the venue has none
    float Volume = 1.f;         // 0..1
    float FadeSeconds = 8.f;    // from the song's start to silence
};

// A venue scene found on disk: a folder holding venue.json (Name, Author, Scene, Preview, Version,
// Ambience) and the .lvl it names. Paths are logical (VFS), so mod overlays and paks are seen.
struct VenueEntry
{
    std::string Id;          // the folder name ("song:<folder>" for a song's own venue)
    std::string Name;
    std::string Author;
    std::string Folder;      // logical, "Assets/Venues/X"
    std::string ScenePath;   // logical path to the .lvl
    std::string PreviewPath; // logical path to the preview image; empty when there is none
    VenueAmbience Ambience;
    int Version = 1;
    bool SongLocal = false;
    bool Hidden = false;     // "Hidden": true in venue.json: usable (--venue) but not listed in the menu
};

// What the venue pick came to: a scene to load, or one of the built-in rooms.
struct VenueChoice
{
    bool IsScene = false;
    int Style = 0;           // VenueShow::Style (0 arena, 1 club, 2 festival) when !IsScene
    std::string ScenePath;   // when IsScene
    std::string Id;          // the registry id, "song:<folder>", or the path given to --venue
    std::string Reason;      // the rule that picked it, for the log ("--venue", "the VenueStyle setting"...)
    VenueAmbience Ambience;  // the venue's, when IsScene and it came from a venue.json
};

// Everything the pick reads, so ChooseVenue stays free of globals.
struct VenueChoiceInputs
{
    std::string CommandVenue;       // --venue <id|path|style name>
    int CommandStyle = -1;          // --venue-style N, -1 when not given
    std::string SongVenue;          // TrackData::m_venue, a registry id or style name
    bool HasSongLocal = false;      // the song's folder carries Venue/venue.json
    VenueEntry SongLocal;           // that venue (Id "song:<folder>")
    bool SongVenues = true;         // GameSettings::SongVenues
    std::string VenueId;            // GameSettings::VenueId
    int VenueStyle = 0;             // GameSettings::VenueStyle, 0..2 a room, 3 random
    uint32_t SongHash = 0;          // VenueSongHash( track name ), for Random
    const std::vector<VenueEntry>* Registry = nullptr;
    // A gig's venue (CoreGame/Progression.h): after --venue and --venue-style, over everything else.
    std::string GigVenue;
    // Whether free play has earned a venue (a registry id or a room name); empty means all are.
    // The player's VenueId and VenueStyle (and Random) only pick open venues; when the room they
    // name is locked, another open room is used, else the first open scene. Gigs, the song's own
    // venue and the command line aren't gated.
    std::function<bool( const std::string& )> VenueOpen;
};

// The rooms VenueShow builds in code, by name (any case): "Arena" 0, "Club" 1, "Festival" 2; -1 otherwise.
int VenueStyleFromName( const std::string& inName );
// The name of room inStyle ("Arena", "Club", "Festival"), empty past them.
std::string VenueStyleName( int inStyle );
// Repeatable per song: the hash VenueShow's Random uses (FNV-1a over the track name).
uint32_t VenueSongHash( const std::string& inTrackName );
// Order: --venue, --venue-style, then (if SongVenues) the song's Venue field and its own folder,
// then the player's VenueId, then VenueStyle. Anything unknown falls through to the next rule.
VenueChoice ChooseVenue( const VenueChoiceInputs& inInputs );

class VenueRegistry
{
    ME_SINGLETON_DEFINITION( VenueRegistry );

public:
    VenueRegistry() = default;

    static constexpr const char* kVenuesRoot = "Assets/Venues";
    static constexpr int kStyleCount = 3;

    // Rescans Assets/Venues/*/venue.json through the VFS. Bad venues are skipped with a log line.
    void Reload();
    // Same for another logical root (tests mount a temp folder under a prefix).
    void Reload( const std::string& inRoot );

    const std::vector<VenueEntry>& Get() const { return m_venues; }
    // By Id; null when unknown.
    const VenueEntry* Find( const std::string& inId ) const;
    // The venue in the song's folder (Venue/venue.json), Id "song:<folder>"; false when none or invalid.
    bool ForSong( const TrackData& inTrack, VenueEntry& outEntry ) const;
    // Reads one venue folder; false (with outReason) when venue.json is missing, bad or names no scene.
    static bool LoadFolder( const std::string& inFolder, const std::string& inId, bool inSongLocal, VenueEntry& outEntry, std::string& outReason );

    // The thin wrapper VenueShow::Build calls: gathers --venue, --venue-style, the song, the
    // settings and this registry, then ChooseVenue.
    VenueChoice ChooseForSong( const TrackData& inTrack ) const;
    // The same pick with no scenes in it (a scene that can't be a venue falls back to this room):
    // --venue or the song's Venue only when they name a room, --venue-style, the VenueStyle setting.
    VenueChoice ChooseRoomForSong( const TrackData& inTrack ) const;

    // The venue the gig being played forces on its songs (empty: none), set by GigSession.
    static std::string& GigVenue()
    {
        static std::string venue;
        return venue;
    }

    // Story mode's state of the venue for the song being played (VenueStory markers): set by
    // GigSession for a story song, or by --story / --story-song for a preview. Empty: no story.
    struct StoryStage
    {
        std::string Set;                // the story set's id
        int Song = -1;
        std::set<std::string> Flags;    // set from the start of the song (band_ flags never carry over)
        std::set<std::string> AtCue;    // set once the song reaches its cue
        std::string Cue;                // "intro", "verse", "first_chorus", "bridge", "solo", "outro", "song_end"
        // More flags landing at their own cues (ProgressionStorySong::Moments), in song order.
        struct Moment
        {
            std::string Cue;
            std::set<std::string> Flags;
            std::string Caption;
            double CaptionSeconds = 4.0;
        };
        std::vector<Moment> Moments;
        bool Active() const { return !Set.empty(); }
    };
    static StoryStage& Story()
    {
        static StoryStage stage;
        return stage;
    }

private:
    std::vector<VenueEntry> m_venues;
    bool m_loaded = false;
};
