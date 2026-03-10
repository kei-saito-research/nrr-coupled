#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${1:-/tmp/nrr-coupled_repro_results}"

cd "$ROOT"
python3 repro/coupled_state_sim.py --outdir "$OUT_DIR"
