#include "Venue/VenueShow.h"
#include "Venue/VenueLayout.h"
#include "Venue/VenueTiming.h"
#include "Components/Camera.h"
#include "Components/Graphics/PostProcess.h"
#include "Components/Lighting/Light.h"
#include "Components/Transform.h"
#include "Config/GameSettings.h"
#include "Core/CommandLine.h"
#include "Engine/World.h"
#include "Graphics/Texture.h"
#include "Materials/StandardMaterial.h"
#include "Resource/ResourceCache.h"
#include "Dementia.h"
#include "CLog.h"
#include <algorithm>
#include <cmath>

namespace
{
    using Shape = Moonlight::MeshType;
    constexpr int kCrowdSize = 520;
    // The highway fades into the venue between these distances from its camera.
    constexpr float kHighwayFadeStart = 42.f;
    constexpr float kHighwayFadeEnd = 120.f;
    constexpr float kHighwayBoardOpacity = 0.6f;
    // The follow spots' floor: a front light on the band in every look.
    constexpr float kFrontFill = 0.18f;
}


void VenueShow::Clear()
{
    // Give the screen back to the highway's camera before the venue's goes.
    if( m_savedHighway && m_highwayCamera && m_highwayCamera->HasComponent<Camera>() )
    {
        Camera& camera = m_highwayCamera->GetComponent<Camera>();
        camera.Overlay = false;
        camera.OverlayDarkOpacity = 1.f;
        camera.SetCurrent();
        if( m_highwayCamera->HasComponent<PostProcess>() )
        {
            m_highwayCamera->GetComponent<PostProcess>().Fog = m_highwayFog;
        }
    }
    m_savedHighway = false;
    m_highwayCamera = {};
    m_lights.Clear();
    m_director.Clear();
    m_crowd.Clear();
    m_band.Clear();
    m_kit.Clear();
    m_root = {};
    m_edgeStrip.clear();
    m_pyro.clear();
    m_venue.Clear();
    m_beats.clear();
}


const char* VenueShow::StyleName( Style inStyle )
{
    switch( inStyle )
    {
    case Style::Arena: return "Arena";
    case Style::Club: return "Club";
    case Style::Festival: return "Festival";
    default: return "";
    }
}


void VenueShow::NextStyle()
{
    if( !m_world || !m_track || !m_highwayCamera )
    {
        return;
    }
    World& world = *m_world;
    const TrackData& track = *m_track;
    const EntityHandle highway = m_highwayCamera;
    const int next = ( static_cast<int>( m_style ) + 1 ) % static_cast<int>( Style::Count );
    Build( world, track, highway, next );
}


void VenueShow::Build( World& inWorld, const TrackData& inTrack, const EntityHandle& inHighwayCamera, int inStyle )
{
    Clear();
    m_world = &inWorld;
    m_track = &inTrack;
    const int setting = GameSettings::GetInstance().Venue;
    if( setting <= 0 || CommandLine::Has( "--no-venue" ) )
    {
        return;
    }
    int style = inStyle >= 0 ? inStyle : GameSettings::GetInstance().VenueStyle;
    if( CommandLine::Has( "--venue-style" ) )
    {
        style = CommandLine::GetInt( "--venue-style", style );
    }
    if( inStyle < 0 && style >= static_cast<int>( Style::Count ) )
    {
        // Random: a different room each song, repeatable for a track.
        uint32_t hash = 2166136261u;
        for( char c : inTrack.m_trackName ) hash = ( hash ^ static_cast<uint8_t>( c ) ) * 16777619u;
        style = static_cast<int>( hash % static_cast<uint32_t>( Style::Count ) );
    }
    m_style = static_cast<Style>( std::clamp( style, 0, static_cast<int>( Style::Count ) - 1 ) );
    m_venue = inTrack.m_venue;
    m_beats = inTrack.m_beats;
    m_bpm = inTrack.m_bpm > 30 ? static_cast<float>( inTrack.m_bpm ) : 120.f;
    m_kit.Begin( inWorld );
    m_root = m_kit.Group( "Venue", nullptr, VenueLayout::kVenueOrigin );
    if( !m_root )
    {
        return;
    }
    Transform& root = m_root->GetComponent<Transform>();
    BuildStage( root );

    float lastNote = 0.f;
    for( const NoteData& note : inTrack.m_noteData ) lastNote = std::max( lastNote, note.m_triggerTime );
    m_band.Build( m_kit, &root, m_venue, inTrack.m_noteData, m_beats, m_bpm );
    if( setting >= 2 )
    {
        // Each room holds a different crowd.
        int count = kCrowdSize;
        float back = VenueLayout::kCrowdBackZ;
        float halfWidth = VenueLayout::kCrowdHalfWidth;
        if( m_style == Style::Club )
        {
            count = 240;
            back = -15.f;
            halfWidth = 11.5f;
        }
        else if( m_style == Style::Festival )
        {
            count = 800;
            back = -42.f;
            halfWidth = 24.f;
        }
        m_crowd.Build( m_kit, &root, m_venue, m_beats, m_bpm, CommandLine::GetInt( "--crowd-size", count ), back, halfWidth );
    }
    m_director.Build( inWorld, m_venue, m_beats, m_bpm, std::max( lastNote + 4.f, inTrack.m_duration ), GameSettings::GetInstance().VenueCamera == 1, &m_band );
    VenueKit* kit = &m_kit;
    m_lights.Build( inWorld, &root, m_director.MainCamera(), inTrack,
        [kit]( const Vector3& inPosition, const Vector3& inScale, const Vector3& inColor, const Vector3& inEmissive, Transform* inParent ) { return kit->Box( inPosition, inScale, inColor, inParent, inEmissive ); },
        []( const EntityHandle& inTarget, const Vector3& inColor, const Vector3& inEmissive ) { VenueKit::SetColor( inTarget, inColor, inEmissive ); } );
    m_director.SetRoomBack( m_style == Style::Club ? -17.f : m_style == Style::Arena ? -34.f : -1000.f );
    if( m_style == Style::Festival )
    {
        // Out of doors: a night sky, and less haze for it to hang in.
        m_lights.SetHazeScale( 0.45f );
        if( const EntityHandle& camera = m_director.MainCamera() )
        {
            Camera& sky = camera->GetComponent<Camera>();
            sky.ClearType = Moonlight::ClearColorType::Procedural;
            sky.ProceduralSky.Time = 22.f;
            sky.ProceduralSky.StarBrightness = 2.f;
            sky.ProceduralSky.MoonPhase = 0.5f;
            sky.ProceduralSky.CloudCoverage = 0.25f;
            if( camera->HasComponent<PostProcess>() )
            {
                camera->GetComponent<PostProcess>().FogMaxOpacity = 0.55f;
            }
        }
    }
    else if( m_style == Style::Club )
    {
        m_lights.SetHazeScale( 1.4f );
    }

    // The highway draws over the venue from now on, fading into it toward its far end instead of
    // into black fog.
    m_highwayCamera = inHighwayCamera;
    if( m_highwayCamera && m_highwayCamera->HasComponent<Camera>() )
    {
        Camera& camera = m_highwayCamera->GetComponent<Camera>();
        camera.Overlay = true;
        camera.OverlayFadeStart = kHighwayFadeStart;
        camera.OverlayFadeEnd = kHighwayFadeEnd;
        // The dark board lets the stage show through; notes, lines and pads stay solid.
        camera.OverlayDarkOpacity = kHighwayBoardOpacity;
        if( CommandLine::Has( "--venue-only" ) )
        {
            // Diagnostics: fade the whole highway out, to frame the venue.
            camera.OverlayFadeStart = 0.f;
            camera.OverlayFadeEnd = 0.001f;
        }
        if( m_highwayCamera->HasComponent<PostProcess>() )
        {
            PostProcess& post = m_highwayCamera->GetComponent<PostProcess>();
            m_highwayFog = post.Fog;
            post.Fog = false;
        }
        m_savedHighway = true;
    }
    if( CommandLine::Has( "--highway-log" ) )
    {
        BRUH_FMT( "Venue: %d camera cuts, %d looks, crowd of %d", static_cast<int>( m_director.CutCount() ), static_cast<int>( m_venue.m_postFx.size() ), static_cast<int>( m_crowd.Size() ) );
    }
}


void VenueShow::BuildScreen( Transform& inRoot, const Vector3& inCentre, const Vector3& inSize, float inYaw, const char* inTexture )
{
    // A frame, and a plane facing the crowd whose emission is the feed camera's image.
    EntityHandle frame = m_kit.Box( inCentre + Vector3( 0.f, 0.f, 0.08f ), Vector3( inSize.x + 0.3f, inSize.y + 0.3f, 0.14f ), Vector3( 0.02f, 0.02f, 0.02f ), &inRoot );
    if( frame ) frame->GetComponent<Transform>().SetRotation( Vector3( 0.f, inYaw, 0.f ) );
    EntityHandle screen = m_kit.Piece( Shape::Plane, inCentre, Vector3( inSize.x, 1.f, inSize.y ), Vector3( 0.f, 0.f, 0.f ), &inRoot, Vector3( 1.f, 1.f, 1.f ) );
    if( !screen )
    {
        return;
    }
    // The plane lies in XZ facing +y: stand it up facing the crowd (-z).
    screen->GetComponent<Transform>().SetRotation( Quaternion::FromEulerDegrees( Vector3( 0.f, inYaw, 0.f ) ) * Quaternion::FromEulerDegrees( Vector3( -90.f, 0.f, 0.f ) ) );
    if( StandardMaterial* material = VenueKit::MaterialOf( screen ) )
    {
        material->SetTexture( Moonlight::TextureType::Emissive, ResourceCache::GetInstance().Get<Moonlight::Texture>( Path( inTexture ) ) );
        material->EmissiveColor = Vector3( 1.f, 1.f, 1.f );
        material->EmissiveIntensity = 2.2f;
        material->Roughness = 0.9f;
        material->Tiling = Vector2( 1.f, -1.f );
        material->Offset = Vector2( 0.f, 1.f );
    }
}


void VenueShow::BuildStage( Transform& inRoot )
{
    using namespace VenueLayout;
    const Vector3 black( 0.015f, 0.015f, 0.018f );
    const Vector3 deckColor( 0.05f, 0.05f, 0.055f );
    const Vector3 metal( 0.18f, 0.18f, 0.2f );
    // The stage, the same in every room: the deck, the drum riser, the back wall with its LED
    // wall, speaker stacks, truss towers and the overhead truss (where the washes hang), the
    // barricade, the LED strip along the front edge, and pyro.
    m_kit.Box( Vector3( 0.f, kStageHeight * 0.5f, kStageDepth * 0.5f + 0.3f ), Vector3( kStageHalfWidth * 2.f, kStageHeight, kStageDepth + 0.6f ), deckColor, &inRoot );
    m_kit.Box( Vector3( 0.f, kStageHeight * 0.5f, -0.02f ), Vector3( kStageHalfWidth * 2.f, kStageHeight, 0.06f ), black, &inRoot );
    m_kit.Box( Vector3( 0.f, kStageHeight + kRiserHeight * 0.5f, kRiserZ + 0.5f ), Vector3( 3.4f, kRiserHeight, 2.8f ), Vector3( 0.06f, 0.06f, 0.07f ), &inRoot );
    m_kit.Box( Vector3( 0.f, kStageHeight + kRiserHeight * 0.5f, kRiserZ - 0.91f ), Vector3( 3.4f, kRiserHeight, 0.04f ), Vector3( 0.02f, 0.02f, 0.02f ), &inRoot, Vector3( 0.05f, 0.05f, 0.06f ) );
    m_kit.Box( Vector3( 0.f, 6.f, kBackWallZ + 0.2f ), Vector3( 24.f, 12.f, 0.4f ), black, &inRoot );
    for( float side : { -1.f, 1.f } )
    {
        for( int box = 0; box < 3; ++box )
        {
            const Vector3 centre( side * ( kStageHalfWidth + 1.1f ), 0.75f + box * 1.45f, 1.2f );
            m_kit.Box( centre, Vector3( 1.8f, 1.4f, 1.2f ), Vector3( 0.02f, 0.02f, 0.02f ), &inRoot );
            m_kit.Box( centre + Vector3( 0.f, 0.f, -0.61f ), Vector3( 1.6f, 1.2f, 0.02f ), Vector3( 0.05f, 0.05f, 0.055f ), &inRoot );
        }
        m_kit.Box( Vector3( side * ( kStageHalfWidth + 0.4f ), kTrussHeight * 0.5f, 0.2f ), Vector3( 0.4f, kTrussHeight, 0.4f ), metal, &inRoot );
        m_kit.Box( Vector3( side * ( kStageHalfWidth + 0.4f ), kTrussHeight * 0.5f, 9.f ), Vector3( 0.4f, kTrussHeight, 0.4f ), metal, &inRoot );
    }
    for( float z : { 0.2f, 4.6f, 9.f } )
    {
        m_kit.Box( Vector3( 0.f, kTrussHeight, z ), Vector3( kStageHalfWidth * 2.f + 1.2f, 0.4f, 0.4f ), metal, &inRoot );
    }
    for( float x : { -kStageHalfWidth - 0.4f, -4.6f, 4.6f, kStageHalfWidth + 0.4f } )
    {
        m_kit.Box( Vector3( x, kTrussHeight, 4.6f ), Vector3( 0.3f, 0.3f, 9.2f ), metal, &inRoot );
    }
    BuildScreen( inRoot, Vector3( 0.f, 6.9f, kBackWallZ - 0.05f ), Vector3( 12.f, 6.f, 0.f ), 0.f, Director::kProgramTexture );
    m_kit.Box( Vector3( 0.f, 0.55f, kBarricadeZ ), Vector3( 20.f, 1.1f, 0.12f ), metal, &inRoot );
    for( int segment = 0; segment < 12; ++segment )
    {
        const float x = -kStageHalfWidth + ( segment + 0.5f ) * ( kStageHalfWidth * 2.f / 12.f );
        m_edgeStrip.push_back( m_kit.Box( Vector3( x, kStageHeight - 0.08f, -0.06f ), Vector3( kStageHalfWidth * 2.f / 12.f - 0.05f, 0.08f, 0.03f ), Vector3( 0.f, 0.f, 0.f ), &inRoot ) );
    }
    // Pyro along the front edge: a flame column and its light per emitter, out of sight until the
    // chart's bonus effects fire.
    for( float x : { -7.5f, -3.f, 3.f, 7.5f } )
    {
        Pyro pyro;
        pyro.Base = Vector3( x, kStageHeight, 0.35f );
        m_kit.Box( pyro.Base + Vector3( 0.f, 0.1f, 0.f ), Vector3( 0.4f, 0.2f, 0.4f ), Vector3( 0.03f, 0.03f, 0.03f ), &inRoot );
        pyro.Flame = m_kit.Piece( Shape::Capsule, pyro.Base + Vector3( 0.f, -5.f, 0.f ), Vector3( 0.5f, 3.f, 0.5f ), Vector3( 0.f, 0.f, 0.f ), &inRoot, Vector3( 30.f, 9.f, 1.5f ) );
        pyro.Light = m_kit.Group( "PyroLight", &inRoot, pyro.Base + Vector3( 0.f, 1.5f, -0.4f ) );
        if( pyro.Light )
        {
            Light& light = pyro.Light->AddComponent<Light>();
            light.LightType = Moonlight::LightType::Point;
            light.Color = Vector3( 1.f, 0.55f, 0.2f );
            light.Intensity = 0.f;
            light.Range = 14.f;
            light.CastShadows = false;
        }
        m_pyro.push_back( pyro );
    }
    switch( m_style )
    {
    case Style::Club: BuildClub( inRoot ); break;
    case Style::Festival: BuildFestival( inRoot ); break;
    default: BuildArena( inRoot ); break;
    }
}


void VenueShow::BuildArena( Transform& inRoot )
{
    // A big dark room: a wide floor, walls far off in the haze, screens either side of the stage.
    const Vector3 black( 0.015f, 0.015f, 0.018f );
    const Vector3 metal( 0.18f, 0.18f, 0.2f );
    m_kit.Box( Vector3( 0.f, -0.05f, -8.f ), Vector3( 70.f, 0.1f, 60.f ), Vector3( 0.03f, 0.03f, 0.035f ), &inRoot );
    m_kit.Box( Vector3( 0.f, 7.f, VenueLayout::kBackWallZ + 0.6f ), Vector3( 70.f, 14.f, 0.4f ), black, &inRoot );
    m_kit.Box( Vector3( 0.f, 7.f, -34.f ), Vector3( 70.f, 14.f, 0.4f ), black, &inRoot );
    for( float side : { -1.f, 1.f } )
    {
        m_kit.Box( Vector3( side * 22.f, 7.f, -8.f ), Vector3( 0.5f, 14.f, 60.f ), black, &inRoot );
        BuildScreen( inRoot, Vector3( side * 14.f, 7.2f, 2.f ), Vector3( 6.f, 3.4f, 0.f ), side * 16.f, Director::kFeedTexture );
        m_kit.Box( Vector3( side * 14.f, 4.2f, 2.3f ), Vector3( 0.2f, 2.8f, 0.2f ), metal, &inRoot );
        // Exit signs.
        m_kit.Box( Vector3( side * 21.7f, 3.f, -20.f ), Vector3( 0.05f, 0.3f, 0.8f ), Vector3( 0.f, 0.f, 0.f ), &inRoot, Vector3( 0.1f, 2.f, 0.3f ) );
    }
}


void VenueShow::BuildClub( Transform& inRoot )
{
    // A sweaty club: brick walls close in, a low ceiling, neon on the walls and a bar at the back.
    const Vector3 brick( 0.16f, 0.06f, 0.045f );
    const Vector3 ceiling( 0.03f, 0.03f, 0.03f );
    m_kit.Box( Vector3( 0.f, -0.05f, -3.f ), Vector3( 28.f, 0.1f, 30.f ), Vector3( 0.06f, 0.04f, 0.03f ), &inRoot );
    m_kit.Box( Vector3( 0.f, 10.6f, -3.f ), Vector3( 28.f, 0.3f, 30.f ), ceiling, &inRoot );
    m_kit.Box( Vector3( 0.f, 5.f, -17.f ), Vector3( 28.f, 10.f, 0.4f ), brick, &inRoot );
    for( float side : { -1.f, 1.f } )
    {
        m_kit.Box( Vector3( side * 12.8f, 5.f, -3.f ), Vector3( 0.4f, 10.f, 30.f ), brick, &inRoot );
        // Neon: a zigzag and a ring of tubes on each side wall.
        const Vector3 neon = side < 0.f ? Vector3( 3.f, 0.25f, 2.2f ) : Vector3( 0.25f, 2.2f, 3.f );
        for( int i = 0; i < 4; ++i )
        {
            EntityHandle tube = m_kit.Box( Vector3( side * 12.55f, 5.f + ( i % 2 ) * 0.5f, -6.f + i * 0.9f ), Vector3( 0.06f, 0.08f, 1.1f ), Vector3( 0.f, 0.f, 0.f ), &inRoot, neon );
            if( tube ) tube->GetComponent<Transform>().SetRotation( Vector3( ( i % 2 == 0 ? 30.f : -30.f ), 0.f, 0.f ) );
        }
        for( int i = 0; i < 8; ++i )
        {
            const float angle = i * 3.14159265f / 4.f;
            EntityHandle tube = m_kit.Box( Vector3( side * 12.55f, 5.2f + std::sin( angle ) * 0.9f, -11.f + std::cos( angle ) * 0.9f ), Vector3( 0.06f, 0.08f, 0.7f ), Vector3( 0.f, 0.f, 0.f ), &inRoot, side < 0.f ? Vector3( 0.3f, 2.5f, 1.f ) : Vector3( 3.f, 1.2f, 0.2f ) );
            if( tube ) tube->GetComponent<Transform>().SetRotation( Vector3( -angle * 180.f / 3.14159265f, 0.f, 0.f ) );
        }
    }
    // The bar along the back wall, its shelf of bottles lit from below.
    m_kit.Box( Vector3( 0.f, 0.55f, -15.6f ), Vector3( 14.f, 1.1f, 0.8f ), Vector3( 0.12f, 0.06f, 0.03f ), &inRoot );
    m_kit.Box( Vector3( 0.f, 1.12f, -15.2f ), Vector3( 14.f, 0.03f, 0.05f ), Vector3( 0.f, 0.f, 0.f ), &inRoot, Vector3( 2.f, 1.f, 0.3f ) );
    for( int i = 0; i < 24; ++i )
    {
        const float x = -6.5f + i * 0.56f;
        const Vector3 glass = i % 3 == 0 ? Vector3( 0.6f, 0.4f, 0.1f ) : i % 3 == 1 ? Vector3( 0.1f, 0.4f, 0.15f ) : Vector3( 0.5f, 0.5f, 0.55f );
        m_kit.Piece( Shape::Cylinder, Vector3( x, 2.2f, -16.6f ), Vector3( 0.12f, 0.36f, 0.12f ), glass, &inRoot, glass * 0.6f );
    }
    m_kit.Box( Vector3( 0.f, 2.f, -16.65f ), Vector3( 14.f, 0.04f, 0.3f ), Vector3( 0.1f, 0.06f, 0.04f ), &inRoot );
}


void VenueShow::BuildFestival( Transform& inRoot )
{
    // Open air at night: a field to the horizon, a roof over the stage, screens on towers, a
    // mixing tent in the crowd and delay towers further back.
    const Vector3 metal( 0.18f, 0.18f, 0.2f );
    const Vector3 canvas( 0.05f, 0.05f, 0.06f );
    m_kit.Box( Vector3( 0.f, -0.05f, -40.f ), Vector3( 400.f, 0.1f, 300.f ), Vector3( 0.02f, 0.04f, 0.02f ), &inRoot );
    // The roof: a canopy on four legs, a little above the truss.
    m_kit.Box( Vector3( 0.f, 12.4f, 4.8f ), Vector3( 24.f, 0.5f, 12.f ), canvas, &inRoot );
    for( float x : { -11.5f, 11.5f } )
    {
        for( float z : { -0.8f, 10.4f } )
        {
            m_kit.Box( Vector3( x, 6.2f, z ), Vector3( 0.6f, 12.4f, 0.6f ), metal, &inRoot );
        }
    }
    for( float side : { -1.f, 1.f } )
    {
        // Screen towers flanking the stage.
        m_kit.Box( Vector3( side * 17.f, 5.f, 1.5f ), Vector3( 0.8f, 10.f, 0.8f ), metal, &inRoot );
        BuildScreen( inRoot, Vector3( side * 17.f, 9.5f, 1.f ), Vector3( 8.f, 4.5f, 0.f ), side * 10.f, Director::kFeedTexture );
        // Delay towers with a wash of their own colour.
        for( float z : { -26.f, -40.f } )
        {
            m_kit.Box( Vector3( side * 14.f, 4.f, z ), Vector3( 0.6f, 8.f, 0.6f ), metal, &inRoot );
            m_kit.Box( Vector3( side * 14.f, 8.2f, z ), Vector3( 1.4f, 0.8f, 0.8f ), Vector3( 0.02f, 0.02f, 0.02f ), &inRoot, Vector3( 0.4f, 0.2f, 1.f ) );
        }
    }
    // The mixing tent.
    m_kit.Box( Vector3( 0.f, 1.f, -24.f ), Vector3( 6.f, 2.f, 4.f ), Vector3( 0.03f, 0.03f, 0.03f ), &inRoot );
    m_kit.Box( Vector3( 0.f, 3.2f, -24.f ), Vector3( 7.f, 0.3f, 5.f ), Vector3( 0.15f, 0.15f, 0.16f ), &inRoot );
    m_kit.Box( Vector3( 0.f, 2.05f, -22.05f ), Vector3( 5.f, 0.06f, 0.04f ), Vector3( 0.f, 0.f, 0.f ), &inRoot, Vector3( 0.2f, 1.5f, 0.4f ) );
}


void VenueShow::UpdateSet( double inSeconds, float inDeltaTime )
{
    (void)inDeltaTime;
    // The edge strip glows with the washes, a chase running along it on the beat.
    double beat = 0.0;
    int measureBeat = 0;
    VenueTiming::BeatAt( m_beats, m_bpm, inSeconds, beat, measureBeat );
    const Vector3 glow = m_lights.WashGlow();
    for( size_t i = 0; i < m_edgeStrip.size(); ++i )
    {
        const double phase = beat * 2.0 - static_cast<double>( i ) * 0.25;
        const float chase = 0.5f + 0.5f * static_cast<float>( std::pow( 1.0 - ( phase - std::floor( phase ) ), 3.0 ) );
        VenueKit::SetColor( m_edgeStrip[i], Vector3( 0.f, 0.f, 0.f ), glow * ( 3.f * chase ) + Vector3( 0.02f, 0.02f, 0.03f ) );
    }
    // Pyro: a column shooting up and dying away over a second and a half.
    float burst = 0.f;
    for( float time : m_venue.m_bonusFx )
    {
        if( time > inSeconds ) break;
        const float since = static_cast<float>( inSeconds ) - time;
        if( since < 1.6f ) burst = std::max( burst, std::exp( -since / 0.45f ) );
    }
    if( GameSettings::GetInstance().StageLighting == 1 )
    {
        burst *= 0.4f;
    }
    for( size_t i = 0; i < m_pyro.size(); ++i )
    {
        Pyro& pyro = m_pyro[i];
        const float flicker = 0.85f + 0.15f * std::sin( static_cast<float>( inSeconds ) * 31.f + i * 2.f );
        const float height = 3.2f * burst * flicker;
        if( pyro.Flame )
        {
            Transform& flame = pyro.Flame->GetComponent<Transform>();
            if( height > 0.05f )
            {
                flame.SetPosition( pyro.Base + Vector3( 0.f, 0.2f + height * 0.5f, 0.f ) );
                flame.SetScale( VenueKit::ScaleFor( Shape::Capsule, Vector3( 0.35f + 0.25f * burst, height, 0.35f + 0.25f * burst ) ) );
            }
            else
            {
                flame.SetPosition( pyro.Base + Vector3( 0.f, -5.f, 0.f ) );
            }
        }
        if( pyro.Light )
        {
            pyro.Light->GetComponent<Light>().Intensity = 4000.f * burst * flicker;
        }
    }
}


void VenueShow::Update( double inSongTimeMs, float inDeltaTime )
{
    if( !m_root )
    {
        return;
    }
    // --venue-time <seconds> shows the venue that far into the song (to frame a moment without
    // playing up to it).
    static const double kPreviewOffset = CommandLine::GetFloat( "--venue-time", 0.f );
    inSongTimeMs += kPreviewOffset * 1000.0;
    const double seconds = inSongTimeMs / 1000.0;
    // A roar when the song ends.
    for( const TimedCueData& event : m_venue.m_songEvents )
    {
        if( ( event.m_name == "music_end" || event.m_name == "end" ) && seconds > event.m_time && seconds < event.m_time + 1.0 )
        {
            m_crowd.OnCheer( 1.f );
        }
    }
    m_crowd.Update( seconds, inDeltaTime, m_performance );
    m_band.Update( seconds, inDeltaTime, m_crowd.Size() > 0 ? m_crowd.Energy() : 0.6f );
    m_director.Update( seconds, inDeltaTime );
    m_lights.SetCrowdEnergy( m_crowd.Size() > 0 ? m_crowd.Energy() : 0.6f );
    // The follow spots keep a little front light on the band so they read in any look, and come
    // up full on whoever's soloing.
    const int spotMembers[5] = { VenueData::Keys, VenueData::Vocals, VenueData::Guitar, VenueData::Drums, VenueData::Bass };
    for( int slot = 0; slot < 5; ++slot )
    {
        const int member = spotMembers[slot];
        const bool solo = m_band.StateOf( member, seconds ) == "play_solo";
        m_lights.SetSpotlightFloor( slot, !m_band.HasMember( member ) ? 0.f : solo ? 0.85f : kFrontFill );
    }
    m_lights.Update( inSongTimeMs, inDeltaTime );
    UpdateSet( seconds, inDeltaTime );
}


void VenueShow::OnHit( PadId inPad )
{
    m_lights.OnHit( inPad );
}


void VenueShow::OnMiss()
{
    m_lights.OnMiss();
    m_crowd.OnMiss();
}


void VenueShow::OnStreak( int inCombo )
{
    // Every fifty in a row gets a cheer.
    if( inCombo > 0 && inCombo % 50 == 0 )
    {
        m_crowd.OnCheer( std::min( 1.f, 0.5f + inCombo / 400.f ) );
    }
}
