#!/usr/bin/env bash
set -euo pipefail

expected_dir="/home/computer/popgen/projects/ashkenazi_reference_test"
stamp="$(date +%Y%m%d_%H%M%S)"

mkdir -p data/plink logs params manifests backups
log="logs/04a_convert_panels_to_plink_${stamp}.log"
exec > >(tee "$log") 2>&1

echo "Stage 04A: convert exact EIGENSTRAT panels to PLINK BED"
echo "Started: $(date --iso-8601=seconds)"
echo "Directory: $(pwd)"
echo "convertf: $(command -v convertf)"
echo "plink: $(command -v plink)"

[[ "$(pwd)" == "$expected_dir" ]] || {
    echo "ERROR: expected directory $expected_dir"
    exit 1
}

command -v convertf >/dev/null || {
    echo "ERROR: convertf is unavailable"
    exit 1
}

command -v plink >/dev/null || {
    echo "ERROR: plink is unavailable"
    exit 1
}

backup_dir="backups/04a_convert_panels_to_plink_${stamp}"
mkdir -p "$backup_dir"

for panel in primary strict_pass
do
    source="data/eigenstrat/modern_${panel}"
    output="data/plink/modern_${panel}"
    work="data/plink/.modern_${panel}_${stamp}"

    for extension in geno snp ind
    do
        [[ -s "${source}.${extension}" ]] || {
            echo "ERROR: missing ${source}.${extension}"
            exit 1
        }
    done

    for extension in bed bim fam
    do
        if [[ -e "${output}.${extension}" ]]; then
            mv "${output}.${extension}" "$backup_dir/"
        fi
    done

    par="params/04a_convert_${panel}_${stamp}.par"

    cat > "$par" <<PAR
genotypename: $PWD/${source}.geno
snpname: $PWD/${source}.snp
indivname: $PWD/${source}.ind
outputformat: PACKEDPED
genotypeoutname: $PWD/${work}.bed
snpoutname: $PWD/${work}.bim
indivoutname: $PWD/${work}.fam
familynames: NO
PAR

    echo
    echo "Converting modern_${panel}"
    convertf -p "$par"

    for extension in bed bim fam
    do
        [[ -s "${work}.${extension}" ]] || {
            echo "ERROR: convertf did not create ${work}.${extension}"
            exit 1
        }
    done

    mv "${work}.bed" "${output}.bed"
    mv "${work}.bim" "${output}.bim"
    mv "${work}.fam" "${output}.fam"

    plink \
        --bfile "$output" \
        --freq counts \
        --missing \
        --out "data/plink/modern_${panel}_audit"

    expected_individuals="$(
        case "$panel" in
            primary) echo 369 ;;
            strict_pass) echo 247 ;;
        esac
    )"

    observed_individuals="$(wc -l < "${output}.fam")"
    observed_snps="$(wc -l < "${output}.bim")"

    [[ "$observed_individuals" -eq "$expected_individuals" ]] || {
        echo "ERROR: ${panel} PLINK sample count is $observed_individuals; expected $expected_individuals"
        exit 1
    }

    [[ "$observed_snps" -eq 276725 ]] || {
        echo "ERROR: ${panel} PLINK SNP count is $observed_snps; expected 276725"
        exit 1
    }

    echo "Verified modern_${panel}: $observed_individuals individuals, $observed_snps SNPs"
done

sha256sum \
    data/plink/modern_primary.bed \
    data/plink/modern_primary.bim \
    data/plink/modern_primary.fam \
    data/plink/modern_strict_pass.bed \
    data/plink/modern_strict_pass.bim \
    data/plink/modern_strict_pass.fam \
    > "manifests/04a_plink_checksums_${stamp}.sha256"

echo
echo "Completion summary"
echo "------------------"
echo "Primary: $(wc -l < data/plink/modern_primary.fam) individuals, $(wc -l < data/plink/modern_primary.bim) SNPs"
echo "Strict: $(wc -l < data/plink/modern_strict_pass.fam) individuals, $(wc -l < data/plink/modern_strict_pass.bim) SNPs"
echo "Primary missingness: data/plink/modern_primary_audit.imiss and .lmiss"
echo "Strict missingness: data/plink/modern_strict_pass_audit.imiss and .lmiss"
echo "Log: $log"
echo "Finished: $(date --iso-8601=seconds)"
