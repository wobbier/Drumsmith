#pragma once
#include "Dementia.h"
#include "CoreGame/TrackList.h"
#include "Editor/Chart/EventTrack.h"
#include <Editor/UndoStack.h>
#include <any>
#include <array>
#include <memory>
#include <set>
#include <string>
#include <vector>

#if USING( ME_EDITOR )

struct ChartItemRef
{
    int Track = 0;
    int Item = 0;
    bool operator<( const ChartItemRef& inOther ) const { return Track != inOther.Track ? Track < inOther.Track : Item < inOther.Item; }
    bool operator==( const ChartItemRef& inOther ) const { return Track == inOther.Track && Item == inOther.Item; }
};

// The chart open in the Track Editor (Docs/Songs-and-DLC.md): a working copy of a song's
// TrackData, its tracks, the selection, the clipboard and its own undo history. Holds no ImGui
// state, so it is driven by the timeline, by editor automation and by unit tests alike.
class ChartDocument
{
public:
    ChartDocument();
    ~ChartDocument();
    ChartDocument( const ChartDocument& ) = delete;
    ChartDocument& operator=( const ChartDocument& ) = delete;

    // Opens a copy of inTrack with its notes loaded from disk.
    void Open( const TrackData& inTrack );
    // Opens inTrack as it stands (no disk).
    void OpenInMemory( const TrackData& inTrack );
    void Close();
    bool IsOpen() const { return m_open; }
    // Marks the chart authored and writes TrackData.txt and NoteData.txt.
    void Save();
    bool IsDirty() const { return m_open && ( History.IsDirty() || MetaDirty ); }

    TrackData Chart;
    std::vector<std::unique_ptr<IEventTrack>> Tracks;
    UndoStack History;
    // Name, artist, BPM or the preview marker changed (these aren't in the undo history).
    bool MetaDirty = false;

    int TrackCount() const { return static_cast<int>( Tracks.size() ); }
    int FindTrack( const std::string& inName ) const;
    static constexpr int kNoteTrack = 0;

    // Selection.
    std::set<ChartItemRef> Selection;
    bool IsSelected( int inTrack, int inItem ) const { return Selection.count( { inTrack, inItem } ) > 0; }
    std::vector<int> SelectedIn( int inTrack ) const;
    std::vector<int> SelectedTracks() const;
    void SelectAll( const std::vector<int>& inTracks );
    // From the selection's first start to its last end; false with nothing selected.
    bool SelectionSpan( double& outStart, double& outEnd ) const;

    // An edit in progress: BeginEdit before changing a track (again for each track touched;
    // repeats are free), CommitEdit to make it one undo step, CancelEdit to put the tracks back.
    void BeginEdit( int inTrack );
    bool HasOpenEdit() const { return !m_edit.empty(); }
    void CommitEdit( const std::string& inName );
    void CancelEdit();

    // Whole operations, each one undo step.
    int AddItem( int inTrack, double inStart, double inEnd, int inRow );
    void DeleteSelection();
    // Moves the selection by seconds and rows (rows only within a track that has several).
    void MoveSelection( double inSeconds, int inRows );
    // Moves the selection along the beat grid, so a nudge keeps its musical place over tempo changes.
    void MoveSelectionBeats( double inBeats, int inRows );
    void SnapSelection( int inDivision );
    bool CanPaste() const { return !m_clipboard.empty(); }
    void Copy();
    void Cut();
    // The copied items, the earliest of them at inSeconds.
    void Paste( double inSeconds );
    // Repeats the selection straight after itself, on the beat.
    void Duplicate();
    void Undo();
    void Redo();

    // Counts every change to a part of the chart; the preview watches these.
    uint32_t Version( ChartDomain inDomain ) const { return m_versions[static_cast<size_t>( inDomain )]; }
    // The chart's length in seconds: its audio's, or far enough to hold every item.
    double Duration() const;

private:
    friend class ChartEditCommand;
    struct OpenEdit { int Track = 0; std::any Before; };
    struct ClipboardEntry { int Track = 0; std::any Items; };

    void Rebind();
    void Touch( int inTrack );
    void OnHistoryApplied( const std::vector<int>& inTracks );

    bool m_open = false;
    std::vector<OpenEdit> m_edit;
    std::vector<ClipboardEntry> m_clipboard;
    double m_clipboardStart = 0.0;
    std::array<uint32_t, static_cast<size_t>( ChartDomain::Count )> m_versions{};
};

#endif
