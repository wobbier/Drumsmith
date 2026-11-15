#include "Venue/Performer.h"
#include "Venue/Puppet.h"
#include "Venue/VenueKit.h"
#include "Animation/IKSolver.h"
#include "Components/Graphics/Mesh.h"
#include "Components/Graphics/Model.h"
#include "Components/Transform.h"
#include "Graphics/ModelResource.h"
#include "Graphics/Texture.h"
#include "Materials/StandardMaterial.h"
#include "Resource/ResourceCache.h"
#include "CLog.h"
#include "Path.h"
#include <algorithm>
#include <cmath>
#include <glm/mat3x3.hpp>

namespace
{
    constexpr float kDeg = 3.14159265f / 180.f;
    // How far the hand bends from the forearm's line, degrees.
    constexpr float kWristLimit = 70.f;
    // The palm's centre under the hand bone, metres: where a stick or a mic sits in the fist.
    constexpr float kPalmDepth = 0.045f;

    const glm::quat kIdentity( 1.f, 0.f, 0.f, 0.f );
    const glm::vec3 kX( 1.f, 0.f, 0.f );
    const glm::vec3 kY( 0.f, 1.f, 0.f );
    const glm::vec3 kZ( 0.f, 0.f, 1.f );

    // Rigify's human: the bones posed here, in Performer::Centre and Performer::Limb order. Limbs
    // take a ".L" or ".R".
    const char* const kCentreNames[] = { "spine", "spine.001", "spine.002", "spine.003", "spine.004", "spine.005", "spine.006" };
    const char* const kLimbNames[] = {
        "upper_arm", "forearm", "hand",
        "f_index.01", "f_index.02", "f_index.03", "f_middle.01", "f_middle.02", "f_middle.03", "thumb.01", "thumb.02", "thumb.03",
        "thigh", "shin", "foot", "toe",
    };
    const char* const kSides[] = { ".L", ".R" };
    // The posed bone each limb bone hangs from: one of its own limb (0 and up), or of the spine
    // (-1 - its Centre: the arm from the ribs, past the collar bone; the leg from the hips).
    constexpr int kLimbAnchors[] = {
        -1 - 3, 0, 1,
        2, 3, 4, 2, 6, 7, 2, 9, 10,
        -1 - 0, 12, 13, 14,
    };
    // Each finger bone's bend at a full fist, degrees: index, the other fingers, thumb.
    constexpr float kCurl[9] = { 70.f, 85.f, 55.f, 70.f, 85.f, 55.f, 30.f, 30.f, 25.f };

    glm::quat Axis( float inDegrees, const glm::vec3& inAxis )
    {
        return glm::angleAxis( inDegrees * kDeg, inAxis );
    }

    // A fraction of a rotation.
    glm::quat Part( const glm::quat& inRotation, float inFraction )
    {
        return glm::slerp( kIdentity, inRotation, inFraction );
    }

    // Whether two poses put everything but the arms (and the mouth) in the same place.
    bool SameStance( const Performer::Pose& inA, const Performer::Pose& inB )
    {
        bool same = inA.Offset == inB.Offset && inA.Crouch == inB.Crouch && inA.Lean == inB.Lean && inA.Side == inB.Side && inA.Turn == inB.Turn
            && inA.Nod == inB.Nod && inA.HeadTurn == inB.HeadTurn && inA.HeadTilt == inB.HeadTilt && inA.Seated == inB.Seated && inA.SeatHeight == inB.SeatHeight;
        for( int side = 0; side < 2 && same; ++side )
        {
            const Performer::Leg& a = inA.Legs[side];
            const Performer::Leg& b = inB.Legs[side];
            same = a.Spread == b.Spread && a.Toe == b.Toe && a.Reach == b.Reach && a.Target == b.Target && a.Pole == b.Pole;
        }
        return same;
    }
}


Transform* Performer::Root() const
{
    return m_root ? &m_root->GetComponent<Transform>() : nullptr;
}


void Performer::Build( VenueKit& inKit, Transform* inParent, const Vector3& inFeet, float inYawDegrees, const Look& inLook )
{
    m_look = inLook;
    m_skin = inKit.SkinTexture( inLook.TexturePath );
    m_root = inKit.Group( "Performer", inParent, inFeet );
    if( !m_root )
    {
        return;
    }
    Transform& root = m_root->GetComponent<Transform>();
    root.SetRotation( Vector3( 0.f, inYawDegrees, 0.f ) );
    root.SetScale( Vector3( inLook.Height, inLook.Height, inLook.Height ) );
    m_mouth = inKit.Piece( Moonlight::MeshType::Cube, Vector3( 0.f, 0.f, 0.f ), Vector3( 0.05f, 0.006f, 0.012f ), Vector3( 0.09f, 0.02f, 0.02f ), &root );
    if( m_mouth )
    {
        m_mouth->GetComponent<Transform>().SetScale( Vector3( 0.001f, 0.001f, 0.001f ) );
    }
    m_body = inKit.Group( "Body", &root );
    if( !m_body )
    {
        return;
    }
    // Loaded here rather than in the background, so the skeleton is there to pose from the first
    // frame (the venue is built while the song loads).
    SharedPtr<ModelResource> resource = ResourceCache::GetInstance().Get<ModelResource>( Path( inLook.ModelPath ) );
    if( !resource || resource->HasLoadFailed() )
    {
        YIKES_FMT( "Performer: no model at %s", inLook.ModelPath.c_str() );
        m_bindFailed = true;
        return;
    }
    Model& model = m_body->AddComponent<Model>( inLook.ModelPath );
    if( model.IsReady() )
    {
        Bind( model );
    }
}


bool Performer::Bind( Model& inModel )
{
    const auto find = [&inModel]( const std::string& inName, Bone& outBone ) {
        outBone.Index = inModel.FindNode( inName );
        outBone.Node = inModel.GetNodeTransform( outBone.Index );
        if( !outBone.Node )
        {
            YIKES_FMT( "Performer: %s has no bone '%s'", inModel.GetModelPath().GetLocalPathString().c_str(), inName.c_str() );
        }
        return outBone.Node != nullptr;
    };
    bool complete = inModel.IsCompact();
    for( int i = 0; i < kCentreCount; ++i )
    {
        m_bones[i].Anchor = i - 1;
        complete = find( kCentreNames[i], m_bones[i] ) && complete;
    }
    for( int side = 0; side < 2; ++side )
    {
        for( int i = 0; i < kLimbCount; ++i )
        {
            Bone& bone = Of( side, static_cast<Limb>( i ) );
            bone.Anchor = kLimbAnchors[i] >= 0 ? kCentreCount + side * kLimbCount + kLimbAnchors[i] : -1 - kLimbAnchors[i];
            complete = find( std::string( kLimbNames[i] ) + kSides[side], bone ) && complete;
        }
    }
    if( !complete )
    {
        m_bindFailed = true;
        return false;
    }

    // Which way the model faces, from its feet; the body is turned so that's the performer's +z.
    glm::vec3 forward( 0.f );
    for( int side = 0; side < 2; ++side )
    {
        forward += Of( side, Toe ).Node->GetWorldPosition().InternalVector - Of( side, Foot ).Node->GetWorldPosition().InternalVector;
    }
    forward.y = 0.f;
    m_facing = glm::dot( forward, forward ) > 1e-10f ? glm::angleAxis( -std::atan2( forward.x, forward.z ), kY ) : kIdentity;
    m_body->GetComponent<Transform>().SetRotation( Quaternion( m_facing ) );

    // The bind pose, in performer space; then each bone as it sits on its anchor.
    for( Bone& bone : m_bones )
    {
        bone.BindLocal = bone.Node->GetRotation().InternalQuat;
        bone.BindWorld = glm::normalize( m_facing * bone.Node->GetWorldRotation().InternalQuat );
        bone.BindPosition = m_facing * bone.Node->GetWorldPosition().InternalVector;
        bone.World = bone.BindWorld;
        bone.Position = bone.BindPosition;
    }
    for( Bone& bone : m_bones )
    {
        Transform* parent = bone.Node->GetParentTransform();
        const glm::quat parentWorld = parent ? glm::normalize( m_facing * parent->GetWorldRotation().InternalQuat ) : m_facing;
        if( bone.Anchor < 0 )
        {
            m_hipsParent = parentWorld;
            continue;
        }
        const Bone& anchor = m_bones[bone.Anchor];
        const glm::quat toAnchor = glm::conjugate( anchor.BindWorld );
        bone.Rest = toAnchor * bone.BindWorld;
        bone.ParentRest = toAnchor * parentWorld;
        bone.Offset = toAnchor * ( bone.BindPosition - anchor.BindPosition );
    }

    for( int side = 0; side < 2; ++side )
    {
        // The hand: T-posed, so its palm faces the floor and its fingers carry on along the arm.
        const glm::vec3 wrist = Of( side, Wrist ).BindPosition;
        const glm::vec3 knuckles = ( Of( side, Index1 ).BindPosition + Of( side, Middle1 ).BindPosition ) * 0.5f;
        m_fingers[side] = glm::normalize( knuckles - wrist );
        m_palm[side] = glm::normalize( -kY + m_fingers[side] * m_fingers[side].y );
        m_grip[side] = m_fingers[side] * ( glm::length( knuckles - wrist ) * 0.7f ) + m_palm[side] * kPalmDepth;
        m_curlAxis[side] = glm::normalize( glm::cross( m_fingers[side], m_palm[side] ) );
        m_thumbAxis[side] = glm::normalize( glm::cross( Of( side, Thumb2 ).BindPosition - Of( side, Thumb1 ).BindPosition, m_palm[side] ) );
    }
    m_upperArm = glm::length( Of( 0, Forearm ).Offset );
    m_forearm = glm::length( Of( 0, Wrist ).Offset );
    m_leg = glm::length( Of( 0, Shin ).Offset ) + glm::length( Of( 0, Foot ).Offset );

    // The FBX names no texture and imports grey: its UVs index the atlas.
    const SharedPtr<Moonlight::Texture>& texture = m_skin;
    for( Model::RenderPart& part : inModel.GetRenderParts() )
    {
        Mesh& mesh = *part.Renderer;
        // Animated performers cast into the same shadow maps as the stage and props.
        mesh.CastShadows = true;
        if( !mesh.MeshMaterial )
        {
            continue;
        }
        mesh.MeshMaterial->SetDiffuseColor( Vector3( 1.f, 1.f, 1.f ) );
        if( texture )
        {
            mesh.MeshMaterial->SetTexture( Moonlight::TextureType::Diffuse, texture );
        }
        if( StandardMaterial* material = dynamic_cast<StandardMaterial*>( mesh.MeshMaterial.get() ) )
        {
            material->SetRoughness( 0.8f );
        }
    }
    m_bound = true;
    m_stood = false;
    return true;
}


bool Performer::Ready()
{
    Model* model = m_body ? m_body->TryGetComponent<Model>() : nullptr;
    if( !model || !model->IsReady() || m_bindFailed || !( m_bound || Bind( *model ) ) )
    {
        return false;
    }
    // The model's nodes, found again: a reloaded model rebuilds them, back in its bind pose.
    bool ready = true;
    for( Bone& bone : m_bones )
    {
        Transform* node = model->GetNodeTransform( bone.Index );
        m_stood = m_stood && node == bone.Node;
        bone.Node = node;
        ready = ready && node;
    }
    return ready;
}


void Performer::Turn( Bone& ioBone, const glm::quat& inWorld )
{
    ioBone.World = inWorld;
    if( ioBone.Anchor < 0 )
    {
        ioBone.Node->SetRotation( Quaternion( glm::normalize( glm::conjugate( m_hipsParent ) * inWorld ) ) );
        return;
    }
    const Bone& anchor = m_bones[ioBone.Anchor];
    ioBone.Position = anchor.Position + anchor.World * ioBone.Offset;
    ioBone.Node->SetRotation( Quaternion( glm::normalize( glm::conjugate( anchor.World * ioBone.ParentRest ) * inWorld ) ) );
}


void Performer::Rest( Bone& ioBone )
{
    const Bone& anchor = m_bones[ioBone.Anchor];
    ioBone.World = anchor.World * ioBone.Rest;
    ioBone.Position = anchor.Position + anchor.World * ioBone.Offset;
    ioBone.Node->SetRotation( Quaternion( ioBone.BindLocal ) );
}


void Performer::Solve( Bone& ioRoot, Bone& ioMid, Bone& ioTip, const glm::vec3& inTarget, const glm::vec3& inPole )
{
    const IK::TwoBoneSolution solution = IK::SolveTwoBone( Vector3( ioRoot.Position ), Vector3( ioMid.Position ), Vector3( ioTip.Position ), Vector3( inTarget ), Vector3( inPole ), true );
    Turn( ioRoot, solution.RootDelta.InternalQuat * ioRoot.World );
    Turn( ioMid, solution.MidDelta.InternalQuat * ( ioRoot.World * ioMid.Rest ) );
    Rest( ioTip );
}


glm::quat Performer::TurnHand( int inSide, const glm::quat& inFollow, const Arm& inArm, const glm::vec3& inForearm ) const
{
    // inFollow: the hand's turn from its bind pose when it just follows the forearm.
    const bool aimed = glm::dot( inArm.Fingers, inArm.Fingers ) > 1e-8f;
    const bool faced = glm::dot( inArm.Palm, inArm.Palm ) > 1e-8f;
    if( !aimed && !faced )
    {
        return inFollow;
    }
    // The wrist only bends so far from the forearm's line.
    glm::vec3 fingers = aimed ? glm::normalize( inArm.Fingers ) : inFollow * m_fingers[inSide];
    fingers = IK::LimitDirection( Vector3( inForearm ), Vector3( fingers ), kWristLimit ).InternalVector;
    glm::vec3 palm = faced ? inArm.Palm : inFollow * m_palm[inSide];
    palm -= fingers * glm::dot( palm, fingers );
    if( glm::dot( palm, palm ) < 1e-8f )
    {
        // Asked to face along the fingers: keep what the arm gave it.
        palm = inFollow * m_palm[inSide];
        palm -= fingers * glm::dot( palm, fingers );
        if( glm::dot( palm, palm ) < 1e-8f )
        {
            return inFollow;
        }
    }
    palm = glm::normalize( palm );
    // The rotation taking the bind pose's fingers and palm to these.
    const glm::mat3 from( m_fingers[inSide], m_palm[inSide], glm::cross( m_fingers[inSide], m_palm[inSide] ) );
    const glm::mat3 to( fingers, palm, glm::cross( fingers, palm ) );
    return glm::normalize( glm::quat_cast( to * glm::transpose( from ) ) );
}


void Performer::CurlFingers( int inSide, float inGrip )
{
    const float grip = std::clamp( inGrip, 0.f, 1.f );
    for( int i = 0; i < 9; ++i )
    {
        const Bone& bone = Of( inSide, static_cast<Limb>( Index1 + i ) );
        const glm::vec3& axis = i < 6 ? m_curlAxis[inSide] : m_thumbAxis[inSide];
        // The axis in the bone's own space, so the curl follows wherever the hand has turned.
        bone.Node->SetRotation( Quaternion( bone.BindLocal * glm::angleAxis( kCurl[i] * grip * kDeg, glm::conjugate( bone.BindWorld ) * axis ) ) );
    }
}


void Performer::PoseArm( int inSide, const Arm& inArm, float inInvScale )
{
    const float s = inSide == 0 ? -1.f : 1.f;
    Bone& upper = Of( inSide, UpperArm );
    Bone& fore = Of( inSide, Forearm );
    Bone& hand = Of( inSide, Wrist );
    Rest( upper );
    Rest( fore );
    Rest( hand );
    const glm::vec3 shoulder = upper.Position;
    const glm::quat fromBind = glm::conjugate( hand.BindWorld );

    if( !inArm.Reach )
    {
        // By angles: the elbow and wrist they put the arm at, reached with the elbow as the pole.
        // Spread first, then the raise about the shoulders' line: an arm that's out to the side
        // stays out as it goes up (the other order swung raised arms in across each other).
        const glm::quat swing = m_spine * Axis( -inArm.Raise, kX ) * Axis( s * inArm.Spread, kZ );
        const glm::vec3 elbow = shoulder + swing * glm::vec3( 0.f, -m_upperArm, 0.f );
        const glm::vec3 wrist = elbow + swing * Axis( -inArm.Elbow, kX ) * glm::vec3( 0.f, -m_forearm, 0.f );
        Solve( upper, fore, hand, wrist, elbow );
    }
    else
    {
        // The palm's centre is ahead of the wrist and under it, so where the wrist goes depends
        // on how the hand turns: solve for a straight wrist, see how the hand turns, then solve
        // again for the wrist that puts the palm on its mark.
        glm::vec3 target = inArm.Target * inInvScale;
        // Instrument reaches can cross the chest (especially crossed hi-hat strokes). Keep
        // the wrist in front of the torso rather than pulling the forearm through the ribs.
        if( inArm.ClearTorso )
        {
            const glm::vec3 local = glm::conjugate( m_spine ) * ( target - shoulder );
            if( s * local.x < 0.08f )
            {
                const float forward = std::max( local.z, 0.15f * inInvScale );
                target = shoulder + m_spine * glm::vec3( local.x, local.y, forward );
            }
        }
        const glm::vec3 pole = shoulder + ( glm::dot( inArm.Pole, inArm.Pole ) > 1e-8f ? glm::normalize( inArm.Pole ) : -kY );
        const glm::vec3 reach = target - shoulder;
        const float distance = glm::length( reach );
        glm::vec3 wrist = distance > 1e-4f ? target - reach * ( glm::length( m_grip[inSide] ) / distance ) : target;
        for( int pass = 0; pass < 2; ++pass )
        {
            if( pass > 0 )
            {
                Rest( upper );
                Rest( fore );
                Rest( hand );
            }
            Solve( upper, fore, hand, wrist, pole );
            wrist = target - TurnHand( inSide, hand.World * fromBind, inArm, glm::normalize( hand.Position - fore.Position ) ) * m_grip[inSide];
        }
    }

    const glm::vec3 along = glm::normalize( hand.Position - fore.Position );
    const glm::quat follow = hand.World * fromBind;
    const glm::quat turn = TurnHand( inSide, follow, inArm, along );
    // Half of the hand's twist about the forearm goes into the forearm, as a real one's does.
    const glm::quat extra = turn * glm::conjugate( follow );
    glm::quat twist( extra.w, along * glm::dot( glm::vec3( extra.x, extra.y, extra.z ), along ) );
    const float size = glm::length( twist );
    if( size > 1e-5f )
    {
        twist = twist / size;
        Turn( fore, Part( twist.w < 0.f ? -twist : twist, 0.5f ) * fore.World );
    }
    Turn( hand, turn * hand.BindWorld );
    CurlFingers( inSide, inArm.Grip );
    m_hands[inSide] = ( hand.Position + turn * m_grip[inSide] ) * m_look.Height;
}


void Performer::PoseBody( const Pose& inPose )
{
    if( m_stood && SameStance( inPose, m_stance ) )
    {
        return;
    }
    m_stance = inPose;
    m_stood = true;

    // Everything is in the root's (scaled) space: the figure is posed at a scale of 1.
    const float invScale = 1.f / std::max( 0.01f, m_look.Height );
    const glm::vec3 offset = inPose.Offset * invScale;
    const glm::quat hipsTurn = Axis( inPose.Turn * 0.3f, kY );
    const glm::quat spineTurn = Axis( inPose.Turn * 0.7f, kY ) * Axis( inPose.Lean, kX ) * Axis( -inPose.Side, kZ );
    const glm::quat headTurn = Axis( inPose.HeadTurn, kY ) * Axis( inPose.Nod, kX ) * Axis( -inPose.HeadTilt, kZ );

    // Where the feet go, before the hips: the hips sit no higher than the legs reach.
    std::array<glm::vec3, 2> ankles;
    std::array<glm::vec3, 2> knees;
    std::array<glm::quat, 2> feet;
    std::array<glm::quat, 2> toes;
    for( int side = 0; side < 2; ++side )
    {
        const float s = side == 0 ? -1.f : 1.f;
        const Leg& leg = inPose.Legs[side];
        const glm::vec3 hip = Of( side, Thigh ).BindPosition;
        const glm::vec3 ankle = Of( side, Foot ).BindPosition;
        glm::quat yaw = kIdentity;
        if( leg.Reach )
        {
            ankles[side] = leg.Target * invScale + glm::vec3( 0.f, ankle.y, 0.f );
            knees[side] = glm::dot( leg.Pole, leg.Pole ) > 1e-8f ? glm::normalize( leg.Pole ) : kZ;
        }
        else if( inPose.Seated )
        {
            // Feet flat on the floor ahead of the seat.
            ankles[side] = glm::vec3( hip.x * 1.5f, ankle.y, 0.42f ) + offset;
            knees[side] = glm::normalize( glm::vec3( s * 0.2f, 1.f, 1.f ) );
        }
        else
        {
            // Planted: out to the side by the spread, and turned out a little with it.
            ankles[side] = glm::vec3( hip.x + s * m_leg * std::sin( leg.Spread * kDeg ), ankle.y, ankle.z ) + offset;
            knees[side] = glm::normalize( glm::vec3( s * 0.25f, 0.f, 1.f ) );
            yaw = Axis( s * leg.Spread * 0.5f, kY );
        }
        feet[side] = yaw * Axis( leg.Toe, kX );
        toes[side] = feet[side];
        if( leg.Toe > 0.f )
        {
            // A pedal stroke: the heel lifts about the ball of the foot, which stays down with
            // the toes.
            const glm::vec3 ball = Of( side, Toe ).BindPosition - ankle;
            ankles[side] += yaw * ball - feet[side] * ball;
            toes[side] = yaw;
        }
    }

    Bone& hips = m_bones[Hips];
    hips.Position = hips.BindPosition + offset;
    if( inPose.Seated )
    {
        hips.Position.y = inPose.SeatHeight * invScale + ( hips.BindPosition.y - Of( 0, Thigh ).BindPosition.y ) + offset.y;
    }
    else
    {
        hips.Position.y -= inPose.Crouch;
        float sink = 0.f;
        for( int side = 0; side < 2; ++side )
        {
            const glm::vec3 joint = hips.Position + hipsTurn * ( Of( side, Thigh ).BindPosition - hips.BindPosition );
            const glm::vec3 toFoot = ankles[side] - joint;
            const float reach = m_leg * 0.995f;
            const float drop = std::sqrt( std::max( 0.f, reach * reach - toFoot.x * toFoot.x - toFoot.z * toFoot.z ) );
            sink = std::max( sink, -toFoot.y - drop );
        }
        hips.Position.y -= sink;
    }
    hips.Node->SetWorldPosition( Vector3( glm::conjugate( m_facing ) * hips.Position ) );
    Turn( hips, hipsTurn * hips.BindWorld );

    // The spine's turn shared over its three bones, the head's over the neck's two and the head.
    m_spine = hipsTurn * spineTurn;
    Turn( m_bones[Spine1], hipsTurn * Part( spineTurn, 1.f / 3.f ) * m_bones[Spine1].BindWorld );
    Turn( m_bones[Spine2], hipsTurn * Part( spineTurn, 2.f / 3.f ) * m_bones[Spine2].BindWorld );
    Turn( m_bones[Ribs], m_spine * m_bones[Ribs].BindWorld );
    m_headRotation = m_spine * headTurn;
    Turn( m_bones[Neck1], m_spine * Part( headTurn, 0.2f ) * m_bones[Neck1].BindWorld );
    Turn( m_bones[Neck2], m_spine * Part( headTurn, 0.5f ) * m_bones[Neck2].BindWorld );
    Turn( m_bones[Head], m_headRotation * m_bones[Head].BindWorld );

    for( int side = 0; side < 2; ++side )
    {
        Bone& thigh = Of( side, Thigh );
        Bone& shin = Of( side, Shin );
        Bone& foot = Of( side, Foot );
        Rest( thigh );
        Rest( shin );
        Rest( foot );
        Solve( thigh, shin, foot, ankles[side], thigh.Position + knees[side] );
        Turn( foot, feet[side] * foot.BindWorld );
        Turn( Of( side, Toe ), toes[side] * Of( side, Toe ).BindWorld );
        // The arms hang from the ribs: the shoulders are placed, however the arms are posed.
        const Bone& upper = Of( side, UpperArm );
        m_shoulders[side] = ( m_bones[upper.Anchor].Position + m_bones[upper.Anchor].World * upper.Offset ) * m_look.Height;
    }
    m_chest = ( m_shoulders[0] + m_shoulders[1] ) * 0.5f + m_spine * glm::vec3( 0.f, 0.f, 0.1f ) * m_look.Height;
    m_headPos = ( m_bones[Head].Position + m_headRotation * glm::vec3( 0.f, 0.105f, 0.03f ) ) * m_look.Height;
    m_spineBase = ( hips.Position + glm::vec3( 0.f, 0.07f, 0.f ) ) * m_look.Height;
}


void Performer::PoseUnbound( const Pose& inPose )
{
    // Nothing to pose (the model is missing, or isn't this rig): the points the cameras and
    // lights ask for, as if standing straight.
    const glm::vec3 base = glm::vec3( 0.f, inPose.Seated ? inPose.SeatHeight + 0.1f : 0.95f * m_look.Height, 0.f ) + inPose.Offset;
    m_spine = kIdentity;
    m_headRotation = kIdentity;
    m_spineBase = base;
    m_chest = base + glm::vec3( 0.f, 0.45f, 0.1f ) * m_look.Height;
    m_headPos = base + glm::vec3( 0.f, 0.73f, 0.03f ) * m_look.Height;
    for( int side = 0; side < 2; ++side )
    {
        const float s = side == 0 ? -1.f : 1.f;
        m_shoulders[side] = base + glm::vec3( s * 0.19f, 0.44f, 0.f ) * m_look.Height;
        m_hands[side] = m_shoulders[side] + glm::vec3( s * 0.05f, -0.55f, 0.1f ) * m_look.Height;
    }
}


void Performer::Stand( const Pose& inPose )
{
    if( !m_root )
    {
        return;
    }
    if( !Ready() )
    {
        PoseUnbound( inPose );
        return;
    }
    PoseBody( inPose );
}


void Performer::Apply( const Pose& inPose )
{
    if( !m_root )
    {
        return;
    }
    if( !Ready() )
    {
        PoseUnbound( inPose );
        return;
    }
    PoseBody( inPose );
    const float invScale = 1.f / std::max( 0.01f, m_look.Height );
    for( int side = 0; side < 2; ++side )
    {
        PoseArm( side, inPose.Arms[side], invScale );
    }
    if( m_mouth )
    {
        // Hidden (shrunk) while shut: the face has its own closed mouth.
        const float open = std::clamp( inPose.Mouth, 0.f, 1.f );
        Puppet::PlacePiece( m_mouth, m_bones[Head].Position + m_headRotation * m_look.Mouth.InternalVector, m_headRotation );
        m_mouth->GetComponent<Transform>().SetScale( open > 0.02f ? VenueKit::ScaleFor( Moonlight::MeshType::Cube, Vector3( 0.05f, 0.006f + 0.028f * open, 0.012f ) ) : Vector3( 0.001f, 0.001f, 0.001f ) );
    }
}
