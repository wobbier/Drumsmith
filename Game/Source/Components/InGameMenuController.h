#pragma once
#include <ECS/Component.h>
#include <ECS/ComponentDetail.h>
class InGameMenuController final : public Component<InGameMenuController>
{
public:
    InGameMenuController();
    void Update( float inDeltaTime );

private:
    void SetPaused( bool inPaused );
    bool m_modelReady = false;
    bool m_paused = false;
    bool m_options = false;
    const char* m_focusTarget = nullptr;
};
ME_REGISTER_COMPONENT( InGameMenuController )
