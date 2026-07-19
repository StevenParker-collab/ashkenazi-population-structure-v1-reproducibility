# Reviewer Runbook

## 1. Verify repository integrity

```bash
python scripts/verify_peer_review_repository.py
```

Expected outcome: required files are present, checksum files exist, no broken truncated GitHub URL is found, and intentionally excluded large genotype binaries are not present in the GitHub package.

## 2. Global25 coordinate-space suite

Start with:

- `global25_experiments/README.md`
- `global25_experiments/REPRODUCIBILITY_STATUS.md`
- `global25_experiments/scripts/validate_experiment_suite.py`
- `global25_experiments/experiments_08_15/Experiment_10_11_12_Comparison.tsv`
- `global25_experiments/experiments_08_15/Experiment_10_11_12_Distance_Comparison.tsv`
- `global25_experiments/experiments_08_15/Experiment_14_Regional_Grouped_Summary.tsv`
- `global25_experiments/experiments_08_15/Experiment_15_Grouped_Continuity_Summary.tsv`

The Global25 calculator outputs are archived as raw and derived files. Rerunning the web calculator itself depends on the external calculator environment, but the declared source/target rows, settings, screenshots, outputs, and validation scripts are included.

## 3. AADR Stages 01-08 genotype workflow

Start with:

- `aadr_genotype_stages_01_08/ashkenazi_project_complete_handoff.txt`
- `aadr_genotype_stages_01_08/complete_handoff_metadata/`
- `aadr_genotype_stages_01_08/manifests/`
- `aadr_genotype_stages_01_08/results/pca/`
- `aadr_genotype_stages_01_08/results/fst/`
- `aadr_genotype_stages_01_08/results/admixture/`
- `aadr_genotype_stages_01_08/results/synthesis/`
- `aadr_genotype_stages_01_08/results/formal_stats_readiness/`

The GitHub package excludes multi-gigabyte genotype binaries and raw ADMIXTURE matrix directories. To rebuild from raw data, obtain the documented AADR v66.p1-compatible files and follow the stage scripts in order:

1. Stage 01: source-data acquisition/conversion/normalization.
2. Stage 02: sample labels, harmonization, primary and strict-pass manifests.
3. Stage 03: QC and panel-integrity audit.
4. Stage 04: PLINK/matched SNP/LD-pruned data construction.
5. Stage 05: PCA and centroid-distance analysis.
6. Stage 06: Hudson FST and validation against PLINK Weir-Cockerham FST.
7. Stage 07: ADMIXTURE K=2-12, five replicates per K/panel, 10-fold CV.
8. Stage 08: integrated PCA/FST/ADMIXTURE comparator ranking.

## 4. Manuscript checks

Use `review_contract/CLAIM_TRACEABILITY.csv` to connect each headline claim to files. The manuscript PDF is a reading artifact; the repository tables and scripts are the audit artifacts.
