# Methods and Reproduction Protocol

## Analysis levels

Experiment 1 uses seven prehistoric sources to test the Natufian argument under a fixed source panel. Experiments 2–7 use modern population references to test historical population-level explanations. Prehistoric components and modern populations are not mixed in one competition panel.

## Expanded Experiment 1 selection rule

The seven source coordinates are unchanged across every target. The target block includes:

- `Italki_Jew_(n=9)` and ten named regional Ashkenazi averages;
- every row beginning `Italian_Calabria:`, `Sicilian_East:`, or `Sicilian_West:`;
- every row beginning `Italian_Campania:` or `Maltese:`;
- every row beginning `Greek_Crete:`, `Greek_Crete_Chania:`, `Greek_Crete_Heraklion:`, or `Greek_Crete_Lasithi:`;
- every row beginning `Greek_Dodecanese:`, `Greek_Dodecanese_Rhodes:`, or `Greek_Kos:`.

No row inside a declared prefix was removed based on its result. The 196 targets are stored in the same order in the experiment input and raw TSV. The pooled Ashkenazi target is a separate matched run and is documented under `results/context/`.

## Calculator settings

- Cycles: 0.25X
- Add distance column: No
- Print zeroes: No
- Fast mode: No
- Aggregate: Yes

Because zeroes are not printed in screenshots, an absent source means only that the optimizer displayed no nonzero coefficient in that run. It is not proof of zero historical ancestry.

## Reproduction

1. Select a numbered file under `experiments/`.
2. Paste coordinate rows under `SOURCES` into the Source field.
3. Paste coordinate rows under `TARGETS` into the Target field.
4. Confirm the settings above and run the model.
5. Export the complete table without renaming target or source labels.
6. Store CSV or TSV under `results/raw/` and document any supplemental run under `results/context/`.
7. Preserve a readable screenshot when the output fits on screen. For the 196-row Experiment 1 run, publish the derived range table and retain the complete row-level TSV.
8. Run the derivation and validation scripts.

## Descriptive summaries

The regional means in `01_natufian_regional_summary.csv` are unweighted arithmetic means of the displayed individual coefficients in each complete label-defined cohort. They are not sample-size-weighted population estimates. The final calculator `Average` row across all 196 targets is not used because the target counts are highly unequal, including 111 Cretans.

Minimums, maximums, and range widths are descriptive values from the submitted target rows. No confidence interval, standard error, bootstrap, or formal hypothesis test is supplied. Accordingly, the documentation uses “substantial observed variation,” not “statistically significant,” unless an actual statistical test is added later.

## Matched comparisons

- Experiments 2 and 3 test redistribution after Northern/Eastern European sources are removed.
- Experiments 2 and 4 test Northern Italian proxy behavior after Calabrian and Sicilian sources are omitted.
- Experiments 2 and 5 test substitution after Italki Jews are removed.
- Experiment 6 reverses the target and models Italki Jews.
- Experiment 7 applies one external panel to ten regional Ashkenazi targets.

## Interpretation limits

- Global25 mixture coefficients are source-panel dependent.
- Correlated sources can divide or absorb the same ancestry direction.
- Natufian is not a Judean ancestry meter, and EHG is not a medieval Northern European population.
- A direct distance is not a mixture coefficient.
- A descriptive coefficient difference does not establish different origins or a specific causal admixture mechanism.
- Several population averages have small sample sizes.
