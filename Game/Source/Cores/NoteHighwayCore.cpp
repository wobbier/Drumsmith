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
    // Widths at scale 1: the note gem (NewNote.obj, 2 units), and the unit cube the kick bar and
    // the strike bar (Example.lvl's "Bar") use.
    constexpr float kNoteMeshWidth = 2.f;
    constexpr float kKickMeshWidth = 1.f;
    constexpr float kBarMeshWidth = 1.f;
    // Steering the song clock toward FMOD's position: the share of the error closed per mixer
    // update, and the error past which the clock jumps (a hitch, a seek).
    constexpr double kClockCorrection = 0.2;
    constexpr double kClockSnapMs = 120.0;
    // MIDI hits older than this when read are judged as if they arrived this long ago.
    constexpr double kMaxInputAgeMs = 250.0;
    // Gem shape (NewNote.obj scale): taller and deeper than the prefab so they read at a glance.
    constexpr float kGemHeight = 1.8f;
    constexpr float kGemDepth = 1.6f;
    // How strongly gems glow in their lane colour (the scene has no lights; emissive carries them).
    constexpr float kGemGlow = 0.55f;
    // Highway pieces (world units): the surface runs this far ahead of the strike bar.
    constexpr float kHighwayLength = 120.f;
    constexpr float kHighwayBehind = 6.f;
    constexpr float kPadFlashSeconds = 0.15f;
    constexpr const char* kHighwayBoxPrefab = "Assets/Prefabs/Highway/HighwayBox.prefab";
    // Cymbals are thin raised plates (the unit cube), drums the chunky gem.
    constexpr float kPlateHeight = 0.07f;
    constexpr float kPlateDepth = 0.42f;
    constexpr float kPlateLift = 0.12f;
    // Ghost notes are smaller and dimmer, accents taller and brighter.
    constexpr uint8_t kGhostVelocity = 40;
    constexpr uint8_t kAccentVelocity = 120;


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
        if( event.TrackIndex >= 0 && event.TrackIndex < static_cast<int>( tracks.size() ) )
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
    MidiDevice::GetInstance().OpenMidiDevice( GameSettings::GetInstance().PreferredMidiDevice );
    // Every HUD value exists before the document loads, so it never reloads for one.
    ResetScore();
}


void NoteHighwayCore::OnRemovedFromWorld()
{
    m_launchTrackSubscription.reset();
    m_pauseTrackSubscription.reset();
    m_resumeTrackSubscription.reset();
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
    m_notePrefabs[PadId::Bass] = "Assets/Prefabs/Notes/BassNotePrefab.prefab";

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

    inTrackData.LoadNoteData();
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
    if( CommandLine::Has( "--highway-log" ) )
    {
        BRUH_FMT( "Highway: playing %s (track %d)", inTrackData.m_trackName.c_str(), inTrackIndex );
    }

    std::array<size_t, PadId::COUNT> nextInLane{};
    for( auto& laneNotes : m_laneNotes )
    {
        std::sort( laneNotes.Notes.begin(), laneNotes.Notes.end(), []( const NoteState& a, const NoteState& b ) { return a.TimeMs < b.TimeMs; } );
    }

    m_lastNoteMs = 0.0;
    m_firstNoteMs = 1e12;
    m_appliedSpeed = UnitsPerSecond();
    m_totalNotes = 0;
    // Spawn in time order per lane so each NoteState gets its entity.
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
            SpawnNote( *it, laneNotes.Notes[next++] );
        }
        m_lastNoteMs = std::max( m_lastNoteMs, static_cast<double>( it->m_triggerTime ) * 1000.0 );
        m_firstNoteMs = std::min( m_firstNoteMs, static_cast<double>( it->m_triggerTime ) * 1000.0 );
        ++m_totalNotes;
    }

    BuildHighway();
    BuildBeatLines();
    if( TrackMover )
    {
        Transform& mover = TrackMover->GetComponent<Transform>();
        Transform* camera = mover.GetChildByName( "Main Camera" );
        m_stageLights.Build( GetWorld(), &mover, camera ? camera->Parent : EntityHandle(), inTrackData,
            [this]( const Vector3& inPosition, const Vector3& inScale, const Vector3& inColor, const Vector3& inEmissive, Transform* inParent ) { return SpawnBox( inPosition, inScale, inColor, inEmissive, inParent ); },
            [this]( const EntityHandle& inTarget, const Vector3& inColor, const Vector3& inEmissive ) { Tint( inTarget, inColor, inEmissive ); } );
    }

    m_currentTrackPack = AudioPack( inTrackData );
    ResetScore();
    m_songState = SongState::Loading;
    m_songTimeMs = -kLeadInMs;
    m_isPaused = false;
    if( RmlUiCore* ui = GetEngine().RmlUi )
    {
        ui->ModelSetString( kModel, "track_title", inTrackData.m_trackName );
        ui->ModelSetString( kModel, "track_artist", inTrackData.m_artistName );
        ui->ModelSetNumber( kModel, "track_index", inTrackIndex );
        ui->ModelSetNumber( kModel, "total_notes", m_totalNotes );
    }
}


void NoteHighwayCore::SpawnNote( const NoteData& inNote, NoteState& outState )
{
    const PadId pad = inNote.m_editorLane;
    const bool kick = pad == PadId::Bass;
    const bool pedal = pad == PadId::HiHatPedal;
    const bool plate = PadUtils::IsCymbal( pad );
    const bool ghost = inNote.m_velocity <= kGhostVelocity;
    const bool accent = inNote.m_velocity >= kAccentVelocity;

    std::string prefab = "Assets/Prefabs/Notes/NewBaseNote.prefab";
    if( kick )
    {
        prefab = m_notePrefabs[PadId::Bass];
    }
    else if( plate || pedal )
    {
        prefab = kHighwayBoxPrefab;
    }
    EntityHandle note = GetWorld().CreateFromPrefab( prefab );
    if( !note )
    {
        return;
    }
    outState.Note = note;

    Transform& transform = note->GetComponent<Transform>();
    const Vector3 baseColor = kick ? Vector3( 1.f, 0.49f, 0.f ) : PadUtils::GetNoteColor( pad );
    const float glow = ghost ? 0.2f : accent ? 1.f : kGemGlow;
    const Vector3 color = ghost ? baseColor * 0.6f : baseColor;
    Tint( note, color, color * glow );

    const float size = ghost ? 0.7f : 1.f;
    const float tall = accent ? 1.35f : 1.f;
    Vector3 scale;
    float lift = 0.f;
    float width = m_laneSpacing * 0.9f * size;
    if( kick )
    {
        scale = Vector3( m_highwayWidth / kKickMeshWidth, 0.12f * tall, 0.3f );
        width = m_highwayWidth;
    }
    else if( pedal )
    {
        width = m_laneSpacing * 0.5f;
        scale = Vector3( width, 0.05f, 0.22f );
        lift = -0.02f;
    }
    else if( plate )
    {
        width = m_laneSpacing * 0.92f * size;
        scale = Vector3( width, kPlateHeight * tall, kPlateDepth * size );
        lift = kPlateLift;
    }
    else
    {
        scale = Vector3( width / kNoteMeshWidth, kGemHeight * tall, kGemDepth * size );
    }
    const Vector3 position( 0.f, lift, static_cast<float>( outState.TimeMs / 1000.0 ) * m_appliedSpeed );
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

    // Technique markings, on top of the gem (drum gems reach ~0.16 up at their base height).
    const float top = plate ? lift + kPlateHeight * tall * 0.5f : 0.16f * tall;
    const float depth = plate ? kPlateDepth * size : 0.28f * size;
    const Vector3 white( 0.95f, 0.95f, 0.95f );
    if( pad == PadId::OpenHiHat )
    {
        // A dark centre makes the plate read as a ring: the open hi-hat.
        AddDecoration( outState, lane, position, Vector3( 0.f, top + 0.005f, 0.f ), Vector3( width * 0.55f, 0.02f, depth * 0.5f ), Vector3( 0.01f, 0.01f, 0.01f ) );
    }
    switch( inNote.m_articulation )
    {
    case Articulation::Rim:
        // Rimshot (or a cymbal's edge): a white strip along the near edge.
        AddDecoration( outState, lane, position, Vector3( 0.f, top + 0.01f, -depth * 0.4f ), Vector3( width, 0.03f, depth * 0.2f ), white );
        break;
    case Articulation::CrossStick:
        // Cross-stick: a white bar down the left side.
        AddDecoration( outState, lane, position, Vector3( -width * 0.4f, top + 0.01f, 0.f ), Vector3( width * 0.18f, 0.03f, depth ), white );
        break;
    case Articulation::Bell:
        // Bell: a white dot in the middle.
        AddDecoration( outState, lane, position, Vector3( 0.f, top + 0.01f, 0.f ), Vector3( width * 0.22f, 0.04f, depth * 0.45f ), white );
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
        ioState.Decorations.push_back( Decoration{ piece, inOffset } );
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


void NoteHighwayCore::LayoutLanes()
{
    // Only the columns this chart uses, spread evenly and centred on the kick.
    std::vector<PadId> columns;
    for( PadId pad : kColumnOrder )
    {
        const bool pedalNotes = pad == PadId::ClosedHiHat && !m_laneNotes[PadId::HiHatPedal].Notes.empty();
        if( !m_laneNotes[LaneOf( pad )].Notes.empty() || pedalNotes )
        {
            columns.push_back( pad );
        }
    }
    const int count = std::max<int>( 1, static_cast<int>( columns.size() ) );
    m_laneSpacing = std::min( kMaxLaneSpacing, kMaxHighwayWidth / static_cast<float>( count ) );
    m_highwayWidth = m_laneSpacing * static_cast<float>( count );

    const auto place = [this]( const char* inLane, float inX ) {
        const auto lane = m_lanes.find( inLane );
        if( lane != m_lanes.end() && lane->second )
        {
            Transform& transform = lane->second->GetComponent<Transform>();
            Vector3 position = transform.GetPosition();
            position.x = inX;
            transform.SetPosition( position );
        }
    };
    for( int i = 0; i < static_cast<int>( columns.size() ); ++i )
    {
        const float x = ( static_cast<float>( i ) - ( static_cast<float>( count ) - 1.f ) * 0.5f ) * m_laneSpacing;
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
    for( auto ent : GetEntities() )
    {
        ent.MarkForDelete();
    }
    for( auto& lane : m_laneNotes )
    {
        for( NoteState& note : lane.Notes )
        {
            for( Decoration& decoration : note.Decorations )
            {
                if( decoration.Piece )
                {
                    decoration.Piece->MarkForDelete();
                }
            }
        }
        lane = LaneNotes();
    }
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
    m_stageLights.Clear();
    m_highwayParts.clear();
    m_targetPads.clear();
    m_beatLines.clear();
    m_pendingTints.clear();
    m_currentTrackPack.Stop();
    m_songState = SongState::Idle;
    m_drumsAudible = true;
}


void NoteHighwayCore::Pause()
{
    m_isPaused = true;
    m_currentTrackPack.Pause();
}


void NoteHighwayCore::Resume()
{
    m_isPaused = false;
    m_currentTrackPack.Resume();
    m_songClockStamp = std::chrono::steady_clock::now();
}


double NoteHighwayCore::JudgeTimeMs() const
{
    // What the player hears now: the audio reaches their ears AudioLatency after FMOD plays it.
    return m_songTimeMs - static_cast<double>( GameSettings::GetInstance().AudioLatency );
}


double NoteHighwayCore::VisualTimeMs() const
{
    // What should be on screen: what they hear, drawn VideoLatency early since the display shows
    // this frame that much later.
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
        mesh.MeshMaterial->DiffuseColor = inColor;
        if( auto* standard = dynamic_cast<StandardMaterial*>( mesh.MeshMaterial.get() ) )
        {
            standard->EmissiveColor = inEmissive;
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
    const float halfWidth = m_highwayWidth * 0.5f;
    const float length = kHighwayLength + kHighwayBehind;
    const float centreZ = kHighwayLength * 0.5f - kHighwayBehind * 0.5f;
    m_highwayParts.push_back( SpawnBox( Vector3( 0.f, -0.08f, centreZ ), Vector3( m_highwayWidth + 0.3f, 0.04f, length ), Vector3( 0.02f, 0.02f, 0.03f ), Vector3( 0.03f, 0.03f, 0.045f ), mover ) );
    // Edge rails and lane dividers.
    for( int i = 0; i <= static_cast<int>( std::lround( m_highwayWidth / m_laneSpacing ) ); ++i )
    {
        const float x = -halfWidth + static_cast<float>( i ) * m_laneSpacing;
        const bool edge = i == 0 || std::fabs( x - halfWidth ) < 0.01f;
        const float brightness = edge ? 0.35f : 0.14f;
        m_highwayParts.push_back( SpawnBox( Vector3( x, -0.05f, centreZ ), Vector3( edge ? 0.08f : 0.035f, 0.02f, length ), Vector3( brightness, brightness, brightness ), Vector3( brightness, brightness, brightness ), mover ) );
    }
    // Target pads, dim until their lane is hit.
    for( PadId pad : kColumnOrder )
    {
        const int lane = LaneOf( pad );
        const auto entity = m_lanes.find( PadUtils::GetPadId( pad ) );
        if( m_laneNotes[lane].Notes.empty() || entity == m_lanes.end() || !entity->second )
        {
            continue;
        }
        const float x = entity->second->GetComponent<Transform>().GetPosition().x;
        const Vector3 color = PadUtils::GetNoteColor( pad );
        TargetPad target;
        target.Lane = lane;
        target.Color = color;
        target.Pad = SpawnBox( Vector3( x, -0.03f, 0.f ), Vector3( m_laneSpacing * 0.86f, 0.05f, 0.45f ), color * 0.5f, color * 0.35f, mover );
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

    Transform* parent = nullptr;
    const auto kickLane = m_lanes.find( PadUtils::GetPadId( PadId::Bass ) );
    if( kickLane != m_lanes.end() && kickLane->second )
    {
        parent = &kickLane->second->GetComponent<Transform>();
    }
    for( const BeatData& beat : beats )
    {
        const double timeMs = static_cast<double>( beat.m_time ) * 1000.0;
        const float brightness = beat.m_measure ? 0.5f : 0.2f;
        BeatLine line;
        line.TimeMs = timeMs;
        line.Line = SpawnBox( Vector3( 0.f, -0.045f, static_cast<float>( timeMs / 1000.0 ) * m_appliedSpeed ), Vector3( m_highwayWidth, 0.015f, beat.m_measure ? 0.09f : 0.045f ), Vector3( brightness, brightness, brightness ), Vector3( brightness, brightness, brightness ), parent );
        m_beatLines.push_back( line );
    }
    if( CommandLine::Has( "--highway-log" ) && !beats.empty() )
    {
        BRUH_FMT( "Highway: %d beat lines from %s", static_cast<int>( m_beatLines.size() ), source.c_str() );
    }
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
    for( LaneNotes& lane : m_laneNotes )
    {
        for( NoteState& note : lane.Notes )
        {
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
    for( BeatLine& line : m_beatLines )
    {
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
    const double stepMs = std::min( static_cast<double>( inDeltaTime ), 0.1 ) * 1000.0;

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
            m_currentTrackPack.Play();
            m_lastAudioPositionMs = 0;
            m_songState = SongState::Playing;
        }
        break;
    case SongState::Playing:
    {
        m_songTimeMs += stepMs;
        // FMOD's position moves once per mixer block; between moves the clock runs on frame
        // time, and each move steers it so it never drifts or jumps backwards visibly.
        const unsigned int audioMs = m_currentTrackPack.GetPositionMs();
        if( audioMs != m_lastAudioPositionMs )
        {
            m_lastAudioPositionMs = audioMs;
            const double error = static_cast<double>( audioMs ) - m_songTimeMs;
            if( std::fabs( error ) > kClockSnapMs )
            {
                m_songTimeMs = static_cast<double>( audioMs );
            }
            else
            {
                m_songTimeMs += error * kClockCorrection;
            }
        }
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

    // --highway-autoplay [offset ms]: hits every note, with its pad and stroke, at its time plus
    // the offset (a demo, and a way to check judging and scoring without a kit).
    static const bool autoplay = CommandLine::Has( "--highway-autoplay" );
    if( autoplay )
    {
        static const double offsetMs = CommandLine::GetFloat( "--highway-autoplay", 0.f );
        for( int lane = 0; lane < PadId::COUNT; ++lane )
        {
            const LaneNotes& notes = m_laneNotes[lane];
            for( size_t i = notes.Cursor; i < notes.Notes.size() && notes.Notes[i].TimeMs + offsetMs <= judgeTime; ++i )
            {
                const NoteState& note = notes.Notes[i];
                if( !note.Judged )
                {
                    // --highway-autoplay-plain: as a kit that only sends plain strokes and one
                    // hi-hat note would (checks technique judging).
                    static const bool plain = CommandLine::Has( "--highway-autoplay-plain" );
                    const PadId pad = plain && note.Pad == PadId::OpenHiHat ? PadId::ClosedHiHat : note.Pad;
                    outHits.push_back( Hit{ pad, plain ? Articulation::Normal : note.Technique, note.TimeMs + offsetMs, true, true } );
                }
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
    m_stageLights.OnHit( inHit.PadKnown ? inHit.Pad : best->Pad );
    if( wrongTechnique && strictness >= 2 )
    {
        ++m_wrongTechnique;
        for( Decoration& decoration : best->Decorations )
        {
            Tint( decoration.Piece, Vector3( 0.2f, 0.2f, 0.2f ), Vector3( 0.f, 0.f, 0.f ) );
        }
        Tint( best->Note, Vector3( 0.2f, 0.2f, 0.2f ), Vector3( 0.f, 0.f, 0.f ) );
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


void NoteHighwayCore::JudgeMisses( double inJudgeTimeMs )
{
    for( LaneNotes& lane : m_laneNotes )
    {
        while( lane.Cursor < lane.Notes.size() )
        {
            NoteState& note = lane.Notes[lane.Cursor];
            if( !note.Judged )
            {
                if( note.TimeMs + kGoodWindowMs >= inJudgeTimeMs )
                {
                    break;
                }
                note.Judged = true;
                // Missed notes go grey and keep scrolling past.
                Tint( note.Note, Vector3( 0.2f, 0.2f, 0.2f ), Vector3( 0.f, 0.f, 0.f ) );
                for( Decoration& decoration : note.Decorations )
                {
                    Tint( decoration.Piece, Vector3( 0.15f, 0.15f, 0.15f ), Vector3( 0.f, 0.f, 0.f ) );
                }
                ApplyJudgement( Judgement::Miss, 0.0 );
                m_lastHint.clear();
            }
            ++lane.Cursor;
        }
    }
}


void NoteHighwayCore::ApplyJudgement( Judgement inJudgement, double inOffsetMs )
{
    m_judgementAge = 0.f;
    if( inJudgement == Judgement::Miss )
    {
        m_stageLights.OnMiss();
        ++m_missed;
        m_combo = 0;
        m_lastJudgement = "MISS";
        m_lastTiming.clear();
        SetDrumsAudible( false );
        return;
    }

    ++m_combo;
    m_maxCombo = std::max( m_maxCombo, m_combo );
    int points = 0;
    switch( inJudgement )
    {
    case Judgement::Perfect: ++m_perfect; points = 100; m_lastJudgement = "PERFECT"; break;
    case Judgement::Great: ++m_great; points = 75; m_lastJudgement = "GREAT"; break;
    default: ++m_good; points = 50; m_lastJudgement = "GOOD"; break;
    }
    m_score += points * Multiplier( m_combo );
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


void NoteHighwayCore::ResetScore()
{
    m_score = m_combo = m_maxCombo = m_perfect = m_great = m_good = m_missed = m_wrongTechnique = 0;
    m_lastJudgement.clear();
    m_lastHint.clear();
    m_lastTiming.clear();
    m_judgementAge = 10.f;
    if( RmlUiCore* ui = GetEngine().RmlUi )
    {
        ui->ModelEnsure( kModel );
        ui->ModelSetNumber( kModel, "playing", 0 );
        ui->ModelSetNumber( kModel, "finished", 0 );
        ui->ModelSetNumber( kModel, "countdown", 0 );
        ui->ModelSetNumber( kModel, "track_index", m_trackIndex );
        ui->ModelSetNumber( kModel, "total_notes", m_totalNotes );
        for( const char* key : { "track_title", "track_artist", "judgement", "timing", "hint", "accuracy", "judgement_opacity" } )
        {
            ui->ModelSetString( kModel, key, "" );
        }
    }
    UpdateHud( 0.f );
}


void NoteHighwayCore::UpdateHud( float inDeltaTime )
{
    RmlUiCore* ui = GetEngine().RmlUi;
    if( !ui )
    {
        return;
    }
    m_judgementAge += inDeltaTime;
    const int judged = m_perfect + m_great + m_good + m_missed;
    const double accuracy = judged > 0 ? ( m_perfect + m_great * 0.75 + m_good * 0.5 ) * 100.0 / judged : 100.0;
    char accuracyText[16];
    std::snprintf( accuracyText, sizeof( accuracyText ), "%.1f%%", accuracy );
    // The judgement holds for a moment, then fades.
    const float opacity = std::clamp( 1.f - ( m_judgementAge - 0.35f ) / 0.3f, 0.f, 1.f );

    ui->ModelSetNumber( kModel, "playing", m_songState != SongState::Idle );
    ui->ModelSetNumber( kModel, "finished", m_songState == SongState::Finished );
    ui->ModelSetNumber( kModel, "countdown", m_songState == SongState::LeadIn || m_songState == SongState::Loading ? std::ceil( -m_songTimeMs / 1000.0 ) : 0.0 );
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
    ui->ModelSetString( kModel, "judgement_opacity", std::to_string( opacity ) );
}


void NoteHighwayCore::Update( const UpdateContext& context )
{
    std::vector<Hit> hits;
    if( m_isPaused || m_songState == SongState::Idle || m_songState == SongState::Finished )
    {
        // Keep the MIDI queue empty so nothing stale is judged on resume.
        MidiDevice::GetInstance().PumpMessages();
        UpdateHud( context.GetDeltaTime() );
        return;
    }

    ApplyPendingTints();
    ApplySpeed();
    UpdateSongClock( context.GetDeltaTime() );
    GatherHits( hits );
    for( const Hit& hit : hits )
    {
        JudgeHit( hit );
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

    UpdateTargetPads( context.GetDeltaTime() );
    m_stageLights.Update( VisualTimeMs(), context.GetDeltaTime() );

    // Done once every note has passed and the audio has stopped (or ran out long ago).
    if( m_songState == SongState::Playing && judgeTime > m_lastNoteMs + kGoodWindowMs )
    {
        const double lengthMs = static_cast<double>( m_currentTrackPack.GetLength() );
        if( !m_currentTrackPack.IsPlaying() || m_songTimeMs > lengthMs + 2000.0 )
        {
            m_songState = SongState::Finished;
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
        BRUH_FMT( "Highway: song %.1f ms, audio %u ms, judged %d (missed %d) of %d, first note %.0f ms",
            m_songTimeMs, m_currentTrackPack.GetPositionMs(), m_perfect + m_great + m_good + m_missed, m_missed, m_totalNotes, m_firstNoteMs );
    }
}


#if USING( ME_EDITOR )

void NoteHighwayCore::OnEditorInspect()
{
}

#endif
