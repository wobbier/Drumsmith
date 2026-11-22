#include "Venue/Director.h"
#include "Venue/Band.h"
#include "Venue/VenueLayout.h"
#include "Venue/VenuePlan.h"
#include "Venue/VenueTiming.h"
#include "Components/Camera.h"
#include "Components/Graphics/PostProcess.h"
#include "Components/Transform.h"
#include "Core/CommandLine.h"
#include "Engine/World.h"
#include "CLog.h"
#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdlib>
#include <limits>
#include <sstream>

namespace
{
    constexpr float kPi = 3.14159265f;
    constexpr float kArrivalInterval = 1.05f;
    // The end of the arrival walk, a documentary operator spotting the band: they stop, whip the
    // camera round onto the band and crash-zoom in, overshooting and hunting back, then hold it.
    constexpr float kArrivalSettle = 0.2f;  // stopped, still looking where they were walking
    constexpr float kArrivalWhip = 0.35f;   // the pan onto the band
    constexpr float kArrivalZoomStart = kArrivalSettle + kArrivalWhip * 0.55f;  // from partway through the pan
    constexpr float kArrivalZoomPeak = 0.4f;   // the zoom's overshoot, from its start
    constexpr float kArrivalOvershoot = 0.12f; // how far past (of the zoom, in log space)
    constexpr float kArrivalHold = 1.5f;       // after the peak: the pull back, the hunt, the hold
    constexpr float kArrivalTail = kArrivalZoomStart + kArrivalZoomPeak + kArrivalHold;

    bool StartsWith( const std::string& inText, const char* inPrefix )
    {
        return inText.rfind( inPrefix, 0 ) == 0;
    }

    int MemberFromLetter( char inLetter )
    {
        switch( inLetter )
        {
        case 'd': return VenueData::Drums;
        case 'g': return VenueData::Guitar;
        case 'b': return VenueData::Bass;
        case 'v': return VenueData::Vocals;
        case 'k': return VenueData::Keys;
        default: return -1;
        }
    }

    int MemberFromWord( const std::string& inWord )
    {
        if( inWord == "drums" ) return VenueData::Drums;
        if( inWord == "guitar" ) return VenueData::Guitar;
        if( inWord == "bass" ) return VenueData::Bass;
        if( inWord == "vocals" ) return VenueData::Vocals;
        if( inWord == "keys" ) return VenueData::Keys;
        return -1;
    }

    std::vector<std::string> Split( const std::string& inText, char inSeparator )
    {
        std::vector<std::string> parts;
        std::stringstream stream( inText );
        std::string part;
        while( std::getline( stream, part, inSeparator ) )
        {
            if( !part.empty() ) parts.push_back( part );
        }
        return parts;
    }

    Vector3 Lerp( const Vector3& inA, const Vector3& inB, float inT )
    {
        return inA + ( inB - inA ) * inT;
    }

    // Smooth repeatable noise in [-1, 1] along a line: a wandering value, not a swinging one.
    float Wander( float inT, uint32_t inSeed )
    {
        const float whole = std::floor( inT );
        const float t = VenueTiming::Smooth( inT - whole );
        const uint32_t cell = static_cast<uint32_t>( static_cast<int32_t>( whole ) );
        const float a = VenueTiming::Noise( cell, inSeed );
        const float b = VenueTiming::Noise( cell + 1u, inSeed );
        return ( a + ( b - a ) * t ) * 2.f - 1.f;
    }

    Vector3 Orbit( const Vector3& inEye, const Vector3& inTarget, float inDegrees )
    {
        const float angle = inDegrees * kPi / 180.f;
        const Vector3 offset = inEye - inTarget;
        const float c = std::cos( angle );
        const float s = std::sin( angle );
        return inTarget + Vector3( offset.x * c - offset.z * s, offset.y, offset.x * s + offset.z * c );
    }
}


void Director::Clear()
{
    if( m_main ) m_main->MarkForDelete();
    if( m_feed ) m_feed->MarkForDelete();
    if( m_program ) m_program->MarkForDelete();
    m_main = {};
    m_feed = {};
    m_program = {};
    m_cuts.clear();
    m_looks.clear();
    m_beats.clear();
    m_world = nullptr;
    m_band = nullptr;
    m_plan = VenuePlan();
    m_arrival.clear();
    m_peakSpots.clear();
    m_storyShots.clear();
    m_accentPhase = -1.f;
    m_arrivalElapsed = -1.f;
    m_shotName.clear();
    m_lookName.clear();
    m_rateCue = -2;
    m_rate = 0.f;
    m_feedSince = -100.0;
    m_framedCut = -2;
    m_framedShot.clear();
    m_surferUp = false;
    m_moveTime = 0.f;
    m_hype = 0.f;
    m_kick = 0.f;
    m_bigStart = -1000.0;
    m_bigEnd = -1000.0;
    m_focus = 8.f;
    m_blur = 0.f;
}


void Director::FollowSurfer( bool inUp, const Vector3& inPosition )
{
    if( inUp && !m_surferUp )
    {
        // Across the room from where they go up, so the shot looks over the crowd at them.
        m_surferSide = inPosition.x > 0.f ? -1.f : 1.f;
    }
    m_surferUp = inUp;
    m_surferPosition = inPosition;
}


void Director::Build( World& inWorld, const VenuePlan& inPlan, const VenueData& inVenue, const std::vector<BeatData>& inBeats, float inBpm, float inSongLength, bool inMusicVideo, const Band* inBand )
{
    Clear();
    m_world = &inWorld;
    m_band = inBand;
    m_plan = inPlan;
    auto& cameras = m_plan.Cameras;
    auto firstArrival = std::stable_partition( cameras.begin(), cameras.end(), []( const VenuePlan::CameraSpot& s ) {
        return s.Shot != VenuePlan::CameraSpot::Kind::Custom || !StartsWith( s.Tag, "arrival/" );
    } );
    m_arrival.assign( firstArrival, cameras.end() );
    cameras.erase( firstArrival, cameras.end() );
    for( size_t i = 0; i < cameras.size(); ++i )
        if( cameras[i].Shot == VenuePlan::CameraSpot::Kind::Custom && StartsWith( cameras[i].Tag, "peak/" ) ) m_peakSpots.push_back( static_cast<int>( i ) );
    std::sort( m_peakSpots.begin(), m_peakSpots.end(), [&]( int a, int b ) { return cameras[a].Tag < cameras[b].Tag; } );
    std::stable_sort( m_arrival.begin(), m_arrival.end(), []( const auto& a, const auto& b ) { return a.Tag < b.Tag; } );
    m_beats = inBeats;
    m_bpm = inBpm;
    const bool mv = inMusicVideo && !inVenue.m_mvCameras.empty();
    const std::vector<TimedCueData>& cuts = mv ? inVenue.m_mvCameras : inVenue.m_cameras;
    for( size_t i = 0; i < cuts.size(); ++i )
    {
        Cut cut;
        cut.Time = cuts[i].m_time;
        cut.Name = cuts[i].m_name;
        cut.Shot = PlanFor( cut.Name, static_cast<int>( i ) );
        m_cuts.push_back( cut );
    }
    if( m_cuts.empty() )
    {
        BuildFallbackCuts( inVenue, inSongLength );
    }
    else
    {
        FillAutoCuts( inVenue, inSongLength );
    }
    for( Cut& cut : m_cuts )
    {
        DropAbsent( cut.Shot );
    }
    AddNeckShots( inVenue );
    AddSpotCuts();
    if( CommandLine::Has( "--highway-log" ) )
    {
        // The cut list as it will play, chart cuts and the director's own.
        for( const Cut& cut : m_cuts )
        {
            BRUH_FMT( "Venue: cut list %.2f s %s (framing %d)", cut.Time, cut.Name.c_str(), static_cast<int>( cut.Shot.Frame ) );
        }
    }
    m_looks = mv && !inVenue.m_mvPostFx.empty() ? inVenue.m_mvPostFx : inVenue.m_postFx;
    if( m_looks.empty() )
    {
        BuildFallbackLooks( inVenue );
    }
    m_rateCue = -2;

    // The main camera: the screen's camera from now on (the highway draws over it).
    m_main = inWorld.CreateEntity( "Venue Camera" );
    if( m_main )
    {
        m_main->AddComponent<Transform>( "Venue Camera" );
        Camera& camera = m_main->AddComponent<Camera>();
        camera.Near = 0.1f;
        camera.Far = 400.f;
        camera.ClearColor = Vector3( 0.f, 0.f, 0.f );
        camera.ClearType = Moonlight::ClearColorType::Color;
        camera.SetCurrent();
        PostProcess& post = m_main->AddComponent<PostProcess>();
        post.AmbientOcclusion = true;
        post.Bloom = true;
        post.BloomIntensity = 0.12f;
        post.BloomThreshold = 0.8f;
        post.VignetteIntensity = 0.35f;
        post.AutoExposure = false;
        post.FXAA = true;
        post.Fog = true;
        post.FogColor = Vector3( 0.01f, 0.01f, 0.015f );
        post.FogDensity = 0.012f;
        post.FogHeight = 0.f;
        post.FogHeightFalloff = 0.02f;
        post.FogStartDistance = 2.f;
        post.FogMaxOpacity = 0.9f;
        // The concert look's toning, faded in by its grade (off for every other look).
        post.Lut = Path( kConcertLut );
        post.LutContribution = 0.f;
    }
    // The screens' feeds: render textures at 30 frames a second, plenty for screens across a
    // hazy room, without the sun's shadows, ambient occlusion or volumetric haze.
    const auto makeFeed = [&inWorld]( const char* inName, const char* inTexture ) {
        EntityHandle entity = inWorld.CreateEntity( inName );
        if( !entity ) return entity;
        entity->AddComponent<Transform>( inName );
        Camera& camera = entity->AddComponent<Camera>();
        camera.TargetTexture = Path( inTexture );
        camera.UpdateInterval = 2;
        camera.Near = 0.1f;
        camera.Far = 120.f;
        camera.ClearColor = Vector3( 0.f, 0.f, 0.f );
        camera.SunShadows = false;
        camera.AmbientOcclusion = false;
        camera.VolumetricFog = false;
        PostProcess& post = entity->AddComponent<PostProcess>();
        post.AmbientOcclusion = false;
        post.Bloom = true;
        post.BloomIntensity = 0.1f;
        post.VignetteIntensity = 0.3f;
        post.Fog = false;
        post.Saturation = 1.1f;
        post.Contrast = 1.1f;
        post.Lut = Path( kConcertLut );
        post.LutContribution = 0.f;
        return entity;
    };
    m_feed = makeFeed( "Venue Feed Camera", kFeedTexture );
    m_program = makeFeed( "Venue Program Camera", kProgramTexture );
}


Director::Plan Director::PlanFor( const std::string& inName, int inIndex ) const
{
    // Rock Band 3's shot names: "coop_<who>_<framing>" and "directed_<who>[_<style>]"; RB2's note
    // cuts arrive as "auto <constraints>".
    Plan plan;
    plan.Variant = static_cast<int>( VenueTiming::Noise( static_cast<uint32_t>( inIndex ), 41u ) * 16.f );
    if( inName == "debug_wall" )
    {
        // Diagnostics (--venue-shot debug_wall): straight at the LED wall from the front of the stage.
        plan.Frame = Framing::Wall;
        return plan;
    }
    if( inName == "guitar_neck" || inName == "bass_neck" || StartsWith( inName, "solo_neck" ) )
    {
        // The neck camera (AddNeckShots; --venue-shot guitar_neck to frame it).
        plan.Subjects = { inName == "bass_neck" ? VenueData::Bass : VenueData::Guitar };
        plan.Frame = Framing::Neck;
        return plan;
    }
    if( StartsWith( inName, "cam_" ) )
    {
        // The crew's own shots by name (--venue-shot cam_crane): "cam_<kind>[_<members>][_<variant>]",
        // e.g. cam_foh_v, cam_hero_g_1, cam_reverse_d.
        const std::vector<std::string> parts = Split( inName.substr( 4 ), '_' );
        const std::string kind = parts.empty() ? std::string() : parts[0];
        for( size_t i = 1; i < parts.size(); ++i )
        {
            if( std::isdigit( static_cast<unsigned char>( parts[i][0] ) ) )
            {
                plan.Variant = std::atoi( parts[i].c_str() );
                continue;
            }
            for( char letter : parts[i] )
            {
                const int member = MemberFromLetter( letter );
                if( member >= 0 ) plan.Subjects.push_back( member );
            }
        }
        if( kind == "crane" ) plan.Frame = Framing::Crane;
        else if( kind == "dolly" ) plan.Frame = Framing::Dolly;
        else if( kind == "drone" ) plan.Frame = Framing::Drone;
        else if( kind == "orbit" ) plan.Frame = Framing::Orbit;
        else if( kind == "foh" ) plan.Frame = Framing::LongLens;
        else if( kind == "crowd" ) { plan.Frame = Framing::CrowdPov; plan.Handheld = true; }
        else if( kind == "side" ) plan.Frame = Framing::Profile;
        else if( kind == "drumtop" ) { plan.Frame = Framing::DrumTop; plan.Subjects = { VenueData::Drums }; }
        else if( kind == "drumlow" ) { plan.Frame = Framing::DrumLow; plan.Subjects = { VenueData::Drums }; }
        else if( kind == "reverse" ) plan.Frame = Framing::Behind;
        else if( kind == "hero" ) { plan.Frame = Framing::LowHero; if( plan.Subjects.empty() ) plan.Subjects = { VenueData::Vocals }; }
        else if( kind == "push" ) plan.Frame = Framing::Push;
        else if( kind == "run" ) { plan.Frame = Framing::PitRun; plan.Handheld = true; }
        return plan;
    }
    if( StartsWith( inName, "auto" ) )
    {
        return PlanAuto( inName.substr( 4 ), inIndex, 0.f );
    }
    if( StartsWith( inName, "coop_" ) )
    {
        const std::vector<std::string> parts = Split( inName.substr( 5 ), '_' );
        if( parts.empty() ) return plan;
        const std::string& who = parts[0];
        if( who == "front" ) plan.Subjects = { VenueData::Guitar, VenueData::Vocals, VenueData::Bass };
        else if( who != "all" )
        {
            for( char letter : who )
            {
                const int member = MemberFromLetter( letter );
                if( member >= 0 ) plan.Subjects.push_back( member );
            }
        }
        const std::string framing = parts.size() > 1 ? parts[1] : "near";
        const std::string detail = parts.size() > 2 ? parts[2] : "";
        if( framing == "behind" ) plan.Frame = Framing::Behind;
        else if( framing == "far" ) plan.Frame = Framing::Far;
        else if( framing == "closeup" ) plan.Frame = detail == "hand" ? Framing::CloseHand : Framing::CloseHead;
        else plan.Frame = Framing::Near;
        Vary( plan );
        return plan;
    }
    if( StartsWith( inName, "directed_" ) )
    {
        const std::string rest = inName.substr( 9 );
        const std::vector<std::string> parts = Split( rest, '_' );
        if( parts.empty() ) return plan;
        const std::string& who = parts[0];
        const std::string style = parts.size() > 1 ? parts[1] : "";
        plan.Handheld = style == "cam" || style == "lt";
        plan.Static = style == "np";
        if( who == "all" )
        {
            plan.Frame = style == "lt" ? Framing::Overhead : style == "yeah" ? Framing::Near : Framing::Far;
        }
        else if( who == "bre" || who == "brej" )
        {
            // The big rock ending: the whole band from up high, swinging round.
            plan.Frame = Framing::Overhead;
            plan.Handheld = true;
        }
        else if( who == "crowd" || who == "stagedive" || who == "crowdsurf" )
        {
            plan.Frame = Framing::Crowd;
            plan.Handheld = who != "crowd";
            if( style == "g" ) plan.Subjects = { VenueData::Guitar };
            else if( style == "b" ) plan.Subjects = { VenueData::Bass };
        }
        else if( who == "duo" )
        {
            const std::string pair = style;
            if( pair == "drums" ) plan.Subjects = { VenueData::Drums, VenueData::Vocals };
            else if( pair == "bass" ) plan.Subjects = { VenueData::Bass, VenueData::Vocals };
            else if( pair == "guitar" ) plan.Subjects = { VenueData::Guitar, VenueData::Vocals };
            else if( pair == "gb" ) plan.Subjects = { VenueData::Guitar, VenueData::Bass };
            else
            {
                for( char letter : pair )
                {
                    const int member = MemberFromLetter( letter );
                    if( member >= 0 ) plan.Subjects.push_back( member );
                }
            }
            plan.Frame = Framing::Near;
        }
        else
        {
            const int member = MemberFromWord( who );
            if( member >= 0 ) plan.Subjects = { member };
            if( style == "cls" ) plan.Frame = Framing::CloseHand;
            else if( style == "kd" ) plan.Frame = Framing::Kick;
            else if( style == "np" || style == "pnt" ) plan.Frame = Framing::CloseHead;
            else if( style == "lt" ) plan.Frame = Framing::Behind;
            else plan.Frame = Framing::Near;
        }
        // The chart's own handheld and locked-off shots are shot as asked.
        if( style.empty() || who == "crowd" ) Vary( plan );
        return plan;
    }
    // Unknown names: a wide shot.
    return plan;
}


void Director::DropAbsent( Plan& ioPlan ) const
{
    // Only the plan's absences: a member the chart has no part for (keys) still has a spot.
    const bool named = !ioPlan.Subjects.empty();
    ioPlan.Subjects.erase( std::remove_if( ioPlan.Subjects.begin(), ioPlan.Subjects.end(), [this]( int inMember ) { return inMember >= 0 && !m_plan.HasMember( inMember ); } ), ioPlan.Subjects.end() );
    const bool kit = ioPlan.Frame == Framing::Kick || ioPlan.Frame == Framing::DrumTop || ioPlan.Frame == Framing::DrumLow;
    // A close-up of nobody in particular is of the singer: with no singer it's a wide.
    const bool lonelyClose = ioPlan.Frame == Framing::CloseHead && ioPlan.Subjects.empty() && !m_plan.HasMember( VenueData::Vocals );
    if( ( named && ioPlan.Subjects.empty() ) || ( kit && !m_plan.HasMember( VenueData::Drums ) ) || lonelyClose )
    {
        ioPlan.Subjects.clear();
        ioPlan.Frame = Framing::Far;
    }
}


Director::Plan Director::PlanAuto( const std::string& inConstraints, int inIndex, float inTime ) const
{
    // An RB2 cut: a shot that suits its constraints ("only_close", "only_far", "no_close",
    // "no_behind", "focus_x"), picked repeatably from the cut's index.
    (void)inTime;
    Plan plan;
    const auto has = [&inConstraints]( const char* inWord ) { return inConstraints.find( inWord ) != std::string::npos; };
    const float roll = VenueTiming::Noise( static_cast<uint32_t>( inIndex ), 7u );
    const float roll2 = VenueTiming::Noise( static_cast<uint32_t>( inIndex ), 8u );
    plan.Variant = static_cast<int>( VenueTiming::Noise( static_cast<uint32_t>( inIndex ), 9u ) * 16.f );
    // Every member the cut focuses on is in it (two make a duo shot).
    for( const char* member : { "focus_bass", "focus_drums", "focus_guitar", "focus_vocals" } )
    {
        if( has( member ) )
        {
            plan.Subjects.push_back( MemberFromWord( std::string( member ).substr( 6 ) ) );
        }
    }
    if( plan.Subjects.empty() && !has( "only_far" ) && roll2 < 0.6f )
    {
        // Single out someone: busier members more often.
        const int members[] = { VenueData::Vocals, VenueData::Guitar, VenueData::Drums, VenueData::Bass, VenueData::Vocals, VenueData::Guitar };
        plan.Subjects = { members[static_cast<int>( roll2 / 0.6f * 6.f ) % 6] };
    }
    if( has( "only_far" ) )
    {
        plan.Frame = Framing::Far;
        plan.Subjects.clear();
    }
    else if( has( "only_close" ) )
    {
        plan.Frame = roll < 0.5f ? Framing::CloseHead : Framing::CloseHand;
    }
    else
    {
        const bool close = !has( "no_close" );
        const bool behind = !has( "no_behind" );
        if( roll < 0.35f ) plan.Frame = Framing::Near;
        else if( roll < 0.55f && close ) plan.Frame = Framing::CloseHead;
        else if( roll < 0.7f && close ) plan.Frame = Framing::CloseHand;
        else if( roll < 0.8f && behind ) plan.Frame = Framing::Behind;
        else plan.Frame = plan.Subjects.empty() ? Framing::Far : Framing::Near;
    }
    plan.Handheld = VenueTiming::Noise( static_cast<uint32_t>( inIndex ), 10u ) < 0.25f;
    // (An "only far" cut stays a wide of one kind or another; a close one stays close.)
    Vary( plan );
    return plan;
}


void Director::Vary( Plan& ioPlan )
{
    // The chart asks for a kind of shot; the crew has several ways to shoot each. Bits 2-3 of
    // the variant pick one, so a song's third wide shot isn't its first again.
    const int treatment = ( ioPlan.Variant >> 2 ) & 3;
    const bool alternate = ( ioPlan.Variant & 2 ) != 0;
    // A close-up is of one player: asked to focus on two, it takes one of them. Framing the
    // point between their heads shows whatever stands between them (an amp).
    if( ( ioPlan.Frame == Framing::CloseHead || ioPlan.Frame == Framing::CloseHand ) && ioPlan.Subjects.size() >= 2 )
    {
        const int kept = ioPlan.Subjects[static_cast<size_t>( ioPlan.Variant ) % ioPlan.Subjects.size()];
        ioPlan.Subjects = { kept };
    }
    const int subject = ioPlan.Subjects.size() == 1 ? ioPlan.Subjects[0] : -1;
    switch( ioPlan.Frame )
    {
    case Framing::Far:
        if( ioPlan.Subjects.empty() )
        {
            if( treatment == 1 ) ioPlan.Frame = Framing::Crane;
            else if( treatment == 2 ) ioPlan.Frame = alternate ? Framing::Orbit : Framing::Drone;
            else if( treatment == 3 ) ioPlan.Frame = Framing::LongLens;
        }
        else if( treatment == 2 )
        {
            ioPlan.Frame = Framing::LongLens;
        }
        break;
    case Framing::Near:
        if( ioPlan.Subjects.empty() )
        {
            if( treatment == 1 ) ioPlan.Frame = Framing::Dolly;
            else if( treatment == 2 ) ioPlan.Frame = Framing::Profile;
        }
        else if( treatment == 3 && subject == VenueData::Drums )
        {
            ioPlan.Frame = Framing::DrumLow;
        }
        else if( treatment == 3 && ( subject == VenueData::Guitar || subject == VenueData::Bass || subject == VenueData::Vocals ) )
        {
            ioPlan.Frame = Framing::LowHero;
        }
        break;
    case Framing::CloseHand:
        if( subject == VenueData::Drums && treatment >= 2 ) ioPlan.Frame = Framing::DrumTop;
        break;
    case Framing::Crowd:
        // (Handheld crowd shots are the stage dive and the crowd surfer: they stay as they are.)
        if( ioPlan.Subjects.empty() && !ioPlan.Handheld && treatment >= 2 )
        {
            ioPlan.Frame = Framing::CrowdPov;
            ioPlan.Handheld = true;
        }
        else if( ioPlan.Subjects.empty() && !ioPlan.Handheld && treatment == 1 )
        {
            ioPlan.Frame = Framing::PitRun;
            ioPlan.Handheld = true;
        }
        break;
    case Framing::Overhead:
        if( !ioPlan.Handheld && ( treatment & 1 ) != 0 ) ioPlan.Frame = Framing::Orbit;
        break;
    default:
        break;
    }
}


const char* Director::FramingName( Framing inFraming )
{
    switch( inFraming )
    {
    case Framing::Far: return "far";
    case Framing::Near: return "near";
    case Framing::Behind: return "behind";
    case Framing::CloseHead: return "head";
    case Framing::CloseHand: return "hand";
    case Framing::Kick: return "kick";
    case Framing::Crowd: return "crowd";
    case Framing::Overhead: return "overhead";
    case Framing::Wall: return "wall";
    case Framing::Neck: return "neck";
    case Framing::Surfer: return "surfer";
    case Framing::Crane: return "crane";
    case Framing::Dolly: return "dolly";
    case Framing::Drone: return "drone";
    case Framing::Orbit: return "orbit";
    case Framing::LongLens: return "foh";
    case Framing::CrowdPov: return "crowdpov";
    case Framing::Profile: return "side";
    case Framing::DrumTop: return "drumtop";
    case Framing::DrumLow: return "drumlow";
    case Framing::LowHero: return "hero";
    case Framing::Push: return "push";
    case Framing::PitRun: return "run";
    case Framing::Spot: return "spot";
    case Framing::Arrival: return "arrival";
    case Framing::Story: return "story";
    }
    return "";
}


void Director::BuildFallbackCuts( const VenueData& inVenue, float inSongLength )
{
    // No camera cuts in the chart: cut it like a live director would. Always on a downbeat (a
    // half measure in a flurry), paced by the section: a chorus or solo every measure, a verse
    // every two, an intro or a quiet stretch every four with slow moves. A chorus opens on a
    // wide or the crane, other sections on whoever carries them; a long section ends on a wide.
    // In between it's the busiest member (the drummer on a fill, the singer on a line), never
    // the same subject and framing twice running. All from seeded noise: a song cuts the same
    // every time.
    struct Beat
    {
        float Time = 0.f;
        bool Downbeat = false;
    };
    std::vector<Beat> beats;
    if( m_beats.size() >= 8 )
    {
        for( const BeatData& beat : m_beats ) beats.push_back( { beat.m_time, beat.m_measure } );
    }
    else
    {
        const float step = 60.f / std::max( 30.f, m_bpm );
        int count = 0;
        for( float time = 0.f; time < std::max( inSongLength, 30.f ); time += step ) beats.push_back( { time, count++ % 4 == 0 } );
    }
    if( beats.empty() )
    {
        return;
    }
    // Each section, lower case, with the beat it starts on.
    struct Section
    {
        std::string Name;
        size_t Beat = 0;
    };
    std::vector<Section> sections;
    for( const TimedCueData& cue : inVenue.m_sections )
    {
        Section section;
        section.Name = cue.m_name;
        std::transform( section.Name.begin(), section.Name.end(), section.Name.begin(), []( unsigned char c ) { return static_cast<char>( std::tolower( c ) ); } );
        while( section.Beat + 1 < beats.size() && beats[section.Beat].Time < cue.m_time - 0.05f ) ++section.Beat;
        sections.push_back( section );
    }
    // 0 calm, 1 steady, 2 hot.
    const auto energyOf = []( const std::string& inName ) {
        const auto has = [&inName]( const char* inWord ) { return VenueTiming::Contains( inName, inWord ); };
        if( has( "chorus" ) || has( "solo" ) || has( "outro" ) || has( "ending" ) || has( "bre" ) ) return 2;
        if( has( "intro" ) || has( "bridge" ) || has( "break" ) || has( "quiet" ) || has( "spacey" ) || has( "mellow" ) || has( "interlude" ) ) return 0;
        return 1;
    };

    size_t next = 0;           // the next section to start
    int cutsInSection = 0;
    int flurry = 0;            // half-measure cuts left to run
    int lastSubject = -2;
    Framing lastFrame = Framing::Wall;
    uint32_t count = 0;
    size_t beat = 0;
    while( beat < beats.size() )
    {
        const float time = beats[beat].Time;
        bool newSection = count == 0;
        while( next < sections.size() && sections[next].Beat <= beat )
        {
            ++next;
            newSection = true;
            cutsInSection = 0;
            flurry = 0;
        }
        const std::string sectionName = next > 0 ? sections[next - 1].Name : std::string();
        const int energy = sections.empty() ? 1 : energyOf( sectionName );
        const bool chorus = VenueTiming::Contains( sectionName, "chorus" );
        const auto noise = [count]( uint32_t inSalt ) { return VenueTiming::Noise( count, inSalt ); };

        // How long this cut holds, in beats: to a downbeat, and never past the section's end.
        int hold = energy == 2 ? 4 : energy == 1 ? 8 : 16;
        if( flurry > 0 )
        {
            hold = 2;
            --flurry;
        }
        else if( energy == 2 && !newSection && noise( 54u ) < 0.18f )
        {
            // A flurry: three quick cuts on the half measure.
            flurry = 2;
            hold = 2;
        }
        size_t end = std::min( beat + static_cast<size_t>( hold ), beats.size() );
        if( hold >= 4 )
        {
            // Land on a downbeat (the tempo map's own, whatever the time signature).
            size_t snapped = end;
            while( snapped < beats.size() && snapped < end + 3 && !beats[snapped].Downbeat ) ++snapped;
            if( snapped < beats.size() && beats[snapped].Downbeat ) end = snapped;
        }
        const size_t sectionEnd = next < sections.size() ? sections[next].Beat : beats.size();
        const bool lastInSection = end >= sectionEnd;
        if( lastInSection ) end = sectionEnd;
        if( end <= beat ) end = beat + 1;
        // (A section that opens on the room doesn't need the one before it to end there too.)
        const bool nextOpensWide = next < sections.size() && ( VenueTiming::Contains( sections[next].Name, "chorus" ) || energyOf( sections[next].Name ) == 0 );
        const float length = ( end < beats.size() ? beats[end].Time : beats.back().Time + 2.f ) - time;

        Cut cut;
        cut.Time = time;
        Plan& plan = cut.Shot;
        plan.Variant = static_cast<int>( noise( 51u ) * 16.f );
        plan.Handheld = noise( 52u ) < ( energy == 2 ? 0.4f : energy == 1 ? 0.2f : 0.05f );
        const float roll = noise( 53u );
        const float roll2 = noise( 55u );
        const Framing wides[] = { Framing::Far, Framing::Crane, Framing::Drone, Framing::LongLens, Framing::Orbit, Framing::Overhead };
        const auto wide = [&]( float inRoll ) {
            Framing frame = wides[static_cast<int>( inRoll * 6.f ) % 6];
            if( frame == lastFrame ) frame = wides[( static_cast<int>( inRoll * 6.f ) + 1 ) % 6];
            return frame;
        };
        if( newSection && ( chorus || count == 0 || energy == 0 ) )
        {
            // Open on the room: the crane or a wide for a chorus, the long lens or the drone
            // coming in for a quiet start.
            plan.Frame = chorus ? ( roll < 0.5f ? Framing::Crane : wide( roll2 ) ) : ( roll < 0.4f ? Framing::LongLens : roll < 0.7f ? Framing::Drone : wide( roll2 ) );
            plan.Handheld = false;
        }
        else if( lastInSection && !nextOpensWide && cutsInSection >= 3 && flurry == 0 && lastSubject != -1 )
        {
            plan.Frame = wide( roll );
            plan.Handheld = false;
        }
        else if( flurry == 0 && hold > 2 && roll2 < ( energy == 2 ? 0.22f : 0.12f ) && lastSubject != -1 )
        {
            // The band together, or the room they're playing to.
            const Framing groups[] = { Framing::Dolly, Framing::Profile, Framing::Behind, Framing::Near, energy == 2 ? Framing::Crowd : Framing::LongLens, energy == 2 ? Framing::CrowdPov : Framing::Orbit };
            plan.Frame = groups[static_cast<int>( roll * 6.f ) % 6];
            if( plan.Frame == Framing::CrowdPov ) plan.Handheld = true;
            // The room at full tilt: half the time it's the operator running the pit.
            if( plan.Frame == Framing::Crowd && ( plan.Variant & 4 ) != 0 )
            {
                plan.Frame = Framing::PitRun;
                plan.Handheld = true;
            }
        }
        else
        {
            // Whoever's carrying this stretch: the drummer through a fill, the singer on a line,
            // the guitarist through a solo. Not whoever just had the shot, unless nobody else is
            // playing.
            const double middle = time + std::min( length, 4.f ) * 0.5;
            int subject = VenueData::Vocals;
            float best = -1e9f;
            if( m_band )
            {
                for( int member = 0; member < VenueData::MemberCount; ++member )
                {
                    if( !m_band->HasMember( member ) ) continue;
                    float score = m_band->Activity( member, middle ) + noise( 60u + static_cast<uint32_t>( member ) ) * 0.8f;
                    if( member == VenueData::Guitar && VenueTiming::Contains( sectionName, "solo" ) ) score += 2.f;
                    if( member == VenueData::Vocals && m_band->Activity( member, middle ) > 0.5f ) score += 0.5f;
                    // A fill: the drums flat out.
                    if( member == VenueData::Drums && m_band->Activity( member, middle ) > 0.85f ) score += 0.7f;
                    if( member == lastSubject ) score -= 0.9f;
                    if( score > best )
                    {
                        best = score;
                        subject = member;
                    }
                }
            }
            plan.Subjects = { subject };
            if( subject == VenueData::Drums )
            {
                const Framing frames[] = { Framing::Near, Framing::DrumLow, Framing::CloseHand, Framing::DrumTop, Framing::Kick, Framing::Behind, Framing::CloseHead, Framing::LongLens };
                plan.Frame = frames[static_cast<int>( roll * 8.f ) % 8];
            }
            else
            {
                const bool front = subject != VenueData::Keys;
                plan.Frame = roll < 0.32f ? Framing::Near : roll < 0.48f ? Framing::CloseHead : roll < 0.6f ? Framing::CloseHand
                    : roll < 0.72f ? ( front ? Framing::LowHero : Framing::Near ) : roll < 0.8f ? Framing::Behind : roll < 0.9f ? Framing::LongLens : Framing::Far;
                // The singer's hands aren't the story.
                if( subject == VenueData::Vocals && plan.Frame == Framing::CloseHand ) plan.Frame = Framing::CloseHead;
            }
            if( subject == lastSubject && plan.Frame == lastFrame )
            {
                plan.Frame = plan.Frame == Framing::Near ? Framing::CloseHead : Framing::Near;
            }
            // A quiet stretch holds still or moves slowly: no shoulder cameras in the pit.
            if( energy == 0 ) plan.Handheld = false;
        }
        lastSubject = plan.Subjects.size() == 1 ? plan.Subjects[0] : -1;
        lastFrame = plan.Frame;
        cut.Name = std::string( "fallback_" ) + FramingName( plan.Frame );
        m_cuts.push_back( cut );
        ++count;
        ++cutsInSection;
        beat = end;
    }
}


void Director::FillAutoCuts( const VenueData& inVenue, float inSongLength )
{
    // A chart cut is one shot, held until the next cut. An "auto" cut held a long while (one
    // dropped in the editor with nothing after it) hands the stretch to the director instead:
    // its own shot first, then the cuts a chart without cameras would have got there. A
    // constrained one ("auto only_close") keeps its constraints on every cut in the stretch.
    const float kLongHold = 10.f;
    const auto handsOver = [&]( const std::vector<Cut>& inCuts, size_t inCut ) {
        const float hold = inCut + 1 < inCuts.size() ? inCuts[inCut + 1].Time - inCuts[inCut].Time
            : inSongLength > 0.f ? inSongLength - inCuts[inCut].Time : kLongHold * 2.f;
        return StartsWith( inCuts[inCut].Name, "auto" ) && hold > kLongHold;
    };
    bool any = false;
    for( size_t i = 0; i < m_cuts.size() && !any; ++i )
    {
        any = handsOver( m_cuts, i );
    }
    if( !any )
    {
        return;
    }
    std::vector<Cut> chart;
    chart.swap( m_cuts );
    BuildFallbackCuts( inVenue, inSongLength );
    std::vector<Cut> crew;
    crew.swap( m_cuts );
    for( size_t i = 0; i < chart.size(); ++i )
    {
        m_cuts.push_back( chart[i] );
        if( !handsOver( chart, i ) )
        {
            continue;
        }
        const float from = chart[i].Time + 2.f;
        const float to = i + 1 < chart.size() ? chart[i + 1].Time - 1.f : std::numeric_limits<float>::max();
        const bool constrained = chart[i].Name.find_first_not_of( ' ', 4 ) != std::string::npos;
        for( size_t j = 0; j < crew.size(); ++j )
        {
            if( crew[j].Time < from || crew[j].Time > to )
            {
                continue;
            }
            Cut fill = crew[j];
            if( constrained )
            {
                fill.Name = chart[i].Name;
                fill.Shot = PlanAuto( chart[i].Name.substr( 4 ), 1000 + static_cast<int>( j ), fill.Time );
            }
            m_cuts.push_back( fill );
        }
    }
}


void Director::AddNeckShots( const VenueData& inVenue )
{
    // Through a guitar solo, every other shot of the guitarist alone is the camera on their
    // headstock, looking down the frets. A solo (PART GUITAR note 103) the cuts never single the
    // guitarist out in gets one anyway, for its middle third.
    if( !m_band || !m_band->HasMember( VenueData::Guitar ) )
    {
        return;
    }
    const auto soloAt = [&]( float inTime ) -> int {
        for( size_t i = 0; i < inVenue.m_guitarSolos.size(); ++i )
        {
            if( inTime >= inVenue.m_guitarSolos[i].m_start - 0.05f && inTime < inVenue.m_guitarSolos[i].m_end ) return static_cast<int>( i );
        }
        // Charts without solo markers: the guitarist's play_solo state (or a "solo" section).
        if( inVenue.m_guitarSolos.empty() && m_band->StateOf( VenueData::Guitar, inTime ) == "play_solo" ) return 0;
        return -1;
    };
    std::vector<bool> soloHasNeck( std::max<size_t>( 1, inVenue.m_guitarSolos.size() ), false );
    int lastSolo = -1;
    int count = 0;
    for( Cut& cut : m_cuts )
    {
        const int solo = soloAt( cut.Time );
        if( solo < 0 )
        {
            lastSolo = -1;
            continue;
        }
        if( solo != lastSolo )
        {
            lastSolo = solo;
            count = 0;
        }
        // Only close-ish shots of the guitarist alone; the chart's wide and no-close cuts stay so.
        const bool wide = cut.Shot.Frame == Framing::Behind || cut.Shot.Frame == Framing::Far || VenueTiming::Contains( cut.Name, "no_close" ) || VenueTiming::Contains( cut.Name, "only_far" );
        if( cut.Shot.Subjects.size() != 1 || cut.Shot.Subjects[0] != VenueData::Guitar || wide )
        {
            continue;
        }
        if( count++ % 2 == 1 )
        {
            cut.Shot.Frame = Framing::Neck;
            cut.Shot.Handheld = false;
            cut.Name += " neck";
            soloHasNeck[solo] = true;
        }
    }
    for( size_t i = 0; i < inVenue.m_guitarSolos.size(); ++i )
    {
        const VenueData::SpanData& solo = inVenue.m_guitarSolos[i];
        const float length = solo.m_end - solo.m_start;
        if( soloHasNeck[i] || length < 6.f )
        {
            continue;
        }
        // In for the middle third (five seconds at most), then back to the shot it interrupted.
        const float in = solo.m_start + length / 3.f;
        const float out = in + std::min( length / 3.f, 5.f );
        auto at = std::upper_bound( m_cuts.begin(), m_cuts.end(), in, []( float t, const Cut& c ) { return t < c.Time; } );
        Cut resume;
        const bool interrupts = at != m_cuts.begin() && ( at == m_cuts.end() || at->Time > out );
        if( interrupts )
        {
            resume = *( at - 1 );
            resume.Time = out;
        }
        Cut neck;
        neck.Time = in;
        neck.Name = "solo_neck";
        neck.Shot.Subjects = { VenueData::Guitar };
        neck.Shot.Frame = Framing::Neck;
        at = m_cuts.insert( at, neck );
        if( interrupts )
        {
            m_cuts.insert( at + 1, resume );
        }
    }
}


const VenuePlan::CameraSpot* Director::SpotFor( VenuePlan::CameraSpot::Kind inKind, int inPick ) const
{
    std::vector<const VenuePlan::CameraSpot*> spots;
    for( const VenuePlan::CameraSpot& spot : m_plan.Cameras )
    {
        if( spot.Shot == inKind ) spots.push_back( &spot );
    }
    return spots.empty() ? nullptr : spots[static_cast<size_t>( std::max( inPick, 0 ) ) % spots.size()];
}


Vector3 Director::SpotTarget( const VenuePlan::CameraSpot& inSpot, const Vector3* inSubject ) const
{
    // Along the spot's own aim, as far off as the subject (or the band's middle) is.
    const Vector3 toward = ( inSubject ? *inSubject : m_plan.MemberCentre() + Vector3( 0.f, 1.3f, 0.f ) ) - inSpot.Eye;
    const float reach = std::max( toward.Dot( inSpot.Forward ), 2.f );
    return inSpot.Eye + inSpot.Forward * reach;
}


void Director::AddSpotCuts()
{
    // The venue's own close and custom positions are extra cuts: about a quarter of the cuts (not
    // the guitar's neck camera, the surfer's, the wall or a run in) go to one, the spots taking
    // turns. A cut of someone only goes to a spot aimed at them; a cut of the band or the room
    // to any, on whoever its aim lands nearest.
    std::vector<int> extras;
    std::vector<int> aimedAt;
    for( size_t i = 0; i < m_plan.Cameras.size(); ++i )
    {
        const VenuePlan::CameraSpot& spot = m_plan.Cameras[i];
        if( spot.Shot != VenuePlan::CameraSpot::Kind::Close && spot.Shot != VenuePlan::CameraSpot::Kind::Custom ) continue;
        if( spot.Shot == VenuePlan::CameraSpot::Kind::Custom && ( StartsWith( spot.Tag, "peak/" ) || StartsWith( spot.Tag, "story/" ) ) ) continue;
        int nearest = -1;
        float best = 0.35f;
        for( int member = 0; member < VenueData::MemberCount; ++member )
        {
            if( !m_plan.HasMember( member ) ) continue;
            const Vector3 toward = m_plan.Members[member].Feet + Vector3( 0.f, 1.3f, 0.f ) - spot.Eye;
            const float along = toward.Dot( spot.Forward );
            if( along <= 0.5f ) continue;
            const float off = ( toward - spot.Forward * along ).Length() / along;
            if( off < best )
            {
                best = off;
                nearest = member;
            }
        }
        extras.push_back( static_cast<int>( i ) );
        aimedAt.push_back( nearest );
    }
    if( extras.empty() )
    {
        return;
    }
    size_t turn = 0;
    for( size_t i = 0; i < m_cuts.size(); ++i )
    {
        Plan& shot = m_cuts[i].Shot;
        if( shot.Frame == Framing::Neck || shot.Frame == Framing::Surfer || shot.Frame == Framing::Wall || shot.Frame == Framing::Push
            || VenueTiming::Noise( static_cast<uint32_t>( i ), 131u ) >= 0.25f )
        {
            continue;
        }
        for( size_t tried = 0; tried < extras.size(); ++tried )
        {
            const size_t pick = ( turn + tried ) % extras.size();
            const int member = aimedAt[pick];
            const bool fits = shot.Subjects.empty() || std::find( shot.Subjects.begin(), shot.Subjects.end(), member ) != shot.Subjects.end();
            if( !fits ) continue;
            shot.Frame = Framing::Spot;
            shot.Variant = extras[pick];
            shot.Handheld = false;
            shot.Static = false;
            shot.Subjects.clear();
            if( member >= 0 ) shot.Subjects.push_back( member );
            turn = pick + 1;
            break;
        }
    }
}


Vector3 Director::SubjectPoint( const Plan& inPlan, bool inHead ) const
{
    if( inPlan.Subjects.empty() || !m_band )
    {
        return OnStage( Vector3( 0.f, 2.7f, 4.2f ) );
    }
    Vector3 sum( 0.f, 0.f, 0.f );
    int count = 0;
    for( int member : inPlan.Subjects )
    {
        if( member < 0 ) continue;
        sum = sum + ( inHead ? m_band->HeadOf( member ) : m_band->ChestOf( member ) );
        ++count;
    }
    return count > 0 ? sum * ( 1.f / static_cast<float>( count ) ) : OnStage( Vector3( 0.f, 2.7f, 4.2f ) );
}


void Director::Contain( Vector3& ioEye, bool inAmongCrowd ) const
{
    // Low cameras stay out of the audience: in the photo pit between the barricade and the stage,
    // or up over their heads. The limit eases back as the camera rises (free by about 4.6 m), so
    // a jib booming up out of the pit moves off over the crowd without a jump.
    if( !inAmongCrowd )
    {
        const float over = std::max( 0.f, ioEye.y - 3.f ) / 1.6f;
        const float limit = m_plan.Stage.BarricadeZ + 0.3f - over * over * 40.f;
        ioEye.z = std::max( ioEye.z, limit );
    }
    // And all stay inside the room: in front of the back wall, under the rig, between the walls.
    ioEye.z = std::max( ioEye.z, m_room.Back + 1.5f );
    if( m_room.Ceiling < 900.f )
    {
        ioEye.y = std::min( ioEye.y, m_room.Ceiling - 2.f );
    }
    if( ioEye.z < 0.f )
    {
        ioEye.x = std::clamp( ioEye.x, -( m_room.HalfWidth - 1.f ), m_room.HalfWidth - 1.f );
    }
}


void Director::Frame( const Plan& inPlan, float inHeld, Vector3& outEye, Vector3& outTarget, float& outFov, Vector3* outUp ) const
{
    // A shot in venue space: where the camera sits and looks, then how it moves while held.
    const float side = ( inPlan.Variant % 2 == 0 ) ? -1.f : 1.f;
    const float alt = ( inPlan.Variant & 2 ) != 0 ? 1.f : 0.f;
    const int subject = inPlan.Subjects.size() == 1 ? inPlan.Subjects[0] : -1;
    const bool duo = inPlan.Subjects.size() >= 2;
    const float held = std::max( inHeld, 0.f );
    // The move's progress: most of it in the first few seconds, then it keeps creeping rather
    // than coming to rest, however long the shot is held.
    const float progress = inPlan.Static ? 0.f : std::min( 1.f - std::exp( -held / 5.f ) + held * 0.03f, 3.f );
    float drift = 0.f;    // degrees of orbit over the shot
    float dolly = 0.f;    // metres toward the target over the shot
    bool amongCrowd = false;
    // A camera spot of the venue's own: where its author put it, not kept to the room.
    bool authored = false;
    const auto pick = [this, &inPlan]( VenuePlan::CameraSpot::Kind inKind ) { return SpotFor( inKind, inPlan.Variant ); };
    if( outUp ) *outUp = Vector3::Up;
    Vector3 headstock;
    Vector3 body;
    Vector3 face;
    Vector3 edge;
    if( inPlan.Frame == Framing::Neck && m_band && m_band->NeckOf( subject >= 0 ? subject : VenueData::Guitar, headstock, body, face, edge ) )
    {
        // Mounted out past the headstock and up off the fretboard, looking down the length of the
        // neck at an angle to the body, the player beyond it. Rolled with the guitar, no drift, no
        // easing: it's bolted on, and the guitar's float is what keeps it smooth.
        face = face.Normalized();
        edge = edge.Normalized();
        const Vector3 along = ( body - headstock ).Normalized();
        outEye = headstock - along * 0.14f + face * 0.2f + edge * 0.02f;
        outTarget = Lerp( headstock, body, 0.55f ) + edge * 0.05f;
        outFov = 60.f;
        if( outUp ) *outUp = ( edge * 0.7f + face * 0.3f ).Normalized();
        return;
    }
    // The drummer's shots are placed for a drummer facing the crowd and turn with their spot.
    const Vector3 drums = m_plan.SpotOf( VenueData::Drums ).Feet;
    switch( inPlan.Frame )
    {
    case Framing::Arrival:
    {
        const int last = static_cast<int>( m_arrival.size() ) - 1;
        const float phase = std::clamp( held / kArrivalInterval, 0.f, static_cast<float>( last ) );
        const int i = std::min( static_cast<int>( phase ), last - 1 );
        const float u = phase - i;
        const auto& a = m_arrival[std::max( i - 1, 0 )];
        const auto& b = m_arrival[i];
        const auto& c = m_arrival[i + 1];
        const auto& d = m_arrival[std::min( i + 2, last )];
        const auto walk = [u]( const Vector3& a, const Vector3& b, const Vector3& c, const Vector3& d ) {
            const float u2 = u * u, u3 = u2 * u;
            return b * ( 2.f*u3 - 3.f*u2 + 1.f ) + ( c-a ) * ( 0.5f*(u3 - 2.f*u2 + u) )
                 + c * ( 3.f*u2 - 2.f*u3 ) + ( d-b ) * ( 0.5f*(u3-u2) );
        };
        outEye = walk( a.Eye, b.Eye, c.Eye, d.Eye );
        const Vector3 ahead = walk( a.Forward, b.Forward, c.Forward, d.Forward );
        const float step = held * ( 1.72f * 2.f * kPi );
        const float gain = std::min( phase, 1.f ) * std::min( last - phase, 1.f );
        outEye.y += gain * 0.025f * std::sin( step );
        const Vector3 walking = ahead.Length() > 0.01f ? ahead.Normalized() : b.Forward;
        outTarget = outEye + walking * 10.f;
        if( outUp ) *outUp = ( Vector3::Up + b.Forward.Cross( Vector3::Up ) * ( gain * 0.012f * std::sin( step * 0.5f ) ) ).Normalized();
        outFov = b.FieldOfView + ( c.FieldOfView - b.FieldOfView ) * VenueTiming::Smooth( u );
        const float tail = held - static_cast<float>( last ) * kArrivalInterval;
        const bool anyone = std::any_of( m_plan.Members.begin(), m_plan.Members.end(), []( const VenuePlan::Spot& s ) { return s.Present; } );
        if( tail <= 0.f || !anyone )
        {
            return;
        }
        // Stopped at the last mark: whip round onto the band, landing a little off them, and
        // crash-zoom in, overshooting, then pull back and nudge the framing onto them.
        const Vector3 centre = m_plan.MemberCentre();
        const Vector3 band = centre + Vector3( 0.f, 1.3f, 0.f );
        const float distance = std::max( ( band - outEye ).Length(), 1.f );
        const Vector3 toBand = ( band - outEye ) * ( 1.f / distance );
        const Vector3 across = toBand.Cross( Vector3::Up ).Length() > 1e-3f ? toBand.Cross( Vector3::Up ).Normalized() : Vector3( 1.f, 0.f, 0.f );
        const float whip = VenueTiming::Smooth( ( tail - kArrivalSettle ) / kArrivalWhip );
        const float zoomTime = tail - kArrivalZoomStart;
        const float reframe = VenueTiming::Smooth( ( zoomTime - kArrivalZoomPeak * 0.7f ) / 0.5f );
        const Vector3 miss = ( across * 0.35f + Vector3( 0.f, 0.25f, 0.f ) ) * ( distance * 0.035f * ( 1.f - reframe ) );
        const Vector3 aim = Lerp( walking, ( band + miss - outEye ).Normalized(), whip );
        outTarget = outEye + ( aim.Length() > 1e-3f ? aim.Normalized() : toBand ) * distance;
        // Zoomed in to the band's width plus a little room (assuming a 16:9 picture), in log space
        // so the push reads even. The zoom is a spring let go from rest: it builds up like a
        // zoom rocker, overshoots, pulls back and hunts once before it settles.
        float spread = 0.f;
        for( const VenuePlan::Spot& spot : m_plan.Members )
        {
            if( !spot.Present ) continue;
            spread = std::max( spread, Vector3( spot.Feet.x - centre.x, 0.f, spot.Feet.z - centre.z ).Length() );
        }
        const float halfWidth = spread * 0.85f + 1.f;
        const float wide = std::tan( outFov * 0.5f * kPi / 180.f );
        const float tight = std::min( wide, halfWidth / distance / ( 16.f / 9.f ) );
        const float ring = kPi / kArrivalZoomPeak;
        const float damping = ring * std::log( 1.f / kArrivalOvershoot ) / kPi;
        const float s = std::max( zoomTime, 0.f );
        const float push = 1.f - std::exp( -damping * s ) * ( std::cos( ring * s ) + damping / ring * std::sin( ring * s ) );
        outFov = 2.f * std::atan( wide * std::pow( tight / wide, push ) ) * 180.f / kPi;
        return;
    }
    case Framing::Far:
        if( subject >= 0 )
        {
            outTarget = SubjectPoint( inPlan, false );
            outEye = outTarget + Vector3( side * 3.f, 1.4f, -9.f );
            outFov = 30.f;
        }
        else if( const VenuePlan::CameraSpot* spot = pick( VenuePlan::CameraSpot::Kind::Wide ) )
        {
            // The venue's own wide: held, creeping in.
            outEye = spot->Eye;
            outTarget = SpotTarget( *spot, nullptr );
            outFov = spot->FieldOfView;
            authored = true;
            drift = 2.f * side;
            dolly = 1.f;
            break;
        }
        else
        {
            outTarget = OnStage( Vector3( 0.f, 2.8f, 4.5f ) );
            outEye = OnStage( alt > 0.f ? Vector3( side * 9.f, 5.5f, -13.f ) : Vector3( side * 1.5f, 6.4f, -17.f ) );
            outTarget.y -= 0.6f;
            outFov = 42.f;
        }
        drift = 6.f * side;
        dolly = 1.5f;
        break;
    case Framing::Overhead:
        outTarget = OnStage( Vector3( 0.f, 2.f, 4.f ) );
        outEye = OnStage( Vector3( side * 6.f, 9.5f, -7.f ) );
        outFov = 55.f;
        drift = 14.f * side;
        break;
    case Framing::Near:
        if( subject >= 0 || duo )
        {
            outTarget = SubjectPoint( inPlan, false ) + Vector3( 0.f, 0.15f, 0.f );
            const float distance = duo ? 5.f : subject == VenueData::Drums ? 3.4f : 3.f;
            outEye = outTarget + Vector3( side * ( 1.2f + alt ), 0.25f - alt * 0.5f, -distance );
            outFov = duo ? 48.f : 42.f;
        }
        else
        {
            outTarget = OnStage( Vector3( 0.f, 2.6f, 4.f ) );
            outEye = OnStage( Vector3( side * 3.f, 2.2f - alt * 0.5f, -3.4f ) );
            outFov = 62.f;
        }
        drift = 5.f * side;
        dolly = 0.6f;
        break;
    case Framing::Behind:
        if( subject >= 0 && subject != VenueData::Drums )
        {
            // Over their shoulder at the crowd they're playing to, rising a little as it's held.
            const Vector3 chest = SubjectPoint( inPlan, false );
            outEye = chest + Vector3( side * 0.75f, 0.55f + 0.35f * std::min( progress, 1.5f ), 2.3f );
            outTarget = chest + Vector3( -side * 1.2f, -0.3f, -12.f );
            outFov = 54.f;
            dolly = 0.4f;
        }
        else if( subject == VenueData::Drums )
        {
            // From behind the throne, over the drummer's head and the kit at the whole room.
            outEye = AtDrums( drums + Vector3( side * 0.9f, 1.95f, 1.8f ) );
            outTarget = AtDrums( Vector3( -side * 1.f, 1.7f, -10.f ) );
            outFov = 62.f;
            drift = 5.f * side;
        }
        else
        {
            // Along the back of the stage, the band's backs against the lit crowd.
            const float travel = std::min( progress, 2.f );
            outEye = OnStage( Vector3( side * ( 2.6f - 1.6f * travel ), 3.6f + 0.3f * travel, 9.8f ) );
            outTarget = OnStage( Vector3( 0.f, 1.8f, -6.f ) );
            outFov = 66.f;
        }
        break;
    case Framing::CloseHead:
        // (No subject: the singer, where there is one; DropAbsent makes it a wide otherwise.)
        outTarget = subject >= 0 || duo ? SubjectPoint( inPlan, true )
            : m_band && m_band->HasMember( VenueData::Vocals ) ? m_band->HeadOf( VenueData::Vocals ) : OnStage( Vector3( 0.f, 2.9f, 1.6f ) );
        outEye = outTarget + Vector3( side * 0.7f, 0.05f - alt * 0.2f, -1.4f );
        outFov = 32.f;
        drift = 7.f * side;
        break;
    case Framing::Neck:    // no guitar to ride: a close-up of the hands instead
    case Framing::CloseHand:
        if( subject == VenueData::Drums )
        {
            outTarget = m_band ? m_band->HandsOf( subject ) : AtDrums( drums + Vector3( 0.f, 0.9f, -0.5f ) );
            outEye = AtDrums( drums + Vector3( side * 1.4f, 1.6f, -1.2f ) );
            outFov = 40.f;
        }
        else
        {
            outTarget = m_band && subject >= 0 ? m_band->HandsOf( subject ) : SubjectPoint( inPlan, false );
            outEye = outTarget + Vector3( side * 0.5f, 0.25f, -1.1f );
            outFov = 34.f;
        }
        drift = 6.f * side;
        break;
    case Framing::Kick:
        outTarget = AtDrums( drums + Vector3( 0.f, 0.45f, -0.6f ) );
        outEye = AtDrums( drums + Vector3( side * 0.4f, 0.35f, -2.2f ) );
        outFov = 46.f;
        dolly = 0.3f;
        break;
    case Framing::Wall:
        outTarget = Vector3( m_plan.ShotOffset.x, 6.9f + m_plan.ShotOffset.y, m_plan.Stage.BackWallZ );
        outEye = OnStage( Vector3( 0.f, 5.5f, -4.f ) );
        outFov = 50.f;
        break;
    case Framing::Crowd:
        outEye = subject >= 0 ? SubjectPoint( inPlan, true ) + Vector3( side * 0.6f, 0.4f, 0.8f ) : OnStage( Vector3( side * 4.f, 3.6f, 0.4f ) );
        outTarget = OnStage( Vector3( -side * 2.f, 1.4f, -12.f ) );
        outFov = 60.f;
        drift = 10.f * side;
        break;
    case Framing::Surfer:
    {
        // Up on a camera platform at the front of the pit, off to one side and looking down on
        // them so they read against the crowd rather than among its raised arms, panning with them
        // from the back of the room to the barricade: zoomed in while they're far off (about
        // four metres of crowd across the frame), widening as they come.
        outEye = Vector3( m_surferSide * 2.5f, 5.2f, m_plan.Stage.BarricadeZ + 1.2f );
        outTarget = m_surferPosition;
        const float distance = std::max( ( outTarget - outEye ).Length(), 0.5f );
        outFov = std::clamp( 2.f * std::atan( 2.f / distance ) * 180.f / kPi, 20.f, 65.f );
        break;
    }
    case Framing::Crane:
    {
        // A jib arm: from low in the pit it booms up and back over the crowd's heads, the band
        // shrinking into the whole stage (the alternate take comes down the same arc into the pit).
        float boom = std::min( progress * 0.75f, 1.2f );
        if( alt > 0.f ) boom = 1.f - std::min( boom, 1.f );
        if( const VenuePlan::CameraSpot* spot = pick( VenuePlan::CameraSpot::Kind::Crane ) )
        {
            // The venue's own crane position: the arm rises into it from lower and further in
            // (the alternate take comes down out of it).
            const float rest = 1.f - std::min( boom, 1.f );
            const Vector3 flat = Vector3( spot->Forward.x, 0.f, spot->Forward.z ).Length() > 1e-3f ? Vector3( spot->Forward.x, 0.f, spot->Forward.z ).Normalized() : Vector3( 0.f, 0.f, 1.f );
            outEye = spot->Eye + Vector3( 0.f, -2.2f * rest, 0.f ) + flat * ( 2.f * rest );
            outEye.y = std::max( outEye.y, 0.8f );
            outTarget = SpotTarget( *spot, nullptr );
            outFov = spot->FieldOfView;
            authored = true;
            break;
        }
        outEye = OnStage( Vector3( side * ( 5.f - 3.f * boom ), 2.f + 6.5f * std::sqrt( boom ), -1.2f - 9.8f * boom * boom ) );
        outTarget = OnStage( Vector3( 0.f, 2.7f - 0.4f * boom, 4.2f ) );
        outFov = 58.f - 12.f * std::min( boom, 1.f );
        break;
    }
    case Framing::Dolly:
    {
        // On a track along the pit rail, below the deck's edge: the front line from underneath,
        // the rig behind them, sliding past at walking pace.
        const float x = side * std::clamp( -6.5f + held * 0.8f, -6.5f, 6.5f );
        outEye = Vector3( x + m_plan.ShotOffset.x, 1.7f, m_plan.Stage.BarricadeZ + 0.4f );
        outTarget = OnStage( Vector3( x * 0.35f, 2.75f, 3.8f ) );
        outFov = 52.f;
        break;
    }
    case Framing::Drone:
    {
        // Flown in from the back of the house over the crowd, sinking toward the stage.
        const float top = std::min( m_room.Ceiling - 2.5f, 13.f );
        const float start = std::max( m_room.Back + 4.f, -40.f );
        outEye = Vector3( side * ( 4.f - std::min( held * 0.25f, 4.f ) ), top - std::min( held * 0.35f, 4.f ), std::min( start + held * 2.4f, -7.f ) );
        outTarget = OnStage( Vector3( 0.f, 2.4f, 5.f ) );
        outFov = 55.f;
        break;
    }
    case Framing::Orbit:
    {
        // High and slow round the front of the stage.
        const float angle = side * std::min( 30.f + held * 2.5f, 75.f ) * kPi / 180.f;
        const float height = std::min( m_room.Ceiling - 2.5f, 10.f );
        outTarget = OnStage( Vector3( 0.f, 2.2f, 3.5f ) );
        outEye = Vector3( outTarget.x + std::sin( angle ) * 15.f, height, outTarget.z - std::cos( angle ) * 15.f );
        outFov = 50.f;
        break;
    }
    case Framing::LongLens:
    {
        // From the mixing desk on a long lens: the stage flattened against its lights, the
        // crowd's heads and hands soft in the foreground. A slow zoom in while it's held.
        amongCrowd = true;
        if( const VenuePlan::CameraSpot* spot = pick( VenuePlan::CameraSpot::Kind::Desk ) )
        {
            outEye = spot->Eye;
            authored = true;
        }
        else
        {
            outEye = Vector3( side * 1.6f + m_plan.ShotOffset.x, 2.7f, std::max( m_room.DeskZ + 1.4f, m_room.Back + 2.f ) );
        }
        outTarget = subject >= 0 || duo ? SubjectPoint( inPlan, false ) + Vector3( 0.f, 0.2f, 0.f ) : OnStage( Vector3( 0.f, 2.7f, 4.f ) );
        const float distance = std::max( ( outTarget - outEye ).Length(), 1.f );
        const float half = subject >= 0 ? 1.5f : duo ? 2.4f : 3.3f;
        outFov = std::clamp( 2.f * std::atan( half / distance ) * 180.f / kPi, 5.f, 34.f ) * ( 1.f - 0.08f * std::min( progress, 1.5f ) );
        break;
    }
    case Framing::CrowdPov:
        // In the crowd a few rows back, on tiptoe: the stage through everyone's raised hands.
        amongCrowd = true;
        outEye = Vector3( side * 2.2f + m_plan.ShotOffset.x, 1.95f, -6.2f + m_plan.ShotOffset.z );
        outTarget = OnStage( Vector3( -side * 0.8f, 3.f, 2.5f ) );
        outFov = 58.f;
        dolly = 0.3f;
        break;
    case Framing::Profile:
        // From the wings across the stage: the band in a line, the crowd beyond the edge.
        outEye = OnStage( Vector3( side * 8.4f, 2.55f, 0.9f + 0.5f * std::min( progress, 2.f ) ) );
        outTarget = OnStage( Vector3( -side * 4.5f, 2.35f, 3.4f ) );
        outFov = 60.f;
        break;
    case Framing::DrumTop:
    {
        // Straight down on the kit from the rig, sinking toward it and turning slowly. The top
        // of the picture is upstage.
        outEye = AtDrums( drums + Vector3( side * 0.25f, 4.4f - 0.5f * std::min( progress, 1.5f ), -0.55f ) );
        outTarget = AtDrums( drums + Vector3( 0.f, 0.75f, -0.45f ) );
        outFov = 50.f;
        const float turn = side * ( 8.f + 6.f * progress ) * kPi / 180.f;
        if( outUp )
        {
            *outUp = Vector3( std::sin( turn ), 0.f, std::cos( turn ) );
            if( m_plan.SpotOf( VenueData::Drums ).Yaw != 180.f ) *outUp = AtDrums( drums + *outUp ) - drums;
        }
        break;
    }
    case Framing::DrumLow:
        // Low at the front of the riser, the drummer through the cymbals.
        outTarget = ( m_band && m_band->HasMember( VenueData::Drums ) ? m_band->HeadOf( VenueData::Drums ) : drums + Vector3( 0.f, 1.25f, 0.f ) ) + Vector3( 0.f, -0.2f, 0.f );
        outEye = AtDrums( drums + Vector3( side * 1.35f, 0.95f, -1.75f ) );
        outFov = 40.f;
        drift = 9.f * side;
        dolly = 0.3f;
        break;
    case Framing::LowHero:
    {
        // Down on the deck by their monitor, looking up: the player against the rig overhead.
        const bool there = m_band && subject >= 0 && m_band->HasMember( subject );
        const Vector3 feet = there ? m_band->FeetOf( subject ) : m_plan.SpotOf( VenueData::Vocals ).Feet;
        outTarget = ( there ? m_band->HeadOf( subject ) : feet + Vector3( 0.f, 1.7f, 0.f ) ) + Vector3( 0.f, -0.3f, 0.f );
        outEye = feet + Vector3( side * 0.85f, 0.32f, -1.3f );
        outFov = 50.f;
        drift = 6.f * side;
        dolly = 0.25f;
        break;
    }
    case Framing::Push:
    {
        // A run in from over the crowd to the lip of the stage, most of it in the first second.
        const float run = 1.f - std::exp( -held / 1.1f );
        outEye = OnStage( Lerp( Vector3( side * 1.5f, 5.6f, -12.f ), Vector3( side * 0.6f, 2.7f, -1.3f ), run ) );
        outTarget = OnStage( Vector3( 0.f, 2.6f, 4.f ) );
        outFov = 56.f;
        break;
    }
    case Framing::PitRun:
    {
        // An operator at a half sprint down the photo pit with the camera on their shoulder,
        // like a reality show's crew chasing someone backstage: the lens ahead of them and turned
        // into the front row, faces going by at arm's length. At the end of the pit they slow,
        // swing round across the crowd and come back. The cut lands on them well into the run.
        constexpr float kHalfRun = 7.f;     // short of the tripods parked at the pit's ends
        constexpr float kTopSpeed = 2.7f;   // metres a second
        // A rounded triangle wave, not a sine: they hold close to the top speed across the whole
        // front of the crowd (over 84% of it for the middle four fifths of the pit) and only brake
        // in the last metre or so. The cut finds them at speed, a second and a half short of centre.
        constexpr float kSharp = 0.95f;     // 0: a sine's long slowing .. 1: an instant turn
        const float span = std::asin( kSharp );
        const float phase = -0.8f + held * kTopSpeed * span / ( kSharp * kHalfRun );
        const float swing = kSharp * std::sin( phase );
        const float x = side * kHalfRun * std::asin( swing ) / span;
        const float pace = side * std::cos( phase ) / std::sqrt( 1.f - swing * swing );    // of the top speed, signed along the pit
        outEye = Vector3( x + m_plan.ShotOffset.x, 1.55f, m_plan.Stage.BarricadeZ + 0.5f );
        outTarget = Vector3( x + m_plan.ShotOffset.x + pace * 1.6f, 1.6f, m_plan.CrowdFront() - 2.2f );
        outFov = 66.f;
        break;
    }
    case Framing::Story:
    {
        // A story shot: its spot, moving to its end spot over the hold (eased at both ends).
        const StoryShot& shot = m_storyShots[static_cast<size_t>( std::max( inPlan.Variant, 0 ) ) % std::max<size_t>( m_storyShots.size(), 1 )];
        const VenuePlan::CameraSpot& a = m_plan.Cameras[shot.Spot];
        const VenuePlan::CameraSpot& b = m_plan.Cameras[shot.End >= 0 ? shot.End : shot.Spot];
        const float u = VenueTiming::Smooth( held / std::max( static_cast<float>( shot.Until - shot.From ), 0.1f ) );
        Vector3 forward;
        if( shot.Via.empty() )
        {
            outEye = Lerp( a.Eye, b.Eye, u );
            forward = Lerp( a.Forward, b.Forward, u );
            outFov = a.FieldOfView + ( b.FieldOfView - a.FieldOfView ) * u;
        }
        else
        {
            // Through the spots on the way: a Catmull-Rom curve, the ends held as their own
            // neighbours, so the camera passes through each one without stopping.
            std::vector<const VenuePlan::CameraSpot*> path;
            path.push_back( &a );
            for( int via : shot.Via ) path.push_back( &m_plan.Cameras[via] );
            if( shot.End >= 0 ) path.push_back( &b );
            const int last = static_cast<int>( path.size() ) - 1;
            const float along = u * static_cast<float>( last );
            const int k = std::clamp( static_cast<int>( along ), 0, last - 1 );
            const float t = along - static_cast<float>( k );
            const VenuePlan::CameraSpot& p0 = *path[std::max( k - 1, 0 )];
            const VenuePlan::CameraSpot& p1 = *path[k];
            const VenuePlan::CameraSpot& p2 = *path[k + 1];
            const VenuePlan::CameraSpot& p3 = *path[std::min( k + 2, last )];
            const float t2 = t * t;
            const float t3 = t2 * t;
            const float w0 = 0.5f * ( -t3 + 2.f * t2 - t );
            const float w1 = 0.5f * ( 3.f * t3 - 5.f * t2 + 2.f );
            const float w2 = 0.5f * ( -3.f * t3 + 4.f * t2 + t );
            const float w3 = 0.5f * ( t3 - t2 );
            outEye = p0.Eye * w0 + p1.Eye * w1 + p2.Eye * w2 + p3.Eye * w3;
            forward = p0.Forward * w0 + p1.Forward * w1 + p2.Forward * w2 + p3.Forward * w3;
            outFov = std::clamp( p0.FieldOfView * w0 + p1.FieldOfView * w1 + p2.FieldOfView * w2 + p3.FieldOfView * w3, 2.f, 120.f );
        }
        // The target is the focus point: where the shot's "f" says, else well ahead.
        float reach = 10.f;
        if( shot.FocusFrom > 0.f || shot.FocusTo > 0.f )
        {
            const float from = shot.FocusFrom > 0.f ? shot.FocusFrom : shot.FocusTo;
            const float to = shot.FocusTo > 0.f ? shot.FocusTo : shot.FocusFrom;
            reach = from + ( to - from ) * u;
        }
        outTarget = outEye + ( forward.Length() > 1e-3f ? forward.Normalized() : a.Forward ) * reach;
        authored = true;
        break;
    }
    case Framing::Spot:
    {
        // One of the venue's own close or custom positions (AddSpotCuts), held, on its subject
        // when it has one.
        if( m_plan.Cameras.empty() )
        {
            outTarget = SubjectPoint( inPlan, false );
            outEye = outTarget + Vector3( 0.f, 0.5f, -6.f );
            outFov = 45.f;
            break;
        }
        const VenuePlan::CameraSpot& spot = m_plan.Cameras[static_cast<size_t>( std::max( inPlan.Variant, 0 ) ) % m_plan.Cameras.size()];
        const Vector3 chest = SubjectPoint( inPlan, false );
        outEye = spot.Eye;
        outTarget = SpotTarget( spot, subject >= 0 || duo ? &chest : nullptr );
        outFov = spot.FieldOfView;
        authored = true;
        drift = 2.f * side;
        dolly = 0.3f;
        break;
    }
    }
    if( !authored ) Contain( outEye, amongCrowd );
    // The generic move: an orbit and a push in.
    outEye = Orbit( outEye, outTarget, drift * progress );
    const Vector3 toward = ( outTarget - outEye ).Normalized();
    outEye = outEye + toward * ( dolly * progress );
    if( !authored ) Contain( outEye, amongCrowd );
}


float Director::LeadSideFor( const Plan& inPlan, const Vector3& inEye, const Vector3& inTarget ) const
{
    // One member, framed on them: not wide group shots, the guitar's neck camera (bolted on),
    // from behind, the kick drum or the crowd.
    const bool framed = inPlan.Frame == Framing::Near || inPlan.Frame == Framing::CloseHead || inPlan.Frame == Framing::CloseHand || inPlan.Frame == Framing::Far
        || inPlan.Frame == Framing::LowHero || inPlan.Frame == Framing::LongLens;
    if( !framed || inPlan.Subjects.size() != 1 || inPlan.Subjects[0] < 0 || !m_band || !m_band->HasMember( inPlan.Subjects[0] ) )
    {
        return 0.f;
    }
    // A sideways axis across the picture (either way: the side is relative to it, then turned
    // back through it, so which way the screen's right is doesn't matter).
    const Vector3 ahead = Vector3( inTarget.x - inEye.x, 0.f, inTarget.z - inEye.z );
    if( ahead.Length() < 1e-3f )
    {
        return 0.f;
    }
    const Vector3 across = ahead.Normalized().Cross( Vector3::Up ).Normalized();
    // Looking toward +across puts them on the -across side, looking into the frame over the
    // highway. Looking down the lens: their side of the stage.
    const int member = inPlan.Subjects[0];
    const float looking = m_band->GazeOf( member ).Dot( across );
    if( std::fabs( looking ) > 0.12f )
    {
        return looking > 0.f ? 1.f : -1.f;
    }
    const float standing = ( m_plan.SpotOf( member ).Feet - Vector3( 0.f, 0.f, 0.f ) ).Dot( across );
    if( std::fabs( standing ) > 0.5f )
    {
        return standing > 0.f ? -1.f : 1.f;
    }
    return inPlan.Variant % 2 == 0 ? 1.f : -1.f;
}


Vector3 Director::LeadRoom( const Vector3& inEye, const Vector3& inTarget, float inSide, float inFov, float inAspect )
{
    // Turn the aim (about the vertical, through the eye) toward inSide * across, far enough that
    // the subject, who was dead centre, sits 60% of the way out from the middle on the other side:
    // past the highway's edge at head height, inside the frame.
    constexpr float kOut = 0.6f;
    const Vector3 toward = inTarget - inEye;
    const Vector3 ahead( toward.x, 0.f, toward.z );
    const float reach = ahead.Length();
    if( reach < 1e-3f )
    {
        return inTarget;
    }
    const Vector3 forward = ahead * ( 1.f / reach );
    const Vector3 across = forward.Cross( Vector3::Up ).Normalized();
    const float halfWidth = std::tan( inFov * 0.5f * 3.14159265f / 180.f ) * std::max( inAspect, 0.1f );
    const float angle = std::atan( kOut * halfWidth );
    const Vector3 turned = ( forward * std::cos( angle ) + across * ( inSide * std::sin( angle ) ) ) * reach;
    return inEye + Vector3( turned.x, toward.y, turned.z );
}


Director::Grade Director::GradeFor( const std::string& inLook )
{
    // Rock Band's post-processing looks, as the engine's grading can make them.
    Grade grade;
    const auto has = [&inLook]( const char* inWord ) { return inLook.find( inWord ) != std::string::npos; };
    if( inLook.empty() || StartsWith( inLook, "ProFilm_a" ) )
    {
        // The everyday look: a concert film's, a little contrast, the lights blooming, the
        // corners falling off.
        grade.Contrast = 1.04f;
        grade.Bloom = 1.25f;
        grade.Vignette = 0.38f;
        return grade;
    }
    if( StartsWith( inLook, "ProFilm_b" ) ) { grade.Contrast = 1.12f; grade.Temperature = 0.12f; return grade; }
    if( has( "psychedelic" ) ) { grade.Saturation = 1.7f; grade.Tint = 0.4f; grade.Bloom = 2.5f; return grade; }
    if( has( "mirror" ) ) { grade.Contrast = 1.15f; grade.Saturation = 1.2f; return grade; }
    if( has( "sepia" ) ) { grade.Saturation = 0.f; grade.Temperature = 0.75f; grade.Contrast = 1.1f; grade.Vignette = 0.55f; return grade; }
    // The concert look: a live feed on an arena screen (black and white toned rose and cream by
    // the LUT, washed out and glowing, grainy, stepping at 12 frames a second). Rock Band's black
    // and white looks all play as this.
    if( has( "concert" ) || has( "silvertone" ) || has( "b+w" ) || has( "_bw" ) || has( "photocopy" ) )
    {
        grade.Saturation = 0.f;
        grade.Contrast = 1.15f;
        grade.Exposure = 0.1f;
        grade.Bloom = 2.2f;
        grade.Vignette = 0.55f;
        grade.Lut = 1.f;
        grade.Grain = 0.11f;
        grade.FrameRate = 12.f;
        return grade;
    }
    if( has( "photo_negative" ) ) { grade.Saturation = 0.f; grade.Contrast = 1.6f; grade.Tint = -0.3f; return grade; }
    if( has( "posterize" ) ) { grade.ColorBits = 3; grade.Saturation = 1.3f; return grade; }
    if( has( "shitty_tv" ) ) { grade.Saturation = 0.55f; grade.Contrast = 1.3f; grade.ColorBits = 4; grade.Dither = 0.6f; grade.Vignette = 0.7f; return grade; }
    if( has( "security" ) ) { grade.Saturation = 0.f; grade.Tint = -0.5f; grade.Contrast = 1.25f; grade.ColorBits = 4; grade.Vignette = 0.6f; return grade; }
    if( has( "16mm" ) ) { grade.Saturation = 0.75f; grade.Contrast = 1.18f; grade.Temperature = 0.3f; grade.Dither = 0.35f; grade.Vignette = 0.6f; return grade; }
    if( StartsWith( inLook, "video_a" ) ) { grade.Saturation = 0.85f; grade.Contrast = 1.12f; grade.Tint = -0.12f; grade.Vignette = 0.45f; return grade; }
    if( has( "blue_filter" ) ) { grade.Temperature = -0.65f; grade.Saturation = 0.9f; return grade; }
    if( has( "desat_blue" ) ) { grade.Saturation = 0.35f; grade.Temperature = -0.45f; return grade; }
    if( has( "contrast_red" ) ) { grade.Contrast = 1.4f; grade.Temperature = 0.5f; grade.Tint = 0.25f; return grade; }
    if( has( "contrast_green" ) ) { grade.Contrast = 1.4f; grade.Tint = -0.45f; return grade; }
    if( has( "contrast_blue" ) ) { grade.Contrast = 1.4f; grade.Temperature = -0.5f; return grade; }
    if( has( "contrast" ) ) { grade.Contrast = 1.42f; grade.Saturation = 1.15f; return grade; }
    if( has( "horror" ) ) { grade.Saturation = 0.2f; grade.Contrast = 1.5f; grade.Temperature = -0.3f; grade.Vignette = 0.8f; return grade; }
    if( has( "trails" ) || has( "woosh" ) ) { grade.Bloom = 3.f; grade.Saturation = has( "desat" ) ? 0.4f : 1.2f; grade.ColorBits = has( "posterize" ) ? 4 : 0; return grade; }
    if( has( "bloom" ) || has( "bright" ) ) { grade.Bloom = 4.f; grade.Exposure = has( "bright" ) ? 0.5f : 0.f; return grade; }
    return grade;
}


void Director::ApplyGrade( float inDeltaTime )
{
    if( !m_main || !m_main->HasComponent<PostProcess>() )
    {
        return;
    }
    // Looks cut in quickly but not in one frame.
    const float ease = 1.f - std::exp( -inDeltaTime * 12.f );
    const auto toward = [ease]( float& ioValue, float inTarget ) { ioValue += ( inTarget - ioValue ) * ease; };
    toward( m_grade.Saturation, m_gradeTarget.Saturation );
    toward( m_grade.Contrast, m_gradeTarget.Contrast );
    toward( m_grade.Temperature, m_gradeTarget.Temperature );
    toward( m_grade.Tint, m_gradeTarget.Tint );
    toward( m_grade.Bloom, m_gradeTarget.Bloom );
    toward( m_grade.Vignette, m_gradeTarget.Vignette );
    toward( m_grade.Exposure, m_gradeTarget.Exposure );
    toward( m_grade.Dither, m_gradeTarget.Dither );
    toward( m_grade.Lut, m_gradeTarget.Lut );
    toward( m_grade.Grain, m_gradeTarget.Grain );
    m_grade.ColorBits = m_gradeTarget.ColorBits;
    m_grade.FrameRate = m_gradeTarget.FrameRate;
    PostProcess& post = m_main->GetComponent<PostProcess>();
    post.Saturation = m_grade.Saturation;
    post.Contrast = m_grade.Contrast;
    post.Temperature = m_grade.Temperature;
    post.Tint = m_grade.Tint;
    post.BloomIntensity = 0.12f * m_grade.Bloom;
    post.VignetteIntensity = m_grade.Vignette;
    post.ExposureCompensation = m_grade.Exposure + m_closeExposure;
    post.EraColorBits = m_grade.ColorBits;
    post.EraDither = m_grade.Dither;
    post.LutContribution = m_grade.Lut;
    post.FilmGrain = m_grade.Grain;
}


float Director::FrameRateAt( double inSeconds ) const
{
    static const std::string forcedLook = CommandLine::GetString( "--venue-look", "" );
    size_t index = 0;
    const TimedCueData* look = forcedLook.empty() ? VenueTiming::CueAt( m_looks, inSeconds, &index ) : nullptr;
    const int cue = !forcedLook.empty() ? -3 : look ? static_cast<int>( index ) : -1;
    if( cue != m_rateCue )
    {
        m_rateCue = cue;
        m_rate = GradeFor( !forcedLook.empty() ? forcedLook : look ? look->m_name : std::string() ).FrameRate;
    }
    return m_rate;
}


void Director::SetFeedStepRate( float inStepRate, float inFrameSeconds )
{
    // Frames per step, 2 (the smooth venue's rate) at the least. The feed then renders on about every step.
    const int interval = inStepRate > 0.f && inFrameSeconds > 0.f ? std::clamp( static_cast<int>( std::lround( 1.f / ( inStepRate * inFrameSeconds ) ) ), 2, 30 ) : 2;
    for( EntityHandle* feed : { &m_feed, &m_program } )
    {
        if( *feed && ( *feed )->HasComponent<Camera>() )
        {
            ( *feed )->GetComponent<Camera>().UpdateInterval = interval;
        }
    }
}


void Director::SetGrainFrame( int inFrame )
{
    for( EntityHandle* camera : { &m_main, &m_program } )
    {
        if( *camera && ( *camera )->HasComponent<PostProcess>() )
        {
            ( *camera )->GetComponent<PostProcess>().FilmGrainFrame = inFrame;
        }
    }
}


void Director::BuildFallbackLooks( const VenueData& inVenue )
{
    // The concert look through each quiet stretch, back to the default grade after it.
    bool inLook = false;
    for( const TimedCueData& section : inVenue.m_sections )
    {
        std::string name = section.m_name;
        std::transform( name.begin(), name.end(), name.begin(), []( unsigned char c ) { return static_cast<char>( std::tolower( c ) ); } );
        const bool quiet = VenueTiming::Contains( name, "intro" ) || VenueTiming::Contains( name, "bridge" ) || VenueTiming::Contains( name, "breakdown" )
            || VenueTiming::Contains( name, "quiet" ) || VenueTiming::Contains( name, "spacey" );
        if( quiet != inLook )
        {
            m_looks.push_back( { section.m_time, quiet ? std::string( kConcertLook ) : std::string() } );
            inLook = quiet;
        }
    }
}


void Director::UpdateFeed( double inSeconds, float inDeltaTime, int inCutIndex )
{
    if( !m_feed || !m_band )
    {
        return;
    }
    // A close-up for the wall, re-chosen every two measures: the main shot's member when it has
    // one, else whoever's carrying the song.
    const double beatLength = 60.0 / std::max( 30.f, m_bpm );
    if( inSeconds - m_feedSince > beatLength * 8.0 || inSeconds < m_feedSince )
    {
        m_feedSince = inSeconds;
        int subject = -1;
        if( inCutIndex >= 0 && m_cuts[inCutIndex].Shot.Subjects.size() == 1 )
        {
            subject = m_cuts[inCutIndex].Shot.Subjects[0];
        }
        if( subject < 0 || !m_band->HasMember( subject ) )
        {
            float best = -1.f;
            for( int member = 0; member < VenueData::MemberCount; ++member )
            {
                const float score = m_band->Activity( member, inSeconds + 1.0 ) * ( member == VenueData::Vocals ? 1.6f : 1.f ) + VenueTiming::Noise( static_cast<uint32_t>( inSeconds ), member ) * 0.7f;
                if( m_band->HasMember( member ) && score > best )
                {
                    best = score;
                    subject = member;
                }
            }
        }
        m_feedSubject = std::max( 0, subject );
        m_feedVariant = static_cast<int>( VenueTiming::Noise( static_cast<uint32_t>( inSeconds * 3.0 ), 77u ) * 4.f );
    }
    const Vector3 head = m_band->HeadOf( m_feedSubject );
    const float side = m_feedVariant % 2 == 0 ? -1.f : 1.f;
    const bool wide = m_feedVariant == 3;
    const Vector3 target = wide ? m_band->ChestOf( m_feedSubject ) : head + Vector3( 0.f, -0.1f, 0.f );
    // The operator stands in the pit: low and to one side, tracking the subject loosely.
    const Vector3 eye = target + Vector3( side * 1.1f, -0.5f, wide ? -3.2f : -1.8f );
    const float t = static_cast<float>( inSeconds );
    const Vector3 shake( 0.02f * std::sin( t * 1.9f ), 0.015f * std::sin( t * 2.6f ), 0.f );
    // Eased per second, not per frame, so it tracks the same at any frame rate.
    const float dt = std::clamp( inDeltaTime, 0.f, 0.1f );
    m_feedEye = Lerp( m_feedEye, eye + shake, 1.f - std::exp( -dt * 6.f ) );
    m_feedTarget = Lerp( m_feedTarget, target, 1.f - std::exp( -dt * 9.f ) );
    Transform& transform = m_feed->GetComponent<Transform>();
    transform.SetPosition( VenueLayout::kVenueOrigin + m_feedEye );
    transform.LookAt( VenueLayout::kVenueOrigin + m_feedTarget );
    Camera& camera = m_feed->GetComponent<Camera>();
    (void)camera;
}


void Director::SetStoryShots( const std::vector<std::pair<std::string, double>>& inLanding )
{
    m_storyShots.clear();
    const auto& spots = m_plan.Cameras;
    for( const auto& [flag, at] : inLanding )
    {
        StoryShot shot;
        float hold = 5.f;
        std::vector<std::pair<int, int>> vias;    // (order, spot)
        for( size_t i = 0; i < spots.size(); ++i )
        {
            const std::string& tag = spots[i].Tag;
            const std::string head = "story/" + flag;
            if( spots[i].Shot != VenuePlan::CameraSpot::Kind::Custom || tag.compare( 0, head.size(), head ) != 0 || ( tag.size() > head.size() && tag[head.size()] != '/' ) )
            {
                continue;
            }
            bool end = false;
            bool hand = false;
            float seconds = -1.f;
            float focus = 0.f;
            int via = -1;
            size_t from = head.size();
            while( from < tag.size() )
            {
                const size_t next = std::min( tag.find( '/', from + 1 ), tag.size() );
                const std::string part = tag.substr( from + 1, next - from - 1 );
                const bool numbered = part.size() > 1 && ( std::isdigit( static_cast<unsigned char>( part[1] ) ) || part[1] == '.' );
                if( part == "end" ) end = true;
                else if( part == "hand" ) hand = true;
                else if( part[0] == 'w' && numbered ) via = std::atoi( part.c_str() + 1 );
                else if( part[0] == 'f' && numbered ) focus = static_cast<float>( std::atof( part.c_str() + 1 ) );
                else if( !part.empty() && ( std::isdigit( static_cast<unsigned char>( part[0] ) ) || part[0] == '.' ) ) seconds = static_cast<float>( std::atof( part.c_str() ) );
                from = next;
            }
            if( via >= 0 )
            {
                vias.emplace_back( via, static_cast<int>( i ) );
                continue;
            }
            if( end )
            {
                shot.End = static_cast<int>( i );
                shot.FocusTo = focus;
                continue;
            }
            shot.Spot = static_cast<int>( i );
            shot.Handheld = hand;
            shot.FocusFrom = focus;
            if( seconds > 0.f ) hold = seconds;
        }
        std::sort( vias.begin(), vias.end() );
        for( const auto& [order, spot] : vias ) shot.Via.push_back( spot );
        if( shot.Spot < 0 )
        {
            continue;
        }
        shot.From = at;
        shot.Until = at + hold;
        m_storyShots.push_back( shot );
    }
    std::sort( m_storyShots.begin(), m_storyShots.end(), []( const StoryShot& a, const StoryShot& b ) { return a.From < b.From; } );
}


void Director::OnBigMoment( double inSeconds, float inHoldSeconds )
{
    m_bigStart = inSeconds;
    m_bigEnd = inSeconds + std::max( inHoldSeconds, 0.f );
}


float Director::BlurFor( const Plan& inPlan )
{
    // How soft the background goes, as a blur radius in pixels at 1080p for things far behind
    // the subject: the tighter the shot, the softer. Wide shots, the neck camera and the crowd
    // surfer's shot keep everything sharp.
    switch( inPlan.Frame )
    {
    case Framing::Near: return inPlan.Subjects.empty() ? 0.f : 6.f;
    case Framing::CloseHead:
    case Framing::CloseHand: return 9.f;
    case Framing::Kick:
    case Framing::DrumLow: return 7.f;
    case Framing::LowHero: return 6.f;
    case Framing::LongLens: return 8.f;
    case Framing::Story: return inPlan.Blur;
    default: return 0.f;
    }
}


float Director::LensFor( const Plan& inPlan )
{
    switch( inPlan.Frame )
    {
    case Framing::PitRun: return 0.8f;
    case Framing::Neck: return 0.6f;
    case Framing::CrowdPov: return 0.8f;
    // The arrival is shot on a handycam with a wide-angle adapter.
    case Framing::Arrival: return 0.6f;
    default: return 0.f;
    }
}


void Director::ApplyFocus( const Plan& inPlan, const Vector3& inEye, const Vector3& inSubject, float inFov, bool inCut, float inDeltaTime )
{
    if( !m_main || !m_main->HasComponent<PostProcess>() )
    {
        return;
    }
    // A focus puller on the subject: the distance and the blur ease (snapped on a cut), and the
    // aperture is whatever gives this shot's blur at its lens and distance, so a long lens from
    // the desk and a wide one in the pit both leave the lights behind the player as soft discs.
    const float focus = std::clamp( ( inSubject - inEye ).Length(), 0.3f, 200.f );
    const float blur = BlurFor( inPlan );
    if( inCut )
    {
        m_focus = focus;
        m_blur = blur;
    }
    else
    {
        const float dt = std::clamp( inDeltaTime, 0.f, 0.1f );
        m_focus += ( focus - m_focus ) * ( 1.f - std::exp( -dt * 5.f ) );
        m_blur += ( blur - m_blur ) * ( 1.f - std::exp( -dt * 6.f ) );
    }
    // The rig is balanced for the wide picture: up close the same light on a white shirt burns
    // out, so the nearer the subject the further the lens is stopped down (eased with the focus).
    m_closeExposure = -1.1f * ( 1.f - VenueTiming::Smooth( ( m_focus - 1.5f ) / 10.f ) );
    PostProcess& post = m_main->GetComponent<PostProcess>();
    post.DepthOfField = m_blur > 0.3f;
    if( !post.DepthOfField )
    {
        return;
    }
    // The engine's thin lens (Engine/Docs/Depth-of-Field.md): at infinity the blur radius is
    // f^2 * height / ( 2 N ( focus - f ) sensor ), with f from the field of view. Solved for N.
    const float sensor = post.DoFSensorHeight * 0.001f;
    const float focal = sensor / ( 2.f * std::tan( std::clamp( inFov, 2.f, 120.f ) * 0.5f * kPi / 180.f ) );
    const float reach = std::max( m_focus - focal, 0.05f );
    post.DoFFocusDistance = m_focus;
    post.DoFAperture = std::clamp( focal * focal * 1080.f / ( 2.f * m_blur * reach * sensor ), 0.7f, 22.f );
    post.DoFMaxBlurRadius = 20.f;
}


void Director::Update( double inSeconds, float inDeltaTime )
{
    if( !m_main )
    {
        return;
    }
    // --venue-shot <name> holds one shot (a cut name) for the whole song, to frame it.
    static const std::string forcedShot = CommandLine::GetString( "--venue-shot", "" );
    static const std::string forcedLook = CommandLine::GetString( "--venue-look", "" );
    const float dt = std::clamp( inDeltaTime, 0.f, 0.1f );
    int index = -1;
    Plan plan;
    float held = 0.f;
    if( !forcedShot.empty() )
    {
        plan = PlanFor( forcedShot, 0 );
        if( StartsWith( forcedShot, "spot:" ) )
        {
            const auto& spots = m_plan.Cameras;
            const auto it = std::find_if( spots.begin(), spots.end(), [&]( const auto& s ) { return s.Tag == forcedShot.substr( 5 ); } );
            if( it != spots.end() )
            {
                plan = Plan();
                plan.Frame = Framing::Spot;
                plan.Variant = static_cast<int>( it - spots.begin() );
                plan.Static = true;
            }
        }
        DropAbsent( plan );
        held = static_cast<float>( inSeconds );
        m_shotName = forcedShot;
    }
    else
    {
        auto it = std::upper_bound( m_cuts.begin(), m_cuts.end(), static_cast<float>( inSeconds ), []( float t, const Cut& c ) { return t < c.Time; } );
        if( it == m_cuts.begin() )
        {
            plan.Frame = Framing::Far;
            held = static_cast<float>( inSeconds ) + 10.f;
            m_shotName = "opening";
        }
        else
        {
            index = static_cast<int>( it - m_cuts.begin() ) - 1;
            plan = m_cuts[index].Shot;
            held = static_cast<float>( inSeconds ) - m_cuts[index].Time;
            m_shotName = m_cuts[index].Name;
        }
        // A big moment gets a hero shot: the crane going up over the crowd, a run in to the
        // band, or over the band at the crowd, the same one for the same moment. The guitar's
        // neck camera keeps the screen.
        if( inSeconds >= m_bigStart && inSeconds < m_bigEnd && plan.Frame != Framing::Neck )
        {
            const uint32_t moment = static_cast<uint32_t>( std::max( 0.0, m_bigStart ) * 2.0 );
            const int pick = static_cast<int>( VenueTiming::Noise( moment, 91u ) * 3.f ) % 3;
            plan = Plan();
            plan.Frame = pick == 0 ? Framing::Crane : pick == 1 ? Framing::Push : Framing::Behind;
            plan.Variant = static_cast<int>( VenueTiming::Noise( moment, 92u ) * 2.f );
            index = -4;
            held = static_cast<float>( inSeconds - m_bigStart );
            m_shotName = pick == 0 ? "big_moment_crane" : pick == 1 ? "big_moment_push" : "big_moment_reverse";
        }
        if( m_accentPhase >= 0.f && m_accentPhase < 1.f && HasPeakShots() && plan.Frame != Framing::Neck )
        {
            const size_t pick = std::min( static_cast<size_t>( m_accentPhase * m_peakSpots.size() ), m_peakSpots.size() - 1 );
            plan = Plan();
            plan.Frame = Framing::Spot;
            plan.Handheld = true;
            plan.Variant = m_peakSpots[pick];
            m_shotName = m_plan.Cameras[plan.Variant].Tag;
            index = -4;
            held = 0.f;
        }
        // A crowd surfer takes the shot until they reach the barricade.
        if( m_surferUp )
        {
            plan = Plan();
            plan.Frame = Framing::Surfer;
            plan.Handheld = true;
            index = -3;
            held = 0.f;
            m_shotName = "follow_surfer";
        }
    }
    if( forcedShot.empty() && m_arrival.size() >= 2 )
    {
        const float duration = static_cast<float>( m_arrival.size() - 1 ) * kArrivalInterval + kArrivalTail;
        if( m_arrivalElapsed < 0.f ) m_arrivalElapsed = inSeconds <= 0.5 ? 0.f : duration;
        else if( std::abs( inSeconds - m_arrivalLastSongTime ) > std::max( 3., 4. * inDeltaTime ) ) m_arrivalElapsed = duration;
        else m_arrivalElapsed = std::min( duration, m_arrivalElapsed + std::max( inDeltaTime, 0.f ) );
        m_arrivalLastSongTime = inSeconds;
        if( m_arrivalElapsed < duration )
        {
            index = -5;
            plan = Plan();
            plan.Frame = Framing::Arrival;
            plan.Handheld = true;
            m_shotName = "venue_arrival";
        }
    }
    // A story shot holds the screen over everything (the arrival too).
    if( forcedShot.empty() )
    {
        for( size_t i = 0; i < m_storyShots.size(); ++i )
        {
            const StoryShot& shot = m_storyShots[i];
            if( inSeconds >= shot.From && inSeconds < shot.Until )
            {
                plan = Plan();
                plan.Frame = Framing::Story;
                plan.Variant = static_cast<int>( i );
                plan.Handheld = shot.Handheld;
                plan.Blur = shot.FocusFrom > 0.f || shot.FocusTo > 0.f ? 11.f : 0.f;
                plan.Static = true;
                index = -6 - static_cast<int>( i );
                held = static_cast<float>( inSeconds - shot.From );
                m_shotName = m_plan.Cameras[shot.Spot].Tag;
            }
        }
    }
    // The shot's move runs on its own clock, a little faster when the show is worked up: started
    // from the time since the cut, so a seek lands mid-move. (A held shot follows the song clock,
    // so a capture at a time always frames the same.)
    const bool cut = index != m_framedCut || m_shotName != m_framedShot;
    // --highway-log: each cut as it's taken.
    static const bool kLogCuts = CommandLine::Has( "--highway-log" );
    if( cut && kLogCuts )
    {
        BRUH_FMT( "Venue: cut at %.2f s to %s (framing %d, variant %d)", inSeconds, m_shotName.c_str(), static_cast<int>( plan.Frame ), plan.Variant );
    }
    if( !forcedShot.empty() || cut )
    {
        m_moveTime = std::max( held, 0.f );
    }
    else
    {
        m_moveTime += dt * ( 1.f + 0.5f * m_hype );
    }
    Vector3 eye;
    Vector3 target;
    float fov = 45.f;
    Vector3 up = Vector3::Up;
    Frame( plan, plan.Frame == Framing::Arrival ? m_arrivalElapsed : plan.Frame == Framing::Story ? held : m_moveTime, eye, target, fov, &up );
    // A fisheye swells the middle of the picture: the shot is taken that much wider, so what it
    // framed is still what's in the middle. The lens changes with the cut.
    const float lensLook = LensFor( plan );
    float lens = lensLook;
    if( lens > 0.f )
    {
        // The bend is a fixed angle over the picture's diagonal (Tonemap.frag), but a zoom lens
        // straightens out as it zooms in: bent past the picture's own field of view, a zoomed shot
        // swells like a magnifying glass. So the lens never bends more than the diagonal the shot
        // sees, which leaves a wide shot as it was and eases the bend off down a zoom (a crash
        // zoom ends near straight). At that bend the middle keeps the framed scale exactly.
        const float aspect = m_main->HasComponent<Camera>() ? m_main->GetComponent<Camera>().GetAspectRatio() : 16.f / 9.f;
        const float diagonal = std::tan( fov * 0.5f * kPi / 180.f ) * std::sqrt( aspect * aspect + 1.f );
        lens = std::min( lens, diagonal / Moonlight::PostProcessSettings::LensDistortionAngle( 1.f ) );
        fov = 2.f * std::atan( std::tan( fov * 0.5f * kPi / 180.f ) * Moonlight::PostProcessSettings::LensDistortionZoom( lens ) ) * 180.f / kPi;
    }
    if( m_main->HasComponent<PostProcess>() )
    {
        PostProcess& post = m_main->GetComponent<PostProcess>();
        post.LensDistortion = lens;
        // The colour fringe is the cheap glass's edge: it eases off with the bend.
        post.LensFringe = lensLook > 0.f ? 0.6f * lens / lensLook : 0.f;
    }
    // What the lens is focused on: the subject, before the aim is turned off it for lead room.
    const Vector3 subject = target;
    // The highway runs up the middle of the screen: a one-member shot puts its subject off to the
    // side they're looking away from, so they look across the frame and aren't hidden under it.
    // The side is chosen on the cut and held, so a turn of the head doesn't swing the shot.
    if( cut )
    {
        m_leadSide = LeadSideFor( plan, eye, target );
    }
    if( m_leadSide != 0.f )
    {
        target = LeadRoom( eye, target, m_leadSide, fov, m_main->GetComponent<Camera>().GetAspectRatio() );
    }
    // The framing tracks the members' live positions, which bob, headbang and strum: following
    // them exactly shakes the whole picture. Ease toward it instead (the aim a little quicker
    // than the dolly), and snap on a cut.
    if( cut )
    {
        m_framedCut = index;
        m_framedShot = m_shotName;
        m_eye = eye;
        m_target = target;
        m_up = up;
        m_fov = fov;
    }
    else if( plan.Frame == Framing::Neck || plan.Frame == Framing::Arrival )
    {
        // The neck camera is bolted to the guitar, like a GoPro on the headstock: no easing, it
        // moves exactly as the guitar does. The guitar floats on its strap (Band::SwingInstrument),
        // which is what keeps the picture from snapping.
        m_eye = eye;
        m_target = target;
        m_up = up;
        m_fov = fov;
    }
    else
    {
        m_eye = Lerp( m_eye, eye, 1.f - std::exp( -dt * 2.5f ) );
        m_target = Lerp( m_target, target, 1.f - std::exp( -dt * 4.f ) );
        m_up = up;
        m_fov += ( fov - m_fov ) * ( 1.f - std::exp( -dt * 4.f ) );
    }
    eye = m_eye;
    target = m_target;
    up = m_up;
    fov = m_fov;
    ApplyFocus( plan, eye, subject, fov, cut, dt );
    const bool bolted = plan.Frame == Framing::Neck;
    const float t = static_cast<float>( inSeconds );
    // Handheld shots sway on top of the eased framing, so the easing doesn't damp the sway: a
    // camera on a shoulder, wandering rather than swinging, tipping a little, and less steady
    // the more the show is worked up.
    if( plan.Handheld && !bolted )
    {
        const float sway = 0.7f + 0.9f * m_hype;
        eye = eye + Vector3( 0.035f * Wander( t * 0.9f, 1u ) + 0.012f * Wander( t * 2.7f, 2u ), 0.028f * Wander( t * 1.1f, 3u ) + 0.01f * Wander( t * 3.1f, 4u ), 0.02f * Wander( t * 0.7f, 5u ) ) * sway;
        // The aim wanders with the distance: the same few degrees at any range.
        const float reach = std::clamp( ( target - eye ).Length(), 1.f, 40.f ) * 0.012f;
        target = target + Vector3( Wander( t * 0.8f, 6u ) + 0.35f * Wander( t * 2.3f, 7u ), 0.8f * Wander( t * 1.f, 8u ) + 0.3f * Wander( t * 2.9f, 9u ), 0.f ) * ( reach * sway );
        const Vector3 ahead = ( target - eye ).Normalized();
        const Vector3 across = ahead.Cross( up );
        if( across.Length() > 1e-3f )
        {
            const float roll = ( 1.1f * Wander( t * 0.6f, 10u ) + 0.35f * Wander( t * 2.2f, 11u ) ) * sway * kPi / 180.f;
            up = ( up + across.Normalized() * std::tan( roll ) ).Normalized();
        }
    }
    // The running operator's footfalls, by the ground covered (so none while they turn): the
    // camera drops and jars on each step, rocks from foot to foot and tips with it.
    if( plan.Frame == Framing::PitRun )
    {
        const float step = eye.x / 1.05f * kPi;
        const float fall = std::fabs( std::sin( step ) );
        eye = eye + Vector3( 0.f, 0.07f * fall - 0.035f, 0.035f * std::sin( step ) );
        target = target + Vector3( 0.f, 0.16f * std::sin( step * 2.f + 0.9f ) + 0.07f * std::sin( step * 4.f ), 0.f );
        const Vector3 across = ( target - eye ).Normalized().Cross( up );
        if( across.Length() > 1e-3f )
        {
            up = ( up + across.Normalized() * std::tan( 2.2f * std::sin( step + 0.4f ) * kPi / 180.f ) ).Normalized();
        }
    }
    // A jolt (Kick): a quick rattle that settles in under half a second.
    m_kick *= std::exp( -dt * 7.5f );
    if( m_kick > 0.01f && !bolted )
    {
        const float shake = 0.05f * std::min( m_kick, 2.f );
        eye = eye + Vector3( Wander( t * 23.f, 12u ), Wander( t * 27.f, 13u ), 0.f ) * shake;
        target = target + Vector3( Wander( t * 19.f, 14u ), Wander( t * 25.f, 15u ), 0.f ) * ( shake * 1.5f );
    }
    // The picture pushes in a touch on each beat when the show is up, harder on the downbeat.
    // Not while a look steps the venue: at twelve frames a second a pulse is just a flicker.
    if( m_hype > 0.01f && !bolted && plan.Frame != Framing::Surfer && FrameRateAt( inSeconds ) <= 0.f )
    {
        double beat = 0.0;
        int measureBeat = 0;
        VenueTiming::BeatAt( m_beats, m_bpm, inSeconds, beat, measureBeat );
        const float since = static_cast<float>( beat - std::floor( beat ) );
        const float pulse = std::exp( -since * 5.f ) * ( measureBeat == 0 ? 1.f : 0.45f ) * m_hype;
        fov *= 1.f - 0.012f * pulse;
    }
    // --venue-eye "x,y,z,tx,ty,tz[,fov]": a free camera in venue space, to inspect the set.
    static const std::string kFreeEye = CommandLine::GetString( "--venue-eye", "" );
    if( !kFreeEye.empty() )
    {
        const std::vector<std::string> parts = Split( kFreeEye, ',' );
        if( parts.size() >= 6 )
        {
            eye = Vector3( std::stof( parts[0] ), std::stof( parts[1] ), std::stof( parts[2] ) );
            target = Vector3( std::stof( parts[3] ), std::stof( parts[4] ), std::stof( parts[5] ) );
            up = Vector3::Up;
            fov = parts.size() >= 7 ? std::stof( parts[6] ) : 60.f;
            m_main->GetComponent<PostProcess>().DepthOfField = false;
        }
    }
    Transform& transform = m_main->GetComponent<Transform>();
    transform.SetPosition( VenueLayout::kVenueOrigin + eye );
    transform.LookAt( VenueLayout::kVenueOrigin + target, up );
    Camera& camera = m_main->GetComponent<Camera>();
    camera.SetFOV( fov );

    const TimedCueData* look = VenueTiming::CueAt( m_looks, inSeconds );
    const std::string lookName = !forcedLook.empty() ? forcedLook : look ? look->m_name : std::string();
    if( lookName != m_lookName || m_lookName.empty() )
    {
        m_lookName = lookName;
        m_gradeTarget = GradeFor( lookName );
    }
    ApplyGrade( inDeltaTime );
    UpdateFeed( inSeconds, inDeltaTime, index );
    if( m_program )
    {
        // The program feed films what the main camera shows, graded the same: in its own shot the
        // wall is black (a camera never samples its own image), so a wide shot puts the show on
        // the wall one level deep.
        Transform& program = m_program->GetComponent<Transform>();
        program.SetPosition( transform.GetPosition() );
        program.SetRotation( transform.GetRotation() );
        m_program->GetComponent<Camera>().SetFOV( fov );
        PostProcess& post = m_program->GetComponent<PostProcess>();
        post.Saturation = m_grade.Saturation;
        post.Contrast = m_grade.Contrast * 1.05f;
        post.Temperature = m_grade.Temperature;
        post.Tint = m_grade.Tint;
        post.EraColorBits = m_grade.ColorBits;
        post.ExposureCompensation = m_grade.Exposure;
        post.LutContribution = m_grade.Lut;
        post.FilmGrain = m_grade.Grain;
    }
}
