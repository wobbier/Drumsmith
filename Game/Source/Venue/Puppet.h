#pragma once
#include "ECS/EntityHandle.h"
#include "Math/Vector3.h"
#include <glm/gtc/quaternion.hpp>
#include <glm/vec3.hpp>
#include <array>

class Transform;
class VenueKit;
namespace People { struct Person; }

// A crowd figure posed procedurally (Docs/Venue-and-Band.md): one of the characters cut into five
// rigid pieces (People::Person: legs, torso, head, an arm each side), with no skeleton or clips,
// just joint positions worked out each frame and a piece turned at each. Rigid pieces instance,
// so a crowd of them is a handful of draws; the band's own figures are skinned (Performer).
// Puppet space: the root is at the feet, +y up, the figure faces +z, its right hand is +x.
class Puppet
{
public:
    struct Look
    {
        float Height = 1.f;        // a scale on the whole figure
        float Build = 1.f;         // a scale on its width
        // The decimated pieces: under a third of the triangles, for figures far from the camera.
        bool Far = false;
        // Which character it is (People::kPeople), and which of the atlas variants it wears
        // (VenueKit::Skin).
        int Model = 0;
        uint32_t Skin = 0;
    };

    struct Arm
    {
        // Angles in degrees: Raise swings the arm forward from hanging (90 points it ahead, 180
        // straight up), Spread out to the side (negative: in across the body, as hands meet to clap), Elbow bends it (the rigid arm shortens).
        float Raise = 5.f;
        float Spread = 8.f;
        float Elbow = 12.f;
    };

    struct Pose
    {
        glm::vec3 Offset{ 0.f };   // the whole figure (a bounce, a jump, a step)
        float Crouch = 0.f;        // metres the hips drop
        float Lean = 0.f;          // the spine forward, degrees
        float Side = 0.f;          // the spine to the figure's right, degrees
        float Turn = 0.f;          // the shoulders to the figure's left (+), degrees
        float Nod = 0.f;           // the head down
        float HeadTurn = 0.f;
        float HeadTilt = 0.f;
        std::array<Arm, 2> Arms;   // 0 left, 1 right
    };

    void Build( VenueKit& inKit, Transform* inParent, const Vector3& inFeet, float inYawDegrees, const Look& inLook );
    void Apply( const Pose& inPose );

    Transform* Root() const;
    // A hand after Apply, in puppet space.
    glm::vec3 Hand( int inSide ) const { return m_hands[inSide]; }
    float Scale() const { return m_look.Height; }

    // Places a piece as a bone between two points of its parent's space (its long axis, y, along
    // them).
    static void PlaceBone( const EntityHandle& inPiece, const glm::vec3& inFrom, const glm::vec3& inTo );
    static void PlacePiece( const EntityHandle& inPiece, const glm::vec3& inCentre, const glm::quat& inRotation );
    static glm::quat FromTo( const glm::vec3& inFrom, const glm::vec3& inTo );


private:
    Look m_look;
    const People::Person* m_person = nullptr;
    EntityHandle m_root;
    EntityHandle m_torso, m_head, m_legs;
    std::array<EntityHandle, 2> m_arms;
    std::array<glm::vec3, 2> m_hands{};
};
