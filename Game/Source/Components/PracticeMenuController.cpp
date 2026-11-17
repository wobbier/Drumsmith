#include "Components/PracticeMenuController.h"

#include <Cores/UI/RmlUiCore.h>
#include <Engine/Engine.h>
#include <Engine/Input.h>
#include <Events/SceneEvents.h>
#include "Config/GameSettings.h"
#include "CoreGame/Practice.h"
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
    for( const char* event : { "select", "start", "bars", "tempo" } )
    {
        ui->ModelRegisterEvent( kModel, event );
    }
    const auto& lessons = Practice::GetInstance().Lessons();
    ui->ModelSetNumber( kModel, "selected", -1 );
    ui->ModelSetNumber( kModel, "bpm", 80 );
    ui->ModelSetNumber( kModel, "bars", m_bars );
    ui->ModelSetNumber( kModel, "lesson_count", static_cast<int>( lessons.size() ) );
    for( const char* key : { "detail_name", "detail_category", "detail_description", "detail_pattern", "detail_feel", "status" } )
    {
        ui->ModelSetString( kModel, key, "" );
    }
    ui->ModelSetListCount( kModel, "lanes", 0 );
    ui->ModelSetListCount( kModel, "lessons", static_cast<int>( lessons.size() ) );
    std::string previousCategory;
    for( int i = 0; i < static_cast<int>( lessons.size() ); ++i )
    {
        ui->ModelSetItemNumber( kModel, "lessons", i, "index", i );
        ui->ModelSetItemString( kModel, "lessons", i, "name", lessons[i].Name );
        ui->ModelSetItemString( kModel, "lessons", i, "category", lessons[i].Category != previousCategory ? lessons[i].Category : "" );
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
    ui->ModelSetListCount( kModel, "lanes", static_cast<int>( lesson.Lanes.size() ) );
    for( int i = 0; i < static_cast<int>( lesson.Lanes.size() ); ++i )
    {
        const PadId pad = PadUtils::GetNewPadId( lesson.Lanes[i].first );
        ui->ModelSetItemString( kModel, "lanes", i, "name", pad >= 0 && pad < PadId::COUNT ? PadUtils::GetPadName( pad ) : lesson.Lanes[i].first.c_str() );
        ui->ModelSetItemString( kModel, "lanes", i, "steps", lesson.Lanes[i].second );
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
    }
}
