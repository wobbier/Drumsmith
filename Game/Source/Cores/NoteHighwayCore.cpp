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
#include "MidiFile.h"
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
    constexpr PadId kColumnOrder[] = { PadId::Crash1, PadId::ClosedHiHat, PadId::Snare, PadId::HighTom, PadId::MidTom, PadId::FloorTom, PadId::Ride, PadId::Crash2 };
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
            m_laneNotes[LaneOf( note.m_editorLane )].Notes.push_back( NoteState{ static_cast<double>( note.m_triggerTime ) * 1000.0 } );
        }
    }
    LayoutLanes();
    if( CommandLine::Has( "--highway-log" ) )
    {
        BRUH_FMT( "Highway: playing %s (track %d)", inTrackData.m_trackName.c_str(), inTrackIndex );
    }

    World& world = GetWorld();
    const float laneSpacing = m_laneSpacing;
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
        std::string prefabName = "Assets/Prefabs/Notes/NewBaseNote.prefab";
        if( !m_notePrefabs[it->m_editorLane].empty() )
        {
            prefabName = m_notePrefabs[it->m_editorLane];
        }
        EntityHandle note = world.CreateFromPrefab( prefabName );

        auto& transform = note->GetComponent<Transform>();
        auto& meshComp = note->GetComponent<Mesh>();
        const bool kick = it->m_editorLane == PadId::Bass;
        const Vector3 color = kick ? meshComp.MeshMaterial->DiffuseColor : PadUtils::GetNoteColor( it->m_editorLane );
        Tint( note, color, color * kGemGlow );
        transform.SetPosition( Vector3( 0, 0, it->m_triggerTime * m_appliedSpeed ) );
        Vector3 scale = transform.GetScale();
        if( kick )
        {
            scale = Vector3( m_highwayWidth / kKickMeshWidth, 0.12f, 0.3f );
        }
        else
        {
            scale = Vector3( laneSpacing * 0.9f / kNoteMeshWidth, kGemHeight, kGemDepth );
        }
        transform.SetScale( scale );
        transform.SetName( it->m_noteName + std::to_string( (uint8_t)it->m_editorLane ) );
        const auto lane = m_lanes.find( it->m_noteName );
        if( lane != m_lanes.end() && lane->second )
        {
            transform.SetParent( lane->second->GetComponent<Transform>() );
        }
        else
        {
            YIKES( "NoteHighwayCore: no lane for note '" + it->m_noteName + "'" );
        }
        auto& noteComp = note->AddComponent<NoteTrigger>();
        noteComp.TriggerTime = it->m_triggerTime;
        noteComp.TriggerTimeMS = it->m_triggerTimeMS;
        noteComp.NoteName = it->m_noteName;
        noteComp.EditorLane = it->m_editorLane;
        noteComp.EditorLaneName = PadUtils::GetPadName( it->m_editorLane );

        LaneNotes& laneNotes = m_laneNotes[LaneOf( it->m_editorLane )];
        size_t& next = nextInLane[LaneOf( it->m_editorLane )];
        if( next < laneNotes.Notes.size() )
        {
            laneNotes.Notes[next++].Note = note;
        }
        m_lastNoteMs = std::max( m_lastNoteMs, static_cast<double>( it->m_triggerTime ) * 1000.0 );
        m_firstNoteMs = std::min( m_firstNoteMs, static_cast<double>( it->m_triggerTime ) * 1000.0 );
        ++m_totalNotes;
    }

    BuildHighway();
    BuildBeatLines();

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


void NoteHighwayCore::LayoutLanes()
{
    // Only the columns this chart uses, spread evenly and centred on the kick.
    std::vector<PadId> columns;
    for( PadId pad : kColumnOrder )
    {
        if( !m_laneNotes[LaneOf( pad )].Notes.empty() )
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
    }
}


void NoteHighwayCore::BuildBeatLines()
{
    // Beat and measure lines come from the chart's own tempo map (notes.mid next to the song).
    // Charts without one get none: TrackData's BPM is a placeholder, and wrong lines read worse
    // than no lines.
    const std::string& source = m_trackData->m_trackSourcePath;
    const size_t slash = source.find_last_of( '/' );
    if( slash == std::string::npos )
    {
        return;
    }
    const Path midiPath( source.substr( 0, slash ) + "/notes.mid" );
    if( !midiPath.Exists )
    {
        return;
    }
    smf::MidiFile midi;
    if( !midi.read( midiPath.FullPath ) )
    {
        return;
    }
    midi.doTimeAnalysis();
    const int ticksPerQuarter = midi.getTicksPerQuarterNote();
    if( ticksPerQuarter <= 0 )
    {
        return;
    }

    // Time signature changes (tick, beats per measure, beat length in ticks); 4/4 until the first.
    struct Signature { int Tick; int Beats; int BeatTicks; };
    std::vector<Signature> signatures{ { 0, 4, ticksPerQuarter } };
    for( int track = 0; track < midi.getTrackCount(); ++track )
    {
        for( int i = 0; i < midi[track].size(); ++i )
        {
            const smf::MidiEvent& event = midi[track][i];
            if( event.isTimeSignature() && event.size() >= 5 )
            {
                const int beats = std::max( 1, static_cast<int>( event[3] ) );
                const int beatTicks = std::max( 1, ticksPerQuarter * 4 / ( 1 << std::min( 6, static_cast<int>( event[4] ) ) ) );
                if( event.tick == 0 )
                {
                    signatures[0] = { 0, beats, beatTicks };
                }
                else
                {
                    signatures.push_back( { event.tick, beats, beatTicks } );
                }
            }
        }
    }
    std::sort( signatures.begin(), signatures.end(), []( const Signature& a, const Signature& b ) { return a.Tick < b.Tick; } );

    Transform* parent = nullptr;
    const auto kickLane = m_lanes.find( PadUtils::GetPadId( PadId::Bass ) );
    if( kickLane != m_lanes.end() && kickLane->second )
    {
        parent = &kickLane->second->GetComponent<Transform>();
    }
    const double endMs = m_lastNoteMs + 4000.0;
    size_t signature = 0;
    int beatInMeasure = 0;
    for( int tick = 0; tick >= 0; tick += signatures[signature].BeatTicks )
    {
        while( signature + 1 < signatures.size() && tick >= signatures[signature + 1].Tick )
        {
            ++signature;
            tick = signatures[signature].Tick;
            beatInMeasure = 0;
        }
        // The library answers -1 past the file's last event (it doesn't extrapolate the tempo).
        const double timeMs = midi.getTimeInSeconds( tick ) * 1000.0;
        if( ( tick > 0 && timeMs < 0.0 ) || timeMs > endMs || m_beatLines.size() >= 4000 )
        {
            break;
        }
        const bool measure = beatInMeasure == 0;
        beatInMeasure = ( beatInMeasure + 1 ) % signatures[signature].Beats;
        const float brightness = measure ? 0.5f : 0.2f;
        BeatLine line;
        line.TimeMs = timeMs;
        line.Line = SpawnBox( Vector3( 0.f, -0.045f, static_cast<float>( timeMs / 1000.0 ) * m_appliedSpeed ), Vector3( m_highwayWidth, 0.015f, measure ? 0.09f : 0.045f ), Vector3( brightness, brightness, brightness ), Vector3( brightness, brightness, brightness ), parent );
        m_beatLines.push_back( line );
    }
    if( CommandLine::Has( "--highway-log" ) )
    {
        BRUH_FMT( "Highway: %d beat lines from %s", static_cast<int>( m_beatLines.size() ), midiPath.GetLocalPathString().c_str() );
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
            if( note.Note )
            {
                Transform& transform = note.Note->GetComponent<Transform>();
                Vector3 position = transform.GetPosition();
                position.z = static_cast<float>( note.TimeMs / 1000.0 ) * speed;
                transform.SetPosition( position );
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


void NoteHighwayCore::GatherHits( std::vector<Hit>& outHits )
{
    PadMappingStorage& storage = PadMappingStorage::GetInstance();
    const double judgeTime = JudgeTimeMs();

    Input& input = GetEngine().GetInput();
    for( const PadDefinition& pad : storage.mappedPads )
    {
        if( pad.keyboardBinding > 0 && input.WasKeyPressed( static_cast<KeyCode>( pad.keyboardBinding ) ) )
        {
            outHits.push_back( Hit{ static_cast<PadId>( pad.padId ), judgeTime } );
        }
    }

    // Drained every frame, so a hit is never left to land on a later note. Each is judged at the
    // moment it arrived, not when this frame read it.
    for( const MidiMessageNew& msg : MidiDevice::GetInstance().PumpMessages() )
    {
        if( !msg.IsOnType() )
        {
            continue;
        }
        const double ageMs = std::clamp( std::chrono::duration<double, std::milli>( m_songClockStamp - msg.m_arrival ).count(), 0.0, kMaxInputAgeMs );
        for( const PadDefinition& pad : storage.mappedPads )
        {
            if( pad.midiBinding == msg.m_data1 )
            {
                outHits.push_back( Hit{ static_cast<PadId>( pad.padId ), judgeTime - ageMs } );
            }
        }
    }

    // --highway-autoplay [offset ms]: hits every note at its time plus the offset (a demo, and a
    // way to check judging and scoring without a kit).
    static const bool autoplay = CommandLine::Has( "--highway-autoplay" );
    if( autoplay )
    {
        static const double offsetMs = CommandLine::GetFloat( "--highway-autoplay", 0.f );
        for( int lane = 0; lane < PadId::COUNT; ++lane )
        {
            const LaneNotes& notes = m_laneNotes[lane];
            for( size_t i = notes.Cursor; i < notes.Notes.size() && notes.Notes[i].TimeMs + offsetMs <= judgeTime; ++i )
            {
                if( !notes.Notes[i].Judged )
                {
                    outHits.push_back( Hit{ static_cast<PadId>( lane ), notes.Notes[i].TimeMs + offsetMs } );
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

    best->Judged = true;
    if( best->Note )
    {
        // Gone this frame, not when the deletion is processed next frame.
        best->Note->GetComponent<Transform>().SetScale( 0.f );
        best->Note->MarkForDelete();
        best->Note = EntityHandle();
    }
    FlashLane( LaneOf( inHit.Pad ) );
    const double magnitude = std::fabs( bestOffset );
    const Judgement judgement = magnitude <= kPerfectWindowMs ? Judgement::Perfect : magnitude <= kGreatWindowMs ? Judgement::Great : Judgement::Good;
    ApplyJudgement( judgement, bestOffset );
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
                ApplyJudgement( Judgement::Miss, 0.0 );
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
    m_lastTiming = inJudgement == Judgement::Perfect ? std::string() : ( offset < 0 ? "EARLY " : "LATE +" ) + std::to_string( offset ) + " ms";
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
    m_score = m_combo = m_maxCombo = m_perfect = m_great = m_good = m_missed = 0;
    m_lastJudgement.clear();
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
        for( const char* key : { "track_title", "track_artist", "judgement", "timing", "accuracy", "judgement_opacity" } )
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
