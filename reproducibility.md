# Reproducibility (NRR-Coupled)

## Scope

This repository bundles the current coupled manuscript package together with the
offline reproduction script and result artifacts used for the public cp line.

## Stable review-package commands

- Reproduce the primary consistency check to temp output:
  - `bash scripts/run_repro_check.sh`
  - output root: `/tmp/nrr-coupled_repro_results/`
- Build the current manuscript to temp output:
  - `bash scripts/build_current_manuscript.sh`
  - output: `/tmp/nrr-coupled_current_build/paper6-nrr-coupled-v19.pdf`
- Verify the current review-package checksum manifest:
  - `bash scripts/verify_current_package.sh`

## Current review package

- Main TeX: `manuscript/current/paper6-nrr-coupled-v19.tex`
- Current PDF snapshot: `manuscript/current/paper6-nrr-coupled-v19.pdf`
- Checksum manifest: `manuscript/current/checksums_sha256.txt`

## Checksum policy

- `manuscript/current/checksums_sha256.txt` covers the tracked files that define the
  current review package for the latest manuscript line in `manuscript/current/`.
- Coverage includes the current main `.tex` file and the committed current `.pdf`.
- Coverage excludes `checksums_sha256.txt` itself, older manuscript versions that may
  remain in `manuscript/current/` for local working continuity, and repo-specific
  artifacts outside `manuscript/current/` unless a separate manifest is provided.

## Environment

- Python: project local environment compatible with `repro/coupled_state_sim.py`
- Main assets: manuscript package, `spec/`, and `repro/results/`

## Fixed protocol settings

- Primary offline entrypoint: `repro/coupled_state_sim.py`
- Stable wrapper: `bash scripts/run_repro_check.sh`
- Output mode: local temp directory rather than in-place overwrite of tracked review artifacts

## Artifact map

| Artifact | Command | Output |
|---|---|---|
| Current manuscript build | `bash scripts/build_current_manuscript.sh` | `/tmp/nrr-coupled_current_build/paper6-nrr-coupled-v19.pdf` |
| Current package checksum verification | `bash scripts/verify_current_package.sh` | stdout verification for `manuscript/current/checksums_sha256.txt` |
| Primary consistency rerun | `bash scripts/run_repro_check.sh` | `/tmp/nrr-coupled_repro_results/` |
| Spec snapshot | N/A (tracked artifact) | `spec/nrr-coupled_spec.md` |
| Offline reproduction script | N/A (tracked artifact) | `repro/coupled_state_sim.py` |
| Bundled result artifacts | N/A (tracked artifact) | `repro/results/cp_consistency_*.csv`, `repro/results/cp_consistency_report.json` |

## Known limitations

- In D-independent, `A_eval=0`, so edge-opportunity count is zero by construction.
- For independent-condition substantive check, use `cp_consistency_independent_check.csv`.
