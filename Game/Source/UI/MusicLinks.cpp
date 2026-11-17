#include "UI/MusicLinks.h"
#include "CLog.h"
#include <SDL.h>
#include <cctype>
#include <cstdio>

namespace
{
    // Percent-encoding for a URL's query or path segment.
    std::string Encode( const std::string& inText )
    {
        std::string encoded;
        for( unsigned char c : inText )
        {
            if( std::isalnum( c ) || c == '-' || c == '_' || c == '.' || c == '~' )
            {
                encoded += static_cast<char>( c );
            }
            else
            {
                char hex[4];
                std::snprintf( hex, sizeof( hex ), "%%%02X", static_cast<unsigned int>( c ) );
                encoded += hex;
            }
        }
        return encoded;
    }


    std::string Trimmed( const std::string& inText )
    {
        const size_t first = inText.find_first_not_of( " \t\r\n" );
        return first == std::string::npos ? std::string() : inText.substr( first, inText.find_last_not_of( " \t\r\n" ) - first + 1 );
    }
}


const char* MusicLinks::Key( Service inService )
{
    switch( inService )
    {
    case Service::Spotify: return "Spotify";
    case Service::AppleMusic: return "AppleMusic";
    case Service::YouTubeMusic: return "YouTubeMusic";
    default: return "";
    }
}


const char* MusicLinks::Name( Service inService )
{
    switch( inService )
    {
    case Service::Spotify: return "Spotify";
    case Service::AppleMusic: return "Apple Music";
    case Service::YouTubeMusic: return "YouTube Music";
    default: return "";
    }
}


std::string MusicLinks::Url( Service inService, const std::string& inArtist, const std::string& inTitle, const std::map<std::string, std::string>& inLinks )
{
    // The chart's own link, when it is one a browser should be handed.
    const auto own = inLinks.find( Key( inService ) );
    if( own != inLinks.end() && ( own->second.rfind( "https://", 0 ) == 0 || own->second.rfind( "http://", 0 ) == 0 ) )
    {
        return own->second;
    }
    const std::string artist = Trimmed( inArtist );
    const std::string title = Trimmed( inTitle );
    const std::string query = Encode( artist + ( artist.empty() || title.empty() ? "" : " " ) + title );
    if( query.empty() )
    {
        return {};
    }
    switch( inService )
    {
    case Service::Spotify: return "https://open.spotify.com/search/" + query;
    case Service::AppleMusic: return "https://music.apple.com/search?term=" + query;
    case Service::YouTubeMusic: return "https://music.youtube.com/search?q=" + query;
    default: return {};
    }
}


bool MusicLinks::Open( Service inService, const std::string& inArtist, const std::string& inTitle, const std::map<std::string, std::string>& inLinks )
{
    const std::string url = Url( inService, inArtist, inTitle, inLinks );
    if( url.empty() )
    {
        return false;
    }
    if( SDL_OpenURL( url.c_str() ) != 0 )
    {
        YIKES( std::string( "Couldn't open " ) + url + ": " + SDL_GetError() );
        return false;
    }
    return true;
}
