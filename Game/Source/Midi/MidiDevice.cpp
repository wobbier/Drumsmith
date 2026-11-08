#include "MidiDevice.h"
#include <RtMidi.h>
#include "Core/Assert.h"
#include "CLog.h"
#include <algorithm>

MidiDevice::MidiDevice()
{
    try
    {
        m_midiIn = new RtMidiIn();
    }
    catch( RtMidiError& error )
    {
        delete m_midiIn;
        m_midiIn = nullptr;
        error.printMessage();
        return;
    }
    RefreshDevices();
    // Drums only send notes and controllers: skip sysex, timing clock and active sensing.
    m_midiIn->ignoreTypes( true, true, true );
    m_midiIn->setCallback( &MidiDevice::OnMessage, this );
}


void MidiDevice::OnMessage( double inDeltaTime, std::vector<unsigned char>* inMessage, void* inUserData )
{
    // RtMidi's thread: only stamp and queue. Never touch the world, events or resources here.
    if( !inMessage || inMessage->size() < 3 )
    {
        return;
    }
    MidiMessageNew msg;
    msg.m_status = ( *inMessage )[0];
    msg.m_data1 = ( *inMessage )[1];
    msg.m_data2 = ( *inMessage )[2];
    msg.m_arrival = std::chrono::steady_clock::now();
    MidiDevice* device = static_cast<MidiDevice*>( inUserData );
    std::lock_guard<std::mutex> lock( device->m_queueLock );
    // A game that stops pumping must not grow the queue forever.
    if( device->m_queue.size() < 4096 )
    {
        device->m_queue.push_back( msg );
    }
}


bool MidiDevice::OpenMidiDevice( unsigned int inIndex )
{
    if( !m_midiIn || inIndex >= m_devices.size() )
    {
        return false;
    }
    if( !m_devices[inIndex].IsOpen )
    {
        CloseMidiDevice();
        m_midiIn->openPort( inIndex );
        m_devices[inIndex].IsOpen = true;
    }
    return true;
}


bool MidiDevice::OpenMidiDevice( const std::string& inName )
{
    for( auto& device : m_devices )
    {
        if( device.Name == inName )
        {
            return OpenMidiDevice( device.Port );
        }
    }
    if( !m_devices.empty() )
    {
        BRUH( "MIDI: no device named '" + inName + "'; opening " + m_devices.front().Name );
    }
    return OpenMidiDevice( 0u );
}


void MidiDevice::CloseMidiDevice()
{
    if( !m_midiIn )
    {
        return;
    }
    m_midiIn->closePort();
    for( auto& device : m_devices )
    {
        device.IsOpen = false;
    }
}


void MidiDevice::RefreshDevices()
{
    m_devices.clear();
    // Check available ports.
    unsigned int nPorts = m_midiIn->getPortCount();
    if( nPorts == 0 )
    {
        BRUH( "No MIDI input ports available!" );
        return;
    }

    for( unsigned int i = 0; i < nPorts; ++i )
    {
        MidiDeviceInfo newDevice;
        newDevice.Name = m_midiIn->getPortName( i );
        newDevice.Port = i;
        m_devices.push_back( newDevice );
    }
}


const std::vector<MidiDeviceInfo>& MidiDevice::GetDevices() const
{
    return m_devices;
}


std::vector<MidiMessageNew> MidiDevice::PumpMessages()
{
    std::vector<MidiMessageNew> messages;
    {
        std::lock_guard<std::mutex> lock( m_queueLock );
        messages.swap( m_queue );
    }
    // A reader that wasn't pumping (an unfocused editor window) shouldn't get a burst of old hits.
    const auto oldest = std::chrono::steady_clock::now() - std::chrono::seconds( 1 );
    messages.erase( std::remove_if( messages.begin(), messages.end(), [oldest]( const MidiMessageNew& m ) { return m.m_arrival < oldest; } ), messages.end() );
    return messages;
}
