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

class AudioSource;
class Drumset;

#if USING(ME_EDITOR)

class TrackEditor
    : public HavanaWidget
    , public EventReceiver
{
public:
    static constexpr const float kLaneSpacing = 5.f;
    static constexpr float kDefaultMaxKeyframeWidth = 1.0f / 16.0f;
    static constexpr float kMaxKeyframeWidth = 20.0f;
    static constexpr float kMinKeyframeWidth = 0.5f;
    static constexpr float kBaseZoomFactor = 1.1f;
    static constexpr float kBeatsPerMeasure = 4.0f; // For now, we do 4/4 time
    static constexpr float kSubMeasure = 4.0f; // For now, we do 4/4 time

    TrackEditor();
    ~TrackEditor();

    void Init() override;
    void Destroy() override;

    void Update() override;
    void Render() override;

    void DrawTrackControls();
    void DrawNoteSnappingControls();

    TrackData& GetCurrentTrackData();

    void DrawMenuBar();

    void DrawPadPreview();

    float TimelineSize = 2000.f;

    bool OnEvent( const BaseEvent& evt ) override;

    float ScrollDelta = 0.f;
    bool IsWindowHovered = false;

    float GetNoteWidth( float timelineSizeScale );
    float CalculateZoom();
    float ScaleValue( float inValue );
    bool CullVisual(float posx);
    float WindowContentSize = 1.f;

    Path SelectedTrackLocation;
    int SelectedTrackIndex = -1;

    SharedPtr<AudioSource> TrackPreview = nullptr;
private:
    float timelineSizeScale = 1.f;
    float timelineSizeZoomed = 1.f;

    std::size_t m_closestNoteIndex = 0;
    float m_cachedTimestamp = 0.f;
    std::vector<bool> hitNotes;
    void ResetTrack();
    bool m_showDebugInfo = false;
    float m_noteHeight = 20.f;
    float m_timeSignature = 4.f;
    float m_timeSignature2 = 4.f;
    bool m_showPadPreview = true;
    bool m_showTrackInfo = true;
    // Maybe store this in the midi file?
    std::vector<MidiMessageNew> m_messages;
    bool m_recordingActive = false;
    Drumset* m_drums = nullptr;
};

ME_REGISTER_EDITOR_WIDGET( TrackEditor );

#endif
