<template>
    <div id="PauseScreenDarkener" v-if="pauseMenuVisible || optionsMenuVisible"></div>
    <div v-if="pauseMenuVisible" id="PauseMenu">
        <img src="img/2x/Asset 2@2x.png" />
        <br />
        <img src="img/Underline.png" class="underline-bar" /><br />
        <br />
        <MenuItem text="RESUME" colorClass="green" :onClick="() => TogglePauseMenu()" />
        <br />
        <MenuItem text="OPTIONS" colorClass="orange" :onClick="() => ToggleOptionsMenu()" />
        <br />
        <MenuItem text="EXIT" colorClass="red" :onClick="() => LoadScene('Assets/TrackList.lvl')" />
    </div>
    <div v-if="optionsMenuVisible" id="OptionsMenu">
        <MenuItem text="Back" colorClass="green" :onClick="() => ToggleOptionsMenu()" />
        <br />
        <p class="menu-text">Options Menu Content Here</p>
    </div>
    <div v-if="!pauseMenuVisible && !optionsMenuVisible" id="GameUI">
        Notes Hit: 1/X
    </div>
</template>
<script>
import MenuItem from "./components/MainMenuOption.vue";

export default {
    data() {
        return {
            pauseMenuVisible: false,
            optionsMenuVisible: false,
        };
    },
    components: {
        MenuItem,
    },
    methods: {
        LoadScene(scene) {
            window.LoadScene(scene);
        },
        TogglePauseMenu() {
            if (this.pauseMenuVisible) {
                if (typeof Internal_Resume === 'function') {
                    // eslint-disable-next-line
                    Internal_Resume();
                }
            } else {
                if (typeof Internal_Pause === 'function') {
                    // eslint-disable-next-line
                    Internal_Pause();
                }
            }
            this.pauseMenuVisible = !this.pauseMenuVisible;
        },
        ToggleOptionsMenu() {
            this.optionsMenuVisible = !this.optionsMenuVisible;
            if (!this.optionsMenuVisible) {
                this.pauseMenuVisible = true;
            } else {
                this.pauseMenuVisible = false;
            }
        },
    },
    mounted() {
        window.TogglePauseMenu = this.TogglePauseMenu;
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" || event.keyCode === 13) {
                this.TogglePauseMenu();
            }
        });
    }
};
</script>

<style scoped>
#PauseMenu,
#OptionsMenu {
    position: absolute;
    top: 10%;
    left: 50%;
    transform: translateX(-50%);
    text-align: center;
    z-index: 100;
}

#GameUI {
    position: absolute;
    top: 10px;
    right: 10px;
    z-index: 100;
    color: white;
}

#PauseScreenDarkener {
    position: fixed;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.7);
    z-index: 99;
}
</style>