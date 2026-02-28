# NRR-Coupled v4 Reproducibility (Dependency-Consistency Protocol)

## Scope
This v4 protocol reproduces:
- `manuscript/current/paper6-nrr-coupled-v4.tex`
- `spec/nrr-coupled_spec_v4.md`
- `repro/coupled_state_sim.py`

v4 key policy:
- No coupled-generated target references for scoring.
- Evaluate by dependency consistency and repair cost.

## Environment
- Python 3.10+
- TeX engine: `tectonic` (or `pdflatex`)
- No external Python package required

## 1) Run v4 simulation

```bash
cd /Users/saitokei/Documents/New\ project/nrr-coupled
python3 repro/coupled_state_sim.py --outdir repro/results
```

Default settings:
- turns: `12`
- streams/pattern: `15`
- patterns: `P1-n4`, `P2-n5`, `P3-n6`
- beta levels: `0.1,0.3,0.5`
- seed base: `20260228`

## 2) Outputs
- `repro/results/cp_v4_per_turn.csv`
- `repro/results/cp_v4_summary.csv`
- `repro/results/cp_v4_pairwise.csv`
- `repro/results/cp_v4_aggregate.csv`
- `repro/results/cp_v4_independent_check.csv`
- `repro/results/cp_v4_report.json`

`cp_v4_aggregate.csv` includes mean/sd/min/max over all streams.

## 3) Contract checks
See `cp_v4_report.json` flags:
- `success_dep_violation_reduction_beta_0_3`
- `success_dep_repair_reduction_beta_0_3`
- `success_mismatch_penalty_beta_0_3`
- `success_independent_non_degrade_beta_0_3`
- `all_indep_equivalence_pass`

## 4) Build v4 PDF

```bash
cd /Users/saitokei/Documents/New\ project/nrr-coupled/manuscript/current
tectonic -X compile paper6-nrr-coupled-v4.tex
```

Expected output:
- `manuscript/current/paper6-nrr-coupled-v4.pdf`

## 5) Note
Transfer/Principles are not edited in this cp workflow.
