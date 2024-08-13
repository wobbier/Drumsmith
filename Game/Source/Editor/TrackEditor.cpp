#include "TrackEditor.h"
#include "CoreGame\TrackList.h"
#include "Events\HavanaEvents.h"
#include "Components\Audio\AudioSource.h"
#include "Events\GameEvents.h"
#include "Events\AudioEvents.h"
#include "Mathf.h"
#include "Engine\Engine.h"
#include "optick.h"
#include "misc/cpp/imgui_stdlib.h"
#include "RtMidi.h"
#include "Utils\HavanaUtils.h"

#if USING(ME_EDITOR)

TrackEditor::TrackEditor()
    : HavanaWidget( "Track Editor" )
{
    EventManager::GetInstance().RegisterReceiver( this, { MouseScrollEvent::GetEventId() } );
    //m_manager.OpenAllDevices();
}


TrackEditor::~TrackEditor()
{

}

void TrackEditor::Init()
{
    auto& trackList = TrackDatabase::GetInstance().m_trackList.m_tracks;
    for( auto& track : trackList )
    {
        //track.LoadNoteData();
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

void TrackEditor::ResetTrack()
{
    SelectedTrackIndex = 0;
    if( !SelectedTrackLocation.Exists )
    {
        return;
    }

    int i = 0;
    for( auto& track : TrackDatabase::GetInstance().m_trackList.m_tracks )
    {
        std::cout << Path( track.m_trackSourcePath ).GetDirectoryString().c_str() << std::endl;
        std::cout << SelectedTrackLocation.GetDirectoryString().c_str() << std::endl;
        if( Path( track.m_trackSourcePath ).GetDirectoryString() == SelectedTrackLocation.GetDirectoryString() )
        {
            SelectedTrackIndex = i;
            TrackDatabase::GetInstance().m_trackList.m_tracks[SelectedTrackIndex].LoadNoteData();
            return;
        }
        ++i;
    }
}

void TrackEditor::Render()
{
    OPTICK_CATEGORY( "TrackEditor::Render", Optick::Category::UI );

    if( TrackDatabase::GetInstance().m_trackList.m_tracks.empty() )
    {
        return;
    }

    if( SelectedTrackIndex < 0 )
    {
        ResetTrack();
    }

    //ScrollDelta += GetEngine().GetEditorInput().GetMouseScrollDelta().x;
    auto& trackData = TrackDatabase::GetInstance().m_trackList.m_tracks[SelectedTrackIndex];

    ImGuiWindowFlags windowFlags = 0 | ImGuiWindowFlags_MenuBar | ImGuiWindowFlags_HorizontalScrollbar | ImGuiWindowFlags_NoScrollWithMouse;
    ImGui::Begin( "Track Editor", &IsOpen, windowFlags );
    //ImGui::SetScrollX( ImGui::GetScrollX() );
    ImVec2 windowCursorPos = ImGui::GetCursorPos();

    DrawMenuBar();

    ImGui::SetCursorPosX( windowCursorPos.x );
    DrawTrackControls();
    auto& m_midi = MidiDevice::GetInstance();
    {
        static std::string m_selectedMidiDeviceName;
        HavanaUtils::Label( "Midi Device" );
        if( ImGui::BeginCombo( "##Device", m_selectedMidiDeviceName.empty() ? "Select a device" : m_selectedMidiDeviceName.c_str() ) )
        {
            for( int i = 0; i < m_midi.m_devices.size(); ++i )
            {
                if( ImGui::Selectable( m_midi.m_devices[i].Name.c_str()) )
                {
                    m_selectedMidiDeviceName = m_midi.m_devices[i].Name;
                    m_midi.OpenMidiDevice( i );
                    m_midi.PumpMessages();
                }
            }

            ImGui::EndCombo();
        }
    }
    //m_midi.IsPaused = !ImGui::IsWindowFocused();

    if( ImGui::IsWindowFocused() )
    {
        m_midi.PumpMessages();
    }
    TimelineSize = trackData.m_duration;

    timelineSizeScale = 1.f + CalculateZoom() * ( 50.f / TimelineSize );
    timelineSizeZoomed = TimelineSize * timelineSizeScale;

    float timelineHeight = ( m_noteHeight + kLaneSpacing ) * PadId::COUNT;
    float scrollOffsetX = ImGui::GetScrollX();
    WindowContentSize = ImGui::GetWindowPos().x + ImGui::GetWindowSize().x + ImGui::GetScrollX();
    float windowPos = 0.f;
    {
        OPTICK_CATEGORY( "Debug Text", Optick::Category::Debug );
        if( m_showDebugInfo )
        {
            ImGui::SetCursorPosX( windowCursorPos.x + ImGui::GetScrollX() );
            ImGui::Text( ( "ImGui::GetScrollX(): " + std::to_string( ImGui::GetScrollX() ) ).c_str() );
            ImGui::SetCursorPosX( windowCursorPos.x + ImGui::GetScrollX() );
            ImGui::Text( ( "WindowContentSize: " + std::to_string( WindowContentSize ) ).c_str() );
            ImGui::SetCursorPosX( windowCursorPos.x + ImGui::GetScrollX() );
            ImGui::Text( ( "ImGui::GetWindowPos().x: " + std::to_string( ImGui::GetWindowPos().x ) ).c_str() );
            ImGui::SetCursorPosX( windowCursorPos.x + ImGui::GetScrollX() );
            ImGui::Text( ( "ImGui::GetMousePos().x: " + std::to_string( ImGui::GetMousePos().x ) ).c_str() );
        }
        windowPos = ImGui::GetWindowPos().x;
        if( m_showDebugInfo )
        {
            ImGui::SetCursorPosX( windowCursorPos.x + ImGui::GetScrollX() );
            ImGui::Text( ( "ImGui::GetWindowSize().x: " + std::to_string( ImGui::GetWindowSize().x ) ).c_str() );
        }
    }

    if( TrackPreview )
    {
        OPTICK_CATEGORY( "TrackPreview", Optick::Category::Debug );
        float progress = (float)TrackPreview->GetPositionMs();

        ImGui::SetNextItemWidth( timelineSizeZoomed );
        if( ImGui::SliderFloat( "##SeekSlider", &progress, 0, (float)TrackPreview->GetLength(), "%.3f" ) )
        {
            TrackPreview->SetPositionMs( progress );
        }
    }
    ImGui::BeginChildFrame( 200, { timelineSizeZoomed, timelineHeight }, ImGuiWindowFlags_NoScrollWithMouse );
    bool isTimelineHovered = ImGui::IsWindowHovered();
    ImDrawList* drawList = ImGui::GetWindowDrawList();
    ImVec2 canvas_pos = ImGui::GetCursorScreenPos();
    ImVec2 canvas_size = { timelineSizeZoomed, m_noteHeight };
    {
        OPTICK_CATEGORY( "SetCursorPosX", Optick::Category::Debug );
        ImGui::SetCursorPosX( windowCursorPos.x + ImGui::GetScrollX() );
    }
    float relativeMouseX = 0.f;
    float relativeMouseY = 0.f;
    {
        if( m_showDebugInfo )
        {
            OPTICK_CATEGORY( "Debug Info", Optick::Category::Debug );
            ImGui::Text( ( "canvas_pos.x: " + std::to_string( canvas_pos.x ) ).c_str() );
            ImGui::SetCursorPosX( windowCursorPos.x + ImGui::GetScrollX() );
            ImGui::Text( ( "canvas_size.x: " + std::to_string( canvas_size.x ) ).c_str() );
        }
        relativeMouseX = ImGui::GetMousePos().x - canvas_pos.x;
        relativeMouseY = ImGui::GetMousePos().y - canvas_pos.y;
        if( m_showDebugInfo )
        {
            ImGui::SetCursorPosX( windowCursorPos.x + ImGui::GetScrollX() );
            ImGui::Text( ( "relativeMouseX: " + std::to_string( relativeMouseX ) ).c_str() );
            ImGui::SetCursorPosX( windowCursorPos.x + ImGui::GetScrollX() );
            ImGui::Text( ( "relativeMouseY: " + std::to_string( relativeMouseY ) ).c_str() );
        }
    }

    // Preview Marker
    if( TrackPreview )
    {
        float totalSongTime = ( TrackPreview->GetLength() / 1000.f );
        float songTime = ( ( TrackPreview->GetLength() * trackData.m_previewPercent ) / 1000.f );
        float scrubberX = canvas_pos.x + ( ( timelineSizeZoomed * ( songTime / totalSongTime ) ) );
        drawList->AddLine( { scrubberX, canvas_pos.y }, { scrubberX, canvas_pos.y + timelineHeight }, 0xFFF00FFF );
    }


    float numBars = 0;
    float numSubBars = 0;
    float numNotes = 0;
    float numCulled = 0;
    // Track Lines
    {
        OPTICK_CATEGORY( "Track Lines", Optick::Category::UI );
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

    // Hover row selection color and labels
    if( relativeMouseY > 0 && relativeMouseY < timelineHeight )
    {
        PadId id = Bass;
        for( int i = (int)id; i < PadId::COUNT; ++i )
        {
            if( relativeMouseY > ( i * m_noteHeight ) + ( i * kLaneSpacing ) )
            {
                id = (PadId)i;
            }

            ImGui::SetCursorPosY( ( (int)i * ( m_noteHeight + kLaneSpacing ) ) + kLaneSpacing );
            ImGui::SetCursorPosX( scrollOffsetX + kLaneSpacing );
            ImGui::Text( PadUtils::GetPadName( (PadId)i ) );
        }
        float notePosX = canvas_pos.x;
        float notePosY = canvas_pos.y + ((int)id * (m_noteHeight + kLaneSpacing));
        ImVec2 timelinePos = { notePosX, notePosY };
        ImVec2 rect( timelinePos.x + timelineSizeZoomed, notePosY + m_noteHeight );

        drawList->AddRectFilled( timelinePos, rect, (ImU32)0x11FFFFFF ); // AGBR
    }

    // Adding Notes
    bool doubleClickHandled = false;
    {
        OPTICK_CATEGORY( "Draw Note Data", Optick::Category::UI );
        for( auto note = trackData.m_noteData.begin(); note != trackData.m_noteData.end(); note++ )
        {
            float notePosX = canvas_pos.x + ( note->m_triggerTime * timelineSizeScale );
            float notePosY = canvas_pos.y + ( note->m_editorLane * m_noteHeight ) + ( note->m_editorLane * kLaneSpacing );
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
    }

    // Removing Notes
    if( !doubleClickHandled && ImGui::IsMouseDoubleClicked( ImGuiMouseButton_Left ) && TrackPreview )
    {
        if( relativeMouseY > 0 && relativeMouseY < timelineHeight )
        {
            NoteData newNote;
            PadId id = Bass;
            for( int i = (int)id; i < PadId::COUNT; ++i )
            {
                if( relativeMouseY > ( i * m_noteHeight ) + ( i * kLaneSpacing ) )
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

    if( m_showDebugInfo )
    {
        ImGui::Text( ( "Num Culled: " + std::to_string( numCulled ) ).c_str() );
    }

    if( TrackPreview )
    {
        float totalSongTime = ( TrackPreview->GetLength() / 1000.f );
        float songTime = ( TrackPreview->GetPositionMs() / 1000.f );
        float scrubberX = canvas_pos.x + ( ( timelineSizeZoomed * ( songTime / totalSongTime ) ) );
        drawList->AddLine( { scrubberX, canvas_pos.y }, { scrubberX, canvas_pos.y + timelineHeight }, 0xFFFFFFFF );
    }

    ImGui::EndChildFrame();

    DrawPadPreview();

    IsWindowHovered = ImGui::IsWindowHovered() || isTimelineHovered;
    ImGui::End();
}

void TrackEditor::DrawTrackControls()
{
    OPTICK_CATEGORY( "Track Controls", Optick::Category::UI );

    Input& input = GetEngine().GetEditorInput();
    ImVec2 windowCursorPos = ImGui::GetCursorPos();
    if( SelectedTrackLocation.Exists )
    {
        TrackData& trackData = GetCurrentTrackData();
        ImGui::SetCursorPosX( windowCursorPos.x + ImGui::GetScrollX() );
        ImGui::Text( SelectedTrackLocation.GetLocalPath().data() );
        ImGui::InputText( "Track Name", &trackData.m_trackName );
        ImGui::InputText( "Artist", &trackData.m_artistName );
        ImGui::InputInt( "BPM", &trackData.m_bpm, 1, 10 );
        ImGui::SliderFloat( "Note Height", &m_noteHeight, 10.f, 50.f, "%.1f" );
        if( ImGui::Button( "Set Track Preview Marker" ) )
        {
            if( TrackPreview )
            {
                trackData.m_previewPercent = (TrackPreview->GetPositionMs() / (float)TrackPreview->GetLength());
            }
        }
        if( TrackPreview )
        {
            float newFrequency = TrackPreview->GetPlaybackSpeed();
            if( ImGui::SliderFloat( "Playback Speed", &newFrequency, 0.f, 2.f, "%.02f" ) )
            {
                TrackPreview->SetPlaybackSpeed( newFrequency );
            }
        }
        //if( ImGui::Button( !SelectedTrackLocation.Exists ? "Select Asset" : SelectedTrackLocation.GetLocalPath().data(), { 200.f, 10.f } ) )
        //{
        //    RequestAssetSelectionEvent evt( [this]( Path selectedAsset ) {
        //        
        //        //ClearData();
        //        //FilePath = selectedAsset;
        //        }, AssetType::Audio );
        //    evt.Fire();
        //}

        ImGui::SetCursorPosX( windowCursorPos.x + ImGui::GetScrollX() );
        if( ( ( TrackPreview && !TrackPreview->IsPlaying() ) || !TrackPreview ) && ( ImGui::Button( "Play" ) || input.WasKeyPressed( KeyCode::Space ) ) )
        {
            PlayAudioEvent evt;
            evt.SourceName = std::string( trackData.m_trackSourcePath );
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
                ImGui::SetCursorPosX( windowCursorPos.x + ImGui::GetScrollX() );
                if( ImGui::Button( "Resume" ) || input.WasKeyPressed( KeyCode::Space ) )
                {
                    TrackPreview->Resume();
                }
            }
            else
            {
                ImGui::SetCursorPosX( windowCursorPos.x + ImGui::GetScrollX() );
                if( ImGui::Button( "Pause" ) || input.WasKeyPressed( KeyCode::Space ) )
                {
                    TrackPreview->Pause();
                }
            }
            ImGui::SameLine(  );
            //ImGui::SetCursorPosX( windowCursorPos.x + ImGui::GetScrollX() );
            if( ImGui::Button( "Stop" ) )
            {
                TrackPreview->Stop();
            }
        }
    }
    else
    {
        TrackData& trackData = GetCurrentTrackData();
        SelectedTrackLocation = Path( Path( trackData.m_trackSourcePath ).GetDirectoryString() + "NoteData.txt" );
    }
}

TrackData& TrackEditor::GetCurrentTrackData()
{
    return TrackDatabase::GetInstance().m_trackList.m_tracks[SelectedTrackIndex];
}

void TrackEditor::DrawMenuBar()
{
    OPTICK_CATEGORY( "Menu Bar", Optick::Category::UI );
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
                    ResetTrack();
                };
                RequestAssetSelectionEvent evt( callback, AssetType::Audio );
                evt.Fire();
            }

            if( ImGui::MenuItem( "Save Track" ) )
            {
                trackData.Save();
            }
            ImGui::EndMenu();
        }
        ImGui::Text( std::to_string( CalculateZoom() ).c_str() );
        ImGui::Checkbox( "Show Debug Info", &m_showDebugInfo );
        ImGui::EndMenuBar();
    }
}

void TrackEditor::DrawPadPreview()
{
    if( ImGui::CollapsingHeader( "Pad Preview", &m_showPadPreview ) )
    {
        auto& trackData = GetCurrentTrackData();
        ImVec2 outerWindowSize = ImGui::GetWindowSize();
        ImGui::SetCursorPosX( ImGui::GetScrollX() );
        const float xSpacing = 5.f;
        ImGui::BeginChildFrame( 2, { outerWindowSize.x - xSpacing, 55.f }, ImGuiWindowFlags_NoScrollWithMouse );

        ImDrawList* drawList = ImGui::GetWindowDrawList();
        ImVec2 canvas_pos = ImGui::GetCursorScreenPos();
        ImVec2 canvas_size = { timelineSizeZoomed, m_noteHeight };
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
                const float kPadHeight = 50.f;
                float padWidth = ( windowSize.x / (int)PadId::COUNT );
                ImVec2 padPos = { canvas_pos.x + ( padWidth * i ), canvas_pos.y };
                ImVec2 padSize = { padPos.x + padWidth - xSpacing, padPos.y + kPadHeight };
                if( hitNotes[i] )
                {
                    drawList->AddRectFilled( padPos, padSize, (ImU32)PadUtils::GetNoteColorABGR( (PadId)i ) );
                }
                else
                {
                    drawList->AddRect( padPos, padSize, (ImU32)PadUtils::GetNoteColorABGR( (PadId)i ) );
                }
                const char* text = PadUtils::GetPadName( (PadId)i );
                ImVec2 textSize = ImGui::CalcTextSize( text );
                ImVec2 textPos = { (padPos.x + padWidth / 2.f) - ( textSize.x / 2.f ), canvas_pos.y + (( kPadHeight / 2.f ) - (textSize.y / 2.f))};
                drawList->AddText( textPos, (ImU32)PadUtils::GetNoteColorABGR( (PadId)i ), text );

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

#endif