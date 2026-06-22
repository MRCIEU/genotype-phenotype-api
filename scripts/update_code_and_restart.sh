#!/bin/bash
set -e

sudo docker stack deploy -c docker-swarm.yml gpmap --resolve-image always --prune --detach=true

sleep 20
bash /home/opc/genotype-phenotype-api/backup_gwas_upload_db.sh
