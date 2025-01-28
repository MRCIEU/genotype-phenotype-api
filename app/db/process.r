library(dplyr)
library(duckdb)
library(data.table)
library(validate)
library(tidyr)

args <- commandArgs(T)

input_dir <- args[1]
db_file <- args[2]

unlink(db_file)

all_study_blocks <- fread(file.path(input_dir, "all_study_blocks.tsv"))
coloc_results <- fread(file.path(input_dir, "coloc_results.tsv"))
raw_coloc_results <- fread(file.path(input_dir, "raw_coloc_results.tsv"))
results_metadata <- fread(file.path(input_dir, "results_metadata.tsv"))
studies_processed <- fread(file.path(input_dir, "studies_processed.tsv"))
variant_annotations <- fread(file.path(input_dir, "variant_annotations.tsv"))

coloc <- raw_coloc_results %>%
    mutate(id=1:n()) %>%
    separate_longer_delim(cols=traits, delim=", ")

s <- all_study_blocks %>%
    select(study, unique_study_id, chr, bp, min_p, cis_trans, ld_block, known_gene)

coloc <- coloc %>%
    left_join(s, by=c("traits"="unique_study_id"))

con <- dbConnect(duckdb::duckdb(), db_file)
dbWriteTable(con, "all_study_blocks", all_study_blocks)
dbWriteTable(con, "results_metadata", results_metadata)
dbWriteTable(con, "studies_processed", studies_processed)
dbWriteTable(con, "variant_annotations", variant_annotations)
dbWriteTable(con, "coloc", coloc)

dbDisconnect(con, shutdown=TRUE)
