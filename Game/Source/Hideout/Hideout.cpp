#include "Hideout/Hideout.h"
#include "CLog.h"
#include "Components/Camera.h"
#include "Components/Hideout/HideoutMarkers.h"
#include "Components/Transform.h"
#include "Config/PlayerProfile.h"
#include "Core/CommandLine.h"
#include "CoreGame/GigSession.h"
#include "CoreGame/Progression.h"
#include "CoreGame/TrackList.h"
#include "Cores/UI/RmlUiCore.h"
#include "Engine/World.h"
#include "Global/TrackRadio.h"
#include "Events/SceneEvents.h"
#include "UI/UIModelUtils.h"
#include "World/SceneSerializer.h"
#include "World/SceneStreaming.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <functional>

namespace
{
    const char* KindName( int inKind )
    {
        static const char* kNames[] = { "PLAY", "PRACTICE", "RADIO", "DLC", "RECORDS", "SETTINGS", "GIGS", "EXIT" };
        return inKind >= 0 && inKind < static_cast<int>( std::size( kNames ) ) ? kNames[inKind] : "";
    }


    // What the label's second line says the station is.
    const char* KindHint( int inKind )
    {
        static const char* kHints[] = { "The kit: play a song", "The practice pad: lessons", "The radio", "The laptop: more songs",
            "The wall: your records", "The mixer: settings", "The board: gigs", "Leave" };
        return inKind >= 0 && inKind < static_cast<int>( std::size( kHints ) ) ? kHints[inKind] : "";
    }


    Vector3 Lerp( const Vector3& a, const Vector3& b, float t )
    {
        return Vector3( a.x + ( b.x - a.x ) * t, a.y + ( b.y - a.y ) * t, a.z + ( b.z - a.z ) * t );
    }


    float Distance( const Vector3& a, const Vector3& b )
    {
        const float dx = a.x - b.x, dy = a.y - b.y, dz = a.z - b.z;
        return std::sqrt( dx * dx + dy * dy + dz * dz );
    }


    // Euler degrees (pitch, yaw, 0) that point a camera's local +Z from inEye at inTarget (as
    // Tools/Venues/venuegen.py look_rotation; positive pitch looks down).
    Vector3 LookRotation( const Vector3& inEye, const Vector3& inTarget )
    {
        const float dx = inTarget.x - inEye.x, dy = inTarget.y - inEye.y, dz = inTarget.z - inEye.z;
        const float horizontal = std::sqrt( dx * dx + dz * dz );
        constexpr float kDegrees = 57.29578f;
        return Vector3( std::atan2( -dy, horizontal ) * kDegrees, std::atan2( dx, dz ) * kDegrees, 0.f );
    }


    std::string Percent( float inValue )
    {
        char text[24];
        std::snprintf( text, sizeof( text ), "%.2f%%", inValue );
        return text;
    }
}


Hideout::~Hideout()
{
    if( m_ready )
    {
        TrackRadio::GetInstance().SetSpeaker( 1.f, 0.f, 1.f );
    }
}


void Hideout::ApplyRadio( float inDeltaTime )
{
    const auto radio = std::find_if( m_stations.begin(), m_stations.end(), []( const Station& inStation ) { return inStation.Kind == static_cast<int>( HideoutStation::Kind::Radio ); } );
    if( radio == m_stations.end() )
    {
        return;
    }
    const bool atRadio = m_chosen == static_cast<int>( radio - m_stations.begin() );
    // From across the room a small speaker, a little more of the song the nearer the camera is;
    // at the radio, all of it.
    const float distance = Distance( m_current.Eye, radio->Position );
    const float goal = atRadio ? 1.f : 0.35f * std::clamp( 1.f - ( distance - 1.5f ) / 4.f, 0.f, 1.f );
    m_radioOpen += ( goal - m_radioOpen ) * ( 1.f - std::exp( -inDeltaTime * 3.f ) );
    // Panned to where it is: right of the camera is +1.
    const Vector3 forward = m_current.Target - m_current.Eye;
    const Vector3 toRadio = radio->Position - m_current.Eye;
    const float flat = std::sqrt( forward.x * forward.x + forward.z * forward.z );
    const float toLength = std::sqrt( toRadio.x * toRadio.x + toRadio.z * toRadio.z );
    float pan = 0.f;
    if( flat > 0.01f && toLength > 0.01f )
    {
        const float rightX = forward.z / flat, rightZ = -forward.x / flat;
        pan = ( toRadio.x * rightX + toRadio.z * rightZ ) / toLength * 0.7f * ( 1.f - m_radioOpen );
    }
    TrackRadio::GetInstance().SetSpeaker( m_radioOpen, pan, 0.7f + 0.3f * m_radioOpen );
}


const std::vector<const char*>& Hideout::Events()
{
    static const std::vector<const char*> kEvents = { "station", "hideout_back", "dismiss_notice", "gig_play" };
    return kEvents;
}


void Hideout::RegisterModel( RmlUiCore& inUi, const char* inModel )
{
    inUi.ModelSetNumber( inModel, "hideout", 0 );
    inUi.ModelSetNumber( inModel, "hideout_focus", -1 );
    for( const char* key : { "hideout_room", "hideout_room_text", "hideout_goal", "hideout_panel", "hideout_notice", "hideout_title", "hideout_hint", "hideout_status" } )
    {
        inUi.ModelSetString( inModel, key, "" );
    }
    inUi.ModelSetListCount( inModel, "stations", 0 );
    inUi.ModelSetListCount( inModel, "records", 0 );
    inUi.ModelSetListCount( inModel, "gigs", 0 );
}


bool Hideout::Start( World& inWorld, const EntityHandle& inCamera )
{
    Clear();
    // Home: a gig left some other way than its own buttons is over.
    GigSession::GetInstance().End();
    m_world = &inWorld;
    m_camera = inCamera;
    PlayerProfile& profile = PlayerProfile::GetInstance();
    const Progression& progression = Progression::GetInstance();
    // A first visit gets the first room's things; anything a rules change opened shows too.
    if( !progression.Evaluate( profile ).empty() )
    {
        profile.Save();
    }
    const ProgressionTier* tier = progression.TierAt( profile.HideoutTier );
    std::string scenePath = tier ? tier->Scene : std::string();
    static const std::string kCommandRoom = CommandLine::GetString( "--hideout-room" );
    if( !kCommandRoom.empty() )
    {
        scenePath = kCommandRoom;
    }
    if( scenePath.empty() )
    {
        return false;
    }
    json scene = SceneStreaming::ReadScene( scenePath );
    if( scene.is_null() || !scene.is_object() )
    {
        YIKES( "Hideout: can't read " + scenePath + "; the menu stays flat" );
        return false;
    }
    SceneSerializer::RemapAssetReferences( scene, scenePath );
    SceneSerializer::LoadOptions options;
    options.RemapGUIDs = true;
    options.LoadCores = false;
    m_roots = SceneSerializer::Deserialize( inWorld, scene, options );
    if( m_roots.empty() )
    {
        YIKES( "Hideout: " + scenePath + " has no entities" );
        return false;
    }

    // Every entity under the roots, parents first.
    std::vector<Entity*> entities;
    const std::function<void( Transform& )> walk = [&]( Transform& inTransform ) {
        if( Entity* entity = inTransform.Parent.Get() ) entities.push_back( entity );
        for( Transform* child : inTransform.GetChildren() )
        {
            if( child ) walk( *child );
        }
    };
    for( const EntityHandle& root : m_roots )
    {
        if( root && root->TryGetComponent<Transform>() ) walk( root->GetComponent<Transform>() );
    }

    bool hasView = false;
    int hidden = 0;
    for( Entity* entity : entities )
    {
        Transform* transform = entity->TryGetComponent<Transform>();
        if( !transform )
        {
            continue;
        }
        if( HideoutView* view = entity->TryGetComponent<HideoutView>() )
        {
            m_overview.Eye = transform->GetWorldPosition();
            // Local +Z, ten metres out, is what the overview looks at.
            const Vector3 euler = transform->GetRotationEuler();
            constexpr float kRadians = 0.01745329f;
            const float pitch = euler.x * kRadians, yaw = euler.y * kRadians;
            m_overview.Target = m_overview.Eye + Vector3( std::sin( yaw ) * std::cos( pitch ), -std::sin( pitch ), std::cos( yaw ) * std::cos( pitch ) ) * 10.f;
            m_overview.FieldOfView = view->FieldOfView;
            hasView = true;
        }
        if( HideoutStation* marker = entity->TryGetComponent<HideoutStation>() )
        {
            Station station;
            station.Kind = static_cast<int>( marker->Station );
            station.Label = marker->Label.empty() ? KindName( station.Kind ) : marker->Label;
            station.Position = transform->GetWorldPosition();
            station.ViewOffset = marker->ViewOffset;
            station.FieldOfView = marker->FieldOfView;
            m_stations.push_back( station );
        }
        if( HideoutItemSlot* slot = entity->TryGetComponent<HideoutItemSlot>() )
        {
            // The slot's item, when one names it: away until it's unlocked.
            for( const ProgressionItem& item : progression.Items() )
            {
                if( item.Slot == slot->Slot && profile.UnlockedItems.count( "item:" + item.Id ) == 0 && !progression.UnlockAll )
                {
                    entity->MarkForDelete();
                    ++hidden;
                    break;
                }
            }
        }
    }
    if( !hasView )
    {
        m_overview.Eye = Vector3( 0.f, 1.7f, -3.f );
        m_overview.Target = Vector3( 0.f, 1.f, 2.f );
    }
    m_notices = profile.Notices;
    m_noticeShown = !m_notices.empty();
    if( !profile.Notices.empty() )
    {
        profile.Notices.clear();
        profile.Save();
    }
    m_ready = true;
    INFO_FMT( "[Hideout]", "%s: %d stations, %d locked items hidden, %d notices", scenePath.c_str(), static_cast<int>( m_stations.size() ), hidden, static_cast<int>( m_notices.size() ) );
    // --gig <id> [--gig-songs N] plays a gig straight away, once (for headless checks).
    static bool gigStarted = false;
    static const std::string kGig = CommandLine::GetString( "--gig" );
    if( !kGig.empty() && !gigStarted )
    {
        gigStarted = true;
        if( const ProgressionGig* gig = progression.FindGig( kGig ) )
        {
            std::vector<int> setlist = progression.Setlist( *gig, TrackDatabase::GetInstance().m_trackList.m_tracks );
            const int songs = CommandLine::GetInt( "--gig-songs", 0 );
            if( songs > 0 && songs < static_cast<int>( setlist.size() ) )
            {
                setlist.resize( static_cast<size_t>( songs ) );
            }
            GigSession& session = GigSession::GetInstance();
            if( session.Begin( *gig, setlist ) && session.LaunchCurrent() )
            {
                INFO_FMT( "[Hideout]", "--gig %s: %d songs", kGig.c_str(), static_cast<int>( setlist.size() ) );
            }
        }
        else
        {
            YIKES( "Hideout: --gig " + kGig + " is no gig" );
        }
    }
    // --hideout-station N starts at a station (for headless captures).
    static const int kStartStation = CommandLine::GetInt( "--hideout-station", -1 );
    if( kStartStation >= 0 && kStartStation < static_cast<int>( m_stations.size() ) )
    {
        m_chosen = kStartStation;
        m_chosenAge = 10.f;
        m_actionDone = false;
        m_current = PoseOf( kStartStation );
        m_hasCurrent = true;
    }
    return true;
}


void Hideout::Clear()
{
    for( EntityHandle& root : m_roots )
    {
        if( root ) root->MarkForDelete();
    }
    m_roots.clear();
    m_stations.clear();
    m_ready = false;
    m_chosen = -1;
    m_panel.clear();
    m_hasCurrent = false;
}


Hideout::Pose Hideout::PoseOf( int inStation ) const
{
    if( inStation < 0 || inStation >= static_cast<int>( m_stations.size() ) )
    {
        return m_overview;
    }
    const Station& station = m_stations[inStation];
    Pose pose;
    pose.Target = station.Position;
    pose.Eye = station.Position + station.ViewOffset;
    pose.FieldOfView = station.FieldOfView;
    // The station's panel covers the left of the screen, so aim left of the station: it sits
    // right of centre, in the part of the picture left open.
    Vector3 forward = pose.Target - pose.Eye;
    const float distance = std::sqrt( forward.x * forward.x + forward.y * forward.y + forward.z * forward.z );
    const float flat = std::sqrt( forward.x * forward.x + forward.z * forward.z );
    if( distance > 0.01f && flat > 0.01f )
    {
        // Right of a camera looking along forward, with y up: cross( up, forward ), flattened.
        const Vector3 right( forward.z / flat, 0.f, -forward.x / flat );
        const float shift = distance * std::tan( pose.FieldOfView * 0.5f * 0.01745329f ) * 0.5f;
        pose.Target = pose.Target - right * shift;
    }
    return pose;
}


void Hideout::Choose( int inStation )
{
    m_chosen = inStation;
    m_chosenAge = 0.f;
    m_actionDone = inStation < 0;
    m_panel.clear();
    m_status.clear();
}


bool Hideout::Back()
{
    if( !m_ready )
    {
        return false;
    }
    if( m_noticeShown )
    {
        m_noticeShown = false;
        return true;
    }
    if( m_chosen >= 0 )
    {
        Choose( -1 );
        return true;
    }
    return false;
}


void Hideout::ApplyCamera( float inDeltaTime )
{
    if( !m_camera )
    {
        return;
    }
    const Pose goal = PoseOf( m_chosen );
    if( !m_hasCurrent )
    {
        m_current = goal;
        m_hasCurrent = true;
    }
    // Eased: most of the way in about half a second.
    const float t = 1.f - std::exp( -inDeltaTime * 6.f );
    m_current.Eye = Lerp( m_current.Eye, goal.Eye, t );
    m_current.Target = Lerp( m_current.Target, goal.Target, t );
    m_current.FieldOfView += ( goal.FieldOfView - m_current.FieldOfView ) * t;
    // A slow sway in the overview, so the room doesn't look like a still.
    static float sway = 0.f;
    sway += inDeltaTime;
    Vector3 eye = m_current.Eye;
    if( m_chosen < 0 )
    {
        eye = eye + Vector3( std::sin( sway * 0.21f ) * 0.08f, std::sin( sway * 0.33f ) * 0.03f, 0.f );
    }
    Transform& transform = m_camera->GetComponent<Transform>();
    transform.SetPosition( eye );
    transform.SetRotation( LookRotation( eye, m_current.Target ) );
    if( Camera* camera = m_camera->TryGetComponent<Camera>() )
    {
        camera->SetFOV( m_current.FieldOfView );
    }
}


void Hideout::UpdateLabels( RmlUiCore& inUi, const char* inModel )
{
    Camera* camera = m_camera ? m_camera->TryGetComponent<Camera>() : nullptr;
    inUi.ModelSetListCount( inModel, "stations", static_cast<int>( m_stations.size() ) );
    if( !camera )
    {
        return;
    }
    const glm::mat4 viewProjection = camera->GetProjectionMatrix().GetInternalMatrix() * camera->WorldToCamera.GetInternalMatrix();
    for( int i = 0; i < static_cast<int>( m_stations.size() ); ++i )
    {
        const Station& station = m_stations[i];
        const glm::vec4 clip = viewProjection * glm::vec4( station.Position.x, station.Position.y, station.Position.z, 1.f );
        bool shown = clip.w > 0.05f && m_chosen < 0 && !m_noticeShown;
        float x = 0.f, y = 0.f;
        if( shown )
        {
            x = clip.x / clip.w;
            y = clip.y / clip.w;
            shown = std::abs( x ) < 1.05f && std::abs( y ) < 1.f;
        }
        inUi.ModelSetItemNumber( inModel, "stations", i, "index", i );
        inUi.ModelSetItemNumber( inModel, "stations", i, "shown", shown ? 1 : 0 );
        inUi.ModelSetItemString( inModel, "stations", i, "label", station.Label );
        inUi.ModelSetItemString( inModel, "stations", i, "hint", KindHint( station.Kind ) );
        // Kept clear of the screen's edges, so a label at the side of the room isn't cut off.
        inUi.ModelSetItemString( inModel, "stations", i, "left", Percent( std::clamp( ( x + 1.f ) * 50.f, 11.f, 89.f ) ) );
        inUi.ModelSetItemString( inModel, "stations", i, "top", Percent( std::clamp( ( 1.f - y ) * 50.f, 12.f, 90.f ) ) );
    }
}


void Hideout::FillRecords( RmlUiCore& inUi, const char* inModel ) const
{
    const PlayerProfile& profile = PlayerProfile::GetInstance();
    const Progression& progression = Progression::GetInstance();
    std::vector<std::pair<std::string, std::string>> rows;
    rows.emplace_back( "Songs played", std::to_string( profile.SongsPlayed() ) );
    rows.emplace_back( "Full combos", std::to_string( profile.FullCombos() ) );
    rows.emplace_back( "Songs at 90% or better", std::to_string( profile.SongsAtAccuracy( 90.0 ) ) );
    int lessons = 0;
    for( const ProgressionLessonStep& step : progression.LessonSteps() )
    {
        lessons += static_cast<int>( step.Lessons.size() );
    }
    rows.emplace_back( "Lessons passed", std::to_string( profile.LessonsPassed() ) + " / " + std::to_string( lessons ) );
    rows.emplace_back( "Gigs played", std::to_string( profile.CompletedGigs.size() ) + " / " + std::to_string( progression.Gigs().size() ) );
    int items = 0;
    for( const ProgressionItem& item : progression.Items() )
    {
        items += profile.UnlockedItems.count( "item:" + item.Id ) > 0 ? 1 : 0;
    }
    rows.emplace_back( "Things in the hideout", std::to_string( items ) + " / " + std::to_string( progression.Items().size() ) );
    for( const ProgressionMilestone& milestone : progression.Milestones() )
    {
        rows.emplace_back( milestone.Name, profile.UnlockedItems.count( "milestone:" + milestone.Id ) > 0 ? "Done" : "-" );
    }
    inUi.ModelSetListCount( inModel, "records", static_cast<int>( rows.size() ) );
    for( int i = 0; i < static_cast<int>( rows.size() ); ++i )
    {
        inUi.ModelSetItemString( inModel, "records", i, "name", rows[i].first );
        inUi.ModelSetItemString( inModel, "records", i, "value", rows[i].second );
    }
}


void Hideout::FillGigs( RmlUiCore& inUi, const char* inModel )
{
    const PlayerProfile& profile = PlayerProfile::GetInstance();
    const Progression& progression = Progression::GetInstance();
    const std::vector<TrackData>& tracks = TrackDatabase::GetInstance().m_trackList.m_tracks;
    const auto& gigs = progression.Gigs();
    m_setlists.assign( gigs.size(), {} );
    inUi.ModelSetListCount( inModel, "gigs", static_cast<int>( gigs.size() ) );
    for( int i = 0; i < static_cast<int>( gigs.size() ); ++i )
    {
        const ProgressionGig& gig = gigs[i];
        const bool open = progression.GigOpen( gig, profile );
        const bool done = profile.CompletedGigs.count( gig.Id ) > 0;
        std::string songs;
        if( open )
        {
            m_setlists[i] = progression.Setlist( gig, tracks );
            for( int track : m_setlists[i] )
            {
                songs += ( songs.empty() ? "" : ", " ) + tracks[track].m_trackName;
            }
            if( songs.empty() )
            {
                songs = "No songs in your library yet.";
            }
        }
        char detail[160];
        std::snprintf( detail, sizeof( detail ), "%d songs at %s. Pass with an average of %.0f%%.", gig.Songs, gig.Venue.c_str(), gig.PassAccuracy );
        inUi.ModelSetItemNumber( inModel, "gigs", i, "index", i );
        inUi.ModelSetItemNumber( inModel, "gigs", i, "open", open && !m_setlists[i].empty() ? 1 : 0 );
        inUi.ModelSetItemString( inModel, "gigs", i, "name", gig.Name );
        inUi.ModelSetItemString( inModel, "gigs", i, "description", gig.Description );
        inUi.ModelSetItemString( inModel, "gigs", i, "detail", detail );
        inUi.ModelSetItemString( inModel, "gigs", i, "songs", open ? songs : std::string() );
        inUi.ModelSetItemString( inModel, "gigs", i, "state", done ? "PLAYED" : open ? "" : "LOCKED" );
    }
}


std::string Hideout::NextGoal() const
{
    const PlayerProfile& profile = PlayerProfile::GetInstance();
    const Progression& progression = Progression::GetInstance();
    // The first open gig not yet played, else the next locked one and what it needs.
    for( const ProgressionGig& gig : progression.Gigs() )
    {
        if( profile.CompletedGigs.count( gig.Id ) == 0 && progression.GigOpen( gig, profile ) )
        {
            return "Next: play " + gig.Name + " (the gig board).";
        }
    }
    for( const ProgressionGig& gig : progression.Gigs() )
    {
        if( profile.CompletedGigs.count( gig.Id ) > 0 )
        {
            continue;
        }
        std::string need;
        for( const std::string& stepId : gig.Requires.LessonSteps )
        {
            for( const ProgressionLessonStep& step : progression.LessonSteps() )
            {
                if( step.Id == stepId && !progression.StepDone( step, profile ) )
                {
                    need += ( need.empty() ? "" : " and " ) + step.Name;
                }
            }
        }
        return need.empty() ? "Next: " + gig.Name + "." : "Next: pass " + need + " (the practice pad) to get booked for " + gig.Name + ".";
    }
    return "You've played every gig. Go for full combos.";
}


Hideout::Action Hideout::Update( float inDeltaTime, RmlUiCore& inUi, const char* inModel )
{
    if( !m_ready )
    {
        inUi.ModelSetNumber( inModel, "hideout", 0 );
        return Action::None;
    }
    ApplyCamera( inDeltaTime );
    ApplyRadio( inDeltaTime );
    UpdateLabels( inUi, inModel );
    const PlayerProfile& profile = PlayerProfile::GetInstance();
    const ProgressionTier* tier = Progression::GetInstance().TierAt( profile.HideoutTier );
    inUi.ModelSetNumber( inModel, "hideout", 1 );
    inUi.ModelSetNumber( inModel, "hideout_focus", m_chosen );
    inUi.ModelSetString( inModel, "hideout_room", tier ? tier->Name : std::string() );
    inUi.ModelSetString( inModel, "hideout_room_text", tier ? tier->Description : std::string() );
    inUi.ModelSetString( inModel, "hideout_goal", NextGoal() );
    inUi.ModelSetString( inModel, "hideout_panel", m_panel );
    inUi.ModelSetString( inModel, "hideout_status", m_status );
    std::string notice;
    if( m_noticeShown )
    {
        for( const std::string& line : m_notices )
        {
            notice += ( notice.empty() ? "" : "\n" ) + line;
        }
    }
    inUi.ModelSetString( inModel, "hideout_notice", notice );
    const bool chosen = m_chosen >= 0 && m_chosen < static_cast<int>( m_stations.size() );
    inUi.ModelSetString( inModel, "hideout_title", chosen ? m_stations[m_chosen].Label : std::string() );
    inUi.ModelSetString( inModel, "hideout_hint", chosen ? KindHint( m_stations[m_chosen].Kind ) : std::string() );

    // The station's action, once the camera has nearly arrived.
    if( !chosen || m_actionDone )
    {
        return Action::None;
    }
    m_chosenAge += inDeltaTime;
    const Pose goal = PoseOf( m_chosen );
    if( m_chosenAge < 0.35f || ( Distance( m_current.Eye, goal.Eye ) > 0.15f && m_chosenAge < 1.2f ) )
    {
        return Action::None;
    }
    m_actionDone = true;
    const auto load = []( const char* inLevel ) {
        LoadSceneEvent event;
        event.Level = inLevel;
        event.Queue();
    };
    switch( static_cast<HideoutStation::Kind>( m_stations[m_chosen].Kind ) )
    {
    case HideoutStation::Kind::Kit:
        load( "Assets/TrackList.lvl" );
        return Action::None;
    case HideoutStation::Kind::PracticePad:
        load( "Assets/Practice.lvl" );
        return Action::None;
    case HideoutStation::Kind::Laptop:
        load( "Assets/DLC.lvl" );
        return Action::None;
    case HideoutStation::Kind::Mixer:
        return Action::OpenSettings;
    case HideoutStation::Kind::Radio:
        m_panel = "radio";
        return Action::ShowRadio;
    case HideoutStation::Kind::TrophyWall:
        FillRecords( inUi, inModel );
        m_panel = "records";
        return Action::None;
    case HideoutStation::Kind::GigBoard:
        FillGigs( inUi, inModel );
        m_panel = "gigs";
        return Action::None;
    case HideoutStation::Kind::Door:
        return Action::Quit;
    }
    return Action::None;
}


bool Hideout::HandleEvent( const std::string& inEvent, const json& inArgs, RmlUiCore& inUi, const char* inModel )
{
    if( inEvent == "station" )
    {
        const int station = static_cast<int>( UIModel::ArgNumber( inArgs, 0, -1.0 ) );
        if( station >= 0 && station < static_cast<int>( m_stations.size() ) )
        {
            Choose( station );
        }
        return true;
    }
    if( inEvent == "hideout_back" )
    {
        Back();
        return true;
    }
    if( inEvent == "dismiss_notice" )
    {
        m_noticeShown = false;
        return true;
    }
    if( inEvent == "gig_play" )
    {
        const int index = static_cast<int>( UIModel::ArgNumber( inArgs, 0, -1.0 ) );
        const auto& gigs = Progression::GetInstance().Gigs();
        if( index < 0 || index >= static_cast<int>( gigs.size() ) || index >= static_cast<int>( m_setlists.size() ) || m_setlists[index].empty() )
        {
            m_status = "That gig isn't open yet.";
            return true;
        }
        GigSession& session = GigSession::GetInstance();
        if( !session.Begin( gigs[index], m_setlists[index] ) || !session.LaunchCurrent() )
        {
            session.End();
            m_status = "Couldn't start the gig.";
        }
        return true;
    }
    (void)inUi;
    (void)inModel;
    return false;
}
