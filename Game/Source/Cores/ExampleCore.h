#pragma once
#include <ECS/Core.h>
#include <Components/Transform.h>
#include "Events/EventReceiver.h"
#include "CoreGame/TrackList.h"
#include "Components/Audio/AudioSource.h"
#include <unordered_map>
#include <MidiDeviceManager.h>

class ExampleCore final
	: public Core<ExampleCore>
	, public EventReceiver
{
public:
	ExampleCore();
	~ExampleCore();

	virtual void Init() final;

	virtual void OnEntityAdded(Entity& NewEntity) final;
	virtual void OnEntityRemoved(Entity& InEntity) final;

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

	void OnAddedToWorld() override;

	void OnRemovedFromWorld() override;

	void OnStop() override;

#endif

	MidiDeviceManager m_midi;
};

ME_REGISTER_CORE(ExampleCore)