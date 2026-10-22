#!/usr/bin/env bash
set -euo pipefail
FIX="$(cd "$(dirname "$0")/../_fixtures" && pwd)"
"$FIX/require-git.sh"
"$FIX/install-runtime.sh"
g() { git -c user.name=eval -c user.email=eval@example.invalid "$@"; }
mkdir -p exportsrv && cd exportsrv
g init -q -b main
cat > go.mod <<'GO'
module exportsrv

go 1.24
GO
cat > export.go <<'GO'
package exportsrv

import (
	"net/http"
	"time"
)

// Client fetches report rows from the reports service.
var Client = &http.Client{Timeout: 30 * time.Second}

// ExportCSV streams all rows of a report into one CSV response.
func ExportCSV(w http.ResponseWriter, r *http.Request) {
	resp, err := Client.Get("http://reports/rows?report=" + r.URL.Query().Get("id"))
	if err != nil {
		http.Error(w, "export failed", http.StatusGatewayTimeout)
		return
	}
	defer resp.Body.Close()
	w.Header().Set("Content-Type", "text/csv")
}
GO
g add . && g commit -q -m "SAS-1 export service"
