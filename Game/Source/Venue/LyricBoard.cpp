#include "Venue/LyricBoard.h"
#include "Venue/LyricFont.generated.h"
#include "Venue/VenueKit.h"
#include "Components/Transform.h"
#include "Materials/StandardMaterial.h"
#include "Resource/ResourceCache.h"
#include "Graphics/Texture.h"
#include <algorithm>

namespace
{
    const Vector3 kSung( 1.f, 0.78f, 0.25f );
    const Vector3 kUnsung( 0.95f, 0.95f, 0.95f );
    const Vector3 kPreview( 0.38f, 0.38f, 0.4f );
    constexpr float kGlow = 2.2f;

    // A lyric's text in the atlas's printable ASCII: curly quotes and dashes straightened,
    // anything else outside it dropped.
    std::string ToAscii( const std::string& inText )
    {
        std::string out;
        for( size_t i = 0; i < inText.size(); ++i )
        {
            const unsigned char c = static_cast<unsigned char>( inText[i] );
            if( c >= 32 && c < 127 )
            {
                out.push_back( static_cast<char>( c ) );
                continue;
            }
            // UTF-8 E2 80 xx: ‘ ’ “ ” – — …
            if( c == 0xE2 && i + 2 < inText.size() && static_cast<unsigned char>( inText[i + 1] ) == 0x80 )
            {
                const unsigned char d = static_cast<unsigned char>( inText[i + 2] );
                if( d == 0x98 || d == 0x99 ) out.push_back( '\'' );
                else if( d == 0x9C || d == 0x9D ) out.push_back( '"' );
                else if( d == 0x93 || d == 0x94 ) out.push_back( '-' );
                else if( d == 0xA6 ) out += "...";
                i += 2;
                continue;
            }
            // Other multi-byte characters: skip their continuation bytes.
            while( i + 1 < inText.size() && ( static_cast<unsigned char>( inText[i + 1] ) & 0xC0 ) == 0x80 ) ++i;
        }
        return out;
    }

    const LyricFont::Glyph& GlyphOf( char inChar )
    {
        const int index = static_cast<unsigned char>( inChar ) - static_cast<unsigned char>( LyricFont::kFirst );
        return LyricFont::kGlyphs[index >= 0 && index < LyricFont::kCount ? index : 0];
    }
}


void LyricBoard::Build( VenueKit& inKit, Transform& inRoot, const Vector3& inCentre, float inWidth, const Lyrics& inLyrics )
{
    Clear();
    if( inLyrics.Empty() )
    {
        return;
    }
    m_lyrics = &inLyrics;
    m_width = inWidth;
    // The current line, and the next under it, smaller.
    m_rows[0].Height = 0.62f;
    m_rows[0].Y = 0.3f;
    m_rows[1].Height = 0.4f;
    m_rows[1].Y = -0.32f;
    m_rows[1].Next = true;
    const float bandHeight = 1.5f;
    // A dark band over the wall for the text to sit on, just in front of it.
    inKit.Box( inCentre + Vector3( 0.f, 0.f, 0.03f ), Vector3( inWidth + 0.4f, bandHeight, 0.02f ), Vector3( 0.005f, 0.005f, 0.006f ), &inRoot );
    m_group = inKit.Group( "Lyrics", &inRoot, inCentre );
    if( !m_group )
    {
        return;
    }
    Transform& group = m_group->GetComponent<Transform>();
    auto atlas = ResourceCache::GetInstance().Get<Moonlight::Texture>( Path( LyricFont::kTexture ) );
    for( Row& row : m_rows )
    {
        row.Glyphs.reserve( Lyrics::kMaxLine + 8 );
        for( size_t i = 0; i < Lyrics::kMaxLine + 8; ++i )
        {
            EntityHandle glyph = inKit.Piece( Moonlight::MeshType::Plane, Vector3( 0.f, row.Y, 0.f ), Vector3( 0.001f, 1.f, 0.001f ), Vector3( 0.f, 0.f, 0.f ), &group, Vector3( 0.f, 0.f, 0.f ), false, "Glyph" );
            if( !glyph ) continue;
            // The plane lies in XZ facing +y: stand it up facing the crowd (-z).
            glyph->GetComponent<Transform>().SetRotation( Quaternion::FromEulerDegrees( Vector3( -90.f, 0.f, 0.f ) ) );
            if( StandardMaterial* material = VenueKit::MaterialOf( glyph ) )
            {
                material->SetTexture( Moonlight::TextureType::Emissive, atlas );
                material->EmissiveIntensity = kGlow;
                material->Roughness = 1.f;
                material->Metallic = 0.f;
            }
            row.Glyphs.push_back( glyph );
        }
    }
}


void LyricBoard::Clear()
{
    // The entities are the kit's: VenueKit::Clear deletes them.
    m_group = {};
    for( Row& row : m_rows )
    {
        row.Glyphs.clear();
        row.Text.clear();
        row.Lit = 0;
    }
    m_lyrics = nullptr;
}


void LyricBoard::Update( double inSeconds )
{
    if( !m_lyrics || !m_group )
    {
        return;
    }
    const Lyrics::View view = m_lyrics->At( inSeconds );
    const auto& lines = m_lyrics->Lines();
    const std::string current = view.Current >= 0 ? lines[view.Current].Text : std::string();
    const std::string next = view.Next >= 0 ? lines[view.Next].Text : std::string();
    // Sung characters counted in the line's own text, then carried into its ASCII version.
    const size_t lit = view.Current >= 0 ? ToAscii( current.substr( 0, view.Sung ) ).size() : 0;
    Show( m_rows[0], ToAscii( current ), lit );
    Show( m_rows[1], ToAscii( next ), 0 );
}


void LyricBoard::Show( Row& ioRow, const std::string& inText, size_t inLit )
{
    if( inText == ioRow.Text && inLit == ioRow.Lit )
    {
        return;
    }
    const bool relayout = inText != ioRow.Text;
    ioRow.Text = inText;
    ioRow.Lit = inLit;
    // Shrink a line that won't fit the band's width.
    float advance = 0.f;
    for( char c : inText ) advance += GlyphOf( c ).Advance;
    const float height = advance * ioRow.Height > m_width ? m_width / advance : ioRow.Height;
    // Centred: the crowd sees -x on its left, so the line runs from -x to +x.
    float pen = -advance * height * 0.5f;
    for( size_t i = 0; i < ioRow.Glyphs.size(); ++i )
    {
        const EntityHandle& glyph = ioRow.Glyphs[i];
        if( !glyph ) continue;
        StandardMaterial* material = VenueKit::MaterialOf( glyph );
        Transform& transform = glyph->GetComponent<Transform>();
        const bool shown = i < inText.size() && inText[i] != ' ';
        if( i < inText.size() && relayout )
        {
            const LyricFont::Glyph& g = GlyphOf( inText[i] );
            const float width = g.Advance * height;
            transform.SetPosition( Vector3( pen + width * 0.5f, ioRow.Y, 0.f ) );
            transform.SetScale( VenueKit::ScaleFor( Moonlight::MeshType::Plane, shown ? Vector3( width, 1.f, height ) : Vector3( 0.001f, 1.f, 0.001f ) ) );
            pen += width;
            if( material )
            {
                // The stood-up plane's v runs up the atlas: flip the cell vertically.
                material->Tiling = Vector2( g.Width, -g.Height );
                material->Offset = Vector2( g.U, g.V + g.Height );
            }
        }
        else if( !shown && relayout )
        {
            transform.SetScale( VenueKit::ScaleFor( Moonlight::MeshType::Plane, Vector3( 0.001f, 1.f, 0.001f ) ) );
        }
        if( material )
        {
            material->EmissiveColor = !shown ? Vector3( 0.f, 0.f, 0.f ) : ioRow.Next ? kPreview : i < inLit ? kSung : kUnsung;
        }
    }
}
