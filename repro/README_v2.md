# NRR-Coupled v2 Reproducibility (Simulation-First)

## Scope
This v2 protocol reproduces the cp simulation evaluation and manuscript numbers in:
- `manuscript/current/paper6-nrr-coupled-v2.tex`
- `spec/nrr-coupled_spec_v2.md`
- `repro/coupled_state_sim.py`

Main policy:
- No API experiment in main evaluation.
- Same pre-defined operator stream is applied to uncoupled/coupled clients.

## Environment
- Python 3.10+
- TeX engine: `tectonic` (or `pdflatex` if available)
- No external Python package is required.

## 1) Run simulation

```bash
cd /Users/saitokei/Documents/New\ project/nrr-coupled
python3 repro/coupled_state_sim.py --outdir repro/results
```

This generates:
- `repro/results/cp_v2_per_turn.csv`
- `repro/results/cp_v2_summary.csv`
- `repro/results/cp_v2_pairwise.csv`
- `repro/results/cp_v2_aggregate.csv`
- `repro/results/cp_v2_independent_check.csv`
- `repro/results/cp_v2_report.json`

## 2) Key checks
- Coupled gain levels are fixed: `beta = 0.1, 0.3, 0.5`.
- D-independent equivalence is checked with tolerance `1e-12`.
- Contract flags are in `cp_v2_report.json`:
  - `success_1_dep_gain_beta_0_3`
  - `success_2_indep_non_degrade_beta_0_3`
  - `success_3_dep_osc_rate_beta_0_3`
  - `all_indep_equivalence_pass`

## 3) Build v2 manuscript PDF

```bash
cd /Users/saitokei/Documents/New\ project/nrr-coupled/manuscript/current
tectonic -X compile paper6-nrr-coupled-v2.tex
```

Expected output:
- `manuscript/current/paper6-nrr-coupled-v2.pdf`

## 4) Guardrail-aligned interpretation
- Transfer/Principles files are not edited in cp work.
- cp claims are conditional, falsifiable, and bounded to tested conditions.
- Failure criteria are explicit and reportable.
