#pragma once
#include "Dementia.h"
#include <array>
#include <cstdint>
#include <string>

#if USING( ME_EDITOR )

class ChartDocument;
class NoteHighwayCore;
class Transport;

// The Track Editor's preview (Docs/Songs-and-DLC.md): the game's own highway and venue, showing
// the chart being edited at the editor's playhead. It is a play session of the gameplay scene
// (game systems only run while playing, and the engine renders one world) in which the highway
// follows the editor instead of playing a song: the editor keeps the audio, the clock and the
// MIDI queue. The picture is the editor's Game View; this draws only the session's controls, in
// the Track Editor's toolbar.
class PreviewSession
{
public:
    // Highway and venue as in a play; the notes alone (for charting); the show alone (for venue work).
    enum class Mode { Both, Highway, Scene };

    // The toolbar's part: start / stop, what is on screen, and the session's state.
    void DrawControls( ChartDocument& inDocument );
    // Feeds the session the playhead and whatever the editor changed. Call once a frame.
    void Update( ChartDocument& inDocument, Transport& inTransport );

    // Starts a session: enters play if the editor isn't playing, and loads the gameplay scene if
    // the highway isn't in the open one. Answers false when it can't begin; it takes a few frames
    // to be running (IsActive).
    bool Start( ChartDocument& inDocument );
    void Stop();
    bool IsActive() const { return m_state == State::Active; }
    bool IsStarting() const { return m_state == State::EnteringPlay || m_state == State::LoadingScene; }
    void SetMode( Mode inMode ) { m_mode = inMode; }
    Mode GetMode() const { return m_mode; }
    // The venue the preview builds (VenueShow::SetOverride): a registry id (hidden venues too), a
    // room name (Arena, Club, Festival) or a .lvl path; empty for the song's own pick (as a play
    // would choose it). A running session rebuilds its venue on the next Update.
    void SetVenue( const std::string& inVenue ) { m_venue = inVenue; }
    const std::string& GetVenue() const { return m_venue; }
    // Rescans Assets/Venues and rebuilds the venue from disk (its .lvl read again), for an author
    // editing the scene in another tab or regenerating it with Tools/Venues.
    void ReloadVenue();
    // What the last venue built under the session's pick came to (VenueShow::GetOverrideOutcome).
    const std::string& GetVenueOutcome() const;
    // That build couldn't make the pick (no such venue, or a scene that can't be one): a room stood in.
    bool VenueFellBack() const;
    // The session has the MIDI device (never: a preview leaves it to the editor's recording).
    bool OwnsMidi() const { return false; }

private:
    enum class State { Idle, EnteringPlay, LoadingScene, Active };

    NoteHighwayCore* FindCore() const;
    void Fail( const std::string& inWhy );
    // The venue picker and its reload button, in the toolbar.
    void DrawVenueControls( ChartDocument& inDocument );
    // The session's over (stopped, or play ended): plays choose their own venue again.
    void ReleaseVenue();

    State m_state = State::Idle;
    Mode m_mode = Mode::Both;
    Mode m_appliedMode = Mode::Both;
    // What this session did, to undo it on Stop.
    bool m_startedPlay = false;
    bool m_loadedScene = false;
    int m_waitFrames = 0;
    std::string m_status;
    // The chart versions the session last built, and how long the venue has been waiting for a
    // rebuild (it is thousands of entities: one rebuild after the edits stop, not one per edit).
    std::array<uint32_t, 4> m_versions{};
    float m_venueWait = -1.f;
    // The venue picked (SetVenue), the one the running venue was built for, and a reload asked for.
    std::string m_venue;
    std::string m_appliedVenue;
    bool m_reloadVenue = false;
    bool m_scannedVenues = false;
};

#endif
