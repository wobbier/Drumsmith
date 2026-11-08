#pragma once
#include "CoreGame/TrackList.h"
#include "Venue/Puppet.h"
#include "ECS/EntityHandle.h"
#include <array>
#include <string>
#include <vector>

class Transform;
class VenueKit;

// The band on stage (Docs/Venue-and-Band.md): a drummer whose sticks land on the chart's notes
// (the PART DRUMS animation notes when the chart has them), a guitarist and bassist strumming
// their parts, a singer working the mic through the sung notes, and a keyboard player when the
// song has keys. Each member's state ("idle", "play", "mellow", "intense", "play_solo") comes from
// its PART track, or from the song's sections and notes when the chart has none.
class Band
{
public:
    void Build( VenueKit& inKit, Transform* inStage, const VenueData& inVenue, const std::vector<NoteData>& inNotes, const std::vector<BeatData>& inBeats, float inBpm );
    void Clear();
    void Update( double inSeconds, float inDeltaTime, float inCrowdEnergy );

    // Venue-space points for the director and the lights: a member's head, chest and hands.
    Vector3 HeadOf( int inMember ) const;
    Vector3 ChestOf( int inMember ) const;
    Vector3 HandsOf( int inMember ) const;
    Vector3 FeetOf( int inMember ) const;
    bool HasMember( int inMember ) const { return inMember >= 0 && inMember < VenueData::MemberCount && m_members[inMember].Present; }
    // How busy a member is around a time (0 resting, 1 flat out), for the director's choices.
    float Activity( int inMember, double inSeconds ) const;
    std::string StateOf( int inMember, double inSeconds ) const;

private:
    using Limb = VenueData::Limb;
    using Piece = VenueData::DrumPiece;

    struct Stroke
    {
        float Time = 0.f;
        Piece Target = Piece::Snare;
        bool Soft = false;
    };

    struct KitPiece
    {
        EntityHandle Entity;
        Vector3 Rest;          // its rotation (euler degrees) at rest
        float Wobble = 0.f;    // cymbals swing after a hit, drums squash
        bool Cymbal = false;
        Vector3 Scale;
    };

    struct Member
    {
        bool Present = false;
        EntityHandle Group;    // at the member's spot, facing the crowd
        Puppet Body;
        Puppet::Pose Pose;
        std::vector<TimedCueData> States;
        std::vector<float> Strums;
        EntityHandle Instrument;   // guitar or bass (a group), the mic for the singer
        std::array<EntityHandle, 2> Sticks;
        EntityHandle MicStand;
        float Phase = 0.f;         // a per-member offset for idle motion
        float Energy = 0.f;        // eased
        Vector3 Spot;
    };

    void BuildDrums( VenueKit& inKit, Member& ioMember );
    void BuildStringed( VenueKit& inKit, Member& ioMember, bool inBass );
    void BuildVocals( VenueKit& inKit, Member& ioMember );
    void BuildKeys( VenueKit& inKit, Member& ioMember );
    void BuildMicStand( VenueKit& inKit, Member& ioMember, const Vector3& inPosition, float inHeight );
    void DeriveStrokes( const std::vector<NoteData>& inNotes );
    void DeriveFallbacks( const std::vector<NoteData>& inNotes );

    void UpdateDrums( Member& ioMember, double inSeconds, double inBeat, float inEnergy, float inDeltaTime );
    void UpdateStringed( Member& ioMember, int inIndex, double inSeconds, double inBeat, float inEnergy );
    void UpdateVocals( Member& ioMember, double inSeconds, double inBeat, float inEnergy );
    void UpdateKeys( Member& ioMember, double inSeconds, double inBeat, float inEnergy );
    void UpdateKit( float inDeltaTime );

    glm::vec3 StrikePoint( Piece inPiece ) const;
    glm::vec3 StickTip( int inLimb, double inSeconds, float& outLift ) const;
    bool Singing( int inMember, double inSeconds, float* outOpen = nullptr ) const;
    float StrumPhase( const Member& inMember, double inSeconds, int& outCount ) const;

    Transform* m_stage = nullptr;
    std::array<Member, VenueData::MemberCount> m_members;
    std::array<std::vector<Stroke>, 4> m_strokes;       // per limb
    std::array<size_t, 4> m_strokeCursor{};
    std::array<KitPiece, 10> m_kit;                     // by DrumPiece
    std::vector<TimedCueData> m_sections;
    std::vector<VenueData::SpanData> m_vocalNotes;
    std::vector<VenueData::SpanData> m_singalong;
    std::vector<BeatData> m_beats;
    std::vector<float> m_drumTimes;                     // every drum note, for activity
    float m_bpm = 120.f;
    double m_lastSeconds = -1000.0;
};
