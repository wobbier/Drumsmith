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

// Drives Assets/UI/DLC.rml through the "dlc_store" view model: the catalogue of every DLC server
// in the settings (each one's dlc_index.json, Docs/Songs-and-DLC.md) with sort/filter, a details
// panel, downloads, updates and removals under Assets/DLC, previews of songs not downloaded yet,
// and the radio widget. Network work runs on one worker thread, a transfer at a time;
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
        std::string AudioFile;     // TrackFileName: the main mix, for a preview
        std::string Version;       // The server's hash of the song's files ("" on an old index)
        std::vector<std::string> Files;
        std::vector<long long> FileSizes;   // Beside Files; empty on an old index
        int Server = 0;            // Which of m_servers lists it
        int Year = 0;
        float PreviewPercent = 0.25f;
        bool Authored = false;     // Charted in the Track Editor: the "DS ready" badge
        int InstalledIndex = -1;   // Its TrackDatabase index once installed
        bool UpdateAvailable = false;   // Installed from a server whose copy has changed since
        std::string State;         // "", "Queued", "Downloading 3/12", "Failed", "Installed", ...
        bool Busy = false;
        bool ArtQueued = false;
    };

    // A server of the settings, and how fetching its index went.
    struct Server
    {
        std::string Url;
        std::string RemoteHash;    // dlc_index.hash as just fetched ("" when it has none)
        int Songs = 0;
        bool Loaded = false;
        bool Reached = true;
    };

    // A worker-thread download: a server's index hash or index, one track's art, every file of a
    // track, or the audio for a preview.
    struct Transfer
    {
        enum class Kind { Hash, Index, Art, Track, Preview };
        struct FileJob
        {
            std::string Url;
            Path Target;
            long long Size = -1;   // What the index says it is; checked when known
        };
        Kind Type = Kind::Index;
        int Track = -1;
        int Server = -1;
        std::vector<FileJob> Files;
        std::atomic<int> Done{ 0 };
        std::atomic<bool> Finished{ false };
        std::atomic<bool> Cancel{ false };
        bool Succeeded = false;
        std::thread Thread;
    };

    void PopulateModel();
    void BeginIndexFetch();
    // Adds a server's index to the catalogue; songs an earlier server already lists are skipped.
    void AppendIndex( int inServer, const std::string& inText );
    void LoadCachedIndex( int inServer );
    void UpdateStatus();
    void QueueMissingArt();
    void QueueTrackDownload( int inTrack );
    void QueuePreview( int inTrack );
    void RemoveInstalled( int inTrack );
    // Whether the installed copy matches the server's (the version noted at download).
    void RefreshInstallState( CatalogueTrack& ioTrack ) const;
    std::string ServerCacheFolder( int inServer ) const;
    Path PreviewPath( const CatalogueTrack& inTrack ) const;
    void PumpTransfers();
    void FinishTransfer( Transfer& inTransfer );
    void RefreshRows();
    void RefreshRow( int inTrack );
    void RefreshFilters();
    void SelectTrack( int inTrack );
    void PlayInstalled( int inTrack );
    void PreviewInstalled( int inTrack );
    void EditInstalled( int inTrack );
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
    std::vector<Server> m_servers;
    int m_pendingServers = 0;
    // The song whose Remove is waiting for a yes, and the preview file last fetched.
    int m_confirmRemove = -1;
    std::string m_previewFile;
    TrackListSort m_sort = TrackListSort::None;
    TrackListFilter m_filter = TrackListFilter::None;
    int m_selectedTrack = -1;
    int m_previewTrack = -1;
    float m_previewDelay = 0.f;
    bool m_modelReady = false;
};

ME_REGISTER_COMPONENT( DLCMenuController )
