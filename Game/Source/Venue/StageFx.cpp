#include "Venue/StageFx.h"
#include "Venue/VenueKit.h"
#include "Venue/VenueLayout.h"
#include "Venue/VenueTiming.h"
#include "Components/Effects/ParticleSystem.h"
#include "Components/Lighting/Light.h"
#include "Components/Transform.h"
#include "Math/Quaternion.h"
#include <algorithm>
#include <cmath>

namespace
{
    using Shape = Moonlight::MeshType;
    constexpr int kClub = 1;
    constexpr int kFestival = 2;
    // Confetti is square paper, not the particle shader's round dot.
    constexpr const char* kConfettiTexture = "Assets/Textures/Venue/Confetti.png";

    // Emission rates while an effect runs, particles a second per emitter.
    constexpr float kFlameRate = 240.f;
    constexpr float kJetRate = 140.f;
    constexpr float kSparkRate = 380.f;
    constexpr float kLowFogRate = 12.f;
    constexpr int kConfettiSalvo = 260;
    constexpr int kShellStars = 240;

    // Where things stand, in venue space. The flame pots and jets alternate along the stage's
    // front edge, clear of the floor cans (x 2.4 and 6.8) and the singer's wedges.
    constexpr float kPotX[] = { -7.5f, -3.f, 3.f, 7.5f };
    constexpr float kJetX[] = { -8.3f, -5.2f, -1.5f, 1.5f, 5.2f, 8.3f };
    constexpr float kSparkX[] = { -8.7f, -4.4f, 4.4f, 8.7f };

    ParticleSystem* SystemOf( const EntityHandle& inEmitter )
    {
        return inEmitter && inEmitter->HasComponent<ParticleSystem>() ? &inEmitter->GetComponent<ParticleSystem>() : nullptr;
    }


    void SetRate( const EntityHandle& inEmitter, float inRate )
    {
        if( ParticleSystem* system = SystemOf( inEmitter ) )
        {
            system->EmissionRate = inRate;
        }
    }
}


EntityHandle StageFx::Emitter( VenueKit& inKit, Transform& inRoot, const char* inName, const Vector3& inPosition, const Vector3& inDirection )
{
    EntityHandle entity = inKit.Group( inName, &inRoot, inPosition );
    if( !entity )
    {
        return entity;
    }
    // A cone emits along its entity's up axis: turn that onto the direction.
    const Vector3 direction = inDirection.Normalized();
    const Vector3 axis = Vector3( 0.f, 1.f, 0.f ).Cross( direction );
    if( axis.Length() > 0.001f )
    {
        entity->GetComponent<Transform>().SetRotation( Quaternion::AngleAxis( std::acos( std::clamp( direction.y, -1.f, 1.f ) ), axis.Normalized() ) );
    }
    ParticleSystem& system = entity->AddComponent<ParticleSystem>();
    // Idle until fired.
    system.Looping = true;
    system.EmissionRate = 0.f;
    system.BurstCount = 0;
    system.SimulationSpace = ParticleSpace::World;
    return entity;
}


void StageFx::Build( VenueKit& inKit, Transform& inRoot, int inStyle, const VenueData& inVenue )
{
    Clear();
    m_style = inStyle;
    m_bonusFx = inVenue.m_bonusFx;
    const float deck = VenueLayout::kStageHeight;
    const Vector3 up( 0.f, 1.f, 0.f );

    // Flame pots: a column of fire, the embers it throws off and the light it casts.
    for( float x : kPotX )
    {
        Pot pot;
        pot.Base = Vector3( x, deck, 0.35f );
        inKit.Box( pot.Base + Vector3( 0.f, 0.1f, 0.f ), Vector3( 0.4f, 0.2f, 0.4f ), Vector3( 0.03f, 0.03f, 0.03f ), &inRoot );
        pot.Flame = inKit.Piece( Shape::Capsule, pot.Base + Vector3( 0.f, -5.f, 0.f ), Vector3( 0.3f, 3.f, 0.3f ), Vector3( 0.f, 0.f, 0.f ), &inRoot, Vector3( 40.f, 16.f, 3.f ), false );
        pot.Fire = Emitter( inKit, inRoot, "Flame", pot.Base + Vector3( 0.f, 0.25f, 0.f ), up );
        if( ParticleSystem* fire = SystemOf( pot.Fire ) )
        {
            fire->MaxParticles = 300;
            fire->Shape = ParticleShape::Cone;
            fire->ShapeRadius = 0.12f;
            fire->ConeAngle = 5.f;
            fire->Lifetime = Vector2( 0.22f, 0.5f );
            fire->Speed = Vector2( 8.f, 14.f );
            fire->Size = Vector2( 0.5f, 0.9f );
            fire->EndSize = 0.3f;
            fire->StartColor = Vector3( 1.f, 0.5f, 0.1f );
            fire->StartColor2 = Vector3( 1.f, 0.78f, 0.28f );
            fire->EndColor = Vector3( 0.85f, 0.1f, 0.02f );
            fire->StartAlpha = 0.9f;
            fire->EndAlpha = 0.f;
            fire->FadeIn = 0.05f;
            fire->Intensity = 5.f;
            fire->Gravity = -0.3f;
            fire->Drag = 1.2f;
            fire->NoiseStrength = 2.f;
            fire->NoiseFrequency = 1.5f;
            fire->Blend = Moonlight::ParticleBlend::Additive;
            fire->SoftParticleDistance = 0.3f;
        }
        pot.Embers = Emitter( inKit, inRoot, "Embers", pot.Base + Vector3( 0.f, 1.2f, 0.f ), up );
        if( ParticleSystem* embers = SystemOf( pot.Embers ) )
        {
            embers->MaxParticles = 200;
            embers->Shape = ParticleShape::Cone;
            embers->ShapeRadius = 0.2f;
            embers->ConeAngle = 28.f;
            embers->Lifetime = Vector2( 1.2f, 2.8f );
            embers->Speed = Vector2( 2.f, 7.f );
            embers->Size = Vector2( 0.03f, 0.06f );
            embers->EndSize = 0.4f;
            embers->StartColor = Vector3( 1.f, 0.55f, 0.15f );
            embers->StartColor2 = Vector3( 1.f, 0.8f, 0.4f );
            embers->EndColor = Vector3( 0.9f, 0.15f, 0.02f );
            embers->EndAlpha = 0.f;
            embers->Intensity = 7.f;
            embers->Gravity = -0.04f;
            embers->Drag = 0.9f;
            embers->NoiseStrength = 2.5f;
            embers->NoiseFrequency = 0.8f;
            embers->Blend = Moonlight::ParticleBlend::Additive;
            embers->SoftParticleDistance = 0.05f;
        }
        pot.Light = inKit.Group( "PyroLight", &inRoot, pot.Base + Vector3( 0.f, 1.5f, -0.4f ) );
        if( pot.Light )
        {
            Light& light = pot.Light->AddComponent<Light>();
            light.LightType = Moonlight::LightType::Point;
            light.Color = Vector3( 1.f, 0.55f, 0.2f );
            light.Intensity = 0.f;
            light.Range = 14.f;
            light.CastShadows = false;
        }
        m_pots.push_back( pot );
    }

    // CO2 jets: white plumes that shoot up, billow and take the colour of whatever lights them.
    for( float x : kJetX )
    {
        inKit.Box( Vector3( x, deck + 0.07f, 0.16f ), Vector3( 0.22f, 0.14f, 0.22f ), Vector3( 0.05f, 0.05f, 0.055f ), &inRoot );
        EntityHandle jet = Emitter( inKit, inRoot, "CO2 Jet", Vector3( x, deck + 0.2f, 0.16f ), Vector3( 0.f, 1.f, -0.06f ) );
        if( ParticleSystem* plume = SystemOf( jet ) )
        {
            plume->MaxParticles = 260;
            plume->Shape = ParticleShape::Cone;
            plume->ShapeRadius = 0.06f;
            plume->ConeAngle = 4.f;
            plume->Lifetime = Vector2( 0.7f, 1.3f );
            plume->Speed = Vector2( 15.f, 23.f );
            plume->Size = Vector2( 0.3f, 0.55f );
            plume->EndSize = 5.f;
            plume->StartColor = Vector3( 0.42f, 0.45f, 0.5f );
            plume->StartColor2 = Vector3( 0.55f, 0.55f, 0.55f );
            plume->EndColor = Vector3( 0.45f, 0.46f, 0.5f );
            plume->StartAlpha = 0.34f;
            plume->EndAlpha = 0.f;
            plume->FadeIn = 0.04f;
            plume->Intensity = 1.f;
            plume->Gravity = -0.02f;
            plume->Drag = 2.4f;
            plume->NoiseStrength = 1.2f;
            plume->NoiseFrequency = 0.7f;
            plume->AngularVelocity = Vector2( -30.f, 30.f );
            plume->Blend = Moonlight::ParticleBlend::Alpha;
            plume->Lit = true;
            plume->SoftParticleDistance = 0.6f;
        }
        m_jets.push_back( jet );
    }

    // Spark fountains: a spray of gold streaks that arcs over and dies before it lands.
    for( float x : kSparkX )
    {
        inKit.Piece( Shape::Cylinder, Vector3( x, deck + 0.1f, 0.5f ), Vector3( 0.16f, 0.2f, 0.16f ), Vector3( 0.05f, 0.05f, 0.055f ), &inRoot );
        EntityHandle fountain = Emitter( inKit, inRoot, "Spark Fountain", Vector3( x, deck + 0.22f, 0.5f ), up );
        if( ParticleSystem* sparks = SystemOf( fountain ) )
        {
            sparks->MaxParticles = 500;
            sparks->Shape = ParticleShape::Cone;
            sparks->ShapeRadius = 0.03f;
            sparks->ConeAngle = 9.f;
            sparks->Lifetime = Vector2( 0.5f, 1.05f );
            sparks->Speed = Vector2( 7.f, 12.f );
            sparks->Size = Vector2( 0.03f, 0.06f );
            sparks->EndSize = 0.4f;
            sparks->StartColor = Vector3( 1.f, 0.72f, 0.32f );
            sparks->StartColor2 = Vector3( 1.f, 0.92f, 0.65f );
            sparks->EndColor = Vector3( 1.f, 0.35f, 0.08f );
            sparks->EndAlpha = 0.f;
            sparks->FadeIn = 0.f;
            sparks->Intensity = 9.f;
            sparks->Gravity = 1.f;
            sparks->Drag = 0.5f;
            sparks->NoiseStrength = 0.6f;
            sparks->Blend = Moonlight::ParticleBlend::Additive;
            sparks->Alignment = Moonlight::ParticleAlignment::Stretched;
            sparks->StretchFactor = 0.05f;
            sparks->SoftParticleDistance = 0.05f;
        }
        m_sparks.push_back( fountain );
    }

    // Confetti cannons: on the front truss blowing out over the crowd, and at the stage's front
    // corners blowing up and across. Each loads its own two colours; they mix in the air.
    struct Cannon
    {
        Vector3 Position;
        Vector3 Aim;
        Vector3 ColorA;
        Vector3 ColorB;
    };
    const float truss = inStyle == kClub ? 8.2f : VenueLayout::kTrussHeight - 0.5f;
    const Cannon cannons[] = {
        { Vector3( -7.2f, truss, -0.3f ), Vector3( -0.15f, 0.45f, -1.f ), Vector3( 1.f, 0.1f, 0.25f ), Vector3( 1.f, 0.85f, 0.1f ) },
        { Vector3( -2.6f, truss, -0.3f ), Vector3( -0.05f, 0.5f, -1.f ), Vector3( 0.1f, 0.6f, 1.f ), Vector3( 1.f, 1.f, 1.f ) },
        { Vector3( 2.6f, truss, -0.3f ), Vector3( 0.05f, 0.5f, -1.f ), Vector3( 1.f, 0.2f, 0.8f ), Vector3( 0.2f, 1.f, 0.5f ) },
        { Vector3( 7.2f, truss, -0.3f ), Vector3( 0.15f, 0.45f, -1.f ), Vector3( 1.f, 0.5f, 0.05f ), Vector3( 0.3f, 0.9f, 1.f ) },
        { Vector3( -8.7f, deck + 0.3f, 0.9f ), Vector3( 0.35f, 1.f, -0.45f ), Vector3( 1.f, 1.f, 1.f ), Vector3( 1.f, 0.8f, 0.2f ) },
        { Vector3( 8.7f, deck + 0.3f, 0.9f ), Vector3( -0.35f, 1.f, -0.45f ), Vector3( 1.f, 1.f, 1.f ), Vector3( 0.9f, 0.15f, 0.2f ) },
    };
    for( const Cannon& cannon : cannons )
    {
        EntityHandle emitter = Emitter( inKit, inRoot, "Confetti Cannon", cannon.Position, cannon.Aim );
        if( ParticleSystem* paper = SystemOf( emitter ) )
        {
            paper->MaxParticles = 1200;
            paper->Shape = ParticleShape::Cone;
            paper->ShapeRadius = 0.15f;
            paper->ConeAngle = 32.f;
            paper->Lifetime = Vector2( 5.f, 9.f );
            paper->Speed = Vector2( 7.f, 17.f );
            paper->Size = Vector2( 0.07f, 0.12f );
            paper->EndSize = 1.f;
            paper->StartColor = cannon.ColorA;
            paper->StartColor2 = cannon.ColorB;
            // The colour over life runs toward EndColor: hold the pair's middle so the paper keeps its colour.
            paper->EndColor = ( cannon.ColorA + cannon.ColorB ) * 0.5f;
            paper->StartAlpha = 1.f;
            paper->EndAlpha = 0.5f;
            paper->FadeIn = 0.f;
            paper->Intensity = 1.5f;
            paper->Gravity = 0.09f;
            paper->Drag = 1.7f;
            paper->NoiseStrength = 2.4f;
            paper->NoiseFrequency = 0.5f;
            paper->AngularVelocity = Vector2( -540.f, 540.f );
            paper->Texture = Path( kConfettiTexture );
            paper->Blend = Moonlight::ParticleBlend::Alpha;
            paper->SoftParticleDistance = 0.f;
        }
        m_confetti.push_back( emitter );
    }

    // Dry ice: a low bank over the whole deck, lit by the rig.
    m_lowFog = Emitter( inKit, inRoot, "Low Fog", Vector3( 0.f, deck + 0.3f, 5.f ), up );
    if( ParticleSystem* fog = SystemOf( m_lowFog ) )
    {
        fog->MaxParticles = 140;
        fog->Shape = ParticleShape::Box;
        fog->BoxSize = Vector3( 17.f, 0.2f, 9.4f );
        fog->Lifetime = Vector2( 5.f, 9.f );
        fog->Speed = Vector2( 0.f, 0.06f );
        fog->Size = Vector2( 1.5f, 2.6f );
        fog->EndSize = 1.7f;
        fog->StartColor = Vector3( 0.75f, 0.8f, 0.88f );
        fog->StartColor2 = Vector3( 0.9f, 0.92f, 0.96f );
        fog->EndColor = Vector3( 0.8f, 0.84f, 0.9f );
        fog->StartAlpha = 0.13f;
        fog->EndAlpha = 0.f;
        fog->FadeIn = 0.3f;
        fog->Intensity = 1.f;
        fog->Gravity = 0.f;
        fog->Drag = 0.2f;
        fog->NoiseStrength = 0.25f;
        fog->NoiseFrequency = 0.25f;
        fog->AngularVelocity = Vector2( -8.f, 8.f );
        fog->Blend = Moonlight::ParticleBlend::Alpha;
        fog->Lit = true;
        fog->SoftParticleDistance = 0.9f;
    }

    // Dust: specks hanging in the air over the stage, dark until a beam finds them.
    m_dust = Emitter( inKit, inRoot, "Dust", Vector3( 0.f, deck + 3.6f, 3.6f ), up );
    if( ParticleSystem* dust = SystemOf( m_dust ) )
    {
        dust->MaxParticles = 700;
        dust->Shape = ParticleShape::Box;
        dust->BoxSize = Vector3( 20.f, 6.5f, 12.f );
        dust->Lifetime = Vector2( 6.f, 10.f );
        dust->Speed = Vector2( 0.f, 0.05f );
        dust->Size = Vector2( 0.014f, 0.035f );
        dust->EndSize = 1.f;
        dust->StartColor = Vector3( 1.f, 1.f, 1.f );
        dust->StartColor2 = Vector3( 0.9f, 0.92f, 1.f );
        dust->EndColor = Vector3( 1.f, 1.f, 1.f );
        dust->StartAlpha = 0.8f;
        dust->EndAlpha = 0.f;
        dust->FadeIn = 0.2f;
        dust->Intensity = 1.f;
        dust->Gravity = 0.002f;
        dust->Drag = 0.4f;
        dust->NoiseStrength = 0.18f;
        dust->NoiseFrequency = 0.4f;
        dust->Blend = Moonlight::ParticleBlend::Alpha;
        dust->Lit = true;
        dust->SoftParticleDistance = 0.1f;
        dust->EmissionRate = 70.f;
    }

    // Fireworks, out of doors: shells that burst high behind the stage.
    if( inStyle == kFestival )
    {
        const Vector3 colors[][2] = {
            { Vector3( 1.f, 0.75f, 0.3f ), Vector3( 1.f, 0.95f, 0.7f ) },
            { Vector3( 1.f, 0.15f, 0.2f ), Vector3( 1.f, 0.5f, 0.3f ) },
            { Vector3( 0.2f, 0.6f, 1.f ), Vector3( 0.7f, 0.9f, 1.f ) },
            { Vector3( 0.3f, 1.f, 0.4f ), Vector3( 0.9f, 1.f, 0.6f ) },
            { Vector3( 1.f, 0.3f, 0.9f ), Vector3( 1.f, 0.8f, 1.f ) },
            { Vector3( 1.f, 1.f, 1.f ), Vector3( 1.f, 0.85f, 0.5f ) },
        };
        for( const auto& pair : colors )
        {
            Shell shell;
            shell.Burst = Emitter( inKit, inRoot, "Firework", Vector3( 0.f, 30.f, 30.f ), up );
            if( ParticleSystem* stars = SystemOf( shell.Burst ) )
            {
                stars->MaxParticles = 600;
                stars->Shape = ParticleShape::Sphere;
                stars->ShapeRadius = 0.4f;
                stars->EmitFromShell = true;
                stars->Lifetime = Vector2( 1.3f, 2.3f );
                stars->Speed = Vector2( 9.f, 16.f );
                stars->Size = Vector2( 0.14f, 0.26f );
                stars->EndSize = 0.3f;
                stars->StartColor = pair[0];
                stars->StartColor2 = pair[1];
                stars->EndColor = pair[0] * 0.6f;
                stars->EndAlpha = 0.f;
                stars->FadeIn = 0.f;
                stars->Intensity = 14.f;
                stars->Gravity = 0.22f;
                stars->Drag = 1.3f;
                stars->NoiseStrength = 0.f;
                stars->Blend = Moonlight::ParticleBlend::Additive;
                stars->Alignment = Moonlight::ParticleAlignment::Stretched;
                stars->StretchFactor = 0.045f;
                stars->SoftParticleDistance = 0.f;
            }
            m_shells.push_back( shell );
        }
    }
}


void StageFx::Clear()
{
    m_pots.clear();
    m_jets.clear();
    m_sparks.clear();
    m_confetti.clear();
    m_shells.clear();
    m_lowFog = {};
    m_dust = {};
    m_bonusFx.clear();
    m_fired.clear();
    m_fireRequested = false;
    m_jetTime = 0.f;
    m_sparkTime = 0.f;
    m_burn = 0.f;
    m_lastBurn = 0.f;
    m_ignited = false;
    m_volley = 0;
}


void StageFx::Flames()
{
    m_fireRequested = true;
}


void StageFx::Jets( float inSeconds )
{
    m_jetTime = std::max( m_jetTime, inSeconds );
}


void StageFx::Sparks( float inSeconds )
{
    m_sparkTime = std::max( m_sparkTime, inSeconds );
}


void StageFx::Confetti( float inAmount )
{
    // A club's low ceiling gets a lighter load.
    const float scale = m_style == kClub ? 0.5f : 1.f;
    const int count = static_cast<int>( static_cast<float>( kConfettiSalvo ) * std::clamp( inAmount, 0.f, 2.f ) * scale );
    for( const EntityHandle& cannon : m_confetti )
    {
        if( ParticleSystem* paper = SystemOf( cannon ) )
        {
            paper->Burst( count );
        }
    }
}


void StageFx::Fireworks( int inShells )
{
    // Staggered over a couple of seconds, each somewhere new in the sky behind the stage.
    int launched = 0;
    for( size_t i = 0; i < m_shells.size() && launched < inShells; ++i )
    {
        Shell& shell = m_shells[( i + m_volley ) % m_shells.size()];
        if( shell.At >= 0.f || !shell.Burst )
        {
            continue;
        }
        const uint32_t seed = m_volley * 31u + static_cast<uint32_t>( i );
        shell.At = 0.05f + 0.35f * static_cast<float>( launched ) + 0.2f * VenueTiming::Noise( seed, 5u );
        shell.Burst->GetComponent<Transform>().SetPosition( Vector3( -30.f + 60.f * VenueTiming::Noise( seed, 1u ), 26.f + 14.f * VenueTiming::Noise( seed, 2u ), 22.f + 24.f * VenueTiming::Noise( seed, 3u ) ) );
        ++launched;
    }
    ++m_volley;
}


void StageFx::Update( double inSeconds, float inDeltaTime, bool inGentle, float inLowFog )
{
    // Flame bursts, the chart's and those fired by hand: up fast and dying away over a second and
    // a half, on the song clock.
    if( m_fireRequested )
    {
        m_fired.push_back( static_cast<float>( inSeconds ) );
        m_fireRequested = false;
    }
    float burn = 0.f;
    const auto burning = [&burn, inSeconds]( const std::vector<float>& inTimes ) {
        for( float time : inTimes )
        {
            if( time > inSeconds ) break;
            const float since = static_cast<float>( inSeconds ) - time;
            if( since < 1.6f ) burn = std::max( burn, std::exp( -since / 0.45f ) );
        }
    };
    burning( m_bonusFx );
    burning( m_fired );
    if( inGentle )
    {
        burn *= 0.4f;
    }
    m_ignited = burn > 0.5f && m_lastBurn <= 0.5f;
    m_lastBurn = burn;
    m_burn = burn;
    for( size_t i = 0; i < m_pots.size(); ++i )
    {
        Pot& pot = m_pots[i];
        const float flicker = 0.85f + 0.15f * std::sin( static_cast<float>( inSeconds ) * 31.f + static_cast<float>( i ) * 2.f );
        const float height = 3.4f * burn * flicker;
        if( pot.Flame )
        {
            Transform& flame = pot.Flame->GetComponent<Transform>();
            if( height > 0.05f )
            {
                flame.SetPosition( pot.Base + Vector3( 0.f, 0.2f + height * 0.5f, 0.f ) );
                flame.SetScale( VenueKit::ScaleFor( Shape::Capsule, Vector3( 0.16f + 0.16f * burn, height, 0.16f + 0.16f * burn ) ) );
            }
            else
            {
                flame.SetPosition( pot.Base + Vector3( 0.f, -5.f, 0.f ) );
            }
        }
        SetRate( pot.Fire, burn > 0.04f ? kFlameRate * std::min( 1.f, burn * 1.6f ) : 0.f );
        if( ParticleSystem* fire = SystemOf( pot.Fire ) )
        {
            // The flames reach as high as the burst is strong.
            fire->Speed = Vector2( 5.f + 5.f * burn, 8.f + 9.f * burn );
        }
        if( m_ignited )
        {
            if( ParticleSystem* embers = SystemOf( pot.Embers ) )
            {
                embers->Burst( inGentle ? 20 : 60 );
            }
        }
        if( pot.Light )
        {
            pot.Light->GetComponent<Light>().Intensity = 2400.f * burn * flicker;
        }
    }

    m_jetTime = std::max( 0.f, m_jetTime - inDeltaTime );
    for( const EntityHandle& jet : m_jets )
    {
        SetRate( jet, m_jetTime > 0.f ? kJetRate : 0.f );
    }
    m_sparkTime = std::max( 0.f, m_sparkTime - inDeltaTime );
    for( const EntityHandle& fountain : m_sparks )
    {
        SetRate( fountain, m_sparkTime > 0.f ? kSparkRate * ( inGentle ? 0.5f : 1.f ) : 0.f );
    }
    SetRate( m_lowFog, kLowFogRate * std::clamp( inLowFog, 0.f, 1.f ) );

    for( Shell& shell : m_shells )
    {
        if( shell.At < 0.f )
        {
            continue;
        }
        shell.At -= inDeltaTime;
        if( shell.At < 0.f )
        {
            if( ParticleSystem* stars = SystemOf( shell.Burst ) )
            {
                stars->Burst( kShellStars );
            }
        }
    }
}
