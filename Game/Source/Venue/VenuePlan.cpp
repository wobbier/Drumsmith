#include "Venue/VenuePlan.h"
#include "Venue/VenueLayout.h"
#include <algorithm>
#include <cmath>

namespace
{
    constexpr float kPi = 3.14159265f;

    VenuePlan::CrowdArea Area( VenuePlan::CrowdArea::Kind inType, float inMinX, float inMaxX, float inMinZ, float inMaxZ )
    {
        VenuePlan::CrowdArea area;
        area.Type = inType;
        area.MinX = inMinX;
        area.MaxX = inMaxX;
        area.MinZ = inMinZ;
        area.MaxZ = inMaxZ;
        return area;
    }


    // The cheap figures of the back of the house (Crowd::AddMob), turned a little more toward the
    // stage than the posed rows.
    VenuePlan::CrowdArea Mob( float inMinX, float inMaxX, float inMinZ, float inMaxZ, float inFloorY, float inSpacing, float inDensity, int inHeads )
    {
        VenuePlan::CrowdArea area = Area( VenuePlan::CrowdArea::Kind::Mob, inMinX, inMaxX, inMinZ, inMaxZ );
        area.FloorY = inFloorY;
        area.Spacing = inSpacing;
        area.Density = inDensity;
        area.Heads = inHeads;
        area.Turn = 0.85f;
        return area;
    }
}


VenuePlan VenuePlan::ForStyle( int inStyle )
{
    using namespace VenueLayout;
    VenuePlan plan;
    plan.Style = inStyle;
    for( size_t i = 0; i < plan.Members.size(); ++i )
    {
        plan.Members[i].Feet = kMemberSpots[i];
        plan.Members[i].Yaw = 180.f;
        plan.Members[i].Present = true;
    }
    // The keyboard player angles in toward the band from their corner.
    plan.Members[4].Yaw = 155.f;

    plan.Stage.Height = kStageHeight;
    plan.Stage.HalfWidth = kStageHalfWidth;
    plan.Stage.Depth = kStageDepth;
    plan.Stage.BackWallZ = kBackWallZ;
    plan.Stage.RiserHeight = kRiserHeight;
    plan.Stage.RiserZ = kRiserZ;
    plan.Stage.TrussHeight = kTrussHeight;
    plan.Stage.BarricadeZ = kBarricadeZ;

    // The LED wall over the back of the stage, its lower part the karaoke band, above the
    // drummer's head (the wall spans 3.9-9.9 m).
    Screen wall;
    wall.Centre = Vector3( 0.f, 6.9f, kBackWallZ - 0.05f );
    wall.Width = 12.f;
    wall.Height = 6.f;
    wall.Source = Screen::Feed::Program;
    wall.Seams = true;
    plan.Screens.push_back( wall );
    plan.Lyrics.Present = true;
    plan.Lyrics.Centre = Vector3( 0.f, 4.75f, kBackWallZ - 0.12f );
    plan.Lyrics.Width = 11.f;

    // The posed crowd, from the barricade back: each room holds a different one.
    CrowdArea posed = Area( CrowdArea::Kind::Posed, -kCrowdHalfWidth, kCrowdHalfWidth, kCrowdBackZ, kCrowdFrontZ );
    posed.Heads = 520;
    switch( inStyle )
    {
    case 1:
    {
        // The club: packed to the bar.
        posed.MinX = -11.5f;
        posed.MaxX = 11.5f;
        posed.MinZ = -15.f;
        posed.Heads = 240;
        plan.Crowd.push_back( posed );
        plan.Crowd.push_back( Mob( -12.1f, 12.1f, -14.7f, kCrowdFrontZ, 0.f, 0.56f, 0.85f, 420 ) );
        plan.Bounds.Back = -17.f;
        plan.Bounds.Ceiling = 10.6f;
        plan.Bounds.HalfWidth = 12.5f;
        plan.Bounds.DeskZ = -13.f;
        plan.HazeScale = 1.05f;
        break;
    }
    case 2:
    {
        // The festival: a field full to the delay towers, thinning out past them into the dark.
        posed.MinX = -24.f;
        posed.MaxX = 24.f;
        posed.MinZ = -42.f;
        posed.Heads = 800;
        plan.Crowd.push_back( posed );
        plan.Crowd.push_back( Area( CrowdArea::Kind::Clear, -3.8f, 3.8f, -26.8f, -21.2f ) );
        for( float side : { -1.f, 1.f } )
        {
            for( float z : { -26.f, -40.f } )
            {
                plan.Crowd.push_back( Area( CrowdArea::Kind::Clear, side * 14.f - 0.7f, side * 14.f + 0.7f, z - 0.7f, z + 0.7f ) );
            }
        }
        plan.Crowd.push_back( Mob( -25.f, 25.f, -34.f, kCrowdFrontZ, 0.f, 0.66f, 0.8f, 900 ) );
        plan.Crowd.push_back( Mob( -28.f, 28.f, -50.f, -34.f, 0.f, 0.74f, 0.55f, 450 ) );
        plan.Crowd.push_back( Mob( -30.f, 30.f, -66.f, -50.f, 0.f, 0.85f, 0.32f, 250 ) );
        plan.Bounds.DeskZ = -24.f;
        plan.Bounds.Outdoor = true;
        plan.HazeScale = 0.45f;
        // Screens on towers flanking the stage.
        for( float side : { -1.f, 1.f } )
        {
            Screen screen;
            screen.Centre = Vector3( side * 17.f, 9.5f, 1.f );
            screen.Width = 8.f;
            screen.Height = 4.5f;
            screen.Yaw = side * 10.f;
            screen.Source = Screen::Feed::Stage;
            plan.Screens.push_back( screen );
        }
        break;
    }
    default:
    {
        // The arena: the floor full to the mixing desk and beyond, the stands up the back and
        // along the sides, aisles up the stands.
        plan.Crowd.push_back( posed );
        plan.Crowd.push_back( Area( CrowdArea::Kind::Clear, -3.6f, 3.6f, kArenaDeskZ - 2.6f, kArenaDeskZ + 2.6f ) );
        for( float x : { -14.f, -5.f, 5.f, 14.f } )
        {
            plan.Crowd.push_back( Area( CrowdArea::Kind::Clear, x - 0.5f, x + 0.5f, kArenaBackWallZ, kArenaStandsZ ) );
        }
        plan.Crowd.push_back( Mob( -14.8f, 14.8f, kArenaStandsZ + 0.6f, kCrowdFrontZ, 0.f, 0.62f, 0.8f, 900 ) );
        for( int tier = 0; tier < kArenaTiers; ++tier )
        {
            const float z0 = kArenaStandsZ - kArenaTierDepth * static_cast<float>( tier );
            plan.Crowd.push_back( Mob( -20.8f, 20.8f, z0 - kArenaTierDepth + 0.3f, z0 - 0.35f, kArenaTierRise * static_cast<float>( tier + 1 ), 0.66f, 0.72f - 0.06f * tier, 140 ) );
        }
        for( float side : { -1.f, 1.f } )
        {
            for( int tier = 0; tier < kArenaSideTiers; ++tier )
            {
                const float inner = kArenaSideStandsX + kArenaTierDepth * static_cast<float>( tier ) + 0.35f;
                const float outer = inner + kArenaTierDepth - 0.65f;
                plan.Crowd.push_back( Mob( side < 0.f ? -outer : inner, side < 0.f ? -inner : outer, kArenaStandsZ + 0.3f, -3.5f, kArenaTierRise * static_cast<float>( tier + 1 ), 0.66f, 0.6f, 80 ) );
            }
        }
        plan.Bounds.Back = kArenaBackWallZ;
        plan.Bounds.Ceiling = 18.f;
        plan.Bounds.HalfWidth = 21.f;
        plan.Bounds.DeskZ = kArenaDeskZ;
        // Screens either side of the stage, on posts.
        for( float side : { -1.f, 1.f } )
        {
            Screen screen;
            screen.Centre = Vector3( side * 14.f, 7.2f, 2.f );
            screen.Width = 6.f;
            screen.Height = 3.4f;
            screen.Yaw = side * 16.f;
            screen.Source = Screen::Feed::Stage;
            plan.Screens.push_back( screen );
        }
        break;
    }
    }
    return plan;
}


const VenuePlan::Spot& VenuePlan::SpotOf( int inMember ) const
{
    return Members[static_cast<size_t>( std::clamp( inMember, 0, static_cast<int>( Members.size() ) - 1 ) )];
}


float VenuePlan::CrowdFront() const
{
    float front = -1e9f;
    for( const CrowdArea& area : Crowd )
    {
        if( area.Type == CrowdArea::Kind::Posed ) front = std::max( front, area.MaxZ );
    }
    return front > -1e8f ? front : Stage.BarricadeZ - 0.8f;
}


Vector3 VenuePlan::TurnWith( int inMember, const Vector3& inPoint ) const
{
    const Spot& spot = SpotOf( inMember );
    const float turn = spot.Yaw - 180.f;
    if( turn == 0.f )
    {
        return inPoint;
    }
    // About +y through the feet: +z toward +x for a positive turn (as Transform's yaw).
    const float angle = turn * kPi / 180.f;
    const float c = std::cos( angle );
    const float s = std::sin( angle );
    const Vector3 offset = inPoint - spot.Feet;
    return spot.Feet + Vector3( offset.x * c + offset.z * s, offset.y, -offset.x * s + offset.z * c );
}
