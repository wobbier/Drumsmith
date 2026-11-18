#include "CoreGame/LessonPatterns.h"
#include "CLog.h"
#include "Config/PlayerProfile.h"
#include "CoreGame/Practice.h"
#include "CoreGame/Progression.h"
#include "CoreGame/TrackList.h"
#include "JSON.h"
#include "Path.h"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <set>
#include <unordered_map>
#include <unordered_set>

namespace
{
    constexpr float kTolerance = 0.22f;     // of a step: further off the grid than this and a note isn't on it

    const std::unordered_set<std::string>& Hands()
    {
        static const std::unordered_set<std::string> hands = { "snare1", "tom1", "tom2", "tom3" };
        return hands;
    }


    const std::unordered_set<std::string>& Cymbals()
    {
        static const std::unordered_set<std::string> cymbals = { "closed_hh", "open_hh", "ride1", "crash1", "crash2" };
        return cymbals;
    }


    // A lane's or a sticking's steps: true for a stroke. Spaces are for reading; ^ (a flam) and >
    // (an accent) mark the stroke after them.
    std::vector<bool> StepsOf( const std::string& inText )
    {
        std::vector<bool> steps;
        for( char c : inText )
        {
            if( c == ' ' || c == '^' || c == '>' )
            {
                continue;
            }
            steps.push_back( c != '-' );
        }
        return steps;
    }


    // A chart's notes on its beat grid at a number of steps a beat.
    class Grid
    {
    public:
        Grid( const std::vector<LessonPatterns::Beat>& inBeats, const std::vector<LessonPatterns::Note>& inNotes, int inStepsPerBeat )
            : m_steps( std::max( 1, inStepsPerBeat ) )
        {
            for( size_t i = 0; i < inBeats.size(); ++i )
            {
                m_times.push_back( inBeats[i].Time );
                if( inBeats[i].Downbeat )
                {
                    m_downbeats.push_back( static_cast<int>( i ) );
                }
            }
            for( const LessonPatterns::Note& note : inNotes )
            {
                int beat = static_cast<int>( std::upper_bound( m_times.begin(), m_times.end(), note.Time ) - m_times.begin() ) - 1;
                if( beat < 0 || beat + 1 >= static_cast<int>( m_times.size() ) )
                {
                    continue;
                }
                const float span = m_times[beat + 1] - m_times[beat];
                if( span <= 0.f )
                {
                    continue;
                }
                const float position = ( note.Time - m_times[beat] ) / span * static_cast<float>( m_steps );
                int step = static_cast<int>( std::lround( position ) );
                if( std::abs( position - static_cast<float>( step ) ) > kTolerance )
                {
                    m_off.insert( beat );
                    continue;
                }
                if( step == m_steps )
                {
                    ++beat;
                    step = 0;
                }
                m_cells[Key( beat, step )].insert( note.Lane );
            }
        }

        // Each bar of inBeatsPerBar beats: its first beat.
        std::vector<int> Bars( int inBeatsPerBar ) const
        {
            std::vector<int> bars;
            for( size_t i = 0; i + 1 < m_downbeats.size(); ++i )
            {
                if( m_downbeats[i + 1] - m_downbeats[i] == inBeatsPerBar )
                {
                    bars.push_back( m_downbeats[i] );
                }
            }
            return bars;
        }

        const std::set<std::string>& Cell( int inFirstBeat, int inStep ) const
        {
            static const std::set<std::string> kEmpty;
            const auto it = m_cells.find( Key( inFirstBeat + inStep / m_steps, inStep % m_steps ) );
            return it == m_cells.end() ? kEmpty : it->second;
        }

        // No note off the grid in these beats.
        bool Clean( int inFirstBeat, int inBeats ) const
        {
            for( int k = 0; k < inBeats; ++k )
            {
                if( m_off.count( inFirstBeat + k ) > 0 )
                {
                    return false;
                }
            }
            return true;
        }

        int Steps() const { return m_steps; }
        float TimeOf( int inBeat ) const { return inBeat >= 0 && inBeat < static_cast<int>( m_times.size() ) ? m_times[inBeat] : 0.f; }

    private:
        static long long Key( int inBeat, int inStep ) { return static_cast<long long>( inBeat ) * 16 + inStep; }

        int m_steps = 4;
        std::vector<float> m_times;
        std::vector<int> m_downbeats;
        std::unordered_map<long long, std::set<std::string>> m_cells;
        std::unordered_set<int> m_off;
    };


    // A groove's bars: on its lanes plus the kick and snare, exactly its strokes.
    std::vector<int> GrooveBars( const Grid& inGrid, const PracticeLesson& inLesson, int& outBars )
    {
        std::vector<std::pair<std::string, std::vector<bool>>> lanes;
        size_t length = 0;
        for( const auto& [lane, text] : inLesson.Lanes )
        {
            lanes.emplace_back( lane, StepsOf( text ) );
            length = std::max( length, lanes.back().second.size() );
        }
        const int barSteps = inLesson.BeatsPerBar * inGrid.Steps();
        outBars = std::max( 1, static_cast<int>( ( length + barSteps - 1 ) / std::max( 1, barSteps ) ) );
        std::vector<std::set<std::string>> want( static_cast<size_t>( outBars * barSteps ) );
        for( size_t k = 0; k < want.size(); ++k )
        {
            for( const auto& [lane, steps] : lanes )
            {
                if( !steps.empty() && steps[k % steps.size()] )
                {
                    want[k].insert( lane );
                }
            }
        }
        std::set<std::string> watched = { "snare1", "bass1" };
        for( const auto& lane : lanes )
        {
            watched.insert( lane.first );
        }
        std::vector<int> hits;
        for( int first : inGrid.Bars( inLesson.BeatsPerBar ) )
        {
            if( !inGrid.Clean( first, inLesson.BeatsPerBar * outBars ) )
            {
                continue;
            }
            bool match = true;
            for( size_t k = 0; k < want.size() && match; ++k )
            {
                std::set<std::string> got;
                for( const std::string& lane : inGrid.Cell( first, static_cast<int>( k ) ) )
                {
                    if( watched.count( lane ) > 0 ) got.insert( lane );
                }
                match = got == want[k];
            }
            if( match )
            {
                hits.push_back( first );
            }
        }
        return hits;
    }


    // A rudiment's bars, by rhythm: the hand drums on exactly the sticking's strokes, no cymbal
    // where it rests.
    std::vector<int> RudimentBars( const Grid& inGrid, const PracticeLesson& inLesson )
    {
        const std::vector<bool> strokes = StepsOf( inLesson.Sticking );
        std::vector<int> hits;
        if( strokes.empty() || inLesson.Sticking.find( '^' ) != std::string::npos )
        {
            return hits;
        }
        const int barSteps = inLesson.BeatsPerBar * inGrid.Steps();
        for( int first : inGrid.Bars( inLesson.BeatsPerBar ) )
        {
            if( !inGrid.Clean( first, inLesson.BeatsPerBar ) )
            {
                continue;
            }
            bool match = true;
            for( int k = 0; k < barSteps && match; ++k )
            {
                const bool want = strokes[static_cast<size_t>( k ) % strokes.size()];
                bool hand = false;
                bool cymbal = false;
                for( const std::string& lane : inGrid.Cell( first, k ) )
                {
                    hand = hand || Hands().count( lane ) > 0;
                    cymbal = cymbal || Cymbals().count( lane ) > 0;
                }
                match = hand == want && ( want || !cymbal );
            }
            if( match )
            {
                hits.push_back( first );
            }
        }
        return hits;
    }
}


std::vector<PatternSection> LessonPatterns::Find( const std::vector<PracticeLesson>& inLessons, const std::vector<Beat>& inBeats, const std::vector<Note>& inNotes )
{
    std::vector<PatternSection> found;
    if( inBeats.size() < 8 || inNotes.empty() )
    {
        return found;
    }
    std::map<int, Grid> grids;
    for( const PracticeLesson& lesson : inLessons )
    {
        const int steps = std::clamp( lesson.StepsPerBeat, 1, 8 );
        auto grid = grids.find( steps );
        if( grid == grids.end() )
        {
            grid = grids.emplace( steps, Grid( inBeats, inNotes, steps ) ).first;
        }
        int bars = 1;
        const bool groove = !lesson.Lanes.empty();
        const std::vector<int> hits = groove ? GrooveBars( grid->second, lesson, bars ) : RudimentBars( grid->second, lesson );
        // Runs of bars in a row: two at least for a one-bar pattern.
        const int need = bars == 1 ? 2 : 1;
        const int stride = lesson.BeatsPerBar * bars;
        std::vector<int> run;
        const auto close = [&]() {
            if( static_cast<int>( run.size() ) >= need )
            {
                found.push_back( { lesson.Id, grid->second.TimeOf( run.front() ), static_cast<int>( run.size() ) * bars, !groove } );
            }
            run.clear();
        };
        for( int first : hits )
        {
            if( !run.empty() && first != run.back() + stride )
            {
                close();
            }
            run.push_back( first );
        }
        close();
    }
    return found;
}


bool LessonPatterns::ReadChart( const std::string& inFile, std::vector<Beat>& outBeats, std::vector<Note>& outNotes )
{
    outBeats.clear();
    outNotes.clear();
    std::ifstream in( inFile, std::ios::binary );
    if( !in )
    {
        return false;
    }
    const json root = json::parse( in, nullptr, false );
    if( !root.is_object() )
    {
        return false;
    }
    if( root.contains( "Beats" ) && root["Beats"].is_array() )
    {
        for( const json& beat : root["Beats"] )
        {
            if( beat.is_array() && beat.size() >= 2 && beat[0].is_number() )
            {
                outBeats.push_back( { beat[0].get<float>(), beat[1].is_number() && beat[1].get<int>() != 0 } );
            }
        }
    }
    if( root.contains( "Notes" ) && root["Notes"].is_array() )
    {
        for( const json& note : root["Notes"] )
        {
            if( note.is_object() && note.contains( "TriggerTime" ) && note["TriggerTime"].is_number() )
            {
                outNotes.push_back( { note["TriggerTime"].get<float>(), note.value( "NoteName", std::string() ) } );
            }
        }
    }
    return !outBeats.empty();
}


LessonPatternIndex::~LessonPatternIndex()
{
    m_stop = true;
    if( m_worker.joinable() )
    {
        m_worker.join();
    }
}


void LessonPatternIndex::Request()
{
    if( m_started )
    {
        return;
    }
    m_started = true;
    // What the worker needs, copied here: the database can change under it (a download, a removal).
    struct Song
    {
        std::string Key;
        std::string File;
    };
    std::vector<Song> songs;
    for( const TrackData& track : TrackDatabase::GetInstance().m_trackList.m_tracks )
    {
        const std::string key = TrackDatabase::FavoriteKey( track );
        if( !key.empty() && !track.GetDirectory().empty() )
        {
            songs.push_back( { key, Path( track.GetDirectory() + "/NoteData.txt" ).FullPath } );
        }
    }
    std::vector<PracticeLesson> lessons = Practice::GetInstance().Lessons();
    m_worker = std::thread( [this, songs = std::move( songs ), lessons = std::move( lessons )]() {
        std::vector<LessonPatterns::Beat> beats;
        std::vector<LessonPatterns::Note> notes;
        for( const Song& song : songs )
        {
            if( m_stop )
            {
                break;
            }
            if( !LessonPatterns::ReadChart( song.File, beats, notes ) )
            {
                continue;
            }
            std::vector<PatternSection> found = LessonPatterns::Find( lessons, beats, notes );
            if( !found.empty() )
            {
                m_found[song.Key] = std::move( found );
            }
        }
        m_done = true;
    } );
}


bool LessonPatternIndex::Poll()
{
    if( !m_started || m_ready || !m_done )
    {
        return false;
    }
    if( m_worker.joinable() )
    {
        m_worker.join();
    }
    m_songs = std::move( m_found );
    m_ready = true;
    // The grooves each song plays open those lessons for a player who has played the song
    // (Progression::Evaluate). Rudiments, found by rhythm alone, don't.
    Progression& progression = Progression::GetInstance();
    progression.SongLessons.clear();
    const auto& lessons = Practice::GetInstance().Lessons();
    const std::vector<TrackData>& tracks = TrackDatabase::GetInstance().m_trackList.m_tracks;
    int grooves = 0;
    for( const auto& [song, sections] : m_songs )
    {
        const auto track = std::find_if( tracks.begin(), tracks.end(), [&song]( const TrackData& inTrack ) { return TrackDatabase::FavoriteKey( inTrack ) == song; } );
        const std::string songName = track != tracks.end() && !track->m_trackName.empty() ? track->m_trackName : song;
        for( const PatternSection& section : sections )
        {
            if( section.RhythmOnly || section.Bars < 2 )
            {
                continue;
            }
            auto& uses = progression.SongLessons[song];
            if( std::none_of( uses.begin(), uses.end(), [&section]( const ProgressionSongLesson& inUse ) { return inUse.Lesson == section.Lesson; } ) )
            {
                const auto lesson = std::find_if( lessons.begin(), lessons.end(), [&section]( const PracticeLesson& inLesson ) { return inLesson.Id == section.Lesson; } );
                uses.push_back( { section.Lesson, lesson != lessons.end() ? lesson->Name : section.Lesson, songName } );
                ++grooves;
            }
        }
    }
    INFO_FMT( "[Patterns]", "%d songs play a lesson; %d song-groove pairs can open lessons", static_cast<int>( m_songs.size() ), grooves );
    return true;
}


std::vector<LessonPatternIndex::Use> LessonPatternIndex::SongsFor( const std::string& inLesson ) const
{
    std::vector<Use> uses;
    const std::vector<TrackData>& tracks = TrackDatabase::GetInstance().m_trackList.m_tracks;
    for( const auto& [song, sections] : m_songs )
    {
        Use use;
        for( const PatternSection& section : sections )
        {
            if( section.Lesson != inLesson )
            {
                continue;
            }
            use.TotalBars += section.Bars;
            if( section.Bars > use.Section.Bars )
            {
                use.Section = section;
            }
        }
        if( use.TotalBars == 0 )
        {
            continue;
        }
        use.Song = song;
        for( size_t i = 0; i < tracks.size(); ++i )
        {
            if( TrackDatabase::FavoriteKey( tracks[i] ) == song )
            {
                use.Track = static_cast<int>( i );
                use.Name = tracks[i].m_trackName + ( tracks[i].m_artistName.empty() ? std::string() : " - " + tracks[i].m_artistName );
                break;
            }
        }
        if( use.Track >= 0 )
        {
            uses.push_back( use );
        }
    }
    std::sort( uses.begin(), uses.end(), []( const Use& a, const Use& b ) { return a.TotalBars > b.TotalBars; } );
    return uses;
}
