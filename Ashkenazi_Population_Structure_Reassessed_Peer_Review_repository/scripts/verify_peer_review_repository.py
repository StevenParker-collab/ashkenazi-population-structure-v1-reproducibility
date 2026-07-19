from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BAD_STEM = "github.com/StevenParker-collab/" + "ashkenazi-population-structure-v1-" + "reprod"
BAD_PATTERNS = [BAD_STEM + suffix for suffix in [")", "]", '"', "'"]]
REQUIRED = [
    "README.md",
    "MANIFEST.csv",
    "SHA256SUMS.txt",
    "manuscript/Ashkenazi_Population_Structure_Reassessed_Peer_Review_Manuscript.pdf",
    "global25_experiments/experiments_08_15/Experiment_10_11_12_Comparison.tsv",
    "global25_experiments/experiments_08_15/Experiment_10_11_12_Distance_Comparison.tsv",
    "global25_experiments/experiments_08_15/Experiment_14_Regional_Grouped_Summary.tsv",
    "global25_experiments/experiments_08_15/Experiment_15_Grouped_Continuity_Summary.tsv",
    "aadr_genotype_stages_01_08/results/pca/analysis/modern_primary_ashkenazi_centroid_distances_pc1_pc10.tsv",
    "aadr_genotype_stages_01_08/results/fst/tables/primary_ashkenazi_hudson_fst.tsv",
    "aadr_genotype_stages_01_08/results/admixture/tables/admixture_cv_summary.tsv",
    "aadr_genotype_stages_01_08/results/synthesis/tables/integrated_comparator_ranking.tsv",
    "review_contract/CLAIM_TRACEABILITY.csv",
    "review_contract/REPRODUCIBILITY_CONTRACT.md",
    "review_contract/RUNBOOK.md",
    "review_contract/DATA_AVAILABILITY.md",
    "review_contract/LIMITATIONS_AND_MODEL_BOUNDARIES.md",
]
FORBIDDEN_SUFFIXES = (".geno", ".bed", ".pgen", ".bcf", ".vcf", ".Q", ".P")


def main() -> int:
    failures = []
    for rel in REQUIRED:
        if not (ROOT / rel).exists():
            failures.append(f"missing required file: {rel}")

    for p in ROOT.rglob("*"):
        if p.is_file() and p.name.endswith(FORBIDDEN_SUFFIXES):
            failures.append(f"forbidden large/raw genotype-style file included: {p.relative_to(ROOT)}")
        if p.is_file() and p.suffix.lower() in {".md", ".txt", ".csv", ".tsv", ".py", ".sh"}:
            if p.resolve() == Path(__file__).resolve():
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for bad in BAD_PATTERNS:
                if bad in text:
                    failures.append(f"broken truncated repo URL found in {p.relative_to(ROOT)}")
                    break

    trace = ROOT / "review_contract" / "CLAIM_TRACEABILITY.csv"
    if trace.exists():
        with trace.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f))
        if len(rows) < 10:
            failures.append("claim traceability table has too few rows")

    if failures:
        print("FAIL")
        for f in failures:
            print("-", f)
        return 1

    print("PASS")
    print("Required files present; no broken truncated GitHub URL found; raw genotype binary exclusions respected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
