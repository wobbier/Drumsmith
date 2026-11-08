#pragma once
#include "Math/Vector3.h"

// The venue's floor plan (Docs/Venue-and-Band.md), in venue space: metres, +x stage left as the
// crowd sees it... no: +x is the crowd's right, +y up, +z from the crowd toward the back wall. The
// crowd stands at z < 0 facing +z; the band faces -z. VenueShow places the venue far from the note
// highway (kVenueOrigin), so the highway's overlay camera never sees it and the venue's cameras
// never see the highway.
namespace VenueLayout
{
    const Vector3 kVenueOrigin( 4000.f, 0.f, 0.f );

    // The stage: a deck kStageHeight high from the front edge (z 0) to the back wall.
    constexpr float kStageHeight = 1.2f;
    constexpr float kStageHalfWidth = 9.f;
    constexpr float kStageDepth = 10.f;
    constexpr float kBackWallZ = 10.6f;
    // The drum riser, centre back.
    constexpr float kRiserHeight = 0.6f;
    constexpr float kRiserZ = 6.6f;
    // The overhead truss.
    constexpr float kTrussHeight = 9.5f;

    // Where each member stands (feet), in VenueData::Member order: drums (on the riser, seated),
    // guitar, bass, vocals, keys.
    const Vector3 kMemberSpots[5] = {
        Vector3( 0.f, kStageHeight + kRiserHeight, kRiserZ + 0.6f ),
        Vector3( -4.6f, kStageHeight, 3.2f ),
        Vector3( 4.6f, kStageHeight, 3.4f ),
        Vector3( 0.f, kStageHeight, 1.6f ),
        Vector3( -6.8f, kStageHeight, 6.4f ),
    };

    // The crowd's floor: barricade at z -1.6, rows back to kCrowdBackZ.
    constexpr float kBarricadeZ = -1.6f;
    constexpr float kCrowdFrontZ = -2.4f;
    constexpr float kCrowdBackZ = -26.f;
    constexpr float kCrowdHalfWidth = 13.f;
}
