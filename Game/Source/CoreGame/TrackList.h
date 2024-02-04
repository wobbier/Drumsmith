#pragma once
#include "Config.h"
#include "Editor/PadBindings.h"

struct NoteData
{
    //"EditorLane": 1,
    //    "TriggerTime" : 4.6472392082214359,
    //    "NoteName" : "snare1",
    //    "NoteObject" : {
    //    "instanceID": -53520
    //}

    PadId m_editorLane = PadId::Invalid;
    float   m_triggerTime = 0.f;
    uint32_t   m_triggerTimeMS = 0u;
    // delete this
    std::string m_noteName;

    bool operator==( const NoteData& other ) const
    {
        return m_triggerTime == other.m_triggerTime && m_editorLane == other.m_editorLane;
    }
};

class TrackData
{
public:
    TrackData() = default;
    TrackData( const Path& inPath );

    void Save();
    void Load();

    void OnSaveTrackData( json& outJson );
    void OnSaveNoteData( json& outJson );

    void OnLoadTrackData( const json& outJson );
    void OnLoadNoteData( const json& outJson );

    void LoadNoteData();

    std::string m_trackName;
    std::string m_artistName;
    std::string m_albumName;
    std::string m_albumArtPath;
    std::string m_trackSourcePath;
    std::string m_trackFileName;
    float m_noteSpeed = 1.f;
    float m_duration = 1.f;
    float m_durationMS = 1.f;
    float m_previewPercent = 0.f;
    int m_bpm = 69;

    std::vector<NoteData> m_noteData;

private:
    std::string m_directory;
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

    void ExportMidiTrackMetaData();

    TrackList m_trackList;
};
