#pragma once
#include "ECS/EntityHandle.h"
#include "Math/Vector3.h"
#include <glm/gtc/quaternion.hpp>
#include <glm/vec3.hpp>
#include <array>
#include <vector>

class Transform;
class VenueKit;

// A figure built from primitives and posed procedurally (Docs/Venue-and-Band.md): no skeleton or
// clips, just joint positions worked out each frame and a capsule laid between each pair. Arms
// pose by angles (forward kinematics) or reach for a point (two-bone IK); legs by angles. Band
// members are detailed (hands, feet, hair, a mouth); the crowd's figures are five pieces each.
// Puppet space: the root is at the feet, +y up, the figure faces +z, its right hand is +x.
class Puppet
{
public:
    struct Look
    {
        Vector3 Skin{ 0.8f, 0.6f, 0.48f };
        Vector3 Shirt{ 0.2f, 0.2f, 0.25f };
        Vector3 Pants{ 0.08f, 0.08f, 0.1f };
        Vector3 Hair{ 0.12f, 0.08f, 0.05f };
        Vector3 Shoes{ 0.05f, 0.05f, 0.05f };
        float Height = 1.f;        // a scale on the whole figure
        float Build = 1.f;         // a scale on its width
        bool LongHair = false;
        // A box for the head instead of a sphere: a dozen triangles instead of thousands, for
        // figures far from the camera.
        bool Blocky = false;
    };

    struct Arm
    {
        // Angles in degrees: Raise swings the arm forward from hanging (90 points it ahead, 180
        // straight up), Spread out to the side, Elbow bends the forearm forward.
        float Raise = 5.f;
        float Spread = 8.f;
        float Elbow = 12.f;
        // Reach: when set, the hand goes to Target (puppet space) and the elbow bends toward Pole.
        bool Reach = false;
        glm::vec3 Target{ 0.f };
        glm::vec3 Pole{ 0.f, -1.f, 0.f };
    };

    struct Leg
    {
        float Lift = 0.f;          // the thigh forward, degrees
        float Spread = 3.f;
        float Knee = 0.f;          // the shin back, degrees
        float Toe = 0.f;           // the foot pitched down, degrees (a pedal stroke)
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
        bool Seated = false;       // hips at SeatHeight, thighs forward
        float SeatHeight = 0.62f;
        std::array<Arm, 2> Arms;   // 0 left, 1 right
        std::array<Leg, 2> Legs;
    };

    void Build( VenueKit& inKit, Transform* inParent, const Vector3& inFeet, float inYawDegrees, const Look& inLook, bool inDetailed );
    void Apply( const Pose& inPose );

    Transform* Root() const;
    // Puppet-space joints after Apply.
    glm::vec3 Chest() const { return m_chest; }
    glm::vec3 HeadCentre() const { return m_headPos; }
    glm::vec3 Shoulder( int inSide ) const { return m_shoulders[inSide]; }
    glm::vec3 Hand( int inSide ) const { return m_hands[inSide]; }
    glm::quat SpineRotation() const { return m_spine; }
    glm::vec3 SpineBase() const { return m_spineBase; }
    float Scale() const { return m_look.Height; }
    float ArmLength() const { return ( kUpperArm + kForearm ) * m_look.Height; }

    // Places a piece as a bone between two puppet-space points (its long axis, y, along them).
    static void PlaceBone( const EntityHandle& inPiece, const glm::vec3& inFrom, const glm::vec3& inTo );
    static void PlacePiece( const EntityHandle& inPiece, const glm::vec3& inCentre, const glm::quat& inRotation );
    static glm::quat FromTo( const glm::vec3& inFrom, const glm::vec3& inTo );

    static constexpr float kUpperArm = 0.3f;
    static constexpr float kForearm = 0.29f;
    static constexpr float kThigh = 0.45f;
    static constexpr float kShin = 0.44f;

private:
    glm::vec3 Reach( const glm::vec3& inShoulder, const Arm& inArm, const glm::quat& inSpine, int inSide, glm::vec3& outElbow ) const;

    Look m_look;
    bool m_detailed = false;
    EntityHandle m_root;
    EntityHandle m_pelvis, m_torso, m_head, m_hair, m_cap, m_mouth, m_legs;
    std::array<EntityHandle, 2> m_eyes;
    std::array<EntityHandle, 2> m_upperArms, m_forearms, m_handPieces, m_thighs, m_shins, m_feet;

    glm::vec3 m_chest{ 0.f };
    glm::vec3 m_headPos{ 0.f };
    glm::quat m_spine{ 1.f, 0.f, 0.f, 0.f };
    glm::vec3 m_spineBase{ 0.f };
    std::array<glm::vec3, 2> m_shoulders{};
    std::array<glm::vec3, 2> m_hands{};
};
