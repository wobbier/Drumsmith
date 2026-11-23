#pragma once
#include "Components/Venue/VenueMarkers.h"
#include "Venue/VenuePlan.h"
#include "ECS/EntityHandle.h"
#include "JSON.h"
#include <string>
#include <vector>

class Transform;
class World;

// A venue scene (Docs/Venue-and-Band.md): a .lvl authored in Havana, instanced under the show's
// venue root (VenueLayout::kVenueOrigin) and read for its markers (Components/Venue). VenueShow
// owns one; the scene's entities go with the venue (Clear, a room swap, the end of the song).
//
// Before it's instanced, a scene loses everything that isn't scenery: its cores, scripts (a mod's
// venue must not run code), UI documents, cameras (the director owns the cameras) and audio
// listeners. Then its markers become a VenuePlan: the band at the VenueSpots, Mob crowds on the
// VenueCrowdAreas, the feeds on the VenueScreens, the director's extra positions from the
// VenueCameraSpots, and the lights tagged VenueShowLight handed to the light show.
class VenueScene
{
public:
    // What came out of a scene before it was instanced.
    struct Stripped
    {
        int Cores = 0;
        int Scripts = 0;       // ScriptComponent
        int Documents = 0;     // UIDocument
        int Cameras = 0;       // Camera, with the PostProcess and camera rigs on the same entity
        int Listeners = 0;     // AudioListener
        int Total() const { return Cores + Scripts + Documents + Cameras + Listeners; }
    };

    // A light of the scene's the show cues (a VenueShowLight that isn't Static).
    struct ShowLight
    {
        EntityHandle Light;
        VenueShowLight::Role Role = VenueShowLight::Role::Wash;
        int Group = 0;
    };

    // What the markers came to.
    struct Markers
    {
        VenuePlan Plan;
        std::vector<ShowLight> Lights;
        std::vector<EntityHandle> Accents;
        // Entities with a VenueStory marker.
        std::vector<EntityHandle> Story;
        // Entities with a VenueBeat marker.
        std::vector<EntityHandle> Beats;
        // Entities with a VenueAim marker.
        std::vector<EntityHandle> Aims;
        // The scene lights itself with a directional (a sun or moon of its own).
        bool HasDirectional = false;
        int Spots = 0;
        int CrowdAreas = 0;
        int Cameras = 0;
        int Screens = 0;
        int StaticLights = 0;
    };

    // Takes out of a scene's JSON what a venue mustn't bring (above). Counts what went.
    static Stripped Strip( json& ioScene );
    // Reads the markers under inRoots into a plan, positions and facings relative to inVenueRoot
    // (venue space). False, with the reason, when the scene can't be a venue: no VenueInfo or no
    // Drummer spot; the caller falls back to a procedural room.
    static bool Collect( const std::vector<EntityHandle>& inRoots, Transform& inVenueRoot, Markers& outMarkers, std::string& outProblem );

    // Reads, strips and instances the scene at inPath (logical, "Assets/Venues/X/X.lvl") under
    // inVenueRoot, then collects its markers. False, with the reason, when the file can't be read
    // or the scene isn't a venue (whatever was instanced is cleared again).
    bool Load( World& inWorld, const std::string& inPath, Transform& inVenueRoot, std::string& outProblem );
    // A venue scene that is already in the world (the open scene, played in Havana): its markers
    // read in place, nothing instanced or stripped. Clear leaves those entities alone.
    bool Adopt( const std::vector<EntityHandle>& inRoots, Transform& inVenueRoot, std::string& outProblem );
    void Clear();

    bool IsLoaded() const { return !m_roots.empty(); }
    const Markers& GetMarkers() const { return m_markers; }
    // Entities the scene instanced (its own, before models expand into theirs).
    size_t EntityCount() const { return m_entityCount; }

private:
    std::vector<EntityHandle> m_roots;
    // The roots are the open scene's (Adopt), not this venue's to delete.
    bool m_adopted = false;
    Markers m_markers;
    size_t m_entityCount = 0;
};
