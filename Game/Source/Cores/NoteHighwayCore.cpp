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

NoteHighwayCore::NoteHighwayCore()
    : Base( ComponentFilter().Requires<Transform>().Requires<NoteTrigger>() )
{
    m_midi.OpenAllDevices();
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
    LaunchPlayTrackEvent::GetEventId()
    };
    EventManager::GetInstance().RegisterReceiver( this, events );
}

void NoteHighwayCore::OnRemovedFromWorld()
{
    EventManager::GetInstance().DeRegisterReciever( this );
}

void NoteHighwayCore::OnStop()
{
    if( m_currentTrack )
    {
        m_currentTrack->Stop();
    }
}

void NoteHighwayCore::OnEntityAdded( Entity& NewEntity )
{
}

void NoteHighwayCore::OnEntityRemoved( Entity& InEntity )
{
}

void NoteHighwayCore::Update( const UpdateContext& context )
{
    if( !m_currentTrack )
    {
        return;
    }
    Input& gameInput = GetEngine().GetInput();
    PadMappingStorage& storage = PadMappingStorage::GetInstance();

    auto& entities = GetEntities();

    MidiMessage msg = m_midi.GetNextMessage();
    if( msg.Encode() > 0 )
    {
        BRUH_FMT( "Midid %s", msg.ToString().c_str() );
    }

    std::vector<Entity>::iterator noteItr = entities.begin();
    for( auto it = noteItr; it != entities.end(); ++it )
    {
        NoteTrigger& note = it->GetComponent<NoteTrigger>();
        const unsigned int triggerTime = (unsigned int)( note.TriggerTime * 1000.f );
        const unsigned int noteTime = m_currentTrack->GetPositionMs();

        if( Mathf::Abs( (float)( noteTime - triggerTime ) ) < 200 )
        {
            // drunk me fucked this up
            for( auto& pad : storage.mappedPads )
            {
                if( gameInput.WasKeyPressed( (KeyCode)pad.keyboardBinding ) && pad.padId == note.EditorLane )
                {
                    it->MarkForDelete();
                }
            }

            if( msg.Encode() > 0 )
            {
                for( auto& pad : storage.mappedPads )
                {
                    if( pad.midiBinding == msg.m_data1 && pad.padId == note.EditorLane )
                    {
                        it->MarkForDelete();
                    }
                }
            }
        }
    }

    if( m_currentTrack )
    {
        //auto& camTransform = Camera::CurrentCamera->Parent->GetComponent<Transform>();
        Transform& camTransform = TrackMover->GetComponent<Transform>();
        camTransform.SetPosition( { 0,0,( (float)m_currentTrack->GetPositionMs() / 1000.f ) * m_trackData->m_noteSpeed } );
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
        SetupTrack( TrackDatabase::GetInstance().m_trackList.m_tracks[event.TrackIndex]);
        return true;
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
        noteComp.NoteName = it.m_noteName;
        noteComp.EditorLane = it.m_editorLane;
        noteComp.EditorLaneName = PadUtils::GetPadName( it.m_editorLane );
    }

    PlayAudioEvent evt( inTrackData.m_trackSourcePath );
    evt.Callback = [this]( SharedPtr<AudioSource> inSource )
    {
        if( m_currentTrack != inSource )
        {
            if( m_currentTrack )
            {
                m_currentTrack->Stop( true );
            }
            m_currentTrack = inSource;
        }
    };
    evt.Fire();
}


void NoteHighwayCore::ShutdownTrack()
{
    auto& entities = GetEntities();
    for( auto ent : entities )
    {
        ent.MarkForDelete();
    }
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