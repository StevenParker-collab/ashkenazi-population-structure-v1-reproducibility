#!/usr/bin/env python3
"""Validate experiment coordinates, raw mixture totals, and SHA-256 hashes."""

from __future__ import annotations

import csv
import hashlib
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT / "experiments"
RAW_RESULTS = ROOT / "results" / "raw"
MANIFEST = ROOT / "MANIFEST.csv"
EXPECTED_EXPERIMENTS = [
    "01_NATUFIAN_PREHISTORIC_CONTROLLED_PANEL.txt",
    "02_ASHKENAZI_MODERN_FULL_COMPETITION.txt",
    "03_ASHKENAZI_SAME_PANEL_NO_NORTH_EAST_EUROPE.txt",
    "04_NORTHERN_ITALIAN_PROXY_TEST_SOUTHERN_ITALY_OMITTED.txt",
    "05_ASHKENAZI_FULL_PANEL_ITALIAN_JEWS_OMITTED.txt",
    "06_ITALIAN_JEWS_RECIPROCAL_FULL_MODERN_PANEL.txt",
    "07_REGIONAL_ASHKENAZI_FULL_MODERN_PANEL.txt",
]


def validate_experiment(path: Path) -> list[str]:
    errors: list[str] = []
    block: str | None = None
    rows: dict[str, list[str]] = {"sources": [], "targets": []}

    for number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if "SOURCES" in line and "=" in line:
            block = "sources"
            continue
        if "TARGETS" in line and "=" in line:
            block = "targets"
            continue
        if not line or block is None or "," not in line:
            continue

        parsed = next(csv.reader([line]))
        if len(parsed) != 26:
            errors.append(f"{path.name}:{number}: expected 26 columns, found {len(parsed)}")
            continue
        label = parsed[0]
        try:
            [float(value) for value in parsed[1:]]
        except ValueError:
            errors.append(f"{path.name}:{number}: non-numeric coordinate in {label}")
        if label in rows[block]:
            errors.append(f"{path.name}:{number}: duplicate {block} label {label}")
        rows[block].append(label)

    if not rows["sources"]:
        errors.append(f"{path.name}: no source rows found")
    if not rows["targets"]:
        errors.append(f"{path.name}: no target rows found")

    print(f"{path.name}: {len(rows['sources'])} sources, {len(rows['targets'])} targets")
    return errors


def validate_mixture_result(path: Path) -> list[str]:
    errors: list[str] = []
    with path.open(newline="", encoding="utf-8") as handle:
        delimiter = "\t" if path.suffix == ".tsv" else ","
        rows = list(csv.reader(handle, delimiter=delimiter))
    if len(rows) < 2 or len(rows[0]) < 3:
        return [f"{path.name}: invalid mixture result table"]
    for number, row in enumerate(rows[1:], 2):
        if not row or row[0] == "Average":
            continue
        try:
            coefficients = [float(value) for value in row[2:] if value != ""]
        except ValueError:
            errors.append(f"{path.name}:{number}: non-numeric coefficient")
            continue
        total = sum(coefficients)
        if abs(total - 100.0) > 0.11:
            errors.append(f"{path.name}:{number}: coefficients sum to {total:.6f}, not 100")
    return errors


def validate_experiment_1_alignment() -> list[str]:
    """Confirm that the expanded input and raw output contain the same 196 targets."""
    input_path = EXPERIMENTS / EXPECTED_EXPERIMENTS[0]
    result_path = RAW_RESULTS / "01_controlled_prehistoric_expanded_results.tsv"
    if not input_path.exists() or not result_path.exists():
        return ["Experiment 1 expanded input or raw result is missing"]

    input_targets: list[str] = []
    block: str | None = None
    for raw_line in input_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if "SOURCES" in line and "=" in line:
            block = "sources"
            continue
        if "TARGETS" in line and "=" in line:
            block = "targets"
            continue
        if block != "targets" or "," not in line:
            continue
        row = next(csv.reader([line]))
        if len(row) == 26:
            input_targets.append(row[0])

    with result_path.open(newline="", encoding="utf-8") as handle:
        result_targets = [
            row["Target"]
            for row in csv.DictReader(handle, delimiter="\t")
            if row["Target"] != "Average"
        ]

    errors: list[str] = []
    if len(input_targets) != 196:
        errors.append(f"Experiment 1 input: expected 196 targets, found {len(input_targets)}")
    if len(result_targets) != 196:
        errors.append(f"Experiment 1 result: expected 196 targets, found {len(result_targets)}")
    if input_targets != result_targets:
        missing_result = sorted(set(input_targets) - set(result_targets))
        missing_input = sorted(set(result_targets) - set(input_targets))
        errors.append(
            "Experiment 1 target order or membership differs between input and result"
            + (f"; absent from result: {', '.join(missing_result)}" if missing_result else "")
            + (f"; absent from input: {', '.join(missing_input)}" if missing_input else "")
        )
    else:
        print("Experiment 1 input/result alignment: 196 matching targets")
    return errors


def validate_hashes() -> list[str]:
    manifest = ROOT / "SHA256SUMS"
    if not manifest.exists():
        return ["SHA256SUMS is missing"]
    errors: list[str] = []
    for number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            errors.append(f"SHA256SUMS:{number}: malformed line")
            continue
        expected, relative = match.groups()
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"SHA256SUMS:{number}: missing file {relative}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            errors.append(f"SHA256SUMS:{number}: hash mismatch for {relative}")
    return errors


def validate_manifest() -> list[str]:
    if not MANIFEST.exists():
        return ["MANIFEST.csv is missing"]
    errors: list[str] = []
    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 7:
        errors.append(f"MANIFEST.csv: expected 7 experiment rows, found {len(rows)}")
    for row in rows:
        number = row.get("experiment", "?")
        status = row.get("status", "")
        input_file = row.get("input_file", "")
        if not input_file or not (ROOT / input_file).is_file():
            errors.append(f"MANIFEST.csv: Experiment {number} input file is missing")
        for field in ("result_file", "figure_file"):
            relative = row.get(field, "")
            if relative and not (ROOT / relative).is_file():
                errors.append(f"MANIFEST.csv: Experiment {number} {field} is missing")
        if status == "input_ready_result_pending" and row.get("result_file"):
            errors.append(f"MANIFEST.csv: Experiment {number} is pending but has a result path")
    return errors


def main() -> int:
    errors: list[str] = []
    for filename in EXPECTED_EXPERIMENTS:
        path = EXPERIMENTS / filename
        if not path.exists():
            errors.append(f"missing experiment file: {filename}")
            continue
        errors.extend(validate_experiment(path))

    for path in sorted([*RAW_RESULTS.glob("*.csv"), *RAW_RESULTS.glob("*.tsv")]):
        if path.name.startswith(("01_", "02_", "03_", "05_", "06_", "07_")):
            errors.extend(validate_mixture_result(path))

    errors.extend(validate_experiment_1_alignment())

    summary_check = ROOT / "scripts" / "summarize_experiment_07.py"
    if not summary_check.exists():
        errors.append("missing Experiment 7 summary script")
    else:
        completed = subprocess.run(
            [sys.executable, str(summary_check), "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode:
            errors.append(completed.stderr.strip() or "Experiment 7 grouped summary check failed")
        elif completed.stdout.strip():
            print(completed.stdout.strip())

    natufian_check = ROOT / "scripts" / "derive_natufian_math.py"
    if not natufian_check.exists():
        errors.append("missing Natufian derivation script")
    else:
        completed = subprocess.run(
            [sys.executable, str(natufian_check), "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode:
            errors.append(completed.stderr.strip() or "Natufian derived-table check failed")
        elif completed.stdout.strip():
            print(completed.stdout.strip())
    errors.extend(validate_manifest())
    errors.extend(validate_hashes())

    if errors:
        print("\nValidation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("\nValidation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
