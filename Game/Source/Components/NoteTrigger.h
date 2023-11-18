#pragma once
#include "ECS\Component.h"

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
    std::string EditorLane;

protected:
    void OnSerialize( json& outJson ) override;
    void OnDeserialize( const json& inJson ) override;
};