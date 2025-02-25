#include "TrackRadioUtils.h"
#include "Global/TrackRadio.h"
#include "CoreGame/TrackList.h"
#include "Path.h"


TrackRadioUtils::TrackRadioUtils( BasicUIView& inOwningView )
    : m_owner( inOwningView )
{

}


void TrackRadioUtils::OnUILoad( ultralight::JSObject& GlobalWindow, ultralight::View* Caller )
{
    GlobalWindow["SkipTrack"] = BindJSCallback( &TrackRadioUtils::SkipTrack );
    GlobalWindow["SeekToPosition"] = BindJSCallback( &TrackRadioUtils::SeekToPosition );
    GlobalWindow["GetCurrentTrackDuration"] = BindJSCallbackWithRetval( &TrackRadioUtils::GetCurrentTrackDuration );
    GlobalWindow["GetCurrentTrackPosition"] = BindJSCallbackWithRetval( &TrackRadioUtils::GetCurrentTrackPosition );
}

void TrackRadioUtils::OnUpdate( float dt )
{
    TrackRadio::GetInstance().Update( dt );
    if( TrackRadio::GetInstance().CanPlayNextTrack() )
    {
        PlayNextRandomTrack();
    }
}


void TrackRadioUtils::PlayNextRandomTrack()
{
    TrackData* randomElement = TrackRadio::GetInstance().m_currentTrack;

    if( !TrackRadio::GetInstance().IsPlaying() )
    {
        auto& trackExample = TrackDatabase::GetInstance().m_trackList.m_tracks;
        if( trackExample.empty() )
        {
            return;
        }

        int trackCount = trackExample.size();
        static int lastIndex = -1;

        int randomIndex;
        do
        {
            randomIndex = m_random( 0, trackCount - 1 );
        } while( trackCount > 1 && randomIndex == lastIndex );

        lastIndex = randomIndex;
        randomElement = &trackExample[randomIndex];

        RadioArgs radioArgs;
        radioArgs.CurrentTrack = randomElement;
        radioArgs.UsePreviewMarker = false;
        radioArgs.CurrentTrackIndex = randomIndex;
        TrackRadio::GetInstance().Play( radioArgs );
    }

    if( randomElement )
    {
        UpdateTrackDisplay( randomElement );
    }
}


ultralight::JSValue TrackRadioUtils::GetCurrentTrackDuration( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    return ultralight::JSValue( TrackRadio::GetInstance().GetTotalLength() );
}


ultralight::JSValue TrackRadioUtils::GetCurrentTrackPosition( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    return ultralight::JSValue( TrackRadio::GetInstance().GetPositionMS() );
}


void TrackRadioUtils::SeekToPosition( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    ME_ASSERT_MSG( args[0].IsNumber(), "Seek Position is not a number ;-;" );
    double seekPos = args[0].ToNumber();
    ME_ASSERT_MSG( seekPos >= 0 && seekPos <= 1.0, "Seek Position is not a percent ;-;" );
    TrackRadio::GetInstance().Seek( (float)seekPos );
    TrackRadio::GetInstance().Resume();
}


void TrackRadioUtils::SkipTrack( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    TrackRadio::GetInstance().Stop();
    PlayNextRandomTrack();
}


void TrackRadioUtils::PlayLatestTrack()
{
    RadioArgs radioArgs;
    radioArgs.CurrentTrack = &TrackDatabase::GetInstance().m_trackList.m_tracks.back();
    radioArgs.UsePreviewMarker = false;
    radioArgs.CurrentTrackIndex = TrackDatabase::GetInstance().m_trackList.m_tracks.size() - 1;
    TrackRadio::GetInstance().Play( radioArgs );

    UpdateTrackDisplay( radioArgs.CurrentTrack );
}


void TrackRadioUtils::UpdateTrackDisplay( TrackData* inTrackData )
{
    Path dlcTest = Path( inTrackData->m_albumArtPath );
    std::string songImage = dlcTest.GetLocalPathString();
    json trackData;
    trackData["TrackName"] = inTrackData->m_trackName;
    trackData["ArtistName"] = inTrackData->m_artistName;
    trackData["AlbumArt"] = songImage;
    trackData["TrackSource"] = inTrackData->m_trackSourcePath;
    trackData["NoteCount"] = inTrackData->m_noteData.size();
    m_owner.ExecuteScript( "window.DisplayTrack(" + trackData.dump() + "); " );
}
