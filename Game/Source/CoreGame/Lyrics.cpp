#include "CoreGame/Lyrics.h"
#include <algorithm>
#include <cmath>

namespace
{
    constexpr float kLineGap = 1.2f;     // without phrases, a longer rest starts a new line
    constexpr float kHold = 0.6f;        // a line stays up this long after its last syllable
    constexpr float kLead = 3.f;         // and comes up this long before its first
    constexpr float kPreview = 10.f;     // the next line previews when it's this close

    struct Token
    {
        float Start = 0.f;
        float End = 0.f;
        std::string Text;
        bool Join = false;    // no space before the next syllable
        int Phrase = -1;
    };

    // A syllable's text with Rock Band's markers resolved; false for a "+" slide.
    bool Clean( const std::string& inRaw, std::string& outText, bool& outJoin )
    {
        outText.clear();
        outJoin = false;
        std::string raw = inRaw;
        if( raw == "+" || raw.empty() )
        {
            return false;
        }
        // "§" (UTF-8 C2 A7) joins two syllables sung as one: show a space.
        for( size_t at = raw.find( "\xC2\xA7" ); at != std::string::npos; at = raw.find( "\xC2\xA7" ) )
        {
            raw.replace( at, 2, " " );
        }
        for( char c : raw )
        {
            if( c == '#' || c == '^' || c == '*' || c == '%' || c == '$' || c == '/' || c == '+' ) continue;
            outText.push_back( c == '_' ? ' ' : c );
        }
        if( !outText.empty() && outText.back() == '-' )
        {
            outText.pop_back();
            outJoin = true;
        }
        else if( !outText.empty() && outText.back() == '=' )
        {
            outText.back() = '-';
            outJoin = true;
        }
        while( !outText.empty() && outText.back() == ' ' ) outText.pop_back();
        while( !outText.empty() && outText.front() == ' ' ) outText.erase( 0, 1 );
        return !outText.empty() || outJoin;
    }

    // The sung note starting with a syllable: its end.
    float NoteEnd( const std::vector<VenueData::SpanData>& inNotes, float inTime, float inFallback )
    {
        auto it = std::lower_bound( inNotes.begin(), inNotes.end(), inTime - 0.02f, []( const VenueData::SpanData& s, float t ) { return s.m_start < t; } );
        if( it != inNotes.end() && std::fabs( it->m_start - inTime ) <= 0.02f )
        {
            return std::max( it->m_end, inTime + 0.05f );
        }
        return inFallback;
    }

    size_t TextLength( const std::vector<Token>& inTokens, size_t inFrom, size_t inTo )
    {
        size_t length = 0;
        for( size_t i = inFrom; i < inTo; ++i )
        {
            length += inTokens[i].Text.size() + ( i + 1 < inTo && !inTokens[i].Join ? 1 : 0 );
        }
        return length;
    }
}


void Lyrics::Build( const std::vector<TimedCueData>& inLyrics, const std::vector<VenueData::SpanData>& inPhrases, const std::vector<VenueData::SpanData>& inNotes )
{
    m_lines.clear();
    std::vector<Token> tokens;
    size_t phrase = 0;
    for( size_t i = 0; i < inLyrics.size(); ++i )
    {
        const float time = inLyrics[i].m_time;
        Token token;
        if( !Clean( inLyrics[i].m_name, token.Text, token.Join ) )
        {
            // A slide carries the last syllable on to the end of this note.
            if( !tokens.empty() ) tokens.back().End = std::max( tokens.back().End, NoteEnd( inNotes, time, time + 0.2f ) );
            continue;
        }
        const float nextTime = i + 1 < inLyrics.size() ? inLyrics[i + 1].m_time : time + 0.5f;
        token.Start = time;
        token.End = NoteEnd( inNotes, time, std::min( nextTime, time + 0.5f ) );
        while( phrase < inPhrases.size() && inPhrases[phrase].m_end <= time ) ++phrase;
        token.Phrase = phrase < inPhrases.size() && inPhrases[phrase].m_start <= time + 0.01f ? static_cast<int>( phrase ) : -1;
        tokens.push_back( token );
    }

    // Lines: the phrases, or (between and without them) runs of syllables without a long rest.
    std::vector<std::pair<size_t, size_t>> groups;
    for( size_t i = 0; i < tokens.size(); ++i )
    {
        const bool breakHere = i == 0 || tokens[i].Phrase != tokens[i - 1].Phrase || ( tokens[i].Phrase < 0 && tokens[i].Start - tokens[i - 1].End > kLineGap );
        if( breakHere ) groups.push_back( { i, i + 1 } );
        else groups.back().second = i + 1;
    }
    // Too long for a line: split at the word nearest the middle, until each fits.
    for( size_t g = 0; g < groups.size(); ++g )
    {
        const auto [from, to] = groups[g];
        const size_t length = TextLength( tokens, from, to );
        if( length <= kMaxLine || to - from < 2 )
        {
            continue;
        }
        size_t best = 0;
        size_t bestDistance = length;
        for( size_t i = from + 1; i < to; ++i )
        {
            if( tokens[i - 1].Join ) continue;
            const size_t before = TextLength( tokens, from, i );
            const size_t distance = before > length / 2 ? before - length / 2 : length / 2 - before;
            if( distance < bestDistance )
            {
                best = i;
                bestDistance = distance;
            }
        }
        if( best == 0 )
        {
            continue;   // one long word: shown as it is
        }
        groups[g] = { from, best };
        groups.insert( groups.begin() + g + 1, { best, to } );
        --g;   // check the first half again
    }

    for( const auto& [from, to] : groups )
    {
        Line line;
        line.Start = tokens[from].Start;
        for( size_t i = from; i < to; ++i )
        {
            Syllable syllable;
            syllable.Start = tokens[i].Start;
            syllable.End = tokens[i].End;
            syllable.From = line.Text.size();
            line.Text += tokens[i].Text;
            syllable.To = line.Text.size();
            if( i + 1 < to && !tokens[i].Join ) line.Text += ' ';
            line.End = std::max( line.End, syllable.End );
            line.Syllables.push_back( syllable );
        }
        if( !line.Text.empty() )
        {
            m_lines.push_back( std::move( line ) );
        }
    }
}


Lyrics::View Lyrics::At( double inSeconds ) const
{
    View view;
    const float t = static_cast<float>( inSeconds );
    // The last line started by now, unless it's finished: then the one coming up.
    auto it = std::upper_bound( m_lines.begin(), m_lines.end(), t, []( float time, const Line& l ) { return time < l.Start; } );
    int current = static_cast<int>( it - m_lines.begin() ) - 1;
    if( current < 0 || m_lines[current].End + kHold < t )
    {
        ++current;
    }
    if( current >= static_cast<int>( m_lines.size() ) || m_lines[current].Start - t > kLead )
    {
        return view;
    }
    view.Current = current;
    for( const Syllable& syllable : m_lines[current].Syllables )
    {
        if( syllable.Start > t ) break;
        view.Sung = syllable.To;
    }
    if( current + 1 < static_cast<int>( m_lines.size() ) && m_lines[current + 1].Start - t < kPreview )
    {
        view.Next = current + 1;
    }
    return view;
}
