# NRR-Coupled (cp): Dependency-Consistency Evaluation for Coupled State Updates

NRR-Coupled (cp) is a client-side extension for dependent-candidate state updates under a fixed LLM interface `(\sigma/\delta, target)`.  
The repository includes manuscript, specification, simulation code, and reproducibility artifacts.

Part of the Non-Resolution Reasoning (NRR) research program. In the current spine, this repository is the dependency-aware propagation layer in the first-principles/implementation chain, carried forward from the standalone `reuse` line (historically labeled under the local `Transfer` filename family) and upstream of Projection and `NRR-Patterns`.  

## NRR Series Hub (Start here)

For the cross-paper map and current series links, start here:
- [NRR Series Hub](https://github.com/kei-saito-research/nrr-series-hub)

NRR is not an anti-LLM framework.  
NRR does not replace standard LLM use.  
NRR optimizes when to commit and when to defer, under explicit conditions.
Series numbering policy: `paper3` is permanently skipped and never reused.

## Quick links
- arXiv: pending (pre-submission; no public URL yet)
- manuscript (current): `manuscript/current/paper6-nrr-coupled-v21.tex`
- active review-surface manifest: `manuscript/checksums_active_review_surface_sha256.txt`
- current package manifest: `manuscript/checksums_current_package_sha256.txt`
- specification: `spec/nrr-coupled_spec.md`
- simulation: `repro/coupled_state_sim.py`
- reproducibility guide: `reproducibility.md`

## DOI
- [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18814806.svg)](https://doi.org/10.5281/zenodo.18814806)

## Repository structure

```text
nrr-coupled/
|-- README.md
|-- LICENSE
|-- requirements.txt
|-- reproducibility.md
|-- manuscript/
|   |-- checksums_active_review_surface_sha256.txt
|   |-- checksums_current_package_sha256.txt
|   `-- current/
|       |-- paper6-nrr-coupled-v21.tex
|       |-- paper6-nrr-coupled-v21.pdf
|       `-- ...
|-- spec/
|   `-- nrr-coupled_spec.md
|-- scripts/
|   |-- README.md
|   |-- build_current_manuscript.sh
|   |-- run_repro_check.sh
|   |-- verify_active_review_surface.sh
|   `-- verify_current_package.sh
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
bash scripts/run_repro_check.sh
bash scripts/build_current_manuscript.sh
```

Stable review-package entrypoints:
- `bash scripts/run_repro_check.sh`
- `bash scripts/build_current_manuscript.sh`
- `bash scripts/verify_active_review_surface.sh`
- `bash scripts/verify_current_package.sh`

## License

CC BY 4.0. See `LICENSE`.

## Contact

Kei Saito  
Independent Researcher, Japan  
ORCID: https://orcid.org/0009-0006-4715-9176  
Email: kei.saito.research@gmail.com
