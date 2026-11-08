#pragma once
#include "ECS/EntityHandle.h"
#include "Math/Vector3.h"
#include "RenderCommands.h"
#include "Pointers.h"
#include <string>
#include <vector>

class Transform;
class World;
class StandardMaterial;

// Builds the venue out of the engine's primitives (Docs/Venue-and-Band.md): every piece is a
// Transform + Mesh entity with a DiffuseMaterial (so pieces sharing a colour instance into one
// draw), and the kit deletes everything it made on Clear.
class VenueKit
{
public:
    VenueKit();
    ~VenueKit();

    void Begin( World& inWorld );
    void Clear();

    // An empty transform (a pivot or a group) under inParent.
    EntityHandle Group( const char* inName, Transform* inParent, const Vector3& inPosition = Vector3( 0.f, 0.f, 0.f ) );
    // A primitive whose full size is inSize (a box inSize across, a sphere inSize.x across, a
    // cylinder or capsule inSize.x wide and inSize.y tall), centred at inPosition.
    EntityHandle Piece( Moonlight::MeshType inShape, const Vector3& inPosition, const Vector3& inSize, const Vector3& inColor, Transform* inParent, const Vector3& inEmissive = Vector3( 0.f, 0.f, 0.f ), bool inShadows = false, const char* inName = "Piece" );
    EntityHandle Box( const Vector3& inPosition, const Vector3& inSize, const Vector3& inColor, Transform* inParent, const Vector3& inEmissive = Vector3( 0.f, 0.f, 0.f ) )
    {
        return Piece( Moonlight::MeshType::Cube, inPosition, inSize, inColor, inParent, inEmissive );
    }

    // The scale a primitive needs for a full size (the engine's shapes fit the [-1, 1] box; the
    // capsule's radius is 0.5 there).
    static Vector3 ScaleFor( Moonlight::MeshType inShape, const Vector3& inSize );

    static void SetColor( const EntityHandle& inPiece, const Vector3& inColor, const Vector3& inEmissive );
    static StandardMaterial* MaterialOf( const EntityHandle& inPiece );

    World* GetWorld() const { return m_world; }

private:
    World* m_world = nullptr;
    std::vector<EntityHandle> m_entities;
    UniquePtr<StandardMaterial> m_template;
};
