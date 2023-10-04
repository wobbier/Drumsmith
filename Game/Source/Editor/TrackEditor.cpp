#include "TrackEditor.h"


TrackEditor::TrackEditor()
    : HavanaWidget("Track Editor")
{

}


TrackEditor::~TrackEditor()
{

}

void TrackEditor::Init()
{
}

void TrackEditor::Destroy()
{
}

void TrackEditor::Update()
{
}

void TrackEditor::Render()
{
    ImGui::Begin( "Track Editor", &IsOpen );

    ImGui::End();
}
