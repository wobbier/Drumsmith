#pragma once
#include <ECS/Component.h>
#include <ECS/ComponentDetail.h>
#include <array>
#include <atomic>
#include <deque>
#include <memory>
#include <string>
#include <thread>
#include <vector>

class TrackRadioUtils;

// Drives Assets/UI/MainMenu.rml through the "main_menu" view model: the settings panel in tabs
// (game, sound and timing with the way into the delay calibration, venue, the drum kit's device and pad
// bindings, the DLC servers with a check of each) and the radio widget.
class MainMenuController final
    : public Component<MainMenuController>
{
public:
    MainMenuController();
    virtual ~MainMenuController();

    void Update( float dt );

private:
    void PopulateModel();
    void RefreshDevices();
    // The scene venues the Venue tab lists after the built-in rooms (VenueRegistry).
    void RefreshVenues();
    void ApplySettings( bool inSave );
    void OpenSettings( bool inOpen );
    // The drum kit rows: each pad's key and MIDI note, and capturing a new one.
    void RefreshPads();
    void UpdateKitBinding( float dt );
    void StopBinding();
    // The DLC server rows, and checking that a server has a catalogue (on a worker thread).
    void RefreshServers();
    void QueueServerCheck( const std::string& inServer );
    void PumpServerChecks();

    struct ServerCheck
    {
        std::string Url;
        std::thread Thread;
        std::atomic<bool> Finished{ false };
        bool Works = false;
        std::string Message;
    };
    // What the last check of a server said, for its row.
    struct ServerResult
    {
        std::string Url;
        int State = 0;   // 1 checking, 2 works, 3 doesn't
        std::string Message;
    };
    std::unique_ptr<ServerCheck> m_serverCheck;
    std::deque<std::string> m_serverChecks;
    std::vector<ServerResult> m_serverResults;

    std::unique_ptr<TrackRadioUtils> m_radioUtils;
    bool m_modelReady = false;

    // The pad being bound and to what (0 nothing, 1 a key, 2 a MIDI note).
    int m_bindPad = -1;
    int m_bindKind = 0;
    // Space and Enter also press the focused button: its click is ignored for this long after
    // one of them was bound.
    float m_bindIgnore = 0.f;
    bool m_kitDirty = false;
    int m_midiGeneration = -1;
};

ME_REGISTER_COMPONENT( MainMenuController );
