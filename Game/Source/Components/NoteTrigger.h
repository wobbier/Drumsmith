#pragma once
#include "ECS\Component.h"

class NoteTrigger
    : public Component<NoteTrigger>
{
public:
    NoteTrigger();
    void OnEditorInspect() override;

protected:
    void OnSerialize( json& outJson ) override;
    void OnDeserialize( const json& inJson ) override;
};