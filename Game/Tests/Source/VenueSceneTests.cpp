#include <doctest/doctest.h>
#include "ComponentRegistry.h"
#include "Components/Camera.h"
#include "Components/Lighting/Light.h"
#include "Components/Transform.h"
#include "Components/Venue/VenueMarkers.h"
#include "CoreGame/TrackList.h"
#include "Venue/VenueScene.h"
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
    // The look defaults to the procedural rooms' (VenuePlan's).
    const VenuePlan rooms;
    CHECK( info.FogColor.z == doctest::Approx( rooms.FogColor.z ) );
    CHECK( info.SkyTime == doctest::Approx( rooms.SkyTime ) );
    CHECK( info.MoonBrightness == doctest::Approx( rooms.MoonBrightness ) );
    CHECK( info.Haze == doctest::Approx( 1.f ) );
    CHECK( VenueCrowdArea().HeadCount == 60 );
    CHECK( VenueCrowdArea().Figures == VenueCrowdArea::Kind::Mob );
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
    info.AmbientColor = Vector3( 0.1f, 0.05f, 0.2f );
    info.FogColor = Vector3( 0.3f, 0.2f, 0.1f );
    info.Haze = 0.5f;
    info.SkyTime = 20.25f;
    info.MoonBrightness = 3.f;

    EntityHandle spot = source->CreateEntity( "Guitarist" );
    Transform& spotTransform = spot->AddComponent<Transform>();
    spotTransform.SetParent( root->GetComponent<Transform>() );
    spot->AddComponent<VenueSpot>().Member = VenueSpot::Role::Bass;

    EntityHandle crowd = source->CreateEntity( "Crowd" );
    Transform& crowdTransform = crowd->AddComponent<Transform>();
    crowdTransform.SetParent( root->GetComponent<Transform>() );
    VenueCrowdArea& area = crowd->AddComponent<VenueCrowdArea>();
    area.Figures = VenueCrowdArea::Kind::Posed;
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
    CHECK( loadedInfo.AmbientColor.y == doctest::Approx( 0.05f ) );
    CHECK( loadedInfo.AmbientColor.z == doctest::Approx( 0.2f ) );
    CHECK( loadedInfo.FogColor.x == doctest::Approx( 0.3f ) );
    CHECK( loadedInfo.Haze == doctest::Approx( 0.5f ) );
    CHECK( loadedInfo.SkyTime == doctest::Approx( 20.25f ) );
    CHECK( loadedInfo.MoonBrightness == doctest::Approx( 3.f ) );

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
            CHECK( c.Figures == VenueCrowdArea::Kind::Posed );
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


namespace
{
    // A venue root out where the show puts it, so venue space and world space differ.
    EntityHandle MakeVenueRoot( World& inWorld )
    {
        EntityHandle root = inWorld.CreateEntity( "Venue" );
        root->AddComponent<Transform>().SetPosition( Vector3( -500.f, 0.f, 0.f ) );
        return root;
    }


    EntityHandle AddMarker( World& inWorld, Transform& inParent, const char* inName, const Vector3& inPosition, const Vector3& inEuler = Vector3( 0.f, 0.f, 0.f ), const Vector3& inScale = Vector3( 1.f, 1.f, 1.f ) )
    {
        EntityHandle entity = inWorld.CreateEntity( inName );
        Transform& transform = entity->AddComponent<Transform>();
        transform.SetParent( inParent );
        transform.SetPosition( inPosition );
        transform.SetRotation( inEuler );
        transform.SetScale( inScale );
        return entity;
    }
}


TEST_CASE( "Venue scene: markers become a plan in venue space" )
{
    auto world = MakeVenueWorld();
    EntityHandle venue = MakeVenueRoot( *world );
    Transform& venueRoot = venue->GetComponent<Transform>();
    // The scene's own root, moved a little: everything under it moves with it.
    EntityHandle scene = AddMarker( *world, venueRoot, "Scene", Vector3( 0.f, 0.f, 1.f ) );
    Transform& sceneRoot = scene->GetComponent<Transform>();

    VenueInfo& info = AddMarker( *world, sceneRoot, "Info", Vector3( 0.f, 0.f, 0.f ) )->AddComponent<VenueInfo>();
    info.Name = "Garage";
    info.Outdoor = true;
    info.RoomBack = -20.f;
    info.RoomHalfWidth = 9.f;
    info.BuildRig = true;
    info.SkyTime = 20.5f;
    AddMarker( *world, sceneRoot, "Drummer", Vector3( 0.f, 0.8f, 5.2f ) )->AddComponent<VenueSpot>().Member = VenueSpot::Role::Drummer;
    // Turned 30 degrees: the performer's own front swings toward +x with it.
    AddMarker( *world, sceneRoot, "Guitar", Vector3( -3.f, 0.5f, 2.f ), Vector3( 0.f, 30.f, 0.f ) )->AddComponent<VenueSpot>().Member = VenueSpot::Role::Guitar;
    // Turned a quarter: 10 m wide by 4 deep becomes 4 wide by 10 deep, facing +x.
    VenueCrowdArea& area = AddMarker( *world, sceneRoot, "Crowd", Vector3( 0.f, 0.3f, -9.f ), Vector3( 0.f, 90.f, 0.f ), Vector3( 10.f, 1.f, 4.f ) )->AddComponent<VenueCrowdArea>();
    area.HeadCount = 80;
    area.Jitter = 0.25f;
    // A posed knot behind it, on a 1 m rise.
    VenueCrowdArea& posedArea = AddMarker( *world, sceneRoot, "Front rows", Vector3( 1.f, 1.f, -16.f ), Vector3( 0.f, 0.f, 0.f ), Vector3( 6.f, 1.f, 2.f ) )->AddComponent<VenueCrowdArea>();
    posedArea.Figures = VenueCrowdArea::Kind::Posed;
    posedArea.HeadCount = 20;
    VenueScreen& tv = AddMarker( *world, sceneRoot, "TV", Vector3( 4.f, 2.f, 8.f ), Vector3( 0.f, 0.f, 0.f ), Vector3( 3.f, 1.5f, 1.f ) )->AddComponent<VenueScreen>();
    tv.Source = VenueScreen::Feed::Program;
    tv.Emissive = 3.f;
    AddMarker( *world, sceneRoot, "Karaoke", Vector3( 0.f, 4.f, 9.f ), Vector3( 0.f, 0.f, 0.f ), Vector3( 6.f, 1.f, 1.f ) )->AddComponent<VenueScreen>().Source = VenueScreen::Feed::Lyrics;
    VenueCameraSpot& camera = AddMarker( *world, sceneRoot, "Wide", Vector3( 0.f, 3.f, -15.f ) )->AddComponent<VenueCameraSpot>();
    camera.Shot = VenueCameraSpot::Kind::Desk;
    camera.FieldOfView = 30.f;
    EntityHandle wash = AddMarker( *world, sceneRoot, "Wash", Vector3( 2.f, 4.f, 3.f ) );
    wash->AddComponent<Light>();
    wash->AddComponent<VenueShowLight>().Group = 2;
    EntityHandle torch = AddMarker( *world, sceneRoot, "Torch", Vector3( 2.f, 2.f, 0.f ) );
    torch->AddComponent<Light>();
    torch->AddComponent<VenueShowLight>().Kind = VenueShowLight::Role::Static;

    VenueScene::Markers markers;
    std::string problem;
    REQUIRE( VenueScene::Collect( { scene }, venueRoot, markers, problem ) );
    const VenuePlan& plan = markers.Plan;
    CHECK( plan.Name == "Garage" );
    CHECK( plan.Bounds.Outdoor );
    CHECK( plan.Bounds.Back == doctest::Approx( -20.f ) );
    CHECK( plan.Bounds.HalfWidth == doctest::Approx( 9.f ) );
    CHECK( plan.BuildRig );
    CHECK_FALSE( plan.BuildStage );
    CHECK_FALSE( plan.BuildRoom );
    CHECK( plan.SkyTime == doctest::Approx( 20.5f ) );
    // Out of doors it dresses as the festival.
    CHECK( plan.Style == 2 );

    // Spots in venue space (the scene root's offset in, the venue root's out); identity faces the crowd.
    REQUIRE( plan.HasMember( VenueData::Drums ) );
    CHECK( plan.Members[VenueData::Drums].Feet.x == doctest::Approx( 0.f ) );
    CHECK( plan.Members[VenueData::Drums].Feet.y == doctest::Approx( 0.8f ) );
    CHECK( plan.Members[VenueData::Drums].Feet.z == doctest::Approx( 6.2f ) );
    CHECK( plan.Members[VenueData::Drums].Yaw == 180.f );
    REQUIRE( plan.HasMember( VenueData::Guitar ) );
    CHECK( plan.Members[VenueData::Guitar].Yaw == doctest::Approx( 210.f ) );
    CHECK_FALSE( plan.HasMember( VenueData::Bass ) );
    CHECK_FALSE( plan.HasMember( VenueData::Vocals ) );
    CHECK_FALSE( plan.HasMember( VenueData::Keys ) );
    CHECK( plan.Stage.Height == doctest::Approx( 0.5f ) );
    CHECK( plan.Stage.RiserHeight == doctest::Approx( 0.3f ) );

    // The crowd: a mob on the turned rectangle's bounds, facing +x, standing at its height.
    REQUIRE( plan.Crowd.size() == 2 );
    const VenuePlan::CrowdArea& mob = plan.Crowd[0];
    CHECK( mob.Type == VenuePlan::CrowdArea::Kind::Mob );
    CHECK( mob.MinX == doctest::Approx( -2.f ).epsilon( 0.001 ) );
    CHECK( mob.MaxX == doctest::Approx( 2.f ).epsilon( 0.001 ) );
    CHECK( mob.MinZ == doctest::Approx( -13.f ).epsilon( 0.001 ) );
    CHECK( mob.MaxZ == doctest::Approx( -3.f ).epsilon( 0.001 ) );
    CHECK( mob.FloorY == doctest::Approx( 0.3f ) );
    CHECK( mob.Heads == 80 );
    CHECK( mob.Yaw == doctest::Approx( 90.f ) );
    CHECK( mob.Scatter == doctest::Approx( 0.5f ) );
    CHECK( mob.Spacing > 0.2f );
    CHECK( plan.BuildCrowd );
    // Posed: rows over the whole rectangle (not the rooms' widening wedge), at its height.
    const VenuePlan::CrowdArea& posed = plan.Crowd[1];
    CHECK( posed.Type == VenuePlan::CrowdArea::Kind::Posed );
    CHECK( posed.Heads == 20 );
    CHECK( posed.FrontHalfWidth == doctest::Approx( 3.f ).epsilon( 0.001 ) );
    CHECK( posed.Widen == 0.f );
    CHECK( posed.FloorY == doctest::Approx( 1.f ) );
    // The barricade runs in front of the crowd, behind the band.
    CHECK( plan.Stage.BarricadeZ > mob.MaxZ );
    CHECK( plan.Stage.BarricadeZ < plan.Members[VenueData::Guitar].Feet.z );

    // Screens: the feed (named, not cast) and the lyric band.
    REQUIRE( plan.Screens.size() == 1 );
    CHECK( plan.Screens[0].Source == VenuePlan::Screen::Feed::Program );
    CHECK( plan.Screens[0].Width == doctest::Approx( 3.f ) );
    CHECK( plan.Screens[0].Height == doctest::Approx( 1.5f ) );
    CHECK( plan.Screens[0].Yaw == 0.f );
    CHECK( plan.Screens[0].Emissive == doctest::Approx( 3.f ) );
    CHECK( plan.Screens[0].Centre.z == doctest::Approx( 9.f ) );
    CHECK( plan.Lyrics.Present );
    CHECK( plan.Lyrics.Width == doctest::Approx( 6.f ) );

    REQUIRE( plan.Cameras.size() == 1 );
    CHECK( plan.Cameras[0].Shot == VenuePlan::CameraSpot::Kind::Desk );
    CHECK( plan.Cameras[0].FieldOfView == doctest::Approx( 30.f ) );
    CHECK( plan.Cameras[0].Eye.z == doctest::Approx( -14.f ) );
    CHECK( plan.Cameras[0].Forward.z == doctest::Approx( 1.f ) );

    // The show cues the wash; the static torch is left alone.
    REQUIRE( markers.Lights.size() == 1 );
    CHECK( markers.Lights[0].Light == wash );
    CHECK( markers.Lights[0].Role == VenueShowLight::Role::Wash );
    CHECK( markers.Lights[0].Group == 2 );
    CHECK( markers.StaticLights == 1 );
    CHECK_FALSE( markers.HasDirectional );
}


TEST_CASE( "Venue scene: no drummer or no VenueInfo is no venue" )
{
    auto world = MakeVenueWorld();
    EntityHandle venue = MakeVenueRoot( *world );
    Transform& venueRoot = venue->GetComponent<Transform>();
    EntityHandle scene = AddMarker( *world, venueRoot, "Scene", Vector3( 0.f, 0.f, 0.f ) );
    Transform& sceneRoot = scene->GetComponent<Transform>();
    AddMarker( *world, sceneRoot, "Singer", Vector3( 0.f, 0.f, 1.f ) )->AddComponent<VenueSpot>().Member = VenueSpot::Role::Vocals;

    VenueScene::Markers markers;
    std::string problem;
    CHECK_FALSE( VenueScene::Collect( { scene }, venueRoot, markers, problem ) );
    CHECK( problem.find( "VenueInfo" ) != std::string::npos );

    AddMarker( *world, sceneRoot, "Info", Vector3( 0.f, 0.f, 0.f ) )->AddComponent<VenueInfo>();
    problem.clear();
    CHECK_FALSE( VenueScene::Collect( { scene }, venueRoot, markers, problem ) );
    CHECK( problem.find( "Drummer" ) != std::string::npos );

    AddMarker( *world, sceneRoot, "Drummer", Vector3( 0.f, 0.5f, 5.f ) )->AddComponent<VenueSpot>();
    problem.clear();
    CHECK( VenueScene::Collect( { scene }, venueRoot, markers, problem ) );
    // Indoors, the club; no lyric screen, no lyric band.
    CHECK( markers.Plan.Style == 1 );
    CHECK_FALSE( markers.Plan.Lyrics.Present );
    CHECK( markers.Plan.Screens.empty() );
    CHECK( markers.Plan.Crowd.empty() );
    CHECK_FALSE( markers.Plan.BuildCrowd );
}


TEST_CASE( "Venue scene: a scene loses its code, cameras and cores before it's instanced" )
{
    json scene = json::parse( R"({
        "Version": 2,
        "Cores": [ { "Type": "PhysicsCore" }, { "Type": "ScriptCore" } ],
        "Entities": [
            { "GUID": "1000000000000001", "Name": "Root", "Components": [ { "Type": "Transform" } ] },
            { "GUID": "1000000000000002", "Name": "Info", "Parent": "1000000000000001", "Components": [
                { "Type": "Transform" }, { "Type": "VenueInfo", "Name": "Basement" }, { "Type": "ScriptComponent" } ] },
            { "GUID": "1000000000000003", "Name": "Drummer", "Parent": "1000000000000001", "Components": [
                { "Type": "Transform", "Position": [ 1, 0.5, 4 ] }, { "Type": "VenueSpot", "Member": "Drummer" } ] },
            { "GUID": "1000000000000004", "Name": "Main Camera", "Parent": "1000000000000001", "Components": [
                { "Type": "Transform" }, { "Type": "Camera" }, { "Type": "PostProcess" }, { "Type": "AudioListener" } ] },
            { "GUID": "1000000000000005", "Name": "Menu", "Components": [ { "Type": "UIDocument" } ] }
        ]
    })" );
    const VenueScene::Stripped stripped = VenueScene::Strip( scene );
    CHECK( stripped.Cores == 2 );
    CHECK( stripped.Scripts == 1 );
    CHECK( stripped.Cameras == 1 );
    CHECK( stripped.Listeners == 1 );
    CHECK( stripped.Documents == 1 );
    CHECK_FALSE( scene.contains( "Cores" ) );
    for( const json& entity : scene["Entities"] )
    {
        for( const json& component : entity["Components"] )
        {
            const std::string type = component["Type"].get<std::string>();
            CHECK( type != "ScriptComponent" );
            CHECK( type != "Camera" );
            CHECK( type != "PostProcess" );
            CHECK( type != "AudioListener" );
            CHECK( type != "UIDocument" );
        }
    }

    // Instanced as the show does it: fresh GUIDs, no cores, under the venue root.
    auto world = MakeVenueWorld();
    EntityHandle venue = MakeVenueRoot( *world );
    Transform& venueRoot = venue->GetComponent<Transform>();
    SceneSerializer::LoadOptions options;
    options.RemapGUIDs = true;
    options.LoadCores = false;
    options.Parent = &venueRoot;
    std::vector<EntityHandle> roots = SceneSerializer::Deserialize( *world, scene, options );
    REQUIRE( roots.size() == 2 );
    CHECK( roots[0]->GetComponent<Transform>().GetParentTransform() == &venueRoot );
    VenueScene::Markers markers;
    std::string problem;
    REQUIRE( VenueScene::Collect( roots, venueRoot, markers, problem ) );
    CHECK( markers.Plan.Name == "Basement" );
    CHECK( markers.Plan.Members[VenueData::Drums].Feet.x == doctest::Approx( 1.f ) );
    CHECK( markers.Plan.Members[VenueData::Drums].Feet.z == doctest::Approx( 4.f ) );
    int cameras = 0;
    world->ForEachEntity( [&cameras]( Entity& inEntity ) { if( inEntity.HasComponent<Camera>() ) ++cameras; } );
    CHECK( cameras == 0 );
}
