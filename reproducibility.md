# Reproducibility

This repository reproduces the current cp manuscript and result artifacts.

## Manuscript
- `manuscript/current/paper6-nrr-coupled-v19.tex`
- `manuscript/current/paper6-nrr-coupled-v19.pdf`
- `manuscript/current/checksums_sha256.txt`

## Spec and Repro
- `spec/nrr-coupled_spec.md`
- `repro/coupled_state_sim.py`
- `repro/results/cp_consistency_*.csv`
- `repro/results/cp_consistency_report.json`

## Run

```bash
cd <nrr-coupled-root>
bash scripts/run_repro_check.sh
```

Default temp output:
- `/tmp/nrr-coupled_repro_results/`

## Build PDF

```bash
cd <nrr-coupled-root>
bash scripts/build_current_manuscript.sh
```

Default temp output:
- `/tmp/nrr-coupled_current_build/paper6-nrr-coupled-v19.pdf`

## Integrity
- Verify current manuscript artifacts with `bash scripts/verify_current_package.sh`.

## Notes
- In D-independent, `A_eval=0`, so edge-opportunity count is zero by construction.
- For independent-condition substantive check, use `cp_consistency_independent_check.csv`.
