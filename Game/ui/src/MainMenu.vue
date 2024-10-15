<template>
    <div id="main-menu" class="main-menu">
    <img src="img/2x/Asset 2@2x.png" />
    <br />
    <img
      src="img/Underline.png"
      class="underline-bar"
    /><br />
    <div class="menu-items">
      <MenuItem 
        text="PLAY" 
        :onClick="() => loadScene('Assets/TrackList.lvl')" 
      />
      <br />
      <MenuItem 
        text="PRACTICE" 
        colorClass="green" 
        :onClick="practice" 
      />
      <br />
      <MenuItem 
        text="DLC" 
        colorClass="pink" 
        :onClick="() => LoadDLCScene('Assets/DLC.lvl')" 
      />
      <br />
      <MenuItem 
        text="SETTINGS" 
        colorClass="orange" 
        :onClick="toggleMenu" 
      />
      <br />
      <MenuItem 
        text="EXIT" 
        colorClass="red" 
        :onClick="quit" 
      />
    </div>
</div>
    <div id="settingsMenu" class="options-menu menu">
      <MenuItem 
        text="Back" 
        :onClick="closeSettings" 
      />
      <br />
      <br />
      <p class="menu-text">Enable Radio</p>
      <input type="checkbox" name="EnableRadio" id="radio-enabled" />
      <br />
      <p class="menu-text" id="menu-volume-text">Radio Volume</p>
      <br />
      <input
        type="range"
        name="RadioVolume"
        id="radio-volume"
        min="0"
        max="100"
        step="1"
        value="50"
        class="slider"
      />
      <p class="menu-text" id="menu-volume-text">DLC Server</p>
      <br />
      <input type="text" v-model="inputText" @keydown.enter="SetDLCURL">
      <br />
      <p class="hover-underline-animation pink" onclick="ConvertCustomDLC()">
        Convert Custom DLC
      </p>
      
      <MenuItem 
        text="Save Settings" 
        colorClass="greed" 
        :onClick="saveSettings" 
      />
    </div>

    <div id="track-radio-hover" onmouseover="ShowTrackRadio()"></div>
    <div id="track-radio" onmouseover="ShowTrackRadio()">
      <div class="track-art">
        <img id="track-art" />
        <!-- src="file:///Assets/DLC/LearnToFly/Album.png" -->
      </div>
      <div class="track-details">
        <!--div class="wrapper">
          <div id="scrollingText1" class="scroll-text">
            This is a very long text that needs to scroll to be fully visible.
            Let's scroll!
          </div>
        </div>
        <div class="wrapper">
          a
          <div id="scrollingText2" class="scroll-text">
            Another long text for a different element. It will also scroll!
          </div>
        </div-->

        <div id="track-title" class="scroll-container">
          <div id="track-title-scroll" class="scroll-content BoldRegular Large">
            EXAMPLE TITLE
          </div>
        </div>
        <div class="clearfix"></div>
        <div id="track-artist" class="Regular Small">EXAMPLE ARTIST</div>
        <div class="clearfix"></div>
        <div class="skip-track" onclick="SkipTrack()">
          <a href="#">Skip</a>
        </div>
      </div>
    </div>
  </template>
  <script>
  import MenuItem from './components/MainMenuOption.vue';
  
  export default {
    components: {
      MenuItem
    },
    computed: {
      inputText: {
        get() {
          if (typeof GetDLCURL_Internal === 'function') {
            // eslint-disable-next-line
            return GetDLCURL_Internal(); // Call the WebAssembly function
          }
          return "dlc.example.com";
        },
        set(value) {
          if (typeof SetDLCURL_Internal === 'function') {
            // eslint-disable-next-line
            SetDLCURL_Internal(value); // Pass the value to the WebAssembly function
          }
        }
      }
    },
    methods: {
      loadScene(scene) {
        if (typeof LoadScene === 'function') {
            // eslint-disable-next-line
            LoadScene(scene);
        }
        window.location.href="/SongList.html";
      },
      LoadDLCScene(scene) {
        if (typeof LoadScene === 'function') {
            // eslint-disable-next-line
            LoadScene(scene);
        }
        window.location.href="/DLC.html";
      },
      SetDLCURL() {
        if (typeof SetDLCURL_Internal === 'function') {
            // eslint-disable-next-line
            SetDLCURL_Internal(this.inputText);
        }
      },
      practice() {
        console.log('Starting practice mode');
        // Add logic for practice mode
      },
      toggleMenu() {
        const menu = document.getElementById("settingsMenu");
        const content = document.getElementById("main-menu");

        if (menu.classList.contains("active")) {
          menu.classList.remove("active");
          content.classList.remove("content-fade");
        } else {
          menu.classList.add("active");
          content.classList.add("content-fade");
        }
      },
      saveSettings() {
        if (typeof SaveSettings === 'function') {
            // eslint-disable-next-line
            SaveSettings();
        }
      },
      closeSettings() {
        // eslint-disable-next-line
        this.toggleMenu();
        this.saveSettings();
      },
      quit() {
        if (typeof Quit === 'function') {
            // eslint-disable-next-line
            Quit();
        }
      }
    }
  };
  </script>
  
  <style scoped>
.menu-text {
    display: inline-block;
    position: relative;
    color: white;
    font-size: 48px;
    font-weight: bolder;
    margin-top: 25px;
    margin-bottom: 0;
    /*background-image: url('file:///Assets/Textures/Bar3.png');*/
}

.background {
    width: 100%;
    height: 100%;
    position: fixed;
    min-height: 100%;
    background-color: rgba(0, 0, 0, 0.52);
    top: 0;
    z-index: -1;
}

.underline-bar{
    margin-bottom: 25px;
}

.main-menu {
    margin-left: 50px;
    margin-top: 50px;
}

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
  