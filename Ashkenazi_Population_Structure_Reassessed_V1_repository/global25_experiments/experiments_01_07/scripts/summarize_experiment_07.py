#!/usr/bin/env python3
"""Recompute and optionally verify the grouped Experiment 7 summary."""

from __future__ import annotations

import csv
import io
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw" / "07_regional_ashkenazi_full_modern_panel.csv"
DERIVED = ROOT / "results" / "derived" / "07_regional_grouped_summary.csv"

MEDITERRANEAN_AEGEAN = [
    "Greek_Crete_(n=10)",
    "Greek_Crete_Lasithi_(n=7)",
    "Greek_Dodecanese_Kos_(n=9)",
    "Greek_Dodecanese_Rhodes_(n=15)",
    "Italian_Sicily_(Sicilian)_(n=2)",
    "Italian_Sicily_Agrigento_(Sicilian)_(n=2)",
    "Italian_Sicily_Central_(Sicilian)_(n=2)",
    "Italian_Sicily_East_(Sicilian)_(n=1)",
    "Italian_Sicily_Palermo_(Sicilian)_(n=2)",
    "Italian_Sicily_Trapani_(Sicilian)_(n=7)",
    "Italki_Jew_(n=9)",
    "Maltese_(n=8)",
]

NORTHERN_EASTERN_EUROPE = [
    "Belarusian_(n=27)",
    "Russian_Smolensk_(n=15)",
    "Swedish_(n=114)",
    "Ukrainian_(n=25)",
]


def one_decimal(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def render() -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([
        "Target",
        "Distance",
        "Italki_Jew_(n=9)",
        "Mediterranean_Aegean_total",
        "Northern_Eastern_Europe_total",
    ])
    with RAW.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            mediterranean = sum(Decimal(row[name]) for name in MEDITERRANEAN_AEGEAN)
            northern_eastern = sum(Decimal(row[name]) for name in NORTHERN_EASTERN_EUROPE)
            writer.writerow([
                row["Target"],
                row["Distance"],
                row["Italki_Jew_(n=9)"],
                one_decimal(mediterranean),
                one_decimal(northern_eastern),
            ])
    return output.getvalue()


def main() -> int:
    generated = render()
    if "--check" in sys.argv:
        expected = DERIVED.read_text(encoding="utf-8")
        if generated != expected:
            print(f"Derived summary is out of date: {DERIVED}", file=sys.stderr)
            return 1
        print("Experiment 7 grouped summary matches the raw result.")
        return 0
    sys.stdout.write(generated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
