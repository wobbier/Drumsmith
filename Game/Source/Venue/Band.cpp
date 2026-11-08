#include "Venue/Band.h"
#include "Venue/VenueKit.h"
#include "Venue/VenueLayout.h"
#include "Venue/VenueTiming.h"
#include "Components/Transform.h"
#include "Materials/StandardMaterial.h"
#include <algorithm>
#include <cmath>

namespace
{
    constexpr float kPi = 3.14159265f;
    constexpr float kDeg = kPi / 180.f;
    constexpr float kStickLength = 0.4f;

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

    // Where each piece is struck, in the drummer's space (the throne at the origin, the kit at +z).
    const glm::vec3 kStrike[10] = {
        glm::vec3( 0.12f, 0.06f, 0.5f ),     // Kick (the pedal)
        glm::vec3( -0.42f, 0.99f, 0.42f ),   // HiHat
        glm::vec3( -0.17f, 0.76f, 0.44f ),   // Snare
        glm::vec3( -0.14f, 0.96f, 0.66f ),   // Tom1
        glm::vec3( 0.17f, 0.96f, 0.66f ),    // Tom2
        glm::vec3( 0.47f, 0.68f, 0.42f ),    // FloorTom
        glm::vec3( -0.56f, 1.3f, 0.66f ),    // Crash1
        glm::vec3( 0.52f, 1.34f, 0.72f ),    // Crash2
        glm::vec3( 0.66f, 1.08f, 0.52f ),    // Ride
        glm::vec3( -0.26f, 0.05f, 0.42f ),   // HiHatPedal
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
    m_singalong.clear();
    m_beats.clear();
    m_drumTimes.clear();
    m_stage = nullptr;
    m_lastSeconds = -1000.0;
}


void Band::Build( VenueKit& inKit, Transform* inStage, const VenueData& inVenue, const std::vector<NoteData>& inNotes, const std::vector<BeatData>& inBeats, float inBpm )
{
    Clear();
    m_stage = inStage;
    m_beats = inBeats;
    m_bpm = inBpm;
    m_sections = inVenue.m_sections;
    m_vocalNotes = inVenue.m_vocalNotes;
    m_singalong = inVenue.m_singalong;
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
    drum( Piece::Kick, glm::vec3( 0.f, 0.3f, 0.84f ), 0.6f, 0.44f, Vector3( 90.f, 0.f, 0.f ) );
    inKit.Piece( Shape::Cylinder, Vector3( 0.f, 0.3f, 1.065f ), Vector3( 0.36f, 0.01f, 0.36f ), Vector3( 0.9f, 0.5f, 0.1f ), &group, Vector3( 0.9f, 0.45f, 0.08f ) )
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
    inKit.Box( Vector3( -0.18f - neck * 0.5f, 0.f, 0.02f ), Vector3( neck, 0.05f, 0.03f ), Vector3( 0.25f, 0.15f, 0.07f ), &guitar );
    inKit.Box( Vector3( -0.26f - neck, 0.f, 0.02f ), Vector3( 0.17f, 0.075f, 0.025f ), Vector3( 0.05f, 0.05f, 0.05f ), &guitar );
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
        const float angle = ( 22.f - 110.f * lift[side] ) * kDeg;   // tip down at the stroke, up as it lifts
        const glm::vec3 stick = glm::normalize( toward * std::cos( angle ) - kY * std::sin( angle ) );
        const glm::vec3 hand = tips[side] - stick * kStickLength;
        Puppet::Arm& arm = pose.Arms[side];
        arm.Reach = true;
        arm.Target = hand;
        arm.Pole = glm::vec3( side == 0 ? -0.9f : 0.9f, -1.f, -0.5f );
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
    for( int side = 0; side < 2; ++side )
    {
        if( ioMember.Sticks[side] )
        {
            const glm::vec3 hand = ioMember.Body.Hand( side );
            Puppet::PlaceBone( ioMember.Sticks[side], hand, hand + glm::normalize( tips[side] - hand ) * kStickLength );
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
    const bool solo = state == "play_solo";
    const float t = static_cast<float>( inSeconds );
    const float pulse = Pulse( inBeat );
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
    if( solo )
    {
        // Out front and leaning back into it.
        pose.Lean = -8.f + 4.f * pulse;
        pose.Offset = glm::vec3( inIndex == VenueData::Guitar ? -0.3f : 0.3f, 0.f, 1.1f );
        pose.Nod = -12.f + 10.f * pulse;
    }
    float open = 0.f;
    const bool singing = Singing( inIndex, inSeconds, &open );
    if( singing )
    {
        pose.Mouth = open;
        pose.Lean = 10.f;
        pose.Nod = -6.f;
        pose.Offset = glm::vec3( 0.f, 0.f, 0.12f );
        pose.Turn = 0.f;
    }
    ioMember.Body.Apply( pose );

    // The guitar hangs off the torso, its neck up and to the player's left.
    const glm::quat spine = ioMember.Body.SpineRotation();
    const float neckAngle = solo ? -48.f : ( -24.f - 10.f * energy * pulse );
    const glm::quat guitarRotation = spine * Axis( neckAngle, kZ ) * Axis( -8.f, kY );
    const glm::vec3 guitarPosition = ioMember.Body.SpineBase() + spine * glm::vec3( 0.04f, 0.2f, 0.17f );
    if( ioMember.Instrument )
    {
        Puppet::PlacePiece( ioMember.Instrument, guitarPosition, guitarRotation );
    }
    int count = 0;
    const float strum = idle ? 0.f : StrumPhase( ioMember, inSeconds, count );
    const float fret = VenueTiming::Noise( static_cast<uint32_t>( count / 6 ), static_cast<uint32_t>( inIndex ) );
    const float neck = inIndex == VenueData::Bass ? 0.86f : 0.62f;
    Puppet::Arm& strumArm = pose.Arms[1];
    strumArm.Reach = true;
    strumArm.Target = guitarPosition + guitarRotation * glm::vec3( 0.1f, 0.07f * strum, 0.09f );
    strumArm.Pole = glm::vec3( 1.f, -0.4f, -1.f );
    Puppet::Arm& fretArm = pose.Arms[0];
    fretArm.Reach = true;
    fretArm.Target = guitarPosition + guitarRotation * glm::vec3( -0.25f - neck * ( 0.15f + 0.7f * fret ), -0.03f, 0.05f );
    fretArm.Pole = glm::vec3( -0.3f, -1.f, -0.3f );
    ioMember.Body.Apply( pose );
    (void)inEnergy;
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
    // Away from the mic between lines: wander, and work the crowd.
    const float wander = singing ? 0.f : 1.f;
    ioMember.Energy += ( wander - ioMember.Energy ) * 0.04f;
    const float away = ioMember.Energy;
    pose.Offset = glm::vec3( away * 1.3f * std::sin( t * 0.27f + ioMember.Phase ), 0.f, -away * 0.5f );
    if( intense && !singing )
    {
        // Jumps on the downbeats.
        const double measure = inBeat / 2.0;
        const float hop = static_cast<float>( measure - std::floor( measure ) );
        pose.Offset.y = 0.35f * std::max( 0.f, std::sin( hop * kPi * 2.f ) ) * ( hop < 0.5f ? 1.f : 0.f );
    }
    pose.Mouth = open;
    pose.Lean = singing ? 8.f : 2.f + 6.f * pulse;
    pose.Nod = singing ? -6.f + 3.f * open : 10.f * pulse - 4.f;
    pose.HeadTurn = singing ? 0.f : 30.f * std::sin( t * 0.5f + ioMember.Phase );
    pose.Side = 4.f * std::sin( static_cast<float>( inBeat ) * kPi * 0.5f );
    pose.Legs[0].Spread = 6.f;
    pose.Legs[1].Spread = 6.f;
    ioMember.Body.Apply( pose );

    Puppet::Arm& micArm = pose.Arms[1];
    Puppet::Arm& freeArm = pose.Arms[0];
    if( singing )
    {
        // A hand on the mic; the other one rides the melody.
        micArm.Reach = true;
        micArm.Target = glm::vec3( 0.02f, 1.5f, 0.32f ) - pose.Offset * 0.f;
        micArm.Pole = glm::vec3( 1.f, -1.f, 0.f );
        const float phrase = VenueTiming::Noise( static_cast<uint32_t>( t * 0.5f ), 3u );
        freeArm.Raise = 30.f + 60.f * phrase + 15.f * open;
        freeArm.Spread = 25.f + 20.f * phrase;
        freeArm.Elbow = 40.f;
    }
    else if( intense )
    {
        // Fist pumps on the beat.
        micArm.Raise = 150.f + 25.f * pulse;
        micArm.Spread = 15.f;
        micArm.Elbow = 50.f * ( 1.f - pulse );
        freeArm.Raise = 20.f;
        freeArm.Spread = 20.f;
        freeArm.Elbow = 70.f;
    }
    else
    {
        // Clapping along over their head.
        const float clap = Pulse( inBeat, 4.0 );
        micArm.Raise = freeArm.Raise = 145.f;
        micArm.Spread = freeArm.Spread = 4.f + 22.f * ( 1.f - clap );
        micArm.Elbow = freeArm.Elbow = 25.f;
    }
    ioMember.Body.Apply( pose );
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
