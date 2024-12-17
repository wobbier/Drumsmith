#include "PadBindings.h"
#include "Utils/HavanaUtils.h"
#include "Engine/Engine.h"
#include <memory>
#include "File.h"
#include "UI/Colors.h"
#include "optick.h"

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

bool MidiBindButton( int inImGUIID, MidiDeviceManager& inDeviceManager, int* outKey, bool* waitingforkey, std::string inLabel = "", const ImVec2& size_arg = ImVec2( 0, 0 ) )
{
    ImGui::PushID( inImGUIID );

    Input& editorInput = GetEngine().GetEditorInput();
    if( !( *waitingforkey ) )
    {
        if( ImGui::Button( ( (KeyCode)( *outKey ) == KeyCode::Unknown ) ? std::string( inLabel + "Not Bound" ).c_str() : std::string( inLabel + std::to_string( *outKey ) ).c_str(), size_arg ) )
        {
            *(int*)waitingforkey = true;

            inDeviceManager.ClearAllPendingMessages();
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

        MidiMessage message = inDeviceManager.GetNextMessage();
        if( message.Encode() > 0 )
        {
            *(int*)outKey = (int)message.m_data1;
            *(int*)waitingforkey = false;
            ImGui::PopID();
            return true;
        }
    }
    ImGui::PopID();
    return false;
}

bool MidiBindButtonNew( int inImGUIID, MidiDevice& inDeviceManager, int* outKey, bool* waitingforkey, std::string inLabel = "", const ImVec2& size_arg = ImVec2( 0, 0 ) )
{
    ImGui::PushID( inImGUIID );

    Input& editorInput = GetEngine().GetEditorInput();
    if( !( *waitingforkey ) )
    {
        if( ImGui::Button( ( (KeyCode)( *outKey ) == KeyCode::Unknown ) ? std::string( inLabel + "Not Bound" ).c_str() : std::string( inLabel + std::to_string( *outKey ) ).c_str(), size_arg ) )
        {
            *(int*)waitingforkey = true;

            // Pump the messages out the queue
            inDeviceManager.PumpMessages();
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
        if( ImGui::IsWindowFocused() )
        {
            auto messages = inDeviceManager.PumpMessages();
            for( auto message : messages )
            {
                if( message.IsOnType() )
                {
                    *(int*)outKey = (int)message.m_data1;
                    *(int*)waitingforkey = false;
                    ImGui::PopID();
                    return true;
                }
            }
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
    //m_midiDeviceManager.OpenAllDevices();
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
    OPTICK_CATEGORY( "PadBindingWidget", Optick::Category::UI );
    ImGui::Begin( "Pad Bindings", &IsOpen );
    {
        HavanaUtils::Label( "Midi Device" );
        if( ImGui::BeginCombo( "##Device", m_selectedMidiDeviceName.empty() ? "Select a device" : m_selectedMidiDeviceName.c_str() ) )
        {
            for (int i = 0; i < m_midiDeviceManager.GetNumActiveDevices(); ++i)
            {
                if( ImGui::Selectable( m_midiDeviceManager.GetDeviceName(i).c_str() ) )
                {
                    m_selectedMidiDeviceName = m_midiDeviceManager.GetDeviceName( i );
                }
            }
            
            ImGui::EndCombo();
        }
    }
    auto& m_midiDevice = MidiDevice::GetInstance();
    {
        //m_midiDevice.IsPaused = !ImGui::IsWindowFocused();
        HavanaUtils::Label( "Midi Device New" );
        if( ImGui::BeginCombo( "##Device2", m_selectedMidiDeviceName.empty() ? "Select a device" : m_selectedMidiDeviceName.c_str() ) )
        {
            for( int i = 0; i < m_midiDevice.m_devices.size(); ++i )
            {
                if( ImGui::Selectable( m_midiDevice.m_devices[i].Name.c_str()) )
                {
                    m_selectedMidiDeviceName = m_midiDevice.m_devices[i].Name;
                    m_midiDevice.OpenMidiDevice( i );
                }
            }

            ImGui::EndCombo();
        }
    }
    auto& mappings = PadMappingStorage::GetInstance();

    for( int16_t id = PadId::Invalid + 1; id < PadId::COUNT; ++id )
    {
        auto& thing = mappings.mappedPads[id];
        HavanaUtils::Label( thing.padName );
        float remainingSpace = ImGui::GetContentRegionAvail().x;
        KeybindButton( id, &thing.keyboardBinding, &keyCatchState[id], "Keyboard: ", { remainingSpace / 2.f, 0 } );
        ImGui::SameLine();
        MidiBindButtonNew( id + PadId::COUNT, m_midiDevice, &thing.midiBinding, &midiCatchState[id], "Midi Pad: ", { -1.f, 0 } );

    }

    float remainingSpace = ImGui::GetContentRegionAvail().x;

    ImGui::PushStyleColor( ImGuiCol_ButtonHovered, ACCENT_RED );
    ImGui::PushStyleColor( ImGuiCol_ButtonActive, (ImVec4)ImColor::HSV( .0f, 0.8f, 0.8f ) );
    if( ImGui::Button( "Reset Keyboard", { remainingSpace / 4.f, 0.f } ) )
    {
        for( auto& pad : mappings.mappedPads )
        {
            pad.keyboardBinding = 0;
        }
    }
    ImGui::SameLine();
    if( ImGui::Button( "Reset MIDI", { remainingSpace / 4.f, 0.f } ) )
    {
        for( auto& pad : mappings.mappedPads )
        {
            pad.midiBinding = 0;
        }
    }
    ImGui::PopStyleColor( 2 );

    ImGui::SameLine();

    ImGui::PushStyleColor( ImGuiCol_Button, (ImVec4)ImColor::HSV( 2.f / 7.0f, 0.6f, 0.6f ) );
    ImGui::PushStyleColor( ImGuiCol_ButtonHovered, (ImVec4)ImColor::HSV( 2.f / 7.0f, 0.7f, 0.7f ) );
    ImGui::PushStyleColor( ImGuiCol_ButtonActive, (ImVec4)ImColor::HSV( 2.f / 7.0f, 0.8f, 0.8f ) );
    if( ImGui::Button( "Save Pad Mappings", { -1.f, 0 } ) )
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
        outFile.Write( mappings.saveData.dump(1) );
    }
    ImGui::PopStyleColor( 3 );

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
            padData.padName = PadUtils::GetPadName(id);
        }
    }
}
