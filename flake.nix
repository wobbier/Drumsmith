{
  description = "MitchEngine dev environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };
        dotnet = pkgs.dotnet-sdk_8;
      in
      {
        # ----------------------------------------------------------
        # MitchEngine Dev Shell
        #
        # - bgfx loads GL/EGL dynamically with dlopen()
        # - Mesa + libglvnd MUST be in LD_LIBRARY_PATH so bgfx finds
        #   64-bit libEGL.so.1 instead of Steam's 32-bit version.
        # - ALWAYS enter this shell with:  nix develop
        # ----------------------------------------------------------
        devShells.default = pkgs.mkShell {
          name = "mitchengine-devshell";

          buildInputs = with pkgs; [
            # Core build tools
            gcc
            gdb
            gnumake
            cmake
            pkg-config

            # SDL2 from Nix
            SDL2

            # GL/EGL libs
            mesa        # GL + EGL + DRI drivers
            libglvnd    # GL/Vulkan dispatch loader

            # Wayland (wl_egl_window_create for native Wayland + Vulkan)
            wayland

            dotnet

            # Vue HTML/JS UI
            nodejs_20
            python3

            # X11 dev headers (needed by SDL_syswm.h and XWayland support)
            xorg.libX11
            xorg.libXcursor
            xorg.libXext
            xorg.libXrandr
            xorg.libXinerama
            xorg.libXxf86vm
            xorg.libXfixes
            xorg.libxcb

            bzip2  # For decompressing .tar.bz2 files from bgfx releases
            alsa-lib
            curl
            # Optional Vulkan support for bgfx
            vulkan-loader

            # Required by Ultralight AppCore on Linux
            fontconfig

            # Ultralight (latest) links against the system GTK3 stack
            gtk3
            glib
            pango
            cairo
            atk
            gdk-pixbuf
            harfbuzz
          ];

          # Provide GL/EGL so bgfx's dlopen("libEGL.so.1") succeeds.
          # makeLibraryPath only adds each listed package's own lib dir
          # (not transitive deps), so every Ultralight/GTK dependency is
          # listed explicitly.
          LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
            pkgs.libglvnd
            pkgs.mesa
            pkgs.SDL2
            pkgs.vulkan-loader

            # Ultralight (latest) GTK3 runtime deps
            pkgs.gtk3
            pkgs.glib
            pkgs.pango
            pkgs.cairo
            pkgs.atk
            pkgs.gdk-pixbuf
            pkgs.harfbuzz
            pkgs.bzip2  # libbz2.so.1.0

            pkgs.alsa-lib
            pkgs.curl
          ];

          shellHook = ''
            export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$(pwd)/Engine/ThirdParty/Optick:$(pwd)/Engine/ThirdParty/fmod/api/core/lib/x86_64"
            export DOTNET_ROOT="${dotnet}/share/dotnet"

            _DOTNET_NATIVE=$(find ${dotnet}/share/dotnet/packs/Microsoft.NETCore.App.Host.linux-x64 -mindepth 3 -maxdepth 3 -name "native" -type d 2>/dev/null | head -1)
            if [ -n "$_DOTNET_NATIVE" ]; then
              export DOTNET_LINUX_NATIVE_DIR="$_DOTNET_NATIVE"
            fi
            unset _DOTNET_NATIVE

            echo "🍉 Shell Ready!"
            echo "  Build: make -f MitchGame.make Havana config=editor_debug"
            echo "  Run:   ./.build/Editor_Debug/Havana"
            echo "  UI:    (cd Game/ui && npm ci && npm run build)"
            echo "  Optional: SDL_VIDEODRIVER=wayland ..."
            echo ""
            echo "DOTNET_LINUX_NATIVE_DIR=$DOTNET_LINUX_NATIVE_DIR"
          '';
        };
      });
}
