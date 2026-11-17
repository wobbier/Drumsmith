#include "TrackEditor.h"
#include "CoreGame/BeatGrid.h"
#include "CoreGame/Drumset.h"
#include "CoreGame/TrackList.h"
#include "Cores/AudioCore.h"
#include "Engine/Engine.h"
#include "Events/GameEvents.h"
#include "Events/HavanaEvents.h"
#include "misc/cpp/imgui_stdlib.h"
#include "optick.h"
#include <algorithm>
#include <chrono>
#include <cmath>

#if USING(ME_EDITOR)
#include <Editor/AutomationCommands.h>
#include <Editor/EditorActions.h>
#include <Utils/EditorIcons.h>

namespace
{
    constexpr const char* kEditorWindow = "Track Editor";
    constexpr const char* kDetailsWindow = "Track Details";

    // Grid steps per beat, and what a charter calls them in 4/4.
    constexpr int kDivisions[] = { 1, 2, 3, 4, 6, 8, 12 };
    constexpr const char* kDivisionNames[] = { "1/4", "1/8", "1/8 triplet", "1/16", "1/16 triplet", "1/32", "1/32 triplet" };

    std::string ClockText( double inSeconds )
    {
        const int minutes = static_cast<int>( inSeconds ) / 60;
        char text[32];
        snprintf( text, sizeof( text ), "%d:%06.3f", minutes, inSeconds - minutes * 60.0 );
        return text;
    }


    std::string Lower( std::string inText )
    {
        std::transform( inText.begin(), inText.end(), inText.begin(), []( unsigned char c ) { return static_cast<char>( std::tolower( c ) ); } );
        return inText;
    }
}


TrackEditor::TrackEditor()
    : HavanaWidget( kEditorWindow )
{
    Listen<EditTrackEvent>( [this]( const EditTrackEvent& event ) {
        const auto& tracks = TrackDatabase::GetInstance().m_trackList.m_tracks;
        for( int i = 0; i < static_cast<int>( tracks.size() ); ++i )
        {
            if( tracks[i].m_trackName == event.FileName )
            {
                IsOpen = true;
                RequestOpen( i );
                return;
            }
        }
    } );
}


TrackEditor::~TrackEditor()
{
}


void TrackEditor::Init()
{
    m_padStates.resize( static_cast<size_t>( PadId::COUNT ) );
    m_drums = new Drumset( GetEngine().AudioThread->GetSystem() );
    InstallActionRouting();
    AutomationCommands::Register( "track-", [this]( const std::string& command, const std::string& args, std::string& error ) {
        return ExecuteAutomation( command, args, error );
    } );
}


void TrackEditor::Destroy()
{
    AutomationCommands::Unregister( "track-" );
    m_preview.Stop();
    m_transport.Close();
    m_document.Close();
    delete m_drums;
    m_drums = nullptr;
}


void TrackEditor::Update()
{
}


void TrackEditor::OpenTrack( const TrackData& inTrack )
{
    StopRecording();
    m_playPending = false;
    m_preview.Stop();
    m_transport.Close();
    m_document.Open( inTrack );
    m_transport.Open( m_document.Chart, m_document.Duration() );
    m_timeline.ViewStart = 0.0;
    m_timeline.ScrollY = 0.f;
    m_pendingOpen = -1;
}


void TrackEditor::Save()
{
    if( !m_document.IsOpen() )
    {
        return;
    }
    StopRecording();
    m_document.Save();
    // The library's copy, so the song list and a play pick the edit up without a reload.
    for( TrackData& track : TrackDatabase::GetInstance().m_trackList.m_tracks )
    {
        if( track.m_trackSourcePath == m_document.Chart.m_trackSourcePath )
        {
            track = m_document.Chart;
            break;
        }
    }
}


void TrackEditor::RequestOpen( int inIndex )
{
    const auto& tracks = TrackDatabase::GetInstance().m_trackList.m_tracks;
    if( inIndex < 0 || inIndex >= static_cast<int>( tracks.size() ) )
    {
        return;
    }
    if( m_document.IsDirty() )
    {
        m_pendingOpen = inIndex;
        return;
    }
    OpenTrack( tracks[inIndex] );
}


void TrackEditor::InstallActionRouting()
{
    // The focused document takes the edit shortcuts (as the sequence editor and shader graphs do).
    auto& actions = EditorActions::Get();
    auto claims = actions.DocumentClaims;
    auto execute = actions.DocumentExecute;
    actions.DocumentClaims = [this, claims]( const std::string& id ) { return ClaimsAction( id ) || ( claims && claims( id ) ); };
    actions.DocumentExecute = [this, claims, execute]( const std::string& id ) {
        if( ClaimsAction( id ) ) ExecuteAction( id );
        else if( claims && execute && claims( id ) ) execute( id );
    };
}


bool TrackEditor::ClaimsAction( const std::string& inId ) const
{
    if( !IsOpen || !m_focused || !m_document.IsOpen() )
    {
        return false;
    }
    return inId == "Edit.Undo" || inId == "Edit.Redo" || inId == "Edit.Copy" || inId == "Edit.Cut" || inId == "Edit.Paste" || inId == "Edit.Duplicate"
        || inId == "Edit.Delete" || inId == "Edit.SelectAll" || inId == "Edit.Deselect" || inId == "File.Save";
}


void TrackEditor::ExecuteAction( const std::string& inId )
{
    if( inId == "Edit.Undo" ) { StopRecording(); m_document.Undo(); }
    else if( inId == "Edit.Redo" ) { StopRecording(); m_document.Redo(); }
    else if( inId == "Edit.Copy" ) m_document.Copy();
    else if( inId == "Edit.Cut" ) m_document.Cut();
    else if( inId == "Edit.Paste" ) m_document.Paste( m_timeline.SnapTime( m_document, m_transport.Seconds() ) );
    else if( inId == "Edit.Duplicate" ) m_document.Duplicate();
    else if( inId == "Edit.Delete" ) m_document.DeleteSelection();
    else if( inId == "Edit.SelectAll" ) m_document.SelectAll( m_timeline.VisibleTracks( m_document ) );
    else if( inId == "Edit.Deselect" ) m_document.Selection.clear();
    else if( inId == "File.Save" ) Save();
}


void TrackEditor::Render()
{
    OPTICK_CATEGORY( "TrackEditor::Render", Optick::Category::UI );
    if( !IsOpen )
    {
        if( m_transport.IsPlaying() )
        {
            m_transport.Pause();
        }
        m_focused = false;
        return;
    }

    m_transport.Update( ImGui::GetIO().DeltaTime );
    bool focused = false;

    DrawDetails();
    focused = focused || ImGui::IsWindowFocused( ImGuiFocusedFlags_RootAndChildWindows );
    ImGui::End();

    ImGui::Begin( kEditorWindow, &IsOpen, ImGuiWindowFlags_MenuBar | ImGuiWindowFlags_NoScrollbar | ImGuiWindowFlags_NoScrollWithMouse | ( m_document.IsDirty() ? ImGuiWindowFlags_UnsavedDocument : 0 ) );
    focused = focused || ImGui::IsWindowFocused( ImGuiFocusedFlags_RootAndChildWindows );
    DrawMenuBar();
    if( !m_document.IsOpen() )
    {
        ImGui::TextUnformatted( "Pick a song to chart." );
        DrawTrackPicker();
    }
    else
    {
        DrawToolbar();
        const float padStrip = m_showPadPreview ? 62.f : 0.f;
        const ImVec2 available = ImGui::GetContentRegionAvail();
        m_timeline.Draw( m_document, m_transport, { available.x, std::max( 120.f, available.y - padStrip ) } );
        if( m_showPadPreview )
        {
            DrawPadPreview();
        }
    }

    if( m_openPicker )
    {
        ImGui::OpenPopup( "Open Track" );
        m_openPicker = false;
    }
    ImGui::SetNextWindowSize( { 460.f, 520.f }, ImGuiCond_Appearing );
    if( ImGui::BeginPopup( "Open Track" ) )
    {
        DrawTrackPicker();
        ImGui::EndPopup();
    }
    if( m_pendingOpen >= 0 )
    {
        ImGui::OpenPopup( "Unsaved Chart" );
    }
    if( ImGui::BeginPopupModal( "Unsaved Chart", nullptr, ImGuiWindowFlags_AlwaysAutoResize ) )
    {
        const auto& tracks = TrackDatabase::GetInstance().m_trackList.m_tracks;
        ImGui::Text( "%s has changes that aren't saved.", m_document.Chart.m_trackName.c_str() );
        const bool valid = m_pendingOpen >= 0 && m_pendingOpen < static_cast<int>( tracks.size() );
        if( ImGui::Button( "Save and Open" ) && valid )
        {
            Save();
            OpenTrack( tracks[m_pendingOpen] );
            ImGui::CloseCurrentPopup();
        }
        ImGui::SameLine();
        if( ImGui::Button( "Discard and Open" ) && valid )
        {
            OpenTrack( tracks[m_pendingOpen] );
            ImGui::CloseCurrentPopup();
        }
        ImGui::SameLine();
        if( ImGui::Button( "Cancel" ) || !valid )
        {
            m_pendingOpen = -1;
            ImGui::CloseCurrentPopup();
        }
        ImGui::EndPopup();
    }
    ImGui::End();

    // A menu or popup of ours keeps the focus.
    m_focused = focused || ( m_focused && ImGui::IsPopupOpen( "", ImGuiPopupFlags_AnyPopupId | ImGuiPopupFlags_AnyPopupLevel ) );

    if( m_document.IsOpen() )
    {
        HandleRecording();
        HandleKeys();
        // A properties edit ends when its widget is let go.
        if( m_propertyEdit && !ImGui::IsAnyItemActive() )
        {
            m_document.CommitEdit( "Edit Properties" );
            m_propertyEdit = false;
        }
        m_preview.Update( m_document, m_transport );
        if( m_playPending && !m_preview.IsStarting() )
        {
            m_playPending = false;
            m_transport.Play();
        }
    }
}


void TrackEditor::DrawMenuBar()
{
    if( !ImGui::BeginMenuBar() )
    {
        return;
    }
    const bool open = m_document.IsOpen();
    if( ImGui::BeginMenu( "File" ) )
    {
        if( ImGui::MenuItem( "Open Track..." ) )
        {
            m_openPicker = true;
        }
        if( ImGui::MenuItem( "Save Track", "Ctrl+S", false, open ) )
        {
            Save();
        }
        ImGui::EndMenu();
    }
    if( ImGui::BeginMenu( "Edit", open ) )
    {
        const bool any = !m_document.Selection.empty();
        if( ImGui::MenuItem( ( "Undo " + m_document.History.GetUndoName() ).c_str(), "Ctrl+Z", false, m_document.History.CanUndo() ) ) ExecuteAction( "Edit.Undo" );
        if( ImGui::MenuItem( ( "Redo " + m_document.History.GetRedoName() ).c_str(), "Ctrl+Y", false, m_document.History.CanRedo() ) ) ExecuteAction( "Edit.Redo" );
        ImGui::Separator();
        if( ImGui::MenuItem( "Cut", "Ctrl+X", false, any ) ) ExecuteAction( "Edit.Cut" );
        if( ImGui::MenuItem( "Copy", "Ctrl+C", false, any ) ) ExecuteAction( "Edit.Copy" );
        if( ImGui::MenuItem( "Paste at Playhead", "Ctrl+V", false, m_document.CanPaste() ) ) ExecuteAction( "Edit.Paste" );
        if( ImGui::MenuItem( "Duplicate", "Ctrl+D", false, any ) ) ExecuteAction( "Edit.Duplicate" );
        if( ImGui::MenuItem( "Delete", "Del", false, any ) ) ExecuteAction( "Edit.Delete" );
        ImGui::Separator();
        if( ImGui::MenuItem( "Select All", "Ctrl+A" ) ) ExecuteAction( "Edit.SelectAll" );
        if( ImGui::MenuItem( "Snap Selection to Grid", nullptr, false, any ) ) m_document.SnapSelection( m_timeline.SnapDivision );
        ImGui::EndMenu();
    }
    if( ImGui::BeginMenu( "View", open ) )
    {
        for( int group = 0; group < static_cast<int>( TrackGroup::Count ); ++group )
        {
            bool shown = !m_timeline.Hidden[group];
            if( ImGui::MenuItem( TrackGroupName( static_cast<TrackGroup>( group ) ), nullptr, &shown ) )
            {
                m_timeline.Hidden[group] = !shown;
            }
        }
        ImGui::Separator();
        // Presets for who is at the desk.
        if( ImGui::MenuItem( "Charting: Notes and Gameplay" ) )
        {
            for( int group = 0; group < static_cast<int>( TrackGroup::Count ); ++group )
            {
                m_timeline.Hidden[group] = group != static_cast<int>( TrackGroup::Notes ) && group != static_cast<int>( TrackGroup::Gameplay ) && group != static_cast<int>( TrackGroup::Structure );
            }
            m_preview.SetMode( PreviewSession::Mode::Highway );
        }
        if( ImGui::MenuItem( "Venue: Show and Band" ) )
        {
            for( int group = 0; group < static_cast<int>( TrackGroup::Count ); ++group )
            {
                m_timeline.Hidden[group] = group == static_cast<int>( TrackGroup::Notes ) || group == static_cast<int>( TrackGroup::Gameplay );
                m_timeline.Collapsed[group] = false;
            }
            m_preview.SetMode( PreviewSession::Mode::Scene );
        }
        if( ImGui::MenuItem( "Everything" ) )
        {
            m_timeline.Hidden.fill( false );
            m_preview.SetMode( PreviewSession::Mode::Both );
        }
        ImGui::Separator();
        ImGui::MenuItem( "Follow Playhead", nullptr, &m_timeline.Follow );
        if( ImGui::MenuItem( "Loop", "L", m_transport.IsLooping() ) ) ToggleLoop();
        if( ImGui::MenuItem( "Clear Loop", nullptr, false, m_transport.HasLoop() ) ) m_transport.ClearLoop();
        ImGui::MenuItem( "Pad Preview", nullptr, &m_showPadPreview );
        if( ImGui::MenuItem( "Zoom to Fit" ) ) m_timeline.ZoomToFit( m_document );
        ImGui::EndMenu();
    }
    if( open )
    {
        // The song, and whether it has changes to save.
        const std::string song = m_document.Chart.m_artistName + " - " + m_document.Chart.m_trackName + ( m_document.IsDirty() ? "  (unsaved)" : "" );
        ImGui::SameLine( std::max( ImGui::GetCursorPosX() + 20.f, ImGui::GetWindowWidth() - ImGui::CalcTextSize( song.c_str() ).x - 16.f ) );
        ImGui::TextDisabled( "%s", song.c_str() );
    }
    ImGui::EndMenuBar();
}


void TrackEditor::TogglePlay()
{
    if( m_transport.IsPlaying() || m_playPending )
    {
        m_playPending = false;
        m_transport.Pause();
        return;
    }
    if( !m_preview.IsActive() && m_preview.Start( m_document ) && m_preview.IsStarting() )
    {
        // Entering play stops all audio: the song starts when the game is up.
        m_playPending = true;
        return;
    }
    m_transport.Play();
}


void TrackEditor::ToggleLoop()
{
    if( m_transport.HasLoop() )
    {
        m_transport.SetLooping( !m_transport.IsLooping() );
        return;
    }
    double start = 0.0;
    double end = 0.0;
    if( !m_document.SelectionSpan( start, end ) || end - start < Transport::kMinLoop )
    {
        const TrackData& chart = m_document.Chart;
        const double playhead = m_transport.Seconds();
        const std::vector<TimedCueData>& sections = chart.m_venue.m_sections;
        int section = -1;
        for( size_t i = 0; i < sections.size() && sections[i].m_time <= playhead; ++i )
        {
            section = static_cast<int>( i );
        }
        if( section >= 0 )
        {
            start = sections[section].m_time;
            end = section + 1 < static_cast<int>( sections.size() ) ? sections[section + 1].m_time : m_transport.Length();
        }
        else
        {
            const float bpm = static_cast<float>( chart.m_bpm );
            start = m_timeline.SnapTime( m_document, playhead );
            end = BeatGrid::TimeOfBeat( chart.m_beats, bpm, BeatGrid::BeatOfTime( chart.m_beats, bpm, start ) + 16.0 );
        }
    }
    m_transport.SetLoop( start, end );
}


void TrackEditor::DrawToolbar()
{
    constexpr float kGroupGap = 16.f;
    constexpr float kItemGap = 4.f;

    // Transport.
    const bool playing = m_transport.IsPlaying() || m_playPending;
    if( EditorIcons::Button( playing ? "player-pause" : "player-play", "Play / Pause", "Plays the song from the playhead, in the Game View too (Space)." ) )
    {
        TogglePlay();
    }
    ImGui::SameLine( 0.f, kItemGap );
    if( EditorIcons::Button( "player-stop", "Stop", "Stops and goes back to the start." ) )
    {
        m_playPending = false;
        m_transport.Stop();
    }
    ImGui::SameLine( 0.f, kItemGap );
    if( EditorIcons::Button( "player-record", "Record", "While the song plays, pad hits (MIDI or the bound keys) become notes.", true, m_recording ) )
    {
        if( m_recording )
        {
            StopRecording();
        }
        else
        {
            m_recording = true;
        }
    }
    ImGui::SameLine( 0.f, kItemGap );
    if( EditorIcons::Button( "repeat", "Loop", "Repeats the loop zone (L). Ctrl-drag on the ruler marks one out, its edges drag, and a right-click there has the rest. Not saved with the song.", true, m_transport.IsLooping() ) )
    {
        ToggleLoop();
    }
    ImGui::SameLine( 0.f, kItemGap );
    if( EditorIcons::Button( "current-location", "Follow Playhead", "The timeline scrolls to keep the playhead in view while the song plays. Off, the view stays where it is.", true, m_timeline.Follow ) )
    {
        m_timeline.Follow = !m_timeline.Follow;
    }

    // The clock, in a slot wide enough for any time so nothing after it moves.
    ImGui::SameLine( 0.f, kGroupGap );
    const float clockStart = ImGui::GetCursorPosX();
    const float clockWidth = ImGui::CalcTextSize( "00:00.000 / 00:00.000" ).x;
    ImGui::AlignTextToFramePadding();
    ImGui::Text( "%s / %s", ClockText( m_transport.Seconds() ).c_str(), ClockText( m_transport.Length() ).c_str() );
    ImGui::SameLine( clockStart + clockWidth, kGroupGap );

    // Speed and volume.
    if( EditorIcons::Button( "gauge", "Speed", "Playback speed. Click to go back to 1.00x." ) )
    {
        m_transport.SetSpeed( 1.f );
    }
    ImGui::SameLine( 0.f, kItemGap );
    float speed = m_transport.Speed();
    ImGui::SetNextItemWidth( 80.f );
    if( ImGui::SliderFloat( "##speed", &speed, 0.25f, 1.5f, "%.2fx" ) )
    {
        m_transport.SetSpeed( speed );
    }
    ImGui::SameLine( 0.f, kItemGap * 2.f );
    const bool audio = m_transport.HasAudio();
    float volume = m_transport.Volume();
    const bool muted = volume <= 0.f;
    if( EditorIcons::Button( !audio || muted ? "volume-off" : "volume", "Volume", audio ? "The song's volume in the editor. Click to mute." : "This song has no audio to play.", audio, audio && muted ) )
    {
        if( !muted )
        {
            m_unmutedVolume = volume;
        }
        m_transport.SetVolume( muted ? m_unmutedVolume : 0.f );
    }
    ImGui::SameLine( 0.f, kItemGap );
    ImGui::BeginDisabled( !audio );
    ImGui::SetNextItemWidth( 70.f );
    if( ImGui::SliderFloat( "##volume", &volume, 0.f, 1.f, "%.1f" ) )
    {
        m_transport.SetVolume( volume );
    }
    ImGui::EndDisabled();
    ImGui::SameLine( 0.f, kItemGap );
    const bool drumStems = m_transport.HasDrumStems();
    if( EditorIcons::Button( "headphones", "Drums Only", drumStems ? "Plays the drum stems alone." : "This song has no separate drum stems.", drumStems, drumStems && m_transport.DrumsOnly() ) )
    {
        m_transport.SetDrumsOnly( !m_transport.DrumsOnly() );
    }

    // Snapping.
    ImGui::SameLine( 0.f, kGroupGap );
    if( EditorIcons::Button( "magnet", "Snap", "Edits land on the grid.", true, m_timeline.SnapEnabled ) )
    {
        m_timeline.SnapEnabled = !m_timeline.SnapEnabled;
    }
    ImGui::SameLine( 0.f, kItemGap );
    int division = 3;
    for( int i = 0; i < IM_ARRAYSIZE( kDivisions ); ++i )
    {
        if( kDivisions[i] == m_timeline.SnapDivision )
        {
            division = i;
        }
    }
    ImGui::SetNextItemWidth( 110.f );
    if( ImGui::Combo( "##grid", &division, kDivisionNames, IM_ARRAYSIZE( kDivisionNames ) ) )
    {
        m_timeline.SnapDivision = kDivisions[division];
    }
    if( ImGui::IsItemHovered() )
    {
        ImGui::SetTooltip( "The grid: how a beat is divided." );
    }

    // The game preview, last: its status text has nothing after it to push.
    ImGui::SameLine( 0.f, kGroupGap );
    m_preview.DrawControls( m_document );
}


void TrackEditor::DrawTrackPicker()
{
    const auto& tracks = TrackDatabase::GetInstance().m_trackList.m_tracks;
    ImGui::SetNextItemWidth( -1.f );
    ImGui::InputTextWithHint( "##filter", "Search songs", &m_pickerFilter );
    const std::string filter = Lower( m_pickerFilter );
    ImGui::BeginChild( "##songs", { 0.f, 0.f } );
    for( int i = 0; i < static_cast<int>( tracks.size() ); ++i )
    {
        const std::string label = tracks[i].m_artistName + " - " + tracks[i].m_trackName;
        if( !filter.empty() && Lower( label ).find( filter ) == std::string::npos )
        {
            continue;
        }
        ImGui::PushID( i );
        if( ImGui::Selectable( label.c_str() ) )
        {
            RequestOpen( i );
            ImGui::CloseCurrentPopup();
        }
        ImGui::PopID();
    }
    if( tracks.empty() )
    {
        ImGui::TextDisabled( "No songs in Assets/DLC." );
    }
    ImGui::EndChild();
}


void TrackEditor::DrawDetails()
{
    // The caller ends the window.
    ImGui::Begin( kDetailsWindow, nullptr );
    if( !m_document.IsOpen() )
    {
        ImGui::TextDisabled( "No song open." );
        return;
    }
    TrackData& chart = m_document.Chart;
    if( ImGui::CollapsingHeader( "Song", ImGuiTreeNodeFlags_DefaultOpen ) )
    {
        bool changed = false;
        changed |= ImGui::InputText( "Title", &chart.m_trackName );
        changed |= ImGui::InputText( "Artist", &chart.m_artistName );
        changed |= ImGui::InputInt( "BPM", &chart.m_bpm, 1, 10 );
        chart.m_bpm = std::clamp( chart.m_bpm, 20, 400 );
        if( ImGui::Button( "Set Song Preview Start to Playhead" ) && m_transport.Length() > 0.0 )
        {
            chart.m_previewPercent = static_cast<float>( m_transport.Seconds() / m_transport.Length() );
            changed = true;
        }
        m_document.MetaDirty = m_document.MetaDirty || changed;
        ImGui::TextDisabled( "%d notes, %d beats%s", static_cast<int>( chart.m_noteData.size() ), static_cast<int>( chart.m_beats.size() ), chart.m_authored ? ", edited by hand" : "" );
    }

    if( ImGui::CollapsingHeader( "Selection", ImGuiTreeNodeFlags_DefaultOpen ) )
    {
        DrawSelectionProperties();
    }

    if( ImGui::CollapsingHeader( "Grid and Tempo" ) )
    {
        ImGui::SliderFloat( "Note Row Height", &m_timeline.NoteRowHeight, 12.f, 40.f, "%.0f" );
        if( chart.m_beats.empty() )
        {
            ImGui::TextWrapped( "This chart has no tempo map; the grid is its BPM in 4/4." );
        }
        if( ImGui::Button( "Generate Beats from BPM" ) )
        {
            GenerateBeats();
        }
        if( ImGui::IsItemHovered() )
        {
            ImGui::SetTooltip( "Replaces the tempo map with a steady one at the song's BPM, 4/4, with a measure line on the start marker (or the first note without one)." );
        }
        // The start marker: where the first measure begins. The game counts in to it.
        if( chart.m_startTime > 0.f )
        {
            ImGui::Text( "Start marker: %.3f s", chart.m_startTime );
        }
        else
        {
            ImGui::TextDisabled( "No start marker" );
        }
        if( ImGui::Button( "Set Start Marker to Playhead" ) )
        {
            chart.m_startTime = static_cast<float>( std::max( 0.0, m_transport.Seconds() ) );
            m_document.MetaDirty = true;
        }
        if( chart.m_startTime > 0.f )
        {
            ImGui::SameLine();
            if( ImGui::Button( "Clear##StartMarker" ) )
            {
                chart.m_startTime = 0.f;
                m_document.MetaDirty = true;
            }
        }
    }

    if( ImGui::CollapsingHeader( "Recording" ) )
    {
        MidiDevice& midi = MidiDevice::GetInstance();
        if( ImGui::BeginCombo( "MIDI Device", m_midiDeviceName.empty() ? "Select a device" : m_midiDeviceName.c_str() ) )
        {
            for( int i = 0; i < static_cast<int>( midi.m_devices.size() ); ++i )
            {
                if( ImGui::Selectable( midi.m_devices[i].Name.c_str() ) )
                {
                    m_midiDeviceName = midi.m_devices[i].Name;
                    midi.OpenMidiDevice( i );
                    midi.PumpMessages();
                }
            }
            ImGui::EndCombo();
        }
        ImGui::TextWrapped( "Press Record, play the song, and hit the pads. The take is one undo step." );
    }

    if( ImGui::CollapsingHeader( "Keys" ) )
    {
        ImGui::TextWrapped(
            "Double-click an empty row to add, an item to remove. Drag to move (Alt: off the grid); drag a span's edge to resize. "
            "Drag empty space to box-select; Ctrl or Shift adds. Click the ruler to scrub; Ctrl-drag it for a loop zone (right-click for more). "
            "Wheel zooms, Shift+wheel pans, Ctrl+wheel scrolls rows, middle-drag pans. "
            "Space plays, L loops; arrows nudge the selection by a grid step or a row; Home and End jump." );
    }
}


void TrackEditor::DrawSelectionProperties()
{
    const std::vector<int> tracks = m_document.SelectedTracks();
    if( tracks.empty() )
    {
        ImGui::TextDisabled( "Nothing selected." );
        return;
    }
    if( tracks.size() > 1 )
    {
        ImGui::Text( "%d items on %d tracks", static_cast<int>( m_document.Selection.size() ), static_cast<int>( tracks.size() ) );
        return;
    }
    const int trackIndex = tracks.front();
    IEventTrack& track = *m_document.Tracks[trackIndex];
    const std::vector<int> items = m_document.SelectedIn( trackIndex );
    if( items.empty() )
    {
        return;
    }
    ImGui::Text( "%d on %s", static_cast<int>( items.size() ), track.Name.c_str() );
    const auto beforeChange = [this, trackIndex]() {
        m_document.BeginEdit( trackIndex );
        m_propertyEdit = true;
    };
    // Don't fight a drag on the timeline for the same items.
    ImGui::BeginDisabled( m_timeline.HasGesture() );
    if( items.size() == 1 )
    {
        const int item = items.front();
        double start = track.Start( item );
        double end = track.End( item );
        if( ImGui::InputDouble( track.Spans ? "Start (s)" : "Time (s)", &start, 0.01, 0.1, "%.3f" ) )
        {
            beforeChange();
            track.Set( item, start, track.Spans ? std::max( end, start + 0.02 ) : start, track.Row( item ) );
        }
        if( track.Spans && ImGui::InputDouble( "End (s)", &end, 0.01, 0.1, "%.3f" ) )
        {
            beforeChange();
            track.Set( item, start, std::max( end, start + 0.02 ), track.Row( item ) );
        }
    }
    track.DrawProperties( items, beforeChange );
    ImGui::EndDisabled();
}


void TrackEditor::GenerateBeats()
{
    const int beats = m_document.FindTrack( "Beats" );
    if( beats < 0 )
    {
        return;
    }
    TrackData& chart = m_document.Chart;
    // From the start marker when the chart has one, else the first note.
    const double start = chart.m_startTime > 0.f ? static_cast<double>( chart.m_startTime )
        : chart.m_noteData.empty() ? 0.0 : static_cast<double>( chart.m_noteData.front().m_triggerTime );
    // Back from there to the start of the song, so it sits on a measure line.
    const double beat = 60.0 / std::max( 20, chart.m_bpm );
    const double first = start - std::floor( start / ( beat * 4.0 ) ) * beat * 4.0;
    m_document.BeginEdit( beats );
    chart.m_beats = BeatGrid::Generate( static_cast<float>( chart.m_bpm ), 4, first, std::max( m_document.Duration(), m_transport.Length() ) );
    m_document.Selection.clear();
    m_document.CommitEdit( "Generate Beats" );
}


void TrackEditor::HandleKeys()
{
    const ImGuiIO& io = ImGui::GetIO();
    if( !m_focused || io.WantTextInput || ImGui::IsPopupOpen( "", ImGuiPopupFlags_AnyPopupId | ImGuiPopupFlags_AnyPopupLevel ) )
    {
        return;
    }
    if( ImGui::IsKeyPressed( ImGuiKey_Space, false ) )
    {
        TogglePlay();
    }
    if( ImGui::IsKeyPressed( ImGuiKey_Home, false ) )
    {
        m_transport.Seek( 0.0 );
        m_timeline.Reveal( 0.0 );
    }
    if( ImGui::IsKeyPressed( ImGuiKey_End, false ) )
    {
        m_transport.Seek( m_transport.Length() );
        m_timeline.Reveal( m_transport.Length() );
    }
    if( io.KeyCtrl || io.KeySuper || m_timeline.HasGesture() )
    {
        return;
    }
    if( ImGui::IsKeyPressed( ImGuiKey_L, false ) )
    {
        ToggleLoop();
    }
    const int horizontal = ( ImGui::IsKeyPressed( ImGuiKey_RightArrow ) ? 1 : 0 ) - ( ImGui::IsKeyPressed( ImGuiKey_LeftArrow ) ? 1 : 0 );
    const int vertical = ( ImGui::IsKeyPressed( ImGuiKey_DownArrow ) ? 1 : 0 ) - ( ImGui::IsKeyPressed( ImGuiKey_UpArrow ) ? 1 : 0 );
    const double step = 1.0 / static_cast<double>( m_timeline.SnapDivision );
    if( !m_document.Selection.empty() )
    {
        if( horizontal != 0 )
        {
            m_document.MoveSelectionBeats( step * horizontal, 0 );
        }
        if( vertical != 0 )
        {
            m_document.MoveSelection( 0.0, vertical );
        }
    }
    else if( horizontal != 0 )
    {
        // Nothing selected: the arrows step the playhead along the grid.
        const TrackData& chart = m_document.Chart;
        const float bpm = static_cast<float>( chart.m_bpm );
        const double beat = std::round( BeatGrid::BeatOfTime( chart.m_beats, bpm, m_transport.Seconds() ) / step ) * step + step * horizontal;
        m_transport.Seek( std::max( 0.0, BeatGrid::TimeOfBeat( chart.m_beats, bpm, beat ) ) );
        m_timeline.Reveal( m_transport.Seconds() );
    }
}


void TrackEditor::StopRecording()
{
    if( !m_recording )
    {
        return;
    }
    m_recording = false;
    m_document.CommitEdit( "Record" );
}


void TrackEditor::HandleRecording()
{
    // The device is read only while the editor has focus (a play session reads it otherwise).
    m_messages.clear();
    if( m_focused && !m_preview.OwnsMidi() )
    {
        m_messages = MidiDevice::GetInstance().PumpMessages();
    }
    const bool take = m_recording && m_transport.IsPlaying();
    // inAge: how long ago the hit happened (a MIDI message waits for the frame that reads it), so
    // the note lands where it was played rather than a frame late.
    const auto record = [&]( PadId inPad, Articulation inArticulation, int inVelocity, double inAge ) {
        if( !take || inPad == PadId::Invalid )
        {
            return;
        }
        m_document.BeginEdit( ChartDocument::kNoteTrack );
        const double seconds = std::max( 0.0, m_transport.Seconds() - std::clamp( inAge, 0.0, 0.25 ) * m_transport.Speed() );
        const int item = m_document.Tracks[ChartDocument::kNoteTrack]->Add( seconds, seconds, static_cast<int>( inPad ) );
        NoteData& note = m_document.Chart.m_noteData[item];
        note.m_articulation = inArticulation;
        note.m_velocity = static_cast<uint8_t>( std::clamp( inVelocity, 1, 127 ) );
    };

    PadMappingStorage& storage = PadMappingStorage::GetInstance();
    std::vector<PadMappingStorage::Resolved> resolved;
    for( const MidiMessageNew& message : m_messages )
    {
        for( const auto& pad : storage.mappedPads )
        {
            if( pad.midiBinding == message.m_data1 && pad.padId >= 0 && pad.padId < static_cast<int>( m_padStates.size() ) )
            {
                m_padStates[pad.padId] = message.IsOnType();
            }
        }
        if( !message.IsOnType() )
        {
            continue;
        }
        // Every pad and stroke the note is bound to (a rim note records a rimshot), with the
        // hit's velocity, so charts keep the drummer's dynamics.
        storage.Resolve( message.m_data1, resolved );
        const double age = message.m_arrival.time_since_epoch().count() != 0 ? std::chrono::duration<double>( std::chrono::steady_clock::now() - message.m_arrival ).count() : 0.0;
        for( const PadMappingStorage::Resolved& meaning : resolved )
        {
            if( m_drums )
            {
                m_drums->hitPad( meaning.pad, message.m_data2 / 127.f );
            }
            record( meaning.pad, meaning.articulation, message.m_data2, age );
        }
    }

    if( m_focused && m_recording && !ImGui::GetIO().WantTextInput )
    {
        Input& input = GetEngine().GetEditorInput();
        for( const auto& pad : storage.mappedPads )
        {
            if( pad.keyboardBinding != 0 && input.WasKeyPressed( static_cast<KeyCode>( pad.keyboardBinding ) ) )
            {
                if( m_drums )
                {
                    m_drums->hitPad( static_cast<PadId>( pad.padId ), 1.f );
                }
                record( static_cast<PadId>( pad.padId ), Articulation::Normal, 100, 0.0 );
            }
        }
    }
    // A take ends with the song.
    if( m_recording && m_document.HasOpenEdit() && !m_transport.IsPlaying() && !m_propertyEdit && !m_timeline.HasGesture() )
    {
        m_document.CommitEdit( "Record" );
    }
}


void TrackEditor::DrawPadPreview()
{
    // The pads the chart strikes at the playhead (and the ones being hit), as lights.
    const std::vector<NoteData>& notes = m_document.Chart.m_noteData;
    std::vector<bool> lit = m_padStates;
    const float now = static_cast<float>( m_transport.Seconds() );
    auto note = std::lower_bound( notes.begin(), notes.end(), now - 0.05f, []( const NoteData& n, float t ) { return n.m_triggerTime < t; } );
    for( ; note != notes.end() && note->m_triggerTime <= now + 0.05f; ++note )
    {
        if( note->m_editorLane >= 0 && note->m_editorLane < PadId::COUNT )
        {
            lit[note->m_editorLane] = true;
        }
    }

    ImDrawList* drawList = ImGui::GetWindowDrawList();
    const ImVec2 origin = ImGui::GetCursorScreenPos();
    const float width = ImGui::GetContentRegionAvail().x;
    const float padWidth = width / static_cast<float>( PadId::COUNT );
    const float height = 50.f;
    for( int pad = 0; pad < PadId::COUNT; ++pad )
    {
        const ImU32 color = static_cast<ImU32>( PadUtils::GetNoteColorABGR( static_cast<PadId>( pad ) ) );
        const ImVec2 min = { origin.x + padWidth * pad + 2.f, origin.y + 4.f };
        const ImVec2 max = { origin.x + padWidth * ( pad + 1 ) - 2.f, origin.y + 4.f + height };
        if( lit[pad] )
        {
            drawList->AddRectFilled( min, max, color, 3.f );
        }
        else
        {
            drawList->AddRect( min, max, color, 3.f );
        }
        const char* name = PadUtils::GetPadName( static_cast<PadId>( pad ) );
        const ImVec2 textSize = ImGui::CalcTextSize( name );
        drawList->PushClipRect( min, max, true );
        drawList->AddText( { ( min.x + max.x - textSize.x ) * 0.5f, ( min.y + max.y - textSize.y ) * 0.5f }, lit[pad] ? 0xFF000000 : color, name );
        drawList->PopClipRect();
    }
    ImGui::Dummy( { width, height + 8.f } );
}

#endif
