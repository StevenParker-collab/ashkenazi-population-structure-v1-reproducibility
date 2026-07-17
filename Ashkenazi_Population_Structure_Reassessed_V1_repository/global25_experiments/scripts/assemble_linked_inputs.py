#!/usr/bin/env python3
"""Assemble explicitly linked Global25 panels from retained coordinate rows.

This script does not infer or download coordinates. It copies exact 25-dimensional
rows already present in the repository and applies only omissions declared in the
Experiment 10-13 setup files.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EARLY = ROOT / "experiments_01_07"
LATE = ROOT / "experiments_08_15"


def coordinate_rows(paths):
    rows = {}
    for path in paths:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            parts = line.split(",")
            if len(parts) != 26:
                continue
            try:
                [float(value) for value in parts[1:]]
            except ValueError:
                continue
            rows[parts[0]] = line
    return rows


paths = list((EARLY / "experiments").glob("*.txt"))
paths += [
    LATE / "Experiment_14_Sources.csv",
    LATE / "Experiment_14_Targets.csv",
    LATE / "Experiment_15_Sources.csv",
    LATE / "Experiment_15_Targets.csv",
]
rows = coordinate_rows(paths)


def write_panel(filename, labels):
    missing = [label for label in labels if label not in rows]
    if missing:
        raise SystemExit(f"Missing retained coordinate rows for {filename}: {missing}")
    content = "\n".join(rows[label] for label in labels) + "\n"
    (LATE / filename).write_text(content, encoding="utf-8")


prehistoric = [
    "Turkey_Anatolia_N_Ceramic_Barcin_(n=22)",
    "Georgia_Mesolithic_Trialetian_Kotias_Klde_(CHG)_(n=1)",
    "Russia_Karelia_Mesolithic_(EHG)_(n=15)",
    "Luxembourg_Mesolithic_Loschbour_(n=1)",
    "Iran_N_Ganj_Dareh_(n=7)",
    "Israel_Epipaleolithic_Natufian_(n=2)",
    "Morocco_UP_Iberomaurusian_Taforalt_(n=6)",
]

modern_full = [
    line.split(",", 1)[0]
    for line in (LATE / "Experiment_14_Sources.csv")
    .read_text(encoding="utf-8")
    .splitlines()
    if line.strip()
]

italki = "Italki_Jew_(n=9)"
ashkenazi = "Ashkenazi_Jew_(n=1209)"
modern_no_italki = [label for label in modern_full if label != italki]

experiment_9_sources = [
    "Greek_Dodecanese_Rhodes_(n=15)",
    "Italian_Calabria_Reggio_Calabria_(Calabrese)_(n=9)",
    "Lebanese_Arab_Christian_(n=27)",
    "Palestinian_Arab_Christian_(n=24)",
    "Samaritan_(n=7)",
]

experiment_12_sources = [
    "Samaritan_(n=7)",
    "Druze_Israel_(n=42)",
    "Palestinian_Arab_Christian_(n=24)",
    "Lebanese_Arab_Christian_(n=27)",
    "Italian_Tuscany_(Tuscan)_(n=138)",
    "Italian_Lombardy_(Lombard)_(n=10)",
    "German_(n=113)",
    "Polish_(n=68)",
    "Russian_Smolensk_(n=15)",
]

write_panel("Experiment_8_Sources.csv", prehistoric)
write_panel("Experiment_9_Sources.csv", experiment_9_sources)
write_panel("Experiment_10_Sources.csv", modern_full)
write_panel("Experiment_10_Targets.csv", [ashkenazi])
write_panel("Experiment_11_Sources.csv", modern_no_italki)
write_panel("Experiment_11_Targets.csv", [ashkenazi])
write_panel("Experiment_12_Sources.csv", experiment_12_sources)
write_panel("Experiment_12_Targets.csv", [ashkenazi])
write_panel("Experiment_13_Sources.csv", modern_no_italki)
write_panel("Experiment_13_Targets.csv", [italki])

print("Assembled linked inputs for Experiments 8-13 from retained repository rows.")
