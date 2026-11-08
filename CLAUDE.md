# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Drumsmith is a drum rhythm game built on top of [MitchEngine](https://github.com/wobbier/MitchEngine) (a git submodule at `Engine/`). The engine is a C++20 ECS-based game engine targeting Windows, macOS, and Linux, with a visual editor called Havana.

## Game Documentation

Game-side systems are documented in `Docs/` (index: `Docs/README.md`) — architecture, gameplay/hit detection, songs/DLC, audio, MIDI input, UI, and the latency budget (`Docs/Latency-and-Responsiveness.md`). **For any game-side question, consult those docs first.** Opinions/priorities (gotchas catalog, responsiveness roadmap) live only in `Docs/State-of-the-Game.md`.

## Engine Documentation

Engine internals are documented in `Engine/Docs/` (index: `Engine/Docs/README.md`; Claude task routing: `Engine/CLAUDE.md`). **For any engine-internal question, consult those docs before this file** — the engine architecture sections below are summaries and may lag; `Engine/Docs/` is canonical and stamped against engine commits. Opinions/priorities live only in `Engine/Docs/State-of-the-Engine.md`.

## Platform Compatibility

All code changes must compile and run correctly on **Win64, macOS, and Linux**. UWP compatibility is also required but held to a looser standard — it should not be actively broken, but UWP-specific quirks are acceptable as long as the other three platforms are unaffected.

Use the `USING( ME_PLATFORM_* )` feature flags (see below) to guard any platform-specific code rather than raw `#ifdef` or `#if defined(...)`. Prefer writing platform-agnostic code first and only branching when a platform truly requires it.

## Build Commands (Linux)

```bash
# Build the Havana editor (default VSCode build task)
make -f Drumsmith.make Havana config=editor_debug -j$(nproc)

# Build the game executable
make -f Drumsmith.make Game_EntryPoint config=game_linux_debug -j$(nproc)

# Run the editor
./.build/Editor_Debug/Havana

# Run the game
./.build/Game_linux_Debug/Game_EntryPoint_x64
```

The Nix dev shell (`nix develop`) provides all required dependencies. Without Nix, the README lists the required X11/Vulkan packages for a manual `nix-shell -p ...` invocation.

### Solution / Project Generation

The Sharpmake generator scripts live in `Project/`: `GenerateSolution.bat` (Windows), `GenerateSolution.command` (macOS), and `GenerateSolution.sh` (Linux). Run the one for your platform to generate the Visual Studio solution / Xcode project / makefiles, then build in the IDE (or via `make` on Linux — see above). Also run `Engine/ThirdParty/GenerateSolutions.bat` once for third-party dependencies.

The generated build files (`Makefile`, `*.make`, `compile_commands.json`) are gitignored — like the generated `.sln`/`.vcxproj`/`.pbxproj` — and must never be committed. Runtime log/dump artifacts (`Engine.txt`, `fmod_log.txt`, `startup.json`) are also ignored.

## Architecture

### Entity-Component-Core (ECS) Pattern

The engine uses an ECS pattern where **Entities** hold **Components** (data) and **Cores** act as systems that process entities matching a component filter.

- `Engine/Source/ECS/Entity.h` — `AddComponent<T>()`, `GetComponent<T>()`, `HasComponent<T>()`
- `Engine/Source/ECS/Core.h` — `BaseCore` base class; implement `Update()`, `OnEntityAdded()`, `OnEntityRemoved()`
- `Engine/Source/Engine/World.h` — manages all entities and cores; `CreateEntity()`, `AddCore<T>()`, `CreateFromPrefab()`

Components are registered at compile time with `ME_REGISTER_COMPONENT(T)` and cores with `ME_REGISTER_CORE(T)`.

### Game Entry Point

Games inherit from the `Game` base class and are wired up with a macro:

```cpp
class MyGame : public Game {
    void OnInitialize() override;
    void OnStart() override;
    void OnUpdate(const UpdateContext&) override;
    void OnEnd() override;
};
ME_APPLICATION_MAIN(MyGame)
```

The game-specific code lives in `Game/Source/` and the executable entry point in `Game_EntryPoint/Source/main.cpp`.

### Major Subsystems

| Subsystem | Location | Backend |
|-----------|----------|---------|
| Rendering | `Engine/Modules/Moonlight/` + `Engine/Source/Cores/Rendering/` | BGFX |
| Physics | `Engine/Source/Cores/PhysicsCore.cpp` | Bullet3D |
| Audio | `Engine/Source/Cores/AudioCore.cpp` | FMOD (optional) |
| UI | `Engine/Source/Cores/UI/` | RmlUi (HTML/CSS-like documents, no JS; see `Docs/UI-and-Menus.md`) |
| Scripting | `Engine/Source/Scripting/` + `Engine/Modules/ScriptCore/` | .NET 8 / C# (experimental) |
| Editor | `Engine/Modules/Havana/` | ImGui (+ RmlUi game view composite) |
| Input | `Engine/Source/Engine/Input.h` | SDL2 |

The `Engine` class (singleton-like, `Engine/Source/Engine/Engine.h`) owns the main loop and provides access to the `World`, renderer, input, and job system.

### Rendering Pipeline

`RenderCore` (`Engine/Source/Cores/Rendering/RenderCore.cpp`) runs a **parallel mesh job** over visible entities and fills a POD `MeshCommand` (`Engine/Modules/Moonlight/Source/RenderCommands.h`) per mesh. The render-loop hot fields are precomputed in that parallel job so the serial submit loop in `BGFXRenderer` (`Renderer.cpp`) does **no virtual calls**: `BatchKey`, `VertexBufferIdx`, `IndexBufferIdx`, `IsTransparent`, `SupportsInstancing`.

**Automatic GPU instancing:** opaque meshes whose material sets `SupportsInstancing = true` (opt-in; see `DiffuseMaterial`) are grouped into `InstanceBatch`es keyed by geometry (vertex/index buffer) + `Material::GetInstanceBatchKey()`. The batch key is a hash of GPU state (program idx, texture idx, render state, `DiffuseColor`, `Tiling`) — **not the material pointer**, because each mesh gets a unique material instance. Each batch is drawn once via `RenderMeshInstanced` (chunked BGFX instance-data buffer, 64-byte/mat4 stride), bypassing the 65536-entry `setTransform` matrix cache. Transparent meshes still submit individually for correct ordering. Shared bind logic lives in `BindMeshDrawState`. See also the `instancing-render-path` memory.

**Transform dirty flags:** `Transform` (`Engine/Source/Components/Transform.cpp`) tracks `IsLocalToWorldDirty` / `IsWorldToLocalDirty` separately. `SetDirty` propagates downward to children eagerly but early-outs when already dirty; matrix recompute is lazy and cached. A static (unmutated) scene therefore costs near-nothing per frame.

### Serialization

Components serialize to/from JSON by overriding:

```cpp
virtual void OnSerialize(json& outJson) final;
virtual void OnDeserialize(const json& inJson) final;
```

Level/scene files are JSON (`.lvl`), prefabs are JSON stored in `Assets/`.

### Key Macros

- `ME_HARDSTUCK(T)` — disables copy/move (use on engine/core types)
- `ME_REGISTER_COMPONENT(T)` / `ME_REGISTER_CORE(T)` — compile-time ECS registration
- `ME_APPLICATION_MAIN(GameClass)` — defines `main()` and wires up the game class

### Feature Flags (`Dementia.h`)

Dementia provides a compile-time feature flag system. Each feature is defined as either `IN_USE` (`1`) or `NOT_IN_USE` (`0`), and `USING(feature)` expands to `(feature)`; composites use `USE_IF(expr)` = `((expr) ? 1 : 0)`. (See `Engine/Docs/Architecture.md` for the current flag table.)

```cpp
#if USING( ME_EDITOR )
    // editor-only code
#endif

#if USING( ME_PLATFORM_LINUX )
    // Linux-only code
#endif
```

Composite features use `USE_IF(expr)` which takes a boolean expression of `USING()` calls:

```cpp
// defined as: USE_IF( USING( ME_EDITOR ) || USING( ME_TOOLS ) )
#if USING( ME_IMGUI )
    // available in editor, tools, and profiling builds
#endif
```

**Available feature flags:**

| Flag | Meaning |
|------|---------|
| `ME_EDITOR` | Havana editor is included |
| `ME_PLATFORM_WIN64` / `ME_PLATFORM_MACOS` / `ME_PLATFORM_LINUX` | Target platform |
| `ME_PLATFORM_WINDOWS` | Win64 or UWP |
| `ME_DEBUG` / `ME_RELEASE` / `ME_RETAIL` | Build configuration |
| `ME_HEADLESS` | No window / no rendering |
| `ME_PHYSICS_3D` | Bullet3D physics enabled |
| `ME_DOTNET` / `ME_SCRIPTING` | C# scripting via .NET 8 (`ME_SCRIPTING` is `USE_IF(USING(ME_DOTNET))`) |
| `ME_RMLUI` | RmlUi HTML UI (always on) |
| `ME_FMOD` | FMOD audio (disabled in headless) |
| `ME_OPTICK` / `ME_PROFILING` | Profiling support |
| `ME_IMGUI` | ImGui (editor, tools, or profiling builds) |
| `ME_TOOLS` / `ME_GAME_TOOLS` | Non-editor tool builds |

Never use plain `#ifdef ME_EDITOR` — always use `#if USING( ME_EDITOR )` so the flag participates correctly in composite `USE_IF` expressions.

### .NET Scripting Architecture

The scripting system migrated from Mono to **.NET 8** via the `hostfxr`/`nethost` hosting API. The feature flag chain is: `DEFINE_ME_DOTNET` (preprocessor define) → `ME_DOTNET` (Dementia flag) → `ME_SCRIPTING` (composite flag).

**C++ side** (`Engine/Source/Scripting/`):

- `ScriptHost` — thin RAII wrapper around `hostfxr`. Loads the .NET runtime from the system-installed `hostfxr.dll`, initializes it with `ScriptCore.runtimeconfig.json` (targets `net8.0`), and resolves `[UnmanagedCallersOnly]` function pointers via `LoadFunction()`.
- `ScriptEngine` — higher-level interface consumed by the rest of the engine. Calls into managed code through the function pointers loaded by `ScriptHost`. Public API: `Init()`, `CreateScript()`, `ScriptOnStart/Update/Destroy/EditorInspect()`, `GetFieldsJson/SetFieldsJson()`, `GetScriptCount/Name()`.
- `ScriptEngineAPI` (`Engine/Source/Scripting/Generated/ScriptEngineAPI.generated.h`) — plain C struct of function pointers passed from C++ to managed code at startup. Covers Log, GetTime, Entity, Transform, Camera, BasicUIView, ImGui, Input, and World operations.
- `BindingContext` (`Engine/Source/Scripting/Bindings/BindingContext.h`, `ScriptBindings` namespace) — per-domain component registry. Call `ScriptBindings::RegisterComponent<T>("Name")` to make a component available to scripts by name via `Entity_HasComponent`/`Entity_AddComponent`. Individual binding files live under `Bindings/Components/` and `Bindings/Systems/`.

**Managed side** (`Engine/Modules/ScriptCore/Source/`):

- `IGameScript` — interface all game scripts implement: `OnStart()`, `OnUpdate(float dt)`, `OnDestroy()`, `OnEditorInspect()`.
- `Engine.cs` (`EngineAPIBindings` struct + `Engine` static class) — mirrors `ScriptEngineAPI` on the C# side using `delegate* unmanaged<>` function pointers. Scripts call e.g. `Engine.Log(...)`, `Engine.Transform.GetTranslation(entity)`.
- `GameScriptALC` — collectible `AssemblyLoadContext` that isolates game script assemblies. Routes `ScriptCore` references back to the already-loaded assembly, resolves everything else via `AssemblyDependencyResolver`. Groundwork for future hot-reload.
- `ScriptRegistry` — scans a loaded assembly for all non-abstract `IGameScript` implementations and keeps them in a sorted list.
- `Inspector.cs` — reflection-based ImGui field drawer for script instances; respects `[HideInInspector]` attribute.

**Build config:**

- Windows: set `Globals.DOTNET_Win64_Dir` in `Game.sharpmake.cs` to the `runtimes/win-x64/native` directory inside the installed `Microsoft.NETCore.App.Host.win-x64` pack (e.g. `C:\Program Files\dotnet\packs\Microsoft.NETCore.App.Host.win-x64\8.0.27\runtimes\win-x64\native`). The build system adds that path as an include/library path and copies `nethost.dll` to the output directory.
- Linux: wired via `Globals.DOTNET_Linux_Dir` in `Engine/Tools/BaseProject.sharpmake.cs`; the Nix dev shell (`flake.nix`) exports `DOTNET_ROOT` and discovers `DOTNET_LINUX_NATIVE_DIR` from the installed SDK. (The `Globals.MONO_Linux_Dir` check is vestigial.)
- The `ScriptCore` C# project (`Engine/Modules/ScriptCore/ScriptCore.sharpmake.cs`) builds as a `DotNetClassLibrary` targeting `net8.0` with unsafe blocks enabled.

### Build Targets (Sharpmake / Make)

`Dementia` → `MitchEngine` → `Moonlight`, `ImGui`, `Havana`, `MitchGame` → `Game_EntryPoint`

`Dementia` is a core utility/reflection library that the engine depends on. All third-party libs live in `Engine/ThirdParty/`.

## Code Style

### Function Definitions in `.cpp` Files

Separate every function definition with **two blank lines**:

```cpp
void Foo::Bar()
{
    // ...
}


void Foo::Baz()
{
    // ...
}
```

## Optick Profiling

Captures are triggered at runtime with **F9** (toggle start/stop/save). `startup.opt` is saved automatically after the first 10 frames. Files land in the working directory.

### Parsing `.opt` files with Python

The format: 8-byte header + **miniz-compressed** body of chunk records.

```python
import struct, zlib

with open("capture.opt", "rb") as f: raw = f.read()
magic, ver, flags = struct.unpack_from("<IHH", raw, 0)
# magic == 0xB50FB50F, flags & 2 == IsMiniz
body = zlib.decompress(raw[8:]) if (flags & 2) else raw[8:]

# Chunks: [u32 proto_ver=26][u32 size][u16 type][u16 app=0xB50F][<size> bytes]
# type 0=FrameDescriptionBoard, 1=EventFrame, 3=NullFrame, 258=SummaryPack, 259=FramesPack
```

**FrameDescriptionBoard** layout (chunk type 0):
```
u32 boardNumber | u64 freq_hz | u64 origin | u32 precision
i64 timeSlice.start | i64 timeSlice.finish
u32 threadCount, per thread: [u64 tid][u32 pid][str name][i32 maxDepth][i32 priority][u32 mask]
u32 fiberCount, per fiber: [u64 id]
i32 forcedMainThread
u32 descCount, per EventDescription: [str name][str file][u32 line][u32 filter][u32 color][f32 budget][u8 flags]
```

Key type gotchas: `ProcessID = uint32` (not uint64). `FrameType::Type` serializes as `i32` (4 bytes, not 1).

**EventFrame** layout (chunk type 1):
```
ScopeHeader: [u32 boardNum][i32 threadNum][i32 fiberNum][i64 start][i64 finish][i32 frameType]
u32 catCount, per cat: [i64 start][i64 finish][u32 descIdx]
u32 evtCount, per evt: [i64 start][i64 finish][u32 descIdx]
```

Timestamps are raw CPU ticks; convert with `ticks * 1000.0 / freq_hz` for milliseconds. On Linux the freq is 1 GHz (nanosecond ticks).

**Strings** are `u32 length` + UTF-8 bytes (no null terminator).

### Findings from first Linux capture (2026-05-11)

- Baseline: p50=4ms, p95=5ms — engine idles at ~240fps with minimal scene
- Only 4 event descriptions registered (CPU/GPU/Render Frame + `EditorApp::OnUpdate`) — most engine systems have no `OPTICK_EVENT` marks yet
- One 172ms spike traced to `EditorApp::OnUpdate` — likely a first-frame asset load; root cause invisible without deeper marks

## TODO / Revisit

- **`EntityID::Value()` hardcoded masks** (`Engine/Source/ECS/EntityID.h`): the bit masks `0xFFFFULL` (counter) and `0x0000FFFFFFFFFFFFULL` (index) are hardcoded rather than derived from `MITCH_ENTITY_ID_COUNTER_BIT_COUNT` (16) / `MITCH_ENTITY_ID_INDEX_BIT_COUNT` (48). If those bit-count macros ever change, the masks silently drift out of sync. Replace with masks computed from the macros (e.g. `((1ULL << N) - 1)`).
