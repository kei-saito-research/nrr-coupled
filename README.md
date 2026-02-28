# NRR-Coupled (cp): Dependency-Consistency Evaluation for Coupled State Updates

NRR-Coupled (cp) is a client-side extension for dependent-candidate state updates under a fixed LLM interface `(\sigma/\delta, target)`.  
The repository includes manuscript, specification, simulation code, and reproducibility artifacts.

Part of the Non-Resolution Reasoning (NRR) research program.  
Program Map (series hub): https://github.com/kei-saito-research/nrr-core/blob/main/PROGRAM_MAP.md

NRR is not an anti-LLM framework.  
NRR does not replace standard LLM use.  
NRR optimizes when to commit and when to defer, under explicit conditions.

## Quick links
- manuscript (current): `manuscript/current/paper6-nrr-coupled-v16.tex`
- specification: `spec/nrr-coupled_spec.md`
- simulation: `repro/coupled_state_sim.py`
- reproducibility guide: `reproducibility.md`

## Repository structure

```text
nrr-coupled/
|-- README.md
|-- LICENSE
|-- requirements.txt
|-- reproducibility.md
|-- manuscript/
|   `-- current/
|       |-- paper6-nrr-coupled-v16.tex
|       `-- paper6-nrr-coupled-v16.pdf
|-- spec/
|   `-- nrr-coupled_spec.md
`-- repro/
    |-- README.md
    |-- coupled_state_sim.py
    `-- results/
        |-- cp_consistency_aggregate.csv
        |-- cp_consistency_independent_check.csv
        |-- cp_consistency_pairwise.csv
        |-- cp_consistency_per_turn.csv
        |-- cp_consistency_report.json
        `-- cp_consistency_summary.csv
```

## Reproduction

```bash
cd <nrr-coupled-root>
python3 repro/coupled_state_sim.py --outdir repro/results
cd manuscript/current
tectonic -X compile paper6-nrr-coupled-v16.tex
```

## License

CC BY 4.0. See `LICENSE`.

## Contact

Kei Saito  
Independent Researcher, Japan  
ORCID: https://orcid.org/0009-0006-4715-9176  
Email: kei.saito.research@gmail.com
