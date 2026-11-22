# Drumsmith — Off-Grid Work Notes 🏔️

Notes for working on Drumsmith + MitchEngine with no internet.
Window: roughly **5 evenings, a few hours each** — tonight (Fri Jun 26) through Tue Jun 30, wheels-up **Wed Jul 1 AM**.

> **Biggest thing to internalize:** when you're off the grid, **you won't have me (Claude)** either —
> Claude Code needs the network. This file is written to be self-sufficient. Anything you'd
> normally hand me ("look this up", "why won't this link", "what's the API for X") you'll be
> doing solo. The [Self-Rescue](#-self-rescue-no-claude-no-google) section is your fallback.

---

## ✈️ Pre-Flight — DO THIS WHILE YOU STILL HAVE INTERNET

These all need the network. If you skip them you'll hit a wall offline.

- [x] **`npm ci` in `Game/ui`** — DONE & verified (959 packages, `npm run serve` boots to
      `http://localhost:8080`). The UI build needs the registry, so it had to be fetched online.
      > ⚠️ Gotcha hit during prep: the first install came out **corrupt** (only 570 packages,
      > `webpack-chain` missing `src/Config.js` → `Cannot find module` on `npm run serve`). Cause was
      > stale/corrupt npm cache entries. If the UI dies with a missing-module error offline, the cache
      > is already clean now, so a plain reinstall should fix it — but the *belt-and-suspenders* recipe is:
      > ```bash
      > cd Game/ui && npm cache verify && rm -rf node_modules && npm ci
      > # verify it actually works:  npm run serve   # → "App running at http://localhost:8080"
      > ```
      > Reinstall needs the registry **or** a complete `~/.npm/_cacache`. Yours is now verified, but a
      > clean `npm ci` offline is not guaranteed — so **don't delete the working `node_modules` offline**
      > unless you have to.
- [ ] **Do one full clean build NOW** to surface any hidden network deps (NuGet restore for the
      C# ScriptCore module, shader tools, etc.) while you can still fix them:
      ```bash
      nix develop --command bash -c './Project/GenerateSolution.sh && make -f Drumsmith.make Havana config=editor_debug -j$(nproc)'
      ```
      `~/.nuget/packages` is currently **empty** — if the managed build needs any NuGet package,
      this is when you'll find out.
- [ ] **Pin the nix dev shell against garbage collection** so the closure survives `nix-collect-garbage`:
      ```bash
      nix develop --profile .nix-devshell-gcroot --command true
      ```
- [ ] **Confirm offline-readiness** (fails fast if anything's missing from the store):
      ```bash
      nix develop --offline --command true   # should print: 🍉 Shell Ready!
      ```
- [ ] **`git pull` / fetch submodules now** if you want latest — you can't offline.
- [ ] Optional: skim/clone any docs you know you'll want (bgfx, Ultralight, FMOD, SDL2 API refs)
      to local files. No `WebFetch`, no Google offline.

---

## 🔌 What Works vs. Breaks Offline

| Works offline ✅ | Breaks offline ❌ |
|---|---|
| `nix develop` (verified — whole closure is in your store) | `nix flake update`, editing flake `inputs` |
| Sharpmake generation (`Sharpmake.Application.dll` is prebuilt, no restore) | `nix-collect-garbage` *can evict the shell* — pin it (above) |
| Full C++ build (bgfx/FMOD/Ultralight libs all present locally) | `npm ci` / `npm install` (registry) |
| Running Havana (after the flake.nix `LD_LIBRARY_PATH` fix) | `git pull` / `git push` / `git submodule update` |
| `git commit`, branch, diff, log, local rebases | NuGet restore for anything not already cached |
| Editing code, reading code, this file | Asking me anything 🙂 |

**Golden rules while off-grid:**
1. Do **not** run `nix flake update` or `nix-collect-garbage`.
2. **Commit often, locally.** Push when you're back. (You already have uncommitted work — see below.)
3. Always work inside `nix develop` (the runtime libs come from its `LD_LIBRARY_PATH`).

### Build & run cheat-sheet
```bash
nix develop                                   # enter the shell first, always
./Project/GenerateSolution.sh                 # regenerate makefiles after a *.sharpmake.cs change
make -f Drumsmith.make Havana config=editor_debug -j$(nproc)
./.build/Editor_Debug/Havana                  # editor
# other targets: Game_EntryPoint, HUB, ShaderEditor   | configs: editor_debug, debug, release
```
> Reminder you rediscovered last session: GNU make won't rebuild just because the makefile
> changed (the makefile isn't a prerequisite of the targets). After regenerating, if a target
> looks stale, touch a source file in it or `make ... clean` that target.

---

## 🌐 Serving a Local DLC Server (any folder over HTTP)

Your DLC "server" is just a static folder served over HTTP. The client (`MainMenuController.cpp:96`)
takes a base URL and fetches **`<baseURL>/dlc_index.json`**, then pulls the DLC files from there.
So all you need is to point an HTTP server at a folder that contains `dlc_index.json` at its root.

**`python3` is already in the `nix develop` shell** — so this works fully offline, no install.

```bash
# Serve ANY folder, no cd needed (Python 3.7+). Folder must contain dlc_index.json at its root.
python3 -m http.server 8000 --directory "/abs/path/to/your/dlc/folder"

# Or the cd version:
cd "/path/to/your/dlc/folder" && python3 -m http.server 8000

# Serve to other devices on the LAN (e.g. a phone/another box), not just localhost:
python3 -m http.server 8000 --bind 0.0.0.0 --directory "/path/to/folder"
```

Then in Drumsmith, point the DLC URL at it. **Two gotchas, both from the actual code:**

1. **Always include the `http://` scheme.** `NormalizeDownloadUrl` (`HttpDownload.cpp:243`) defaults
   to **`https://`** when no scheme is present — so a bare `localhost:8000` becomes
   `https://localhost:8000` and fails against a plain dev server. Use exactly:
   ```
   http://localhost:8000
   ```
   (no trailing slash — the client appends `/dlc_index.json` itself).
2. **The index file must be named `dlc_index.json`** (not `index.json`) and live at the root of the
   served folder, alongside the DLC files it references.

**Sanity-check the server before launching the game** (proves the path + scheme + filename):
```bash
curl http://localhost:8000/dlc_index.json     # should dump your index JSON
```

The C++ download path uses libcurl directly (not the webview), so **CORS doesn't apply** here — a
plain `python3 -m http.server` is enough. (If you ever fetch the index from JS inside the Ultralight
UI instead, then you'd need a server that sends `Access-Control-Allow-Origin`.)

---

## 🧷 Uncommitted work to commit before you go

So you don't lose it / so you have a clean base to branch from:

- **Engine submodule** (`Engine/`): `Engine.sharpmake.cs`, `Tools/BaseProject.sharpmake.cs`
  (the LibGroup / `IsLinkerInvokedViaCompiler` link refactor), `Source/Window/SDLWindow.cpp`,
  `Tools/ProjectTemplate/.../GenerateSolution.sh`, `Assets/Config/imgui.cfg`.
- **Main repo**: `flake.nix` (the fontconfig/wayland runtime fix), `Game/Source/CoreGame/AudioPack.cpp`,
  `Game.sharpmake.cs`, configs.

Commit the submodule first, then bump the pointer in the main repo. All offline-safe; push when home.

---

## 📋 Worklist — Pick by Energy Level

All grounded in real TODOs/files in the repo. Estimates assume a tired-but-functional evening.
Suggested rhythm: **warm up on an XS, then sink the rest of the night into one S or M.**

### XS — 15–45 min, low risk, good for a tired night
- [ ] **Window icon support** — `Engine/Source/Window/SDLWindow.cpp:121` (`#TODO Icon support`).
      `SDL_SetWindowIcon` + an `SDL_Surface` from a bundled PNG. Self-contained, satisfying.
- [ ] **Editor clear-type label** — `Engine/Source/Components/Camera.cpp:269`
      (`TODO: Display the proper clear type as text`). Map the enum → string in the inspector.
- [ ] **Kill a dead TODO** — `Engine/Source/Components/Scripting/ScriptComponent.h:7`
      (`TODO: this should go`). Confirm it's dead, remove it, rebuild.
- [ ] **Texture/Cubemap unload stubs** — `Moonlight/.../Graphics/Texture.cpp:46` &
      `Cubemap.cpp:13` (`TODO: Unload`). At minimum document the lifetime; ideally free the bgfx handle.
- [ ] **Cache an input lookup** — `Engine/Source/Engine/Input.cpp:156` (`TODO: Cache this :/`).

### S — one evening, contained
- [ ] **Recursive `FindByName`** — `Engine/Source/Scripting/Bindings/Systems/World.bindings.cpp:33`.
      The binding only scans the scene root's direct children; make it walk the whole hierarchy.
      Real correctness bug, well-scoped.
- [ ] **Editor game-view output sizing** — `Engine/Source/Components/Camera.cpp:133` & `:296`.
      Camera reads the wrong output size in the editor viewport. Visible, testable in Havana.
- [ ] **Audio flags support** — `Engine/Source/Cores/AudioCore.cpp:69`
      (`#TODO: Add support for audio flags.`). Plumb FMOD flags through `SoundResource`.
- [ ] **Script name-clash fix** — `Engine/Modules/ScriptCore/Source/ScriptRegistry.cs:12`.
      Scripts are looked up by `Type.Name`; collisions silently break. Qualify by namespace/full name.
- [ ] **Framebuffer resize** — `Moonlight/.../Device/FrameBuffer.cpp:22` logs
      `[TODO] Trying to resize frame buffer.` and does nothing. Implement the bgfx resize path;
      fixes editor-viewport / window-resize glitches.

### M — two or three evenings, meaty
- [ ] **DLC chart parsing** — you have a real test song locally
      (`Assets/DLC/30 Seconds To Mars - The Kill/`). Knock out the `TrackList` / `CustomTrackDefineTest`
      TODOs as a set:
      - `Game/Source/CoreGame/TrackList.cpp:129` — support `.chart` DLC files
      - `TrackList.cpp:244` — support MIDI DLC files
      - `CustomTrackDefineTest.cpp:152` — switch on event type
      - `CustomTrackDefineTest.cpp:267` — map pro-drums to proper lanes
      Pure parsing + data, no network, immediately playable to verify.
- [ ] **Script lifecycle split** — `Engine/Source/Cores/Scripting/ScriptCore.cpp:60`
      (`Awake-before-Start split`) + `:85` (re-add the class dump binding). Touches C++/C# interop.
- [ ] **Physics collision-events cleanup** — `Engine/Source/Physics/RigidBodyWithCollisionEvents.h:32`
      ("clean up this huge mess"). The author (you) warned future-you about it — good evening for a
      careful refactor while it's fresh-ish.

### L — the whole week if you want one big arc
- [ ] **End-to-end custom-song pipeline** — fold all the DLC/chart TODOs above into one feature:
      detect a song folder → parse `.chart`/`.ini`/MIDI → load audio (decide the OPUS question at
      `TrackList.cpp:142`) → build the note highway → play. The 30STM test song is your fixture.
      High payoff, fully offline.
- [ ] **MIDI drum-kit input pass** — `Game/Source/Midi/MidiDevice.cpp`. Hot-plug handling, a
      mapping/config surface, latency tuning (ties into your recent "Latency config" commit).

### Non-code, high-value, zero-network
- [ ] **Write the docs you keep meaning to** — there's no `CLAUDE.md`/architecture doc. Capture the
      module map (Dementia=core/util, Moonlight=bgfx renderer, Havana=editor, ScriptCore=C# scripting,
      ImGUI, Tool), the Linux build quirks, and the Sharpmake LibGroup fix rationale. Future-you and
      future-me both benefit.
- [ ] **flake.nix deprecation cleanup** — nixpkgs now warns `xorg.libX11 → libx11`, etc. Rename the
      `pkgs.xorg.*` refs to the new top-level names. These are aliases to the *same* store paths, so
      it's **offline-safe** — but re-run `nix develop --offline --command true` after to confirm.
- [ ] **Investigate empty `DOTNET_LINUX_NATIVE_DIR`** — the shellHook's `find` came back empty this
      session; trace why (path/glob changed?) and fix the hook.

---

## 🛟 Self-Rescue (no Claude, no Google)

When something breaks and you can't ask me:

- **Build fails after a `.sharpmake.cs` edit** → re-run `./Project/GenerateSolution.sh`, then if the
  target won't rebuild, `touch` a source file in it (make-staleness gotcha above).
- **Link errors about archive order / undefined symbols** → it's the GNU `ld.bfd` single-pass thing.
  The fix lives in `Engine/Tools/BaseProject.sharpmake.cs` (`LibGroup` + `LibraryFiles`) and
  `Engine/Engine.sharpmake.cs` (`IsLinkerInvokedViaCompiler = true`). New static lib? add it to
  `conf.LibraryFiles` or as a dependency — don't hand-roll `--start-group`.
- **`error while loading shared libraries: libfoo.so.N`** → the lib is in `buildInputs` but missing
  from the runtime list. Add its `pkgs.*` to the `makeLibraryPath` block in `flake.nix` (~line 91),
  re-enter `nix develop`, verify with `ldd ./.build/Editor_Debug/Havana | grep 'not found'`.
- **Shell suddenly wants to download things** → you (or a tool) probably touched the flake/lock, or
  GC ran. You pinned `.nix-devshell-gcroot` pre-flight; re-enter via that profile if needed.
- **Read the source.** It's all local. `grep -rn`, the `.natvis`, and your own TODO comments are the
  oracle now.

---

## 🏠 When You're Back Online

- [ ] `git push` the Engine submodule, then the main repo (submodule pointer).
- [ ] `nix flake update` only if you actually want newer pkgs (re-test the build after).
- [ ] If you queued questions for me, this is when to ask. Leave yourself a `### Ask Claude:` list
      at the bottom of this file as you go.

---

### Ask Claude (queue questions here while offline)
- I must be out of date, I have no idea why my setup with my dotnet stuff isn't working. unless I messed something up, but my last sync was a week ago.
- claude satellite texting via twitter as a middleman. if you can still tweet via text, make two different accounts, one for the server, and one for the client where the phone is conneted. make them both follow eachother and just have them reply via twitter and use the service to make claude requests.
- take it easy black tide as a song for drumsmith
  - sleepers saosin