# Ashkenazi Population Structure Reassessed - Peer-Review Reproducibility Repository

This repository folder is the reproducibility package for the peer-review manuscript:

`manuscript/Ashkenazi_Population_Structure_Reassessed_Peer_Review_Manuscript.pdf`

## Core thesis

The manuscript tests whether the familiar description of Ashkenazi Jews as genetically intermediate between Europe and the Levant is stable once Italian Jewish and central Mediterranean comparators are included directly. The central claim is not that Levant-related continuity is absent. The claim is that an overstated or false genetic-intermediacy framing can be produced when Ashkenazi affinity to Italian Jewish, Southern Italian, Sicilian, Maltese, Aegean, and broader central Mediterranean populations is under-modeled or omitted, allowing Northern Italian/Northern European and Levantine proxies to bracket missing central Mediterranean space.

## Repository rule for peer review

Every manuscript claim should trace to at least one of these evidence classes:

- a source file or external data release note;
- a run script, method note, or exact calculator setting;
- a raw output table;
- a derived table or figure;
- a log, QC record, manifest, or checksum;
- an explicit limitation or data-availability statement.

## Correct repository URL

Use this URL for the original Version 1 repository, not shortened or truncated links:

https://github.com/StevenParker-collab/ashkenazi-population-structure-v1-reproducibility/tree/main/Ashkenazi_Population_Structure_Reassessed_V1_repository

## Main folders

- `manuscript/` - final peer-review manuscript PDF.
- `source_preprints/` - source PDFs used to build the peer-review synthesis.
- `global25_experiments/` - Global25 Experiments 1-15, including source/target rows, raw outputs, grouped summaries, screenshots, scripts, and checksums.
- `aadr_genotype_stages_01_08/` - AADR-derived genotype workflow materials: scripts, manifests, QC records, PCA, FST, ADMIXTURE, synthesis tables, figures, logs, and formal-stats readiness notes.
- `descriptive_fst/` - retained descriptive web-platform FST comparison materials from V1, explicitly not primary evidence.
- `review_contract/` - claim traceability, runbook, data availability, limitations, and peer-review audit notes.
- `scripts/` - repository verification script.

## Reviewer quick start

```bash
python scripts/verify_peer_review_repository.py
```

Then read:

1. `review_contract/REPRODUCIBILITY_CONTRACT.md`
2. `review_contract/CLAIM_TRACEABILITY.md`
3. `review_contract/RUNBOOK.md`
4. `review_contract/DATA_AVAILABILITY.md`
5. `review_contract/LIMITATIONS_AND_MODEL_BOUNDARIES.md`

## Boundary conditions

This repository does not claim a completed qpAdm or qpWave result. ADMIXTURE components, PCA distances, FST values, and Global25 coefficients are descriptive outputs and are not final historical source-proportion estimates. Raw multi-gigabyte genotype binaries are not duplicated in the GitHub package; the rebuild path from AADR v66.p1 is documented in the runbook and AADR stage files.
