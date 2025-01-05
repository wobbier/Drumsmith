<template>
    <div id="track-radio-hover" :onmouseover=ShowTrackRadio></div>
    <div id="track-radio" :class="{ visible: isVisible }" :onmouseover=ShowTrackRadio>
      <div class="track-art">
        <img id="track-art" />
        <!-- src="file:///Assets/DLC/LearnToFly/Album.png" -->
      </div>
      <div class="track-details">
        <ScrollingText baseId="track-title" textStyle="BoldRegular Large" :text="trackTitle" />
        <div class="clearfix"></div>
        <ScrollingText baseId="track-artist" textStyle="Regular Small" :text="trackArtist" />
        <div class="clearfix"></div>
        <div class="skip-track" onclick="SkipTrack()">
          <a href="#">Skip</a>
        </div>
      </div>
    </div>
</template>

<script>
import ScrollingText from './ScrollingText.vue';

export default {
  components: {
    ScrollingText
  },
  data() {
    return {
      titleTrackScrolling: null,
      trackTitle: "EXAMPLE TITLE",
      trackArtist: "EXAMPLE ARTIST",
      isVisible: false,
      timer: null
    };
  },
  mounted() {
    window.DisplayTrack = this.DisplayTrack;
  },
  beforeUnmount() {
    clearTimeout(this.timer);
  },
  methods: {
    ShowTrackRadio() {
      clearTimeout(this.timer);

      if (!this.isVisible) {
        this.isVisible = true;
      }

      this.timer = setTimeout(() => {
        if (this.isVisible) {
          this.isVisible = false;
        }
      }, 15000);
    },
    DisplayTrack(track) {
      var imageContainer = document.getElementById("track-art");
      imageContainer.src = `file:///${track.AlbumArt}`;

      this.trackTitle = `${track.TrackName}`;
      this.trackArtist = `${track.ArtistName}`;

      this.ShowTrackRadio();
    }
  },
};
</script>

<style scoped>

#track-radio{
    width: 600px;
    height: 200px;
    position: fixed;
    bottom: 0;
    right: 0;
    background: rgba(36, 36, 36, 0);
}

.track-art{
    display: flex;
}
.track-details{
    margin-left: 15px;
    margin: 15px;
    position: relative;
    width: inherit;
}
#track-radio img {
    width: 200px;
    height: 200px;
}

#track-radio div {
}
#track-title {
    margin-bottom: 10px;
}
#track-artist {
}

.clearfix::after {
    content: "";
    clear: both;
    display: table;
}

#track-radio .skip-track {
    position: absolute;
    right: 0;
    bottom: 0;
    padding:15px;
    background-color: rgba(255, 255, 255, 0.164);
}

#track-radio .skip-track:hover {
    text-decoration: underline;
    color: white;
    cursor: pointer;
}
#track-radio .skip-track a {
    margin: 10px;
    color: rgba(255, 255, 255, 0.842);
    text-decoration: none;
}

#track-radio a {
    margin: 10px;
    color: rgba(255, 255, 255, 0.842);
    text-decoration: none;
}
#track-radio-hover {
    width: 300px;
    height: 200px;
    /*background-color: #f1f1f1;*/
    position: fixed;
    bottom: 10px;
    right: 0; /* Initially off-screen */
    z-index: 0;
}

#track-radio {
    /*width: 300px;
    height: 100px;
    background-color: #f1f1f1;*/
    position: fixed;
    bottom: 10px;
    right: -390px; /* Initially off-screen */
    z-index: 0;
    transition: right 0.5s;
    display: flex;
}

#track-radio.visible {
    right: 10px; /* Slide in to full view */
    background: rgba(36, 36, 36, 0.376);
}
  </style>
  