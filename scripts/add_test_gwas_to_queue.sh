JSON_PAYLOAD='{
  "file_location": "gwas_upload/22d5cdd8-ac0b-bb58-d2c3-c342ac8ec78b/hg38_gwas_upload.tsv.gz",
  "metadata": {
    "guid": "22d5cdd8-ac0b-bb58-d2c3-c342ac8ec78b",
    "reference_build": "GRCh38",
    "name": "height",
    "category": "continuous",
    "is_published": false,
    "doi": null,
    "should_be_added": false,
    "ancestry": "EUR",
    "sample_size": 234234,
    "p_value_threshold": 1.5e-4,
    "column_names": {
      "SNP": null,
      "RSID": null,
      "CHR": "CHR",
      "BP": "BP",
      "EA": "EA",
      "OA": "OA",
      "P": "P",
      "BETA": "BETA",
      "OR": null,
      "SE": "SE",
      "EAF": "EAF"
    },
    "status": "processing"
  }
}'

curl -X POST http://127.0.0.1:8000/v1/internal/gwas-queue/add -H "Content-Type: application/json" -d "$JSON_PAYLOAD"

#Delete specific GWAS upload
#curl -X DELETE http://127.0.0.1:8000/v1/internal/gwas/c32e8a74-818a-0f0f-8ebf-4cc5097e6ad4

#Clear GWAS dead letter queue
#curl -X DELETE http://127.0.0.1:8000/v1/internal/gwas-dlq