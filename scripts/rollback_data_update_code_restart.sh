#!/bin/bash
set -e

echo "Swapping back to old databases"
mv /home/opc/gpmap_data/db/studies.db /home/opc/gpmap_data/db/studies_new.db
mv /home/opc/gpmap_data/db/studies_backup.db /home/opc/gpmap_data/db/studies.db

mv /home/opc/gpmap_data/db/coloc_pairs.db /home/opc/gpmap_data/db/coloc_pairs_new.db
mv /home/opc/gpmap_data/db/coloc_pairs_backup.db /home/opc/gpmap_data/db/coloc_pairs.db

mv /home/opc/gpmap_data/db/associations.db /home/opc/gpmap_data/db/associations_new.db
mv /home/opc/gpmap_data/db/associations_backup.db /home/opc/gpmap_data/db/associations.db

mv /home/opc/gpmap_data/db/ld.db /home/opc/gpmap_data/db/ld_new.db
mv /home/opc/gpmap_data/db/ld_backup.db /home/opc/gpmap_data/db/ld.db

sudo docker stack deploy -c docker-swarm.yml gpmap --resolve-image always --prune --detach=true

echo "Refreshing cache"
sleep 5
./refresh_cache.sh

echo "Done"
