#include "CoreGame/StageLights.h"
#include "Components/Transform.h"
#include "Components/Lighting/Light.h"
#include "Components/Graphics/PostProcess.h"
#include "Config/GameSettings.h"
#include "Engine/World.h"
#include "Core/CommandLine.h"
#include "Venue/VenuePlan.h"
#include <algorithm>
#include <cmath>

namespace
{
    constexpr float kPi = 3.14159265f;

    // The rig, in venue space (Venue/VenuePlan.h: the stage's front edge at z 0, the crowd at
    // -z), placed for the procedural rooms' stage; its heights come from the plan. Light settings follow MitchGame's ConcertTest study: narrow, very bright cones in haze.
    // Beams: moving heads on the deck, rows 0-1 along the stage's front edge throwing up and back
    // over the band, rows 2-3 along the back throwing up and out over the crowd (the silhouette
    // lights).
    constexpr int kBeamRows = 4;
    constexpr float kBeamRowX[kBeamRows] = { 2.4f, 6.8f, 3.6f, 7.8f };
    constexpr float kBeamRowZ[kBeamRows] = { 0.45f, 0.45f, 9.7f, 9.7f };
    constexpr float kBeamIntensity = 20000.f;
    constexpr float kBeamInner = 4.f;
    constexpr float kBeamOuter = 8.f;
    constexpr float kBeamRange = 40.f;

    // Washes: on the truss over the stage, pooling colour on the band.
    constexpr int kWashRows = 3;
    constexpr float kWashRowZ[kWashRows] = { 1.6f, 4.6f, 7.6f };
    constexpr float kWashX = 4.6f;
    constexpr float kWashIntensity = 2100.f;

    // Movers: moving heads hung under the three cross trusses. The front truss's light the band
    // from the front or throw out over the crowd, the middle's drop columns around the band, the
    // back truss's fan forward over the band's heads into the audience (the look of a big show).
    constexpr int kMoverRows = 3;
    constexpr float kMoverRowZ[kMoverRows] = { 0.2f, 4.6f, 9.f };
    constexpr int kMoverCount[kMoverRows] = { 4, 4, 8 };
    constexpr float kMoverX[kMoverRows][8] = {
        { -5.6f, -1.9f, 1.9f, 5.6f, 0.f, 0.f, 0.f, 0.f },
        { -6.6f, -1.6f, 1.6f, 6.6f, 0.f, 0.f, 0.f, 0.f },
        { -8.4f, -6.f, -3.6f, -1.2f, 1.2f, 3.6f, 6.f, 8.4f },
    };
    constexpr float kMoverIntensity = 5500.f;
    constexpr float kMoverInner = 3.5f;
    constexpr float kMoverOuter = 7.5f;
    constexpr float kMoverRange = 46.f;

    // Side light: two wide cans on each wing's tower, cross-lighting the band so faces and
    // instruments have a lit edge whatever the washes are doing.
    constexpr float kSideX = 9.1f;
    constexpr float kSideIntensity = 1000.f;

    // Spotlights (VENUE notes 37-41: keys, vocals, guitar, drums, bass): narrow white follow spots
    // from the front-of-house truss onto each member.
    constexpr int kSpotCount = 5;
    constexpr int kSpotMember[kSpotCount] = { VenueData::Keys, VenueData::Vocals, VenueData::Guitar, VenueData::Drums, VenueData::Bass };
    constexpr float kSpotIntensity = 5500.f;

    // Crowd blinders: on the front truss, aimed out over the audience.
    constexpr int kCrowdLights = 4;
    constexpr float kCrowdX[kCrowdLights] = { -8.f, -3.5f, 3.5f, 8.f };
    constexpr float kCrowdIntensity = 2400.f;

    // Lasers: projectors on the back truss, each a fan of rays out over the crowd.
    constexpr int kLaserProjectors = 3;
    constexpr int kLaserRays = 7;
    constexpr float kLaserX[kLaserProjectors] = { -4.8f, 0.f, 4.8f };
    constexpr float kLaserLength = 58.f;
    constexpr float kLaserWidth = 0.03f;

    // Haze while the show runs: denser on "[FogOn]".
    constexpr float kHazeDensity = 0.016f;
    constexpr float kHazeDensityFogOn = 0.03f;
    constexpr float kHazeStart = 1.f;
    constexpr float kHazeScatter = 0.6f;
    // Samples each fixture takes along the part of a view ray inside its beam
    // (PostProcess::VolumetricLightSamples). Lighting every march step from its cluster instead
    // (0) visits about 46 lights a step to find the 4 that reach it: 24 ms of a 38 ms frame at
    // 5120 x 1440 on an RTX 4090 (RenderDoc), against 1.4 ms this way (4 samples 1.2 ms, 16
    // samples 2.0 ms). --haze-light-samples N overrides it for a run.
    constexpr int kHazeLightSamples = 8;

    constexpr float kKeyIntensity = 2.f;

    const Vector3 kWhite( 1.f, 0.96f, 0.9f );
    const Vector3 kHousing( 0.035f, 0.035f, 0.04f );
    const Vector3 kNoColor( 0.f, 0.f, 0.f );

    // A song's colours: three cool, three warm, two that clash. Rock Band's cues only say cool or
    // warm, so which blue and which red is ours to choose, and a different set per song keeps one
    // show from looking like the last.
    struct Palette
    {
        Vector3 Cool[3];
        Vector3 Warm[3];
        Vector3 Clash[2];
    };
    const Palette kPalettes[] = {
        // Classic rock: blues and violet against amber and red.
        { { Vector3( 0.15f, 0.35f, 1.f ), Vector3( 0.1f, 0.8f, 1.f ), Vector3( 0.5f, 0.2f, 1.f ) },
          { Vector3( 1.f, 0.5f, 0.12f ), Vector3( 1.f, 0.14f, 0.08f ), Vector3( 1.f, 0.2f, 0.55f ) },
          { Vector3( 0.3f, 1.f, 0.15f ), Vector3( 1.f, 0.1f, 0.8f ) } },
        // Neon: teal and electric blue against hot pink and orange.
        { { Vector3( 0.f, 1.f, 0.75f ), Vector3( 0.1f, 0.3f, 1.f ), Vector3( 0.7f, 0.1f, 1.f ) },
          { Vector3( 1.f, 0.08f, 0.5f ), Vector3( 1.f, 0.4f, 0.05f ), Vector3( 1.f, 0.8f, 0.1f ) },
          { Vector3( 0.6f, 1.f, 0.f ), Vector3( 1.f, 0.f, 0.6f ) } },
        // Ice and fire: pale blue and deep blue against red and tungsten.
        { { Vector3( 0.55f, 0.78f, 1.f ), Vector3( 0.04f, 0.14f, 1.f ), Vector3( 0.1f, 0.9f, 1.f ) },
          { Vector3( 1.f, 0.06f, 0.03f ), Vector3( 1.f, 0.36f, 0.05f ), Vector3( 1.f, 0.78f, 0.55f ) },
          { Vector3( 0.f, 0.9f, 1.f ), Vector3( 1.f, 0.f, 0.1f ) } },
        // Emerald: greens and teal against gold and magenta.
        { { Vector3( 0.1f, 1.f, 0.3f ), Vector3( 0.f, 0.75f, 0.8f ), Vector3( 0.1f, 0.3f, 1.f ) },
          { Vector3( 1.f, 0.68f, 0.1f ), Vector3( 1.f, 0.12f, 0.06f ), Vector3( 1.f, 0.1f, 0.7f ) },
          { Vector3( 0.1f, 0.4f, 1.f ), Vector3( 1.f, 0.5f, 0.f ) } },
        // Synthwave: purple, blue and pink against orange and gold.
        { { Vector3( 0.5f, 0.1f, 1.f ), Vector3( 0.1f, 0.2f, 1.f ), Vector3( 1.f, 0.2f, 0.8f ) },
          { Vector3( 1.f, 0.45f, 0.1f ), Vector3( 1.f, 0.1f, 0.35f ), Vector3( 1.f, 0.82f, 0.2f ) },
          { Vector3( 0.f, 1.f, 0.9f ), Vector3( 1.f, 0.1f, 0.9f ) } },
    };

    Vector3 Mix( const Vector3& inA, const Vector3& inB, float inT )
    {
        return inA * ( 1.f - inT ) + inB * inT;
    }


    // A beat-locked pulse: 1 on the beat, easing down to 0 over a beat.
    float Pulse( double inBeat )
    {
        const double fraction = inBeat - std::floor( inBeat );
        return static_cast<float>( std::pow( 1.0 - fraction, 2.0 ) );
    }


    // A repeatable pseudo-random value in [0, 1) for a fixture and step.
    float Noise( int inA, int inB )
    {
        uint32_t h = static_cast<uint32_t>( inA ) * 374761393u + static_cast<uint32_t>( inB ) * 668265263u;
        h = ( h ^ ( h >> 13 ) ) * 1274126177u;
        return static_cast<float>( ( h ^ ( h >> 16 ) ) & 0xFFFF ) / 65536.f;
    }


    bool StartsWith( const std::string& inText, const char* inPrefix )
    {
        return inText.rfind( inPrefix, 0 ) == 0;
    }


    bool IsMovingHead( int inKind, int inBeam, int inMover )
    {
        return inKind == inBeam || inKind == inMover;
    }
}


void StageLights::Build( World& inWorld, Transform* inParent, const EntityHandle& inCamera, const TrackData& inTrack, const VenuePlan& inPlan, const SpawnBoxFn& inSpawnBox, const TintFn& inTint )
{
    Clear();
    // --stage-lights N overrides the setting (0 off, 1 gentle, 2 full) for a run.
    const int setting = CommandLine::GetInt( "--stage-lights", GameSettings::GetInstance().StageLighting );
    if( setting <= 0 || !inParent )
    {
        return;
    }
    m_world = &inWorld;
    m_root = inParent;
    m_tint = inTint;
    m_gentle = setting == 1;
    m_camera = inCamera;
    m_venue = inTrack.m_venue;
    m_beats = inTrack.m_beats;
    m_bpm = inTrack.m_bpm > 30 ? static_cast<float>( inTrack.m_bpm ) : 120.f;
    if( !m_venue.HasLighting() )
    {
        BuildFallbackShow( inTrack );
    }
    // The song's colours, by its title (--stage-palette N to pick one).
    uint32_t hash = 2166136261u;
    for( char c : inTrack.m_trackName ) hash = ( hash ^ static_cast<uint8_t>( c ) ) * 16777619u;
    const int paletteCount = static_cast<int>( sizeof( kPalettes ) / sizeof( kPalettes[0] ) );
    const int chosen = CommandLine::GetInt( "--stage-palette", static_cast<int>( ( hash >> 8 ) % static_cast<uint32_t>( paletteCount ) ) );
    const Palette& palette = kPalettes[( ( chosen % paletteCount ) + paletteCount ) % paletteCount];
    for( int i = 0; i < 3; ++i )
    {
        m_cool[i] = palette.Cool[i];
        m_warm[i] = palette.Warm[i];
    }
    m_clash[0] = palette.Clash[0];
    m_clash[1] = palette.Clash[1];

    // Haze, so the beams show: the camera's fog turns volumetric and starts close.
    if( m_camera && m_camera->HasComponent<PostProcess>() )
    {
        PostProcess& post = m_camera->GetComponent<PostProcess>();
        m_savedFog = true;
        m_fogWasVolumetric = post.VolumetricFog;
        m_fogDensity = post.FogDensity;
        m_fogStart = post.FogStartDistance;
        m_fogScatter = post.FogSunIntensity;
        m_fogSteps = post.VolumetricSteps;
        m_fogDistance = post.VolumetricDistance;
        m_fogLightSamples = post.VolumetricLightSamples;
        post.Fog = true;
        post.VolumetricFog = true;
        post.VolumetricSteps = std::max( post.VolumetricSteps, 64 );
        post.VolumetricDistance = std::max( post.VolumetricDistance, 60.f );
        post.FogStartDistance = std::min( post.FogStartDistance, kHazeStart );
        post.FogSunIntensity = kHazeScatter;
        post.FogLocalAnisotropy = 0.2f;
        post.VolumetricLightSamples = CommandLine::GetInt( "--haze-light-samples", kHazeLightSamples );
        m_hazeLevel = 0.f;
    }
    m_bandCentre = inPlan.MemberCentre();
    for( int slot = 0; slot < kSpotCount; ++slot )
    {
        m_members[slot] = inPlan.HasMember( kSpotMember[slot] );
    }
    if( !inPlan.BuildRig )
    {
        // A scene venue lit by its own lights (AdoptFixture): the show without the rig.
        return;
    }

    const float deck = inPlan.Stage.Height;
    // The overhead rig hangs just under the truss (lower in a room with a low ceiling).
    const float truss = inPlan.Stage.TrussHeight - m_trussDrop;
    const float hang = truss - 0.55f;
    int index = 0;
    for( int row = 0; row < kBeamRows; ++row )
    {
        for( int side : { -1, 1 } )
        {
            const Vector3 base( static_cast<float>( side ) * kBeamRowX[row], deck, kBeamRowZ[row] );
            SpawnMovingHead( Group::Beam, side, row, index++, base + Vector3( 0.f, 0.42f, 0.f ), false, Vector3( 0.f, 1.f, row >= 2 ? -0.4f : 0.4f ), kBeamInner, kBeamOuter, kBeamRange, kBeamIntensity, inParent, inSpawnBox );
        }
    }
    index = 0;
    for( int row = 0; row < kWashRows; ++row )
    {
        for( int side : { -1, 1 } )
        {
            const Vector3 position( static_cast<float>( side ) * kWashX, truss - 0.3f, kWashRowZ[row] );
            const Vector3 target( static_cast<float>( side ) * ( kWashX - 2.f ), deck, kWashRowZ[row] + 0.4f );
            m_props.push_back( inSpawnBox( position + Vector3( 0.f, 0.2f, 0.f ), Vector3( 0.45f, 0.45f, 0.45f ), kHousing, kNoColor, inParent ) );
            const EntityHandle lens = inSpawnBox( position + Vector3( 0.f, -0.04f, 0.f ), Vector3( 0.36f, 0.04f, 0.36f ), kNoColor, kNoColor, inParent );
            SpawnFixture( Group::Wash, side, row, index++, position, target - position, 24.f, 40.f, 16.f, kWashIntensity, inParent, lens );
        }
    }
    index = 0;
    for( int row = 0; row < kMoverRows; ++row )
    {
        for( int column = 0; column < kMoverCount[row]; ++column )
        {
            const float x = kMoverX[row][column];
            const Vector3 pivot( x, hang, kMoverRowZ[row] );
            if( Fixture* mover = SpawnMovingHead( Group::Mover, x < 0.f ? -1 : 1, row, index++, pivot, true, Vector3( 0.f, -1.f, -0.6f ), kMoverInner, kMoverOuter, kMoverRange, kMoverIntensity, inParent, inSpawnBox ) )
            {
                mover->Column = column;
                mover->Spread = x / 8.4f;
            }
        }
    }
    index = 0;
    for( int side : { -1, 1 } )
    {
        for( int level = 0; level < 2; ++level )
        {
            const Vector3 position( static_cast<float>( side ) * kSideX, deck + 2.6f + 2.2f * static_cast<float>( level ), 2.2f + 2.6f * static_cast<float>( level ) );
            const Vector3 target( static_cast<float>( -side ) * 1.5f, deck + 1.3f, 3.f + 2.f * static_cast<float>( level ) );
            const Vector3 aim = ( target - position ).Normalized();
            m_props.push_back( inSpawnBox( position - aim * 0.12f, Vector3( 0.34f, 0.34f, 0.34f ), kHousing, kNoColor, inParent ) );
            const EntityHandle lens = inSpawnBox( position + aim * 0.07f, Vector3( 0.26f, 0.26f, 0.26f ), kNoColor, kNoColor, inParent );
            SpawnFixture( Group::Side, side, level, index++, position + aim * 0.25f, aim, 22.f, 38.f, 24.f, kSideIntensity, inParent, lens );
        }
    }
    for( int slot = 0; slot < kSpotCount; ++slot )
    {
        if( !inPlan.HasMember( kSpotMember[slot] ) )
        {
            continue;
        }
        const Vector3 target = inPlan.SpotOf( kSpotMember[slot] ).Feet + Vector3( 0.f, 1.f, 0.f );
        const Vector3 position( target.x * 0.4f, std::min( 11.f, truss + 1.5f ), -9.f );
        SpawnFixture( Group::Spot, target.x < 0.f ? -1 : 1, 0, slot, position, target - position, 3.5f, 6.f, 32.f, kSpotIntensity, inParent, {} );
    }
    for( int light = 0; light < kCrowdLights; ++light )
    {
        // An eight-lamp blinder: two rows of four tungsten faces in a frame, tipped down at the crowd.
        const Vector3 position( kCrowdX[light], truss - 0.4f, 0.f );
        const Vector3 target( kCrowdX[light] * 1.3f, 0.f, -11.f );
        m_props.push_back( inSpawnBox( position + Vector3( 0.f, 0.f, 0.12f ), Vector3( 0.96f, 0.5f, 0.18f ), kHousing, kNoColor, inParent ) );
        Fixture* blinder = SpawnFixture( Group::Crowd, kCrowdX[light] < 0.f ? -1 : 1, 0, light, position, target - position, 30.f, 50.f, 30.f, kCrowdIntensity, inParent, {} );
        if( blinder )
        {
            for( int lamp = 0; lamp < 8; ++lamp )
            {
                const Vector3 offset( -0.33f + 0.22f * static_cast<float>( lamp % 4 ), lamp < 4 ? 0.11f : -0.11f, 0.02f );
                blinder->Lenses.push_back( inSpawnBox( position + offset, Vector3( 0.17f, 0.17f, 0.04f ), kNoColor, kNoColor, inParent ) );
            }
        }
    }
    // Strobe bars: a white tube in a reflector, under the middle and back trusses.
    for( float z : { kMoverRowZ[1], kMoverRowZ[2] } )
    {
        for( float x : { -4.1f, 0.f, 4.1f } )
        {
            const Vector3 position( x, truss - 0.38f, z - 0.05f );
            m_props.push_back( inSpawnBox( position + Vector3( 0.f, 0.05f, 0.04f ), Vector3( 0.9f, 0.2f, 0.16f ), kHousing, kNoColor, inParent ) );
            m_strobes.push_back( inSpawnBox( position + Vector3( 0.f, 0.f, -0.05f ), Vector3( 0.8f, 0.1f, 0.03f ), kNoColor, kNoColor, inParent ) );
        }
    }
    // Laser projectors on the back truss; their rays stay scaled to nothing until the show calls
    // for them.
    for( int projector = 0; projector < kLaserProjectors; ++projector )
    {
        const Vector3 origin( kLaserX[projector], truss + 0.38f, kMoverRowZ[2] - 0.1f );
        m_props.push_back( inSpawnBox( origin + Vector3( 0.f, 0.f, 0.15f ), Vector3( 0.4f, 0.22f, 0.4f ), kHousing, kNoColor, inParent ) );
        for( int ray = 0; ray < kLaserRays; ++ray )
        {
            Laser laser;
            laser.Origin = origin;
            laser.Projector = projector;
            laser.Ray = ray;
            laser.Bar = inSpawnBox( origin, Vector3( 0.001f, 0.001f, 0.001f ), kNoColor, kNoColor, inParent );
            m_lasers.push_back( laser );
        }
    }

    // With no directional light the renderer supplies a daylight sun, which the haze would scatter
    // into a grey veil. A dim key light takes its place: enough to keep the highway's notes lit
    // (it lights every camera), too little to grey the venue.
    if( EntityHandle key = m_world->CreateEntity( "StageKeyLight" ) )
    {
        Transform& transform = key->AddComponent<Transform>( "StageKeyLight" );
        transform.SetParent( *inParent );
        transform.LookDirection( Vector3( 0.15f, -0.8f, 0.6f ).Normalized() );
        Light& light = key->AddComponent<Light>();
        light.LightType = Moonlight::LightType::Directional;
        light.DirectionalSource = Moonlight::DirectionalSource::Manual;
        light.Color = Vector3( 0.85f, 0.9f, 1.f );
        light.Intensity = kKeyIntensity;
        light.CastShadows = true;
        m_props.push_back( key );
    }

}


StageLights::Fixture* StageLights::SpawnFixture( Group inKind, int inSide, int inRow, int inIndex, const Vector3& inPosition, const Vector3& inAim, float inInner, float inOuter, float inRange, float inIntensity, Transform* inParent, const EntityHandle& inLens )
{
    Fixture fixture;
    fixture.Kind = inKind;
    fixture.Side = inSide;
    fixture.Row = inRow;
    fixture.Index = inIndex;
    fixture.MaxIntensity = inIntensity;

    Transform* parent = inParent;
    EntityHandle entity = m_world->CreateEntity( "StageLight" );
    if( !entity )
    {
        return nullptr;
    }
    Transform& transform = entity->AddComponent<Transform>( "StageLight" );
    if( parent )
    {
        transform.SetParent( *parent );
    }
    transform.SetPosition( inPosition );
    transform.LookDirection( inAim.Normalized() );
    Light& light = entity->AddComponent<Light>();
    light.LightType = Moonlight::LightType::Spot;
    light.Intensity = 0.f;
    light.Range = inRange;
    light.InnerConeAngle = inInner;
    light.OuterConeAngle = inOuter;
    // Four local shadow slots: the front and rear washes cover the stage.
    // Keep the middle wash row and decorative beams outside that budget.
    light.CastShadows = inKind == Group::Wash && ( inRow == 0 || inRow == kWashRows - 1 );
    fixture.Light = entity;
    if( inLens )
    {
        fixture.Lenses.push_back( inLens );
    }
    m_fixtures.push_back( fixture );
    return &m_fixtures.back();
}


StageLights::Fixture* StageLights::SpawnMovingHead( Group inKind, int inSide, int inRow, int inIndex, const Vector3& inPivot, bool inHung, const Vector3& inAim, float inInner, float inOuter, float inRange, float inIntensity, Transform* inParent, const SpawnBoxFn& inSpawnBox )
{
    // The base, on its mount: clamped under the truss, or sitting on the deck.
    const float toMount = inHung ? 0.36f : -0.34f;
    m_props.push_back( inSpawnBox( inPivot + Vector3( 0.f, toMount, 0.f ), Vector3( 0.4f, 0.16f, 0.4f ), kHousing, kNoColor, inParent ) );
    // The yoke: a fork from the base down (or up) either side of the head; it only pans.
    EntityHandle yoke = m_world->CreateEntity( "StageYoke" );
    if( yoke )
    {
        Transform& transform = yoke->AddComponent<Transform>( "StageYoke" );
        if( inParent ) transform.SetParent( *inParent );
        transform.SetPosition( inPivot );
        for( float arm : { -0.2f, 0.2f } )
        {
            m_props.push_back( inSpawnBox( Vector3( arm, toMount * 0.42f, 0.f ), Vector3( 0.05f, 0.36f, 0.14f ), kHousing, kNoColor, &transform ) );
        }
        m_props.push_back( yoke );
    }
    // The head carries the light, and tilts and pans with it: its body and lens are its children.
    Fixture* fixture = SpawnFixture( inKind, inSide, inRow, inIndex, inPivot, inAim, inInner, inOuter, inRange, inIntensity, inParent, {} );
    if( !fixture )
    {
        return nullptr;
    }
    fixture->Yoke = yoke;
    Transform& head = fixture->Light->GetComponent<Transform>();
    m_props.push_back( inSpawnBox( Vector3( 0.f, 0.f, -0.02f ), Vector3( 0.3f, 0.3f, 0.44f ), kHousing, kNoColor, &head ) );
    fixture->Lenses.push_back( inSpawnBox( Vector3( 0.f, 0.f, 0.205f ), Vector3( 0.23f, 0.23f, 0.03f ), kNoColor, kNoColor, &head ) );
    return fixture;
}


void StageLights::BuildFallbackShow( const TrackData& inTrack )
{
    // No VENUE lighting: cues from the song's sections, or alternate looks every eight measures.
    // Keyframed looks get a keyframe every two beats.
    auto& cues = m_venue.m_lighting;
    for( const TimedCueData& section : m_venue.m_sections )
    {
        const std::string& name = section.m_name;
        const auto has = [&name]( const char* inWord ) { return name.find( inWord ) != std::string::npos; };
        std::string cue = "loop_warm";
        if( has( "intro" ) ) cue = "manual_cool";
        else if( has( "pre" ) || has( "build" ) ) cue = "sweep";
        else if( has( "chorus" ) ) cue = "loop_warm";
        else if( has( "verse" ) ) cue = "loop_cool";
        else if( has( "solo" ) ) cue = "searchlights";
        else if( has( "bridge" ) || has( "break" ) ) cue = "harmony";
        else if( has( "outro" ) || has( "ending" ) ) cue = "silhouettes";
        else if( has( "riff" ) ) cue = "stomp";
        cues.push_back( TimedCueData{ section.m_time, cue } );
    }
    if( cues.empty() )
    {
        const float measure = 4.f * 60.f / m_bpm;
        const float length = std::max( inTrack.m_duration, 60.f );
        const char* looks[] = { "loop_cool", "loop_warm", "sweep", "loop_warm", "harmony", "stomp" };
        int step = 0;
        for( float time = 0.f; time < length; time += measure * 8.f )
        {
            cues.push_back( TimedCueData{ time, looks[step++ % 6] } );
        }
    }
    if( m_venue.m_keyframes.empty() )
    {
        const float beat = 60.f / m_bpm;
        const float length = std::max( inTrack.m_duration, cues.empty() ? 60.f : cues.back().m_time + 60.f );
        if( !m_beats.empty() )
        {
            for( size_t i = 0; i < m_beats.size(); i += 2 )
            {
                m_venue.m_keyframes.push_back( { m_beats[i].m_time, VenueData::Keyframe::Next } );
            }
        }
        else
        {
            for( float time = 0.f; time < length; time += beat * 2.f )
            {
                m_venue.m_keyframes.push_back( { time, VenueData::Keyframe::Next } );
            }
        }
    }
}


void StageLights::Clear()
{
    for( Fixture& fixture : m_fixtures )
    {
        if( fixture.Adopted )
        {
            // The scene's own light: it goes with the scene, as it was authored.
            if( fixture.Light && fixture.Light->HasComponent<Light>() )
            {
                Light& light = fixture.Light->GetComponent<Light>();
                light.Color = fixture.BaseColor;
                light.Intensity = fixture.BaseIntensity;
            }
            continue;
        }
        if( fixture.Light ) fixture.Light->MarkForDelete();
        for( EntityHandle& lens : fixture.Lenses )
        {
            if( lens ) lens->MarkForDelete();
        }
    }
    for( EntityHandle& prop : m_props )
    {
        if( prop ) prop->MarkForDelete();
    }
    for( EntityHandle& strobe : m_strobes )
    {
        if( strobe ) strobe->MarkForDelete();
    }
    for( Laser& laser : m_lasers )
    {
        if( laser.Bar ) laser.Bar->MarkForDelete();
    }
    m_fixtures.clear();
    m_props.clear();
    m_strobes.clear();
    m_lasers.clear();
    m_laserLevel = 0.f;
    m_root = nullptr;
    if( m_savedFog && m_camera && m_camera->HasComponent<PostProcess>() )
    {
        PostProcess& post = m_camera->GetComponent<PostProcess>();
        post.VolumetricFog = m_fogWasVolumetric;
        post.FogDensity = m_fogDensity;
        post.FogStartDistance = m_fogStart;
        post.FogSunIntensity = m_fogScatter;
        post.VolumetricSteps = m_fogSteps;
        post.VolumetricDistance = m_fogDistance;
        post.VolumetricLightSamples = m_fogLightSamples;
    }
    m_savedFog = false;
    m_camera = {};
    m_venue.Clear();
    m_beats.clear();
    m_kickPulse = m_snarePulse = m_crashFlash = m_missDip = 0.f;
    m_tomPulse = { 0.f, 0.f };
    m_spotFloor = {};
    m_spotTracked = {};
    m_hazeScale = 1.f;
    m_soloist = -1;
    m_hype = 0.f;
    m_accent = 0.f;
    m_burn = 0.f;
    m_adoptedSpots = 0;
    m_members = {};
}


StageLights::CueState StageLights::CueAt( double inSeconds, size_t inBefore ) const
{
    // The latest cue at or before inSeconds, skipping inBefore of them (1 = the one before that).
    CueState state;
    const auto& cues = m_venue.m_lighting;
    auto it = std::upper_bound( cues.begin(), cues.end(), inSeconds, []( double t, const TimedCueData& c ) { return t < c.m_time; } );
    size_t index = static_cast<size_t>( it - cues.begin() );
    if( index <= inBefore )
    {
        state.Name = "";
        state.Start = -1000.0;
        return state;
    }
    index -= 1 + inBefore;
    state.Name = cues[index].m_name;
    state.Start = cues[index].m_time;
    // Keyframes since the cue began step its pattern; "first" starts it over.
    for( const VenueData::KeyframeData& keyframe : m_venue.m_keyframes )
    {
        if( keyframe.m_time < state.Start - 0.001 )
        {
            continue;
        }
        if( keyframe.m_time > inSeconds )
        {
            break;
        }
        switch( keyframe.m_step )
        {
        case VenueData::Keyframe::Next: ++state.Keyframe; break;
        case VenueData::Keyframe::Previous: state.Keyframe = std::max( 0, state.Keyframe - 1 ); break;
        case VenueData::Keyframe::First: state.Keyframe = 0; break;
        }
    }
    return state;
}


void StageLights::BeatAt( double inSeconds, double& outBeat, int& outMeasureBeat ) const
{
    // Beats as a continuous count from the chart's tempo map (or its BPM), and the beat's place in
    // its measure.
    if( m_beats.size() >= 2 )
    {
        auto it = std::upper_bound( m_beats.begin(), m_beats.end(), static_cast<float>( inSeconds ), []( float t, const BeatData& b ) { return t < b.m_time; } );
        size_t index = it == m_beats.begin() ? 0 : static_cast<size_t>( it - m_beats.begin() ) - 1;
        index = std::min( index, m_beats.size() - 2 );
        const double span = std::max( 0.01, static_cast<double>( m_beats[index + 1].m_time - m_beats[index].m_time ) );
        outBeat = static_cast<double>( index ) + ( inSeconds - m_beats[index].m_time ) / span;
        outMeasureBeat = 0;
        for( size_t i = index; i > 0 && !m_beats[i].m_measure; --i )
        {
            ++outMeasureBeat;
        }
        return;
    }
    outBeat = inSeconds * m_bpm / 60.0;
    const long long whole = static_cast<long long>( std::floor( outBeat ) );
    outMeasureBeat = static_cast<int>( ( ( whole % 4 ) + 4 ) % 4 );
}


StageLights::Look StageLights::MoverLook( const Fixture& inFixture, const CueState& inCue, double inSeconds, double inBeat ) const
{
    // The overhead moving heads. Yaw is degrees round from pointing at the crowd (positive toward
    // the crowd's right, 180 upstage), Pitch degrees below horizontal (90 straight down).
    Look look;
    const std::string& cue = inCue.Name;
    const int key = inCue.Keyframe;
    const int beat = static_cast<int>( std::floor( inBeat ) );
    const int row = inFixture.Row;
    const int n = inFixture.Index;
    const int column = inFixture.Column;
    const float x = inFixture.Spread;
    const float t = static_cast<float>( inSeconds );
    const float wave = static_cast<float>( std::sin( inBeat * kPi * 0.5 - column * 0.7 ) );
    // The resting fan: the front truss lights the band, the middle drops columns that lean
    // outward, the back fans over the band's heads into the crowd.
    const auto fan = [&look, row, x]( float inBackPitch ) {
        if( row == 0 )
        {
            look.Yaw = 180.f - x * 22.f;
            look.Pitch = 56.f;
        }
        else if( row == 1 )
        {
            look.Yaw = x * 80.f;
            look.Pitch = 74.f;
        }
        else
        {
            look.Yaw = x * 40.f;
            look.Pitch = inBackPitch;
        }
    };
    fan( 27.f );

    if( cue == "manual_cool" || cue == "manual_warm" || cue == "verse" || cue == "chorus" || cue.empty() )
    {
        const bool warm = cue == "manual_warm" || cue == "chorus";
        const Vector3* palette = warm ? m_warm : m_cool;
        look.Color = palette[( n + key ) % 3];
        look.Level = cue == "chorus" ? 1.f : 0.8f;
        fan( 25.f + 7.f * static_cast<float>( ( key + column ) % 2 ) );
        if( cue == "chorus" && row == 2 )
        {
            // The back row nods with the beat.
            look.Pitch = 24.f + 12.f * Pulse( inBeat );
        }
        if( cue.empty() )
        {
            look.Color = Mix( m_warm[0], m_cool[0], 0.5f + 0.5f * std::sin( t * 0.3f + n ) );
            look.Level = 0.6f;
            look.Yaw += 8.f * std::sin( t * 0.25f + column );
        }
    }
    else if( cue == "dischord" )
    {
        look.Color = m_clash[( n + key ) % 2];
        look.Level = 0.6f + 0.4f * Noise( n, key );
        look.Yaw = ( Noise( n + 7, key ) - 0.5f ) * 120.f;
        look.Pitch = 25.f + 55.f * Noise( n + 3, key );
    }
    else if( cue == "stomp" )
    {
        look.Color = m_warm[0];
        look.Level = key % 2 == 0 ? 1.f : 0.f;
        fan( 40.f );
    }
    else if( cue == "loop_cool" || cue == "loop_warm" )
    {
        // A wave along each truss: the heads light and tip one after another, a head a half beat.
        const Vector3* palette = cue == "loop_warm" ? m_warm : m_cool;
        const float chase = std::max( 0.f, static_cast<float>( std::sin( inBeat * kPi - column * 0.8 ) ) );
        look.Color = palette[( beat / 4 + row ) % 3];
        look.Level = 0.3f + 0.7f * chase * chase;
        if( row == 0 )
        {
            // The front truss turns out over the crowd and sweeps them.
            look.Yaw = x * 35.f + 14.f * wave;
            look.Pitch = 30.f + 9.f * wave;
        }
        else if( row == 1 )
        {
            look.Yaw = x * 80.f;
            look.Pitch = 70.f + 10.f * wave;
        }
        else
        {
            look.Yaw = x * 42.f;
            look.Pitch = 31.f + 11.f * wave;
        }
    }
    else if( cue == "harmony" )
    {
        // Warm from one side, cool from the other, crossing over the stage; the sides trade each measure.
        const int measure = beat / 4;
        const bool warmSide = ( inFixture.Side > 0 ) == ( measure % 2 == 0 );
        look.Color = warmSide ? m_warm[0] : m_cool[1];
        look.Level = 0.85f;
        if( row == 0 ) { look.Yaw = 180.f + x * 30.f; look.Pitch = 52.f; }
        else if( row == 1 ) { look.Yaw = -x * 70.f; look.Pitch = 62.f; }
        else { look.Yaw = -x * 46.f; look.Pitch = 34.f; }
    }
    else if( cue == "frenzy" || cue == "bre" )
    {
        // A ballyhoo: every head somewhere new each half beat.
        const int step = static_cast<int>( std::floor( inBeat * 2.0 ) );
        const Vector3 colors[] = { m_warm[0], m_warm[1], m_cool[0], m_cool[1], m_clash[1], kWhite };
        look.Color = colors[static_cast<int>( Noise( n + 20, step ) * 6.f ) % 6];
        look.Level = m_gentle ? 0.6f : 0.3f + 0.45f * Noise( n + 31, step );
        look.Yaw = ( Noise( n + 25, step ) - 0.5f ) * 150.f;
        // Never level: a beam thrown flat down the room goes through the cameras over the crowd.
        look.Pitch = 32.f + 48.f * Noise( n + 29, step );
    }
    else if( cue == "silhouettes" || cue == "silhouettes_spot" )
    {
        // The back truss alone, steep onto the band's backs: rim light and shapes in the haze.
        look.Color = Mix( m_cool[0], kWhite, 0.6f );
        look.Level = row == 2 ? 1.f : 0.f;
        look.Yaw = x * 18.f;
        look.Pitch = 50.f;
    }
    else if( cue == "searchlights" )
    {
        look.Color = Mix( kWhite, m_cool[1], 0.25f );
        look.Level = 0.95f;
        look.Yaw = x * 20.f + 55.f * std::sin( t * 0.7f + n * 1.3f );
        look.Pitch = ( row == 1 ? 55.f : 34.f ) + 18.f * std::sin( t * 0.5f + n * 0.9f );
    }
    else if( cue == "sweep" )
    {
        // Every head pans together across a measure, alternating colour by side.
        const double measure = inBeat / 4.0;
        look.Color = inFixture.Side > 0 ? m_warm[2] : m_cool[2];
        look.Level = 0.95f;
        look.Yaw = 50.f * static_cast<float>( std::sin( measure * 2.0 * kPi ) ) + x * 14.f;
        look.Pitch = row == 1 ? 60.f : 36.f;
    }
    else if( StartsWith( cue, "strobe" ) )
    {
        look.Color = kWhite;
        if( m_gentle )
        {
            look.Level = 0.6f;
        }
        else
        {
            const double rate = cue == "strobe_fast" ? 4.0 : 2.0;
            const double phase = inBeat * rate - std::floor( inBeat * rate );
            look.Level = phase < 0.3 ? 1.f : 0.f;
        }
        fan( 34.f );
        if( row == 0 ) { look.Yaw = x * 30.f; look.Pitch = 28.f; }
    }
    else if( StartsWith( cue, "blackout" ) )
    {
        look.Level = 0.f;
        look.Color = m_cool[0];
    }
    else
    {
        look.Color = m_warm[n % 3];
        look.Level = 0.65f;
    }

    // The heads pointed down at the deck light it from close by: they run lower than the ones
    // throwing out through the air, or the stage floor outshines the band.
    if( look.Pitch > 48.f )
    {
        look.Level *= 0.6f;
    }

    // A soloist takes the front truss: its heads swing onto them, pale against the colour behind.
    if( m_soloist >= 0 && m_soloist < 5 && m_spotTracked[m_soloist] && row == 0 && inFixture.Light && !StartsWith( cue, "blackout" ) )
    {
        const Vector3 aim = m_spotTargets[m_soloist] - inFixture.Light->GetComponent<Transform>().GetPosition();
        const float flat = std::sqrt( aim.x * aim.x + aim.z * aim.z );
        if( flat > 0.01f )
        {
            look.Yaw = std::atan2( aim.x, -aim.z ) * 180.f / kPi;
            look.Pitch = std::atan2( -aim.y, flat ) * 180.f / kPi;
            // (Four heads and a follow spot on one player: each well down, or they burn out.)
            look.Color = Mix( look.Color, kWhite, 0.6f );
            look.Level = 0.28f;
        }
    }
    return look;
}


StageLights::Look StageLights::LookFor( const Fixture& inFixture, const CueState& inCue, double inSeconds, double inBeat ) const
{
    // One look per Rock Band cue, in the spirit of its name (Docs/Stage-Lighting.md): what each
    // fixture shows given the cue, its keyframe step and the beat.
    Look look;
    const std::string& cue = inCue.Name;
    const int key = inCue.Keyframe;
    const int beat = static_cast<int>( std::floor( inBeat ) );
    const float side = static_cast<float>( inFixture.Side );
    const bool beam = inFixture.Kind == Group::Beam;
    const bool wash = inFixture.Kind == Group::Wash;
    const int n = inFixture.Index;
    const float t = static_cast<float>( inSeconds );
    look.Yaw = side * 18.f;
    look.Pitch = 62.f;

    if( StartsWith( cue, "flare" ) )
    {
        // A white flash fading back to the look before it.
        Look base = LookFor( inFixture, CueAt( inCue.Start - 0.001, 0 ), inSeconds, inBeat );
        if( inFixture.Kind == Group::Spot )
        {
            return base;
        }
        const float fade = cue == "flare_fast" ? 0.35f : 1.2f;
        const float flash = std::exp( -static_cast<float>( inSeconds - inCue.Start ) / fade ) * ( m_gentle ? 0.3f : 1.f );
        base.Color = Mix( base.Color, kWhite, flash );
        base.Level = std::min( 1.f, base.Level + flash );
        return base;
    }
    if( inFixture.Kind == Group::Spot )
    {
        look.Color = kWhite;
        look.Level = 0.f;
        return look;
    }
    if( inFixture.Kind == Group::Crowd )
    {
        // Blinders: a low warm glow on the crowd that swells with them, white flashes on strobes,
        // dark in a blackout.
        look.Color = Mix( m_warm[0], kWhite, 0.5f );
        look.Level = 0.06f + 0.22f * m_crowdEnergy;
        if( StartsWith( cue, "blackout" ) ) look.Level = 0.f;
        else if( StartsWith( cue, "strobe" ) && !m_gentle ) look.Level = ( inBeat * 2.0 - std::floor( inBeat * 2.0 ) ) < 0.2 ? 0.9f : 0.05f;
        return look;
    }
    if( inFixture.Kind == Group::Mover )
    {
        return MoverLook( inFixture, inCue, inSeconds, inBeat );
    }
    if( inFixture.Kind == Group::Side )
    {
        // Cross light in the colour the washes aren't: cool from the wings under a warm look and
        // warm under a cool one, so the band never goes flat. Gone when the stage should be dark.
        const bool warmCue = cue == "manual_warm" || cue == "chorus" || cue == "loop_warm" || cue == "stomp";
        look.Color = Mix( warmCue ? m_cool[( key + n ) % 3] : m_warm[( key + n ) % 3], kWhite, 0.35f );
        look.Level = 0.55f;
        if( StartsWith( cue, "blackout" ) || StartsWith( cue, "silhouettes" ) ) look.Level = 0.f;
        else if( StartsWith( cue, "strobe" ) ) look.Level = 0.15f;
        else if( cue == "frenzy" || cue == "bre" ) look.Level = 0.8f;
        else if( cue == "harmony" ) look.Color = Mix( inFixture.Side > 0 ? m_warm[0] : m_cool[1], kWhite, 0.3f );
        return look;
    }

    if( cue == "manual_cool" || cue == "manual_warm" || cue == "verse" || cue == "chorus" || cue.empty() )
    {
        const bool warm = cue == "manual_warm" || cue == "chorus";
        const Vector3* palette = warm ? m_warm : m_cool;
        look.Color = palette[( n + key ) % 3];
        look.Level = cue == "chorus" ? 1.f : 0.75f;
        look.Pitch = 58.f + 8.f * static_cast<float>( ( key + inFixture.Row ) % 2 );
        if( cue.empty() )
        {
            look.Color = Mix( m_warm[0], m_cool[0], 0.5f + 0.5f * std::sin( t * 0.3f + n ) );
            look.Level = 0.55f;
        }
    }
    else if( cue == "dischord" )
    {
        look.Color = m_clash[( n + key ) % 2];
        look.Level = 0.6f + 0.4f * Noise( n, key );
        look.Yaw = side * ( 10.f + 30.f * Noise( n + 7, key ) );
        look.Pitch = 50.f + 25.f * Noise( n + 3, key );
    }
    else if( cue == "stomp" )
    {
        look.Color = m_warm[0];
        look.Level = key % 2 == 0 ? 1.f : 0.f;
    }
    else if( cue == "loop_cool" || cue == "loop_warm" )
    {
        // A chase down the rows, a row a beat, on a slow sway.
        const Vector3* palette = cue == "loop_warm" ? m_warm : m_cool;
        const int rows = wash ? kWashRows : kBeamRows;
        const bool lit = ( beat % rows ) == inFixture.Row;
        look.Color = palette[( beat / rows + ( inFixture.Side > 0 ? 1 : 0 ) ) % 3];
        look.Level = 0.35f + 0.65f * ( lit ? Pulse( inBeat ) : 0.f );
        look.Yaw = side * ( 18.f + 12.f * std::sin( t * 0.8f + inFixture.Row ) );
    }
    else if( cue == "harmony" )
    {
        const int measure = beat / 4;
        const bool warmSide = ( inFixture.Side > 0 ) == ( measure % 2 == 0 );
        look.Color = warmSide ? m_warm[0] : m_cool[1];
        look.Level = 0.8f;
        look.Yaw = -side * 14.f;   // beams cross over the highway
        look.Pitch = 55.f;
    }
    else if( cue == "frenzy" || cue == "bre" )
    {
        const int step = static_cast<int>( std::floor( inBeat * 2.0 ) );
        const Vector3 colors[] = { m_warm[0], m_warm[1], m_cool[0], m_cool[1], m_clash[1], kWhite };
        look.Color = colors[static_cast<int>( Noise( n, step ) * 6.f ) % 6];
        look.Level = m_gentle ? 0.7f : 0.35f + 0.5f * Noise( n + 11, step );
        look.Yaw = side * 40.f * ( Noise( n + 5, step ) - 0.3f );
        look.Pitch = 45.f + 30.f * Noise( n + 9, step );
    }
    else if( cue == "silhouettes" || cue == "silhouettes_spot" )
    {
        // Backlight only: the far rows bright and pale, the rest dark.
        const bool back = beam ? inFixture.Row >= kBeamRows - 1 : inFixture.Row >= kWashRows - 1;
        look.Color = Mix( m_cool[0], kWhite, 0.6f );
        look.Level = back ? 1.f : 0.f;
        look.Pitch = 70.f;
        look.Yaw = -side * 8.f;
    }
    else if( cue == "searchlights" )
    {
        look.Color = Mix( kWhite, m_cool[1], 0.25f );
        look.Level = wash ? 0.1f : 0.9f;
        look.Yaw = side * 10.f + 45.f * std::sin( t * 0.9f + n * 1.7f );
        look.Pitch = 50.f + 15.f * std::sin( t * 0.6f + n );
    }
    else if( cue == "sweep" )
    {
        // Every beam sweeps together across a measure, alternating colour by side.
        const double measure = inBeat / 4.0;
        look.Color = inFixture.Side > 0 ? m_warm[2] : m_cool[2];
        look.Level = wash ? 0.4f : 0.95f;
        look.Yaw = 40.f * static_cast<float>( std::sin( measure * 2.0 * kPi ) );
        look.Pitch = 55.f;
    }
    else if( StartsWith( cue, "strobe" ) )
    {
        look.Color = kWhite;
        if( m_gentle )
        {
            look.Level = 0.6f;
        }
        else
        {
            const double rate = cue == "strobe_fast" ? 4.0 : 2.0;   // flashes per beat
            const double phase = inBeat * rate - std::floor( inBeat * rate );
            look.Level = phase < 0.3 ? 1.f : 0.f;
        }
        look.Pitch = 65.f;
    }
    else if( StartsWith( cue, "blackout" ) )
    {
        look.Level = 0.f;
        look.Color = m_cool[0];
    }
    else
    {
        look.Color = m_warm[n % 3];
        look.Level = 0.6f;
    }
    return look;
}


float StageLights::EaseRate( const std::string& inCue ) const
{
    // How fast fixtures move to their look, per second: hard cuts for strobes and stomps.
    if( StartsWith( inCue, "strobe" ) || inCue == "stomp" || inCue == "frenzy" || inCue == "bre" || inCue == "dischord" ) return m_gentle ? 6.f : 60.f;
    if( inCue == "blackout_fast" ) return 14.f;
    if( inCue == "blackout_slow" ) return 1.5f;
    if( inCue == "searchlights" || inCue == "sweep" ) return 30.f;
    return 6.f;
}


void StageLights::SetFog( double inSeconds, float inDeltaTime )
{
    if( !m_savedFog || !m_camera || !m_camera->HasComponent<PostProcess>() )
    {
        return;
    }
    bool fogOn = false;
    for( const VenueData::FogData& change : m_venue.m_fog )
    {
        if( change.m_time > inSeconds )
        {
            break;
        }
        fogOn = change.m_on;
    }
    const float target = fogOn ? 1.f : 0.f;
    m_hazeLevel += ( target - m_hazeLevel ) * std::min( 1.f, inDeltaTime * 0.8f );
    m_camera->GetComponent<PostProcess>().FogDensity = ( kHazeDensity + ( kHazeDensityFogOn - kHazeDensity ) * m_hazeLevel ) * m_hazeScale;
}


void StageLights::Accent( float inStrength )
{
    m_accent = std::max( m_accent, std::clamp( inStrength, 0.f, 1.f ) * ( m_gentle ? 0.35f : 1.f ) );
}


Vector3 StageLights::AimOf( const Fixture& inFixture )
{
    const float yaw = inFixture.Yaw * kPi / 180.f;
    const float pitch = std::clamp( inFixture.Pitch, -86.f, 86.f ) * kPi / 180.f;
    if( inFixture.Kind == Group::Mover )
    {
        // Hung: yaw round from the crowd, pitch below horizontal.
        return Vector3( std::sin( yaw ) * std::cos( pitch ), -std::sin( pitch ), -std::cos( yaw ) * std::cos( pitch ) );
    }
    // On the deck: front rows throw back over the band, back rows out over the crowd.
    const float away = inFixture.Row >= 2 ? -1.f : 1.f;
    return Vector3( std::sin( yaw ) * std::cos( pitch ), std::sin( pitch ), away * std::cos( yaw ) * std::cos( pitch ) );
}


void StageLights::UpdateLasers( const CueState& inCue, double inSeconds, double inBeat, float inDeltaTime )
{
    if( m_lasers.empty() )
    {
        return;
    }
    // Lasers are for the big moments: the wild cues, and whenever the show's hype peaks.
    const std::string& cue = inCue.Name;
    const bool wild = cue == "frenzy" || cue == "bre" || cue == "searchlights" || cue == "sweep" || cue == "dischord";
    const bool dark = StartsWith( cue, "blackout" ) || StartsWith( cue, "silhouettes" );
    const float target = dark ? 0.f : ( wild || m_hype > 0.72f ) ? 1.f : 0.f;
    m_laserLevel += ( target - m_laserLevel ) * ( 1.f - std::exp( -inDeltaTime * 5.f ) );
    const float t = static_cast<float>( inSeconds );
    const int measure = static_cast<int>( std::floor( inBeat / 4.0 ) );
    for( Laser& laser : m_lasers )
    {
        if( !laser.Bar )
        {
            continue;
        }
        Transform& bar = laser.Bar->GetComponent<Transform>();
        if( m_laserLevel < 0.02f )
        {
            bar.SetScale( Vector3( 0.f, 0.f, 0.f ) );
            continue;
        }
        // Each projector's fan opens and closes over two measures and tips with the beat; the
        // outer projectors lean outward.
        const float centre = static_cast<float>( laser.Ray ) - static_cast<float>( kLaserRays - 1 ) * 0.5f;
        const float open = 5.f + 9.f * ( 0.5f + 0.5f * static_cast<float>( std::sin( inBeat * kPi / 4.0 + laser.Projector * 2.1 ) ) );
        const float yaw = ( static_cast<float>( laser.Projector - 1 ) * 22.f + centre * open + 10.f * std::sin( t * 0.4f + laser.Projector ) ) * kPi / 180.f;
        // Thrown high, over the cameras that fly above the crowd, to land up the back wall.
        const float pitch = ( 1.f + 4.f * static_cast<float>( std::sin( inBeat * kPi / 2.0 + laser.Projector ) ) + std::abs( centre ) * 0.6f ) * kPi / 180.f;
        const Vector3 direction( std::sin( yaw ) * std::cos( pitch ), -std::sin( pitch ), -std::cos( yaw ) * std::cos( pitch ) );
        bar.SetPosition( laser.Origin + direction * ( kLaserLength * 0.5f ) );
        bar.LookDirection( direction );
        // The engine's cube spans [-1, 1]: half sizes.
        bar.SetScale( Vector3( kLaserWidth * 0.5f, kLaserWidth * 0.5f, kLaserLength * 0.5f ) );
        if( m_tint )
        {
            // Green is the classic; the song's clashing pair takes over measure by measure.
            const Vector3 color = ( measure + laser.Projector ) % 3 == 0 ? m_clash[1] : ( measure + laser.Projector ) % 3 == 1 ? Vector3( 0.1f, 1.f, 0.25f ) : m_clash[0];
            m_tint( laser.Bar, kNoColor, color * ( 3.2f * m_laserLevel ) );
        }
    }
}


void StageLights::Update( double inSongTimeMs, float inDeltaTime )
{
    if( m_fixtures.empty() )
    {
        return;
    }
    const double seconds = inSongTimeMs / 1000.0;
    CueState cue = CueAt( seconds, 0 );
    // --stage-cue <name> holds one look for the whole song, to tune it ("default" for the empty cue).
    static const std::string forcedCue = CommandLine::GetString( "--stage-cue", "" );
    if( !forcedCue.empty() )
    {
        cue.Name = forcedCue == "default" ? "" : forcedCue;
    }
    double beat = 0.0;
    int measureBeat = 0;
    BeatAt( seconds, beat, measureBeat );
    SetFog( seconds, inDeltaTime );

    // Crowd energy scales the whole show a little, and so does the hype.
    float energy = 0.9f;
    for( const TimedCueData& crowd : m_venue.m_crowd )
    {
        if( crowd.m_time > seconds ) break;
        energy = crowd.m_name == "intense" ? 1.f : crowd.m_name == "mellow" ? 0.7f : 0.9f;
    }
    energy *= 0.92f + 0.16f * m_hype;
    // Pyro: a burst of hot white and orange, from the chart's bonus effects or the flame pots.
    float bonus = 0.f;
    for( float time : m_venue.m_bonusFx )
    {
        if( time > seconds ) break;
        bonus = std::max( bonus, std::exp( -static_cast<float>( seconds - time ) / 0.6f ) );
    }
    if( m_gentle ) bonus *= 0.35f;
    bonus = std::max( bonus, m_burn );

    const float decay = std::exp( -inDeltaTime * 7.f );
    m_kickPulse *= decay;
    m_snarePulse *= decay;
    m_crashFlash *= std::exp( -inDeltaTime * 5.f );
    m_tomPulse[0] *= decay;
    m_tomPulse[1] *= decay;
    m_missDip *= std::exp( -inDeltaTime * 4.f );
    m_accent *= std::exp( -inDeltaTime * 4.5f );

    const float ease = 1.f - std::exp( -inDeltaTime * EaseRate( cue.Name ) );
    // Moving heads have motors: they swing to a new aim rather than jump (quicker when the show's
    // hot, and in the cues that are all movement).
    const bool quick = cue.Name == "frenzy" || cue.Name == "bre" || cue.Name == "searchlights" || cue.Name == "sweep";
    const float swing = 1.f - std::exp( -inDeltaTime * ( quick ? 14.f : 4.5f + 3.f * m_hype ) );
    // Strobe bars: with the strobe cues, and a burst of flashes on an accent.
    float strobe = 0.f;
    if( !m_gentle )
    {
        if( StartsWith( cue.Name, "strobe" ) )
        {
            const double rate = cue.Name == "strobe_fast" ? 4.0 : 2.0;
            strobe = ( beat * rate - std::floor( beat * rate ) ) < 0.3 ? 1.f : 0.f;
        }
        if( m_accent > 0.25f )
        {
            strobe = std::max( strobe, std::fmod( static_cast<float>( seconds ) * 14.f, 1.f ) < 0.4f ? m_accent : 0.f );
        }
    }
    const bool blackout = StartsWith( cue.Name, "blackout" );
    for( Fixture& fixture : m_fixtures )
    {
        Look look = LookFor( fixture, cue, seconds, beat );
        if( fixture.Kind == Group::Strobe )
        {
            // A scene's strobe (a patrol car's light bar): flashing with the strobe cues and on
            // big moments, the groups taking turns, and at the show's peak a slow alternation.
            const float turn = 0.5f * static_cast<float>( fixture.Index % 2 );
            float flash = 0.f;
            if( StartsWith( cue.Name, "strobe" ) )
            {
                const double rate = cue.Name == "strobe_fast" ? 4.0 : 2.0;
                flash = m_gentle ? 0.4f : ( std::fmod( static_cast<float>( beat * rate ) + turn, 1.f ) < 0.3f ? 1.f : 0.f );
            }
            if( m_accent > 0.25f && !m_gentle )
            {
                flash = std::max( flash, std::fmod( static_cast<float>( seconds ) * 7.f + turn, 1.f ) < 0.4f ? m_accent : 0.f );
            }
            if( m_hype > 0.72f && !blackout )
            {
                flash = std::max( flash, std::fmod( static_cast<float>( seconds ) * 1.5f + turn, 1.f ) < 0.5f ? ( m_gentle ? 0.3f : 0.7f ) : 0.f );
            }
            fixture.Level = flash;
            UpdateAdopted( fixture, fixture.BaseColor, flash );
            continue;
        }
        if( fixture.Kind == Group::Spot )
        {
            for( const VenueData::SpotlightData& spot : m_venue.m_spotlights )
            {
                if( spot.m_slot == fixture.Index && seconds >= spot.m_start && seconds < spot.m_end )
                {
                    look.Level = 1.f;
                }
            }
            // The front-light floor (VenueShow), mostly gone in a blackout.
            const float floor = m_spotFloor[std::clamp( fixture.Index, 0, 4 )];
            look.Level = std::max( look.Level, blackout ? floor * 0.15f : floor );
            if( cue.Name == "silhouettes_spot" || cue.Name == "blackout_spot" )
            {
                look.Level = std::max( look.Level, fixture.Index < 2 ? 1.f : 0.f );
            }
            if( fixture.Adopted && !blackout )
            {
                // A scene's searchlight is part of the set: always on its member.
                look.Level = std::max( look.Level, 0.35f );
            }
        }
        const bool head = fixture.Kind == Group::Beam || fixture.Kind == Group::Mover;
        fixture.Color = Mix( fixture.Color, look.Color, ease );
        fixture.Level += ( look.Level - fixture.Level ) * ease;
        fixture.Yaw += ( look.Yaw - fixture.Yaw ) * ( head ? swing : ease );
        fixture.Pitch += ( look.Pitch - fixture.Pitch ) * ( head ? swing : ease );

        // The player's hits on top: kicks swell the washes, snares and toms punch the beams,
        // cymbals flash them white. A miss dims everything for a moment.
        Vector3 color = fixture.Color;
        float level = fixture.Level * energy;
        switch( fixture.Kind )
        {
        case Group::Wash:
            level += 0.45f * m_kickPulse;
            color = Mix( color, Vector3( 1.f, 0.45f, 0.1f ), bonus );
            level += bonus;
            break;
        case Group::Side:
            level += 0.25f * m_kickPulse + 0.5f * bonus;
            color = Mix( color, Vector3( 1.f, 0.5f, 0.15f ), bonus );
            break;
        case Group::Crowd:
            // A big moment lights the whole house.
            level += 0.6f * bonus + 1.1f * m_accent;
            color = Mix( color, kWhite, std::min( 1.f, m_accent ) );
            break;
        case Group::Beam:
        case Group::Mover:
        {
            const float punch = fixture.Kind == Group::Beam ? 1.f : 0.7f;
            level += punch * ( 0.35f * m_snarePulse + 0.5f * m_tomPulse[fixture.Side > 0 ? 1 : 0] );
            const float flash = std::max( { m_crashFlash * ( m_gentle ? 0.3f : 0.7f ) * punch, bonus, blackout ? 0.f : m_accent * 0.8f } );
            color = Mix( color, kWhite, std::min( 1.f, flash ) );
            level += flash;
            break;
        }
        default:
            break;
        }
        level *= 1.f - 0.5f * m_missDip;
        level = std::clamp( level, 0.f, 1.5f );
        if( head )
        {
            // White is three colours' worth of light: a white beam in haze whites the picture
            // out where a saturated one glows, so beams dim as they pale.
            const float most = std::max( { color.x, color.y, color.z, 0.001f } );
            const float least = std::min( { color.x, color.y, color.z } );
            level *= 1.f - 0.55f * ( least / most );
        }

        if( fixture.Adopted )
        {
            UpdateAdopted( fixture, color, level );
            continue;
        }
        if( fixture.Light )
        {
            Transform& transform = fixture.Light->GetComponent<Transform>();
            if( head )
            {
                const Vector3 aim = AimOf( fixture );
                transform.LookDirection( aim );
                if( fixture.Yoke )
                {
                    const Vector3 flat( aim.x, 0.f, aim.z );
                    if( flat.Length() > 0.02f ) fixture.Yoke->GetComponent<Transform>().LookDirection( flat.Normalized() );
                }
            }
            else if( fixture.Kind == Group::Spot && m_spotTracked[std::clamp( fixture.Index, 0, 4 )] )
            {
                // A follow spot follows: onto the member wherever they've wandered.
                const Vector3 aim = m_spotTargets[std::clamp( fixture.Index, 0, 4 )] - transform.GetPosition();
                if( aim.Length() > 0.1f ) transform.LookDirection( aim.Normalized() );
            }
            Light& light = fixture.Light->GetComponent<Light>();
            light.Color = color;
            light.Intensity = fixture.MaxIntensity * level;
        }
        if( m_tint )
        {
            // The lamp's face: a moving head's glares (it's what the bloom catches), a blinder's
            // glows tungsten even at a low level.
            const float glare = head ? 9.f : fixture.Kind == Group::Crowd ? 5.f : 2.5f;
            for( const EntityHandle& lens : fixture.Lenses )
            {
                m_tint( lens, color * 0.2f, color * ( glare * level ) );
            }
        }
    }

    if( m_tint )
    {
        for( const EntityHandle& bar : m_strobes )
        {
            m_tint( bar, Vector3( 0.1f, 0.1f, 0.1f ), kWhite * ( 30.f * strobe ) );
        }
    }
    UpdateLasers( cue, seconds, beat, inDeltaTime );
}


void StageLights::AdoptFixture( const EntityHandle& inLight, VenueShowLight::Role inRole, int inGroup )
{
    if( !m_world || !m_root || !inLight || !inLight->HasComponent<Light>() || !inLight->HasComponent<Transform>() || inRole == VenueShowLight::Role::Static )
    {
        return;
    }
    Fixture fixture;
    fixture.Adopted = true;
    fixture.Light = inLight;
    const Light& light = inLight->GetComponent<Light>();
    fixture.BaseColor = light.Color;
    fixture.BaseIntensity = light.Intensity;
    fixture.MaxIntensity = light.Intensity;
    fixture.Color = light.Color;
    Transform& transform = inLight->GetComponent<Transform>();
    const Vector3 position = m_root->InverseTransformPoint( transform.GetWorldPosition() );
    const Vector3 aim = m_root->InverseTransformDirection( transform.Front() );
    fixture.BaseAim = aim.Length() > 1e-4f ? aim.Normalized() : Vector3( 0.f, 0.f, 1.f );
    fixture.Side = position.x < m_bandCentre.x ? -1 : 1;
    // Lights of a group share a seed (Index), so a look gives them the same colour and moves.
    const int group = std::abs( inGroup );
    fixture.Index = group;
    switch( inRole )
    {
    case VenueShowLight::Role::Wash:
        fixture.Kind = Group::Wash;
        fixture.Row = group % kWashRows;
        break;
    case VenueShowLight::Role::Beam:
        fixture.Kind = Group::Beam;
        fixture.Row = group % kBeamRows;
        break;
    case VenueShowLight::Role::Blinder:
        fixture.Kind = Group::Crowd;
        break;
    case VenueShowLight::Role::Strobe:
        fixture.Kind = Group::Strobe;
        break;
    case VenueShowLight::Role::Spot:
    {
        // Follow spots go to the drummer first, then the singer, guitar, bass and keys: the
        // members there are, in turn.
        fixture.Kind = Group::Spot;
        const int order[kSpotCount] = { VenueData::Drums, VenueData::Vocals, VenueData::Guitar, VenueData::Bass, VenueData::Keys };
        std::vector<int> slots;
        for( int member : order )
        {
            for( int slot = 0; slot < kSpotCount; ++slot )
            {
                if( kSpotMember[slot] == member && m_members[slot] ) slots.push_back( slot );
            }
        }
        if( slots.empty() )
        {
            return;
        }
        fixture.Index = slots[static_cast<size_t>( m_adoptedSpots++ ) % slots.size()];
        break;
    }
    default:
        return;
    }
    m_fixtures.push_back( fixture );
}


void StageLights::UpdateAdopted( Fixture& ioFixture, const Vector3& inColor, float inLevel )
{
    if( !ioFixture.Light || !ioFixture.Light->HasComponent<Light>() )
    {
        return;
    }
    Transform& transform = ioFixture.Light->GetComponent<Transform>();
    if( ioFixture.Kind == Group::Beam )
    {
        // Swaying about its authored aim as a moving head would move: the look's pan and tilt,
        // scaled down and kept within reach of where it was pointed.
        const float pan = std::clamp( ( ioFixture.Yaw - static_cast<float>( ioFixture.Side ) * 18.f ) * 0.5f, -30.f, 30.f ) * kPi / 180.f;
        const float tilt = std::clamp( ( ioFixture.Pitch - 62.f ) * 0.35f, -12.f, 12.f ) * kPi / 180.f;
        const Vector3& base = ioFixture.BaseAim;
        const float flat = std::sqrt( base.x * base.x + base.z * base.z );
        const float heading = std::atan2( base.x, base.z ) + pan;
        const float pitch = std::clamp( std::atan2( base.y, flat ) + tilt, -85.f * kPi / 180.f, 85.f * kPi / 180.f );
        const Vector3 aim( std::sin( heading ) * std::cos( pitch ), std::sin( pitch ), std::cos( heading ) * std::cos( pitch ) );
        transform.LookDirection( m_root->TransformDirection( aim ) );
    }
    else if( ioFixture.Kind == Group::Spot && m_spotTracked[std::clamp( ioFixture.Index, 0, 4 )] )
    {
        transform.LookAt( m_root->TransformPoint( m_spotTargets[std::clamp( ioFixture.Index, 0, 4 )] ) );
    }
    Light& light = ioFixture.Light->GetComponent<Light>();
    // The cue's colour, keeping a little of the light's own.
    light.Color = Mix( inColor, ioFixture.BaseColor, 0.3f );
    light.Intensity = ioFixture.MaxIntensity * std::max( inLevel, 0.f );
}


void StageLights::OnHit( PadId inPad )
{
    switch( inPad )
    {
    case PadId::Bass: m_kickPulse = 1.f; break;
    case PadId::Snare: m_snarePulse = 1.f; break;
    case PadId::HighTom: m_tomPulse[0] = 1.f; break;
    case PadId::MidTom: m_tomPulse[0] = m_tomPulse[1] = 0.7f; break;
    case PadId::FloorTom: m_tomPulse[1] = 1.f; break;
    case PadId::Crash1:
    case PadId::Crash2:
    case PadId::China:
    case PadId::Splash: m_crashFlash = 1.f; break;
    default: break;
    }
}


void StageLights::OnMiss()
{
    m_missDip = 1.f;
}


Vector3 StageLights::WashGlow() const
{
    Vector3 sum( 0.f, 0.f, 0.f );
    int count = 0;
    for( const Fixture& fixture : m_fixtures )
    {
        if( fixture.Kind == Group::Wash || fixture.Kind == Group::Beam || fixture.Kind == Group::Mover )
        {
            sum = sum + fixture.Color * fixture.Level;
            ++count;
        }
    }
    return count > 0 ? sum * ( 1.f / static_cast<float>( count ) ) : sum;
}
