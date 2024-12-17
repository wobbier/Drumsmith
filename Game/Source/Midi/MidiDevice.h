#pragma once
#include <vector>
#include <string>
#include "Singleton.h"

class RtMidiIn;

struct MidiDeviceInfo
{
    std::string Name;
    int Port = 0;
    // Is this needed?
    bool IsOpen = false;
};

struct MidiMessageNew
{
    std::uint8_t m_status = 0;
    std::uint8_t m_data1 = 0;
    std::uint8_t m_data2 = 0;

    std::uint8_t GetMessageType() const
    {
        return ( m_status & 0xF0 ) >> 4; // 0x9 -> Note On
    }

    bool IsOnType() const
    {
        return GetMessageType() == 9;
    }
    bool IsOffType() const
    {
        return GetMessageType() == 8;
    }
};

class MidiDevice
{
    ME_SINGLETON_DEFINITION(MidiDevice);
    MidiDevice();
public:
    RtMidiIn* m_midiIn = nullptr;

    MidiDeviceInfo& OpenMidiDevice( unsigned int inIndex );
    MidiDeviceInfo& OpenMidiDevice( const std::string& inName );
    void CloseMidiDevice();

    void RefreshDevices();
    const std::vector<MidiDeviceInfo>& GetDevices() const;

    std::vector<MidiMessageNew> PumpMessages();

    std::vector<MidiDeviceInfo> m_devices;
    bool IsPaused = false;
};