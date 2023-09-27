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
    World& world = GetWorld();

    // open_hh
    {
        EntityHandle lane1 = world.CreateEntity();
        auto& snareLane = lane1->AddComponent<Transform>( "open_hh" );
        snareLane.SetPosition( { -3, 1, 0 } );
        snareLane.SetScale( { 1, .3f, .1f } );
        m_lanes["open_hh"] = lane1;
    }

    // open_hh
    {
        EntityHandle lane1 = world.CreateEntity();
        auto& snareLane = lane1->AddComponent<Transform>( "closed_hh" );
        snareLane.SetPosition( { -3, 1, 0 } );
        snareLane.SetScale( { 1, .3f, .1f } );
        m_lanes["closed_hh"] = lane1;
    }

    // Snare1
    {
        EntityHandle lane1 = world.CreateEntity();
        auto& snareLane = lane1->AddComponent<Transform>( "Snare1" );
        snareLane.SetPosition( { -2, 0, 0 } );
        snareLane.SetScale( { 1, .3f, .1f } );
        m_lanes["snare1"] = lane1;
    }
    // Crash1
    {
        EntityHandle lane1 = world.CreateEntity();
        auto& snareLane = lane1->AddComponent<Transform>( "Crash1" );
        snareLane.SetPosition( { 2, 0, 0 } );
        snareLane.SetScale( { 1, .3f, .1f } );
        m_lanes["crash1"] = lane1;
    }

    // Kick
    {
        EntityHandle lane1 = world.CreateEntity();
        auto& snareLane = lane1->AddComponent<Transform>( "Bass1" );
        snareLane.SetPosition( { 0, -2, 0 } );
        snareLane.SetScale( { 1, .3f, .1f } );
        m_lanes["bass1"] = lane1;
    }
}

void ExampleCore::OnEntityAdded( Entity& NewEntity )
{
}

void ExampleCore::OnEntityRemoved( Entity& InEntity )
{
}

void ExampleCore::Update( const UpdateContext& context )
{
    auto& entities = GetEntities();
    for( auto ent : entities )
    {
    }
    if( m_currentTrack )
    {
        auto& camTransform = Camera::CurrentCamera->Parent->GetComponent<Transform>();
        camTransform.SetPosition( { 0,0,(float)m_currentTrack->GetPositionMs() / 1000 } );
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
        transform.SetName( it.m_noteName + std::to_string( it.m_editorLane ) );
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


#if USING( ME_EDITOR )

void ExampleCore::OnEditorInspect()
{
}

#endif