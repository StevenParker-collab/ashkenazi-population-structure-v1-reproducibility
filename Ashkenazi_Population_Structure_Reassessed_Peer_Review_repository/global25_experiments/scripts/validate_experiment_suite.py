#!/usr/bin/env python3
"""Validate the distributed Global25 experiment suite."""

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LATE = ROOT / "experiments_08_15"
errors = []


def coordinate_labels(path):
    labels = []
    with path.open(encoding="utf-8") as handle:
        for number, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) != 26:
                errors.append(f"{path.name}:{number}: expected label plus 25 coordinates")
                continue
            try:
                [float(value) for value in parts[1:]]
            except ValueError:
                errors.append(f"{path.name}:{number}: nonnumeric coordinate")
            labels.append(parts[0])
    return labels


for path in sorted(LATE.glob("Experiment_*_Sources.csv")) + sorted(
    LATE.glob("Experiment_*_Targets.csv")
):
    coordinate_labels(path)


for path in sorted(LATE.glob("Experiment_*_Raw_Data.tsv")):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        header = next(reader)
        if len(header) < 3 or header[:2] != ["Target", "Distance"]:
            errors.append(f"{path.name}: unexpected header")
            continue
        for number, row in enumerate(reader, 2):
            if len(row) != len(header):
                errors.append(f"{path.name}:{number}: row width differs from header")
                continue
            try:
                distance = float(row[1])
                weights = [float(value) for value in row[2:]]
            except ValueError:
                errors.append(f"{path.name}:{number}: nonnumeric output value")
                continue
            if distance < 0:
                errors.append(f"{path.name}:{number}: negative distance")
            total = sum(weights)
            if abs(total - 100.0) > 0.2:
                errors.append(f"{path.name}:{number}: coefficients sum to {total:.3f}")


expected_distances = {
    10: 0.00819655,
    11: 0.00922012,
    12: 0.01206331,
    13: 0.00984550,
    14: 0.01041373,
    15: 0.01805080,
}
for experiment, expected in expected_distances.items():
    path = LATE / f"Experiment_{experiment}_Raw_Data.tsv"
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    average = next((row for row in rows if row["Target"] == "Average"), None)
    if average is None or abs(float(average["Distance"]) - expected) > 1e-10:
        errors.append(f"Experiment {experiment}: average distance mismatch")


full = coordinate_labels(LATE / "Experiment_10_Sources.csv")
regional = coordinate_labels(LATE / "Experiment_14_Sources.csv")
no_italki = coordinate_labels(LATE / "Experiment_11_Sources.csv")
reciprocal = coordinate_labels(LATE / "Experiment_13_Sources.csv")
if full != regional:
    errors.append("Experiment 10 source panel does not match Experiment 14")
if no_italki != [label for label in full if label != "Italki_Jew_(n=9)"]:
    errors.append("Experiment 11 is not the declared Italki omission panel")
if reciprocal != no_italki:
    errors.append("Experiment 13 reciprocal panel does not match the declared panel")


if errors:
    print("Experiment-suite validation failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)

print("Experiment-suite validation passed.")
