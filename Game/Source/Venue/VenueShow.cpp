#include "Venue/VenueShow.h"
#include "Venue/VenueLayout.h"
#include "Venue/VenueRegistry.h"
#include "Venue/VenueTiming.h"
#include "Components/Audio/AudioSource.h"
#include "Components/Animation/Sequence.h"
#include "Components/Effects/ParticleSystem.h"
#include "Components/Camera.h"
#include "Components/Graphics/PostProcess.h"
#include "Components/Lighting/Light.h"
#include "Components/Transform.h"
#include "Config/GameSettings.h"
#include "Core/CommandLine.h"
#include "Engine/World.h"
#include "Graphics/Texture.h"
#include "Materials/StandardMaterial.h"
#include "Resource/ResourceCache.h"
#include "Dementia.h"
#include "CLog.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <random>

namespace
{
    using Shape = Moonlight::MeshType;
    // The highway fades into the venue between these distances from its camera.
    constexpr float kHighwayFadeStart = 42.f;
    constexpr float kHighwayFadeEnd = 120.f;
    constexpr float kHighwayBoardOpacity = 0.6f;
    // The follow spots' floor: a front light on the band in every look.
    constexpr float kFrontFill = 0.18f;
    // The arena's floor plan behind the crowd (VenueLayout): its geometry is built here.
    using VenueLayout::kArenaDeskZ;
    using VenueLayout::kArenaStandsZ;
    using VenueLayout::kArenaTiers;
    using VenueLayout::kArenaSideTiers;
    using VenueLayout::kArenaTierDepth;
    using VenueLayout::kArenaTierRise;
    using VenueLayout::kArenaBackWallZ;
    using VenueLayout::kArenaSideStandsX;

    // VenueShow::SetOverride's venue, and what its last build came to.
    std::string& OverrideVenue()
    {
        static std::string venue;
        return venue;
    }


    std::string& OverrideOutcome()
    {
        static std::string outcome;
        return outcome;
    }


    bool& OverrideFallback()
    {
        static bool fellBack = false;
        return fellBack;
    }
}


void VenueShow::SetOverride( const std::string& inVenue )
{
    OverrideVenue() = inVenue;
    OverrideOutcome().clear();
    OverrideFallback() = false;
}


const std::string& VenueShow::GetOverride()
{
    return OverrideVenue();
}


const std::string& VenueShow::GetOverrideOutcome()
{
    return OverrideOutcome();
}


bool VenueShow::OverrideFellBack()
{
    return OverrideFallback();
}


void VenueShow::Clear()
{
    // Give the screen back to the highway's camera before the venue's goes.
    if( m_savedHighway && m_highwayCamera && m_highwayCamera->HasComponent<Camera>() )
    {
        Camera& camera = m_highwayCamera->GetComponent<Camera>();
        camera.Overlay = false;
        camera.OverlayDarkOpacity = 1.f;
        camera.SetCurrent();
        if( m_highwayCamera->HasComponent<PostProcess>() )
        {
            m_highwayCamera->GetComponent<PostProcess>().Fog = m_highwayFog;
        }
    }
    m_savedHighway = false;
    m_highwayCamera = {};
    m_fromOverride = false;
    if( m_accentPlaying ) SampleAccents( m_accentBeat );
    m_lights.Clear();
    m_director.Clear();
    m_crowd.Clear();
    m_band.Clear();
    m_lyricBoard.Clear();
    m_lyrics.Clear();
    m_accentPlaying = false;
    m_accentBeat = -10000.;
    m_captureElapsed = 0.;
    m_scene.Clear();
    m_kit.Clear();
    m_root = {};
    m_ambience = {};
    m_ambienceSettings = VenueAmbience();
    m_sceneId.clear();
    m_set.Clear();
    m_fx.Clear();
    m_hype = 0.f;
    m_lastMoment = -1000.0;
    m_lastSeconds = -1000.0;
    m_lastPlayerPeak = -1000.0;
    m_pendingMoment = 0;
    m_kick = 0.f;
    m_peaks.clear();
    m_finale = 1e9f;
    m_venue.Clear();
    m_plan = VenuePlan();
    m_beats.clear();
    m_lastStep = INT64_MIN;
    m_stepDelta = 0.f;
}


const char* VenueShow::StyleName( Style inStyle )
{
    switch( inStyle )
    {
    case Style::Arena: return "Arena";
    case Style::Club: return "Club";
    case Style::Festival: return "Festival";
    default: return "";
    }
}


void VenueShow::NextStyle()
{
    if( !m_world || !m_track || !m_highwayCamera )
    {
        return;
    }
    World& world = *m_world;
    const TrackData& track = *m_track;
    const EntityHandle highway = m_highwayCamera;
    // Arena, Club, Festival, then each venue scene the menu lists, then the arena again.
    const std::vector<VenueEntry>& venues = VenueRegistry::GetInstance().Get();
    size_t from = 0;
    if( m_sceneId.empty() && m_style != Style::Festival )
    {
        Build( world, track, highway, static_cast<int>( m_style ) + 1 );
        return;
    }
    if( !m_sceneId.empty() )
    {
        // After the scene showing (a song's own venue, or a hidden one, starts the list over).
        for( size_t i = 0; i < venues.size(); ++i )
        {
            if( venues[i].Id == m_sceneId ) from = i + 1;
        }
    }
    for( size_t i = from; i < venues.size(); ++i )
    {
        if( venues[i].Hidden ) continue;
        VenueChoice choice;
        choice.IsScene = true;
        choice.ScenePath = venues[i].ScenePath;
        choice.Id = venues[i].Id;
        choice.Reason = "F7";
        Clear();
        m_world = &world;
        m_track = &track;
        if( Wanted( track ) ) BuildChoice( world, track, highway, choice );
        return;
    }
    Build( world, track, highway, static_cast<int>( Style::Arena ) );
}


bool VenueShow::Wanted( const TrackData& inTrack ) const
{
    // A practice lesson has no show: just the highway and the click.
    return GameSettings::GetInstance().Venue > 0 && !inTrack.m_practice && !inTrack.m_calibration && !CommandLine::Has( "--no-venue" );
}


void VenueShow::Build( World& inWorld, const TrackData& inTrack, const EntityHandle& inHighwayCamera, int inStyle )
{
    Clear();
    m_world = &inWorld;
    m_track = &inTrack;
    if( !Wanted( inTrack ) )
    {
        return;
    }
    VenueChoice choice;
    if( inStyle >= 0 )
    {
        // A room asked for by name (F7 stepping through the rooms).
        choice.Style = std::clamp( inStyle, 0, static_cast<int>( Style::Count ) - 1 );
        choice.Reason = "F7";
    }
    else if( !OverrideVenue().empty() )
    {
        // The Track Editor preview's pick, resolved as --venue would be (hidden venues too).
        VenueRegistry& registry = VenueRegistry::GetInstance();
        if( registry.Get().empty() )
        {
            registry.Reload();
        }
        VenueChoiceInputs inputs;
        inputs.CommandVenue = OverrideVenue();
        inputs.SongVenues = false;
        inputs.VenueStyle = GameSettings::GetInstance().VenueStyle;
        inputs.SongHash = VenueSongHash( inTrack.m_trackName );
        inputs.Registry = &registry.Get();
        choice = ChooseVenue( inputs );
        // (ChooseVenue answers "--venue..." when the name matched; otherwise it fell through to the setting.)
        if( choice.Reason.rfind( "--venue", 0 ) != 0 )
        {
            choice.Id = OverrideVenue();
            choice.Reason = "a fallback for the editor's venue " + OverrideVenue() + ", which matches no venue id, room or .lvl path";
        }
        else
        {
            choice.Reason = "the editor's venue override";
        }
        m_fromOverride = true;
    }
    else
    {
        // --venue, --venue-style, the song's venue, the player's pick, the VenueStyle setting
        // (VenueRegistry: ChooseVenue), the same pick every time for a song.
        choice = VenueRegistry::GetInstance().ChooseForSong( inTrack );
    }
    BuildChoice( inWorld, inTrack, inHighwayCamera, choice );
}


void VenueShow::BuildChoice( World& inWorld, const TrackData& inTrack, const EntityHandle& inHighwayCamera, const VenueChoice& inChoice )
{
    VenueChoice choice = inChoice;
    if( choice.IsScene )
    {
        // The venue root first: the scene is instanced under it.
        m_kit.Begin( inWorld );
        m_root = m_kit.Group( "Venue", nullptr, VenueLayout::kVenueOrigin );
        std::string problem;
        if( m_root && m_scene.Load( inWorld, choice.ScenePath, m_root->GetComponent<Transform>(), problem ) )
        {
            m_sceneId = choice.Id;
            if( m_fromOverride )
            {
                OverrideOutcome() = "\"" + m_scene.GetMarkers().Plan.Name + "\" (" + choice.ScenePath + ")";
                OverrideFallback() = false;
            }
            INFO_FMT( "[Venues]", "Venue: scene \"%s\" (%s), chosen by %s; %d entities in the world before the show", m_scene.GetMarkers().Plan.Name.c_str(), choice.ScenePath.c_str(),
                choice.Reason.c_str(), static_cast<int>( inWorld.GetEntityCount() ) );
            if( m_ambienceWanted )
            {
                StartAmbience( choice.Ambience );
            }
            BuildShow( inWorld, inTrack, inHighwayCamera, m_scene.GetMarkers().Plan );
            return;
        }
        // Not a venue after all: the room the pick would have made without scenes.
        const VenueChoice room = VenueRegistry::GetInstance().ChooseRoomForSong( inTrack );
        YIKES_FMT( "[Venues] Venue scene %s can't be used (%s): the %s instead", choice.ScenePath.c_str(), problem.c_str(), StyleName( static_cast<Style>( std::clamp( room.Style, 0, 2 ) ) ) );
        m_scene.Clear();
        choice = room;
        choice.Reason = "a fallback for " + inChoice.Id;
        if( m_fromOverride )
        {
            OverrideOutcome() = std::string( "the " ) + StyleName( static_cast<Style>( std::clamp( room.Style, 0, 2 ) ) ) + ": " + inChoice.ScenePath + " can't be a venue (" + problem + ")";
            OverrideFallback() = true;
        }
    }
    else if( m_fromOverride )
    {
        const std::string room = std::string( "the " ) + StyleName( static_cast<Style>( std::clamp( choice.Style, 0, static_cast<int>( Style::Count ) - 1 ) ) );
        OverrideFallback() = choice.Reason.rfind( "a fallback", 0 ) == 0;
        OverrideOutcome() = OverrideFallback() ? room + ": " + choice.Id + " matches no venue" : room;
    }
    const int style = std::clamp( choice.Style, 0, static_cast<int>( Style::Count ) - 1 );
    VenuePlan plan = VenuePlan::ForStyle( style );
    if( CommandLine::Has( "--venue-plan-test" ) )
    {
        // A plan unlike the rooms': no bassist or keyboard player, the drummer and kit moved
        // down onto the deck in the bassist's place and turned in toward the middle. Everything
        // of a member should follow their spot, and nothing should be left of the missing.
        plan.Members[VenueData::Bass].Present = false;
        plan.Members[VenueData::Keys].Present = false;
        plan.Members[VenueData::Drums].Feet = Vector3( 3.6f, plan.Stage.Height, 3.4f );
        plan.Members[VenueData::Drums].Yaw = 215.f;
        const Vector3& feet = plan.Members[VenueData::Drums].Feet;
        BRUH_FMT( "Venue: plan test: no bass or keys, the drummer at (%.2f, %.2f, %.2f) turned to %.0f degrees", feet.x, feet.y, feet.z, plan.Members[VenueData::Drums].Yaw );
    }
    INFO_FMT( "[Venues]", "Venue: the %s, chosen by %s; %d entities in the world before the show", StyleName( static_cast<Style>( style ) ), choice.Reason.c_str(),
        static_cast<int>( inWorld.GetEntityCount() ) );
    BuildShow( inWorld, inTrack, inHighwayCamera, plan );
}


void VenueShow::Build( World& inWorld, const TrackData& inTrack, const EntityHandle& inHighwayCamera, const VenuePlan& inPlan )
{
    // (By value before Clear: the plan may be this show's own, GetPlan.)
    const VenuePlan plan = inPlan;
    Clear();
    m_world = &inWorld;
    m_track = &inTrack;
    if( !Wanted( inTrack ) )
    {
        return;
    }
    BuildShow( inWorld, inTrack, inHighwayCamera, plan );
}


bool VenueShow::BuildAround( World& inWorld, const TrackData& inTrack, const std::vector<EntityHandle>& inSceneRoots, std::string& outProblem )
{
    Clear();
    m_world = &inWorld;
    m_track = &inTrack;
    // The scene stays where it was authored: venue space is world space.
    m_kit.Begin( inWorld );
    m_root = m_kit.Group( "Venue", nullptr, Vector3( 0.f, 0.f, 0.f ) );
    if( !m_root || !m_scene.Adopt( inSceneRoots, m_root->GetComponent<Transform>(), outProblem ) )
    {
        Clear();
        return false;
    }
    m_sceneId = "(open scene)";
    INFO_FMT( "[Venues]", "Venue: the open scene \"%s\", built in place; %d entities in the world before the show", m_scene.GetMarkers().Plan.Name.c_str(),
        static_cast<int>( inWorld.GetEntityCount() ) );
    BuildShow( inWorld, inTrack, EntityHandle(), m_scene.GetMarkers().Plan );
    return true;
}


void VenueShow::BuildShow( World& inWorld, const TrackData& inTrack, const EntityHandle& inHighwayCamera, const VenuePlan& inPlan )
{
    const int setting = GameSettings::GetInstance().Venue;
    m_plan = inPlan;
    m_style = static_cast<Style>( std::clamp( inPlan.Style, 0, static_cast<int>( Style::Count ) - 1 ) );
    m_venue = inTrack.m_venue;
    m_beats = inTrack.m_beats;
    m_bpm = inTrack.m_bpm > 30 ? static_cast<float>( inTrack.m_bpm ) : 120.f;
    if( !m_root )
    {
        // (A scene venue's root is already up, the scene under it.)
        m_kit.Begin( inWorld );
        m_root = m_kit.Group( "Venue", nullptr, VenueLayout::kVenueOrigin );
    }
    if( !m_root )
    {
        return;
    }
    Transform& root = m_root->GetComponent<Transform>();
    BuildStage( root );
    // Karaoke on the plan's lyric band (the LED wall's lower part, above the drummer's head).
    m_lyrics.Build( m_venue.m_lyrics, m_venue.m_vocalPhrases, m_venue.m_vocalNotes );
    if( GameSettings::GetInstance().LyricsInVenue() && m_plan.Lyrics.Present )
    {
        m_lyricBoard.Build( m_kit, root, m_plan.Lyrics.Centre, m_plan.Lyrics.Width, m_lyrics );
    }

    float lastNote = 0.f;
    for( const NoteData& note : inTrack.m_noteData ) lastNote = std::max( lastNote, note.m_triggerTime );
    m_band.Build( m_kit, &root, m_plan, m_venue, inTrack.m_noteData, m_beats, m_bpm );
    if( setting >= 2 && m_plan.BuildCrowd )
    {
        // Each room holds a different crowd: the plan's posed areas' heads.
        int count = 0;
        for( const VenuePlan::CrowdArea& area : m_plan.Crowd )
        {
            if( area.Type == VenuePlan::CrowdArea::Kind::Posed ) count += std::max( area.Heads, 0 );
        }
        const int posed = CommandLine::GetInt( "--crowd-size", count );
        // The crowd is everyone the band isn't.
        m_crowd.SetModels( m_band.SpareModels() );
        m_crowd.Build( m_kit, &root, m_plan, m_venue, m_beats, m_bpm, posed );
        // --crowd-size trims the back of the house in proportion.
        FillHouse( root, count > 0 ? std::clamp( static_cast<float>( posed ) / static_cast<float>( count ), 0.f, 4.f ) : 1.f );
    }
    m_director.Build( inWorld, m_plan, m_venue, m_beats, m_bpm, std::max( lastNote + 4.f, inTrack.m_duration ), GameSettings::GetInstance().VenueCamera == 1, &m_band );
    VenueKit* kit = &m_kit;
    const VenueScene::Markers* scene = m_scene.IsLoaded() ? &m_scene.GetMarkers() : nullptr;
    if( m_plan.BuildRig || ( scene && !scene->Lights.empty() ) )
    {
        m_lights.Build( inWorld, &root, m_director.MainCamera(), inTrack, m_plan,
            [kit]( const Vector3& inPosition, const Vector3& inScale, const Vector3& inColor, const Vector3& inEmissive, Transform* inParent ) { return kit->Piece( Shape::Cube, inPosition, inScale, inColor, inParent, inEmissive, false ); },
            []( const EntityHandle& inTarget, const Vector3& inColor, const Vector3& inEmissive ) { VenueKit::SetColor( inTarget, inColor, inEmissive ); } );
    }
    if( scene )
    {
        // The scene's own show lights join the rig (or are the rig).
        for( const VenueScene::ShowLight& light : scene->Lights )
        {
            m_lights.AdoptFixture( light.Light, light.Role, light.Group );
        }
    }
    if( scene && !m_plan.BuildRig && !scene->HasDirectional )
    {
        // A scene lit only by its own lights, with no sun or moon of its own: a key light, soft
        // under the show and the house light without one. Without any directional the renderer
        // would light the room with a daylight sun.
        if( EntityHandle key = m_kit.Group( "VenueKeyLight", &root ) )
        {
            key->GetComponent<Transform>().LookDirection( Vector3( 0.15f, -0.8f, 0.6f ).Normalized() );
            Light& light = key->AddComponent<Light>();
            light.LightType = Moonlight::LightType::Directional;
            light.DirectionalSource = Moonlight::DirectionalSource::Manual;
            light.Color = m_lights.IsActive() ? Vector3( 0.85f, 0.9f, 1.f ) : Vector3( 1.f, 0.92f, 0.8f );
            light.Intensity = m_lights.IsActive() ? 2.f : 7.f;
            light.CastShadows = false;
        }
    }
    else if( !scene && !m_lights.IsActive() )
    {
        // Stage Lights off: no rig, but a soft house light so the band still reads. Without any
        // directional the renderer would light the room with a daylight sun.
        if( EntityHandle key = m_kit.Group( "VenueKeyLight", &root ) )
        {
            key->GetComponent<Transform>().LookDirection( Vector3( 0.15f, -0.8f, 0.6f ).Normalized() );
            Light& light = key->AddComponent<Light>();
            light.LightType = Moonlight::LightType::Directional;
            light.DirectionalSource = Moonlight::DirectionalSource::Manual;
            light.Color = Vector3( 1.f, 0.92f, 0.8f );
            light.Intensity = 7.f;
            // No shadows: every room has a roof or a canopy over the stage, and a shadowed
            // house light leaves the band in the dark.
            light.CastShadows = false;
        }
    }
    m_director.SetRoom( m_plan.Bounds );
    // The chart's own peaks: where each chorus or intense passage starts. The last is the finale.
    std::string mood;
    for( const TimedCueData& crowd : m_venue.m_crowd )
    {
        if( crowd.m_name == "intense" && mood != "intense" ) m_peaks.push_back( crowd.m_time );
        if( crowd.m_name == "intense" || crowd.m_name == "normal" || crowd.m_name == "mellow" || crowd.m_name == "realtime" ) mood = crowd.m_name;
    }
    for( const TimedCueData& section : m_venue.m_sections )
    {
        if( VenueTiming::Contains( section.m_name, "chorus" ) ) m_peaks.push_back( section.m_time );
    }
    std::sort( m_peaks.begin(), m_peaks.end() );
    // Peaks that crowd each other (a chorus that's also marked intense) count once.
    std::vector<float> peaks;
    for( float peak : m_peaks )
    {
        if( peaks.empty() || peak - peaks.back() > 12.f ) peaks.push_back( peak );
    }
    m_peaks = peaks;
    m_finale = m_peaks.size() >= 2 ? m_peaks.back() : 1e9f;
    // Less haze out of doors, a touch more in a club.
    m_lights.SetHazeScale( m_plan.HazeScale );
    if( m_plan.Bounds.Outdoor )
    {
        // Out of doors: a night sky.
        if( const EntityHandle& camera = m_director.MainCamera() )
        {
            Camera& sky = camera->GetComponent<Camera>();
            sky.ClearType = Moonlight::ClearColorType::Procedural;
            sky.ProceduralSky.Time = m_plan.SkyTime;
            sky.ProceduralSky.StarBrightness = 2.f;
            sky.ProceduralSky.MoonPhase = 0.5f;
            sky.ProceduralSky.MoonBrightness = m_plan.MoonBrightness;
            sky.ProceduralSky.CloudCoverage = 0.25f;
            if( camera->HasComponent<PostProcess>() )
            {
                camera->GetComponent<PostProcess>().FogMaxOpacity = 0.55f;
            }
        }
    }
    if( scene )
    {
        // A scene's look (VenueInfo): the colour behind it all, which lights the room a little
        // indoors, and the light its haze scatters.
        if( const EntityHandle& camera = m_director.MainCamera() )
        {
            camera->GetComponent<Camera>().ClearColor = m_plan.Background;
            if( camera->HasComponent<PostProcess>() )
            {
                camera->GetComponent<PostProcess>().FogColor = m_plan.FogColor;
            }
        }
    }

    // The highway draws over the venue from now on, fading into it toward its far end instead of
    // into black fog.
    m_highwayCamera = inHighwayCamera;
    if( m_highwayCamera && m_highwayCamera->HasComponent<Camera>() )
    {
        if( m_highwayCamera->HasComponent<PostProcess>() )
        {
            m_highwayFog = m_highwayCamera->GetComponent<PostProcess>().Fog;
        }
        m_savedHighway = true;
        m_highwayAlone = false;
        ApplyPresentation();
    }
    if( CommandLine::Has( "--highway-log" ) )
    {
        BRUH_FMT( "Venue: %d camera cuts, %d looks, crowd of %d", static_cast<int>( m_director.CutCount() ), static_cast<int>( m_venue.m_postFx.size() ), static_cast<int>( m_crowd.Size() ) );
    }
}


void VenueShow::SetPresentation( Presentation inPresentation )
{
    if( m_presentation != inPresentation )
    {
        m_presentation = inPresentation;
        ApplyPresentation();
    }
}


void VenueShow::ApplyPresentation()
{
    if( !m_savedHighway || !m_highwayCamera || !m_highwayCamera->HasComponent<Camera>() )
    {
        return;
    }
    Camera& camera = m_highwayCamera->GetComponent<Camera>();
    PostProcess* post = m_highwayCamera->HasComponent<PostProcess>() ? &m_highwayCamera->GetComponent<PostProcess>() : nullptr;
    if( m_presentation == Presentation::HighwayOnly )
    {
        // The highway's camera takes the screen back, as it has it without a venue.
        camera.Overlay = false;
        camera.OverlayDarkOpacity = 1.f;
        camera.SetCurrent();
        if( post )
        {
            post->Fog = m_highwayFog;
        }
        m_highwayAlone = true;
        return;
    }
    camera.Overlay = true;
    camera.OverlayFadeStart = kHighwayFadeStart;
    camera.OverlayFadeEnd = kHighwayFadeEnd;
    // The dark board lets the stage show through; notes, lines and pads stay solid.
    camera.OverlayDarkOpacity = kHighwayBoardOpacity;
    if( m_presentation == Presentation::VenueOnly || CommandLine::Has( "--venue-only" ) )
    {
        // Fade the whole highway out, to frame the venue.
        camera.OverlayFadeStart = 0.f;
        camera.OverlayFadeEnd = 0.001f;
    }
    if( post )
    {
        post->Fog = false;
    }
    if( m_highwayAlone )
    {
        m_highwayAlone = false;
        if( const EntityHandle& main = m_director.MainCamera() )
        {
            main->GetComponent<Camera>().SetCurrent();
        }
    }
}


void VenueShow::BuildScreen( Transform& inRoot, const VenuePlan::Screen& inScreen )
{
    // A frame, and a plane facing the crowd whose emission is the feed camera's image.
    const Vector3& centre = inScreen.Centre;
    const Vector3 size( inScreen.Width, inScreen.Height, 0.f );
    const float yaw = inScreen.Yaw;
    const char* texture = inScreen.Source == VenuePlan::Screen::Feed::Stage ? Director::kFeedTexture : Director::kProgramTexture;
    // The frame sits behind the picture, turned with it.
    const float turn = yaw * 3.14159265f / 180.f;
    const Vector3 behind( 0.08f * std::sin( turn ), 0.f, 0.08f * std::cos( turn ) );
    EntityHandle frame = m_kit.Box( centre + behind, Vector3( size.x + 0.3f, size.y + 0.3f, 0.14f ), Vector3( 0.02f, 0.02f, 0.02f ), &inRoot );
    if( frame ) frame->GetComponent<Transform>().SetRotation( Vector3( 0.f, yaw, 0.f ) );
    EntityHandle screen = m_kit.Piece( Shape::Plane, centre, Vector3( size.x, 1.f, size.y ), Vector3( 0.f, 0.f, 0.f ), &inRoot, Vector3( 1.f, 1.f, 1.f ) );
    if( !screen )
    {
        return;
    }
    // The plane lies in XZ facing +y: stand it up facing the crowd (-z).
    screen->GetComponent<Transform>().SetRotation( Quaternion::FromEulerDegrees( Vector3( 0.f, yaw, 0.f ) ) * Quaternion::FromEulerDegrees( Vector3( -90.f, 0.f, 0.f ) ) );
    if( StandardMaterial* material = VenueKit::MaterialOf( screen ) )
    {
        material->SetTexture( Moonlight::TextureType::Emissive, ResourceCache::GetInstance().Get<Moonlight::Texture>( Path( texture ) ) );
        material->SetEmissiveColor( Vector3( 1.f, 1.f, 1.f ) );
        material->SetEmissiveIntensity( inScreen.Emissive );
        material->SetRoughness( 0.9f );
        material->SetTiling( Vector2( 1.f, -1.f ) );
        material->SetOffset( Vector2( 0.f, 1.f ) );
    }
}


void VenueShow::BuildStage( Transform& inRoot )
{
    const VenuePlan::StageDims& stage = m_plan.Stage;
    const Vector3 black( 0.015f, 0.015f, 0.018f );
    const Vector3 deckColor( 0.05f, 0.05f, 0.055f );
    // The stage, the same in every room: the deck, the drum riser, the back wall with its LED
    // wall and the speaker stacks. StageSet dresses it and StageFx arms it.
    if( m_plan.BuildStage )
    {
        m_kit.Box( Vector3( 0.f, stage.Height * 0.5f, stage.Depth * 0.5f + 0.3f ), Vector3( stage.HalfWidth * 2.f, stage.Height, stage.Depth + 0.6f ), deckColor, &inRoot );
        m_kit.Box( Vector3( 0.f, stage.Height * 0.5f, -0.02f ), Vector3( stage.HalfWidth * 2.f, stage.Height, 0.06f ), black, &inRoot );
        m_kit.Box( Vector3( 0.f, stage.Height + stage.RiserHeight * 0.5f, stage.RiserZ + 0.5f ), Vector3( 3.4f, stage.RiserHeight, 2.8f ), Vector3( 0.06f, 0.06f, 0.07f ), &inRoot );
        m_kit.Box( Vector3( 0.f, 6.f, stage.BackWallZ + 0.2f ), Vector3( 24.f, 12.f, 0.4f ), black, &inRoot );
        for( float side : { -1.f, 1.f } )
        {
            for( int box = 0; box < 3; ++box )
            {
                const Vector3 centre( side * ( stage.HalfWidth + 1.1f ), 0.75f + box * 1.45f, 1.2f );
                m_kit.Box( centre, Vector3( 1.8f, 1.4f, 1.2f ), Vector3( 0.02f, 0.02f, 0.02f ), &inRoot );
                m_kit.Box( centre + Vector3( 0.f, 0.f, -0.61f ), Vector3( 1.6f, 1.2f, 0.02f ), Vector3( 0.05f, 0.05f, 0.055f ), &inRoot );
            }
        }
    }
    // The LED wall and any other screens the plan has.
    for( const VenuePlan::Screen& screen : m_plan.Screens )
    {
        BuildScreen( inRoot, screen );
    }
    // The truss, backline, dressing and LED pieces (StageSet), and the effects (StageFx).
    uint32_t seed = 2166136261u;
    if( m_track )
    {
        for( char c : m_track->m_trackName ) seed = ( seed ^ static_cast<uint8_t>( c ) ) * 16777619u;
    }
    if( m_plan.BuildSet )
    {
        const bool keys = !m_venue.m_keysStrums.empty() || !m_venue.m_bandStates[VenueData::Keys].empty();
        m_set.Build( m_kit, inRoot, m_plan, keys && m_plan.HasMember( VenueData::Keys ), seed );
    }
    if( m_plan.BuildFx )
    {
        m_fx.Build( m_kit, inRoot, m_plan, m_venue );
    }
    if( m_plan.BuildRoom )
    {
        switch( m_style )
        {
        case Style::Club: BuildClub( inRoot ); break;
        case Style::Festival: BuildFestival( inRoot ); break;
        default: BuildArena( inRoot ); break;
        }
    }
}


void VenueShow::BuildArena( Transform& inRoot )
{
    // A big dark hall: the floor full to the mixing desk and beyond, stands rising at the back
    // and along the sides, a roof with the rigging grid, PA hangs either side of the stage.
    const Vector3 black( 0.015f, 0.015f, 0.018f );
    const Vector3 metal( 0.18f, 0.18f, 0.2f );
    const Vector3 seating( 0.035f, 0.03f, 0.04f );
    const Vector3 aisleGlow( 0.5f, 0.28f, 0.08f );
    const float back = kArenaBackWallZ;
    const float length = m_plan.Stage.BackWallZ + 1.f - back;
    const float middle = ( m_plan.Stage.BackWallZ + 1.f + back ) * 0.5f;
    m_kit.Box( Vector3( 0.f, -0.05f, middle ), Vector3( 70.f, 0.1f, length + 4.f ), Vector3( 0.03f, 0.03f, 0.035f ), &inRoot );
    m_kit.Box( Vector3( 0.f, 11.f, m_plan.Stage.BackWallZ + 0.6f ), Vector3( 70.f, 22.f, 0.4f ), black, &inRoot );
    m_kit.Box( Vector3( 0.f, 11.f, back - 0.2f ), Vector3( 70.f, 22.f, 0.4f ), black, &inRoot );
    // The roof, and the grid the house rig hangs from.
    m_kit.Box( Vector3( 0.f, 22.f, middle ), Vector3( 46.f, 0.4f, length ), Vector3( 0.012f, 0.012f, 0.014f ), &inRoot );
    for( float z = -2.f; z > back + 2.f; z -= 9.f )
    {
        m_kit.Box( Vector3( 0.f, 19.5f, z ), Vector3( 40.f, 0.35f, 0.35f ), metal * 0.6f, &inRoot );
    }
    for( float x : { -12.f, 0.f, 12.f } )
    {
        m_kit.Box( Vector3( x, 19.5f, middle - 4.f ), Vector3( 0.35f, 0.35f, length - 14.f ), metal * 0.6f, &inRoot );
    }
    // The back stands: tiers rising to the back wall, an aisle light along each step.
    for( int tier = 0; tier < kArenaTiers; ++tier )
    {
        const float top = kArenaTierRise * static_cast<float>( tier + 1 );
        const float z = kArenaStandsZ - kArenaTierDepth * ( static_cast<float>( tier ) + 0.5f );
        m_kit.Box( Vector3( 0.f, top * 0.5f, z ), Vector3( 43.f, top, kArenaTierDepth ), seating, &inRoot );
        m_kit.Box( Vector3( 0.f, top + 0.01f, z + kArenaTierDepth * 0.5f - 0.05f ), Vector3( 43.f, 0.03f, 0.05f ), Vector3( 0.f, 0.f, 0.f ), &inRoot, aisleGlow );
    }
    m_kit.Box( Vector3( 0.f, kArenaTierRise * kArenaTiers + 0.55f, back + 0.5f ), Vector3( 43.f, 1.1f, 0.2f ), metal * 0.4f, &inRoot );
    for( float side : { -1.f, 1.f } )
    {
        m_kit.Box( Vector3( side * 22.f, 11.f, middle ), Vector3( 0.5f, 22.f, length + 4.f ), black, &inRoot );
        m_kit.Box( Vector3( side * 14.f, 4.2f, 2.3f ), Vector3( 0.2f, 2.8f, 0.2f ), metal, &inRoot );
        // The side stands, from beside the stage back to the back stands.
        for( int tier = 0; tier < kArenaSideTiers; ++tier )
        {
            const float top = kArenaTierRise * static_cast<float>( tier + 1 );
            const float x = side * ( kArenaSideStandsX + kArenaTierDepth * ( static_cast<float>( tier ) + 0.5f ) );
            const float z0 = kArenaStandsZ;
            const float z1 = -3.f;
            m_kit.Box( Vector3( x, top * 0.5f, ( z0 + z1 ) * 0.5f ), Vector3( kArenaTierDepth, top, z1 - z0 ), seating, &inRoot );
            m_kit.Box( Vector3( x - side * ( kArenaTierDepth * 0.5f - 0.05f ), top + 0.01f, ( z0 + z1 ) * 0.5f ), Vector3( 0.05f, 0.03f, z1 - z0 ), Vector3( 0.f, 0.f, 0.f ), &inRoot, aisleGlow );
        }
        // PA hangs either side of the stage.
        m_kit.Box( Vector3( side * 11.5f, 11.f, -0.4f ), Vector3( 1.2f, 4.6f, 1.1f ), black, &inRoot );
        m_kit.Box( Vector3( side * 11.5f, 16.f, -0.4f ), Vector3( 0.06f, 5.4f, 0.06f ), metal, &inRoot );
        // Exit signs over the side stands.
        m_kit.Box( Vector3( side * 21.7f, 4.6f, -20.f ), Vector3( 0.05f, 0.3f, 0.8f ), Vector3( 0.f, 0.f, 0.f ), &inRoot, Vector3( 0.1f, 2.f, 0.3f ) );
        m_kit.Box( Vector3( side * 9.f, kArenaTierRise * kArenaTiers + 2.f, back + 0.05f ), Vector3( 0.8f, 0.3f, 0.05f ), Vector3( 0.f, 0.f, 0.f ), &inRoot, Vector3( 0.1f, 2.f, 0.3f ) );
    }
    // Front of house: the mixing desk on its riser in the middle of the floor.
    m_kit.Box( Vector3( 0.f, 0.45f, kArenaDeskZ ), Vector3( 6.f, 0.9f, 4.f ), Vector3( 0.05f, 0.05f, 0.055f ), &inRoot );
    m_kit.Box( Vector3( 0.f, 1.35f, kArenaDeskZ + 0.6f ), Vector3( 4.2f, 0.9f, 1.f ), Vector3( 0.06f, 0.06f, 0.065f ), &inRoot );
    m_kit.Box( Vector3( 0.f, 1.81f, kArenaDeskZ + 0.6f ), Vector3( 4.f, 0.02f, 0.9f ), Vector3( 0.f, 0.f, 0.f ), &inRoot, Vector3( 0.15f, 0.35f, 0.5f ) );
    for( float x : { -1.2f, 1.2f } )
    {
        m_kit.Box( Vector3( x, 2.2f, kArenaDeskZ + 1.f ), Vector3( 0.9f, 0.55f, 0.04f ), Vector3( 0.f, 0.f, 0.f ), &inRoot, Vector3( 0.3f, 0.6f, 1.f ) );
    }
    BuildArenaDetail( inRoot );
}


void VenueShow::BuildArenaDetail( Transform& inRoot )
{
    const Vector3 steel( 0.22f, 0.25f, 0.29f );
    const Vector3 charcoal( 0.025f, 0.032f, 0.045f );
    const Vector3 dark( 0.f, 0.f, 0.f );
    const Vector3 cyan( 0.06f, 0.75f, 1.2f );
    const Vector3 amber( 1.2f, 0.34f, 0.06f );
    // Static accents stay modest: the chart-controlled washes remain the brightest elements.
    const auto box = [&]( const Vector3& p, const Vector3& size, const Vector3& color ) {
        return m_kit.Box( p, size, color, &inRoot );
    };
    const auto glow = [&]( const Vector3& p, const Vector3& size, const Vector3& color ) {
        return m_kit.Box( p, size, dark, &inRoot, color );
    };
    const auto beam = [&]( const Vector3& a, const Vector3& b, float width ) {
        const Vector3 delta = b - a;
        EntityHandle piece = box( ( a + b ) * 0.5f, Vector3( width, width, delta.Length() ), steel );
        if( piece ) piece->GetComponent<Transform>().LookDirection( delta.Normalized() );
    };

    // Twin portal frames and staggered LED fins give the stage a recognizable silhouette,
    // leaving the video wall, lyrics and all performer positions clear.
    for( float side : { -1.f, 1.f } )
    {
        for( int fin = 0; fin < 3; ++fin )
        {
            const float x = side * ( 6.8f + fin * 1.05f );
            const float height = 8.f - fin * 1.2f;
            box( Vector3( x, 1.2f + height * 0.5f, 10.05f ), Vector3( 0.65f, height, 0.38f ), charcoal );
            for( int cell = 0; cell < 8; ++cell )
            {
                glow( Vector3( x, 1.4f + cell * ( height - 0.4f ) / 8.f, 9.84f ),
                    Vector3( 0.48f, ( height - 0.4f ) / 8.f - 0.09f, 0.035f ), cell % 3 == 0 ? amber : cyan * 0.45f );
            }
        }
        box( Vector3( side * 10.5f, 6.4f, 7.8f ), Vector3( 0.65f, 12.8f, 0.7f ), charcoal );
        glow( Vector3( side * 10.5f, 6.4f, 7.42f ), Vector3( 0.08f, 12.4f, 0.04f ), cyan );
        // Pleated wing curtains behind the side-screen towers.
        for( int fold = 0; fold < 11; ++fold )
            box( Vector3( side * ( 12.f + fold * 0.75f ), 5.4f, 8.8f + ( fold % 2 ) * 0.18f ),
                Vector3( 0.72f, 10.8f, 0.35f ), fold % 2 ? Vector3( 0.055f, 0.025f, 0.035f ) : charcoal );
        // Real speaker cones and cases make the wings read as a working touring stage.
        for( int stack = 0; stack < 3; ++stack )
            m_kit.Prop( "Assets/Models/Venue/Speaker.obj", Vector3( side * 8.2f, 1.2f + stack * 1.05f, 5.8f ), 1.f, 180.f, &inRoot );
        for( int crate = 0; crate < 3; ++crate )
            m_kit.Prop( "Assets/Models/Venue/RoadCase.obj", Vector3( side * ( 12.2f + crate * 1.4f ), 0.f, 5.2f + ( crate % 2 ) * 1.1f ), 1.f, side * 12.f, &inRoot );
        // Stage access stairs, with warm tread markings.
        for( int step = 0; step < 4; ++step )
        {
            const float height = ( step + 1 ) * 0.3f;
            box( Vector3( side * 9.8f, height * 0.5f, 2.1f + step * 0.4f ), Vector3( 1.4f, height, 0.4f ), steel * 0.45f );
            glow( Vector3( side * 9.8f, height + 0.01f, 1.92f + step * 0.4f ), Vector3( 1.25f, 0.025f, 0.035f ), amber * 0.4f );
        }
        // A concourse fascia and acoustic wall bays give the seating bowl a human scale.
        box( Vector3( side * 21.45f, 7.2f, -18.f ), Vector3( 0.5f, 0.9f, 32.f ), charcoal );
        glow( Vector3( side * 21.16f, 6.8f, -18.f ), Vector3( 0.04f, 0.06f, 32.f ), cyan * 0.55f );
        for( int bay = 0; bay < 6; ++bay )
        {
            const float z = -5.f - bay * 6.6f;
            box( Vector3( side * 21.55f, 13.4f, z ), Vector3( 0.45f, 10.f, 0.45f ), steel * 0.55f );
            box( Vector3( side * 21.65f, 12.7f, z - 2.6f ), Vector3( 0.15f, 7.f, 4.2f ), Vector3( 0.065f, 0.075f, 0.1f ) );
            glow( Vector3( side * 21.5f, 12.7f, z - 0.6f ), Vector3( 0.04f, 6.6f, 0.07f ), cyan * 0.35f );
        }
        // Segmented PA grilles, rigging cables and spreader bars on the existing hangs.
        for( int cabinet = 0; cabinet < 8; ++cabinet )
            box( Vector3( side * 11.5f, 8.85f + cabinet * 0.56f, -0.97f ), Vector3( 1.08f, 0.48f, 0.08f ), steel * 0.32f );
        box( Vector3( side * 11.5f, 13.5f, -0.4f ), Vector3( 1.6f, 0.15f, 1.4f ), steel );
    }
    box( Vector3( 0.f, 12.8f, 7.8f ), Vector3( 21.65f, 0.65f, 0.7f ), charcoal );
    glow( Vector3( 0.f, 12.8f, 7.42f ), Vector3( 21.f, 0.08f, 0.04f ), cyan );

    // Open web roof trusses: depth and diagonal members instead of isolated solid bars.
    for( float z : { -2.f, -11.f, -20.f, -29.f, -38.f } )
    {
        box( Vector3( 0.f, 18.1f, z ), Vector3( 42.f, 0.13f, 0.13f ), steel );
        for( int bay = 0; bay < 14; ++bay )
        {
            const float x = -21.f + bay * 3.f;
            beam( Vector3( x, 18.1f, z ), Vector3( x + 1.5f, 19.5f, z ), 0.1f );
            beam( Vector3( x + 1.5f, 19.5f, z ), Vector3( x + 3.f, 18.1f, z ), 0.1f );
        }
    }
    // Rear fascia, with vertical breaks echoing the stage's LED fins.
    box( Vector3( 0.f, 8.f, kArenaBackWallZ + 0.3f ), Vector3( 43.f, 1.3f, 0.25f ), charcoal );
    glow( Vector3( 0.f, 7.38f, kArenaBackWallZ + 0.45f ), Vector3( 43.f, 0.06f, 0.04f ), cyan * 0.55f );
    for( float x : { -18.f, -12.f, -6.f, 0.f, 6.f, 12.f, 18.f } )
    {
        box( Vector3( x, 13.f, kArenaBackWallZ + 0.3f ), Vector3( 3.6f, 6.f, 0.25f ), charcoal );
        glow( Vector3( x - 1.7f, 13.f, kArenaBackWallZ + 0.45f ), Vector3( 0.07f, 5.8f, 0.04f ), amber * 0.45f );
    }
    // FOH railings stay inside the crowd's existing KeepClear rectangle.
    for( float side : { -1.f, 1.f } )
    {
        beam( Vector3( side * 2.9f, 1.9f, kArenaDeskZ - 1.8f ), Vector3( side * 2.9f, 1.9f, kArenaDeskZ + 1.8f ), 0.07f );
        for( float z : { -1.8f, 0.f, 1.8f } )
            box( Vector3( side * 2.9f, 1.4f, kArenaDeskZ + z ), Vector3( 0.07f, 1.f, 0.07f ), steel );
        m_kit.Prop( "Assets/Models/Venue/RoadCase.obj", Vector3( side * 2.f, 0.9f, kArenaDeskZ - 1.f ), 0.8f, 0.f, &inRoot );
    }
    for( int channel = 0; channel < 16; ++channel )
    {
        const float x = -1.8f + channel * 0.24f;
        box( Vector3( x, 1.83f, kArenaDeskZ + 0.55f ), Vector3( 0.025f, 0.02f, 0.55f ), charcoal );
        glow( Vector3( x, 1.85f, kArenaDeskZ + 0.35f + ( channel % 4 ) * 0.1f ), Vector3( 0.09f, 0.025f, 0.045f ), channel % 3 == 0 ? amber : cyan );
    }
}


void VenueShow::FillHouse( Transform& inRoot, float inScale )
{
    // The back of the house: cheap figures everywhere the posed crowd doesn't reach, so no shot
    // finds an empty floor behind the front rows. The floor kept clear first (a desk, the aisles,
    // the towers' feet), then the plan's mobs in turn.
    const auto cap = [inScale]( int inCount ) { return static_cast<int>( static_cast<float>( inCount ) * inScale ); };
    for( const VenuePlan::CrowdArea& area : m_plan.Crowd )
    {
        if( area.Type == VenuePlan::CrowdArea::Kind::Clear ) m_crowd.KeepClear( area.MinX, area.MaxX, area.MinZ, area.MaxZ );
    }
    for( const VenuePlan::CrowdArea& area : m_plan.Crowd )
    {
        if( area.Type == VenuePlan::CrowdArea::Kind::Mob ) m_crowd.AddMob( m_kit, &inRoot, area, cap( area.Heads ) );
    }
}


void VenueShow::BuildClub( Transform& inRoot )
{
    // A sweaty club: brick walls close in, a low ceiling, neon on the walls and a bar at the back.
    const Vector3 brick( 0.16f, 0.06f, 0.045f );
    const Vector3 ceiling( 0.03f, 0.03f, 0.03f );
    m_kit.Box( Vector3( 0.f, -0.05f, -3.f ), Vector3( 28.f, 0.1f, 30.f ), Vector3( 0.06f, 0.04f, 0.03f ), &inRoot );
    m_kit.Box( Vector3( 0.f, 10.6f, -3.f ), Vector3( 28.f, 0.3f, 30.f ), ceiling, &inRoot );
    m_kit.Box( Vector3( 0.f, 5.f, -17.f ), Vector3( 28.f, 10.f, 0.4f ), brick, &inRoot );
    for( float side : { -1.f, 1.f } )
    {
        m_kit.Box( Vector3( side * 12.8f, 5.f, -3.f ), Vector3( 0.4f, 10.f, 30.f ), brick, &inRoot );
        // Neon: a zigzag and a ring of tubes on each side wall.
        const Vector3 neon = side < 0.f ? Vector3( 3.f, 0.25f, 2.2f ) : Vector3( 0.25f, 2.2f, 3.f );
        for( int i = 0; i < 4; ++i )
        {
            EntityHandle tube = m_kit.Box( Vector3( side * 12.55f, 5.f + ( i % 2 ) * 0.5f, -6.f + i * 0.9f ), Vector3( 0.06f, 0.08f, 1.1f ), Vector3( 0.f, 0.f, 0.f ), &inRoot, neon );
            if( tube ) tube->GetComponent<Transform>().SetRotation( Vector3( ( i % 2 == 0 ? 30.f : -30.f ), 0.f, 0.f ) );
        }
        for( int i = 0; i < 8; ++i )
        {
            const float angle = i * 3.14159265f / 4.f;
            EntityHandle tube = m_kit.Box( Vector3( side * 12.55f, 5.2f + std::sin( angle ) * 0.9f, -11.f + std::cos( angle ) * 0.9f ), Vector3( 0.06f, 0.08f, 0.7f ), Vector3( 0.f, 0.f, 0.f ), &inRoot, side < 0.f ? Vector3( 0.3f, 2.5f, 1.f ) : Vector3( 3.f, 1.2f, 0.2f ) );
            if( tube ) tube->GetComponent<Transform>().SetRotation( Vector3( -angle * 180.f / 3.14159265f, 0.f, 0.f ) );
        }
    }
    // The bar along the back wall, its shelf of bottles lit from below.
    m_kit.Box( Vector3( 0.f, 0.55f, -15.6f ), Vector3( 14.f, 1.1f, 0.8f ), Vector3( 0.12f, 0.06f, 0.03f ), &inRoot );
    m_kit.Box( Vector3( 0.f, 1.12f, -15.2f ), Vector3( 14.f, 0.03f, 0.05f ), Vector3( 0.f, 0.f, 0.f ), &inRoot, Vector3( 2.f, 1.f, 0.3f ) );
    for( int i = 0; i < 24; ++i )
    {
        const float x = -6.5f + i * 0.56f;
        const Vector3 glass = i % 3 == 0 ? Vector3( 0.6f, 0.4f, 0.1f ) : i % 3 == 1 ? Vector3( 0.1f, 0.4f, 0.15f ) : Vector3( 0.5f, 0.5f, 0.55f );
        m_kit.Piece( Shape::Cylinder, Vector3( x, 2.2f, -16.6f ), Vector3( 0.12f, 0.36f, 0.12f ), glass, &inRoot, glass * 0.6f );
    }
    m_kit.Box( Vector3( 0.f, 2.f, -16.65f ), Vector3( 14.f, 0.04f, 0.3f ), Vector3( 0.1f, 0.06f, 0.04f ), &inRoot );
}


void VenueShow::BuildFestival( Transform& inRoot )
{
    // Open air at night: a field to the horizon, a roof over the stage, screens on towers, a
    // mixing tent in the crowd and delay towers further back.
    const Vector3 metal( 0.18f, 0.18f, 0.2f );
    const Vector3 canvas( 0.05f, 0.05f, 0.06f );
    m_kit.Box( Vector3( 0.f, -0.05f, -40.f ), Vector3( 400.f, 0.1f, 300.f ), Vector3( 0.02f, 0.04f, 0.02f ), &inRoot );
    // The roof: a canopy on four legs, a little above the truss.
    m_kit.Box( Vector3( 0.f, 12.4f, 4.8f ), Vector3( 24.f, 0.5f, 12.f ), canvas, &inRoot );
    for( float x : { -11.5f, 11.5f } )
    {
        for( float z : { -0.8f, 10.4f } )
        {
            m_kit.Box( Vector3( x, 6.2f, z ), Vector3( 0.6f, 12.4f, 0.6f ), metal, &inRoot );
        }
    }
    for( float side : { -1.f, 1.f } )
    {
        // Screen towers flanking the stage (the screens are the plan's).
        m_kit.Box( Vector3( side * 17.f, 5.f, 1.5f ), Vector3( 0.8f, 10.f, 0.8f ), metal, &inRoot );
        // Delay towers with a wash of their own colour.
        for( float z : { -26.f, -40.f } )
        {
            m_kit.Box( Vector3( side * 14.f, 4.f, z ), Vector3( 0.6f, 8.f, 0.6f ), metal, &inRoot );
            m_kit.Box( Vector3( side * 14.f, 8.2f, z ), Vector3( 1.4f, 0.8f, 0.8f ), Vector3( 0.02f, 0.02f, 0.02f ), &inRoot, Vector3( 0.4f, 0.2f, 1.f ) );
        }
    }
    // The mixing tent.
    m_kit.Box( Vector3( 0.f, 1.f, -24.f ), Vector3( 6.f, 2.f, 4.f ), Vector3( 0.03f, 0.03f, 0.03f ), &inRoot );
    m_kit.Box( Vector3( 0.f, 3.2f, -24.f ), Vector3( 7.f, 0.3f, 5.f ), Vector3( 0.15f, 0.15f, 0.16f ), &inRoot );
    m_kit.Box( Vector3( 0.f, 2.05f, -22.05f ), Vector3( 5.f, 0.06f, 0.04f ), Vector3( 0.f, 0.f, 0.f ), &inRoot, Vector3( 0.2f, 1.5f, 0.4f ) );
}


void VenueShow::Update( double inSongTimeMs, float inDeltaTime )
{
    if( !m_root )
    {
        return;
    }
    UpdateAmbience( inSongTimeMs );
    if( m_presentation == Presentation::HighwayOnly )
    {
        // Nothing of the venue is on screen.
        return;
    }
    const auto started = std::chrono::steady_clock::now();
    // --venue-time <seconds> shows the venue that far into the song (to frame a moment without
    // playing up to it).
    static const double kPreviewOffset = CommandLine::GetFloat( "--venue-time", 0.f );
    inSongTimeMs += kPreviewOffset * 1000.0;
    // Offline venue reels may render more slowly than the silent audio device plays.
    // Start on the requested chart time and advance by the capture step for every image.
    static const float kCaptureFrom = CommandLine::Has( "--venue-only" ) ? CommandLine::GetFloat( "--venue-capture-from", -1.f ) : -1.f;
    if( kCaptureFrom >= 0.f )
    {
        inSongTimeMs = ( kCaptureFrom + m_captureElapsed ) * 1000.0;
        m_captureElapsed += inDeltaTime;
    }
    double seconds = inSongTimeMs / 1000.0;
    // A look with a frame rate steps the venue: update it on each step's time with the time since
    // the last step, and hold it (skip the update) in between.
    const float stepRate = m_director.FrameRateAt( seconds );
    // (A smoothed frame time, so the feeds' interval doesn't jitter with it.)
    m_frameSeconds += ( inDeltaTime - m_frameSeconds ) * 0.05f;
    m_director.SetFeedStepRate( stepRate, m_frameSeconds );
    if( stepRate > 0.f )
    {
        m_stepDelta += inDeltaTime;
        const int64_t step = static_cast<int64_t>( std::floor( seconds * stepRate ) );
        if( step == m_lastStep )
        {
            LogUpdateCost( started );
            return;
        }
        m_lastStep = step;
        seconds = static_cast<double>( step ) / stepRate;
        inSongTimeMs = seconds * 1000.0;
        // (Capped: a pause piles up time without stepping.)
        inDeltaTime = std::min( m_stepDelta, 0.25f );
        m_stepDelta = 0.f;
        m_director.SetGrainFrame( static_cast<int>( ( step % 100000 + 100000 ) % 100000 ) );
    }
    else if( m_lastStep != INT64_MIN )
    {
        m_lastStep = INT64_MIN;
        m_stepDelta = 0.f;
        m_director.SetGrainFrame( -1 );
    }
    // A roar when the song ends.
    for( const TimedCueData& event : m_venue.m_songEvents )
    {
        if( ( event.m_name == "music_end" || event.m_name == "end" ) && seconds > event.m_time && seconds < event.m_time + 1.0 )
        {
            m_crowd.OnCheer( 1.f );
        }
    }
    // A crowd surfer on the chart's crowd-surf / stage-dive shots, and now and then when it's intense.
    const std::string& shot = m_director.CurrentShot();
    const bool surfShot = shot.find( "crowdsurf" ) != std::string::npos || shot.find( "stagedive" ) != std::string::npos;
    m_crowd.SetSurfing( surfShot || ( m_crowd.Mood( seconds ) == "intense" && std::fmod( seconds, 53.0 ) < 1.0 ) );
    const double sinceLift = seconds - m_lastMoment;
    m_crowd.Update( seconds, inDeltaTime, m_performance, sinceLift >= 0. && sinceLift < 12. * 60. / std::max( m_bpm, 1.f ) );
    Vector3 surfer;
    const bool surferUp = m_crowd.SurferUp( surfer );
    m_director.FollowSurfer( surferUp, surfer );
    m_band.Update( seconds, inDeltaTime, CrowdUp() ? m_crowd.Energy() : 0.6f );
    m_lyricBoard.Update( seconds );
    m_director.SetHype( m_hype );
    m_director.Update( seconds, inDeltaTime );
    m_lights.SetCrowdEnergy( CrowdUp() ? m_crowd.Energy() : 0.6f );
    UpdateHype( seconds, inDeltaTime );
    // The follow spots keep a little front light on the band so they read in any look, and come
    // up full on whoever's soloing.
    const int spotMembers[5] = { VenueData::Keys, VenueData::Vocals, VenueData::Guitar, VenueData::Drums, VenueData::Bass };
    int soloist = -1;
    for( int slot = 0; slot < 5; ++slot )
    {
        const int member = spotMembers[slot];
        const bool solo = m_band.StateOf( member, seconds ) == "play_solo";
        m_lights.SetSpotlightFloor( slot, !m_band.HasMember( member ) ? 0.f : solo ? 0.45f : kFrontFill );
        if( solo && m_band.HasMember( member ) ) soloist = slot;
        if( m_band.HasMember( member ) )
        {
            // An operator keeps the spot on them, not on every bob: eased, snapped when far off
            // (the first frame, a room swap).
            const Vector3 chest = m_band.ChestOf( member );
            Vector3& aim = m_spotAims[slot];
            aim = ( aim - chest ).Length() > 3.f ? chest : aim + ( chest - aim ) * ( 1.f - std::exp( -std::clamp( inDeltaTime, 0.f, 0.1f ) * 5.f ) );
            m_lights.SetSpotlightTarget( slot, aim );
        }
    }
    m_lights.SetSoloist( soloist );
    m_lights.SetHype( m_hype );
    m_lights.SetBurn( m_fx.Burn() );
    m_lights.Update( inSongTimeMs, inDeltaTime );
    // The dressing's LED pieces follow the rig, the beat and the kick.
    m_kick *= std::exp( -std::clamp( inDeltaTime, 0.f, 0.1f ) * 8.f );
    StageSet::Show show;
    show.Seconds = seconds;
    int measureBeat = 0;
    VenueTiming::BeatAt( m_beats, m_bpm, seconds, show.Beat, measureBeat );
    show.Glow = m_lights.WashGlow();
    show.Kick = m_kick;
    show.Hype = m_hype;
    show.Energy = CrowdUp() ? m_crowd.Energy() : 0.6f;
    m_set.Update( show );
    LogUpdateCost( started );
}


void VenueShow::StartAmbience( const VenueAmbience& inAmbience )
{
    m_ambienceSettings = inAmbience;
    if( inAmbience.SoundPath.empty() || !m_root )
    {
        return;
    }
    m_ambience = m_kit.Group( "Venue ambience", &m_root->GetComponent<Transform>() );
    if( !m_ambience )
    {
        return;
    }
    // Streamed (a long loop shouldn't be decoded whole) and 2D. AudioCore opens the stream in
    // the background; UpdateAmbience starts it once it has, well inside the load and lead-in.
    AudioSource& source = m_ambience->AddComponent<AudioSource>( inAmbience.SoundPath );
    source.Stream = true;
    source.Loop = true;
    source.Volume = inAmbience.Volume;
    m_ambienceStarted = false;
    INFO_FMT( "[Venues]", "Venue ambience: %s at %.0f%%, fading over the song's first %.1f s", inAmbience.SoundPath.c_str(), inAmbience.Volume * 100.f, inAmbience.FadeSeconds );
}


void VenueShow::UpdateAmbience( double inSongTimeMs )
{
    if( !m_ambience || !m_ambience->HasComponent<AudioSource>() )
    {
        return;
    }
    AudioSource& source = m_ambience->GetComponent<AudioSource>();
    // Full through the load and the count-in (the song clock is negative until the song starts),
    // then an ease down to nothing over FadeSeconds.
    const double fadeMs = static_cast<double>( m_ambienceSettings.FadeSeconds ) * 1000.0;
    float gain = 1.f;
    if( inSongTimeMs > 0.0 )
    {
        if( inSongTimeMs >= fadeMs )
        {
            source.Stop();
            m_ambience = {};
            return;
        }
        const double pi = 3.14159265358979323846;
        gain = static_cast<float>( 0.5 * ( 1.0 + std::cos( pi * inSongTimeMs / fadeMs ) ) );
    }
    source.SetVolume( m_ambienceSettings.Volume * gain );
    if( !m_ambienceStarted && source.SoundInstance )
    {
        if( source.SoundInstance->HasFailed() )
        {
            YIKES_FMT( "[Venues] Venue ambience %s couldn't be opened", m_ambienceSettings.SoundPath.c_str() );
            m_ambience = {};
            return;
        }
        if( source.IsLoaded() )
        {
            // From a random point in the loop, so the crowd isn't the same few seconds every
            // song: started paused, moved there, then let go.
            static std::mt19937 random( std::random_device{}() );
            source.Play( true, true );
            if( const unsigned int lengthMs = source.GetLength() )
            {
                source.SetPositionMs( std::uniform_int_distribution<unsigned int>( 0, lengthMs - 1 )( random ) );
            }
            source.Resume();
            m_ambienceStarted = true;
        }
    }
}


void VenueShow::SetAmbiencePaused( bool inPaused )
{
    if( !m_ambience || !m_ambience->HasComponent<AudioSource>() )
    {
        return;
    }
    AudioSource& source = m_ambience->GetComponent<AudioSource>();
    if( inPaused )
    {
        source.Pause();
    }
    else
    {
        source.Resume();
    }
}


void VenueShow::UpdateHype( double inSeconds, float inDeltaTime )
{
    // How hot the show runs: the chart's mood, lifted by the player's streak, with a kick after
    // each big moment. The rig, the cameras and the dressing all read it.
    const std::string mood = CrowdUp() ? m_crowd.Mood( inSeconds ) : std::string( "normal" );
    const float chart = mood == "intense" ? 0.75f : mood == "mellow" ? 0.2f : 0.45f;
    const float afterglow = 0.25f * std::exp( -static_cast<float>( std::max( 0.0, inSeconds - m_lastMoment ) ) / 6.f );
    const float target = std::clamp( chart * 0.75f + m_performance * 0.25f + afterglow, 0.f, 1.f );
    m_hype += ( target - m_hype ) * ( 1.f - std::exp( -std::clamp( inDeltaTime, 0.f, 0.25f ) * 1.5f ) );

    // The big moments. The chart's: each chorus or intense passage as it starts (the finale
    // biggest of all) and the song's end. The player's: asked for by OnStreak.
    const bool playing = inSeconds > m_lastSeconds && inSeconds - m_lastSeconds < 1.0;
    if( !m_scene.GetMarkers().Accents.empty() && ( inSeconds < m_lastSeconds || inSeconds - m_lastSeconds >= 1.0 ) )
    {
        if( m_accentPlaying ) SampleAccents( m_accentBeat );
        m_accentPlaying = false;
        m_director.SetAccentPhase( -1.f );
        m_accentBeat = -10000.;
    }
    if( playing )
    {
        for( float peak : m_peaks )
        {
            if( peak > m_lastSeconds && peak <= inSeconds )
            {
                BigMoment( inSeconds, peak >= m_finale ? 2 : 1 );
            }
        }
        for( const TimedCueData& event : m_venue.m_songEvents )
        {
            if( ( event.m_name == "music_end" || event.m_name == "end" ) && event.m_time > m_lastSeconds && event.m_time <= inSeconds )
            {
                m_lastMoment = -1000.0;
                BigMoment( inSeconds, 2 );
            }
        }
    }
    if( m_pendingMoment > 0 )
    {
        BigMoment( inSeconds, m_pendingMoment );
        m_pendingMoment = 0;
    }
    // --venue-moment N: a big moment every N seconds, to tune the effects.
    static const float kEvery = CommandLine::GetFloat( "--venue-moment", 0.f );
    if( kEvery > 0.f && std::floor( inSeconds / kEvery ) != std::floor( m_lastSeconds / kEvery ) )
    {
        m_lastMoment = -1000.0;
        BigMoment( inSeconds, 2 );
    }
    if( !m_scene.GetMarkers().Accents.empty() )
    {
        double beat; int barBeat;
        VenueTiming::BeatAt( m_beats, m_bpm, inSeconds, beat, barBeat );
        const bool loud = mood == "intense" || ( mood == "realtime" && m_performance > 0.8f );
        if( playing && loud && inSeconds >= 0. && beat - m_accentBeat >= 32. ) StartAccent( inSeconds, 1 );
        if( m_accentPlaying ) SampleAccents( beat );
    }
    m_lastSeconds = inSeconds;

    const bool gentle = GameSettings::GetInstance().StageLighting == 1;
    // Dry ice rolls in for the slow parts and clears when it's intense.
    m_fx.Update( inSeconds, inDeltaTime, gentle, mood == "mellow" ? 1.f : mood == "intense" ? 0.f : 0.3f );
    if( m_fx.Ignited() )
    {
        m_director.Kick( 1.f );
    }
}


void VenueShow::StartAccent( double inSeconds, int inLevel )
{
    const auto& cues = m_scene.GetMarkers().Accents;
    if( cues.empty() || inSeconds < 0. ) return;
    double beat; int barBeat;
    VenueTiming::BeatAt( m_beats, m_bpm, inSeconds, beat, barBeat );
    // A major hit during an ordinary rally adds the remaining paper while the ball stays in flight.
    const bool upgrade = m_accentPlaying;
    if( upgrade ? inLevel <= m_accentLevel : beat - m_accentBeat < 8. ) return;
    if( !upgrade ) m_accentBeat = beat;
    m_accentLevel = inLevel;
    m_accentPlaying = true;
    for( const auto& e : cues )
    {
        if( !e ) continue;
        auto* cue = e->TryGetComponent<VenueAccent>();
        auto* particles = e->TryGetComponent<ParticleSystem>();
        if( !cue || !particles ) continue;
        const int full = std::clamp( cue->Particles, 0, 512 );
        const int count = inLevel >= 2 ? full : full / 2;
        particles->Burst( count - ( upgrade ? full / 2 : 0 ) );
    }
    if( CommandLine::Has( "--highway-log" ) ) BRUH_FMT( "Venue: scene accent level %d at beat %.2f", inLevel, beat );
}


void VenueShow::SampleAccents( double inBeat )
{
    const bool fullLighting = CommandLine::GetInt( "--stage-lights", GameSettings::GetInstance().StageLighting ) >= 2;
    float progress = 1.f;
    for( const auto& e : m_scene.GetMarkers().Accents )
    {
        if( !e ) continue;
        const auto* cue = e->TryGetComponent<VenueAccent>();
        auto* seq = e->TryGetComponent<Sequence>();
        if( !cue ) continue;
        const float fraction = std::clamp( static_cast<float>( inBeat - m_accentBeat ) / std::clamp( cue->Beats, 1.f, 32.f ), 0.f, 1.f );
        if( seq ) seq->Seek( cue->FullLightingOnly && !fullLighting ? 0.f : fraction * seq->GetDuration() );
        progress = std::min( progress, fraction );
    }
    m_director.SetAccentPhase( progress );
    m_accentPlaying = progress < 1.f;
}


void VenueShow::BigMoment( double inSeconds, int inLevel )
{
    // Not while the last one is still ringing (a peak may still top a lift).
    const double since = inSeconds - m_lastMoment;
    if( since >= 0. && since < ( inLevel >= 2 ? 3.0 : 12.0 ) )
    {
        return;
    }
    m_lastMoment = inSeconds;
    StartAccent( inSeconds, inLevel );
    if( CommandLine::Has( "--highway-log" ) )
    {
        BRUH_FMT( "Venue: big moment (level %d) at %.2f s, hype %.2f", inLevel, inSeconds, m_hype );
    }
    if( inLevel >= 2 )
    {
        // A peak: everything goes off, and the cameras take a hero shot for two measures.
        m_fx.Jets( 1.3f );
        m_fx.Sparks( 3.5f );
        m_fx.Confetti( 1.f );
        m_fx.Flames();
        m_fx.Fireworks( 4 );
        m_lights.Accent( 1.f );
        if( !m_director.HasPeakShots() || m_scene.GetMarkers().Accents.empty() ) m_director.OnBigMoment( inSeconds, 8.f * 60.f / m_bpm );
        m_director.Kick( 1.f );
        m_crowd.OnCheer( 1.f );
    }
    else
    {
        // A lift: the jets and a hit on the blinders.
        m_fx.Jets( 0.8f );
        m_fx.Fireworks( 2 );
        m_lights.Accent( 0.7f );
        m_director.Kick( 0.5f );
        m_crowd.OnCheer( 0.5f );
    }
}


void VenueShow::LogUpdateCost( std::chrono::steady_clock::time_point inStarted )
{
    // --highway-log: what the venue costs on the main thread, every five seconds.
    static const bool kLog = CommandLine::Has( "--highway-log" );
    if( kLog )
    {
        m_updateMs += std::chrono::duration<double, std::milli>( std::chrono::steady_clock::now() - inStarted ).count();
        if( ++m_updateFrames >= 300 )
        {
            BRUH_FMT( "Venue: update %.2f ms a frame (%s, crowd %d, shot %s, look %s)", m_updateMs / m_updateFrames, StyleName( m_style ), static_cast<int>( m_crowd.Size() ),
                m_director.CurrentShot().c_str(), m_director.CurrentLook().empty() ? "-" : m_director.CurrentLook().c_str() );
            m_updateMs = 0.0;
            m_updateFrames = 0;
        }
    }
}


void VenueShow::OnHit( PadId inPad )
{
    m_lights.OnHit( inPad );
    if( inPad == PadId::Bass ) m_kick = 1.f;
}


void VenueShow::OnMiss()
{
    m_lights.OnMiss();
    m_crowd.OnMiss();
}


void VenueShow::OnStreak( int inCombo )
{
    // Every fifty in a row gets a cheer and a lift; reaching the top multiplier and every
    // hundred set the whole show off (BigMoment keeps them from piling up).
    if( inCombo > 0 && inCombo % 50 == 0 )
    {
        m_crowd.OnCheer( std::min( 1.f, 0.5f + inCombo / 400.f ) );
        // A peak for the player at most every 45 seconds, so a flawless run doesn't wear the
        // confetti out: the hundreds in between are lifts.
        const bool peak = inCombo % 100 == 0 && m_lastSeconds - m_lastPlayerPeak > 45.0;
        if( peak ) m_lastPlayerPeak = m_lastSeconds;
        m_pendingMoment = std::max( m_pendingMoment, peak ? 2 : 1 );
    }
    else if( inCombo == 30 && m_lastSeconds - m_lastPlayerPeak > 45.0 )
    {
        m_lastPlayerPeak = m_lastSeconds;
        m_pendingMoment = std::max( m_pendingMoment, 2 );
    }
}
