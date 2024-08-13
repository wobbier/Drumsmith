#include "MidiDevice.h"
#include "RtMidi.h"
#include "Core\Assert.h"
#include "CLog.h"

MidiDevice::MidiDevice()
{
    try {
        m_midiIn = new RtMidiIn();
    }
    catch( RtMidiError& error ) {
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

void MidiDevice::CloseMidiDevice()
{
    m_midiIn->closePort();
}

void MidiDevice::RefreshDevices()
{
    m_devices.clear();
    // Check available ports.
    unsigned int nPorts = m_midiIn->getPortCount();
    if( nPorts == 0 ) {
        BRUH( "No MIDI input ports available!" );
        delete m_midiIn;
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

std::vector<MidiMessageNew> MidiDevice::PumpMessages()
{
    std::vector<MidiMessageNew> messages;
    // Infinite loop to keep reading incoming MIDI messages.
    while( !IsPaused ) {
        std::vector<unsigned char> message;
        int nBytes, i;
        double stamp = m_midiIn->getMessage( &message );
        nBytes = message.size();
        for( i = 0; i < nBytes; i++ ) {
            std::cout << "Byte " << i << " = " << (int)message[i] << ", ";
        }
        if( nBytes > 0 ) {
            std::cout << "stamp = " << stamp << std::endl;
        }
        if (message.empty())
        {
            break;
        }
        MidiMessageNew msg;
        msg.m_status = message[0];
        msg.m_data1 = message[1];
        msg.m_data2 = message[2];
        std::cout << "Status " << 0 << " = " << (int)msg.GetMessageType() << std::endl;
        messages.push_back( msg );
    }
    return messages;
}

