library(dplyr)
library(duckdb)
library(data.table)
library(validate)
library(tidyr)
library(R.utils)

args <- commandArgs(T)

input_dir <- "data/results/2025_01_21-09_45"

input_dir <- args[1]
db_file <- args[2]



unlink(db_file)

all_study_blocks <- fread(file.path(input_dir, "all_study_blocks.tsv"))
str(all_study_blocks)
raw_coloc_results <- fread(file.path(input_dir, "raw_coloc_results.tsv"))
str(raw_coloc_results)
results_metadata <- fread(file.path(input_dir, "results_metadata.tsv"))
str(results_metadata)
studies_processed <- fread(file.path(input_dir, "studies_processed.tsv"))
str(studies_processed)
variant_annotations <- fread(file.path(input_dir, "variant_annotations.tsv"))
str(variant_annotations)

results_metadata <- results_metadata %>%
    tidyr::separate(ld_block, into=c("pop", "chr", "start", "end"), sep="[/-]", remove=FALSE) %>%
    mutate(chr=as.integer(chr), start=as.integer(start), end=as.integer(end))

head(all_study_blocks)


# This is super slow
# all_study_blocks$ld_block <- NA
# i <- 1
# dim(all_study_blocks)
# for(i in 1:nrow(all_study_blocks)) {
#     all_study_blocks$ld_block[i] <- subset(results_metadata, chr==all_study_blocks$chr[i] & start <= all_study_blocks$bp[i] & end >= all_study_blocks$bp[i])$ld_block

#     subset(results_metadata, chr==all_study_blocks$chr[i] & start <= all_study_blocks$bp[i])$ld_block
# }


ldblocks <- lapply(unique(results_metadata$ld_block), \(x) {
    a <- fread(file.path("data/data/ld_blocks", x, "finemapped_studies.tsv")) %>% mutate(ld_block=x) %>% select(unique_study_id, ld_block)
}) %>% bind_rows()

dim(ldblocks)
dim(all_study_blocks)
all_study_blocks <- left_join(all_study_blocks, ldblocks, by="unique_study_id")
dim(all_study_blocks)


coloc <- raw_coloc_results %>%
    mutate(id=1:n()) %>%
    separate_longer_delim(cols=traits, delim=", ")

s <- all_study_blocks %>%
    select(study, unique_study_id, chr, bp, min_p, cis_trans, ld_block, known_gene)

coloc <- coloc %>%
    left_join(s, by=c("traits"="unique_study_id"))

db_file <- file.path(input_dir, "processed.db")

dir(input_dir)

a <- lapply(list.files(file.path("data/data/study/UKB-PPP-european-ZNRF4:Q8WWF5:OID31347:v1/imputed"), full.names=TRUE), fread) %>% bind_rows()









con <- dbConnect(duckdb::duckdb(), db_file)
dbWriteTable(con, "all_study_blocks", all_study_blocks)
dbWriteTable(con, "results_metadata", results_metadata)
dbWriteTable(con, "studies_processed", studies_processed)
dbWriteTable(con, "variant_annotations", variant_annotations)
dbWriteTable(con, "coloc", coloc)

dbDisconnect(con, shutdown=TRUE)




lookup_ld <- function(variants, ld_dir) {
    
}



