#!/usr/bin/env bash
set -euo pipefail

expected_dir="/home/computer/popgen/projects/ashkenazi_reference_test"
anno="v66.p1_compatibility_HO.aadr.PUB.anno"
ind="v66.p1_compatibility_HO.aadr.patch.PUB.ind"
stamp="$(date +%Y%m%d_%H%M%S)"

mkdir -p logs manifests backups
log="logs/02_finalize_clean_manifest_${stamp}.log"
exec > >(tee "$log") 2>&1

echo "Stage 02B: finalize modern sample manifests"
echo "Started: $(date --iso-8601=seconds)"
echo "Directory: $(pwd)"

[[ "$(pwd)" == "$expected_dir" ]] || { echo "ERROR: wrong directory"; exit 1; }
[[ -s "$anno" ]] || { echo "ERROR: missing $anno"; exit 1; }
[[ -s "$ind" ]] || { echo "ERROR: missing $ind"; exit 1; }

backup_dir="backups/02_finalize_clean_manifest_${stamp}"
mkdir -p "$backup_dir"
for file in manifests/modern_panel_*.tsv manifests/modern_panel_*_ids.txt; do
    [[ -e "$file" ]] && cp -a "$file" "$backup_dir/"
done

python - <<'PY'
import csv
from collections import Counter
from pathlib import Path

anno = Path("v66.p1_compatibility_HO.aadr.PUB.anno")
ind = Path("v66.p1_compatibility_HO.aadr.patch.PUB.ind")
outdir = Path("manifests")

base_groups = {
    "Jew_Ashkenazi",
    "Italian_South",
    "Sicilian",
    "Maltese",
    "Greek",
    "Italian_Central",
    "Italian_North",
    "Cypriot",
    "Palestinian",
    "Lebanese",
    "Lebanese_Christian",
    "Lebanese_Muslim",
    "Druze",
    "Jew_Turkish",
    "Jew_Iraqi",
    "Jew_Yemenite",
}

with anno.open(encoding="utf-8-sig", newline="") as handle:
    reader = csv.reader(handle, delimiter="\t")
    header = next(reader)
    rows = list(reader)

ind_rows = {}
with ind.open(encoding="utf-8-sig") as handle:
    for line in handle:
        fields = line.split()
        if len(fields) >= 3:
            ind_rows[fields[0]] = fields[2]

records = []
exclusions = []

for row in rows:
    if len(row) < 49:
        continue

    genetic_id = row[0].strip()
    group = row[14].strip()
    locality = row[15].strip()
    suffix = row[20].strip()
    data_type = row[21].strip()
    family_relations = row[31].strip()
    assessment = row[47].strip()
    assessment_warning = row[48].strip()

    matching_base = next(
        (
            base
            for base in sorted(base_groups, key=len, reverse=True)
            if group == base or group.startswith(base + "-")
        ),
        None,
    )

    if matching_base is None:
        continue

    if genetic_id not in ind_rows:
        raise RuntimeError(f"Annotation ID absent from IND file: {genetic_id}")

    if ind_rows[genetic_id] != group:
        raise RuntimeError(
            f"Group mismatch for {genetic_id}: annotation={group}, IND={ind_rows[genetic_id]}"
        )

    if group != matching_base:
        exclusions.append({
            "Genetic_ID": genetic_id,
            "Original_Group": group,
            "Locality": locality,
            "Assessment": assessment,
            "Reason": "Variant group excluded by default, including QCremove/outlier/subgroup labels",
        })
        continue

    if assessment not in {"Pass", "PROVISIONAL_PASS"}:
        exclusions.append({
            "Genetic_ID": genetic_id,
            "Original_Group": group,
            "Locality": locality,
            "Assessment": assessment,
            "Reason": "Assessment is not Pass or PROVISIONAL_PASS",
        })
        continue

    if assessment == "PROVISIONAL_PASS":
        if suffix != "DG" or data_type != "Shotgun.diploid":
            raise RuntimeError(
                f"Unexpected PROVISIONAL_PASS data type for {genetic_id}: "
                f"{suffix}, {data_type}"
            )
        if assessment_warning not in {"", ".."}:
            raise RuntimeError(
                f"Specific PROVISIONAL_PASS warning requires review for "
                f"{genetic_id}: {assessment_warning}"
            )

    clean_group = group
    relabel_basis = "Original exact AADR group retained"

    if group == "Italian_North":
        if locality == "Italy, modern 2":
            clean_group = "Italian_Bergamo"
            relabel_basis = "AADR locality Italy, modern 2"
        elif locality == "Italy, modern 3":
            clean_group = "Italian_Tuscan"
            relabel_basis = "AADR locality Italy, modern 3"
        else:
            clean_group = "Italian_North"
            relabel_basis = "Explicit northern Italian locality"

    assessment_basis = (
        "AADR Pass"
        if assessment == "Pass"
        else "AADR PROVISIONAL_PASS; DG Shotgun.diploid; no specific warning"
    )

    records.append({
        "Genetic_ID": genetic_id,
        "Original_Group": group,
        "Clean_Group": clean_group,
        "Locality": locality,
        "Suffix": suffix,
        "Data_Type": data_type,
        "Assessment": assessment,
        "Assessment_Warning": assessment_warning,
        "Assessment_Basis": assessment_basis,
        "Relabel_Basis": relabel_basis,
        "Family_Relations": family_relations,
    })

records.sort(key=lambda x: (x["Clean_Group"], x["Genetic_ID"]))
exclusions.sort(key=lambda x: (x["Original_Group"], x["Genetic_ID"]))
strict = [record for record in records if record["Assessment"] == "Pass"]

fields = [
    "Genetic_ID",
    "Original_Group",
    "Clean_Group",
    "Locality",
    "Suffix",
    "Data_Type",
    "Assessment",
    "Assessment_Warning",
    "Assessment_Basis",
    "Relabel_Basis",
    "Family_Relations",
]

with (outdir / "modern_panel_primary.tsv").open(
    "w", encoding="utf-8", newline=""
) as handle:
    writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
    writer.writeheader()
    writer.writerows(records)

with (outdir / "modern_panel_strict_pass.tsv").open(
    "w", encoding="utf-8", newline=""
) as handle:
    writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
    writer.writeheader()
    writer.writerows(strict)

with (outdir / "modern_panel_primary_ids.txt").open("w", encoding="utf-8") as handle:
    for record in records:
        handle.write(record["Genetic_ID"] + "\n")

with (outdir / "modern_panel_strict_pass_ids.txt").open(
    "w", encoding="utf-8"
) as handle:
    for record in strict:
        handle.write(record["Genetic_ID"] + "\n")

exclusion_fields = [
    "Genetic_ID",
    "Original_Group",
    "Locality",
    "Assessment",
    "Reason",
]

with (outdir / "modern_panel_exclusions.tsv").open(
    "w", encoding="utf-8", newline=""
) as handle:
    writer = csv.DictWriter(handle, fieldnames=exclusion_fields, delimiter="\t")
    writer.writeheader()
    writer.writerows(exclusions)

primary_counts = Counter(record["Clean_Group"] for record in records)
strict_counts = Counter(record["Clean_Group"] for record in strict)

expected = {
    "Jew_Ashkenazi": 7,
    "Italian_Bergamo": 26,
    "Italian_Tuscan": 16,
    "Italian_North": 19,
}

for group, expected_count in expected.items():
    observed = primary_counts[group]
    if observed != expected_count:
        raise RuntimeError(
            f"Unexpected primary count for {group}: "
            f"expected {expected_count}, observed {observed}"
        )

unexpected_family = [
    record
    for record in records
    if record["Family_Relations"] not in {"", ".."}
]

print()
print("Completion summary")
print("------------------")
print(f"Primary panel samples: {len(records)}")
print(f"Strict Pass-only samples: {len(strict)}")
print(f"PROVISIONAL_PASS samples retained and flagged: {len(records) - len(strict)}")
print(f"Excluded variant or failed-review records: {len(exclusions)}")
print(f"Included samples with non-placeholder family-relation entries: {len(unexpected_family)}")

print()
print("Primary panel counts")
for group, count in sorted(primary_counts.items()):
    print(f"{group}\t{count}")

print()
print("Strict Pass-only counts")
for group, count in sorted(strict_counts.items()):
    print(f"{group}\t{count}")

if unexpected_family:
    print()
    print("Family-relation entries requiring review before PCA")
    for record in unexpected_family:
        print(
            f"{record['Genetic_ID']}\t{record['Clean_Group']}\t"
            f"{record['Family_Relations']}"
        )

print()
print("Outputs")
print("manifests/modern_panel_primary.tsv")
print("manifests/modern_panel_primary_ids.txt")
print("manifests/modern_panel_strict_pass.tsv")
print("manifests/modern_panel_strict_pass_ids.txt")
print("manifests/modern_panel_exclusions.tsv")
PY

sha256sum \
    manifests/modern_panel_primary.tsv \
    manifests/modern_panel_primary_ids.txt \
    manifests/modern_panel_strict_pass.tsv \
    manifests/modern_panel_strict_pass_ids.txt \
    manifests/modern_panel_exclusions.tsv \
    > "manifests/02_final_manifest_checksums_${stamp}.sha256"

echo
echo "Log: $log"
echo "Finished: $(date --iso-8601=seconds)"
