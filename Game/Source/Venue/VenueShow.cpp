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
#include <chrono>
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
    // The arena's floor plan behind the crowd (venue z): the mixing desk, where the back stands
    // start, their steps, and the back wall behind the top step; the side stands start at
    // kArenaSideStandsX either side.
    constexpr float kArenaDeskZ = -22.f;
    constexpr float kArenaStandsZ = -32.f;
    constexpr int kArenaTiers = 7;
    constexpr int kArenaSideTiers = 3;
    constexpr float kArenaTierDepth = 2.f;
    constexpr float kArenaTierRise = 0.8f;
    constexpr float kArenaBackWallZ = kArenaStandsZ - kArenaTierDepth * kArenaTiers;
    constexpr float kArenaSideStandsX = 15.5f;
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
    m_lyricBoard.Clear();
    m_lyrics.Clear();
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
    // Karaoke on the LED wall's lower part, above the drummer's head (the wall spans 3.9-9.9 m).
    m_lyrics.Build( m_venue.m_lyrics, m_venue.m_vocalPhrases, m_venue.m_vocalNotes );
    if( GameSettings::GetInstance().LyricsInVenue() )
    {
        m_lyricBoard.Build( m_kit, root, Vector3( 0.f, 4.75f, VenueLayout::kBackWallZ - 0.12f ), 11.f, m_lyrics );
    }

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
        const int posed = CommandLine::GetInt( "--crowd-size", count );
        m_crowd.Build( m_kit, &root, m_venue, m_beats, m_bpm, posed, back, halfWidth );
        // --crowd-size trims the back of the house in proportion.
        FillHouse( root, count > 0 ? std::clamp( static_cast<float>( posed ) / static_cast<float>( count ), 0.f, 4.f ) : 1.f );
    }
    m_director.Build( inWorld, m_venue, m_beats, m_bpm, std::max( lastNote + 4.f, inTrack.m_duration ), GameSettings::GetInstance().VenueCamera == 1, &m_band );
    VenueKit* kit = &m_kit;
    m_lights.Build( inWorld, &root, m_director.MainCamera(), inTrack,
        [kit]( const Vector3& inPosition, const Vector3& inScale, const Vector3& inColor, const Vector3& inEmissive, Transform* inParent ) { return kit->Box( inPosition, inScale, inColor, inParent, inEmissive ); },
        []( const EntityHandle& inTarget, const Vector3& inColor, const Vector3& inEmissive ) { VenueKit::SetColor( inTarget, inColor, inEmissive ); } );
    if( !m_lights.IsActive() )
    {
        // Stage Lights off: no rig, but a soft house light so the band still reads. Without any
        // directional the renderer would light the room with a daylight sun.
        if( EntityHandle key = m_kit.Group( "VenueKeyLight", &root ) )
        {
            key->GetComponent<Transform>().LookDirection( Vector3( 0.15f, -0.8f, 0.6f ).Normalized() );
            Light& light = key->AddComponent<Light>();
            light.LightType = Moonlight::LightType::Directional;
            light.DirectionalSource = Moonlight::DirectionalSource::Manual;
            light.Color = Vector3( 1.f, 0.92f, 0.8f );
            light.Intensity = 7.f;
        }
    }
    m_director.SetRoomBack( m_style == Style::Club ? -17.f : m_style == Style::Arena ? kArenaBackWallZ : -1000.f );
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
    // A big dark hall: the floor full to the mixing desk and beyond, stands rising at the back
    // and along the sides, a roof with the rigging grid, PA hangs either side of the stage.
    const Vector3 black( 0.015f, 0.015f, 0.018f );
    const Vector3 metal( 0.18f, 0.18f, 0.2f );
    const Vector3 seating( 0.035f, 0.03f, 0.04f );
    const Vector3 aisleGlow( 0.5f, 0.28f, 0.08f );
    const float back = kArenaBackWallZ;
    const float length = VenueLayout::kBackWallZ + 1.f - back;
    const float middle = ( VenueLayout::kBackWallZ + 1.f + back ) * 0.5f;
    m_kit.Box( Vector3( 0.f, -0.05f, middle ), Vector3( 70.f, 0.1f, length + 4.f ), Vector3( 0.03f, 0.03f, 0.035f ), &inRoot );
    m_kit.Box( Vector3( 0.f, 11.f, VenueLayout::kBackWallZ + 0.6f ), Vector3( 70.f, 22.f, 0.4f ), black, &inRoot );
    m_kit.Box( Vector3( 0.f, 11.f, back - 0.2f ), Vector3( 70.f, 22.f, 0.4f ), black, &inRoot );
    // The roof, and the grid the house rig hangs from.
    m_kit.Box( Vector3( 0.f, 22.f, middle ), Vector3( 46.f, 0.4f, length ), Vector3( 0.012f, 0.012f, 0.014f ), &inRoot );
    for( float z = -2.f; z > back + 2.f; z -= 9.f )
    {
        m_kit.Box( Vector3( 0.f, 19.5f, z ), Vector3( 40.f, 0.35f, 0.35f ), metal * 0.6f, &inRoot );
    }
    for( float x : { -12.f, 0.f, 12.f } )
    {
        m_kit.Box( Vector3( x, 19.5f, middle - 4.f ), Vector3( 0.35f, 0.35f, length - 14.f ), metal * 0.6f, &inRoot );
    }
    // The back stands: tiers rising to the back wall, an aisle light along each step.
    for( int tier = 0; tier < kArenaTiers; ++tier )
    {
        const float top = kArenaTierRise * static_cast<float>( tier + 1 );
        const float z = kArenaStandsZ - kArenaTierDepth * ( static_cast<float>( tier ) + 0.5f );
        m_kit.Box( Vector3( 0.f, top * 0.5f, z ), Vector3( 43.f, top, kArenaTierDepth ), seating, &inRoot );
        m_kit.Box( Vector3( 0.f, top + 0.01f, z + kArenaTierDepth * 0.5f - 0.05f ), Vector3( 43.f, 0.03f, 0.05f ), Vector3( 0.f, 0.f, 0.f ), &inRoot, aisleGlow );
    }
    m_kit.Box( Vector3( 0.f, kArenaTierRise * kArenaTiers + 0.55f, back + 0.5f ), Vector3( 43.f, 1.1f, 0.2f ), metal * 0.4f, &inRoot );
    for( float side : { -1.f, 1.f } )
    {
        m_kit.Box( Vector3( side * 22.f, 11.f, middle ), Vector3( 0.5f, 22.f, length + 4.f ), black, &inRoot );
        BuildScreen( inRoot, Vector3( side * 14.f, 7.2f, 2.f ), Vector3( 6.f, 3.4f, 0.f ), side * 16.f, Director::kFeedTexture );
        m_kit.Box( Vector3( side * 14.f, 4.2f, 2.3f ), Vector3( 0.2f, 2.8f, 0.2f ), metal, &inRoot );
        // The side stands, from beside the stage back to the back stands.
        for( int tier = 0; tier < kArenaSideTiers; ++tier )
        {
            const float top = kArenaTierRise * static_cast<float>( tier + 1 );
            const float x = side * ( kArenaSideStandsX + kArenaTierDepth * ( static_cast<float>( tier ) + 0.5f ) );
            const float z0 = kArenaStandsZ;
            const float z1 = -3.f;
            m_kit.Box( Vector3( x, top * 0.5f, ( z0 + z1 ) * 0.5f ), Vector3( kArenaTierDepth, top, z1 - z0 ), seating, &inRoot );
            m_kit.Box( Vector3( x - side * ( kArenaTierDepth * 0.5f - 0.05f ), top + 0.01f, ( z0 + z1 ) * 0.5f ), Vector3( 0.05f, 0.03f, z1 - z0 ), Vector3( 0.f, 0.f, 0.f ), &inRoot, aisleGlow );
        }
        // PA hangs either side of the stage.
        m_kit.Box( Vector3( side * 11.5f, 11.f, -0.4f ), Vector3( 1.2f, 4.6f, 1.1f ), black, &inRoot );
        m_kit.Box( Vector3( side * 11.5f, 16.f, -0.4f ), Vector3( 0.06f, 5.4f, 0.06f ), metal, &inRoot );
        // Exit signs over the side stands.
        m_kit.Box( Vector3( side * 21.7f, 4.6f, -20.f ), Vector3( 0.05f, 0.3f, 0.8f ), Vector3( 0.f, 0.f, 0.f ), &inRoot, Vector3( 0.1f, 2.f, 0.3f ) );
        m_kit.Box( Vector3( side * 9.f, kArenaTierRise * kArenaTiers + 2.f, back + 0.05f ), Vector3( 0.8f, 0.3f, 0.05f ), Vector3( 0.f, 0.f, 0.f ), &inRoot, Vector3( 0.1f, 2.f, 0.3f ) );
    }
    // Front of house: the mixing desk on its riser in the middle of the floor.
    m_kit.Box( Vector3( 0.f, 0.45f, kArenaDeskZ ), Vector3( 6.f, 0.9f, 4.f ), Vector3( 0.05f, 0.05f, 0.055f ), &inRoot );
    m_kit.Box( Vector3( 0.f, 1.35f, kArenaDeskZ + 0.6f ), Vector3( 4.2f, 0.9f, 1.f ), Vector3( 0.06f, 0.06f, 0.065f ), &inRoot );
    m_kit.Box( Vector3( 0.f, 1.81f, kArenaDeskZ + 0.6f ), Vector3( 4.f, 0.02f, 0.9f ), Vector3( 0.f, 0.f, 0.f ), &inRoot, Vector3( 0.15f, 0.35f, 0.5f ) );
    for( float x : { -1.2f, 1.2f } )
    {
        m_kit.Box( Vector3( x, 2.2f, kArenaDeskZ + 1.f ), Vector3( 0.9f, 0.55f, 0.04f ), Vector3( 0.f, 0.f, 0.f ), &inRoot, Vector3( 0.3f, 0.6f, 1.f ) );
    }
}


void VenueShow::FillHouse( Transform& inRoot, float inScale )
{
    // The back of the house: cheap figures everywhere the posed crowd doesn't reach, so no shot
    // finds an empty floor behind the front rows.
    const auto cap = [inScale]( int inCount ) { return static_cast<int>( static_cast<float>( inCount ) * inScale ); };
    switch( m_style )
    {
    case Style::Arena:
    {
        m_crowd.KeepClear( -3.6f, 3.6f, kArenaDeskZ - 2.6f, kArenaDeskZ + 2.6f );
        m_crowd.AddMob( m_kit, &inRoot, -14.8f, 14.8f, VenueLayout::kCrowdFrontZ, kArenaStandsZ + 0.6f, 0.f, 0.62f, 0.8f, cap( 900 ) );
        // Aisles up the stands.
        for( float x : { -14.f, -5.f, 5.f, 14.f } )
        {
            m_crowd.KeepClear( x - 0.5f, x + 0.5f, kArenaBackWallZ, kArenaStandsZ );
        }
        for( int tier = 0; tier < kArenaTiers; ++tier )
        {
            const float z0 = kArenaStandsZ - kArenaTierDepth * static_cast<float>( tier );
            m_crowd.AddMob( m_kit, &inRoot, -20.8f, 20.8f, z0 - 0.35f, z0 - kArenaTierDepth + 0.3f, kArenaTierRise * static_cast<float>( tier + 1 ), 0.66f, 0.72f - 0.06f * tier, cap( 140 ) );
        }
        for( float side : { -1.f, 1.f } )
        {
            for( int tier = 0; tier < kArenaSideTiers; ++tier )
            {
                const float inner = kArenaSideStandsX + kArenaTierDepth * static_cast<float>( tier ) + 0.35f;
                const float outer = inner + kArenaTierDepth - 0.65f;
                m_crowd.AddMob( m_kit, &inRoot, side < 0.f ? -outer : inner, side < 0.f ? -inner : outer, -3.5f, kArenaStandsZ + 0.3f, kArenaTierRise * static_cast<float>( tier + 1 ), 0.66f, 0.6f, cap( 80 ) );
            }
        }
        break;
    }
    case Style::Club:
        // Packed to the bar.
        m_crowd.AddMob( m_kit, &inRoot, -12.1f, 12.1f, VenueLayout::kCrowdFrontZ, -14.7f, 0.f, 0.56f, 0.85f, cap( 420 ) );
        break;
    case Style::Festival:
        // A field full to the delay towers, thinning out past them into the dark.
        m_crowd.KeepClear( -3.8f, 3.8f, -26.8f, -21.2f );
        for( float side : { -1.f, 1.f } )
        {
            for( float z : { -26.f, -40.f } )
            {
                m_crowd.KeepClear( side * 14.f - 0.7f, side * 14.f + 0.7f, z - 0.7f, z + 0.7f );
            }
        }
        m_crowd.AddMob( m_kit, &inRoot, -25.f, 25.f, VenueLayout::kCrowdFrontZ, -34.f, 0.f, 0.66f, 0.8f, cap( 900 ) );
        m_crowd.AddMob( m_kit, &inRoot, -28.f, 28.f, -34.f, -50.f, 0.f, 0.74f, 0.55f, cap( 450 ) );
        m_crowd.AddMob( m_kit, &inRoot, -30.f, 30.f, -50.f, -66.f, 0.f, 0.85f, 0.32f, cap( 250 ) );
        break;
    default:
        break;
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
    const auto started = std::chrono::steady_clock::now();
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
    // A crowd surfer on the chart's crowd-surf / stage-dive shots, and now and then when it's intense.
    const std::string& shot = m_director.CurrentShot();
    const bool surfShot = shot.find( "crowdsurf" ) != std::string::npos || shot.find( "stagedive" ) != std::string::npos;
    m_crowd.SetSurfing( surfShot || ( m_crowd.Mood( seconds ) == "intense" && std::fmod( seconds, 53.0 ) < 1.0 ) );
    m_crowd.Update( seconds, inDeltaTime, m_performance );
    m_band.Update( seconds, inDeltaTime, m_crowd.Size() > 0 ? m_crowd.Energy() : 0.6f );
    m_lyricBoard.Update( seconds );
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
        if( m_band.HasMember( member ) )
        {
            // An operator keeps the spot on them, not on every bob: eased, snapped when far off
            // (the first frame, a room swap).
            const Vector3 chest = m_band.ChestOf( member );
            Vector3& aim = m_spotAims[slot];
            aim = ( aim - chest ).Length() > 3.f ? chest : aim + ( chest - aim ) * ( 1.f - std::exp( -std::clamp( inDeltaTime, 0.f, 0.1f ) * 5.f ) );
            m_lights.SetSpotlightTarget( slot, aim );
        }
    }
    m_lights.Update( inSongTimeMs, inDeltaTime );
    UpdateSet( seconds, inDeltaTime );

    // --highway-log: what the venue costs on the main thread, every five seconds.
    static const bool kLog = CommandLine::Has( "--highway-log" );
    if( kLog )
    {
        m_updateMs += std::chrono::duration<double, std::milli>( std::chrono::steady_clock::now() - started ).count();
        if( ++m_updateFrames >= 300 )
        {
            BRUH_FMT( "Venue: update %.2f ms a frame (%s, crowd %d, shot %s, look %s)", m_updateMs / m_updateFrames, StyleName( m_style ), static_cast<int>( m_crowd.Size() ),
                m_director.CurrentShot().c_str(), m_director.CurrentLook().empty() ? "-" : m_director.CurrentLook().c_str() );
            m_updateMs = 0.0;
            m_updateFrames = 0;
        }
    }
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
