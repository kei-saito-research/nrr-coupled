# NRR-Coupled Reproducibility (Dependency-Consistency Protocol)

## Scope
This guide reproduces:
- `manuscript/paper6-nrr-coupled-v14.tex`
- `spec/nrr-coupled_spec.md`
- `repro/coupled_state_sim.py`

Key policy:
- No coupled-generated target references for scoring.
- Evaluate by dependency consistency and repair cost.

## Environment
- Python 3.10+
- TeX engine: `tectonic` (or `pdflatex`)
- No external Python package required

## 1) Run simulation

```bash
cd <nrr-coupled-root>
python3 repro/coupled_state_sim.py --outdir repro/results
```

Default settings:
- turns: `12`
- streams/pattern: `15`
- patterns: `P1-n4`, `P2-n5`, `P3-n6`
- beta levels: `0.1,0.3,0.5`
- seed base: `20260228`

## 2) Outputs
- `repro/results/cp_consistency_per_turn.csv`
- `repro/results/cp_consistency_summary.csv`
- `repro/results/cp_consistency_pairwise.csv`
- `repro/results/cp_consistency_aggregate.csv`
- `repro/results/cp_consistency_independent_check.csv`
- `repro/results/cp_consistency_report.json`

`cp_consistency_aggregate.csv` includes mean/sd/min/max over all streams.

## 3) Contract checks
See `cp_consistency_report.json` flags:
- `success_dep_violation_reduction_beta_0_3`
- `success_dep_repair_reduction_beta_0_3`
- `success_mismatch_penalty_beta_0_3`
- `success_independent_non_degrade_beta_0_3`
- `all_indep_equivalence_pass`

## 4) Build PDF

```bash
cd manuscript
tectonic -X compile paper6-nrr-coupled-v14.tex
```

Expected output:
- `manuscript/paper6-nrr-coupled-v14.pdf`

Interpretation notes:
- In `D-independent`, `A_eval=0` so violation opportunities are zero; use
  `cp_consistency_independent_check.csv` equality checks for substantive confirmation.
- Zero-movement under clipping saturation is conservatively counted as violation.
- Repair uses cap `max_repair_ops=30`; cap hits can understate mismatch degradation.

## 5) Note
Transfer/Principles are not edited in this cp workflow.
