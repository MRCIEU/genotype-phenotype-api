Data Export


Files may include:
- coloc_groups.tsv: Clustered colocalization results
- coloc_pairs.tsv: Pairwise colocalization results
- rare.tsv: Rare variant results  
- trait.tsv: High level information about the trait
- gene.tsv: High level information about the gene
- study_extractions.tsv: Study extraction data
- upload_study_extractions.tsv: additional upload specific study extraction data
- README.txt: This file

Column descriptions:
- coloc.csv: Contains posterior probabilities, candidate SNPs, and trait associations
- rare.csv: Contains rare variant associations and significance data
- study_extractions.csv: Contains study-level extraction data

For more information, visit: https://gpmap.opengwas.io

To access the GWAS / summary statistics, you can either download information related to a specific SNP on the https://gpmap.opengwas.io SNP view,
or you can access all summary statistics on a "requester pays" bucket on Google Cloud Storage: https://console.cloud.google.com/storage/browser/genotype-phenotype-map 

This limitation is enforced to reduce cost of running the GP Map.