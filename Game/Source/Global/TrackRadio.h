#pragma once
#include "Singleton.h"
#include "Components/Audio/AudioSource.h"
#include "CoreGame/TrackList.h"
#include "Pointers.h"
#include "CoreGame/AudioPack.h"
#include <memory>

class TrackData;

struct RadioArgs
{
    TrackData* CurrentTrack = nullptr;
    int CurrentTrackIndex = 0;
    bool UsePreviewMarker = false;
};

enum class RadioState
{
    None = 0,
    Loading,
    Seeking,
    Playing,
    Paused
};

class TrackRadio
{
    ME_SINGLETON_DEFINITION( TrackRadio );
public:
    TrackRadio() = default;

    void Play( RadioArgs inTrackArgs );
    // Plays a song that isn't in the library (the DLC page's preview of a song not downloaded
    // yet, from the files it fetched). The radio keeps its own copy of inTrack.
    void PlayGuest( const TrackData& inTrack, bool inUsePreviewMarker );
    bool IsGuest() const { return m_guest != nullptr; }
    // TrackDatabase::RemoveTrack: the song at inIndex is going and later ones move down.
    void OnTrackRemoved( int inIndex );
    bool IsPlaying() const;
    void Stop();
    void SetVolume( float inVolume );
    float GetTotalLength() const;
    float GetPositionMS() const;
    void Seek( float inPercent );
    void Update( float dt );
    // What the radio plays through and from where (AudioPack::SetSpeaker), kept across songs
    // until set back to a default RoomSpeaker with 1, 0, 1. The hideout's radio sets it every
    // frame (the room's own speaker); leaving the main menu takes it off.
    void SetSpeaker( const RoomSpeaker& inSpeaker, float inOpen, float inPan, float inLevel );
    // How loud the radio is playing right now (AudioPack::GetLevel); 0 when it isn't.
    float GetLevel();
    bool CanPlayNextTrack() const;
    void Resume();

    // The playing track, looked up by index each call: a finished DLC download appends to the
    // database and a removal shifts it, so a stored TrackData* would dangle. A guest is the
    // radio's own copy.
    const TrackData* GetCurrentTrack() const;
    int GetCurrentTrackIndex() const { return m_currentTrackIndex; }

    AudioSource m_currentlyPlaying;
    SharedPtr<AudioSource> m_currentlyPlayingPtr;
    std::vector<SharedPtr<AudioSource>> m_currentStems;
    RadioState m_radioState = RadioState::None;
    RadioArgs m_radioArgs;
    AudioPack m_audioPack;
private:

    bool PlayStem( const char* inFileName, bool inUsePreviewMarker );
    void Start( TrackData& inTrack, int inTrackIndex, bool inUsePreviewMarker );
    int m_currentTrackIndex = -1;
    std::unique_ptr<TrackData> m_guest;
    // How long the current song has been loading; one that never loads is given up on.
    float m_loadingFor = 0.f;
    float m_delayTimer = 0.f;
    float m_previewPercent = 0.f;
    // The previous track, fading out instead of being cut off (a click), and how long it has left.
    AudioPack m_fadingPack;
    RoomSpeaker m_speaker;
    float m_speakerOpen = 1.f;
    float m_speakerPan = 0.f;
    float m_speakerLevel = 1.f;
    float m_fadingTimer = 0.f;
};