# UI and Menus

> Verified against the working tree on 2026-11-08 (the RmlUi port, not yet committed). Engine submodule at 8cee2340.

The game's menus are RmlUi documents (`.rml` + `.rcss` under `Assets/UI/`) shown by the engine's `UIDocument` component, and plain game components that drive them through the engine's script view models. There is no JavaScript and no browser: every value a page shows is a model value a controller sets, and every button either carries an engine inline action (`load-scene:`, `quit`) or raises a model event the controller polls. The engine side is documented in `Engine/Docs/UI-RmlUi-and-ImGui.md`.

## Overview

Each menu scene has one entity carrying two components: a `UIDocument` naming the `.rml` file, and a controller component (`MainMenuController`, `DLCMenuController`, ...). Controllers are ordinary components with a `Update( float )` method; `MenuCore` (`Game/Source/Cores/MenuCore.cpp`), declared in each menu scene's `Cores`, ticks whichever controllers its `UIDocument` entities carry. Cores run while the world runs, so the menus also work in the editor's Play mode. The first update creates the page's model (`RmlUiCore::ModelEnsure`), registers its events and sets every value the document binds; later updates poll events and keep the values current.

| Scene | Document | Model | Controller |
|-------|----------|-------|------------|
| `Assets/MainMenu.lvl` | `Assets/UI/MainMenu.rml` | `main_menu` | `MainMenuController` |
| `Assets/TrackList.lvl` | `Assets/UI/TrackList.rml` | `song_library` | `TrackListMenuController` |
| `Assets/DLC.lvl` | `Assets/UI/DLC.rml` | `dlc_store` | `DLCMenuController` |
| `Assets/Example.lvl` (gameplay) | `Assets/UI/InGameMenu.rml` | `in_game` | `InGameMenuController` |
| `Assets/TrackStats.lvl` | `Assets/UI/TrackStats.rml` | none | `TrackStatsMenuController` (Escape only) |
| `Assets/Vocals.lvl` | `Assets/UI/Vocals.rml` | `vocals` | `VocalsTestCore` fills it; `VocalsTestComponent` only tags the entity |

## Key Files

| Path | Role |
|------|------|
| `Assets/UI/Drumsmith.rcss` | Shared controls: buttons with the coloured underline, sliders, scrollbars, the plain "menu page" layout |
| `Assets/UI/Radio.rcss` | The radio widget both the main menu and the DLC page carry |
| `Assets/UI/Library.rcss` | The list/details/footer/flyout layout the song library and the DLC catalogue share |
| `Assets/UI/MainMenu.rcss`, `InGameMenu.rcss`, `Vocals.rcss` | Per-page layout |
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

### Main menu (`main_menu`)

Six links (Practice is a disabled placeholder) and a settings panel over the same backdrop. The panel's sliders bind two-way with `data-value`, and `ApplySettings( false )` copies them into `GameSettings` every frame while it is open; Back, Escape and Save Settings write the file. The DLC server is a text field (host name; a scheme is optional, trailing slashes are stripped). MIDI devices are listed from `MidiDevice::GetDevices()` as choice buttons, and the chosen name is what `PreferredMidiDevice` stores.

The **visual latency test** replaces the old pixel-based widget: while the test runs, a marker sweeps a box every 2 s and the controller watches the keyboard (`UpdateLatencyTest`; Escape, Tab, Enter and Space are excluded because the UI reacts to them). Each press records `(marker position - centre)` in milliseconds, positive when late; the page shows the last value and the rolling average of 10, and "Use the average" copies that into the Visual Delay slider. Nothing consumes `VideoLatency` yet (`Docs/Latency-and-Responsiveness.md`).

### The radio widget (`TrackRadioUtils`)

Both pages that play menu music carry the same markup (`#track-radio`, styled by `Assets/UI/Radio.rcss`) and give their model to a `TrackRadioUtils`. It ticks `TrackRadio::Update`, auto-plays the next random track, and fills `radio_title`, `radio_artist`, `radio_art`, `radio_position`, `radio_duration`, `radio_progress` (0..1000) and `radio_visible`. The widget slides in for a new track or a hover (`radio_show`, also raised by a hover zone where it hides) and slides out 15 s later. Events: `skip`, `seek(ev.value)`. `TrackRadio` therefore still only advances while a menu with the widget is loaded (`Docs/Audio.md`).

`TrackRadioUtils::ArtSource` is the one place album-art paths are built: `/Assets/DLC/<song>/<art>`. The leading slash makes RmlUi resolve the path through the VFS instead of relative to the document.

### Song library (`song_library`)

`TrackListMenuController::PopulateModel` turns `TrackDatabase::SortTracks( sort, filter )` into the `tracks` list (category headers when sorting by title, artist or year) and the `filters` list with counts. Hovering or focusing a row selects it (details panel, and a radio preview of the song after 0.25 s); clicking the art or PLAY loads the gameplay scene with that track; View Stats loads `Assets/TrackStats.lvl`. The footer button opens the sort/filter flyout; a scrim click or Escape closes it.

### DLC catalogue (`dlc_store`)

`DLCMenuController` owns the whole flow the old page split between JavaScript and C++:

1. **Index:** the first update queues a download of `<server>/dlc_index.json` to `Assets/DLC/dlc_index.download`; on success the file replaces `Assets/DLC/dlc_index.json`, so a failed fetch never truncates the cached copy. With no server set, or when the server can't be reached, the cached copy is shown with a status line saying so.
2. **Catalogue:** each entry (`Title`, `Artist`, `Album`, `Year`, `DLCSource`, `AlbumArtFileName`, `FolderPath`, `FilesInFolder`; `Assets/DLC/DLCParser.py`) becomes a `CatalogueTrack`. A track already in `TrackDatabase` (its source path contains `/<FolderPath>/`) is marked installed and gets PLAY, Preview and (editor builds) Edit chart instead of a download button.
3. **Art:** covers are prefetched one at a time into `Assets/DLC/.catalogue/<FolderPath>/<art>`; rows show `img/track-bg.png` until theirs arrives. The library scan ignores dot-folders.
4. **Download:** `download(index)` queues every file of `FilesInFolder` into `Assets/DLC/<FolderPath>/`, ahead of the art prefetch; the row shows `Downloading n/m`. When all files landed, `TrackDatabase::RegisterNewTrack` adds the song and the radio plays it (`PlayLatestTrack`), as the old page did.

All network work runs on one worker thread, one `Transfer` at a time (`Web::DownloadFile` per file); `Update` polls it and does every model and database change on the main thread. Sorting and filtering are the library's (`TrackListSort`, `TrackListFilter` by `DLCSource` tag, the same tag table as `TrackDatabase::GatherFilterCounts`).

### Pause menu (`in_game`)

Escape or Resume toggles the overlay and fires `InGamePauseCurrentTrack` / `InGameResumeCurrentTrack`; `NoteHighwayCore` also stops ticking while paused. Options holds the two delay sliders (saved on Back) and Exit returns to the library. The controller focuses the right button after each panel change so a gamepad can drive it.

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
- **The latency test only hears the keyboard.** MIDI pads don't register, and `VideoLatency` is still read by nothing.
- **Leftovers:** the Vue project (`Game/ui/`) and the old HTML/CSS/JS under `Assets/UI/` are unused and ship with the assets until deleted.

## Related Docs

- `Docs/Game-Architecture.md`: events the controllers fire, the settings table
- `Docs/Audio.md`: the radio the widget drives
- `Docs/Songs-and-DLC.md`: the index format and the download flow behind the DLC page
- `Engine/Docs/UI-RmlUi-and-ImGui.md`: documents, models, inline actions, the designer and hot reload
