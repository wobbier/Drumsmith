#pragma once
#include "Config.h"

struct NoteData
{
    //"EditorLane": 1,
    //    "TriggerTime" : 4.6472392082214359,
    //    "NoteName" : "snare1",
    //    "NoteObject" : {
    //    "instanceID": -53520
    //}

    uint8_t m_editorLane = 0;
    float   m_triggerTime = 0.f;
    std::string m_noteName;
};

class TrackData
    : public ConfigFile
{
public:
    TrackData( const Path& inPath );

    void OnSave( json& outJson ) override;


    void OnLoadConfig( const json& outJson ) override;

    void LoadNoteData();

    std::string m_trackName;
    std::string m_artistName;
    std::string m_albumArtPath;
    std::string m_trackSourcePath;
    float m_noteSpeed = 1.f;
    std::vector<NoteData> m_noteData;
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