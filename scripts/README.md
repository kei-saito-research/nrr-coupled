# Scripts

This directory contains the stable manuscript and reproduction wrappers for the
current NRR-Coupled repository surface.

## Stable entrypoints

- `build_current_manuscript.sh`
  - builds the latest manuscript in `manuscript/current/` to a temp output directory
- `run_repro_check.sh`
  - reruns the coupled consistency simulation to a temp output directory
- `verify_active_review_surface.sh`
  - verifies that `manuscript/current/` contains only the current `.tex` / `.pdf` pair and checks `manuscript/checksums_active_review_surface_sha256.txt`
- `verify_current_package.sh`
  - verifies the active review surface first and then checks `manuscript/checksums_current_package_sha256.txt`

These four entrypoints define the stable current-package interface.
