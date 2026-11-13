#include "Venue/VenueKit.h"
#include "Venue/People.generated.h"
#include "Components/Graphics/Mesh.h"
#include "Components/Graphics/Model.h"
#include "Components/Transform.h"
#include "Engine/World.h"
#include "Graphics/ModelResource.h"
#include "Graphics/Texture.h"
#include "Materials/DiffuseMaterial.h"
#include "Resource/ResourceCache.h"
#include "CLog.h"
#include "Path.h"
#include <bgfx/bgfx.h>
#include <algorithm>


VenueKit::VenueKit() = default;


VenueKit::~VenueKit() = default;


void VenueKit::Begin( World& inWorld )
{
    Clear();
    m_world = &inWorld;
    if( !m_template )
    {
        m_template = MakeUnique<DiffuseMaterial>();
        m_template->Init();
    }
}


void VenueKit::Clear()
{
    for( EntityHandle& entity : m_entities )
    {
        if( entity ) entity->MarkForDelete();
    }
    m_entities.clear();
    m_world = nullptr;
}


EntityHandle VenueKit::Group( const char* inName, Transform* inParent, const Vector3& inPosition )
{
    if( !m_world )
    {
        return {};
    }
    EntityHandle entity = m_world->CreateEntity( inName );
    if( !entity )
    {
        return entity;
    }
    Transform& transform = entity->AddComponent<Transform>( inName );
    if( inParent )
    {
        transform.SetParent( *inParent );
    }
    transform.SetPosition( inPosition );
    m_entities.push_back( entity );
    return entity;
}


EntityHandle VenueKit::Prop( const char* inPath, const Vector3& inPosition, float inScale, float inYaw, Transform* inParent )
{
    EntityHandle entity = Group( "Venue prop", inParent, inPosition );
    if( entity )
    {
        Transform& transform = entity->GetComponent<Transform>();
        transform.SetScale( Vector3( inScale, inScale, inScale ) );
        transform.SetRotation( Vector3( 0.f, inYaw, 0.f ) );
        entity->AddComponent<Model>( std::string( inPath ) );
    }
    return entity;
}


namespace
{
    const std::vector<std::string>& Skins()
    {
        // Synty's naming: a palette number and a letter. Found once; the first is the fallback.
        static const std::vector<std::string> skins = [] {
            std::vector<std::string> found;
            for( int palette = 1; palette <= 9; ++palette )
            {
                for( char letter = 'A'; letter <= 'F'; ++letter )
                {
                    const std::string path = "Assets/Models/Venue/PolygonTown_0" + std::to_string( palette ) + "_" + letter + ".png";
                    if( Path( path ).Exists ) found.push_back( path );
                }
            }
            if( found.empty() ) found.push_back( "Assets/Models/Venue/PolygonTown_01_A.png" );
            return found;
        }();
        return skins;
    }

    // A variant's tile in the crowd's packed atlas, or -1 when it isn't in it (added since the
    // atlas was made: Game/Tools/MakeCrowdPieces.py packs it).
    int SkinTile( const std::string& inSkin )
    {
        for( int tile = 0; tile < People::kSkinCount; ++tile )
        {
            if( inSkin == People::kSkins[tile] ) return tile;
        }
        return -1;
    }
}


const std::string& VenueKit::Skin( uint32_t inIndex )
{
    return Skins()[inIndex % Skins().size()];
}


uint32_t VenueKit::SkinCount()
{
    return static_cast<uint32_t>( Skins().size() );
}


SharedPtr<Moonlight::Texture> VenueKit::SkinTexture( const std::string& inSkin )
{
    auto found = m_skins.find( inSkin );
    if( found == m_skins.end() )
    {
        const Path path( inSkin );
        found = m_skins.emplace( inSkin, path.Exists ? ResourceCache::GetInstance().Get<Moonlight::Texture>( path ) : nullptr ).first;
    }
    return found->second;
}


SharedPtr<Moonlight::Texture> VenueKit::SkinAtlas()
{
    // Whole or not at all: a texture size cap would drop the atlas's top mips, and with them every
    // tile's, where the separate variants it caps less would keep theirs.
    const uint32_t size = static_cast<uint32_t>( std::max( People::kSkinColumns, People::kSkinRows ) * People::kSkinTile );
    const uint32_t cap = Moonlight::Texture::GetMaxUploadSize();
    const bgfx::Caps* caps = bgfx::getCaps();
    if( ( cap > 0 && cap < size ) || ( caps && caps->limits.maxTextureSize < size ) )
    {
        return nullptr;
    }
    if( !m_skinAtlas )
    {
        const Path path( People::kSkinAtlas );
        if( path.Exists )
        {
            m_skinAtlas = ResourceCache::GetInstance().Get<Moonlight::Texture>( path );
        }
    }
    return m_skinAtlas && !m_skinAtlas->HasLoadFailed() ? m_skinAtlas : nullptr;
}


EntityHandle VenueKit::Part( const char* inPath, Transform* inParent, const char* inName, const std::string& inSkin )
{
    auto found = m_parts.find( inPath );
    if( found == m_parts.end() )
    {
        // Loaded here, not in the background: the mesh is needed to make the piece.
        SharedPtr<ModelResource> model = ResourceCache::GetInstance().Get<ModelResource>( Path( inPath ) );
        if( !model || model->HasLoadFailed() || model->GetAllMeshes().empty() )
        {
            YIKES_FMT( "VenueKit: no mesh in %s", inPath );
            model = nullptr;
        }
        found = m_parts.emplace( inPath, model ).first;
    }
    EntityHandle entity = Group( inName, inParent );
    if( entity && found->second )
    {
        Mesh& mesh = entity->AddComponent<Mesh>( found->second->GetAllMeshes()[0] );
        mesh.CastShadows = true;
        Moonlight::Material* material = mesh.MeshMaterial.get();
        // The packed atlas when the variant is in it (and the model's own uv transform is the
        // identity, which the tile's sits in place of): uv + (column, row) through a tiling of
        // one tile, the same texels as the variant's own texture, so figures in different
        // clothes share a draw (ME-365).
        const int tile = inSkin.empty() || !material || material->Tiling != Vector2( 1.f, 1.f ) || material->Offset != Vector2( 0.f, 0.f ) ? -1 : SkinTile( inSkin );
        SharedPtr<Moonlight::Texture> atlas = tile >= 0 ? SkinAtlas() : nullptr;
        if( atlas )
        {
            material->SetTexture( Moonlight::TextureType::Diffuse, atlas );
            material->Tiling = Vector2( 1.f / static_cast<float>( People::kSkinColumns ), 1.f / static_cast<float>( People::kSkinRows ) );
            mesh.InstanceData = glm::vec3( static_cast<float>( tile % People::kSkinColumns ), static_cast<float>( tile / People::kSkinColumns ), 0.f );
        }
        else if( SharedPtr<Moonlight::Texture> skin = inSkin.empty() ? nullptr : SkinTexture( inSkin ); skin && material )
        {
            material->SetTexture( Moonlight::TextureType::Diffuse, skin );
        }
    }
    return entity;
}


Vector3 VenueKit::ScaleFor( Moonlight::MeshType inShape, const Vector3& inSize )
{
    switch( inShape )
    {
    case Moonlight::MeshType::Sphere: return Vector3( inSize.x * 0.5f, inSize.y * 0.5f, inSize.z * 0.5f );
    case Moonlight::MeshType::Capsule: return Vector3( inSize.x, inSize.y * 0.5f, inSize.z );
    default: return inSize * 0.5f;
    }
}


EntityHandle VenueKit::Piece( Moonlight::MeshType inShape, const Vector3& inPosition, const Vector3& inSize, const Vector3& inColor, Transform* inParent, const Vector3& inEmissive, bool inShadows, const char* inName )
{
    EntityHandle entity = Group( inName, inParent, inPosition );
    if( !entity )
    {
        return entity;
    }
    entity->GetComponent<Transform>().SetScale( ScaleFor( inShape, inSize ) );
    Mesh& mesh = entity->AddComponent<Mesh>( inShape, m_template.get() );
    mesh.CastShadows = inShadows;
    SetColor( entity, inColor, inEmissive );
    return entity;
}


StandardMaterial* VenueKit::MaterialOf( const EntityHandle& inPiece )
{
    if( !inPiece || !inPiece->HasComponent<Mesh>() )
    {
        return nullptr;
    }
    Mesh& mesh = inPiece->GetComponent<Mesh>();
    return mesh.MeshMaterial ? dynamic_cast<StandardMaterial*>( mesh.MeshMaterial.get() ) : nullptr;
}


void VenueKit::SetColor( const EntityHandle& inPiece, const Vector3& inColor, const Vector3& inEmissive )
{
    if( StandardMaterial* material = MaterialOf( inPiece ) )
    {
        material->DiffuseColor = inColor;
        material->EmissiveColor = inEmissive;
    }
}
