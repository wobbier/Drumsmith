#pragma once
#include "Dementia.h"
#include <algorithm>
#include <any>
#include <cstdint>
#include <functional>
#include <memory>
#include <numeric>
#include <string>
#include <vector>

#if USING( ME_EDITOR )

// Which part of the chart a track edits; the preview rebuilds only what changed.
enum class ChartDomain : uint8_t
{
    Notes = 0,
    Beats,
    Phrases,
    Venue,
    Count
};

// How the Track Editor's timeline groups its tracks.
enum class TrackGroup : uint8_t
{
    Notes = 0,
    Gameplay,
    Structure,
    Venue,
    Band,
    Lyrics,
    Count
};

inline const char* TrackGroupName( TrackGroup inGroup )
{
    switch( inGroup )
    {
    case TrackGroup::Notes: return "Notes";
    case TrackGroup::Gameplay: return "Gameplay";
    case TrackGroup::Structure: return "Song Structure";
    case TrackGroup::Venue: return "Venue";
    case TrackGroup::Band: return "Band";
    case TrackGroup::Lyrics: return "Lyrics";
    default: return "";
    }
}

// One kind of chart event as rows on the Track Editor's timeline (Docs/Songs-and-DLC.md): the
// notes, a list of lighting cues, the star power phrases, ... Items are addressed by index into the
// list the track is bound to, so indices change when items are added, removed or sorted.
class IEventTrack
{
public:
    virtual ~IEventTrack() = default;

    std::string Name;
    TrackGroup Group = TrackGroup::Venue;
    ChartDomain Domain = ChartDomain::Venue;
    // Items have a length (held spans) rather than being a moment.
    bool Spans = false;
    // One name per row; a track with no names has one row.
    std::vector<std::string> RowNames;
    uint32_t Color = 0xFFC8C8C8; // ABGR, as ImGui packs it

    int Rows() const { return RowNames.empty() ? 1 : static_cast<int>( RowNames.size() ); }

    virtual int Count() const = 0;
    virtual double Start( int inItem ) const = 0;
    virtual double End( int inItem ) const { return Start( inItem ); }
    virtual int Row( int inItem ) const { return 0; }
    virtual void Set( int inItem, double inStart, double inEnd, int inRow ) = 0;
    // Appends an item and answers its index.
    virtual int Add( double inStart, double inEnd, int inRow ) = 0;
    // inItems ascending.
    virtual void Remove( const std::vector<int>& inItems ) = 0;
    virtual std::string Label( int inItem ) const { return {}; }
    virtual uint32_t ItemColor( int inItem ) const { return Color; }

    // The whole list, for undo.
    virtual std::any Snapshot() const = 0;
    virtual void Restore( const std::any& inSnapshot ) = 0;
    // Some items, for the clipboard; Paste appends them moved by inOffset seconds and answers
    // their indices.
    virtual std::any Copy( const std::vector<int>& inItems ) const = 0;
    virtual std::vector<int> Paste( const std::any& inItems, double inOffset ) = 0;
    // Orders the list by time, keeping ioSelection on the same items.
    virtual void Sort( std::vector<int>& ioSelection ) = 0;

    // The selected items' fields (ImGui). Calls inBeforeChange before the first change it makes.
    virtual void DrawProperties( const std::vector<int>& inItems, const std::function<void()>& inBeforeChange ) {}
};

// A track over a std::vector of the chart.
template<class T>
class VectorTrack
    : public IEventTrack
{
public:
    explicit VectorTrack( std::vector<T>& inItems )
        : Items( &inItems )
    {
    }

    int Count() const override { return static_cast<int>( Items->size() ); }

    void Remove( const std::vector<int>& inItems ) override
    {
        for( auto it = inItems.rbegin(); it != inItems.rend(); ++it )
        {
            if( *it >= 0 && *it < Count() )
            {
                Items->erase( Items->begin() + *it );
            }
        }
    }

    std::any Snapshot() const override { return *Items; }

    void Restore( const std::any& inSnapshot ) override
    {
        if( const auto* items = std::any_cast<std::vector<T>>( &inSnapshot ) )
        {
            *Items = *items;
        }
    }

    std::any Copy( const std::vector<int>& inItems ) const override
    {
        std::vector<T> copied;
        for( int item : inItems )
        {
            if( item >= 0 && item < Count() )
            {
                copied.push_back( ( *Items )[item] );
            }
        }
        return copied;
    }

    std::vector<int> Paste( const std::any& inItems, double inOffset ) override
    {
        std::vector<int> pasted;
        if( const auto* items = std::any_cast<std::vector<T>>( &inItems ) )
        {
            for( const T& item : *items )
            {
                Items->push_back( item );
                const int index = Count() - 1;
                Set( index, std::max( 0.0, Start( index ) + inOffset ), std::max( 0.0, End( index ) + inOffset ), Row( index ) );
                pasted.push_back( index );
            }
        }
        return pasted;
    }

    void Sort( std::vector<int>& ioSelection ) override
    {
        std::vector<int> order( Items->size() );
        std::iota( order.begin(), order.end(), 0 );
        std::stable_sort( order.begin(), order.end(), [this]( int a, int b ) { return Start( a ) < Start( b ); } );
        std::vector<T> sorted;
        sorted.reserve( Items->size() );
        std::vector<int> movedTo( Items->size() );
        for( size_t i = 0; i < order.size(); ++i )
        {
            sorted.push_back( ( *Items )[order[i]] );
            movedTo[order[i]] = static_cast<int>( i );
        }
        *Items = std::move( sorted );
        for( int& item : ioSelection )
        {
            if( item >= 0 && item < static_cast<int>( movedTo.size() ) )
            {
                item = movedTo[item];
            }
        }
        std::sort( ioSelection.begin(), ioSelection.end() );
    }

    std::vector<T>* Items = nullptr;
};

class TrackData;

namespace EventTracks
{
    // Every editable track of a chart, the notes first.
    std::vector<std::unique_ptr<IEventTrack>> Build( TrackData& inChart );
}

#endif
