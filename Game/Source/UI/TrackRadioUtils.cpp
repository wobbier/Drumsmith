#include "TrackRadioUtils.h"
#include "Global/TrackRadio.h"
#include "CoreGame/TrackList.h"
#include "UI/UIModelUtils.h"
#include <Cores/UI/RmlUiCore.h>
#include <Engine/Engine.h>
#include "Path.h"
#include <algorithm>
#include <cmath>

namespace
{
    // How long the widget stays on screen after a new track or a hover (the old page used 15 s).
    constexpr float kVisibleSeconds = 15.f;


    std::string FormatTime( float inMilliseconds )
    {
        const int seconds = std::isfinite( inMilliseconds ) ? static_cast<int>( std::max( 0.f, inMilliseconds ) / 1000.f ) : 0;
        return std::to_string( seconds / 60 ) + ":" + ( seconds % 60 < 10 ? "0" : "" ) + std::to_string( seconds % 60 );
    }
}


TrackRadioUtils::TrackRadioUtils( std::string inModel )
    : m_model( std::move( inModel ) )
{
}


void TrackRadioUtils::RegisterEvents( RmlUiCore& inUI )
{
    inUI.ModelEnsure( m_model );
    for( const char* event : { "skip", "seek", "radio_show" } )
    {
        inUI.ModelRegisterEvent( m_model, event );
    }
}


void TrackRadioUtils::OnUpdate( float dt )
{
    TrackRadio& radio = TrackRadio::GetInstance();
    radio.Update( dt );
    if( radio.CanPlayNextTrack() )
    {
        PlayNextRandomTrack();
    }
    if( radio.m_currentTrack != m_displayedTrack )
    {
        m_displayedTrack = radio.m_currentTrack;
        Show();
    }
    m_visibleTimer = std::max( 0.f, m_visibleTimer - dt );
    m_seekHold = std::max( 0.f, m_seekHold - dt );
    UpdateModel();
}


bool TrackRadioUtils::HandleEvent( const std::string& inEvent, const json& inArgs )
{
    if( inEvent == "skip" )
    {
        SkipTrack();
    }
    else if( inEvent == "seek" )
    {
        const double value = UIModel::ArgNumber( inArgs, 0, -1.0 );
        // Only a value the user moved counts; the slider also reports the one we set.
        if( value >= 0.0 && std::abs( value - m_pushedProgress ) >= 1.5 )
        {
            SeekToPosition( static_cast<float>( value / 1000.0 ) );
            m_pushedProgress = value;
            m_seekHold = 0.75f;
            Show();
        }
    }
    else if( inEvent == "radio_show" )
    {
        Show();
    }
    else
    {
        return false;
    }
    return true;
}


void TrackRadioUtils::PlayNextRandomTrack()
{
    TrackRadio& radio = TrackRadio::GetInstance();
    if( radio.IsPlaying() )
    {
        return;
    }

    auto& tracks = TrackDatabase::GetInstance().m_trackList.m_tracks;
    if( tracks.empty() )
    {
        return;
    }

    const int trackCount = static_cast<int>( tracks.size() );
    static int lastIndex = -1;
    int randomIndex;
    do
    {
        randomIndex = m_random( 0, trackCount - 1 );
    } while( trackCount > 1 && randomIndex == lastIndex );
    lastIndex = randomIndex;

    RadioArgs radioArgs;
    radioArgs.CurrentTrack = &tracks[randomIndex];
    radioArgs.UsePreviewMarker = false;
    radioArgs.CurrentTrackIndex = randomIndex;
    radio.Play( radioArgs );
}


void TrackRadioUtils::SeekToPosition( float inPosition )
{
    TrackRadio::GetInstance().Seek( std::clamp( inPosition, 0.0f, 1.0f ) );
    TrackRadio::GetInstance().Resume();
}


void TrackRadioUtils::SkipTrack()
{
    TrackRadio::GetInstance().Stop();
    PlayNextRandomTrack();
}


void TrackRadioUtils::PlayLatestTrack()
{
    auto& tracks = TrackDatabase::GetInstance().m_trackList.m_tracks;
    if( tracks.empty() )
    {
        return;
    }
    TrackRadio::GetInstance().Stop();
    RadioArgs radioArgs;
    radioArgs.CurrentTrack = &tracks.back();
    radioArgs.UsePreviewMarker = false;
    radioArgs.CurrentTrackIndex = static_cast<int>( tracks.size() ) - 1;
    TrackRadio::GetInstance().Play( radioArgs );
    Show();
}


void TrackRadioUtils::Show()
{
    m_visibleTimer = kVisibleSeconds;
}


std::string TrackRadioUtils::ArtSource( const TrackData& inTrack )
{
    if( !inTrack.m_albumArtPath.empty() )
    {
        // A track saved without an art file name points at its folder; a folder is no image.
        const Path art( inTrack.m_albumArtPath );
        if( art.Exists && art.IsFile )
        {
            return "/" + art.GetLocalPathString();
        }
    }
    return "img/track-bg.png";
}


void TrackRadioUtils::UpdateModel()
{
    RmlUiCore* ui = GetEngine().RmlUi;
    if( !ui )
    {
        return;
    }
    const TrackRadio& radio = TrackRadio::GetInstance();
    const TrackData* track = radio.m_currentTrack;
    const float duration = radio.GetTotalLength();
    const float position = radio.GetPositionMS();
    ui->ModelSetNumber( m_model, "radio_available", track != nullptr );
    ui->ModelSetNumber( m_model, "radio_visible", track != nullptr && m_visibleTimer > 0.f );
    ui->ModelSetString( m_model, "radio_title", track ? track->m_trackName : "" );
    ui->ModelSetString( m_model, "radio_artist", track ? track->m_artistName : "" );
    ui->ModelSetString( m_model, "radio_art", track ? ArtSource( *track ) : "img/track-bg.png" );
    ui->ModelSetString( m_model, "radio_position", FormatTime( position ) );
    ui->ModelSetString( m_model, "radio_duration", FormatTime( duration ) );
    if( m_seekHold <= 0.f )
    {
        m_pushedProgress = duration > 0.f ? std::round( std::clamp( position / duration, 0.f, 1.f ) * 1000.f ) : 0.0;
        ui->ModelSetNumber( m_model, "radio_progress", m_pushedProgress );
    }
}
