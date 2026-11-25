#pragma once
#include "CoreGame/TrackList.h"
#include "Venue/Performer.h"
#include "ECS/EntityHandle.h"
#include <array>
#include <memory>
#include <string>
#include <vector>

class Transform;
namespace Moonlight { class Material; }
class VenueKit;
struct VenuePlan;

// The band on stage (Docs/Venue-and-Band.md): a drummer whose sticks land on the chart's notes
// (the PART DRUMS animation notes when the chart has them), a guitarist and bassist strumming
// their parts, a singer working the mic through the sung notes, and a keyboard player when the
// song has keys. Each member's state ("idle", "play", "mellow", "intense", "play_solo") comes from
// its PART track, or from the song's sections and notes when the chart has none.
class Band
{
public:
    // inPlan: where each member stands and faces, and who's there at all (VenuePlan::Spot).
    void Build( VenueKit& inKit, Transform* inStage, const VenuePlan& inPlan, const VenueData& inVenue, const std::vector<NoteData>& inNotes, const std::vector<BeatData>& inBeats, float inBpm );
    void Clear();
    // When 0 or more, the cast (each member's character and skin) is this one whatever the song,
    // instead of a different cast every song. The hideout's drummer is always the player's.
    int CastSeed = -1;
    // The characters (People::kPeople indices) no member on stage is: the crowd's.
    std::vector<int> SpareModels() const;
    void Update( double inSeconds, float inDeltaTime, float inCrowdEnergy );
    // Story mode's hold on the band (VenueShow's band_ story flags). The pose moves each member,
    // instrument and all, off their spot: Hidden (gone: posed figures stand in), Falling
    // (tumbling, each their own way), Rising (lifted off the floor and away), Down (on their
    // backs), Floating (drifting and bobbing in place). A fall that lasts turns into a dive: once
    // the tumble is over everyone but the drummer goes head first, the amps and wedges tumble
    // loose beside them, the mic stands are gone and the singer has a mic in hand. inTo has held
    // inToSeconds; it blends in
    // from inFrom (held inFromSeconds when inTo came) by inBlend, 0 to 1. inGhost 0 to 1 turns
    // them see-through and pale, glowing: a ghost of themselves. Reach and Shield are Aloft
    // with the singer's free hand at work: up toward the light overhead, the fingers spread
    // (Reach), then brought across in front of the eyes against it (Shield).
    enum class StoryPose : int { Playing = 0, Hidden, Falling, Rising, Down, Floating, Aloft, Reach, Shield };
    void SetStoryState( StoryPose inFrom, float inFromSeconds, StoryPose inTo, float inToSeconds, float inBlend, float inGhost );
    // A member's spot on something that moves (a trailer on its hitch, a truck on the road):
    // where its marker is now (venue space) and how far it has turned since the scene was read.
    // The member and their gear go with it, and their body rides it on a spring: a jolt of the
    // deck throws them a little off it and they come down again, swaying against the lurch.
    void Carry( int inMember, const Vector3& inFeet, const glm::quat& inTurn, float inDeltaTime );
    // The member's character and clothes as cast for this song (a VenueFigure dressed as them).
    bool LookOf( int inMember, std::string& outModel, std::string& outSkin ) const;

    // Venue-space points for the director and the lights: a member's head, chest and hands (for
    // a member who isn't there, points over their spot).
    Vector3 HeadOf( int inMember ) const;
    // Which way the member's face looks (venue space, unit length).
    Vector3 GazeOf( int inMember ) const;
    Vector3 ChestOf( int inMember ) const;
    Vector3 HandsOf( int inMember ) const;
    // Where their feet stand: their spot, and as far over it as a story pose has the band lifted.
    Vector3 FeetOf( int inMember ) const;
    // How far off the floor a story pose has the band (0 on it): the director's floor-placed
    // cameras ride up with them.
    float Lift() const;
    // The band are ghosts (see-through: they write no depth, so a lens focused on them can't be).
    bool Ghosted() const { return m_ghost > 0.f; }
    // A guitarist's or bassist's instrument in venue space, for the neck camera: the headstock,
    // the middle of the body, the fretboard's facing and the neck's upper edge (toward the
    // player's head). False for anyone without one.
    bool NeckOf( int inMember, Vector3& outHeadstock, Vector3& outBody, Vector3& outFace, Vector3& outEdge ) const;
    // Every member's body has loaded and can be posed (Performer::IsReady).
    bool BodiesReady();
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
        // What stands on the floor at their spot (kit, rug, amp, wedges, mic stand, keyboard): a
        // sibling of Group in the same frame. It stays down when they rise and isn't there
        // while they float (SetStoryState).
        EntityHandle Backline;
        // The gear that comes loose in a fall (amps, wedges): each tumbles its own way beside
        // them (SetStoryState), from where it stands in the backline.
        struct LoosePiece
        {
            EntityHandle Entity;
            Vector3 Rest;
            glm::quat Turn{ 1.f, 0.f, 0.f, 0.f };
            float Seed = 0.f;
        };
        std::vector<LoosePiece> Loose;
        EntityHandle HandMic;      // the singer's, in their hand while in the air (hidden otherwise)
        EntityHandle Rug;          // the drummer's: it stays behind when the kit leaves the floor
        Performer Body;
        int Model = -1;            // which character (People::kPeople)
        Performer::Pose Pose;
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
        Vector3 Spot;              // the plan's, whether they're there or not (where Carry has it)
        float Yaw = 180.f;
        float SeatHeight = 0.f;
        bool PowerStance = false;
        bool Gear = true;
        std::string Skin;          // the atlas they wear
        // Carried (Carry): the spot's turn since the scene was read, and the spring between the
        // deck and the body: how far the body is off its spot, and its own velocity.
        bool Carried = false;
        glm::quat CarryTurn{ 1.f, 0.f, 0.f, 0.f };
        glm::vec3 Jolt{ 0.f };
        glm::vec3 JoltVelocity{ 0.f };
        // Standing on what carries them (not seated, not the drummer): the feet stay planted on
        // the deck and the throw goes into the body above them (CarryPose), in their own space,
        // and the degrees it tips them forward and to their right.
        bool Planted = false;
        glm::vec3 Thrown{ 0.f };
        float ThrownLean = 0.f;
        float ThrownSide = 0.f;
    };
    // A carried member's group and backline placed on their spot, the body off it by the spring.
    void PlaceCarried( int inIndex );

    void BuildDrums( VenueKit& inKit, Member& ioMember );
    void BuildStringed( VenueKit& inKit, Member& ioMember, bool inBass );
    void BuildVocals( VenueKit& inKit, Member& ioMember );
    void BuildKeys( VenueKit& inKit, Member& ioMember );
    void BuildMicStand( VenueKit& inKit, Member& ioMember, const Vector3& inPosition, float inHeight );
    void DeriveStrokes( const std::vector<NoteData>& inNotes );
    // Which crash each crash note is, for a chart that doesn't say (ioPieces: inNotes' pieces).
    void ChooseCrashes( const std::vector<const NoteData*>& inNotes, std::vector<Piece>& ioPieces ) const;
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
    // A fall's dive (m_dive) laid over a playing pose, before the body stands in it: the back
    // arched, the head up to see where they're going, the legs trailing and kicking.
    // A planted carried member's throw (PlaceCarried) put into their pose: the body off the feet.
    void CarryPose( const Member& inMember, Performer::Pose& ioPose ) const;
    void DivePose( const Member& inMember, Performer::Pose& ioPose, bool inKeepLean ) const;
    // Hanging aloft (m_aloft), laid over a playing pose before DivePose: nothing under the feet,
    // so the legs dangle and tread the air slowly, each out of step with the other.
    void FloatPose( const Member& inMember, Performer::Pose& ioPose ) const;

    // Where a piece is struck (the drummer's space): its middle, or where a hand's (0 left, 1
    // right) stick lands on it.
    glm::vec3 StrikePoint( Piece inPiece, int inHand = -1 ) const;
    glm::vec3 StickTip( int inLimb, double inSeconds, float& outLift ) const;
    bool Singing( int inMember, double inSeconds, float* outOpen = nullptr ) const;
    // How far the singer is from the mic (0 at it, 1 out working the stage); outBreak numbers the break.
    float AwayFromMic( double inSeconds, uint32_t* outBreak = nullptr ) const;
    float StrumPhase( const Member& inMember, double inSeconds, int& outCount ) const;

    Transform* m_stage = nullptr;
    std::array<Member, VenueData::MemberCount> m_members;
    // SetStoryState's ghost as last applied, and each material's own look to go back to.
    struct GhostedMaterial
    {
        std::weak_ptr<Moonlight::Material> Material;
        Vector3 Emissive;
        float Opacity = 1.f;
        bool Transparent = false;
        float Rim = 0.f;
        bool Shell = false;
        // The singer's own (their body, not what they play): backlit through Free Bird's plea.
        bool Singer = false;
    };
    std::vector<GhostedMaterial> m_ghosted;
    // How far the singer is a dark shape against the light (the plea's hand up into it, 0 to 1),
    // as last applied.
    float m_backlit = 0.f;
    // A member's group placed for a story pose (position, euler rotation, scale).
    void StoryPlacement( int inIndex, StoryPose inPose, float inSeconds, Vector3& outPosition, Vector3& outRotation, float& outScale, bool inBackline = false ) const;
    // Adds the StandardMaterials under inRoot that m_ghosted doesn't have yet; true if any were new.
    bool GatherGhosted( Transform& inRoot, bool inSinger = false );
    float m_ghost = 0.f;
    // SetStoryState has the band (it places the members from then on).
    bool m_storied = false;
    // SetStoryState's fall as last set: how much of the band's hold is Falling (0 to 1), how long
    // the fall has lasted, and how far into the dive they are (0 the tumble, 1 head first).
    float m_fall = 0.f;
    float m_fallSeconds = 0.f;
    float m_dive = 0.f;
    float m_air = 0.f;          // how far the band is in the air with its gear (a fall, or aloft)
    // How far the band hangs aloft (StoryPose Aloft, Reach, Shield), 0 to 1: the legs float
    // (FloatPose) on the song's clock (m_poseSeconds, set each Update).
    float m_aloft = 0.f;
    float m_poseSeconds = 0.f;
    // The singer's plea (StoryPose Reach, Shield) as last set: how far the free hand is up toward
    // the light (0 to 1), how far it has come across the eyes, and how long the pose has held.
    float m_reach = 0.f;
    float m_shield = 0.f;
    float m_reachSeconds = 0.f;
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
