#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CURRENT_DIR="$ROOT/manuscript/current"
MAIN_TEX="$(find "$CURRENT_DIR" -maxdepth 1 -type f -name 'paper6-nrr-coupled-v*.tex' | sort -V | tail -n 1)"
OUT_DIR="${1:-/tmp/nrr-coupled_current_build}"

if [ -z "$MAIN_TEX" ]; then
  echo "No current manuscript TeX found in $CURRENT_DIR" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
cd "$CURRENT_DIR"
tectonic -X compile --outdir "$OUT_DIR" "$(basename "$MAIN_TEX")"
