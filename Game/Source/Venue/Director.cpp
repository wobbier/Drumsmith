#include "Venue/Director.h"
#include "Venue/Band.h"
#include "Venue/VenueLayout.h"
#include "Venue/VenueTiming.h"
#include "Components/Camera.h"
#include "Components/Graphics/PostProcess.h"
#include "Components/Transform.h"
#include "Core/CommandLine.h"
#include "Engine/World.h"
#include <algorithm>
#include <cmath>
#include <sstream>

namespace
{
    constexpr float kPi = 3.14159265f;

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
    m_shotName.clear();
    m_lookName.clear();
    m_feedSince = -100.0;
    m_framedCut = -2;
    m_framedShot.clear();
}


void Director::Build( World& inWorld, const VenueData& inVenue, const std::vector<BeatData>& inBeats, float inBpm, float inSongLength, bool inMusicVideo, const Band* inBand )
{
    Clear();
    m_world = &inWorld;
    m_band = inBand;
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
    AddNeckShots( inVenue );
    m_looks = mv && !inVenue.m_mvPostFx.empty() ? inVenue.m_mvPostFx : inVenue.m_postFx;

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
        post.AmbientOcclusion = false;
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
    plan.Variant = static_cast<int>( VenueTiming::Noise( static_cast<uint32_t>( inIndex ), 41u ) * 4.f );
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
        else plan.Frame = plan.Subjects.empty() ? Framing::Near : Framing::Near;
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
        return plan;
    }
    // Unknown names: a wide shot.
    return plan;
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
    plan.Variant = static_cast<int>( VenueTiming::Noise( static_cast<uint32_t>( inIndex ), 9u ) * 4.f );
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
    return plan;
}


void Director::BuildFallbackCuts( const VenueData& inVenue, float inSongLength )
{
    // No camera cuts in the chart: a cut every two measures (on the downbeat when the tempo map
    // allows), wide at the start of a section, then whoever's busiest.
    std::vector<float> times;
    if( m_beats.size() >= 8 )
    {
        int measures = 0;
        for( const BeatData& beat : m_beats )
        {
            if( beat.m_measure && measures++ % 2 == 0 ) times.push_back( beat.m_time );
        }
    }
    else
    {
        const float step = 8.f * 60.f / std::max( 30.f, m_bpm );
        for( float time = 0.f; time < std::max( inSongLength, 30.f ); time += step ) times.push_back( time );
    }
    size_t section = 0;
    for( size_t i = 0; i < times.size(); ++i )
    {
        const float time = times[i];
        Cut cut;
        cut.Time = time;
        bool newSection = false;
        while( section < inVenue.m_sections.size() && inVenue.m_sections[section].m_time <= time + 0.05f )
        {
            ++section;
            newSection = true;
        }
        const std::string sectionName = section > 0 ? inVenue.m_sections[section - 1].m_name : std::string();
        Plan& plan = cut.Shot;
        plan.Variant = static_cast<int>( VenueTiming::Noise( static_cast<uint32_t>( i ), 51u ) * 4.f );
        plan.Handheld = VenueTiming::Noise( static_cast<uint32_t>( i ), 52u ) < 0.2f;
        const float roll = VenueTiming::Noise( static_cast<uint32_t>( i ), 53u );
        if( newSection || i == 0 )
        {
            plan.Frame = roll < 0.5f ? Framing::Far : Framing::Overhead;
            cut.Name = "fallback_all_far";
        }
        else
        {
            int subject = VenueData::Vocals;
            float best = -1.f;
            if( m_band )
            {
                for( int member = 0; member < VenueData::MemberCount; ++member )
                {
                    float score = m_band->Activity( member, time + 2.0 ) + VenueTiming::Noise( static_cast<uint32_t>( i ), 60u + member ) * 0.9f;
                    if( member == VenueData::Guitar && VenueTiming::Contains( sectionName, "solo" ) ) score += 2.f;
                    if( member == VenueData::Vocals ) score += 0.2f;
                    if( m_band->HasMember( member ) && score > best )
                    {
                        best = score;
                        subject = member;
                    }
                }
            }
            if( roll < 0.18f )
            {
                plan.Frame = Framing::Far;
            }
            else if( roll < 0.26f && VenueTiming::Contains( sectionName, "chorus" ) )
            {
                plan.Frame = Framing::Crowd;
            }
            else if( roll < 0.34f )
            {
                plan.Frame = Framing::Behind;
            }
            else
            {
                plan.Subjects = { subject };
                plan.Frame = roll < 0.6f ? Framing::Near : roll < 0.8f ? Framing::CloseHead : Framing::CloseHand;
            }
            cut.Name = "fallback";
        }
        m_cuts.push_back( cut );
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


Vector3 Director::SubjectPoint( const Plan& inPlan, bool inHead ) const
{
    if( inPlan.Subjects.empty() || !m_band )
    {
        return Vector3( 0.f, 2.7f, 4.2f );
    }
    Vector3 sum( 0.f, 0.f, 0.f );
    int count = 0;
    for( int member : inPlan.Subjects )
    {
        if( member < 0 ) continue;
        sum = sum + ( inHead ? m_band->HeadOf( member ) : m_band->ChestOf( member ) );
        ++count;
    }
    return count > 0 ? sum * ( 1.f / static_cast<float>( count ) ) : Vector3( 0.f, 2.7f, 4.2f );
}


void Director::Frame( const Plan& inPlan, float inHeld, Vector3& outEye, Vector3& outTarget, float& outFov, Vector3* outUp ) const
{
    // A shot in venue space: where the camera sits and looks, then how it drifts while held.
    const float side = ( inPlan.Variant % 2 == 0 ) ? -1.f : 1.f;
    const float alt = inPlan.Variant >= 2 ? 1.f : 0.f;
    const int subject = inPlan.Subjects.size() == 1 ? inPlan.Subjects[0] : -1;
    const bool duo = inPlan.Subjects.size() >= 2;
    float drift = 0.f;    // degrees of orbit over the shot
    float dolly = 0.f;    // metres toward the target over the shot
    if( outUp ) *outUp = Vector3::Up;
    Vector3 headstock;
    Vector3 body;
    Vector3 face;
    Vector3 edge;
    if( inPlan.Frame == Framing::Neck && m_band && m_band->NeckOf( subject >= 0 ? subject : VenueData::Guitar, headstock, body, face, edge ) )
    {
        // Mounted out past the headstock and up off the fretboard, looking down the length of the
        // neck at an angle to the body, the player beyond it. Rolled with the guitar, no drift;
        // Update steadies it so the beat's bob doesn't shake it.
        face = face.Normalized();
        edge = edge.Normalized();
        const Vector3 along = ( body - headstock ).Normalized();
        outEye = headstock - along * 0.14f + face * 0.2f + edge * 0.02f;
        outTarget = Lerp( headstock, body, 0.55f ) + edge * 0.05f;
        outFov = 60.f;
        if( outUp ) *outUp = ( edge * 0.7f + face * 0.3f ).Normalized();
        return;
    }
    switch( inPlan.Frame )
    {
    case Framing::Far:
        if( subject >= 0 )
        {
            outTarget = SubjectPoint( inPlan, false );
            outEye = outTarget + Vector3( side * 3.f, 1.4f, -9.f );
            outFov = 30.f;
        }
        else
        {
            outTarget = Vector3( 0.f, 2.8f, 4.5f );
            outEye = alt > 0.f ? Vector3( side * 9.f, 5.5f, -13.f ) : Vector3( side * 1.5f, 6.4f, -17.f );
            outTarget.y -= 0.6f;
            outFov = 42.f;
        }
        drift = 6.f * side;
        dolly = 1.5f;
        break;
    case Framing::Overhead:
        outTarget = Vector3( 0.f, 2.f, 4.f );
        outEye = Vector3( side * 6.f, 9.5f, -7.f );
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
            outTarget = Vector3( 0.f, 2.6f, 4.f );
            outEye = Vector3( side * 3.f, 2.2f - alt * 0.5f, -3.4f );
            outFov = 62.f;
        }
        drift = 5.f * side;
        dolly = 0.6f;
        break;
    case Framing::Behind:
        if( subject >= 0 && subject != VenueData::Drums )
        {
            const Vector3 chest = SubjectPoint( inPlan, false );
            outEye = chest + Vector3( side * 0.9f, 0.7f, 2.6f );
            outTarget = chest + Vector3( -side * 0.5f, -0.6f, -6.f );
            outFov = 58.f;
        }
        else
        {
            outEye = Vector3( side * 2.f, 3.8f, 9.8f );
            outTarget = Vector3( 0.f, 1.8f, -6.f );
            outFov = 66.f;
        }
        drift = 4.f * side;
        break;
    case Framing::CloseHead:
        outTarget = subject >= 0 || duo ? SubjectPoint( inPlan, true ) : Vector3( 0.f, 2.9f, 1.6f );
        outEye = outTarget + Vector3( side * 0.7f, 0.05f - alt * 0.2f, -1.4f );
        outFov = 32.f;
        drift = 7.f * side;
        break;
    case Framing::Neck:    // no guitar to ride: a close-up of the hands instead
    case Framing::CloseHand:
        if( subject == VenueData::Drums )
        {
            const Vector3 spot = VenueLayout::kMemberSpots[VenueData::Drums];
            outTarget = m_band ? m_band->HandsOf( subject ) : spot + Vector3( 0.f, 0.9f, -0.5f );
            outEye = spot + Vector3( side * 1.4f, 1.6f, -1.2f );
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
    {
        const Vector3 spot = VenueLayout::kMemberSpots[VenueData::Drums];
        outTarget = spot + Vector3( 0.f, 0.45f, -0.6f );
        outEye = spot + Vector3( side * 0.4f, 0.35f, -2.2f );
        outFov = 46.f;
        dolly = 0.3f;
        break;
    }
    case Framing::Wall:
        outTarget = Vector3( 0.f, 6.9f, VenueLayout::kBackWallZ );
        outEye = Vector3( 0.f, 5.5f, -4.f );
        outFov = 50.f;
        break;
    case Framing::Crowd:
        outEye = subject >= 0 ? SubjectPoint( inPlan, true ) + Vector3( side * 0.6f, 0.4f, 0.8f ) : Vector3( side * 4.f, 3.6f, 0.4f );
        outTarget = Vector3( -side * 2.f, 1.4f, -12.f );
        outFov = 60.f;
        drift = 10.f * side;
        break;
    }
    if( inPlan.Static )
    {
        drift = 0.f;
        dolly = 0.f;
    }
    // Low cameras stay out of the audience: in the photo pit between the barricade and the stage,
    // or up over their heads. All stay inside the room.
    const float roomBack = m_roomBack + 1.5f;
    const auto keepClear = [roomBack]( Vector3& ioEye ) {
        if( ioEye.y < 4.6f && ioEye.z < VenueLayout::kBarricadeZ + 0.3f )
        {
            ioEye.z = VenueLayout::kBarricadeZ + 0.3f;
        }
        ioEye.z = std::max( ioEye.z, roomBack );
    };
    keepClear( outEye );
    // Drift: an orbit and a push in, easing over about eight seconds.
    const float progress = 1.f - std::exp( -inHeld / 6.f );
    outEye = Orbit( outEye, outTarget, drift * progress );
    const Vector3 toward = ( outTarget - outEye ).Normalized();
    outEye = outEye + toward * ( dolly * progress );
    keepClear( outEye );
}


Director::Grade Director::GradeFor( const std::string& inLook )
{
    // Rock Band's post-processing looks, as the engine's grading can make them.
    Grade grade;
    const auto has = [&inLook]( const char* inWord ) { return inLook.find( inWord ) != std::string::npos; };
    if( inLook.empty() || StartsWith( inLook, "ProFilm_a" ) ) return grade;
    if( StartsWith( inLook, "ProFilm_b" ) ) { grade.Contrast = 1.12f; grade.Temperature = 0.12f; return grade; }
    if( has( "psychedelic" ) ) { grade.Saturation = 1.7f; grade.Tint = 0.4f; grade.Bloom = 2.5f; return grade; }
    if( has( "mirror" ) ) { grade.Contrast = 1.15f; grade.Saturation = 1.2f; return grade; }
    if( has( "sepia" ) ) { grade.Saturation = 0.f; grade.Temperature = 0.75f; grade.Contrast = 1.1f; grade.Vignette = 0.55f; return grade; }
    if( has( "silvertone" ) ) { grade.Saturation = 0.08f; grade.Contrast = 1.35f; grade.Temperature = -0.2f; return grade; }
    if( has( "b+w" ) || has( "_bw" ) || inLook == "video_bw" ) { grade.Saturation = 0.f; grade.Contrast = has( "video" ) ? 1.4f : 1.22f; grade.Vignette = 0.5f; return grade; }
    if( has( "photocopy" ) ) { grade.Saturation = 0.f; grade.Contrast = 1.9f; grade.ColorBits = 3; return grade; }
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
    m_grade.ColorBits = m_gradeTarget.ColorBits;
    PostProcess& post = m_main->GetComponent<PostProcess>();
    post.Saturation = m_grade.Saturation;
    post.Contrast = m_grade.Contrast;
    post.Temperature = m_grade.Temperature;
    post.Tint = m_grade.Tint;
    post.BloomIntensity = 0.12f * m_grade.Bloom;
    post.VignetteIntensity = m_grade.Vignette;
    post.ExposureCompensation = m_grade.Exposure;
    post.EraColorBits = m_grade.ColorBits;
    post.EraDither = m_grade.Dither;
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


void Director::Update( double inSeconds, float inDeltaTime )
{
    if( !m_main )
    {
        return;
    }
    // --venue-shot <name> holds one shot (a cut name) for the whole song, to frame it.
    static const std::string forcedShot = CommandLine::GetString( "--venue-shot", "" );
    static const std::string forcedLook = CommandLine::GetString( "--venue-look", "" );
    int index = -1;
    Plan plan;
    float held = 0.f;
    if( !forcedShot.empty() )
    {
        plan = PlanFor( forcedShot, 0 );
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
    }
    Vector3 eye;
    Vector3 target;
    float fov = 45.f;
    Vector3 up = Vector3::Up;
    Frame( plan, held, eye, target, fov, &up );
    // The framing tracks the members' live positions, which bob, headbang and strum: following
    // them exactly shakes the whole picture. Ease toward it instead (the aim a little quicker
    // than the dolly), and snap on a cut.
    if( index != m_framedCut || m_shotName != m_framedShot )
    {
        m_framedCut = index;
        m_framedShot = m_shotName;
        m_eye = eye;
        m_target = target;
        m_up = up;
        m_fov = fov;
    }
    else if( plan.Frame == Framing::Neck )
    {
        // The neck camera rides the guitar, which bobs with every beat: steadied like a
        // stabilised mount, following its swing in about a fifth of a second without the shake.
        const float dt = std::clamp( inDeltaTime, 0.f, 0.1f );
        const float follow = 1.f - std::exp( -dt * 5.f );
        m_eye = Lerp( m_eye, eye, follow );
        m_target = Lerp( m_target, target, follow );
        m_up = Lerp( m_up, up, follow ).Normalized();
        m_fov = fov;
    }
    else
    {
        const float dt = std::clamp( inDeltaTime, 0.f, 0.1f );
        m_eye = Lerp( m_eye, eye, 1.f - std::exp( -dt * 2.5f ) );
        m_target = Lerp( m_target, target, 1.f - std::exp( -dt * 4.f ) );
        m_up = up;
        m_fov += ( fov - m_fov ) * ( 1.f - std::exp( -dt * 4.f ) );
    }
    eye = m_eye;
    target = m_target;
    up = m_up;
    fov = m_fov;
    // Handheld shots sway on top of the eased framing, so the easing doesn't damp the sway.
    if( plan.Handheld )
    {
        const float t = static_cast<float>( inSeconds );
        eye = eye + Vector3( 0.03f * std::sin( t * 2.1f ) + 0.015f * std::sin( t * 5.3f ), 0.025f * std::sin( t * 2.7f + 1.f ), 0.02f * std::sin( t * 1.7f ) );
        target = target + Vector3( 0.05f * std::sin( t * 1.3f + 2.f ), 0.04f * std::sin( t * 1.9f ), 0.f );
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
    }
}
