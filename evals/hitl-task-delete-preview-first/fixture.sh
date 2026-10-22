#!/usr/bin/env bash
set -euo pipefail
FIX="$(cd "$(dirname "$0")/../_fixtures" && pwd)"
"$FIX/install-runtime.sh"
