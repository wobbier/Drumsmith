#pragma once
#include "ECS/EntityHandle.h"
#include "Math/Vector3.h"
#include "RenderCommands.h"
#include "Pointers.h"
#include <string>
#include <unordered_map>
#include <vector>

class ModelResource;
namespace Moonlight { class Texture; }
class Transform;
class World;
class StandardMaterial;

// Builds the venue from primitives and imported props (Docs/Venue-and-Band.md): each primitive is a
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
    // Imported scenery shares the kit's lifetime, including room swaps.
    EntityHandle Prop( const char* inPath, const Vector3& inPosition, float inScale, float inYaw, Transform* inParent );
    // A primitive whose full size is inSize (a box inSize across, a sphere inSize.x across, a
    // cylinder or capsule inSize.x wide and inSize.y tall), centred at inPosition.
    EntityHandle Piece( Moonlight::MeshType inShape, const Vector3& inPosition, const Vector3& inSize, const Vector3& inColor, Transform* inParent, const Vector3& inEmissive = Vector3( 0.f, 0.f, 0.f ), bool inShadows = false, const char* inName = "Piece" );
    EntityHandle Box( const Vector3& inPosition, const Vector3& inSize, const Vector3& inColor, Transform* inParent, const Vector3& inEmissive = Vector3( 0.f, 0.f, 0.f ) )
    {
        return Piece( Moonlight::MeshType::Cube, inPosition, inSize, inColor, inParent, inEmissive );
    }

    // A model's first mesh as a piece of its own, drawn with the model's material: pieces of the
    // same model instance into one draw, where Prop's don't have to. The crowd's figures.
    // inSkin: the character atlas it's drawn with (a path from Skin; empty: the model's own).
    // A variant packed in the crowd's atlas (People::kSkinAtlas) is drawn from that atlas, its tile
    // picked per instance (Mesh::InstanceData), so parts of one model batch together whatever
    // they wear; any other skin draws its own texture and batches per model and skin.
    EntityHandle Part( const char* inPath, Transform* inParent, const char* inName = "Part", const std::string& inSkin = std::string() );

    // The character's atlas variants (Assets/Models/Venue/PolygonTown_NN_L.png, whichever exist):
    // the band's and the crowd's figures each wear one. Any index picks one (it wraps).
    static const std::string& Skin( uint32_t inIndex );
    static uint32_t SkinCount();
    // Loaded once, and held.
    SharedPtr<Moonlight::Texture> SkinTexture( const std::string& inSkin );
    // The packed atlas of every variant, when it's there and the GPU and the texture size cap
    // (hardware profile) take it whole; null otherwise, and the crowd falls back to SkinTexture.
    SharedPtr<Moonlight::Texture> SkinAtlas();

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
    // Parts' models, held so their meshes outlive the pieces drawn from them.
    std::unordered_map<std::string, SharedPtr<ModelResource>> m_parts;
    std::unordered_map<std::string, SharedPtr<Moonlight::Texture>> m_skins;
    SharedPtr<Moonlight::Texture> m_skinAtlas;
};
