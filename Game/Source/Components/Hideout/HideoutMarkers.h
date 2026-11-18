#pragma once
#include "ECS/Component.h"
#include "ECS/ComponentDetail.h"
#include "Math/Vector3.h"
#include <string>

// Markers placed in a hideout room scene (Assets/Hideout/*.lvl; Docs/Hideout-and-Progression.md),
// read by the main menu's Hideout. Plain data, like the venue markers.


// Something in the room the player can go to: the kit plays a song, the practice pad opens the
// lessons and so on. The entity's position is what the camera looks at; ViewOffset is where the
// camera stands, relative to it, when the station is chosen.
class HideoutStation
    : public Component<HideoutStation>
{
    ME_REFLECTABLE( HideoutStation )
public:
    enum class Kind : int { Kit = 0, PracticePad, Radio, Laptop, TrophyWall, Mixer, GigBoard, Door };

    HideoutStation();

    virtual void Init() final;

    Kind Station = Kind::Kit;
    // The label over it; empty uses the station's usual name.
    std::string Label;
    Vector3 ViewOffset{ 0.f, 0.6f, -1.6f };
    float FieldOfView = 45.f;
};
ME_REGISTER_COMPONENT_FOLDER( HideoutStation, "Hideout" )


// Where an unlockable item stands (CoreGame/Progression.h: an item's Slot). The entity and its
// children are the item: they are taken out of the room until the item is unlocked. A slot that
// no item names stays.
class HideoutItemSlot
    : public Component<HideoutItemSlot>
{
    ME_REFLECTABLE( HideoutItemSlot )
public:
    HideoutItemSlot();

    virtual void Init() final;

    std::string Slot;
};
ME_REGISTER_COMPONENT_FOLDER( HideoutItemSlot, "Hideout" )


// The room's overview: where the camera stands when no station is chosen. It looks along the
// entity's local +Z. One per room.
class HideoutView
    : public Component<HideoutView>
{
    ME_REFLECTABLE( HideoutView )
public:
    HideoutView();

    virtual void Init() final;

    float FieldOfView = 55.f;
};
ME_REGISTER_COMPONENT_FOLDER( HideoutView, "Hideout" )
