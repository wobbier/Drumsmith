#include "GameSettings.h"
#include "CLog.h"
#include "File.h"
#include <algorithm>

GameSettings::GameSettings()
{
    Path settingsFilePath( "Settings.json" );
    if( !settingsFilePath.Exists )
    {
        Save();
    }
    else
    {
        File settingsFile( settingsFilePath );
        RootJson = json::parse( settingsFile.Read() );
        Load();
    }
}

void GameSettings::Save()
{
    RootJson = json();
    RootJson["RadioVolume"] = RadioVolume;
    RootJson["DLCURL"] = DLCURL;
    RootJson["Device"] = PreferredMidiDevice;
    RootJson["AudioLatency"] = AudioLatency;
    RootJson["VideoLatency"] = VideoLatency;
    RootJson["HighwaySpeed"] = HighwaySpeed;
    RootJson["TechniqueStrictness"] = TechniqueStrictness;
    RootJson["StageLighting"] = StageLighting;
    RootJson["Venue"] = Venue;
    RootJson["VenueCamera"] = VenueCamera;

    Path settingsFilePath( "Settings.json" );
    File settingsFile( settingsFilePath );
    settingsFile.Write(RootJson.dump());
}

void GameSettings::Load()
{
    if( RootJson.empty() )
    {
        YIKES( "Loading game settings without any data" );
        return;
    }

    if( RootJson.contains( "RadioVolume" ) )
    {
        RadioVolume = RootJson["RadioVolume"];
    }

    if( RootJson.contains( "DLCURL" ) )
    {
        DLCURL = RootJson["DLCURL"];
    }

    if( RootJson.contains( "Device" ) )
    {
        PreferredMidiDevice = RootJson["Device"];
    }

    if( RootJson.contains( "AudioLatency" ) )
    {
        AudioLatency = RootJson["AudioLatency"];
    }

    if( RootJson.contains( "VideoLatency" ) )
    {
        VideoLatency = RootJson["VideoLatency"];
    }

    if( RootJson.contains( "TechniqueStrictness" ) && RootJson["TechniqueStrictness"].is_number() )
    {
        TechniqueStrictness = std::clamp( RootJson["TechniqueStrictness"].get<int>(), 0, 2 );
    }

    if( RootJson.contains( "StageLighting" ) && RootJson["StageLighting"].is_number() )
    {
        StageLighting = std::clamp( RootJson["StageLighting"].get<int>(), 0, 2 );
    }

    if( RootJson.contains( "Venue" ) && RootJson["Venue"].is_number() )
    {
        Venue = std::clamp( RootJson["Venue"].get<int>(), 0, 2 );
    }

    if( RootJson.contains( "VenueCamera" ) && RootJson["VenueCamera"].is_number() )
    {
        VenueCamera = std::clamp( RootJson["VenueCamera"].get<int>(), 0, 1 );
    }

    if( RootJson.contains( "HighwaySpeed" ) && RootJson["HighwaySpeed"].is_number() )
    {
        HighwaySpeed = std::clamp( RootJson["HighwaySpeed"].get<float>(), 0.5f, 2.f );
    }
}

