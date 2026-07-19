#!/usr/bin/env bash
set -euo pipefail

expected_dir="/home/computer/popgen/projects/ashkenazi_reference_test"
input="v66.p1_compatibility_HO.aadr.patch.PUB.geno"
output="data/eigenstrat/v66.p1_compatibility_HO.aadr.patch.PUB.packed.geno"
stamp="$(date +%Y%m%d_%H%M%S)"

read_genotype_header() {
    python -c 'import re,sys; data=open(sys.argv[1],"rb").read(128); m=re.match(rb"^(T?GENO)\s+(\d+)\s+(\d+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)",data); sys.exit("ERROR: could not parse genotype header: "+sys.argv[1]) if not m else print(" ".join(x.decode("ascii") for x in m.groups()))' "$1"
}

mkdir -p data/eigenstrat logs manifests backups
log="logs/03a_transpose_aadr_genotype_${stamp}.log"
exec > >(tee "$log") 2>&1

echo "Stage 03A: transpose AADR TGENO to standard packed GENO"
echo "Started: $(date --iso-8601=seconds)"
echo "Directory: $(pwd)"
echo "transpose: $(command -v transpose)"

[[ "$(pwd)" == "$expected_dir" ]] || {
    echo "ERROR: expected directory $expected_dir"
    exit 1
}

[[ -s "$input" ]] || {
    echo "ERROR: missing or empty input: $input"
    exit 1
}

command -v transpose >/dev/null || {
    echo "ERROR: transpose is unavailable"
    exit 1
}

input_header="$(read_genotype_header "$input")"
echo "Input header: $input_header"

[[ "$input_header" == TGENO* ]] || {
    echo "ERROR: input does not have a TGENO header"
    exit 1
}

if [[ -s "$output" ]]; then
    output_header="$(read_genotype_header "$output")"

    if [[ "$output_header" == GENO* ]]; then
        echo "Existing valid packed GENO output found; skipping conversion."
    else
        backup="backups/$(basename "$output").invalid_${stamp}"
        mv "$output" "$backup"
        echo "Moved invalid prior output to: $backup"
    fi
fi

if [[ ! -s "$output" ]]; then
    temporary="${output}.partial_${stamp}"
    rm -f "$temporary"

    echo "Running transpose..."
    transpose "$input" "$temporary"

    temporary_header="$(read_genotype_header "$temporary")"
    echo "Temporary output header: $temporary_header"

    [[ "$temporary_header" == GENO* ]] || {
        echo "ERROR: transpose output does not have a GENO header"
        exit 1
    }

    mv "$temporary" "$output"
fi

output_header="$(read_genotype_header "$output")"

python - "$input_header" "$output_header" <<'PY'
import sys

input_fields = sys.argv[1].split()
output_fields = sys.argv[2].split()

if len(input_fields) < 5 or len(output_fields) < 5:
    raise SystemExit("ERROR: incomplete genotype header")

if input_fields[0] != "TGENO":
    raise SystemExit("ERROR: unexpected input format")

if output_fields[0] != "GENO":
    raise SystemExit("ERROR: unexpected output format")

input_individuals = int(input_fields[1])
input_snps = int(input_fields[2])
output_individuals = int(output_fields[1])
output_snps = int(output_fields[2])

if (input_individuals, input_snps) != (output_individuals, output_snps):
    raise SystemExit(
        "ERROR: transposed dimensions differ: "
        f"input={input_individuals}x{input_snps}, "
        f"output={output_individuals}x{output_snps}"
    )

if input_fields[3:] != output_fields[3:]:
    raise SystemExit("ERROR: SNP or individual hashes changed during transpose")

print(f"Verified individuals: {output_individuals}")
print(f"Verified SNPs: {output_snps}")
print("Verified SNP and individual hashes: unchanged")
PY

sha256sum "$input" "$output" > "manifests/03a_transpose_checksums_${stamp}.sha256"

echo
echo "Completion summary"
echo "------------------"
echo "Input size: $(du -h "$input" | cut -f1)"
echo "Output size: $(du -h "$output" | cut -f1)"
echo "Output header: $output_header"
echo "Output file: $output"
echo "Log: $log"
echo "Finished: $(date --iso-8601=seconds)"
