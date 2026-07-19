#!/usr/bin/env python3
"""Reproduce the Experiment 14 Ashkenazi Germany vector-geometry diagnostic.

The required Experiment 14 input files are read from the parent directory.

The script uses all 25 scaled Global25 dimensions. PCA is only a visualization;
the cosine, vector magnitudes, combined displacement, and residual are calculated
in the full 25-dimensional space.
"""
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
INPUT = HERE.parent
sources = pd.read_csv(INPUT / 'Experiment_14_Sources.csv', header=None)
targets = pd.read_csv(INPUT / 'Experiment_14_Targets.csv', header=None)
raw = pd.read_csv(INPUT / 'Experiment_14_Raw_Data.tsv', sep='\t')
sources.index = sources.iloc[:, 0]
targets.index = targets.iloc[:, 0]
src = sources.iloc[:, 1:].astype(float)
tgt = targets.iloc[:, 1:].astype(float)

central = {
    'Italian_Calabria_Reggio_Calabria_(Calabrese)_(n=9)': 22.0,
    'Italki_Jew_(n=9)': 31.8,
    'Maltese_(n=8)': 21.6,
}
levant = {
    'Lebanese_Arab_Christian_(n=27)': 9.0,
    'Palestinian_Arab_Christian_(n=24)': 7.6,
}
north = {
    'German_(n=113)': 6.8,
    'Polish_(n=68)': 1.2,
}

def centroid(weights):
    total = sum(weights.values())
    return sum(src.loc[k].to_numpy() * v for k, v in weights.items()) / total

C, L, N = centroid(central), centroid(levant), centroid(north)
vL, vN = L - C, N - C
wL, wN = 0.166 * vL, 0.080 * vN
cosine = np.dot(vL, vN) / (np.linalg.norm(vL) * np.linalg.norm(vN))
reconstruction = C + wL + wN
germany = tgt.loc['Ashkenazi_Jew_Germany_(n=10)'].to_numpy()

X = np.vstack([src.to_numpy(), tgt.to_numpy()])
Xc = X - X.mean(axis=0)
_, s, Vt = np.linalg.svd(Xc, full_matrices=False)
variance = s**2 / (X.shape[0] - 1)
explained = variance / variance.sum()
pc1 = Vt[0]
if np.dot(vL, pc1) > 0:
    pc1 = -pc1

print(f'cosine_similarity={cosine:.10f}')
print(f'central_to_levant_distance={np.linalg.norm(vL):.10f}')
print(f'central_to_north_distance={np.linalg.norm(vN):.10f}')
print(f'weighted_levant_magnitude={np.linalg.norm(wL):.10f}')
print(f'weighted_north_magnitude={np.linalg.norm(wN):.10f}')
print(f'combined_displacement_magnitude={np.linalg.norm(wL+wN):.10f}')
print(f'reconstruction_residual={np.linalg.norm(germany-reconstruction):.10f}')
print(f'reported_distance={raw.loc[raw.Target=="Ashkenazi_Jew_Germany_(n=10)", "Distance"].iloc[0]:.10f}')
print(f'pc1_explained_variance={explained[0]:.10f}')
print(f'levant_shift_pc1={np.dot(wL,pc1):.10f}')
print(f'north_shift_pc1={np.dot(wN,pc1):.10f}')
print(f'net_shift_pc1={np.dot(wL+wN,pc1):.10f}')

expected = {
    'cosine_similarity': (-0.7864541172, cosine),
    'weighted_levant_magnitude': (0.0102400003, np.linalg.norm(wL)),
    'weighted_north_magnitude': (0.0109810785, np.linalg.norm(wN)),
    'combined_displacement_magnitude': (0.0069695096, np.linalg.norm(wL+wN)),
    'reconstruction_residual': (0.0066523896, np.linalg.norm(germany-reconstruction)),
    'reported_distance': (0.0066523900, raw.loc[raw.Target=="Ashkenazi_Jew_Germany_(n=10)", "Distance"].iloc[0]),
}
for label, (reference, observed) in expected.items():
    if not np.isclose(reference, observed, rtol=0, atol=5e-10):
        raise SystemExit(f'{label} mismatch: expected {reference:.10f}, observed {observed:.10f}')
print('verification=passed')
