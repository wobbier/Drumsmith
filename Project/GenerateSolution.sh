#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd -- "$project_root"
exec "$project_root/Engine/Tools/GenerateProject.sh" --compile-commands "$@"
