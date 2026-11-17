#include "Venue/Crowd.h"
#include "Venue/People.generated.h"
#include "Venue/VenueKit.h"
#include "Venue/VenueTiming.h"
#include "Components/Transform.h"
#include <algorithm>
#include <cmath>

namespace
{
    constexpr float kPi = 3.14159265f;

    float Pulse( double inBeat, double inPower = 2.0 )
    {
        const double fraction = inBeat - std::floor( inBeat );
        return static_cast<float>( std::pow( 1.0 - fraction, inPower ) );
    }

    // How a back-of-the-house figure's arm hangs, or goes up (a little out to the side).
    glm::quat MobArm( int inSide, bool inUp )
    {
        const float s = inSide == 0 ? -1.f : 1.f;
        const float spread = ( inUp ? 12.f : 8.f ) * s * kPi / 180.f;
        const float raise = ( inUp ? 172.f : 5.f ) * kPi / 180.f;
        return glm::angleAxis( -raise, glm::vec3( 1.f, 0.f, 0.f ) ) * glm::angleAxis( spread, glm::vec3( 0.f, 0.f, 1.f ) );
    }


    // Which way someone standing at x, z in an area faces (degrees): the area's yaw, turned part
    // of the way toward its focus.
    float FacingIn( const VenuePlan::CrowdArea& inArea, float inX, float inZ )
    {
        float toward = std::atan2( inArea.Focus.x - inX, inArea.Focus.z - inZ ) * 180.f / kPi - inArea.Yaw;
        if( toward > 180.f ) toward -= 360.f;
        else if( toward < -180.f ) toward += 360.f;
        return inArea.Yaw + toward * inArea.Turn;
    }
}


int Crowd::ModelFor( float inNoise ) const
{
    if( m_models.empty() )
    {
        return static_cast<int>( inNoise * People::kCount ) % People::kCount;
    }
    return m_models[static_cast<size_t>( inNoise * static_cast<float>( m_models.size() ) ) % m_models.size()];
}


void Crowd::Clear()
{
    m_people.clear();
    m_moods.clear();
    m_claps.clear();
    m_bonusFx.clear();
    m_beats.clear();
    m_sections.clear();
    m_energy = 0.5f;
    m_missDip = 0.f;
    m_cheer = 0.f;
    m_surfer = Puppet();
    m_surfRequested = false;
    m_surfProgress = -1.f;
    m_surfCount = 0;
    m_mob.clear();
    m_keepClear.clear();
    m_rows.clear();
    m_surfFromZ = -12.f;
    m_surfToZ = -2.2f;
}


void Crowd::Build( VenueKit& inKit, Transform* inFloor, const VenuePlan& inPlan, const VenueData& inVenue, const std::vector<BeatData>& inBeats, float inBpm, int inCount )
{
    Clear();
    m_beats = inBeats;
    m_bpm = inBpm;
    m_bonusFx = inVenue.m_bonusFx;
    m_sections = inVenue.m_sections;
    for( const TimedCueData& cue : inVenue.m_crowd )
    {
        if( cue.m_name == "clap" || cue.m_name == "noclap" ) m_claps.push_back( cue );
        else m_moods.push_back( cue );
    }
    if( m_moods.empty() )
    {
        BuildFallbackMoods();
    }

    // The posed figures, shared between the Posed areas by their head counts.
    int heads = 0;
    std::vector<const VenuePlan::CrowdArea*> posed;
    for( const VenuePlan::CrowdArea& area : inPlan.Crowd )
    {
        if( area.Type != VenuePlan::CrowdArea::Kind::Posed ) continue;
        posed.push_back( &area );
        heads += std::max( area.Heads, 0 );
    }
    uint32_t seed = 1;
    int given = 0;
    for( size_t i = 0; i < posed.size(); ++i )
    {
        const int count = i + 1 == posed.size() ? inCount - given
            : heads > 0 ? static_cast<int>( std::lround( static_cast<double>( inCount ) * std::max( posed[i]->Heads, 0 ) / heads ) ) : 0;
        given += count;
        BuildRows( inKit, inFloor, *posed[i], static_cast<int>( m_people.size() ) + count, seed );
    }
    if( !m_people.empty() )
    {
        // The crowd surfer goes up behind the front rows of the first area and is carried to
        // the barricade.
        const VenuePlan::CrowdArea& first = m_rows.front().Area;
        m_surfFromZ = std::min( std::max( -12.f, first.MinZ + 2.f ), first.MaxZ );
        m_surfToZ = inPlan.Stage.BarricadeZ - 0.6f;
        m_surfCentreX = ( first.MinX + first.MaxX ) * 0.5f;
        Puppet::Look look;
        look.Skin = static_cast<uint32_t>( m_people.size() );
        look.Model = ModelFor( 0.5f );
        m_surfer.Build( inKit, inFloor, Vector3( 0.f, -10.f, 0.f ), 0.f, look );
    }
}


void Crowd::BuildRows( VenueKit& inKit, Transform* inFloor, const VenuePlan::CrowdArea& inArea, int inCount, uint32_t& ioSeed )
{
    // Rows from the front back, widening toward the back of the room and thinning out.
    uint32_t& seed = ioSeed;
    const float front = inArea.MaxZ;
    const float back = inArea.MinZ;
    const float widest = ( inArea.MaxX - inArea.MinX ) * 0.5f;
    const float centre = ( inArea.MinX + inArea.MaxX ) * 0.5f;
    const float span = front - back;
    Rows rows{ inArea, front };
    const size_t before = m_people.size();
    for( float z = front; z > back && static_cast<int>( m_people.size() ) < inCount; z -= 0.64f )
    {
        const float depth = front - z;
        const float halfWidth = std::min( widest, inArea.FrontHalfWidth + depth * inArea.Widen );
        const float density = depth < span * 0.3f ? 0.95f : depth < span * 0.65f ? 0.75f : 0.5f;
        for( float x = -halfWidth; x <= halfWidth && static_cast<int>( m_people.size() ) < inCount; x += 0.58f )
        {
            ++seed;
            if( VenueTiming::Noise( seed, 1u ) > density )
            {
                continue;
            }
            Person person;
            const Vector3 feet( centre + x + ( VenueTiming::Noise( seed, 2u ) - 0.5f ) * 0.36f, 0.f, z + ( VenueTiming::Noise( seed, 3u ) - 0.5f ) * 0.3f );
            // Facing the stage, the singer's spot for those off to the side.
            const float yaw = FacingIn( inArea, feet.x, feet.z ) + ( VenueTiming::Noise( seed, 4u ) - 0.5f ) * 16.f;
            Puppet::Look look;
            look.Height = 0.9f + VenueTiming::Noise( seed, 10u ) * 0.2f;
            look.Build = 0.9f + VenueTiming::Noise( seed, 11u ) * 0.25f;
            // Full detail for the front rows only: the rest are small on screen.
            look.Far = depth > 4.5f;
            look.Skin = static_cast<uint32_t>( VenueTiming::Noise( seed, 5u ) * 1000.f );
            look.Model = ModelFor( VenueTiming::Noise( seed, 6u ) );
            person.Body.Build( inKit, inFloor, feet, yaw, look );
            person.Phase = VenueTiming::Noise( seed, 12u );
            // Keener toward the front.
            person.Enthusiasm = std::clamp( 0.25f + 0.75f * VenueTiming::Noise( seed, 13u ) + ( depth < 5.f ? 0.25f : 0.f ) - depth * 0.012f, 0.1f, 1.f );
            person.Kind = static_cast<int>( VenueTiming::Noise( seed, 14u ) * 4.f ) % 4;
            person.Depth = depth;
            const float item = VenueTiming::Noise( seed, 15u );
            person.Item = item < 0.07f ? 1 : item < 0.2f ? 2 : 0;
            if( person.Item != 0 )
            {
                const bool lighter = person.Item == 1;
                person.ItemPiece = inKit.Piece( lighter ? Moonlight::MeshType::Sphere : Moonlight::MeshType::Cube, Vector3( 0.f, -10.f, 0.f ), lighter ? Vector3( 0.05f, 0.08f, 0.05f ) : Vector3( 0.08f, 0.15f, 0.015f ),
                    Vector3( 0.f, 0.f, 0.f ), person.Body.Root(), lighter ? Vector3( 4.f, 1.6f, 0.3f ) : Vector3( 1.6f, 2.f, 3.f ) );
            }
            m_people.push_back( std::move( person ) );
            rows.BackZ = z;
        }
    }
    if( m_people.size() > before )
    {
        m_rows.push_back( rows );
    }
}


void Crowd::BuildFallbackMoods()
{
    // No crowd states in the chart: from its sections (mellow intros, intense choruses and solos),
    // clapping through the verses; or the player's own performance when it has no sections.
    if( m_sections.empty() )
    {
        m_moods.push_back( { 0.f, "realtime" } );
        return;
    }
    m_moods.push_back( { 0.f, "mellow" } );
    for( const TimedCueData& section : m_sections )
    {
        using VenueTiming::Contains;
        const std::string& name = section.m_name;
        std::string mood = "normal";
        if( Contains( name, "chorus" ) || Contains( name, "solo" ) || Contains( name, "big" ) || Contains( name, "loud" ) ) mood = "intense";
        else if( Contains( name, "intro" ) || Contains( name, "quiet" ) || Contains( name, "spacey" ) || Contains( name, "break" ) ) mood = "mellow";
        m_moods.push_back( { section.m_time, mood } );
        m_claps.push_back( { section.m_time, Contains( name, "verse" ) || Contains( name, "pre" ) ? "clap" : "noclap" } );
    }
}


std::string Crowd::Mood( double inSeconds ) const
{
    const TimedCueData* mood = VenueTiming::CueAt( m_moods, inSeconds );
    return mood ? mood->m_name : std::string( "normal" );
}


bool Crowd::Clapping( double inSeconds ) const
{
    const TimedCueData* clap = VenueTiming::CueAt( m_claps, inSeconds );
    return clap && clap->m_name == "clap";
}


void Crowd::OnMiss()
{
    m_missDip = std::min( 1.f, m_missDip + 0.35f );
}


void Crowd::OnCheer( float inAmount )
{
    m_cheer = std::max( m_cheer, inAmount );
}


void Crowd::Update( double inSeconds, float inDeltaTime, float inPerformance )
{
    if( m_people.empty() )
    {
        return;
    }
    const std::string mood = Mood( inSeconds );
    const bool clapping = Clapping( inSeconds ) && mood != "intense";
    float target = 0.6f;
    if( mood == "intense" ) target = 1.f;
    else if( mood == "mellow" ) target = 0.25f;
    else if( mood == "realtime" ) target = 0.2f + 0.8f * inPerformance;
    // The player's playing sways every mood a little; pyro sends it up.
    target += 0.2f * ( inPerformance - 0.5f );
    float bonus = 0.f;
    for( float time : m_bonusFx )
    {
        if( time > inSeconds ) break;
        bonus = std::max( bonus, std::exp( -static_cast<float>( inSeconds - time ) / 1.5f ) );
    }
    m_cheer *= std::exp( -inDeltaTime * 0.8f );
    m_missDip *= std::exp( -inDeltaTime * 1.2f );
    target = std::clamp( target + 0.6f * std::max( bonus, m_cheer ) - 0.5f * m_missDip, 0.f, 1.2f );
    m_energy += ( target - m_energy ) * ( 1.f - std::exp( -inDeltaTime * 1.5f ) );
    const bool lightersUp = mood == "mellow";

    double beat = 0.0;
    int measureBeat = 0;
    VenueTiming::BeatAt( m_beats, m_bpm, inSeconds, beat, measureBeat );
    const float t = static_cast<float>( inSeconds );
    ++m_frame;
    UpdateMob( beat, t, m_energy, lightersUp, clapping );

    // The crowd surfer: up at the back, carried to the barricade over six seconds or so.
    if( m_surfProgress < 0.f && m_surfRequested && m_surfer.Root() )
    {
        m_surfProgress = 0.f;
        m_surfX = m_surfCentreX + ( VenueTiming::Noise( static_cast<uint32_t>( ++m_surfCount ), 99u ) - 0.5f ) * 8.f;
    }
    if( m_surfProgress >= 0.f && m_surfer.Root() )
    {
        m_surfProgress += inDeltaTime / 6.5f;
        Transform& surfer = *m_surfer.Root();
        if( m_surfProgress >= 1.f )
        {
            m_surfProgress = -1.f;
            surfer.SetPosition( Vector3( 0.f, -10.f, 0.f ) );
        }
        else
        {
            const float z = m_surfFromZ + ( m_surfToZ - m_surfFromZ ) * m_surfProgress;
            const float bob = 0.12f * std::sin( t * 5.f ) + 0.06f * std::sin( t * 8.3f );
            m_surfPosition = Vector3( m_surfX + 0.6f * std::sin( t * 0.9f ), 2.4f + bob, z );
            // Face down, head toward the stage.
            surfer.SetPosition( m_surfPosition + Vector3( 0.f, 0.f, -0.8f ) );
            surfer.SetRotation( Vector3( 90.f + 8.f * std::sin( t * 3.f ), 0.f, 10.f * std::sin( t * 2.f ) ) );
            Puppet::Pose pose;
            pose.Arms[0].Raise = 150.f + 25.f * std::sin( t * 6.f );
            pose.Arms[1].Raise = 150.f + 25.f * std::sin( t * 6.f + 1.5f );
            pose.Arms[0].Spread = pose.Arms[1].Spread = 30.f;
            pose.Nod = -20.f;
            m_surfer.Apply( pose );
        }
    }
    // The rows further back are posed every second or third frame (in turns) when the frame rate
    // is high enough that they still move at 60 a second or better; at 60 fps everyone is posed
    // every frame, or the back of the room visibly steps. Far figures are small, and posing is
    // most of the crowd's cost.
    m_frameTime += ( std::clamp( inDeltaTime, 0.001f, 0.1f ) - m_frameTime ) * 0.05f;
    const uint32_t spare = static_cast<uint32_t>( std::clamp( ( 1.f / 60.f ) / m_frameTime + 0.15f, 1.f, 3.f ) );
    for( size_t index = 0; index < m_people.size(); ++index )
    {
        Person& person = m_people[index];
        const uint32_t stride = person.Depth > 16.f ? spare : person.Depth > 8.f ? std::min( spare, 2u ) : 1u;
        if( ( m_frame + static_cast<uint32_t>( index ) ) % stride != 0 )
        {
            continue;
        }
        // Under the crowd surfer: hands up holding them.
        bool carrying = false;
        if( m_surfProgress >= 0.f && person.Body.Root() )
        {
            const Vector3 feet = person.Body.Root()->GetPosition();
            const float dx = feet.x - m_surfPosition.x;
            const float dz = feet.z - m_surfPosition.z;
            carrying = dx * dx + dz * dz < 1.3f;
        }
        Puppet::Pose& pose = person.Pose;
        pose = Puppet::Pose();
        // Everyone's a little behind the beat, by their own amount.
        const double myBeat = beat - person.Phase * 0.12;
        const float pulse = Pulse( myBeat );
        const float energy = std::clamp( m_energy * ( 0.55f + 0.7f * person.Enthusiasm ), 0.f, 1.3f );
        const float wobble = std::sin( t * ( 0.7f + person.Phase * 0.5f ) + person.Phase * 20.f );
        pose.Nod = -6.f + ( 2.f + 18.f * energy ) * pulse;
        pose.HeadTurn = 8.f * wobble;
        pose.Side = 3.f * wobble;
        auto& left = pose.Arms[0];
        auto& right = pose.Arms[1];
        left.Raise = right.Raise = 6.f;
        left.Spread = right.Spread = 8.f;
        if( carrying )
        {
            left.Raise = right.Raise = 172.f;
            left.Spread = right.Spread = 12.f;
            left.Elbow = right.Elbow = 15.f + 10.f * wobble;
            pose.Nod = -25.f;
        }
        else if( m_missDip > 0.4f && energy < 0.8f )
        {
            // Disappointed: arms down, leaning back.
            pose.Lean = -6.f * m_missDip;
            pose.Nod = 8.f * m_missDip;
        }
        else if( !lightersUp && person.Item == 2 && energy > 0.7f && person.Enthusiasm > 0.5f )
        {
            // Filming it on their phone.
            right.Raise = 125.f;
            right.Spread = 6.f;
            right.Elbow = 35.f;
            pose.Nod = -4.f;
        }
        else if( lightersUp && person.Item != 0 )
        {
            // One arm up with the light, swaying to the half-time.
            right.Raise = 160.f;
            right.Spread = 12.f;
            right.Elbow = 15.f;
            pose.Side = 9.f * std::sin( static_cast<float>( myBeat ) * kPi * 0.5f );
        }
        else if( clapping && person.Kind != 0 )
        {
            // Hands meeting on the beat, over their heads for the keen ones.
            const float clap = Pulse( myBeat, 5.0 );
            const float raise = person.Enthusiasm > 0.6f ? 150.f : 85.f;
            left.Raise = right.Raise = raise;
            left.Spread = right.Spread = -14.f + 30.f * ( 1.f - clap );
            left.Elbow = right.Elbow = 30.f;
            pose.Crouch = 0.03f * pulse;
        }
        else if( energy > 0.75f )
        {
            // Jumping, hands up.
            if( person.Kind == 0 || person.Kind == 3 || energy > 1.f )
            {
                const double hop = myBeat - std::floor( myBeat );
                pose.Offset.y = 0.32f * person.Enthusiasm * std::max( 0.f, static_cast<float>( std::sin( hop * kPi ) ) );
            }
            else
            {
                pose.Crouch = 0.07f * pulse;
            }
            left.Raise = 150.f + 20.f * pulse;
            right.Raise = 155.f + 20.f * pulse;
            left.Spread = right.Spread = 18.f;
            left.Elbow = right.Elbow = 25.f * ( 1.f - pulse );
            if( person.Kind == 2 )
            {
                // Horns up, one arm.
                left.Raise = 20.f;
                left.Elbow = 60.f;
            }
        }
        else if( energy > 0.4f )
        {
            // Bobbing; the pumpers punch the air on the beat.
            pose.Crouch = 0.05f * pulse * energy;
            if( person.Kind == 1 || ( person.Kind == 0 && person.Enthusiasm > 0.7f ) )
            {
                right.Raise = 120.f + 45.f * pulse;
                right.Spread = 10.f;
                right.Elbow = 70.f * ( 1.f - pulse );
            }
            else if( person.Kind == 2 )
            {
                pose.Side = 7.f * std::sin( static_cast<float>( myBeat ) * kPi * 0.5f );
                left.Raise = right.Raise = 10.f;
            }
        }
        else
        {
            // Standing about.
            left.Elbow = right.Elbow = person.Kind == 3 ? 100.f : 15.f;
            left.Raise = right.Raise = person.Kind == 3 ? 25.f : 4.f;
            pose.Side = 4.f * wobble;
        }
        person.Body.Apply( pose );
        if( person.ItemPiece )
        {
            Transform& item = person.ItemPiece->GetComponent<Transform>();
            const bool filming = !lightersUp && person.Item == 2 && energy > 0.7f && person.Enthusiasm > 0.5f && !carrying;
            if( ( lightersUp && energy <= 1.f ) || filming )
            {
                // At the raised hand (root space; the root carries the figure's scale).
                const glm::vec3 hand = person.Body.Hand( 1 ) / person.Body.Scale();
                item.SetPosition( Vector3( hand + glm::vec3( 0.f, 0.08f, 0.f ) ) );
                const float flicker = person.Item == 1 ? 0.8f + 0.2f * std::sin( t * 23.f + person.Phase * 50.f ) : 1.f;
                // Now and then a photo: a flash for a frame or two.
                const bool flash = filming && VenueTiming::Noise( static_cast<uint32_t>( t * 8.f ), static_cast<uint32_t>( index ) ) < 0.012f;
                const Vector3 glow = person.Item == 1 ? Vector3( 4.f, 1.6f, 0.3f ) * flicker : flash ? Vector3( 40.f, 40.f, 40.f ) : Vector3( 1.6f, 2.f, 3.f );
                VenueKit::SetColor( person.ItemPiece, Vector3( 0.f, 0.f, 0.f ), glow );
            }
            else
            {
                item.SetPosition( Vector3( 0.f, -10.f, 0.f ) );
            }
        }
    }
}


bool Crowd::Occupied( float inX, float inZ ) const
{
    // The posed crowd's rows, widening toward the back as Build lays them out.
    for( const Rows& rows : m_rows )
    {
        const VenuePlan::CrowdArea& area = rows.Area;
        if( inZ > rows.BackZ - 0.4f && inZ < area.MaxZ + 0.4f )
        {
            const float depth = area.MaxZ - inZ;
            const float centre = ( area.MinX + area.MaxX ) * 0.5f;
            if( std::fabs( inX - centre ) < std::min( ( area.MaxX - area.MinX ) * 0.5f, area.FrontHalfWidth + depth * area.Widen ) + 0.4f )
            {
                return true;
            }
        }
    }
    for( const std::array<float, 4>& area : m_keepClear )
    {
        if( inX > area[0] && inX < area[1] && inZ > area[2] && inZ < area[3] )
        {
            return true;
        }
    }
    return false;
}


void Crowd::AddMob( VenueKit& inKit, Transform* inFloor, const VenuePlan::CrowdArea& inArea, int inMax )
{
    // (z0 is the front edge, where the seed starts.)
    const float x0 = inArea.MinX;
    const float x1 = inArea.MaxX;
    const float z0 = inArea.MaxZ;
    const float z1 = inArea.MinZ;
    const float floorY = inArea.FloorY;
    const float spacing = inArea.Spacing;
    const float density = inArea.Density;
    // Figures far enough back that a silhouette and a bob read as a crowd: four or five boxes
    // each, moved as one, so filling a room costs a transform a figure a frame.
    // Two passes over the same spots: count where they'd stand, then thin evenly to inMax, so a
    // cap leaves the area sparser rather than empty at the back.
    const uint32_t firstSeed = static_cast<uint32_t>( m_mob.size() ) * 7919u + static_cast<uint32_t>( std::fabs( z0 * 31.f + floorY * 7.f ) ) + 17u;
    std::vector<std::pair<Vector3, uint32_t>> spots;
    uint32_t seed = firstSeed;
    for( float z = std::max( z0, z1 ); z > std::min( z0, z1 ); z -= spacing * 1.1f )
    {
        for( float x = x0; x <= x1; x += spacing )
        {
            ++seed;
            const float fx = x + ( VenueTiming::Noise( seed, 22u ) - 0.5f ) * spacing * 0.6f;
            const float fz = z + ( VenueTiming::Noise( seed, 23u ) - 0.5f ) * spacing * 0.5f;
            if( VenueTiming::Noise( seed, 21u ) <= density && !Occupied( fx, fz ) )
            {
                spots.push_back( { Vector3( fx, 0.f, fz ), seed } );
            }
        }
    }
    const float keep = spots.empty() ? 0.f : std::min( 1.f, static_cast<float>( std::max( inMax, 0 ) ) / static_cast<float>( spots.size() ) );
    int added = 0;
    for( const auto& [spot, spotSeed] : spots )
    {
        seed = spotSeed;
        if( VenueTiming::Noise( seed, 20u ) >= keep || added >= inMax )
        {
            continue;
        }
        const float fx = spot.x;
        const float fz = spot.z;
        MobFigure figure;
        figure.Base = Vector3( fx, floorY, fz );
        figure.Phase = VenueTiming::Noise( seed, 24u );
        figure.Enthusiasm = 0.2f + 0.7f * VenueTiming::Noise( seed, 25u );
        figure.Jumper = VenueTiming::Noise( seed, 26u ) < 0.45f;
        figure.Root = inKit.Group( "Mob", inFloor, figure.Base );
        if( !figure.Root )
        {
            return;
        }
        Transform* root = &figure.Root->GetComponent<Transform>();
        root->SetRotation( Vector3( 0.f, FacingIn( inArea, fx, fz ) + ( VenueTiming::Noise( seed, 27u ) - 0.5f ) * 20.f, 0.f ) );
        const float height = 0.9f + VenueTiming::Noise( seed, 28u ) * 0.2f;
        const float build = 0.9f + VenueTiming::Noise( seed, 29u ) * 0.25f;
        root->SetScale( Vector3( height * build, height, height * build ) );
        // The body in one piece; the arms hang, and go up as the mood has them (UpdateMob).
        const std::string& skin = VenueKit::Skin( static_cast<uint32_t>( VenueTiming::Noise( seed, 30u ) * 1000.f ) );
        figure.Model = ModelFor( VenueTiming::Noise( seed, 31u ) );
        const People::Person& person = People::kPeople[figure.Model];
        inKit.Part( person.Body, root, "Body", skin );
        for( int side = 0; side < 2; ++side )
        {
            figure.Arms[side] = inKit.Part( person.Arms[side][1], root, "Arm", skin );
            if( figure.Arms[side] )
            {
                Transform& arm = figure.Arms[side]->GetComponent<Transform>();
                arm.SetPosition( Vector3( person.Shoulders[side] ) );
                arm.SetRotation( Quaternion( MobArm( side, false ) ) );
            }
        }
        const float item = VenueTiming::Noise( seed, 33u );
        if( !figure.Jumper && item < 0.35f )
        {
            const bool lighter = item < 0.12f;
            figure.Light = inKit.Box( Vector3( 0.f, -10.f, 0.f ), lighter ? Vector3( 0.05f, 0.08f, 0.05f ) : Vector3( 0.08f, 0.14f, 0.02f ), Vector3( 0.f, 0.f, 0.f ), root,
                lighter ? Vector3( 4.f, 1.6f, 0.3f ) : Vector3( 1.6f, 2.f, 3.f ) );
        }
        m_mob.push_back( figure );
        ++added;
    }
}


void Crowd::UpdateMob( double inBeat, float inSeconds, float inEnergy, bool inLightsUp, bool inClapping )
{
    for( MobFigure& figure : m_mob )
    {
        const double myBeat = inBeat - figure.Phase * 0.15;
        const float pulse = Pulse( myBeat );
        const float energy = std::clamp( inEnergy * ( 0.5f + 0.7f * figure.Enthusiasm ), 0.f, 1.3f );
        Vector3 offset( 0.f, 0.f, 0.f );
        bool armsUp = false;
        bool lightUp = false;
        if( inLightsUp )
        {
            // Swaying to the half-time, the lights up.
            offset.x = 0.07f * std::sin( static_cast<float>( myBeat ) * kPi * 0.5f + figure.Phase * 3.f );
            lightUp = static_cast<bool>( figure.Light );
            armsUp = lightUp;
        }
        else if( inClapping && figure.Enthusiasm > 0.5f )
        {
            armsUp = true;
            offset.y = -0.03f * pulse;
        }
        else if( energy > 0.75f )
        {
            if( figure.Jumper )
            {
                const double hop = myBeat - std::floor( myBeat );
                offset.y = 0.26f * figure.Enthusiasm * std::max( 0.f, static_cast<float>( std::sin( hop * kPi ) ) );
            }
            else
            {
                offset.y = -0.06f * pulse;
            }
            armsUp = true;
        }
        else if( energy > 0.4f )
        {
            offset.y = -0.05f * pulse * energy;
            armsUp = !figure.Jumper && figure.Enthusiasm > 0.6f && pulse > 0.45f;
        }
        else
        {
            offset.x = 0.03f * std::sin( inSeconds * ( 0.6f + figure.Phase * 0.5f ) + figure.Phase * 20.f );
        }
        figure.Root->GetComponent<Transform>().SetPosition( figure.Base + offset );
        if( armsUp != figure.ArmsUp )
        {
            // Both arms for the jumpers, the right for the rest.
            figure.ArmsUp = armsUp;
            for( int side = figure.Jumper ? 0 : 1; side < 2; ++side )
            {
                if( figure.Arms[side] ) figure.Arms[side]->GetComponent<Transform>().SetRotation( Quaternion( MobArm( side, armsUp ) ) );
            }
        }
        if( lightUp != figure.LightUp && figure.Light )
        {
            // In the raised right hand (the root's space, which carries the figure's scale).
            figure.LightUp = lightUp;
            const People::Person& person = People::kPeople[figure.Model];
            const glm::vec3 hand = person.Shoulders[1] + MobArm( 1, true ) * glm::vec3( 0.f, -person.ArmLength - 0.08f, 0.f );
            figure.Light->GetComponent<Transform>().SetPosition( lightUp ? Vector3( hand ) : Vector3( 0.f, -10.f, 0.f ) );
        }
    }
}
