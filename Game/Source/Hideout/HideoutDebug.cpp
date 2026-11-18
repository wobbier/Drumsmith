// The hideout's debug menu (F2 in the main menu; Docs/Hideout-and-Progression.md → Debug menu): the
// room, its items, the gigs and lesson steps, the time of day and the band's name, changed on the
// spot, so every stage of the journey can be looked at without playing to it. The player's own
// profile is copied aside before the first change (Profile.debug-backup.json beside it) and its
// Restore button puts it back.
#include "Hideout/Hideout.h"
#include "CLog.h"
#include "Config/PlayerProfile.h"
#include "CoreGame/Progression.h"
#include "Cores/UI/RmlUiCore.h"
#include "UI/UIModelUtils.h"
#include <algorithm>
#include <cstdio>
#include <filesystem>
#include <fstream>

namespace
{
    // Beside the profile: "Profile.json" keeps its copy in "Profile.debug-backup.json".
    std::string BackupFile()
    {
        const std::string& file = PlayerProfile::GetInstance().File();
        if( file.empty() )
        {
            return std::string();
        }
        const std::filesystem::path path( file );
        return ( path.parent_path() / ( path.stem().string() + ".debug-backup.json" ) ).string();
    }


    bool HasBackup()
    {
        const std::string file = BackupFile();
        std::error_code error;
        return !file.empty() && std::filesystem::exists( file, error );
    }


    // The player's profile, once, before the debug menu changes it.
    void KeepBackup()
    {
        const std::string file = BackupFile();
        if( file.empty() || HasBackup() )
        {
            return;
        }
        std::ofstream out( file, std::ios::binary | std::ios::trunc );
        out << PlayerProfile::GetInstance().ToJson().dump( 1 );
        if( !out )
        {
            YIKES( "Hideout debug: couldn't write " + file );
        }
    }


    const char* kBandNames[] = { "The Rimshots", "Paradiddle Riot", "Lawnmower Money", "Blast Beat Bakery", "Ghost Notes", "Cracked Crash" };
}


void Hideout::DebugUpdate( RmlUiCore& inUi, const char* inModel )
{
    inUi.ModelSetNumber( inModel, "debug_open", m_debugOpen ? 1 : 0 );
    if( !m_debugOpen )
    {
        return;
    }
    const PlayerProfile& profile = PlayerProfile::GetInstance();
    const Progression& progression = Progression::GetInstance();

    const auto& tiers = progression.Tiers();
    inUi.ModelSetListCount( inModel, "debug_rooms", static_cast<int>( tiers.size() ) );
    for( int i = 0; i < static_cast<int>( tiers.size() ); ++i )
    {
        std::string name = tiers[i].Name;
        if( name.rfind( "the ", 0 ) == 0 )
        {
            name = name.substr( 4 );
        }
        inUi.ModelSetItemNumber( inModel, "debug_rooms", i, "index", i );
        inUi.ModelSetItemNumber( inModel, "debug_rooms", i, "on", profile.HideoutTier == i ? 1 : 0 );
        inUi.ModelSetItemString( inModel, "debug_rooms", i, "name", name );
    }

    const auto& items = progression.Items();
    inUi.ModelSetListCount( inModel, "debug_items", static_cast<int>( items.size() ) );
    for( int i = 0; i < static_cast<int>( items.size() ); ++i )
    {
        inUi.ModelSetItemNumber( inModel, "debug_items", i, "index", i );
        inUi.ModelSetItemNumber( inModel, "debug_items", i, "on", profile.UnlockedItems.count( "item:" + items[i].Id ) > 0 ? 1 : 0 );
        inUi.ModelSetItemString( inModel, "debug_items", i, "name", items[i].Name );
        inUi.ModelSetItemString( inModel, "debug_items", i, "slot", items[i].Slot );
    }

    const auto& gigs = progression.Gigs();
    inUi.ModelSetListCount( inModel, "debug_gigs", static_cast<int>( gigs.size() ) );
    for( int i = 0; i < static_cast<int>( gigs.size() ); ++i )
    {
        inUi.ModelSetItemNumber( inModel, "debug_gigs", i, "index", i );
        inUi.ModelSetItemNumber( inModel, "debug_gigs", i, "on", profile.CompletedGigs.count( gigs[i].Id ) > 0 ? 1 : 0 );
        inUi.ModelSetItemString( inModel, "debug_gigs", i, "name", gigs[i].Name );
    }

    const auto& steps = progression.LessonSteps();
    inUi.ModelSetListCount( inModel, "debug_steps", static_cast<int>( steps.size() ) );
    for( int i = 0; i < static_cast<int>( steps.size() ); ++i )
    {
        const auto passed = std::count_if( steps[i].Lessons.begin(), steps[i].Lessons.end(), [&profile]( const std::string& inLesson ) { return profile.LessonPassed( inLesson ); } );
        char count[32];
        std::snprintf( count, sizeof( count ), "%d/%d", static_cast<int>( passed ), static_cast<int>( steps[i].Lessons.size() ) );
        inUi.ModelSetItemNumber( inModel, "debug_steps", i, "index", i );
        inUi.ModelSetItemNumber( inModel, "debug_steps", i, "on", progression.StepDone( steps[i], profile ) ? 1 : 0 );
        inUi.ModelSetItemString( inModel, "debug_steps", i, "name", steps[i].Name );
        inUi.ModelSetItemString( inModel, "debug_steps", i, "count", count );
    }

    const int minutes = static_cast<int>( ClockSeconds() / 60.0 ) % ( 24 * 60 );
    char clock[48];
    std::snprintf( clock, sizeof( clock ), "%s, %02d:%02d on the room's clock", IsDay() ? "Day" : "Night", minutes / 60, minutes % 60 );
    inUi.ModelSetString( inModel, "debug_clock", clock );
    inUi.ModelSetNumber( inModel, "debug_time", static_cast<int>( TimeOverride() ) );
    inUi.ModelSetNumber( inModel, "debug_backup", HasBackup() ? 1 : 0 );
    inUi.ModelSetNumber( inModel, "debug_freelook", m_freeLook ? 1 : 0 );
    inUi.ModelSetString( inModel, "debug_status", m_debugStatus );
}


bool Hideout::DebugEvent( const std::string& inEvent, const json& inArgs, RmlUiCore& inUi, const char* inModel )
{
    (void)inUi;
    (void)inModel;
    if( inEvent == "debug_toggle" )
    {
        m_debugOpen = !m_debugOpen;
        return true;
    }
    if( !DebugAllowed() )
    {
        return true;
    }
    PlayerProfile& profile = PlayerProfile::GetInstance();
    const Progression& progression = Progression::GetInstance();
    const int index = static_cast<int>( UIModel::ArgNumber( inArgs, 0, -1.0 ) );
    // Every change below is to the profile, which is saved: the player's own is copied aside first
    // (KeepBackup).
    const auto done = [this, &profile]( const std::string& inStatus, bool inReload, bool inEvaluate = false ) {
        profile.Save();
        m_debugStatus = inStatus;
        if( inReload )
        {
            Reload( inEvaluate );
        }
        INFO_FMT( "[Hideout]", "debug: %s", inStatus.c_str() );
        return true;
    };

    if( inEvent == "debug_room" && index >= 0 && index < static_cast<int>( progression.Tiers().size() ) )
    {
        KeepBackup();
        profile.HideoutTier = index;
        profile.SeenTier = index;
        return done( "Room: " + progression.Tiers()[index].Name, true );
    }
    if( inEvent == "debug_move_in" )
    {
        KeepBackup();
        // The room as if just moved into: the way in, and the boxes.
        profile.SeenTier = profile.HideoutTier - 1;
        return done( "Moving into " + ( progression.TierAt( profile.HideoutTier ) ? progression.TierAt( profile.HideoutTier )->Name : std::string( "the room" ) ), true );
    }
    if( inEvent == "debug_item" && index >= 0 && index < static_cast<int>( progression.Items().size() ) )
    {
        KeepBackup();
        const ProgressionItem& item = progression.Items()[index];
        const std::string key = "item:" + item.Id;
        if( profile.UnlockedItems.erase( key ) == 0 )
        {
            profile.UnlockedItems.insert( key );
            // Shown off as a new item would be.
            profile.NewItems = { item.Id };
            return done( "Unlocked " + item.Name, true );
        }
        return done( "Locked " + item.Name, true );
    }
    if( inEvent == "debug_items" )
    {
        KeepBackup();
        for( const ProgressionItem& item : progression.Items() )
        {
            if( index > 0 )
            {
                profile.UnlockedItems.insert( "item:" + item.Id );
            }
            else
            {
                profile.UnlockedItems.erase( "item:" + item.Id );
            }
        }
        return done( index > 0 ? "Every item unlocked" : "Every item locked", true );
    }
    if( inEvent == "debug_gig" && index >= 0 && index < static_cast<int>( progression.Gigs().size() ) )
    {
        KeepBackup();
        const ProgressionGig& gig = progression.Gigs()[index];
        const bool played = profile.CompletedGigs.erase( gig.Id ) == 0;
        if( played )
        {
            profile.CompletedGigs.insert( gig.Id );
        }
        return done( ( played ? "Played " : "Not played: " ) + gig.Name + " (Apply the rules to move up)", false );
    }
    if( inEvent == "debug_step" && index >= 0 && index < static_cast<int>( progression.LessonSteps().size() ) )
    {
        KeepBackup();
        const ProgressionLessonStep& step = progression.LessonSteps()[index];
        const bool pass = !progression.StepDone( step, profile );
        for( const std::string& lesson : step.Lessons )
        {
            profile.SetLessonPassed( lesson, pass );
        }
        return done( ( pass ? "Passed " : "Unpassed " ) + step.Name + " (Apply the rules for its reward)", false );
    }
    if( inEvent == "debug_time" && index >= 0 && index <= static_cast<int>( TimeOfDay::Night ) )
    {
        TimeOverride() = static_cast<TimeOfDay>( index );
        m_debugStatus = index == 0 ? "Time: the clock's" : index == 1 ? "Time: day" : "Time: night";
        Reload( false );
        return true;
    }
    if( inEvent == "debug_evaluate" )
    {
        KeepBackup();
        const std::vector<ProgressionUnlock> unlocks = progression.Evaluate( profile );
        return done( unlocks.empty() ? "The rules: nothing new" : "The rules: " + std::to_string( unlocks.size() ) + " new things", true );
    }
    if( inEvent == "debug_intro" )
    {
        Choose( -1 );
        ReplayIntro();
        m_debugStatus = m_hasIntro ? "The way in" : "This room has no way in";
        return true;
    }
    if( inEvent == "debug_tour" )
    {
        Choose( -1 );
        Tour( {} );
        m_noticeShown = false;
        m_debugStatus = std::to_string( m_reveals.size() ) + " things on the tour";
        return true;
    }
    if( inEvent == "debug_overlay" )
    {
        m_overlayHidden = !m_overlayHidden;
        return true;
    }
    if( inEvent == "debug_freelook" )
    {
        SetFreeLook( !m_freeLook );
        m_debugStatus = m_freeLook ? "Free look: right-drag to look, WASD to move, Q/E down/up, Shift faster, wheel zooms, Esc leaves" : "Free look off";
        return true;
    }
    if( inEvent == "debug_name" )
    {
        KeepBackup();
        // Round the names, then none.
        const int count = static_cast<int>( std::size( kBandNames ) );
        int next = 0;
        for( int i = 0; i < count; ++i )
        {
            if( profile.BandName == kBandNames[i] )
            {
                next = i + 1;
            }
        }
        profile.BandName = next < count ? kBandNames[next] : "";
        ApplyBandName();
        return done( profile.BandName.empty() ? "The band has no name" : "The band: " + profile.BandName, false );
    }
    if( inEvent == "debug_reset" )
    {
        KeepBackup();
        // A new player: nothing done, the basement not moved into yet.
        profile.FromJson( json::object() );
        profile.SeenTier = -1;
        return done( "A new player", true, true );
    }
    if( inEvent == "debug_restore" )
    {
        const std::string file = BackupFile();
        std::ifstream in( file, std::ios::binary );
        const json saved = in ? json::parse( in, nullptr, false ) : json();
        if( !saved.is_object() )
        {
            m_debugStatus = "No profile to put back";
            return true;
        }
        profile.FromJson( saved );
        in.close();
        std::error_code error;
        std::filesystem::remove( file, error );
        return done( "Your own profile is back", true );
    }
    if( inEvent == "debug_reload" )
    {
        m_debugStatus = "Reloaded";
        Reload( false );
        return true;
    }
    return true;
}
