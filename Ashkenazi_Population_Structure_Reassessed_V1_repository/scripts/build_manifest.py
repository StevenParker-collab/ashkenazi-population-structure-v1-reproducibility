#!/usr/bin/env python3
"""Rebuild the repository payload manifest and SHA-256 checksum list."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "MANIFEST.csv"
SUMS = ROOT / "SHA256SUMS.txt"
EXCLUDED_FROM_MANIFEST = {"MANIFEST.csv", "SHA256SUMS.txt"}
EXCLUDED_FROM_SUMS = {"SHA256SUMS.txt"}


def files(excluded: set[str]):
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel in excluded:
            continue
        if any(part == ".git" for part in path.parts):
            continue
        yield path, rel


with MANIFEST.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.writer(handle)
    writer.writerow(["path", "size_bytes", "sha256"])
    for path, rel in files(EXCLUDED_FROM_MANIFEST):
        writer.writerow([rel, path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()])

with SUMS.open("w", encoding="utf-8", newline="\n") as handle:
    for path, rel in files(EXCLUDED_FROM_SUMS):
        handle.write(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {rel}\n")

print("Repository manifest and checksum list rebuilt.")
