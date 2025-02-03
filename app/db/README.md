# Build a duckdb from the pipeline files

## Setup

```r
renv::restore()
```

## Run

```bash
Rscript process.r /local-scratch/projects/genotype-phenotype-map/results/2025_01_28-13_04 /local-scratch/projects/genotype-phenotype-map
```

This will create a `processed.db` and `assocs.db` in the `/local-scratch/projects/genotype-phenotype-map/results/2025_01_28-13_04` directory.
