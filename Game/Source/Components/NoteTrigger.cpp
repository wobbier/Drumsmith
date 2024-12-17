#include "NoteTrigger.h"

NoteTrigger::NoteTrigger()
    : Component("NoteTrigger")
{

}

void NoteTrigger::OnSerialize( json& outJson )
{
}

void NoteTrigger::OnDeserialize( const json& inJson )
{
}

#if USING(ME_EDITOR)

void NoteTrigger::OnEditorInspect()
{
    ImGui::Text( PadUtils::GetPadName( EditorLane ) );
}

#endif
