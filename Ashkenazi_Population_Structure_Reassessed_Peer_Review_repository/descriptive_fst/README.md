# Descriptive FST audit trail

This directory contains only the FST material retained as a descriptive secondary comparison in the Version 1 manuscript and Supplementary Appendix. The obsolete qpAdm material from an earlier manuscript version is not included.

## Original environment

- Platform: IllustrativeDNA Admix Lab web interface
- Dataset: Human Origins v62.0
- Target: `Jew_Ashkenazi.HO`
- Setting: `Adjust Pseudohaploids = NO`

## Contents

- `inputs/`: exact target and comparator labels.
- `models/`: retained FST comparison and calibration specifications.
- `raw_outputs/`: copied web-platform output.
- `figures/`: screenshot of the original web output.
- `tables/`: machine-readable Supplementary Tables S1-S2.
- `scripts/validate_fst_tables.py`: checks tables against specifications and copied output.

## Interpretation limits

The underlying Human Origins genotype files and complete web-platform filtering pipeline were not available for independent audit and are not redistributed. These outputs are not treated as primary evidence, formal demographic estimates, or a command-line replication. They provide only descriptive distance context.

Run `python3 scripts/validate_fst_tables.py` from this directory or run the repository-wide `python3 verify_repository.py`.
