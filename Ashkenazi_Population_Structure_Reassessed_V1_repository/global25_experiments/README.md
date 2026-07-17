# Global25 reference-panel sensitivity and validation suite

This directory contains the linked Experiments 1-15 used in the Version 1 manuscript. The suite tests how model allocation and fit change when reference populations are added, omitted, or reversed and whether the same framework recovers known regional continuity in ancient Levant controls.

## Design

| Experiments | Design | Primary comparison |
|---|---|---|
| 1 and 8 | Fixed prehistoric panels | Component contrasts under shared sources |
| 2 and 10 | Full modern panels | Competition with Italki and central Mediterranean sources present |
| 3, 5, 11, and 12 | Omission tests | Redistribution and fit deterioration after source removal |
| 4, 6, and 13 | Direct and reciprocal controls | Proxy behavior and Italki target reversal |
| 7 and 14 | Regional replications | Stability across ten regional Ashkenazi averages |
| 9 and 15 | Ancient positive controls | Recovery of southern-Levantine continuity |

## Directory layout

- `experiments_01_07/`: the original seven-experiment research package, limited here to analytical documentation, inputs, outputs, figures, and scripts.
- `experiments_08_15/`: the Experiment 8-15 handoff files, with linked input panels assembled for Experiments 10-13 from exact coordinate rows already preserved elsewhere in the package.
- `experiments_08_15/analysis/`: the full-dimensional Experiment 14 Ashkenazi Germany vector diagnostic, result tables, direct distances, and illustrative PCA figure.
- `scripts/assemble_linked_inputs.py`: reconstructs only explicitly linked panels from the package's own retained coordinate rows.
- `scripts/validate_experiment_suite.py`: checks coordinate dimensions, row totals, declared distances, and cross-experiment relationships.
- `REPRODUCIBILITY_STATUS.md`: exact completeness and provenance status for each experiment.

## Calculator settings

The recorded ExploreYourDNA Atlantic Bronze Age calculator settings are:

- cycles: 0.25X
- add distance column: no
- print zeroes: no
- fast mode: no
- aggregate: yes

## Interpretation limits

Displayed coefficients are constrained similarity weights conditional on the source panel. They are not literal genealogical or historical ancestry percentages. A zero coefficient means that another source represented the relevant direction more efficiently in that panel; it does not prove historical absence.

The Experiment 14 geometry diagnostic uses all twenty-five Global25 dimensions. It shows that the retained Levantine-continuity and Northern/Eastern European blocks act as strongly opposing, nearly equal weighted displacements around the coefficient-weighted central Mediterranean centroid. PCA is used only to visualize that geometry.

Prehistoric and modern panels are interpreted separately. `Russia_Karelia_Mesolithic_(EHG)_(n=15)` is an experimental prehistoric reference label and must not be translated into recent ethnic Russian ancestry. Lombardy is reported separately and is never classified as Southern Italian.
