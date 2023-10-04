#pragma once
#include "Dementia.h"
#include <Editor/WidgetRegistry.h>
#include "HavanaWidget.h"

#if USING(ME_EDITOR)

class TrackEditor
    : public HavanaWidget
{
public:
    TrackEditor();
    ~TrackEditor();

    void Init() override;
    void Destroy() override;

    void Update() override;
    void Render() override;
};

ME_REGISTER_EDITOR_WIDGET( TrackEditor );

#endif