#pragma once
#include <ECS/Core.h>

// Ticks the menu controller components of the loaded scene (MainMenuController, DLCMenuController,
// ...), which drive the RmlUi pages (Docs/UI-and-Menus.md). Declared in each menu scene's "Cores",
// so the menus also run in the editor's Play mode.
class MenuCore final
    : public Core<MenuCore>
{
public:
    MenuCore();

    virtual void Update( const UpdateContext& inUpdateContext ) final;
};

ME_REGISTER_CORE( MenuCore )
