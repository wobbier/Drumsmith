#include "PlayerProfile.h"
#include "CLog.h"
#include "Core/CommandLine.h"
#include "CoreGame/Practice.h"
#include "Path.h"
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <sstream>

PlayerProfile::PlayerProfile()
    // --profile <file>: another profile for this run (tests and captures, which shouldn't touch the player's).
    : PlayerProfile( CommandLine::Has( "--profile" ) ? CommandLine::GetString( "--profile" ) : Path( "Profile.json" ).FullPath )
{
}


PlayerProfile::PlayerProfile( const std::string& inFile )
    : m_file( inFile )
{
    Load();
}


PlayerProfile::Outcome PlayerProfile::RecordSong( const std::string& inSongKey, const SongResult& inResult )
{
    Outcome outcome;
    if( inSongKey.empty() )
    {
        return outcome;
    }
    SongRecord& record = m_songs[inSongKey];
    // A first play is a best in every way, but only a score above nothing is worth calling one.
    outcome.NewBestScore = inResult.Score > record.BestScore;
    outcome.NewBestAccuracy = inResult.Accuracy > record.BestAccuracy;
    const bool fullCombo = inResult.TotalNotes > 0 && inResult.Missed == 0 && inResult.MaxCombo >= inResult.TotalNotes;
    outcome.FirstFullCombo = fullCombo && !record.FullCombo;

    ++record.Plays;
    record.BestScore = std::max( record.BestScore, inResult.Score );
    record.BestAccuracy = std::max( record.BestAccuracy, inResult.Accuracy );
    record.BestCombo = std::max( record.BestCombo, inResult.MaxCombo );
    record.FullCombo = record.FullCombo || fullCombo;
    RecentSongs.erase( std::remove( RecentSongs.begin(), RecentSongs.end(), inSongKey ), RecentSongs.end() );
    RecentSongs.insert( RecentSongs.begin(), inSongKey );
    if( RecentSongs.size() > kRecentSongs )
    {
        RecentSongs.resize( kRecentSongs );
    }
    Save();
    return outcome;
}


PlayerProfile::Outcome PlayerProfile::RecordLesson( const PracticeLesson& inLesson, int inBpm, double inAccuracy )
{
    Outcome outcome;
    if( inLesson.Id.empty() )
    {
        return outcome;
    }
    LessonRecord& record = m_lessons[inLesson.Id];
    ++record.Plays;
    outcome.NewBestAccuracy = inAccuracy > record.BestAccuracy;
    record.BestAccuracy = std::max( record.BestAccuracy, inAccuracy );
    if( inAccuracy >= inLesson.PassAccuracy )
    {
        record.BestBpm = std::max( record.BestBpm, inBpm );
    }
    if( !record.Passed && inLesson.Passes( inBpm, inAccuracy ) )
    {
        record.Passed = true;
        outcome.LessonPassed = true;
    }
    Save();
    return outcome;
}


const PlayerProfile::SongRecord* PlayerProfile::FindSong( const std::string& inSongKey ) const
{
    const auto it = m_songs.find( inSongKey );
    return it == m_songs.end() ? nullptr : &it->second;
}


const PlayerProfile::LessonRecord* PlayerProfile::FindLesson( const std::string& inLessonId ) const
{
    const auto it = m_lessons.find( inLessonId );
    return it == m_lessons.end() ? nullptr : &it->second;
}


int PlayerProfile::FullCombos() const
{
    return static_cast<int>( std::count_if( m_songs.begin(), m_songs.end(), []( const auto& inEntry ) { return inEntry.second.FullCombo; } ) );
}


int PlayerProfile::SongsAtAccuracy( double inAccuracy ) const
{
    return static_cast<int>( std::count_if( m_songs.begin(), m_songs.end(), [inAccuracy]( const auto& inEntry ) { return inEntry.second.BestAccuracy >= inAccuracy; } ) );
}


int PlayerProfile::LessonsPassed() const
{
    return static_cast<int>( std::count_if( m_lessons.begin(), m_lessons.end(), []( const auto& inEntry ) { return inEntry.second.Passed; } ) );
}


bool PlayerProfile::LessonPassed( const std::string& inLessonId ) const
{
    const LessonRecord* record = FindLesson( inLessonId );
    return record && record->Passed;
}


void PlayerProfile::SetLessonPassed( const std::string& inLessonId, bool inPassed )
{
    if( inLessonId.empty() )
    {
        return;
    }
    LessonRecord& record = m_lessons[inLessonId];
    record.Passed = inPassed;
}


json PlayerProfile::ToJson() const
{
    json root;
    root["Version"] = 1;
    json songs = json::object();
    for( const auto& [key, record] : m_songs )
    {
        songs[key] = {
            { "Plays", record.Plays },
            { "BestScore", record.BestScore },
            { "BestAccuracy", record.BestAccuracy },
            { "BestCombo", record.BestCombo },
            { "FullCombo", record.FullCombo },
        };
    }
    root["Songs"] = songs;
    json lessons = json::object();
    for( const auto& [id, record] : m_lessons )
    {
        lessons[id] = {
            { "Plays", record.Plays },
            { "BestAccuracy", record.BestAccuracy },
            { "BestBpm", record.BestBpm },
            { "Passed", record.Passed },
        };
    }
    root["Lessons"] = lessons;
    root["HideoutTier"] = HideoutTier;
    root["BandName"] = BandName;
    root["CompletedGigs"] = CompletedGigs;
    root["UnlockedItems"] = UnlockedItems;
    root["Notices"] = Notices;
    root["NewItems"] = NewItems;
    root["SeenTier"] = SeenTier;
    root["RecentSongs"] = RecentSongs;
    return root;
}


void PlayerProfile::FromJson( const json& inRoot )
{
    m_songs.clear();
    m_lessons.clear();
    CompletedGigs.clear();
    UnlockedItems.clear();
    Notices.clear();
    NewItems.clear();
    RecentSongs.clear();
    HideoutTier = 0;
    SeenTier = -1;
    BandName.clear();
    if( !inRoot.is_object() )
    {
        return;
    }
    if( inRoot.contains( "Songs" ) && inRoot["Songs"].is_object() )
    {
        for( const auto& [key, entry] : inRoot["Songs"].items() )
        {
            if( !entry.is_object() )
            {
                continue;
            }
            SongRecord& record = m_songs[key];
            record.Plays = entry.value( "Plays", 0 );
            record.BestScore = entry.value( "BestScore", 0 );
            record.BestAccuracy = entry.value( "BestAccuracy", 0.0 );
            record.BestCombo = entry.value( "BestCombo", 0 );
            record.FullCombo = entry.value( "FullCombo", false );
        }
    }
    if( inRoot.contains( "Lessons" ) && inRoot["Lessons"].is_object() )
    {
        for( const auto& [id, entry] : inRoot["Lessons"].items() )
        {
            if( !entry.is_object() )
            {
                continue;
            }
            LessonRecord& record = m_lessons[id];
            record.Plays = entry.value( "Plays", 0 );
            record.BestAccuracy = entry.value( "BestAccuracy", 0.0 );
            record.BestBpm = entry.value( "BestBpm", 0 );
            record.Passed = entry.value( "Passed", false );
        }
    }
    HideoutTier = std::max( 0, inRoot.value( "HideoutTier", 0 ) );
    BandName = inRoot.value( "BandName", std::string() );
    const auto readSet = [&inRoot]( const char* inKey, std::set<std::string>& outSet ) {
        if( inRoot.contains( inKey ) && inRoot[inKey].is_array() )
        {
            for( const json& value : inRoot[inKey] )
            {
                if( value.is_string() )
                {
                    outSet.insert( value.get<std::string>() );
                }
            }
        }
    };
    readSet( "CompletedGigs", CompletedGigs );
    readSet( "UnlockedItems", UnlockedItems );
    if( inRoot.contains( "NewItems" ) && inRoot["NewItems"].is_array() )
    {
        for( const json& value : inRoot["NewItems"] )
        {
            if( value.is_string() )
            {
                NewItems.push_back( value.get<std::string>() );
            }
        }
    }
    if( inRoot.contains( "Notices" ) && inRoot["Notices"].is_array() )
    {
        for( const json& value : inRoot["Notices"] )
        {
            if( value.is_string() )
            {
                Notices.push_back( value.get<std::string>() );
            }
        }
    }
    // A profile from before SeenTier: its room has been seen (no moving-in on the next visit).
    SeenTier = inRoot.contains( "SeenTier" ) ? std::max( -1, inRoot.value( "SeenTier", -1 ) ) : HideoutTier;
    if( inRoot.contains( "RecentSongs" ) && inRoot["RecentSongs"].is_array() )
    {
        for( const json& value : inRoot["RecentSongs"] )
        {
            if( value.is_string() && RecentSongs.size() < kRecentSongs )
            {
                RecentSongs.push_back( value.get<std::string>() );
            }
        }
    }
}


void PlayerProfile::Load()
{
    if( m_file.empty() )
    {
        return;
    }
    std::ifstream in( m_file, std::ios::binary );
    if( !in )
    {
        return;
    }
    std::stringstream text;
    text << in.rdbuf();
    const json root = json::parse( text.str(), nullptr, false );
    if( root.is_discarded() )
    {
        YIKES( "PlayerProfile: " + m_file + " isn't valid JSON; starting a new profile (the old file is kept as .bad)" );
        std::error_code error;
        std::filesystem::copy_file( m_file, m_file + ".bad", std::filesystem::copy_options::overwrite_existing, error );
        return;
    }
    FromJson( root );
}


void PlayerProfile::Save() const
{
    if( m_file.empty() )
    {
        return;
    }
    // Written beside the profile and renamed over it, so a crash mid-write never leaves half a file.
    const std::string temp = m_file + ".tmp";
    {
        std::ofstream out( temp, std::ios::binary | std::ios::trunc );
        if( !out )
        {
            YIKES( "PlayerProfile: couldn't write " + temp );
            return;
        }
        out << ToJson().dump( 1 );
        if( !out )
        {
            YIKES( "PlayerProfile: couldn't write " + temp );
            return;
        }
    }
    std::error_code error;
    std::filesystem::rename( temp, m_file, error );
    if( error )
    {
        YIKES( "PlayerProfile: couldn't replace " + m_file + ": " + error.message() );
    }
}
