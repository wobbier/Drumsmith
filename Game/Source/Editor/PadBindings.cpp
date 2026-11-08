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
        if( !thing.extraMidi.empty() )
        {
            std::string extras = "Also: ";
            for( const MidiNoteBinding& extra : thing.extraMidi )
            {
                extras += std::to_string( extra.note ) + ( extra.articulation == Articulation::Normal ? "" : std::string( " " ) + PadUtils::GetArticulationName( extra.articulation ) ) + "  ";
            }
            HavanaUtils::SkipLabel();
            ImGui::TextDisabled( "%s", extras.c_str() );
        }
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
            pad.extraMidi.clear();
        }
    }
    ImGui::PopStyleColor( 2 );
    ImGui::SameLine();
    if( ImGui::Button( "Standard e-kit MIDI", { remainingSpace / 4.f, 0.f } ) )
    {
        mappings.ApplyStandardKitMidi();
    }

    ImGui::SameLine();

    ImGui::PushStyleColor( ImGuiCol_Button, (ImVec4)ImColor::HSV( 2.f / 7.0f, 0.6f, 0.6f ) );
    ImGui::PushStyleColor( ImGuiCol_ButtonHovered, (ImVec4)ImColor::HSV( 2.f / 7.0f, 0.7f, 0.7f ) );
    ImGui::PushStyleColor( ImGuiCol_ButtonActive, (ImVec4)ImColor::HSV( 2.f / 7.0f, 0.8f, 0.8f ) );
    if( ImGui::Button( "Save Pad Mappings", { -1.f, 0 } ) )
    {
        mappings.Save();
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

    std::vector<bool> loaded( PadId::COUNT, false );
    bool hasExtras = false;
    Path mappingConfig( "Assets/Config/PadMappings.json" );
    if( mappingConfig.Exists )
    {
        File outFile( mappingConfig );
        saveData = json::parse( outFile.Read(), nullptr, false );
        if( saveData.is_object() && saveData.contains( "PadMap" ) )
        {
            for( auto& pad : saveData["PadMap"] )
            {
                const int16_t id = pad.value( "ID", static_cast<int16_t>( -1 ) );
                if( id < 0 || id >= PadId::COUNT )
                {
                    continue;
                }
                auto& padData = mappedPads[id];
                padData.padId = id;
                padData.keyboardBinding = pad.value( "KB", 0 );
                padData.midiBinding = pad.value( "MIDI", 0 );
                padData.padName = PadUtils::GetPadName( id );
                if( pad.contains( "MIDIExtra" ) && pad["MIDIExtra"].is_array() )
                {
                    hasExtras = true;
                    for( const json& extra : pad["MIDIExtra"] )
                    {
                        MidiNoteBinding binding;
                        binding.note = extra.value( "Note", 0 );
                        binding.articulation = PadUtils::GetArticulation( extra.value( "Articulation", std::string( "Normal" ) ) );
                        if( binding.note > 0 )
                        {
                            padData.extraMidi.push_back( binding );
                        }
                    }
                }
                loaded[id] = true;
            }
        }
    }

    // Pads the file predates (the pedal, splash, china), and a file from before extra notes
    // existed, get the standard kit's notes; the player's own main notes are kept.
    for( int16_t id = PadId::Invalid + 1; id < PadId::COUNT; ++id )
    {
        int32_t main = 0;
        std::vector<MidiNoteBinding> extra;
        StandardKitNotes( static_cast<PadId>( id ), main, extra );
        if( !loaded[id] )
        {
            mappedPads[id].midiBinding = main;
        }
        if( !hasExtras )
        {
            mappedPads[id].extraMidi = extra;
        }
    }
}


void PadMappingStorage::StandardKitNotes( PadId inPad, int32_t& outMain, std::vector<MidiNoteBinding>& outExtra )
{
    outExtra.clear();
    switch( inPad )
    {
    case PadId::Bass: outMain = 36; outExtra = { { 35, Articulation::Normal } }; break;
    case PadId::Snare: outMain = 38; outExtra = { { 40, Articulation::Rim }, { 37, Articulation::CrossStick } }; break;
    case PadId::ClosedHiHat: outMain = 42; outExtra = { { 22, Articulation::Normal } }; break;
    case PadId::OpenHiHat: outMain = 46; outExtra = { { 26, Articulation::Normal } }; break;
    case PadId::HiHatPedal: outMain = 44; break;
    case PadId::Crash1: outMain = 49; outExtra = { { 55, Articulation::Normal } }; break;
    case PadId::Crash2: outMain = 57; outExtra = { { 52, Articulation::Normal } }; break;
    case PadId::Ride: outMain = 51; outExtra = { { 53, Articulation::Bell }, { 59, Articulation::Normal } }; break;
    case PadId::HighTom: outMain = 48; outExtra = { { 50, Articulation::Rim } }; break;
    case PadId::MidTom: outMain = 45; outExtra = { { 47, Articulation::Rim } }; break;
    case PadId::FloorTom: outMain = 43; outExtra = { { 58, Articulation::Rim } }; break;
    default: outMain = 0; break;
    }
}


void PadMappingStorage::ApplyStandardKitMidi()
{
    for( int16_t id = PadId::Invalid + 1; id < PadId::COUNT; ++id )
    {
        StandardKitNotes( static_cast<PadId>( id ), mappedPads[id].midiBinding, mappedPads[id].extraMidi );
    }
}


void PadMappingStorage::Resolve( int inNote, std::vector<Resolved>& outResolved ) const
{
    outResolved.clear();
    for( const PadDefinition& pad : mappedPads )
    {
        if( pad.padId < 0 )
        {
            continue;
        }
        if( pad.midiBinding > 0 && pad.midiBinding == inNote )
        {
            outResolved.push_back( { static_cast<PadId>( pad.padId ), Articulation::Normal } );
        }
        for( const MidiNoteBinding& extra : pad.extraMidi )
        {
            if( extra.note == inNote )
            {
                outResolved.push_back( { static_cast<PadId>( pad.padId ), extra.articulation } );
            }
        }
    }
}


void PadMappingStorage::Save()
{
    saveData = json::object();
    json& padData = saveData["PadMap"];
    for( const PadDefinition& pad : mappedPads )
    {
        json entry;
        entry["ID"] = pad.padId;
        entry["NAME"] = pad.padName;
        entry["KB"] = pad.keyboardBinding;
        entry["MIDI"] = pad.midiBinding;
        json& extras = entry["MIDIExtra"];
        extras = json::array();
        for( const MidiNoteBinding& extra : pad.extraMidi )
        {
            extras.push_back( { { "Note", extra.note }, { "Articulation", PadUtils::GetArticulationName( extra.articulation ) } } );
        }
        padData.push_back( entry );
    }
    File outFile( Path( "Assets/Config/PadMappings.json" ) );
    outFile.Write( saveData.dump( 1 ) );
}
