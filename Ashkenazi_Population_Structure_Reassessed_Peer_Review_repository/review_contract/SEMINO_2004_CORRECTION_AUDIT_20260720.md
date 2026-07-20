# Semino 2004 Correction Audit - 2026-07-20

This note records the correction made to Table 13 of the peer-review manuscript after checking the manuscript table against Semino et al. (2004), Tables 1 and 2.

## Correction Summary

The previous manuscript table used one sample-size column and mixed values from Semino's separate Hg E and Hg J tables. The corrected manuscript now reports separate `E n` and `J n` columns.

| Population | E n | J n | E-M78 | E-M123 | J1-M267 | J2-M172 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Ashkenazi Jews | 77 | 82 | 5.2 | 11.7 | 14.6 | 23.2 |
| Apulia | 86 | 86 | 11.6 | 2.3 | 2.3 | 29.1 |
| Calabria 1 | 80 | 57 | 16.3 | 2.5 | 1.8 | 22.8 |
| Cosenza Albanian community | 68 | 45 | 5.9 | 13.2 | 0.0 | 20.0 |
| Sicily | 55 | 42 | 12.7 | 3.6 | 7.1 | 16.7 |

## Specific Fixes

- Ashkenazi E-M78 corrected from `7.8` to `5.2`.
- Ashkenazi J1-M267 corrected from `3.9` to `14.6`.
- Ashkenazi J denominator corrected from `77` to `82`; the E denominator remains `77`.
- Southern Italian regional E and J values were corrected to preserve Semino's separate Hg E and Hg J denominators.
- The Table 13 caption now states that E and J sample sizes are reported separately because the Semino tables use different denominators.

## Verification

- Rebuilt manuscript extraction confirms the corrected Table 13 values.
- Rebuilt manuscript text contains no remaining `7.8` or `3.9` Semino-table values.
- Page 13 was rendered and visually checked after rebuilding.
