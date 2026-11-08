#pragma once
#include "Math/Random.h"
#include "JSON.h"
#include <string>

class RmlUiCore;
class TrackData;

// The menu radio: plays random installed tracks between menus and drives the "track-radio"
// widget of a page's view model (the markup MainMenu.rml and DLC.rml share, styled by Radio.rcss).
// Model values: radio_available, radio_visible, radio_title, radio_artist, radio_art,
// radio_position, radio_duration, radio_progress (0..1000). Events: skip, seek(value), radio_show.
class TrackRadioUtils
{
public:
    explicit TrackRadioUtils( std::string inModel );

    // Registers the widget's events on the model; call once the model exists.
    void RegisterEvents( RmlUiCore& inUI );
    // Ticks the radio and refreshes the widget.
    void OnUpdate( float dt );
    // Handles one polled model event; true when it was one of the radio's.
    bool HandleEvent( const std::string& inEvent, const json& inArgs );

    void PlayNextRandomTrack();
    void SkipTrack();
    // inPosition is a fraction of the track (0..1).
    void SeekToPosition( float inPosition );
    void PlayLatestTrack();
    // Slides the widget in; it hides itself again after a while, like the old page's hover widget.
    void Show();

    // An img src for a track's album art ("/Assets/DLC/..." so RmlUi resolves it through the VFS
    // instead of relative to the document), or the stock placeholder.
    static std::string ArtSource( const TrackData& inTrack );

private:
    void UpdateModel();

    std::string m_model;
    Random64 m_random;
    float m_visibleTimer = 0.f;
    const TrackData* m_displayedTrack = nullptr;
    // RmlUi raises "change" on the seek slider whenever its value attribute is set, so the
    // position the widget was last given is remembered and echoes of it aren't seeks.
    double m_pushedProgress = -1.0;
    // After a real seek the widget keeps the dragged position until the audio has moved.
    float m_seekHold = 0.f;
};
