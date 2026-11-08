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
private:
    json RootJson;
    void Load();
};