# Data Provenance

## Coordinate sources

Two supplied coordinate collections are used at different levels:

1. The seven named ancient sources, Italki Jewish average, pooled and regional Ashkenazi averages, and the modern population averages used in Experiments 2–7 were retained from the Moriopoulos Collection 2026 averages/no-simulations files supplied for the project.
2. The individual Calabrian, eastern Sicilian, western Sicilian, Campanian, Maltese, Cretan, Rhodian, Dodecanese, and Kos rows in expanded Experiment 1 were copied verbatim from the supplied scaled individual file `Global25_PCA_modern_scaled(4).txt` using the exact label-prefix inclusion rule recorded in `METHODS.md`.

The full upstream collections are not redistributed here. The repository contains only the rows needed to reproduce the declared experiments. The supplied individual source file had SHA-256:

`9bee845e62a9d59437a55409f9a435a99a8b2079624f5c8783c92af8c4fdb4d7`

## Transformations and selection

No coordinate transformation or new ancestry composite was applied. Specifically:

- no Southern Italian, Northern Italian, Northern/Eastern European, or central Mediterranean coordinate was newly averaged;
- no simulated population row was added;
- labels and all 25 dimensions were preserved;
- individual cohorts were included exhaustively by declared label prefix;
- population-average and individual coordinates are explicitly distinguished in the documentation.

The regional values in `results/derived/` are summaries of calculator coefficients, not new target or source coordinates.

## Result provenance

`results/raw/01_controlled_prehistoric_expanded_results.tsv` is the supplied full calculator export containing 196 substantive targets and a final Average row. Its SHA-256 before repository packaging was:

`6e1a0de3c4f93986693bb3930853499736be8b84c21e03e338cff6538a737387`

The pooled Ashkenazi matched result was supplied separately and is stored under `results/context/`; it is not inserted into the 196-row raw export. The Reddit screenshot transcription is also contextual and is not represented as a new controlled run.

The Reddit screenshot uses the same fourteen visible Calabrian and Sicilian target labels as the controlled comparison, but it does not disclose exact source coordinates. Its transcription is used only to compare displayed outputs and document the panel mismatch.

Experiment 7 was previously checked against the corrected screenshot uploaded at 09:29:46 on 2026-07-13. Other raw outputs remain mapped in `MANIFEST.csv`.

## Versioning

Never silently replace a coordinate or result row after publication. Record the change in `CHANGELOG.md`, preserve the new raw export, regenerate derived tables, refresh `SHA256SUMS`, and run the repository validator.
