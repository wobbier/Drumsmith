#pragma once
#include <ECS/Component.h>
#include <ECS/ComponentDetail.h>

class TrackListMenuController final : public Component<TrackListMenuController>
{
public:
    TrackListMenuController();
    void Update( float inDeltaTime );

private:
    void PopulateModel();
    void SelectTrack( int inTrackIndex );
    void PreviewTrack( int inTrackIndex );
    void PlayTrack( int inTrackIndex );
    bool m_modelReady = false;
    int m_selectedTrack = -1;
    int m_previewTrack = -1;
    float m_previewDelay = 0.f;
};

ME_REGISTER_COMPONENT( TrackListMenuController )
