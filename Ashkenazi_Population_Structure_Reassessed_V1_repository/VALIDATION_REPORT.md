# Validation report

Validation date: 2026-07-17

Result: all repository-wide integrity and supplied analysis validators passed.

## Package assembly

- The corrected 15-page Version 1 manuscript DOCX and PDF were included under clean filenames.
- The complete retained `global25_experiments/` directory was copied into the package.
- Earlier Version 4 manuscript and DOI metadata were excluded.
- The earlier qpAdm analysis was excluded because the Version 1 manuscript states that it was removed from the evidentiary framework.
- The descriptive FST records required for Supplementary Tables S1-S2 were retained in a separate, clearly limited directory.
- A Supplementary Appendix was generated directly from the retained FST CSV tables without changing their values.
- Fresh repository-level inventory and SHA-256 files were generated.

## Automated checks

The repository-wide verifier checks:

- required file presence;
- absence of embedded `.git` files, obsolete Version 4 manuscript, and obsolete `qpadm_fst/` directory;
- SHA-256 correctness and complete checksum coverage;
- manifest paths, file sizes, and hashes;
- Global25 coordinate dimensions, raw-output structure, coefficient totals, declared average distances, and cross-experiment source-panel relationships;
- Experiments 1-7 input/result alignment, grouped summaries, derived tables, and internal checksums;
- Experiment 14 twenty-five-dimensional vector geometry, weighted displacement values, reconstruction residual, direct distances, and PCA summary; and
- Supplementary Tables S1-S2 against retained FST specifications and copied raw output.

## Declared limitation

Separate ancient target-coordinate files were not present for every target in Experiments 8 and 9. The available raw outputs, source files, findings, and screenshots are retained, and no missing target coordinate was inferred or fabricated. The package is therefore transparent about this limitation rather than claiming complete rerunnability for those two experiment inputs.
