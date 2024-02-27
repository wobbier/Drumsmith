#include <Components/TrackStatsMenuController.h>

#include <Events/SceneEvents.h>
#include "CoreGame/TrackList.h"
#include "Events/GameEvents.h"
#include "Global/TrackRadio.h"

TrackStatsMenuController::TrackStatsMenuController()
    : BasicUIView( "TrackStatsMenuController" )
{
    FilePath = Path( "Assets/UI/TrackStats.html" );
}

#if USING( ME_UI )

void TrackStatsMenuController::OnUILoad( ultralight::JSObject& GlobalWindow, ultralight::View* Caller )
{
    BasicUIView::OnUILoad( GlobalWindow, Caller );

}

#endif