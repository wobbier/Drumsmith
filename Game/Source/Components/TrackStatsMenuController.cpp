#include "Components/TrackStatsMenuController.h"

#include <Engine/Engine.h>
#include <Engine/Input.h>
#include <Events/SceneEvents.h>


TrackStatsMenuController::TrackStatsMenuController()
    : Component( "TrackStatsMenuController" )
{
}


void TrackStatsMenuController::Update( float inDeltaTime )
{
    if( GetEngine().GetInput().WasKeyPressed( KeyCode::Escape ) )
    {
        LoadSceneEvent event;
        event.Level = "Assets/TrackList.lvl";
        event.Queue();
    }
}
