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

private:
    json RootJson;
    void Load();
};