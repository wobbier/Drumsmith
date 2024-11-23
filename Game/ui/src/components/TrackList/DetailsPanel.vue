<template>
    <div class="album-art">
        <img v-if="!track?.FolderPath" class="album-art" src="file:///{{track.AlbumArt}}" />
        <img v-if="track?.FolderPath" class="album-art" :src="`http://${track.DLCURL}/${track.FolderPath
            }/${track.AlbumArtFileName}`" />
    </div>
    <div class="dynamic-div" @click="selectTrackToPlay(track.Title); toggleTrackListVisibility()">
        <div class="album-title">
            <h1>{{ track.Title }}</h1>
            <h2>{{ track.Artist }}</h2>
            <h3>{{ track.Album }}</h3>
            <h3>{{ track.Genre }}</h3>
            <h3>{{ track.Year }}</h3>
        </div>
        <div class="note-count">Note Count: {{ track.NoteCount }}</div>
        <div class="clearfix"></div>
    </div>
    <div class="dynamic-div" @click="viewTrackStats(track.Title)">
        View Stats
    </div>
</template>

<script>
export default {
    props: {
        track: {
            type: Object,
            required: true,
        },
    },
    methods: {
        selectTrackToPlay(trackName) {
            console.log('Track selected:', trackName);
        },
        toggleTrackListVisibility() {
            console.log('Toggled track list visibility');
        },
        viewTrackStats(trackName) {
            console.log('Viewing stats for track:', trackName);
        },
    },
};
</script>

<style scoped></style>