var timer;
function DelayedTrackPreview(trackIndex) {
  clearTimeout(timer);
  RequestDetailsPanelUpdate(trackIndex);
  timer = setTimeout(function () {
    PlayTrackPreview(trackIndex);
  }, 250);
}

function ClearTrackList() {
  // Fetch the container div
  const containerDiv = document.getElementById("myDivContainer");

  // Clear previous divs
  const oldDivs = containerDiv.querySelectorAll(".dynamic-div");
  oldDivs.forEach((div) => div.remove());
}

function ToggleTrackListVisibility() {
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
}

function TryAreToolsEnabled() {
  if (typeof AreToolsEnabled === "function") {
    // eslint-disable-next-line
    return AreToolsEnabled();
  }
  return false;
}

function AddTrack(track) {
  // Fetch the container div
  const containerDiv = document.getElementById("myDivContainer");
  const dynamicDiv = document.createElement("div");
  dynamicDiv.classList.add("dynamic-div");

  dynamicDiv.innerHTML = `
      <div class="dynamic-div" onclick="SelectTrackToPlay('${track.TrackName}', '${track.TrackIndex}'); ToggleTrackListVisibility();" onmouseover="DelayedTrackPreview('${track.TrackIndex}')">
      <!--div class="album-art" style="background-image: url('file:///${track.AlbumArt}');"-->
      <img class="album-art" src="file:///${track.AlbumArt}" />
      </div>
      <div class="album-title">
          <h1 class="BoldRegular Large">${track.TrackName}</h1>
          <h2 class="Regular Small">${track.ArtistName}</h2>
          <h3>${track.Year}</h3>
      </div>
      <div class="note-count">Note Count: ${track.NoteCount}</div>`;
  if (TryAreToolsEnabled()) {
    dynamicDiv.innerHTML += `<div onclick="EditTrack('${track.TrackName}')">DEV TOOLS ENABLED</div>`;
  }
  if (track.FolderPath) {
    dynamicDiv.innerHTML += `<div onclick="DownloadDLC('${track.FolderPath}')">DEV TOOLS ENABLED</div>`;
  }
  dynamicDiv.innerHTML += `
      <div class="clearfix"></div>
  </div>`;

  // Create and append text content
  //const textNode = document.createTextNode(track);
  //dynamicDiv.appendChild(textNode);

  //// Create and append image
  //const image = document.createElement('img');
  //image.src = "file:///" + imageSrc;
  //image.alt = track;
  //dynamicDiv.appendChild(image);

  containerDiv.appendChild(dynamicDiv);
}

function AddCategory(name) {
  const containerDiv = document.getElementById("myDivContainer");
  const dynamicDiv = document.createElement("div");
  dynamicDiv.classList.add("dynamic-div");
  dynamicDiv.classList.add("BoldRegular");
  dynamicDiv.classList.add("Large");

  dynamicDiv.innerHTML = name;

  containerDiv.appendChild(dynamicDiv);
}

function UpdateDetailsPanel(track) {
  const containerDiv = document.getElementById("trackDetails");

  containerDiv.innerHTML = `
          <div class="album-art">
              <img src="file:///${track.AlbumArt}" />
          </div>
          <div class="dynamic-div" onclick="SelectTrackToPlay('${track.TrackName}'); ToggleTrackListVisibility();" onmouseover="DelayedTrackPreview('${track.TrackIndex}')">
          <div class="album-title">
              <h1>${track.TrackName}</h1>
              <h2>${track.ArtistName}</h2>
              <h3>${track.AlbumName}</h3>
              <h3>${track.Genre}</h3>
              <h3>${track.Year}</h3>
          </div>
          <div class="note-count">Note Count: ${track.NoteCount}</div>
          <div class="clearfix"></div>
      </div>
          <div class="dynamic-div" onclick="ViewTrackStats('${track.TrackName}');">
            View Stats
          </div>`;
}

function fillDivs() {
  // Fetch the container div
  const containerDiv = document.getElementById("myDivContainer");
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
    AddTrack(item);
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
}

AddTrack({
  AlbumArt: "../DLC/30 Seconds to Mars - The Kill/album.png",
  AlbumName: "",
  ArtistName: " 30 Seconds to Mars",
  Genre: " Modern Rock",
  Icon: " ghwt",
  NoteCount: 0,
  TrackIndex: 0,
  TrackName: " The Kill",
  TrackSource:
    "M:/Projects/ME/Drumsmith/Assets/DLC/30 Seconds to Mars - The Kill//song.ogg",
  Year: 2006,
});

function SetFilters(inFilters) {
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
