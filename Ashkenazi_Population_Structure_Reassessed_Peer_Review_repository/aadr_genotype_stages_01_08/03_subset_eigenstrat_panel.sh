#!/usr/bin/env bash
set -euo pipefail

expected_dir="/home/computer/popgen/projects/ashkenazi_reference_test"
source_prefix="v66.p1_compatibility_HO.aadr.patch.PUB"
primary_manifest="manifests/modern_panel_primary.tsv"
strict_manifest="manifests/modern_panel_strict_pass.tsv"
stamp="$(date +%Y%m%d_%H%M%S)"

mkdir -p logs manifests params backups data/eigenstrat
log="logs/03_subset_eigenstrat_panel_${stamp}.log"
exec > >(tee "$log") 2>&1

echo "Stage 03: construct exact-ID EIGENSTRAT subsets"
echo "Started: $(date --iso-8601=seconds)"
echo "Directory: $(pwd)"
echo "convertf: $(command -v convertf)"

[[ "$(pwd)" == "$expected_dir" ]] || {
    echo "ERROR: expected directory $expected_dir"
    exit 1
}

for file in \
    "${source_prefix}.geno" \
    "${source_prefix}.snp" \
    "${source_prefix}.ind" \
    "$primary_manifest" \
    "$strict_manifest"
do
    [[ -s "$file" ]] || {
        echo "ERROR: missing or empty input file: $file"
        exit 1
    }
done

command -v convertf >/dev/null || {
    echo "ERROR: convertf is not available"
    exit 1
}

backup_dir="backups/03_subset_eigenstrat_panel_${stamp}"
mkdir -p "$backup_dir"

for file in \
    data/eigenstrat/modern_primary.geno \
    data/eigenstrat/modern_primary.snp \
    data/eigenstrat/modern_primary.ind \
    data/eigenstrat/modern_strict_pass.geno \
    data/eigenstrat/modern_strict_pass.snp \
    data/eigenstrat/modern_strict_pass.ind \
    manifests/modern_primary_relabel_full.ind \
    manifests/modern_primary_poplist.txt \
    manifests/modern_strict_relabel_primary.ind \
    manifests/modern_strict_poplist.txt \
    params/03_convertf_primary.par \
    params/03_convertf_strict_pass.par
do
    [[ -e "$file" ]] && cp -a "$file" "$backup_dir/"
done

workdir="$(mktemp -d "data/eigenstrat/.stage03_${stamp}_XXXXXX")"
trap 'rm -rf "$workdir"' EXIT

python - <<'PY'
import csv
from pathlib import Path

source_ind = Path("v66.p1_compatibility_HO.aadr.patch.PUB.ind")
primary_manifest = Path("manifests/modern_panel_primary.tsv")
strict_manifest = Path("manifests/modern_panel_strict_pass.tsv")
primary_full_ind = Path("manifests/modern_primary_relabel_full.ind")
primary_poplist = Path("manifests/modern_primary_poplist.txt")

def read_manifest(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    mapping = {}
    for row in rows:
        genetic_id = row["Genetic_ID"].strip()
        clean_group = row["Clean_Group"].strip()

        if not genetic_id or not clean_group:
            raise RuntimeError(f"Blank ID or group in {path}")

        if genetic_id in mapping:
            raise RuntimeError(f"Duplicate ID in {path}: {genetic_id}")

        mapping[genetic_id] = clean_group

    return mapping

primary = read_manifest(primary_manifest)
strict = read_manifest(strict_manifest)

if not set(strict).issubset(primary):
    extra = sorted(set(strict) - set(primary))
    raise RuntimeError(
        "Strict manifest contains IDs absent from primary manifest: "
        + ", ".join(extra)
    )

seen = set()
source_count = 0

with source_ind.open(encoding="utf-8-sig") as source, primary_full_ind.open(
    "w", encoding="utf-8"
) as output:
    for line in source:
        fields = line.split()

        if len(fields) < 3:
            continue

        source_count += 1
        genetic_id, sex = fields[0], fields[1]

        if genetic_id in primary:
            clean_group = primary[genetic_id]
            seen.add(genetic_id)
        else:
            clean_group = "__EXCLUDE__"

        output.write(f"{genetic_id}\t{sex}\t{clean_group}\n")

missing = sorted(set(primary) - seen)

if missing:
    raise RuntimeError(
        "Primary manifest IDs absent from source IND: " + ", ".join(missing)
    )

with primary_poplist.open("w", encoding="utf-8") as handle:
    for group in sorted(set(primary.values())):
        handle.write(group + "\n")

print(f"Source IND records: {source_count}")
print(f"Primary manifest IDs verified: {len(primary)}")
print(f"Strict manifest IDs verified as primary subset: {len(strict)}")
print(f"Primary clean populations: {len(set(primary.values()))}")
PY

cat > params/03_convertf_primary.par <<EOF2
genotypename: ${source_prefix}.geno
snpname: ${source_prefix}.snp
indivname: ${PWD}/manifests/modern_primary_relabel_full.ind
poplistname: ${PWD}/manifests/modern_primary_poplist.txt
outputformat: PACKEDANCESTRYMAP
genotypeoutname: ${PWD}/${workdir}/modern_primary.geno
snpoutname: ${PWD}/${workdir}/modern_primary.snp
indivoutname: ${PWD}/${workdir}/modern_primary.ind
familynames: NO
EOF2

echo
echo "Creating primary subset"
convertf -p params/03_convertf_primary.par

python - "$workdir" <<'PY'
import csv
import sys
from pathlib import Path

workdir = Path(sys.argv[1])
manifest_path = Path("manifests/modern_panel_primary.tsv")
ind_path = workdir / "modern_primary.ind"
snp_path = workdir / "modern_primary.snp"
geno_path = workdir / "modern_primary.geno"

with manifest_path.open(encoding="utf-8-sig", newline="") as handle:
    manifest_rows = list(csv.DictReader(handle, delimiter="\t"))

expected = {
    row["Genetic_ID"].strip(): row["Clean_Group"].strip()
    for row in manifest_rows
}

observed = {}

with ind_path.open(encoding="utf-8-sig") as handle:
    for line in handle:
        fields = line.split()

        if len(fields) < 3:
            raise RuntimeError(f"Malformed primary IND row: {line!r}")

        genetic_id = fields[0]
        clean_group = fields[2]

        if genetic_id in observed:
            raise RuntimeError(f"Duplicate output ID: {genetic_id}")

        observed[genetic_id] = clean_group

if observed != expected:
    missing = sorted(set(expected) - set(observed))
    extra = sorted(set(observed) - set(expected))
    wrong = sorted(
        genetic_id
        for genetic_id in set(expected) & set(observed)
        if expected[genetic_id] != observed[genetic_id]
    )
    raise RuntimeError(
        f"Primary output mismatch; missing={missing}, extra={extra}, "
        f"wrong_groups={wrong}"
    )

snp_count = sum(1 for _ in snp_path.open(encoding="utf-8-sig"))

with geno_path.open("rb") as handle:
    header = handle.read(64).split(b"\0", 1)[0].decode("ascii", "replace")

if not header.startswith("TGENO"):
    raise RuntimeError(f"Unexpected primary genotype header: {header!r}")

print(f"Primary output individuals: {len(observed)}")
print(f"Primary output SNPs: {snp_count}")
print(f"Primary genotype header: {header}")
PY

python - "$workdir" <<'PY'
import csv
import sys
from pathlib import Path

workdir = Path(sys.argv[1])
primary_ind = workdir / "modern_primary.ind"
strict_manifest = Path("manifests/modern_panel_strict_pass.tsv")
strict_relabel = Path("manifests/modern_strict_relabel_primary.ind")
strict_poplist = Path("manifests/modern_strict_poplist.txt")

with strict_manifest.open(encoding="utf-8-sig", newline="") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))

strict = {}
for row in rows:
    genetic_id = row["Genetic_ID"].strip()
    clean_group = row["Clean_Group"].strip()

    if genetic_id in strict:
        raise RuntimeError(f"Duplicate strict manifest ID: {genetic_id}")

    strict[genetic_id] = clean_group

seen = set()

with primary_ind.open(encoding="utf-8-sig") as source, strict_relabel.open(
    "w", encoding="utf-8"
) as output:
    for line in source:
        fields = line.split()

        if len(fields) < 3:
            continue

        genetic_id, sex = fields[0], fields[1]

        if genetic_id in strict:
            clean_group = strict[genetic_id]
            seen.add(genetic_id)
        else:
            clean_group = "__EXCLUDE__"

        output.write(f"{genetic_id}\t{sex}\t{clean_group}\n")

missing = sorted(set(strict) - seen)

if missing:
    raise RuntimeError(
        "Strict manifest IDs absent from primary subset: " + ", ".join(missing)
    )

with strict_poplist.open("w", encoding="utf-8") as handle:
    for group in sorted(set(strict.values())):
        handle.write(group + "\n")

print(f"Strict IDs prepared from primary subset: {len(strict)}")
print(f"Strict clean populations: {len(set(strict.values()))}")
PY

cat > params/03_convertf_strict_pass.par <<EOF2
genotypename: ${PWD}/${workdir}/modern_primary.geno
snpname: ${PWD}/${workdir}/modern_primary.snp
indivname: ${PWD}/manifests/modern_strict_relabel_primary.ind
poplistname: ${PWD}/manifests/modern_strict_poplist.txt
outputformat: PACKEDANCESTRYMAP
genotypeoutname: ${PWD}/${workdir}/modern_strict_pass.geno
snpoutname: ${PWD}/${workdir}/modern_strict_pass.snp
indivoutname: ${PWD}/${workdir}/modern_strict_pass.ind
familynames: NO
EOF2

echo
echo "Creating strict Pass-only subset"
convertf -p params/03_convertf_strict_pass.par

python - "$workdir" <<'PY'
import csv
import sys
from pathlib import Path

workdir = Path(sys.argv[1])
manifest_path = Path("manifests/modern_panel_strict_pass.tsv")
ind_path = workdir / "modern_strict_pass.ind"
snp_path = workdir / "modern_strict_pass.snp"
geno_path = workdir / "modern_strict_pass.geno"

with manifest_path.open(encoding="utf-8-sig", newline="") as handle:
    manifest_rows = list(csv.DictReader(handle, delimiter="\t"))

expected = {
    row["Genetic_ID"].strip(): row["Clean_Group"].strip()
    for row in manifest_rows
}

observed = {}

with ind_path.open(encoding="utf-8-sig") as handle:
    for line in handle:
        fields = line.split()

        if len(fields) < 3:
            raise RuntimeError(f"Malformed strict IND row: {line!r}")

        observed[fields[0]] = fields[2]

if observed != expected:
    missing = sorted(set(expected) - set(observed))
    extra = sorted(set(observed) - set(expected))
    wrong = sorted(
        genetic_id
        for genetic_id in set(expected) & set(observed)
        if expected[genetic_id] != observed[genetic_id]
    )
    raise RuntimeError(
        f"Strict output mismatch; missing={missing}, extra={extra}, "
        f"wrong_groups={wrong}"
    )

snp_count = sum(1 for _ in snp_path.open(encoding="utf-8-sig"))

with geno_path.open("rb") as handle:
    header = handle.read(64).split(b"\0", 1)[0].decode("ascii", "replace")

if not header.startswith("TGENO"):
    raise RuntimeError(f"Unexpected strict genotype header: {header!r}")

print(f"Strict output individuals: {len(observed)}")
print(f"Strict output SNPs: {snp_count}")
print(f"Strict genotype header: {header}")
PY

for stem in modern_primary modern_strict_pass; do
    for extension in geno snp ind; do
        destination="data/eigenstrat/${stem}.${extension}"

        if [[ -e "$destination" ]]; then
            cp -a "$destination" "$backup_dir/"
        fi

        mv "${workdir}/${stem}.${extension}" "$destination"
    done
done

sha256sum \
    data/eigenstrat/modern_primary.geno \
    data/eigenstrat/modern_primary.snp \
    data/eigenstrat/modern_primary.ind \
    data/eigenstrat/modern_strict_pass.geno \
    data/eigenstrat/modern_strict_pass.snp \
    data/eigenstrat/modern_strict_pass.ind \
    manifests/modern_primary_relabel_full.ind \
    manifests/modern_primary_poplist.txt \
    manifests/modern_strict_relabel_primary.ind \
    manifests/modern_strict_poplist.txt \
    params/03_convertf_primary.par \
    params/03_convertf_strict_pass.par \
    > "manifests/03_subset_checksums_${stamp}.sha256"

echo
echo "Completion summary"
echo "------------------"
echo "Primary individuals: $(wc -l < data/eigenstrat/modern_primary.ind)"
echo "Primary SNPs: $(wc -l < data/eigenstrat/modern_primary.snp)"
echo "Primary genotype size: $(du -h data/eigenstrat/modern_primary.geno | cut -f1)"
echo "Strict individuals: $(wc -l < data/eigenstrat/modern_strict_pass.ind)"
echo "Strict SNPs: $(wc -l < data/eigenstrat/modern_strict_pass.snp)"
echo "Strict genotype size: $(du -h data/eigenstrat/modern_strict_pass.geno | cut -f1)"
echo "Log: $log"
echo "Finished: $(date --iso-8601=seconds)"
