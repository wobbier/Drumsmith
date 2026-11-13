#pragma once
#include "ECS/EntityHandle.h"
#include "Pointers.h"
#include "Math/Vector3.h"
#include <glm/gtc/quaternion.hpp>
#include <glm/vec3.hpp>
#include <array>
#include <string>

class Model;
namespace Moonlight { class Texture; }
class Transform;
class VenueKit;

// A band member's body (Docs/Venue-and-Band.md): a rigged, skinned character posed through its
// skeleton each frame, with no clips. The spine and head turn by angles, shared out along their
// bones; the arms and legs are bent by the engine's two-bone IK (IK::SolveTwoBone) so a palm or a
// foot lands on its mark; the hands turn and their fingers curl to hold what they reach for.
// The character is a T-posed Rigify human (spine, spine.001-006, upper_arm.L, forearm.L, hand.L,
// thigh.L, shin.L, foot.L ...); which way it faces and how long its limbs are is read from its
// bind pose.
// Performer space: the root is at the feet, +y up, the figure faces +z, its right hand is +x.
class Performer
{
public:
    struct Look
    {
        std::string ModelPath = "Assets/Models/People/BodyType1_Rigged.fbx";
        // The atlas the model's UVs index (the FBX names no texture): one of VenueKit::Skin's.
        std::string TexturePath = "Assets/Models/Venue/PolygonTown_01_A.png";
        // The mouth, from the head bone (performer space): a dark piece there opens as they sing.
        Vector3 Mouth{ 0.f, -0.008f, 0.131f };
        float Height = 1.f;        // a scale on the whole figure
    };

    struct Arm
    {
        // Angles in degrees: Raise swings the arm forward from hanging (90 points it ahead, 180
        // straight up), Spread out to the side (negative: in across the body, as hands meet to clap), Elbow bends the forearm forward.
        float Raise = 5.f;
        float Spread = 8.f;
        float Elbow = 12.f;
        // Reach: when set, the palm goes to Target (performer space) and the elbow bends toward
        // Pole (a direction).
        bool Reach = false;
        glm::vec3 Target{ 0.f };
        glm::vec3 Pole{ 0.f, -1.f, 0.f };
        // The hand (performer space): which way the fingers point, and what the palm faces. Zero
        // leaves either to the arm: a straight wrist, the palm as the arm's swing turned it.
        glm::vec3 Fingers{ 0.f };
        glm::vec3 Palm{ 0.f };
        float Grip = 0.15f;        // 0 an open hand, 1 a fist
    };

    struct Leg
    {
        float Spread = 3.f;        // standing: the foot out to the side, degrees at the hip
        float Toe = 0.f;           // the foot pitched down, degrees (a pedal stroke: the heel lifts)
        // Reach: when set, the sole (under the ankle) goes to Target (performer space) and the
        // knee bends toward Pole (a direction). Standing legs plant their feet instead.
        bool Reach = false;
        glm::vec3 Target{ 0.f };
        glm::vec3 Pole{ 0.f, 0.4f, 1.f };
    };

    struct Pose
    {
        glm::vec3 Offset{ 0.f };   // the whole figure (a bounce, a jump, a step)
        float Crouch = 0.f;        // metres the hips drop, the knees bending to suit
        float Lean = 0.f;          // the spine forward, degrees
        float Side = 0.f;          // the spine to the figure's right, degrees
        float Turn = 0.f;          // the shoulders to the figure's left (+), degrees
        float Nod = 0.f;           // the head down
        float HeadTurn = 0.f;
        float HeadTilt = 0.f;
        float Mouth = 0.f;         // 0 shut, 1 wide open
        bool Seated = false;       // the hip joints at SeatHeight
        float SeatHeight = 0.67f;
        std::array<Arm, 2> Arms;   // 0 left, 1 right
        std::array<Leg, 2> Legs;
    };

    void Build( VenueKit& inKit, Transform* inParent, const Vector3& inFeet, float inYawDegrees, const Look& inLook );
    // The hips, spine, head and legs only: enough for Chest() and SpineBase(), for arms that reach
    // from where those are. An Apply of the same pose then has only the arms left to do.
    void Stand( const Pose& inPose );
    void Apply( const Pose& inPose );

    Transform* Root() const;
    // Performer-space points after Apply.
    glm::vec3 Chest() const { return m_chest; }
    glm::vec3 HeadCentre() const { return m_headPos; }
    glm::vec3 Shoulder( int inSide ) const { return m_shoulders[inSide]; }
    // The palm's centre: where a held thing sits.
    glm::vec3 Hand( int inSide ) const { return m_hands[inSide]; }
    // How far the chest has turned from standing straight.
    glm::quat SpineRotation() const { return m_spine; }
    // The head's turn from facing straight ahead: the face looks along its +z.
    glm::quat HeadRotation() const { return m_headRotation; }
    // Just above the hips.
    glm::vec3 SpineBase() const { return m_spineBase; }

private:
    // The bones posed: the spine up to the head, then each side's arm, fingers and leg.
    enum Centre : int { Hips = 0, Spine1, Spine2, Ribs, Neck1, Neck2, Head, kCentreCount };
    enum Limb : int
    {
        UpperArm = 0, Forearm, Wrist,                  // Wrist: the hand bone
        Index1, Index2, Index3, Middle1, Middle2, Middle3, Thumb1, Thumb2, Thumb3,
        Thigh, Shin, Foot, Toe,
        kLimbCount
    };
    static constexpr int kBoneCount = kCentreCount + 2 * kLimbCount;

    // The pose is worked out here, in performer space, and only written to the model's nodes:
    // reading a node back has the engine rebuild its matrices each time a bone above it turned.
    struct Bone
    {
        int Index = -1;                 // the model's node
        Transform* Node = nullptr;      // found again every pose (a reloaded model rebuilds them)
        int Anchor = -1;                // the nearest posed bone above it
        glm::quat BindLocal{ 1.f, 0.f, 0.f, 0.f };
        // At the bind pose, in performer space.
        glm::quat BindWorld{ 1.f, 0.f, 0.f, 0.f };
        glm::vec3 BindPosition{ 0.f };
        // At the bind pose, in its anchor's frame: its rotation, its parent's (the bones between
        // an anchor and it are never posed) and its place.
        glm::quat Rest{ 1.f, 0.f, 0.f, 0.f };
        glm::quat ParentRest{ 1.f, 0.f, 0.f, 0.f };
        glm::vec3 Offset{ 0.f };
        // As posed.
        glm::quat World{ 1.f, 0.f, 0.f, 0.f };
        glm::vec3 Position{ 0.f };
    };

    Bone& Of( int inSide, Limb inLimb ) { return m_bones[kCentreCount + inSide * kLimbCount + inLimb]; }
    const Bone& Of( int inSide, Limb inLimb ) const { return m_bones[kCentreCount + inSide * kLimbCount + inLimb]; }

    bool Bind( Model& inModel );
    // Finds the model's nodes again; false when there's no skeleton to pose.
    bool Ready();
    void PoseBody( const Pose& inPose );
    void PoseArm( int inSide, const Arm& inArm, float inInvScale );
    void PoseUnbound( const Pose& inPose );
    // Turns a bone to a rotation (performer space); its place follows its anchor.
    void Turn( Bone& ioBone, const glm::quat& inWorld );
    // Back to how it sits on its anchor at the bind pose.
    void Rest( Bone& ioBone );
    // Bends ioRoot and ioMid (at rest on it) so ioTip lands on inTarget, the middle joint toward
    // inPole (a point). ioTip is carried along at rest.
    void Solve( Bone& ioRoot, Bone& ioMid, Bone& ioTip, const glm::vec3& inTarget, const glm::vec3& inPole );
    glm::quat TurnHand( int inSide, const glm::quat& inFollow, const Arm& inArm, const glm::vec3& inForearm ) const;
    void CurlFingers( int inSide, float inGrip );

    Look m_look;
    EntityHandle m_root;
    EntityHandle m_body;       // carries the Model
    EntityHandle m_mouth;
    SharedPtr<Moonlight::Texture> m_skin;
    bool m_bound = false;
    bool m_bindFailed = false;
    // The pose the hips, spine, head and legs were last put in: the same again is already done.
    Pose m_stance;
    bool m_stood = false;
    // Model space to performer space: the model's own facing turned to +z.
    glm::quat m_facing{ 1.f, 0.f, 0.f, 0.f };
    // The rotation the hips sit under (the armature's), in performer space.
    glm::quat m_hipsParent{ 1.f, 0.f, 0.f, 0.f };
    std::array<Bone, kBoneCount> m_bones;
    // From the bind pose, in performer space.
    float m_upperArm = 0.34f;
    float m_forearm = 0.27f;
    float m_leg = 0.78f;
    std::array<glm::vec3, 2> m_fingers{};      // the way the fingers point
    std::array<glm::vec3, 2> m_palm{};         // what the palm faces
    std::array<glm::vec3, 2> m_grip{};         // the palm's centre, from the wrist
    std::array<glm::vec3, 2> m_curlAxis{};     // fingers curl about it, toward the palm
    std::array<glm::vec3, 2> m_thumbAxis{};

    glm::vec3 m_chest{ 0.f, 1.35f, 0.f };
    glm::vec3 m_headPos{ 0.f, 1.67f, 0.f };
    glm::quat m_spine{ 1.f, 0.f, 0.f, 0.f };
    glm::quat m_headRotation{ 1.f, 0.f, 0.f, 0.f };
    glm::vec3 m_spineBase{ 0.f, 0.95f, 0.f };
    std::array<glm::vec3, 2> m_shoulders{ glm::vec3( -0.19f, 1.39f, 0.f ), glm::vec3( 0.19f, 1.39f, 0.f ) };
    std::array<glm::vec3, 2> m_hands{ glm::vec3( -0.25f, 0.8f, 0.f ), glm::vec3( 0.25f, 0.8f, 0.f ) };
};
