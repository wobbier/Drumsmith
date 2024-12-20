#include <Cores/NoteHighwayCore.h>
#include <Components/Transform.h>
#include "Events/GameEvents.h"
#include "CoreGame/TrackList.h"
#include "Engine/World.h"
#include "Components/Graphics/Model.h"
#include "Components/NoteTrigger.h"
#include "Core/Assert.h"
#include "Components/Camera.h"
#include "Events/AudioEvents.h"
#include "Engine/Engine.h"
#include "Editor/PadBindings.h"
#include "Mathf.h"
#include "Cores/SceneCore.h"
#include "Components/Graphics/Mesh.h"
#include "Config/GameSettings.h"
#include "ECS/Core.h"
#include "Components/MainMenuController.h"

NoteHighwayCore::NoteHighwayCore()
    : Base( ComponentFilter().Requires<Transform>().Requires<NoteTrigger>() )
{
}

NoteHighwayCore::~NoteHighwayCore()
{
}

void NoteHighwayCore::Init()
{
}

void NoteHighwayCore::OnAddedToWorld()
{
    std::vector<TypeId> events = {
    LaunchPlayTrackEvent::GetEventId(),
    InGamePauseCurrentTrack::GetEventId(),
    InGameResumeCurrentTrack::GetEventId()
    };
    EventManager::GetInstance().RegisterReceiver( this, events );
    MidiDevice::GetInstance().OpenMidiDevice( GameSettings::GetInstance().PreferredMidiDevice );
}

void NoteHighwayCore::OnRemovedFromWorld()
{
    EventManager::GetInstance().DeRegisterReciever( this );
    //MidiDevice::GetInstance().CloseMidiDevice();
}

void NoteHighwayCore::OnStop()
{
    m_currentTrackPack.Stop();
}

void NoteHighwayCore::OnEntityAdded( Entity& NewEntity )
{
}

void NoteHighwayCore::OnEntityRemoved( Entity& InEntity )
{
}

void NoteHighwayCore::Update( const UpdateContext& context )
{
    if( !m_currentTrackPack.IsReady() )
    {
        return;
    }
    if( !m_hasStartedTrackYet )
    {
        m_currentTrackPack.Play();
        m_hasStartedTrackYet = true;
    }

    Input& gameInput = GetEngine().GetInput();
    PadMappingStorage& storage = PadMappingStorage::GetInstance();

    auto& entities = GetEntities();

    std::vector<Entity>::iterator noteItr = entities.begin();

    // I need to keep track of where we are in a track to avoid itr on entities
    // this whole shit is fucked
    bool handled = false;
    const unsigned int noteTime = m_currentTrackPack.GetPositionMs();
    for( auto it = noteItr; it != entities.end(); ++it )
    {
        NoteTrigger& note = it->GetComponent<NoteTrigger>();

        const unsigned int triggerTime = note.TriggerTimeMS;
        float hitWindow = Mathf::Abs( (float)( (float)noteTime - (float)triggerTime ) );
        if( hitWindow < 50.f )
        {
            // drunk me fucked this up
            for( auto& pad : storage.mappedPads )
            {
                if( gameInput.WasKeyPressed( (KeyCode)pad.keyboardBinding ) && pad.padId == note.EditorLane )
                {
                    it->MarkForDelete();
                    handled = true;
                }
            }
            m_drumVolume = Mathf::Clamp( 0.f, 1.f, m_drumVolume - context.GetDeltaTime() );
            m_currentTrackPack.SetDrumVolume( Mathf::Clamp( 0.f, 1.f, m_drumVolume ) );
            //it->MarkForDelete();
#if USING(ME_PLATFORM_WIN64)
            if( !handled )
            {
                auto midiMessages = MidiDevice::GetInstance().PumpMessages();
                for( auto& msg : midiMessages )
                {
                    if( msg.IsOnType() )
                    {
                        for( auto& pad : storage.mappedPads )
                        {
                            if( pad.midiBinding == msg.m_data1 && pad.padId == note.EditorLane )
                            {
                                //BRUH_FMT( "Midid %s", msg.ToString().c_str() );
                                it->MarkForDelete();
                                handled = true;
                                break;
                            }
                        }
                    }
                }
            }
#endif
        }

        // This is correct, right?
        if( handled )
        {
            m_drumVolume = Mathf::Clamp( 0.f, 1.f, m_drumVolume + .5f );
            break;
        }
    }

    {
        //auto& camTransform = Camera::CurrentCamera->Parent->GetComponent<Transform>();
        Transform& camTransform = TrackMover->GetComponent<Transform>();
        camTransform.SetPosition( { 0,0,( (float)m_currentTrackPack.GetPositionMs() / 1000.f ) * m_trackData->m_noteSpeed } );
    }


}

void NoteHighwayCore::OnStart()
{
    World& world = GetWorld();
    m_lanes.clear();

    m_notePrefabs[PadId::Bass] = "Assets/Prefabs/Notes/BassNotePrefab.prefab";


    SceneCore* scene = static_cast<SceneCore*>( world.GetCore( SceneCore::GetTypeId() ) );
    // open_hh
    {
        Transform* lane = scene->GetRootTransform()->GetChildByName( "open_hh" );
        m_lanes["open_hh"] = lane->Parent;
    }

    // open_hh
    {
        Transform* lane = scene->GetRootTransform()->GetChildByName( "closed_hh" );
        m_lanes["closed_hh"] = lane->Parent;
    }

    // Snare1
    {
        Transform* lane = scene->GetRootTransform()->GetChildByName( "Snare1" );
        m_lanes["snare1"] = lane->Parent;
    }
    // Crash1
    {
        Transform* lane = scene->GetRootTransform()->GetChildByName( "Crash1" );
        m_lanes["crash1"] = lane->Parent;
    }
    // Crash2
    {
        Transform* lane = scene->GetRootTransform()->GetChildByName( "crash2" );
        m_lanes["crash2"] = lane->Parent;
    }

    // Kick
    {
        Transform* lane = scene->GetRootTransform()->GetChildByName( "Bass1" );
        m_lanes["bass1"] = lane->Parent;
    }

    // Ride
    {
        Transform* lane = scene->GetRootTransform()->GetChildByName( "ride1" );
        m_lanes["ride1"] = lane->Parent;
    }

    // Tom1
    {
        Transform* lane = scene->GetRootTransform()->GetChildByName( "tom1" );
        m_lanes["tom1"] = lane->Parent;
    }
    // Tom2
    {
        Transform* lane = scene->GetRootTransform()->GetChildByName( "tom2" );
        m_lanes["tom2"] = lane->Parent;
    }
    // Tom3
    {
        Transform* lane = scene->GetRootTransform()->GetChildByName( "tom3" );
        m_lanes["tom3"] = lane->Parent;
    }
    // Tom3
    {
        Transform* lane = scene->GetRootTransform()->GetChildByName( "TrackMover" );
        TrackMover = lane->Parent;
    }
}


bool NoteHighwayCore::OnEvent( const BaseEvent& evt )
{
    if( evt.GetEventId() == LaunchPlayTrackEvent::GetEventId() )
    {
        const LaunchPlayTrackEvent& event = static_cast<const LaunchPlayTrackEvent&>( evt );
        SetupTrack( TrackDatabase::GetInstance().m_trackList.m_tracks[event.TrackIndex] );
        return true;
    }
    if( evt.GetEventId() == InGameResumeCurrentTrack::GetEventId() )
    {
        Resume();
    }
    if( evt.GetEventId() == InGamePauseCurrentTrack::GetEventId() )
    {
        Pause();
    }

    return false;
}


void NoteHighwayCore::SetupTrack( TrackData& inTrackData )
{
    ShutdownTrack();
    m_trackData = &inTrackData;

    inTrackData.LoadNoteData();

    World& world = GetWorld();

    for( auto& it : inTrackData.m_noteData )
    {
        std::string prefabName = "Assets/Prefabs/Notes/NewBaseNote.prefab";
        if( !m_notePrefabs[it.m_editorLane].empty() )
        {
            prefabName = m_notePrefabs[it.m_editorLane];
        }
        EntityHandle note = world.CreateFromPrefab( prefabName );

        auto& transform = note->GetComponent<Transform>();
        auto& meshComp = note->GetComponent<Mesh>();
        meshComp.MeshMaterial->DiffuseColor = PadUtils::GetNoteColor( it.m_editorLane );
        transform.SetPosition( Vector3( 0, 0, it.m_triggerTime * inTrackData.m_noteSpeed ) );
        transform.SetName( it.m_noteName + std::to_string( (uint8_t)it.m_editorLane ) );
        if( m_lanes[it.m_noteName] )
        {
            transform.SetParent( m_lanes[it.m_noteName]->GetComponent<Transform>() );
        }
        else
        {
            ME_ASSERT_MSG( false, "Unhandled note lane." );
        }
        auto& noteComp = note->AddComponent<NoteTrigger>();
        noteComp.TriggerTime = it.m_triggerTime;
        noteComp.TriggerTimeMS = it.m_triggerTimeMS;
        noteComp.NoteName = it.m_noteName;
        noteComp.EditorLane = it.m_editorLane;
        noteComp.EditorLaneName = PadUtils::GetPadName( it.m_editorLane );
    }

    m_currentTrackPack = AudioPack( inTrackData );
}


void NoteHighwayCore::ShutdownTrack()
{
    auto& entities = GetEntities();
    for( auto ent : entities )
    {
        ent.MarkForDelete();
    }

    m_currentTrackPack.Stop();
}

void NoteHighwayCore::Pause()
{
    m_currentTrackPack.Pause();
}

void NoteHighwayCore::Resume()
{
    m_currentTrackPack.Resume();
}

int32_t NoteHighwayCore::LegacyConvertLane( const std::string& lane )
{
    if( lane == "bass1" )
    {
        return PadId::Bass;
    }
    return -1;
}

const char* NoteHighwayCore::ConvertPadToLane( int16_t lane )
{
    if( lane == PadId::Bass )
    {
        return "bass1";
    }
    return "";
}

#if USING( ME_EDITOR )

void NoteHighwayCore::OnEditorInspect()
{
}

#endif