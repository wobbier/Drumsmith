#pragma once
#include <ECS/Core.h>
#include <Components/Transform.h>
#include "Events/EventReceiver.h"
#include "CoreGame/TrackList.h"
#include "Components/Audio/AudioSource.h"
#include <unordered_map>
#include <MidiDeviceManager.h>

class NoteHighwayCore final
	: public Core<NoteHighwayCore>
	, public EventReceiver
{
public:
	NoteHighwayCore();
	~NoteHighwayCore();

	virtual void Init() final;

	virtual void OnEntityAdded(Entity& NewEntity) final;
    virtual void OnEntityRemoved( Entity& InEntity ) final;

    void OnAddedToWorld() override;
    void OnRemovedFromWorld() override;

    void OnStop() override;

    virtual void Update( const UpdateContext& context ) final;
    bool OnEvent( const BaseEvent& evt ) override;

	void SetupTrack( TrackData& inTrackData );
	void ShutdownTrack();

	int32_t LegacyConvertLane( const std::string& lane );
	const char* ConvertPadToLane( int16_t lane );

	std::map<std::string, EntityHandle> m_lanes;
	std::map<PadId, std::string> m_notePrefabs;
	SharedPtr<AudioSource> m_currentTrack;
    void OnStart() override;

	EntityHandle TrackMover;
	TrackData* m_trackData = nullptr;

private:
#if USING( ME_EDITOR )
	virtual void OnEditorInspect() final;

#endif
    bool PlayStem( const char* inFileName, bool inUsePreviewMarker );

#if USING(ME_PLATFORM_WIN64)
	MidiDeviceManager m_midi;
#endif
    std::vector<SharedPtr<AudioSource>> m_currentStems;
};

ME_REGISTER_CORE(NoteHighwayCore)