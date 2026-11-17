#pragma once
#include <string>
#include <vector>

// Click tracks as WAV files: what a practice lesson and the calibration play as their "song",
// and the metronome a song can have laid over it (Docs/Audio.md).
namespace ClickTrack
{
    struct Click
    {
        double Seconds = 0.0;
        // A bar's first beat: higher and louder.
        bool Accent = false;
    };

    // Writes inSeconds of mono 16-bit silence with a 30 ms click at each of inClicks. Each click
    // starts on its own sample, so the clicks can't drift from what they are written for.
    bool Write( const std::string& inFile, const std::vector<Click>& inClicks, double inSeconds, int inSampleRate = 44100 );

    // The file a song's metronome is kept in, named for its clicks (so a changed beat grid is a
    // new file), written if it isn't there yet. Only the newest few are kept. Empty when there
    // are no clicks or the file can't be written.
    std::string MetronomeFile( const std::vector<Click>& inClicks );
}
