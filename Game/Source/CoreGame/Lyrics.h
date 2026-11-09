#pragma once
#include "CoreGame/TrackList.h"
#include <string>
#include <vector>

// Karaoke lines from a chart's lyric events (Docs/Venue-and-Band.md → Lyrics), for the HUD and the
// venue's LED wall. Rock Band's syllable markers are resolved here, not at import, so the display
// rules can change without converting the charts again:
//   "Hel-" joins the next syllable, "to=" joins it with a hyphen shown, "+" continues the last
//   syllable's note (a slide: no text), "#" "^" "*" "%" "$" "/" are dropped, "§" and "_" are spaces.
// Lines are the chart's phrases (PART VOCALS notes 105/106); without them, a gap of more than 1.2 s
// starts a new line. Long lines are split near the middle at a word.
class Lyrics
{
public:
    struct Syllable
    {
        float Start = 0.f;
        float End = 0.f;
        size_t From = 0;    // its characters in the line's text
        size_t To = 0;
    };

    struct Line
    {
        float Start = 0.f;
        float End = 0.f;
        std::string Text;
        std::vector<Syllable> Syllables;
    };

    // What's showing at a moment: the line being sung (or about to be), how much of it has been
    // sung, and the line after it as a preview.
    struct View
    {
        int Current = -1;
        int Next = -1;
        size_t Sung = 0;      // characters of the current line sung so far
    };

    void Build( const std::vector<TimedCueData>& inLyrics, const std::vector<VenueData::SpanData>& inPhrases, const std::vector<VenueData::SpanData>& inNotes );
    void Clear() { m_lines.clear(); }
    bool Empty() const { return m_lines.empty(); }
    const std::vector<Line>& Lines() const { return m_lines; }
    View At( double inSeconds ) const;

    // The longest line Build makes, in characters (the LED wall sizes its glyphs for it).
    static constexpr size_t kMaxLine = 44;

private:
    std::vector<Line> m_lines;
};
