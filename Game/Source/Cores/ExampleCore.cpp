#include <Cores/ExampleCore.h>
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

ExampleCore::ExampleCore()
    : Base( ComponentFilter().Requires<Transform>().Requires<NoteTrigger>() )
{
    std::vector<TypeId> events = {
    LaunchPlayTrackEvent::GetEventId()
    };
    EventManager::GetInstance().RegisterReceiver( this, events );
}

void ExampleCore::Init()
{

}

void ExampleCore::OnEntityAdded( Entity& NewEntity )
{
}

void ExampleCore::OnEntityRemoved( Entity& InEntity )
{
}

void ExampleCore::Update( const UpdateContext& context )
{
    if( !m_currentTrack )
    {
        return;
    }
    Input& gameInput = GetEngine().GetInput();
    PadMappingStorage& storage = PadMappingStorage::GetInstance();

    auto& entities = GetEntities();

    std::vector<Entity>::iterator noteItr = entities.begin();
    for( auto it = noteItr; it != entities.end(); ++it )
    {
        NoteTrigger& note = it->GetComponent<NoteTrigger>();
        const unsigned int triggerTime = (unsigned int)(note.TriggerTime * 1000.f);
        const unsigned int noteTime = m_currentTrack->GetPositionMs();

        if( Mathf::Abs( (float)( noteTime - triggerTime ) ) < 200 )
        {
            // drunk me fucked this up
            for( auto& pad : storage.mappedPads )
            {
                std::string con = ConvertPadToLane( pad.padId );
                if( gameInput.WasKeyPressed( (KeyCode)pad.keyboardBinding ) && con == note.EditorLane )
                {
                    it->MarkForDelete();
                }
            }
        }
    }

    if( m_currentTrack )
    {
        auto& camTransform = Camera::CurrentCamera->Parent->GetComponent<Transform>();
        camTransform.SetPosition( { 0,0,(float)m_currentTrack->GetPositionMs() / 1000 } );
    }


}

void ExampleCore::OnStart()
{
    World& world = GetWorld();
    m_lanes.clear();

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
}



bool ExampleCore::OnEvent( const BaseEvent& evt )
{
    if( evt.GetEventId() == LaunchPlayTrackEvent::GetEventId() )
    {
        const LaunchPlayTrackEvent& event = static_cast<const LaunchPlayTrackEvent&>( evt );

        for( auto it : TrackDatabase::GetInstance().m_trackList.m_tracks )
        {
            if( it.m_trackName == event.TrackID )
            {
                SetupTrack( it );
                break;
            }
        }
        return true;
    }

    return false;
}


void ExampleCore::SetupTrack( TrackData& inTrackData )
{
    ShutdownTrack();

    inTrackData.LoadNoteData();

    World& world = GetWorld();

    for( auto& it : inTrackData.m_noteData )
    {
        EntityHandle note = world.CreateEntity();
        auto& transform = note->AddComponent<Transform>();
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
        auto& modelComp = note->AddComponent<Model>( "Assets/cube.obj" );
        auto& noteComp = note->AddComponent<NoteTrigger>();
        noteComp.TriggerTime = it.m_triggerTime;
        noteComp.NoteName = it.m_noteName;
        noteComp.EditorLane = it.m_editorLane;
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


void ExampleCore::ShutdownTrack()
{
    auto& entities = GetEntities();
    for( auto ent : entities )
    {
        ent.MarkForDelete();
    }
}


int32_t ExampleCore::LegacyConvertLane( const std::string& lane )
{
    if( lane == "bass1" )
    {
        return PadId::Bass;
    }
    return -1;
}

const char* ExampleCore::ConvertPadToLane( int16_t lane )
{
    if( lane == PadId::Bass )
    {
        return "bass1";
    }
    return "";
}

#if USING( ME_EDITOR )

void ExampleCore::OnEditorInspect()
{
}

#endif