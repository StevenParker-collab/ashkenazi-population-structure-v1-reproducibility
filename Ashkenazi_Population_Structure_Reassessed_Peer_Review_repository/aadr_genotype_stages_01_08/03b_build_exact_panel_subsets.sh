#!/usr/bin/env bash
set -euo pipefail

expected_dir="/home/computer/popgen/projects/ashkenazi_reference_test"
source_geno="data/eigenstrat/v66.p1_compatibility_HO.aadr.patch.PUB.packed.geno"
source_snp="v66.p1_compatibility_HO.aadr.patch.PUB.snp"
source_ind="v66.p1_compatibility_HO.aadr.patch.PUB.ind"
primary_manifest="manifests/modern_panel_primary.tsv"
strict_manifest="manifests/modern_panel_strict_pass.tsv"
stamp="$(date +%Y%m%d_%H%M%S)"

mkdir -p data/eigenstrat logs params manifests backups
log="logs/03b_build_exact_panel_subsets_${stamp}.log"
exec > >(tee "$log") 2>&1

echo "Stage 03B: build exact-ID primary and strict EIGENSTRAT panels"
echo "Started: $(date --iso-8601=seconds)"
echo "Directory: $(pwd)"

[[ "$(pwd)" == "$expected_dir" ]] || {
    echo "ERROR: expected directory $expected_dir"
    exit 1
}

for file in \
    "$source_geno" \
    "$source_snp" \
    "$source_ind" \
    "$primary_manifest" \
    "$strict_manifest"
do
    [[ -s "$file" ]] || {
        echo "ERROR: missing or empty input: $file"
        exit 1
    }
done

command -v convertf >/dev/null || {
    echo "ERROR: convertf is unavailable"
    exit 1
}

work="$(mktemp -d "data/eigenstrat/.stage03b_${stamp}_XXXXXX")"
backup_dir="backups/03b_build_exact_panel_subsets_${stamp}"
mkdir -p "$backup_dir"

cleanup() {
    rc=$?
    if [[ $rc -eq 0 ]]; then
        rm -rf "$work"
    else
        echo
        echo "Stage 03B failed; diagnostic files retained at: $work"
    fi
}
trap cleanup EXIT

python - "$primary_manifest" "$strict_manifest" "$source_ind" "$work" <<'PY'
import csv
import sys
from pathlib import Path

primary_path = Path(sys.argv[1])
strict_path = Path(sys.argv[2])
source_ind_path = Path(sys.argv[3])
work = Path(sys.argv[4])

required = {"Genetic_ID", "Original_Group", "Clean_Group"}

def read_manifest(path):
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise SystemExit(f"ERROR: missing header in {path}")
        missing = required - set(reader.fieldnames)
        if missing:
            raise SystemExit(
                f"ERROR: {path} lacks required columns: {sorted(missing)}"
            )
        rows = list(reader)

    ids = [row["Genetic_ID"].strip() for row in rows]
    if len(ids) != len(set(ids)):
        raise SystemExit(f"ERROR: duplicate Genetic_ID values in {path}")

    for row in rows:
        for field in required:
            if not row[field].strip():
                raise SystemExit(
                    f"ERROR: blank {field} for a record in {path}"
                )
    return rows

source = {}
with source_ind_path.open() as handle:
    for line_number, raw in enumerate(handle, 1):
        fields = raw.split()
        if len(fields) < 3:
            raise SystemExit(
                f"ERROR: malformed source IND line {line_number}"
            )
        sample_id, sex, population = fields[0], fields[1], fields[2]
        if sample_id in source:
            raise SystemExit(f"ERROR: duplicate source ID: {sample_id}")
        source[sample_id] = (sex, population)

primary = read_manifest(primary_path)
strict = read_manifest(strict_path)

primary_ids = {row["Genetic_ID"].strip() for row in primary}
strict_ids = {row["Genetic_ID"].strip() for row in strict}

if not strict_ids <= primary_ids:
    extra = sorted(strict_ids - primary_ids)
    raise SystemExit(
        "ERROR: strict manifest is not a primary subset: "
        + ", ".join(extra[:20])
    )

for label, rows in (("primary", primary), ("strict", strict)):
    for row in rows:
        sample_id = row["Genetic_ID"].strip()
        original_group = row["Original_Group"].strip()

        if sample_id not in source:
            raise SystemExit(
                f"ERROR: {label} ID absent from source IND: {sample_id}"
            )

        source_group = source[sample_id][1]
        if source_group != original_group:
            raise SystemExit(
                f"ERROR: original-group mismatch for {sample_id}: "
                f"manifest={original_group}, source={source_group}"
            )

populations = sorted(
    {row["Original_Group"].strip() for row in primary}
)

(work / "broad_poplist.txt").write_text(
    "\n".join(populations) + "\n"
)

with (work / "manifest_validation.tsv").open("w") as handle:
    handle.write("Panel\tSamples\tOriginal_Groups\tClean_Groups\n")
    for label, rows in (("primary", primary), ("strict", strict)):
        handle.write(
            f"{label}\t"
            f"{len(rows)}\t"
            f"{len({r['Original_Group'].strip() for r in rows})}\t"
            f"{len({r['Clean_Group'].strip() for r in rows})}\n"
        )

print(f"Source IND records: {len(source)}")
print(f"Primary manifest IDs verified: {len(primary)}")
print(f"Strict manifest IDs verified: {len(strict)}")
print(f"Broad original populations: {len(populations)}")
PY

broad_par="params/03b_convertf_broad_${stamp}.par"

cat > "$broad_par" <<PAR
genotypename: $PWD/$source_geno
snpname: $PWD/$source_snp
indivname: $PWD/$source_ind
poplistname: $PWD/$work/broad_poplist.txt
outputformat: EIGENSTRAT
genotypeoutname: $PWD/$work/broad.geno
snpoutname: $PWD/$work/broad.snp
indivoutname: $PWD/$work/broad.ind
familynames: NO
PAR

echo
echo "Decoding relevant original populations"
convertf -p "$broad_par"

[[ -s "$work/broad.geno" ]] || {
    echo "ERROR: broad EIGENSTRAT genotype output is missing"
    exit 1
}

[[ -s "$work/broad.snp" ]] || {
    echo "ERROR: broad SNP output is missing"
    exit 1
}

[[ -s "$work/broad.ind" ]] || {
    echo "ERROR: broad IND output is missing"
    exit 1
}

python - \
    "$primary_manifest" \
    "$strict_manifest" \
    "$work/broad.ind" \
    "$work/broad.geno" \
    "$work/broad.snp" \
    "$work" <<'PY'
import csv
import sys
from pathlib import Path

primary_path = Path(sys.argv[1])
strict_path = Path(sys.argv[2])
broad_ind_path = Path(sys.argv[3])
broad_geno_path = Path(sys.argv[4])
broad_snp_path = Path(sys.argv[5])
work = Path(sys.argv[6])

def read_manifest(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))

individuals = []
id_to_index = {}

with broad_ind_path.open() as handle:
    for raw in handle:
        fields = raw.split()
        if len(fields) < 3:
            raise SystemExit("ERROR: malformed broad IND record")
        sample_id, sex, population = fields[0], fields[1], fields[2]
        if sample_id in id_to_index:
            raise SystemExit(f"ERROR: duplicate broad ID: {sample_id}")
        id_to_index[sample_id] = len(individuals)
        individuals.append((sample_id, sex, population))

snp_count = sum(1 for _ in broad_snp_path.open())

panels = {
    "primary_text": read_manifest(primary_path),
    "strict_text": read_manifest(strict_path),
}

panel_indices = {}

for panel, rows in panels.items():
    missing = [
        row["Genetic_ID"].strip()
        for row in rows
        if row["Genetic_ID"].strip() not in id_to_index
    ]
    if missing:
        raise SystemExit(
            f"ERROR: {panel} IDs missing after broad extraction: "
            + ", ".join(missing[:20])
        )

    indices = [
        id_to_index[row["Genetic_ID"].strip()]
        for row in rows
    ]
    panel_indices[panel] = indices

    with (work / f"{panel}.ind").open("w") as handle:
        for row in rows:
            sample_id = row["Genetic_ID"].strip()
            clean_group = row["Clean_Group"].strip()
            sex = individuals[id_to_index[sample_id]][1]
            handle.write(f"{sample_id:>24} {sex} {clean_group}\n")

outputs = {
    panel: (work / f"{panel}.geno").open("w")
    for panel in panels
}

try:
    observed_snps = 0

    with broad_geno_path.open() as source:
        for observed_snps, raw in enumerate(source, 1):
            genotype = raw.rstrip("\r\n")

            if len(genotype) != len(individuals):
                raise SystemExit(
                    f"ERROR: broad genotype row {observed_snps} has "
                    f"length {len(genotype)}, expected {len(individuals)}"
                )

            for panel, indices in panel_indices.items():
                outputs[panel].write(
                    "".join(genotype[index] for index in indices) + "\n"
                )
finally:
    for handle in outputs.values():
        handle.close()

if observed_snps != snp_count:
    raise SystemExit(
        f"ERROR: genotype/SNP count mismatch: "
        f"geno={observed_snps}, snp={snp_count}"
    )

print(f"Broad extracted individuals: {len(individuals)}")
print(f"Broad SNPs: {snp_count}")
print(f"Primary exact genotype columns: {len(panels['primary_text'])}")
print(f"Strict exact genotype columns: {len(panels['strict_text'])}")
PY

for panel in primary strict_pass
do
    if [[ "$panel" == "primary" ]]; then
        text_stem="primary_text"
        expected_individuals=369
    else
        text_stem="strict_text"
        expected_individuals=247
    fi

    par="params/03b_convertf_${panel}_${stamp}.par"

    cat > "$par" <<PAR
genotypename: $PWD/$work/${text_stem}.geno
snpname: $PWD/$work/broad.snp
indivname: $PWD/$work/${text_stem}.ind
outputformat: PACKEDANCESTRYMAP
genotypeoutname: $PWD/$work/modern_${panel}.geno
snpoutname: $PWD/$work/modern_${panel}.snp
indivoutname: $PWD/$work/modern_${panel}.ind
familynames: NO
PAR

    echo
    echo "Packing modern_${panel}"
    convertf -p "$par"

    for extension in geno snp ind
    do
        [[ -s "$work/modern_${panel}.${extension}" ]] || {
            echo "ERROR: missing modern_${panel}.${extension}"
            exit 1
        }
    done

    actual_individuals="$(wc -l < "$work/modern_${panel}.ind")"
    actual_snps="$(wc -l < "$work/modern_${panel}.snp")"

    [[ "$actual_individuals" -eq "$expected_individuals" ]] || {
        echo "ERROR: modern_${panel} has $actual_individuals individuals; expected $expected_individuals"
        exit 1
    }

    [[ "$actual_snps" -eq 276725 ]] || {
        echo "ERROR: modern_${panel} has $actual_snps SNPs; expected 276725"
        exit 1
    }

    python - "$work/modern_${panel}.geno" "$expected_individuals" "$actual_snps" <<'PY'
import re
import sys

path = sys.argv[1]
expected_individuals = int(sys.argv[2])
expected_snps = int(sys.argv[3])

data = open(path, "rb").read(128)
match = re.match(
    rb"^GENO\s+(\d+)\s+(\d+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)",
    data,
)

if not match:
    raise SystemExit(f"ERROR: invalid packed GENO header: {path}")

individuals = int(match.group(1))
snps = int(match.group(2))

if individuals != expected_individuals or snps != expected_snps:
    raise SystemExit(
        f"ERROR: packed header mismatch for {path}: "
        f"{individuals} individuals, {snps} SNPs"
    )

print(
    f"Verified packed header: {individuals} individuals, "
    f"{snps} SNPs"
)
PY
done

for panel in primary strict_pass
do
    for extension in geno snp ind
    do
        destination="data/eigenstrat/modern_${panel}.${extension}"

        if [[ -e "$destination" ]]; then
            mv "$destination" "$backup_dir/"
        fi

        mv "$work/modern_${panel}.${extension}" "$destination"
    done
done

cp "$work/broad_poplist.txt" \
    "manifests/modern_panel_original_populations.txt"

cp "$work/manifest_validation.tsv" \
    "manifests/03b_manifest_validation_${stamp}.tsv"

sha256sum \
    data/eigenstrat/modern_primary.geno \
    data/eigenstrat/modern_primary.snp \
    data/eigenstrat/modern_primary.ind \
    data/eigenstrat/modern_strict_pass.geno \
    data/eigenstrat/modern_strict_pass.snp \
    data/eigenstrat/modern_strict_pass.ind \
    > "manifests/03b_panel_checksums_${stamp}.sha256"

echo
echo "Completion summary"
echo "------------------"
echo "Primary individuals: $(wc -l < data/eigenstrat/modern_primary.ind)"
echo "Primary SNPs: $(wc -l < data/eigenstrat/modern_primary.snp)"
echo "Strict individuals: $(wc -l < data/eigenstrat/modern_strict_pass.ind)"
echo "Strict SNPs: $(wc -l < data/eigenstrat/modern_strict_pass.snp)"
echo "Primary populations: $(awk '{print $3}' data/eigenstrat/modern_primary.ind | sort -u | wc -l)"
echo "Strict populations: $(awk '{print $3}' data/eigenstrat/modern_strict_pass.ind | sort -u | wc -l)"
echo "Log: $log"
echo "Finished: $(date --iso-8601=seconds)"
