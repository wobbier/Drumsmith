#include "Progression.h"
#include "CLog.h"
#include "Config/PlayerProfile.h"
#include "Core/CommandLine.h"
#include "CoreGame/TrackList.h"
#include "File.h"
#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdio>
#include <cstdint>
#include <map>
#include <set>

namespace
{
    // A story song's stand-in (Tools/Story/make_stub_songs.py): a click and a rock beat.
    constexpr const char* kStubSource = "story-stub";


    std::string Lower( std::string inText )
    {
        std::transform( inText.begin(), inText.end(), inText.begin(), []( unsigned char c ) { return static_cast<char>( std::tolower( c ) ); } );
        return inText;
    }


    std::vector<std::string> Strings( const json& inEntry, const char* inKey )
    {
        std::vector<std::string> values;
        if( inEntry.contains( inKey ) && inEntry[inKey].is_array() )
        {
            for( const json& value : inEntry[inKey] )
            {
                if( value.is_string() )
                {
                    values.push_back( value.get<std::string>() );
                }
            }
        }
        return values;
    }


    ProgressionRequirement Requirement( const json& inEntry )
    {
        ProgressionRequirement requirement;
        if( !inEntry.contains( "Requires" ) || !inEntry["Requires"].is_object() )
        {
            return requirement;
        }
        const json& need = inEntry["Requires"];
        requirement.Tier = need.value( "Tier", 0 );
        requirement.Gigs = Strings( need, "Gigs" );
        requirement.LessonSteps = Strings( need, "LessonSteps" );
        requirement.LessonsPassed = need.value( "LessonsPassed", 0 );
        requirement.SongsPlayed = need.value( "SongsPlayed", 0 );
        requirement.FullCombos = need.value( "FullCombos", 0 );
        requirement.SongsAtAccuracy = need.value( "SongsAtAccuracy", 0 );
        requirement.Accuracy = need.value( "Accuracy", 0.0 );
        requirement.StorySets = Strings( need, "StorySets" );
        requirement.Members = Strings( need, "Members" );
        return requirement;
    }


    std::vector<json> Entries( const json& inRoot, const char* inKey )
    {
        std::vector<json> entries;
        if( inRoot.contains( inKey ) && inRoot[inKey].is_array() )
        {
            for( const json& entry : inRoot[inKey] )
            {
                if( entry.is_object() && !entry.value( "Id", std::string() ).empty() )
                {
                    entries.push_back( entry );
                }
                else
                {
                    YIKES( std::string( "Progression: an entry in " ) + inKey + " has no Id; skipped" );
                }
            }
        }
        return entries;
    }


    // A song's name reduced for matching a chart to a recording: the first artist only, no
    // "- Remastered 2011" or "(feat. ...)", lower case letters and digits.
    std::string MatchName( const std::string& inText, bool inArtist )
    {
        std::string text = inText;
        if( inArtist )
        {
            text = text.substr( 0, text.find( ',' ) );
        }
        else
        {
            text = text.substr( 0, text.find( " - " ) );
            text = text.substr( 0, text.find( '(' ) );
        }
        std::string name;
        for( unsigned char c : text )
        {
            if( std::isalnum( c ) )
            {
                name += static_cast<char>( std::tolower( c ) );
            }
        }
        return name;
    }


    // Who sits in a seat, for the player: "bass" -> "bassist".
    std::string SeatPlayer( const std::string& inSeat )
    {
        static const std::map<std::string, std::string> kPlayers = { { "bass", "bassist" }, { "guitar", "guitarist" }, { "vocals", "singer" }, { "keys", "keys player" } };
        const auto it = kPlayers.find( inSeat );
        return it == kPlayers.end() ? inSeat + " player" : it->second;
    }


    // The track id of a Spotify link ("https://open.spotify.com/track/<id>?si=..."), else empty.
    std::string SpotifyId( const std::string& inLink )
    {
        const size_t track = inLink.find( "/track/" );
        if( track == std::string::npos )
        {
            return std::string();
        }
        const std::string id = inLink.substr( track + 7 );
        return id.substr( 0, id.find_first_of( "?/#" ) );
    }


    // FNV-1a: the same order for the same gig and song on every machine.
    uint32_t Hash( const std::string& inText, uint32_t inSeed = 2166136261u )
    {
        uint32_t hash = inSeed;
        for( char c : inText )
        {
            hash ^= static_cast<unsigned char>( c );
            hash *= 16777619u;
        }
        return hash;
    }
}


bool ProgressionRequirement::Empty() const
{
    return Tier <= 0 && Gigs.empty() && LessonSteps.empty() && LessonsPassed <= 0 && SongsPlayed <= 0 && FullCombos <= 0 && SongsAtAccuracy <= 0
        && StorySets.empty() && Members.empty();
}


Progression::Progression()
{
    UnlockAll = CommandLine::Has( "--unlock-all" );
    const Path file( kFile );
    if( !file.Exists )
    {
        YIKES( std::string( "Progression: no " ) + kFile + "; everything is open" );
        UnlockAll = true;
        return;
    }
    const json root = json::parse( File( file ).Read(), nullptr, false );
    if( root.is_discarded() )
    {
        YIKES( std::string( "Progression: " ) + kFile + " isn't valid JSON; everything is open" );
        UnlockAll = true;
        return;
    }
    Load( root );
    // Story mode is its own file. Without it there is no story; the rest still works.
    const Path story( kStoryFile );
    if( story.Exists )
    {
        const json storyRoot = json::parse( File( story ).Read(), nullptr, false );
        if( storyRoot.is_discarded() )
        {
            YIKES( std::string( "Progression: " ) + kStoryFile + " isn't valid JSON; no story mode" );
        }
        else
        {
            LoadStory( storyRoot );
        }
    }
}


Progression::Progression( const json& inRoot )
{
    Load( inRoot );
}


void Progression::Load( const json& inRoot )
{
    m_tiers.clear();
    m_gigs.clear();
    m_steps.clear();
    m_milestones.clear();
    m_items.clear();
    m_venues.clear();
    m_story.clear();
    m_proposed.clear();
    m_auditions.clear();
    if( !inRoot.is_object() )
    {
        return;
    }
    for( const json& entry : Entries( inRoot, "Tiers" ) )
    {
        ProgressionTier tier;
        tier.Id = entry.value( "Id", std::string() );
        tier.Name = entry.value( "Name", tier.Id );
        tier.Description = entry.value( "Description", std::string() );
        tier.Scene = entry.value( "Scene", std::string() );
        tier.Requires = Requirement( entry );
        tier.Rewards = Strings( entry, "Rewards" );
        m_tiers.push_back( std::move( tier ) );
    }
    for( const json& entry : Entries( inRoot, "Gigs" ) )
    {
        ProgressionGig gig;
        gig.Id = entry.value( "Id", std::string() );
        gig.Name = entry.value( "Name", gig.Id );
        gig.Description = entry.value( "Description", std::string() );
        gig.Venue = entry.value( "Venue", std::string() );
        gig.Songs = std::clamp( entry.value( "Songs", 3 ), 1, 20 );
        gig.MinNotesPerSecond = entry.value( "MinNotesPerSecond", 0.0 );
        gig.MaxNotesPerSecond = entry.value( "MaxNotesPerSecond", 1000.0 );
        gig.SongKeys = Strings( entry, "SongKeys" );
        gig.PassAccuracy = std::clamp( entry.value( "PassAccuracy", 70.0 ), 0.0, 100.0 );
        gig.Requires = Requirement( entry );
        gig.Rewards = Strings( entry, "Rewards" );
        m_gigs.push_back( std::move( gig ) );
    }
    for( const json& entry : Entries( inRoot, "LessonSteps" ) )
    {
        ProgressionLessonStep step;
        step.Id = entry.value( "Id", std::string() );
        step.Name = entry.value( "Name", step.Id );
        step.Lessons = Strings( entry, "Lessons" );
        step.Requires = Requirement( entry );
        step.Rewards = Strings( entry, "Rewards" );
        m_steps.push_back( std::move( step ) );
    }
    for( const json& entry : Entries( inRoot, "Milestones" ) )
    {
        ProgressionMilestone milestone;
        milestone.Id = entry.value( "Id", std::string() );
        milestone.Name = entry.value( "Name", milestone.Id );
        milestone.Description = entry.value( "Description", std::string() );
        milestone.Requires = Requirement( entry );
        milestone.Rewards = Strings( entry, "Rewards" );
        m_milestones.push_back( std::move( milestone ) );
    }
    for( const json& entry : Entries( inRoot, "Items" ) )
    {
        ProgressionItem item;
        item.Id = entry.value( "Id", std::string() );
        item.Name = entry.value( "Name", item.Id );
        item.Description = entry.value( "Description", std::string() );
        item.Slot = entry.value( "Slot", item.Id );
        m_items.push_back( std::move( item ) );
    }
    for( const json& entry : Entries( inRoot, "Venues" ) )
    {
        ProgressionVenue venue;
        venue.Id = entry.value( "Id", std::string() );
        venue.Name = entry.value( "Name", venue.Id );
        venue.Requires = Requirement( entry );
        m_venues.push_back( std::move( venue ) );
    }
    if( inRoot.contains( "Sets" ) || inRoot.contains( "Auditions" ) )
    {
        LoadStory( inRoot );
    }
}


void Progression::LoadStory( const json& inRoot )
{
    m_story.clear();
    m_proposed.clear();
    m_auditions.clear();
    if( !inRoot.is_object() )
    {
        return;
    }
    const auto readSet = []( const json& entry, std::vector<ProgressionStorySet>& outSets )
    {
        ProgressionStorySet set;
        set.Id = entry.value( "Id", std::string() );
        set.Act = entry.value( "Act", 0 );
        set.Name = entry.value( "Name", set.Id );
        set.Description = entry.value( "Description", std::string() );
        set.Venue = entry.value( "Venue", std::string() );
        set.VenueBase = entry.value( "VenueBase", std::string() );
        set.PassAccuracy = std::clamp( entry.value( "PassAccuracy", 70.0 ), 0.0, 100.0 );
        set.OneSitting = entry.value( "OneSitting", false );
        set.Continuous = entry.value( "Continuous", false );
        set.Credits = entry.value( "Credits", false );
        set.PostCredits = entry.value( "PostCredits", false );
        set.Requires = Requirement( entry );
        set.Rewards = Strings( entry, "Rewards" );
        set.MovesInto = entry.value( "MovesInto", std::string() );
        set.Audition = entry.value( "Audition", std::string() );
        if( entry.contains( "Songs" ) && entry["Songs"].is_array() )
        {
            for( const json& value : entry["Songs"] )
            {
                if( !value.is_object() )
                {
                    continue;
                }
                ProgressionStorySong song;
                song.Artist = value.value( "Artist", std::string() );
                song.Title = value.value( "Title", std::string() );
                song.Spotify = value.value( "Spotify", std::string() );
                song.Flags = Strings( value, "Flags" );
                song.Cue = value.value( "Cue", std::string() );
                for( const json& moment : value.contains( "Moments" ) && value["Moments"].is_array() ? value["Moments"] : json::array() )
                {
                    if( !moment.is_object() )
                    {
                        continue;
                    }
                    ProgressionStorySong::Moment entry;
                    entry.Cue = moment.value( "Cue", std::string() );
                    entry.Flags = Strings( moment, "Flags" );
                    entry.Caption = moment.value( "Caption", std::string() );
                    entry.CaptionSeconds = moment.value( "CaptionSeconds", 4.0 );
                    if( !entry.Cue.empty() && ( !entry.Flags.empty() || !entry.Caption.empty() ) )
                    {
                        song.Moments.push_back( std::move( entry ) );
                    }
                }
                song.Venue = value.value( "Venue", std::string() );
                song.HighwayRests = value.value( "HighwayRests", false );
                set.Songs.push_back( std::move( song ) );
            }
        }
        if( set.Songs.empty() )
        {
            YIKES( "Progression: story set " + set.Id + " has no songs; skipped" );
            return;
        }
        outSets.push_back( std::move( set ) );
    };
    for( const json& entry : Entries( inRoot, "Sets" ) )
    {
        readSet( entry, m_story );
    }
    for( const json& entry : Entries( inRoot, "ProposedSets" ) )
    {
        readSet( entry, m_proposed );
    }
    for( const json& entry : Entries( inRoot, "Auditions" ) )
    {
        ProgressionAudition audition;
        audition.Id = entry.value( "Id", std::string() );
        audition.Seat = entry.value( "Seat", std::string() );
        audition.After = entry.value( "After", std::string() );
        audition.Optional = entry.value( "Optional", false );
        audition.Description = entry.value( "Description", std::string() );
        for( const json& value : Entries( entry, "Candidates" ) )
        {
            ProgressionCandidate candidate;
            candidate.Id = value.value( "Id", std::string() );
            candidate.Name = value.value( "Name", candidate.Id );
            candidate.Description = value.value( "Description", std::string() );
            candidate.Leans = value.value( "Leans", std::string() );
            candidate.Pitch = value.value( "Pitch", std::string() );
            candidate.Body = value.value( "Body", std::string() );
            candidate.Clothes = value.value( "Clothes", std::string() );
            audition.Candidates.push_back( std::move( candidate ) );
        }
        m_auditions.push_back( std::move( audition ) );
    }
    // The story's rewards join the hideout's items (an id already there keeps its first entry).
    for( const json& entry : Entries( inRoot, "Items" ) )
    {
        ProgressionItem item;
        item.Id = entry.value( "Id", std::string() );
        if( FindItem( item.Id ) )
        {
            continue;
        }
        item.Name = entry.value( "Name", item.Id );
        item.Description = entry.value( "Description", std::string() );
        item.Slot = entry.value( "Slot", item.Id );
        m_items.push_back( std::move( item ) );
    }
}


const ProgressionGig* Progression::FindGig( const std::string& inId ) const
{
    const auto it = std::find_if( m_gigs.begin(), m_gigs.end(), [&inId]( const ProgressionGig& inGig ) { return inGig.Id == inId; } );
    return it == m_gigs.end() ? nullptr : &*it;
}


const ProgressionStorySet* Progression::FindStorySet( const std::string& inId ) const
{
    for( const std::vector<ProgressionStorySet>* sets : { &m_story, &m_proposed } )
    {
        const auto it = std::find_if( sets->begin(), sets->end(), [&inId]( const ProgressionStorySet& inSet ) { return inSet.Id == inId; } );
        if( it != sets->end() )
        {
            return &*it;
        }
    }
    return nullptr;
}


const ProgressionStorySet* Progression::FindStorySong( const TrackData& inTrack, int& outSong ) const
{
    const std::vector<TrackData> one = { inTrack };
    for( const std::vector<ProgressionStorySet>* sets : { &m_story, &m_proposed } )
    {
        for( const ProgressionStorySet& set : *sets )
        {
            const std::vector<int> setlist = StorySetlist( set, one );
            const auto it = std::find( setlist.begin(), setlist.end(), 0 );
            if( it != setlist.end() )
            {
                outSong = static_cast<int>( it - setlist.begin() );
                return &set;
            }
        }
    }
    return nullptr;
}


const ProgressionAudition* Progression::FindAudition( const std::string& inId ) const
{
    const auto it = std::find_if( m_auditions.begin(), m_auditions.end(), [&inId]( const ProgressionAudition& inAudition ) { return inAudition.Id == inId; } );
    return it == m_auditions.end() ? nullptr : &*it;
}


const ProgressionItem* Progression::FindItem( const std::string& inId ) const
{
    const auto it = std::find_if( m_items.begin(), m_items.end(), [&inId]( const ProgressionItem& inItem ) { return inItem.Id == inId; } );
    return it == m_items.end() ? nullptr : &*it;
}


const ProgressionTier* Progression::TierAt( int inTier ) const
{
    if( m_tiers.empty() )
    {
        return nullptr;
    }
    return &m_tiers[static_cast<size_t>( std::clamp( inTier, 0, static_cast<int>( m_tiers.size() ) - 1 ) )];
}


bool Progression::Holds( const ProgressionRequirement& inRequirement, const PlayerProfile& inProfile ) const
{
    if( inProfile.HideoutTier < inRequirement.Tier )
    {
        return false;
    }
    for( const std::string& gig : inRequirement.Gigs )
    {
        if( inProfile.CompletedGigs.count( gig ) == 0 )
        {
            return false;
        }
    }
    for( const std::string& id : inRequirement.LessonSteps )
    {
        const auto step = std::find_if( m_steps.begin(), m_steps.end(), [&id]( const ProgressionLessonStep& inStep ) { return inStep.Id == id; } );
        if( step == m_steps.end() || !StepDone( *step, inProfile ) )
        {
            return false;
        }
    }
    for( const std::string& id : inRequirement.StorySets )
    {
        const ProgressionStorySet* set = FindStorySet( id );
        if( !set || !StoryPassed( *set, inProfile ) )
        {
            return false;
        }
    }
    for( const std::string& seat : inRequirement.Members )
    {
        if( inProfile.BandMembers.count( seat ) == 0 )
        {
            return false;
        }
    }
    return inProfile.LessonsPassed() >= inRequirement.LessonsPassed
        && inProfile.SongsPlayed() >= inRequirement.SongsPlayed
        && inProfile.FullCombos() >= inRequirement.FullCombos
        && ( inRequirement.SongsAtAccuracy <= 0 || inProfile.SongsAtAccuracy( inRequirement.Accuracy ) >= inRequirement.SongsAtAccuracy );
}


std::string Progression::Describe( const ProgressionRequirement& inRequirement, const PlayerProfile& inProfile ) const
{
    std::vector<std::string> parts;
    if( inProfile.HideoutTier < inRequirement.Tier )
    {
        const ProgressionTier* tier = TierAt( inRequirement.Tier );
        parts.push_back( "move into " + ( tier ? tier->Name : "the next room" ) );
    }
    for( const std::string& id : inRequirement.Gigs )
    {
        if( inProfile.CompletedGigs.count( id ) == 0 )
        {
            const ProgressionGig* gig = FindGig( id );
            parts.push_back( "play " + ( gig ? gig->Name : id ) );
        }
    }
    for( const std::string& id : inRequirement.LessonSteps )
    {
        const auto step = std::find_if( m_steps.begin(), m_steps.end(), [&id]( const ProgressionLessonStep& inStep ) { return inStep.Id == id; } );
        if( step != m_steps.end() && !StepDone( *step, inProfile ) )
        {
            const auto passed = std::count_if( step->Lessons.begin(), step->Lessons.end(), [&inProfile]( const std::string& inLesson ) { return inProfile.LessonPassed( inLesson ); } );
            parts.push_back( "pass " + step->Name + " (" + std::to_string( passed ) + " of " + std::to_string( step->Lessons.size() ) + " lessons)" );
        }
    }
    for( const std::string& id : inRequirement.StorySets )
    {
        const ProgressionStorySet* set = FindStorySet( id );
        if( !set || !StoryPassed( *set, inProfile ) )
        {
            parts.push_back( "finish " + ( set ? set->Name : id ) );
        }
    }
    for( const std::string& seat : inRequirement.Members )
    {
        if( inProfile.BandMembers.count( seat ) == 0 )
        {
            parts.push_back( "find a " + SeatPlayer( seat ) );
        }
    }
    const auto count = [&parts]( int inHave, int inNeed, const char* inWhat ) {
        if( inHave < inNeed )
        {
            parts.push_back( std::to_string( inNeed ) + " " + inWhat + " (" + std::to_string( inHave ) + " so far)" );
        }
    };
    count( inProfile.LessonsPassed(), inRequirement.LessonsPassed, "lessons passed" );
    count( inProfile.SongsPlayed(), inRequirement.SongsPlayed, inRequirement.SongsPlayed == 1 ? "song played" : "songs played" );
    count( inProfile.FullCombos(), inRequirement.FullCombos, inRequirement.FullCombos == 1 ? "full combo" : "full combos" );
    if( inRequirement.SongsAtAccuracy > 0 )
    {
        char what[48];
        std::snprintf( what, sizeof( what ), "songs at %.0f%%", inRequirement.Accuracy );
        count( inProfile.SongsAtAccuracy( inRequirement.Accuracy ), inRequirement.SongsAtAccuracy, what );
    }
    std::string text;
    for( size_t i = 0; i < parts.size(); ++i )
    {
        text += ( i == 0 ? "" : i + 1 == parts.size() ? " and " : ", " ) + parts[i];
    }
    return text;
}


std::string Progression::HowToUnlock( const std::string& inItemId, const PlayerProfile& inProfile ) const
{
    const auto gives = [&inItemId]( const std::vector<std::string>& inRewards ) { return std::find( inRewards.begin(), inRewards.end(), inItemId ) != inRewards.end(); };
    const auto capital = []( std::string inText ) {
        if( !inText.empty() && inText[0] >= 'a' && inText[0] <= 'z' )
        {
            inText[0] = static_cast<char>( inText[0] - 'a' + 'A' );
        }
        return inText;
    };
    for( size_t tier = 0; tier < m_tiers.size(); ++tier )
    {
        if( gives( m_tiers[tier].Rewards ) )
        {
            if( tier == 0 )
            {
                return "Comes with " + m_tiers[tier].Name;
            }
            const std::string need = Describe( m_tiers[tier].Requires, inProfile );
            return "Move into " + m_tiers[tier].Name + ( need.empty() ? std::string() : ": " + need );
        }
    }
    for( const ProgressionGig& gig : m_gigs )
    {
        if( gives( gig.Rewards ) )
        {
            const std::string need = Describe( gig.Requires, inProfile );
            return "Play " + gig.Name + " (the gig board)" + ( need.empty() ? std::string() : "; to get booked: " + need );
        }
    }
    for( const ProgressionStorySet& set : m_story )
    {
        if( gives( set.Rewards ) )
        {
            const std::string need = StoryOpen( set, inProfile ) ? std::string() : Describe( set.Requires, inProfile );
            return "Finish " + set.Name + " (story mode)" + ( need.empty() ? std::string() : "; to get booked: " + need );
        }
    }
    for( const ProgressionLessonStep& step : m_steps )
    {
        if( gives( step.Rewards ) )
        {
            const auto passed = std::count_if( step.Lessons.begin(), step.Lessons.end(), [&inProfile]( const std::string& inLesson ) { return inProfile.LessonPassed( inLesson ); } );
            std::string text = "Pass " + step.Name + " on the practice pad (" + std::to_string( passed ) + " of " + std::to_string( step.Lessons.size() ) + " lessons)";
            const std::string open = StepOpen( step, inProfile ) ? std::string() : Describe( step.Requires, inProfile );
            return open.empty() ? text : text + "; it opens once you " + open;
        }
    }
    for( const ProgressionMilestone& milestone : m_milestones )
    {
        if( gives( milestone.Rewards ) )
        {
            const std::string need = Describe( milestone.Requires, inProfile );
            return need.empty() ? milestone.Name : capital( need );
        }
    }
    return FindItem( inItemId ) ? "Not given by anything yet" : std::string();
}


bool Progression::StepDone( const ProgressionLessonStep& inStep, const PlayerProfile& inProfile ) const
{
    return std::all_of( inStep.Lessons.begin(), inStep.Lessons.end(), [&inProfile]( const std::string& inLesson ) { return inProfile.LessonPassed( inLesson ); } );
}


bool Progression::StepOpen( const ProgressionLessonStep& inStep, const PlayerProfile& inProfile ) const
{
    // Once opened, a step stays open even if its rules change under an old profile.
    return UnlockAll || Holds( inStep.Requires, inProfile ) || inProfile.UnlockedItems.count( "step:" + inStep.Id ) > 0;
}


const ProgressionLessonStep* Progression::StepOf( const std::string& inLessonId ) const
{
    for( const ProgressionLessonStep& step : m_steps )
    {
        if( std::find( step.Lessons.begin(), step.Lessons.end(), inLessonId ) != step.Lessons.end() )
        {
            return &step;
        }
    }
    return nullptr;
}


bool Progression::LessonOpen( const std::string& inLessonId, const PlayerProfile& inProfile ) const
{
    if( UnlockAll || inProfile.UnlockedItems.count( "lesson:" + inLessonId ) > 0 || inProfile.LessonPassed( inLessonId ) )
    {
        return true;
    }
    const ProgressionLessonStep* step = StepOf( inLessonId );
    return !step || StepOpen( *step, inProfile );
}


bool Progression::VenueOpen( const std::string& inVenue, const PlayerProfile& inProfile ) const
{
    if( UnlockAll )
    {
        return true;
    }
    const std::string venue = Lower( inVenue );
    for( const ProgressionVenue& gate : m_venues )
    {
        if( Lower( gate.Id ) == venue )
        {
            return Holds( gate.Requires, inProfile ) || inProfile.UnlockedItems.count( "venue:" + gate.Id ) > 0;
        }
    }
    return true;
}


bool Progression::GigOpen( const ProgressionGig& inGig, const PlayerProfile& inProfile ) const
{
    return UnlockAll || Holds( inGig.Requires, inProfile );
}


bool Progression::StoryOpen( const ProgressionStorySet& inSet, const PlayerProfile& inProfile ) const
{
    return UnlockAll || Holds( inSet.Requires, inProfile );
}


bool Progression::StoryPassed( const ProgressionStorySet& inSet, const PlayerProfile& inProfile ) const
{
    const auto it = inProfile.Story.find( inSet.Id );
    return it != inProfile.Story.end() && it->second.Passed;
}


std::vector<int> Progression::StorySetlist( const ProgressionStorySet& inSet, const std::vector<TrackData>& inTracks ) const
{
    std::vector<int> setlist;
    for( const ProgressionStorySong& song : inSet.Songs )
    {
        // The recording the chart says it is, else the same artist and title.
        const std::string spotify = SpotifyId( song.Spotify );
        const std::string artist = MatchName( song.Artist, true );
        const std::string title = MatchName( song.Title, false );
        // [0] real charts, [1] stand-ins: a real chart found only by name still wins over the
        // stand-in carrying the link, so charting a song takes over from its stand-in.
        int byLink[2] = { -1, -1 };
        int byName[2] = { -1, -1 };
        for( int i = 0; i < static_cast<int>( inTracks.size() ) && byLink[0] < 0; ++i )
        {
            const TrackData& track = inTracks[i];
            // Not m_noteCount: most charts' TrackData.txt leaves it 0 until the notes are read.
            if( track.m_practice || track.m_calibration )
            {
                continue;
            }
            const int stub = track.m_dlcSource == kStubSource ? 1 : 0;
            const auto link = track.m_links.find( "Spotify" );
            if( !spotify.empty() && link != track.m_links.end() && SpotifyId( link->second ) == spotify )
            {
                if( byLink[stub] < 0 )
                {
                    byLink[stub] = i;
                }
            }
            else if( byName[stub] < 0 && MatchName( track.m_artistName, true ) == artist && MatchName( track.m_trackName, false ) == title )
            {
                byName[stub] = i;
            }
        }
        setlist.push_back( byLink[0] >= 0 ? byLink[0] : byName[0] >= 0 ? byName[0] : byLink[1] >= 0 ? byLink[1] : byName[1] );
    }
    return setlist;
}


int Progression::StoryNextSong( const ProgressionStorySet& inSet, const PlayerProfile& inProfile ) const
{
    const auto it = inProfile.Story.find( inSet.Id );
    if( inSet.OneSitting || it == inProfile.Story.end() )
    {
        return 0;
    }
    const std::vector<double>& banked = it->second.Banked;
    for( int i = 0; i < static_cast<int>( inSet.Songs.size() ); ++i )
    {
        if( i >= static_cast<int>( banked.size() ) || banked[i] < 0.0 )
        {
            return i;
        }
    }
    return 0;
}


double Progression::StoryAverage( const ProgressionStorySet& inSet, const PlayerProfile& inProfile ) const
{
    const auto it = inProfile.Story.find( inSet.Id );
    if( it == inProfile.Story.end() || inSet.Songs.empty() )
    {
        return 0.0;
    }
    double sum = 0.0;
    for( size_t i = 0; i < inSet.Songs.size() && i < it->second.Banked.size(); ++i )
    {
        sum += std::max( 0.0, it->second.Banked[i] );
    }
    return sum / static_cast<double>( inSet.Songs.size() );
}


std::vector<std::string> Progression::StoryFlags( const ProgressionStorySet& inSet, int inSong, const PlayerProfile& inProfile ) const
{
    // A OneSitting run plays in order, so everything before the song has happened in this run.
    const auto it = inProfile.Story.find( inSet.Id );
    std::set<std::string> flags;
    for( int i = 0; i < inSong && i < static_cast<int>( inSet.Songs.size() ); ++i )
    {
        const bool banked = it != inProfile.Story.end() && i < static_cast<int>( it->second.Banked.size() ) && it->second.Banked[i] >= 0.0;
        if( inSet.OneSitting || banked )
        {
            flags.insert( inSet.Songs[i].Flags.begin(), inSet.Songs[i].Flags.end() );
        }
    }
    return std::vector<std::string>( flags.begin(), flags.end() );
}


bool Progression::StoryFinished( const PlayerProfile& inProfile ) const
{
    return std::any_of( m_story.begin(), m_story.end(), [&]( const ProgressionStorySet& inSet ) { return inSet.Credits && StoryPassed( inSet, inProfile ); } );
}


const ProgressionAudition* Progression::PendingAudition( const PlayerProfile& inProfile ) const
{
    for( const ProgressionAudition& audition : m_auditions )
    {
        const ProgressionStorySet* after = FindStorySet( audition.After );
        const bool declined = inProfile.UnlockedItems.count( "declined:" + audition.Id ) > 0;
        if( after && StoryPassed( *after, inProfile ) && inProfile.BandMembers.count( audition.Seat ) == 0 && !declined && !audition.Candidates.empty() )
        {
            return &audition;
        }
    }
    return nullptr;
}


bool Progression::ChooseMember( const std::string& inAuditionId, const std::string& inCandidateId, PlayerProfile& ioProfile ) const
{
    const ProgressionAudition* audition = FindAudition( inAuditionId );
    if( !audition )
    {
        return false;
    }
    const auto candidate = std::find_if( audition->Candidates.begin(), audition->Candidates.end(), [&inCandidateId]( const ProgressionCandidate& inCandidate ) { return inCandidate.Id == inCandidateId; } );
    if( candidate == audition->Candidates.end() )
    {
        return false;
    }
    ioProfile.BandMembers[audition->Seat] = candidate->Id;
    return true;
}


bool Progression::DeclineAudition( const std::string& inAuditionId, PlayerProfile& ioProfile ) const
{
    const ProgressionAudition* audition = FindAudition( inAuditionId );
    if( !audition || !audition->Optional )
    {
        return false;
    }
    ioProfile.UnlockedItems.insert( "declined:" + audition->Id );
    return true;
}


double Progression::NotesPerSecond( const TrackData& inTrack )
{
    return inTrack.m_duration > 1.f ? static_cast<double>( inTrack.m_noteCount ) / inTrack.m_duration : 0.0;
}


std::vector<int> Progression::Setlist( const ProgressionGig& inGig, const std::vector<TrackData>& inTracks ) const
{
    std::vector<int> setlist;
    std::set<int> used;
    // Songs the gig names first, in its order.
    for( const std::string& key : inGig.SongKeys )
    {
        for( int i = 0; i < static_cast<int>( inTracks.size() ) && static_cast<int>( setlist.size() ) < inGig.Songs; ++i )
        {
            if( !inTracks[i].m_practice && !inTracks[i].m_calibration && used.count( i ) == 0 && TrackDatabase::FavoriteKey( inTracks[i] ) == key )
            {
                setlist.push_back( i );
                used.insert( i );
                break;
            }
        }
    }
    // Then the rest, nearest the range first (0 inside it), each distance in the gig's own order.
    struct Candidate
    {
        double Distance;
        uint32_t Order;
        int Index;
    };
    std::vector<Candidate> candidates;
    const uint32_t seed = Hash( inGig.Id );
    for( int i = 0; i < static_cast<int>( inTracks.size() ); ++i )
    {
        const TrackData& track = inTracks[i];
        if( used.count( i ) > 0 || track.m_practice || track.m_calibration || track.m_noteCount <= 0 )
        {
            continue;
        }
        const double nps = NotesPerSecond( track );
        const double distance = nps < inGig.MinNotesPerSecond ? inGig.MinNotesPerSecond - nps : nps > inGig.MaxNotesPerSecond ? nps - inGig.MaxNotesPerSecond : 0.0;
        // Rounded to half a note a second, so a song just outside the range shuffles in with its neighbours.
        candidates.push_back( { std::ceil( distance * 2.0 ) / 2.0, Hash( TrackDatabase::FavoriteKey( track ), seed ), i } );
    }
    std::sort( candidates.begin(), candidates.end(), []( const Candidate& a, const Candidate& b ) {
        return a.Distance != b.Distance ? a.Distance < b.Distance : a.Order != b.Order ? a.Order < b.Order : a.Index < b.Index;
    } );
    // One copy of a song: a library can hold the same song twice (a ChartGen chart beside the original).
    std::set<std::string> titles;
    const auto title = [&inTracks]( int inIndex ) { return Lower( inTracks[inIndex].m_artistName + "\n" + inTracks[inIndex].m_trackName ); };
    for( int index : setlist )
    {
        titles.insert( title( index ) );
    }
    for( const Candidate& candidate : candidates )
    {
        if( static_cast<int>( setlist.size() ) >= inGig.Songs )
        {
            break;
        }
        if( titles.insert( title( candidate.Index ) ).second )
        {
            setlist.push_back( candidate.Index );
        }
    }
    return setlist;
}


std::vector<ProgressionUnlock> Progression::Evaluate( PlayerProfile& ioProfile ) const
{
    std::vector<ProgressionUnlock> unlocks;
    const auto unlock = [&]( const std::string& inKind, const std::string& inId, const std::string& inText ) {
        if( ioProfile.UnlockedItems.insert( inKind + ":" + inId ).second )
        {
            unlocks.push_back( { inKind, inId, inText } );
            ioProfile.Notices.push_back( inText );
            return true;
        }
        return false;
    };
    const auto reward = [&]( const std::vector<std::string>& inRewards ) {
        for( const std::string& id : inRewards )
        {
            const ProgressionItem* item = FindItem( id );
            if( unlock( "item", id, "New for the hideout: " + ( item ? item->Name : id ) ) )
            {
                ioProfile.NewItems.push_back( id );
            }
        }
    };
    const auto moveTo = [&]( int inTier ) {
        for( int moved = ioProfile.HideoutTier + 1; moved <= inTier; ++moved )
        {
            unlock( "tier", m_tiers[moved].Id, "Moved into " + m_tiers[moved].Name );
            reward( m_tiers[moved].Rewards );
        }
        ioProfile.HideoutTier = std::max( ioProfile.HideoutTier, inTier );
    };
    // Each pass can open something the next one needs (a tier opens a gig's venue...), so go
    // round until nothing changes. Every unlock is a set insert, so this ends.
    for( int pass = 0; pass < 32; ++pass )
    {
        const size_t before = unlocks.size();
        // The hideout: the highest room whose requirement holds, never a lower one.
        for( int tier = static_cast<int>( m_tiers.size() ) - 1; tier > ioProfile.HideoutTier; --tier )
        {
            if( Holds( m_tiers[tier].Requires, ioProfile ) )
            {
                moveTo( tier );
                break;
            }
        }
        for( const ProgressionTier& tier : m_tiers )
        {
            // The first room's rewards (and any of a room moved into before its rewards existed).
            if( ioProfile.UnlockedItems.count( "tier:" + tier.Id ) > 0 || &tier == &m_tiers.front() )
            {
                reward( tier.Rewards );
            }
        }
        for( const ProgressionLessonStep& step : m_steps )
        {
            if( Holds( step.Requires, ioProfile ) && !step.Requires.Empty() )
            {
                unlock( "step", step.Id, "New lessons: " + step.Name );
            }
            if( StepDone( step, ioProfile ) && !step.Lessons.empty() )
            {
                if( unlock( "lessons", step.Id, step.Name + " passed" ) )
                {
                    reward( step.Rewards );
                }
            }
        }
        // A groove the player has already played in a song opens its lesson.
        for( const auto& [song, record] : ioProfile.Songs() )
        {
            const auto uses = SongLessons.find( song );
            if( uses == SongLessons.end() || record.Plays <= 0 )
            {
                continue;
            }
            for( const ProgressionSongLesson& use : uses->second )
            {
                if( !LessonOpen( use.Lesson, ioProfile ) )
                {
                    unlock( "lesson", use.Lesson, "New lesson: " + use.LessonName + " (you played it in " + use.SongName + ")" );
                }
            }
        }
        for( const ProgressionMilestone& milestone : m_milestones )
        {
            if( Holds( milestone.Requires, ioProfile ) && unlock( "milestone", milestone.Id, milestone.Name ) )
            {
                reward( milestone.Rewards );
            }
        }
        for( const ProgressionGig& gig : m_gigs )
        {
            if( ioProfile.CompletedGigs.count( gig.Id ) > 0 )
            {
                reward( gig.Rewards );
            }
            else if( Holds( gig.Requires, ioProfile ) && !gig.Requires.Empty() )
            {
                unlock( "gig", gig.Id, "New gig: " + gig.Name );
            }
        }
        // Story mode: a passed set gives its rewards and moves the band in; the next one is booked.
        for( const ProgressionStorySet& set : m_story )
        {
            if( StoryPassed( set, ioProfile ) )
            {
                unlock( "story", set.Id, ( set.Credits ? "The story is told: " : "Finished: " ) + set.Name );
                reward( set.Rewards );
                const auto tier = std::find_if( m_tiers.begin(), m_tiers.end(), [&set]( const ProgressionTier& inTier ) { return inTier.Id == set.MovesInto; } );
                if( tier != m_tiers.end() && tier - m_tiers.begin() > ioProfile.HideoutTier )
                {
                    moveTo( static_cast<int>( tier - m_tiers.begin() ) );
                }
            }
            else if( Holds( set.Requires, ioProfile ) && !set.Requires.Empty() )
            {
                unlock( "booking", set.Id, ( set.PostCredits ? "After the credits: " : "New booking: " ) + set.Name );
            }
        }
        if( const ProgressionAudition* audition = PendingAudition( ioProfile ) )
        {
            unlock( "audition", audition->Id, "Auditions: the band needs a " + SeatPlayer( audition->Seat ) );
        }
        for( const ProgressionVenue& venue : m_venues )
        {
            if( Holds( venue.Requires, ioProfile ) )
            {
                unlock( "venue", venue.Id, "New venue for free play: " + venue.Name );
            }
        }
        if( unlocks.size() == before )
        {
            break;
        }
    }
    return unlocks;
}
