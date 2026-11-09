#pragma once
#include "CoreGame/Lyrics.h"
#include "ECS/EntityHandle.h"
#include "Math/Vector3.h"
#include <array>
#include <string>
#include <vector>

class Transform;
class VenueKit;

// Karaoke lyrics on the LED wall (Docs/Venue-and-Band.md → Lyrics): a dark band across the lower
// part of the wall with the line being sung (sung syllables lit gold) and the next one under it.
// Each character is a plane whose emissive texture is the lyric font atlas
// (Game/Tools/MakeLyricFont.py), its glyph picked with the material's Tiling and Offset; glyphs
// that look the same batch together.
class LyricBoard
{
public:
    // inCentre is the band's centre in front of the wall (venue space, under inRoot), inWidth its
    // width in metres.
    void Build( VenueKit& inKit, Transform& inRoot, const Vector3& inCentre, float inWidth, const Lyrics& inLyrics );
    void Clear();
    void Update( double inSeconds );

private:
    struct Row
    {
        std::vector<EntityHandle> Glyphs;
        float Height = 0.f;     // line height, metres
        float Y = 0.f;          // centre, in the band's space
        std::string Text;       // what it shows now
        size_t Lit = 0;         // characters lit (sung)
        bool Next = false;      // the preview row
    };

    void Show( Row& ioRow, const std::string& inText, size_t inLit );

    const Lyrics* m_lyrics = nullptr;
    EntityHandle m_group;
    float m_width = 0.f;
    std::array<Row, 2> m_rows;
};
