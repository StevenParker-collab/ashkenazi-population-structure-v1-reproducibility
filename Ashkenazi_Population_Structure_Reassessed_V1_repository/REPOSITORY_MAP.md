# Repository map

## Manuscript

- `manuscript/Ashkenazi_Population_Structure_Reassessed_V1.docx`
- `manuscript/Ashkenazi_Population_Structure_Reassessed_V1.pdf`

## Supplementary appendix

- `supplementary/Supplementary_Appendix.docx`
- `supplementary/Supplementary_Appendix.pdf`
- `supplementary/tables/Table_S1_FST_results.csv`
- `supplementary/tables/Table_S2_FST_calibration.csv`

## Primary Global25 analysis

- `global25_experiments/README.md`: experiment design and calculator settings.
- `global25_experiments/REPRODUCIBILITY_STATUS.md`: per-experiment completeness.
- `global25_experiments/experiments_01_07/`: original seven-experiment package with inputs, outputs, figures, scripts, and internal checksums.
- `global25_experiments/experiments_08_15/`: Experiment 8-15 source/target files where retained, raw outputs, findings, screenshots, and grouped summaries.
- `global25_experiments/experiments_08_15/analysis/`: Experiment 14 Germany vector geometry and direct-distance diagnostic.
- `global25_experiments/scripts/`: linked-input assembly and suite validation.

## Descriptive FST records

- `descriptive_fst/README.md`: scope and limitations.
- `descriptive_fst/inputs/`: exact comparator labels.
- `descriptive_fst/models/`: retained comparison specifications.
- `descriptive_fst/raw_outputs/`: copied web-platform output.
- `descriptive_fst/figures/`: original web-output screenshot.
- `descriptive_fst/tables/`: machine-readable Supplementary Tables S1-S2.
- `descriptive_fst/scripts/validate_fst_tables.py`: structural cross-check.

## Repository validation

- `verify_repository.py`: runs integrity checks and all supplied validators.
- `scripts/build_manifest.py`: rebuilds `MANIFEST.csv` and `SHA256SUMS.txt`.
- `VALIDATION_REPORT.md`: validation status and declared limitations.
