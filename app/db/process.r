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

install.packages("future.apply")
library(future.apply)
plan(multicore, workers = 1)
ext <- future_lapply(ld_blocks, \(x) generate_ld_obj(ld_dir, x, variant_annotations)) %>% bind_rows()


# Extract summary statistics
varids <- unique(all_study_blocks$SNP)
length(varids)
varids_info <- tibble(varids) %>% separate(varids, into=c("chr", "other"), sep=":", remove=FALSE)
varids_list <- lapply(1:22, \(x) {
    subset(varids_info, chr==x)$varids
})

str(varids_list)

path <- studies_processed$extracted_location[1]
path <- file.path(rtdir, "data/study/", studies_processed$study_name[1], "imputed")
dir(path)
extract_variants <- function(varids, path) {
    file_list <- list.files(path) %>% file.path(path, .)
    ext <- lapply(file_list, \(x) fread(x) %>% filter(SNP %in% varids)) %>% bind_rows()
    return(ext)
}

t1 <- Sys.time()
extract_variants(varids_list, path)
Sys.time() - t1

extract_variants2 <- function(varids_list, path, study="study") {
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

t1 <- Sys.time()
extract_variants2(varids_list, path)
Sys.time() - t1
x <- "ebi-a-GCST90026162"


table(studies_processed$source)

x <- "UKB-PPP-european-CELA2A:P08217:OID30411:v1"
x <- "UKB-PPP-european-IKBKG:Q9Y6K9:OID20544:v1"
x <- studies_processed$study_name[studies_processed$source == "brain_emeta"][28504]

assocs1 <- mclapply(studies_processed$study_name[studies_processed$source == "brain_emeta"][6], \(x) {
    message(x)
    path <- file.path(rtdir, "data/study/", x, "imputed")
    tryCatch({
        extract_variants2(varids_list, path)
    }, error=function(e) {
        message(e)
        return(NULL)
    })
}, mc.cores=30)

a1 <- bind_rows(assocs1)
a1 <- a1 %>% select(SNP, study, BETA, SE, IMPUTED, P, EAF)



assocs_source <- function(source, mc.cores=30) {
    assocs <- mclapply(studies_processed$study_name[studies_processed$source == source], \(x) {
        message(x)
        path <- file.path(rtdir, "data/study/", x, "imputed")
        tryCatch({
            extract_variants2(varids_list, path, x)
        }, error=function(e) {
            message(e)
            return(NULL)
        })
    }, mc.cores=mc.cores)
    assocs <- assocs[!sapply(assocs, \(x) inherits(x, "try-error"))]
    return(assocs %>% bind_rows())
}

assocs3 <- assocs_source("brain_emeta", 50)

assocs4 <- assocs_source("ukb", 50)
assocs5 <- assocs_source("ebi_catalog", 50)


assocs2 <- mclapply(studies_processed$study_name[studies_processed$source == "ukb_ppp"], \(x) {
    message(x)
    path <- file.path(rtdir, "data/study/", x, "imputed")
    tryCatch({
        extract_variants2(varids_list, path) %>% mutate(study=x)
    }, error=function(e) {
        message(e)
        return(tibble())
    })
}, mc.cores=30)

length(assocs2)
sapply(assocs2, class)

a2 <- lapply(assocs2, \(x) {
    if("try-error" %in% class(x)) {
        return(NULL)
    }
    return(x)
}) %>% bind_rows

dim(a2)

a2 <- bind_rows(assocs2)
a1 <- a1 %>% select(SNP, study, BETA, SE, IMPUTED, P, EAF)

a2


assocs1 <- mclapply(studies_processed$study_name[studies_processed$source == "brain_meta"], \(x) {
    message(x)
    path <- file.path(rtdir, "data/study/", x, "imputed")
    tryCatch({
        extract_variants2(varids_list, path) %>% mutate(study=x)
    }, error=function(e) {
        message(e)
        return(NULL)
    })
}, mc.cores=30)


tryCatch(adsasd, error=function(e) {
    message(e)
    return(tibble())
})




db_file <- file.path(input_dir, "processed.db")

con <- dbConnect(duckdb::duckdb(), db_file)
dbWriteTable(con, "all_study_blocks", all_study_blocks)
dbWriteTable(con, "results_metadata", results_metadata)
dbWriteTable(con, "studies_processed", studies_processed)
dbWriteTable(con, "variant_annotations", variant_annotations_full)
dbWriteTable(con, "coloc", coloc)
dbWriteTable(con, "ld", ldl)
dbWriteTable(con, "assocs", assocs)

dbDisconnect(con, shutdown=TRUE)
