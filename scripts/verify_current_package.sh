#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CURRENT_DIR="$ROOT/manuscript/current"

cd "$CURRENT_DIR"
shasum -a 256 -c checksums_sha256.txt
