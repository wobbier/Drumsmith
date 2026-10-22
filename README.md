# Drumsmith

Linux development
-----------------------

Install Nix and VS Code's C/C++ extension, initialize the engine submodules, and open this folder. F5 enters the engine-owned environment, generates build files, builds, and starts the debugger.

```bash
Engine/Tools/DevShell.sh
Engine/Tools/BuildProject.sh Havana editor_debug
Engine/Tools/NixEnv.sh ./.build/Editor_Debug/Havana
```

Drumsmith's Node and ALSA additions live in `devshell.nix`. The engine owns the shared package lock. See [the environment guide](Engine/Docs/Development-Environment.md).
