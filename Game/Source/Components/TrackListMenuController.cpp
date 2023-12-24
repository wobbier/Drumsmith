#include <Components/TrackListMenuController.h>

#include <Events/SceneEvents.h>
#include "CoreGame/TrackList.h"
#include "Events/GameEvents.h"
#include "Global/TrackRadio.h"

TrackListMenuController::TrackListMenuController()
    : BasicUIView( "TrackListMenuController" )
{
    FilePath = Path( "Assets/UI/SongList.html" );
    m_playAudioCallback = [this]( SharedPtr<AudioSource> playedAudioSource )
    {
        if( m_currentTrack != playedAudioSource )
        {
            if( m_currentTrack )
            {
                m_currentTrack->Stop( true );
            }
            m_currentTrack = playedAudioSource;
        }
        else
        {
            if( m_currentTrack && m_currentTrack->IsPlaying() )
            {
                m_currentTrack->Stop( true );
            }
        }
    };
}

void TrackListMenuController::OnUILoad( ultralight::JSObject& GlobalWindow, ultralight::View* Caller )
{
    BasicUIView::OnUILoad( GlobalWindow, Caller );

    GlobalWindow["SelectTrackToPlay"] = BindJSCallback( &TrackListMenuController::SelectTrackToPlay );
    GlobalWindow["PlayTrackPreview"] = BindJSCallback( &TrackListMenuController::PlayTrackPreview );
    ExecuteScript( "ClearTrackList();" );

    auto& trackList = TrackDatabase::GetInstance().m_trackList.m_tracks;
    for( int i = 0; i < trackList.size(); ++i )
    {
        auto& trackData = trackList[i];
        Path dlcTest = Path( trackData.m_albumArtPath );
        std::string songImage = dlcTest.GetLocalPathString();
        json uiTrackData;
        uiTrackData["TrackName"] = trackData.m_trackName;
        uiTrackData["ArtistName"] = trackData.m_artistName;
        uiTrackData["AlbumArt"] = songImage;
        uiTrackData["TrackSource"] = trackData.m_trackSourcePath;
        uiTrackData["NoteCount"] = trackData.m_noteData.size();
        uiTrackData["TrackIndex"] = i;
        ExecuteScript( "AddTrack(" + uiTrackData.dump() + "); " );
    }
}

void TrackListMenuController::SelectTrackToPlay( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    ultralight::String path = args[0].ToString();

    LaunchPlayTrackEvent evt;
    evt.TrackID = std::string( path.utf8().data() );
    evt.Fire();
}

void TrackListMenuController::PlayTrackPreview( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    if( args.empty() || !args[0].IsString() )
    {
        BRUH( "PlaySound(string) argument mismatch." );
        return;
    }

    int str = args[0].ToInteger();

    auto& trackList = TrackDatabase::GetInstance().m_trackList.m_tracks;
    if (str >= trackList.size())
    {
        return;
    }
    TrackRadio::GetInstance().Play( &trackList[str] );
}
