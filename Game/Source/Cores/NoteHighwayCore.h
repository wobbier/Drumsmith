#pragma once
#include <ECS/Core.h>
#include <Components/Transform.h>
#include "Events/EventReceiver.h"
#include "CoreGame/TrackList.h"
#include "Components/Audio/AudioSource.h"
#include "CoreGame/AudioPack.h"
#include "Editor/PadBindings.h"
#include "Midi/MidiDevice.h"
#include "Venue/VenueShow.h"
#include "CoreGame/Lyrics.h"
#include <array>
#include <chrono>
#include <map>
#include <memory>
#include <string>
#include <vector>

class RmlUiCore;

// Plays a chart: spawns its notes on the highway, runs the song clock, judges keyboard and MIDI
// hits per lane, mutes the drum stems on a miss, and keeps score in the "in_game" view model
// (Docs/Gameplay-Note-Highway.md).
class NoteHighwayCore final
	: public Core<NoteHighwayCore>
{
public:
	// Hit windows, either side of the note (ms). Anything outside the widest is not a hit.
	static constexpr float kPerfectWindowMs = 30.f;
	static constexpr float kGreatWindowMs = 60.f;
	static constexpr float kGoodWindowMs = 90.f;
	// Silence before the song starts so the first notes can scroll in (ms).
	static constexpr double kLeadInMs = 2000.0;

	NoteHighwayCore();
	~NoteHighwayCore();

	virtual void Init() final;

	virtual void OnEntityAdded( Entity& NewEntity ) final;
	virtual void OnEntityRemoved( Entity& InEntity ) final;

	void OnAddedToWorld() override;
	void OnRemovedFromWorld() override;
	void OnStart() override;
	void OnStop() override;

	virtual void Update( const UpdateContext& context ) final;

	void SetupTrack( TrackData& inTrackData, int inTrackIndex );
	void ShutdownTrack();

	void Pause();
	void Resume();

	std::map<std::string, EntityHandle> m_lanes;
	std::map<PadId, std::string> m_notePrefabs;
	EntityHandle TrackMover;
	TrackData* m_trackData = nullptr;

private:
#if USING( ME_EDITOR )
	virtual void OnEditorInspect() final;
#endif

	enum class Judgement { None, Perfect, Great, Good, Miss };

	// A piece drawn on a gem to show its technique (the rim strip, the open hi-hat's hole, the
	// bell dot), placed relative to the gem in its lane.
	struct Decoration
	{
		EntityHandle Piece;
		Vector3 Offset;
	};

	struct NoteState
	{
		double TimeMs = 0.0;
		EntityHandle Note;
		bool Judged = false;
		PadId Pad = PadId::Invalid;
		Articulation Technique = Articulation::Normal;
		std::vector<Decoration> Decorations;
		// The chart note it was spawned from, to spawn it again when the song is scrubbed back.
		const NoteData* Source = nullptr;
	};

	// A colour for a spawned mesh. Applied once its model has bound: binding rebuilds the material
	// from the prefab's (Mesh::BindModelMesh), which would undo a colour set at spawn.
	struct PendingTint
	{
		EntityHandle Target;
		Vector3 Color;
		Vector3 Emissive;
	};

	// A lane's target pad at the strike bar; it flashes when the lane is hit.
	struct TargetPad
	{
		int Lane = -1;
		EntityHandle Pad;
		Vector3 Color;
		float Flash = 0.f;
	};

	struct BeatLine
	{
		double TimeMs = 0.0;
		EntityHandle Line;
	};

	// One lane's notes in time order; Cursor is the first that might still be judged.
	struct LaneNotes
	{
		std::vector<NoteState> Notes;
		size_t Cursor = 0;
	};

	struct Hit
	{
		PadId Pad = PadId::Invalid;
		Articulation Technique = Articulation::Normal;
		double TimeMs = 0.0;   // Song time the player was hearing when they hit
		// Whether the input says which pad of a shared lane (open vs closed hi-hat) and which
		// stroke it was. A keyboard key knows no stroke; a MIDI note bound to two pads knows
		// neither. Unknown parts are never judged wrong.
		bool PadKnown = true;
		bool TechniqueKnown = true;
	};

	void ApplyPendingTints();
	void UpdateLyrics( RmlUiCore& inUi );
	void SpawnNote( const NoteData& inNote, NoteState& outState );
	void AddDecoration( NoteState& ioState, Transform* inLane, const Vector3& inGemPosition, const Vector3& inOffset, const Vector3& inScale, const Vector3& inColor );
	void HideNote( NoteState& ioNote );
	// One hit per lane among an input's meanings (a MIDI note or key can mean several pads).
	void AddHits( const std::vector<std::pair<PadId, Articulation>>& inMeanings, double inTimeMs, bool inInputKnowsTechnique, std::vector<Hit>& outHits );
	static std::string TechniqueName( PadId inPad, Articulation inTechnique );
	void Tint( const EntityHandle& inTarget, const Vector3& inColor, const Vector3& inEmissive );
	EntityHandle SpawnBox( const Vector3& inPosition, const Vector3& inScale, const Vector3& inColor, const Vector3& inEmissive, Transform* inParent );
	void BuildHighway();
	void BuildBeatLines();
	void UpdateTargetPads( float inDeltaTime );
	void FlashLane( int inLane );
	void ApplySpeed();
	float UnitsPerSecond() const;
	void UpdateSongClock( float inDeltaTime );
	void GatherHits( std::vector<Hit>& outHits );
	void JudgeHit( const Hit& inHit );
	void JudgeMisses( double inJudgeTimeMs );
	void ApplyJudgement( Judgement inJudgement, double inOffsetMs );
	void LayoutLanes();
	void ResetScore();
	void UpdateHud( float inDeltaTime );
	void SetDrumsAudible( bool inAudible );
	// The debug scrubber: the song, the clock and the notes to inTimeMs (notes before it are
	// cleared without counting, notes after it are armed again).
	void SeekTo( double inTimeMs );
	double SongLengthMs() const;
	double JudgeTimeMs() const;
	double VisualTimeMs() const;
	static int LaneOf( PadId inPad );

	AudioPack m_currentTrackPack;
	int m_trackIndex = -1;
	bool m_isPaused = false;

	// The song clock: ms into the song, negative during the lead-in. It runs on frame time and is
	// steered toward FMOD's position, which only moves once per mixer block.
	enum class SongState { Idle, Loading, LeadIn, Playing, Finished };
	SongState m_songState = SongState::Idle;
	double m_songTimeMs = 0.0;
	unsigned int m_lastAudioPositionMs = 0;
	// The gap to FMOD's position still to close, and the smoothed frame step (UpdateSongClock).
	double m_clockErrorMs = 0.0;
	double m_frameStepMs = 0.0;
	std::chrono::steady_clock::time_point m_songClockStamp{};
	double m_lastNoteMs = 0.0;
	double m_firstNoteMs = 0.0;

	std::array<LaneNotes, PadId::COUNT> m_laneNotes;
	float m_laneSpacing = 1.8f;
	float m_highwayWidth = 7.2f;
	bool m_drumsAudible = true;
	std::vector<PendingTint> m_pendingTints;
	// Highway pieces built per chart: surface, dividers and pads move with the camera; beat lines
	// sit in song space like the notes.
	std::vector<EntityHandle> m_highwayParts;
	std::vector<TargetPad> m_targetPads;
	std::vector<BeatLine> m_beatLines;
	float m_kickFlash = 0.f;
	// The highway speed the notes were last placed for (chart NoteSpeed x the player's setting).
	float m_appliedSpeed = 0.f;
	// The venue under the highway: stage, band, crowd, lights and cameras (Docs/Venue-and-Band.md).
	VenueShow m_venueShow;
	// The chart's lyrics for the HUD's karaoke line (Settings > Lyrics), and what it shows now.
	Lyrics m_lyrics;
	std::string m_lyricSung;
	std::string m_lyricRest;
	std::string m_lyricNext;
	float m_venueSwapTimer = 0.f;

	// Score
	int m_score = 0;
	int m_combo = 0;
	int m_maxCombo = 0;
	int m_perfect = 0;
	int m_great = 0;
	int m_good = 0;
	int m_missed = 0;
	int m_wrongTechnique = 0;
	int m_totalNotes = 0;
	std::string m_lastJudgement;
	std::string m_lastTiming;
	std::string m_lastHint;
	float m_judgementAge = 10.f;

	std::unique_ptr<EventSubscription> m_launchTrackSubscription;
	std::unique_ptr<EventSubscription> m_pauseTrackSubscription;
	std::unique_ptr<EventSubscription> m_resumeTrackSubscription;
	std::unique_ptr<EventSubscription> m_seekTrackSubscription;
	// Debug no-fail (the F8 panel, or --no-fail): misses count but cost nothing.
	bool m_noFail = false;
	// Debug autoplay (the F8 panel, or --highway-autoplay): 0 off, 1 perfect, 2 sloppy. Plain:
	// as a kit that only sends plain strokes and one hi-hat note would.
	int m_autoplay = 0;
	bool m_autoplayPlain = false;
	bool m_seekedFromCommandLine = false;
};

ME_REGISTER_CORE( NoteHighwayCore )
