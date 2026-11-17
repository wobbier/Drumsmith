#pragma once
#include <ECS/Component.h>
#include <ECS/ComponentDetail.h>
#include <string>

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
    void ToggleFavorite( int inTrackIndex );
    void EditTrack( int inTrackIndex );
    // Fills the details panel's recommendations (ChartAdvice) for the selected track.
    void ShowAdvice( int inTrackIndex );
    bool m_modelReady = false;
    // The search box's text as last applied to the list, and whether only favorites are listed.
    std::string m_search;
    bool m_favoritesOnly = false;
    int m_selectedTrack = -1;
    int m_previewTrack = -1;
    float m_previewDelay = 0.f;
    // The song whose Remove is waiting for a yes.
    int m_confirmRemove = -1;
    int m_adviceTrack = -1;
    float m_adviceDelay = 0.f;
};

ME_REGISTER_COMPONENT( TrackListMenuController )
