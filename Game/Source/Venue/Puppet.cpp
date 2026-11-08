#include "Venue/Puppet.h"
#include "Venue/VenueKit.h"
#include "Components/Transform.h"
#include <algorithm>
#include <cmath>

namespace
{
    constexpr float kDeg = 3.14159265f / 180.f;

    glm::quat Axis( float inDegrees, const glm::vec3& inAxis )
    {
        return glm::angleAxis( inDegrees * kDeg, inAxis );
    }

    const glm::vec3 kX( 1.f, 0.f, 0.f );
    const glm::vec3 kY( 0.f, 1.f, 0.f );
    const glm::vec3 kZ( 0.f, 0.f, 1.f );
}


glm::quat Puppet::FromTo( const glm::vec3& inFrom, const glm::vec3& inTo )
{
    const glm::vec3 a = glm::normalize( inFrom );
    const glm::vec3 b = glm::normalize( inTo );
    const float d = glm::dot( a, b );
    if( d > 0.99999f )
    {
        return glm::quat( 1.f, 0.f, 0.f, 0.f );
    }
    if( d < -0.99999f )
    {
        glm::vec3 axis = glm::cross( kX, a );
        if( glm::dot( axis, axis ) < 1e-6f ) axis = glm::cross( kZ, a );
        return glm::angleAxis( 3.14159265f, glm::normalize( axis ) );
    }
    const glm::vec3 c = glm::cross( a, b );
    return glm::normalize( glm::quat( 1.f + d, c.x, c.y, c.z ) );
}


void Puppet::PlacePiece( const EntityHandle& inPiece, const glm::vec3& inCentre, const glm::quat& inRotation )
{
    if( !inPiece )
    {
        return;
    }
    Transform& transform = inPiece->GetComponent<Transform>();
    transform.SetPosition( Vector3( inCentre ) );
    transform.SetRotation( Quaternion( inRotation ) );
}


void Puppet::PlaceBone( const EntityHandle& inPiece, const glm::vec3& inFrom, const glm::vec3& inTo )
{
    const glm::vec3 span = inTo - inFrom;
    if( glm::dot( span, span ) < 1e-8f )
    {
        PlacePiece( inPiece, inFrom, glm::quat( 1.f, 0.f, 0.f, 0.f ) );
        return;
    }
    PlacePiece( inPiece, ( inFrom + inTo ) * 0.5f, FromTo( kY, span ) );
}


Transform* Puppet::Root() const
{
    return m_root ? &m_root->GetComponent<Transform>() : nullptr;
}


void Puppet::Build( VenueKit& inKit, Transform* inParent, const Vector3& inFeet, float inYawDegrees, const Look& inLook, bool inDetailed )
{
    m_look = inLook;
    m_detailed = inDetailed;
    m_root = inKit.Group( "Puppet", inParent, inFeet );
    if( !m_root )
    {
        return;
    }
    Transform& root = m_root->GetComponent<Transform>();
    root.SetRotation( Vector3( 0.f, inYawDegrees, 0.f ) );
    root.SetScale( Vector3( inLook.Height * inLook.Build, inLook.Height, inLook.Height * inLook.Build ) );

    using Shape = Moonlight::MeshType;
    const Vector3 zero( 0.f, 0.f, 0.f );
    m_torso = inKit.Piece( Shape::Cube, zero, Vector3( 0.4f, 0.56f, 0.22f ), inLook.Shirt, &root );
    m_head = inKit.Piece( Shape::Sphere, zero, Vector3( 0.23f, 0.27f, 0.25f ), inLook.Skin, &root );
    m_hair = inKit.Piece( Shape::Cube, zero, inLook.LongHair ? Vector3( 0.24f, 0.4f, 0.07f ) : Vector3( 0.25f, 0.1f, 0.25f ), inLook.Hair, &root );
    for( int side = 0; side < 2; ++side )
    {
        m_upperArms[side] = inKit.Piece( Shape::Capsule, zero, inDetailed ? Vector3( 0.1f, kUpperArm + 0.06f, 0.1f ) : Vector3( 0.1f, kUpperArm + kForearm + 0.04f, 0.1f ), inDetailed ? inLook.Shirt : inLook.Skin, &root );
    }
    if( !inDetailed )
    {
        // The crowd: a torso, a head with hair, arms in one piece, and legs as one block.
        m_legs = inKit.Piece( Shape::Cube, zero, Vector3( 0.32f, 0.92f, 0.2f ), inLook.Pants, &root );
        return;
    }
    m_pelvis = inKit.Piece( Shape::Cube, zero, Vector3( 0.36f, 0.2f, 0.22f ), inLook.Pants, &root );
    m_mouth = inKit.Piece( Shape::Cube, zero, Vector3( 0.07f, 0.02f, 0.03f ), Vector3( 0.15f, 0.03f, 0.03f ), &root );
    // A face: eyes, and a cap of hair over the crown for the long-haired.
    for( int side = 0; side < 2; ++side )
    {
        m_eyes[side] = inKit.Piece( Shape::Sphere, zero, Vector3( 0.035f, 0.035f, 0.02f ), Vector3( 0.02f, 0.02f, 0.02f ), &root );
    }
    if( inLook.LongHair )
    {
        m_cap = inKit.Piece( Shape::Sphere, zero, Vector3( 0.25f, 0.16f, 0.27f ), inLook.Hair, &root );
    }
    for( int side = 0; side < 2; ++side )
    {
        m_forearms[side] = inKit.Piece( Shape::Capsule, zero, Vector3( 0.085f, kForearm + 0.04f, 0.085f ), inLook.Skin, &root );
        m_handPieces[side] = inKit.Piece( Shape::Sphere, zero, Vector3( 0.09f, 0.1f, 0.07f ), inLook.Skin, &root );
        m_thighs[side] = inKit.Piece( Shape::Capsule, zero, Vector3( 0.15f, kThigh + 0.08f, 0.15f ), inLook.Pants, &root );
        m_shins[side] = inKit.Piece( Shape::Capsule, zero, Vector3( 0.12f, kShin + 0.06f, 0.12f ), inLook.Pants, &root );
        m_feet[side] = inKit.Piece( Shape::Cube, zero, Vector3( 0.11f, 0.08f, 0.27f ), inLook.Shoes, &root );
    }
}


glm::vec3 Puppet::Reach( const glm::vec3& inShoulder, const Arm& inArm, const glm::quat& inSpine, int inSide, glm::vec3& outElbow ) const
{
    // Puppet space is unscaled; the figure's lengths are, so targets are divided by the scale.
    const float l1 = kUpperArm;
    const float l2 = kForearm;
    if( inArm.Reach )
    {
        const glm::vec3 target = inArm.Target;
        glm::vec3 toTarget = target - inShoulder;
        float distance = glm::length( toTarget );
        if( distance < 1e-4f )
        {
            toTarget = glm::vec3( 0.f, -1.f, 0.f );
            distance = 1e-4f;
        }
        const glm::vec3 dir = toTarget / distance;
        const float d = std::clamp( distance, std::fabs( l1 - l2 ) + 0.01f, l1 + l2 - 0.002f );
        const float a = ( l1 * l1 - l2 * l2 + d * d ) / ( 2.f * d );
        const float h = std::sqrt( std::max( 0.f, l1 * l1 - a * a ) );
        glm::vec3 pole = inArm.Pole - dir * glm::dot( inArm.Pole, dir );
        if( glm::dot( pole, pole ) < 1e-6f )
        {
            pole = glm::cross( dir, kX );
        }
        pole = glm::normalize( pole );
        outElbow = inShoulder + dir * a + pole * h;
        return inShoulder + dir * d;
    }
    const float s = inSide == 0 ? -1.f : 1.f;
    const glm::quat upper = inSpine * Axis( s * inArm.Spread, kZ ) * Axis( -inArm.Raise, kX );
    outElbow = inShoulder + upper * glm::vec3( 0.f, -l1, 0.f );
    if( !m_detailed )
    {
        // One-piece arms: straight, but shortened as the elbow bends.
        const float bend = std::cos( std::clamp( inArm.Elbow, 0.f, 150.f ) * kDeg * 0.5f );
        return inShoulder + upper * glm::vec3( 0.f, -( l1 + l2 ) * bend, 0.f );
    }
    const glm::quat fore = upper * Axis( -inArm.Elbow, kX );
    return outElbow + fore * glm::vec3( 0.f, -l2, 0.f );
}


void Puppet::Apply( const Pose& inPose )
{
    if( !m_root )
    {
        return;
    }
    // Joint positions in the root's (scaled) space: the figure is built for a scale of 1.
    const float invScale = 1.f / std::max( 0.01f, m_look.Height );
    const glm::vec3 offset = inPose.Offset * invScale;
    const float hipHeight = inPose.Seated ? inPose.SeatHeight * invScale : 0.95f - inPose.Crouch;
    const glm::vec3 pelvis = glm::vec3( 0.f, hipHeight, 0.f ) + offset;
    const glm::quat hips = Axis( inPose.Turn * 0.3f, kY );
    m_spine = hips * Axis( inPose.Turn * 0.7f, kY ) * Axis( inPose.Lean, kX ) * Axis( -inPose.Side, kZ );
    const glm::vec3 spineBase = pelvis + glm::vec3( 0.f, 0.07f, 0.f );
    constexpr float kSpine = 0.56f;
    m_chest = spineBase + m_spine * glm::vec3( 0.f, kSpine * 0.65f, 0.04f );
    PlacePiece( m_torso, spineBase + m_spine * glm::vec3( 0.f, kSpine * 0.5f, 0.f ), m_spine );
    const glm::vec3 neck = spineBase + m_spine * glm::vec3( 0.f, kSpine + 0.02f, 0.f );
    const glm::quat head = m_spine * Axis( inPose.HeadTurn, kY ) * Axis( inPose.Nod, kX ) * Axis( -inPose.HeadTilt, kZ );
    m_headPos = neck + head * glm::vec3( 0.f, 0.15f, 0.01f );
    PlacePiece( m_head, m_headPos, head );
    if( m_look.LongHair )
    {
        // Hanging down the back from the crown, so a headbang throws it about.
        PlacePiece( m_hair, neck + head * glm::vec3( 0.f, 0.1f, -0.115f ), head * Axis( -10.f, kX ) );
        PlacePiece( m_cap, neck + head * glm::vec3( 0.f, 0.235f, -0.015f ), head );
    }
    else
    {
        PlacePiece( m_hair, neck + head * glm::vec3( 0.f, 0.26f, -0.015f ), head );
    }
    for( int side = 0; side < 2; ++side )
    {
        PlacePiece( m_eyes[side], neck + head * glm::vec3( side == 0 ? -0.045f : 0.045f, 0.165f, 0.112f ), head );
    }
    if( m_mouth )
    {
        const float open = std::clamp( inPose.Mouth, 0.f, 1.f );
        PlacePiece( m_mouth, neck + head * glm::vec3( 0.f, 0.08f, 0.118f ), head );
        m_mouth->GetComponent<Transform>().SetScale( VenueKit::ScaleFor( Moonlight::MeshType::Cube, Vector3( 0.06f + 0.02f * open, 0.012f + 0.06f * open, 0.03f ) ) );
    }

    for( int side = 0; side < 2; ++side )
    {
        const float s = side == 0 ? -1.f : 1.f;
        m_shoulders[side] = spineBase + m_spine * glm::vec3( s * 0.215f, kSpine - 0.07f, 0.f );
        glm::vec3 elbow;
        Arm arm = inPose.Arms[side];
        if( arm.Reach )
        {
            arm.Target = arm.Target * invScale;
        }
        m_hands[side] = Reach( m_shoulders[side], arm, m_spine, side, elbow );
        if( m_detailed )
        {
            PlaceBone( m_upperArms[side], m_shoulders[side], elbow );
            PlaceBone( m_forearms[side], elbow, m_hands[side] );
            const glm::vec3 wrist = glm::normalize( m_hands[side] - elbow );
            PlacePiece( m_handPieces[side], m_hands[side] + wrist * 0.04f, FromTo( kY, wrist ) );
        }
        else
        {
            PlaceBone( m_upperArms[side], m_shoulders[side], m_hands[side] );
        }
        m_hands[side] = m_hands[side] * m_look.Height;
        m_shoulders[side] = m_shoulders[side] * m_look.Height;
    }
    m_chest *= m_look.Height;
    m_spineBase = spineBase * m_look.Height;
    m_headPos *= m_look.Height;

    if( !m_detailed )
    {
        // Legs from the feet (which leave the floor in a jump) to the hips.
        const float legTop = pelvis.y + 0.05f;
        const float legLength = std::max( 0.3f, legTop - offset.y );
        PlacePiece( m_legs, glm::vec3( offset.x, offset.y + legLength * 0.5f, offset.z ), hips );
        m_legs->GetComponent<Transform>().SetScale( VenueKit::ScaleFor( Moonlight::MeshType::Cube, Vector3( 0.32f, legLength, 0.2f ) ) );
        return;
    }
    PlacePiece( m_pelvis, pelvis, hips );
    for( int side = 0; side < 2; ++side )
    {
        const float s = side == 0 ? -1.f : 1.f;
        Leg leg = inPose.Legs[side];
        if( inPose.Seated )
        {
            leg.Lift = std::max( leg.Lift, 80.f );
            leg.Knee = std::max( leg.Knee, 85.f );
        }
        else if( inPose.Crouch > 0.f )
        {
            // Bend the knees to drop the hips: thigh forward, shin back, by the same angle.
            const float drop = std::clamp( inPose.Crouch / ( kThigh + kShin ), 0.f, 0.9f );
            const float angle = std::acos( 1.f - drop ) / kDeg;
            leg.Lift += angle;
            leg.Knee += angle * 2.f;
        }
        const glm::vec3 hip = pelvis + hips * glm::vec3( s * 0.1f, -0.06f, 0.f );
        const glm::quat thigh = hips * Axis( s * leg.Spread, kZ ) * Axis( -leg.Lift, kX );
        const glm::vec3 knee = hip + thigh * glm::vec3( 0.f, -kThigh, 0.f );
        const glm::quat shin = thigh * Axis( leg.Knee, kX );
        const glm::vec3 ankle = knee + shin * glm::vec3( 0.f, -kShin, 0.f );
        PlaceBone( m_thighs[side], hip, knee );
        PlaceBone( m_shins[side], knee, ankle );
        const glm::quat foot = hips * Axis( leg.Toe, kX );
        PlacePiece( m_feet[side], ankle + foot * glm::vec3( 0.f, -0.03f, 0.07f ), foot );
    }
}
