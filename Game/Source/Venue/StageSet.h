#pragma once
#include "ECS/EntityHandle.h"
#include "Math/Vector3.h"
#include <cstdint>
#include <vector>

class Transform;
class VenueKit;

// The stage's dressing (Docs/Venue-and-Band.md): everything that makes the deck look like a
// touring show rather than a bare platform. Lattice truss with its hoists, the backline (amp
// walls, pedalboards, wedges, setlists), the drum riser's skirt and rug, subs and front fills
// along the lip, the barricade and the pit's camera track, the wings (guitar world, monitor
// desk, racks, cases) and each room's extras. A few LED pieces move with the show: the strip
// along the stage's edge, the riser's fascia, pixel tubes on the towers and battens on the truss.
// It adds no lights of its own; StageLights owns those. VenueShow owns it.
class StageSet
{
public:
    // What the LED pieces follow, each frame.
    struct Show
    {
        double Seconds = 0.0;
        double Beat = 0.0;          // continuous beat count (VenueTiming::BeatAt)
        Vector3 Glow;               // the rig's average colour x level (StageLights::WashGlow)
        float Kick = 0.f;           // 1 on a kick, decaying
        float Hype = 0.f;           // 0 calm .. 1 peak
        float Energy = 0.5f;        // crowd energy
    };

    // inStyle: VenueShow::Style as an int (0 arena, 1 club, 2 festival). inSeed: per song, for
    // repeatable variety (amp finishes, banners, posters).
    void Build( VenueKit& inKit, Transform& inRoot, int inStyle, bool inHasKeys, uint32_t inSeed );
    // Forgets its handles; the kit deletes the entities.
    void Clear();
    void Update( const Show& inShow );

private:
    void BuildRig( VenueKit& inKit, Transform& inRoot, int inStyle );
    void BuildBackline( VenueKit& inKit, Transform& inRoot, bool inHasKeys, uint32_t inSeed );
    void BuildRiser( VenueKit& inKit, Transform& inRoot );
    void BuildFront( VenueKit& inKit, Transform& inRoot, int inStyle );
    void BuildWings( VenueKit& inKit, Transform& inRoot );
    void BuildPixels( VenueKit& inKit, Transform& inRoot );
    void BuildArena( VenueKit& inKit, Transform& inRoot );
    void BuildClub( VenueKit& inKit, Transform& inRoot, uint32_t inSeed );
    void BuildFestival( VenueKit& inKit, Transform& inRoot, uint32_t inSeed );

    // LED pieces, tinted each frame.
    std::vector<EntityHandle> m_edgeStrip;     // along the stage's front edge
    std::vector<EntityHandle> m_fascia;        // the drum riser's front
    std::vector<EntityHandle> m_tubes;         // pixel tubes up the front towers, six a tower
    std::vector<EntityHandle> m_battens;       // along the cross trusses, kBattensPerTruss each
    // Festival flags, swaying on their poles.
    std::vector<EntityHandle> m_flags;
    std::vector<float> m_flagYaws;
};
