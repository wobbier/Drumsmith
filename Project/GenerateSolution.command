#!/usr/bin/env bash
# Generates Drumsmith.xcworkspace with Sharpmake.
# Uses the cross-platform Sharpmake DLL (Engine/Tools/Sharpmake) on any .NET 8+ runtime, so it
# works on Intel and Apple Silicon. The bundled Engine/Tools/Sharpmake/macOS build is arm64-only
# and too old for Engine.sharpmake.cs, so it is not used.
set -euo pipefail
cd "$(dirname "$0")"

sharpmake_dll="../Engine/Tools/Sharpmake/Sharpmake.Application.dll"

has_net8() {
    [ -x "$1" ] && "$1" --list-runtimes 2>/dev/null | grep -Eq '^Microsoft\.NETCore\.App ([8-9]|[1-9][0-9])\.'
}

dotnet_bin=""
for candidate in \
    "${DOTNET_ROOT:+$DOTNET_ROOT/dotnet}" \
    "$HOME/.dotnet-8/dotnet" \
    "$HOME/.dotnet/dotnet" \
    "$(command -v dotnet 2>/dev/null || true)" \
    "/usr/local/share/dotnet/dotnet" \
    "/opt/homebrew/share/dotnet/dotnet"; do
    if [ -n "$candidate" ] && has_net8 "$candidate"; then
        dotnet_bin="$candidate"
        break
    fi
done

if [ -z "$dotnet_bin" ]; then
    echo "error: no .NET 8+ runtime found (Sharpmake needs one)." >&2
    echo "Install one user-locally (no sudo):" >&2
    echo "  curl -sSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh" >&2
    echo "  bash /tmp/dotnet-install.sh --channel 8.0 --runtime dotnet --install-dir ~/.dotnet-8" >&2
    exit 1
fi

echo "Using $dotnet_bin"
export DOTNET_ROOT="$(dirname "$dotnet_bin")"
exec "$dotnet_bin" "$sharpmake_dll" "/sources('../Game.sharpmake.cs')"
