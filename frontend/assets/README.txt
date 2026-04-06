Data Export


Files may include:
- coloc_groups.tsv: Clustered colocalization results
- coloc_pairs.tsv: Pairwise colocalization results (except for region download)
- associations.tsv: SNP-level association statistics (beta, se, p, eaf)
- rare.tsv: Rare variant results  
- trait.tsv: High level information about the trait
- gene.tsv: High level information about the gene
- study_extractions.tsv: Study extraction data
- upload_study_extractions.tsv: Additional upload-specific study extraction data
- README.txt: This file

Column descriptions:
You can find detailed descriptions of the columns for each tsv in the "details" section of the documentation in the R package: https://mrcieu.r-universe.dev/gpmapr/doc/manual.html#trait

For more information, visit: https://gpmap.opengwas.io

To access the GWAS / summary statistics, you can either download information related to a specific SNP on the https://gpmap.opengwas.io SNP view,
or you can access all summary statistics on a "requester pays" bucket on Google Cloud Storage: https://console.cloud.google.com/storage/browser/genotype-phenotype-map 

This limitation is enforced to reduce cost of running the GPMap.