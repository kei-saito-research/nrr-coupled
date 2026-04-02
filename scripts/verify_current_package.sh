#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MANIFEST="$ROOT/manuscript/checksums_current_package_sha256.txt"

bash "$ROOT/scripts/verify_active_review_surface.sh"

cd "$ROOT"
shasum -a 256 -c "$MANIFEST"
