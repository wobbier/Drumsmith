<template>
  <div id="main-menu" class="main-menu" style="height: 1000px;">
    <img src="img/2x/Asset 2@2x.png" />
    <br />
    <img src="img/Underline.png" class="underline-bar" /><br />
    <div class="menu-items">
      <MenuItem text="PLAY" :onClick="() => loadScene('Assets/TrackList.lvl')" />
      <br />
      <MenuItem text="PRACTICE" colorClass="green" :onClick="practice" />
      <br />
      <MenuItem text="DLC" colorClass="pink" :onClick="() => LoadDLCScene('Assets/DLC.lvl')" />
      <br />
      <MenuItem text="SETTINGS" colorClass="orange" :onClick="toggleMenu" />
      <br />
      <MenuItem text="EXIT" colorClass="red" :onClick="quit" />
    </div>
  </div>
  <div id="settingsMenu" class="options-menu menu" style="height: 1000px;">
    <MenuItem text="Back" :onClick="closeSettings" />
    <br />
    <br />

    <label class="container" name="EnableRadio" id="radio-enabled">
      <p class="menu-text">Enable Radio</p>
      <input type="checkbox">
      <span class="checkmark"></span>
    </label>
    <input type="checkbox" />
    <br />
    <p class="menu-text" id="menu-volume-text">Radio Volume</p>
    <br />
    <input type="range" name="RadioVolume" id="radio-volume" min="0" max="100" step="1" value="50" class="slider" />
    <p class="menu-text" id="menu-volume-text">DLC Server</p>
    <br />
    <div class="url-input-container">
      <span class="prefix">http://</span>
      <input class="myinput-link" v-model="inputText" :placeholder="inputText" @keydown.enter="SetDLCURL" />
      <span class="link-icon">
        🔗
      </span>
    </div>

    <br />
    <p class="hover-underline-animation pink" onclick="ConvertCustomDLC()">
      Convert Custom DLC
    </p>
    <div>
      <h3>Select a MIDI Device:</h3>
      <div v-if="midiDevices.length > 0">
        <label v-for="device in midiDevices" :key="device.Port">
          <input type="radio" :value="device.Port" v-model="selectedDevice" @change="updatePreferredDevice" />
          {{ device.Name }}
        </label>
      </div>
      <p v-else>No devices available</p>

      <p>Selected Device: {{ selectedDeviceName }}</p>
    </div>
    <MenuItem text="Save Settings" colorClass="green" :onClick="saveSettings" />
    <VisualLatencyTest />
  </div>
  <TrackRadio />
</template>
<script>
import MenuItem from './components/MainMenuOption.vue';
import TrackRadio from './components/TrackRadio.vue';
import VisualLatencyTest from './components/Settings/VisualLatencyTest.vue';

export default {
  components: {
    MenuItem,
    TrackRadio,
    VisualLatencyTest
  },
  data() {
    return {
      midiDevices: [{
        Name: "Test", Port: 0
      }], // List of MIDI devices
      selectedDevice: null, // Selected MIDI device index
    };
  },
  computed: {
    inputText: {
      get() {
        if (typeof GetDLCURL_Internal === 'function') {
          // eslint-disable-next-line
          return GetDLCURL_Internal();
        }
        return "dlc.example.com";
      },
      set(value) {
        if (typeof SetDLCURL_Internal === 'function') {
          // eslint-disable-next-line
          SetDLCURL_Internal(value);
        }
      }
    },
    selectedDeviceName() {
      const device = this.midiDevices.find((d) => d.Port === this.selectedDevice);
      return device ? device.Name : "None";
    },
  },
  mounted() {
    if (typeof GetMIDIDevices_Internal === 'function') {
      // eslint-disable-next-line
      console.log(GetMIDIDevices_Internal());
      // eslint-disable-next-line
      this.midiDevices = JSON.parse(GetMIDIDevices_Internal());
    }
  },
  methods: {
    loadScene(scene) {
      if (typeof LoadScene === 'function') {
        // eslint-disable-next-line
        LoadScene(scene);
      }
      window.location.href = "/SongList.html";
    },
    LoadDLCScene(scene) {
      if (typeof LoadScene === 'function') {
        // eslint-disable-next-line
        LoadScene(scene);
      }
      window.location.href = "/DLC_NEW.html";
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
    updatePreferredDevice() {
      console.log("Selected MIDI Device Index:", this.selectedDevice);
      if (typeof SetPreferredMidiDevice_Internal === 'function') {
        // eslint-disable-next-line
        SetPreferredMidiDevice_Internal(this.selectedDeviceName);
      }
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
    },
  },
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

.underline-bar {
  margin-bottom: 25px;
}

.main-menu {
  margin-left: 50px;
  margin-top: 50px;
}

.url-input-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 270px;
  height: 40px;
  border-radius: 2px;
  position: relative;
  border: 1px solid #2f2f2f;
}

.url-input-container .prefix {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
  font-size: 15px;
  height: 100%;
  width: 70px;
  font-weight: 600;
  padding: 0 10px;
  background-color: #f0f0f0;
  border-radius: 2px 0px 0px 2px;
}

.myinput-link {
  display: flex;
  align-items: center;
  justify-content: center;
  outline: none;
  font-weight: 500;
  border: none;
  padding: 0px 10px;
  height: 100%;
  width: 160px;
  background-color: #fff;
  font-size: 15px;
}

.link-icon {
  font-size: 16px;
  background-color: #fff;
  height: 100%;
  width: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding-right: 10px;
  border-radius: 0px 2px 2px 0px;
  cursor: pointer;
  position: relative;
}
</style>