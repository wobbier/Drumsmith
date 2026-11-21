#include <doctest/doctest.h>
#include "Components/Transform.h"
#include "Components/Venue/VenueMarkers.h"
#include "Cores/VenuePreviewCore.h"
#include "CoreGame/TrackList.h"
#include "Venue/VenueScene.h"
#include "Venue/VenueShow.h"
#include "Engine/World.h"

namespace
{
    std::shared_ptr<World> MakePreviewWorld()
    {
        auto world = std::make_shared<World>();
        world->IsLoading = false;
        return world;
    }


    EntityHandle AddEntity( World& inWorld, Transform* inParent, const char* inName, const Vector3& inPosition )
    {
        EntityHandle entity = inWorld.CreateEntity( inName );
        Transform& transform = entity->AddComponent<Transform>();
        if( inParent )
        {
            transform.SetParent( *inParent );
        }
        transform.SetPosition( inPosition );
        return entity;
    }
}


TEST_CASE( "Venue preview: an adopted scene is read in place and left standing" )
{
    auto world = MakePreviewWorld();
    // The open scene, at the world's origin as it was authored.
    EntityHandle scene = AddEntity( *world, nullptr, "Backyard", Vector3( 0.f, 0.f, 0.f ) );
    Transform& sceneRoot = scene->GetComponent<Transform>();
    AddEntity( *world, &sceneRoot, "Info", Vector3( 0.f, 0.f, 0.f ) )->AddComponent<VenueInfo>().Name = "Backyard";
    AddEntity( *world, &sceneRoot, "Drummer", Vector3( 0.f, 0.55f, 6.2f ) )->AddComponent<VenueSpot>().Member = VenueSpot::Role::Drummer;
    EntityHandle venue = AddEntity( *world, nullptr, "Venue", Vector3( 0.f, 0.f, 0.f ) );

    VenueScene adopted;
    std::string problem;
    REQUIRE( adopted.Adopt( { scene }, venue->GetComponent<Transform>(), problem ) );
    CHECK( adopted.IsLoaded() );
    CHECK( adopted.GetMarkers().Plan.Name == "Backyard" );
    // Venue space is world space: the spot is where the author put it.
    CHECK( adopted.GetMarkers().Plan.Members[VenueData::Drums].Feet.z == doctest::Approx( 6.2f ) );

    adopted.Clear();
    world->Simulate();
    CHECK_FALSE( adopted.IsLoaded() );
    CHECK( static_cast<bool>( scene ) );

    // Not a venue: nothing is kept.
    EntityHandle other = AddEntity( *world, nullptr, "Room", Vector3( 0.f, 0.f, 0.f ) );
    CHECK_FALSE( adopted.Adopt( { other }, venue->GetComponent<Transform>(), problem ) );
    CHECK_FALSE( adopted.IsLoaded() );
    CHECK( problem.find( "VenueInfo" ) != std::string::npos );
}


TEST_CASE( "Venue preview: the rock beat is a steady chart with its grid" )
{
    const TrackData chart = VenuePreviewCore::RockBeat( 120, 4 );
    // 16 beats: a hat or crash on each beat and each off-beat, a kick or snare on each beat.
    CHECK( chart.m_beats.size() == 16 );
    CHECK( chart.m_noteData.size() == 48 );
    CHECK( chart.m_duration == doctest::Approx( 8.f ) );
    CHECK( chart.m_beats[4].m_measure );
    CHECK_FALSE( chart.m_beats[5].m_measure );
    int kicks = 0, snares = 0, crashes = 0;
    float last = -1.f;
    bool sorted = true;
    for( const NoteData& note : chart.m_noteData )
    {
        kicks += note.m_editorLane == PadId::Bass;
        snares += note.m_editorLane == PadId::Snare;
        crashes += note.m_editorLane == PadId::Crash1;
        sorted = sorted && note.m_triggerTime >= last;
        last = note.m_triggerTime;
    }
    CHECK( kicks == 8 );
    CHECK( snares == 8 );
    CHECK( crashes == 1 );
    CHECK( sorted );
}


TEST_CASE( "Venue preview: the editor's venue override is set, read and cleared" )
{
    VenueShow::SetOverride( "Backyard" );
    CHECK( VenueShow::GetOverride() == "Backyard" );
    CHECK( VenueShow::GetOverrideOutcome().empty() );
    CHECK_FALSE( VenueShow::OverrideFellBack() );
    VenueShow::SetOverride( std::string() );
    CHECK( VenueShow::GetOverride().empty() );
}

#if USING( ME_EDITOR )
TEST_CASE( "Venue preview: the core joins a world with a VenueInfo and nothing else" )
{
    auto plain = MakePreviewWorld();
    AddEntity( *plain, nullptr, "Room", Vector3( 0.f, 0.f, 0.f ) );
    CHECK_FALSE( VenuePreviewCore::AttachIfVenue( *plain ) );
    CHECK_FALSE( plain->HasCore<VenuePreviewCore>() );

    auto venue = MakePreviewWorld();
    AddEntity( *venue, nullptr, "Info", Vector3( 0.f, 0.f, 0.f ) )->AddComponent<VenueInfo>();
    CHECK( VenuePreviewCore::AttachIfVenue( *venue ) );
    REQUIRE( venue->HasCore<VenuePreviewCore>() );
    // Never written into the scene.
    CHECK_FALSE( venue->GetCore<VenuePreviewCore>()->GetIsSerializable() );
    CHECK_FALSE( venue->GetCore<VenuePreviewCore>()->IsShowing() );
}
#endif
