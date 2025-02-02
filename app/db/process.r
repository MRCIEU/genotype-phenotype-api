# sudo docker run -it -v /local-scratch/projects/genotype-phenotype-map:/project/data gpmap_duckdb R

# install.packages("R.utils")
# install.packages("furrr")


library(dplyr)
library(duckdb)
library(data.table)
library(validate)
library(tidyr)
library(R.utils)
library(purrr)
library(furrr)
library(parallel)

args <- commandArgs(T)

input_dir <- "data/results/2025_01_28-13_04"
input_dir <- "/local-scratch/projects/genotype-phenotype-map/results/2025_01_28-13_04"
rtdir <- "data"
rtdir <- "/local-scratch/projects/genotype-phenotype-map"
db_file <- file.path(input_dir, "processed.db")

input_dir <- args[1]
db_file <- args[2]
unlink(db_file)

all_study_blocks <- fread(file.path(input_dir, "all_study_blocks.tsv"))
str(all_study_blocks)
raw_coloc_results <- fread(file.path(input_dir, "raw_coloc_results.tsv"))
str(raw_coloc_results)
# rare_results <- fread(file.path(input_dir, "rare_results.tsv"))
# str(rare_results)
results_metadata <- fread(file.path(input_dir, "results_metadata.tsv"))
str(results_metadata)
studies_processed <- fread(file.path(input_dir, "studies_processed.tsv"))
str(studies_processed)
variant_annotations <- fread(file.path(input_dir, "variant_annotations.tsv"))
str(variant_annotations)
variant_annotations_full <- fread(file.path(rtdir, "data", "variant_annotation", "vep_annotations_hg38.tsv.gz"))
names(variant_annotations)
names(variant_annotations_full)

results_metadata <- results_metadata %>%
    tidyr::separate(ld_block, into=c("pop", "chr", "start", "end"), sep="[/-]", remove=FALSE) %>%
    mutate(chr=as.integer(chr), start=as.integer(start), end=as.integer(end))


vl <- mclapply(1:nrow(results_metadata), \(i) {
    message(i)
    chr <- results_metadata$chr[i]
    start <- results_metadata$start[i]
    end <- results_metadata$end[i]
    ind <- variant_annotations_full$CHR == chr & variant_annotations_full$BP >= start & variant_annotations_full$BP < end
    tibble(SNP=variant_annotations$SNP[ind], ld_block=results_metadata$ld_block[i])
}, mc.cores=50) %>% bind_rows()

variant_annotations_full <- left_join(variant_annotations_full, vl, by="SNP")
str(variant_annotations_full)


coloc <- raw_coloc_results %>%
    mutate(id=1:n()) %>%
    separate_longer_delim(cols=traits, delim=", ")

s <- all_study_blocks %>%
    select(study, unique_study_id, chr, bp, min_p, cis_trans, ld_block, known_gene)

coloc <- coloc %>%
    left_join(s, by=c("traits"="unique_study_id"))

str(coloc)


# Find finemapped results that colocalise with nothing
no_coloc <- subset(all_study_blocks, !unique_study_id %in% coloc$traits) %>% rename(candidate_snp=SNP, traits=unique_study_id) %>% mutate(id=(1:nrow(.))+nrow(coloc))
coloc <- bind_rows(coloc, no_coloc)


# all_study_blocks includes variants that don't colocalise with anything. Need to get those, but they don't have variant IDs
head(all_study_blocks)
dim(all_study_blocks)
temp <- select(variant_annotations_full, SNP, CHR, BP)
all_study_blocks <- left_join(all_study_blocks, temp, by=c("chr"="CHR", "bp"="BP")) %>% filter(!duplicated(unique_study_id))
dim(all_study_blocks)

# Add ld_block to variant_annotations
temp <- coloc %>% group_by(candidate_snp) %>% slice_head(n=1)
temp <- select(temp, candidate_snp, ld_block)
variant_annotations <- left_join(variant_annotations, temp, by=c("SNP"="candidate_snp"))
dim(variant_annotations)
head(variant_annotations)


# Generate LD
ld_dir <- "data/data/ld_reference_panel_hg38"
ld_dir <- file.path(rtdir, "data/ld_reference_panel_hg38")

generate_ld_obj <- function(ld_dir, ld_block, all_study_blocks) {
    message(ld_block)
    ld <- suppressMessages(fread(file.path(ld_dir, paste0(ld_block, ".unphased.vcor1"))))
    # ld <- readr::read_tsv(file.path(ld_dir, paste0(ld_block, ".unphased.vcor1")), col_names=FALSE)
    ldvars <- suppressMessages(scan(file.path(ld_dir, paste0(ld_block, ".unphased.vcor1.vars")), character()))
    names(ld) <- ldvars
    ld$lead <- ldvars
    ind <- which(ldvars %in% all_study_blocks$SNP)
    ld <- ld[ind,]
    ldl <- tidyr::pivot_longer(ld, cols=-lead, names_to="variant", values_to="r2") %>% filter(r2 > 0.8 | variant %in% ld$lead) %>% filter(lead != variant) %>% mutate(ld_block=ld_block)
    return(ldl)
}

ld_blocks <- unique(all_study_blocks$ld_block)
generate_ld_obj(ld_dir, ld_blocks[1000], variant_annotations)
ldl <- mclapply(ld_blocks, \(x) generate_ld_obj(ld_dir, x, variant_annotations), mc.cores=20) %>% bind_rows()


processed_db <- file.path(input_dir, "processed.db")
unlink(processed_db)

processed_con <- dbConnect(duckdb::duckdb(), processed_db)
dbWriteTable(processed_con, "all_study_blocks", all_study_blocks)
dbWriteTable(processed_con, "results_metadata", results_metadata)
dbWriteTable(processed_con, "studies_processed", studies_processed)
dbWriteTable(processed_con, "variant_annotations", variant_annotations_full)
dbWriteTable(processed_con, "coloc", coloc)
dbWriteTable(processed_con, "ld", ldl)

dbDisconnect(processed_con, shutdown=TRUE)




# Extract summary statistics
varids <- unique(all_study_blocks$SNP)
length(varids)
varids_info <- tibble(varids) %>% separate(varids, into=c("chr", "other"), sep=":", remove=FALSE)
varids_list <- lapply(1:22, \(x) {
    subset(varids_info, chr==x)$varids
})

extract_variants <- function(varids_list, path, study="study") {
    file_list <- list.files(path) %>% file.path(path, .) %>% grep("pre_filter", ., value=TRUE, invert=TRUE) %>% grep("dentist", ., value=TRUE, invert=TRUE)
    if(length(file_list) == 0) {
        return(NULL)
    }
    ext <- lapply(file_list, \(y) {
        chr <- strsplit(basename(y), "_")[[1]][2] %>% as.numeric()
        tryCatch({
            fread(y) %>% filter(SNP %in% varids_list[[chr]]) %>% select(SNP, BETA, SE, IMPUTED, P, EAF) %>% mutate(study=study)
        }, error=function(e) {
            message(e)
            return(NULL)
        })
    }) 
    ext <- ext[!sapply(ext, is.null)] %>% bind_rows()
    return(ext)
}


assocs_source <- function(source, mc.cores=30) {
    assocs <- mclapply(studies_processed$study_name[studies_processed$source == source], \(x) {
        message(x)
        path <- file.path(rtdir, "data/study/", x, "imputed")
        tryCatch({
            extract_variants(varids_list, path, x)
        }, error=function(e) {
            message(e)
            return(NULL)
        })
    }, mc.cores=mc.cores)
    assocs <- assocs[!sapply(assocs, \(x) inherits(x, "try-error"))]
    return(assocs %>% bind_rows())
}

sources <- unique(studies_processed$source)

assocs <- lapply(sources, \(x) assocs_source(x, 30))
assocs_db <- file.path(input_dir, "assocs.db")
unlink(assocs_db)
assocs_con <- dbConnect(duckdb::duckdb(), assocs_db)
dbWriteTable(assocs_con, "assocs", assocs[[1]])
for(i in 2:length(assocs)) {
    dbAppendTable(assocs_con, "assocs", assocs[[i]])
}

dbGetQuery(assocs_con, "SELECT * FROM assocs where SNP = '1:833068_A_G'")
dbGetQuery(assocs_con, "SELECT * FROM assocs where study = 'ebi-a-GCST90013905' AND P < 5e-8")

dbDisconnect(assocs_con, shutdown=TRUE)






