#include "TrackEditor.h"
#include "CoreGame\TrackList.h"
#include "Events\HavanaEvents.h"
#include "Components\Audio\AudioSource.h"
#include "Events\GameEvents.h"
#include "Events\AudioEvents.h"
#include "Mathf.h"
#include "Engine\Engine.h"


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
    hitNotes.resize( (int)PadId::COUNT );
}

void TrackEditor::Destroy()
{
}

void TrackEditor::Update()
{
}

float TrackEditor::GetNoteWidth( float timelineSizeScale )
{
    float scaledWidth = kDefaultMaxKeyframeWidth * timelineSizeScale;
    return std::clamp( scaledWidth, kMinKeyframeWidth, kMaxKeyframeWidth );
}

float TrackEditor::CalculateZoom()
{
    return std::powf( kBaseZoomFactor, ScrollDelta );
}

float TrackEditor::ScaleValue( float inValue )
{
    return inValue * ( 1.f + CalculateZoom() * ( 50.f / TimelineSize ) );
}

bool TrackEditor::CullVisual( float posx )
{
    if( posx > WindowContentSize )
    {
        return true;
    }
    return false;
}

void TrackEditor::Render()
{
    //ScrollDelta += GetEngine().GetEditorInput().GetMouseScrollDelta().x;
    auto& trackData = TrackDatabase::GetInstance().m_trackList.m_tracks[SelectedTrackIndex];

    ImGuiWindowFlags windowFlags = 0 | ImGuiWindowFlags_MenuBar | ImGuiWindowFlags_HorizontalScrollbar | ImGuiWindowFlags_NoScrollWithMouse;
    ImGui::Begin( "Track Editor", &IsOpen, windowFlags );
    //ImGui::SetScrollX( ImGui::GetScrollX() );

    DrawMenuBar();
    DrawTrackControls();

    TimelineSize = trackData.m_duration;

    timelineSizeScale = 1.f + CalculateZoom() * ( 50.f / TimelineSize );
    timelineSizeZoomed = TimelineSize * timelineSizeScale;

    float timelineHeight = ( kNoteHeight + kLaneSpacing ) * PadId::COUNT;
    WindowContentSize = ImGui::GetWindowPos().x + ImGui::GetWindowSize().x + ImGui::GetScrollX();

    ImGui::Text( ( "ImGui::GetScrollX(): " + std::to_string( ImGui::GetScrollX() ) ).c_str() );
    ImGui::Text( ( "WindowContentSize: " + std::to_string( WindowContentSize ) ).c_str() );
    ImGui::Text( ( "ImGui::GetWindowPos().x: " + std::to_string( ImGui::GetWindowPos().x ) ).c_str() );
    ImGui::Text( ( "ImGui::GetMousePos().x: " + std::to_string( ImGui::GetMousePos().x ) ).c_str() );
    float windowPos = ImGui::GetWindowPos().x;
    ImGui::Text( ( "ImGui::GetWindowSize().x: " + std::to_string( ImGui::GetWindowSize().x ) ).c_str() );

    if( TrackPreview )
    {
        float progress = (float)TrackPreview->GetPositionMs() / 1000.f;

        ImGui::SetNextItemWidth( timelineSizeZoomed );
        if( ImGui::SliderFloat( "##SeekSlider", &progress, 0, (float)TrackPreview->GetLength() / 1000.f, "%.3f" ) )
        {
            TrackPreview->SetPositionMs( progress * 1000.f );
        }
    }
    ImGui::BeginChildFrame( 200, { timelineSizeZoomed, timelineHeight }, ImGuiWindowFlags_NoScrollWithMouse );

    ImDrawList* drawList = ImGui::GetWindowDrawList();
    ImVec2 canvas_pos = ImGui::GetCursorScreenPos();
    ImVec2 canvas_size = { timelineSizeZoomed, kNoteHeight };

    ImGui::Text( ( "canvas_pos.x: " + std::to_string( canvas_pos.x ) ).c_str() );
    ImGui::Text( ( "canvas_size.x: " + std::to_string( canvas_size.x ) ).c_str() );
    float relativeMouseX = ImGui::GetMousePos().x - canvas_pos.x;
    float relativeMouseY = ImGui::GetMousePos().y - canvas_pos.y;
    ImGui::Text( ( "relativeMouseX: " + std::to_string( relativeMouseX ) ).c_str() );
    ImGui::Text( ( "relativeMouseY: " + std::to_string( relativeMouseY ) ).c_str() );


    float numBars = 0;
    float numSubBars = 0;
    float numNotes = 0;
    float numCulled = 0;
    // Track Lines
    {
        float secondsPerMeasure = kBeatsPerMeasure * ( 60.f / trackData.m_bpm );
        float scaledSecondsPerMeasure = secondsPerMeasure * ( CalculateZoom() );
        for( float position = 0; position <= WindowContentSize; position += ScaleValue( secondsPerMeasure ) )
        {
            numBars++;
            if( CullVisual( canvas_pos.x + position ) || canvas_pos.x + position < windowPos )
            {
                numCulled++;
                //continue;
            }
            else
            {
                if( CalculateZoom() > 100.f )
                {
                    drawList->AddLine( { canvas_pos.x + position, canvas_pos.y }, { canvas_pos.x + position, canvas_pos.y + timelineHeight }, 0xFFFFFFFF );
                }
                if( CalculateZoom() > 400.f )
                {
                    float subMeasures = ( kBeatsPerMeasure / 4.f ) * ( 60.f / trackData.m_bpm );
                    for( float pos = position + subMeasures; pos < WindowContentSize; pos += ScaleValue( subMeasures ) )
                    {
                        numSubBars++;
                        if( CullVisual( canvas_pos.x + pos ) )
                        {
                            numCulled++;
                            //break;
                        }
                        else
                        {
                            drawList->AddLine( { canvas_pos.x + pos, canvas_pos.y }, { canvas_pos.x + pos, canvas_pos.y + timelineHeight }, 0x10FFFFFF );
                        }
                    }
                }
            }
        }
    }

    bool doubleClickHandled = false;
    for( auto note = trackData.m_noteData.begin(); note != trackData.m_noteData.end(); note++ )
    {
        float notePosX = canvas_pos.x + ( note->m_triggerTime * timelineSizeScale );
        float notePosY = canvas_pos.y + ( note->m_editorLane * kNoteHeight ) + ( note->m_editorLane * kLaneSpacing );
        ImVec2 timelinePos = { notePosX, notePosY };

        numNotes++;
        if( CullVisual( timelinePos.x ) )
        {
            numCulled++;
            //break;
        }
        else
        {
            ImVec2 rect( timelinePos.x + GetNoteWidth( timelineSizeScale ), timelinePos.y + canvas_size.y );
            if( ImGui::IsMouseDoubleClicked( ImGuiMouseButton_Left ) )
            {
                if( canvas_pos.x + relativeMouseX > timelinePos.x && canvas_pos.x + relativeMouseX < rect.x
                    && canvas_pos.y + relativeMouseY > timelinePos.y && canvas_pos.y + relativeMouseY < rect.y )
                {
                    doubleClickHandled = true;
                    trackData.m_noteData.erase( note );
                    break;
                }
            }
            drawList->AddRectFilled( timelinePos, rect/*+ ( 1.f * ScrollDelta/10.f )*/, (ImU32)PadUtils::GetNoteColorABGR( note->m_editorLane ) );
        }
    }

    if( !doubleClickHandled && ImGui::IsMouseDoubleClicked( ImGuiMouseButton_Left ) && TrackPreview )
    {
        if( relativeMouseY > 0 && relativeMouseY < timelineHeight )
        {
            NoteData newNote;
            PadId id = Bass;
            for( int i = (int)id; i < PadId::COUNT; ++i )
            {
                if( relativeMouseY > ( i * kNoteHeight ) + ( i * kLaneSpacing ) )
                {
                    id = (PadId)i;
                }
            }
            newNote.m_editorLane = id;
            newNote.m_noteName = PadUtils::GetPadId( id );
            float percent = relativeMouseX / timelineSizeZoomed;
            newNote.m_triggerTime = ( TrackPreview->GetLength() * percent ) / 1000.f;
            trackData.m_noteData.push_back( newNote );
        }
    }

    ImGui::Text( ( "Num Culled: " + std::to_string( numCulled ) ).c_str() );

    if( TrackPreview )
    {
        float totalSongTime = ( TrackPreview->GetLength() / 1000.f );
        float songTime = ( TrackPreview->GetPositionMs() / 1000.f );
        float scrubberX = canvas_pos.x + ( ( timelineSizeZoomed * ( songTime / totalSongTime ) ) );
        drawList->AddLine( { scrubberX, canvas_pos.y }, { scrubberX, canvas_pos.y + timelineHeight }, 0xFFFFFFFF );
    }

    ImGui::EndChildFrame();

    DrawPadPreview();

    IsWindowHovered = true;// ImGui::IsWindowHovered();
    ImGui::End();
}

void TrackEditor::DrawTrackControls()
{
    Input& input = GetEngine().GetEditorInput();
    TrackData& trackData = GetCurrentTrackData();
    if( SelectedTrackLocation.Exists )
    {
        ImGui::Text( SelectedTrackLocation.GetLocalPath().data() );
        int i = 0;
        for( auto& track : TrackDatabase::GetInstance().m_trackList.m_tracks )
        {
            if( Path( track.m_trackSourcePath ).GetDirectoryString() == SelectedTrackLocation.GetDirectoryString() )
            {
                SelectedTrackIndex = i;
            }
            ++i;
        }
        if( ( ( TrackPreview && !TrackPreview->IsPlaying() ) || !TrackPreview ) && ( ImGui::Button( "Play" ) || input.WasKeyPressed( KeyCode::Space ) ) )
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
            if( TrackPreview->IsPaused() )
            {
                if( ImGui::Button( "Resume" ) || input.WasKeyPressed( KeyCode::Space ) )
                {
                    TrackPreview->Resume();
                }
            }
            else
            {
                if( ImGui::Button( "Pause" ) || input.WasKeyPressed( KeyCode::Space ) )
                {
                    TrackPreview->Pause();
                }
            }
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
}

TrackData& TrackEditor::GetCurrentTrackData()
{
    return TrackDatabase::GetInstance().m_trackList.m_tracks[SelectedTrackIndex];
}

void TrackEditor::DrawMenuBar()
{
    TrackData& trackData = GetCurrentTrackData();
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

            if( ImGui::MenuItem( "Save Track" ) )
            {
                trackData.Clear();
                trackData.Save();
            }
            ImGui::EndMenu();
        }
        ImGui::Text( std::to_string( CalculateZoom() ).c_str() );
        ImGui::EndMenuBar();
    }
}

void TrackEditor::DrawPadPreview()
{
    if( ImGui::CollapsingHeader( "Pad Preview" ) )
    {
        auto& trackData = GetCurrentTrackData();
        ImVec2 outerWindowSize = ImGui::GetWindowSize();
        ImGui::SetCursorPosX( ImGui::GetScrollX() );
        const float xSpacing = 5.f;
        ImGui::BeginChildFrame( 2, { outerWindowSize.x - xSpacing, 55.f }, ImGuiWindowFlags_NoScrollWithMouse );

        ImDrawList* drawList = ImGui::GetWindowDrawList();
        ImVec2 canvas_pos = ImGui::GetCursorScreenPos();
        ImVec2 canvas_size = { timelineSizeZoomed, kNoteHeight };
        ImVec2 windowSize = ImGui::GetWindowSize();

        if( TrackPreview )
        {
            if( TrackPreview->GetPositionMs() < m_cachedTimestamp )
            {
                m_closestNoteIndex = 0;
            }
            m_cachedTimestamp = TrackPreview->GetPositionMs();
        }

        if( TrackPreview )
        {
            for( size_t i = m_closestNoteIndex; i < trackData.m_noteData.size(); ++i )
            {
                auto& currentNote = trackData.m_noteData[i];
                float triggerTime = currentNote.m_triggerTime * 1000.f;
                float timeDiff = triggerTime - m_cachedTimestamp;
                if( Mathf::Abs( timeDiff ) <= 50.f )
                {
                    hitNotes[(int)currentNote.m_editorLane] = true;
                }
                if( timeDiff > 500 )
                {
                    break;
                }
                if( timeDiff <= -500 )
                {
                    m_closestNoteIndex = i;
                    //m_closestNoteIndex = i;
                }
            }


            for( int i = 0; i < (int)PadId::COUNT; ++i )
            {
                ImVec2 padPos = { canvas_pos.x + ( ( windowSize.x / (int)PadId::COUNT ) * i ), canvas_pos.y };
                ImVec2 padSize = { padPos.x + ( windowSize.x / (int)PadId::COUNT ) - xSpacing, padPos.y + 50 };
                if( hitNotes[i] )
                {
                    drawList->AddRectFilled( padPos, padSize, (ImU32)PadUtils::GetNoteColorABGR( (PadId)i ) );
                }
                else
                {
                    drawList->AddRect( padPos, padSize, (ImU32)PadUtils::GetNoteColorABGR( (PadId)i ) );
                }

                hitNotes[i] = false;
            }
        }

        ImGui::EndChildFrame();
    }
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