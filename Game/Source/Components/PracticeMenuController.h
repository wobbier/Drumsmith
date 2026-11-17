#pragma once
#include <ECS/Component.h>
#include <ECS/ComponentDetail.h>

// Drives Assets/UI/Practice.rml through the "practice_menu" view model: the lessons
// (CoreGame/Practice.h) by category, the chosen one's description and pattern, its tempo and
// length, and Start, which plays it on the highway over a click (Docs/Practice.md).
class PracticeMenuController final
    : public Component<PracticeMenuController>
{
public:
    PracticeMenuController();

    void Update( float inDeltaTime );

private:
    void PopulateModel();
    void SelectLesson( int inLesson );
    void StartLesson();

    bool m_modelReady = false;
    int m_selected = -1;
    int m_bars = 16;
};

ME_REGISTER_COMPONENT( PracticeMenuController )
