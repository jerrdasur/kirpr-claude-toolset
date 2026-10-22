#!/usr/bin/env bash
set -euo pipefail
FIX="$(cd "$(dirname "$0")/../_fixtures" && pwd)"
"$FIX/require-git.sh"
"$FIX/install-runtime.sh"
g() { git -c user.name=eval -c user.email=eval@example.invalid "$@"; }
for svc in svc-a svc-b; do
    mkdir -p "$svc"
    ( cd "$svc" && g init -q -b main && printf 'module %s\n\ngo 1.24\n' "$svc" > go.mod && g add . && g commit -q -m "SAS-1 init" )
done
