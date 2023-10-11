#pragma once
#include "Dementia.h"
#include <stdint.h>
#include "Singleton.h"
#include <string>
#include <vector>
#include "Engine/Input.h"
#include "JSON.h"

enum PadId
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
        case Crash:
            return "Crash";
        case Ride:
            return "Ride";
        case COUNT:
        default:
            break;
        }
        return "";
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
        case Crash:
            return "crash1";
        case Ride:
            return "ride1";
        case COUNT:
        default:
            break;
        }
        return "";
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