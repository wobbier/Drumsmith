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
    // Ends the gig being played (CoreGame/GigSession.h) and goes home to the hideout.
    void LeaveGig();
    bool m_modelReady = false;
    bool m_paused = false;
    bool m_options = false;
    bool m_midiUnplugged = false;
    const char* m_focusTarget = nullptr;
};
ME_REGISTER_COMPONENT( InGameMenuController )
