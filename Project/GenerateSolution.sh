#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

dotnet "../Engine/Tools/Sharpmake/Sharpmake.Application.dll" "/sources('../Game.sharpmake.cs')"

echo ""
echo "Generating compile_commands.json for CLion / clangd..."
bear --output ../compile_commands.json -- make -C .. -f Drumsmith.make Havana config=editor_debug -j$(nproc)
echo "Done. Open the project folder in CLion."
