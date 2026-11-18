#pragma once
#include "CoreGame/TrackList.h"
#include "ECS/EntityHandle.h"
#include "JSON.h"
#include "Venue/Band.h"
#include "Venue/VenueKit.h"
#include "Math/Vector3.h"
#include <string>
#include <vector>

class RmlUiCore;
class World;
class Transform;
class Camera;

// The main menu's room (Docs/Hideout-and-Progression.md): the hideout tier's scene loaded behind
// the menu, its unlocked items, the camera flying between the stations, and the labels over them
// in the "main_menu" model. MainMenuController owns one and hands it the events it doesn't know.
class Hideout
{
public:
    // What choosing a station asks of the menu.
    enum class Action { None, OpenSettings, ShowRadio, Quit };

    Hideout() = default;
    // Gives the radio back its full sound.
    ~Hideout();

    // Loads the profile's room under the menu camera's world. False (and the old flat menu
    // stays) when there is no room to load.
    bool Start( World& inWorld, const EntityHandle& inCamera );
    void Clear();
    bool IsReady() const { return m_ready; }
    // The room again, from the profile as it is now (the debug menu's changes). inEvaluate runs
    // the progression rules first, as coming back to the menu does.
    bool Reload( bool inEvaluate );
    // The camera's way in again (HideoutView::IntroEye), when the room has one.
    void ReplayIntro();
    // The new items' tour through these items (ids), or every unlocked item in the room.
    void Tour( const std::vector<std::string>& inItems );

    // Day or night in the room (HideoutWhen): the player's clock unless overridden.
    enum class TimeOfDay : int { Auto = 0, Day, Night };
    static TimeOfDay& TimeOverride();
    static bool IsDay();
    // Seconds since midnight on the room's clock (the player's, or a time of day the override picked).
    static double ClockSeconds();

    // Event names Update may hand to HandleEvent.
    static const std::vector<const char*>& Events();
    // Sets every value the page binds, before the first Update (RmlUi reloads a page whose model
    // gains a key later).
    static void RegisterModel( RmlUiCore& inUi, const char* inModel );

    // The camera, the labels' places, the panels. Returns what the menu should do this frame.
    Action Update( float inDeltaTime, RmlUiCore& inUi, const char* inModel );
    // True when it was one of the hideout's events.
    bool HandleEvent( const std::string& inEvent, const json& inArgs, RmlUiCore& inUi, const char* inModel );
    // The station whose label the pointer (or focus) is on: it's lit a little. -1: none.
    void Hover( int inStation ) { m_hover = inStation; }
    // Escape: closes a panel or leaves a station. False when there was nothing to leave.
    bool Back();
    // The hideout debug menu (F2; Hideout/HideoutDebug.cpp): non-Retail builds, or --hideout-debug.
    static bool DebugAllowed();
    // Back to the overview (the settings panel closed).
    void ReturnToOverview() { Choose( -1 ); }

private:
    struct Station
    {
        EntityHandle Entity;
        int Kind = 0;
        std::string Label;
        Vector3 Position;
        Vector3 ViewOffset;
        float FieldOfView = 45.f;
    };
    struct Pose
    {
        Vector3 Eye;
        Vector3 Target;
        float FieldOfView = 55.f;
    };

    // Start's work, and Reload's: the room's scene, its markers, the drummer.
    bool Load( bool inEvaluate );
    void Choose( int inStation );
    Pose PoseOf( int inStation ) const;
    void ApplyCamera( float inDeltaTime );
    // The menu music as the radio in the room plays it: muffled and off to its side from across
    // the room, the whole song once the camera is at it (TrackRadio::SetSpeaker).
    void ApplyRadio( float inDeltaTime );
    // The band's name on the bedsheet and the kick (HideoutBandName), from PlayerProfile::BandName.
    void ApplyBandName();
    // The radio's beat and loudness (m_music), then every HideoutMotion in the room.
    void UpdateMusic( float inDeltaTime );
    void UpdateMotions( float inDeltaTime );
    // The player's drummer at the kit (HideoutDrummer): rebuilt for each song the radio plays,
    // from that song's chart, and played along with the radio's position.
    void UpdateDrummer( float inDeltaTime );
    void BuildBand( const TrackData* inTrack );
    // Depth of field on the menu camera: focused on whatever the camera is looking at.
    void UpdateFocus( float inDeltaTime );
    void UpdateLabels( RmlUiCore& inUi, const char* inModel );
    // The words in the room that come from the player (HideoutReadout).
    void UpdateReadouts( float inDeltaTime );
    void FillRecords( RmlUiCore& inUi, const char* inModel ) const;
    void FillGigs( RmlUiCore& inUi, const char* inModel );
    // The wishlist: every item, whether it's in, and how to get the ones that aren't.
    void FillWishlist( RmlUiCore& inUi, const char* inModel ) const;
    std::string NextGoal() const;
    // The debug menu (HideoutDebug.cpp): its rows, and what its buttons do.
    void DebugUpdate( RmlUiCore& inUi, const char* inModel );
    bool DebugEvent( const std::string& inEvent, const json& inArgs, RmlUiCore& inUi, const char* inModel );

    bool m_ready = false;
    World* m_world = nullptr;
    EntityHandle m_camera;
    std::vector<EntityHandle> m_roots;
    std::vector<Station> m_stations;
    Pose m_overview;
    Pose m_current;
    bool m_hasCurrent = false;
    int m_chosen = -1;
    // Seconds since the station was chosen: its action runs once the camera is nearly there.
    float m_chosenAge = 0.f;
    bool m_actionDone = true;
    // The open panel: "", "records", "gigs", "radio".
    std::string m_panel;
    std::vector<std::string> m_notices;
    bool m_noticeShown = false;
    // The gigs the board lists, by index into Progression::Gigs, and each one's setlist.
    std::vector<std::vector<int>> m_setlists;
    std::string m_status;
    float m_radioOpen = 0.f;
    // The hover light (a soft point light over the station whose label is under the pointer).
    int m_hover = -1;
    EntityHandle m_highlight;
    float m_highlightLevel = 0.f;
    Vector3 m_parallax;
    // New items' tour: after the notice, the camera visits each item just unlocked.
    struct Reveal
    {
        std::string Name;
        Vector3 Centre;
    };
    std::vector<Reveal> m_reveals;
    int m_reveal = -1;          // the one being shown; -1 before the tour or after it
    float m_revealAge = 0.f;
    Pose PoseOfReveal( const Reveal& inReveal ) const;
    // The first visit's camera move (HideoutView's IntroEye): seconds into it, < 0 when there's none.
    float m_intro = -1.f;
    Pose m_introFrom;
    bool m_hasIntro = false;
    static constexpr float kIntroSeconds = 4.5f;
    // The first visit after moving into this room (PlayerProfile::SeenTier): the boxes are out.
    bool m_movingIn = false;
    // The slots' entities (not the stand-ins), for the tour.
    std::vector<std::pair<std::string, EntityHandle>> m_slots;

    // A prop's motion and how the scene left it.
    struct Motion
    {
        EntityHandle Entity;
        int Kind = 0;
        float Amount = 1.f;
        float Speed = 1.f;
        Vector3 Axis;
        float Phase = 0.f;
        bool Music = false;
        Vector3 BaseEuler;
        Vector3 BasePosition;
        Vector3 BaseScale;
        float BaseIntensity = 0.f;
        bool HasLight = false;
        // A glowing mesh on the same entity (StandardMaterial): its emissive follows the Light's
        // motion, or is the motion when there's no Light.
        float BaseEmissive = 0.f;
        bool HasEmissive = false;
        // Flicker: the current dip and how long it lasts.
        float Dip = 0.f;
        float DipLeft = 0.f;
        uint32_t Random = 1;
    };
    std::vector<Motion> m_motions;
    float m_time = 0.f;

    // What the radio is playing, as the room hears it.
    struct MusicClock
    {
        const void* Track = nullptr;      // the song the beats are for
        std::vector<float> Beats;         // seconds
        std::vector<bool> Measures;       // a bar starts on this beat
        bool HasBeat = false;             // the song is playing and has a beat grid
        int Beat = 0;                     // the beat it's in
        float BeatPhase = 0.f;            // 0..1 through it
        float SinceBeat = 10.f;           // seconds since it started
        bool Downbeat = false;
        float Envelope = 0.f;             // 1 on the beat, decaying (louder songs hit harder)
        float Level = 0.f;                // smoothed loudness, 0..1
    };
    MusicClock m_music;

    struct Readout
    {
        EntityHandle Entity;
        int Source = 0;
        int Line = 0;
        std::string Item;
        std::string Prefix;
        int MaxLetters = 0;
        bool Upper = false;
        float Scroll = 0.f;
        std::string Shown;
    };
    std::vector<Readout> m_readouts;
    float m_readoutTime = 0.f;
    // PlayerProfile::RecentSongs as the songs' names (looked up when the list changes).
    std::vector<std::string> m_recentKeys;
    std::vector<std::string> m_recentNames;

    // The debug menu: open, the overlay hidden for a clean look at the room, the player's own
    // profile as it was before the menu changed anything (put back by its Restore button).
    bool m_debugOpen = false;
    bool m_overlayHidden = false;
    bool m_debugHasBackup = false;
    json m_debugBackup;
    std::string m_debugStatus;

    struct BandNamePart
    {
        EntityHandle Entity;
        bool Named = true;
        int FitLetters = 9;
        Vector3 Scale;
        float TextSize = 0.f;
    };
    std::vector<BandNamePart> m_bandNameParts;
    bool m_naming = false;

    // The drummer: where, who, and the chart of the song they're playing along with.
    bool m_hasDrummer = false;
    Vector3 m_drummerFeet;
    float m_drummerYaw = 180.f;
    int m_drummerCast = 0;
    float m_drummerEnergy = 0.55f;
    // The kit's finish (HideoutDrummer::Finish), put on each song's kit once its drums have loaded.
    Vector3 m_finish;
    float m_finishMetallic = 0.f;
    float m_finishRoughness = 0.4f;
    bool m_finishDone = true;
    float m_finishWait = 0.f;
    void ApplyFinish( float inDeltaTime );
    VenueKit m_kit;
    // The band's stage: an empty group at the room's origin (Band needs one to update).
    EntityHandle m_stage;
    // What the band is built from, cleared before each song's build: the drummer and kit of the
    // song before go with it.
    VenueKit m_bandKit;
    Band m_band;
    TrackData m_chart;
    const void* m_bandTrack = reinterpret_cast<const void*>( 1 );   // nothing built yet
    double m_bandSeconds = 0.0;
    bool m_bandShown = true;
    float m_focus = 3.f;
};
