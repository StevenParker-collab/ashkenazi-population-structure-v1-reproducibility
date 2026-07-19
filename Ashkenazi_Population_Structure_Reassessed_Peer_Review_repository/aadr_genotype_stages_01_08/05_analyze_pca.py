#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path("/home/computer/popgen/projects/ashkenazi_reference_test")
PCA_DIR = ROOT / "results" / "pca"
OUT_DIR = PCA_DIR / "analysis"
CONDA = Path("/home/computer/miniconda3/bin/conda")
ENV_PYTHON = Path("/home/computer/miniconda3/envs/popgen/bin/python")
N_DISTANCE_PCS = 10

PANELS = {
    "primary": {
        "manifest": ROOT / "manifests" / "modern_panel_primary.tsv",
        "eigenvec": PCA_DIR / "modern_primary.eigenvec",
        "eigenval": PCA_DIR / "modern_primary.eigenval",
    },
    "strict_pass": {
        "manifest": ROOT / "manifests" / "modern_panel_strict_pass.tsv",
        "eigenvec": PCA_DIR / "modern_strict_pass.eigenvec",
        "eigenval": PCA_DIR / "modern_strict_pass.eigenval",
    },
}


def ensure_dependencies() -> None:
    try:
        import numpy  # noqa: F401
        import matplotlib  # noqa: F401
        return
    except ImportError:
        pass

    if os.environ.get("PCA_STAGE_BOOTSTRAPPED") == "1":
        raise SystemExit(
            "ERROR: numpy/matplotlib are still unavailable after installation."
        )

    if not CONDA.is_file():
        raise SystemExit(f"ERROR: conda executable not found: {CONDA}")

    print("Installing missing PCA dependencies into the popgen environment...")
    subprocess.run(
        [str(CONDA), "install", "-n", "popgen", "-y", "numpy", "matplotlib"],
        check=True,
    )

    if not ENV_PYTHON.is_file():
        raise SystemExit(f"ERROR: popgen Python not found: {ENV_PYTHON}")

    env = dict(os.environ)
    env["PCA_STAGE_BOOTSTRAPPED"] = "1"
    os.execve(str(ENV_PYTHON), [str(ENV_PYTHON), str(Path(__file__).resolve())], env)


ensure_dependencies()

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def require_file(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise SystemExit(f"ERROR: required file is missing or empty: {path}")


def resolve_column(fieldnames: list[str], candidates: list[str], label: str) -> str:
    lookup = {name.strip().lower(): name for name in fieldnames}
    for candidate in candidates:
        match = lookup.get(candidate.lower())
        if match:
            return match
    raise SystemExit(
        f"ERROR: could not find {label} column. Available columns: {fieldnames}"
    )


def read_manifest(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = reader.fieldnames or []
        if not fieldnames:
            raise SystemExit(f"ERROR: manifest has no header: {path}")

        id_col = resolve_column(
            fieldnames,
            ["Genetic_ID", "Genetic ID", "IID", "Sample_ID", "Sample ID", "ID"],
            "sample ID",
        )
        pop_col = resolve_column(
            fieldnames,
            ["Clean_Group", "Clean Group", "Population", "Group", "Pop"],
            "population",
        )

        optional_candidates = {
            "Original_Group": ["Original_Group", "Original Group"],
            "Locality": ["Locality", "Location"],
            "Assessment": ["Assessment", "Status"],
        }
        optional_columns: dict[str, str | None] = {}
        lowered = {name.strip().lower(): name for name in fieldnames}
        for output_name, candidates in optional_candidates.items():
            optional_columns[output_name] = next(
                (lowered[c.lower()] for c in candidates if c.lower() in lowered),
                None,
            )

        records: dict[str, dict[str, str]] = {}
        for row in reader:
            sample_id = row[id_col].strip()
            if not sample_id:
                continue
            if sample_id in records:
                raise SystemExit(f"ERROR: duplicate manifest ID: {sample_id}")
            records[sample_id] = {
                "Population": row[pop_col].strip(),
                "Original_Group": (
                    row[optional_columns["Original_Group"]].strip()
                    if optional_columns["Original_Group"] else ""
                ),
                "Locality": (
                    row[optional_columns["Locality"]].strip()
                    if optional_columns["Locality"] else ""
                ),
                "Assessment": (
                    row[optional_columns["Assessment"]].strip()
                    if optional_columns["Assessment"] else ""
                ),
            }
    return records


def read_eigenvec(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    with path.open(encoding="utf-8-sig") as handle:
        header_line = handle.readline().strip()
        if not header_line:
            raise SystemExit(f"ERROR: empty eigenvector file: {path}")

        header = header_line.lstrip("#").split()
        normalized = [item.upper() for item in header]

        if "IID" in normalized:
            iid_index = normalized.index("IID")
        elif len(header) >= 2:
            iid_index = 1
        else:
            raise SystemExit(f"ERROR: cannot identify IID column in {path}")

        fid_index = normalized.index("FID") if "FID" in normalized else 0
        pc_indices = [
            index for index, column in enumerate(normalized)
            if column.startswith("PC") and column[2:].isdigit()
        ]
        pc_indices.sort(key=lambda index: int(normalized[index][2:]))

        if len(pc_indices) < N_DISTANCE_PCS:
            raise SystemExit(
                f"ERROR: {path} contains {len(pc_indices)} PCs; "
                f"{N_DISTANCE_PCS} required."
            )

        pc_names = [normalized[index] for index in pc_indices]
        rows: list[dict[str, Any]] = []

        for line_number, line in enumerate(handle, start=2):
            if not line.strip():
                continue
            fields = line.split()
            if len(fields) != len(header):
                raise SystemExit(
                    f"ERROR: malformed row {line_number} in {path}: "
                    f"expected {len(header)} fields, found {len(fields)}."
                )
            rows.append(
                {
                    "FID": fields[fid_index],
                    "IID": fields[iid_index],
                    "PC": np.array(
                        [float(fields[index]) for index in pc_indices],
                        dtype=float,
                    ),
                }
            )

    return pc_names, rows


def read_eigenvalues(path: Path) -> np.ndarray:
    values = np.array(
        [
            float(line.strip())
            for line in path.read_text(encoding="utf-8-sig").splitlines()
            if line.strip()
        ],
        dtype=float,
    )
    if len(values) == 0 or np.any(values < 0):
        raise SystemExit(f"ERROR: invalid eigenvalues: {path}")
    return values


def write_tsv(path: Path, header: list[str], rows: list[list[Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def analyze_panel(panel: str, paths: dict[str, Path]) -> dict[str, Any]:
    for path in paths.values():
        require_file(path)

    manifest = read_manifest(paths["manifest"])
    pc_names, eigen_rows = read_eigenvec(paths["eigenvec"])
    eigenvalues = read_eigenvalues(paths["eigenval"])

    if len(eigenvalues) != len(pc_names):
        raise SystemExit(
            f"ERROR: {panel} has {len(pc_names)} PCs but "
            f"{len(eigenvalues)} eigenvalues."
        )

    eigen_ids = [str(row["IID"]) for row in eigen_rows]
    if len(eigen_ids) != len(set(eigen_ids)):
        raise SystemExit(f"ERROR: duplicate PCA IDs in {panel}.")

    missing_manifest = sorted(set(eigen_ids) - set(manifest))
    missing_pca = sorted(set(manifest) - set(eigen_ids))
    if missing_manifest:
        raise SystemExit(
            f"ERROR: {panel} PCA IDs missing from manifest: {missing_manifest[:10]}"
        )
    if missing_pca:
        raise SystemExit(
            f"ERROR: {panel} manifest IDs missing from PCA: {missing_pca[:10]}"
        )

    explained = eigenvalues / eigenvalues.sum() * 100.0
    annotated: list[dict[str, Any]] = []

    for row in eigen_rows:
        sample_id = str(row["IID"])
        metadata = manifest[sample_id]
        annotated.append(
            {
                "FID": row["FID"],
                "IID": sample_id,
                "Population": metadata["Population"],
                "Original_Group": metadata["Original_Group"],
                "Locality": metadata["Locality"],
                "Assessment": metadata["Assessment"],
                "PC": row["PC"],
            }
        )

    write_tsv(
        OUT_DIR / f"modern_{panel}_annotated.tsv",
        [
            "FID", "IID", "Population", "Original_Group",
            "Locality", "Assessment", *pc_names,
        ],
        [
            [
                row["FID"], row["IID"], row["Population"],
                row["Original_Group"], row["Locality"], row["Assessment"],
                *[f"{value:.10f}" for value in row["PC"]],
            ]
            for row in annotated
        ],
    )

    write_tsv(
        OUT_DIR / f"modern_{panel}_variance_explained.tsv",
        ["PC", "Eigenvalue", "Variance_Percent", "Cumulative_Percent"],
        [
            [
                index + 1,
                f"{eigenvalues[index]:.10f}",
                f"{explained[index]:.6f}",
                f"{explained[:index + 1].sum():.6f}",
            ]
            for index in range(len(eigenvalues))
        ],
    )

    grouped: dict[str, list[np.ndarray]] = {}
    for row in annotated:
        grouped.setdefault(row["Population"], []).append(
            np.asarray(row["PC"][:N_DISTANCE_PCS], dtype=float)
        )

    centroids = {
        population: np.mean(np.vstack(values), axis=0)
        for population, values in grouped.items()
    }
    counts = {population: len(values) for population, values in grouped.items()}

    write_tsv(
        OUT_DIR / f"modern_{panel}_population_centroids.tsv",
        ["Population", "N", *[f"PC{i}" for i in range(1, N_DISTANCE_PCS + 1)]],
        [
            [
                population,
                counts[population],
                *[f"{value:.10f}" for value in centroids[population]],
            ]
            for population in sorted(centroids)
        ],
    )

    ashkenazi_candidates = [
        population for population in centroids
        if "ashkenazi" in population.lower()
    ]
    if len(ashkenazi_candidates) != 1:
        raise SystemExit(
            "ERROR: expected exactly one Ashkenazi population label; found "
            f"{ashkenazi_candidates}"
        )
    ashkenazi = ashkenazi_candidates[0]

    distances = []
    for population, centroid in centroids.items():
        if population == ashkenazi:
            continue
        distance = float(np.linalg.norm(centroids[ashkenazi] - centroid))
        distances.append([population, counts[population], distance])
    distances.sort(key=lambda row: row[2])

    write_tsv(
        OUT_DIR / (
            f"modern_{panel}_ashkenazi_centroid_distances_"
            f"pc1_pc{N_DISTANCE_PCS}.tsv"
        ),
        ["Population", "N", "Euclidean_Distance"],
        [
            [population, count, f"{distance:.10f}"]
            for population, count, distance in distances
        ],
    )

    populations = sorted(grouped)
    for x_index, y_index in [(0, 1), (0, 2)]:
        figure, axis = plt.subplots(figsize=(13, 9))
        for population in populations:
            subset = [row for row in annotated if row["Population"] == population]
            x_values = [row["PC"][x_index] for row in subset]
            y_values = [row["PC"][y_index] for row in subset]
            axis.scatter(
                x_values,
                y_values,
                s=30,
                alpha=0.75,
                label=population,
            )
            axis.text(
                float(np.mean(x_values)),
                float(np.mean(y_values)),
                population,
                fontsize=8,
                ha="center",
                va="center",
            )

        axis.axhline(0, linewidth=0.5)
        axis.axvline(0, linewidth=0.5)
        axis.set_xlabel(
            f"PC{x_index + 1} ({explained[x_index]:.2f}% variance)"
        )
        axis.set_ylabel(
            f"PC{y_index + 1} ({explained[y_index]:.2f}% variance)"
        )
        axis.set_title(
            f"{panel.replace('_', ' ').title()} PCA: "
            f"PC{x_index + 1} vs PC{y_index + 1}"
        )
        axis.legend(
            bbox_to_anchor=(1.02, 1),
            loc="upper left",
            fontsize=8,
            frameon=False,
        )
        figure.tight_layout()

        stem = OUT_DIR / (
            f"modern_{panel}_pc{x_index + 1}_pc{y_index + 1}"
        )
        figure.savefig(stem.with_suffix(".png"), dpi=300)
        figure.savefig(stem.with_suffix(".pdf"))
        plt.close(figure)

    return {
        "annotated": annotated,
        "explained": explained,
        "distances": distances,
    }


def compare_panels(
    primary: dict[str, Any],
    strict: dict[str, Any],
) -> float:
    primary_rows = {row["IID"]: row for row in primary["annotated"]}
    strict_rows = {row["IID"]: row for row in strict["annotated"]}
    shared_ids = sorted(set(primary_rows) & set(strict_rows))

    if set(shared_ids) != set(strict_rows):
        raise SystemExit(
            "ERROR: every strict-pass PCA sample must also exist in primary."
        )

    primary_matrix = np.vstack(
        [primary_rows[sample_id]["PC"][:N_DISTANCE_PCS] for sample_id in shared_ids]
    )
    strict_matrix = np.vstack(
        [strict_rows[sample_id]["PC"][:N_DISTANCE_PCS] for sample_id in shared_ids]
    )

    primary_mean = primary_matrix.mean(axis=0)
    strict_mean = strict_matrix.mean(axis=0)
    primary_centered = primary_matrix - primary_mean
    strict_centered = strict_matrix - strict_mean

    u_matrix, _, vt_matrix = np.linalg.svd(
        strict_centered.T @ primary_centered
    )
    rotation = u_matrix @ vt_matrix
    strict_aligned = strict_centered @ rotation + primary_mean

    residuals = primary_matrix - strict_aligned
    sample_rmsd = np.sqrt(np.mean(residuals ** 2, axis=1))
    overall_rmsd = float(np.sqrt(np.mean(residuals ** 2)))

    write_tsv(
        OUT_DIR / "primary_strict_procrustes_aligned_samples.tsv",
        [
            "IID", "Population", "RMSD",
            *[f"Aligned_PC{i}" for i in range(1, N_DISTANCE_PCS + 1)],
        ],
        [
            [
                sample_id,
                primary_rows[sample_id]["Population"],
                f"{sample_rmsd[index]:.10f}",
                *[f"{value:.10f}" for value in strict_aligned[index]],
            ]
            for index, sample_id in enumerate(shared_ids)
        ],
    )

    stability_rows = []
    populations = sorted(
        {primary_rows[sample_id]["Population"] for sample_id in shared_ids}
    )
    for population in populations:
        indices = [
            index
            for index, sample_id in enumerate(shared_ids)
            if primary_rows[sample_id]["Population"] == population
        ]
        values = sample_rmsd[indices]
        stability_rows.append(
            [
                population,
                len(indices),
                float(np.mean(values)),
                float(np.median(values)),
                float(np.max(values)),
            ]
        )
    stability_rows.sort(key=lambda row: row[2], reverse=True)

    write_tsv(
        OUT_DIR / "primary_strict_population_pca_stability.tsv",
        ["Population", "N", "Mean_RMSD", "Median_RMSD", "Maximum_RMSD"],
        [
            [
                population,
                count,
                f"{mean_value:.10f}",
                f"{median_value:.10f}",
                f"{maximum_value:.10f}",
            ]
            for population, count, mean_value, median_value, maximum_value
            in stability_rows
        ],
    )

    return overall_rmsd


def main() -> None:
    if Path.cwd().resolve() != ROOT:
        raise SystemExit(f"ERROR: run this script from: {ROOT}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    results: dict[str, dict[str, Any]] = {}
    for panel, paths in PANELS.items():
        print(f"Analyzing {panel} PCA...")
        results[panel] = analyze_panel(panel, paths)
        nearest = results[panel]["distances"][:5]
        print(
            f"{panel} nearest Ashkenazi centroids: "
            + ", ".join(
                f"{population} ({distance:.6f})"
                for population, _, distance in nearest
            )
        )

    overall_rmsd = compare_panels(
        results["primary"],
        results["strict_pass"],
    )

    summary_path = OUT_DIR / "pca_analysis_summary.txt"
    with summary_path.open("w", encoding="utf-8") as handle:
        handle.write("PCA analysis summary\n")
        handle.write("====================\n\n")
        handle.write(
            f"Primary-strict Procrustes RMSD across "
            f"PC1-PC{N_DISTANCE_PCS}: {overall_rmsd:.10f}\n\n"
        )
        for panel in ("primary", "strict_pass"):
            explained = results[panel]["explained"]
            handle.write(f"{panel}\n")
            handle.write("-" * len(panel) + "\n")
            handle.write(
                "Variance explained PC1-PC5: "
                + ", ".join(f"{value:.3f}%" for value in explained[:5])
                + "\n"
            )
            handle.write(
                "Five nearest population centroids to Ashkenazi using "
                f"PC1-PC{N_DISTANCE_PCS}:\n"
            )
            for rank, (population, _, distance) in enumerate(
                results[panel]["distances"][:5],
                start=1,
            ):
                handle.write(f"  {rank}. {population}: {distance:.10f}\n")
            handle.write("\n")

    print()
    print("Stage 05 PCA analysis completed successfully.")
    print(f"Primary-strict Procrustes RMSD: {overall_rmsd:.10f}")
    print(f"Outputs: {OUT_DIR}")


if __name__ == "__main__":
    main()
