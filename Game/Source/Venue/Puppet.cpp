#include "Venue/Puppet.h"
#include "Venue/People.generated.h"
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


void Puppet::Build( VenueKit& inKit, Transform* inParent, const Vector3& inFeet, float inYawDegrees, const Look& inLook )
{
    m_look = inLook;
    m_root = inKit.Group( "Puppet", inParent, inFeet );
    if( !m_root )
    {
        return;
    }
    Transform& root = m_root->GetComponent<Transform>();
    root.SetRotation( Vector3( 0.f, inYawDegrees, 0.f ) );
    root.SetScale( Vector3( inLook.Height * inLook.Build, inLook.Height, inLook.Height * inLook.Build ) );

    const int detail = inLook.Far ? 1 : 0;
    m_person = &People::kPeople[std::clamp( inLook.Model, 0, People::kCount - 1 )];
    const std::string& skin = VenueKit::Skin( inLook.Skin );
    m_legs = inKit.Part( m_person->Legs[detail], &root, "Legs", skin );
    m_torso = inKit.Part( m_person->Torso[detail], &root, "Torso", skin );
    m_head = inKit.Part( m_person->Head[detail], &root, "Head", skin );
    for( int side = 0; side < 2; ++side )
    {
        m_arms[side] = inKit.Part( m_person->Arms[side][detail], &root, "Arm", skin );
    }
}


void Puppet::Apply( const Pose& inPose )
{
    if( !m_root || !m_person )
    {
        return;
    }
    // Joint positions in the root's (scaled) space: the figure is built for a scale of 1. Each
    // piece turns about its own pivot: the legs at the feet, the torso at the hips, the head at
    // the neck, an arm at its shoulder.
    const float invScale = 1.f / std::max( 0.01f, m_look.Height );
    const glm::vec3 offset = inPose.Offset * invScale;
    const glm::vec3 hips = m_person->Hips + glm::vec3( 0.f, -inPose.Crouch, 0.f ) + offset;
    const glm::quat turn = Axis( inPose.Turn * 0.3f, kY );
    const glm::quat spine = turn * Axis( inPose.Turn * 0.7f, kY ) * Axis( inPose.Lean, kX ) * Axis( -inPose.Side, kZ );
    // The legs stay as they are (feet that leave the floor in a jump); a crouch sinks the torso
    // into them.
    PlacePiece( m_legs, offset, turn );
    PlacePiece( m_torso, hips, spine );
    const glm::quat head = spine * Axis( inPose.HeadTurn, kY ) * Axis( inPose.Nod, kX ) * Axis( -inPose.HeadTilt, kZ );
    PlacePiece( m_head, hips + spine * ( m_person->Neck - m_person->Hips ), head );

    for( int side = 0; side < 2; ++side )
    {
        // Rigid arms: straight, but shortened as the elbow bends.
        const float s = side == 0 ? -1.f : 1.f;
        const Arm& arm = inPose.Arms[side];
        const glm::vec3 shoulder = hips + spine * ( m_person->Shoulders[side] - m_person->Hips );
        // Spread first, then the raise about the shoulders' line: an arm that's out to the side
        // stays out as it goes up (the other order swung raised arms in across each other).
        const glm::quat swing = spine * Axis( -arm.Raise, kX ) * Axis( s * arm.Spread, kZ );
        const float bend = std::cos( std::clamp( arm.Elbow, 0.f, 150.f ) * kDeg * 0.5f );
        PlacePiece( m_arms[side], shoulder, swing );
        if( m_arms[side] )
        {
            m_arms[side]->GetComponent<Transform>().SetScale( Vector3( 1.f, bend, 1.f ) );
        }
        m_hands[side] = ( shoulder + swing * glm::vec3( 0.f, -m_person->ArmLength * bend, 0.f ) ) * m_look.Height;
    }
}
