#pragma once
#include "Dementia.h"
#include <Editor/WidgetRegistry.h>
#include "HavanaWidget.h"
#include "Events/EventReceiver.h"
#include "PadBindings.h"
#include "Path.h"
#include "Pointers.h"
#include "CoreGame/TrackList.h"
#include "Midi/MidiDevice.h"

#if USING(ME_EDITOR)
#include "Editor/Chart/ChartDocument.h"
#include "Editor/Chart/PreviewSession.h"
#include "Editor/Chart/TimelineView.h"
#include "Editor/Chart/Transport.h"

class Drumset;

// The chart editor (Docs/Songs-and-DLC.md, "Authoring: the Track Editor"): a timeline of a song's
// notes and every other charted event, with selection, undo and a clipboard, playback of the
// song's stems, MIDI recording, and a preview of the real highway and venue. This class is the
// windows and their wiring; the parts live in Editor/Chart/.
class TrackEditor
    : public HavanaWidget
    , public EventReceiver
{
public:
    TrackEditor();
    ~TrackEditor();

    void Init() override;
    void Destroy() override;

    void Update() override;
    void Render() override;

    // Opens a song from the library for editing (unsaved changes to the open one are dropped).
    void OpenTrack( const TrackData& inTrack );
    void Save();

    ChartDocument& Document() { return m_document; }
    Transport& GetTransport() { return m_transport; }
    TimelineView& Timeline() { return m_timeline; }
    PreviewSession& Preview() { return m_preview; }

    // --editor-exec commands (track-*); the list is in TrackEditorAutomation.cpp.
    bool ExecuteAutomation( const std::string& inCommand, const std::string& inArgs, std::string& outError );

private:
    void InstallActionRouting();
    bool ClaimsAction( const std::string& inId ) const;
    void ExecuteAction( const std::string& inId );

    void DrawMenuBar();
    // Story mode: puts each moment of the story set this song plays in on the Story track, where
    // the set's own cue has it (those already there are left); one undo step.
    void PlaceStoryMoments();
    void DrawToolbar();
    // Play from the toolbar or Space: the game preview comes up first, then the song starts.
    void TogglePlay();
    // Looping on or off; with no loop zone yet, makes one (the selection, else the section under
    // the playhead, else four measures from it).
    void ToggleLoop();
    void DrawTrackPicker();
    void DrawDetails();
    void DrawSelectionProperties();
    void DrawPadPreview();
    void HandleKeys();
    void HandleRecording();
    // Opens the library's inIndex-th song, asking first when there are unsaved changes.
    void RequestOpen( int inIndex );
    void StopRecording();
    void GenerateBeats();

    ChartDocument m_document;
    Transport m_transport;
    TimelineView m_timeline;
    PreviewSession m_preview;

    bool m_focused = false;
    // Play was pressed; the song starts once the preview is running (or has failed to).
    bool m_playPending = false;
    float m_unmutedVolume = 1.f;
    bool m_showPadPreview = true;
    bool m_openPicker = false;
    std::string m_pickerFilter;
    int m_pendingOpen = -1;
    // A change made in the properties panel, committed as one undo step when the widget lets go.
    bool m_propertyEdit = false;

    std::vector<MidiMessageNew> m_messages;
    std::vector<bool> m_padStates;
    std::string m_midiDeviceName;
    bool m_recording = false;
    Drumset* m_drums = nullptr;
};

ME_REGISTER_EDITOR_WIDGET( TrackEditor );

#endif
