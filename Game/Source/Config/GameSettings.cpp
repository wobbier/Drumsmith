#include "GameSettings.h"
#include "CLog.h"
#include "File.h"

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
}

