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
    DLCURL = DLCServers.empty() ? std::string() : DLCServers.front();
    RootJson["DLCURL"] = DLCURL;
    RootJson["DLCServers"] = DLCServers;
    RootJson["Device"] = PreferredMidiDevice;
    RootJson["AudioLatency"] = AudioLatency;
    RootJson["VideoLatency"] = VideoLatency;
    RootJson["HighwaySpeed"] = HighwaySpeed;
    RootJson["Metronome"] = Metronome;
    RootJson["TechniqueStrictness"] = TechniqueStrictness;
    RootJson["StageLighting"] = StageLighting;
    RootJson["Venue"] = Venue;
    RootJson["VenueCamera"] = VenueCamera;
    RootJson["VenueDateStamp"] = VenueDateStamp;
    RootJson["VenueStyle"] = VenueStyle;
    RootJson["VenueId"] = VenueId;
    RootJson["SongVenues"] = SongVenues;
    RootJson["Lyrics"] = Lyrics;
    RootJson["Favorites"] = FavoriteTracks;
    RootJson["PracticeTempos"] = PracticeTempos;

    Path settingsFilePath( "Settings.json" );
    File settingsFile( settingsFilePath );
    settingsFile.Write(RootJson.dump());
}

std::string GameSettings::CleanServer( std::string inServer )
{
    const size_t first = inServer.find_first_not_of( " \t\r\n" );
    if( first == std::string::npos )
    {
        return {};
    }
    inServer = inServer.substr( first, inServer.find_last_not_of( " \t\r\n" ) - first + 1 );
    while( !inServer.empty() && inServer.back() == '/' )
    {
        inServer.pop_back();
    }
    return inServer;
}


bool GameSettings::AddDLCServer( const std::string& inServer )
{
    const std::string server = CleanServer( inServer );
    if( server.empty() || std::find( DLCServers.begin(), DLCServers.end(), server ) != DLCServers.end() )
    {
        return false;
    }
    DLCServers.push_back( server );
    DLCURL = DLCServers.front();
    return true;
}


bool GameSettings::RemoveDLCServer( const std::string& inServer )
{
    const auto it = std::find( DLCServers.begin(), DLCServers.end(), CleanServer( inServer ) );
    if( it == DLCServers.end() )
    {
        return false;
    }
    DLCServers.erase( it );
    DLCURL = DLCServers.empty() ? std::string() : DLCServers.front();
    return true;
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

    if( RootJson.contains( "DLCURL" ) && RootJson["DLCURL"].is_string() )
    {
        DLCURL = RootJson["DLCURL"];
    }
    DLCServers.clear();
    if( RootJson.contains( "DLCServers" ) && RootJson["DLCServers"].is_array() )
    {
        for( const json& server : RootJson["DLCServers"] )
        {
            if( server.is_string() )
            {
                AddDLCServer( server.get<std::string>() );
            }
        }
    }
    else
    {
        // A settings file from when there was one server.
        AddDLCServer( DLCURL );
    }
    DLCURL = DLCServers.empty() ? std::string() : DLCServers.front();

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

    if( RootJson.contains( "Metronome" ) && RootJson["Metronome"].is_boolean() )
    {
        Metronome = RootJson["Metronome"].get<bool>();
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

    if( RootJson.contains( "VenueDateStamp" ) && RootJson["VenueDateStamp"].is_boolean() )
    {
        VenueDateStamp = RootJson["VenueDateStamp"].get<bool>();
    }

    if( RootJson.contains( "VenueStyle" ) && RootJson["VenueStyle"].is_number() )
    {
        VenueStyle = std::clamp( RootJson["VenueStyle"].get<int>(), 0, 3 );
    }

    VenueId = RootJson.contains( "VenueId" ) && RootJson["VenueId"].is_string() ? RootJson["VenueId"].get<std::string>() : std::string();

    if( RootJson.contains( "SongVenues" ) && RootJson["SongVenues"].is_boolean() )
    {
        SongVenues = RootJson["SongVenues"].get<bool>();
    }

    if( RootJson.contains( "Lyrics" ) && RootJson["Lyrics"].is_number() )
    {
        Lyrics = std::clamp( RootJson["Lyrics"].get<int>(), 0, 3 );
    }

    if( RootJson.contains( "Favorites" ) && RootJson["Favorites"].is_array() )
    {
        FavoriteTracks.clear();
        for( const json& favorite : RootJson["Favorites"] )
        {
            if( favorite.is_string() )
            {
                FavoriteTracks.insert( favorite.get<std::string>() );
            }
        }
    }

    PracticeTempos.clear();
    if( RootJson.contains( "PracticeTempos" ) && RootJson["PracticeTempos"].is_object() )
    {
        for( const auto& [lesson, tempo] : RootJson["PracticeTempos"].items() )
        {
            if( tempo.is_number() )
            {
                PracticeTempos[lesson] = tempo.get<int>();
            }
        }
    }

    if( RootJson.contains( "HighwaySpeed" ) && RootJson["HighwaySpeed"].is_number() )
    {
        HighwaySpeed = std::clamp( RootJson["HighwaySpeed"].get<float>(), 0.5f, 2.f );
    }
}

