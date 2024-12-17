#include "TrackRadioUtils.h"
#include "Global\TrackRadio.h"
#include "CoreGame\TrackList.h"
#include "Path.h"


TrackRadioUtils::TrackRadioUtils( BasicUIView& inOwningView )
    : m_owner(inOwningView)
{

}


void TrackRadioUtils::OnUILoad( ultralight::JSObject& GlobalWindow, ultralight::View* Caller )
{
    GlobalWindow["SkipTrack"] = BindJSCallback( &TrackRadioUtils::SkipTrack );
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

        lastIndex = randomIndex; // Update the last played index
        randomElement = &trackExample[randomIndex];

        RadioArgs radioArgs;
        radioArgs.CurrentTrack = randomElement;
        radioArgs.UsePreviewMarker = false;
        TrackRadio::GetInstance().Play( radioArgs );
    }

    if( randomElement )
    {
        Path dlcTest = Path( randomElement->m_albumArtPath );
        std::string songImage = dlcTest.GetLocalPathString();
        json trackData;
        trackData["TrackName"] = randomElement->m_trackName;
        trackData["ArtistName"] = randomElement->m_artistName;
        trackData["AlbumArt"] = songImage;
        trackData["TrackSource"] = randomElement->m_trackSourcePath;
        trackData["NoteCount"] = randomElement->m_noteData.size();
        m_owner.ExecuteScript( "window.DisplayTrack(" + trackData.dump() + "); " );
    }
}

void TrackRadioUtils::SkipTrack( const ultralight::JSObject& thisObject, const ultralight::JSArgs& args )
{
    TrackRadio::GetInstance().Stop();
    PlayNextRandomTrack();
    //m_drums->hitPad( PadId::Snare, 1.f );
}
