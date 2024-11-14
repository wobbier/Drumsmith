#pragma once
#include "ECS\Component.h"
#include "ECS\ComponentDetail.h"
#include "Editor\PadBindings.h"

class NoteTrigger
    : public Component<NoteTrigger>
{
public:
    NoteTrigger();
#if USING(ME_EDITOR)
    void OnEditorInspect() override;
#endif

    float TriggerTime = 0.f;
    std::string NoteName;
    PadId EditorLane;
    std::string EditorLaneName;

protected:
    void OnSerialize( json& outJson ) override;
    void OnDeserialize( const json& inJson ) override;
};

ME_REGISTER_COMPONENT_FOLDER( NoteTrigger, "Game" );