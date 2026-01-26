#!/bin/bash
set -e

echo "Swapping to new databases"
if [ -f /home/opc/gpmap_data/db/studies_new.db ]; then
    mv /home/opc/gpmap_data/db/studies.db /home/opc/gpmap_data/db/studies_backup.db
    mv /home/opc/gpmap_data/db/studies_new.db /home/opc/gpmap_data/db/studies.db
fi

if [ -f /home/opc/gpmap_data/db/coloc_pairs_new.db ]; then
    mv /home/opc/gpmap_data/db/coloc_pairs.db /home/opc/gpmap_data/db/coloc_pairs_backup.db
    mv /home/opc/gpmap_data/db/coloc_pairs_new.db /home/opc/gpmap_data/db/coloc_pairs.db
fi

if [ -f /home/opc/gpmap_data/db/associations_new.db ]; then
    mv /home/opc/gpmap_data/db/associations.db /home/opc/gpmap_data/db/associations_backup.db
    mv /home/opc/gpmap_data/db/associations_new.db /home/opc/gpmap_data/db/associations.db
fi

if [ -f /home/opc/gpmap_data/db/associations_full_new.db ]; then
    mv /home/opc/gpmap_data/db/associations_full.db /home/opc/gpmap_data/db/associations_full_backup.db
    mv /home/opc/gpmap_data/db/associations_full_new.db /home/opc/gpmap_data/db/associations_full.db
fi

if [ -f /home/opc/gpmap_data/db/ld_new.db ]; then
    mv /home/opc/gpmap_data/db/ld.db /home/opc/gpmap_data/db/ld_backup.db
    mv /home/opc/gpmap_data/db/ld_new.db /home/opc/gpmap_data/db/ld.db
fi

sudo docker stack deploy -c docker-swarm.yml gpmap --resolve-image always --prune --detach=true
sudo sudo docker service update --force gpmap_api
sudo sudo docker service update --force gpmap_gwas_upload_worker

echo "Refreshing cache"
sleep 5
./refresh_cache.sh

echo "Done"
