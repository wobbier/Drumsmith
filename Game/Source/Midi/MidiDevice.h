#pragma once
#include <vector>
#include <string>
#include <chrono>
#include <cstdint>
#include <mutex>
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
    uint8_t m_status = 0;
    uint8_t m_data1 = 0;
    uint8_t m_data2 = 0;
    // When RtMidi's thread received it (steady clock), so gameplay can judge the hit at the
    // moment it arrived rather than the frame that read it.
    std::chrono::steady_clock::time_point m_arrival{};

    uint8_t GetMessageType() const
    {
        return ( m_status & 0xF0 ) >> 4; // 0x9 -> Note On
    }

    // A note-on with velocity 0 is a note-off by MIDI convention.
    bool IsOnType() const
    {
        return GetMessageType() == 9 && m_data2 > 0;
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

    // Both return false when there is nothing to open. By name, an unknown or empty name falls
    // back to the first device.
    bool OpenMidiDevice( unsigned int inIndex );
    bool OpenMidiDevice( const std::string& inName );
    void CloseMidiDevice();

    void RefreshDevices();
    const std::vector<MidiDeviceInfo>& GetDevices() const;

    // Every message received in the last second since the previous call, oldest first. Messages
    // arrive on RtMidi's thread through a callback and wait in a locked queue.
    std::vector<MidiMessageNew> PumpMessages();

    std::vector<MidiDeviceInfo> m_devices;
    bool IsPaused = false;

private:
    static void OnMessage( double inDeltaTime, std::vector<unsigned char>* inMessage, void* inUserData );

    std::mutex m_queueLock;
    std::vector<MidiMessageNew> m_queue;
};