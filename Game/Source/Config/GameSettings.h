#pragma once
#include "Singleton.h"
#include "JSON.h"

class GameSettings
{
    ME_SINGLETON_DEFINITION( GameSettings );

public:
    GameSettings();

    void Save();

    float RadioVolume = .5f;
    std::string DLCURL;
    std::string PreferredMidiDevice;
    int AudioLatency = 0;
    int VideoLatency = 0;
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
private:
    json RootJson;
    void Load();
};