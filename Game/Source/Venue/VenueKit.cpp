#include "Venue/VenueKit.h"
#include "Components/Graphics/Mesh.h"
#include "Components/Graphics/Model.h"
#include "Components/Transform.h"
#include "Engine/World.h"
#include "Materials/DiffuseMaterial.h"


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
