#include "Editor/Chart/PreviewSession.h"
#include "Editor/Chart/ChartDocument.h"
#include "Editor/Chart/Transport.h"
#include "Cores/NoteHighwayCore.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Events/SceneEvents.h"
#include "Global/TrackRadio.h"
#include <Utils/ImGuiUtils.h>
#include <imgui.h>

#if USING( ME_EDITOR )
#include <Editor/EditorActions.h>
#include <Utils/EditorIcons.h>
#include <Editor/HostedPlay.h>

namespace
{
    constexpr const char* kGameplayScene = "Assets/Example.lvl";
    constexpr const char* kSongListScene = "Assets/TrackList.lvl";
    constexpr int kStartTimeoutFrames = 900;
    constexpr float kVenueRebuildDelay = 0.4f;

    bool IsPlaying()
    {
        // Pause / Resume is only enabled during play; it is what the editor itself asks.
        return EditorActions::Get().IsEnabled( "Play.Pause" );
    }


    VenueShow::Presentation PresentationOf( PreviewSession::Mode inMode )
    {
        switch( inMode )
        {
        case PreviewSession::Mode::Highway: return VenueShow::Presentation::HighwayOnly;
        case PreviewSession::Mode::Scene: return VenueShow::Presentation::VenueOnly;
        default: return VenueShow::Presentation::Both;
        }
    }
}


NoteHighwayCore* PreviewSession::FindCore() const
{
    if( !IsPlaying() )
    {
        return nullptr;
    }
    const SharedPtr<World> world = GetEngine().GetWorld().lock();
    return world ? world->GetCore<NoteHighwayCore>() : nullptr;
}


void PreviewSession::Fail( const std::string& inWhy )
{
    m_status = inWhy;
    Stop();
    m_status = inWhy;
}


bool PreviewSession::Start( ChartDocument& inDocument )
{
    if( m_state != State::Idle )
    {
        return true;
    }
    if( !inDocument.IsOpen() )
    {
        return false;
    }
    m_status.clear();
    m_startedPlay = false;
    m_loadedScene = false;
    m_waitFrames = 0;
    if( !IsPlaying() )
    {
        // The Game View is the picture, beside the editor: no Maximize On Play, and the focus stays here.
        HostedPlay::Active() = true;
        if( !EditorActions::Get().Execute( "Play.Toggle" ) || !IsPlaying() )
        {
            HostedPlay::Active() = false;
            m_status = "The editor couldn't enter play.";
            return false;
        }
        m_startedPlay = true;
    }
    m_state = State::EnteringPlay;
    return true;
}


void PreviewSession::Stop()
{
    if( m_state == State::Idle )
    {
        return;
    }
    if( NoteHighwayCore* core = FindCore() )
    {
        core->EndPreview();
        core->SetPreviewPresentation( VenueShow::Presentation::Both );
    }
    if( m_startedPlay && IsPlaying() )
    {
        // Out of play: the editor puts the scene back as it was.
        EditorActions::Get().Execute( "Play.Toggle" );
    }
    else if( m_loadedScene && IsPlaying() )
    {
        // The game was running (the editor was opened from its song list): hand it back there.
        LoadSceneEvent load;
        load.Level = kSongListScene;
        load.Queue();
    }
    if( !IsPlaying() )
    {
        // Play that was refused never ended: the next one is the Game View's again.
        HostedPlay::Active() = false;
    }
    m_state = State::Idle;
    m_startedPlay = false;
    m_loadedScene = false;
    m_venueWait = -1.f;
    m_status.clear();
}


void PreviewSession::Update( ChartDocument& inDocument, Transport& inTransport )
{
    if( m_state == State::Idle )
    {
        return;
    }
    if( TrackRadio::GetInstance().IsPlaying() )
    {
        // A menu scene that was open started its radio on entering play: the editor has the audio.
        TrackRadio::GetInstance().Stop();
    }
    NoteHighwayCore* core = FindCore();
    if( m_state != State::Active )
    {
        if( ++m_waitFrames > kStartTimeoutFrames )
        {
            Fail( "The gameplay scene didn't start." );
            return;
        }
        if( !IsPlaying() )
        {
            // Play takes a frame or two to begin.
            return;
        }
        if( core && core->CanPreview() )
        {
            core->BeginPreview( inDocument.Chart );
            m_appliedMode = Mode::Both;
            for( size_t domain = 0; domain < m_versions.size(); ++domain )
            {
                m_versions[domain] = inDocument.Version( static_cast<ChartDomain>( domain ) );
            }
            m_venueWait = -1.f;
            m_state = State::Active;
            // The editor keeps the keyboard: this is editing, not playing.
            GetEngine().GetInput().Stop();
            GetEngine().GetEditorInput().Resume();
        }
        else if( m_state == State::EnteringPlay && m_waitFrames > 5 )
        {
            // The open scene has no highway: load the one that does.
            LoadSceneEvent load;
            load.Level = kGameplayScene;
            load.Queue();
            m_loadedScene = true;
            m_state = State::LoadingScene;
        }
        return;
    }

    if( !core || !core->IsPreviewing() )
    {
        // Play was stopped, or the game went on to something else.
        m_state = State::Idle;
        m_startedPlay = false;
        m_loadedScene = false;
        return;
    }
    if( GetEngine().GetInput().IsCapturing() )
    {
        // A click in the Game View gave the game the keyboard: the editor takes it back.
        GetEngine().GetInput().Stop();
        GetEngine().GetEditorInput().Resume();
    }
    if( m_appliedMode != m_mode )
    {
        core->SetPreviewPresentation( PresentationOf( m_mode ) );
        m_appliedMode = m_mode;
    }

    // What changed since the session last built it. Versions move when an edit is committed (or
    // undone), not during a drag.
    int parts = 0;
    const auto changed = [&]( ChartDomain inDomain ) {
        const size_t index = static_cast<size_t>( inDomain );
        if( m_versions[index] == inDocument.Version( inDomain ) )
        {
            return false;
        }
        m_versions[index] = inDocument.Version( inDomain );
        return true;
    };
    if( changed( ChartDomain::Notes ) ) parts |= NoteHighwayCore::PreviewNotes;
    // The venue plays to the beat too.
    const bool beats = changed( ChartDomain::Beats );
    if( beats ) parts |= NoteHighwayCore::PreviewBeats;
    if( changed( ChartDomain::Venue ) || beats ) m_venueWait = 0.f;
    changed( ChartDomain::Phrases );
    if( m_venueWait >= 0.f )
    {
        m_venueWait += ImGui::GetIO().DeltaTime;
        if( m_venueWait >= kVenueRebuildDelay && !inDocument.HasOpenEdit() )
        {
            parts |= NoteHighwayCore::PreviewVenue;
            m_venueWait = -1.f;
        }
    }
    if( parts != 0 )
    {
        core->RefreshPreview( parts );
    }
    core->SetPreviewTime( inTransport.Seconds() * 1000.0 );
}


void PreviewSession::DrawControls( ChartDocument& inDocument )
{
    const bool running = m_state != State::Idle;
    if( EditorIcons::Button( "eye", "Game Preview", "Shows this chart in the Game View at the playhead, live as you edit, scrub and play. Play starts it. It runs the gameplay scene in play mode; turning it off puts the open scene back.", true, running ) )
    {
        if( running )
        {
            Stop();
        }
        else
        {
            Start( inDocument );
        }
    }
    ImGui::SameLine( 0.f, 4.f );
    static const char* const kModes[] = { "Both", "Highway", "Scene" };
    int mode = static_cast<int>( m_mode );
    ImGui::SetNextItemWidth( 96.f );
    if( ImGui::Combo( "##previewMode", &mode, kModes, IM_ARRAYSIZE( kModes ) ) )
    {
        m_mode = static_cast<Mode>( mode );
    }
    if( ImGui::IsItemHovered() )
    {
        ImGui::SetTooltip( "What the preview shows: the highway and the venue, the notes alone, or the show alone." );
    }
    if( IsStarting() )
    {
        ImGui::SameLine();
        ImGui::TextDisabled( m_state == State::LoadingScene ? "Loading the gameplay scene..." : "Entering play..." );
    }
    else if( m_state == State::Active && m_venueWait >= 0.f )
    {
        ImGui::SameLine();
        ImGui::TextDisabled( "(venue updating)" );
    }
    else if( !m_status.empty() )
    {
        ImGui::SameLine();
        ImGui::TextColored( ImVec4( 1.f, 0.5f, 0.4f, 1.f ), "%s", m_status.c_str() );
    }
}

#endif
