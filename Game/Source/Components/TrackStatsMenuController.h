#pragma once
#include <ECS/Component.h>
#include <ECS/ComponentDetail.h>

// Drives Assets/UI/TrackStats.rml. Nothing records play statistics yet, so the page only shows
// the track the library came from and a way back (Escape or the Back button).
class TrackStatsMenuController final
    : public Component<TrackStatsMenuController>
{
public:
    TrackStatsMenuController();

    void Update( float inDeltaTime );
};

ME_REGISTER_COMPONENT( TrackStatsMenuController )
