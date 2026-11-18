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
#include "CoreGame/ChartAdvice.h"
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
	// The countdown shows the last this-many ms before the first note (ms).
	static constexpr double kCountdownMs = 3000.0;
	// Resuming from a pause pulls the song back this far and fades it in over kResumeFadeSeconds,
	// so the player gets a run-up instead of the next note at once.
	static constexpr double kResumeRewindMs = 2000.0;
	static constexpr float kResumeFadeSeconds = 1.5f;

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

	// The Track Editor's preview (Docs/Songs-and-DLC.md): the highway and venue of a chart the
	// editor owns, shown at the time the editor gives. No audio, no judging and no input: the
	// editor has the stems, the clock and the MIDI queue. inTrackData must outlive the preview.
	enum PreviewPart : int { PreviewNotes = 1, PreviewBeats = 2, PreviewVenue = 4 };
	void BeginPreview( TrackData& inTrackData );
	void EndPreview();
	bool IsPreviewing() const { return m_songState == SongState::Preview; }
	// Whether the scene's highway has been found (the core has started in a gameplay scene).
	bool CanPreview() const { return static_cast<bool>( TrackMover ); }
	void SetPreviewTime( double inTimeMs );
	// Rebuilds what the editor changed (PreviewPart flags) from the chart as it now stands.
	void RefreshPreview( int inParts );
	void SetPreviewPresentation( VenueShow::Presentation inPresentation ) { m_venueShow.SetPresentation( inPresentation ); }

	std::map<std::string, EntityHandle> m_lanes;
	EntityHandle TrackMover;
	TrackData* m_trackData = nullptr;

private:
#if USING( ME_EDITOR )
	virtual void OnEditorInspect() final;
#endif

	enum class Judgement { None, Perfect, Great, Good, Miss };
	using KickFoot = KickFeet::Foot;

	// A piece drawn on a gem to show its technique (the rim strip, the open hi-hat's hole, the
	// bell dot), placed relative to the gem in its lane.
	struct Decoration
	{
		EntityHandle Piece;
		Vector3 Offset;
		Vector3 Color;
	};

	struct NoteState
	{
		double TimeMs = 0.0;
		EntityHandle Note;
		bool Judged = false;
		// A note judged before a pause, inside the stretch the resume plays again: it shows as a
		// grey gem and isn't judged twice.
		bool Passed = false;
		// Past the Perfect window and not hit yet: its gem is dimmed, but it can still be hit
		// until the Good window closes.
		bool Late = false;
		// The gem's own colour, to dim it from.
		Vector3 Color;
		// Which foot a double bass kick is for (the bar is drawn on that half of the highway).
		KickFoot Foot = KickFoot::Either;
		PadId Pad = PadId::Invalid;
		Articulation Technique = Articulation::Normal;
		std::vector<Decoration> Decorations;
		// The chart note it was spawned from (a copy: the chart may be edited meanwhile), to spawn
		// it again when the song is scrubbed back.
		NoteData Source;
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
		bool Measure = false;
		EntityHandle Line;
	};

	// The stretch of a time-sorted list that has entities: [Begin, End). Only what is on the
	// visible highway is spawned (UpdateWindow).
	struct LiveRange
	{
		size_t Begin = 0;
		size_t End = 0;
	};

	// One lane's notes in time order; Cursor is the first that might still be judged.
	struct LaneNotes
	{
		std::vector<NoteState> Notes;
		size_t Cursor = 0;
		LiveRange Live;
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
	// A missed or already-played note: grey. inGlow lifts it off the black highway (the scene has
	// no lights), for the notes a resume replays.
	void GreyOut( NoteState& ioNote, float inGlow = 0.f );
	void DimLate( NoteState& ioNote );
	// Splits double bass between the feet (NoteState::Foot); call once the kick lane is built.
	void AssignKickFeet();
	// Pulls a paused song back kResumeRewindMs and starts it again, fading in.
	void ResumeWithRunUp();
	// One hit per lane among an input's meanings (a MIDI note or key can mean several pads).
	void AddHits( const std::vector<std::pair<PadId, Articulation>>& inMeanings, double inTimeMs, bool inInputKnowsTechnique, std::vector<Hit>& outHits );
	static std::string TechniqueName( PadId inPad, Articulation inTechnique );
	void Tint( const EntityHandle& inTarget, const Vector3& inColor, const Vector3& inEmissive );
	EntityHandle SpawnBox( const Vector3& inPosition, const Vector3& inScale, const Vector3& inColor, const Vector3& inEmissive, Transform* inParent );
	void BuildHighway();
	void BuildBeatLines();
	// The chart's notes as lane states and gems, and their removal.
	void BuildNotes();
	void ClearNotes();
	void ClearBeatLines();
	void BuildVenue();
	void SpawnBeatLine( BeatLine& ioLine );
	// Spawns the notes and beat lines on the highway seen at inTimeMs (plus a margin ahead, so a gem
	// is coloured before it comes into view) and deletes the ones past its back end. inRecheck also
	// spawns notes inside a range that was already live (notes re-armed by a scrub).
	void UpdateWindow( double inTimeMs, bool inRecheck = false );
	void UpdatePreview( float inDeltaTime );
	void UpdateTargetPads( float inDeltaTime );
	void FlashLane( int inLane );
	void ApplySpeed();
	float UnitsPerSecond() const;
	void UpdateSongClock( float inDeltaTime );
	void GatherHits( std::vector<Hit>& outHits );
	void JudgeHit( const Hit& inHit );
	void JudgeMisses( double inJudgeTimeMs );
	// The delay calibration (CoreGame/Calibration.h): hits are measured against the beat, not judged.
	void CalibrationHits( const std::vector<Hit>& inHits );
	// The Metronome setting: a click stem written from the chart's beat lines, added to the
	// song's stems the first time it is wanted and silenced when it isn't.
	void UpdateMetronome();
	void ApplyJudgement( Judgement inJudgement, double inOffsetMs );
	void LayoutLanes();
	// A lane's width at the strike bar: the lane spacing, slimmer for toms.
	float LaneWidth( PadId inPad ) const;
	// Whether a kit column is drawn: it has notes (toms come as a set of three).
	bool ShowsColumn( PadId inPad ) const;
	void ResetScore();
	// Accuracy so far, 0 to 100: perfect counts whole, great 3/4, good half, a miss nothing.
	double Accuracy() const;
	// The song or lesson is over: writes its result to PlayerProfile, and what it changed to the
	// results screen. Calibration, autoplay, no-fail and skipped-ahead runs aren't recorded (--record-autoplay
	// records autoplay, for headless checks).
	void RecordResult();
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
	enum class SongState { Idle, Loading, LeadIn, Playing, Finished, Preview };
	SongState m_songState = SongState::Idle;
	double m_songTimeMs = 0.0;
	unsigned int m_lastAudioPositionMs = 0;
	// The gap to FMOD's position still to close, and the smoothed frame step (UpdateSongClock).
	double m_clockErrorMs = 0.0;
	double m_frameStepMs = 0.0;
	std::chrono::steady_clock::time_point m_songClockStamp{};
	double m_lastNoteMs = 0.0;
	double m_firstNoteMs = 0.0;
	// What the countdown counts in to: the first note, or the chart's start marker when that
	// comes first (TrackData::m_startTime).
	double m_countInMs = 0.0;

	std::array<LaneNotes, PadId::COUNT> m_laneNotes;
	float m_laneSpacing = 1.8f;
	float m_highwayWidth = 7.2f;
	// Lane divider x positions, left edge to right edge (tom lanes are narrower).
	std::vector<float> m_columnEdges;
	bool m_drumsAudible = true;
	std::vector<PendingTint> m_pendingTints;
	// Highway pieces built per chart: surface, dividers and pads move with the camera; beat lines
	// sit in song space like the notes.
	std::vector<EntityHandle> m_highwayParts;
	std::vector<TargetPad> m_targetPads;
	std::vector<BeatLine> m_beatLines;
	LiveRange m_beatLive;
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
	// The hits' offsets from their notes (ms, late positive), for the results' average timing.
	double m_offsetSumMs = 0.0;
	int m_offsetCount = 0;
	std::string m_lastJudgement;
	// The results screen's line about the profile: a new best, a full combo, a lesson passed, or
	// the standing bests; empty when nothing was recorded.
	std::string m_resultNews;
	std::string m_resultBests;
	// What the run unlocked (Progression::Evaluate), a line each.
	std::string m_resultUnlocks;
	// A gig's last song: how the set went.
	std::string m_resultGig;
	// The player seeked forward this run (the debug scrubber, --seek): its result isn't recorded.
	bool m_skippedAhead = false;
	std::string m_lastTiming;
	std::string m_lastHint;
	float m_judgementAge = 10.f;

	std::unique_ptr<EventSubscription> m_launchTrackSubscription;
	std::unique_ptr<EventSubscription> m_pauseTrackSubscription;
	std::unique_ptr<EventSubscription> m_resumeTrackSubscription;
	std::unique_ptr<EventSubscription> m_seekTrackSubscription;
	// Debug no-fail (the F8 panel, or --no-fail): misses count but cost nothing.
	bool m_noFail = false;
	// Playing the calibration's chart: the latency settings are left out (they are what is being
	// measured), and hits go to Calibration instead of the judge.
	bool m_calibrating = false;
	double m_lastTapMs = -1e9;
	double m_autoTapsToMs = -1e9;
	bool m_metronomeTried = false;
	// Debug autoplay (the F8 panel, or --highway-autoplay): 0 off, 1 perfect, 2 sloppy. Plain:
	// as a kit that only sends plain strokes and one hi-hat note would.
	int m_autoplay = 0;
	bool m_autoplayPlain = false;
	bool m_seekedFromCommandLine = false;
	// The preview's time last frame, to tell playing on from a scrub.
	double m_previewLastMs = 0.0;
	// The preview's notes need re-arming from the playhead (a fresh build), as after a scrub.
	bool m_previewRearm = true;
};

ME_REGISTER_CORE( NoteHighwayCore )
