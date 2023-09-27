#pragma once
#include "Config.h"

class TrackData
    : public ConfigFile
{
public:
    TrackData( const Path& inPath );

    void OnSave( json& outJson ) override;


    void OnLoadConfig( const json& outJson ) override;

    std::string m_trackName;
    std::string m_artistName;
    std::string m_albumArtPath;
    std::string m_trackSourcePath;
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

class TrackDatabase
{
    ME_SINGLETON_DEFINITION( TrackDatabase );
public:
    TrackDatabase();

    TrackList m_trackList;
};