#include <nlohmann/json.hpp>
#include <fstream>
#include "Drumset.h"

Drumset::Drumset( FMOD::System* system )
    : fmodSystem( system )
{
}


Drumset::~Drumset()
{
    for( auto& pair : sounds )
    {
        pair.second->release();
    }
}


void Drumset::loadSound( PadId pad, const std::string& filepath )
{
    FMOD::Sound* sound;
    Path drumPath( filepath );
    FMOD_RESULT result = fmodSystem->createSound( drumPath.FullPath.c_str(), FMOD_CREATESAMPLE, nullptr, &sound );
    if( result == FMOD_OK )
    {
        sounds[pad] = sound;
    }
    else
    {
        // Log error
        // I should really make a FMOD_IF macro that does error handling...
    }
}


void Drumset::hitPad( PadId pad, float velocity )
{
    if( sounds.find( pad ) == sounds.end() )
    {
        return;
    }

    FMOD::Channel* channel;
    fmodSystem->playSound( sounds[pad], nullptr, false, &channel );

    float volume = velocityToVolume( velocity );
    channel->setVolume( volume );

    channels[pad] = channel;
}


float Drumset::velocityToVolume( float velocity )
{
    return std::clamp( velocity, 0.0f, 1.0f );
}


void Drumset::loadFromJson( const std::string& jsonPath )
{
    std::ifstream file( jsonPath );
    nlohmann::json jsonData;
    file >> jsonData;

    for( const auto& [padName, soundPath] : jsonData["kits"]["default"].items() )
    {
        PadId pad = stringToPadID( padName );
        loadSound( pad, soundPath );
    }
}


PadId Drumset::stringToPadID( const std::string& name )
{
    static const std::unordered_map<std::string, PadId> padMap = {
        {"Bass", PadId::Bass},
        {"Snare", PadId::Snare},
        {"OpenHiHat", PadId::OpenHiHat},
        {"ClosedHiHat", PadId::ClosedHiHat},
        {"Crash1", PadId::Crash1},
        {"HighTom", PadId::HighTom},
        {"MidTom", PadId::MidTom},
        {"FloorTom", PadId::FloorTom},
        {"Ride", PadId::Ride},
        {"Crash2", PadId::Crash2}
    };
    return padMap.at( name );
}
