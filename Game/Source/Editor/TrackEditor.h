#pragma once
#include "Dementia.h"
#include <Editor/WidgetRegistry.h>
#include "HavanaWidget.h"
#include "Events/EventReceiver.h"
#include "PadBindings.h"
#include "Path.h"
#include "Pointers.h"

class AudioSource;

#if USING(ME_EDITOR)

class TrackEditor
    : public HavanaWidget
    , public EventReceiver
{
public:
    static constexpr const float kNoteHeight = 10.f;

    TrackEditor();
    ~TrackEditor();

    void Init() override;
    void Destroy() override;

    void Update() override;
    void Render() override;

    float TimelineSize = 2000.f;

    bool OnEvent( const BaseEvent& evt ) override;

    float ScrollDelta = 0.f;
    bool IsWindowHovered = false;

    int GetNoteColor( PadId inId );

    Path SelectedTrackLocation;
    int SelectedTrackIndex = 0;

    SharedPtr<AudioSource> TrackPreview = nullptr;
};

ME_REGISTER_EDITOR_WIDGET( TrackEditor );

#endif