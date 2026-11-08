#include "Cores/MenuCore.h"

#include <Components/UI/UIDocument.h>
#include "Components/DLCMenuController.h"
#include "Components/InGameMenuController.h"
#include "Components/MainMenuController.h"
#include "Components/TrackListMenuController.h"
#include "Components/TrackStatsMenuController.h"

namespace
{
    template<typename Controller>
    void Tick( Entity& inEntity, float inDeltaTime )
    {
        if( inEntity.HasComponent<Controller>() )
        {
            inEntity.GetComponent<Controller>().Update( inDeltaTime );
        }
    }
}


MenuCore::MenuCore()
    : Base( ComponentFilter().Requires<UIDocument>() )
{
}


void MenuCore::Update( const UpdateContext& inUpdateContext )
{
    const float deltaTime = inUpdateContext.GetDeltaTime();
    for( Entity& entity : GetEntities() )
    {
        Tick<MainMenuController>( entity, deltaTime );
        Tick<DLCMenuController>( entity, deltaTime );
        Tick<TrackListMenuController>( entity, deltaTime );
        Tick<InGameMenuController>( entity, deltaTime );
        Tick<TrackStatsMenuController>( entity, deltaTime );
    }
}
