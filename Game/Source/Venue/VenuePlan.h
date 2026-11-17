#pragma once
#include "Math/Vector3.h"
#include <array>
#include <vector>

// The venue's floor plan at run time (Docs/Venue-and-Band.md): where the band stands and faces,
// the stage's size, where the crowd fills the floor, the room the cameras work in, the screens,
// and which of the built-in pieces go up. VenueShow builds the show from one, and everything that
// places something belonging to a member (body, instrument, kit, mic stand, follow spot, the
// director's shots of them) reads it, so moving a spot here moves all of it. ForStyle gives the
// three procedural rooms (VenueLayout's numbers); a scene venue fills one from its markers.
//
// Venue space, as VenueLayout: metres, +x the crowd's right, +y up, +z from the crowd toward the
// back wall; the crowd at z < 0 facing +z, the band facing -z.
struct VenuePlan
{
    // Where one member stands, in VenueData::Member order (drums, guitar, bass, vocals, keys).
    struct Spot
    {
        Vector3 Feet;
        // The member's yaw (degrees about +y). Their own front is their +z, so 180 faces the
        // crowd. The drum kit is built as one unit in the drummer's frame (Band's kStrike) and
        // turns with it.
        float Yaw = 180.f;
        // False: nobody stands here. No body, instrument, follow spot or shot of the spot.
        bool Present = true;
    };

    // The stage: a deck Height high from its front edge (z 0) back to the back wall, the drum
    // riser centre back, the overhead truss, and the barricade the photo pit runs behind.
    struct StageDims
    {
        float Height = 1.2f;
        float HalfWidth = 9.f;
        float Depth = 10.f;
        float BackWallZ = 10.6f;
        float RiserHeight = 0.6f;
        float RiserZ = 6.6f;
        float TrussHeight = 9.5f;
        float BarricadeZ = -1.6f;
    };

    // A rectangle of floor (axis aligned in venue xz, MinZ the back, MaxZ the edge nearest the
    // stage) the crowd fills, or keeps clear.
    struct CrowdArea
    {
        // Posed: the full figures (Crowd::Build), in rows from MaxZ back to MinZ, narrow at the
        // front (FrontHalfWidth either side of the middle) and widening by Widen a metre back, to
        // the rectangle's width. Mob: the cheap figures (Crowd::AddMob), on a grid Spacing apart
        // with Density of its spots taken. Clear: floor neither fills (a desk, an aisle, a tower).
        enum class Kind : int { Posed = 0, Mob, Clear };
        Kind Type = Kind::Mob;
        float MinX = 0.f;
        float MaxX = 0.f;
        float MinZ = 0.f;
        float MaxZ = 0.f;
        float FloorY = 0.f;            // the height they stand at (a tier of seating)
        int Heads = 0;                 // at a full house; --crowd-size scales them all
        float Spacing = 0.62f;         // Mob
        float Density = 0.8f;          // Mob
        float FrontHalfWidth = 7.5f;   // Posed
        float Widen = 0.35f;           // Posed
        // Which way they face: Yaw (degrees, 0 faces +z), then turned Turn of the way toward
        // Focus (venue xz), the singer's spot for those off to the side.
        float Yaw = 0.f;
        float Turn = 0.8f;
        Vector3 Focus{ 0.f, 0.f, 4.f };
    };

    // The room the cameras work in (Director::Room): every shot stays inside it. Back is the back
    // wall's z, Ceiling the lowest thing overhead, HalfWidth the side walls, DeskZ the mixing desk
    // the long lens shoots from. An open-air venue leaves the defaults.
    struct Room
    {
        float Back = -1000.f;
        float Ceiling = 1000.f;
        float HalfWidth = 30.f;
        float DeskZ = -22.f;
        bool Outdoor = false;
    };

    // A screen showing a feed: a plane Width x Height centred at Centre, facing the crowd (-z)
    // turned by Yaw, in a black frame. Program: the main camera's shot (Director::kProgramTexture);
    // Stage: the close-up feed (Director::kFeedTexture). Seams: an LED wall built of panels, the
    // dressing (StageSet) draws the seams a metre apart.
    struct Screen
    {
        enum class Feed : int { Program = 0, Stage };
        Vector3 Centre;
        float Width = 12.f;
        float Height = 6.f;
        float Yaw = 0.f;
        Feed Source = Feed::Program;
        bool Seams = false;
    };

    // The karaoke band (LyricBoard): Width wide, centred at Centre, facing the crowd.
    struct LyricBand
    {
        bool Present = true;
        Vector3 Centre;
        float Width = 11.f;
    };

    // The procedural room this plan dresses as (VenueShow::Style as an int): BuildRoom's
    // geometry, StageSet's room extras and barricade, StageFx's fireworks and confetti.
    int Style = 0;
    std::array<Spot, 5> Members;
    StageDims Stage;
    // In build order: every Posed area, then every Clear area, then every Mob area in turn.
    std::vector<CrowdArea> Crowd;
    Room Bounds;
    std::vector<Screen> Screens;
    LyricBand Lyrics;
    // How thick the haze hangs (StageLights::SetHazeScale): less of it out of doors.
    float HazeScale = 1.f;

    // Which built-in pieces go up. Stage: the deck, riser, back wall and speaker stacks. Set: the
    // dressing (StageSet). Rig: the light rig (StageLights; without it a soft key light). Fx: the
    // effects (StageFx). Crowd: the audience. Room: the procedural room around it all (Style's).
    bool BuildStage = true;
    bool BuildSet = true;
    bool BuildRig = true;
    bool BuildFx = true;
    bool BuildCrowd = true;
    bool BuildRoom = true;

    // One of the three procedural rooms (VenueShow::Style as an int), as they have always been.
    static VenuePlan ForStyle( int inStyle );

    bool HasMember( int inMember ) const { return inMember >= 0 && inMember < static_cast<int>( Members.size() ) && Members[inMember].Present; }
    // A member's spot (clamped to the five), present or not.
    const Spot& SpotOf( int inMember ) const;
    // The front of the crowd (venue z): the nearest Posed area's front edge, else just behind
    // the barricade.
    float CrowdFront() const;
    // A point given in the frame a member facing the crowd (Yaw 180) would have, turned with
    // that member's own yaw about their feet: inPoint unchanged at Yaw 180.
    Vector3 TurnWith( int inMember, const Vector3& inPoint ) const;
};
