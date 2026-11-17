#pragma once
#include "CoreGame/TrackList.h"
#include "Singleton.h"
#include <array>
#include <string>
#include <vector>

class GameSettings;

// The audio and video delay calibration (Docs/Latency-and-Responsiveness.md): a short session on
// the note highway in two parts. Watch: notes cross the strike bar in silence and the player hits
// as each one does. Listen: a click plays with nothing on the highway and the player hits on each
// one. How late the hits land on the highway's clock in each part is the delay of the screen and
// of the speakers (each plus the same input delay, which cancels where the two are compared), and
// those are GameSettings::VideoLatency and AudioLatency.
class Calibration
{
    ME_SINGLETON_DEFINITION( Calibration );

public:
    // What LaunchPlayTrackEvent::TrackID carries to play the session's chart.
    static constexpr const char* kTrackId = "calibration";
    static constexpr int kBpm = 100;
    static constexpr double kBeatMs = 60000.0 / kBpm;
    // Each part: a few beats to find the pulse, which aren't measured, then the ones that are.
    static constexpr int kWarmUpBeats = 4;
    static constexpr int kMeasuredBeats = 16;
    static constexpr int kPartBeats = kWarmUpBeats + kMeasuredBeats;
    static constexpr int kWatchFirstBeat = 4;
    static constexpr int kListenFirstBeat = kWatchFirstBeat + kPartBeats + 4;
    static constexpr int kTotalBeats = kListenFirstBeat + kPartBeats + 1;
    // A hit counts for the nearest beat when it is within this of it.
    static constexpr double kReachMs = kBeatMs * 0.45;
    // Fewer measured hits than this is no result; hits further apart than kSteadyMs (on average,
    // from their median) are a shaky one.
    static constexpr int kMinSamples = 8;
    static constexpr double kSteadyMs = 35.0;

    enum class Part
    {
        Watch = 0,
        Listen = 1,
    };

    struct Result
    {
        int Samples = 0;
        double OffsetMs = 0.0;      // The median: positive when the hits came after the beat
        double SpreadMs = 0.0;      // Mean distance of the hits from it
        bool Valid() const { return Samples >= kMinSamples; }
        bool Steady() const { return Valid() && SpreadMs <= kSteadyMs; }
    };

    Calibration() = default;

    // Starts a session: the chart, the click track for the Listen part, and no hits yet. False
    // when the click track can't be written.
    bool Begin();
    bool IsActive() const { return m_active; }
    TrackData& Chart() { return m_chart; }

    // The session's chart: notes for the Watch part only. No audio.
    static TrackData BuildChart();
    // Which part a moment of the session belongs to.
    static Part PartAt( double inTimeMs );
    // When beat inBeat of a part falls (0 is its first warm-up beat).
    static double BeatTimeMs( Part inPart, int inBeat );

    // A hit at inTimeMs on the highway's clock (no latency settings applied). True when it was
    // within reach of one of the part's beats, warm-up or measured. One hit a beat: a later hit
    // for the same beat replaces the earlier (a resume plays a stretch again).
    bool AddTap( double inTimeMs );
    // How many of a part's measured beats have a hit.
    int Measured( Part inPart ) const;
    Result ResultOf( Part inPart ) const;
    static Result Summarise( std::vector<double> inOffsetsMs );

    // The setting a result stands for: its offset in whole ms, within what the settings allow.
    static int SettingFor( const Result& inResult );
    // The value and the remark the results screen shows for a result.
    static std::string ValueText( const Result& inResult );
    static std::string Remark( const Result& inResult );
    // Writes every valid result into the settings. False when neither part has one.
    bool Apply( GameSettings& ioSettings ) const;

private:
    struct Samples
    {
        std::array<double, kMeasuredBeats> OffsetMs{};
        std::array<bool, kMeasuredBeats> Has{};
    };

    TrackData m_chart;
    std::array<Samples, 2> m_samples{};
    bool m_active = false;
};
