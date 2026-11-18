#pragma once
#include <ECS/Component.h>
#include <ECS/ComponentDetail.h>

// Drives Assets/UI/Practice.rml through the "practice_menu" view model: the lessons
// (CoreGame/Practice.h) by category, the chosen one's description and pattern, its tempo and
// length, Start, which plays it on the highway over a click (Docs/Practice.md), and the songs in
// the player's library that play it (CoreGame/LessonPatterns.h), each one a click from playing.
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
    // The songs that play the chosen lesson (LessonPatternIndex), or why there are none yet.
    void FillSongs();

    bool m_modelReady = false;
    int m_selected = -1;
    int m_bars = 16;
};

ME_REGISTER_COMPONENT( PracticeMenuController )
