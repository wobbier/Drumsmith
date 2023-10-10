#include "TrackEditor.h"
#include "CoreGame\TrackList.h"
#include "Events\HavanaEvents.h"
#include "Components\Audio\AudioSource.h"
#include "Events\GameEvents.h"
#include "Events\AudioEvents.h"


TrackEditor::TrackEditor()
    : HavanaWidget( "Track Editor" )
{
    EventManager::GetInstance().RegisterReceiver( this, { MouseScrollEvent::GetEventId() } );
}


TrackEditor::~TrackEditor()
{

}

void TrackEditor::Init()
{
    auto& trackList = TrackDatabase::GetInstance().m_trackList.m_tracks;
    for( auto& track : trackList )
    {
        track.LoadNoteData();
    }

}

void TrackEditor::Destroy()
{
}

void TrackEditor::Update()
{
}

float TrackEditor::GetNoteWidth(float timelineSizeScale)
{
    float scaledWidth = kDefaultMaxKeyframeWidth * timelineSizeScale;
    return std::clamp( scaledWidth, kMinKeyframeWidth, kMaxKeyframeWidth );
}

float TrackEditor::CalculateZoom()
{
    return std::powf( kBaseZoomFactor, ScrollDelta );
}

void TrackEditor::Render()
{
    //ScrollDelta += GetEngine().GetEditorInput().GetMouseScrollDelta().x;

    ImGuiWindowFlags windowFlags = 0 | ImGuiWindowFlags_MenuBar | ImGuiWindowFlags_HorizontalScrollbar | ImGuiWindowFlags_NoScrollWithMouse;
    ImGui::Begin( "Track Editor", &IsOpen, windowFlags );
    if( ImGui::BeginMenuBar() )
    {
        if( ImGui::BeginMenu( "File" ) )
        {
            if( ImGui::MenuItem( "Open Track" ) )
            {
                auto callback = [this]( Path selectedAsset )
                {
                    SelectedTrackLocation = Path( selectedAsset.GetDirectoryString() + "NoteData.txt" );

                    if( !SelectedTrackLocation.Exists )
                    {
                        YIKES_FMT( "Failed to find note data: %s", SelectedTrackLocation.FullPath );
                    }
                };
                RequestAssetSelectionEvent evt( callback, AssetType::Audio );
                evt.Fire();
            }
            ImGui::EndMenu();
        }
        ImGui::EndMenuBar();
    }

    auto& trackData = TrackDatabase::GetInstance().m_trackList.m_tracks[SelectedTrackIndex];

    if( SelectedTrackLocation.Exists )
    {
        ImGui::Text( SelectedTrackLocation.GetLocalPath().data() );
        int i = 0;
        for( auto& track : TrackDatabase::GetInstance().m_trackList.m_tracks )
        {
            if( Path( track.m_trackSourcePath ).FullPath == SelectedTrackLocation.FullPath )
            {
                SelectedTrackIndex = i;
            }
            ++i;
        }
        if( ( ( TrackPreview && !TrackPreview->IsPlaying() ) || !TrackPreview ) && ImGui::Button( "Play" ) )
        {
            PlayAudioEvent evt;
            evt.SourceName = std::string( SelectedTrackLocation.GetDirectoryString() + std::string( "Track.mp3" ) );
            evt.Callback = [this]( SharedPtr<AudioSource> inSource )
            {
                TrackPreview = inSource;
            };
            evt.Fire();
        }
        else if( TrackPreview && TrackPreview->IsPlaying() )
        {
            if( ImGui::Button( "Stop" ) )
            {
                TrackPreview->Stop();
            }
        }
    }
    else
    {
        SelectedTrackLocation = Path( Path( trackData.m_trackSourcePath ).GetDirectoryString() + "NoteData.txt" );
    }


    TimelineSize = trackData.m_duration;

    float timelineSizeScale = 1.f + CalculateZoom() * ( 50.f / TimelineSize );
    float timelineSizeZoomed = TimelineSize * timelineSizeScale;

    float timelineHeight = ( kNoteHeight + 5.f ) * PadId::COUNT;
    ImGui::BeginChildFrame( 200, { timelineSizeZoomed, timelineHeight }, ImGuiWindowFlags_NoScrollWithMouse );

    if( TrackPreview )
    {
        float progress = (float)TrackPreview->GetPositionMs() / 1000.f;

        if( ImGui::SliderFloat( "##SeekSlider", &progress, 0, (float)TrackPreview->GetLength() / 1000.f, "%.3f" ) )
        {
            TrackPreview->SetPositionMs( progress * 1000.f );
        }
    }

    ImDrawList* drawList = ImGui::GetWindowDrawList();
    ImVec2 canvas_pos = ImGui::GetCursorScreenPos();
    ImVec2 canvas_size = { timelineSizeZoomed, kNoteHeight };


    for( NoteData& note : trackData.m_noteData )
    {
        float notePosX = canvas_pos.x + ( note.m_triggerTime * timelineSizeScale );
        float notePosY = canvas_pos.y + ( note.m_editorLane * kNoteHeight ) + ( note.m_editorLane * 5.f );
        ImVec2 timelinePos = { notePosX, notePosY };
        drawList->AddRectFilled( timelinePos, ImVec2( timelinePos.x + GetNoteWidth(timelineSizeScale)/*+ ( 1.f * ScrollDelta/10.f )*/, timelinePos.y + canvas_size.y ), (ImU32)GetNoteColor( note.m_editorLane ) );
    }

    if( TrackPreview )
    {
        float totalSongTime = ( TrackPreview->GetLength() / 1000.f );
        float songTime = ( TrackPreview->GetPositionMs() / 1000.f );
        float scrubberX = canvas_pos.x + ( ( timelineSizeZoomed * ( songTime / totalSongTime ) ) );
        drawList->AddLine( { scrubberX, canvas_pos.y }, { scrubberX, canvas_pos.y + timelineHeight }, 0xFFFFFFFF );
    }

    ImGui::EndChildFrame();

    IsWindowHovered = true;// ImGui::IsWindowHovered();
    ImGui::End();
}

bool TrackEditor::OnEvent( const BaseEvent& evt )
{
    //if( evt.GetEventId() == RequestAssetSelectionEvent::GetEventId() )
    //{
    //    RequestAssetSelectionEvent& event = static_cast<RequestAssetSelectionEvent>( evt );
    //}
    if( IsWindowHovered && evt.GetEventId() == MouseScrollEvent::GetEventId() )
    {
        const MouseScrollEvent& event = static_cast<const MouseScrollEvent&>( evt );
        ScrollDelta += event.Scroll.y;
    }
    return false;
}

int TrackEditor::GetNoteColor( PadId inId )
{
    switch( inId )
    {
    case PadId::Bass:
        return 0xFF4A9FE5;
    case PadId::Snare:
        return 0xFF334FCB;
    case PadId::ClosedHiHat:
    case PadId::OpenHiHat:
        return 0xFF73EDF3;
    case PadId::HighTom:
        return 0xFFC38839;
    case PadId::MidTom:
    case PadId::Crash:
    case PadId::FloorTom:
        return 0xFFA0C263;
    }
    return 0xFFFFFFFF;
}
