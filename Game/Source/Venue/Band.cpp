#include "Venue/Band.h"
#include "Venue/VenueKit.h"
#include "Venue/VenueLayout.h"
#include "Venue/VenueTiming.h"
#include "Components/Transform.h"
#include "Materials/StandardMaterial.h"
#include "Core/CommandLine.h"
#include "CLog.h"
#include <algorithm>
#include <cmath>
#include <cstring>

namespace
{
    constexpr float kPi = 3.14159265f;
    constexpr float kDeg = kPi / 180.f;
    constexpr float kStickLength = 0.4f;
    // The grip: the hand holds the stick this far from its tip (a quarter up from the butt).
    constexpr float kStickReach = 0.3f;

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

    // Shirt colours, one per member.
    const Vector3 kShirts[VenueData::MemberCount] = { Vector3( 0.6f, 0.6f, 0.58f ), Vector3( 0.55f, 0.06f, 0.06f ), Vector3( 0.1f, 0.18f, 0.4f ), Vector3( 0.85f, 0.82f, 0.78f ), Vector3( 0.3f, 0.12f, 0.35f ) };
    const Vector3 kHair[VenueData::MemberCount] = { Vector3( 0.05f, 0.04f, 0.03f ), Vector3( 0.35f, 0.2f, 0.08f ), Vector3( 0.03f, 0.03f, 0.03f ), Vector3( 0.75f, 0.6f, 0.3f ), Vector3( 0.5f, 0.1f, 0.1f ) };
    const Vector3 kSkin[VenueData::MemberCount] = { Vector3( 0.78f, 0.58f, 0.45f ), Vector3( 0.9f, 0.72f, 0.6f ), Vector3( 0.45f, 0.3f, 0.2f ), Vector3( 0.85f, 0.65f, 0.52f ), Vector3( 0.62f, 0.45f, 0.32f ) };

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

    bool IsCymbal( VenueData::DrumPiece inPiece )
    {
        using Piece = VenueData::DrumPiece;
        return inPiece == Piece::HiHat || inPiece == Piece::Crash1 || inPiece == Piece::Crash2 || inPiece == Piece::Ride;
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


void Band::Build( VenueKit& inKit, Transform* inStage, const VenueData& inVenue, const std::vector<NoteData>& inNotes, const std::vector<BeatData>& inBeats, float inBpm )
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
        member.Spot = VenueLayout::kMemberSpots[index];
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
    for( auto& strokes : m_strokes )
    {
        std::stable_sort( strokes.begin(), strokes.end(), []( const Stroke& a, const Stroke& b ) { return a.Time < b.Time; } );
    }
    DeriveFallbacks( inNotes );

    for( int index = 0; index < VenueData::MemberCount; ++index )
    {
        if( index == VenueData::Keys && !keys )
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
        group.SetRotation( Vector3( 0.f, index == VenueData::Keys ? 155.f : 180.f, 0.f ) );
        Puppet::Look look;
        look.Shirt = kShirts[index];
        look.Hair = kHair[index];
        look.Skin = kSkin[index];
        look.LongHair = index == VenueData::Guitar || index == VenueData::Vocals || index == VenueData::Drums;
        look.Pants = index == VenueData::Vocals ? Vector3( 0.04f, 0.04f, 0.05f ) : Vector3( 0.07f, 0.08f, 0.12f );
        member.Body.Build( inKit, &group, Vector3( 0.f, 0.f, 0.f ), 0.f, look, true );
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


void Band::DeriveStrokes( const std::vector<NoteData>& inNotes )
{
    // Hands from the chart's gems: notes struck together go left-most piece to the left hand;
    // alone, cymbals and the floor tom take the right hand, the snare the left (both alternate in
    // fast runs); the kick is the right foot and the hi-hat pedal the left.
    std::vector<const NoteData*> notes;
    for( const NoteData& note : inNotes ) notes.push_back( &note );
    std::stable_sort( notes.begin(), notes.end(), []( const NoteData* a, const NoteData* b ) { return a->m_triggerTime < b->m_triggerTime; } );
    float lastHand[2] = { -10.f, -10.f };
    Piece lastPiece[2] = { Piece::Snare, Piece::HiHat };
    for( size_t i = 0; i < notes.size(); )
    {
        const float time = notes[i]->m_triggerTime;
        std::vector<std::pair<Piece, bool>> hands;
        size_t j = i;
        for( ; j < notes.size() && notes[j]->m_triggerTime - time < 0.015f; ++j )
        {
            const Piece piece = PieceFor( notes[j]->m_editorLane );
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
        std::sort( hands.begin(), hands.end(), []( const auto& a, const auto& b ) { return kStrike[static_cast<int>( a.first )].x < kStrike[static_cast<int>( b.first )].x; } );
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
        if( IsCymbal( piece ) || piece == Piece::FloorTom || piece == Piece::Tom2 )
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
    const Vector3 metal( 0.08f, 0.08f, 0.09f );
    ioMember.MicStand = inKit.Group( "MicStand", &group, inPosition );
    Transform& stand = ioMember.MicStand->GetComponent<Transform>();
    inKit.Piece( Moonlight::MeshType::Cylinder, Vector3( 0.f, 0.01f, 0.f ), Vector3( 0.3f, 0.02f, 0.3f ), metal, &stand );
    inKit.Piece( Moonlight::MeshType::Cylinder, Vector3( 0.f, inHeight * 0.5f, 0.f ), Vector3( 0.025f, inHeight, 0.025f ), metal, &stand );
    // The mic, angled at the singer's mouth.
    EntityHandle mic = inKit.Piece( Moonlight::MeshType::Capsule, Vector3( 0.f, inHeight + 0.03f, -0.07f ), Vector3( 0.045f, 0.18f, 0.045f ), Vector3( 0.1f, 0.1f, 0.1f ), &stand );
    if( mic ) mic->GetComponent<Transform>().SetRotation( Vector3( -70.f, 0.f, 0.f ) );
    inKit.Piece( Moonlight::MeshType::Sphere, Vector3( 0.f, inHeight + 0.06f, -0.15f ), Vector3( 0.06f, 0.06f, 0.06f ), Vector3( 0.45f, 0.45f, 0.48f ), &stand );
}


void Band::BuildDrums( VenueKit& inKit, Member& ioMember )
{
    using Shape = Moonlight::MeshType;
    Transform& group = ioMember.Group->GetComponent<Transform>();
    const Vector3 shell( 0.55f, 0.05f, 0.07f );
    const Vector3 head( 0.85f, 0.83f, 0.78f );
    const Vector3 brass( 0.75f, 0.55f, 0.18f );
    const Vector3 metal( 0.12f, 0.12f, 0.13f );
    const auto drum = [&]( Piece inPiece, const glm::vec3& inCentre, float inDiameter, float inDepth, const Vector3& inTilt ) {
        KitPiece& piece = m_kit[static_cast<int>( inPiece )];
        piece.Entity = inKit.Group( "Drum", &group, Vector3( inCentre ) );
        piece.Rest = inTilt;
        piece.Scale = Vector3( 1.f, 1.f, 1.f );
        if( !piece.Entity ) return;
        Transform& transform = piece.Entity->GetComponent<Transform>();
        transform.SetRotation( inTilt );
        inKit.Piece( Shape::Cylinder, Vector3( 0.f, 0.f, 0.f ), Vector3( inDiameter, inDepth, inDiameter ), shell, &transform );
        inKit.Piece( Shape::Cylinder, Vector3( 0.f, inDepth * 0.5f + 0.004f, 0.f ), Vector3( inDiameter * 0.96f, 0.01f, inDiameter * 0.96f ), head, &transform );
    };
    const auto cymbal = [&]( Piece inPiece, const glm::vec3& inCentre, float inDiameter, const Vector3& inTilt ) {
        KitPiece& piece = m_kit[static_cast<int>( inPiece )];
        piece.Cymbal = true;
        piece.Rest = inTilt;
        piece.Scale = Vector3( 1.f, 1.f, 1.f );
        piece.Entity = inKit.Piece( Shape::Cylinder, Vector3( inCentre ), Vector3( inDiameter, 0.012f, inDiameter ), brass, &group, brass * 0.08f );
        if( piece.Entity ) piece.Entity->GetComponent<Transform>().SetRotation( inTilt );
        if( StandardMaterial* material = VenueKit::MaterialOf( piece.Entity ) )
        {
            material->Metallic = 0.9f;
            material->Roughness = 0.3f;
        }
        // Its stand.
        inKit.Piece( Shape::Cylinder, Vector3( inCentre.x, inCentre.y * 0.5f, inCentre.z + 0.02f ), Vector3( 0.022f, inCentre.y, 0.022f ), metal, &group );
    };
    // A rug, the throne, the kick with the band's logo on its front head.
    inKit.Box( Vector3( 0.05f, 0.005f, 0.45f ), Vector3( 2.2f, 0.01f, 2.f ), Vector3( 0.25f, 0.04f, 0.04f ), &group );
    inKit.Piece( Shape::Cylinder, Vector3( 0.f, 0.29f, -0.04f ), Vector3( 0.38f, 0.58f, 0.38f ), Vector3( 0.05f, 0.05f, 0.05f ), &group );
    drum( Piece::Kick, glm::vec3( 0.f, 0.3f, 0.9f ), 0.6f, 0.44f, Vector3( 90.f, 0.f, 0.f ) );
    inKit.Piece( Shape::Cylinder, Vector3( 0.f, 0.3f, 1.125f ), Vector3( 0.36f, 0.01f, 0.36f ), Vector3( 0.9f, 0.5f, 0.1f ), &group, Vector3( 0.9f, 0.45f, 0.08f ) )
        ->GetComponent<Transform>().SetRotation( Vector3( 90.f, 0.f, 0.f ) );
    drum( Piece::Snare, kStrike[static_cast<int>( Piece::Snare )] - glm::vec3( 0.f, 0.07f, 0.f ), 0.36f, 0.13f, Vector3( -8.f, 0.f, 4.f ) );
    drum( Piece::Tom1, kStrike[static_cast<int>( Piece::Tom1 )] - glm::vec3( 0.f, 0.1f, -0.02f ), 0.28f, 0.2f, Vector3( -22.f, 0.f, 8.f ) );
    drum( Piece::Tom2, kStrike[static_cast<int>( Piece::Tom2 )] - glm::vec3( 0.f, 0.1f, -0.02f ), 0.3f, 0.22f, Vector3( -22.f, 0.f, -8.f ) );
    drum( Piece::FloorTom, kStrike[static_cast<int>( Piece::FloorTom )] - glm::vec3( 0.f, 0.22f, 0.f ), 0.42f, 0.42f, Vector3( 0.f, 0.f, 0.f ) );
    cymbal( Piece::HiHat, kStrike[static_cast<int>( Piece::HiHat )] - glm::vec3( 0.f, 0.01f, 0.f ), 0.36f, Vector3( -4.f, 0.f, 0.f ) );
    inKit.Piece( Shape::Cylinder, Vector3( kStrike[1] - glm::vec3( 0.f, 0.035f, 0.f ) ), Vector3( 0.36f, 0.012f, 0.36f ), brass, &group, brass * 0.08f );
    cymbal( Piece::Crash1, kStrike[static_cast<int>( Piece::Crash1 )] - glm::vec3( 0.f, 0.02f, -0.12f ), 0.46f, Vector3( -18.f, 0.f, 12.f ) );
    cymbal( Piece::Crash2, kStrike[static_cast<int>( Piece::Crash2 )] - glm::vec3( 0.f, 0.02f, -0.12f ), 0.48f, Vector3( -18.f, 0.f, -12.f ) );
    cymbal( Piece::Ride, kStrike[static_cast<int>( Piece::Ride )] - glm::vec3( 0.f, 0.02f, -0.1f ), 0.56f, Vector3( -12.f, 0.f, -10.f ) );
    // Pedals.
    inKit.Box( Vector3( kStrike[0] ), Vector3( 0.1f, 0.03f, 0.28f ), metal, &group );
    inKit.Box( Vector3( kStrike[9] ), Vector3( 0.1f, 0.03f, 0.28f ), metal, &group );
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
    using Shape = Moonlight::MeshType;
    Transform& group = ioMember.Group->GetComponent<Transform>();
    ioMember.Instrument = inKit.Group( inBass ? "Bass" : "Guitar", &group );
    if( !ioMember.Instrument ) return;
    Transform& guitar = ioMember.Instrument->GetComponent<Transform>();
    // The guitar's own space: the neck along -x, the face toward +z.
    const Vector3 finish = inBass ? Vector3( 0.05f, 0.12f, 0.3f ) : Vector3( 0.7f, 0.08f, 0.05f );
    inKit.Piece( Shape::Sphere, Vector3( 0.11f, 0.f, 0.f ), Vector3( 0.36f, 0.34f, 0.07f ), finish, &guitar );
    inKit.Piece( Shape::Sphere, Vector3( -0.08f, 0.f, 0.f ), Vector3( 0.27f, 0.26f, 0.07f ), finish, &guitar );
    inKit.Box( Vector3( 0.08f, -0.05f, 0.037f ), Vector3( 0.16f, 0.12f, 0.01f ), Vector3( 0.85f, 0.85f, 0.8f ), &guitar );
    inKit.Box( Vector3( 0.06f, 0.02f, 0.04f ), Vector3( 0.03f, 0.1f, 0.01f ), Vector3( 0.6f, 0.6f, 0.6f ), &guitar );
    const float neck = inBass ? 0.86f : 0.62f;
    ioMember.NeckLength = neck;
    inKit.Box( Vector3( -0.18f - neck * 0.5f, 0.f, 0.02f ), Vector3( neck, 0.05f, 0.03f ), Vector3( 0.25f, 0.15f, 0.07f ), &guitar );
    inKit.Box( Vector3( -0.26f - neck, 0.f, 0.02f ), Vector3( 0.17f, 0.075f, 0.025f ), Vector3( 0.05f, 0.05f, 0.05f ), &guitar );
    // Frets, a nut and strings, for the neck camera: the fretboard's face is at z 0.035, from the
    // nut (x -0.18 - neck) to the body (x -0.18). Frets fall at the scale length's spacing, the
    // sixteenth meeting the body.
    const float nut = -0.18f - neck;
    const float scale = neck / ( 1.f - std::pow( 2.f, -16.f / 12.f ) );
    const Vector3 metal( 0.75f, 0.74f, 0.7f );
    inKit.Box( Vector3( nut, 0.f, 0.037f ), Vector3( 0.006f, 0.05f, 0.006f ), Vector3( 0.95f, 0.93f, 0.85f ), &guitar );
    for( int fret = 1; fret < 16; ++fret )
    {
        const float x = nut + scale * ( 1.f - std::pow( 2.f, -static_cast<float>( fret ) / 12.f ) );
        inKit.Box( Vector3( x, 0.f, 0.036f ), Vector3( 0.003f, 0.05f, 0.004f ), metal, &guitar );
    }
    const int strings = inBass ? 4 : 6;
    const float bridge = 0.16f;
    for( int string = 0; string < strings; ++string )
    {
        const float y = -0.019f + 0.038f * static_cast<float>( string ) / static_cast<float>( strings - 1 );
        inKit.Box( Vector3( ( nut + bridge ) * 0.5f, y, 0.041f ), Vector3( bridge - nut, inBass ? 0.0035f : 0.0025f, 0.0025f ), Vector3( 0.85f, 0.84f, 0.8f ), &guitar );
    }
    // An amp behind them.
    const float side = inBass ? 1.f : -1.f;
    inKit.Box( Vector3( side * 0.4f, 0.55f, -1.5f ), Vector3( 0.9f, 1.1f, 0.45f ), Vector3( 0.04f, 0.04f, 0.04f ), &group );
    inKit.Box( Vector3( side * 0.4f, 0.55f, -1.27f ), Vector3( 0.8f, 0.8f, 0.01f ), Vector3( 0.08f, 0.08f, 0.09f ), &group );
    inKit.Box( Vector3( side * 0.4f, 1.03f, -1.27f ), Vector3( 0.06f, 0.03f, 0.01f ), Vector3( 1.f, 0.1f, 0.05f ), &group, Vector3( 2.f, 0.2f, 0.1f ) );
    BuildMicStand( inKit, ioMember, Vector3( 0.f, 0.f, 0.55f ), 1.46f );
}


void Band::BuildVocals( VenueKit& inKit, Member& ioMember )
{
    BuildMicStand( inKit, ioMember, Vector3( 0.f, 0.f, 0.42f ), 1.5f );
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
    const Vector3 metal( 0.1f, 0.1f, 0.11f );
    inKit.Box( Vector3( 0.f, 0.92f, 0.42f ), Vector3( 1.2f, 0.08f, 0.34f ), Vector3( 0.06f, 0.06f, 0.07f ), &group );
    inKit.Box( Vector3( 0.f, 0.965f, 0.36f ), Vector3( 1.1f, 0.012f, 0.16f ), Vector3( 0.9f, 0.9f, 0.88f ), &group );
    inKit.Box( Vector3( 0.3f, 0.965f, 0.5f ), Vector3( 0.2f, 0.012f, 0.06f ), Vector3( 0.2f, 0.6f, 1.f ), &group, Vector3( 0.3f, 1.f, 2.f ) );
    for( float x : { -0.4f, 0.4f } )
    {
        EntityHandle leg = inKit.Box( Vector3( x, 0.45f, 0.42f ), Vector3( 0.04f, 1.f, 0.04f ), metal, &group );
        if( leg ) leg->GetComponent<Transform>().SetRotation( Vector3( 0.f, 0.f, x > 0.f ? 20.f : -20.f ) );
        EntityHandle cross = inKit.Box( Vector3( x, 0.45f, 0.42f ), Vector3( 0.04f, 1.f, 0.04f ), metal, &group );
        if( cross ) cross->GetComponent<Transform>().SetRotation( Vector3( 0.f, 0.f, x > 0.f ? -20.f : 20.f ) );
    }
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


glm::vec3 Band::StrikePoint( Piece inPiece ) const
{
    return kStrike[static_cast<int>( inPiece )];
}


glm::vec3 Band::StickTip( int inLimb, double inSeconds, float& outLift ) const
{
    // The tip arcs from stroke to stroke, landing on each note: up as high as the gap allows,
    // across to the next piece on the way.
    const auto& strokes = m_strokes[inLimb];
    const glm::vec3 rest = inLimb == 0 ? StrikePoint( Piece::Snare ) + glm::vec3( 0.02f, 0.14f, -0.04f ) : StrikePoint( Piece::HiHat ) + glm::vec3( 0.08f, 0.14f, -0.02f );
    auto it = std::upper_bound( strokes.begin(), strokes.end(), static_cast<float>( inSeconds ), []( float t, const Stroke& s ) { return t < s.Time; } );
    const Stroke* next = it != strokes.end() ? &*it : nullptr;
    const Stroke* prev = it != strokes.begin() ? &*( it - 1 ) : nullptr;
    const float t = static_cast<float>( inSeconds );
    constexpr float kWindUp = 0.28f;
    constexpr float kRecover = 0.3f;
    glm::vec3 from = prev ? StrikePoint( prev->Target ) : rest;
    float fromTime = prev ? prev->Time : -1000.f;
    if( !next || next->Time - t > kWindUp + 0.05f )
    {
        // Between phrases: recover from the last stroke toward rest.
        const float since = prev ? t - prev->Time : 10.f;
        const float s = VenueTiming::Smooth( since / kRecover );
        outLift = 0.14f * s + 0.12f * std::sin( std::min( 1.f, since / kRecover ) * kPi ) * ( 1.f - s );
        glm::vec3 tip = glm::mix( from, rest, s );
        tip.y += 0.12f * std::sin( std::min( 1.f, since / kRecover ) * kPi ) * ( 1.f - s );
        if( next && next->Time - t <= kWindUp + 0.05f + 0.25f )
        {
            // Lining up for the next phrase.
            const float s2 = VenueTiming::Smooth( 1.f - ( next->Time - t - kWindUp - 0.05f ) / 0.25f );
            tip = glm::mix( tip, StrikePoint( next->Target ) + glm::vec3( 0.f, 0.14f, 0.f ), s2 );
        }
        return tip;
    }
    if( !prev || t - fromTime > kWindUp * 2.f )
    {
        from = rest;
        fromTime = next->Time - kWindUp;
    }
    const float gap = std::max( 0.03f, next->Time - fromTime );
    const float s = std::clamp( ( t - fromTime ) / gap, 0.f, 1.f );
    const float height = std::clamp( gap * 0.55f, 0.05f, 0.3f ) * ( next->Soft ? 0.45f : 1.f );
    outLift = height * 4.f * s * ( 1.f - s );
    glm::vec3 tip = glm::mix( from, StrikePoint( next->Target ), VenueTiming::Smooth( ( s - 0.1f ) / 0.75f ) );
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
    Puppet::Pose& pose = ioMember.Pose;
    pose = Puppet::Pose();
    pose.Seated = true;
    pose.SeatHeight = 0.62f;
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
        pose.HeadTurn = 35.f;
        pose.Nod = -4.f;
    }

    // Hands: the stick tips follow the strokes; the hand sits a stick's length behind each tip.
    float lift[2] = { 0.f, 0.f };
    glm::vec3 tips[2];
    for( int side = 0; side < 2; ++side )
    {
        tips[side] = StickTip( side, inSeconds, lift[side] );
    }
    // The shoulders follow the hands across the kit.
    const float reach = ( tips[0].x + tips[1].x ) * 0.5f;
    pose.Turn = -reach * 40.f;
    pose.Side = reach * 10.f;
    ioMember.Body.Apply( pose );
    for( int side = 0; side < 2; ++side )
    {
        const glm::vec3 chest = ioMember.Body.Chest();
        glm::vec3 toward = tips[side] - chest;
        toward.y = 0.f;
        toward = glm::dot( toward, toward ) > 1e-6f ? glm::normalize( toward ) : kZ;
        const float angle = ( 24.f - 100.f * lift[side] ) * kDeg;   // tip down at the stroke, up as it lifts
        const glm::vec3 stick = glm::normalize( toward * std::cos( angle ) - kY * std::sin( angle ) );
        const glm::vec3 hand = tips[side] - stick * kStickReach;
        Puppet::Arm& arm = pose.Arms[side];
        arm.Reach = true;
        arm.Target = hand;
        arm.Pole = glm::vec3( side == 0 ? -0.6f : 0.6f, -1.f, -0.3f );
    }
    // Feet: the kick and hi-hat pedal.
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
    pose.Legs[1].Spread = 6.f;
    pose.Legs[0].Toe = footFor( Limb::LeftFoot, m_strokes[static_cast<int>( Limb::LeftFoot )].empty() ? 14.f : 4.f );
    pose.Legs[0].Spread = 14.f;
    ioMember.Body.Apply( pose );
    static const bool kDebug = CommandLine::Has( "--band-debug" );
    if( kDebug && static_cast<int>( inSeconds * 2.0 ) != static_cast<int>( m_lastSeconds * 2.0 ) )
    {
        for( int side = 0; side < 2; ++side )
        {
            const glm::vec3 h = ioMember.Body.Hand( side );
            const glm::vec3 s = ioMember.Body.Shoulder( side );
            BRUH_FMT( "Drummer %d t=%.2f tip(%.2f %.2f %.2f) target(%.2f %.2f %.2f) hand(%.2f %.2f %.2f) shoulder(%.2f %.2f %.2f) lift %.2f", side, inSeconds,
                tips[side].x, tips[side].y, tips[side].z, pose.Arms[side].Target.x, pose.Arms[side].Target.y, pose.Arms[side].Target.z, h.x, h.y, h.z, s.x, s.y, s.z, lift[side] );
        }
    }
    for( int side = 0; side < 2; ++side )
    {
        if( ioMember.Sticks[side] )
        {
            const glm::vec3 hand = ioMember.Body.Hand( side );
            const glm::vec3 along = glm::normalize( tips[side] - hand );
            Puppet::PlaceBone( ioMember.Sticks[side], hand - along * ( kStickLength - kStickReach ), hand + along * kStickReach );
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


void Band::UpdateStringed( Member& ioMember, int inIndex, double inSeconds, double inBeat, float inEnergy )
{
    Puppet::Pose& pose = ioMember.Pose;
    pose = Puppet::Pose();
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
    ioMember.Body.Apply( pose );

    // The guitar hangs off the torso, its neck up and to the player's left.
    const glm::quat spine = ioMember.Body.SpineRotation();
    const float neckAngle = -24.f - 10.f * energy * pulse * ( 1.f - soloing ) - 24.f * soloing;
    const glm::quat guitarRotation = spine * Axis( neckAngle, kZ ) * Axis( -8.f, kY );
    const glm::vec3 guitarPosition = ioMember.Body.SpineBase() + spine * glm::vec3( 0.04f, 0.2f, 0.17f );
    if( ioMember.Instrument )
    {
        Puppet::PlacePiece( ioMember.Instrument, guitarPosition, guitarRotation );
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
    Puppet::Arm& strumArm = pose.Arms[1];
    strumArm.Reach = true;
    strumArm.Target = guitarPosition + guitarRotation * ( slap ? glm::vec3( -0.06f, 0.1f * strum, 0.1f ) : glm::vec3( 0.1f, 0.07f * strum, 0.09f ) );
    strumArm.Pole = glm::vec3( 1.f, -0.4f, -1.f );
    Puppet::Arm& fretArm = pose.Arms[0];
    fretArm.Reach = true;
    fretArm.Target = guitarPosition + guitarRotation * glm::vec3( -0.25f - neck * ( 0.15f + 0.7f * fret ), -0.03f - 0.02f * wrap, 0.05f + 0.015f * wrap + lift );
    fretArm.Pole = glm::vec3( -0.3f, -1.f, -0.3f );
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
    Puppet::Pose& pose = ioMember.Pose;
    pose = Puppet::Pose();
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
    ioMember.Body.Apply( pose );

    Puppet::Arm& micArm = pose.Arms[1];
    Puppet::Arm& freeArm = pose.Arms[0];
    // What they do with their hands on this break, the same every time it plays.
    const float habit = VenueTiming::Noise( gap, 23u );
    if( atMic )
    {
        // A hand on the mic; the other one rides the melody while singing, else hangs loose.
        micArm.Reach = true;
        micArm.Target = glm::vec3( 0.02f, 1.5f, 0.32f );
        micArm.Pole = glm::vec3( 1.f, -1.f, 0.f );
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
        micArm.Spread = freeArm.Spread = 4.f + 22.f * ( 1.f - clap );
        micArm.Elbow = freeArm.Elbow = 25.f;
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
        micArm.Reach = freeArm.Reach = false;
        micArm.Raise = freeArm.Raise = 100.f;
        micArm.Spread = freeArm.Spread = 4.f + 26.f * ( 1.f - strike );
        micArm.Elbow = freeArm.Elbow = 45.f;
    }
    else if( percussion && percussion->Kind == Percussion::Tambourine )
    {
        freeArm.Reach = false;
        freeArm.Raise = 55.f + 45.f * strike;
        freeArm.Spread = 30.f;
        freeArm.Elbow = 75.f - 35.f * strike;
    }
    else if( percussion && percussion->Kind == Percussion::Cowbell )
    {
        freeArm.Reach = false;
        freeArm.Raise = 50.f;
        freeArm.Spread = 15.f;
        freeArm.Elbow = 95.f;
        if( !atMic )
        {
            micArm.Reach = false;
            micArm.Raise = 35.f + 35.f * strike;
            micArm.Spread = 8.f;
            micArm.Elbow = 85.f - 30.f * strike;
        }
    }
    ioMember.Body.Apply( pose );
    // The instrument in the playing hand; hidden (shrunk) the rest of the time.
    const glm::quat spine = ioMember.Body.SpineRotation();
    const auto hold = [&]( const EntityHandle& inProp, bool inShown, const glm::quat& inTurn ) {
        if( !inProp ) return;
        Transform& transform = inProp->GetComponent<Transform>();
        transform.SetScale( inShown ? Vector3( 1.f, 1.f, 1.f ) : Vector3( 0.001f, 0.001f, 0.001f ) );
        if( inShown ) Puppet::PlacePiece( inProp, ioMember.Body.Hand( 0 ), spine * inTurn );
    };
    hold( ioMember.Tambourine, percussion && percussion->Kind == Percussion::Tambourine, Axis( 75.f, kX ) * Axis( 25.f * strike, kZ ) );
    hold( ioMember.Cowbell, percussion && percussion->Kind == Percussion::Cowbell, Axis( 20.f, kX ) );
}


void Band::UpdateKeys( Member& ioMember, double inSeconds, double inBeat, float inEnergy )
{
    Puppet::Pose& pose = ioMember.Pose;
    pose = Puppet::Pose();
    const float pulse = Pulse( inBeat );
    const std::string state = StateOf( VenueData::Keys, inSeconds );
    const bool idle = state == "idle" || state == "idle_realtime";
    pose.Lean = 14.f;
    pose.Nod = ( idle ? 2.f : 12.f ) * pulse;
    pose.Crouch = 0.03f * pulse;
    int count = 0;
    const float press = idle ? 0.f : std::fabs( StrumPhase( ioMember, inSeconds, count ) );
    ioMember.Body.Apply( pose );
    for( int side = 0; side < 2; ++side )
    {
        Puppet::Arm& arm = pose.Arms[side];
        arm.Reach = true;
        const float slide = 0.15f * std::sin( static_cast<float>( count ) * 0.7f + side * 2.f );
        arm.Target = glm::vec3( ( side == 0 ? -0.28f : 0.24f ) + slide, 1.0f - 0.025f * press, 0.36f );
        arm.Pole = glm::vec3( side == 0 ? -1.f : 1.f, -1.f, -0.4f );
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
            Puppet::Pose& pose = member.Pose;
            pose = Puppet::Pose();
            const float since = static_cast<float>( inSeconds ) - m_endTime;
            pose.Offset.y = 0.12f * std::fabs( std::sin( since * 4.f + member.Phase ) ) * std::exp( -since * 0.3f );
            pose.Arms[0].Raise = pose.Arms[1].Raise = 160.f;
            pose.Arms[0].Spread = pose.Arms[1].Spread = 25.f + 10.f * std::sin( since * 3.f );
            pose.Nod = -10.f;
            member.Body.Apply( pose );
            if( member.Instrument && index != VenueData::Vocals )
            {
                const glm::quat spine = member.Body.SpineRotation();
                Puppet::PlacePiece( member.Instrument, member.Body.SpineBase() + spine * glm::vec3( 0.04f, 0.15f, 0.17f ), spine * Axis( -10.f, kZ ) );
            }
            continue;
        }
        // A soloist walks out front and back over a moment (snapped on a seek).
        const float solo = StateOf( index, inSeconds ) == "play_solo" ? 1.f : 0.f;
        const bool seeked = std::fabs( inSeconds - m_lastSeconds ) > 0.5;
        member.Solo = seeked ? solo : member.Solo + ( solo - member.Solo ) * ( 1.f - std::exp( -std::clamp( inDeltaTime, 0.f, 0.1f ) * 3.f ) );
        switch( index )
        {
        case VenueData::Drums: UpdateDrums( member, inSeconds, beat, inCrowdEnergy, inDeltaTime ); break;
        case VenueData::Guitar:
        case VenueData::Bass: UpdateStringed( member, index, inSeconds, beat + ( index == VenueData::Bass ? 0.03 : 0.0 ), inCrowdEnergy ); break;
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
    if( !HasMember( inMember ) ) return VenueLayout::kMemberSpots[std::clamp( inMember, 0, 4 )] + Vector3( 0.f, 1.6f, 0.f );
    const Member& member = m_members[inMember];
    return ToVenue( member.Group ? &member.Group->GetComponent<Transform>() : nullptr, member.Body.HeadCentre() );
}


Vector3 Band::ChestOf( int inMember ) const
{
    if( !HasMember( inMember ) ) return VenueLayout::kMemberSpots[std::clamp( inMember, 0, 4 )] + Vector3( 0.f, 1.3f, 0.f );
    const Member& member = m_members[inMember];
    return ToVenue( member.Group ? &member.Group->GetComponent<Transform>() : nullptr, member.Body.Chest() );
}


Vector3 Band::HandsOf( int inMember ) const
{
    if( !HasMember( inMember ) ) return VenueLayout::kMemberSpots[std::clamp( inMember, 0, 4 )] + Vector3( 0.f, 1.f, 0.f );
    const Member& member = m_members[inMember];
    return ToVenue( member.Group ? &member.Group->GetComponent<Transform>() : nullptr, ( member.Body.Hand( 0 ) + member.Body.Hand( 1 ) ) * 0.5f );
}


Vector3 Band::FeetOf( int inMember ) const
{
    return VenueLayout::kMemberSpots[std::clamp( inMember, 0, 4 )];
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
