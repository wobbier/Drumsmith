#include "Editor/Chart/EventTrack.h"
#include "CoreGame/TrackList.h"
#include "Editor/PadBindings.h"
#include <imgui.h>
#include "misc/cpp/imgui_stdlib.h"
#include <cmath>
#include <cstring>

#if USING( ME_EDITOR )

namespace
{
    float Seconds( double inSeconds )
    {
        return static_cast<float>( std::max( 0.0, inSeconds ) );
    }


    // A field shared by the selected items: shows the first item's value, and a change goes to all.
    template<class T, class TValue>
    bool AllSame( const std::vector<T>& inItems, const std::vector<int>& inSelected, TValue( *inGet )( const T& ) )
    {
        for( int item : inSelected )
        {
            if( !( inGet( inItems[item] ) == inGet( inItems[inSelected.front()] ) ) )
            {
                return false;
            }
        }
        return true;
    }


    // The drum chart: one row per pad.
    class NoteTrack final
        : public VectorTrack<NoteData>
    {
    public:
        explicit NoteTrack( std::vector<NoteData>& inNotes )
            : VectorTrack( inNotes )
        {
            Name = "Notes";
            Group = TrackGroup::Notes;
            Domain = ChartDomain::Notes;
            for( int pad = 0; pad < PadId::COUNT; ++pad )
            {
                RowNames.push_back( PadUtils::GetPadName( static_cast<PadId>( pad ) ) );
            }
        }

        double Start( int inItem ) const override { return ( *Items )[inItem].m_triggerTime; }
        int Row( int inItem ) const override { return static_cast<int>( ( *Items )[inItem].m_editorLane ); }

        void Set( int inItem, double inStart, double inEnd, int inRow ) override
        {
            NoteData& note = ( *Items )[inItem];
            note.m_triggerTime = Seconds( inStart );
            note.m_triggerTimeMS = static_cast<uint32_t>( note.m_triggerTime * 1000.f );
            note.m_editorLane = static_cast<PadId>( std::clamp( inRow, 0, static_cast<int>( PadId::COUNT ) - 1 ) );
            note.m_noteName = PadUtils::GetPadId( note.m_editorLane );
        }

        int Add( double inStart, double inEnd, int inRow ) override
        {
            Items->emplace_back();
            Set( Count() - 1, inStart, inEnd, inRow );
            return Count() - 1;
        }

        std::string Label( int inItem ) const override
        {
            switch( ( *Items )[inItem].m_articulation )
            {
            case Articulation::Rim: return "R";
            case Articulation::CrossStick: return "X";
            case Articulation::Bell: return "B";
            default: return {};
            }
        }

        uint32_t ItemColor( int inItem ) const override
        {
            const NoteData& note = ( *Items )[inItem];
            uint32_t color = static_cast<uint32_t>( PadUtils::GetNoteColorABGR( note.m_editorLane ) );
            // Ghost notes are drawn faint.
            if( note.m_velocity <= 40 )
            {
                color = ( color & 0x00FFFFFF ) | 0x70000000;
            }
            return color;
        }

        void DrawProperties( const std::vector<int>& inItems, const std::function<void()>& inBeforeChange ) override
        {
            const auto setVelocity = [&]( int inVelocity ) {
                inBeforeChange();
                for( int item : inItems ) ( *Items )[item].m_velocity = static_cast<uint8_t>( std::clamp( inVelocity, 1, 127 ) );
            };
            const NoteData& first = ( *Items )[inItems.front()];
            ImGui::TextUnformatted( "Dynamics" );
            if( ImGui::Button( "Ghost" ) ) setVelocity( 30 );
            ImGui::SameLine();
            if( ImGui::Button( "Normal" ) ) setVelocity( 100 );
            ImGui::SameLine();
            if( ImGui::Button( "Accent" ) ) setVelocity( 127 );
            int velocity = first.m_velocity;
            const bool sameVelocity = AllSame<NoteData, int>( *Items, inItems, []( const NoteData& n ) { return static_cast<int>( n.m_velocity ); } );
            if( ImGui::SliderInt( "Velocity", &velocity, 1, 127, sameVelocity ? "%d" : "mixed (%d)" ) )
            {
                setVelocity( velocity );
            }

            ImGui::TextUnformatted( "Stroke" );
            const bool sameStroke = AllSame<NoteData, int>( *Items, inItems, []( const NoteData& n ) { return static_cast<int>( n.m_articulation ); } );
            static const char* const kStrokes[] = { "Normal", "Rim", "Cross-stick", "Bell" };
            for( int stroke = 0; stroke < static_cast<int>( Articulation::Count ); ++stroke )
            {
                if( stroke > 0 ) ImGui::SameLine();
                if( ImGui::RadioButton( kStrokes[stroke], sameStroke && static_cast<int>( first.m_articulation ) == stroke ) )
                {
                    inBeforeChange();
                    for( int item : inItems ) ( *Items )[item].m_articulation = static_cast<Articulation>( stroke );
                }
            }
        }
    };


    // Named moments: lighting cues, sections, camera cuts, band states, lyrics, ...
    class CueTrack final
        : public VectorTrack<TimedCueData>
    {
    public:
        CueTrack( const char* inName, TrackGroup inGroup, ChartDomain inDomain, uint32_t inColor, std::vector<TimedCueData>& inCues, std::vector<const char*> inVocabulary = {} )
            : VectorTrack( inCues )
            , Vocabulary( std::move( inVocabulary ) )
        {
            Name = inName;
            Group = inGroup;
            Domain = inDomain;
            Color = inColor;
        }

        double Start( int inItem ) const override { return ( *Items )[inItem].m_time; }
        void Set( int inItem, double inStart, double inEnd, int inRow ) override { ( *Items )[inItem].m_time = Seconds( inStart ); }

        int Add( double inStart, double inEnd, int inRow ) override
        {
            Items->push_back( TimedCueData{ Seconds( inStart ), Vocabulary.empty() ? std::string( "new" ) : WordOf( Vocabulary.front() ) } );
            return Count() - 1;
        }

        std::string Label( int inItem ) const override
        {
            const std::string& name = ( *Items )[inItem].m_name;
            return name.empty() ? std::string( "(default)" ) : name;
        }

        void DrawProperties( const std::vector<int>& inItems, const std::function<void()>& inBeforeChange ) override
        {
            std::string name = ( *Items )[inItems.front()].m_name;
            const auto setName = [&]( const std::string& inName ) {
                inBeforeChange();
                for( int item : inItems ) ( *Items )[item].m_name = inName;
            };
            if( ImGui::InputText( "Name", &name ) )
            {
                setName( name );
            }
            if( !Vocabulary.empty() && ImGui::BeginCombo( "Known", "choose...", ImGuiComboFlags_HeightLarge ) )
            {
                for( const char* entry : Vocabulary )
                {
                    if( entry[0] == '#' )
                    {
                        ImGui::SeparatorText( entry + 1 );
                        continue;
                    }
                    const std::string word = WordOf( entry );
                    const char* note = std::strchr( entry, '|' );
                    if( ImGui::Selectable( word.empty() ? "(default)" : word.c_str(), name == word ) )
                    {
                        setName( word );
                    }
                    if( note )
                    {
                        ImGui::SameLine();
                        ImGui::TextDisabled( "%s", note + 1 );
                    }
                }
                ImGui::EndCombo();
            }
        }


        // A vocabulary entry is "word", "word|what it is" or "#heading" (the first is never a heading).
        static std::string WordOf( const char* inEntry )
        {
            const char* note = std::strchr( inEntry, '|' );
            return note ? std::string( inEntry, note ) : std::string( inEntry );
        }

        std::vector<const char*> Vocabulary;
    };


    // Bare moments: pyro hits.
    class TimeTrack final
        : public VectorTrack<float>
    {
    public:
        TimeTrack( const char* inName, TrackGroup inGroup, ChartDomain inDomain, uint32_t inColor, std::vector<float>& inTimes )
            : VectorTrack( inTimes )
        {
            Name = inName;
            Group = inGroup;
            Domain = inDomain;
            Color = inColor;
        }

        double Start( int inItem ) const override { return ( *Items )[inItem]; }
        void Set( int inItem, double inStart, double inEnd, int inRow ) override { ( *Items )[inItem] = Seconds( inStart ); }

        int Add( double inStart, double inEnd, int inRow ) override
        {
            Items->push_back( Seconds( inStart ) );
            return Count() - 1;
        }
    };


    // Held spans: star power, fills, solos, phrases; with a row per band member where the span
    // belongs to one (singalongs).
    class SpanTrack final
        : public VectorTrack<VenueData::SpanData>
    {
    public:
        SpanTrack( const char* inName, TrackGroup inGroup, ChartDomain inDomain, uint32_t inColor, std::vector<VenueData::SpanData>& inSpans, bool inMemberRows = false )
            : VectorTrack( inSpans )
            , MemberRows( inMemberRows )
        {
            Name = inName;
            Group = inGroup;
            Domain = inDomain;
            Color = inColor;
            Spans = true;
            if( MemberRows )
            {
                for( int member = 0; member < VenueData::MemberCount; ++member )
                {
                    RowNames.push_back( VenueData::MemberName( member ) );
                }
            }
        }

        double Start( int inItem ) const override { return ( *Items )[inItem].m_start; }
        double End( int inItem ) const override { return ( *Items )[inItem].m_end; }
        int Row( int inItem ) const override { return MemberRows ? ( *Items )[inItem].m_member : 0; }

        void Set( int inItem, double inStart, double inEnd, int inRow ) override
        {
            VenueData::SpanData& span = ( *Items )[inItem];
            span.m_start = Seconds( inStart );
            span.m_end = std::max( span.m_start, Seconds( inEnd ) );
            if( MemberRows )
            {
                span.m_member = std::clamp( inRow, 0, static_cast<int>( VenueData::MemberCount ) - 1 );
            }
        }

        int Add( double inStart, double inEnd, int inRow ) override
        {
            Items->emplace_back();
            Set( Count() - 1, inStart, inEnd, inRow );
            return Count() - 1;
        }

        bool MemberRows = false;
    };


    class KeyframeTrack final
        : public VectorTrack<VenueData::KeyframeData>
    {
    public:
        explicit KeyframeTrack( std::vector<VenueData::KeyframeData>& inKeyframes )
            : VectorTrack( inKeyframes )
        {
            Name = "Light Keyframes";
            Group = TrackGroup::Venue;
            Color = 0xFF6FD0F0;
        }

        double Start( int inItem ) const override { return ( *Items )[inItem].m_time; }
        void Set( int inItem, double inStart, double inEnd, int inRow ) override { ( *Items )[inItem].m_time = Seconds( inStart ); }

        int Add( double inStart, double inEnd, int inRow ) override
        {
            Items->push_back( VenueData::KeyframeData{ Seconds( inStart ), VenueData::Keyframe::Next } );
            return Count() - 1;
        }

        std::string Label( int inItem ) const override
        {
            switch( ( *Items )[inItem].m_step )
            {
            case VenueData::Keyframe::Previous: return "prev";
            case VenueData::Keyframe::First: return "first";
            default: return "next";
            }
        }

        void DrawProperties( const std::vector<int>& inItems, const std::function<void()>& inBeforeChange ) override
        {
            static const char* const kSteps[] = { "Next", "Previous", "First" };
            int step = static_cast<int>( ( *Items )[inItems.front()].m_step );
            if( ImGui::Combo( "Step", &step, kSteps, 3 ) )
            {
                inBeforeChange();
                for( int item : inItems ) ( *Items )[item].m_step = static_cast<VenueData::Keyframe>( step );
            }
        }
    };


    class FogTrack final
        : public VectorTrack<VenueData::FogData>
    {
    public:
        explicit FogTrack( std::vector<VenueData::FogData>& inFog )
            : VectorTrack( inFog )
        {
            Name = "Fog";
            Group = TrackGroup::Venue;
            Color = 0xFFB0B0B0;
        }

        double Start( int inItem ) const override { return ( *Items )[inItem].m_time; }
        void Set( int inItem, double inStart, double inEnd, int inRow ) override { ( *Items )[inItem].m_time = Seconds( inStart ); }

        int Add( double inStart, double inEnd, int inRow ) override
        {
            // Alternates: on after an off (or first), off after an on.
            const bool on = Items->empty() || !Items->back().m_on;
            Items->push_back( VenueData::FogData{ Seconds( inStart ), on } );
            return Count() - 1;
        }

        std::string Label( int inItem ) const override { return ( *Items )[inItem].m_on ? "on" : "off"; }
        uint32_t ItemColor( int inItem ) const override { return ( *Items )[inItem].m_on ? Color : 0xFF606060; }

        void DrawProperties( const std::vector<int>& inItems, const std::function<void()>& inBeforeChange ) override
        {
            bool on = ( *Items )[inItems.front()].m_on;
            if( ImGui::Checkbox( "Fog on", &on ) )
            {
                inBeforeChange();
                for( int item : inItems ) ( *Items )[item].m_on = on;
            }
        }
    };


    // Follow spots, a row per member in VENUE's order (notes 37-41).
    class SpotlightTrack final
        : public VectorTrack<VenueData::SpotlightData>
    {
    public:
        explicit SpotlightTrack( std::vector<VenueData::SpotlightData>& inSpots )
            : VectorTrack( inSpots )
        {
            Name = "Spotlights";
            Group = TrackGroup::Venue;
            Color = 0xFFE8F4FF;
            Spans = true;
            RowNames = { "keys", "vocals", "guitar", "drums", "bass" };
        }

        double Start( int inItem ) const override { return ( *Items )[inItem].m_start; }
        double End( int inItem ) const override { return ( *Items )[inItem].m_end; }
        int Row( int inItem ) const override { return ( *Items )[inItem].m_slot; }

        void Set( int inItem, double inStart, double inEnd, int inRow ) override
        {
            VenueData::SpotlightData& spot = ( *Items )[inItem];
            spot.m_start = Seconds( inStart );
            spot.m_end = std::max( spot.m_start, Seconds( inEnd ) );
            spot.m_slot = std::clamp( inRow, 0, 4 );
        }

        int Add( double inStart, double inEnd, int inRow ) override
        {
            Items->emplace_back();
            Set( Count() - 1, inStart, inEnd, inRow );
            return Count() - 1;
        }
    };


    // The tempo map: a beat per item, measure starts marked.
    class BeatTrack final
        : public VectorTrack<BeatData>
    {
    public:
        explicit BeatTrack( std::vector<BeatData>& inBeats )
            : VectorTrack( inBeats )
        {
            Name = "Beats";
            Group = TrackGroup::Structure;
            Domain = ChartDomain::Beats;
            Color = 0xFF909090;
        }

        double Start( int inItem ) const override { return ( *Items )[inItem].m_time; }
        void Set( int inItem, double inStart, double inEnd, int inRow ) override { ( *Items )[inItem].m_time = Seconds( inStart ); }

        int Add( double inStart, double inEnd, int inRow ) override
        {
            Items->push_back( BeatData{ Seconds( inStart ), false } );
            return Count() - 1;
        }

        std::string Label( int inItem ) const override { return ( *Items )[inItem].m_measure ? "|" : std::string(); }
        uint32_t ItemColor( int inItem ) const override { return ( *Items )[inItem].m_measure ? 0xFFFFFFFF : Color; }

        void DrawProperties( const std::vector<int>& inItems, const std::function<void()>& inBeforeChange ) override
        {
            bool measure = ( *Items )[inItems.front()].m_measure;
            if( ImGui::Checkbox( "Starts a measure", &measure ) )
            {
                inBeforeChange();
                for( int item : inItems ) ( *Items )[item].m_measure = measure;
            }
        }
    };
}


std::vector<std::unique_ptr<IEventTrack>> EventTracks::Build( TrackData& inChart )
{
    std::vector<std::unique_ptr<IEventTrack>> tracks;
    VenueData& venue = inChart.m_venue;
    const auto cues = [&tracks]( const char* inName, TrackGroup inGroup, ChartDomain inDomain, uint32_t inColor, std::vector<TimedCueData>& inCues, std::vector<const char*> inVocabulary = {} ) {
        tracks.push_back( std::make_unique<CueTrack>( inName, inGroup, inDomain, inColor, inCues, std::move( inVocabulary ) ) );
    };
    const auto spans = [&tracks]( const char* inName, TrackGroup inGroup, ChartDomain inDomain, uint32_t inColor, std::vector<VenueData::SpanData>& inSpans, bool inMemberRows = false ) {
        tracks.push_back( std::make_unique<SpanTrack>( inName, inGroup, inDomain, inColor, inSpans, inMemberRows ) );
    };

    tracks.push_back( std::make_unique<NoteTrack>( inChart.m_noteData ) );

    // Gameplay phrases (charted; not scored yet).
    spans( "Star Power", TrackGroup::Gameplay, ChartDomain::Phrases, 0xFFF0D060, inChart.m_starPower );
    spans( "Drum Fills", TrackGroup::Gameplay, ChartDomain::Phrases, 0xFF60D0A0, inChart.m_drumFills );
    spans( "Drum Solos", TrackGroup::Gameplay, ChartDomain::Phrases, 0xFF6090F0, inChart.m_drumSolos );

    cues( "Sections", TrackGroup::Structure, ChartDomain::Venue, 0xFFE0C080, venue.m_sections,
        { "intro", "verse_1", "prechorus_1", "chorus_1", "verse_2", "chorus_2", "bridge", "breakdown", "solo", "chorus_3", "outro" } );
    cues( "Song Events", TrackGroup::Structure, ChartDomain::Venue, 0xFFC0C0E0, venue.m_songEvents, { "music_start", "music_end", "end", "coda" } );
    tracks.push_back( std::make_unique<BeatTrack>( inChart.m_beats ) );

    cues( "Lighting", TrackGroup::Venue, ChartDomain::Venue, 0xFF50C8FF, venue.m_lighting,
        { "", "verse", "chorus", "intro", "manual_cool", "manual_warm", "dischord", "stomp", "loop_cool", "loop_warm", "harmony", "frenzy", "silhouettes",
          "silhouettes_spot", "searchlights", "sweep", "strobe_slow", "strobe_fast", "blackout_slow", "blackout_fast", "blackout_spot", "flare_slow", "flare_fast", "bre" } );
    tracks.push_back( std::make_unique<KeyframeTrack>( venue.m_keyframes ) );
    tracks.push_back( std::make_unique<FogTrack>( venue.m_fog ) );
    tracks.push_back( std::make_unique<TimeTrack>( "Pyro", TrackGroup::Venue, ChartDomain::Venue, 0xFF3070FF, venue.m_bonusFx ) );
    tracks.push_back( std::make_unique<SpotlightTrack>( venue.m_spotlights ) );
    const std::vector<const char*> cameraShots =
        { "auto|the director picks, and keeps cutting if held past 10 s", "auto only_close", "auto only_far", "auto no_close", "auto no_behind", "auto focus_drums", "auto focus_guitar", "auto focus_bass", "auto focus_vocals",
          // The crew's own shots (Director::PlanFor): cam_<kind>[_<member letters>][_<variant>].
          "#The crew",
          "guitar_neck|GoPro on the guitar's headstock", "bass_neck|GoPro on the bass's headstock",
          "cam_drumtop|the kit from overhead", "cam_drumlow|the kit from low, through the cymbals",
          "cam_crane|booms up out of the pit", "cam_dolly|trucks along the pit rail", "cam_drone|over the crowd", "cam_orbit|slow high orbit",
          "cam_foh|long lens from the mixing desk", "cam_foh_d|long lens on the drummer", "cam_foh_g", "cam_foh_b", "cam_foh_v",
          "cam_crowd|from a few rows back", "cam_side|profile from the wings", "cam_push|fast push in", "cam_run|operator running the pit, along the front row",
          "cam_reverse|from behind the band at the crowd", "cam_reverse_d|from behind the throne", "cam_reverse_g|over the guitarist's shoulder", "cam_reverse_b", "cam_reverse_v",
          "cam_hero_g|low angle at the guitarist's feet", "cam_hero_b", "cam_hero_v",
          "#The whole band",
          "directed_all", "directed_all_cam|handheld", "directed_all_lt|from up high", "directed_all_yeah", "directed_bre|big rock ending, high and swinging", "directed_brej",
          "coop_all_near", "coop_all_far", "coop_all_behind", "coop_front_near", "coop_front_behind",
          "#Drummer",
          "directed_drums", "directed_drums_lt|from behind", "directed_drums_kd|the kick drum", "directed_drums_np|locked off on the head", "directed_drums_pnt", "coop_d_near", "coop_d_behind",
          "#Guitarist",
          "directed_guitar", "directed_guitar_cam|handheld", "directed_guitar_cls|the hands", "directed_guitar_np|locked off on the head", "coop_g_near", "coop_g_behind", "coop_g_closeup_hand", "coop_g_closeup_head",
          "#Bassist",
          "directed_bass", "directed_bass_cam", "directed_bass_cls", "directed_bass_np", "coop_b_near", "coop_b_behind",
          "#Vocalist",
          "directed_vocals", "directed_vocals_cam", "directed_vocals_cls", "directed_vocals_np", "coop_v_near", "coop_v_behind", "coop_v_closeup",
          "#Pairs and the crowd",
          "directed_duo_drums", "directed_duo_guitar", "directed_duo_bass", "directed_duo_gb",
          "directed_crowd", "directed_crowd_b", "directed_stagedive", "directed_crowdsurf" };
    const std::vector<const char*> postLooks =
        { "ProFilm_a", "ProFilm_b", "ProFilm_mirror_a", "ProFilm_psychedelic_blue_red", "film_b+w", "film_sepia_ink", "film_silvertone", "film_16mm", "film_contrast",
          "film_contrast_blue", "film_contrast_green", "film_contrast_red", "contrast_a", "photocopy", "photo_negative", "bloom", "bright", "posterize", "clean_trails",
          "video_trails", "flicker_trails", "desat_posterize_trails", "space_woosh", "shitty_tv", "video_a", "video_bw", "video_security", "horror_movie_special", "bleach_bypass" };
    cues( "Camera Cuts", TrackGroup::Venue, ChartDomain::Venue, 0xFFE09050, venue.m_cameras, cameraShots );
    cues( "Post FX", TrackGroup::Venue, ChartDomain::Venue, 0xFFD070D0, venue.m_postFx, postLooks );
    // The music video's own cuts and looks (Venue Camera: Music video); empty, it plays the live show's.
    cues( "MV Camera Cuts", TrackGroup::Venue, ChartDomain::Venue, 0xFFC07840, venue.m_mvCameras, cameraShots );
    cues( "MV Post FX", TrackGroup::Venue, ChartDomain::Venue, 0xFFB058B0, venue.m_mvPostFx, postLooks );
    cues( "Crowd", TrackGroup::Venue, ChartDomain::Venue, 0xFF80E080, venue.m_crowd, { "normal", "mellow", "intense", "realtime", "clap", "noclap" } );

    static const char* const kMemberTracks[VenueData::MemberCount] = { "Drummer", "Guitarist", "Bassist", "Vocalist", "Keyboardist" };
    for( int member = 0; member < VenueData::MemberCount; ++member )
    {
        cues( kMemberTracks[member], TrackGroup::Band, ChartDomain::Venue, 0xFFA0D8E8, venue.m_bandStates[member],
            { "idle", "idle_realtime", "idle_intense", "play", "mellow", "intense", "play_solo" } );
    }
    spans( "Singalong", TrackGroup::Band, ChartDomain::Venue, 0xFFE8B0D0, venue.m_singalong, true );
    spans( "Guitar Solos", TrackGroup::Band, ChartDomain::Venue, 0xFF70A0FF, venue.m_guitarSolos );

    cues( "Lyrics", TrackGroup::Lyrics, ChartDomain::Venue, 0xFFE8E8E8, venue.m_lyrics );
    spans( "Vocal Phrases", TrackGroup::Lyrics, ChartDomain::Venue, 0xFFB0B0F0, venue.m_vocalPhrases );
    return tracks;
}

#endif
