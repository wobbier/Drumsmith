#pragma once
#include <map>
#include <string>

// Where to hear (and buy) a song for real: links from the song panels out to the streaming
// services. A chart can carry its own links (TrackData.txt "Links": { "Spotify": "https://..." });
// without one the link is that service's search for the artist and title.
namespace MusicLinks
{
    enum class Service : int { Spotify = 0, AppleMusic, YouTubeMusic, Count };

    // The name a chart's "Links" uses for a service, and the one a button shows.
    const char* Key( Service inService );
    const char* Name( Service inService );

    // inLinks: the chart's own links by Key (may be empty). Only http(s) links are used.
    std::string Url( Service inService, const std::string& inArtist, const std::string& inTitle, const std::map<std::string, std::string>& inLinks = {} );
    // Opens it in the player's browser; false when the system couldn't.
    bool Open( Service inService, const std::string& inArtist, const std::string& inTitle, const std::map<std::string, std::string>& inLinks = {} );
}
