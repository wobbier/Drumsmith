#include <unordered_map>
#include <string>
#include <fmod.hpp>
#include "Editor\PadBindings.h"
#include "Path.h"

class Drumset
{
private:
    FMOD::System* fmodSystem;
    std::unordered_map<PadId, FMOD::Sound*> sounds;
    std::unordered_map<PadId, FMOD::Channel*> channels;

public:
    Drumset( FMOD::System* system );
    ~Drumset();

    void loadSound( PadId pad, const std::string& filepath );
    void hitPad( PadId pad, float velocity );
    float velocityToVolume( float velocity );

    void loadFromJson( const std::string& jsonPath );

    PadId stringToPadID( const std::string& name );
};
