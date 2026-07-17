# Expanded Natufian Range and Method Analysis

This note reproduces the arithmetic used by the revised article. It keeps four different things separate: the Reddit screenshot transcription, the controlled 196-target raw export, the separate pooled Ashkenazi matched run, and the derived summaries.

## Why the two original screenshots are not controlled

The Reddit Italian-Jewish screenshot displays six broad sources, while its Southern Italian screenshot adds WHG as a seventh source. The aliases do not identify exact coordinate vectors, sample membership, averaging rules, or scaled status. Because Global25 coefficients are conditional on the competing source geometry, the Natufian columns from the two screenshots are not measurements made with one fixed instrument.

The controlled run instead gives every target the same seven explicit sources: Barcin Anatolian Neolithic, Kotias CHG, Karelia EHG, Loschbour WHG, Ganj Dareh Iran Neolithic, Natufian, and Taforalt Iberomaurusian.

## Same fourteen targets, different method

The screenshot's fourteen Calabrian and Sicilian rows average 7.0429% Natufian and span 4.6%–9.8%. The identical target names average 8.3857% in the controlled replication and span 6.2%–12.2%.

```text
Mean shift = 8.3857 - 7.0429 = 1.3429 percentage points
```

Twelve rows are higher under the declared controlled panel, two are unchanged, and none is lower. This supports a method/panel critique. It does not establish that the poster deleted individuals inside the three labels shown; all fourteen displayed individuals are present in the controlled rerun.

## Complete Southern Italian distribution

Campania, Calabria, eastern Sicily, and western Sicily together provide forty individuals.

```text
Southern Italian low = 2.4%
Southern Italian high = 12.2%
Internal range = 12.2 - 2.4 = 9.8 points
Italki gap above the high end = 16.2 - 12.2 = 4.0 points
Range-to-gap ratio = 9.8 / 4.0 = 2.45
```

The internal Southern Italian variation is therefore 2.45 times the high-Southern-Italian-to-Italki gap. This does not prove identical origins. It shows that the selected Natufian rule is incapable of disproving a common ancestry foundation without first fragmenting known Southern Italian groups.

Campania averages 7.1308%, so adding it lowers the restricted Calabria/Sicily mean. At the same time, Campania widens the Southern Italian range to 2.4%–12.2%. A mean summarizes the selected rows; it is not the maximum allowed by a region and cannot substitute for the full distribution.

## Larger Greco-Roman central Mediterranean comparison

Malta spans 4.0%–16.4%, Crete 0.0%–13.4%, and Dodecanese/Rhodes/Kos 0.4%–12.0%. The ten regional Ashkenazi averages span 11.4%–15.0% with a mean of 13.24%. Pooled Ashkenazi Jews receive 12.8%, and Italki Jews receive 16.2%.

The means differ, but the distributions overlap. Natufian in this restricted prehistoric model does not produce the categorical Jewish-versus-Southern-European separation asserted by the Reddit argument.

## Northern-European dilution boundary

The post did not identify a historical Northern European source, give its Natufian coefficient, estimate an admixture fraction, or model an Ashkenazi target. Under the deliberately extreme assumption that the unspecified second source has 0% Natufian:

```text
12.8 = (1 - m) × 16.2
m = 1 - (12.8 / 16.2) = 0.209877...
```

The lower-bound dilution fraction is approximately 21.0%. This is not a historical ancestry estimate. It is a boundary calculation showing that the claimed causal mechanism requires an explicit source and mixture fraction. Any source with a nonzero coefficient below 12.8% in this same panel would require a larger fraction.

## Reproduce the tables

Run:

```bash
python3 scripts/derive_natufian_math.py
python3 scripts/derive_natufian_math.py --check
```

The generated tables are:

- `results/derived/01_natufian_regional_summary.csv`
- `results/derived/01_natufian_method_comparison.csv`
- `results/derived/01_natufian_math_summary.csv`
- `results/derived/01_natufian_comparison_points.csv`
