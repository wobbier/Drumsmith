#include "Hideout/Hideout.h"
#include "CLog.h"
#include "Components/Camera.h"
#include "Components/Lighting/Light.h"
#include "Components/Graphics/Mesh.h"
#include "Components/Graphics/PostProcess.h"
#include "Materials/StandardMaterial.h"
#include "Venue/VenuePlan.h"
#include "Components/Hideout/HideoutMarkers.h"
#include "Components/Transform.h"
#include "Config/PlayerProfile.h"
#include "Core/CommandLine.h"
#include "CoreGame/GigSession.h"
#include "CoreGame/Progression.h"
#include "CoreGame/TrackList.h"
#include "Cores/UI/RmlUiCore.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "Engine/Input.h"
#include "Window/IWindow.h"
#include "File.h"
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
    m_band.Clear();
    m_kit.Clear();
}


namespace
{
    StandardMaterial* EmissiveOf( Entity& inEntity )
    {
        Mesh* mesh = inEntity.TryGetComponent<Mesh>();
        return mesh ? dynamic_cast<StandardMaterial*>( mesh->MeshMaterial.get() ) : nullptr;
    }
}


void Hideout::BuildBand( const TrackData* inTrack )
{
    m_band.Clear();
    m_chart = TrackData();
    if( inTrack )
    {
        m_chart = *inTrack;
        m_chart.LoadNoteData();
    }
    VenuePlan plan;
    for( auto& spot : plan.Members )
    {
        spot.Present = false;
    }
    auto& drums = plan.Members[VenueData::Drums];
    drums.Feet = m_drummerFeet;
    drums.Yaw = m_drummerYaw;
    drums.Present = true;
    m_band.CastSeed = m_drummerCast;
    // No song (or one with no chart): the drummer sits at the kit, idle.
    static const std::vector<NoteData> kNoNotes;
    static const std::vector<BeatData> kNoBeats;
    const bool chart = !m_chart.m_noteData.empty();
    Transform* stage = m_stage ? m_stage->TryGetComponent<Transform>() : nullptr;
    if( !stage )
    {
        return;
    }
    m_band.Build( m_kit, stage, plan, m_chart.m_venue, chart ? m_chart.m_noteData : kNoNotes, chart ? m_chart.m_beats : kNoBeats, static_cast<float>( m_chart.m_bpm ) );
}


void Hideout::UpdateDrummer( float inDeltaTime )
{
    if( !m_hasDrummer )
    {
        return;
    }
    TrackRadio& radio = TrackRadio::GetInstance();
    const TrackData* track = radio.GetCurrentTrack();
    if( track != m_bandTrack )
    {
        m_bandTrack = track;
        BuildBand( track );
    }
    if( radio.IsPlaying() )
    {
        m_bandSeconds = radio.GetPositionMS() / 1000.0;
    }
    m_band.Update( m_bandSeconds, inDeltaTime, m_drummerEnergy );
    // Out of sight (under the floor) until the drummer's body has loaded: no T-pose on the way in.
    if( Transform* stage = m_stage ? m_stage->TryGetComponent<Transform>() : nullptr )
    {
        const bool ready = m_band.BodiesReady();
        if( ready != m_bandShown )
        {
            m_bandShown = ready;
            stage->SetPosition( Vector3( 0.f, ready ? 0.f : -50.f, 0.f ) );
        }
    }
}


void Hideout::UpdateFocus( float inDeltaTime )
{
    PostProcess* post = m_camera ? m_camera->TryGetComponent<PostProcess>() : nullptr;
    if( !post || !post->DepthOfField )
    {
        return;
    }
    const float distance = Distance( m_current.Eye, m_current.Target );
    m_focus += ( distance - m_focus ) * ( 1.f - std::exp( -inDeltaTime * 5.f ) );
    post->DoFFocusDistance = m_focus;
}


void Hideout::UpdateMusic( float inDeltaTime )
{
    TrackRadio& radio = TrackRadio::GetInstance();
    const TrackData* track = radio.GetCurrentTrack();
    if( track != m_music.Track )
    {
        // A new song: its beat grid, read from the chart beside it (the database's TrackData
        // doesn't load notes until the song is played).
        m_music.Track = track;
        m_music.Beats.clear();
        m_music.Measures.clear();
        if( track && !track->m_beats.empty() )
        {
            for( const BeatData& beat : track->m_beats )
            {
                m_music.Beats.push_back( beat.m_time );
                m_music.Measures.push_back( beat.m_measure );
            }
        }
        else if( track && !track->GetDirectory().empty() )
        {
            const Path file( track->GetDirectory() + "/NoteData.txt" );
            if( file.Exists )
            {
                const json root = json::parse( File( file ).Read(), nullptr, false );
                if( root.is_object() && root.contains( "Beats" ) && root["Beats"].is_array() )
                {
                    for( const json& beat : root["Beats"] )
                    {
                        if( beat.is_array() && beat.size() >= 2 && beat[0].is_number() )
                        {
                            m_music.Beats.push_back( beat[0].get<float>() );
                            m_music.Measures.push_back( beat[1].is_number() && beat[1].get<int>() != 0 );
                        }
                    }
                }
            }
        }
    }
    const float level = radio.IsPlaying() ? radio.GetLevel() : 0.f;
    m_music.Level += ( level - m_music.Level ) * ( 1.f - std::exp( -inDeltaTime * 10.f ) );
    m_music.HasBeat = false;
    if( radio.IsPlaying() && m_music.Beats.size() >= 2 )
    {
        const float now = radio.GetPositionMS() / 1000.f;
        const auto next = std::upper_bound( m_music.Beats.begin(), m_music.Beats.end(), now );
        if( next != m_music.Beats.begin() && next != m_music.Beats.end() )
        {
            const int beat = static_cast<int>( next - m_music.Beats.begin() ) - 1;
            const float start = m_music.Beats[beat];
            const float length = std::max( 0.05f, *next - start );
            m_music.HasBeat = true;
            m_music.Beat = beat;
            m_music.BeatPhase = std::clamp( ( now - start ) / length, 0.f, 1.f );
            m_music.SinceBeat = now - start;
            m_music.Downbeat = m_music.Measures[beat];
        }
    }
    // The hit: sharp on the beat and gone by the next, harder on a bar's first beat and in a loud
    // passage. Without a beat grid, the loudness alone.
    const float loud = std::clamp( m_music.Level * 3.f, 0.25f, 1.f );
    m_music.Envelope = m_music.HasBeat ? std::exp( -m_music.SinceBeat * 7.f ) * loud * ( m_music.Downbeat ? 1.f : 0.75f ) : std::clamp( m_music.Level * 2.5f, 0.f, 1.f );
}


void Hideout::UpdateMotions( float inDeltaTime )
{
    m_time += inDeltaTime;
    constexpr float kTau = 6.2831853f;
    for( Motion& motion : m_motions )
    {
        if( !motion.Entity )
        {
            continue;
        }
        Transform* transform = motion.Entity->TryGetComponent<Transform>();
        Light* light = motion.HasLight ? motion.Entity->TryGetComponent<Light>() : nullptr;
        if( !transform )
        {
            continue;
        }
        const bool music = motion.Music && m_music.HasBeat;
        StandardMaterial* glow = motion.HasEmissive ? EmissiveOf( *motion.Entity.Get() ) : nullptr;
        // A share of how the scene left it, for the Light and the glow alike. False: neither is here.
        const auto shine = [&]( float inFactor ) {
            if( light )
            {
                light->Intensity = motion.BaseIntensity * inFactor;
            }
            if( glow )
            {
                glow->SetEmissiveIntensity( motion.BaseEmissive * inFactor );
            }
            return light || glow;
        };
        const float cycle = kTau * ( motion.Speed * m_time + motion.Phase );
        switch( static_cast<HideoutMotion::Kind>( motion.Kind ) )
        {
        case HideoutMotion::Kind::Sway:
        {
            // On the music: one way on a beat, back the other on the next.
            const float swing = music ? std::sin( 3.1415927f * ( static_cast<float>( m_music.Beat % 2 ) + m_music.BeatPhase ) ) : std::sin( cycle );
            transform->SetRotation( motion.BaseEuler + motion.Axis * ( motion.Amount * swing ) );
            break;
        }
        case HideoutMotion::Kind::Flicker:
        {
            // Restless hum, and now and then a dip (a dying tube drops right out).
            motion.DipLeft -= inDeltaTime;
            if( motion.DipLeft <= 0.f )
            {
                motion.Random = motion.Random * 1664525u + 1013904223u;
                const float roll = static_cast<float>( motion.Random >> 8 ) / 16777216.f;
                const bool dip = roll < 0.08f * motion.Speed;
                motion.Dip = dip ? motion.Amount * ( 0.5f + 0.5f * static_cast<float>( ( motion.Random >> 4 ) & 255u ) / 255.f ) : 0.f;
                motion.DipLeft = dip ? 0.04f + 0.12f * roll : 0.05f + 0.25f * roll;
            }
            const float hum = 1.f - 0.06f * motion.Amount * ( 0.5f + 0.5f * std::sin( m_time * 37.f + motion.Phase * 11.f ) );
            shine( std::max( 0.f, hum - motion.Dip ) );
            break;
        }
        case HideoutMotion::Kind::Pulse:
        {
            float pulse = 0.5f + 0.5f * std::sin( cycle );
            if( motion.Music && ( m_music.HasBeat || m_music.Level > 0.01f ) )
            {
                // Phase > 0 picks one beat of four to fire on (a chase along a string of lights).
                const int step = static_cast<int>( motion.Phase * 4.f ) % 4;
                const bool mine = motion.Phase <= 0.f || !m_music.HasBeat || m_music.Beat % 4 == step;
                pulse = mine ? m_music.Envelope : m_music.Envelope * 0.15f;
            }
            if( !shine( 1.f - motion.Amount + motion.Amount * pulse ) )
            {
                transform->SetScale( motion.BaseScale * ( 1.f + motion.Amount * pulse ) );
            }
            break;
        }
        case HideoutMotion::Kind::Spin:
            transform->SetRotation( motion.BaseEuler + motion.Axis * ( motion.Speed * m_time + motion.Phase * 360.f ) );
            break;
        case HideoutMotion::Kind::Breathe:
        {
            const float breath = 0.5f + 0.5f * std::sin( cycle );
            const Vector3 grow = motion.Axis * ( motion.Amount * breath );
            transform->SetScale( Vector3( motion.BaseScale.x * ( 1.f + grow.x ), motion.BaseScale.y * ( 1.f + grow.y ), motion.BaseScale.z * ( 1.f + grow.z ) ) );
            break;
        }
        case HideoutMotion::Kind::Blink:
        {
            const float position = motion.Speed * m_time + motion.Phase;
            const bool on = position - std::floor( position ) < motion.Amount;
            if( !shine( on ? 1.f : 0.f ) )
            {
                transform->SetScale( on ? motion.BaseScale : motion.BaseScale * 0.001f );
            }
            break;
        }
        case HideoutMotion::Kind::Pass:
        {
            // Every 1 / Speed seconds a pass of 2.5 s: across and back to dark.
            const float period = 1.f / std::max( 0.001f, motion.Speed );
            const float into = std::fmod( m_time + motion.Phase * period, period );
            const float u = std::clamp( into / 2.5f, 0.f, 1.f );
            const bool passing = into < 2.5f;
            transform->SetPosition( motion.BasePosition + motion.Axis * ( motion.Amount * ( 2.f * u - 1.f ) ) );
            shine( passing ? std::sin( 3.1415927f * u ) : 0.f );
            break;
        }
        case HideoutMotion::Kind::Bob:
        {
            const float bob = music ? m_music.Envelope : 0.5f + 0.5f * std::sin( cycle );
            transform->SetPosition( motion.BasePosition + motion.Axis * ( motion.Amount * bob ) );
            break;
        }
        }
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
    static const std::vector<const char*> kEvents = { "station", "station_hover", "hideout_back", "dismiss_notice", "gig_play" };
    return kEvents;
}


void Hideout::RegisterModel( RmlUiCore& inUi, const char* inModel )
{
    inUi.ModelSetNumber( inModel, "hideout", 0 );
    inUi.ModelSetNumber( inModel, "hideout_tier", 0 );
    inUi.ModelSetNumber( inModel, "hideout_focus", -1 );
    for( const char* key : { "hideout_room", "hideout_room_text", "hideout_goal", "hideout_panel", "hideout_notice", "hideout_title", "hideout_hint", "hideout_status", "hideout_reveal" } )
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
            // Once a session, and not when a capture asks for a station.
            static bool introPlayed = false;
            const bool capture = CommandLine::Has( "--hideout-look" ) || CommandLine::Has( "--hideout-station" ) || CommandLine::Has( "--gig" );
            const bool hasIntro = view->IntroEye.x != 0.f || view->IntroEye.y != 0.f || view->IntroEye.z != 0.f;
            if( hasIntro && !introPlayed && !capture && !CommandLine::Has( "--no-hideout-intro" ) )
            {
                introPlayed = true;
                m_intro = 0.f;
                m_introFrom.Eye = view->IntroEye;
                m_introFrom.Target = view->IntroTarget;
                m_introFrom.FieldOfView = view->FieldOfView + 8.f;
                m_current = m_introFrom;
                m_hasCurrent = true;
            }
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
    // The props' motions, but not under an item slot that was just taken away.
    std::vector<Entity*> hiddenSlots;
    for( Entity* entity : entities )
    {
        if( HideoutItemSlot* slot = entity->TryGetComponent<HideoutItemSlot>() )
        {
            for( const ProgressionItem& item : progression.Items() )
            {
                if( item.Slot == slot->Slot && profile.UnlockedItems.count( "item:" + item.Id ) == 0 && !progression.UnlockAll )
                {
                    hiddenSlots.push_back( entity );
                }
            }
        }
    }
    // The items just unlocked (PlayerProfile::NewItems), each where its slot's pieces are.
    m_reveals.clear();
    for( const std::string& id : profile.NewItems )
    {
        const ProgressionItem* item = progression.FindItem( id );
        if( !item )
        {
            continue;
        }
        for( Entity* entity : entities )
        {
            HideoutItemSlot* slot = entity->TryGetComponent<HideoutItemSlot>();
            if( !slot || slot->Slot != item->Slot )
            {
                continue;
            }
            // The middle of its pieces (a slot's own position is usually the room's origin).
            Vector3 sum;
            int count = 0;
            const std::function<void( Transform& )> gather = [&]( Transform& inTransform ) {
                for( Transform* child : inTransform.GetChildren() )
                {
                    if( !child ) continue;
                    sum = sum + child->GetWorldPosition();
                    ++count;
                    gather( *child );
                }
            };
            gather( entity->GetComponent<Transform>() );
            m_reveals.push_back( { item->Name, count > 0 ? sum * ( 1.f / static_cast<float>( count ) ) : entity->GetComponent<Transform>().GetWorldPosition() } );
            break;
        }
    }
    m_reveal = -1;
    m_motions.clear();
    for( Entity* entity : entities )
    {
        HideoutMotion* marker = entity->TryGetComponent<HideoutMotion>();
        Transform* transform = entity->TryGetComponent<Transform>();
        if( !marker || !transform )
        {
            continue;
        }
        bool hidden = false;
        for( Transform* up = transform; up && !hidden; up = up->GetParentTransform() )
        {
            hidden = std::find( hiddenSlots.begin(), hiddenSlots.end(), up->Parent.Get() ) != hiddenSlots.end();
        }
        if( hidden )
        {
            continue;
        }
        Motion motion;
        motion.Entity = transform->Parent;
        motion.Kind = static_cast<int>( marker->Motion );
        motion.Amount = marker->Amount;
        motion.Speed = marker->Speed;
        motion.Axis = marker->Axis;
        motion.Phase = marker->Phase;
        motion.Music = marker->Music;
        motion.BaseEuler = transform->GetRotationEuler();
        motion.BasePosition = transform->GetPosition();
        motion.BaseScale = transform->GetScale();
        if( Light* light = entity->TryGetComponent<Light>() )
        {
            motion.HasLight = true;
            motion.BaseIntensity = light->Intensity;
        }
        if( StandardMaterial* material = EmissiveOf( *entity ) )
        {
            if( material->EmissiveIntensity > 0.f )
            {
                motion.HasEmissive = true;
                motion.BaseEmissive = material->EmissiveIntensity;
            }
        }
        motion.Random = 0x9E3779B9u ^ static_cast<uint32_t>( m_motions.size() * 2654435761u );
        m_motions.push_back( motion );
    }
    // The hover light: off until a label is pointed at.
    m_highlight = inWorld.CreateEntity( "Hideout Hover Light" );
    if( m_highlight )
    {
        m_highlight->AddComponent<Transform>( "Hideout Hover Light" );
        Light& glow = m_highlight->AddComponent<Light>();
        glow.Color = Vector3( 1.f, 0.88f, 0.7f );
        glow.Intensity = 0.f;
        glow.Range = 2.2f;
    }
    // The drummer, at the first HideoutDrummer (built on the first update, once the radio is known).
    for( Entity* entity : entities )
    {
        if( HideoutDrummer* drummer = entity->TryGetComponent<HideoutDrummer>() )
        {
            Transform& transform = entity->GetComponent<Transform>();
            m_hasDrummer = true;
            m_drummerFeet = transform.GetWorldPosition();
            m_drummerYaw = drummer->Yaw;
            m_drummerCast = drummer->Cast;
            m_drummerEnergy = drummer->Energy;
            m_kit.Begin( inWorld );
            m_stage = m_kit.Group( "Hideout Stage", nullptr );
            break;
        }
    }
    if( !hasView )
    {
        m_overview.Eye = Vector3( 0.f, 1.7f, -3.f );
        m_overview.Target = Vector3( 0.f, 1.f, 2.f );
    }
    if( !profile.NewItems.empty() )
    {
        profile.NewItems.clear();
        profile.Save();
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
    // --hideout-look N only frames it (no action), for close-up captures.
    static const int kStartStation = CommandLine::GetInt( "--hideout-station", -1 );
    static const int kLookStation = CommandLine::GetInt( "--hideout-look", -1 );
    const int start = kLookStation >= 0 ? kLookStation : kStartStation;
    if( start >= 0 && start < static_cast<int>( m_stations.size() ) )
    {
        m_chosen = start;
        m_chosenAge = 10.f;
        m_actionDone = kLookStation >= 0;
        m_current = PoseOf( start );
        m_hasCurrent = true;
    }
    for( int i = 0; i < static_cast<int>( m_stations.size() ); ++i )
    {
        INFO_FMT( "[Hideout]", "station %d: %s", i, m_stations[i].Label.c_str() );
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
    if( m_highlight )
    {
        m_highlight->MarkForDelete();
    }
    m_highlight = EntityHandle();
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


Hideout::Pose Hideout::PoseOfReveal( const Reveal& inReveal ) const
{
    // From the middle of the room's side of it (most things are on a wall), a metre and a half
    // away and a little above.
    Pose pose;
    pose.Target = inReveal.Centre;
    Vector3 away = m_overview.Target - inReveal.Centre;
    away.y = 0.f;
    const float length = std::sqrt( away.x * away.x + away.z * away.z );
    away = length > 0.01f ? away * ( 1.f / length ) : Vector3( 0.f, 0.f, -1.f );
    pose.Eye = inReveal.Centre + away * 1.5f + Vector3( 0.f, 0.3f, 0.f );
    pose.FieldOfView = 42.f;
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
    if( m_reveal >= 0 )
    {
        m_reveal = static_cast<int>( m_reveals.size() );
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
    const Pose goal = m_reveal >= 0 && m_reveal < static_cast<int>( m_reveals.size() ) && m_chosen < 0 ? PoseOfReveal( m_reveals[m_reveal] ) : PoseOf( m_chosen );
    if( !m_hasCurrent )
    {
        m_current = goal;
        m_hasCurrent = true;
    }
    if( m_intro >= 0.f && m_chosen < 0 )
    {
        // The intro: down the stairs and into the room, eased in and out over kIntroSeconds.
        m_intro += inDeltaTime;
        const float u = std::clamp( m_intro / kIntroSeconds, 0.f, 1.f );
        const float e = u * u * u * ( u * ( u * 6.f - 15.f ) + 10.f );
        m_current.Eye = Lerp( m_introFrom.Eye, goal.Eye, e );
        m_current.Target = Lerp( m_introFrom.Target, goal.Target, e );
        m_current.FieldOfView = m_introFrom.FieldOfView + ( goal.FieldOfView - m_introFrom.FieldOfView ) * e;
        if( u >= 1.f )
        {
            m_intro = -1.f;
        }
    }
    else
    {
        // Eased: most of the way in about half a second.
        m_intro = -1.f;
        const float t = 1.f - std::exp( -inDeltaTime * 6.f );
        m_current.Eye = Lerp( m_current.Eye, goal.Eye, t );
        m_current.Target = Lerp( m_current.Target, goal.Target, t );
        m_current.FieldOfView += ( goal.FieldOfView - m_current.FieldOfView ) * t;
    }
    // A slow sway in the overview, so the room doesn't look like a still.
    static float sway = 0.f;
    sway += inDeltaTime;
    Vector3 eye = m_current.Eye;
    if( m_chosen < 0 )
    {
        eye = eye + Vector3( std::sin( sway * 0.21f ) * 0.08f, std::sin( sway * 0.33f ) * 0.03f, 0.f );
        // The camera leans a little toward the pointer, as a head turns to look.
        Vector3 lean;
        if( IWindow* window = GetEngine().GetWindow() )
        {
            const Vector2 size = window->GetSize();
            Input& input = GetEngine().GetInput();
            const Vector2 mouse = input.GetMousePosition() - input.GetMouseOffset();
            if( size.x > 1.f && size.y > 1.f && mouse.x >= 0.f && mouse.y >= 0.f && mouse.x <= size.x && mouse.y <= size.y )
            {
                lean = Vector3( ( mouse.x / size.x - 0.5f ) * 0.3f, -( mouse.y / size.y - 0.5f ) * 0.12f, 0.f );
            }
        }
        m_parallax = Lerp( m_parallax, lean, 1.f - std::exp( -inDeltaTime * 2.5f ) );
        eye = eye + m_parallax;
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
    // Where each label goes (percent of the screen), pushed apart where two would overlap: the
    // lower of the two moves down until they clear (a label is about 19% wide and 7% tall).
    struct Spot
    {
        float X = 0.f;
        float Y = 0.f;
        bool Shown = false;
    };
    std::vector<Spot> spots( m_stations.size() );
    for( int i = 0; i < static_cast<int>( m_stations.size() ); ++i )
    {
        const Station& station = m_stations[i];
        const glm::vec4 clip = viewProjection * glm::vec4( station.Position.x, station.Position.y, station.Position.z, 1.f );
        Spot& spot = spots[i];
        // Not during the intro: the labels come up once the camera is in the room.
        const bool touring = m_reveal >= 0 && m_reveal < static_cast<int>( m_reveals.size() );
        spot.Shown = clip.w > 0.05f && m_chosen < 0 && !m_noticeShown && m_intro < 0.f && !touring;
        if( spot.Shown )
        {
            const float x = clip.x / clip.w;
            const float y = clip.y / clip.w;
            spot.Shown = std::abs( x ) < 1.05f && std::abs( y ) < 1.f;
            spot.X = std::clamp( ( x + 1.f ) * 50.f, 11.f, 89.f );
            spot.Y = std::clamp( ( 1.f - y ) * 50.f, 12.f, 90.f );
        }
    }
    std::vector<int> order;
    for( int i = 0; i < static_cast<int>( spots.size() ); ++i )
    {
        if( spots[i].Shown ) order.push_back( i );
    }
    std::sort( order.begin(), order.end(), [&spots]( int a, int b ) { return spots[a].Y < spots[b].Y; } );
    constexpr float kLabelWidth = 19.f;
    constexpr float kLabelHeight = 7.f;
    for( size_t a = 0; a < order.size(); ++a )
    {
        for( size_t b = 0; b < a; ++b )
        {
            Spot& lower = spots[order[a]];
            const Spot& upper = spots[order[b]];
            if( std::abs( lower.X - upper.X ) < kLabelWidth && lower.Y - upper.Y < kLabelHeight )
            {
                lower.Y = upper.Y + kLabelHeight;
            }
        }
    }
    for( int i = 0; i < static_cast<int>( m_stations.size() ); ++i )
    {
        const Station& station = m_stations[i];
        inUi.ModelSetItemNumber( inModel, "stations", i, "index", i );
        inUi.ModelSetItemNumber( inModel, "stations", i, "shown", spots[i].Shown ? 1 : 0 );
        inUi.ModelSetItemString( inModel, "stations", i, "label", station.Label );
        inUi.ModelSetItemString( inModel, "stations", i, "hint", KindHint( station.Kind ) );
        // Each label a little crooked, its own way (the basement's labels are strips of tape).
        char tilt[32];
        std::snprintf( tilt, sizeof( tilt ), "rotate(%ddeg)", ( i * 5 ) % 7 - 3 );
        inUi.ModelSetItemString( inModel, "stations", i, "tilt", tilt );
        // Kept clear of the screen's edges (above), so a label at the side of the room isn't cut off.
        inUi.ModelSetItemString( inModel, "stations", i, "left", Percent( spots[i].X ) );
        inUi.ModelSetItemString( inModel, "stations", i, "top", Percent( std::min( spots[i].Y, 92.f ) ) );
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
    UpdateMusic( inDeltaTime );
    UpdateMotions( inDeltaTime );
    UpdateDrummer( inDeltaTime );
    UpdateFocus( inDeltaTime );
    // The new items' tour: once the notice is read and the camera is in, each new thing in turn.
    if( m_reveal < 0 && !m_reveals.empty() && !m_noticeShown && m_intro < 0.f && m_chosen < 0 )
    {
        m_reveal = 0;
        m_revealAge = 0.f;
    }
    const bool touring = m_reveal >= 0 && m_reveal < static_cast<int>( m_reveals.size() );
    if( touring )
    {
        m_revealAge += inDeltaTime;
        if( m_revealAge > 2.6f )
        {
            ++m_reveal;
            m_revealAge = 0.f;
        }
    }
    const bool showing = m_reveal >= 0 && m_reveal < static_cast<int>( m_reveals.size() );
    inUi.ModelSetString( inModel, "hideout_reveal", showing ? "NEW: " + m_reveals[m_reveal].Name : std::string() );
    // The hover light eases up over the pointed-at station (a little above it, toward the camera),
    // or over the new item being shown.
    if( m_highlight )
    {
        const bool hovering = m_hover >= 0 && m_hover < static_cast<int>( m_stations.size() ) && m_chosen < 0 && !m_noticeShown;
        const bool lit = hovering || showing;
        m_highlightLevel += ( ( lit ? 1.f : 0.f ) - m_highlightLevel ) * ( 1.f - std::exp( -inDeltaTime * 8.f ) );
        if( lit )
        {
            const Vector3 at = showing ? m_reveals[m_reveal].Centre : m_stations[m_hover].Position;
            const Vector3 toward = m_current.Eye - at;
            const float length = std::max( 0.01f, Distance( m_current.Eye, at ) );
            m_highlight->GetComponent<Transform>().SetPosition( at + toward * ( 0.7f / length ) + Vector3( 0.f, 0.35f, 0.f ) );
        }
        m_highlight->GetComponent<Light>().Intensity = 3.5f * m_highlightLevel;
    }
    UpdateLabels( inUi, inModel );
    const PlayerProfile& profile = PlayerProfile::GetInstance();
    const ProgressionTier* tier = Progression::GetInstance().TierAt( profile.HideoutTier );
    inUi.ModelSetNumber( inModel, "hideout", 1 );
    inUi.ModelSetNumber( inModel, "hideout_tier", profile.HideoutTier );
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
    if( inEvent == "station_hover" )
    {
        m_hover = static_cast<int>( UIModel::ArgNumber( inArgs, 0, -1.0 ) );
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
