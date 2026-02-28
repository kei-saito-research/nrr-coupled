# NRR-Coupled v3 Reproducibility (Robust Simulation)

## Scope
This v3 protocol reproduces:
- `manuscript/current/paper6-nrr-coupled-v3.tex`
- `spec/nrr-coupled_spec_v3.md`
- `repro/coupled_state_sim.py`

Main policy:
- No API experiment in main evaluation.
- Robustness is evaluated across multiple random operator streams.

## Environment
- Python 3.10+
- TeX engine: `tectonic` (or `pdflatex` if available)
- No external Python package required

## 1) Run robust simulation

```bash
cd /Users/saitokei/Documents/New\ project/nrr-coupled
python3 repro/coupled_state_sim.py --outdir repro/results
```

Default settings:
- turns: `12`
- streams per pattern: `15`
- patterns: `P1-n4`, `P2-n5`, `P3-n6`
- beta levels: `0.1,0.3,0.5`
- hidden true coupling: `beta_true=0.5`

## 2) Output files
- `repro/results/cp_v3_per_turn.csv`
- `repro/results/cp_v3_summary.csv`
- `repro/results/cp_v3_pairwise.csv`
- `repro/results/cp_v3_aggregate.csv`
- `repro/results/cp_v3_independent_check.csv`
- `repro/results/cp_v3_report.json`

`cp_v3_aggregate.csv` reports robustness statistics (`mean/sd/min/max`) over all streams.

## 3) Contract check
`cp_v3_report.json` contains pass/fail flags:
- `success_dep_tau_gain_beta_0_3`
- `success_dep_u_gain_beta_0_3`
- `success_mismatch_penalty_beta_0_3`
- `success_independent_non_degrade_beta_0_3`
- `all_indep_equivalence_pass`

## 4) Build v3 PDF

```bash
cd /Users/saitokei/Documents/New\ project/nrr-coupled/manuscript/current
tectonic -X compile paper6-nrr-coupled-v3.tex
```

Expected output:
- `manuscript/current/paper6-nrr-coupled-v3.pdf`

## 5) Notes
- Transfer/Principles files are not edited by cp workflow.
- Claims are conditional and tied to reported conditions.
