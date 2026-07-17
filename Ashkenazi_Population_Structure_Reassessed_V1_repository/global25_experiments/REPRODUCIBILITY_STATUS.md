# Experiment reproducibility status

This file distinguishes supplied evidence from linked panels assembled from exact coordinate rows elsewhere in the same source package.

| Experiment | Inputs | Outputs and evidence | Status |
|---|---|---|---|
| 1 | Supplied paste-ready seven-source panel and 196 targets; pooled Ashkenazi matched target retained separately | Full raw TSV, contextual comparison, derived summaries, figures, and checks | Complete supplied package |
| 2-7 | Supplied paste-ready source and target panels | Raw tables, summaries, figures, and checks | Complete supplied package |
| 8 | Seven sources recoverable exactly from Experiment 1 | Raw TSV, detailed findings, and original screenshot | Ancient and modern target-coordinate file was not separately supplied |
| 9 | Five modern sources recoverable exactly from Experiment 14 | Raw TSV, findings, and original screenshot | Ancient target-coordinate file was not separately supplied |
| 10 | Experiment 14 explicitly states that it uses the identical Experiment 10 panel; pooled target is retained in Experiment 2 | Raw TSV, findings, comparisons, and original screenshot | Complete linked panel assembled from retained rows |
| 11 | Experiment 10 panel with only `Italki_Jew_(n=9)` omitted; pooled target retained in Experiment 2 | Setup, raw TSV, findings, checksum, and screenshot | Complete linked panel assembled from retained rows |
| 12 | Declared omission of Italki, Southern Italian, Sicilian, Maltese, and Aegean sources from Experiment 10; pooled target retained in Experiment 2 | Setup, raw TSV, findings, checksum, and screenshot | Complete linked panel assembled from retained rows |
| 13 | Experiment 10 panel without Italki as a source; Italki target retained in Experiment 1/2 | Setup, raw TSV, grouped summary, findings, checksum, and screenshot | Complete linked panel assembled from retained rows |
| 14 | Supplied source and ten-target coordinate files | Setup, raw TSV, grouped summary, persistence table, findings, checksum, screenshot, and full-dimensional Ashkenazi Germany vector diagnostic | Complete supplied package with reproducible geometry analysis |
| 15 | Supplied source and three-target coordinate files | Setup, raw TSV, grouped summary, persistence table, findings, checksum, and screenshot | Complete supplied package |

The assembly script never searches for or infers missing ancient target coordinates. It copies exact rows already distributed inside this repository and applies only the omissions explicitly declared in the setup files.

The Experiment 14 geometry analysis reads the supplied source, target, and raw-result files directly. Its cosine similarity, weighted vector magnitudes, combined displacement, reconstruction residual, direct distances, and PCA summary are retained in `experiments_08_15/analysis/`.
