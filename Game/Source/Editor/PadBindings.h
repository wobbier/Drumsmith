#pragma once
#include "Dementia.h"
#include <stdint.h>
#include "Singleton.h"
#include <string>
#include <vector>
#include "Engine/Input.h"
#include "JSON.h"
#include "Math/Vector3.h"
#include "Core/Assert.h"
#include "Midi/MidiDevice.h"

enum PadId
{
    Invalid = -1,
    Bass = 0,
    Snare,
    OpenHiHat,
    ClosedHiHat,
    Crash1,
    HighTom,
    MidTom,
    FloorTom,
    Ride,
    Crash2,
    // Appended so saved pad IDs keep their meaning.
    HiHatPedal,
    Splash,
    China,
    COUNT
};

// How a pad is played, beyond which pad it is (Docs/MIDI-and-Pads.md). Open and closed hi-hat are
// separate pads; these are the strokes a pad can take.
enum class Articulation : uint8_t
{
    Normal = 0,
    Rim,          // Rimshot on a snare or tom; the edge of a cymbal
    CrossStick,   // Snare side-stick
    Bell,         // Ride or crash bell
    Count
};

namespace PadUtils
{
    static const char* GetPadName( int16_t inPadId )
    {
        switch( inPadId )
        {
        case Invalid:
            break;
        case Bass:
            return "Bass";
        case Snare:
            return "Snare";
        case HighTom:
            return "HighTom";
        case MidTom:
            return "MidTom";
        case FloorTom:
            return "FloorTom";
        case OpenHiHat:
            return "OpenHiHat";
        case ClosedHiHat:
            return "ClosedHiHat";
        case Crash1:
            return "Crash";
        case Ride:
            return "Ride";
        case Crash2:
            return "Crash2";
        case HiHatPedal:
            return "HiHatPedal";
        case Splash:
            return "Splash";
        case China:
            return "China";
        case COUNT:
        default:
            break;
        }
        return "";
    }


    inline static const char* GetPadName( PadId inPadId )
    {
        return GetPadName( static_cast<int16_t>( inPadId ) );
    }


    static const char* GetPadId( int16_t inPadId )
    {
        switch( inPadId )
        {
        case Invalid:
            break;
        case Bass:
            return "bass1";
        case Snare:
            return "snare1";
        case HighTom:
            return "tom1";
        case MidTom:
            return "tom2";
        case FloorTom:
            return "tom3";
        case OpenHiHat:
            return "open_hh";
        case ClosedHiHat:
            return "closed_hh";
        case Crash1:
            return "crash1";
        case Ride:
            return "ride1";
        case Crash2:
            return "crash2";
        case HiHatPedal:
            return "hh_pedal";
        case Splash:
            return "splash1";
        case China:
            return "china1";
        case COUNT:
        default:
            break;
        }
        ME_ASSERT_MSG(false, "Dumbass note name" );
        return "";
    }


    inline static const char* GetPadId( PadId inPadId )
    {
        return GetPadId( static_cast<int16_t>( inPadId ) );
    }


    static PadId GetNewPadId( std::string inPadId )
    {
        if( inPadId == "bass1" )
            return PadId::Bass;
        if( inPadId == "snare1" )
            return PadId::Snare;
        if( inPadId == "tom1" )
            return PadId::HighTom;
        if( inPadId == "tom2" )
            return PadId::MidTom;
        if( inPadId == "tom3" )
            return PadId::FloorTom;
        if( inPadId == "open_hh" )
            return PadId::OpenHiHat;
        if( inPadId == "closed_hh" )
            return PadId::ClosedHiHat;
        if( inPadId == "crash1" )
            return PadId::Crash1;
        if( inPadId == "crash2" )
            return PadId::Crash2;
        if( inPadId == "ride1" )
            return PadId::Ride;
        if( inPadId == "hh_pedal" )
            return PadId::HiHatPedal;
        if( inPadId == "splash1" )
            return PadId::Splash;
        if( inPadId == "china1" )
            return PadId::China;
        ME_ASSERT_MSG( false, "Unhandled note name" );
        return PadId::COUNT;
    }


    static int GetNoteColorABGR( PadId inId )
    {
        switch( inId )
        {
        case PadId::Bass:
            return 0xFF4A9FE5;
        case PadId::Snare:
            return 0xFF334FCB;
        case PadId::ClosedHiHat:
        case PadId::OpenHiHat:
            return 0xFF73EDF3;
        case PadId::HighTom:
            return 0xFFC38839;
        case PadId::MidTom:
        case PadId::Crash1:
        case PadId::Crash2:
        case PadId::FloorTom:
            return 0xFFA0C263;
        case PadId::Ride:
            return 0xFFE0B040;
        case PadId::HiHatPedal:
            return 0xFF73EDF3;
        case PadId::Splash:
            return 0xFFE07AD8;
        case PadId::China:
            return 0xFF3A8CF0;
        }
        return 0xFFFFFFFF;
    }


    static Vector3 HexToVector4( uint32_t hexColor )
    {
        Vector3 vec;

        //vec.a = ( hexColor >> 24 ) & 0xFF; // Extract alpha
        vec.z = static_cast<float>( ( hexColor >> 16 ) & 0xFF ); // Extract blue
        vec.y = static_cast<float>( ( hexColor >> 8 ) & 0xFF );  // Extract green
        vec.x = static_cast<float>( hexColor & 0xFF );           // Extract red

        return vec / 255.f;
    }


    inline static Vector3 GetNoteColor( PadId inId )
    {
        return HexToVector4( GetNoteColorABGR( inId ) );
    }


    inline static const char* GetArticulationName( Articulation inArticulation )
    {
        switch( inArticulation )
        {
        case Articulation::Rim: return "Rim";
        case Articulation::CrossStick: return "CrossStick";
        case Articulation::Bell: return "Bell";
        default: return "Normal";
        }
    }


    inline static Articulation GetArticulation( const std::string& inName )
    {
        if( inName == "Rim" ) return Articulation::Rim;
        if( inName == "CrossStick" ) return Articulation::CrossStick;
        if( inName == "Bell" ) return Articulation::Bell;
        return Articulation::Normal;
    }


    inline static bool IsCymbal( PadId inId )
    {
        switch( inId )
        {
        case PadId::OpenHiHat:
        case PadId::ClosedHiHat:
        case PadId::Crash1:
        case PadId::Crash2:
        case PadId::Ride:
        case PadId::Splash:
        case PadId::China:
            return true;
        default:
            return false;
        }
    }

}

// A further MIDI note a pad sends, and the stroke it means (a snare's rim, a ride's bell).
struct MidiNoteBinding
{
    int32_t note = 0;
    Articulation articulation = Articulation::Normal;
};

struct PadDefinition
{
    int16_t padId = PadId::Invalid;
    std::string padName;
    int32_t keyboardBinding = 0;
    // The pad's main note (a plain stroke), plus any others it sends.
    int32_t midiBinding = 0;
    std::vector<MidiNoteBinding> extraMidi;
};

class PadMappingStorage
{
    ME_SINGLETON_DEFINITION( PadMappingStorage );

public:
    PadMappingStorage();

    // A MIDI note's meanings: every pad (and stroke) bound to it. Usually one; a kit that sends
    // one note for two pads (open and closed hi-hat on 46) gives both.
    struct Resolved
    {
        PadId pad = PadId::Invalid;
        Articulation articulation = Articulation::Normal;
    };
    void Resolve( int inNote, std::vector<Resolved>& outResolved ) const;

    // Roland-style e-kit notes (most modules use them): every pad's main note and its rim, edge,
    // bell and pedal notes. Splash and china are left unbound (their notes clash with crash edges).
    void ApplyStandardKitMidi();
    void Save();

    std::vector<PadDefinition> mappedPads;
    json saveData;

private:
    static void StandardKitNotes( PadId inPad, int32_t& outMain, std::vector<MidiNoteBinding>& outExtra );
};


#if USING(ME_EDITOR)

#include <Editor/WidgetRegistry.h>
#include "HavanaWidget.h"

class PadBindingWidget
    : public HavanaWidget
{
public:
    PadBindingWidget();
    ~PadBindingWidget();

    void Init() override;
    void Destroy() override;

    void Update() override;
    void Render() override;
    bool keyCatchState[PadId::COUNT];
    bool midiCatchState[PadId::COUNT];
    std::string m_selectedMidiDeviceName;
};

ME_REGISTER_EDITOR_WIDGET( PadBindingWidget );

#endif
