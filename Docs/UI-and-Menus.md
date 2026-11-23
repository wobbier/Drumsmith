# UI and Menus

> Verified against the working tree on 2026-11-08 (the RmlUi port, not yet committed). Engine submodule at 8cee2340.
>
> Updated 2026-11-17 against the working tree (the Linear ticket pass, DRU-14 to DRU-54, on game commit 4f29840; engine submodule at c5bb6135): the tabbed settings panel (Drum Kit, Songs), the library's details, the DLC catalogue, the pause menu and the practice page. The rest is as last verified.

The game's menus are RmlUi documents (`.rml` + `.rcss` under `Assets/UI/`) shown by the engine's `UIDocument` component, and plain game components that drive them through the engine's script view models. There is no JavaScript and no browser: every value a page shows is a model value a controller sets, and every button either carries an engine inline action (`load-scene:`, `quit`) or raises a model event the controller polls. The engine side is documented in `Engine/Docs/UI-RmlUi-and-ImGui.md`.

## Overview

Each menu scene has one entity carrying two components: a `UIDocument` naming the `.rml` file, and a controller component (`MainMenuController`, `DLCMenuController`, ...). Controllers are ordinary components with a `Update( float )` method; `MenuCore` (`Game/Source/Cores/MenuCore.cpp`), declared in each menu scene's `Cores`, ticks whichever controllers its `UIDocument` entities carry. Cores run while the world runs, so the menus also work in the editor's Play mode. The first update creates the page's model (`RmlUiCore::ModelEnsure`), registers its events and sets every value the document binds; later updates poll events and keep the values current.

| Scene | Document | Model | Controller |
|-------|----------|-------|------------|
| `Assets/MainMenu.lvl` | `Assets/UI/MainMenu.rml` | `main_menu` | `MainMenuController` |
| `Assets/TrackList.lvl` | `Assets/UI/TrackList.rml` | `song_library` | `TrackListMenuController` |
| `Assets/DLC.lvl` | `Assets/UI/DLC.rml` | `dlc_store` | `DLCMenuController` |
| `Assets/Practice.lvl` | `Assets/UI/Practice.rml` | `practice_menu` | `PracticeMenuController` (`Docs/Practice.md`) |
| `Assets/Example.lvl` (gameplay) | `Assets/UI/InGameMenu.rml` | `in_game` | `InGameMenuController` |
| `Assets/TrackStats.lvl` | `Assets/UI/TrackStats.rml` | none | `TrackStatsMenuController` (Escape only) |
| `Assets/Vocals.lvl` | `Assets/UI/Vocals.rml` | `vocals` | `VocalsTestCore` fills it; `VocalsTestComponent` only tags the entity |

## Key Files

| Path | Role |
|------|------|
| `Assets/UI/Drumsmith.rcss` | Shared controls: buttons with the coloured underline, sliders, scrollbars, the plain "menu page" layout |
| `Assets/UI/Radio.rcss` | The radio widget both the main menu and the DLC page carry |
| `Assets/UI/Library.rcss` | The list/details/footer/flyout layout the song library and the DLC catalogue share |
| `Assets/UI/MainMenu.rcss`, `InGameMenu.rcss`, `Vocals.rcss`, `Practice.rcss` | Per-page layout |
| `Game/Source/UI/MusicLinks.h/.cpp` | The song panels' links out to Spotify, Apple Music and YouTube Music |
| `Game/Source/Components/*MenuController.h/.cpp` | The controllers |
| `Game/Source/Cores/MenuCore.h/.cpp` | Ticks the controllers of the loaded scene |
| `Game/Source/UI/TrackRadioUtils.h/.cpp` | The radio: random playback between menus, and the `radio_*` values and events of a page's model |
| `Game/Source/UI/UIModelUtils.h` | `UIModel::LastEventArgs` / `ArgNumber` / `ArgString`: event arguments as JSON |
| `Game/ui/`, `Assets/UI/*.html`, `Assets/UI/css`, `Assets/UI/js`, `Assets/UI/Old` | The retired Ultralight/Vue pages. Nothing loads them; kept until deleted |

## How It Works

### The controller pattern

```cpp
RmlUiCore* ui = GetEngine().RmlUi;
ui->ModelEnsure( "main_menu" );
ui->ModelRegisterEvent( "main_menu", "open_settings" );      // <button data-event-click="open_settings">
ui->ModelSetNumber( "main_menu", "settings_open", 0 );       // data-if="settings_open"
for( std::string e; !( e = ui->ModelPollEvent( "main_menu" ) ).empty(); )
{
    const json args = UIModel::LastEventArgs( *ui, "main_menu" );   // data-event-click="select(track.index)"
    ...
}
```

- **Values** are numbers or strings; lists (`ModelSetListCount` / `ModelSetItemString`) back `data-for` rows. A changed value dirties only its bindings, so controllers may set their whole model every frame (the radio does).
- **Events** carry their arguments as a JSON array. Range inputs report `ev.value` as text, so `UIModel::ArgNumber` parses both forms.
- **Register every bound key before the document loads.** When a model gains a key after a document bound to it loaded, the engine reloads that document (`RmlUiCore::SyncModels`), which resets scroll and focus. The controllers set all `detail_*` keys up front for that reason.
- **Scene changes** go through `LoadSceneEvent` (`Queue()`), from inline actions or controller code, exactly as before; the play handoff to `NoteHighwayCore` is unchanged (`Docs/Game-Architecture.md`).
- **Escape** is read from `Input::WasKeyPressed` in each controller: closes the flyout or settings panel first, else leaves the scene.
- **Alt+Z** hides every page and the in-game HUD for screenshots, in every build including Retail. It is the engine's (`RmlUiCore::SetUIHidden`, `Engine/Docs/UI-RmlUi-and-ImGui.md`): pages keep updating but draw nothing and take no clicks, keys or gamepad navigation. Alt+Z again or Escape brings the UI back; that Escape also reaches the controllers, so in a song it shows the UI and opens the pause menu.

### Main menu (`main_menu`)

The hideout (`Docs/Hideout-and-Progression.md`) is the main menu when its room loads: the tier's 3D scene behind the page, a label over each station (`stations`), a header with the room and the next goal, the station panels (records, gigs), a *While you were out* notice, and Vocal Test and Exit in a corner. `MainMenuController` owns the `Hideout` and passes it the events it doesn't handle itself. `hideout` (0 or 1) switches the page between that and the flat menu below, which stays as the fallback when there's no room. The settings panel is the same in both; the hideout's mixer opens it.

Six links and a settings panel over the same backdrop. The panel is six tabs (`settings_tab`): **Game** (highway speed, technique, lyrics), **Sound & Timing** (radio volume, the metronome, the two delays, the way into the calibration), **Venue** (stage lights, venue, room, camera), **Graphics** (tab 5, shown after Venue), **Drum Kit** and **Songs**. Graphics isn't `GameSettings`: its buttons are the engine's player-settings actions (`onclick="setting:Graphics.VSync|false"`, `window-mode:`, `setting-step:`, and `data-setting-selected` / `data-window-mode` / `data-options="quality"` for the selection; `Engine/Docs/Player-Settings.md`), so they apply and save on their own (`user://Settings.json`) without Save Settings: quality preset (Auto or the engine's Low..Ultra), display mode, VSync, frame rate limit, render scale, upscaling and dynamic resolution. RmlUi ignores those `data-` attributes because no data view has their names. The sliders bind two-way with `data-value`, and `ApplySettings( false )` copies them into `GameSettings` every frame while the panel is open; Back, Escape and Save Settings write the file.

**Drum Kit.** MIDI devices are listed from `MidiDevice::GetDevices()` as choice buttons; choosing one stores its name (`PreferredMidiDevice`) and opens it at once, and the list follows devices being plugged in and unplugged (`MidiDevice::GetGeneration`, `Docs/MIDI-and-Pads.md`). Below it every pad has a **Key** and a **MIDI** button (`pads` list; `RefreshPads`): press one, then press the key or hit the pad (`UpdateKitBinding`; Escape cancels, and Escape itself can't be bound). A captured MIDI note becomes the pad's main note and is dropped from its other strokes. *Clear* unbinds a pad, *Use the standard e-kit MIDI notes* calls `PadMappingStorage::ApplyStandardKitMidi`, and *Last hit* shows what every incoming note is bound to while the panel is open. Changes apply to `PadMappingStorage` at once and are written to `Assets/Config/PadMappings.json` with the settings (Save, Back or Escape).

**Songs.** The DLC servers (`GameSettings::DLCServers`) as rows with *Test* and *Remove*, and a text field with *Add and test this server* (a server typed but not added is added on Save). A test runs on a worker thread and the row shows the answer (`QueueServerCheck` / `PumpServerChecks`, `Docs/Songs-and-DLC.md`). *Convert Custom DLC* is here too.

**Calibrate audio and video** (the `calibrate` event) saves the panel, starts a `Calibration` session and loads `Assets/Example.lvl` with `LaunchPlayTrackEvent::TrackID = Calibration::kTrackId`, the way the practice page starts a lesson. The session runs on the highway and its HUD (`#hud-calibration`, `#calibration-results` in `InGameMenu.rml`; the `in_game` model's `calibration` and `cal_*` values); *Use these* (`cal_apply`, `InGameMenuController`) writes the delays and returns here, as do Back and Escape. It replaced the keyboard-only visual latency test that sat on this tab (`Docs/Latency-and-Responsiveness.md` → Calibration).

### The radio widget (`TrackRadioUtils`)

Both pages that play menu music carry the same markup (`#track-radio`, styled by `Assets/UI/Radio.rcss`) and give their model to a `TrackRadioUtils`. It ticks `TrackRadio::Update`, auto-plays the next random track, and fills `radio_title`, `radio_artist`, `radio_art`, `radio_position`, `radio_duration`, `radio_progress` (0..1000) and `radio_visible`. The widget slides in for a new track or a hover (`radio_show`, also raised by a hover zone where it hides) and slides out 15 s later. Events: `skip`, `seek(ev.value)`, `radio_play` (the widget's Play button: `PlayRadioTrack` loads the gameplay scene with the song on the radio). `TrackRadioUtils::LaunchTrack( index )` is the one place a menu starts a song; the library, the DLC page and the radio all call it. `MenuCore::Update` ticks `TrackRadio` itself on every page, so a page without the widget still loads, fades and finishes its songs; only a page with the widget starts the next random one (`Docs/Audio.md`).

`TrackRadioUtils::ArtSource` is the one place album-art paths are built: `/Assets/DLC/<song>/<art>`. The leading slash makes RmlUi resolve the path through the VFS instead of relative to the document.

### Song library (`song_library`)

`TrackListMenuController::PopulateModel` turns `TrackDatabase::SortTracks( sort, filter )` into the `tracks` list (category headers when sorting by title, artist or year) and the `filters` list with counts. Hovering or focusing a row selects it (details panel, and a radio preview of the song after 0.25 s); clicking anywhere on a row (or pressing Enter on it, or the details column's PLAY button) loads the gameplay scene with that track, and the selected row shows a PLAY tag to say so; the star is the one part of a row that doesn't play. The library's compact rows and details column are the `.song-library` rules at the end of `Library.rcss`; the DLC catalogue keeps the older, taller rows; View Stats loads `Assets/TrackStats.lvl`. The footer button opens the sort/filter flyout; a scrim click or Escape closes it.

**Details.** Under the song's fields the panel shows its source badge ("RB2", "DS"; `TrackDatabase::SourceBadge`), *DS READY* once the chart is known to be one saved from the Track Editor, and what the chart recommends (`advice` list, `ChartAdvice::For`: a double bass pedal, extra kit pieces, techniques), filled 0.25 s after the selection settles since it reads the chart file. *Hear the original on* links out to Spotify, Apple Music and YouTube Music (`MusicLinks::Open`: the chart's own `Links`, else a search for the artist and title, in the player's browser). *Remove* deletes the song after a second, explicit yes (`TrackDatabase::RemoveTrack`). In editor builds *Edit chart* and **F4** open the song in the Track Editor.

**Search and favorites.** The search box (`search`, bound two-way) narrows the sorted, filtered list as you type: every word must appear in the title, artist, album or genre, any case. The controller compares the model's text with its own copy each frame and repopulates when it moves; Clear or Escape (with the flyout closed) empties it. Each row has a star (`favorite(track.index)`), the details panel a Favorite button, and the Favorites toggle beside the search box (also in the flyout's Filter section) lists only favorites (`favorites_only`, `favorite_count`). Favorites are saved at once in `Settings.json` (`GameSettings::FavoriteTracks`) under the song's folder name (`TrackDatabase::FavoriteKey`), so a rescan or reinstall keeps them; two DLC folders with the same name would share a star.

### DLC catalogue (`dlc_store`)

`DLCMenuController` shows every song of every server in `GameSettings::DLCServers` (the formats and rules are in `Docs/Songs-and-DLC.md`):

1. **Index:** per server, a fetch of `dlc_index.hash`; the index itself is downloaded only when the hash differs from the cached copy's (`Assets/DLC/.catalogue/_servers/<server>/`). Each server's songs are appended as it answers (`AppendIndex`); a song an earlier server already lists is skipped. The status line counts songs and servers and names the servers that couldn't be reached (their cached catalogue is shown).
2. **Catalogue:** each entry becomes a `CatalogueTrack`. A track already in `TrackDatabase` (its source path contains `/<FolderPath>/`) is installed: PLAY, Preview, Remove and (editor builds) Edit chart; when the server's `Version` differs from the one noted at download it also gets **Update** (`RefreshInstallState`). Rows carry the source badge and *DS READY* for charts made in the Track Editor.
3. **Art:** covers are prefetched one at a time into `Assets/DLC/.catalogue/<FolderPath>/<art>`; rows show `img/track-bg.png` until theirs arrives. The library scan ignores dot-folders.
4. **Download and update:** `download(index)` / `update(index)` queue every file of `FilesInFolder` into `Assets/DLC/<FolderPath>/`, ahead of the art prefetch; the row shows `Downloading n/m`. Sizes are checked; a new song that fails is deleted, a good one is registered and played on the radio (`PlayLatestTrack`), an updated one reloaded.
5. **Preview:** on a song that isn't installed, Preview fetches its main mix into the catalogue cache and the radio plays it as a guest (`QueuePreview`, `TrackRadio::PlayGuest`).
6. **Remove:** asks once in the details panel, then deletes the song's folder (`RemoveInstalled`). The other songs' library indices are re-resolved.

All network work runs on one worker thread, one `Transfer` at a time (`Web::DownloadFile` per file); `Update` polls it and does every model and database change on the main thread. Sorting and filtering are the library's (`TrackListSort`, `TrackListFilter` through `TrackDatabase::FilterForSource`). The details panel also has the *Hear the original on* links.

### Pause menu (`in_game`)

Escape or Resume toggles the overlay (in editor builds **Shift+Escape**: plain Escape belongs to Havana, which frees the mouse and hands input to the editor while the song keeps playing; the `pause_hint` model value shows the right key, and the results screen's leave-for-library key follows the same rule) and fires `InGamePauseCurrentTrack` / `InGameResumeCurrentTrack`; `NoteHighwayCore` also stops ticking while paused. Restart raises the same `retry` event as the results screen's Retry: it reloads `Assets/Example.lvl` and launches the song again from its lead-in (a practice lesson or a calibration starts over the same way). Options has two tabs (the engine's `tab:` action, no model key): **Game** holds master volume, the two delay sliders, the metronome and highway speed (saved on Back), and **Graphics** is the main menu's Graphics tab again (the same player-settings actions, so the two always agree and changes save themselves). Exit returns to the library (to the lessons after a practice lesson). The controller focuses the right button after each panel change so a gamepad can drive it. Resuming pulls the song back two seconds and fades it in (`Docs/Gameplay-Note-Highway.md`). If the MIDI device is unplugged mid-song the controller pauses and the menu says so (`midi_notice`); it also says when the device is back. In editor builds **F4** opens the song in the Track Editor.

### Practice (`practice_menu`)

`PracticeMenuController` lists the lessons of `Assets/Practice/Lessons.json` by category, with the chosen one's description, pattern, tempo (a slider and -5 / +5, remembered per lesson in `GameSettings::PracticeTempos`) and length (8, 16 or 32 bars). START builds the lesson's chart and click track (`Practice::Begin`) and loads the gameplay scene with `LaunchPlayTrackEvent::TrackID` set to `Practice::kTrackId`. `Docs/Practice.md` has the rest.

### Track stats and vocal test

Nothing records play statistics, so `TrackStats.rml` says so and offers Back. `Vocals.rml` shows the pitch meter `VocalsTestCore` writes into the `vocals` model (`pitch`, `meter`, `listening`); the core now survives a missing test vocals file instead of dereferencing a null channel.

### Editing pages

`.rml`/`.rcss` edits hot reload in the running game. The editor's UI designer (Window > UI Designer) can edit a loaded page in place (`Engine/Docs/UI-RmlUi-and-ImGui.md`). To check a page without a window: `./Engine/Tools/NixEnv.sh env -u NIX_CC ./Engine/Tools/Headless.sh ./.build/Game_linux_Debug/Game_EntryPoint_x64 --scene Assets/DLC.lvl --frames 400 --screenshot out.png`. Clicks need the editor: a flow of `play`, `ui-click #settings`, `screenshot ...` run with `Havana --scene Assets/MainMenu.lvl --editor-exec flow.edscript` (`Engine/Docs/Editor-Havana.md`). Escape can't be scripted (`Input::WasKeyPressed` reads SDL, not simulated keys).

## Caveats & Fragility

- **RmlUi has no default stylesheet.** `Assets/UI/Drumsmith.rcss` makes `div`, `h1`-`h3` and `p` blocks; anything else is inline. Bare text inside a `display: flex` container renders nothing: wrap it in a `span`. The `disabled` attribute does nothing on a `button`; use the `.disabled` class. Transition tweens are RmlUi's names (`cubic-out`, `sine-in-out`), not CSS's `ease`.
- **An image path must name a regular file.** A `TrackData.txt` with an empty `AlbumArtFileName` gives the track a folder as its art path; the engine's VFS reader aborts on a directory (ext4 reports a huge size). `ArtSource` checks `Path::IsFile`; do the same for any new image source.
- **Model keys added late reload the document** (see the controller pattern). Add new bound keys to the controller's `PopulateModel`.
- **The DLC worker joins on scene change.** Leaving the DLC page mid-download waits for the file in flight to finish (the queue is dropped). `Web::DownloadFile` has no cancel hook.
- **Partial downloads still register.** A failed multi-file download leaves whatever arrived in `Assets/DLC/<song>/`; the song registers only if every file succeeded, but the next scan picks the folder up if `TrackData.txt` landed (`Docs/Songs-and-DLC.md`).
- **Tab is focus navigation, not the flyout.** The old pages opened the sort/filter flyout on Tab; RmlUi uses Tab (and the dpad) to move focus, so the footer button and Escape are the only ways to open and close it.
- **`MenuCore` ticks controllers by type.** A new controller must be added to its `Update`, and a new menu scene must declare `MenuCore` in its `Cores`, or the page stays static.
- **MIDI devices are matched by name.** The settings panel stores the chosen device's name; two devices with the same name are indistinguishable (`Docs/MIDI-and-Pads.md`).
- **Space and Enter also press the focused button.** Binding one of them to a pad would click the pad's Key button again, so `bind_key` / `bind_midi` events are ignored for 0.3 s after either is bound (`m_bindIgnore`).
- **A server check in flight is joined on scene change**, like the DLC worker.
- **The music links open the system browser** (`SDL_OpenURL`); nothing checks that the search finds the song.
- **Leftovers:** the Vue project (`Game/ui/`) and the old HTML/CSS/JS under `Assets/UI/` are unused and ship with the assets until deleted.

## Related Docs

- `Docs/Game-Architecture.md`: events the controllers fire, the settings table
- `Docs/Audio.md`: the radio the widget drives
- `Docs/Songs-and-DLC.md`: the index format and the download flow behind the DLC page
- `Engine/Docs/UI-RmlUi-and-ImGui.md`: documents, models, inline actions, the designer and hot reload
