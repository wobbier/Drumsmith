#include <doctest/doctest.h>
#include "CoreGame/TrackList.h"
#include "JSON.h"
#include "Venue/VenueRegistry.h"
#include "VFS/VFS.h"
#include <filesystem>
#include <fstream>

namespace
{
    VenueEntry Entry( const std::string& inId )
    {
        VenueEntry entry;
        entry.Id = inId;
        entry.Name = inId;
        entry.ScenePath = "Assets/Venues/" + inId + "/" + inId + ".lvl";
        return entry;
    }


    // Registry: Backyard, Garage. Song-local venue "song:Folder". Everything else is off by default.
    struct Fixture
    {
        std::vector<VenueEntry> Registry{ Entry( "Backyard" ), Entry( "Garage" ) };
        VenueChoiceInputs In;
        Fixture()
        {
            In.Registry = &Registry;
            In.SongLocal = Entry( "song:Folder" );
            In.SongLocal.SongLocal = true;
        }
    };
}


TEST_CASE( "Venue registry: with nothing set the style setting decides" )
{
    Fixture f;
    f.In.VenueStyle = 2;
    VenueChoice choice = ChooseVenue( f.In );
    CHECK( !choice.IsScene );
    CHECK( choice.Style == 2 );
}


TEST_CASE( "Venue registry: Random uses the song hash like VenueShow does" )
{
    Fixture f;
    f.In.VenueStyle = 3;
    f.In.SongHash = VenueSongHash( "Some Song" );
    CHECK( ChooseVenue( f.In ).Style == static_cast<int>( f.In.SongHash % 3u ) );
    f.In.SongHash = 4;
    CHECK( ChooseVenue( f.In ).Style == 1 );
    // The hash is FNV-1a over the track name, unchanged from VenueShow::Build.
    CHECK( VenueSongHash( "" ) == 2166136261u );
    CHECK( VenueSongHash( "a" ) == ( 2166136261u ^ 'a' ) * 16777619u );
}


TEST_CASE( "Venue registry: the player's venue id beats the style, an unknown one falls through" )
{
    Fixture f;
    f.In.VenueStyle = 1;
    f.In.VenueId = "Garage";
    VenueChoice choice = ChooseVenue( f.In );
    CHECK( choice.IsScene );
    CHECK( choice.Id == "Garage" );
    CHECK( choice.ScenePath == "Assets/Venues/Garage/Garage.lvl" );
    f.In.VenueId = "Gone";
    choice = ChooseVenue( f.In );
    CHECK( !choice.IsScene );
    CHECK( choice.Style == 1 );
}


TEST_CASE( "Venue registry: the song's venue beats the player's pick when song venues are on" )
{
    Fixture f;
    f.In.VenueId = "Garage";
    f.In.SongVenue = "Backyard";
    CHECK( ChooseVenue( f.In ).Id == "Backyard" );
    f.In.SongVenue = "club";
    VenueChoice choice = ChooseVenue( f.In );
    CHECK( !choice.IsScene );
    CHECK( choice.Style == 1 );
    // Unknown: on to the song's own folder, then the player's pick.
    f.In.SongVenue = "Nowhere";
    f.In.HasSongLocal = true;
    CHECK( ChooseVenue( f.In ).Id == "song:Folder" );
    f.In.HasSongLocal = false;
    CHECK( ChooseVenue( f.In ).Id == "Garage" );
}


TEST_CASE( "Venue registry: the song field beats the song folder" )
{
    Fixture f;
    f.In.SongVenue = "Festival";
    f.In.HasSongLocal = true;
    VenueChoice choice = ChooseVenue( f.In );
    CHECK( !choice.IsScene );
    CHECK( choice.Style == 2 );
}


TEST_CASE( "Venue registry: song venues off ignores the song entirely" )
{
    Fixture f;
    f.In.SongVenues = false;
    f.In.SongVenue = "Backyard";
    f.In.HasSongLocal = true;
    f.In.VenueId = "Garage";
    CHECK( ChooseVenue( f.In ).Id == "Garage" );
    f.In.VenueId.clear();
    f.In.VenueStyle = 0;
    CHECK( !ChooseVenue( f.In ).IsScene );
}


TEST_CASE( "Venue registry: --venue-style beats the song and the player" )
{
    Fixture f;
    f.In.CommandStyle = 1;
    f.In.SongVenue = "Backyard";
    f.In.HasSongLocal = true;
    f.In.VenueId = "Garage";
    f.In.VenueStyle = 0;
    VenueChoice choice = ChooseVenue( f.In );
    CHECK( !choice.IsScene );
    CHECK( choice.Style == 1 );
    // A style past the rooms is Random.
    f.In.CommandStyle = 3;
    f.In.SongHash = 5;
    CHECK( ChooseVenue( f.In ).Style == 2 );
}


TEST_CASE( "Venue registry: --venue beats everything" )
{
    Fixture f;
    f.In.CommandStyle = 1;
    f.In.SongVenue = "Garage";
    f.In.HasSongLocal = true;
    f.In.VenueId = "Garage";
    f.In.CommandVenue = "Backyard";
    CHECK( ChooseVenue( f.In ).Id == "Backyard" );
    f.In.CommandVenue = "backyard";
    CHECK( ChooseVenue( f.In ).Id == "Backyard" );
    f.In.CommandVenue = "ARENA";
    VenueChoice choice = ChooseVenue( f.In );
    CHECK( !choice.IsScene );
    CHECK( choice.Style == 0 );
    f.In.CommandVenue = "Assets/Elsewhere/Hall.LVL";
    choice = ChooseVenue( f.In );
    CHECK( choice.IsScene );
    CHECK( choice.ScenePath == "Assets/Elsewhere/Hall.LVL" );
}


TEST_CASE( "Venue registry: an unknown --venue falls through to the rules after it" )
{
    Fixture f;
    f.In.CommandVenue = "NoSuchPlace";
    f.In.CommandStyle = 2;
    CHECK( ChooseVenue( f.In ).Style == 2 );
    f.In.CommandStyle = -1;
    f.In.VenueId = "Garage";
    CHECK( ChooseVenue( f.In ).Id == "Garage" );
}


TEST_CASE( "Venue registry: style names are case-insensitive" )
{
    CHECK( VenueStyleFromName( "Arena" ) == 0 );
    CHECK( VenueStyleFromName( "cLUB" ) == 1 );
    CHECK( VenueStyleFromName( "FESTIVAL" ) == 2 );
    CHECK( VenueStyleFromName( "random" ) == -1 );
    CHECK( VenueStyleFromName( "" ) == -1 );
}


TEST_CASE( "Venue registry: a song's Venue field round-trips through TrackData.txt" )
{
    TrackData track;
    track.m_venueId = "Backyard";
    json meta;
    track.OnSaveTrackData( meta );
    CHECK( meta["Venue"] == "Backyard" );
    TrackData loaded;
    loaded.OnLoadTrackData( meta );
    CHECK( loaded.m_venueId == "Backyard" );

    TrackData none;
    json noneMeta;
    none.OnSaveTrackData( noneMeta );
    CHECK( !noneMeta.contains( "Venue" ) );
    TrackData reloaded;
    reloaded.m_venueId = "stale";
    reloaded.OnLoadTrackData( noneMeta );
    CHECK( reloaded.m_venueId.empty() );
}


TEST_CASE( "Venue registry: Reload reads a mounted folder, skips bad venues and sorts by name" )
{
    namespace fs = std::filesystem;
    const fs::path base = fs::temp_directory_path() / "drumsmith_venue_registry_test";
    fs::remove_all( base );
    auto write = [&]( const std::string& inRelative, const std::string& inText )
    {
        fs::create_directories( ( base / inRelative ).parent_path() );
        std::ofstream( base / inRelative, std::ios::binary ) << inText;
    };
    write( "Venues/Zed/venue.json", R"({"Name":"Alpha","Author":"Me","Scene":"Zed.lvl","Preview":"p.png","Version":2})" );
    write( "Venues/Zed/Zed.lvl", "{}" );
    write( "Venues/Beta/venue.json", R"({"Name":"Beta","Scene":"Beta.lvl"})" );
    write( "Venues/Beta/Beta.lvl", "{}" );
    write( "Venues/NoScene/venue.json", R"({"Name":"Missing","Scene":"Nope.lvl"})" );
    write( "Venues/BadJson/venue.json", "{ not json" );
    write( "Venues/Empty/readme.txt", "x" );

    SharedPtr<IMountSource> mount = MakeShared<DirectoryMount>( base.string() );
    VFS::Get().Mount( "VenueTest/", mount, 500, false );
    VenueRegistry registry;
    registry.Reload( "VenueTest/Venues" );
    const std::vector<VenueEntry>& venues = registry.Get();
    REQUIRE( venues.size() == 2 );
    CHECK( venues[0].Id == "Zed" );
    CHECK( venues[0].Name == "Alpha" );
    CHECK( venues[0].Author == "Me" );
    CHECK( venues[0].Version == 2 );
    CHECK( venues[0].ScenePath == "VenueTest/Venues/Zed/Zed.lvl" );
    CHECK( venues[0].PreviewPath == "VenueTest/Venues/Zed/p.png" );
    CHECK( venues[1].Id == "Beta" );
    CHECK( venues[1].PreviewPath.empty() );
    CHECK( registry.Find( "Beta" ) != nullptr );
    CHECK( registry.Find( "NoScene" ) == nullptr );
    CHECK( registry.Find( "BadJson" ) == nullptr );
    VFS::Get().Unmount( mount );
    fs::remove_all( base );
}


TEST_CASE( "Venue registry: ForSong reads a song's Venue folder and Hidden venues load" )
{
    namespace fs = std::filesystem;
    const fs::path base = fs::temp_directory_path() / "drumsmith_venue_song_test";
    fs::remove_all( base );
    fs::create_directories( base / "Songs/My Song/Venue" );
    fs::create_directories( base / "Songs/Plain" );
    std::ofstream( base / "Songs/My Song/Venue/venue.json" ) << R"({"Name":"Local","Scene":"Room.lvl","Hidden":true})";
    std::ofstream( base / "Songs/My Song/Venue/Room.lvl" ) << "{}";
    SharedPtr<IMountSource> mount = MakeShared<DirectoryMount>( base.string() );
    VFS::Get().Mount( "VenueSong/", mount, 500, false );

    VenueRegistry registry;
    TrackData track;
    track.SetDirectory( "VenueSong/Songs/My Song/" );
    VenueEntry entry;
    REQUIRE( registry.ForSong( track, entry ) );
    CHECK( entry.Id == "song:My Song" );
    CHECK( entry.SongLocal );
    CHECK( entry.Hidden );
    CHECK( entry.ScenePath == "VenueSong/Songs/My Song/Venue/Room.lvl" );

    TrackData plain;
    plain.SetDirectory( "VenueSong/Songs/Plain" );
    CHECK( !registry.ForSong( plain, entry ) );

    // An absolute disk path becomes the logical Assets/... form.
    const std::string absolute = Path( "Assets" ).FullPath + "/DLC/Some Song/";
    CHECK( Path( absolute ).GetLocalPathString().rfind( "Assets/DLC/Some Song", 0 ) == 0 );

    VFS::Get().Unmount( mount );
    fs::remove_all( base );
}
