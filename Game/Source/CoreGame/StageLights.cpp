#include "CoreGame/StageLights.h"
#include "Components/Transform.h"
#include "Components/Lighting/Light.h"
#include "Components/Graphics/PostProcess.h"
#include "Config/GameSettings.h"
#include "Engine/World.h"
#include "Core/CommandLine.h"
#include <algorithm>
#include <cmath>

namespace
{
    // The rig, in the camera rig's space (the strike bar at z 0, the highway along +z, 7.2 wide).
    // Light settings follow MitchGame's ConcertTest study: narrow, very bright cones in haze.
    constexpr int kBeamRows = 4;
    constexpr float kBeamRowZ[kBeamRows] = { 4.f, 16.f, 28.f, 40.f };
    constexpr float kBeamX = 6.6f;
    constexpr float kBeamIntensity = 30000.f;
    constexpr float kBeamInner = 4.f;
    constexpr float kBeamOuter = 8.f;
    constexpr float kBeamRange = 60.f;

    constexpr int kWashRows = 3;
    constexpr float kWashRowZ[kWashRows] = { 8.f, 24.f, 40.f };
    constexpr float kWashX = 13.5f;
    constexpr float kWashHeight = 13.f;
    constexpr float kWashIntensity = 3000.f;

    // Spotlights (VENUE notes 37-41): pools of white on the floor beside the highway.
    constexpr int kSpotCount = 5;
    const Vector3 kSpotTargets[kSpotCount] = { Vector3( -10.f, 0.f, 12.f ), Vector3( 10.f, 0.f, 12.f ), Vector3( -16.f, 0.f, 28.f ), Vector3( 16.f, 0.f, 28.f ), Vector3( 20.f, 0.f, 44.f ) };
    constexpr float kSpotIntensity = 6000.f;

    // Haze while the show runs (the camera's own fog comes back after): denser on "[FogOn]".
    constexpr float kHazeDensity = 0.009f;
    constexpr float kHazeDensityFogOn = 0.016f;
    constexpr float kHazeStart = 8.f;
    constexpr float kHazeScatter = 0.6f;

    constexpr float kKeyIntensity = 2.f;

    const Vector3 kWhite( 1.f, 0.96f, 0.9f );
    const Vector3 kCool[] = { Vector3( 0.15f, 0.35f, 1.f ), Vector3( 0.1f, 0.8f, 1.f ), Vector3( 0.5f, 0.2f, 1.f ) };
    const Vector3 kWarm[] = { Vector3( 1.f, 0.5f, 0.12f ), Vector3( 1.f, 0.14f, 0.08f ), Vector3( 1.f, 0.2f, 0.55f ) };
    const Vector3 kClash[] = { Vector3( 0.3f, 1.f, 0.15f ), Vector3( 1.f, 0.1f, 0.8f ) };

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
}


void StageLights::Build( World& inWorld, Transform* inParent, const EntityHandle& inCamera, const TrackData& inTrack, const SpawnBoxFn& inSpawnBox, const TintFn& inTint )
{
    Clear();
    const int setting = GameSettings::GetInstance().StageLighting;
    if( setting <= 0 || !inParent )
    {
        return;
    }
    m_world = &inWorld;
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

    // A dark stage floor for the washes and spots to land on, under the highway.
    m_props.push_back( inSpawnBox( Vector3( 0.f, -0.16f, 45.f ), Vector3( 90.f, 0.04f, 140.f ), Vector3( 0.05f, 0.05f, 0.06f ), Vector3( 0.f, 0.f, 0.f ), inParent ) );

    int index = 0;
    for( int row = 0; row < kBeamRows; ++row )
    {
        for( int side : { -1, 1 } )
        {
            const Vector3 base( static_cast<float>( side ) * kBeamX, 0.f, kBeamRowZ[row] );
            // The fixture's can on the floor; its lens is tinted with the beam each frame.
            m_props.push_back( inSpawnBox( base + Vector3( 0.f, 0.2f, 0.f ), Vector3( 0.7f, 0.4f, 0.7f ), Vector3( 0.04f, 0.04f, 0.05f ), Vector3( 0.f, 0.f, 0.f ), inParent ) );
            const EntityHandle lens = inSpawnBox( base + Vector3( 0.f, 0.42f, 0.f ), Vector3( 0.5f, 0.06f, 0.5f ), Vector3( 0.f, 0.f, 0.f ), Vector3( 0.f, 0.f, 0.f ), inParent );
            SpawnFixture( Group::Beam, side, row, index++, base + Vector3( 0.f, 0.5f, 0.f ), Vector3( 0.f, 1.f, 0.4f ), kBeamInner, kBeamOuter, kBeamRange, kBeamIntensity, inParent, lens );
        }
    }
    index = 0;
    for( int row = 0; row < kWashRows; ++row )
    {
        for( int side : { -1, 1 } )
        {
            const Vector3 position( static_cast<float>( side ) * kWashX, kWashHeight, kWashRowZ[row] );
            const Vector3 target( static_cast<float>( side ) * ( kWashX - 1.f ), 0.f, kWashRowZ[row] + 3.f );
            SpawnFixture( Group::Wash, side, row, index++, position, target - position, 22.f, 34.f, 30.f, kWashIntensity, inParent, {} );
        }
    }
    for( int slot = 0; slot < kSpotCount; ++slot )
    {
        const Vector3 position = kSpotTargets[slot] + Vector3( 0.f, 16.f, -4.f );
        SpawnFixture( Group::Spot, kSpotTargets[slot].x < 0.f ? -1 : 1, 0, slot, position, kSpotTargets[slot] - position, 6.f, 9.f, 30.f, kSpotIntensity, inParent, {} );
    }

    // With no directional light the renderer supplies a daylight sun, which the haze would scatter
    // into a grey veil. A dim key light from behind the camera takes its place: enough to keep the
    // notes lit, too little to fog the highway.
    if( EntityHandle key = m_world->CreateEntity( "StageKeyLight" ) )
    {
        Transform& transform = key->AddComponent<Transform>( "StageKeyLight" );
        transform.SetParent( *inParent );
        transform.LookDirection( Vector3( 0.f, -0.8f, 0.6f ).Normalized() );
        Light& light = key->AddComponent<Light>();
        light.LightType = Moonlight::LightType::Directional;
        light.DirectionalSource = Moonlight::DirectionalSource::Manual;
        light.Color = Vector3( 0.85f, 0.9f, 1.f );
        light.Intensity = kKeyIntensity;
        m_props.push_back( key );
    }

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
        post.Fog = true;
        post.VolumetricFog = true;
        post.VolumetricSteps = std::max( post.VolumetricSteps, 64 );
        post.VolumetricDistance = std::max( post.VolumetricDistance, 90.f );
        post.FogStartDistance = std::min( post.FogStartDistance, kHazeStart );
        post.FogSunIntensity = kHazeScatter;
        post.FogLocalAnisotropy = 0.2f;
        m_hazeLevel = 0.f;
    }
}


void StageLights::SpawnFixture( Group inKind, int inSide, int inRow, int inIndex, const Vector3& inPosition, const Vector3& inAim, float inInner, float inOuter, float inRange, float inIntensity, Transform* inParent, const EntityHandle& inLens )
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
        return;
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
    light.CastShadows = false;
    fixture.Light = entity;
    fixture.Lens = inLens;
    m_fixtures.push_back( fixture );
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
        if( fixture.Light ) fixture.Light->MarkForDelete();
        if( fixture.Lens ) fixture.Lens->MarkForDelete();
    }
    for( EntityHandle& prop : m_props )
    {
        if( prop ) prop->MarkForDelete();
    }
    m_fixtures.clear();
    m_props.clear();
    if( m_savedFog && m_camera && m_camera->HasComponent<PostProcess>() )
    {
        PostProcess& post = m_camera->GetComponent<PostProcess>();
        post.VolumetricFog = m_fogWasVolumetric;
        post.FogDensity = m_fogDensity;
        post.FogStartDistance = m_fogStart;
        post.FogSunIntensity = m_fogScatter;
        post.VolumetricSteps = m_fogSteps;
        post.VolumetricDistance = m_fogDistance;
    }
    m_savedFog = false;
    m_camera = {};
    m_venue.Clear();
    m_beats.clear();
    m_kickPulse = m_snarePulse = m_crashFlash = m_missDip = 0.f;
    m_tomPulse = { 0.f, 0.f };
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

    if( inFixture.Kind == Group::Spot )
    {
        look.Color = kWhite;
        look.Level = 0.f;
        return look;
    }

    if( cue == "manual_cool" || cue == "manual_warm" || cue == "verse" || cue == "chorus" || cue.empty() )
    {
        const bool warm = cue == "manual_warm" || cue == "chorus";
        const Vector3* palette = warm ? kWarm : kCool;
        look.Color = palette[( n + key ) % 3];
        look.Level = cue == "chorus" ? 1.f : 0.75f;
        look.Pitch = 58.f + 8.f * static_cast<float>( ( key + inFixture.Row ) % 2 );
        if( cue.empty() )
        {
            look.Color = Mix( kWarm[0], kCool[0], 0.5f + 0.5f * std::sin( t * 0.3f + n ) );
            look.Level = 0.55f;
        }
    }
    else if( cue == "dischord" )
    {
        look.Color = kClash[( n + key ) % 2];
        look.Level = 0.6f + 0.4f * Noise( n, key );
        look.Yaw = side * ( 10.f + 30.f * Noise( n + 7, key ) );
        look.Pitch = 50.f + 25.f * Noise( n + 3, key );
    }
    else if( cue == "stomp" )
    {
        look.Color = kWarm[0];
        look.Level = key % 2 == 0 ? 1.f : 0.f;
    }
    else if( cue == "loop_cool" || cue == "loop_warm" )
    {
        // A chase down the rows, a row a beat, on a slow sway.
        const Vector3* palette = cue == "loop_warm" ? kWarm : kCool;
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
        look.Color = warmSide ? kWarm[0] : kCool[1];
        look.Level = 0.8f;
        look.Yaw = -side * 14.f;   // beams cross over the highway
        look.Pitch = 55.f;
    }
    else if( cue == "frenzy" || cue == "bre" )
    {
        const int step = static_cast<int>( std::floor( inBeat * 2.0 ) );
        const Vector3 colors[] = { kWarm[0], kWarm[1], kCool[0], kCool[1], kClash[1], kWhite };
        look.Color = colors[static_cast<int>( Noise( n, step ) * 6.f ) % 6];
        look.Level = m_gentle ? 0.8f : 0.4f + 0.6f * Noise( n + 11, step );
        look.Yaw = side * 40.f * ( Noise( n + 5, step ) - 0.3f );
        look.Pitch = 45.f + 30.f * Noise( n + 9, step );
    }
    else if( cue == "silhouettes" || cue == "silhouettes_spot" )
    {
        // Backlight only: the far rows bright and pale, the rest dark.
        const bool back = beam ? inFixture.Row >= kBeamRows - 1 : inFixture.Row >= kWashRows - 1;
        look.Color = Mix( kCool[0], kWhite, 0.6f );
        look.Level = back ? 1.f : 0.f;
        look.Pitch = 70.f;
        look.Yaw = -side * 8.f;
    }
    else if( cue == "searchlights" )
    {
        look.Color = Mix( kWhite, kCool[1], 0.25f );
        look.Level = wash ? 0.1f : 0.9f;
        look.Yaw = side * 10.f + 45.f * std::sin( t * 0.9f + n * 1.7f );
        look.Pitch = 50.f + 15.f * std::sin( t * 0.6f + n );
    }
    else if( cue == "sweep" )
    {
        // Every beam sweeps together across a measure, alternating colour by side.
        const double measure = inBeat / 4.0;
        look.Color = inFixture.Side > 0 ? kWarm[2] : kCool[2];
        look.Level = wash ? 0.4f : 0.95f;
        look.Yaw = 40.f * static_cast<float>( std::sin( measure * 2.0 * 3.14159265 ) );
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
        look.Color = kCool[0];
    }
    else if( StartsWith( cue, "flare" ) )
    {
        // A white flash fading back to the look before it.
        Look base = LookFor( inFixture, CueAt( inCue.Start - 0.001, 0 ), inSeconds, inBeat );
        const float fade = cue == "flare_fast" ? 0.35f : 1.2f;
        const float flash = std::exp( -static_cast<float>( inSeconds - inCue.Start ) / fade ) * ( m_gentle ? 0.3f : 1.f );
        base.Color = Mix( base.Color, kWhite, flash );
        base.Level = std::min( 1.f, base.Level + flash );
        return base;
    }
    else
    {
        look.Color = kWarm[n % 3];
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
    m_camera->GetComponent<PostProcess>().FogDensity = kHazeDensity + ( kHazeDensityFogOn - kHazeDensity ) * m_hazeLevel;
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

    // Crowd energy scales the whole show a little.
    float energy = 0.9f;
    for( const TimedCueData& crowd : m_venue.m_crowd )
    {
        if( crowd.m_time > seconds ) break;
        energy = crowd.m_name == "intense" ? 1.f : crowd.m_name == "mellow" ? 0.7f : 0.9f;
    }
    // Pyro: a burst of hot white and orange.
    float bonus = 0.f;
    for( float time : m_venue.m_bonusFx )
    {
        if( time > seconds ) break;
        bonus = std::max( bonus, std::exp( -static_cast<float>( seconds - time ) / 0.6f ) );
    }
    if( m_gentle ) bonus *= 0.35f;

    const float decay = std::exp( -inDeltaTime * 7.f );
    m_kickPulse *= decay;
    m_snarePulse *= decay;
    m_crashFlash *= std::exp( -inDeltaTime * 5.f );
    m_tomPulse[0] *= decay;
    m_tomPulse[1] *= decay;
    m_missDip *= std::exp( -inDeltaTime * 4.f );

    const float ease = 1.f - std::exp( -inDeltaTime * EaseRate( cue.Name ) );
    for( Fixture& fixture : m_fixtures )
    {
        Look look = LookFor( fixture, cue, seconds, beat );
        if( fixture.Kind == Group::Spot )
        {
            for( const VenueData::SpotlightData& spot : m_venue.m_spotlights )
            {
                if( spot.m_slot == fixture.Index && seconds >= spot.m_start && seconds < spot.m_end )
                {
                    look.Level = 1.f;
                }
            }
            if( cue.Name == "silhouettes_spot" || cue.Name == "blackout_spot" )
            {
                look.Level = std::max( look.Level, fixture.Index < 2 ? 1.f : 0.f );
            }
        }
        fixture.Color = Mix( fixture.Color, look.Color, ease );
        fixture.Level += ( look.Level - fixture.Level ) * ease;
        fixture.Yaw += ( look.Yaw - fixture.Yaw ) * ease;
        fixture.Pitch += ( look.Pitch - fixture.Pitch ) * ease;

        // The player's hits on top: kicks swell the washes, snares and toms punch the beams,
        // cymbals flash them white. A miss dims everything for a moment.
        Vector3 color = fixture.Color;
        float level = fixture.Level * energy;
        if( fixture.Kind == Group::Wash )
        {
            level += 0.45f * m_kickPulse;
            color = Mix( color, Vector3( 1.f, 0.45f, 0.1f ), bonus );
            level += bonus;
        }
        else if( fixture.Kind == Group::Beam )
        {
            level += 0.35f * m_snarePulse + 0.5f * m_tomPulse[fixture.Side > 0 ? 1 : 0];
            const float flash = std::max( m_crashFlash * ( m_gentle ? 0.3f : 0.7f ), bonus );
            color = Mix( color, kWhite, flash );
            level += flash;
        }
        level *= 1.f - 0.5f * m_missDip;
        level = std::clamp( level, 0.f, 1.5f );

        if( fixture.Light )
        {
            Transform& transform = fixture.Light->GetComponent<Transform>();
            if( fixture.Kind == Group::Beam )
            {
                const float yaw = fixture.Yaw * 3.14159265f / 180.f;
                const float pitch = fixture.Pitch * 3.14159265f / 180.f;
                transform.LookDirection( Vector3( std::sin( yaw ) * std::cos( pitch ), std::sin( pitch ), std::cos( yaw ) * std::cos( pitch ) ) );
            }
            Light& light = fixture.Light->GetComponent<Light>();
            light.Color = color;
            light.Intensity = fixture.MaxIntensity * level;
        }
        if( fixture.Lens && m_tint )
        {
            m_tint( fixture.Lens, color * 0.2f, color * ( 2.5f * level ) );
        }
    }
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
