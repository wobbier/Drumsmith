#include "PadBindings.h"
#include "Utils/HavanaUtils.h"
#include "Engine/Engine.h"
#include <memory>
#include "File.h"

#if USING(ME_EDITOR)


bool KeybindButton( int inImGUIID, int* outKey, bool* waitingforkey, std::string inLabel = "", const ImVec2& size_arg = ImVec2( 0, 0 ) )
{
    ImGui::PushID( inImGUIID );

    Input& editorInput = GetEngine().GetEditorInput();
    if( !( *waitingforkey ) )
    {
        if( ImGui::Button( ( (KeyCode)( *outKey ) == KeyCode::Unknown ) ? std::string( inLabel + "Not Bound" ).c_str() : std::string( inLabel + std::string( editorInput.GetKeyCodeName( (KeyCode)*outKey ) ) ).c_str(), size_arg ) )
        {
            *(int*)waitingforkey = true;
        }
    }
    else
    {
        ImGui::Button( "...", size_arg );
        if( editorInput.WasKeyPressed( KeyCode::Escape ) )
        {
            *(int*)waitingforkey = false;
            ImGui::PopID();
            return false;
        }
        if( editorInput.WasKeyPressed( editorInput.GetLastKeyPressed() ) )
        {
            *(int*)outKey = (int)editorInput.GetLastKeyPressed();
            *(int*)waitingforkey = false;
            ImGui::PopID();
            return true;
        }
    }
    ImGui::PopID();
    return false;
}

PadBindingWidget::PadBindingWidget()
    : HavanaWidget( "Pad Bindings" )
{
    memset( &keyCatchState[0], 0, PadId::COUNT );
    memset( &midiCatchState[0], 0, PadId::COUNT );
}


PadBindingWidget::~PadBindingWidget()
{

}

void PadBindingWidget::Init()
{
}

void PadBindingWidget::Destroy()
{
}

void PadBindingWidget::Update()
{
}

void PadBindingWidget::Render()
{
    ImGui::Begin( "Pad Bindings", &IsOpen );
    auto& mappings = PadMappingStorage::GetInstance();

    for( int16_t id = PadId::Invalid + 1; id < PadId::COUNT; ++id )
    {
        auto& thing = mappings.mappedPads[id];
        HavanaUtils::Label( thing.padName );
        float remainingSpace = ImGui::GetContentRegionAvail().x;
        KeybindButton( id, &thing.keyboardBinding, &keyCatchState[id], "Keyboard: ", { remainingSpace / 2.f, 0 } );
        ImGui::SameLine();
        KeybindButton( id + PadId::COUNT, &thing.midiBinding, &midiCatchState[id], "Midi Pad: ", { -1.f, 0 } );

    }

    if( ImGui::Button( "Save Pad Mappings", { -1, 0 } ) )
    {
        mappings.saveData.clear();

        for( auto pad : mappings.mappedPads )
        {
            json& padData = mappings.saveData["PadMap"];
            json entry;
            entry["ID"] = pad.padId;
            entry["NAME"] = pad.padName;
            entry["KB"] = pad.keyboardBinding;
            entry["MIDI"] = pad.midiBinding;
            padData.push_back( entry );
        }

        File outFile( Path("Assets/Config/PadMappings.json"));
        outFile.Write( mappings.saveData.dump() );
    }

    if( ImGui::CollapsingHeader( "RAW JSON" ) )
    {
        ImGui::TextWrapped( mappings.saveData.dump(1).c_str() );
    }

    ImGui::End();
}

#endif

PadMappingStorage::PadMappingStorage()
{
    mappedPads.resize( PadId::COUNT );

    for( int16_t id = PadId::Invalid + 1; id < PadId::COUNT; ++id )
    {
        mappedPads[id].padId = id;
        mappedPads[id].padName = PadUtils::GetPadName( id );
    }

    Path mappingConfig( "Assets/Config/PadMappings.json" );
    if( mappingConfig.Exists )
    {
        File outFile( mappingConfig );
        saveData = json::parse(outFile.Read());

        json& padMap = saveData["PadMap"];
        for (auto& pad : padMap)
        {
            int16_t id = pad["ID"];
            auto& padData = mappedPads[id];
            padData.padId = id;
            padData.keyboardBinding = pad["KB"];
            padData.midiBinding = pad["MIDI"];
            padData.padName = pad["NAME"];
        }
    }
}
