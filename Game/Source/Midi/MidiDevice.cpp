#include "MidiDevice.h"
#include <RtMidi.h>
#include "Core/Assert.h"
#include "CLog.h"
#include <algorithm>
#include <cctype>

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


namespace
{
    // A port name without the numbers the system appends: ALSA's client and port ("TD-17 28:0"),
    // WinMM's device index ("TD-17 1").
    std::string BaseName( const std::string& inName )
    {
        size_t end = inName.size();
        while( end > 0 && ( std::isdigit( static_cast<unsigned char>( inName[end - 1] ) ) || inName[end - 1] == ':' ) )
        {
            --end;
        }
        if( end == inName.size() || end == 0 || inName[end - 1] != ' ' )
        {
            return inName;
        }
        while( end > 0 && inName[end - 1] == ' ' )
        {
            --end;
        }
        return inName.substr( 0, end );
    }


    std::vector<std::string> PortNames( RtMidiIn& inMidi )
    {
        std::vector<std::string> names;
        try
        {
            const unsigned int count = inMidi.getPortCount();
            for( unsigned int i = 0; i < count; ++i )
            {
                names.push_back( inMidi.getPortName( i ) );
            }
        }
        catch( RtMidiError& error )
        {
            error.printMessage();
        }
        return names;
    }
}


bool MidiDevice::SameDevice( const std::string& inName, const std::string& inOther )
{
    return inName == inOther || ( !inName.empty() && BaseName( inName ) == BaseName( inOther ) );
}


int MidiDevice::FindDevice( const std::string& inName ) const
{
    for( const auto& device : m_devices )
    {
        if( device.Name == inName )
        {
            return device.Port;
        }
    }
    for( const auto& device : m_devices )
    {
        if( SameDevice( inName, device.Name ) )
        {
            return device.Port;
        }
    }
    return -1;
}


bool MidiDevice::OpenMidiDevice( unsigned int inIndex )
{
    if( !m_midiIn || inIndex >= m_devices.size() )
    {
        return false;
    }
    if( !m_wantsDevice || !SameDevice( m_wantedName, m_devices[inIndex].Name ) )
    {
        // Opened by index (the editor's device lists): this is the device to come back to.
        m_wantedName = m_devices[inIndex].Name;
    }
    m_wantsDevice = true;
    if( !m_devices[inIndex].IsOpen )
    {
        CloseMidiDevice();
        try
        {
            m_midiIn->openPort( inIndex );
        }
        catch( RtMidiError& error )
        {
            error.printMessage();
            return false;
        }
        m_devices[inIndex].IsOpen = true;
        m_openName = m_devices[inIndex].Name;
        m_unplugged = false;
        ++m_generation;
    }
    return true;
}


bool MidiDevice::OpenMidiDevice( const std::string& inName )
{
    m_wantedName = inName;
    m_wantsDevice = true;
    const int port = FindDevice( inName );
    if( port >= 0 )
    {
        return OpenMidiDevice( static_cast<unsigned int>( port ) );
    }
    if( m_devices.empty() )
    {
        return false;
    }
    if( !inName.empty() )
    {
        BRUH( "MIDI: no device named '" + inName + "'; opening " + m_devices.front().Name );
    }
    // The fallback isn't what was asked for: keep wanting the named device.
    const bool opened = OpenMidiDevice( 0u );
    m_wantedName = inName;
    return opened;
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
    if( !m_openName.empty() )
    {
        m_openName.clear();
        ++m_generation;
    }
}


void MidiDevice::RefreshDevices()
{
    if( !m_midiIn )
    {
        return;
    }
    const std::vector<std::string> names = PortNames( *m_midiIn );
    m_devices.clear();
    for( unsigned int i = 0; i < names.size(); ++i )
    {
        MidiDeviceInfo newDevice;
        newDevice.Name = names[i];
        newDevice.Port = static_cast<int>( i );
        // The open port stays open when the others around it change; only its index moves.
        newDevice.IsOpen = !m_openName.empty() && names[i] == m_openName;
        m_devices.push_back( newDevice );
    }
}


void MidiDevice::Poll()
{
    if( !m_midiIn )
    {
        return;
    }
    const auto now = std::chrono::steady_clock::now();
    if( now - m_lastPoll < std::chrono::seconds( 1 ) )
    {
        return;
    }
    m_lastPoll = now;

    const std::vector<std::string> names = PortNames( *m_midiIn );
    bool changed = names.size() != m_devices.size();
    for( size_t i = 0; i < names.size() && !changed; ++i )
    {
        changed = names[i] != m_devices[i].Name;
    }
    if( !changed )
    {
        return;
    }
    ++m_generation;
    const bool openGone = !m_openName.empty() && std::find( names.begin(), names.end(), m_openName ) == names.end();
    if( openGone )
    {
        BRUH( "MIDI: " + m_openName + " was unplugged" );
        // Its port is gone; close our end so the next open starts clean.
        m_midiIn->closePort();
        m_openName.clear();
        m_unplugged = true;
    }
    RefreshDevices();
    OpenWanted();
}


void MidiDevice::OpenWanted()
{
    if( !m_wantsDevice || m_devices.empty() )
    {
        return;
    }
    // The wanted device when it's there (also when a fallback is open in its place); else, with
    // nothing open, whatever is.
    const int wanted = FindDevice( m_wantedName );
    if( wanted >= 0 )
    {
        if( !m_devices[wanted].IsOpen )
        {
            const std::string name = m_wantedName;
            if( OpenMidiDevice( static_cast<unsigned int>( wanted ) ) )
            {
                BRUH( "MIDI: opened " + m_devices[wanted].Name );
            }
            m_wantedName = name;
        }
    }
    else if( m_openName.empty() )
    {
        // A stand-in for the wanted device: it is still wanted, and still counts as unplugged.
        const std::string name = m_wantedName;
        const bool unplugged = m_unplugged;
        if( OpenMidiDevice( 0u ) )
        {
            BRUH( "MIDI: opened " + m_devices.front().Name );
        }
        m_wantedName = name;
        m_unplugged = unplugged;
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
