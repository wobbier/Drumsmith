<template>
  <div id="track-radio-hover" :onmouseover="ShowTrackRadio"></div>
  <div id="track-radio" :class="{ visible: isVisible }" :onmouseover="ShowTrackRadio">
    <div class="track-art">
      <img id="track-art" />
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

    <!-- Custom Audio Progress Bar -->
    <div class="track-progress">
      <!-- Range slider that we bind to currentTime -->
      <input type="range" min="0" :max="duration" step="1" v-model="currentTime" @change="seekAudio" />
      <div class="progress-labels">
        <span>{{ formatTime(currentTime) }}</span>
        <span>/</span>
        <span>{{ formatTime(duration) }}</span>
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
      trackTitle: "EXAMPLE TITLE",
      trackArtist: "EXAMPLE ARTIST",
      isVisible: false,
      timer: null,
      currentTime: 0,
      duration: 0,
      updateIntervalId: null
    };
  },

  mounted() {
    window.DisplayTrack = this.DisplayTrack;

    // eslint-disable-next-line
    if (typeof GetCurrentTrackDuration === 'function') {
      // eslint-disable-next-line
      var ms = GetCurrentTrackDuration();
      this.duration = ms / 1000; // store in seconds
    }

    this.updateIntervalId = setInterval(() => {
      if (this.duration === 0) {
        // eslint-disable-next-line
        if (typeof GetCurrentTrackDuration === 'function') {
          // eslint-disable-next-line
          var ms = GetCurrentTrackDuration();
          this.duration = ms / 1000; // store in seconds
        }
      }
      // eslint-disable-next-line
      if (typeof GetCurrentTrackPosition === 'function') {
        // eslint-disable-next-line
        var ms = GetCurrentTrackPosition();
        this.currentTime = ms / 1000; // store in seconds
      }
    }, 1000);
  },

  beforeUnmount() {
    clearTimeout(this.timer);
    clearInterval(this.updateIntervalId);
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
      // eslint-disable-next-line
      if (typeof GetCurrentTrackDuration === 'function') {
        // eslint-disable-next-line
        var ms = GetCurrentTrackDuration();
        this.duration = ms / 1000; // store in seconds
      }
      // eslint-disable-next-line
      if (typeof GetCurrentTrackPosition === 'function') {
        // eslint-disable-next-line
        var ms = GetCurrentTrackPosition();
        this.currentTime = ms / 1000; // store in seconds
      }

      this.ShowTrackRadio();
    },

    seekAudio() {
      // eslint-disable-next-line
      if (typeof SeekToPosition === 'function') {
        const fraction = this.currentTime / this.duration;
        // eslint-disable-next-line
        SeekToPosition(fraction);
      }
    },
    formatTime(seconds) {
      if (!seconds) return "0:00";
      const m = Math.floor(seconds / 60);
      const s = Math.floor(seconds % 60).toString().padStart(2, '0');
      return `${m}:${s}`;
    }
  }
};
</script>

<style scoped>
.track-progress {
  margin-top: 10px;
}

.track-progress input[type="range"] {
  width: 100%;
}

.progress-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.9em;
  margin-top: 5px;
}

#track-radio {
  width: 600px;
  height: 200px;
  position: fixed;
  bottom: 0;
  right: 0;
  background: rgba(36, 36, 36, 0);
}

.track-art {
  display: flex;
}

.track-details {
  margin-left: 15px;
  margin: 15px;
  position: relative;
  width: inherit;
}

#track-radio img {
  width: 200px;
  height: 200px;
}

#track-radio div {}

#track-title {
  margin-bottom: 10px;
}

#track-artist {}

.clearfix::after {
  content: "";
  clear: both;
  display: table;
}

#track-radio .skip-track {
  position: absolute;
  right: 0;
  bottom: 0;
  padding: 15px;
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
  right: 0;
  /* Initially off-screen */
  z-index: 0;
}

#track-radio {
  /*width: 300px;
    height: 100px;
    background-color: #f1f1f1;*/
  position: fixed;
  bottom: 10px;
  right: -390px;
  /* Initially off-screen */
  z-index: 0;
  transition: right 0.5s;
  display: flex;
}

#track-radio.visible {
  right: 10px;
  /* Slide in to full view */
  background: rgba(36, 36, 36, 0.376);
}
</style>