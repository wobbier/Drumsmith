<template>
  <div id="header" class="header">
    <!--a href="#" onclick="fillDivs()">Fill Divs</a-->
    <button class="filter-button" onclick="LoadScene('Assets/MainMenu.lvl')">
      <img src="img/Esc_Key_Light.png" alt="Icon" />
      <span>Main Menu</span>
    </button>
    <button class="filter-button" onclick="ToggleTrackListVisibility()">
      <span>View Track List</span>
    </button>
  </div>

  <div id="sidebar" class="sidebar">
    <div id="trackPanel" class="content">
      <div id="trackDetails">
        <DetailsPanel :track="this.focusedTrack" v-if="this.focusedTrack != null" />
      </div>
    </div>
  </div>
  <div id="myDivContainer" class="main-content">
    <div v-for="(group, index) in sortedSections" :key="index" class="section">
      <div class="dynamic-div BoldRegular Large">{{ group.header }}</div>
      <div class="clearfix"></div>

      <div v-for="(track, itemIndex) in group.items" :key="itemIndex" class="dynamic-div"
        @click="playSound(track.TrackSource)">

        <div class="dynamic-div" @click="SelectTrackToPlay(track.Title, itemIndex); ToggleTrackListVisibility();"
          @mouseenter="DelayedTrackPreview(track)">
          <img v-if="!track?.FolderPath" class="album-art" src="file:///{{track.AlbumArt}}" />
          <img v-if="track?.FolderPath" class="album-art" :src="`http://${this.TryGetDLCURL()}/${track.FolderPath
            }/${track.AlbumArtFileName}`" />
        </div>
        <div class="album-title">
          <h1 class="BoldRegular Large">{{ track.Title }}</h1>
          <h2 class="Regular Small">{{ track.Artist }}</h2>
          <h3>{{ track.Year }}</h3>
        </div>
        <div class="note-count">Note Count: {{ track.NoteCount }}</div>
        <div v-if="TryAreToolsEnabled()" onclick="EditTrack('${track.TrackName}')">DEV TOOLS
          ENABLED</div>
        <div v-if="track?.FolderPath ?? false" onclick="DownloadDLC('${track.FolderPath}')">DOWNLOAD TRACK</div>
        <div class="clearfix"></div>
      </div>

    </div>
  </div>
  <div id="filterMenu" class="flyout right">
    <p class="hover-underline-animation" onclick="closeFlyout('filterMenu');">
      &lt; Back </p>
    <br />
    <h1>Sort</h1>
    <br />
    <p class="menu-text flyout-select" onclick="FilterSortTracks(0); closeFlyout('filterMenu');">
      Default
    </p>
    <p class="menu-text flyout-select" onclick="FilterSortTracks(1); closeFlyout('filterMenu');">
      Title
    </p>
    <p class="menu-text flyout-select" onclick="FilterSortTracks(2); closeFlyout('filterMenu');">
      Artist
    </p>
    <p class="menu-text flyout-select" onclick="FilterSortTracks(3); closeFlyout('filterMenu');">
      Year
    </p>
    <br />
    <h1>Filter</h1>
    <br />
    <div id="TrackFilters">
      <p class="menu-text flyout-select" onclick="FilterTracks(0); closeFlyout('filterMenu');">
        None
      </p>
      <br />
    </div>
  </div>

  <div class="footer">
    <button class="openButton filter-button" onclick="openFlyout('filterMenu')">
      <img class="openButton" src="img/Tab_Key_Light.png" alt="Icon" />
      <span class="openButton">Sorting (Ascending)</span>
    </button>
  </div>
</template>

<script>
import DetailsPanel from './components/TrackList/DetailsPanel.vue';

var timer;

export default {
  name: 'DLC',
  components: {
    DetailsPanel
  },
  data() {
    return {
      tracks: [],
      sortBy: 'Title', // Current sorting criterion: 'name', 'artist', or 'year'
      dlcIndex: [], // Store the JSON data
      focusedTrack: null
    };
  },
  mounted() {
    // Fetch the JSON file when the component is mounted
    this.fetchDlcIndex();
    window.UpdateDetailsPanel = this.UpdateDetailsPanel;

    //this.AddTrack({
    //  AlbumArt: "../DLC/30 Seconds to Mars - The Kill/album.png",
    //  Album: "",
    //  Artist: " 30 Seconds to Mars",
    //  Genre: " Modern Rock",
    //  Icon: " ghwt",
    //  NoteCount: 0,
    //  TrackIndex: 0,
    //  Title: " The Kill",
    //  TrackSource:
    //    "M:/Projects/ME/Drumsmith/Assets/DLC/30 Seconds to Mars - The Kill//song.ogg",
    //  Year: 2006,
    //});
    //document.addEventListener("keydown", function (event) {
    //  if (event.key === "Tab" || event.keyCode === 9) {
    //    this.openFlyout("filterMenu");
    //  }
    //});
  },
  computed: {
    sortedSections() {
      // Group and sort tracks by the chosen criterion
      const grouped = this.tracks.reduce((acc, track) => {
        // Log each track to ensure it's valid
        let groupKey;
        if (this.sortBy === "Artist") {
          const artistName = track.Artist ? track.Artist.trim() : "Unknown";
          groupKey = artistName[0]?.toUpperCase() || "Unknown";
        } else if (this.sortBy === "Title") {
          const title = track.Title ? track.Title.trim() : "Unknown";
          groupKey = title[0]?.toUpperCase() || "Unknown";
        } else {
          groupKey = track[this.sortBy] || "Unknown";
        }

        if (!acc[groupKey]) {
          acc[groupKey] = [];
        }

        acc[groupKey].push(track);

        return acc;
      }, {});

      // Convert grouped data into an array of { header, items } objects
      return Object.keys(grouped)
        .sort()
        .map((key) => ({
          header: key,
          items: grouped[key].sort((a, b) => {
            if (this.sortBy === "Artist") {
              return a.Artist.localeCompare(b.Artist);
            }
            return a[this.sortBy]?.toString().localeCompare(b[this.sortBy]?.toString() || "");
          }),
        }));
    },
  },
  methods: {
    async fetchDlcIndex() {
      try {
        const response = await fetch('https://' + this.TryGetDLCURL() + '/dlc_index.json'); // Adjust the path
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        this.dlcIndex = await response.json();
        this.dlcIndex.forEach((item) => {
          //console.log(JSON.stringify(item));
          if (!item.AlbumArtFileName) {
            item.AlbumArtFileName = "Album.png";
          }
          this.AddTrack(item);
        });
      } catch (error) {
        console.error('Error fetching DLC index:', error);
      }
    },
    TryGetDLCURL() {
      if (typeof GetDLCURL === "function") {
        // eslint-disable-next-line
        return GetDLCURL();
      }
      return "test.domain.com";
    },
    RequestDetailsPanelUpdate2(trackIndex) {
      if (typeof RequestDetailsPanelUpdate === "function") {
        // eslint-disable-next-line
        return RequestDetailsPanelUpdate(trackIndex);
      }
    },
    SelectTrackToPlay(title, index) {
      console.log(`SelectTrackToPlay called with Title: ${title}, Index: ${index}`);
      // Add your existing logic here
    },
    // eslint-disable-next-line
    DelayedTrackPreview(track) {
      clearTimeout(timer);
      this.focusedTrack = track;
      this.focusedTrack.DLCURL = this.TryGetDLCURL();
      console.log(track);
      // this timer is messing with the document too much
      //this.RequestDetailsPanelUpdate2(trackIndex);
      //timer = setTimeout(function () {
      //
      //  if (typeof PlayTrackPreview === "function") {
      //    // eslint-disable-next-line
      //    //PlayTrackPreview(trackIndex);
      //  }
      //}, 250);
    },

    ClearTrackList() {
      // Fetch the container div
      const containerDiv = document.getElementById("myDivContainer");

      // Clear previous divs
      const oldDivs = containerDiv.querySelectorAll(".dynamic-div");
      oldDivs.forEach((div) => div.remove());
    },

    ToggleTrackListVisibility() {
      var x = document.getElementById("sidebar");
      var bg = document.getElementById("background");
      var containerDiv = document.getElementById("main-body");
      if (x.style.display === "none") {
        //  || x.style.display === ""
        x.style.display = "flex";
      } else {
        x.style.display = "none";
      }

      if (bg.style.display === "none") {
        //  || x.style.display === ""
        bg.style.display = "block";
      } else {
        bg.style.display = "none";
      }

      if (containerDiv.style.display === "none") {
        //  || x.style.display === ""
        containerDiv.style.display = "block";
      } else {
        containerDiv.style.display = "none";
      }
    },

    TryAreToolsEnabled() {
      if (typeof AreToolsEnabled === "function") {
        // eslint-disable-next-line
        return AreToolsEnabled();
      }
      return false;
    },

    AddTrack(track) {
      this.tracks.push(track);
    },

    // eslint-disable-next-line
    UpdateDetailsPanel(track) {
    },

    fillDivs() {
      // Fetch the container div
      //const containerDiv = document.getElementById("myDivContainer");
      //ClearTrackList();
      // Sample data to populate the divs
      const items = [
        {
          TrackName: "Data 1",
          ArtistName: "Data 1",
          AlbumArt: "../DLC/ExampleSong/this_suffering_cover.jpg",
        },
        {
          TrackName: "Data 2",
          ArtistName: "Data 2",
          AlbumArt:
            "file:///M:/Projects/ME/Drumsmith/Assets/DLC/ExampleSong2/album.jpg",
        },
        { TrackName: "Data 3", ArtistName: "Data 3", AlbumArt: "image3.jpg" },
        { TrackName: "Data 4", ArtistName: "Data 4", AlbumArt: "image4.jpg" },
      ];

      // Loop through each item and create a div for it
      items.forEach((item) => {
        this.AddTrack(item);
        //const dynamicDiv = document.createElement('div');
        //dynamicDiv.classList.add('dynamic-div');
        //// Create and append text content
        //const textNode = document.createTextNode(item.text);
        //dynamicDiv.appendChild(textNode);
        //
        //// Create and append image
        //const image = document.createElement('img');
        //image.src = item.imgSrc;
        //image.alt = item.text;
        //dynamicDiv.appendChild(image);
        //
        //containerDiv.appendChild(dynamicDiv);
      });
    },
    SetFilters(inFilters) {
      const filtersDiv = document.getElementById("TrackFilters");
      filtersDiv.innerHTML = "";
      inFilters.forEach((filter) => {
        filtersDiv.innerHTML += `<p
    class="menu-text flyout-select"
    onclick="FilterTracks(${filter.FilterID}); closeFlyout('filterMenu');"
  >
  ${filter.FilterName} (${filter.Count})
  </p>`;
      });
      filtersDiv.innerHTML += `
  <br />
  <br />`;
    }
  }
}
</script>