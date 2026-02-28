# Reproducibility

This repository reproduces the current cp manuscript and result artifacts.

## Manuscript
- `manuscript/current/paper6-nrr-coupled-v16.tex`
- `manuscript/current/paper6-nrr-coupled-v16.pdf`

## Spec and Repro
- `spec/nrr-coupled_spec.md`
- `repro/coupled_state_sim.py`
- `repro/results/cp_consistency_*.csv`
- `repro/results/cp_consistency_report.json`

## Run

```bash
cd <nrr-coupled-root>
python3 repro/coupled_state_sim.py --outdir repro/results
```

## Build PDF

```bash
cd manuscript/current
tectonic -X compile paper6-nrr-coupled-v16.tex
```

## Notes
- In D-independent, `A_eval=0`, so edge-opportunity count is zero by construction.
- For independent-condition substantive check, use `cp_consistency_independent_check.csv`.
