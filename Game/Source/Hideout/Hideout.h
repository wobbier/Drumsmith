#pragma once
#include "ECS/EntityHandle.h"
#include "JSON.h"
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

    // Event names Update may hand to HandleEvent.
    static const std::vector<const char*>& Events();
    // Sets every value the page binds, before the first Update (RmlUi reloads a page whose model
    // gains a key later).
    static void RegisterModel( RmlUiCore& inUi, const char* inModel );

    // The camera, the labels' places, the panels. Returns what the menu should do this frame.
    Action Update( float inDeltaTime, RmlUiCore& inUi, const char* inModel );
    // True when it was one of the hideout's events.
    bool HandleEvent( const std::string& inEvent, const json& inArgs, RmlUiCore& inUi, const char* inModel );
    // Escape: closes a panel or leaves a station. False when there was nothing to leave.
    bool Back();
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

    void Choose( int inStation );
    Pose PoseOf( int inStation ) const;
    void ApplyCamera( float inDeltaTime );
    // The menu music as the radio in the room plays it: muffled and off to its side from across
    // the room, the whole song once the camera is at it (TrackRadio::SetSpeaker).
    void ApplyRadio( float inDeltaTime );
    void UpdateLabels( RmlUiCore& inUi, const char* inModel );
    void FillRecords( RmlUiCore& inUi, const char* inModel ) const;
    void FillGigs( RmlUiCore& inUi, const char* inModel );
    std::string NextGoal() const;

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
};
