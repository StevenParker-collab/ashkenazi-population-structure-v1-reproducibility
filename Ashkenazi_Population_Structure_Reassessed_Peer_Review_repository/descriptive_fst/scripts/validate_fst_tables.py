#!/usr/bin/env python3
"""Validate the retained descriptive FST tables against specifications and copied raw output."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []


def read_dicts(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


specs = read_dicts(ROOT / "models" / "fst_comparisons.tsv", "\t")
table = read_dicts(ROOT / "tables" / "table_s1_fst_results.csv")
by_population = {row["population"]: row for row in table}

if len(specs) != 12 or len(table) != 12:
    errors.append(f"Expected 12 FST comparison rows; found specs={len(specs)}, table={len(table)}")

for spec in specs:
    row = by_population.get(spec["population_2"])
    if row is None:
        errors.append(f"Table S1 is missing {spec['population_2']}")
        continue
    if abs(float(spec["fst_distance"]) - float(row["fst_distance"])) > 1e-10:
        errors.append(f"FST mismatch for {spec['population_2']}")
    if abs(float(spec["standard_error"]) - float(row["standard_error"])) > 1e-10:
        errors.append(f"standard-error mismatch for {spec['population_2']}")

# Check rank is sequential and distances are nondecreasing.
ranks = [int(row["rank"]) for row in table]
if ranks != list(range(1, len(table) + 1)):
    errors.append("Table S1 ranks are not sequential from 1")
distances = [float(row["fst_distance"]) for row in table]
if distances != sorted(distances):
    errors.append("Table S1 is not sorted by FST distance")

cal_specs = read_dicts(ROOT / "models" / "fst_calibration_comparisons.tsv", "\t")
cal_table = read_dicts(ROOT / "tables" / "table_s2_fst_calibration.csv")
cal_keys = {(r["population_1"], r["population_2"], r["fst_distance"]) for r in cal_table}
for spec in cal_specs:
    key = (spec["population_1"], spec["population_2"], spec["fst_distance"])
    if key not in cal_keys:
        errors.append(f"Table S2 mismatch for {spec['population_1']} vs {spec['population_2']}")

raw = (ROOT / "raw_outputs" / "fst_jew_ashkenazi_raw_output.txt").read_text(encoding="utf-8")
for row in table:
    # Require population and exact displayed distance to occur in copied raw output.
    if row["population"] not in raw:
        errors.append(f"Raw output is missing population {row['population']}")
    if row["fst_distance"] not in raw:
        errors.append(f"Raw output is missing distance {row['fst_distance']}")

if errors:
    print("Descriptive FST validation failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)

print("Descriptive FST validation passed.")
