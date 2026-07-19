ASHKENAZI REFERENCE-PANEL SENSITIVITY PROJECT
COMPLETE STAGES 01–08 HANDOFF

Project purpose
===============

This project evaluates Ashkenazi Jewish population structure using deliberately
constructed Mediterranean and European reference panels. The central objective
is to test how comparator selection influences the apparent position of
Ashkenazi populations in population-genetic analyses.

The workflow emphasizes comparisons involving:

Southern Italians
Sicilians
Central Italians
Maltese
Aegean Greeks
Italian Jews / Italkim where available
Northern Italians
Tuscans
Levantine populations
Other European and Mediterranean reference populations

A principal research question is whether the commonly reported appearance of
Ashkenazi Jews as intermediate between Europe and the Levant is partly produced
by reference-panel design, especially when Southern Italian, Sicilian, Maltese,
Aegean, and Italian Jewish comparators are absent or underrepresented.

Project structure
=================

Stage 01
Source-data collection, conversion, normalization, and initial organization.

Stage 02
Sample identification, population-label harmonization, reference-panel design,
and construction of primary and strict-pass population manifests.

Stage 03
Sample-level and variant-level quality control, exclusions, integrity checks,
and documentation of retained and rejected samples and variants.

Stage 04
Construction of matched primary and strict-pass genotype datasets, shared SNP
sets, allele-order validation, and LD-pruned datasets for PCA and ADMIXTURE.

Stage 05
Principal component analysis for the primary and strict-pass panels, including:

PCA coordinates
Eigenvalues and variance explained
Population centroids
Ashkenazi centroid-distance rankings
Primary-versus-strict Procrustes comparison
Population stability measurements
PCA figures and summary documentation

Stage 06
FST analysis for the primary and strict-pass panels, including:

Hudson FST for all population pairs
Chromosome jackknife standard errors
Confidence intervals
Ashkenazi-specific population rankings
Primary-versus-strict comparisons
PLINK Weir–Cockerham validation
FST heatmaps, rankings, tables, and methods documentation

Stage 07
ADMIXTURE analysis for the primary and strict-pass panels, including:

K=2 through K=12
Five deterministic replicates per K
Ten-fold cross-validation
Raw Q matrices
Raw P matrices
Run logs
Replicate alignment
Consensus ancestry components
Replicate stability measurements
Primary-versus-strict component alignment
Ashkenazi-specific summaries
Cross-panel sensitivity analyses
Figures and tables

The completed ADMIXTURE design contains:

11 K values
5 replicates per K
2 panels
110 total ADMIXTURE runs

Stage 08
Integrated synthesis of PCA, FST, and ADMIXTURE, including:

Integrated comparator rankings
Cross-method agreement
Primary-versus-strict robustness assessment
Manuscript-ready methods and results summaries
Integrated figures and tables
Preparation for subsequent interpretation and manuscript revision

Primary and strict panels
=========================

The primary panel preserves the broad intended sample set after baseline quality
control.

The strict-pass panel applies more restrictive sample filtering and serves as a
robustness and sensitivity test.

The two panels are designed to determine whether major findings remain stable
after removing samples that do not pass the stricter criteria.

Known dataset dimensions from completed stages
==============================================

Primary panel:
369 samples

Strict-pass panel:
247 samples

Population groups:
18

Shared post-QC SNP set:
184,385 SNPs

Shared LD-pruned PCA/ADMIXTURE SNP set:
70,530 SNPs

Analytical methods
==================

Principal component analysis
Population centroid distances
Procrustes alignment
Hudson FST
Weir–Cockerham FST validation
Chromosome jackknife uncertainty estimation
ADMIXTURE maximum-likelihood ancestry inference
Ten-fold cross-validation
Multiple random-seed replicates
Component-label alignment
Consensus ancestry estimation
Cross-panel sensitivity testing
Integrated ranking across analytical methods

Interpretive caution
====================

ADMIXTURE components are statistical clusters and must not be treated as literal
historical populations without additional evidence.

PCA distances, FST rankings, and ADMIXTURE similarity measure different aspects
of population structure. Conclusions should emphasize convergence across
methods rather than relying on one plot, one K value, or one statistic.

Modern populations are imperfect proxies for historical ancestral populations.

The primary-versus-strict comparison is a sensitivity analysis, not a replacement
for appropriate ancient-DNA modeling or formal source-mixture testing.

Archive purpose
===============

This archive is intended to preserve the complete project state, including:

Original and converted data stored within the project directory
Primary and strict genotype datasets
EIGENSTRAT files
PLINK files
Manifests
QC records
Excluded-sample records
Shared SNP lists
LD-pruned SNP lists
Scripts
Logs
PCA results
FST results
ADMIXTURE results
Integrated synthesis
Figures
Tables
Methods
Completion records
Environment and software information
File inventories
Cryptographic checksums

The archive is a complete project snapshot rather than a small results-only
handoff.

Important preservation note
===========================

This archive may contain large genotype files and intermediate datasets. It
should not be modified in place. Preserve the original ZIP as a read-only master
archive and create working copies for further analysis.

Project location at archive creation
====================================

/home/computer/popgen/projects/ashkenazi_reference_test
