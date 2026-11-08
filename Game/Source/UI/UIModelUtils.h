#pragma once
#include <Cores/UI/RmlUiCore.h>
#include "JSON.h"
#include <string>

// Small helpers for the RmlUi view models the menu controllers drive (Docs/UI-and-Menus.md).
namespace UIModel
{
    // The arguments of the event RmlUiCore::ModelPollEvent last returned, as a JSON array.
    inline json LastEventArgs( RmlUiCore& inUI, const std::string& inModel )
    {
        json args = json::parse( inUI.ModelLastEventArgs( inModel ), nullptr, false );
        return args.is_array() ? args : json::array();
    }


    // Argument inIndex as a number. Range inputs report their value as text, so both forms parse.
    inline double ArgNumber( const json& inArgs, size_t inIndex, double inDefault = -1.0 )
    {
        if( !inArgs.is_array() || inIndex >= inArgs.size() )
        {
            return inDefault;
        }
        const json& arg = inArgs[inIndex];
        if( arg.is_number() )
        {
            return arg.get<double>();
        }
        if( arg.is_boolean() )
        {
            return arg.get<bool>() ? 1.0 : 0.0;
        }
        if( arg.is_string() )
        {
            try
            {
                return std::stod( arg.get<std::string>() );
            }
            catch( const std::exception& )
            {
            }
        }
        return inDefault;
    }


    inline std::string ArgString( const json& inArgs, size_t inIndex )
    {
        if( !inArgs.is_array() || inIndex >= inArgs.size() )
        {
            return {};
        }
        const json& arg = inArgs[inIndex];
        return arg.is_string() ? arg.get<std::string>() : arg.dump();
    }
}
