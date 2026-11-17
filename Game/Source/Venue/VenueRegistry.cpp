#include "VenueRegistry.h"
#include "CLog.h"
#include "Core/CommandLine.h"
#include "CoreGame/TrackList.h"
#include "Config/GameSettings.h"
#include "File.h"
#include "Path.h"
#include "VFS/VFS.h"
#include <algorithm>
#include <cctype>


namespace
{
    const char* const kNoVenueJson = "no venue.json";


    std::string Lower( std::string inText )
    {
        std::transform( inText.begin(), inText.end(), inText.begin(), []( unsigned char c ) { return static_cast<char>( std::tolower( c ) ); } );
        return inText;
    }


    bool EndsWithLvl( const std::string& inText )
    {
        const std::string lower = Lower( inText );
        return lower.size() > 4 && lower.compare( lower.size() - 4, 4, ".lvl" ) == 0;
    }


    std::string LastComponent( std::string inPath )
    {
        while( !inPath.empty() && ( inPath.back() == '/' || inPath.back() == '\\' ) )
        {
            inPath.pop_back();
        }
        const size_t slash = inPath.find_last_of( "/\\" );
        return slash == std::string::npos ? inPath : inPath.substr( slash + 1 );
    }


    const VenueEntry* FindIn( const std::vector<VenueEntry>* inRegistry, const std::string& inId )
    {
        if( !inRegistry || inId.empty() )
        {
            return nullptr;
        }
        for( const VenueEntry& entry : *inRegistry )
        {
            if( entry.Id == inId )
            {
                return &entry;
            }
        }
        const std::string lower = Lower( inId );
        for( const VenueEntry& entry : *inRegistry )
        {
            if( Lower( entry.Id ) == lower )
            {
                return &entry;
            }
        }
        return nullptr;
    }


    VenueChoice SceneChoice( const VenueEntry& inEntry )
    {
        VenueChoice choice;
        choice.IsScene = true;
        choice.ScenePath = inEntry.ScenePath;
        choice.Id = inEntry.Id;
        return choice;
    }


    VenueChoice StyleChoice( int inStyle, uint32_t inHash )
    {
        VenueChoice choice;
        choice.IsScene = false;
        // 3 (and anything past the rooms) is Random: a different room each song, repeatable for a track.
        choice.Style = inStyle >= VenueRegistry::kStyleCount ? static_cast<int>( inHash % static_cast<uint32_t>( VenueRegistry::kStyleCount ) ) : std::max( inStyle, 0 );
        return choice;
    }


    // A registry id or a style name; false when it names neither.
    bool ResolveName( const VenueChoiceInputs& inInputs, const std::string& inName, VenueChoice& outChoice )
    {
        if( inName.empty() )
        {
            return false;
        }
        if( const VenueEntry* entry = FindIn( inInputs.Registry, inName ) )
        {
            outChoice = SceneChoice( *entry );
            return true;
        }
        const int style = VenueStyleFromName( inName );
        if( style >= 0 )
        {
            outChoice = StyleChoice( style, inInputs.SongHash );
            return true;
        }
        return false;
    }
}


int VenueStyleFromName( const std::string& inName )
{
    const std::string lower = Lower( inName );
    if( lower == "arena" )
    {
        return 0;
    }
    if( lower == "club" )
    {
        return 1;
    }
    if( lower == "festival" )
    {
        return 2;
    }
    return -1;
}


uint32_t VenueSongHash( const std::string& inTrackName )
{
    uint32_t hash = 2166136261u;
    for( char c : inTrackName )
    {
        hash = ( hash ^ static_cast<uint8_t>( c ) ) * 16777619u;
    }
    return hash;
}


VenueChoice ChooseVenue( const VenueChoiceInputs& inInputs )
{
    VenueChoice choice;
    if( ResolveName( inInputs, inInputs.CommandVenue, choice ) )
    {
        choice.Reason = "--venue";
        return choice;
    }
    if( EndsWithLvl( inInputs.CommandVenue ) )
    {
        choice.IsScene = true;
        choice.ScenePath = inInputs.CommandVenue;
        choice.Id = inInputs.CommandVenue;
        choice.Reason = "--venue (a scene path)";
        return choice;
    }
    if( inInputs.CommandStyle >= 0 )
    {
        choice = StyleChoice( inInputs.CommandStyle, inInputs.SongHash );
        choice.Reason = inInputs.CommandStyle >= VenueRegistry::kStyleCount ? "--venue-style (random for the song)" : "--venue-style";
        return choice;
    }
    if( inInputs.SongVenues )
    {
        if( ResolveName( inInputs, inInputs.SongVenue, choice ) )
        {
            choice.Reason = "the song's Venue";
            return choice;
        }
        if( inInputs.HasSongLocal )
        {
            choice = SceneChoice( inInputs.SongLocal );
            choice.Reason = "the song's own Venue folder";
            return choice;
        }
    }
    if( const VenueEntry* entry = FindIn( inInputs.Registry, inInputs.VenueId ) )
    {
        choice = SceneChoice( *entry );
        choice.Reason = "the player's venue (VenueId)";
        return choice;
    }
    choice = StyleChoice( inInputs.VenueStyle, inInputs.SongHash );
    choice.Reason = inInputs.VenueStyle >= VenueRegistry::kStyleCount ? "the VenueStyle setting (random for the song)" : "the VenueStyle setting";
    return choice;
}


void VenueRegistry::Reload()
{
    Reload( kVenuesRoot );
}


void VenueRegistry::Reload( const std::string& inRoot )
{
    m_venues.clear();
    m_loaded = true;
    std::vector<std::string> folders;
    VFS::Get().Enumerate( inRoot, false, [&folders]( const std::string& inPath, bool inIsDirectory )
    {
        if( inIsDirectory )
        {
            folders.push_back( inPath );
        }
    } );
    for( const std::string& folder : folders )
    {
        VenueEntry entry;
        std::string reason;
        if( LoadFolder( folder, LastComponent( folder ), false, entry, reason ) )
        {
            m_venues.push_back( std::move( entry ) );
        }
        else if( reason == kNoVenueJson )
        {
            INFO_FMT( "[Venues]", "%s has no venue.json, ignoring it", folder.c_str() );
        }
        else
        {
            YIKES_FMT( "[Venues] Skipping %s: %s", folder.c_str(), reason.c_str() );
        }
    }
    std::stable_sort( m_venues.begin(), m_venues.end(), []( const VenueEntry& a, const VenueEntry& b )
    {
        const std::string left = Lower( a.Name );
        const std::string right = Lower( b.Name );
        return left != right ? left < right : a.Id < b.Id;
    } );
}


const VenueEntry* VenueRegistry::Find( const std::string& inId ) const
{
    for( const VenueEntry& entry : m_venues )
    {
        if( entry.Id == inId )
        {
            return &entry;
        }
    }
    return nullptr;
}


bool VenueRegistry::LoadFolder( const std::string& inFolder, const std::string& inId, bool inSongLocal, VenueEntry& outEntry, std::string& outReason )
{
    // A song's directory is an absolute disk path: the VFS wants the logical "Assets/..." form.
    std::string folder = inFolder;
    if( !folder.empty() && ( folder[0] == '/' || folder[0] == '\\' || ( folder.size() > 1 && folder[1] == ':' ) ) )
    {
        const std::string local = Path( folder ).GetLocalPathString();
        if( !local.empty() )
        {
            folder = local;
        }
    }
    std::replace( folder.begin(), folder.end(), '\\', '/' );
    while( !folder.empty() && ( folder.back() == '/' || folder.back() == '\\' ) )
    {
        folder.pop_back();
    }
    std::string text;
    if( !VFS::Get().ReadText( Path( folder + "/venue.json" ), text ) )
    {
        outReason = kNoVenueJson;
        return false;
    }
    const json root = json::parse( text, nullptr, false );
    if( root.is_discarded() || !root.is_object() )
    {
        outReason = "venue.json is not valid JSON";
        return false;
    }
    const std::string scene = root.contains( "Scene" ) && root["Scene"].is_string() ? root["Scene"].get<std::string>() : std::string();
    if( scene.empty() )
    {
        outReason = "venue.json has no Scene";
        return false;
    }
    const Path scenePath( folder + "/" + scene );
    if( !scenePath.Exists )
    {
        outReason = "scene file " + scene + " is missing";
        return false;
    }
    VenueEntry entry;
    entry.Id = inId;
    entry.Folder = folder;
    entry.ScenePath = folder + "/" + scene;
    entry.Name = root.contains( "Name" ) && root["Name"].is_string() ? root["Name"].get<std::string>() : std::string();
    if( entry.Name.empty() )
    {
        entry.Name = LastComponent( folder );
    }
    entry.Author = root.contains( "Author" ) && root["Author"].is_string() ? root["Author"].get<std::string>() : std::string();
    entry.Version = root.contains( "Version" ) && root["Version"].is_number_integer() ? root["Version"].get<int>() : 1;
    entry.SongLocal = inSongLocal;
    entry.Hidden = root.contains( "Hidden" ) && root["Hidden"].is_boolean() && root["Hidden"].get<bool>();
    if( root.contains( "Preview" ) && root["Preview"].is_string() && !root["Preview"].get<std::string>().empty() )
    {
        entry.PreviewPath = folder + "/" + root["Preview"].get<std::string>();
    }
    outEntry = std::move( entry );
    return true;
}


bool VenueRegistry::ForSong( const TrackData& inTrack, VenueEntry& outEntry ) const
{
    if( inTrack.GetDirectory().empty() )
    {
        return false;
    }
    std::string directory = inTrack.GetDirectory();
    while( !directory.empty() && ( directory.back() == '/' || directory.back() == '\\' ) )
    {
        directory.pop_back();
    }
    const std::string folder = directory + "/Venue";
    std::string reason;
    if( !Path( folder + "/venue.json" ).Exists )
    {
        return false;
    }
    if( !LoadFolder( folder, "song:" + LastComponent( directory ), true, outEntry, reason ) )
    {
        YIKES_FMT( "[Venues] Skipping song venue %s: %s", folder.c_str(), reason.c_str() );
        return false;
    }
    return true;
}


VenueChoice VenueRegistry::ChooseForSong( const TrackData& inTrack ) const
{
    const GameSettings& settings = GameSettings::GetInstance();
    // A run that skipped the main menu (--play-track) hasn't scanned yet.
    if( !m_loaded )
    {
        const_cast<VenueRegistry*>( this )->Reload();
    }
    VenueChoiceInputs inputs;
    inputs.CommandVenue = CommandLine::GetString( "--venue" );
    inputs.CommandStyle = CommandLine::Has( "--venue-style" ) ? CommandLine::GetInt( "--venue-style", -1 ) : -1;
    inputs.SongVenue = inTrack.m_venueId;
    inputs.SongVenues = settings.SongVenues;
    inputs.VenueId = settings.VenueId;
    inputs.VenueStyle = settings.VenueStyle;
    inputs.SongHash = VenueSongHash( inTrack.m_trackName );
    inputs.Registry = &m_venues;
    if( inputs.SongVenues )
    {
        inputs.HasSongLocal = ForSong( inTrack, inputs.SongLocal );
    }
    const VenueChoice choice = ChooseVenue( inputs );
    if( !inputs.CommandVenue.empty() && choice.Id != inputs.CommandVenue && VenueStyleFromName( inputs.CommandVenue ) < 0 && !FindIn( &m_venues, inputs.CommandVenue ) && !EndsWithLvl( inputs.CommandVenue ) )
    {
        INFO_FMT( "[Venues]", "--venue %s matches no venue id, room or .lvl path; using the normal pick", inputs.CommandVenue.c_str() );
    }
    return choice;
}


VenueChoice VenueRegistry::ChooseRoomForSong( const TrackData& inTrack ) const
{
    const GameSettings& settings = GameSettings::GetInstance();
    VenueChoiceInputs inputs;
    const std::string command = CommandLine::GetString( "--venue" );
    inputs.CommandVenue = VenueStyleFromName( command ) >= 0 ? command : std::string();
    inputs.CommandStyle = CommandLine::Has( "--venue-style" ) ? CommandLine::GetInt( "--venue-style", -1 ) : -1;
    inputs.SongVenue = VenueStyleFromName( inTrack.m_venueId ) >= 0 ? inTrack.m_venueId : std::string();
    inputs.SongVenues = settings.SongVenues;
    inputs.VenueStyle = settings.VenueStyle;
    inputs.SongHash = VenueSongHash( inTrack.m_trackName );
    inputs.Registry = nullptr;
    return ChooseVenue( inputs );
}
