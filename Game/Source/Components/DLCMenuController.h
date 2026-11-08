#pragma once
#include <ECS/Component.h>
#include <ECS/ComponentDetail.h>
#include "CoreGame/TrackList.h"
#include "Path.h"
#include <atomic>
#include <deque>
#include <memory>
#include <string>
#include <thread>
#include <vector>

class TrackRadioUtils;

// Drives Assets/UI/DLC.rml through the "dlc_store" view model: the DLC server's catalogue
// (dlc_index.json, Docs/Songs-and-DLC.md) with sort/filter, a details panel, downloads into
// Assets/DLC, and the radio widget. Network work runs on one worker thread, a transfer at a time;
// the controller polls it every update and only ever touches the track database on the main thread.
class DLCMenuController final
    : public Component<DLCMenuController>
{
public:
    DLCMenuController();
    ~DLCMenuController();

    void Update( float inDeltaTime );

private:
    // One song of the server's catalogue.
    struct CatalogueTrack
    {
        std::string Title;
        std::string Artist;
        std::string Album;
        std::string Source;        // The DLCSource tag (song.ini's icon)
        std::string Folder;        // FolderPath on the server, and under Assets/DLC
        std::string ArtFile;       // AlbumArtFileName ("" when the server found none)
        std::vector<std::string> Files;
        int Year = 0;
        int InstalledIndex = -1;   // Its TrackDatabase index once installed
        std::string State;         // "", "Queued", "Downloading 3/12", "Failed", "Installed"
        bool Busy = false;
    };

    // A worker-thread download: the index, one track's art, or every file of a track.
    struct Transfer
    {
        enum class Kind { Index, Art, Track };
        Kind Type = Kind::Index;
        int Track = -1;
        std::vector<std::pair<std::string, Path>> Files;
        std::atomic<int> Done{ 0 };
        std::atomic<bool> Finished{ false };
        std::atomic<bool> Cancel{ false };
        bool Succeeded = false;
        std::thread Thread;
    };

    void PopulateModel();
    void BeginIndexFetch();
    void LoadIndex( const std::string& inText, const std::string& inStatus );
    void QueueMissingArt();
    void QueueTrackDownload( int inTrack );
    void PumpTransfers();
    void FinishTransfer( Transfer& inTransfer );
    void RefreshRows();
    void RefreshRow( int inTrack );
    void RefreshFilters();
    void SelectTrack( int inTrack );
    void PlayInstalled( int inTrack );
    void PreviewInstalled( int inTrack );
    std::string ArtSource( const CatalogueTrack& inTrack ) const;
    std::string FileURL( const CatalogueTrack& inTrack, const std::string& inFile ) const;
    Path FilePath( const CatalogueTrack& inTrack, const std::string& inFile ) const;
    Path ArtCachePath( const CatalogueTrack& inTrack ) const;
    bool TrackPassesFilter( const CatalogueTrack& inTrack ) const;
    std::vector<int> SortedTracks() const;

    std::unique_ptr<TrackRadioUtils> m_radioUtils;
    std::vector<CatalogueTrack> m_catalogue;
    std::vector<int> m_rowOfTrack;          // Catalogue index -> row of the "tracks" list, or -1
    std::deque<std::unique_ptr<Transfer>> m_queue;
    std::unique_ptr<Transfer> m_active;
    std::string m_server;
    TrackListSort m_sort = TrackListSort::None;
    TrackListFilter m_filter = TrackListFilter::None;
    int m_selectedTrack = -1;
    int m_previewTrack = -1;
    float m_previewDelay = 0.f;
    bool m_modelReady = false;
};

ME_REGISTER_COMPONENT( DLCMenuController )
