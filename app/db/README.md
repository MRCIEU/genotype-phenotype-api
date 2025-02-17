# Build a duckdb from the pipeline files

Database contents:

## `processed.db`

- `studies_processed` - list of studies that have been processed
- `all_study_blocks` - each fine-mapped region for each study
- `variant_annotations` - variant annotations for all variants that were included
- `results_metadata` - summary of results for each LD block
- `coloc` - coloc results. The `id` field represents a coloc cluster, with the number of rows in that cluster representing one trait. There are also single row `id` values that represent a single finemapped region that doesn't co-localise with any other traits.
- `ld` - LD proxies for each `candidate_snp`, and LD matrix for all `candidate_snps` in a region. 

## `assocs.db`

- `assocs` - imputed summary statistics for every available `candidate_snp` extracted for every trait 

## Setup

```r
renv::restore()
```

## Run

```bash
Rscript process.r /local-scratch/projects/genotype-phenotype-map/results/2025_01_28-13_04 /local-scratch/projects/genotype-phenotype-map
```

This will create a `processed.db` and `assocs.db` in the `/local-scratch/projects/genotype-phenotype-map/results/2025_01_28-13_04` directory.
