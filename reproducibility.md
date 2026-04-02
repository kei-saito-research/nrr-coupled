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
  - output: `/tmp/nrr-coupled_current_build/paper6-nrr-coupled-v21.pdf`
- Verify that `manuscript/current/` contains only the latest `.tex` / `.pdf` pair:
  - `bash scripts/verify_active_review_surface.sh`
- Verify the current review-package checksum manifest:
  - `bash scripts/verify_current_package.sh`

## Current review package

- Main TeX: `manuscript/current/paper6-nrr-coupled-v21.tex`
- Current PDF snapshot: `manuscript/current/paper6-nrr-coupled-v21.pdf`
- Active review-surface checksum manifest: `manuscript/checksums_active_review_surface_sha256.txt`
- Current package checksum manifest: `manuscript/checksums_current_package_sha256.txt`

## Checksum policy

- `manuscript/checksums_active_review_surface_sha256.txt` covers the latest
  `.tex` / `.pdf` pair in `manuscript/current/`.
- `manuscript/checksums_current_package_sha256.txt` covers the current review
  package entrypoints, the latest manuscript pair, `spec/nrr-coupled_spec.md`,
  `repro/README.md`, `repro/coupled_state_sim.py`, and the bundled result artifacts.
- Coverage excludes generated temp outputs outside the tracked current package.

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
| Current manuscript build | `bash scripts/build_current_manuscript.sh` | `/tmp/nrr-coupled_current_build/paper6-nrr-coupled-v21.pdf` |
| Active review-surface verification | `bash scripts/verify_active_review_surface.sh` | stdout verification for `manuscript/checksums_active_review_surface_sha256.txt` |
| Current package checksum verification | `bash scripts/verify_current_package.sh` | stdout verification for `manuscript/checksums_current_package_sha256.txt` |
| Primary consistency rerun | `bash scripts/run_repro_check.sh` | `/tmp/nrr-coupled_repro_results/` |
| Spec snapshot | N/A (tracked artifact) | `spec/nrr-coupled_spec.md` |
| Offline reproduction script | N/A (tracked artifact) | `repro/coupled_state_sim.py` |
| Bundled result artifacts | N/A (tracked artifact) | `repro/results/cp_consistency_*.csv`, `repro/results/cp_consistency_report.json` |

## Known limitations

- In D-independent, `A_eval=0`, so edge-opportunity count is zero by construction.
- For independent-condition substantive check, use `cp_consistency_independent_check.csv`.
