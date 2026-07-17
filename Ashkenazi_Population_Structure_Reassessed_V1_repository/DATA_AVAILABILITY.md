# Data and software availability

No newly sequenced genotype data are reported. This repository contains the corrected Version 1 manuscript, supplementary materials, retained coordinate rows, source-panel definitions, calculator settings, copied raw outputs, grouped summaries, comparison tables, figures, screenshots, provenance notes, validation scripts, and integrity records.

## Global25 Experiments 1-15

The primary analysis uses scaled Global25 population-average coordinates and the ExploreYourDNA Atlantic Bronze Age calculator. Recorded settings are cycles 0.25X, distance column off, printed zeroes off, fast mode off, and aggregate mode on, except where an experiment-specific setup file records only settings visible in the original screenshot.

The package contains the rows needed for the declared experiments where they were retained in the source handoff. Experiments 10-13 use exact linked rows assembled from coordinate files already present in the package; `global25_experiments/scripts/assemble_linked_inputs.py` performs only those documented linkages and omissions. Experiment 14 contains a reproducible full-dimensional geometry diagnostic.

For Experiments 8 and 9, separate target-coordinate files for every ancient target were not present in the source handoff. Their raw outputs, source files, findings, and screenshots are retained without alteration. No missing target row was reconstructed from an unverified external source.

The upstream full Global25 coordinate collections are not redistributed. The package documents the retained-row provenance and upstream-file checksum where available.

## Descriptive FST material

The FST outputs were obtained through the IllustrativeDNA Admix Lab web interface using Human Origins v62.0 with `Adjust Pseudohaploids = NO`. The exact population labels, copied web output, screenshot, tables, and a structural validation script are included in `descriptive_fst/`.

The underlying Human Origins genotype files and full web-platform filtering pipeline are not distributed. The FST outputs are therefore descriptive secondary comparisons and are not claimed as a local command-line replication, a formal demographic model, or primary evidence.

## Scripts

Python scripts were used to:

- validate coordinate dimensions, result-table structure, coefficient totals, declared distances, and source-panel relationships;
- assemble only explicitly linked source and target rows already present in the package;
- reproduce and verify the Experiment 14 twenty-five-dimensional vector diagnostic;
- derive or check documented summaries for Experiments 1 and 7;
- validate Supplementary Tables S1-S2 against the retained FST specifications and copied raw output; and
- build and verify repository manifests and SHA-256 checksums.

No new compiled software or original standalone program was developed. The scripts are analysis and validation utilities.

## Integrity

Run `python3 verify_repository.py` from the repository root. `MANIFEST.csv` inventories every payload file other than the manifest and checksum list. `SHA256SUMS.txt` hashes every distributed file other than itself.
