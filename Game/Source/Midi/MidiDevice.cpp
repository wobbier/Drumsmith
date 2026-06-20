#include "MidiDevice.h"
#include <RtMidi.h>
#include "Core/Assert.h"
#include "CLog.h"

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
    // Don't ignore sysex, timing, or active sensing messages.
    m_midiIn->ignoreTypes( false, false, false );
}


MidiDeviceInfo& MidiDevice::OpenMidiDevice( unsigned int inIndex )
{
    ME_ASSERT_MSG( inIndex < m_devices.size(), "Trying to open a Midi device at an invalid index." );
    if( !m_devices[inIndex].IsOpen )
    {
        CloseMidiDevice();
        m_midiIn->openPort( inIndex );
        m_devices[inIndex].IsOpen = true;
    }
    return m_devices[inIndex];
}


MidiDeviceInfo& MidiDevice::OpenMidiDevice( const std::string& inName )
{
    for (auto& device : m_devices)
    {
        if (device.Name != inName)
        {
            continue;
        }
        return OpenMidiDevice( device.Port );
    }
    ME_ASSERT_MSG( false, "Failed to open device by name." );
    return OpenMidiDevice( 0 );
}


void MidiDevice::CloseMidiDevice()
{
    m_midiIn->closePort();
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
    if( !m_midiIn )
    {
        return {};
    }

    std::vector<MidiMessageNew> messages;
    std::vector<unsigned char> message;
    m_midiIn->getMessage( &message );
    while( message.size() >= 3 )
    {
        MidiMessageNew msg;
        msg.m_status = message[0];
        msg.m_data1  = message[1];
        msg.m_data2  = message[2];
        messages.push_back( msg );
        m_midiIn->getMessage( &message );
    }
    return messages;
}

