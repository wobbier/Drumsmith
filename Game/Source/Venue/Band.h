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
    // Which way the member's face looks (venue space, unit length).
    Vector3 GazeOf( int inMember ) const;
    Vector3 ChestOf( int inMember ) const;
    Vector3 HandsOf( int inMember ) const;
    Vector3 FeetOf( int inMember ) const;
    // A guitarist's or bassist's instrument in venue space, for the neck camera: the headstock,
    // the middle of the body, the fretboard's facing and the neck's upper edge (toward the
    // player's head). False for anyone without one.
    bool NeckOf( int inMember, Vector3& outHeadstock, Vector3& outBody, Vector3& outFace, Vector3& outEdge ) const;
    bool HasMember( int inMember ) const { return inMember >= 0 && inMember < VenueData::MemberCount && m_members[inMember].Present; }
    // How busy a member is around a time (0 resting, 1 flat out), for the director's choices.
    float Activity( int inMember, double inSeconds ) const;
    std::string StateOf( int inMember, double inSeconds ) const;
    // 0 to 1 a guitarist or bassist leaning into their mic for a singalong, eased around it.
    float AtSingalong( int inMember, double inSeconds ) const;

private:
    using Limb = VenueData::Limb;
    using Piece = VenueData::DrumPiece;
    // The singer's percussion: tambourine, cowbell or clap sections (m_percussion) and their hits.
    enum class Percussion : int { Tambourine = 0, Cowbell, Clap };
    struct PercussionSpan
    {
        float Start = 0.f;
        float End = 0.f;
        Percussion Kind = Percussion::Tambourine;
    };

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
        std::vector<VenueData::SpanData> Frets;   // the fretting hand's position (m_member 0-19)
        std::vector<TimedCueData> Maps;           // "[map ...]": hand and strum maps
        EntityHandle Tambourine;   // the singer's percussion, shown only while playing it
        EntityHandle Cowbell;
        EntityHandle Instrument;   // guitar or bass (a group), the mic for the singer
        float NeckLength = 0.f;    // guitar or bass, for the neck camera
        // The guitar's pose relative to the figure's step (pose.Offset), damped: it hangs on a
        // strap and has weight, so it follows the torso's lean and bob without its jerks.
        // Two cascaded eases (a critically damped follow), the second stage drawn.
        // The guitar on its strap (SwingInstrument): springs on its place and its tilt.
        glm::vec3 GuitarAt{};
        glm::vec3 GuitarVelocity{};
        glm::quat GuitarTilt{ 1.f, 0.f, 0.f, 0.f };
        glm::vec3 GuitarSpin{};    // angular velocity, radians a second about each world axis
        bool GuitarHung = false;   // false: snap on the next swing (first frame, a seek)
        std::array<EntityHandle, 2> Sticks;
        EntityHandle MicStand;
        float Phase = 0.f;         // a per-member offset for idle motion
        float Energy = 0.f;        // eased
        float Solo = 0.f;          // 0 to 1 out front for a play_solo, eased
        Vector3 Spot;
    };

    void BuildDrums( VenueKit& inKit, Member& ioMember );
    void BuildStringed( VenueKit& inKit, Member& ioMember, bool inBass );
    void BuildVocals( VenueKit& inKit, Member& ioMember );
    void BuildKeys( VenueKit& inKit, Member& ioMember );
    void BuildMicStand( VenueKit& inKit, Member& ioMember, const Vector3& inPosition, float inHeight );
    void DeriveStrokes( const std::vector<NoteData>& inNotes );
    void DeriveFallbacks( const std::vector<NoteData>& inNotes );
    void DerivePercussion( const VenueData& inVenue );
    void DeriveHarmonies( const VenueData& inVenue );
    const PercussionSpan* PercussionAt( double inSeconds ) const;
    float PercussionStrike( double inSeconds, double inBeat ) const;

    void UpdateDrums( Member& ioMember, double inSeconds, double inBeat, float inEnergy, float inDeltaTime );
    void UpdateStringed( Member& ioMember, int inIndex, double inSeconds, double inBeat, float inEnergy, float inDeltaTime );
    // Eases a guitar or bass toward where the torso holds it and places it; returns where it is.
    void SwingInstrument( Member& ioMember, const glm::vec3& inOffset, glm::vec3& ioPosition, glm::quat& ioRotation, float inDeltaTime );
    void UpdateVocals( Member& ioMember, double inSeconds, double inBeat, float inEnergy );
    void UpdateKeys( Member& ioMember, double inSeconds, double inBeat, float inEnergy );
    void UpdateKit( float inDeltaTime );

    glm::vec3 StrikePoint( Piece inPiece ) const;
    glm::vec3 StickTip( int inLimb, double inSeconds, float& outLift ) const;
    bool Singing( int inMember, double inSeconds, float* outOpen = nullptr ) const;
    // How far the singer is from the mic (0 at it, 1 out working the stage); outBreak numbers the break.
    float AwayFromMic( double inSeconds, uint32_t* outBreak = nullptr ) const;
    float StrumPhase( const Member& inMember, double inSeconds, int& outCount ) const;

    Transform* m_stage = nullptr;
    std::array<Member, VenueData::MemberCount> m_members;
    std::array<std::vector<Stroke>, 4> m_strokes;       // per limb
    std::array<size_t, 4> m_strokeCursor{};
    std::array<KitPiece, 10> m_kit;                     // by DrumPiece
    std::vector<TimedCueData> m_sections;
    std::vector<VenueData::SpanData> m_vocalNotes;
    std::vector<VenueData::SpanData> m_vocalPhrases;    // the chart's lyric lines (notes 105/106)
    std::vector<VenueData::SpanData> m_singalong;
    std::vector<PercussionSpan> m_percussion;
    std::vector<float> m_percussionHits;
    std::vector<BeatData> m_beats;
    std::vector<float> m_drumTimes;                     // every drum note, for activity
    float m_bpm = 120.f;
    double m_lastSeconds = -1000.0;
    // After the song's [music_end] / [end]: everyone takes the applause.
    float m_endTime = 1e9f;
};
