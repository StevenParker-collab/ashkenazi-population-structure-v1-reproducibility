# Reproducibility Contract

This package is organized so a skeptical reviewer can trace manuscript claims to files.

## Contract

1. No manuscript result should rely on an undocumented file, missing script, or untraceable manual statement.
2. Global25 and AADR are separate input data types and are not merged at the input level.
3. Global25 coefficients are constrained coordinate-space similarity weights, not ancestry percentages.
4. AADR PCA, FST, and ADMIXTURE are descriptive genotype-panel analyses, not formal demographic models.
5. No qpAdm or qpWave result is inferred from ADMIXTURE, PCA, FST, or Global25.
6. If raw data cannot be redistributed in GitHub because of size or licensing, the repository must state this and give a rebuild path.
7. Every table, figure, and headline number must be present in a source table, derived table, raw output, method note, or manifest.

## Review checklist

- Run `python scripts/verify_peer_review_repository.py`.
- Confirm `MANIFEST.csv` and `SHA256SUMS.txt` exist and cover all package files.
- Confirm no broken `ashkenazi-population-structure-v1-reprod` URL remains.
- Confirm the manuscript PDF is present.
- Confirm Global25 Experiments 1-15 files are present.
- Confirm AADR Stages 01-08 scripts/manifests/results are present.
- Confirm large raw genotype binaries are excluded intentionally and documented.
