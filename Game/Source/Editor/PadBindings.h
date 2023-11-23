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

enum class  OldPadId
{
    Invalid = -1,
    Bass = 0,
    Snare,
    HighTom,
    MidTom,
    FloorTom,
    OpenHiHat,
    ClosedHiHat,
    Crash,
    Ride,
    COUNT
};

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
    COUNT
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
        ME_ASSERT_MSG( false, "Unhandles note name" );
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
        case PadId::FloorTom:
            return 0xFFA0C263;
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

}

struct PadDefinition
{
    int16_t padId = PadId::Invalid;
    std::string padName;
    int32_t keyboardBinding;
    int32_t midiBinding;
};

class PadMappingStorage
{
    ME_SINGLETON_DEFINITION( PadMappingStorage );

public:
    PadMappingStorage();
    std::vector<PadDefinition> mappedPads;
    json saveData;
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
};

ME_REGISTER_EDITOR_WIDGET( PadBindingWidget );

#endif