#!/usr/bin/env python3
"""Verify integrity, required contents, and supplied analysis checks for the Version 1 repository."""

from __future__ import annotations

import csv
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
errors: list[str] = []

required = [
    "README.md",
    "CITATION.cff",
    "DATA_AVAILABILITY.md",
    "REPOSITORY_MAP.md",
    "VALIDATION_REPORT.md",
    "MANIFEST.csv",
    "SHA256SUMS.txt",
    "manuscript/Ashkenazi_Population_Structure_Reassessed_V1.docx",
    "manuscript/Ashkenazi_Population_Structure_Reassessed_V1.pdf",
    "supplementary/Supplementary_Appendix.docx",
    "supplementary/Supplementary_Appendix.pdf",
    "supplementary/tables/Table_S1_FST_results.csv",
    "supplementary/tables/Table_S2_FST_calibration.csv",
    "global25_experiments/scripts/validate_experiment_suite.py",
    "descriptive_fst/scripts/validate_fst_tables.py",
]
for rel in required:
    if not (ROOT / rel).is_file():
        errors.append(f"missing required file: {rel}")

# Reject obsolete package material.
for path in ROOT.rglob("*"):
    rel = path.relative_to(ROOT).as_posix()
    if ".git" in path.parts:
        errors.append(f"embedded .git material is not allowed: {rel}")
    if path.is_dir() and path.name == "qpadm_fst":
        errors.append("obsolete qpadm_fst directory is present")
    if path.is_file() and "Geometry_Update_2026-07-16" in path.name:
        errors.append(f"obsolete Version 4 manuscript is present: {rel}")

# Check SHA256SUMS and require complete file coverage.
if (ROOT / "SHA256SUMS.txt").is_file():
    listed: set[str] = set()
    for number, line in enumerate((ROOT / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            errors.append(f"SHA256SUMS.txt:{number}: malformed line")
            continue
        expected, rel = match.groups()
        listed.add(rel)
        path = ROOT / rel
        if not path.is_file():
            errors.append(f"SHA256SUMS.txt:{number}: missing file {rel}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            errors.append(f"SHA256SUMS.txt:{number}: hash mismatch for {rel}")
    actual_files = {
        p.relative_to(ROOT).as_posix()
        for p in ROOT.rglob("*")
        if p.is_file() and p.name != "SHA256SUMS.txt" and ".git" not in p.parts
    }
    if listed != actual_files:
        for rel in sorted(actual_files - listed):
            errors.append(f"checksum list omits file: {rel}")
        for rel in sorted(listed - actual_files):
            errors.append(f"checksum list contains nonexistent file: {rel}")

# Check MANIFEST payload inventory.
if (ROOT / "MANIFEST.csv").is_file():
    with (ROOT / "MANIFEST.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    listed = {r["path"] for r in rows}
    actual = {
        p.relative_to(ROOT).as_posix()
        for p in ROOT.rglob("*")
        if p.is_file() and p.relative_to(ROOT).as_posix() not in {"MANIFEST.csv", "SHA256SUMS.txt"} and ".git" not in p.parts
    }
    if listed != actual:
        for rel in sorted(actual - listed):
            errors.append(f"manifest omits file: {rel}")
        for rel in sorted(listed - actual):
            errors.append(f"manifest contains nonexistent file: {rel}")
    by_path = {r["path"]: r for r in rows}
    for rel in sorted(actual & listed):
        p = ROOT / rel
        row = by_path[rel]
        if int(row["size_bytes"]) != p.stat().st_size:
            errors.append(f"manifest size mismatch for {rel}")
        if row["sha256"] != hashlib.sha256(p.read_bytes()).hexdigest():
            errors.append(f"manifest hash mismatch for {rel}")

validators = [
    "global25_experiments/scripts/validate_experiment_suite.py",
    "global25_experiments/experiments_01_07/scripts/validate_repository.py",
    "global25_experiments/experiments_08_15/analysis/verify_experiment14_germany_geometry.py",
    "descriptive_fst/scripts/validate_fst_tables.py",
]
for rel in validators:
    path = ROOT / rel
    if not path.is_file():
        continue
    completed = subprocess.run([sys.executable, str(path)], cwd=ROOT, text=True, capture_output=True)
    if completed.stdout.strip():
        print(completed.stdout.strip())
    if completed.returncode:
        errors.append(f"validator failed: {rel}: {completed.stderr.strip() or completed.stdout.strip()}")

if errors:
    print("\nRepository validation failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    raise SystemExit(1)

print("\nVersion 1 repository validation passed.")
