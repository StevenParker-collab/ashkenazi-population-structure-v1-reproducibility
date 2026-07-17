#!/usr/bin/env python3
"""Derive the expanded Experiment 1 Natufian tables used in the article."""

from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw" / "01_controlled_prehistoric_expanded_results.tsv"
REDDIT = ROOT / "results" / "context" / "01_reddit_screenshot_14_targets.csv"
POOLED = ROOT / "results" / "context" / "01_pooled_ashkenazi_matched_result.csv"
SUMMARY = ROOT / "results" / "derived" / "01_natufian_math_summary.csv"
REGIONS = ROOT / "results" / "derived" / "01_natufian_regional_summary.csv"
METHOD = ROOT / "results" / "derived" / "01_natufian_method_comparison.csv"
POINTS = ROOT / "results" / "derived" / "01_natufian_comparison_points.csv"

NATUFIAN_COLUMN = "Israel_Epipaleolithic_Natufian_(n=2)"

GROUPS = [
    ("Calabria", ("Italian_Calabria:",), 8, "individual"),
    ("Eastern Sicily", ("Sicilian_East:",), 3, "individual"),
    ("Western Sicily", ("Sicilian_West:",), 3, "individual"),
    ("Campania", ("Italian_Campania:",), 26, "individual"),
    ("Southern Italy combined", ("Italian_Calabria:", "Sicilian_East:", "Sicilian_West:", "Italian_Campania:"), 40, "individual"),
    ("Malta", ("Maltese:",), 8, "individual"),
    ("Crete", ("Greek_Crete:", "Greek_Crete_Chania:", "Greek_Crete_Heraklion:", "Greek_Crete_Lasithi:"), 111, "individual"),
    ("Dodecanese, Rhodes, and Kos", ("Greek_Dodecanese:", "Greek_Dodecanese_Rhodes:", "Greek_Kos:"), 26, "individual"),
    ("Regional Ashkenazi populations", ("Ashkenazi_Jew_",), 10, "population average"),
]


def read_dicts(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def make_csv(header: list[str], data: list[list[object]]) -> str:
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(data)
    return stream.getvalue()


def stats(values: list[float]) -> tuple[float, float, float, float]:
    low = min(values)
    high = max(values)
    return sum(values) / len(values), low, high, high - low


def raw_values(rows: list[dict[str, str]], prefixes: tuple[str, ...]) -> list[float]:
    return [
        float(row[NATUFIAN_COLUMN])
        for row in rows
        if row["Target"].startswith(prefixes)
    ]


def render() -> dict[Path, str]:
    raw_rows = [
        row
        for row in read_dicts(RAW, delimiter="\t")
        if row["Target"] != "Average"
    ]
    if len(raw_rows) != 196:
        raise ValueError(f"Expanded Experiment 1 must contain 196 targets, found {len(raw_rows)}")

    reddit_rows = [row for row in read_dicts(REDDIT) if row["Target"] != "Average"]
    if len(reddit_rows) != 14:
        raise ValueError(f"Reddit transcription must contain 14 targets, found {len(reddit_rows)}")

    raw_by_target = {row["Target"]: row for row in raw_rows}
    reddit_by_target = {row["Target"]: row for row in reddit_rows}
    missing = sorted(set(reddit_by_target) - set(raw_by_target))
    if missing:
        raise ValueError("Reddit targets missing from controlled run: " + ", ".join(missing))

    italki = float(raw_by_target["Italki_Jew_(n=9)"][NATUFIAN_COLUMN])
    pooled_rows = read_dicts(POOLED)
    if len(pooled_rows) != 1:
        raise ValueError("Pooled Ashkenazi context table must contain exactly one result")
    pooled = float(pooled_rows[0]["Natufian"])

    regional_rows: list[list[object]] = []
    grouped: dict[str, tuple[float, float, float, float, int]] = {}
    for name, prefixes, expected_count, level in GROUPS:
        values = raw_values(raw_rows, prefixes)
        if len(values) != expected_count:
            raise ValueError(f"{name}: expected {expected_count} targets, found {len(values)}")
        mean, low, high, width = stats(values)
        grouped[name] = (mean, low, high, width, len(values))
        regional_rows.append(
            [name, len(values), f"{mean:.4f}", f"{low:.1f}", f"{high:.1f}", f"{width:.1f}", level, "controlled expanded run"]
        )

    reddit_values = [float(row["Natufian"]) for row in reddit_rows]
    reddit_mean, reddit_low, reddit_high, reddit_width = stats(reddit_values)
    controlled_14_values = [float(raw_by_target[target][NATUFIAN_COLUMN]) for target in reddit_by_target]
    controlled_14_mean, controlled_14_low, controlled_14_high, controlled_14_width = stats(controlled_14_values)
    regional_rows[0:0] = [
        ["Reddit screenshot: selected Calabria and Sicily", 14, f"{reddit_mean:.4f}", f"{reddit_low:.1f}", f"{reddit_high:.1f}", f"{reddit_width:.1f}", "individual", "Reddit screenshot transcription"],
        ["Controlled replication: identical fourteen targets", 14, f"{controlled_14_mean:.4f}", f"{controlled_14_low:.1f}", f"{controlled_14_high:.1f}", f"{controlled_14_width:.1f}", "individual", "controlled expanded run"],
    ]
    regional_rows.extend(
        [
            ["Pooled Ashkenazi Jews", 1, f"{pooled:.4f}", f"{pooled:.1f}", f"{pooled:.1f}", "0.0", "pooled population", "matched supplemental run"],
            ["Italki Jews", 1, f"{italki:.4f}", f"{italki:.1f}", f"{italki:.1f}", "0.0", "pooled population", "controlled expanded run"],
        ]
    )

    method_rows: list[list[object]] = []
    higher = same = lower = 0
    for target in reddit_by_target:
        reddit_value = float(reddit_by_target[target]["Natufian"])
        controlled_value = float(raw_by_target[target][NATUFIAN_COLUMN])
        difference = controlled_value - reddit_value
        if difference > 1e-9:
            direction = "higher in controlled run"
            higher += 1
        elif difference < -1e-9:
            direction = "lower in controlled run"
            lower += 1
        else:
            direction = "unchanged"
            same += 1
        method_rows.append(
            [target, f"{reddit_value:.1f}", f"{controlled_value:.1f}", f"{difference:.1f}", direction]
        )

    south_mean, south_low, south_high, south_width, south_count = grouped["Southern Italy combined"]
    regional_mean, regional_low, regional_high, regional_width, regional_count = grouped["Regional Ashkenazi populations"]
    maltese_mean, maltese_low, maltese_high, maltese_width, maltese_count = grouped["Malta"]
    crete_mean, crete_low, crete_high, crete_width, crete_count = grouped["Crete"]
    dodec_mean, dodec_low, dodec_high, dodec_width, dodec_count = grouped["Dodecanese, Rhodes, and Kos"]
    italki_gap = italki - south_high
    dilution_boundary = 100 * (1 - pooled / italki)

    summary_rows = [
        ["expanded_experiment_1_target_count", "count(non-Average rows)", len(raw_rows), "rows"],
        ["reddit_screenshot_target_count", "count(transcribed targets)", len(reddit_rows), "rows"],
        ["reddit_screenshot_natufian_mean", "sum(Natufian)/n", f"{reddit_mean:.4f}", "percent"],
        ["controlled_same_14_natufian_mean", "sum(Natufian)/n", f"{controlled_14_mean:.4f}", "percent"],
        ["same_14_mean_shift", "controlled mean - Reddit mean", f"{controlled_14_mean - reddit_mean:.4f}", "percentage_points"],
        ["same_14_rows_higher_in_controlled_run", "count(controlled > Reddit)", higher, "rows"],
        ["same_14_rows_unchanged", "count(controlled = Reddit)", same, "rows"],
        ["same_14_rows_lower_in_controlled_run", "count(controlled < Reddit)", lower, "rows"],
        ["southern_italian_reference_count", "Campania + Calabria + eastern Sicily + western Sicily", south_count, "rows"],
        ["southern_italian_natufian_mean", "sum(Natufian)/n", f"{south_mean:.4f}", "percent"],
        ["southern_italian_low", "min(Natufian)", f"{south_low:.1f}", "percent"],
        ["southern_italian_high", "max(Natufian)", f"{south_high:.1f}", "percent"],
        ["southern_italian_internal_range", "high - low", f"{south_width:.1f}", "percentage_points"],
        ["italki_natufian", "observed", f"{italki:.1f}", "percent"],
        ["italki_gap_above_southern_italian_high", "Italki - Southern Italian high", f"{italki_gap:.1f}", "percentage_points"],
        ["southern_range_to_italki_gap_ratio", "Southern Italian range / Italki high-end gap", f"{south_width / italki_gap:.2f}", "ratio"],
        ["pooled_ashkenazi_natufian", "matched supplemental result", f"{pooled:.1f}", "percent"],
        ["pooled_ashkenazi_gap_above_southern_italian_high", "pooled Ashkenazi - Southern Italian high", f"{pooled - south_high:.1f}", "percentage_points"],
        ["regional_ashkenazi_natufian_mean", "mean of ten population-average targets", f"{regional_mean:.4f}", "percent"],
        ["regional_ashkenazi_natufian_range", "minimum to maximum", f"{regional_low:.1f}-{regional_high:.1f}", "percent"],
        ["maltese_natufian_range", "minimum to maximum", f"{maltese_low:.1f}-{maltese_high:.1f}", "percent"],
        ["crete_natufian_range", "minimum to maximum", f"{crete_low:.1f}-{crete_high:.1f}", "percent"],
        ["dodecanese_rhodes_kos_natufian_range", "minimum to maximum", f"{dodec_low:.1f}-{dodec_high:.1f}", "percent"],
        ["zero_natufian_source_dilution_boundary", "100 * (1 - pooled Ashkenazi / Italki)", f"{dilution_boundary:.4f}", "percent"],
    ]

    point_rows = [
        ["Lowest Southern Italian individual", f"{south_low:.1f}", f"{100-south_low:.1f}", "controlled expanded run"],
        ["Southern Italian mean, 40 individuals", f"{south_mean:.2f}", f"{100-south_mean:.2f}", "controlled expanded run"],
        ["Highest Southern Italian individual", f"{south_high:.1f}", f"{100-south_high:.1f}", "controlled expanded run"],
        ["Pooled Ashkenazi Jews", f"{pooled:.1f}", f"{100-pooled:.1f}", "matched supplemental run"],
        ["Highest regional Ashkenazi average", f"{regional_high:.1f}", f"{100-regional_high:.1f}", "controlled expanded run"],
        ["Italki Jews", f"{italki:.1f}", f"{100-italki:.1f}", "controlled expanded run"],
        ["Highest Maltese individual", f"{maltese_high:.1f}", f"{100-maltese_high:.1f}", "controlled expanded run"],
    ]

    return {
        SUMMARY: make_csv(["metric", "formula", "value", "unit"], summary_rows),
        REGIONS: make_csv(["comparison_set", "n", "mean_natufian_percent", "minimum_percent", "maximum_percent", "range_width_points", "coordinate_level", "provenance"], regional_rows),
        METHOD: make_csv(["target", "reddit_natufian_percent", "controlled_natufian_percent", "controlled_minus_reddit_points", "direction"], method_rows),
        POINTS: make_csv(["comparison_point", "natufian_percent", "other_six_components_percent", "provenance"], point_rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = render()

    if args.check:
        stale = [
            str(path.relative_to(ROOT))
            for path, content in expected.items()
            if not path.exists() or path.read_text(encoding="utf-8") != content
        ]
        if stale:
            print("Derived Natufian files are stale or missing: " + ", ".join(stale), file=sys.stderr)
            return 1
        print("Expanded Experiment 1 derived tables match the documented inputs.")
        return 0

    for path, content in expected.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    print("Wrote " + ", ".join(str(path.relative_to(ROOT)) for path in expected))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
