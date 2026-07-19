#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

try:
    import numpy as np
except ImportError as exc:
    raise SystemExit(
        "ERROR: NumPy is required. Run this script with "
        "/home/computer/miniconda3/envs/pca-tools/bin/python"
    ) from exc

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError as exc:
    raise SystemExit(
        "ERROR: Matplotlib is required. Run this script with "
        "/home/computer/miniconda3/envs/pca-tools/bin/python"
    ) from exc


ROOT = Path("/home/computer/popgen/projects/ashkenazi_reference_test")
PLINK = Path("/home/computer/miniconda3/envs/popgen/bin/plink")
PCA_PYTHON = Path("/home/computer/miniconda3/envs/pca-tools/bin/python")
OUT = ROOT / "results" / "fst"
WORK = OUT / "work"
FREQ_DIR = OUT / "stratified_frequencies"
WC_DIR = OUT / "weir_cockerham_validation"
FIG_DIR = OUT / "figures"
TABLE_DIR = OUT / "tables"
LOG_DIR = OUT / "logs"
LOCK_FILE = OUT / ".stage06.lock"
COMPLETE_FLAG = OUT / "stage06_complete.json"
EXPECTED_SHARED_SNPS = 184_385
EXPECTED_POPULATIONS = 18
EXPECTED_PAIR_COUNT = EXPECTED_POPULATIONS * (EXPECTED_POPULATIONS - 1) // 2
EXCLUDED_AJ_IDS = {"YZ024.HO", "AshkenaziJew5780.HO", "AshkenaziJew5775.HO"}

PANEL_SPECS = {
    "primary": {
        "bfile": ROOT / "data" / "plink" / "modern_primary",
        "manifest": ROOT / "manifests" / "modern_panel_primary.tsv",
        "expected_samples": 369,
    },
    "strict_pass": {
        "bfile": ROOT / "data" / "plink" / "modern_strict_pass",
        "manifest": ROOT / "manifests" / "modern_panel_strict_pass.tsv",
        "expected_samples": 247,
    },
}

SHARED_SNPS = ROOT / "manifests" / "pca_admixture_shared_qc_snps.txt"
STAGE05_SUMMARY = ROOT / "results" / "pca" / "analysis" / "pca_analysis_summary.txt"
STAGE05_DIR = ROOT / "results" / "pca" / "analysis"


@dataclass(frozen=True)
class Sample:
    fid: str
    iid: str
    population: str


@dataclass
class PanelData:
    name: str
    bfile: Path
    manifest: Path
    samples: list[Sample]
    populations: list[str]
    ashkenazi_population: str
    pop_to_code: dict[str, str]
    code_to_pop: dict[str, str]
    cluster_file: Path
    count_file: Path


class StageLock:
    def __init__(self, path: Path) -> None:
        self.path = path

    def __enter__(self) -> "StageLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            content = self.path.read_text(encoding="utf-8", errors="replace").strip()
            raise SystemExit(
                f"ERROR: Stage 06 lock already exists: {self.path}\n"
                f"Lock content: {content}\n"
                "Remove it only if no Stage 06 process is running."
            )
        self.path.write_text(
            json.dumps(
                {
                    "pid": os.getpid(),
                    "started_utc": datetime.now(timezone.utc).isoformat(),
                    "host": os.uname().nodename if hasattr(os, "uname") else "unknown",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        try:
            self.path.unlink(missing_ok=True)
        except Exception:
            pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Stage 06: inspect Stage 05, calculate genome-wide pairwise Hudson FST "
            "for primary and strict panels on the shared post-QC SNP set, run "
            "Ashkenazi-focused PLINK Weir-Cockerham validation, and generate tables, "
            "figures, and a manuscript-ready summary."
        )
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recompute PLINK outputs even when resumable outputs already exist.",
    )
    parser.add_argument(
        "--skip-wc",
        action="store_true",
        help="Skip Ashkenazi-focused PLINK Weir-Cockerham validation.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=min(4, max(1, os.cpu_count() or 1)),
        help="Concurrent PLINK jobs for Weir-Cockerham validation (default: up to 4).",
    )
    parser.add_argument(
        "--drop-wc-variant-files",
        action="store_true",
        help="Delete large per-variant .fst files after validated global estimates are parsed.",
    )
    return parser.parse_args()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_file(path: Path, label: str | None = None) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise SystemExit(f"ERROR: missing or empty {label or 'required file'}: {path}")


def require_bfile(prefix: Path) -> None:
    for ext in (".bed", ".bim", ".fam"):
        require_file(Path(str(prefix) + ext), f"PLINK {ext} file")


def sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(chunk_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def count_nonempty_lines(path: Path) -> int:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return sum(1 for line in handle if line.strip())


def natural_key(value: str) -> tuple[Any, ...]:
    return tuple(int(piece) if piece.isdigit() else piece.lower() for piece in re.split(r"(\d+)", value))


def resolve_column(fieldnames: Sequence[str], candidates: Sequence[str], label: str) -> str:
    normalized = {name.strip().lower(): name for name in fieldnames}
    for candidate in candidates:
        hit = normalized.get(candidate.strip().lower())
        if hit:
            return hit
    raise SystemExit(
        f"ERROR: could not locate {label} column. Available columns: {list(fieldnames)}"
    )


def read_manifest(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = reader.fieldnames or []
        if not fields:
            raise SystemExit(f"ERROR: manifest has no header: {path}")
        id_col = resolve_column(
            fields,
            ["Genetic_ID", "Genetic ID", "IID", "Sample_ID", "Sample ID", "ID"],
            "sample ID",
        )
        pop_col = resolve_column(
            fields,
            ["Clean_Group", "Clean Group", "Population", "Group", "Pop"],
            "population",
        )
        result: dict[str, str] = {}
        for row_number, row in enumerate(reader, start=2):
            iid = (row.get(id_col) or "").strip()
            pop = (row.get(pop_col) or "").strip()
            if not iid:
                continue
            if not pop:
                raise SystemExit(
                    f"ERROR: blank population for {iid} at {path}:{row_number}"
                )
            if iid in result:
                raise SystemExit(f"ERROR: duplicate manifest IID {iid}: {path}")
            result[iid] = pop
    return result


def read_fam(path: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    seen_iids: set[str] = set()
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            fields = line.split()
            if len(fields) < 2:
                raise SystemExit(f"ERROR: malformed FAM row {path}:{line_number}")
            fid, iid = fields[0], fields[1]
            if iid in seen_iids:
                raise SystemExit(
                    f"ERROR: duplicate IID {iid} in FAM. Stage 06 requires unique IIDs: {path}"
                )
            seen_iids.add(iid)
            rows.append((fid, iid))
    return rows


def detect_ashkenazi_population(populations: Sequence[str]) -> str:
    exact_priority = [
        "Ashkenazi",
        "Ashkenazi_Jew",
        "AshkenaziJew",
        "Jew_Ashkenazi",
        "Ashkenazi_Germany",
        "Ashkenazi_Poland",
    ]
    lowered = {p.lower(): p for p in populations}
    for name in exact_priority:
        if name.lower() in lowered:
            return lowered[name.lower()]
    candidates = [p for p in populations if "ashken" in p.lower()]
    if len(candidates) == 1:
        return candidates[0]
    raise SystemExit(
        "ERROR: could not uniquely identify the Ashkenazi population label. "
        f"Candidates: {candidates}; all populations: {list(populations)}"
    )


def prepare_directories() -> None:
    for path in (OUT, WORK, FREQ_DIR, WC_DIR, FIG_DIR, TABLE_DIR, LOG_DIR):
        path.mkdir(parents=True, exist_ok=True)


def inspect_stage05() -> None:
    require_file(STAGE05_SUMMARY, "Stage 05 summary")
    print("\n===== Stage 05 PCA summary (inspection requested in handoff) =====")
    print(STAGE05_SUMMARY.read_text(encoding="utf-8", errors="replace").rstrip())
    print("\n===== Generated Stage 05 PCA files =====")
    files = sorted((p for p in STAGE05_DIR.iterdir() if p.is_file()), key=lambda p: p.name)
    for path in files:
        print(path.name)
    if len(files) < 10:
        raise SystemExit(
            f"ERROR: Stage 05 analysis directory contains unexpectedly few files ({len(files)})."
        )


def validate_shared_snps() -> tuple[list[str], set[str]]:
    require_file(SHARED_SNPS, "shared post-QC SNP list")
    snps: list[str] = []
    seen: set[str] = set()
    with SHARED_SNPS.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            value = line.strip().split()[0] if line.strip() else ""
            if not value:
                continue
            if value in seen:
                raise SystemExit(
                    f"ERROR: duplicate SNP {value} in {SHARED_SNPS}:{line_number}"
                )
            seen.add(value)
            snps.append(value)
    if len(snps) != EXPECTED_SHARED_SNPS:
        raise SystemExit(
            f"ERROR: shared SNP count is {len(snps):,}; expected {EXPECTED_SHARED_SNPS:,}."
        )
    return snps, seen


def validate_bim(prefix: Path, shared_snp_set: set[str]) -> tuple[int, set[str]]:
    bim = Path(str(prefix) + ".bim")
    ids: set[str] = set()
    count = 0
    with bim.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            fields = line.split()
            if len(fields) < 6:
                raise SystemExit(f"ERROR: malformed BIM row {bim}:{line_number}")
            snp = fields[1]
            if snp in ids:
                raise SystemExit(f"ERROR: duplicate BIM SNP {snp}: {bim}")
            ids.add(snp)
            count += 1
    missing = shared_snp_set - ids
    if missing:
        raise SystemExit(
            f"ERROR: {len(missing):,} shared-QC SNPs are absent from {bim}; "
            f"examples: {sorted(missing)[:10]}"
        )
    return count, ids


def write_tsv(path: Path, header: Sequence[str], rows: Iterable[Sequence[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)
    temp.replace(path)


def build_panel_data(panel_name: str, spec: dict[str, Any]) -> PanelData:
    bfile = Path(spec["bfile"])
    manifest_path = Path(spec["manifest"])
    require_bfile(bfile)
    require_file(manifest_path, f"{panel_name} manifest")
    manifest = read_manifest(manifest_path)
    fam_rows = read_fam(Path(str(bfile) + ".fam"))
    fam_iids = {iid for _, iid in fam_rows}
    manifest_iids = set(manifest)
    if fam_iids != manifest_iids:
        missing_manifest = sorted(fam_iids - manifest_iids)
        missing_fam = sorted(manifest_iids - fam_iids)
        raise SystemExit(
            f"ERROR: {panel_name} FAM/manifest ID mismatch. "
            f"Missing from manifest: {missing_manifest[:10]}; "
            f"missing from FAM: {missing_fam[:10]}"
        )
    samples = [Sample(fid=fid, iid=iid, population=manifest[iid]) for fid, iid in fam_rows]
    expected_samples = int(spec["expected_samples"])
    if len(samples) != expected_samples:
        raise SystemExit(
            f"ERROR: {panel_name} contains {len(samples)} samples; expected {expected_samples}."
        )
    excluded_present = EXCLUDED_AJ_IDS & fam_iids
    if excluded_present:
        raise SystemExit(
            f"ERROR: excluded Ashkenazi IDs present in {panel_name}: {sorted(excluded_present)}"
        )
    populations = sorted({sample.population for sample in samples}, key=natural_key)
    if len(populations) != EXPECTED_POPULATIONS:
        raise SystemExit(
            f"ERROR: {panel_name} contains {len(populations)} populations; "
            f"expected {EXPECTED_POPULATIONS}. Populations: {populations}"
        )
    counts = {pop: sum(s.population == pop for s in samples) for pop in populations}
    too_small = {pop: n for pop, n in counts.items() if n < 2}
    if too_small:
        raise SystemExit(
            f"ERROR: FST requires at least two samples per population; too small: {too_small}"
        )
    ashkenazi = detect_ashkenazi_population(populations)
    pop_to_code = {pop: f"P{index:03d}" for index, pop in enumerate(populations, start=1)}
    code_to_pop = {code: pop for pop, code in pop_to_code.items()}
    cluster_file = WORK / f"{panel_name}.within.tsv"
    count_file = TABLE_DIR / f"{panel_name}_population_counts.tsv"
    write_tsv(
        cluster_file,
        [],
        [],
    )
    # --within files must not have a header, so overwrite atomically without one.
    temp = cluster_file.with_suffix(cluster_file.suffix + ".tmp")
    with temp.open("w", encoding="utf-8", newline="") as handle:
        for sample in samples:
            handle.write(f"{sample.fid}\t{sample.iid}\t{pop_to_code[sample.population]}\n")
    temp.replace(cluster_file)
    write_tsv(
        count_file,
        ["Panel", "Population", "PLINK_cluster_code", "N_samples"],
        [
            [panel_name, pop, pop_to_code[pop], counts[pop]]
            for pop in populations
        ],
    )
    return PanelData(
        name=panel_name,
        bfile=bfile,
        manifest=manifest_path,
        samples=samples,
        populations=populations,
        ashkenazi_population=ashkenazi,
        pop_to_code=pop_to_code,
        code_to_pop=code_to_pop,
        cluster_file=cluster_file,
        count_file=count_file,
    )


def run_command(
    cmd: Sequence[str],
    console_log: Path,
    cwd: Path | None = None,
    echo: bool = True,
) -> None:
    console_log.parent.mkdir(parents=True, exist_ok=True)
    if echo:
        print("Running:", " ".join(cmd))
    with console_log.open("w", encoding="utf-8") as handle:
        handle.write("COMMAND\n")
        handle.write(" ".join(cmd) + "\n\nOUTPUT\n")
        handle.flush()
        result = subprocess.run(
            list(cmd),
            cwd=str(cwd) if cwd else None,
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    if result.returncode != 0:
        tail = tail_text(console_log, 50)
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}: {' '.join(cmd)}\n"
            f"Last output lines:\n{tail}"
        )


def tail_text(path: Path, n: int = 30) -> str:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-n:])


def get_plink_version() -> str:
    result = subprocess.run(
        [str(PLINK), "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"ERROR: PLINK --version failed: {result.stdout}")
    return result.stdout.strip()


def run_stratified_frequencies(panel: PanelData, force: bool) -> Path:
    out_prefix = FREQ_DIR / f"{panel.name}_shared_qc"
    frq = Path(str(out_prefix) + ".frq.strat")
    log = Path(str(out_prefix) + ".log")
    if not force and frq.is_file() and frq.stat().st_size > 0 and log.is_file():
        log_text = log.read_text(encoding="utf-8", errors="replace")
        if "Analysis finished" in log_text or "End time:" in log_text:
            print(f"Resuming: using existing stratified frequency file for {panel.name}: {frq}")
            return frq
    cmd = [
        str(PLINK),
        "--bfile", str(panel.bfile),
        "--extract", str(SHARED_SNPS),
        "--within", str(panel.cluster_file),
        "--freq",
        "--keep-allele-order",
        "--nonfounders",
        "--threads", "1",
        "--out", str(out_prefix),
    ]
    run_command(cmd, LOG_DIR / f"{panel.name}_frequency_console.txt")
    require_file(frq, f"{panel.name} stratified frequency report")
    require_file(log, f"{panel.name} PLINK frequency log")
    return frq


def iter_snp_groups(frq_path: Path) -> Iterator[tuple[str, str, list[dict[str, str]]]]:
    with frq_path.open("r", encoding="utf-8", errors="replace") as handle:
        header_line = handle.readline()
        if not header_line:
            raise SystemExit(f"ERROR: empty frequency file: {frq_path}")
        header = header_line.split()
        required = {"CHR", "SNP", "CLST", "A1", "A2", "MAC", "NCHROBS"}
        missing = required - set(header)
        if missing:
            raise SystemExit(
                f"ERROR: {frq_path} missing required columns {sorted(missing)}. Header: {header}"
            )
        index = {name: header.index(name) for name in header}
        current_key: tuple[str, str] | None = None
        rows: list[dict[str, str]] = []
        for line_number, line in enumerate(handle, start=2):
            if not line.strip():
                continue
            fields = line.split()
            if len(fields) < len(header):
                raise SystemExit(f"ERROR: malformed row {frq_path}:{line_number}")
            chrom = fields[index["CHR"]]
            snp = fields[index["SNP"]]
            key = (chrom, snp)
            row = {name: fields[position] for name, position in index.items()}
            if current_key is None:
                current_key = key
            if key != current_key:
                assert current_key is not None
                yield current_key[0], current_key[1], rows
                current_key = key
                rows = []
            rows.append(row)
        if current_key is not None:
            yield current_key[0], current_key[1], rows


def safe_float(value: str) -> float:
    try:
        return float(value)
    except ValueError:
        return math.nan


def compute_hudson_pairwise(
    panel: PanelData,
    frq_path: Path,
    expected_snp_set: set[str],
) -> list[dict[str, Any]]:
    populations = panel.populations
    pop_index = {pop: i for i, pop in enumerate(populations)}
    pair_i: list[int] = []
    pair_j: list[int] = []
    pair_names: list[tuple[str, str]] = []
    for i, j in itertools.combinations(range(len(populations)), 2):
        pair_i.append(i)
        pair_j.append(j)
        pair_names.append((populations[i], populations[j]))
    pair_i_arr = np.asarray(pair_i, dtype=np.int16)
    pair_j_arr = np.asarray(pair_j, dtype=np.int16)
    n_pairs = len(pair_names)
    sum_num = np.zeros(n_pairs, dtype=np.float64)
    sum_den = np.zeros(n_pairs, dtype=np.float64)
    n_used = np.zeros(n_pairs, dtype=np.int64)
    n_negative_num = np.zeros(n_pairs, dtype=np.int64)
    chrom_num: dict[str, np.ndarray] = {}
    chrom_den: dict[str, np.ndarray] = {}
    chrom_n: dict[str, np.ndarray] = {}
    observed_snps: set[str] = set()
    n_groups = 0
    allele_mismatch_count = 0
    missing_cluster_rows = 0

    print(f"Calculating pairwise Hudson FST for {panel.name} from {frq_path.name}...")
    for chrom, snp, rows in iter_snp_groups(frq_path):
        n_groups += 1
        if snp in observed_snps:
            raise SystemExit(f"ERROR: duplicate SNP group {snp} in {frq_path}")
        observed_snps.add(snp)
        if snp not in expected_snp_set:
            raise SystemExit(f"ERROR: unexpected SNP {snp} in {frq_path}")
        allele_pairs = {(row["A1"], row["A2"]) for row in rows}
        if len(allele_pairs) > 1:
            allele_mismatch_count += 1
            raise SystemExit(
                f"ERROR: allele coding differs among clusters for SNP {snp}: {allele_pairs}"
            )
        p = np.full(len(populations), np.nan, dtype=np.float64)
        nchrom = np.zeros(len(populations), dtype=np.float64)
        seen_codes: set[str] = set()
        for row in rows:
            code = row["CLST"]
            if code in seen_codes:
                raise SystemExit(
                    f"ERROR: duplicate cluster {code} for SNP {snp} in {frq_path}"
                )
            seen_codes.add(code)
            pop = panel.code_to_pop.get(code)
            if pop is None:
                raise SystemExit(
                    f"ERROR: unknown cluster code {code} in {frq_path}; expected {panel.code_to_pop}"
                )
            idx = pop_index[pop]
            mac = safe_float(row["MAC"])
            nobs = safe_float(row["NCHROBS"])
            if math.isfinite(mac) and math.isfinite(nobs) and nobs > 1:
                if mac < 0 or mac > nobs:
                    raise SystemExit(
                        f"ERROR: invalid allele count at {panel.name} {snp} {pop}: MAC={mac}, NCHROBS={nobs}"
                    )
                p[idx] = mac / nobs
                nchrom[idx] = nobs
        if len(seen_codes) != len(populations):
            missing_cluster_rows += len(populations) - len(seen_codes)

        p1 = p[pair_i_arr]
        p2 = p[pair_j_arr]
        n1 = nchrom[pair_i_arr]
        n2 = nchrom[pair_j_arr]
        valid = np.isfinite(p1) & np.isfinite(p2) & (n1 > 1) & (n2 > 1)
        if not np.any(valid):
            continue
        num = np.zeros(n_pairs, dtype=np.float64)
        den = np.zeros(n_pairs, dtype=np.float64)
        num[valid] = (
            (p1[valid] - p2[valid]) ** 2
            - p1[valid] * (1.0 - p1[valid]) / (n1[valid] - 1.0)
            - p2[valid] * (1.0 - p2[valid]) / (n2[valid] - 1.0)
        )
        den[valid] = (
            p1[valid] * (1.0 - p2[valid])
            + p2[valid] * (1.0 - p1[valid])
        )
        usable = valid & np.isfinite(num) & np.isfinite(den) & (den > 0)
        sum_num[usable] += num[usable]
        sum_den[usable] += den[usable]
        n_used[usable] += 1
        n_negative_num[usable] += num[usable] < 0
        if chrom not in chrom_num:
            chrom_num[chrom] = np.zeros(n_pairs, dtype=np.float64)
            chrom_den[chrom] = np.zeros(n_pairs, dtype=np.float64)
            chrom_n[chrom] = np.zeros(n_pairs, dtype=np.int64)
        chrom_num[chrom][usable] += num[usable]
        chrom_den[chrom][usable] += den[usable]
        chrom_n[chrom][usable] += 1

        if n_groups % 25_000 == 0:
            print(f"  {panel.name}: processed {n_groups:,} SNPs")

    missing_snps = expected_snp_set - observed_snps
    if missing_snps:
        raise SystemExit(
            f"ERROR: {panel.name} frequency report is missing {len(missing_snps):,} shared SNPs; "
            f"examples: {sorted(missing_snps)[:10]}"
        )
    if n_groups != EXPECTED_SHARED_SNPS:
        raise SystemExit(
            f"ERROR: {panel.name} frequency report contains {n_groups:,} SNP groups; "
            f"expected {EXPECTED_SHARED_SNPS:,}."
        )
    if allele_mismatch_count:
        raise SystemExit(f"ERROR: {allele_mismatch_count} SNPs had allele mismatches.")

    chroms = sorted(chrom_num, key=natural_key)
    if chroms != [str(i) for i in range(1, 23)]:
        raise SystemExit(
            f"ERROR: expected autosomes 1-22 in {panel.name} frequency report; found {chroms}"
        )

    results: list[dict[str, Any]] = []
    for pair_index, (pop1, pop2) in enumerate(pair_names):
        if sum_den[pair_index] <= 0 or n_used[pair_index] == 0:
            raise SystemExit(
                f"ERROR: no usable Hudson FST denominator for {panel.name}: {pop1} vs {pop2}"
            )
        estimate = sum_num[pair_index] / sum_den[pair_index]
        leave_one_out: list[float] = []
        for chrom in chroms:
            den_loo = sum_den[pair_index] - chrom_den[chrom][pair_index]
            num_loo = sum_num[pair_index] - chrom_num[chrom][pair_index]
            if den_loo > 0:
                leave_one_out.append(num_loo / den_loo)
        if len(leave_one_out) < 2:
            jackknife_se = math.nan
        else:
            loo = np.asarray(leave_one_out, dtype=np.float64)
            loo_mean = float(np.mean(loo))
            b = len(loo)
            jackknife_se = math.sqrt((b - 1.0) / b * float(np.sum((loo - loo_mean) ** 2)))
        ci_low = estimate - 1.96 * jackknife_se if math.isfinite(jackknife_se) else math.nan
        ci_high = estimate + 1.96 * jackknife_se if math.isfinite(jackknife_se) else math.nan
        results.append(
            {
                "Panel": panel.name,
                "Population_1": pop1,
                "Population_2": pop2,
                "Hudson_FST_ratio_of_sums": float(estimate),
                "Chromosome_jackknife_SE": float(jackknife_se),
                "CI95_low": float(ci_low),
                "CI95_high": float(ci_high),
                "SNPs_used": int(n_used[pair_index]),
                "Negative_numerator_SNPs": int(n_negative_num[pair_index]),
                "Sum_numerator": float(sum_num[pair_index]),
                "Sum_denominator": float(sum_den[pair_index]),
                "Jackknife_blocks": len(leave_one_out),
            }
        )

    if len(results) != EXPECTED_PAIR_COUNT:
        raise SystemExit(
            f"ERROR: generated {len(results)} pairwise rows for {panel.name}; "
            f"expected {EXPECTED_PAIR_COUNT}."
        )
    if missing_cluster_rows:
        print(
            f"NOTE: {panel.name} had {missing_cluster_rows:,} absent cluster rows across SNPs; "
            "these are handled as missing allele observations."
        )
    return results


def canonical_pair(pop1: str, pop2: str) -> tuple[str, str]:
    return tuple(sorted((pop1, pop2), key=natural_key))  # type: ignore[return-value]


def rank_values(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        average_rank = (start + 1 + end) / 2.0
        for k in range(start, end):
            ranks[order[k]] = average_rank
        start = end
    return ranks


def pearson(x: Sequence[float], y: Sequence[float]) -> float:
    if len(x) != len(y) or len(x) < 2:
        return math.nan
    xa = np.asarray(x, dtype=np.float64)
    ya = np.asarray(y, dtype=np.float64)
    if np.std(xa) == 0 or np.std(ya) == 0:
        return math.nan
    return float(np.corrcoef(xa, ya)[0, 1])


def spearman(x: Sequence[float], y: Sequence[float]) -> float:
    return pearson(rank_values(x), rank_values(y))


def write_hudson_outputs(
    panel: PanelData,
    results: list[dict[str, Any]],
) -> tuple[Path, list[dict[str, Any]]]:
    pair_path = TABLE_DIR / f"{panel.name}_hudson_pairwise_fst.tsv"
    header = [
        "Panel",
        "Population_1",
        "Population_2",
        "Hudson_FST_ratio_of_sums",
        "Chromosome_jackknife_SE",
        "CI95_low",
        "CI95_high",
        "SNPs_used",
        "Negative_numerator_SNPs",
        "Sum_numerator",
        "Sum_denominator",
        "Jackknife_blocks",
    ]
    write_tsv(pair_path, header, [[row[col] for col in header] for row in results])

    ash = panel.ashkenazi_population
    ash_rows: list[dict[str, Any]] = []
    for row in results:
        if row["Population_1"] == ash:
            comparator = row["Population_2"]
        elif row["Population_2"] == ash:
            comparator = row["Population_1"]
        else:
            continue
        copied = dict(row)
        copied["Ashkenazi_population"] = ash
        copied["Comparator"] = comparator
        ash_rows.append(copied)
    ash_rows.sort(key=lambda row: row["Hudson_FST_ratio_of_sums"])
    for rank, row in enumerate(ash_rows, start=1):
        row["Rank_nearest_lowest_FST"] = rank
    if len(ash_rows) != EXPECTED_POPULATIONS - 1:
        raise SystemExit(
            f"ERROR: {panel.name} Ashkenazi ranking has {len(ash_rows)} rows; "
            f"expected {EXPECTED_POPULATIONS - 1}."
        )
    ash_path = TABLE_DIR / f"{panel.name}_ashkenazi_hudson_fst.tsv"
    ash_header = [
        "Panel",
        "Ashkenazi_population",
        "Comparator",
        "Rank_nearest_lowest_FST",
        "Hudson_FST_ratio_of_sums",
        "Chromosome_jackknife_SE",
        "CI95_low",
        "CI95_high",
        "SNPs_used",
        "Negative_numerator_SNPs",
    ]
    write_tsv(ash_path, ash_header, [[row[col] for col in ash_header] for row in ash_rows])
    return pair_path, ash_rows


def compare_hudson_panels(
    primary_results: list[dict[str, Any]],
    strict_results: list[dict[str, Any]],
    primary_ash: list[dict[str, Any]],
    strict_ash: list[dict[str, Any]],
) -> dict[str, Any]:
    def keyed(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
        return {
            canonical_pair(row["Population_1"], row["Population_2"]): row
            for row in rows
        }

    pmap = keyed(primary_results)
    smap = keyed(strict_results)
    if set(pmap) != set(smap):
        raise SystemExit(
            "ERROR: primary and strict pairwise Hudson tables do not contain identical population pairs."
        )
    comparison: list[dict[str, Any]] = []
    for pair in sorted(pmap, key=lambda x: (natural_key(x[0]), natural_key(x[1]))):
        p = pmap[pair]
        s = smap[pair]
        pv = float(p["Hudson_FST_ratio_of_sums"])
        sv = float(s["Hudson_FST_ratio_of_sums"])
        comparison.append(
            {
                "Population_1": pair[0],
                "Population_2": pair[1],
                "Primary_Hudson_FST": pv,
                "Strict_Hudson_FST": sv,
                "Strict_minus_primary": sv - pv,
                "Absolute_change": abs(sv - pv),
                "Primary_SE": p["Chromosome_jackknife_SE"],
                "Strict_SE": s["Chromosome_jackknife_SE"],
                "Primary_SNPs_used": p["SNPs_used"],
                "Strict_SNPs_used": s["SNPs_used"],
            }
        )
    comparison.sort(key=lambda row: row["Absolute_change"], reverse=True)
    comp_path = TABLE_DIR / "primary_strict_hudson_pairwise_comparison.tsv"
    comp_header = [
        "Population_1",
        "Population_2",
        "Primary_Hudson_FST",
        "Strict_Hudson_FST",
        "Strict_minus_primary",
        "Absolute_change",
        "Primary_SE",
        "Strict_SE",
        "Primary_SNPs_used",
        "Strict_SNPs_used",
    ]
    write_tsv(comp_path, comp_header, [[row[col] for col in comp_header] for row in comparison])

    p_ash_map = {row["Comparator"]: row for row in primary_ash}
    s_ash_map = {row["Comparator"]: row for row in strict_ash}
    if set(p_ash_map) != set(s_ash_map):
        raise SystemExit("ERROR: primary and strict Ashkenazi comparator sets differ.")
    ash_comparison: list[dict[str, Any]] = []
    for comparator in sorted(p_ash_map, key=natural_key):
        p = p_ash_map[comparator]
        s = s_ash_map[comparator]
        pv = float(p["Hudson_FST_ratio_of_sums"])
        sv = float(s["Hudson_FST_ratio_of_sums"])
        pr = int(p["Rank_nearest_lowest_FST"])
        sr = int(s["Rank_nearest_lowest_FST"])
        ash_comparison.append(
            {
                "Comparator": comparator,
                "Primary_rank": pr,
                "Strict_rank": sr,
                "Strict_minus_primary_rank": sr - pr,
                "Primary_Hudson_FST": pv,
                "Strict_Hudson_FST": sv,
                "Strict_minus_primary_FST": sv - pv,
                "Absolute_FST_change": abs(sv - pv),
                "Primary_SE": p["Chromosome_jackknife_SE"],
                "Strict_SE": s["Chromosome_jackknife_SE"],
            }
        )
    ash_comparison.sort(key=lambda row: row["Primary_rank"])
    ash_comp_path = TABLE_DIR / "primary_strict_ashkenazi_hudson_comparison.tsv"
    ash_header = [
        "Comparator",
        "Primary_rank",
        "Strict_rank",
        "Strict_minus_primary_rank",
        "Primary_Hudson_FST",
        "Strict_Hudson_FST",
        "Strict_minus_primary_FST",
        "Absolute_FST_change",
        "Primary_SE",
        "Strict_SE",
    ]
    write_tsv(ash_comp_path, ash_header, [[row[col] for col in ash_header] for row in ash_comparison])

    p_all = [float(pmap[p]["Hudson_FST_ratio_of_sums"]) for p in sorted(pmap)]
    s_all = [float(smap[p]["Hudson_FST_ratio_of_sums"]) for p in sorted(smap)]
    p_ash_vals = [float(p_ash_map[c]["Hudson_FST_ratio_of_sums"]) for c in sorted(p_ash_map)]
    s_ash_vals = [float(s_ash_map[c]["Hudson_FST_ratio_of_sums"]) for c in sorted(s_ash_map)]
    p_ash_ranks = [float(p_ash_map[c]["Rank_nearest_lowest_FST"]) for c in sorted(p_ash_map)]
    s_ash_ranks = [float(s_ash_map[c]["Rank_nearest_lowest_FST"]) for c in sorted(s_ash_map)]
    return {
        "pairwise_comparison_path": comp_path,
        "ashkenazi_comparison_path": ash_comp_path,
        "pairwise_rows": comparison,
        "ashkenazi_rows": ash_comparison,
        "all_pair_pearson": pearson(p_all, s_all),
        "all_pair_spearman": spearman(p_all, s_all),
        "ashkenazi_fst_pearson": pearson(p_ash_vals, s_ash_vals),
        "ashkenazi_fst_spearman": spearman(p_ash_vals, s_ash_vals),
        "ashkenazi_rank_pearson": pearson(p_ash_ranks, s_ash_ranks),
        "ashkenazi_rank_spearman": spearman(p_ash_ranks, s_ash_ranks),
    }


def sanitize_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")
    return cleaned or "population"


def write_pair_files(panel: PanelData, comparator: str) -> tuple[Path, Path]:
    ash = panel.ashkenazi_population
    pair_tag = f"{sanitize_filename(ash)}__{sanitize_filename(comparator)}"
    pair_dir = WORK / "wc_pairs" / panel.name
    pair_dir.mkdir(parents=True, exist_ok=True)
    keep = pair_dir / f"{pair_tag}.keep.tsv"
    within = pair_dir / f"{pair_tag}.within.tsv"
    selected = [s for s in panel.samples if s.population in {ash, comparator}]
    temp_keep = keep.with_suffix(keep.suffix + ".tmp")
    temp_within = within.with_suffix(within.suffix + ".tmp")
    with temp_keep.open("w", encoding="utf-8") as kh, temp_within.open("w", encoding="utf-8") as wh:
        for sample in selected:
            kh.write(f"{sample.fid}\t{sample.iid}\n")
            wh.write(f"{sample.fid}\t{sample.iid}\t{panel.pop_to_code[sample.population]}\n")
    temp_keep.replace(keep)
    temp_within.replace(within)
    return keep, within


def parse_plink_fst_log(log_path: Path) -> tuple[float, float]:
    text = log_path.read_text(encoding="utf-8", errors="replace")
    weighted_match = re.search(
        r"Weighted\s+Fst\s+estimate:\s*([^\s]+)", text, flags=re.IGNORECASE
    )
    mean_match = re.search(
        r"Mean\s+Fst\s+estimate:\s*([^\s]+)", text, flags=re.IGNORECASE
    )
    if not weighted_match or not mean_match:
        raise RuntimeError(
            f"Could not parse weighted/mean Fst estimates from {log_path}.\n"
            f"Last lines:\n{tail_text(log_path, 60)}"
        )
    weighted = safe_float(weighted_match.group(1))
    mean = safe_float(mean_match.group(1))
    if not math.isfinite(weighted) or not math.isfinite(mean):
        raise RuntimeError(
            f"Non-finite PLINK Fst estimate in {log_path}: weighted={weighted}, mean={mean}"
        )
    return weighted, mean


def run_one_wc_pair(
    panel: PanelData,
    comparator: str,
    force: bool,
    drop_variant_file: bool,
) -> dict[str, Any]:
    ash = panel.ashkenazi_population
    pair_tag = f"{sanitize_filename(ash)}__{sanitize_filename(comparator)}"
    out_dir = WC_DIR / panel.name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_prefix = out_dir / pair_tag
    fst_path = Path(str(out_prefix) + ".fst")
    log_path = Path(str(out_prefix) + ".log")
    console_path = LOG_DIR / f"wc_{panel.name}_{pair_tag}_console.txt"
    keep, within = write_pair_files(panel, comparator)

    use_existing = False
    if not force and log_path.is_file() and log_path.stat().st_size > 0:
        try:
            weighted, mean = parse_plink_fst_log(log_path)
            if fst_path.is_file() and fst_path.stat().st_size > 0:
                use_existing = True
        except Exception:
            use_existing = False
    if not use_existing:
        cmd = [
            str(PLINK),
            "--bfile", str(panel.bfile),
            "--extract", str(SHARED_SNPS),
            "--keep", str(keep),
            "--within", str(within),
            "--fst",
            "--keep-allele-order",
            "--nonfounders",
            "--threads", "1",
            "--out", str(out_prefix),
        ]
        run_command(cmd, console_path, echo=False)
        require_file(fst_path, f"PLINK WC per-variant FST for {panel.name} {comparator}")
        require_file(log_path, f"PLINK WC log for {panel.name} {comparator}")
        weighted, mean = parse_plink_fst_log(log_path)
    else:
        weighted, mean = parse_plink_fst_log(log_path)

    n_variant_rows = max(0, count_nonempty_lines(fst_path) - 1)
    if n_variant_rows == 0:
        raise RuntimeError(f"No per-variant FST rows in {fst_path}")
    ash_n = sum(s.population == ash for s in panel.samples)
    comp_n = sum(s.population == comparator for s in panel.samples)
    result = {
        "Panel": panel.name,
        "Ashkenazi_population": ash,
        "Comparator": comparator,
        "PLINK_Weir_Cockerham_weighted_FST": weighted,
        "PLINK_Weir_Cockerham_mean_FST": mean,
        "Per_variant_rows": n_variant_rows,
        "Ashkenazi_N": ash_n,
        "Comparator_N": comp_n,
        "PLINK_log": str(log_path.relative_to(ROOT)),
        "PLINK_fst_file": str(fst_path.relative_to(ROOT)),
    }
    if drop_variant_file:
        fst_path.unlink(missing_ok=True)
        result["PLINK_fst_file"] = "deleted_after_validation_by_request"
    return result


def run_wc_validation(
    panels: dict[str, PanelData],
    force: bool,
    workers: int,
    drop_variant_files: bool,
) -> dict[str, list[dict[str, Any]]]:
    jobs: list[tuple[PanelData, str]] = []
    for panel in panels.values():
        for comparator in panel.populations:
            if comparator != panel.ashkenazi_population:
                jobs.append((panel, comparator))
    workers = max(1, workers)
    print(
        f"Running/resuming {len(jobs)} Ashkenazi-focused PLINK Weir-Cockerham "
        f"validation jobs with {workers} worker(s)..."
    )
    results: dict[str, list[dict[str, Any]]] = {name: [] for name in panels}
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(
                run_one_wc_pair,
                panel,
                comparator,
                force,
                drop_variant_files,
            ): (panel.name, comparator)
            for panel, comparator in jobs
        }
        completed = 0
        for future in as_completed(future_map):
            panel_name, comparator = future_map[future]
            completed += 1
            try:
                row = future.result()
                results[panel_name].append(row)
                print(
                    f"  WC {completed}/{len(jobs)}: {panel_name} "
                    f"{row['Ashkenazi_population']} vs {comparator} = "
                    f"{row['PLINK_Weir_Cockerham_weighted_FST']:.8f}"
                )
            except Exception as exc:
                errors.append(f"{panel_name} {comparator}: {exc}")
    if errors:
        raise SystemExit(
            "ERROR: one or more PLINK Weir-Cockerham jobs failed:\n" + "\n".join(errors)
        )
    for panel_name, rows in results.items():
        rows.sort(key=lambda row: row["PLINK_Weir_Cockerham_weighted_FST"])
        for rank, row in enumerate(rows, start=1):
            row["Rank_nearest_lowest_WC_FST"] = rank
        if len(rows) != EXPECTED_POPULATIONS - 1:
            raise SystemExit(
                f"ERROR: {panel_name} WC validation produced {len(rows)} rows; "
                f"expected {EXPECTED_POPULATIONS - 1}."
            )
        path = TABLE_DIR / f"{panel_name}_ashkenazi_plink_weir_cockerham_fst.tsv"
        header = [
            "Panel",
            "Ashkenazi_population",
            "Comparator",
            "Rank_nearest_lowest_WC_FST",
            "PLINK_Weir_Cockerham_weighted_FST",
            "PLINK_Weir_Cockerham_mean_FST",
            "Per_variant_rows",
            "Ashkenazi_N",
            "Comparator_N",
            "PLINK_log",
            "PLINK_fst_file",
        ]
        write_tsv(path, header, [[row[col] for col in header] for row in rows])
    return results


def compare_hudson_wc(
    hudson: dict[str, list[dict[str, Any]]],
    wc: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    metrics: dict[str, dict[str, float]] = {}
    for panel_name in sorted(hudson):
        hmap = {row["Comparator"]: row for row in hudson[panel_name]}
        wmap = {row["Comparator"]: row for row in wc[panel_name]}
        if set(hmap) != set(wmap):
            raise SystemExit(
                f"ERROR: Hudson/WC comparator mismatch in {panel_name}: "
                f"Hudson-only={sorted(set(hmap)-set(wmap))}, WC-only={sorted(set(wmap)-set(hmap))}"
            )
        hvals: list[float] = []
        wvals: list[float] = []
        for comparator in sorted(hmap, key=natural_key):
            h = hmap[comparator]
            w = wmap[comparator]
            hv = float(h["Hudson_FST_ratio_of_sums"])
            wv = float(w["PLINK_Weir_Cockerham_weighted_FST"])
            hvals.append(hv)
            wvals.append(wv)
            rows.append(
                {
                    "Panel": panel_name,
                    "Comparator": comparator,
                    "Hudson_rank": h["Rank_nearest_lowest_FST"],
                    "WC_rank": w["Rank_nearest_lowest_WC_FST"],
                    "WC_minus_Hudson_rank": int(w["Rank_nearest_lowest_WC_FST"]) - int(h["Rank_nearest_lowest_FST"]),
                    "Hudson_FST": hv,
                    "PLINK_WC_weighted_FST": wv,
                    "WC_minus_Hudson_FST": wv - hv,
                }
            )
        metrics[panel_name] = {
            "pearson": pearson(hvals, wvals),
            "spearman": spearman(hvals, wvals),
        }
    path = TABLE_DIR / "ashkenazi_hudson_vs_weir_cockerham_validation.tsv"
    header = [
        "Panel",
        "Comparator",
        "Hudson_rank",
        "WC_rank",
        "WC_minus_Hudson_rank",
        "Hudson_FST",
        "PLINK_WC_weighted_FST",
        "WC_minus_Hudson_FST",
    ]
    write_tsv(path, header, [[row[col] for col in header] for row in rows])
    return {"path": path, "rows": rows, "metrics": metrics}


def plot_ashkenazi_bars(
    primary_ash: list[dict[str, Any]],
    strict_ash: list[dict[str, Any]],
) -> Path:
    pmap = {row["Comparator"]: row for row in primary_ash}
    smap = {row["Comparator"]: row for row in strict_ash}
    comparators = [row["Comparator"] for row in primary_ash]
    x = np.arange(len(comparators), dtype=float)
    width = 0.38
    pvals = [float(pmap[c]["Hudson_FST_ratio_of_sums"]) for c in comparators]
    svals = [float(smap[c]["Hudson_FST_ratio_of_sums"]) for c in comparators]
    fig, ax = plt.subplots(figsize=(15, 7.5))
    ax.bar(x - width / 2, pvals, width, label="Primary")
    ax.bar(x + width / 2, svals, width, label="Strict Pass-only")
    ax.set_xticks(x)
    ax.set_xticklabels(comparators, rotation=55, ha="right")
    ax.set_ylabel("Hudson FST (ratio of sums)")
    ax.set_title("Ashkenazi pairwise Hudson FST by comparator")
    ax.legend()
    ax.axhline(0, linewidth=0.8)
    fig.tight_layout()
    path = FIG_DIR / "ashkenazi_hudson_fst_primary_vs_strict.png"
    fig.savefig(path, dpi=240, bbox_inches="tight")
    fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)
    return path


def plot_primary_strict_scatter(comparison_rows: list[dict[str, Any]]) -> Path:
    x = np.asarray([row["Primary_Hudson_FST"] for row in comparison_rows], dtype=float)
    y = np.asarray([row["Strict_Hudson_FST"] for row in comparison_rows], dtype=float)
    low = float(min(np.min(x), np.min(y)))
    high = float(max(np.max(x), np.max(y)))
    margin = max((high - low) * 0.05, 1e-5)
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(x, y, s=28, alpha=0.75)
    ax.plot([low - margin, high + margin], [low - margin, high + margin], linestyle="--", linewidth=1)
    ax.set_xlim(low - margin, high + margin)
    ax.set_ylim(low - margin, high + margin)
    ax.set_xlabel("Primary Hudson FST")
    ax.set_ylabel("Strict Pass-only Hudson FST")
    ax.set_title("All population pairs: primary versus strict Hudson FST")
    fig.tight_layout()
    path = FIG_DIR / "all_pairs_primary_vs_strict_hudson_fst.png"
    fig.savefig(path, dpi=240, bbox_inches="tight")
    fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)
    return path


def make_fst_matrix(
    populations: Sequence[str],
    results: list[dict[str, Any]],
) -> np.ndarray:
    index = {pop: i for i, pop in enumerate(populations)}
    matrix = np.zeros((len(populations), len(populations)), dtype=float)
    for row in results:
        i = index[row["Population_1"]]
        j = index[row["Population_2"]]
        value = float(row["Hudson_FST_ratio_of_sums"])
        matrix[i, j] = value
        matrix[j, i] = value
    return matrix


def plot_heatmap(
    populations: Sequence[str],
    matrix: np.ndarray,
    title: str,
    filename: str,
    symmetric: bool = False,
) -> Path:
    fig, ax = plt.subplots(figsize=(12, 10))
    kwargs: dict[str, Any] = {"aspect": "auto"}
    if symmetric:
        bound = float(np.max(np.abs(matrix)))
        kwargs.update({"vmin": -bound, "vmax": bound, "cmap": "coolwarm"})
    image = ax.imshow(matrix, **kwargs)
    ax.set_xticks(np.arange(len(populations)))
    ax.set_yticks(np.arange(len(populations)))
    ax.set_xticklabels(populations, rotation=55, ha="right")
    ax.set_yticklabels(populations)
    ax.set_title(title)
    cbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Hudson FST" if not symmetric else "Strict minus primary Hudson FST")
    fig.tight_layout()
    path = FIG_DIR / filename
    fig.savefig(path, dpi=240, bbox_inches="tight")
    fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)
    return path


def plot_hudson_wc(validation: dict[str, Any]) -> Path:
    rows = validation["rows"]
    fig, ax = plt.subplots(figsize=(8, 8))
    for panel_name in sorted({row["Panel"] for row in rows}):
        subset = [row for row in rows if row["Panel"] == panel_name]
        ax.scatter(
            [row["Hudson_FST"] for row in subset],
            [row["PLINK_WC_weighted_FST"] for row in subset],
            label=panel_name,
            s=40,
            alpha=0.8,
        )
    all_values = [float(row["Hudson_FST"]) for row in rows] + [
        float(row["PLINK_WC_weighted_FST"]) for row in rows
    ]
    low = min(all_values)
    high = max(all_values)
    margin = max((high - low) * 0.05, 1e-5)
    ax.plot([low - margin, high + margin], [low - margin, high + margin], linestyle="--", linewidth=1)
    ax.set_xlim(low - margin, high + margin)
    ax.set_ylim(low - margin, high + margin)
    ax.set_xlabel("Hudson FST")
    ax.set_ylabel("PLINK Weir-Cockerham weighted FST")
    ax.set_title("Ashkenazi comparisons: estimator validation")
    ax.legend()
    fig.tight_layout()
    path = FIG_DIR / "ashkenazi_hudson_vs_weir_cockerham.png"
    fig.savefig(path, dpi=240, bbox_inches="tight")
    fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)
    return path


def format_float(value: float, digits: int = 8) -> str:
    return "NA" if not math.isfinite(value) else f"{value:.{digits}f}"


def write_methods(plink_version: str) -> Path:
    path = OUT / "METHODS_STAGE06_FST.txt"
    text = f"""Stage 06 FST methods

Dataset framework

The primary and strict Pass-only panels were analyzed on the identical shared post-QC autosomal SNP set containing {EXPECTED_SHARED_SNPS:,} markers. The LD-pruned PCA/ADMIXTURE marker set was not used for the primary FST analysis because genome-wide FST estimation does not require LD pruning; retaining the broader shared post-QC set preserves information while keeping SNP ascertainment identical across panels.

Primary estimator

Pairwise Hudson FST was computed for every unordered population pair from PLINK cluster-stratified allele counts. At each biallelic SNP, the finite-sample-corrected Hudson numerator was calculated as (p1-p2)^2 - p1(1-p1)/(n1-1) - p2(1-p2)/(n2-1), and the denominator as p1(1-p2) + p2(1-p1), where p is the observed A1 allele frequency and n is the number of observed chromosomes. Genome-wide FST is the ratio of the summed numerators to the summed denominators, rather than the unweighted mean of per-SNP ratios.

Uncertainty

Standard errors were estimated with a delete-one-autosome jackknife across chromosomes 1-22. Approximate 95 percent confidence intervals are the point estimate plus or minus 1.96 times the chromosome-jackknife standard error.

Validation estimator

For every Ashkenazi-versus-comparator pair, PLINK --fst was run as a second estimator. PLINK reports Weir-Cockerham per-marker FST and global weighted and mean estimates. The weighted estimate is used for rank validation against Hudson FST.

Sample-size handling

No individuals were downsampled. The primary and strict panels retain their intended compositions, and sample counts are reported for every population. Hudson FST was selected as the primary pairwise estimator because its finite-sample correction is comparatively robust to unequal sample sizes. Primary-versus-strict changes are interpreted as sensitivity to panel composition, with estimator concordance checked against PLINK Weir-Cockerham estimates.

Software

{plink_version}
Python: {sys.version.splitlines()[0]}
NumPy: {np.__version__}
Matplotlib: {matplotlib.__version__}
"""
    path.write_text(text, encoding="utf-8")
    return path


def write_summary(
    panels: dict[str, PanelData],
    hudson_results: dict[str, list[dict[str, Any]]],
    hudson_ash: dict[str, list[dict[str, Any]]],
    comparison: dict[str, Any],
    wc_results: dict[str, list[dict[str, Any]]] | None,
    estimator_validation: dict[str, Any] | None,
    generated_files: Sequence[Path],
    plink_version: str,
    elapsed_seconds: float,
) -> tuple[Path, Path]:
    lines: list[str] = []
    lines.append("Stage 06 FST analysis summary")
    lines.append("")
    lines.append(f"Completed UTC: {now_utc()}")
    lines.append(f"Elapsed seconds: {elapsed_seconds:.1f}")
    lines.append(f"Shared post-QC SNPs: {EXPECTED_SHARED_SNPS:,}")
    lines.append(f"Populations per panel: {EXPECTED_POPULATIONS}")
    lines.append(f"Pairwise comparisons per panel: {EXPECTED_PAIR_COUNT}")
    lines.append(f"Primary samples: {len(panels['primary'].samples)}")
    lines.append(f"Strict Pass-only samples: {len(panels['strict_pass'].samples)}")
    lines.append(f"PLINK: {plink_version}")
    lines.append("")
    lines.append("Primary estimator: Hudson FST ratio of summed finite-sample-corrected numerators to summed denominators.")
    lines.append("Uncertainty: delete-one-autosome jackknife across chromosomes 1-22.")
    lines.append("Validation: PLINK Weir-Cockerham weighted FST for Ashkenazi-versus-comparator pairs." if wc_results else "Validation: skipped by --skip-wc.")
    lines.append("")
    for panel_name in ("primary", "strict_pass"):
        panel = panels[panel_name]
        lines.append(f"{panel_name} Ashkenazi population label: {panel.ashkenazi_population}")
        lines.append(f"{panel_name} nearest Ashkenazi comparators by Hudson FST:")
        for row in hudson_ash[panel_name][:10]:
            lines.append(
                f"  {int(row['Rank_nearest_lowest_FST'])}. {row['Comparator']}: "
                f"FST={format_float(float(row['Hudson_FST_ratio_of_sums']))}, "
                f"SE={format_float(float(row['Chromosome_jackknife_SE']))}, "
                f"95% CI=[{format_float(float(row['CI95_low']))}, {format_float(float(row['CI95_high']))}], "
                f"SNPs={int(row['SNPs_used']):,}"
            )
        lines.append("")
    lines.append("Primary-versus-strict concordance:")
    lines.append(f"  All-pair Pearson r: {format_float(comparison['all_pair_pearson'], 6)}")
    lines.append(f"  All-pair Spearman rho: {format_float(comparison['all_pair_spearman'], 6)}")
    lines.append(f"  Ashkenazi-pair Pearson r: {format_float(comparison['ashkenazi_fst_pearson'], 6)}")
    lines.append(f"  Ashkenazi-pair Spearman rho: {format_float(comparison['ashkenazi_fst_spearman'], 6)}")
    lines.append("")
    lines.append("Largest absolute primary-versus-strict pairwise FST changes:")
    for row in comparison["pairwise_rows"][:10]:
        lines.append(
            f"  {row['Population_1']} vs {row['Population_2']}: "
            f"primary={format_float(float(row['Primary_Hudson_FST']))}, "
            f"strict={format_float(float(row['Strict_Hudson_FST']))}, "
            f"delta={format_float(float(row['Strict_minus_primary']))}"
        )
    lines.append("")
    lines.append("Ashkenazi comparator rank changes (strict rank minus primary rank):")
    for row in sorted(
        comparison["ashkenazi_rows"],
        key=lambda item: abs(int(item["Strict_minus_primary_rank"])),
        reverse=True,
    ):
        lines.append(
            f"  {row['Comparator']}: primary rank {row['Primary_rank']}, "
            f"strict rank {row['Strict_rank']}, change {int(row['Strict_minus_primary_rank']):+d}"
        )
    if estimator_validation is not None:
        lines.append("")
        lines.append("Hudson versus PLINK Weir-Cockerham Ashkenazi-pair concordance:")
        for panel_name in ("primary", "strict_pass"):
            metric = estimator_validation["metrics"][panel_name]
            lines.append(
                f"  {panel_name}: Pearson r={format_float(metric['pearson'], 6)}, "
                f"Spearman rho={format_float(metric['spearman'], 6)}"
            )
    lines.append("")
    lines.append("Generated files:")
    for path in sorted(set(generated_files), key=lambda p: str(p)):
        if path.exists():
            lines.append(f"  {path.relative_to(ROOT)}")
    summary_path = OUT / "fst_analysis_summary.txt"
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manuscript_lines: list[str] = []
    manuscript_lines.append("Stage 06 FST results for manuscript integration")
    manuscript_lines.append("")
    manuscript_lines.append(
        f"Pairwise population differentiation was estimated on the same {EXPECTED_SHARED_SNPS:,} shared post-QC autosomal SNPs in both the primary and strict Pass-only panels. Genome-wide Hudson FST was calculated as a ratio of sums, with uncertainty estimated by delete-one-autosome jackknife."
    )
    manuscript_lines.append("")
    for panel_name, display in (("primary", "Primary"), ("strict_pass", "Strict Pass-only")):
        top = hudson_ash[panel_name][:5]
        rendered = ", ".join(
            f"{row['Comparator']} ({format_float(float(row['Hudson_FST_ratio_of_sums']), 6)})"
            for row in top
        )
        manuscript_lines.append(
            f"{display} panel: the five lowest Ashkenazi pairwise Hudson FST values were {rendered}."
        )
    manuscript_lines.append("")
    manuscript_lines.append(
        f"Across all {EXPECTED_PAIR_COUNT} population pairs, primary and strict Hudson FST estimates had Pearson r={format_float(comparison['all_pair_pearson'], 4)} and Spearman rho={format_float(comparison['all_pair_spearman'], 4)}. For the {EXPECTED_POPULATIONS - 1} Ashkenazi-versus-comparator pairs, Spearman rho was {format_float(comparison['ashkenazi_fst_spearman'], 4)}."
    )
    if estimator_validation is not None:
        primary_metric = estimator_validation["metrics"]["primary"]
        strict_metric = estimator_validation["metrics"]["strict_pass"]
        manuscript_lines.append(
            f"Ashkenazi-comparator Hudson rankings were cross-validated with PLINK Weir-Cockerham weighted FST; estimator rank correlations were rho={format_float(primary_metric['spearman'], 4)} in the primary panel and rho={format_float(strict_metric['spearman'], 4)} in the strict panel."
        )
    manuscript_lines.append("")
    manuscript_lines.append(
        "Interpretation should emphasize rank stability and rank movement under reference-panel restriction, while avoiding causal ancestry claims from FST alone. FST quantifies population differentiation; it does not by itself identify admixture direction, dates, or source proportions."
    )
    manuscript_path = OUT / "stage06_fst_results_for_manuscript.txt"
    manuscript_path.write_text("\n".join(manuscript_lines) + "\n", encoding="utf-8")
    return summary_path, manuscript_path


def validate_final_outputs(
    panels: dict[str, PanelData],
    hudson_results: dict[str, list[dict[str, Any]]],
    hudson_ash: dict[str, list[dict[str, Any]]],
    wc_results: dict[str, list[dict[str, Any]]] | None,
    required_files: Sequence[Path],
) -> None:
    for panel_name in panels:
        if len(hudson_results[panel_name]) != EXPECTED_PAIR_COUNT:
            raise SystemExit(f"ERROR: final {panel_name} Hudson pair count is incorrect.")
        if len(hudson_ash[panel_name]) != EXPECTED_POPULATIONS - 1:
            raise SystemExit(f"ERROR: final {panel_name} Ashkenazi row count is incorrect.")
        for row in hudson_results[panel_name]:
            value = float(row["Hudson_FST_ratio_of_sums"])
            se = float(row["Chromosome_jackknife_SE"])
            if not math.isfinite(value) or not math.isfinite(se):
                raise SystemExit(
                    f"ERROR: non-finite final Hudson statistic: {panel_name} {row}"
                )
            if value < -0.1 or value > 1.0:
                raise SystemExit(
                    f"ERROR: implausible genome-wide Hudson FST {value}: {panel_name} {row}"
                )
            if int(row["Jackknife_blocks"]) != 22:
                raise SystemExit(
                    f"ERROR: expected 22 jackknife blocks: {panel_name} {row}"
                )
    if wc_results is not None:
        for panel_name in panels:
            if len(wc_results[panel_name]) != EXPECTED_POPULATIONS - 1:
                raise SystemExit(f"ERROR: final {panel_name} WC row count is incorrect.")
    for path in required_files:
        require_file(path, "final Stage 06 output")


def write_run_metadata(
    args: argparse.Namespace,
    panels: dict[str, PanelData],
    plink_version: str,
    start_utc: str,
    elapsed_seconds: float,
    generated_files: Sequence[Path],
) -> Path:
    metadata = {
        "stage": 6,
        "status": "complete",
        "project": "Ashkenazi reference-panel sensitivity experiment",
        "started_utc": start_utc,
        "completed_utc": now_utc(),
        "elapsed_seconds": elapsed_seconds,
        "command_line": sys.argv,
        "root": str(ROOT),
        "shared_qc_snp_count": EXPECTED_SHARED_SNPS,
        "shared_qc_snp_file": str(SHARED_SNPS),
        "shared_qc_snp_sha256": sha256(SHARED_SNPS),
        "plink_version": plink_version,
        "python": sys.version,
        "numpy": np.__version__,
        "matplotlib": matplotlib.__version__,
        "options": {
            "force": args.force,
            "skip_wc": args.skip_wc,
            "workers": args.workers,
            "drop_wc_variant_files": args.drop_wc_variant_files,
        },
        "panels": {
            name: {
                "samples": len(panel.samples),
                "populations": len(panel.populations),
                "ashkenazi_population": panel.ashkenazi_population,
                "bfile": str(panel.bfile),
                "manifest": str(panel.manifest),
                "manifest_sha256": sha256(panel.manifest),
                "fam_sha256": sha256(Path(str(panel.bfile) + ".fam")),
                "bim_sha256": sha256(Path(str(panel.bfile) + ".bim")),
            }
            for name, panel in panels.items()
        },
        "generated_files": [
            str(path.relative_to(ROOT))
            for path in sorted(set(generated_files), key=lambda p: str(p))
            if path.exists()
        ],
    }
    temp = COMPLETE_FLAG.with_suffix(".json.tmp")
    temp.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(COMPLETE_FLAG)
    return COMPLETE_FLAG


def main() -> None:
    args = parse_args()
    start_time = time.time()
    start_utc = now_utc()
    if args.workers < 1:
        raise SystemExit("ERROR: --workers must be at least 1.")

    prepare_directories()
    with StageLock(LOCK_FILE):
        print("Stage 06 FST analysis")
        print(f"Project: {ROOT}")
        inspect_stage05()
        require_file(PLINK, "PLINK executable")
        require_file(PCA_PYTHON, "pca-tools Python interpreter")
        shared_snps, shared_snp_set = validate_shared_snps()
        print(f"\nValidated shared post-QC SNP list: {len(shared_snps):,} unique SNPs")

        panels = {
            name: build_panel_data(name, spec)
            for name, spec in PANEL_SPECS.items()
        }
        primary_ids = {sample.iid for sample in panels["primary"].samples}
        strict_ids = {sample.iid for sample in panels["strict_pass"].samples}
        if not strict_ids < primary_ids:
            raise SystemExit(
                "ERROR: strict Pass-only sample set is not a proper subset of primary."
            )
        if panels["primary"].populations != panels["strict_pass"].populations:
            raise SystemExit(
                "ERROR: primary and strict panels do not contain identical population labels."
            )
        for name, panel in panels.items():
            bim_count, _ = validate_bim(panel.bfile, shared_snp_set)
            print(
                f"Validated {name}: {len(panel.samples)} samples, "
                f"{len(panel.populations)} populations, {bim_count:,} BIM variants, "
                f"Ashkenazi label={panel.ashkenazi_population}"
            )

        primary_bim = Path(str(panels["primary"].bfile) + ".bim")
        strict_bim = Path(str(panels["strict_pass"].bfile) + ".bim")
        if sha256(primary_bim) != sha256(strict_bim):
            raise SystemExit("ERROR: primary and strict full-panel BIM files are not identical.")

        plink_version = get_plink_version()
        print(f"PLINK: {plink_version}")
        methods_path = write_methods(plink_version)

        frq_paths = {
            name: run_stratified_frequencies(panel, args.force)
            for name, panel in panels.items()
        }

        hudson_results: dict[str, list[dict[str, Any]]] = {}
        hudson_ash: dict[str, list[dict[str, Any]]] = {}
        generated: list[Path] = [methods_path]
        for name, panel in panels.items():
            results = compute_hudson_pairwise(panel, frq_paths[name], shared_snp_set)
            hudson_results[name] = results
            pair_path, ash_rows = write_hudson_outputs(panel, results)
            hudson_ash[name] = ash_rows
            generated.extend([frq_paths[name], pair_path, TABLE_DIR / f"{name}_ashkenazi_hudson_fst.tsv", panel.count_file])

        comparison = compare_hudson_panels(
            hudson_results["primary"],
            hudson_results["strict_pass"],
            hudson_ash["primary"],
            hudson_ash["strict_pass"],
        )
        generated.extend(
            [
                comparison["pairwise_comparison_path"],
                comparison["ashkenazi_comparison_path"],
            ]
        )

        wc_results: dict[str, list[dict[str, Any]]] | None = None
        estimator_validation: dict[str, Any] | None = None
        if not args.skip_wc:
            wc_results = run_wc_validation(
                panels,
                args.force,
                args.workers,
                args.drop_wc_variant_files,
            )
            estimator_validation = compare_hudson_wc(hudson_ash, wc_results)
            generated.append(estimator_validation["path"])
            for name in panels:
                generated.append(TABLE_DIR / f"{name}_ashkenazi_plink_weir_cockerham_fst.tsv")

        bar_plot = plot_ashkenazi_bars(hudson_ash["primary"], hudson_ash["strict_pass"])
        scatter_plot = plot_primary_strict_scatter(comparison["pairwise_rows"])
        populations = panels["primary"].populations
        primary_matrix = make_fst_matrix(populations, hudson_results["primary"])
        strict_matrix = make_fst_matrix(populations, hudson_results["strict_pass"])
        primary_heatmap = plot_heatmap(
            populations,
            primary_matrix,
            "Primary panel pairwise Hudson FST",
            "primary_hudson_fst_heatmap.png",
        )
        strict_heatmap = plot_heatmap(
            populations,
            strict_matrix,
            "Strict Pass-only panel pairwise Hudson FST",
            "strict_pass_hudson_fst_heatmap.png",
        )
        difference_heatmap = plot_heatmap(
            populations,
            strict_matrix - primary_matrix,
            "Strict minus primary pairwise Hudson FST",
            "strict_minus_primary_hudson_fst_heatmap.png",
            symmetric=True,
        )
        generated.extend(
            [
                bar_plot,
                bar_plot.with_suffix(".pdf"),
                scatter_plot,
                scatter_plot.with_suffix(".pdf"),
                primary_heatmap,
                primary_heatmap.with_suffix(".pdf"),
                strict_heatmap,
                strict_heatmap.with_suffix(".pdf"),
                difference_heatmap,
                difference_heatmap.with_suffix(".pdf"),
            ]
        )
        if estimator_validation is not None:
            validation_plot = plot_hudson_wc(estimator_validation)
            generated.extend([validation_plot, validation_plot.with_suffix(".pdf")])

        elapsed = time.time() - start_time
        summary_path, manuscript_path = write_summary(
            panels,
            hudson_results,
            hudson_ash,
            comparison,
            wc_results,
            estimator_validation,
            generated,
            plink_version,
            elapsed,
        )
        generated.extend([summary_path, manuscript_path])

        validate_final_outputs(
            panels,
            hudson_results,
            hudson_ash,
            wc_results,
            generated,
        )
        complete_path = write_run_metadata(
            args,
            panels,
            plink_version,
            start_utc,
            elapsed,
            generated,
        )
        generated.append(complete_path)

        print("\n===== Stage 06 completed successfully =====")
        print(summary_path.read_text(encoding="utf-8", errors="replace").rstrip())
        print(f"\nCompletion record: {complete_path}")
        print(f"Results directory: {OUT}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit("\nERROR: Stage 06 interrupted by user. Existing completed suboutputs are resumable.")
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"ERROR: subprocess failed: {exc}")
    except RuntimeError as exc:
        raise SystemExit(f"ERROR: {exc}")
