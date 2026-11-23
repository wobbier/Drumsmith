#pragma once
#include "Math/Vector3.h"
#include <array>
#include <string>
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
        bool DanceFloor = false;
        float Widen = 0.35f;           // Posed
        // Which way they face: Yaw (degrees, 0 faces +z), then turned Turn of the way toward
        // Focus (venue xz), the singer's spot for those off to the side.
        float Yaw = 0.f;
        float Turn = 0.8f;
        Vector3 Focus{ 0.f, 0.f, 4.f };
        // Mob: how far each figure strays from its grid spot, as a share of the usual stray.
        float Scatter = 1.f;
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
        // HDR multiplier on the picture's light.
        float Emissive = 2.2f;
    };

    // The karaoke band (LyricBoard): Width wide, centred at Centre, facing the crowd.
    struct LyricBand
    {
        bool Present = true;
        Vector3 Centre;
        float Width = 11.f;
    };

    // A camera position of the venue's own (a scene's VenueCameraSpot) the director cuts to: the
    // eye and the way it looks (venue space), its vertical field of view, and the kind of shot it
    // is for. Wide, Desk and Crane spots take the place of the director's own wides, crane and
    // long lens; Close and Custom ones are extra cuts.
    struct CameraSpot
    {
        enum class Kind : int { Wide = 0, Desk, Crane, Close, Custom };
        Vector3 Eye;
        Vector3 Forward{ 0.f, 0.f, 1.f };
        float FieldOfView = 55.f;
        Kind Shot = Kind::Wide;
        std::string Tag;
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
    // The venue's own camera positions (none in the procedural rooms).
    std::vector<CameraSpot> Cameras;
    // How far this stage sits from the procedural rooms' (the members' middle against theirs):
    // the director's framings placed for those rooms move with it. Zero in the rooms.
    Vector3 ShotOffset{ 0.f, 0.f, 0.f };
    // The room's look. Background: the main camera's clear colour indoors, which also sets the
    // renderer's ambient light. FogColor: the light the fog scatters. Out of doors, the night
    // sky's hour, how bright its moon is and how much of it is cloud (0: no cloud pass).
    Vector3 Background{ 0.f, 0.f, 0.f };
    Vector3 FogColor{ 0.01f, 0.01f, 0.015f };
    float SkyTime = 22.f;
    float MoonBrightness = 1.f;
    float CloudCoverage = 0.25f;
    // The show's haze from the froxel grid instead of the march (VenueInfo::HazeFroxels, DRU-78).
    bool HazeFroxels = false;
    // Who films the live show (VenueInfo::FootageKind as an int): 0 the crew; 1 camcorders, 2 flip
    // phones, 3 both, held by guests at the venue's guest/ camera spots (Director, "Found footage").
    int Footage = 0;
    // The venue is on the move (VenueInfo::Ride): how hard the cameras take the road, and the
    // story flag that ends it (empty: never).
    float Ride = 0.f;
    std::string RideUntil;
    // What a desaturating look leaves in colour (VenueInfo::KeepRed...): x reds, y blues, z how
    // far the reds reach into fire; and the story flags between which it keeps all three.
    Vector3 ColorKeep = Vector3( 0.f, 0.f, 0.f );
    std::string LightsFrom;
    std::string LightsUntil;
    // The venue's name, for the logs (a scene's VenueInfo; the rooms leave it empty).
    std::string Name;

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
    // Nothing placed yet: no members, no lyric band, no screens, no crowd (a scene's markers fill
    // it in). A default VenuePlan has every member present at the origin.
    static VenuePlan Empty();

    bool HasMember( int inMember ) const { return inMember >= 0 && inMember < static_cast<int>( Members.size() ) && Members[inMember].Present; }
    // A member's spot (clamped to the five), present or not.
    const Spot& SpotOf( int inMember ) const;
    // The front of the crowd (venue z): the nearest Posed area's front edge, else just behind
    // the barricade.
    float CrowdFront() const;
    // The middle of the present members' feet (the stage's centre as the band stands on it).
    Vector3 MemberCentre() const;
    // A point given in the frame a member facing the crowd (Yaw 180) would have, turned with
    // that member's own yaw about their feet: inPoint unchanged at Yaw 180.
    Vector3 TurnWith( int inMember, const Vector3& inPoint ) const;
};
