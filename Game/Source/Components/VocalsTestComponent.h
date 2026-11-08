#pragma once
#include <ECS/Component.h>
#include <ECS/ComponentDetail.h>

// Tags the entity VocalsTestCore moves with the detected pitch (Assets/Vocals.lvl). The core also
// fills the "vocals" view model that Assets/UI/Vocals.rml shows.
class VocalsTestComponent final
    : public Component<VocalsTestComponent>
{
public:
    VocalsTestComponent();
};

ME_REGISTER_COMPONENT( VocalsTestComponent )
