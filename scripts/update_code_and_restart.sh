#!/bin/bash
set -e

sudo docker stack deploy -c docker-swarm.yml gpmap --resolve-image always --prune --detach=true

bash /home/opc/genotype-phenotype-api/scripts/backup_gwas_upload_db.sh