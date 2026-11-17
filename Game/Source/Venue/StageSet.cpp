#include "Venue/StageSet.h"
#include "Venue/VenueKit.h"
#include "Venue/VenuePlan.h"
#include "Venue/VenueTiming.h"
#include "Components/Transform.h"
#include "Math/Quaternion.h"
#include "Path.h"
#include <algorithm>
#include <cmath>

namespace
{
    using Shape = Moonlight::MeshType;

    // Every imported prop the set uses, with the yaw that turns its front toward the crowd (-z).
    // Facings are easiest to judge from a screenshot: fix them here and every placement follows.
    // A prop whose file is missing is skipped (or stood in for by boxes where it matters).
    struct PropDef
    {
        const char* File;
        float Yaw;
    };
    const PropDef kDrumRug{ "Assets/Models/Venue/DrumRug.obj", 90.f };          // 2.9 x 3.4 m: long side across the riser
    const PropDef kGuitar{ "Assets/Models/Instruments/Runtime/Guitar.obj", 0.f };  // neck along -x, face +z
    const PropDef kBass{ "Assets/Models/Instruments/Runtime/Bass.obj", 0.f };
    const PropDef kRoadCase{ "Assets/Models/Venue/RoadCase.obj", 0.f };
    const PropDef kFlightCase{ "Assets/Models/Venue/FlightCaseWide.obj", 0.f };
    const PropDef kToolChest{ "Assets/Models/Venue/ToolChest.obj", 0.f };
    const PropDef kToolBox{ "Assets/Models/Venue/ToolBox.obj", 0.f };
    const PropDef kStool{ "Assets/Models/Venue/Stool.obj", 0.f };
    const PropDef kAmpRack{ "Assets/Models/Venue/AmpRack.obj", 0.f };
    const PropDef kPowerDistro{ "Assets/Models/Venue/PowerDistro.obj", 0.f };
    const PropDef kStageFan{ "Assets/Models/Venue/StageFan.obj", 0.f };
    const PropDef kCooler{ "Assets/Models/Venue/Cooler.obj", 0.f };
    const PropDef kBottle{ "Assets/Models/Venue/Bottle.obj", 0.f };
    const PropDef kBeerCup{ "Assets/Models/Venue/BeerCup.obj", 0.f };
    const PropDef kLadder{ "Assets/Models/Venue/Ladder.obj", 0.f };
    const PropDef kCableA{ "Assets/Models/Venue/CableA.obj", 0.f };             // 2 m along x
    const PropDef kCableB{ "Assets/Models/Venue/CableB.obj", 0.f };
    const PropDef kCableCoil{ "Assets/Models/Venue/CableCoil.obj", 0.f };
    const PropDef kCameraTripod{ "Assets/Models/Venue/CameraTripod.obj", 180.f };  // lens toward the stage
    const PropDef kCardboardBox{ "Assets/Models/Venue/CardboardBox.obj", 0.f };
    const PropDef kKeg{ "Assets/Models/Venue/Keg.obj", 0.f };
    const PropDef kBarrel{ "Assets/Models/Venue/Barrel.obj", 0.f };
    const PropDef kPallet{ "Assets/Models/Venue/Pallet.obj", 0.f };
    const PropDef kFlagA{ "Assets/Models/Venue/FlagA.obj", 0.f };
    const PropDef kFlagB{ "Assets/Models/Venue/FlagB.obj", 0.f };
    const PropDef kFoodStall{ "Assets/Models/Venue/FoodStall.obj", 0.f };
    const PropDef kUmbrellaTable{ "Assets/Models/Venue/UmbrellaTable.obj", 0.f };
    const PropDef kWheelieBin{ "Assets/Models/Venue/WheelieBin.obj", 0.f };
    const PropDef kTruck{ "Assets/Models/Venue/Truck.obj", 0.f };               // 7.6 m along z
    const PropDef kTourBus{ "Assets/Models/Venue/TourBus.obj", 0.f };           // 11.4 m along z

    constexpr int kEdgeSegments = 12;
    constexpr int kFasciaSegments = 8;
    constexpr int kTubeSegments = 6;
    constexpr int kBattensPerTruss = 8;
    constexpr float kTrussZ[3] = { 0.2f, 4.6f, 9.f };
    constexpr float kTrussSize = 0.4f;

    // A small palette: pieces sharing a colour draw as one batch.
    const Vector3 kBlack( 0.015f, 0.015f, 0.018f );
    const Vector3 kTolex( 0.028f, 0.028f, 0.03f );
    const Vector3 kGrille( 0.075f, 0.07f, 0.065f );
    const Vector3 kSteel( 0.18f, 0.18f, 0.2f );
    const Vector3 kAlu( 0.4f, 0.41f, 0.43f );
    const Vector3 kPaper( 0.55f, 0.55f, 0.5f );
    const Vector3 kDeckColor( 0.05f, 0.05f, 0.055f );
    const Vector3 kNone( 0.f, 0.f, 0.f );


    bool Has( const PropDef& inProp )
    {
        return Path( inProp.File ).Exists;
    }


    // A prop on its floor pivot, turned inYaw from its crowd-facing rest. Null when the file is missing.
    EntityHandle Put( VenueKit& inKit, Transform& inRoot, const PropDef& inProp, const Vector3& inPosition, float inYaw = 0.f, float inScale = 1.f )
    {
        if( !Has( inProp ) )
        {
            return {};
        }
        return inKit.Prop( inProp.File, inPosition, inScale, inProp.Yaw + inYaw, &inRoot );
    }


    // A square bar from one point to another.
    EntityHandle Beam( VenueKit& inKit, Transform& inRoot, const Vector3& inA, const Vector3& inB, float inWidth, const Vector3& inColor, bool inShadows = false )
    {
        const Vector3 delta = inB - inA;
        const float length = delta.Length();
        if( length < 0.001f )
        {
            return {};
        }
        EntityHandle piece = inKit.Piece( Shape::Cube, ( inA + inB ) * 0.5f, Vector3( inWidth, inWidth, length ), inColor, &inRoot, kNone, inShadows, "Beam" );
        if( piece )
        {
            const Vector3 direction = delta * ( 1.f / length );
            // Straight up or down has no "up" to keep: use x.
            piece->GetComponent<Transform>().LookDirection( direction, std::abs( direction.y ) > 0.95f ? Vector3( 1.f, 0.f, 0.f ) : Vector3::Up );
        }
        return piece;
    }


    // A box truss between two points: four chords and zigzag webbing on its faces. inFaces picks
    // the webbed faces (bit 0 / 1: the two across the first side axis, bit 2 / 3: across the
    // second), so runs nobody sees from below can skip half of them.
    void Truss( VenueKit& inKit, Transform& inRoot, const Vector3& inA, const Vector3& inB, float inSize, const Vector3& inColor, int inFaces = 15 )
    {
        const Vector3 delta = inB - inA;
        const float length = delta.Length();
        if( length < 0.01f )
        {
            return;
        }
        const Vector3 along = delta * ( 1.f / length );
        Vector3 side;
        Vector3 up;
        if( std::abs( along.y ) > 0.9f )
        {
            side = Vector3( 1.f, 0.f, 0.f );
            up = Vector3( 0.f, 0.f, 1.f );
        }
        else
        {
            side = along.Cross( Vector3::Up ).Normalized();
            up = side.Cross( along ).Normalized();
        }
        const float half = inSize * 0.5f;
        for( float u : { -1.f, 1.f } )
        {
            for( float v : { -1.f, 1.f } )
            {
                const Vector3 offset = side * ( u * half ) + up * ( v * half );
                Beam( inKit, inRoot, inA + offset, inB + offset, 0.05f, inColor, true );
            }
        }
        const int bays = std::max( 1, static_cast<int>( std::round( length / ( inSize * 1.6f ) ) ) );
        const float bay = length / static_cast<float>( bays );
        const Vector3 normals[4] = { side, side * -1.f, up, up * -1.f };
        const Vector3 spans[4] = { up, up, side, side };
        for( int face = 0; face < 4; ++face )
        {
            if( !( inFaces & ( 1 << face ) ) )
            {
                continue;
            }
            for( int i = 0; i < bays; ++i )
            {
                const float flip = ( i % 2 == 0 ) ? 1.f : -1.f;
                const Vector3 from = inA + along * ( bay * static_cast<float>( i ) ) + normals[face] * half - spans[face] * ( flip * half );
                const Vector3 to = inA + along * ( bay * static_cast<float>( i + 1 ) ) + normals[face] * half + spans[face] * ( flip * half );
                Beam( inKit, inRoot, from, to, 0.028f, inColor );
            }
        }
    }


    // A speaker cabinet facing the crowd: a body and its grille, inPosition at the floor centre.
    void Cabinet( VenueKit& inKit, Transform& inRoot, const Vector3& inPosition, const Vector3& inSize, const Vector3& inBody, const Vector3& inCloth )
    {
        inKit.Box( inPosition + Vector3( 0.f, inSize.y * 0.5f, 0.f ), inSize, inBody, &inRoot );
        inKit.Piece( Shape::Cube, inPosition + Vector3( 0.f, inSize.y * 0.5f, -inSize.z * 0.5f - 0.006f ), Vector3( inSize.x - 0.09f, inSize.y - 0.09f, 0.012f ), inCloth, &inRoot, kNone, false, "Grille" );
    }


    // A floor monitor: a wedge tipped back toward whoever stands upstage of it (inYaw 0), its
    // grille on the raised face.
    void Wedge( VenueKit& inKit, Transform& inRoot, const Vector3& inPosition, float inYaw )
    {
        EntityHandle group = inKit.Group( "Wedge", &inRoot, inPosition + Vector3( 0.f, 0.19f, 0.f ) );
        if( !group )
        {
            return;
        }
        Transform& wedge = group->GetComponent<Transform>();
        wedge.SetRotation( Quaternion::FromEulerDegrees( Vector3( 0.f, inYaw, 0.f ) ) * Quaternion::FromEulerDegrees( Vector3( -35.f, 0.f, 0.f ) ) );
        inKit.Box( Vector3( 0.f, 0.f, 0.f ), Vector3( 0.62f, 0.34f, 0.45f ), kTolex, &wedge );
        inKit.Piece( Shape::Cube, Vector3( 0.f, 0.172f, 0.f ), Vector3( 0.54f, 0.01f, 0.37f ), kGrille, &wedge, kNone, false, "Grille" );
    }


    // A row of little glowing dots (rack LEDs, faders, pedal lights), alternating two colours.
    void Dots( VenueKit& inKit, Transform& inRoot, const Vector3& inFrom, const Vector3& inStep, int inCount, const Vector3& inSize, const Vector3& inA, const Vector3& inB )
    {
        for( int i = 0; i < inCount; ++i )
        {
            inKit.Piece( Shape::Cube, inFrom + inStep * static_cast<float>( i ), inSize, kNone, &inRoot, i % 3 == 0 ? inB : inA, false, "LED" );
        }
    }
}


void StageSet::Clear()
{
    m_edgeStrip.clear();
    m_fascia.clear();
    m_tubes.clear();
    m_battens.clear();
    m_flags.clear();
    m_flagYaws.clear();
    m_plan = VenuePlan();
}


void StageSet::Build( VenueKit& inKit, Transform& inRoot, const VenuePlan& inPlan, bool inHasKeys, uint32_t inSeed )
{
    Clear();
    // The dressing is placed by hand for the procedural rooms' stage, relative to the plan's
    // sizes and member spots.
    m_plan = inPlan;
    const int style = inPlan.Style;
    BuildRig( inKit, inRoot, style );
    BuildBackline( inKit, inRoot, inHasKeys, inSeed );
    BuildRiser( inKit, inRoot );
    BuildFront( inKit, inRoot, style );
    BuildWings( inKit, inRoot );
    BuildPixels( inKit, inRoot );
    switch( style )
    {
    case 1: BuildClub( inKit, inRoot, inSeed ); break;
    case 2: BuildFestival( inKit, inRoot, inSeed ); break;
    default: BuildArena( inKit, inRoot ); break;
    }
}


void StageSet::BuildRig( VenueKit& inKit, Transform& inRoot, int inStyle )
{
    const float deck = m_plan.Stage.Height;
    const float stageHalfWidth = m_plan.Stage.HalfWidth;
    const float trussHeight = m_plan.Stage.TrussHeight;
    // The rig the lights hang from, as open lattice: three cross trusses over the stage, four
    // runs tying them together, a tower at each corner.
    const float y = trussHeight;
    const float reach = stageHalfWidth + 0.6f;
    for( float z : kTrussZ )
    {
        Truss( inKit, inRoot, Vector3( -reach, y, z ), Vector3( reach, y, z ), kTrussSize, kSteel );
    }
    for( float x : { -stageHalfWidth - 0.4f, -4.6f, 4.6f, stageHalfWidth + 0.4f } )
    {
        // Only the sides of these show from the floor.
        Truss( inKit, inRoot, Vector3( x, y, kTrussZ[0] + 0.2f ), Vector3( x, y, kTrussZ[2] - 0.2f ), kTrussSize, kSteel, 3 );
    }
    for( float x : { -stageHalfWidth - 0.4f, stageHalfWidth + 0.4f } )
    {
        for( float z : { kTrussZ[0], kTrussZ[2] } )
        {
            Truss( inKit, inRoot, Vector3( x, 0.06f, z ), Vector3( x, y - 0.2f, z ), kTrussSize, kSteel );
            inKit.Box( Vector3( x, 0.03f, z ), Vector3( 1.f, 0.06f, 1.f ), kSteel, &inRoot );
            // Ballast on the base plate.
            inKit.Box( Vector3( x + ( x < 0.f ? -0.32f : 0.32f ), 0.16f, z ), Vector3( 0.3f, 0.2f, 0.7f ), kBlack, &inRoot );
        }
    }
    // What it hangs from: chains up to the roof (the arena's grid, the club's ceiling, the
    // festival's canopy), with a hoist motor on each where there's the height for one.
    const float roof = inStyle == 1 ? 10.45f : inStyle == 2 ? 12.15f : 19.4f;
    for( float z : kTrussZ )
    {
        for( float x : { -8.f, 0.f, 8.f } )
        {
            Beam( inKit, inRoot, Vector3( x, y + 0.2f, z ), Vector3( x, roof, z ), 0.03f, kSteel );
            if( roof - y > 2.f )
            {
                inKit.Piece( Shape::Cube, Vector3( x, y + 0.75f, z ), Vector3( 0.26f, 0.5f, 0.3f ), Vector3( 0.5f, 0.38f, 0.04f ), &inRoot, kNone, false, "Hoist" );
            }
        }
    }
    // Cable looms: down the truss' ends into the wings, sagging on the way.
    for( float side : { -1.f, 1.f } )
    {
        const Vector3 from( side * ( stageHalfWidth + 0.2f ), y - 0.25f, 4.6f );
        const Vector3 to( side * 11.2f, deck + 0.9f, 8.6f );
        Vector3 last = from;
        for( int i = 1; i <= 6; ++i )
        {
            const float t = static_cast<float>( i ) / 6.f;
            // Mostly a drop, then a run: the loom hangs off the truss and trails to the racks.
            Vector3 point = from + ( to - from ) * t;
            point.y = from.y + ( to.y - from.y ) * ( 1.f - ( 1.f - t ) * ( 1.f - t ) );
            Beam( inKit, inRoot, last, point, 0.09f, kBlack );
            last = point;
        }
    }
}


void StageSet::BuildBackline( VenueKit& inKit, Transform& inRoot, bool inHasKeys, uint32_t inSeed )
{
    const float deck = m_plan.Stage.Height;
    // The guitarist's wall: full stacks behind them (the band's own combo sits in front of it). A
    // song's amps share a finish; the panel is gold or silver, the tolex black, wine or cream.
    const int finish = static_cast<int>( VenueTiming::Noise( inSeed, 71u ) * 3.f );
    const Vector3 tolex = finish == 1 ? Vector3( 0.09f, 0.015f, 0.02f ) : finish == 2 ? Vector3( 0.3f, 0.27f, 0.2f ) : kTolex;
    const Vector3 cloth = finish == 2 ? Vector3( 0.12f, 0.09f, 0.05f ) : kGrille;
    const Vector3 panel = VenueTiming::Noise( inSeed, 72u ) < 0.5f ? Vector3( 0.55f, 0.42f, 0.14f ) : Vector3( 0.5f, 0.5f, 0.52f );
    const Vector3 pilot( 4.f, 0.25f, 0.1f );
    const auto stack = [&]( float inX, float inZ, bool inFridge ) {
        // Guitar: two 4x12s and a head. Bass: one tall 8x10 and a head.
        const Vector3 cab = inFridge ? Vector3( 0.66f, 1.24f, 0.42f ) : Vector3( 0.76f, 0.76f, 0.36f );
        const int cabs = inFridge ? 1 : 2;
        for( int i = 0; i < cabs; ++i )
        {
            Cabinet( inKit, inRoot, Vector3( inX, deck + cab.y * static_cast<float>( i ), inZ ), cab, tolex, cloth );
            // The maker's plate, top left of the grille.
            inKit.Piece( Shape::Cube, Vector3( inX - cab.x * 0.3f, deck + cab.y * static_cast<float>( i + 1 ) - 0.1f, inZ - cab.z * 0.5f - 0.014f ), Vector3( 0.16f, 0.035f, 0.006f ), kPaper, &inRoot, kNone, false, "Plate" );
        }
        const float top = deck + cab.y * static_cast<float>( cabs );
        const Vector3 head( cab.x - 0.08f, 0.27f, cab.z - 0.1f );
        inKit.Box( Vector3( inX, top + head.y * 0.5f, inZ ), head, tolex, &inRoot );
        inKit.Piece( Shape::Cube, Vector3( inX, top + 0.07f, inZ - head.z * 0.5f - 0.004f ), Vector3( head.x - 0.06f, 0.07f, 0.008f ), panel, &inRoot, kNone, false, "Panel" );
        inKit.Piece( Shape::Cube, Vector3( inX + head.x * 0.38f, top + 0.07f, inZ - head.z * 0.5f - 0.01f ), Vector3( 0.025f, 0.025f, 0.01f ), kNone, &inRoot, pilot, false, "Pilot" );
        return top + head.y;
    };
    // With a keyboard player the wall gives up its outer stack to their corner.
    const float guitarZ = 5.9f;
    float guitarTop = 0.f;
    for( float x : { -3.7f, -4.55f, -5.4f } )
    {
        if( inHasKeys && x < -5.f ) continue;
        guitarTop = stack( x, guitarZ, false );
    }
    const float bassZ = 6.f;
    float bassTop = 0.f;
    for( float x : { 3.75f, 4.5f } )
    {
        bassTop = stack( x, bassZ, true );
    }
    // Lived-in: a towel and a bottle on a head each side, drinks within reach.
    inKit.Piece( Shape::Cube, Vector3( -4.55f, guitarTop + 0.012f, guitarZ - 0.02f ), Vector3( 0.34f, 0.024f, 0.3f ), Vector3( 0.5f, 0.5f, 0.52f ), &inRoot, kNone, false, "Towel" );
    Put( inKit, inRoot, kBottle, Vector3( -3.55f, guitarTop, guitarZ ) );
    Put( inKit, inRoot, kBottle, Vector3( 4.6f, bassTop, bassZ ) );
    Put( inKit, inRoot, kBeerCup, Vector3( 3.65f, bassTop, bassZ + 0.03f ) );
    inKit.Piece( Shape::Cube, Vector3( 3.9f, bassTop + 0.012f, bassZ - 0.03f ), Vector3( 0.3f, 0.024f, 0.26f ), Vector3( 0.5f, 0.5f, 0.52f ), &inRoot, kNone, false, "Towel" );

    if( inHasKeys )
    {
        // The keys corner: a rotary cabinet and a combo behind the player, a rug under them.
        const Vector3 spot = m_plan.SpotOf( 4 ).Feet;
        const Vector3 wood( 0.16f, 0.08f, 0.04f );
        inKit.Box( Vector3( spot.x - 0.25f, deck + 0.52f, spot.z + 1.5f ), Vector3( 0.74f, 1.04f, 0.52f ), wood, &inRoot );
        for( float y : { 0.2f, 0.26f, 0.32f, 0.84f, 0.9f, 0.96f } )
        {
            inKit.Piece( Shape::Cube, Vector3( spot.x - 0.25f, deck + y, spot.z + 1.5f - 0.265f ), Vector3( 0.6f, 0.03f, 0.012f ), kBlack, &inRoot, kNone, false, "Louvre" );
        }
        Cabinet( inKit, inRoot, Vector3( spot.x + 0.7f, deck, spot.z + 1.55f ), Vector3( 0.6f, 0.5f, 0.3f ), tolex, cloth );
        inKit.Piece( Shape::Cube, Vector3( spot.x + 0.92f, deck + 0.46f, spot.z + 1.55f - 0.16f ), Vector3( 0.02f, 0.02f, 0.01f ), kNone, &inRoot, Vector3( 0.2f, 3.f, 0.4f ), false, "Pilot" );
        Put( inKit, inRoot, kDrumRug, Vector3( spot.x, deck, spot.z + 0.2f ), 0.f, 0.6f );
    }

    // At their feet: pedalboards off to the outside (the soloist's walk forward stays clear), a
    // wedge each, a setlist and tape marks.
    const Vector3 pedalColors[4] = { Vector3( 0.5f, 0.3f, 0.02f ), Vector3( 0.05f, 0.3f, 0.1f ), Vector3( 0.45f, 0.05f, 0.05f ), Vector3( 0.08f, 0.15f, 0.45f ) };
    const Vector3 pedalLeds[4] = { Vector3( 3.f, 0.2f, 0.1f ), Vector3( 0.2f, 3.f, 0.3f ), Vector3( 3.f, 0.2f, 0.1f ), Vector3( 0.2f, 0.8f, 3.f ) };
    for( float side : { -1.f, 1.f } )
    {
        const Vector3 spot = m_plan.SpotOf( side < 0.f ? 1 : 2 ).Feet;
        // Theirs, unless the plan leaves them out: pedalboard, wedge, setlist and marks.
        if( m_plan.HasMember( side < 0.f ? 1 : 2 ) )
        {
            const Vector3 board( spot.x + side * 0.75f, deck, spot.z - 0.75f );
            inKit.Piece( Shape::Cube, board + Vector3( 0.f, 0.02f, 0.f ), Vector3( 0.66f, 0.04f, 0.34f ), kBlack, &inRoot, kNone, false, "Pedalboard" );
            const int pedals = side < 0.f ? 4 : 2;
            for( int i = 0; i < pedals; ++i )
            {
                const float x = board.x + ( static_cast<float>( i ) - ( pedals - 1 ) * 0.5f ) * 0.15f;
                inKit.Piece( Shape::Cube, Vector3( x, deck + 0.065f, board.z ), Vector3( 0.09f, 0.05f, 0.14f ), pedalColors[i], &inRoot, kNone, false, "Pedal" );
                inKit.Piece( Shape::Cube, Vector3( x, deck + 0.093f, board.z + 0.05f ), Vector3( 0.014f, 0.008f, 0.014f ), kNone, &inRoot, pedalLeds[i], false, "LED" );
            }
            Wedge( inKit, inRoot, Vector3( spot.x + side * 0.7f, deck, 1.25f ), 0.f );
            // The setlist, taped down beside the mic stand, and a spike mark where they stand.
            inKit.Piece( Shape::Cube, Vector3( spot.x - side * 0.45f, deck + 0.003f, spot.z - 0.8f ), Vector3( 0.21f, 0.004f, 0.3f ), kPaper, &inRoot, kNone, false, "Setlist" );
            inKit.Piece( Shape::Cube, Vector3( spot.x, deck + 0.002f, spot.z - 0.3f ), Vector3( 0.3f, 0.003f, 0.04f ), Vector3( 0.5f, 0.42f, 0.05f ), &inRoot, kNone, false, "Tape" );
            inKit.Piece( Shape::Cube, Vector3( spot.x, deck + 0.002f, spot.z - 0.2f ), Vector3( 0.04f, 0.003f, 0.2f ), Vector3( 0.5f, 0.42f, 0.05f ), &inRoot, kNone, false, "Tape" );
            // A DI box by the amps, and the cable run from the backline toward the front.
            inKit.Piece( Shape::Cube, Vector3( spot.x + side * 1.6f, deck + 0.03f, 5.3f ), Vector3( 0.12f, 0.06f, 0.16f ), Vector3( 0.3f, 0.05f, 0.05f ), &inRoot, kNone, false, "DI" );
            Put( inKit, inRoot, kCableA, Vector3( spot.x + side * 0.2f, deck, 5.1f ), side * 12.f );
        }
        Put( inKit, inRoot, kCableB, Vector3( side * 2.4f, deck, 4.9f ), side * 62.f );
        Put( inKit, inRoot, kCableCoil, Vector3( side * 6.3f, deck, 7.7f ) );
        // Flight cases upstage of the backline, where the crew left them.
        for( float x : { 3.6f, 4.9f } )
        {
            if( !Put( inKit, inRoot, kFlightCase, Vector3( side * x, deck, 8.2f ), side * 4.f ) )
            {
                inKit.Box( Vector3( side * x, deck + 0.3f, 8.2f ), Vector3( 1.2f, 0.6f, 0.66f ), kBlack, &inRoot );
            }
        }
        // A fan on each side of the deck, blowing across the front line.
    }
    // The singer's setlist and mark, and a rug to stand on.
    if( !m_plan.HasMember( 3 ) )
    {
        return;
    }
    const Vector3 singer = m_plan.SpotOf( 3 ).Feet;
    inKit.Piece( Shape::Cube, Vector3( singer.x, deck + 0.003f, singer.z - 0.85f ), Vector3( 0.21f, 0.004f, 0.3f ), kPaper, &inRoot, kNone, false, "Setlist" );
    for( float turn : { 45.f, -45.f } )
    {
        EntityHandle mark = inKit.Piece( Shape::Cube, Vector3( singer.x, deck + 0.002f, singer.z + 0.25f ), Vector3( 0.3f, 0.003f, 0.04f ), Vector3( 0.6f, 0.6f, 0.58f ), &inRoot, kNone, false, "Tape" );
        if( mark ) mark->GetComponent<Transform>().SetRotation( Vector3( 0.f, turn, 0.f ) );
    }
}


void StageSet::BuildRiser( VenueKit& inKit, Transform& inRoot )
{
    const float deck = m_plan.Stage.Height;
    const float riserHeight = m_plan.Stage.RiserHeight;
    const float riserZ = m_plan.Stage.RiserZ;
    // The drum riser (3.4 x 2.8 m, its front at z 5.7): an aluminium frame round the top, black
    // skirts, an LED fascia across the front that thumps with the kick, a rug under the kit and
    // steps up its side.
    const float top = deck + riserHeight;
    const float centreZ = riserZ + 0.5f;
    const float front = centreZ - 1.4f;
    const float width = 3.4f;
    inKit.Piece( Shape::Cube, Vector3( 0.f, top - 0.03f, front - 0.02f ), Vector3( width + 0.06f, 0.06f, 0.04f ), kAlu, &inRoot, kNone, false, "Trim" );
    for( float side : { -1.f, 1.f } )
    {
        inKit.Piece( Shape::Cube, Vector3( side * ( width * 0.5f + 0.02f ), top - 0.03f, centreZ ), Vector3( 0.04f, 0.06f, 2.84f ), kAlu, &inRoot, kNone, false, "Trim" );
        inKit.Piece( Shape::Cube, Vector3( side * ( width * 0.5f + 0.015f ), deck + ( riserHeight - 0.06f ) * 0.5f, centreZ ), Vector3( 0.02f, riserHeight - 0.06f, 2.8f ), kBlack, &inRoot, kNone, false, "Skirt" );
    }
    const float cell = width / static_cast<float>( kFasciaSegments );
    for( int i = 0; i < kFasciaSegments; ++i )
    {
        const float x = -width * 0.5f + ( static_cast<float>( i ) + 0.5f ) * cell;
        m_fascia.push_back( inKit.Piece( Shape::Cube, Vector3( x, deck + 0.27f, front - 0.045f ), Vector3( cell - 0.04f, 0.42f, 0.02f ), kNone, &inRoot, Vector3( 0.02f, 0.02f, 0.03f ), false, "Fascia" ) );
    }
    // The rug: a touch narrower than the riser, the long way across it.
    Put( inKit, inRoot, kDrumRug, Vector3( 0.f, top, centreZ ), 0.f, 0.92f );
    // Steps on the bass side, clear of the floor lights along the back.
    inKit.Box( Vector3( width * 0.5f + 0.32f, deck + 0.2f, centreZ + 0.9f ), Vector3( 0.56f, 0.4f, 0.7f ), kDeckColor, &inRoot );
    inKit.Box( Vector3( width * 0.5f + 0.82f, deck + 0.1f, centreZ + 0.9f ), Vector3( 0.44f, 0.2f, 0.7f ), kDeckColor, &inRoot );
    // The drummer's wedge on the hi-hat side, their setlist, water and a towel.
    Wedge( inKit, inRoot, Vector3( -1.3f, top, centreZ + 0.35f ), -100.f );
    inKit.Piece( Shape::Cube, Vector3( 1.25f, top + 0.045f, front + 0.3f ), Vector3( 0.21f, 0.004f, 0.3f ), kPaper, &inRoot, kNone, false, "Setlist" );
    Put( inKit, inRoot, kBottle, Vector3( -1.5f, top, front + 0.2f ) );
    Put( inKit, inRoot, kBottle, Vector3( -1.38f, top, front + 0.26f ) );
    inKit.Piece( Shape::Cube, Vector3( 1.5f, top + 0.012f, centreZ + 1.2f ), Vector3( 0.3f, 0.024f, 0.24f ), Vector3( 0.5f, 0.5f, 0.52f ), &inRoot, kNone, false, "Towel" );
}


void StageSet::BuildFront( VenueKit& inKit, Transform& inRoot, int inStyle )
{
    const float deck = m_plan.Stage.Height;
    const float barricadeZ = m_plan.Stage.BarricadeZ;
    // Subs in a row against the stage's front, their grilles to the crowd. The pit's cameras work
    // above and in front of them.
    for( int i = 0; i < 12; ++i )
    {
        const float x = -7.7f + static_cast<float>( i ) * 1.4f;
        Cabinet( inKit, inRoot, Vector3( x, 0.f, -0.42f ), Vector3( 1.26f, 0.58f, 0.7f ), kBlack, kGrille );
    }
    // Front fills on the lip, between the floor lights and the pyro.
    for( float x : { -8.45f, -4.5f, 4.5f, 8.45f } )
    {
        Cabinet( inKit, inRoot, Vector3( x, deck, 0.24f ), Vector3( 0.5f, 0.24f, 0.3f ), kTolex, kGrille );
    }
    // The barricade: panels with a post at each joint, a rail along the top and a brace on the
    // pit side of every post. As wide as the room's floor.
    const float halfWidth = inStyle == 1 ? 12.4f : inStyle == 2 ? 25.f : 13.75f;
    const float panel = 1.25f;
    const int panels = static_cast<int>( std::round( halfWidth * 2.f / panel ) );
    const float start = -static_cast<float>( panels ) * panel * 0.5f;
    for( int i = 0; i <= panels; ++i )
    {
        const float x = start + static_cast<float>( i ) * panel;
        inKit.Piece( Shape::Cube, Vector3( x, 0.58f, barricadeZ ), Vector3( 0.07f, 1.16f, 0.09f ), kSteel, &inRoot, kNone, false, "Post" );
        Beam( inKit, inRoot, Vector3( x, 0.95f, barricadeZ + 0.03f ), Vector3( x, 0.03f, barricadeZ + 0.5f ), 0.045f, kSteel );
        if( i < panels )
        {
            inKit.Box( Vector3( x + panel * 0.5f, 0.55f, barricadeZ ), Vector3( panel - 0.05f, 1.02f, 0.035f ), Vector3( 0.1f, 0.1f, 0.115f ), &inRoot );
        }
    }
    inKit.Piece( Shape::Cube, Vector3( 0.f, 1.13f, barricadeZ ), Vector3( static_cast<float>( panels ) * panel + 0.1f, 0.06f, 0.11f ), kAlu, &inRoot, kNone, false, "Rail" );
    // The pit: a camera track along it with a dolly parked at the guitarist's end, and a second
    // operator's tripod at the other. Both stay at the ends, out of the director's own shots.
    for( float z : { -0.98f, -1.24f } )
    {
        inKit.Piece( Shape::Cube, Vector3( 0.f, 0.035f, z ), Vector3( 17.6f, 0.03f, 0.03f ), kAlu, &inRoot, kNone, false, "Rail" );
    }
    for( int i = 0; i < 15; ++i )
    {
        inKit.Piece( Shape::Cube, Vector3( -8.4f + static_cast<float>( i ) * 1.2f, 0.012f, -1.11f ), Vector3( 0.1f, 0.024f, 0.36f ), kBlack, &inRoot, kNone, false, "Sleeper" );
    }
    inKit.Box( Vector3( -8.3f, 0.12f, -1.11f ), Vector3( 0.9f, 0.1f, 0.44f ), kBlack, &inRoot );
    Put( inKit, inRoot, kCameraTripod, Vector3( -8.3f, 0.17f, -1.11f ), 20.f, 0.85f );
    Put( inKit, inRoot, kCameraTripod, Vector3( 8.8f, 0.f, -1.05f ), -25.f, 0.9f );
    // Spare water for the front row, and somebody's case.
    Put( inKit, inRoot, kCardboardBox, Vector3( 9.3f, 0.f, -0.5f ), 15.f );
    Put( inKit, inRoot, kFlightCase, Vector3( -9.4f, 0.f, -0.5f ), 90.f );
}


void StageSet::BuildWings( VenueKit& inKit, Transform& inRoot )
{
    const float deck = m_plan.Stage.Height;
    // Wing platforms at deck height either side, upstage of the access stairs: guitar world on
    // the guitarist's side, monitor world on the bassist's.
    const float wingX = 10.3f;
    for( float side : { -1.f, 1.f } )
    {
        inKit.Box( Vector3( side * wingX, deck * 0.5f, 7.1f ), Vector3( 2.6f, deck, 5.8f ), kDeckColor, &inRoot );
        inKit.Box( Vector3( side * wingX, deck * 0.5f, 4.19f ), Vector3( 2.6f, deck, 0.02f ), kBlack, &inRoot );
    }

    // Guitar world: a rack of spares, the tech's bench and stool, a work light.
    const float rackX = -10.7f;
    inKit.Piece( Shape::Cube, Vector3( rackX, deck + 0.05f, 6.2f ), Vector3( 0.5f, 0.1f, 2.8f ), kBlack, &inRoot, kNone, false, "Rack" );
    inKit.Piece( Shape::Cube, Vector3( rackX - 0.2f, deck + 1.f, 6.2f ), Vector3( 0.04f, 0.04f, 2.8f ), kSteel, &inRoot, kNone, false, "Rack" );
    for( float z : { 4.85f, 7.55f } )
    {
        inKit.Piece( Shape::Cube, Vector3( rackX - 0.2f, deck + 0.5f, z ), Vector3( 0.04f, 1.f, 0.04f ), kSteel, &inRoot, kNone, false, "Rack" );
    }
    for( int i = 0; i < 4; ++i )
    {
        // Stood on end, necks up, leaning back on the rail, faces to the stage.
        const PropDef& model = i == 3 ? kBass : kGuitar;
        if( EntityHandle spare = Put( inKit, inRoot, model, Vector3( rackX, deck + 0.42f, 5.2f + static_cast<float>( i ) * 0.62f ) ) )
        {
            spare->GetComponent<Transform>().SetRotation( Quaternion::FromEulerDegrees( Vector3( 0.f, model.Yaw + 90.f, 0.f ) )
                * Quaternion::FromEulerDegrees( Vector3( -9.f, 0.f, 0.f ) ) * Quaternion::FromEulerDegrees( Vector3( 0.f, 0.f, -90.f ) ) );
        }
    }
    if( !Put( inKit, inRoot, kToolChest, Vector3( -10.9f, deck, 8.6f ), 90.f ) )
    {
        inKit.Box( Vector3( -10.9f, deck + 0.45f, 8.6f ), Vector3( 0.74f, 0.9f, 1.f ), kBlack, &inRoot );
    }
    Put( inKit, inRoot, kToolBox, Vector3( -10.9f, deck + 0.9f, 8.75f ), 80.f );
    inKit.Piece( Shape::Cube, Vector3( -10.95f, deck + 1.02f, 8.3f ), Vector3( 0.1f, 0.03f, 0.18f ), kNone, &inRoot, Vector3( 2.4f, 1.6f, 0.7f ), false, "Work light" );
    Put( inKit, inRoot, kStool, Vector3( -10.1f, deck, 8.4f ) );
    Put( inKit, inRoot, kCableCoil, Vector3( -9.9f, deck, 9.3f ) );
    Put( inKit, inRoot, kRoadCase, Vector3( -10.6f, deck, 9.45f ), 8.f );

    // Monitor world: the desk facing across the stage, its engineer's stool, amp and dimmer
    // racks behind it, the power distro, a cooler.
    const float deskX = 10.4f;
    const float deskZ = 6.f;
    inKit.Box( Vector3( deskX, deck + 0.42f, deskZ ), Vector3( 0.8f, 0.84f, 1.9f ), kBlack, &inRoot );
    if( EntityHandle surface = inKit.Piece( Shape::Cube, Vector3( deskX - 0.02f, deck + 0.93f, deskZ ), Vector3( 0.86f, 0.06f, 1.8f ), Vector3( 0.06f, 0.06f, 0.07f ), &inRoot, kNone, false, "Desk" ) )
    {
        // Tipped toward the engineer, who sits on the offstage side.
        surface->GetComponent<Transform>().SetRotation( Vector3( 0.f, 0.f, -12.f ) );
    }
    Dots( inKit, inRoot, Vector3( deskX - 0.12f, deck + 0.975f, deskZ - 0.78f ), Vector3( 0.f, 0.f, 0.12f ), 14, Vector3( 0.2f, 0.012f, 0.02f ), Vector3( 0.1f, 1.4f, 2.4f ), Vector3( 2.4f, 0.7f, 0.1f ) );
    for( float z : { -0.45f, 0.45f } )
    {
        inKit.Piece( Shape::Cube, Vector3( deskX - 0.36f, deck + 1.25f, deskZ + z ), Vector3( 0.03f, 0.34f, 0.56f ), kBlack, &inRoot, kNone, false, "Screen" );
        inKit.Piece( Shape::Cube, Vector3( deskX - 0.34f, deck + 1.25f, deskZ + z ), Vector3( 0.012f, 0.3f, 0.52f ), kNone, &inRoot, Vector3( 0.25f, 0.5f, 0.9f ), false, "Screen" );
    }
    Put( inKit, inRoot, kStool, Vector3( deskX + 0.75f, deck, deskZ ) );
    for( float z : { 7.9f, 8.55f } )
    {
        if( !Put( inKit, inRoot, kAmpRack, Vector3( 11.1f, deck, z ), -90.f ) )
        {
            inKit.Box( Vector3( 11.1f, deck + 0.65f, z ), Vector3( 0.64f, 1.3f, 0.6f ), kBlack, &inRoot );
        }
        // Signal lights down the rack's face, toward the stage.
        Dots( inKit, inRoot, Vector3( 10.76f, deck + 0.3f, z - 0.15f ), Vector3( 0.f, 0.16f, 0.f ), 6, Vector3( 0.012f, 0.02f, 0.02f ), Vector3( 0.2f, 3.f, 0.4f ), Vector3( 3.f, 1.5f, 0.1f ) );
    }
    if( !Put( inKit, inRoot, kPowerDistro, Vector3( 10.9f, deck, 9.4f ), -90.f ) )
    {
        inKit.Box( Vector3( 10.9f, deck + 0.5f, 9.4f ), Vector3( 0.8f, 1.f, 0.9f ), Vector3( 0.3f, 0.08f, 0.03f ), &inRoot );
    }
    Put( inKit, inRoot, kCooler, Vector3( 9.7f, deck, 9.3f ), 20.f );
    Put( inKit, inRoot, kBottle, Vector3( 9.55f, deck + 0.45f, 9.3f ) );
    Put( inKit, inRoot, kBeerCup, Vector3( 9.85f, deck + 0.45f, 9.25f ) );
    Put( inKit, inRoot, kRoadCase, Vector3( 10.9f, deck, 4.75f ), -6.f );
    if( EntityHandle ladder = Put( inKit, inRoot, kLadder, Vector3( 11.35f, deck, 7.2f ) ) )
    {
        // Leant against the racks.
        ladder->GetComponent<Transform>().SetRotation( Quaternion::FromEulerDegrees( Vector3( 0.f, kLadder.Yaw + 90.f, 0.f ) ) * Quaternion::FromEulerDegrees( Vector3( 0.f, 0.f, 10.f ) ) );
    }
}


void StageSet::BuildPixels( VenueKit& inKit, Transform& inRoot )
{
    const float deck = m_plan.Stage.Height;
    const float stageHalfWidth = m_plan.Stage.HalfWidth;
    const float trussHeight = m_plan.Stage.TrussHeight;
    // The LED strip along the stage's front edge.
    const float cell = stageHalfWidth * 2.f / static_cast<float>( kEdgeSegments );
    for( int i = 0; i < kEdgeSegments; ++i )
    {
        const float x = -stageHalfWidth + ( static_cast<float>( i ) + 0.5f ) * cell;
        m_edgeStrip.push_back( inKit.Piece( Shape::Cube, Vector3( x, deck - 0.08f, -0.06f ), Vector3( cell - 0.05f, 0.08f, 0.03f ), kNone, &inRoot, kNone, false, "Edge strip" ) );
    }
    // Pixel tubes up the crowd's side of the two front towers.
    for( float side : { -1.f, 1.f } )
    {
        for( int i = 0; i < kTubeSegments; ++i )
        {
            const float y = 1.7f + static_cast<float>( i ) * 1.3f;
            m_tubes.push_back( inKit.Piece( Shape::Cube, Vector3( side * ( stageHalfWidth + 0.4f ), y + 0.6f, kTrussZ[0] - 0.26f ), Vector3( 0.07f, 1.2f, 0.05f ), kNone, &inRoot, kNone, false, "Pixel tube" ) );
        }
    }
    // Battens along the crowd's face of each cross truss.
    const float span = ( stageHalfWidth - 0.4f ) * 2.f / static_cast<float>( kBattensPerTruss );
    for( float z : kTrussZ )
    {
        for( int i = 0; i < kBattensPerTruss; ++i )
        {
            const float x = -( stageHalfWidth - 0.4f ) + ( static_cast<float>( i ) + 0.5f ) * span;
            m_battens.push_back( inKit.Piece( Shape::Cube, Vector3( x, trussHeight, z - 0.26f ), Vector3( span - 0.25f, 0.07f, 0.05f ), kNone, &inRoot, kNone, false, "Batten" ) );
        }
    }
    // An LED wall is built of panels: seams a metre apart, just in front of the screen and
    // behind the lyric band. (Only on a wall facing straight out.)
    for( const VenuePlan::Screen& screen : m_plan.Screens )
    {
        if( !screen.Seams || screen.Yaw != 0.f )
        {
            continue;
        }
        const Vector3 wall( screen.Centre.x, screen.Centre.y, screen.Centre.z - 0.02f );
        const int columns = static_cast<int>( std::round( screen.Width ) );
        const int rows = static_cast<int>( std::round( screen.Height ) );
        for( int i = 1; i < columns; ++i )
        {
            inKit.Piece( Shape::Cube, wall + Vector3( -screen.Width * 0.5f + static_cast<float>( i ), 0.f, 0.f ), Vector3( 0.012f, screen.Height, 0.004f ), kNone, &inRoot, kNone, false, "Seam" );
        }
        for( int i = 1; i < rows; ++i )
        {
            inKit.Piece( Shape::Cube, wall + Vector3( 0.f, -screen.Height * 0.5f + static_cast<float>( i ), 0.f ), Vector3( screen.Width, 0.012f, 0.004f ), kNone, &inRoot, kNone, false, "Seam" );
        }
    }
}


void StageSet::BuildArena( VenueKit& inKit, Transform& inRoot )
{
    // The front-of-house truss the follow spots work from (StageLights puts them at y 11, z -9),
    // hung from the roof grid, a lamp housing at each spot.
    const float z = -9.f;
    Truss( inKit, inRoot, Vector3( -6.f, 11.45f, z ), Vector3( 6.f, 11.45f, z ), kTrussSize, kSteel );
    for( float x : { -5.f, 5.f } )
    {
        Beam( inKit, inRoot, Vector3( x, 11.65f, z ), Vector3( x, 19.4f, z ), 0.03f, kSteel );
        inKit.Piece( Shape::Cube, Vector3( x, 12.2f, z ), Vector3( 0.26f, 0.5f, 0.3f ), Vector3( 0.5f, 0.38f, 0.04f ), &inRoot, kNone, false, "Hoist" );
    }
    for( float x : { -2.72f, -1.84f, 0.f, 1.84f } )
    {
        if( EntityHandle housing = inKit.Piece( Shape::Cube, Vector3( x, 11.f, z - 0.1f ), Vector3( 0.34f, 0.34f, 0.8f ), kBlack, &inRoot, kNone, false, "Follow spot" ) )
        {
            housing->GetComponent<Transform>().LookDirection( Vector3( 0.f, -0.55f, 0.83f ) );
        }
        inKit.Piece( Shape::Cube, Vector3( x, 11.3f, z ), Vector3( 0.05f, 0.3f, 0.05f ), kSteel, &inRoot, kNone, false, "Yoke" );
    }
    // Broadcast cameras on the mixing riser's front corners (the riser's top is 0.9 m up; the
    // desk and its railings are VenueShow's).
    for( float side : { -1.f, 1.f } )
    {
        Put( inKit, inRoot, kCameraTripod, Vector3( side * 2.45f, 0.9f, -20.35f ), -side * 6.f );
        Put( inKit, inRoot, kCableCoil, Vector3( side * 1.5f, 0.9f, -20.4f ) );
    }
    Put( inKit, inRoot, kStool, Vector3( 0.6f, 0.9f, -22.6f ) );
    Put( inKit, inRoot, kStool, Vector3( -0.9f, 0.9f, -22.7f ) );
}


void StageSet::BuildClub( VenueKit& inKit, Transform& inRoot, uint32_t inSeed )
{
    const float deck = m_plan.Stage.Height;
    const float backWallZ = m_plan.Stage.BackWallZ;
    // Small and scrappy: years of gig posters on the wall either side of the screen and down
    // the side walls by the stage, a merch table against the wall near the bar.
    const Vector3 inks[5] = { Vector3( 0.45f, 0.06f, 0.05f ), Vector3( 0.5f, 0.4f, 0.08f ), Vector3( 0.06f, 0.2f, 0.4f ), Vector3( 0.4f, 0.38f, 0.33f ), Vector3( 0.05f, 0.3f, 0.2f ) };
    for( uint32_t i = 0; i < 22; ++i )
    {
        const float side = i % 2 == 0 ? -1.f : 1.f;
        const float x = side * ( 6.7f + VenueTiming::Noise( inSeed + i, 3u ) * 4.6f );
        const float y = deck + 1.1f + VenueTiming::Noise( inSeed + i, 5u ) * 2.2f;
        const float size = 0.4f + VenueTiming::Noise( inSeed + i, 7u ) * 0.25f;
        EntityHandle poster = inKit.Piece( Shape::Cube, Vector3( x, y, backWallZ - 0.01f - 0.002f * static_cast<float>( i ) ), Vector3( size, size * 1.4f, 0.004f ),
            inks[static_cast<int>( VenueTiming::Noise( inSeed + i, 9u ) * 5.f ) % 5], &inRoot, kNone, false, "Poster" );
        if( poster ) poster->GetComponent<Transform>().SetRotation( Vector3( 0.f, 0.f, ( VenueTiming::Noise( inSeed + i, 11u ) - 0.5f ) * 14.f ) );
    }
    for( uint32_t i = 0; i < 14; ++i )
    {
        const float side = i % 2 == 0 ? -1.f : 1.f;
        const float z = -1.f - VenueTiming::Noise( inSeed + i, 13u ) * 7.f;
        const float y = 1.5f + VenueTiming::Noise( inSeed + i, 15u ) * 1.6f;
        inKit.Piece( Shape::Cube, Vector3( side * 12.58f, y, z ), Vector3( 0.004f, 0.62f, 0.44f ), inks[static_cast<int>( VenueTiming::Noise( inSeed + i, 17u ) * 5.f ) % 5], &inRoot, kNone, false, "Poster" );
    }
    // Merch: a trestle table of shirts and records, the shirts pinned up behind it, a lit sign.
    const float x = -12.2f;
    const float z = -12.6f;
    inKit.Box( Vector3( x, 0.74f, z ), Vector3( 0.6f, 0.05f, 2.f ), Vector3( 0.2f, 0.12f, 0.06f ), &inRoot );
    for( float end : { -0.9f, 0.9f } )
    {
        inKit.Piece( Shape::Cube, Vector3( x, 0.36f, z + end ), Vector3( 0.5f, 0.72f, 0.04f ), kSteel, &inRoot, kNone, false, "Trestle" );
    }
    for( int i = 0; i < 4; ++i )
    {
        const Vector3& ink = inks[( i + static_cast<int>( inSeed % 5u ) ) % 5];
        inKit.Piece( Shape::Cube, Vector3( x, 0.79f, z - 0.72f + static_cast<float>( i ) * 0.48f ), Vector3( 0.4f, 0.05f, 0.34f ), ink, &inRoot, kNone, false, "Shirts" );
        inKit.Piece( Shape::Cube, Vector3( -12.57f, 2.f, z - 0.72f + static_cast<float>( i ) * 0.48f ), Vector3( 0.01f, 0.5f, 0.4f ), ink, &inRoot, kNone, false, "Shirt" );
    }
    inKit.Piece( Shape::Cube, Vector3( -12.56f, 2.6f, z ), Vector3( 0.02f, 0.16f, 1.2f ), kNone, &inRoot, Vector3( 2.4f, 2.f, 1.2f ), false, "Merch sign" );
    Put( inKit, inRoot, kCardboardBox, Vector3( x, 0.f, z + 0.3f ) );
    // Kegs and crates by the bar's end.
    Put( inKit, inRoot, kKeg, Vector3( 7.6f, 0.f, -16.3f ) );
    Put( inKit, inRoot, kKeg, Vector3( 8.15f, 0.f, -16.4f ) );
}


void StageSet::BuildFestival( VenueKit& inKit, Transform& inRoot, uint32_t inSeed )
{
    // Scaffold PA towers either side of the stage with the line arrays hung off their fronts, and
    // the tour's banners down the canopy's front corners.
    const Vector3 banners[4] = { Vector3( 0.45f, 0.04f, 0.05f ), Vector3( 0.04f, 0.14f, 0.42f ), Vector3( 0.45f, 0.3f, 0.03f ), Vector3( 0.26f, 0.04f, 0.4f ) };
    const Vector3 banner = banners[inSeed % 4u];
    for( float side : { -1.f, 1.f } )
    {
        const float x = side * 13.4f;
        for( float dx : { -0.7f, 0.7f } )
        {
            for( float dz : { -0.7f, 0.7f } )
            {
                Beam( inKit, inRoot, Vector3( x + dx, 0.f, -0.6f + dz ), Vector3( x + dx, 11.f, -0.6f + dz ), 0.06f, kSteel, true );
            }
        }
        for( int level = 1; level <= 5; ++level )
        {
            const float y = 2.2f * static_cast<float>( level );
            for( float d : { -0.7f, 0.7f } )
            {
                Beam( inKit, inRoot, Vector3( x - 0.7f, y, -0.6f + d ), Vector3( x + 0.7f, y, -0.6f + d ), 0.045f, kSteel );
                Beam( inKit, inRoot, Vector3( x + d, y, -1.3f ), Vector3( x + d, y, 0.1f ), 0.045f, kSteel );
                // Cross-bracing on the faces the crowd sees.
                Beam( inKit, inRoot, Vector3( x - 0.7f, y - 2.2f, -0.6f + d ), Vector3( x + 0.7f, y, -0.6f + d ), 0.03f, kSteel );
            }
        }
        for( int cabinet = 0; cabinet < 9; ++cabinet )
        {
            // The array curves under as it comes down.
            const float y = 10.4f - static_cast<float>( cabinet ) * 0.52f;
            const float tuck = 0.012f * static_cast<float>( cabinet * cabinet );
            Cabinet( inKit, inRoot, Vector3( x, y - 0.24f, -1.75f + tuck ), Vector3( 1.3f, 0.48f, 0.6f ), kBlack, kGrille );
        }
        inKit.Piece( Shape::Cube, Vector3( side * 10.7f, 8.3f, -1.05f ), Vector3( 1.5f, 7.4f, 0.03f ), banner, &inRoot, kNone, false, "Banner" );
        inKit.Piece( Shape::Cube, Vector3( side * 10.7f, 9.6f, -1.07f ), Vector3( 0.9f, 0.9f, 0.02f ), Vector3( 0.6f, 0.58f, 0.5f ), &inRoot, kNone, false, "Banner" );
        inKit.Piece( Shape::Cube, Vector3( side * 10.7f, 6.4f, -1.07f ), Vector3( 1.1f, 0.14f, 0.02f ), Vector3( 0.6f, 0.58f, 0.5f ), &inRoot, kNone, false, "Banner" );

        // Festoon bulbs strung from the mixing tent out to the first delay tower and on to the
        // second, sagging between.
        const Vector3 warm( 2.6f, 1.6f, 0.6f );
        const Vector3 posts[3] = { Vector3( side * 3.5f, 3.5f, -24.f ), Vector3( side * 14.f, 7.6f, -26.f ), Vector3( side * 14.f, 7.6f, -40.f ) };
        for( int run = 0; run < 2; ++run )
        {
            for( int bulb = 1; bulb < 12; ++bulb )
            {
                const float t = static_cast<float>( bulb ) / 12.f;
                Vector3 at = posts[run] + ( posts[run + 1] - posts[run] ) * t;
                at.y -= 1.4f * 4.f * t * ( 1.f - t );
                inKit.Piece( Shape::Sphere, at, Vector3( 0.16f, 0.16f, 0.16f ), kNone, &inRoot, warm, false, "Festoon" );
            }
        }
        // Out at the field's edges, past the crowd: food stalls with their tables and bins.
        for( float z : { -15.f, -24.f } )
        {
            Put( inKit, inRoot, kFoodStall, Vector3( side * 30.5f, 0.f, z ), -side * 90.f, 2.2f );
            Put( inKit, inRoot, kWheelieBin, Vector3( side * 30.2f, 0.f, z + 2.6f ), -side * 90.f );
        }
        Put( inKit, inRoot, kUmbrellaTable, Vector3( side * 31.f, 0.f, -19.5f ) );
        Put( inKit, inRoot, kBarrel, Vector3( side * 12.6f, 0.f, 1.4f ) );
    }
    // Backstage: the tour's truck and bus parked behind the stage's ends.
    Put( inKit, inRoot, kTruck, Vector3( -17.5f, 0.f, 14.f ), 24.f );
    Put( inKit, inRoot, kTourBus, Vector3( 19.f, 0.f, 16.f ), -18.f );
    Put( inKit, inRoot, kPallet, Vector3( -13.5f, 0.f, 9.5f ) );
    Put( inKit, inRoot, kKeg, Vector3( -13.4f, 0.2f, 9.4f ) );
    // Flags on tall poles, planted where they read above the crowd's heads.
    const Vector3 poles[7] = { Vector3( -8.f, 0.f, -13.f ), Vector3( 6.5f, 0.f, -19.f ), Vector3( -16.f, 0.f, -24.f ), Vector3( 13.f, 0.f, -10.5f ),
        Vector3( 19.f, 0.f, -31.f ), Vector3( -3.5f, 0.f, -34.f ), Vector3( -21.f, 0.f, -12.f ) };
    for( int i = 0; i < 7; ++i )
    {
        const PropDef& flag = ( i % 2 == 0 || !Has( kFlagB ) ) ? kFlagA : kFlagB;
        const float yaw = VenueTiming::Noise( inSeed, 90u + static_cast<uint32_t>( i ) ) * 60.f - 30.f;
        if( EntityHandle pole = Put( inKit, inRoot, flag, poles[i], yaw, 1.6f ) )
        {
            m_flags.push_back( pole );
            m_flagYaws.push_back( flag.Yaw + yaw );
        }
    }
}


void StageSet::Update( const Show& inShow )
{
    const Vector3 glow = inShow.Glow;
    const float hype = std::clamp( inShow.Hype, 0.f, 1.f );
    const float lift = std::max( std::clamp( inShow.Energy, 0.f, 1.f ), hype );
    const double beat = inShow.Beat;
    const float pulse = static_cast<float>( std::pow( 1.0 - ( beat - std::floor( beat ) ), 2.0 ) );
    const Vector3 idle( 0.02f, 0.02f, 0.03f );

    // The edge strip glows with the rig, a chase running along it on the beat.
    for( size_t i = 0; i < m_edgeStrip.size(); ++i )
    {
        const double phase = beat * 2.0 - static_cast<double>( i ) * 0.25;
        const float chase = 0.5f + 0.5f * static_cast<float>( std::pow( 1.0 - ( phase - std::floor( phase ) ), 3.0 ) );
        VenueKit::SetColor( m_edgeStrip[i], kNone, glow * ( 3.f * chase ) + idle );
    }
    // The riser's fascia thumps with the kick, brightest in the middle.
    for( size_t i = 0; i < m_fascia.size(); ++i )
    {
        const float off = std::abs( static_cast<float>( i ) - ( kFasciaSegments - 1 ) * 0.5f ) / ( ( kFasciaSegments - 1 ) * 0.5f );
        const float level = 0.25f + 3.2f * inShow.Kick * ( 1.f - 0.65f * off );
        VenueKit::SetColor( m_fascia[i], kNone, ( glow + Vector3( 0.12f, 0.12f, 0.12f ) ) * level + idle );
    }
    // The tower tubes are level meters: they fill from the bottom on each beat, higher the more
    // the room is going.
    const float fill = 0.2f + 0.8f * pulse * ( 0.35f + 0.65f * lift );
    for( size_t i = 0; i < m_tubes.size(); ++i )
    {
        const float height = ( static_cast<float>( i % kTubeSegments ) + 0.5f ) / static_cast<float>( kTubeSegments );
        VenueKit::SetColor( m_tubes[i], kNone, glow * ( height < fill ? 3.5f : 0.35f ) + idle );
    }
    // The truss battens chase across, quicker and brighter with the hype; at the peak they sparkle
    // white on the half beat.
    const int sparkle = static_cast<int>( std::floor( beat * 2.0 ) );
    for( size_t i = 0; i < m_battens.size(); ++i )
    {
        const int truss = static_cast<int>( i ) / kBattensPerTruss;
        const int cell = static_cast<int>( i ) % kBattensPerTruss;
        const double phase = beat * ( 1.0 + static_cast<double>( hype ) ) - static_cast<double>( cell ) / kBattensPerTruss + truss * 0.33;
        const float chase = static_cast<float>( std::pow( 1.0 - ( phase - std::floor( phase ) ), 3.0 ) );
        Vector3 color = glow * ( 0.6f + 3.f * chase * ( 0.4f + hype ) ) + idle;
        if( hype > 0.6f && VenueTiming::Noise( static_cast<uint32_t>( sparkle ), static_cast<uint32_t>( i ) ) > 0.72f )
        {
            color = Vector3( 4.f, 3.8f, 3.4f ) * hype;
        }
        VenueKit::SetColor( m_battens[i], kNone, color );
    }
    // Flags sway on their poles.
    const float t = static_cast<float>( inShow.Seconds );
    for( size_t i = 0; i < m_flags.size(); ++i )
    {
        if( !m_flags[i] ) continue;
        m_flags[i]->GetComponent<Transform>().SetRotation( Quaternion::FromEulerDegrees( Vector3( 0.f, m_flagYaws[i], 0.f ) )
            * Quaternion::FromEulerDegrees( Vector3( 3.f * std::sin( t * 1.1f + static_cast<float>( i ) * 1.7f ), 0.f, 4.f * std::sin( t * 0.8f + static_cast<float>( i ) ) ) ) );
    }
}
