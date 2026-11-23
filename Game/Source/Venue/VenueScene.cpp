#include "Venue/VenueScene.h"
#include "CoreGame/TrackList.h"
#include "Components/Lighting/Light.h"
#include "Components/Transform.h"
#include "Engine/World.h"
#include "World/SceneSerializer.h"
#include "World/SceneStreaming.h"
#include "CLog.h"
#include <algorithm>
#include <cmath>
#include <functional>

namespace
{
    constexpr float kPi = 3.14159265f;
    // The member each VenueSpot role stands for (VenueData::Member order, named not cast).
    int MemberOf( VenueSpot::Role inRole )
    {
        switch( inRole )
        {
        case VenueSpot::Role::Drummer: return VenueData::Drums;
        case VenueSpot::Role::Guitar: return VenueData::Guitar;
        case VenueSpot::Role::Bass: return VenueData::Bass;
        case VenueSpot::Role::Vocals: return VenueData::Vocals;
        case VenueSpot::Role::Keys: return VenueData::Keys;
        }
        return -1;
    }


    VenuePlan::CameraSpot::Kind KindOf( VenueCameraSpot::Kind inKind )
    {
        switch( inKind )
        {
        case VenueCameraSpot::Kind::Wide: return VenuePlan::CameraSpot::Kind::Wide;
        case VenueCameraSpot::Kind::Desk: return VenuePlan::CameraSpot::Kind::Desk;
        case VenueCameraSpot::Kind::Crane: return VenuePlan::CameraSpot::Kind::Crane;
        case VenueCameraSpot::Kind::Close: return VenuePlan::CameraSpot::Kind::Close;
        case VenueCameraSpot::Kind::Custom: return VenuePlan::CameraSpot::Kind::Custom;
        }
        return VenuePlan::CameraSpot::Kind::Custom;
    }


    // Degrees about +y that turn +z to point along inDirection's flat part (0 is +z, positive
    // toward +x, as Transform's yaw), rounded to a hundredth so a square-on marker reads exactly.
    float YawOf( const Vector3& inDirection )
    {
        if( std::fabs( inDirection.x ) < 1e-6f && std::fabs( inDirection.z ) < 1e-6f )
        {
            return 0.f;
        }
        float yaw = std::atan2( inDirection.x, inDirection.z ) * 180.f / kPi;
        yaw = std::round( yaw * 100.f ) / 100.f;
        return yaw <= -180.f ? yaw + 360.f : yaw;
    }


    // A marker's point and axis in venue space (relative to the venue root).
    Vector3 PointIn( Transform& inVenueRoot, Transform& inMarker, const Vector3& inLocal )
    {
        return inVenueRoot.InverseTransformPoint( inMarker.TransformPoint( inLocal ) );
    }


    Vector3 AxisIn( Transform& inVenueRoot, Transform& inMarker, const Vector3& inLocal )
    {
        return inVenueRoot.InverseTransformDirection( inMarker.TransformDirection( inLocal ) );
    }


    const char* RoleName( VenueShowLight::Role inRole )
    {
        switch( inRole )
        {
        case VenueShowLight::Role::Wash: return "wash";
        case VenueShowLight::Role::Beam: return "beam";
        case VenueShowLight::Role::Spot: return "spot";
        case VenueShowLight::Role::Blinder: return "blinder";
        case VenueShowLight::Role::Strobe: return "strobe";
        case VenueShowLight::Role::Static: return "static";
        }
        return "?";
    }
}


VenueScene::Stripped VenueScene::Strip( json& ioScene )
{
    Stripped stripped;
    if( !ioScene.is_object() )
    {
        return stripped;
    }
    if( ioScene.contains( "Cores" ) )
    {
        stripped.Cores = ioScene["Cores"].is_array() ? static_cast<int>( ioScene["Cores"].size() ) : 1;
        ioScene.erase( "Cores" );
    }
    if( !ioScene.contains( "Entities" ) || !ioScene["Entities"].is_array() )
    {
        return stripped;
    }
    for( json& entity : ioScene["Entities"] )
    {
        if( !entity.is_object() || !entity.contains( "Components" ) || !entity["Components"].is_array() )
        {
            continue;
        }
        json& components = entity["Components"];
        bool camera = false;
        for( const json& component : components )
        {
            camera = camera || ( component.is_object() && component.value( "Type", std::string() ) == "Camera" );
        }
        json kept = json::array();
        for( json& component : components )
        {
            const std::string type = component.is_object() ? component.value( "Type", std::string() ) : std::string();
            if( type == "ScriptComponent" ) { ++stripped.Scripts; continue; }
            if( type == "UIDocument" ) { ++stripped.Documents; continue; }
            if( type == "AudioListener" ) { ++stripped.Listeners; continue; }
            if( type == "Camera" ) { ++stripped.Cameras; continue; }
            // A camera's grading and its rigs go with it: without the camera they'd do nothing,
            // or move nothing the director owns.
            if( camera && ( type == "PostProcess" || type == "FlyingCamera" || type == "CameraSway" ) ) continue;
            kept.push_back( std::move( component ) );
        }
        components = std::move( kept );
    }
    return stripped;
}


bool VenueScene::Collect( const std::vector<EntityHandle>& inRoots, Transform& inVenueRoot, Markers& outMarkers, std::string& outProblem )
{
    outMarkers = Markers();
    VenuePlan& plan = outMarkers.Plan;
    plan = VenuePlan::Empty();

    // Every entity under the roots, parents first.
    std::vector<Entity*> entities;
    const std::function<void( Transform& )> walk = [&]( Transform& inTransform ) {
        if( Entity* entity = inTransform.Parent.Get() ) entities.push_back( entity );
        for( Transform* child : inTransform.GetChildren() )
        {
            if( child ) walk( *child );
        }
    };
    for( const EntityHandle& root : inRoots )
    {
        if( !root ) continue;
        if( Transform* transform = root->TryGetComponent<Transform>() ) walk( *transform );
        else entities.push_back( root.Get() );
    }

    VenueInfo* info = nullptr;
    struct Area { VenueCrowdArea* Marker; Transform* Where; };
    std::vector<Area> areas;
    for( Entity* entity : entities )
    {
        Transform* transform = entity->TryGetComponent<Transform>();
        if( VenueInfo* found = entity->TryGetComponent<VenueInfo>() )
        {
            if( !info ) info = found;
            else YIKES_FMT( "[Venues] A second VenueInfo (%s) is ignored", entity->GetName().c_str() );
        }
        if( Light* light = entity->TryGetComponent<Light>() )
        {
            outMarkers.HasDirectional = outMarkers.HasDirectional || light->LightType == Moonlight::LightType::Directional;
            if( VenueShowLight* show = entity->TryGetComponent<VenueShowLight>() )
            {
                if( show->Kind == VenueShowLight::Role::Static )
                {
                    ++outMarkers.StaticLights;
                }
                else if( transform )
                {
                    ShowLight cued;
                    cued.Light = transform->Parent;
                    cued.Role = show->Kind;
                    cued.Group = show->Group;
                    outMarkers.Lights.push_back( cued );
                }
            }
        }
        else if( entity->TryGetComponent<VenueShowLight>() )
        {
            YIKES_FMT( "[Venues] %s is a VenueShowLight without a Light: ignored", entity->GetName().c_str() );
        }
        if( !transform )
        {
            continue;
        }
        if( VenueSpot* spot = entity->TryGetComponent<VenueSpot>() )
        {
            const int member = MemberOf( spot->Member );
            if( member >= 0 && !plan.Members[member].Present )
            {
                // The performer faces the marker's -Z; the plan's yaw turns their own +z.
                VenuePlan::Spot& place = plan.Members[member];
                place.Feet = PointIn( inVenueRoot, *transform, Vector3( 0.f, 0.f, 0.f ) );
                place.Yaw = YawOf( AxisIn( inVenueRoot, *transform, Vector3( 0.f, 0.f, -1.f ) ) );
                if( place.Yaw < 0.f ) place.Yaw += 360.f;
                place.Present = true;
                ++outMarkers.Spots;
            }
            else if( member >= 0 )
            {
                YIKES_FMT( "[Venues] A second spot for the same member (%s) is ignored", entity->GetName().c_str() );
            }
        }
        if( entity->HasComponent<VenueAccent>() ) outMarkers.Accents.push_back( transform->Parent );
        if( entity->HasComponent<VenueStory>() ) outMarkers.Story.push_back( transform->Parent );
        if( VenueCrowdArea* area = entity->TryGetComponent<VenueCrowdArea>() )
        {
            areas.push_back( { area, transform } );
        }
        if( VenueCameraSpot* camera = entity->TryGetComponent<VenueCameraSpot>() )
        {
            VenuePlan::CameraSpot shot;
            shot.Eye = PointIn( inVenueRoot, *transform, Vector3( 0.f, 0.f, 0.f ) );
            shot.Forward = AxisIn( inVenueRoot, *transform, Vector3( 0.f, 0.f, 1.f ) ).Normalized();
            shot.FieldOfView = std::clamp( camera->FieldOfView, 5.f, 140.f );
            shot.Shot = KindOf( camera->Shot );
            shot.Tag = camera->Tag.empty() ? entity->GetName() : camera->Tag;
            plan.Cameras.push_back( shot );
            ++outMarkers.Cameras;
        }
        if( VenueScreen* screen = entity->TryGetComponent<VenueScreen>() )
        {
            // The quad's size is the marker's scale; the picture faces its -Z, as the plan's
            // screens face -z turned by their yaw.
            const Vector3 centre = PointIn( inVenueRoot, *transform, Vector3( 0.f, 0.f, 0.f ) );
            const Vector3 scale = transform->GetWorldScale();
            if( screen->Source == VenueScreen::Feed::Lyrics )
            {
                if( plan.Lyrics.Present )
                {
                    YIKES_FMT( "[Venues] A second Lyrics screen (%s) is ignored", entity->GetName().c_str() );
                }
                else
                {
                    plan.Lyrics.Present = true;
                    plan.Lyrics.Centre = centre;
                    plan.Lyrics.Width = std::max( std::fabs( scale.x ), 0.5f );
                }
            }
            else
            {
                VenuePlan::Screen feed;
                feed.Centre = centre;
                feed.Width = std::max( std::fabs( scale.x ), 0.1f );
                feed.Height = std::max( std::fabs( scale.y ), 0.1f );
                feed.Yaw = YawOf( AxisIn( inVenueRoot, *transform, Vector3( 0.f, 0.f, 1.f ) ) );
                feed.Source = screen->Source == VenueScreen::Feed::Program ? VenuePlan::Screen::Feed::Program : VenuePlan::Screen::Feed::Stage;
                feed.Emissive = std::max( screen->Emissive, 0.f );
                plan.Screens.push_back( feed );
            }
            ++outMarkers.Screens;
        }
    }

    if( !info )
    {
        outProblem = "no VenueInfo marker";
        return false;
    }
    if( !plan.HasMember( VenueData::Drums ) )
    {
        outProblem = "no Drummer VenueSpot";
        return false;
    }

    // The room and the built-in pieces asked for. The procedural room never goes up round a scene.
    plan.Name = info->Name;
    plan.Bounds.Back = info->RoomBack;
    plan.Bounds.Ceiling = info->RoomCeiling;
    plan.Bounds.HalfWidth = std::max( info->RoomHalfWidth, 2.f );
    plan.Bounds.DeskZ = info->DeskZ;
    plan.Bounds.Outdoor = info->Outdoor;
    plan.BuildStage = info->BuildStage;
    plan.BuildSet = info->BuildSet;
    plan.BuildRig = info->BuildRig;
    plan.BuildFx = info->BuildFx;
    plan.BuildRoom = false;
    // Whatever's keyed by the room (the dressing's extras, the effects) dresses as the festival
    // out of doors and the club indoors.
    plan.Style = info->Outdoor ? 2 : 1;
    plan.HazeScale = std::max( info->Haze, 0.f ) * ( info->Outdoor ? 0.45f : 1.f );
    plan.Background = info->AmbientColor;
    plan.FogColor = info->FogColor;
    plan.SkyTime = std::clamp( info->SkyTime, 0.f, 24.f );
    plan.MoonBrightness = std::max( info->MoonBrightness, 0.f );
    plan.CloudCoverage = std::clamp( info->CloudCoverage, 0.f, 1.f );
    plan.HazeFroxels = info->HazeFroxels;
    plan.Footage = static_cast<int>( info->Footage );
    plan.Ride = std::max( info->Ride, 0.f );
    plan.RideUntil = info->RideUntil;
    plan.ColorKeep = Vector3( std::clamp( info->KeepRed, 0.f, 1.f ), std::clamp( info->KeepBlue, 0.f, 1.f ), std::clamp( info->KeepWarmth, 0.f, 1.f ) );
    plan.LightsFrom = info->LightsFrom;
    plan.LightsUntil = info->LightsUntil;

    // The stage as the band stands on it: its deck the lowest non-drummer's feet, the riser the
    // drummer's, the back wall behind the furthest back, wide enough for the widest.
    const VenuePlan::Spot& drums = plan.Members[VenueData::Drums];
    float deck = 1e9f;
    float front = 1e9f;
    float back = -1e9f;
    float wide = 0.f;
    for( int member = 0; member < static_cast<int>( plan.Members.size() ); ++member )
    {
        const VenuePlan::Spot& spot = plan.Members[member];
        if( !spot.Present ) continue;
        if( member != VenueData::Drums ) deck = std::min( deck, spot.Feet.y );
        front = std::min( front, spot.Feet.z );
        back = std::max( back, spot.Feet.z );
        wide = std::max( wide, std::fabs( spot.Feet.x ) );
    }
    if( deck > 1e8f ) deck = drums.Feet.y;
    plan.Stage.Height = deck;
    plan.Stage.RiserHeight = std::max( drums.Feet.y - deck, 0.f );
    plan.Stage.RiserZ = drums.Feet.z - 0.6f;
    plan.Stage.BackWallZ = back + 3.4f;
    plan.Stage.Depth = plan.Stage.BackWallZ - 0.6f;
    plan.Stage.HalfWidth = std::max( wide + 2.2f, 4.f );
    plan.Stage.TrussHeight = info->RoomCeiling < 900.f ? std::max( std::min( deck + 8.3f, info->RoomCeiling - 0.6f ), deck + 2.5f ) : deck + 8.3f;

    // The crowd: each area's figures, posed or a Mob of cheap ones on a grid spaced to hold its
    // head count.
    float crowdFront = -1e9f;
    const Vector3 focus = plan.HasMember( VenueData::Vocals ) ? plan.Members[VenueData::Vocals].Feet : drums.Feet;
    for( const Area& area : areas )
    {
        ++outMarkers.CrowdAreas;
        if( area.Marker->HeadCount <= 0 )
        {
            continue;
        }
        float minX = 1e9f, maxX = -1e9f, minZ = 1e9f, maxZ = -1e9f;
        for( float x : { -0.5f, 0.5f } )
        {
            for( float z : { -0.5f, 0.5f } )
            {
                const Vector3 corner = PointIn( inVenueRoot, *area.Where, Vector3( x, 0.f, z ) );
                minX = std::min( minX, corner.x );
                maxX = std::max( maxX, corner.x );
                minZ = std::min( minZ, corner.z );
                maxZ = std::max( maxZ, corner.z );
            }
        }
        VenuePlan::CrowdArea crowd;
        crowd.DanceFloor = area.Marker->DanceFloor;
        crowd.Type = area.Marker->Figures == VenueCrowdArea::Kind::Posed ? VenuePlan::CrowdArea::Kind::Posed : VenuePlan::CrowdArea::Kind::Mob;
        crowd.MinX = minX;
        crowd.MaxX = std::max( maxX, minX + 0.5f );
        crowd.MinZ = minZ;
        crowd.MaxZ = std::max( maxZ, minZ + 0.5f );
        crowd.FloorY = PointIn( inVenueRoot, *area.Where, Vector3( 0.f, 0.f, 0.f ) ).y;
        crowd.Heads = area.Marker->HeadCount;
        crowd.Density = 0.85f;
        // A grid with a quarter more spots taken than heads, so thinning to the count leaves it
        // even rather than short at the back.
        const float size = ( crowd.MaxX - crowd.MinX ) * ( crowd.MaxZ - crowd.MinZ );
        crowd.Spacing = std::clamp( std::sqrt( size * crowd.Density / ( 1.1f * 1.25f * static_cast<float>( crowd.Heads ) ) ), 0.4f, 3.f );
        // Jitter 0.5 is the usual stray (Scatter 1).
        crowd.Scatter = std::clamp( area.Marker->Jitter, 0.f, 1.f ) * 2.f;
        crowd.Yaw = YawOf( AxisIn( inVenueRoot, *area.Where, Vector3( 0.f, 0.f, 1.f ) ) );
        crowd.Turn = 0.85f;
        crowd.Focus = focus;
        // Posed rows fill the whole rectangle, front to back (Crowd::BuildRows), rather than
        // the built-in rooms' wedge that widens away from the stage.
        crowd.FrontHalfWidth = ( crowd.MaxX - crowd.MinX ) * 0.5f;
        crowd.Widen = 0.f;
        crowdFront = std::max( crowdFront, crowd.MaxZ );
        plan.Crowd.push_back( crowd );
    }
    plan.BuildCrowd = !plan.Crowd.empty();
    plan.Stage.BarricadeZ = crowdFront > -1e8f ? std::min( crowdFront + 0.8f, front - 0.4f ) : front - 1.6f;

    // The director's framings were placed for the procedural rooms' stage: they move by how far
    // this band's middle sits from that band's (the same members).
    VenuePlan rooms = VenuePlan::ForStyle( 0 );
    for( size_t i = 0; i < plan.Members.size(); ++i )
    {
        rooms.Members[i].Present = plan.Members[i].Present;
    }
    plan.ShotOffset = plan.MemberCentre() - rooms.MemberCentre();
    return true;
}


bool VenueScene::Load( World& inWorld, const std::string& inPath, Transform& inVenueRoot, std::string& outProblem )
{
    Clear();
    json scene = SceneStreaming::ReadScene( inPath );
    if( scene.is_null() || !scene.is_object() )
    {
        outProblem = "can't read " + inPath;
        return false;
    }
    SceneSerializer::RemapAssetReferences( scene, inPath );
    const Stripped stripped = Strip( scene );
    if( stripped.Total() > 0 )
    {
        INFO_FMT( "[Venues]", "%s: took out %d core(s), %d script(s), %d UI document(s), %d camera(s), %d audio listener(s)", inPath.c_str(),
            stripped.Cores, stripped.Scripts, stripped.Documents, stripped.Cameras, stripped.Listeners );
    }
    m_entityCount = scene.contains( "Entities" ) && scene["Entities"].is_array() ? scene["Entities"].size() : 0;
    // As a prefab is instanced at run time (World::CreateFromPrefab): fresh GUIDs, no cores, each
    // entity held as loading until its components are all in and initialised.
    SceneSerializer::LoadOptions options;
    options.RemapGUIDs = true;
    options.LoadCores = false;
    options.Parent = &inVenueRoot;
    m_roots = SceneSerializer::Deserialize( inWorld, scene, options );
    if( m_roots.empty() )
    {
        outProblem = inPath + " has no entities";
        Clear();
        return false;
    }
    if( !Collect( m_roots, inVenueRoot, m_markers, outProblem ) )
    {
        Clear();
        return false;
    }
    const VenuePlan& plan = m_markers.Plan;
    int cued[6] = {};
    for( const ShowLight& light : m_markers.Lights )
    {
        ++cued[std::clamp( static_cast<int>( light.Role ), 0, 5 )];
    }
    INFO_FMT( "[Venues]", "%s (\"%s\"): %d entities, %d spots, %d crowd areas, %d camera spots, %d screens; lights cued: %d %s, %d %s, %d %s, %d %s, %d %s; %d static%s",
        inPath.c_str(), plan.Name.c_str(), static_cast<int>( m_entityCount ), m_markers.Spots, m_markers.CrowdAreas, m_markers.Cameras, m_markers.Screens,
        cued[0], RoleName( VenueShowLight::Role::Wash ), cued[1], RoleName( VenueShowLight::Role::Beam ), cued[2], RoleName( VenueShowLight::Role::Spot ),
        cued[3], RoleName( VenueShowLight::Role::Blinder ), cued[4], RoleName( VenueShowLight::Role::Strobe ), m_markers.StaticLights,
        m_markers.HasDirectional ? ", its own directional" : ", no directional" );
    return true;
}


bool VenueScene::Adopt( const std::vector<EntityHandle>& inRoots, Transform& inVenueRoot, std::string& outProblem )
{
    Clear();
    if( !Collect( inRoots, inVenueRoot, m_markers, outProblem ) )
    {
        m_markers = Markers();
        return false;
    }
    m_roots = inRoots;
    m_adopted = true;
    m_entityCount = inRoots.size();
    INFO_FMT( "[Venues]", "The open scene (\"%s\"): %d spots, %d crowd areas, %d camera spots, %d screens, %d cued lights, %d static%s",
        m_markers.Plan.Name.c_str(), m_markers.Spots, m_markers.CrowdAreas, m_markers.Cameras, m_markers.Screens, static_cast<int>( m_markers.Lights.size() ),
        m_markers.StaticLights, m_markers.HasDirectional ? ", its own directional" : ", no directional" );
    return true;
}


void VenueScene::Clear()
{
    for( EntityHandle& root : m_roots )
    {
        if( root && !m_adopted ) root->MarkForDelete();
    }
    m_adopted = false;
    m_roots.clear();
    m_markers = Markers();
    m_entityCount = 0;
}
