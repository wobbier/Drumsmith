#include "Components/PracticeMenuController.h"

#include <Cores/UI/RmlUiCore.h>
#include <Engine/Engine.h>
#include <Engine/Input.h>
#include <Events/SceneEvents.h>
#include "Config/GameSettings.h"
#include "Core/CommandLine.h"
#include "Config/PlayerProfile.h"
#include "CoreGame/LessonPatterns.h"
#include "CoreGame/Progression.h"
#include "CoreGame/Practice.h"
#include "UI/TrackRadioUtils.h"
#include "Events/GameEvents.h"
#include "Global/TrackRadio.h"
#include "UI/UIModelUtils.h"
#include <algorithm>
#include <cmath>

namespace
{
    constexpr const char* kModel = "practice_menu";


    // What the page shows for a lesson's pattern: a rudiment's sticking, or a groove's lanes.
    std::string PatternText( const PracticeLesson& inLesson )
    {
        if( !inLesson.Sticking.empty() )
        {
            // The accent and flam marks as a drummer writes them; RmlUi would read ">" as markup.
            std::string text;
            for( char c : inLesson.Sticking )
            {
                text += c == '>' ? std::string( "'" ) : c == '^' ? std::string( "f" ) : std::string( 1, c );
            }
            return text;
        }
        return {};
    }
}


PracticeMenuController::PracticeMenuController()
    : Component( "PracticeMenuController" )
{
}


void PracticeMenuController::PopulateModel()
{
    RmlUiCore* ui = GetEngine().RmlUi;
    if( !ui )
    {
        return;
    }
    ui->ModelEnsure( kModel );
    for( const char* event : { "select", "start", "bars", "tempo", "play_song" } )
    {
        ui->ModelRegisterEvent( kModel, event );
    }
    const auto& lessons = Practice::GetInstance().Lessons();
    ui->ModelSetNumber( kModel, "selected", -1 );
    ui->ModelSetNumber( kModel, "bpm", 80 );
    ui->ModelSetNumber( kModel, "bars", m_bars );
    ui->ModelSetNumber( kModel, "lesson_count", static_cast<int>( lessons.size() ) );
    for( const char* key : { "detail_name", "detail_category", "detail_description", "detail_pattern", "detail_feel", "detail_progress", "status", "songs_heading",
        "songs_state" } )
    {
        ui->ModelSetString( kModel, key, "" );
    }
    ui->ModelSetNumber( kModel, "detail_locked", 0 );
    ui->ModelSetNumber( kModel, "detail_passed", 0 );
    const Progression& progression = Progression::GetInstance();
    const PlayerProfile& profile = PlayerProfile::GetInstance();
    ui->ModelSetListCount( kModel, "lanes", 0 );
    ui->ModelSetListCount( kModel, "songs", 0 );
    // The library's patterns, read on a worker thread the first time this session.
    LessonPatternIndex::GetInstance().Request();
    ui->ModelSetListCount( kModel, "lessons", static_cast<int>( lessons.size() ) );
    std::string previousCategory;
    for( int i = 0; i < static_cast<int>( lessons.size() ); ++i )
    {
        ui->ModelSetItemNumber( kModel, "lessons", i, "index", i );
        ui->ModelSetItemString( kModel, "lessons", i, "name", lessons[i].Name );
        ui->ModelSetItemString( kModel, "lessons", i, "category", lessons[i].Category != previousCategory ? lessons[i].Category : "" );
        ui->ModelSetItemString( kModel, "lessons", i, "state", profile.LessonPassed( lessons[i].Id ) ? "PASSED" : !progression.LessonOpen( lessons[i].Id, profile ) ? "LOCKED" : "" );
        previousCategory = lessons[i].Category;
    }
    m_modelReady = true;
    // Back from a lesson: the one just played is still the one selected.
    const int last = Practice::GetInstance().LessonIndex();
    SelectLesson( last >= 0 && last < static_cast<int>( lessons.size() ) ? last : 0 );
}


void PracticeMenuController::SelectLesson( int inLesson )
{
    RmlUiCore* ui = GetEngine().RmlUi;
    const auto& lessons = Practice::GetInstance().Lessons();
    if( !ui || inLesson < 0 || inLesson >= static_cast<int>( lessons.size() ) )
    {
        return;
    }
    const PracticeLesson& lesson = lessons[inLesson];
    m_selected = inLesson;
    const auto& tempos = GameSettings::GetInstance().PracticeTempos;
    const auto remembered = tempos.find( lesson.Id );
    const int bpm = std::clamp( remembered != tempos.end() ? remembered->second : lesson.Bpm, Practice::kMinBpm, Practice::kMaxBpm );
    static const char* kFeel[] = { "", "quarter notes", "eighth notes", "triplets", "sixteenth notes" };
    ui->ModelSetNumber( kModel, "selected", inLesson );
    ui->ModelSetNumber( kModel, "bpm", bpm );
    ui->ModelSetString( kModel, "detail_name", lesson.Name );
    ui->ModelSetString( kModel, "detail_category", lesson.Category );
    ui->ModelSetString( kModel, "detail_description", lesson.Description );
    ui->ModelSetString( kModel, "detail_pattern", PatternText( lesson ) );
    ui->ModelSetString( kModel, "detail_feel", lesson.StepsPerBeat >= 1 && lesson.StepsPerBeat <= 4 ? kFeel[lesson.StepsPerBeat] : "" );
    ui->ModelSetString( kModel, "status", "" );
    // The ladder: passed, what passing takes, or what opens it.
    const Progression& progression = Progression::GetInstance();
    const PlayerProfile& profile = PlayerProfile::GetInstance();
    const PlayerProfile::LessonRecord* record = profile.FindLesson( lesson.Id );
    const bool locked = !progression.LessonOpen( lesson.Id, profile );
    std::string progress;
    if( record && record->Passed )
    {
        progress = "Passed. Fastest clean tempo: " + std::to_string( record->BestBpm ) + " BPM";
    }
    else if( locked )
    {
        progress = "Locked.";
        if( const ProgressionLessonStep* step = progression.StepOf( lesson.Id ) )
        {
            for( const std::string& before : step->Requires.LessonSteps )
            {
                const auto& steps = progression.LessonSteps();
                const auto it = std::find_if( steps.begin(), steps.end(), [&before]( const ProgressionLessonStep& inStep ) { return inStep.Id == before; } );
                progress += " Pass every lesson in " + ( it != steps.end() ? it->Name : before ) + " to open " + step->Name + ".";
            }
        }
    }
    else
    {
        progress = "To pass: " + std::to_string( static_cast<int>( lesson.PassAccuracy ) ) + "% at " + std::to_string( lesson.PassTempo() ) + " BPM or faster.";
        if( record && record->Plays > 0 )
        {
            progress += " Your best: " + std::to_string( static_cast<int>( record->BestAccuracy ) ) + "%" + ( record->BestBpm > 0 ? " (clean at " + std::to_string( record->BestBpm ) + " BPM)" : std::string() ) + ".";
        }
    }
    ui->ModelSetString( kModel, "detail_progress", progress );
    ui->ModelSetNumber( kModel, "detail_locked", locked ? 1 : 0 );
    ui->ModelSetNumber( kModel, "detail_passed", record && record->Passed ? 1 : 0 );
    ui->ModelSetListCount( kModel, "lanes", static_cast<int>( lesson.Lanes.size() ) );
    for( int i = 0; i < static_cast<int>( lesson.Lanes.size() ); ++i )
    {
        const PadId pad = PadUtils::GetNewPadId( lesson.Lanes[i].first );
        ui->ModelSetItemString( kModel, "lanes", i, "name", pad >= 0 && pad < PadId::COUNT ? PadUtils::GetPadName( pad ) : lesson.Lanes[i].first.c_str() );
        ui->ModelSetItemString( kModel, "lanes", i, "steps", lesson.Lanes[i].second );
    }
    FillSongs();
}


void PracticeMenuController::FillSongs()
{
    RmlUiCore* ui = GetEngine().RmlUi;
    const auto& lessons = Practice::GetInstance().Lessons();
    if( !ui || m_selected < 0 || m_selected >= static_cast<int>( lessons.size() ) )
    {
        return;
    }
    const PracticeLesson& lesson = lessons[m_selected];
    const LessonPatternIndex& index = LessonPatternIndex::GetInstance();
    const bool rudiment = lesson.Lanes.empty();
    ui->ModelSetString( kModel, "songs_heading", rudiment ? "Songs with its rhythm" : "Songs with this groove" );
    std::vector<LessonPatternIndex::Use> uses;
    if( index.Ready() )
    {
        uses = index.SongsFor( lesson.Id );
    }
    if( uses.size() > 6 )
    {
        uses.resize( 6 );
    }
    const bool locked = !Progression::GetInstance().LessonOpen( lesson.Id, PlayerProfile::GetInstance() );
    const char* state = !index.Ready() ? "Looking through your songs..."
        : !uses.empty() ? ( rudiment ? "Found by rhythm: a chart says which drum, not which hand, so try the sticking over these."
            : locked ? "Play one of these and the lesson opens." : "" )
        : lesson.Sticking.find( '^' ) != std::string::npos ? "Flams aren't in the charts, so no song shows them."
        : "None of your songs has it yet.";
    ui->ModelSetString( kModel, "songs_state", state );
    ui->ModelSetListCount( kModel, "songs", static_cast<int>( uses.size() ) );
    for( int i = 0; i < static_cast<int>( uses.size() ); ++i )
    {
        const LessonPatternIndex::Use& use = uses[i];
        const int seconds = static_cast<int>( use.Section.Start );
        char detail[96];
        std::snprintf( detail, sizeof( detail ), "%d bar%s, from %d:%02d", use.TotalBars, use.TotalBars == 1 ? "" : "s", seconds / 60, seconds % 60 );
        ui->ModelSetItemNumber( kModel, "songs", i, "track", use.Track );
        ui->ModelSetItemString( kModel, "songs", i, "name", use.Name );
        ui->ModelSetItemString( kModel, "songs", i, "detail", detail );
    }
}


void PracticeMenuController::StartLesson()
{
    RmlUiCore* ui = GetEngine().RmlUi;
    const auto& lessons = Practice::GetInstance().Lessons();
    if( !ui || m_selected < 0 || m_selected >= static_cast<int>( lessons.size() ) )
    {
        return;
    }
    if( !Progression::GetInstance().LessonOpen( lessons[m_selected].Id, PlayerProfile::GetInstance() ) )
    {
        ui->ModelSetString( kModel, "status", "This lesson isn't open yet." );
        return;
    }
    const int bpm = std::clamp( static_cast<int>( std::lround( ui->ModelGetNumber( kModel, "bpm" ) ) ), Practice::kMinBpm, Practice::kMaxBpm );
    if( !Practice::GetInstance().Begin( m_selected, bpm, m_bars ) )
    {
        ui->ModelSetString( kModel, "status", "Couldn't start the lesson: its click track wasn't written" );
        return;
    }
    // The tempo is where this lesson starts next time.
    GameSettings& settings = GameSettings::GetInstance();
    if( settings.PracticeTempos[lessons[m_selected].Id] != bpm )
    {
        settings.PracticeTempos[lessons[m_selected].Id] = bpm;
        settings.Save();
    }
    TrackRadio::GetInstance().Stop();
    LoadSceneEvent load;
    load.Level = "Assets/Example.lvl";
    load.Callback = []()
    {
        LaunchPlayTrackEvent play;
        play.TrackID = Practice::kTrackId;
        play.TrackIndex = -1;
        play.Fire();
    };
    load.Queue();
}


void PracticeMenuController::Update( float inDeltaTime )
{
    if( !m_modelReady )
    {
        PopulateModel();
    }
    RmlUiCore* ui = GetEngine().RmlUi;
    if( !ui )
    {
        return;
    }
    if( GetEngine().GetInput().WasKeyPressed( KeyCode::Escape ) )
    {
        LoadSceneEvent load;
        load.Level = "Assets/MainMenu.lvl";
        load.Queue();
        return;
    }
    // --practice-select N: lesson N chosen a second in, after the page's own first focus (captures).
    static float selectIn = 1.f;
    if( selectIn > 0.f && ( selectIn -= inDeltaTime ) <= 0.f )
    {
        const int select = CommandLine::GetInt( "--practice-select", -1 );
        if( select >= 0 && select < static_cast<int>( Practice::GetInstance().Lessons().size() ) )
        {
            SelectLesson( select );
        }
    }
    // The library's patterns arrive: the chosen lesson's songs, and any lesson a played song opens.
    if( LessonPatternIndex::GetInstance().Poll() )
    {
        PlayerProfile& profile = PlayerProfile::GetInstance();
        if( !Progression::GetInstance().Evaluate( profile ).empty() )
        {
            profile.Save();
            m_modelReady = false;
            PopulateModel();
            if( m_selected >= 0 )
            {
                const int selected = m_selected;
                m_selected = -1;
                SelectLesson( selected );
            }
        }
        FillSongs();
    }
    for( std::string event; !( event = ui->ModelPollEvent( kModel ) ).empty(); )
    {
        const json args = UIModel::LastEventArgs( *ui, kModel );
        const int value = static_cast<int>( UIModel::ArgNumber( args, 0, -1.0 ) );
        if( event == "select" )
        {
            if( value != m_selected )
            {
                SelectLesson( value );
            }
        }
        else if( event == "bars" && value > 0 )
        {
            m_bars = std::clamp( value, 4, 64 );
            ui->ModelSetNumber( kModel, "bars", m_bars );
        }
        else if( event == "tempo" )
        {
            // The -5 / +5 buttons beside the slider.
            const int bpm = static_cast<int>( std::lround( ui->ModelGetNumber( kModel, "bpm" ) ) ) + value;
            ui->ModelSetNumber( kModel, "bpm", std::clamp( bpm, Practice::kMinBpm, Practice::kMaxBpm ) );
        }
        else if( event == "start" )
        {
            StartLesson();
            return;
        }
        else if( event == "play_song" && value >= 0 )
        {
            TrackRadioUtils::LaunchTrack( value );
            return;
        }
    }
}
