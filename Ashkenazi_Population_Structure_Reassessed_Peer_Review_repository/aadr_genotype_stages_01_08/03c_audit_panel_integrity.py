#!/usr/bin/env python3

import csv
import hashlib
import re
from datetime import datetime
from pathlib import Path

root = Path.cwd()
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

panels = {
    "primary": (
        root / "manifests/modern_panel_primary.tsv",
        root / "data/eigenstrat/modern_primary",
        369,
    ),
    "strict_pass": (
        root / "manifests/modern_panel_strict_pass.tsv",
        root / "data/eigenstrat/modern_strict_pass",
        247,
    ),
}

prohibited = {
    "YZ024.HO",
    "AshkenaziJew5780.HO",
    "AshkenaziJew5775.HO",
}

def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def read_manifest(path):
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    ids = [row["Genetic_ID"].strip() for row in rows]
    groups = {
        row["Genetic_ID"].strip(): row["Clean_Group"].strip()
        for row in rows
    }

    if len(ids) != len(set(ids)):
        raise SystemExit(f"ERROR: duplicate manifest IDs: {path}")

    return ids, groups

def read_ind(path):
    ids = []
    groups = {}

    with path.open() as handle:
        for number, raw in enumerate(handle, 1):
            fields = raw.split()

            if len(fields) != 3:
                raise SystemExit(
                    f"ERROR: malformed IND line {number}: {path}"
                )

            sample_id, sex, group = fields

            if sample_id in groups:
                raise SystemExit(
                    f"ERROR: duplicate IND ID {sample_id}: {path}"
                )

            ids.append(sample_id)
            groups[sample_id] = group

    return ids, groups

def read_header(path):
    data = path.open("rb").read(128)
    match = re.match(
        rb"^GENO\s+(\d+)\s+(\d+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)",
        data,
    )

    if not match:
        raise SystemExit(f"ERROR: invalid packed GENO header: {path}")

    return (
        int(match.group(1)),
        int(match.group(2)),
        match.group(3).decode(),
        match.group(4).decode(),
    )

results = {}
report_rows = []

for panel, (manifest, stem, expected) in panels.items():
    geno = Path(f"{stem}.geno")
    snp = Path(f"{stem}.snp")
    ind = Path(f"{stem}.ind")

    for path in (manifest, geno, snp, ind):
        if not path.is_file() or path.stat().st_size == 0:
            raise SystemExit(f"ERROR: missing or empty file: {path}")

    manifest_ids, manifest_groups = read_manifest(manifest)
    ind_ids, ind_groups = read_ind(ind)
    snp_count = sum(1 for _ in snp.open())
    header_ind, header_snp, snp_hash, ind_hash = read_header(geno)

    if len(manifest_ids) != expected:
        raise SystemExit(
            f"ERROR: {panel} manifest count "
            f"{len(manifest_ids)} != {expected}"
        )

    if ind_ids != manifest_ids:
        raise SystemExit(
            f"ERROR: {panel} IND IDs/order differ from manifest"
        )

    mismatches = [
        sample_id
        for sample_id in manifest_ids
        if ind_groups[sample_id] != manifest_groups[sample_id]
    ]

    if mismatches:
        raise SystemExit(
            f"ERROR: {panel} clean-label mismatches: {mismatches[:10]}"
        )

    bad_ids = sorted(set(ind_ids) & prohibited)

    if bad_ids:
        raise SystemExit(
            f"ERROR: prohibited IDs present in {panel}: {bad_ids}"
        )

    if snp_count != 276725:
        raise SystemExit(
            f"ERROR: {panel} SNP count {snp_count} != 276725"
        )

    if (header_ind, header_snp) != (expected, snp_count):
        raise SystemExit(
            f"ERROR: {panel} packed header is "
            f"{header_ind}x{header_snp}, expected {expected}x{snp_count}"
        )

    results[panel] = {
        "ids": set(ind_ids),
        "snp_sha256": sha256(snp),
    }

    report_rows.append({
        "Panel": panel,
        "Individuals": len(ind_ids),
        "SNPs": snp_count,
        "Populations": len(set(ind_groups.values())),
        "Exact_ID_Order": "PASS",
        "Clean_Labels": "PASS",
        "Prohibited_IDs_Absent": "PASS",
        "Packed_Header": "PASS",
        "GENO_SHA256": sha256(geno),
        "SNP_SHA256": results[panel]["snp_sha256"],
        "IND_SHA256": sha256(ind),
        "Header_SNP_Hash": snp_hash,
        "Header_IND_Hash": ind_hash,
    })

if not results["strict_pass"]["ids"] < results["primary"]["ids"]:
    raise SystemExit(
        "ERROR: strict-pass IDs are not a proper primary subset"
    )

if results["primary"]["snp_sha256"] != results["strict_pass"]["snp_sha256"]:
    raise SystemExit(
        "ERROR: primary and strict SNP files differ"
    )

report = root / f"manifests/03c_panel_integrity_audit_{stamp}.tsv"

with report.open("w", newline="") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=list(report_rows[0]),
        delimiter="\t",
    )
    writer.writeheader()
    writer.writerows(report_rows)

print("Stage 03C integrity audit passed")
print("--------------------------------")
for row in report_rows:
    print(
        f"{row['Panel']}: {row['Individuals']} individuals, "
        f"{row['SNPs']} SNPs, {row['Populations']} populations"
    )
print("Exact manifest ID order: PASS")
print("Clean population labels: PASS")
print("Excluded Ashkenazi IDs absent: PASS")
print("Strict-pass is a proper primary subset: PASS")
print("Primary and strict SNP files identical: PASS")
print(f"Audit report: {report}")
