#include <Cores/VocalsTestCore.h>
#include <Components/Transform.h>
#include "CoreGame/TrackList.h"
#include "Engine/Engine.h"
#include "Editor/PadBindings.h"
#include "ECS/Core.h"
#include "Cores/AudioCore.h"
#include "Resources/SoundResource.h"
#include <fmod.hpp>
#include "Components/VocalsTestComponent.h"
#include <deque>


VocalsTestCore::VocalsTestCore()
    : Base( ComponentFilter().Requires<Transform>().Requires<VocalsTestComponent>() )
{
}

VocalsTestCore::~VocalsTestCore()
{
}

void VocalsTestCore::Init()
{
}

void VocalsTestCore::OnAddedToWorld()
{
}

void VocalsTestCore::OnRemovedFromWorld()
{
    //EventManager::GetInstance().DeRegisterReciever( this );
    //MidiDevice::GetInstance().CloseMidiDevice();
}

void VocalsTestCore::OnStop()
{
}

void VocalsTestCore::OnEntityAdded( Entity& NewEntity )
{
}

void VocalsTestCore::OnEntityRemoved( Entity& InEntity )
{
}

const int MIDI_NOTES[] = { 36, 38, 40, 41, 43, 45, 47, 48, 50, 52, 53, 55, 57, 59, 60 }; // C2 to C6 in steps

int SnapToClosestMIDI( int midiNote )
{
    int closestNote = MIDI_NOTES[0];
    for( int note : MIDI_NOTES )
    {
        if( std::abs( note - midiNote ) < std::abs( closestNote - midiNote ) )
            closestNote = note;
    }
    return closestNote;
}


float smoothedValue = 50.0f; // Start at middle range
const float SMOOTHING_FACTOR = 0.2f; // Lower value = smoother
std::deque<float> pitchHistory;
const int SMOOTHING_WINDOW = 100;
void VocalsTestCore::Update( const UpdateContext& context )
{
    ProcessFFT();
    for( auto& ent : GetEntities() )
    {
        Transform& transform = ent.GetComponent<Transform>();

        //smoothedValue = SMOOTHING_FACTOR * mappedValue + ( 1 - SMOOTHING_FACTOR ) * smoothedValue;
        transform.SetPosition( { 0, (float)mappedValue, 0 } );
    }
}

void VocalsTestCore::OnStart()
{
    audioCore = GetEngine().AudioThread;
    audioSystem = audioCore->GetSystem();
    testVocals = MakeShared<Sound>( Path( "Assets/DLC/Saosin - Mookies Last Christmas/vocals.ogg" ), audioSystem );


    audioSystem->playSound( testVocals->Handle, 0, false, &channel );
    // AttachFFT
    audioSystem->createDSPByType( FMOD_DSP_TYPE_FFT, &fftDsp );
    fftDsp->setParameterInt( FMOD_DSP_FFT_WINDOWTYPE, FMOD_DSP_FFT_WINDOW_HAMMING );
    fftDsp->setParameterInt( FMOD_DSP_FFT_WINDOWSIZE, 1024 );  // Resolution of FFT
    channel->addDSP( 0, fftDsp );
}


bool VocalsTestCore::OnEvent( const BaseEvent& evt )
{
    return false;
}

void VocalsTestCore::ProcessFFT()
{
    FMOD_DSP_PARAMETER_FFT* fftData = nullptr;
    unsigned int length;

    fftDsp->getParameterData( FMOD_DSP_FFT_SPECTRUMDATA, (void**)&fftData, &length, nullptr, 0 );

    if( fftData && fftData->numchannels > 0 )
    {
        int numBins = fftData->length;
        float binWidth = 48000.0f / ( 2 * numBins );

        int maxIndex = 0;
        float maxMagnitude = 0.0f;

        for( int i = 0; i < numBins; ++i )
        {
            if( fftData->spectrum[0][i] > maxMagnitude )
            {
                maxMagnitude = fftData->spectrum[0][i];
                maxIndex = i;
            }
        }

        float dominantFrequency = maxIndex * binWidth;

        int midiNote = round( 12 * log2( dominantFrequency / 440.0 ) + 69 );
        midiNote = std::clamp( midiNote, 36, 84 );

        int snappedMIDI = SnapToClosestMIDI( midiNote );

        mappedValue = ( snappedMIDI - 36 ) / 48.0f * 100;

        std::cout << "Smoothed Pitch Graph Value: " << smoothedPitch << "/100" << std::endl;
    }
}



#if USING( ME_EDITOR )

std::vector<float> pitchGraph;  // Store the last 100 pitch values
void VocalsTestCore::OnEditorInspect()
{
    if( pitchGraph.size() > 100 )
        pitchGraph.erase( pitchGraph.begin() );  // Keep buffer size 100

    pitchGraph.push_back( mappedValue );  // Add the new value

    ImGui::PlotLines( "Pitch Graph", pitchGraph.data(), pitchGraph.size(), 0, nullptr, 0.0f, 100.0f, ImVec2( 400, 150 ) );
}

#endif