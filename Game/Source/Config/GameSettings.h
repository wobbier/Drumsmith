#pragma once
#include "Singleton.h"
#include "JSON.h"
#include <map>
#include <set>
#include <string>
#include <vector>

class GameSettings
{
    ME_SINGLETON_DEFINITION( GameSettings );

public:
    GameSettings();

    void Save();

    float RadioVolume = .5f;
    // The DLC servers the catalogue is read from, in the player's order (Docs/Songs-and-DLC.md):
    // host names or URLs without a trailing slash. DLCURL is the first of them, kept for
    // settings files and code from when there was one.
    std::vector<std::string> DLCServers;
    std::string DLCURL;
    // A server as it is stored: trimmed, no trailing slashes. Empty when there is nothing left.
    static std::string CleanServer( std::string inServer );
    // Adds a server (cleaned); false when it is empty or already listed.
    bool AddDLCServer( const std::string& inServer );
    bool RemoveDLCServer( const std::string& inServer );
    std::string PreferredMidiDevice;
    // The delays the highway makes up for (Docs/Latency-and-Responsiveness.md), 0 to kMaxLatencyMs.
    static constexpr int kMaxLatencyMs = 250;
    int AudioLatency = 0;
    int VideoLatency = 0;
    // A click on every beat of the song's beat grid, over the song (Docs/Audio.md → Metronome).
    bool Metronome = false;
    // Scroll speed of the note highway, as a multiple of each chart's NoteSpeed (0.5 to 2).
    float HighwaySpeed = 1.f;
    // How playing the right pad with the wrong technique (closed for open hi-hat, head for a
    // rimshot) is judged: 0 off (it's a hit), 1 lenient (one grade lower, combo kept), 2 strict (a miss).
    int TechniqueStrictness = 1;
    // The stage lights behind the highway (Docs/Stage-Lighting.md): 0 off, 1 on without strobes or
    // flashes (photosensitivity), 2 full show.
    int StageLighting = 2;
    // The venue under the highway (Docs/Venue-and-Band.md): 0 off (a black backdrop), 1 the stage
    // and band, 2 the stage, band and crowd.
    int Venue = 2;
    // Whose camera cuts the venue plays: 0 the live show's (VENUE), 1 the music video's (MV VENUE)
    // where the chart has one.
    int VenueCamera = 0;
    // Found footage (Docs/Venue-and-Band.md): the guests' camcorders burn their date and time into
    // the picture.
    bool VenueDateStamp = false;
    // Which room (VenueShow::Style): 0 arena, 1 club, 2 festival, 3 a random one per song.
    int VenueStyle = 0;
    // A scene venue picked from Assets/Venues (Venue/VenueRegistry.h) by its id; empty uses VenueStyle.
    std::string VenueId;
    // Whether a song may bring its own venue (its Venue field or Venue/ folder) over the player's pick.
    bool SongVenues = true;
    // Where a chart's lyrics show (Docs/Venue-and-Band.md → Lyrics): 0 off, 1 the HUD, 2 the
    // venue's LED wall, 3 both.
    int Lyrics = 3;
    // Favorite songs, by song folder name (TrackDatabase::FavoriteKey), so a rescan or a moved
    // DLC folder keeps them.
    std::set<std::string> FavoriteTracks;
    // The tempo each practice lesson was last played at, by lesson id (CoreGame/Practice.h).
    std::map<std::string, int> PracticeTempos;
    bool LyricsOnHud() const { return ( Lyrics & 1 ) != 0; }
    bool LyricsInVenue() const { return ( Lyrics & 2 ) != 0; }
private:
    json RootJson;
    void Load();
};