# NRR-Coupled Reproducibility Steps (v1)

## Scope
This reproducibility note covers the cp definition and falsifiable evaluation harness in:
- `manuscript/current/paper6-nrr-coupled-v1.tex`
- `spec/nrr-coupled_spec_v1.md`
- `repro/coupled_state_sim.py`

## Environment
- Python: 3.10+
- LaTeX: `pdflatex`
- No external Python package is required.

## 1) Run synthetic paired evaluation
From repository root:

```bash
cd /Users/saitokei/Documents/New\ project/nrr-coupled
python3 repro/coupled_state_sim.py \
  --seeds 30 \
  --n 6 \
  --turns 60 \
  --alpha 0.08 \
  --beta 0.6 \
  --output repro/repro_summary.json
```

Expected artifact:
- `repro/repro_summary.json`

Interpretation:
- `summary.D-dependent.u_diff_cp_minus_base` corresponds to Success-1.
- `summary.D-independent.u_diff_cp_minus_base` corresponds to Success-2.
- `summary.D-dependent.osc_rate_cp` corresponds to Success-3.
- `contract.overall_pass` is true only when all pre-registered criteria pass.

## 2) Build manuscript PDF

```bash
cd /Users/saitokei/Documents/New\ project/nrr-coupled/manuscript/current
pdflatex -interaction=nonstopmode paper6-nrr-coupled-v1.tex
pdflatex -interaction=nonstopmode paper6-nrr-coupled-v1.tex
```

Expected artifact:
- `manuscript/current/paper6-nrr-coupled-v1.pdf`

## 3) Guardrail alignment checks
- Uncoupled baseline definition is inherited from Transfer (not redefined in cp).
- cp adds only coupled propagation, complexity bounds, and falsifiable evaluation contract.
- LLM interface assumption remains fixed (`sigma/delta` selection unchanged).
- If interface mismatch occurs, mark `TRANSFER_PRINCIPLES_REEVAL_REQUIRED=true`.

## 4) Optional quick sanity loop

```bash
python3 repro/coupled_state_sim.py --seeds 10 --output /tmp/cp_quick.json
cat /tmp/cp_quick.json
```
