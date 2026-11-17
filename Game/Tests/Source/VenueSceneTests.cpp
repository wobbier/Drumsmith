#include <doctest/doctest.h>
#include "ComponentRegistry.h"
#include "Components/Transform.h"
#include "Components/Venue/VenueMarkers.h"
#include "ECS/ComponentDetail.h"
#include "Engine/World.h"
#include "World/SceneSerializer.h"

namespace
{
    std::shared_ptr<World> MakeVenueWorld()
    {
        auto world = std::make_shared<World>();
        world->IsLoading = false;
        return world;
    }
}


TEST_CASE( "Venue markers: every component is in the registry under its name" )
{
    for( const char* name : { "VenueInfo", "VenueSpot", "VenueCrowdArea", "VenueCameraSpot", "VenueScreen", "VenueShowLight" } )
    {
        auto it = FindComponentInfo( name );
        REQUIRE( it != GetComponentRegistry().end() );
        CHECK( it->second.CreateFunc != nullptr );
#if USING( ME_EDITOR )
        CHECK( it->second.Folder == "Venue" );
#endif
    }
}


TEST_CASE( "Venue markers: defaults match the room the director assumes" )
{
    VenueInfo info;
    CHECK( info.RoomBack == doctest::Approx( -1000.f ) );
    CHECK( info.RoomCeiling == doctest::Approx( 1000.f ) );
    CHECK( info.RoomHalfWidth == doctest::Approx( 30.f ) );
    CHECK( info.DeskZ == doctest::Approx( -22.f ) );
    CHECK_FALSE( info.BuildStage );
    CHECK_FALSE( info.BuildSet );
    CHECK_FALSE( info.BuildRig );
    CHECK_FALSE( info.BuildFx );
    CHECK( VenueCrowdArea().HeadCount == 60 );
    CHECK( VenueCameraSpot().FieldOfView == doctest::Approx( 55.f ) );
    CHECK( VenueShowLight().Group == 0 );
}


TEST_CASE( "Venue markers: fields survive a scene round trip" )
{
    auto source = MakeVenueWorld();
    EntityHandle root = source->CreateEntity( "Venue" );
    root->AddComponent<Transform>();
    VenueInfo& info = root->AddComponent<VenueInfo>();
    info.Name = "Warehouse";
    info.Author = "Mitch";
    info.Outdoor = true;
    info.RoomBack = -40.f;
    info.RoomCeiling = 12.5f;
    info.RoomHalfWidth = 18.f;
    info.DeskZ = -15.f;
    info.BuildStage = true;
    info.BuildSet = true;
    info.BuildRig = true;
    info.BuildFx = true;

    EntityHandle spot = source->CreateEntity( "Guitarist" );
    Transform& spotTransform = spot->AddComponent<Transform>();
    spotTransform.SetParent( root->GetComponent<Transform>() );
    spot->AddComponent<VenueSpot>().Member = VenueSpot::Role::Bass;

    EntityHandle crowd = source->CreateEntity( "Crowd" );
    Transform& crowdTransform = crowd->AddComponent<Transform>();
    crowdTransform.SetParent( root->GetComponent<Transform>() );
    VenueCrowdArea& area = crowd->AddComponent<VenueCrowdArea>();
    area.HeadCount = 123;
    area.Jitter = 0.25f;

    EntityHandle camera = source->CreateEntity( "Crane" );
    Transform& cameraTransform = camera->AddComponent<Transform>();
    cameraTransform.SetParent( root->GetComponent<Transform>() );
    VenueCameraSpot& shot = camera->AddComponent<VenueCameraSpot>();
    shot.Shot = VenueCameraSpot::Kind::Crane;
    shot.FieldOfView = 72.f;
    shot.Tag = "balcony";

    EntityHandle screen = source->CreateEntity( "Screen" );
    Transform& screenTransform = screen->AddComponent<Transform>();
    screenTransform.SetParent( root->GetComponent<Transform>() );
    VenueScreen& feed = screen->AddComponent<VenueScreen>();
    feed.Source = VenueScreen::Feed::Lyrics;
    feed.Emissive = 4.5f;

    EntityHandle light = source->CreateEntity( "Strobe" );
    Transform& lightTransform = light->AddComponent<Transform>();
    lightTransform.SetParent( root->GetComponent<Transform>() );
    VenueShowLight& show = light->AddComponent<VenueShowLight>();
    show.Kind = VenueShowLight::Role::Strobe;
    show.Group = 3;

    const json saved = SceneSerializer::SerializeEntities( *source, { root.Get() } );
    REQUIRE( saved["Entities"].size() == 6 );

    auto loaded = MakeVenueWorld();
    SceneSerializer::LoadOptions options;
    std::vector<EntityHandle> roots = SceneSerializer::Deserialize( *loaded, saved, options );
    REQUIRE( roots.size() == 1 );

    VenueInfo& loadedInfo = roots[0]->GetComponent<VenueInfo>();
    CHECK( loadedInfo.Name == "Warehouse" );
    CHECK( loadedInfo.Author == "Mitch" );
    CHECK( loadedInfo.Outdoor );
    CHECK( loadedInfo.RoomBack == doctest::Approx( -40.f ) );
    CHECK( loadedInfo.RoomCeiling == doctest::Approx( 12.5f ) );
    CHECK( loadedInfo.RoomHalfWidth == doctest::Approx( 18.f ) );
    CHECK( loadedInfo.DeskZ == doctest::Approx( -15.f ) );
    CHECK( loadedInfo.BuildStage );
    CHECK( loadedInfo.BuildSet );
    CHECK( loadedInfo.BuildRig );
    CHECK( loadedInfo.BuildFx );

    const auto& children = roots[0]->GetComponent<Transform>().GetChildren();
    REQUIRE( children.size() == 5 );
    int found = 0;
    for( Transform* child : children )
    {
        Entity* entity = child->Parent.Get();
        if( VenueSpot* s = entity->HasComponent<VenueSpot>() ? &entity->GetComponent<VenueSpot>() : nullptr )
        {
            CHECK( s->Member == VenueSpot::Role::Bass );
            ++found;
        }
        if( entity->HasComponent<VenueCrowdArea>() )
        {
            VenueCrowdArea& c = entity->GetComponent<VenueCrowdArea>();
            CHECK( c.HeadCount == 123 );
            CHECK( c.Jitter == doctest::Approx( 0.25f ) );
            ++found;
        }
        if( entity->HasComponent<VenueCameraSpot>() )
        {
            VenueCameraSpot& c = entity->GetComponent<VenueCameraSpot>();
            CHECK( c.Shot == VenueCameraSpot::Kind::Crane );
            CHECK( c.FieldOfView == doctest::Approx( 72.f ) );
            CHECK( c.Tag == "balcony" );
            ++found;
        }
        if( entity->HasComponent<VenueScreen>() )
        {
            VenueScreen& c = entity->GetComponent<VenueScreen>();
            CHECK( c.Source == VenueScreen::Feed::Lyrics );
            CHECK( c.Emissive == doctest::Approx( 4.5f ) );
            ++found;
        }
        if( entity->HasComponent<VenueShowLight>() )
        {
            VenueShowLight& c = entity->GetComponent<VenueShowLight>();
            CHECK( c.Kind == VenueShowLight::Role::Strobe );
            CHECK( c.Group == 3 );
            ++found;
        }
    }
    CHECK( found == 5 );
}
