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
    // back to the first device. Either way the name is remembered as the wanted device: Poll
    // opens it when it is plugged in later, and again after it was unplugged.
    bool OpenMidiDevice( unsigned int inIndex );
    bool OpenMidiDevice( const std::string& inName );
    void CloseMidiDevice();

    void RefreshDevices();
    const std::vector<MidiDeviceInfo>& GetDevices() const;

    // Hot-plug: call every frame from whatever is running (menus, gameplay, the editor's
    // windows). About once a second it lists the ports again; when they changed it drops an
    // unplugged device and opens the wanted one if it has come back. Cheap to call more than once
    // a frame.
    void Poll();
    // Goes up whenever the device list or the open device changes, so a page can tell when to
    // list the devices again.
    int GetGeneration() const { return m_generation; }
    // The open device's name, or empty.
    const std::string& GetOpenDeviceName() const { return m_openName; }
    // The open device was unplugged and nothing has been opened since.
    bool IsUnplugged() const { return m_unplugged; }
    // Whether inName names the same device as inOther, allowing for the port numbers the system
    // appends (ALSA's "28:0", WinMM's index), which change when a device is plugged in again.
    static bool SameDevice( const std::string& inName, const std::string& inOther );

    // Every message received in the last second since the previous call, oldest first. Messages
    // arrive on RtMidi's thread through a callback and wait in a locked queue.
    std::vector<MidiMessageNew> PumpMessages();

    std::vector<MidiDeviceInfo> m_devices;
    bool IsPaused = false;

private:
    static void OnMessage( double inDeltaTime, std::vector<unsigned char>* inMessage, void* inUserData );

    // The index of the port inName names (exactly, else by SameDevice), or -1.
    int FindDevice( const std::string& inName ) const;
    void OpenWanted();

    std::mutex m_queueLock;
    std::vector<MidiMessageNew> m_queue;
    // What OpenMidiDevice was last asked for (m_wantsDevice: it was asked at all), and what is open.
    std::string m_wantedName;
    bool m_wantsDevice = false;
    std::string m_openName;
    int m_generation = 0;
    bool m_unplugged = false;
    std::chrono::steady_clock::time_point m_lastPoll{};
};