#include "TrackList.h"
#include <filesystem>
#include "Core/Assert.h"
#include "CustomTrackDefineTest.h"
#include "JSON.h"
#include "Utils/StringUtils.h"
#include "CLog.h"

DISABLE_OPTIMIZATION;

TrackList::TrackList()
    : ConfigFile( Path( "Assets/TrackDatabase.json" ) )
{
    if( !m_configFile.Data.empty() )
    {
        //Save();
    }

    //Load();
}

void TrackList::OnSave( json& outJson )
{
}

void TrackList::OnLoadConfig( const json& outJson )
{
}

namespace fs = std::filesystem;

bool fileExistsInDirectory( const fs::path& dirPath, const std::string& fileName )
{
    for( const auto& entry : fs::directory_iterator( dirPath ) )
    {
        if( entry.is_regular_file() && entry.path().filename() == fileName )
        {
            return true;
        }
    }
    return false;
}


PadId ConvertLegacyPad( int inPad )
{
    switch( inPad )
    {
    case 0:
        return PadId::Bass;
    case 1:
        return PadId::Snare;
    case 2:
        return PadId::ClosedHiHat;
    default:
        break;
    }
    return PadId::Bass;
}


LegacySongMetaData ConvertFromLegacy( const std::string& inTrackDirectory, TrackData& outNewTrack )
{
    // bro 💀 https://xkcd.com/927/
    LegacySongMetaData metadata = CustomTrackDefineTest::GetInstance().readSongMetaData( inTrackDirectory + "/song.ini" );

    outNewTrack.m_trackName = metadata.m_name;
    outNewTrack.m_artistName = metadata.m_artist;
    outNewTrack.m_genre = metadata.m_genre;
    outNewTrack.m_year = std::stoi( metadata.m_year );
    outNewTrack.m_icon = metadata.m_icon;
    if( metadata.m_previewStartTime > 0 )
    {
        outNewTrack.m_previewPercent = ( metadata.m_previewStartTime / (float)metadata.m_songLength );
    }
    outNewTrack.m_durationMS = metadata.m_songLength;
    outNewTrack.m_duration = metadata.m_songLength / 1000.f;

    Path albumArtPath( inTrackDirectory + "/album.jpg" );
    if( !albumArtPath.Exists )
    {
        albumArtPath = Path( inTrackDirectory + "/album.png" );
    }
    ME_ASSERT( albumArtPath.Exists );
    outNewTrack.m_albumArtPath = albumArtPath.GetLocalPathString();

    // I don't know how much this differs from chart to chart

    Path songFile( inTrackDirectory + "/song.ogg" );
    if( !songFile.Exists )
    {
        // opus will require some manual converting... as fmod doesn't support this type atm
        //outNewTrack.m_trackFileName = "song.opus";
        //outNewTrack.m_trackSourcePath = inTrackDirectory + "song.opus";
    }
    else
    {
        outNewTrack.m_trackFileName = "song.ogg";
        outNewTrack.m_trackSourcePath = inTrackDirectory + "/song.ogg";
    }

    outNewTrack.m_bpm = 110;//(float)inLegacyData.syncTracks[0].value >> 3;
    outNewTrack.m_noteSpeed = 10;//(float)inLegacyData.syncTracks[0].value >> 3;

    outNewTrack.m_bpm = 180.f;

    outNewTrack.Save();
    return metadata;
}

TrackDatabase::TrackDatabase()
{
    Reload();
}


void TrackDatabase::Reload()
{
    m_trackList.Clear();
    m_trackList.m_tracks.clear();
    fs::path rootPath = Path( "Assets/DLC" ).FullPath;  // Replace with your directory path
    std::vector<Path> m_drumlessSongs;
    try
    {
        for( const auto& entry : fs::directory_iterator( rootPath ) )
        {
            if( entry.is_directory() )
            {
                // #TODO: Support CHART DLC files
                //bool chartFormat = fileExistsInDirectory( entry.path(), "notes.chart" );
                //if( chartFormat )
                //{
                //    //Path midiPath = Path( std::string( entry.path().u8string() ) );
                //    //    
                //    //if( !CustomTrackDefineTest::GetInstance().ParseMidi( midiPath ) )
                //    //{
                //    //    m_drumlessSongs.push_back( midiPath );
                //    //}
                //    continue;
                //}

                // #TODO: Do we even support OPUS? I would need to convert it for fmod...
                //bool opusFormat = fileExistsInDirectory( entry.path(), "song.opus" );
                //if( opusFormat )
                //{
                //    YIKES( entry.path().u8string().c_str() );
                //    continue;
                //}

                // Check for any Custom DLC from other formats
                //bool exists = fileExistsInDirectory( entry.path(), "song.ini" );
                //if( exists )
                //{
                //    Path chartFilePath = Path( entry.path().u8string() + "/notes.chart" );
                //    Song rbCustomTrack;
                //    if( chartFilePath.Exists )
                //    {
                //        rbCustomTrack = CustomTrackDefineTest::GetInstance().readSongFile( chartFilePath.FullPath );
                //    }
                //    TrackData newTrack = TrackData( Path( chartFilePath.GetDirectoryString() + "/NoteData.txt" ) );
                //
                //    m_trackList.m_tracks.push_back( ConvertFromLegacy( chartFilePath.GetDirectoryString(), rbCustomTrack, newTrack ) );
                //    //newTrack.Save();
                //}
                //else
                {
                    bool exists = fileExistsInDirectory( entry.path(), "TrackData.txt" );
                    if( exists )
                    {
                        m_trackList.m_tracks.emplace_back( TrackData( Path( entry.path().u8string() + "/TrackData.txt" ) ) );
                        m_trackList.m_tracks.back().Load();

                        Path trackPath( m_trackList.m_tracks.back().m_trackSourcePath );
                        if( !trackPath.Exists )
                        {
                            YIKES_FMT( "Song does not exist in directory: %s", m_trackList.m_tracks.back().m_trackFileName.c_str() );
                            continue;
                        }
                    }
                    else
                    {
                        YIKES_FMT( "TrackData.txt doesn't exist for: %s", entry.path().u8string().c_str() );
                    }
                }
            }
        }
    }
    catch( fs::filesystem_error& e )
    {
        std::cout << e.what() << std::endl;
    }

    for( auto& path : m_drumlessSongs )
    {
        YIKES( path.FullPath.c_str() );
    }

    //for (auto& path : m_trackList.m_tracks)
    //{
    //    path.LoadNoteData();
    //    path.Save();
    //}
}


bool TrackDatabase::RegisterNewTrack( const std::string& inDirectory )
{
    auto it = std::find_if( m_trackList.m_tracks.begin(), m_trackList.m_tracks.end(),
        [&]( const TrackData& track )
        {
            return track.m_trackSourcePath.rfind( inDirectory ) != std::string::npos;
        } );

    if( it != m_trackList.m_tracks.end() )
    {
        YIKES_FMT( "Track already registered for directory: %s", inDirectory.c_str() );
        return false;
    }

    m_trackList.m_tracks.emplace_back( TrackData( Path( "Assets/DLC/" + inDirectory + "/TrackData.txt" ) ) );
    m_trackList.m_tracks.back().Load();

    Path trackPath( m_trackList.m_tracks.back().m_trackSourcePath );
    if( !trackPath.Exists )
    {
        YIKES_FMT( "Song does not exist in directory: %s", m_trackList.m_tracks.back().m_trackFileName.c_str() );
    }
    m_needsSort = true;
    return true;
}

void TrackDatabase::ExportMidiTrackMetaData()
{
    fs::path rootPath = Path( "Assets/DLC" ).FullPath;
    try
    {
        for( const auto& entry : fs::directory_iterator( rootPath ) )
        {
            if( !entry.is_directory() )
            {
                continue;
            }

            // #TODO: Support MIDI DLC files
            bool midiFormat = fileExistsInDirectory( entry.path(), "notes.mid" );
            if( midiFormat )
            {
                Path midiPath = Path( std::string( entry.path().u8string() ) );

                TrackData newTrack = TrackData( Path( midiPath.FullPath + "/NoteData.txt" ) );
                LegacySongMetaData legacyTrack = ConvertFromLegacy( midiPath.FullPath, newTrack );
                if( CustomTrackDefineTest::GetInstance().ParseMidi( midiPath, newTrack, legacyTrack ) )
                {
                    m_trackList.m_tracks.push_back( newTrack );
                    m_trackList.m_tracks.back().Save();
                }
                //LegacySongMetaData metadata = CustomTrackDefineTest::GetInstance().readSongMetaData( midiPath.FullPath + "/song.ini" );
                //
                //json iniMetaData;
                //iniMetaData["TrackName"] = metadata.m_name;
                //
                //File iniOutput( Path( midiPath.FullPath + "/TrackData.txt" ) );
                //iniOutput.Write( iniMetaData.dump( 1 ) );

                continue;
            }
        }
    }
    catch( fs::filesystem_error& e )
    {
        std::cout << e.what() << std::endl;
    }
}

std::vector<unsigned int>& TrackDatabase::SortTracks( TrackListSort inSortBy, TrackListFilter inFilterBy )
{
    if( inSortBy != m_currentSort || inFilterBy != m_currentFilter )
    {
        m_needsSort = true;
    }
    GatherFilterCounts();
    if( !m_needsSort && !m_pendingInitialSort )
    {
        return m_sortedIndices;
    }

    auto& trackList = m_trackList.m_tracks;
    auto& sortedTracks = m_sortedIndices;
    sortedTracks.clear();
    sortedTracks.reserve( trackList.size() );
    for( int i = 0; i < trackList.size(); ++i )
    {
        bool passesFilter = false;
        BRUH( trackList[i].m_dlcSource );
        switch( inFilterBy )
        {
        case TrackListFilter::Drumsmith:
            passesFilter = trackList[i].m_dlcSource == "DS";
            break;
        case TrackListFilter::RockBand:
            passesFilter = trackList[i].m_dlcSource == "rb1";
            break;
        case TrackListFilter::RockBand2:
            passesFilter = trackList[i].m_dlcSource == "rb2";
            break;
        case TrackListFilter::RockBand3:
            passesFilter = trackList[i].m_dlcSource == "rb3";
            break;
        case TrackListFilter::RockBand4:
            passesFilter = trackList[i].m_dlcSource == "rb4";
            break;
        case TrackListFilter::RockBandBlitz:
            passesFilter = trackList[i].m_dlcSource == "rbb";
            break;
        case TrackListFilter::LegoRockBand:
            passesFilter = trackList[i].m_dlcSource == "lrb";
            break;
        case TrackListFilter::GreenDayRockBand:
            passesFilter = trackList[i].m_dlcSource == "gdrb";
            break;
        case TrackListFilter::GuitarHero5:
            passesFilter = trackList[i].m_dlcSource == "gh5";
            break;
        case TrackListFilter::GuitarHero5DLC:
            passesFilter = trackList[i].m_dlcSource == "gh5dlc";
            break;
        case TrackListFilter::GuitarHeroWorldTour:
            passesFilter = trackList[i].m_dlcSource == "ghwt";
            break;
        case TrackListFilter::GuitarHeroWorldTourDLC:
            passesFilter = trackList[i].m_dlcSource == "ghwtdlc";
            break;
        case TrackListFilter::None:
        default:
            passesFilter = true;
            break;
        }

        if( passesFilter )
        {
            sortedTracks.push_back( i );
        }
    }
    m_currentSort = inSortBy;
    m_currentFilter = inFilterBy;
    m_sortedSize = sortedTracks.size();

    switch( inSortBy )
    {
    case TrackListSort::Title:
        std::sort( sortedTracks.begin(), sortedTracks.end(), [trackList]( unsigned int& first, unsigned int& second )
            {
                return trackList[first].m_trackName < trackList[second].m_trackName;
            } );
        break;
    case TrackListSort::Artist:
        std::sort( sortedTracks.begin(), sortedTracks.end(), [trackList]( unsigned int& first, unsigned int& second )
            {
                return trackList[first].m_artistName < trackList[second].m_artistName;
            } );
        break;
    case TrackListSort::Year:
        std::sort( sortedTracks.begin(), sortedTracks.end(), [trackList]( unsigned int& first, unsigned int& second )
            {
                return trackList[first].m_year < trackList[second].m_year;
            } );
        break;
    default:
    case TrackListSort::None:
        break;
    }

    m_pendingInitialSort = false;
    m_needsSort = false;

    return m_sortedIndices;
}

std::vector<unsigned int>& TrackDatabase::FilterTracks( TrackListFilter inFilterBy )
{
    return m_sortedIndices;
}

void TrackDatabase::GatherFilterCounts()
{
    auto& trackList = m_trackList.m_tracks;
    m_filterMatches.clear();
    m_filterMatches.resize( (int)TrackListFilter::Count );
    for( int i = 0; i < trackList.size(); ++i )
    {
        if( trackList[i].m_dlcSource == "DS" )
        {
            m_filterMatches[(int)TrackListFilter::Drumsmith]++;
        }
        else if( trackList[i].m_dlcSource == "rb1" )
        {
            m_filterMatches[(int)TrackListFilter::RockBand]++;
        }
        else if( trackList[i].m_dlcSource == "rb2" )
        {
            m_filterMatches[(int)TrackListFilter::RockBand2]++;
        }
        else if( trackList[i].m_dlcSource == "rb3" )
        {
            m_filterMatches[(int)TrackListFilter::RockBand3]++;
        }
        else if( trackList[i].m_dlcSource == "rb3dlc" ) // This is messy, just make it a part of regular RB?
        {
            m_filterMatches[(int)TrackListFilter::RockBand3]++;
        }
        else if( trackList[i].m_dlcSource == "rb4" )
        {
            m_filterMatches[(int)TrackListFilter::RockBand4]++;
        }
        else if( trackList[i].m_dlcSource == "lrb" )
        {
            m_filterMatches[(int)TrackListFilter::LegoRockBand]++;
        }
        else if( trackList[i].m_dlcSource == "gdrb" )
        {
            m_filterMatches[(int)TrackListFilter::GreenDayRockBand]++;
        }
        else if( trackList[i].m_dlcSource == "rbb" )
        {
            m_filterMatches[(int)TrackListFilter::RockBandBlitz]++;
        }
        else if( trackList[i].m_dlcSource == "gh" )
        {
            m_filterMatches[(int)TrackListFilter::GuitarHero]++;
        }
        else if( trackList[i].m_dlcSource == "ghwt" )
        {
            m_filterMatches[(int)TrackListFilter::GuitarHeroWorldTour]++;
        }
        else if( trackList[i].m_dlcSource == "ghwtdlc" )
        {
            m_filterMatches[(int)TrackListFilter::GuitarHeroWorldTourDLC]++;
        }
        else if( trackList[i].m_dlcSource == "gh5" )
        {
            m_filterMatches[(int)TrackListFilter::GuitarHero5]++;
        }
        else if( trackList[i].m_dlcSource == "gh5dlc" )
        {
            m_filterMatches[(int)TrackListFilter::GuitarHero5DLC]++;
        }
        else
        {
            YIKES_FMT( "Unhandled %s", trackList[i].m_dlcSource.c_str() );
        }
    }
}

std::string TrackDatabase::GetFilterName( TrackListFilter inFilter )
{
    switch( inFilter )
    {
    case TrackListFilter::Drumsmith:
        return "Drumsmith";
    case TrackListFilter::RockBand:
        return "Rock Band";
    case TrackListFilter::RockBand2:
        return "Rock Band 2";
    case TrackListFilter::RockBand3:
        return "Rock Band 3";
    case TrackListFilter::RockBand4:
        return "Rock Band 4";
    case TrackListFilter::RockBandBlitz:
        return "Rock Band: Blitz";
    case TrackListFilter::GuitarHero:
        return "Guitar Hero";
    case TrackListFilter::GuitarHero2:
        return "Guitar Hero 2";
    case TrackListFilter::GuitarHero3:
        return "Guitar Hero 3";
    case TrackListFilter::GuitarHero4:
        return "Guitar Hero 4";
    case TrackListFilter::GuitarHero5:
        return "Guitar Hero 5";
    case TrackListFilter::GuitarHero5DLC:
        return "Guitar Hero 5 DLC";
    case TrackListFilter::GreenDayRockBand:
        return "Rock Band: Green Day";
    case TrackListFilter::GuitarHeroWorldTour:
        return "Guitar Hero: World Tour";
    case TrackListFilter::GuitarHeroWorldTourDLC:
        return "Guitar Hero: World Tour DLC";
    case TrackListFilter::LegoRockBand:
        return "Lego: Rock Band";
    case TrackListFilter::Other:
        return "Other";
    case TrackListFilter::None:
    case TrackListFilter::Count:
    default:
        return "None";
        break;
    }
    return "Other";
}

TrackData::TrackData( const Path& inPath )
{
    if( inPath.IsFile || !inPath.Exists )
    {
        m_directory = inPath.GetDirectoryString();
    }
    else
    {
        m_directory = inPath.FullPath;
    }
}

void TrackData::Save()
{
    {
        json metaData;
        OnSaveTrackData( metaData );
        File metaFile( Path( m_directory + "/TrackData.txt" ) );
        metaFile.Write( metaData.dump( 1 ) );
    }

    if( !m_noteData.empty() )
    {
        json metaData;
        OnSaveNoteData( metaData );
        File metaFile( Path( m_directory + "/NoteData.txt" ) );
        metaFile.Write( metaData.dump( 1 ) );
    }
}

void TrackData::Load()
{
    {
        Path trackDataFile( m_directory + "/TrackData.txt" );
        if( trackDataFile.Exists )
        {
            File metaFile( trackDataFile );
            json metaData = json::parse( metaFile.Read() );
            OnLoadTrackData( metaData );
        }
    }
    if( m_albumArtFilename.empty() )
    {
        Path possibleAlbumArt = Path( m_directory + "album.png" );
        if( possibleAlbumArt.Exists )
        {
            m_albumArtFilename = possibleAlbumArt.GetFileNameString();
            m_albumArtPath = m_directory + m_albumArtFilename;
        }
        else
        {
            possibleAlbumArt = Path( m_directory + "album.jpg" );
            if( possibleAlbumArt.Exists )
            {
                m_albumArtFilename = possibleAlbumArt.GetFileNameString();
                m_albumArtPath = m_directory + m_albumArtFilename;
            }
        }
    }
    //{
    //    File metaFile( Path( m_directory + "/NoteData.txt" ) );
    //    json metaData = json::parse( metaFile.Read() );
    //    OnLoadConfig( metaData );
    //}
}

void TrackData::OnSaveTrackData( json& outJson )
{
    outJson["Title"] = m_trackName;
    outJson["Artist"] = m_artistName;
    outJson["Album"] = m_albumName;
    outJson["Genre"] = m_genre;
    outJson["Year"] = m_year;
    outJson["Icon"] = m_icon;
    outJson["AlbumArtFileName"] = Path( m_albumArtPath ).GetFileNameString();
    outJson["DLCSource"] = m_dlcSource;
    //m_albumArtPath = m_configFile.FilePath.GetDirectoryString() + "/Album.png";
    //m_trackSourcePath = m_configFile.FilePath.GetDirectoryString() + "/Track.mp3";
    outJson["NoteSpeed"] = m_noteSpeed;
    outJson["Duration"] = m_duration;
    outJson["BPM"] = m_bpm;
    outJson["TrackFileName"] = m_trackFileName;
    outJson["PreviewPercent"] = m_previewPercent;
    outJson["NoteCount"] = m_noteCount;
}

void TrackData::OnSaveNoteData( json& outJson )
{
    std::sort( m_noteData.begin(), m_noteData.end(), []( NoteData& first, NoteData& second )
        {
            if( first.m_triggerTimeMS != second.m_triggerTimeMS )
            {
                return first.m_triggerTimeMS < second.m_triggerTimeMS;
            }
            return first.m_editorLane < second.m_editorLane;
        } );
    //m_noteData.erase( std::unique( m_noteData.begin(), m_noteData.end() ), m_noteData.end() );
    m_noteData.erase( std::unique( m_noteData.begin(), m_noteData.end(),
        []( const NoteData& first, const NoteData& second )
        {
            return first.m_triggerTimeMS == second.m_triggerTimeMS &&
                first.m_editorLane == second.m_editorLane;
        } ),
        m_noteData.end() );
    json& noteData = outJson["Notes"];
    for( NoteData& note : m_noteData )
    {
        json noteEntry;
        noteEntry["EditorLane"] = note.m_editorLane;
        noteEntry["NoteName"] = note.m_noteName;
        noteEntry["TriggerTime"] = note.m_triggerTime;
        noteEntry["TriggerTimeMS"] = (uint32_t)( note.m_triggerTime * 1000.f );

        noteData.push_back( noteEntry );
    }
}

void TrackData::OnLoadTrackData( const json& inJson )
{
    if( inJson.contains( "SongName" ) )
    {
        m_trackName = StringUtils::TrimLeadingSpaces( inJson["SongName"] );
    }
    if( inJson.contains( "Title" ) )
    {
        m_trackName = StringUtils::TrimLeadingSpaces( inJson["Title"] );
    }
    if( inJson.contains( "SongArtist" ) )
    {
        m_artistName = StringUtils::TrimLeadingSpaces( inJson["SongArtist"] );
    }
    if( inJson.contains( "Artist" ) )
    {
        m_artistName = StringUtils::TrimLeadingSpaces( inJson["Artist"] );
    }
    if( inJson.contains( "AlbumName" ) )
    {
        m_albumName = StringUtils::TrimLeadingSpaces( inJson["AlbumName"] );
    }

    if( inJson.contains( "Album" ) )
    {
        m_albumName = StringUtils::TrimLeadingSpaces( inJson["Album"] );
    }
    if( inJson.contains( "Genre" ) )
    {
        m_genre = StringUtils::TrimLeadingSpaces( inJson["Genre"] );
    }
    if( inJson.contains( "Year" ) )
    {
        m_year = inJson["Year"];
    }
    if( inJson.contains( "Icon" ) )
    {
        m_icon = StringUtils::TrimLeadingSpaces( inJson["Icon"] );
        m_dlcSource = m_icon;
    }
    if( inJson.contains( "NoteCount" ) )
    {
        m_noteCount = inJson["NoteCount"];
    }
    if( inJson.contains( "DLCSource" ) )
    {
        m_dlcSource = inJson["DLCSource"];
    }
    if( inJson.contains( "AlbumArtFileName" ) )
    {
        m_albumArtFilename = inJson["AlbumArtFileName"];
    }
    m_albumArtPath = m_directory + m_albumArtFilename;
    if( inJson.contains( "TrackFileName" ) )
    {
        m_trackFileName = inJson["TrackFileName"];
        m_trackSourcePath = m_directory + "/" + std::string( inJson["TrackFileName"] );
    }
    else
    {
        m_trackFileName = "Track.mp3";
        m_trackSourcePath = m_directory + "/" + m_trackFileName;
    }

    if( inJson.contains( "PreviewPercent" ) )
    {
        m_previewPercent = inJson["PreviewPercent"];
    }

    if( inJson.contains( "NoteSpeed" ) )
    {
        m_noteSpeed = inJson["NoteSpeed"];
    }
    if( inJson.contains( "Duration" ) )
    {
        m_duration = inJson["Duration"];
    }
    if( inJson.contains( "BPM" ) )
    {
        m_bpm = inJson["BPM"];
    }
}

void TrackData::OnLoadNoteData( const json& inJson )
{
    if( inJson.contains( "Notes" ) )
    {
        const json& noteData = inJson["Notes"];
        m_noteData.clear();
        m_noteData.reserve( noteData.size() );
        for( const json& note : noteData )
        {
            NoteData noteEntry;
            noteEntry.m_editorLane = PadUtils::GetNewPadId( note["NoteName"] );
            noteEntry.m_noteName = PadUtils::GetPadId( noteEntry.m_editorLane );
            noteEntry.m_triggerTime = note["TriggerTime"];
            if( note.contains( "TriggerTimeMS" ) )
                noteEntry.m_triggerTimeMS = note["TriggerTimeMS"];

            m_noteData.push_back( noteEntry );
        }
    }
}

void TrackData::LoadNoteData()
{
    // #TODO: Temp, might be a custom format charted file
    Path noteDataFile( m_directory + "/NoteData.txt" );
    if( !noteDataFile.Exists )
    {
        return;
    }

    File metaFile( noteDataFile );
    json Root = json::parse( metaFile.Read() );

    ME_ASSERT_MSG( !Root.empty(), "Trying to read an empty track file." );

    OnLoadNoteData( Root );
}
