# Ashkenazi Population Structure Reassessed - Version 1 reproducibility repository

This repository accompanies:

Steven Parker. Ashkenazi Population Structure Reassessed: Reference-Panel Sensitivity and the Europe-Levant Cline.

It is a clean Version 1 package. It contains the corrected manuscript, a supplementary appendix, the full retained Global25 Experiments 1-15 archive, the descriptive FST records retained as secondary evidence, validation scripts, provenance notes, and fresh integrity manifests.

No Version 4 manuscript, Version 4 DOI metadata, or obsolete qpAdm analysis is included.

## Repository contents

- `manuscript/`: corrected Version 1 manuscript in DOCX and PDF.
- `supplementary/`: Supplementary Appendix and machine-readable Tables S1-S2.
- `global25_experiments/`: source and target coordinate rows where retained, calculator setups, raw outputs, grouped summaries, screenshots, figures, provenance documentation, and validation scripts for Experiments 1-15.
- `descriptive_fst/`: the limited web-platform FST audit trail used only for Supplementary Tables S1-S2.
- `DATA_AVAILABILITY.md`: exact data and software availability statement.
- `REPOSITORY_MAP.md`: reviewer-oriented file map.
- `VALIDATION_REPORT.md`: checks run and known limitations.
- `MANIFEST.csv` and `SHA256SUMS.txt`: fresh repository inventory and integrity hashes.
- `verify_repository.py`: repository-wide integrity and analysis validation.

## Start here

1. Read `manuscript/Ashkenazi_Population_Structure_Reassessed_V1.pdf`.
2. Read `supplementary/Supplementary_Appendix.pdf`.
3. Read `global25_experiments/README.md` and `global25_experiments/REPRODUCIBILITY_STATUS.md`.
4. Run `python3 verify_repository.py` from the repository root.

## Analysis scope

The primary quantitative contribution is a linked set of fifteen Global25 coordinate-space experiments. The experiments test reference-panel sensitivity through full competition panels, matched omissions, reciprocal Italki targets, regional replication, prehistoric controls, ancient Levant positive controls, and a full twenty-five-dimensional vector diagnostic.

The Global25 runs were recorded from Thierry Kerneur's ExploreYourDNA Atlantic Bronze Age calculator using the settings documented in the manuscript and experiment files. Displayed coefficients are constrained, source-panel-dependent similarity weights. They are not literal historical ancestry percentages.

The FST material was obtained through the IllustrativeDNA Admix Lab web interface using Human Origins v62.0. It is retained only as a descriptive comparison in Supplementary Tables S1-S2. The underlying genotype files and complete web-platform filtering pipeline are not distributed, so the FST material is not presented as an independently auditable command-line analysis.

## Scripts and code

Python scripts were used to assemble linked input panels, check coordinate dimensions and table structure, verify calculations, reproduce the Experiment 14 geometry diagnostic, validate the descriptive FST tables, and verify file integrity. No new compiled program or standalone software package was developed for the study.

## Known completeness limitation

The source handoff did not contain separate target-coordinate files for every ancient target in Experiments 8 and 9. Their raw output tables, findings, sources, and original screenshots are retained. The missing target coordinate rows were not inferred or fabricated. The exact status of each experiment is documented in `global25_experiments/REPRODUCIBILITY_STATUS.md`.
