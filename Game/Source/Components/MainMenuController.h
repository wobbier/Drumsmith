#pragma once
#include <ECS/Component.h>
#include <ECS/ComponentDetail.h>
#include <array>
#include <memory>

class TrackRadioUtils;

// Drives Assets/UI/MainMenu.rml through the "main_menu" view model: the settings panel (radio
// volume, latency sliders, DLC server, MIDI device, the visual latency test) and the radio widget.
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
    void ApplySettings( bool inSave );
    void OpenSettings( bool inOpen );
    void UpdateLatencyTest( float dt );
    void RecordLatencySample();
    void StopLatencyTest();

    std::unique_ptr<TrackRadioUtils> m_radioUtils;
    bool m_modelReady = false;

    // The visual latency test: a marker sweeps the box; a key press at the centre line is on time.
    bool m_latencyTestActive = false;
    float m_latencySweep = 0.f;
    std::array<float, 10> m_latencySamples{};
    int m_latencySampleCount = 0;
    int m_latencyNextSample = 0;
};

ME_REGISTER_COMPONENT( MainMenuController );
