#include "Venue/Band.h"
#include "Venue/People.generated.h"
#include "Venue/Puppet.h"
#include "Venue/VenueKit.h"
#include "Venue/VenueLayout.h"
#include "Venue/VenuePlan.h"
#include "Venue/VenueTiming.h"
#include "Components/Transform.h"
#include "Materials/StandardMaterial.h"
#include "Core/CommandLine.h"
#include "CLog.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <numeric>

namespace
{
    constexpr float kPi = 3.14159265f;
    constexpr float kDeg = kPi / 180.f;
    constexpr float kStickLength = 0.4f;
    // The grip: the hand holds the stick this far from its tip (a quarter up from the butt).
    constexpr float kStickReach = 0.3f;
    // How far a stick's tip is from its shoulder (level) before the drummer leans for it.
    constexpr float kComfort = 0.74f;
    // The drummer's hip joints, seated: on the throne (its top is at 0.58), sunk in a little.
    constexpr float kSeatHeight = 0.67f;
    // Where a guitar or bass hangs, from just above the hips: clear of the belly, the bass
    // further across so its longer neck stays in reach.
    const glm::vec3 kGuitarHang( 0.04f, 0.115f, 0.30f );
    const glm::vec3 kBassHang( 0.12f, 0.115f, 0.33f );
    // The singer's stand (the mic comes to their mouth), and where their hand holds it: under
    // the mic's clip.
    constexpr float kMicStandZ = 0.42f;
    constexpr float kMicStandHeight = 1.47f;
    const glm::vec3 kMicGrip( 0.f, kMicStandHeight - 0.05f, kMicStandZ );

    glm::quat Axis( float inDegrees, const glm::vec3& inAxis )
    {
        return glm::angleAxis( inDegrees * kDeg, inAxis );
    }

    const glm::vec3 kX( 1.f, 0.f, 0.f );
    const glm::vec3 kY( 0.f, 1.f, 0.f );
    const glm::vec3 kZ( 0.f, 0.f, 1.f );

    // A beat-locked pulse: 1 on the beat, easing to 0 over it.
    float Pulse( double inBeat, double inPower = 2.0 )
    {
        const double fraction = inBeat - std::floor( inBeat );
        return static_cast<float>( std::pow( 1.0 - fraction, inPower ) );
    }

    // The same pulse rising over the first 15% of the beat instead of jumping: for the stringed
    // players, whose guitar necks swing with it (and carry the neck camera).
    float SoftPulse( double inBeat )
    {
        constexpr double kRise = 0.15;
        const double fraction = inBeat - std::floor( inBeat );
        if( fraction < kRise )
        {
            const double t = fraction / kRise;
            return static_cast<float>( t * t * ( 3.0 - 2.0 * t ) );
        }
        const double fall = ( fraction - kRise ) / ( 1.0 - kRise );
        return static_cast<float>( ( 1.0 - fall ) * ( 1.0 - fall ) );
    }

    // Where each piece is struck, in the drummer's space (the throne at the origin, the kit at +z).
    const glm::vec3 kStrike[10] = {
        glm::vec3( 0.12f, 0.06f, 0.52f ),    // Kick (the pedal)
        glm::vec3( -0.44f, 0.98f, 0.56f ),   // HiHat
        glm::vec3( -0.16f, 0.74f, 0.6f ),    // Snare
        glm::vec3( -0.15f, 0.95f, 0.82f ),   // Tom1
        glm::vec3( 0.18f, 0.95f, 0.82f ),    // Tom2
        glm::vec3( 0.52f, 0.68f, 0.52f ),    // FloorTom
        glm::vec3( -0.6f, 1.28f, 0.86f ),    // Crash1
        glm::vec3( 0.55f, 1.32f, 0.92f ),    // Crash2
        glm::vec3( 0.72f, 1.06f, 0.66f ),    // Ride
        glm::vec3( -0.26f, 0.05f, 0.44f ),   // HiHatPedal
    };

    VenueData::DrumPiece PieceFor( PadId inPad )
    {
        using Piece = VenueData::DrumPiece;
        switch( inPad )
        {
        case PadId::Bass: return Piece::Kick;
        case PadId::HiHatPedal: return Piece::HiHatPedal;
        case PadId::ClosedHiHat:
        case PadId::OpenHiHat: return Piece::HiHat;
        case PadId::Snare: return Piece::Snare;
        case PadId::HighTom: return Piece::Tom1;
        case PadId::MidTom: return Piece::Tom2;
        case PadId::FloorTom: return Piece::FloorTom;
        case PadId::Crash1: return Piece::Crash1;
        case PadId::Ride: return Piece::Ride;
        default: return Piece::Crash2;
        }
    }

    // The shortest distance between two segments (a to b, c to d).
    float Between( const glm::vec3& inA, const glm::vec3& inB, const glm::vec3& inC, const glm::vec3& inD )
    {
        const glm::vec3 u = inB - inA;
        const glm::vec3 v = inD - inC;
        const glm::vec3 w = inA - inC;
        const float a = glm::dot( u, u );
        const float b = glm::dot( u, v );
        const float c = glm::dot( v, v );
        const float d = glm::dot( u, w );
        const float e = glm::dot( v, w );
        const float det = a * c - b * b;
        float s = det > 1e-8f ? std::clamp( ( b * e - c * d ) / det, 0.f, 1.f ) : 0.f;
        float t = c > 1e-8f ? std::clamp( ( b * s + e ) / c, 0.f, 1.f ) : 0.f;
        s = a > 1e-8f ? std::clamp( ( b * t - d ) / a, 0.f, 1.f ) : 0.f;
        return glm::length( w + u * s - v * t );
    }

    bool IsCymbal( VenueData::DrumPiece inPiece )
    {
        using Piece = VenueData::DrumPiece;
        return inPiece == Piece::HiHat || inPiece == Piece::Crash1 || inPiece == Piece::Crash2 || inPiece == Piece::Ride;
    }

    // Where a hand's stick lands on a piece, from kStrike: each hand has its own side of a head
    // (so the sticks of a roll don't share a spot), and the hi-hat is struck on its near edge,
    // toward the hand reaching for it, not on its bell.
    glm::vec3 HandSpot( VenueData::DrumPiece inPiece, int inHand )
    {
        using Piece = VenueData::DrumPiece;
        const float side = inHand == 0 ? -1.f : 1.f;
        switch( inPiece )
        {
        case Piece::HiHat: return inHand == 0 ? glm::vec3( 0.01f, 0.01f, -0.11f ) : glm::vec3( 0.1f, 0.01f, -0.07f );
        case Piece::Snare: return glm::vec3( side * 0.045f, 0.f, inHand == 0 ? -0.02f : 0.01f );
        case Piece::Tom1:
        case Piece::Tom2: return glm::vec3( side * 0.035f, 0.f, -0.02f );
        case Piece::FloorTom: return glm::vec3( side * 0.045f, 0.f, 0.f );
        case Piece::Crash1:
        case Piece::Crash2:
        case Piece::Ride:
        {
            // A cymbal is struck where the hand's shoulder is nearest it: on a crash's edge, on
            // the ride's bow. (kStrike has them at their near edge; their middles are behind.)
            const glm::vec3 point = kStrike[static_cast<int>( inPiece )];
            const bool ride = inPiece == Piece::Ride;
            const glm::vec3 middle( point.x, 0.f, point.z + ( ride ? 0.1f : 0.12f ) );
            const glm::vec3 shoulder( side * 0.19f, 0.f, 0.03f );
            return middle + glm::normalize( shoulder - middle ) * ( ride ? 0.11f : 0.19f ) - glm::vec3( point.x, 0.f, point.z );
        }
        default: return glm::vec3( 0.f );
        }
    }

    // Two pieces struck together: the one lower in this order takes the left hand. The kit from
    // left to right, except that the right hand crosses over to the hi-hat (a backbeat is the
    // left hand on the snare under the right on the hi-hat).
    float HandOrder( VenueData::DrumPiece inPiece )
    {
        using Piece = VenueData::DrumPiece;
        switch( inPiece )
        {
        case Piece::HiHat: return 0.05f;
        case Piece::Tom1: return -0.1f;
        default: return kStrike[static_cast<int>( inPiece )].x;
        }
    }
}


void Band::Clear()
{
    for( Member& member : m_members )
    {
        member = Member();
    }
    for( auto& strokes : m_strokes ) strokes.clear();
    m_strokeCursor = {};
    for( KitPiece& piece : m_kit ) piece = KitPiece();
    m_sections.clear();
    m_vocalNotes.clear();
    m_vocalPhrases.clear();
    m_singalong.clear();
    m_percussion.clear();
    m_percussionHits.clear();
    m_beats.clear();
    m_drumTimes.clear();
    m_stage = nullptr;
    m_lastSeconds = -1000.0;
    m_endTime = 1e9f;
}


void Band::Build( VenueKit& inKit, Transform* inStage, const VenuePlan& inPlan, const VenueData& inVenue, const std::vector<NoteData>& inNotes, const std::vector<BeatData>& inBeats, float inBpm )
{
    Clear();
    m_stage = inStage;
    m_beats = inBeats;
    m_bpm = inBpm;
    m_sections = inVenue.m_sections;
    m_vocalNotes = inVenue.m_vocalNotes;
    m_vocalPhrases = inVenue.m_vocalPhrases;
    m_singalong = inVenue.m_singalong;
    DerivePercussion( inVenue );
    for( const NoteData& note : inNotes )
    {
        m_drumTimes.push_back( note.m_triggerTime );
    }
    std::sort( m_drumTimes.begin(), m_drumTimes.end() );

    for( int index = 0; index < VenueData::MemberCount; ++index )
    {
        Member& member = m_members[index];
        member.States = inVenue.m_bandStates[index];
        member.Phase = VenueTiming::Noise( 17u, static_cast<uint32_t>( index ) ) * 6.f;
        member.Spot = inPlan.SpotOf( index ).Feet;
        member.Yaw = inPlan.SpotOf( index ).Yaw;
    }
    m_members[VenueData::Guitar].Strums = inVenue.m_guitarStrums;
    m_members[VenueData::Bass].Strums = inVenue.m_bassStrums;
    m_members[VenueData::Keys].Strums = inVenue.m_keysStrums;
    m_members[VenueData::Guitar].Frets = inVenue.m_guitarFrets;
    m_members[VenueData::Bass].Frets = inVenue.m_bassFrets;
    m_members[VenueData::Guitar].Maps = inVenue.m_guitarMaps;
    m_members[VenueData::Bass].Maps = inVenue.m_bassMaps;
    for( const TimedCueData& event : inVenue.m_songEvents )
    {
        if( event.m_name == "music_end" || event.m_name == "end" )
        {
            m_endTime = std::min( m_endTime, event.m_time );
        }
    }
    const bool keys = !inVenue.m_keysStrums.empty() || !inVenue.m_bandStates[VenueData::Keys].empty();

    // Strokes: the chart's drum animation notes, else worked out from its gems.
    for( const VenueData::DrumHitData& hit : inVenue.m_drumHits )
    {
        m_strokes[static_cast<int>( hit.m_limb )].push_back( Stroke{ hit.m_time, hit.m_piece, hit.m_soft } );
    }
    if( inVenue.m_drumHits.empty() )
    {
        DeriveStrokes( inNotes );
    }
    else
    {
        // Animation notes carry no pedals: the chart's kick and hi-hat pedal gems drive the feet.
        for( const NoteData& note : inNotes )
        {
            if( note.m_editorLane == PadId::HiHatPedal ) m_strokes[static_cast<int>( Limb::LeftFoot )].push_back( Stroke{ note.m_triggerTime, Piece::HiHatPedal, false } );
        }
        if( m_strokes[static_cast<int>( Limb::RightFoot )].empty() )
        {
            for( const NoteData& note : inNotes )
            {
                if( note.m_editorLane == PadId::Bass ) m_strokes[static_cast<int>( Limb::RightFoot )].push_back( Stroke{ note.m_triggerTime, Piece::Kick, false } );
            }
        }
    }
    int crashes[2] = { 0, 0 };
    for( auto& strokes : m_strokes )
    {
        std::stable_sort( strokes.begin(), strokes.end(), []( const Stroke& a, const Stroke& b ) { return a.Time < b.Time; } );
        for( const Stroke& stroke : strokes )
        {
            if( stroke.Target == Piece::Crash1 ) ++crashes[0];
            else if( stroke.Target == Piece::Crash2 ) ++crashes[1];
        }
    }
    if( CommandLine::Has( "--band-debug" ) )
    {
        BRUH_FMT( "Drummer strokes: %s, left hand %d, right hand %d, crashes left %d right %d", inVenue.m_drumHits.empty() ? "from the gems" : "animation notes",
            static_cast<int>( m_strokes[0].size() ), static_cast<int>( m_strokes[1].size() ), crashes[0], crashes[1] );
    }
    DeriveFallbacks( inNotes );

    for( int index = 0; index < VenueData::MemberCount; ++index )
    {
        if( ( index == VenueData::Keys && !keys ) || !inPlan.HasMember( index ) )
        {
            continue;
        }
        Member& member = m_members[index];
        member.Present = true;
        member.Group = inKit.Group( VenueData::MemberName( index ), inStage, member.Spot );
        if( !member.Group )
        {
            member.Present = false;
            continue;
        }
        Transform& group = member.Group->GetComponent<Transform>();
        // Everything a member has (their kit, instrument, mic stand) is built in their own frame,
        // their front +z: it turns with them.
        group.SetRotation( Vector3( 0.f, member.Yaw, 0.f ) );
        // Each a character of their own in an atlas of their own, a different cast every song
        // (the same every time it's played): a step through each list that visits all of it
        // before repeating.
        Performer::Look look;
        const uint32_t song = static_cast<uint32_t>( m_drumTimes.size() ) + static_cast<uint32_t>( m_bpm );
        const auto pick = [song, index]( uint32_t inCount, uint32_t inSalt ) {
            uint32_t step = 1 + ( song + inSalt ) % inCount;
            while( std::gcd( step, inCount ) != 1 ) ++step;
            return ( song + inSalt + static_cast<uint32_t>( index ) * step ) % inCount;
        };
        look.TexturePath = VenueKit::Skin( pick( VenueKit::SkinCount(), 0u ) );
        member.Model = static_cast<int>( pick( static_cast<uint32_t>( People::kCount ), 7u ) );
        look.ModelPath = People::kPeople[member.Model].Model;
        look.Mouth = Vector3( People::kPeople[member.Model].Mouth );
        member.Body.Build( inKit, &group, Vector3( 0.f, 0.f, 0.f ), 0.f, look );
        switch( index )
        {
        case VenueData::Drums: BuildDrums( inKit, member ); break;
        case VenueData::Guitar: BuildStringed( inKit, member, false ); break;
        case VenueData::Bass: BuildStringed( inKit, member, true ); break;
        case VenueData::Vocals: BuildVocals( inKit, member ); break;
        case VenueData::Keys: BuildKeys( inKit, member ); break;
        default: break;
        }
    }
    // Backing vocals from the harmony parts, once it's known who's on stage.
    DeriveHarmonies( inVenue );
}


std::vector<int> Band::SpareModels() const
{
    std::vector<int> spare;
    for( int model = 0; model < People::kCount; ++model )
    {
        const bool taken = std::any_of( m_members.begin(), m_members.end(), [model]( const Member& inMember ) { return inMember.Present && inMember.Model == model; } );
        if( !taken ) spare.push_back( model );
    }
    return spare;
}


void Band::DeriveStrokes( const std::vector<NoteData>& inNotes )
{
    // Hands from the chart's gems: of two struck together the one further left takes the left
    // hand (HandOrder); alone, cymbals and the right-hand toms take the right hand, the snare and
    // the left crash the left (both alternate in fast runs); the kick is the right foot and the hi-hat pedal the left.
    std::vector<const NoteData*> notes;
    for( const NoteData& note : inNotes ) notes.push_back( &note );
    std::stable_sort( notes.begin(), notes.end(), []( const NoteData* a, const NoteData* b ) { return a->m_triggerTime < b->m_triggerTime; } );
    std::vector<Piece> pieces;
    pieces.reserve( notes.size() );
    for( const NoteData* note : notes ) pieces.push_back( PieceFor( note->m_editorLane ) );
    ChooseCrashes( notes, pieces );

    float lastHand[2] = { -10.f, -10.f };
    Piece lastPiece[2] = { Piece::Snare, Piece::HiHat };
    for( size_t i = 0; i < notes.size(); )
    {
        const float time = notes[i]->m_triggerTime;
        std::vector<std::pair<Piece, bool>> hands;
        size_t j = i;
        for( ; j < notes.size() && notes[j]->m_triggerTime - time < 0.015f; ++j )
        {
            const Piece piece = pieces[j];
            const bool soft = notes[j]->m_velocity <= 40;
            if( piece == Piece::Kick ) m_strokes[static_cast<int>( Limb::RightFoot )].push_back( Stroke{ time, piece, soft } );
            else if( piece == Piece::HiHatPedal ) m_strokes[static_cast<int>( Limb::LeftFoot )].push_back( Stroke{ time, piece, soft } );
            else hands.push_back( { piece, soft } );
        }
        i = j;
        if( hands.empty() )
        {
            continue;
        }
        std::stable_sort( hands.begin(), hands.end(), []( const auto& a, const auto& b ) { return HandOrder( a.first ) < HandOrder( b.first ); } );
        int hand = 0;
        if( hands.size() >= 2 )
        {
            m_strokes[0].push_back( Stroke{ time, hands.front().first, hands.front().second } );
            m_strokes[1].push_back( Stroke{ time, hands.back().first, hands.back().second } );
            lastHand[0] = lastHand[1] = time;
            lastPiece[0] = hands.front().first;
            lastPiece[1] = hands.back().first;
            continue;
        }
        const Piece piece = hands.front().first;
        const bool fast0 = time - lastHand[0] < 0.14f;
        const bool fast1 = time - lastHand[1] < 0.14f;
        if( ( IsCymbal( piece ) && piece != Piece::Crash1 ) || piece == Piece::FloorTom || piece == Piece::Tom2 )
        {
            hand = fast1 && !fast0 ? 0 : 1;
        }
        else
        {
            hand = fast0 && !fast1 ? 1 : 0;
        }
        // A fill across the toms alternates.
        if( piece != Piece::Snare && !IsCymbal( piece ) && lastPiece[hand] != piece && time - lastHand[hand] < 0.2f && time - lastHand[1 - hand] > 0.05f )
        {
            hand = 1 - hand;
        }
        m_strokes[hand].push_back( Stroke{ time, piece, hands.front().second } );
        lastHand[hand] = time;
        lastPiece[hand] = piece;
    }
}


void Band::ChooseCrashes( const std::vector<const NoteData*>& inNotes, std::vector<Piece>& ioPieces ) const
{
    // A chart with one crash lane (a Rock Band green cymbal says "a crash", not which) has every
    // crash as Crash1. Pick a side for each from what's played around it, as a drummer would: the
    // crash beside the cymbal keeping time (the left one over the hi-hat, the right one by the
    // ride), the right one off the end of a fill down the toms; a run of crashes stays on one
    // cymbal, and with nothing else to go by the runs take turns. A chart that uses both lanes
    // has made its own choice.
    bool left = false;
    bool right = false;
    for( size_t i = 0; i < inNotes.size(); ++i )
    {
        left = left || inNotes[i]->m_editorLane == PadId::Crash1;
        right = right || inNotes[i]->m_editorLane == PadId::Crash2;
    }
    if( left == right )
    {
        return;
    }
    constexpr float kAround = 2.5f;    // the groove a crash belongs to
    constexpr float kRun = 0.7f;       // crashes this close are one run
    constexpr float kFill = 0.4f;      // a tom this soon before leads into the crash
    float lastCrash = -100.f;
    Piece lastSide = Piece::Crash2;
    size_t from = 0;
    for( size_t i = 0; i < inNotes.size(); ++i )
    {
        if( inNotes[i]->m_editorLane != PadId::Crash1 && inNotes[i]->m_editorLane != PadId::Crash2 )
        {
            continue;
        }
        const float time = inNotes[i]->m_triggerTime;
        Piece side = lastSide;
        if( time - lastCrash > kRun )
        {
            while( from < i && inNotes[from]->m_triggerTime < time - kAround ) ++from;
            int hats = 0;
            int rides = 0;
            Piece lead = Piece::Kick;
            for( size_t k = from; k < inNotes.size() && inNotes[k]->m_triggerTime < time + kAround; ++k )
            {
                const float at = inNotes[k]->m_triggerTime;
                if( ioPieces[k] == Piece::HiHat ) ++hats;
                else if( ioPieces[k] == Piece::Ride ) ++rides;
                if( at < time - 0.015f && at > time - kFill && ( ioPieces[k] == Piece::Tom1 || ioPieces[k] == Piece::Tom2 || ioPieces[k] == Piece::FloorTom ) )
                {
                    lead = ioPieces[k];
                }
            }
            if( lead == Piece::Tom2 || lead == Piece::FloorTom ) side = Piece::Crash2;
            else if( lead == Piece::Tom1 ) side = Piece::Crash1;
            else if( rides > hats ) side = Piece::Crash2;
            else if( hats > rides ) side = Piece::Crash1;
            else side = lastSide == Piece::Crash1 ? Piece::Crash2 : Piece::Crash1;
        }
        ioPieces[i] = side;
        lastSide = side;
        lastCrash = time;
    }
}


void Band::DeriveFallbacks( const std::vector<NoteData>& inNotes )
{
    // States from sections where the chart's PART tracks have none: intense choruses and solos,
    // gentle intros; the guitarist takes the solos.
    const auto stateFor = []( int inMember, const std::string& inSection ) {
        using VenueTiming::Contains;
        if( Contains( inSection, "solo" ) ) return std::string( inMember == VenueData::Guitar ? "play_solo" : "play" );
        if( Contains( inSection, "chorus" ) || Contains( inSection, "big" ) || Contains( inSection, "loud" ) ) return std::string( "intense" );
        if( Contains( inSection, "intro" ) || Contains( inSection, "quiet" ) || Contains( inSection, "spacey" ) ) return std::string( "mellow" );
        return std::string( "play" );
    };
    const float first = m_drumTimes.empty() ? 0.f : m_drumTimes.front();
    const float last = m_drumTimes.empty() ? 0.f : m_drumTimes.back();
    for( int index = 0; index < VenueData::MemberCount; ++index )
    {
        Member& member = m_members[index];
        if( !member.States.empty() )
        {
            continue;
        }
        member.States.push_back( { 0.f, "idle" } );
        if( m_sections.empty() )
        {
            member.States.push_back( { std::max( 0.f, first - 1.f ), "play" } );
        }
        for( const TimedCueData& section : m_sections )
        {
            member.States.push_back( { section.m_time, stateFor( index, section.m_name ) } );
        }
        member.States.push_back( { last + 1.5f, "idle" } );
    }

    // Strums on the half beat wherever the drums play, for charts without guitar or bass parts.
    for( int index : { VenueData::Guitar, VenueData::Bass } )
    {
        Member& member = m_members[index];
        if( !member.Strums.empty() || m_drumTimes.empty() )
        {
            continue;
        }
        const float beat = 60.f / std::max( 30.f, m_bpm );
        std::vector<float> beats;
        if( m_beats.size() >= 2 )
        {
            for( size_t i = 0; i + 1 < m_beats.size(); ++i )
            {
                beats.push_back( m_beats[i].m_time );
                beats.push_back( ( m_beats[i].m_time + m_beats[i + 1].m_time ) * 0.5f );
            }
        }
        else
        {
            for( float time = 0.f; time < last + 2.f; time += beat * 0.5f ) beats.push_back( time );
        }
        size_t cursor = 0;
        for( size_t i = 0; i < beats.size(); ++i )
        {
            const float time = beats[i];
            while( cursor < m_drumTimes.size() && m_drumTimes[cursor] < time - beat * 2.f ) ++cursor;
            const bool drumsPlaying = cursor < m_drumTimes.size() && m_drumTimes[cursor] < time + beat * 2.f;
            // The bass plays the beats, the guitar every half beat.
            const bool onBeat = index == VenueData::Guitar || i % 2 == 0;
            if( drumsPlaying && onBeat ) member.Strums.push_back( time );
        }
    }

    // The singer sings through the verses and choruses of charts without vocals: three beats on,
    // one off.
    if( m_vocalNotes.empty() && !m_drumTimes.empty() )
    {
        const auto sings = [this, first, last]( float inTime ) {
            if( inTime < first + 4.f || inTime > last - 2.f ) return false;
            const TimedCueData* section = VenueTiming::CueAt( m_sections, inTime );
            if( !section ) return m_sections.empty();
            return !VenueTiming::Contains( section->m_name, "solo" ) && !VenueTiming::Contains( section->m_name, "intro" ) && !VenueTiming::Contains( section->m_name, "outro" );
        };
        const float beat = 60.f / std::max( 30.f, m_bpm );
        for( size_t i = 0; i < m_beats.size(); ++i )
        {
            const float time = m_beats[i].m_time;
            if( i % 4 != 3 && sings( time ) && ( i / 16 ) % 2 == 0 )
            {
                m_vocalNotes.push_back( { time, time + beat * 0.8f, VenueData::Vocals } );
            }
        }
    }
}


void Band::BuildMicStand( VenueKit& inKit, Member& ioMember, const Vector3& inPosition, float inHeight )
{
    Transform& group = ioMember.Group->GetComponent<Transform>();
    ioMember.MicStand = inKit.Group( "MicStand", &group, inPosition );
    if( !ioMember.MicStand ) return;
    Transform& stand = ioMember.MicStand->GetComponent<Transform>();
    // Runtime OBJ compensates for the importer Z flip; the mic faces the performer (-Z).
    // Keep the floor pivot and horizontal dimensions; only adapt its height for backing vocals.
    EntityHandle model = inKit.Prop( "Assets/Models/Instruments/Runtime/MicStand.obj",
        Vector3( 0.f, 0.f, 0.f ), 1.f, 0.f, &stand );
    if( model ) model->GetComponent<Transform>().SetScale( Vector3( 1.f, inHeight / kMicStandHeight, 1.f ) );
}


void Band::BuildDrums( VenueKit& inKit, Member& ioMember )
{
    using Shape = Moonlight::MeshType;
    Transform& group = ioMember.Group->GetComponent<Transform>();
    inKit.Box( Vector3( 0.05f, 0.005f, 0.45f ), Vector3( 2.2f, 0.01f, 2.f ), Vector3( 0.25f, 0.04f, 0.04f ), &group );
    inKit.Prop( "Assets/Models/Instruments/Runtime/DrumHardware.obj", Vector3( 0.f, 0.f, 0.f ), 1.f, 0.f, &group );
    // Each exported piece has a local origin for hit squash / cymbal wobble. The hardware
    // stays stationary, and head centres remain on the same IK strike targets.
    const auto piece = [&]( Piece inPiece, const char* inName, const glm::vec3& inCentre, bool inCymbal ) {
        KitPiece& part = m_kit[static_cast<int>( inPiece )];
        const std::string path = std::string( "Assets/Models/Instruments/Runtime/" ) + inName + ".obj";
        part.Entity = inKit.Prop( path.c_str(), Vector3( inCentre ), 1.f, 0.f, &group );
        part.Cymbal = inCymbal;
        part.Rest = Vector3( 0.f, 0.f, 0.f );
        part.Scale = Vector3( 1.f, 1.f, 1.f );
    };
    piece( Piece::Kick, "Kick", glm::vec3( 0.f, 0.31f, 0.9f ), false );
    piece( Piece::Snare, "Snare", kStrike[2] - glm::vec3( 0.f, 0.069f, 0.f ), false );
    piece( Piece::Tom1, "Tom1", kStrike[3] - glm::vec3( 0.f, 0.104f, 0.f ), false );
    piece( Piece::Tom2, "Tom2", kStrike[4] - glm::vec3( 0.f, 0.114f, 0.f ), false );
    piece( Piece::FloorTom, "FloorTom", kStrike[5] - glm::vec3( 0.f, 0.214f, 0.f ), false );
    piece( Piece::HiHat, "HiHat", kStrike[1] - glm::vec3( 0.f, 0.01f, 0.f ), true );
    piece( Piece::Crash1, "Crash1", kStrike[6] - glm::vec3( 0.f, 0.02f, -0.12f ), true );
    piece( Piece::Crash2, "Crash2", kStrike[7] - glm::vec3( 0.f, 0.02f, -0.12f ), true );
    piece( Piece::Ride, "Ride", kStrike[8] - glm::vec3( 0.f, 0.02f, -0.1f ), true );
    for( int side = 0; side < 2; ++side )
    {
        ioMember.Sticks[side] = inKit.Piece( Shape::Cylinder, Vector3( 0.f, 0.f, 0.f ), Vector3( 0.02f, kStickLength, 0.02f ), Vector3( 0.85f, 0.7f, 0.45f ), &group );
    }
    // A backing vocal mic on a boom, off to the drummer's right.
    BuildMicStand( inKit, ioMember, Vector3( -0.75f, 0.f, 0.15f ), 1.12f );
    if( ioMember.MicStand ) ioMember.MicStand->GetComponent<Transform>().SetRotation( Vector3( 0.f, 60.f, 0.f ) );
}


void Band::BuildStringed( VenueKit& inKit, Member& ioMember, bool inBass )
{
    Transform& group = ioMember.Group->GetComponent<Transform>();
    ioMember.Instrument = inKit.Group( inBass ? "Bass" : "Guitar", &group );
    if( !ioMember.Instrument ) return;
    Transform& guitar = ioMember.Instrument->GetComponent<Transform>();
    // Authored to the same body origin, -X neck and +Z face as the hand/neck camera targets.
    ioMember.NeckLength = inBass ? 0.86f : 0.62f;
    inKit.Prop( inBass ? "Assets/Models/Instruments/Runtime/Bass.obj" : "Assets/Models/Instruments/Runtime/Guitar.obj",
        Vector3( 0.f, 0.f, 0.f ), 1.f, 0.f, &guitar );
    // An amp behind them.
    const float side = inBass ? 1.f : -1.f;
    inKit.Box( Vector3( side * 0.4f, 0.55f, -1.5f ), Vector3( 0.9f, 1.1f, 0.45f ), Vector3( 0.04f, 0.04f, 0.04f ), &group );
    inKit.Box( Vector3( side * 0.4f, 0.55f, -1.27f ), Vector3( 0.8f, 0.8f, 0.01f ), Vector3( 0.08f, 0.08f, 0.09f ), &group );
    inKit.Box( Vector3( side * 0.4f, 1.03f, -1.27f ), Vector3( 0.06f, 0.03f, 0.01f ), Vector3( 1.f, 0.1f, 0.05f ), &group, Vector3( 2.f, 0.2f, 0.1f ) );
    BuildMicStand( inKit, ioMember, Vector3( 0.f, 0.f, 0.55f ), 1.46f );
}


void Band::BuildVocals( VenueKit& inKit, Member& ioMember )
{
    BuildMicStand( inKit, ioMember, Vector3( 0.f, 0.f, kMicStandZ ), kMicStandHeight );
    // A pair of monitor wedges at the singer's feet.
    Transform& group = ioMember.Group->GetComponent<Transform>();
    // Percussion for the vocal part's tambourine and cowbell sections, hidden until played. In
    // its own space a tambourine's disc lies flat (y up), a cowbell's mouth points down -y.
    if( !m_percussion.empty() )
    {
        using Shape = Moonlight::MeshType;
        ioMember.Tambourine = inKit.Group( "Tambourine", &group );
        if( ioMember.Tambourine )
        {
            Transform& tambourine = ioMember.Tambourine->GetComponent<Transform>();
            inKit.Piece( Shape::Cylinder, Vector3( 0.f, 0.f, 0.f ), Vector3( 0.24f, 0.045f, 0.24f ), Vector3( 0.4f, 0.22f, 0.09f ), &tambourine );
            inKit.Piece( Shape::Cylinder, Vector3( 0.f, 0.012f, 0.f ), Vector3( 0.21f, 0.025f, 0.21f ), Vector3( 0.85f, 0.82f, 0.7f ), &tambourine );
            for( int jingle = 0; jingle < 5; ++jingle )
            {
                const float angle = 0.4f + 1.1f * static_cast<float>( jingle );
                inKit.Piece( Shape::Cylinder, Vector3( 0.12f * std::cos( angle ), 0.f, 0.12f * std::sin( angle ) ), Vector3( 0.045f, 0.012f, 0.045f ), Vector3( 0.8f, 0.78f, 0.72f ), &tambourine );
            }
            tambourine.SetScale( Vector3( 0.001f, 0.001f, 0.001f ) );
        }
        ioMember.Cowbell = inKit.Group( "Cowbell", &group );
        if( ioMember.Cowbell )
        {
            Transform& cowbell = ioMember.Cowbell->GetComponent<Transform>();
            inKit.Box( Vector3( 0.f, -0.06f, 0.f ), Vector3( 0.09f, 0.14f, 0.06f ), Vector3( 0.32f, 0.32f, 0.34f ), &cowbell );
            inKit.Box( Vector3( 0.f, 0.04f, 0.f ), Vector3( 0.03f, 0.08f, 0.03f ), Vector3( 0.1f, 0.1f, 0.1f ), &cowbell );
            cowbell.SetScale( Vector3( 0.001f, 0.001f, 0.001f ) );
        }
    }
    for( float x : { -0.6f, 0.6f } )
    {
        EntityHandle wedge = inKit.Box( Vector3( x, 0.18f, 1.15f ), Vector3( 0.6f, 0.34f, 0.45f ), Vector3( 0.04f, 0.04f, 0.04f ), &group );
        if( wedge ) wedge->GetComponent<Transform>().SetRotation( Vector3( 35.f, 0.f, 0.f ) );
    }
}


void Band::BuildKeys( VenueKit& inKit, Member& ioMember )
{
    Transform& group = ioMember.Group->GetComponent<Transform>();
    inKit.Prop( "Assets/Models/Instruments/Runtime/Keyboard.obj",
        Vector3( 0.f, 0.f, 0.f ), 1.f, 0.f, &group );
}


std::string Band::StateOf( int inMember, double inSeconds ) const
{
    if( inMember < 0 || inMember >= VenueData::MemberCount )
    {
        return "idle";
    }
    const TimedCueData* state = VenueTiming::CueAt( m_members[inMember].States, inSeconds );
    return state ? state->m_name : std::string( "idle" );
}


float Band::AtSingalong( int inMember, double inSeconds ) const
{
    // 1 through a member's singalong span, easing from and back to 0 over the 0.4 s around it.
    constexpr float kEase = 0.4f;
    const float t = static_cast<float>( inSeconds );
    auto it = std::upper_bound( m_singalong.begin(), m_singalong.end(), t + kEase, []( float time, const VenueData::SpanData& s ) { return time < s.m_start; } );
    float nearest = kEase;
    while( it != m_singalong.begin() )
    {
        --it;
        if( t - it->m_start > 30.f )
        {
            break;
        }
        if( it->m_member == inMember )
        {
            nearest = std::min( nearest, std::max( { 0.f, it->m_start - t, t - it->m_end } ) );
        }
    }
    return 1.f - VenueTiming::Smooth( nearest / kEase );
}


bool Band::Singing( int inMember, double inSeconds, float* outOpen ) const
{
    const auto& spans = inMember == VenueData::Vocals ? m_vocalNotes : m_singalong;
    auto it = std::upper_bound( spans.begin(), spans.end(), static_cast<float>( inSeconds ), []( float t, const VenueData::SpanData& s ) { return t < s.m_start; } );
    while( it != spans.begin() )
    {
        --it;
        if( inMember != VenueData::Vocals && it->m_member != inMember )
        {
            continue;
        }
        if( inSeconds <= it->m_end )
        {
            if( outOpen )
            {
                // Open on the note's attack, then a wobble through it.
                const float age = static_cast<float>( inSeconds - it->m_start );
                *outOpen = std::clamp( 0.45f + 0.45f * std::exp( -age * 6.f ) + 0.15f * std::sin( age * 19.f ), 0.f, 1.f );
            }
            return true;
        }
        if( inMember == VenueData::Vocals || inSeconds - it->m_end > 30.f )
        {
            break;
        }
    }
    if( outOpen ) *outOpen = 0.f;
    return false;
}


float Band::Activity( int inMember, double inSeconds ) const
{
    if( !HasMember( inMember ) )
    {
        return 0.f;
    }
    const auto count = []( const std::vector<float>& inTimes, double inFrom, double inTo ) {
        return static_cast<float>( VenueTiming::After( inTimes, inTo ) - VenueTiming::After( inTimes, inFrom ) );
    };
    switch( inMember )
    {
    case VenueData::Drums: return std::min( 1.f, count( m_drumTimes, inSeconds - 1.0, inSeconds + 1.0 ) / 14.f );
    case VenueData::Vocals: return Singing( inMember, inSeconds ) || Singing( inMember, inSeconds + 0.5 ) || Singing( inMember, inSeconds - 0.5 ) ? 1.f : 0.f;
    default: return std::min( 1.f, count( m_members[inMember].Strums, inSeconds - 1.0, inSeconds + 1.0 ) / 8.f );
    }
}


glm::vec3 Band::StrikePoint( Piece inPiece, int inHand ) const
{
    const glm::vec3 point = kStrike[static_cast<int>( inPiece )];
    return inHand == 0 || inHand == 1 ? point + HandSpot( inPiece, inHand ) : point;
}


glm::vec3 Band::StickTip( int inLimb, double inSeconds, float& outLift ) const
{
    // A stroke at a time: the tip bounces off the last piece to a ready height, crosses to the
    // next piece early and waits over it, then winds up and whips down onto the note. The time
    // between the two sets how high it can go; a crash gets a bigger swing, a ghost note a
    // small one. outLift is the tip's height over the pieces (the returned point less it lies
    // on them): the hand rises by a part of it and the wrist does the rest.
    constexpr float kReady = 0.09f;      // the tip's height over a piece, waiting
    constexpr float kRebound = 0.1f;     // seconds up off the head
    constexpr float kSwing = 0.28f;      // seconds of wind-up and downstroke
    constexpr float kIdle = 2.5f;        // a longer gap goes by way of the rest
    constexpr float kLeadIn = 0.7f;      // from the rest to a note
    const auto& strokes = m_strokes[inLimb];
    const float t = static_cast<float>( inSeconds );
    auto it = std::upper_bound( strokes.begin(), strokes.end(), t, []( float inTime, const Stroke& s ) { return inTime < s.Time; } );
    const Stroke* next = it != strokes.end() ? &*it : nullptr;
    const Stroke* prev = it != strokes.begin() ? &*( it - 1 ) : nullptr;
    // At rest the sticks hover side by side over the snare.
    const glm::vec3 rest = StrikePoint( Piece::Snare, inLimb ) + glm::vec3( inLimb == 0 ? -0.04f : 0.07f, 0.f, -0.06f );

    glm::vec3 from = prev ? StrikePoint( prev->Target, inLimb ) : rest;
    float fromTime = prev ? prev->Time : -1000.f;
    bool bounced = prev != nullptr;
    if( next && next->Time - fromTime > kIdle && next->Time - t < kLeadIn )
    {
        from = rest;
        fromTime = next->Time - kLeadIn;
        bounced = false;
    }
    else if( !next || next->Time - fromTime > kIdle )
    {
        // Nothing to play for a while: off the last piece and back to the rest.
        const float since = t - fromTime;
        outLift = kReady * std::sin( std::clamp( since / kRebound, 0.f, 1.f ) * kPi * 0.5f );
        glm::vec3 tip = glm::mix( from, rest, VenueTiming::Smooth( ( since - 0.05f ) / 0.45f ) );
        tip.y += outLift;
        return tip;
    }

    const glm::vec3 to = StrikePoint( next->Target, inLimb );
    const float gap = std::max( 0.03f, next->Time - fromTime );
    const bool accent = next->Target == Piece::Crash1 || next->Target == Piece::Crash2;
    const float height = std::clamp( gap * 0.6f, 0.04f, accent ? 0.38f : 0.26f ) * ( next->Soft ? 0.45f : 1.f );
    const float ready = std::min( kReady, height * 0.6f );
    const float rebound = std::min( kRebound, gap * 0.25f );
    const float swing = std::min( kSwing, gap * 0.55f );
    const float since = t - fromTime;
    const float until = next->Time - t;
    if( until < swing )
    {
        // Up for the first part, then down faster and faster: it lands moving.
        const float w = 1.f - until / swing;
        constexpr float kTop = 0.55f;
        const float fall = ( w - kTop ) / ( 1.f - kTop );
        outLift = w < kTop ? ready + ( height - ready ) * VenueTiming::Smooth( w / kTop ) : height * ( 1.f - fall * fall );
    }
    else
    {
        outLift = bounced ? ready * std::sin( std::clamp( since / rebound, 0.f, 1.f ) * kPi * 0.5f ) : ready;
    }
    // Across as soon as it's off the head, there before the downstroke.
    const float start = rebound * 0.3f;
    const float arrive = gap - swing * 0.4f;
    const float travel = 0.12f + 0.45f * glm::length( to - from );
    glm::vec3 tip = glm::mix( from, to, VenueTiming::Smooth( ( since - start ) / std::max( 0.02f, std::min( arrive - start, travel ) ) ) );
    tip.y += outLift;
    return tip;
}


float Band::StrumPhase( const Member& inMember, double inSeconds, int& outCount ) const
{
    // -1 .. 1: the strumming hand's place, down on even strums and up on odd ones.
    const size_t after = VenueTiming::After( inMember.Strums, inSeconds );
    outCount = static_cast<int>( after );
    if( after == 0 )
    {
        return 0.f;
    }
    const float since = static_cast<float>( inSeconds ) - inMember.Strums[after - 1];
    if( since > 0.6f )
    {
        return 0.f;
    }
    const float stroke = VenueTiming::Smooth( since / 0.07f );
    const float from = ( after % 2 == 1 ) ? 1.f : -1.f;
    const float settle = std::exp( -std::max( 0.f, since - 0.25f ) * 6.f );
    return ( from - 2.f * from * stroke ) * settle;
}


void Band::UpdateDrums( Member& ioMember, double inSeconds, double inBeat, float inEnergy, float inDeltaTime )
{
    Performer::Pose& pose = ioMember.Pose;
    pose = Performer::Pose();
    pose.Seated = true;
    pose.SeatHeight = kSeatHeight;
    const std::string state = StateOf( VenueData::Drums, inSeconds );
    const bool intense = VenueTiming::Contains( state, "intense" );
    const bool idle = state == "idle" || state == "idle_realtime";
    const float pulse = Pulse( inBeat );
    pose.Lean = 12.f + ( intense ? 8.f * pulse : 2.f * pulse );
    pose.Nod = idle ? 4.f * std::sin( static_cast<float>( inSeconds ) * 0.7f + ioMember.Phase ) : ( intense ? 26.f : 9.f ) * pulse - 4.f;
    pose.HeadTurn = idle ? 20.f * std::sin( static_cast<float>( inSeconds ) * 0.31f + ioMember.Phase ) : 0.f;
    float open = 0.f;
    if( Singing( VenueData::Drums, inSeconds, &open ) )
    {
        pose.Mouth = open;
        pose.HeadTurn = -35.f;    // toward the mic, on their left
        pose.Nod = -4.f;
    }

    // Hands: the stick tips follow the strokes; the hand sits a stick's length behind each tip.
    float lift[2] = { 0.f, 0.f };
    glm::vec3 tips[2];
    for( int side = 0; side < 2; ++side )
    {
        tips[side] = StickTip( side, inSeconds, lift[side] );
    }
    // The body goes with the hands across the kit: turned and tipped toward where they are, and
    // leaning in for what's far away (a crash). Where they are is averaged from a little behind
    // now to a little ahead, so the body moves smoothly and leads the sticks slightly.
    glm::vec3 reach( 0.f );
    glm::vec3 stretch( 0.f );
    float twist = 0.f;
    constexpr int kSamples = 6;
    for( int sample = 0; sample < kSamples; ++sample )
    {
        const double at = inSeconds - 0.12 + 0.08 * sample;
        for( int side = 0; side < 2; ++side )
        {
            float unused = 0.f;
            const glm::vec3 tip = StickTip( side, at, unused );
            reach += tip;
            // Further than the arm and stick go from a shoulder sitting square: the body makes
            // up the difference, toward the piece.
            const float outward = side == 0 ? -1.f : 1.f;
            const glm::vec3 away( tip.x - outward * 0.19f, 0.f, tip.z - 0.03f );
            const float distance = glm::length( away );
            if( distance > kComfort )
            {
                stretch += away * ( ( distance - kComfort ) / distance );
                twist += ( distance - kComfort ) * ( outward * away.x < 0.f ? outward : 0.f );
            }
        }
    }
    reach /= static_cast<float>( kSamples * 2 );
    stretch /= static_cast<float>( kSamples );
    twist /= static_cast<float>( kSamples );
    // (A turn is positive toward the figure's right, +x.)
    pose.Turn = std::clamp( reach.x * 30.f - twist * 55.f, -38.f, 38.f );
    pose.Side = std::clamp( reach.x * 10.f + stretch.x * 30.f, -13.f, 13.f );
    pose.Lean = std::min( pose.Lean + stretch.z * 38.f, 25.f );
    // Leaning in, the head stays up: they're looking at what they're reaching for.
    pose.Nod *= 1.f - std::clamp( glm::length( stretch ) / 0.2f, 0.f, 0.7f );
    if( !idle && pose.Mouth <= 0.f )
    {
        // Eyes on the kit, toward the hands (unless they're at the mic).
        pose.HeadTurn = std::clamp( reach.x * 30.f, -25.f, 25.f );
    }
    // A kick rocks the shoulders.
    {
        const auto& kicks = m_strokes[static_cast<int>( Limb::RightFoot )];
        auto it = std::upper_bound( kicks.begin(), kicks.end(), static_cast<float>( inSeconds ), []( float t, const Stroke& s ) { return t < s.Time; } );
        if( it != kicks.begin() )
        {
            pose.Lean += 2.5f * std::exp( -( static_cast<float>( inSeconds ) - ( it - 1 )->Time ) / 0.12f );
        }
    }
    // Feet: on the kick and hi-hat pedals, the ball of the foot over each one's middle.
    for( int side = 0; side < 2; ++side )
    {
        const glm::vec3 pedal = StrikePoint( side == 0 ? Piece::HiHatPedal : Piece::Kick );
        pose.Legs[side].Reach = true;
        pose.Legs[side].Target = pedal + glm::vec3( 0.f, 0.015f, -0.05f );
        pose.Legs[side].Pole = glm::vec3( side == 0 ? -0.25f : 0.1f, 0.5f, 1.f );
    }
    const auto footFor = [&]( Limb inLimb, float inHold ) {
        const auto& strokes = m_strokes[static_cast<int>( inLimb )];
        auto it = std::upper_bound( strokes.begin(), strokes.end(), static_cast<float>( inSeconds ), []( float t, const Stroke& s ) { return t < s.Time; } );
        float toe = inHold;
        if( it != strokes.begin() )
        {
            const float since = static_cast<float>( inSeconds ) - ( it - 1 )->Time;
            toe = std::max( toe, 24.f * std::exp( -since / 0.07f ) );
        }
        if( it != strokes.end() )
        {
            const float until = it->Time - static_cast<float>( inSeconds );
            if( until < 0.08f ) toe = std::max( toe, -10.f * ( 1.f - until / 0.08f ) );
        }
        return toe;
    };
    pose.Legs[1].Toe = footFor( Limb::RightFoot, 0.f );
    // With no pedal part of its own the hi-hat foot keeps time, heel bouncing on the beat.
    pose.Legs[0].Toe = footFor( Limb::LeftFoot, m_strokes[static_cast<int>( Limb::LeftFoot )].empty() ? ( idle ? 8.f : 6.f + 9.f * pulse ) : 4.f );
    // The body first: the arms reach from wherever it puts the chest.
    ioMember.Body.Stand( pose );
    // Each stick points away from its own shoulder, pivoting in the hand: the hand goes up by a
    // part of the tip's lift and the wrist cocks the stick back for the rest. A hand reaching
    // across the body (the right, to the hi-hat) comes at its piece from further forward, so it
    // passes ahead of the other hand, not through it.
    constexpr float kGripRise = 0.1f;     // the hand above the tip as it lands
    constexpr float kArm = 0.6f;          // as far from the shoulder as the palm goes
    constexpr float kHandLift = 0.22f;    // of the tip's lift
    const glm::vec3 chest = ioMember.Body.Chest();
    const glm::quat spine = ioMember.Body.SpineRotation();
    glm::vec3 toward[2];
    float handHeight[2];
    const auto handAt = [&]( int inSide ) {
        const float sine = std::clamp( ( handHeight[inSide] - tips[inSide].y ) / kStickReach, -0.85f, 0.8f );
        const glm::vec3 stick = toward[inSide] * std::sqrt( 1.f - sine * sine ) - kY * sine;
        glm::vec3 hand = tips[inSide] - stick * kStickReach;
        // Out of the arm's reach: bring the hand in toward the line from the shoulder to the
        // tip, where it's nearest.
        const glm::vec3 shoulder = ioMember.Body.Shoulder( inSide );
        const float over = VenueTiming::Smooth( ( glm::length( hand - shoulder ) - ( kArm - 0.08f ) ) / 0.1f );
        if( over > 0.f )
        {
            const glm::vec3 direct = tips[inSide] - glm::normalize( tips[inSide] - shoulder ) * kStickReach;
            hand = tips[inSide] + glm::normalize( glm::mix( hand, direct, over ) - tips[inSide] ) * kStickReach;
        }
        return hand;
    };
    for( int side = 0; side < 2; ++side )
    {
        const float outward = side == 0 ? -1.f : 1.f;
        const float across = std::max( 0.f, -outward * tips[side].x - 0.05f );
        glm::vec3 origin = chest + spine * glm::vec3( outward * 0.16f, 0.f, 0.f );
        origin.z += 0.05f + across * 0.9f;
        glm::vec3 away = tips[side] - origin;
        away.y = 0.f;
        toward[side] = glm::dot( away, away ) > 1e-6f ? glm::normalize( away ) : kZ;
        // No higher than the arm can hold it: a high cymbal is struck from below its edge.
        handHeight[side] = std::min( tips[side].y - lift[side] + kGripRise, chest.y + 0.12f ) + kHandLift * lift[side];
    }
    // One hand over the other (a backbeat under the hi-hat hand): keep the upper one clear.
    {
        const glm::vec3 hands[2] = { handAt( 0 ), handAt( 1 ) };
        const int upper = hands[0].y > hands[1].y ? 0 : 1;
        const glm::vec3 apart = hands[upper] - hands[1 - upper];
        const float level = std::sqrt( apart.x * apart.x + apart.z * apart.z );
        const float needed = 0.19f * ( 1.f - VenueTiming::Smooth( ( level - 0.12f ) / 0.1f ) );
        if( apart.y < needed )
        {
            handHeight[upper] += needed - apart.y;
        }
    }
    for( int side = 0; side < 2; ++side )
    {
        const glm::vec3 hand = handAt( side );
        const glm::vec3 stick = glm::normalize( tips[side] - hand );
        Performer::Arm& arm = pose.Arms[side];
        arm.Reach = true;
        arm.Target = hand;
        arm.Pole = spine * glm::vec3( side == 0 ? -1.f : 1.f, -0.45f, 0.65f );
        arm.ClearTorso = true;
        // Palm down, the stick running across it: the fingers point a little outside the stick.
        arm.Fingers = Axis( side == 0 ? -30.f : 30.f, kY ) * stick;
        arm.Palm = -kY;
        arm.Grip = 0.85f;
    }
    ioMember.Body.Apply( pose );
    static const bool kDebug = CommandLine::Has( "--band-debug" );
    if( kDebug )
    {
        // How near one arm (forearm and stick) comes to the other.
        float apart = 10.f;
        int nearest = 0;
        glm::vec3 chain[2][3];
        for( int side = 0; side < 2; ++side )
        {
            chain[side][0] = ioMember.Body.Elbow( side );
            chain[side][1] = ioMember.Body.Hand( side );
            chain[side][2] = tips[side];
        }
        for( int i = 0; i < 2; ++i )
        {
            for( int j = 0; j < 2; ++j )
            {
                const float gap = Between( chain[0][i], chain[0][i + 1], chain[1][j], chain[1][j + 1] );
                if( gap < apart )
                {
                    apart = gap;
                    nearest = i * 2 + j;
                }
            }
        }
        if( apart < 0.09f )
        {
            static const char* const kPairs[] = { "forearms", "left forearm, right stick", "left stick, right forearm", "sticks" };
            BRUH_FMT( "Drummer arms %.3f apart at t=%.2f (%s)", apart, inSeconds, kPairs[nearest] );
        }
        // Twice a second, and whenever a hand falls short of where its stick needs it.
        const bool tick = static_cast<int>( inSeconds * 2.0 ) != static_cast<int>( m_lastSeconds * 2.0 );
        for( int side = 0; side < 2; ++side )
        {
            const glm::vec3 h = ioMember.Body.Hand( side );
            const glm::vec3 s = ioMember.Body.Shoulder( side );
            if( !tick && glm::length( h - pose.Arms[side].Target ) < 0.03f )
            {
                continue;
            }
            BRUH_FMT( "Drummer %d t=%.2f tip(%.2f %.2f %.2f) target(%.2f %.2f %.2f) hand(%.2f %.2f %.2f) shoulder(%.2f %.2f %.2f) lift %.2f lean %.0f side %.0f turn %.0f short %.3f", side, inSeconds,
                tips[side].x, tips[side].y, tips[side].z, pose.Arms[side].Target.x, pose.Arms[side].Target.y, pose.Arms[side].Target.z, h.x, h.y, h.z, s.x, s.y, s.z, lift[side], pose.Lean, pose.Side, pose.Turn,
                glm::length( h - pose.Arms[side].Target ) );
        }
    }
    for( int side = 0; side < 2; ++side )
    {
        if( ioMember.Sticks[side] )
        {
            const glm::vec3 hand = ioMember.Body.Hand( side );
            const glm::vec3 along = glm::normalize( tips[side] - hand );
            // At full stretch the stick slides through the fingers a little to make the distance.
            const float held = std::clamp( glm::length( tips[side] - hand ), kStickReach, kStickLength - 0.03f );
            Puppet::PlaceBone( ioMember.Sticks[side], hand - along * ( kStickLength - held ), hand + along * held );
        }
    }

    // Kit reactions as strokes land.
    for( int limb = 0; limb < 4; ++limb )
    {
        const auto& strokes = m_strokes[limb];
        size_t& cursor = m_strokeCursor[limb];
        if( inSeconds < m_lastSeconds - 0.5 )
        {
            cursor = 0;
        }
        while( cursor < strokes.size() && strokes[cursor].Time <= inSeconds )
        {
            if( inSeconds - strokes[cursor].Time < 0.25 )
            {
                KitPiece& piece = m_kit[static_cast<int>( strokes[cursor].Target == Piece::HiHatPedal ? Piece::HiHat : strokes[cursor].Target )];
                piece.Wobble = std::max( piece.Wobble, strokes[cursor].Soft ? 0.45f : 1.f );
            }
            ++cursor;
        }
    }
    UpdateKit( inDeltaTime );
    (void)inEnergy;
}


void Band::UpdateKit( float inDeltaTime )
{
    for( int i = 0; i < static_cast<int>( m_kit.size() ); ++i )
    {
        KitPiece& piece = m_kit[i];
        if( !piece.Entity )
        {
            continue;
        }
        Transform& transform = piece.Entity->GetComponent<Transform>();
        if( piece.Cymbal )
        {
            // A struck cymbal rocks on its stand.
            piece.Wobble *= std::exp( -inDeltaTime * 2.2f );
            const float swing = piece.Wobble * 9.f * std::sin( static_cast<float>( m_lastSeconds ) * 16.f + i );
            transform.SetRotation( piece.Rest + Vector3( swing, 0.f, swing * 0.6f ) );
        }
        else if( i != static_cast<int>( Piece::Kick ) )
        {
            piece.Wobble *= std::exp( -inDeltaTime * 18.f );
            transform.SetScale( Vector3( 1.f + 0.04f * piece.Wobble, 1.f - 0.08f * piece.Wobble, 1.f + 0.04f * piece.Wobble ) );
        }
        else
        {
            piece.Wobble *= std::exp( -inDeltaTime * 14.f );
            transform.SetScale( Vector3( 1.f + 0.05f * piece.Wobble, 1.f, 1.f + 0.05f * piece.Wobble ) );
        }
    }
}


void Band::SwingInstrument( Member& ioMember, const glm::vec3& inOffset, glm::vec3& ioPosition, glm::quat& ioRotation, float inDeltaTime )
{
    // Follow the torso promptly, with some strap swing rather than filtering out the beat.
    // The neck camera rides this transform, so excessive lag makes its movement feel detached.
    constexpr float kHoldRate = 14.f;
    constexpr float kHoldDamping = 0.75f;
    constexpr float kSwayRate = 10.f;
    constexpr float kSwayDamping = 0.65f;
    const glm::vec3 at = ioPosition - inOffset;
    if( !ioMember.GuitarHung )
    {
        ioMember.GuitarAt = at;
        ioMember.GuitarVelocity = glm::vec3( 0.f );
        ioMember.GuitarTilt = ioRotation;
        ioMember.GuitarSpin = glm::vec3( 0.f );
        ioMember.GuitarHung = true;
    }
    else
    {
        // Small fixed steps, so the springs behave the same at any frame rate (and through the
        // venue's stepped clock).
        const float dt = std::clamp( inDeltaTime, 0.f, 0.1f );
        const int steps = std::max( 1, static_cast<int>( std::ceil( dt * 240.f ) ) );
        const float h = dt / static_cast<float>( steps );
        for( int i = 0; i < steps; ++i )
        {
            ioMember.GuitarVelocity += ( ( at - ioMember.GuitarAt ) * ( kHoldRate * kHoldRate ) - ioMember.GuitarVelocity * ( 2.f * kHoldDamping * kHoldRate ) ) * h;
            ioMember.GuitarAt += ioMember.GuitarVelocity * h;
            // The tilt still to go, as an axis times an angle (the short way round).
            glm::quat error = ioRotation * glm::conjugate( ioMember.GuitarTilt );
            if( error.w < 0.f ) error = -error;
            const glm::vec3 axis( error.x, error.y, error.z );
            const float sine = glm::length( axis );
            const glm::vec3 togo = sine > 1e-6f ? axis * ( 2.f * std::atan2( sine, error.w ) / sine ) : axis * 2.f;
            ioMember.GuitarSpin += ( togo * ( kSwayRate * kSwayRate ) - ioMember.GuitarSpin * ( 2.f * kSwayDamping * kSwayRate ) ) * h;
            const float turn = glm::length( ioMember.GuitarSpin ) * h;
            if( turn > 1e-7f )
            {
                ioMember.GuitarTilt = glm::normalize( glm::angleAxis( turn, ioMember.GuitarSpin / ( turn / h ) ) * ioMember.GuitarTilt );
            }
        }
    }
    ioPosition = ioMember.GuitarAt + inOffset;
    ioRotation = ioMember.GuitarTilt;
    Puppet::PlacePiece( ioMember.Instrument, ioPosition, ioRotation );
}


void Band::UpdateStringed( Member& ioMember, int inIndex, double inSeconds, double inBeat, float inEnergy, float inDeltaTime )
{
    Performer::Pose& pose = ioMember.Pose;
    pose = Performer::Pose();
    const std::string state = StateOf( inIndex, inSeconds );
    const bool intense = VenueTiming::Contains( state, "intense" );
    const bool mellow = state == "mellow";
    const bool idle = state == "idle" || state == "idle_realtime";
    const float soloing = ioMember.Solo;
    const float t = static_cast<float>( inSeconds );
    const float pulse = SoftPulse( inBeat );
    ioMember.Energy += ( ( intense ? 1.f : idle ? 0.1f : mellow ? 0.3f : 0.6f ) - ioMember.Energy ) * 0.05f;
    const float energy = ioMember.Energy;
    pose.Legs[0].Spread = 5.f + 9.f * energy;
    pose.Legs[1].Spread = 5.f + 9.f * energy;
    pose.Crouch = 0.03f * pulse * energy + 0.06f * energy;
    pose.Lean = 6.f + 10.f * energy * pulse;
    pose.Nod = ( idle ? 3.f : 8.f + 26.f * energy * energy ) * pulse - 5.f;
    pose.Side = mellow ? 5.f * std::sin( static_cast<float>( inBeat ) * kPi * 0.5f ) : 0.f;
    pose.HeadTurn = idle ? 25.f * std::sin( t * 0.4f + ioMember.Phase ) : 6.f * std::sin( t * 0.9f + ioMember.Phase );
    pose.Turn = inIndex == VenueData::Guitar ? -8.f : 8.f;
    if( soloing > 0.f )
    {
        // Out front and leaning back into it, walked into over a moment.
        pose.Lean += ( -8.f + 4.f * pulse - pose.Lean ) * soloing;
        pose.Offset = glm::vec3( inIndex == VenueData::Guitar ? -0.3f : 0.3f, 0.f, 1.1f ) * soloing;
        pose.Nod += ( -12.f + 10.f * pulse - pose.Nod ) * soloing;
    }
    float open = 0.f;
    if( Singing( inIndex, inSeconds, &open ) )
    {
        pose.Mouth = open;
    }
    // Leaning into their mic for a singalong, eased in and out around it. Not mid-solo: the
    // soloist is out front.
    const float atMic = AtSingalong( inIndex, inSeconds ) * ( 1.f - soloing );
    if( atMic > 0.f )
    {
        pose.Lean += ( 10.f - pose.Lean ) * atMic;
        pose.Nod += ( -6.f - pose.Nod ) * atMic;
        pose.Offset += ( glm::vec3( 0.f, 0.f, 0.12f ) - pose.Offset ) * atMic;
        pose.Turn *= 1.f - atMic;
    }
    ioMember.Body.Stand( pose );

    // The guitar hangs off the torso, its neck up and to the player's left.
    const glm::quat spine = ioMember.Body.SpineRotation();
    const float neckAngle = -24.f - 10.f * energy * pulse * ( 1.f - soloing ) - 24.f * soloing;
    // Damped (SwingInstrument): the hands below reach for where the guitar is, not where the
    // torso would hold it, so they stay on the strings and the neck camera rides it steadily.
    glm::quat guitarRotation = spine * Axis( neckAngle, kZ ) * Axis( 14.f, kY ) * Axis( -12.f, kX );
    glm::vec3 guitarPosition = ioMember.Body.SpineBase() + spine * ( inIndex == VenueData::Bass ? kBassHang : kGuitarHang );
    if( ioMember.Instrument )
    {
        SwingInstrument( ioMember, pose.Offset, guitarPosition, guitarRotation, inDeltaTime );
    }
    int count = 0;
    const float strum = idle ? 0.f : StrumPhase( ioMember, inSeconds, count );
    // The chart's hand positions (notes 40-59) when it has them, else a new spot every few strums.
    float fret = VenueTiming::Noise( static_cast<uint32_t>( count / 6 ), static_cast<uint32_t>( inIndex ) );
    if( !ioMember.Frets.empty() )
    {
        auto it = std::upper_bound( ioMember.Frets.begin(), ioMember.Frets.end(), static_cast<float>( inSeconds ), []( float t, const VenueData::SpanData& s ) { return t < s.m_start; } );
        if( it != ioMember.Frets.begin() )
        {
            fret = static_cast<float>( ( it - 1 )->m_member ) / 19.f;
        }
    }
    // The chart's hand and strum maps ("[map HandMap_Chord_A]", "[map StrumMap_SlapBass]"): a
    // fixed chord shape near the nut, chords throughout, single notes, open strings, a solo's
    // runs; slapping over the neck pickup.
    const auto mapOf = [&ioMember, inSeconds]( const char* inPrefix ) -> std::string {
        size_t index = 0;
        if( !VenueTiming::CueAt( ioMember.Maps, inSeconds, &index ) ) return std::string();
        for( size_t i = index + 1; i-- > 0; )
        {
            if( ioMember.Maps[i].m_name.rfind( inPrefix, 0 ) == 0 ) return ioMember.Maps[i].m_name.substr( std::strlen( inPrefix ) );
        }
        return std::string();
    };
    const std::string hand = mapOf( "HandMap_" );
    const bool slap = mapOf( "StrumMap_" ) == "SlapBass";
    float wrap = 0.f;     // a chord shape: the hand wraps further round the neck
    float lift = 0.f;     // open strings: the hand comes off the fretboard as they're struck
    if( hand.rfind( "Chord_", 0 ) == 0 && hand.size() > 6 )
    {
        // Open chord shapes sit in the first few frets.
        const char root = hand[6];
        fret = ( root == 'E' ? 1.f : root == 'C' || root == 'F' ? 2.f : 2.5f ) / 19.f;
        wrap = 1.f;
    }
    else if( hand == "AllChords" )
    {
        wrap = 1.f;
    }
    else if( hand == "NoChords" )
    {
        fret = std::clamp( fret + 0.025f * static_cast<float>( count % 3 - 1 ), 0.f, 1.f );
    }
    else if( hand == "Solo" )
    {
        fret = std::clamp( fret + 0.05f * ( static_cast<float>( count % 4 ) - 1.5f ), 0.f, 1.f );
    }
    else if( hand.rfind( "DropD", 0 ) == 0 )
    {
        fret = std::min( fret, 0.15f );
        lift = 0.035f * std::fabs( strum );
    }
    const float neck = inIndex == VenueData::Bass ? 0.86f : 0.62f;
    Performer::Arm& strumArm = pose.Arms[1];
    strumArm.Reach = true;
    strumArm.Target = guitarPosition + guitarRotation * ( slap ? glm::vec3( -0.06f, 0.1f * strum, 0.09f ) : glm::vec3( 0.1f, 0.07f * strum, 0.08f ) );
    strumArm.Pole = spine * glm::vec3( 1.f, -0.35f, 0.65f );
    strumArm.ClearTorso = true;
    // The palm over the strings, the fingers hanging down across them (a pick in them).
    strumArm.Fingers = guitarRotation * glm::vec3( -0.6f, -0.8f, 0.f );
    strumArm.Palm = guitarRotation * glm::vec3( 0.f, 0.f, -1.f );
    strumArm.Grip = slap ? 0.3f : 0.6f;
    Performer::Arm& fretArm = pose.Arms[0];
    fretArm.Reach = true;
    // 0 is the nut, 1 up toward the body: between the frets BuildStringed lays out (the scale
    // length's spacing, the sixteenth at the body), from just behind the first to the fourteenth.
    const float nut = -0.18f - neck;
    const float scale = neck / ( 1.f - std::pow( 2.f, -16.f / 12.f ) );
    const float handFret = 0.5f + 13.5f * fret;
    const float handX = nut + scale * ( 1.f - std::pow( 2.f, -handFret / 12.f ) );
    // The palm cups the neck's lower edge from underneath, the fingers reaching round the front
    // of it and curling back onto the fretboard: further round for a chord, off it as open
    // strings ring.
    fretArm.Target = guitarPosition + guitarRotation * glm::vec3( handX, -0.045f - lift, 0.01f + 0.012f * wrap );
    fretArm.Pole = spine * glm::vec3( -0.8f, -0.6f, 0.6f );
    fretArm.ClearTorso = true;
    fretArm.Fingers = guitarRotation * glm::vec3( 0.f, 0.35f, 1.f );
    fretArm.Palm = guitarRotation * glm::vec3( 0.f, 1.f, 0.f );
    fretArm.Grip = 0.6f + 0.2f * wrap - 6.f * lift;
    ioMember.Body.Apply( pose );
    (void)inEnergy;
}


void Band::DerivePercussion( const VenueData& inVenue )
{
    // Sections from the vocal part's cues ("[tambourine_start]" ... "[tambourine_end]"), and the
    // hits (notes 96/97). Hits outside any section get a tambourine section of their own.
    m_percussionHits = inVenue.m_vocalPercussion;
    const auto kindOf = []( const std::string& inName ) {
        return inName.find( "cowbell" ) != std::string::npos ? Percussion::Cowbell : inName.find( "clap" ) != std::string::npos ? Percussion::Clap : Percussion::Tambourine;
    };
    for( size_t i = 0; i < inVenue.m_vocalCues.size(); ++i )
    {
        const TimedCueData& cue = inVenue.m_vocalCues[i];
        if( cue.m_name.find( "_start" ) == std::string::npos ) continue;
        PercussionSpan span;
        span.Start = cue.m_time;
        span.End = 1e9f;
        span.Kind = kindOf( cue.m_name );
        for( size_t j = i + 1; j < inVenue.m_vocalCues.size(); ++j )
        {
            if( inVenue.m_vocalCues[j].m_name.find( "_end" ) != std::string::npos && kindOf( inVenue.m_vocalCues[j].m_name ) == span.Kind )
            {
                span.End = inVenue.m_vocalCues[j].m_time;
                break;
            }
        }
        m_percussion.push_back( span );
    }
    const auto covered = [this]( float inTime ) {
        for( const PercussionSpan& span : m_percussion )
        {
            if( inTime >= span.Start - 0.05f && inTime <= span.End + 0.05f ) return true;
        }
        return false;
    };
    std::vector<PercussionSpan> loose;
    for( float hit : m_percussionHits )
    {
        if( covered( hit ) ) continue;
        if( !loose.empty() && hit - loose.back().End < 2.f ) loose.back().End = hit + 0.4f;
        else loose.push_back( { hit - 0.4f, hit + 0.4f, Percussion::Tambourine } );
    }
    m_percussion.insert( m_percussion.end(), loose.begin(), loose.end() );
    std::sort( m_percussion.begin(), m_percussion.end(), []( const PercussionSpan& a, const PercussionSpan& b ) { return a.Start < b.Start; } );
}


void Band::DeriveHarmonies( const VenueData& inVenue )
{
    // Backing vocals from the harmony parts, for charts whose VENUE has no singalong notes:
    // HARM2 to the guitarist, HARM3 to the bassist (or whoever else has a mic), each run of notes
    // without a long rest one singalong.
    if( !m_singalong.empty() )
    {
        return;
    }
    std::array<bool, VenueData::MemberCount> taken{};
    const int preferences[2][4] = { { VenueData::Guitar, VenueData::Bass, VenueData::Keys, VenueData::Drums }, { VenueData::Bass, VenueData::Guitar, VenueData::Keys, VenueData::Drums } };
    for( int part = 1; part < VenueData::kHarmonyParts; ++part )
    {
        const std::vector<VenueData::SpanData>& notes = inVenue.m_harmonyNotes[part];
        if( notes.empty() ) continue;
        int singer = -1;
        for( int member : preferences[part - 1] )
        {
            if( HasMember( member ) && !taken[member] )
            {
                singer = member;
                break;
            }
        }
        if( singer < 0 ) continue;
        taken[singer] = true;
        for( const VenueData::SpanData& note : notes )
        {
            if( !m_singalong.empty() && m_singalong.back().m_member == singer && note.m_start - m_singalong.back().m_end < 0.6f )
            {
                m_singalong.back().m_end = std::max( m_singalong.back().m_end, note.m_end );
            }
            else
            {
                m_singalong.push_back( { note.m_start, note.m_end, singer } );
            }
        }
    }
    std::sort( m_singalong.begin(), m_singalong.end(), []( const VenueData::SpanData& a, const VenueData::SpanData& b ) { return a.m_start < b.m_start; } );
}


const Band::PercussionSpan* Band::PercussionAt( double inSeconds ) const
{
    for( const PercussionSpan& span : m_percussion )
    {
        if( inSeconds < span.Start ) break;
        if( inSeconds <= span.End ) return &span;
    }
    return nullptr;
}


float Band::PercussionStrike( double inSeconds, double inBeat ) const
{
    // A sharp strike on each charted hit, fading over a tenth of a second; on the beat in a
    // section with no hits.
    auto it = std::upper_bound( m_percussionHits.begin(), m_percussionHits.end(), static_cast<float>( inSeconds ) );
    if( it == m_percussionHits.begin() || inSeconds - *( it - 1 ) > 1.5 )
    {
        return m_percussionHits.empty() || it == m_percussionHits.begin() ? Pulse( inBeat, 4.0 ) : 0.f;
    }
    return std::exp( -static_cast<float>( inSeconds - *( it - 1 ) ) * 14.f );
}


float Band::AwayFromMic( double inSeconds, uint32_t* outBreak ) const
{
    // The singer holds the mic through a whole line, breaths and short rests included; only a
    // real break between lines sends them off to work the stage, lingering a moment after the
    // line and back at the mic before the next one. From the clock alone, so it's the same at
    // any frame rate and after a seek.
    constexpr float kLinger = 0.8f;   // at the mic after a line ends
    constexpr float kReturn = 1.2f;   // back at the mic before the next line starts
    constexpr float kWalk = 1.2f;     // to walk off, or back
    constexpr float kShortest = kLinger + kReturn + 2.f * kWalk + 1.f;   // shorter gaps stay put
    // The chart's lines (its phrases, notes 105/106) when it has them, else the sung notes.
    const std::vector<VenueData::SpanData>& lines = m_vocalPhrases.empty() ? m_vocalNotes : m_vocalPhrases;
    const float t = static_cast<float>( inSeconds );
    auto next = std::upper_bound( lines.begin(), lines.end(), t, []( float time, const VenueData::SpanData& s ) { return time < s.m_start; } );
    float lastEnd = -1e6f;
    // Notes can overlap: the latest end of the last few closes the line so far.
    for( auto it = next - std::min<std::ptrdiff_t>( 8, next - lines.begin() ); it != next; ++it )
    {
        lastEnd = std::max( lastEnd, it->m_end );
    }
    const float nextStart = next != lines.end() ? next->m_start : 1e6f;
    if( outBreak ) *outBreak = static_cast<uint32_t>( next - lines.begin() );
    if( t <= lastEnd || nextStart - lastEnd < kShortest )
    {
        return 0.f;
    }
    const float leaving = VenueTiming::Smooth( ( t - lastEnd - kLinger ) / kWalk );
    const float returning = VenueTiming::Smooth( ( nextStart - kReturn - t ) / kWalk );
    return std::min( leaving, returning );
}


void Band::UpdateVocals( Member& ioMember, double inSeconds, double inBeat, float inEnergy )
{
    Performer::Pose& pose = ioMember.Pose;
    pose = Performer::Pose();
    const std::string state = StateOf( VenueData::Vocals, inSeconds );
    const bool intense = VenueTiming::Contains( state, "intense" ) || inEnergy > 0.85f;
    const float t = static_cast<float>( inSeconds );
    const float pulse = Pulse( inBeat );
    float open = 0.f;
    const bool singing = Singing( VenueData::Vocals, inSeconds, &open );
    // At the mic through a line; out working the crowd between lines.
    uint32_t gap = 0;
    const float away = AwayFromMic( inSeconds, &gap );
    const bool atMic = away < 0.2f;
    const bool out = away > 0.85f;
    pose.Offset = glm::vec3( away * 1.3f * std::sin( t * 0.27f + ioMember.Phase ), 0.f, -away * 0.5f );
    if( intense && out )
    {
        // Jumps on the downbeats.
        const double measure = inBeat / 2.0;
        const float hop = static_cast<float>( measure - std::floor( measure ) );
        pose.Offset.y = 0.35f * std::max( 0.f, std::sin( hop * kPi * 2.f ) ) * ( hop < 0.5f ? 1.f : 0.f );
    }
    pose.Mouth = open;
    pose.Lean = atMic ? 8.f : 2.f + 6.f * pulse;
    pose.Nod = singing ? -6.f + 3.f * open : atMic ? 4.f * pulse - 3.f : 10.f * pulse - 4.f;
    pose.HeadTurn = away * 30.f * std::sin( t * 0.5f + ioMember.Phase );
    pose.Side = 4.f * std::sin( static_cast<float>( inBeat ) * kPi * 0.5f );
    pose.Legs[0].Spread = 6.f;
    pose.Legs[1].Spread = 6.f;

    Performer::Arm& micArm = pose.Arms[1];
    Performer::Arm& freeArm = pose.Arms[0];
    // What they do with their hands on this break, the same every time it plays.
    const float habit = VenueTiming::Noise( gap, 23u );
    if( atMic )
    {
        // A hand on the mic; the other one rides the melody while singing, else hangs loose.
        micArm.Reach = true;
        micArm.Target = kMicGrip;
        micArm.Pole = glm::vec3( 1.f, -1.f, 0.f );
        // Round the stand from its right, under the mic.
        micArm.Fingers = glm::vec3( 0.f, 0.2f, 1.f );
        micArm.Palm = glm::vec3( -1.f, 0.f, 0.f );
        micArm.Grip = 0.9f;
        const float phrase = VenueTiming::Noise( static_cast<uint32_t>( t * 0.5f ), 3u );
        freeArm.Raise = singing ? 30.f + 60.f * phrase + 15.f * open : 15.f + 5.f * pulse;
        freeArm.Spread = singing ? 25.f + 20.f * phrase : 15.f;
        freeArm.Elbow = singing ? 40.f : 25.f;
    }
    else if( out && intense )
    {
        // Fist pumps on the beat.
        micArm.Raise = 150.f + 25.f * pulse;
        micArm.Spread = 15.f;
        micArm.Elbow = 50.f * ( 1.f - pulse );
        freeArm.Raise = 20.f;
        freeArm.Spread = 20.f;
        freeArm.Elbow = 70.f;
    }
    else if( out && habit < 0.4f )
    {
        // Clapping along over their head.
        const float clap = Pulse( inBeat, 4.0 );
        micArm.Raise = freeArm.Raise = 145.f;
        micArm.Spread = freeArm.Spread = -14.f + 30.f * ( 1.f - clap );
        micArm.Elbow = freeArm.Elbow = 25.f;
        micArm.Palm = -kX;
        freeArm.Palm = kX;
    }
    else if( out && habit < 0.75f )
    {
        // An arm out to the crowd, swept slowly across them.
        micArm.Raise = 95.f + 10.f * pulse;
        micArm.Spread = 30.f + 25.f * std::sin( t * 0.6f + ioMember.Phase );
        micArm.Elbow = 10.f;
        freeArm.Raise = 15.f;
        freeArm.Spread = 15.f;
        freeArm.Elbow = 30.f;
    }
    else
    {
        // Walking: arms loose, swinging a little with the beat.
        const float swing = std::sin( static_cast<float>( inBeat ) * kPi );
        micArm.Raise = 12.f + 8.f * swing;
        micArm.Spread = 12.f;
        micArm.Elbow = 25.f;
        freeArm.Raise = 12.f - 8.f * swing;
        freeArm.Spread = 12.f;
        freeArm.Elbow = 25.f;
    }
    // Percussion sections (the vocal part's tambourine, cowbell or clap), struck on the chart's
    // hits. The free hand plays, and the mic hand helps when it isn't on the mic.
    const PercussionSpan* percussion = singing ? nullptr : PercussionAt( inSeconds );
    const float strike = percussion ? PercussionStrike( inSeconds, inBeat ) : 0.f;
    if( percussion && percussion->Kind == Percussion::Clap )
    {
        micArm = freeArm = Performer::Arm();
        micArm.Raise = freeArm.Raise = 100.f;
        micArm.Spread = freeArm.Spread = -14.f + 30.f * ( 1.f - strike );
        micArm.Elbow = freeArm.Elbow = 45.f;
        micArm.Palm = -kX;
        freeArm.Palm = kX;
    }
    else if( percussion && percussion->Kind == Percussion::Tambourine )
    {
        freeArm = Performer::Arm();
        freeArm.Raise = 55.f + 45.f * strike;
        freeArm.Spread = 30.f;
        freeArm.Elbow = 75.f - 35.f * strike;
        freeArm.Grip = 0.8f;
    }
    else if( percussion && percussion->Kind == Percussion::Cowbell )
    {
        freeArm = Performer::Arm();
        freeArm.Raise = 50.f;
        freeArm.Spread = 15.f;
        freeArm.Elbow = 95.f;
        freeArm.Grip = 0.8f;
        if( !atMic )
        {
            micArm = Performer::Arm();
            micArm.Raise = 35.f + 35.f * strike;
            micArm.Spread = 8.f;
            micArm.Elbow = 85.f - 30.f * strike;
            micArm.Grip = 0.8f;
        }
    }
    ioMember.Body.Apply( pose );
    // The instrument in the playing hand; hidden (shrunk) the rest of the time.
    const glm::quat spine = ioMember.Body.SpineRotation();
    // inGrip: the point of the prop (its own space) that sits in the palm.
    const auto hold = [&]( const EntityHandle& inProp, bool inShown, const glm::quat& inTurn, const glm::vec3& inGrip ) {
        if( !inProp ) return;
        Transform& transform = inProp->GetComponent<Transform>();
        transform.SetScale( inShown ? Vector3( 1.f, 1.f, 1.f ) : Vector3( 0.001f, 0.001f, 0.001f ) );
        if( inShown ) Puppet::PlacePiece( inProp, ioMember.Body.Hand( 0 ) - spine * inTurn * inGrip, spine * inTurn );
    };
    // The tambourine by its rim, its head up and toward the crowd, shaken about the grip; the
    // cowbell by its handle.
    hold( ioMember.Tambourine, percussion && percussion->Kind == Percussion::Tambourine, Axis( 75.f, kX ) * Axis( 25.f * strike, kZ ), glm::vec3( 0.f, 0.f, 0.11f ) );
    hold( ioMember.Cowbell, percussion && percussion->Kind == Percussion::Cowbell, Axis( 20.f, kX ), glm::vec3( 0.f, 0.04f, 0.f ) );
}


void Band::UpdateKeys( Member& ioMember, double inSeconds, double inBeat, float inEnergy )
{
    Performer::Pose& pose = ioMember.Pose;
    pose = Performer::Pose();
    const float pulse = Pulse( inBeat );
    const std::string state = StateOf( VenueData::Keys, inSeconds );
    const bool idle = state == "idle" || state == "idle_realtime";
    pose.Lean = 14.f;
    pose.Nod = ( idle ? 2.f : 12.f ) * pulse;
    pose.Crouch = 0.03f * pulse;
    int count = 0;
    const float press = idle ? 0.f : std::fabs( StrumPhase( ioMember, inSeconds, count ) );
    for( int side = 0; side < 2; ++side )
    {
        Performer::Arm& arm = pose.Arms[side];
        arm.Reach = true;
        const float slide = 0.15f * std::sin( static_cast<float>( count ) * 0.7f + side * 2.f );
        arm.Target = glm::vec3( ( side == 0 ? -0.28f : 0.24f ) + slide, 1.0f - 0.025f * press, 0.36f );
        arm.Pole = glm::vec3( side == 0 ? -1.f : 1.f, -1.f, -0.4f );
        // Palms over the keys, the fingers hanging onto them.
        arm.Fingers = kZ;
        arm.Palm = -kY;
        arm.Grip = 0.3f;
    }
    ioMember.Body.Apply( pose );
    (void)inEnergy;
}


void Band::Update( double inSeconds, float inDeltaTime, float inCrowdEnergy )
{
    if( !m_stage )
    {
        return;
    }
    double beat = 0.0;
    int measureBeat = 0;
    VenueTiming::BeatAt( m_beats, m_bpm, inSeconds, beat, measureBeat );
    for( int index = 0; index < VenueData::MemberCount; ++index )
    {
        Member& member = m_members[index];
        if( !member.Present )
        {
            continue;
        }
        if( inSeconds > m_endTime && index != VenueData::Drums )
        {
            // The song's over: arms up to the crowd, a bounce on the spot.
            Performer::Pose& pose = member.Pose;
            pose = Performer::Pose();
            const float since = static_cast<float>( inSeconds ) - m_endTime;
            pose.Offset.y = 0.12f * std::fabs( std::sin( since * 4.f + member.Phase ) ) * std::exp( -since * 0.3f );
            pose.Arms[0].Raise = pose.Arms[1].Raise = 160.f;
            pose.Arms[0].Spread = pose.Arms[1].Spread = 25.f + 10.f * std::sin( since * 3.f );
            pose.Nod = -10.f;
            member.Body.Apply( pose );
            if( member.Instrument && index != VenueData::Vocals )
            {
                const glm::quat spine = member.Body.SpineRotation();
                glm::vec3 position = member.Body.SpineBase() + spine * ( index == VenueData::Bass ? kBassHang : kGuitarHang );
                glm::quat rotation = spine * Axis( -10.f, kZ );
                if( index == VenueData::Guitar || index == VenueData::Bass )
                {
                    SwingInstrument( member, pose.Offset, position, rotation, inDeltaTime );
                }
                else
                {
                    Puppet::PlacePiece( member.Instrument, position, rotation );
                }
            }
            continue;
        }
        // A soloist walks out front and back over a moment (snapped on a seek).
        const float solo = StateOf( index, inSeconds ) == "play_solo" ? 1.f : 0.f;
        const bool seeked = std::fabs( inSeconds - m_lastSeconds ) > 0.5;
        if( seeked )
        {
            member.GuitarHung = false;
        }
        member.Solo = seeked ? solo : member.Solo + ( solo - member.Solo ) * ( 1.f - std::exp( -std::clamp( inDeltaTime, 0.f, 0.1f ) * 3.f ) );
        switch( index )
        {
        case VenueData::Drums: UpdateDrums( member, inSeconds, beat, inCrowdEnergy, inDeltaTime ); break;
        case VenueData::Guitar:
        case VenueData::Bass: UpdateStringed( member, index, inSeconds, beat + ( index == VenueData::Bass ? 0.03 : 0.0 ), inCrowdEnergy, inDeltaTime ); break;
        case VenueData::Vocals: UpdateVocals( member, inSeconds, beat, inCrowdEnergy ); break;
        case VenueData::Keys: UpdateKeys( member, inSeconds, beat, inCrowdEnergy ); break;
        default: break;
        }
    }
    m_lastSeconds = inSeconds;
}


namespace
{
    // A member-space point in venue space.
    Vector3 ToVenue( const Transform* inGroup, const glm::vec3& inLocal )
    {
        if( !inGroup )
        {
            return Vector3( inLocal );
        }
        const glm::quat rotation = inGroup->GetRotation().InternalQuat;
        return Vector3( inGroup->GetPosition().InternalVector + rotation * inLocal );
    }
}


Vector3 Band::HeadOf( int inMember ) const
{
    if( !HasMember( inMember ) ) return m_members[std::clamp( inMember, 0, 4 )].Spot + Vector3( 0.f, 1.6f, 0.f );
    const Member& member = m_members[inMember];
    return ToVenue( member.Group ? &member.Group->GetComponent<Transform>() : nullptr, member.Body.HeadCentre() );
}


Vector3 Band::GazeOf( int inMember ) const
{
    if( !HasMember( inMember ) ) return Vector3( 0.f, 0.f, -1.f );
    const Member& member = m_members[inMember];
    const glm::quat group = member.Group ? member.Group->GetComponent<Transform>().GetRotation().InternalQuat : glm::quat( 1.f, 0.f, 0.f, 0.f );
    return Vector3( glm::normalize( group * member.Body.HeadRotation() * glm::vec3( 0.f, 0.f, 1.f ) ) );
}


Vector3 Band::ChestOf( int inMember ) const
{
    if( !HasMember( inMember ) ) return m_members[std::clamp( inMember, 0, 4 )].Spot + Vector3( 0.f, 1.3f, 0.f );
    const Member& member = m_members[inMember];
    return ToVenue( member.Group ? &member.Group->GetComponent<Transform>() : nullptr, member.Body.Chest() );
}


Vector3 Band::HandsOf( int inMember ) const
{
    if( !HasMember( inMember ) ) return m_members[std::clamp( inMember, 0, 4 )].Spot + Vector3( 0.f, 1.f, 0.f );
    const Member& member = m_members[inMember];
    return ToVenue( member.Group ? &member.Group->GetComponent<Transform>() : nullptr, ( member.Body.Hand( 0 ) + member.Body.Hand( 1 ) ) * 0.5f );
}


Vector3 Band::FeetOf( int inMember ) const
{
    return m_members[std::clamp( inMember, 0, 4 )].Spot;
}


bool Band::NeckOf( int inMember, Vector3& outHeadstock, Vector3& outBody, Vector3& outFace, Vector3& outEdge ) const
{
    if( !HasMember( inMember ) || !m_members[inMember].Instrument || m_members[inMember].NeckLength <= 0.f )
    {
        return false;
    }
    // In the guitar's own space (BuildStringed) the neck runs along -x from the body, the face
    // toward +z, the neck's upper edge toward +y; taken through its world matrix, so the camera
    // sits exactly on what's drawn.
    const Member& member = m_members[inMember];
    const Matrix4& world = member.Instrument->GetComponent<Transform>().GetLocalToWorldMatrix();
    const auto at = [&]( const glm::vec3& inLocal ) { return world.TransformPoint( Vector3( inLocal ) ) - VenueLayout::kVenueOrigin; };
    outHeadstock = at( glm::vec3( -0.26f - member.NeckLength, 0.f, 0.02f ) );
    outBody = at( glm::vec3( 0.05f, 0.f, 0.02f ) );
    outFace = at( glm::vec3( 0.f, 0.f, 1.f ) ) - at( glm::vec3( 0.f ) );
    outEdge = at( glm::vec3( 0.f, 1.f, 0.f ) ) - at( glm::vec3( 0.f ) );
    return true;
}
