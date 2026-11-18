#include <Cores/NoteHighwayCore.h>
#include <Components/Transform.h>
#include "Events/GameEvents.h"
#include "CoreGame/TrackList.h"
#include "Engine/World.h"
#include "Components/NoteTrigger.h"
#include "Core/Assert.h"
#include "Core/CommandLine.h"
#include "Engine/Engine.h"
#include "Editor/PadBindings.h"
#include "Mathf.h"
#include "Cores/SceneCore.h"
#include "Cores/UI/RmlUiCore.h"
#include "Components/Graphics/Mesh.h"
#include "Materials/StandardMaterial.h"
#include "CoreGame/CustomTrackDefineTest.h"
#include "Config/GameSettings.h"
#include "Config/PlayerProfile.h"
#include "CoreGame/Progression.h"
#include "CoreGame/GigSession.h"
#include "CoreGame/Practice.h"
#include "CoreGame/Calibration.h"
#include "CoreGame/ClickTrack.h"
#include "ECS/Core.h"
#include <algorithm>
#include <cmath>
#include <cstdio>

namespace
{
    constexpr const char* kModel = "in_game";
    // Lanes left to right, as a kit sits in front of the drummer. The hi-hat's open and closed
    // notes share a column (and either pad hits either), and the kick is a bar across all of them.
    // The hi-hat pedal has no column: its notes are low bars in the hi-hat's.
    constexpr PadId kColumnOrder[] = { PadId::Crash1, PadId::ClosedHiHat, PadId::Splash, PadId::Snare, PadId::HighTom, PadId::MidTom, PadId::FloorTom, PadId::Ride, PadId::Crash2, PadId::China };
    // The widest the lanes may get at the strike bar (world units), and the most room one lane takes.
    constexpr float kMaxHighwayWidth = 8.f;
    constexpr float kMaxLaneSpacing = 1.8f;
    // Tom lanes are this much of a full lane: toms are the plainest notes to read, and slimmer
    // tom columns keep a full kit's highway from sprawling.
    constexpr float kTomLaneScale = 0.7f;
    bool IsTom( PadId inPad )
    {
        return inPad == PadId::HighTom || inPad == PadId::MidTom || inPad == PadId::FloorTom;
    }
    // Width at scale 1 of the unit cube the strike bar (Example.lvl's "Bar") uses. The note models
    // are one unit wide too (Tools/NoteAssets/build.py).
    constexpr float kBarMeshWidth = 1.f;
    // Steering the song clock toward FMOD's position: how long the clock takes to close the gap
    // (a time constant, spread over the frames between mixer updates rather than stepped at
    // each one), and the error past which the clock jumps (a hitch, a seek).
    constexpr double kClockCorrectionSeconds = 0.1;
    constexpr double kClockSnapMs = 120.0;
    // MIDI hits older than this when read are judged as if they arrived this long ago.
    constexpr double kMaxInputAgeMs = 250.0;
    // The note models (Tools/NoteAssets/build.py): one unit wide with their base at y = 0, so a
    // note's scale is its width, and 1 in height and depth is the size they were drawn at.
    constexpr const char* kDrumGemPrefab = "Assets/Prefabs/Notes/DrumGem.prefab";
    constexpr const char* kCymbalPrefab = "Assets/Prefabs/Notes/CymbalGem.prefab";
    constexpr const char* kOpenHiHatPrefab = "Assets/Prefabs/Notes/CymbalRing.prefab";
    constexpr const char* kKickPrefab = "Assets/Prefabs/Notes/KickBar.prefab";
    // Where each model's top is, and how deep its top is front to back (for the technique markings).
    constexpr float kGemTop = 0.29f;
    constexpr float kGemTopDepth = 0.2f;
    constexpr float kCymbalBellTop = 0.18f;
    constexpr float kCymbalBowTop = 0.06f;
    constexpr float kCymbalDepth = 0.5f;
    // Heights above the lane (the highway's surface is at -0.06). The kick lies on the surface, the
    // drums stand on it with the kick's top level with their base, and the cymbals float over both.
    constexpr float kKickBase = -0.055f;
    constexpr float kGemBase = -0.05f;
    constexpr float kCymbalBase = 0.05f;
    // A note's colour is its glow: the models' textures leave only the pale base to the material's
    // own colour (kNoteTrim), and the rest to the emissive colour (the scene has no lights).
    constexpr float kNoteTrim = 0.85f;
    constexpr float kGemGlow = 1.f;
    constexpr float kGhostGlow = 0.6f;
    constexpr float kAccentGlow = 1.3f;
    // Highway pieces (world units): the surface runs this far ahead of the strike bar.
    constexpr float kHighwayLength = 120.f;
    constexpr float kHighwayBehind = 6.f;
    constexpr float kPadFlashSeconds = 0.15f;
    constexpr const char* kHighwayBoxPrefab = "Assets/Prefabs/Highway/HighwayBox.prefab";
    // A note past the Perfect window but still hittable keeps this much of its base and glow.
    constexpr float kLateDim = 0.4f;
    constexpr float kLateGlow = 0.45f;
    // A missed note's grey.
    constexpr float kMissedGlow = 0.25f;
    // Ghost notes are smaller and dimmer, accents taller and brighter.
    constexpr uint8_t kGhostVelocity = 40;
    constexpr uint8_t kAccentVelocity = 120;


    // The lane colour pushed away from grey: a note shows its colour as a glow, where a pale
    // colour (the hi-hat's yellow) would read as a dull one.
    Vector3 Vivid( const Vector3& inColor )
    {
        const float luma = inColor.x * 0.3f + inColor.y * 0.59f + inColor.z * 0.11f;
        const auto push = [luma]( float inChannel ) { return std::clamp( luma + ( inChannel - luma ) * 1.5f, 0.f, 1.f ); };
        return Vector3( push( inColor.x ), push( inColor.y ), push( inColor.z ) );
    }


    int Multiplier( int inCombo )
    {
        return std::min( 4, 1 + inCombo / 10 );
    }
}


NoteHighwayCore::NoteHighwayCore()
    : Base( ComponentFilter().Requires<Transform>().Requires<NoteTrigger>() )
{
}


NoteHighwayCore::~NoteHighwayCore()
{
}


void NoteHighwayCore::Init()
{
}


void NoteHighwayCore::OnAddedToWorld()
{
    m_launchTrackSubscription = EventSubscription::Create<LaunchPlayTrackEvent>( [this]( const LaunchPlayTrackEvent& event ) {
        auto& tracks = TrackDatabase::GetInstance().m_trackList.m_tracks;
        if( event.TrackID == Practice::kTrackId )
        {
            // A practice lesson: its chart is the session's, not a library song.
            if( Practice::GetInstance().IsActive() )
            {
                SetupTrack( Practice::GetInstance().Chart(), -1 );
            }
        }
        else if( event.TrackID == Calibration::kTrackId )
        {
            if( Calibration::GetInstance().IsActive() )
            {
                SetupTrack( Calibration::GetInstance().Chart(), -1 );
            }
        }
        else if( event.TrackIndex >= 0 && event.TrackIndex < static_cast<int>( tracks.size() ) )
        {
            SetupTrack( tracks[event.TrackIndex], event.TrackIndex );
        }
        return true;
    } );
    m_pauseTrackSubscription = EventSubscription::Create<InGamePauseCurrentTrack>( [this]( const InGamePauseCurrentTrack& ) {
        Pause();
    } );
    m_resumeTrackSubscription = EventSubscription::Create<InGameResumeCurrentTrack>( [this]( const InGameResumeCurrentTrack& ) {
        Resume();
    } );
    m_seekTrackSubscription = EventSubscription::Create<InGameSeekTrack>( [this]( const InGameSeekTrack& inEvent ) {
        SeekTo( static_cast<double>( inEvent.Fraction ) * SongLengthMs() );
    } );
    MidiDevice::GetInstance().OpenMidiDevice( GameSettings::GetInstance().PreferredMidiDevice );
    // Every HUD value exists before the document loads, so it never reloads for one.
    ResetScore();
}


void NoteHighwayCore::OnRemovedFromWorld()
{
    m_launchTrackSubscription.reset();
    m_pauseTrackSubscription.reset();
    m_resumeTrackSubscription.reset();
    m_seekTrackSubscription.reset();
}


void NoteHighwayCore::OnStop()
{
    m_currentTrackPack.Stop();
}


void NoteHighwayCore::OnEntityAdded( Entity& NewEntity )
{
}


void NoteHighwayCore::OnEntityRemoved( Entity& InEntity )
{
}


void NoteHighwayCore::OnStart()
{
    m_lanes.clear();

    SceneCore* scene = static_cast<SceneCore*>( GetWorld().GetCore( SceneCore::GetTypeId() ) );
    Transform* root = scene ? scene->GetRootTransform() : nullptr;
    const auto find = [root]( const char* inName ) -> EntityHandle {
        Transform* child = root ? root->GetChildByName( inName ) : nullptr;
        if( !child )
        {
            YIKES( std::string( "NoteHighwayCore: the scene has no '" ) + inName + "' entity" );
            return {};
        }
        return child->Parent;
    };
    // Scene entity names; the map is keyed by the charts' lane names (PadUtils::GetPadId).
    m_lanes["open_hh"] = find( "open_hh" );
    m_lanes["closed_hh"] = find( "closed_hh" );
    m_lanes["snare1"] = find( "Snare1" );
    m_lanes["crash1"] = find( "Crash1" );
    m_lanes["crash2"] = find( "crash2" );
    m_lanes["bass1"] = find( "Bass1" );
    m_lanes["ride1"] = find( "ride1" );
    m_lanes["tom1"] = find( "tom1" );
    m_lanes["tom2"] = find( "tom2" );
    m_lanes["tom3"] = find( "tom3" );
    TrackMover = find( "TrackMover" );
    // Pads the scene predates get a lane entity of their own.
    for( PadId pad : { PadId::HiHatPedal, PadId::Splash, PadId::China } )
    {
        const char* lane = PadUtils::GetPadId( pad );
        Transform* existing = root ? root->GetChildByName( lane ) : nullptr;
        if( existing )
        {
            m_lanes[lane] = existing->Parent;
            continue;
        }
        EntityHandle entity = GetWorld().CreateEntity( lane );
        if( entity )
        {
            entity->AddComponent<Transform>( lane );
            m_lanes[lane] = entity;
        }
    }

    // --play-track <index> starts a track straight away (a gameplay scene opened on its own).
    if( CommandLine::Has( "--play-track" ) && !m_trackData )
    {
        const int index = CommandLine::GetInt( "--play-track", 0 );
        auto& tracks = TrackDatabase::GetInstance().m_trackList.m_tracks;
        if( index >= 0 && index < static_cast<int>( tracks.size() ) )
        {
            SetupTrack( tracks[index], index );
        }
    }
    // --practice <lesson index> [--practice-bpm <bpm>] starts a practice lesson the same way.
    if( CommandLine::Has( "--practice" ) && !m_trackData )
    {
        Practice& practice = Practice::GetInstance();
        const int lesson = CommandLine::GetInt( "--practice", 0 );
        const int bpm = lesson >= 0 && lesson < static_cast<int>( practice.Lessons().size() ) ? practice.Lessons()[lesson].Bpm : 80;
        if( practice.Begin( lesson, CommandLine::GetInt( "--practice-bpm", bpm ), 8 ) )
        {
            SetupTrack( practice.Chart(), -1 );
        }
    }
    // --calibrate starts the delay calibration; with --highway-autoplay <ms> every beat of both
    // parts is hit that late, so the results should read that many ms.
    if( CommandLine::Has( "--calibrate" ) && !m_trackData && Calibration::GetInstance().Begin() )
    {
        SetupTrack( Calibration::GetInstance().Chart(), -1 );
    }
}


int NoteHighwayCore::LaneOf( PadId inPad )
{
    return inPad == PadId::OpenHiHat ? static_cast<int>( PadId::ClosedHiHat ) : static_cast<int>( inPad );
}


void NoteHighwayCore::SetupTrack( TrackData& inTrackData, int inTrackIndex )
{
    ShutdownTrack();
    m_trackData = &inTrackData;
    m_trackIndex = inTrackIndex;

    // A library song's notes are on disk; a practice lesson's chart (and the calibration's) was
    // built in memory.
    if( !inTrackData.m_practice && !inTrackData.m_calibration )
    {
        inTrackData.LoadNoteData();
    }
    m_calibrating = inTrackData.m_calibration;
    m_lastTapMs = m_autoTapsToMs = -1e9;
    BuildNotes();
    if( CommandLine::Has( "--highway-log" ) )
    {
        BRUH_FMT( "Highway: playing %s (track %d)", inTrackData.m_trackName.c_str(), inTrackIndex );
    }

    BuildHighway();
    // The calibration's Listen part has nothing to watch: no beat lines crossing the bar.
    if( !m_calibrating )
    {
        BuildBeatLines();
    }
    // A play: the venue's ambience (a crowd waiting) runs through the load and count-in.
    m_venueShow.SetAmbienceWanted( true );
    BuildVenue();

    m_currentTrackPack = AudioPack( inTrackData );
    m_metronomeTried = false;
    UpdateMetronome();
    ResetScore();
    m_songState = SongState::Loading;
    // At least kLeadInMs of silence, and enough that a song whose drums come in straight away still
    // gets a full countdown before its first note.
    m_songTimeMs = -std::max( kLeadInMs, kCountdownMs - m_countInMs );
    m_isPaused = false;
    if( RmlUiCore* ui = GetEngine().RmlUi )
    {
        ui->ModelSetString( kModel, "track_title", inTrackData.m_trackName );
        ui->ModelSetString( kModel, "track_artist", inTrackData.m_artistName );
        ui->ModelSetNumber( kModel, "track_index", inTrackIndex );
        ui->ModelSetNumber( kModel, "total_notes", m_totalNotes );
        ui->ModelSetNumber( kModel, "practice", inTrackData.m_practice );
    }
    m_lyrics.Clear();
    // A lesson's sticking is its lyric line, whatever the lyrics setting says.
    if( GameSettings::GetInstance().LyricsOnHud() || inTrackData.m_practice )
    {
        m_lyrics.Build( inTrackData.m_venue.m_lyrics, inTrackData.m_venue.m_vocalPhrases, inTrackData.m_venue.m_vocalNotes );
    }
    m_lyricSung.clear();
    m_lyricRest.clear();
    m_lyricNext.clear();
}


void NoteHighwayCore::BuildVenue()
{
    if( TrackMover && m_trackData )
    {
        Transform& mover = TrackMover->GetComponent<Transform>();
        Transform* camera = mover.GetChildByName( "Main Camera" );
        m_venueShow.Build( GetWorld(), *m_trackData, camera ? camera->Parent : EntityHandle() );
    }
}


void NoteHighwayCore::BuildNotes()
{
    TrackData& inTrackData = *m_trackData;
    for( const NoteData& note : inTrackData.m_noteData )
    {
        if( note.m_editorLane >= 0 && note.m_editorLane < PadId::COUNT )
        {
            NoteState state;
            state.TimeMs = static_cast<double>( note.m_triggerTime ) * 1000.0;
            state.Pad = note.m_editorLane;
            state.Technique = note.m_articulation;
            m_laneNotes[LaneOf( note.m_editorLane )].Notes.push_back( state );
        }
    }
    LayoutLanes();

    std::array<size_t, PadId::COUNT> nextInLane{};
    for( auto& laneNotes : m_laneNotes )
    {
        std::sort( laneNotes.Notes.begin(), laneNotes.Notes.end(), []( const NoteState& a, const NoteState& b ) { return a.TimeMs < b.TimeMs; } );
    }

    m_lastNoteMs = 0.0;
    m_firstNoteMs = 1e12;
    m_appliedSpeed = UnitsPerSecond();
    m_totalNotes = 0;
    // Match each NoteState to its chart note, in time order per lane. Gems are spawned later, as
    // the highway reaches them (UpdateWindow).
    std::vector<const NoteData*> ordered;
    for( const NoteData& note : inTrackData.m_noteData )
    {
        if( note.m_editorLane >= 0 && note.m_editorLane < PadId::COUNT )
        {
            ordered.push_back( &note );
        }
    }
    std::stable_sort( ordered.begin(), ordered.end(), []( const NoteData* a, const NoteData* b ) { return a->m_triggerTime < b->m_triggerTime; } );
    for( const NoteData* it : ordered )
    {
        LaneNotes& laneNotes = m_laneNotes[LaneOf( it->m_editorLane )];
        size_t& next = nextInLane[LaneOf( it->m_editorLane )];
        if( next < laneNotes.Notes.size() )
        {
            laneNotes.Notes[next++].Source = *it;
        }
        m_lastNoteMs = std::max( m_lastNoteMs, static_cast<double>( it->m_triggerTime ) * 1000.0 );
        m_firstNoteMs = std::min( m_firstNoteMs, static_cast<double>( it->m_triggerTime ) * 1000.0 );
        ++m_totalNotes;
    }
    const double startMarkerMs = static_cast<double>( inTrackData.m_startTime ) * 1000.0;
    m_countInMs = startMarkerMs > 0.0 && startMarkerMs < m_firstNoteMs ? startMarkerMs : m_firstNoteMs;
    AssignKickFeet();
}


void NoteHighwayCore::AssignKickFeet()
{
    // Double bass: which half of the highway each kick's bar is drawn on (SpawnNote).
    std::vector<NoteState>& kicks = m_laneNotes[PadId::Bass].Notes;
    std::vector<double> times;
    std::vector<bool> marks;
    for( const NoteState& kick : kicks )
    {
        times.push_back( kick.TimeMs );
        marks.push_back( kick.Source.m_secondPedal );
    }
    const std::vector<KickFoot> feet = KickFeet::Assign( times, marks );
    for( size_t i = 0; i < kicks.size(); ++i )
    {
        kicks[i].Foot = feet[i];
    }
}


void NoteHighwayCore::ClearNotes()
{
    for( auto& lane : m_laneNotes )
    {
        for( NoteState& note : lane.Notes )
        {
            // Out of sight at once (a rebuild puts new gems in their place this frame).
            HideNote( note );
        }
        lane = LaneNotes();
    }
    for( auto ent : GetEntities() )
    {
        ent.MarkForDelete();
    }
}


void NoteHighwayCore::ClearBeatLines()
{
    for( BeatLine& line : m_beatLines )
    {
        if( line.Line )
        {
            line.Line->MarkForDelete();
        }
    }
    m_beatLines.clear();
    m_beatLive = LiveRange();
}


void NoteHighwayCore::BeginPreview( TrackData& inTrackData )
{
    ShutdownTrack();
    m_trackData = &inTrackData;
    m_trackIndex = -1;
    BuildNotes();
    BuildHighway();
    BuildBeatLines();
    // The Track Editor has the clock: no crowd noise over the charter's playback.
    m_venueShow.SetAmbienceWanted( false );
    BuildVenue();
    ResetScore();
    m_songState = SongState::Preview;
    m_songTimeMs = 0.0;
    m_previewLastMs = 0.0;
    m_previewRearm = true;
    m_isPaused = false;
    m_lyrics.Clear();
    if( GameSettings::GetInstance().LyricsOnHud() )
    {
        m_lyrics.Build( inTrackData.m_venue.m_lyrics, inTrackData.m_venue.m_vocalPhrases, inTrackData.m_venue.m_vocalNotes );
    }
    m_lyricSung.clear();
    m_lyricRest.clear();
    m_lyricNext.clear();
}


void NoteHighwayCore::EndPreview()
{
    if( m_songState == SongState::Preview )
    {
        ShutdownTrack();
        m_trackData = nullptr;
    }
}


void NoteHighwayCore::SetPreviewTime( double inTimeMs )
{
    if( m_songState == SongState::Preview )
    {
        m_songTimeMs = std::max( 0.0, inTimeMs );
    }
}


void NoteHighwayCore::RefreshPreview( int inParts )
{
    if( m_songState != SongState::Preview || !m_trackData )
    {
        return;
    }
    if( inParts & PreviewNotes )
    {
        ClearNotes();
        BuildNotes();
        m_previewRearm = true;
    }
    if( inParts & PreviewBeats )
    {
        ClearBeatLines();
        BuildBeatLines();
    }
    if( inParts & PreviewVenue )
    {
        m_venueShow.Clear();
        BuildVenue();
        m_lyrics.Clear();
        if( GameSettings::GetInstance().LyricsOnHud() )
        {
            m_lyrics.Build( m_trackData->m_venue.m_lyrics, m_trackData->m_venue.m_vocalPhrases, m_trackData->m_venue.m_vocalNotes );
        }
    }
}


void NoteHighwayCore::UpdatePreview( float inDeltaTime )
{
    ApplyPendingTints();
    ApplySpeed();
    // The editor's playhead is the time on the strike bar: no latency offsets, the editor isn't
    // being played. Notes behind it are gone as a clean play leaves them, lighting their pads as
    // they cross while the song plays on (not on a scrub); notes ahead are there again.
    const double now = m_songTimeMs;
    const bool playing = !m_previewRearm && now >= m_previewLastMs && now - m_previewLastMs < 250.0;
    for( size_t lane = 0; lane < m_laneNotes.size(); ++lane )
    {
        LaneNotes& notes = m_laneNotes[lane];
        if( playing )
        {
            // Playing on: only the notes that crossed the bar since last frame change.
            for( ; notes.Cursor < notes.Notes.size() && notes.Notes[notes.Cursor].TimeMs <= now; ++notes.Cursor )
            {
                NoteState& note = notes.Notes[notes.Cursor];
                if( !note.Judged )
                {
                    note.Judged = true;
                    HideNote( note );
                    if( note.TimeMs > m_previewLastMs )
                    {
                        FlashLane( static_cast<int>( lane ) );
                    }
                }
            }
            continue;
        }
        // A scrub (or a fresh build): every note is re-armed from the playhead. Only flags change
        // here; UpdateWindow spawns what is in view.
        notes.Cursor = notes.Notes.size();
        for( size_t i = 0; i < notes.Notes.size(); ++i )
        {
            NoteState& note = notes.Notes[i];
            const bool past = note.TimeMs <= now;
            if( past && !note.Judged )
            {
                HideNote( note );
            }
            note.Judged = past;
            if( !past )
            {
                notes.Cursor = std::min( notes.Cursor, i );
            }
        }
    }
    UpdateWindow( now, !playing );
    m_previewRearm = false;
    m_previewLastMs = now;
    if( TrackMover )
    {
        Transform& mover = TrackMover->GetComponent<Transform>();
        Vector3 position = mover.GetPosition();
        position.z = static_cast<float>( now / 1000.0 ) * m_appliedSpeed;
        mover.SetPosition( position );
    }
    UpdateTargetPads( inDeltaTime );
    m_venueShow.SetPerformance( 0.8f );
    m_venueShow.Update( now, inDeltaTime );
    UpdateHud( inDeltaTime );
}


void NoteHighwayCore::SpawnNote( const NoteData& inNote, NoteState& outState )
{
    const PadId pad = inNote.m_editorLane;
    const bool kick = pad == PadId::Bass;
    const bool pedal = pad == PadId::HiHatPedal;
    const bool plate = PadUtils::IsCymbal( pad );
    const bool ghost = inNote.m_velocity <= kGhostVelocity;
    const bool accent = inNote.m_velocity >= kAccentVelocity;

    const char* prefab = kDrumGemPrefab;
    if( kick || pedal )
    {
        prefab = kKickPrefab;
    }
    else if( plate )
    {
        prefab = pad == PadId::OpenHiHat ? kOpenHiHatPrefab : kCymbalPrefab;
    }
    EntityHandle note = GetWorld().CreateFromPrefab( prefab );
    if( !note )
    {
        return;
    }
    outState.Note = note;

    Transform& transform = note->GetComponent<Transform>();
    const Vector3 baseColor = kick ? Vector3( 1.f, 0.49f, 0.f ) : Vivid( PadUtils::GetNoteColor( pad ) );
    const float glow = ghost ? kGhostGlow : accent ? kAccentGlow : kGemGlow;
    const Vector3 color = baseColor * glow;
    Tint( note, Vector3( kNoteTrim, kNoteTrim, kNoteTrim ), color );
    outState.Color = color;
    outState.Late = false;

    const float size = ghost ? 0.7f : 1.f;
    const float tall = ( accent ? 1.35f : 1.f ) * ( ghost ? 0.8f : 1.f );
    Vector3 scale;
    float base = kGemBase;
    const float laneWidth = LaneWidth( pad );
    float width = laneWidth * 0.9f * size;
    // Double bass: the bar fills the half of the highway on its foot's side, and a thin line
    // carries it across the other half.
    float kickSide = 0.f;
    if( kick )
    {
        // Past the rails, so its points show even where notes cover the lanes.
        width = m_highwayWidth + 0.3f;
        if( outState.Foot != KickFoot::Either )
        {
            kickSide = outState.Foot == KickFoot::Right ? 1.f : -1.f;
            width = m_highwayWidth * 0.5f;
        }
        scale = Vector3( width, tall, 1.f );
        base = kKickBase;
    }
    else if( pedal )
    {
        width = laneWidth * 0.5f;
        scale = Vector3( width, 0.8f, 0.6f );
        base = kKickBase;
    }
    else if( plate )
    {
        width = laneWidth * 0.94f * size;
        scale = Vector3( width, tall, size );
        base = kCymbalBase;
    }
    else
    {
        scale = Vector3( width, tall, size );
    }
    const Vector3 position( kickSide * m_highwayWidth * 0.25f, base, static_cast<float>( outState.TimeMs / 1000.0 ) * m_appliedSpeed );
    transform.SetPosition( position );
    transform.SetScale( scale );
    transform.SetName( inNote.m_noteName + std::to_string( (uint8_t)pad ) );
    Transform* lane = nullptr;
    const auto laneEntity = m_lanes.find( inNote.m_noteName );
    if( laneEntity != m_lanes.end() && laneEntity->second )
    {
        lane = &laneEntity->second->GetComponent<Transform>();
        transform.SetParent( *lane );
    }
    else
    {
        YIKES( "NoteHighwayCore: no lane for note '" + inNote.m_noteName + "'" );
    }

    // Technique markings: white pieces on top of the note.
    const float top = base + ( plate ? kCymbalBowTop : kGemTop ) * tall;
    const float depth = ( plate ? kCymbalDepth : kGemTopDepth ) * size;
    const Vector3 white( 0.95f, 0.95f, 0.95f );
    if( kickSide != 0.f )
    {
        AddDecoration( outState, lane, position, Vector3( -kickSide * m_highwayWidth * 0.5f, kKickBase + 0.015f, 0.f ), Vector3( m_highwayWidth * 0.5f, 0.03f, 0.07f ), baseColor );
    }
    switch( inNote.m_articulation )
    {
    case Articulation::Rim:
        // Rimshot (or a cymbal's edge): a white strip along the near edge.
        if( plate )
        {
            AddDecoration( outState, lane, position, Vector3( 0.f, base + 0.045f * tall, -depth * 0.4f ), Vector3( width * 0.55f, 0.025f, depth * 0.12f ), white );
        }
        else
        {
            AddDecoration( outState, lane, position, Vector3( 0.f, top + 0.008f, -depth * 0.32f ), Vector3( width * 0.78f, 0.02f, depth * 0.3f ), white );
        }
        break;
    case Articulation::CrossStick:
        // Cross-stick: a white bar down the left side.
        AddDecoration( outState, lane, position, Vector3( -width * 0.3f, top + 0.008f, 0.f ), Vector3( width * 0.14f, 0.02f, depth ), white );
        break;
    case Articulation::Bell:
        // Bell: a white dot on the cymbal's bell (or the middle of a drum).
        AddDecoration( outState, lane, position, Vector3( 0.f, plate ? base + kCymbalBellTop * tall + 0.005f : top + 0.008f, 0.f ), Vector3( width * 0.18f, 0.02f, plate ? 0.09f * size : depth * 0.6f ), white );
        break;
    default:
        break;
    }

    auto& noteComp = note->AddComponent<NoteTrigger>();
    noteComp.TriggerTime = inNote.m_triggerTime;
    noteComp.TriggerTimeMS = inNote.m_triggerTimeMS;
    noteComp.NoteName = inNote.m_noteName;
    noteComp.EditorLane = pad;
    noteComp.EditorLaneName = PadUtils::GetPadName( pad );
}


void NoteHighwayCore::AddDecoration( NoteState& ioState, Transform* inLane, const Vector3& inGemPosition, const Vector3& inOffset, const Vector3& inScale, const Vector3& inColor )
{
    const Vector3 position( inGemPosition.x + inOffset.x, inOffset.y, inGemPosition.z + inOffset.z );
    EntityHandle piece = SpawnBox( position, inScale, inColor, inColor * 0.8f, inLane );
    if( piece )
    {
        ioState.Decorations.push_back( Decoration{ piece, inOffset, inColor } );
    }
}


void NoteHighwayCore::HideNote( NoteState& ioNote )
{
    // Gone this frame, not when the deletion is processed next frame.
    if( ioNote.Note )
    {
        ioNote.Note->GetComponent<Transform>().SetScale( 0.f );
        ioNote.Note->MarkForDelete();
        ioNote.Note = EntityHandle();
    }
    for( Decoration& decoration : ioNote.Decorations )
    {
        if( decoration.Piece )
        {
            decoration.Piece->GetComponent<Transform>().SetScale( 0.f );
            decoration.Piece->MarkForDelete();
        }
    }
    ioNote.Decorations.clear();
}


void NoteHighwayCore::GreyOut( NoteState& ioNote, float inGlow )
{
    // The note's body shows only what it glows, so a missed one keeps a little.
    const float body = std::max( inGlow, kMissedGlow );
    const Vector3 glow( inGlow, inGlow, inGlow );
    Tint( ioNote.Note, Vector3( 0.2f, 0.2f, 0.2f ), Vector3( body, body, body ) );
    for( Decoration& decoration : ioNote.Decorations )
    {
        Tint( decoration.Piece, Vector3( 0.15f, 0.15f, 0.15f ), glow * 0.75f );
    }
}


void NoteHighwayCore::DimLate( NoteState& ioNote )
{
    // Still its own colour, so it reads as "late" rather than "missed" (grey).
    ioNote.Late = true;
    Tint( ioNote.Note, Vector3( kNoteTrim, kNoteTrim, kNoteTrim ) * kLateDim, ioNote.Color * kLateGlow );
    for( Decoration& decoration : ioNote.Decorations )
    {
        Tint( decoration.Piece, decoration.Color * kLateDim, decoration.Color * 0.08f );
    }
}


void NoteHighwayCore::UpdateWindow( double inTimeMs, bool inRecheck )
{
    // Only what is on the visible highway has entities: the renderer and the ECS visit every
    // entity each frame, seen or not, so a whole song's worth would cost every frame of it.
    // Margins: a gem spawns half a second before the far end (so its colour, which waits for its
    // model to bind, is on before it shows) and goes half a second after the back end.
    constexpr double kMarginMs = 500.0;
    const double msPerUnit = 1000.0 / static_cast<double>( std::max( m_appliedSpeed, 0.01f ) );
    const double fromMs = inTimeMs - static_cast<double>( kHighwayBehind ) * msPerUnit - kMarginMs;
    const double toMs = inTimeMs + static_cast<double>( kHighwayLength ) * msPerUnit + kMarginMs;

    // Moves [Begin, End) to the new range: what left it is despawned, what joined it spawned. The
    // overlap is untouched, unless inRecheck asks for it to be spawned where it has to be.
    const auto reconcile = [inRecheck]( LiveRange& ioLive, size_t inBegin, size_t inEnd, const auto& inSpawn, const auto& inDespawn ) {
        for( size_t i = ioLive.Begin; i < std::min( ioLive.End, inBegin ); ++i )
        {
            inDespawn( i );
        }
        for( size_t i = std::max( ioLive.Begin, inEnd ); i < ioLive.End; ++i )
        {
            inDespawn( i );
        }
        if( inRecheck )
        {
            for( size_t i = inBegin; i < inEnd; ++i )
            {
                inSpawn( i );
            }
        }
        else
        {
            for( size_t i = inBegin; i < std::min( inEnd, ioLive.Begin ); ++i )
            {
                inSpawn( i );
            }
            for( size_t i = std::max( inBegin, ioLive.End ); i < inEnd; ++i )
            {
                inSpawn( i );
            }
        }
        ioLive.Begin = inBegin;
        ioLive.End = inEnd;
    };

    for( LaneNotes& lane : m_laneNotes )
    {
        std::vector<NoteState>& notes = lane.Notes;
        const size_t begin = static_cast<size_t>( std::lower_bound( notes.begin(), notes.end(), fromMs, []( const NoteState& n, double t ) { return n.TimeMs < t; } ) - notes.begin() );
        const size_t end = static_cast<size_t>( std::upper_bound( notes.begin(), notes.end(), toMs, []( double t, const NoteState& n ) { return t < n.TimeMs; } ) - notes.begin() );
        // A hit note stays gone and a missed one keeps its grey gem: only unjudged notes spawn,
        // and the ones a resume is playing again (grey: they have been judged).
        reconcile( lane.Live, begin, std::max( begin, end ),
            [&notes, this]( size_t i ) {
                NoteState& note = notes[i];
                if( ( !note.Judged || note.Passed ) && !note.Note )
                {
                    SpawnNote( note.Source, note );
                    if( note.Judged )
                    {
                        GreyOut( note, 0.3f );
                    }
                }
            },
            [&notes, this]( size_t i ) { HideNote( notes[i] ); } );
    }

    const size_t beatBegin = static_cast<size_t>( std::lower_bound( m_beatLines.begin(), m_beatLines.end(), fromMs, []( const BeatLine& b, double t ) { return b.TimeMs < t; } ) - m_beatLines.begin() );
    const size_t beatEnd = static_cast<size_t>( std::upper_bound( m_beatLines.begin(), m_beatLines.end(), toMs, []( double t, const BeatLine& b ) { return t < b.TimeMs; } ) - m_beatLines.begin() );
    reconcile( m_beatLive, beatBegin, std::max( beatBegin, beatEnd ),
        [this]( size_t i ) {
            if( !m_beatLines[i].Line )
            {
                SpawnBeatLine( m_beatLines[i] );
            }
        },
        [this]( size_t i ) {
            BeatLine& line = m_beatLines[i];
            if( line.Line )
            {
                line.Line->GetComponent<Transform>().SetScale( 0.f );
                line.Line->MarkForDelete();
                line.Line = EntityHandle();
            }
        } );
}


std::string NoteHighwayCore::TechniqueName( PadId inPad, Articulation inTechnique )
{
    switch( inTechnique )
    {
    case Articulation::Rim: return PadUtils::IsCymbal( inPad ) ? "EDGE" : "RIMSHOT";
    case Articulation::CrossStick: return "CROSS-STICK";
    case Articulation::Bell: return "BELL";
    default: break;
    }
    if( inPad == PadId::OpenHiHat ) return "OPEN HI-HAT";
    if( inPad == PadId::ClosedHiHat ) return "CLOSED HI-HAT";
    return PadUtils::IsCymbal( inPad ) ? "BOW" : "HEAD";
}


float NoteHighwayCore::LaneWidth( PadId inPad ) const
{
    return IsTom( inPad ) ? m_laneSpacing * kTomLaneScale : m_laneSpacing;
}


bool NoteHighwayCore::ShowsColumn( PadId inPad ) const
{
    const auto hasNotes = [this]( PadId inLanePad ) { return !m_laneNotes[LaneOf( inLanePad )].Notes.empty(); };
    if( IsTom( inPad ) )
    {
        // All three toms or none: a chart that only uses two would otherwise leave the player
        // guessing which drums those two columns are.
        return hasNotes( PadId::HighTom ) || hasNotes( PadId::MidTom ) || hasNotes( PadId::FloorTom );
    }
    if( inPad == PadId::ClosedHiHat && hasNotes( PadId::HiHatPedal ) )
    {
        return true;
    }
    return hasNotes( inPad );
}


void NoteHighwayCore::LayoutLanes()
{
    // Only the columns this chart uses, spread evenly and centred on the kick.
    std::vector<PadId> columns;
    for( PadId pad : kColumnOrder )
    {
        if( ShowsColumn( pad ) )
        {
            columns.push_back( pad );
        }
    }
    const int count = std::max<int>( 1, static_cast<int>( columns.size() ) );
    float units = 0.f;
    for( PadId pad : columns )
    {
        units += IsTom( pad ) ? kTomLaneScale : 1.f;
    }
    // Spacing as if every lane were full width, so the slimmer toms narrow the highway rather than
    // handing their room to the other lanes.
    m_laneSpacing = std::min( kMaxLaneSpacing, kMaxHighwayWidth / static_cast<float>( count ) );
    m_highwayWidth = m_laneSpacing * std::max( units, 1.f );

    const auto place = [this]( const char* inLane, float inX ) {
        const auto lane = m_lanes.find( inLane );
        if( lane != m_lanes.end() && lane->second )
        {
            Transform& transform = lane->second->GetComponent<Transform>();
            Vector3 position = transform.GetPosition();
            position.x = inX;
            transform.SetPosition( position );
            // Notes are sized in world units against LaneWidth; Example.lvl gives some lanes
            // (toms, ride) a half-width scale that the notes would otherwise inherit.
            transform.SetScale( Vector3( 1.f, 1.f, 1.f ) );
        }
    };
    m_columnEdges.clear();
    float edge = -m_highwayWidth * 0.5f;
    m_columnEdges.push_back( edge );
    for( int i = 0; i < static_cast<int>( columns.size() ); ++i )
    {
        const float width = LaneWidth( columns[i] );
        const float x = edge + width * 0.5f;
        edge += width;
        m_columnEdges.push_back( edge );
        place( PadUtils::GetPadId( columns[i] ), x );
        if( columns[i] == PadId::ClosedHiHat )
        {
            place( PadUtils::GetPadId( PadId::OpenHiHat ), x );
            place( PadUtils::GetPadId( PadId::HiHatPedal ), x );
        }
    }
    place( PadUtils::GetPadId( PadId::Bass ), 0.f );
    if( CommandLine::Has( "--highway-log" ) )
    {
        std::string layout;
        for( int i = 0; i < static_cast<int>( columns.size() ); ++i )
        {
            layout += std::string( PadUtils::GetPadName( columns[i] ) ) + " ";
        }
        BRUH_FMT( "Highway: %d lanes (%s), spacing %.2f, width %.2f", count, layout.c_str(), m_laneSpacing, m_highwayWidth );
    }

    // The strike bar spans the lanes.
    if( TrackMover )
    {
        if( Transform* bar = TrackMover->GetComponent<Transform>().GetChildByName( "Bar" ) )
        {
            Vector3 scale = bar->GetScale();
            scale.x = m_highwayWidth / kBarMeshWidth;
            bar->SetScale( scale );
        }
    }
}


void NoteHighwayCore::ShutdownTrack()
{
    m_calibrating = false;
    ClearNotes();
    for( EntityHandle& part : m_highwayParts )
    {
        if( part )
        {
            part->MarkForDelete();
        }
    }
    for( BeatLine& line : m_beatLines )
    {
        if( line.Line )
        {
            line.Line->MarkForDelete();
        }
    }
    m_venueShow.Clear();
    m_highwayParts.clear();
    m_targetPads.clear();
    m_beatLines.clear();
    m_beatLive = LiveRange();
    m_pendingTints.clear();
    m_currentTrackPack.Stop();
    m_songState = SongState::Idle;
    m_drumsAudible = true;
}


void NoteHighwayCore::Pause()
{
    m_isPaused = true;
    m_currentTrackPack.Pause();
    m_venueShow.SetAmbiencePaused( true );
}


void NoteHighwayCore::Resume()
{
    m_isPaused = false;
    m_venueShow.SetAmbiencePaused( false );
    ResumeWithRunUp();
    m_songClockStamp = std::chrono::steady_clock::now();
}


void NoteHighwayCore::ResumeWithRunUp()
{
    const double lengthMs = SongLengthMs();
    if( m_songState != SongState::Playing || lengthMs <= 0.0 || m_songTimeMs <= 0.0 )
    {
        // Nothing has played yet (the lead-in), or nothing to rewind.
        m_currentTrackPack.Resume();
        return;
    }
    const double target = std::max( 0.0, m_songTimeMs - kResumeRewindMs );
    // Everything on the highway is respawned for the new time. What was judged before the pause
    // stays judged, and comes back grey where the run-up passes it again.
    const double greyFromMs = target - 10000.0;
    for( LaneNotes& lane : m_laneNotes )
    {
        for( size_t i = lane.Live.Begin; i < lane.Live.End; ++i )
        {
            HideNote( lane.Notes[i] );
        }
        lane.Live = LiveRange();
        for( NoteState& note : lane.Notes )
        {
            note.Passed = note.Judged && note.TimeMs >= greyFromMs;
        }
    }
    // AudioPack::Seek leaves the stems held until all have seeked; they start together, fading in.
    m_currentTrackPack.Seek( static_cast<float>( target / lengthMs ), kResumeFadeSeconds );
    m_currentTrackPack.Resume();
    m_songTimeMs = target;
    m_clockErrorMs = 0.0;
    m_lastAudioPositionMs = m_currentTrackPack.GetPositionMs();
    // The drums come back for the run-up even if a miss had muted them.
    SetDrumsAudible( true );
    if( TrackMover )
    {
        Transform& mover = TrackMover->GetComponent<Transform>();
        Vector3 position = mover.GetPosition();
        position.z = static_cast<float>( VisualTimeMs() / 1000.0 ) * m_appliedSpeed;
        mover.SetPosition( position );
    }
    UpdateWindow( VisualTimeMs() );
    if( CommandLine::Has( "--highway-log" ) )
    {
        BRUH_FMT( "Highway: resumed %.0f ms back, at %.0f ms", kResumeRewindMs, target );
    }
}


double NoteHighwayCore::JudgeTimeMs() const
{
    // What the player hears now: the audio reaches their ears AudioLatency after FMOD plays it.
    // The calibration measures against the bare clock: the settings are what it is finding.
    if( m_calibrating )
    {
        return m_songTimeMs;
    }
    return m_songTimeMs - static_cast<double>( GameSettings::GetInstance().AudioLatency );
}


double NoteHighwayCore::VisualTimeMs() const
{
    // What should be on screen: what they hear, drawn VideoLatency early since the display shows
    // this frame that much later.
    if( m_calibrating )
    {
        return m_songTimeMs;
    }
    return JudgeTimeMs() + static_cast<double>( GameSettings::GetInstance().VideoLatency );
}


void NoteHighwayCore::Tint( const EntityHandle& inTarget, const Vector3& inColor, const Vector3& inEmissive )
{
    if( !inTarget )
    {
        return;
    }
    Mesh& mesh = inTarget->GetComponent<Mesh>();
    if( mesh.MeshReferece && mesh.MeshMaterial )
    {
        mesh.MeshMaterial->SetDiffuseColor( inColor );
        if( auto* standard = dynamic_cast<StandardMaterial*>( mesh.MeshMaterial.get() ) )
        {
            standard->SetEmissiveColor( inEmissive );
        }
        // A newer colour wins over one still waiting.
        m_pendingTints.erase( std::remove_if( m_pendingTints.begin(), m_pendingTints.end(), [&inTarget]( const PendingTint& t ) { return t.Target == inTarget; } ), m_pendingTints.end() );
        return;
    }
    for( PendingTint& pending : m_pendingTints )
    {
        if( pending.Target == inTarget )
        {
            pending.Color = inColor;
            pending.Emissive = inEmissive;
            return;
        }
    }
    m_pendingTints.push_back( PendingTint{ inTarget, inColor, inEmissive } );
}


void NoteHighwayCore::ApplyPendingTints()
{
    if( m_pendingTints.empty() )
    {
        return;
    }
    std::vector<PendingTint> pending;
    pending.swap( m_pendingTints );
    for( const PendingTint& tint : pending )
    {
        Tint( tint.Target, tint.Color, tint.Emissive );
    }
}


EntityHandle NoteHighwayCore::SpawnBox( const Vector3& inPosition, const Vector3& inScale, const Vector3& inColor, const Vector3& inEmissive, Transform* inParent )
{
    EntityHandle box = GetWorld().CreateFromPrefab( kHighwayBoxPrefab );
    if( !box )
    {
        return box;
    }
    Transform& transform = box->GetComponent<Transform>();
    if( inParent )
    {
        transform.SetParent( *inParent );
    }
    transform.SetPosition( inPosition );
    transform.SetScale( inScale );
    Tint( box, inColor, inEmissive );
    return box;
}


void NoteHighwayCore::BuildHighway()
{
    // Everything here rides with the camera: a dark surface, a divider between lanes, and a pad
    // per lane at the strike bar in that lane's colour.
    Transform* mover = TrackMover ? &TrackMover->GetComponent<Transform>() : nullptr;
    if( !mover )
    {
        return;
    }
    const float length = kHighwayLength + kHighwayBehind;
    const float centreZ = kHighwayLength * 0.5f - kHighwayBehind * 0.5f;
    m_highwayParts.push_back( SpawnBox( Vector3( 0.f, -0.08f, centreZ ), Vector3( m_highwayWidth + 0.3f, 0.04f, length ), Vector3( 0.02f, 0.02f, 0.03f ), Vector3( 0.03f, 0.03f, 0.045f ), mover ) );
    // Edge rails and lane dividers.
    for( size_t i = 0; i < m_columnEdges.size(); ++i )
    {
        const float x = m_columnEdges[i];
        const bool edge = i == 0 || i + 1 == m_columnEdges.size();
        const float brightness = edge ? 0.35f : 0.14f;
        m_highwayParts.push_back( SpawnBox( Vector3( x, -0.05f, centreZ ), Vector3( edge ? 0.08f : 0.035f, 0.02f, length ), Vector3( brightness, brightness, brightness ), Vector3( brightness, brightness, brightness ), mover ) );
    }
    // Target pads, dim until their lane is hit.
    for( PadId pad : kColumnOrder )
    {
        const int lane = LaneOf( pad );
        const auto entity = m_lanes.find( PadUtils::GetPadId( pad ) );
        if( !ShowsColumn( pad ) || entity == m_lanes.end() || !entity->second )
        {
            continue;
        }
        const float x = entity->second->GetComponent<Transform>().GetPosition().x;
        const Vector3 color = PadUtils::GetNoteColor( pad );
        TargetPad target;
        target.Lane = lane;
        target.Color = color;
        target.Pad = SpawnBox( Vector3( x, -0.03f, 0.f ), Vector3( LaneWidth( pad ) * 0.86f, 0.05f, 0.45f ), color * 0.5f, color * 0.35f, mover );
        m_highwayParts.push_back( target.Pad );
        m_targetPads.push_back( target );

        // The hi-hat pedal's pad: a small bar just in front of the hi-hat's.
        if( pad == PadId::ClosedHiHat && !m_laneNotes[PadId::HiHatPedal].Notes.empty() )
        {
            TargetPad pedal;
            pedal.Lane = PadId::HiHatPedal;
            pedal.Color = color;
            pedal.Pad = SpawnBox( Vector3( x, -0.035f, -0.5f ), Vector3( m_laneSpacing * 0.5f, 0.04f, 0.22f ), color * 0.5f, color * 0.35f, mover );
            m_highwayParts.push_back( pedal.Pad );
            m_targetPads.push_back( pedal );
        }
    }
}


void NoteHighwayCore::BuildBeatLines()
{
    // Beat and measure lines from the chart's tempo map: stored in NoteData.txt by the converter,
    // else read from notes.mid next to the song. Charts with neither get none: TrackData's BPM is
    // a placeholder, and wrong lines read worse than no lines.
    std::vector<BeatData> beats = m_trackData->m_beats;
    std::string source = "NoteData.txt";
    if( beats.empty() )
    {
        const std::string& audio = m_trackData->m_trackSourcePath;
        const size_t slash = audio.find_last_of( '/' );
        const Path midiPath( slash == std::string::npos ? std::string() : audio.substr( 0, slash ) + "/notes.mid" );
        if( slash != std::string::npos && midiPath.Exists )
        {
            beats = CustomTrackDefineTest::ReadMidiBeats( midiPath.FullPath, m_lastNoteMs / 1000.0 + 4.0 );
            source = midiPath.GetLocalPathString();
        }
    }

    // Spawned as the highway reaches them (UpdateWindow), which needs them in time order.
    for( const BeatData& beat : beats )
    {
        BeatLine line;
        line.TimeMs = static_cast<double>( beat.m_time ) * 1000.0;
        line.Measure = beat.m_measure;
        m_beatLines.push_back( line );
    }
    std::stable_sort( m_beatLines.begin(), m_beatLines.end(), []( const BeatLine& a, const BeatLine& b ) { return a.TimeMs < b.TimeMs; } );
    m_beatLive = LiveRange();
    if( CommandLine::Has( "--highway-log" ) && !beats.empty() )
    {
        BRUH_FMT( "Highway: %d beat lines from %s", static_cast<int>( m_beatLines.size() ), source.c_str() );
    }
}


void NoteHighwayCore::SpawnBeatLine( BeatLine& ioLine )
{
    // Beat lines sit in song space in the kick's lane, like the notes.
    Transform* parent = nullptr;
    const auto kickLane = m_lanes.find( PadUtils::GetPadId( PadId::Bass ) );
    if( kickLane != m_lanes.end() && kickLane->second )
    {
        parent = &kickLane->second->GetComponent<Transform>();
    }
    const float brightness = ioLine.Measure ? 0.5f : 0.2f;
    const Vector3 grey( brightness, brightness, brightness );
    ioLine.Line = SpawnBox( Vector3( 0.f, -0.045f, static_cast<float>( ioLine.TimeMs / 1000.0 ) * m_appliedSpeed ), Vector3( m_highwayWidth, 0.015f, ioLine.Measure ? 0.09f : 0.045f ), grey, grey, parent );
}


void NoteHighwayCore::FlashLane( int inLane )
{
    if( inLane == PadId::Bass )
    {
        m_kickFlash = 1.f;
        return;
    }
    for( TargetPad& pad : m_targetPads )
    {
        if( pad.Lane == inLane )
        {
            pad.Flash = 1.f;
        }
    }
}


void NoteHighwayCore::UpdateTargetPads( float inDeltaTime )
{
    // A hit lights its lane's pad (the strike bar for the kick), which fades back to dim.
    const float step = inDeltaTime / kPadFlashSeconds;
    for( TargetPad& pad : m_targetPads )
    {
        if( pad.Flash > 0.f )
        {
            pad.Flash = std::max( 0.f, pad.Flash - step );
            Tint( pad.Pad, pad.Color * ( 0.5f + pad.Flash * 0.5f ), pad.Color * ( 0.35f + pad.Flash * 1.5f ) );
        }
    }
    if( m_kickFlash > 0.f && TrackMover )
    {
        m_kickFlash = std::max( 0.f, m_kickFlash - step );
        if( Transform* bar = TrackMover->GetComponent<Transform>().GetChildByName( "Bar" ) )
        {
            const Vector3 grey( 0.7f, 0.7f, 0.7f );
            const Vector3 kick( 1.f, 0.49f, 0.f );
            Tint( bar->Parent, grey * ( 1.f - m_kickFlash ) + kick * m_kickFlash, Vector3( 0.25f, 0.25f, 0.25f ) + kick * ( m_kickFlash * 1.4f ) );
        }
    }
}


float NoteHighwayCore::UnitsPerSecond() const
{
    const float chart = m_trackData ? m_trackData->m_noteSpeed : 10.f;
    return chart * std::clamp( GameSettings::GetInstance().HighwaySpeed, 0.5f, 2.f );
}


void NoteHighwayCore::ApplySpeed()
{
    // The speed setting changed (pause options): move every note and beat line to its new place.
    const float speed = UnitsPerSecond();
    if( speed == m_appliedSpeed )
    {
        return;
    }
    m_appliedSpeed = speed;
    // Only what has entities; the window spawns the rest at the new speed.
    for( LaneNotes& lane : m_laneNotes )
    {
        for( size_t i = lane.Live.Begin; i < lane.Live.End; ++i )
        {
            NoteState& note = lane.Notes[i];
            const float z = static_cast<float>( note.TimeMs / 1000.0 ) * speed;
            if( note.Note )
            {
                Transform& transform = note.Note->GetComponent<Transform>();
                Vector3 position = transform.GetPosition();
                position.z = z;
                transform.SetPosition( position );
            }
            for( Decoration& decoration : note.Decorations )
            {
                if( decoration.Piece )
                {
                    Transform& transform = decoration.Piece->GetComponent<Transform>();
                    Vector3 position = transform.GetPosition();
                    position.z = z + decoration.Offset.z;
                    transform.SetPosition( position );
                }
            }
        }
    }
    for( size_t i = m_beatLive.Begin; i < m_beatLive.End; ++i )
    {
        BeatLine& line = m_beatLines[i];
        if( line.Line )
        {
            Transform& transform = line.Line->GetComponent<Transform>();
            Vector3 position = transform.GetPosition();
            position.z = static_cast<float>( line.TimeMs / 1000.0 ) * speed;
            transform.SetPosition( position );
        }
    }
}


void NoteHighwayCore::UpdateSongClock( float inDeltaTime )
{
    m_songClockStamp = std::chrono::steady_clock::now();
    // A long hitch (a load) shouldn't fling the clock; the correction below catches it up.
    const double rawStepMs = std::min( static_cast<double>( inDeltaTime ), 0.1 ) * 1000.0;
    // With vsync on, frames reach the screen a refresh apart, but the measured frame time wobbles
    // around it by a millisecond or two; advancing by it makes everything that rides the clock
    // (the highway, the venue) judder. Steady frames advance by the running average instead; a
    // dropped or late frame by what it took. FMOD's position keeps the sum honest.
    m_frameStepMs = m_frameStepMs <= 0.0 ? rawStepMs : m_frameStepMs + ( rawStepMs - m_frameStepMs ) * 0.05;
    const double stepMs = std::fabs( rawStepMs - m_frameStepMs ) < m_frameStepMs * 0.25 ? m_frameStepMs : rawStepMs;

    switch( m_songState )
    {
    case SongState::Loading:
        if( m_currentTrackPack.IsReady() )
        {
            m_songState = SongState::LeadIn;
        }
        break;
    case SongState::LeadIn:
        m_songTimeMs += stepMs;
        if( m_songTimeMs >= 0.0 )
        {
            // A stem added during the lead-in (the metronome, from the pause options) may still
            // be opening: the song waits at its start for it.
            if( !m_currentTrackPack.IsReady() )
            {
                m_songTimeMs = 0.0;
                break;
            }
            m_currentTrackPack.Play();
            m_lastAudioPositionMs = 0;
            m_clockErrorMs = 0.0;
            m_songState = SongState::Playing;
        }
        break;
    case SongState::Playing:
    {
        // A seek holds the clock until every stem has got there and they start together.
        m_currentTrackPack.Update();
        if( m_currentTrackPack.IsSeeking() )
        {
            m_lastAudioPositionMs = m_currentTrackPack.GetPositionMs();
            m_clockErrorMs = 0.0;
            break;
        }
        m_songTimeMs += stepMs;
        // FMOD's position moves once per mixer block; between moves the clock runs on frame
        // time. Each move measures the gap, and the frames after it close the gap a little at a
        // time, so the clock never steps (a few ms at once is a visible hitch on the highway).
        const unsigned int audioMs = m_currentTrackPack.GetPositionMs();
        if( audioMs != m_lastAudioPositionMs )
        {
            m_lastAudioPositionMs = audioMs;
            const double error = static_cast<double>( audioMs ) - m_songTimeMs;
            if( std::fabs( error ) > kClockSnapMs )
            {
                m_songTimeMs = static_cast<double>( audioMs );
                m_clockErrorMs = 0.0;
            }
            else
            {
                m_clockErrorMs = error;
            }
        }
        const double correction = m_clockErrorMs * std::min( 1.0, stepMs / ( kClockCorrectionSeconds * 1000.0 ) );
        m_songTimeMs += correction;
        m_clockErrorMs -= correction;
        break;
    }
    default:
        break;
    }
}


void NoteHighwayCore::AddHits( const std::vector<std::pair<PadId, Articulation>>& inMeanings, double inTimeMs, bool inInputKnowsTechnique, std::vector<Hit>& outHits )
{
    // One hit per lane. When an input means several pads in a lane (one key or MIDI note bound
    // to open and closed hi-hat), the pad is unknown; likewise the stroke.
    std::array<int, PadId::COUNT> firstInLane;
    firstInLane.fill( -1 );
    for( const auto& [pad, technique] : inMeanings )
    {
        if( pad < 0 || pad >= PadId::COUNT )
        {
            continue;
        }
        const int lane = LaneOf( pad );
        if( firstInLane[lane] < 0 )
        {
            firstInLane[lane] = static_cast<int>( outHits.size() );
            outHits.push_back( Hit{ pad, technique, inTimeMs, true, inInputKnowsTechnique } );
            continue;
        }
        Hit& hit = outHits[firstInLane[lane]];
        hit.PadKnown = hit.PadKnown && hit.Pad == pad;
        hit.TechniqueKnown = hit.TechniqueKnown && hit.Technique == technique;
    }
}


void NoteHighwayCore::GatherHits( std::vector<Hit>& outHits )
{
    PadMappingStorage& storage = PadMappingStorage::GetInstance();
    const double judgeTime = JudgeTimeMs();
    std::vector<std::pair<PadId, Articulation>> meanings;

    // Keyboard: every key pressed this frame, with every pad it's bound to. Keys carry no stroke.
    Input& input = GetEngine().GetInput();
    std::vector<int32_t> keys;
    for( const PadDefinition& pad : storage.mappedPads )
    {
        if( pad.keyboardBinding > 0 && std::find( keys.begin(), keys.end(), pad.keyboardBinding ) == keys.end() && input.WasKeyPressed( static_cast<KeyCode>( pad.keyboardBinding ) ) )
        {
            keys.push_back( pad.keyboardBinding );
        }
    }
    for( int32_t key : keys )
    {
        meanings.clear();
        for( const PadDefinition& pad : storage.mappedPads )
        {
            if( pad.keyboardBinding == key )
            {
                meanings.emplace_back( static_cast<PadId>( pad.padId ), Articulation::Normal );
            }
        }
        AddHits( meanings, judgeTime, false, outHits );
    }

    // MIDI: drained every frame, each note judged at the moment it arrived, as the pads and
    // strokes it's bound to (Docs/MIDI-and-Pads.md).
    std::vector<PadMappingStorage::Resolved> resolved;
    for( const MidiMessageNew& msg : MidiDevice::GetInstance().PumpMessages() )
    {
        if( !msg.IsOnType() )
        {
            continue;
        }
        const double ageMs = std::clamp( std::chrono::duration<double, std::milli>( m_songClockStamp - msg.m_arrival ).count(), 0.0, kMaxInputAgeMs );
        storage.Resolve( msg.m_data1, resolved );
        meanings.clear();
        for( const auto& meaning : resolved )
        {
            meanings.emplace_back( meaning.pad, meaning.articulation );
        }
        AddHits( meanings, judgeTime - ageMs, true, outHits );
    }

    // Autoplay (the F8 panel's toggle, or --highway-autoplay [offset ms]): hits every note, with
    // its pad and stroke, at its time plus the offset: a demo, and a way to check judging and
    // scoring without a kit. Sloppy plays like a person: each note early or late by up to 75 ms
    // (mostly within the great window) and about one in twenty-five missed, the same every run.
    // Plain hits as a kit that only sends plain strokes and one hi-hat note would.
    if( m_autoplay > 0 )
    {
        static const double offsetMs = CommandLine::GetFloat( "--highway-autoplay", 0.f );
        constexpr double kSloppyMs = 75.0;
        const bool sloppy = m_autoplay == 2;
        const double reach = sloppy ? kSloppyMs : 0.0;
        for( int lane = 0; lane < PadId::COUNT; ++lane )
        {
            const LaneNotes& notes = m_laneNotes[lane];
            for( size_t i = notes.Cursor; i < notes.Notes.size() && notes.Notes[i].TimeMs + offsetMs - reach <= judgeTime; ++i )
            {
                const NoteState& note = notes.Notes[i];
                if( note.Judged )
                {
                    continue;
                }
                double jitter = 0.0;
                if( sloppy )
                {
                    // From the note itself, so a seek or a retry plays it the same way.
                    uint32_t h = static_cast<uint32_t>( static_cast<int64_t>( note.TimeMs * 10.0 ) ) * 0x9E3779B1u ^ static_cast<uint32_t>( lane + 1 ) * 0x85EBCA77u;
                    h ^= h >> 15;
                    h *= 0x2C1B3C6Du;
                    h ^= h >> 12;
                    if( h % 1000u < 40u )
                    {
                        continue;   // never hit: JudgeMisses counts it
                    }
                    // Two uniforms summed: a triangle around on time.
                    const double u = static_cast<double>( ( h >> 10 ) & 1023u ) / 1023.0 + static_cast<double>( ( h >> 20 ) & 1023u ) / 1023.0 - 1.0;
                    jitter = u * kSloppyMs;
                }
                const double hitTime = note.TimeMs + offsetMs + jitter;
                if( hitTime > judgeTime )
                {
                    continue;
                }
                const PadId pad = m_autoplayPlain && note.Pad == PadId::OpenHiHat ? PadId::ClosedHiHat : note.Pad;
                outHits.push_back( Hit{ pad, m_autoplayPlain ? Articulation::Normal : note.Technique, hitTime, true, true } );
            }
        }
    }
    std::sort( outHits.begin(), outHits.end(), []( const Hit& a, const Hit& b ) { return a.TimeMs < b.TimeMs; } );
}


void NoteHighwayCore::JudgeHit( const Hit& inHit )
{
    if( inHit.Pad < 0 || inHit.Pad >= PadId::COUNT )
    {
        return;
    }
    LaneNotes& lane = m_laneNotes[LaneOf( inHit.Pad )];
    // The closest unjudged note in this lane within the widest window.
    NoteState* best = nullptr;
    double bestOffset = 0.0;
    for( size_t i = lane.Cursor; i < lane.Notes.size(); ++i )
    {
        NoteState& note = lane.Notes[i];
        const double offset = inHit.TimeMs - note.TimeMs;
        if( offset < -kGoodWindowMs )
        {
            break;
        }
        if( note.Judged || offset > kGoodWindowMs )
        {
            continue;
        }
        if( !best || std::fabs( offset ) < std::fabs( bestOffset ) )
        {
            best = &note;
            bestOffset = offset;
        }
    }
    if( !best )
    {
        return;   // An extra hit: the kit still sounds, nothing is scored
    }

    // Right drum; was it played the way the chart asks (open vs closed hi-hat, rim vs head)?
    const bool padRight = !inHit.PadKnown || inHit.Pad == best->Pad;
    const bool techniqueRight = !inHit.TechniqueKnown || inHit.Technique == best->Technique;
    const int strictness = GameSettings::GetInstance().TechniqueStrictness;
    const bool wrongTechnique = strictness > 0 && !( padRight && techniqueRight );

    best->Judged = true;
    FlashLane( LaneOf( inHit.Pad ) );
    m_venueShow.OnHit( inHit.PadKnown ? inHit.Pad : best->Pad );
    if( wrongTechnique && strictness >= 2 )
    {
        ++m_wrongTechnique;
        GreyOut( *best );
        ApplyJudgement( Judgement::Miss, bestOffset );
        m_lastHint = TechniqueName( best->Pad, best->Technique ) + "!";
        return;
    }
    HideNote( *best );
    const double magnitude = std::fabs( bestOffset );
    Judgement judgement = magnitude <= kPerfectWindowMs ? Judgement::Perfect : magnitude <= kGreatWindowMs ? Judgement::Great : Judgement::Good;
    if( wrongTechnique )
    {
        // Lenient: it counts, one grade lower, and says what was wanted.
        ++m_wrongTechnique;
        judgement = judgement == Judgement::Perfect ? Judgement::Great : Judgement::Good;
    }
    ApplyJudgement( judgement, bestOffset );
    m_lastHint = wrongTechnique ? TechniqueName( best->Pad, best->Technique ) + "!" : std::string();
}


void NoteHighwayCore::UpdateMetronome()
{
    // A lesson and the calibration are click tracks already. A chart with no beat grid has no
    // beat lines, and nothing to click on.
    // --metronome [seconds]: on whatever the setting says, from that point of the song (with
    // --pause-at, a headless check of switching it on mid-song).
    static const bool kForced = CommandLine::Has( "--metronome" );
    static const double kForcedFromMs = static_cast<double>( CommandLine::GetFloat( "--metronome", 0.f ) ) * 1000.0;
    const bool wanted = GameSettings::GetInstance().Metronome || ( kForced && ( kForcedFromMs <= 0.0 || m_songTimeMs >= kForcedFromMs ) );
    if( !m_trackData || m_trackData->m_practice || m_trackData->m_calibration || m_beatLines.empty() )
    {
        return;
    }
    if( wanted && !m_metronomeTried )
    {
        // Once a song: written from the beat lines, so the clicks are where the lines are.
        m_metronomeTried = true;
        std::vector<ClickTrack::Click> clicks;
        clicks.reserve( m_beatLines.size() );
        for( const BeatLine& line : m_beatLines )
        {
            clicks.push_back( { line.TimeMs / 1000.0, line.Measure } );
        }
        const std::string file = ClickTrack::MetronomeFile( clicks );
        const bool added = !file.empty() && m_currentTrackPack.AddMetronome( file );
        if( CommandLine::Has( "--highway-log" ) )
        {
            BRUH_FMT( "Highway: metronome %s, %d clicks, %s", added ? "added" : "not added", static_cast<int>( clicks.size() ), file.c_str() );
        }
    }
    m_currentTrackPack.SetMetronomeVolume( wanted ? 1.f : 0.f );
}


void NoteHighwayCore::CalibrationHits( const std::vector<Hit>& inHits )
{
    Calibration& calibration = Calibration::GetInstance();
    std::vector<double> taps;
    if( m_autoplay > 0 )
    {
        // Autoplay stands in for the player in both parts: every beat, late by its offset.
        static const double offsetMs = CommandLine::GetFloat( "--highway-autoplay", 0.f );
        for( Calibration::Part part : { Calibration::Part::Watch, Calibration::Part::Listen } )
        {
            for( int beat = 0; beat < Calibration::kPartBeats; ++beat )
            {
                const double time = Calibration::BeatTimeMs( part, beat ) + offsetMs;
                if( time > m_autoTapsToMs && time <= m_songTimeMs )
                {
                    taps.push_back( time );
                }
            }
        }
        m_autoTapsToMs = std::max( m_autoTapsToMs, m_songTimeMs );
    }
    else
    {
        for( const Hit& hit : inHits )
        {
            taps.push_back( hit.TimeMs );
        }
    }
    std::sort( taps.begin(), taps.end() );
    for( double tap : taps )
    {
        // One strike can arrive as several hits (a key or a note bound to pads in several lanes,
        // a pad that double-triggers): only the first counts.
        constexpr double kSameStrikeMs = 80.0;
        if( std::fabs( tap - m_lastTapMs ) < kSameStrikeMs )
        {
            continue;
        }
        m_lastTapMs = tap;
        // The pad lights for every strike, so the player can see it was heard.
        FlashLane( LaneOf( PadId::Snare ) );
        if( !calibration.AddTap( tap ) )
        {
            continue;
        }
        // Watch: the note the hit was for goes, as a hit note does in a song.
        NoteState* best = nullptr;
        double bestGap = 0.0;
        for( LaneNotes& lane : m_laneNotes )
        {
            for( size_t i = lane.Cursor; i < lane.Notes.size(); ++i )
            {
                NoteState& note = lane.Notes[i];
                const double gap = std::fabs( note.TimeMs - tap );
                if( note.TimeMs - tap > Calibration::kReachMs )
                {
                    break;
                }
                if( !note.Judged && gap <= Calibration::kReachMs && ( !best || gap < bestGap ) )
                {
                    best = &note;
                    bestGap = gap;
                }
            }
        }
        if( best )
        {
            best->Judged = true;
            HideNote( *best );
        }
    }
}


void NoteHighwayCore::JudgeMisses( double inJudgeTimeMs )
{
    // The calibration counts nothing as a miss; a note nobody hit goes grey once it is out of reach.
    const double window = m_calibrating ? Calibration::kReachMs : static_cast<double>( kGoodWindowMs );
    for( LaneNotes& lane : m_laneNotes )
    {
        while( lane.Cursor < lane.Notes.size() )
        {
            NoteState& note = lane.Notes[lane.Cursor];
            if( !note.Judged )
            {
                if( note.TimeMs + window >= inJudgeTimeMs )
                {
                    break;
                }
                note.Judged = true;
                // Missed notes go grey and keep scrolling past.
                GreyOut( note );
                if( !m_calibrating )
                {
                    ApplyJudgement( Judgement::Miss, 0.0 );
                    m_lastHint.clear();
                }
            }
            ++lane.Cursor;
        }
        if( m_calibrating )
        {
            // How late a hit lands is the thing being measured: no dimming to hurry the player.
            continue;
        }
        // What is left at the cursor is still in reach. Once a note is past the Perfect window its
        // gem dims: it has gone by the bar, and a hit now scores less.
        for( size_t i = lane.Cursor; i < lane.Notes.size(); ++i )
        {
            NoteState& note = lane.Notes[i];
            if( note.TimeMs + kPerfectWindowMs >= inJudgeTimeMs )
            {
                break;
            }
            if( !note.Judged && !note.Late && note.Note )
            {
                DimLate( note );
            }
        }
    }
}


void NoteHighwayCore::ApplyJudgement( Judgement inJudgement, double inOffsetMs )
{
    m_judgementAge = 0.f;
    if( inJudgement == Judgement::Miss && m_noFail )
    {
        // No fail: counted, but the streak, the drums and the crowd carry on.
        ++m_missed;
        m_lastJudgement = "MISS";
        m_lastTiming.clear();
        return;
    }
    if( inJudgement == Judgement::Miss )
    {
        m_venueShow.OnMiss();
        ++m_missed;
        m_combo = 0;
        m_lastJudgement = "MISS";
        m_lastTiming.clear();
        SetDrumsAudible( false );
        return;
    }

    ++m_combo;
    m_maxCombo = std::max( m_maxCombo, m_combo );
    m_venueShow.OnStreak( m_combo );
    int points = 0;
    switch( inJudgement )
    {
    case Judgement::Perfect: ++m_perfect; points = 100; m_lastJudgement = "PERFECT"; break;
    case Judgement::Great: ++m_great; points = 75; m_lastJudgement = "GREAT"; break;
    default: ++m_good; points = 50; m_lastJudgement = "GOOD"; break;
    }
    m_score += points * Multiplier( m_combo );
    m_offsetSumMs += inOffsetMs;
    ++m_offsetCount;
    const int offset = static_cast<int>( std::lround( inOffsetMs ) );
    m_lastTiming = std::abs( offset ) <= static_cast<int>( kPerfectWindowMs ) ? std::string() : ( offset < 0 ? "EARLY " : "LATE +" ) + std::to_string( offset ) + " ms";
    SetDrumsAudible( true );
}


void NoteHighwayCore::SetDrumsAudible( bool inAudible )
{
    // The drum stems are the player's part: they drop out on a miss and come back on the next hit.
    if( m_drumsAudible != inAudible )
    {
        m_drumsAudible = inAudible;
        if( CommandLine::Has( "--highway-log" ) )
        {
            BRUH_FMT( "Highway: drums %s at %.0f ms", inAudible ? "back" : "muted", m_songTimeMs );
        }
        m_currentTrackPack.SetDrumVolume( inAudible ? 1.f : 0.f );
    }
}


double NoteHighwayCore::SongLengthMs() const
{
    // The audio's length once it has loaded (AudioPack has no sounds before then).
    const bool loaded = m_songState == SongState::LeadIn || m_songState == SongState::Playing || m_songState == SongState::Finished;
    return loaded && m_trackData ? static_cast<double>( m_currentTrackPack.GetLength() ) : 0.0;
}


void NoteHighwayCore::SeekTo( double inTimeMs )
{
    const double lengthMs = SongLengthMs();
    if( !m_trackData || lengthMs <= 0.0 || m_songState == SongState::Idle || m_songState == SongState::Loading || m_songState == SongState::Finished )
    {
        return;
    }
    const double target = std::clamp( inTimeMs, 0.0, std::max( 0.0, lengthMs - 500.0 ) );
    // Skipping ahead leaves notes unjudged, so the run's result isn't a fair one to keep. Going
    // back (a resume's run-up, a retry of a passage) is fine.
    m_skippedAhead = m_skippedAhead || target > m_songTimeMs + 1000.0;
    if( m_songState == SongState::LeadIn )
    {
        m_currentTrackPack.Play();
        m_songState = SongState::Playing;
    }
    // AudioPack::Seek leaves the stems paused at the new position.
    m_currentTrackPack.Seek( static_cast<float>( target / lengthMs ) );
    if( !m_isPaused )
    {
        m_currentTrackPack.Resume();
    }
    m_songTimeMs = target;
    m_clockErrorMs = 0.0;
    m_lastAudioPositionMs = m_currentTrackPack.GetPositionMs();
    m_songClockStamp = std::chrono::steady_clock::now();

    // Notes already past the judge are cleared without counting; the rest are armed again and the
    // window spawns them fresh (hit ones were deleted, missed ones greyed).
    const double judgeTime = JudgeTimeMs();
    for( LaneNotes& lane : m_laneNotes )
    {
        for( size_t i = lane.Live.Begin; i < lane.Live.End; ++i )
        {
            HideNote( lane.Notes[i] );
        }
        lane.Live = LiveRange();
        lane.Cursor = lane.Notes.size();
        for( size_t i = 0; i < lane.Notes.size(); ++i )
        {
            NoteState& note = lane.Notes[i];
            note.Judged = note.TimeMs + kGoodWindowMs < judgeTime;
            note.Passed = false;
            if( !note.Judged )
            {
                lane.Cursor = std::min( lane.Cursor, i );
            }
        }
    }
    if( TrackMover )
    {
        Transform& mover = TrackMover->GetComponent<Transform>();
        Vector3 position = mover.GetPosition();
        position.z = static_cast<float>( VisualTimeMs() / 1000.0 ) * m_appliedSpeed;
        mover.SetPosition( position );
    }
    UpdateWindow( VisualTimeMs() );
    SetDrumsAudible( true );
    m_lastJudgement.clear();
    m_lastHint.clear();
    if( CommandLine::Has( "--highway-log" ) )
    {
        BRUH_FMT( "Highway: seek to %.0f ms", target );
    }
}


double NoteHighwayCore::Accuracy() const
{
    const int judged = m_perfect + m_great + m_good + m_missed;
    return judged > 0 ? ( m_perfect + m_great * 0.75 + m_good * 0.5 ) * 100.0 / judged : 100.0;
}


void NoteHighwayCore::RecordResult()
{
    m_resultNews.clear();
    m_resultBests.clear();
    m_resultUnlocks.clear();
    m_resultGig.clear();
    static const bool recordAutoplay = CommandLine::Has( "--record-autoplay" );
    if( !m_trackData || m_trackData->m_calibration || m_noFail || m_skippedAhead || ( m_autoplay != 0 && !recordAutoplay ) )
    {
        return;
    }
    PlayerProfile& profile = PlayerProfile::GetInstance();
    const double accuracy = Accuracy();
    char text[128];
    if( m_trackData->m_practice )
    {
        const Practice& practice = Practice::GetInstance();
        const PracticeLesson* lesson = practice.CurrentLesson();
        if( !lesson )
        {
            return;
        }
        const PlayerProfile::Outcome outcome = profile.RecordLesson( *lesson, practice.Tempo(), accuracy );
        const PlayerProfile::LessonRecord* record = profile.FindLesson( lesson->Id );
        if( outcome.LessonPassed )
        {
            m_resultNews = "Lesson passed!";
        }
        else if( record && !record->Passed )
        {
            std::snprintf( text, sizeof( text ), "To pass: %.0f%% at %d BPM or faster", lesson->PassAccuracy, lesson->PassTempo() );
            m_resultNews = text;
        }
        if( record )
        {
            if( record->BestBpm > 0 )
            {
                std::snprintf( text, sizeof( text ), "Best %.1f%%, fastest clean tempo %d BPM", record->BestAccuracy, record->BestBpm );
            }
            else
            {
                std::snprintf( text, sizeof( text ), "Best %.1f%%", record->BestAccuracy );
            }
            m_resultBests = text;
        }
    }
    else
    {
        const std::string key = TrackDatabase::FavoriteKey( *m_trackData );
        PlayerProfile::SongResult result;
        result.Score = m_score;
        result.Accuracy = accuracy;
        result.MaxCombo = m_maxCombo;
        result.Missed = m_missed;
        result.TotalNotes = m_totalNotes;
        const PlayerProfile::SongRecord* before = profile.FindSong( key );
        const bool firstPlay = !before || before->Plays == 0;
        const PlayerProfile::Outcome outcome = profile.RecordSong( key, result );
        if( outcome.FirstFullCombo )
        {
            m_resultNews = "Full combo!";
        }
        else if( outcome.NewBestScore && !firstPlay )
        {
            m_resultNews = "New best score!";
        }
        else if( outcome.NewBestAccuracy && !firstPlay )
        {
            m_resultNews = "New best accuracy!";
        }
        if( const PlayerProfile::SongRecord* record = profile.FindSong( key ) )
        {
            std::snprintf( text, sizeof( text ), "Best %d, %.1f%%, played %d time%s", record->BestScore, record->BestAccuracy, record->Plays, record->Plays == 1 ? "" : "s" );
            m_resultBests = text;
        }
        // A gig's song: the set's tally, and the gig completed when its last song passes it.
        GigSession& gig = GigSession::GetInstance();
        if( gig.IsActive() && gig.RecordSong( m_trackIndex, accuracy ) )
        {
            if( gig.Passed() )
            {
                gig.Complete( profile );
                std::snprintf( text, sizeof( text ), "%s played! The set averaged %.0f%% (%.0f%% needed).", gig.GigName().c_str(), gig.AverageAccuracy(), gig.PassAccuracy() );
            }
            else
            {
                std::snprintf( text, sizeof( text ), "Not this time: the set averaged %.0f%%, %.0f%% needed. Retry a song to raise it.", gig.AverageAccuracy(), gig.PassAccuracy() );
            }
            m_resultGig = text;
            profile.Save();
        }
    }
    // What it opened: a new room, items, lessons, venues. The hideout shows them again (Notices).
    const std::vector<ProgressionUnlock> unlocks = Progression::GetInstance().Evaluate( profile );
    for( const ProgressionUnlock& unlock : unlocks )
    {
        m_resultUnlocks += ( m_resultUnlocks.empty() ? "" : "\n" ) + unlock.Text;
    }
    if( !unlocks.empty() )
    {
        profile.Save();
    }
    if( CommandLine::Has( "--highway-log" ) )
    {
        BRUH_FMT( "Highway: recorded the result: '%s' / '%s', %d unlocks", m_resultNews.c_str(), m_resultBests.c_str(), static_cast<int>( unlocks.size() ) );
        for( const ProgressionUnlock& unlock : unlocks )
        {
            BRUH_FMT( "Highway: unlocked %s:%s (%s)", unlock.Kind.c_str(), unlock.Id.c_str(), unlock.Text.c_str() );
        }
    }
}


void NoteHighwayCore::ResetScore()
{
    m_score = m_combo = m_maxCombo = m_perfect = m_great = m_good = m_missed = m_wrongTechnique = 0;
    m_offsetSumMs = 0.0;
    m_offsetCount = 0;
    m_skippedAhead = false;
    m_lastJudgement.clear();
    m_resultNews.clear();
    m_resultBests.clear();
    m_resultUnlocks.clear();
    m_resultGig.clear();
    m_lastHint.clear();
    m_lastTiming.clear();
    m_judgementAge = 10.f;
    if( RmlUiCore* ui = GetEngine().RmlUi )
    {
        ui->ModelEnsure( kModel );
        ui->ModelSetNumber( kModel, "playing", 0 );
        ui->ModelSetNumber( kModel, "finished", 0 );
        ui->ModelSetNumber( kModel, "countdown", 0 );
        ui->ModelSetNumber( kModel, "countdown_intro", 0 );
        ui->ModelSetNumber( kModel, "track_index", m_trackIndex );
        ui->ModelSetNumber( kModel, "total_notes", m_totalNotes );
        ui->ModelSetNumber( kModel, "song_progress", 0 );
        ui->ModelSetNumber( kModel, "practice", 0 );
        for( const char* key : { "track_title", "track_artist", "judgement", "timing", "hint", "accuracy", "judgement_opacity", "song_clock", "avg_timing" } )
        {
            ui->ModelSetString( kModel, key, "" );
        }
    }
    UpdateHud( 0.f );
}


void NoteHighwayCore::UpdateLyrics( RmlUiCore& inUi )
{
    // The karaoke line: what's been sung of it, the rest, and the next line under it. Set only
    // when they change.
    std::string sung;
    std::string rest;
    std::string next;
    if( !m_lyrics.Empty() && m_songState != SongState::Idle && m_songState != SongState::Finished )
    {
        const Lyrics::View view = m_lyrics.At( VisualTimeMs() / 1000.0 );
        const auto& lines = m_lyrics.Lines();
        if( view.Current >= 0 )
        {
            sung = lines[view.Current].Text.substr( 0, view.Sung );
            rest = lines[view.Current].Text.substr( view.Sung );
        }
        if( view.Next >= 0 )
        {
            next = lines[view.Next].Text;
        }
        // The text goes into the document: keep markup characters out of it.
        for( std::string* text : { &sung, &rest, &next } )
        {
            text->erase( std::remove_if( text->begin(), text->end(), []( char c ) { return c == '<' || c == '>' || c == '&'; } ), text->end() );
        }
    }
    if( sung != m_lyricSung || rest != m_lyricRest || next != m_lyricNext )
    {
        m_lyricSung = sung;
        m_lyricRest = rest;
        m_lyricNext = next;
        inUi.ModelSetString( kModel, "lyric_sung", sung );
        inUi.ModelSetString( kModel, "lyric_rest", rest );
        inUi.ModelSetString( kModel, "lyric_next", next );
        inUi.ModelSetNumber( kModel, "lyrics_shown", !sung.empty() || !rest.empty() || !next.empty() );
    }
}


void NoteHighwayCore::UpdateHud( float inDeltaTime )
{
    RmlUiCore* ui = GetEngine().RmlUi;
    if( !ui )
    {
        return;
    }
    m_judgementAge += inDeltaTime;
    char accuracyText[16];
    std::snprintf( accuracyText, sizeof( accuracyText ), "%.1f%%", Accuracy() );
    // The judgement holds for a moment, then fades.
    const float opacity = std::clamp( 1.f - ( m_judgementAge - 0.35f ) / 0.3f, 0.f, 1.f );

    ui->ModelSetNumber( kModel, "playing", m_songState != SongState::Idle );
    // The debug panel's scrubber and clock.
    {
        const double lengthMs = SongLengthMs();
        const double nowMs = std::max( 0.0, m_songTimeMs );
        ui->ModelSetNumber( kModel, "song_progress", lengthMs > 0.0 ? std::round( std::min( 1.0, nowMs / lengthMs ) * 1000.0 ) : 0.0 );
        const auto clock = []( double inMs ) {
            const int seconds = static_cast<int>( inMs / 1000.0 );
            char text[16];
            std::snprintf( text, sizeof( text ), "%d:%02d", seconds / 60, seconds % 60 );
            return std::string( text );
        };
        ui->ModelSetString( kModel, "song_clock", clock( nowMs ) + " / " + clock( lengthMs ) );
    }
    ui->ModelSetNumber( kModel, "finished", m_songState == SongState::Finished );
    UpdateLyrics( *ui );
    // The title card shows over the lead-in; the count runs down to the first note, not the
    // song's start, so a long intro doesn't end the countdown long before there's anything to hit.
    const bool counting = m_songState == SongState::Loading || m_songState == SongState::LeadIn || m_songState == SongState::Playing;
    const double toFirstNoteMs = m_countInMs - m_songTimeMs;
    ui->ModelSetNumber( kModel, "countdown", counting && toFirstNoteMs > 0.0 && toFirstNoteMs <= kCountdownMs ? std::ceil( toFirstNoteMs / 1000.0 ) : 0.0 );
    ui->ModelSetNumber( kModel, "countdown_intro", m_songState == SongState::Loading || m_songState == SongState::LeadIn );
    ui->ModelSetNumber( kModel, "score", m_score );
    ui->ModelSetNumber( kModel, "combo", m_combo );
    ui->ModelSetNumber( kModel, "multiplier", Multiplier( m_combo ) );
    ui->ModelSetNumber( kModel, "max_combo", m_maxCombo );
    ui->ModelSetNumber( kModel, "hits_perfect", m_perfect );
    ui->ModelSetNumber( kModel, "hits_great", m_great );
    ui->ModelSetNumber( kModel, "hits_good", m_good );
    ui->ModelSetNumber( kModel, "hits_missed", m_missed );
    ui->ModelSetString( kModel, "accuracy", accuracyText );
    ui->ModelSetString( kModel, "judgement", m_lastJudgement );
    ui->ModelSetString( kModel, "timing", m_lastTiming );
    ui->ModelSetString( kModel, "hint", m_lastHint );
    ui->ModelSetNumber( kModel, "wrong_technique", m_wrongTechnique );
    // Whether the player sits ahead of the beat or behind it, over every note they hit.
    std::string averageTiming = "--";
    if( m_offsetCount > 0 )
    {
        const int average = static_cast<int>( std::lround( m_offsetSumMs / m_offsetCount ) );
        averageTiming = average == 0 ? std::string( "On the beat" ) : std::to_string( std::abs( average ) ) + ( average < 0 ? " ms early" : " ms late" );
    }
    ui->ModelSetString( kModel, "avg_timing", averageTiming );
    ui->ModelSetString( kModel, "result_news", m_resultNews );
    ui->ModelSetString( kModel, "result_bests", m_resultBests );
    ui->ModelSetString( kModel, "result_unlocks", m_resultUnlocks );
    // A gig in progress (CoreGame/GigSession.h): which song of the set, and what comes after.
    {
        const GigSession& gig = GigSession::GetInstance();
        const bool inGig = gig.IsActive() && m_trackData && !m_trackData->m_practice && !m_trackData->m_calibration;
        ui->ModelSetNumber( kModel, "gig", inGig ? 1 : 0 );
        ui->ModelSetString( kModel, "gig_name", inGig ? gig.GigName() : std::string() );
        ui->ModelSetString( kModel, "gig_progress", inGig ? "Song " + std::to_string( gig.SongIndex() + 1 ) + " of " + std::to_string( gig.SongCount() ) : std::string() );
        ui->ModelSetNumber( kModel, "gig_next", inGig && !gig.IsLastSong() ? 1 : 0 );
        ui->ModelSetString( kModel, "gig_result", m_resultGig );
    }
    // The delay calibration: what to do now, how far along, and what it found.
    ui->ModelSetNumber( kModel, "calibration", m_calibrating );
    if( m_calibrating )
    {
        const Calibration& calibration = Calibration::GetInstance();
        const Calibration::Part part = Calibration::PartAt( m_songTimeMs );
        const bool watch = part == Calibration::Part::Watch;
        const Calibration::Result video = calibration.ResultOf( Calibration::Part::Watch );
        const Calibration::Result audio = calibration.ResultOf( Calibration::Part::Listen );
        ui->ModelSetString( kModel, "cal_prompt", watch ? "WATCH" : "LISTEN" );
        ui->ModelSetString( kModel, "cal_detail", watch ? "Hit as each note crosses the line. This part is silent." : "Hit on every click. There is nothing to watch." );
        ui->ModelSetString( kModel, "cal_progress", std::to_string( calibration.Measured( part ) ) + " / " + std::to_string( Calibration::kMeasuredBeats ) );
        ui->ModelSetString( kModel, "cal_video", Calibration::ValueText( video ) );
        ui->ModelSetString( kModel, "cal_video_note", Calibration::Remark( video ) );
        ui->ModelSetString( kModel, "cal_audio", Calibration::ValueText( audio ) );
        ui->ModelSetString( kModel, "cal_audio_note", Calibration::Remark( audio ) );
        ui->ModelSetNumber( kModel, "cal_can_apply", video.Valid() || audio.Valid() );
    }
    else
    {
        for( const char* key : { "cal_prompt", "cal_detail", "cal_progress", "cal_video", "cal_video_note", "cal_audio", "cal_audio_note" } )
        {
            ui->ModelSetString( kModel, key, "" );
        }
        ui->ModelSetNumber( kModel, "cal_can_apply", 0 );
    }
    ui->ModelSetString( kModel, "judgement_opacity", std::to_string( opacity ) );
}


void NoteHighwayCore::Update( const UpdateContext& context )
{
    if( m_songState == SongState::Preview )
    {
        // The Track Editor drives: it has the clock, and the MIDI queue for recording.
        UpdatePreview( context.GetDeltaTime() );
        return;
    }
    std::vector<Hit> hits;
    // --pause-at <seconds>: pause there for a second, then resume (headless checks of the resume).
    static const float kPauseAt = CommandLine::GetFloat( "--pause-at", -1.f );
    static int pauseAtStage = 0;
    static float pausedFor = 0.f;
    if( kPauseAt >= 0.f && pauseAtStage == 0 && m_songState == SongState::Playing && m_songTimeMs >= kPauseAt * 1000.0 )
    {
        pauseAtStage = 1;
        pausedFor = 0.f;
        Pause();
    }
    else if( pauseAtStage == 1 && ( pausedFor += context.GetDeltaTime() ) >= 1.f )
    {
        pauseAtStage = 2;
        Resume();
    }
    if( m_isPaused || m_songState == SongState::Idle || m_songState == SongState::Finished )
    {
        // Keep the MIDI queue empty so nothing stale is judged on resume.
        MidiDevice::GetInstance().PumpMessages();
        // Switched on in the pause options: its stem is in place before the resume's seek.
        UpdateMetronome();
        UpdateHud( context.GetDeltaTime() );
        return;
    }

    // No fail and autoplay are the debug panel's toggles (InGameMenuController; --no-fail and
    // --highway-autoplay start them on).
    if( RmlUiCore* ui = GetEngine().RmlUi )
    {
        m_noFail = ui->ModelGetNumber( kModel, "debug_nofail" ) != 0;
        m_autoplay = static_cast<int>( ui->ModelGetNumber( kModel, "debug_autoplay" ) );
        m_autoplayPlain = ui->ModelGetNumber( kModel, "debug_plain" ) != 0;
    }
    else
    {
        static const int kAutoplay = CommandLine::Has( "--highway-autoplay" ) ? ( CommandLine::Has( "--highway-autoplay-sloppy" ) ? 2 : 1 ) : 0;
        m_autoplay = kAutoplay;
        m_autoplayPlain = CommandLine::Has( "--highway-autoplay-plain" );
    }
    ApplyPendingTints();
    ApplySpeed();
    UpdateMetronome();
    UpdateSongClock( context.GetDeltaTime() );
    // --seek <seconds>: jump there once the song starts (the debug scrubber, from the command line).
    static const float kSeekTo = CommandLine::GetFloat( "--seek", -1.f );
    if( kSeekTo >= 0.f && !m_seekedFromCommandLine && m_songState == SongState::Playing )
    {
        m_seekedFromCommandLine = true;
        SeekTo( kSeekTo * 1000.0 );
    }
    GatherHits( hits );
    if( m_calibrating )
    {
        CalibrationHits( hits );
    }
    else
    {
        for( const Hit& hit : hits )
        {
            JudgeHit( hit );
        }
    }
    const double judgeTime = JudgeTimeMs();
    JudgeMisses( judgeTime );

    // The highway is a direct read of the clock: a note crosses the bar when it should be hit.
    if( TrackMover && m_trackData )
    {
        Transform& mover = TrackMover->GetComponent<Transform>();
        Vector3 position = mover.GetPosition();
        position.z = static_cast<float>( VisualTimeMs() / 1000.0 ) * m_appliedSpeed;
        mover.SetPosition( position );
    }
    if( m_trackData )
    {
        UpdateWindow( VisualTimeMs() );
    }

    UpdateTargetPads( context.GetDeltaTime() );
    // F7 swaps the room under the highway mid-song (--venue-swap-every <seconds> does it on a
    // timer, for headless captures).
    static const float kSwapEvery = CommandLine::GetFloat( "--venue-swap-every", 0.f );
    m_venueSwapTimer += context.GetDeltaTime();
    if( GetEngine().GetInput().WasKeyPressed( KeyCode::F7 ) || ( kSwapEvery > 0.f && m_venueSwapTimer >= kSwapEvery ) )
    {
        m_venueSwapTimer = 0.f;
        m_venueShow.NextStyle();
    }
    // The crowd reads the player's streak: a long one gets them going.
    m_venueShow.SetPerformance( 0.25f + 0.75f * std::min( 1.f, static_cast<float>( m_combo ) / 80.f ) );
    m_venueShow.Update( VisualTimeMs(), context.GetDeltaTime() );

    // Done once every note has passed and the audio has stopped (or ran out long ago).
    if( m_songState == SongState::Playing && judgeTime > m_lastNoteMs + kGoodWindowMs )
    {
        const double lengthMs = static_cast<double>( m_currentTrackPack.GetLength() );
        if( !m_currentTrackPack.IsPlaying() || m_songTimeMs > lengthMs + 2000.0 )
        {
            m_songState = SongState::Finished;
            RecordResult();
            if( CommandLine::Has( "--highway-log" ) )
            {
                BRUH_FMT( "Highway: finished, score %d, perfect %d great %d good %d missed %d, best combo %d", m_score, m_perfect, m_great, m_good, m_missed, m_maxCombo );
            }
        }
    }
    UpdateHud( context.GetDeltaTime() );

    // --highway-log: once a second, the clock against FMOD and the score, to check sync by hand.
    static const bool logClock = CommandLine::Has( "--highway-log" );
    static double nextLogMs = 0.0;
    if( logClock && m_songTimeMs >= nextLogMs )
    {
        nextLogMs = std::floor( m_songTimeMs / 1000.0 ) * 1000.0 + 1000.0;
        BRUH_FMT( "Highway: song %.1f ms, audio %u ms (stems %u ms apart, metronome %s), judged %d (missed %d) of %d, first note %.0f ms, %d gems and %d beat lines live",
            m_songTimeMs, m_currentTrackPack.GetPositionMs(), m_currentTrackPack.StemSpreadMs(), !m_currentTrackPack.HasMetronome() ? "none" : m_currentTrackPack.IsMetronomePlaying() ? "playing" : "not playing", m_perfect + m_great + m_good + m_missed, m_missed, m_totalNotes, m_firstNoteMs,
            static_cast<int>( GetEntities().size() ), static_cast<int>( m_beatLive.End - m_beatLive.Begin ) );
    }
}


#if USING( ME_EDITOR )

void NoteHighwayCore::OnEditorInspect()
{
}

#endif
