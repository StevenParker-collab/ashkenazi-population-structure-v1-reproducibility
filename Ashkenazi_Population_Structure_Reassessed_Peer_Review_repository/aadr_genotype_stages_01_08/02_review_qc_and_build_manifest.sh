#!/usr/bin/env bash
set -euo pipefail

expected_dir="/home/computer/popgen/projects/ashkenazi_reference_test"
anno="v66.p1_compatibility_HO.aadr.PUB.anno"
ind="v66.p1_compatibility_HO.aadr.patch.PUB.ind"
italian_map="modern_italian_manifest.tsv"
stamp="$(date +%Y%m%d_%H%M%S)"

mkdir -p logs manifests backups
log="logs/02_review_qc_and_build_manifest_${stamp}.log"
exec > >(tee "$log") 2>&1

echo "Stage 02: assessment review and conservative manifest construction"
echo "Started: $(date --iso-8601=seconds)"
echo "Directory: $(pwd)"
echo "Python: $(python --version 2>&1)"

if [[ "$(pwd)" != "$expected_dir" ]]; then
    echo "ERROR: expected directory $expected_dir"
    exit 1
fi

for file in "$anno" "$ind" "$italian_map"; do
    if [[ ! -s "$file" ]]; then
        echo "ERROR: missing or empty input file: $file"
        exit 1
    fi
done

backup_dir="backups/02_review_qc_and_build_manifest_${stamp}"
mkdir -p "$backup_dir"

for file in manifests/target_sample_review.tsv manifests/clean_population_manifest.tsv manifests/clean_population_ids.txt; do
    if [[ -e "$file" ]]; then
        cp -a "$file" "$backup_dir/"
    fi
done

sha256sum "$anno" "$ind" "$italian_map" > "manifests/02_input_checksums_${stamp}.sha256"

python - <<'PY'
import csv
import re
from collections import Counter
from pathlib import Path

anno_path = Path("v66.p1_compatibility_HO.aadr.PUB.anno")
ind_path = Path("v66.p1_compatibility_HO.aadr.patch.PUB.ind")
map_path = Path("modern_italian_manifest.tsv")
review_path = Path("manifests/target_sample_review.tsv")
clean_path = Path("manifests/clean_population_manifest.tsv")
ids_path = Path("manifests/clean_population_ids.txt")

def normalized(value):
    return re.sub(r"[^a-z0-9]+", "", value.lower().strip())

with anno_path.open(encoding="utf-8-sig", newline="") as handle:
    reader = csv.reader(handle, delimiter="\t")
    header = next(reader)
    rows = list(reader)

header_lookup = {normalized(name): index for index, name in enumerate(header)}

def column(*names):
    for name in names:
        key = normalized(name)
        if key in header_lookup:
            return header_lookup[key]
    raise RuntimeError(f"Required annotation column not found: {names}")

id_i = 0
group_i = column("Group ID", "Group_ID")
assessment_i = column("ASSESSMENT", "Assessment")
locality_i = column("Locality")
publication_i = 5

italian_map = {}
with map_path.open(encoding="utf-8-sig", newline="") as handle:
    reader = csv.DictReader(handle, delimiter="\t")
    for row in reader:
        genetic_id = row["Genetic_ID"].strip()
        clean_group = row["Clean_Group"].strip()
        if genetic_id in italian_map:
            raise RuntimeError(f"Duplicate Italian mapping: {genetic_id}")
        italian_map[genetic_id] = clean_group

ind_ids = set()
with ind_path.open(encoding="utf-8-sig") as handle:
    for line in handle:
        fields = line.split()
        if fields:
            ind_ids.add(fields[0])

target_groups = {
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

known_questionable_ashkenazi = {"YZ024.HO", "Z024.HO"}
records = []
seen_ids = set()

for row in rows:
    if len(row) <= max(id_i, group_i, assessment_i, locality_i, publication_i):
        continue

    genetic_id = row[id_i].strip()
    original_group = row[group_i].strip()
    assessment = row[assessment_i].strip()
    locality = row[locality_i].strip()
    publication = row[publication_i].strip()

    if original_group not in target_groups and not original_group.startswith("Jew_Ashkenazi"):
        continue

    if genetic_id in seen_ids:
        raise RuntimeError(f"Duplicate target Genetic ID in annotation: {genetic_id}")
    seen_ids.add(genetic_id)

    clean_group = original_group
    italian_split_status = "Not_applicable"

    if original_group == "Italian_North":
        if genetic_id in italian_map:
            clean_group = italian_map[genetic_id]
            italian_split_status = "Mapped_by_existing_manifest"
        elif locality == "Italy, modern 2":
            clean_group = "Italian_Bergamo_candidate"
            italian_split_status = "Needs_ID_level_confirmation"
        elif locality == "Italy, modern 3":
            clean_group = "Italian_Tuscan_candidate"
            italian_split_status = "Needs_ID_level_confirmation"
        else:
            clean_group = "Italian_North_unresolved"
            italian_split_status = "Needs_locality_review"

    assessment_upper = assessment.upper()

    if "QCREMOVE" in original_group.upper():
        decision = "EXCLUDE"
        reason = "AADR group label explicitly marks QCremove"
    elif genetic_id in known_questionable_ashkenazi or assessment_upper == "QUESTIONABLE":
        decision = "EXCLUDE"
        reason = "Questionable assessment or known Iran-locality Ashkenazi sample"
    elif assessment_upper == "PROVISIONAL_PASS":
        decision = "REVIEW"
        reason = "PROVISIONAL_PASS retained for explicit review before inclusion"
    elif original_group == "Italian_North" and italian_split_status != "Mapped_by_existing_manifest":
        decision = "REVIEW"
        reason = "Italian_North pooling unresolved at individual level"
    elif assessment_upper == "PASS":
        decision = "INCLUDE"
        reason = "Pass assessment and no predefined exclusion"
    else:
        decision = "REVIEW"
        reason = f"Unrecognized assessment category: {assessment}"

    if genetic_id not in ind_ids:
        raise RuntimeError(f"Target annotation ID absent from IND file: {genetic_id}")

    records.append({
        "Genetic_ID": genetic_id,
        "Original_Group": original_group,
        "Clean_Group": clean_group,
        "Locality": locality,
        "Publication": publication,
        "Assessment": assessment,
        "Italian_Split_Status": italian_split_status,
        "Decision": decision,
        "Reason": reason,
    })

fieldnames = [
    "Genetic_ID",
    "Original_Group",
    "Clean_Group",
    "Locality",
    "Publication",
    "Assessment",
    "Italian_Split_Status",
    "Decision",
    "Reason",
]

records.sort(key=lambda item: (item["Clean_Group"], item["Genetic_ID"]))

with review_path.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
    writer.writeheader()
    writer.writerows(records)

included = [record for record in records if record["Decision"] == "INCLUDE"]

with clean_path.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
    writer.writeheader()
    writer.writerows(included)

with ids_path.open("w", encoding="utf-8") as handle:
    for record in included:
        handle.write(record["Genetic_ID"] + "\n")

clean_ashkenazi = [
    record["Genetic_ID"]
    for record in included
    if record["Clean_Group"] == "Jew_Ashkenazi"
]

expected_clean_ashkenazi = {
    "AshkenaziJew5779.HO",
    "AshkenaziJew5782.HO",
    "AshkenaziJew5783.HO",
    "AshkenaziJew5704.HO",
    "AshkenaziJew5728.HO",
    "AshkenaziJew5790.HO",
    "AshkenaziJew5788.HO",
}

if set(clean_ashkenazi) != expected_clean_ashkenazi:
    raise RuntimeError(
        "Clean Ashkenazi set differs from the expected seven Poland-locality Pass samples: "
        + ", ".join(sorted(clean_ashkenazi))
    )

missing_mapped_ids = sorted(set(italian_map) - seen_ids)

print()
print("Completion summary")
print("------------------")
print(f"Target records reviewed: {len(records)}")
print(f"Conservatively included: {len(included)}")
print(f"Awaiting explicit review: {sum(r['Decision'] == 'REVIEW' for r in records)}")
print(f"Excluded: {sum(r['Decision'] == 'EXCLUDE' for r in records)}")
print(f"Clean Ashkenazi samples: {len(clean_ashkenazi)}")
print(f"Italian_North records awaiting split review: {sum(r['Original_Group'] == 'Italian_North' and r['Decision'] == 'REVIEW' for r in records)}")
print(f"Existing Italian mappings loaded: {len(italian_map)}")
print(f"Existing Italian mappings absent from target annotation: {len(missing_mapped_ids)}")

print()
print("Included samples by clean group")
for group, count in sorted(Counter(r["Clean_Group"] for r in included).items()):
    print(f"{group}\t{count}")

print()
print("Review records by group and assessment")
review_counts = Counter(
    (r["Clean_Group"], r["Assessment"])
    for r in records
    if r["Decision"] == "REVIEW"
)
for (group, assessment), count in sorted(review_counts.items()):
    print(f"{group}\t{assessment}\t{count}")

print()
print("Clean Ashkenazi IDs")
for genetic_id in sorted(clean_ashkenazi):
    print(genetic_id)

print()
print(f"Review table: {review_path}")
print(f"Conservative manifest: {clean_path}")
print(f"Included-ID list: {ids_path}")
PY

echo
echo "Log: $log"
echo "Finished: $(date --iso-8601=seconds)"
